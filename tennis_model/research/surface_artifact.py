"""Bounded, pinned surface-candidate artifact; production readers cannot load it."""

from __future__ import annotations

import hashlib
import json
import pickle
import struct
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
from historical_signals import SignalState
from surface_candidate import COLUMNS, FEATURE, SCHEMA, SurfaceCandidatePredictor
from tennis_model.config import OUTPUT_DIR
from tennis_model.model import artifact as a
from tennis_model.model.features import ANTISYM

MAGIC = b"DEUCE-WTA-SURFACE\x00\x01"
FIELDS = frozenset({"surface_main", "surface_lower", "surface_provenance"})
PROVENANCE_FIELDS = frozenset({"numericalFreeze", "servingFreeze", "selection", "mainInput",
                               "enrichedInput", "mainState", "lowerState"})
HEADER_FIELDS = frozenset({"schema", "artifactId", "trainedAt", "tour", "python", "libraries",
                           "contract", "provenance", "states", "payloadBytes", "payloadSha256"})


def fail(reason, detail):
    raise a.PredictorArtifactError(reason, detail)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def checked_provenance(value):
    if (type(value) is not dict or set(value) != PROVENANCE_FIELDS
            or any(type(v) is not str or not a._SHA256_RE.fullmatch(v) for v in value.values())):
        fail(a.PredictorArtifactReason.CONTRACT_MISMATCH, "explicit surface provenance required")
    return value


def surface_contract():
    package = Path(a.__file__).resolve().parent.parent
    sources = [(str(p.relative_to(package)), digest(p.read_bytes()))
               for p in sorted(package.rglob("*")) if p.is_file() and p.suffix in {".py", ".json"}]
    research = Path(__file__).parent
    for name in ("historical_signals.py", "signal_combiner.py", "surface_candidate.py", "surface_artifact.py"):
        sources.append(("research/"+name, digest((research / name).read_bytes())))
    return {"base": a.predictor_contract("wta"), "researchSchema": SCHEMA,
            "features": COLUMNS, "signedFeatures": [*ANTISYM, FEATURE],
            "statePolicy": "inclusive-60-day-completed-surface-count-pre-row-v1",
            "sourceSHA256": digest(canonical(sources))}


def state_receipt(state):
    """Pin the complete original signal state, including otherwise unused histories."""
    try:
        if type(state) is not SignalState or set(vars(state)) != {"recent", "exposure", "ranks", "through"}:
            raise ValueError("signal state type/fields differ")
        through = state.through
        if through is not None and (type(through) is not pd.Timestamp or pd.isna(through)):
            raise ValueError("invalid signal cutoff")
        encoded = {"through": through.isoformat() if through is not None else None}
        players = set()
        for name, span, maxlen in (("recent", None, 10), ("exposure", 60, None), ("ranks", 365, None)):
            mapping = getattr(state, name)
            if type(mapping) is not dict:
                raise ValueError("signal state mapping differs")
            encoded[name] = {}
            for player, rows in mapping.items():
                if type(player) is not str or not player or type(rows) is not deque or rows.maxlen != maxlen:
                    raise ValueError("invalid signal player/history")
                if not rows or through is None:
                    raise ValueError("signal history without cutoff/observations")
                players.add(player)
                converted, previous = [], None
                for row in rows:
                    if type(row) is not tuple or len(row) != 2:
                        raise ValueError("invalid signal observation")
                    date, value = row
                    if (type(date) is not pd.Timestamp or pd.isna(date) or date > through
                            or (previous is not None and (date < previous or (name == "ranks" and date == previous)))):
                        raise ValueError("invalid signal date order")
                    if name == "exposure":
                        if type(value) is not str or not value:
                            raise ValueError("invalid surface")
                    else:
                        if not isinstance(value, (float, int, np.floating)) or not np.isfinite(value):
                            raise ValueError("nonfinite signal value")
                        value = float(value)
                        if (name == "recent" and not -1 <= value <= 1) or (name == "ranks" and value <= 0):
                            raise ValueError("invalid signal value range")
                    previous = date
                    converted.append([date.isoformat(), value])
                if span is not None and (rows[-1][0]-rows[0][0]).days > span:
                    raise ValueError("unpruned signal history")
                encoded[name][player] = converted
        return {"players": len(players), "through": encoded["through"], "sha256": digest(canonical(encoded))}
    except (AttributeError, TypeError, ValueError, KeyError, OverflowError) as exc:
        fail(a.PredictorArtifactReason.STATE_INVALID, str(exc))


def validate_surface_structure(predictor, *, expected_provenance):
    expected = checked_provenance(expected_provenance)
    a._validate_predictor(predictor, "wta", artifact_id=getattr(predictor, "artifact_id", None),
                          trained_at=getattr(predictor, "trained_at", None),
                          predictor_type=SurfaceCandidatePredictor, additional_fields=FIELDS,
                          model_features=COLUMNS)
    if checked_provenance(predictor.surface_provenance) != expected:
        fail(a.PredictorArtifactReason.CONTRACT_MISMATCH, "surface provenance differs")
    for label, elo in (("main", predictor.elo), ("lower", predictor.lower_elo)):
        state = getattr(predictor, "surface_"+label)
        receipt = state_receipt(state)
        if receipt["sha256"] != expected[label+"State"]:
            fail(a.PredictorArtifactReason.STATE_INVALID, "surface state differs from pinned input walk")
        if state.through != (pd.Timestamp(elo.last_date) if elo.last_date is not None else None):
            fail(a.PredictorArtifactReason.STATE_INVALID, "surface cutoff differs from selected ordinary state")


def checked_path(path, trusted_root):
    path = a._absolute_without_symlink_resolution(path)
    root = a._absolute_without_symlink_resolution(trusted_root)
    production = a._absolute_without_symlink_resolution(OUTPUT_DIR)
    if path.suffix != ".surface" or path.is_relative_to(production) or root.is_relative_to(production):
        fail(a.PredictorArtifactReason.PATH_INVALID, "explicit .surface artifact outside production output required")
    a._trusted_root_for(path, root)
    return path, root


def save_surface(predictor, path, *, trusted_root):
    path, root = checked_path(path, trusted_root)
    a._preflight_write_path(path, trusted_root=root)
    validate_surface_structure(predictor, expected_provenance=predictor.surface_provenance)
    payload = pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL)
    if not 0 < len(payload) <= a.MAX_PREDICTOR_BYTES:
        fail(a.PredictorArtifactReason.PAYLOAD_TOO_LARGE, "surface payload size")
    header = {"schema": SCHEMA, "artifactId": predictor.artifact_id, "trainedAt": predictor.trained_at,
              "tour": "wta", "python": a._python_identity(), "libraries": a._library_versions(),
              "contract": surface_contract(), "provenance": predictor.surface_provenance,
              "states": {key: state_receipt(getattr(predictor, "surface_"+key)) for key in ("main", "lower")},
              "payloadBytes": len(payload), "payloadSha256": digest(payload)}
    encoded = canonical(header)
    if len(encoded) > a.MAX_ENVELOPE_BYTES:
        fail(a.PredictorArtifactReason.ENVELOPE_TOO_LARGE, "surface header size")
    a._atomic_write(path, MAGIC+struct.pack(">I", len(encoded))+encoded+payload, trusted_root=root)


def load_surface(path, *, expected_provenance, trusted_root):
    expected = checked_provenance(expected_provenance)
    path, root = checked_path(path, trusted_root)
    data = a._read_bounded(path, len(MAGIC)+4+a.MAX_ENVELOPE_BYTES+a.MAX_PREDICTOR_BYTES,
                           io_reason=a.PredictorArtifactReason.PAYLOAD_IO,
                           too_large_reason=a.PredictorArtifactReason.PAYLOAD_TOO_LARGE, trusted_root=root)
    prefix = len(MAGIC)+4
    if len(data) < prefix or data[:len(MAGIC)] != MAGIC:
        fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "not a surface artifact")
    size = struct.unpack(">I", data[len(MAGIC):prefix])[0]
    if not 0 < size <= a.MAX_ENVELOPE_BYTES or prefix+size >= len(data):
        fail(a.PredictorArtifactReason.ENVELOPE_TOO_LARGE, "surface header boundary")
    try:
        header = json.loads(data[prefix:prefix+size], object_pairs_hook=a._reject_duplicate_keys,
                            parse_constant=a._reject_json_constant)
    except (UnicodeDecodeError, ValueError) as exc:
        fail(a.PredictorArtifactReason.ENVELOPE_MALFORMED, str(exc))
    if (type(header) is not dict or set(header) != HEADER_FIELDS or header["schema"] != SCHEMA
            or header["tour"] != "wta" or not a._valid_artifact_id(header["artifactId"])
            or not a._valid_timestamp(header["trainedAt"])):
        fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "invalid surface header")
    if (canonical(header["python"]) != canonical(a._python_identity())
            or canonical(header["libraries"]) != canonical(a._library_versions())):
        fail(a.PredictorArtifactReason.RUNTIME_MISMATCH, "surface runtime differs")
    if (canonical(header["contract"]) != canonical(surface_contract())
            or checked_provenance(header["provenance"]) != expected):
        fail(a.PredictorArtifactReason.CONTRACT_MISMATCH, "surface contract differs")
    states = header["states"]
    if type(states) is not dict or set(states) != {"main", "lower"}:
        fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "surface state receipts absent")
    for label, receipt in states.items():
        if (type(receipt) is not dict or set(receipt) != {"players", "through", "sha256"}
                or type(receipt["players"]) is not int or receipt["players"] < 0
                or (receipt["through"] is not None and type(receipt["through"]) is not str)
                or receipt["sha256"] != expected[label+"State"]):
            fail(a.PredictorArtifactReason.ENVELOPE_SCHEMA, "invalid or unpinned surface state receipt")
    payload = data[prefix+size:]
    if (type(header["payloadBytes"]) is not int or not 0 < header["payloadBytes"] <= a.MAX_PREDICTOR_BYTES
            or header["payloadBytes"] != len(payload)):
        fail(a.PredictorArtifactReason.PAYLOAD_SIZE_MISMATCH, "surface payload length differs")
    if type(header["payloadSha256"]) is not str or header["payloadSha256"] != digest(payload):
        fail(a.PredictorArtifactReason.PAYLOAD_CHECKSUM_MISMATCH, "surface payload digest differs")
    predictor = a._deserialize(payload)
    validate_surface_structure(predictor, expected_provenance=expected)
    if predictor.artifact_id != header["artifactId"] or predictor.trained_at != header["trainedAt"]:
        fail(a.PredictorArtifactReason.PREDICTOR_ID, "surface generation differs")
    if states != {key: state_receipt(getattr(predictor, "surface_"+key)) for key in ("main", "lower")}:
        fail(a.PredictorArtifactReason.STATE_INVALID, "surface state receipts differ")
    return predictor
