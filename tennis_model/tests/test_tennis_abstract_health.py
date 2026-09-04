from __future__ import annotations

import copy
import json
import shutil

import pandas as pd
import pytest
from tennis_model.eval import tennis_abstract_benchmark as benchmark

from tennis_model.data import health

_DIRECTION = "tennisAbstract-minus-deuce; positive favors DEUCE"


def _metrics(n: int) -> dict:
    return {
        "n": n,
        "logloss": None if n == 0 else 0.5,
        "brier": None if n == 0 else 0.2,
    }


def _paired(n: int) -> dict:
    return {
        "n": n,
        "direction": _DIRECTION,
        "loglossDelta": None if n == 0 else 0.1,
        "seLogloss": None if n < 2 else 0.0,
        "brierDelta": None if n == 0 else 0.05,
        "seBrier": None if n < 2 else 0.0,
    }


def _payload() -> dict:
    stages = [
        {
            "stage": stage,
            "n": 128,
            "resolved": 0,
            "eligible": 128,
            "graded": 0,
            "pending": 128,
            "excluded": 0,
            "deuce": _metrics(0),
            "tennisAbstract": _metrics(0),
            "paired": _paired(0),
            "exclusionReasons": {},
        }
        for stage in ("R64", "R32", "R16", "QF", "SF", "F", "W")
    ]
    match_round = {
        "round": "R128",
        "eligible": 32,
        "graded": 0,
        "pending": 32,
        "excluded": 32,
        "deuce": _metrics(0),
        "tennisAbstract": _metrics(0),
        "paired": _paired(0),
    }
    return {
        "schema": "tennis-abstract-benchmark-v1",
        "benchmark": {
            "id": "tennis-abstract",
            "name": "Tennis Abstract",
            "tour": "atp",
            "event": "US Open",
            "espnId": "189-2026",
            "season": 2026,
        },
        "status": "accruing",
        "source": {
            "name": "Tennis Abstract",
            "url": "https://www.tennisabstract.com/current/2026USOpenMenForecast.html",
            "capturedAt": "2026-08-31T00:55:47.502Z",
            "normalizedSha256": (
                "7d638fc8692e1e2f0ea64172b7f28c14299a7de3d58efa9fec9a42b8dc055ac4"
            ),
        },
        "matchComparison": {
            "eligible": 32,
            "graded": 0,
            "pending": 32,
            "excluded": 32,
            "deuce": _metrics(0),
            "tennisAbstract": _metrics(0),
            "paired": _paired(0),
            "byRound": [match_round],
            "exclusionReasons": {"prestart_timing_unproven": 32},
        },
        "reachComparison": {
            "fieldSize": 128,
            "fieldAligned": True,
            "stages": stages,
            "exclusionReasons": {},
        },
        "capture": {
            "classification": "first-post-start-capture",
            "eventTimezone": "America/New_York",
            "captureLocalDate": "2026-08-30",
            "eligibleMatchProof": (
                "saved scheduledDate is strictly after captureLocalDate"
            ),
        },
        "caveats": [
            "This first capture was made after Day 1 began.",
            "One tournament is descriptive evidence, not a model-selection result.",
        ],
        "receipts": {
            "sourceNormalizedSha256": (
                "7d638fc8692e1e2f0ea64172b7f28c14299a7de3d58efa9fec9a42b8dc055ac4"
            ),
            "predictorArtifactId": "2fa029c9-9851-4dd5-95ee-89b980284b54",
            "predictorTrainedAt": "2026-08-29T22:05:27Z",
            "forecastMalformedLinesSkipped": 0,
        },
    }


def _findings(payload: dict, tour: str = "atp") -> list[health.HealthFinding]:
    return health.output_findings(
        tour,
        {
            "data": {"tennis-abstract": payload},
            "missing": [],
            "corrupt": [],
            "missing_files": [],
            "corrupt_files": [],
            "stage_status": {"state": "missing"},
            "draw_cache_status": {"state": "missing"},
            "forecast": None,
            "kalshi_ledger": None,
        },
        pd.Timestamp("2026-08-31", tz="UTC"),
    )


def _contract_hits(payload: dict, tour: str = "atp") -> list[health.HealthFinding]:
    return [
        finding for finding in _findings(payload, tour)
        if finding.code == "output.tennis_abstract.contract_invalid"
    ]


def test_emitted_tennis_abstract_contract_is_accepted() -> None:
    assert not _contract_hits(_payload())


@pytest.mark.parametrize(
    ("mutation", "expected_problem"),
    [
        (
            lambda payload: payload["source"].__setitem__(
                "capturedAt", "2026-09-01T00:00:00Z"
            ),
            "frozen source identity",
        ),
        (
            lambda payload: payload["source"].__setitem__(
                "normalizedSha256", "0" * 64
            ),
            "frozen source identity",
        ),
        (
            lambda payload: payload["matchComparison"].update(
                eligible=0, graded=0, pending=0, excluded=0
            ),
            "match counts",
        ),
        (
            lambda payload: payload["reachComparison"].__setitem__("stages", []),
            "reach stages",
        ),
        (
            lambda payload: payload.__setitem__("status", "complete"),
            "status lifecycle",
        ),
    ],
    ids=("capture", "hash", "lost-cohort", "empty-reach", "false-complete"),
)
def test_tennis_abstract_contract_rejects_honesty_mutations(
    mutation, expected_problem: str,
) -> None:
    payload = copy.deepcopy(_payload())
    mutation(payload)
    hits = _contract_hits(payload)
    assert len(hits) == 1
    assert hits[0].severity == "error"
    assert health._gate_blocks(hits[0])
    assert expected_problem in hits[0].evidence["problems"]


def test_single_graded_match_accepts_the_reported_zero_paired_se() -> None:
    payload = _payload()
    for block in (
        payload["matchComparison"], payload["matchComparison"]["byRound"][0]
    ):
        block.update(eligible=32, graded=1, pending=31, excluded=32)
        block["deuce"] = _metrics(1)
        block["tennisAbstract"] = _metrics(1)
        block["paired"] = _paired(1)
    assert not _contract_hits(payload)


def test_champion_multiclass_brier_uses_its_two_point_upper_bound() -> None:
    payload = _payload()
    champion_metrics = {"n": 1, "logloss": 1.0, "brier": 1.5}
    payload["reachComparison"]["champion"] = {
        "status": "graded",
        "n": 1,
        "resolved": 1,
        "champion": "Alpha One",
        "deuce": dict(champion_metrics),
        "tennisAbstract": dict(champion_metrics),
        "paired": _paired(1),
    }
    assert not _contract_hits(payload)

    payload["reachComparison"]["champion"]["deuce"]["brier"] = 2.01
    hits = _contract_hits(payload)
    assert len(hits) == 1
    assert "champion distribution" in hits[0].evidence["problems"]


def test_reach_resolved_counts_must_be_monotone_by_stage() -> None:
    payload = _payload()
    later = payload["reachComparison"]["stages"][1]
    later.update(resolved=1, graded=1, pending=127)
    later["deuce"] = _metrics(1)
    later["tennisAbstract"] = _metrics(1)
    later["paired"] = _paired(1)

    hits = _contract_hits(payload)
    assert len(hits) == 1
    assert "reach resolved monotonicity" in hits[0].evidence["problems"]


@pytest.mark.parametrize("tour", ("atp", "wta"))
@pytest.mark.parametrize("completed_rounds", (0, 1, 7), ids=("pending", "in-progress", "complete"))
def test_produced_reach_reports_obey_the_gate_through_settlement(
    tmp_path, monkeypatch: pytest.MonkeyPatch, tour: str, completed_rounds: int,
) -> None:
    # Replay the actual producer with frozen evidence and synthetic bracket outcomes.
    # Hand-written pending-only payloads missed the deployment failure at graded n >= 2.
    evidence = tmp_path / "evidence"
    shutil.copytree(
        benchmark.TENNIS_ABSTRACT_DIR / tour, evidence / tour,
        ignore=shutil.ignore_patterns("comparison.jsonl"),
    )
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", evidence)
    emitted = []
    monkeypatch.setattr(
        benchmark, "write_produced_artifact",
        lambda _tour, _path, raw, **_kwargs: emitted.append(json.loads(raw)),
    )
    players = [row["name"] for row in benchmark.first_capture_snapshot(tour)["players"]]
    results = []
    for round_name in ("R128", "R64", "R32", "R16", "QF", "SF", "F")[:completed_rounds]:
        winners = []
        for winner, loser in zip(players[::2], players[1::2], strict=True):
            results.append({
                "espnId": "189-2026", "season": 2026, "round": round_name,
                "winner_name": winner, "loser_name": loser, "completed": True,
                "result_type": "completed", "startedAt": "2026-09-01T16:00:00Z",
            })
            winners.append(winner)
        players = winners
    produced = benchmark.run_benchmark(tour, object(), results)["report"]
    assert emitted == [produced]
    assert produced["status"] == ("complete" if completed_rounds == 7 else "accruing")
    assert _contract_hits(produced, tour) == []

    if completed_rounds:
        assert produced["reachComparison"]["stages"][0]["graded"] == 128
        assert produced["reachComparison"]["stages"][0]["paired"]["seLogloss"] is None
        broken = copy.deepcopy(produced)
        broken["reachComparison"]["stages"][0]["paired"]["seLogloss"] = 0.01
        broken["reachComparison"]["stages"][0]["paired"]["seBrier"] = 0.01
        findings = _contract_hits(broken, tour)
        assert len(findings) == 1
        assert health._gate_blocks(findings[0])
        assert "reach stage 'R64'" in findings[0].evidence["problems"]
