"""Train and walk-forward-validate the XGBoost combiner.

The combiner takes the leakage-free feature frame (Elo + point-model + context) and
learns one calibrated P(A beats B). Validation is strictly walk-forward: for each
test season we train only on prior seasons, then predict the held-out season.

Calibration: each fold Platt-calibrates on the most recent prior season. The
"honest" alternative — calibrating on the pooled out-of-sample predictions of all
earlier folds (--pooled-cal) — measured clearly WORSE (ATP Brier 0.2013 vs 0.1994):
early folds' weaker models pollute the mapping, while the prior-season fit matches
the current fold's output distribution. Isotonic also lost to Platt at every size
tried (--cal isotonic to re-check). We compare against the two component models
(Elo blend, point model) on identical rows, and against the literature/market anchors.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ..config import BACKTEST_START_YEAR, OUTPUT_DIR
from .features import FEATURES, build_feature_frame, make_oriented_xy


def _cache_path(tour: str):
    from ..config import INCLUDE_CHALLENGERS, INCLUDE_WTA_LOWER_STATE  # patchable
    # regime-keyed: a cache built without lower-tier rows must never silently
    # serve a run that expects them (and vice versa)
    lower = INCLUDE_CHALLENGERS if tour == "atp" else INCLUDE_WTA_LOWER_STATE
    suffix = "_lower" if lower else ""
    return OUTPUT_DIR / f"_features_{tour}{suffix}.pkl"


def load_or_build_features(rebuild: bool = False, tour: str = "atp") -> pd.DataFrame:
    cache = _cache_path(tour)
    if not rebuild and cache.exists():
        feat = pd.read_pickle(cache)
        if set(FEATURES) <= set(feat.columns):
            return feat
        # cache predates a feature addition — rebuild instead of KeyError-ing
        # inside make_oriented_xy (mirrors pipeline._predictor_current)
        print(f"  feature cache {cache.name}: stale schema -> rebuilding")
    feat = build_feature_frame(tour=tour)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    feat.to_pickle(cache)
    return feat


def xgb_params_for(tour: str) -> dict:
    """The adopted per-tour combiner hyperparameters (empty dict = _xgb defaults)."""
    from ..config import XGB_PARAM_OVERRIDES  # read at call time (patchable)
    return dict(XGB_PARAM_OVERRIDES.get(tour, {}))


# Combiner defaults (per-tour adopted overrides in config.XGB_PARAM_OVERRIDES layer on
# top). reg_alpha/gamma are the xgboost library defaults, spelled out so the published
# method.json can state them.
XGB_DEFAULTS = dict(
    n_estimators=600, max_depth=4, learning_rate=0.03,
    subsample=0.85, colsample_bytree=0.85, min_child_weight=5.0,
    reg_alpha=0.0, reg_lambda=1.0, gamma=0.0,
    objective="binary:logistic", eval_metric="logloss",
    tree_method="hist", n_jobs=0, random_state=0,  # explicit: sweeps A/B paired fits
)
EARLY_STOPPING_ROUNDS = 40   # on the calibration season; n_estimators is only a cap
FINAL_TRAIN_SEED = 12345

# the knobs sweeps tune (published in method.json) — not the plumbing args above
_XGB_DISPLAY_KEYS = ("n_estimators", "max_depth", "learning_rate", "subsample",
                     "colsample_bytree", "min_child_weight", "reg_alpha", "reg_lambda",
                     "gamma")


def effective_xgb_params(tour: str) -> dict:
    """The hyperparameters the tour's combiner actually trains with (defaults layered
    with the adopted overrides), restricted to the display-relevant keys."""
    merged = {**XGB_DEFAULTS, **xgb_params_for(tour)}
    return {k: merged[k] for k in _XGB_DISPLAY_KEYS}


def _xgb(**overrides):
    import xgboost as xgb
    params = dict(XGB_DEFAULTS)
    params.update(overrides)
    return xgb.XGBClassifier(**params)


def full_xgb_params(overrides: dict | None = None, *, bag_index: int = 0) -> dict:
    """Every constructor parameter used by one fitted bag member.

    This is the serialization contract as well as the training source of truth: the
    predictor envelope must describe the complete requested XGBoost configuration,
    including the early-stopping setting and each bag member's distinct tree seed.
    """
    if type(bag_index) is not int or bag_index < 0:
        raise ValueError("bag_index must be a non-negative integer")
    params = {**XGB_DEFAULTS, **(overrides or {})}
    params["random_state"] = int(params["random_state"]) + bag_index
    params["early_stopping_rounds"] = EARLY_STOPPING_ROUNDS
    return params


def production_xgb_params(tour: str, *, bag_index: int = 0) -> dict:
    """Complete XGBoost parameters for a production tour bag member."""
    return full_xgb_params(xgb_params_for(tour), bag_index=bag_index)


class BaggedClassifier:
    """Average predict_proba over seed-varied XGB fits (variance reduction).

    Members differ in training-set orientation and tree seed; the k=0 member is
    exactly the incumbent single fit, so n_bag=1 reproduces it bit-for-bit.
    """

    def __init__(self, clfs):
        self.clfs = clfs

    def predict_proba(self, X):
        return np.mean([c.predict_proba(X) for c in self.clfs], axis=0)

    @property
    def feature_importances_(self):
        return np.mean([c.feature_importances_ for c in self.clfs], axis=0)

    def get_booster(self):
        # members share one schema; delegating keeps the pipeline's stale-feature
        # guard (predictor.clf.get_booster().feature_names) working when bagged
        return self.clfs[0].get_booster()


class PlattCalibrator:
    """Smooth, monotonic probability calibration: sigmoid(a*logit(p) + b).

    Stays smooth and order-preserving at any calibration-set size (isotonic forms
    piecewise-constant plateaus when the set is small — with the pooled-OOS set it
    becomes viable; compare via --cal isotonic).
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


class IsotonicCalibrator:
    """Non-parametric monotone calibration (needs a large calibration set)."""

    def __init__(self):
        from sklearn.isotonic import IsotonicRegression
        self.ir = IsotonicRegression(y_min=1e-4, y_max=1 - 1e-4, out_of_bounds="clip")

    def fit(self, p, y):
        self.ir.fit(np.asarray(p, dtype=float), np.asarray(y))
        return self

    def predict(self, p):
        return self.ir.predict(np.asarray(p, dtype=float))


class IdentityCalibrator:
    def fit(self, p, y):
        return self

    def predict(self, p):
        return np.asarray(p, dtype=float)


class StackedCalibrator:
    """Season-level re-blend: logistic regression on [logit(p_raw), logit(p_blend),
    logit(p_point)] — lets the calibration season also correct the combiner's weighting
    of its two component models, not just its probability scale."""

    def __init__(self, C: float = 1e4):
        from sklearn.linear_model import LogisticRegression
        self.lr = LogisticRegression(C=C, solver="lbfgs")

    @staticmethod
    def _z(cols):
        z = []
        for c in cols:
            p = np.clip(np.asarray(c, dtype=float), 1e-6, 1 - 1e-6)
            z.append(np.log(p / (1 - p)))
        return np.column_stack(z)

    def fit(self, cols, y):
        self.lr.fit(self._z(cols), np.asarray(y))
        return self

    def predict(self, cols):
        return self.lr.predict_proba(self._z(cols))[:, 1]


_CALIBRATORS = {"platt": PlattCalibrator, "isotonic": IsotonicCalibrator,
                "none": IdentityCalibrator}
_MIN_POOLED = 3000            # pooled-OOS rows needed before we trust pooled calibration


def _orient_for_cal(p_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Winner-oriented raw predictions -> balanced (p, y) for calibrator fitting."""
    flip = np.arange(len(p_raw)) % 2 == 1
    return np.where(flip, 1.0 - p_raw, p_raw), np.where(flip, 0, 1)


def _fit_fold(core: pd.DataFrame, cal: pd.DataFrame, seed: int,
              calibrator: str = "platt", pooled_raw: np.ndarray | None = None,
              xgb_overrides: dict | None = None, n_bag: int = 1,
              sample_weight: np.ndarray | None = None):
    """Fit XGB on `core` with early stopping on `cal`; calibrate on the pooled OOS
    predictions of earlier folds when available, else on `cal`.

    n_bag > 1 averages seed-varied fits (training orientation + tree seed vary; the
    k=0 member is the incumbent fit, so n_bag=1 is bit-identical to the single fit).
    `sample_weight` aligns with `core` rows (orientation flips don't reorder)."""
    Xcal, ycal = make_oriented_xy(cal, seed=seed + 1)
    clfs = []
    for k in range(n_bag):
        Xtr, ytr = make_oriented_xy(core, seed=seed + 100_000 * k)
        clf = _xgb(**full_xgb_params(xgb_overrides, bag_index=k))
        clf.fit(Xtr, ytr, sample_weight=sample_weight,
                eval_set=[(Xcal, ycal)], verbose=False)
        clfs.append(clf)
    model = clfs[0] if n_bag == 1 else BaggedClassifier(clfs)
    if pooled_raw is not None and len(pooled_raw) >= _MIN_POOLED:
        p, y = _orient_for_cal(pooled_raw)
    else:
        p, y = model.predict_proba(Xcal)[:, 1], ycal
    cal_model = _CALIBRATORS[calibrator]().fit(p, y)
    return model, cal_model


def _stacked_predict(clf, cal_rows: pd.DataFrame, raw: np.ndarray,
                     test: pd.DataFrame) -> np.ndarray:
    """Fit a StackedCalibrator on the calibration season and apply it to `raw`."""
    raw_cal = clf.predict_proba(cal_rows[FEATURES])[:, 1]
    flip = np.arange(len(raw_cal)) % 2 == 1

    def _cols(pr, rows, fl):
        return [np.where(fl, 1 - pr, pr),
                np.where(fl, 1 - rows["p_blend"].to_numpy(), rows["p_blend"].to_numpy()),
                np.where(fl, 1 - rows["p_point"].to_numpy(), rows["p_point"].to_numpy())]

    stk = StackedCalibrator().fit(_cols(raw_cal, cal_rows, flip), np.where(flip, 0, 1))
    return stk.predict(_cols(raw, test, np.zeros(len(raw), dtype=bool)))


def _combiner_rows(feat: pd.DataFrame, *, allow_lower: bool = False) -> pd.DataFrame:
    """The single admission boundary for combiner fitting/scoring.

    Sequential rating/serve/context walks happen before this function and may consume
    lower-tier rows.  Production combiner callers must not remember to filter them at
    each call site: lower-row training is available only through the explicit research
    opt-in used by the full-distribution A/B arm.
    """
    if allow_lower:
        return feat
    from .features import main_rows
    return main_rows(feat)


def walk_forward(feat: pd.DataFrame, start_test: int = BACKTEST_START_YEAR,
                 end_test: int | None = None, min_train_year: int = 1991,
                 cal: str = "platt", pooled_cal: bool = False,
                 xgb_overrides: dict | None = None, verbose: bool = True,
                 n_bag: int | None = None,
                 weight_halflife: float | None = None,
                 allow_lower: bool = False) -> pd.DataFrame:
    """Out-of-sample predictions for every test season, winner-oriented.

    `n_bag=None` reads config.N_BAG (production = bagged; sweeps pass 1 for speed).
    `weight_halflife` (years) exponentially down-weights older training seasons
    (None = uniform, the incumbent). `cal="stacked"` re-blends the combiner with its
    component models on the calibration season instead of plain Platt."""
    from .features import ANTISYM  # noqa: F401  (kept explicit for clarity)
    if n_bag is None:
        from ..config import N_BAG  # read at call time (patchable)
        n_bag = N_BAG
    if end_test is None:
        end_test = int(feat["year"].max())
    feat = _combiner_rows(feat, allow_lower=allow_lower)
    feat = feat[feat["completed"]].copy()
    chunks, importances = [], []
    for ty in range(start_test, end_test + 1):
        train = feat[(feat["year"] < ty) & (feat["year"] >= min_train_year)]
        test = feat[feat["year"] == ty]
        if len(test) == 0 or len(train) < 5000:
            continue
        cal_year = ty - 1
        core = train[train["year"] < cal_year]
        cal_rows = train[train["year"] == cal_year]
        if len(cal_rows) < 500 or len(core) < 2000:
            core, cal_rows = train, train  # early seasons: reuse (mild, warm-up folds only)
        pooled = (np.concatenate([c["p_raw"].to_numpy() for c in chunks])
                  if pooled_cal and chunks else None)
        sw = (np.power(0.5, (ty - core["year"].to_numpy()) / float(weight_halflife))
              if weight_halflife else None)
        clf, cal_model = _fit_fold(core, cal_rows, seed=ty,
                                   calibrator=("none" if cal == "stacked" else cal),
                                   pooled_raw=pooled, xgb_overrides=xgb_overrides,
                                   n_bag=n_bag, sample_weight=sw)
        raw = clf.predict_proba(test[FEATURES])[:, 1]
        # P(winner wins) — test is winner-oriented
        p = (_stacked_predict(clf, cal_rows, raw, test) if cal == "stacked"
             else cal_model.predict(raw))
        chunks.append(test.assign(p_combiner=p, p_raw=raw))
        importances.append(pd.Series(clf.feature_importances_, index=FEATURES))
        if verbose:
            print(f"  {ty}: train={len(train):,} test={len(test):,}  combiner brier="
                  f"{np.mean((1 - p) ** 2):.4f}")
    if not chunks:
        raise ValueError(f"walk_forward: no scoreable folds in [{start_test}, {end_test}]"
                         " — check the feature frame's year range")
    oos = pd.concat(chunks, ignore_index=True)
    imp = pd.concat(importances, axis=1).mean(axis=1).sort_values(ascending=False)
    walk_forward.importances = imp  # stash for the caller
    return oos


def walk_forward_state_gate(base_feat: pd.DataFrame, enriched_feat: pd.DataFrame,
                            thresholds: tuple[int | None, ...],
                            start_test: int = BACKTEST_START_YEAR,
                            end_test: int | None = None,
                            min_train_year: int = 1991,
                            xgb_overrides: dict | None = None,
                            verbose: bool = True,
                            n_bag: int | None = None) -> dict[int | None, pd.DataFrame]:
    """Score state-gated arms through ONE unchanged baseline combiner per fold.

    The lower-tier intervention is prediction-time state enrichment, not a new
    combiner-training population.  Every fold therefore fits and calibrates on the
    main-only ``base_feat``.  Each requested threshold selects complete enriched
    feature rows only for its eligible test matchups; ``None`` is the bit-identical
    baseline arm.  Training once per fold also keeps a threshold sweep paired down
    to the exact same fitted models.
    """
    from .features import select_dual_state_features

    if not thresholds or len(set(thresholds)) != len(thresholds):
        raise ValueError("state-gate thresholds must be a non-empty unique tuple")
    if n_bag is None:
        from ..config import N_BAG
        n_bag = N_BAG
    if end_test is None:
        end_test = int(base_feat["year"].max())

    base = _combiner_rows(base_feat)
    arms = {
        threshold: _combiner_rows(
            select_dual_state_features(base_feat, enriched_feat, threshold))
        for threshold in thresholds
    }
    base = base[base["completed"]].reset_index(drop=True)
    arms = {
        threshold: frame[frame["completed"]].reset_index(drop=True)
        for threshold, frame in arms.items()
    }
    for threshold, frame in arms.items():
        if len(frame) != len(base):
            raise AssertionError(
                f"state-gate arm {threshold} changed completed-row count: "
                f"{len(frame)} vs {len(base)}")

    chunks: dict[int | None, list[pd.DataFrame]] = {t: [] for t in thresholds}
    importances = []
    for ty in range(start_test, end_test + 1):
        train = base[(base["year"] < ty) & (base["year"] >= min_train_year)]
        test = base[base["year"] == ty]
        if len(test) == 0 or len(train) < 5000:
            continue
        cal_year = ty - 1
        core = train[train["year"] < cal_year]
        cal_rows = train[train["year"] == cal_year]
        if len(cal_rows) < 500 or len(core) < 2000:
            core, cal_rows = train, train
        clf, cal_model = _fit_fold(
            core, cal_rows, seed=ty, calibrator="platt",
            xgb_overrides=xgb_overrides, n_bag=n_bag)
        importances.append(pd.Series(clf.feature_importances_, index=FEATURES))

        for threshold, frame in arms.items():
            test_arm = frame[frame["year"] == ty]
            if len(test_arm) != len(test):
                raise AssertionError(
                    f"state-gate arm {threshold} changed {ty} test rows: "
                    f"{len(test_arm)} vs {len(test)}")
            raw = clf.predict_proba(test_arm[FEATURES])[:, 1]
            p = cal_model.predict(raw)
            chunks[threshold].append(test_arm.assign(p_combiner=p, p_raw=raw))
        if verbose:
            baseline = chunks[None][-1] if None in chunks else chunks[thresholds[0]][-1]
            p = baseline["p_combiner"].to_numpy()
            print(f"  {ty}: train={len(train):,} test={len(test):,}  combiner brier="
                  f"{np.mean((1 - p) ** 2):.4f}")

    if not any(chunks.values()):
        raise ValueError(f"walk_forward_state_gate: no scoreable folds in "
                         f"[{start_test}, {end_test}]")
    walk_forward_state_gate.importances = (
        pd.concat(importances, axis=1).mean(axis=1).sort_values(ascending=False))
    return {threshold: pd.concat(parts, ignore_index=True)
            for threshold, parts in chunks.items()}


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


def train_final(feat: pd.DataFrame, min_train_year: int = 1991, cal_days: int = 365,
                cal: str = "platt", oos: pd.DataFrame | None = None,
                xgb_overrides: dict | None = None, n_bag: int | None = None,
                allow_lower: bool = False):
    """Train the production combiner on all data. Calibrates on the walk-forward's
    pooled OOS predictions when provided (honest, large), else on the most recent
    ~12 months (a robust holdout — the partial current season alone is too small).
    `n_bag=None` reads config.N_BAG (production = bagged)."""
    if n_bag is None:
        from ..config import N_BAG
        n_bag = N_BAG
    feat = _combiner_rows(feat, allow_lower=allow_lower)
    feat = feat[feat["completed"] & (feat["year"] >= min_train_year)]
    cutoff = feat["date"].max() - np.timedelta64(cal_days, "D")
    core = feat[feat["date"] < cutoff]
    cal_rows = feat[feat["date"] >= cutoff]
    pooled = (oos["p_raw"].to_numpy()
              if oos is not None and "p_raw" in oos and len(oos) >= _MIN_POOLED else None)
    clf, cal_model = _fit_fold(core, cal_rows, seed=FINAL_TRAIN_SEED,
                               calibrator=cal, pooled_raw=pooled,
                               xgb_overrides=xgb_overrides, n_bag=n_bag)
    return clf, cal_model, FEATURES


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="atp", choices=["atp", "wta"])
    ap.add_argument("--rebuild", action="store_true", help="rebuild feature cache")
    ap.add_argument("--start", type=int, default=BACKTEST_START_YEAR)
    ap.add_argument("--end", type=int, default=None,
                    help="last test year (default: latest year in the data)")
    ap.add_argument("--cal", default="platt", choices=sorted(_CALIBRATORS) + ["stacked"])
    ap.add_argument("--pooled-cal", action="store_true",
                    help="calibrate on pooled prior-fold OOS (measured worse; kept "
                         "for experiments)")
    args = ap.parse_args()
    feat = load_or_build_features(rebuild=args.rebuild, tour=args.tour)
    oos = walk_forward(feat, start_test=args.start, end_test=args.end,
                       cal=args.cal, pooled_cal=args.pooled_cal,
                       xgb_overrides=xgb_params_for(args.tour))
    report(oos)
