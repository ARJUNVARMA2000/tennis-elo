"""Finding fingerprints must use provider identity, never mutable display prose."""

from __future__ import annotations

import copy

import pandas as pd

from tennis_model.data import health


def _collector() -> health._FindingCollector:
    return health._FindingCollector("output", "atp")


def _only(out: health._FindingCollector, code: str) -> health.HealthFinding:
    hits = [finding for finding in out.findings if finding.code == code]
    assert len(hits) == 1
    return hits[0]


def _invalid_prediction(row: dict, label: str) -> health.HealthFinding:
    out = _collector()
    health._check_prediction_evidence(
        out,
        "atp",
        label,
        None,
        row.get("playerA"),
        row.get("playerB"),
        entity=health._match_entity(
            row,
            player_a=row.get("playerA"),
            player_b=row.get("playerB"),
        ),
    )
    return _only(out, "output.prediction_evidence.payload_invalid")


def test_prediction_identity_prefers_match_id_over_names_orientation_and_prose():
    original = {
        "matchId": "provider-match-17",
        "espnId": "event-4",
        "event": "Old Sponsor Open",
        "playerA": "Alpha Player",
        "playerB": "Beta Player",
    }
    renamed = {
        **original,
        "event": "New Sponsor Championships",
        "playerA": "B. Player",
        "playerB": "A. Player",
    }

    first = _invalid_prediction(original, "old presentation label")
    second = _invalid_prediction(renamed, "rewritten presentation label")
    distinct = _invalid_prediction(
        {**renamed, "matchId": "provider-match-18"},
        "rewritten presentation label",
    )

    assert first.entity == second.entity == "match:provider-match-17"
    assert first.fingerprint == second.fingerprint
    assert distinct.fingerprint != first.fingerprint


def test_match_fallback_uses_event_id_and_unordered_canonical_pair():
    first_row = {
        "espnId": "event-9",
        "event": "Old Sponsor Open",
        "playerA": "Alpha Player",
        "playerB": "Beta Player",
    }
    reversed_row = {
        **first_row,
        "event": "New Sponsor Open",
        "playerA": "Beta Player",
        "playerB": "Alpha Player",
    }

    first = _invalid_prediction(first_row, "Alpha Player vs Beta Player")
    reversed_finding = _invalid_prediction(reversed_row, "Beta Player vs Alpha Player")
    other_event = _invalid_prediction(
        {**reversed_row, "espnId": "event-10"},
        "Beta Player vs Alpha Player",
    )

    assert first.entity == "espn:event-9#players:alpha player:beta player"
    assert reversed_finding.fingerprint == first.fingerprint
    assert other_event.fingerprint != first.fingerprint


def test_event_identity_bridges_espn_coverage_key_and_late_explicit_id():
    coverage_only = {"espnId": None, "coverageKey": "espn:875-2026"}
    explicit = {"espnId": "875-2026", "coverageKey": "espn:875-2026"}
    snake_fallback = {"espnId": "", "espn_id": "875-2026"}

    assert health._event_entity(coverage_only) == "espn:875-2026"
    assert health._event_entity(explicit) == health._event_entity(coverage_only)
    assert health._event_entity(snake_fallback) == health._event_entity(coverage_only)


def test_event_coverage_finding_uses_canonical_espn_event_entity():
    coverage = {
        "version": 1,
        "tour": "atp",
        "events": [{"key": "espn:875-2026", "name": "Sponsor Open"}],
        "shippedKeys": [],
        "shellKeys": [],
    }
    out = _collector()

    health._check_event_coverage(out, "atp", coverage, [])

    finding = _only(out, "output.event_coverage.missing_card")
    assert finding.entity == "espn:875-2026"


def test_forecast_label_is_message_only_when_match_identity_is_supplied():
    forecast = {"timeline": []}
    out_a, out_b = _collector(), _collector()
    health._check_forecast_history(
        out_a,
        "atp",
        "old sponsor: Alpha vs Beta",
        forecast,
        entity="match:provider-match-17",
    )
    health._check_forecast_history(
        out_b,
        "atp",
        "new sponsor: Beta vs Alpha",
        forecast,
        entity="match:provider-match-17",
    )

    first = _only(out_a, "output.forecast.timeline_missing")
    second = _only(out_b, "output.forecast.timeline_missing")
    assert first.fingerprint == second.fingerprint
    assert first.revision != second.revision


def _tournament(name: str, espn_id: str) -> dict:
    return {
        "name": name,
        "espnId": espn_id,
        "surface": "Hard",
        "level": "ATP 500",
        "bestOf": 3,
        "status": "live",
        "drawStatus": "real",
        "drawSize": 32,
        "aliveCount": 16,
        "champion": None,
        "hasBracket": False,
        "projection": [{
            "name": "Alpha Player",
            "champion": 1.2,
            "final": 0.5,
            "sf": 0.7,
            "reach": {},
        }],
    }


def _projection_finding(name: str, espn_id: str) -> health.HealthFinding:
    out = _collector()
    health._check_tournament(out, "atp", _tournament(name, espn_id))
    return _only(out, "output.projection.probability_invalid")


def test_projection_inherits_stable_tournament_entity_across_sponsor_rename():
    old = _projection_finding("Old Sponsor Open", "event-12")
    renamed = _projection_finding("New Sponsor Championships", "event-12")
    distinct = _projection_finding("New Sponsor Championships", "event-13")

    assert old.entity == renamed.entity == "espn:event-12#player:alpha player#stage:champion"
    assert old.fingerprint == renamed.fingerprint
    assert distinct.fingerprint != old.fingerprint


def _bracket(name: str, espn_id: str) -> dict:
    return {
        "name": name,
        "espnId": espn_id,
        "start": "2026-08-17",
        "end": "2026-08-23",
        "status": "upcoming",
        "drawSize": 2,
        "bracketSize": 2,
        "drawSource": "wikipedia",
        "drawSourceId": "stable-draw-id",
        "drawSourceUrl": "https://en.wikipedia.org/wiki/Stable_draw",
        "rounds": [{
            "round": "F",
            "matches": [{
                "a": "TBD",
                "b": "Alpha Player",
                "winner": None,
                "p": None,
                "probSource": None,
            }],
        }],
    }


def _bracket_placeholder(name: str, espn_id: str) -> health.HealthFinding:
    out = _collector()
    health._check_brackets(out, "atp", [_bracket(name, espn_id)], tournaments=None)
    return _only(out, "output.participant.placeholder_name")


def test_bracket_placeholder_inherits_event_entity_not_where_prose():
    old = _bracket_placeholder("Old Sponsor Open", "event-21")
    renamed = _bracket_placeholder("New Sponsor Open", "event-21")
    distinct = _bracket_placeholder("New Sponsor Open", "event-22")

    assert old.entity == renamed.entity == "espn:event-21"
    assert old.fingerprint == renamed.fingerprint
    assert distinct.fingerprint != old.fingerprint


def test_bracket_tournament_join_survives_sponsor_rename_by_event_identity():
    bracket = _bracket("Old Sponsor Open", "event-41")
    bracket.update(status="completed", champion="Alpha Player")
    bracket["rounds"][0]["matches"][0].update(
        a="Alpha Player",
        b="Beta Player",
        winner="a",
        p=0.6,
        probSource="model",
    )
    tournament = _tournament("New Sponsor Championships", "event-41")
    tournament.update(
        status="completed",
        drawSize=4,
        aliveCount=1,
        champion="Beta Player",
        hasBracket=True,
    )

    out = _collector()
    health._check_brackets(out, "atp", [bracket], [tournament])
    by_code = {finding.code: finding for finding in out.findings}

    assert by_code["output.bracket.tournament_draw_size_mismatch"].evidence == {
        "bracketDrawSize": 2,
        "tournamentDrawSize": 4,
    }
    assert by_code["output.bracket.tournament_champion_mismatch"].evidence == {
        "bracketChampion": "'Alpha Player'",
        "tournamentChampion": "'Beta Player'",
    }
    assert "output.bracket.entry_missing" not in by_code
    assert "output.bracket.tournament_missing" not in by_code
    assert all(
        finding.entity == "espn:event-41"
        for code, finding in by_code.items()
        if code.startswith("output.bracket.tournament_")
    )

    legacy: list[str] = []
    health._check_brackets(legacy, "atp", [bracket], [tournament])
    assert any(
        "bracket 'Old Sponsor Open' drawSize 2 != tournaments.json 4" in message
        for message in legacy
    )
    assert any(
        "bracket 'Old Sponsor Open' champion 'Alpha Player' != tournaments.json "
        "'Beta Player'" in message
        for message in legacy
    )


def test_bracket_tournament_join_rejects_same_title_with_different_event_ids():
    bracket = _bracket("Shared Open", "event-51")
    bracket["rounds"][0]["matches"][0].update(
        a="Alpha Player",
        b="Beta Player",
    )
    tournament = _tournament("Shared Open", "event-52")
    tournament.update(
        start="2026-08-17",
        end="2026-08-23",
        drawSize=2,
        hasBracket=True,
        projection=[{"name": "Alpha Player"}, {"name": "Beta Player"}],
    )

    out = _collector()
    health._check_brackets(out, "atp", [bracket], [tournament])
    by_code = {finding.code: finding for finding in out.findings}

    assert by_code["output.bracket.entry_missing"].entity == "espn:event-52"
    assert by_code["output.bracket.entry_missing"].evidence == {}
    assert by_code["output.bracket.tournament_missing"].entity == "espn:event-51"
    assert by_code["output.bracket.tournament_missing"].evidence == {}
    assert "output.bracket.tournament_draw_size_mismatch" not in by_code
    assert "output.bracket.tournament_champion_mismatch" not in by_code

    legacy: list[str] = []
    health._check_brackets(legacy, "atp", [bracket], [tournament])
    assert "atp: tournaments.json 'Shared Open' hasBracket but no brackets.json entry" in legacy
    assert "atp: brackets.json entry 'shared open' has no tournaments.json event" in legacy


def _idless_bracket_and_tournament() -> tuple[dict, dict]:
    bracket = _bracket("Archive City", "")
    bracket["rounds"][0]["matches"][0].update(
        a="Alpha Player",
        b="Beta Player",
    )
    tournament = _tournament("Current Sponsor Championships", "")
    tournament.update(
        start="2026-08-17",
        end="2026-08-23",
        drawSize=4,
        hasBracket=True,
        projection=[{"name": "Alpha Player"}, {"name": "Beta Player"}],
    )
    return bracket, tournament


def test_bracket_tournament_evidence_join_allows_id_only_on_bracket():
    bracket, tournament = _idless_bracket_and_tournament()
    bracket["espnId"] = "event-61"
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [tournament])

    mismatch = _only(out, "output.bracket.tournament_draw_size_mismatch")
    codes = [finding.code for finding in out.findings]
    assert mismatch.entity == "espn:event-61"
    assert "output.bracket.entry_missing" not in codes
    assert "output.bracket.tournament_missing" not in codes


def test_bracket_tournament_evidence_join_allows_id_only_on_tournament():
    bracket, tournament = _idless_bracket_and_tournament()
    tournament["espnId"] = "event-62"
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [tournament])

    mismatch = _only(out, "output.bracket.tournament_draw_size_mismatch")
    codes = [finding.code for finding in out.findings]
    assert mismatch.entity == "espn:event-62"
    assert "output.bracket.entry_missing" not in codes
    assert "output.bracket.tournament_missing" not in codes


def test_idless_bracket_tournament_join_requires_date_and_player_evidence():
    bracket, tournament = _idless_bracket_and_tournament()
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [tournament])

    by_code = {finding.code: finding for finding in out.findings}
    assert by_code["output.bracket.tournament_draw_size_mismatch"].evidence == {
        "bracketDrawSize": 2,
        "tournamentDrawSize": 4,
    }
    assert "output.bracket.entry_missing" not in by_code
    assert "output.bracket.tournament_missing" not in by_code


def test_idless_bracket_tournament_join_rejects_disjoint_dates():
    bracket, tournament = _idless_bracket_and_tournament()
    tournament.update(start="2026-09-01", end="2026-09-07")
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [tournament])

    codes = [finding.code for finding in out.findings]
    assert "output.bracket.tournament_draw_size_mismatch" not in codes
    assert "output.bracket.entry_missing" in codes
    assert "output.bracket.tournament_missing" in codes


def test_idless_bracket_tournament_join_rejects_date_only_match():
    bracket, tournament = _idless_bracket_and_tournament()
    tournament["projection"] = [
        {"name": "Gamma Player"},
        {"name": "Delta Player"},
    ]
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [tournament])

    codes = [finding.code for finding in out.findings]
    assert "output.bracket.tournament_draw_size_mismatch" not in codes
    assert "output.bracket.entry_missing" in codes
    assert "output.bracket.tournament_missing" in codes


def test_idless_bracket_tournament_join_rejects_ambiguous_player_evidence():
    bracket, first = _idless_bracket_and_tournament()
    second = copy.deepcopy(first)
    second.update(
        name="Other Concurrent Open",
        start="2026-08-18",
        end="2026-08-24",
    )
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [first, second])

    codes = [finding.code for finding in out.findings]
    assert "output.bracket.tournament_draw_size_mismatch" not in codes
    assert codes.count("output.bracket.entry_missing") == 2
    assert codes.count("output.bracket.tournament_missing") == 1


def test_one_sided_bracket_tournament_join_rejects_disjoint_dates():
    bracket, tournament = _idless_bracket_and_tournament()
    bracket["espnId"] = "event-63"
    tournament.update(start="2026-09-01", end="2026-09-07")
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [tournament])

    codes = [finding.code for finding in out.findings]
    assert "output.bracket.tournament_draw_size_mismatch" not in codes
    assert "output.bracket.entry_missing" in codes
    assert "output.bracket.tournament_missing" in codes


def test_one_sided_bracket_tournament_join_rejects_ambiguous_evidence():
    bracket, first = _idless_bracket_and_tournament()
    bracket["espnId"] = "event-64"
    second = copy.deepcopy(first)
    second.update(name="Other Concurrent Open", start="2026-08-18", end="2026-08-24")
    out = _collector()

    health._check_brackets(out, "atp", [bracket], [first, second])

    codes = [finding.code for finding in out.findings]
    assert "output.bracket.tournament_draw_size_mismatch" not in codes
    assert codes.count("output.bracket.entry_missing") == 2
    assert codes.count("output.bracket.tournament_missing") == 1


def _minimal_output(card: dict) -> dict:
    return {
        "data": {"tournaments": [card]},
        "missing": [],
        "corrupt": [],
        "shards": {},
        "missing_files": [],
        "corrupt_files": [],
        "draw_cache": None,
        "forecast": None,
        "kalshi_ledger": None,
    }


def test_lost_bracket_uses_persisted_event_identity_across_sponsor_rename():
    card = _tournament("New Sponsor Championships", "event-31")
    card["projection"] = []
    previous = {
        "bracket_event_entities": {"espn:event-31": "Old Sponsor Open"},
        "bracket_events": ["old sponsor open"],
    }

    findings = health.output_findings(
        "atp",
        _minimal_output(copy.deepcopy(card)),
        pd.Timestamp("2026-08-23"),
        prev=previous,
    )
    lost = [finding for finding in findings
            if finding.code == "output.tournament.bracket_lost"]

    assert len(lost) == 1
    assert lost[0].entity == "espn:event-31"
    assert lost[0].evidence == {
        "previousName": "Old Sponsor Open",
        "currentName": "New Sponsor Championships",
    }


def _lost_bracket_findings(card: dict, previous: dict) -> list[health.HealthFinding]:
    return [
        finding for finding in health.output_findings(
            "atp",
            _minimal_output(copy.deepcopy(card)),
            pd.Timestamp("2026-08-23"),
            prev=previous,
        )
        if finding.code == "output.tournament.bracket_lost"
    ]


def test_lost_bracket_baseline_survives_repeated_loss_until_event_exits():
    missing = _tournament("New Sponsor Championships", "event-31")
    missing["projection"] = []
    previous = {
        "bracket_event_entities": {"espn:event-31": "Old Sponsor Open"},
        "bracket_events": ["old sponsor open"],
    }

    first = _lost_bracket_findings(missing, previous)
    first_state = {
        "bracket_event_entities": health._remembered_bracket_event_entities(
            [missing], previous),
        "bracket_events": [],
    }
    second = _lost_bracket_findings(missing, first_state)

    assert len(first) == len(second) == 1
    assert first[0].fingerprint == second[0].fingerprint
    assert first[0].revision == second[0].revision
    assert first_state["bracket_event_entities"] == {
        "espn:event-31": "Old Sponsor Open",
    }

    restored = {**missing, "hasBracket": True}
    assert _lost_bracket_findings(restored, first_state) == []
    restored_state = {
        "bracket_event_entities": health._remembered_bracket_event_entities(
            [restored], first_state),
    }
    assert restored_state["bracket_event_entities"] == {
        "espn:event-31": "New Sponsor Championships",
    }

    completed = {**missing, "status": "completed", "champion": "Alpha Player",
                 "aliveCount": 1}
    assert _lost_bracket_findings(completed, first_state) == []
    assert health._remembered_bracket_event_entities([completed], first_state) == {}
    assert health._remembered_bracket_event_entities([], first_state) == {}


def _forecast_output(lines: int) -> dict:
    output = _minimal_output({})
    output["data"] = {}
    output["forecast"] = {"lines": lines, "max_as_of": "2026-08-23"}
    return output


def _forecast_shrink(lines: int, previous: dict) -> list[health.HealthFinding]:
    return [
        finding for finding in health.output_findings(
            "atp", _forecast_output(lines), pd.Timestamp("2026-08-23"), prev=previous)
        if finding.code == "output.forecast_log.shrank"
    ]


def test_forecast_log_high_water_survives_repeated_shrink_and_advances_on_new_high():
    legacy = {"forecast_lines": 200}
    first = _forecast_shrink(100, legacy)
    first_state = {
        "forecast_lines": 100,
        "forecast_high_water_lines": health._forecast_high_water(100, legacy),
    }
    second = _forecast_shrink(100, first_state)

    assert len(first) == len(second) == 1
    assert first[0].fingerprint == second[0].fingerprint
    assert first[0].revision == second[0].revision
    assert first_state["forecast_high_water_lines"] == 200

    recovered_state = {
        "forecast_lines": 200,
        "forecast_high_water_lines": health._forecast_high_water(200, first_state),
    }
    assert _forecast_shrink(200, first_state) == []
    assert recovered_state["forecast_high_water_lines"] == 200

    new_high_state = {
        "forecast_lines": 250,
        "forecast_high_water_lines": health._forecast_high_water(250, recovered_state),
    }
    assert _forecast_shrink(250, recovered_state) == []
    assert new_high_state["forecast_high_water_lines"] == 250
    later_shrink = _forecast_shrink(240, new_high_state)
    assert len(later_shrink) == 1
    assert later_shrink[0].evidence["highWaterLines"] == 250


def test_forecast_log_disappearance_stays_active_until_high_water_is_restored():
    first_previous = {"forecast_lines": 200}
    missing = _forecast_output(0)
    missing["forecast"] = None

    first = [
        finding for finding in health.output_findings(
            "atp", missing, pd.Timestamp("2026-08-23"), prev=first_previous)
        if finding.code == "output.forecast_log.shrank"
    ]
    repeated_previous = {
        "forecast_lines": None,
        "forecast_high_water_lines": health._forecast_high_water(None, first_previous),
    }
    repeated = [
        finding for finding in health.output_findings(
            "atp", missing, pd.Timestamp("2026-08-23"), prev=repeated_previous)
        if finding.code == "output.forecast_log.shrank"
    ]

    assert len(first) == len(repeated) == 1
    assert first[0].fingerprint == repeated[0].fingerprint
    assert first[0].revision == repeated[0].revision
    assert first[0].evidence == {
        "highWaterLines": 200,
        "lines": 0,
        "artifactState": "absent",
    }
    assert "forecast log disappeared after reaching 200 lines" in first[0].message
    assert any(
        "forecast log disappeared after reaching 200 lines" in problem
        for problem in health.output_problems(
            "atp", missing, pd.Timestamp("2026-08-23"), prev=repeated_previous)
    )

    restored = _forecast_output(200)
    assert _forecast_shrink(200, repeated_previous) == []
    assert not any(
        finding.code == "output.forecast_log.shrank"
        for finding in health.output_findings(
            "atp", restored, pd.Timestamp("2026-08-23"), prev=repeated_previous)
    )

    # A missing log without any prior persisted baseline is a valid fresh clone.
    assert not any(
        finding.code == "output.forecast_log.shrank"
        for finding in health.output_findings(
            "atp", missing, pd.Timestamp("2026-08-23"), prev={})
    )


def _cross_card(name: str, espn_id: str, surface: str) -> dict:
    return {
        "name": name,
        "espnId": espn_id,
        "surface": surface,
        "start": "2026-08-17",
        "end": "2026-08-23",
    }


def _cross_outputs(atp: dict, wta: dict) -> dict:
    return {
        "atp": {"data": {"tournaments": [atp]}},
        "wta": {"data": {"tournaments": [wta]}},
    }


def test_cross_tour_join_uses_shared_espn_id_not_sponsor_title():
    findings = health.cross_tour_findings(_cross_outputs(
        _cross_card("ATP Sponsor Open", "shared-44", "Hard"),
        _cross_card("WTA Sponsor Championships", "shared-44", "Clay"),
    ))

    assert len(findings) == 1
    assert findings[0].code == "cross.tournament.surface_mismatch"
    assert findings[0].entity == "espn:shared-44"


def test_cross_tour_join_rejects_same_name_with_different_espn_ids():
    findings = health.cross_tour_findings(_cross_outputs(
        _cross_card("Shared Display Name", "atp-44", "Hard"),
        _cross_card("Shared Display Name", "wta-44", "Clay"),
    ))

    assert findings == []


def test_cross_tour_shared_espn_id_cannot_be_hidden_by_bad_dates():
    atp = _cross_card("ATP Sponsor Open", "shared-44", "Hard")
    wta = _cross_card("WTA Sponsor Championships", "shared-44", "Clay")
    wta.update(start=None, end=None)

    findings = health.cross_tour_findings(_cross_outputs(atp, wta))
    assert len(findings) == 1 and findings[0].entity == "espn:shared-44"


def _source_health(status: str, *, failed: int, completed_at: str,
                   last_good_at: str) -> dict:
    attempted = 28
    return {
        "result_age_days": 1,
        "stats_age_days": 2,
        "cur_year_stats_fraction": 0.9,
        "cur_year_matches": 500,
        "fresh_age_days": 3,
        "charting_age_days": 30,
        "espn_acquisition": {
            "schema": "espn-acquisition-v1",
            "tour": "atp",
            "completedAt": completed_at,
            "status": status,
            "eventCount": 0 if status == "total_transport_failure" else 1,
            "queries": {
                "attempted": attempted,
                "succeeded": attempted - failed,
                "failed": failed,
                "featuredSucceeded": failed == 0,
                "failedKeys": ["featured"] if failed else [],
                "failureTypes": {"OSError": failed} if failed else {},
            },
            "overlay": {
                "status": "retained_last_good" if failed == attempted else "partially_updated",
                "updatedFiles": ["2026.csv"] if failed != attempted else [],
                "retainedFiles": ["2025.csv"],
                "lastGoodAt": last_good_at,
            },
        },
    }


def _espn_source_finding(state: dict) -> health.HealthFinding:
    return next(
        finding for finding in health.source_findings(
            "atp", state, pd.Timestamp("2026-08-23"))
        if finding.code.startswith("source.espn.")
    )


def test_espn_partial_finding_revision_ignores_receipt_timestamps():
    first = _espn_source_finding(_source_health(
        "partial_query_failure",
        failed=1,
        completed_at="2026-08-23T10:00:00Z",
        last_good_at="2026-08-23T09:00:00Z",
    ))
    later = _espn_source_finding(_source_health(
        "partial_query_failure",
        failed=1,
        completed_at="2026-08-23T11:00:00Z",
        last_good_at="2026-08-23T10:00:00Z",
    ))

    assert first.fingerprint == later.fingerprint
    assert first.revision == later.revision
    assert "completedAt" not in first.evidence
    assert "lastGoodAt" not in first.evidence["overlay"]


def test_espn_total_failure_revision_ignores_receipt_timestamps():
    first = _espn_source_finding(_source_health(
        "total_transport_failure",
        failed=28,
        completed_at="2026-08-23T10:00:00Z",
        last_good_at="2026-08-22T22:00:00Z",
    ))
    later = _espn_source_finding(_source_health(
        "total_transport_failure",
        failed=28,
        completed_at="2026-08-23T11:00:00Z",
        last_good_at="2026-08-23T09:00:00Z",
    ))

    assert first.code == later.code == "source.espn.total_transport_failure"
    assert first.fingerprint == later.fingerprint
    assert first.revision == later.revision


def test_espn_revision_tracks_failed_query_identity_and_error_type():
    first_state = _source_health(
        "partial_query_failure", failed=1,
        completed_at="2026-08-23T10:00:00Z", last_good_at="2026-08-23T09:00:00Z")
    changed_state = copy.deepcopy(first_state)
    changed_state["espn_acquisition"]["queries"].update(
        failedKeys=["date:2026-08-23"], failureTypes={"TimeoutError": 1})

    first = _espn_source_finding(first_state)
    changed = _espn_source_finding(changed_state)

    assert first.fingerprint == changed.fingerprint
    assert first.revision != changed.revision
    assert changed.evidence["queries"]["failedKeys"] == ["date:2026-08-23"]
    assert changed.evidence["queries"]["failureTypes"] == {"TimeoutError": 1}
