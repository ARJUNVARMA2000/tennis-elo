from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from tennis_model.eval import tennis_abstract_benchmark as benchmark
from tennis_model.eval import tennis_abstract_report as report
from tennis_model.eval import track

from tennis_model import pipeline


class _State:
    def __init__(self, names: list[str]):
        self.overall = dict.fromkeys(names, 1500.0)


class _Predictor:
    def __init__(self, names: list[str], trained_at: str):
        self.artifact_id = "predictor-before-capture"
        self.trained_at = trained_at
        self.elo = _State(names)
        self.lower_elo = None

    def _states_for(self, _a: str, _b: str):
        return self.elo, None, None

    def prediction_matrices(self, players, **_kwargs):
        n = len(players)
        matrix = np.full((n, n), 0.5)
        for i in range(n):
            for j in range(i + 1, n):
                matrix[i, j] = 0.6
                matrix[j, i] = 0.4
        return {"combiner": matrix}


def _snapshot() -> dict:
    players = [
        {"drawPosition": index, "name": name, "probabilities": {"F": 0.5, "W": 0.25}}
        for index, name in enumerate(("Alpha One", "Beta Two", "Gamma Three", "Delta Four"), 1)
    ]
    return {
        "schema": "tennis-abstract-forecast-v1",
        "event": "US Open",
        "season": 2026,
        "tour": "atp",
        "espnId": "189-2026",
        "source": {
            "provider": "Tennis Abstract",
            "url": "https://www.tennisabstract.com/current/test.html",
            "capturedAt": "2026-08-31T00:55:47.502Z",
        },
        "rounds": ["F", "W"],
        "players": players,
    }


def _comparison_snapshot() -> dict:
    snapshot = copy.deepcopy(_snapshot())
    snapshot["rounds"] = ["R64"]
    for player, probability in zip(
        snapshot["players"], (0.6, 0.4, 0.55, 0.45), strict=True
    ):
        player["probabilities"] = {"R64": probability}
    return snapshot


def _pending_comparison(snapshot: dict) -> dict:
    return {
        "matchId": benchmark.snapshot_match_ids(snapshot)[0],
        "round": "R128",
        "drawPositions": [1, 2],
        "playerA": "Alpha One",
        "playerB": "Beta Two",
        "pTennisAbstract": 0.6,
        "pDeuce": 0.58,
        "deuceAsOf": "2026-08-30T23:00:00Z",
        "status": "pending",
    }


def _record(*, as_of: str, probability: float) -> dict:
    return {
        "as_of": as_of,
        "type": "match_snapshot",
        "tour": "atp",
        "event": "US Open",
        "espnId": "189-2026",
        "season": 2026,
        "round": "SF",
        "playerA": "Alpha One",
        "playerB": "Beta Two",
        "p": probability,
        "match_id": (
            f"{track.MATCH_ID_VERSION}|espn:189-2026|2026|SF|alpha one|beta two"
        ),
    }


def test_first_capture_is_the_strict_frozen_128_player_cohort() -> None:
    for tour in ("atp", "wta"):
        snapshot = benchmark.first_capture_snapshot(tour)
        assert snapshot["schema"] == "tennis-abstract-forecast-v1"
        assert snapshot["espnId"] == "189-2026"
        assert len(snapshot["players"]) == 128
        assert snapshot["rounds"] == ["R64", "R32", "R16", "QF", "SF", "F", "W"]
        assert snapshot["source"]["captureMethod"] == "browser-dom-normalized"
        assert len(snapshot["source"]["normalizedSha256"]) == 64


def test_baseline_requires_a_pre_capture_predictor_and_conserves_stage_mass() -> None:
    snapshot = _snapshot()
    baseline = benchmark.build_deuce_baseline(
        "atp", _Predictor([row["name"] for row in snapshot["players"]], "2026-08-30T23:00:00Z"),
        snapshot,
    )
    assert len(baseline["players"]) == 4
    assert sum(row["probabilities"]["F"] for row in baseline["players"]) == pytest.approx(2)
    assert sum(row["probabilities"]["W"] for row in baseline["players"]) == pytest.approx(1)
    with pytest.raises(benchmark.BenchmarkEvidenceError, match="trained after capture"):
        benchmark.build_deuce_baseline(
            "atp",
            _Predictor([row["name"] for row in snapshot["players"]], "2026-08-31T01:00:00Z"),
            snapshot,
        )


def test_timing_eligibility_admits_only_a_later_local_schedule_day(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = tmp_path / "live"
    live.mkdir()
    schedule = live / "upcoming.csv"
    schedule.write_text(
        "tourney_name,espn_id,tourney_date,round,playerA,playerB\n"
        "US Open,189-2026,2026-08-30,SF,Alpha One,Beta Two\n"
        "US Open,189-2026,2026-08-31,SF,Gamma Three,Delta Four\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark, "live_dir", lambda _tour: live)
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", tmp_path / "evidence")
    payload = benchmark.build_timing_eligibility("atp", _snapshot())
    assert len(payload["eligibleMatchIds"]) == 1
    assert payload["eligibleMatchIds"][0].endswith("|delta four|gamma three")
    assert payload["unprovenMatchCount"] == 1
    assert payload["captureLocalDate"] == "2026-08-30"
    receipt = benchmark.schedule_receipt_path("atp")
    assert receipt.read_bytes() == schedule.read_bytes()
    assert payload["schedule"]["receiptRelativePath"].endswith(
        "/189-2026/schedule-receipt.csv"
    )


def test_timing_eligibility_rejects_a_malformed_future_sort_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = tmp_path / "live"
    live.mkdir()
    (live / "upcoming.csv").write_text(
        "tourney_name,espn_id,tourney_date,round,playerA,playerB\n"
        "US Open,189-2026,tomorrow,SF,Alpha One,Beta Two\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark, "live_dir", lambda _tour: live)
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", tmp_path / "evidence")
    payload = benchmark.build_timing_eligibility("atp", _snapshot())
    assert payload["eligibleMatchIds"] == []
    assert payload["unprovenMatchCount"] == 2


def test_forecast_loader_keeps_latest_quote_before_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(track, "FORECAST_DIR", tmp_path)
    rows = [
        _record(as_of="2026-08-30T22:00:00Z", probability=0.55),
        _record(as_of="2026-08-31T00:30:00Z", probability=0.60),
        _record(as_of="2026-08-31T01:30:00Z", probability=0.99),
    ]
    (tmp_path / "atp.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    loaded, malformed = benchmark.load_forecast_records(
        "atp", captured_at="2026-08-31T00:55:47.502Z"
    )
    assert malformed == 0
    assert len(loaded) == 1
    assert loaded[0]["p"] == 0.60


def test_forecast_loader_preserves_post_capture_identity_bridge_for_frozen_quote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(track, "FORECAST_DIR", tmp_path)
    source_id = f"{track.MATCH_ID_VERSION}|espn:189-2026|2026|QF|alpha one|beta two"
    target_id = f"{track.MATCH_ID_VERSION}|espn:189-2026|2026|SF|alpha one|beta two"
    quote = {
        **_record(as_of="2026-08-30T22:00:00Z", probability=0.55),
        "round": "QF",
        "match_id": source_id,
    }
    bridge = {
        "type": "match_identity_bridge",
        "bridge_version": "bracket-round-v1",
        "evidence": "unique_knockout_bracket_round",
        "as_of": "2026-08-31T02:00:00Z",
        "tour": "atp",
        "event": "US Open",
        "espnId": "189-2026",
        "season": 2026,
        "playerA": "Alpha One",
        "playerB": "Beta Two",
        "from_round": "QF",
        "round": "SF",
        "from_match_id": source_id,
        "to_match_id": target_id,
    }
    (tmp_path / "atp.jsonl").write_text(
        "\n".join(json.dumps(row) for row in (quote, bridge)) + "\n",
        encoding="utf-8",
    )

    loaded, malformed = benchmark.load_forecast_records(
        "atp", captured_at="2026-08-31T00:55:47.502Z"
    )
    rows = report.evaluate_matches(
        _snapshot(), loaded, [], eligible_match_ids=report.snapshot_match_ids(_snapshot())
    )

    assert malformed == 0
    assert [row["type"] for row in loaded] == ["match_identity_bridge", "match_snapshot"]
    alpha_beta = next(row for row in rows if row.get("playerA") == "Alpha One")
    assert alpha_beta["status"] == "pending"
    assert alpha_beta["pDeuce"] == 0.55


def test_comparison_ledger_is_idempotent_but_preserves_transitions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", tmp_path)
    snapshot = _comparison_snapshot()
    pending = _pending_comparison(snapshot)
    assert benchmark.append_comparison_ledger("atp", snapshot, [pending]) == 1
    assert benchmark.append_comparison_ledger("atp", snapshot, [pending]) == 0
    graded = {
        **pending,
        "status": "graded",
        "winner": "Alpha One",
        "aWon": True,
        "resultType": "completed",
    }
    assert benchmark.append_comparison_ledger("atp", snapshot, [graded]) == 1
    lines = benchmark.ledger_path("atp").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["comparison"]["status"] for line in lines] == [
        "pending", "graded"
    ]


def test_comparison_ledger_recomputes_every_transition_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", tmp_path)
    snapshot = _comparison_snapshot()
    assert benchmark.append_comparison_ledger(
        "atp", snapshot, [_pending_comparison(snapshot)]
    ) == 1
    path = benchmark.ledger_path("atp")
    transition = json.loads(path.read_text(encoding="utf-8"))
    transition["comparison"]["pDeuce"] = 0.99
    path.write_text(json.dumps(transition) + "\n", encoding="utf-8")

    with pytest.raises(benchmark.BenchmarkEvidenceError, match="immutable contract"):
        benchmark.load_comparison_ledger("atp", snapshot)


def test_terminal_ledger_state_survives_a_temporary_result_gap() -> None:
    snapshot = _comparison_snapshot()
    pending = _pending_comparison(snapshot)
    graded = {
        **pending,
        "status": "graded",
        "winner": "Alpha One",
        "aWon": True,
        "resultType": "completed",
    }
    assert benchmark.merge_terminal_comparisons([pending], [graded]) == [graded]

    contradiction = {
        **graded,
        "winner": "Beta Two",
        "aWon": False,
    }
    with pytest.raises(benchmark.BenchmarkEvidenceError, match="contradicts terminal"):
        benchmark.merge_terminal_comparisons([contradiction], [graded])


def test_generated_frozen_files_are_stable_across_reloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot()
    names = [row["name"] for row in snapshot["players"]]
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", tmp_path)
    before = _Predictor(names, "2026-08-30T23:00:00Z")
    first = benchmark.ensure_deuce_baseline("atp", before, snapshot)
    after = _Predictor(names, "2026-08-31T02:00:00Z")
    second = benchmark.ensure_deuce_baseline("atp", after, snapshot)
    assert second == first
    assert second["predictor"]["artifactId"] == "predictor-before-capture"


def test_existing_baseline_rejects_probability_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot()
    names = [row["name"] for row in snapshot["players"]]
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", tmp_path)
    predictor = _Predictor(names, "2026-08-30T23:00:00Z")
    baseline = benchmark.ensure_deuce_baseline("atp", predictor, snapshot)
    baseline["players"][0]["probabilities"]["W"] = 0.9
    benchmark.baseline_path("atp").write_text(
        json.dumps(baseline), encoding="utf-8"
    )

    with pytest.raises(benchmark.BenchmarkEvidenceError, match="probability is invalid"):
        benchmark.ensure_deuce_baseline("atp", predictor, snapshot)


def test_existing_eligibility_rejects_unsupported_proof_and_receipt_tampering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = tmp_path / "live"
    live.mkdir()
    (live / "upcoming.csv").write_text(
        "tourney_name,espn_id,tourney_date,round,playerA,playerB\n"
        "US Open,189-2026,2026-08-31,SF,Alpha One,Beta Two\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark, "live_dir", lambda _tour: live)
    monkeypatch.setattr(benchmark, "TENNIS_ABSTRACT_DIR", tmp_path / "evidence")
    snapshot = _snapshot()
    eligibility = benchmark.ensure_timing_eligibility("atp", snapshot)
    eligibility["proofs"][0]["scheduledDate"] = "2026-08-30"
    benchmark.eligibility_path("atp").write_text(
        json.dumps(eligibility), encoding="utf-8"
    )
    with pytest.raises(benchmark.BenchmarkEvidenceError, match="proof is not supported"):
        benchmark.ensure_timing_eligibility("atp", snapshot)

    clean = benchmark.build_timing_eligibility("atp", snapshot)
    benchmark.eligibility_path("atp").write_text(json.dumps(clean), encoding="utf-8")
    benchmark.schedule_receipt_path("atp").write_text(
        "corrupt receipt\n", encoding="utf-8"
    )
    with pytest.raises(benchmark.BenchmarkEvidenceError, match="receipt digest mismatch"):
        benchmark.ensure_timing_eligibility("atp", snapshot)


def test_frozen_predictor_timestamp_is_before_capture() -> None:
    # Explicit regression fixture for the real immutable files, not wall-clock behavior.
    for tour in ("atp", "wta"):
        baseline = json.loads(benchmark.baseline_path(tour).read_text(encoding="utf-8"))
        captured = datetime.fromisoformat(
            baseline["sourceCapturedAt"].replace("Z", "+00:00")
        ).astimezone(UTC)
        trained = datetime.fromisoformat(
            baseline["predictor"]["trainedAt"].replace("Z", "+00:00")
        ).astimezone(UTC)
        assert trained < captured


def test_pipeline_benchmark_stage_is_fail_soft(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        pipeline,
        "_tennis_abstract_source_identity",
        lambda _tour, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("provider unavailable")
        ),
    )
    pipeline._tennis_abstract_benchmark(
        "atp", object(), object(), refresh_external=True
    )
    assert "tennis-abstract/atp: skipped (provider unavailable)" in capsys.readouterr().out


def test_external_refresh_exception_does_not_suppress_frozen_grading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _comparison_snapshot()
    monkeypatch.setattr(benchmark, "first_capture_snapshot", lambda _tour: snapshot)
    monkeypatch.setattr(
        benchmark,
        "_refresh_external_receipts",
        lambda _tour: (_ for _ in ()).throw(RuntimeError("corrupt latest pointer")),
    )
    monkeypatch.setattr(
        benchmark,
        "ensure_deuce_baseline",
        lambda *_args: {
            "predictor": {
                "artifactId": "predictor-before-capture",
                "trainedAt": "2026-08-30T23:00:00Z",
            }
        },
    )
    monkeypatch.setattr(
        benchmark,
        "ensure_timing_eligibility",
        lambda *_args: {
            "eligibleMatchIds": [],
            "eventTimezone": "America/New_York",
            "captureLocalDate": "2026-08-30",
            "rule": "saved scheduledDate is strictly after captureLocalDate",
        },
    )
    monkeypatch.setattr(benchmark, "load_forecast_records", lambda *_a, **_k: ([], 0))
    monkeypatch.setattr(benchmark, "_result_records", lambda _results: [])
    monkeypatch.setattr(benchmark, "evaluate_matches", lambda *_a, **_k: [])
    monkeypatch.setattr(benchmark, "load_comparison_ledger", lambda *_args: [])
    monkeypatch.setattr(benchmark, "append_comparison_ledger", lambda *_args: 0)
    monkeypatch.setattr(
        benchmark,
        "build_public_report",
        lambda *_a, **_k: {"matchComparison": {"eligible": 0}, "caveats": []},
    )
    monkeypatch.setattr(benchmark, "output_dir", lambda _tour: tmp_path)
    written = []
    monkeypatch.setattr(
        benchmark,
        "write_produced_artifact",
        lambda _tour, path, raw, **_kwargs: written.append((path, raw)),
    )

    result = benchmark.run_benchmark(
        "atp", object(), [], refresh_external=True
    )

    assert result["refreshStatus"] == "error"
    assert result["refreshError"] == "RuntimeError: corrupt latest pointer"
    assert result["report"]["receipts"]["forecastMalformedLinesSkipped"] == 0
    assert len(written) == 1


def test_pipeline_rebinds_final_sources_used_by_release_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = {
        "firstCapture": {"sha256": "capture"},
        "forecastLog": {"sha256": "forecast"},
        "baseline": {"state": "missing"},
        "eligibility": {"state": "missing"},
        "scheduleReceipt": {"state": "missing"},
        "ledger": {"sha256": "ledger-before"},
        "latestExternal": {"sha256": "external-before"},
    }
    after = {
        "firstCapture": {"sha256": "capture"},
        "forecastLog": {"sha256": "forecast"},
        "baseline": {"sha256": "baseline-after"},
        "eligibility": {"sha256": "eligibility-after"},
        "scheduleReceipt": {"sha256": "schedule-after"},
        "ledger": {"sha256": "ledger-after"},
    }
    calls = []

    def source_identity(_tour: str, *, include_external: bool = False) -> dict:
        calls.append(include_external)
        return copy.deepcopy(before if include_external else after)

    @contextmanager
    def receipt_stage(*_args, **_kwargs):
        yield SimpleNamespace(mark_failure=lambda _error: None)

    monkeypatch.setattr(pipeline, "_tennis_abstract_source_identity", source_identity)
    monkeypatch.setattr(pipeline, "_receipt_stage", receipt_stage)
    monkeypatch.setattr(
        benchmark,
        "run_benchmark",
        lambda *_a, **_k: {
            "report": {"matchComparison": {}},
            "refreshStatus": "written",
            "refreshError": None,
        },
    )
    frame = SimpleNamespace(attrs={})

    pipeline._tennis_abstract_benchmark(
        "atp", object(), frame, refresh_external=True
    )

    expected = {**after, "ledgerBefore": before["ledger"]}
    assert calls == [True, False]
    assert frame.attrs[pipeline._FRAME_RELEASE_STAGE_INPUTS][
        "tennisAbstractBenchmark"
    ] == expected
    release_identity = pipeline._release_source_identity(
        "atp",
        frame,
        "full",
        release_created_at="2026-08-31T02:00:00Z",
        producer_revision="src1:test",
        accepted_parent=None,
    )
    assert release_identity["stageInputs"] == pipeline._json_input_identity(
        {"tennisAbstractBenchmark": expected}
    )
    assert "latestExternal" not in expected


def test_refresh_workflow_persists_benchmark_evidence() -> None:
    workflow = (
        Path(__file__).resolve().parents[2] / ".github" / "workflows" / "refresh.yml"
    ).read_text(encoding="utf-8")
    assert "git add data/forecast_log data/kalshi_ledger data/tennis_abstract" in workflow
