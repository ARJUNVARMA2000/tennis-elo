"""Calendar planning ceilings, not expected eligible matches or statistical power."""
import argparse
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import prospective_sources as p
import wta_orders as orders


def capacity(payload, *, start, days=30):
    start = date.fromisoformat(start)
    if type(days) is not int or not 1 <= days <= 90:
        raise ValueError("bounded positive planning window required")
    end = start + timedelta(days=days)
    rows, info = payload.get("content"), payload.get("pageInfo", {})
    if (type(rows) is not list or len(rows) > 100 or info.get("page") != 0
            or info.get("numPages") not in (0, 1) or type(info.get("numEntries")) is not int
            or info["numEntries"] != len(rows) or type(info.get("pageSize")) is not int
            or not len(rows) <= info["pageSize"] <= 100):
        raise ValueError("complete bounded calendar page required")
    grouped, excluded, events = defaultdict(list), [], []
    for row in rows:
        if type(row) is not dict or type(row.get("tournamentGroup")) is not dict:
            raise ValueError("invalid calendar event")
        event, year = row["tournamentGroup"].get("id"), row.get("year")
        if not re.fullmatch(r"[1-9][0-9]{0,7}", str(event)) or type(year) is not int:
            raise ValueError("invalid calendar identity")
        grouped[(str(event), year)].append(row)
    for (event, year), candidates in grouped.items():
        if len({p._digest(r) for r in candidates}) != 1:
            excluded.append({"event": event, "year": year, "reason": "conflicting-duplicate-event"})
            continue
        row = candidates[0]
        reason = None
        level = p._normalized_level(row.get("level"))
        if level is None or level[1] != "main" or level[0] not in {"Grand Slam", "WTA250", "WTA500", "WTA1000"}:
            reason = "outside-individual-main-tour"
        metadata = row["tournamentGroup"].get("metadata", {})
        if row.get("status") in {"cancelled", "canceled"} or str(year) in re.findall(r"\b[0-9]{4}\b", str(metadata.get("cancelledSeasons", ""))):
            reason = "cancelled-edition"
        try:
            begin, finish = date.fromisoformat(row["startDate"]), date.fromisoformat(row["endDate"])
            draw = row.get("singlesDrawSize")
            if begin.year != year or not 0 <= (finish - begin).days <= 21 or type(draw) is not int or not 2 <= draw <= 128:
                raise ValueError("invalid dates or entrants")
            if finish < start or begin >= end:
                reason = reason or "outside-window"
        except (ValueError, KeyError, TypeError):
            reason = "invalid-event-metadata"
        if reason:
            excluded.append({"event": event, "year": year, "reason": reason})
            continue
        if row.get("status") not in {"future", "inProgress", "completed"}:
            excluded.append({"event": event, "year": year, "reason": "unknown-event-status"})
            continue
        started = begin < start or row["status"] != "future"
        scope = "already-started-or-completed" if started else ("fully-contained-future" if finish < end else "partial-future")
        events.append({"event": event, "year": year, "name": row["tournamentGroup"].get("name"),
                       "level": level[0], "start": begin.isoformat(), "end": finish.isoformat(),
                       "entrants": draw, "calendarStatus": row["status"], "scope": scope,
                       "wholeDrawCeiling": draw - 1, "remainingCeilingFromCalendar": None if started else draw - 1})
    totals = {scope: sum(e["wholeDrawCeiling"] for e in events if e["scope"] == scope)
              for scope in ("fully-contained-future", "partial-future")}
    return {"windowStartDate": start.isoformat(), "windowEndExclusiveDate": end.isoformat(), "days": days,
            "scope": "date-based planning in the supplied calendar; not timed evaluator registration",
            "events": sorted(events, key=lambda e: (e["start"], e["event"])), "exclusions": excluded,
            "futureWholeDrawCeilings": totals, "optimisticFutureCeiling": sum(totals.values()),
            "ongoingRemainingUnknown": [e["event"] for e in events if e["remainingCeilingFromCalendar"] is None],
            "guaranteedEligiblePairs": 0, "partialEventsProrated": False, "readyForLiveEvaluation": False}


def read_capacity(root, *, trusted_root, start, days=30):
    receipt, raw = orders.read_inspection(root, trusted_root=trusted_root, media="application/json")
    if raw is None:
        raise ValueError("failed calendar capture")
    parts = urlsplit(receipt["url"])
    query = parse_qs(parts.query)
    if (parts.scheme != "https" or parts.netloc != "api.wtatennis.com" or parts.path != "/tennis/tournaments/"
            or set(query) != {"from", "to", "page", "pageSize"} or any(len(v) != 1 for v in query.values())
            or query["page"] != ["0"] or query["pageSize"] != ["100"] or parts.fragment):
        raise ValueError("unrecognized calendar source")
    if not date.fromisoformat(query["from"][0]) <= date.fromisoformat(start) < date.fromisoformat(query["to"][0]):
        raise ValueError("calendar query does not cover planning start")
    result = capacity(p._json(raw), start=start, days=days)
    if date.fromisoformat(query["to"][0]) < date.fromisoformat(result["windowEndExclusiveDate"]) - timedelta(days=1):
        raise ValueError("calendar query does not cover planning endpoint")
    return {**result, "sourceReceipt": receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calendar", type=Path)
    parser.add_argument("--trusted-root", required=True, type=Path)
    parser.add_argument("--start", required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", required=True, type=Path)
    args = vars(parser.parse_args())
    root, output = args.pop("calendar"), args.pop("output")
    if p.a._absolute_without_symlink_resolution(output).is_relative_to(p.a._absolute_without_symlink_resolution(orders.u.OUTPUT_DIR)):
        raise ValueError("calendar plans cannot enter production output")
    result = read_capacity(root, **args)
    orders._save(output, result, args["trusted_root"])
    print(json.dumps(result["futureWholeDrawCeilings"] | {"optimisticFutureCeiling": result["optimisticFutureCeiling"]}))


if __name__ == "__main__":
    main()
