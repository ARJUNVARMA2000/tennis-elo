"""Immutable WTA order-page observations. No forecasts or actual-start evidence."""
import argparse
import hashlib
import http.client
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import prospective_sources as p
import usopen_schedule as u
from tennis_model.eval.prospective import _bytes, _digest, _time

SCHEMA = "wta-order-observation-v1"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
ROUNDS = {**{f"Round of {n}": f"R{n}" for n in (128, 64, 32, 16)},
          "Quarterfinals": "QF", "Semifinals": "SF", "Final": "F"}


def page_identity(url):
    parts = urlsplit(url)
    match = re.fullmatch(r"/tournaments/([1-9][0-9]{0,7})/([a-z0-9-]+)/([0-9]{4})/order-of-play", parts.path)
    if (parts.scheme != "https" or parts.netloc != "www.wtatennis.com" or parts.query or parts.fragment or not match):
        raise ValueError("explicit official WTA order URL required")
    event, year = match[1], int(match[3])
    p.endpoint("wta", event=event, year=year)
    return event, year


def _save(path, value, trusted_root):
    body = {k: v for k, v in value.items() if k != "sha256"}
    body["schema"] = SCHEMA
    p._write(path, _bytes({**body, "sha256": _digest(body)}), trusted_root)


def _load(path, trusted_root):
    body = p._json(p._read(path, trusted_root))
    if (body.get("schema") != SCHEMA or body.get("sha256") != _digest({k: v for k, v in body.items() if k != "sha256"})):
        raise ValueError("WTA order document integrity failure")
    return body


def read_inspection(root, *, trusted_root, media):
    """Read private bounded inspection receipts or this adapter's page receipts."""
    root = Path(root)
    receipt = p._json(p._read(root / "receipt.json", trusted_root))
    attempt = p._json(p._read(root / "attempt.json", trusted_root))
    if receipt.get("schema") == SCHEMA:
        receipt, attempt = _load(root / "receipt.json", trusted_root), _load(root / "attempt.json", trusted_root)
    elif receipt.get("schema") != "wta-coverage-inspection-v1":
        raise ValueError("unrecognized inspection schema")
    if any(receipt.get(k) != v for k, v in attempt.items() if k != "sha256"):
        raise ValueError("inspection request/receipt mismatch")
    raw = p._read(root / "response.bin", trusted_root)
    if (len(raw) != receipt.get("rawBytes") or hashlib.sha256(raw).hexdigest() != receipt.get("rawSHA256")
            or _time(receipt["receivedAt"]) < _time(receipt["requestedAt"])):
        raise ValueError("inspection byte/clock integrity failure")
    failed = receipt.get("outcome") == "failed" or bool(receipt.get("error"))
    receipt = {**receipt, "outcome": "failed" if failed else "ok", "sha256": _digest(receipt)}
    if failed:
        return receipt, None
    if (receipt.get("status") != 200 or receipt.get("responseUrl") != receipt.get("url")
            or receipt.get("rawComplete") is not True or len(raw) > p.MAX_BODY
            or receipt.get("headers", {}).get("content-type", "").split(";", 1)[0] != media
            or receipt.get("headers", {}).get("content-encoding", "identity") != "identity"):
        raise ValueError("inspection transport/media failure")
    length = receipt["headers"].get("content-length")
    if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) != len(raw)):
        raise ValueError("incomplete inspection body")
    return receipt, raw


def fetch_page(root, *, trusted_root, url):
    page_identity(url)
    root = u._mkdir(root, trusted_root)
    attempt = {"url": url, "requestedAt": p._now().isoformat(),
               "adapterSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    _save(root / "attempt.json", attempt, trusted_root)
    receipt, raw, tick = {**attempt, "outcome": "failed", "rawComplete": False}, b"", time.monotonic()
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DEUCE schedule research)",
                                         "Accept": "text/html", "Accept-Encoding": "identity", "Cache-Control": "no-cache"})
        try:
            response = urllib.request.build_opener(p._NoRedirect()).open(request, timeout=25)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            receipt.update(status=response.status, responseUrl=response.geturl(),
                           headers={k.lower(): v for k, v in response.headers.items() if k.lower() in p.HTTP_HEADERS})
            raw = response.read(p.MAX_BODY + 1)
        receipt["rawComplete"] = len(raw) <= p.MAX_BODY
        if (receipt["status"] != 200 or receipt["responseUrl"] != url or not receipt["rawComplete"]
                or receipt["headers"].get("content-type", "").split(";", 1)[0] != "text/html"
                or receipt["headers"].get("content-encoding", "identity") != "identity"):
            raise ValueError("invalid HTML response")
        length = receipt["headers"].get("content-length")
        if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) != len(raw)):
            raise ValueError("partial HTML body")
        raw.decode("utf-8")
        receipt["outcome"] = "ok"
    except (OSError, ValueError, http.client.HTTPException) as exc:
        if isinstance(exc, http.client.IncompleteRead):
            raw = exc.partial[:p.MAX_BODY + 1]
        receipt["failure"] = f"{type(exc).__name__}: {exc}"[:1000]
    receipt.update(receivedAt=p._now().isoformat(), elapsedSeconds=time.monotonic() - tick,
                   rawBytes=len(raw), rawSHA256=hashlib.sha256(raw).hexdigest())
    p._write(root / "response.bin", raw, trusted_root)
    _save(root / "receipt.json", receipt, trusted_root)
    return read_inspection(root, trusted_root=trusted_root, media="text/html")


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children, self.text = tag, dict(attrs), [], ""

    def find(self, cls):
        found = [self] if cls in self.attrs.get("class", "").split() else []
        for child in self.children:
            found.extend(child.find(cls))
        return found

    def content(self):
        return self.text + " " + " ".join(child.content() for child in self.children)


class Tree(HTMLParser):
    """Inert page tree; only known order court comments are expanded as templates."""
    def __init__(self, *, comments=True):
        super().__init__()
        self.root, self.comments = Node(), comments
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, 0, -1):
            if self.stack[k].tag == tag:
                del self.stack[k:]
                break

    def handle_data(self, text):
        self.stack[-1].text += text

    def handle_comment(self, text):
        if self.comments and "tournament-oop__court" in text:
            fragment = Tree(comments=False)
            fragment.feed(text)
            self.stack[-1].children.extend(fragment.root.children)


def parse_page(raw, event, year):
    tree = Tree()
    tree.feed(raw.decode("utf-8"))
    widgets = [n for n in tree.root.find("tournament-oop") if n.attrs.get("data-widget") == "tournament-oop/order-of-play"]
    if len(widgets) != 1:
        raise ValueError("missing or duplicate WTA order widget")
    widget = widgets[0]
    a = widget.attrs
    if a.get("data-tournament-id") != str(event) or a.get("data-year") != str(year):
        raise ValueError("order widget edition conflict")
    start, end = date.fromisoformat(a["data-startdate"]), date.fromisoformat(a["data-enddate"])
    if start.year != year or not 0 <= (end - start).days <= 21:
        raise ValueError("invalid widget event dates")
    days, occurrences, seen = widget.find("js-oop-day"), [], set()
    dates = [n.attrs.get("data-date") for n in days]
    if len(set(dates)) != len(dates) or len(days) > 30:
        raise ValueError("duplicate or excessive order days")
    for day in days:
        d = day.attrs["data-date"]
        if not start - timedelta(days=7) <= date.fromisoformat(d) <= end + timedelta(days=1):
            raise ValueError("order day outside edition interval")
        for ci, court in enumerate(day.find("tournament-oop__court")):
            names, clocks = court.find("court-header__name"), court.find("js-start-time")
            if len(names) != 1:
                raise ValueError("ambiguous court name")
            header_clocks = [n.attrs for n in clocks if "js-start-time--match" not in n.attrs.get("class", "").split()]
            if len(header_clocks) > 1:
                raise ValueError("ambiguous court clocks")
            for order, card in enumerate(court.find("js-tennis-match-wta"), 1):
                mid = card.attrs.get("data-match-id")
                classes = card.attrs.get("class", "").split()
                ids = [re.fullmatch(r"js-match-([0-9]+)-([0-9]{4})-([A-Za-z0-9_-]+)", c) for c in classes]
                ids = [m for m in ids if m]
                if (type(mid) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+", mid) or len(ids) != 1
                        or int(ids[0][1]) != int(event) or int(ids[0][2]) != year or ids[0][3] != mid):
                    raise ValueError("card MatchID or edition conflict")
                if (d, mid) in seen:
                    raise ValueError("duplicate same-day match occurrence")
                seen.add((d, mid))
                teams = []
                for cls in ("js-team-a-players", "js-team-b-players"):
                    groups = card.find(cls)
                    links = groups[0].find("match-table__player--link") if len(groups) == 1 else []
                    teams.append([n.attrs.get("href", "") for n in links])
                rounds = card.find("js-match-round")
                occurrences.append({"pageDate": d, "sourceMatchId": mid,
                                    "court": " ".join(names[0].content().split()), "courtGroup": ci, "order": order,
                                    "pageStatus": card.attrs.get("data-status"), "playerLinks": teams,
                                    "pageRound": " ".join(rounds[0].content().split()) if len(rounds) == 1 else None,
                                    "courtClock": header_clocks[0] if header_clocks else None,
                                    "dedicatedClockUnqualified": bool(card.find("js-start-time"))})
    return {"event": str(event), "year": year, "start": start.isoformat(), "end": end.isoformat(),
            "utcOffsetText": a.get("data-utcoffset"), "days": dates, "occurrences": occurrences,
            "unpublishedMarker": "Order of Play Not Available Yet" in widget.content()}


def normalize(page, api, *, page_receipt, api_receipt):
    event, year = page_identity(page_receipt["url"])
    parsed = parse_page(page, event, year)
    tournament, rows, api_exclusions, _ = p._wta(api)
    if (str(tournament["tournamentGroup"]["id"]) != event or tournament["year"] != year
            or tournament["startDate"] != parsed["start"] or tournament["endDate"] != parsed["end"]):
        raise ValueError("page/API event edition or dates disagree")
    stamp = max(_time(page_receipt["receivedAt"]), _time(api_receipt["receivedAt"]))
    fresh = {"page": p.freshness(page_receipt, now=stamp), "api": p.freshness(api_receipt, now=stamp)}
    result = {"outcome": "observed", "event": event, "year": year, "observedAt": stamp.isoformat(),
              "observations": [], "exclusions": [], "freshnessAtAcquisition": fresh,
              "apiExclusions": api_exclusions, "completeForAbsenceComparison": False,
              "actualStartVerified": False, "firstPublicationEstablished": False,
              "pageRows": len(parsed["occurrences"]), "pageDays": parsed["days"]}
    if not parsed["days"]:
        if parsed["unpublishedMarker"] and not api.get("matches"):
            return {**result, "outcome": "unpublished"}
        raise ValueError("missing order days; not an authoritative empty order")
    if parsed["unpublishedMarker"]:
        raise ValueError("order data conflicts with unpublished marker")
    index = {r["sourceMatchId"]: r for r in rows}
    seen, incomplete = set(), False
    for occurrence in parsed["occurrences"]:
        mid, row = occurrence["sourceMatchId"], index.get(occurrence["sourceMatchId"])
        if row is None:
            result["exclusions"].append({"sourceMatchId": mid, "pageDate": occurrence["pageDate"],
                                         "reason": "outside-admitted-API-main-singles"})
            continue
        seen.add(mid)
        teams = occurrence["playerLinks"]
        player_ids = []
        for links in teams:
            match = re.fullmatch(r"/players/([1-9][0-9]*)/[a-z0-9-]+", links[0]) if len(links) == 1 else None
            player_ids.append(match[1] if match else None)
        expected_ids = [str(row["raw"]["PlayerID" + s]) for s in ("A", "B")]
        if player_ids != expected_ids:
            incomplete = True
            result["exclusions"].append({"sourceMatchId": mid, "pageDate": occurrence["pageDate"],
                                         "reason": "page/API-player-identity-disagreement",
                                         "pagePlayerIDs": player_ids, "apiPlayerIDs": expected_ids})
            continue
        if ROUNDS.get(occurrence["pageRound"]) != row["round"]:
            incomplete = True
            result["exclusions"].append({"sourceMatchId": mid, "pageDate": occurrence["pageDate"],
                                         "reason": "page/API-round-disagreement",
                                         "pageRound": occurrence["pageRound"], "apiRound": row["round"]})
            continue
        kind, published, issues = "sequence-only", None, []
        status_agrees = occurrence["pageStatus"] == row["raw"].get("MatchState")
        if not status_agrees:
            incomplete = True
            issues.append("page/API-status-disagreement")
        if row["status"] != "scheduled":
            kind = "historical-or-nonscheduled"
        elif occurrence["dedicatedClockUnqualified"]:
            kind = "unresolved-time"
            issues.append("dedicated-match-clock-semantics-unqualified")
        elif occurrence["order"] == 1:
            clock = occurrence["courtClock"]
            try:
                if not status_agrees or not clock or clock.get("data-date") != occurrence["pageDate"]:
                    raise ValueError("missing or inconsistent court clock")
                offset = clock.get("data-utc-offset")
                if type(offset) is not str or not re.fullmatch(r"[+-](?:0[0-9]|1[0-4])[0-5][0-9]", offset) or offset != parsed["utcOffsetText"]:
                    raise ValueError("missing or conflicting explicit UTC offset")
                local = datetime.strptime(clock["data-start-time"], "%I:%M %p").strftime("%H:%M")
                published = _time(occurrence["pageDate"] + "T" + local + offset)
                if published != _time(row["raw"]["MatchTimeStamp"]):
                    raise ValueError("published court/API schedule conflict")
                published, kind = published.isoformat(), "first-match-court-start"
            except (KeyError, ValueError, TypeError) as exc:
                published, kind = None, "unresolved-time"
                issues.append(str(exc))
        result["observations"].append({
            **occurrence, "sourceMatchKey": f"wta:{event}:{year}:{mid}", "event": event, "year": year,
            "players": row["names"], "playerIDs": player_ids, "round": row["round"], "status": row["status"],
            "publishedTimeKind": kind, "publishedTimeUTC": published, "timingIssues": issues,
            "apiScheduleField": row["raw"].get("MatchTimeStamp"), "apiNotBeforeField": row["raw"].get("NotBeforeISOTime"),
            "sourceURL": page_receipt["url"], "observedAt": stamp.isoformat(),
            "pageObservedAt": page_receipt["receivedAt"], "apiObservedAt": api_receipt["receivedAt"],
            "sourceDigests": {"page": page_receipt["rawSHA256"], "api": api_receipt["rawSHA256"]},
            "qualification": "schedule-observation-only", "actualStartVerified": False})
    missing = sorted(set(index) - seen)
    result["missingAPIMainMatchIDsFromPage"] = missing
    # Population exclusions can include unresolved main-draw participants. Such a
    # source pair cannot establish exhaustive identity coverage for disappearance.
    unresolved_api = any(reason != "outside-main-singles" for reason in api_exclusions)
    result["completeForAbsenceComparison"] = bool(not missing and not incomplete and not unresolved_api
                                                   and all(v["ready"] for v in fresh.values()))
    return result


def _derive(page_capture, api_capture):
    pr, raw = page_capture
    event, year = page_identity(pr["url"])
    ar, api = api_capture if api_capture else (None, None)
    stamp = max(_time(pr["receivedAt"]), _time(ar["receivedAt"]) if ar else _time(pr["receivedAt"]))
    try:
        if raw is None or api is None:
            raise ValueError("failed or missing source acquisition")
        if ar["url"] != p.endpoint("wta", event=event, year=year):
            raise ValueError("wrong API source")
        return normalize(raw, api, page_receipt=pr, api_receipt=ar)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {"outcome": "gap", "event": event, "year": year, "observedAt": stamp.isoformat(),
                "observations": [], "issues": [str(exc)], "completeForAbsenceComparison": False,
                "actualStartVerified": False}


def ingest(root, page_root, api_root, *, trusted_root, provenance="retrospective-intake"):
    root = u._mkdir(root, trusted_root)
    return _finish(root, page_root, api_root, trusted_root, provenance)


def _finish(root, page_root, api_root, trusted_root, provenance):
    page = read_inspection(page_root, trusted_root=trusted_root, media="text/html")
    api = p.read_capture(api_root, trusted_root=trusted_root, require_ok=False) if api_root else None
    body = {"pageRoot": str(Path(page_root).absolute()), "apiRoot": str(Path(api_root).absolute()) if api_root else None,
            "pageReceipt": page[0]["sha256"], "apiReceipt": api[0]["sha256"] if api else None,
            "provenance": provenance, "report": _derive(page, api)}
    _save(root / "collection.json", body, trusted_root)
    return read_collection(root, trusted_root=trusted_root)


def read_collection(root, *, trusted_root):
    saved = _load(Path(root) / "collection.json", trusted_root)
    page = read_inspection(saved["pageRoot"], trusted_root=trusted_root, media="text/html")
    api = p.read_capture(saved["apiRoot"], trusted_root=trusted_root, require_ok=False) if saved["apiRoot"] else None
    if (page[0]["sha256"] != saved["pageReceipt"] or (api and api[0]["sha256"] != saved["apiReceipt"])
            or saved["report"] != _derive(page, api)):
        raise ValueError("WTA collection replay integrity failure")
    return saved


def collect(root, *, trusted_root, url):
    event, year = page_identity(url)
    root = u._mkdir(root, trusted_root)
    page = fetch_page(root / "page", trusted_root=trusted_root, url=url)
    try:
        if page[1] is None:
            raise ValueError("failed HTML")
        parse_page(page[1], event, year)
    except (ValueError, KeyError, TypeError):
        api_root = None
    else:
        api_root = root / "api"
        p.fetch_once(api_root, trusted_root=trusted_root, source="wta", event=event, year=year)
    return _finish(root, root / "page", api_root, trusted_root, "manual-network-collection")


def history(roots, *, trusted_root):
    if not roots or len(roots) > 128 or len({str(Path(r).absolute()) for r in roots}) != len(roots):
        raise ValueError("provide 1 to 128 distinct collection directories")
    archives = [(str(Path(r).absolute()), read_collection(r, trusted_root=trusted_root)) for r in roots]
    archives.sort(key=lambda pair: (_time(pair[1]["report"]["observedAt"]), pair[0]))
    versions, changes, gaps, conflicts, previous = defaultdict(list), [], [], set(), {}
    seen_times = Counter((a["report"]["event"], a["report"]["year"], a["report"]["observedAt"]) for _, a in archives)
    for path, saved in archives:
        report = saved["report"]
        key = (report["event"], report["year"])
        complete = report["completeForAbsenceComparison"] and seen_times[(*key, report["observedAt"])] == 1
        present = {(r["sourceMatchKey"], r["pageDate"]) for r in report["observations"]}
        if not complete:
            gaps.append({"collection": path, "outcome": report["outcome"], "issues": report.get("issues", ["absence-comparison-unavailable"])})
        else:
            if key in previous:
                changes.extend({"kind": "absent-from-complete-source-pair", "occurrence": list(x), "collection": path}
                               for x in sorted(previous[key] - present))
                changes.extend({"kind": "added-or-reappeared", "occurrence": list(x), "collection": path}
                               for x in sorted(present - previous[key]))
            previous[key] = present
        for excluded in report.get("exclusions", []):
            if excluded["reason"] in {"page/API-player-identity-disagreement", "page/API-round-disagreement"}:
                conflicts.add(f"wta:{key[0]}:{key[1]}:{excluded['sourceMatchId']}")
        current = defaultdict(list)
        for row in report["observations"]:
            current[row["sourceMatchKey"]].append(row)
        for mid, rows in current.items():
            prior = versions[mid]
            # One capture can retain the same match on several days. Compare
            # whole snapshots, not adjacent occurrences within that capture.
            identities = {(r["round"], tuple(sorted(zip(r["players"], r["playerIDs"])))) for r in prior + rows}
            if len(identities) > 1:
                conflicts.add(mid)
            if prior:
                old = [r for r in prior if r["collectionSHA256"] == prior[-1]["collectionSHA256"]]
                fields = [k for k in ("pageDate", "court", "courtGroup", "order", "publishedTimeUTC", "publishedTimeKind", "status")
                          if Counter(r[k] for r in rows) != Counter(r[k] for r in old)]
                signature = lambda r: tuple(r[k] for k in ("pageDate", "court", "courtGroup", "order", "publishedTimeUTC", "publishedTimeKind", "status"))
                if not fields and Counter(map(signature, rows)) != Counter(map(signature, old)):
                    fields = ["occurrence-association"]
                if fields:
                    changes.append({"sourceMatchKey": mid, "kind": "fields-changed", "fields": fields, "collection": path})
                old_times = {_time(r["publishedTimeUTC"]) for r in prior if r["publishedTimeUTC"]}
                new_times = {_time(r["publishedTimeUTC"]) for r in rows if r["publishedTimeUTC"]} - old_times
                if old_times and new_times and min(new_times) < max(old_times):
                    changes.append({"sourceMatchKey": mid, "kind": "earlier-published-time", "collection": path})
            prior.extend({**row, "collectionSHA256": saved["sha256"]} for row in rows)
    return {"schema": SCHEMA, "inputs": [{"path": path, "sha256": saved["sha256"]} for path, saved in archives],
            "coverageClaim": "explicitly supplied source pairs only", "versions": dict(versions),
            "changes": changes, "gaps": gaps, "identityConflicts": sorted(conflicts), "readyForLiveEvaluation": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("collect")
    fetch.add_argument("root", type=Path)
    fetch.add_argument("--url", required=True)
    intake = commands.add_parser("ingest")
    for name in ("root", "page_root", "api_root"):
        intake.add_argument(name, type=Path)
    past = commands.add_parser("history")
    past.add_argument("roots", type=Path, nargs="+")
    past.add_argument("--output", type=Path, required=True)
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "history":
        output = args.pop("output")
        if p.a._absolute_without_symlink_resolution(output).is_relative_to(p.a._absolute_without_symlink_resolution(u.OUTPUT_DIR)):
            raise ValueError("history cannot enter production output")
        result = history(**args)
        _save(output, result, args["trusted_root"])
        print(json.dumps({"matches": len(result["versions"]), "changes": len(result["changes"]), "gaps": len(result["gaps"])}))
    else:
        result = (collect if command == "collect" else ingest)(**args)["report"]
        print(json.dumps({k: result[k] for k in ("outcome", "observedAt", "completeForAbsenceComparison")} |
                         {"observations": len(result["observations"]), "issues": result.get("issues", [])}))
        if result["outcome"] == "gap":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
