"""Replay the WTA Finals group-stage deployment failure from November 8."""

import copy
import json

import pandas as pd
import pytest
from tennis_model.model import export
from test_health import _healthy_data, _healthy_evidence, _oc
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import event_coverage, health, live, results, source_audit

EVENT_ID = "382-2026"
NOW = "2026-11-08T20:30:00Z"
# Match IDs, pairs and round objects from the November 8 ESPN scoreboard.
GROUP_MATCHES = [
    ("187373", "Linda Noskova", "Marta Kostyuk"),
    ("187374", "Jessica Pegula", "Coco Gauff"),
    ("187381", "Karolina Muchova", "Aryna Sabalenka"),
    ("187382", "Elina Svitolina", "Mirra Andreeva"),
    ("187372", "Jessica Pegula", "Marta Kostyuk"),
    ("187385", "Karolina Muchova", "Elina Svitolina"),
    ("187384", "Karolina Muchova", "Mirra Andreeva"),
    ("187379", "Elina Svitolina", "Aryna Sabalenka"),
    ("187378", "Mirra Andreeva", "Aryna Sabalenka"),
    ("187376", "Linda Noskova", "Jessica Pegula"),
    ("187375", "Linda Noskova", "Coco Gauff"),
    ("187371", "Coco Gauff", "Marta Kostyuk"),
]


def competition(match_id, a, b, round_id="15", label="Group Stage"):
    return {
        "id": match_id, "date": "2026-11-08T21:30Z", "timeValid": True,
        "round": {"id": round_id, "displayName": label},
        "status": {"type": {"state": "pre", "completed": False}},
        "competitors": [{"athlete": {"displayName": n}} for n in (a, b)],
    }


def completed(match):
    match["status"]["type"].update(state="post", completed=True, name="STATUS_FINAL")
    match["competitors"][0].update(winner=False, linescores=[{"value": 3}, {"value": 4}])
    match["competitors"][1].update(winner=True, linescores=[{"value": 6}, {"value": 6}])


def event_at_phase(phase):
    matches = [competition(*m) for m in GROUP_MATCHES]
    matches[0]["status"]["type"]["state"] = "in"
    for match in matches[2:4]:
        match["date"] = "2026-11-09T20:00Z"
    for match in matches[4:]:
        match.update(date="2026-11-10T05:00Z", timeValid=False)
    if phase != "opening":
        # Synthetic later results exercise the result and rematch paths.
        completed(matches[0])
    if phase == "final":
        final = competition("187442", *GROUP_MATCHES[0][1:], "7", "Final")
        final["date"] = "2026-11-15T21:00Z"
        completed(final)
        matches.append(final)
    return {
        "id": EVENT_ID, "name": "FAGE WTA Finals Indian Wells",
        "date": "2026-11-08T05:00Z", "endDate": "2026-11-16T04:59Z",
        "calendar": {"startDate": "2026-11-08T05:00Z", "endDate": "2026-11-15T05:00Z"},
        "groupings": [{"grouping": {"slug": "womens-singles"}, "competitions": matches}],
    }


def wta_evidence(a, b):
    evidence = _healthy_evidence(a, b)
    evidence["signals"].append({"key": "recentSurface", "available": False,
                                "supports": None, "impactPp": 0.0, "facts": {}})
    return evidence


def candidate(monkeypatch, tmp_path, phase):
    event = event_at_phase(phase)
    raw, proof = source_audit.capture_source("wta", [event], NOW)
    (tmp_path / "source_audit.json").write_bytes(raw)
    (tmp_path / "espn_acquisition.json").write_text(
        json.dumps({"tour": "wta", "completedAt": NOW, "eventCount": 1, "sourceAudit": proof})
    )
    monkeypatch.setattr(config, "live_dir", lambda _tour: tmp_path)
    monkeypatch.setattr(results, "event_match_view", lambda df, _tour: df)
    schedule = live.parse_upcoming([event], "womens")
    # Use the real coverage builder against a deterministic snapshot of the live inputs.
    build_coverage = event_coverage.build_event_coverage
    monkeypatch.setattr(event_coverage, "build_event_coverage", lambda df, tour: build_coverage(
        df, tour, build_date=NOW[:10], registry={}, draws={}, upcoming_df=schedule))
    from tennis_model.sim import tournaments
    for loader in ("_load_fields", "_load_upcoming", "_load_upcoming_bounds",
                   "_load_tournament_draws", "load_registry"):
        monkeypatch.setattr(tournaments, loader, lambda _tour: {})
    names = {n for _, a, b in GROUP_MATCHES for n in (a, b)}
    frame = pd.DataFrame(columns=["date", "tourney_name", "round", "winner_name", "loser_name"])
    manifest, cards = export.build_event_outputs(_Pred(dict.fromkeys(names, 1700.0)), frame, "wta")
    data = _healthy_data()
    sample, = data["upcoming"]
    data["meta"].update(modelPlayerNames=sorted(names), tournamentSourceAudit=proof)
    data.update(tournaments=cards, brackets=export.build_brackets_payload(cards),
                event_coverage=manifest,
                upcoming=[{**sample, "event": "WTA Finals", "espnId": row.espn_id,
                           "round": row.round, "date": row.tourney_date,
                           "surface": "Hard", "level": "Tour Finals", "bestOf": 3,
                           "playerA": row.playerA, "playerB": row.playerB,
                           "evidence": wta_evidence(row.playerA, row.playerB), "watchRank": rank}
                          for rank, row in enumerate(schedule.itertuples(), 1)])
    oc = _oc(data=data)
    oc["source_audit"] = source_audit.read_source(tmp_path, "wta")
    return oc


def incident_blockers(oc):
    return {f.code for f in health.output_findings("wta", oc, pd.Timestamp(NOW))
            if EVENT_ID in f.entity and health._gate_blocks(f)}


@pytest.mark.parametrize("phase", ["opening", "group-results", "final"])
def test_finals_event_projection_and_gate(monkeypatch, tmp_path, phase):
    oc = candidate(monkeypatch, tmp_path, phase)
    card, = oc["data"]["tournaments"]
    assert not incident_blockers(oc)
    assert card["level"] == "Tour Finals" and card["surface"] == "Hard"
    assert card["drawSize"] == 8 and not card["coverageOnly"]
    assert card["drawStatus"] == "round-robin" and not card["hasBracket"]
    assert card["status"] == {"opening": "live", "group-results": "live", "final": "completed"}[phase]
    assert card["end"] == ("2026-11-15" if phase == "final" else "2026-11-08")
    assert card["scheduledEnd"] == "2026-11-15"
    assert len(card["roundRobinFixtures"]) == 12 + (phase == "final")
    assert card["champion"] == ("Marta Kostyuk" if phase == "final" else None)
    assert set(r["round"] for r in oc["data"]["upcoming"]) == {"RR"}

    broken = copy.deepcopy(oc)
    broken_card = broken["data"]["tournaments"][0]
    broken_card["roundRobinFixtures"].pop(0)
    assert "output.source_audit.group_stage_fixture_mismatch" in incident_blockers(broken)
    broken = copy.deepcopy(oc)
    broken["data"]["upcoming"][0]["round"] = "QF"
    assert "output.source_audit.group_stage_schedule_unwitnessed" in incident_blockers(broken)

    if phase != "opening":
        broken = copy.deepcopy(oc)
        broken["data"]["tournaments"][0]["roundRobinFixtures"][0]["score"] = "6-0 6-0"
        assert "output.source_audit.score_mismatch" in incident_blockers(broken)
        event = event_at_phase(phase)
        assert live.parse_fields([event], "womens")[event["name"]]["eliminated"] == (
            ["Linda Noskova"] if phase == "final" else [])
        assert set(live.parse_events([event], "womens")["round"]) == (
            {"RR", "F"} if phase == "final" else {"RR"})


def test_opening_placeholder_replays_gate_errors(monkeypatch, tmp_path):
    oc = candidate(monkeypatch, tmp_path, "opening")
    manifest = oc["data"]["event_coverage"]
    cards = []
    oc["data"]["event_coverage"] = event_coverage.finalize_event_coverage(manifest, cards)
    oc["data"]["tournaments"] = cards
    cards[0]["level"] = "WTA Tour"
    for row in oc["data"]["upcoming"]:
        row["round"] = "R64"
    assert {
        "output.event_coverage.shell_only",
        "output.tournament.tier_unresolved",
        "output.source_audit.scheduled_match_missing",
    } <= incident_blockers(oc)


def test_opening_schedule_is_bounded_by_the_witnessed_calendar(monkeypatch, tmp_path):
    oc = candidate(monkeypatch, tmp_path, "opening")
    assert {row["date"] for row in oc["data"]["upcoming"]} > {"2026-11-08"}
    assert not incident_blockers(oc)

    card, = oc["data"]["tournaments"]
    del card["scheduledEnd"]
    assert {"output.upcoming.date_outside_event",
            "output.source_audit.group_stage_calendar_end_mismatch"} <= incident_blockers(oc)

    card["scheduledEnd"] = "2026-11-15"
    oc["data"]["upcoming"][0]["date"] = "2026-11-16"
    assert "output.upcoming.date_outside_event" in incident_blockers(oc)
