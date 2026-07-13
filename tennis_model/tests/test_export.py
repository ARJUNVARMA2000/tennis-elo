"""Unit checks for the web-export serialisation seam (model/export.py).

Focus: _write must never emit non-finite floats. json.dump allows the bare tokens
NaN/Infinity by default (valid Python-JSON), but the browser's strict JSON.parse
rejects them — a single NaN in a shipped file makes the whole file fail to parse and
the page render blank (the /player and /style WTA regression). Runnable directly or
under pytest.
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.model.export as export


def _raise_nonfinite(tok):
    raise ValueError(f"non-finite token {tok!r}")


def _strict_load(text: str):
    """Parse the way a browser does — reject NaN/Infinity instead of accepting them."""
    return json.loads(text, parse_constant=_raise_nonfinite)


def test_finite_replaces_nonfinite_scalars():
    assert export._finite(math.nan) is None
    assert export._finite(math.inf) is None
    assert export._finite(-math.inf) is None
    # finite values (and non-floats) pass through untouched
    assert export._finite(0.5) == 0.5
    assert export._finite(0) == 0 and export._finite("6-4 6-3") == "6-4 6-3"
    assert export._finite(None) is None and export._finite(True) is True
    print("ok test_finite_replaces_nonfinite_scalars")


def test_finite_recurses_into_nested_containers():
    src = {"recent": [{"score": math.nan, "won": True}, {"score": "6-3", "won": False}],
           "style": {"a": 0.5, "b": float("nan")}, "history": [[1.0, math.inf]]}
    out = export._finite(src)
    assert out["recent"][0]["score"] is None and out["recent"][0]["won"] is True
    assert out["recent"][1]["score"] == "6-3"
    assert out["style"] == {"a": 0.5, "b": None}
    assert out["history"] == [[1.0, None]]
    # the sanitised structure round-trips through a strict (browser-like) parser
    assert _strict_load(json.dumps(out)) == out
    print("ok test_finite_recurses_into_nested_containers")


def test_write_output_is_browser_strict_parseable():
    """A NaN reaching _write (a scoreless match) must ship as null, not the NaN token."""
    payload = {"Sabalenka": {"recent": [{"opp": "Svitolina", "score": math.nan, "won": True}]}}
    orig = export.output_dir
    try:
        with tempfile.TemporaryDirectory() as d:
            export.output_dir = lambda tour: Path(d) / tour
            export._write("wta", "profiles.json", payload)
            text = (Path(d) / "wta" / "profiles.json").read_text(encoding="utf-8")
    finally:
        export.output_dir = orig
    assert "NaN" not in text                       # the bare invalid token is gone
    parsed = _strict_load(text)                     # and it parses under browser rules
    assert parsed["Sabalenka"]["recent"][0]["score"] is None
    print("ok test_write_output_is_browser_strict_parseable")


def _synthetic_states():
    """Minimal real state objects for build_players: two active players, tuned
    WTA-style windows (form_days=65, a 23-long results deque) so the test fails
    if the export ever reads the state's own window instead of the explicit
    display windows (90d / last-10)."""
    import numpy as np
    from tennis_model.model.features import H2HState
    from tennis_model.points.serve_return import ServeReturnState
    from tennis_model.ratings.build import RatingState
    from tennis_model.ratings.elo import EloParams

    last = np.datetime64("2026-01-01")
    elo = RatingState(
        params=EloParams(form_days=65.0),
        overall={"A": 1550.0, "B": 1500.0},
        n={"A": 100, "B": 50},
        last_played={"A": last, "B": last},
        # A: snapshot 95d old (1500) and 70d old (1530). Explicit days=90 must pick
        # the 95d one (form90 = 50); the state's own 65d window would give 20.
        _form={"A": [(np.datetime64("2025-09-28"), 1500.0),
                     (np.datetime64("2025-10-23"), 1530.0)]},
    )
    elo.last_date = last
    srv = ServeReturnState(avg=0.62, base={"Hard": 0.63, "Clay": 0.60, "Grass": 0.65})
    srv.gsw["A"] = 66.0; srv.gsp["A"] = 100.0          # nonzero global serve skill
    srv.ssw["Hard"]["A"] = 33.0; srv.ssp["Hard"]["A"] = 50.0   # nonzero Hard serve skill
    seq = deque([1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1],
                maxlen=23)                              # WTA winrate_window-sized history
    ctx = H2HState({}, {}, {"A": seq})
    meta = {"A": {"rank_points": 1000.0, "age": 25.0, "ht": 185.0, "hand": "R", "ioc": "USA"},
            "B": {}}
    return elo, srv, ctx, meta, seq


def test_build_players_enrichment_fields():
    elo, srv, ctx, meta, seq = _synthetic_states()
    rows = export.build_players(elo, srv, meta, {}, ctx=ctx)
    a = next(r for r in rows if r["name"] == "A")
    b = next(r for r in rows if r["name"] == "B")

    # height: int when known, null when not (same nullable pattern as rankPoints)
    assert a["heightCm"] == 185 and isinstance(a["heightCm"], int)
    assert b["heightCm"] is None

    # per-surface serve/return use the SURFACE accessors, not the global ones
    assert a["servePctHard"] == round(srv.base["Hard"] + srv.serve_skill("A", "Hard"), 3)
    assert a["servePctHard"] != a["servePct"]           # the Hard accumulator moved it
    assert a["returnPctClay"] == round((1.0 - srv.base["Clay"]) + srv.return_skill("A", "Clay"), 3)
    # empty accumulators degrade to the surface prior, never null
    assert b["servePctGrass"] == 0.65 and b["returnPctGrass"] == 0.35

    # form90 uses the EXPLICIT 90d window (95d-old snapshot -> +50), not the
    # state's tuned form_days=65 (which would see the 70d snapshot -> +20)
    assert a["form90"] == 50
    assert b["form90"] == 0                             # no snapshots -> neutral

    # winRate10 is the mean of the LAST 10 of the 23-long deque; untracked -> null
    assert a["winRate10"] == round(sum(list(seq)[-10:]) / 10, 3)
    assert b["winRate10"] is None

    # ctx=None (foreign pickle on the quick path) keeps the export alive
    rows_no_ctx = export.build_players(elo, srv, meta, {}, ctx=None)
    assert all(r["winRate10"] is None for r in rows_no_ctx)
    print("ok test_build_players_enrichment_fields")


def test_enrichment_propagates_to_profiles_and_parses_strict():
    import pandas as pd
    elo, srv, ctx, meta, _ = _synthetic_states()
    rows = export.build_players(elo, srv, meta, {}, ctx=ctx)
    df = pd.DataFrame(columns=["winner_name", "loser_name", "date", "surface_b",
                               "score", "tourney_name"])
    profiles = export.build_profiles_json(df, elo, srv, meta, {}, rows)
    # build_profiles_json spreads the player row -> the new fields ride along
    row_a = next(r for r in rows if r["name"] == "A")
    assert profiles["A"]["heightCm"] == 185
    assert profiles["A"]["form90"] == 50
    assert profiles["A"]["servePctClay"] == row_a["servePctClay"]
    # both artifacts survive a browser-strict JSON round-trip
    for payload in (rows, profiles):
        assert _strict_load(json.dumps(export._finite(payload)))
    print("ok test_enrichment_propagates_to_profiles_and_parses_strict")


def test_build_method_matches_accessors():
    """method.json states the EFFECTIVE production params — always equal to the
    *_params_for accessors (never literals), so a retune can't break this test."""
    from tennis_model.data.results import tier_mults
    from tennis_model.model.features import feat_params_for
    from tennis_model.model.train import effective_xgb_params
    from tennis_model.points.serve_return import sr_params_for
    from tennis_model.ratings.elo import params_for

    for tour in ("atp", "wta"):
        m = export.build_method(tour)
        assert m["tour"] == tour
        assert m["elo"]["surfaceBlend"] == params_for(tour).surface_blend
        assert m["elo"]["kScale"] == params_for(tour).k_scale
        assert m["elo"]["xsurf"] == params_for(tour).xsurf
        assert m["serveReturn"]["formHalflifeDays"] == sr_params_for(tour).form_halflife_days
        assert m["context"]["winrateWindow"] == feat_params_for(tour).winrate_window
        assert m["combiner"]["xgb"] == export._camel(effective_xgb_params(tour))
        mults, default = tier_mults(tour)
        assert m["tiers"]["kMult"] == mults and m["tiers"]["default"] == default
    print("ok test_build_method_matches_accessors")


def test_build_method_shape_and_strict_json():
    """Schema-level keys are camelCase, tuples arrive as lists, counts are coherent,
    and the payload survives a browser-strict round-trip through _finite."""
    from tennis_model.model.features import FEATURES

    def _assert_camel(d, path=""):
        for k, v in d.items():
            if path != "tiers.kMult":   # tier names are data values (grand_slam, ...)
                assert "_" not in k, f"snake_case key {k!r} at {path or 'root'}"
            if isinstance(v, dict):
                _assert_camel(v, f"{path}.{k}".lstrip("."))

    for tour in ("atp", "wta"):
        m = export.build_method(tour)
        _assert_camel(m)
        groups = m["combiner"]["featureGroups"]
        assert sum(groups.values()) == m["combiner"]["featureCount"] == len(FEATURES)
        for field in (m["tiers"]["anchors"], m["serveReturn"]["pClip"],
                      m["protocol"]["tuneYears"], m["surfaces"]):
            assert isinstance(field, list)
        parsed = _strict_load(json.dumps(export._finite(m)))
        assert parsed["elo"]["skipWalkovers"] in (True, False)   # bools survive
    print("ok test_build_method_shape_and_strict_json")


def test_build_method_atp_uses_xgb_defaults():
    """ATP carries no XGB override (its sweeps kept overfitting the tune window) —
    the exported dict must be the _xgb defaults, not a stale override."""
    from tennis_model.model.train import XGB_DEFAULTS

    m = export.build_method("atp")
    assert m["combiner"]["xgb"]["nEstimators"] == XGB_DEFAULTS["n_estimators"]
    assert m["combiner"]["xgb"]["regLambda"] == XGB_DEFAULTS["reg_lambda"]
    print("ok test_build_method_atp_uses_xgb_defaults")


def test_build_brackets_payload_splits_and_stamps():
    """The bracket is popped OUT of tournaments.json (kept small for the home page) into
    brackets.json, and every tournaments entry gets an explicit hasBracket flag."""
    rounds = [{"round": "F", "matches": [{"a": "A", "b": "B", "winner": "a"}]}]
    tournaments = [
        {"name": "With Draw", "surface": "Hard", "status": "completed", "drawSize": 2,
         "champion": "A", "runnerUp": "B", "bestOf": 3, "start": "2026-07-01",
         "end": "2026-07-02", "bracket": rounds, "bracketSize": 2, "wikiUrl": "http://x"},
        {"name": "No Draw", "status": "live", "bracket": None, "bracketSize": None,
         "wikiUrl": None},
    ]
    payload = export.build_brackets_payload(tournaments)

    # tournaments.json is stripped of the heavy bracket + stamped hasBracket
    assert "bracket" not in tournaments[0] and "bracketSize" not in tournaments[0]
    assert "wikiUrl" not in tournaments[0]
    assert tournaments[0]["hasBracket"] is True
    assert tournaments[1]["hasBracket"] is False

    # brackets.json carries exactly the one real draw, with header + rounds preserved
    assert len(payload) == 1
    b = payload[0]
    assert b["name"] == "With Draw" and b["rounds"] == rounds
    assert b["bracketSize"] == 2 and b["champion"] == "A" and b["wikiUrl"] == "http://x"
    _strict_load(json.dumps(export._finite(payload)))     # browser-strict round-trip
    print("ok test_build_brackets_payload_splits_and_stamps")


if __name__ == "__main__":
    test_finite_replaces_nonfinite_scalars()
    test_finite_recurses_into_nested_containers()
    test_write_output_is_browser_strict_parseable()
    test_build_players_enrichment_fields()
    test_enrichment_propagates_to_profiles_and_parses_strict()
    test_build_method_matches_accessors()
    test_build_method_shape_and_strict_json()
    test_build_method_atp_uses_xgb_defaults()
    test_build_brackets_payload_splits_and_stamps()
    print("\nALL PASSED")
