"""Pure tests for the Tennis Abstract comparison report."""

from __future__ import annotations

import json
import math

import pytest
from tennis_model.eval import tennis_abstract_report as report

CAPTURE = "2026-08-30T12:00:00Z"


def _snapshot(players, *, rounds=None):
    return {
        "schema": "external-tournament-forecast-snapshot-v1",
        "benchmark": "tennis-abstract",
        "tour": "atp",
        "event": "US Open",
        "espnId": "18910",
        "season": 2026,
        "source": {
            "name": "Tennis Abstract",
            "url": "https://www.tennisabstract.com/current/2026USOpenMenForecast.html",
            "capturedAt": CAPTURE,
            "normalizedSha256": "abc123",
        },
        "rounds": rounds or ["R64", "R32", "R16", "QF", "SF", "F", "W"],
        "players": [
            {"drawPosition": index + 1, "name": name, "probabilities": probabilities}
            for index, (name, probabilities) in enumerate(players)
        ],
    }


def _two_pair_snapshot():
    return _snapshot([
        ("Daniel Merida Aguilar", {"R64": 0.7004, "R32": 0.40, "R16": 0.2,
                                   "QF": 0.1, "SF": 0.05, "F": 0.02, "W": 0.01}),
        ("Bob", {"R64": 0.2996, "R32": 0.10, "R16": 0.05,
                 "QF": 0.02, "SF": 0.01, "F": 0.004, "W": 0.001}),
        ("Cara", {"R64": 0.4004, "R32": 0.20, "R16": 0.1,
                  "QF": 0.05, "SF": 0.02, "F": 0.01, "W": 0.003}),
        ("Dana", {"R64": 0.5996, "R32": 0.30, "R16": 0.15,
                  "QF": 0.08, "SF": 0.04, "F": 0.02, "W": 0.006}),
    ])


def _quote(a, b, p, as_of, *, kind="match_snapshot", event_id="18910", rnd="R128"):
    return {
        "type": kind,
        "tour": "atp",
        "event": "A sponsor name is irrelevant",
        "espnId": event_id,
        "season": 2026,
        "round": rnd,
        "as_of": as_of,
        "playerA": a,
        "playerB": b,
        "p": p,
    }


def _result(winner, loser, *, started="2026-08-31T16:00:00Z", result_type="completed",
            event_id="18910", rnd="R128"):
    return {
        "espnId": event_id,
        "season": 2026,
        "round": rnd,
        "startedAt": started,
        "winner_name": winner,
        "loser_name": loser,
        "completed": True,
        "result_type": result_type,
    }


def test_time_aligned_exact_pairs_aliases_orientation_and_paired_scores():
    snapshot = _two_pair_snapshot()
    forecasts = [
        # The explicit alias makes this an exact identity match. The 13:00 quote is after
        # the external capture and must not leak into scoring.
        _quote("Daniel Merida", "Bob", 0.60, "2026-08-30T08:00:00Z", kind="match"),
        _quote("Daniel Merida", "Bob", 0.65, "2026-08-30T11:00:00Z"),
        _quote("Daniel Merida", "Bob", 0.99, "2026-08-30T13:00:00Z"),
        # Stored in the opposite orientation: P(Cara)=1-.55=.45.
        _quote("Dana", "Cara", 0.55, "2026-08-30T10:00:00Z"),
    ]
    results = [_result("Daniel Merida", "Bob"), _result("Dana", "Cara")]

    rows = report.evaluate_matches(snapshot, forecasts, results)
    assert [(row["pTennisAbstract"], row["pDeuce"], row["aWon"])
            for row in rows] == [(0.7, 0.65, True), (0.4, 0.45, False)]
    assert rows[0]["round"] == "R128"

    payload = report.build_public_report(snapshot, forecasts, results)
    comparison = payload["matchComparison"]
    assert payload["schema"] == "tennis-abstract-benchmark-v1"
    assert payload["status"] == "complete"
    assert (comparison["eligible"], comparison["graded"], comparison["pending"],
            comparison["excluded"]) == (2, 2, 0, 0)
    expected_deuce_ll = (-math.log(0.65) - math.log(0.55)) / 2
    expected_external_ll = (-math.log(0.7) - math.log(0.6)) / 2
    assert comparison["deuce"]["logloss"] == pytest.approx(expected_deuce_ll)
    assert comparison["tennisAbstract"]["logloss"] == pytest.approx(expected_external_ll)
    assert comparison["paired"]["loglossDelta"] == pytest.approx(
        expected_external_ll - expected_deuce_ll)
    assert comparison["paired"]["seLogloss"] > 0
    assert comparison["byRound"][0]["round"] == "R128"
    assert comparison["byRound"][0]["graded"] == 2


def test_timing_fails_closed_and_explicit_match_ids_are_the_only_date_less_escape_hatch():
    snapshot = _snapshot([
        ("Alice", {"R64": 0.6}),
        ("Bob", {"R64": 0.4}),
    ])
    forecasts = [_quote("Alice", "Bob", 0.55, "2026-08-30T11:00:00Z")]
    date_only_result = _result("Alice", "Bob", started=None)

    unproven = report.build_public_report(snapshot, forecasts, [date_only_result])
    assert unproven["matchComparison"]["eligible"] == 0
    assert unproven["matchComparison"]["exclusionReasons"] == {
        "prestart_timing_unproven": 1,
    }

    match_ids = report.snapshot_match_ids(snapshot)
    assert len(match_ids) == 1 and "|espn:18910|2026|R128|" in match_ids[0]
    explicit = report.build_public_report(
        snapshot, forecasts, [date_only_result], eligible_match_ids=match_ids)
    assert explicit["matchComparison"]["graded"] == 1

    already_started = _result("Alice", "Bob", started="2026-08-30T11:59:59Z")
    excluded = report.build_public_report(
        snapshot, forecasts, [already_started], eligible_match_ids=match_ids)
    assert excluded["matchComparison"]["graded"] == 0
    assert excluded["matchComparison"]["exclusionReasons"] == {
        "capture_not_prestart": 1,
    }


@pytest.mark.parametrize(
    ("players", "reason"),
    [
        ([
            ("Alice", {"R64": 0.6}),
            ("Bob", {"R64": 0.5}),
        ], "external_pair_mass_invalid"),
        ([
            ("Alice", {"R64": "bad"}),
            ("Bob", {"R64": 0.4}),
        ], "external_probability_malformed"),
    ],
)
def test_external_probability_exclusions_are_explicit(players, reason):
    payload = report.build_public_report(_snapshot(players), [], [])
    assert payload["matchComparison"]["excluded"] == 1
    assert payload["matchComparison"]["exclusionReasons"] == {reason: 1}


def test_no_fuzzy_name_matching_and_no_event_name_join():
    snapshot = _snapshot([
        ("Ann Lee", {"R64": 0.6}),
        ("Bob", {"R64": 0.4}),
    ])
    match_ids = report.snapshot_match_ids(snapshot)
    # Ann Li is deliberately not Ann Lee, however similar the strings look. A matching
    # display event name under the wrong stable id is also irrelevant.
    forecasts = [
        _quote("Ann Li", "Bob", 0.6, "2026-08-30T10:00:00Z"),
        _quote("Ann Lee", "Bob", 0.6, "2026-08-30T10:00:00Z", event_id="wrong"),
    ]
    payload = report.build_public_report(
        snapshot, forecasts, [], eligible_match_ids=match_ids)
    assert payload["matchComparison"]["exclusionReasons"] == {
        "deuce_pair_mismatch": 1,
    }


def test_missing_quote_pair_mismatch_walkover_and_retirement_are_separate_reasons():
    snapshot = _two_pair_snapshot()
    ids = report.snapshot_match_ids(snapshot)
    # First pair has no DEUCE quote. Second has an exact quote but a replacement result.
    forecasts = [_quote("Cara", "Dana", 0.4, "2026-08-30T10:00:00Z")]
    replacement = _result("Cara", "Eve", started=None)
    payload = report.build_public_report(
        snapshot, forecasts, [replacement], eligible_match_ids=ids)
    assert payload["matchComparison"]["exclusionReasons"] == {
        "deuce_quote_missing": 1,
        "result_pair_mismatch": 1,
    }

    one = _snapshot([("Alice", {"R64": 0.6}), ("Bob", {"R64": 0.4})])
    quote = [_quote("Alice", "Bob", 0.6, "2026-08-30T10:00:00Z")]
    walkover = report.build_public_report(one, quote, [
        _result("Alice", "Bob", result_type="walkover")])
    assert walkover["matchComparison"]["exclusionReasons"] == {"walkover": 1}
    retired_result = [_result("Alice", "Bob", result_type="retired")]
    retirement = report.build_public_report(one, quote, retired_result)
    assert retirement["matchComparison"]["exclusionReasons"] == {"retirement": 1}
    sensitivity = report.build_public_report(
        one, quote, retired_result, include_retirements=True)
    assert sensitivity["matchComparison"]["graded"] == 1


@pytest.mark.parametrize(
    ("score", "walkover", "reason"),
    [
        ("W/O", True, "walkover"),
        ("6-4 2-1 RET", False, "retirement"),
    ],
)
def test_actual_incomplete_result_rows_are_excluded_but_resolve_advancement(
    score: str, walkover: bool, reason: str,
) -> None:
    snapshot = _snapshot([
        ("Alice", {"R64": 0.6, "W": 0.2}),
        ("Bob", {"R64": 0.4, "W": 0.1}),
    ], rounds=["R64", "W"])
    quote = [_quote("Alice", "Bob", 0.6, "2026-08-30T10:00:00Z")]
    result = _result("Alice", "Bob")
    result.update({
        "completed": False,
        "walkover": walkover,
        "score": score,
    })
    deuce = [
        {"name": "Alice", "reach": {"R64": 0.55, "Champion": 0.2}},
        {"name": "Bob", "reach": {"R64": 0.45, "Champion": 0.1}},
    ]

    payload = report.build_public_report(
        snapshot, quote, [result], deuce_stage_probabilities=deuce)

    assert payload["matchComparison"]["graded"] == 0
    assert payload["matchComparison"]["exclusionReasons"] == {reason: 1}
    reach = payload["reachComparison"]
    r64 = next(stage for stage in reach["stages"] if stage["stage"] == "R64")
    assert r64["resolved"] == r64["graded"] == 2


def test_display_rounding_and_rounded_zero_log_loss_clip():
    assert report._display_probability(0.5005) == 0.501
    snapshot = _snapshot([
        ("Alice", {"R64": 0.0004}),
        ("Bob", {"R64": 0.9996}),
    ])
    forecasts = [_quote("Alice", "Bob", 0.00049, "2026-08-30T10:00:00Z")]
    payload = report.build_public_report(snapshot, forecasts, [_result("Alice", "Bob")])
    comparison = payload["matchComparison"]
    assert comparison["deuce"]["logloss"] == pytest.approx(-math.log(0.0005))
    assert comparison["tennisAbstract"]["logloss"] == pytest.approx(-math.log(0.0005))
    assert comparison["deuce"]["brier"] == 1.0
    assert comparison["tennisAbstract"]["brier"] == 1.0
    assert comparison["paired"]["loglossDelta"] == pytest.approx(0.0)
    assert comparison["paired"]["seLogloss"] is None
    assert comparison["paired"]["seBrier"] is None


def test_reach_stage_macro_and_champion_scores_use_full_field_without_naive_se():
    snapshot = _snapshot([
        ("Alice", {"F": 0.8, "W": 0.5}),
        ("Bob", {"F": 0.2, "W": 0.1}),
        ("Cara", {"F": 0.6, "W": 0.3}),
        ("Dana", {"F": 0.4, "W": 0.1}),
    ], rounds=["F", "W"])
    deuce = [
        {"name": "Alice", "reach": {"F": 0.7, "Champion": 0.4}},
        {"name": "Bob", "reach": {"F": 0.3, "Champion": 0.2}},
        {"name": "Cara", "reach": {"F": 0.55, "Champion": 0.25}},
        {"name": "Dana", "reach": {"F": 0.45, "Champion": 0.15}},
    ]
    outcomes = {
        "champion": "Alice",
        "players": {
            "Alice": {"F": True, "W": True},
            "Bob": {"F": False, "W": False},
            "Cara": {"F": True, "W": False},
            "Dana": {"F": False, "W": False},
        },
    }

    payload = report.build_public_report(
        snapshot, [], [], deuce_stage_probabilities=deuce, stage_outcomes=outcomes)
    reach = payload["reachComparison"]
    assert reach["fieldAligned"] is True
    assert [stage["stage"] for stage in reach["stages"]] == ["F", "W"]
    assert all(stage["graded"] == 4 for stage in reach["stages"])
    assert all(stage["n"] == stage["resolved"] == 4 for stage in reach["stages"])
    assert all(stage["paired"]["seLogloss"] is None for stage in reach["stages"])
    assert reach["macro"]["stages"] == 2
    assert reach["macro"]["weighting"] == "equal-stage"
    assert reach["macro"]["paired"]["seLogloss"] is None
    assert "No naive SE" in reach["macro"]["uncertainty"]
    champion = reach["champion"]
    assert champion["status"] == "graded" and champion["champion"] == "Alice"
    assert champion["deuce"]["categoricalLogScore"] == pytest.approx(-math.log(0.4))
    assert champion["tennisAbstract"]["categoricalLogScore"] == pytest.approx(-math.log(0.5))
    assert champion["deuce"]["multiclassBrier"] == pytest.approx(
        (0.4 - 1) ** 2 + 0.2**2 + 0.25**2 + 0.15**2)


def test_reach_field_mismatch_fails_closed_and_report_is_json_deterministic():
    snapshot = _snapshot([
        ("Alice", {"F": 0.6, "W": 0.4}),
        ("Bob", {"F": 0.4, "W": 0.6}),
    ], rounds=["F", "W"])
    deuce = [{"name": "Alice", "reach": {"F": 0.6, "Champion": 0.4}}]
    first = report.build_public_report(snapshot, [], [], deuce_stage_probabilities=deuce)
    second = report.build_report(snapshot, [], [], deuce_stage_probabilities=deuce)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["reachComparison"]["fieldAligned"] is False
    assert first["reachComparison"]["stages"] == []
    assert first["reachComparison"]["exclusionReasons"] == {
        "deuce_field_player_missing": 1,
    }
    assert set(first) == {
        "schema", "benchmark", "status", "source", "matchComparison",
        "reachComparison", "caveats",
    }


def test_duplicate_or_missing_draw_positions_fail_the_snapshot_closed():
    snapshot = _snapshot([
        ("Alice", {"R64": 0.6}),
        ("Bob", {"R64": 0.4}),
    ])
    snapshot["players"][1]["drawPosition"] = 1
    payload = report.build_public_report(snapshot, [], [])
    assert payload["matchComparison"]["eligible"] == 0
    assert payload["matchComparison"]["exclusionReasons"] == {
        "draw_position_invalid": 1,
    }
