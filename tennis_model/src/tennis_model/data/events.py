"""Stable event identity: an ESPN event id, and every display name it has ever worn.

THE INVARIANT THIS MODULE EXISTS TO ESTABLISH: display names are for display; joins use
``espnId``; the name history is the alias table.

Nineteen separate seams in this codebase join two sources on an event-NAME string, and that
is the single largest bug family in its history — the duplicate Bad Homburg card with the
finalists swapped, tier regressions to "Tour", clay events shipped as Grass because the
archive calls Bastad "Bastad" while ESPN calls it "Nordea Open" (zero shared substring), and
on 2026-07-27 the DC Open losing its bracket outright when ESPN renamed it mid-tournament.

The fix was always available and never plumbed. ESPN gives every event a stable id —
``888-2026`` is the DC Open, on BOTH tours — and ``live.parse_event_meta`` has always
extracted it. It was used once, to dedup a fetch, and then thrown away: nothing persisted it,
so nothing could join on it. This module persists it.

Design notes worth keeping:

* **Per tour.** The same id legitimately appears in both tours' registries (a combined event
  is one id, two draws); each file describes that tour's half. Every consumer is already
  per-tour, and so are the caches this has to line up with.
* **``names`` is append-only.** A rename adds; it never replaces. That list IS the alias
  table, and it is what lets a cache written under yesterday's sponsor title still be found
  today.
* **Pruning never orphans a draw.** An entry is dropped only when it is both stale AND
  unreferenced by any draw cache. Leaning on a cache that could vanish under a consumer is
  what produced the 256-slot Wimbledon crash twice.

Stdlib + config only, so the offline loaders can import it without dragging in the network
modules (``live``/``draws`` import THIS, never the other way round).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..config import EVENT_DISPLAY_NAME_OVERRIDES, EVENT_REGISTRY_RETENTION_DAYS, live_dir

REGISTRY_FILE = "events.json"
REGISTRY_VERSION = 2

# ESPN event ids are "<numeric>-<year>" (888-2026). Used to tell an id-keyed cache entry from
# a legacy name-keyed one during the migration, so both formats can be read at once.
EVENT_ID_RE = re.compile(r"^\d+-\d{4}$")

# Caches whose keys may reference an event id; an entry referenced by any of them is never
# pruned, however stale it looks.
_REFERENCING_CACHES = (
    "tournament_draws.json", "wiki_draws.json",  # source-neutral + legacy migration input
    "wiki_surface.json", "wiki_category.json",
)

_MIN_CONTAINMENT = 5   # a shorter fragment matches far too much to be evidence of identity


def is_event_id(key: object) -> bool:
    """True for an ESPN event id, False for a legacy display-name key."""
    return bool(EVENT_ID_RE.match(str(key)))


def norm_event_name(name: object) -> str:
    """Case/whitespace-insensitive event key. Mirrors ``health._norm_name`` and
    ``sim.tournaments._norm_display`` so all three collapse exactly the same pairs."""
    return " ".join(str(name).split()).casefold()


def display_event_name(
    tour: str,
    raw_name: object,
    event_id: object = None,
    *,
    identity_names: Iterable[object] = (),
    known_names: Iterable[object] = (),
) -> str:
    """Return the familiar public label without weakening event identity.

    Precedence is deliberately evidence-based: a reviewed edition override, then a safe
    series fallback, then an archive name already joined to this exact event, then the old
    containment cleanup for sponsor titles that include their city. No fuzzy name match can
    establish identity here; callers may supply ``identity_names`` only after an id/evidence
    join has already done that work.
    """
    raw = " ".join(str(raw_name or "").split())
    eid = str(event_id or "").strip()
    overrides = EVENT_DISPLAY_NAME_OVERRIDES.get(str(tour).lower(), {})
    if eid and eid in overrides:
        return overrides[eid]
    series = eid.split("-", 1)[0] if eid else ""
    if series and series in overrides:
        return overrides[series]

    identity = {" ".join(str(name).split()) for name in identity_names if str(name).strip()}
    identity.discard(raw)
    if identity:
        # City/archive labels are normally the shortest trustworthy alias. Stable identity
        # evidence makes this safe even when sponsor and archive strings share no substring.
        return min(identity, key=lambda name: (len(name.split()), len(name), name.casefold()))

    low = raw.casefold()
    contained = [" ".join(str(name).split()) for name in known_names
                 if len(" ".join(str(name).split())) >= 5
                 and " ".join(str(name).split()) != raw
                 and " ".join(str(name).split()).casefold() in low]
    return max(contained, key=len) if contained else raw


def registry_path(tour: str) -> Path:
    return live_dir(tour) / REGISTRY_FILE


def load_registry(tour: str) -> dict:
    """The tour's registry, or an empty one. Never raises: a missing file is a fresh
    checkout and a corrupt one is a cache to rebuild, neither of which is fatal."""
    path = registry_path(tour)
    if not path.exists():
        return {"version": REGISTRY_VERSION, "events": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt registry just rebuilds from the next sweep
        return {"version": REGISTRY_VERSION, "events": {}}
    if not isinstance(data, dict) or not isinstance(data.get("events"), dict):
        return {"version": REGISTRY_VERSION, "events": {}}
    data.setdefault("version", REGISTRY_VERSION)
    return data


def _referenced_ids(tour: str) -> set:
    """Event ids any draw/metadata cache still keys on — these must survive pruning."""
    out: set = set()
    for fname in _REFERENCING_CACHES:
        p = live_dir(tour) / fname
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — an unreadable cache references nothing
            continue
        if isinstance(d, dict):
            out |= {k for k in d if is_event_id(k)}
            # entries may also carry the id inside the value during cache migrations
            out |= {v["espnId"] for v in d.values()
                    if isinstance(v, dict) and v.get("espnId")}
    return out


def prune(events: dict, referenced: set, now: datetime) -> dict:
    """Drop only entries that are BOTH long unseen AND unreferenced by any cache.

    The reference check is the load-bearing half. A cached complete draw outliving the
    registry entry that names it is precisely how the field lost its anchor and padded to an
    impossible 256-slot bracket, twice."""
    cutoff = (now - timedelta(days=EVENT_REGISTRY_RETENTION_DAYS)).strftime("%Y-%m-%d")
    keep = {}
    for eid, e in events.items():
        if eid in referenced or str(e.get("lastSeen", ""))[:10] >= cutoff:
            keep[eid] = e
    return keep


def update_registry(tour: str, meta: dict, now: datetime | None = None) -> dict:
    """Fold this run's ESPN event metadata into the tour's registry and persist it.

    ``meta`` is ``live.parse_event_meta`` output: ``{name: {espnId, start, end}}``. Upserts by
    id; a RENAME appends to ``names`` and moves ``name``, so the old title stays resolvable
    forever. Idempotent, so both downloaders can call it without coordinating."""
    now = now or datetime.now(UTC)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    reg = load_registry(tour)
    events = reg.get("events") or {}

    for name, m in (meta or {}).items():
        eid = str((m or {}).get("espnId") or "").strip()
        if not eid or not name:
            continue                       # no id -> nothing to key on; the caller falls back
        e = events.setdefault(eid, {"names": [], "firstSeen": stamp})
        names = [n for n in (e.get("names") or []) if n]
        if name not in names:
            names.append(str(name))        # append-only: this list IS the alias table
        e["names"] = names
        e["name"] = str(name)
        for k in ("start", "end"):
            if (m or {}).get(k):
                e[k] = m[k]                # ESPN corrects dates; last sighting wins
        e.setdefault("firstSeen", stamp)
        e["lastSeen"] = stamp

    reg["events"] = prune(events, _referenced_ids(tour), now)
    reg["version"] = REGISTRY_VERSION
    path = registry_path(tour)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg), encoding="utf-8")
    return reg


def set_source_id(tour: str, event_id: str, provider: str, source_id: str) -> dict:
    """Persist a validated provider id under an existing ESPN event identity.

    Provider ids make the next refresh cheap, but they never replace ``espnId`` as the join
    key. A missing event is not invented here: discovery must first be anchored to registry
    metadata written by :func:`update_registry`.
    """
    reg = load_registry(tour)
    event = (reg.get("events") or {}).get(str(event_id))
    if not isinstance(event, dict):
        return reg
    source_ids = dict(event.get("sourceIds") or {})
    if source_ids.get(str(provider)) == str(source_id):
        return reg
    source_ids[str(provider)] = str(source_id)
    event["sourceIds"] = source_ids
    reg["version"] = REGISTRY_VERSION
    path = registry_path(tour)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg), encoding="utf-8")
    return reg


class EventResolver:
    """Name -> event id, across every name an event has ever been seen under.

    Two tiers, both deliberately conservative — a wrong join is worse than no join, because
    it merges two real tournaments into one card:

    1. exact match on the normalised name, over the FULL history;
    2. containment either way (>=5 chars), accepted only when exactly ONE event matches.
    """

    def __init__(self, registry: dict | None = None, extra: Iterable[tuple[str, str]] = ()):
        self._entries = dict((registry or {}).get("events") or {})
        self._exact: dict[str, set] = {}
        for eid, e in self._entries.items():
            for n in list(e.get("names") or []) + [e.get("name")]:
                if n:
                    self._exact.setdefault(norm_event_name(n), set()).add(eid)
        for name, eid in extra:            # names known only to a cache, not yet to the registry
            if name and eid:
                self._exact.setdefault(norm_event_name(name), set()).add(str(eid))

    def id_of(self, name: object) -> str | None:
        key = norm_event_name(name)
        if not key:
            return None
        hit = self._exact.get(key)
        if hit and len(hit) == 1:
            return next(iter(hit))
        if len(key) < _MIN_CONTAINMENT:
            return None
        loose = {eid for known, ids in self._exact.items() for eid in ids
                 if len(known) >= _MIN_CONTAINMENT and (known in key or key in known)}
        return next(iter(loose)) if len(loose) == 1 else None

    def entry(self, eid: str) -> dict | None:
        return self._entries.get(str(eid))

    def names_of(self, eid: str) -> list:
        return list((self.entry(eid) or {}).get("names") or [])

    def current_name(self, eid: str) -> str | None:
        return (self.entry(eid) or {}).get("name")
