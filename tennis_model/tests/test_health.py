"""Unit checks for the data-health sentinel (data/health.py) — fully synthetic.

Runnable directly (`python tests/test_health.py`) or under pytest. problems() and
output_problems() are pure given their input dicts; tour_health()/read_outputs()/main()
are exercised with their IO seams redirected (same save/restore pattern as test_track).
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.health as health
from tennis_model.model.features import FEATURES

NOW = pd.Timestamp("2026-07-09")   # mid-season, deterministic (July)


# --- synthetic healthy produced-output builders --------------------------------------
def _healthy_evidence(a="P0", b="P1", p=0.7) -> dict:
    return {
        "schema": "evidence-v1", "playerA": a, "playerB": b,
        "probabilityA": p,
        "signals": [
            {"key": key, "available": key not in ("home", "h2h", "style"),
             "supports": a if key == "surfaceElo" else None,
             "impactPp": 2.0 if key == "surfaceElo" else 0.0, "facts": {}}
            for key in health._EVIDENCE_KEYS
        ],
        "note": "Grouped model sensitivity; evidence, not causation; groups need not add up.",
    }


def _healthy_watch() -> dict:
    return {
        "schema": "watch-v1", "score": 45.5,
        "weights": copy.deepcopy(health._WATCH_WEIGHTS),
        "factors": {
            "closeness": {"score": 60.0, "available": True},
            "quality": {"score": 80.0, "available": True},
            "styleContrast": {"score": 0.0, "available": False},
            "stakes": {"score": 50.0, "available": True},
            "titleLeverage": {"score": 0.0, "available": False},
        },
        "coverage": 3,
    }


def _healthy_bracket() -> dict:
    """A clean 4-player completed bracket (SF -> F) consistent with the 'Mini Open'
    tournaments entry: rounds halve, winners feed forward, champion agrees, probs in range."""
    return {
        "name": "Mini Open", "surface": "Hard", "level": "ATP 250", "bestOf": 3,
        "start": "2026-07-01", "end": "2026-07-06", "status": "completed",
        "drawSize": 4, "bracketSize": 4, "champion": "A", "runnerUp": "C",
        "drawSource": "wikipedia", "drawSourceId": "Mini Open draw",
        "drawSourceUrl": "https://en.wikipedia.org/wiki/Mini_Open_draw",
        "rounds": [
            {"round": "SF", "matches": [
                {"a": "A", "b": "B", "seedA": 1, "seedB": None, "winner": "a",
                 "score": "6-3 6-4", "p": 0.8, "probSource": "logged", "upset": False},
                {"a": "C", "b": "D", "seedA": 2, "seedB": None, "winner": "a",
                 "score": "7-5 6-4", "p": 0.6, "probSource": "model", "upset": False},
            ]},
            {"round": "F", "matches": [
                {"a": "A", "b": "C", "seedA": 1, "seedB": 2, "winner": "a",
                 "score": "6-4 6-4", "p": 0.55, "probSource": "logged", "upset": False},
            ]},
        ],
    }


def _healthy_data() -> dict:
    return {
        "meta": {"matches": 300_000, "activePlayers": 3, "features": ["f"] * len(FEATURES),
                 "matchPopulationVersion": health.MATCH_POPULATION_VERSION,
                 "modelPopulationVersion": health.MATCH_POPULATION_VERSION,
                 "dualStateThreshold": None, "dualStateReady": False,
                 "wta125Matches": 0, "excludedWta125Matches": 0,
                 "excludedUnclassifiedWtaLiveMatches": 0,
                 "lastUpdated": "2026-07-09T00:00:00Z",
                 "modelTrainedAt": "2026-07-08T04:30:00Z"},   # last night's full retrain
        "players": [{"name": f"P{i}", "elo": 2000 - i, "eloRank": i + 1, "liveRank": i + 1,
                     "heightCm": 185, "winRate10": 0.6,
                     "servePctHard": 0.64, "servePctClay": 0.61, "servePctGrass": 0.66,
                     "returnPctHard": 0.36, "returnPctClay": 0.39, "returnPctGrass": 0.34}
                    for i in range(3)],
        "matrix-index": {"generation": "2026-07-08T04:30:00Z",
                         "players": ["P0", "P1", "P2"], "formats": [3],
                         "surfaces": {"Hard": {"3": "matrix-hard-bo3.json"}}},
        "profile-index": {"generation": "2026-07-08T04:30:00Z", "profiles": [
            {"name": f"P{i}", "file": f"profile-{i}.json", "eloRank": i + 1,
             "servePct": 0.64, "returnPct": 0.36, "eloHard": 2000 - i,
             "eloClay": 2000 - i, "eloGrass": 2000 - i, "style": {}}
            for i in range(3)
        ]},
        "tournaments": [{"name": "Test Open", "surface": "Grass", "level": "ATP 250",
                         "bestOf": 3, "status": "live",
                         "drawStatus": "real", "drawSize": 128, "aliveCount": 7, "champion": None,
                         "coverageKey": "espn:1-2026",
                         "hasBracket": False,
                         "projection": [{"name": "P0", "champion": 0.5, "final": 0.6, "sf": 0.8,
                                         "reach": {"R32": 1.0, "R16": 1.0, "QF": 0.95,
                                                   "SF": 0.8, "F": 0.6, "Champion": 0.5}}]},
                        {"name": "Mini Open", "surface": "Hard", "level": "ATP 250",
                         "bestOf": 3, "status": "completed",
                         "drawStatus": "real", "drawSize": 4, "aliveCount": 1, "champion": "A",
                         "coverageKey": "espn:2-2026",
                         "hasBracket": True, "projection": []}],
        "event_coverage": {"version": 1, "tour": "atp", "buildDate": "2026-07-09",
                           "events": [
                               {"key": "espn:1-2026", "name": "Test Open", "espnId": "1-2026",
                                "start": "2026-07-01", "end": "2026-07-12",
                                "evidence": ["result"], "players": ["P0", "P1"]},
                           ], "shippedKeys": ["espn:1-2026", "espn:2-2026"],
                           "shellKeys": []},
        "brackets": [_healthy_bracket()],
        "scenario-index": {"schema": "scenario-v1", "schemaVersion": 1,
                           "generation": "2026-07-08T04:30:00Z", "events": []},
        "performance": {"tour": "atp", "window": 10, "players": []},
        "upcoming": [{"event": "Test Open", "playerA": "P0", "playerB": "P1",
                      "pA": 0.7, "components": {"eloBlend": 0.68, "pointModel": 0.72,
                                                    "combiner": 0.7},
                      "evidence": _healthy_evidence(), "watch": _healthy_watch(),
                      "watchRank": 1}],
        "fixtures": [{"modelProb": 0.6, "upset": False}, {"modelProb": 0.4, "upset": True}],
        "track": {"matchForecasts": {"logged": 10, "graded": 6, "pending": 4,
                                     "drift": {"status": "ok", "windowDays": 90, "n": 400,
                                               "logloss": 0.58, "expectedLogloss": 0.575,
                                               "d": 0.005, "se": 0.019, "t": 0.26}}},
        "market": {"years": [2012, 2026], "matched": 20_000,
                   "oosEnd": "2026-07-06", "lastMatchedDate": "2026-07-04"},
        "method": {"tour": "atp",
                   "elo": {"ratingScale": 400.0, "kScale": 145.0,
                           "surfaceBlend": 0.63, "movCap": 2.0},
                   "serveReturn": {"formHalflifeDays": 200.0},
                   "context": {"peakAge": 26.5},
                   "stateGate": {"enabled": False, "minMainMatches": None,
                                 "trainingPopulation": "main-only", "enrichedRows": []},
                   "tiers": {"kMult": {"grand_slam": 0.91, "atp250": 0.9}, "default": 0.9},
                   "combiner": {"featureCount": len(FEATURES), "nBag": 5},
                   "protocol": {"tuneYears": [2010, 2019], "valStartYear": 2020}},
    }


def _healthy_shards() -> dict:
    m = [[0.5 if i == j else (0.6 if i < j else 0.4) for j in range(3)] for i in range(3)]
    z = [0, 0, 0]  # packed upper triangle for a three-player roster
    availability = [0, 0, 0]
    generation = "2026-07-08T04:30:00Z"
    return {
        "matrix-hard-bo3.json": {"generation": generation, "players": ["P0", "P1", "P2"],
                                 "surface": "Hard", "bestOf": 3,
                                 "components": {key: copy.deepcopy(m)
                                                for key in ("eloBlend", "pointModel", "combiner")},
                                 "evidence": {"schema": "evidence-v1",
                                              "encoding": "upper-triangle-bps-v1",
                                              "effects": {key: copy.deepcopy(z)
                                                          for key in health._EVIDENCE_KEYS},
                                              "available": {"h2h": copy.deepcopy(availability),
                                                            "style": copy.deepcopy(availability)},
                                              "homeAvailable": False}},
        **{f"profile-{i}.json": {"generation": generation, "name": f"P{i}",
                                    "history": [], "recent": [], "h2h": []}
           for i in range(3)},
    }


def _oc(data=None, missing=None, corrupt=None, forecast=("keep",), kalshi_ledger=None,
        shards=None, missing_files=None, corrupt_files=None, draw_cache=None) -> dict:
    return {"data": _healthy_data() if data is None else data,
            "missing": missing or [], "corrupt": corrupt or [],
            "shards": _healthy_shards() if shards is None else shards,
            "missing_files": missing_files or [], "corrupt_files": corrupt_files or [],
            "draw_cache": draw_cache,
            "forecast": {"lines": 200, "max_as_of": "2026-07-09"} if forecast == ("keep",) else forecast,
            "kalshi_ledger": kalshi_ledger}


def _ledger_row(**over) -> dict:
    """A clean SCORED kalshi-ledger row (morning-anchored quote, consistent join)."""
    row = {"event_ticker": "KXATPMATCH-26JUL08AAABBB", "match_status": "matched",
           "result_type": "completed", "price_kind": "candle",
           "p_model": "0.6100", "p_kalshi": "0.5500",
           "mid_a": "0.5500", "mid_b": "0.4500",
           "price_ts": "2026-07-08T07:55:00Z", "result_date": "2026-07-08",
           "player_a": "Arthur Fery", "player_b": "Flavio Cobolli",
           "kalshi_result_a": "no", "a_won": "0"}
    row.update(over)
    return row


def test_visible_forecast_timeline_must_be_current_and_hour_deduped():
    d = _healthy_data()
    d["upcoming"][0]["forecast"] = {
        "first": 0.6, "current": 0.7, "delta": 0.1, "snapshots": 2,
        "timeline": [
            {"asOf": "2026-07-09T08:00:00Z", "p": 0.6, "firstSighting": True},
            {"asOf": "2026-07-09T08:30:00Z", "p": 0.65},
        ],
    }
    problems = health.output_problems("atp", _oc(data=d), NOW)
    assert any("repeats a UTC hour" in problem for problem in problems)
    assert any("current probability disagrees" in problem for problem in problems)


def test_expectation_summary_arithmetic_is_a_blocking_invariant():
    d, shards = _healthy_data(), _healthy_shards()
    d["performance"]["players"] = [{
        "name": "P0", "n": 1, "wins": 1, "expectedWins": 0.7, "delta": 0.9,
    }]
    d["profile-index"]["profiles"][0]["performance"] = {
        "n": 1, "wins": 1, "expectedWins": 0.7, "delta": 0.9,
    }
    shards["profile-0.json"]["performance"] = {
        "name": "P0", "n": 1, "wins": 1, "expectedWins": 0.7, "delta": 0.9,
        "recent": [{"matchId": "v2|espn:1|2026|F|p0|p1", "p": 0.7,
                    "won": True, "residual": 0.3}],
    }
    problems = health.output_problems("atp", _oc(data=d, shards=shards), NOW)
    problem = next(problem for problem in problems if "performance.json summary" in problem)
    assert health._gate_blocks(problem)


def test_scenario_base_must_equal_exact_propagation():
    from tennis_model.sim.exact import propagate_rounds, title_leverage
    from tennis_model.sim.scenarios import exact_bracket

    rounds = [{"round": "F", "matches": [{"a": "P0", "b": "P1", "winner": None}]}]
    matrix = [[0.5, 0.7], [0.3, 0.5]]
    baseline = propagate_rounds(rounds, ["P0", "P1"], matrix, event_id="event-1")
    shard = {
        "schema": "scenario-v1", "schemaVersion": 1, "generation": "g",
        "modelGeneration": "mg", "event": {"espnId": "event-1"},
        "players": ["P0", "P1"], "rounds": rounds, "matrix": matrix,
        "matrices": {key: copy.deepcopy(matrix) for key in ("eloBlend", "pointModel", "combiner")},
        "geometry": [{"round": "F", "matches": [{"id": "event-1:r0:m0"}]}],
        "baseline": baseline,
        "titleLeverage": title_leverage(rounds, ["P0", "P1"], matrix, event_id="event-1"),
        "base": exact_bracket(rounds, ["P0", "P1"], matrix),
    }
    shard["base"]["champion"][0]["p"] = 0.9
    out = []
    health._check_scenarios(
        out, "atp", {"schema": "scenario-v1", "schemaVersion": 1, "generation": "g",
                       "events": [{"file": "scenario-test.json", "espnId": "event-1",
                                   "generation": "g", "modelGeneration": "mg",
                                   "lockableMatches": 1}]},
        {"scenario-test.json": shard},
        [{"status": "live", "scenarioFile": "scenario-test.json"}],
    )
    assert any("disagrees with exact propagation" in problem for problem in out)


def test_prediction_evidence_requires_seven_ranked_noncausal_signals():
    d = _healthy_data()
    d["upcoming"][0]["evidence"]["note"] = "This caused the prediction."
    d["upcoming"][0]["evidence"]["signals"].reverse()
    problems = health.output_problems("atp", _oc(data=d), NOW)
    assert any("non-causal disclaimer" in problem for problem in problems)
    assert any("strongest evidence" in problem for problem in problems)


def test_watch_score_and_matrix_evidence_are_blocking_invariants():
    d, shards = _healthy_data(), _healthy_shards()
    d["upcoming"][0]["watch"]["score"] = 99.0
    shards["matrix-hard-bo3.json"]["evidence"]["effects"]["form"][0] = 10_001
    problems = health.output_problems("atp", _oc(data=d, shards=shards), NOW)
    assert any("watch score disagrees" in problem for problem in problems)
    assert any("packed evidence[form] is malformed" in problem for problem in problems)


def test_begun_event_missing_from_tournaments_is_a_blocking_output_problem():
    d = _healthy_data()
    d["tournaments"] = [t for t in d["tournaments"] if t["coverageKey"] != "espn:1-2026"]
    out = health.output_problems("atp", _oc(data=d), NOW)
    problem = next(p for p in out if "begun tournament" in p)
    assert "Test Open" in problem and "espn:1-2026" in problem
    assert health._gate_blocks(problem)


def test_begun_event_must_ship_exactly_once_by_coverage_key():
    d = _healthy_data()
    d["tournaments"].append(dict(d["tournaments"][0], name="Renamed Test Open"))
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("coverage key espn:1-2026 appears 2 times" in p for p in out)


def test_calendar_only_event_is_not_an_expected_coverage_entry():
    d = _healthy_data()
    d["event_coverage"]["calendarOnly"] = [{"key": "espn:future-2026", "name": "Future"}]
    assert not any("Future" in p for p in health.output_problems("atp", _oc(data=d), NOW))


def _h(result_age=1, stats_age=2, frac=0.9, n=500, fresh_age=3, charting_age=30) -> dict:
    return {"result_age_days": result_age, "stats_age_days": stats_age,
            "cur_year_stats_fraction": frac, "cur_year_matches": n,
            "fresh_age_days": fresh_age, "charting_age_days": charting_age}


def _espn_receipt(status="success", *, failed=0, overlay="updated") -> dict:
    attempted = 28
    return {
        "schema": "espn-acquisition-v1", "tour": "atp",
        "completedAt": "2026-07-09T12:00:00Z", "status": status,
        "eventCount": 1 if status in ("success", "partial_query_failure") else 0,
        "queries": {"attempted": attempted, "succeeded": attempted - failed,
                    "failed": failed},
        "overlay": {"status": overlay, "updatedFiles": [], "retainedFiles": [],
                    "lastGoodAt": "2026-07-09T12:00:00Z"},
    }


def test_espn_acquisition_receipt_surfaces_same_run_transport_state():
    clean = _h(); clean["espn_acquisition"] = _espn_receipt()
    row = next(r for r in health.source_checks("atp", clean, NOW)
               if r["key"] == "espn_acquisition")
    assert row["ok"] and row["note"] is None

    empty = _h(); empty["espn_acquisition"] = _espn_receipt("success_empty")
    row = next(r for r in health.source_checks("atp", empty, NOW)
               if r["key"] == "espn_acquisition")
    assert row["ok"] and "0 events" in row["note"]

    partial = _h(); partial["espn_acquisition"] = _espn_receipt(
        "partial_query_failure", failed=1, overlay="partially_updated")
    row = next(r for r in health.source_checks("atp", partial, NOW)
               if r["key"] == "espn_acquisition")
    assert row["ok"] and "27 of 28" in row["note"]

    failed = _h(); failed["espn_acquisition"] = _espn_receipt(
        "total_transport_failure", failed=28, overlay="retained_last_good")
    problem = health.problems("atp", failed, NOW)[0]
    assert problem == ("atp: ESPN scoreboard acquisition failed for all 28 queries — "
                       "retained last-good live overlay")
    # Attempt timestamps never enter the problem string, so hourly dedup cannot flap.
    failed["espn_acquisition"]["completedAt"] = "2026-07-09T13:00:00Z"
    assert health.problems("atp", failed, NOW) == [problem]


def test_majority_failed_partial_acquisition_stays_failing():
    degraded = _h()
    receipt = _espn_receipt("partial_query_failure", failed=27,
                            overlay="retained_last_good")
    receipt["eventCount"] = 0
    degraded["espn_acquisition"] = receipt
    problem = next(p for p in health.problems("atp", degraded, NOW)
                   if "ESPN scoreboard" in p)
    assert problem == ("atp: ESPN scoreboard acquisition severely degraded "
                       "(27 of 28 queries failed) — retained last-good live overlay")

    # Older/foreign producers that did publish a degraded sweep must not be described as
    # having no overlay at all; the red incident should state what actually happened.
    degraded["espn_acquisition"]["overlay"]["status"] = "updated"
    problem = next(p for p in health.problems("atp", degraded, NOW)
                   if "ESPN scoreboard" in p)
    assert problem == ("atp: ESPN scoreboard acquisition severely degraded "
                       "(27 of 28 queries failed) — wrote a degraded live overlay")

    # One bad day in an otherwise answered, genuinely idle window remains an amber note.
    mostly_answered = _h()
    receipt = _espn_receipt("partial_query_failure", failed=1,
                            overlay="retained_last_good")
    receipt["eventCount"] = 0
    mostly_answered["espn_acquisition"] = receipt
    row = next(r for r in health.source_checks("atp", mostly_answered, NOW)
               if r["key"] == "espn_acquisition")
    assert row["ok"] and "27 of 28" in row["note"] and "usable" not in row["note"]
    assert row["unit"] == ""


def test_partial_overlay_processing_failure_is_named_not_called_retained():
    h = _h(); receipt = _espn_receipt()
    receipt["overlay"].update(status="partially_updated", processingFailureType="OSError",
                              updatedFiles=["live.csv"], retainedFiles=["fields.json"])
    h["espn_acquisition"] = receipt
    problem = next(p for p in health.problems("atp", h, NOW) if "ESPN live overlay" in p)
    assert "explicitly partial overlay update" in problem
    assert "retained last-good" not in problem


def test_espn_receipt_missing_is_rollout_note_but_malformed_is_actionable():
    missing = _h(); missing["espn_acquisition"] = {"status": "missing"}
    row = next(r for r in health.source_checks("atp", missing, NOW)
               if r["key"] == "espn_acquisition")
    assert row["ok"] and "legacy cache" in row["note"]
    malformed = _h(); malformed["espn_acquisition"] = {"status": "malformed"}
    assert health.problems("atp", malformed, NOW) == [
        "atp: ESPN scoreboard acquisition receipt is malformed/incompatible"]


def test_espn_receipt_reader_rejects_contradictory_status_counts(tmp_path, monkeypatch):
    monkeypatch.setattr(health, "live_dir", lambda tour: tmp_path)
    path = tmp_path / "espn_acquisition.json"
    path.write_text(json.dumps(_espn_receipt()), encoding="utf-8")
    assert health._espn_acquisition("atp")["status"] == "success"
    bad = _espn_receipt("success_empty")
    bad["eventCount"] = 4
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert health._espn_acquisition("atp") == {"status": "malformed"}


def test_espn_receipt_changes_the_source_manifest_fingerprint(tmp_path, monkeypatch):
    roots = {name: tmp_path / name for name in ("historical", "stats", "fresh", "lower", "live")}
    for root in roots.values():
        root.mkdir()
    monkeypatch.setattr(health, "historical_dir", lambda tour: roots["historical"])
    monkeypatch.setattr(health, "stats_dir", lambda tour: roots["stats"])
    monkeypatch.setattr(health, "fresh_dir", lambda tour: roots["fresh"])
    monkeypatch.setattr(health, "lower_dir", lambda tour: roots["lower"])
    monkeypatch.setattr(health, "live_dir", lambda tour: roots["live"])
    monkeypatch.setattr(health, "CHARTING_DIR", tmp_path / "charting")
    before = health._health_input_fingerprint("atp")
    (roots["live"] / "espn_acquisition.json").write_text(
        json.dumps(_espn_receipt()), encoding="utf-8")
    after = health._health_input_fingerprint("atp")
    assert before != after


def test_new_receipt_invalidates_and_reloads_a_same_day_source_manifest(tmp_path, monkeypatch):
    roots = {name: tmp_path / name for name in ("historical", "stats", "fresh", "lower", "live")}
    for root in roots.values():
        root.mkdir()
    monkeypatch.setattr(health, "historical_dir", lambda tour: roots["historical"])
    monkeypatch.setattr(health, "stats_dir", lambda tour: roots["stats"])
    monkeypatch.setattr(health, "fresh_dir", lambda tour: roots["fresh"])
    monkeypatch.setattr(health, "lower_dir", lambda tour: roots["lower"])
    monkeypatch.setattr(health, "live_dir", lambda tour: roots["live"])
    monkeypatch.setattr(health, "CHARTING_DIR", tmp_path / "charting")
    monkeypatch.setattr(health, "OUTPUT_DIR", tmp_path / "output")
    monkeypatch.setattr(health, "fresh_date_max", lambda tour, now=None: NOW)
    monkeypatch.setattr(health, "fresh_future_date_max", lambda tour, now=None: None)
    monkeypatch.setattr(health, "charting_date_max", lambda tour: NOW)
    frame = pd.DataFrame({"date": pd.to_datetime([NOW]), "completed": [True],
                          "has_stats": [True]})
    health.write_health_manifest("atp", frame, NOW)
    receipt = _espn_receipt("total_transport_failure", failed=28,
                            overlay="retained_last_good")
    receipt["eventCount"] = 0
    (roots["live"] / "espn_acquisition.json").write_text(
        json.dumps(receipt), encoding="utf-8")
    loads = []
    monkeypatch.setattr(health, "load_matches", lambda tour: loads.append(tour) or frame)
    current = health.tour_health("atp", NOW)
    assert loads == ["atp"]
    assert current["espn_acquisition"]["status"] == "total_transport_failure"


def test_a_future_row_cannot_disable_the_fresh_overlay_freshness_gate(tmp_path, monkeypatch):
    """Found 2026-08-07 on live data: WTA reported fresh_age_days = -1078 against a 14-day
    limit and passed, because the overlay still carried the Iasi final as 2029/7/20 (the
    same corrupt row as the 2026-07-25 incident). Age is `now - max`, so one future row pins
    it negative forever and the freeze alarm for that source is dead — for three weeks, it
    was. `_drop_impossible_dates` keeps the row out of the model population, which is
    exactly why the merged future_dates check never saw it either."""
    d = tmp_path / "wta" / "fresh"
    d.mkdir(parents=True)
    (d / "2026.csv").write_text(
        "tourney_date\n2026/7/18\n2026/7/20\n2029/7/20\n", encoding="utf-8")
    monkeypatch.setattr(health, "fresh_dir", lambda tour: d)
    now = pd.Timestamp("2026-08-07")

    assert health.fresh_date_max("wta", now) == pd.Timestamp("2026-07-20"), \
        "the corrupt row must not be the reported maximum"
    assert int((now - health.fresh_date_max("wta", now)).days) == 18, "18d stale, and visible"
    # and the row it excluded is still named, so the fix reports the corruption rather than
    # burying it — the whole failure mode here was a bad row nothing could see.
    assert health.fresh_future_date_max("wta", now) == pd.Timestamp("2029-07-20")

    (d / "2026.csv").write_text("tourney_date\n2026/7/18\n2026/8/05\n", encoding="utf-8")
    assert health.fresh_date_max("wta", now) == pd.Timestamp("2026-08-05")
    assert health.fresh_future_date_max("wta", now) is None, "a clean file reports nothing"
    print("ok test_a_future_row_cannot_disable_the_fresh_overlay_freshness_gate")


def test_fresh_overlay_corruption_is_noted_but_does_not_page():
    """Visible, not alarming. The row is already handled three ways by the time it reaches
    here (repaired where topology proves the year, dropped otherwise, and excluded from the
    age signal beside it), and the daily full run reds on ANY problem no matter what the
    hourly dedup says — so raising one would page every morning forever about an upstream
    typo nobody on this side can edit. That standing-red trap is already in the lessons."""
    rows = health.source_checks("wta", dict(_h(), fresh_future_date_max="2029-07-20"),
                                pd.Timestamp("2026-08-07"))
    hit = next(r for r in rows if r["key"] == "fresh_future")
    assert "2029-07-20" in hit["note"], hit
    assert hit["ok"] and hit["problem"] is None, "must not red the daily run"
    assert health.problems("wta", dict(_h(), fresh_future_date_max="2029-07-20"),
                           pd.Timestamp("2026-08-07")) == []
    clean = health.source_checks("wta", _h(), pd.Timestamp("2026-08-07"))
    assert next(r for r in clean if r["key"] == "fresh_future")["note"] is None
    print("ok test_fresh_overlay_corruption_is_noted_but_does_not_page")


def test_problems_fresh_is_clean():
    assert health.problems("atp", _h(), pd.Timestamp("2026-07-01")) == []
    print("ok test_problems_fresh_is_clean")


def test_problems_future_dated_match_flagged():
    """A future date is corruption, not staleness, and the result-age check structurally
    cannot see it: result_age_days goes NEGATIVE and sails under its maximum. One mistyped
    year in the WTA overlay (Iasi as 2029/7/20, 2026-07-25) moved elo.last_date three years
    out, so the 550d active window kept only the 2 players in that row and the tour exported
    2 players instead of 200."""
    now = pd.Timestamp("2026-07-25")
    out = health.problems("wta", {**_h(result_age=-1095), "date_max": "2029-07-20"}, now)
    assert any("in the FUTURE" in p for p in out), out
    # the negative age must NOT be reported as fresh-and-fine
    assert not any("newest completed match is -" in p for p in out), out
    # a normal past date is clean, and so is a plausible near-future scheduled row
    for dmax in ("2026-07-24", "2026-07-30"):
        assert health.problems("wta", {**_h(), "date_max": dmax}, now) == [], dmax
    print("ok test_problems_future_dated_match_flagged")


def test_problems_stale_results_flagged():
    out = health.problems("atp", _h(result_age=10), pd.Timestamp("2026-07-01"))
    assert len(out) == 1 and "newest completed match" in out[0], out
    print("ok test_problems_stale_results_flagged")


def test_problems_offseason_relax_window():
    h = _h(result_age=20, stats_age=20)
    assert health.problems("atp", h, pd.Timestamp("2026-12-15")) == []
    # season effectively ends mid-November: late Nov must relax too (regression:
    # the relax used to start Dec 1, redding every build Nov 21-30)
    assert health.problems("atp", h, pd.Timestamp("2026-11-25")) == []
    assert health.problems("atp", h, pd.Timestamp("2026-11-10")) != []
    print("ok test_problems_offseason_relax_window")


def test_problems_missing_results_is_a_problem():
    out = health.problems("atp", _h(result_age=None), pd.Timestamp("2026-07-01"))
    assert any("no completed matches" in p for p in out), out
    print("ok test_problems_missing_results_is_a_problem")


def test_problems_coverage_gate_needs_volume():
    now = pd.Timestamp("2026-07-01")
    assert any("coverage" in p for p in health.problems("atp", _h(frac=0.3), now))
    # under 100 matches the season fraction is noise — not gated
    assert not any("coverage" in p
                   for p in health.problems("atp", _h(frac=0.3, n=50), now))
    print("ok test_problems_coverage_gate_needs_volume")


def test_problems_fresh_overlay_freeze_flagged():
    """The merged result_age can't see a fresh-overlay freeze (the ESPN live overlay
    keeps the merged max current) — the overlay's own age gate must catch it, with
    off-season + early-January grace (the ~weekly updater lags the season restart).
    The gate is enforced only while the stats overlay is ALSO stale: fresh is a
    redundancy layer, and a shadowed freeze (TennisCourtLog's ATP file frozen
    2026-06-22 while the TML site stayed daily-fresh) is a standing red no local
    action can clear."""
    july, dec = pd.Timestamp("2026-07-01"), pd.Timestamp("2026-12-15")
    stale = {"fresh_age": 20, "stats_age": 17}     # stats stale too -> fresh gate is live
    assert any("fresh-overlay" in p for p in health.problems("atp", _h(**stale), july))
    # shadowed: the full-schema stats overlay is current, so results/ranks/stats all
    # still flow — a frozen fresh overlay starves nothing and must not stand red
    assert not any("fresh-overlay" in p
                   for p in health.problems("atp", _h(fresh_age=20), july))
    assert health.problems("atp", _h(fresh_age=20), dec) == []                     # off-season
    assert not any("fresh-overlay" in p                                            # Jan grace
                   for p in health.problems("atp", _h(**stale), pd.Timestamp("2026-01-10")))
    assert any("fresh-overlay" in p                                                # grace caps at 45
               for p in health.problems("atp", _h(fresh_age=50, stats_age=50),
                                        pd.Timestamp("2026-01-10")))
    assert any("fresh-overlay" in p                                                # grace ends Jan 15
               for p in health.problems("atp", _h(**stale), pd.Timestamp("2026-01-20")))
    # a wholly-unloadable overlay is a setup/bootstrap break, never shadowed
    assert any("no loadable results" in p
               for p in health.problems("atp", _h(fresh_age=None), july))
    print("ok test_problems_fresh_overlay_freeze_flagged")


def test_charting_coverage_age_is_context_not_a_source_failure():
    """MCP match age cannot diagnose its transport: the volunteer source's official
    Overview commits have landed 145-200 days apart. Keep old coverage visible as a
    note, but alarm when no charting data can be loaded at all."""
    now = pd.Timestamp("2026-07-01")
    lim = health.HEALTH_CHARTING_COVERAGE_NOTE_DAYS
    stale = _h(charting_age=lim + 110)
    rows = {r["key"]: r for r in health.source_checks("atp", stale, now)}
    assert rows["charting"]["ok"]
    assert "volunteer batch source" in rows["charting"]["note"]
    assert not any("charting" in p for p in health.problems("atp", stale, now))
    current = {r["key"]: r for r in health.source_checks(
        "atp", _h(charting_age=max(0, lim - 10)), now)}
    assert current["charting"]["note"] is None
    assert any("charting files missing" in p
               for p in health.problems("atp", _h(charting_age=None), now))
    print("ok test_charting_coverage_age_is_context_not_a_source_failure")


def test_source_checks_structure_and_consistency():
    """source_checks() is the single source of truth the /health page renders and
    problems() derives from — rows must be structurally complete, and the derived
    problem list must equal the failing rows' problems in every scenario."""
    july = pd.Timestamp("2026-07-01")
    scenarios = [
        _h(),                                             # healthy
        _h(result_age=10),                                # stale results
        _h(fresh_age=20),                                 # fresh over limit, shadowed
        _h(fresh_age=20, stats_age=17),                   # fresh over limit, gate live
        _h(charting_age=None),                            # charting missing
        _h(result_age=None, stats_age=None, frac=None),   # empty tour
    ]
    for h in scenarios:
        for now in (july, pd.Timestamp("2026-12-15"), pd.Timestamp("2026-01-10")):
            rows = health.source_checks("atp", h, now)
            assert [r["key"] for r in rows] == ["results", "future_dates", "stats", "coverage", "fresh", "fresh_future", "charting"]
            for r in rows:
                assert set(r) == {"key", "label", "value", "limit", "unit", "date",
                                  "ok", "note", "problem"}
                assert r["ok"] == (r["problem"] is None)
            assert health.problems("atp", h, now) == [r["problem"] for r in rows if r["problem"]]
    # the shadowed fresh overlay renders as a NOTE (page shows amber), never a problem
    rows = {r["key"]: r for r in health.source_checks("atp", _h(fresh_age=20), july)}
    assert rows["fresh"]["ok"] and "shadowed" in rows["fresh"]["note"]
    live = {r["key"]: r for r in health.source_checks("atp", _h(fresh_age=20, stats_age=17), july)}
    assert not live["fresh"]["ok"] and live["fresh"]["note"] is None
    print("ok test_source_checks_structure_and_consistency")


def test_tour_health_empty_frame_reports_none():
    """An empty tour must report None ages (flagged downstream), not crash on NaT."""
    orig = (health.load_matches, health.fresh_date_max, health.fresh_future_date_max, health.charting_date_max)
    try:
        health.load_matches = lambda tour: pd.DataFrame(
            {"date": pd.to_datetime(pd.Series([], dtype="object")),
             "completed": pd.Series([], dtype=bool),
             "has_stats": pd.Series([], dtype=bool)})
        health.fresh_future_date_max = lambda tour, now=None: None
        health.fresh_date_max = lambda tour, now=None: None
        health.charting_date_max = lambda tour: None
        h = health.tour_health("atp", pd.Timestamp("2026-07-01"))
    finally:
        health.load_matches, health.fresh_date_max, health.fresh_future_date_max, health.charting_date_max = orig
    assert h["matches"] == 0
    assert h["date_max"] is None and h["result_age_days"] is None
    assert h["fresh_age_days"] is None and h["charting_age_days"] is None
    assert any("no completed matches" in p
               for p in health.problems("atp", h, pd.Timestamp("2026-07-01")))
    print("ok test_tour_health_empty_frame_reports_none")


def test_pipeline_health_manifest_reuses_only_the_same_input_fingerprint(monkeypatch, tmp_path):
    """The standalone health pass may skip the expensive merge only for the exact
    source-file generation the pipeline summarized; a changed input falls back."""
    frame = pd.DataFrame({
        "date": pd.to_datetime(["2026-07-08"]),
        "completed": [True],
        "has_stats": [True],
    })
    fallback = pd.DataFrame({
        "date": pd.to_datetime(["2026-07-08", "2026-07-09"]),
        "completed": [True, True],
        "has_stats": [True, True],
    })
    fingerprint = {"value": "source-a"}
    loads = []
    monkeypatch.setattr(health, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(health, "_health_input_fingerprint", lambda tour: fingerprint["value"])
    monkeypatch.setattr(health, "fresh_date_max", lambda tour, now=None: pd.Timestamp("2026-07-09"))
    monkeypatch.setattr(health, "fresh_future_date_max", lambda tour, now=None: None)
    monkeypatch.setattr(health, "charting_date_max", lambda tour: pd.Timestamp("2026-07-09"))
    monkeypatch.setattr(health, "load_matches", lambda tour: loads.append(tour) or fallback)
    now = pd.Timestamp("2026-07-09")

    health.write_health_manifest("atp", frame, now)
    assert health.tour_health("atp", now)["matches"] == 1
    assert loads == []

    fingerprint["value"] = "source-b"
    assert health.tour_health("atp", now)["matches"] == 2
    assert loads == ["atp"]


def test_main_strict_exit_code_and_report():
    from datetime import UTC, datetime
    today = pd.Timestamp(datetime.now(UTC).date())
    stale = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]),
                          "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
            health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
            health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: stale
            health.read_outputs = lambda tour: _oc()          # outputs clean; failure is source-side
            health.fresh_future_date_max = lambda tour, now=None: None
            health.fresh_date_max = lambda tour, now=None: today        # hermetic: no real data/raw reads
            health.charting_date_max = lambda tour: today
            health.OUTPUT_DIR = Path(d)
            health.WEB_DATA_DIR = Path(d) / "web"             # hermetic: no real web/ mirror
            health.TOURS = ("atp",)
            sys.argv = ["health", "--strict"]
            rc_strict = health.main()
            report = json.loads((Path(d) / "health.json").read_text())
            sys.argv = ["health"]
            rc_soft = health.main()
    finally:
        (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
         health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
         health.TOURS, sys.argv) = orig
    assert rc_strict == 1 and report["ok"] is False and report["tours"]["atp"]["problems"]
    assert report["tours"]["atp"]["output"]["matches"] == 300_000   # output snapshot persisted
    assert report["tours"]["atp"]["output"]["high_water_matches"] == 300_000
    assert report["tours"]["atp"]["output"]["high_water_match_population_version"] == \
        health.MATCH_POPULATION_VERSION
    assert rc_soft == 0                      # same problems, but only --strict reds the build
    # /health page contract: structured rows + precise stamp + forecast liveness detail
    assert [r["key"] for r in report["tours"]["atp"]["checks"]] == \
        ["results", "future_dates", "stats", "coverage", "fresh", "fresh_future", "charting",
         "espn_acquisition"]
    assert report["generatedAt"].endswith("Z") and "T" in report["generatedAt"]
    assert report["eventCoverage"]["atp"] == {
        "expectedKeys": ["espn:1-2026"],
        "shippedKeys": ["espn:1-2026", "espn:2-2026"],
    }
    assert report["tours"]["atp"]["output"]["forecast_max_as_of"] == "2026-07-09"
    print("ok test_main_strict_exit_code_and_report")


def test_main_surfaces_output_problems():
    """A clean source but a broken produced artifact must still red the build."""
    from datetime import UTC, datetime
    today = pd.Timestamp(datetime.now(UTC).date())
    fresh = pd.DataFrame({"date": pd.to_datetime([datetime.now(UTC).date()]),
                          "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
            health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
            health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: fresh
            health.read_outputs = lambda tour: _oc(missing=["tournaments"])
            health.fresh_future_date_max = lambda tour, now=None: None
            health.fresh_date_max = lambda tour, now=None: today        # hermetic: no real data/raw reads
            health.charting_date_max = lambda tour: today
            health.OUTPUT_DIR = Path(d)
            health.WEB_DATA_DIR = Path(d) / "web"             # hermetic: no real web/ mirror
            health.TOURS = ("atp",)
            sys.argv = ["health", "--strict"]
            rc = health.main()
            report = json.loads((Path(d) / "health.json").read_text())
    finally:
        (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
         health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
         health.TOURS, sys.argv) = orig
    assert rc == 1 and report["ok"] is False
    assert report["tours"]["atp"]["problems"] == []              # source was fine
    assert any("tournaments.json missing" in p for p in report["tours"]["atp"]["output"]["problems"])
    print("ok test_main_surfaces_output_problems")


def test_main_reports_a_stale_model_through_the_alert_path():
    """The check only earns its keep if it reaches a human. Output problems fold into
    health.json `ok`, which is exactly what .github/scripts/report-data-health.sh reads to
    open the data-health issue — so a dead retrain now pages, with no workflow change. The
    /health page's stamp rides along in output.model_trained_at."""
    from datetime import UTC, datetime, timedelta
    today = pd.Timestamp(datetime.now(UTC).date())
    fresh = pd.DataFrame({"date": pd.to_datetime([datetime.now(UTC).date()]),
                          "completed": [True], "has_stats": [True]})
    stale = _healthy_data()
    stale["meta"]["lastUpdated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    stale["meta"]["modelTrainedAt"] = (datetime.now(UTC) - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    orig = (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
            health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
            health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: fresh
            health.read_outputs = lambda tour: _oc(data=stale)
            health.fresh_future_date_max = lambda tour, now=None: None
            health.fresh_date_max = lambda tour, now=None: today
            health.charting_date_max = lambda tour: today
            health.OUTPUT_DIR = Path(d)
            health.WEB_DATA_DIR = Path(d) / "web"
            health.TOURS = ("atp",)
            sys.argv = ["health"]
            health.main()
            report = json.loads((Path(d) / "health.json").read_text())
    finally:
        (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
         health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
         health.TOURS, sys.argv) = orig
    out = report["tours"]["atp"]["output"]
    assert report["ok"] is False                                   # -> data-health issue opens
    assert any("model last retrained" in p for p in out["problems"]), out["problems"]
    assert out["model_trained_at"] == stale["meta"]["modelTrainedAt"]
    print("ok test_main_reports_a_stale_model_through_the_alert_path")


def test_gate_blocks_bad_output_without_writing_healthjson():
    """--gate reds the deploy on an integrity problem but must NOT clobber the sentinel's
    health.json, and must pass on internally-consistent output (fresh lastUpdated so the
    build-age check stays clean whatever the real date this runs)."""
    from datetime import UTC, datetime
    fresh_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    clean = _healthy_data(); clean["meta"]["lastUpdated"] = fresh_iso
    orig = (health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.OUTPUT_DIR = Path(d)
            health.TOURS = ("atp",)
            health.read_outputs = lambda tour: _oc(missing=["tournaments"])   # required JSON gone
            sys.argv = ["health", "--gate"]
            rc_bad = health.main()
            wrote_healthjson = (Path(d) / "health.json").exists()
            health.read_outputs = lambda tour: _oc(data=clean)                # internally consistent
            sys.argv = ["health", "--gate"]
            rc_ok = health.main()
    finally:
        health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv = orig
    assert rc_bad == 1                        # a broken build is blocked from deploying
    assert not wrote_healthjson               # the gate leaves the post-deploy sentinel's file alone
    assert rc_ok == 0                         # a clean build deploys
    print("ok test_gate_blocks_bad_output_without_writing_healthjson")


def test_gate_writes_an_atomic_structured_report_without_touching_sentinel():
    from datetime import UTC, datetime
    clean = _healthy_data()
    clean["meta"]["lastUpdated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    orig = (health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            health.OUTPUT_DIR = root
            health.TOURS = ("atp",)
            sentinel = root / "health.json"
            sentinel.write_text('{"sentinel":true}', encoding="utf-8")
            report_path = root / "ci" / "gate.json"
            health.read_outputs = lambda tour: _oc(missing=["tournaments"])
            sys.argv = ["health", "--gate", "--gate-report", str(report_path)]
            rc = health.main()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            untouched = sentinel.read_text(encoding="utf-8")
            health.read_outputs = lambda tour: _oc(data=clean)
            sys.argv = ["health", "--gate", "--gate-report", str(report_path)]
            rc_clean = health.main()
            recovered = json.loads(report_path.read_text(encoding="utf-8"))
    finally:
        health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv = orig
    assert rc == 1 and report["schema"] == "predeploy-gate-v1" and not report["ok"]
    assert report["blocking"] == [{"scope": "atp", "problem": "atp: tournaments.json missing"}]
    assert untouched == '{"sentinel":true}'
    assert rc_clean == 0 and recovered["ok"] is True and recovered["blocking"] == []


def test_gate_report_can_never_alias_health_json():
    orig = (health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.OUTPUT_DIR = Path(d)
            health.TOURS = ("atp",)
            health.read_outputs = lambda tour: _oc()
            target = Path(d) / "health.json"
            target.write_text("sentinel", encoding="utf-8")
            sys.argv = ["health", "--gate", "--gate-report", str(target)]
            rc = health.main()
            content = target.read_text(encoding="utf-8")
    finally:
        health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv = orig
    assert rc == 1 and content == "sentinel"


def test_gate_report_cannot_alias_the_deployed_health_mirror(monkeypatch, tmp_path):
    output = tmp_path / "output"; web = tmp_path / "web"
    target = web / "health.json"; target.parent.mkdir()
    target.write_text("deployed-sentinel", encoding="utf-8")
    monkeypatch.setattr(health, "OUTPUT_DIR", output)
    monkeypatch.setattr(health, "WEB_DATA_DIR", web)
    monkeypatch.setattr(health, "TOURS", ("atp",))
    monkeypatch.setattr(health, "read_outputs", lambda tour: _oc())
    monkeypatch.setattr(sys, "argv", ["health", "--gate", "--gate-report", str(target)])
    assert health.main() == 1
    assert target.read_text(encoding="utf-8") == "deployed-sentinel"


def test_gate_fails_closed_when_structured_report_cannot_be_published(monkeypatch, tmp_path):
    monkeypatch.setattr(health, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(health, "TOURS", ("atp",))
    monkeypatch.setattr(health, "read_outputs", lambda tour: _oc())
    monkeypatch.setattr(health, "_write_json_atomic",
                        lambda path, payload: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(sys, "argv", ["health", "--gate", "--gate-report",
                                      str(tmp_path / "gate.json")])
    assert health.main() == 1
    assert not (tmp_path / "gate.json").exists()


def test_atomic_json_write_preserves_previous_report_on_replace_failure(monkeypatch, tmp_path):
    target = tmp_path / "health.json"
    target.write_bytes(b'{"old":true}')
    monkeypatch.setattr(health.os, "replace",
                        lambda src, dst: (_ for _ in ()).throw(OSError("replace failed")))
    try:
        health._write_json_atomic(target, {"new": True})
    except OSError as exc:
        assert "replace failed" in str(exc)
    else:
        raise AssertionError("atomic publication failure was swallowed")
    assert target.read_bytes() == b'{"old":true}'
    assert not list(tmp_path.glob(".*.tmp"))


def test_gate_classifies_advisory_vs_blocking():
    """Provably-wrong output blocks the deploy; a thin/quirky schedule/rankings feed only warns
    (so a cosmetic naming split or a quiet week can't freeze the site)."""
    assert health._gate_blocks("wta: 'X' 'P0' champion=1.4 out of [0,1]")            # impossible number
    assert health._gate_blocks("atp: tournaments.json missing")                      # missing required JSON
    assert health._gate_blocks("wta: tournament 'X' aliveCount 99 > drawSize 32")    # structural break
    assert health._gate_blocks(
        "atp: begun tournament 'Wimbledon' (coverage key espn:188-2026) is represented only by a coverage shell")
    assert not health._gate_blocks(
        "wta: tournaments.json lists the same event more than once (Bad Homburg) — a naming/dedup split")
    assert not health._gate_blocks("atp: tournaments.json has no live/upcoming event")
    assert not health._gate_blocks(
        "wta: 40% of top players have no liveRank (max 30%) — rankings source may have drifted")
    print("ok test_gate_classifies_advisory_vs_blocking")


# --- produced-output validation (output_problems / read_outputs / format_issue_body) --
def test_output_healthy_is_clean():
    assert health.output_problems("atp", _oc(), NOW) == []
    print("ok test_output_healthy_is_clean")


def test_output_missing_and_corrupt_files():
    out = health.output_problems("atp", _oc(missing=["meta"], corrupt=["matrix"]), NOW)
    assert any("meta.json missing" in p for p in out)
    assert any("matrix.json is present but unparseable" in p for p in out)
    print("ok test_output_missing_and_corrupt_files")


def test_output_malformed_shard_indexes_fail_closed_without_crashing():
    d = _healthy_data()
    d["matrix-index"]["surfaces"] = ["not", "a", "mapping"]
    d["profile-index"]["generation"] = ""
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("matrix-index.json surfaces is missing/malformed" in problem for problem in out)
    assert any("profile-index.json is missing generation" in problem for problem in out)
    assert all(health._gate_blocks(problem) for problem in out
               if "matrix-index" in problem or "profile-index" in problem)


def test_output_feature_schema_drift():
    d = _healthy_data()
    d["meta"]["features"] = ["only", "three", "features"]
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("meta.features has 3 entries" in p for p in out)
    print("ok test_output_feature_schema_drift")


def test_output_method_missing_blocks():
    """method.json powers the /method detail sections; its absence must block the gate."""
    out = health.output_problems("atp", _oc(missing=["method"]), NOW)
    assert any("method.json missing" in p for p in out)
    assert all(health._gate_blocks(p) for p in out if "method.json" in p)
    print("ok test_output_method_missing_blocks")


def test_output_method_feature_count_drift():
    d = _healthy_data()
    d["method"]["combiner"]["featureCount"] = len(FEATURES) - 1
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any(f"featureCount {len(FEATURES) - 1} != {len(FEATURES)}" in p for p in out)
    assert any("!= meta.features" in p for p in out)
    print("ok test_output_method_feature_count_drift")


def test_output_method_out_of_range():
    d = _healthy_data()
    d["method"]["elo"]["surfaceBlend"] = 1.4          # a blend weight can't exceed 1
    d["method"]["tiers"]["kMult"]["atp250"] = 9.0     # a 9x tier K is nonsense
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("elo.surfaceBlend=1.4 out of range" in p for p in out)
    assert any("tiers.kMult implausible" in p for p in out)
    # a section vanishing entirely is a build bug, not a rendering choice
    d2 = _healthy_data(); del d2["method"]["combiner"]
    out2 = health.output_problems("atp", _oc(data=d2), NOW)
    assert any("missing section(s) combiner" in p for p in out2)
    print("ok test_output_method_out_of_range")


def test_output_model_age_flags_a_dead_retrain():
    """The production failure this check exists for: the daily full run is red, but the
    hourly quick refresh keeps exporting off the saved pickle — so `lastUpdated` stays
    fresh and every other invariant passes while the model behind the site rots."""
    d = _healthy_data()
    d["meta"]["lastUpdated"] = "2026-07-09T00:00:00Z"          # shipped an hour ago...
    d["meta"]["modelTrainedAt"] = "2026-07-04T00:00:00Z"       # ...off a 5-day-old model
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("model last retrained 5d ago" in p for p in out), out
    # the build-age check is structurally blind to this — it is why the outage ran 5 days
    assert not any("outputs last built" in p for p in out), out
    print("ok test_output_model_age_flags_a_dead_retrain")


def test_output_model_age_is_advisory_never_blocking():
    """A stale model still forecasts. Blocking the deploy would strand the site on an even
    older build, so this warns and ships (same policy as forecast drift)."""
    d = _healthy_data()
    d["meta"]["modelTrainedAt"] = "2026-06-01T04:30:00Z"
    out = [p for p in health.output_problems("atp", _oc(data=d), NOW) if "model last retrained" in p]
    assert out and not any(health._gate_blocks(p) for p in out), out
    print("ok test_output_model_age_is_advisory_never_blocking")


def test_output_model_age_missing_is_silent_and_fresh_is_clean():
    """A pickle predating the stamp exports modelTrainedAt=null; alerting on that would
    fire on every tour for one cycle and teach the reader to ignore the check. The next
    full retrain fills it in."""
    d = _healthy_data(); d["meta"]["modelTrainedAt"] = None
    assert health.output_problems("atp", _oc(data=d), NOW) == []
    d2 = _healthy_data(); del d2["meta"]["modelTrainedAt"]
    assert health.output_problems("atp", _oc(data=d2), NOW) == []
    # exactly at the ceiling is still fine — only strictly over alerts
    d3 = _healthy_data(); d3["meta"]["modelTrainedAt"] = "2026-07-06T00:00:00Z"   # exactly 3d
    assert not any("model last retrained" in p for p in health.output_problems("atp", _oc(data=d3), NOW))
    print("ok test_output_model_age_missing_is_silent_and_fresh_is_clean")


def test_output_match_floor_and_drop():
    low = _healthy_data(); low["meta"]["matches"] = 1000
    assert any("below floor" in p for p in health.output_problems("atp", _oc(data=low), NOW))
    # a silent source drop vs the prior run's snapshot
    dropped = health.output_problems(
        "atp", _oc(), NOW,
        prev={"matches": 400_000,
              "match_population_version": health.MATCH_POPULATION_VERSION})
    assert any("dropped 400000 -> 300000" in p for p in dropped)
    print("ok test_output_match_floor_and_drop")


def test_match_population_high_water_does_not_ratchet_down_after_a_regression():
    data = _healthy_data()
    data["meta"]["matches"] = 299_948
    legacy = {"matches": 300_000,
              "match_population_version": health.MATCH_POPULATION_VERSION}
    assert health._population_high_water("atp", data["meta"], legacy) == \
        (300_000, health.MATCH_POPULATION_VERSION)
    first = health.output_problems("atp", _oc(data=data), NOW, legacy)
    assert any("dropped 300000 -> 299948" in problem for problem in first)

    # Persisting the raw lower count must not make the identical bad output look recovered.
    persisted = {
        "matches": 299_948,
        "match_population_version": health.MATCH_POPULATION_VERSION,
        "high_water_matches": 300_000,
        "high_water_match_population_version": health.MATCH_POPULATION_VERSION,
    }
    repeat = health.output_problems("atp", _oc(data=data), NOW, persisted)
    assert any("dropped 300000 -> 299948" in problem for problem in repeat)

    data["meta"]["matches"] = 300_000
    assert not any("meta.matches dropped" in p
                   for p in health.output_problems("atp", _oc(data=data), NOW, persisted))
    data["meta"]["matches"] = 300_001
    assert health._population_high_water("atp", data["meta"], persisted) == \
        (300_001, health.MATCH_POPULATION_VERSION)


def test_match_population_version_boundary_is_the_only_high_water_reset():
    data = _healthy_data()
    data["meta"]["matches"] = 299_920
    previous = {
        "matches": 300_000,
        "match_population_version": health.MATCH_POPULATION_VERSION - 1,
        "high_water_matches": 300_000,
        "high_water_match_population_version": health.MATCH_POPULATION_VERSION - 1,
    }
    assert health._population_high_water("atp", data["meta"], previous) == \
        (299_920, health.MATCH_POPULATION_VERSION)
    assert not any("meta.matches dropped" in p
                   for p in health.output_problems("atp", _oc(data=data), NOW, previous))

    invalid = copy.deepcopy(data)
    invalid["meta"]["modelPopulationVersion"] = health.MATCH_POPULATION_VERSION - 1
    assert health._population_high_water("atp", invalid["meta"], previous) == \
        (300_000, health.MATCH_POPULATION_VERSION - 1)


def test_high_water_threshold_and_malformed_numeric_versions_are_pinned():
    previous = {
        "matches": 300_000,
        "match_population_version": health.MATCH_POPULATION_VERSION,
        "high_water_matches": 300_000,
        "high_water_match_population_version": health.MATCH_POPULATION_VERSION,
    }
    within = _healthy_data(); within["meta"]["matches"] = 299_950
    assert not any("meta.matches dropped" in p
                   for p in health.output_problems("atp", _oc(data=within), NOW, previous))
    outside = _healthy_data(); outside["meta"]["matches"] = 299_949
    assert any("dropped 300000 -> 299949" in p
               for p in health.output_problems("atp", _oc(data=outside), NOW, previous))

    malformed = copy.deepcopy(outside)
    malformed["meta"]["matchPopulationVersion"] = float(health.MATCH_POPULATION_VERSION)
    malformed["meta"]["modelPopulationVersion"] = float(health.MATCH_POPULATION_VERSION)
    assert health._population_high_water("atp", malformed["meta"], previous) == \
        (300_000, health.MATCH_POPULATION_VERSION)
    problems = health.output_problems("atp", _oc(data=malformed), NOW, previous)
    assert any("matchPopulationVersion" in p for p in problems)
    assert any("modelPopulationVersion" in p for p in problems)


def test_main_persists_high_water_across_repeated_bad_runs(tmp_path, monkeypatch):
    from datetime import UTC, datetime
    today = pd.Timestamp(datetime.now(UTC).date())
    fresh = pd.DataFrame({"date": pd.to_datetime([today]),
                          "completed": [True], "has_stats": [True]})
    data = _healthy_data()
    data["meta"].update(matches=299_948,
                        lastUpdated=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        modelTrainedAt=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    monkeypatch.setattr(health, "load_matches", lambda tour: fresh)
    monkeypatch.setattr(health, "read_outputs", lambda tour: _oc(
        data=data, forecast={"lines": 200, "max_as_of": str(today.date())}))
    monkeypatch.setattr(health, "fresh_date_max", lambda tour, now=None: today)
    monkeypatch.setattr(health, "fresh_future_date_max", lambda tour, now=None: None)
    monkeypatch.setattr(health, "charting_date_max", lambda tour: today)
    monkeypatch.setattr(health, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(health, "WEB_DATA_DIR", tmp_path / "web")
    monkeypatch.setattr(health, "TOURS", ("atp",))
    monkeypatch.setattr(sys, "argv", ["health"])
    (tmp_path / "health.json").write_text(json.dumps({"tours": {"atp": {"output": {
        "matches": 300_000,
        "match_population_version": health.MATCH_POPULATION_VERSION,
    }}}}), encoding="utf-8")

    assert health.main() == 0
    first = json.loads((tmp_path / "health.json").read_text(encoding="utf-8"))
    assert first["tours"]["atp"]["output"]["matches"] == 299_948
    assert first["tours"]["atp"]["output"]["high_water_matches"] == 300_000
    assert any("dropped 300000 -> 299948" in p
               for p in first["tours"]["atp"]["output"]["problems"])
    assert health.main() == 0
    second = json.loads((tmp_path / "health.json").read_text(encoding="utf-8"))
    assert second["tours"]["atp"]["output"]["high_water_matches"] == 300_000
    assert any("dropped 300000 -> 299948" in p
               for p in second["tours"]["atp"]["output"]["problems"])


def test_output_wta_125_policy_is_a_blocking_invariant():
    leaked = _healthy_data(); leaked["meta"]["wta125Matches"] = 31
    out = health.output_problems("wta", _oc(data=leaked), NOW)
    hits = [p for p in out if "WTA 125" in p]
    assert hits and all(health._gate_blocks(p) for p in hits), out

    missing = _healthy_data(); del missing["meta"]["wta125Matches"]
    out = health.output_problems("wta", _oc(data=missing), NOW)
    assert any("wta125Matches missing" in p for p in out), out
    missing_audit = _healthy_data(); del missing_audit["meta"]["excludedWta125Matches"]
    out = health.output_problems("wta", _oc(data=missing_audit), NOW)
    assert any("excludedWta125Matches missing/invalid" in p for p in out), out

    unknown = _healthy_data(); unknown["meta"]["excludedUnclassifiedWtaLiveMatches"] = 2
    out = [p for p in health.output_problems("wta", _oc(data=unknown), NOW)
           if "unclassified live match(es) withheld" in p]
    assert out and not any(health._gate_blocks(p) for p in out), out
    print("ok test_output_wta_125_policy_is_a_blocking_invariant")


def test_output_wta_dual_state_contract_is_blocking():
    threshold = health.WTA_DUAL_STATE_GATE_THRESHOLD
    d = _healthy_data()
    d["method"]["tour"] = "wta"
    d["method"]["stateGate"] = {
        "enabled": True, "minMainMatches": threshold,
        "trainingPopulation": "main-only", "enrichedRows": ["qualifying", "wta125"],
    }
    d["meta"]["dualStateThreshold"] = threshold
    d["meta"]["dualStateReady"] = True
    clean = health.output_problems("wta", _oc(data=d), NOW)
    assert not [p for p in clean if "dualState" in p or "stateGate" in p], clean

    missing_state = copy.deepcopy(d)
    missing_state["meta"]["dualStateReady"] = False
    out = health.output_problems("wta", _oc(data=missing_state), NOW)
    hits = [p for p in out if "dualStateReady" in p]
    assert hits and all(health._gate_blocks(p) for p in hits), out

    drift = copy.deepcopy(d)
    drift["method"]["stateGate"]["minMainMatches"] = threshold + 1
    out = health.output_problems("wta", _oc(data=drift), NOW)
    assert any("stateGate.minMainMatches" in p for p in out), out


def test_output_match_drop_resets_only_across_a_population_version_boundary():
    clean = _healthy_data()
    clean["meta"]["matches"] = 299_920
    clean["meta"]["excludedWta125Matches"] = 80
    # The deployed baseline predates the explicit population contract. This intentional
    # version boundary resets comparison exactly once; the first new report records v2.
    first = health.output_problems(
        "wta", _oc(data=clean), NOW,
        prev={"matches": 300_000, "match_population_version": 1})
    assert not any("meta.matches dropped" in p for p in first), first
    # Same-version comparisons resume immediately and retain the ordinary >50-row threshold.
    audited = health.output_problems(
        "wta", _oc(data=clean), NOW,
        prev={"matches": 300_000,
              "match_population_version": health.MATCH_POPULATION_VERSION})
    assert any("meta.matches dropped" in p for p in audited), audited
    print("ok test_output_match_drop_resets_only_across_a_population_version_boundary")


def test_output_model_population_must_match_current_data_population():
    stale = _healthy_data()
    stale["meta"]["modelPopulationVersion"] = health.MATCH_POPULATION_VERSION - 1
    out = health.output_problems("wta", _oc(data=stale), NOW)
    hits = [p for p in out if "modelPopulationVersion" in p]
    assert hits and all(health._gate_blocks(p) for p in hits), out

    missing = _healthy_data()
    del missing["meta"]["modelPopulationVersion"]
    out = health.output_problems("wta", _oc(data=missing), NOW)
    assert any("modelPopulationVersion" in p for p in out), out
    print("ok test_output_model_population_must_match_current_data_population")


def test_output_real_draw_must_be_standard_size():
    """A leaked 'TBD' (128->129, 28->29) or a name-resolution loss (28->27) lands outside
    the standard sizes and blocks; sanctioned bye-draws (Gstaad's 28, Masters 56/96...)
    are REAL tour draws and must pass (28 blocked a deploy on 2026-07-10)."""
    for bad in (130, 129, 29, 27):
        d = _healthy_data(); d["tournaments"][0]["drawSize"] = bad
        assert any("not a standard bracket size" in p
                   for p in health.output_problems("atp", _oc(data=d), NOW)), bad
    for ok in (28, 32, 48, 56, 96, 128):
        d = _healthy_data(); d["tournaments"][0]["drawSize"] = ok
        assert not any("bracket size" in p
                       for p in health.output_problems("atp", _oc(data=d), NOW)), ok
    print("ok test_output_real_draw_must_be_standard_size")


def test_output_completed_nonpower_of_two_is_fine():
    """A completed event's drawSize is len(field_pool) — 41 (main draw + qualifiers) is normal."""
    d = _healthy_data()
    d["tournaments"] = [{"name": "Halle", "status": "completed", "drawStatus": "final",
                         "drawSize": 41, "aliveCount": 1, "champion": "Someone", "projection": []}]
    d["brackets"] = []           # Halle-only scenario ships no ordered draw
    assert not any("bracket size" in p for p in health.output_problems("atp", _oc(data=d), NOW))


# --- /bracket payload invariants (sim/bracket.py -> brackets.json) --------------
def test_output_healthy_bracket_is_clean():
    assert health.output_problems("atp", _oc(), NOW) == []
    print("ok test_output_healthy_bracket_is_clean")


def test_output_bracket_rounds_must_halve():
    d = _healthy_data()
    d["brackets"][0]["rounds"][0]["matches"].append(          # SF now 3 matches -> doesn't halve
        {"a": "E", "b": "F", "seedA": None, "seedB": None, "winner": "a",
         "score": "6-0 6-0", "p": 0.7, "probSource": "model", "upset": False})
    assert any("must halve" in p or "not a power of two" in p or "round 0 has" in p
               for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_rounds_must_halve")


def test_output_bracket_live_final_cannot_be_decided():
    d = _healthy_data()
    d["brackets"][0]["status"] = "live"
    d["tournaments"][1]["status"] = "live"; d["tournaments"][1]["champion"] = None
    assert any("final match already decided" in p
               for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_live_final_cannot_be_decided")


def test_output_bracket_feeder_mismatch_blocks():
    d = _healthy_data()
    d["brackets"][0]["rounds"][1]["matches"][0]["a"] = "Z"    # SF winner A must feed the final
    assert any("not fed to next round" in p
               for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_feeder_mismatch_blocks")


def test_output_bracket_upset_flag_must_agree():
    d = _healthy_data()
    d["brackets"][0]["rounds"][0]["matches"][0]["upset"] = True   # p=0.8, winner a -> not an upset
    assert any("upset flag disagrees" in p
               for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_upset_flag_must_agree")


def test_output_bracket_champion_must_agree():
    d = _healthy_data()
    d["brackets"][0]["champion"] = "C"                        # final winner is A, not C
    assert any("!= champion" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    d2 = _healthy_data()
    d2["tournaments"][1]["champion"] = "C"                    # disagree with tournaments.json
    assert any("!= tournaments.json" in p
               for p in health.output_problems("atp", _oc(data=d2), NOW))
    print("ok test_output_bracket_champion_must_agree")


def test_output_bracket_champion_accent_is_not_a_mismatch():
    """The bracket slot carries the elo-canonical spelling; `champion` comes from the
    results winner_name. A diacritic-only difference (Nosková vs Noskova) is the same
    player and must NOT trip the cross-check (it would have blocked the deploy)."""
    d = _healthy_data()
    br = d["brackets"][0]
    br["rounds"][0]["matches"][0]["a"] = "Linda Nosková"   # bracket slot (canonical, accented)
    br["rounds"][1]["matches"][0]["a"] = "Linda Nosková"
    br["champion"] = "Linda Noskova"                        # results spelling (no accent)
    d["tournaments"][1]["champion"] = "Linda Noskova"
    assert not any("champion" in p and "!=" in p
                   for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_champion_accent_is_not_a_mismatch")


def test_output_bracket_drawsize_must_match_slots():
    d = _healthy_data()
    d["brackets"][0]["drawSize"] = 3                          # 4 non-bye round-0 slots, not 3
    assert any("round-0 slots but drawSize" in p
               for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_drawsize_must_match_slots")


def test_output_bracket_requires_source_neutral_provenance():
    d = _healthy_data()
    d["brackets"][0]["drawSource"] = None
    d["brackets"][0]["drawSourceId"] = None
    d["brackets"][0]["drawSourceUrl"] = None
    problems = health.output_problems("atp", _oc(data=d), NOW)
    assert any("invalid drawSource" in problem for problem in problems)
    assert any("missing drawSourceId" in problem for problem in problems)


def test_output_official_bracket_requires_provider_host_dates_and_strong_field_evidence():
    d = _healthy_data()
    bracket = d["brackets"][0]
    bracket.update({
        "drawSource": "atp", "drawSourceId": "123", "espnId": "1-2026",
        "drawSourceUrl": "https://wtafiles.wtatennis.com/wrong.pdf",
        "drawSourceStart": "2026-08-01", "drawSourceEnd": "2026-08-07",
        "drawEvidencePlayers": 2, "drawEvidenceFieldPlayers": 28,
    })
    problems = health.output_problems("atp", _oc(data=d), NOW)
    assert any("URL host" in problem for problem in problems)
    assert any("2/28" in problem and "minimum 75%" in problem for problem in problems)
    assert any("calendar overlap is too small" in problem for problem in problems)


def test_output_official_bracket_rejects_adjacent_event_date_overlap():
    d = _healthy_data()
    bracket = d["brackets"][0]
    bracket.update({
        "drawSource": "atp", "drawSourceId": "806", "espnId": "718-2026",
        "drawSourceUrl": "https://www.protennislive.com/posting/2026/806/mds.pdf",
        "drawSourceStart": "2026-08-01", "drawSourceEnd": "2026-08-13",
        "start": "2026-08-11", "end": "2026-08-24",
        "drawEvidencePlayers": 72, "drawEvidenceFieldPlayers": 83,
    })
    problems = health.output_problems("atp", _oc(data=d), NOW)
    hit = [problem for problem in problems if "calendar overlap is too small" in problem]
    assert hit and health._gate_blocks(hit[0]), problems


def test_output_one_official_draw_cannot_attach_to_multiple_espn_events():
    d = _healthy_data()
    first = d["brackets"][0]
    first.update({
        "drawSource": "atp", "drawSourceId": "806", "espnId": "421-2026",
        "drawSourceUrl": "https://www.protennislive.com/posting/2026/806/mds.pdf",
        "drawSourceStart": first["start"], "drawSourceEnd": first["end"],
        "drawEvidencePlayers": 4, "drawEvidenceFieldPlayers": 4,
    })
    second = copy.deepcopy(first)
    second.update(name="Adjacent Open", espnId="718-2026")
    d["brackets"].append(second)

    problems = health.output_problems("atp", _oc(data=d), NOW)
    hit = [problem for problem in problems if "attached to multiple ESPN events" in problem]
    assert hit and health._gate_blocks(hit[0]), problems
    assert "421-2026" in hit[0] and "718-2026" in hit[0]


def test_output_one_wikipedia_draw_cannot_attach_to_multiple_espn_events():
    d = _healthy_data()
    first = d["brackets"][0]
    first.update({
        "drawSource": "wikipedia", "espnId": "188-2026",
        "drawSourceId": "2026 Wimbledon Championships – Women's singles",
        "drawSourceUrl": "https://en.wikipedia.org/wiki/2026_Wimbledon_Women",
    })
    second = copy.deepcopy(first)
    second.update(name="US Open", espnId="189-2026")
    d["brackets"].append(second)

    problems = health.output_problems("wta", _oc(data=d), NOW)
    hit = [problem for problem in problems if "attached to multiple ESPN events" in problem]
    assert hit and all(health._gate_blocks(problem) for problem in hit), problems
    assert "188-2026" in hit[0] and "189-2026" in hit[0]


def test_output_retained_draw_cache_duplicate_is_blocking_even_when_old_event_is_not_displayed():
    source = {
        "source": "wikipedia",
        "sourceId": "2026 Wimbledon Championships – Women's singles",
        "sourceUrl": "https://en.wikipedia.org/wiki/2026_Wimbledon_Women",
        "slots": [f"P{i}" for i in range(8)],
    }
    cache = {
        "188-2026": {**source, "name": "Wimbledon", "espnId": "188-2026"},
        "189-2026": {**source, "name": "US Open", "espnId": "189-2026"},
    }

    problems = health.output_problems("wta", _oc(draw_cache=cache), NOW)
    hit = [problem for problem in problems if "tournament_draws.json" in problem]
    assert hit and health._gate_blocks(hit[0]), problems
    assert "188-2026" in hit[0] and "189-2026" in hit[0]


def test_output_bracket_early_draw_with_qualifiers_is_clean():
    """An early-captured draw carries unresolved 'Qualifier N' placeholders. tournaments.json
    drawSize counts them (field_pool = non-null slots), so the bracket check must too — else
    it false-positives (Gstaad blocked the 2026-07-13 deploy: 2 named + 26 qualifiers = 28)."""
    pend = lambda a=None, b=None: {"a": a, "b": b, "seedA": None, "seedB": None, "p": None,
                                   "probSource": None, "winner": None, "score": None, "upset": None}
    # real Gstaad shape: a 32-slot draw with 2 named + 26 qualifiers + 4 byes -> drawSize 28
    slots = (["Named One", "Named Two"] + [f"Qualifier {i}" for i in range(1, 27)] + [None] * 4)
    rounds = [{"round": "R32", "matches": [pend(slots[i], slots[i + 1]) for i in range(0, 32, 2)]}]
    for lab, n in (("R16", 8), ("QF", 4), ("SF", 2), ("F", 1)):
        rounds.append({"round": lab, "matches": [pend() for _ in range(n)]})
    d = _healthy_data()
    d["brackets"] = [{
        "name": "Gstaad", "surface": "Clay", "level": "ATP 250", "bestOf": 3,
        "start": "2026-07-14", "end": "2026-07-20", "status": "upcoming",
        "drawSize": 28, "bracketSize": 32, "champion": None, "runnerUp": None,
        "drawSource": "wikipedia", "drawSourceId": "Gstaad draw",
        "drawSourceUrl": "https://en.wikipedia.org/wiki/Gstaad_draw",
        "rounds": rounds,
    }]
    d["tournaments"] = [{"name": "Gstaad", "surface": "Clay", "level": "ATP 250",
                         "bestOf": 3, "status": "upcoming",
                         "drawStatus": "real", "drawSize": 28, "aliveCount": 28, "champion": None,
                         "coverageKey": "espn:7-2026", "hasBracket": True, "projection": []}]
    d["event_coverage"] = {
        "version": 1, "tour": "atp", "buildDate": "2026-07-09",
        "events": [{"key": "espn:7-2026", "espnId": "7-2026", "name": "Gstaad",
                    "start": "2026-07-14", "end": "2026-07-20",
                    "evidence": ["scheduled"], "players": ["Named One", "Named Two"]}],
        "shippedKeys": ["espn:7-2026"], "shellKeys": [],
    }
    assert health.output_problems("atp", _oc(data=d), NOW) == []     # fully clean, no false-positive
    print("ok test_output_bracket_early_draw_with_qualifiers_is_clean")


def test_output_bracket_prob_out_of_range_blocks():
    d = _healthy_data()
    d["brackets"][0]["rounds"][1]["matches"][0]["p"] = 1.2
    assert any("out of [0,1]" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_prob_out_of_range_blocks")


def test_output_bracket_prob_source_presence_coupled():
    d = _healthy_data()
    d["brackets"][0]["rounds"][1]["matches"][0]["probSource"] = None   # p set but source null
    assert any("presence mismatch" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_prob_source_presence_coupled")


def test_output_bracket_hasBracket_needs_entry():
    d = _healthy_data()
    d["brackets"] = []                                        # tournaments still claims hasBracket
    assert any("hasBracket but no brackets.json entry" in p
               for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_hasBracket_needs_entry")


def test_output_bracket_placeholder_token_leaks():
    d = _healthy_data()
    d["brackets"][0]["rounds"][0]["matches"][0]["b"] = "Qualifier"   # bare token = leak; "Qualifier 3" is fine
    assert any("placeholder" in p.lower() for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_bracket_placeholder_token_leaks")
    print("ok test_output_completed_nonpower_of_two_is_fine")


def test_output_alive_gt_draw_and_missing_champion():
    d = _healthy_data()
    d["tournaments"] = [{"name": "X", "status": "completed", "drawStatus": "final",
                         "drawSize": 32, "aliveCount": 99, "champion": None, "projection": []}]
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("aliveCount 99 > drawSize 32" in p for p in out)
    assert any("has no champion" in p for p in out)
    print("ok test_output_alive_gt_draw_and_missing_champion")


def test_output_draw_cannot_exceed_128():
    """A >128 field means qualifying players leaked into a Slam's main draw."""
    d = _healthy_data()
    d["tournaments"] = [{"name": "Wimbledon", "status": "completed", "drawStatus": "final",
                         "drawSize": 168, "aliveCount": 1, "champion": "Someone", "projection": []}]
    out = health.output_problems("wta", _oc(data=d), NOW)
    problem = next(p for p in out if "maximum 128-player draw" in p)
    assert health._gate_blocks(problem)
    print("ok test_output_draw_cannot_exceed_128")


def test_output_probability_and_monotonicity():
    d = _healthy_data()
    d["tournaments"][0]["projection"][0]["champion"] = 1.4          # out of [0,1]
    assert any("out of [0,1]" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    d2 = _healthy_data()
    d2["tournaments"][0]["projection"][0]["reach"]["F"] = 0.9       # F(0.9) > SF(0.8): rises
    assert any("not monotonically" in p for p in health.output_problems("atp", _oc(data=d2), NOW))
    print("ok test_output_probability_and_monotonicity")


def test_output_projection_none_round_is_tolerated():
    """A finalist is past the semis, so the live projector emits sf=None (round already
    determined) — that must NOT flag 'out of [0,1]'; only a PRESENT out-of-range value does."""
    d = _healthy_data()
    d["tournaments"][0]["projection"][0]["sf"] = None            # already past the SF
    assert not any("out of [0,1]" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    d2 = _healthy_data()
    d2["tournaments"][0]["projection"][0]["sf"] = 1.4            # present + impossible -> still caught
    assert any("sf=1.4 out of [0,1]" in p for p in health.output_problems("atp", _oc(data=d2), NOW))
    print("ok test_output_projection_none_round_is_tolerated")


def test_output_matrix_antisymmetry():
    shards = _healthy_shards()
    shards["matrix-hard-bo3.json"]["components"]["combiner"][1][0] = 0.6
    assert any("antisymmetric" in p for p in health.output_problems(
        "atp", _oc(shards=shards), NOW))
    print("ok test_output_matrix_antisymmetry")


def test_output_blocks_matches_outside_stable_event_bounds():
    d = _healthy_data()
    d["tournaments"][0].update({
        "espnId": "718-2026", "start": "2026-08-01", "end": "2026-08-10",
    })
    d["upcoming"] = [{
        "event": "Test Open", "espnId": "718-2026", "date": "2026-08-11",
        "playerA": "P0", "playerB": "P1", "pA": 0.7,
    }]
    d["fixtures"] = [{
        "event": "Test Open", "espnId": "718-2026", "date": "2026-07-31",
        "winner": "P0", "loser": "P1", "modelProb": 0.6, "upset": False,
    }]
    problems = health.output_problems("atp", _oc(data=d), NOW)
    hits = [problem for problem in problems if "outside 'Test Open' event bounds" in problem]
    assert len(hits) == 2 and all(health._gate_blocks(problem) for problem in hits)
    print("ok test_output_blocks_matches_outside_stable_event_bounds")


def test_output_placeholder_name_leak():
    """A projection row must name a person. The old check tested membership of a fixed word
    set, so the bare "TBD" was caught but the NUMBERED "Qualifier 30" walked through — which
    is the form real draws actually use, and why 22 of the DC Open's 24 projected "players"
    shipped unflagged. Both forms are caught now, via the same `is_real` the draw machinery
    and the modelFavorite check use."""
    for ghost in ("TBD", "Qualifier 30", "Lucky Loser", "Bye"):
        d = _healthy_data()
        d["tournaments"][0]["level"] = "ATP 500"          # a tier where board quality blocks
        d["tournaments"][0]["projection"][0]["name"] = ghost
        out = health.output_problems("atp", _oc(data=d), NOW)
        hit = [p for p in out if "draw placeholder(s) as players" in p]
        assert hit, (ghost, out)
        assert health._gate_blocks(hit[0]), ghost
        assert repr(ghost) in hit[0]
    # ...and the same leak on a small event warns instead of freezing the whole site
    d = _healthy_data()
    d["tournaments"][0]["level"] = "WTA 125"
    d["tournaments"][0]["projection"][0]["name"] = "Qualifier 30"
    hit = [p for p in health.output_problems("wta", _oc(data=d), NOW)
           if "draw placeholder(s) as players" in p]
    assert hit and not health._gate_blocks(hit[0]), hit
    print("ok test_output_placeholder_name_leak")


def _tourn(name, start, end, players):
    return {"name": name, "status": "completed", "drawStatus": "final", "drawSize": 32,
            "aliveCount": 1, "champion": "X", "start": start, "end": end,
            "projection": [{"name": p} for p in players]}


def test_output_duplicate_tournament_name():
    """A YoY sponsor rename the pipeline doesn't reconcile splits one event into two rows."""
    out = []
    health._tournament_name_problems(out, "wta", [
        _tourn("Bad Homburg", "2026-06-21", "2026-06-27", ["A", "B", "C"]),
        _tourn("Bad Homburg", "2026-06-22", "2026-06-27", ["A", "B", "D"]),
    ])
    assert any("same event more than once" in p for p in out), out
    print("ok test_output_duplicate_tournament_name")


def test_output_split_event_under_two_names():
    # different names, overlapping dates, >=3 shared players -> one event, two names
    out = []
    health._tournament_name_problems(out, "atp", [
        _tourn("Halle", "2026-06-15", "2026-06-21", ["A", "B", "C", "D"]),
        _tourn("Terra Wortmann Open", "2026-06-16", "2026-06-21", ["A", "B", "C", "E"]),
    ])
    assert any("one event under two names" in p for p in out), out
    print("ok test_output_split_event_under_two_names")


def test_output_distinct_events_are_clean():
    # concurrent DISTINCT events share no players (a player plays one event per week)
    out = []
    health._tournament_name_problems(out, "atp", [
        _tourn("Eastbourne", "2026-06-22", "2026-06-28", ["A", "B", "C"]),
        _tourn("Mallorca", "2026-06-22", "2026-06-27", ["D", "E", "F"]),
    ])
    assert out == [], out
    # consecutive events touch at ONE boundary day and share players (played both weeks) -> clean
    out2 = []
    health._tournament_name_problems(out2, "wta", [
        _tourn("Berlin", "2026-06-15", "2026-06-21", ["A", "B", "C", "D"]),
        _tourn("Bad Homburg", "2026-06-21", "2026-06-27", ["A", "B", "C", "D"]),
    ])
    assert out2 == [], out2
    print("ok test_output_distinct_events_are_clean")


def test_output_distinct_stable_ids_override_the_overlap_heuristic():
    """Calendar ranges overlap and players move between successive events.

    Toronto and Washington shared 13 players in production, but their distinct stable ids
    prove they are not one event under two names.  The name heuristic remains a fallback for
    id-less archive evidence; it must never overrule stronger identity.
    """
    toronto = _tourn("Toronto", "2026-08-02", "2026-08-14", ["A", "B", "C", "D"])
    washington = _tourn(
        "Mubadala DC Open", "2026-07-25", "2026-08-04", ["A", "B", "C", "E"],
    )
    toronto["espnId"] = "421-2026"
    washington["espnId"] = "888-2026"

    out = []
    health._tournament_name_problems(out, "atp", [toronto, washington])
    assert out == [], out

    toronto["espnId"] = washington["espnId"] = None
    health._tournament_name_problems(out, "atp", [toronto, washington])
    assert any("one event under two names" in p for p in out), out
    print("ok test_output_distinct_stable_ids_override_the_overlap_heuristic")


def test_output_concurrent_events_with_open_qualifying_are_clean():
    """Issue #9 (2026-07-24): Washington (WTA 500) and Memphis (WTA 250) run the same week
    with entirely different fields, but both draws were still mostly unfilled — so they
    "shared" 20 identical `Qualifier N` strings and zero actual players, and the gate
    reported them as one event under two names. Placeholders name nobody."""
    quali = [f"Qualifier {i}" for i in range(3, 23)]
    out = []
    health._tournament_name_problems(out, "wta", [
        _tourn("Mubadala Citi DC Open", "2026-07-25", "2026-08-03",
               ["Jessica Pegula", "Elina Svitolina", *quali]),
        _tourn("Memphis", "2026-07-25", "2026-08-03",
               ["Ekaterina Alexandrova", "Viktorija Golubic", *quali]),
    ])
    assert out == [], out
    # ...and a genuine split is still caught when the shared names are real players
    out2 = []
    health._tournament_name_problems(out2, "wta", [
        _tourn("Cincinnati", "2026-08-10", "2026-08-17",
               ["Jessica Pegula", "Elina Svitolina", "Iga Swiatek", *quali]),
        _tourn("Western & Southern Open", "2026-08-10", "2026-08-17",
               ["Jessica Pegula", "Elina Svitolina", "Iga Swiatek", *quali]),
    ])
    assert any("one event under two names" in p for p in out2), out2
    print("ok test_output_concurrent_events_with_open_qualifying_are_clean")


def test_output_split_event_caught_on_a_barely_filled_draw():
    """Excluding placeholders also drops the shared COUNT, so the >=3 rule alone would let
    a rename through on the day the draw drops (2 names in, 30 qualifiers). One field being
    wholly contained in the other is the same impossibility at any size."""
    quali = [f"Qualifier {i}" for i in range(1, 31)]
    out = []
    health._tournament_name_problems(out, "wta", [
        _tourn("Memphis", "2026-07-25", "2026-08-03", ["A. Player", "B. Player", *quali]),
        _tourn("Memphis Open", "2026-07-25", "2026-08-03", ["A. Player", "B. Player", *quali]),
    ])
    assert any("one event under two names" in p for p in out), out
    # a single real name in common is NOT enough — a late wildcard/alternate moving between
    # two concurrent events is legal, and a standing false red masks the next real problem
    out2 = []
    health._tournament_name_problems(out2, "wta", [
        _tourn("Washington", "2026-07-25", "2026-08-03", ["A. Player", "C. Player", *quali]),
        _tourn("Memphis", "2026-07-25", "2026-08-03", ["A. Player", "D. Player", *quali]),
    ])
    assert out2 == [], out2
    # and an all-placeholder draw must not be "contained" in every other event
    out3 = []
    health._tournament_name_problems(out3, "wta", [
        _tourn("Washington", "2026-07-25", "2026-08-03", quali),
        _tourn("Memphis", "2026-07-25", "2026-08-03", ["A. Player", "B. Player", *quali]),
    ])
    assert out3 == [], out3
    print("ok test_output_split_event_caught_on_a_barely_filled_draw")


def test_output_upcoming_and_fixtures_consistency():
    d = _healthy_data()
    d["upcoming"][0]["playerB"] = "P0"                             # identical players
    d["fixtures"][0]["upset"] = True                               # but modelProb 0.6 >= 0.5
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("identical players" in p for p in out)
    assert any("upset flag disagrees" in p for p in out)
    print("ok test_output_upcoming_and_fixtures_consistency")


def test_output_duplicate_fixture_result_is_blocking():
    """The 2026 Cincinnati WTA board shipped stable-source and ESPN copies of the
    same result under different event/round spellings, so /results counted it twice."""
    d = _healthy_data()
    d["fixtures"] = [
        {"date": "2026-08-16", "event": "Cincinnati", "round": "R64",
         "winner": "Shuai Zhang", "loser": "Opponent", "score": "7-6(5) 6-3",
         "modelProb": 0.6, "upset": False},
        {"date": "2026-08-16", "event": "Cincinnati Open", "round": "R32",
         "winner": "Zhang Shuai", "loser": "Opponent", "score": "7-6 6-3",
         "modelProb": 0.6, "upset": False},
    ]
    out = health.output_problems("wta", _oc(data=d), NOW)
    hit = [p for p in out if "duplicates one completed fixture" in p]
    assert hit and health._gate_blocks(hit[0]), out

    d["fixtures"][1]["date"] = "2026-08-17"
    assert not any("duplicates one completed fixture" in p
                   for p in health.output_problems("wta", _oc(data=d), NOW))

    # Archive sources can stamp a round-robin meeting and final rematch with the same
    # event start date. Distinct rounds within one stable event remain legitimate.
    d["fixtures"][1].update(date="2026-08-16", event="Cincinnati", round="F")
    assert not any("duplicates one completed fixture" in p
                   for p in health.output_problems("wta", _oc(data=d), NOW))
    print("ok test_output_duplicate_fixture_result_is_blocking")


def test_output_upcoming_round_must_match_its_bracket_slot():
    """When stable event identity and the exact player pair locate a bracket match,
    its round is factual. Cincinnati upcoming rows said R16 while the official bracket
    placed those same pairs in R32, and the old gate checked neither artifact together."""
    d = _healthy_data()
    d["upcoming"][0].update(espnId="1-2026", round="R16", playerA="Xiyu Wang")
    d["brackets"][0]["espnId"] = "1-2026"
    d["brackets"][0]["rounds"][0]["matches"][0].update(a="Wang Xiyu", b="P1")

    out = health.output_problems("atp", _oc(data=d), NOW)
    hit = [p for p in out if "upcoming round R16 disagrees with bracket round SF" in p]
    assert hit and health._gate_blocks(hit[0]), out

    d["upcoming"][0]["round"] = "SF"
    assert not any("upcoming round" in p and "disagrees with bracket round" in p
                   for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_upcoming_round_must_match_its_bracket_slot")


def test_output_fixture_round_must_match_its_bracket_slot():
    """A future completed-result round regression is independently visible because
    exported fixtures retain their event id and the bracket check gates the mismatch."""
    d = _healthy_data()
    d["fixtures"] = [{
        "date": "2026-08-16", "event": "Cincinnati", "espnId": "1-2026",
        "round": "R16", "winner": "P0", "loser": "P1", "score": "6-4 6-3",
        "modelProb": 0.6, "upset": False,
    }]
    d["brackets"][0]["espnId"] = "1-2026"
    d["brackets"][0]["rounds"][0]["matches"][0].update(a="P0", b="P1")

    out = health.output_problems("atp", _oc(data=d), NOW)
    hit = [p for p in out if "fixture round R16 disagrees with bracket round SF" in p]
    assert hit and health._gate_blocks(hit[0]), out

    d["fixtures"][0]["round"] = "SF"
    assert not any("fixture round" in p and "disagrees with bracket round" in p
                   for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_fixture_round_must_match_its_bracket_slot")


def test_output_surface_must_be_canonical_and_month_guess_is_advisory():
    """A non-canonical surface is a builder bug (the card, the per-surface Elo blend and
    /style all key off this exact string) -> blocking. A month-of-year GUESS is advisory:
    it is what shipped the DC Open, a hard court, priced on grass Elo — but for a genuinely
    new event with no archive row and no Wikipedia article it is the only answer there is,
    so blocking would freeze the site on events we simply don't know yet."""
    d = _healthy_data()
    d["tournaments"][0]["surface"] = "Astroturf"
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("not a canonical surface" in p for p in out), out
    assert health._gate_blocks(next(p for p in out if "not a canonical surface" in p))

    d = _healthy_data()
    d["tournaments"][0]["surfaceSource"] = "month"          # live event, surface guessed
    out = health.output_problems("atp", _oc(data=d), NOW)
    guess = [p for p in out if "is a month-of-year guess" in p]
    assert guess, out
    assert not health._gate_blocks(guess[0])
    # a COMPLETED event's month guess is not surfaced — its rows are archive-backed by then
    d = _healthy_data()
    d["tournaments"][1]["surfaceSource"] = "month"
    assert not any("month-of-year guess" in p
                   for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_surface_must_be_canonical_and_month_guess_is_advisory")


def test_output_surface_is_required():
    d = _healthy_data()
    d["tournaments"][0]["surface"] = None
    out = health.output_problems("atp", _oc(data=d), NOW)
    missing = [p for p in out if "has no surface" in p]
    assert missing and health._gate_blocks(missing[0]), out
    print("ok test_output_surface_is_required")


def test_output_best_of_matches_tour_and_tier():
    cases = [
        ("atp", "Grand Slam", 3, True, True),
        ("atp", "Grand Slam", 5, False, False),
        ("wta", "Grand Slam", 5, True, True),
        ("wta", "Grand Slam", 3, False, False),
        ("atp", "ATP 500", 5, True, True),
        ("atp", "ATP 250", 5, True, False),
        ("atp", "ATP Tour", 5, False, False),
    ]
    for tour, level, best_of, has_problem, blocks in cases:
        card = {
            "name": "Format Open", "surface": "Hard", "level": level,
            "bestOf": best_of, "status": "live", "drawStatus": "real",
            "drawSize": 32, "aliveCount": 16, "champion": None, "projection": [],
        }
        out: list[str] = []
        health._check_tournament(out, tour, card, NOW)
        problems = [p for p in out if "bestOf" in p]
        assert bool(problems) is has_problem, (tour, level, best_of, out)
        if problems:
            assert health._gate_blocks(problems[0]) is blocks, problems
    print("ok test_output_best_of_matches_tour_and_tier")


def test_output_completed_generic_tier_is_advisory_unless_coverage_only():
    card = {
        "name": "Generic Open", "surface": "Hard", "level": "ATP Tour", "bestOf": 3,
        "status": "completed", "drawStatus": "final", "drawSize": 32,
        "aliveCount": 1, "champion": "P0", "projection": [],
    }
    out: list[str] = []
    health._check_tournament(out, "atp", card, NOW)
    unresolved = [p for p in out if "tier did not resolve" in p]
    assert unresolved and not health._gate_blocks(unresolved[0]), out

    out = []
    health._check_tournament(out, "atp", {**card, "coverageOnly": True}, NOW)
    unresolved = [p for p in out if "tier did not resolve" in p]
    assert unresolved and health._gate_blocks(unresolved[0]), out
    print("ok test_output_completed_generic_tier_is_advisory_unless_coverage_only")


def test_output_coverage_only_card_is_gated_not_downgraded():
    d = _healthy_data()
    key = "espn:188-2026"
    d["tournaments"] = [{
        "name": "Wimbledon", "surface": None, "surfaceSource": "month",
        "level": "ATP Tour", "bestOf": 3, "status": "live", "drawStatus": "partial",
        "drawSize": None, "aliveCount": 1, "champion": None, "projection": [],
        "coverageOnly": True, "coverageKey": key, "hasBracket": False,
    }]
    d["brackets"] = []
    d["event_coverage"] = {
        "version": 1, "tour": "atp", "buildDate": "2026-07-09",
        "events": [{"key": key, "name": "Wimbledon", "espnId": "188-2026",
                    "start": "2026-06-29", "end": "2026-07-12",
                    "evidence": ["result"], "players": ["P0", "P1"]}],
        "shippedKeys": [key], "shellKeys": [key],
    }
    out = health.output_problems("atp", _oc(data=d), NOW)
    shell = [p for p in out if "represented only by a coverage shell" in p]
    missing_surface = [p for p in out if "has no surface" in p]
    month_guess = [p for p in out if "month-of-year guess" in p]
    unresolved = [p for p in out if "tier did not resolve" in p]
    assert shell and all(health._gate_blocks(p) for p in shell), out
    assert missing_surface and all(health._gate_blocks(p) for p in missing_surface), out
    assert month_guess and all(health._gate_blocks(p) and health._BELOW_TIER not in p
                               for p in month_guess), out
    assert unresolved and all(health._gate_blocks(p) for p in unresolved), out
    print("ok test_output_coverage_only_card_is_gated_not_downgraded")


def test_output_event_coverage_shell_keys_match_cards_and_report_each_shell():
    d = _healthy_data()
    d["event_coverage"]["shellKeys"] = ["espn:1-2026"]
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("shellKeys does not match" in p for p in out), out

    d = _healthy_data()
    keys = ["espn:shell-a", "espn:shell-b"]
    shells = []
    events = []
    for i, key in enumerate(keys):
        name = f"Shell Open {i}"
        shells.append({
            "name": name, "surface": "Hard", "level": "ATP Tour", "bestOf": 3,
            "status": "upcoming", "drawStatus": "partial", "drawSize": None,
            "aliveCount": 0, "champion": None, "projection": [], "coverageOnly": True,
            "coverageKey": key, "hasBracket": False,
        })
        events.append({"key": key, "name": name, "start": "2026-07-10",
                       "end": "2026-07-20", "evidence": ["scheduled"], "players": []})
    d["tournaments"] = shells
    d["brackets"] = []
    d["event_coverage"] = {
        "version": 1, "tour": "atp", "buildDate": "2026-07-09", "events": events,
        "shippedKeys": keys, "shellKeys": keys,
    }
    out = health.output_problems("atp", _oc(data=d), NOW)
    shell_problems = [p for p in out if "represented only by a coverage shell" in p]
    assert len(shell_problems) == 2, out
    assert all(health._gate_blocks(p) for p in shell_problems), shell_problems
    print("ok test_output_event_coverage_shell_keys_match_cards_and_report_each_shell")


def test_output_level_must_be_in_the_tour_vocabulary():
    """A tier outside the vocabulary means some source's dialect reached a card verbatim —
    the ATP board carried 'ATP 250 series' and 'C' beside 'ATP 250' as if they were three
    tiers. Blocking regardless of tier: it is a builder bug, not board quality."""
    d = _healthy_data()
    d["tournaments"][0]["level"] = "ATP 250 series"          # raw wiki prose
    out = health.output_problems("atp", _oc(data=d), NOW)
    prob = [p for p in out if "level vocabulary" in p]
    assert prob and health._gate_blocks(prob[0]), out

    d = _healthy_data()
    d["tournaments"][0]["level"] = "WTA 125"                 # the Generali Open symptom
    out = health.output_problems("atp", _oc(data=d), NOW)
    prob = [p for p in out if "belongs to the other tour" in p]
    assert prob and health._gate_blocks(prob[0]), out

    # a resolved, in-vocabulary tier is silent; the generic is advisory, not silent
    d = _healthy_data()
    d["tournaments"][0]["level"] = "ATP 500"
    assert not any("level" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    d["tournaments"][0]["level"] = "ATP Tour"
    out = health.output_problems("atp", _oc(data=d), NOW)
    unresolved = [p for p in out if "tier did not resolve" in p]
    assert unresolved and not health._gate_blocks(unresolved[0]), out
    print("ok test_output_level_must_be_in_the_tour_vocabulary")


def test_board_quality_severity_follows_the_event_tier():
    """500-and-above must never ship wrong; below that, warn. One obscure 125 freezing the
    whole site is the failure mode that cost 16 hours on 2026-07-27."""
    assert health._tier_blocks("ATP 500") and health._tier_blocks("WTA 500")
    assert health._tier_blocks("Grand Slam") and health._tier_blocks("Masters 1000")
    assert health._tier_blocks("WTA 1000") and health._tier_blocks("Tour Finals")
    for small in ("ATP 250", "WTA 250", "WTA 125", "Challenger", "ATP Tour", "WTA Tour",
                  "Olympics", "Davis/BJK Cup", None):
        assert not health._tier_blocks(small), small
    # the SAME problem blocks on a 500 and only warns on a 125
    msg = "atp: live tournament 'X' surface 'Grass' is a month-of-year guess — no archive"
    assert health._gate_blocks(health._tiered(msg, "ATP 500"))
    assert not health._gate_blocks(health._tiered(msg, "WTA 125"))
    assert health._tiered(msg, "WTA 125").endswith("[below the 500 tier — advisory]")

    # end to end through the real check: identical defect, opposite severity
    def _probs(level):
        d = _healthy_data()
        d["tournaments"][0].update(level=level, surfaceSource="month")
        return health.output_problems("atp", _oc(data=d), NOW)
    big = [p for p in _probs("ATP 500") if "month-of-year guess" in p]
    small = [p for p in _probs("ATP 250") if "month-of-year guess" in p]
    assert big and health._gate_blocks(big[0]), big
    assert small and not health._gate_blocks(small[0]), small
    print("ok test_board_quality_severity_follows_the_event_tier")


def test_upcoming_event_that_already_ended_or_never_started():
    """The mirror of the stuck-'live' check. Ending while never having gone live is
    impossible — the results never joined — so the card invites clicks on odds for a
    tournament that is already over. The started-but-not-live case only WARNS: ESPN start
    dates include qualifying, so a main draw legitimately reads upcoming for a day or two,
    and a Slam for its whole quali week."""
    def _card(level, start, end, status="upcoming"):
        d = _healthy_data()
        d["tournaments"][0].update(name="Future Open", status=status, level=level,
                                   start=start, end=end, champion=None)
        return health.output_problems("atp", _oc(data=d), NOW)

    # ended while still 'upcoming' -> blocks on a 500, warns on a 250
    big = [p for p in _card("ATP 500", "2026-06-20", "2026-06-27") if "already ended" in p]
    assert big and health._gate_blocks(big[0]), big
    small = [p for p in _card("ATP 250", "2026-06-20", "2026-06-27") if "already ended" in p]
    assert small and not health._gate_blocks(small[0]), small

    # started days ago, not yet ended -> advisory at EVERY tier (qualifying lag is normal)
    lag = [p for p in _card("ATP 500", "2026-07-01", "2026-07-30") if "has not flipped live" in p]
    assert lag and not health._gate_blocks(lag[0]), lag
    # ...and inside the grace window nothing fires at all
    quiet = _card("ATP 500", str(NOW.date()), "2026-08-30")
    assert not any("has not flipped live" in p or "already ended" in p for p in quiet), quiet
    print("ok test_upcoming_event_that_already_ended_or_never_started")


def test_lost_bracket_is_sentinel_only():
    """A live event that HAD a bracket and now doesn't means its cached Wikipedia draw is
    gone — the 2026-07-27 Wimbledon class, where the field then fell back to a noisy results
    union and padded to an impossible 256-slot bracket, taking the whole board down."""
    d = _healthy_data()
    d["tournaments"][0].update(name="Test Open", status="live", hasBracket=False)
    prev = {"bracket_events": ["test open"]}
    out = health.output_problems("atp", _oc(data=d), NOW, prev)
    hit = [p for p in out if "lost its bracket" in p]
    assert hit and not health._gate_blocks(hit[0]), out
    # the gate runs prev=None, so it can never see this at all
    assert not any("lost its bracket" in p
                   for p in health.output_problems("atp", _oc(data=d), NOW, None))
    # still has its bracket -> silent; and a COMPLETED event dropping it is not news
    d2 = _healthy_data()
    d2["tournaments"][0].update(name="Test Open", status="live", hasBracket=True)
    assert not any("lost its bracket" in p
                   for p in health.output_problems("atp", _oc(data=d2), NOW, prev))
    d3 = _healthy_data()
    d3["tournaments"][0].update(name="Test Open", status="completed", hasBracket=False,
                                champion="P0", aliveCount=1)
    assert not any("lost its bracket" in p
                   for p in health.output_problems("atp", _oc(data=d3), NOW, prev))
    print("ok test_lost_bracket_is_sentinel_only")


def test_calendar_complete_without_a_final_is_honest_not_a_bug():
    """An event can now be called over by its CALENDAR when the results feed never delivered
    a final — the alternative was Iasi sitting 'live' with three players alive for NINE days.
    That card admits the champion is unknown, so it warns. A completed card with no champion
    and no such explanation is still a builder bug and still blocks."""
    d = _healthy_data()
    d["tournaments"][1].update(champion=None, finalRecorded=False)
    out = health.output_problems("atp", _oc(data=d), NOW)
    hit = [p for p in out if "completed without a recorded final" in p]
    assert hit and not health._gate_blocks(hit[0]), out

    d = _healthy_data()
    d["tournaments"][1].update(champion=None)          # no explanation -> builder bug
    out = health.output_problems("atp", _oc(data=d), NOW)
    hit = [p for p in out if "has no champion" in p]
    assert hit and health._gate_blocks(hit[0]), out
    print("ok test_calendar_complete_without_a_final_is_honest_not_a_bug")


def test_one_identity_one_card():
    """Two cards sharing an espnId is the duplicate-event class, finally checkable. On
    2026-07-28 the WTA board shipped a 12-player 'Washington Dc' fragment beside the full
    'Mubadala DC Open' — one tournament, two cards, two different favourites. Blocking:
    coalescing merges BEFORE projecting, so a duplicate here means that merge failed and at
    least one card is built on a partial event."""
    d = _healthy_data()
    d["tournaments"][0]["espnId"] = "888-2026"
    d["tournaments"][1]["espnId"] = "888-2026"
    out = health.output_problems("atp", _oc(data=d), NOW)
    hit = [p for p in out if "ships on 2 cards" in p]
    assert hit and health._gate_blocks(hit[0]), out
    assert "888-2026" in hit[0]
    # distinct ids, and id-less cards (an archive-only event outside ESPN's window), are fine
    d = _healthy_data()
    d["tournaments"][0]["espnId"] = "1-2026"
    d["tournaments"][1]["espnId"] = "2-2026"
    assert not any("ships on" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    d = _healthy_data()
    for t in d["tournaments"]:
        t["espnId"] = None
    assert not any("ships on" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_one_identity_one_card")


def test_cross_tour_surface_split_is_flagged():
    """One venue, one week, one court: a combined event ships a card on each tour. When they
    disagree, one is provably wrong — and no per-tour check can see it. On 2026-07-27 BOTH
    tours shipped the DC Open as Grass in the hard-court swing and every invariant passed."""
    def _card(surface, **over):
        c = {"name": "Mubadala DC Open", "surface": surface, "status": "live",
             "start": "2026-07-27", "end": "2026-08-03"}
        c.update(over)
        return c

    outs = {"atp": _oc(data={"tournaments": [_card("Hard")]}),
            "wta": _oc(data={"tournaments": [_card("Grass")]})}
    probs = health.cross_tour_problems(outs)
    assert any("surface split across tours" in p for p in probs), probs
    assert not health._gate_blocks(probs[0])          # advisory: which side is wrong is unknown
    # agreeing boards are silent
    same = {"atp": _oc(data={"tournaments": [_card("Hard")]}),
            "wta": _oc(data={"tournaments": [_card("Hard")]})}
    assert health.cross_tour_problems(same) == []
    # same NAME in different weeks is a different event — never compared
    apart = {"atp": _oc(data={"tournaments": [_card("Hard")]}),
             "wta": _oc(data={"tournaments": [_card("Clay", start="2026-10-05",
                                                     end="2026-10-11")]})}
    assert health.cross_tour_problems(apart) == []
    # a one-sided board (no counterpart) is silent
    assert health.cross_tour_problems({"atp": _oc(data={"tournaments": [_card("Hard")]})}) == []
    print("ok test_cross_tour_surface_split_is_flagged")


def test_output_market_benchmark_freeze_is_flagged_advisory():
    """tennis-data dropped Pinnacle mid-Jan 2026 and the market benchmark silently
    stopped gaining rows while still claiming a current window. A matched-odds date
    trailing the scored matches by > HEALTH_MAX_MARKET_LAG_DAYS must flag — but stay
    ADVISORY (odds are a benchmark, never a deploy dependency)."""
    d = _healthy_data()
    d["market"] = {"oosEnd": "2026-07-06", "lastMatchedDate": "2026-01-13"}
    out = health.output_problems("atp", _oc(data=d), NOW)
    hits = [p for p in out if "market.json odds coverage" in p]
    assert hits, out
    assert all(not health._gate_blocks(p) for p in hits)
    # pre-census payloads (or a benchmark-less tour) lack the fields — never flag/crash
    d2 = _healthy_data()
    d2["market"] = {"years": [2012, 2026], "matched": 5}
    assert not any("market.json" in p for p in health.output_problems("atp", _oc(data=d2), NOW))
    print("ok test_output_market_benchmark_freeze_is_flagged_advisory")


def test_output_forecast_drift_flagged_advisory():
    """track.json's drift monitor says the model scores worse than its own stated
    confidence -> surface a "re-tune recommended" problem, but ADVISORY only (a
    re-tune recommendation must never block a deploy, same as the market benchmark)."""
    d = _healthy_data()
    d["track"]["matchForecasts"]["drift"] = {
        "status": "drift", "windowDays": 90, "n": 412,
        "logloss": 0.642, "expectedLogloss": 0.581, "d": 0.061, "se": 0.019, "t": 3.2}
    out = health.output_problems("atp", _oc(data=d), NOW)
    hits = [p for p in out if "forecast drift" in p]
    assert hits and "re-tune recommended" in hits[0], out
    assert all(not health._gate_blocks(p) for p in hits)
    # a young log ("insufficient"), a healthy window ("ok"), or an old cached
    # track.json with no drift block at all must never flag or crash
    for drift in ({"status": "insufficient", "n": 30}, {"status": "ok", "n": 400}, None):
        d2 = _healthy_data()
        if drift is None:
            del d2["track"]["matchForecasts"]["drift"]
        else:
            d2["track"]["matchForecasts"]["drift"] = drift
        assert not any("forecast drift" in p
                       for p in health.output_problems("atp", _oc(data=d2), NOW)), drift
    print("ok test_output_forecast_drift_flagged_advisory")


def test_output_forecast_log_stale_flagged_advisory():
    """A present-but-frozen forecast log means the track step is silently failing (or the
    daily persist push keeps losing) — flag it, but ADVISORY (eval history is never a
    build dependency). Absent/young logs stay silent: a fresh clone is legitimate."""
    stale = health.output_problems(
        "atp", _oc(forecast={"lines": 200, "max_as_of": "2026-06-20"}), NOW)
    hits = [p for p in stale if "forecast log last advanced" in p]
    assert hits, stale
    assert all(not health._gate_blocks(p) for p in hits)
    # off-season: no upcoming matches -> no appends -> relaxed
    assert not any("last advanced" in p for p in health.output_problems(
        "atp", _oc(forecast={"lines": 200, "max_as_of": "2026-11-25"}),
        pd.Timestamp("2026-12-15")))
    # absent log / unparseable max_as_of: silent, no crash
    assert not any("last advanced" in p
                   for p in health.output_problems("atp", _oc(forecast=None), NOW))
    assert not any("last advanced" in p for p in health.output_problems(
        "atp", _oc(forecast={"lines": 0, "max_as_of": None}), NOW))
    print("ok test_output_forecast_log_stale_flagged_advisory")


def test_main_reports_problems_changed():
    """The hourly report step dedups on problems_changed: True on the first failure (no
    prev health.json), False while the problem set is identical, True when it shifts."""
    from datetime import UTC, datetime
    today = pd.Timestamp(datetime.now(UTC).date())
    stale = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]),
                          "completed": [True], "has_stats": [True]})
    staler = pd.DataFrame({"date": pd.to_datetime(["2025-06-01"]),
                           "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
            health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
            health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.read_outputs = lambda tour: _oc()
            health.fresh_future_date_max = lambda tour, now=None: None
            health.fresh_date_max = lambda tour, now=None: today
            health.charting_date_max = lambda tour: today
            health.OUTPUT_DIR = Path(d)
            health.WEB_DATA_DIR = Path(d) / "web"
            health.TOURS = ("atp",)
            sys.argv = ["health"]
            health.load_matches = lambda tour: stale
            health.main()
            first = json.loads((Path(d) / "health.json").read_text())
            health.main()
            second = json.loads((Path(d) / "health.json").read_text())
            health.load_matches = lambda tour: staler         # problem strings shift
            health.main()
            third = json.loads((Path(d) / "health.json").read_text())
            mirrored = json.loads((Path(d) / "web" / "health.json").read_text())
    finally:
        (health.load_matches, health.read_outputs, health.fresh_date_max, health.fresh_future_date_max,
         health.charting_date_max, health.OUTPUT_DIR, health.WEB_DATA_DIR,
         health.TOURS, sys.argv) = orig
    assert first["ok"] is False and first["problems_changed"] is True
    assert second["problems_changed"] is False
    assert third["problems_changed"] is True
    # the /health page's copy is the same report, mirrored on every sentinel run
    assert mirrored == third
    print("ok test_main_reports_problems_changed")


def test_output_track_and_forecast_monotonicity():
    d = _healthy_data(); d["track"]["matchForecasts"]["graded"] = 99
    assert any("graded+pending" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    shrank = health.output_problems("atp", _oc(forecast={"lines": 100, "max_as_of": "x"}),
                                    NOW, prev={"forecast_lines": 200})
    assert any("forecast log shrank 200 -> 100" in p for p in shrank)
    print("ok test_output_track_and_forecast_monotonicity")


def test_output_emptiness_is_season_gated():
    d = _healthy_data(); d["upcoming"] = []; d["tournaments"] = []
    assert any("upcoming feed is empty" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    # in the Nov/Dec off-season the tours are dark — empty schedules must NOT red the build
    dec = pd.Timestamp("2026-12-15")
    assert not any("empty" in p for p in health.output_problems("atp", _oc(data=d), dec))
    print("ok test_output_emptiness_is_season_gated")


def test_upcoming_v2_index_and_shards_are_one_gated_graph():
    d = _healthy_data()
    base = {
        "matchId": "v2|espn:1-2026|2026|R32|p0|p1",
        "event": "Test Open", "espnId": "1-2026", "date": "2026-07-09",
        "round": "R32", "surface": "Grass", "bestOf": 3, "level": "ATP 250",
        "playerA": "P0", "playerB": "P1", "pA": 0.7,
        "watch": _healthy_watch(), "watchRank": 1,
    }
    detail = {
        "matchId": base["matchId"],
        "components": {"eloBlend": 0.68, "pointModel": 0.72, "combiner": 0.7},
        "evidence": _healthy_evidence(), "forecast": None,
    }
    d["upcoming-index"] = {
        "schema": "upcoming-v2", "schemaVersion": 2, "generation": "g", "count": 1,
        "events": [{"name": "Test Open", "espnId": "1-2026", "surface": "Grass",
                    "level": "ATP 250", "count": 1, "file": "upcoming-event-1.json",
                    "evidenceFile": "upcoming-evidence-1.json"}],
        "highlights": [{**base, "watch": {"score": 45.5}}],
    }
    shards = {
        "upcoming-event-1.json": {"schema": "upcoming-event-v1", "generation": "g",
                                  "matches": [base]},
        "upcoming-evidence-1.json": {"schema": "upcoming-evidence-v1", "generation": "g",
                                     "details": [detail]},
    }
    out = health.output_problems("atp", _oc(data=d, shards=shards), NOW)
    assert not any("upcoming-index" in problem or "match/detail identities" in problem
                   for problem in out)

    broken = copy.deepcopy(shards)
    broken["upcoming-evidence-1.json"]["details"] = []
    out = health.output_problems("atp", _oc(data=d, shards=broken), NOW)
    assert any("match/detail identities disagree" in problem for problem in out)


def test_output_liverank_drift_is_season_gated():
    d = _healthy_data()
    for p in d["players"]:
        p["liveRank"] = None                                       # rankings source vanished
    assert any("liveRank" in x for x in health.output_problems("atp", _oc(data=d), NOW))
    dec = pd.Timestamp("2026-12-15")
    assert not any("liveRank" in x for x in health.output_problems("atp", _oc(data=d), dec))
    print("ok test_output_liverank_drift_is_season_gated")


def test_output_player_enrichment_fields_gated():
    """Present-but-insane enrichment values (junk height, a 64.2 units slip for 0.642)
    must BLOCK; absent/null fields never flag (old snapshots lack the keys)."""
    d = _healthy_data()
    d["players"][0]["heightCm"] = 641                              # junk height
    d["players"][1]["servePctHard"] = 64.2                         # percent instead of fraction
    d["players"][2]["winRate10"] = 1.4                             # not a probability
    out = health.output_problems("atp", _oc(data=d), NOW)
    height_hits = [p for p in out if "heightCm" in p]
    pct_hits = [p for p in out if "out of [0,1]" in p and "players.json" in p]
    assert height_hits and pct_hits, out
    assert all(health._gate_blocks(p) for p in height_hits + pct_hits)
    # nulls and absent keys are the nullable-by-design path -> clean
    d2 = _healthy_data()
    d2["players"][0]["heightCm"] = None
    d2["players"][1]["winRate10"] = None
    for k in ("servePctHard", "servePctClay", "servePctGrass",
              "returnPctHard", "returnPctClay", "returnPctGrass",
              "heightCm", "winRate10"):
        d2["players"][2].pop(k, None)
    assert health.output_problems("atp", _oc(data=d2), NOW) == []
    print("ok test_output_player_enrichment_fields_gated")


def test_output_kalshi_ledger_clean_and_unscored_ignored():
    """Clean scored rows pass; unscored rows (pending, degraded price, no p_model)
    are outside the scorecard and never flagged even with wild timestamps."""
    rows = [_ledger_row(),
            _ledger_row(event_ticker="K2", match_status="pending",
                        price_ts="2026-07-08T12:55:00Z", result_date="", a_won=""),
            _ledger_row(event_ticker="K3", price_kind="none", p_kalshi="",
                        price_ts="2026-07-08T16:00:00Z")]
    assert health.output_problems("atp", _oc(kalshi_ledger=rows), NOW) == []
    print("ok test_output_kalshi_ledger_clean_and_unscored_ignored")


def test_output_kalshi_ledger_post_anchor_quote_blocks():
    """A scored quote stamped after 08:00 on its result date is the pending-race
    occurrence-anchor escape (possibly in-play) — must block the deploy."""
    rows = [_ledger_row(price_ts="2026-07-08T12:55:00Z")]
    out = health.output_problems("atp", _oc(kalshi_ledger=rows), NOW)
    assert any("quoted after its 08:00 anchor" in p for p in out)
    assert all(health._gate_blocks(p) for p in out)
    print("ok test_output_kalshi_ledger_post_anchor_quote_blocks")


def test_output_kalshi_ledger_settled_carry_blocks():
    """A window-edge carry candle with a settled-extreme mid is a post-result print;
    the same carry with a live two-sided mid is a quiet overnight book (fine)."""
    bad = [_ledger_row(price_ts="2026-07-08T04:00:00Z",
                       mid_a="0.9950", mid_b="0.0050", p_kalshi="0.9950")]
    out = health.output_problems("atp", _oc(kalshi_ledger=bad), NOW)
    assert any("settled-extreme window-edge quote" in p for p in out)
    ok = [_ledger_row(price_ts="2026-07-08T04:00:00Z")]
    assert health.output_problems("atp", _oc(kalshi_ledger=ok), NOW) == []
    print("ok test_output_kalshi_ledger_settled_carry_blocks")


def test_output_kalshi_ledger_settlement_disagreement_blocks():
    """Kalshi settling the market for the OTHER player than the joined result is a
    provably mis-joined row (the FRIZVE/Halle chimera signature)."""
    rows = [_ledger_row(kalshi_result_a="yes")]                    # a lost, settled yes
    out = health.output_problems("atp", _oc(kalshi_ledger=rows), NOW)
    assert any("settlement contradicts" in p for p in out)
    print("ok test_output_kalshi_ledger_settlement_disagreement_blocks")


def test_output_kalshi_ledger_double_scored_result_blocks():
    """One (pair, result_date) scored under two tickers = one match counted twice."""
    rows = [_ledger_row(),
            _ledger_row(event_ticker="KXATPMATCH-26JUL09AAABBB")]
    out = health.output_problems("atp", _oc(kalshi_ledger=rows), NOW)
    assert any("scores one result twice" in p for p in out)
    print("ok test_output_kalshi_ledger_double_scored_result_blocks")


def test_read_outputs_detects_missing_and_corrupt(tmp_path=None):
    orig = (health.output_dir, health.DATA_DIR, health.live_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "atp").mkdir()
            (root / "raw" / "atp").mkdir(parents=True)
            (root / "atp" / "meta.json").write_text('{"matches": 1}')
            (root / "atp" / "tournaments.json").write_text("{ not json")
            (root / "raw" / "atp" / "tournament_draws.json").write_text(
                '{"1-2026":{"espnId":"1-2026","source":"wikipedia",'
                '"sourceId":"Draw","sourceUrl":"https://en.wikipedia.org/wiki/Draw"}}')
            health.output_dir = lambda tour: root / tour
            health.live_dir = lambda tour: root / "raw" / tour
            health.DATA_DIR = root
            oc = health.read_outputs("atp")
    finally:
        health.output_dir, health.DATA_DIR, health.live_dir = orig
    assert "meta" in oc["data"] and oc["data"]["meta"]["matches"] == 1
    assert "1-2026" in oc["draw_cache"]
    assert "tournaments" in oc["corrupt"]
    assert "players" in oc["missing"] and "upcoming-index" in oc["missing"]
    assert oc["forecast"] is None                                  # no forecast_log in the temp root
    print("ok test_read_outputs_detects_missing_and_corrupt")


def test_read_outputs_flags_nan_as_corrupt():
    """json.loads accepts the bare NaN token but the browser's JSON.parse rejects it — a
    NaN that ships blanks the page (the WTA /player,/style regression: a scoreless match
    left "score": NaN in profiles.json). The gate must treat such a file as unparseable."""
    orig = (health.output_dir, health.DATA_DIR, health.live_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "atp").mkdir()
            (root / "atp" / "meta.json").write_text('{"matches": 1}')
            (root / "atp" / "profile-index.json").write_text(
                '{"generation":"g","profiles":[{"name":"P","file":"profile-p.json"}]}')
            # a real scoreless-match row, exactly as json.dump would have emitted it
            (root / "atp" / "profile-p.json").write_text(
                '{"generation":"g","name":"P","recent":[{"score": NaN}]}')
            health.output_dir = lambda tour: root / tour
            health.live_dir = lambda tour: root / "raw" / tour
            health.DATA_DIR = root
            oc = health.read_outputs("atp")
    finally:
        health.output_dir, health.DATA_DIR, health.live_dir = orig
    assert "profile-p.json" in oc["corrupt_files"] and "profile-p.json" not in oc["shards"]
    # and output_problems surfaces it through the existing unparseable channel
    assert any("profile-p.json" in p and "unparseable" in p
               for p in health.output_problems("atp", oc, NOW))
    print("ok test_read_outputs_flags_nan_as_corrupt")


def test_format_issue_body_has_problems_and_fix_prompt():
    report = {"generated": "2026-07-09", "ok": False,
              "tours": {"wta": {"problems": ["wta: newest completed match is 9d old"],
                                "output": {"problems": ["wta: tournaments.json is empty"]}}}}
    body = health.format_issue_body(report, run_url="https://example/run/1",
                                    health_url="https://example.github.io/site/health/")
    assert "newest completed match is 9d old" in body
    assert "tournaments.json is empty" in body
    assert "https://example/run/1" in body
    assert "Live status page: https://example.github.io/site/health/" in body
    assert "new Claude Code session" in body and "data-health" in body
    # both links are optional (local runs / a deploy-less context) — never rendered empty
    bare = health.format_issue_body(report)
    assert "Live status page" not in bare and "Failing run" not in bare
    print("ok test_format_issue_body_has_problems_and_fix_prompt")


def test_output_stale_live_event_severity_follows_the_event_tier():
    """The real Iasi card (2026-07-27): status live, champion null, 3 alive — nine days
    after it ended. `completed` is set ONLY by a round-"F" row, so a results feed that
    drops the final strands the event at the top of the board forever. The producer fix has
    now stayed quiet through successive real refreshes, so the normal board-quality tier
    policy applies: a marquee event blocks while the long tail warns."""
    def _problems(level):
        d = _healthy_data()
        d["tournaments"] = [dict(d["tournaments"][0], name="Iasi", status="live",
                                 level=level, drawStatus="seeded", drawSize=34, aliveCount=3,
                                 champion=None, end="2026-06-30")]     # NOW is 2026-07-09
        return [p for p in health.output_problems("atp", _oc(data=d), NOW)
                if "last played" in p]

    big = _problems("ATP 500")
    small = _problems("ATP 250")
    assert big and "9d ago" in big[0] and health._gate_blocks(big[0]), big
    assert small and not health._gate_blocks(small[0]), small
    # a normally in-progress event is silent
    d2 = _healthy_data()
    d2["tournaments"] = [dict(d2["tournaments"][0], status="live", champion=None,
                              end="2026-07-08")]
    assert not any("last played" in p for p in health.output_problems("atp", _oc(data=d2), NOW))
    d3 = _healthy_data()
    d3["tournaments"] = [dict(d3["tournaments"][0], name="Hagen", status="live",
                              level="Challenger", champion=None, end="2026-07-01",
                              dateBasis="start")]
    assert not any("last played" in p for p in health.output_problems("atp", _oc(data=d3), NOW))
    print("ok test_output_stale_live_event_severity_follows_the_event_tier")


def test_output_drawn_player_missing_from_the_feed_blocks():
    """The gate half of the withdrawal class. Eliminations come from loser rows, so a player
    who leaves without losing is invisible to every other check — Auger-Aliassime shipped as
    Toronto's FAVOURITE at 14.3% having never played there. The producer derives the list
    (only it can reconcile draw spellings against the feed); the gate refuses to ship it."""
    def _problems(level, missing):
        d = _healthy_data()
        d["tournaments"] = [dict(d["tournaments"][0], name="Toronto", status="live",
                                 level=level, champion=None, drawnNotInField=missing)]
        return [p for p in health.output_problems("atp", _oc(data=d), NOW)
                if "no longer lists" in p]

    hits = _problems("Masters 1000", ["Felix Auger-Aliassime"])
    assert hits and "Felix Auger-Aliassime" in hits[0], hits
    assert health._gate_blocks(hits[0]), "a marquee board must not ship a phantom entrant"
    assert not _problems("Masters 1000", []), "a clean draw is silent"
    # Absent key = a build from before this shipped; it must not read as a problem.
    d = _healthy_data()
    d["tournaments"] = [dict(d["tournaments"][0], status="live", champion=None)]
    d["tournaments"][0].pop("drawnNotInField", None)
    assert not [p for p in health.output_problems("atp", _oc(data=d), NOW)
                if "no longer lists" in p]
    print("ok test_output_drawn_player_missing_from_the_feed_blocks")


def test_a_tournament_stamped_feed_is_exempt_but_nothing_else_is():
    """Hagen, 2026-08-08: 28 rows across R32/R16/QF all dated 08-03, so a live event playing
    its quarter-finals read as five days idle. `end` is the tournament's start there, and
    ageing it measures nothing — the signal is absent, not coarse, so the check is skipped
    rather than given a slack limit that would pretend otherwise.

    The exemption is per card and must be EARNED. A card whose dates are real match dates
    keeps the full-strength check, or one badly-dated feed would blind the invariant that
    caught Toronto."""
    def _problems(basis):
        d = _healthy_data()
        d["tournaments"] = [dict(d["tournaments"][0], name="Hagen", status="live",
                                 level="ATP 250", champion=None, end="2026-07-04",
                                 dateBasis=basis)]        # NOW is 2026-07-09 -> 5 idle days
        return [p for p in health.output_problems("atp", _oc(data=d), NOW)
                if "last played" in p]

    assert not _problems("start"), "a tournament-stamped card must not be aged"
    assert _problems("match"), "a match-dated card keeps the full-strength check"
    # An absent key is an older build, and must NOT silently buy the exemption.
    d = _healthy_data()
    d["tournaments"] = [dict(d["tournaments"][0], name="Hagen", status="live",
                             level="ATP 250", champion=None, end="2026-07-04")]
    d["tournaments"][0].pop("dateBasis", None)
    assert [p for p in health.output_problems("atp", _oc(data=d), NOW) if "last played" in p]
    print("ok test_a_tournament_stamped_feed_is_exempt_but_nothing_else_is")


def test_output_live_event_with_a_stalled_results_feed_blocks():
    """Regression for 2026-08-05: ESPN began 403-ing the live overlay's User-Agent, ATP
    results froze at 08-04, and Toronto shipped Zverev at 21% to win a title Griekspoor had
    already knocked him out of — for three days, with the gate green the whole time.

    The tour-wide `results` freshness check cannot catch this: its limit is 5 days and it is
    dominated by finished events, so one stalled tournament never moves it. Only the
    per-event check sees it, and it must fire at three idle days — the age this actually
    reached — not four, which is what the old off-by-one limit of 3 allowed."""
    def _toronto(end: str, level: str = "Masters 1000"):
        d = _healthy_data()
        d["tournaments"] = [dict(d["tournaments"][0], name="Toronto", status="live",
                                 level=level, drawSize=96, aliveCount=79, champion=None,
                                 end=end)]
        return [p for p in health.output_problems("atp", _oc(data=d), NOW)
                if "last played" in p]

    stalled = _toronto("2026-07-06")            # NOW is 2026-07-09 -> 3 idle days
    assert stalled, "a live draw idle for three days must fire"
    assert "results feed has stalled" in stalled[0], stalled
    assert health._gate_blocks(stalled[0]), "a Masters 1000 board must not ship stale"

    # A rest or washed-out day is normal and must stay silent, so the limit is the first age
    # a real tour week cannot explain — not a blanket alarm on every live event.
    for playing in ("2026-07-09", "2026-07-08", "2026-07-07"):
        assert not _toronto(playing), playing
    print("ok test_output_live_event_with_a_stalled_results_feed_blocks")


def test_output_completed_event_with_many_alive_is_flagged():
    """The real Palermo card: completed, champion 'Francesca Jones', aliveCount 32 of 32.
    The authoritative draw supplied the field while the results supplied the eliminations
    and the two never joined — a finished event has exactly one player standing. The fixed
    ingestion is quiet, so this now follows the same tier policy as other board defects."""
    def _problems(level):
        d = _healthy_data()
        d["tournaments"] = [dict(d["tournaments"][0], name="Palermo", status="completed",
                                 level=level, drawStatus="final", drawSize=32, aliveCount=32,
                                 champion="Francesca Jones", end="2026-07-08")]
        return [p for p in health.output_problems("atp", _oc(data=d), NOW)
                if "players alive (expected 1)" in p]

    big = _problems("ATP 500")
    small = _problems("ATP 250")
    assert big and "32 players alive" in big[0] and health._gate_blocks(big[0]), big
    assert small and not health._gate_blocks(small[0]), small
    print("ok test_output_completed_event_with_many_alive_is_flagged")


def test_output_numbered_qualifier_as_model_favourite_is_flagged():
    """`_flag_placeholders` matches a fixed word set, so the NUMBERED form slipped through
    and Palermo shipped modelFavorite 'Qualifier 30'. The check now delegates to the draw
    machinery's own is_real predicate, which already understands that form."""
    d = _healthy_data()
    d["tournaments"] = [dict(d["tournaments"][0], modelFavorite="Qualifier 30")]
    out = health.output_problems("atp", _oc(data=d), NOW)
    bad = [p for p in out if "is a draw placeholder" in p]
    assert bad, out
    assert not any(health._gate_blocks(p) for p in bad)
    # a real name is silent
    d2 = _healthy_data()
    d2["tournaments"] = [dict(d2["tournaments"][0], modelFavorite="P0")]
    assert not any("is a draw placeholder" in p
                   for p in health.output_problems("atp", _oc(data=d2), NOW))
    print("ok test_output_numbered_qualifier_as_model_favourite_is_flagged")

if __name__ == "__main__":
    test_problems_fresh_is_clean()
    test_problems_future_dated_match_flagged()
    test_problems_stale_results_flagged()
    test_problems_offseason_relax_window()
    test_problems_missing_results_is_a_problem()
    test_problems_coverage_gate_needs_volume()
    test_problems_fresh_overlay_freeze_flagged()
    test_charting_coverage_age_is_context_not_a_source_failure()
    test_source_checks_structure_and_consistency()
    test_tour_health_empty_frame_reports_none()
    test_main_strict_exit_code_and_report()
    test_main_surfaces_output_problems()
    test_main_reports_problems_changed()
    test_main_reports_a_stale_model_through_the_alert_path()
    test_gate_blocks_bad_output_without_writing_healthjson()
    test_gate_classifies_advisory_vs_blocking()
    test_output_healthy_is_clean()
    test_output_stale_live_event_severity_follows_the_event_tier()
    test_output_completed_event_with_many_alive_is_flagged()
    test_output_numbered_qualifier_as_model_favourite_is_flagged()
    test_output_model_age_flags_a_dead_retrain()
    test_output_model_age_is_advisory_never_blocking()
    test_output_model_age_missing_is_silent_and_fresh_is_clean()
    test_output_missing_and_corrupt_files()
    test_output_feature_schema_drift()
    test_output_method_missing_blocks()
    test_output_method_feature_count_drift()
    test_output_method_out_of_range()
    test_output_match_floor_and_drop()
    test_output_wta_125_policy_is_a_blocking_invariant()
    test_output_match_drop_resets_only_across_a_population_version_boundary()
    test_output_model_population_must_match_current_data_population()
    test_output_real_draw_must_be_standard_size()
    test_output_completed_nonpower_of_two_is_fine()
    test_output_alive_gt_draw_and_missing_champion()
    test_output_draw_cannot_exceed_128()
    test_output_probability_and_monotonicity()
    test_output_projection_none_round_is_tolerated()
    test_output_matrix_antisymmetry()
    test_output_placeholder_name_leak()
    test_output_duplicate_tournament_name()
    test_output_split_event_under_two_names()
    test_output_distinct_events_are_clean()
    test_output_concurrent_events_with_open_qualifying_are_clean()
    test_output_split_event_caught_on_a_barely_filled_draw()
    test_output_upcoming_and_fixtures_consistency()
    test_output_market_benchmark_freeze_is_flagged_advisory()
    test_output_forecast_drift_flagged_advisory()
    test_output_forecast_log_stale_flagged_advisory()
    test_output_track_and_forecast_monotonicity()
    test_output_emptiness_is_season_gated()
    test_output_liverank_drift_is_season_gated()
    test_output_player_enrichment_fields_gated()
    test_output_kalshi_ledger_clean_and_unscored_ignored()
    test_output_kalshi_ledger_post_anchor_quote_blocks()
    test_output_kalshi_ledger_settled_carry_blocks()
    test_output_kalshi_ledger_settlement_disagreement_blocks()
    test_output_kalshi_ledger_double_scored_result_blocks()
    test_output_surface_must_be_canonical_and_month_guess_is_advisory()
    test_output_level_must_be_in_the_tour_vocabulary()
    test_board_quality_severity_follows_the_event_tier()
    test_upcoming_event_that_already_ended_or_never_started()
    test_lost_bracket_is_sentinel_only()
    test_calendar_complete_without_a_final_is_honest_not_a_bug()
    test_one_identity_one_card()
    test_cross_tour_surface_split_is_flagged()
    test_read_outputs_detects_missing_and_corrupt()
    test_read_outputs_flags_nan_as_corrupt()
    test_format_issue_body_has_problems_and_fix_prompt()
    print("\nALL PASSED")
