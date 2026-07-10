"""Paired A/B arbiter for DATA-side experiments (A5 challenger+quali ingestion).

Unlike parameter sweeps (eval/tune.py), a data experiment changes the match set the
walks consume, so the two arms build separate feature frames end-to-end. The gate is
scored on the IDENTICAL main-draw eval set: lower-tier rows feed the rating walks but
are never scored — otherwise d would measure eval-set drift, not rating quality.

Protocol (matches the established arbiter): full walk-forward with the adopted
combiner params and production bagging (config.N_BAG), paired per-match log-loss
d±SE reported on tune (2010-19), validation (2020+) and full windows.
Gate: d_tune > 0 AND d_val > -1*SE_val.

Run:  PYTHONPATH=src python -m tennis_model.eval.ab_data --tour atp
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from .. import config
from ..config import TUNE_YEARS, VAL_START
from ..model.features import build_feature_frame, main_rows
from ..model.train import walk_forward, xgb_params_for
from .metrics import score

AB_DIR = config.OUTPUT_DIR / "tuning"


def _build_oos(tour: str, include_lower: bool, start: int, end: int | None,
               ratings_only: bool = False) -> pd.DataFrame:
    """One arm: feature frame (with/without lower-tier rows) -> full walk-forward.

    ratings_only=True keeps lower-tier rows in the WALKS (Elo/point/context states
    see them) but drops them before walk_forward, so combiner training, per-fold
    calibration and the test folds stay main-draw-only — isolating the
    better-rating-priors mechanism from the training-distribution shift (the full
    arm measured huge tune gains but year-level instability from the shift).
    """
    prev = config.INCLUDE_CHALLENGERS
    config.INCLUDE_CHALLENGERS = include_lower
    try:
        feat = build_feature_frame(tour=tour)
    finally:
        config.INCLUDE_CHALLENGERS = prev
    n_low = int((feat["draw_level"] != "main").sum())
    print(f"  frame: {len(feat):,} rows ({n_low:,} lower-tier)"
          + (" -> combiner sees main only" if ratings_only and n_low else ""))
    if ratings_only:
        feat = feat[feat["draw_level"] == "main"]
    return walk_forward(feat, start_test=start, end_test=end,
                        xgb_overrides=xgb_params_for(tour))


def _key(df: pd.DataFrame) -> pd.Series:
    """Match identity, stable across arms: post-dedup (winner, loser, date, round)
    is unique and round_order preserves the distinctions that matter here."""
    return (df["winner_name"].astype(str) + "|" + df["loser_name"].astype(str)
            + "|" + df["date"].astype(str) + "|" + df["round_order"].astype(str))


def _align(base: pd.DataFrame, arm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pair the two arms' main-draw rows 1:1; loud about any residue."""
    arm = arm[arm["draw_level"] == "main"]
    b = base.assign(__k=_key(base)).set_index("__k")
    a = arm.assign(__k=_key(arm)).set_index("__k")
    if not (b.index.is_unique and a.index.is_unique):
        raise AssertionError("A/B pairing key is not unique — investigate before trusting d±SE")
    only_b, only_a = b.index.difference(a.index), a.index.difference(b.index)
    if len(only_b) or len(only_a):
        print(f"  WARNING: eval sets differ: base-only={len(only_b)}, arm-only={len(only_a)} "
              f"(scoring the intersection)")
        common = b.index.intersection(a.index)
        b, a = b.loc[common], a.loc[common]
    return b, a.loc[b.index]


def _verdict(b: pd.DataFrame, a: pd.DataFrame) -> None:
    """Paired d±SE table + gate for two row-aligned OOS frames (base, arm)."""
    print(f"\n=== paired eval set: {len(b):,} matches "
          f"({b['year'].min()}-{b['year'].max()}) ===")
    llb = -np.log(np.clip(b["p_combiner"].to_numpy(), 1e-12, None))
    lla = -np.log(np.clip(a["p_combiner"].to_numpy(), 1e-12, None))
    years = b["year"].to_numpy()
    windows = [("tune 2010-19", (years >= TUNE_YEARS[0]) & (years <= TUNE_YEARS[1])),
               (f"val {VAL_START}+", years >= VAL_START),
               ("full", np.ones(len(years), dtype=bool))]

    results = {}
    print(f"{'window':<14}{'base ll':>10}{'arm ll':>10}{'d±SE':>22}"
          f"{'base acc':>10}{'arm acc':>10}{'base br':>9}{'arm br':>9}")
    for label, m in windows:
        d = llb[m] - lla[m]                      # >0 = arm better
        se = float(d.std(ddof=1) / np.sqrt(len(d)))
        sb, sa = score(b["p_combiner"].to_numpy()[m]), score(a["p_combiner"].to_numpy()[m])
        results[label] = (float(d.mean()), se)
        print(f"{label:<14}{llb[m].mean():>10.5f}{lla[m].mean():>10.5f}"
              f"{d.mean():>+13.5f}±{se:.5f}{sb['acc']:>10.4f}{sa['acc']:>10.4f}"
              f"{sb['brier']:>9.4f}{sa['brier']:>9.4f}")

    # per-year paired d — the instability tripwire (lessons.md): a real improvement
    # lifts (nearly) every year; bidirectional many-SE flapping = distribution artifact
    print("\nper-year paired d (>0 = arm better):")
    year_means = []
    for y in np.unique(years):
        dy = llb[years == y] - lla[years == y]
        se_y = float(dy.std(ddof=1) / np.sqrt(len(dy))) if len(dy) > 1 else 0.0
        t = f"{dy.mean() / se_y:+6.1f}" if se_y > 0 else "     -"
        year_means.append(float(dy.mean()))
        print(f"  {int(y)}: {dy.mean():+.5f}±{se_y:.5f}  t={t}  n={len(dy):,}")
    n_pos = sum(1 for m in year_means if m > 0)
    print(f"per-year: {n_pos}/{len(year_means)} positive, "
          f"max |d| = {max(abs(m) for m in year_means):.5f}")

    d_tune, _ = results["tune 2010-19"]
    d_val, se_val = results[f"val {VAL_START}+"]
    gate = d_tune > 0 and d_val > -se_val
    print(f"\nGATE: d_tune={d_tune:+.5f}  d_val={d_val:+.5f} (SE {se_val:.5f})  "
          f"-> {'PASS' if gate else 'REJECT'}")


def run(tour: str, start: int, end: int | None, save: bool = True,
        mode: str = "full") -> None:
    ratings_only = mode == "ratings-only"
    print(f"=== A/B {tour}: BASELINE arm (main draws only) ===")
    base = _build_oos(tour, include_lower=False, start=start, end=end)
    print(f"=== A/B {tour}: LOWER arm (challenger + qualifying, mode={mode}) ===")
    arm = _build_oos(tour, include_lower=True, start=start, end=end,
                     ratings_only=ratings_only)

    if save:
        AB_DIR.mkdir(parents=True, exist_ok=True)
        tag = "_ro" if ratings_only else ""
        base.to_pickle(AB_DIR / f"ab_lower_{tour}_base{tag}.pkl")
        arm.to_pickle(AB_DIR / f"ab_lower_{tour}_arm{tag}.pkl")

    b, a = _align(base, arm)
    _verdict(b, a)


def run_altitude(tour: str, start: int, end: int | None, save: bool = True) -> None:
    """Altitude feature A/B: ONE frame under the current (adopted) regime; the
    baseline arm zeroes altitude_km so both arms carry the same column count and
    colsample behavior — the paired d isolates the altitude signal exactly.
    Rows are identical by construction, so pairing is positional."""
    print(f"=== A/B {tour}: altitude — building frame (current regime) ===")
    feat = main_rows(build_feature_frame(tour=tour))
    nz = int((feat["altitude_km"] > 0.5).sum())
    print(f"  frame: {len(feat):,} main rows; {nz:,} at >500 m")
    print(f"=== A/B {tour}: BASELINE arm (altitude_km zeroed) ===")
    base = walk_forward(feat.assign(altitude_km=0.0), start_test=start, end_test=end,
                        xgb_overrides=xgb_params_for(tour))
    print(f"=== A/B {tour}: ALTITUDE arm (real values) ===")
    arm = walk_forward(feat, start_test=start, end_test=end,
                       xgb_overrides=xgb_params_for(tour))
    if save:
        AB_DIR.mkdir(parents=True, exist_ok=True)
        base.to_pickle(AB_DIR / f"ab_alt_{tour}_base.pkl")
        arm.to_pickle(AB_DIR / f"ab_alt_{tour}_arm.pkl")
    _verdict(base, arm)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="atp", choices=["atp", "wta"])
    ap.add_argument("--start", type=int, default=config.BACKTEST_START_YEAR)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--no-save", action="store_true", help="skip writing OOS pickles")
    ap.add_argument("--exp", default="lower", choices=["lower", "altitude"])
    ap.add_argument("--mode", default="full", choices=["full", "ratings-only"],
                    help="lower exp only — full: lower rows also train the combiner; "
                         "ratings-only: walks see them, the combiner sees main only")
    args = ap.parse_args()
    if args.exp == "altitude":
        run_altitude(args.tour, args.start, args.end, save=not args.no_save)
    else:
        run(args.tour, args.start, args.end, save=not args.no_save, mode=args.mode)
