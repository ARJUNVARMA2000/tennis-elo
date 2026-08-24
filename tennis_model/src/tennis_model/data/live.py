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
import os
import urllib.request
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from ..config import PLAYER_ALIASES, TOURS, live_dir
from .names import name_key
from .participants import ParticipantContext, ParticipantSource, classify_participant
from .timezones import local_date

# `site.web.api`, NOT the `site.api` host this used until 2026-08-04. That edge began
# 403-ing every request carrying a custom User-Agent — it now admits only the default a
# plain HTTP client sends — and took both tours' overlay down mid-Masters. `site.web.api`
# serves the identical payload under any User-Agent. Do not "simplify" the host back.
SCOREBOARD = "https://site.web.api.espn.com/apis/site/v2/sports/tennis/{tour}/scoreboard"
_ACQUISITION_SCHEMA = "espn-acquisition-v1"
_ACQUISITION_FILE = "espn_acquisition.json"
_OVERLAY_FILES = ("live.csv", "fields.json", "upcoming.csv")

class ScoreboardUnavailable(RuntimeError):
    """Every scoreboard query failed — the overlay is blind, not merely idle."""


def _athlete_name(c: dict | None) -> str | None:
    """Competitor -> canonical athlete name, or None for placeholders like 'TBD'.

    Applying verified aliases at the common ESPN boundary keeps results, live fields and
    upcoming matchups on one identity. Results-only normalization is too late: once a saved
    predictor correctly drops the short-lived duplicate identity, an unnormalized upcoming
    row can no longer resolve to that player's rating and silently disappears.
    """
    athlete = ((c or {}).get("athlete") or {})
    nm = athlete.get("displayName")
    participant = classify_participant(
        nm,
        source=ParticipantSource.ESPN,
        context=ParticipantContext.ATHLETE,
        provider_id=athlete.get("id"),
    )
    if not participant.is_real:
        return None
    return PLAYER_ALIASES.get(name_key(nm), nm)


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
    a 32-draw event; only the draw size disambiguates. The bracket must be large enough to
    contain EVERY populated numbered stage: round id ``r`` with ``n`` matches requires at
    least ``2 * n * 2**(r-1)`` slots. This matters for bye-heavy draws: Cincinnati's
    96-player field has 32 matches in both rounds 1 and 2; round 2 proves a 128-slot bracket
    even though round 1 alone looks like a 64-draw. Power-of-two rounding still absorbs a
    smaller bye field (12 opening matches -> 32 slots)."""
    from collections import Counter
    per_round: Counter = Counter()
    for c in comps:
        rid = (c.get("round") or {}).get("id")
        if isinstance(rid, str) and rid.isdigit() and 1 <= int(rid) <= 4:
            per_round[int(rid)] += 1
    required = [2 * count * (2 ** (rid - 1)) for rid, count in per_round.items()]
    return _next_pow2(max(required)) if required else 0


def _event_venue(ev: dict, name: str | None) -> str | None:
    """Best available location string for the offline timezone resolver."""
    venue = ev.get("venue") or {}
    return venue.get("displayName") or venue.get("fullName") or name


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
        payload = json.loads(r.read())
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError("ESPN scoreboard response has no events list")
    for event in payload["events"]:
        event_id = event.get("id") if isinstance(event, dict) else None
        if (not isinstance(event_id, (str, int)) or isinstance(event_id, bool)
                or not str(event_id).strip()):
            raise ValueError("ESPN scoreboard response contains an event without a stable id")
    return payload["events"]


def parse_events(events: list, gender: str) -> pd.DataFrame:
    """ESPN event objects -> rows in the fresh-overlay schema (completed singles only).

    `gender` is "mens" (ATP) or "womens" (WTA): combined events expose both as separate
    groupings under the same league endpoint, so we keep only the matching tour.
    """
    keep_slug = f"{gender}-singles"
    rows = []
    for ev in events:
        name = ev.get("shortName") or ev.get("name")
        venue = _event_venue(ev, name)
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
                    # The stable identity beside the display name: `tourney_name` is a
                    # sponsor title that churns mid-event, `espn_id` does not.
                    "espn_id": ev.get("id"),
                    "tourney_date": local_date(comp.get("date"), venue),
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


def _acquire_events(tour: str, days_back: int = 14, days_fwd: int = 12) \
        -> tuple[list, dict, Exception | None]:
    """Run the scoreboard sweep and return events plus its structured acquisition fact."""
    attempted_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now(UTC).date()
    offsets = range(-days_fwd, days_back + 1)        # negative = upcoming, positive = past
    queries = [None] + [(today - timedelta(days=k)).strftime("%Y%m%d") for k in offsets]
    seen: dict = {}
    failures: list[tuple[str, Exception]] = []
    succeeded = 0
    for q in queries:
        try:
            for ev in _fetch(tour, q):
                eid = str(ev["id"])
                if eid not in seen:
                    seen[eid] = ev
            succeeded += 1
        except Exception as e:  # noqa: BLE001 — one malformed ESPN query must not kill the scoreboard
            failures.append(("featured" if q is None else q, e))
            continue
    events = list(seen.values())
    if succeeded == 0:
        status = "total_transport_failure"
    elif failures:
        status = "partial_query_failure"
    elif not events:
        status = "success_empty"
    else:
        status = "success"
    failure_types = Counter(type(exc).__name__ for _, exc in failures)
    receipt = {
        "schema": _ACQUISITION_SCHEMA,
        "tour": tour,
        "source": "site.web.api.espn.com",
        "attemptedAt": attempted_at,
        "completedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status,
        "queries": {
            "attempted": len(queries),
            "succeeded": succeeded,
            "failed": len(failures),
            "featuredSucceeded": not any(key == "featured" for key, _ in failures),
            "failedKeys": [key for key, _ in failures],
            "failureTypes": dict(sorted(failure_types.items())),
        },
        "eventCount": len(events),
    }
    return events, receipt, failures[-1][1] if failures else None


def fetch_events(tour: str, days_back: int = 14, days_fwd: int = 12) -> list:
    """Union featured + dated scoreboard queries; empty means ESPN really answered empty.

    The window spans both past completed results and upcoming scheduled matches. Partial
    query failures return their union, while a total failure remains distinguishable from a
    genuinely quiet window.
    """
    events, receipt, last_error = _acquire_events(tour, days_back, days_fwd)
    if receipt["status"] == "total_transport_failure":
        attempted = receipt["queries"]["attempted"]
        raise ScoreboardUnavailable(
            f"all {attempted} scoreboard queries failed; last: {last_error!r}"
        ) from last_error
    return events


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
            # Still keyed by name (readers flip in B3); the id rides INSIDE so a rename can
            # be bridged the way complete-draw cache entries already allow.
            out[name] = {"field": sorted(field), "eliminated": sorted(elim),
                         "espnId": ev.get("id")}
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
        venue = _event_venue(ev, name)
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
                    "tourney_name": name, "espn_id": ev.get("id"),
                    "tourney_date": local_date(comp.get("date"), venue),
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
        venue = _event_venue(ev, name)
        out[str(name)] = {
            "espnId": ev.get("id"),
            "start": local_date(ev.get("date"), venue),
            "end": local_date(ev.get("endDate") or ev.get("date"), venue),
        }
    return out


def _receipt_last_good(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = (payload.get("overlay") or {}).get("lastGoodAt")
        return value if isinstance(value, str) and value else None
    except (OSError, ValueError, AttributeError):
        return None


def _write_atomic(path: Path, writer) -> None:
    """Stage a sibling file and replace only after the complete payload is durable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        writer(tmp)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _write_receipt(path: Path, receipt: dict) -> None:
    """Atomically publish the fact that health.py consumes later in this same run."""
    _write_atomic(path, lambda tmp: tmp.write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"))


def _write_frame(path: Path, frame: pd.DataFrame) -> None:
    _write_atomic(path, lambda tmp: frame.to_csv(tmp, index=False, encoding="utf-8"))


def _write_fields(path: Path, fields: dict) -> None:
    _write_atomic(path, lambda tmp: tmp.write_text(json.dumps(fields), encoding="utf-8"))


def _overlay_receipt(directory: Path, before: set[str], updated: list[str],
                     last_good: str | None, *, processing_failure: Exception | None = None) -> dict:
    retained = sorted(before - set(updated))
    if processing_failure is not None:
        if updated:
            status = "partially_updated"
        else:
            status = "retained_last_good" if retained else "unavailable"
    elif updated and retained:
        status = "partially_updated"
    elif updated:
        status = "updated"
    elif retained:
        status = "retained_last_good"
    else:
        status = "unavailable"
    result = {
        "status": status,
        "updatedFiles": sorted(updated),
        "retainedFiles": retained,
        "lastGoodAt": last_good,
    }
    if processing_failure is not None:
        result["processingFailureType"] = type(processing_failure).__name__
    return result


def download_live(tours=TOURS) -> dict[str, list]:
    """Refresh live overlays and return each successfully fetched raw ESPN event list.

    Complete-draw discovery consumes the same scoreboard window immediately afterward;
    returning the raw response avoids repeating 28 requests per tour. A total failure is
    represented by an explicit empty list so that stage retains cached facts without making
    the same doomed sweep again; the receipt distinguishes that from success-empty."""
    fetched: dict[str, list] = {}
    for tour in tours:
        d = live_dir(tour)
        d.mkdir(parents=True, exist_ok=True)
        receipt_path = d / _ACQUISITION_FILE
        prior_last_good = _receipt_last_good(receipt_path)
        before = {name for name in _OVERLAY_FILES if (d / name).exists()}
        events, receipt, last_error = _acquire_events(tour)
        if receipt["status"] == "total_transport_failure":
            # An explicit empty shared result prevents the immediately-following draw stage
            # from repeating the same 28 doomed requests. Cached draw/live artifacts remain.
            fetched[tour] = []
            receipt["overlay"] = _overlay_receipt(d, before, [], prior_last_good)
            _write_receipt(receipt_path, receipt)
            attempted = receipt["queries"]["attempted"]
            print(f"  live/{tour}: ERROR scoreboard unreachable, overlay is now STALE "
                  f"(all {attempted} queries failed; last: {last_error!r})")
            continue
        queries = receipt["queries"]
        if (receipt["status"] == "partial_query_failure"
                and queries["failed"] >= queries["succeeded"]):
            # A majority-failed sweep is an observed outage, not a usable refresh.  Do not
            # replace a coherent prior overlay with whatever happened to be returned by the
            # minority of queries, and do not feed that incomplete event set to draw discovery.
            fetched[tour] = []
            receipt["overlay"] = _overlay_receipt(d, before, [], prior_last_good)
            _write_receipt(receipt_path, receipt)
            print(f"  live/{tour}: ERROR scoreboard severely degraded; retained prior overlay "
                  f"({queries['failed']} of {queries['attempted']} queries failed)")
            continue
        try:
            fetched[tour] = events
            df = parse_events(events, _gender(tour))
            fields = parse_fields(events, _gender(tour))
            upcoming = parse_upcoming(events, _gender(tour))
        except Exception as e:  # noqa: BLE001 — live overlay is best-effort, never build-fatal
            receipt["overlay"] = _overlay_receipt(
                d, before, [], prior_last_good, processing_failure=e)
            _write_receipt(receipt_path, receipt)
            print(f"  live/{tour}: skipped ({e})")
            continue
        # Record identity BEFORE the per-file writes, and before any `if` that could skip
        # them: a quiet week with no completed matches still needs its events registered, and
        # a rename must be captured the run it happens or the old name is lost.
        from .events import update_registry
        updated: list[str] = []
        try:
            update_registry(tour, parse_event_meta(events))
            if not df.empty:
                _write_frame(d / "live.csv", df)
                updated.append("live.csv")
                print(f"  live/{tour}: {len(df)} matches across {df['tourney_name'].nunique()} events "
                      f"(latest {df['tourney_date'].max()}) -> {d / 'live.csv'}")
            else:
                print(f"  live/{tour}: no completed matches found")
            if fields:
                _write_fields(d / "fields.json", fields)
                updated.append("fields.json")
                print(f"  live/{tour}: fields for {len(fields)} event(s) -> {d / 'fields.json'}")
            if not upcoming.empty:
                _write_frame(d / "upcoming.csv", upcoming)
                updated.append("upcoming.csv")
                print(f"  upcoming/{tour}: {len(upcoming)} scheduled matchups across "
                      f"{upcoming['tourney_name'].nunique()} events -> {d / 'upcoming.csv'}")
        except Exception as e:  # noqa: BLE001 — preserve artifacts, but make the failure observable
            receipt["overlay"] = _overlay_receipt(
                d, before | set(updated), updated, prior_last_good, processing_failure=e)
            _write_receipt(receipt_path, receipt)
            print(f"  live/{tour}: overlay write skipped ({e})")
            continue
        overlay = _overlay_receipt(d, before, updated, prior_last_good)
        if overlay["status"] == "updated" and receipt["status"] == "success":
            overlay["lastGoodAt"] = receipt["completedAt"]
        receipt["overlay"] = overlay
        _write_receipt(receipt_path, receipt)
    return fetched


if __name__ == "__main__":
    download_live()
