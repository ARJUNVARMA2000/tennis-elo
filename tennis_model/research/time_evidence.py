"""Typed start intervals and observed completion bounds; never infer play from a schedule."""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import defaultdict
from datetime import timedelta

import prospective_sources as sources
from tennis_model.data.bracket_rounds import player_identity_key
from tennis_model.eval.prospective import _bytes, _digest, _time, match_key

POLICY = {
    "schema": "prospective-time-evidence-v2",
    "marginMinutes": 5,
    "startProducers": ["synthetic-start-v1"],
    "completionProducers": ["synthetic-completed-v1", "espn-wta-completed-v1"],
    "liveQualified": False,
    "weekBasis": "unambiguous-actual-start-interval",
}
TERMINAL = frozenset({"completed", "retired", "walkover", "withdrawn", "cancelled"})


def check_mode(evidence_kind):
    if evidence_kind != "synthetic-qa":
        raise ValueError("no qualified live start producer; only explicit synthetic-qa registration is available")


def _common(value, row, batch, producer):
    if type(value) is not dict:
        raise ValueError("typed time evidence required")
    if value.get("producer") not in producer:
        raise ValueError("unqualified time producer")
    if value.get("matchKey") != match_key(row, "wta"):
        raise ValueError("time evidence match identity differs")
    if type(value.get("sourceSHA256")) is not str or not re.fullmatch(r"[0-9a-f]{64}", value["sourceSHA256"]):
        raise ValueError("time evidence source digest required")
    observed = _time(value["observedAt"])
    if observed > _time(batch["observedAt"]):
        raise ValueError("time evidence observed after its source batch")
    return observed


def start_interval(value, row, batch, *, evidence_kind):
    """Exact events include measurement uncertainty; upper bounds alone cannot qualify."""
    check_mode(evidence_kind)
    observed = _common(value, row, batch, POLICY["startProducers"])
    fields = {"kind", "producer", "matchKey", "sourceSHA256", "observedAt"}
    if value.get("kind") == "actual-start":
        if set(value) != fields | {"at", "errorSeconds"}:
            raise ValueError("exact event fields differ")
        error = value["errorSeconds"]
        if type(error) is not int or not 0 <= error <= 3600:
            raise ValueError("bounded explicit timestamp error required")
        lower = _time(value["at"]) - timedelta(seconds=error)
        upper = _time(value["at"]) + timedelta(seconds=error)
    elif value.get("kind") == "actual-start-interval":
        if set(value) != fields | {"lowerAt", "upperAt"}:
            raise ValueError("start interval fields differ")
        lower, upper = _time(value["lowerAt"]), _time(value["upperAt"])
    else:
        raise ValueError("schedule, live observation or upper bound is not actual-start proof")
    if not lower <= upper <= observed:
        raise ValueError("reversed or future start interval")
    return lower, upper


def completion_bound(value, row, batch, *, evidence_kind):
    check_mode(evidence_kind)
    observed = _common(value, row, batch, POLICY["completionProducers"])
    if (
        set(value) != {"kind", "producer", "matchKey", "sourceSHA256", "observedAt"}
        or value["kind"] != "completed-observation"
        or row.get("status") != "completed"
    ):
        raise ValueError("normal completed observation required")
    if value["producer"] == "espn-wta-completed-v1":
        bundle = batch.get("completionBundle")
        if type(bundle) is not dict or value["sourceSHA256"] != _digest(bundle):
            raise ValueError("completion source bundle differs")
        match = {k: v for k, v in row.items() if k not in {"startEvidence", "completionEvidence"}}
        if match not in bundle.get("matches", []):
            raise ValueError("completion not in source bundle")
        if set(bundle.get("sources", {})) != {"espn", "wta"} or observed != max(
            _time(r["receivedAt"]) for r in bundle["sources"].values()
        ):
            raise ValueError("completion observation clock differs")
    return observed


def resolve(evidence, *, original, captured_at, evidence_kind):
    """Accumulate complete claims, retaining contradictions and conservative bounds."""
    if any(r.get("status") == "source-conflict" for r, _, _ in evidence):
        return None, "sourceResultConflict"
    terminal = [(r, b, i) for r, b, i in evidence if r.get("status") in TERMINAL]
    if not terminal:
        return None, "pending"
    if len({r["status"] for r, _, _ in terminal}) != 1:
        return None, "conflictingResults"
    if terminal[0][0]["status"] != "completed":
        return None, terminal[0][0]["status"]
    winners, scores, starts, completions, complete = set(), set(), [], [], []
    try:
        for row, batch, identity in terminal:
            if any(field in row for field in ("actualStartedAt", "finishedAt")):
                return None, "legacyTimeFields"
            if row.get("winner"):
                winners.add(player_identity_key(row["winner"]))
            if row.get("score") is not None:
                scores.add(_bytes(row["score"]))
            start = finish = None
            if row.get("startEvidence") is not None:
                start = start_interval(row["startEvidence"], row, batch, evidence_kind=evidence_kind)
                starts.append(start)
            if row.get("completionEvidence") is not None:
                finish = completion_bound(row["completionEvidence"], row, batch, evidence_kind=evidence_kind)
                completions.append(finish)
            if row.get("winner") and start and finish:
                complete.append((row, batch, identity))
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return None, "invalidTimeEvidence"
    if len(winners) > 1 or len(scores) > 1:
        return None, "conflictingResults"
    if starts and max(lo for lo, _ in starts) > min(hi for _, hi in starts):
        return None, "conflictingStartIntervals"
    if not starts:
        return None, "missingStartProof"
    if not completions:
        return None, "missingCompletionProof"
    if not complete:
        return None, "noCompleteTimingClaim"
    lower, upper = min(lo for lo, _ in starts), max(hi for _, hi in starts)
    finish = min(completions)
    # A verified completion bounds the start above too. It cannot strengthen its lower edge.
    upper = min(upper, finish)
    if (
        not lower <= upper
        or max(lo for lo, _ in starts) > finish
        or not _time(captured_at) + timedelta(minutes=5) < _time(original["earliestStartAt"]) <= lower
    ):
        return None, "timingNotProved"
    chosen = min(complete, key=lambda item: (_time(item[1]["observedAt"]), item[2]))
    proof = {
        "schema": POLICY["schema"],
        "startLowerAt": lower.isoformat(),
        "startUpperAt": upper.isoformat(),
        "finishUpperAt": finish.isoformat(),
        "sourceEvidence": sorted({identity for _, _, identity in terminal}),
    }
    return {
        "row": chosen[0],
        "resultEvidence": chosen[2],
        "startLowerAt": lower.isoformat(),
        "startUpperAt": upper.isoformat(),
        "proof": proof,
    }, None


def identity_conflicts(rows):
    by_source = defaultdict(set)
    for row in rows:
        evidence = row.get("sourceEvidence", {})
        if type(evidence) is not dict:
            raise ValueError("source identity must be an object")
        for field in ("espnMatchId", "wtaMatchId"):
            if field in evidence:
                if type(evidence[field]) is not str or not evidence[field]:
                    raise ValueError("source match id required")
                by_source[(row["espnId"], row["season"], field, evidence[field])].add(match_key(row, "wta"))
    return {key for keys in by_source.values() if len(keys) > 1 for key in keys}


def moved_earlier(original, history):
    key = match_key(original, "wta")
    for row in history:
        if match_key(row, "wta") != key or "earliestStartAt" not in row:
            continue
        try:
            if _time(row["earliestStartAt"]) < _time(original["earliestStartAt"]):
                return True
        except (ValueError, TypeError, AttributeError):
            return True
    return False


def completed_batch(espn_path, wta_path, *, trusted_root):
    """Convert retained acquisition receipts; these bounds do not prove pre-play capture."""
    captures = {
        name: sources.read_capture(path, trusted_root=trusted_root)
        for name, path in (("espn", espn_path), ("wta", wta_path))
    }
    # read_capture returns receipt and decoded body; both must be the requested providers.
    receipts = {name: capture[0] for name, capture in captures.items()}
    if any(r["source"] != name for name, r in receipts.items()):
        raise ValueError("completion source roles differ")
    analysis = sources.audit(captures["espn"][1], captures["wta"][1])
    rows = copy.deepcopy(analysis["resultCandidates"])
    identities = []
    if analysis.get("mapping"):
        tournament, wrows, _, _ = sources._wta(captures["wta"][1])
        event = next(e for e in captures["espn"][1]["events"] if e["id"] == analysis["mapping"]["espnId"])
        erows, _ = sources._espn(event, tournament["singlesDrawSize"])
        eindex = {(r["round"], r["pair"]): r for r in erows}
        admitted = {match_key(r, "wta") for r in rows}
        for provider, records in (("wta", wrows), ("espn", erows)):
            for record in records:
                identities.append(
                    {
                        "espnId": event["id"],
                        "season": tournament["year"],
                        "round": record["round"],
                        "playerA": record["names"][0],
                        "playerB": record["names"][1],
                        "status": record["status"],
                        "sourceEvidence": {provider + "MatchId": record["sourceMatchId"]},
                    }
                )
        terminal_states = TERMINAL | {"terminal", "unresolved-terminal"}
        for w in wrows:
            e = eindex.get((w["round"], w["pair"]))
            row = {
                "espnId": event["id"],
                "season": tournament["year"],
                "round": w["round"],
                "playerA": w["names"][0],
                "playerB": w["names"][1],
                "status": "source-conflict",
                "sourceEvidence": {"wtaMatchId": w["sourceMatchId"]},
            }
            if (
                e is not None
                and w["status"] in terminal_states
                and e["status"] in terminal_states
                and match_key(row, "wta") not in admitted
            ):
                row["sourceEvidence"]["espnMatchId"] = e["sourceMatchId"]
                rows.append(row)
    bundle = {
        "schema": "espn-wta-completion-bundle-v1",
        "mapping": analysis.get("mapping"),
        "sources": {
            name: {
                "url": r["url"],
                "receivedAt": r["receivedAt"],
                "receiptSHA256": r["sha256"],
                "rawSHA256": r["rawSHA256"],
            }
            for name, r in receipts.items()
        },
        "matches": copy.deepcopy(rows),
        "sourceIdentityRows": identities,
    }
    observed = max(_time(r["receivedAt"]) for r in receipts.values()).isoformat()
    for row in rows:
        if row["status"] != "completed":
            continue
        row["completionEvidence"] = {
            "kind": "completed-observation",
            "producer": "espn-wta-completed-v1",
            "matchKey": match_key(row, "wta"),
            "sourceSHA256": _digest(bundle),
            "observedAt": observed,
        }
    return {
        "tour": "wta",
        "observedAt": observed,
        "sourceUrl": receipts["wta"]["url"],
        "completionBundle": bundle,
        "matches": rows,
        "sourceIdentityRows": identities,
        "startProofCount": 0,
        "readyForLive": False,
        "auditIssues": analysis["issues"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", required=True)
    parser.add_argument("espn_capture")
    parser.add_argument("wta_capture")
    args = parser.parse_args()
    batch = completed_batch(args.espn_capture, args.wta_capture, trusted_root=args.trusted_root)
    print(json.dumps(batch, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
