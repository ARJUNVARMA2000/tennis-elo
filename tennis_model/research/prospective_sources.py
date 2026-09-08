"""First-party source audit outside the frozen model package. No forecast collector.

Draft batch conversion is diagnostic. Live export fails closed until independently
validated timing semantics and a real source lifecycle exist. See the source handoff.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

from tennis_model.config import ROUND_ORDER, TIER_NAMES
from tennis_model.data.bracket_rounds import player_identity_key
from tennis_model.data.live import _athlete_name, _score
from tennis_model.data.participants import is_real_participant
from tennis_model.data.results import tier_mults
from tennis_model.data.wta_results import canonical_name, completed_score, games, same_edition
from tennis_model.data.wta_stats import _normalized_level, _winner_first_score
from tennis_model.eval.prospective import _bytes, _digest, _time, match_key
from tennis_model.model import artifact as a

SCHEMA = "prospective-source-audit-v1"
MAX_BODY = 8 * 1024 * 1024
HTTP_HEADERS = frozenset({"date", "age", "cache-control", "content-type", "content-length",
                          "content-encoding", "etag", "last-modified", "retry-after"})
ESPN_STATUS = {"STATUS_SCHEDULED": ("pre", False, "scheduled"),
               "STATUS_IN_PROGRESS": ("in", False, "live"),
               "STATUS_FINAL": ("post", True, "completed"),
               "STATUS_RETIRED": ("post", True, "retired"),
               "STATUS_WALKOVER": ("post", True, "walkover"),
               "STATUS_CANCELED": ("post", True, "cancelled")}


def _now():
    return datetime.now(UTC)


def _json(raw):
    return json.loads(raw, object_pairs_hook=a._reject_duplicate_keys,
                      parse_constant=a._reject_json_constant)


def _read(path, root, limit=MAX_BODY + 1):
    return a._read_bounded(path, limit, trusted_root=root,
                          io_reason=a.PredictorArtifactReason.PAYLOAD_IO,
                          too_large_reason=a.PredictorArtifactReason.PAYLOAD_TOO_LARGE)


def _write(path, raw, root):
    """Atomic create-only publication inside a descriptor-validated parent."""
    with a._open_artifact_parent(path, trusted_root=root) as (directory, name):
        a._validate_write_destination(directory, name)
        temp = ".source-" + uuid.uuid4().hex
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temp, name, src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
            os.fsync(directory)
        finally:
            os.unlink(temp, dir_fd=directory)


def write_json(path, value, *, trusted_root):
    body = {"schema": SCHEMA, **value}
    _write(Path(path), _bytes({**body, "sha256": _digest(body)}), trusted_root)


def endpoint(source, *, event=None, year=None):
    if source == "espn" and event is None and year is None:
        return "https://site.web.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard?limit=300"
    if (source == "wta" and re.fullmatch(r"[1-9][0-9]{0,7}", str(event))
            and type(year) is int and 2000 <= year <= 2100):
        return f"https://api.wtatennis.com/tennis/tournaments/{event}/{year}/matches?page=0&pageSize=100"
    raise ValueError("explicit supported source/event/year required")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch_once(root, *, trusted_root, source, event=None, year=None):
    """One bounded attempt; preserve HTTP/transport/parse failures without fallback."""
    root = a._absolute_without_symlink_resolution(root)
    url = endpoint(source, event=event, year=year)
    with a._open_artifact_parent(root, trusted_root=trusted_root) as (directory, name):
        os.mkdir(name, mode=0o700, dir_fd=directory)
        os.fsync(directory)
    request_time, tick = _now(), time.monotonic()
    request = {"source": source, "event": event, "year": year, "url": url,
               "requestedAt": request_time.isoformat(), "adapterSHA256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "purpose": "source audit only; no forecasts"}
    write_json(root / "attempt.json", request, trusted_root=root)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; tennis_model personal analytics)",
               "Accept": "application/json", "Accept-Encoding": "identity", "Cache-Control": "no-cache"}
    if source == "wta":
        headers["account"] = "wta"
    record, raw, body_complete = dict(request), b"", False
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            response = opener.open(urllib.request.Request(url, headers=headers), timeout=25)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            record.update(status=response.status, responseUrl=response.geturl(),
                          headers={k.lower(): v for k, v in response.headers.items() if k.lower() in HTTP_HEADERS})
            raw = response.read(MAX_BODY + 1)
        body_complete = len(raw) <= MAX_BODY
        if len(raw) > MAX_BODY:
            raise ValueError("response too large; retained prefix is incomplete")
        if record["responseUrl"] != url or record["status"] != 200:
            raise ValueError("HTTP response not accepted")
        media = record["headers"].get("content-type", "").split(";")[0].strip().lower()
        if media != "application/json" or record["headers"].get("content-encoding", "identity").lower() != "identity":
            raise ValueError("unsupported response media or encoding")
        size = record["headers"].get("content-length")
        if size is not None and (not size.isdigit() or int(size) != len(raw)):
            raise ValueError("response length differs")
        if type(_json(raw)) is not dict:
            raise ValueError("object response required")
        record["outcome"] = "ok"
    except (OSError, ValueError, http.client.HTTPException) as exc:
        if isinstance(exc, http.client.IncompleteRead):
            raw = exc.partial[:MAX_BODY+1]
        record.update(outcome="failed", error=type(exc).__name__, detail=str(exc)[:300])
    received = _now()
    record.update(receivedAt=received.isoformat(), elapsedSeconds=time.monotonic()-tick,
                  rawBytes=len(raw), rawSHA256=hashlib.sha256(raw).hexdigest(),
                  rawComplete=body_complete)
    if received < request_time:
        record.update(outcome="failed", error="ClockRegression", detail="local clock moved backward")
    _write(root / "response.bin", raw, root)
    write_json(root / "receipt.json", record, trusted_root=root)
    return read_capture(root, trusted_root=trusted_root, require_ok=False)[0]


def _receipt(path, root):
    value = _json(_read(path, root, 65536))
    if (type(value) is not dict or value.get("schema") != SCHEMA
            or value.get("sha256") != _digest({k: v for k, v in value.items() if k != "sha256"})):
        raise ValueError("source receipt integrity failure")
    return value


def read_capture(root, *, trusted_root, require_ok=True):
    root = Path(root)
    receipt = _receipt(root / "receipt.json", trusted_root)
    request = _receipt(root / "attempt.json", trusted_root)
    if any(receipt.get(k) != v for k, v in request.items() if k != "sha256"):
        raise ValueError("source receipt lost its initial request")
    if receipt["url"] != endpoint(receipt["source"], event=receipt["event"], year=receipt["year"]):
        raise ValueError("unsupported source receipt URL")
    if _time(receipt["receivedAt"]) < _time(receipt["requestedAt"]):
        raise ValueError("source clock regression")
    raw = _read(root / "response.bin", trusted_root)
    if len(raw) != receipt["rawBytes"] or hashlib.sha256(raw).hexdigest() != receipt["rawSHA256"]:
        raise ValueError("source payload integrity failure")
    if receipt["outcome"] != "ok":
        if require_ok:
            raise ValueError("source attempt failed: " + receipt.get("detail", "unknown"))
        return receipt, None
    if not receipt["rawComplete"] or receipt["status"] != 200 or receipt["responseUrl"] != receipt["url"]:
        raise ValueError("incomplete or unsuccessful source response")
    payload = _json(raw)
    if receipt["source"] == "wta":
        tournament = payload.get("tournament", {})
        if (str(tournament.get("tournamentGroup", {}).get("id")) != str(receipt["event"])
                or tournament.get("year") != receipt["year"]):
            raise ValueError("response edition differs from requested endpoint")
    return receipt, payload


def freshness(receipt, *, now=None):
    """HTTP/cache freshness only. This is not match-timestamp semantic validation."""
    now = _now() if now is None else now
    received = _time(receipt["receivedAt"])
    issues = []
    if receipt["outcome"] != "ok":
        issues.append("failed-source")
    if not timedelta(0) <= now - received <= timedelta(minutes=10):
        issues.append("stale-or-future-observation")
    headers = receipt.get("headers", {})
    age = None
    try:
        date = parsedate_to_datetime(headers["date"])
        age_text = headers.get("age", "0")
        if date.tzinfo is None or not re.fullmatch(r"[0-9]+", age_text):
            raise ValueError("invalid cache time")
        age = max(0., (received-date).total_seconds(), int(age_text)) + max(0., (now-received).total_seconds())
        if age > 600 or date > received + timedelta(seconds=5):
            issues.append("stale-or-future-http-clock")
    except (KeyError, TypeError, ValueError, OverflowError):
        issues.append("missing-or-invalid-http-clock")
    return {"ready": not issues, "issues": issues, "httpAgeSeconds": age,
            "matchLevelFreshnessVerified": False}


def _pair(names):
    if len(names) != 2 or not all(is_real_participant(n) for n in names):
        raise ValueError("two real players required")
    keys = sorted(player_identity_key(n) for n in names)
    if not all(keys) or keys[0] == keys[1]:
        raise ValueError("distinct player identities required")
    return tuple(keys)


def _round(value, draw, *, provider):
    if type(draw) is not int or draw < 2 or draw > 128:
        raise ValueError("explicit singles draw size required")
    if provider == "wta":
        rid = str(value)
        fixed = {"Q": "QF", "S": "SF", "F": "F"}
    else:
        rid = str(value.get("id", ""))
        display = str(value.get("displayName", ""))
        if "qualif" in display.lower():
            raise ValueError("qualifying")
        fixed = {"5": "QF", "6": "SF", "7": "F"}
        labels = {"5": {"quarterfinal", "quarterfinals"}, "6": {"semifinal", "semifinals"}, "7": {"final"}}
        if rid in fixed and display.lower() not in labels[rid]:
            raise ValueError("ambiguous round label")
    if rid in fixed:
        return fixed[rid]
    if rid not in ("1", "2", "3", "4"):
        raise ValueError("unknown round")
    size = (1 << (draw-1).bit_length()) >> (int(rid)-1)
    result = {8: "QF", 4: "SF", 2: "F"}.get(size, f"R{size}")
    if result not in ROUND_ORDER or result in {"RR", "BR"}:
        raise ValueError("invalid round for draw")
    return result


def _unique(rows):
    ids, identities = Counter(r["sourceMatchId"] for r in rows), Counter((r["round"], r["pair"]) for r in rows)
    if any(n > 1 for n in ids.values()) or any(n > 1 for n in identities.values()):
        raise ValueError("duplicate or ambiguous provider match identity")


def _wta(payload):
    tournament = payload["tournament"]
    event = {"id": str(tournament["tournamentGroup"]["id"]), "year": tournament["year"]}
    classification = _normalized_level(tournament.get("level"))
    if classification is None or classification[1] != "main" or classification[0] not in TIER_NAMES:
        raise ValueError("not an admitted main-tour event")
    rows, excluded = [], Counter()
    if type(payload.get("matches")) is not list or len(payload["matches"]) > 2048:
        raise ValueError("bounded WTA match list required")
    for i, raw in enumerate(payload["matches"]):
        if raw.get("DrawMatchType") != "S" or raw.get("DrawLevelType") != "M":
            excluded["outside-main-singles"] += 1
            continue
        if not same_edition(event, raw):
            raise ValueError("WTA record/header edition conflict")
        names = [canonical_name(f'{raw.get("PlayerNameFirst"+s, "")} {raw.get("PlayerNameLast"+s, "")}') for s in ("A", "B")]
        try:
            pair = _pair(names)
            if any(not raw.get("PlayerNameFirst"+s) or not raw.get("PlayerNameLast"+s) for s in ("A", "B")):
                raise ValueError("missing player identity")
            if (any(not str(raw.get("PlayerID"+s) or "").isdigit() for s in ("A", "B"))
                    or str(raw["PlayerIDA"]) == str(raw["PlayerIDB"])):
                raise ValueError("invalid provider player identities")
            rnd = _round(raw.get("RoundID"), tournament["singlesDrawSize"], provider="wta")
        except ValueError as exc:
            excluded[str(exc)] += 1
            continue
        mid = raw.get("MatchID")
        if type(mid) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+", mid):
            raise ValueError("missing WTA match identity")
        state = {"U": "scheduled", "P": "live", "F": "terminal"}.get(raw.get("MatchState"), "unknown")
        winner, score = None, None
        if state == "terminal" and str(raw.get("Winner")) in {"2", "3"}:
            won_a = str(raw["Winner"]) == "2"
            winner = names[0 if won_a else 1]
            score = _winner_first_score(raw, won_a)
            state = "completed" if completed_score(score) else "unresolved-terminal"
        rows.append({"sourceMatchId": mid, "round": rnd, "pair": pair, "names": names,
                     "status": state, "winner": winner, "score": score, "raw": raw, "path": f"/matches/{i}"})
    _unique(rows)
    return tournament, rows, dict(excluded), classification[0]


def _espn(event, draw):
    rows, excluded = [], Counter()
    groups = event.get("groupings")
    if type(groups) is not list:
        raise ValueError("ESPN grouping list required")
    for gi, group in enumerate(groups):
        if group.get("grouping", {}).get("slug") != "womens-singles":
            excluded["outside-womens-singles"] += len(group.get("competitions", []))
            continue
        for ci, raw in enumerate(group["competitions"]):
            try:
                rnd = _round(raw.get("round", {}), draw, provider="espn")
                names = [_athlete_name(c) for c in raw.get("competitors", [])]
                pair = _pair(names)
                player_ids = [str(c.get("id") or "") for c in raw["competitors"]]
                if (any(not pid.isdigit() for pid in player_ids) or len(set(player_ids)) != 2
                        or raw.get("type", {}).get("slug") != "womens-singles"):
                    raise ValueError("invalid provider player identities or competition type")
            except ValueError as exc:
                excluded[str(exc)] += 1
                continue
            mid = raw.get("id")
            if type(mid) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+", mid):
                raise ValueError("missing ESPN match identity")
            st = raw.get("status", {}).get("type", {})
            known = ESPN_STATUS.get(st.get("name"))
            state = known[2] if known and st.get("state") == known[0] and st.get("completed") is known[1] else "unknown"
            winner, score = None, None
            if state == "completed":
                cs = raw["competitors"]
                wins = [i for i, c in enumerate(cs) if c.get("winner") is True]
                if len(wins) == 1 and cs[1-wins[0]].get("winner") is False:
                    wi = wins[0]
                    winner = names[wi]
                    score = _score(cs[wi].get("linescores"), cs[1-wi].get("linescores"))
                if not winner or not completed_score(score):
                    state = "unresolved-terminal"
            rows.append({"sourceMatchId": mid, "round": rnd, "pair": pair, "names": names,
                         "status": state, "winner": winner, "score": score, "raw": raw,
                         "path": f"/groupings/{gi}/competitions/{ci}"})
    _unique(rows)
    return rows, dict(excluded)


def _result_key(row):
    return (row["round"], row["pair"], player_identity_key(row["winner"]), games(row["score"]))


def _overlap(event, tournament):
    try:
        e0, e1 = _time(event["date"]).date(), _time(event["endDate"]).date()
        w0, w1 = (datetime.strptime(tournament[k], "%Y-%m-%d").date() for k in ("startDate", "endDate"))
        return (0 <= (w1-w0).days <= 21 and 0 <= (e1-e0).days <= 28
                and abs((w0-e0).days) <= 8 and abs((w1-e1).days) <= 1 and max(e0,w0) <= min(e1,w1))
    except (KeyError, ValueError, TypeError, AttributeError):
        return False


def _bound(wta, espn):
    raw, other = wta["raw"], espn["raw"]
    flags = [raw.get(k) for k in ("estimatedStartTime", "isEstimatedStartTime")]
    if not any(v is False for v in flags) or any(v is not None and (type(v) is not bool or v) for v in flags):
        raise ValueError("estimated-or-unknown-start")
    if other.get("timeValid") is not True:
        raise ValueError("ESPN-time-unconfirmed")
    not_before = raw.get("NotBeforeISOTime")
    if type(not_before) is not str or not re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})", not_before):
        raise ValueError("missing-zoned-not-before")
    try:
        stamp = _time(raw["MatchTimeStamp"])
        # Derive the date in the not-before field's OWN offset, including UTC rollover.
        original_zone = datetime.fromisoformat(("2000-01-01T"+not_before).replace("Z", "+00:00")).tzinfo
        date = stamp.astimezone(original_zone).date().isoformat()
        bound = _time(date + "T" + not_before)
        if not bound == stamp == _time(other["date"]) == _time(other["startDate"]):
            raise ValueError("conflicting-schedule-times")
        return bound.isoformat()
    except (KeyError, TypeError, AttributeError):
        raise ValueError("missing-schedule-times") from None


def audit(espn_payload, wta_payload):
    """Deterministic evidence mapping; candidate schedules are not live authorization."""
    tournament, wrows, wexcluded, level = _wta(wta_payload)
    if type(espn_payload.get("events")) is not list or len(espn_payload["events"]) > 128:
        raise ValueError("bounded ESPN event list required")
    candidates, event_audits = [], []
    wk = {_result_key(r) for r in wrows if r["status"] == "completed"}
    ids = [e.get("id") for e in espn_payload["events"]]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate ESPN event identity")
    for event in espn_payload["events"]:
        if (not re.fullmatch(r"[A-Za-z0-9_-]+", str(event.get("id", "")))
                or event.get("season", {}).get("year") != tournament["year"] or not _overlap(event, tournament)):
            continue
        erows, excluded = _espn(event, tournament["singlesDrawSize"])
        ek = {_result_key(r) for r in erows if r["status"] == "completed"}
        common = sorted(wk & ek)
        accepted = len(common) >= 8 and len(common) >= .8*max(len(wk),len(ek))
        event_audits.append({"espnId": event["id"], "sharedCompleted": len(common), "wtaCompleted": len(wk),
                             "espnCompleted": len(ek), "accepted": accepted})
        if accepted:
            candidates.append((event, erows, excluded, common))
    if len(candidates) != 1:
        return {"readyForLive": False, "issues": ["event-mapping-unproven-or-ambiguous"],
                "eventCandidates": event_audits, "wtaExcluded": wexcluded, "scheduleCandidates": [], "resultCandidates": []}
    event, erows, eexcluded, common = candidates[0]
    eindex = {(r["round"],r["pair"]): r for r in erows}
    schedules, results, exclusions, comparisons = [], [], Counter(), []
    context_ready = tournament.get("surface") in {"Hard", "Clay", "Grass"} and tournament.get("inOutdoor") in {"I", "O"}
    tier = tier_mults("wta")[0][TIER_NAMES[level]]
    for w in wrows:
        e = eindex.get((w["round"], w["pair"]))
        if e is None:
            exclusions["no-unique-ESPN-match"] += 1
            continue
        row = {"espnId": event["id"], "season": tournament["year"], "round": w["round"],
               "playerA": w["names"][0], "playerB": w["names"][1], "status": w["status"],
               "sourceEvidence": {"wtaMatchId": w["sourceMatchId"], "espnMatchId": e["sourceMatchId"],
                                  "wtaPath": w["path"], "espnPath": "/events/"+str(ids.index(event["id"]))+e["path"]}}
        match_key(row, "wta")
        if w["status"] == e["status"] == "scheduled":
            try:
                bound = _bound(w,e)
                if not context_ready or e["raw"].get("format", {}).get("regulation", {}).get("periods") != 3:
                    raise ValueError("missing-or-invalid-context")
                row.update(earliestStartAt=bound, surface=tournament["surface"], bestOf=3,
                           context={"event": event["name"], "as_of": bound, "indoor": tournament["inOutdoor"] == "I",
                                    "tier_k": tier, "round_order": ROUND_ORDER[w["round"]]})
                schedules.append(row)
            except ValueError as exc:
                exclusions[str(exc)] += 1
        elif w["status"] == e["status"] == "completed" and _result_key(w) == _result_key(e):
            row.update(winner=w["winner"], score=w["score"], timingStatus="actual-start-and-finish-unverified")
            results.append(row)
            # These are fields with unverified meanings, not actual-time discrepancies.
            try:
                comparisons.append((_time(e["raw"]["startDate"])-_time(w["raw"]["MatchTimeStamp"])).total_seconds())
            except (KeyError, ValueError, TypeError):
                pass
        elif w["status"] != e["status"]:
            exclusions["source-status-disagreement"] += 1
        else:
            exclusions["not-scheduled-or-normally-completed"] += 1
    return {"readyForLive": False,
            "issues": ["actual-start-and-finish-mapping-unverified", "not-before-semantics-and-lifecycle-unverified", "execution-cadence-unverified"],
            "mapping": {"wtaId": str(tournament["tournamentGroup"]["id"]), "year": tournament["year"], "espnId": event["id"],
                        "sharedCompleted": len(common), "evidenceSHA256": _digest(common), "basis": "edition-bounds-plus-unique-pair-round-winner-games"},
            "eventCandidates": event_audits, "wtaExcluded": wexcluded, "espnExcluded": eexcluded,
            "wtaMainRealRows": len(wrows), "espnMainRealRows": len(erows), "conversionExclusions": dict(exclusions),
            "scheduleCandidates": schedules, "resultCandidates": results, "actualTimedResults": 0,
            "scheduleFieldComparisons": {"n": len(comparisons), "equal": sum(x == 0 for x in comparisons),
                                         "minSeconds": min(comparisons,default=None), "maxSeconds": max(comparisons,default=None)}}


def draft_batches(analysis, espn_receipt, wta_receipt):
    """Diagnostic shapes retain original observation times; never make old data fresh."""
    metadata = {"tour": "wta", "observedAt": wta_receipt["receivedAt"], "sourceUrl": wta_receipt["url"],
                "adapterSchema": SCHEMA, "readyForLive": False,
                "sourceReceipts": {"espn": espn_receipt["sha256"], "wta": wta_receipt["sha256"]}}
    return {"schedule": {**metadata, "matches": analysis["scheduleCandidates"]},
            "results": {**metadata, "matches": analysis["resultCandidates"]}}


def export_live(*args, **kwargs):
    raise ValueError("live export unavailable: actual timing, lifecycle and cadence are not validated")


def lifecycle(snapshots):
    """Keep event/source-match identity and raw field changes; never infer actual times."""
    series = defaultdict(list)
    for receipt, payload in snapshots:
        seen = set()
        if receipt["source"] == "wta":
            event = payload["tournament"]
            for raw in payload["matches"]:
                if raw.get("DrawMatchType") != "S" or raw.get("DrawLevelType") != "M":
                    continue
                key = ("wta", str(event["tournamentGroup"]["id"]), event["year"], raw["MatchID"])
                if key in seen:
                    raise ValueError("duplicate source identity within snapshot")
                seen.add(key)
                state = {"U": "scheduled", "P": "live", "F": "terminal"}.get(raw.get("MatchState"), "unknown")
                pair = sorted(canonical_name(f'{raw.get("PlayerNameFirst"+s, "")} {raw.get("PlayerNameLast"+s, "")}') for s in ("A","B"))
                values = {"status": state, "pair": pair, "round": raw.get("RoundID"), "time": raw.get("MatchTimeStamp"),
                          "notBefore": raw.get("NotBeforeISOTime"), "score": raw.get("ScoreString"), "winner": raw.get("Winner")}
                series[key].append({"observedAt": receipt["receivedAt"], "receipt": receipt["sha256"], **values})
        else:
            for event in payload["events"]:
                for group in event.get("groupings",[]):
                    if group.get("grouping",{}).get("slug") != "womens-singles":
                        continue
                    for raw in group["competitions"]:
                        if "qualif" in raw.get("round",{}).get("displayName", "").lower():
                            continue
                        key = ("espn", event["id"], event["season"]["year"], raw["id"])
                        if key in seen:
                            raise ValueError("duplicate source identity within snapshot")
                        seen.add(key)
                        state = raw.get("status",{}).get("type",{}).get("state")
                        values = {"status": {"pre":"scheduled","in":"live","post":"terminal"}.get(state,"unknown"),
                                  "pair": sorted(str(_athlete_name(c)) for c in raw.get("competitors",[])),
                                  "round": raw.get("round"), "time": raw.get("startDate"),
                                  "score": [c.get("linescores") for c in raw.get("competitors",[])],
                                  "winner": [c.get("winner") for c in raw.get("competitors",[])]}
                        series[key].append({"observedAt": receipt["receivedAt"], "receipt": receipt["sha256"], **values})
    changed, counts = [], Counter()
    for key, rows in sorted(series.items()):
        rows.sort(key=lambda r: (_time(r["observedAt"]),r["receipt"]))
        states = [r["status"] for r in rows]
        complete = any(states[i] == "scheduled" and states[j] == "live" and states[k] == "terminal"
                       for i in range(len(states)) for j in range(i+1,len(states)) for k in range(j+1,len(states)))
        fields = sorted({f for first,last in zip(rows,rows[1:]) for f in set(first)|set(last)
                         if f not in {"observedAt","receipt"} and first.get(f) != last.get(f)})
        ranks = {"unknown": -1, "scheduled": 0, "live": 1, "terminal": 2}
        regression = any(ranks[right] < ranks[left] for left,right in zip(states,states[1:]))
        if "pair" in fields or "round" in fields or regression or "unknown" in states:
            complete = False
            counts["identityOrStatusConflict"] += 1
        counts["completePreLiveTerminal" if complete else "incompleteLifecycle"] += 1
        if fields:
            changed.append({"identity":list(key),"changedFields":fields,"statusRegression":regression,"observations":rows})
    return {"counts":dict(counts),"changed":changed,"actualTimingInferred":False,
            "note":"Observed transitions and time-field changes are audit facts, not exact actual-start/finish proof."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", required=True, type=Path)
    sub = parser.add_subparsers(dest="command",required=True)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("source",choices=("espn","wta"))
    fetch.add_argument("root",type=Path)
    fetch.add_argument("--event")
    fetch.add_argument("--year",type=int)
    analyze = sub.add_parser("audit")
    analyze.add_argument("espn",type=Path)
    analyze.add_argument("wta",type=Path)
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "fetch":
        output = fetch_once(**args)
    else:
        er,ep = read_capture(args["espn"],trusted_root=args["trusted_root"])
        wr,wp = read_capture(args["wta"],trusted_root=args["trusted_root"])
        output = {"analysis":audit(ep,wp),"freshness":{"espn":freshness(er),"wta":freshness(wr)}}
    print(json.dumps(output,indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
