"""Source-neutral complete tournament draws.

The cache contract is deliberately independent of whichever site supplied a draw.  Every
entry is keyed by the tour-local ESPN event id when one exists and carries ordered slots,
entrant/bracket sizes, and explicit provenance.  Acquisition precedence is:

1. validated first-party ATP/WTA artifact;
2. Wikipedia's complete ordered bracket;
3. retained same-event cache when a source is transiently unavailable.

ESPN's day-by-day field remains outside this cache.  It is the projector's honest partial
frontier when none of the complete sources succeeds.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import urllib.parse
from datetime import UTC, datetime, timedelta

from ..config import TOURNAMENT_DRAW_RETENTION_DAYS, TOURS, live_dir
from .events import load_registry, set_source_id, update_registry
from .participants import (
    ParticipantContext,
    ParticipantKind,
    ParticipantSource,
    canonical_placeholder,
    draw_is_settled,
    is_real_participant,
)

CACHE_FILE = "tournament_draws.json"
LEGACY_CACHE_FILE = "wiki_draws.json"
CACHE_STATUS_FILE = "tournament_draws-status.private"
CACHE_STATUS_SCHEMA = "tournament-draw-cache-status-v1"
_CACHE_STATUS_MAX_FAILURES = 8
_CACHE_STATUS_MAX_BYTES = 4_096
_REGISTRY_BACKFILL_DAYS = 40
_ROUND_BY_SIZE = {128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF"}


def _read_json(path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _reject_nonfinite(token: str):
    raise ValueError(f"non-finite JSON constant {token!r}")


def _read_draw_cache(path, *, source: str, failures: list[dict[str, str]]) -> dict:
    """Read one optional draw cache without erasing present-but-invalid source state."""
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_nonfinite,
        )
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        failures.append({"source": source, "errorType": type(exc).__name__})
        return {}
    if not isinstance(value, dict):
        failures.append({"source": source, "errorType": "SchemaError"})
        return {}
    return value


def _bounded_cache_failures(failures) -> list[dict[str, str]]:
    bounded = []
    seen = set()
    for item in failures or []:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "unknown")[:80]
        error_type = str(item.get("errorType") or "UnknownError")[:80]
        marker = (source, error_type)
        if marker in seen:
            continue
        seen.add(marker)
        bounded.append({"source": source, "errorType": error_type})
        if len(bounded) >= _CACHE_STATUS_MAX_FAILURES:
            break
    return bounded


def _content_identity(raw: bytes) -> dict[str, int | str]:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _valid_content_identity(value) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"bytes", "sha256"}
        and isinstance(value["bytes"], int)
        and not isinstance(value["bytes"], bool)
        and value["bytes"] >= 0
        and isinstance(value["sha256"], str)
        and len(value["sha256"]) == 64
        and all(char in "0123456789abcdef" for char in value["sha256"])
    )


def draw_cache_refresh_failures(tour: str, *, directory=None) -> list[dict[str, str]]:
    """Strictly read the bounded, private status carried across a cache rewrite."""
    path = (directory or live_dir(tour)) / CACHE_STATUS_FILE
    try:
        with open(path, "rb") as source:
            raw = source.read(_CACHE_STATUS_MAX_BYTES + 1)
        if len(raw) > _CACHE_STATUS_MAX_BYTES:
            return [{"source": "draw-cache-status", "errorType": "SchemaError"}]
        payload = json.loads(
            raw.decode("utf-8"), parse_constant=_reject_nonfinite)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        return [{"source": "draw-cache-status", "errorType": type(exc).__name__}]
    if (not isinstance(payload, dict)
            or set(payload) != {"schema", "cache", "failures"}
            or payload.get("schema") != CACHE_STATUS_SCHEMA
            or not _valid_content_identity(payload.get("cache"))
            or not isinstance(payload.get("failures"), list)
            or len(payload["failures"]) > _CACHE_STATUS_MAX_FAILURES):
        return [{"source": "draw-cache-status", "errorType": "SchemaError"}]
    failures = payload["failures"]
    if any(
        not isinstance(item, dict)
        or set(item) != {"source", "errorType"}
        or not isinstance(item["source"], str)
        or not item["source"]
        or len(item["source"]) > 80
        or not isinstance(item["errorType"], str)
        or not item["errorType"]
        or len(item["errorType"]) > 80
        for item in failures
    ):
        return [{"source": "draw-cache-status", "errorType": "SchemaError"}]
    current_cache_path = (directory or live_dir(tour)) / CACHE_FILE
    try:
        current_cache = _content_identity(current_cache_path.read_bytes())
    except FileNotFoundError:
        return [{"source": "draw-cache-status", "errorType": "GenerationMismatch"}]
    except OSError as exc:
        return [{"source": "draw-cache-status", "errorType": type(exc).__name__}]
    if current_cache != payload["cache"]:
        return [{"source": "draw-cache-status", "errorType": "GenerationMismatch"}]
    return _bounded_cache_failures(failures)


def _atomic_write(path, raw: bytes) -> None:
    tmp = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_bytes(raw)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _write_draw_cache_status(directory, failures, *, cache_identity: dict) -> None:
    """Atomically persist category-only cache evidence outside every public JSON glob."""
    if not _valid_content_identity(cache_identity):
        raise ValueError("draw cache status requires a valid content identity")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / CACHE_STATUS_FILE
    payload = {
        "schema": CACHE_STATUS_SCHEMA,
        "cache": cache_identity,
        "failures": _bounded_cache_failures(failures),
    }
    _atomic_write(
        path,
        json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8"),
    )


def _normalize_entry(name: str, entry: dict, *, legacy: bool = False) -> dict | None:
    """Normalize source-specific/legacy fields into the one cache schema."""
    if not isinstance(entry, dict) or not isinstance(entry.get("slots"), list):
        return None
    slots = list(entry["slots"])
    size = len(slots)
    if size < 8 or size > 128 or size & (size - 1):
        return None
    if any(slot is not None and not isinstance(slot, str) for slot in slots):
        return None

    raw_seeds = entry.get("seeds")
    if raw_seeds is None:
        seeds: dict[str, int] = {}
    elif not isinstance(raw_seeds, dict):
        return None
    else:
        seeds = {}
        for player, raw_seed in raw_seeds.items():
            if not isinstance(player, str) or isinstance(raw_seed, bool):
                return None
            try:
                seed = int(raw_seed)
            except (TypeError, ValueError, OverflowError):
                return None
            if (isinstance(raw_seed, float) and not raw_seed.is_integer()
                    or seed < 1 or seed > size):
                return None
            seeds[player] = seed

    raw_best_of = entry.get("bestOf")
    if raw_best_of is None:
        best_of = 3
    else:
        if isinstance(raw_best_of, bool):
            return None
        try:
            best_of = int(raw_best_of)
        except (TypeError, ValueError, OverflowError):
            return None
        if isinstance(raw_best_of, float) and not raw_best_of.is_integer():
            return None
        if best_of not in (3, 5):
            return None
    source = entry.get("source") or ("wikipedia" if legacy or entry.get("url") else None)
    source_url = entry.get("sourceUrl") or entry.get("url")
    source_id = entry.get("sourceId") or entry.get("title")
    source_draw_size = entry.get("sourceDrawSize")
    if source == "wikipedia" and source_draw_size is None and legacy:
        source_draw_size = entry.get("drawSize")
    try:
        source_draw_size = int(source_draw_size)
    except (TypeError, ValueError, OverflowError):
        source_draw_size = None

    source_named = sum(slot is not None for slot in slots)
    if (source == "wikipedia" and any(slot is None for slot in slots)
            and source_draw_size != source_named):
        # Old Wiki rows cannot distinguish a true bye from an omitted unresolved entrant.
        # Make that uncertainty explicit at the normalization boundary so provider failure,
        # retention, simulation, and every later consumer see placeholders—not false byes.
        used = {str(slot).strip().casefold() for slot in slots if slot is not None}
        ordinal = 0
        materialized = []
        for slot in slots:
            if slot is not None:
                materialized.append(slot)
                continue
            while True:
                ordinal += 1
                candidate = canonical_placeholder(ParticipantKind.UNRESOLVED, ordinal)
                if candidate.casefold() not in used:
                    break
            used.add(candidate.casefold())
            materialized.append(candidate)
        slots = materialized
    normalized = {
        **entry,
        "name": str(entry.get("name") or name),
        "slots": slots,
        "seeds": seeds,
        "bestOf": best_of,
        # The old cache overloaded drawSize with bracket width. Recompute the two concepts.
        "drawSize": sum(slot is not None for slot in slots),
        "bracketSize": size,
        "source": source,
        "sourceId": str(source_id) if source_id is not None else None,
        "sourceUrl": str(source_url) if source_url else None,
        "retrieved": entry.get("retrieved") or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    # Preserve Wikipedia's source-derived entrant count before canonical normalization. Round 3
    # derives it only after distinguishing explicit/proven byes from unresolved omissions. Older
    # caches used bracket width instead; their mismatch deliberately forces one safe refresh rather
    # than manufacturing proof from the normalized non-null count.
    if source == "wikipedia":
        if source_draw_size is not None and source_draw_size > 0:
            normalized["sourceDrawSize"] = source_draw_size
    return normalized


def load_tournament_draws(
    tour: str,
    *,
    status: dict | None = None,
    include_refresh_status: bool = True,
) -> dict:
    """Read the normalized cache, falling back to an in-memory legacy migration."""
    directory = live_dir(tour)
    failures: list[dict[str, str]] = (
        draw_cache_refresh_failures(tour, directory=directory)
        if include_refresh_status else []
    )
    path = directory / CACHE_FILE
    payload_source = "complete-draw-cache"
    payload = _read_draw_cache(
        path, source=payload_source, failures=failures)
    legacy = False
    if not payload:
        payload_source = "legacy-draw-cache"
        payload = _read_draw_cache(
            directory / LEGACY_CACHE_FILE,
            source=payload_source,
            failures=failures,
        )
        legacy = bool(payload)
    out: dict = {}
    for key, value in payload.items():
        try:
            normalized = _normalize_entry(str(key), value, legacy=legacy)
        except (TypeError, ValueError, OverflowError):
            # A malformed field inside one otherwise JSON-shaped entry (for example seeds or
            # bestOf) is source degradation, not permission to abort the whole refresh before
            # its generation-bound status can be published.
            normalized = None
        if not normalized:
            failures.append({"source": payload_source, "errorType": "SchemaError"})
            continue
        event_id = str(normalized.get("espnId") or "")
        out[event_id if event_id else str(key)] = normalized
    if status is not None:
        status["failures"] = _bounded_cache_failures(failures)
    return out


def _draw_is_settled(entry: dict | None) -> bool:
    """Every entrant is a distinct real player and the recorded count reconciles."""
    if not isinstance(entry, dict):
        return False
    expected = entry.get("drawSize")
    if entry.get("source") == "wikipedia":
        expected = entry.get("sourceDrawSize")
        if any(slot is None for slot in entry.get("slots") or []):
            # Round 3's parser emits null only for an explicit/proven bye and preserves its
            # non-null entrant count as source evidence. Older normalized rows cannot prove
            # that distinction and fail closed for a one-time refresh.
            if expected != entry.get("drawSize"):
                return False
    return draw_is_settled(
        entry.get("slots"),
        expected_entrants=expected,
        require_expected=True,
        source=ParticipantSource.CANONICAL,
    )


def _official_evidence_is_valid(entry: dict | None, tour: str) -> bool:
    from .draws_official import official_dates_match

    if not isinstance(entry, dict) or entry.get("source") != tour:
        return False
    matched, field = entry.get("evidencePlayers"), entry.get("evidenceFieldPlayers")
    return (isinstance(matched, int) and isinstance(field, int) and field >= 2
            and matched >= 2 and matched * 4 >= field * 3
            and official_dates_match(
                entry.get("start"), entry.get("end") or entry.get("start"),
                entry.get("sourceStart"), entry.get("sourceEnd")))


def _canonical_source_url(value: object) -> str:
    """Stable comparison form for one draw source URL (query/fragment are not identity)."""
    try:
        parsed = urllib.parse.urlsplit(str(value or ""))
    except ValueError:
        return ""
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = urllib.parse.unquote(parsed.path).rstrip("/")
    return urllib.parse.urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def _duplicate_source_groups(draws: dict) -> list[tuple[set[str], str, str]]:
    """Cache keys, stable source identity, and evidence for duplicate attachments."""
    markers: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    for key, entry in draws.items():
        if not isinstance(entry, dict):
            continue
        espn_id = str(entry.get("espnId") or "").strip()
        source = str(entry.get("source") or "").strip().lower()
        if not espn_id or not source:
            continue
        source_id = str(entry.get("sourceId") or "").strip()
        source_url = _canonical_source_url(entry.get("sourceUrl"))
        if source_id:
            marker = ("drawSourceId", source, source_id.casefold())
            markers.setdefault(marker, {}).setdefault(espn_id, set()).add(str(key))
        if source_url:
            # A URL names the artifact globally; source-label drift must not evade the check.
            marker = ("drawSourceUrl", "", source_url)
            markers.setdefault(marker, {}).setdefault(espn_id, set()).add(str(key))

    # The same two bad rows normally collide on both id and URL. Merge those reasons into
    # one finding so health output is actionable rather than duplicated.
    grouped: dict[frozenset[str], list[str]] = {}
    grouped_markers: dict[frozenset[str], list[tuple[str, str, str]]] = {}
    event_ids: dict[frozenset[str], set[str]] = {}
    for marker, by_event in markers.items():
        if len(by_event) < 2:
            continue
        kind, source, value = marker
        keys = frozenset(key for cache_keys in by_event.values() for key in cache_keys)
        label = f"{kind} {source}:{value}" if source else f"{kind} {value}"
        grouped.setdefault(keys, []).append(label)
        grouped_markers.setdefault(keys, []).append(marker)
        event_ids.setdefault(keys, set()).update(by_event)

    incidents = []
    for keys, reasons in grouped.items():
        markers_for_group = grouped_markers[keys]
        ids = sorted((source, value) for kind, source, value in markers_for_group
                     if kind == "drawSourceId")
        if len(ids) == 1:
            identity = f"{ids[0][0]}:{ids[0][1]}"
        else:
            # A canonical URL is stable evidence too, but keep it out of issue titles and
            # fingerprints. Hashing also bounds identities for unusually long Wikipedia URLs.
            identity_payload = json.dumps(sorted(markers_for_group), separators=(",", ":"))
            identity = f"markers:{hashlib.sha256(identity_payload.encode()).hexdigest()[:20]}"
        detail = (f"{' and '.join(sorted(reasons))} attached to multiple ESPN events: "
                  f"{', '.join(sorted(event_ids[keys]))}")
        incidents.append((set(keys), identity, detail))
    return incidents


def duplicate_draw_source_incidents(draws: dict) -> list[tuple[str, str]]:
    """Stable source identity plus human evidence for health finding emitters."""
    return [(identity, detail) for _keys, identity, detail in _duplicate_source_groups(draws)]


def duplicate_draw_source_attachments(draws: dict) -> list[str]:
    """Human-readable duplicate attachment findings for health/output validation."""
    return [detail for _identity, detail in duplicate_draw_source_incidents(draws)]


def _quarantine_duplicate_sources(draws: dict) -> tuple[dict, list[str]]:
    groups = _duplicate_source_groups(draws)
    bad = {key for keys, _identity, _detail in groups for key in keys}
    return ({key: entry for key, entry in draws.items() if str(key) not in bad},
            [detail for _keys, _identity, detail in groups])


def _retained(entry: dict, cutoff: str) -> bool:
    ref = str(entry.get("end") or entry.get("start") or entry.get("retrieved") or "")[:10]
    return not ref or ref >= cutoff


def _with_event(entry: dict, name: str, meta: dict) -> dict:
    return {**entry, "name": str(name), "espnId": meta.get("espnId"),
            "start": meta.get("start"), "end": meta.get("end")}


def _lookup(cache: dict, name: str, meta: dict) -> dict | None:
    event_id = str(meta.get("espnId") or "")
    if event_id and event_id in cache:
        return cache[event_id]
    if name in cache:
        return cache[name]
    for entry in cache.values():
        if isinstance(entry, dict) and event_id and str(entry.get("espnId") or "") == event_id:
            return entry
    return None


def _field_evidence(tour: str, name: str, meta: dict) -> list[str]:
    fields = _read_json(live_dir(tour) / "fields.json")
    event_id = str(meta.get("espnId") or "")
    entry = fields.get(event_id) or fields.get(name)
    if not entry and event_id:
        entry = next((value for value in fields.values()
                      if isinstance(value, dict) and str(value.get("espnId") or "") == event_id), None)
    if not isinstance(entry, dict):
        return []
    return [str(player) for player in entry.get("field") or []
            if is_real_participant(player, source=ParticipantSource.ESPN,
                                   context=ParticipantContext.ATHLETE)]


def _field_membership_matches(entry: dict, evidence_players) -> bool:
    """Whether a settled cached draw still names ESPN's current full event field.

    Official PDFs are revised after withdrawals and seed re-ordering. A normalized draw can
    therefore be geometrically settled yet stale; compare canonical name keys so harmless
    punctuation/accent differences do not turn every refresh into a provider request.
    """
    from .results import _name_key
    drawn = {
        _name_key(player) for player in entry.get("slots") or []
        if is_real_participant(player, context=ParticipantContext.OPENING_DRAW_SLOT)
    }
    current = {
        _name_key(player) for player in evidence_players or []
        if is_real_participant(player, source=ParticipantSource.ESPN,
                               context=ParticipantContext.ATHLETE)
    }
    return bool(drawn) and drawn == current


def _wikipedia_evidence_is_valid(entry: dict | None, name: str, year: int,
                                 tour: str, meta: dict) -> bool:
    """Whether an active cached Wikipedia draw still resolves to this exact event.

    Settled bracket geometry proves only that the cached page held a complete draw. It says
    nothing about which event that page described. Re-resolve the current event under today's
    year/anchor/gender/explicit-id contract before the settled-cache shortcut may reuse it.
    """
    from .draws_wiki import resolve_title

    if not isinstance(entry, dict) or entry.get("source") != "wikipedia":
        return False
    expected = resolve_title(
        name, year, tour, str(meta.get("espnId") or "") or None)
    if not expected or str(entry.get("sourceId") or "").casefold() != expected.casefold():
        return False
    expected_url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(
        expected.replace(" ", "_"))
    return _canonical_source_url(entry.get("sourceUrl")) == _canonical_source_url(expected_url)


def _wiki_draw(name: str, year: int, tour: str, meta: dict) -> dict | None:
    from .draws_wiki import fetch_draw
    raw = fetch_draw(name, year, tour, meta)
    normalized = _normalize_entry(name, raw or {}, legacy=True)
    return _with_event(normalized, name, meta) if normalized else None


def _resolve_one(tour: str, name: str, meta: dict, registry_entry: dict,
                 previous: dict | None) -> tuple[dict | None, list[str]]:
    """Provider first, then Wikipedia/cache fallback for one registered event."""
    from .draws_official import fetch_official_draw

    # Attachment evidence is permanent; field membership is not. Official PDFs can be revised
    # after a withdrawal and seed re-ordering, so an ACTIVE settled artifact is reused only while
    # ESPN's full field still agrees with it. Cincinnati 2026 otherwise retained Griekspoor after
    # ATP source 422 had re-seated the draw around his withdrawal.
    if previous and previous.get("source") == tour and not _official_evidence_is_valid(previous, tour):
        previous = None  # generated/legacy official entry without strong attachment evidence

    # Do not spend provider requests upgrading a settled fallback after its event is over.
    # New/live draws move to first-party; retained historical brackets remain valid Wikipedia
    # provenance and are naturally replaced next edition.
    end = str(meta.get("end") or meta.get("start") or "")[:10]
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if previous and _draw_is_settled(previous) and end and end < today:
        return _with_event(previous, name, meta), []

    year = int(str(meta.get("start") or datetime.now(UTC).year)[:4])
    cache_rejected: list[str] = []
    if previous and previous.get("source") == "wikipedia":
        try:
            valid_wiki = _wikipedia_evidence_is_valid(previous, name, year, tour, meta)
        except Exception as exc:  # noqa: BLE001 - active cache must fail closed on uncertainty
            valid_wiki = False
            cache_rejected.append(f"wikipedia cache revalidation failed: {exc}")
        if not valid_wiki:
            cache_rejected.append("wikipedia cache identity does not match this active event")
            previous = None

    evidence = _field_evidence(tour, name, meta)
    if (previous and _official_evidence_is_valid(previous, tour)
            and _draw_is_settled(previous)
            and _field_membership_matches(previous, evidence)):
        return _with_event(previous, name, meta), []
    if len(evidence) >= 2:
        official, rejected = fetch_official_draw(
            tour, year, {**meta, "name": name}, registry_entry, evidence)
    else:
        official, rejected = None, [f"{tour}: official draw deferred; fewer than 2 live players"]
    rejected = cache_rejected + rejected
    if official:
        return _with_event(official, name, meta), rejected

    # A settled fallback cache is reusable only after its active event identity was revalidated
    # above. An incomplete entry is re-fetched so qualifiers/null holes can resolve.
    if previous and _draw_is_settled(previous):
        return _with_event(previous, name, meta), rejected
    try:
        wiki = _wiki_draw(name, year, tour, meta)
    except Exception as exc:  # noqa: BLE001 - provider/cache fallback remains usable
        rejected.append(f"wikipedia fetch failed: {exc}")
        wiki = None
    return wiki or (_with_event(previous, name, meta) if previous else None), rejected


def download_tournament_draws(tours=TOURS,
                              events_by_tour: dict[str, list] | None = None) -> None:
    """Refresh current/recent complete draws and write ``tournament_draws.json``.

    ``events_by_tour`` is the raw scoreboard response already acquired by ``download_live``.
    Missing tours are fetched independently, preserving the draw layer's best-effort retry
    when the live overlay could not reach ESPN."""
    from .draws_wiki import _download_wiki_meta
    from .live import fetch_events, parse_event_meta

    for tour in tours:
        try:
            raw_events = (events_by_tour or {}).get(tour)
            if events_by_tour is None or tour not in events_by_tour:
                raw_events = fetch_events(tour)
            meta = parse_event_meta(raw_events or [])
            registry = update_registry(tour, meta) or load_registry(tour)
        except Exception as exc:  # noqa: BLE001 - draw overlay is best effort
            print(f"  tournament-draws/{tour}: skipped ({exc})")
            continue

        directory = live_dir(tour)
        prior_cache_failures = draw_cache_refresh_failures(tour, directory=directory)
        cache_status: dict = {}
        cache = load_tournament_draws(
            tour, status=cache_status, include_refresh_status=False)
        out: dict = {}
        official_count = wiki_count = kept_count = 0
        unresolved_refresh = 0
        events = registry.get("events") or {}
        current_ids = {str(event.get("espnId")) for event in meta.values()
                       if event.get("espnId")}
        current_names = {str(name).casefold() for name in meta}

        # Surface/tier metadata still comes from Wikipedia's main article, independently of
        # which source supplied the bracket.
        try:
            _download_wiki_meta(tour, directory, meta)
        except Exception as exc:  # noqa: BLE001
            print(f"  wiki-meta/{tour}: skipped ({exc})")

        for name, event_meta in meta.items():
            event_id = str(event_meta.get("espnId") or "")
            previous = _lookup(cache, name, event_meta)
            entry, rejected = _resolve_one(
                tour, name, event_meta, (events.get(event_id) or {}), previous)
            if not entry:
                unresolved_refresh += 1
                if rejected:
                    print(f"  tournament-draws/{tour}: {name}: " + "; ".join(rejected[:3]))
                continue
            key = event_id or name
            out[key] = entry
            if entry.get("source") == tour:
                official_count += 1
                if event_id and entry.get("sourceId"):
                    set_source_id(tour, event_id, tour, str(entry["sourceId"]))
                    (events.get(event_id) or {}).setdefault("sourceIds", {})[tour] = str(entry["sourceId"])
            elif entry.get("source") == "wikipedia":
                wiki_count += 1

        # The cache must outlive ESPN's discovery window. Keep recent entries even when the
        # event has disappeared from the current scoreboard.
        cutoff = (datetime.now(UTC) - timedelta(days=TOURNAMENT_DRAW_RETENTION_DAYS)).strftime("%Y-%m-%d")
        for key, entry in cache.items():
            source = entry.get("source") if isinstance(entry, dict) else None
            invalid_official = source in ("atp", "wta") and not _official_evidence_is_valid(entry, source)
            entry_id = str(entry.get("espnId") or key) if isinstance(entry, dict) else str(key)
            entry_name = str(entry.get("name") or key).casefold() if isinstance(entry, dict) else str(key).casefold()
            currently_tracked = entry_id in current_ids or entry_name in current_names
            if (key not in out and not currently_tracked and not invalid_official
                    and _retained(entry, cutoff)):
                out[key] = entry
                kept_count += 1

        # Recover a recent registry event if the cache itself was evicted. A persisted source
        # id is trusted only because it was originally written after player/date validation.
        backfill_cutoff = (datetime.now(UTC) - timedelta(days=_REGISTRY_BACKFILL_DAYS)).strftime("%Y-%m-%d")
        present_ids = {str(entry.get("espnId")) for entry in out.values() if entry.get("espnId")}
        present_ids |= {str(event.get("espnId")) for event in meta.values() if event.get("espnId")}
        for event_id, event in events.items():
            ref = str(event.get("end") or event.get("start") or "")[:10]
            if not ref or ref < backfill_cutoff or str(event_id) in present_ids:
                continue
            name = str(event.get("name") or next(iter(event.get("names") or []), ""))
            if not name:
                continue
            backfill_meta = {"espnId": str(event_id), "start": event.get("start"), "end": event.get("end")}
            entry, rejected = _resolve_one(tour, name, backfill_meta, event, None)
            if entry:
                out[str(event_id)] = entry
                if entry.get("source") == tour and entry.get("sourceId"):
                    set_source_id(tour, str(event_id), tour, str(entry["sourceId"]))
            else:
                unresolved_refresh += 1
                if rejected:
                    print(f"  tournament-draws/{tour}: {name} backfill: " + "; ".join(rejected[:2]))

        out, duplicate_findings = _quarantine_duplicate_sources(out)
        for finding in duplicate_findings:
            print(f"  tournament-draws/{tour}: quarantined duplicate source attachment: {finding}")

        directory.mkdir(parents=True, exist_ok=True)
        path = directory / CACHE_FILE
        # A cache read/schema failure belongs to this refresh attempt even if providers happen
        # to reconstruct every current event: retain it for the newly written generation and
        # clear it only after a subsequent clean read/refresh. If any current or recent-registry
        # event is still unresolved, preserve the prior generation's evidence as well.
        carried_failures = cache_status.get("failures") or []
        if not carried_failures and unresolved_refresh:
            carried_failures = prior_cache_failures
        cache_raw = json.dumps(
            out, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        cache_identity = _content_identity(cache_raw)
        # Publish the future generation-bound status first. Until the atomic cache replace,
        # readers see a digest mismatch and fail closed; a crash can never attach clean or
        # stale status to different cache bytes.
        _write_draw_cache_status(
            directory, carried_failures, cache_identity=cache_identity)
        _atomic_write(path, cache_raw)
        if out:
            print(f"  tournament-draws/{tour}: {len(out)} draw(s) "
                  f"({official_count} official, {wiki_count} wikipedia, {kept_count} retained) -> {path}")
        else:
            print(f"  tournament-draws/{tour}: no complete draws for {len(meta)} tracked event(s) -> {path}")


def _rows_from_draws(draws: dict, today: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for key, draw in draws.items():
        start = str(draw.get("start") or "")
        if today and start and start < today:
            continue
        slots = draw.get("slots") or []
        round_name = _ROUND_BY_SIZE.get(len(slots), "R64")
        name = str(draw.get("name") or key)
        for index in range(0, len(slots) - 1, 2):
            a, b = slots[index], slots[index + 1]
            if (is_real_participant(a, context=ParticipantContext.OPENING_DRAW_SLOT)
                    and is_real_participant(b, context=ParticipantContext.OPENING_DRAW_SLOT)):
                rows.append({"tourney_name": name, "espn_id": draw.get("espnId"),
                             "tourney_date": start, "round": round_name,
                             "playerA": a, "playerB": b})
    return rows


def tournament_draw_upcoming_rows(tour: str, *, status: dict | None = None) -> list[dict]:
    return _rows_from_draws(load_tournament_draws(tour, status=status),
                            today=datetime.now(UTC).strftime("%Y-%m-%d"))
