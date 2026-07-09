"""Unit checks for the data-health sentinel (data/health.py) — fully synthetic.

Runnable directly (`python tests/test_health.py`) or under pytest. problems() and
output_problems() are pure given their input dicts; tour_health()/read_outputs()/main()
are exercised with their IO seams redirected (same save/restore pattern as test_track).
"""

from __future__ import annotations

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
def _healthy_data() -> dict:
    m = [[0.5 if i == j else (0.6 if i < j else 0.4) for j in range(3)] for i in range(3)]
    return {
        "meta": {"matches": 300_000, "activePlayers": 3, "features": ["f"] * len(FEATURES),
                 "lastUpdated": "2026-07-09T00:00:00Z"},
        "players": [{"name": f"P{i}", "elo": 2000 - i, "eloRank": i + 1, "liveRank": i + 1}
                    for i in range(3)],
        "matrix": {"players": ["P0", "P1", "P2"], "formats": [3], "surfaces": {"Hard": {"3": m}}},
        "tournaments": [{"name": "Test Open", "surface": "Grass", "status": "live",
                         "drawStatus": "real", "drawSize": 128, "aliveCount": 7, "champion": None,
                         "projection": [{"name": "P0", "champion": 0.5, "final": 0.6, "sf": 0.8,
                                         "reach": {"R32": 1.0, "R16": 1.0, "QF": 0.95,
                                                   "SF": 0.8, "F": 0.6, "Champion": 0.5}}]}],
        "upcoming": [{"event": "Test Open", "playerA": "P0", "playerB": "P1", "pA": 0.7}],
        "fixtures": [{"modelProb": 0.6, "upset": False}, {"modelProb": 0.4, "upset": True}],
        "track": {"matchForecasts": {"logged": 10, "graded": 6, "pending": 4}},
    }


def _oc(data=None, missing=None, corrupt=None, forecast=("keep",)) -> dict:
    return {"data": _healthy_data() if data is None else data,
            "missing": missing or [], "corrupt": corrupt or [],
            "forecast": {"lines": 200, "max_as_of": "2026-07-09"} if forecast == ("keep",) else forecast}


def _h(result_age=1, stats_age=2, frac=0.9, n=500) -> dict:
    return {"result_age_days": result_age, "stats_age_days": stats_age,
            "cur_year_stats_fraction": frac, "cur_year_matches": n}


def test_problems_fresh_is_clean():
    assert health.problems("atp", _h(), pd.Timestamp("2026-07-01")) == []
    print("ok test_problems_fresh_is_clean")


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


def test_tour_health_empty_frame_reports_none():
    """An empty tour must report None ages (flagged downstream), not crash on NaT."""
    orig = health.load_matches
    try:
        health.load_matches = lambda tour: pd.DataFrame(
            {"date": pd.to_datetime(pd.Series([], dtype="object")),
             "completed": pd.Series([], dtype=bool),
             "has_stats": pd.Series([], dtype=bool)})
        h = health.tour_health("atp", pd.Timestamp("2026-07-01"))
    finally:
        health.load_matches = orig
    assert h["matches"] == 0
    assert h["date_max"] is None and h["result_age_days"] is None
    assert any("no completed matches" in p
               for p in health.problems("atp", h, pd.Timestamp("2026-07-01")))
    print("ok test_tour_health_empty_frame_reports_none")


def test_main_strict_exit_code_and_report():
    stale = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]),
                          "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: stale
            health.read_outputs = lambda tour: _oc()          # outputs clean; failure is source-side
            health.OUTPUT_DIR = Path(d)
            health.TOURS = ("atp",)
            sys.argv = ["health", "--strict"]
            rc_strict = health.main()
            report = json.loads((Path(d) / "health.json").read_text())
            sys.argv = ["health"]
            rc_soft = health.main()
    finally:
        health.load_matches, health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv = orig
    assert rc_strict == 1 and report["ok"] is False and report["tours"]["atp"]["problems"]
    assert report["tours"]["atp"]["output"]["matches"] == 300_000   # output snapshot persisted
    assert rc_soft == 0                      # same problems, but only --strict reds the build
    print("ok test_main_strict_exit_code_and_report")


def test_main_surfaces_output_problems():
    """A clean source but a broken produced artifact must still red the build."""
    from datetime import UTC, datetime
    fresh = pd.DataFrame({"date": pd.to_datetime([datetime.now(UTC).date()]),
                          "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: fresh
            health.read_outputs = lambda tour: _oc(missing=["tournaments"])
            health.OUTPUT_DIR = Path(d)
            health.TOURS = ("atp",)
            sys.argv = ["health", "--strict"]
            rc = health.main()
            report = json.loads((Path(d) / "health.json").read_text())
    finally:
        health.load_matches, health.read_outputs, health.OUTPUT_DIR, health.TOURS, sys.argv = orig
    assert rc == 1 and report["ok"] is False
    assert report["tours"]["atp"]["problems"] == []              # source was fine
    assert any("tournaments.json missing" in p for p in report["tours"]["atp"]["output"]["problems"])
    print("ok test_main_surfaces_output_problems")


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


def test_gate_classifies_advisory_vs_blocking():
    """Provably-wrong output blocks the deploy; a thin/quirky schedule/rankings feed only warns
    (so a cosmetic naming split or a quiet week can't freeze the site)."""
    assert health._gate_blocks("wta: 'X' 'P0' champion=1.4 out of [0,1]")            # impossible number
    assert health._gate_blocks("atp: tournaments.json missing")                      # missing required JSON
    assert health._gate_blocks("wta: tournament 'X' aliveCount 99 > drawSize 32")    # structural break
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


def test_output_feature_schema_drift():
    d = _healthy_data()
    d["meta"]["features"] = ["only", "three", "features"]
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("meta.features has 3 entries" in p for p in out)
    print("ok test_output_feature_schema_drift")


def test_output_match_floor_and_drop():
    low = _healthy_data(); low["meta"]["matches"] = 1000
    assert any("below floor" in p for p in health.output_problems("atp", _oc(data=low), NOW))
    # a silent source drop vs the prior run's snapshot
    dropped = health.output_problems("atp", _oc(), NOW, prev={"matches": 400_000})
    assert any("dropped 400000 -> 300000" in p for p in dropped)
    print("ok test_output_match_floor_and_drop")


def test_output_real_draw_must_be_power_of_two():
    d = _healthy_data(); d["tournaments"][0]["drawSize"] = 130       # 128 + a leaked 'TBD'
    assert any("not a power of two" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_real_draw_must_be_power_of_two")


def test_output_completed_nonpower_of_two_is_fine():
    """A completed event's drawSize is len(field_pool) — 41 (main draw + qualifiers) is normal."""
    d = _healthy_data()
    d["tournaments"] = [{"name": "Halle", "status": "completed", "drawStatus": "final",
                         "drawSize": 41, "aliveCount": 1, "champion": "Someone", "projection": []}]
    assert not any("power of two" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_completed_nonpower_of_two_is_fine")


def test_output_alive_gt_draw_and_missing_champion():
    d = _healthy_data()
    d["tournaments"] = [{"name": "X", "status": "completed", "drawStatus": "final",
                         "drawSize": 32, "aliveCount": 99, "champion": None, "projection": []}]
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("aliveCount 99 > drawSize 32" in p for p in out)
    assert any("has no champion" in p for p in out)
    print("ok test_output_alive_gt_draw_and_missing_champion")


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
    d = _healthy_data()
    d["matrix"]["surfaces"]["Hard"]["3"][1][0] = 0.6               # now 0.6 + 0.6 != 1
    assert any("antisymmetric" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    print("ok test_output_matrix_antisymmetry")


def test_output_placeholder_name_leak():
    d = _healthy_data()
    d["tournaments"][0]["projection"][0]["name"] = "TBD"
    assert any("placeholder name" in p for p in health.output_problems("atp", _oc(data=d), NOW))
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


def test_output_upcoming_and_fixtures_consistency():
    d = _healthy_data()
    d["upcoming"][0]["playerB"] = "P0"                             # identical players
    d["fixtures"][0]["upset"] = True                               # but modelProb 0.6 >= 0.5
    out = health.output_problems("atp", _oc(data=d), NOW)
    assert any("identical players" in p for p in out)
    assert any("upset flag disagrees" in p for p in out)
    print("ok test_output_upcoming_and_fixtures_consistency")


def test_output_track_and_forecast_monotonicity():
    d = _healthy_data(); d["track"]["matchForecasts"]["graded"] = 99
    assert any("graded+pending" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    shrank = health.output_problems("atp", _oc(forecast={"lines": 100, "max_as_of": "x"}),
                                    NOW, prev={"forecast_lines": 200})
    assert any("forecast log shrank 200 -> 100" in p for p in shrank)
    print("ok test_output_track_and_forecast_monotonicity")


def test_output_emptiness_is_season_gated():
    d = _healthy_data(); d["upcoming"] = []; d["tournaments"] = []
    assert any("upcoming.json is empty" in p for p in health.output_problems("atp", _oc(data=d), NOW))
    # in the Nov/Dec off-season the tours are dark — empty schedules must NOT red the build
    dec = pd.Timestamp("2026-12-15")
    assert not any("empty" in p for p in health.output_problems("atp", _oc(data=d), dec))
    print("ok test_output_emptiness_is_season_gated")


def test_output_liverank_drift_is_season_gated():
    d = _healthy_data()
    for p in d["players"]:
        p["liveRank"] = None                                       # rankings source vanished
    assert any("liveRank" in x for x in health.output_problems("atp", _oc(data=d), NOW))
    dec = pd.Timestamp("2026-12-15")
    assert not any("liveRank" in x for x in health.output_problems("atp", _oc(data=d), dec))
    print("ok test_output_liverank_drift_is_season_gated")


def test_read_outputs_detects_missing_and_corrupt(tmp_path=None):
    orig = (health.output_dir, health.DATA_DIR)
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "atp").mkdir()
            (root / "atp" / "meta.json").write_text('{"matches": 1}')
            (root / "atp" / "tournaments.json").write_text("{ not json")
            health.output_dir = lambda tour: root / tour
            health.DATA_DIR = root
            oc = health.read_outputs("atp")
    finally:
        health.output_dir, health.DATA_DIR = orig
    assert "meta" in oc["data"] and oc["data"]["meta"]["matches"] == 1
    assert "tournaments" in oc["corrupt"]
    assert "players" in oc["missing"] and "upcoming" in oc["missing"]
    assert oc["forecast"] is None                                  # no forecast_log in the temp root
    print("ok test_read_outputs_detects_missing_and_corrupt")


def test_read_outputs_flags_nan_as_corrupt():
    """json.loads accepts the bare NaN token but the browser's JSON.parse rejects it — a
    NaN that ships blanks the page (the WTA /player,/style regression: a scoreless match
    left "score": NaN in profiles.json). The gate must treat such a file as unparseable."""
    orig = (health.output_dir, health.DATA_DIR)
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "atp").mkdir()
            (root / "atp" / "meta.json").write_text('{"matches": 1}')
            # a real scoreless-match row, exactly as json.dump would have emitted it
            (root / "atp" / "profiles.json").write_text('{"P": {"recent": [{"score": NaN}]}}')
            health.output_dir = lambda tour: root / tour
            health.DATA_DIR = root
            oc = health.read_outputs("atp")
    finally:
        health.output_dir, health.DATA_DIR = orig
    assert "profiles" in oc["corrupt"] and "profiles" not in oc["data"]
    # and output_problems surfaces it through the existing unparseable channel
    assert any("profiles.json is present but unparseable" in p
               for p in health.output_problems("atp", oc, NOW))
    print("ok test_read_outputs_flags_nan_as_corrupt")


def test_format_issue_body_has_problems_and_fix_prompt():
    report = {"generated": "2026-07-09", "ok": False,
              "tours": {"wta": {"problems": ["wta: newest completed match is 9d old"],
                                "output": {"problems": ["wta: tournaments.json is empty"]}}}}
    body = health.format_issue_body(report, run_url="https://example/run/1")
    assert "newest completed match is 9d old" in body
    assert "tournaments.json is empty" in body
    assert "https://example/run/1" in body
    assert "new Claude Code session" in body and "data-health" in body
    print("ok test_format_issue_body_has_problems_and_fix_prompt")


if __name__ == "__main__":
    test_problems_fresh_is_clean()
    test_problems_stale_results_flagged()
    test_problems_offseason_relax_window()
    test_problems_missing_results_is_a_problem()
    test_problems_coverage_gate_needs_volume()
    test_tour_health_empty_frame_reports_none()
    test_main_strict_exit_code_and_report()
    test_main_surfaces_output_problems()
    test_gate_blocks_bad_output_without_writing_healthjson()
    test_gate_classifies_advisory_vs_blocking()
    test_output_healthy_is_clean()
    test_output_missing_and_corrupt_files()
    test_output_feature_schema_drift()
    test_output_match_floor_and_drop()
    test_output_real_draw_must_be_power_of_two()
    test_output_completed_nonpower_of_two_is_fine()
    test_output_alive_gt_draw_and_missing_champion()
    test_output_probability_and_monotonicity()
    test_output_projection_none_round_is_tolerated()
    test_output_matrix_antisymmetry()
    test_output_placeholder_name_leak()
    test_output_duplicate_tournament_name()
    test_output_split_event_under_two_names()
    test_output_distinct_events_are_clean()
    test_output_upcoming_and_fixtures_consistency()
    test_output_track_and_forecast_monotonicity()
    test_output_emptiness_is_season_gated()
    test_output_liverank_drift_is_season_gated()
    test_read_outputs_detects_missing_and_corrupt()
    test_read_outputs_flags_nan_as_corrupt()
    test_format_issue_body_has_problems_and_fix_prompt()
    print("\nALL PASSED")
