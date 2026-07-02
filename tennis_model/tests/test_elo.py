"""Unit checks for ratings/elo + ratings/build — fully synthetic (no data, no network).

Runnable directly (`python tests/test_elo.py`) or under pytest. Covers the core Elo
math (expected score, dynamic K, margin-of-victory multiplier) and the chronological
rating builder: winner/loser updates, surface seeding on debut, the overall/surface
blend, and leakage-freedom of the recorded pre-match probabilities.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.config import DEFAULT_RATING, MOV_CAP, RATING_SCALE, SURFACE_BLEND
from tennis_model.ratings.build import run_elo
from tennis_model.ratings.elo import dynamic_k, expected_score, mov_multiplier, surface_k


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _df(rows):
    """rows: list of (winner, loser, surface, game_diff, date) — the exact columns
    run_elo reads (tier_k fixed at 1.0, all matches completed)."""
    return pd.DataFrame([
        {"winner_name": w, "loser_name": l, "surface_b": s, "tier_k": 1.0,
         "game_diff": gd, "completed": True, "date": pd.Timestamp(d)}
        for (w, l, s, gd, d) in rows
    ])


# ---------------------------------------------------------------------------
# core math
# ---------------------------------------------------------------------------
def test_expected_score():
    # symmetry: E(a,b) + E(b,a) == 1
    for ra, rb in [(1500, 1500), (1700, 1450), (2000, 1500), (1400, 1900)]:
        assert abs(expected_score(ra, rb) + expected_score(rb, ra) - 1.0) < 1e-12, (ra, rb)
    # equal ratings -> even money
    assert abs(expected_score(1500, 1500) - 0.5) < 1e-12
    # a full RATING_SCALE gap -> 10:1 odds = 10/11
    assert abs(expected_score(1500 + RATING_SCALE, 1500) - 10.0 / 11.0) < 1e-12
    print("ok test_expected_score")


def test_dynamic_k_monotone():
    ns = (0, 1, 5, 20, 100, 500)
    ks = [dynamic_k(n) for n in ns]
    sks = [surface_k(n) for n in ns]
    # rookies move fast, veterans settle: K strictly decreasing in match count
    assert all(a > b for a, b in zip(ks, ks[1:])), ks
    assert all(a > b for a, b in zip(sks, sks[1:])), sks
    assert all(k > 0 for k in ks + sks)
    print("ok test_dynamic_k_monotone")


def test_mov_multiplier():
    vals = [mov_multiplier(g) for g in range(0, 15)]
    assert vals[0] == 1.0                                      # dead-even margin
    assert all(b >= a for a, b in zip(vals, vals[1:])), vals   # non-decreasing
    below = [v for v in vals if v < MOV_CAP]
    assert all(b > a for a, b in zip(below, below[1:])), below  # strictly up until cap
    assert mov_multiplier(1000) == MOV_CAP                     # blowouts capped
    assert mov_multiplier(-4) == mov_multiplier(4)             # sign-insensitive
    print("ok test_mov_multiplier")


# ---------------------------------------------------------------------------
# rating builder
# ---------------------------------------------------------------------------
def test_run_elo_updates_and_seeding():
    df = _df([
        ("Ana", "Ben", "Hard", 4, "2026-01-05"),
        ("Ana", "Cai", "Clay", 3, "2026-01-12"),
    ])
    st, feats = run_elo(df)
    # winner gains, loser drops
    assert st.overall["Ana"] > DEFAULT_RATING > st.overall["Ben"], st.overall
    # two debutants: pre-match ratings at default, even-money call
    assert feats.loc[0, "w_elo"] == DEFAULT_RATING == feats.loc[0, "l_elo"]
    assert feats.loc[0, "p_blend"] == 0.5
    # surface seeding: Ana's Clay debut starts from her CURRENT overall, not 1500
    assert feats.loc[1, "w_selo"] == feats.loc[1, "w_elo"]
    assert feats.loc[1, "w_selo"] > DEFAULT_RATING
    assert st.surface["Clay"]["Ana"] > DEFAULT_RATING
    # blended rating equals the configured overall/surface mix, on every row
    for side in ("w", "l"):
        exp = (1 - SURFACE_BLEND) * feats[f"{side}_elo"] + SURFACE_BLEND * feats[f"{side}_selo"]
        assert (feats[f"{side}_belo"] - exp).abs().max() < 1e-9
    # elo_diff derived from blended ratings
    assert (feats["elo_diff"] - (feats["w_belo"] - feats["l_belo"])).abs().max() < 1e-12
    print("ok test_run_elo_updates_and_seeding")


def test_run_elo_no_leakage():
    df = _df([
        ("Ana", "Ben", "Hard", 4, "2026-01-05"),
        ("Ana", "Ben", "Hard", 4, "2026-01-19"),
    ])
    st, feats = run_elo(df)
    p1, p2 = feats["p_blend"].tolist()
    # row 0 is recorded BEFORE anything is known — exactly even, despite the fact
    # that Ana wins both matches (i.e. the future result did not leak in)
    assert p1 == 0.5, p1
    # row 1 reflects only the first result: prob moved in the winner's direction
    assert p2 > p1, (p1, p2)
    # recorded pre-match rating on row 1 is below Ana's final (post-row-1) rating
    assert st.overall["Ana"] > feats.loc[1, "w_elo"] > DEFAULT_RATING
    print("ok test_run_elo_no_leakage")


if __name__ == "__main__":
    test_expected_score()
    test_dynamic_k_monotone()
    test_mov_multiplier()
    test_run_elo_updates_and_seeding()
    test_run_elo_no_leakage()
    print("\nALL PASSED")
