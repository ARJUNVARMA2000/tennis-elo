"""Independent begun-event coverage contract (source evidence -> site card)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.event_coverage import build_event_coverage, finalize_event_coverage

BUILD_DATE = pd.Timestamp("2026-07-28")


def _registry() -> dict:
    return {"version": 1, "events": {
        "875-2026": {"name": "Odlum Brown VanOpen", "names": ["Vancouver", "Odlum Brown VanOpen"],
                     "start": "2026-07-25", "end": "2026-08-02"},
        "421-2026": {"name": "National Bank Open", "names": ["National Bank Open"],
                     "start": "2026-08-02", "end": "2026-08-14"},
    }}


def _results() -> pd.DataFrame:
    return pd.DataFrame([
        {"tourney_name": "Vancouver", "espn_id": "875-2026", "date": BUILD_DATE,
         "round": "R32", "winner_name": "A Player", "loser_name": "B Player",
         "tourney_level": None, "draw_level": "main"},
        {"tourney_name": "Vancouver", "espn_id": "875-2026", "date": BUILD_DATE,
         "round": "R32", "winner_name": "C Player", "loser_name": "D Player",
         "tourney_level": None, "draw_level": "main"},
        # Challenger evidence with no stable tour-event identity is outside this board.
        {"tourney_name": "Small Challenger", "espn_id": None, "date": BUILD_DATE,
         "round": "R32", "winner_name": "E Player", "loser_name": "F Player",
         "tourney_level": "C", "draw_level": "main"},
    ])


def test_begun_event_comes_from_results_even_when_projection_would_filter_it():
    manifest = build_event_coverage(_results(), "wta", build_date=BUILD_DATE,
                                    upcoming_df=pd.DataFrame(), registry=_registry())
    assert [e["key"] for e in manifest["events"]] == ["espn:875-2026"]
    event = manifest["events"][0]
    assert event["name"] == "Odlum Brown VanOpen"       # current registry display name
    assert event["evidence"] == ["result"]
    assert event["start"] == "2026-07-25" and event["end"] == "2026-08-02"


def test_completed_fallback_preserves_a_known_final_result():
    results = pd.DataFrame([
        {"tourney_name": "Settled Open", "espn_id": "999-2026", "date": "2026-07-20",
         "round": "F", "winner_name": "A Champion", "loser_name": "B Runner",
         "tourney_level": "G", "surface_b": "Grass", "surface_src": "archive",
         "best_of": 5, "draw_level": "main"},
    ])
    registry = {"events": {"999-2026": {
        "name": "Settled Open", "names": ["Settled Open"],
        "start": "2026-07-14", "end": "2026-07-20",
    }}}
    manifest = build_event_coverage(results, "atp", build_date=BUILD_DATE,
                                    upcoming_df=pd.DataFrame(), registry=registry)
    event = manifest["events"][0]
    assert event["finalRecorded"] is True
    assert (event["champion"], event["runnerUp"]) == ("A Champion", "B Runner")

    tournaments: list[dict] = []  # fewer than eight result players: projector returns no card
    finalize_event_coverage(manifest, tournaments)
    shell = tournaments[0]
    assert shell["status"] == "completed" and shell["drawStatus"] == "final"
    assert shell["finalRecorded"] is True
    assert (shell["champion"], shell["runnerUp"]) == ("A Champion", "B Runner")
    assert (shell["level"], shell["surface"], shell["surfaceSource"]) == (
        "Grand Slam", "Grass", "archive")
    assert shell["bestOf"] == 5 and shell["drawSize"] is None


def test_expired_live_name_recovers_cached_draw_id_from_match_evidence():
    """The August 4 Iasi rollover: ESPN's 14-day result window expired, leaving the
    stable feed's short city label with no id.  The official draw still carries the id,
    dates, players, and first-round pairings, which are enough to prove identity without
    treating the four-letter name as string evidence."""
    slots = [f"P{i}" for i in range(32)]
    results = pd.DataFrame([
        {"tourney_name": "Iasi", "espn_id": None,
         "date": pd.Timestamp("2026-07-13") + pd.Timedelta(days=i % 6),
         "round": "R32", "winner_name": slots[2 * i], "loser_name": slots[2 * i + 1],
         "tourney_level": "WTA250", "draw_level": "main"}
        for i in range(16)
    ])
    registry = {"events": {"874-2026": {
        "name": "Unicredit Iasi Open", "names": ["Unicredit Iasi Open"],
        "start": "2026-07-12", "end": "2026-07-21",
    }}}
    draws = {"874-2026": {
        "name": "Unicredit Iasi Open", "espnId": "874-2026",
        "start": "2026-07-12", "end": "2026-07-21", "slots": slots,
    }}
    # Adjacent events can overlap and reuse entrants.  This decoy shares 13 players but only
    # one real matchup, the exact evidence shape that must not make identity ambiguous.
    decoy_slots = ["P0", "P1"]
    for i in range(2, 13):
        decoy_slots.extend([f"P{i}", f"D{i}"])
    decoy_slots.extend([f"D{i}" for i in range(13, 21)])
    draws["306-2026"] = {
        "name": "Nordea Open", "espnId": "306-2026",
        "start": "2026-07-06", "end": "2026-07-20", "slots": decoy_slots,
    }

    manifest = build_event_coverage(
        results, "wta", build_date="2026-08-04", upcoming_df=pd.DataFrame(),
        registry=registry, draws=draws,
    )

    assert len(manifest["events"]) == 1
    event = manifest["events"][0]
    assert event["espnId"] == "874-2026" and event["key"] == "espn:874-2026"
    assert event["name"] == "Iasi" and set(event["names"]) == {
        "Iasi", "Unicredit Iasi Open"}
    assert (event["start"], event["end"]) == ("2026-07-12", "2026-07-21")


def test_wta_slam_shell_is_best_of_three_and_evidence_free_shell_stays_generic(monkeypatch):
    from tennis_model.data import event_coverage as ec

    monkeypatch.setattr(ec, "resolve_level", lambda tour, name, archive_level=None, event_id=None:
                        "Grand Slam" if archive_level == "G" else f"{tour.upper()} Tour")
    monkeypatch.setattr(ec, "resolve_surface_info", lambda tour, name, date, archive_surface=None:
                        (archive_surface, "archive") if archive_surface else ("Hard", "month"))
    base = {"version": 1, "tour": "wta", "buildDate": "2026-07-28"}
    slam = {"key": "espn:1-2026", "espnId": "1-2026", "name": "Test Slam",
            "names": ["Test Slam"], "start": "2026-07-01", "end": "2026-07-14",
            "archiveLevel": "G", "surface": "Grass", "surfaceSource": "archive",
            "bestOf": None, "finalRecorded": False, "players": []}
    generic = {"key": "espn:2-2026", "espnId": "2-2026", "name": "Mystery Event",
               "names": ["Mystery Event"], "start": "2026-07-20", "end": "2026-07-30",
               "archiveLevel": None, "surface": None, "surfaceSource": None,
               "bestOf": None, "finalRecorded": False, "players": []}
    tournaments: list[dict] = []
    finalized = finalize_event_coverage({**base, "events": [slam, generic]}, tournaments)
    by_name = {card["name"]: card for card in tournaments}
    assert by_name["Test Slam"]["level"] == "Grand Slam"
    assert by_name["Test Slam"]["bestOf"] == 3
    assert by_name["Mystery Event"]["level"] == "WTA Tour"
    assert by_name["Mystery Event"]["bestOf"] == 3
    assert finalized["shellKeys"] == ["espn:1-2026", "espn:2-2026"]


def test_shell_resolution_tries_every_known_event_name(monkeypatch):
    from tennis_model.data import event_coverage as ec

    level_calls: list[tuple[str, str | None]] = []
    surface_calls: list[str] = []

    def level(_tour, name, archive_level=None, event_id=None):
        level_calls.append((name, event_id))
        return "Grand Slam" if name == "Wimbledon" else "ATP Tour"

    def surface(_tour, name, _date, archive_surface=None):
        surface_calls.append(name)
        return ("Grass", "wiki") if name == "Wimbledon" else ("Hard", "month")

    monkeypatch.setattr(ec, "resolve_level", level)
    monkeypatch.setattr(ec, "resolve_surface_info", surface)
    event = {"key": "espn:188-2026", "espnId": "188-2026", "name": "The Championships",
             "names": ["The Championships", "Wimbledon"],
             "start": "2026-06-29", "end": "2026-07-12", "archiveLevel": None,
             "surface": None, "surfaceSource": None, "bestOf": None,
             "finalRecorded": False, "players": []}
    tournaments: list[dict] = []
    finalize_event_coverage({"version": 1, "tour": "atp", "buildDate": "2026-07-28",
                             "events": [event]}, tournaments)
    shell = tournaments[0]
    assert shell["level"] == "Grand Slam" and shell["surface"] == "Grass"
    assert shell["surfaceSource"] == "wiki" and shell["bestOf"] == 5
    assert level_calls == [
        ("The Championships", "188-2026"), ("Wimbledon", "188-2026"),
    ]
    assert surface_calls == ["The Championships", "Wimbledon"]


def test_started_schedule_counts_but_future_and_calendar_only_do_not():
    upcoming = pd.DataFrame([
        {"tourney_name": "Odlum Brown VanOpen", "espn_id": "875-2026",
         "tourney_date": "2026-07-28", "round": "R32",
         "playerA": "A Player", "playerB": "B Player"},
        {"tourney_name": "National Bank Open", "espn_id": "421-2026",
         "tourney_date": "2026-08-03", "round": "R64",
         "playerA": "C Player", "playerB": "D Player"},
    ])
    manifest = build_event_coverage(pd.DataFrame(), "wta", build_date=BUILD_DATE,
                                    upcoming_df=upcoming, registry=_registry())
    assert [e["key"] for e in manifest["events"]] == ["espn:875-2026"]
    # 421 exists in the calendar, but neither its calendar date nor a future scheduled match
    # is proof that it has begun on the build date.
    assert all(e["key"] != "espn:421-2026" for e in manifest["events"])


def test_idless_sources_join_only_on_dates_plus_two_shared_real_players():
    results = pd.DataFrame([
        {"tourney_name": "Archive City", "espn_id": None, "date": BUILD_DATE,
         "round": "R32", "winner_name": "A Player", "loser_name": "B Player",
         "tourney_level": "250", "draw_level": "main"},
    ])
    upcoming = pd.DataFrame([
        {"tourney_name": "Sponsor Open", "espn_id": None, "tourney_date": "2026-07-28",
         "round": "R32", "playerA": "A Player", "playerB": "B Player"},
        {"tourney_name": "Other Open", "espn_id": None, "tourney_date": "2026-07-28",
         "round": "R32", "playerA": "A Player", "playerB": "C Player"},
    ])
    manifest = build_event_coverage(results, "atp", build_date=BUILD_DATE,
                                    upcoming_df=upcoming, registry={"events": {}})
    assert len(manifest["events"]) == 2
    merged = next(e for e in manifest["events"] if set(e["names"]) == {"Archive City", "Sponsor Open"})
    assert merged["evidence"] == ["result", "scheduled"]
    assert merged["key"].startswith("evidence:")


def test_finalize_stamps_cards_and_adds_an_honest_shell_for_any_gap():
    manifest = build_event_coverage(_results(), "wta", build_date=BUILD_DATE,
                                    upcoming_df=pd.DataFrame(), registry=_registry())
    tournaments: list[dict] = []                 # the projector filtered the begun event
    finalized = finalize_event_coverage(manifest, tournaments)

    assert len(tournaments) == 1
    shell = tournaments[0]
    assert shell["name"] == "Odlum Brown VanOpen"
    assert shell["coverageKey"] == "espn:875-2026"
    assert shell["coverageOnly"] is True
    assert shell["status"] == "live" and shell["drawStatus"] == "unavailable"
    assert shell["projection"] == [] and shell["drawSize"] is None
    assert finalized["shippedKeys"] == ["espn:875-2026"]
    assert finalized["shellKeys"] == ["espn:875-2026"]


def test_finalize_never_matches_idless_events_by_similar_name_alone():
    manifest = {"version": 1, "tour": "atp", "buildDate": "2026-07-28", "events": [{
        "key": "evidence:abc", "espnId": None, "name": "Springfield Open",
        "names": ["Springfield Open"], "start": "2026-07-28", "end": "2026-08-02",
        "evidence": ["result"], "players": ["A Player", "B Player"],
    }]}
    card = {"name": "Springfield Tennis Open", "espnId": None,
            "start": "2026-07-28", "end": "2026-08-02", "projection": [
                {"name": "X Player"}, {"name": "Y Player"}],
            "status": "live", "drawStatus": "seeded"}
    finalize_event_coverage(manifest, [card])
    assert card["coverageKey"] != "evidence:abc"
