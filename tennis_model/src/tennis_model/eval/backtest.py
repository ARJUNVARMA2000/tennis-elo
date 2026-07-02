"""Walk-forward backtest of the Elo ratings.

Because run_elo records each match's probability BEFORE updating ratings, every
prediction is already out-of-sample — the single chronological pass is itself a
walk-forward test. We score the post-warmup window and compare the overall-only,
surface-only, and blended ratings, plus a ranking-difference baseline.
"""

from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from ..config import BACKTEST_START_YEAR
from ..data.results import load_matches
from ..ratings.build import run_elo
from .metrics import calibration_table, score, winner_oriented


def _rank_baseline_p(df: pd.DataFrame) -> np.ndarray:
    """P(winner) from ATP rank points alone (logistic on log-point ratio)."""
    wp = pd.to_numeric(df["winner_rank_points"], errors="coerce")
    lp = pd.to_numeric(df["loser_rank_points"], errors="coerce")
    r = np.log((wp + 1) / (lp + 1))
    return 1.0 / (1.0 + np.exp(-r))  # slope 1 in log-points; rough but honest baseline


def run_backtest(start_year: int = BACKTEST_START_YEAR, min_matches: int = 0,
                 tour: str = "atp") -> dict:
    from ..ratings.elo import params_for
    df = load_matches(tour)
    st, feats = run_elo(df, params=params_for(tour))
    data = df.join(feats)

    mask = (
        (data["date"].dt.year >= start_year)
        & data["completed"].to_numpy()
        & (data["w_n"] >= min_matches)
        & (data["l_n"] >= min_matches)
    )
    sub = data[mask]
    print(f"Backtest window: {start_year}+  |  {len(sub):,} completed matches"
          + (f"  (both players >= {min_matches} career matches)" if min_matches else ""))

    results = {}
    for label, col in [("Elo overall", "p_overall"),
                       ("Elo surface", "p_surface"),
                       ("Elo blended", "p_blend")]:
        results[label] = score(sub[col].to_numpy())
    # ranking baseline (only where both ranks exist)
    rb = _rank_baseline_p(sub)
    valid = np.isfinite(rb)
    results["Rank points"] = score(rb[valid])

    print(f"\n{'model':<14}{'n':>8}{'acc':>9}{'logloss':>10}{'brier':>9}")
    for k, v in results.items():
        print(f"{k:<14}{v['n']:>8,}{v['acc']:>9.3f}{v['logloss']:>10.4f}{v['brier']:>9.4f}")

    print("\nLiterature anchors:  Weighted Elo ~0.664 acc / 0.212 brier ;"
          "  bookmaker ~0.690 / 0.196")

    # Calibration of the blended model (randomized A/B orientation).
    winner_first = (np.arange(len(sub)) % 2 == 0)  # deterministic 50/50 split
    p_a, lab = winner_oriented(sub["p_blend"].to_numpy(), winner_first)
    print("\nCalibration (Elo blended):")
    print(calibration_table(p_a, lab).to_string(index=False))
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=BACKTEST_START_YEAR)
    ap.add_argument("--tour", default="atp", choices=["atp", "wta"])
    ap.add_argument("--min-matches", type=int, default=0,
                    help="restrict to matches where both players have >= N career matches")
    args = ap.parse_args()
    run_backtest(start_year=args.start, min_matches=args.min_matches, tour=args.tour)
