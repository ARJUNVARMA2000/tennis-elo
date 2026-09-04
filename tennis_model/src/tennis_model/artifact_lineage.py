"""Strict whole-release provenance for the public JSON artifact graph.

The web build consumes a graph rather than a bag of unrelated JSON files: four indexes
name their shards, while a fixed core and a few evaluation products are read directly.
This module makes that graph one bounded, byte-exact release.  The public manifest is
written only after all declared artifacts; the private acceptance receipt is written only
after the caller confirms that the existing semantic output gate passed.

The module deliberately owns no pipeline policy.  Every mutation/publication primitive
throws on failure; typed inspection remains available for the gate and health reporter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Literal

ARTIFACT_LINEAGE_SCHEMA = "artifact-lineage-v1"
ACCEPTANCE_SCHEMA = "artifact-lineage-acceptance-v1"
MANIFEST_FILENAME = "release-manifest.json"
# Intentionally not JSON-suffixed.  A rollback to a wildcard ``*.json`` mirror still
# cannot publish the fact that an operational gate accepted a particular cache entry.
ACCEPTANCE_FILENAME = "release-accepted.private"

TOURS = ("atp", "wta")
RELEASE_MODES = frozenset({"full", "quick"})

MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_ACCEPTANCE_BYTES = 8 * 1024
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
MAX_PRIVATE_PREDICTOR_BYTES = 256 * 1024 * 1024
MAX_PRIVATE_ENVELOPE_BYTES = 1 * 1024 * 1024
MAX_RELEASE_BYTES = 512 * 1024 * 1024
MAX_ARTIFACTS = 1_024
MAX_INDEX_REFERENCES = 512
MAX_FILENAME_CHARS = 160
MAX_PRODUCER_CHARS = 160
MAX_VALIDATOR_CHARS = 160
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 1_000_000
MAX_FUTURE_SKEW = timedelta(minutes=5)

ROLE_PUBLIC_CORE = "public-core"
ROLE_MATRIX_INDEX = "matrix-index"
ROLE_MATRIX_SHARD = "matrix-shard"
ROLE_PROFILE_INDEX = "profile-index"
ROLE_PROFILE_SHARD = "profile-shard"
ROLE_SCENARIO_INDEX = "scenario-index"
ROLE_SCENARIO_SHARD = "scenario-shard"
ROLE_UPCOMING_INDEX = "upcoming-index"
ROLE_UPCOMING_EVENT = "upcoming-event"
ROLE_UPCOMING_EVIDENCE = "upcoming-evidence"
ROLE_EVALUATION = "evaluation"

ARTIFACT_ROLES = frozenset({
    ROLE_PUBLIC_CORE,
    ROLE_MATRIX_INDEX,
    ROLE_MATRIX_SHARD,
    ROLE_PROFILE_INDEX,
    ROLE_PROFILE_SHARD,
    ROLE_SCENARIO_INDEX,
    ROLE_SCENARIO_SHARD,
    ROLE_UPCOMING_INDEX,
    ROLE_UPCOMING_EVENT,
    ROLE_UPCOMING_EVIDENCE,
    ROLE_EVALUATION,
})

# These match the output gate's always-present public surface.  Indexes live separately
# because their recursively declared shards are part of the release too.
FIXED_PUBLIC_CORE = frozenset({
    "brackets.json",
    "draws.json",
    "event_coverage.json",
    "fixtures.json",
    "meta.json",
    "method.json",
    "performance.json",
    "players.json",
    "ratings_history.json",
    "tournaments.json",
})
INDEX_FILES = {
    "matrix-index.json": ROLE_MATRIX_INDEX,
    "profile-index.json": ROLE_PROFILE_INDEX,
    "scenario-index.json": ROLE_SCENARIO_INDEX,
    "upcoming-index.json": ROLE_UPCOMING_INDEX,
}
# These may legitimately be absent on a bootstrap or best-effort evaluation failure.  If
# present, however, they are parsed, hashed, declared, and mirrored like every other file.
OPTIONAL_EVALUATION_FILES = frozenset({
    "accuracy.json",
    "kalshi.json",
    "market.json",
    "tennis-abstract.json",
    "track.json",
})
# Operational JSON predates the non-JSON private naming rule.  It is never public and does
# not count as an unknown graph node while the rollout migrates it.
PRIVATE_JSON_FILES = frozenset({"health-source.json", "stage-status.json"})
PRIVATE_MIRROR_FILES = frozenset({
    ACCEPTANCE_FILENAME,
    "predictor.pkl",
    "predictor.pkl.envelope",
    "predictor.pkl.envelope.pending",
    "stage-status.private",
})
_PRIVATE_PRODUCER_JSON = PRIVATE_JSON_FILES | frozenset({MANIFEST_FILENAME})

_ARTIFACT_FIELDS = frozenset({
    "path",
    "role",
    "bytes",
    "sha256",
    "producer",
    "sourceFingerprint",
    "predictorArtifactId",
    "originRelease",
})
_MANIFEST_FIELDS = frozenset({
    "schema", "releaseId", "parent", "createdAt", "mode", "artifacts",
})
_ACCEPTANCE_FIELDS = frozenset({
    "schema", "releaseId", "manifestSha256", "acceptedAt", "validator",
})

_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_FINGERPRINT_RE = re.compile(r"^sf1:[0-9a-f]{64}$")
_PRODUCER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]*$")
_DYNAMIC_FILENAME_RE = {
    ROLE_MATRIX_SHARD: re.compile(r"^matrix-[A-Za-z0-9][A-Za-z0-9._-]*\.json$"),
    ROLE_PROFILE_SHARD: re.compile(r"^profile-[0-9a-f]{16}\.json$"),
    ROLE_SCENARIO_SHARD: re.compile(r"^scenario-[A-Za-z0-9][A-Za-z0-9._-]*\.json$"),
    ROLE_UPCOMING_EVENT: re.compile(
        r"^upcoming-event-[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    ),
    ROLE_UPCOMING_EVIDENCE: re.compile(
        r"^upcoming-evidence-[A-Za-z0-9][A-Za-z0-9._-]*\.json$"
    ),
}
_UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)


class LineageReason(StrEnum):
    """Stable failure classes suitable for health-finding identity."""

    MANIFEST_MISSING = "manifest-missing"
    MANIFEST_INVALID = "manifest-invalid"
    CONTRACT_INVALID = "contract-invalid"
    PATH_INVALID = "path-invalid"
    BOUNDS_EXCEEDED = "bounds-exceeded"
    GRAPH_INVALID = "graph-invalid"
    ARTIFACT_MISSING = "artifact-missing"
    ARTIFACT_MISMATCH = "artifact-mismatch"
    ACCEPTANCE_MISSING = "acceptance-missing"
    ACCEPTANCE_INVALID = "acceptance-invalid"
    ACCEPTANCE_MISMATCH = "acceptance-mismatch"
    SEMANTIC_GATE_RED = "semantic-gate-red"
    IO_ERROR = "io-error"


class ArtifactLineageError(ValueError):
    """One bounded, typed lineage failure.

    ``detail`` is intended for logs, not public health evidence.  The typed reason and
    optional safe relative path are sufficient to create stable public findings.
    """

    def __init__(
        self,
        reason: LineageReason,
        detail: str,
        *,
        path: str | None = None,
        tour: str | None = None,
    ) -> None:
        self.reason = reason
        self.detail = " ".join(str(detail).split())[:500]
        self.path = path
        self.tour = tour if tour in TOURS else None
        super().__init__(f"{reason.value}: {self.detail}")


@dataclass(frozen=True, slots=True)
class ArtifactProvenance:
    producer: str
    source_fingerprint: str
    predictor_artifact_id: str

    def __post_init__(self) -> None:
        _validate_bounded_identity(self.producer, "producer", MAX_PRODUCER_CHARS)
        if not _SOURCE_FINGERPRINT_RE.fullmatch(self.source_fingerprint):
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "source fingerprint must use the sf1 digest format",
            )
        _validate_uuid4(self.predictor_artifact_id, "predictor artifact id")


@dataclass(frozen=True, slots=True)
class ReleaseContext:
    release_id: str
    parent: str | None
    created_at: str
    mode: Literal["full", "quick"]

    def __post_init__(self) -> None:
        _validate_uuid4(self.release_id, "release id")
        if self.parent is not None:
            _validate_uuid4(self.parent, "parent release id")
            if self.parent == self.release_id:
                raise ArtifactLineageError(
                    LineageReason.CONTRACT_INVALID, "a release cannot parent itself"
                )
        _parse_utc(self.created_at, "createdAt")
        if self.mode not in RELEASE_MODES:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID, f"unknown release mode {self.mode!r}"
            )


@dataclass(frozen=True, slots=True)
class TourDraft:
    context: ReleaseContext
    tour: Literal["atp", "wta"]
    artifacts: tuple[dict, ...]


@dataclass(frozen=True, slots=True)
class ValidatedRelease:
    root: Path
    manifest: dict
    manifest_bytes: bytes
    manifest_sha256: str

    @property
    def release_id(self) -> str:
        return self.manifest["releaseId"]

    @property
    def records(self) -> tuple[dict, ...]:
        return tuple(self.manifest["artifacts"])

    @property
    def records_by_path(self) -> dict[str, dict]:
        return {record["path"]: record for record in self.records}


@dataclass(frozen=True, slots=True)
class AcceptedRelease:
    release: ValidatedRelease
    receipt: dict
    receipt_bytes: bytes

    @property
    def release_id(self) -> str:
        return self.release.release_id


@dataclass(frozen=True, slots=True)
class CarriedRelease:
    accepted: AcceptedRelease
    destination_root: Path


@dataclass(frozen=True, slots=True)
class LineageIssue:
    code: str
    severity: Literal["error", "info"]
    reason: LineageReason
    tour: str | None = None
    path: str | None = None

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "reason": self.reason.value,
            "tour": self.tour,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class LineageState:
    state: Literal["valid", "accepted", "missing", "invalid", "unaccepted"]
    release: ValidatedRelease | AcceptedRelease | None
    issues: tuple[LineageIssue, ...] = ()


@dataclass(frozen=True, slots=True)
class MirrorResult:
    release_id: str
    manifest_sha256: str
    manifest_bytes: bytes
    copied: tuple[str, ...]
    removed: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PublicationRoots:
    source: Path
    destination: Path
    source_fd: int
    destination_fd: int

@dataclass(slots=True)
class ProducedArtifactCollector:
    """One process-local all-tour write ledger shared by worker threads."""

    _token: str
    _records: dict[str, set[str]] = field(
        default_factory=lambda: {tour: set() for tour in TOURS}
    )
    _closed: bool = False

    def __enter__(self) -> ProducedArtifactCollector:
        with _PRODUCED_LOCK:
            if self._closed or _ACTIVE_PRODUCED is not self:
                raise ArtifactLineageError(
                    LineageReason.CONTRACT_INVALID,
                    "produced-artifact collector is no longer active",
                )
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        reset_produced_artifacts(self)

    def snapshot(self, tour: str | None = None) -> tuple[str, ...] | dict[str, tuple[str, ...]]:
        with _PRODUCED_LOCK:
            if tour is not None:
                _validate_tour(tour)
                return tuple(sorted(self._records[tour]))
            return {
                current_tour: tuple(sorted(self._records[current_tour]))
                for current_tour in TOURS
            }

    def reset(self) -> None:
        reset_produced_artifacts(self)


_PRODUCED_LOCK = threading.RLock()
_ACTIVE_PRODUCED: ProducedArtifactCollector | None = None


@dataclass(slots=True)
class ReleaseCoordinator:
    """Small parent-process helper for merging independent ATP/WTA drafts."""

    context: ReleaseContext
    _drafts: dict[str, TourDraft] = field(default_factory=dict)

    def merge(self, draft: TourDraft) -> None:
        if draft.context != self.context:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "tour draft belongs to a different release context",
            )
        if draft.tour in self._drafts:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                f"duplicate {draft.tour} tour draft",
            )
        self._drafts[draft.tour] = draft

    def manifest(self) -> dict:
        return merge_release_drafts(self.context, tuple(self._drafts.values()))

    def seal(self, root: Path) -> ValidatedRelease:
        return seal_release(root, self.manifest())


def source_fingerprint(*parts: object) -> str:
    """Canonical identity for the compact JSON-safe inputs behind an artifact set."""

    try:
        raw = json.dumps(
            parts,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (OverflowError, TypeError, ValueError) as exc:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "source fingerprint inputs must be strict JSON",
        ) from exc
    return f"sf1:{hashlib.sha256(raw).hexdigest()}"


def begin_release(
    mode: Literal["full", "quick"],
    *,
    accepted_prior: AcceptedRelease | None = None,
    release_id: str | None = None,
    created_at: datetime | str | None = None,
) -> ReleaseContext:
    """Create the one release identity that must be shared by both tour workers."""

    if isinstance(created_at, datetime):
        created = _iso(created_at)
    elif created_at is None:
        created = _iso(datetime.now(UTC))
    else:
        created = created_at
    return ReleaseContext(
        release_id=release_id or str(uuid.uuid4()),
        parent=accepted_prior.release_id if accepted_prior is not None else None,
        created_at=created,
        mode=mode,
    )


def begin_produced_artifacts() -> ProducedArtifactCollector:
    """Activate one write collector before the exact all-tour producer round.

    Activation happens before this function returns, so two concurrent or nested callers
    cannot both believe they own the ledger.  The returned object is also a context manager;
    reset is guaranteed on normal or exceptional exit.
    """

    global _ACTIVE_PRODUCED
    with _PRODUCED_LOCK:
        if _ACTIVE_PRODUCED is not None:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "a produced-artifact collector is already active",
            )
        collector = ProducedArtifactCollector(_token=str(uuid.uuid4()))
        _ACTIVE_PRODUCED = collector
        return collector


def note_produced_artifact(tour: str, filename: str) -> None:
    """Record one completed public JSON write, or do nothing outside a release round."""

    with _PRODUCED_LOCK:
        collector = _ACTIVE_PRODUCED
        if collector is None:
            return
        _validate_tour(tour)
        _validate_filename(filename)
        if filename in _PRIVATE_PRODUCER_JSON:
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "private or root manifest JSON cannot be recorded as a public write",
            )
        collector._records[tour].add(f"{tour}/{filename}")


def begin_artifact_write(tour: str, filename: str) -> None:
    """Invalidate any earlier success proof immediately before mutating a public file.

    A few pipeline paths are intentionally rewritten later in the same run.  A monotone
    success set would let the first completed write bless bytes left by a failed second
    write, so every writer removes the path before opening/truncating/replacing it and
    calls :func:`note_produced_artifact` only after the new write completes.
    """

    with _PRODUCED_LOCK:
        collector = _ACTIVE_PRODUCED
        if collector is None:
            return
        _validate_tour(tour)
        _validate_filename(filename)
        if filename in _PRIVATE_PRODUCER_JSON:
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "private or root manifest JSON cannot be recorded as a public write",
            )
        collector._records[tour].discard(f"{tour}/{filename}")


def write_produced_artifact(
    tour: str,
    path: Path,
    raw: bytes,
    *,
    trusted_root: Path | None = None,
) -> None:
    """Durably replace one public artifact and record only the completed generation."""

    if not isinstance(raw, bytes):
        raise TypeError("public artifact payload must be bytes")
    _validate_public_producer_filename(Path(path).name)
    path = _validate_public_write_path(tour, Path(path), trusted_root=trusted_root)
    parent_fd = _open_directory_without_symlinks(path.parent, create=True)
    try:
        _validate_public_write_leaf(parent_fd, path.name)
        begin_artifact_write(tour, path.name)
        _atomic_write_public_bytes(parent_fd, path.name, raw)
        _validate_open_directory_binding(path.parent, parent_fd)
    finally:
        os.close(parent_fd)
    note_produced_artifact(tour, path.name)


def write_produced_artifact_batch(
    tour: str,
    artifacts: Sequence[tuple[Path, bytes]],
    *,
    trusted_root: Path | None = None,
) -> None:
    """Durably replace a logical artifact group and prove it only as one completion."""

    _validate_tour(tour)
    items = [(Path(path), raw) for path, raw in artifacts]
    if not items or len({path.name for path, _ in items}) != len(items):
        raise ValueError("public artifact batch must be non-empty with unique filenames")
    validated = []
    for path, raw in items:
        if not isinstance(raw, bytes):
            raise TypeError("public artifact payload must be bytes")
        _validate_public_producer_filename(path.name)
        validated.append((
            _validate_public_write_path(tour, path, trusted_root=trusted_root),
            raw,
        ))
    if len({path.parent for path, _ in validated}) != 1:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "public artifact batch must share one trusted tour directory",
        )
    parent = validated[0][0].parent
    parent_fd = _open_directory_without_symlinks(parent, create=True)
    try:
        for path, _ in validated:
            _validate_public_write_leaf(parent_fd, path.name)
        for path, _ in validated:
            begin_artifact_write(tour, path.name)
        for path, raw in validated:
            _atomic_write_public_bytes(parent_fd, path.name, raw)
        _validate_open_directory_binding(parent, parent_fd)
    finally:
        os.close(parent_fd)
    for path, _ in validated:
        note_produced_artifact(tour, path.name)


def remove_produced_artifact(
    tour: str,
    path: Path,
    *,
    trusted_root: Path | None = None,
) -> None:
    """Durably remove one public artifact and invalidate any earlier success proof."""

    _validate_public_producer_filename(Path(path).name)
    authority = _public_trusted_root(trusted_root)
    path = _validate_public_write_path(tour, Path(path), trusted_root=authority)
    parent_fd = _open_directory_without_symlinks(path.parent, create=True)
    try:
        begin_artifact_write(tour, path.name)
        _durable_unlink_at(parent_fd, path.name)
        _validate_open_directory_binding(path.parent, parent_fd)
    finally:
        os.close(parent_fd)


def unbless_release_for_mutation(root: Path) -> None:
    """Durably remove old acceptance/root pointers before candidate bytes can change."""

    root = _lexical_absolute(Path(root))
    root_fd = _open_directory_without_symlinks(root, create=False)
    try:
        _validate_open_directory_binding(root, root_fd)
        _durable_unlink_at(root_fd, ACCEPTANCE_FILENAME)
        _durable_unlink_at(root_fd, MANIFEST_FILENAME)
        # If the configured path was replaced while revocation ran, both pointers were
        # still removed from the intended descriptor-bound tree, but the caller must stop
        # before any later artifact writer can target the unrelated replacement.
        _validate_open_directory_binding(root, root_fd)
    finally:
        os.close(root_fd)


def snapshot_produced_artifacts(
    tour: str | None = None,
) -> tuple[str, ...] | dict[str, tuple[str, ...]]:
    """Snapshot the active ledger; inactive callers receive an empty stable shape."""

    with _PRODUCED_LOCK:
        if _ACTIVE_PRODUCED is None:
            if tour is not None:
                _validate_tour(tour)
                return ()
            return {current_tour: () for current_tour in TOURS}
        return _ACTIVE_PRODUCED.snapshot(tour)


def reset_produced_artifacts(collector: ProducedArtifactCollector) -> None:
    """Deactivate exactly the collector returned by :func:`begin_produced_artifacts`."""

    global _ACTIVE_PRODUCED
    with _PRODUCED_LOCK:
        if _ACTIVE_PRODUCED is not collector:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "cannot reset a collector that does not own the active ledger",
            )
        _ACTIVE_PRODUCED = None
        collector._closed = True


def discover_tour_artifacts(root: Path, tour: str) -> dict[str, str]:
    """Return the exact safe public graph for one tour as ``path -> role``.

    Every declared file is strict JSON; duplicate object keys, duplicate references,
    unsafe references, missing shards, unreferenced public JSON, and bounds violations are
    rejected here before any manifest can bless them.
    """

    _validate_tour(tour)
    root = Path(root)
    tour_dir = _tour_directory(root, tour)
    if not tour_dir.is_dir():
        raise ArtifactLineageError(
            LineageReason.ARTIFACT_MISSING,
            f"missing {tour} artifact directory",
            path=tour,
        )

    discovered: dict[str, str] = {}
    payloads: dict[str, object] = {}

    def add_required(filename: str, role: str) -> None:
        relative = _artifact_path(tour, filename)
        payloads[filename] = _load_artifact_json(root, relative)
        discovered[relative] = role

    for filename in sorted(FIXED_PUBLIC_CORE):
        add_required(filename, ROLE_PUBLIC_CORE)
    for filename, role in sorted(INDEX_FILES.items()):
        add_required(filename, role)
    for filename in sorted(OPTIONAL_EVALUATION_FILES):
        relative = _artifact_path(tour, filename)
        candidate = _safe_join(root, relative)
        if candidate.exists() or candidate.is_symlink():
            payloads[filename] = _load_artifact_json(root, relative)
            discovered[relative] = ROLE_EVALUATION

    references: list[tuple[str, str]] = []
    references.extend(_matrix_references(payloads["matrix-index.json"]))
    references.extend(_profile_references(payloads["profile-index.json"]))
    references.extend(_scenario_references(payloads["scenario-index.json"]))
    references.extend(_upcoming_references(payloads["upcoming-index.json"]))
    if len(references) > MAX_ARTIFACTS:
        raise ArtifactLineageError(
            LineageReason.BOUNDS_EXCEEDED, "artifact graph has too many references"
        )

    referenced: set[str] = set()
    for filename, role in references:
        _validate_dynamic_filename(filename, role)
        relative = _artifact_path(tour, filename)
        if relative in referenced or relative in discovered:
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID,
                "artifact graph contains a duplicate reference",
                path=relative,
            )
        referenced.add(relative)
    for filename, role in references:
        relative = _artifact_path(tour, filename)
        _load_artifact_json(root, relative)
        discovered[relative] = role

    if len(discovered) > MAX_ARTIFACTS:
        raise ArtifactLineageError(
            LineageReason.BOUNDS_EXCEEDED, "artifact graph exceeds the artifact cap"
        )

    known = {Path(path).name for path in discovered}
    for candidate in tour_dir.rglob("*.json"):
        try:
            relative_to_tour = candidate.relative_to(tour_dir)
        except ValueError as exc:  # pragma: no cover - defensive Path invariant
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID, "artifact escaped its tour directory"
            ) from exc
        if len(relative_to_tour.parts) != 1:
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "nested public JSON is not allowed",
                path=f"{tour}/{relative_to_tour.as_posix()}",
            )
        if candidate.name not in known and candidate.name not in PRIVATE_JSON_FILES:
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID,
                "unreferenced or unknown public JSON artifact",
                path=f"{tour}/{candidate.name}",
            )
    return dict(sorted(discovered.items()))


def draft_tour_release(
    root: Path,
    tour: Literal["atp", "wta"],
    context: ReleaseContext,
    provenance: ArtifactProvenance,
    *,
    carried: CarriedRelease | None = None,
    produced_paths: Iterable[str] | None = None,
) -> TourDraft:
    """Hash one tour graph, preserving provenance only for exact accepted carry-over."""

    root = _lexical_absolute(Path(root))
    if context.mode == "quick" and carried is None:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "quick release requires an exact accepted carry-forward baseline",
        )
    roles = discover_tour_artifacts(root, tour)
    meta_path = f"{tour}/meta.json"
    predictor_identity = _validate_meta_predictor_binding(root, tour)
    meta_artifact_id = predictor_identity["artifactId"]
    if meta_artifact_id != provenance.predictor_artifact_id:
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "meta.json predictor identity does not match draft provenance",
            path=meta_path,
        )

    if produced_paths is None:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "tour draft requires explicit current-run produced paths",
        )
    produced_list = list(produced_paths)
    if len(produced_list) != len(set(produced_list)):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "produced path proof contains duplicates"
        )
    produced = set()
    for path in produced_list:
        path_tour, _ = _split_artifact_path(path)
        if path_tour != tour:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "produced path proof crosses tour boundaries",
                path=path,
            )
        produced.add(path)
    extra_produced = produced - set(roles)
    if extra_produced:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "produced path proof names an artifact outside the discovered graph",
            path=sorted(extra_produced)[0],
        )
    if meta_path not in produced:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "meta.json must be produced in every release",
            path=meta_path,
        )

    carried_records: Mapping[str, dict] = {}
    if carried is not None:
        if _lexical_absolute(carried.destination_root) != root:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "carried release belongs to another destination",
            )
        if context.parent != carried.accepted.release_id:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "carried release does not match the new parent",
            )
        carried_records = carried.accepted.release.records_by_path

    records = []
    total_bytes = 0
    for relative, role in roles.items():
        size, digest = exact_file_identity(
            _safe_join(root, relative), trusted_root=root
        )
        total_bytes += size
        if total_bytes > MAX_RELEASE_BYTES:
            raise ArtifactLineageError(
                LineageReason.BOUNDS_EXCEEDED, "release artifact bytes exceed the cap"
            )
        prior = carried_records.get(relative)
        exact_carry = (
            prior is not None
            and prior["role"] == role
            and prior["bytes"] == size
            and prior["sha256"] == digest
        )
        if relative in produced:
            record = {
                "path": relative,
                "role": role,
                "bytes": size,
                "sha256": digest,
                "producer": provenance.producer,
                "sourceFingerprint": provenance.source_fingerprint,
                "predictorArtifactId": provenance.predictor_artifact_id,
                "originRelease": context.release_id,
            }
        elif exact_carry:
            record = dict(prior)
        else:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "artifact has neither current production proof nor exact accepted carry-forward",
                path=relative,
            )
        records.append(record)
    return TourDraft(context=context, tour=tour, artifacts=tuple(records))


def merge_release_drafts(context: ReleaseContext, drafts: Sequence[TourDraft]) -> dict:
    """Merge exactly one ATP and one WTA draft into the root manifest payload."""

    by_tour: dict[str, TourDraft] = {}
    for draft in drafts:
        if draft.context != context:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "tour drafts do not share one release identity",
            )
        if draft.tour in by_tour:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                f"duplicate {draft.tour} tour draft",
            )
        by_tour[draft.tour] = draft
    if set(by_tour) != set(TOURS):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "a root release requires exactly one ATP and one WTA draft",
        )
    artifacts = sorted(
        (dict(record) for draft in by_tour.values() for record in draft.artifacts),
        key=lambda record: record["path"],
    )
    payload = {
        "schema": ARTIFACT_LINEAGE_SCHEMA,
        "releaseId": context.release_id,
        "parent": context.parent,
        "createdAt": context.created_at,
        "mode": context.mode,
        "artifacts": artifacts,
    }
    _validate_manifest_contract(payload)
    return payload


def seal_release(
    root: Path,
    manifest: object,
    *,
    _root_fd: int | None = None,
) -> ValidatedRelease:
    """Validate and atomically publish the root manifest after all artifact bytes exist."""

    root = _lexical_absolute(Path(root))
    with _borrow_bound_root_fd(root, _root_fd) as root_fd:
        _validate_manifest_against_graph(manifest, root)
        assert isinstance(manifest, dict)
        raw = _json_bytes(manifest)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise ArtifactLineageError(
                LineageReason.BOUNDS_EXCEEDED,
                "serialized manifest exceeds the byte cap",
            )
        mutation_started = False
        try:
            # Once the candidate is proven complete, durably unbless the prior state
            # before publishing the new root pointer. A crash can leave no manifest,
            # never a stale accepted manifest over a mixture of generations.
            _validate_open_directory_binding(root, root_fd)
            mutation_started = True
            _durable_unlink_at(root_fd, ACCEPTANCE_FILENAME)
            _validate_open_directory_binding(root, root_fd)
            _durable_unlink_at(root_fd, MANIFEST_FILENAME)
            _validate_open_directory_binding(root, root_fd)
            _validate_regular_write_leaf(root_fd, MANIFEST_FILENAME)
            _atomic_replace_at(root_fd, MANIFEST_FILENAME, raw)
            _validate_open_directory_binding(root, root_fd)
            sealed = validate_release(root)
            assert isinstance(sealed, ValidatedRelease)
            _require_release_identity(
                ValidatedRelease(
                    root=root,
                    manifest=manifest,
                    manifest_bytes=raw,
                    manifest_sha256=hashlib.sha256(raw).hexdigest(),
                ),
                sealed,
                label="sealed release",
            )
            _validate_open_directory_binding(root, root_fd)
            return sealed
        except Exception:
            if mutation_started:
                _durable_unlink_at(root_fd, MANIFEST_FILENAME)
            raise


def validate_release(
    root: Path,
    *,
    require_accepted: bool = False,
    observed_at: datetime | None = None,
) -> ValidatedRelease | AcceptedRelease:
    """Validate manifest contract, exact graph, exact file bytes, and optionally receipt."""

    root = Path(root)
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.exists() and not manifest_path.is_symlink():
        raise ArtifactLineageError(
            LineageReason.MANIFEST_MISSING, "release manifest is absent"
        )
    try:
        raw = _read_regular_file(
            manifest_path, MAX_MANIFEST_BYTES, trusted_root=root
        )
        manifest = _strict_json_loads(raw, reason=LineageReason.MANIFEST_INVALID)
    except ArtifactLineageError:
        raise
    except OSError as exc:
        raise ArtifactLineageError(
            LineageReason.IO_ERROR, "release manifest is unreadable"
        ) from exc
    _validate_manifest_against_graph(manifest, root, observed_at=observed_at)
    release = ValidatedRelease(
        root=_lexical_absolute(root),
        manifest=manifest,
        manifest_bytes=raw,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )
    if require_accepted:
        return _load_acceptance(release, observed_at=observed_at)
    return release


def accept_release(
    root: Path,
    *,
    semantic_gate_passed: bool,
    validator: str,
    accepted_at: datetime | str | None = None,
    _root_fd: int | None = None,
) -> AcceptedRelease:
    """Write the private receipt only after an explicit green semantic-gate verdict."""

    if semantic_gate_passed is not True:
        raise ArtifactLineageError(
            LineageReason.SEMANTIC_GATE_RED,
            "semantic output gate did not pass; acceptance was not written",
        )
    _validate_bounded_identity(validator, "validator", MAX_VALIDATOR_CHARS)
    root = _lexical_absolute(Path(root))
    with _borrow_bound_root_fd(root, _root_fd) as root_fd:
        release = validate_release(root)
        assert isinstance(release, ValidatedRelease)  # narrow static union
        _validate_open_directory_binding(root, root_fd)
        if isinstance(accepted_at, datetime):
            accepted = _iso(accepted_at)
        elif accepted_at is None:
            accepted = _iso(datetime.now(UTC))
        else:
            accepted = accepted_at
        if _parse_utc(accepted, "acceptedAt") < _parse_utc(
            release.manifest["createdAt"], "createdAt"
        ):
            raise ArtifactLineageError(
                LineageReason.ACCEPTANCE_INVALID,
                "acceptance cannot predate its release",
            )
        receipt = {
            "schema": ACCEPTANCE_SCHEMA,
            "releaseId": release.release_id,
            "manifestSha256": release.manifest_sha256,
            "acceptedAt": accepted,
            "validator": validator,
        }
        _validate_acceptance_contract(receipt)
        raw = _json_bytes(receipt)
        mutation_started = False
        try:
            _validate_open_directory_binding(root, root_fd)
            _validate_regular_write_leaf(root_fd, ACCEPTANCE_FILENAME)
            mutation_started = True
            _atomic_replace_at(root_fd, ACCEPTANCE_FILENAME, raw)
            _validate_open_directory_binding(root, root_fd)
            # Re-read the entire graph, private predictor bindings, manifest, and receipt
            # after publication. A concurrent mutation must never return stale acceptance.
            loaded = load_accepted_release(root)
            _require_accepted_identity(release, raw, loaded, label="accepted release")
            _validate_open_directory_binding(root, root_fd)
            return loaded
        except Exception:
            if mutation_started:
                _durable_unlink_at(root_fd, ACCEPTANCE_FILENAME)
            raise


def load_accepted_release(
    root: Path, *, observed_at: datetime | None = None
) -> AcceptedRelease:
    """Load the only release eligible to seed carry-forward."""

    release = validate_release(
        root, require_accepted=True, observed_at=observed_at
    )
    assert isinstance(release, AcceptedRelease)
    return release


def carry_forward_release(source_root: Path, destination_root: Path) -> CarriedRelease:
    """Copy an exact accepted prior release before any quick-run producer starts.

    Validation and buffering finish before the first destination write.  The accepted
    receipt is copied after the manifest, so a crash can only leave an unaccepted state.
    """

    source, destination = _normalize_root_relationship(
        Path(source_root),
        Path(destination_root),
    )
    if source == destination:
        source_fd = _open_directory_without_symlinks(source, create=False)
        try:
            accepted = load_accepted_release(source)
            _validate_open_directory_binding(source, source_fd)
            return CarriedRelease(accepted=accepted, destination_root=destination)
        finally:
            os.close(source_fd)

    with _publication_roots(source, destination) as roots:
        accepted = load_accepted_release(roots.source)
        _validate_open_directory_binding(roots.source, roots.source_fd)
        buffered = _buffer_release_artifacts(accepted.release)
        private_predictors = _buffer_predictor_artifacts(roots.source)
        _validate_open_directory_binding(roots.source, roots.source_fd)
        _preflight_destination_tours(roots.destination)
        tour_fds = _open_destination_tour_fds(
            roots.destination,
            roots.destination_fd,
        )
        mutation_started = False
        try:
            mutation_started = True
            _durable_unlink_at(roots.destination_fd, ACCEPTANCE_FILENAME)
            _durable_unlink_at(roots.destination_fd, MANIFEST_FILENAME)
            _validate_open_directory_binding(roots.destination, roots.destination_fd)
            _validate_destination_tour_bindings(roots.destination, tour_fds)

            declared = {record["path"] for record, _raw in buffered}
            _prune_carried_destination_at(
                roots.destination_fd,
                tour_fds,
                declared,
            )
            _validate_open_directory_binding(roots.destination, roots.destination_fd)
            _validate_destination_tour_bindings(roots.destination, tour_fds)

            for relative, raw in private_predictors:
                tour, filename = relative.split("/", 1)
                _validate_tour(tour)
                _validate_regular_write_leaf(tour_fds[tour], filename)
                _atomic_replace_at(tour_fds[tour], filename, raw)
                _validate_open_directory_binding(
                    roots.destination,
                    roots.destination_fd,
                )
                _validate_destination_tour_bindings(roots.destination, tour_fds)
            for tour in TOURS:
                _durable_unlink_at(
                    tour_fds[tour],
                    "predictor.pkl.envelope.pending",
                )
            for record, raw in buffered:
                tour, filename = _split_artifact_path(record["path"])
                _validate_regular_write_leaf(tour_fds[tour], filename)
                _atomic_write_public_bytes(tour_fds[tour], filename, raw)
                _validate_open_directory_binding(
                    roots.destination,
                    roots.destination_fd,
                )
                _validate_destination_tour_bindings(roots.destination, tour_fds)

            _validate_regular_write_leaf(
                roots.destination_fd,
                MANIFEST_FILENAME,
            )
            _atomic_replace_at(
                roots.destination_fd,
                MANIFEST_FILENAME,
                accepted.release.manifest_bytes,
            )
            _validate_open_directory_binding(roots.destination, roots.destination_fd)
            _validate_regular_write_leaf(
                roots.destination_fd,
                ACCEPTANCE_FILENAME,
            )
            _atomic_replace_at(
                roots.destination_fd,
                ACCEPTANCE_FILENAME,
                accepted.receipt_bytes,
            )
            _validate_open_directory_binding(roots.destination, roots.destination_fd)
            _validate_destination_tour_bindings(roots.destination, tour_fds)

            copied_release = load_accepted_release(roots.destination)
            _require_accepted_identity(
                accepted.release,
                accepted.receipt_bytes,
                copied_release,
                label="carried destination release",
            )
            _validate_open_directory_binding(roots.destination, roots.destination_fd)
            _validate_destination_tour_bindings(roots.destination, tour_fds)
            return CarriedRelease(
                accepted=copied_release,
                destination_root=roots.destination,
            )
        except Exception as exc:
            if mutation_started:
                try:
                    _revoke_publication_pointers((
                        (roots.destination_fd, ACCEPTANCE_FILENAME),
                        (roots.destination_fd, MANIFEST_FILENAME),
                    ))
                except (ArtifactLineageError, OSError) as cleanup_error:
                    raise cleanup_error from exc
            raise
        finally:
            for tour_fd in tour_fds.values():
                os.close(tour_fd)


def mirror_release(
    source_root: Path,
    destination_root: Path,
    *,
    require_accepted: bool = False,
    on_copy: Callable[[str], None] | None = None,
    _source_root_fd: int | None = None,
    _destination_root_fd: int | None = None,
) -> MirrorResult:
    """Mirror only declared public files and publish the manifest last.

    Stable root descriptors make both writes and failure cleanup refer to the attempted
    trees even if a callback renames a root and installs an unrelated replacement path.
    """

    source, destination = _validate_root_relationship(
        Path(source_root), Path(destination_root), allow_equal=False
    )
    source_fd = _open_directory_without_symlinks(source, create=False)
    try:
        destination_fd = _open_directory_without_symlinks(destination, create=False)
    except Exception:
        os.close(source_fd)
        raise
    mutation_started = False
    tour_fds: dict[str, int] = {}
    try:
        if (
            _source_root_fd is not None
            and not _same_file_identity(
                os.fstat(source_fd), os.fstat(_source_root_fd)
            )
        ):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "publication source root changed before mirror",
            )
        if (
            _destination_root_fd is not None
            and not _same_file_identity(
                os.fstat(destination_fd), os.fstat(_destination_root_fd)
            )
        ):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "publication destination root changed before mirror",
            )
        _validate_open_directory_binding(source, source_fd)
        _validate_open_directory_binding(destination, destination_fd)
        _preflight_destination_tours(destination)
        tour_fds = _open_destination_tour_fds(destination, destination_fd)
        loaded = validate_release(source, require_accepted=require_accepted)
        release = loaded.release if isinstance(loaded, AcceptedRelease) else loaded
        _validate_open_directory_binding(source, source_fd)
        buffered = _buffer_release_artifacts(release)
        _validate_open_directory_binding(source, source_fd)

        _validate_open_directory_binding(destination, destination_fd)
        mutation_started = True
        _durable_unlink_at(destination_fd, MANIFEST_FILENAME)
        removed = _clear_public_destination_at(destination_fd, tour_fds)
        copied: list[str] = []
        for record, raw in buffered:
            relative = record["path"]
            _validate_open_directory_binding(destination, destination_fd)
            tour, filename = _split_artifact_path(relative)
            _validate_regular_write_leaf(tour_fds[tour], filename)
            _atomic_write_public_bytes(tour_fds[tour], filename, raw)
            copied.append(relative)
            if on_copy is not None:
                on_copy(relative)
            _validate_open_directory_binding(destination, destination_fd)
            _validate_destination_tour_bindings(destination, tour_fds)

        _validate_open_directory_binding(destination, destination_fd)
        _validate_destination_tour_bindings(destination, tour_fds)
        # Exact source bytes, not a reserialization. The acceptance receipt is
        # deliberately never copied: it is private operational state, not web data.
        _validate_regular_write_leaf(destination_fd, MANIFEST_FILENAME)
        _atomic_replace_at(destination_fd, MANIFEST_FILENAME, release.manifest_bytes)
        copied.append(MANIFEST_FILENAME)
        if on_copy is not None:
            on_copy(MANIFEST_FILENAME)
        _validate_open_directory_binding(destination, destination_fd)
        _validate_destination_tour_bindings(destination, tour_fds)
        mirrored = validate_public_release(destination)
        _require_release_identity(
            release,
            mirrored,
            label="public destination release",
        )
        _validate_open_directory_binding(destination, destination_fd)

        final_source = validate_release(
            source,
            require_accepted=require_accepted,
        )
        if isinstance(loaded, AcceptedRelease):
            assert isinstance(final_source, AcceptedRelease)
            _require_accepted_identity(
                loaded.release,
                loaded.receipt_bytes,
                final_source,
                label="mirror source release",
            )
        else:
            assert isinstance(final_source, ValidatedRelease)
            _require_release_identity(
                loaded,
                final_source,
                label="mirror source release",
            )
        _validate_open_directory_binding(source, source_fd)
        return MirrorResult(
            release_id=release.release_id,
            manifest_sha256=release.manifest_sha256,
            manifest_bytes=release.manifest_bytes,
            copied=tuple(copied),
            removed=tuple(removed),
        )
    except Exception:
        # The manifest is the public validity pointer. Never return or fall back while a
        # failed post-copy validation can still advertise the destination as complete.
        if _destination_root_fd is not None:
            _durable_unlink_at(_destination_root_fd, MANIFEST_FILENAME)
        elif mutation_started:
            _durable_unlink_at(destination_fd, MANIFEST_FILENAME)
        raise
    finally:
        for tour_fd in tour_fds.values():
            os.close(tour_fd)
        os.close(destination_fd)
        os.close(source_fd)


def _revoke_publication_pointers(
    pointers: Sequence[tuple[int, str]],
) -> None:
    """Durably revoke pointers from exact transaction roots, never replacement paths."""

    failures: list[ArtifactLineageError] = []
    for root_fd, filename in pointers:
        try:
            _durable_unlink_at(root_fd, filename)
        except (ArtifactLineageError, OSError) as exc:
            failures.append(_coerce_error(exc))
    if failures:
        primary = failures[0]
        raise ArtifactLineageError(
            primary.reason,
            f"could not revoke {len(failures)} failed-publication pointer(s)",
            path=primary.path,
        ) from primary


def _require_mirror_identity(
    expected: ValidatedRelease,
    mirrored: MirrorResult,
) -> None:
    if (
        mirrored.release_id != expected.release_id
        or mirrored.manifest_sha256 != expected.manifest_sha256
        or mirrored.manifest_bytes != expected.manifest_bytes
    ):
        raise ArtifactLineageError(
            LineageReason.ARTIFACT_MISMATCH,
            "mirror source identity differs from the accepted publication candidate",
        )


def _postvalidate_publication_identity(
    expected: AcceptedRelease,
    roots: _PublicationRoots,
) -> None:
    """Bracket exact destination proof with repeated exact accepted-source proofs."""

    for _ in range(2):
        _validate_open_directory_binding(roots.source, roots.source_fd)
        source = load_accepted_release(roots.source)
        _require_accepted_identity(
            expected.release,
            expected.receipt_bytes,
            source,
            label="publication source release",
        )
        _validate_open_directory_binding(roots.source, roots.source_fd)

        _validate_open_directory_binding(roots.destination, roots.destination_fd)
        destination = validate_public_release(roots.destination)
        _require_release_identity(
            expected.release,
            destination,
            label="publication destination release",
        )
        _validate_open_directory_binding(roots.destination, roots.destination_fd)


def publish_data_release(
    source_root: Path,
    destination_root: Path,
    *,
    semantic_gate_passed: bool,
    validator: str,
    on_copy: Callable[[str], None] | None = None,
) -> tuple[AcceptedRelease, MirrorResult]:
    """Accept one green candidate and exact-mirror it, or revoke every validity pointer.

    Acceptance belongs to this publication attempt.  If acceptance, copy, or destination
    postvalidation fails, neither the cache nor the public tree may continue advertising
    the candidate as valid.
    """

    with _publication_roots(Path(source_root), Path(destination_root)) as roots:
        try:
            accepted = accept_release(
                roots.source,
                semantic_gate_passed=semantic_gate_passed,
                validator=validator,
                _root_fd=roots.source_fd,
            )
            _validate_open_directory_binding(roots.source, roots.source_fd)
            mirrored = mirror_release(
                roots.source,
                roots.destination,
                require_accepted=True,
                on_copy=on_copy,
                _source_root_fd=roots.source_fd,
                _destination_root_fd=roots.destination_fd,
            )
            _require_mirror_identity(accepted.release, mirrored)
            _postvalidate_publication_identity(accepted, roots)
            return accepted, mirrored
        except Exception as exc:
            try:
                _revoke_publication_pointers((
                    (roots.source_fd, ACCEPTANCE_FILENAME),
                    (roots.source_fd, MANIFEST_FILENAME),
                    (roots.destination_fd, MANIFEST_FILENAME),
                ))
            except (ArtifactLineageError, OSError) as cleanup_error:
                raise cleanup_error from exc
            raise


def publish_web_release(
    source_root: Path,
    destination_root: Path,
    *,
    on_copy: Callable[[str], None] | None = None,
) -> MirrorResult:
    """Exact-mirror an already accepted cache release; web scope never accepts.

    A source/validation/copy failure revokes only the destination validity pointer.  The
    source acceptance remains intact for a later publication retry.
    """

    with _publication_roots(Path(source_root), Path(destination_root)) as roots:
        try:
            accepted = load_accepted_release(roots.source)
            _validate_open_directory_binding(roots.source, roots.source_fd)
            mirrored = mirror_release(
                roots.source,
                roots.destination,
                require_accepted=True,
                on_copy=on_copy,
                _source_root_fd=roots.source_fd,
                _destination_root_fd=roots.destination_fd,
            )
            _require_mirror_identity(accepted.release, mirrored)
            _postvalidate_publication_identity(accepted, roots)
            return mirrored
        except Exception as exc:
            try:
                _revoke_publication_pointers((
                    (roots.destination_fd, MANIFEST_FILENAME),
                ))
            except (ArtifactLineageError, OSError) as cleanup_error:
                raise cleanup_error from exc
            raise


def inspect_release(
    root: Path,
    *,
    require_accepted: bool = True,
    observed_at: datetime | None = None,
) -> LineageState:
    """Return stable typed enforcement state for health and gate reporting."""

    try:
        release = validate_release(
            root, require_accepted=require_accepted, observed_at=observed_at
        )
    except (ArtifactLineageError, OSError) as exc:
        error = _coerce_error(exc)
        if error.reason == LineageReason.MANIFEST_MISSING:
            state = "missing"
        elif error.reason in {
            LineageReason.ACCEPTANCE_MISSING,
            LineageReason.ACCEPTANCE_INVALID,
            LineageReason.ACCEPTANCE_MISMATCH,
        }:
            state = "unaccepted"
        else:
            state = "invalid"
        return LineageState(
            state=state,
            release=None,
            issues=(_issue_for(error),),
        )
    return LineageState(
        state="accepted" if isinstance(release, AcceptedRelease) else "valid",
        release=release,
    )


def lineage_health_summary(root: Path) -> dict:
    """Return the small, stable lineage block embedded by the health writer.

    Details stay in :func:`inspect_release` issues.  This summary deliberately has only
    five top-level fields so its public contract cannot accrete private receipt evidence.
    """

    state = inspect_release(root, require_accepted=True)
    release: ValidatedRelease | None
    if isinstance(state.release, AcceptedRelease):
        release = state.release.release
    else:
        release = None
    return {
        "schema": ARTIFACT_LINEAGE_SCHEMA,
        "status": state.state,
        "releaseId": release.release_id if release is not None else None,
        "manifestSha256": release.manifest_sha256 if release is not None else None,
        "tours": list(TOURS),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Workflow entry point for mandatory accepted-release publication."""

    parser = argparse.ArgumentParser(prog="python -m tennis_model.artifact_lineage")
    subparsers = parser.add_subparsers(dest="command", required=True)
    publish = subparsers.add_parser("publish")
    publish.add_argument("--scope", choices=("data", "web"), required=True)
    publish.add_argument("--semantic-gate-passed", action="store_true")
    publish.add_argument("--validator")
    publish.add_argument("--source", type=Path)
    publish.add_argument("--destination", type=Path)
    args = parser.parse_args(argv)

    from .config import OUTPUT_DIR, WEB_DATA_DIR

    source = args.source or OUTPUT_DIR
    destination = args.destination or WEB_DATA_DIR
    if args.scope == "data":
        if not args.semantic_gate_passed:
            parser.error("data publication requires --semantic-gate-passed")
        if not args.validator:
            parser.error("data publication requires --validator")
    else:
        if args.semantic_gate_passed or args.validator is not None:
            parser.error("web publication never accepts a candidate")

    try:
        if args.scope == "data":
            _, mirrored = publish_data_release(
                source,
                destination,
                semantic_gate_passed=True,
                validator=args.validator,
            )
        else:
            mirrored = publish_web_release(source, destination)
    except Exception as exc:  # noqa: BLE001 - CLI serializes the stable typed failure
        issue = _issue_for(_coerce_error(exc))
        diagnostic = {
            "schema": "artifact-lineage-publication-v1",
            "status": "failed",
            "releaseId": None,
            "issues": [issue.as_dict()],
        }
        print(json.dumps(diagnostic, sort_keys=True, separators=(",", ":")), flush=True)
        return 1

    diagnostic = {
        "schema": "artifact-lineage-publication-v1",
        "status": "published",
        "releaseId": mirrored.release_id,
        "issues": [],
    }
    print(json.dumps(diagnostic, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


def exact_file_identity(
    path: Path, *, trusted_root: Path | None = None
) -> tuple[int, str]:
    """Return size and SHA-256 of the exact bytes read from one regular file."""

    raw = _read_regular_file(
        Path(path), MAX_ARTIFACT_BYTES, trusted_root=trusted_root
    )
    return len(raw), hashlib.sha256(raw).hexdigest()


def validate_public_release(
    root: Path, *, observed_at: datetime | None = None
) -> ValidatedRelease:
    """Validate the exact public graph without requiring private predictor siblings."""

    root = Path(root)
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.exists() and not manifest_path.is_symlink():
        raise ArtifactLineageError(
            LineageReason.MANIFEST_MISSING, "release manifest is absent"
        )
    try:
        raw = _read_regular_file(
            manifest_path, MAX_MANIFEST_BYTES, trusted_root=root
        )
        manifest = _strict_json_loads(raw, reason=LineageReason.MANIFEST_INVALID)
    except ArtifactLineageError:
        raise
    except OSError as exc:
        raise ArtifactLineageError(
            LineageReason.IO_ERROR, "release manifest is unreadable"
        ) from exc
    _validate_public_manifest_against_graph(
        manifest, root, observed_at=observed_at, exact_public=True
    )
    return ValidatedRelease(
        root=_lexical_absolute(root),
        manifest=manifest,
        manifest_bytes=raw,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )


def _validate_manifest_against_graph(
    manifest: object,
    root: Path,
    *,
    observed_at: datetime | None = None,
) -> None:
    _validate_public_manifest_against_graph(
        manifest, root, observed_at=observed_at
    )
    for tour in TOURS:
        try:
            _validate_meta_predictor_binding(root, tour)
        except ArtifactLineageError as exc:
            raise _scoped_lineage_error(exc, tour) from exc


def _validate_public_manifest_against_graph(
    manifest: object,
    root: Path,
    *,
    observed_at: datetime | None = None,
    exact_public: bool = False,
) -> None:
    _validate_manifest_contract(manifest, observed_at=observed_at)
    assert isinstance(manifest, dict)
    discovered = {}
    meta_artifact_ids = {}
    for tour in TOURS:
        try:
            discovered.update(discover_tour_artifacts(root, tour))
            meta_identity = _validate_public_meta_identity(root, tour)
        except ArtifactLineageError as exc:
            raise _scoped_lineage_error(exc, tour) from exc
        meta_artifact_ids[tour] = meta_identity["artifactId"]

    records = manifest["artifacts"]
    declared = {record["path"]: record["role"] for record in records}
    if declared != discovered:
        missing = sorted(set(discovered) - set(declared))
        extra = sorted(set(declared) - set(discovered))
        detail = "manifest artifact set does not match the discovered public graph"
        path = (missing or extra or [None])[0]
        raise ArtifactLineageError(LineageReason.GRAPH_INVALID, detail, path=path)
    if exact_public:
        _validate_exact_public_files(root, set(declared))

    release_id = manifest["releaseId"]
    records_by_path = {record["path"]: record for record in records}
    for tour, artifact_id in meta_artifact_ids.items():
        meta_path = f"{tour}/meta.json"
        meta_record = records_by_path[meta_path]
        if (
            meta_record["originRelease"] != release_id
            or meta_record["predictorArtifactId"] != artifact_id
        ):
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "meta artifact record is not bound to its current predictor identity",
                path=meta_path,
            )
        for record in records:
            if (
                record["path"].startswith(f"{tour}/")
                and record["originRelease"] == release_id
                and record["predictorArtifactId"] != artifact_id
            ):
                raise ArtifactLineageError(
                    LineageReason.CONTRACT_INVALID,
                    "current-origin artifact uses a predictor identity unlike meta.json",
                    path=record["path"],
                )

    total = 0
    for record in records:
        path = record["path"]
        try:
            size, digest = exact_file_identity(
                _safe_join(root, path), trusted_root=root
            )
        except ArtifactLineageError as exc:
            tour = path.split("/", 1)[0]
            raise ArtifactLineageError(
                exc.reason,
                exc.detail,
                path=path,
                tour=tour,
            ) from exc
        except FileNotFoundError as exc:
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISSING,
                "declared artifact is absent",
                path=path,
            ) from exc
        except OSError as exc:
            raise ArtifactLineageError(
                LineageReason.IO_ERROR,
                "declared artifact is unreadable",
                path=path,
            ) from exc
        total += size
        if total > MAX_RELEASE_BYTES:
            raise ArtifactLineageError(
                LineageReason.BOUNDS_EXCEEDED, "release artifact bytes exceed the cap"
            )
        if size != record["bytes"] or digest != record["sha256"]:
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISMATCH,
                "declared artifact bytes do not match the manifest",
                path=path,
            )


def _validate_manifest_contract(
    manifest: object, *, observed_at: datetime | None = None
) -> None:
    if not isinstance(manifest, dict) or set(manifest) != _MANIFEST_FIELDS:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "manifest top-level fields do not match artifact-lineage-v1",
        )
    if manifest["schema"] != ARTIFACT_LINEAGE_SCHEMA:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "manifest schema is unsupported"
        )
    release_id = manifest["releaseId"]
    _validate_uuid4(release_id, "release id")
    parent = manifest["parent"]
    if parent is not None:
        _validate_uuid4(parent, "parent release id")
        if parent == release_id:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID, "a release cannot parent itself"
            )
    created = _parse_utc(manifest["createdAt"], "createdAt")
    observed = (observed_at or datetime.now(UTC)).astimezone(UTC)
    if created > observed + MAX_FUTURE_SKEW:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "manifest is implausibly future-dated"
        )
    if manifest["mode"] not in RELEASE_MODES:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "manifest mode is unknown"
        )
    if manifest["mode"] == "quick" and parent is None:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "quick manifest requires an accepted parent release",
        )
    artifacts = manifest["artifacts"]
    if (
        not isinstance(artifacts, list)
        or not artifacts
        or len(artifacts) > MAX_ARTIFACTS
    ):
        raise ArtifactLineageError(
            LineageReason.BOUNDS_EXCEEDED, "manifest artifact list is empty or oversized"
        )
    paths = []
    tours = set()
    for record in artifacts:
        if not isinstance(record, dict) or set(record) != _ARTIFACT_FIELDS:
            raise ArtifactLineageError(
                LineageReason.CONTRACT_INVALID,
                "artifact record fields do not match artifact-lineage-v1",
            )
        path = _validate_artifact_record(record)
        paths.append(path)
        tours.add(path.split("/", 1)[0])
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "artifact records must be uniquely and exactly sorted by path",
        )
    if tours != set(TOURS):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "manifest must cover both tours"
        )
    if parent is None and any(
        record["originRelease"] != release_id for record in artifacts
    ):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "bootstrap artifacts must originate in their release",
        )


def _validate_artifact_record(record: dict) -> str:
    path = record["path"]
    tour, filename = _split_artifact_path(path)
    role = record["role"]
    if role not in ARTIFACT_ROLES:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "artifact role is unknown", path=path
        )
    expected_role = _role_for_filename(filename)
    if expected_role is not None and role != expected_role:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "artifact role does not match its path",
            path=path,
        )
    if expected_role is None:
        _validate_dynamic_filename(filename, role)
    size = record["bytes"]
    if (
        not isinstance(size, int)
        or isinstance(size, bool)
        or size <= 0
        or size > MAX_ARTIFACT_BYTES
    ):
        raise ArtifactLineageError(
            LineageReason.BOUNDS_EXCEEDED, "artifact byte count is invalid", path=path
        )
    if not isinstance(record["sha256"], str) or not _SHA256_RE.fullmatch(
        record["sha256"]
    ):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "artifact SHA-256 is invalid", path=path
        )
    _validate_bounded_identity(record["producer"], "producer", MAX_PRODUCER_CHARS)
    source = record["sourceFingerprint"]
    if not isinstance(source, str) or not _SOURCE_FINGERPRINT_RE.fullmatch(source):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID,
            "artifact source fingerprint is invalid",
            path=path,
        )
    _validate_uuid4(record["predictorArtifactId"], "predictor artifact id")
    _validate_uuid4(record["originRelease"], "origin release id")
    # Keep the local variable use explicit: splitting also validates tour membership.
    assert tour in TOURS
    return path


def _load_acceptance(
    release: ValidatedRelease, *, observed_at: datetime | None = None
) -> AcceptedRelease:
    path = release.root / ACCEPTANCE_FILENAME
    if not path.exists() and not path.is_symlink():
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_MISSING, "release acceptance receipt is absent"
        )
    try:
        raw = _read_regular_file(
            path, MAX_ACCEPTANCE_BYTES, trusted_root=release.root
        )
        receipt = _strict_json_loads(raw, reason=LineageReason.ACCEPTANCE_INVALID)
    except ArtifactLineageError:
        raise
    except OSError as exc:
        raise ArtifactLineageError(
            LineageReason.IO_ERROR, "release acceptance receipt is unreadable"
        ) from exc
    _validate_acceptance_contract(receipt, observed_at=observed_at)
    if (
        receipt["releaseId"] != release.release_id
        or receipt["manifestSha256"] != release.manifest_sha256
    ):
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_MISMATCH,
            "acceptance receipt does not bind the current manifest",
        )
    if _parse_utc(receipt["acceptedAt"], "acceptedAt") < _parse_utc(
        release.manifest["createdAt"], "createdAt"
    ):
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID,
            "acceptance predates the bound release",
        )
    return AcceptedRelease(release=release, receipt=receipt, receipt_bytes=raw)


def _validate_acceptance_contract(
    receipt: object, *, observed_at: datetime | None = None
) -> None:
    if not isinstance(receipt, dict) or set(receipt) != _ACCEPTANCE_FIELDS:
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID,
            "acceptance fields do not match artifact-lineage-acceptance-v1",
        )
    if receipt["schema"] != ACCEPTANCE_SCHEMA:
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID, "acceptance schema is unsupported"
        )
    try:
        _validate_uuid4(receipt["releaseId"], "accepted release id")
    except ArtifactLineageError as exc:
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID, exc.detail
        ) from exc
    if not isinstance(receipt["manifestSha256"], str) or not _SHA256_RE.fullmatch(
        receipt["manifestSha256"]
    ):
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID, "acceptance manifest SHA-256 is invalid"
        )
    try:
        accepted = _parse_utc(receipt["acceptedAt"], "acceptedAt")
    except ArtifactLineageError as exc:
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID, exc.detail
        ) from exc
    observed = (observed_at or datetime.now(UTC)).astimezone(UTC)
    if accepted > observed + MAX_FUTURE_SKEW:
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID,
            "acceptance is implausibly future-dated",
        )
    try:
        _validate_bounded_identity(
            receipt["validator"], "validator", MAX_VALIDATOR_CHARS
        )
    except ArtifactLineageError as exc:
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_INVALID, exc.detail
        ) from exc


def _matrix_references(payload: object) -> list[tuple[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("surfaces"), dict):
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID, "matrix index surfaces must be an object"
        )
    refs = []
    for surface, formats in payload["surfaces"].items():
        if not isinstance(surface, str) or not isinstance(formats, dict):
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID, "matrix index surface entry is malformed"
            )
        for best_of, filename in formats.items():
            if not isinstance(best_of, str) or not isinstance(filename, str):
                raise ArtifactLineageError(
                    LineageReason.GRAPH_INVALID,
                    "matrix index format reference is malformed",
                )
            refs.append((filename, ROLE_MATRIX_SHARD))
    return _bounded_references(refs, "matrix")


def _profile_references(payload: object) -> list[tuple[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), list):
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID, "profile index profiles must be an array"
        )
    refs = []
    for row in payload["profiles"]:
        if not isinstance(row, dict) or not isinstance(row.get("file"), str):
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID, "profile index reference is malformed"
            )
        refs.append((row["file"], ROLE_PROFILE_SHARD))
    return _bounded_references(refs, "profile")


def _scenario_references(payload: object) -> list[tuple[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID, "scenario index events must be an array"
        )
    refs = []
    for row in payload["events"]:
        if not isinstance(row, dict) or not isinstance(row.get("file"), str):
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID, "scenario index reference is malformed"
            )
        refs.append((row["file"], ROLE_SCENARIO_SHARD))
    return _bounded_references(refs, "scenario")


def _upcoming_references(payload: object) -> list[tuple[str, str]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID, "upcoming index events must be an array"
        )
    refs = []
    for row in payload["events"]:
        if not isinstance(row, dict):
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID, "upcoming index event is malformed"
            )
        event_file, evidence_file = row.get("file"), row.get("evidenceFile")
        if not isinstance(event_file, str) or not isinstance(evidence_file, str):
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID, "upcoming index references are malformed"
            )
        refs.extend((
            (event_file, ROLE_UPCOMING_EVENT),
            (evidence_file, ROLE_UPCOMING_EVIDENCE),
        ))
    return _bounded_references(refs, "upcoming")


def _bounded_references(
    references: list[tuple[str, str]], graph: str
) -> list[tuple[str, str]]:
    if len(references) > MAX_INDEX_REFERENCES:
        raise ArtifactLineageError(
            LineageReason.BOUNDS_EXCEEDED,
            f"{graph} index exceeds its reference cap",
        )
    return references


def _role_for_filename(filename: str) -> str | None:
    if filename in FIXED_PUBLIC_CORE:
        return ROLE_PUBLIC_CORE
    if filename in INDEX_FILES:
        return INDEX_FILES[filename]
    if filename in OPTIONAL_EVALUATION_FILES:
        return ROLE_EVALUATION
    return None


def _validate_dynamic_filename(filename: object, role: object) -> None:
    if not isinstance(filename, str) or role not in _DYNAMIC_FILENAME_RE:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID, "artifact filename/role is not public"
        )
    _validate_filename(filename)
    if not _DYNAMIC_FILENAME_RE[role].fullmatch(filename):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "artifact filename does not match its graph role",
            path=filename,
        )


def _artifact_path(tour: str, filename: str) -> str:
    _validate_tour(tour)
    _validate_filename(filename)
    return f"{tour}/{filename}"


def _split_artifact_path(path: object) -> tuple[str, str]:
    if not isinstance(path, str) or len(path) > len("wta/") + MAX_FILENAME_CHARS:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID, "artifact path is malformed"
        )
    if "\\" in path or path.count("/") != 1:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID, "artifact path must be one safe tour JSON path"
        )
    tour, filename = path.split("/", 1)
    _validate_tour(tour)
    _validate_filename(filename)
    return tour, filename


def _validate_filename(filename: object) -> None:
    if (
        not isinstance(filename, str)
        or len(filename) > MAX_FILENAME_CHARS
        or ".." in filename
        or not _FILENAME_RE.fullmatch(filename)
    ):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID, "artifact filename is unsafe or unbounded"
        )


def _validate_tour(tour: object) -> None:
    if tour not in TOURS:
        raise ArtifactLineageError(LineageReason.PATH_INVALID, "artifact tour is unknown")


def _lexical_absolute(path: Path) -> Path:
    """Normalize separators and dot segments without following filesystem links."""

    return Path(os.path.abspath(os.fspath(path)))


def _trusted_path(path: Path, trusted_root: Path) -> tuple[Path, Path, Path]:
    """Return lexical absolute path/root/relative or reject authority escape."""

    absolute = _lexical_absolute(path)
    root = _lexical_absolute(trusted_root)
    try:
        relative = absolute.relative_to(root)
    except ValueError as exc:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "artifact path escapes its trusted root",
        ) from exc
    if not relative.parts:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "artifact path must name a leaf below its trusted root",
        )
    return absolute, root, relative


def _validate_public_producer_filename(filename: str) -> None:
    _validate_filename(filename)
    if filename in _PRIVATE_PRODUCER_JSON:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "private or root manifest JSON cannot be produced as a public artifact",
        )


def _public_trusted_root(trusted_root: Path | None) -> Path:
    if trusted_root is None:
        from .config import OUTPUT_DIR

        trusted_root = OUTPUT_DIR
    return _lexical_absolute(Path(trusted_root))


def _validate_public_write_path(
    tour: str,
    path: Path,
    *,
    trusted_root: Path | None,
) -> Path:
    """Bind public output to production or an explicitly authorized custom root."""

    _validate_tour(tour)
    _validate_public_producer_filename(path.name)
    trusted_root = _public_trusted_root(trusted_root)
    absolute, _, relative = _trusted_path(path, trusted_root)
    if relative.parts != (tour, path.name):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "public artifact path does not match its trusted tour root",
        )
    return absolute


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _normalize_filesystem_anchor_alias(path: Path) -> Path:
    """Expand only an administrator-owned alias directly below the filesystem root.

    macOS exposes temporary paths through ``/var -> /private/var`` (and similarly
    ``/tmp``).  Treating that immutable root entry as an application-controlled parent
    link would make secure temporary/custom outputs unusable.  No deeper component is
    resolved here; those remain subject to the strict descriptor walk below.
    """

    if len(path.parts) < 2:
        return path
    anchor = Path(path.anchor)
    first = anchor / path.parts[1]
    try:
        first_stat = os.lstat(first)
    except OSError:
        return path
    if not stat.S_ISLNK(first_stat.st_mode):
        return path
    anchor_stat = os.stat(anchor)
    if anchor_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "writable filesystem root cannot authorize a directory alias",
        )
    target = Path(os.readlink(first))
    if not target.is_absolute():
        target = first.parent / target
    expanded = Path(os.path.abspath(os.fspath(target)))
    return expanded.joinpath(*path.parts[2:])


def _open_directory_without_symlinks(directory: Path, *, create: bool) -> int:
    """Open one absolute directory component-by-component and return a stable fd.

    Directory-relative stat/open identity checks are the portable no-follow fallback:
    even where ``O_NOFOLLOW`` is unavailable, swapping a checked component for a link
    either changes the opened inode or is detected by the second no-follow stat.
    """

    absolute = _normalize_filesystem_anchor_alias(
        Path(os.path.abspath(os.fspath(directory)))
    )
    if not absolute.is_absolute() or not absolute.anchor:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "public artifact parent must be an absolute local path",
        )

    descriptor: int | None = None
    try:
        descriptor = os.open(absolute.anchor, _directory_open_flags())
        if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "filesystem anchor is not a directory",
            )
        for component in absolute.parts[1:]:
            try:
                entry = os.stat(
                    component,
                    dir_fd=descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(component, mode=0o755, dir_fd=descriptor)
                except FileExistsError:
                    pass
                else:
                    try:
                        os.fsync(descriptor)
                    except OSError as exc:
                        raise ArtifactLineageError(
                            LineageReason.IO_ERROR,
                            "new public artifact parent could not be synced",
                        ) from exc
                entry = os.stat(
                    component,
                    dir_fd=descriptor,
                    follow_symlinks=False,
                )
            if stat.S_ISLNK(entry.st_mode) or not stat.S_ISDIR(entry.st_mode):
                raise ArtifactLineageError(
                    LineageReason.PATH_INVALID,
                    "public artifact parent components must be real directories",
                )

            child = os.open(
                component,
                _directory_open_flags(),
                dir_fd=descriptor,
            )
            try:
                opened = os.fstat(child)
                entry_after = os.stat(
                    component,
                    dir_fd=descriptor,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISDIR(opened.st_mode)
                    or not _same_file_identity(entry, opened)
                    or not _same_file_identity(entry_after, opened)
                ):
                    raise ArtifactLineageError(
                        LineageReason.PATH_INVALID,
                        "public artifact parent changed during traversal",
                    )
            except Exception:
                os.close(child)
                raise
            previous = descriptor
            descriptor = child
            os.close(previous)
        return descriptor
    except ArtifactLineageError:
        if descriptor is not None:
            os.close(descriptor)
        raise
    except (NotImplementedError, OSError, TypeError) as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "public artifact parent traversal failed",
        ) from exc


def _open_or_create_directory_child(
    parent_fd: int,
    name: str,
    *,
    label: str,
) -> int:
    """Open one real child directory, creating only that descriptor-relative leaf."""

    _validate_regular_leaf_name(name)
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        try:
            os.mkdir(name, mode=0o755, dir_fd=parent_fd)
        except FileExistsError:
            pass
        except (NotImplementedError, OSError, TypeError) as exc:
            raise ArtifactLineageError(
                LineageReason.IO_ERROR,
                f"{label} could not be created",
            ) from exc
        else:
            try:
                os.fsync(parent_fd)
            except OSError as exc:
                raise ArtifactLineageError(
                    LineageReason.IO_ERROR,
                    f"{label} creation could not be synced",
                ) from exc
        try:
            entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except (NotImplementedError, OSError, TypeError) as exc:
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                f"{label} changed during creation",
            ) from exc
    except (NotImplementedError, OSError, TypeError) as exc:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            f"{label} cannot be inspected",
        ) from exc

    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISDIR(entry.st_mode):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            f"{label} must be a real directory",
        )
    try:
        child = os.open(name, _directory_open_flags(), dir_fd=parent_fd)
    except (NotImplementedError, OSError, TypeError) as exc:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            f"{label} cannot be opened safely",
        ) from exc
    try:
        opened = os.fstat(child)
        entry_after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not _same_file_identity(entry, opened)
            or not _same_file_identity(entry_after, opened)
        ):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                f"{label} changed during secure open",
            )
    except ArtifactLineageError:
        os.close(child)
        raise
    except (NotImplementedError, OSError, TypeError) as exc:
        os.close(child)
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            f"{label} cannot be verified",
        ) from exc
    return child


def initialize_release_root(root: Path) -> Path:
    """Securely initialize only a missing release-root leaf and its two tour children.

    The configured root's parent must already exist and every ancestor must be a real
    directory. This deliberately does not use the general recursive-create path: a typo
    or missing higher ancestor cannot authorize creation of an unexpected directory tree.
    """

    root = _normalize_filesystem_anchor_alias(_lexical_absolute(Path(root)))
    if root == Path(root.anchor) or not root.name:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "release root must be a bounded directory below an existing parent",
        )
    parent_fd = _open_directory_without_symlinks(root.parent, create=False)
    root_fd: int | None = None
    try:
        root_fd = _open_or_create_directory_child(
            parent_fd,
            root.name,
            label="release root",
        )
        for tour in TOURS:
            tour_fd = _open_or_create_directory_child(
                root_fd,
                tour,
                label=f"{tour} release directory",
            )
            try:
                _validate_open_directory_binding(root / tour, tour_fd)
            finally:
                os.close(tour_fd)
        _validate_open_directory_binding(root, root_fd)
    finally:
        if root_fd is not None:
            os.close(root_fd)
        os.close(parent_fd)
    return root


def _validate_public_write_leaf(parent_fd: int, filename: str) -> None:
    """Reject an existing non-regular or linked destination without following it."""

    _validate_filename(filename)
    _validate_regular_write_leaf(parent_fd, filename)


def _validate_regular_leaf_name(filename: str) -> None:
    if (
        not filename
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or len(filename) > 255
    ):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID, "artifact destination leaf is unsafe"
        )


def _validate_regular_write_leaf(parent_fd: int, filename: str) -> None:
    _validate_regular_leaf_name(filename)
    try:
        leaf = os.stat(filename, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    except (NotImplementedError, OSError, TypeError) as exc:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "public artifact destination cannot be inspected",
        ) from exc
    if stat.S_ISLNK(leaf.st_mode) or not stat.S_ISREG(leaf.st_mode):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "public artifact destination must be a regular file or absent",
        )


def _validate_open_directory_binding(directory: Path, expected_fd: int) -> None:
    """Prove the lexical parent still names the stable directory just written."""

    observed_fd = _open_directory_without_symlinks(directory, create=False)
    try:
        if not _same_file_identity(os.fstat(expected_fd), os.fstat(observed_fd)):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "public artifact parent changed before completion proof",
            )
    finally:
        os.close(observed_fd)


@contextmanager
def _borrow_bound_root_fd(root: Path, supplied_fd: int | None):
    """Hold one exact no-follow root identity across validation and pointer writes."""

    owns_fd = supplied_fd is None
    root_fd = (
        _open_directory_without_symlinks(root, create=False)
        if supplied_fd is None
        else supplied_fd
    )
    try:
        if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "release root descriptor is not a directory",
            )
        _validate_open_directory_binding(root, root_fd)
        yield root_fd
    finally:
        if owns_fd:
            os.close(root_fd)


def _require_release_identity(
    expected: ValidatedRelease,
    observed: ValidatedRelease,
    *,
    label: str,
) -> None:
    """Require the exact release id and manifest bytes, not one mutable path name."""

    if (
        observed.release_id != expected.release_id
        or observed.manifest_sha256 != expected.manifest_sha256
        or observed.manifest_bytes != expected.manifest_bytes
    ):
        raise ArtifactLineageError(
            LineageReason.ARTIFACT_MISMATCH,
            f"{label} changed during publication",
        )


def _require_accepted_identity(
    expected_release: ValidatedRelease,
    expected_receipt_bytes: bytes,
    observed: AcceptedRelease,
    *,
    label: str,
) -> None:
    """Require one exact manifest and its exact acceptance receipt bytes."""

    _require_release_identity(expected_release, observed.release, label=label)
    if observed.receipt_bytes != expected_receipt_bytes:
        raise ArtifactLineageError(
            LineageReason.ACCEPTANCE_MISMATCH,
            f"{label} acceptance changed during publication",
        )


def _tour_directory(root: Path, tour: str) -> Path:
    candidate = _safe_join(root, tour)
    if candidate.is_symlink():
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID, "tour artifact directory cannot be a symlink"
        )
    return candidate


def _safe_join(root: Path, relative: str) -> Path:
    root = _lexical_absolute(Path(root))
    if not isinstance(relative, str) or relative.startswith(("/", "\\")):
        raise ArtifactLineageError(LineageReason.PATH_INVALID, "unsafe relative path")
    parts = relative.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts) or "\\" in relative:
        raise ArtifactLineageError(LineageReason.PATH_INVALID, "unsafe relative path")
    candidate = root.joinpath(*parts)
    return candidate


def _validate_root_relationship(
    source: Path, destination: Path, *, allow_equal: bool
) -> tuple[Path, Path]:
    """Reject symlink roots and destructive ancestor overlap before any mutation."""

    source, destination = _normalize_root_relationship(source, destination)
    if source == destination:
        source_fd = _open_directory_without_symlinks(source, create=False)
        os.close(source_fd)
        if allow_equal:
            return source, destination
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID, "release source and destination must differ"
        )
    if (
        source in destination.parents
        or destination in source.parents
    ):
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "release source and destination cannot contain one another",
        )
    source_fd = _open_directory_without_symlinks(source, create=False)
    try:
        destination_fd = _open_directory_without_symlinks(destination, create=True)
        try:
            if _same_file_identity(os.fstat(source_fd), os.fstat(destination_fd)):
                raise ArtifactLineageError(
                    LineageReason.PATH_INVALID,
                    "release source and destination resolve to one directory",
                )
        finally:
            os.close(destination_fd)
    finally:
        os.close(source_fd)
    return source, destination


def _normalize_root_relationship(source: Path, destination: Path) -> tuple[Path, Path]:
    """Normalize no-follow authority names and reject lexical destructive overlap."""

    source = _normalize_filesystem_anchor_alias(_lexical_absolute(source))
    destination = _normalize_filesystem_anchor_alias(_lexical_absolute(destination))
    if source == destination:
        return source, destination
    if source in destination.parents or destination in source.parents:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "release source and destination cannot contain one another",
        )
    return source, destination


def _preflight_publication_relationship(
    source: Path,
    destination: Path,
) -> tuple[Path, Path]:
    """Read-only proof that publisher roots are real and disjoint.

    A missing destination leaf is allowed, but its parent must already be a real secure
    directory.  This check never accepts, revokes, creates, or otherwise mutates either
    release tree.
    """

    source, destination = _normalize_root_relationship(source, destination)
    if source == destination:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "release source and destination must differ",
        )
    _validate_regular_leaf_name(destination.name)
    source_fd = _open_directory_without_symlinks(source, create=False)
    destination_fd: int | None = None
    parent_fd: int | None = None
    try:
        parent_fd = _open_directory_without_symlinks(
            destination.parent,
            create=False,
        )
        try:
            destination_entry = os.stat(
                destination.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return source, destination
        except (NotImplementedError, OSError, TypeError) as exc:
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "publication destination cannot be inspected",
            ) from exc
        if (
            stat.S_ISLNK(destination_entry.st_mode)
            or not stat.S_ISDIR(destination_entry.st_mode)
        ):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "publication destination must be a real directory or absent",
            )
        destination_fd = _open_directory_without_symlinks(
            destination,
            create=False,
        )
        if _same_file_identity(os.fstat(source_fd), os.fstat(destination_fd)):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "release source and destination resolve to one directory",
            )
        return source, destination
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        if parent_fd is not None:
            os.close(parent_fd)
        os.close(source_fd)


@contextmanager
def _publication_roots(source: Path, destination: Path):
    """Bind exact source/destination descriptors for one publication transaction."""

    source, destination = _preflight_publication_relationship(source, destination)
    source_fd = _open_directory_without_symlinks(source, create=False)
    destination_fd: int | None = None
    try:
        destination_fd = _open_directory_without_symlinks(destination, create=True)
        if _same_file_identity(os.fstat(source_fd), os.fstat(destination_fd)):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "release source and destination resolve to one directory",
            )
        _validate_open_directory_binding(source, source_fd)
        _validate_open_directory_binding(destination, destination_fd)
        yield _PublicationRoots(
            source=source,
            destination=destination,
            source_fd=source_fd,
            destination_fd=destination_fd,
        )
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        os.close(source_fd)


def _preflight_destination_tours(destination: Path) -> None:
    """Prove tour parents are real, distinct directories before the first write."""

    for tour in TOURS:
        _preflight_destination_tour(destination, tour)


def _preflight_destination_tour(destination: Path, tour: str) -> None:
    """Reject a linked or non-directory destination tour before any cleanup."""

    _validate_tour(tour)
    tour_path = destination / tour
    if tour_path.is_symlink():
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "destination tour directory cannot be a symlink",
            path=tour,
        )
    if tour_path.exists() and not tour_path.is_dir():
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "destination tour path is not a directory",
            path=tour,
        )


def _open_destination_tour_fds(
    destination: Path,
    destination_fd: int,
) -> dict[str, int]:
    """Bind the two exact destination tour directories for the mirror transaction."""

    tour_fds: dict[str, int] = {}
    try:
        for tour in TOURS:
            tour_fd = _open_or_create_directory_child(
                destination_fd,
                tour,
                label=f"{tour} publication directory",
            )
            tour_fds[tour] = tour_fd
            _validate_open_directory_binding(destination / tour, tour_fd)
        return tour_fds
    except Exception:
        for tour_fd in tour_fds.values():
            os.close(tour_fd)
        raise


def _validate_destination_tour_bindings(
    destination: Path,
    tour_fds: Mapping[str, int],
) -> None:
    """Reject a renamed/replaced tour before any later lexical cleanup or proof."""

    for tour in TOURS:
        _validate_open_directory_binding(destination / tour, tour_fds[tour])


def _open_bound_directory_child(
    parent_fd: int,
    name: str,
    entry: os.stat_result,
) -> int:
    """Open one already-lstat'd real directory without accepting a name swap."""

    try:
        child_fd = os.open(name, _directory_open_flags(), dir_fd=parent_fd)
    except (NotImplementedError, OSError, TypeError) as exc:
        raise ArtifactLineageError(
            LineageReason.PATH_INVALID,
            "public cleanup directory cannot be opened safely",
        ) from exc
    try:
        opened = os.fstat(child_fd)
        after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not _same_file_identity(entry, opened)
            or not _same_file_identity(after, opened)
        ):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "public cleanup directory changed during secure open",
            )
        return child_fd
    except Exception:
        os.close(child_fd)
        raise


def _clear_directory_at(parent_fd: int, *, prefix: str) -> list[str]:
    """Remove one stale tree through its stable descriptor without following links."""

    try:
        names = sorted(os.listdir(parent_fd))
    except OSError as exc:
        raise ArtifactLineageError(
            LineageReason.IO_ERROR,
            "public cleanup directory cannot be listed",
        ) from exc
    removed: list[str] = []
    for name in names:
        _validate_regular_leaf_name(name)
        relative = f"{prefix}/{name}" if prefix else name
        try:
            entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "public cleanup entry cannot be inspected",
            ) from exc
        if stat.S_ISDIR(entry.st_mode) and not stat.S_ISLNK(entry.st_mode):
            child_fd = _open_bound_directory_child(parent_fd, name, entry)
            try:
                removed.extend(_clear_directory_at(child_fd, prefix=relative))
            finally:
                os.close(child_fd)
            try:
                os.rmdir(name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except OSError as exc:
                raise ArtifactLineageError(
                    LineageReason.IO_ERROR,
                    "stale public directory could not be removed",
                ) from exc
            removed.append(relative)
        else:
            _durable_unlink_at(parent_fd, name)
            removed.append(relative)
    return removed


def _clear_public_destination_at(
    destination_fd: int,
    tour_fds: Mapping[str, int],
) -> list[str]:
    """Empty only the bound attempted public tree, preserving root health.json."""

    removed: list[str] = []
    for tour in TOURS:
        removed.extend(_clear_directory_at(tour_fds[tour], prefix=tour))

    try:
        root_names = sorted(os.listdir(destination_fd))
    except OSError as exc:
        raise ArtifactLineageError(
            LineageReason.IO_ERROR,
            "public destination root cannot be listed",
        ) from exc
    for name in root_names:
        _validate_regular_leaf_name(name)
        entry = os.stat(name, dir_fd=destination_fd, follow_symlinks=False)
        if name in TOURS:
            if not _same_file_identity(entry, os.fstat(tour_fds[name])):
                raise ArtifactLineageError(
                    LineageReason.PATH_INVALID,
                    "destination tour changed during bound cleanup",
                    path=name,
                    tour=name,
                )
            continue
        if name == "health.json" and stat.S_ISREG(entry.st_mode):
            continue
        if stat.S_ISDIR(entry.st_mode) and not stat.S_ISLNK(entry.st_mode):
            child_fd = _open_bound_directory_child(destination_fd, name, entry)
            try:
                removed.extend(_clear_directory_at(child_fd, prefix=name))
            finally:
                os.close(child_fd)
            try:
                os.rmdir(name, dir_fd=destination_fd)
                os.fsync(destination_fd)
            except OSError as exc:
                raise ArtifactLineageError(
                    LineageReason.IO_ERROR,
                    "stale public root directory could not be removed",
                ) from exc
            removed.append(name)
        else:
            _durable_unlink_at(destination_fd, name)
            removed.append(name)
    return removed


def _prune_carried_tree_at(
    parent_fd: int,
    *,
    prefix: str,
    declared_json: set[str],
) -> list[str]:
    """Descriptor-bound equivalent of carry's symlink/undeclared-JSON cleanup."""

    try:
        names = sorted(os.listdir(parent_fd))
    except OSError as exc:
        raise ArtifactLineageError(
            LineageReason.IO_ERROR,
            "carried destination directory cannot be listed",
        ) from exc
    removed: list[str] = []
    for name in names:
        _validate_regular_leaf_name(name)
        relative = f"{prefix}/{name}" if prefix else name
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISLNK(entry.st_mode):
            _durable_unlink_at(parent_fd, name)
            removed.append(relative)
            continue
        if stat.S_ISDIR(entry.st_mode):
            child_fd = _open_bound_directory_child(parent_fd, name, entry)
            try:
                removed.extend(_prune_carried_tree_at(
                    child_fd,
                    prefix=relative,
                    declared_json=declared_json,
                ))
            finally:
                os.close(child_fd)
            continue
        if (
            name.endswith(".json")
            and relative != MANIFEST_FILENAME
            and relative not in declared_json
            and name not in PRIVATE_JSON_FILES
        ):
            _durable_unlink_at(parent_fd, name)
            removed.append(relative)
    return removed


def _prune_carried_destination_at(
    destination_fd: int,
    tour_fds: Mapping[str, int],
    declared_json: set[str],
) -> list[str]:
    """Prune the exact attempted cache tree without reopening lexical tour paths."""

    removed: list[str] = []
    for tour in TOURS:
        removed.extend(_prune_carried_tree_at(
            tour_fds[tour],
            prefix=tour,
            declared_json=declared_json,
        ))
    for name in sorted(os.listdir(destination_fd)):
        _validate_regular_leaf_name(name)
        entry = os.stat(name, dir_fd=destination_fd, follow_symlinks=False)
        if name in TOURS:
            if not _same_file_identity(entry, os.fstat(tour_fds[name])):
                raise ArtifactLineageError(
                    LineageReason.PATH_INVALID,
                    "carried destination tour changed during bound cleanup",
                    path=name,
                    tour=name,
                )
            continue
        relative = name
        if stat.S_ISLNK(entry.st_mode):
            _durable_unlink_at(destination_fd, name)
            removed.append(relative)
        elif stat.S_ISDIR(entry.st_mode):
            child_fd = _open_bound_directory_child(destination_fd, name, entry)
            try:
                removed.extend(_prune_carried_tree_at(
                    child_fd,
                    prefix=relative,
                    declared_json=declared_json,
                ))
            finally:
                os.close(child_fd)
        elif (
            name.endswith(".json")
            and name != MANIFEST_FILENAME
            and name not in declared_json
            and name not in PRIVATE_JSON_FILES
        ):
            _durable_unlink_at(destination_fd, name)
            removed.append(relative)
    return removed


def _load_artifact_json(root: Path, relative: str) -> object:
    path = _safe_join(root, relative)
    try:
        raw = _read_regular_file(
            path, MAX_ARTIFACT_BYTES, trusted_root=root
        )
    except FileNotFoundError as exc:
        raise ArtifactLineageError(
            LineageReason.ARTIFACT_MISSING,
            "public graph artifact is absent",
            path=relative,
        ) from exc
    except OSError as exc:
        raise ArtifactLineageError(
            LineageReason.IO_ERROR,
            "public graph artifact is unreadable",
            path=relative,
        ) from exc
    return _strict_json_loads(raw, reason=LineageReason.GRAPH_INVALID, path=relative)


def _validate_predictor_identity(root: Path, tour: str) -> dict:
    """Bind lineage to the strict private envelope without ever unpickling here."""

    from .model.artifact import (
        PredictorArtifactError,
        PredictorArtifactReason,
        validate_predictor_artifact_identity,
    )

    payload_path = _safe_join(root, f"{tour}/predictor.pkl")
    try:
        identity = validate_predictor_artifact_identity(payload_path, tour)
    except PredictorArtifactError as exc:
        if exc.reason is PredictorArtifactReason.PATH_INVALID:
            reason = LineageReason.PATH_INVALID
        elif exc.reason in {
            PredictorArtifactReason.ENVELOPE_IO,
            PredictorArtifactReason.PAYLOAD_IO,
            PredictorArtifactReason.PENDING_IO,
            PredictorArtifactReason.PUBLICATION_IO,
        }:
            reason = LineageReason.IO_ERROR
        else:
            reason = LineageReason.GRAPH_INVALID
        raise ArtifactLineageError(
            reason,
            f"predictor artifact identity is invalid ({exc.reason.value})",
        ) from exc
    if not isinstance(identity, dict):  # pragma: no cover - public helper contract guard
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "predictor artifact identity helper returned a malformed value",
        )
    try:
        _validate_uuid4(identity.get("artifactId"), "predictor envelope artifact id")
    except ArtifactLineageError as exc:
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "predictor envelope artifact identity is malformed",
        ) from exc
    return identity


def _validate_meta_predictor_binding(root: Path, tour: str) -> dict:
    """Prove public model age/tour/UUID against the strict private envelope."""

    meta_path = f"{tour}/meta.json"
    meta_identity = _validate_public_meta_identity(root, tour)
    artifact_id = meta_identity["artifactId"]
    predictor_identity = _validate_predictor_identity(root, tour)
    if predictor_identity["artifactId"] != artifact_id:
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "strict predictor envelope identity does not match meta.json",
            path=meta_path,
        )
    if meta_identity["trainedAt"] != predictor_identity.get("trainedAt"):
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "meta.json model age does not match the strict predictor envelope",
            path=meta_path,
        )
    return predictor_identity


def _validate_public_meta_identity(root: Path, tour: str) -> dict:
    """Validate the public half of the model identity chain."""

    meta_path = f"{tour}/meta.json"
    meta = _load_artifact_json(root, meta_path)
    if not isinstance(meta, dict) or meta.get("tour") != tour:
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "meta.json tour does not match its release tour",
            path=meta_path,
        )
    artifact_id = meta.get("predictorArtifactId")
    try:
        _validate_uuid4(artifact_id, "meta predictor artifact id")
    except ArtifactLineageError as exc:
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "meta.json lacks a valid predictor artifact identity",
            path=meta_path,
        ) from exc
    trained_at = meta.get("modelTrainedAt")
    try:
        parsed = _parse_utc(trained_at, "meta modelTrainedAt")
    except ArtifactLineageError as exc:
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "meta.json lacks a valid model training timestamp",
            path=meta_path,
        ) from exc
    if (
        not isinstance(trained_at, str)
        or len(trained_at) != 20
        or parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != trained_at
        or parsed > datetime.now(UTC) + MAX_FUTURE_SKEW
    ):
        raise ArtifactLineageError(
            LineageReason.GRAPH_INVALID,
            "meta.json model training timestamp is not canonical UTC",
            path=meta_path,
        )
    return {"artifactId": artifact_id, "trainedAt": trained_at}


def _strict_json_loads(
    raw: bytes,
    *,
    reason: LineageReason,
    path: str | None = None,
) -> object:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key")
            result[key] = value
        return result

    def reject_constant(token: str) -> None:
        raise ValueError(f"non-finite JSON constant {token}")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_constant,
        )
        _assert_json_bounds(value)
    except (RecursionError, UnicodeDecodeError, ValueError) as exc:
        raise ArtifactLineageError(reason, "file is not strict bounded JSON", path=path) from exc
    return value


def _assert_json_bounds(value: object) -> None:
    stack = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ValueError("JSON structure exceeds bounds")
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("JSON number is not finite")
        elif isinstance(item, int) and not isinstance(item, bool):
            try:
                finite_in_browser = math.isfinite(float(item))
            except OverflowError:
                finite_in_browser = False
            if not finite_in_browser:
                raise ValueError("JSON integer is not finite in the browser runtime")


def _read_regular_file(
    path: Path,
    limit: int,
    *,
    trusted_root: Path | None = None,
) -> bytes:
    path = _lexical_absolute(Path(path))
    if trusted_root is not None:
        _trusted_path(path, trusted_root)
    parent_fd = _open_directory_without_symlinks(path.parent, create=False)
    fd: int | None = None
    try:
        leaf_before = os.stat(
            path.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if stat.S_ISLNK(leaf_before.st_mode) or not stat.S_ISREG(leaf_before.st_mode):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID, "artifact path is not a regular file"
            )
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path.name, flags, dir_fd=parent_fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID, "artifact path is not a regular file"
            )
        if not _same_file_snapshot(leaf_before, before):
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISMATCH,
                "artifact changed before its exact bytes were read",
            )
        if before.st_size > limit:
            raise ArtifactLineageError(
                LineageReason.BOUNDS_EXCEEDED, "file exceeds its byte cap"
            )
        chunks = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        if len(raw) > limit:
            raise ArtifactLineageError(
                LineageReason.BOUNDS_EXCEEDED, "file exceeds its byte cap"
            )
        if (
            len(raw) != after.st_size
            or before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or before.st_ctime_ns != after.st_ctime_ns
        ):
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISMATCH,
                "file changed while its exact bytes were read",
            )
        try:
            leaf_after = os.stat(
                path.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISMATCH,
                "artifact path changed while its exact bytes were read",
            ) from exc
        if (
            stat.S_ISLNK(leaf_after.st_mode)
            or not stat.S_ISREG(leaf_after.st_mode)
            or not _same_file_snapshot(leaf_after, after)
        ):
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISMATCH,
                "artifact path changed while its exact bytes were read",
            )
        _validate_open_directory_binding(path.parent, parent_fd)
        return raw
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent_fd)


def _same_file_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev == right.st_dev
        and left.st_ino == right.st_ino
        and stat.S_IFMT(left.st_mode) == stat.S_IFMT(right.st_mode)
    )


def _same_file_snapshot(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare a path lstat with an opened descriptor without following a leaf link."""

    return (
        _same_file_identity(left, right)
        and left.st_size == right.st_size
        and left.st_mtime_ns == right.st_mtime_ns
        and left.st_ctime_ns == right.st_ctime_ns
    )


def _atomic_write_public_bytes(parent_fd: int, filename: str, raw: bytes) -> None:
    """Create, fsync, and rename one public file relative to a stable parent fd."""

    _validate_filename(filename)
    _atomic_replace_at(parent_fd, filename, raw)


def _atomic_replace_at(parent_fd: int, filename: str, raw: bytes) -> None:
    """Replace one leaf relative to a stable parent and durably clean failed temps."""

    _validate_regular_leaf_name(filename)
    temporary = f".{filename}.{uuid.uuid4()}.tmp"
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    temporary_fd: int | None = None
    try:
        temporary_fd = os.open(temporary, flags, 0o600, dir_fd=parent_fd)
        handle = os.fdopen(temporary_fd, "wb")
        temporary_fd = None
        with handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(
            temporary,
            filename,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
    finally:
        if temporary_fd is not None:
            os.close(temporary_fd)
        removed_temporary = False
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        else:
            removed_temporary = True
        if removed_temporary:
            os.fsync(parent_fd)


def _atomic_write_bytes(
    path: Path,
    raw: bytes,
    *,
    trusted_root: Path | None = None,
) -> None:
    """Descriptor-anchored atomic replace with a caller-bounded authority root."""

    path = _lexical_absolute(Path(path))
    if trusted_root is not None:
        _trusted_path(path, trusted_root)
    parent_fd = _open_directory_without_symlinks(path.parent, create=True)
    try:
        _validate_regular_write_leaf(parent_fd, path.name)
        _atomic_replace_at(parent_fd, path.name, raw)
        _validate_open_directory_binding(path.parent, parent_fd)
    finally:
        os.close(parent_fd)


def _durable_unlink(
    path: Path,
    *,
    trusted_root: Path | None = None,
) -> None:
    """Unlink relative to a stable parent and fsync even if the leaf is absent."""

    path = _lexical_absolute(Path(path))
    if trusted_root is not None:
        _trusted_path(path, trusted_root)
    parent_fd = _open_directory_without_symlinks(path.parent, create=True)
    try:
        _durable_unlink_at(parent_fd, path.name)
        _validate_open_directory_binding(path.parent, parent_fd)
    finally:
        os.close(parent_fd)


def _durable_unlink_at(parent_fd: int, filename: str) -> None:
    """Unlink one descriptor-relative leaf and always fsync the observed absence."""

    _validate_regular_leaf_name(filename)
    try:
        os.unlink(filename, dir_fd=parent_fd)
    except FileNotFoundError:
        pass
    os.fsync(parent_fd)


def _buffer_release_artifacts(
    release: ValidatedRelease,
) -> list[tuple[dict, bytes]]:
    buffered = []
    total = 0
    for record in release.records:
        raw = _read_regular_file(
            _safe_join(release.root, record["path"]),
            MAX_ARTIFACT_BYTES,
            trusted_root=release.root,
        )
        total += len(raw)
        if total > MAX_RELEASE_BYTES:
            raise ArtifactLineageError(
                LineageReason.BOUNDS_EXCEEDED, "release artifact bytes exceed the cap"
            )
        if (
            len(raw) != record["bytes"]
            or hashlib.sha256(raw).hexdigest() != record["sha256"]
        ):
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISMATCH,
                "artifact changed before copy",
                path=record["path"],
            )
        buffered.append((record, raw))
    return buffered


def _buffer_predictor_artifacts(root: Path) -> list[tuple[str, bytes]]:
    """Buffer already-validated private predictor pairs for cache carry-forward."""

    buffered = []
    total = 0
    for tour in TOURS:
        identity = _validate_predictor_identity(root, tour)
        payload_relative = f"{tour}/predictor.pkl"
        envelope_relative = f"{tour}/predictor.pkl.envelope"
        payload = _read_regular_file(
            _safe_join(root, payload_relative),
            MAX_PRIVATE_PREDICTOR_BYTES,
            trusted_root=root,
        )
        envelope = _read_regular_file(
            _safe_join(root, envelope_relative),
            MAX_PRIVATE_ENVELOPE_BYTES,
            trusted_root=root,
        )
        total += len(payload) + len(envelope)
        if total > 2 * (MAX_PRIVATE_PREDICTOR_BYTES + MAX_PRIVATE_ENVELOPE_BYTES):
            raise ArtifactLineageError(
                LineageReason.BOUNDS_EXCEEDED,
                "private predictor carry-forward exceeds its byte cap",
            )
        if (
            len(payload) != identity.get("payloadBytes")
            or hashlib.sha256(payload).hexdigest() != identity.get("payloadSha256")
        ):
            raise ArtifactLineageError(
                LineageReason.ARTIFACT_MISMATCH,
                "predictor payload changed after envelope validation",
            )
        # Envelope first makes any interrupted destination state fail closed; only the
        # following exact payload copy can make the pair valid.
        buffered.extend((
            (envelope_relative, envelope),
            (payload_relative, payload),
        ))
    return buffered


def _remove_undeclared_json(
    root: Path,
    declared: set[str],
    *,
    preserve_private: bool = False,
) -> list[str]:
    root = Path(root)
    removed = []
    if not root.exists():
        return removed
    manifest_path = root / MANIFEST_FILENAME
    for path in sorted(root.rglob("*.json")):
        if path == manifest_path:
            continue
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError as exc:  # pragma: no cover - defensive Path invariant
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID, "mirror cleanup escaped destination"
            ) from exc
        if (
            relative not in declared
            and not (preserve_private and path.name in PRIVATE_JSON_FILES)
        ):
            _durable_unlink(path, trusted_root=root)
            removed.append(relative)
    if not preserve_private:
        removed.extend(_remove_private_mirror_files(root))
    return removed


def _remove_private_mirror_files(root: Path) -> list[str]:
    removed = []
    for path in sorted(
        candidate
        for candidate in root.rglob("*")
        if (candidate.is_file() or candidate.is_symlink())
        and candidate.name in PRIVATE_MIRROR_FILES
    ):
        relative = path.relative_to(root).as_posix()
        _durable_unlink(path, trusted_root=root)
        removed.append(relative)
    return removed


def _remove_destination_symlinks(root: Path) -> list[str]:
    """Remove nested stale symlinks without following them outside the public root."""

    root = Path(root)
    if not root.exists():
        return []
    symlinks = sorted(
        (path for path in root.rglob("*") if path.is_symlink()),
        key=lambda path: (len(path.parts), path.as_posix()),
        reverse=True,
    )
    removed = []
    for path in symlinks:
        relative = path.relative_to(root).as_posix()
        _durable_unlink(path, trusted_root=root)
        removed.append(relative)
    return removed


def _remove_undeclared_public_files(root: Path, declared: set[str]) -> list[str]:
    """Leave only declared tour artifacts plus the separately-owned root health file."""

    root = Path(root)
    removed = []
    if not root.exists():
        return removed
    for path in sorted(root.rglob("*")):
        if not path.is_file() and not path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in declared or relative == "health.json":
            continue
        _durable_unlink(path, trusted_root=root)
        removed.append(relative)
    return removed


def _validate_exact_public_files(root: Path, declared: set[str]) -> None:
    """Reject every extra/symlinked public file after manifest publication."""

    root = Path(root)
    allowed = set(declared) | {MANIFEST_FILENAME, "health.json"}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            relative = path.relative_to(root).as_posix()
            raise ArtifactLineageError(
                LineageReason.PATH_INVALID,
                "public destination contains a symlink",
                path=relative if relative in declared else None,
            )
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in allowed:
            raise ArtifactLineageError(
                LineageReason.GRAPH_INVALID,
                "public destination contains an undeclared file",
                path=relative if relative in declared else None,
            )


def _json_bytes(payload: object) -> bytes:
    try:
        return (
            json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (OverflowError, TypeError, ValueError) as exc:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "payload is not strict JSON"
        ) from exc


def _validate_uuid4(value: object, label: str) -> None:
    if not isinstance(value, str) or len(value) != 36 or value.lower() != value:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, f"{label} must be a canonical UUID4"
        )
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, ValueError) as exc:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, f"{label} must be a canonical UUID4"
        ) from exc
    if str(parsed) != value or parsed.version != 4:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, f"{label} must be a canonical UUID4"
        )


def _validate_bounded_identity(value: object, label: str, limit: int) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > limit
        or not _PRODUCER_RE.fullmatch(value)
    ):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, f"{label} is malformed or unbounded"
        )


def _parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not _UTC_TIMESTAMP_RE.fullmatch(value):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, f"{label} must be a canonical UTC timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, f"{label} is unparseable"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, f"{label} must be UTC"
        )
    return parsed


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ArtifactLineageError(
            LineageReason.CONTRACT_INVALID, "release timestamps must be timezone-aware"
        )
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


_ISSUE_CODES = {
    LineageReason.MANIFEST_MISSING: "output.lineage.manifest_missing",
    LineageReason.MANIFEST_INVALID: "output.lineage.manifest_invalid",
    LineageReason.CONTRACT_INVALID: "output.lineage.manifest_invalid",
    LineageReason.PATH_INVALID: "output.lineage.graph_invalid",
    LineageReason.BOUNDS_EXCEEDED: "output.lineage.bounds_exceeded",
    LineageReason.GRAPH_INVALID: "output.lineage.graph_invalid",
    LineageReason.ARTIFACT_MISSING: "output.lineage.artifact_missing",
    LineageReason.ARTIFACT_MISMATCH: "output.lineage.artifact_mismatch",
    LineageReason.ACCEPTANCE_MISSING: "output.lineage.acceptance_missing",
    LineageReason.ACCEPTANCE_INVALID: "output.lineage.acceptance_invalid",
    LineageReason.ACCEPTANCE_MISMATCH: "output.lineage.acceptance_invalid",
    LineageReason.SEMANTIC_GATE_RED: "output.lineage.candidate_rejected",
    LineageReason.IO_ERROR: "output.lineage.unreadable",
}


def _issue_for(
    error: ArtifactLineageError,
    *,
    tour: str | None = None,
) -> LineageIssue:
    safe_path = _safe_issue_path(error.path)
    issue_tour = tour or error.tour
    if issue_tour is None and safe_path:
        candidate = safe_path.split("/", 1)[0]
        issue_tour = candidate if candidate in TOURS else None
    return LineageIssue(
        code=_ISSUE_CODES[error.reason],
        severity="error",
        reason=error.reason,
        tour=issue_tour,
        path=safe_path,
    )


def _safe_issue_path(path: str | None) -> str | None:
    if path is None:
        return None
    if path in TOURS:
        return path
    try:
        _split_artifact_path(path)
    except ArtifactLineageError:
        return None
    return path


def _scoped_lineage_error(
    error: ArtifactLineageError,
    tour: str,
) -> ArtifactLineageError:
    """Attach one tour at a validation boundary without exposing private detail."""

    _validate_tour(tour)
    if error.tour == tour:
        return error
    return ArtifactLineageError(
        error.reason,
        error.detail,
        path=error.path,
        tour=tour,
    )


def _coerce_error(error: Exception) -> ArtifactLineageError:
    if isinstance(error, ArtifactLineageError):
        return error
    return ArtifactLineageError(LineageReason.IO_ERROR, type(error).__name__)


__all__ = [
    "ACCEPTANCE_FILENAME",
    "ACCEPTANCE_SCHEMA",
    "ARTIFACT_LINEAGE_SCHEMA",
    "MANIFEST_FILENAME",
    "OPTIONAL_EVALUATION_FILES",
    "AcceptedRelease",
    "ArtifactLineageError",
    "ArtifactProvenance",
    "begin_artifact_write",
    "CarriedRelease",
    "LineageIssue",
    "LineageReason",
    "LineageState",
    "MirrorResult",
    "ProducedArtifactCollector",
    "ReleaseContext",
    "ReleaseCoordinator",
    "TourDraft",
    "ValidatedRelease",
    "accept_release",
    "begin_produced_artifacts",
    "begin_release",
    "carry_forward_release",
    "discover_tour_artifacts",
    "draft_tour_release",
    "exact_file_identity",
    "initialize_release_root",
    "inspect_release",
    "lineage_health_summary",
    "load_accepted_release",
    "main",
    "merge_release_drafts",
    "mirror_release",
    "note_produced_artifact",
    "publish_data_release",
    "publish_web_release",
    "remove_produced_artifact",
    "reset_produced_artifacts",
    "seal_release",
    "snapshot_produced_artifacts",
    "source_fingerprint",
    "unbless_release_for_mutation",
    "validate_public_release",
    "write_produced_artifact",
    "write_produced_artifact_batch",
]


if __name__ == "__main__":
    raise SystemExit(main())
