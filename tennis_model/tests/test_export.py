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

import pandas as pd

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


def test_matrix_shards_use_compact_strict_json(monkeypatch, tmp_path):
    monkeypatch.setattr(export, "output_dir", lambda tour: tmp_path / tour)
    export._write_shards("atp", "matrix", {"matrix-hard-bo3.json": {
        "players": ["A", "B"], "components": {"combiner": [[0.5, 0.6], [0.4, 0.5]]},
    }})
    text = (tmp_path / "atp" / "matrix-hard-bo3.json").read_text(encoding="utf-8")
    assert "\n" not in text
    assert _strict_load(text)["components"]["combiner"][0][1] == 0.6


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
    # A quick run reloads profile-index.json, where sanitised missing values are None
    # rather than pandas NaN. Both representations must remain nullable, never crash.
    rows_cached = export.build_players(
        elo, srv, meta,
        {export.name_key("A"): {"style_aggression": None, "style_serve_dom": None}},
        ctx=ctx,
    )
    cached_a = next(r for r in rows_cached if r["name"] == "A")
    assert cached_a["aggression"] is None and cached_a["serveDom"] is None
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
    from tennis_model.config import WTA_DUAL_STATE_GATE_THRESHOLD
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
        assert m["stateGate"]["enabled"] == (tour == "wta")
        assert m["stateGate"]["minMainMatches"] == (
            WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None)
        assert m["stateGate"]["trainingPopulation"] == "main-only"
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
         "espnId": "123-2026",
         "champion": "A", "runnerUp": "B", "bestOf": 3, "start": "2026-07-01",
         "end": "2026-07-02", "bracket": rounds, "bracketSize": 2,
         "drawSource": "atp", "drawSourceId": "123",
         "drawSourceUrl": "https://www.protennislive.com/x"},
        {"name": "No Draw", "status": "live", "bracket": None, "bracketSize": None,
         "drawSource": None, "drawSourceId": None, "drawSourceUrl": None},
    ]
    payload = export.build_brackets_payload(tournaments)

    # tournaments.json is stripped of the heavy bracket + stamped hasBracket
    assert "bracket" not in tournaments[0] and "bracketSize" not in tournaments[0]
    assert "drawSourceUrl" not in tournaments[0]
    assert tournaments[0]["hasBracket"] is True
    assert tournaments[1]["hasBracket"] is False

    # brackets.json carries exactly the one real draw, with header + rounds preserved
    assert len(payload) == 1
    b = payload[0]
    assert b["name"] == "With Draw" and b["rounds"] == rounds
    assert b["bracketSize"] == 2 and b["champion"] == "A"
    assert b["espnId"] == "123-2026"
    assert b["drawSource"] == "atp" and b["drawSourceId"] == "123"
    _strict_load(json.dumps(export._finite(payload)))     # browser-strict round-trip
    print("ok test_build_brackets_payload_splits_and_stamps")


def test_build_meta_separates_build_time_from_model_time():
    """`lastUpdated` is when this JSON was written; `modelTrainedAt` is when the predictor
    was trained. The hourly quick refresh rewrites the first while reusing the pickle
    behind the second — so only their divergence can reveal a dead daily retrain."""
    df = pd.DataFrame({"tour": ["atp"], "date": [pd.Timestamp("2026-07-24")],
                       "winner_name": ["A"], "loser_name": ["B"],
                       "has_stats": [True], "completed": [True], "surface_b": ["Hard"]})
    trained = "2026-07-04T04:31:07Z"
    meta = export.build_meta(df, players=[], accuracy=None, trained_at=trained,
                             model_population_version=export.MATCH_POPULATION_VERSION)
    assert meta["modelTrainedAt"] == trained
    assert meta["modelPopulationVersion"] == export.MATCH_POPULATION_VERSION
    assert meta["dualStateThreshold"] is None and meta["dualStateReady"] is False
    assert meta["lastUpdated"] != trained and meta["lastUpdated"].endswith("Z")
    # a pickle predating the stamp must export null, not crash or fake a fresh time
    assert export.build_meta(df, players=[], accuracy=None)["modelTrainedAt"] is None
    _strict_load(json.dumps(export._finite(meta)))
    print("ok test_build_meta_separates_build_time_from_model_time")


def test_build_meta_audits_wta_125_policy_rows():
    df = pd.DataFrame({"tour": ["wta", "wta"],
                       "date": [pd.Timestamp("2026-07-24")] * 2,
                       "winner_name": ["A", "C"], "loser_name": ["B", "D"],
                       "tourney_level": ["WTA250", "WTA125"],
                       "has_stats": [True, False], "completed": [True, True],
                       "surface_b": ["Hard", "Clay"]})
    df.attrs["excluded_wta125_matches"] = 31
    df.attrs["excluded_unclassified_wta_live_matches"] = 2
    meta = export.build_meta(df, players=[], accuracy=None)
    assert meta["wta125Matches"] == 1
    assert meta["excludedWta125Matches"] == 31
    assert meta["excludedUnclassifiedWtaLiveMatches"] == 2
    print("ok test_build_meta_audits_wta_125_policy_rows")


def test_build_event_outputs_uses_event_view_for_coverage_and_cards(monkeypatch):
    """The model frame intentionally excludes WTA 125s, but tournament lifecycle and
    coverage must consume the event-facing view that restores their factual live results."""
    from tennis_model.sim import tournaments

    from tennis_model.data import event_coverage, results

    model_frame, event_frame = object(), object()
    cards = [{"name": "Completed 125"}]
    manifest = {"events": [{"key": "espn:1-2026"}]}
    seen = []
    monkeypatch.setattr(
        results, "event_match_view",
        lambda df, tour: seen.append(("view", df, tour)) or event_frame,
    )
    monkeypatch.setattr(
        event_coverage, "build_event_coverage",
        lambda df, tour: seen.append(("coverage", df, tour)) or manifest,
    )
    monkeypatch.setattr(
        tournaments, "build_tournaments",
        lambda predictor, df, tour: seen.append(("cards", predictor, df, tour)) or cards,
    )
    monkeypatch.setattr(
        event_coverage, "finalize_event_coverage",
        lambda got, ts: seen.append(("finalize", got, ts)) or {**got, "finalized": True},
    )

    predictor = object()
    got_manifest, got_cards = export.build_event_outputs(
        predictor, model_frame, "wta")

    assert got_manifest == {**manifest, "finalized": True}
    assert got_cards is cards
    assert seen == [
        ("view", model_frame, "wta"),
        ("coverage", event_frame, "wta"),
        ("cards", predictor, event_frame, "wta"),
        ("finalize", manifest, cards),
    ]


def test_predictor_stamps_trained_at_and_survives_a_pickle_round_trip():
    """The stamp is derived in the constructor (not at the two call sites, which have
    forgotten a constructor arg before) and rides INSIDE the pickle — a file mtime would
    be laundered by the CI cache restore that hands the quick run its predictor."""
    import pickle

    from tennis_model.model.predict import TennisPredictor

    p = TennisPredictor(clf=None, iso=None, elo=None, srv=None, ctx=None, meta={}, tour="wta")
    assert p.trained_at and p.trained_at.endswith("Z")
    restored = pickle.loads(pickle.dumps(p))
    assert restored.trained_at == p.trained_at
    assert restored._match_population_version == export.MATCH_POPULATION_VERSION

    # a pickle from before the stamp existed degrades to None, never raises
    old = TennisPredictor(clf=None, iso=None, elo=None, srv=None, ctx=None, meta={}, tour="wta")
    del old.trained_at
    assert old._trained_at is None
    del old.match_population_version
    assert old._match_population_version is None
    assert getattr(old, "trained_at", None) is None      # the accessor export_all uses
    print("ok test_predictor_stamps_trained_at_and_survives_a_pickle_round_trip")


def test_fixtures_upset_flag_agrees_with_the_rounded_prob_it_ships():
    """The flag must be derived from the prob that ships, not from full-precision p.

    A winner priced .4996 rounds to modelProb .500; a flag taken off the raw p says
    "upset" while the shipped number says even money. That contradiction blocked every
    scheduled deploy on 2026-07-27 — the gate can only re-derive the flag from the file.
    """
    import pandas as pd

    # probs straddling the rounding boundary, including the exact .4995/.4996 hinge
    probs = deque([0.4996, 0.49951, 0.4995, 0.4994, 0.5, 0.50049, 0.8, 0.2])

    class _Stub:
        def win_prob(self, w, l, surface=None, best_of=3, event=None):
            return probs.popleft()

    n = 8
    df = pd.DataFrame({
        "completed": [True] * n,
        "date": pd.date_range("2026-07-01", periods=n),
        "tourney_name": ["Umag"] * n,
        "espn_id": [f"439-{i}" for i in range(n)],
        "surface_b": ["Clay"] * n,
        "round": ["R32"] * n,
        "winner_name": [f"W{i}" for i in range(n)],
        "loser_name": [f"L{i}" for i in range(n)],
        "score": ["6-4 6-4"] * n,
        "best_of": [3] * n,
    })

    out = export.build_fixtures(df, _Stub(), n=n)
    assert len(out) == n
    assert [f["espnId"] for f in out] == [f"439-{i}" for i in reversed(range(n))]
    for f in out:
        mp = f["modelProb"]
        # the exact predicate health.output_problems re-derives the flag with
        assert f["upset"] == (mp < 0.5), f"flag {f['upset']} contradicts modelProb {mp}"
    # and specifically: the value that shipped as 0.5 is not badged an upset
    assert any(f["modelProb"] == 0.5 for f in out)
    assert all(f["upset"] is False for f in out if f["modelProb"] == 0.5)
    print("ok test_fixtures_upset_flag_agrees_with_the_rounded_prob_it_ships")


def test_build_upcoming_preserves_stable_event_id(monkeypatch):
    """The tournament card join must survive sponsor/city display-name differences."""
    import pandas as pd
    from tennis_model.model import upcoming

    enriched = [{
        "event": "National Bank Open presented by Rogers",
        "date": "2026-08-03",
        "round": "R64",
        "surface": "Hard",
        "best_of": 3,
        "level": "ATP 1000",
        "playerA": "A",
        "playerB": "B",
        "pA": 0.61234,
        "espnId": "421-2026",
    }]
    monkeypatch.setattr(upcoming, "load_upcoming", lambda tour: pd.DataFrame())
    monkeypatch.setattr(upcoming, "enrich_upcoming", lambda *args: enriched)

    rows = export.build_upcoming(object(), pd.DataFrame(), "atp")
    assert rows[0]["event"] == "Montreal"   # ATP 421-2026 is the Montreal edition
    assert rows[0]["espnId"] == "421-2026"


def test_upcoming_v2_shards_round_trip_without_heavy_index_payload():
    rows = []
    for i in range(7):
        rows.append({
            "event": "Test Open", "espnId": "421-2026", "date": "2026-08-03",
            "round": "R64", "surface": "Hard", "bestOf": 3, "level": "ATP 1000",
            "playerA": f"A{i}", "playerB": f"B{i}", "pA": 0.55,
            "components": {"eloBlend": 0.54, "pointModel": 0.56, "combiner": 0.55},
            "evidence": {"schema": "evidence-v1", "signals": [{"large": "x" * 500}]},
            "forecast": {"first": 0.5, "current": 0.55, "delta": 0.05,
                         "snapshots": 1, "timeline": [{"p": 0.55, "large": "y" * 500}]},
            "watch": {"schema": "watch-v1", "score": 90 - i, "weights": {},
                      "factors": {}, "coverage": 1.0},
            "watchRank": i + 1,
        })
    index, shards = export.build_upcoming_shards(rows, "generation-1")

    assert index["schema"] == "upcoming-v2" and index["count"] == len(rows)
    assert len(index["events"]) == 1
    assert len(index["highlights"]) == 5  # next three union top five watch candidates
    assert all(not any(key in row for key in ("components", "evidence", "forecast"))
               for row in index["highlights"])
    ref = index["events"][0]
    event_rows = shards[ref["file"]]["matches"]
    details = {row["matchId"]: row for row in shards[ref["evidenceFile"]]["details"]}
    rebuilt = [{**row, **{key: details[row["matchId"]][key]
                          for key in ("components", "evidence", "forecast")}}
               for row in event_rows]
    assert [{key: row[key] for key in rows[0]} for row in rebuilt] == rows
    assert len(json.dumps(index)) < len(json.dumps(rows)) * 0.2


def test_post_tracking_export_builds_upcoming_once_and_replaces_legacy(monkeypatch, tmp_path):
    calls = []
    out = tmp_path / "atp"
    out.mkdir(parents=True)
    (out / "upcoming.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(export, "output_dir", lambda tour: out)
    monkeypatch.setattr(
        export, "build_upcoming",
        lambda predictor, df, tour, enriched=None: calls.append(enriched) or [],
    )

    enriched = [{"already": "priced"}]
    export.export_forecast_products("atp", object(), pd.DataFrame(), enriched=enriched)
    assert calls == [enriched]
    assert (out / "upcoming-index.json").exists()
    assert not (out / "upcoming.json").exists()


def test_matrix_and_profile_exports_are_generation_aware_shards():
    """Indexes stay light and every referenced file carries the same model generation."""
    import numpy as np

    class _Predictor:
        def prediction_matrices(self, names, surface="Hard", best_of=3):
            n = len(names)
            matrix = np.full((n, n), 0.5)
            if n > 1:
                matrix[0, 1], matrix[1, 0] = 0.6, 0.4
            return {key: matrix.copy() for key in ("eloBlend", "pointModel", "combiner")}

        def prediction_evidence_matrices(self, names, surface="Hard", best_of=3):
            import tennis_model.model.predict as predict

            n = len(names)
            return {
                "effects": {key: np.zeros((n, n)) for key in predict.EVIDENCE_GROUPS},
                "available": {key: np.zeros((n, n)) for key in predict.EVIDENCE_GROUPS},
            }

    players = [{"name": "A"}, {"name": "B"}]
    index, shards = export.build_matrix_shards(_Predictor(), players, "atp", "generation-1")
    assert index["generation"] == "generation-1"
    assert len(shards) == 6
    assert set(index["surfaces"]) == set(export.SURFACES)
    assert all(shard["generation"] == "generation-1" for shard in shards.values())
    assert all(set(shard["components"]) == {"eloBlend", "pointModel", "combiner"}
               for shard in shards.values())
    assert all(shard["evidence"]["encoding"] == "upper-triangle-bps-v1"
               and len(shard["evidence"]["effects"]["surfaceElo"]) == 1
               for shard in shards.values())

    profiles = {
        "A": {"name": "A", "eloRank": 1, "style": {"style_aggression": 0.2},
              "history": [["2026-01", 1800]], "recent": [{"won": True}], "h2h": []},
        "B": {"name": "B", "eloRank": 2, "style": {},
              "history": [], "recent": [], "h2h": [{"opp": "A", "w": 0, "l": 1}]},
    }
    profile_index, profile_shards = export.build_profile_shards(profiles, "generation-1")
    assert [row["name"] for row in profile_index["profiles"]] == ["A", "B"]
    assert len(profile_shards) == 2
    assert all("history" not in row for row in profile_index["profiles"])
    for row in profile_index["profiles"]:
        shard = profile_shards[row["file"]]
        assert shard["name"] == row["name"] and shard["generation"] == "generation-1"


def test_released_draw_exports_stable_exact_scenario_contract():
    import numpy as np

    names = ["A", "B", "C", "D"]
    matrix = np.array([
        [0.5, 0.6, 0.7, 0.8], [0.4, 0.5, 0.55, 0.65],
        [0.3, 0.45, 0.5, 0.6], [0.2, 0.35, 0.4, 0.5],
    ])

    class _Elo:
        overall = {name: 1 for name in names}

    class _Predictor:
        elo = _Elo()
        trained_at = "model-generation"

        def prediction_matrices(self, players, **kwargs):
            assert players == names
            return {key: matrix.copy() for key in ("eloBlend", "pointModel", "combiner")}

    event = {
        "name": "Exact Open", "espnId": "event-9", "status": "live",
        "surface": "Hard", "bestOf": 3, "drawSize": 4, "bracketSize": 4,
        "rounds": [
            {"round": "SF", "matches": [
                {"a": "A", "b": "B", "winner": None},
                {"a": "C", "b": "D", "winner": None},
            ]},
            {"round": "F", "matches": [{"a": None, "b": None, "winner": None}]},
        ],
    }
    tournament = {"name": "Exact Open", "espnId": "event-9"}
    index, shards = export.build_scenario_shards(
        _Predictor(), [event], [tournament], "build-generation",
    )
    ref = index["events"][0]
    shard = shards[ref["file"]]
    assert index["schema"] == "scenario-v1"
    assert ref["espnId"] == "event-9" and ref["lockableMatches"] == 2
    assert shard["geometry"][0]["matches"][0]["id"] == "event-9:r0:m0"
    assert shard["matrix"] == shard["matrices"]["combiner"]
    assert sum(shard["baseline"]["champion"].values()) == 1.0
    assert set(shard["titleLeverage"]) == {"event-9:r0:m0", "event-9:r0:m1"}
    assert event["scenario"]["file"] == ref["file"]
    assert tournament["scenario"]["modelGeneration"] == "model-generation"


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
    test_build_meta_separates_build_time_from_model_time()
    test_build_meta_audits_wta_125_policy_rows()
    test_predictor_stamps_trained_at_and_survives_a_pickle_round_trip()
    test_fixtures_upset_flag_agrees_with_the_rounded_prob_it_ships()
    print("\nALL PASSED")
