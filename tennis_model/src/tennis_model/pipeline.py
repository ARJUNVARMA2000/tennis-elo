"""End-to-end pipeline: data -> ratings -> point model -> combiner -> JSON + model.

Run:  PYTHONPATH=src python -m tennis_model.pipeline --tour all [--download] [--backtest]

For each tour it builds the production predictor (data/output/<tour>/predictor.pkl)
and writes the full set of frontend JSON artifacts (see model/export.py). The web app
reads data/output/<tour>/*.json; accepted all-tour publication mirrors them later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .artifact_lineage import CarriedRelease, ReleaseContext

from . import __version__
from .config import (
    DATA_DIR,
    KALSHI_LEDGER_DIR,
    MATCH_POPULATION_VERSION,
    OUTPUT_DIR,
    PLAYER_ALIASES,
    TENNIS_ABSTRACT_DIR,
    TOURS,
    WTA_DUAL_STATE_GATE_THRESHOLD,
    kalshi_dir,
    live_dir,
    odds_dir,
    output_dir,
)
from .data.results import load_matches
from .model.export import export_all
from .model.features import (
    FEATURES,
    build_dual_state_inputs,
    build_predictor_inputs,
    feat_params_for,
)
from .model.features import main_rows as main_rows  # noqa: F401 — compatibility seam for guard tests
from .model.predict import TennisPredictor
from .model.train import train_final, walk_forward, walk_forward_state_gate, xgb_params_for
from .timing import stage_input_fingerprint, timed

# These are the soft-fail boundaries whose outcomes otherwise exist only as log prose.
# Product stages feed a shipped/operator-facing artifact and become actionable health
# warnings. Evaluation stages are benchmarks/metrics and remain informational.
PIPELINE_STAGE_CRITICALITY = {
    # Failure only loses a private reuse optimization; the standalone health command
    # recomputes the same summary safely, so this is operational/evaluation evidence.
    "health_manifest": "evaluation",
    "upcoming_prepare": "product",
    "tracking": "product",
    "forecast_products": "product",
    "backtest": "evaluation",
    "market_scorecard": "evaluation",
    "kalshi_benchmark": "evaluation",
    "kalshi_report": "evaluation",
    "tennis_abstract_benchmark": "evaluation",
}


class UpcomingInputDegraded(RuntimeError):
    """An upcoming source was corrupt/unavailable but usable fallback data remained."""


class ForecastLogDegraded(RuntimeError):
    """Forecast tracking skipped one or more malformed persisted records."""


class TennisAbstractAcquisitionDegraded(RuntimeError):
    """The optional external benchmark refresh failed while frozen evidence remained usable."""


class KalshiAcquisitionDegraded(RuntimeError):
    """The evaluation provider wholly failed or exhausted its shared time budget."""


class KalshiPartialSweepDegraded(RuntimeError):
    """At least one evaluation-provider sweep failed while another remained usable."""


class MarketScorecardNoMatchesDegraded(RuntimeError):
    """The market benchmark ran but could not join any odds rows to OOS predictions."""


# File content is the durable identity, while this process-local cache is only a read
# optimization.  The full stat signature invalidates on in-place edits, chmod, or atomic
# replacement; callers still receive only content digests and never private filesystem paths.
_FILE_INPUT_IDENTITY_CACHE: dict[str, tuple[tuple[int, ...], dict]] = {}
_FILE_INPUT_IDENTITY_CACHE_LOCK = threading.Lock()
_PRODUCER_SOURCE_MAX_FILES = 512
_PRODUCER_SOURCE_MAX_BYTES = 16 * 1024 * 1024
_PRODUCER_SOURCE_SUFFIXES = frozenset({".py", ".csv"})


def _frame_input_identity(frame) -> dict:
    """Compact deterministic provenance for a pipeline frame.

    Production match frames carry the exact normalized-source fingerprint assigned by
    ``load_matches``. Derived metric frames are content-hashed: row/column shape alone is
    not provenance because two OOS runs with different probabilities commonly share it.
    """
    attrs = getattr(frame, "attrs", {})
    normalized = attrs.get("normalizedInputFingerprint") if isinstance(attrs, dict) else None
    identity = {
        "type": f"{type(frame).__module__}.{type(frame).__qualname__}",
        "normalized": normalized if isinstance(normalized, str) else None,
    }
    try:
        identity["rows"] = len(frame)
    except TypeError:
        identity["rows"] = None
    columns = getattr(frame, "columns", None)
    if columns is not None:
        identity["columns"] = [str(column) for column in columns]
    dtypes = getattr(frame, "dtypes", None)
    if dtypes is not None:
        identity["dtypes"] = [str(dtype) for dtype in dtypes]
    if identity["normalized"] is None:
        try:
            # ``orient=split`` fixes index/column/value ordering and handles the datetime,
            # nullable, and object columns found in walk-forward frames.  This path is used
            # only for derived frames; the large production match frame takes the O(1)
            # normalized fingerprint above.
            raw = frame.to_json(
                orient="split", date_format="iso", date_unit="ns", default_handler=str
            ).encode("utf-8")
            identity["contentSha256"] = hashlib.sha256(raw).hexdigest()
        except (AttributeError, TypeError, ValueError, OverflowError):
            identity["contentSha256"] = None
    return identity


def _predictor_input_identity(predictor) -> dict:
    trained = getattr(predictor, "trained_at", None)
    feature_params = getattr(predictor, "_fp", None)
    if is_dataclass(feature_params) and not isinstance(feature_params, type):
        feature_params = asdict(feature_params)
    return {
        "artifactId": getattr(predictor, "artifact_id", None),
        "trainedAt": str(trained) if trained is not None else None,
        "populationVersion": getattr(predictor, "_match_population_version", None),
        "schemaVersion": getattr(predictor, "_inference_schema_version", None),
        "featureParams": _json_input_identity(feature_params),
        "dualStateThreshold": getattr(predictor, "_dual_state_threshold", None),
        "hasLowerState": bool(getattr(predictor, "_has_lower_state", False)),
        "playerAliases": _json_input_identity(
            getattr(predictor, "_player_aliases", None)
        ),
        "modelVersion": __version__,
        "sourceRevision": os.environ.get("GITHUB_SHA") or __version__,
    }


def _stat_signature(stat_result) -> tuple[int, ...]:
    return (
        int(stat_result.st_dev),
        int(stat_result.st_ino),
        int(stat_result.st_size),
        int(stat_result.st_mtime_ns),
        int(stat_result.st_ctime_ns),
    )


def _file_input_identity(path) -> dict:
    """Content identity for one file, cached only while its full stat signature agrees."""
    path = Path(path)
    try:
        signature = _stat_signature(path.stat())
    except FileNotFoundError:
        return {"state": "missing"}
    except OSError as exc:
        return {"state": "unreadable", "errorType": type(exc).__name__}

    cache_key = str(path.resolve(strict=False))
    with _FILE_INPUT_IDENTITY_CACHE_LOCK:
        cached = _FILE_INPUT_IDENTITY_CACHE.get(cache_key)
    if cached is not None and cached[0] == signature:
        return dict(cached[1])

    digest = hashlib.sha256()
    try:
        size = 0
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                size += len(chunk)
                digest.update(chunk)
        identity = {"state": "present", "bytes": size, "sha256": digest.hexdigest()}
        # A concurrent replacement/write must not let bytes from one generation be cached
        # under another generation's signature. The identity remains safe for this attempt;
        # it is simply left uncached and recomputed by the next stage.
        if _stat_signature(path.stat()) == signature:
            with _FILE_INPUT_IDENTITY_CACHE_LOCK:
                _FILE_INPUT_IDENTITY_CACHE[cache_key] = (signature, identity)
        return dict(identity)
    except FileNotFoundError:
        return {"state": "missing"}
    except OSError as exc:
        return {"state": "unreadable", "errorType": type(exc).__name__}


def _directory_input_identity(directory, patterns: tuple[str, ...]) -> dict:
    """Deterministic identity for the matching files directly under a directory."""
    directory = Path(directory)
    try:
        if not directory.is_dir():
            return {"state": "missing"}
        paths = sorted({path for pattern in patterns for path in directory.glob(pattern)})
    except OSError as exc:
        return {"state": "unreadable", "errorType": type(exc).__name__}
    return {
        "state": "present",
        "files": {path.name: _file_input_identity(path) for path in paths if path.is_file()},
    }


def _producer_revision(source_root: Path | None = None) -> str:
    """Bind a release to the exact producer checkout or a bounded local source tree.

    GitHub supplies the immutable commit SHA in production.  Local and test runs may
    have uncommitted source, so their deterministic fallback hashes every Python module
    under the package root instead of collapsing distinct implementations onto the
    static package version. Committed CSV resources beside those modules are included
    because venue altitude/timezone tables alter feature and simulation behavior.
    """
    github_sha = os.environ.get("GITHUB_SHA", "")
    normalized_sha = github_sha.lower()
    if len(github_sha) in {40, 64} and all(
        c in "0123456789abcdef" for c in normalized_sha
    ):
        return f"git:{normalized_sha}"

    root = (source_root or Path(__file__).resolve().parent).resolve(strict=False)
    paths = sorted(
        (path for path in root.rglob("*") if path.suffix in _PRODUCER_SOURCE_SUFFIXES),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    if not paths or len(paths) > _PRODUCER_SOURCE_MAX_FILES:
        raise ValueError("producer source file count is outside the bounded contract")

    digest = hashlib.sha256(b"tennis-model-producer-source-v1\0")
    total_bytes = 0
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError("producer source tree contains a non-regular Python file")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        raw = path.read_bytes()
        total_bytes += len(raw)
        if total_bytes > _PRODUCER_SOURCE_MAX_BYTES:
            raise ValueError("producer source bytes exceed the bounded contract")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return f"src1:{digest.hexdigest()}"


def _json_input_identity(value: object) -> dict:
    """Canonical content identity for already-JSON-shaped derived stage inputs."""
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError):
        return {"state": "unhashable", "type": f"{type(value).__module__}.{type(value).__qualname__}"}
    try:
        items = len(value)  # type: ignore[arg-type]
    except TypeError:
        items = None
    return {"state": "present", "items": items, "sha256": hashlib.sha256(raw).hexdigest()}


def _enriched_input_identity(enriched: list[dict] | None) -> dict:
    return {"state": "unavailable"} if enriched is None else _json_input_identity(enriched)


def _forecast_log_input_identity(tour: str) -> dict:
    return _file_input_identity(DATA_DIR / "forecast_log" / f"{tour}.jsonl")


def _output_files_input_identity(tour: str, names: tuple[str, ...]) -> dict:
    root = output_dir(tour)
    return {name: _file_input_identity(root / name) for name in names}


def _tracking_source_identity(tour: str) -> dict:
    """Persisted state read by log/grade in addition to frame/predictor inputs."""
    return {
        "forecastLog": _forecast_log_input_identity(tour),
        "outputs": _output_files_input_identity(
            tour, ("brackets.json", "tournaments.json", "accuracy.json")
        ),
    }


def _tennis_abstract_source_identity(
    tour: str, *, include_external: bool = False
) -> dict:
    """Frozen cohort and durable state read by the public benchmark.

    The provider pointer is an acquisition input only. The public report is anchored to
    the frozen first capture and deliberately omits transport status, so its release
    provenance must not change merely because a conditional request updated ``latest``.
    """
    from .eval.tennis_abstract_benchmark import (
        FIRST_CAPTURE_PATH,
        baseline_path,
        eligibility_path,
        ledger_path,
        schedule_receipt_path,
    )

    identity = {
        "firstCapture": _file_input_identity(FIRST_CAPTURE_PATH),
        "forecastLog": _forecast_log_input_identity(tour),
        "baseline": _file_input_identity(baseline_path(tour)),
        "eligibility": _file_input_identity(eligibility_path(tour)),
        "scheduleReceipt": _file_input_identity(schedule_receipt_path(tour)),
        "ledger": _file_input_identity(ledger_path(tour)),
    }
    if include_external:
        event_root = TENNIS_ABSTRACT_DIR / tour / "189-2026"
        identity["latestExternal"] = _file_input_identity(event_root / "latest.json")
    return identity


def _profile_sources_input_identity(tour: str) -> dict:
    """Profile index plus only the referenced shards; never follow paths outside output."""
    root = output_dir(tour)
    index_path = root / "profile-index.json"
    identity = {"index": _file_input_identity(index_path), "shards": {}}
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return identity
    except (OSError, TypeError, ValueError) as exc:
        identity["shards"] = {"state": "unreadable", "errorType": type(exc).__name__}
        return identity
    if not isinstance(payload, dict):
        identity["shards"] = {"state": "malformed", "errorType": type(payload).__name__}
        return identity

    root_resolved = root.resolve(strict=False)
    shards = {}
    profiles = payload.get("profiles") or []
    if not isinstance(profiles, list):
        identity["shards"] = {"state": "malformed", "errorType": type(profiles).__name__}
        return identity
    for row in profiles:
        filename = row.get("file") if isinstance(row, dict) else None
        if not isinstance(filename, str) or not filename:
            continue
        candidate = (root / filename).resolve(strict=False)
        try:
            relative = candidate.relative_to(root_resolved).as_posix()
        except ValueError:
            shards[filename] = {"state": "outside-output"}
            continue
        shards[relative] = _file_input_identity(candidate)
    identity["shards"] = dict(sorted(shards.items()))
    return identity


def _forecast_products_source_identity(tour: str) -> dict:
    """Persisted sources read while decorating movement and player performance."""
    return {
        "forecastLog": _forecast_log_input_identity(tour),
        "outputs": _output_files_input_identity(
            tour, ("brackets.json", "performance.json")
        ),
        "profiles": _profile_sources_input_identity(tour),
    }


def _health_manifest_source_identity(tour: str) -> dict:
    # Reuse the health module's canonical source set (all match overlays plus ESPN
    # acquisition and Charting Overview) so the receipt and manifest cannot drift.
    from .data.health import _health_input_fingerprint

    return {"sourceHealthFingerprint": _health_input_fingerprint(tour)}


def _market_scorecard_source_identity(tour: str) -> dict:
    return {
        "odds": _directory_input_identity(odds_dir(tour), ("*.xlsx", "*.csv")),
    }


def _kalshi_benchmark_source_identity(tour: str) -> dict:
    return {
        "snapshots": _file_input_identity(kalshi_dir(tour) / "snapshots.json"),
        "ledger": _file_input_identity(KALSHI_LEDGER_DIR / f"{tour}.csv"),
        "forecastLog": _forecast_log_input_identity(tour),
        "rankings": _file_input_identity(live_dir(tour) / "rankings.json"),
    }


def _backtest_contract_identity(tour: str, *, threshold, dual_input, end_year: int) -> dict:
    params = feat_params_for(tour)
    params = asdict(params) if is_dataclass(params) and not isinstance(params, type) else params
    return {
        "startTest": 2016,
        "endTest": end_year,
        "threshold": threshold,
        "dualInput": dual_input,
        "features": list(FEATURES),
        "featureParams": _json_input_identity(params),
        "xgbOverrides": _json_input_identity(xgb_params_for(tour)),
        "matchPopulationVersion": MATCH_POPULATION_VERSION,
        "playerAliases": _json_input_identity(sorted(PLAYER_ALIASES.items())),
        "modelVersion": __version__,
    }


def _upcoming_source_identity(tour: str) -> dict:
    from .data.draws import CACHE_STATUS_FILE

    directory = live_dir(tour)
    return {
        "utcDate": datetime.now(UTC).date().isoformat(),
        "files": {
            name: _file_input_identity(directory / name)
            for name in (
                "upcoming.csv",
                "tournament_draws.json",
                CACHE_STATUS_FILE,
                "wiki_draws.json",
            )
        },
    }


def _kalshi_report_input_identity(tours) -> dict:
    ordered = list(tours)
    return {
        "tours": ordered,
        "reportTours": list(TOURS),
        "ledgers": {
            tour: _file_input_identity(DATA_DIR / "kalshi_ledger" / f"{tour}.csv")
            for tour in TOURS
        },
    }


@contextmanager
def _receipt_stage(tour: str, stage: str, *inputs: object):
    """Bind a named soft-fail stage to timing plus its durable per-tour receipt."""
    criticality = PIPELINE_STAGE_CRITICALITY[stage]
    fingerprint = stage_input_fingerprint({
        "tour": tour,
        "stage": stage,
        "inputs": inputs,
    })
    with timed(tour, stage, criticality=criticality, input_fingerprint=fingerprint) as attempt:
        yield attempt


_FRAME_PREDICTOR_ARTIFACT_ID = "_pipelinePredictorArtifactId"
_FRAME_RELEASE_STAGE_INPUTS = "_pipelineReleaseStageInputs"


@dataclass(frozen=True, slots=True)
class _ReleasePlan:
    """Strict all-tour lineage plan decided before the first output mutation."""

    context: ReleaseContext
    carried: CarriedRelease | None
    bootstrap: bool


def _bind_frame_predictor(frame, predictor) -> None:
    """Carry validated runtime model identity to the parent release coordinator."""
    attrs = getattr(frame, "attrs", None)
    if isinstance(attrs, dict):
        attrs[_FRAME_PREDICTOR_ARTIFACT_ID] = getattr(predictor, "artifact_id", None)


def _bind_frame_release_stage_input(frame, stage: str, identity: dict) -> None:
    """Retain the exact pre-stage view of mutable outputs consumed in this run."""

    attrs = getattr(frame, "attrs", None)
    if isinstance(attrs, dict):
        stage_inputs = attrs.setdefault(_FRAME_RELEASE_STAGE_INPUTS, {})
        if isinstance(stage_inputs, dict):
            stage_inputs[stage] = identity


def _release_source_identity(
    tour: str,
    frame,
    mode: str,
    *,
    release_created_at: str,
    producer_revision: str,
    accepted_parent: dict | None,
) -> dict:
    """Compact aggregate identity for non-output inputs behind one tour graph."""
    attrs = getattr(frame, "attrs", None)
    stage_inputs = (
        attrs.get(_FRAME_RELEASE_STAGE_INPUTS, {})
        if isinstance(attrs, dict) else {}
    )
    return {
        "tour": tour,
        "mode": mode,
        "modelVersion": __version__,
        "producerRevision": producer_revision,
        "releaseCreatedAt": release_created_at,
        # A current artifact may read an old accuracy/profile/performance artifact on a
        # quick or soft-fail path. The exact accepted parent manifest is the conservative
        # transitive binding for every such retained input; bootstrap sealing requires all
        # graph nodes to have current-run production proof instead.
        "acceptedParent": accepted_parent,
        # Captured immediately before a stage reads mutable retained/current outputs.
        # This closes bootstrap provenance too, where no accepted-parent hash exists.
        "stageInputs": _json_input_identity(
            stage_inputs if isinstance(stage_inputs, dict) else {}
        ),
        "matches": _frame_input_identity(frame),
        "rankings": _file_input_identity(live_dir(tour) / "rankings.json"),
        "fields": _file_input_identity(live_dir(tour) / "fields.json"),
        "events": _file_input_identity(live_dir(tour) / "events.json"),
        "upcoming": _upcoming_source_identity(tour),
        "forecastLog": _forecast_log_input_identity(tour),
        "odds": _directory_input_identity(odds_dir(tour), ("*.xlsx", "*.csv")),
        "kalshiLedger": _file_input_identity(
            KALSHI_LEDGER_DIR / f"{tour}.csv"
        ),
        "charting": _directory_input_identity(
            DATA_DIR / "raw" / "charting", ("*.csv", "*.json")
        ),
    }


def _begin_release(mode: str) -> _ReleasePlan:
    """Choose exact carry or a parentless graph bootstrap before any output write.

    A missing/corrupt lineage pointer is recoverable by rebuilding the complete public
    graph. Unsafe paths, I/O failures, and pointer-revocation failures are not evidence
    that the cache is merely absent, so those propagate and stop the run.
    """
    from .artifact_lineage import (
        ArtifactLineageError,
        LineageReason,
        begin_release,
        carry_forward_release,
        initialize_release_root,
        unbless_release_for_mutation,
    )

    initialize_release_root(OUTPUT_DIR)
    carried = None
    try:
        # Source and destination intentionally coincide in the production cache: the
        # validated manifest records are the immutable prior snapshot used for exact
        # carry decisions while writers replace files below it.
        carried = carry_forward_release(OUTPUT_DIR, OUTPUT_DIR)
    except ArtifactLineageError as exc:
        if exc.reason in {LineageReason.PATH_INVALID, LineageReason.IO_ERROR}:
            raise
        print(
            f"  lineage/{mode}: no accepted parent ({exc.reason.value}); "
            "promoting to parentless full graph bootstrap"
        )
    bootstrap = carried is None
    accepted = carried.accepted if carried is not None else None
    context = begin_release(
        "full" if bootstrap else mode,
        accepted_prior=accepted,
    )
    # The carried manifest/receipt are now immutable in memory. Remove their durable
    # pointers before the first public artifact can be mutated, so a host crash exposes
    # an explicitly unblessed candidate rather than an old pointer over mixed bytes.
    unbless_release_for_mutation(OUTPUT_DIR)
    return _ReleasePlan(context=context, carried=carried, bootstrap=bootstrap)


def _remove_unproduced_bootstrap_evaluations(produced) -> None:
    """Remove stale optional JSON that has no production proof in this bootstrap."""
    from .artifact_lineage import OPTIONAL_EVALUATION_FILES, remove_produced_artifact

    snapshots = produced.snapshot()
    for tour in TOURS:
        proved = set(snapshots[tour])
        for filename in sorted(OPTIONAL_EVALUATION_FILES):
            if f"{tour}/{filename}" in proved:
                continue
            remove_produced_artifact(
                tour,
                output_dir(tour) / filename,
                trusted_root=OUTPUT_DIR,
            )


def _seal_release(frames: dict, plan: _ReleasePlan, produced):
    """Strictly draft and seal one ATP+WTA release; every failure stops the run."""
    from .artifact_lineage import (
        ArtifactProvenance,
        ReleaseCoordinator,
        draft_tour_release,
        source_fingerprint,
    )

    if plan.bootstrap:
        _remove_unproduced_bootstrap_evaluations(produced)

    coordinator = ReleaseCoordinator(plan.context)
    producer_revision = _producer_revision()
    accepted_parent = None
    if plan.carried is not None:
        accepted_parent = {
            "releaseId": plan.carried.accepted.release_id,
            "manifestSha256": plan.carried.accepted.release.manifest_sha256,
        }
    for tour in TOURS:
        frame = frames[tour]
        attrs = getattr(frame, "attrs", None)
        artifact_id = (
            attrs.get(_FRAME_PREDICTOR_ARTIFACT_ID)
            if isinstance(attrs, dict) else None
        )
        provenance = ArtifactProvenance(
            producer=f"tennis_model.pipeline@{producer_revision}",
            source_fingerprint=source_fingerprint(
                _release_source_identity(
                    tour,
                    frame,
                    plan.context.mode,
                    release_created_at=plan.context.created_at,
                    producer_revision=producer_revision,
                    accepted_parent=accepted_parent,
                )
            ),
            predictor_artifact_id=artifact_id,
        )
        coordinator.merge(draft_tour_release(
            OUTPUT_DIR,
            tour,
            plan.context,
            provenance,
            carried=plan.carried,
            produced_paths=produced.snapshot(tour),
        ))

    release = coordinator.seal(OUTPUT_DIR)
    print(
        f"  lineage/{plan.context.mode}: sealed {release.release_id} "
        f"({len(release.records)} exact artifacts, {release.manifest_sha256[:12]})"
    )
    return release


def _unbless_partial_output() -> None:
    """Revoke all-tour validity before a single-tour developer run mutates output."""
    from .artifact_lineage import (
        initialize_release_root,
        unbless_release_for_mutation,
    )

    initialize_release_root(OUTPUT_DIR)
    unbless_release_for_mutation(OUTPUT_DIR)


def _prepare_upcoming(tour: str, predictor, df) -> list[dict] | None:
    """Price the live schedule once for both tracking and the published snapshot."""
    try:
        with _receipt_stage(
            tour, "upcoming_prepare", _frame_input_identity(df),
            _predictor_input_identity(predictor),
            _upcoming_source_identity(tour),
        ) as attempt:
            from .model.upcoming import enrich_upcoming, load_upcoming
            status: dict = {}
            upcoming = load_upcoming(tour, status=status)
            enriched = enrich_upcoming(predictor, df, upcoming, tour)
            failures = status.get("failures") or []
            if failures:
                attempt.mark_failure(UpcomingInputDegraded(
                    "; ".join(
                        f"{item.get('source')}: {item.get('errorType')}"
                        for item in failures if isinstance(item, dict)
                    ) or "upcoming input degraded"
                ))
            return enriched
    except Exception as e:                                   # noqa: BLE001 — both consumers degrade
        print(f"  upcoming/{tour}: shared enrichment unavailable ({e})")
        return None


def _track(tour: str, predictor, df, enriched: list[dict] | None = None) -> None:
    """Log point-in-time forecasts + (re)grade them (writes track.json). Best-effort:
    a tracking failure must never break the build/deploy."""
    try:
        tracking_sources = _tracking_source_identity(tour)
        _bind_frame_release_stage_input(df, "tracking", tracking_sources)
        with _receipt_stage(
            tour, "tracking", _frame_input_identity(df),
            _predictor_input_identity(predictor),
            _enriched_input_identity(enriched),
            tracking_sources,
        ) as attempt:
            from .eval.track import log_and_grade
            status: dict = {}
            log_and_grade(tour, predictor, df, enriched=enriched, status=status)
            if status.get("malformedLines"):
                attempt.mark_failure(ForecastLogDegraded(
                    f"forecast log contains {status['malformedLines']} malformed line(s)"
                ))
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  track/{tour}: skipped ({e})")


def _forecast_products(tour: str, predictor, df,
                       enriched: list[dict] | None = None) -> None:
    """Publish history/performance decorations after the current snapshot is logged."""
    try:
        forecast_sources = _forecast_products_source_identity(tour)
        _bind_frame_release_stage_input(df, "forecastProducts", forecast_sources)
        with _receipt_stage(
            tour, "forecast_products", _frame_input_identity(df),
            _predictor_input_identity(predictor),
            _enriched_input_identity(enriched),
            forecast_sources,
        ):
            from .model.export import export_forecast_products
            export_forecast_products(tour, predictor, df, enriched=enriched)
    except Exception as e:                                   # noqa: BLE001 — tracking UI is non-fatal
        print(f"  forecast-products/{tour}: skipped ({e})")


def _tennis_abstract_benchmark(
    tour: str,
    predictor,
    df,
    *,
    refresh_external: bool,
) -> None:
    """Grade the frozen external benchmark without becoming a release dependency."""
    try:
        sources = _tennis_abstract_source_identity(
            tour, include_external=refresh_external
        )
        _bind_frame_release_stage_input(df, "tennisAbstractBenchmark", sources)
        with _receipt_stage(
            tour,
            "tennis_abstract_benchmark",
            _frame_input_identity(df),
            _predictor_input_identity(predictor),
            sources,
            {"refreshExternal": refresh_external},
        ) as attempt:
            from .eval.tennis_abstract_benchmark import run_benchmark

            result = run_benchmark(
                tour,
                predictor,
                df,
                refresh_external=refresh_external,
            )
            final_sources = _tennis_abstract_source_identity(tour)
            final_sources["ledgerBefore"] = sources["ledger"]
            _bind_frame_release_stage_input(
                df, "tennisAbstractBenchmark", final_sources
            )
            if result.get("refreshError"):
                attempt.mark_failure(TennisAbstractAcquisitionDegraded(
                    str(result["refreshError"])
                ))
            report = result["report"]
            comparison = report.get("matchComparison") or {}
            print(
                f"  tennis-abstract/{tour}: eligible={comparison.get('eligible', 0)} "
                f"graded={comparison.get('graded', 0)} "
                f"excluded={comparison.get('excluded', 0)} "
                f"refresh={result.get('refreshStatus')}"
            )
    except Exception as e:  # noqa: BLE001 — external evaluation must never block release
        print(f"  tennis-abstract/{tour}: skipped ({e})")


def _health_manifest(tour: str, df) -> None:
    """Let the later standalone health command reuse this exact normalized frame."""
    try:
        with _receipt_stage(
            tour, "health_manifest", _frame_input_identity(df),
            _health_manifest_source_identity(tour),
        ):
            from .data.health import write_health_manifest
            write_health_manifest(tour, df)
    except Exception as e:  # noqa: BLE001 — health command safely recomputes on a miss
        print(f"  health-manifest/{tour}: skipped ({e})")


@contextmanager
def _stage(label: str):
    """Emit one unbuffered-friendly elapsed-time line around a pipeline stage."""
    started = time.monotonic()
    print(f"--- {label} started", flush=True)
    try:
        yield
    finally:
        print(f"--- {label} finished in {time.monotonic() - started:.1f}s", flush=True)


# One allowance shared by both tours. Morning-of historical requotes are deliberately
# daily-only; the hourly path captures new/open snapshots and repeats soon if the market
# API is slow. This benchmark never determines a forecast or deploy-gate verdict.
KALSHI_QUICK_BUDGET_S = 75
KALSHI_FULL_BUDGET_S = 1200    # daily run: 20 min for the historical backfill, which is
                               # resumable, so a slow day just finishes it tomorrow
QUICK_KALSHI_DAYS = 4   # hourly run only backfills candles for the last few days; the
                        # committed ledger carries older history, the daily run the rest


def _kalshi_status_degradation(status: dict, *, budget_exhausted: bool) -> RuntimeError | None:
    """Translate provider detail into stable receipt categories, not transient prose."""
    attempted = status.get("sweepsAttempted")
    succeeded = status.get("sweepsSucceeded")
    failed = status.get("failedSweeps") or []
    if succeeded == 0:
        return KalshiAcquisitionDegraded("Kalshi market sweeps all failed")
    if budget_exhausted:
        return KalshiAcquisitionDegraded("Kalshi time budget exhausted")
    if failed or (
        isinstance(attempted, int)
        and isinstance(succeeded, int)
        and succeeded < attempted
    ):
        return KalshiPartialSweepDegraded(
            f"Kalshi market sweeps partially failed ({succeeded}/{attempted} succeeded)"
        )
    return None


def _kalshi(tour: str, df, oos) -> None:
    """Kalshi eval ledger: capture market snapshots, upsert the CSV. Best-effort:
    Kalshi is a benchmark, never a build dependency (report runs after both tours).
    This daily path owns historical quote repair; the hourly helper below deliberately
    disables requotes and shares one smaller allowance across both tours."""
    try:
        with _receipt_stage(
            tour, "kalshi_benchmark", _frame_input_identity(df),
            {"mode": "full", "oos": _frame_input_identity(oos) if oos is not None else None},
            _kalshi_benchmark_source_identity(tour),
        ) as attempt:
            from .data.kalshi import budget_spent, refresh_snapshots, time_budget
            from .eval.kalshi_ledger import refresh_ledger
            # The historical repair remains resumable, but even a rate-limited API cannot
            # monopolize the serialized deploy queue indefinitely.
            with time_budget(KALSHI_FULL_BUDGET_S):
                status: dict = {}
                refresh_snapshots(tour, status=status)
                refresh_ledger(tour, df, oos=oos)
                degradation = _kalshi_status_degradation(
                    status, budget_exhausted=budget_spent())
                if degradation is not None:
                    attempt.mark_failure(degradation)
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  kalshi/{tour}: skipped ({e})")


def _quick_kalshi(tours, frames: dict) -> None:
    """Refresh the benchmark for all quick-run tours under one real wall-clock budget.

    Historical morning quote repair can issue hundreds of candle requests and is safe to
    defer to the daily full run because Kalshi is evaluation-only. New/open snapshots still
    refresh hourly and the cross-tour report is republished from whatever completed."""
    try:
        # Enter both receipts before importing/initializing the shared provider budget.  A
        # setup failure is therefore durable for both tours instead of remaining one log line.
        with ExitStack() as stack:
            attempts = {
                tour: stack.enter_context(_receipt_stage(
                    tour, "kalshi_benchmark", _frame_input_identity(frames[tour]),
                    {"mode": "quick", "recentDays": QUICK_KALSHI_DAYS},
                    _kalshi_benchmark_source_identity(tour),
                ))
                for tour in tours
            }
            from .data.kalshi import budget_spent, refresh_snapshots, time_budget
            from .eval.kalshi_ledger import refresh_ledger

            with time_budget(KALSHI_QUICK_BUDGET_S):
                for tour in tours:
                    try:
                        status: dict = {}
                        refresh_snapshots(
                            tour, recent_days=QUICK_KALSHI_DAYS, status=status)
                        refresh_ledger(tour, frames[tour], oos=None, requote=False)
                        degradation = _kalshi_status_degradation(
                            status, budget_exhausted=budget_spent())
                        if degradation is not None:
                            attempts[tour].mark_failure(degradation)
                    except Exception as e:                     # noqa: BLE001 — per-tour soft fail
                        attempts[tour].mark_failure(e)
                        print(f"  kalshi/{tour}: skipped ({e})")
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  kalshi/quick: skipped ({e})")


def _kalshi_report(tours) -> None:
    """Regenerate the cross-tour Kalshi scorecard inside the private output tree.

    Publication is exclusively the post-gate accepted-release step. Reads the committed
    CSVs, so this also regenerates ``kalshi.json`` after a data-cache eviction. Best-effort.
    """
    try:
        report_inputs = _kalshi_report_input_identity(tours)
        with ExitStack() as stack:
            for tour in report_inputs["tours"]:
                stack.enter_context(_receipt_stage(
                    tour, "kalshi_report", report_inputs,
                ))
            from .eval.kalshi_report import build_report
            build_report()
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  kalshi-report: skipped ({e})")


def build_tour(
    tour: str,
    do_backtest: bool,
    *,
    run_kalshi: bool = True,
    refresh_tennis_abstract: bool = True,
):
    """Full build: re-walk ratings, retrain the combiner, write every JSON (daily).
    ``run_kalshi=False`` is used only by a quick-mode compatibility rebuild so the
    caller can keep both tours under the shared hourly benchmark budget. Public bytes are
    never mutated here; the accepted all-tour publisher owns that boundary."""
    print(f"\n=== {tour.upper()} === loading matches + building features...")
    threshold = WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None
    # Keep the user-facing/health population main-only.  The WTA overlay is loaded a
    # second time solely for the secondary state walk and never leaks into exports.
    df = load_matches(tour, include_lower=False) if threshold is not None else load_matches(tour)
    _health_manifest(tour, df)
    dual = None
    if threshold is not None:
        enriched_df = load_matches(tour, include_lower=True)
        dual = build_dual_state_inputs(df, enriched_df, tour=tour)
        feat, elo, srv, ctx, meta = (
            dual.base_features, dual.elo, dual.srv, dual.ctx, dual.meta)
    else:
        feat, elo, srv, ctx, meta = build_predictor_inputs(df)

    oos = None
    if do_backtest:
        print("  walk-forward backtest...")
        # Best-effort, like _market_scorecard and _kalshi below: this produces
        # accuracy.json (reported metrics) and NOTHING the shipped model depends on — but
        # it runs before train_final, so an exception here used to abort build_tour before
        # predictor.save(), throwing away a completed ratings walk over a reporting
        # artifact. accuracy.json simply persists from the previous full run.
        try:
            end_year = datetime.now(UTC).year
            backtest_inputs = [_frame_input_identity(df), {
                "contract": _backtest_contract_identity(
                    tour,
                    threshold=threshold,
                    dual_input=(
                        _frame_input_identity(enriched_df) if dual is not None else None
                    ),
                    end_year=end_year,
                ),
            }]
            with _receipt_stage(tour, "backtest", *backtest_inputs):
                if dual is not None:
                    oos = walk_forward_state_gate(
                        dual.base_features, dual.enriched_features, (threshold,),
                        start_test=2016, end_test=end_year,
                        xgb_overrides=xgb_params_for(tour))[threshold]
                else:
                    oos = walk_forward(feat, start_test=2016, end_test=end_year,
                                       xgb_overrides=xgb_params_for(tour))
        except Exception as e:                               # noqa: BLE001 — metrics only
            print(f"  backtest: SKIPPED ({type(e).__name__}: {e}) — accuracy.json keeps "
                  f"the previous run's values; the retrain continues")

    print("  training production combiner...")
    clf, iso, _ = train_final(feat, xgb_overrides=xgb_params_for(tour))
    predictor = TennisPredictor(
        clf, iso, elo, srv, ctx, meta, tour=tour,
        lower_elo=dual.lower_elo if dual else None,
        lower_srv=dual.lower_srv if dual else None,
        lower_ctx=dual.lower_ctx if dual else None,
        dual_state_threshold=threshold,
    )
    predictor.save()
    _bind_frame_predictor(df, predictor)

    export_all(tour, df, elo, srv, meta, predictor, oos=oos)
    if oos is not None:
        _market_scorecard(tour, oos)
    enriched = _prepare_upcoming(tour, predictor, df)
    _track(tour, predictor, df, enriched)        # logs upcoming forecasts first, so
    _tennis_abstract_benchmark(
        tour,
        predictor,
        df,
        refresh_external=refresh_tennis_abstract,
    )
    _forecast_products(tour, predictor, df, enriched)  # this run's snapshot reaches same deploy
    if run_kalshi:
        _kalshi(tour, df, oos)                         # daily historical benchmark repair
    return df


def _market_scorecard(tour: str, oos) -> None:
    """Model-vs-closing-line scorecard from the just-computed OOS predictions (writes
    market.json). Best-effort: odds are a benchmark, never a build dependency."""
    try:
        with _receipt_stage(
            tour, "market_scorecard", _frame_input_identity(oos),
            _market_scorecard_source_identity(tour),
        ) as attempt:
            import json

            from .eval.compare import scorecard_from_oos
            sc = scorecard_from_oos(tour, oos)
            if sc.get("matched") == 0:
                attempt.mark_failure(MarketScorecardNoMatchesDegraded(
                    "market scorecard joined zero OOS matches"
                ))
            tour_dir = output_dir(tour)
            path = tour_dir / "market.json"
            from .artifact_lineage import write_produced_artifact
            write_produced_artifact(
                tour,
                path,
                json.dumps(sc, indent=2).encode("utf-8"),
                trusted_root=tour_dir.parent,
            )
            print(f"  market/{tour}: matched={sc.get('matched')} "
                  f"model={sc.get('model', {}).get('brier')} "
                  f"market={sc.get('market', {}).get('brier')} "
                  f"lastMatched={sc.get('lastMatchedDate')}")
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  market/{tour}: skipped ({e})")


def _predictor_current(predictor, tour: str) -> bool:
    """Fail closed unless every cached predictor field and fitted object is current.

    The artifact reader performs this validation after strict envelope/hash preflight;
    the quick guard deliberately repeats it at its reuse decision so an opaque booster,
    unfitted calibrator, partial state bundle, or stale raw-field shape can only trigger
    a controlled full rebuild.
    """
    from .model.artifact import PredictorArtifactError, validate_predictor_structure

    try:
        validate_predictor_structure(predictor, tour)
    except PredictorArtifactError:
        return False
    return True


def build_tour_quick(
    tour: str,
    *,
    force_static: bool = False,
):
    """Quick refresh (intra-day): reuse the saved predictor's states, re-pull live
    results, regenerate JSON. No re-walk or retrain; warm-cache tours export in parallel.
    to persist from the last full run (the workflow caches data/output)."""
    print(f"\n=== {tour.upper()} [quick] === live refresh from saved model...")
    threshold = WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None
    df = load_matches(tour, include_lower=False) if threshold is not None else load_matches(tour)
    _health_manifest(tour, df)
    from .model.artifact import PredictorArtifactError
    try:
        predictor = TennisPredictor.load(tour)
    except PredictorArtifactError as exc:
        print(
            f"  quick: saved predictor rejected ({exc.reason.value}) -> full rebuild"
        )
        return build_tour(
            tour,
            do_backtest=False,
            run_kalshi=False,
            refresh_tennis_abstract=False,
        )
    if not _predictor_current(predictor, tour):
        print("  quick: saved predictor is stale (feature schema, FeatureParams, match "
              "population, or player aliases) -> full rebuild")
        return build_tour(
            tour,
            do_backtest=False,
            run_kalshi=False,
            refresh_tennis_abstract=False,
        )
    _bind_frame_predictor(df, predictor)
    export_all(tour, df, predictor.elo, predictor.srv, predictor.meta, predictor,
               oos=None, full=force_static)
    enriched = _prepare_upcoming(tour, predictor, df)
    _track(tour, predictor, df, enriched)
    _tennis_abstract_benchmark(
        tour,
        predictor,
        df,
        refresh_external=False,
    )
    _forecast_products(tour, predictor, df, enriched)
    return df


def _build_quick_tours(
    tours: list[str],
    *,
    force_static: bool = False,
) -> dict:
    """Build independent tour outputs concurrently after shared downloads complete."""
    def build_one(tour: str):
        with _stage(f"{tour.upper()} forecast export"):
            return build_tour_quick(
                tour,
                force_static=force_static,
            )

    if len(tours) <= 1:
        return {tour: build_one(tour) for tour in tours}
    frames = {}
    with ThreadPoolExecutor(max_workers=min(2, len(tours)),
                            thread_name_prefix="tour-export") as pool:
        futures = {tour: pool.submit(build_one, tour) for tour in tours}
        # Resolve in requested tour order. Exceptions propagate and stop the deploy exactly
        # as they did in the serial loop; only the independent work itself overlaps.
        for tour in tours:
            frames[tour] = futures[tour].result()
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tour",
        choices=(*TOURS, "all"),
        default="atp",
        help="atp | wta | all",
    )
    ap.add_argument("--download", action="store_true", help="fetch latest results overlay first")
    ap.add_argument("--backtest", action="store_true", help="run walk-forward metrics + accuracy.json")
    ap.add_argument("--quick", action="store_true",
                    help="fast refresh: re-pull live results + regenerate JSON from the saved model")
    args = ap.parse_args()
    tours = list(TOURS) if args.tour == "all" else [args.tour]

    if args.quick:
        from .data.download import download_tml_stats
        from .data.draws import download_tournament_draws
        from .data.live import download_live
        from .data.rankings import download_rankings
        # ESPN's live window drops an event soon after its final. Refresh the lightweight
        # current-year ATP overlay first so a quick run cannot keep reconstructing a
        # completed bracket from a cache that stopped before the final (Kitzbuhel, 2026).
        # One attempt keeps an unavailable stats host bounded; atomic writes preserve the
        # cached file on failure. WTA's rate-limited stats backfill remains daily-only.
        if "atp" in tours:
            with _stage("current ATP stats"):
                download_tml_stats(full=False, retries=1)
        with _stage("ESPN live results"):
            events_by_tour = download_live(tours)
        with _stage("complete tournament draws"):
            download_tournament_draws(tours, events_by_tour=events_by_tour)
        with _stage("live rankings"):
            download_rankings(tours)
        if tuple(tours) == tuple(TOURS):
            from .artifact_lineage import begin_produced_artifacts
            with begin_produced_artifacts() as produced:
                plan = _begin_release("quick")
                frames = _build_quick_tours(
                    tours,
                    force_static=plan.bootstrap,
                )
                with _stage("Kalshi quick benchmark"):
                    _quick_kalshi(tours, frames)
                with _stage("Kalshi report"):
                    _kalshi_report(tours)
                _seal_release(frames, plan, produced)
        else:
            _unbless_partial_output()
            frames = _build_quick_tours(tours)
            with _stage("Kalshi quick benchmark"):
                _quick_kalshi(tours, frames)
            with _stage("Kalshi report"):
                _kalshi_report(tours)
        return

    if args.download:
        from .data.download import download_fresh
        from .data.draws import download_tournament_draws
        from .data.live import download_live
        from .data.rankings import download_rankings
        download_fresh(tours)
        events_by_tour = download_live(tours)  # ESPN same-day overlay; also feeds draw discovery
        download_tournament_draws(tours, events_by_tour=events_by_tour)
        download_rankings(tours)

    if tuple(tours) == tuple(TOURS):
        from .artifact_lineage import begin_produced_artifacts
        with begin_produced_artifacts() as produced:
            plan = _begin_release("full")
            frames = {
                tour: build_tour(tour, args.backtest)
                for tour in tours
            }
            _kalshi_report(tours)
            _seal_release(frames, plan, produced)
    else:
        _unbless_partial_output()
        for tour in tours:
            build_tour(tour, args.backtest)
        _kalshi_report(tours)


if __name__ == "__main__":
    main()
