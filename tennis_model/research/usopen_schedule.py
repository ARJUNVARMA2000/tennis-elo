"""Immutable official US Open schedule observations; never actual-start evidence.

Manual collect: at most a catalogue and its selected released daily order. History
replays the explicitly supplied archives. Retained fixture import is retrospective.
"""
import argparse
import gzip
import hashlib
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import prospective_sources as p
from tennis_model.config import OUTPUT_DIR
from tennis_model.data.participants import is_real_participant
from tennis_model.eval.prospective import _bytes, _digest, _time
from tennis_model.model import artifact as a

SCHEMA = "usopen-schedule-observation-v1"
ZONE = ZoneInfo("America/New_York")
FIXTURES = Path(__file__).parents[1] / "tests/fixtures/usopen_schedule"
ROUNDS = {**{str(i): f"Round {i}" for i in range(1, 5)},
          "Q": "Quarterfinals", "S": "Semifinals", "F": "Final"}


def endpoint(year, day=None):
    if type(year) is not int or not 2000 <= year <= 2100:
        raise ValueError("explicit edition required")
    if day is not None and (type(day) is not int or not 1 <= day <= 60):
        raise ValueError("explicit tournament day required")
    suffix = "Days" if day is None else str(day)
    return f"https://www.usopen.org/en_US/scores/feeds/{year}/schedule/schedule{suffix}.json"


def _mkdir(path, trusted_root):
    path = a._absolute_without_symlink_resolution(path)
    if path.is_relative_to(a._absolute_without_symlink_resolution(OUTPUT_DIR)):
        raise ValueError("schedule archives cannot enter production output")
    with a._open_artifact_parent(path, trusted_root=trusted_root) as (fd, name):
        os.mkdir(name, mode=0o700, dir_fd=fd)
        os.fsync(fd)
    return path


def _save(path, body, trusted_root):
    body = {**body, "schema": SCHEMA}
    p._write(path, _bytes({**body, "sha256": _digest(body)}), trusted_root)


def _load(path, trusted_root):
    body = p._json(p._read(path, trusted_root))
    if type(body) is not dict or body.get("schema") != SCHEMA:
        raise ValueError("schedule schema mismatch")
    digest = body.get("sha256")
    if digest != _digest({k: v for k, v in body.items() if k != "sha256"}):
        raise ValueError("schedule document integrity failure")
    return body


def fetch_once(root, *, trusted_root, year, day=None):
    url = endpoint(year, day)
    root = _mkdir(root, trusted_root)
    attempt = {"url": url, "edition": year, "day": day,
               "requestedAt": p._now().isoformat(), "provenance": "network-observation",
               "adapterSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    _save(root / "attempt.json", attempt, trusted_root)
    receipt, raw, started = dict(attempt), b"", time.monotonic()
    receipt.update(outcome="failed", rawComplete=False)
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; DEUCE schedule research)",
            "Accept": "application/json", "Accept-Encoding": "identity", "Cache-Control": "no-cache"})
        opener = urllib.request.build_opener(p._NoRedirect())
        try:
            response = opener.open(request, timeout=25)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            receipt.update(status=response.status, responseUrl=response.geturl(),
                           headers={k.lower(): v for k, v in response.headers.items()
                                    if k.lower() in p.HTTP_HEADERS})
            raw = response.read(p.MAX_BODY + 1)
        receipt["rawComplete"] = len(raw) <= p.MAX_BODY
        _validate_http(receipt, raw)
        receipt["outcome"] = "ok"
    except (OSError, ValueError, http.client.HTTPException) as exc:
        if isinstance(exc, http.client.IncompleteRead):
            raw = exc.partial[:p.MAX_BODY + 1]
        receipt["failure"] = f"{type(exc).__name__}: {exc}"[:1000]
    receipt.update(receivedAt=p._now().isoformat(), elapsedSeconds=time.monotonic() - started,
                   rawBytes=len(raw), rawSHA256=hashlib.sha256(raw).hexdigest())
    if _time(receipt["receivedAt"]) < _time(receipt["requestedAt"]):
        receipt.update(outcome="failed", failure="local acquisition clock regression")
    p._write(root / "response.bin", raw, trusted_root)
    _save(root / "receipt.json", receipt, trusted_root)
    return read_capture(root, trusted_root=trusted_root)


def _validate_http(receipt, raw):
    headers = receipt.get("headers", {})
    if (receipt.get("status") != 200 or receipt.get("responseUrl") != receipt["url"]
            or not receipt.get("rawComplete") or len(raw) > p.MAX_BODY
            or headers.get("content-type", "").split(";", 1)[0].strip() != "application/json"
            or headers.get("content-encoding", "identity").lower() != "identity"):
        raise ValueError("invalid status, URL, body size, media or encoding")
    length = headers.get("content-length")
    if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) != len(raw)):
        raise ValueError("incomplete or conflicting body length")
    payload = p._json(raw)
    if type(payload) is not dict:
        raise ValueError("JSON object required")
    return payload


def _fixture(name):
    manifest = p._json((FIXTURES / "manifest.json").read_bytes())
    entry = manifest[name]
    encoded = (FIXTURES / f"{name}.json.gz").read_bytes()
    if hashlib.sha256(encoded).hexdigest() != entry["compressedSHA256"]:
        raise ValueError("fixture archive integrity failure")
    raw = gzip.decompress(encoded)
    if hashlib.sha256(raw).hexdigest() != entry["rawSHA256"]:
        raise ValueError("fixture raw integrity failure")
    return entry, raw


def _import_capture(root, trusted_root, name, day):
    entry, raw = _fixture(name)
    upstream = entry["receipt"]
    root = _mkdir(root, trusted_root)
    attempt = {"url": endpoint(2026, day), "edition": 2026, "day": day,
               "requestedAt": upstream["requestedAt"], "provenance": "pinned-retrospective-import",
               "fixture": name, "importedAt": p._now().isoformat()}
    _save(root / "attempt.json", attempt, trusted_root)
    p._write(root / "response.bin", raw, trusted_root)
    _save(root / "receipt.json", {**upstream, **attempt, "outcome": "ok",
                                  "upstreamReceipt": upstream}, trusted_root)
    return read_capture(root, trusted_root=trusted_root)


def read_capture(root, *, trusted_root):
    root = Path(root)
    receipt = _load(root / "receipt.json", trusted_root)
    attempt = _load(root / "attempt.json", trusted_root)
    if any(receipt.get(k) != v for k, v in attempt.items() if k not in {"sha256", "schema"}):
        raise ValueError("request/receipt mismatch")
    if receipt["url"] != endpoint(receipt["edition"], receipt["day"]):
        raise ValueError("noncanonical source URL")
    raw = p._read(root / "response.bin", trusted_root)
    if len(raw) != receipt["rawBytes"] or hashlib.sha256(raw).hexdigest() != receipt["rawSHA256"]:
        raise ValueError("raw response integrity failure")
    provenance = receipt.get("provenance")
    if provenance == "pinned-retrospective-import":
        entry, _ = _fixture(receipt["fixture"])
        if (receipt["upstreamReceipt"] != entry["receipt"] or receipt["rawSHA256"] != entry["rawSHA256"]
                or any(receipt.get(k) != v for k, v in entry["receipt"].items() if k != "schema")):
            raise ValueError("retrospective fixture provenance mismatch")
    elif provenance != "network-observation":
        raise ValueError("unknown acquisition provenance")
    if receipt["outcome"] == "failed":
        return receipt, None
    if receipt["outcome"] != "ok" or _time(receipt["receivedAt"]) < _time(receipt["requestedAt"]):
        raise ValueError("invalid acquisition outcome or clock")
    return receipt, _validate_http(receipt, raw)


def _listing(payload, year, day):
    if type(payload) is not dict or type(payload.get("eventDays")) is not list:
        raise ValueError("missing catalogue days")
    all_rows = payload["eventDays"]
    if len(all_rows) > 61 or any(type(row) is not dict for row in all_rows):
        raise ValueError("malformed catalogue rows")
    # The real catalogue includes a practice link with a null tournament day.
    # It cannot locate an order and is explicitly outside this collector's scope.
    rows = [row for row in all_rows if not (row.get("practice") is True and row.get("tournDay") is None)]
    ids = [row.get("tournDay") for row in rows if type(row) is dict]
    if (len(ids) != len(rows) or len(rows) > 60
            or any(type(i) is not int or not 1 <= i <= 60 for i in ids) or len(set(ids)) != len(ids)):
        raise ValueError("malformed or duplicate catalogue day")
    selected = [row for row in rows if row["tournDay"] == day]
    if not selected:
        raise ValueError("selected day missing from catalogue")
    row = selected[0]
    if row.get("released") is not True:
        raise ValueError("day not released")
    if row.get("feedUrl") != endpoint(year, day):
        raise ValueError("catalogue endpoint edition/day/host conflict")
    if row.get("quals") is not False or row.get("practice") is not False:
        raise ValueError("outside main event schedule")
    return row


def _date(label, year):
    if type(label) is not str or not re.fullmatch(r"Day [0-9]+: [A-Za-z]+, [A-Za-z]+ [0-9]{1,2}", label):
        raise ValueError("invalid explicit calendar label")
    value = label.split(": ", 1)[1]
    result = datetime.strptime(f"{value}, {year}", "%A, %B %d, %Y").date()
    if result.strftime("%A") != value.split(",")[0]:
        raise ValueError("edition/weekday conflict")
    return result


def _clock(date, text):
    if type(text) is not str or not re.fullmatch(r"(?:[1-9]|1[0-2]):[0-5][0-9] [AP]M", text):
        raise ValueError("ambiguous local clock")
    result = datetime.combine(date, datetime.strptime(text, "%I:%M %p").time(), ZONE)
    if (result.utcoffset() != result.replace(fold=1).utcoffset()
            or result.astimezone(UTC).astimezone(ZONE) != result):
        raise ValueError("ambiguous venue offset")
    return result


def normalize(catalogue, payload, *, year, day, receipt, catalogue_receipt):
    """Pure schedule extraction; callers must verify receipt-to-raw binding first."""
    listing = _listing(catalogue, year, day)
    if type(payload) is not dict or type(payload.get("day")) is not int or payload["day"] != day:
        raise ValueError("daily edition/day conflict")
    date = _date(payload.get("displayDate"), year)
    if _date(listing.get("message"), year) != date or listing["message"] != payload["displayDate"]:
        raise ValueError("catalogue/daily date conflict")
    courts = payload.get("courts")
    if type(courts) is not list or not courts or len(courts) > 100:
        raise ValueError("missing or invalid courts; not an empty authoritative order")
    observations, exclusions, anomalies = [], [], []
    try:
        if datetime.fromtimestamp(listing["epoch"], ZONE).date() != date:
            anomalies.append("catalogue-epoch-date-disagreement")
    except (KeyError, ValueError, TypeError, OSError, OverflowError):
        anomalies.append("catalogue-epoch-unusable")
    fresh = {"catalogue": p.freshness(catalogue_receipt, now=_time(receipt["receivedAt"])),
             "daily": p.freshness(receipt, now=_time(receipt["receivedAt"]))}
    complete = all(v["ready"] for v in fresh.values())
    ids, locations, census = set(), set(), Counter()
    for ci, court in enumerate(courts):
        if type(court) is not dict:
            raise ValueError("malformed court")
        cid, session = court.get("courtId"), court.get("session")
        if type(cid) is not str or not cid or type(session) is not int or session < 1:
            raise ValueError("malformed court/session")
        location = (cid, session)
        if location in locations:
            raise ValueError("duplicate court/session")
        locations.add(location)
        start = _clock(date, court.get("time"))
        if type(court.get("startEpoch")) is not int or start.timestamp() != court["startEpoch"]:
            raise ValueError("court epoch/date/venue-clock conflict")
        rows = court.get("matches")
        if type(rows) is not list or len(rows) > 256:
            raise ValueError("missing or invalid match list")
        orders = set()
        for ri, row in enumerate(rows):
            path = f"/courts/{ci}/matches/{ri}"
            if type(row) is not dict:
                raise ValueError("malformed match row")
            code, mid, order = row.get("eventCode"), row.get("match_id"), row.get("order")
            census[str(code)] += 1
            if type(order) is not int or order < 1 or order in orders:
                raise ValueError("malformed or duplicate match order")
            orders.add(order)
            if type(mid) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", mid) or mid in ids:
                raise ValueError("malformed or duplicate match ID")
            ids.add(mid)
            if code != "WS":
                blank = code is None and not row.get("team1") and not row.get("team2")
                exclusions.append({"path": path, "sourceMatchId": mid,
                                   "reason": "intentional-blank" if blank else "outside-WTA-singles"})
                if code is None and not blank:
                    complete = False
                continue
            try:
                if row.get("courtId") != cid or ROUNDS.get(row.get("roundCode")) != row.get("roundName"):
                    raise ValueError("court or round conflict")
                if row.get("roundCode") not in ROUNDS:
                    raise ValueError("unknown round")
                teams = [row.get(k) for k in ("team1", "team2")]
                if any(type(t) is not list or len(t) != 1 or type(t[0]) is not dict or t[0].get("idB") for t in teams):
                    raise ValueError("not two singles participants")
                players = [t[0] for t in teams]
                player_ids = [t.get("idA") for t in players]
                names = [f"{t.get('firstNameA') or ''} {t.get('lastNameA') or ''}".strip() for t in players]
                if (any(type(i) is not str or not re.fullmatch(r"wta[0-9]+", i) for i in player_ids)
                        or any(type(t.get(k)) is not str or not t[k].strip()
                               for t in players for k in ("firstNameA", "lastNameA"))
                        or len(set(player_ids)) != 2 or not all(is_real_participant(n) for n in names)):
                    raise ValueError("invalid or unresolved player identity")
            except ValueError as exc:
                exclusions.append({"path": path, "sourceMatchId": mid, "reason": str(exc)})
                complete = False
                continue
            timing_issues, scheduled, kind = [], None, "sequence-only"
            try:
                if any(row.get(k) not in (None, "") for k in ("conjunction", "comment")):
                    raise ValueError("timing qualifier requires source review")
                if row.get("notBefore") is not None:
                    scheduled, kind = _clock(date, row["notBefore"]), "explicit-not-before"
                    if scheduled < start:
                        raise ValueError("not-before precedes session clock")
                elif order == 1:
                    scheduled, kind = start, "first-match-session-start"
            except ValueError as exc:
                scheduled, kind = None, "unresolved-time"
                timing_issues.append(str(exc))
            observations.append({
                "sourceMatchKey": f"usopen:{year}:{mid}", "edition": year, "day": day,
                "sourceMatchId": mid, "sourceEventCode": code, "playerIDs": player_ids, "players": names,
                "roundCode": row["roundCode"], "courtId": cid, "session": session, "order": order,
                "localDate": date.isoformat(), "venueTimezone": ZONE.key,
                "publishedTimeKind": kind, "publishedTimeUTC": scheduled.astimezone(UTC).isoformat() if scheduled else None,
                "notBeforeText": row.get("notBefore"), "sessionStartText": court["time"],
                "conjunction": row.get("conjunction"), "comment": row.get("comment"),
                "statusText": row.get("status"), "statusCode": row.get("statusCode"),
                "timingIssues": timing_issues, "observedAtUTC": receipt["receivedAt"],
                "sourceURL": receipt["url"], "rawSHA256": receipt["rawSHA256"], "receiptSHA256": receipt["sha256"],
                "sourcePath": path, "qualification": "schedule-observation-only", "actualStartVerified": False})
    pairs = Counter((r["roundCode"], tuple(sorted(r["playerIDs"]))) for r in observations)
    if any(count > 1 for count in pairs.values()):
        raise ValueError("ambiguous duplicate participant pair/round")
    if type(listing.get("matchCount")) is not int or listing["matchCount"] != sum(census.values()):
        complete = False
        anomalies.append("catalogue-daily-count-disagreement")
    return {"outcome": "observed", "edition": year, "day": day, "localDate": date.isoformat(),
            "observedAtUTC": receipt["receivedAt"], "observations": observations, "exclusions": exclusions,
            "coverage": {"allRows": sum(census.values()), "eventCodeCounts": dict(census),
                         "WTAObservations": len(observations), "completeForAbsenceComparison": complete},
            "freshnessAtAcquisition": fresh, "anomalies": anomalies,
            "publicationHints": {"releaseTime": payload.get("releaseTime"), "epoch": payload.get("epoch"),
                                 "catalogueEpoch": listing.get("epoch"), "lastWrite": listing.get("lastWrite")},
            "firstPublicationTimeEstablished": False, "actualStartVerified": False}


def _derive(catalogue, daily, year, day):
    cr, cp = catalogue
    gap = {"outcome": "gap", "edition": year, "day": day, "observedAtUTC": cr["receivedAt"],
           "observations": [], "actualStartVerified": False}
    try:
        _listing(cp, year, day)
        if daily is None:
            raise ValueError("missing daily acquisition")
        dr, dp = daily
        gap["observedAtUTC"] = dr["receivedAt"]
        if (cr["url"] != endpoint(year) or dr["url"] != endpoint(year, day)
                or _time(dr["requestedAt"]) < _time(cr["receivedAt"])):
            raise ValueError("capture source or acquisition order conflict")
        return normalize(cp, dp, year=year, day=day, receipt=dr, catalogue_receipt=cr)
    except (ValueError, TypeError, KeyError, OverflowError, OSError) as exc:
        return {**gap, "issues": [f"{type(exc).__name__}: {exc}"]}


def _finish(root, trusted_root, catalogue, daily, year, day):
    report = _derive(catalogue, daily, year, day)
    body = {"edition": year, "day": day, "catalogueReceipt": catalogue[0]["sha256"],
            "dailyReceipt": daily[0]["sha256"] if daily else None, "report": report}
    _save(root / "collection.json", body, trusted_root)
    return read_collection(root, trusted_root=trusted_root)


def collect(root, *, trusted_root, year, day):
    endpoint(year, day)
    root = _mkdir(root, trusted_root)
    catalogue = fetch_once(root / "catalogue", trusted_root=trusted_root, year=year)
    try:
        _listing(catalogue[1], year, day)
    except ValueError:
        daily = None
    else:
        daily = fetch_once(root / "daily", trusted_root=trusted_root, year=year, day=day)
    return _finish(root, trusted_root, catalogue, daily, year, day)


def import_retained(root, *, trusted_root, day):
    if day not in (16, 17) or type(day) is not int:
        raise ValueError("only the retained 2026 days 16 and 17 may be imported")
    root = _mkdir(root, trusted_root)
    catalogue = _import_capture(root / "catalogue", trusted_root, "uso-schedule-days", None)
    daily = _import_capture(root / "daily", trusted_root, f"uso-schedule-{day}", day)
    return _finish(root, trusted_root, catalogue, daily, 2026, day)


def read_collection(root, *, trusted_root):
    root = Path(root)
    saved = _load(root / "collection.json", trusted_root)
    catalogue = read_capture(root / "catalogue", trusted_root=trusted_root)
    daily = read_capture(root / "daily", trusted_root=trusted_root) if saved["dailyReceipt"] else None
    if (catalogue[0]["sha256"] != saved["catalogueReceipt"]
            or (daily and daily[0]["sha256"] != saved["dailyReceipt"])
            or saved["report"] != _derive(catalogue, daily, saved["edition"], saved["day"])):
        raise ValueError("collection replay integrity failure")
    return saved


def history(roots, *, trusted_root):
    if not roots or len(roots) > 256:
        raise ValueError("provide 1 to 256 explicit collection directories")
    archives = [(str(Path(root).absolute()), read_collection(root, trusted_root=trusted_root)) for root in roots]
    if len({path for path, _ in archives}) != len(archives):
        raise ValueError("duplicate collection input")
    archives.sort(key=lambda item: (_time(item[1]["report"]["observedAtUTC"]), item[0]))
    versions, revisions, gaps = defaultdict(list), [], []
    previous_days, ever_seen, conflicts = {}, defaultdict(set), set()
    times = Counter((s["edition"], s["report"]["observedAtUTC"]) for _, s in archives)
    for path, saved in archives:
        report, digest = saved["report"], saved["sha256"]
        daykey = (report["edition"], report["day"])
        stamp = report["observedAtUTC"]
        def record(key, kind, *, stamp=stamp, digest=digest, **detail):
            revisions.append({"sourceMatchKey": key, "kind": kind, "observedAtUTC": stamp,
                              "collectionSHA256": digest, **detail})
        if report["outcome"] != "observed":
            gaps.append({"collection": path, "issues": report["issues"]})
            continue
        rows = {r["sourceMatchKey"]: r for r in report["observations"]}
        complete = report["coverage"]["completeForAbsenceComparison"]
        if times[(report["edition"], stamp)] > 1:
            complete = False
            gaps.append({"collection": path, "issues": ["ambiguous-acquisition-order"]})
        if complete:
            old = previous_days.get(daykey)
            if old is not None:
                for key in sorted(old - rows.keys()):
                    record(key, "absent-from-complete-order")
                for key in sorted((rows.keys() - old) & ever_seen[daykey]):
                    record(key, "reappeared-in-complete-order")
            previous_days[daykey] = set(rows)
            ever_seen[daykey].update(rows)
        else:
            gaps.append({"collection": path, "issues": ["absence-comparison-unavailable"],
                         "coverage": report["coverage"], "anomalies": report["anomalies"]})
        for key, row in rows.items():
            prior = versions[key]
            if prior:
                old = prior[-1]
                if set(row["playerIDs"]) != set(old["playerIDs"]) or row["roundCode"] != old["roundCode"]:
                    conflicts.add(key)
                    record(key, "identity-conflict", previousReceipt=old["receiptSHA256"])
                fields = [f for f in ("publishedTimeUTC", "publishedTimeKind", "localDate", "courtId", "session",
                                      "order", "statusText", "statusCode", "notBeforeText", "conjunction", "comment")
                          if row[f] != old[f]]
                if fields:
                    record(key, "fields-changed", fields=fields, previousReceipt=old["receiptSHA256"])
                if row["publishedTimeUTC"] and any(v["publishedTimeUTC"] and
                        _time(row["publishedTimeUTC"]) < _time(v["publishedTimeUTC"]) for v in prior):
                    record(key, "earlier-published-time")
            text = " ".join(str(row.get(f) or "") for f in ("statusText", "comment", "conjunction"))
            if re.search(r"\bcancel(?:l)?ed\b", text, re.I):
                record(key, "cancellation-text-observed")
            prior.append({**row, "collectionSHA256": digest})
    return {"schema": SCHEMA, "purpose": "schedule history only; no actual-start or forecast export",
            "inputs": [{"path": path, "sha256": saved["sha256"]} for path, saved in archives],
            "coverageClaim": "explicitly supplied collections only", "versions": dict(versions),
            "revisions": revisions, "gaps": gaps, "identityConflicts": sorted(conflicts),
            "actualStartVerified": False, "readyForLiveEvaluation": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("collect")
    fetch.add_argument("root", type=Path)
    fetch.add_argument("--year", required=True, type=int)
    fetch.add_argument("--day", required=True, type=int)
    retained = sub.add_parser("import-retained")
    retained.add_argument("root", type=Path)
    retained.add_argument("--day", required=True, type=int, choices=(16, 17))
    audit = sub.add_parser("history")
    audit.add_argument("roots", type=Path, nargs="+")
    audit.add_argument("--output", required=True, type=Path)
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "history":
        output = args.pop("output")
        result = history(**args)
        if a._absolute_without_symlink_resolution(output).is_relative_to(a._absolute_without_symlink_resolution(OUTPUT_DIR)):
            raise ValueError("history cannot enter production output")
        _save(output, result, args["trusted_root"])
        print(json.dumps({"output": str(output), "matches": len(result["versions"]),
                          "revisions": len(result["revisions"]), "gaps": len(result["gaps"])}))
    else:
        result = (collect if command == "collect" else import_retained)(**args)
        print(json.dumps(result["report"], indent=2, allow_nan=False))
        if result["report"]["outcome"] != "observed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
