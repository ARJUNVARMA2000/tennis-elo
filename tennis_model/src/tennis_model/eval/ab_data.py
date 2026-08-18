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
from ..config import TUNE_YEARS, VAL_START, WTA_LOWER_STATE_FIRST_YEAR
from ..data.names import name_key
from ..data.results import load_matches
from ..model.features import build_feature_frame, main_rows
from ..model.train import walk_forward, xgb_params_for
from .kalshi_report import load_ledger, scored_set
from .metrics import score

AB_DIR = config.OUTPUT_DIR / "tuning"


def _build_oos(tour: str, include_lower: bool, start: int, end: int | None,
               ratings_only: bool = False, lower_role: str = "all") -> pd.DataFrame:
    """One arm: feature frame (with/without lower-tier rows) -> full walk-forward.

    ratings_only=True keeps lower-tier rows in the WALKS (Elo/point/context states
    see them) but drops them before walk_forward, so combiner training, per-fold
    calibration and the test folds stay main-draw-only — isolating the
    better-rating-priors mechanism from the training-distribution shift (the full
    arm measured huge tune gains but year-level instability from the shift).
    """
    flag = "INCLUDE_CHALLENGERS" if tour == "atp" else "INCLUDE_WTA_LOWER_STATE"
    prev = getattr(config, flag)
    setattr(config, flag, include_lower)
    try:
        matches = load_matches(tour)
    finally:
        setattr(config, flag, prev)
    if include_lower and lower_role != "all":
        matches = matches[
            matches["draw_level"].isin(("main", lower_role))
        ].copy()
    feat = build_feature_frame(
        df=matches, tour=tour, state_only_lower=include_lower)
    n_low = int((feat["draw_level"] != "main").sum())
    print(f"  frame: {len(feat):,} rows ({n_low:,} lower-tier)"
          + (" -> combiner sees main only" if ratings_only and n_low else ""))
    if ratings_only:
        feat = feat[feat["draw_level"] == "main"]
    return walk_forward(feat, start_test=start, end_test=end,
                        xgb_overrides=xgb_params_for(tour),
                        allow_lower=include_lower and not ratings_only)


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


def _assert_unaffected_parity(b: pd.DataFrame, a: pd.DataFrame,
                              first_effect_year: int) -> None:
    """A state-only intervention cannot alter predictions before its first row."""
    pre = b["year"].to_numpy() < int(first_effect_year)
    if not pre.any():
        return
    pb = b["p_combiner"].to_numpy()[pre]
    pa = a["p_combiner"].to_numpy()[pre]
    if not np.array_equal(pb, pa):
        max_diff = float(np.max(np.abs(pb - pa)))
        raise AssertionError(
            f"state-only A/B changed {int((pb != pa).sum()):,} pre-{first_effect_year} "
            f"prediction(s), max |d|={max_diff:.3g}; check global priors/order leakage")


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
        if not m.any():
            results[label] = (float("nan"), float("nan"))
            print(f"{label:<14}{'n/a':>10}{'n/a':>10}{'no rows':>22}")
            continue
        d = llb[m] - lla[m]                      # >0 = arm better
        se = float(d.std(ddof=1) / np.sqrt(len(d)))
        sb, sa = score(b["p_combiner"].to_numpy()[m]), score(a["p_combiner"].to_numpy()[m])
        results[label] = (float(d.mean()), se)
        print(f"{label:<14}{llb[m].mean():>10.5f}{lla[m].mean():>10.5f}"
              f"{d.mean():>+13.5f}±{se:.5f}{sb['acc']:>10.4f}{sa['acc']:>10.4f}"
              f"{sb['brier']:>9.4f}{sa['brier']:>9.4f}")

    # per-year paired d — the instability tripwire (lessons/model-research.md): a real improvement
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
    gate = bool(np.isfinite([d_tune, d_val, se_val]).all()
                and d_tune > 0 and d_val > -se_val)
    print(f"\nGATE: d_tune={d_tune:+.5f}  d_val={d_val:+.5f} (SE {se_val:.5f})  "
          f"-> {'PASS' if gate else 'REJECT'}")


def _pair_date_key(a: object, b: object, date: object) -> tuple[frozenset[str], object]:
    """Orientation-free player pair plus result date for frozen-ledger joins."""
    return frozenset((name_key(a), name_key(b))), pd.Timestamp(date).date()


def _kalshi_outside_top50_keys(s: pd.DataFrame) -> set[tuple[frozenset[str], object]]:
    """Match keys in the already-frozen Kalshi score set involving rank > 50."""
    if s.empty:
        return set()
    ra = pd.to_numeric(s["rank_a"], errors="coerce")
    rb = pd.to_numeric(s["rank_b"], errors="coerce")
    # One observed rank > 50 is sufficient evidence that the match involves an
    # outside-top-50 player; unlike "both inside", the other rank need not be known.
    outside = pd.concat([ra, rb], axis=1).max(axis=1) > 50
    return {
        _pair_date_key(r.player_a, r.player_b, r.result_date)
        for r in s.loc[outside].itertuples(index=False)
        if str(r.result_date).strip()
    }


def _slice_line(label: str, b: pd.DataFrame, a: pd.DataFrame,
                mask: np.ndarray) -> str:
    """One identical-row A/B slice; positive d means the lower-state arm wins."""
    n = int(mask.sum())
    if n == 0:
        return f"{label:<38}{'n=0':>12}"
    lb = -np.log(np.clip(b.loc[mask, "p_combiner"].to_numpy(), 1e-12, None))
    la = -np.log(np.clip(a.loc[mask, "p_combiner"].to_numpy(), 1e-12, None))
    d = lb - la
    se = float(d.std(ddof=1) / np.sqrt(n)) if n > 1 else 0.0
    return (f"{label:<38}n={n:>5,}  base={lb.mean():.5f}  arm={la.mean():.5f}  "
            f"d={d.mean():+.5f}±{se:.5f}")


def _focused_wta_slices(b: pd.DataFrame, a: pd.DataFrame,
                        kalshi: pd.DataFrame | None = None) -> None:
    """Report the WTA populations that motivated this data experiment.

    The Kalshi membership comes from ``scored_set`` before looking at either A/B
    prediction, keeping the comparison paired and frozen.
    """
    wr = pd.to_numeric(b["winner_rank"], errors="coerce")
    lr = pd.to_numeric(b["loser_rank"], errors="coerce")
    known = (wr.notna() & lr.notna()).to_numpy()
    worst = pd.concat([wr, lr], axis=1).max(axis=1).to_numpy()
    affected = b["year"].to_numpy() >= WTA_LOWER_STATE_FIRST_YEAR
    both_top50 = affected & known & (worst <= 50)
    outside_top50 = affected & (worst > 50)

    frozen = scored_set(load_ledger("wta")) if kalshi is None else kalshi
    kalshi_keys = _kalshi_outside_top50_keys(frozen)
    row_keys = [_pair_date_key(w, l, d) for w, l, d in
                zip(b["winner_name"], b["loser_name"], b["date"])]
    kalshi_outside = np.asarray([key in kalshi_keys for key in row_keys], dtype=bool)

    print("\n=== focused WTA slices (affected 2016+, same paired predictions) ===")
    print(_slice_line("both players inside top 50", b, a, both_top50))
    print(_slice_line("someone outside top 50", b, a, outside_top50))
    print(_slice_line("frozen Kalshi + outside top 50", b, a, kalshi_outside))


def run(tour: str, start: int, end: int | None, save: bool = True,
        mode: str = "full", lower_role: str = "all") -> None:
    ratings_only = mode == "ratings-only"
    print(f"=== A/B {tour}: BASELINE arm (main draws only) ===")
    base = _build_oos(tour, include_lower=False, start=start, end=end)
    print(f"=== A/B {tour}: LOWER arm (role={lower_role}, mode={mode}) ===")
    arm = _build_oos(tour, include_lower=True, start=start, end=end,
                     ratings_only=ratings_only, lower_role=lower_role)

    if save:
        AB_DIR.mkdir(parents=True, exist_ok=True)
        role_tag = "" if lower_role == "all" else f"_{lower_role}"
        tag = ("_ro" if ratings_only else "") + role_tag
        base.to_pickle(AB_DIR / f"ab_lower_{tour}_base{tag}.pkl")
        arm.to_pickle(AB_DIR / f"ab_lower_{tour}_arm{tag}.pkl")

    b, a = _align(base, arm)
    if tour == "wta":
        _assert_unaffected_parity(b, a, WTA_LOWER_STATE_FIRST_YEAR)
    _verdict(b, a)
    if tour == "wta":
        _focused_wta_slices(b, a)


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
    ap.add_argument("--lower-role", default="all", choices=["all", "qual", "chall"],
                    help="lower exp only — ablate qualifying or WTA 125 state rows")
    args = ap.parse_args()
    if args.exp == "altitude":
        run_altitude(args.tour, args.start, args.end, save=not args.no_save)
    else:
        run(args.tour, args.start, args.end, save=not args.no_save, mode=args.mode,
            lower_role=args.lower_role)
