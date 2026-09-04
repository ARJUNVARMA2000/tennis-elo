"""Prospective, evaluation-only comparison of two frozen compatible predictors.

Registration fixes both artifacts and the observation horizon before any calls. Capture
prices the same scheduled matchup with both arms and timestamps the receipt after inference.
Grading requires independent actual-start evidence and never changes a forecast receipt.
This research CLI is intentionally separate from production and the walk-forward arbiter.
See tasks/research/PROSPECTIVE.md for the input contract and commands.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev

from ..data.bracket_rounds import player_identity_key
from ..data.participants import is_real_participant
from ..model.artifact import (
    load_predictor_artifact,
    predictor_envelope_path,
    save_predictor_artifact,
)
from ..model.predict import can_predict_match

SCHEMA = "prospective-v1"
ROLES = ("incumbent", "candidate")
ROUNDS = frozenset({"R128", "R64", "R32", "R16", "QF", "SF", "F", "RR"})


def _now() -> datetime:
    return datetime.now(UTC)


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(UTC)


def _bytes(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def _digest(payload: object) -> str:
    return hashlib.sha256(_bytes(payload)).hexdigest()


def _read(path: Path) -> dict:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict) or value.get("sha256") != _digest(
            {k: v for k, v in value.items() if k != "sha256"}):
        raise ValueError(f"receipt integrity failure: {path.name}")
    if value.get("schema") != SCHEMA:
        raise ValueError("unsupported prospective schema")
    return value


def _write_once(path: Path, payload: dict) -> bool:
    """Atomic create-only publication; concurrent retries cannot replace first sighting."""
    raw = _bytes({**payload, "sha256": _digest(payload)})
    descriptor, temporary = tempfile.mkstemp(prefix=".receipt-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            return False
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        return True
    finally:
        os.unlink(temporary)


def _files(root: Path, role: str) -> dict[str, str]:
    path = root / f"{role}.pkl"
    return {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
            for file in (path, predictor_envelope_path(path))}


def register(root: Path, *, tour: str, hypothesis: str, incumbent: Path, candidate: Path,
             days: int = 30, min_pairs: int = 200) -> dict:
    if tour not in ("atp", "wta") or not hypothesis.strip():
        raise ValueError("a tour and a written hypothesis are required")
    if not 1 <= days <= 180 or min_pairs < 2:
        raise ValueError("use a 1–180 day horizon and at least two target pairs")
    models = {role: load_predictor_artifact(path, tour)
              for role, path in zip(ROLES, (incumbent, candidate), strict=True)}
    if models["incumbent"].artifact_id == models["candidate"].artifact_id:
        raise ValueError("candidate must be a distinct fitted artifact")
    root.mkdir(parents=True, exist_ok=False)
    (root / "receipts").mkdir()
    (root / "observations").mkdir()
    (root / "results").mkdir()
    for role, model in models.items():
        save_predictor_artifact(model, root / f"{role}.pkl", trusted_root=root)
    now = _now()
    if any(_time(model.trained_at) > now for model in models.values()):
        raise ValueError("a frozen model claims training in the future")
    receipt = {
        "schema": SCHEMA, "tour": tour, "hypothesis": hypothesis.strip(),
        "registeredAt": now.isoformat(), "captureUntil": (now + timedelta(days=days)).isoformat(),
        "minPairs": min_pairs, "primaryMetric": "logloss", "delta": "incumbent-minus-candidate",
        "models": {role: {"artifactId": model.artifact_id, "trainedAt": model.trained_at,
                          "files": _files(root, role)} for role, model in models.items()},
    }
    _write_once(root / "registration.json", receipt)
    return _read(root / "registration.json")


def _models(root: Path, registration: dict) -> dict:
    models = {}
    for role in ROLES:
        expected = registration["models"][role]
        if _files(root, role) != expected["files"]:
            raise ValueError(f"frozen {role} artifacts changed")
        models[role] = load_predictor_artifact(root / f"{role}.pkl", registration["tour"], trusted_root=root)
        if models[role].artifact_id != expected["artifactId"]:
            raise ValueError("frozen model identity changed")
    return models


def match_key(row: dict, tour: str) -> str:
    event = row.get("espnId")
    season = row.get("season")
    rnd = row.get("round")
    if not isinstance(event, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", event):
        raise ValueError("stable ESPN event identity required")
    if type(season) is not int or not 2000 <= season <= 2100 or rnd not in ROUNDS:
        raise ValueError("explicit season and canonical main-draw round required")
    if not all(is_real_participant(row.get(side)) for side in ("playerA", "playerB")):
        raise ValueError("two real players required")
    players = sorted(player_identity_key(row.get(side)) for side in ("playerA", "playerB"))
    if not all(players) or players[0] == players[1]:
        raise ValueError("two distinct real player identities required")
    return _digest([tour, event, season, rnd, players])


def capture(root: Path, schedule: dict) -> dict:
    registration = _read(root / "registration.json")
    now = _now()
    if not _time(registration["registeredAt"]) <= now < _time(registration["captureUntil"]):
        raise ValueError("outside the registered capture horizon")
    observed = _time(schedule["observedAt"])
    if not timedelta(0) <= now - observed <= timedelta(minutes=10):
        raise ValueError("schedule observation must be from the last ten minutes")
    if schedule.get("tour") != registration["tour"] or not str(schedule.get("sourceUrl", "")).startswith("https://"):
        raise ValueError("schedule tour and HTTPS source URL required")
    rows = schedule.get("matches")
    if not isinstance(rows, list) or len(rows) > 2048:
        raise ValueError("bounded schedule matches array required")
    models = _models(root, registration)
    counters = Counter()
    seen = set()
    for row in rows:
        key = match_key(row, registration["tour"])
        if key in seen:
            raise ValueError("duplicate matchup in one schedule observation")
        seen.add(key)
    observation = {"schema": SCHEMA, "registration": registration["sha256"],
                   "capturedAt": now.isoformat(), "schedule": schedule}
    observation_id = _digest(observation)
    _write_once(root / "observations" / f"{observation_id}.json", observation)
    for row in rows:
        key = match_key(row, registration["tour"])
        destination = root / "receipts" / f"{key}.json"
        if destination.exists():
            _read(destination)
            counters["alreadyCaptured"] += 1
            continue
        if row.get("status") != "scheduled":
            counters["notScheduled"] += 1
            continue
        start = _time(row["earliestStartAt"])
        if start <= _now() + timedelta(minutes=5):
            counters["tooLateOrUncertain"] += 1
            continue
        if row.get("surface") not in ("Hard", "Clay", "Grass") or row.get("bestOf") not in (3, 5):
            counters["missingContext"] += 1
            continue
        if not all(can_predict_match(model, row["playerA"], row["playerB"]) for model in models.values()):
            counters["unpriced"] += 1
            continue
        # Both arms receive exactly the same factual context; missing context is excluded.
        context = row.get("context", {})
        if set(context) != {"event", "as_of", "indoor", "tier_k", "round_order"}:
            counters["missingContext"] += 1
            continue
        if (not isinstance(context["event"], str) or not context["event"].strip()
                or type(context["indoor"]) is not bool
                or type(context["round_order"]) is not int or not 0 <= context["round_order"] <= 10
                or type(context["tier_k"]) not in (float, int)
                or not math.isfinite(context["tier_k"]) or context["tier_k"] <= 0
                or _time(context["as_of"]) != start or start.year != row["season"]):
            counters["missingContext"] += 1
            continue
        probabilities = {role: float(model.prediction_components(
            row["playerA"], row["playerB"], surface=row["surface"], best_of=row["bestOf"],
            **context)["combiner"]) for role, model in models.items()}
        if not all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values()):
            raise ValueError("model produced invalid probability")
        captured = _now()  # Timestamp AFTER both arms finish, never caller supplied.
        if captured + timedelta(minutes=5) >= start or captured >= _time(registration["captureUntil"]):
            counters["tooLateOrUncertain"] += 1
            continue
        receipt = {"schema": SCHEMA, "registration": registration["sha256"],
                   "matchKey": key, "observation": observation_id, "match": row,
                   "capturedAt": captured.isoformat(), "probabilities": probabilities}
        counters["captured" if _write_once(destination, receipt) else "alreadyCaptured"] += 1
    return dict(counters)


def grade(root: Path, results: dict) -> dict:
    registration = _read(root / "registration.json")
    if results.get("tour") != registration["tour"] or not str(results.get("sourceUrl", "")).startswith("https://"):
        raise ValueError("result tour and HTTPS source URL required")
    observed = _time(results["observedAt"])
    if observed > _now():
        raise ValueError("result observation is in the future")
    index = {}
    for row in results["matches"]:
        key = match_key(row, registration["tour"])
        if key in index:
            raise ValueError("ambiguous duplicate results")
        index[key] = row
    result_evidence = {"schema": SCHEMA, "registration": registration["sha256"], "results": results}
    result_id = _digest(result_evidence)
    _write_once(root / "results" / f"{result_id}.json", result_evidence)
    excluded = Counter()
    scored = []
    pending = 0
    for path in sorted((root / "receipts").glob("*.json")):
        receipt = _read(path)
        key = match_key(receipt["match"], registration["tour"])
        if receipt["registration"] != registration["sha256"] or key != path.stem or key != receipt["matchKey"]:
            raise ValueError("forecast receipt belongs to a different experiment or match")
        observation = _read(root / "observations" / f'{receipt["observation"]}.json')
        if (observation["sha256"] != receipt["observation"]
                or observation["registration"] != registration["sha256"]
                or receipt["match"] not in observation["schedule"]["matches"]):
            raise ValueError("forecast receipt lost its source observation")
        result = index.get(key)
        if result is None or result.get("status") in ("scheduled", "live", "in_progress"):
            pending += 1
            continue
        if result.get("status") != "completed":
            excluded[str(result.get("status", "unknownStatus"))] += 1
            continue
        if not result.get("actualStartedAt") or not result.get("finishedAt"):
            excluded["missingActualTiming"] += 1
            continue
        started, finished = _time(result["actualStartedAt"]), _time(result["finishedAt"])
        if not _time(receipt["capturedAt"]) < started <= finished <= observed:
            excluded["timingNotProved"] += 1
            continue
        original = receipt["match"]
        winner = player_identity_key(result.get("winner"))
        if winner not in {player_identity_key(original["playerA"]), player_identity_key(original["playerB"])}:
            excluded["winnerMismatch"] += 1
            continue
        a_won = winner == player_identity_key(original["playerA"])
        scores = {}
        for role, probability in receipt["probabilities"].items():
            p_winner = probability if a_won else 1 - probability
            scores[role] = {"logloss": -math.log(max(1e-12, min(1 - 1e-12, p_winner))),
                            "brier": (1 - p_winner) ** 2}
        scored.append(scores)
    paired = {}
    for metric in ("logloss", "brier"):
        deltas = [s["incumbent"][metric] - s["candidate"][metric] for s in scored]
        paired[metric] = {
            **{role: mean(s[role][metric] for s in scored) if scored else None for role in ROLES},
            "delta": mean(deltas) if deltas else None,
            "se": stdev(deltas) / math.sqrt(len(deltas)) if len(deltas) >= 2 else None,
        }
    return {"schema": SCHEMA, "registration": registration["sha256"], "resultEvidence": result_id,
            "graded": len(scored), "pending": pending, "excluded": dict(excluded), "paired": paired,
            "targetPairs": registration["minPairs"], "targetReached": len(scored) >= registration["minPairs"],
            "captureClosed": _now() >= _time(registration["captureUntil"]),
            "note": "Positive delta favors candidate. Paired match SE is descriptive and does not correct event/player dependence. No automatic adoption; the full walk-forward arbiter remains required."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    reg = commands.add_parser("register")
    reg.add_argument("root", type=Path)
    reg.add_argument("--tour", choices=("atp", "wta"), required=True)
    reg.add_argument("--hypothesis", required=True)
    reg.add_argument("--incumbent", type=Path, required=True)
    reg.add_argument("--candidate", type=Path, required=True)
    reg.add_argument("--days", type=int, default=30)
    reg.add_argument("--min-pairs", type=int, default=200)
    for name in ("capture", "grade"):
        command = commands.add_parser(name)
        command.add_argument("root", type=Path)
        command.add_argument("input", type=Path)
    args = vars(parser.parse_args())
    command = args.pop("command")
    root = args.pop("root")
    if command == "register":
        output = register(root, **args)
    else:
        payload = json.loads(args["input"].read_bytes())
        output = capture(root, payload) if command == "capture" else grade(root, payload)
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
