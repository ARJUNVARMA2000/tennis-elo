"""Audit official US Open/WTA/ESPN identities, without timing or forecast export."""
import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import prospective_sources as p
import usopen_schedule as u
from tennis_model.eval.prospective import _bytes, _digest, _time

SCHEMA = "usopen-identity-audit-v1"
ROUND_LABELS = {**{str(i): f"Round {i}" for i in range(1, 5)},
                "Q": "Quarter-Finals", "S": "Semi-Finals", "F": "Final"}
ROUND_COUNTS = {"1": 64, "2": 32, "3": 16, "4": 8, "Q": 4, "S": 2, "F": 1}


def endpoint(year, kind):
    u.endpoint(year)  # Same explicit edition bounds as the schedule collector.
    if kind not in {"index", "draw"}:
        raise ValueError("explicit index or WS draw required")
    file = "draws" if kind == "index" else "WS"
    return f"https://www.usopen.org/en_US/scores/feeds/{year}/draws/{file}.json"


def read_draw(root, *, trusted_root, year, kind):
    """Read a retained bounded inspection; never fetch or freshen its receipt."""
    root = Path(root)
    receipt = p._json(p._read(root / "receipt.json", trusted_root))
    attempt = p._json(p._read(root / "attempt.json", trusted_root))
    raw = p._read(root / "response.bin", trusted_root)
    if (receipt.get("schema") != "official-draw-inspection-v1"
            or any(receipt.get(k) != v for k, v in attempt.items())
            or receipt.get("url") != endpoint(year, kind)
            or receipt.get("responseUrl") != receipt["url"]
            or receipt.get("status") != 200 or receipt.get("rawComplete") is not True
            or receipt.get("error") or len(raw) != receipt.get("rawBytes")
            or hashlib.sha256(raw).hexdigest() != receipt.get("rawSHA256")
            or _time(receipt["receivedAt"]) < _time(receipt["requestedAt"])):
        raise ValueError("official draw capture integrity/source failure")
    payload = u._validate_http(receipt, raw)
    return {**receipt, "sha256": _digest(receipt)}, payload


def retained_provider(name):
    if name not in {"wta", "espn"}:
        raise ValueError("known retained provider required")
    fixtures = Path(__file__).parents[1] / "tests/fixtures/prospective_sources"
    entry = p._json((fixtures / "manifest.json").read_bytes())[name]
    encoded = (fixtures / f"{name}.json.gz").read_bytes()
    if hashlib.sha256(encoded).hexdigest() != entry["compressedSHA256"]:
        raise ValueError("retained provider archive integrity failure")
    raw = gzip.decompress(encoded)
    receipt = entry["originalReceipt"]
    if (len(raw) != entry["rawBytes"] or hashlib.sha256(raw).hexdigest() != entry["rawSHA256"]
            or receipt["rawSHA256"] != entry["rawSHA256"]):
        raise ValueError("retained provider raw integrity failure")
    return {**receipt, "sha256": _digest(receipt), "provenance": "pinned-retrospective-provider"}, p._json(raw)


def _draw(index, draw, year):
    entries = index.get("draws")
    if type(entries) is not list or not 1 <= len(entries) <= 64 or any(type(e) is not dict for e in entries):
        raise ValueError("bounded official draw index required")
    selected = [e for e in entries if e.get("id") == "WS"]
    if len(selected) != 1 or selected[0].get("feed_url") != endpoint(year, "draw"):
        raise ValueError("ambiguous or wrong-edition WS draw endpoint")
    raw_rows = draw.get("matches")
    if (draw.get("drawFormat") != "bracket" or draw.get("drawSize") != "128"
            or type(draw.get("totalRounds")) is not int or draw["totalRounds"] != 7
            or type(raw_rows) is not list or len(raw_rows) != 127
            or any(type(r) is not dict for r in raw_rows)
            or Counter(r.get("roundCode") for r in raw_rows) != ROUND_COUNTS):
        raise ValueError("complete 128-player seven-round bracket required")
    rows, exclusions, mids, matchups = [], [], set(), set()
    for i, raw in enumerate(raw_rows):
        mid = raw.get("match_id")
        if type(mid) is not str or not re.fullmatch(r"[0-9]{4}", mid) or mid in mids:
            raise ValueError("malformed or duplicate official match ID")
        mids.add(mid)
        if raw.get("eventCode") != "WS" or ROUND_LABELS[raw["roundCode"]] != raw.get("roundName"):
            raise ValueError("official row population/round conflict")
        path = f"/matches/{i}"
        try:
            teams = [raw.get(k) for k in ("team1", "team2")]
            if any(type(t) is not dict or t.get("idB") for t in teams):
                raise ValueError("invalid singles teams")
            if any(type(t.get(k)) is not str or not t[k].strip()
                   for t in teams for k in ("firstNameA", "lastNameA")):
                raise ValueError("invalid or unresolved official player names")
            names = [p.canonical_name(f"{t.get('firstNameA') or ''} {t.get('lastNameA') or ''}") for t in teams]
            pair = p._pair(names)
            ids = [t.get("idA") for t in teams]
            if (any(type(pid) is not str or not re.fullmatch(r"wta[1-9][0-9]+", pid) for pid in ids)
                    or len(set(ids)) != 2):
                raise ValueError("invalid or unresolved official player IDs")
        except ValueError as exc:
            exclusions.append({"sourceMatchId": mid, "path": path, "reason": str(exc)})
            continue
        rnd = p._round(raw["roundCode"], 128, provider="wta")
        key = (rnd, pair)
        if key in matchups:
            raise ValueError("duplicate official real matchup/round")
        matchups.add(key)
        state = {("Completed", "D"): "completed", ("", "B"): "scheduled"}.get(
            (raw.get("status"), raw.get("statusCode")), "unresolved-status")
        winner, score, issue = None, None, None
        if state == "completed":
            try:
                if raw.get("winner") not in ("1", "2"):
                    raise ValueError("invalid winner code")
                wi = int(raw["winner"]) - 1
                if teams[wi].get("won") is not True or teams[1 - wi].get("won") is not False:
                    raise ValueError("conflicting winner flags")
                sets = raw.get("scores", {}).get("sets")
                if type(sets) is not list or len(sets) not in (2, 3):
                    raise ValueError("invalid completed sets")
                games = []
                for ss in sets:
                    if (type(ss) is not list or len(ss) != 2
                            or any(type(s) is not dict or type(s.get("score")) is not int or s["score"] < 0 for s in ss)):
                        raise ValueError("invalid set games")
                    games.append((ss[wi]["score"], ss[1 - wi]["score"]))
                score = " ".join(f"{a}-{b}" for a, b in games)
                if not p.completed_score(score):
                    raise ValueError("not a normal completed match")
                totals = [sum(a > b for a, b in games), sum(b > a for a, b in games)]
                if any(type(teams[j].get("totalSetsWon")) is not int or teams[j]["totalSetsWon"] != totals[k]
                       for k, j in enumerate((wi, 1 - wi))):
                    raise ValueError("set totals conflict")
                winner = names[wi]
            except (ValueError, TypeError, AttributeError) as exc:
                state, issue, winner, score = "unresolved-terminal", str(exc), None, None
        rows.append({"sourceMatchId": mid, "round": rnd, "roundCode": raw["roundCode"], "pair": pair,
                     "names": names, "playerIDs": ids, "status": state, "winner": winner, "score": score,
                     "terminalIssue": issue, "path": path})
    return rows, exclusions, sum(r.get("statusCode") == "D" for r in raw_rows)


def _ids_by_player(names, ids):
    return {p.player_identity_key(n): pid for n, pid in zip(names, ids, strict=True)}


def audit(index, draw, espn, wta, *, year):
    """Pure identity predicates; only run() binds them to verified observations."""
    official, excluded, claimed_completed = _draw(index, draw, year)
    tournament, wrows, _, _ = p._wta(wta)
    if year != tournament["year"] or tournament["singlesDrawSize"] != 128:
        raise ValueError("official/WTA edition or draw-size conflict")
    existing = p.audit(espn, wta)
    result = {"schema": SCHEMA, "edition": year, "eventAccepted": False, "links": [],
              "exclusions": excluded, "issues": [], "readyForLiveEvaluation": False,
              "actualStartVerified": False, "sourceRows": 127, "realOfficialRows": len(official)}
    if "mapping" not in existing:
        return {**result, "issues": ["WTA-ESPN-event-unproven-or-ambiguous"]}
    event_index, event = next((idx, e) for idx, e in enumerate(espn["events"])
                             if e["id"] == existing["mapping"]["espnId"])
    erows, _ = p._espn(event, 128)
    completed = [{p._result_key(r) for r in rows if r["status"] == "completed"}
                 for rows in (official, wrows, erows)]
    common = sorted(set.intersection(*completed))
    denominator = max(claimed_completed, len(completed[1]), len(completed[2]))
    result["eventEvidence"] = {"sharedCompleted": len(common), "officialClaimedCompleted": claimed_completed,
                               "wtaCompleted": len(completed[1]), "espnCompleted": len(completed[2]),
                               "requiredFraction": .8, "evidenceSHA256": _digest(common),
                               "basis": "explicit-edition-and-unique-pair-round-winner-games"}
    if len(common) < 8 or len(common) < .8 * denominator:
        return {**result, "issues": ["insufficient-completed-event-overlap"]}
    result.update(eventAccepted=True, mapping={**existing["mapping"], "officialEventCode": "WS"})
    windex = {(r["round"], r["pair"]): r for r in wrows}
    eindex = {(r["round"], r["pair"]): r for r in erows}
    for row in official:
        key = (row["round"], row["pair"])
        wr, er = windex.get(key), eindex.get(key)
        reasons, detail = [], {}
        if wr is None or er is None:
            reasons.append("missing-provider-matchup")
        else:
            wids = [str(wr["raw"]["PlayerID" + suffix]) for suffix in ("A", "B")]
            oid = _ids_by_player(row["names"], [pid.removeprefix("wta") for pid in row["playerIDs"]])
            wid = _ids_by_player(wr["names"], wids)
            if oid != wid:
                reasons.append("player-number-disagreement")
                detail.update(officialPlayerNumbers=oid, wtaPlayerNumbers=wid)
            if any(r["status"] not in {"completed", "scheduled", "live"} for r in (row, wr, er)):
                reasons.append("unresolved-source-status-or-terminal")
            terminal = [p._result_key(r) for r in (row, wr, er) if r["status"] == "completed"]
            if len(set(terminal)) > 1:
                reasons.append("terminal-result-conflict")
        if reasons:
            result["exclusions"].append({"sourceMatchId": row["sourceMatchId"], "path": row["path"],
                                         "reasons": reasons, "terminalIssue": row["terminalIssue"], **detail})
            continue
        result["links"].append({"sourceMatchKey": f"usopen:{year}:{row['sourceMatchId']}",
                               "sourceMatchId": row["sourceMatchId"], "edition": year,
                               "espnId": event["id"], "wtaEventId": existing["mapping"]["wtaId"],
                               "wtaMatchId": wr["sourceMatchId"], "espnMatchId": er["sourceMatchId"],
                               "round": row["round"], "roundCode": row["roundCode"],
                               "players": row["names"], "playerIDs": row["playerIDs"],
                               "observedStatuses": {"official": row["status"], "wta": wr["status"], "espn": er["status"]},
                               "sourcePaths": {"official": row["path"], "wta": wr["path"],
                                               "espn": f"/events/{event_index}" + er["path"]}})
    return result


def associate(history, analysis, *, evidence_at):
    """Retrospective annotations only; any identity conflict excludes all versions."""
    links = {r["sourceMatchKey"]: r for r in analysis["links"]} if analysis["eventAccepted"] else {}
    conflicts, associations, exclusions = set(history["identityConflicts"]), [], []
    for key, versions in history["versions"].items():
        link = links.get(key)
        if not link:
            exclusions.append({"sourceMatchKey": key, "reason": "no-qualified-identity-link", "versions": len(versions)})
            continue
        for row in versions:
            if (row["edition"] != link["edition"] or row["roundCode"] != link["roundCode"]
                    or _ids_by_player(row["players"], row["playerIDs"]) != _ids_by_player(link["players"], link["playerIDs"])):
                conflicts.add(key)
        if key in conflicts:
            exclusions.append({"sourceMatchKey": key, "reason": "schedule-draw-identity-conflict", "versions": len(versions)})
            continue
        for row in versions:
            associations.append({"scheduleObservation": row, "identityLink": link,
                                 "associationAvailableAt": max(_time(evidence_at), _time(row["observedAtUTC"])).isoformat(),
                                 "retrospectiveAssociation": True, "readyForLiveEvaluation": False})
    return {"associations": associations, "exclusions": exclusions, "identityConflicts": sorted(conflicts),
            "purpose": "identity annotations; not forecast/context donation", "actualStartVerified": False}


def run(index_root, draw_root, collections, *, trusted_root, year):
    captures = {"index": read_draw(index_root, trusted_root=trusted_root, year=year, kind="index"),
                "draw": read_draw(draw_root, trusted_root=trusted_root, year=year, kind="draw"),
                **{name: retained_provider(name) for name in ("espn", "wta")}}
    if _time(captures["draw"][0]["requestedAt"]) < _time(captures["index"][0]["receivedAt"]):
        raise ValueError("draw was not acquired after its index")
    analysis = audit(*(captures[k][1] for k in ("index", "draw", "espn", "wta")), year=year)
    evidence_at = max(_time(r["receivedAt"]) for r, _ in captures.values()).isoformat()
    analysis["sourceReceipts"] = {name: receipt for name, (receipt, _) in captures.items()}
    analysis["evidenceAvailableAt"] = evidence_at
    analysis["providerBasis"] = "pinned historical provider captures; not current result intake"
    history = u.history(collections, trusted_root=trusted_root)
    analysis["scheduleInputs"] = history["inputs"]
    analysis["scheduleGaps"] = history["gaps"]
    analysis["scheduleAssociations"] = associate(history, analysis, evidence_at=evidence_at)
    return analysis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", required=True, type=Path)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--index-root", required=True, type=Path)
    parser.add_argument("--draw-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("collections", nargs="+", type=Path)
    args = vars(parser.parse_args())
    output = args.pop("output")
    if p.a._absolute_without_symlink_resolution(output).is_relative_to(p.a._absolute_without_symlink_resolution(u.OUTPUT_DIR)):
        raise ValueError("identity audits cannot enter production output")
    result = run(**args)
    p._write(output, _bytes({**result, "sha256": _digest(result)}), args["trusted_root"])
    print(json.dumps({"eventAccepted": result["eventAccepted"], "links": len(result["links"]),
                      "exclusions": len(result["exclusions"]), "associatedVersions": len(result["scheduleAssociations"]["associations"])}))


if __name__ == "__main__":
    main()
