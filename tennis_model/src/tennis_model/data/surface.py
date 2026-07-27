"""Court-surface resolution for live / upcoming / brand-new events — fully offline.

ESPN carries no surface, so it is re-derived downstream. For an event already in the
historical archive that is trivial (its real surface is on every prior row); the gap is
*new* or *sponsor-renamed* events (e.g. "Nordea Open" = clay Bastad, "Grand Est Open 88" =
new clay) that the archive name-match misses — those used to fall straight to a month-of-year
guess (July -> Grass), mislabeling the mid-July clay swing.

`resolve_surface` closes that gap with a priority chain:
    real archive value  ->  Wikipedia main-article surface  ->  month-of-year fallback
The Wikipedia surfaces are fetched + cached to ``live/<tour>/wiki_surface.json`` by the
download step (``data.draws_wiki.download_wiki_draws``); this module only READS that cache,
so it never touches the network and is import-safe for the offline loader (``data.results``).
"""

from __future__ import annotations

import json

from ..config import EVENT_TIER_FALLBACK, MONTH_SURFACE, live_dir

# Paired with the writer in data/draws_wiki.download_wiki_draws (like wiki_draws.json).
_WIKI_SURFACE_FILE = "wiki_surface.json"
_WIKI_CATEGORY_FILE = "wiki_category.json"


def wiki_surface_map(tour: str) -> dict:
    """{espn_event_name: canonical_surface} from the cached Wikipedia surfaces.

    Empty when the cache is absent/corrupt — so an un-refreshed checkout degrades cleanly to
    the month fallback rather than erroring. Read fresh each call (the file is a handful of
    events; the download step writes it before any build reads it)."""
    path = live_dir(tour) / _WIKI_SURFACE_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt/partial cache just means no wiki surfaces
        return {}
    return data if isinstance(data, dict) else {}


def _norm_event(name: object) -> str:
    """Case/whitespace-insensitive event key (mirrors health._norm_name)."""
    return " ".join(str(name).split()).casefold()


def _lookup_by_name(mapping: dict, event: str) -> str | None:
    """Cache lookup tolerant of how one event is spelled across feeds.

    Exact key, then whitespace/case-normalised, then containment either way behind a
    >=5-char guard — the same rule `_display_name` uses to tie a sponsor title to its
    archive city. The two surface paths used to disagree here (the pre-start one matched
    loosely, the live one exactly), so the SAME event could change surface the day it
    started: WTA Memphis read Hard while upcoming and flipped to a Grass month-guess on
    day one. An ambiguous containment hit (two different surfaces) resolves to None rather
    than guessing.
    """
    if not mapping:
        return None
    ev = str(event)
    if ev in mapping:
        return mapping[ev]
    key = _norm_event(ev)
    norm = {_norm_event(k): v for k, v in mapping.items()}
    if key in norm:
        return norm[key]
    if len(key) < 5:
        return None
    hits = {v for k, v in norm.items() if len(k) >= 5 and (k in key or key in k)}
    return hits.pop() if len(hits) == 1 else None


def wiki_surface(tour: str, event: str) -> str | None:
    """Cached Wikipedia surface for one event, or None if not cached."""
    return _lookup_by_name(wiki_surface_map(tour), event)


def wiki_surface_lookup(tour: str, names) -> dict:
    """{name: surface} over the given event names, using the tolerant match.

    Names that don't resolve are simply absent, so a caller can `.map()` this and keep NaN
    for the month fallback. Exists so the loader (`data.results.clean`) and the projector
    resolve a surface through the identical predicate."""
    m = wiki_surface_map(tour)
    if not m:
        return {}
    out = {}
    for n in names:
        v = _lookup_by_name(m, n)
        if v:
            out[str(n)] = v
    return out


def resolve_surface_info(tour: str, event: str, date,
                         archive_surface: str | None = None) -> tuple[str, str]:
    """``(surface, source)`` — the single resolution chain, source in
    ``archive`` | ``wiki`` | ``month``.

    The source is not decoration: a month value is a GUESS, and the callers that feed a
    resolved surface back in as ``archive_surface`` must not recycle a guess as though it
    were a fact. That loop is what pinned the DC Open to Grass while its Wikipedia infobox
    said Hard the whole time."""
    if archive_surface is not None:
        return archive_surface, "archive"
    cached = wiki_surface(tour, event)
    if cached:
        return cached, "wiki"
    mm = str(date)[5:7]
    return MONTH_SURFACE.get(int(mm) if mm.isdigit() else 1, "Hard"), "month"


def resolve_surface(tour: str, event: str, date, archive_surface: str | None = None) -> str:
    """Surface for a live/upcoming event: real archive value -> Wikipedia cache -> month.

    ``archive_surface`` is whatever the caller resolved from the match archive by name (None
    if the event isn't in it). ``date`` is the event's start (any ISO-ish string); only its
    month is used for the final fallback."""
    return resolve_surface_info(tour, event, date, archive_surface)[0]


def wiki_category_map(tour: str) -> dict:
    """{espn_event_name: display_tier} from the cached Wikipedia categories; {} if absent/corrupt.
    Read offline like wiki_surface_map — never touches the network, import-safe for the loader."""
    path = live_dir(tour) / _WIKI_CATEGORY_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt/partial cache just means no wiki categories
        return {}
    return data if isinstance(data, dict) else {}


def wiki_category(tour: str, event: str) -> str | None:
    """Cached Wikipedia tier/category for one event, or None if not cached."""
    return wiki_category_map(tour).get(str(event))


def resolve_level(tour: str, event: str, archive_level: str | None = None) -> str:
    """Display tier for a live/upcoming event, mirroring resolve_surface:
        real archive level -> Wikipedia category -> curated EVENT_TIER_FALLBACK -> '{TOUR} Tour'.
    The caller passes ``archive_level`` only when the match frame gives a reliable current-edition
    level (else None, so a stale historical tier can't win). Fallback values that are bare tier
    numbers ("250") render "{TOUR} 250"; full strings ("Grand Slam") pass through."""
    generic = f"{tour.upper()} Tour"
    if archive_level and archive_level != generic:
        return archive_level
    cat = wiki_category(tour, event)
    if cat:
        return cat
    fb = EVENT_TIER_FALLBACK.get(str(event))
    if not fb:  # tolerate sponsor prefixes/suffixes: a fallback key that appears in the event name
        low = str(event).lower()
        fb = next((v for k, v in EVENT_TIER_FALLBACK.items() if k.lower() in low), None)
    if fb:
        return f"{tour.upper()} {fb}" if str(fb).isdigit() else str(fb)
    return generic
