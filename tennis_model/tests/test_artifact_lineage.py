"""Focused contract and crash-boundary tests for whole-release artifact lineage."""

from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tennis_model import artifact_lineage as lineage

PREDICTOR_IDS = {
    "atp": "11111111-1111-4111-8111-111111111111",
    "wta": "22222222-2222-4222-8222-222222222222",
}
_REAL_VALIDATE_PREDICTOR_IDENTITY = lineage._validate_predictor_identity


@pytest.fixture(autouse=True)
def _bounded_fake_predictor_identity(monkeypatch):
    """Most core tests isolate lineage from the heavyweight model contract fixture."""

    def validate(root: Path, tour: str) -> dict:
        payload = (Path(root) / tour / "predictor.pkl").read_bytes()
        return {
            "artifactId": PREDICTOR_IDS[tour],
            "tour": tour,
            "trainedAt": "2026-08-24T00:00:00Z",
            "payloadBytes": len(payload),
            "payloadSha256": hashlib.sha256(payload).hexdigest(),
        }

    monkeypatch.setattr(lineage, "_validate_predictor_identity", validate)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _write_tour_graph(root: Path, tour: str, *, evaluation: bool = True) -> None:
    directory = root / tour
    for name in lineage.FIXED_PUBLIC_CORE:
        _write_json(directory / name, {"tour": tour, "file": name})
    _write_json(
        directory / "meta.json",
        {
            "tour": tour,
            "predictorArtifactId": PREDICTOR_IDS[tour],
            "modelTrainedAt": "2026-08-24T00:00:00Z",
        },
    )

    matrix = "matrix-hard-bo3.json"
    profile = "profile-0123456789abcdef.json"
    scenario = "scenario-718-2026.json"
    upcoming_event = "upcoming-event-718-2026.json"
    upcoming_evidence = "upcoming-evidence-718-2026.json"
    _write_json(
        directory / "matrix-index.json",
        {"surfaces": {"Hard": {"3": matrix}}},
    )
    _write_json(
        directory / "profile-index.json",
        {"profiles": [{"name": "Player", "file": profile}]},
    )
    _write_json(
        directory / "scenario-index.json",
        {"events": [{"espnId": "718-2026", "file": scenario}]},
    )
    _write_json(
        directory / "upcoming-index.json",
        {
            "events": [{
                "espnId": "718-2026",
                "file": upcoming_event,
                "evidenceFile": upcoming_evidence,
            }]
        },
    )
    for name in (matrix, profile, scenario, upcoming_event, upcoming_evidence):
        _write_json(directory / name, {"tour": tour, "shard": name})
    if evaluation:
        for name in lineage.OPTIONAL_EVALUATION_FILES:
            _write_json(directory / name, {"tour": tour, "evaluation": name})

    # Both legacy JSON-private and new non-JSON-private state coexist during rollout.
    _write_json(directory / "health-source.json", {"private": True})
    (directory / "stage-status.private").write_text("private", encoding="utf-8")
    (directory / "predictor.pkl").write_bytes(b"private pickle")
    (directory / "predictor.pkl.envelope").write_text("private", encoding="utf-8")


def _write_graph(root: Path, *, evaluation: bool = True) -> None:
    for tour in lineage.TOURS:
        _write_tour_graph(root, tour, evaluation=evaluation)


def _provenance(
    tour: str, label: str = "pipeline.full"
) -> lineage.ArtifactProvenance:
    return lineage.ArtifactProvenance(
        producer=label,
        source_fingerprint=lineage.source_fingerprint({"producer": label}),
        predictor_artifact_id=PREDICTOR_IDS[tour],
    )


def _draft(
    root: Path,
    tour: str,
    context: lineage.ReleaseContext,
    *,
    carried: lineage.CarriedRelease | None = None,
    produced_paths=None,
    producer: str = "pipeline.full",
) -> lineage.TourDraft:
    if produced_paths is None:
        produced_paths = lineage.discover_tour_artifacts(root, tour)
    return lineage.draft_tour_release(
        root,
        tour,
        context,
        _provenance(tour, producer),
        carried=carried,
        produced_paths=produced_paths,
    )


def _seal(
    root: Path,
    *,
    accepted_prior: lineage.AcceptedRelease | None = None,
    carried: lineage.CarriedRelease | None = None,
    mode: str = "full",
) -> lineage.ValidatedRelease:
    context = lineage.begin_release(mode, accepted_prior=accepted_prior)
    drafts = [
        _draft(root, tour, context, carried=carried)
        for tour in lineage.TOURS
    ]
    return lineage.seal_release(root, lineage.merge_release_drafts(context, drafts))


def _accepted(root: Path) -> lineage.AcceptedRelease:
    _write_graph(root)
    _seal(root)
    return lineage.accept_release(
        root,
        semantic_gate_passed=True,
        validator="predeploy-integrity-gate-v1",
    )


def _accepted_with_strict_predictors(
    root: Path,
    monkeypatch,
) -> lineage.AcceptedRelease:
    _write_graph(root)
    for tour in lineage.TOURS:
        _write_strict_predictor_pair(root, tour)
    monkeypatch.setattr(
        lineage,
        "_validate_predictor_identity",
        _REAL_VALIDATE_PREDICTOR_IDENTITY,
    )
    _seal(root)
    return lineage.accept_release(
        root,
        semantic_gate_passed=True,
        validator="predeploy-integrity-gate-v1",
    )


def _write_strict_predictor_pair(root: Path, tour: str) -> bytes:
    from tennis_model.model import artifact

    payload = f"strict-private-payload:{tour}".encode()
    envelope = {
        "schema": artifact.PREDICTOR_ENVELOPE_SCHEMA,
        "artifactId": PREDICTOR_IDS[tour],
        "tour": tour,
        "trainedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payloadBytes": len(payload),
        "payloadSha256": hashlib.sha256(payload).hexdigest(),
        "python": artifact._python_identity(),
        "libraries": artifact._library_versions(),
        "contract": artifact.predictor_contract(tour),
    }
    directory = root / tour
    (directory / "predictor.pkl").write_bytes(payload)
    (directory / "predictor.pkl.envelope").write_text(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (directory / "predictor.pkl.envelope.pending").unlink(missing_ok=True)
    meta_path = directory / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({
        "tour": tour,
        "predictorArtifactId": PREDICTOR_IDS[tour],
        "modelTrainedAt": envelope["trainedAt"],
    })
    _write_json(meta_path, meta)
    return payload


@pytest.mark.parametrize(
    ("predictor_reason", "lineage_reason"),
    [
        ("PATH_INVALID", "PATH_INVALID"),
        ("ENVELOPE_IO", "IO_ERROR"),
        ("PAYLOAD_IO", "IO_ERROR"),
        ("PENDING_IO", "IO_ERROR"),
        ("PUBLICATION_IO", "IO_ERROR"),
        ("ENVELOPE_MALFORMED", "GRAPH_INVALID"),
        ("PAYLOAD_CHECKSUM_MISMATCH", "GRAPH_INVALID"),
    ],
)
def test_predictor_identity_failure_preserves_fatal_vs_rebuildable_class(
    tmp_path,
    monkeypatch,
    predictor_reason,
    lineage_reason,
):
    from tennis_model.model import artifact

    def reject(*_args, **_kwargs):
        raise artifact.PredictorArtifactError(
            getattr(artifact.PredictorArtifactReason, predictor_reason),
            "injected",
        )

    monkeypatch.setattr(
        lineage,
        "_validate_predictor_identity",
        _REAL_VALIDATE_PREDICTOR_IDENTITY,
    )
    monkeypatch.setattr(artifact, "validate_predictor_artifact_identity", reject)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage._validate_predictor_identity(tmp_path, "atp")

    assert caught.value.reason == getattr(lineage.LineageReason, lineage_reason)


def test_discovers_exact_fixed_recursive_and_optional_graph(tmp_path):
    _write_graph(tmp_path)
    roles = lineage.discover_tour_artifacts(tmp_path, "atp")

    assert roles["atp/meta.json"] == lineage.ROLE_PUBLIC_CORE
    assert roles["atp/matrix-index.json"] == lineage.ROLE_MATRIX_INDEX
    assert roles["atp/matrix-hard-bo3.json"] == lineage.ROLE_MATRIX_SHARD
    assert roles["atp/profile-0123456789abcdef.json"] == lineage.ROLE_PROFILE_SHARD
    assert roles["atp/scenario-718-2026.json"] == lineage.ROLE_SCENARIO_SHARD
    assert roles["atp/upcoming-event-718-2026.json"] == lineage.ROLE_UPCOMING_EVENT
    assert roles["atp/upcoming-evidence-718-2026.json"] == lineage.ROLE_UPCOMING_EVIDENCE
    assert roles["atp/accuracy.json"] == lineage.ROLE_EVALUATION
    assert "atp/health-source.json" not in roles
    assert list(roles) == sorted(roles)

    without_eval = tmp_path / "without-eval"
    _write_graph(without_eval, evaluation=False)
    assert not any(
        role == lineage.ROLE_EVALUATION
        for role in lineage.discover_tour_artifacts(without_eval, "wta").values()
    )


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("profile-index.json", {"profiles": [{"file": "../escape.json"}]}),
        (
            "upcoming-index.json",
            {"events": [{"file": "upcoming-event-x.json", "evidenceFile": "/x.json"}]},
        ),
    ],
)
def test_rejects_traversal_and_absolute_index_references(tmp_path, filename, payload):
    _write_graph(tmp_path)
    _write_json(tmp_path / "atp" / filename, payload)
    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.discover_tour_artifacts(tmp_path, "atp")
    assert caught.value.reason == lineage.LineageReason.PATH_INVALID


def test_rejects_duplicate_refs_duplicate_json_keys_unknown_files_and_caps(tmp_path, monkeypatch):
    _write_graph(tmp_path)
    profile = "profile-0123456789abcdef.json"
    _write_json(
        tmp_path / "atp" / "profile-index.json",
        {"profiles": [{"file": profile}, {"file": profile}]},
    )
    with pytest.raises(lineage.ArtifactLineageError, match="duplicate reference"):
        lineage.discover_tour_artifacts(tmp_path, "atp")

    _write_tour_graph(tmp_path, "atp")
    (tmp_path / "atp" / "matrix-index.json").write_text(
        '{"surfaces":{},"surfaces":{}}', encoding="utf-8"
    )
    with pytest.raises(lineage.ArtifactLineageError) as duplicate_key:
        lineage.discover_tour_artifacts(tmp_path, "atp")
    assert duplicate_key.value.reason == lineage.LineageReason.GRAPH_INVALID

    _write_tour_graph(tmp_path, "atp")
    _write_json(tmp_path / "atp" / "stray.json", {})
    with pytest.raises(lineage.ArtifactLineageError, match="unknown public JSON"):
        lineage.discover_tour_artifacts(tmp_path, "atp")

    (tmp_path / "atp" / "stray.json").unlink()
    monkeypatch.setattr(lineage, "MAX_INDEX_REFERENCES", 0)
    with pytest.raises(lineage.ArtifactLineageError) as oversized:
        lineage.discover_tour_artifacts(tmp_path, "atp")
    assert oversized.value.reason == lineage.LineageReason.BOUNDS_EXCEEDED


def test_manifest_contract_is_exact_sorted_and_rejects_unknown_role(tmp_path):
    _write_graph(tmp_path)
    context = lineage.begin_release("full")
    drafts = [
        _draft(tmp_path, tour, context)
        for tour in lineage.TOURS
    ]
    manifest = lineage.merge_release_drafts(context, drafts)
    assert list(manifest) == [
        "schema", "releaseId", "parent", "createdAt", "mode", "artifacts"
    ]
    assert [row["path"] for row in manifest["artifacts"]] == sorted(
        row["path"] for row in manifest["artifacts"]
    )
    assert set(manifest["artifacts"][0]) == lineage._ARTIFACT_FIELDS

    extra = dict(manifest)
    extra["surprise"] = True
    with pytest.raises(lineage.ArtifactLineageError) as unknown:
        lineage.seal_release(tmp_path, extra)
    assert unknown.value.reason == lineage.LineageReason.CONTRACT_INVALID

    bad_role = json.loads(json.dumps(manifest))
    bad_role["artifacts"][0]["role"] = "mystery"
    with pytest.raises(lineage.ArtifactLineageError, match="role is unknown"):
        lineage.seal_release(tmp_path, bad_role)

    reversed_rows = json.loads(json.dumps(manifest))
    reversed_rows["artifacts"].reverse()
    with pytest.raises(lineage.ArtifactLineageError, match="sorted"):
        lineage.seal_release(tmp_path, reversed_rows)

    forged_predictor = json.loads(json.dumps(manifest))
    players = next(
        row for row in forged_predictor["artifacts"]
        if row["path"] == "atp/players.json"
    )
    players["predictorArtifactId"] = "33333333-3333-4333-8333-333333333333"
    with pytest.raises(lineage.ArtifactLineageError, match="unlike meta"):
        lineage.seal_release(tmp_path, forged_predictor)

    fully_forged = json.loads(json.dumps(manifest))
    forged_id = "33333333-3333-4333-8333-333333333333"
    _write_json(
        tmp_path / "atp" / "meta.json",
        {
            "tour": "atp",
            "predictorArtifactId": forged_id,
            "modelTrainedAt": "2026-08-24T00:00:00Z",
        },
    )
    meta_bytes = (tmp_path / "atp" / "meta.json").read_bytes()
    for record in fully_forged["artifacts"]:
        if record["path"].startswith("atp/"):
            record["predictorArtifactId"] = forged_id
        if record["path"] == "atp/meta.json":
            record["bytes"] = len(meta_bytes)
            record["sha256"] = hashlib.sha256(meta_bytes).hexdigest()
    with pytest.raises(lineage.ArtifactLineageError, match="envelope identity"):
        lineage.seal_release(tmp_path, fully_forged)


def test_hashes_exact_bytes_not_semantically_equivalent_json(tmp_path):
    _write_graph(tmp_path)
    release = _seal(tmp_path)
    record = release.records_by_path["atp/players.json"]
    original = (tmp_path / "atp" / "players.json").read_bytes()
    assert record["bytes"] == len(original)
    assert record["sha256"] == hashlib.sha256(original).hexdigest()

    parsed = json.loads(original)
    (tmp_path / "atp" / "players.json").write_text(
        json.dumps(parsed, indent=4) + "\n", encoding="utf-8"
    )
    with pytest.raises(lineage.ArtifactLineageError) as changed:
        lineage.validate_release(tmp_path)
    assert changed.value.reason == lineage.LineageReason.ARTIFACT_MISMATCH
    assert changed.value.path == "atp/players.json"


def test_private_acceptance_binds_exact_manifest_release_and_validator(tmp_path):
    accepted = _accepted(tmp_path)
    receipt_path = tmp_path / lineage.ACCEPTANCE_FILENAME
    assert receipt_path.suffix == ".private"
    assert accepted.receipt == {
        "schema": lineage.ACCEPTANCE_SCHEMA,
        "releaseId": accepted.release_id,
        "manifestSha256": accepted.release.manifest_sha256,
        "acceptedAt": accepted.receipt["acceptedAt"],
        "validator": "predeploy-integrity-gate-v1",
    }

    # JSON-equivalent manifest bytes still have a different receipt binding.
    receipt_before = receipt_path.read_bytes()
    manifest_path = tmp_path / lineage.MANIFEST_FILENAME
    manifest_path.write_bytes(manifest_path.read_bytes() + b"\n")
    with pytest.raises(lineage.ArtifactLineageError) as mismatch:
        lineage.load_accepted_release(tmp_path)
    assert mismatch.value.reason == lineage.LineageReason.ACCEPTANCE_MISMATCH
    assert receipt_path.read_bytes() == receipt_before


def test_acceptance_rereads_graph_after_receipt_publication(tmp_path, monkeypatch):
    _write_graph(tmp_path)
    _seal(tmp_path)
    real_atomic = lineage._atomic_replace_at

    def mutate_after_receipt(parent_fd, filename, raw):
        real_atomic(parent_fd, filename, raw)
        if filename == lineage.ACCEPTANCE_FILENAME:
            (tmp_path / "atp" / "players.json").write_text(
                '{"mutated":true}', encoding="utf-8"
            )

    monkeypatch.setattr(lineage, "_atomic_replace_at", mutate_after_receipt)
    with pytest.raises(lineage.ArtifactLineageError) as changed:
        lineage.accept_release(
            tmp_path,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )
    assert changed.value.reason == lineage.LineageReason.ARTIFACT_MISMATCH
    with pytest.raises(lineage.ArtifactLineageError):
        lineage.load_accepted_release(tmp_path)


def test_acceptance_root_swap_before_receipt_write_mutates_neither_replacement(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "source"
    moved_source = tmp_path / "moved-source"
    replacement = tmp_path / "replacement"
    _write_graph(source)
    candidate = _seal(source)
    replacement_accepted = _accepted(replacement)
    real_validate = lineage.validate_release
    swapped = False

    def validate_then_swap(root, *args, **kwargs):
        nonlocal swapped
        result = real_validate(root, *args, **kwargs)
        if Path(root) == source and not swapped:
            swapped = True
            source.replace(moved_source)
            replacement.replace(source)
        return result

    monkeypatch.setattr(lineage, "validate_release", validate_then_swap)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.accept_release(
            source,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (moved_source / lineage.MANIFEST_FILENAME).read_bytes() == (
        candidate.manifest_bytes
    )
    assert not (moved_source / lineage.ACCEPTANCE_FILENAME).exists()
    assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
        replacement_accepted.release.manifest_bytes
    )
    assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
        replacement_accepted.receipt_bytes
    )


def test_seal_root_swap_after_graph_validation_preserves_both_existing_roots(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "source"
    moved_source = tmp_path / "moved-source"
    replacement = tmp_path / "replacement"
    accepted_a = _accepted(source)
    accepted_b = _accepted(replacement)
    context = lineage.begin_release("full")
    manifest = lineage.merge_release_drafts(
        context,
        [_draft(source, tour, context) for tour in lineage.TOURS],
    )
    real_validate_graph = lineage._validate_manifest_against_graph
    swapped = False

    def validate_graph_then_swap(*args, **kwargs):
        nonlocal swapped
        result = real_validate_graph(*args, **kwargs)
        if not swapped:
            swapped = True
            source.replace(moved_source)
            replacement.replace(source)
        return result

    monkeypatch.setattr(
        lineage,
        "_validate_manifest_against_graph",
        validate_graph_then_swap,
    )

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.seal_release(source, manifest)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (moved_source / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted_a.release.manifest_bytes
    )
    assert (moved_source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
        accepted_a.receipt_bytes
    )
    assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted_b.release.manifest_bytes
    )
    assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == accepted_b.receipt_bytes


def test_acceptance_receipt_rejects_unknown_duplicate_and_future_fields(tmp_path):
    accepted = _accepted(tmp_path)
    receipt_path = tmp_path / lineage.ACCEPTANCE_FILENAME
    malformed = dict(accepted.receipt)
    malformed["unknown"] = True
    receipt_path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(lineage.ArtifactLineageError) as unknown:
        lineage.load_accepted_release(tmp_path)
    assert unknown.value.reason == lineage.LineageReason.ACCEPTANCE_INVALID

    receipt_path.write_text(
        '{"schema":"artifact-lineage-acceptance-v1",'
        '"schema":"artifact-lineage-acceptance-v1"}',
        encoding="utf-8",
    )
    with pytest.raises(lineage.ArtifactLineageError) as duplicate:
        lineage.load_accepted_release(tmp_path)
    assert duplicate.value.reason == lineage.LineageReason.ACCEPTANCE_INVALID

    future = dict(accepted.receipt)
    future["acceptedAt"] = (
        datetime.now(UTC) + timedelta(hours=1)
    ).isoformat().replace("+00:00", "Z")
    receipt_path.write_text(json.dumps(future), encoding="utf-8")
    with pytest.raises(lineage.ArtifactLineageError) as future_error:
        lineage.load_accepted_release(tmp_path)
    assert future_error.value.reason == lineage.LineageReason.ACCEPTANCE_INVALID


def test_red_candidate_is_never_accepted_and_stale_receipt_cannot_bless_it(tmp_path):
    prior = _accepted(tmp_path)
    carried = lineage.carry_forward_release(tmp_path, tmp_path)
    candidate = _seal(
        tmp_path,
        accepted_prior=prior,
        carried=carried,
        mode="quick",
    )
    assert candidate.release_id != prior.release_id
    assert not (tmp_path / lineage.ACCEPTANCE_FILENAME).exists()

    with pytest.raises(lineage.ArtifactLineageError) as red:
        lineage.accept_release(
            tmp_path,
            semantic_gate_passed=False,
            validator="predeploy-integrity-gate-v1",
        )
    assert red.value.reason == lineage.LineageReason.SEMANTIC_GATE_RED
    assert not (tmp_path / lineage.ACCEPTANCE_FILENAME).exists()
    with pytest.raises(lineage.ArtifactLineageError) as stale:
        lineage.load_accepted_release(tmp_path)
    assert stale.value.reason == lineage.LineageReason.ACCEPTANCE_MISSING


def test_carry_requires_full_exact_accepted_prior_and_preserves_origin(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    prior = _accepted(source)
    _write_json(destination / "atp" / "health-source.json", {"operational": True})
    (destination / "atp" / "predictor.pkl").write_bytes(b"cached model remains private")
    carried = lineage.carry_forward_release(source, destination)
    assert carried.accepted.release_id == prior.release_id
    assert (destination / "atp" / "health-source.json").exists()
    assert (destination / "atp" / "predictor.pkl").exists()

    context = lineage.begin_release("quick", accepted_prior=carried.accepted)
    old_records = carried.accepted.release.records_by_path
    _write_json(destination / "atp" / "players.json", {"quick": "new exact bytes"})
    drafts = [
        _draft(
            destination,
            tour,
            context,
            carried=carried,
            produced_paths=(
                {"atp/players.json", "atp/meta.json"}
                if tour == "atp"
                else {"wta/meta.json"}
            ),
            producer="pipeline.quick",
        )
        for tour in lineage.TOURS
    ]
    candidate = lineage.seal_release(
        destination, lineage.merge_release_drafts(context, drafts)
    )
    records = candidate.records_by_path
    assert records["atp/method.json"]["originRelease"] == old_records["atp/method.json"][
        "originRelease"
    ]
    assert records["atp/meta.json"]["originRelease"] == context.release_id
    assert records["atp/players.json"]["originRelease"] == context.release_id

    # A tampered accepted cache is rejected before any destination byte is touched.
    broken_destination = tmp_path / "broken-destination"
    broken_destination.mkdir()
    sentinel = broken_destination / "sentinel"
    sentinel.write_text("untouched", encoding="utf-8")
    _write_json(source / "wta" / "players.json", {"tampered": True})
    with pytest.raises(lineage.ArtifactLineageError):
        lineage.carry_forward_release(source, broken_destination)
    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert not (broken_destination / lineage.MANIFEST_FILENAME).exists()


@pytest.mark.parametrize("swap_kind", ["root", "parent", "tour"])
def test_unequal_carry_is_bound_to_attempted_destination_under_replacement(
    tmp_path,
    monkeypatch,
    swap_kind,
):
    source = tmp_path / "source"
    source_accepted = _accepted(source)
    if swap_kind == "parent":
        parent = tmp_path / "carry-parent"
        destination = parent / "output"
        moved_parent = tmp_path / "moved-carry-parent"
        replacement_parent = tmp_path / "replacement-carry-parent"
        replacement_root = replacement_parent / "output"
    else:
        parent = tmp_path
        destination = tmp_path / "destination"
        moved_destination = tmp_path / "moved-carry-attempt"
        replacement_root = tmp_path / "replacement-destination"
    destination_accepted = _accepted(destination)
    if swap_kind in {"root", "parent"}:
        replacement_accepted = _accepted(replacement_root)
    else:
        replacement_atp = tmp_path / "replacement-atp"
        replacement_atp.mkdir()
        (replacement_atp / "sentinel.bin").write_bytes(b"unrelated tour bytes")
        (replacement_atp / "predictor.pkl.envelope").write_bytes(
            b"unrelated predictor envelope"
        )
        moved_atp = tmp_path / "moved-carry-atp"

    destination_identity = (
        os.stat(destination).st_dev,
        os.stat(destination).st_ino,
    )
    atp_identity = (
        os.stat(destination / "atp").st_dev,
        os.stat(destination / "atp").st_ino,
    )
    real_unlink = lineage._durable_unlink_at
    real_replace = lineage._atomic_replace_at
    swapped = False

    def unlink_then_swap(parent_fd, filename):
        nonlocal swapped
        real_unlink(parent_fd, filename)
        opened = os.fstat(parent_fd)
        if (
            swapped
            or swap_kind == "tour"
            or filename != lineage.ACCEPTANCE_FILENAME
            or (opened.st_dev, opened.st_ino) != destination_identity
        ):
            return
        swapped = True
        if swap_kind == "root":
            destination.replace(moved_destination)
            replacement_root.replace(destination)
        else:
            parent.replace(moved_parent)
            replacement_parent.replace(parent)

    def replace_then_swap(parent_fd, filename, raw):
        nonlocal swapped
        real_replace(parent_fd, filename, raw)
        opened = os.fstat(parent_fd)
        if (
            swapped
            or swap_kind != "tour"
            or filename != "predictor.pkl.envelope"
            or (opened.st_dev, opened.st_ino) != atp_identity
        ):
            return
        swapped = True
        (destination / "atp").replace(moved_atp)
        replacement_atp.replace(destination / "atp")

    monkeypatch.setattr(lineage, "_durable_unlink_at", unlink_then_swap)
    monkeypatch.setattr(lineage, "_atomic_replace_at", replace_then_swap)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.carry_forward_release(source, destination)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert swapped
    assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
        source_accepted.release.manifest_bytes
    )
    assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
        source_accepted.receipt_bytes
    )
    if swap_kind in {"root", "parent"}:
        moved_attempt = (
            moved_destination if swap_kind == "root" else moved_parent / "output"
        )
        assert not (moved_attempt / lineage.MANIFEST_FILENAME).exists()
        assert not (moved_attempt / lineage.ACCEPTANCE_FILENAME).exists()
        assert (destination / lineage.MANIFEST_FILENAME).read_bytes() == (
            replacement_accepted.release.manifest_bytes
        )
        assert (destination / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
            replacement_accepted.receipt_bytes
        )
    else:
        assert not (destination / lineage.MANIFEST_FILENAME).exists()
        assert not (destination / lineage.ACCEPTANCE_FILENAME).exists()
        assert (destination / "atp" / "sentinel.bin").read_bytes() == (
            b"unrelated tour bytes"
        )
        assert (destination / "atp" / "predictor.pkl.envelope").read_bytes() == (
            b"unrelated predictor envelope"
        )
        assert (moved_atp / "predictor.pkl.envelope").read_bytes() != (
            destination / "atp" / "predictor.pkl.envelope"
        ).read_bytes()
    assert destination_accepted.release_id != source_accepted.release_id


def test_meta_predictor_chain_quick_bootstrap_and_current_production_proof(tmp_path):
    _write_graph(tmp_path)
    context = lineage.begin_release("full")
    all_atp = set(lineage.discover_tour_artifacts(tmp_path, "atp"))

    _write_json(
        tmp_path / "atp" / "meta.json",
        {
            "tour": "wta",
            "predictorArtifactId": PREDICTOR_IDS["atp"],
            "modelTrainedAt": "2026-08-24T00:00:00Z",
        },
    )
    with pytest.raises(lineage.ArtifactLineageError, match="tour"):
        _draft(tmp_path, "atp", context)

    _write_json(
        tmp_path / "atp" / "meta.json",
        {
            "tour": "atp",
            "predictorArtifactId": PREDICTOR_IDS["atp"],
            "modelTrainedAt": "2026-08-23T00:00:00Z",
        },
    )
    with pytest.raises(lineage.ArtifactLineageError, match="model age"):
        _draft(tmp_path, "atp", context)

    _write_json(
        tmp_path / "atp" / "meta.json",
        {
            "tour": "atp",
            "predictorArtifactId": PREDICTOR_IDS["wta"],
            "modelTrainedAt": "2026-08-24T00:00:00Z",
        },
    )
    with pytest.raises(lineage.ArtifactLineageError) as mismatch:
        lineage.draft_tour_release(
            tmp_path,
            "atp",
            context,
            _provenance("atp"),
            produced_paths=all_atp,
        )
    assert mismatch.value.reason == lineage.LineageReason.GRAPH_INVALID
    assert mismatch.value.path == "atp/meta.json"

    _write_json(
        tmp_path / "atp" / "meta.json",
        {
            "tour": "atp",
            "predictorArtifactId": PREDICTOR_IDS["atp"],
            "modelTrainedAt": "2026-08-24T00:00:00Z",
        },
    )
    with pytest.raises(lineage.ArtifactLineageError) as retained_optional:
        lineage.draft_tour_release(
            tmp_path,
            "atp",
            context,
            _provenance("atp"),
            produced_paths=all_atp - {"atp/track.json"},
        )
    assert retained_optional.value.reason == lineage.LineageReason.CONTRACT_INVALID
    assert retained_optional.value.path == "atp/track.json"

    quick = lineage.begin_release("quick")
    with pytest.raises(lineage.ArtifactLineageError, match="accepted carry-forward"):
        lineage.draft_tour_release(
            tmp_path,
            "atp",
            quick,
            _provenance("atp", "pipeline.quick"),
            produced_paths=all_atp,
        )


def test_draft_strictly_binds_envelope_payload_tour_runtime_meta_and_provenance(
    tmp_path, monkeypatch
):
    _write_graph(tmp_path)
    payloads = {
        tour: _write_strict_predictor_pair(tmp_path, tour)
        for tour in lineage.TOURS
    }
    monkeypatch.setattr(
        lineage, "_validate_predictor_identity", _REAL_VALIDATE_PREDICTOR_IDENTITY
    )
    context = lineage.begin_release("full")
    _draft(tmp_path, "atp", context)

    (tmp_path / "atp" / "predictor.pkl").write_bytes(b"X" * len(payloads["atp"]))
    with pytest.raises(lineage.ArtifactLineageError, match="payload_checksum_mismatch"):
        _draft(tmp_path, "atp", context)

    _write_strict_predictor_pair(tmp_path, "atp")
    (tmp_path / "atp" / "predictor.pkl.envelope.pending").write_text(
        "publication interrupted", encoding="utf-8"
    )
    with pytest.raises(lineage.ArtifactLineageError, match="incomplete_write"):
        _draft(tmp_path, "atp", context)

    _write_strict_predictor_pair(tmp_path, "atp")
    (tmp_path / "atp" / "predictor.pkl.envelope").unlink()
    with pytest.raises(lineage.ArtifactLineageError, match="envelope_io"):
        _draft(tmp_path, "atp", context)

    _write_strict_predictor_pair(tmp_path, "atp")
    (tmp_path / "wta" / "predictor.pkl").write_bytes(payloads["atp"])
    (tmp_path / "wta" / "predictor.pkl.envelope").write_bytes(
        (tmp_path / "atp" / "predictor.pkl.envelope").read_bytes()
    )
    with pytest.raises(lineage.ArtifactLineageError, match="tour_mismatch"):
        _draft(tmp_path, "wta", context)

    _write_strict_predictor_pair(tmp_path, "wta")
    _write_json(
        tmp_path / "atp" / "meta.json",
        {
            "tour": "atp",
            "predictorArtifactId": PREDICTOR_IDS["wta"],
            "modelTrainedAt": json.loads(
                (tmp_path / "atp" / "predictor.pkl.envelope").read_text()
            )["trainedAt"],
        },
    )
    with pytest.raises(lineage.ArtifactLineageError, match="does not match meta"):
        _draft(tmp_path, "atp", context)


def test_produced_artifact_recorder_is_thread_safe_scoped_and_success_only(tmp_path):
    # Calls made by single-tour/legacy writers outside an exact all-tour round are no-ops,
    # even if their arguments would not be valid public paths.
    lineage.note_produced_artifact("unknown", "../ignored.json")
    assert lineage.snapshot_produced_artifacts() == {"atp": (), "wta": ()}

    collector = lineage.begin_produced_artifacts()
    with collector:
        with pytest.raises(lineage.ArtifactLineageError, match="already active"):
            lineage.begin_produced_artifacts()

        filenames = [f"profile-{index:016x}.json" for index in range(12)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda name: lineage.note_produced_artifact("atp", name), filenames))
        lineage.note_produced_artifact("wta", "meta.json")

        with pytest.raises(lineage.ArtifactLineageError):
            lineage.note_produced_artifact("atp", "../escape.json")
        with pytest.raises(lineage.ArtifactLineageError):
            lineage.note_produced_artifact("atp", "health-source.json")

        def write_then_note(path: Path, *, fail: bool) -> None:
            path.write_text("partial", encoding="utf-8")
            if fail:
                raise OSError("simulated write failure before completion note")
            lineage.note_produced_artifact("atp", path.name)

        with pytest.raises(OSError):
            write_then_note(tmp_path / "failed.json", fail=True)
        write_then_note(tmp_path / "completed.json", fail=False)
        active = lineage.snapshot_produced_artifacts("atp")
        assert "atp/failed.json" not in active
        assert "atp/completed.json" in active

    final = collector.snapshot()
    assert final["wta"] == ("wta/meta.json",)
    assert set(final["atp"]) == {
        *(f"atp/{name}" for name in filenames),
        "atp/completed.json",
    }
    assert lineage.snapshot_produced_artifacts("atp") == ()
    with pytest.raises(lineage.ArtifactLineageError, match="does not own"):
        collector.reset()


def test_rewrite_invalidates_earlier_success_before_mutation(monkeypatch, tmp_path):
    path = tmp_path / "atp" / "players.json"
    path.parent.mkdir()
    with lineage.begin_produced_artifacts() as produced:
        lineage.write_produced_artifact(
            "atp", path, b'{"generation":1}', trusted_root=tmp_path
        )
        assert produced.snapshot("atp") == ("atp/players.json",)

        real_atomic = lineage._atomic_write_public_bytes

        def replace_then_crash(parent_fd, filename, raw):
            real_atomic(parent_fd, filename, raw)
            raise OSError("crash after durable replace, before completion proof")

        monkeypatch.setattr(
            lineage, "_atomic_write_public_bytes", replace_then_crash
        )
        with pytest.raises(OSError, match="before completion proof"):
            lineage.write_produced_artifact(
                "atp", path, b'{"generation":2}', trusted_root=tmp_path
            )

        assert path.read_bytes() == b'{"generation":2}'
        assert produced.snapshot("atp") == ()


def test_atomic_writer_preserves_prior_bytes_when_replace_fails(monkeypatch, tmp_path):
    path = tmp_path / "atp" / "performance.json"
    path.parent.mkdir()
    path.write_bytes(b'{"prior":true}')
    real_replace = lineage.os.replace

    def fail_target_replace(source, target, **kwargs):
        if target == path.name and kwargs.get("dst_dir_fd") is not None:
            raise OSError("replace failed")
        real_replace(source, target, **kwargs)

    monkeypatch.setattr(lineage.os, "replace", fail_target_replace)
    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", path.name)
        with pytest.raises(OSError, match="replace failed"):
            lineage.write_produced_artifact(
                "atp", path, b'{"new":true}', trusted_root=tmp_path
            )
        assert produced.snapshot("atp") == ()
    assert path.read_bytes() == b'{"prior":true}'
    assert not list(path.parent.glob(".*.tmp"))


def test_artifact_batch_proves_nothing_when_second_replace_fails(monkeypatch, tmp_path):
    tour_dir = tmp_path / "atp"
    tour_dir.mkdir()
    track_path = tour_dir / "track.json"
    performance_path = tour_dir / "performance.json"
    track_path.write_bytes(b'{"prior":1}')
    performance_path.write_bytes(b'{"prior":1}')
    real_atomic = lineage._atomic_write_public_bytes
    calls = 0

    def fail_second(parent_fd, filename, raw):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("second artifact failed")
        real_atomic(parent_fd, filename, raw)

    monkeypatch.setattr(lineage, "_atomic_write_public_bytes", fail_second)
    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", track_path.name)
        lineage.note_produced_artifact("atp", performance_path.name)
        with pytest.raises(OSError, match="second artifact failed"):
            lineage.write_produced_artifact_batch(
                "atp",
                (
                    (track_path, b'{"current":2}'),
                    (performance_path, b'{"current":2}'),
                ),
                trusted_root=tmp_path,
            )
        assert produced.snapshot("atp") == ()
    assert track_path.read_bytes() == b'{"current":2}'
    assert performance_path.read_bytes() == b'{"prior":1}'


@pytest.mark.parametrize("symlink_component", ["root", "tour"])
def test_public_writer_rejects_symlinked_parent_before_invalidating_proof(
    tmp_path, symlink_component
):
    external = tmp_path / "external"
    external.mkdir()
    if symlink_component == "root":
        (external / "atp").mkdir()
        root = tmp_path / "output"
        root.symlink_to(external, target_is_directory=True)
    else:
        root = tmp_path / "output"
        root.mkdir()
        (root / "atp").symlink_to(external, target_is_directory=True)
    path = root / "atp" / "players.json"

    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", path.name)
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage.write_produced_artifact(
                "atp", path, b'{"new":true}', trusted_root=root
            )
        assert caught.value.reason == lineage.LineageReason.PATH_INVALID
        assert produced.snapshot("atp") == ("atp/players.json",)

    assert not (external / "players.json").exists()
    assert not (external / "atp" / "players.json").exists()


def test_public_writer_rejects_symlinked_ancestor_without_o_nofollow(
    tmp_path, monkeypatch
):
    external = tmp_path / "external"
    (external / "output" / "atp").mkdir(parents=True)
    alias = tmp_path / "aliased-parent"
    alias.symlink_to(external, target_is_directory=True)
    path = alias / "output" / "atp" / "players.json"
    monkeypatch.delattr(lineage.os, "O_NOFOLLOW", raising=False)

    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", path.name)
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage.write_produced_artifact(
                "atp",
                path,
                b'{"new":true}',
                trusted_root=alias / "output",
            )
        assert caught.value.reason == lineage.LineageReason.PATH_INVALID
        assert produced.snapshot("atp") == ("atp/players.json",)

    assert not (external / "output" / "atp" / "players.json").exists()


def test_public_writer_parent_swap_cannot_redirect_or_restore_fresh_proof(
    tmp_path, monkeypatch
):
    root = tmp_path / "output"
    tour_dir = root / "atp"
    tour_dir.mkdir(parents=True)
    detached = root / "detached-atp"
    external = tmp_path / "external"
    external.mkdir()
    path = tour_dir / "players.json"
    real_atomic = lineage._atomic_write_public_bytes

    def swap_parent_then_write(parent_fd, filename, raw):
        tour_dir.rename(detached)
        tour_dir.symlink_to(external, target_is_directory=True)
        real_atomic(parent_fd, filename, raw)

    monkeypatch.setattr(
        lineage, "_atomic_write_public_bytes", swap_parent_then_write
    )
    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", path.name)
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage.write_produced_artifact(
                "atp", path, b'{"new":true}', trusted_root=root
            )
        assert caught.value.reason == lineage.LineageReason.PATH_INVALID
        assert produced.snapshot("atp") == ()

    assert (detached / "players.json").read_bytes() == b'{"new":true}'
    assert not (external / "players.json").exists()


def test_public_batch_validates_every_parent_before_invalidating_any_proof(tmp_path):
    root = tmp_path / "output"
    tour_dir = root / "atp"
    tour_dir.mkdir(parents=True)
    external = tmp_path / "external"
    external.mkdir()
    alias = root / "alias"
    alias.symlink_to(external, target_is_directory=True)
    valid = tour_dir / "track.json"
    redirected = alias / "performance.json"

    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", valid.name)
        lineage.note_produced_artifact("atp", redirected.name)
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage.write_produced_artifact_batch(
                "atp",
                (
                    (valid, b'{"current":2}'),
                    (redirected, b'{"current":2}'),
                ),
                trusted_root=root,
            )
        assert caught.value.reason == lineage.LineageReason.PATH_INVALID
        assert produced.snapshot("atp") == (
            "atp/performance.json",
            "atp/track.json",
        )

    assert not valid.exists()
    assert not (external / "performance.json").exists()


def test_public_writer_requires_production_or_explicit_trusted_root(tmp_path):
    root = tmp_path / "custom-output"
    path = root / "atp" / "players.json"

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.write_produced_artifact("atp", path, b'{"blocked":true}')
    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert not path.exists()

    lineage.write_produced_artifact(
        "atp", path, b'{"allowed":true}', trusted_root=root
    )
    assert path.read_bytes() == b'{"allowed":true}'


def test_private_producer_names_fail_before_write_or_batch_invalidation(tmp_path):
    root = tmp_path / "output"
    tour_dir = root / "atp"
    tour_dir.mkdir(parents=True)
    private = tour_dir / "health-source.json"
    private.write_bytes(b'{"private":"prior"}')

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.write_produced_artifact(
            "atp", private, b'{"private":"overwritten"}', trusted_root=root
        )
    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert private.read_bytes() == b'{"private":"prior"}'

    players = tour_dir / "players.json"
    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", players.name)
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage.write_produced_artifact_batch(
                "atp",
                (
                    (players, b'{"public":true}'),
                    (private, b'{"private":"overwritten"}'),
                ),
                trusted_root=root,
            )
        assert caught.value.reason == lineage.LineageReason.PATH_INVALID
        assert produced.snapshot("atp") == ("atp/players.json",)
    assert not players.exists()
    assert private.read_bytes() == b'{"private":"prior"}'


def test_remove_produced_artifact_rejects_parent_symlink_without_external_delete(
    tmp_path
):
    root = tmp_path / "output"
    root.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    victim = external / "players.json"
    victim.write_bytes(b'{"external":true}')
    (root / "atp").symlink_to(external, target_is_directory=True)
    path = root / "atp" / "players.json"

    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", path.name)
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage.remove_produced_artifact(
                "atp", path, trusted_root=root
            )
        assert caught.value.reason == lineage.LineageReason.PATH_INVALID
        assert produced.snapshot("atp") == ("atp/players.json",)
    assert victim.read_bytes() == b'{"external":true}'


def test_remove_produced_artifact_absence_is_synced_and_private_rejected(
    tmp_path, monkeypatch
):
    root = tmp_path / "output"
    tour_dir = root / "atp"
    tour_dir.mkdir(parents=True)
    missing = tour_dir / "players.json"
    private = tour_dir / "health-source.json"
    fsyncs = []
    real_fsync = lineage.os.fsync

    def observe_fsync(fd):
        fsyncs.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(lineage.os, "fsync", observe_fsync)
    with lineage.begin_produced_artifacts() as produced:
        lineage.note_produced_artifact("atp", missing.name)
        lineage.remove_produced_artifact(
            "atp", missing, trusted_root=root
        )
        assert produced.snapshot("atp") == ()
        synced_after_absence = len(fsyncs)

        lineage.note_produced_artifact("atp", missing.name)
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage.remove_produced_artifact(
                "atp", private, trusted_root=root
            )
        assert caught.value.reason == lineage.LineageReason.PATH_INVALID
        assert produced.snapshot("atp") == ("atp/players.json",)

    assert synced_after_absence >= 1


def test_candidate_mutation_unblesses_receipt_then_manifest(tmp_path, monkeypatch):
    _accepted(tmp_path)
    order = []
    real_unlink = lineage._durable_unlink_at

    def record_unlink(parent_fd, filename):
        order.append(filename)
        real_unlink(parent_fd, filename)

    monkeypatch.setattr(lineage, "_durable_unlink_at", record_unlink)
    lineage.unbless_release_for_mutation(tmp_path)
    assert order == [lineage.ACCEPTANCE_FILENAME, lineage.MANIFEST_FILENAME]
    assert not (tmp_path / lineage.ACCEPTANCE_FILENAME).exists()
    assert not (tmp_path / lineage.MANIFEST_FILENAME).exists()


@pytest.mark.parametrize("swap_kind", ["root", "parent"])
def test_unbless_root_binding_revokes_attempt_without_touching_replacement(
    tmp_path,
    monkeypatch,
    swap_kind,
):
    if swap_kind == "root":
        parent = tmp_path
        root = parent / "output"
        moved_root = tmp_path / "moved-output-attempt"
        replacement = tmp_path / "replacement-output"
        replacement_root = replacement
    else:
        parent = tmp_path / "candidate-parent"
        root = parent / "output"
        moved_parent = tmp_path / "moved-candidate-parent"
        replacement_parent = tmp_path / "replacement-parent"
        replacement_root = replacement_parent / "output"
    accepted_attempt = _accepted(root)
    accepted_replacement = _accepted(replacement_root)
    real_unlink = lineage._durable_unlink_at
    swapped = False

    def unlink_then_swap(parent_fd, filename):
        nonlocal swapped
        real_unlink(parent_fd, filename)
        if swapped or filename != lineage.ACCEPTANCE_FILENAME:
            return
        swapped = True
        if swap_kind == "root":
            root.replace(moved_root)
            replacement.replace(root)
        else:
            parent.replace(moved_parent)
            replacement_parent.replace(parent)

    monkeypatch.setattr(lineage, "_durable_unlink_at", unlink_then_swap)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.unbless_release_for_mutation(root)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    moved_attempt = moved_root if swap_kind == "root" else moved_parent / "output"
    assert not (moved_attempt / lineage.ACCEPTANCE_FILENAME).exists()
    assert not (moved_attempt / lineage.MANIFEST_FILENAME).exists()
    assert (root / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
        accepted_replacement.receipt_bytes
    )
    assert (root / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted_replacement.release.manifest_bytes
    )
    assert accepted_attempt.release.manifest_bytes != (
        root / lineage.MANIFEST_FILENAME
    ).read_bytes()


def test_unbless_rejects_symlinked_root_without_deleting_external_release(tmp_path):
    external = tmp_path / "external"
    accepted = _accepted(external)
    manifest = accepted.release.manifest_bytes
    receipt = accepted.receipt_bytes
    alias = tmp_path / "output"
    alias.symlink_to(external, target_is_directory=True)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.unbless_release_for_mutation(alias)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (external / lineage.MANIFEST_FILENAME).read_bytes() == manifest
    assert (external / lineage.ACCEPTANCE_FILENAME).read_bytes() == receipt


def test_atomic_writes_use_unique_temps_fsync_and_manifest_after_artifacts(
    tmp_path, monkeypatch
):
    _write_graph(tmp_path)
    context = lineage.begin_release("full")
    drafts = [
        _draft(tmp_path, tour, context)
        for tour in lineage.TOURS
    ]
    manifest = lineage.merge_release_drafts(context, drafts)

    replacements = []
    fsyncs = []
    real_replace = lineage.os.replace
    real_fsync = lineage.os.fsync

    def observe_replace(source, destination, **kwargs):
        replacements.append((Path(source), Path(destination)))
        real_replace(source, destination, **kwargs)

    def observe_fsync(fd):
        fsyncs.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(lineage.os, "replace", observe_replace)
    monkeypatch.setattr(lineage.os, "fsync", observe_fsync)
    lineage.seal_release(tmp_path, manifest)
    lineage._atomic_write_bytes(tmp_path / "one.private", b"one")
    lineage._atomic_write_bytes(tmp_path / "one.private", b"two")

    assert replacements[0][1].name == lineage.MANIFEST_FILENAME
    temp_names = [source.name for source, target in replacements if target.name == "one.private"]
    assert len(temp_names) == 2 and len(set(temp_names)) == 2
    assert all(name.endswith(".tmp") for name in temp_names)
    assert len(fsyncs) >= 6  # file and directory for all three atomic writes
    assert not list(tmp_path.glob(".*.tmp"))


def test_failed_public_replace_fsyncs_temp_cleanup_directory(tmp_path, monkeypatch):
    root = tmp_path / "output"
    path = root / "atp" / "players.json"
    (root / "atp").mkdir(parents=True)
    cleanup_unlinked = False
    cleanup_synced = False
    real_replace = lineage.os.replace
    real_unlink = lineage.os.unlink
    real_fsync = lineage.os.fsync

    def fail_replace(source, destination, **kwargs):
        if destination == path.name and kwargs.get("dst_dir_fd") is not None:
            raise OSError("simulated replace failure")
        return real_replace(source, destination, **kwargs)

    def observe_unlink(target, **kwargs):
        nonlocal cleanup_unlinked
        result = real_unlink(target, **kwargs)
        if str(target).startswith(f".{path.name}."):
            cleanup_unlinked = True
        return result

    def observe_fsync(fd):
        nonlocal cleanup_synced
        if cleanup_unlinked:
            cleanup_synced = True
        return real_fsync(fd)

    monkeypatch.setattr(lineage.os, "replace", fail_replace)
    monkeypatch.setattr(lineage.os, "unlink", observe_unlink)
    monkeypatch.setattr(lineage.os, "fsync", observe_fsync)
    with pytest.raises(OSError, match="replace failure"):
        lineage.write_produced_artifact(
            "atp", path, b'{"new":true}', trusted_root=root
        )

    assert cleanup_unlinked is True
    assert cleanup_synced is True
    assert not path.exists()
    assert not list(path.parent.glob(".*.tmp"))


def test_durable_unlink_fsyncs_parent_after_removing_leaf(tmp_path, monkeypatch):
    path = tmp_path / "atp" / "stale.json"
    path.parent.mkdir()
    path.write_text("stale", encoding="utf-8")
    events = []

    real_unlink = lineage.os.unlink
    real_fsync = lineage.os.fsync

    def observe_unlink(filename, **kwargs):
        result = real_unlink(filename, **kwargs)
        events.append(("unlink", filename))
        return result

    def observe_fsync(fd):
        assert not path.exists()
        events.append(("fsync", fd))
        return real_fsync(fd)

    monkeypatch.setattr(lineage.os, "unlink", observe_unlink)
    monkeypatch.setattr(lineage.os, "fsync", observe_fsync)

    lineage._durable_unlink(path, trusted_root=tmp_path)

    assert [event[0] for event in events] == ["unlink", "fsync"]


def test_durable_unlink_fsyncs_parent_when_leaf_is_already_absent(
    tmp_path, monkeypatch
):
    path = tmp_path / "atp" / "missing.json"
    path.parent.mkdir()
    fsyncs = []
    real_fsync = lineage.os.fsync

    def observe_fsync(fd):
        fsyncs.append(fd)
        real_fsync(fd)

    monkeypatch.setattr(lineage.os, "fsync", observe_fsync)
    lineage._durable_unlink(path, trusted_root=tmp_path)

    assert len(fsyncs) == 1


def test_durable_unlink_retry_syncs_absence_after_first_sync_failure(
    tmp_path, monkeypatch
):
    path = tmp_path / "atp" / "stale.json"
    path.parent.mkdir()
    path.write_text("stale", encoding="utf-8")
    real_fsync = lineage.os.fsync
    calls = 0

    def fail_once(fd):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated directory sync failure")
        real_fsync(fd)

    monkeypatch.setattr(lineage.os, "fsync", fail_once)
    with pytest.raises(OSError, match="directory sync failure"):
        lineage._durable_unlink(path, trusted_root=tmp_path)
    assert not path.exists()

    lineage._durable_unlink(path, trusted_root=tmp_path)
    assert calls == 2


def test_mirror_prune_sync_failure_cannot_publish_manifest(tmp_path, monkeypatch):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _accepted(source)
    _write_json(public / "atp" / "stale.json", {"old": True})
    (public / lineage.MANIFEST_FILENAME).write_bytes(b"old public pointer")
    real_unlink = lineage._durable_unlink_at

    def fail_after_prune_unlink(parent_fd, filename):
        if filename == "stale.json":
            os.unlink(filename, dir_fd=parent_fd)
            raise OSError("simulated prune directory fsync failure")
        real_unlink(parent_fd, filename)

    monkeypatch.setattr(lineage, "_durable_unlink_at", fail_after_prune_unlink)
    with pytest.raises(OSError, match="prune directory fsync failure"):
        lineage.mirror_release(source, public, require_accepted=True)

    assert not (public / "atp" / "stale.json").exists()
    assert not (public / lineage.MANIFEST_FILENAME).exists()


def test_manifest_driven_mirror_removes_unknown_and_private_and_copies_manifest_last(tmp_path):
    source = tmp_path / "source"
    public = tmp_path / "public"
    accepted = _accepted(source)
    _write_json(public / "atp" / "stale.json", {"old": True})
    (public / "atp" / "stage-status.private").write_text("leaked", encoding="utf-8")
    (public / lineage.ACCEPTANCE_FILENAME).write_text("leaked", encoding="utf-8")
    (public / "wta").mkdir(parents=True, exist_ok=True)
    (public / "wta" / "predictor.pkl.envelope").symlink_to(
        public / "does-not-exist"
    )
    (public / "wta" / "predictor.pkl.envelope.pending").symlink_to(
        public / "also-does-not-exist"
    )
    external = tmp_path / "external"
    external.mkdir()
    _write_json(external / "secret.json", {"private": True})
    (public / "atp" / "leak").symlink_to(external, target_is_directory=True)
    (public / "atp" / "stale.tmp").write_text("partial", encoding="utf-8")
    copied = []

    result = lineage.mirror_release(
        source,
        public,
        require_accepted=True,
        on_copy=copied.append,
    )
    assert result.release_id == accepted.release_id
    assert copied[-1] == lineage.MANIFEST_FILENAME
    assert result.copied[-1] == lineage.MANIFEST_FILENAME
    assert not (public / "atp" / "stale.json").exists()
    assert not (public / "atp" / "stage-status.private").exists()
    assert not (public / lineage.ACCEPTANCE_FILENAME).exists()
    assert not (public / "atp" / "predictor.pkl").exists()
    assert not (public / "wta" / "predictor.pkl.envelope").is_symlink()
    assert not (public / "wta" / "predictor.pkl.envelope.pending").is_symlink()
    assert not (public / "atp" / "leak").is_symlink()
    assert not (public / "atp" / "stale.tmp").exists()
    assert (external / "secret.json").exists()
    assert (public / lineage.MANIFEST_FILENAME).read_bytes() == accepted.release.manifest_bytes
    assert (public / "wta" / "players.json").read_bytes() == (
        source / "wta" / "players.json"
    ).read_bytes()


@pytest.mark.parametrize("operation", ["mirror", "carry"])
@pytest.mark.parametrize("source_inside_destination", [False, True])
def test_copy_roots_cannot_overlap_in_either_direction(
    tmp_path, operation, source_inside_destination
):
    if source_inside_destination:
        destination = tmp_path / "outer"
        source = destination / "source"
    else:
        source = tmp_path / "source"
        destination = source / "destination"
    accepted = _accepted(source)
    before_manifest = accepted.release.manifest_bytes
    before_player = (source / "atp" / "players.json").read_bytes()
    destination.mkdir(parents=True, exist_ok=True)
    sentinel = destination / "sentinel.txt"
    sentinel.write_text("untouched", encoding="utf-8")

    call = lineage.mirror_release if operation == "mirror" else lineage.carry_forward_release
    with pytest.raises(lineage.ArtifactLineageError) as caught:
        call(source, destination)
    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (source / lineage.MANIFEST_FILENAME).read_bytes() == before_manifest
    assert (source / "atp" / "players.json").read_bytes() == before_player
    assert sentinel.read_text(encoding="utf-8") == "untouched"


def test_publication_relationship_preflight_is_read_only_for_missing_destination(
    tmp_path,
):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    _accepted(source)

    assert lineage._preflight_publication_relationship(source, destination) == (
        source,
        destination,
    )
    assert not destination.exists()


@pytest.mark.parametrize("scope", ["data", "web"])
@pytest.mark.parametrize(
    "relationship",
    ["equal", "source-ancestor", "destination-ancestor", "alias"],
)
def test_publishers_reject_overlapping_roots_before_any_mutation(
    tmp_path,
    monkeypatch,
    scope,
    relationship,
):
    if relationship == "destination-ancestor":
        destination = tmp_path / "outer"
        source = destination / "source"
    else:
        source = tmp_path / "source"
        destination = tmp_path / "public"
    accepted = _accepted(source)

    if relationship == "equal":
        destination = source
    elif relationship == "source-ancestor":
        destination = source / "nested-public"
        destination.mkdir()
    elif relationship == "alias":
        destination.symlink_to(source, target_is_directory=True)

    sentinel_root = (
        destination
        if relationship in {"source-ancestor", "destination-ancestor"}
        else source
    )
    sentinel = sentinel_root / "unrelated-sentinel.txt"
    sentinel.write_bytes(b"must remain untouched")
    destination_pointer = destination / lineage.MANIFEST_FILENAME
    if relationship in {"source-ancestor", "destination-ancestor"}:
        destination_pointer.write_bytes(b"unrelated destination pointer")
    destination_before = destination_pointer.read_bytes()
    source_manifest_before = (source / lineage.MANIFEST_FILENAME).read_bytes()
    source_receipt_before = (source / lineage.ACCEPTANCE_FILENAME).read_bytes()

    if scope == "data":
        monkeypatch.setattr(
            lineage,
            "accept_release",
            lambda *_args, **_kwargs: pytest.fail(
                "relationship failure must precede acceptance"
            ),
        )
        call = lambda: lineage.publish_data_release(
            source,
            destination,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )
    else:
        call = lambda: lineage.publish_web_release(source, destination)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        call()

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (source / lineage.MANIFEST_FILENAME).read_bytes() == source_manifest_before
    assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == source_receipt_before
    assert destination_pointer.read_bytes() == destination_before
    assert sentinel.read_bytes() == b"must remain untouched"
    assert accepted.release.manifest_bytes == source_manifest_before


@pytest.mark.parametrize("operation", ["mirror", "carry"])
def test_copy_rejects_destination_tour_symlink_before_mutation(tmp_path, operation):
    source = tmp_path / "source"
    destination = tmp_path / "public"
    _accepted(source)
    (destination / "wta").mkdir(parents=True)
    sentinel = destination / "wta" / "sentinel.txt"
    sentinel.write_text("untouched", encoding="utf-8")
    (destination / "atp").symlink_to(destination / "wta", target_is_directory=True)

    call = lineage.mirror_release if operation == "mirror" else lineage.carry_forward_release
    with pytest.raises(lineage.ArtifactLineageError) as caught:
        call(source, destination)
    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert sentinel.read_text(encoding="utf-8") == "untouched"
    assert not (destination / lineage.MANIFEST_FILENAME).exists()


def test_two_tour_raw_legacy_fallback_is_removed():
    assert not hasattr(lineage, "_legacy_mirror_two_tour")
    assert not hasattr(lineage, "legacy_mirror_tour")
    assert not hasattr(lineage, "publish_shadow_release")


@pytest.mark.parametrize(
    ("reason", "code"),
    [
        (lineage.LineageReason.MANIFEST_MISSING, "output.lineage.manifest_missing"),
        (lineage.LineageReason.MANIFEST_INVALID, "output.lineage.manifest_invalid"),
        (lineage.LineageReason.CONTRACT_INVALID, "output.lineage.manifest_invalid"),
        (lineage.LineageReason.PATH_INVALID, "output.lineage.graph_invalid"),
        (lineage.LineageReason.BOUNDS_EXCEEDED, "output.lineage.bounds_exceeded"),
        (lineage.LineageReason.GRAPH_INVALID, "output.lineage.graph_invalid"),
        (lineage.LineageReason.ARTIFACT_MISSING, "output.lineage.artifact_missing"),
        (lineage.LineageReason.ARTIFACT_MISMATCH, "output.lineage.artifact_mismatch"),
        (lineage.LineageReason.ACCEPTANCE_MISSING, "output.lineage.acceptance_missing"),
        (lineage.LineageReason.ACCEPTANCE_INVALID, "output.lineage.acceptance_invalid"),
        (lineage.LineageReason.ACCEPTANCE_MISMATCH, "output.lineage.acceptance_invalid"),
        (lineage.LineageReason.SEMANTIC_GATE_RED, "output.lineage.candidate_rejected"),
        (lineage.LineageReason.IO_ERROR, "output.lineage.unreadable"),
    ],
)
def test_every_lineage_reason_has_one_blocking_issue_contract(reason, code):
    issue = lineage._issue_for(lineage.ArtifactLineageError(reason, "private detail"))

    assert issue.code == code
    assert issue.severity == "error"
    assert issue.reason == reason
    assert issue.tour is None and issue.path is None


@pytest.mark.parametrize(
    ("path", "expected_path", "expected_tour"),
    [
        ("atp", "atp", "atp"),
        ("wta", "wta", "wta"),
        ("atp/meta.json", "atp/meta.json", "atp"),
        ("wta/matrix-index.json", "wta/matrix-index.json", "wta"),
        ("../secret", None, None),
        (None, None, None),
    ],
)
def test_issue_scope_accepts_only_safe_tour_paths(path, expected_path, expected_tour):
    issue = lineage._issue_for(lineage.ArtifactLineageError(
        lineage.LineageReason.GRAPH_INVALID,
        "private detail",
        path=path,
    ))

    assert issue.path == expected_path
    assert issue.tour == expected_tour


@pytest.mark.parametrize("tour", lineage.TOURS)
@pytest.mark.parametrize(
    "breakage",
    ["missing-tour", "predictor", "malformed-index", "artifact-hash"],
)
def test_real_tour_lineage_failure_pages_only_its_owner_with_stable_identity(
    tmp_path,
    monkeypatch,
    tour,
    breakage,
):
    from tennis_model.data import health

    root = tmp_path / "output"
    if breakage == "predictor":
        _accepted_with_strict_predictors(root, monkeypatch)
    else:
        _accepted(root)
    if breakage == "missing-tour":
        (root / tour).replace(tmp_path / f"missing-{tour}")
    elif breakage == "predictor":
        predictor = root / tour / "predictor.pkl"
        predictor.write_bytes(b"X" * predictor.stat().st_size)
    elif breakage == "malformed-index":
        (root / tour / "matrix-index.json").write_bytes(b"[]")
    else:
        (root / tour / "players.json").write_bytes(b'{"changed":true}')
    monkeypatch.setattr(health, "OUTPUT_DIR", root)

    first_summary, first = health._lineage_observation(require_accepted=True)
    second_summary, second = health._lineage_observation(require_accepted=True)
    other = next(item for item in lineage.TOURS if item != tour)

    assert first_summary["status"] == "invalid"
    assert second_summary == first_summary
    assert first[other] == [] and second[other] == []
    assert len(first[tour]) == len(second[tour]) == 1
    assert first[tour][0].severity == "error"
    assert first[tour][0].fingerprint == second[tour][0].fingerprint
    assert first[tour][0].as_dict() == second[tour][0].as_dict()


@pytest.mark.parametrize("breakage", ["manifest", "acceptance"])
def test_real_root_lineage_failure_remains_global_without_duplicate_findings(
    tmp_path,
    monkeypatch,
    breakage,
):
    from tennis_model.data import health

    root = tmp_path / "output"
    _accepted(root)
    if breakage == "manifest":
        (root / lineage.MANIFEST_FILENAME).write_bytes(b"not strict json")
    else:
        (root / lineage.ACCEPTANCE_FILENAME).unlink()
    monkeypatch.setattr(health, "OUTPUT_DIR", root)

    _, findings = health._lineage_observation(require_accepted=True)

    assert all(len(findings[tour]) == 1 for tour in lineage.TOURS)
    assert {finding.tour for values in findings.values() for finding in values} == {
        "atp",
        "wta",
    }
    assert len({
        finding.fingerprint
        for values in findings.values()
        for finding in values
    }) == 2


def test_real_lineage_gate_lifecycle_requires_authoritative_acceptance_and_recovers(
    tmp_path,
    monkeypatch,
):
    from tennis_model.data import health

    root = tmp_path / "output"
    _write_graph(root)
    monkeypatch.setattr(health, "OUTPUT_DIR", root)

    missing_summary, missing = health._lineage_observation(require_accepted=False)
    assert missing_summary["status"] == "missing"
    assert all(len(missing[tour]) == 1 for tour in lineage.TOURS)

    candidate = _seal(root)
    candidate_summary, candidate_findings = health._lineage_observation(
        require_accepted=False
    )
    assert candidate_summary["status"] == "valid"
    assert candidate_summary["releaseId"] == candidate.release_id
    assert candidate_findings == {"atp": [], "wta": []}

    unaccepted_summary, unaccepted = health._lineage_observation(
        require_accepted=True
    )
    assert unaccepted_summary["status"] == "unaccepted"
    assert all(len(unaccepted[tour]) == 1 for tour in lineage.TOURS)

    accepted = lineage.accept_release(
        root,
        semantic_gate_passed=True,
        validator="predeploy-integrity-gate-v1",
    )
    recovered_summary, recovered = health._lineage_observation(require_accepted=True)
    repeated_summary, repeated = health._lineage_observation(require_accepted=True)
    assert recovered_summary["status"] == "accepted"
    assert recovered_summary["releaseId"] == accepted.release_id
    assert recovered == repeated == {"atp": [], "wta": []}
    assert repeated_summary == recovered_summary


def test_root_relationship_normalizes_filesystem_anchor_alias_before_overlap(tmp_path):
    tmp_alias = Path("/tmp")
    if not tmp_alias.is_symlink() or tmp_alias.resolve() != Path("/private/tmp"):
        pytest.skip("requires the macOS /tmp filesystem alias")
    alias_base = tmp_alias / f"lineage-overlap-{tmp_path.name}"
    source = alias_base / "source"
    physical_source = Path("/private/tmp") / alias_base.name / "source"
    destination = physical_source / "destination"
    source.mkdir(parents=True)
    try:
        with pytest.raises(lineage.ArtifactLineageError) as caught:
            lineage._validate_root_relationship(
                source, destination, allow_equal=False
            )
        assert "cannot contain one another" in caught.value.detail
        assert not destination.exists()
    finally:
        if destination.exists():
            destination.rmdir()
        source.rmdir()
        alias_base.rmdir()


def test_mirror_failure_before_manifest_leaves_release_explicitly_unblessed(tmp_path, monkeypatch):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _accepted(source)
    public.mkdir()
    old_manifest = b"old accepted public manifest"
    (public / lineage.MANIFEST_FILENAME).write_bytes(old_manifest)
    real_write = lineage._atomic_replace_at

    def crash_before_manifest(parent_fd, filename, raw):
        if filename == lineage.MANIFEST_FILENAME:
            raise OSError("simulated crash")
        real_write(parent_fd, filename, raw)

    monkeypatch.setattr(lineage, "_atomic_replace_at", crash_before_manifest)
    with pytest.raises(OSError, match="simulated crash"):
        lineage.mirror_release(source, public, require_accepted=True)
    assert not (public / lineage.MANIFEST_FILENAME).exists()


def test_mirror_postvalidates_destination_and_removes_manifest_on_callback_corruption(
    tmp_path
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _accepted(source)

    def corrupt_after_copy(relative):
        if relative == "atp/players.json":
            (public / relative).write_text('{"corrupt":true}', encoding="utf-8")

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.mirror_release(
            source,
            public,
            require_accepted=True,
            on_copy=corrupt_after_copy,
        )
    assert caught.value.reason == lineage.LineageReason.ARTIFACT_MISMATCH
    assert not (public / lineage.MANIFEST_FILENAME).exists()


@pytest.mark.parametrize("relative", [
    "atp/health-source.json",
    "wta/leaked.private",
])
def test_mirror_rejects_file_created_after_cleanup_and_revokes_manifest(
    tmp_path, relative
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _accepted(source)

    def leak_after_manifest(copied):
        if copied == lineage.MANIFEST_FILENAME:
            target = public / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("private", encoding="utf-8")

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.mirror_release(
            source,
            public,
            require_accepted=True,
            on_copy=leak_after_manifest,
        )
    assert caught.value.reason == lineage.LineageReason.GRAPH_INVALID
    assert (public / relative).exists()
    assert not (public / lineage.MANIFEST_FILENAME).exists()


def test_mirror_rejects_symlink_created_after_cleanup_and_revokes_manifest(tmp_path):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _accepted(source)
    relative = Path("wta/leaked-link.json")

    def leak_after_manifest(copied):
        if copied == lineage.MANIFEST_FILENAME:
            target = public / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(Path("../atp/players.json"))

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.mirror_release(
            source,
            public,
            require_accepted=True,
            on_copy=leak_after_manifest,
        )
    assert caught.value.reason == lineage.LineageReason.GRAPH_INVALID
    assert (public / relative).is_symlink()
    assert not (public / lineage.MANIFEST_FILENAME).exists()


def test_enforced_state_is_blocking_and_draft_propagates(tmp_path):
    state = lineage.inspect_release(tmp_path)
    assert state.state == "missing"
    assert state.issues[0].as_dict() == {
        "code": "output.lineage.manifest_missing",
        "severity": "error",
        "reason": "manifest-missing",
        "tour": None,
        "path": None,
    }

    _write_graph(tmp_path)
    _write_json(
        tmp_path / "atp" / "scenario-index.json",
        {"events": [{"file": "../../private.json"}]},
    )
    context = lineage.begin_release("full")
    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.draft_tour_release(
            tmp_path,
            "atp",
            context,
            _provenance("atp"),
            produced_paths=(),
        )
    assert caught.value.reason == lineage.LineageReason.PATH_INVALID


def test_health_summary_has_exact_safe_shape(tmp_path):
    accepted = _accepted(tmp_path)
    summary = lineage.lineage_health_summary(tmp_path)
    assert set(summary) == {
        "schema", "status", "releaseId", "manifestSha256", "tours"
    }
    assert summary["schema"] == lineage.ARTIFACT_LINEAGE_SCHEMA
    assert summary["status"] == "accepted"
    assert summary["releaseId"] == accepted.release_id
    assert summary["manifestSha256"] == accepted.release.manifest_sha256
    assert summary["tours"] == ["atp", "wta"]

    missing = lineage.lineage_health_summary(tmp_path / "missing")
    assert missing == {
        "schema": lineage.ARTIFACT_LINEAGE_SCHEMA,
        "status": "missing",
        "releaseId": None,
        "manifestSha256": None,
        "tours": ["atp", "wta"],
    }


def test_strict_json_rejects_integer_that_is_nonfinite_in_browser_runtime():
    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage._strict_json_loads(
            b'{"value":1e309}',
            reason=lineage.LineageReason.GRAPH_INVALID,
        )
    assert caught.value.reason == lineage.LineageReason.GRAPH_INVALID

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage._strict_json_loads(
            b'{"value":1' + (b"0" * 400) + b'}',
            reason=lineage.LineageReason.GRAPH_INVALID,
        )
    assert caught.value.reason == lineage.LineageReason.GRAPH_INVALID


def test_regular_file_reader_rejects_leaf_symlink_without_o_nofollow(
    tmp_path, monkeypatch
):
    target = tmp_path / "target.json"
    target.write_bytes(b'{"secret":true}')
    link = tmp_path / "artifact.json"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("filesystem does not support symlinks")
    monkeypatch.delattr(lineage.os, "O_NOFOLLOW", raising=False)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage._read_regular_file(link, lineage.MAX_ARTIFACT_BYTES)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert target.read_bytes() == b'{"secret":true}'


def test_release_reader_rejects_symlinked_source_ancestor(tmp_path):
    real_parent = tmp_path / "real-parent"
    release_root = real_parent / "release"
    accepted = _accepted(release_root)
    alias = tmp_path / "source-alias"
    alias.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.validate_release(alias / "release", require_accepted=True)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (release_root / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted.release.manifest_bytes
    )


def test_initialize_release_root_creates_only_expected_leaf_and_tours(tmp_path):
    parent = tmp_path / "data"
    parent.mkdir()
    root = parent / "output"

    initialized = lineage.initialize_release_root(root)

    assert initialized == root
    assert {path.name for path in parent.iterdir()} == {"output"}
    assert {path.name for path in root.iterdir()} == {"atp", "wta"}
    assert all(path.is_dir() and not path.is_symlink() for path in root.iterdir())


def test_initialize_release_root_never_creates_missing_higher_ancestor(tmp_path):
    missing_parent = tmp_path / "missing-parent"

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.initialize_release_root(missing_parent / "output")

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert not missing_parent.exists()


@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_initialize_release_root_rejects_non_directory_or_linked_root(tmp_path, kind):
    parent = tmp_path / "data"
    parent.mkdir()
    root = parent / "output"
    external = tmp_path / "external"
    if kind == "file":
        root.write_text("not a directory", encoding="utf-8")
    else:
        external.mkdir()
        root.symlink_to(external, target_is_directory=True)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.initialize_release_root(root)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    if kind == "file":
        assert root.read_text(encoding="utf-8") == "not a directory"
    else:
        assert root.is_symlink()
        assert list(external.iterdir()) == []


def test_initialize_release_root_rejects_linked_ancestor(tmp_path):
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    alias = tmp_path / "parent-alias"
    alias.symlink_to(real_parent, target_is_directory=True)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.initialize_release_root(alias / "output")

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert not (real_parent / "output").exists()


@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_initialize_release_root_rejects_non_directory_or_linked_tour(tmp_path, kind):
    root = tmp_path / "output"
    root.mkdir()
    tour = root / "atp"
    external = tmp_path / "external-tour"
    if kind == "file":
        tour.write_text("not a directory", encoding="utf-8")
    else:
        external.mkdir()
        tour.symlink_to(external, target_is_directory=True)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.initialize_release_root(root)

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    if kind == "file":
        assert tour.read_text(encoding="utf-8") == "not a directory"
    else:
        assert tour.is_symlink()
        assert list(external.iterdir()) == []


def test_begin_release_rejects_linked_predictor_leaf_without_revoking_proof(
    tmp_path,
    monkeypatch,
):
    from tennis_model import pipeline

    root = tmp_path / "output"
    accepted = _accepted_with_strict_predictors(root, monkeypatch)
    payload = root / "atp" / "predictor.pkl"
    external = tmp_path / "external-predictor.pkl"
    payload.replace(external)
    payload.symlink_to(external)
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", root)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        pipeline._begin_release("quick")

    assert caught.value.reason == lineage.LineageReason.IO_ERROR
    assert (root / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted.release.manifest_bytes
    )
    assert (root / lineage.ACCEPTANCE_FILENAME).read_bytes() == accepted.receipt_bytes
    assert external.read_bytes() == b"strict-private-payload:atp"


def test_begin_release_rejects_linked_predictor_parent_without_revoking_proof(
    tmp_path,
    monkeypatch,
):
    from tennis_model import pipeline

    root = tmp_path / "output"
    accepted = _accepted_with_strict_predictors(root, monkeypatch)
    external = tmp_path / "external-atp"
    (root / "atp").replace(external)
    (root / "atp").symlink_to(external, target_is_directory=True)
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", root)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        pipeline._begin_release("quick")

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (root / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted.release.manifest_bytes
    )
    assert (root / lineage.ACCEPTANCE_FILENAME).read_bytes() == accepted.receipt_bytes
    assert (external / "predictor.pkl").read_bytes() == b"strict-private-payload:atp"


@pytest.mark.parametrize(
    "predictor_reason",
    ["ENVELOPE_IO", "PAYLOAD_IO", "PENDING_IO", "PUBLICATION_IO"],
)
def test_begin_release_propagates_predictor_io_without_revoking_proof(
    tmp_path,
    monkeypatch,
    predictor_reason,
):
    from tennis_model.model import artifact

    from tennis_model import pipeline

    root = tmp_path / "output"
    accepted = _accepted(root)

    def reject(*_args, **_kwargs):
        raise artifact.PredictorArtifactError(
            getattr(artifact.PredictorArtifactReason, predictor_reason),
            "injected I/O",
        )

    monkeypatch.setattr(
        lineage,
        "_validate_predictor_identity",
        _REAL_VALIDATE_PREDICTOR_IDENTITY,
    )
    monkeypatch.setattr(artifact, "validate_predictor_artifact_identity", reject)
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", root)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        pipeline._begin_release("quick")

    assert caught.value.reason == lineage.LineageReason.IO_ERROR
    assert (root / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted.release.manifest_bytes
    )
    assert (root / lineage.ACCEPTANCE_FILENAME).read_bytes() == accepted.receipt_bytes


def test_begin_release_treats_predictor_checksum_failure_as_rebuildable(
    tmp_path,
    monkeypatch,
):
    from tennis_model.model import artifact

    from tennis_model import pipeline

    root = tmp_path / "output"
    _accepted(root)

    def reject(*_args, **_kwargs):
        raise artifact.PredictorArtifactError(
            artifact.PredictorArtifactReason.PAYLOAD_CHECKSUM_MISMATCH,
            "injected corruption",
        )

    monkeypatch.setattr(
        lineage,
        "_validate_predictor_identity",
        _REAL_VALIDATE_PREDICTOR_IDENTITY,
    )
    monkeypatch.setattr(artifact, "validate_predictor_artifact_identity", reject)
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", root)

    plan = pipeline._begin_release("quick")

    assert plan.bootstrap and plan.context.mode == "full" and plan.context.parent is None
    assert not (root / lineage.MANIFEST_FILENAME).exists()
    assert not (root / lineage.ACCEPTANCE_FILENAME).exists()


def test_web_publication_requires_acceptance_and_never_raw_copies(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _write_graph(source)
    public.mkdir()
    (public / lineage.MANIFEST_FILENAME).write_text("stale", encoding="utf-8")

    def forbidden_accept(*args, **kwargs):
        raise AssertionError("web scope must never accept")

    monkeypatch.setattr(lineage, "accept_release", forbidden_accept)
    assert lineage.main([
        "publish",
        "--scope", "web",
        "--source", str(source),
        "--destination", str(public),
    ]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["schema"] == "artifact-lineage-publication-v1"
    assert output["status"] == "failed"
    assert output["issues"][0]["code"] == "output.lineage.manifest_missing"
    assert output["issues"][0]["severity"] == "error"
    assert not (public / lineage.MANIFEST_FILENAME).exists()
    assert not (public / "atp" / "players.json").exists()


def test_data_publication_failure_revokes_source_and_destination_validity(
    tmp_path, monkeypatch
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _write_graph(source)
    _seal(source)
    public.mkdir()
    (public / lineage.MANIFEST_FILENAME).write_text("stale", encoding="utf-8")

    def fail_mirror(*_args, **_kwargs):
        raise OSError("public destination unavailable")

    monkeypatch.setattr(lineage, "mirror_release", fail_mirror)
    with pytest.raises(OSError, match="destination unavailable"):
        lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )
    assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    assert not (source / lineage.MANIFEST_FILENAME).exists()
    assert not (public / lineage.MANIFEST_FILENAME).exists()


def test_data_publication_revokes_receipt_and_manifest_when_acceptance_raises_after_replace(
    tmp_path, monkeypatch
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _write_graph(source)
    _seal(source)
    real_atomic = lineage._atomic_replace_at

    def fail_after_receipt_replace(parent_fd, filename, raw):
        real_atomic(parent_fd, filename, raw)
        if filename == lineage.ACCEPTANCE_FILENAME:
            raise RuntimeError("post-receipt callback failed")

    monkeypatch.setattr(lineage, "_atomic_replace_at", fail_after_receipt_replace)
    with pytest.raises(RuntimeError, match="post-receipt"):
        lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )
    assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    assert not (source / lineage.MANIFEST_FILENAME).exists()


def test_web_copy_failure_preserves_source_acceptance_and_revokes_public_pointer(
    tmp_path, monkeypatch
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    accepted = _accepted(source)
    public.mkdir()
    (public / lineage.MANIFEST_FILENAME).write_text("stale", encoding="utf-8")

    def broken_mirror(*args, **kwargs):
        raise OSError("destination unavailable")

    monkeypatch.setattr(lineage, "mirror_release", broken_mirror)
    with pytest.raises(OSError, match="destination unavailable"):
        lineage.publish_web_release(source, public)
    assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == accepted.receipt_bytes
    assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted.release.manifest_bytes
    )
    assert not (public / lineage.MANIFEST_FILENAME).exists()


@pytest.mark.parametrize("scope", ["data", "web"])
@pytest.mark.parametrize("mutation", ["artifact", "manifest", "receipt"])
def test_publishers_reject_source_mutation_after_copy_and_apply_scope_cleanup(
    tmp_path,
    scope,
    mutation,
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    accepted = _accepted(source)
    original_manifest = accepted.release.manifest_bytes
    original_receipt = accepted.receipt_bytes
    mutated = False

    def mutate_source(_relative):
        nonlocal mutated
        if mutated:
            return
        mutated = True
        if mutation == "artifact":
            (source / "atp" / "players.json").write_bytes(b'{"mutated":true}')
        elif mutation == "manifest":
            (source / lineage.MANIFEST_FILENAME).write_bytes(b"mutated manifest")
        else:
            (source / lineage.ACCEPTANCE_FILENAME).write_bytes(b"mutated receipt")

    if scope == "data":
        call = lambda: lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
            on_copy=mutate_source,
        )
    else:
        call = lambda: lineage.publish_web_release(
            source,
            public,
            on_copy=mutate_source,
        )

    with pytest.raises(lineage.ArtifactLineageError):
        call()

    assert mutated
    assert not (public / lineage.MANIFEST_FILENAME).exists()
    if scope == "data":
        assert not (source / lineage.MANIFEST_FILENAME).exists()
        assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    elif mutation == "manifest":
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == b"mutated manifest"
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == original_receipt
    elif mutation == "receipt":
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == original_manifest
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == b"mutated receipt"
    else:
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == original_manifest
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == original_receipt


@pytest.mark.parametrize("scope", ["data", "web"])
def test_publishers_reject_a_different_still_valid_source_receipt(
    tmp_path,
    scope,
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    accepted = _accepted(source)
    replacement_receipt = None

    def reaccept_source(_relative):
        nonlocal replacement_receipt
        if replacement_receipt is None:
            replacement_receipt = lineage.accept_release(
                source,
                semantic_gate_passed=True,
                validator="alternate-predeploy-gate-v1",
            ).receipt_bytes

    if scope == "data":
        call = lambda: lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
            on_copy=reaccept_source,
        )
    else:
        call = lambda: lineage.publish_web_release(
            source,
            public,
            on_copy=reaccept_source,
        )

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        call()

    assert caught.value.reason == lineage.LineageReason.ACCEPTANCE_MISMATCH
    assert replacement_receipt is not None
    assert replacement_receipt != accepted.receipt_bytes
    assert not (public / lineage.MANIFEST_FILENAME).exists()
    if scope == "data":
        assert not (source / lineage.MANIFEST_FILENAME).exists()
        assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    else:
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
            accepted.release.manifest_bytes
        )
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == replacement_receipt


@pytest.mark.parametrize("scope", ["data", "web"])
def test_publishers_reject_valid_source_a_to_b_swap_with_exact_pointer_policy(
    tmp_path,
    monkeypatch,
    scope,
):
    source = tmp_path / "source"
    replacement = tmp_path / "replacement-source"
    moved_attempt = tmp_path / "moved-source-a"
    public = tmp_path / "public"
    accepted_a = _accepted(source)
    accepted_b = _accepted(replacement)
    real_accept = lineage.accept_release
    real_mirror = lineage.mirror_release
    swapped = False

    def swap_sources():
        nonlocal swapped
        if swapped:
            return
        swapped = True
        source.replace(moved_attempt)
        replacement.replace(source)

    if scope == "data":
        def accept_then_swap(*args, **kwargs):
            accepted = real_accept(*args, **kwargs)
            swap_sources()
            return accepted

        monkeypatch.setattr(lineage, "accept_release", accept_then_swap)
        call = lambda: lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )
    else:
        def mirror_after_swap(*args, **kwargs):
            swap_sources()
            return real_mirror(*args, **kwargs)

        monkeypatch.setattr(lineage, "mirror_release", mirror_after_swap)
        call = lambda: lineage.publish_web_release(source, public)

    with pytest.raises(lineage.ArtifactLineageError):
        call()

    assert swapped
    assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
        accepted_b.release.manifest_bytes
    )
    assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == accepted_b.receipt_bytes
    if scope == "data":
        assert not (moved_attempt / lineage.MANIFEST_FILENAME).exists()
        assert not (moved_attempt / lineage.ACCEPTANCE_FILENAME).exists()
    else:
        assert (moved_attempt / lineage.MANIFEST_FILENAME).read_bytes() == (
            accepted_a.release.manifest_bytes
        )
        assert (moved_attempt / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
            accepted_a.receipt_bytes
        )
    assert not (public / lineage.MANIFEST_FILENAME).exists()


@pytest.mark.parametrize("scope", ["data", "web"])
@pytest.mark.parametrize("swap_kind", ["root", "parent"])
def test_publication_failure_cleans_attempt_fd_without_touching_replacement_root(
    tmp_path,
    scope,
    swap_kind,
):
    source = tmp_path / "source"
    accepted = _accepted(source)
    if swap_kind == "root":
        parent = tmp_path
        public = parent / "public"
        moved_public = tmp_path / "moved-public-attempt"
        replacement = tmp_path / "replacement-public"
        replacement.mkdir()
        replacement_pointer = replacement / lineage.MANIFEST_FILENAME
    else:
        parent = tmp_path / "publication-parent"
        public = parent / "public"
        moved_parent = tmp_path / "moved-publication-parent"
        replacement_parent = tmp_path / "replacement-parent"
        replacement = replacement_parent / "public"
        replacement.mkdir(parents=True)
        replacement_pointer = replacement / lineage.MANIFEST_FILENAME
    public.mkdir(parents=True)
    replacement_pointer.write_bytes(b"unrelated replacement manifest")
    replacement_sentinel = replacement / "unrelated-sentinel.txt"
    replacement_sentinel.write_bytes(b"unrelated replacement bytes")
    swapped = False

    def swap_and_fail(_relative):
        nonlocal swapped
        if swapped:
            return
        swapped = True
        if swap_kind == "root":
            public.replace(moved_public)
            replacement.replace(public)
        else:
            parent.replace(moved_parent)
            replacement_parent.replace(parent)
        raise RuntimeError("injected publication root swap")

    if scope == "data":
        call = lambda: lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
            on_copy=swap_and_fail,
        )
    else:
        call = lambda: lineage.publish_web_release(
            source,
            public,
            on_copy=swap_and_fail,
        )

    with pytest.raises(RuntimeError, match="root swap"):
        call()

    assert swapped
    assert (public / lineage.MANIFEST_FILENAME).read_bytes() == (
        b"unrelated replacement manifest"
    )
    assert (public / "unrelated-sentinel.txt").read_bytes() == (
        b"unrelated replacement bytes"
    )
    original_attempt = (
        moved_public if swap_kind == "root" else moved_parent / "public"
    )
    assert not (original_attempt / lineage.MANIFEST_FILENAME).exists()
    if scope == "data":
        assert not (source / lineage.MANIFEST_FILENAME).exists()
        assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    else:
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
            accepted.release.manifest_bytes
        )
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
            accepted.receipt_bytes
        )


@pytest.mark.parametrize("scope", ["data", "web"])
def test_pre_mirror_destination_replacement_never_revokes_unrelated_pointer(
    tmp_path,
    monkeypatch,
    scope,
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    moved_attempt = tmp_path / "moved-public-attempt"
    replacement = tmp_path / "replacement-public"
    accepted = _accepted(source)
    public.mkdir()
    (public / lineage.MANIFEST_FILENAME).write_bytes(b"old attempt pointer")
    replacement.mkdir()
    (replacement / lineage.MANIFEST_FILENAME).write_bytes(
        b"unrelated replacement pointer"
    )
    (replacement / "sentinel.txt").write_bytes(b"unrelated replacement bytes")
    real_accept = lineage.accept_release
    real_mirror = lineage.mirror_release
    swapped = False

    def swap_destination():
        nonlocal swapped
        if swapped:
            return
        swapped = True
        public.replace(moved_attempt)
        replacement.replace(public)

    if scope == "data":
        def accept_then_swap(*args, **kwargs):
            result = real_accept(*args, **kwargs)
            swap_destination()
            return result

        monkeypatch.setattr(lineage, "accept_release", accept_then_swap)
        call = lambda: lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )
    else:
        def mirror_after_swap(*args, **kwargs):
            swap_destination()
            return real_mirror(*args, **kwargs)

        monkeypatch.setattr(lineage, "mirror_release", mirror_after_swap)
        call = lambda: lineage.publish_web_release(source, public)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        call()

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert (public / lineage.MANIFEST_FILENAME).read_bytes() == (
        b"unrelated replacement pointer"
    )
    assert (public / "sentinel.txt").read_bytes() == b"unrelated replacement bytes"
    assert not (moved_attempt / lineage.MANIFEST_FILENAME).exists()
    if scope == "data":
        assert not (source / lineage.MANIFEST_FILENAME).exists()
        assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    else:
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
            accepted.release.manifest_bytes
        )
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
            accepted.receipt_bytes
        )


@pytest.mark.parametrize("scope", ["data", "web"])
@pytest.mark.parametrize("swap_phase", ["during-copy", "before-prune"])
def test_destination_tour_replacement_is_never_written_or_pruned(
    tmp_path,
    scope,
    swap_phase,
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    moved_atp = tmp_path / "moved-atp-attempt"
    replacement_atp = tmp_path / "replacement-atp"
    accepted = _accepted(source)
    (public / "atp").mkdir(parents=True)
    (public / "wta").mkdir()
    replacement_atp.mkdir()
    replacement_sentinel = replacement_atp / "sentinel.json"
    replacement_sentinel.write_bytes(b'{"unrelated":true}')
    replacement_private = replacement_atp / "private.bin"
    replacement_private.write_bytes(b"unrelated private bytes")
    copied_artifacts = 0
    trigger_at = 1 if swap_phase == "during-copy" else len(accepted.release.records)
    swapped = False

    def swap_tour(relative):
        nonlocal copied_artifacts, swapped
        if relative == lineage.MANIFEST_FILENAME:
            return
        copied_artifacts += 1
        if copied_artifacts != trigger_at:
            return
        (public / "atp").replace(moved_atp)
        replacement_atp.replace(public / "atp")
        swapped = True

    if scope == "data":
        call = lambda: lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
            on_copy=swap_tour,
        )
    else:
        call = lambda: lineage.publish_web_release(
            source,
            public,
            on_copy=swap_tour,
        )

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        call()

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert swapped
    assert (public / "atp" / "sentinel.json").read_bytes() == b'{"unrelated":true}'
    assert (public / "atp" / "private.bin").read_bytes() == b"unrelated private bytes"
    assert not (public / lineage.MANIFEST_FILENAME).exists()
    if scope == "data":
        assert not (source / lineage.MANIFEST_FILENAME).exists()
        assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    else:
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
            accepted.release.manifest_bytes
        )
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
            accepted.receipt_bytes
        )


@pytest.mark.parametrize("scope", ["data", "web"])
def test_mid_prune_tour_swap_keeps_unrelated_same_name_files(
    tmp_path,
    monkeypatch,
    scope,
):
    source = tmp_path / "source"
    public = tmp_path / "public"
    moved_atp = tmp_path / "moved-atp-attempt"
    replacement_atp = tmp_path / "replacement-atp"
    accepted = _accepted(source)
    (public / "atp").mkdir(parents=True)
    (public / "wta").mkdir()
    stale = public / "atp" / "same-name-stale.json"
    stale.write_bytes(b"attempt stale bytes")
    replacement_atp.mkdir()
    (replacement_atp / stale.name).write_bytes(b"unrelated same-name bytes")
    (replacement_atp / "sentinel.bin").write_bytes(b"unrelated sentinel")
    attempted_atp_identity = (
        os.stat(public / "atp").st_dev,
        os.stat(public / "atp").st_ino,
    )
    real_unlink = lineage._durable_unlink_at
    swapped = False

    def swap_during_bound_unlink(parent_fd, filename):
        nonlocal swapped
        opened = os.fstat(parent_fd)
        if not swapped and (opened.st_dev, opened.st_ino) == attempted_atp_identity:
            (public / "atp").replace(moved_atp)
            replacement_atp.replace(public / "atp")
            swapped = True
        real_unlink(parent_fd, filename)

    monkeypatch.setattr(lineage, "_durable_unlink_at", swap_during_bound_unlink)
    if scope == "data":
        call = lambda: lineage.publish_data_release(
            source,
            public,
            semantic_gate_passed=True,
            validator="predeploy-integrity-gate-v1",
        )
    else:
        call = lambda: lineage.publish_web_release(source, public)

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        call()

    assert caught.value.reason == lineage.LineageReason.PATH_INVALID
    assert swapped
    assert (public / "atp" / stale.name).read_bytes() == b"unrelated same-name bytes"
    assert (public / "atp" / "sentinel.bin").read_bytes() == b"unrelated sentinel"
    assert not (public / lineage.MANIFEST_FILENAME).exists()
    if scope == "data":
        assert not (source / lineage.MANIFEST_FILENAME).exists()
        assert not (source / lineage.ACCEPTANCE_FILENAME).exists()
    else:
        assert (source / lineage.MANIFEST_FILENAME).read_bytes() == (
            accepted.release.manifest_bytes
        )
        assert (source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
            accepted.receipt_bytes
        )


def test_web_publication_fails_if_stale_manifest_cannot_be_revoked(tmp_path):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _write_graph(source)
    (public / lineage.MANIFEST_FILENAME).mkdir(parents=True)
    with pytest.raises(lineage.ArtifactLineageError) as caught:
        lineage.publish_web_release(source, public)
    assert caught.value.reason == lineage.LineageReason.IO_ERROR


@pytest.mark.parametrize("unsafe_pointer", ["source", "destination"])
def test_strict_publication_never_follows_symlinked_validity_pointer(
    tmp_path, unsafe_pointer
):
    real_source = tmp_path / "real-source"
    real_destination = tmp_path / "real-public"
    accepted = _accepted(real_source)
    real_destination.mkdir()
    (real_destination / lineage.MANIFEST_FILENAME).write_bytes(b"external pointer")
    source = real_source
    destination = real_destination
    if unsafe_pointer == "source":
        source = tmp_path / "source-alias"
        source.symlink_to(real_source, target_is_directory=True)
    else:
        destination = tmp_path / "destination-alias"
        destination.symlink_to(real_destination, target_is_directory=True)
    with pytest.raises(lineage.ArtifactLineageError):
        if unsafe_pointer == "source":
            lineage.publish_data_release(
                source,
                destination,
                semantic_gate_passed=True,
                validator="predeploy-integrity-gate-v1",
            )
        else:
            lineage.publish_web_release(source, destination)
    assert (real_source / lineage.ACCEPTANCE_FILENAME).read_bytes() == (
        accepted.receipt_bytes
    )
    if unsafe_pointer == "destination":
        assert (real_destination / lineage.MANIFEST_FILENAME).read_bytes() == (
            b"external pointer"
        )


def test_successful_data_publication_accepts_and_exact_mirrors(tmp_path, capsys):
    source = tmp_path / "source"
    public = tmp_path / "public"
    _write_graph(source)
    candidate = _seal(source)

    assert lineage.main([
        "publish",
        "--scope", "data",
        "--semantic-gate-passed",
        "--validator", "predeploy-integrity-gate-v1",
        "--source", str(source),
        "--destination", str(public),
    ]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "issues": [],
        "releaseId": candidate.release_id,
        "schema": "artifact-lineage-publication-v1",
        "status": "published",
    }
    assert lineage.load_accepted_release(source).release_id == candidate.release_id
    assert lineage.validate_public_release(public).release_id == candidate.release_id


def test_data_cli_requires_explicit_green_gate_and_validator():
    with pytest.raises(SystemExit):
        lineage.main(["publish", "--scope", "data"])
    with pytest.raises(SystemExit):
        lineage.main([
            "publish", "--scope", "data", "--semantic-gate-passed"
        ])
    with pytest.raises(SystemExit):
        lineage.main([
            "publish", "--scope", "web", "--semantic-gate-passed",
        ])


def test_future_timestamps_and_non_uuid_predictor_identity_are_rejected(tmp_path):
    with pytest.raises(lineage.ArtifactLineageError):
        lineage.ArtifactProvenance(
            producer="pipeline",
            source_fingerprint=lineage.source_fingerprint("x"),
            predictor_artifact_id="not-a-uuid",
        )

    _write_graph(tmp_path)
    context = lineage.begin_release("full")
    manifest = lineage.merge_release_drafts(
        context, [_draft(tmp_path, tour, context) for tour in lineage.TOURS]
    )
    for noncanonical in (
        "2026-08-24 00:00:00Z",
        "20260824T000000Z",
        "2026-08-24T00:00:00.1234567Z",
    ):
        malformed = dict(manifest, createdAt=noncanonical)
        with pytest.raises(lineage.ArtifactLineageError, match="canonical UTC"):
            lineage.seal_release(tmp_path, malformed)

    _write_graph(tmp_path)
    context = lineage.begin_release(
        "full", created_at=datetime.now(UTC) + timedelta(hours=1)
    )
    drafts = [
        _draft(tmp_path, tour, context)
        for tour in lineage.TOURS
    ]
    with pytest.raises(lineage.ArtifactLineageError, match="future-dated"):
        lineage.seal_release(
            tmp_path, lineage.merge_release_drafts(context, drafts)
        )
