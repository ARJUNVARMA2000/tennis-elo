"""Timing and durable status receipts for pipeline stages.

The hourly refresh log is the profiler we always have in CI. Keep each measurement to
one atomic line so ATP/WTA output remains readable when their exports run concurrently.

Selected soft-fail stages additionally persist one private, per-tour receipt.  The
receipt is operational state rather than a web artifact: it remembers the most recent
attempt and the last success independently, so an unchanged failure cannot disappear
merely because a later quick/full mode did not attempt that stage.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from .config import output_dir

STAGE_STATUS_SCHEMA = "stage-status-v1"
# Deliberately not JSON-suffixed: a rollback to an older mirror that copies every
# ``*.json`` must still be unable to publish private exception prose.
STAGE_STATUS_FILENAME = "stage-status.private"
LEGACY_STAGE_STATUS_FILENAME = "stage-status.json"
STAGE_ERROR_TYPE_MAX_CHARS = 120
STAGE_ERROR_MESSAGE_MAX_CHARS = 500
PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS = 36
STAGE_STATUS_MAX_FUTURE_SKEW_MINUTES = 5
PRODUCT_STAGE_NAMES = frozenset({"upcoming_prepare", "tracking", "forecast_products"})

_CRITICALITIES = frozenset({"product", "evaluation"})
_OUTCOMES = frozenset({"success", "failure"})
_STAGE_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_INPUT_FINGERPRINT_RE = re.compile(r"^si1:[0-9a-f]{64}$")
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


@dataclass(slots=True)
class StageAttempt:
    """Mutable observation returned by :func:`timed` for non-throwing degradation.

    Some best-effort producers deliberately retain their last-good artifact and return
    normally when an input is corrupt or an optional provider is wholly unavailable.  The
    pipeline can mark that attempt failed for observability without changing the producer's
    fallback behavior or raising through its established soft-fail boundary.
    """

    failure: BaseException | None = None

    def mark_failure(self, error: BaseException) -> None:
        if not isinstance(error, BaseException):
            raise TypeError("stage degradation must be represented by an exception")
        if self.failure is None:
            self.failure = error


def stage_input_fingerprint(*parts: object) -> str:
    """Return a deterministic identity for JSON-safe stage inputs.

    Callers pass compact provenance (normalized-frame fingerprint, predictor generation,
    mode flags), never a mutable object's repr.  Rejecting non-finite/non-JSON values
    keeps the same fingerprint stable across processes and Python invocations.
    """
    raw = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode()
    return f"si1:{hashlib.sha256(raw).hexdigest()}"


def stage_status_path(tour: str) -> Path:
    return output_dir(tour) / STAGE_STATUS_FILENAME


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("stage timestamp must be a UTC ISO string")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("stage timestamp is unparseable") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("stage timestamp must be UTC")
    return parsed


def _validate_stage_record(stage: str, record: object, updated_at: datetime) -> None:
    if not _STAGE_RE.fullmatch(stage):
        raise ValueError(f"invalid pipeline stage identity {stage!r}")
    if not isinstance(record, dict):
        raise ValueError("stage record must be an object")
    required = {
        "criticality", "outcome", "attemptedAt", "completedAt", "durationMs",
        "inputFingerprint", "lastSuccessAt", "lastSuccessInputFingerprint", "error",
    }
    if set(record) != required:
        raise ValueError("stage record fields do not match stage-status-v1")
    if record["criticality"] not in _CRITICALITIES:
        raise ValueError("stage criticality is invalid")
    if record["outcome"] not in _OUTCOMES:
        raise ValueError("stage outcome is invalid")
    attempted = _parse_utc(record["attemptedAt"])
    completed = _parse_utc(record["completedAt"])
    if attempted > completed or completed > updated_at:
        raise ValueError("stage timestamps are out of order")
    duration = record["durationMs"]
    if not isinstance(duration, int) or isinstance(duration, bool) or duration < 0:
        raise ValueError("stage durationMs must be a non-negative integer")
    if not isinstance(record["inputFingerprint"], str) or not _INPUT_FINGERPRINT_RE.fullmatch(
            record["inputFingerprint"]):
        raise ValueError("stage input fingerprint is invalid")

    last_success = record["lastSuccessAt"]
    last_fp = record["lastSuccessInputFingerprint"]
    if (last_success is None) != (last_fp is None):
        raise ValueError("last-success timestamp and fingerprint must be paired")
    if last_success is not None:
        if _parse_utc(last_success) > completed:
            raise ValueError("stage last success follows its latest attempt")
        if not isinstance(last_fp, str) or not _INPUT_FINGERPRINT_RE.fullmatch(last_fp):
            raise ValueError("stage last-success input fingerprint is invalid")

    error = record["error"]
    if record["outcome"] == "success":
        if error is not None:
            raise ValueError("successful stage cannot carry an error")
        if last_success != record["completedAt"] or last_fp != record["inputFingerprint"]:
            raise ValueError("successful stage must advance last-success state")
    else:
        if not isinstance(error, dict) or set(error) != {"type", "message"}:
            raise ValueError("failed stage must carry bounded error evidence")
        error_type, message = error["type"], error["message"]
        if (not isinstance(error_type, str) or not error_type
                or len(error_type) > STAGE_ERROR_TYPE_MAX_CHARS
                or not isinstance(message, str) or not message
                or len(message) > STAGE_ERROR_MESSAGE_MAX_CHARS):
            raise ValueError("stage error evidence is malformed or unbounded")


def validate_stage_status(
    payload: object,
    tour: str,
    *,
    observed_at: datetime | None = None,
) -> dict:
    """Validate and return one ``stage-status-v1`` receipt.

    Strict validation prevents a corrupt operational file from manufacturing a product
    failure or recovery. Writers preserve malformed state so the health reader can surface
    it; only a genuinely absent receipt starts a new ledger.
    """
    if not isinstance(payload, dict) or set(payload) != {"schema", "tour", "updatedAt", "stages"}:
        raise ValueError("stage-status-v1 top-level contract mismatch")
    if payload["schema"] != STAGE_STATUS_SCHEMA or payload["tour"] != tour:
        raise ValueError("stage-status-v1 schema/tour mismatch")
    updated_at = _parse_utc(payload["updatedAt"])
    observed = (observed_at or _utc_now()).astimezone(UTC)
    if updated_at > observed + timedelta(minutes=STAGE_STATUS_MAX_FUTURE_SKEW_MINUTES):
        raise ValueError("stage-status-v1 updatedAt is implausibly future-dated")
    stages = payload["stages"]
    if not isinstance(stages, dict):
        raise ValueError("stage-status-v1 stages must be an object")
    for stage, record in stages.items():
        _validate_stage_record(stage, record, updated_at)
    return payload


def _path_lock(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.Lock())


def _bounded_error(error: BaseException) -> dict[str, str]:
    error_type = type(error).__name__[:STAGE_ERROR_TYPE_MAX_CHARS] or "Exception"
    message = " ".join(str(error).split()) or error_type
    if len(message) > STAGE_ERROR_MESSAGE_MAX_CHARS:
        message = message[:STAGE_ERROR_MESSAGE_MAX_CHARS - 1] + "…"
    return {"type": error_type, "message": message}


def record_stage_status(
    tour: str,
    stage: str,
    *,
    criticality: Literal["product", "evaluation"],
    outcome: Literal["success", "failure"],
    attempted_at: datetime,
    completed_at: datetime,
    duration_ms: int,
    input_fingerprint: str,
    error: BaseException | None = None,
    path: Path | None = None,
) -> dict:
    """Atomically merge one attempt into a tour's durable stage receipt."""
    destination = path or stage_status_path(tour)
    with _path_lock(destination):
        if path is None:
            legacy = destination.with_name(LEGACY_STAGE_STATUS_FILENAME)
            if legacy.exists():
                if destination.exists():
                    # The private receipt is authoritative; remove the stale JSON-suffixed
                    # duplicate so even an old wildcard mirror cannot expose it on rollback.
                    legacy.unlink()
                else:
                    # Preserve valid history and malformed evidence alike. Validation below
                    # still refuses to launder a malformed migrated receipt.
                    os.replace(legacy, destination)
        prior: dict = {
            "schema": STAGE_STATUS_SCHEMA,
            "tour": tour,
            "updatedAt": _iso(completed_at),
            "stages": {},
        }
        try:
            raw = destination.read_text(encoding="utf-8")
        except FileNotFoundError:
            raw = None
        except OSError:
            # An unreadable receipt is itself operational evidence.  Do not launder it into
            # a fresh one-stage success before the health reader can surface the defect.
            raise
        if raw is not None:
            try:
                loaded = json.loads(raw)
                prior = validate_stage_status(loaded, tour)
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    "existing stage-status receipt is malformed; refusing to overwrite"
                ) from exc

        previous_stage = prior["stages"].get(stage) or {}
        completed_iso = _iso(completed_at)
        if previous_stage:
            previous_completed = _parse_utc(previous_stage["completedAt"])
            if previous_completed > completed_at:
                # Concurrent attempts can acquire the merge lock in the opposite order
                # from completion. The latest completed attempt remains authoritative.
                return prior
        if outcome == "success":
            last_success_at = completed_iso
            last_success_fp = input_fingerprint
            error_evidence = None
        else:
            last_success_at = previous_stage.get("lastSuccessAt")
            last_success_fp = previous_stage.get("lastSuccessInputFingerprint")
            error_evidence = _bounded_error(
                error if error is not None else RuntimeError("stage failed")
            )
        record = {
            "criticality": criticality,
            "outcome": outcome,
            "attemptedAt": _iso(attempted_at),
            "completedAt": completed_iso,
            "durationMs": max(0, int(duration_ms)),
            "inputFingerprint": input_fingerprint,
            "lastSuccessAt": last_success_at,
            "lastSuccessInputFingerprint": last_success_fp,
            "error": error_evidence,
        }
        stages = dict(prior["stages"])
        stages[stage] = record
        updated_at = max(_parse_utc(prior["updatedAt"]), completed_at)
        payload = {
            "schema": STAGE_STATUS_SCHEMA,
            "tour": tour,
            "updatedAt": _iso(updated_at),
            "stages": dict(sorted(stages.items())),
        }
        validate_stage_status(payload, tour)

        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_name(
            f".{destination.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        try:
            tmp.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
            os.replace(tmp, destination)
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        return payload


@contextmanager
def timed(
    tour: str,
    stage: str,
    *,
    criticality: Literal["product", "evaluation"] | None = None,
    input_fingerprint: str | None = None,
    status_path: Path | None = None,
):
    """Print elapsed wall time and optionally persist the stage attempt.

    Receipt failures are observational and never mask either a successful stage or its
    original exception.  Soft-fail behavior stays owned by the caller's existing boundary.
    """
    if (criticality is None) != (input_fingerprint is None):
        raise ValueError("criticality and input_fingerprint must be supplied together")
    if criticality is not None and criticality not in _CRITICALITIES:
        raise ValueError(f"invalid stage criticality {criticality!r}")
    if input_fingerprint is not None and not _INPUT_FINGERPRINT_RE.fullmatch(input_fingerprint):
        raise ValueError("invalid stage input fingerprint")

    attempted_at = _utc_now()
    started = time.perf_counter()
    failure: BaseException | None = None
    observation = StageAttempt()
    try:
        yield observation
    except BaseException as exc:
        failure = exc
        raise
    finally:
        elapsed = time.perf_counter() - started
        print(f"  timing/{tour}/{stage}: {elapsed:.3f}s", flush=True)
        if criticality is not None and input_fingerprint is not None:
            recorded_failure = failure if failure is not None else observation.failure
            try:
                record_stage_status(
                    tour,
                    stage,
                    criticality=criticality,
                    outcome="failure" if recorded_failure is not None else "success",
                    attempted_at=attempted_at,
                    completed_at=_utc_now(),
                    duration_ms=round(elapsed * 1_000),
                    input_fingerprint=input_fingerprint,
                    error=recorded_failure,
                    path=status_path,
                )
            except Exception as receipt_error:  # noqa: BLE001 - observability cannot own outcome
                print(
                    f"  stage-status/{tour}/{stage}: receipt unavailable "
                    f"({type(receipt_error).__name__}: {receipt_error})",
                    flush=True,
                )
