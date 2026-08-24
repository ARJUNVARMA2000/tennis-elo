"""Durable pipeline stage receipt and health-lifecycle controls."""

from __future__ import annotations

import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from tennis_model import pipeline, timing
from tennis_model.data import health

BASE = datetime(2026, 8, 20, 12, tzinfo=UTC)


def _record(
    path,
    *,
    tour="atp",
    stage="forecast_products",
    criticality="product",
    outcome="success",
    completed=BASE,
    fingerprint=None,
    error=None,
):
    return timing.record_stage_status(
        tour,
        stage,
        criticality=criticality,
        outcome=outcome,
        attempted_at=completed - timedelta(seconds=2),
        completed_at=completed,
        duration_ms=2_000,
        input_fingerprint=fingerprint or timing.stage_input_fingerprint(tour, stage, 1),
        error=error,
        path=path,
    )


def _snapshot(receipt):
    return {"state": "valid", "receipt": receipt}


def _stage_findings(receipt, now=None, *, data=None, observed_at=None):
    findings = health.output_findings(
        "atp",
        {"data": data or {}, "stage_status": _snapshot(receipt)},
        pd.Timestamp(now or BASE),
        observed_at=pd.Timestamp(observed_at) if observed_at is not None else None,
    )
    return [finding for finding in findings if ".pipeline_stage." in finding.code]


def test_stage_input_fingerprint_is_stable_and_sensitive():
    first = timing.stage_input_fingerprint({"b": 2, "a": 1}, ["x", 3])
    reordered = timing.stage_input_fingerprint({"a": 1, "b": 2}, ["x", 3])
    changed = timing.stage_input_fingerprint({"a": 1, "b": 3}, ["x", 3])
    assert first == reordered
    assert first.startswith("si1:") and len(first) == 68
    assert changed != first
    with pytest.raises(ValueError):
        timing.stage_input_fingerprint(float("nan"))


def test_timed_stage_records_success_without_changing_context_behavior(tmp_path):
    path = tmp_path / timing.STAGE_STATUS_FILENAME
    fingerprint = timing.stage_input_fingerprint("frame-v1")
    marker = []
    with timing.timed(
        "atp",
        "forecast_products",
        criticality="product",
        input_fingerprint=fingerprint,
        status_path=path,
    ):
        marker.append("ran")

    receipt = timing.validate_stage_status(json.loads(path.read_text()), "atp")
    record = receipt["stages"]["forecast_products"]
    assert marker == ["ran"]
    assert record["outcome"] == "success"
    assert record["inputFingerprint"] == fingerprint
    assert record["lastSuccessAt"] == record["completedAt"]
    assert record["error"] is None


def test_repeated_failure_retains_success_and_recovery_clears_error(tmp_path):
    path = tmp_path / timing.STAGE_STATUS_FILENAME
    original_fp = timing.stage_input_fingerprint("frame-v1")
    _record(path, fingerprint=original_fp)

    first_failure = _record(
        path,
        outcome="failure",
        completed=BASE + timedelta(hours=1),
        fingerprint=timing.stage_input_fingerprint("frame-v2"),
        error=RuntimeError("first failure " + "x" * 1_000),
    )
    first = first_failure["stages"]["forecast_products"]
    assert first["lastSuccessInputFingerprint"] == original_fp
    assert len(first["error"]["message"]) == timing.STAGE_ERROR_MESSAGE_MAX_CHARS

    second_failure = _record(
        path,
        outcome="failure",
        completed=BASE + timedelta(hours=2),
        fingerprint=timing.stage_input_fingerprint("frame-v3"),
        error=KeyError("still broken"),
    )
    second = second_failure["stages"]["forecast_products"]
    assert second["lastSuccessAt"] == first["lastSuccessAt"]
    assert second["lastSuccessInputFingerprint"] == original_fp

    recovered = _record(
        path,
        completed=BASE + timedelta(hours=3),
        fingerprint=timing.stage_input_fingerprint("frame-v4"),
    )["stages"]["forecast_products"]
    assert recovered["outcome"] == "success"
    assert recovered["error"] is None
    assert recovered["lastSuccessAt"] == recovered["completedAt"]


def test_unattempted_full_stage_survives_quick_stage_update(tmp_path):
    path = tmp_path / timing.STAGE_STATUS_FILENAME
    _record(path, stage="backtest", criticality="evaluation")
    receipt = _record(
        path,
        stage="forecast_products",
        completed=BASE + timedelta(hours=1),
        fingerprint=timing.stage_input_fingerprint("quick-frame"),
    )
    assert set(receipt["stages"]) == {"backtest", "forecast_products"}
    assert receipt["stages"]["backtest"]["completedAt"].startswith("2026-08-20T12:")


def test_current_failure_fingerprint_and_revision_stay_stable_then_recover(tmp_path):
    path = tmp_path / timing.STAGE_STATUS_FILENAME
    _record(path)
    first_receipt = _record(
        path,
        outcome="failure",
        completed=BASE + timedelta(hours=1),
        error=RuntimeError("provider unavailable"),
    )
    first = _stage_findings(first_receipt, BASE + timedelta(hours=1))[0]
    assert first.code == "output.pipeline_stage.current_failure"
    assert first.severity == "warning"
    assert first.entity == "pipeline-stage:forecast_products"

    repeated_receipt = _record(
        path,
        outcome="failure",
        completed=BASE + timedelta(hours=2),
        fingerprint=timing.stage_input_fingerprint("different-current-input"),
        error=RuntimeError("provider unavailable again at https://example.test/?token=secret"),
    )
    repeated = _stage_findings(repeated_receipt, BASE + timedelta(hours=2))[0]
    assert repeated.fingerprint == first.fingerprint
    assert repeated.revision == first.revision

    changed_type = _record(
        path,
        outcome="failure",
        completed=BASE + timedelta(hours=2, minutes=30),
        error=KeyError("different failure class"),
    )
    changed = _stage_findings(changed_type, BASE + timedelta(hours=2, minutes=30))[0]
    assert changed.fingerprint == first.fingerprint
    assert changed.revision != first.revision

    recovered = _record(path, completed=BASE + timedelta(hours=3))
    assert _stage_findings(recovered, BASE + timedelta(hours=3)) == []


def test_evaluation_failure_is_informational_and_product_success_can_age(tmp_path):
    eval_path = tmp_path / "eval.json"
    evaluation = _record(
        eval_path,
        stage="backtest",
        criticality="evaluation",
        outcome="failure",
        error=RuntimeError("metric failed"),
    )
    finding = _stage_findings(evaluation)[0]
    assert finding.code == "output.pipeline_stage.current_failure"
    assert finding.severity == "info"

    product_path = tmp_path / "product.json"
    product = _record(product_path)
    stale = _stage_findings(
        product,
        BASE + timedelta(hours=timing.PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS + 1),
    )
    assert [(item.code, item.severity) for item in stale] == [
        ("output.pipeline_stage.success_overdue", "warning")
    ]


def test_product_success_sla_uses_precise_boundary_and_overdue_revision_is_stable(tmp_path):
    path = tmp_path / "product.json"
    receipt = _record(path)

    assert _stage_findings(receipt, BASE, observed_at=BASE + timedelta(hours=36)) == []
    just_over = _stage_findings(
        receipt, BASE, observed_at=BASE + timedelta(hours=36, seconds=1)
    )[0]
    much_later = _stage_findings(
        receipt, BASE, observed_at=BASE + timedelta(hours=90)
    )[0]
    assert just_over.code == "output.pipeline_stage.success_overdue"
    assert just_over.revision == much_later.revision
    assert "ageHours" not in just_over.evidence


def test_public_stage_failure_serialization_never_contains_private_exception_detail(tmp_path):
    path = tmp_path / timing.STAGE_STATUS_FILENAME
    secret = (
        "Authorization: Bearer TEST_SECRET https://provider.test/path?token=TEST_TOKEN "
        "/Users/example/private/input.csv"
    )
    receipt = _record(path, outcome="failure", error=RuntimeError(secret))
    private = receipt["stages"]["forecast_products"]["error"]
    assert secret in private["message"]

    finding = _stage_findings(receipt)[0]
    serialized = json.dumps(health._serialize_findings([finding]), sort_keys=True)
    for forbidden in ("TEST_SECRET", "TEST_TOKEN", "provider.test", "/Users/example", "Bearer"):
        assert forbidden not in serialized
    assert finding.evidence == {"criticality": "product", "errorType": "RuntimeError"}
    assert finding.message.endswith("failed (RuntimeError)")


def test_malformed_receipt_is_actionable_but_missing_rollout_state_is_silent():
    malformed = health.output_findings(
        "atp",
        {"data": {}, "stage_status": {"state": "malformed", "error": "wrong schema"}},
        pd.Timestamp(BASE),
    )
    finding = next(item for item in malformed if ".pipeline_stage." in item.code)
    assert finding.code == "output.pipeline_stage.receipt_malformed"
    assert finding.severity == "warning"
    missing = health.output_findings(
        "atp", {"data": {}, "stage_status": {"state": "missing"}}, pd.Timestamp(BASE)
    )
    assert not [item for item in missing if ".pipeline_stage." in item.code]

    expected_missing = health.output_findings(
        "atp",
        {
            "data": {"meta": {"stageStatusSchema": timing.STAGE_STATUS_SCHEMA}},
            "stage_status": {"state": "missing"},
        },
        pd.Timestamp(BASE),
    )
    assert [(item.code, item.severity) for item in expected_missing
            if ".pipeline_stage." in item.code] == [
        ("output.pipeline_stage.receipt_missing", "warning")
    ]


def test_expected_receipt_requires_each_product_stage_but_not_mode_specific_evaluation(tmp_path):
    path = tmp_path / timing.STAGE_STATUS_FILENAME
    receipt = _record(path, stage="forecast_products")
    findings = _stage_findings(
        receipt,
        data={"meta": {"stageStatusSchema": timing.STAGE_STATUS_SCHEMA}},
    )
    incomplete = next(item for item in findings
                      if item.code == "output.pipeline_stage.receipt_incomplete")
    assert incomplete.evidence == {"missingStages": ["tracking", "upcoming_prepare"]}

    for stage in ("tracking", "upcoming_prepare"):
        receipt = _record(path, stage=stage, completed=BASE + timedelta(minutes=1))
    assert not [item for item in _stage_findings(
        receipt,
        data={"meta": {"stageStatusSchema": timing.STAGE_STATUS_SCHEMA}},
    ) if item.code == "output.pipeline_stage.receipt_incomplete"]


def test_read_outputs_distinguishes_malformed_receipt(monkeypatch, tmp_path):
    tour_dir = tmp_path / "atp"
    tour_dir.mkdir()
    (tour_dir / timing.STAGE_STATUS_FILENAME).write_text('{"schema":"wrong"}')
    monkeypatch.setattr(health, "output_dir", lambda tour: tmp_path / tour)

    snapshot = health.read_outputs("atp")["stage_status"]
    assert snapshot["state"] == "malformed"
    assert "contract" in snapshot["error"]


def test_writer_preserves_malformed_receipt_for_health_instead_of_laundering_it(tmp_path):
    path = tmp_path / timing.STAGE_STATUS_FILENAME
    original = '{"schema":"wrong","secret":"retain evidence"}'
    path.write_text(original)

    with pytest.raises(ValueError, match="refusing to overwrite"):
        _record(path)
    assert path.read_text() == original


def test_legacy_json_receipt_is_migrated_privately_without_losing_history(
        monkeypatch, tmp_path):
    tour_dir = tmp_path / "output" / "atp"
    legacy = tour_dir / timing.LEGACY_STAGE_STATUS_FILENAME
    _record(
        legacy,
        outcome="failure",
        error=RuntimeError("private provider detail"),
    )
    monkeypatch.setattr(timing, "output_dir", lambda tour: tmp_path / "output" / tour)

    with timing.timed(
        "atp",
        "tracking",
        criticality="product",
        input_fingerprint=timing.stage_input_fingerprint("current"),
    ):
        pass

    private = tour_dir / timing.STAGE_STATUS_FILENAME
    assert private.exists()
    assert not legacy.exists()
    receipt = timing.validate_stage_status(
        json.loads(private.read_text(encoding="utf-8")), "atp")
    assert receipt["stages"]["forecast_products"]["outcome"] == "failure"
    assert receipt["stages"]["tracking"]["outcome"] == "success"


def test_future_dated_receipt_cannot_suppress_real_attempts_or_look_healthy(
        monkeypatch, tmp_path):
    tour_dir = tmp_path / "atp"
    tour_dir.mkdir()
    path = tour_dir / timing.STAGE_STATUS_FILENAME
    future = datetime.now(UTC) + timedelta(days=1)
    stamp = future.isoformat(timespec="microseconds").replace("+00:00", "Z")
    fingerprint = timing.stage_input_fingerprint("future")
    path.write_text(json.dumps({
        "schema": timing.STAGE_STATUS_SCHEMA,
        "tour": "atp",
        "updatedAt": stamp,
        "stages": {
            "forecast_products": {
                "criticality": "product",
                "outcome": "success",
                "attemptedAt": stamp,
                "completedAt": stamp,
                "durationMs": 0,
                "inputFingerprint": fingerprint,
                "lastSuccessAt": stamp,
                "lastSuccessInputFingerprint": fingerprint,
                "error": None,
            },
        },
    }))
    original = path.read_text()
    monkeypatch.setattr(health, "output_dir", lambda tour: tmp_path / tour)

    with pytest.raises(ValueError, match="future-dated"):
        timing.validate_stage_status(json.loads(path.read_text()), "atp")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        _record(path, completed=datetime.now(UTC))
    snapshot = health.read_outputs("atp")["stage_status"]
    assert snapshot["state"] == "malformed"
    assert snapshot["errorType"] == "ValueError"

    # The observational context still must not make a successful product stage fatal.
    with timing.timed(
        "atp",
        "forecast_products",
        criticality="product",
        input_fingerprint=timing.stage_input_fingerprint("current"),
        status_path=path,
    ):
        pass
    assert path.read_text() == original


def test_stage_receipt_and_error_evidence_never_enter_public_mirror(monkeypatch, tmp_path):
    output_root, public_root = tmp_path / "output", tmp_path / "public"
    source = output_root / "atp"
    source.mkdir(parents=True)
    (source / "meta.json").write_text('{"ok":true}')
    (source / "health-source.json").write_text('{"private":true}')
    (source / timing.STAGE_STATUS_FILENAME).write_text(
        '{"error":"RECEIPT_SECRET"}')
    monkeypatch.setattr(pipeline, "output_dir", lambda tour: output_root / tour)
    monkeypatch.setattr(pipeline, "WEB_DATA_DIR", public_root)

    pipeline._mirror("atp")
    assert (public_root / "atp" / "meta.json").exists()
    assert not (public_root / "atp" / "health-source.json").exists()
    assert not (public_root / "atp" / timing.STAGE_STATUS_FILENAME).exists()

    # The extension is the rollback boundary: a pre-Round-3 mirror copied every JSON and
    # knew nothing about the receipt name, but still cannot select the private receipt.
    assert not timing.STAGE_STATUS_FILENAME.endswith(".json")
    legacy_public = public_root / "legacy" / "atp"
    legacy_public.mkdir(parents=True)
    for artifact in source.glob("*.json"):
        shutil.copy(artifact, legacy_public / artifact.name)
    assert not (legacy_public / timing.STAGE_STATUS_FILENAME).exists()
    assert "RECEIPT_SECRET" not in "\n".join(
        artifact.read_text(encoding="utf-8") for artifact in legacy_public.glob("*.json")
    )


def test_atomic_concurrent_tour_writes_remain_valid_and_isolated(tmp_path):
    paths = {
        tour: tmp_path / tour / timing.STAGE_STATUS_FILENAME
        for tour in ("atp", "wta")
    }

    def write(item):
        tour, index = item
        return _record(
            paths[tour],
            tour=tour,
            stage=f"stage_{index}",
            criticality="evaluation" if index % 2 else "product",
            completed=BASE + timedelta(seconds=index),
            fingerprint=timing.stage_input_fingerprint(tour, index),
        )

    work = [(tour, index) for tour in ("atp", "wta") for index in range(20)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, work))

    for tour in ("atp", "wta"):
        receipt = timing.validate_stage_status(json.loads(paths[tour].read_text()), tour)
        assert len(receipt["stages"]) == 20
        assert not list(paths[tour].parent.glob("*.tmp"))
    assert paths["atp"].read_text() != paths["wta"].read_text()


def test_pipeline_soft_fail_registry_covers_product_and_evaluation_stages():
    assert pipeline.PIPELINE_STAGE_CRITICALITY == {
        "health_manifest": "evaluation",
        "upcoming_prepare": "product",
        "tracking": "product",
        "forecast_products": "product",
        "backtest": "evaluation",
        "market_scorecard": "evaluation",
        "kalshi_benchmark": "evaluation",
        "kalshi_report": "evaluation",
    }
    assert {stage for stage, criticality in pipeline.PIPELINE_STAGE_CRITICALITY.items()
            if criticality == "product"} == set(timing.PRODUCT_STAGE_NAMES)


def test_same_shape_frame_and_derived_inputs_have_content_sensitive_fingerprints(tmp_path,
                                                                                 monkeypatch):
    first = pd.DataFrame({"p": [0.4, 0.6], "year": [2025, 2026]})
    second = pd.DataFrame({"p": [0.5, 0.5], "year": [2025, 2026]})
    assert first.shape == second.shape
    assert pipeline._frame_input_identity(first)["contentSha256"] != (
        pipeline._frame_input_identity(second)["contentSha256"]
    )

    enriched_a = [{"playerA": "A", "playerB": "B", "pA": 0.6}]
    enriched_b = [{"playerA": "A", "playerB": "B", "pA": 0.7}]
    assert pipeline._enriched_input_identity(enriched_a)["sha256"] != (
        pipeline._enriched_input_identity(enriched_b)["sha256"]
    )

    monkeypatch.setattr(pipeline, "DATA_DIR", tmp_path)
    ledger_dir = tmp_path / "kalshi_ledger"
    ledger_dir.mkdir()
    (ledger_dir / "atp.csv").write_text("row\n1\n")
    (ledger_dir / "wta.csv").write_text("row\n2\n")
    before = timing.stage_input_fingerprint(pipeline._kalshi_report_input_identity(["atp"]))
    (ledger_dir / "wta.csv").write_text("row\n3\n")
    after = timing.stage_input_fingerprint(pipeline._kalshi_report_input_identity(["atp"]))
    assert before != after, "ATP's cross-tour report identity ignored the changed WTA ledger"


def test_pipeline_soft_fail_boundaries_record_without_becoming_fatal(monkeypatch, tmp_path):
    import tennis_model.eval.compare as compare
    import tennis_model.eval.track as track

    monkeypatch.setattr(timing, "output_dir", lambda tour: tmp_path / tour)
    monkeypatch.setattr(
        track,
        "log_and_grade",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("tracking unavailable")),
    )
    monkeypatch.setattr(
        compare,
        "scorecard_from_oos",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("odds unavailable")),
    )

    # Both helpers keep their original best-effort API: neither exception escapes.
    pipeline._track("atp", object(), object())
    pipeline._market_scorecard("atp", object())

    receipt = timing.validate_stage_status(
        json.loads((tmp_path / "atp" / timing.STAGE_STATUS_FILENAME).read_text()), "atp"
    )
    assert receipt["stages"]["tracking"]["outcome"] == "failure"
    assert receipt["stages"]["tracking"]["criticality"] == "product"
    assert receipt["stages"]["market_scorecard"]["outcome"] == "failure"
    assert receipt["stages"]["market_scorecard"]["criticality"] == "evaluation"


def test_nonthrowing_producer_degradation_records_failure_without_losing_fallback(
        monkeypatch, tmp_path):
    import tennis_model.eval.track as track
    import tennis_model.model.upcoming as upcoming

    monkeypatch.setattr(timing, "output_dir", lambda tour: tmp_path / tour)
    monkeypatch.setattr(pipeline, "live_dir", lambda tour: tmp_path / "live" / tour)

    enriched = [{"playerA": "A", "playerB": "B", "pA": 0.6}]

    def degraded_upcoming(_tour, *, status):
        status["failures"] = [{"source": "espn-upcoming", "errorType": "UnicodeError"}]
        return pd.DataFrame()

    monkeypatch.setattr(upcoming, "load_upcoming", degraded_upcoming)
    monkeypatch.setattr(upcoming, "enrich_upcoming", lambda *_args: enriched)
    assert pipeline._prepare_upcoming("atp", object(), pd.DataFrame()) == enriched

    def degraded_tracking(*_args, status, **_kwargs):
        status["malformedLines"] = 2
        return {}

    monkeypatch.setattr(track, "log_and_grade", degraded_tracking)
    pipeline._track("atp", object(), pd.DataFrame(), enriched)

    receipt = timing.validate_stage_status(
        json.loads((tmp_path / "atp" / timing.STAGE_STATUS_FILENAME).read_text()), "atp"
    )
    assert receipt["stages"]["upcoming_prepare"]["outcome"] == "failure"
    assert receipt["stages"]["upcoming_prepare"]["error"]["type"] == (
        "UpcomingInputDegraded"
    )
    assert receipt["stages"]["tracking"]["outcome"] == "failure"
    assert receipt["stages"]["tracking"]["error"]["type"] == "ForecastLogDegraded"


def test_malformed_draw_cache_preserves_espn_fallback_and_stage_recovers(
        monkeypatch, tmp_path):
    from tennis_model.model import upcoming

    from tennis_model.data import draws, draws_wiki
    from tennis_model.data import live as live_data

    live = tmp_path / "live" / "atp"
    live.mkdir(parents=True)
    (live / "upcoming.csv").write_text(
        "tourney_name,espn_id,tourney_date,round,playerA,playerB\n"
        "Fallback Open,7-2026,2026-08-24,R32,A Player,B Player\n",
        encoding="utf-8",
    )
    cache = live / draws.CACHE_FILE
    cache.write_text("{ not json", encoding="utf-8")
    monkeypatch.setattr(timing, "output_dir", lambda tour: tmp_path / "receipts" / tour)
    monkeypatch.setattr(pipeline, "live_dir", lambda _tour: live)
    monkeypatch.setattr(upcoming, "live_dir", lambda _tour: live)
    monkeypatch.setattr(draws, "live_dir", lambda _tour: live)
    meta = {"Fallback Open": {
        "espnId": "7-2026", "start": "2099-08-24", "end": "2099-08-31"}}
    provider = {"entry": None}
    monkeypatch.setattr(live_data, "parse_event_meta", lambda _events: meta)
    monkeypatch.setattr(draws, "update_registry", lambda *_args: {"events": {}})
    monkeypatch.setattr(draws, "load_registry", lambda *_args: {"events": {}})
    monkeypatch.setattr(draws_wiki, "_download_wiki_meta", lambda *_args: None)
    monkeypatch.setattr(
        draws,
        "_resolve_one",
        lambda *_args: (
            provider["entry"], [] if provider["entry"] else ["providers failed"]),
    )
    monkeypatch.setattr(
        upcoming,
        "enrich_upcoming",
        lambda _predictor, _df, frame, _tour: frame.to_dict("records"),
    )

    # Production ordering rewrites the malformed cache before upcoming preparation. The
    # generation-bound private status must carry that read failure across the valid `{}`.
    draws.download_tournament_draws(["atp"], events_by_tour={"atp": []})
    assert cache.read_text(encoding="utf-8") == "{}"
    assert draws.draw_cache_refresh_failures("atp", directory=live) == [{
        "source": "complete-draw-cache", "errorType": "JSONDecodeError"}]

    enriched = pipeline._prepare_upcoming("atp", object(), pd.DataFrame())
    assert enriched and enriched[0]["tourney_name"] == "Fallback Open"
    receipt_path = tmp_path / "receipts" / "atp" / timing.STAGE_STATUS_FILENAME
    receipt = timing.validate_stage_status(
        json.loads(receipt_path.read_text(encoding="utf-8")), "atp")
    failed = receipt["stages"]["upcoming_prepare"]
    assert failed["outcome"] == "failure"
    assert failed["error"]["type"] == "UpcomingInputDegraded"
    assert "complete-draw-cache: JSONDecodeError" in failed["error"]["message"]

    provider["entry"] = {
        "name": "Fallback Open",
        "espnId": "7-2026",
        "source": "wikipedia",
        "sourceId": "2099 Fallback Open – Singles",
        "sourceUrl": "https://en.wikipedia.org/wiki/2099_Fallback_Open",
        "slots": [f"Player {index}" for index in range(8)],
        "seeds": {},
        "bestOf": 3,
        "drawSize": 8,
        "bracketSize": 8,
        "start": "2099-08-24",
        "end": "2099-08-31",
    }
    draws.download_tournament_draws(["atp"], events_by_tour={"atp": []})
    assert draws.draw_cache_refresh_failures("atp", directory=live) == []
    recovered = pipeline._prepare_upcoming("atp", object(), pd.DataFrame())
    assert recovered and recovered[0]["tourney_name"] == "Fallback Open"
    receipt = timing.validate_stage_status(
        json.loads(receipt_path.read_text(encoding="utf-8")), "atp")
    record = receipt["stages"]["upcoming_prepare"]
    assert record["outcome"] == "success"
    assert record["error"] is None
    assert record["lastSuccessAt"] == record["completedAt"]


def test_file_identity_cache_reuses_unchanged_digest_and_invalidates_same_size_edit(
        monkeypatch, tmp_path):
    path = tmp_path / "large-input.jsonl"
    path.write_text("alpha", encoding="utf-8")
    real_open = open
    reads = []

    def counting_open(candidate, *args, **kwargs):
        if candidate == path:
            reads.append(candidate)
        return real_open(candidate, *args, **kwargs)

    monkeypatch.setattr(pipeline, "open", counting_open, raising=False)
    first = pipeline._file_input_identity(path)
    repeated = pipeline._file_input_identity(path)
    assert repeated == first
    assert len(reads) == 1

    # Same byte length exercises stat-aware invalidation rather than a size-only shortcut.
    path.write_text("omega", encoding="utf-8")
    changed = pipeline._file_input_identity(path)
    assert changed["sha256"] != first["sha256"]
    assert len(reads) == 2


def test_every_stage_source_identity_is_sensitive_to_its_mutable_inputs(
        monkeypatch, tmp_path):
    from tennis_model.data import draws

    data_root = tmp_path / "data"
    output_root = data_root / "output"
    live_root = data_root / "live"
    odds_root = data_root / "odds"
    kalshi_root = data_root / "kalshi"
    ledger_root = data_root / "kalshi-ledger"
    tour_output = output_root / "atp"
    forecast_log = data_root / "forecast_log" / "atp.jsonl"
    profile_shard = tour_output / "profile" / "a.json"
    for directory in (
        tour_output, forecast_log.parent, profile_shard.parent, odds_root,
        kalshi_root, ledger_root, live_root,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    paths = {
        "forecast": forecast_log,
        "brackets": tour_output / "brackets.json",
        "tournaments": tour_output / "tournaments.json",
        "accuracy": tour_output / "accuracy.json",
        "performance": tour_output / "performance.json",
        "profile_index": tour_output / "profile-index.json",
        "profile_shard": profile_shard,
        "odds": odds_root / "2026.csv",
        "snapshots": kalshi_root / "snapshots.json",
        "ledger": ledger_root / "atp.csv",
        "rankings": live_root / "rankings.json",
        "draw_status": live_root / draws.CACHE_STATUS_FILE,
    }
    paths["forecast"].write_text('{"v":1}\n', encoding="utf-8")
    for name in ("brackets", "tournaments", "accuracy", "performance"):
        paths[name].write_text('{"v":1}', encoding="utf-8")
    paths["profile_index"].write_text(
        '{"generation":1,"profiles":[{"file":"profile/a.json"}]}', encoding="utf-8"
    )
    paths["profile_shard"].write_text('{"v":1}', encoding="utf-8")
    paths["odds"].write_text("v\n1\n", encoding="utf-8")
    paths["snapshots"].write_text('{"v":1}', encoding="utf-8")
    paths["ledger"].write_text("v\n1\n", encoding="utf-8")
    paths["rankings"].write_text('{"v":1}', encoding="utf-8")
    paths["draw_status"].write_text(
        json.dumps({"schema": draws.CACHE_STATUS_SCHEMA, "failures": []}),
        encoding="utf-8",
    )

    monkeypatch.setattr(pipeline, "DATA_DIR", data_root)
    monkeypatch.setattr(pipeline, "KALSHI_LEDGER_DIR", ledger_root)
    monkeypatch.setattr(pipeline, "output_dir", lambda _tour: tour_output)
    monkeypatch.setattr(pipeline, "live_dir", lambda _tour: live_root)
    monkeypatch.setattr(pipeline, "odds_dir", lambda _tour: odds_root)
    monkeypatch.setattr(pipeline, "kalshi_dir", lambda _tour: kalshi_root)

    def fingerprint(identity):
        return timing.stage_input_fingerprint(identity())

    def assert_mutation(identity, path, replacement):
        before = fingerprint(identity)
        path.write_text(replacement, encoding="utf-8")
        assert fingerprint(identity) != before, f"identity ignored mutation of {path.name}"

    tracking = lambda: pipeline._tracking_source_identity("atp")
    for name, replacement in (
        ("forecast", '{"v":2}\n'),
        ("brackets", '{"v":2}'),
        ("tournaments", '{"v":2}'),
        ("accuracy", '{"v":2}'),
    ):
        assert_mutation(tracking, paths[name], replacement)

    products = lambda: pipeline._forecast_products_source_identity("atp")
    for name, replacement in (
        ("forecast", '{"v":3}\n'),
        ("brackets", '{"v":3}'),
        ("performance", '{"v":2}'),
        ("profile_index", '{"generation":2,"profiles":[{"file":"profile/a.json"}]}'),
        ("profile_shard", '{"v":2}'),
    ):
        assert_mutation(products, paths[name], replacement)

    market = lambda: pipeline._market_scorecard_source_identity("atp")
    assert_mutation(market, paths["odds"], "v\n2\n")

    upcoming_sources = lambda: pipeline._upcoming_source_identity("atp")
    assert_mutation(
        upcoming_sources,
        paths["draw_status"],
        json.dumps({
            "schema": draws.CACHE_STATUS_SCHEMA,
            "failures": [{
                "source": "complete-draw-cache",
                "errorType": "JSONDecodeError",
            }],
        }),
    )

    kalshi = lambda: pipeline._kalshi_benchmark_source_identity("atp")
    for name, replacement in (
        ("snapshots", '{"v":2}'),
        ("ledger", "v\n2\n"),
        ("forecast", '{"v":4}\n'),
        ("rankings", '{"v":2}'),
    ):
        assert_mutation(kalshi, paths[name], replacement)

    source_health = {"value": "health-a"}
    monkeypatch.setattr(
        health, "_health_input_fingerprint", lambda _tour: source_health["value"]
    )
    before = fingerprint(lambda: pipeline._health_manifest_source_identity("atp"))
    source_health["value"] = "health-b"
    assert fingerprint(lambda: pipeline._health_manifest_source_identity("atp")) != before

    xgb = {"max_depth": 3}
    monkeypatch.setattr(pipeline, "xgb_params_for", lambda _tour: dict(xgb))
    backtest = lambda: pipeline._backtest_contract_identity(
        "atp", threshold=None, dual_input=None, end_year=2026
    )
    before = fingerprint(backtest)
    xgb["max_depth"] = 4
    assert fingerprint(backtest) != before


def test_profile_fingerprint_never_follows_index_paths_outside_private_output(
        monkeypatch, tmp_path):
    output = tmp_path / "output" / "atp"
    output.mkdir(parents=True)
    secret = tmp_path / "secret.txt"
    secret.write_text("must not be fingerprinted", encoding="utf-8")
    (output / "profile-index.json").write_text(
        '{"profiles":[{"file":"../../secret.txt"}]}', encoding="utf-8"
    )
    monkeypatch.setattr(pipeline, "output_dir", lambda _tour: output)

    identity = pipeline._profile_sources_input_identity("atp")
    assert identity["shards"] == {"../../secret.txt": {"state": "outside-output"}}
    assert secret.read_text(encoding="utf-8") not in json.dumps(identity)


def test_partial_kalshi_and_zero_match_market_are_stable_evaluation_degradations(
        monkeypatch, tmp_path):
    from contextlib import contextmanager

    import tennis_model.data.kalshi as kalshi_data
    import tennis_model.eval.compare as compare
    import tennis_model.eval.kalshi_ledger as kalshi_ledger

    receipt_root = tmp_path / "receipts"
    output_root = tmp_path / "output"
    for tour in ("atp", "wta"):
        (output_root / tour).mkdir(parents=True)
    monkeypatch.setattr(timing, "output_dir", lambda tour: receipt_root / tour)
    monkeypatch.setattr(pipeline, "output_dir", lambda tour: output_root / tour)
    monkeypatch.setattr(pipeline, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(pipeline, "KALSHI_LEDGER_DIR", tmp_path / "ledgers")
    monkeypatch.setattr(pipeline, "kalshi_dir", lambda tour: tmp_path / "kalshi" / tour)
    monkeypatch.setattr(pipeline, "live_dir", lambda tour: tmp_path / "live" / tour)
    monkeypatch.setattr(pipeline, "odds_dir", lambda tour: tmp_path / "odds" / tour)

    monkeypatch.setattr(compare, "scorecard_from_oos", lambda *_args: {"matched": 0})
    frame = pd.DataFrame({"p_combiner": [0.6], "year": [2026]})
    pipeline._market_scorecard("atp", frame)

    @contextmanager
    def time_budget(_seconds):
        yield

    def partial_sweep(_tour, **kwargs):
        kwargs["status"].update({
            "sweepsAttempted": 2,
            "sweepsSucceeded": 1,
            "failedSweeps": [{"sweep": "series", "errorType": "TimeoutError"}],
        })

    monkeypatch.setattr(kalshi_data, "time_budget", time_budget)
    monkeypatch.setattr(kalshi_data, "budget_spent", lambda: False)
    monkeypatch.setattr(kalshi_data, "refresh_snapshots", partial_sweep)
    monkeypatch.setattr(kalshi_ledger, "refresh_ledger", lambda *_args, **_kwargs: {})

    pipeline._kalshi("atp", frame, None)
    pipeline._quick_kalshi(["wta"], {"wta": frame})

    expected = {
        "atp": {
            "market_scorecard": "MarketScorecardNoMatchesDegraded",
            "kalshi_benchmark": "KalshiPartialSweepDegraded",
        },
        "wta": {"kalshi_benchmark": "KalshiPartialSweepDegraded"},
    }
    for tour, stages in expected.items():
        receipt = timing.validate_stage_status(
            json.loads(
                (receipt_root / tour / timing.STAGE_STATUS_FILENAME).read_text(encoding="utf-8")
            ),
            tour,
        )
        for stage, category in stages.items():
            record = receipt["stages"][stage]
            assert record["outcome"] == "failure"
            assert record["criticality"] == "evaluation"
            assert record["error"]["type"] == category

        findings = health.output_findings(
            tour, {"data": {}, "stage_status": _snapshot(receipt)}, pd.Timestamp.now(tz="UTC")
        )
        stage_findings = [item for item in findings if ".pipeline_stage." in item.code]
        assert stage_findings
        assert {item.severity for item in stage_findings} == {"info"}
