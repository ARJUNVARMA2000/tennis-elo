"""Feature-contract property tests for model/features.py — fully synthetic.

Runnable directly (`python tests/test_features.py`) or under pytest. These pin the
orientation contract the whole training pipeline rests on: swapping the two players
must negate every ANTISYM feature and leave every SYMMETRIC feature unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.model.features as features
from tennis_model.model.features import ANTISYM, FEATURES, SYMMETRIC, make_oriented_xy


def test_feature_partition_sane():
    assert set(ANTISYM) & set(SYMMETRIC) == set()
    assert list(FEATURES) == list(ANTISYM) + list(SYMMETRIC)
    assert len(FEATURES) == len(set(FEATURES))
    print("ok test_feature_partition_sane")


def _joined_frame() -> pd.DataFrame:
    """Two rows: row 1 is row 0 with the players' slots swapped. Every column
    _assemble reads is present; pair-level walk outputs are transformed per their
    orientation semantics (diffs negate, probabilities complement)."""
    r0 = {
        "elo_diff": 42.0, "w_elo": 1650.0, "l_elo": 1580.0, "w_selo": 1700.0,
        "l_selo": 1560.0, "p_blend": 0.62, "p_point": 0.58,
        "serve_skill_diff": 0.013, "return_skill_diff": -0.007,
        "winner_rank_points": 3200.0, "loser_rank_points": 900.0,
        "w_n": 210, "l_n": 145, "winner_age": 24.5, "loser_age": 29.0,
        "winner_ht": 185.0, "loser_ht": 191.0, "winner_hand": "R", "loser_hand": "L",
        "w_days_since": 7.0, "l_days_since": 21.0, "w_fat": 3.0, "l_fat": 1.0,
        "w_h2h": 4, "l_h2h": 2, "w_form90": 0.10, "l_form90": -0.05,
        "w_wr10": 0.7, "l_wr10": 0.5, "w_h2h_s": 2, "l_h2h_s": 1,
        "winner_entry": "Q", "loser_entry": None,
        "best_of": 3, "is_indoor": False, "tier_k": 1.05, "round_order": 4,
        "surface_b": "Clay", "w_srv_pts": 900.0, "l_srv_pts": 750.0,
        "date": pd.Timestamp("2024-06-01"), "completed": True,
        "winner_name": "Alfa One", "loser_name": "Bravo Two", "tour": "atp",
    }
    r1 = dict(r0)
    for w, l in (("w_elo", "l_elo"), ("w_selo", "l_selo"),
                 ("winner_rank_points", "loser_rank_points"), ("w_n", "l_n"),
                 ("winner_age", "loser_age"), ("winner_ht", "loser_ht"),
                 ("winner_hand", "loser_hand"), ("w_days_since", "l_days_since"),
                 ("w_fat", "l_fat"), ("w_h2h", "l_h2h"), ("w_form90", "l_form90"),
                 ("w_wr10", "l_wr10"), ("w_h2h_s", "l_h2h_s"),
                 ("winner_entry", "loser_entry"), ("w_srv_pts", "l_srv_pts"),
                 ("winner_name", "loser_name")):
        r1[w], r1[l] = r0[l], r0[w]
    r1["elo_diff"] = -r0["elo_diff"]
    r1["serve_skill_diff"] = -r0["serve_skill_diff"]
    r1["return_skill_diff"] = -r0["return_skill_diff"]
    r1["p_blend"] = 1.0 - r0["p_blend"]
    r1["p_point"] = 1.0 - r0["p_point"]
    return pd.DataFrame([r0, r1])


def test_assemble_orientation_contract():
    """Player-swap must negate every ANTISYM output and fix every SYMMETRIC one —
    the test that catches 'added to ANTISYM but not actually anti-symmetric'."""
    orig = features.build_profiles
    try:
        features.build_profiles = lambda tour: {}       # style diffs -> 0, has_style -> 0
        f = features._assemble(_joined_frame())
    finally:
        features.build_profiles = orig
    a, b = f.iloc[0], f.iloc[1]
    for c in ANTISYM:
        assert np.isclose(a[c], -b[c], atol=1e-9), (c, a[c], b[c])
    for c in SYMMETRIC:
        assert np.isclose(a[c], b[c], atol=1e-9), (c, a[c], b[c])
    assert a["has_style"] == 0 and a["style_net_diff"] == 0.0
    print("ok test_assemble_orientation_contract")


def test_make_oriented_xy_flip_contract():
    rng = np.random.default_rng(11)
    n = 400
    feat = pd.DataFrame({c: rng.normal(size=n) for c in ANTISYM})
    for c in SYMMETRIC:
        feat[c] = rng.uniform(0, 1, n)
    X, y = make_oriented_xy(feat, seed=5)
    assert list(X.columns) == list(FEATURES)
    flip = np.random.default_rng(5).random(n) < 0.5     # reproduce the internal mask
    assert np.array_equal(y, np.where(flip, 0, 1))
    for c in ANTISYM:
        assert np.allclose(X[c].to_numpy()[flip], -feat[c].to_numpy()[flip])
        assert np.allclose(X[c].to_numpy()[~flip], feat[c].to_numpy()[~flip])
    for c in SYMMETRIC:
        assert np.allclose(X[c].to_numpy(), feat[c].to_numpy())
    # same seed -> bit-identical (training reproducibility)
    X2, y2 = make_oriented_xy(feat, seed=5)
    assert X.equals(X2) and np.array_equal(y, y2)
    print("ok test_make_oriented_xy_flip_contract")


if __name__ == "__main__":
    test_feature_partition_sane()
    test_assemble_orientation_contract()
    test_make_oriented_xy_flip_contract()
    print("\nALL PASSED")
