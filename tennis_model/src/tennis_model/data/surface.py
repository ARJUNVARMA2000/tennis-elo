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

from ..config import MONTH_SURFACE, live_dir

# Paired with the writer in data/draws_wiki.download_wiki_draws (like wiki_draws.json).
_WIKI_SURFACE_FILE = "wiki_surface.json"


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


def wiki_surface(tour: str, event: str) -> str | None:
    """Cached Wikipedia surface for one event, or None if not cached."""
    return wiki_surface_map(tour).get(str(event))


def resolve_surface(tour: str, event: str, date, archive_surface: str | None = None) -> str:
    """Surface for a live/upcoming event: real archive value -> Wikipedia cache -> month.

    ``archive_surface`` is whatever the caller resolved from the match archive by name (None
    if the event isn't in it). ``date`` is the event's start (any ISO-ish string); only its
    month is used for the final fallback."""
    if archive_surface is not None:
        return archive_surface
    cached = wiki_surface(tour, event)
    if cached:
        return cached
    mm = str(date)[5:7]
    return MONTH_SURFACE.get(int(mm) if mm.isdigit() else 1, "Hard")
