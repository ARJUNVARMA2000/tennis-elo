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


def test_run_elo_cross_surface_transfer():
    """xsurf=0 must reproduce today's walk exactly (no off-surface writes); xsurf>0
    moves the other surfaces by a fraction of the source-surface update."""
    from dataclasses import replace

    from tennis_model.ratings.elo import DEFAULT_PARAMS
    df = _df([("Ana", "Ben", "Clay", 4, "2026-01-05")])
    st0, _ = run_elo(df)
    assert "Ana" not in st0.surface["Hard"]                # incumbent behavior intact
    st1, _ = run_elo(df, params=replace(DEFAULT_PARAMS, xsurf=0.3))
    clay_gain = st1.surface["Clay"]["Ana"] - DEFAULT_RATING
    hard_gain = st1.surface["Hard"]["Ana"] - DEFAULT_RATING
    assert 0 < hard_gain < clay_gain
    assert abs(hard_gain - 0.3 * clay_gain) < 1e-9         # exactly xsurf x source
    assert st1.surface["Hard"]["Ben"] < DEFAULT_RATING     # loser transfers down
    assert st1.surface["Clay"]["Ana"] == st0.surface["Clay"]["Ana"]  # source unchanged
    print("ok test_run_elo_cross_surface_transfer")


def test_run_elo_adaptive_blend():
    """blend_n50=0 must reproduce the incumbent fixed blend exactly; >0 gates the
    surface weight by the player's own-surface match count (P3)."""
    from dataclasses import replace

    from tennis_model.ratings.elo import DEFAULT_PARAMS
    df = _df([
        ("Ana", "Ben", "Hard", 4, "2026-01-05"),
        ("Ana", "Ben", "Hard", 4, "2026-01-12"),
        ("Ana", "Ben", "Clay", 4, "2026-01-19"),
    ])
    _, f0 = run_elo(df)
    _, f1 = run_elo(df, params=replace(DEFAULT_PARAMS, blend_n50=0.0))
    assert (f0 == f1).all().all()                          # 0 = off = incumbent walk
    st2, f2 = run_elo(df, params=replace(DEFAULT_PARAMS, blend_n50=10.0))
    # match 1: Ana has 1 hard match -> effective blend = SURFACE_BLEND * 1/11
    exp_b = SURFACE_BLEND * 1.0 / 11.0
    exp = (1 - exp_b) * f2.loc[1, "w_elo"] + exp_b * f2.loc[1, "w_selo"]
    assert abs(f2.loc[1, "w_belo"] - exp) < 1e-9
    # prediction-time mirror: RatingState.blended applies the same gating
    ns = st2.n_surface["Hard"]["Ana"]
    b = SURFACE_BLEND * ns / (ns + 10.0)
    exp_state = (1 - b) * st2.elo("Ana") + b * st2.surface_elo("Ana", "Hard")
    assert abs(st2.blended("Ana", "Hard") - exp_state) < 1e-9
    # debutant on a surface (ns=0) leans fully on overall Elo
    assert st2.blended("Ben", "Grass") == st2.elo("Ben")
    print("ok test_run_elo_adaptive_blend")


def test_run_elo_home_advantage():
    """home_adv > 0 venue-adjusts only the UPDATE expectation (a home win moves the
    rating less); the RECORDED probabilities stay venue-free so logit_p_blend keeps
    train/inference parity. Frames without venue/ioc columns are untouched (W2c)."""
    from dataclasses import replace

    from tennis_model.ratings.elo import DEFAULT_PARAMS
    df = pd.DataFrame([{
        "winner_name": "Ana", "loser_name": "Ben", "surface_b": "Hard",
        "tier_k": 1.0, "game_diff": 4, "completed": True,
        "date": pd.Timestamp("2026-01-05"),
        "tourney_name": "Roland Garros", "winner_ioc": "FRA", "loser_ioc": "USA",
    }])
    st0, f0 = run_elo(df)
    st1, f1 = run_elo(df, params=replace(DEFAULT_PARAMS, home_adv=50.0))
    assert (f0 == f1).all().all()                          # recorded features venue-free
    assert st1.overall["Ana"] < st0.overall["Ana"]         # home win moves less
    assert st1.overall["Ben"] > st0.overall["Ben"]         # away loss punished less
    # ioc-less frames (e.g. synthetic tests) are untouched even with home_adv on
    df2 = _df([("Ana", "Ben", "Hard", 4, "2026-01-05")])
    _, g0 = run_elo(df2)
    _, g1 = run_elo(df2, params=replace(DEFAULT_PARAMS, home_adv=50.0))
    assert (g0 == g1).all().all()
    print("ok test_run_elo_home_advantage")


if __name__ == "__main__":
    test_expected_score()
    test_dynamic_k_monotone()
    test_mov_multiplier()
    test_run_elo_updates_and_seeding()
    test_run_elo_no_leakage()
    test_run_elo_cross_surface_transfer()
    test_run_elo_adaptive_blend()
    test_run_elo_home_advantage()
    print("\nALL PASSED")
