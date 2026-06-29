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
from datetime import datetime, timedelta, timezone

import pandas as pd

from ..config import TOURS, live_dir

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"


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
            for comp in grp.get("competitions", []) or []:
                stype = (comp.get("status") or {}).get("type") or {}
                if not stype.get("completed"):              # only finished matches
                    continue
                rnd = _round_label((comp.get("round") or {}).get("displayName", ""))
                if rnd is None:
                    continue
                cs = comp.get("competitors") or []
                win = next((c for c in cs if c.get("winner")), None)
                los = next((c for c in cs if c.get("winner") is False), None)
                if not win or not los:
                    continue
                wn = (win.get("athlete") or {}).get("displayName")
                ln = (los.get("athlete") or {}).get("displayName")
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
    today = datetime.now(timezone.utc).date()
    offsets = range(-days_fwd, days_back + 1)        # negative = upcoming, positive = past
    queries = [None] + [(today - timedelta(days=k)).strftime("%Y%m%d") for k in offsets]
    seen: dict = {}
    for q in queries:
        try:
            for ev in _fetch(tour, q):
                eid = ev.get("id")
                if eid and eid not in seen:
                    seen[eid] = ev
        except Exception:
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
            for comp in grp.get("competitions", []) or []:
                if _round_label((comp.get("round") or {}).get("displayName", "")) is None:
                    continue                                  # skip qualifying
                cs = comp.get("competitors") or []
                for c in cs:
                    nm = (c.get("athlete") or {}).get("displayName")
                    if nm:
                        field.add(nm)
                if ((comp.get("status") or {}).get("type") or {}).get("completed"):
                    lc = next((c for c in cs if c.get("winner") is False), None)
                    ln = (lc.get("athlete") or {}).get("displayName") if lc else None
                    if ln:
                        elim.add(ln)
        if len(field) >= 8:
            out[name] = {"field": sorted(field), "eliminated": sorted(elim)}
    return out


def download_live(tours=TOURS) -> None:
    for tour in tours:
        try:
            events = fetch_events(tour)
            df = parse_events(events, _gender(tour))
            fields = parse_fields(events, _gender(tour))
        except Exception as e:
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


if __name__ == "__main__":
    download_live()
