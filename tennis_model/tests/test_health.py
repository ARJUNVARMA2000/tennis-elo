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
        "players": [{"name": f"P{i}", "elo": 2000 - i, "eloRank": i + 1, "liveRank": i + 1,
                     "heightCm": 185, "winRate10": 0.6,
                     "servePctHard": 0.64, "servePctClay": 0.61, "servePctGrass": 0.66,
                     "returnPctHard": 0.36, "returnPctClay": 0.39, "returnPctGrass": 0.34}
                    for i in range(3)],
        "matrix": {"players": ["P0", "P1", "P2"], "formats": [3], "surfaces": {"Hard": {"3": m}}},
        "tournaments": [{"name": "Test Open", "surface": "Grass", "status": "live",
                         "drawStatus": "real", "drawSize": 128, "aliveCount": 7, "champion": None,
                         "projection": [{"name": "P0", "champion": 0.5, "final": 0.6, "sf": 0.8,
                                         "reach": {"R32": 1.0, "R16": 1.0, "QF": 0.95,
                                                   "SF": 0.8, "F": 0.6, "Champion": 0.5}}]}],
        "upcoming": [{"event": "Test Open", "playerA": "P0", "playerB": "P1", "pA": 0.7}],
        "fixtures": [{"modelProb": 0.6, "upset": False}, {"modelProb": 0.4, "upset": True}],
        "track": {"matchForecasts": {"logged": 10, "graded": 6, "pending": 4,
                                     "drift": {"status": "ok", "windowDays": 90, "n": 400,
                                               "logloss": 0.58, "expectedLogloss": 0.575,
                                               "d": 0.005, "se": 0.019, "t": 0.26}}},
        "market": {"years": [2012, 2026], "matched": 20_000,
                   "oosEnd": "2026-07-06", "lastMatchedDate": "2026-07-04"},
    }


def _oc(data=None, missing=None, corrupt=None, forecast=("keep",), kalshi_ledger=None) -> dict:
    return {"data": _healthy_data() if data is None else data,
            "missing": missing or [], "corrupt": corrupt or [],
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


def _h(result_age=1, stats_age=2, frac=0.9, n=500, fresh_age=3, charting_age=30) -> dict:
    return {"result_age_days": result_age, "stats_age_days": stats_age,
            "cur_year_stats_fraction": frac, "cur_year_matches": n,
            "fresh_age_days": fresh_age, "charting_age_days": charting_age}


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


def test_problems_charting_freeze_flagged():
    """MCP is batch-updated — a 80d lag is normal, 120d means the source moved/froze;
    a missing file means style features are silently gone."""
    now = pd.Timestamp("2026-07-01")
    assert any("charted match" in p for p in health.problems("atp", _h(charting_age=120), now))
    assert health.problems("atp", _h(charting_age=80), now) == []
    assert any("charting files missing" in p
               for p in health.problems("atp", _h(charting_age=None), now))
    print("ok test_problems_charting_freeze_flagged")


def test_tour_health_empty_frame_reports_none():
    """An empty tour must report None ages (flagged downstream), not crash on NaT."""
    orig = (health.load_matches, health.fresh_date_max, health.charting_date_max)
    try:
        health.load_matches = lambda tour: pd.DataFrame(
            {"date": pd.to_datetime(pd.Series([], dtype="object")),
             "completed": pd.Series([], dtype=bool),
             "has_stats": pd.Series([], dtype=bool)})
        health.fresh_date_max = lambda tour: None
        health.charting_date_max = lambda tour: None
        h = health.tour_health("atp", pd.Timestamp("2026-07-01"))
    finally:
        health.load_matches, health.fresh_date_max, health.charting_date_max = orig
    assert h["matches"] == 0
    assert h["date_max"] is None and h["result_age_days"] is None
    assert h["fresh_age_days"] is None and h["charting_age_days"] is None
    assert any("no completed matches" in p
               for p in health.problems("atp", h, pd.Timestamp("2026-07-01")))
    print("ok test_tour_health_empty_frame_reports_none")


def test_main_strict_exit_code_and_report():
    from datetime import UTC, datetime
    today = pd.Timestamp(datetime.now(UTC).date())
    stale = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]),
                          "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.read_outputs, health.fresh_date_max,
            health.charting_date_max, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: stale
            health.read_outputs = lambda tour: _oc()          # outputs clean; failure is source-side
            health.fresh_date_max = lambda tour: today        # hermetic: no real data/raw reads
            health.charting_date_max = lambda tour: today
            health.OUTPUT_DIR = Path(d)
            health.TOURS = ("atp",)
            sys.argv = ["health", "--strict"]
            rc_strict = health.main()
            report = json.loads((Path(d) / "health.json").read_text())
            sys.argv = ["health"]
            rc_soft = health.main()
    finally:
        (health.load_matches, health.read_outputs, health.fresh_date_max,
         health.charting_date_max, health.OUTPUT_DIR, health.TOURS, sys.argv) = orig
    assert rc_strict == 1 and report["ok"] is False and report["tours"]["atp"]["problems"]
    assert report["tours"]["atp"]["output"]["matches"] == 300_000   # output snapshot persisted
    assert rc_soft == 0                      # same problems, but only --strict reds the build
    print("ok test_main_strict_exit_code_and_report")


def test_main_surfaces_output_problems():
    """A clean source but a broken produced artifact must still red the build."""
    from datetime import UTC, datetime
    today = pd.Timestamp(datetime.now(UTC).date())
    fresh = pd.DataFrame({"date": pd.to_datetime([datetime.now(UTC).date()]),
                          "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.read_outputs, health.fresh_date_max,
            health.charting_date_max, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: fresh
            health.read_outputs = lambda tour: _oc(missing=["tournaments"])
            health.fresh_date_max = lambda tour: today        # hermetic: no real data/raw reads
            health.charting_date_max = lambda tour: today
            health.OUTPUT_DIR = Path(d)
            health.TOURS = ("atp",)
            sys.argv = ["health", "--strict"]
            rc = health.main()
            report = json.loads((Path(d) / "health.json").read_text())
    finally:
        (health.load_matches, health.read_outputs, health.fresh_date_max,
         health.charting_date_max, health.OUTPUT_DIR, health.TOURS, sys.argv) = orig
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
    assert not any("bracket size" in p for p in health.output_problems("atp", _oc(data=d), NOW))
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
    orig = (health.load_matches, health.read_outputs, health.fresh_date_max,
            health.charting_date_max, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.read_outputs = lambda tour: _oc()
            health.fresh_date_max = lambda tour: today
            health.charting_date_max = lambda tour: today
            health.OUTPUT_DIR = Path(d)
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
    finally:
        (health.load_matches, health.read_outputs, health.fresh_date_max,
         health.charting_date_max, health.OUTPUT_DIR, health.TOURS, sys.argv) = orig
    assert first["ok"] is False and first["problems_changed"] is True
    assert second["problems_changed"] is False
    assert third["problems_changed"] is True
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
    test_problems_fresh_overlay_freeze_flagged()
    test_problems_charting_freeze_flagged()
    test_tour_health_empty_frame_reports_none()
    test_main_strict_exit_code_and_report()
    test_main_surfaces_output_problems()
    test_main_reports_problems_changed()
    test_gate_blocks_bad_output_without_writing_healthjson()
    test_gate_classifies_advisory_vs_blocking()
    test_output_healthy_is_clean()
    test_output_missing_and_corrupt_files()
    test_output_feature_schema_drift()
    test_output_match_floor_and_drop()
    test_output_real_draw_must_be_standard_size()
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
    test_read_outputs_detects_missing_and_corrupt()
    test_read_outputs_flags_nan_as_corrupt()
    test_format_issue_body_has_problems_and_fix_prompt()
    print("\nALL PASSED")
