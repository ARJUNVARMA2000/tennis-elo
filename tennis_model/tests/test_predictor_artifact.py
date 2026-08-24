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


def test_genuine_legacy_pickle_gets_stable_derived_id(tmp_path):
    predictor = TennisPredictor(None, None, None, None, None, {}, tour="atp")
    del predictor.artifact_id
    path = tmp_path / "predictor.pkl"
    payload = pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL)
    path.write_bytes(payload)

    first = TennisPredictor.load("atp", path)
    second = TennisPredictor.load("atp", path)
    assert first.artifact_id == second.artifact_id
    assert uuid.UUID(first.artifact_id).version == 5
    assert "artifact_id" not in vars(pickle.loads(payload))
    with pytest.raises(PredictorArtifactError) as caught:
        validate_predictor_structure(first, "atp")
    assert caught.value.reason is PredictorArtifactReason.PREDICTOR_ID


def test_shared_structure_guard_accepts_only_explicit_valid_legacy_id(
    valid_artifact, tmp_path
):
    source, _ = valid_artifact
    predictor = pickle.loads(source.read_bytes())
    del predictor.artifact_id
    path = tmp_path / "predictor.pkl"
    path.write_bytes(pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL))
    loaded = TennisPredictor.load("atp", path)

    validate_predictor_structure(loaded, "atp", allow_legacy_id=True)
    with pytest.raises(PredictorArtifactError) as caught:
        validate_predictor_structure(loaded, "atp")
    assert caught.value.reason is PredictorArtifactReason.PREDICTOR_ID


def test_new_payload_without_envelope_is_not_legacy(tmp_path):
    predictor = TennisPredictor(None, None, None, None, None, {}, tour="atp")
    path = tmp_path / "predictor.pkl"
    path.write_bytes(pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL))

    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.ENVELOPE_MISSING_FOR_CURRENT_PAYLOAD


def test_legacy_preflight_rechecks_marker_after_payload_read(tmp_path, monkeypatch):
    predictor = TennisPredictor(None, None, None, None, None, {}, tour="atp")
    del predictor.artifact_id
    path = tmp_path / "predictor.pkl"
    path.write_bytes(pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL))
    original_read_payload = artifact._read_payload
    original_loads = artifact.pickle.loads
    calls = []

    def marker_appears_after_read(payload_path):
        payload = original_read_payload(payload_path)
        predictor_pending_path(path).write_bytes(b"writer-started")
        return payload

    monkeypatch.setattr(artifact, "_read_payload", marker_appears_after_read)
    monkeypatch.setattr(
        artifact.pickle,
        "loads",
        lambda payload: calls.append(payload) or original_loads(payload),
    )
    with pytest.raises(PredictorArtifactError) as caught:
        TennisPredictor.load("atp", path)
    assert caught.value.reason is PredictorArtifactReason.INCOMPLETE_WRITE
    assert calls == []


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

    # Before the marker replace, the untouched legacy artifact remains transitional.
    before_marker = tmp_path / "before-marker" / "predictor.pkl"
    before_marker.parent.mkdir()
    before_marker.write_bytes(legacy_bytes)
    with monkeypatch.context() as patch:
        patch.setattr(
            artifact,
            "_atomic_write",
            lambda path, payload: (_ for _ in ()).throw(OSError("marker crash")),
        )
        with pytest.raises(PredictorArtifactError) as caught:
            current.save(before_marker)
        assert caught.value.reason is PredictorArtifactReason.PUBLICATION_IO
    assert TennisPredictor.load("atp", before_marker).artifact_id

    # Once the marker is durable, crashes at the payload and envelope replaces both
    # reject before deserialization, whether the bytes are old or new.
    for fail_at in (2, 3):
        path = tmp_path / f"replace-{fail_at}" / "predictor.pkl"
        path.parent.mkdir()
        path.write_bytes(legacy_bytes)
        calls = []

        def crashing_write(target, payload, *, _calls=calls, _fail_at=fail_at):
            _calls.append(Path(target))
            if len(_calls) == _fail_at:
                raise OSError(f"replace {_fail_at} crash")
            original_atomic_write(target, payload)

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


def test_completed_pair_is_readable_if_pending_cleanup_crashes(
    valid_artifact, tmp_path, monkeypatch
):
    source, artifact_id = valid_artifact
    predictor = pickle.loads(source.read_bytes())
    path = tmp_path / "predictor.pkl"
    with monkeypatch.context() as patch:
        patch.setattr(
            artifact,
            "_remove_pending",
            lambda pending: (_ for _ in ()).throw(OSError("cleanup crash")),
        )
        with pytest.raises(PredictorArtifactError) as caught:
            predictor.save(path)
        assert caught.value.reason is PredictorArtifactReason.PUBLICATION_IO

    assert predictor_pending_path(path).exists()
    assert TennisPredictor.load("atp", path).artifact_id == artifact_id


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
    original_mkstemp = artifact.tempfile.mkstemp
    original_fsync = artifact.os.fsync
    temporary_names = []
    fsync_calls = []

    def recording_mkstemp(*args, **kwargs):
        descriptor, name = original_mkstemp(*args, **kwargs)
        temporary_names.append(name)
        return descriptor, name

    monkeypatch.setattr(artifact.tempfile, "mkstemp", recording_mkstemp)
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
    assert not any(Path(name).exists() for name in temporary_names)


def test_error_reason_is_typed_and_stable():
    error = PredictorArtifactError(PredictorArtifactReason.CONTRACT_MISMATCH, "detail")
    assert error.reason is PredictorArtifactReason.CONTRACT_MISMATCH
    assert error.code == "contract_mismatch"
    assert str(error) == "contract_mismatch: detail"
