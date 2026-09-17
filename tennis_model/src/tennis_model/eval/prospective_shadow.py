"""Fixed WTA mixed-format pilot. No collection, scheduling or adoption side effects.

See tasks/research/2026-09-07-prospective-shadow-interface.md. Source adapters must
supply independent timing evidence; this runner cannot establish a provider's semantics.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from urllib.parse import urlsplit

import pandas as pd

from ..config import OUTPUT_DIR
from ..data.bracket_rounds import player_identity_key
from ..model import artifact as a
from ..model import shadow_artifact as sa
from ..model.dynamic_shadow import DynamicShadowPredictor
from ..model.predict import can_predict_match
from .prospective import ROLES, _bytes, _digest, _time, match_key
from .protocol import block_uncertainty

SCHEMA = "prospective-shadow-v1"
MAX_JSON = 8 * 1024 * 1024
POLICY = {"captureDays": 30, "settlementDays": 7, "minPairs": 200,
          "marginMinutes": 5, "scheduleAgeMinutes": 10, "bestOf": 3}
FILES = {"incumbent": ("incumbent.pkl", "incumbent.pkl.envelope"),
         "candidate": ("candidate.shadow",)}
TERMINAL = frozenset({"completed", "retired", "walkover", "withdrawn", "cancelled"})
CONTEXT = frozenset({"event", "as_of", "indoor", "tier_k", "round_order"})


def _now():
    return datetime.now(UTC)


def _raw(path, root, limit=MAX_JSON):
    return a._read_bounded(path, limit, trusted_root=root,
                           io_reason=a.PredictorArtifactReason.PAYLOAD_IO,
                           too_large_reason=a.PredictorArtifactReason.PAYLOAD_TOO_LARGE)


def _json(raw):
    return json.loads(raw, object_pairs_hook=a._reject_duplicate_keys,
                      parse_constant=a._reject_json_constant)


def _read(path, root):
    value = _json(_raw(path, root))
    if (type(value) is not dict or value.get("schema") != SCHEMA
            or value.get("sha256") != _digest({k: v for k, v in value.items() if k != "sha256"})):
        raise ValueError("receipt integrity or schema failure")
    return value


def _write_once(path, payload, root):
    raw = _bytes({**payload, "sha256": _digest(payload)})
    if len(raw) > MAX_JSON:
        raise ValueError("receipt exceeds size bound")
    with a._open_artifact_parent(path, trusted_root=root) as (directory, name):
        a._validate_write_destination(directory, name)
        temporary = ".receipt-" + uuid.uuid4().hex
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, name, src_dir_fd=directory, dst_dir_fd=directory,
                        follow_symlinks=False)
            except FileExistsError:
                _read(path, root)
                return False
            os.fsync(directory)
            return True
        finally:
            os.unlink(temporary, dir_fd=directory)


def _root(root, trusted_root):
    root = a._absolute_without_symlink_resolution(root)
    trusted = a._absolute_without_symlink_resolution(trusted_root)
    production = a._absolute_without_symlink_resolution(OUTPUT_DIR)
    if root == trusted or root.is_relative_to(production):
        raise ValueError("use an exclusive experiment directory below a private trusted root")
    a._trusted_root_for(root, trusted)
    return root


@contextmanager
def _locked(root, trusted_root):
    root = _root(root, trusted_root)
    # Created exclusively at registration; never replace a lock inode during retries.
    with a._open_artifact_parent(root / ".lock", trusted_root=trusted_root) as (directory, name):
        a._validate_write_destination(directory, name)
        before = a._directory_entry(directory, name)
        fd = os.open(name, os.O_RDWR | a._nofollow_flag(), dir_fd=directory)
        try:
            if (not a._same_file_identity(before, os.fstat(fd))
                    or not a._same_file_identity(before, a._directory_entry(directory, name))):
                raise ValueError("experiment lock changed")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield root
        finally:
            os.close(fd)


def _all(root, folder):
    with a._open_artifact_parent(root / folder / "entry", trusted_root=root) as (directory, _):
        names = sorted(os.listdir(directory))
    for name in names:
        if name.startswith(".receipt-"):
            continue  # Interrupted unpublished temporary files remain diagnostic only.
        if not re.fullmatch(r"[0-9a-f]{64}\.json", name):
            raise ValueError("unexpected evidence filename")
        value = _read(root / folder / name, root)
        yield name[:-5], value


def _contract():
    return {"python": a._python_identity(), "libraries": a._library_versions(),
            "incumbent": a.predictor_contract("wta"), "candidate": sa.shadow_contract()}


def _fingerprints(root, role):
    limit = a.MAX_PREDICTOR_BYTES + a.MAX_ENVELOPE_BYTES + len(sa.MAGIC) + 4
    return {name: hashlib.sha256(_raw(root / name, root, limit)).hexdigest() for name in FILES[role]}


def _load(root, provenance):
    return {"incumbent": a.load_predictor_artifact(root / FILES["incumbent"][0], "wta", trusted_root=root),
            "candidate": DynamicShadowPredictor.load(root / FILES["candidate"][0],
                                                       expected_provenance=provenance, trusted_root=root)}


def _models(root, registration):
    registered = _time(registration["registeredAt"])
    if (_time(registration["captureUntil"]) != registered + timedelta(days=30)
            or _time(registration["settleUntil"]) != registered + timedelta(days=37)
            or registration.get("evidenceKind") not in {"live", "synthetic-qa"}):
        raise ValueError("registered pilot interval or evidence kind changed")
    _sources(registration["sources"])
    if (registration.get("tour") != "wta" or registration.get("policy") != POLICY
            or _bytes(registration.get("contracts")) != _bytes(_contract())):
        raise ValueError("registered runner contract changed")
    provenance = sa.checked_provenance(registration["provenance"])
    for role in ROLES:
        expected_format = "production-pickle" if role == "incumbent" else sa.SHADOW_SCHEMA
        if registration["models"][role].get("format") != expected_format:
            raise ValueError("registered role format differs")
        if _fingerprints(root, role) != registration["models"][role]["files"]:
            raise ValueError(f"frozen {role} artifacts changed")
    models = _load(root, provenance)
    for role, model in models.items():
        record = registration["models"][role]
        if (model.artifact_id != record["artifactId"] or model.trained_at != record["trainedAt"]
                or _state_dates(model, registered) != record["stateThrough"]):
            raise ValueError("frozen model identity changed")
    return models


def _host(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port:
        raise ValueError("plain HTTPS source URL required")
    return parsed.hostname


def _sources(sources):
    if (type(sources) is not dict
            or set(sources) != {"scheduleHost", "resultHost", "timingEvidence", "cadence"}
            or any(type(v) is not str or not v.strip() or len(v) > 4096 for v in sources.values())):
        raise ValueError("explicit source hosts, timing evidence and cadence required")
    for key in ("scheduleHost", "resultHost"):
        if _host("https://" + sources[key]) != sources[key]:
            raise ValueError("canonical source host required")
    return sources


def _state_dates(model, registered):
    dates = {label: pd.Timestamp(state.last_date) for label, state in
             (("main", model.elo), ("lower", model.lower_elo))}
    if any(pd.isna(day) or day.tzinfo is not None or day > pd.Timestamp(registered).tz_localize(None)
           for day in dates.values()):
        raise ValueError("known state cutoffs before registration required")
    return {label: str(day) for label, day in dates.items()}


def register(root, *, trusted_root, incumbent, candidate, provenance, hypothesis, sources,
             evidence_kind="live"):
    """Copy exact validated artifact bytes; registration is the last published file."""
    root = _root(root, trusted_root)
    provenance = dict(sa.checked_provenance(provenance))
    sources = _sources(sources)
    if evidence_kind not in {"live", "synthetic-qa"} or not hypothesis.strip():
        raise ValueError("hypothesis and explicit evidence kind required")
    paths = [Path(incumbent), Path(candidate)]
    # Validate source roles before creating the experiment. Copies are validated again.
    a.load_predictor_artifact(paths[0], "wta", trusted_root=trusted_root)
    DynamicShadowPredictor.load(paths[1], expected_provenance=provenance, trusted_root=trusted_root)
    with a._open_artifact_parent(root, trusted_root=trusted_root) as (directory, name):
        os.mkdir(name, mode=0o700, dir_fd=directory)
        os.fsync(directory)
    for folder in ("receipts", "observations", "attempts", "results"):
        with a._open_artifact_parent(root / folder, trusted_root=root) as (directory, name):
            os.mkdir(name, mode=0o700, dir_fd=directory)
    with a._open_artifact_parent(root / ".lock", trusted_root=root) as (directory, name):
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
        os.close(fd)
        os.fsync(directory)
    with _locked(root, trusted_root):
        source_files = (paths[0], a.predictor_envelope_path(paths[0]), paths[1])
        for source, dest in zip(source_files, FILES["incumbent"] + FILES["candidate"], strict=True):
            raw = _raw(source, trusted_root, a.MAX_PREDICTOR_BYTES + a.MAX_ENVELOPE_BYTES + 100)
            a._atomic_write(root / dest, raw, trusted_root=root)
        models = _load(root, provenance)
        now = _now()
        if (models["incumbent"].artifact_id == models["candidate"].artifact_id
                or any(_time(m.trained_at) > now for m in models.values())):
            raise ValueError("distinct models trained before registration required")
        end = now + timedelta(days=POLICY["captureDays"])
        receipt = {"schema": SCHEMA, "tour": "wta", "hypothesis": hypothesis.strip(),
                   "evidenceKind": evidence_kind, "sources": sources, "policy": POLICY,
                   "registeredAt": now.isoformat(), "captureUntil": end.isoformat(),
                   "settleUntil": (end + timedelta(days=POLICY["settlementDays"])).isoformat(),
                   "provenance": provenance, "contracts": _contract(),
                   "models": {role: {"format": "production-pickle" if role == "incumbent" else sa.SHADOW_SCHEMA,
                                     "artifactId": model.artifact_id, "trainedAt": model.trained_at,
                                     "stateThrough": _state_dates(model, now),
                                     "files": _fingerprints(root, role)} for role, model in models.items()}}
        _write_once(root / "registration.json", receipt, root)
        return _read(root / "registration.json", root)


def _batch(batch, registration, kind, now):
    raw = _bytes(batch)
    if len(raw) > MAX_JSON // 2:
        raise ValueError("bounded source batch required")
    batch = _json(raw)  # Snapshot caller-owned objects.
    observed = _time(batch["observedAt"])
    if (batch.get("tour") != "wta" or _host(batch.get("sourceUrl", "")) != registration["sources"][kind + "Host"]):
        raise ValueError("source tour or registered host differs")
    if not _time(registration["registeredAt"]) <= observed <= now:
        raise ValueError("source observation must be after registration and not in the future")
    rows = batch.get("matches")
    if type(rows) is not list or len(rows) > 2048 or any(type(row) is not dict for row in rows):
        raise ValueError("bounded matches array required")
    keys = [match_key(row, "wta") for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate matchup in source observation")
    return batch, observed


def _context(row):
    try:
        start = _time(row["earliestStartAt"])
        context = row.get("context", {})
        if (type(context) is not dict or set(context) != CONTEXT
                or row.get("surface") not in ("Hard", "Clay", "Grass")
                or type(row.get("bestOf")) is not int or row["bestOf"] != 3
                or not isinstance(context["event"], str) or not context["event"].strip()
                or type(context["indoor"]) is not bool
                or type(context["round_order"]) is not int or not 0 <= context["round_order"] <= 10
                or type(context["tier_k"]) not in (float, int)
                or not math.isfinite(context["tier_k"]) or context["tier_k"] <= 0
                or _time(context["as_of"]) != start or start.year != row["season"]):
            raise ValueError("invalid context")
        return start, context
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


def capture(root, schedule, *, trusted_root):
    with _locked(root, trusted_root) as root:
        registration = _read(root / "registration.json", root)
        models = _models(root, registration)
        now = _now()
        end = _time(registration["captureUntil"])
        if not _time(registration["registeredAt"]) <= now < end:
            raise ValueError("outside registered capture horizon")
        schedule, observed = _batch(schedule, registration, "schedule", now)
        if now - observed > timedelta(minutes=10):
            raise ValueError("schedule observation must be from the last ten minutes")
        observation = {"schema": SCHEMA, "registration": registration["sha256"],
                       "acceptedAt": now.isoformat(), "schedule": schedule}
        oid = _digest(observation)
        _write_once(root / "observations" / f"{oid}.json", observation, root)
        decisions = {}
        for row in schedule["matches"]:
            key = match_key(row, "wta")
            destination = root / "receipts" / f"{key}.json"
            if a._lexists_secure(destination, trusted_root=root):
                _forecast(root, key, _read(destination, root), registration)
                decisions[key] = "alreadyCaptured"
                continue
            if row.get("status") != "scheduled":
                decisions[key] = "notScheduled"
                continue
            parsed = _context(row)
            if parsed is None:
                decisions[key] = "missingContext"
                continue
            start, context = parsed
            if start >= end:
                decisions[key] = "outsideMatchHorizon"
                continue
            if start <= _now() + timedelta(minutes=5):
                decisions[key] = "tooLateOrUncertain"
                continue
            if not all(can_predict_match(m, row["playerA"], row["playerB"]) for m in models.values()):
                decisions[key] = "unpriced"
                continue
            probabilities = {role: float(model.prediction_components(
                row["playerA"], row["playerB"], surface=row["surface"], best_of=3, **context)["combiner"])
                for role, model in models.items()}
            if not all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values()):
                raise ValueError("model produced invalid probability")
            captured = _now()
            if (captured < now or captured + timedelta(minutes=5) >= start or captured >= end
                    or captured - observed > timedelta(minutes=10)):
                decisions[key] = "tooLateOrUncertain"
                continue
            receipt = {"schema": SCHEMA, "registration": registration["sha256"], "matchKey": key,
                       "observation": oid, "match": row, "capturedAt": captured.isoformat(),
                       "probabilities": probabilities}
            _write_once(destination, receipt, root)
            decisions[key] = "captured"
        attempt = {"schema": SCHEMA, "registration": registration["sha256"], "observation": oid,
                   "finishedAt": _now().isoformat(), "decisions": decisions}
        _write_once(root / "attempts" / f"{_digest(attempt)}.json", attempt, root)
        return dict(Counter(decisions.values()))


def _linked(root, folder, identity, registration):
    if type(identity) is not str or not re.fullmatch(r"[0-9a-f]{64}", identity):
        raise ValueError("invalid evidence identity")
    value = _read(root / folder / f"{identity}.json", root)
    if value["sha256"] != identity or value["registration"] != registration["sha256"]:
        raise ValueError("evidence belongs to a different experiment")
    return value


def _forecast(root, key, receipt, registration):
    row = receipt["match"]
    if (key != match_key(row, "wta") or key != receipt["matchKey"]
            or receipt["registration"] != registration["sha256"]):
        raise ValueError("forecast identity differs")
    observation = _linked(root, "observations", receipt["observation"], registration)
    accepted = _time(observation["acceptedAt"])
    batch, observed = _batch(observation["schedule"], registration, "schedule", accepted)
    captured = _time(receipt["capturedAt"])
    parsed = _context(row)
    if (row not in batch["matches"] or row.get("status") != "scheduled" or parsed is None
            or not observed <= accepted <= captured < _time(registration["captureUntil"])
            or captured - observed > timedelta(minutes=10)
            or not captured + timedelta(minutes=5) < parsed[0] < _time(registration["captureUntil"])
            or set(receipt["probabilities"]) != set(ROLES)
            or any(type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1
                   for p in receipt["probabilities"].values())):
        raise ValueError("forecast lost source, context, probability or timing proof")
    return row


def grade(root, results, *, trusted_root):
    with _locked(root, trusted_root) as root:
        registration = _read(root / "registration.json", root)
        _models(root, registration)
        now = _now()
        if now >= _time(registration["settleUntil"]):
            raise ValueError("settlement intake closed; use report")
        results, _ = _batch(results, registration, "result", now)
        accepted = _now()
        if not now <= accepted < _time(registration["settleUntil"]):
            raise ValueError("settlement intake closed or clock moved backward")
        evidence = {"schema": SCHEMA, "registration": registration["sha256"],
                    "acceptedAt": accepted.isoformat(), "results": results}
        # Retry identity excludes local intake time; the first accepted observation wins.
        identity = _digest({"registration": registration["sha256"], "results": results})
        path = root / "results" / f"{identity}.json"
        _write_once(path, evidence, root)
        return _report(root, registration, accepted)


def _outcome(evidence):
    terminal = [(row, batch, identity) for row, batch, identity in evidence if row.get("status") in TERMINAL]
    if not terminal:
        return None, "pending"
    signatures = {row["status"] for row, _, _ in terminal}
    for field in ("winner", "actualStartedAt", "finishedAt"):
        values = set()
        for row, _, _ in terminal:
            if row.get(field):
                try:
                    value = player_identity_key(row[field]) if field == "winner" else _time(row[field]).isoformat()
                except (ValueError, TypeError, AttributeError):
                    return None, "invalidResultTiming"
                values.add(value)
        if len(values) > 1:
            return None, "conflictingResults"
    if len(signatures) > 1:
        return None, "conflictingResults"
    status = next(iter(signatures))
    if status != "completed":
        return None, status
    # Never combine partial timing claims from separate observations into invented proof.
    complete = [item for item in terminal if all(item[0].get(f) for f in ("winner", "actualStartedAt", "finishedAt"))]
    if not complete:
        return None, "missingActualTiming"
    return sorted(complete, key=lambda item: (_time(item[1]["observedAt"]), item[2]))[0], None


def _report(root, registration, now):
    end = _time(registration["settleUntil"])
    index = defaultdict(list)
    result_ids = []
    for identity, value in _all(root, "results"):
        accepted = _time(value["acceptedAt"])
        batch, _ = _batch(value["results"], registration, "result", accepted)
        if (value["registration"] != registration["sha256"] or not accepted < end or accepted > now
                or identity != _digest({"registration": registration["sha256"], "results": batch})):
            raise ValueError("invalid accumulated result evidence")
        result_ids.append(identity)
        for row in batch["matches"]:
            index[match_key(row, "wta")].append((row, batch, identity))
    observations = {identity: value for identity, value in _all(root, "observations")}
    for identity, value in observations.items():
        _linked(root, "observations", identity, registration)
        accepted = _time(value["acceptedAt"])
        _, observed = _batch(value["schedule"], registration, "schedule", accepted)
        if not accepted < _time(registration["captureUntil"]) or accepted > now or accepted - observed > timedelta(minutes=10):
            raise ValueError("invalid schedule evidence time")
    capture_counts, attempts, attempted_observations = Counter(), 0, set()
    forecasts = dict(_all(root, "receipts"))
    for identity, attempt in _all(root, "attempts"):
        if attempt["sha256"] != identity or attempt["registration"] != registration["sha256"]:
            raise ValueError("capture summary identity differs")
        observation = _linked(root, "observations", attempt["observation"], registration)
        if set(attempt["decisions"]) != {match_key(r, "wta") for r in observation["schedule"]["matches"]}:
            raise ValueError("capture summary lost source membership")
        for key, decision in attempt["decisions"].items():
            if decision in {"captured", "alreadyCaptured"} and key not in forecasts:
                raise ValueError("captured forecast receipt missing")
        capture_counts.update(attempt["decisions"].values())
        attempted_observations.add(attempt["observation"])
        attempts += 1
    excluded, pending, rows = Counter(), 0, []
    for key, receipt in forecasts.items():
        original = _forecast(root, key, receipt, registration)
        if _time(receipt["capturedAt"]) > now:
            raise ValueError("forecast timestamp is in the future")
        outcome, reason = _outcome(index[key])
        if reason == "pending":
            pending += 1
            continue
        if reason:
            excluded[reason] += 1
            continue
        result, batch, result_id = outcome
        started, finished = _time(result["actualStartedAt"]), _time(result["finishedAt"])
        captured, earliest = _time(receipt["capturedAt"]), _time(original["earliestStartAt"])
        if not captured + timedelta(minutes=5) < earliest <= started <= finished <= _time(batch["observedAt"]):
            excluded["timingNotProved"] += 1
            continue
        winner = player_identity_key(result["winner"])
        if winner not in {player_identity_key(original["playerA"]), player_identity_key(original["playerB"])}:
            excluded["winnerMismatch"] += 1
            continue
        a_won = winner == player_identity_key(original["playerA"])
        scores = {}
        for role, p in receipt["probabilities"].items():
            pw = p if a_won else 1-p
            scores[role] = {"logloss": -math.log(max(1e-12, min(1-1e-12, pw))),
                            "brier": (1-pw)**2, "accuracy": .5 if p == .5 else float((p > .5) == a_won)}
        rows.append({"matchKey": key, "forecast": receipt["sha256"], "resultEvidence": result_id,
                     "week": str(pd.Timestamp(started).tz_localize(None).to_period("W-SUN")),
                     "event": f'{original["espnId"]}:{original["season"]}', "scores": scores})
    paired = {}
    for metric in ("logloss", "brier", "accuracy"):
        deltas = [r["scores"]["incumbent"][metric] - r["scores"]["candidate"][metric] for r in rows]
        paired[metric] = {**{role: mean(r["scores"][role][metric] for r in rows) if rows else None for role in ROLES},
                          "delta": mean(deltas) if deltas else None,
                          "se": stdev(deltas)/math.sqrt(len(deltas)) if len(deltas) > 1 else None,
                          "blocks": {label: block_uncertainty(deltas, [r[label] for r in rows])
                                     if rows else {"n": 0, "status": "no-pairs"} for label in ("week", "event")}}
    as_of = min(now, end)
    report = {"schema": SCHEMA, "registration": registration["sha256"], "evidenceKind": registration["evidenceKind"],
              "asOf": as_of.isoformat(), "final": now >= end, "captureClosed": now >= _time(registration["captureUntil"]),
              "targetPairs": POLICY["minPairs"], "targetReached": len(rows) >= POLICY["minPairs"],
              "coverage": "adequate-count" if len(rows) >= POLICY["minPairs"] else "insufficient-pilot-coverage",
              "captured": len(forecasts), "graded": len(rows), "pending": pending, "excluded": dict(excluded),
              "observations": len(observations), "captureAttempts": attempts, "captureCounts": dict(capture_counts),
              "unfinishedObservations": len(set(observations) - attempted_observations),
              "resultBatches": len(result_ids), "resultEvidence": result_ids, "paired": paired, "pairs": rows,
              "stalenessDays": {role: {"trained": (as_of-_time(model["trainedAt"])).total_seconds()/86400,
                                        **{label: (pd.Timestamp(as_of).tz_localize(None)-pd.Timestamp(day)).total_seconds()/86400
                                           for label, day in model["stateThrough"].items()}}
                                for role, model in registration["models"].items()},
              "note": "All deltas are incumbent minus candidate: positive favors candidate for losses, incumbent for accuracy. Fixed horizon; count is adequacy only. Week/event resampling does not remove all player dependence. No automatic adoption. Synthetic QA is not performance evidence."}
    if report["final"]:
        _write_once(root / "endpoint.json", report, root)
        saved = _read(root / "endpoint.json", root)
        if saved["sha256"] != _digest(report):
            raise ValueError("endpoint evidence changed")
        return saved
    return report


def report(root, *, trusted_root):
    with _locked(root, trusted_root) as root:
        registration = _read(root / "registration.json", root)
        _models(root, registration)
        return _report(root, registration, _now())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    reg = commands.add_parser("register")
    reg.add_argument("root", type=Path)
    for field in ("incumbent", "candidate", "provenance", "sources"):
        reg.add_argument("--" + field, required=True, type=Path)
    reg.add_argument("--hypothesis", required=True)
    reg.add_argument("--evidence-kind", choices=("live", "synthetic-qa"), default="live")
    for name in ("capture", "grade", "report"):
        command = commands.add_parser(name)
        command.add_argument("root", type=Path)
        if name != "report":
            command.add_argument("input", type=Path)
    args = vars(parser.parse_args())
    command = args.pop("command")
    if command == "register":
        for key in ("provenance", "sources"):
            args[key] = _json(_raw(args[key], args["trusted_root"]))
        output = register(**args)
    elif command == "report":
        output = report(**args)
    else:
        payload = _json(_raw(args.pop("input"), args["trusted_root"]))
        output = (capture if command == "capture" else grade)(args.pop("root"), payload, **args)
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
