"""Live results from ESPN's keyless tennis scoreboard API.

The free community mirror lags ~1 week; ESPN's hidden scoreboard endpoint carries the
current and in-progress events (including Grand Slams) same-day, keyless, for both
tours. We pull completed singles matches, normalise them to the fresh-overlay schema,
and write them to fresh_dir/live.csv so the existing loader merges + de-dups them like
any other results row (preferring stat-bearing rows, so once the mirror catches up the
fuller version wins). Surface / best-of / level are absent from ESPN and get backfilled
by tournament name from the historical archive in the loader.

A single scoreboard call returns the featured event(s) with their FULL match list; we
also sweep recent individual days and union by event id so concurrent and just-finished
tournaments are captured too. Best-effort: any failure leaves the existing data intact.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime, timedelta

import pandas as pd

from ..config import TOURS, live_dir

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"

# ESPN fills an undetermined slot in a scheduled match (opponent awaiting a prior
# result, or a draw not yet published) with a pseudo-athlete named "TBD" — a
# placeholder, not a player. It must never enter a field / matchup / result row:
# one leaked "TBD" makes a 128-player Slam draw count 129.
_PLACEHOLDER_NAMES = {"tbd", "tba", "bye", "qualifier"}


def _athlete_name(c: dict | None) -> str | None:
    """Competitor -> athlete displayName, or None for draw placeholders like 'TBD'."""
    nm = ((c or {}).get("athlete") or {}).get("displayName")
    if not isinstance(nm, str) or nm.strip().lower() in _PLACEHOLDER_NAMES:
        return None
    return nm


def _round_label(disp: str) -> str | None:
    """Map an ESPN round name to our codes; None drops the match (qualifying/doubles)."""
    d = (disp or "").lower()
    if "qualif" in d:
        return None
    if d.startswith("final"):
        return "F"
    if "semi" in d:
        return "SF"
    if "quarter" in d:
        return "QF"
    if "16" in d or "fourth" in d or "4th" in d:
        return "R16"
    if "third" in d or "3rd" in d:
        return "R32"
    if "second" in d or "2nd" in d:
        return "R64"
    if "first" in d or "1st" in d:
        return "R128"
    return "R64"          # generic main-draw round (only "F" must be exact for status)


def _next_pow2(n: int) -> int:
    p = 1
    while p < n:
        p <<= 1
    return p


def _draw_size(comps: list) -> int:
    """Main-draw bracket size for one event grouping, or 0 if indeterminable.

    ESPN numbers main-draw rounds from 1 (id 1 = the opening, most-populous round) and always
    tags QF/SF/F as ids 5/6/7 — so the *label* "Round 2" is R64 at a 128-draw Slam but R16 at
    a 32-draw event; only the draw size disambiguates. We take it as the next power of two
    >= 2 x (largest numbered round's match count): the opening round ships complete when the
    draw is published, so it fixes the size even mid-event, and the power-of-two rounding
    absorbs byes (a 28-player field brackets as 32)."""
    from collections import Counter
    per_round: Counter = Counter()
    for c in comps:
        rid = (c.get("round") or {}).get("id")
        if isinstance(rid, str) and rid.isdigit() and 1 <= int(rid) <= 4:
            per_round[int(rid)] += 1
    return _next_pow2(2 * max(per_round.values())) if per_round else 0


def _round_code(rnd: dict, draw: int) -> str | None:
    """ESPN round object + the event's draw size -> our round code (None drops the match).

    The numbered main-draw rounds (ESPN ids 1-4, labelled "Round N") are draw-relative and
    resolved against `draw`; qualifying is dropped; everything else (QF/SF/F, or any other
    wording) falls to the draw-agnostic name map. Keeps the historical vocabulary
    (R128/R64/R32/R16/QF/SF/F)."""
    disp = (rnd or {}).get("displayName", "")
    if "qualif" in disp.lower():
        return None
    rid = (rnd or {}).get("id")
    if draw and isinstance(rid, str) and rid.isdigit() and 1 <= int(rid) <= 4:
        size = draw >> (int(rid) - 1)                # id 1 = full draw, halving each round
        return {8: "QF", 4: "SF", 2: "F"}.get(size, f"R{size}")
    return _round_label(disp)


def _score(win_ls: list, los_ls: list) -> str:
    """Winner-perspective games string, e.g. '6-7 6-4 7-5' (tiebreak points dropped)."""
    sets = []
    for ws, ls in zip(win_ls or [], los_ls or []):
        try:
            sets.append(f"{int(round(ws.get('value', 0)))}-{int(round(ls.get('value', 0)))}")
        except (TypeError, ValueError):
            continue
    return " ".join(sets)


def _fetch(tour: str, datestr: str | None = None) -> list:
    url = SCOREBOARD.format(tour=tour) + (f"?dates={datestr}&limit=300" if datestr else "?limit=300")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 tennis_model"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("events", []) or []


def parse_events(events: list, gender: str) -> pd.DataFrame:
    """ESPN event objects -> rows in the fresh-overlay schema (completed singles only).

    `gender` is "mens" (ATP) or "womens" (WTA): combined events expose both as separate
    groupings under the same league endpoint, so we keep only the matching tour.
    """
    keep_slug = f"{gender}-singles"
    rows = []
    for ev in events:
        name = ev.get("shortName") or ev.get("name")
        for grp in ev.get("groupings", []) or []:
            slug = (grp.get("grouping") or {}).get("slug", "")
            if slug != keep_slug:                           # skip doubles + the other tour
                continue
            comps = grp.get("competitions", []) or []
            draw = _draw_size(comps)
            for comp in comps:
                stype = (comp.get("status") or {}).get("type") or {}
                if not stype.get("completed"):              # only finished matches
                    continue
                rnd = _round_code(comp.get("round") or {}, draw)
                if rnd is None:
                    continue
                cs = comp.get("competitors") or []
                win = next((c for c in cs if c.get("winner")), None)
                los = next((c for c in cs if c.get("winner") is False), None)
                if not win or not los:
                    continue
                wn = _athlete_name(win)
                ln = _athlete_name(los)
                if not wn or not ln:
                    continue
                rows.append({
                    "tourney_name": name,
                    "tourney_date": (comp.get("date") or "")[:10],   # YYYY-MM-DD
                    "round": rnd,
                    "best_of": None, "surface": None, "tourney_level": None,
                    "winner_name": wn, "loser_name": ln,
                    "score": _score(win.get("linescores"), los.get("linescores")),
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["tourney_name", "winner_name", "loser_name", "score"])
    return df


def _gender(tour: str) -> str:
    return "mens" if tour == "atp" else "womens"


def fetch_events(tour: str, days_back: int = 14, days_fwd: int = 12) -> list:
    """Union of the featured event(s) + a per-day sweep over a window (dedup by id).

    The window spans both **past** days (completed results) and **upcoming** days
    (scheduled matches) so a live event's FULL field is captured — e.g. a Slam's
    Day-2/3 players, whose matches haven't happened yet, still appear in the draw."""
    today = datetime.now(UTC).date()
    offsets = range(-days_fwd, days_back + 1)        # negative = upcoming, positive = past
    queries = [None] + [(today - timedelta(days=k)).strftime("%Y%m%d") for k in offsets]
    seen: dict = {}
    for q in queries:
        try:
            for ev in _fetch(tour, q):
                eid = ev.get("id")
                if eid and eid not in seen:
                    seen[eid] = ev
        except Exception:  # noqa: BLE001 — one malformed ESPN query must not kill the scoreboard
            continue
    return list(seen.values())


def fetch_live(tour: str, days_back: int = 14) -> pd.DataFrame:
    return parse_events(fetch_events(tour, days_back), _gender(tour))


def parse_fields(events: list, gender: str) -> dict:
    """Per active event: the FULL main-draw singles field + who's been eliminated, taken
    from every main-draw match (completed, in-progress, AND scheduled). This lets the
    projector seed a live Slam with its real field on Day 1 — not just the handful of
    players who happen to have finished a match — so the favourite is correct."""
    keep = f"{gender}-singles"
    out = {}
    for ev in events:
        name = ev.get("shortName") or ev.get("name")
        field, elim = set(), set()
        for grp in ev.get("groupings", []) or []:
            if (grp.get("grouping") or {}).get("slug", "") != keep:
                continue
            comps = grp.get("competitions", []) or []
            draw = _draw_size(comps)
            for comp in comps:
                if _round_code(comp.get("round") or {}, draw) is None:
                    continue                                  # skip qualifying
                cs = comp.get("competitors") or []
                for c in cs:
                    nm = _athlete_name(c)
                    if nm:
                        field.add(nm)
                if ((comp.get("status") or {}).get("type") or {}).get("completed"):
                    lc = next((c for c in cs if c.get("winner") is False), None)
                    ln = _athlete_name(lc)
                    if ln:
                        elim.add(ln)
        if len(field) >= 8:
            out[name] = {"field": sorted(field), "eliminated": sorted(elim)}
    return out


def parse_upcoming(events: list, gender: str) -> pd.DataFrame:
    """ESPN event objects -> scheduled/in-progress singles matchups (not yet completed).

    Mirror of `parse_events`, but keeps competitions whose status state is "pre"
    (scheduled) or "in" (in-progress) with both competitors already known. Orientation
    is arbitrary (playerA/playerB) — the match has no winner yet — which is the point:
    these power point-in-time forecast logging (eval/track) *before* results exist.
    """
    keep = f"{gender}-singles"
    rows = []
    for ev in events:
        name = ev.get("shortName") or ev.get("name")
        for grp in ev.get("groupings", []) or []:
            if (grp.get("grouping") or {}).get("slug", "") != keep:
                continue
            comps = grp.get("competitions", []) or []
            draw = _draw_size(comps)
            for comp in comps:
                stype = (comp.get("status") or {}).get("type") or {}
                if stype.get("completed") or stype.get("state") not in ("pre", "in"):
                    continue                                # only not-yet-finished matchups
                rnd = _round_code(comp.get("round") or {}, draw)
                if rnd is None:
                    continue
                names = [_athlete_name(c) for c in (comp.get("competitors") or [])]
                names = [n for n in names if n]
                if len(names) < 2:                          # matchup not set yet (TBD player)
                    continue
                rows.append({
                    "tourney_name": name,
                    "tourney_date": (comp.get("date") or "")[:10],   # YYYY-MM-DD
                    "round": rnd, "playerA": names[0], "playerB": names[1],
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["tourney_name", "playerA", "playerB"])
    return df


def parse_event_meta(events: list) -> dict:
    """Per event: {name: {espnId, start, end}} from the scoreboard event objects.

    Event-level (gender-agnostic) — dates come straight from ESPN's `date`/`endDate`
    even for not-yet-started, all-TBD events, which is what lets draws_wiki discover an
    upcoming tournament and stamp its projection before any match is played."""
    out: dict = {}
    for ev in events:
        name = ev.get("shortName") or ev.get("name")
        if not name or name in out:
            continue
        out[str(name)] = {
            "espnId": ev.get("id"),
            "start": (ev.get("date") or "")[:10],
            "end": (ev.get("endDate") or ev.get("date") or "")[:10],
        }
    return out


def download_live(tours=TOURS) -> None:
    for tour in tours:
        try:
            events = fetch_events(tour)
            df = parse_events(events, _gender(tour))
            fields = parse_fields(events, _gender(tour))
            upcoming = parse_upcoming(events, _gender(tour))
        except Exception as e:  # noqa: BLE001 — live overlay is best-effort, never build-fatal
            print(f"  live/{tour}: skipped ({e})")
            continue
        d = live_dir(tour)
        d.mkdir(parents=True, exist_ok=True)
        if not df.empty:
            df.to_csv(d / "live.csv", index=False, encoding="utf-8")
            print(f"  live/{tour}: {len(df)} matches across {df['tourney_name'].nunique()} events "
                  f"(latest {df['tourney_date'].max()}) -> {d / 'live.csv'}")
        else:
            print(f"  live/{tour}: no completed matches found")
        if fields:
            (d / "fields.json").write_text(json.dumps(fields), encoding="utf-8")
            print(f"  live/{tour}: fields for {len(fields)} event(s) -> {d / 'fields.json'}")
        if not upcoming.empty:
            upcoming.to_csv(d / "upcoming.csv", index=False, encoding="utf-8")
            print(f"  upcoming/{tour}: {len(upcoming)} scheduled matchups across "
                  f"{upcoming['tourney_name'].nunique()} events -> {d / 'upcoming.csv'}")


if __name__ == "__main__":
    download_live()
