"""Versioned integrity envelope for the production ``predictor.pkl`` artifact.

The payload deliberately remains a plain pickle so the immediately previous release
can roll back and read it.  New readers validate this bounded, non-``.json`` sibling
before deserializing the exact payload bytes whose length and digest were checked.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
import stat
import sys
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np

from ..config import (
    MATCH_POPULATION_VERSION,
    N_BAG,
    OUTPUT_DIR,
    PLAYER_ALIASES,
    WTA_DUAL_STATE_GATE_THRESHOLD,
)
from ..points.serve_return import ServeReturnState, sr_params_for
from ..ratings.build import RatingState
from ..ratings.elo import params_for
from .features import FEATURES, H2HState, feat_params_for
from .train import (
    BaggedClassifier,
    PlattCalibrator,
    production_xgb_params,
)

PREDICTOR_ENVELOPE_SCHEMA = "tennis-predictor-envelope-v1"
MAX_ENVELOPE_BYTES = 1 * 1024 * 1024
MAX_PREDICTOR_BYTES = 256 * 1024 * 1024
MAX_PENDING_BYTES = 4 * 1024
PREDICTOR_PENDING_SCHEMA = "tennis-predictor-envelope-pending-v1"
MAX_TRAINED_AT_FUTURE_SKEW = timedelta(minutes=5)

_TOURS = frozenset({"atp", "wta"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_MODEL_LIBRARIES = ("numpy", "pandas", "scikit-learn", "xgboost")
_TOP_LEVEL_KEYS = frozenset({
    "schema",
    "artifactId",
    "tour",
    "trainedAt",
    "payloadBytes",
    "payloadSha256",
    "python",
    "libraries",
    "contract",
})
_PENDING_KEYS = frozenset({
    "schema", "artifactId", "tour", "trainedAt", "payloadBytes", "payloadSha256"
})
_CONTRACT_KEYS = frozenset({
    "features",
    "featureParams",
    "eloParams",
    "serveReturnParams",
    "xgboost",
    "population",
    "inference",
    "classes",
    "bag",
    "calibrator",
})
_PREDICTOR_FIELDS = frozenset({
    "clf",
    "iso",
    "elo",
    "srv",
    "ctx",
    "meta",
    "tour",
    "lower_elo",
    "lower_srv",
    "lower_ctx",
    "dual_state_threshold",
    "fp",
    "player_aliases",
    "match_population_version",
    "inference_schema_version",
    "trained_at",
    "artifact_id",
})


class PredictorArtifactReason(StrEnum):
    """Stable machine-readable failure categories for artifact handling."""

    ENVELOPE_IO = "envelope_io"
    ENVELOPE_TOO_LARGE = "envelope_too_large"
    ENVELOPE_MALFORMED = "envelope_malformed"
    ENVELOPE_SCHEMA = "envelope_schema"
    ENVELOPE_MISSING_FOR_CURRENT_PAYLOAD = "envelope_missing_for_current_payload"
    PATH_INVALID = "path_invalid"
    PENDING_IO = "pending_io"
    PENDING_TOO_LARGE = "pending_too_large"
    PENDING_MALFORMED = "pending_malformed"
    INCOMPLETE_WRITE = "incomplete_write"
    TOUR_MISMATCH = "tour_mismatch"
    RUNTIME_MISMATCH = "runtime_mismatch"
    CONTRACT_MISMATCH = "contract_mismatch"
    PAYLOAD_IO = "payload_io"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    PAYLOAD_SIZE_MISMATCH = "payload_size_mismatch"
    PAYLOAD_CHECKSUM_MISMATCH = "payload_checksum_mismatch"
    SERIALIZATION_FAILED = "serialization_failed"
    PUBLICATION_IO = "publication_io"
    DESERIALIZATION_FAILED = "deserialization_failed"
    PREDICTOR_TYPE = "predictor_type"
    PREDICTOR_FIELDS = "predictor_fields"
    PREDICTOR_ID = "predictor_id"
    PREDICTOR_TIME = "predictor_time"
    MODEL_STRUCTURE = "model_structure"
    BOOSTER_INVALID = "booster_invalid"
    CALIBRATOR_INVALID = "calibrator_invalid"
    STATE_INVALID = "state_invalid"


class PredictorArtifactError(RuntimeError):
    """A predictor artifact failed a bounded, typed validation step."""

    def __init__(self, reason: PredictorArtifactReason, detail: str = ""):
        self.reason = PredictorArtifactReason(reason)
        self.code = self.reason.value
        self.detail = str(detail)[:240]
        message = self.code if not self.detail else f"{self.code}: {self.detail}"
        super().__init__(message)


def predictor_envelope_path(payload_path: str | os.PathLike[str]) -> Path:
    """The private sibling path; the suffix keeps old ``*.json`` mirrors away."""
    return Path(f"{os.fspath(payload_path)}.envelope")


def predictor_pending_path(payload_path: str | os.PathLike[str]) -> Path:
    """Crash marker written and fsynced before any new-format payload replace."""
    return Path(f"{os.fspath(payload_path)}.envelope.pending")


def _class_name(value: object | type) -> str:
    cls = value if isinstance(value, type) else type(value)
    return f"{cls.__module__}.{cls.__qualname__}"


def _library_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in _MODEL_LIBRARIES:
        try:
            versions[package] = version(package)
        except PackageNotFoundError as exc:  # pragma: no cover - production deps are pinned
            raise PredictorArtifactError(
                PredictorArtifactReason.RUNTIME_MISMATCH,
                f"required model library is not installed: {package}",
            ) from exc
    return versions


def _python_identity() -> dict[str, str | int]:
    return {
        "cacheTag": sys.implementation.cache_tag or "",
        "major": sys.version_info.major,
        "minor": sys.version_info.minor,
    }


def _calibrator_params() -> dict[str, Any]:
    return PlattCalibrator().lr.get_params(deep=False)


def predictor_contract(tour: str) -> dict[str, Any]:
    """Canonical production contract derived from the code that actually trains it."""
    if tour not in _TOURS:
        raise PredictorArtifactError(
            PredictorArtifactReason.TOUR_MISMATCH, f"unsupported tour: {tour!r}"
        )

    from sklearn.linear_model import LogisticRegression
    from xgboost import Booster, XGBClassifier

    from .predict import INFERENCE_SCHEMA_VERSION, TennisPredictor

    gate = WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None
    return {
        "features": list(FEATURES),
        "featureParams": asdict(feat_params_for(tour)),
        "eloParams": asdict(params_for(tour)),
        "serveReturnParams": asdict(sr_params_for(tour)),
        "xgboost": {"params": production_xgb_params(tour)},
        "population": {
            "matchPopulationVersion": MATCH_POPULATION_VERSION,
            "playerAliases": [list(pair) for pair in sorted(PLAYER_ALIASES.items())],
        },
        "inference": {
            "schemaVersion": INFERENCE_SCHEMA_VERSION,
            "dualStateGateThreshold": gate,
        },
        "classes": {
            "predictor": _class_name(TennisPredictor),
            "combiner": _class_name(BaggedClassifier),
            "boosterEstimator": _class_name(XGBClassifier),
            "booster": _class_name(Booster),
            "calibrator": _class_name(PlattCalibrator),
            "calibratorEstimator": _class_name(LogisticRegression),
            "eloState": _class_name(RatingState),
            "serveReturnState": _class_name(ServeReturnState),
            "contextState": _class_name(H2HState),
        },
        "bag": {
            "size": N_BAG,
            "memberRandomStates": [
                production_xgb_params(tour, bag_index=i)["random_state"]
                for i in range(N_BAG)
            ],
        },
        "calibrator": {
            "features": 1,
            "classes": [0, 1],
            "estimatorParams": _calibrator_params(),
        },
    }


def _fail_schema(detail: str) -> None:
    raise PredictorArtifactError(PredictorArtifactReason.ENVELOPE_SCHEMA, detail)


def _require_dict(value: Any, keys: frozenset[str] | set[str], name: str) -> dict:
    if type(value) is not dict:
        _fail_schema(f"{name} must be an object")
    if set(value) != set(keys):
        _fail_schema(f"{name} keys differ")
    return value


def _require_exact_scalar_types(actual: dict, expected: dict, name: str) -> None:
    _require_dict(actual, set(expected), name)
    for key, expected_value in expected.items():
        value = actual[key]
        if expected_value is None:
            if value is not None:
                _fail_schema(f"{name}.{key} must be null")
        elif type(value) is not type(expected_value):
            _fail_schema(f"{name}.{key} has the wrong type")


def _valid_timestamp(value: Any) -> bool:
    if type(value) is not str or len(value) != 20:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return False
    return (
        parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value
        and parsed <= datetime.now(UTC) + MAX_TRAINED_AT_FUTURE_SKEW
    )


def _valid_artifact_id(value: Any, *, version_number: int = 4) -> bool:
    if type(value) is not str or len(value) != 36:
        return False
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        return False
    return str(parsed) == value and parsed.version == version_number


def _validate_contract_shape(contract: Any, expected: dict[str, Any]) -> None:
    contract = _require_dict(contract, _CONTRACT_KEYS, "contract")

    features = contract["features"]
    if type(features) is not list or not features or any(type(v) is not str for v in features):
        _fail_schema("contract.features must be a non-empty string list")

    for key in ("featureParams", "eloParams", "serveReturnParams"):
        _require_exact_scalar_types(contract[key], expected[key], f"contract.{key}")

    xgboost = _require_dict(contract["xgboost"], {"params"}, "contract.xgboost")
    _require_exact_scalar_types(
        xgboost["params"], expected["xgboost"]["params"], "contract.xgboost.params"
    )

    population = _require_dict(
        contract["population"],
        {"matchPopulationVersion", "playerAliases"},
        "contract.population",
    )
    if type(population["matchPopulationVersion"]) is not int:
        _fail_schema("contract.population.matchPopulationVersion must be an integer")
    aliases = population["playerAliases"]
    if type(aliases) is not list or len(aliases) > 20_000:
        _fail_schema("contract.population.playerAliases must be a bounded list")
    if any(
        type(pair) is not list
        or len(pair) != 2
        or any(type(value) is not str or len(value) > 256 for value in pair)
        for pair in aliases
    ):
        _fail_schema("contract.population.playerAliases contains an invalid pair")

    inference = _require_dict(
        contract["inference"],
        {"schemaVersion", "dualStateGateThreshold"},
        "contract.inference",
    )
    if type(inference["schemaVersion"]) is not int:
        _fail_schema("contract.inference.schemaVersion must be an integer")
    gate = inference["dualStateGateThreshold"]
    if gate is not None and type(gate) is not int:
        _fail_schema("contract.inference.dualStateGateThreshold is invalid")

    classes = contract["classes"]
    _require_exact_scalar_types(classes, expected["classes"], "contract.classes")
    if any(not value or len(value) > 160 for value in classes.values()):
        _fail_schema("contract.classes contains an invalid class name")

    bag = _require_dict(contract["bag"], {"size", "memberRandomStates"}, "contract.bag")
    if type(bag["size"]) is not int or bag["size"] < 1 or bag["size"] > 64:
        _fail_schema("contract.bag.size is invalid")
    seeds = bag["memberRandomStates"]
    if type(seeds) is not list or any(type(seed) is not int for seed in seeds):
        _fail_schema("contract.bag.memberRandomStates is invalid")

    calibrator = _require_dict(
        contract["calibrator"],
        {"features", "classes", "estimatorParams"},
        "contract.calibrator",
    )
    if type(calibrator["features"]) is not int:
        _fail_schema("contract.calibrator.features must be an integer")
    classes_value = calibrator["classes"]
    if type(classes_value) is not list or any(type(value) is not int for value in classes_value):
        _fail_schema("contract.calibrator.classes must be an integer list")
    _require_exact_scalar_types(
        calibrator["estimatorParams"],
        expected["calibrator"]["estimatorParams"],
        "contract.calibrator.estimatorParams",
    )


def _validate_envelope(envelope: Any, expected_tour: str) -> dict[str, Any]:
    envelope = _require_dict(envelope, _TOP_LEVEL_KEYS, "envelope")
    if envelope["schema"] != PREDICTOR_ENVELOPE_SCHEMA:
        _fail_schema("unsupported envelope schema")
    if type(envelope["tour"]) is not str or envelope["tour"] not in _TOURS:
        _fail_schema("envelope.tour is invalid")
    if envelope["tour"] != expected_tour:
        raise PredictorArtifactError(
            PredictorArtifactReason.TOUR_MISMATCH,
            f"expected {expected_tour}, found {envelope['tour']}",
        )
    if not _valid_artifact_id(envelope["artifactId"]):
        _fail_schema("envelope.artifactId is not a canonical UUIDv4")
    if not _valid_timestamp(envelope["trainedAt"]):
        _fail_schema("envelope.trainedAt is not canonical UTC")
    if (
        type(envelope["payloadBytes"]) is not int
        or not 1 <= envelope["payloadBytes"] <= MAX_PREDICTOR_BYTES
    ):
        _fail_schema("envelope.payloadBytes is out of bounds")
    if type(envelope["payloadSha256"]) is not str or not _SHA256_RE.fullmatch(
        envelope["payloadSha256"]
    ):
        _fail_schema("envelope.payloadSha256 is invalid")

    python = _require_dict(envelope["python"], {"cacheTag", "major", "minor"}, "python")
    if (
        type(python["cacheTag"]) is not str
        or not 1 <= len(python["cacheTag"]) <= 64
        or type(python["major"]) is not int
        or type(python["minor"]) is not int
    ):
        _fail_schema("envelope.python is invalid")
    libraries = _require_dict(envelope["libraries"], set(_MODEL_LIBRARIES), "libraries")
    if any(type(value) is not str or not 1 <= len(value) <= 80 for value in libraries.values()):
        _fail_schema("envelope.libraries contains an invalid version")

    if python != _python_identity() or libraries != _library_versions():
        raise PredictorArtifactError(
            PredictorArtifactReason.RUNTIME_MISMATCH,
            "Python or model-library versions differ from the writer",
        )
    expected_contract = predictor_contract(expected_tour)
    _validate_contract_shape(envelope["contract"], expected_contract)
    if envelope["contract"] != expected_contract:
        raise PredictorArtifactError(
            PredictorArtifactReason.CONTRACT_MISMATCH,
            "serialized model contract differs from current production",
        )
    return envelope


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate key: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def _absolute_without_symlink_resolution(path: str | os.PathLike[str]) -> Path:
    """Normalize ``.``/``..`` without following any filesystem link."""

    return Path(os.path.abspath(os.fspath(path)))


def _trusted_root_for(
    path: Path, trusted_root: str | os.PathLike[str] | None
) -> Path:
    """Return the lexical authority boundary for one predictor triplet.

    Production artifacts are rooted at ``OUTPUT_DIR``. Explicit test/tool paths retain
    their historical custom-location API and trust only their containing directory unless
    the caller supplies a narrower shared root.
    """

    absolute = _absolute_without_symlink_resolution(path)
    if trusted_root is not None:
        root = _absolute_without_symlink_resolution(trusted_root)
    else:
        production_root = _absolute_without_symlink_resolution(OUTPUT_DIR)
        try:
            absolute.relative_to(production_root)
        except ValueError:
            root = absolute.parent
        else:
            root = production_root
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.PATH_INVALID,
            "predictor path escapes its trusted root",
        ) from exc
    if not relative.parts:
        raise PredictorArtifactError(
            PredictorArtifactReason.PATH_INVALID,
            "predictor path must name a file below its trusted root",
        )
    return root


def _nofollow_flag() -> int:
    """Return the platform no-follow flag through one testable boundary."""

    return getattr(os, "O_NOFOLLOW", 0)


def _directory_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | _nofollow_flag()
    )


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def _directory_entry(directory: int, name: str) -> os.stat_result:
    """lstat one entry relative to a stable parent descriptor."""

    return os.stat(name, dir_fd=directory, follow_symlinks=False)


def _open_directory_without_symlinks(directory: Path, *, create: bool) -> int:
    """Open an absolute directory one component at a time without following links."""

    absolute = _absolute_without_symlink_resolution(directory)
    if not absolute.is_absolute() or absolute.anchor != os.path.sep:
        raise PredictorArtifactError(
            PredictorArtifactReason.PATH_INVALID,
            "predictor directory must be an absolute local path",
        )
    descriptor: int | None = None
    try:
        descriptor = os.open(os.path.sep, _directory_flags())
        for component in absolute.parts[1:]:
            try:
                entry_before = _directory_entry(descriptor, component)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(component, mode=0o755, dir_fd=descriptor)
                entry_before = _directory_entry(descriptor, component)
            if not stat.S_ISDIR(entry_before.st_mode):
                raise OSError("predictor path component is not a real directory")
            child = os.open(
                component,
                _directory_flags(),
                dir_fd=descriptor,
            )
            try:
                opened = os.fstat(child)
                entry_after = _directory_entry(descriptor, component)
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or not stat.S_ISDIR(entry_after.st_mode)
                    or not _same_file_identity(entry_before, opened)
                    or not _same_file_identity(opened, entry_after)
                ):
                    raise OSError(
                        "predictor path component changed or resolved through a link"
                    )
            except Exception:
                os.close(child)
                raise
            os.close(descriptor)
            descriptor = child
        return descriptor
    except PredictorArtifactError:
        if descriptor is not None:
            os.close(descriptor)
        raise
    except OSError as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise PredictorArtifactError(
            PredictorArtifactReason.PATH_INVALID,
            f"predictor directory traversal failed ({type(exc).__name__})",
        ) from exc


@contextmanager
def _open_artifact_parent(
    path: Path,
    *,
    trusted_root: str | os.PathLike[str] | None = None,
    create: bool = False,
):
    """Yield one stable parent fd after lexical-root and no-symlink validation."""

    absolute = _absolute_without_symlink_resolution(path)
    _trusted_root_for(absolute, trusted_root)
    descriptor = _open_directory_without_symlinks(absolute.parent, create=create)
    try:
        yield descriptor, absolute.name
    finally:
        os.close(descriptor)


def _lexists_secure(
    path: Path, *, trusted_root: str | os.PathLike[str] | None = None
) -> bool:
    with _open_artifact_parent(path, trusted_root=trusted_root) as (directory, name):
        try:
            os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise PredictorArtifactError(
                PredictorArtifactReason.PATH_INVALID,
                f"predictor path inspection failed ({type(exc).__name__})",
            ) from exc
        return True


def _validate_write_destination(directory: int, name: str) -> None:
    """Allow only a missing or real regular-file replacement target."""

    try:
        target = _directory_entry(directory, name)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.PATH_INVALID,
            f"predictor write target inspection failed ({type(exc).__name__})",
        ) from exc
    if not stat.S_ISREG(target.st_mode):
        raise PredictorArtifactError(
            PredictorArtifactReason.PATH_INVALID,
            "predictor write target must be a real regular file",
        )


def _preflight_write_path(
    path: Path, *, trusted_root: str | os.PathLike[str] | None = None
) -> None:
    with _open_artifact_parent(
        path, trusted_root=trusted_root, create=True
    ) as (directory, name):
        _validate_write_destination(directory, name)


def _read_bounded(
    path: Path,
    limit: int,
    *,
    io_reason: PredictorArtifactReason,
    too_large_reason: PredictorArtifactReason,
    trusted_root: str | os.PathLike[str] | None = None,
) -> bytes:
    descriptor = None
    try:
        with _open_artifact_parent(path, trusted_root=trusted_root) as (directory, name):
            entry_before = _directory_entry(directory, name)
            if not stat.S_ISREG(entry_before.st_mode):
                raise OSError("artifact path is not a real regular file")
            descriptor = os.open(
                name,
                os.O_RDONLY | _nofollow_flag(),
                dir_fd=directory,
            )
            before = os.fstat(descriptor)
            entry_after_open = _directory_entry(directory, name)
            if (
                not stat.S_ISREG(before.st_mode)
                or not stat.S_ISREG(entry_after_open.st_mode)
                or not _same_file_identity(entry_before, before)
                or not _same_file_identity(before, entry_after_open)
            ):
                raise OSError("artifact path changed or resolved through a link")
            if before.st_size > limit:
                raise PredictorArtifactError(
                    too_large_reason, f"limit is {limit} bytes"
                )
            chunks = []
            remaining = limit + 1
            while remaining:
                chunk = os.read(descriptor, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            value = b"".join(chunks)
            after = os.fstat(descriptor)
            entry_after_read = _directory_entry(directory, name)
            if (
                len(value) != after.st_size
                or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns
                or before.st_ctime_ns != after.st_ctime_ns
                or not stat.S_ISREG(entry_after_read.st_mode)
                or not _same_file_identity(after, entry_after_read)
            ):
                raise OSError("artifact changed while being read")
    except PredictorArtifactError:
        raise
    except OSError as exc:
        raise PredictorArtifactError(io_reason, type(exc).__name__) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(value) > limit:
        raise PredictorArtifactError(too_large_reason, f"limit is {limit} bytes")
    return value


def _read_envelope(
    path: Path,
    expected_tour: str,
    *,
    trusted_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    raw = _read_bounded(
        path,
        MAX_ENVELOPE_BYTES,
        io_reason=PredictorArtifactReason.ENVELOPE_IO,
        too_large_reason=PredictorArtifactReason.ENVELOPE_TOO_LARGE,
        trusted_root=trusted_root,
    )
    try:
        envelope = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.ENVELOPE_MALFORMED, type(exc).__name__
        ) from exc
    return _validate_envelope(envelope, expected_tour)


def _read_pending(
    path: Path,
    expected_tour: str,
    *,
    trusted_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    raw = _read_bounded(
        path,
        MAX_PENDING_BYTES,
        io_reason=PredictorArtifactReason.PENDING_IO,
        too_large_reason=PredictorArtifactReason.PENDING_TOO_LARGE,
        trusted_root=trusted_root,
    )
    try:
        pending = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.PENDING_MALFORMED, type(exc).__name__
        ) from exc
    try:
        pending = _require_dict(pending, _PENDING_KEYS, "pending")
    except PredictorArtifactError as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.PENDING_MALFORMED, exc.detail
        ) from exc
    if pending["schema"] != PREDICTOR_PENDING_SCHEMA:
        raise PredictorArtifactError(
            PredictorArtifactReason.PENDING_MALFORMED, "unsupported pending schema"
        )
    if pending["tour"] != expected_tour:
        raise PredictorArtifactError(
            PredictorArtifactReason.TOUR_MISMATCH, "pending marker tour mismatch"
        )
    if not _valid_artifact_id(pending["artifactId"]):
        raise PredictorArtifactError(
            PredictorArtifactReason.PENDING_MALFORMED, "pending artifactId is invalid"
        )
    if not _valid_timestamp(pending["trainedAt"]):
        raise PredictorArtifactError(
            PredictorArtifactReason.PENDING_MALFORMED, "pending trainedAt is invalid"
        )
    if (
        type(pending["payloadBytes"]) is not int
        or not 1 <= pending["payloadBytes"] <= MAX_PREDICTOR_BYTES
        or type(pending["payloadSha256"]) is not str
        or not _SHA256_RE.fullmatch(pending["payloadSha256"])
    ):
        raise PredictorArtifactError(
            PredictorArtifactReason.PENDING_MALFORMED, "pending payload identity is invalid"
        )
    return pending


def _read_payload(
    path: Path, *, trusted_root: str | os.PathLike[str] | None = None
) -> bytes:
    return _read_bounded(
        path,
        MAX_PREDICTOR_BYTES,
        io_reason=PredictorArtifactReason.PAYLOAD_IO,
        too_large_reason=PredictorArtifactReason.PAYLOAD_TOO_LARGE,
        trusted_root=trusted_root,
    )


def _checked_payload(
    path: Path,
    envelope: dict[str, Any],
    *,
    trusted_root: str | os.PathLike[str] | None = None,
) -> bytes:
    payload = _read_payload(path, trusted_root=trusted_root)
    if len(payload) != envelope["payloadBytes"]:
        raise PredictorArtifactError(
            PredictorArtifactReason.PAYLOAD_SIZE_MISMATCH,
            f"expected {envelope['payloadBytes']}, found {len(payload)}",
        )
    if hashlib.sha256(payload).hexdigest() != envelope["payloadSha256"]:
        raise PredictorArtifactError(
            PredictorArtifactReason.PAYLOAD_CHECKSUM_MISMATCH,
            "payload digest differs from envelope",
        )
    return payload


def validate_predictor_artifact_identity(
    payload_path: str | os.PathLike[str],
    expected_tour: str,
    *,
    trusted_root: str | os.PathLike[str] | None = None,
) -> dict[str, str | int]:
    """Validate a completed envelope/payload pair without deserializing the pickle.

    Whole-release lineage uses this stricter completed-publication view: unlike the
    loader's crash-recovery path, a still-present pending marker is ineligible even when
    it happens to match a complete pair.
    """
    if expected_tour not in _TOURS:
        raise PredictorArtifactError(
            PredictorArtifactReason.TOUR_MISMATCH, f"unsupported tour: {expected_tour!r}"
        )
    path = Path(payload_path)
    pending_path = predictor_pending_path(path)
    if _lexists_secure(pending_path, trusted_root=trusted_root):
        raise PredictorArtifactError(
            PredictorArtifactReason.INCOMPLETE_WRITE,
            "pending marker makes the predictor publication incomplete",
        )
    envelope_path = predictor_envelope_path(path)
    if not _lexists_secure(envelope_path, trusted_root=trusted_root):
        raise PredictorArtifactError(
            PredictorArtifactReason.ENVELOPE_IO,
            "completed predictor publication requires an envelope",
        )
    envelope = _read_envelope(
        envelope_path, expected_tour, trusted_root=trusted_root
    )
    _checked_payload(path, envelope, trusted_root=trusted_root)
    if _lexists_secure(pending_path, trusted_root=trusted_root):
        raise PredictorArtifactError(
            PredictorArtifactReason.INCOMPLETE_WRITE,
            "pending marker appeared during predictor identity validation",
        )
    return {
        key: envelope[key]
        for key in ("artifactId", "tour", "trainedAt", "payloadBytes", "payloadSha256")
    }


def _deserialize(payload: bytes) -> Any:
    try:
        return pickle.loads(payload)
    except Exception as exc:  # noqa: BLE001 - pickle/library failures share a stable boundary
        raise PredictorArtifactError(
            PredictorArtifactReason.DESERIALIZATION_FAILED, type(exc).__name__
        ) from exc


def _validate_mapping_fields(value: object, fields: tuple[str, ...], name: str) -> None:
    for field in fields:
        if type(getattr(value, field, None)) is not dict:
            raise PredictorArtifactError(
                PredictorArtifactReason.STATE_INVALID, f"{name}.{field} is not a dict"
            )


def _validate_state_bundle(predictor: Any, tour: str) -> None:
    expected_elo_params = params_for(tour)
    expected_sr_params = sr_params_for(tour)
    expected_fp = feat_params_for(tour)

    def validate(elo: Any, srv: Any, ctx: Any, name: str) -> None:
        if type(elo) is not RatingState or type(srv) is not ServeReturnState or type(ctx) is not H2HState:
            raise PredictorArtifactError(
                PredictorArtifactReason.STATE_INVALID, f"{name} state class mismatch"
            )
        if "params" not in vars(elo) or vars(elo)["params"] != expected_elo_params:
            raise PredictorArtifactError(
                PredictorArtifactReason.STATE_INVALID, f"{name} Elo params mismatch"
            )
        if "params" not in vars(srv) or vars(srv)["params"] != expected_sr_params:
            raise PredictorArtifactError(
                PredictorArtifactReason.STATE_INVALID, f"{name} serve/return params mismatch"
            )
        _validate_mapping_fields(
            elo,
            ("overall", "surface", "n", "n_surface", "last_played", "history", "_form"),
            f"{name}.elo",
        )
        _validate_mapping_fields(
            srv,
            ("base", "gsw", "gsp", "grw", "grp", "ssw", "ssp", "srw", "srp", "t_last"),
            f"{name}.srv",
        )
        _validate_mapping_fields(
            ctx, ("_h2h", "_h2h_surface", "_last10", "_recent_work"), f"{name}.ctx"
        )

    if vars(predictor)["fp"] != expected_fp:
        raise PredictorArtifactError(
            PredictorArtifactReason.STATE_INVALID, "predictor FeatureParams mismatch"
        )
    validate(predictor.elo, predictor.srv, predictor.ctx, "main")
    gate = WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None
    lower = (predictor.lower_elo, predictor.lower_srv, predictor.lower_ctx)
    if gate is None:
        if any(value is not None for value in lower):
            raise PredictorArtifactError(
                PredictorArtifactReason.STATE_INVALID, "disabled gate carries lower state"
            )
    else:
        validate(*lower, "lower")


def _same_param(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(expected) is float and np.isnan(expected):
        return np.isnan(actual)
    return actual == expected


def _validate_model(predictor: Any, tour: str) -> None:
    from sklearn.linear_model import LogisticRegression
    from xgboost import Booster, XGBClassifier

    clf = predictor.clf
    if type(clf) is not BaggedClassifier or type(getattr(clf, "clfs", None)) is not list:
        raise PredictorArtifactError(
            PredictorArtifactReason.MODEL_STRUCTURE, "combiner is not a concrete bag"
        )
    if len(clf.clfs) != N_BAG:
        raise PredictorArtifactError(
            PredictorArtifactReason.MODEL_STRUCTURE, "bag size differs from production"
        )
    for index, member in enumerate(clf.clfs):
        if type(member) is not XGBClassifier:
            raise PredictorArtifactError(
                PredictorArtifactReason.BOOSTER_INVALID, f"bag member {index} class mismatch"
            )
        try:
            actual_params = member.get_params(deep=False)
            # Compare the complete wrapper configuration, not only the explicitly
            # requested training knobs.  Exact xgboost-version validation above makes
            # its resolved defaults part of this deterministic contract as well.
            expected_params = XGBClassifier(
                **production_xgb_params(tour, bag_index=index)
            ).get_params(deep=False)
        except Exception as exc:  # noqa: BLE001 - normalize corrupt wrapper state
            raise PredictorArtifactError(
                PredictorArtifactReason.BOOSTER_INVALID,
                f"bag member {index} parameters are unreadable",
            ) from exc
        if any(
            key not in actual_params
            or not _same_param(actual_params[key], expected_value)
            for key, expected_value in expected_params.items()
        ) or set(actual_params) != set(expected_params):
            raise PredictorArtifactError(
                PredictorArtifactReason.BOOSTER_INVALID, f"bag member {index} params mismatch"
            )
        try:
            booster = member.get_booster()
            names = booster.feature_names
            rounds = booster.num_boosted_rounds()
            count = booster.num_features()
        except Exception as exc:  # noqa: BLE001 - normalize XGBoost's fitted-state errors
            raise PredictorArtifactError(
                PredictorArtifactReason.BOOSTER_INVALID,
                f"bag member {index} is not a readable fitted booster",
            ) from exc
        if (
            type(booster) is not Booster
            or names != list(FEATURES)
            or count != len(FEATURES)
            or rounds < 1
        ):
            raise PredictorArtifactError(
                PredictorArtifactReason.BOOSTER_INVALID,
                f"bag member {index} feature schema or fitted state mismatch",
            )

    calibrator = predictor.iso
    if type(calibrator) is not PlattCalibrator or type(getattr(calibrator, "lr", None)) is not LogisticRegression:
        raise PredictorArtifactError(
            PredictorArtifactReason.CALIBRATOR_INVALID, "calibrator class mismatch"
        )
    lr = calibrator.lr
    try:
        calibrator_params_match = lr.get_params(deep=False) == _calibrator_params()
    except Exception as exc:  # noqa: BLE001 - normalize corrupt estimator state
        raise PredictorArtifactError(
            PredictorArtifactReason.CALIBRATOR_INVALID,
            "calibrator params are unreadable",
        ) from exc
    if not calibrator_params_match:
        raise PredictorArtifactError(
            PredictorArtifactReason.CALIBRATOR_INVALID, "calibrator params mismatch"
        )
    try:
        coef = np.asarray(lr.coef_)
        intercept = np.asarray(lr.intercept_)
        classes = np.asarray(lr.classes_)
        feature_count = int(lr.n_features_in_)
    except (AttributeError, TypeError, ValueError) as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.CALIBRATOR_INVALID, "calibrator is not fitted"
        ) from exc
    try:
        valid_shape = (
            coef.shape == (1, 1)
            and intercept.shape == (1,)
            and classes.shape == (2,)
            and np.array_equal(classes, np.array([0, 1]))
            and feature_count == 1
            and bool(np.isfinite(coef).all())
            and bool(np.isfinite(intercept).all())
        )
    except (TypeError, ValueError):
        valid_shape = False
    if not valid_shape:
        raise PredictorArtifactError(
            PredictorArtifactReason.CALIBRATOR_INVALID, "calibrator fitted shape is invalid"
        )


def _validate_predictor(
    predictor: Any,
    tour: str,
    *,
    artifact_id: str,
    trained_at: str,
) -> None:
    # Imported lazily to keep ``predict.TennisPredictor`` free to delegate here.
    from .predict import INFERENCE_SCHEMA_VERSION, TennisPredictor

    if type(predictor) is not TennisPredictor:
        raise PredictorArtifactError(
            PredictorArtifactReason.PREDICTOR_TYPE, "payload class mismatch"
        )
    raw = vars(predictor)
    if set(raw) != set(_PREDICTOR_FIELDS):
        raise PredictorArtifactError(
            PredictorArtifactReason.PREDICTOR_FIELDS, "raw predictor fields differ"
        )
    if raw["tour"] != tour:
        raise PredictorArtifactError(
            PredictorArtifactReason.TOUR_MISMATCH, "payload tour differs from envelope"
        )
    if raw["artifact_id"] != artifact_id or not _valid_artifact_id(raw["artifact_id"]):
        raise PredictorArtifactError(
            PredictorArtifactReason.PREDICTOR_ID, "payload artifact_id differs from envelope"
        )
    if raw["trained_at"] != trained_at or not _valid_timestamp(raw["trained_at"]):
        raise PredictorArtifactError(
            PredictorArtifactReason.PREDICTOR_TIME, "payload trained_at differs from envelope"
        )
    if type(raw["meta"]) is not dict:
        raise PredictorArtifactError(PredictorArtifactReason.STATE_INVALID, "meta is not a dict")
    if raw["player_aliases"] != tuple(sorted(PLAYER_ALIASES.items())):
        raise PredictorArtifactError(
            PredictorArtifactReason.PREDICTOR_FIELDS, "raw player_aliases mismatch"
        )
    if (
        type(raw["match_population_version"]) is not int
        or raw["match_population_version"] != MATCH_POPULATION_VERSION
        or type(raw["inference_schema_version"]) is not int
        or raw["inference_schema_version"] != INFERENCE_SCHEMA_VERSION
    ):
        raise PredictorArtifactError(
            PredictorArtifactReason.PREDICTOR_FIELDS, "raw version fields mismatch"
        )
    expected_gate = WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None
    if raw["dual_state_threshold"] != expected_gate:
        raise PredictorArtifactError(
            PredictorArtifactReason.PREDICTOR_FIELDS, "raw gate threshold mismatch"
        )
    _validate_state_bundle(predictor, tour)
    _validate_model(predictor, tour)


def validate_predictor_structure(predictor: Any, tour: str) -> None:
    """Shared current-contract guard for pipeline reuse."""
    raw = vars(predictor) if hasattr(predictor, "__dict__") else {}
    _validate_predictor(
        predictor,
        tour,
        artifact_id=raw.get("artifact_id"),
        trained_at=raw.get("trained_at"),
    )


def _temporary_name(target_name: str) -> str:
    return f".{target_name}.{uuid.uuid4().hex}.tmp"


def _atomic_write(
    path: Path,
    payload: bytes,
    *,
    trusted_root: str | os.PathLike[str] | None = None,
) -> None:
    temporary_name = _temporary_name(path.name)
    descriptor: int | None = None
    try:
        with _open_artifact_parent(
            path, trusted_root=trusted_root, create=True
        ) as (directory, name):
            _validate_write_destination(directory, name)
            descriptor = os.open(
                temporary_name,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | _nofollow_flag(),
                0o600,
                dir_fd=directory,
            )
            remaining = memoryview(payload)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:  # pragma: no cover - defensive OS contract guard
                    raise OSError("artifact temporary write made no progress")
                remaining = remaining[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            _validate_write_destination(directory, name)
            os.replace(
                temporary_name,
                name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
            )
            os.fsync(directory)
    except Exception:
        if descriptor is not None:
            os.close(descriptor)
        try:
            with _open_artifact_parent(
                path, trusted_root=trusted_root
            ) as (directory, _):
                os.unlink(temporary_name, dir_fd=directory)
        except FileNotFoundError:
            pass
        except PredictorArtifactError:
            pass
        raise


def _remove_pending(
    path: Path, *, trusted_root: str | os.PathLike[str] | None = None
) -> None:
    with _open_artifact_parent(path, trusted_root=trusted_root) as (directory, name):
        os.unlink(name, dir_fd=directory)
        os.fsync(directory)


def save_predictor_artifact(
    predictor: Any,
    payload_path: str | os.PathLike[str],
    *,
    trusted_root: str | os.PathLike[str] | None = None,
) -> None:
    """Atomically publish a rollback-readable pickle, then its strict envelope."""
    path = Path(payload_path)
    tour = getattr(predictor, "tour", None)
    artifact_id = getattr(predictor, "artifact_id", None)
    trained_at = getattr(predictor, "trained_at", None)
    if tour not in _TOURS:
        raise PredictorArtifactError(PredictorArtifactReason.TOUR_MISMATCH, "invalid tour")
    _validate_predictor(
        predictor, tour, artifact_id=artifact_id, trained_at=trained_at
    )
    try:
        payload = pickle.dumps(predictor, protocol=pickle.HIGHEST_PROTOCOL)
    except Exception as exc:  # noqa: BLE001 - normalize third-party pickle failures
        raise PredictorArtifactError(
            PredictorArtifactReason.SERIALIZATION_FAILED, type(exc).__name__
        ) from exc
    if len(payload) > MAX_PREDICTOR_BYTES:
        raise PredictorArtifactError(
            PredictorArtifactReason.PAYLOAD_TOO_LARGE,
            f"payload is {len(payload)} bytes",
        )

    envelope = {
        "schema": PREDICTOR_ENVELOPE_SCHEMA,
        "artifactId": artifact_id,
        "tour": tour,
        "trainedAt": trained_at,
        "payloadBytes": len(payload),
        "payloadSha256": hashlib.sha256(payload).hexdigest(),
        "python": _python_identity(),
        "libraries": _library_versions(),
        "contract": predictor_contract(tour),
    }
    try:
        envelope_bytes = (
            json.dumps(
                envelope,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.SERIALIZATION_FAILED, type(exc).__name__
        ) from exc
    if len(envelope_bytes) > MAX_ENVELOPE_BYTES:
        raise PredictorArtifactError(
            PredictorArtifactReason.ENVELOPE_TOO_LARGE,
            f"envelope is {len(envelope_bytes)} bytes",
        )

    pending = {
        "schema": PREDICTOR_PENDING_SCHEMA,
        "artifactId": artifact_id,
        "tour": tour,
        "trainedAt": trained_at,
        "payloadBytes": len(payload),
        "payloadSha256": envelope["payloadSha256"],
    }
    pending_bytes = (
        json.dumps(
            pending,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    if len(pending_bytes) > MAX_PENDING_BYTES:  # pragma: no cover - fixed tiny schema
        raise PredictorArtifactError(
            PredictorArtifactReason.PENDING_TOO_LARGE,
            f"pending marker is {len(pending_bytes)} bytes",
        )

    # Crash contract: the fsynced marker makes the envelope mandatory before the
    # payload can change. A crash at either later replace cannot expose unpaired bytes.
    pending_path = predictor_pending_path(path)
    try:
        # Validate every publication target before creating the pending marker. Each
        # atomic write repeats this check to close later path-replacement races.
        for target in (pending_path, path, predictor_envelope_path(path)):
            _preflight_write_path(target, trusted_root=trusted_root)
        _atomic_write(pending_path, pending_bytes, trusted_root=trusted_root)
        _atomic_write(path, payload, trusted_root=trusted_root)
        _atomic_write(
            predictor_envelope_path(path), envelope_bytes, trusted_root=trusted_root
        )
        _remove_pending(pending_path, trusted_root=trusted_root)
    except PredictorArtifactError:
        raise
    except OSError as exc:
        raise PredictorArtifactError(
            PredictorArtifactReason.PUBLICATION_IO, type(exc).__name__
        ) from exc


def load_predictor_artifact(
    payload_path: str | os.PathLike[str],
    expected_tour: str,
    *,
    trusted_root: str | os.PathLike[str] | None = None,
) -> Any:
    """Load only after strict rooted envelope and exact-payload preflight."""
    if expected_tour not in _TOURS:
        raise PredictorArtifactError(
            PredictorArtifactReason.TOUR_MISMATCH, f"unsupported tour: {expected_tour!r}"
        )
    path = Path(payload_path)
    envelope_path = predictor_envelope_path(path)
    pending_path = predictor_pending_path(path)
    pending_present = _lexists_secure(pending_path, trusted_root=trusted_root)
    envelope_present = _lexists_secure(envelope_path, trusted_root=trusted_root)
    if pending_present:
        pending = _read_pending(
            pending_path, expected_tour, trusted_root=trusted_root
        )
        if not envelope_present:
            raise PredictorArtifactError(
                PredictorArtifactReason.INCOMPLETE_WRITE,
                "pending marker exists without an envelope",
            )
        envelope = _read_envelope(
            envelope_path, expected_tour, trusted_root=trusted_root
        )
        pending_identity = {
            "artifactId": pending["artifactId"],
            "tour": pending["tour"],
            "trainedAt": pending["trainedAt"],
            "payloadBytes": pending["payloadBytes"],
            "payloadSha256": pending["payloadSha256"],
        }
        envelope_identity = {
            key: envelope[key]
            for key in ("artifactId", "tour", "trainedAt", "payloadBytes", "payloadSha256")
        }
        if pending_identity != envelope_identity:
            raise PredictorArtifactError(
                PredictorArtifactReason.INCOMPLETE_WRITE,
                "pending marker and envelope identify different generations",
            )
    elif envelope_present:
        envelope = _read_envelope(
            envelope_path, expected_tour, trusted_root=trusted_root
        )
    else:
        raise PredictorArtifactError(
            PredictorArtifactReason.ENVELOPE_MISSING_FOR_CURRENT_PAYLOAD,
            "strict predictor envelope is required",
        )

    payload = _checked_payload(path, envelope, trusted_root=trusted_root)

    # This is deliberately the same in-memory byte string checked immediately above;
    # the path is never reopened between checksum validation and deserialization.
    predictor = _deserialize(payload)
    _validate_predictor(
        predictor,
        expected_tour,
        artifact_id=envelope["artifactId"],
        trained_at=envelope["trainedAt"],
    )
    if pending_present:
        try:
            _remove_pending(pending_path, trusted_root=trusted_root)
        except PredictorArtifactError:
            raise
        except OSError as exc:
            raise PredictorArtifactError(
                PredictorArtifactReason.PENDING_IO,
                f"validated pending-marker cleanup failed ({type(exc).__name__})",
            ) from exc
    return predictor
