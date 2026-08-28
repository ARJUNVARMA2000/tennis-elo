"""First-party ATP/WTA ordered main draws.

Both tours publish a stable main-draw PDF once the draw is released.  The branded web pages
are presentation layers (ATP's is also Cloudflare-blocked in headless CI), while these PDFs
are the actual provider artifacts:

* ATP: ``protennislive.com/posting/{year}/{event_id}/mds.pdf``
* WTA: ``wtafiles.wtatennis.com/pdf/draws/{year}/{event_id}/MDS.pdf``

This module only discovers provider ids, extracts the ordered first-round slots, and validates
provider evidence.  ``data.draws`` owns source precedence, retention, migration, and the cache.
An ATP/WTA id is never an event join key: the caller supplies ESPN event metadata and live-field
evidence, and a candidate is accepted only after its dates and players agree.
"""

from __future__ import annotations

import csv
import io
import math
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path

from pypdf import PdfReader

from ..config import OFFICIAL_DRAW_ID_OVERRIDES, historical_dir, live_dir
from .participants import (
    ParticipantContext,
    ParticipantKind,
    ParticipantSource,
    canonical_placeholder,
    classify_participant,
)
from .results import _name_key

ATP_PDF = "https://www.protennislive.com/posting/{year}/{source_id}/mds.pdf"
WTA_PDF = "https://wtafiles.wtatennis.com/pdf/draws/{year}/{source_id}/MDS.pdf"
PDF_UA = "Mozilla/5.0 (compatible; Deuce tennis draw monitor)"
_ENTRY_CODES = frozenset({"A", "ALT", "JE", "JR", "LL", "NG", "PR", "Q", "Q/LL", "SE", "WC"})
_GENERIC_EVENT_TOKENS = frozenset({"atp", "by", "championships", "classic", "ladies",
                                   "men", "open", "presented", "tennis", "the", "wta", "women"})
_MONTHS = {m.lower(): i for i, m in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"), start=1)}
_MIN_DATE_OVERLAP_RATIO = 0.5


def official_pdf_url(tour: str, year: int, source_id: str) -> str:
    template = ATP_PDF if tour == "atp" else WTA_PDF
    return template.format(year=year, source_id=source_id)


def _download(url: str, cache_path: Path | None = None, retries: int = 1) -> bytes | None:
    """Bounded binary fetch with a last-good raw artifact fallback.

    Fetch first so an early qualifier PDF can evolve, but retain the previous valid bytes on a
    provider outage/rate limit. A settled normalized draw calls this again only when its active
    event field drifts, so withdrawal revisions can replace stale bytes without hourly churn.
    """
    cached = None
    if cache_path and cache_path.exists():
        try:
            candidate = cache_path.read_bytes()
            cached = candidate if candidate.startswith(b"%PDF") else None
        except OSError:
            cached = None
    attempts = 1 if cached else retries
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": PDF_UA, "Accept": "application/pdf"})
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read()
            if not body.startswith(b"%PDF"):
                return cached
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                temporary = cache_path.with_suffix(".tmp")
                temporary.write_bytes(body)
                temporary.replace(cache_path)
            return body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return cached
            if attempt == attempts - 1:
                return cached
            time.sleep(min(20, 2 ** attempt if exc.code != 429 else 5 * (attempt + 1)))
        except Exception:  # noqa: BLE001 - one provider failure must preserve the last good draw
            if attempt == attempts - 1:
                return cached
            time.sleep(2 ** attempt)
    return cached


def extract_pdf_text(data: bytes) -> str | None:
    """Layout-preserving text from a provider PDF, or ``None`` for a malformed artifact."""
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
    except Exception:  # noqa: BLE001 - a corrupt upstream PDF is a rejected candidate
        return None


def _pretty_name(surname: str, given: str) -> str:
    surname = " ".join(surname.split()).title()
    given = " ".join(given.split())
    return f"{given} {surname}".strip()


def _slot_line(line: str) -> tuple[int, str | None, int | None] | None:
    """Parse one numbered first-round row from ATP/WTA's shared PDF layout."""
    match = re.match(r"^(\s*)(\d{1,3})(\s*)(.+?)\s*$", line)
    if not match:
        return None
    if len(match.group(1)) > 3:  # downstream score/seed tables are deeply indented
        return None
    number, gap, body = int(match.group(2)), match.group(3), match.group(4)
    # PDF text extraction occasionally glues a slot number to its entry marker (`124WC`).
    # A missing gap is valid only for a known marker, otherwise ordinary numbered prose could
    # be mistaken for a player row.
    glued_entry = re.match(r"^([A-Za-z/]{1,4})\s+", body)
    if not gap and (not glued_entry or glued_entry.group(1).upper() not in _ENTRY_CODES):
        return None
    if re.match(r"^Bye(?:\s|$)", body, re.IGNORECASE):
        return number, None, None

    # Remove entry/seed prefixes before parsing the name columns. A very long surname can be
    # clipped before the comma (`VAN DE ZANDSCHULP…`), in which case the live-field
    # reconciliation expands the surname-only token to the unique full player.
    prefix = body.lstrip()
    entry_match = re.match(r"^([A-Za-z/]{1,4})\s+", prefix)
    if entry_match and entry_match.group(1).upper() in _ENTRY_CODES:
        prefix = prefix[entry_match.end():]
    seed = None
    seed_match = re.match(r"^(\d{1,2})\s+", prefix)
    if seed_match:
        seed = int(seed_match.group(1))
        prefix = prefix[seed_match.end():]
    if "," not in prefix:
        clipped = re.split(r"\s{2,}", prefix.strip(), maxsplit=1)[0].strip()
        if clipped and re.search(r"[A-Za-zÀ-ÖØ-öø-ÿﬁ…]", clipped):
            return number, " ".join(clipped.split()).title(), seed
        return None

    before, after = prefix.split(",", 1)
    tokens = before.split()
    if not tokens:
        return None
    surname = " ".join(tokens)
    # The first two-or-more-space gap after the given name starts country/results columns.
    given = re.split(r"\s{2,}", after.strip(), maxsplit=1)[0].strip()
    # Some PDF rows have no country column. Conversely, plain extraction may leave a final
    # three-letter country separated by one space; strip only an all-caps terminal token.
    given = re.sub(r"\s+[A-Z]{3}$", "", given).strip()
    if not given or not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿﬁ…]", given):
        return None
    return number, _pretty_name(surname, given), seed


def parse_official_text(text: str, best_of: int = 3) -> dict | None:
    """Ordered slots/seeds from extracted provider text.

    Numbered lines after the first complete 8..128 contiguous block belong to notes or seeded
    player tables, so the first-round index itself is the geometry contract. Provider PDFs use
    one repeated bare label for every unresolved qualifying seat; number those seats uniquely,
    just like the Wikipedia parser, so distinct entrants cannot collapse in set-backed consumers.
    """
    rows: dict[int, tuple[str | None, int | None]] = {}
    started = False
    for line in (text or "").splitlines():
        parsed = _slot_line(line)
        if not parsed:
            continue
        number, player, seed = parsed
        if number == 1 and not started:
            started = True
        if not started:
            continue
        if number in rows:
            continue
        if number != len(rows) + 1:
            if len(rows) >= 8:
                break
            rows.clear()
            started = number == 1
            if not started:
                continue
        rows[number] = (player, seed)
        if len(rows) == 128:
            break
    size = len(rows)
    if size < 8 or size > 128 or size & (size - 1):
        return None
    slots: list[str | None] = []
    seeds: dict[str, int] = {}
    placeholders: Counter[ParticipantKind] = Counter()
    for i in range(1, size + 1):
        player, seed = rows[i]
        participant = classify_participant(
            player,
            source=ParticipantSource.OFFICIAL,
            context=ParticipantContext.OPENING_DRAW_SLOT,
        )
        if participant.is_placeholder:
            placeholders[participant.kind] += 1
            player = canonical_placeholder(
                participant.kind, placeholders[participant.kind])
        elif participant.kind is ParticipantKind.BYE:
            player = None
        slots.append(player)
        if player and seed is not None:
            seeds[player] = seed
    return {"slots": slots, "seeds": seeds, "bestOf": int(best_of),
            "drawSize": sum(player is not None for player in slots), "bracketSize": size}


def _month(value: str) -> int | None:
    return _MONTHS.get(str(value).strip().lower())


def parse_date_span(text: str, year: int) -> tuple[date, date] | None:
    """Provider calendar range from the PDF header (ATP and WTA date dialects)."""
    header = " ".join((text or "").splitlines()[:12])
    month = "|".join(name.title() for name in _MONTHS)
    patterns = (
        # 27 July — 1 August 2026
        rf"(\d{{1,2}})\s+({month})\s*[–—-]+\s*(\d{{1,2}})\s+({month})\s*,?\s*({year})",
        # July 27 - August 2, 2026
        rf"({month})\s+(\d{{1,2}})\s*[–—-]+\s*({month})\s+(\d{{1,2}})\s*,?\s*({year})",
        # July 27 - 31, 2026
        rf"({month})\s+(\d{{1,2}})\s*[–—-]+\s*(\d{{1,2}})\s*,?\s*({year})",
        # 17 - 24 May 2026
        rf"(\d{{1,2}})\s*[–—-]+\s*(\d{{1,2}})\s+({month})\s*,?\s*({year})",
    )
    for i, pattern in enumerate(patterns):
        found = re.search(pattern, header, re.IGNORECASE)
        if not found:
            continue
        values = found.groups()
        try:
            if i == 0:
                d1, m1, d2, m2, y = values
            elif i == 1:
                m1, d1, m2, d2, y = values
            elif i == 2:
                m1, d1, d2, y = values
                m2 = m1
            else:
                d1, d2, m1, y = values
                m2 = m1
            start_month, end_month, end_year = int(_month(m1)), int(_month(m2)), int(y)
            # WTA sometimes writes a cross-month range without repeating the end month
            # (`July 26-1 2026`). A lower end-day necessarily means the next month.
            if i == 2 and int(d2) < int(d1):
                end_month += 1
                if end_month == 13:
                    end_month, end_year = 1, end_year + 1
            return date(int(y), start_month, int(d1)), date(end_year, end_month, int(d2))
        except (TypeError, ValueError):
            continue
    return None


def _date(value) -> date | None:
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (TypeError, ValueError):
        return None


def _overlaps(a_start, a_end, b_start, b_end) -> bool:
    a1, a2, b1, b2 = _date(a_start), _date(a_end), _date(b_start), _date(b_end)
    return bool(a1 and a2 and b1 and b2 and max(a1, b1) <= min(a2, b2))


def official_dates_match(event_start, event_end, source_start, source_end) -> bool:
    """Whether provider and ESPN spans describe the same event, not adjacent events.

    ESPN includes qualifying while an official PDF can cover only the main draw, so exact
    dates are too strict. Mere intersection is too weak: Toronto and Cincinnati 2026 shared
    three calendar days and 72 players, which attached Toronto's source id 806 to Cincinnati.
    Requiring at least half of the shorter inclusive span preserves nested main-draw windows
    while rejecting a small boundary overlap between consecutive tournaments.
    """
    a1, a2 = _date(event_start), _date(event_end or event_start)
    b1, b2 = _date(source_start), _date(source_end or source_start)
    if not (a1 and a2 and b1 and b2) or a2 < a1 or b2 < b1:
        return False
    overlap = (min(a2, b2) - max(a1, b1)).days + 1
    shorter = min((a2 - a1).days + 1, (b2 - b1).days + 1)
    return overlap > 0 and overlap / shorter >= _MIN_DATE_OVERLAP_RATIO


def _reconcile_slots(slots: list, seeds: dict, evidence_players) -> tuple[list, dict, int]:
    """Canonicalize provider abbreviations against this event's live field, one-to-one."""
    evidence = [str(player) for player in dict.fromkeys(evidence_players or ()) if player]
    by_key = {_name_key(player): player for player in evidence}
    used: set[str] = set()
    mapped: dict[str, str] = {}
    for raw in (player for player in slots if player):
        key = _name_key(raw)
        if key in by_key and key not in used:
            mapped[raw] = by_key[key]
            used.add(key)
            continue
        raw_tokens = set(key.split())
        candidates = []
        for player in evidence:
            pkey = _name_key(player)
            if pkey in used:
                continue
            shared = raw_tokens & set(pkey.split())
            if not shared:
                continue
            # Require a substantive shared token (normally the surname), then prefer the
            # greatest token overlap. This expands PDF clipping (`Francis… Cerundolo`) and
            # provider short names (`Coleman Wong` / `Chak Lam Coleman Wong`) safely.
            anchor = max((len(token) for token in shared), default=0)
            if anchor >= 4:
                candidates.append((len(shared), anchor, player))
        if candidates:
            candidates.sort(reverse=True)
            best_score = candidates[0][:2]
            winners = [player for shared, anchor, player in candidates if (shared, anchor) == best_score]
            if len(winners) == 1:
                mapped[raw] = winners[0]
                used.add(_name_key(winners[0]))
    resolved_slots = [mapped.get(player, player) if player else None for player in slots]
    resolved_seeds = {mapped.get(player, player): seed for player, seed in seeds.items()}
    shared_count = len({_name_key(player) for player in resolved_slots if player} & set(by_key))
    return resolved_slots, resolved_seeds, shared_count


@lru_cache(maxsize=8)
def _atp_archive_catalog(year: int) -> tuple[dict, ...]:
    """Stable ATP ids and seasonal dates from the five preceding archive editions."""
    latest: dict[str, dict] = {}
    for edition in range(year - 5, year):
        path = historical_dir("atp") / f"{edition}.csv"
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    tid = str(row.get("tourney_id") or "")
                    match = re.search(r"-(\d+)$", tid)
                    stamp = re.sub(r"\D", "", str(row.get("tourney_date") or ""))
                    if not match or len(stamp) != 8:
                        continue
                    source_id = match.group(1)
                    latest[source_id] = {
                        "id": source_id, "name": row.get("tourney_name"),
                        "date": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}",
                        "level": row.get("tourney_level"), "edition": edition,
                    }
        except (OSError, csv.Error):
            continue
    return tuple(latest.values())


def _seasonal_delta(current: date, previous: date) -> int:
    try:
        projected = previous.replace(year=current.year)
    except ValueError:  # February 29 into a non-leap year
        projected = previous.replace(year=current.year, day=28)
    return abs((projected - current).days)


def atp_candidate_ids(year: int, meta: dict, registry_entry: dict | None = None) -> list[dict]:
    start = _date(meta.get("start")) or date(year, 1, 1)
    catalog = list(_atp_archive_catalog(year))
    catalog_by_id = {str(item.get("id")): item for item in catalog if item.get("id")}
    preferred = []
    event_id = str(meta.get("espnId") or "")
    saved = str(((registry_entry or {}).get("sourceIds") or {}).get("atp") or "")
    override = str(OFFICIAL_DRAW_ID_OVERRIDES.get("atp", {}).get(event_id) or "")
    for source_id in (override, saved):
        if source_id and source_id not in {item["id"] for item in preferred}:
            # Persisting the provider ID must not discard archive metadata that changes
            # match format. An unsettled ATP Slam is refetched through this preferred path;
            # without its level="G", bestOf silently regressed from five to three.
            preferred.append({
                **catalog_by_id.get(source_id, {}),
                "id": source_id,
                "trusted": source_id == saved,
            })
    candidates = []
    for item in catalog:
        previous = _date(item.get("date"))
        if previous is None:
            continue
        delta = _seasonal_delta(start, previous)
        if delta <= 45:
            candidates.append({**item, "delta": delta, "trusted": False})
    target_tokens = set(_name_key(meta.get("name") or "").split()) - _GENERIC_EVENT_TOKENS
    candidates.sort(key=lambda item: (
        -len(target_tokens & set(_name_key(item.get("name") or "").split())),
        item["delta"], -int(item.get("edition") or 0)))
    seen = {item["id"] for item in preferred}
    return preferred + [item for item in candidates if item["id"] not in seen][:10]


@lru_cache(maxsize=4)
def wta_catalog(year: int) -> tuple[dict, ...]:
    """Official WTA tournament calendar, including 125s (draw coverage is not model scope)."""
    try:
        from .wta_stats import _paged
        items = _paged("/tournaments/", "content",
                       {"from": f"{year}-01-01", "to": f"{year}-12-31"})
    except Exception:  # noqa: BLE001 - cached/provider-id paths can still succeed
        return ()
    out = []
    for item in items:
        group = item.get("tournamentGroup") or {}
        source_id = group.get("id")
        if source_id is None or str(item.get("level") or "").upper() == "ITF":
            continue
        out.append({"id": str(source_id), "name": group.get("name"),
                    "start": str(item.get("startDate") or "")[:10],
                    "end": str(item.get("endDate") or item.get("startDate") or "")[:10],
                    "level": item.get("level"), "trusted": False})
    return tuple(out)


def wta_candidate_ids(year: int, meta: dict, registry_entry: dict | None = None) -> list[dict]:
    event_id = str(meta.get("espnId") or "")
    saved = str(((registry_entry or {}).get("sourceIds") or {}).get("wta") or "")
    override = str(OFFICIAL_DRAW_ID_OVERRIDES.get("wta", {}).get(event_id) or "")
    preferred = []
    for source_id in (override, saved):
        if source_id and source_id not in {item["id"] for item in preferred}:
            preferred.append({"id": source_id, "trusted": bool(saved)})
    nearby = [dict(item) for item in wta_catalog(year)
              if _overlaps(meta.get("start"), meta.get("end") or meta.get("start"),
                           item.get("start"), item.get("end"))]
    # Display-name tokens only order network attempts; acceptance still requires dates plus
    # player evidence. This makes obvious calendar matches cheap without turning names into ids.
    target_tokens = set(_name_key(meta.get("name") or "").split()) - _GENERIC_EVENT_TOKENS
    nearby.sort(key=lambda item: len(target_tokens & set(_name_key(item.get("name") or "").split())),
                reverse=True)
    seen = {item["id"] for item in preferred}
    return preferred + [item for item in nearby if item["id"] not in seen]


def fetch_official_draw(tour: str, year: int, meta: dict, registry_entry: dict | None,
                        evidence_players) -> tuple[dict | None, list[str]]:
    """First validated provider draw for one ESPN event plus human-readable rejections."""
    candidates = (atp_candidate_ids(year, meta, registry_entry) if tour == "atp"
                  else wta_candidate_ids(year, meta, registry_entry))
    rejected: list[str] = []
    accepted: list[tuple[int, dict]] = []
    evidence_total = len({_name_key(player) for player in evidence_players or () if player})
    # One event can overlap several tour calendars. Bound the request fan-out so an upstream
    # throttle never turns this best-effort overlay into the slowest hourly pipeline step.
    for candidate in candidates[:6]:
        source_id = str(candidate["id"])
        url = official_pdf_url(tour, year, source_id)
        raw_cache = live_dir(tour) / "official_draw_pdfs" / f"{year}-{source_id}.pdf"
        body = _download(url, raw_cache)
        if not body:
            rejected.append(f"{tour}:{source_id} unavailable")
            continue
        text = extract_pdf_text(body)
        span = parse_date_span(text or "", year)
        best_of = 5 if tour == "atp" and str(candidate.get("level") or "").upper() == "G" else 3
        draw = parse_official_text(text or "", best_of=best_of)
        if not draw:
            rejected.append(f"{tour}:{source_id} malformed draw geometry")
            continue
        if not span or not official_dates_match(
                meta.get("start"), meta.get("end") or meta.get("start"),
                span[0].isoformat(), span[1].isoformat()):
            rejected.append(f"{tour}:{source_id} calendar overlap is too small for ESPN event")
            continue
        slots, seeds, shared = _reconcile_slots(draw["slots"], draw["seeds"], evidence_players)
        required = max(2, math.ceil(evidence_total * 0.75))
        if shared < required:
            rejected.append(f"{tour}:{source_id} matches {shared}/{evidence_total} live players "
                            f"(minimum {required})")
            continue
        title = next((line.strip() for line in (text or "").splitlines() if line.strip()), "")
        record = {**draw, "slots": slots, "seeds": seeds,
                  "source": tour, "sourceId": source_id, "sourceUrl": url,
                  "sourceTitle": title, "sourceStart": span[0].isoformat(),
                  "sourceEnd": span[1].isoformat(), "evidencePlayers": shared,
                  "evidenceFieldPlayers": evidence_total,
                  "retrieved": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
        if shared == evidence_total:
            return record, rejected
        accepted.append((shared, record))
    if not accepted:
        return None, rejected
    accepted.sort(key=lambda item: item[0], reverse=True)
    best = accepted[0][0]
    winners = [record for shared, record in accepted if shared == best]
    if len(winners) != 1:
        rejected.append(f"{tour}: ambiguous official draw candidates share {best} players")
        return None, rejected
    return winners[0], rejected
