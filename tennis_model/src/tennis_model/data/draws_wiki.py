"""Wikipedia complete-draw fallback and tournament metadata (MediaWiki API).

ESPN's scoreboard pre-creates a tournament's bracket as empty shells and fills the real
player names in **one day at a time** off the daily order of play, so it never carries a
complete draw at release — which is why the live projector was forced to Elo-*seed* a
hypothetical bracket until ESPN caught up. Wikipedia often mirrors the complete draw as
ordered bracket templates and remains useful when a first-party artifact is absent.

``data.draws`` owns event discovery, first-party ATP/WTA precedence, retention and the
normalized cache. This module resolves a Wikipedia article and parses its ordered first-round
bracket. The draw is
laid out as several `{N}TeamBracket-Compact-Tennis{3|5}[-Byes]` section templates (one per
bracket section, top-to-bottom) plus small non-compact summary brackets for the late
rounds; concatenating the `-Compact-` sections' first-round slots in document order
reconstructs the full ordered draw. That order pins every downstream pairing (which half
two future winners land on) — the piece ESPN's `match_num`-less feed can never give.

The normalized output is written by ``data.draws`` to ``tournament_draws.json`` with explicit
provenance. The old direct ``wiki_draws.json`` writer below remains only as a migration/test
seam. Player names are reconciled to the model at simulation time.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta

from ..config import (
    SURFACE_MAP,
    TOURS,
    WIKI_API,
    WIKI_DRAW_RETENTION_DAYS,
    WIKI_DRAW_TITLE_OVERRIDES,
    WIKI_TITLE_OVERRIDES,
    WIKI_UA,
    live_dir,
)
from .participants import (
    ParticipantContext,
    ParticipantKind,
    ParticipantSource,
    canonical_placeholder,
    classify_participant,
    draw_is_settled,
    is_real_participant,
    placeholder_label,
)

# `mwparserfromhell` is imported lazily inside _parse_bracket so cache readers never need it.

# ESPN sponsor titles carry noise words that hurt Wikipedia search; drop them so
# "EFG Swiss Open Gstaad" -> "Swiss Open Gstaad" matches the article.
_SPONSOR_NOISE = {"efg", "atp", "wta", "presented", "by", "powered"}
# Words too common to identify a tournament — never used as the search anchor (else a
# search for "... Open ... singles" can match the wrong Open, e.g. the Australian Open).
_TITLE_GENERIC = {"open", "cup", "championships", "international", "classic", "masters",
                  "tennis", "grand", "prix", "trophy", "championship", "tour"}
_SENTINEL = object()   # RD1 slot param absent (a bye position, seed sits in RD2)


class _LinkedIdentity(str):
    """Transient positive identity evidence while one Wiki bracket is being parsed."""


_GET_ATTEMPTS = 3
_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_BACKOFF_S = 30.0


def _get(params: dict) -> dict:
    """GET the MediaWiki API as JSON (keyless; descriptive UA per Wikimedia etiquette).

    Retries a rate-limit or transient server error, honouring `Retry-After` when Wikimedia
    sends one. Every other fetcher against a rate-limited source in this repo already does
    this (`kalshi`, `wta_stats`); this one had no backoff at all, so a single 429 turned into
    a missing surface — which falls through to the month-of-year guess, and on a 500-tier
    event that now blocks the deploy. A permanent error (404 for a page that does not exist)
    is NOT retried: it is raised on the first attempt for the caller to handle."""
    url = WIKI_API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    for attempt in range(_GET_ATTEMPTS):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in _RETRY_STATUS or attempt == _GET_ATTEMPTS - 1:
                raise
            hdr = (e.headers or {}).get("Retry-After") if hasattr(e, "headers") else None
            try:
                wait = min(float(hdr), _MAX_BACKOFF_S) if hdr else float(2 ** attempt)
            except (TypeError, ValueError):
                wait = float(2 ** attempt)
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == _GET_ATTEMPTS - 1:
                raise
            wait = float(2 ** attempt)
        time.sleep(wait)
    raise RuntimeError("unreachable")   # pragma: no cover — the loop always returns or raises


def _wikitext(title: str) -> str | None:
    """Article wikitext (following redirects), or None if the page doesn't exist."""
    d = _get({"action": "parse", "page": title, "prop": "wikitext", "redirects": 1})
    if "error" in d:
        return None
    return d.get("parse", {}).get("wikitext", {}).get("*")


def _anchor(clean_event: str) -> str | None:
    """The most distinctive token of an event name (a city/name, not "Open"/"Cup"), used
    to reject a search hit for a different tournament. None if the name is all-generic."""
    toks = [w for w in re.split(r"[\s\-]+", clean_event)
            if len(w) >= 4 and w.lower() not in _SPONSOR_NOISE | _TITLE_GENERIC]
    return max(toks, key=len).lower() if toks else None


def _gender_of(title_low: str) -> str | None:
    """Which draw a Wikipedia title is: "men", "women", or None for a tour-only "– Singles"
    article. Guards against resolving an ATP query to the Women's draw of a combined event."""
    if "women" in title_low or "ladies" in title_low:
        return "women"
    if re.search(r"\bmen['’s]", title_low) or title_low.rstrip().endswith(" men"):
        return "men"
    return None


def _search_title(query: str, year: int, anchor: str | None, gender: str | None) -> str | None:
    """Best draw-article title for a query, gated so it can only be THIS tournament's draw:
    a singles (not doubles/qualifying) article, whose title carries the right `year`, the
    distinctive `anchor` token, and the right `gender` (men/women, or None = tour-only
    "Singles"). The year gate stops a not-yet-posted draw silently resolving to last year's;
    the gender gate stops an ATP event resolving to the Women's draw of a combined event."""
    d = _get({"action": "query", "list": "search", "srsearch": query, "srlimit": 10})
    for h in d.get("query", {}).get("search", []) or []:
        low = h.get("title", "").lower()
        if "doubles" in low or "qualif" in low or "singles" not in low:
            continue
        if str(year) not in low or (anchor and anchor not in low):
            continue                              # wrong year / different tournament
        if _gender_of(low) == gender:
            return h["title"]
    return None


def resolve_title(event: str, year: int, tour: str, espn_id: str | None = None) -> str | None:
    """ESPN event name -> Wikipedia draw-article title, or None if not found.

    Slams and combined events split into "Men's singles"/"Women's singles"; tour-only events
    use a plain "Singles" article. We try the tour-specific article first, then the tour-only
    one, via the search API (robust to sponsor names / curly apostrophes), gated on year +
    a distinctive token + the right tour. A generic-only event name cannot safely search:
    it requires an exact, per-tour ESPN-id locator in ``WIKI_DRAW_TITLE_OVERRIDES``."""
    override = WIKI_DRAW_TITLE_OVERRIDES.get(tour, {}).get(str(espn_id or ""))
    if override:
        return override.format(year=year)
    gword = "Men's singles" if tour == "atp" else "Women's singles"
    clean = " ".join(w for w in event.split() if w.lower() not in _SPONSOR_NOISE)
    anchor = _anchor(clean)
    if not anchor:
        return None
    return (_search_title(f"{year} {clean} {gword}", year, anchor, "men" if tour == "atp" else "women")
            or _search_title(f"{year} {clean} singles", year, anchor, None))


def _slot_name(value) -> str | None:
    """A bracket team parameter -> canonical wiki player name, or None for a bye.

    A real player (incl. wildcards) is a [[wikilink]] — take its target, stripping any
    "(tennis)" disambiguator so it matches the model's spelling. Otherwise the slot is a
    placeholder: "Bye" (true bye -> None) or the canonical role label for an as-yet-
    undetermined qualifier/lucky-loser/wildcard/alternate/empty seat (the caller numbers it)."""
    links = value.filter_wikilinks()
    if links:
        name = re.sub(r"\s*\([^)]*\)\s*$", "", str(links[0].title)).strip()
        # The target, not display text such as ``WC``, is identity evidence. A target that is
        # itself only a reserved role cannot survive as distinguishable identity in the
        # string-only artifact, so keep it a placeholder and fail closed.
        participant = classify_participant(
            name,
            source=ParticipantSource.WIKIPEDIA,
            context=ParticipantContext.LINKED_IDENTITY,
        )
        if participant.is_real:
            return _LinkedIdentity(name)
        if participant.is_placeholder:
            return placeholder_label(participant.kind)
        return None
    text = value.strip_code().strip()
    participant = classify_participant(
        text,
        source=ParticipantSource.WIKIPEDIA,
        context=ParticipantContext.OPENING_DRAW_SLOT,
    )
    if participant.kind is ParticipantKind.BYE:
        return None
    if participant.is_placeholder:
        return placeholder_label(participant.kind)
    return text                                   # unlinked/red-link player (no article yet)


def _team(tmpl, rd: str, i: int):
    """RDx-team{i} value (zero-padded or not), or the _SENTINEL when the param is absent
    (a bye position — the seed is carried in the next round instead of a leaf slot)."""
    for key in (f"{rd}-team{i:02d}", f"{rd}-team{i}"):
        if tmpl.has(key):
            return tmpl.get(key).value
    return _SENTINEL


def _seed_of(tmpl, i: int) -> int | None:
    for key in (f"RD1-seed{i:02d}", f"RD1-seed{i}"):
        if tmpl.has(key):
            sd = tmpl.get(key).value.strip_code().strip()
            return int(sd) if sd.isdigit() else None
    return None


def _parse_bracket(wikitext: str) -> dict | None:
    """Ordered draw from a draw article's wikitext, or None if no draw is posted.

    Each `{N}TeamBracket-Compact-...` template is one bracket SECTION (N leaves). Its first
    round is the N/2 matches over leaves (1,2),(3,4),…; a match whose two RD1 leaves are
    both absent is a seed BYE only when a real seed rides in RD2-team{k} (k = match index),
    so we seat that player against None. Other omissions stay unresolved. Concatenating every
    section's ordered leaf slots in document order rebuilds the full 2^k draw, proven byes as
    None, and unresolved entrant roles as unique placeholders.
    Returns {slots, seeds, bestOf} or None when no bracket template is present or the
    result isn't a clean power-of-two draw."""
    import mwparserfromhell
    code = mwparserfromhell.parse(wikitext)
    slots: list = []
    seeds: dict = {}
    best_of = 3
    placeholders: Counter[ParticipantKind] = Counter()
    for tmpl in code.filter_templates():
        name = str(tmpl.name)
        if "Bracket" not in name or "Compact" not in name:
            continue                              # skip late-round summary brackets
        if "Tennis5" in name:
            best_of = 5
        m = re.match(r"\s*(\d+)TeamBracket", name)
        if not m:
            continue
        leaves = int(m.group(1))
        for k in range(1, leaves // 2 + 1):       # k-th first-round match of the section
            lv, rv = _team(tmpl, "RD1", 2 * k - 1), _team(tmpl, "RD1", 2 * k)
            # An absent parameter is not itself proof of a bye: early articles also omit an
            # unresolved entrant. Explicit ``Bye`` parses to None. The compact-template bye
            # encoding with both leaves absent is accepted only when RD2 positively names the
            # carried player; every other omission remains an explicit unresolved seat.
            left = "Unresolved" if lv is _SENTINEL else _slot_name(lv)
            right = "Unresolved" if rv is _SENTINEL else _slot_name(rv)
            if lv is _SENTINEL and rv is _SENTINEL:
                bye = _team(tmpl, "RD2", k)        # both leaves absent -> a seed's bye
                carried = None if bye is _SENTINEL else _slot_name(bye)
                carried_participant = classify_participant(
                    carried,
                    source=ParticipantSource.WIKIPEDIA,
                    context=(ParticipantContext.LINKED_IDENTITY
                             if isinstance(carried, _LinkedIdentity)
                             else ParticipantContext.OPENING_DRAW_SLOT),
                )
                if carried_participant.is_real:
                    left, right = carried, None
                else:
                    left, right = "Unresolved", "Unresolved"
            pair = []
            for nm, idx in ((left, 2 * k - 1), (right, 2 * k)):
                participant = classify_participant(
                    nm,
                    source=ParticipantSource.WIKIPEDIA,
                    context=(ParticipantContext.LINKED_IDENTITY
                             if isinstance(nm, _LinkedIdentity)
                             else ParticipantContext.OPENING_DRAW_SLOT),
                )
                if participant.is_placeholder:
                    placeholders[participant.kind] += 1
                    nm = canonical_placeholder(
                        participant.kind, placeholders[participant.kind])
                elif isinstance(nm, _LinkedIdentity):
                    # The source marker exists only during parsing; artifacts retain strings.
                    nm = str(nm)
                if nm is not None:
                    sd = _seed_of(tmpl, idx)
                    if sd is not None:
                        seeds[nm] = sd
                pair.append(nm)
            slots.extend(pair)
    n = len(slots)
    if n < 2 or (n & (n - 1)):                    # empty / not a power-of-two draw
        return None
    return {"slots": slots, "seeds": seeds, "bestOf": best_of}


def fetch_draw(event: str, year: int, tour: str, meta: dict) -> dict | None:
    """Resolve + parse one event's Wikipedia fallback draw, or ``None``."""
    title = resolve_title(event, year, tour, str(meta.get("espnId") or "") or None)
    if not title:
        return None
    wt = _wikitext(title)
    if not wt:
        return None
    draw = _parse_bracket(wt)
    if not draw:
        return None                               # article exists but no draw posted yet
    return {
        **draw,
        "drawSize": sum(slot is not None for slot in draw["slots"]),
        "start": meta.get("start"), "end": meta.get("end"), "espnId": meta.get("espnId"),
        "title": title,
        "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
        "retrieved": datetime.now(UTC).strftime("%Y-%m-%d"),
    }


# Capture the WHOLE field value to end of line, like _CATEGORY_FIELD_RE does. Stopping at
# the first `|` only ever saw the wikilink TARGET, and a target need not name the surface:
# Memphis writes `[[Tennis court#outdoor courts|Hard]] / outdoor`, where the surface is in
# the DISPLAY text. Infobox parameters are separated by a newline-anchored `|`, so a pipe
# inside `[[...|...]]` never ends the field.
_SURFACE_FIELD_RE = re.compile(r"\bsurface\s*=([^\n]*)", re.IGNORECASE)
# `court`/`courts` may be joined to the surface word: `[[Clay court|Clay]]` reads "Clay
# court" but `[[Hardcourt|Hard (outdoor)]]` reads "Hardcourt", where a bare \bHard\b cannot
# match. Between them, these two gaps meant EVERY hard-court event (DC Open, National Bank
# Open, Memphis) resolved to no surface and fell through to the month-of-year guess —
# July -> Grass, on hard courts.
_SURFACE_WORD_RE = re.compile(r"\b(Hard|Clay|Grass|Carpet)(?:\s?courts?)?\b", re.IGNORECASE)


def _parse_surface(wikitext: str) -> str | None:
    """Canonical court surface from a main tournament article's infobox, or None.

    The infobox carries e.g. ``| surface=[[Clay court|Clay]] / outdoor``; take the first
    surface keyword inside the ``surface=`` field value (``[^|]`` stops at the wikilink pipe,
    but the link TARGET — "Clay court" — already names the surface) and fold via SURFACE_MAP
    (Carpet -> Hard). Pure regex, no mwparserfromhell, so it's importable without the parser."""
    for field in _SURFACE_FIELD_RE.finditer(wikitext or ""):
        m = _SURFACE_WORD_RE.search(field.group(1))
        if m:
            return SURFACE_MAP[m.group(1).capitalize()]
    return None


def _main_article_title(singles_title: str) -> str:
    """The main tournament article for a "… – Singles" draw sub-article title — the surface
    infobox lives only on the main article. Wikipedia's separator is a spaced en/em/hyphen."""
    return re.split(r"\s+[–—-]\s+", singles_title)[0].strip()


def _surface_of(title: str) -> str | None:
    """Surface parsed from a resolved MAIN-article title, or None if it carries no surface field.

    A parseable ``surface=[[…court]]`` field is itself the tennis-tournament signal (a
    non-tournament page won't carry one), so no infobox-name gate is needed — and a name gate
    wrongly rejects Grand Slams, whose main article uses a differently-named infobox template."""
    wt = _wikitext(title)
    return _parse_surface(wt) if wt else None


_FALLBACK_FETCH_CAP = 5   # candidate articles fetched per event before giving up this run


def event_meta(event: str, year: int, tour: str) -> tuple[str | None, str | None]:
    """``(surface, category)`` for an ESPN event, from its Wikipedia MAIN article, in ONE pass.

    Both fields live on the SAME article, but they used to be resolved by two functions that
    each re-ran ``resolve_title`` and then each walked their own search-result loop fetching
    up to ten more articles — roughly thirty API calls per unresolved event, every hour,
    against a source with no backoff. Resolve once, fetch each candidate once, parse both.

    The resolution is deliberately LOOSER than ``resolve_title``: the main article is findable
    by sponsor name even when the gendered singles draw is not ("Nordea Open" -> "2026 Swedish
    Open"). Wrong-event risk stays bounded by year-in-title, a distinctive body anchor, and —
    for the tier specifically — ``_parse_category``'s tour gate."""
    def _both(wt: str | None) -> tuple[str | None, str | None]:
        if not wt:
            return None, None
        return _parse_surface(wt), _parse_category(wt, tour)

    ov = WIKI_TITLE_OVERRIDES.get(event)
    if ov:
        return _both(_wikitext(ov if str(year) in ov else f"{year} {ov}"))

    surface = category = None
    singles = resolve_title(event, year, tour)          # fully year+anchor+gender gated
    if singles:
        surface, category = _both(_wikitext(_main_article_title(singles)))
        if surface and category:
            return surface, category
    # Sponsor-renamed / brand-new: search directly for the main (non-singles) article.
    clean = " ".join(w for w in event.split() if w.lower() not in _SPONSOR_NOISE)
    anchor = _anchor(clean)
    if not anchor:
        return surface, category
    d = _get({"action": "query", "list": "search", "srsearch": f"{year} {clean}", "srlimit": 10})
    fetched = 0
    for h in d.get("query", {}).get("search", []) or []:
        title = h.get("title", "")
        low = title.lower()
        if str(year) not in low or any(x in low for x in ("doubles", "qualif", "singles")):
            continue
        if fetched >= _FALLBACK_FETCH_CAP:
            break
        wt = _wikitext(title)
        fetched += 1
        if not wt or (anchor and anchor not in wt.lower()):  # body must name the distinctive token
            continue
        s, c = _both(wt)
        surface, category = surface or s, category or c
        if surface and category:
            break
    return surface, category


def event_surface(event: str, year: int, tour: str) -> str | None:
    """Court surface from the event's Wikipedia main article, or None. Thin view of
    `event_meta` — the download sweep calls that directly to resolve both fields at once."""
    return event_meta(event, year, tour)[0]


_CATEGORY_FIELD_RE = re.compile(r"\bcategory\s*=([^\n]*)", re.IGNORECASE)
_CATEGORY_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
# Which link belongs to which tour in a combined event's `category` value. WORD-BOUNDARY
# matching is load-bearing: plain substrings made "men" match inside "tournaments", so an ATP
# request matched the WTA segment `[[WTA 125 tournaments|WTA 125]]` and shipped "WTA 125" on
# the ATP board (Generali Open, 2026-07-27). `\bmen\b` correctly declines to match "women".
_TOUR_TAG_RE = {
    "atp": re.compile(r"\b(?:atp|men)\b", re.IGNORECASE),
    "wta": re.compile(r"\b(?:wta|women)\b", re.IGNORECASE),
}
_OTHER_TOUR = {"atp": "wta", "wta": "atp"}


def _parse_category(wikitext: str, tour: str) -> str | None:
    """Tournament tier ('WTA 250', 'Grand Slam', ...) from a main article's infobox
    ``category=`` field, for ``tour``. The value is one or two ``[[Target|Display]]`` wikilinks
    — combined events carry both (ATP + WTA), split by ``<br/>`` and tagged (ATP)/(men)/(WTA)/
    (women); a Slam carries a single (ITF) link. Returns the tour's Display, or None if the
    field is absent (e.g. 2025 Swedish Open). Pure regex, no parser dependency.

    Gated on tour in BOTH directions. It previously returned a lone link unconditionally and
    guessed ``picks[0]`` when nothing was tagged, so an ATP lookup landing on the WTA article
    of a combined event happily returned that tour's tier. None is the right answer when the
    field does not say which tour it describes — the caller then falls back rather than
    publishing another tour's tier."""
    m = _CATEGORY_FIELD_RE.search(wikitext or "")
    if not m:
        return None
    ours = _TOUR_TAG_RE.get(tour)
    theirs = _TOUR_TAG_RE.get(_OTHER_TOUR.get(tour, ""))
    picks = []
    for seg in re.split(r"<br\s*/?>", m.group(1), flags=re.IGNORECASE):
        lm = _CATEGORY_LINK_RE.search(seg)
        if lm:
            disp = (lm.group(2) or lm.group(1)).strip()
            disp = re.sub(r"\s+tournaments$", "", disp, flags=re.IGNORECASE)  # bare link target -> "WTA 125"
            disp = re.sub(r"\s*\(tennis\)$", "", disp, flags=re.IGNORECASE)   # "Grand Slam (tennis)" -> "Grand Slam"
            picks.append((disp, seg))
    if not picks:
        return None
    for disp, seg in picks:                      # explicitly ours wins outright
        if ours and (ours.search(seg) or ours.search(disp)):
            return disp
    # Nothing is tagged as ours. A link that is explicitly the OTHER tour's is never ours;
    # what remains is tour-neutral (a Slam's single (ITF) link). Exactly one neutral link is
    # unambiguous — ours by elimination. Two would be a guess about which tour they describe.
    neutral = [d for d, s in picks
               if not (theirs and (theirs.search(s) or theirs.search(d)))]
    return neutral[0] if len(neutral) == 1 else None


def _category_of(title: str, tour: str) -> str | None:
    """Tier parsed from a resolved MAIN-article title, or None if it carries no category field."""
    wt = _wikitext(title)
    return _parse_category(wt, tour) if wt else None


def event_category(event: str, year: int, tour: str) -> str | None:
    """Tournament tier from the event's Wikipedia main article ``category``, or None when the
    article omits the field (so the curated EVENT_TIER_FALLBACK then applies). Thin view of
    `event_meta` — the download sweep calls that directly to resolve both fields at once."""
    return event_meta(event, year, tour)[1]


_ROUND_BY_SIZE = {128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F"}
_REGISTRY_BACKFILL_DAYS = 40


def wiki_upcoming_rows(tour: str) -> list:
    """Legacy first-round rows from ``wiki_draws.json`` (new consumers use ``data.draws``).
    (tourney_name, tourney_date, round, playerA, playerB) — so the schedule board and the
    forecast log price the whole first round the moment the official draw is released.

    Byes and all not-yet-named entrant slots are skipped (nothing to price). Read-only: no
    network, no parser dependency."""
    path = live_dir(tour) / "wiki_draws.json"
    if not path.exists():
        return []
    try:
        draws = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt cache just means no wiki rows
        return []
    return _rows_from_draws(draws, today=datetime.now(UTC).strftime("%Y-%m-%d"))


def _rows_from_draws(draws: dict, today: str | None = None) -> list:
    """First-round matchup rows implied by a {event: draw} mapping (pure; testable).

    Only for events that HAVEN'T started yet (start >= today): the value here is showing the
    opening round the moment the draw drops, while ESPN's feed is still all-TBD. Once an event
    is under way ESPN names the live round day-by-day, so emitting the original R1 then would
    just replay long-finished matches on the schedule board. ISO dates compare lexically."""
    rows = []
    for name, wd in draws.items():
        start = wd.get("start") or ""
        if today and start and start < today:
            continue                          # already under way -> ESPN owns the schedule
        slots = wd.get("slots") or []
        rnd = _ROUND_BY_SIZE.get(len(slots), "R64")
        for i in range(0, len(slots) - 1, 2):
            a, b = slots[i], slots[i + 1]
            if (is_real_participant(a, context=ParticipantContext.OPENING_DRAW_SLOT)
                    and is_real_participant(b, context=ParticipantContext.OPENING_DRAW_SLOT)):
                rows.append({"tourney_name": name, "tourney_date": start,
                             "round": rnd, "playerA": a, "playerB": b})
    return rows


def _retention_cutoff(now: datetime | None = None) -> str:
    """ISO date before which a no-longer-listed cache entry may be dropped."""
    return ((now or datetime.now(UTC)) - timedelta(days=WIKI_DRAW_RETENTION_DAYS)).strftime("%Y-%m-%d")


def _registry_backfill_cutoff(now: datetime | None = None) -> str:
    """Oldest registry event whose missing draw is still useful to the projector."""
    return ((now or datetime.now(UTC)) - timedelta(days=_REGISTRY_BACKFILL_DAYS)).strftime("%Y-%m-%d")


def _still_worth_keeping(entry: object, cutoff: str) -> bool:
    """Whether a cached entry ESPN no longer lists should be carried forward.

    Keyed on the EVENT's own dates, not on whether ESPN still mentions it. A dict entry with
    no usable date is kept (better a stale draw than a deleted one — a missing draw is what
    crashes the board); a bare value with no dates at all is also kept, since a surface or a
    tier never changes for a given event-year and costs nothing to hold."""
    if not isinstance(entry, dict):
        return True
    ref = str(entry.get("end") or entry.get("start") or entry.get("retrieved") or "")[:10]
    return not ref or ref >= cutoff


def _draw_is_settled(slots, draw_size: object = None) -> bool:
    """True when every named slot in a captured draw is a real player.

    "A draw doesn't change once released" holds only for a draw captured AFTER qualifying
    resolves. Capture it earlier and its numbered entrant-role slots are placeholders that Wikipedia
    later replaces with real names — so such a capture must not be kept forever. Wikipedia can
    also encode an unresolved qualifier as ``None``, which is otherwise indistinguishable from
    a legitimate bye in the slot list. When the cached entry carries the published draw size,
    require exactly that many real entrants. The shared participant classifier keeps ingestion,
    simulation, event evidence, and the health gate on the same definition of a placeholder.
    """
    try:
        expected = int(draw_size) if draw_size is not None else None
        expected = expected if expected is not None and expected > 0 else None
    except (TypeError, ValueError, OverflowError):
        expected = None
    return draw_is_settled(
        slots,
        expected_entrants=expected,
        source=ParticipantSource.WIKIPEDIA,
    )


def download_wiki_draws(tours=TOURS) -> None:
    """Legacy direct Wikipedia cache writer retained for migration regression tests.

    Idempotent + polite: an event whose draw we've already captured AND fully resolved is
    kept as-is, so we only hit Wikipedia for events still awaiting a draw or still carrying
    qualifier placeholders. Events that have aged out of the ESPN window are pruned.
    Best-effort per event."""
    from .events import load_registry, update_registry
    from .live import fetch_events, parse_event_meta
    for tour in tours:
        try:
            events = fetch_events(tour)
            meta = parse_event_meta(events)
            # Idempotent double-write with download_live: whichever downloader survives a
            # best-effort failure still records identity, so a rename can't slip through.
            registry = update_registry(tour, meta) or load_registry(tour)
        except Exception as e:  # noqa: BLE001 — draw overlay is best-effort, never build-fatal
            print(f"  wiki-draws/{tour}: skipped ({e})")
            continue
        d = live_dir(tour)
        path = d / "wiki_draws.json"
        cached: dict = {}
        if path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — a corrupt cache just means re-fetch
                cached = {}
        out: dict = {}
        fetched = refreshed = backfilled = 0
        for name, m in meta.items():
            prev = cached.get(name) or {}
            if _draw_is_settled(prev.get("slots"), prev.get("drawSize")):
                # fully resolved — this one never changes
                out[name] = prev
                continue
            year = int((m.get("start") or "2026")[:4] or 2026)
            try:
                entry = fetch_draw(name, year, tour, m)
            except Exception as e:  # noqa: BLE001 — one bad article must not kill the rest
                print(f"  wiki-draws/{tour}: {name} skipped ({e})")
                entry = None
            if entry:
                out[name] = entry
                if prev.get("slots"):
                    refreshed += 1                    # placeholders replaced by real names
                else:
                    fetched += 1
            elif prev.get("slots"):
                out[name] = prev                      # re-fetch failed — keep what we had
        # Carry forward draws ESPN has stopped listing, until the EVENT's own dates age out.
        # Rebuilding `out` from the current window alone silently deleted every other draw —
        # and `build_tournaments` keeps projecting an event for weeks after ESPN drops it, so
        # the draw vanished from under a live consumer. That is the 256-slot Wimbledon crash:
        # the field lost its anchor, fell back to a noisy results union, and took the whole
        # board down. Twice, because the first fix leaned on this very cache being present.
        cutoff = _retention_cutoff()
        kept = 0
        for name, prev in cached.items():
            if name not in out and _still_worth_keeping(prev, cutoff):
                out[name] = prev
                kept += 1
        # Carry-forward cannot repair a cache that was already evicted. The event registry
        # survives independently and still knows recent ids, names, and dates, so use it as a
        # targeted recovery queue for exactly the projector's 40-day window. This stays behind
        # the same per-event best-effort boundary as the current ESPN sweep.
        present_ids = {str(entry.get("espnId")) for entry in out.values()
                       if isinstance(entry, dict) and entry.get("espnId")}
        present_names = {str(name).casefold() for name in out}
        backfill_cutoff = _registry_backfill_cutoff()
        for event_id, event in (registry.get("events") or {}).items():
            ref = str(event.get("end") or event.get("start") or "")[:10]
            names = [event.get("name"), *(event.get("names") or [])]
            if (not ref or ref < backfill_cutoff or str(event_id) in present_ids
                    or any(str(name).casefold() in present_names for name in names if name)):
                continue
            name = str(event.get("name") or next((n for n in names if n), ""))
            if not name:
                continue
            recovery_meta = {
                "espnId": str(event_id),
                "start": event.get("start"),
                "end": event.get("end"),
            }
            year = int(str(recovery_meta.get("start") or "2026")[:4] or 2026)
            try:
                entry = fetch_draw(name, year, tour, recovery_meta)
            except Exception as e:  # noqa: BLE001 — registry recovery is best-effort too
                print(f"  wiki-draws/{tour}: {name} backfill skipped ({e})")
                entry = None
            if entry:
                out[name] = entry
                present_ids.add(str(event_id))
                present_names.add(name.casefold())
                backfilled += 1
        if out:
            d.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out), encoding="utf-8")
            print(f"  wiki-draws/{tour}: {len(out)} draw(s) "
                  f"({fetched} new, {refreshed} re-fetched, {backfilled} registry-backfilled, "
                  f"{kept} kept past the window) -> {path}")
        else:
            print(f"  wiki-draws/{tour}: no draws posted yet for {len(meta)} tracked event(s)")
        _download_wiki_meta(tour, d, meta)   # main-article surface + tier, one pass (best-effort)


def _load_json(path) -> dict:
    """Read a best-effort JSON cache; {} when absent or corrupt (a corrupt cache re-fetches)."""
    if not path.exists():
        return {}
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a corrupt cache just means re-fetch
        return {}
    return d if isinstance(d, dict) else {}


_MISS_RETRY_IMMINENT_DAYS = 2   # an event starting this soon is retried every run regardless


def _download_wiki_meta(tour: str, d, meta: dict) -> None:
    """Cache each tracked event's main-article SURFACE and TIER in one sweep ->
    live/<tour>/wiki_surface.json + wiki_category.json (both read offline by data.surface).

    One pass, not two. Both fields live on the same article, but they used to be fetched by
    two functions that each re-resolved the title and each walked their own candidate loop —
    up to ~30 API calls per unresolved event, every hour, against a source this module gave no
    backoff at all. Formats are unchanged, so every reader is untouched.

    Policy per field: idempotent (a surface does not change once known), window-pruned, and
    never caches a MISS — a value must be able to appear when the article is finally written.
    A miss is only STAMPED, so we stop re-asking hourly for an event that is weeks away; an
    event starting within _MISS_RETRY_IMMINENT_DAYS is always retried. A cached TIER is
    additionally dropped when it is no longer sayable in this tour's vocabulary (a value
    captured before the tour gate existed can be the other tour's — see _parse_category)."""
    from .surface import normalize_level

    s_path, c_path = d / "wiki_surface.json", d / "wiki_category.json"
    miss_path = d / "wiki_meta_misses.json"
    surf_cached, cat_cached = _load_json(s_path), _load_json(c_path)
    misses = _load_json(miss_path)
    today = datetime.now(UTC).strftime("%Y-%m-%d")

    surf_out: dict = {}
    cat_out: dict = {}
    miss_out: dict = {}
    fetched = skipped = 0
    for name, m in meta.items():
        have_s = surf_cached.get(name)
        prev_c = cat_cached.get(name)
        have_c = prev_c if (prev_c and normalize_level(prev_c, tour)) else None
        if have_s:
            surf_out[name] = have_s
        if have_c:
            cat_out[name] = have_c
        if have_s and have_c:
            continue

        start = str(m.get("start") or "")
        imminent = start <= (datetime.now(UTC) + timedelta(days=_MISS_RETRY_IMMINENT_DAYS)) \
            .strftime("%Y-%m-%d")
        if misses.get(name) == today and not imminent:
            miss_out[name] = misses[name]      # already asked today; the article won't appear faster
            skipped += 1
            continue

        year = int((start or "2026")[:4] or 2026)
        try:
            surf, cat = event_meta(name, year, tour)
        except Exception as e:  # noqa: BLE001 — one bad article must not kill the sweep
            print(f"  wiki-meta/{tour}: {name} skipped ({e})")
            surf = cat = None
        if surf and not have_s:
            surf_out[name] = surf
            fetched += 1
        if cat and not have_c:
            cat_out[name] = cat
            fetched += 1
        if not (surf_out.get(name) and cat_out.get(name)):
            miss_out[name] = today             # stamp, never cache the miss as a value

    # Same retention rule as the draws: an event leaving ESPN's window must not delete facts
    # we already know about it. A surface and a tier never change for a given event-year, so
    # holding them costs nothing — and losing one sends the event straight back to the
    # month-of-year guess, which on a 500 now blocks the deploy.
    cutoff = _retention_cutoff()
    for name, prev in surf_cached.items():
        if name not in surf_out and _still_worth_keeping(prev, cutoff):
            surf_out[name] = prev
    for name, prev in cat_cached.items():
        # A tier no longer sayable in THIS tour's vocabulary is poison, not a fact — carrying
        # it forward would re-pin the "WTA 125 on the ATP board" value the drop above exists
        # to clear. Retention protects what we know; it must not resurrect what we rejected.
        if (name not in cat_out and _still_worth_keeping(prev, cutoff)
                and normalize_level(prev, tour)):
            cat_out[name] = prev

    d.mkdir(parents=True, exist_ok=True)
    for path, out in ((s_path, surf_out), (c_path, cat_out)):
        if out:
            path.write_text(json.dumps(out), encoding="utf-8")
    miss_path.write_text(json.dumps(miss_out), encoding="utf-8")
    print(f"  wiki-meta/{tour}: {len(surf_out)} surface(s), {len(cat_out)} tier(s) "
          f"({fetched} newly resolved, {skipped} miss-throttled) -> {d}")


if __name__ == "__main__":
    from .draws import download_tournament_draws
    download_tournament_draws()
