"""Real mixed-format artifacts, immutable evidence and fixed endpoint behavior."""
import copy
import json
import math
from datetime import UTC, datetime, timedelta

import pytest
from tennis_model.eval import prospective as old
from tennis_model.eval import prospective_shadow as ps
from tennis_model.model import artifact as a
from tennis_model.model.dynamic_shadow import DynamicShadowPredictor
from test_dynamic_shadow import PROVENANCE, repack, shadow, unpack  # noqa: F401
from test_predictor_artifact import _valid_predictor

SOURCES = {"scheduleHost": "schedule.example.org", "resultHost": "results.example.org",
           "timingEvidence": "Synthetic fixtures, no live source", "cadence": "Manual synthetic QA"}


@pytest.fixture(scope="module")
def pair(shadow, tmp_path_factory):  # noqa: F811 - imported pytest fixture
    root = tmp_path_factory.mktemp("mixed-models")
    model = _valid_predictor("wta")
    for field in ("elo", "lower_elo", "srv", "lower_srv", "ctx", "lower_ctx", "meta"):
        setattr(model, field, copy.deepcopy(getattr(shadow, field)))
    a.save_predictor_artifact(model, root / "incumbent.pkl", trusted_root=root)
    shadow.save(root / "candidate.shadow", trusted_root=root)
    return root


@pytest.fixture
def clock(monkeypatch):
    current = [datetime.now(UTC) + timedelta(seconds=1)]
    monkeypatch.setattr(ps, "_now", lambda: current[0])
    return current


def registration(root, pair, **kwargs):
    return ps.register(root, trusted_root=root.parent.parent, incumbent=pair / "incumbent.pkl",
                       candidate=pair / "candidate.shadow", provenance=PROVENANCE,
                       hypothesis="Synthetic QA only", sources=SOURCES, evidence_kind="synthetic-qa", **kwargs)


@pytest.fixture
def experiment(pair, clock, tmp_path):
    root = tmp_path / "pilot"
    registration(root, pair)
    return root


def schedule(clock, event="123", players=("A", "B")):
    start = (clock[0] + timedelta(hours=2)).isoformat()
    return {"tour": "wta", "observedAt": clock[0].isoformat(),
            "sourceUrl": "https://schedule.example.org/draw",
            "matches": [{"espnId": event, "season": clock[0].year, "round": "R32",
                         "playerA": players[0], "playerB": players[1], "status": "scheduled",
                         "earliestStartAt": start, "surface": "Hard", "bestOf": 3,
                         "context": {"event": "Synthetic Open", "as_of": start, "indoor": False,
                                     "tier_k": 1., "round_order": 3}}]}


def result(batch, clock, **changes):
    row = copy.deepcopy(batch["matches"][0])
    row.update(status="completed", winner=row["playerA"], actualStartedAt=row["earliestStartAt"],
               finishedAt=clock[0].isoformat())
    row.update(changes)
    return {"tour": "wta", "observedAt": clock[0].isoformat(),
            "sourceUrl": "https://results.example.org/results", "matches": [row]}


def capture(root, batch):
    return ps.capture(root, batch, trusted_root=root.parent)


def grade(root, batch):
    return ps.grade(root, batch, trusted_root=root.parent)


def report(root):
    return ps.report(root, trusted_root=root.parent)


def test_real_roundtrip_accumulates_batches_and_retains_first_forecast(experiment, clock):
    root = experiment
    first, second = schedule(clock), schedule(clock, "456", ("A", "C"))
    assert capture(root, first) == {"captured": 1}
    assert capture(root, second) == {"captured": 1}
    key = ps.match_key(first["matches"][0], "wta")
    path = root / "receipts" / f"{key}.json"
    before = path.read_bytes()
    retry = copy.deepcopy(first)
    retry["matches"][0].update(playerA="B", playerB="A")
    retry["matches"][0]["context"]["event"] = "Changed sponsor"
    assert capture(root, retry) == {"alreadyCaptured": 1}
    assert before == path.read_bytes()
    clock[0] += timedelta(hours=4)
    assert grade(root, result(first, clock))["graded"] == 1
    final = grade(root, result(second, clock, winner="C"))
    assert final["graded"] == 2 and final["pending"] == 0 and final["captured"] == 2
    assert final["evidenceKind"] == "synthetic-qa" and not final["final"]
    assert final["paired"]["logloss"]["blocks"]["event"]["blocks"] == 2
    assert final["paired"]["logloss"]["blocks"]["week"]["status"] == "insufficient-blocks"
    assert final["captureCounts"] == {"captured": 2, "alreadyCaptured": 1}
    retry_result = result(second, clock, winner="C")
    assert grade(root, retry_result)["resultBatches"] == 2
    clock[0] += timedelta(minutes=1)
    assert grade(root, retry_result)["resultBatches"] == 2
    probabilities = ps._read(path, root)["probabilities"]
    expected = -math.log(probabilities["incumbent"])
    scored = next(p for p in final["pairs"] if p["matchKey"] == key)
    assert scored["scores"]["incumbent"]["logloss"] == expected


@pytest.mark.parametrize("field,value,reason", [
    ("status", "live", "notScheduled"), ("bestOf", 5, "missingContext"),
    ("surface", "unknown", "missingContext"), ("context", {}, "missingContext"),
    ("earliestStartAt", "unknown", "missingContext"), ("playerB", "Unknown Entrant", "unpriced"),
])
def test_exclusions_preserve_source_and_counters(experiment, clock, field, value, reason):
    batch = schedule(clock)
    batch["matches"][0][field] = value
    assert capture(experiment, batch) == {reason: 1}
    summary = report(experiment)
    assert summary["observations"] == 1 and summary["captured"] == 0
    assert summary["captureCounts"] == {reason: 1}


@pytest.mark.parametrize("change", ["stale", "future", "wrong-host", "duplicate", "identity", "before-registration"])
def test_invalid_observations_rejected(experiment, clock, change):
    batch = schedule(clock)
    if change == "stale":
        clock[0] += timedelta(minutes=11)
    elif change == "future":
        batch["observedAt"] = (clock[0] + timedelta(seconds=1)).isoformat()
    elif change == "before-registration":
        batch["observedAt"] = (clock[0] - timedelta(seconds=1)).isoformat()
    elif change == "wrong-host":
        batch["sourceUrl"] = "https://unregistered.example.org/results"
    elif change == "duplicate":
        batch["matches"] *= 2
    else:
        batch["matches"][0]["espnId"] = ""
    with pytest.raises(ValueError):
        capture(experiment, batch)
    assert not list((experiment / "receipts").iterdir())


@pytest.mark.parametrize("advance", [timedelta(minutes=11), timedelta(hours=2), timedelta(days=31), timedelta(seconds=-1)])
def test_after_inference_clock_and_freshness_rechecked(experiment, clock, monkeypatch, advance):
    batch = schedule(clock)
    original = DynamicShadowPredictor.prediction_components
    def delayed(self, *args, **kwargs):
        answer = original(self, *args, **kwargs)
        clock[0] += advance
        return answer
    monkeypatch.setattr(DynamicShadowPredictor, "prediction_components", delayed)
    assert capture(experiment, batch) == {"tooLateOrUncertain": 1}
    assert not list((experiment / "receipts").iterdir())


@pytest.mark.parametrize("filename", ["incumbent.pkl", "incumbent.pkl.envelope", "candidate.shadow"])
@pytest.mark.parametrize("operation", ["capture", "grade", "report"])
def test_changed_frozen_bytes_block_every_operation(experiment, clock, filename, operation):
    path = experiment / filename
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(ValueError, match="artifacts changed"):
        if operation == "capture":
            capture(experiment, schedule(clock))
        elif operation == "grade":
            grade(experiment, result(schedule(clock), clock))
        else:
            report(experiment)


@pytest.mark.parametrize("change,reason", [
    ({"status": "retired"}, "retired"), ({"status": "walkover"}, "walkover"),
    ({"actualStartedAt": None}, "missingActualTiming"), ({"winner": "Other Player"}, "winnerMismatch"),
    ({"actualStartedAt": "broken"}, "invalidResultTiming"),
])
def test_settlement_exclusions(experiment, clock, change, reason):
    batch = schedule(clock)
    capture(experiment, batch)
    clock[0] += timedelta(hours=4)
    assert grade(experiment, result(batch, clock, **change))["excluded"] == {reason: 1}


def test_actual_start_must_corroborate_lower_bound(experiment, clock):
    batch = schedule(clock)
    capture(experiment, batch)
    early = clock[0] + timedelta(minutes=1)
    clock[0] += timedelta(hours=4)
    assert grade(experiment, result(batch, clock, actualStartedAt=early.isoformat()))["excluded"] == {"timingNotProved": 1}


@pytest.mark.parametrize("change", [{"winner": "B"}, {"status": "retired"}, {"actualStartedAt": "2026-09-08T00:00:00Z"}])
def test_conflicts_fail_closed_and_all_evidence_remains(experiment, clock, change):
    batch = schedule(clock)
    capture(experiment, batch)
    clock[0] += timedelta(hours=4)
    first = result(batch, clock)
    assert grade(experiment, first)["graded"] == 1
    updated = copy.deepcopy(first)
    updated["matches"][0].update(change)
    summary = grade(experiment, updated)
    assert summary["graded"] == 0 and summary["excluded"] == {"conflictingResults": 1}
    assert summary["resultBatches"] == 2
    assert report(experiment)["excluded"] == summary["excluded"]


def test_later_timing_proof_and_pending_do_not_erase_terminal_facts(experiment, clock):
    batch = schedule(clock)
    capture(experiment, batch)
    clock[0] += timedelta(hours=4)
    assert grade(experiment, result(batch, clock, actualStartedAt=None))["graded"] == 0
    assert grade(experiment, result(batch, clock))["graded"] == 1
    assert grade(experiment, result(batch, clock, status="live", winner=None))["graded"] == 1


def test_fixed_horizon_grace_and_immutable_endpoint(experiment, clock):
    batch = schedule(clock)
    capture(experiment, batch)
    started = clock[0]
    clock[0] += timedelta(days=30)
    with pytest.raises(ValueError, match="capture horizon"):
        capture(experiment, schedule(clock))
    summary = grade(experiment, result(batch, clock))
    assert summary["captureClosed"] and not summary["final"] and summary["graded"] == 1
    clock[0] = started + timedelta(days=37)
    with pytest.raises(ValueError, match="intake closed"):
        grade(experiment, result(batch, clock))
    endpoint = report(experiment)
    assert endpoint["final"] and endpoint["coverage"] == "insufficient-pilot-coverage"
    before = (experiment / "endpoint.json").read_bytes()
    clock[0] += timedelta(days=3)
    assert report(experiment) == endpoint
    assert (experiment / "endpoint.json").read_bytes() == before


def test_match_start_cannot_fall_outside_capture_window(experiment, clock):
    batch = schedule(clock)
    start = (clock[0] + timedelta(days=30)).isoformat()
    batch["matches"][0]["earliestStartAt"] = start
    batch["matches"][0]["context"]["as_of"] = start
    assert capture(experiment, batch) == {"outsideMatchHorizon": 1}


def test_failed_registration_never_publishes_and_cannot_be_reused(pair, clock, tmp_path, monkeypatch):
    root = tmp_path / "broken"
    original = ps._load
    monkeypatch.setattr(ps, "_load", lambda *args: (_ for _ in ()).throw(ValueError("copy validation failed")))
    with pytest.raises(ValueError, match="copy validation failed"):
        registration(root, pair)
    assert root.exists() and not (root / "registration.json").exists()
    monkeypatch.setattr(ps, "_load", original)
    with pytest.raises(FileExistsError):
        registration(root, pair)
    with pytest.raises(a.PredictorArtifactError):
        capture(root, schedule(clock))


@pytest.mark.parametrize("wrong", ["provenance", "missing-provenance", "incumbent-format", "candidate-format", "damaged-state"])
def test_wrong_formats_and_provenance_rejected(pair, clock, tmp_path, wrong):
    inc, cand = pair / "incumbent.pkl", pair / "candidate.shadow"
    provenance = dict(PROVENANCE)
    if wrong == "provenance":
        provenance["selection"] = "f" * 64
    elif wrong == "missing-provenance":
        provenance.pop("selection")
    elif wrong == "incumbent-format":
        inc = cand
    elif wrong == "candidate-format":
        cand = inc
    else:
        header, payload = unpack(cand)
        import hashlib
        import pickle
        model = pickle.loads(payload)
        model.dynamic_main.players["A"].covariance[0, 0] = -1
        payload = pickle.dumps(model)
        header.update(payloadBytes=len(payload), payloadSha256=hashlib.sha256(payload).hexdigest())
        cand = tmp_path / "damaged.shadow"
        repack(cand, header, payload)
    with pytest.raises((a.PredictorArtifactError, ValueError)):
        ps.register(tmp_path / "bad", trusted_root=tmp_path.parent, incumbent=inc, candidate=cand,
                    provenance=provenance, hypothesis="QA", sources=SOURCES)
    assert not (tmp_path / "bad" / "registration.json").exists()


def test_old_runner_keeps_rejecting_shadow(pair, tmp_path):
    with pytest.raises(a.PredictorArtifactError):
        old.register(tmp_path / "old", tour="wta", hypothesis="QA", incumbent=pair / "incumbent.pkl",
                     candidate=pair / "candidate.shadow")


@pytest.mark.parametrize("folder", ["receipts", "observations", "results", "attempts"])
def test_symlinked_evidence_directory_rejected(experiment, clock, tmp_path, folder):
    outside = tmp_path / "external"
    outside.mkdir()
    (experiment / folder).rmdir()
    (experiment / folder).symlink_to(outside, target_is_directory=True)
    with pytest.raises(a.PredictorArtifactError):
        report(experiment)
    assert not list(outside.iterdir())


def test_deleted_or_corrupted_receipts_and_sources_are_detected(experiment, clock):
    batch = schedule(clock)
    capture(experiment, batch)
    path = next((experiment / "receipts").iterdir())
    before = path.read_bytes()
    path.unlink()
    with pytest.raises(ValueError, match="receipt missing"):
        report(experiment)
    path.write_bytes(before)
    source = next((experiment / "observations").iterdir())
    source.write_text('{}')
    with pytest.raises(ValueError, match="integrity"):
        report(experiment)


def test_unfinished_capture_is_visible(experiment, clock, monkeypatch):
    original = ps._write_once
    def interrupted(path, *args):
        if path.parent.name == "attempts":
            raise OSError("interrupted")
        return original(path, *args)
    monkeypatch.setattr(ps, "_write_once", interrupted)
    with pytest.raises(OSError):
        capture(experiment, schedule(clock))
    monkeypatch.setattr(ps, "_write_once", original)
    summary = report(experiment)
    assert summary["captured"] == 1 and summary["unfinishedObservations"] == 1


def test_receipt_size_and_duplicate_json_are_bounded(experiment):
    with pytest.raises(ValueError, match="duplicate"):
        ps._json('{"a":1,"a":2}')
    with pytest.raises(ValueError, match="size bound"):
        ps._write_once(experiment / "big.json", {"schema": ps.SCHEMA, "huge": "x" * ps.MAX_JSON}, experiment)
    assert not (experiment / "big.json").exists()
    assert json.loads((experiment / "registration.json").read_bytes())["policy"] == ps.POLICY


def test_concurrent_capture_retains_one_forecast(experiment, clock):
    from concurrent.futures import ThreadPoolExecutor
    batch = schedule(clock)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outputs = list(pool.map(lambda _: capture(experiment, batch), range(2)))
    assert sorted(next(iter(o)) for o in outputs) == ["alreadyCaptured", "captured"]
    assert report(experiment)["captured"] == 1


def test_result_intake_rechecks_deadline_after_validation(experiment, clock, monkeypatch):
    batch = schedule(clock)
    capture(experiment, batch)
    clock[0] += timedelta(days=37, seconds=-1)
    evidence = result(batch, clock)
    original = ps._batch
    def delayed(*args):
        checked = original(*args)
        clock[0] += timedelta(seconds=2)
        return checked
    monkeypatch.setattr(ps, "_batch", delayed)
    with pytest.raises(ValueError, match="intake closed"):
        grade(experiment, evidence)
    assert not list((experiment / "results").iterdir())


def test_exact_five_minute_boundary_is_ineligible(experiment, clock):
    batch = schedule(clock)
    start = (clock[0] + timedelta(minutes=5)).isoformat()
    batch["matches"][0]["earliestStartAt"] = start
    batch["matches"][0]["context"]["as_of"] = start
    assert capture(experiment, batch) == {"tooLateOrUncertain": 1}


def test_symlinked_receipt_file_is_rejected_before_write(experiment, clock, tmp_path):
    batch = schedule(clock)
    key = ps.match_key(batch["matches"][0], "wta")
    outside = tmp_path / "outside.json"
    outside.write_text('unchanged')
    (experiment / "receipts" / f"{key}.json").symlink_to(outside)
    with pytest.raises(a.PredictorArtifactError):
        capture(experiment, batch)
    assert outside.read_text() == 'unchanged'


def test_create_only_publication_failure_leaves_no_partial_receipt(experiment, monkeypatch):
    def crash(*args, **kwargs):
        raise OSError("publication interrupted")
    monkeypatch.setattr(ps.os, "link", crash)
    with pytest.raises(OSError, match="interrupted"):
        ps._write_once(experiment / "new.json", {"schema": ps.SCHEMA}, experiment)
    assert not (experiment / "new.json").exists()
    assert not list(experiment.glob('.receipt-*'))


@pytest.mark.parametrize("change", ["format", "interval"])
def test_registered_format_and_interval_are_enforced(experiment, change):
    path = experiment / "registration.json"
    value = ps._read(path, experiment)
    value.pop("sha256")
    if change == "format":
        value["models"]["candidate"]["format"] = "production-pickle"
    else:
        value["settleUntil"] = value["captureUntil"]
    path.write_bytes(ps._bytes({**value, "sha256": ps._digest(value)}))
    with pytest.raises(ValueError, match="format|interval"):
        report(experiment)
