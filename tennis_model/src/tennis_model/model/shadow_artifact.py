"""Bounded, atomic, explicitly pinned OFFLINE shadow artifact; never a production pickle."""

from __future__ import annotations

import hashlib
import json
import pickle
import struct
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import OUTPUT_DIR
from ..ratings.dynamic import STATE_SCHEMA, DynamicParams, DynamicState, PlayerGaussian
from . import artifact as a
from . import dynamic_research as dr
from .dynamic_shadow import SHADOW_SCHEMA, DynamicShadowPredictor, shadow_params

MAGIC = b"DEUCE-WTA-SHADOW\x00\x01"
FIELDS = frozenset({"dynamic_main", "dynamic_lower", "shadow_provenance"})
PROVENANCE_FIELDS = frozenset({
    "referenceFreeze", "candidateFreeze", "selection", "mainInput", "enrichedInput",
})
HEADER_FIELDS = frozenset({
    "schema", "artifactId", "trainedAt", "tour", "python", "libraries", "contract",
    "provenance", "states", "payloadBytes", "payloadSha256",
})


def _fail(reason, detail):
    raise a.PredictorArtifactError(reason, detail)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def checked_provenance(value):
    if (type(value) is not dict or set(value) != PROVENANCE_FIELDS
            or any(type(v) is not str or not a._SHA256_RE.fullmatch(v) for v in value.values())):
        _fail(a.PredictorArtifactReason.CONTRACT_MISMATCH, "explicit shadow provenance required")
    return value


def shadow_contract():
    package = Path(__file__).parent.parent
    sources = [(str(p.relative_to(package)), _digest(p.read_bytes()))
               for p in sorted(package.rglob("*")) if p.suffix in {".py", ".json"} and p.is_file()]
    return {
        "base": a.predictor_contract("wta"),
        "researchSchema": SHADOW_SCHEMA,
        "combinerSchema": dr.SCHEMA,
        "features": list(dr.COLUMNS),
        "signedFeatures": list(dr.SIGNED_COLUMNS),
        "dynamicStateSchema": STATE_SCHEMA,
        "dynamicParams": asdict(shadow_params()),
        "sourceSHA256": _digest(_canonical(sources)),
    }


def _state_receipt(state):
    return {"players": len(state.players), "lastDay": state.last_day,
            "sha256": _digest(_canonical(state.to_dict()))}


def validate_shadow_structure(predictor, *, expected_provenance):
    expected = checked_provenance(expected_provenance)
    a._validate_predictor(
        predictor, "wta", artifact_id=getattr(predictor, "artifact_id", None),
        trained_at=getattr(predictor, "trained_at", None), predictor_type=DynamicShadowPredictor,
        additional_fields=FIELDS, model_features=dr.COLUMNS,
    )
    if checked_provenance(predictor.shadow_provenance) != expected:
        _fail(a.PredictorArtifactReason.CONTRACT_MISMATCH, "shadow provenance differs")
    for label, elo in (("main", predictor.elo), ("lower", predictor.lower_elo)):
        state = getattr(predictor, "dynamic_" + label)
        try:
            if (type(state) is not DynamicState or set(vars(state)) != {"params", "players", "last_day"}
                    or type(state.params) is not DynamicParams or state.params != shadow_params()
                    or type(state.players) is not dict or set(state.players) != set(elo.n)):
                raise ValueError("dynamic state/parameters/player population differ")
            DynamicState.from_dict(state.to_dict())
            for name, player in state.players.items():
                if (type(player) is not PlayerGaussian
                        or set(vars(player)) != {"mean", "covariance", "day", "matches"}
                        or type(player.mean) is not np.ndarray or player.mean.dtype.kind != "f"
                        or type(player.covariance) is not np.ndarray or player.covariance.dtype.kind != "f"
                        or player.matches != elo.n[name]
                        or player.day != _day(elo.last_played[name])):
                    raise ValueError("dynamic player differs from selected history")
            if state.players:
                if (state.last_day != max(p.day for p in state.players.values())
                        or state.last_day > _day(elo.last_date)):
                    raise ValueError("dynamic cutoff differs from selected history")
            elif state.last_day is not None:
                raise ValueError("empty dynamic state has observations")
        except (AttributeError, TypeError, ValueError, KeyError, OverflowError) as exc:
            _fail(a.PredictorArtifactReason.STATE_INVALID, f"{label}: {exc}")


def _day(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("missing state cutoff")
    return int(stamp.to_datetime64().astype("datetime64[D]").astype(int))


def _path(path, trusted_root):
    path = a._absolute_without_symlink_resolution(path)
    if path.suffix != ".shadow":
        _fail(a.PredictorArtifactReason.PATH_INVALID, "explicit .shadow destination required")
    root = a._absolute_without_symlink_resolution(trusted_root)
    production = a._absolute_without_symlink_resolution(OUTPUT_DIR)
    if path.is_relative_to(production) or root.is_relative_to(production):
        _fail(a.PredictorArtifactReason.PATH_INVALID, "shadow artifacts cannot enter production output")
    a._trusted_root_for(path, root)
    return path, root


def save_shadow(predictor, path, *, trusted_root):
    path, root = _path(path, trusted_root)
    a._preflight_write_path(path, trusted_root=root)
    validate_shadow_structure(predictor, expected_provenance=predictor.shadow_provenance)
    payload = pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL)
    if not 0 < len(payload) <= a.MAX_PREDICTOR_BYTES:
        _fail(a.PredictorArtifactReason.PAYLOAD_TOO_LARGE, "shadow payload size")
    header = {
        "schema": SHADOW_SCHEMA, "artifactId": predictor.artifact_id,
        "trainedAt": predictor.trained_at, "tour": "wta", "python": a._python_identity(),
        "libraries": a._library_versions(), "contract": shadow_contract(),
        "provenance": predictor.shadow_provenance,
        "states": {key: _state_receipt(getattr(predictor, "dynamic_" + key)) for key in ("main", "lower")},
        "payloadBytes": len(payload), "payloadSha256": _digest(payload),
    }
    encoded = _canonical(header)
    if len(encoded) > a.MAX_ENVELOPE_BYTES:
        _fail(a.PredictorArtifactReason.ENVELOPE_TOO_LARGE, "shadow header size")
    a._atomic_write(path, MAGIC + struct.pack(">I", len(encoded)) + encoded + payload,
                    trusted_root=root)


def load_shadow(path, *, expected_provenance, trusted_root):
    expected = checked_provenance(expected_provenance)
    path, root = _path(path, trusted_root)
    content = a._read_bounded(
        path, len(MAGIC) + 4 + a.MAX_ENVELOPE_BYTES + a.MAX_PREDICTOR_BYTES,
        io_reason=a.PredictorArtifactReason.PAYLOAD_IO,
        too_large_reason=a.PredictorArtifactReason.PAYLOAD_TOO_LARGE, trusted_root=root,
    )
    prefix = len(MAGIC) + 4
    if len(content) < prefix or content[:len(MAGIC)] != MAGIC:
        _fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "not a shadow artifact")
    size = struct.unpack(">I", content[len(MAGIC):prefix])[0]
    if not 0 < size <= a.MAX_ENVELOPE_BYTES or prefix + size >= len(content):
        _fail(a.PredictorArtifactReason.ENVELOPE_TOO_LARGE, "invalid shadow header boundary")
    try:
        header = json.loads(content[prefix:prefix + size], object_pairs_hook=a._reject_duplicate_keys,
                            parse_constant=a._reject_json_constant)
    except (UnicodeDecodeError, ValueError) as exc:
        _fail(a.PredictorArtifactReason.ENVELOPE_MALFORMED, str(exc))
    if (type(header) is not dict or set(header) != HEADER_FIELDS
            or header["schema"] != SHADOW_SCHEMA or header["tour"] != "wta"
            or not a._valid_artifact_id(header["artifactId"])
            or not a._valid_timestamp(header["trainedAt"])):
        _fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "invalid shadow header")
    if (_canonical(header["python"]) != _canonical(a._python_identity())
            or _canonical(header["libraries"]) != _canonical(a._library_versions())):
        _fail(a.PredictorArtifactReason.RUNTIME_MISMATCH, "shadow runtime differs")
    if (_canonical(header["contract"]) != _canonical(shadow_contract())
            or checked_provenance(header["provenance"]) != expected):
        _fail(a.PredictorArtifactReason.CONTRACT_MISMATCH, "shadow contract differs")
    states = header["states"]
    if type(states) is not dict or set(states) != {"main", "lower"}:
        _fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "shadow state receipt absent")
    for receipt in states.values():
        if (type(receipt) is not dict or set(receipt) != {"players", "lastDay", "sha256"}
                or type(receipt["players"]) is not int or receipt["players"] < 0
                or (receipt["lastDay"] is not None and type(receipt["lastDay"]) is not int)
                or type(receipt["sha256"]) is not str or not a._SHA256_RE.fullmatch(receipt["sha256"])):
            _fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "invalid shadow state receipt")
    payload = content[prefix + size:]
    if (type(header["payloadBytes"]) is not int or not 0 < header["payloadBytes"] <= a.MAX_PREDICTOR_BYTES
            or header["payloadBytes"] != len(payload)):
        _fail(a.PredictorArtifactReason.PAYLOAD_SIZE_MISMATCH, "shadow payload length differs")
    if type(header["payloadSha256"]) is not str or header["payloadSha256"] != _digest(payload):
        _fail(a.PredictorArtifactReason.PAYLOAD_CHECKSUM_MISMATCH, "shadow payload digest differs")
    predictor = a._deserialize(payload)
    validate_shadow_structure(predictor, expected_provenance=expected)
    if predictor.artifact_id != header["artifactId"] or predictor.trained_at != header["trainedAt"]:
        _fail(a.PredictorArtifactReason.PREDICTOR_ID, "shadow generation differs")
    if states != {key: _state_receipt(getattr(predictor, "dynamic_" + key)) for key in ("main", "lower")}:
        _fail(a.PredictorArtifactReason.STATE_INVALID, "shadow state receipt differs")
    return predictor
