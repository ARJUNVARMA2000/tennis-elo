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
from tennis_model.model.features import (
    ANTISYM,
    FEATURES,
    SYMMETRIC,
    FeatureParams,
    dual_state_gate_mask,
    make_oriented_xy,
    run_context,
    select_dual_state_features,
    use_lower_state,
)


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
        "winner_rank": 12.0, "loser_rank": 71.0,
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
        "tourney_name": "Roland Garros", "winner_ioc": "FRA", "loser_ioc": "USA",
    }
    r1 = dict(r0)
    for w, l in (("w_elo", "l_elo"), ("w_selo", "l_selo"),
                 ("winner_rank_points", "loser_rank_points"), ("w_n", "l_n"),
                 ("winner_rank", "loser_rank"),
                 ("winner_age", "loser_age"), ("winner_ht", "loser_ht"),
                 ("winner_hand", "loser_hand"), ("w_days_since", "l_days_since"),
                 ("w_fat", "l_fat"), ("w_h2h", "l_h2h"), ("w_form90", "l_form90"),
                 ("w_wr10", "l_wr10"), ("w_h2h_s", "l_h2h_s"),
                 ("winner_entry", "loser_entry"), ("w_srv_pts", "l_srv_pts"),
                 ("winner_name", "loser_name"), ("winner_ioc", "loser_ioc")):
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
    assert a["winner_rank"] == 12 and a["loser_rank"] == 71
    assert b["winner_rank"] == 71 and b["loser_rank"] == 12
    assert a["winner_state_matches"] == 210 and a["loser_state_matches"] == 145
    assert b["winner_state_matches"] == 145 and b["loser_state_matches"] == 210
    print("ok test_assemble_orientation_contract")


def _dual_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    n = 3
    base = pd.DataFrame({c: np.arange(n, dtype=float) + i
                         for i, c in enumerate(FEATURES)})
    base["p_blend"] = [0.51, 0.52, 0.53]
    base["p_point"] = [0.54, 0.55, 0.56]
    base["date"] = pd.date_range("2024-01-01", periods=n)
    base["year"] = 2024
    base["completed"] = True
    base["winner_name"] = ["A", "B", "C"]
    base["loser_name"] = ["D", "E", "F"]
    base["winner_rank"] = [10, 20, 30]
    base["loser_rank"] = [40, 50, 60]
    base["draw_level"] = "main"
    base["winner_state_matches"] = [0, 16, 100]
    base["loser_state_matches"] = [200, 16, 15]
    enriched = base.copy()
    enriched.loc[:, FEATURES] = enriched.loc[:, FEATURES] + 1000.0
    enriched["round_order"] = base["round_order"]  # match identity, never state-derived
    enriched[["p_blend", "p_point"]] += 0.1
    enriched[["winner_state_matches", "loser_state_matches"]] += 50
    return base, enriched


def test_dual_state_gate_selects_complete_bundle_at_strict_boundary():
    base, enriched = _dual_frames()
    out = select_dual_state_features(base, enriched, threshold=16)
    assert list(out["uses_lower_state"]) == [True, False, True]
    state_columns = FEATURES + ["p_blend", "p_point"]
    assert np.array_equal(out.loc[[0, 2], state_columns].to_numpy(),
                          enriched.loc[[0, 2], state_columns].to_numpy())
    assert np.array_equal(out.loc[[1], state_columns].to_numpy(),
                          base.loc[[1], state_columns].to_numpy())
    # Row identity, audit ranks and MAIN-only gate counts always remain baseline-owned.
    for column in ("date", "winner_name", "loser_name", "winner_rank", "loser_rank",
                   "winner_state_matches", "loser_state_matches"):
        assert out[column].equals(base[column]), column


def test_dual_state_gate_is_orientation_safe_and_handles_unseen_players():
    assert use_lower_state(7, 200, 8)
    assert use_lower_state(200, 7, 8)
    assert not use_lower_state(8, 200, 8)  # threshold is strict: sufficient at 8
    assert use_lower_state(np.nan, 200, 8)
    assert not use_lower_state(0, 0, None)
    base, _ = _dual_frames()
    assert not dual_state_gate_mask(base, None).any()


def test_dual_state_gate_rejects_row_identity_drift():
    base, enriched = _dual_frames()
    enriched.loc[1, "loser_name"] = "Wrong Player"
    try:
        select_dual_state_features(base, enriched, threshold=16)
        raise AssertionError("expected dual-state identity mismatch")
    except ValueError as exc:
        assert "loser_name" in str(exc)


def test_assemble_respects_feature_params():
    """Non-default layoff/peak-age params must change the assembled features — the
    guard that FeatureParams actually threads through (not silently ignored)."""
    d = _joined_frame()          # w_days_since=7, l_days_since=21; ages 24.5 / 29.0
    orig = features.build_profiles
    try:
        features.build_profiles = lambda tour: {}
        base = features._assemble(d)
        tuned = features._assemble(d, params=FeatureParams(layoff_days=10.0,
                                                           peak_age=29.0))
    finally:
        features.build_profiles = orig
    assert base["layoff_flag_diff"].iloc[0] == 0        # neither side idle > 120d
    assert tuned["layoff_flag_diff"].iloc[0] == -1      # only loser (21d) > 10d
    assert np.isclose(base["peak_age_dev_diff"].iloc[0], -0.5)   # |24.5-26.5|-|29-26.5|
    assert np.isclose(tuned["peak_age_dev_diff"].iloc[0], 4.5)   # |24.5-29|-|29-29|
    print("ok test_assemble_respects_feature_params")


def test_run_context_respects_params():
    """winrate_window and fatigue_window_days must govern the context walk."""
    day0 = pd.Timestamp("2024-01-01")
    rows = []
    for i in range(12):          # Alfa loses 6, then wins 6 (one match per day)
        w, l = ("Bravo Two", "Alfa One") if i < 6 else ("Alfa One", "Bravo Two")
        rows.append(dict(winner_name=w, loser_name=l, date=day0 + pd.Timedelta(days=i),
                         surface_b="Hard", completed=True, w_games=12, l_games=8))
    rows.append(dict(winner_name="Alfa One", loser_name="Charlie Three",
                     date=day0 + pd.Timedelta(days=12), surface_b="Hard",
                     completed=True, w_games=12, l_games=8))
    df = pd.DataFrame(rows)

    _, base = run_context(df)                            # window 10, fatigue 14d
    assert np.isclose(base["w_wr10"].iloc[-1], 0.6)      # last 10: 4 losses + 6 wins
    assert np.isclose(base["w_fat"].iloc[-1], 12 * 20)   # all 12 matches in 14d

    _, tuned = run_context(df, params=FeatureParams(winrate_window=5,
                                                    fatigue_window_days=3.0))
    assert np.isclose(tuned["w_wr10"].iloc[-1], 1.0)     # last 5 are all wins
    assert np.isclose(tuned["w_fat"].iloc[-1], 3 * 20)   # only 3 days back
    print("ok test_run_context_respects_params")


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


def test_assemble_carries_draw_level_so_the_tier_filter_still_bites():
    """`main_rows` filters on draw_level, and `_assemble` is the ONLY thing that carries
    that column from the results frame into the feature frame. Drop the carry-through and
    main_rows returns every row: no error, no failing test, and a metric that still looks
    plausible — the combiner just quietly trains on every tier. That is the 2026-07-25
    challenger contamination arriving by a second route, so pin the link itself."""
    d = _joined_frame()
    d["draw_level"] = ["main", "chall"]
    orig = features.build_profiles
    try:
        features.build_profiles = lambda tour: {}
        f = features._assemble(d)
    finally:
        features.build_profiles = orig
    assert list(f["draw_level"]) == ["main", "chall"], "draw_level lost in _assemble"
    kept = features.main_rows(f)
    assert len(kept) == 1 and list(kept["draw_level"]) == ["main"], kept


def test_main_rows_is_audible_when_it_cannot_filter():
    """The no-op path must announce itself. It is reachable only if draw_level goes
    missing, which is precisely the failure nobody would otherwise notice."""
    import contextlib
    import io
    bare = pd.DataFrame({"elo_diff": [1.0, 2.0, 3.0]})
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        out = features.main_rows(bare)
    assert len(out) == 3, "must not drop rows it cannot classify"
    assert "NO-OP" in buf.getvalue(), f"silent no-op: {buf.getvalue()!r}"
    # and the normal path stays quiet
    ok = pd.DataFrame({"draw_level": ["main", "chall"], "elo_diff": [1.0, 2.0]})
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        kept = features.main_rows(ok)
    assert len(kept) == 1 and buf2.getvalue() == ""

if __name__ == "__main__":
    test_feature_partition_sane()
    test_assemble_orientation_contract()
    test_dual_state_gate_selects_complete_bundle_at_strict_boundary()
    test_dual_state_gate_is_orientation_safe_and_handles_unseen_players()
    test_dual_state_gate_rejects_row_identity_drift()
    test_assemble_respects_feature_params()
    test_run_context_respects_params()
    test_make_oriented_xy_flip_contract()
    test_assemble_carries_draw_level_so_the_tier_filter_still_bites()
    test_main_rows_is_audible_when_it_cannot_filter()
    print("\nALL PASSED")
