"""Durable orchestration for the frozen 2026 US Open Tennis Abstract benchmark.

The external pages are mutable, so the comparison is anchored to the normalized first
capture committed under ``tasks/research``.  Later conditional fetches are retained as
immutable receipts but never rewrite that benchmark cohort.  DEUCE's full-field exact
distribution and the conservative pre-start eligibility proof are likewise written once
and then treated as immutable evaluation evidence.

Nothing in this module is imported by training or prediction.  Acquisition, grading,
ledger persistence, and the public scorecard are all best-effort evaluation products.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import os
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from ..artifact_lineage import write_produced_artifact
from ..config import (
    MODEL_DIR,
    PLAYER_ALIASES,
    TENNIS_ABSTRACT_DIR,
    TENNIS_ABSTRACT_US_OPEN_FROZEN,
    live_dir,
    output_dir,
)
from ..data.bracket_rounds import player_identity_key
from ..data.names import name_key
from ..model.predict import can_predict_match, predictor_player_names
from ..sim.exact import exact_from_slots
from . import track
from .tennis_abstract import (
    PROVIDER,
    SNAPSHOT_SCHEMA,
    normalized_sha256,
    refresh_snapshot,
    source_for,
    validate_forecast,
)
from .tennis_abstract_report import build_public_report, evaluate_matches, snapshot_match_ids

EVENT_ID = "189-2026"
EVENT_SLUG = "2026-us-open"
EVENT_TIMEZONE = "America/New_York"
FIRST_CAPTURE_PATH = (
    MODEL_DIR.parent / "tasks" / "research" /
    "2026-us-open-tennis-abstract-first-capture.json"
)
BASELINE_SCHEMA = "deuce-tournament-baseline-v1"
ELIGIBILITY_SCHEMA = "tennis-abstract-timing-eligibility-v1"
LEDGER_SCHEMA = "tennis-abstract-comparison-ledger-v1"
PUBLIC_FILENAME = "tennis-abstract.json"


class BenchmarkEvidenceError(RuntimeError):
    """Frozen benchmark evidence is absent, inconsistent, or would be overwritten."""


def _json_bytes(payload: object, *, pretty: bool = True) -> bytes:
    options = {"ensure_ascii": False, "sort_keys": True, "allow_nan": False}
    if pretty:
        options["indent"] = 2
    else:
        options["separators"] = (",", ":")
    return (json.dumps(payload, **options) + "\n").encode("utf-8")


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), 0o644)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_object(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BenchmarkEvidenceError(f"cannot read benchmark evidence {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkEvidenceError(f"benchmark evidence {path} is not an object")
    return payload


def _parse_instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise BenchmarkEvidenceError("benchmark capture time is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkEvidenceError("benchmark capture time is malformed") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BenchmarkEvidenceError("benchmark capture time is not timezone-aware")
    return parsed.astimezone(UTC)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _frozen_contract(tour: str) -> dict:
    try:
        return TENNIS_ABSTRACT_US_OPEN_FROZEN[tour]
    except KeyError as exc:
        raise BenchmarkEvidenceError(f"unsupported frozen benchmark tour {tour!r}") from exc


def _is_real_frozen_snapshot(tour: str, snapshot: dict) -> bool:
    expected = _frozen_contract(tour)
    return (
        snapshot.get("source", {}).get("capturedAt") == expected["capturedAt"]
        and normalized_sha256(snapshot) == expected["normalizedSha256"]
    )


def _validate_anchored_file(tour: str, snapshot: dict, path: Path, key: str) -> None:
    if not _is_real_frozen_snapshot(tour, snapshot):
        return
    try:
        actual = _sha256_bytes(path.read_bytes())
    except OSError as exc:
        raise BenchmarkEvidenceError(f"cannot hash frozen evidence {path}: {exc}") from exc
    expected = _frozen_contract(tour)[key]
    if actual != expected:
        raise BenchmarkEvidenceError(
            f"frozen evidence digest mismatch in {path}: {actual} != {expected}"
        )


def first_capture_snapshot(tour: str) -> dict:
    """Translate the preserved browser-DOM capture into the strict parser contract."""
    source = source_for(tour, EVENT_ID)
    try:
        capture_bytes = FIRST_CAPTURE_PATH.read_bytes()
    except OSError as exc:
        raise BenchmarkEvidenceError(f"cannot read first capture: {exc}") from exc
    if _sha256_bytes(capture_bytes) != _frozen_contract(tour)["firstCaptureFileSha256"]:
        raise BenchmarkEvidenceError("first-capture file digest differs from frozen contract")
    capture = _read_object(FIRST_CAPTURE_PATH)
    if (
        capture.get("schema") != "external-tournament-forecast-snapshot-v1"
        or capture.get("event") != source.event
        or capture.get("season") != source.season
    ):
        raise BenchmarkEvidenceError("first-capture event identity is malformed")
    raw = (capture.get("snapshots") or {}).get(tour)
    if not isinstance(raw, dict):
        raise BenchmarkEvidenceError(f"first capture has no {tour} snapshot")
    players = raw.get("players")
    if not isinstance(players, list):
        raise BenchmarkEvidenceError(f"first capture has no {tour} player list")
    normalized_players = []
    for position, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            raise BenchmarkEvidenceError(f"first capture {tour} player {position} is malformed")
        normalized_players.append({
            "drawPosition": position,
            "name": player.get("name"),
            "href": player.get("tennisAbstractUrl"),
            "country": player.get("country"),
            "seed": player.get("seed"),
            "entry": player.get("entry"),
            "probabilities": player.get("probabilities"),
        })
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "event": source.event,
        "season": source.season,
        "tour": source.tour,
        "espnId": source.espn_id,
        "source": {
            "provider": PROVIDER,
            "url": source.url,
            "capturedAt": raw.get("capturedAt"),
        },
        "rounds": raw.get("rounds"),
        "players": normalized_players,
    }
    try:
        validate_forecast(snapshot, source)
    except (TypeError, ValueError) as exc:
        raise BenchmarkEvidenceError(f"first capture is invalid: {exc}") from exc
    snapshot["source"]["captureMethod"] = "browser-dom-normalized"
    snapshot["source"]["legacyNormalizedPlayersSha256"] = raw.get(
        "normalizedPlayersSha256"
    )
    snapshot["source"]["normalizedSha256"] = normalized_sha256(snapshot)
    expected = _frozen_contract(tour)
    if (
        snapshot["source"].get("capturedAt") != expected["capturedAt"]
        or snapshot["source"]["normalizedSha256"] != expected["normalizedSha256"]
    ):
        raise BenchmarkEvidenceError("first-capture content or timestamp is not frozen")
    return snapshot


def _event_root(tour: str) -> Path:
    return TENNIS_ABSTRACT_DIR / tour / EVENT_ID


def baseline_path(tour: str) -> Path:
    return _event_root(tour) / "deuce-baseline.json"


def eligibility_path(tour: str) -> Path:
    return _event_root(tour) / "timing-eligibility.json"


def ledger_path(tour: str) -> Path:
    return _event_root(tour) / "comparison.jsonl"


def schedule_receipt_path(tour: str) -> Path:
    return _event_root(tour) / "schedule-receipt.csv"


def _resolve_deuce_names(snapshot: dict, predictor) -> list[tuple[str, str]]:
    available: dict[str, list[str]] = {}
    for candidate in predictor_player_names(predictor):
        available.setdefault(name_key(candidate), []).append(candidate)
    resolved = []
    for player in snapshot["players"]:
        external = str(player["name"])
        aliased = PLAYER_ALIASES.get(name_key(external), external)
        candidates = available.get(name_key(aliased), [])
        if len(candidates) != 1:
            raise BenchmarkEvidenceError(
                f"cannot uniquely map Tennis Abstract player {external!r} into DEUCE state"
            )
        resolved.append((external, candidates[0]))
    if len({canonical for _, canonical in resolved}) != len(resolved):
        raise BenchmarkEvidenceError("DEUCE name reconciliation is not one-to-one")
    return resolved


def build_deuce_baseline(tour: str, predictor, snapshot: dict | None = None) -> dict:
    """Exact full-field reach distribution from a predictor frozen before capture."""
    snapshot = snapshot or first_capture_snapshot(tour)
    captured_at = _parse_instant(snapshot["source"].get("capturedAt"))
    trained_at = _parse_instant(getattr(predictor, "trained_at", None))
    if trained_at > captured_at:
        raise BenchmarkEvidenceError(
            "refusing to backfill the benchmark with a predictor trained after capture"
        )
    resolved = _resolve_deuce_names(snapshot, predictor)
    canonical = [name for _, name in resolved]
    for player_a, player_b in itertools.combinations(canonical, 2):
        if not can_predict_match(predictor, player_a, player_b):
            raise BenchmarkEvidenceError(
                f"DEUCE baseline cannot price {player_a!r} vs {player_b!r}"
            )

    best_of = 5 if tour == "atp" else 3
    matrices = predictor.prediction_matrices(
        canonical,
        surface="Hard",
        best_of=best_of,
        event=snapshot["event"],
    )
    matrix = np.round(np.asarray(matrices["combiner"], dtype=float), 6)
    exact = exact_from_slots(canonical, canonical, matrix)
    rows = []
    for position, (external, deuce_name) in enumerate(resolved, start=1):
        reach = exact["reach"].get(deuce_name, {})
        probabilities = {
            round_name: float(
                reach.get("Champion" if round_name == "W" else round_name, 0.0)
            )
            for round_name in snapshot["rounds"]
        }
        rows.append({
            "drawPosition": position,
            "name": external,
            "deuceName": deuce_name,
            "probabilities": probabilities,
        })
    for round_name in snapshot["rounds"]:
        expected = {"R64": 64, "R32": 32, "R16": 16, "QF": 8,
                    "SF": 4, "F": 2, "W": 1}[round_name]
        actual = math.fsum(row["probabilities"][round_name] for row in rows)
        if not math.isclose(actual, expected, abs_tol=2e-6):
            raise BenchmarkEvidenceError(
                f"DEUCE {round_name} baseline mass {actual} differs from {expected}"
            )
    return {
        "schema": BASELINE_SCHEMA,
        "tour": tour,
        "event": snapshot["event"],
        "season": snapshot["season"],
        "espnId": snapshot["espnId"],
        "sourceCapturedAt": snapshot["source"]["capturedAt"],
        "sourceNormalizedSha256": normalized_sha256(snapshot),
        "predictor": {
            "artifactId": getattr(predictor, "artifact_id", None),
            "trainedAt": getattr(predictor, "trained_at", None),
        },
        "method": {
            "name": "exact-fixed-bracket-propagation",
            "surface": "Hard",
            "bestOf": best_of,
            "pairwiseMatrixRoundedDigits": 6,
            "usesPlayedResults": False,
        },
        "rounds": list(snapshot["rounds"]),
        "players": rows,
    }


def _validate_frozen_identity(payload: dict, schema: str, snapshot: dict, path: Path) -> None:
    if (
        payload.get("schema") != schema
        or payload.get("tour") != snapshot["tour"]
        or payload.get("event") != snapshot["event"]
        or payload.get("espnId") != snapshot["espnId"]
        or payload.get("season") != snapshot["season"]
        or payload.get("sourceCapturedAt") != snapshot["source"].get("capturedAt")
        or payload.get("sourceNormalizedSha256") != normalized_sha256(snapshot)
    ):
        raise BenchmarkEvidenceError(f"frozen benchmark identity mismatch in {path}")


def _valid_probability(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )


def _validate_deuce_baseline(tour: str, payload: dict, snapshot: dict, path: Path) -> None:
    _validate_frozen_identity(payload, BASELINE_SCHEMA, snapshot, path)
    rounds = list(snapshot["rounds"])
    players = payload.get("players")
    if payload.get("rounds") != rounds or not isinstance(players, list):
        raise BenchmarkEvidenceError(f"frozen baseline rounds or players are malformed in {path}")
    if len(players) != len(snapshot["players"]):
        raise BenchmarkEvidenceError(f"frozen baseline field size is malformed in {path}")

    deuce_names: set[str] = set()
    for position, (row, external) in enumerate(
        zip(players, snapshot["players"], strict=True), start=1
    ):
        if (
            not isinstance(row, dict)
            or row.get("drawPosition") != position
            or row.get("name") != external.get("name")
            or not isinstance(row.get("deuceName"), str)
            or not row["deuceName"].strip()
        ):
            raise BenchmarkEvidenceError(
                f"frozen baseline player {position} is malformed in {path}"
            )
        deuce_key = name_key(row["deuceName"])
        if not deuce_key or deuce_key in deuce_names:
            raise BenchmarkEvidenceError(f"frozen baseline names are not one-to-one in {path}")
        deuce_names.add(deuce_key)
        probabilities = row.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != set(rounds):
            raise BenchmarkEvidenceError(
                f"frozen baseline probabilities are malformed for player {position}"
            )
        previous = math.inf
        for round_name in rounds:
            probability = probabilities[round_name]
            if not _valid_probability(probability) or float(probability) > previous + 1e-12:
                raise BenchmarkEvidenceError(
                    f"frozen baseline probability is invalid for player {position} {round_name}"
                )
            previous = float(probability)

    expected_mass = {"R64": 64, "R32": 32, "R16": 16, "QF": 8,
                     "SF": 4, "F": 2, "W": 1}
    for round_name in rounds:
        expected = expected_mass.get(round_name)
        if expected is None:
            raise BenchmarkEvidenceError(f"unknown frozen baseline round {round_name!r}")
        actual = math.fsum(
            float(row["probabilities"][round_name]) for row in players
        )
        if not math.isclose(actual, expected, abs_tol=2e-6):
            raise BenchmarkEvidenceError(
                f"frozen baseline {round_name} mass {actual} differs from {expected}"
            )

    predictor = payload.get("predictor")
    method = payload.get("method")
    if not isinstance(predictor, dict) or not isinstance(
        predictor.get("artifactId"), str
    ) or not predictor["artifactId"].strip():
        raise BenchmarkEvidenceError(f"frozen baseline predictor identity is malformed in {path}")
    trained_at = _parse_instant(predictor.get("trainedAt"))
    captured_at = _parse_instant(snapshot["source"].get("capturedAt"))
    if trained_at > captured_at:
        raise BenchmarkEvidenceError(f"frozen baseline predictor postdates capture in {path}")
    expected_method = {
        "name": "exact-fixed-bracket-propagation",
        "surface": "Hard",
        "bestOf": 5 if tour == "atp" else 3,
        "pairwiseMatrixRoundedDigits": 6,
        "usesPlayedResults": False,
    }
    if method != expected_method:
        raise BenchmarkEvidenceError(f"frozen baseline method is malformed in {path}")
    _validate_anchored_file(tour, snapshot, path, "baselineSha256")


def ensure_deuce_baseline(tour: str, predictor, snapshot: dict | None = None) -> dict:
    snapshot = snapshot or first_capture_snapshot(tour)
    path = baseline_path(tour)
    if path.exists():
        payload = _read_object(path)
        _validate_deuce_baseline(tour, payload, snapshot, path)
        return payload
    payload = build_deuce_baseline(tour, predictor, snapshot)
    _atomic_write(path, _json_bytes(payload))
    _validate_deuce_baseline(tour, payload, snapshot, path)
    return payload


def _canonical_match_id(snapshot: dict, row: dict) -> str:
    pair = sorted((player_identity_key(row.get("playerA")),
                   player_identity_key(row.get("playerB"))))
    round_name = str(row.get("round") or "").upper()
    return (
        f"{track.MATCH_ID_VERSION}|espn:{snapshot['espnId']}|{snapshot['season']}|"
        f"{round_name}|{pair[0]}|{pair[1]}"
    )


def build_timing_eligibility(tour: str, snapshot: dict | None = None) -> dict:
    """Freeze next-local-day match IDs as conservative proof of pre-start capture.

    The saved ESPN schedule exposes a calendar date, not an exact start instant.  A row
    dated strictly after the capture's New York calendar day could not yet have begun;
    same-day rows and pairs missing from that saved schedule remain unproven.
    """
    snapshot = snapshot or first_capture_snapshot(tour)
    schedule_path = live_dir(tour) / "upcoming.csv"
    receipt_path = schedule_receipt_path(tour)
    capture_local = _parse_instant(snapshot["source"]["capturedAt"]).astimezone(
        ZoneInfo(EVENT_TIMEZONE)
    )
    snapshot_ids = set(snapshot_match_ids(snapshot))
    safe: dict[str, dict] = {}
    schedule_sha = None
    try:
        if receipt_path.exists():
            raw = receipt_path.read_bytes()
        else:
            raw = schedule_path.read_bytes()
            _atomic_write(receipt_path, raw)
        schedule_sha = _sha256_bytes(raw)
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise BenchmarkEvidenceError(f"cannot read saved schedule proof: {exc}") from exc
    for row in rows:
        if str(row.get("espn_id") or "") != snapshot["espnId"]:
            continue
        scheduled_date = str(row.get("tourney_date") or "")
        try:
            scheduled_day = date.fromisoformat(scheduled_date)
        except ValueError:
            continue
        if scheduled_day <= capture_local.date():
            continue
        match_id = _canonical_match_id(snapshot, row)
        if match_id not in snapshot_ids:
            continue
        safe[match_id] = {
            "matchId": match_id,
            "scheduledDate": scheduled_date,
            "playerA": row.get("playerA"),
            "playerB": row.get("playerB"),
        }
    return {
        "schema": ELIGIBILITY_SCHEMA,
        "tour": tour,
        "event": snapshot["event"],
        "season": snapshot["season"],
        "espnId": snapshot["espnId"],
        "sourceCapturedAt": snapshot["source"]["capturedAt"],
        "sourceNormalizedSha256": normalized_sha256(snapshot),
        "eventTimezone": EVENT_TIMEZONE,
        "captureLocalDate": capture_local.date().isoformat(),
        "rule": "saved scheduledDate is strictly after captureLocalDate",
        "schedule": {
            "relativePath": f"data/raw/{tour}/live/upcoming.csv",
            "receiptRelativePath": (
                f"data/tennis_abstract/{tour}/{EVENT_ID}/schedule-receipt.csv"
            ),
            "sha256": schedule_sha,
        },
        "eligibleMatchIds": sorted(safe),
        "proofs": [safe[key] for key in sorted(safe)],
        "unprovenMatchCount": len(snapshot_ids - set(safe)),
    }


def _validate_timing_eligibility(
    tour: str, payload: dict, snapshot: dict, path: Path
) -> None:
    _validate_frozen_identity(payload, ELIGIBILITY_SCHEMA, snapshot, path)
    capture_local = _parse_instant(snapshot["source"]["capturedAt"]).astimezone(
        ZoneInfo(EVENT_TIMEZONE)
    )
    expected_ids = set(snapshot_match_ids(snapshot))
    eligible_ids = payload.get("eligibleMatchIds")
    proofs = payload.get("proofs")
    if (
        payload.get("eventTimezone") != EVENT_TIMEZONE
        or payload.get("captureLocalDate") != capture_local.date().isoformat()
        or payload.get("rule")
        != "saved scheduledDate is strictly after captureLocalDate"
        or not isinstance(eligible_ids, list)
        or eligible_ids != sorted(eligible_ids)
        or len(eligible_ids) != len(set(eligible_ids))
        or not set(eligible_ids).issubset(expected_ids)
        or not isinstance(proofs, list)
        or len(proofs) != len(eligible_ids)
        or payload.get("unprovenMatchCount") != len(expected_ids) - len(eligible_ids)
    ):
        raise BenchmarkEvidenceError(f"frozen timing eligibility is malformed in {path}")

    schedule = payload.get("schedule")
    expected_source = f"data/raw/{tour}/live/upcoming.csv"
    expected_receipt = f"data/tennis_abstract/{tour}/{EVENT_ID}/schedule-receipt.csv"
    if (
        not isinstance(schedule, dict)
        or schedule.get("relativePath") != expected_source
        or schedule.get("receiptRelativePath") != expected_receipt
        or not isinstance(schedule.get("sha256"), str)
        or len(schedule["sha256"]) != 64
    ):
        raise BenchmarkEvidenceError(f"frozen schedule receipt metadata is malformed in {path}")
    receipt_path = schedule_receipt_path(tour)
    try:
        receipt_raw = receipt_path.read_bytes()
        schedule_rows = list(
            csv.DictReader(receipt_raw.decode("utf-8-sig").splitlines())
        )
    except (OSError, UnicodeError, csv.Error) as exc:
        raise BenchmarkEvidenceError(f"cannot read frozen schedule receipt: {exc}") from exc
    receipt_sha = _sha256_bytes(receipt_raw)
    if receipt_sha != schedule["sha256"]:
        raise BenchmarkEvidenceError(f"frozen schedule receipt digest mismatch in {path}")
    if _is_real_frozen_snapshot(tour, snapshot):
        expected_sha = _frozen_contract(tour)["scheduleReceiptSha256"]
        if receipt_sha != expected_sha:
            raise BenchmarkEvidenceError(f"schedule receipt differs from frozen contract in {path}")

    schedule_evidence = set()
    for row in schedule_rows:
        if str(row.get("espn_id") or "") != snapshot["espnId"]:
            continue
        try:
            scheduled_day = date.fromisoformat(str(row.get("tourney_date") or ""))
        except ValueError:
            continue
        match_id = _canonical_match_id(snapshot, row)
        schedule_evidence.add((
            match_id,
            scheduled_day.isoformat(),
            player_identity_key(row.get("playerA")),
            player_identity_key(row.get("playerB")),
        ))

    seen_proofs: set[str] = set()
    for proof in proofs:
        if not isinstance(proof, dict):
            raise BenchmarkEvidenceError(f"frozen timing proof is malformed in {path}")
        match_id = proof.get("matchId")
        try:
            scheduled_day = date.fromisoformat(str(proof.get("scheduledDate") or ""))
        except ValueError as exc:
            raise BenchmarkEvidenceError(
                f"frozen timing proof date is malformed in {path}"
            ) from exc
        evidence = (
            match_id,
            scheduled_day.isoformat(),
            player_identity_key(proof.get("playerA")),
            player_identity_key(proof.get("playerB")),
        )
        if (
            match_id not in set(eligible_ids)
            or match_id in seen_proofs
            or scheduled_day <= capture_local.date()
            or evidence not in schedule_evidence
        ):
            raise BenchmarkEvidenceError(f"frozen timing proof is not supported in {path}")
        seen_proofs.add(str(match_id))
    if seen_proofs != set(eligible_ids):
        raise BenchmarkEvidenceError(f"frozen timing proofs do not cover eligibility in {path}")
    _validate_anchored_file(tour, snapshot, path, "eligibilitySha256")


def ensure_timing_eligibility(tour: str, snapshot: dict | None = None) -> dict:
    snapshot = snapshot or first_capture_snapshot(tour)
    path = eligibility_path(tour)
    if path.exists():
        payload = _read_object(path)
        _validate_timing_eligibility(tour, payload, snapshot, path)
        return payload
    payload = build_timing_eligibility(tour, snapshot)
    _atomic_write(path, _json_bytes(payload))
    _validate_timing_eligibility(tour, payload, snapshot, path)
    return payload


def load_forecast_records(
    tour: str,
    *,
    captured_at: object | None = None,
) -> tuple[list[dict], int]:
    """Load persisted identity bridges plus the latest pre-capture quote per matchup."""
    path = track.FORECAST_DIR / f"{tour}.jsonl"
    records: list[tuple[datetime, int, dict]] = []
    bridges: list[dict] = []
    malformed = 0
    cutoff = _parse_instant(captured_at) if captured_at is not None else None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return [], 0
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        if not isinstance(row, dict):
            malformed += 1
            continue
        if str(row.get("espnId") or row.get("espn_id") or "") != EVENT_ID:
            continue
        if row.get("type") == "match_identity_bridge":
            # A bridge carries no probability and can be learned after capture: it only
            # preserves the bracket-proven identity of an already-frozen quote.
            bridges.append(row)
            continue
        if row.get("type") not in {"match", "match_snapshot"}:
            continue
        try:
            instant = _parse_instant(row.get("as_of"))
        except BenchmarkEvidenceError:
            malformed += 1
            continue
        if cutoff is not None and instant > cutoff:
            continue
        records.append((instant, index, row))
    latest: dict[tuple[str, frozenset[str]], tuple[datetime, int, dict]] = {}
    for instant, index, row in records:
        pair = frozenset((player_identity_key(row.get("playerA")),
                          player_identity_key(row.get("playerB"))))
        if len(pair) != 2 or not all(pair):
            malformed += 1
            continue
        key = str(row.get("round") or "").upper(), pair
        if key not in latest or (instant, index) > latest[key][:2]:
            latest[key] = (instant, index, row)
    quotes = [latest[key][2] for key in sorted(
        latest, key=lambda item: (item[0], sorted(item[1]))
    )]
    return [*bridges, *quotes], malformed


def _result_records(results: object) -> list[dict]:
    if hasattr(results, "to_dict"):
        frame = results
        columns = set(getattr(frame, "columns", ()))
        event_column = "espn_id" if "espn_id" in columns else (
            "espnId" if "espnId" in columns else None
        )
        if event_column is not None:
            frame = frame[frame[event_column].astype(str).eq(EVENT_ID)]
        return [dict(row) for row in frame.to_dict("records")]
    if isinstance(results, list):
        return [
            dict(row) for row in results
            if isinstance(row, dict)
            and str(row.get("espnId") or row.get("espn_id") or "") == EVENT_ID
        ]
    return []


_LEDGER_FIELDS = (
    "matchId", "round", "drawPositions", "playerA", "playerB", "pTennisAbstract",
    "pDeuce", "deuceAsOf", "status", "reason", "winner", "aWon", "resultType",
)


def _ledger_row(row: dict) -> dict:
    return {key: row[key] for key in _LEDGER_FIELDS if key in row}


def _validate_ledger_comparison(snapshot: dict, row: object) -> dict:
    if not isinstance(row, dict) or row != _ledger_row(row):
        raise BenchmarkEvidenceError("comparison ledger row fields are malformed")
    match_id = row.get("matchId")
    status = row.get("status")
    positions = row.get("drawPositions")
    if (
        not isinstance(match_id, str)
        or match_id not in set(snapshot_match_ids(snapshot))
        or status not in {"pending", "graded", "excluded"}
        or row.get("round") != "R128"
        or not isinstance(positions, list)
        or len(positions) != 2
        or not all(isinstance(value, int) and not isinstance(value, bool) for value in positions)
        or not isinstance(row.get("playerA"), str)
        or not isinstance(row.get("playerB"), str)
        or _canonical_match_id(snapshot, row) != match_id
        or not _valid_probability(row.get("pTennisAbstract"))
    ):
        raise BenchmarkEvidenceError("comparison ledger row identity is malformed")
    if "pDeuce" in row and not _valid_probability(row["pDeuce"]):
        raise BenchmarkEvidenceError("comparison ledger DEUCE probability is malformed")
    if status == "pending" and (
        "pDeuce" not in row or not isinstance(row.get("deuceAsOf"), str)
    ):
        raise BenchmarkEvidenceError("comparison ledger pending row is malformed")
    if status == "graded" and (
        "pDeuce" not in row
        or not isinstance(row.get("winner"), str)
        or not isinstance(row.get("aWon"), bool)
        or row.get("resultType") not in {"completed", "retirement"}
    ):
        raise BenchmarkEvidenceError("comparison ledger graded row is malformed")
    if status == "excluded" and not isinstance(row.get("reason"), str):
        raise BenchmarkEvidenceError("comparison ledger exclusion is malformed")
    return row


def _load_ledger_transitions(tour: str, snapshot: dict) -> list[dict]:
    path = ledger_path(tour)
    if not path.exists():
        return []
    transitions = []
    seen: set[str] = set()
    source_hash = normalized_sha256(snapshot)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise BenchmarkEvidenceError(f"cannot read comparison ledger: {exc}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            transition = json.loads(line)
        except ValueError as exc:
            raise BenchmarkEvidenceError(
                f"comparison ledger line {line_number} is malformed"
            ) from exc
        if not isinstance(transition, dict):
            raise BenchmarkEvidenceError(
                f"comparison ledger line {line_number} is not an object"
            )
        digest = transition.get("transitionSha256")
        unsigned = {
            key: value for key, value in transition.items()
            if key != "transitionSha256"
        }
        expected_digest = hashlib.sha256(
            _json_bytes(unsigned, pretty=False)
        ).hexdigest()
        if (
            set(transition) != {
                "schema", "tour", "espnId", "season", "sourceNormalizedSha256",
                "comparison", "transitionSha256",
            }
            or transition.get("schema") != LEDGER_SCHEMA
            or transition.get("tour") != tour
            or transition.get("espnId") != snapshot["espnId"]
            or transition.get("season") != snapshot["season"]
            or transition.get("sourceNormalizedSha256") != source_hash
            or not isinstance(digest, str)
            or digest != expected_digest
            or digest in seen
        ):
            raise BenchmarkEvidenceError(
                f"comparison ledger line {line_number} fails its immutable contract"
            )
        _validate_ledger_comparison(snapshot, transition.get("comparison"))
        transitions.append(transition)
        seen.add(digest)
    return transitions


def load_comparison_ledger(tour: str, snapshot: dict) -> list[dict]:
    """Return validated comparison states in append order."""
    return [transition["comparison"] for transition in _load_ledger_transitions(tour, snapshot)]


_TERMINAL_EXCLUSION_REASONS = frozenset({"walkover", "retirement"})


def merge_terminal_comparisons(current: list[dict], prior: list[dict]) -> list[dict]:
    """Keep settled ledger states when an upstream result temporarily disappears."""
    terminal: dict[str, dict] = {}
    for row in prior:
        if row.get("status") == "graded" or (
            row.get("status") == "excluded"
            and row.get("reason") in _TERMINAL_EXCLUSION_REASONS
        ):
            terminal[str(row.get("matchId"))] = row
    merged = []
    for row in current:
        match_id = str(row.get("matchId"))
        settled = terminal.get(match_id)
        if settled is None:
            merged.append(row)
            continue
        if row.get("status") == "graded" and settled.get("status") == "graded":
            comparable = ("winner", "aWon", "resultType", "pDeuce", "pTennisAbstract")
            if any(row.get(key) != settled.get(key) for key in comparable):
                raise BenchmarkEvidenceError(
                    f"current result contradicts terminal ledger state for {match_id}"
                )
            merged.append(row)
        elif row.get("status") == "excluded" and row.get("reason") in (
            _TERMINAL_EXCLUSION_REASONS
        ):
            if row.get("reason") != settled.get("reason"):
                raise BenchmarkEvidenceError(
                    f"current result contradicts terminal ledger state for {match_id}"
                )
            merged.append(row)
        else:
            merged.append(dict(settled))
    return merged


def _ledger_result_rows(snapshot: dict, rows: list[dict]) -> list[dict]:
    """Rehydrate settled first-round outcomes so reach scores cannot regress."""
    out = []
    for row in rows:
        if not (
            row.get("status") == "graded"
            or row.get("reason") in _TERMINAL_EXCLUSION_REASONS
        ) or not isinstance(row.get("winner"), str):
            continue
        winner_key = player_identity_key(row["winner"])
        loser = row.get("playerB") if winner_key == player_identity_key(
            row.get("playerA")
        ) else row.get("playerA")
        out.append({
            "espnId": snapshot["espnId"],
            "season": snapshot["season"],
            "round": row.get("round"),
            "winner_name": row.get("winner"),
            "loser_name": loser,
            "completed": row.get("resultType") == "completed",
            "result_type": row.get("resultType", row.get("reason")),
            "walkover": row.get("reason") == "walkover",
        })
    return out


def append_comparison_ledger(tour: str, snapshot: dict, rows: list[dict]) -> int:
    """Append each new match-state transition once; never rewrite an existing line."""
    path = ledger_path(tour)
    seen = {
        transition["transitionSha256"]
        for transition in _load_ledger_transitions(tour, snapshot)
    }
    additions = []
    source_hash = normalized_sha256(snapshot)
    for row in rows:
        public_row = _validate_ledger_comparison(snapshot, _ledger_row(row))
        transition = {
            "schema": LEDGER_SCHEMA,
            "tour": tour,
            "espnId": snapshot["espnId"],
            "season": snapshot["season"],
            "sourceNormalizedSha256": source_hash,
            "comparison": public_row,
        }
        digest = hashlib.sha256(_json_bytes(transition, pretty=False)).hexdigest()
        if digest in seen:
            continue
        transition["transitionSha256"] = digest
        additions.append(_json_bytes(transition, pretty=False))
        seen.add(digest)
    if not additions:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as handle:
        for raw in additions:
            handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return len(additions)


def _refresh_external_receipts(tour: str) -> tuple[str, str | None]:
    result = refresh_snapshot(TENNIS_ABSTRACT_DIR, source_for(tour, EVENT_ID))
    return result.status, result.error


def run_benchmark(
    tour: str,
    predictor,
    results: object,
    *,
    refresh_external: bool = False,
) -> dict:
    """Grade the frozen benchmark, append transitions, and publish a compact artifact."""
    snapshot = first_capture_snapshot(tour)
    refresh_status, refresh_error = ("skipped", None)
    if refresh_external:
        try:
            refresh_status, refresh_error = _refresh_external_receipts(tour)
        except Exception as exc:  # noqa: BLE001 - acquisition must not suppress grading
            refresh_status = "error"
            refresh_error = f"{type(exc).__name__}: {exc}"
    baseline = ensure_deuce_baseline(tour, predictor, snapshot)
    eligibility = ensure_timing_eligibility(tour, snapshot)
    forecast_records, malformed = load_forecast_records(
        tour,
        captured_at=snapshot["source"]["capturedAt"],
    )
    result_rows = _result_records(results)
    eligible_ids = eligibility["eligibleMatchIds"]
    current_rows = evaluate_matches(
        snapshot,
        forecast_records,
        result_rows,
        eligible_match_ids=eligible_ids,
    )
    prior_rows = load_comparison_ledger(tour, snapshot)
    comparison_rows = merge_terminal_comparisons(current_rows, prior_rows)
    appended = append_comparison_ledger(tour, snapshot, comparison_rows)
    reach_results = [*result_rows, *_ledger_result_rows(snapshot, comparison_rows)]
    report = build_public_report(
        snapshot,
        forecast_records,
        reach_results,
        eligible_match_ids=eligible_ids,
        deuce_stage_probabilities=baseline,
        evaluated_match_rows=comparison_rows,
    )
    report["caveats"] = [
        (
            "This first capture was made after Day 1 began. Same-day or otherwise "
            "unproven matches are excluded; reach and champion comparisons retain that "
            "post-start capture caveat."
        ),
        *report.get("caveats", []),
        "One tournament is descriptive evidence, not a model-selection result.",
    ]
    report["capture"] = {
        "classification": "first-post-start-capture",
        "eventTimezone": eligibility["eventTimezone"],
        "captureLocalDate": eligibility["captureLocalDate"],
        "eligibleMatchProof": eligibility["rule"],
    }
    report["receipts"] = {
        "sourceNormalizedSha256": normalized_sha256(snapshot),
        "predictorArtifactId": baseline["predictor"].get("artifactId"),
        "predictorTrainedAt": baseline["predictor"].get("trainedAt"),
        "forecastMalformedLinesSkipped": malformed,
    }
    destination = output_dir(tour) / PUBLIC_FILENAME
    write_produced_artifact(
        tour,
        destination,
        _json_bytes(report),
        trusted_root=destination.parent.parent,
    )
    return {
        "report": report,
        "rows": comparison_rows,
        "refreshStatus": refresh_status,
        "refreshError": refresh_error,
        "ledgerAppended": appended,
    }
