"""Regression tests for eval/compare market scorecard — fully synthetic, no odds files.

Runnable directly (`python tests/test_compare.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
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


def _synthetic_market(n_tune: int = 900, n_val: int = 700, seed: int = 3):
    """Winner-oriented OOS + odds where model and market are noisy reads of the
    same true probability — the stacker has a real (if boring) blend to find."""
    rng = np.random.default_rng(seed)
    n = n_tune + n_val
    years = np.concatenate([2015 + np.arange(n_tune) % 5, 2020 + np.arange(n_val) % 5])
    q = rng.uniform(0.55, 0.90, n)                       # P(player A) pre-match
    a_won = rng.random(n) < q
    p_true = np.where(a_won, q, 1 - q)                   # P(recorded winner)
    clip = lambda p: np.clip(p, 0.02, 0.98)
    model = clip(p_true + rng.normal(0, 0.05, n))
    mkt_w = clip(p_true + rng.normal(0, 0.03, n))
    oos = pd.DataFrame({
        "year": years,
        "date": pd.to_datetime([f"{y}-06-01" for y in years]) + pd.to_timedelta(np.arange(n) % 20, unit="D"),
        "winner_name": [f"Alfa {i}" for i in range(n)],
        "loser_name": [f"Zulu {i}" for i in range(n)],
        "p_combiner": model,
    })
    odds = pd.DataFrame({
        "date": oos["date"],
        "w_key": oos["winner_name"].map(compare.normalize_name),
        "l_key": oos["loser_name"].map(compare.normalize_name),
        "odds_w_ps": 1.0 / (mkt_w + 0.02),               # ~4% overround
        "odds_l_ps": 1.0 / (1 - mkt_w + 0.02),
    })
    return oos, odds


def test_stacker_is_val_only_and_sane():
    """The stack block must fit on tune years only, score on validation years, and
    not be worse than the better of its two inputs by more than noise."""
    orig = compare.load_odds
    try:
        oos, odds = _synthetic_market()
        compare.load_odds = lambda tour, years=None: odds
        sc = compare.scorecard_from_oos("atp", oos)
    finally:
        compare.load_odds = orig
    st = sc["stack"]
    assert st["fit"]["nTune"] == 900 and st["fit"]["nVal"] == 700
    best_input = min(st["val"]["model"]["brier"], st["val"]["market"]["brier"])
    assert st["val"]["stack"]["brier"] <= best_input + 0.005
    for k in ("flatModel", "flatStack", "kellyModel", "kellyStack"):
        assert "roi" in st["bettingVal"][k] and "nBets" in st["bettingVal"][k]
    print("ok test_stacker_is_val_only_and_sane")


def test_stacker_skipped_when_thin():
    """Three matched rows (the classic fixture) must not grow a stack block."""
    orig = compare.load_odds
    try:
        oos = _oos()
        compare.load_odds = lambda tour, years=None: _odds(oos)
        sc = compare.scorecard_from_oos("atp", oos)
    finally:
        compare.load_odds = orig
    assert "stack" not in sc
    print("ok test_stacker_skipped_when_thin")


if __name__ == "__main__":
    test_scorecard_roi_is_scalar()
    test_scorecard_no_matches_note()
    test_stacker_is_val_only_and_sane()
    test_stacker_skipped_when_thin()
    print("\nALL PASSED")
