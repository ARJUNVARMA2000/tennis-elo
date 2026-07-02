"""Regression tests for eval/compare market scorecard — fully synthetic, no odds files.

Runnable directly (`python tests/test_compare.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.eval.compare as compare


def _oos() -> pd.DataFrame:
    return pd.DataFrame({
        "year": [2024, 2024, 2024],
        "date": pd.to_datetime(["2024-06-01", "2024-06-02", "2024-06-03"]),
        "winner_name": ["Alfa One", "Bravo Two", "Charlie Three"],
        "loser_name": ["Xray Nine", "Yankee Eight", "Zulu Seven"],
        "p_combiner": [0.80, 0.30, 0.55],
    })


def _odds(oos: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "date": oos["date"],
        "w_key": oos["winner_name"].map(compare.normalize_name),
        "l_key": oos["loser_name"].map(compare.normalize_name),
        "odds_w_ps": [1.60, 2.50, 1.90],
        "odds_l_ps": [2.40, 1.55, 1.90],
    })


def test_scorecard_roi_is_scalar():
    """Edge bets on both sides must yield a scalar ROI (regression: the pnl reduction
    once broadcast back to an ndarray and market.json was silently never written)."""
    orig = compare.load_odds
    try:
        oos = _oos()
        compare.load_odds = lambda tour, years=None: _odds(oos)
        sc = compare.scorecard_from_oos("atp", oos, edge_min=0.05)
    finally:
        compare.load_odds = orig
    assert sc["matched"] == 3
    assert sc["betting"]["nBets"] >= 1
    assert isinstance(sc["betting"]["roi"], float)
    assert "brier" in sc["model"] and "brier" in sc["market"]
    print("ok test_scorecard_roi_is_scalar")


def test_scorecard_no_matches_note():
    orig = compare.load_odds
    try:
        oos = _oos()
        odds = _odds(oos)
        odds["w_key"] = "nobody at all"                 # kill the join
        compare.load_odds = lambda tour, years=None: odds
        sc = compare.scorecard_from_oos("atp", oos)
    finally:
        compare.load_odds = orig
    assert sc["matched"] == 0 and "note" in sc
    print("ok test_scorecard_no_matches_note")


if __name__ == "__main__":
    test_scorecard_roi_is_scalar()
    test_scorecard_no_matches_note()
    print("\nALL PASSED")
