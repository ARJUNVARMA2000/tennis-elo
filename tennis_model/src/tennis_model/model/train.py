"""Train and walk-forward-validate the XGBoost combiner.

The combiner takes the leakage-free feature frame (Elo + point-model + context) and
learns one calibrated P(A beats B). Validation is strictly walk-forward: for each
test season we train only on prior seasons, calibrate on the most recent prior season
(isotonic), then predict the held-out season. We compare against the two component
models (Elo blend, point model) on identical rows, and against the literature/market
anchors.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ..config import BACKTEST_START_YEAR, OUTPUT_DIR
from .features import FEATURES, build_feature_frame, make_oriented_xy

def _cache_path(tour: str):
    return OUTPUT_DIR / f"_features_{tour}.pkl"


def load_or_build_features(rebuild: bool = False, tour: str = "atp") -> pd.DataFrame:
    cache = _cache_path(tour)
    if not rebuild and cache.exists():
        return pd.read_pickle(cache)
    feat = build_feature_frame(tour=tour)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    feat.to_pickle(cache)
    return feat


def _xgb(**overrides):
    import xgboost as xgb
    params = dict(
        n_estimators=600, max_depth=4, learning_rate=0.03,
        subsample=0.85, colsample_bytree=0.85, min_child_weight=5.0,
        reg_lambda=1.0, objective="binary:logistic", eval_metric="logloss",
        tree_method="hist", n_jobs=0,
    )
    params.update(overrides)
    return xgb.XGBClassifier(**params)


class PlattCalibrator:
    """Smooth, monotonic probability calibration: sigmoid(a*logit(p) + b).

    Preferred over isotonic for the deployed model: with a few thousand calibration
    points isotonic forms wide piecewise-constant plateaus (distinct matchups collapse
    to identical probabilities), whereas Platt stays smooth and order-preserving.
    """

    def __init__(self, C: float = 1e4):
        from sklearn.linear_model import LogisticRegression
        self.lr = LogisticRegression(C=C, solver="lbfgs")

    @staticmethod
    def _z(p):
        p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
        return np.log(p / (1 - p)).reshape(-1, 1)

    def fit(self, p, y):
        self.lr.fit(self._z(p), np.asarray(y))
        return self

    def predict(self, p):
        return self.lr.predict_proba(self._z(p))[:, 1]


def _fit_fold(core: pd.DataFrame, cal: pd.DataFrame, seed: int):
    """Fit XGB on `core` with early stopping on `cal`, then Platt-calibrate on `cal`."""
    Xtr, ytr = make_oriented_xy(core, seed=seed)
    Xcal, ycal = make_oriented_xy(cal, seed=seed + 1)
    clf = _xgb(early_stopping_rounds=40)
    clf.fit(Xtr, ytr, eval_set=[(Xcal, ycal)], verbose=False)
    cal_model = PlattCalibrator().fit(clf.predict_proba(Xcal)[:, 1], ycal)
    return clf, cal_model


def _predict(clf, iso, feat_rows: pd.DataFrame) -> np.ndarray:
    raw = clf.predict_proba(feat_rows[FEATURES])[:, 1]
    return iso.predict(raw)


def walk_forward(feat: pd.DataFrame, start_test: int = BACKTEST_START_YEAR,
                 end_test: int = 2025, min_train_year: int = 1991) -> pd.DataFrame:
    """Out-of-sample predictions for every test season, winner-oriented."""
    from .features import ANTISYM  # noqa: F401  (kept explicit for clarity)
    feat = feat[feat["completed"]].copy()
    chunks, importances = [], []
    for ty in range(start_test, end_test + 1):
        train = feat[(feat["year"] < ty) & (feat["year"] >= min_train_year)]
        test = feat[feat["year"] == ty]
        if len(test) == 0 or len(train) < 5000:
            continue
        cal_year = ty - 1
        core = train[train["year"] < cal_year]
        cal = train[train["year"] == cal_year]
        if len(cal) < 500 or len(core) < 2000:
            core, cal = train, train  # early seasons: reuse (mild, only affects warm-up folds)
        clf, iso = _fit_fold(core, cal, seed=ty)
        p = _predict(clf, iso, test)            # P(winner wins) — test is winner-oriented
        chunks.append(test.assign(p_combiner=p))
        importances.append(pd.Series(clf.feature_importances_, index=FEATURES))
        print(f"  {ty}: train={len(train):,} test={len(test):,}  combiner brier="
              f"{np.mean((1 - p) ** 2):.4f}")
    oos = pd.concat(chunks, ignore_index=True)
    imp = pd.concat(importances, axis=1).mean(axis=1).sort_values(ascending=False)
    walk_forward.importances = imp  # stash for the caller
    return oos


def report(oos: pd.DataFrame) -> None:
    from ..eval.metrics import calibration_table, score, winner_oriented

    print(f"\n=== Walk-forward OOS: {len(oos):,} matches "
          f"({oos['year'].min()}-{oos['year'].max()}) ===")
    print(f"{'model':<16}{'acc':>9}{'logloss':>10}{'brier':>9}")
    for label, col in [("Elo blended", "p_blend"), ("Point model", "p_point"),
                       ("XGB combiner", "p_combiner")]:
        s = score(oos[col].to_numpy())
        print(f"{label:<16}{s['acc']:>9.3f}{s['logloss']:>10.4f}{s['brier']:>9.4f}")
    print("anchors:        Weighted Elo 0.664 / .212 brier ;  bookmaker 0.690 / .196")

    wf = np.arange(len(oos)) % 2 == 0
    p_a, lab = winner_oriented(oos["p_combiner"].to_numpy(), wf)
    print("\nCalibration (XGB combiner):")
    print(calibration_table(p_a, lab).to_string(index=False))

    if hasattr(walk_forward, "importances"):
        print("\nTop feature importances (avg across folds):")
        print(walk_forward.importances.head(12).to_string())


def train_final(feat: pd.DataFrame, min_train_year: int = 1991, cal_days: int = 365):
    """Train the production combiner on all data, calibrating on the most recent
    ~12 months (a robust holdout — the partial current season alone is too small)."""
    feat = feat[feat["completed"] & (feat["year"] >= min_train_year)]
    cutoff = feat["date"].max() - np.timedelta64(cal_days, "D")
    core = feat[feat["date"] < cutoff]
    cal = feat[feat["date"] >= cutoff]
    clf, iso = _fit_fold(core, cal, seed=12345)
    return clf, iso, FEATURES


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="atp", choices=["atp", "wta"])
    ap.add_argument("--rebuild", action="store_true", help="rebuild feature cache")
    ap.add_argument("--start", type=int, default=BACKTEST_START_YEAR)
    ap.add_argument("--end", type=int, default=2025)
    args = ap.parse_args()
    feat = load_or_build_features(rebuild=args.rebuild, tour=args.tour)
    oos = walk_forward(feat, start_test=args.start, end_test=args.end)
    report(oos)
