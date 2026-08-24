"""Strict predictor-envelope checks with a small real fitted model."""

from __future__ import annotations

import hashlib
import json
import pickle
import shutil
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from tennis_model.config import WTA_DUAL_STATE_GATE_THRESHOLD
from tennis_model.model import artifact
from tennis_model.model.artifact import (
    PREDICTOR_ENVELOPE_SCHEMA,
    PREDICTOR_PENDING_SCHEMA,
    PredictorArtifactError,
    PredictorArtifactReason,
    predictor_contract,
    predictor_envelope_path,
    predictor_pending_path,
    validate_predictor_artifact_identity,
    validate_predictor_structure,
)
from tennis_model.model.features import FEATURES, H2HState, feat_params_for
from tennis_model.model.predict import TennisPredictor
from tennis_model.model.train import (
    BaggedClassifier,
    PlattCalibrator,
    production_xgb_params,
)
from tennis_model.points.serve_return import ServeReturnState, sr_params_for
from tennis_model.ratings.build import RatingState
from tennis_model.ratings.elo import params_for
from xgboost import XGBClassifier


def _valid_predictor(tour: str = "atp") -> TennisPredictor:
    rng = np.random.default_rng(41)
    train_x = pd.DataFrame(
        rng.normal(size=(128, len(FEATURES))), columns=FEATURES
    )
    train_y = rng.integers(0, 2, len(train_x))
    cal_x = pd.DataFrame(
        rng.normal(size=(128, len(FEATURES))), columns=FEATURES
    )
    cal_y = rng.integers(0, 2, len(cal_x))
    members = []
    for index in range(5):
        member = XGBClassifier(**production_xgb_params(tour, bag_index=index))
        member.fit(train_x, train_y, eval_set=[(cal_x, cal_y)], verbose=False)
        members.append(member)
    calibrator = PlattCalibrator().fit(
        np.linspace(0.05, 0.95, len(cal_y)), cal_y
    )
    dual = tour == "wta"
    return TennisPredictor(
        BaggedClassifier(members),
        calibrator,
        RatingState(params=params_for(tour)),
        ServeReturnState(params=sr_params_for(tour)),
        H2HState({}),
        {},
        tour=tour,
        fp=feat_params_for(tour),
        lower_elo=RatingState(params=params_for(tour)) if dual else None,
        lower_srv=ServeReturnState(params=sr_params_for(tour)) if dual else None,
        lower_ctx=H2HState({}) if dual else None,
        dual_state_threshold=WTA_DUAL_STATE_GATE_THRESHOLD if dual else None,
    )


@pytest.fixture(scope="module")
def valid_artifact(tmp_path_factory):
    directory = tmp_path_factory.mktemp("predictor-artifact")
    path = directory / "predictor.pkl"
    predictor = _valid_predictor()
    predictor.save(path)
    return path, predictor.artifact_id


def _copy_artifact(source: Path, directory: Path) -> Path:
    path = directory / "predictor.pkl"
    shutil.copyfile(source, path)
    shutil.copyfile(predictor_envelope_path(source), predictor_envelope_path(path))
    return path


def _write_envelope(path: Path, envelope: dict) -> None:
    predictor_envelope_path(path).write_text(
        json.dumps(envelope, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _resign_mutated_payload(path: Path, mutate) -> None:
    predictor = pickle.loads(path.read_bytes())
    mutate(predictor)
    payload = pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL)
    path.write_bytes(payload)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["payloadBytes"] = len(payload)
    envelope["payloadSha256"] = hashlib.sha256(payload).hexdigest()
    _write_envelope(path, envelope)


def _pending_from_envelope(path: Path) -> dict:
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    return {
        "schema": PREDICTOR_PENDING_SCHEMA,
        **{
            key: envelope[key]
            for key in (
                "artifactId",
                "tour",
                "trainedAt",
                "payloadBytes",
                "payloadSha256",
            )
        },
    }


def test_roundtrip_keeps_plain_pickle_and_stable_generation_id(valid_artifact, tmp_path):
    source, artifact_id = valid_artifact
    path = _copy_artifact(source, tmp_path)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))

    assert envelope["schema"] == PREDICTOR_ENVELOPE_SCHEMA
    assert envelope["artifactId"] == artifact_id
    assert envelope["payloadBytes"] == path.stat().st_size
    assert envelope["payloadSha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert envelope["contract"] == predictor_contract("atp")
    contract = envelope["contract"]
    assert contract["features"] == list(FEATURES)
    assert (
        contract["featureParams"]["fatigue_window_days"]
        == feat_params_for("atp").fatigue_window_days
    )
    assert "rating_scale" in contract["eloParams"]
    assert "serve_shrinkage_points" in contract["serveReturnParams"]
    assert contract["xgboost"]["params"] == production_xgb_params("atp")
    assert contract["population"]["matchPopulationVersion"] >= 1
    assert type(contract["population"]["playerAliases"]) is list
    assert contract["inference"] == {
        "schemaVersion": 3,
        "dualStateGateThreshold": None,
    }
    assert contract["classes"]["combiner"].endswith(".BaggedClassifier")
    assert contract["classes"]["calibrator"].endswith(".PlattCalibrator")
    assert contract["bag"]["size"] == 5
    assert contract["bag"]["memberRandomStates"] == [0, 1, 2, 3, 4]
    assert contract["calibrator"]["features"] == 1
    assert contract["calibrator"]["classes"] == [0, 1]
    assert set(envelope["libraries"]) == {
        "numpy", "pandas", "scikit-learn", "xgboost"
    }

    # This is the rollback contract: the payload itself is still directly readable.
    old_reader = pickle.loads(path.read_bytes())
    loaded = TennisPredictor.load("atp", path)
    assert old_reader.artifact_id == loaded.artifact_id == artifact_id
    assert loaded.trained_at == envelope["trainedAt"]
    validate_predictor_structure(loaded, "atp")
    assert not predictor_pending_path(path).exists()

    # Saving the same trained generation does not silently mint a new identity.
    loaded.save(path)
    saved_again = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    assert loaded.artifact_id == saved_again["artifactId"] == artifact_id


def test_wta_dual_state_fitted_artifact_roundtrip(tmp_path):
    path = tmp_path / "predictor.pkl"
    predictor = _valid_predictor("wta")
    predictor.save(path)

    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    loaded = TennisPredictor.load("wta", path)

    assert envelope["tour"] == "wta"
    assert (
        envelope["contract"]["inference"]["dualStateGateThreshold"]
        == WTA_DUAL_STATE_GATE_THRESHOLD
    )
    assert loaded.dual_state_threshold == WTA_DUAL_STATE_GATE_THRESHOLD
    assert loaded._has_lower_state
    validate_predictor_structure(loaded, "wta")


@pytest.mark.parametrize("legacy", [True, False])
def test_missing_envelope_rejects_before_payload_read_or_unpickle(
    tmp_path, monkeypatch, legacy
):
    predictor = TennisPredictor(None, None, None, None, None, {}, tour="atp")
    if legacy:
        del predictor.artifact_id
    path = tmp_path / "predictor.pkl"
    path.write_bytes(pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL))
    payload_reads = []
    unpickle_calls = []
    monkeypatch.setattr(
        artifact, "_read_payload", lambda *args, **kwargs: payload_reads.append(args)
    )
    monkeypatch.setattr(
        artifact.pickle, "loads", lambda payload: unpickle_calls.append(payload)
    )

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.ENVELOPE_MISSING_FOR_CURRENT_PAYLOAD
    assert payload_reads == []
    assert unpickle_calls == []


def test_shared_structure_guard_accepts_uuid4_only(valid_artifact):
    source, _ = valid_artifact
    predictor = pickle.loads(source.read_bytes())
    predictor.artifact_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "legacy-predictor"))

    with pytest.raises(PredictorArtifactError) as caught:
        validate_predictor_structure(predictor, "atp")
    assert caught.value.reason is PredictorArtifactReason.PREDICTOR_ID


def test_every_invalid_present_envelope_stops_before_unpickle(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    original_loads = artifact.pickle.loads
    calls = []

    def forbidden(payload):
        calls.append(payload)
        return original_loads(payload)

    monkeypatch.setattr(artifact.pickle, "loads", forbidden)
    cases = []

    malformed = tmp_path / "malformed"
    malformed.mkdir()
    path = _copy_artifact(source, malformed)
    predictor_envelope_path(path).write_bytes(b"not-json")
    cases.append((path, PredictorArtifactReason.ENVELOPE_MALFORMED))

    duplicate = tmp_path / "duplicate"
    duplicate.mkdir()
    path = _copy_artifact(source, duplicate)
    raw = predictor_envelope_path(path).read_text(encoding="utf-8")
    predictor_envelope_path(path).write_text(
        raw.replace('"schema":', '"schema":"duplicate","schema":', 1),
        encoding="utf-8",
    )
    cases.append((path, PredictorArtifactReason.ENVELOPE_MALFORMED))

    unknown = tmp_path / "unknown"
    unknown.mkdir()
    path = _copy_artifact(source, unknown)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["unexpected"] = True
    _write_envelope(path, envelope)
    cases.append((path, PredictorArtifactReason.ENVELOPE_SCHEMA))

    runtime = tmp_path / "runtime"
    runtime.mkdir()
    path = _copy_artifact(source, runtime)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["python"]["minor"] += 1
    _write_envelope(path, envelope)
    cases.append((path, PredictorArtifactReason.RUNTIME_MISMATCH))

    library = tmp_path / "library"
    library.mkdir()
    path = _copy_artifact(source, library)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["libraries"]["scikit-learn"] = "0.0.invalid"
    _write_envelope(path, envelope)
    cases.append((path, PredictorArtifactReason.RUNTIME_MISMATCH))

    contract = tmp_path / "contract"
    contract.mkdir()
    path = _copy_artifact(source, contract)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["contract"]["features"][0] = "wrong"
    _write_envelope(path, envelope)
    cases.append((path, PredictorArtifactReason.CONTRACT_MISMATCH))

    digest = tmp_path / "digest"
    digest.mkdir()
    path = _copy_artifact(source, digest)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["payloadSha256"] = "0" * 64
    _write_envelope(path, envelope)
    cases.append((path, PredictorArtifactReason.PAYLOAD_CHECKSUM_MISMATCH))

    size = tmp_path / "size"
    size.mkdir()
    path = _copy_artifact(source, size)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["payloadBytes"] += 1
    _write_envelope(path, envelope)
    cases.append((path, PredictorArtifactReason.PAYLOAD_SIZE_MISMATCH))

    for path, reason in cases:
        with pytest.raises(PredictorArtifactError) as caught:
            TennisPredictor.load("atp", path)
        assert caught.value.reason is reason
    assert calls == []


def test_present_dangling_envelope_never_falls_back(tmp_path, monkeypatch):
    legacy = TennisPredictor(None, None, None, None, None, {}, tour="atp")
    del legacy.artifact_id
    path = tmp_path / "predictor.pkl"
    path.write_bytes(pickle.dumps(legacy, protocol=pickle.HIGHEST_PROTOCOL))
    predictor_envelope_path(path).symlink_to(tmp_path / "missing-target")
    calls = []
    monkeypatch.setattr(artifact.pickle, "loads", lambda payload: calls.append(payload))

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.ENVELOPE_IO
    assert calls == []


def test_valid_external_envelope_symlink_is_rejected(valid_artifact, tmp_path):
    source, _ = valid_artifact
    path = _copy_artifact(source, tmp_path)
    envelope_path = predictor_envelope_path(path)
    external = tmp_path.parent / f"{tmp_path.name}-external-envelope"
    external.write_bytes(envelope_path.read_bytes())
    envelope_path.unlink()
    envelope_path.symlink_to(external)

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.ENVELOPE_IO
    with pytest.raises(PredictorArtifactError) as identity_error:
        artifact.validate_predictor_artifact_identity(path, "atp")
    assert identity_error.value.reason is PredictorArtifactReason.ENVELOPE_IO


@pytest.mark.parametrize("link_is_immediate_parent", [True, False])
def test_symlinked_parent_component_cannot_read_outside_artifact_root(
    valid_artifact, tmp_path, monkeypatch, link_is_immediate_parent
):
    source, _ = valid_artifact
    outside = tmp_path / "outside"
    outside.mkdir()
    _copy_artifact(source, outside)
    logical = tmp_path / "logical"
    logical.mkdir()
    if link_is_immediate_parent:
        parent = logical / "atp"
        parent.symlink_to(outside, target_is_directory=True)
    else:
        outside_parent = tmp_path / "outside-parent"
        outside_parent.mkdir()
        outside_tour = outside_parent / "atp"
        outside_tour.mkdir()
        _copy_artifact(source, outside_tour)
        jump = logical / "jump"
        jump.symlink_to(outside_parent, target_is_directory=True)
        parent = jump / "atp"
    path = parent / "predictor.pkl"
    calls = []
    monkeypatch.setattr(artifact.pickle, "loads", lambda payload: calls.append(payload))

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.PATH_INVALID
    with pytest.raises(PredictorArtifactError) as identity_error:
        validate_predictor_artifact_identity(path, "atp")
    assert identity_error.value.reason is PredictorArtifactReason.PATH_INVALID
    assert calls == []


def test_symlinked_parent_cannot_write_outside_artifact_root(
    valid_artifact, tmp_path
):
    source, _ = valid_artifact
    outside = tmp_path / "outside"
    outside.mkdir()
    external_path = _copy_artifact(source, outside)
    before = {
        candidate.name: candidate.read_bytes()
        for candidate in outside.iterdir()
        if candidate.is_file()
    }
    logical_parent = tmp_path / "logical-atp"
    logical_parent.symlink_to(outside, target_is_directory=True)
    predictor = pickle.loads(source.read_bytes())
    predictor.artifact_id = str(uuid.uuid4())

    with pytest.raises(PredictorArtifactError) as caught:
        predictor.save(logical_parent / "predictor.pkl")
    assert caught.value.reason is PredictorArtifactReason.PATH_INVALID
    assert external_path.exists()
    assert before == {
        candidate.name: candidate.read_bytes()
        for candidate in outside.iterdir()
        if candidate.is_file()
    }
    assert not any(candidate.name.endswith(".tmp") for candidate in outside.iterdir())


def test_in_root_cross_tour_alias_is_not_a_trusted_path(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    output = tmp_path / "output"
    atp = output / "atp"
    atp.mkdir(parents=True)
    real_path = _copy_artifact(source, atp)
    before = {
        candidate.name: candidate.read_bytes()
        for candidate in atp.iterdir()
        if candidate.is_file()
    }
    alias = output / "wta"
    alias.symlink_to(atp, target_is_directory=True)
    path = alias / "predictor.pkl"
    predictor = pickle.loads(source.read_bytes())
    unpickle_calls = []
    monkeypatch.setattr(artifact, "OUTPUT_DIR", output)
    monkeypatch.setattr(
        artifact.pickle, "loads", lambda payload: unpickle_calls.append(payload)
    )

    with pytest.raises(PredictorArtifactError) as read_error:
        TennisPredictor.load("wta", path)
    assert read_error.value.reason is PredictorArtifactReason.PATH_INVALID
    with pytest.raises(PredictorArtifactError) as write_error:
        predictor.save(path)
    assert write_error.value.reason is PredictorArtifactReason.PATH_INVALID
    assert unpickle_calls == []
    assert real_path.exists()
    assert before == {
        candidate.name: candidate.read_bytes()
        for candidate in atp.iterdir()
        if candidate.is_file()
    }


def test_lstat_fstat_fallback_rejects_parent_and_leaf_symlinks_before_read(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    outside = tmp_path / "outside-read"
    outside.mkdir()
    external_path = _copy_artifact(source, outside)

    parent_link = tmp_path / "parent-link-read"
    parent_link.symlink_to(outside, target_is_directory=True)
    parent_path = parent_link / "predictor.pkl"

    leaf_parent = tmp_path / "leaf-read"
    leaf_parent.mkdir()
    leaf_path = leaf_parent / "predictor.pkl"
    leaf_path.symlink_to(external_path)
    shutil.copyfile(
        predictor_envelope_path(source), predictor_envelope_path(leaf_path)
    )
    unpickle_calls = []
    monkeypatch.setattr(artifact, "_nofollow_flag", lambda: 0)
    monkeypatch.setattr(
        artifact.pickle, "loads", lambda payload: unpickle_calls.append(payload)
    )

    with pytest.raises(PredictorArtifactError) as parent_error:
        TennisPredictor.load("atp", parent_path)
    assert parent_error.value.reason is PredictorArtifactReason.PATH_INVALID
    with pytest.raises(PredictorArtifactError) as leaf_error:
        TennisPredictor.load("atp", leaf_path)
    assert leaf_error.value.reason is PredictorArtifactReason.PAYLOAD_IO
    assert unpickle_calls == []


def test_lstat_fstat_fallback_rejects_parent_and_leaf_symlinks_before_write(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    predictor = pickle.loads(source.read_bytes())
    outside = tmp_path / "outside-write"
    outside.mkdir()
    _copy_artifact(source, outside)
    outside_before = {
        candidate.name: candidate.read_bytes()
        for candidate in outside.iterdir()
        if candidate.is_file()
    }
    parent_link = tmp_path / "parent-link-write"
    parent_link.symlink_to(outside, target_is_directory=True)

    leaf_parent = tmp_path / "leaf-write"
    leaf_parent.mkdir()
    external_leaf = tmp_path / "external-leaf.pkl"
    external_leaf.write_bytes(b"must remain unchanged")
    leaf_path = leaf_parent / "predictor.pkl"
    leaf_path.symlink_to(external_leaf)
    atomic_calls = []
    monkeypatch.setattr(artifact, "_nofollow_flag", lambda: 0)
    monkeypatch.setattr(
        artifact,
        "_atomic_write",
        lambda *args, **kwargs: atomic_calls.append((args, kwargs)),
    )

    with pytest.raises(PredictorArtifactError) as parent_error:
        predictor.save(parent_link / "predictor.pkl")
    assert parent_error.value.reason is PredictorArtifactReason.PATH_INVALID
    with pytest.raises(PredictorArtifactError) as leaf_error:
        predictor.save(leaf_path)
    assert leaf_error.value.reason is PredictorArtifactReason.PATH_INVALID
    assert atomic_calls == []
    assert external_leaf.read_bytes() == b"must remain unchanged"
    assert leaf_path.is_symlink()
    assert not predictor_pending_path(leaf_path).exists()
    assert not predictor_envelope_path(leaf_path).exists()
    assert outside_before == {
        candidate.name: candidate.read_bytes()
        for candidate in outside.iterdir()
        if candidate.is_file()
    }


def test_explicit_trusted_root_blocks_outside_reads_and_writes(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    path = _copy_artifact(source, outside)
    before = {
        candidate.name: candidate.read_bytes()
        for candidate in outside.iterdir()
        if candidate.is_file()
    }
    predictor = pickle.loads(source.read_bytes())
    predictor.artifact_id = str(uuid.uuid4())
    calls = []
    monkeypatch.setattr(artifact.pickle, "loads", lambda payload: calls.append(payload))

    with pytest.raises(PredictorArtifactError) as read_error:
        artifact.load_predictor_artifact(path, "atp", trusted_root=trusted)
    assert read_error.value.reason is PredictorArtifactReason.PATH_INVALID
    assert calls == []

    with pytest.raises(PredictorArtifactError) as write_error:
        artifact.save_predictor_artifact(predictor, path, trusted_root=trusted)
    assert write_error.value.reason is PredictorArtifactReason.PATH_INVALID
    assert before == {
        candidate.name: candidate.read_bytes()
        for candidate in outside.iterdir()
        if candidate.is_file()
    }


def test_checked_bytes_are_the_bytes_deserialized(valid_artifact, tmp_path, monkeypatch):
    source, artifact_id = valid_artifact
    path = _copy_artifact(source, tmp_path)
    original_loads = artifact.pickle.loads

    def replace_after_preflight(payload):
        path.write_bytes(b"changed after checksum")
        return original_loads(payload)

    monkeypatch.setattr(artifact.pickle, "loads", replace_after_preflight)
    loaded = TennisPredictor.load("atp", path)
    assert loaded.artifact_id == artifact_id


def test_preunpickle_identity_helper_binds_completed_pair(
    valid_artifact, tmp_path, monkeypatch
):
    source, artifact_id = valid_artifact
    path = _copy_artifact(source, tmp_path)
    calls = []
    monkeypatch.setattr(artifact.pickle, "loads", lambda payload: calls.append(payload))

    identity = validate_predictor_artifact_identity(path, "atp")
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    assert identity == {
        key: envelope[key]
        for key in ("artifactId", "tour", "trainedAt", "payloadBytes", "payloadSha256")
    }
    assert identity["artifactId"] == artifact_id
    assert calls == []

    predictor_pending_path(path).write_text(
        json.dumps(_pending_from_envelope(path)), encoding="utf-8"
    )
    with pytest.raises(PredictorArtifactError) as caught:
        validate_predictor_artifact_identity(path, "atp")
    assert caught.value.reason is PredictorArtifactReason.INCOMPLETE_WRITE
    assert calls == []


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda predictor: setattr(
                predictor.clf.clfs[3].get_booster(),
                "feature_names",
                list(reversed(FEATURES)),
            ),
            PredictorArtifactReason.BOOSTER_INVALID,
        ),
        (
            lambda predictor: predictor.clf.clfs[2].set_params(max_depth=99),
            PredictorArtifactReason.BOOSTER_INVALID,
        ),
        (
            # An otherwise-implicit XGBoost default is still part of the exact
            # resolved wrapper contract, not merely the tuned parameter subset.
            lambda predictor: predictor.clf.clfs[2].set_params(max_leaves=99),
            PredictorArtifactReason.BOOSTER_INVALID,
        ),
        (
            lambda predictor: predictor.clf.clfs.__setitem__(4, object()),
            PredictorArtifactReason.BOOSTER_INVALID,
        ),
        (
            lambda predictor: predictor.clf.clfs.__setitem__(
                4, XGBClassifier(**production_xgb_params("atp", bag_index=4))
            ),
            PredictorArtifactReason.BOOSTER_INVALID,
        ),
        (
            lambda predictor: setattr(predictor.iso.lr, "coef_", np.zeros((1, 2))),
            PredictorArtifactReason.CALIBRATOR_INVALID,
        ),
        (
            lambda predictor: setattr(predictor, "unexpected", True),
            PredictorArtifactReason.PREDICTOR_FIELDS,
        ),
        (
            lambda predictor: setattr(predictor, "ctx", {}),
            PredictorArtifactReason.STATE_INVALID,
        ),
        (
            lambda predictor: setattr(predictor, "fp", feat_params_for("wta")),
            PredictorArtifactReason.STATE_INVALID,
        ),
        (
            lambda predictor: setattr(
                predictor,
                "player_aliases",
                predictor.player_aliases + (("Alias Drift", "Player Drift"),),
            ),
            PredictorArtifactReason.PREDICTOR_FIELDS,
        ),
        (
            lambda predictor: vars(predictor).pop("player_aliases"),
            PredictorArtifactReason.PREDICTOR_FIELDS,
        ),
        (
            lambda predictor: setattr(
                predictor,
                "match_population_version",
                predictor.match_population_version + 1,
            ),
            PredictorArtifactReason.PREDICTOR_FIELDS,
        ),
        (
            lambda predictor: setattr(
                predictor,
                "inference_schema_version",
                predictor.inference_schema_version + 1,
            ),
            PredictorArtifactReason.PREDICTOR_FIELDS,
        ),
        (
            lambda predictor: setattr(predictor, "dual_state_threshold", 32),
            PredictorArtifactReason.PREDICTOR_FIELDS,
        ),
        (
            lambda predictor: setattr(
                predictor, "lower_elo", RatingState(params=params_for("atp"))
            ),
            PredictorArtifactReason.STATE_INVALID,
        ),
        (
            lambda predictor: setattr(predictor, "artifact_id", str(uuid.uuid4())),
            PredictorArtifactReason.PREDICTOR_ID,
        ),
        (
            lambda predictor: setattr(predictor, "trained_at", "2000-01-01T00:00:00Z"),
            PredictorArtifactReason.PREDICTOR_TIME,
        ),
        (
            lambda predictor: setattr(predictor, "tour", "wta"),
            PredictorArtifactReason.TOUR_MISMATCH,
        ),
    ],
)
def test_resigned_payload_still_fails_closed_postload(
    valid_artifact, tmp_path, mutate, reason
):
    source, _ = valid_artifact
    path = _copy_artifact(source, tmp_path)
    _resign_mutated_payload(path, mutate)

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is reason


def test_pending_marker_closes_each_atomic_crash_window(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    current = pickle.loads(source.read_bytes())
    legacy = pickle.loads(source.read_bytes())
    del legacy.artifact_id
    legacy_bytes = pickle.dumps(legacy, protocol=pickle.HIGHEST_PROTOCOL)
    original_atomic_write = artifact._atomic_write
    original_loads = artifact.pickle.loads

    # Before the marker replace, the untouched legacy artifact remains unpaired and
    # therefore cannot be read by the strict loader.
    before_marker = tmp_path / "before-marker" / "predictor.pkl"
    before_marker.parent.mkdir()
    before_marker.write_bytes(legacy_bytes)
    with monkeypatch.context() as patch:
        patch.setattr(
            artifact,
            "_atomic_write",
            lambda path, payload, **kwargs: (
                _ for _ in ()
            ).throw(OSError("marker crash")),
        )
        with pytest.raises(PredictorArtifactError) as caught:
            current.save(before_marker)
        assert caught.value.reason is PredictorArtifactReason.PUBLICATION_IO
    unpickle_calls = []
    with monkeypatch.context() as patch:
        patch.setattr(
            artifact.pickle,
            "loads",
            lambda payload: unpickle_calls.append(payload),
        )
        with pytest.raises(PredictorArtifactError) as caught:
            TennisPredictor.load("atp", before_marker)
    assert caught.value.reason is PredictorArtifactReason.ENVELOPE_MISSING_FOR_CURRENT_PAYLOAD
    assert unpickle_calls == []

    # Once the marker is durable, crashes at the payload and envelope replaces both
    # reject before deserialization, whether the bytes are old or new.
    for fail_at in (2, 3):
        path = tmp_path / f"replace-{fail_at}" / "predictor.pkl"
        path.parent.mkdir()
        path.write_bytes(legacy_bytes)
        calls = []

        def crashing_write(
            target, payload, *, _calls=calls, _fail_at=fail_at, **kwargs
        ):
            _calls.append(Path(target))
            if len(_calls) == _fail_at:
                raise OSError(f"replace {_fail_at} crash")
            original_atomic_write(target, payload, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(artifact, "_atomic_write", crashing_write)
            with pytest.raises(PredictorArtifactError) as caught:
                current.save(path)
            assert caught.value.reason is PredictorArtifactReason.PUBLICATION_IO
        unpickle_calls = []
        with monkeypatch.context() as patch:
            patch.setattr(
                artifact.pickle,
                "loads",
                lambda payload, _calls=unpickle_calls: (
                    _calls.append(payload) or original_loads(payload)
                ),
            )
            with pytest.raises(PredictorArtifactError) as caught:
                TennisPredictor.load("atp", path)
        assert caught.value.reason is PredictorArtifactReason.INCOMPLETE_WRITE
        assert unpickle_calls == []
        assert calls[0] == predictor_pending_path(path)
        assert calls[1] == path
        if fail_at == 3:
            assert calls[2] == predictor_envelope_path(path)


def test_completed_pair_recovers_pending_cleanup_crash_on_load(
    valid_artifact, tmp_path, monkeypatch
):
    source, artifact_id = valid_artifact
    predictor = pickle.loads(source.read_bytes())
    path = tmp_path / "predictor.pkl"
    with monkeypatch.context() as patch:
        patch.setattr(
            artifact,
            "_remove_pending",
            lambda pending, **kwargs: (
                _ for _ in ()
            ).throw(OSError("cleanup crash")),
        )
        with pytest.raises(PredictorArtifactError) as caught:
            predictor.save(path)
        assert caught.value.reason is PredictorArtifactReason.PUBLICATION_IO

    assert predictor_pending_path(path).exists()
    assert TennisPredictor.load("atp", path).artifact_id == artifact_id
    assert not predictor_pending_path(path).exists()
    assert validate_predictor_artifact_identity(path, "atp")["artifactId"] == artifact_id


def test_pending_recovery_cleanup_failure_is_a_typed_load_rejection(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    path = _copy_artifact(source, tmp_path)
    pending_path = predictor_pending_path(path)
    pending_path.write_text(
        json.dumps(_pending_from_envelope(path)), encoding="utf-8"
    )
    monkeypatch.setattr(
        artifact,
        "_remove_pending",
        lambda pending, **kwargs: (
            _ for _ in ()
        ).throw(OSError("cleanup still unavailable")),
    )

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.PENDING_IO
    assert pending_path.exists()


def test_pending_without_envelope_rejects_before_unpickle(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    path = _copy_artifact(source, tmp_path)
    pending = _pending_from_envelope(path)
    predictor_pending_path(path).write_text(json.dumps(pending), encoding="utf-8")
    predictor_envelope_path(path).unlink()
    calls = []
    monkeypatch.setattr(artifact.pickle, "loads", lambda payload: calls.append(payload))

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.INCOMPLETE_WRITE
    assert calls == []


def test_future_trained_at_is_rejected_before_unpickle(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    future = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    calls = []
    monkeypatch.setattr(artifact.pickle, "loads", lambda payload: calls.append(payload))

    envelope_dir = tmp_path / "envelope"
    envelope_dir.mkdir()
    path = _copy_artifact(source, envelope_dir)
    envelope = json.loads(predictor_envelope_path(path).read_text(encoding="utf-8"))
    envelope["trainedAt"] = future
    _write_envelope(path, envelope)
    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.ENVELOPE_SCHEMA

    pending_dir = tmp_path / "pending"
    pending_dir.mkdir()
    path = _copy_artifact(source, pending_dir)
    pending = _pending_from_envelope(path)
    pending["trainedAt"] = future
    predictor_pending_path(path).write_text(json.dumps(pending), encoding="utf-8")
    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.PENDING_MALFORMED
    assert calls == []


def test_envelope_read_is_bounded_before_unpickle(
    valid_artifact, tmp_path, monkeypatch
):
    source, _ = valid_artifact
    path = _copy_artifact(source, tmp_path)
    monkeypatch.setattr(artifact, "MAX_ENVELOPE_BYTES", 16)
    calls = []
    monkeypatch.setattr(artifact.pickle, "loads", lambda payload: calls.append(payload))

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.ENVELOPE_TOO_LARGE
    assert calls == []


def test_atomic_writer_uses_unique_temps_and_fsyncs(valid_artifact, tmp_path, monkeypatch):
    source, _ = valid_artifact
    predictor = pickle.loads(source.read_bytes())
    path = tmp_path / "predictor.pkl"
    original_temporary_name = artifact._temporary_name
    original_fsync = artifact.os.fsync
    temporary_names = []
    fsync_calls = []

    def recording_temporary_name(target_name):
        name = original_temporary_name(target_name)
        temporary_names.append(name)
        return name

    monkeypatch.setattr(artifact, "_temporary_name", recording_temporary_name)
    monkeypatch.setattr(
        artifact.os,
        "fsync",
        lambda descriptor: fsync_calls.append(descriptor) or original_fsync(descriptor),
    )
    predictor.save(path)

    assert len(temporary_names) == 3
    assert len(set(temporary_names)) == 3
    assert all(name.endswith(".tmp") for name in temporary_names)
    assert len(fsync_calls) >= 7  # each file + directory, then pending-unlink directory
    assert not any((tmp_path / name).exists() for name in temporary_names)


def test_error_reason_is_typed_and_stable():
    error = PredictorArtifactError(PredictorArtifactReason.CONTRACT_MISMATCH, "detail")
    assert error.reason is PredictorArtifactReason.CONTRACT_MISMATCH
    assert error.code == "contract_mismatch"
    assert str(error) == "contract_mismatch: detail"
