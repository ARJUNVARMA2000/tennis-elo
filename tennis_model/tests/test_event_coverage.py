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
