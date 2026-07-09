"""Authoritative tournament draws from Wikipedia (MediaWiki API).

ESPN's scoreboard pre-creates a tournament's bracket as empty shells and fills the real
player names in **one day at a time** off the daily order of play, so it never carries a
complete draw at release — which is why the live projector was forced to Elo-*seed* a
hypothetical bracket until ESPN caught up. Wikipedia posts the **complete official draw
the day it is released** (verified down to ATP-250), as ordered bracket templates.

We discover the current/upcoming events from the ESPN sweep (name + dates), resolve each
to its Wikipedia draw article, and parse the **ORDERED** first-round bracket. The draw is
laid out as several `{N}TeamBracket-Compact-Tennis{3|5}[-Byes]` section templates (one per
bracket section, top-to-bottom) plus small non-compact summary brackets for the late
rounds; concatenating the `-Compact-` sections' first-round slots in document order
reconstructs the full ordered draw. That order pins every downstream pairing (which half
two future winners land on) — the piece ESPN's `match_num`-less feed can never give.

Output: data/raw/<tour>/live/wiki_draws.json — {event: {slots, seeds, bestOf, drawSize,
start, end, title, url, retrieved}} with RAW wiki player names (resolved to the model's
canonical spellings at sim time, exactly like ESPN names). Best-effort: any failure leaves
the existing file intact and never breaks a build.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from ..config import SURFACE_MAP, TOURS, WIKI_API, WIKI_TITLE_OVERRIDES, WIKI_UA, live_dir

# `mwparserfromhell` is imported lazily inside _parse_bracket so that merely READING the
# cached wiki_draws.json (wiki_upcoming_rows, sim loaders) never needs the parser installed.

# ESPN sponsor titles carry noise words that hurt Wikipedia search; drop them so
# "EFG Swiss Open Gstaad" -> "Swiss Open Gstaad" matches the article.
_SPONSOR_NOISE = {"efg", "atp", "wta", "presented", "by", "powered"}
# Words too common to identify a tournament — never used as the search anchor (else a
# search for "... Open ... singles" can match the wrong Open, e.g. the Australian Open).
_TITLE_GENERIC = {"open", "cup", "championships", "international", "classic", "masters",
                  "tennis", "grand", "prix", "trophy", "championship", "tour"}
# No-wikilink slot labels that are placeholders, not players (a real player — even a
# wildcard — carries a [[link]]). "Bye" is handled separately (a true bye = empty slot).
_PLACEHOLDER = {"qualifier", "q", "ll", "lucky loser", "wc", "wildcard", "alt", "alternate"}
_SENTINEL = object()   # RD1 slot param absent (a bye position, seed sits in RD2)


def _get(params: dict) -> dict:
    """GET the MediaWiki API as JSON (keyless; descriptive UA per Wikimedia etiquette)."""
    url = WIKI_API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


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


def resolve_title(event: str, year: int, tour: str) -> str | None:
    """ESPN event name -> Wikipedia draw-article title, or None if not found.

    Slams and combined events split into "Men's singles"/"Women's singles"; tour-only events
    use a plain "Singles" article. We try the tour-specific article first, then the tour-only
    one, via the search API (robust to sponsor names / curly apostrophes), gated on year +
    a distinctive token + the right tour, with a config override map as the escape hatch."""
    ov = WIKI_TITLE_OVERRIDES.get(event)
    if ov:
        return ov if str(year) in ov else f"{year} {ov}"
    gword = "Men's singles" if tour == "atp" else "Women's singles"
    clean = " ".join(w for w in event.split() if w.lower() not in _SPONSOR_NOISE)
    anchor = _anchor(clean)
    return (_search_title(f"{year} {clean} {gword}", year, anchor, "men" if tour == "atp" else "women")
            or _search_title(f"{year} {clean} singles", year, anchor, None))


def _slot_name(value) -> str | None:
    """A bracket team parameter -> canonical wiki player name, or None for a bye.

    A real player (incl. wildcards) is a [[wikilink]] — take its target, stripping any
    "(tennis)" disambiguator so it matches the model's spelling. Otherwise the slot is a
    placeholder: "Bye" (true bye -> None) or an as-yet-undetermined qualifier/lucky-loser/
    empty slot -> the literal "Qualifier" (the caller makes it unique)."""
    links = value.filter_wikilinks()
    if links:
        return re.sub(r"\s*\([^)]*\)\s*$", "", str(links[0].title)).strip()
    text = value.strip_code().strip()
    low = text.lower()
    if "bye" in low:
        return None
    if not text or low in _PLACEHOLDER or "qualif" in low:
        return "Qualifier"
    return text                                   # red-link player (no article yet)


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
    both absent is a seed BYE — that seed rides in RD2-team{k} (k = match index), so we
    seat it against a None. Concatenating every section's ordered leaf slots in document
    order rebuilds the full 2^k draw, byes as None, unique "Qualifier N" placeholders.
    Returns {slots, seeds, bestOf} or None when no bracket template is present or the
    result isn't a clean power-of-two draw."""
    import mwparserfromhell
    code = mwparserfromhell.parse(wikitext)
    slots: list = []
    seeds: dict = {}
    best_of = 3
    ph = 0
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
            left = None if lv is _SENTINEL else _slot_name(lv)
            right = None if rv is _SENTINEL else _slot_name(rv)
            if lv is _SENTINEL and rv is _SENTINEL:
                bye = _team(tmpl, "RD2", k)        # both leaves absent -> a seed's bye
                left, right = (None if bye is _SENTINEL else _slot_name(bye)), None
            pair = []
            for nm, idx in ((left, 2 * k - 1), (right, 2 * k)):
                if nm == "Qualifier":
                    ph += 1
                    nm = f"Qualifier {ph}"
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
    """Resolve + parse one event's Wikipedia draw into a wiki_draws.json entry, or None."""
    title = resolve_title(event, year, tour)
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
        "drawSize": len(draw["slots"]),
        "start": meta.get("start"), "end": meta.get("end"), "espnId": meta.get("espnId"),
        "title": title,
        "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_")),
        "retrieved": datetime.now(UTC).strftime("%Y-%m-%d"),
    }


_SURFACE_FIELD_RE = re.compile(r"\bsurface\s*=([^\n|]*)", re.IGNORECASE)
_SURFACE_WORD_RE = re.compile(r"\b(Hard|Clay|Grass|Carpet)\b", re.IGNORECASE)


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


def event_surface(event: str, year: int, tour: str) -> str | None:
    """Court surface for an ESPN event from its Wikipedia MAIN article infobox, or None.

    Surface lives only on the main tournament article, never the "– Singles" draw sub-article
    fetch_draw reads — so this is a separate resolution. It is deliberately LOOSER than
    resolve_title: surface is gender-invariant, and the main article is findable by sponsor name
    even when the gendered singles draw isn't ("Nordea Open" -> "2026 Swedish Open"). Wrong-event
    risk is bounded by year-in-title + a parseable surface field + a distinctive body anchor."""
    ov = WIKI_TITLE_OVERRIDES.get(event)
    if ov:
        return _surface_of(ov if str(year) in ov else f"{year} {ov}")
    singles = resolve_title(event, year, tour)          # fully year+anchor+gender gated
    if singles:
        surf = _surface_of(_main_article_title(singles))
        if surf:
            return surf
    # Sponsor-renamed / brand-new: search directly for the main (non-singles) article.
    clean = " ".join(w for w in event.split() if w.lower() not in _SPONSOR_NOISE)
    anchor = _anchor(clean)
    d = _get({"action": "query", "list": "search", "srsearch": f"{year} {clean}", "srlimit": 10})
    for h in d.get("query", {}).get("search", []) or []:
        title = h.get("title", "")
        low = title.lower()
        if str(year) not in low or any(x in low for x in ("doubles", "qualif", "singles")):
            continue
        wt = _wikitext(title)
        if not wt or (anchor and anchor not in wt.lower()):  # body must name the distinctive token
            continue
        surf = _parse_surface(wt)
        if surf:
            return surf
    return None


_CATEGORY_FIELD_RE = re.compile(r"\bcategory\s*=([^\n]*)", re.IGNORECASE)
_CATEGORY_LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
# Words tagging which link is which tour's in a combined event's `category` value.
_TOUR_TAG = {"atp": ("atp", "men"), "wta": ("wta", "women")}


def _parse_category(wikitext: str, tour: str) -> str | None:
    """Tournament tier ('WTA 250', 'Grand Slam', ...) from a main article's infobox
    ``category=`` field, for ``tour``. The value is one or two ``[[Target|Display]]`` wikilinks
    — combined events carry both (ATP + WTA), split by ``<br/>`` and tagged (ATP)/(men)/(WTA)/
    (women); a Slam carries a single (ITF) link. Returns the tour's Display, or None if the
    field is absent (e.g. 2025 Swedish Open). Pure regex, no parser dependency."""
    m = _CATEGORY_FIELD_RE.search(wikitext or "")
    if not m:
        return None
    tags = _TOUR_TAG.get(tour, ())
    picks = []
    for seg in re.split(r"<br\s*/?>", m.group(1), flags=re.IGNORECASE):
        lm = _CATEGORY_LINK_RE.search(seg)
        if lm:
            disp = (lm.group(2) or lm.group(1)).strip()
            disp = re.sub(r"\s+tournaments$", "", disp, flags=re.IGNORECASE)  # bare link target -> "WTA 125"
            disp = re.sub(r"\s*\(tennis\)$", "", disp, flags=re.IGNORECASE)   # "Grand Slam (tennis)" -> "Grand Slam"
            picks.append((disp, seg.lower()))
    if not picks:
        return None
    if len(picks) == 1:
        return picks[0][0]
    for display, low in picks:
        if any(t in low for t in tags):
            return display
    return picks[0][0]


def _category_of(title: str, tour: str) -> str | None:
    """Tier parsed from a resolved MAIN-article title, or None if it carries no category field."""
    wt = _wikitext(title)
    return _parse_category(wt, tour) if wt else None


def event_category(event: str, year: int, tour: str) -> str | None:
    """Tournament tier for an ESPN event from its Wikipedia MAIN article ``category``, or None.
    Mirrors event_surface's resolution (category lives on the main article like surface); None
    when the article omits the field, so the curated EVENT_TIER_FALLBACK then applies."""
    ov = WIKI_TITLE_OVERRIDES.get(event)
    if ov:
        return _category_of(ov if str(year) in ov else f"{year} {ov}", tour)
    singles = resolve_title(event, year, tour)
    if singles:
        cat = _category_of(_main_article_title(singles), tour)
        if cat:
            return cat
    clean = " ".join(w for w in event.split() if w.lower() not in _SPONSOR_NOISE)
    anchor = _anchor(clean)
    d = _get({"action": "query", "list": "search", "srsearch": f"{year} {clean}", "srlimit": 10})
    for h in d.get("query", {}).get("search", []) or []:
        title = h.get("title", "")
        low = title.lower()
        if str(year) not in low or any(x in low for x in ("doubles", "qualif", "singles")):
            continue
        wt = _wikitext(title)
        if not wt or (anchor and anchor not in wt.lower()):
            continue
        cat = _parse_category(wt, tour)
        if cat:
            return cat
    return None


_ROUND_BY_SIZE = {128: "R128", 64: "R64", 32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F"}


def wiki_upcoming_rows(tour: str) -> list:
    """First-round matchups from the cached Wikipedia draws in upcoming.csv schema
    (tourney_name, tourney_date, round, playerA, playerB) — so the schedule board and the
    forecast log price the whole first round the moment the official draw is released.

    Byes and not-yet-named qualifier slots are skipped (nothing to price). Read-only: no
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
            if a and b and not str(a).startswith("Qualifier") and not str(b).startswith("Qualifier"):
                rows.append({"tourney_name": name, "tourney_date": start,
                             "round": rnd, "playerA": a, "playerB": b})
    return rows


def download_wiki_draws(tours=TOURS) -> None:
    """Fetch each current/upcoming event's official draw from Wikipedia -> wiki_draws.json.

    Idempotent + polite: an event whose draw we've already captured is kept as-is (a draw
    doesn't change once released), so we only hit Wikipedia for events still awaiting one.
    Events that have aged out of the ESPN window are pruned. Best-effort per event."""
    from .live import fetch_events, parse_event_meta
    for tour in tours:
        try:
            events = fetch_events(tour)
            meta = parse_event_meta(events)
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
        fetched = 0
        for name, m in meta.items():
            if cached.get(name, {}).get("slots"):      # already have this draw — keep it
                out[name] = cached[name]
                continue
            year = int((m.get("start") or "2026")[:4] or 2026)
            try:
                entry = fetch_draw(name, year, tour, m)
            except Exception as e:  # noqa: BLE001 — one bad article must not kill the rest
                print(f"  wiki-draws/{tour}: {name} skipped ({e})")
                entry = None
            if entry:
                out[name] = entry
                fetched += 1
        if out:
            d.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out), encoding="utf-8")
            print(f"  wiki-draws/{tour}: {len(out)} draw(s) "
                  f"({fetched} new) -> {path}")
        else:
            print(f"  wiki-draws/{tour}: no draws posted yet for {len(meta)} tracked event(s)")
        _download_wiki_surfaces(tour, d, meta)   # main-article surfaces (separate best-effort cache)
        _download_wiki_categories(tour, d, meta)  # main-article tier/category (separate best-effort cache)


def _download_wiki_surfaces(tour: str, d, meta: dict) -> None:
    """Cache each tracked event's Wikipedia main-article surface -> live/<tour>/wiki_surface.json
    (read offline by data.surface.wiki_surface_map).

    A SEPARATE cache from wiki_draws.json because surface must be captured even for events with
    no parseable draw yet — the exact new/sponsor-named events that otherwise fall to the month
    guess. Idempotent (a surface doesn't change once known), pruned to the current ESPN window,
    never caches a miss (so it retries once the article appears), best-effort per event."""
    path = d / "wiki_surface.json"
    cached: dict = {}
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — a corrupt cache just means re-fetch
            cached = {}
    out: dict = {}
    fetched = 0
    for name, m in meta.items():
        if cached.get(name):                      # already resolved — keep it
            out[name] = cached[name]
            continue
        year = int((m.get("start") or "2026")[:4] or 2026)
        try:
            surf = event_surface(name, year, tour)
        except Exception as e:  # noqa: BLE001 — one bad article must not kill the sweep
            print(f"  wiki-surface/{tour}: {name} skipped ({e})")
            surf = None
        if surf:                                  # never cache a miss -> retry when it posts
            out[name] = surf
            fetched += 1
    if out:
        d.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out), encoding="utf-8")
        print(f"  wiki-surface/{tour}: {len(out)} surface(s) ({fetched} new) -> {path}")


def _download_wiki_categories(tour: str, d, meta: dict) -> None:
    """Cache each tracked event's Wikipedia main-article tier/category ->
    live/<tour>/wiki_category.json (read offline by data.surface.wiki_category_map). Parallel to
    _download_wiki_surfaces (same idempotent / window-pruned / never-cache-a-miss policy) — the
    tier is needed for the exact new/sponsor-named events the archive can't identify. Best-effort."""
    path = d / "wiki_category.json"
    cached: dict = {}
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — a corrupt cache just means re-fetch
            cached = {}
    out: dict = {}
    fetched = 0
    for name, m in meta.items():
        if cached.get(name):                      # already resolved — keep it
            out[name] = cached[name]
            continue
        year = int((m.get("start") or "2026")[:4] or 2026)
        try:
            cat = event_category(name, year, tour)
        except Exception as e:  # noqa: BLE001 — one bad article must not kill the sweep
            print(f"  wiki-category/{tour}: {name} skipped ({e})")
            cat = None
        if cat:                                   # never cache a miss -> retry when it posts
            out[name] = cat
            fetched += 1
    if out:
        d.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out), encoding="utf-8")
        print(f"  wiki-category/{tour}: {len(out)} categor(ies) ({fetched} new) -> {path}")


if __name__ == "__main__":
    download_wiki_draws()
