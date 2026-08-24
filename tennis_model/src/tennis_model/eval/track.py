"""Forecast tracking: log point-in-time predictions, grade them against results.

The rest of the engine is overwrite-only — today's JSON replaces yesterday's, nothing
is kept. This module adds the one thing needed for forecast *validation* (as opposed to
live forecasting): an append-only log of predictions captured BEFORE matches resolve,
plus a grader that scores them once the actual results arrive.

  data/forecast_log/<tour>.jsonl   the log — the single source of truth that PERSISTS
                                   across daily runs (committed back by the workflow).
  data/output/<tour>/track.json    derived scorecard — regenerated every run, mirrored
                                   to the web app like every other artifact.

Four line types in the log:
  match       one upcoming matchup + P(playerA wins), logged once at first sighting so
              the probability is a genuine pre-result forecast (the model has not yet
              trained on the outcome).
  match_snapshot  an hourly, idempotent pending-match snapshot. The first-sighting record
              remains the grading contract; these snapshots power forecast movement and
              let market comparisons select the model state available at the quote time.
  match_identity_bridge  append-only provenance for a bracket-proven round correction, so
              a blocked run's first sighting stays canonical after that bracket ages out.
  tournament  a daily snapshot of an in-progress event's title odds (odds evolve as the
              draw thins, so we keep one snapshot per event per day).

Grading joins logged matches to completed results by player-pair within a short date
window (a given pair rarely plays twice in three weeks), so it is robust to ESPN's
sponsor event names vs the archive's clean names. Unresolved logs stay `pending`.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .. import __version__
from ..config import (
    DATA_DIR,
    DRIFT_MIN_EXCESS,
    DRIFT_MIN_N,
    DRIFT_TRIGGER_K,
    DRIFT_WINDOW_DAYS,
    SURFACES,
    output_dir,
)
from ..data.bracket_rounds import (
    build_bracket_round_index,
    player_identity_key,
    unique_bracket_round,
)
from ..data.results import _name_key as nkey
from ..model.upcoming import enrich_upcoming, load_upcoming
from ..timing import timed
from .metrics import EPS, calibration_table, score

FORECAST_DIR = DATA_DIR / "forecast_log"
JOIN_WINDOW_DAYS = 21          # max gap between forecast and the result it grades
RECENT_N = 60                  # graded decisions surfaced for the UI table
PERFORMANCE_N = 10             # genuine first-sighting decisions in a player's scorecard
MATCH_ID_VERSION = "v2"
_KNOCKOUT_ROUNDS = frozenset({"R128", "R64", "R32", "R16", "QF", "SF", "F"})


# ---------------------------------------------------------------------------
# Keys / small helpers
# ---------------------------------------------------------------------------
def _norm_event(name: object) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())[:18]


def _season(*candidates) -> int:
    for c in candidates:
        s = str(c) if c is not None else ""
        if len(s) >= 4 and s[:4].isdigit():
            return int(s[:4])
    return datetime.now(UTC).year


def _clean_id(value: object) -> str | None:
    """Normalize registry IDs without turning pandas' missing values into real IDs."""
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    return value if value and value.lower() not in {"nan", "none", "null"} else None


def match_identity(r: dict) -> str:
    """Versioned, orientation-safe identity shared by forecast-log consumers.

    ESPN's event registry ID is the event key whenever it exists. The normalized display
    name is only a legacy fallback for old/non-ESPN schedules; it must never displace a
    real ID because sponsor titles can change while an event is live.
    """
    a, b = sorted((nkey(r["playerA"]), nkey(r["playerB"])))
    event_id = _clean_id(r.get("espnId", r.get("espn_id")))
    event = f"espn:{event_id}" if event_id else f"legacy:{_norm_event(r.get('event'))}"
    season = _season(r.get("season"), r.get("date"), r.get("as_of"))
    rnd = re.sub(r"[^A-Z0-9]", "", str(r.get("round") or "").upper()) or "?"
    return f"{MATCH_ID_VERSION}|{event}|{season}|{rnd}|{a}|{b}"


def _match_key(r: dict) -> str:
    """Read an explicit ID when present; derive it for legacy append-only records."""
    return str(r.get("match_id") or match_identity(r))


def _bridge_evidence_key(r: dict) -> tuple[str, str, int, str]:
    """Non-name evidence used only to migrate pre-ID append-only records.

    Event display names are deliberately absent. A bridge needs the same real players,
    season, and round, then a unique nearby ESPN event ID before it is accepted.
    """
    a, b = sorted((nkey(r.get("playerA")), nkey(r.get("playerB"))))
    season = _season(r.get("season"), r.get("date"), r.get("as_of"))
    rnd = re.sub(r"[^A-Z0-9]", "", str(r.get("round") or "").upper()) or "?"
    return a, b, season, rnd


def _legacy_match_bridges(records: list[dict]) -> dict[str, str]:
    """Map an unambiguous pre-v2 match key to its later registry-backed identity.

    The old log predates ``espnId``. We retain its immutable first forecast only when
    exactly one legacy first-sighting and one distinct explicit event ID share the
    player/season/round evidence inside the grading window. Ambiguity fails closed.
    """
    legacy: dict[tuple[str, str, int, str], list[dict]] = defaultdict(list)
    explicit: dict[tuple[str, str, int, str], list[dict]] = defaultdict(list)
    for rec in records:
        if rec.get("type") not in ("match", "match_snapshot"):
            continue
        evidence = _bridge_evidence_key(rec)
        event_id = _clean_id(rec.get("espnId", rec.get("espn_id")))
        if event_id:
            explicit[evidence].append(rec)
        elif rec.get("type") == "match" and not rec.get("match_id"):
            legacy[evidence].append(rec)

    bridges: dict[str, str] = {}
    for evidence, old_matches in legacy.items():
        candidates = explicit.get(evidence) or []
        event_ids = {
            _clean_id(r.get("espnId", r.get("espn_id"))) for r in candidates
        } - {None}
        if len(old_matches) != 1 or len(event_ids) != 1:
            continue
        old = old_matches[0]
        try:
            old_time = pd.Timestamp(old.get("as_of"))
            candidate_times = [pd.Timestamp(r.get("as_of")) for r in candidates]
            if old_time.tzinfo is not None:
                old_time = old_time.tz_convert(None)
            candidate_times = [
                t.tz_convert(None) if t.tzinfo is not None else t for t in candidate_times
            ]
            delta_days = (min(candidate_times) - old_time).total_seconds() / 86400
        except (TypeError, ValueError):
            continue
        if not 0 <= delta_days <= JOIN_WINDOW_DAYS:
            continue
        explicit_id = match_identity(candidates[0])
        bridges[_match_key(old)] = explicit_id
    return bridges


def _canonical_bracket_match_identity(r: dict, canonical_round: str) -> str:
    """Build the corrected ID with the same explicit aliases as bracket matching."""
    a, b = sorted((player_identity_key(r.get("playerA")),
                   player_identity_key(r.get("playerB"))))
    event_id = _clean_id(r.get("espnId", r.get("espn_id")))
    season = _season(r.get("season"), r.get("date"), r.get("as_of"))
    rnd = re.sub(r"[^A-Z0-9]", "", canonical_round.upper()) or "?"
    return f"{MATCH_ID_VERSION}|espn:{event_id}|{season}|{rnd}|{a}|{b}"


def _bracket_round_bridges(tour: str, records: list[dict]) -> dict[str, str]:
    """Canonicalize cached ESPN identities only from one exact bracket matchup.

    A failed refresh can append an immutable first-sighting under ESPN's wrong round
    before the independent deploy gate blocks publication.  The next refresh must keep
    that forecast, not append a second decision under the corrected round.  Stable event
    id + exact canonical pair + one knockout bracket round is the complete bridge; missing
    or ambiguous evidence deliberately leaves the append-only identities separate.
    """
    try:
        index = build_bracket_round_index(
            _read_json(output_dir(tour) / "brackets.json") or [])
    except (OSError, TypeError, ValueError):
        return {}

    bridges: dict[str, str] = {}
    for rec in records:
        if rec.get("type") not in ("match", "match_snapshot"):
            continue
        event_id = _clean_id(rec.get("espnId", rec.get("espn_id")))
        canonical_round = unique_bracket_round(
            index, event_id, rec.get("playerA"), rec.get("playerB"))
        if canonical_round not in _KNOCKOUT_ROUNDS:
            continue
        canonical_id = _canonical_bracket_match_identity(rec, canonical_round)
        old_id = _match_key(rec)
        if old_id != canonical_id and _valid_persisted_round_bridge(old_id, canonical_id):
            bridges[old_id] = canonical_id
    return bridges


def _valid_persisted_round_bridge(source_id: object, target_id: object) -> bool:
    """A durable bridge may change only one knockout round in one ESPN identity."""
    if not isinstance(source_id, str) or not isinstance(target_id, str):
        return False
    source = source_id.split("|")
    target = target_id.split("|")
    if len(source) != 6 or len(target) != 6:
        return False
    if source[0] != MATCH_ID_VERSION or target[0] != MATCH_ID_VERSION:
        return False
    if not source[1].startswith("espn:") or source[1] == "espn:":
        return False
    source_pair = sorted(player_identity_key(name) for name in source[4:])
    target_pair = sorted(player_identity_key(name) for name in target[4:])
    same_match = source[:3] == target[:3] and source_pair == target_pair
    return (
        same_match
        and len(set(target_pair)) == 2
        and all(target_pair)
        and target[4:] == target_pair
        and source[3] != target[3]
        and source[3] in _KNOCKOUT_ROUNDS
        and target[3] in _KNOCKOUT_ROUNDS
    )


def _persisted_round_bridge_candidates(records: list[dict]) -> dict[str, set[str]]:
    """Read structurally valid bracket-backed markers without resolving conflicts."""
    candidates: dict[str, set[str]] = defaultdict(set)
    for rec in records:
        if rec.get("type") != "match_identity_bridge":
            continue
        if rec.get("bridge_version") != "bracket-round-v1":
            continue
        if rec.get("evidence") != "unique_knockout_bracket_round":
            continue
        source_id = rec.get("from_match_id")
        target_id = rec.get("to_match_id")
        if _valid_persisted_round_bridge(source_id, target_id):
            candidates[source_id].add(target_id)
    return dict(candidates)


def _persisted_round_bridges(records: list[dict]) -> dict[str, str]:
    """Consume prior bracket-backed markers, rejecting any conflicting mapping."""
    candidates = _persisted_round_bridge_candidates(records)
    return {
        source_id: next(iter(targets))
        for source_id, targets in candidates.items()
        if len(targets) == 1
    }


def _merge_round_bridges(*sources: dict[str, str]) -> dict[str, str]:
    """Require stored and current bracket evidence to agree when both exist."""
    candidates: dict[str, set[str]] = defaultdict(set)
    for source in sources:
        for source_id, target_id in source.items():
            candidates[source_id].add(target_id)
    return {
        source_id: next(iter(targets))
        for source_id, targets in candidates.items()
        if len(targets) == 1
    }


def _reconciled_round_bridges(
    records: list[dict], current: dict[str, str],
) -> dict[str, str]:
    """Resolve durable and current evidence, failing closed on stored corruption."""
    persisted_candidates = _persisted_round_bridge_candidates(records)
    conflicts = {
        source_id for source_id, targets in persisted_candidates.items() if len(targets) != 1
    }
    merged = _merge_round_bridges(_persisted_round_bridges(records), current)
    return {
        source_id: target_id
        for source_id, target_id in merged.items()
        if source_id not in conflicts
    }


def _forecast_match_bridges(tour: str, records: list[dict]) -> dict[str, str]:
    """Compose pre-ID migration and durable/current bracket reconciliation."""
    bridges = _legacy_match_bridges(records)
    current = _bracket_round_bridges(tour, records)
    bridges.update(_reconciled_round_bridges(records, current))
    return bridges


def _effective_match_id(r: dict, bridges: dict[str, str]) -> str:
    match_id = _match_key(r)
    seen: set[str] = set()
    while match_id in bridges and match_id not in seen:
        seen.add(match_id)
        next_id = bridges[match_id]
        if next_id == match_id:
            break
        match_id = next_id
    return match_id


def _event_id_from_match_id(match_id: str) -> str | None:
    prefix = f"{MATCH_ID_VERSION}|espn:"
    if not match_id.startswith(prefix):
        return None
    return match_id[len(prefix):].split("|", 1)[0] or None


def _round_from_match_id(match_id: str) -> str | None:
    parts = match_id.split("|", 5)
    if len(parts) < 4 or parts[0] != MATCH_ID_VERSION:
        return None
    return parts[3] or None


def _new_identity_bridge_records(
    tour: str,
    records: list[dict],
    current: dict[str, str],
    accepted: dict[str, str],
    as_of: str,
) -> list[dict]:
    """Persist newly accepted round bridges without rewriting old forecast lines."""
    source_records: dict[str, dict] = {}
    for rec in sorted(
        (r for r in records if r.get("type") in ("match", "match_snapshot")),
        key=lambda r: str(r.get("as_of") or ""),
    ):
        source_records.setdefault(_match_key(rec), rec)

    stored = _persisted_round_bridge_candidates(records)
    new = []
    for source_id, target_id in sorted(current.items()):
        source = source_records.get(source_id)
        if source is None or accepted.get(source_id) != target_id:
            continue
        if target_id in stored.get(source_id, set()):
            continue
        new.append({
            "type": "match_identity_bridge",
            "bridge_version": "bracket-round-v1",
            "evidence": "unique_knockout_bracket_round",
            "as_of": as_of,
            "tour": tour,
            "event": source.get("event"),
            "espnId": _event_id_from_match_id(target_id),
            "season": _season(source.get("season"), source.get("as_of")),
            "playerA": source.get("playerA"),
            "playerB": source.get("playerB"),
            "from_round": _round_from_match_id(source_id),
            "round": _round_from_match_id(target_id),
            "from_match_id": source_id,
            "to_match_id": target_id,
        })
    return new


def _tourn_key(r: dict) -> str:
    return f"{_norm_event(r.get('event'))}|{r.get('season')}|{str(r.get('as_of'))[:10]}"


def _snapshot_key(r: dict, bridges: dict[str, str] | None = None) -> str:
    """One snapshot per matchup per UTC hour, even when a job is retried."""
    match_id = _effective_match_id(r, bridges or {})
    return f"{match_id}|{str(r.get('as_of'))[:13]}"


def _oriented_probability(rec: dict, player_a: object) -> float | None:
    """P(player_a wins) regardless of the orientation used by a stored record."""
    try:
        p = float(rec["p"])
    except (KeyError, TypeError, ValueError):
        return None
    key = player_identity_key(player_a)
    if key == player_identity_key(rec.get("playerA")):
        return p
    if key == player_identity_key(rec.get("playerB")):
        return 1.0 - p
    return None


def _oriented_components(rec: dict, player_a: object) -> dict | None:
    components = rec.get("components")
    if not isinstance(components, dict):
        return None
    flip = player_identity_key(player_a) == player_identity_key(rec.get("playerB"))
    out = {}
    for name, value in components.items():
        if isinstance(value, (int, float)) and np.isfinite(value):
            out[name] = round(1.0 - float(value) if flip else float(value), 4)
    return out or None


def _oriented_evidence(rec: dict, player_a: object) -> dict | None:
    """Return recorded evidence with its signed sensitivities oriented to ``player_a``."""
    evidence = rec.get("evidence")
    if not isinstance(evidence, dict):
        return None
    # JSON round-trip is an inexpensive defensive copy for this compact payload and keeps
    # the append-only record immutable while a reversed feed orientation is normalized.
    out = json.loads(json.dumps(evidence))
    if player_identity_key(player_a) != player_identity_key(rec.get("playerB")):
        return out
    out["playerA"], out["playerB"] = out.get("playerB"), out.get("playerA")
    if isinstance(out.get("probabilityA"), (int, float)):
        out["probabilityA"] = round(1.0 - float(out["probabilityA"]), 4)
    for signal in out.get("signals") or []:
        if isinstance(signal.get("impactPp"), (int, float)):
            signal["impactPp"] = round(-float(signal["impactPp"]), 2)
        facts = signal.get("facts") or {}
        for left, right in (
            ("a", "b"), ("form90A", "form90B"),
            ("recentWinRateA", "recentWinRateB"),
            ("daysSinceA", "daysSinceB"), ("workloadA", "workloadB"),
            ("winsA", "winsB"), ("surfaceWinsA", "surfaceWinsB"),
            ("playerAHome", "playerBHome"),
        ):
            if left in facts or right in facts:
                facts[left], facts[right] = facts.get(right), facts.get(left)
        if isinstance(facts.get("pointProbabilityA"), (int, float)):
            facts["pointProbabilityA"] = round(1.0 - float(facts["pointProbabilityA"]), 4)
        for signed in ("gap", "serveEdge", "returnEdge", "diff"):
            if isinstance(facts.get(signed), (int, float)):
                facts[signed] = -facts[signed]
        for contrast in facts.get("contrasts") or []:
            contrast["a"], contrast["b"] = contrast.get("b"), contrast.get("a")
            if isinstance(contrast.get("diff"), (int, float)):
                contrast["diff"] = -contrast["diff"]
    return out


def _history_index(records: list[dict], bridges: dict[str, str] | None = None) -> dict[str, list[dict]]:
    bridges = bridges or _legacy_match_bridges(records)
    history: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        if rec.get("type") in ("match", "match_snapshot") and rec.get("p") is not None:
            history[_effective_match_id(rec, bridges)].append(rec)
    return history


def _forecast_history(records: list[dict], player_a: object,
                      current: float | None = None) -> dict | None:
    """Normalize one match's append-only records into a de-duplicated timeline."""
    if not records:
        return None
    records = sorted(records, key=lambda r: str(r.get("as_of") or ""))
    first = next((r for r in records if r.get("type") == "match"), records[0])
    initial = _oriented_probability(first, player_a)
    if initial is None:
        return None

    # The first run writes a `match` provenance row and a same-hour snapshot. They are
    # one observation in the graph, not two apparent model changes.
    buckets: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        buckets[str(rec.get("as_of") or "")[:13]].append(rec)
    timeline = []
    for bucket in sorted(buckets):
        recs = buckets[bucket]
        rec = recs[-1]
        p = _oriented_probability(rec, player_a)
        if p is None:
            continue
        item = {
            "asOf": rec.get("as_of"),
            "p": round(p, 4),
            "modelVersion": rec.get("model_version"),
            "firstSighting": any(r is first for r in recs),
        }
        components = _oriented_components(rec, player_a)
        if components:
            item["components"] = components
        evidence = _oriented_evidence(rec, player_a)
        if evidence:
            item["evidence"] = evidence
        timeline.append(item)

    now = float(current) if current is not None else (
        float(timeline[-1]["p"]) if timeline else initial)
    return {
        "first": round(initial, 4),
        "current": round(now, 4),
        "delta": round(now - initial, 4),
        "firstAsOf": first.get("as_of"),
        "latestAsOf": timeline[-1].get("asOf") if timeline else first.get("as_of"),
        "snapshots": len(timeline),
        "timeline": timeline,
    }


def _read_log(path, *, status: dict | None = None) -> list:
    if not path.exists():
        return []
    out = []
    malformed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                malformed += 1
                continue
    if status is not None and malformed:
        # The same log is read during append and grade. Keep the actual number of bad
        # persisted lines rather than double-counting both passes.
        status["malformedLines"] = max(status.get("malformedLines", 0), malformed)
    return out


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log_forecasts(tour: str, predictor, df: pd.DataFrame,
                  upcoming: pd.DataFrame | None, as_of: str, *,
                  enriched: list[dict] | None = None,
                  status: dict | None = None) -> int:
    """Append new match + tournament forecasts to the log. Returns # records added.

    Idempotent: a matchup is logged once (first sighting locks the forecast), and a
    tournament once per day — so re-running the pipeline never duplicates lines.
    """
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    path = FORECAST_DIR / f"{tour}.jsonl"
    existing = _read_log(path, status=status)
    # match forecasts: one locked P(playerA wins) per scheduled matchup (first sighting).
    # Name-resolution / surface inference / pricing live in model.upcoming.enrich_upcoming,
    # shared with the web schedule board so the two can never disagree on a matchup.
    if enriched is None:
        enriched = enrich_upcoming(predictor, df, upcoming, tour)
    bases = []
    for row in enriched:
        base = {
            "as_of": as_of, "tour": tour,
            "event": row["event"], "espnId": row.get("espnId"), "round": row["round"],
            "surface": row["surface"], "best_of": row["best_of"],
            "season": _season(row["date"], as_of),
            "playerA": row["playerA"], "playerB": row["playerB"],
            "model_version": __version__, "p": round(row["pA"], 4),
            "components": row.get("components"),
            "evidence": row.get("evidence"),
        }
        base["match_id"] = match_identity(base)
        bases.append(base)

    # Include today's registry-backed probes when deriving the one-time legacy bridge.
    # This prevents the first run that learns an espnId from appending a second immutable
    # first-sighting for the same real match.
    probes = [{**base, "type": "match_snapshot"} for base in bases]
    evidence_records = existing + probes
    current_round_bridges = _bracket_round_bridges(tour, evidence_records)
    accepted_round_bridges = _reconciled_round_bridges(
        evidence_records, current_round_bridges)
    bridges = _legacy_match_bridges(evidence_records)
    bridges.update(accepted_round_bridges)
    seen_match = {
        _effective_match_id(r, bridges) for r in existing if r.get("type") == "match"
    }
    seen_snap = {
        _snapshot_key(r, bridges) for r in existing if r.get("type") == "match_snapshot"
    }
    seen_tourn = {_tourn_key(r) for r in existing if r.get("type") == "tournament"}

    new: list = _new_identity_bridge_records(
        tour, existing, current_round_bridges, accepted_round_bridges, as_of)
    for base in bases:
        rec = {
            **base,
            "type": "match", "as_of": as_of, "tour": tour,
        }
        k = _effective_match_id(rec, bridges)
        if k not in seen_match:
            seen_match.add(k)
            new.append(rec)
        snap = {**base, "type": "match_snapshot"}
        sk = _snapshot_key(snap, bridges)
        if sk not in seen_snap:
            seen_snap.add(sk)
            new.append(snap)

    # tournament snapshots: reuse the title odds already computed for tournaments.json
    # (status == "live" only — completed events have no pre-result odds to log).
    tournaments = _read_json(output_dir(tour) / "tournaments.json") or []
    for ev in tournaments:
        if ev.get("status") != "live":
            continue
        rec = {
            "type": "tournament", "as_of": as_of, "tour": tour,
            "event": ev.get("name"), "season": _season(ev.get("end"), as_of),
            "surface": ev.get("surface"), "level": ev.get("level"),
            "modelFavorite": ev.get("modelFavorite"),
            "projection": ev.get("projection"), "model_version": __version__,
        }
        k = _tourn_key(rec)
        if k in seen_tourn:
            continue
        seen_tourn.add(k)
        new.append(rec)

    if new:
        with open(path, "a", encoding="utf-8") as f:
            for rec in new:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(new)


def movement_for_upcoming(tour: str, rows: list[dict]) -> dict[str, dict]:
    """Movement summaries keyed by the shared matchup key for enriched upcoming rows."""
    records = _read_log(FORECAST_DIR / f"{tour}.jsonl")
    bridges = _forecast_match_bridges(tour, records)
    history = _history_index(records, bridges)
    out: dict[str, dict] = {}
    for row in rows:
        probe = {
            **row,
            "season": _season(row.get("date")),
        }
        key = _effective_match_id(probe, bridges)
        records = history.get(key) or []
        if not records:
            continue
        normalized = _forecast_history(records, row["playerA"], current=float(row["pA"]))
        if normalized:
            out[key] = normalized
    return out


def movement_key(row: dict) -> str:
    """Public key helper for consumers decorating the same enriched upcoming rows."""
    return _match_key({**row, "season": _season(row.get("date"))})


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------
def _grade_matches(matches: list, df: pd.DataFrame) -> list:
    """Join logged match forecasts to completed results; return graded records."""
    comp = df[df["completed"]] if "completed" in df else df
    index: dict = defaultdict(list)
    for row in comp.itertuples(index=False):
        wk = player_identity_key(row.winner_name)
        lk = player_identity_key(row.loser_name)
        walkover = getattr(row, "walkover", False)
        walkover = bool(walkover) if not pd.isna(walkover) else False
        index[frozenset((wk, lk))].append({
            "date": pd.Timestamp(row.date),
            "winner": row.winner_name,
            "loser": row.loser_name,
            "espnId": _clean_id(getattr(row, "espn_id", None)),
            "round": getattr(row, "round", None),
            "walkover": walkover,
        })

    graded = []
    for r in matches:
        pair = frozenset((player_identity_key(r["playerA"]),
                          player_identity_key(r["playerB"])))
        cands = index.get(pair)
        if not cands:
            continue                                        # not resolved yet -> pending
        as_of = pd.Timestamp(r["as_of"])
        # New hourly records carry an explicit UTC offset; historical result frames are
        # intentionally date-only/naive. Compare calendar instants on the same basis so
        # enabling snapshots cannot disable the entire best-effort tracker.
        if as_of.tzinfo is not None:
            as_of = as_of.tz_convert(None)
        valid = [c for c in cands if -1 <= (c["date"] - as_of).days <= JOIN_WINDOW_DAYS]
        if not valid:
            continue
        event_id = _clean_id(r.get("espnId", r.get("espn_id")))
        if event_id:
            same_event = [c for c in valid if c["espnId"] == event_id]
            if same_event:
                valid = same_event
        # A pair can meet twice inside the 21-day safety window. Without registry evidence,
        # guessing which result belongs to the forecast would silently corrupt both the
        # benchmark and expectation scorecard, so leave ambiguous records pending.
        if len(valid) != 1:
            continue
        result = valid[0]
        date, winner = result["date"], result["winner"]
        a_won = player_identity_key(winner) == player_identity_key(r["playerA"])
        p_a = float(r["p"])
        graded.append({
            **r, "date": date.strftime("%Y-%m-%d"), "actualWinner": winner,
            "match_id": _match_key(r), "walkover": result["walkover"],
            "p_a": p_a, "a_won": a_won,
            "p_winner": p_a if a_won else 1.0 - p_a,        # winner-oriented (metrics.score)
            "hit": (p_a > 0.5) == a_won,
        })
    return graded


def _player_performance(graded: list[dict]) -> list[dict]:
    """Last-N actual wins versus first-sighting expected wins, per player.

    This is a descriptive evaluation surface, not a model feature. Only immutable `match`
    records reach `graded`; walkovers are excluded because no competitive win occurred.
    """
    rows: dict[str, list[dict]] = defaultdict(list)
    for g in graded:
        if g.get("walkover"):
            continue
        for player, opponent, p, won in (
            (g["playerA"], g["playerB"], float(g["p_a"]), bool(g["a_won"])),
            (g["playerB"], g["playerA"], 1.0 - float(g["p_a"]), not bool(g["a_won"])),
        ):
            rows[player].append({
                "matchId": _match_key(g),
                "date": g["date"], "event": g.get("event"), "round": g.get("round"),
                "surface": g.get("surface"), "opponent": opponent,
                "p": round(p, 4), "won": won, "residual": round((1.0 if won else 0.0) - p, 4),
            })

    out = []
    for name, decisions in rows.items():
        recent = sorted(decisions, key=lambda r: (r["date"], r["matchId"]), reverse=True)[:PERFORMANCE_N]
        expected = sum(r["p"] for r in recent)
        actual = sum(1 for r in recent if r["won"])
        out.append({
            "name": name, "n": len(recent), "wins": actual,
            "expectedWins": round(expected, 3), "delta": round(actual - expected, 3),
            "recent": recent,
        })
    return sorted(out, key=lambda r: (-r["delta"], -r["n"], r["name"]))


def _grade_tournaments(tourns: list, tour: str) -> dict:
    """Score logged title-odds snapshots against the eventual champion of each event."""
    completed = {}
    for ev in (_read_json(output_dir(tour) / "tournaments.json") or []):
        if ev.get("status") == "completed" and ev.get("champion"):
            completed[_norm_event(ev.get("name"))] = ev

    by_event: dict = defaultdict(list)
    for r in tourns:
        by_event[(_norm_event(r.get("event")), r.get("season"))].append(r)

    events = []
    for (ek, _), snaps in by_event.items():
        ev = completed.get(ek)
        if not ev:
            continue                                        # not finished (or name miss)
        ck = nkey(ev["champion"])
        # Score only snapshots that actually carried odds. A card whose draw was still mostly
        # unresolved qualifiers publishes NO projection by design (see
        # sim.tournaments.projection_is_meaningful); counting that as a forecast would charge
        # the model a Brier of 1.0 — the worst possible score — for declining to guess.
        priced = [s for s in snaps if (s.get("projection") or [])]
        if not priced:
            continue                                        # never priced -> not a benchmark event
        briers = []
        for s in priced:
            proj = {nkey(p["name"]): p.get("champion", 0.0) for p in s["projection"]}
            briers.append((1.0 - proj.get(ck, 0.0)) ** 2)   # champion-indicator Brier
        last = max(priced, key=lambda s: s.get("as_of", ""))
        fav = (last.get("projection") or [{}])[0].get("name")
        events.append({
            "event": ev.get("name"), "end": ev.get("end"), "champion": ev["champion"],
            "modelFavorite": fav, "favoritePicked": bool(fav and nkey(fav) == ck),
            "championBrier": round(float(np.mean(briers)), 4), "snapshots": len(snaps),
        })

    if not events:
        return {"events": 0, "hitRate": None, "championBrier": None, "recent": []}
    return {
        "events": len(events),
        "hitRate": round(float(np.mean([e["favoritePicked"] for e in events])), 3),
        "championBrier": round(float(np.mean([e["championBrier"] for e in events])), 4),
        "recent": sorted(events, key=lambda e: e.get("end") or "", reverse=True)[:20],
    }


def _score_or_empty(probs: list) -> dict:
    return score(np.asarray(probs, dtype=float)) if probs else {"n": 0, "acc": None,
                                                                 "logloss": None, "brier": None}


def _drift_block(graded: list, baseline: dict | None,
                 current_version: str = __version__) -> dict:
    """Calibration-drift monitor: is the model scoring worse than its own confidence?

    Per graded match, d_i = realized logloss − forecast entropy (the forecast's expected
    logloss under perfect calibration). E[d] = 0 for a calibrated model regardless of slate
    composition, so d > 0 = overconfident/decayed — the "re-tune recommended" signal that
    data/health.py surfaces as an advisory. One-sided: a lucky window (d < 0) never fires.
    Window: trailing DRIFT_WINDOW_DAYS anchored to the newest graded RESULT date (not wall
    clock, so the off-season doesn't drain the sample), filtered to the current model
    version so a re-tune + __version__ bump resets the monitor. `baseline` (accuracy.json)
    is context only — an unpaired live-vs-backtest logloss gap is composition-confounded,
    which is exactly why it is not the trigger.
    """
    recs = [g for g in graded if g.get("model_version") == current_version]
    if recs:
        newest = max(pd.Timestamp(g["date"]) for g in recs)
        cutoff = newest - pd.Timedelta(days=DRIFT_WINDOW_DAYS)
        recs = [g for g in recs if pd.Timestamp(g["date"]) >= cutoff]

    out: dict = {
        "status": "insufficient", "windowDays": DRIFT_WINDOW_DAYS,
        "modelVersion": current_version, "n": len(recs),
        "logloss": None, "expectedLogloss": None, "d": None, "se": None, "t": None,
        "baseline": None, "worstBin": None,
    }

    live_ll = None
    if len(recs) >= DRIFT_MIN_N:
        p_w = np.clip(np.array([g["p_winner"] for g in recs], dtype=float), EPS, 1 - EPS)
        p_a = np.clip(np.array([g["p_a"] for g in recs], dtype=float), EPS, 1 - EPS)
        ll = -np.log(p_w)
        ent = -(p_a * np.log(p_a) + (1 - p_a) * np.log(1 - p_a))
        d_i = ll - ent
        d = float(d_i.mean())
        se = float(d_i.std(ddof=1) / np.sqrt(len(d_i)))
        live_ll = float(ll.mean())
        out.update({
            "status": "drift" if (se > 0 and d > DRIFT_TRIGGER_K * se and d > DRIFT_MIN_EXCESS)
                      else "ok",
            "logloss": round(live_ll, 4), "expectedLogloss": round(float(ent.mean()), 4),
            "d": round(d, 4), "se": round(se, 4),
            "t": round(d / se, 2) if se > 0 else 0.0,
        })

        cal = calibration_table(np.array([g["p_a"] for g in recs]),
                                np.array([1.0 if g["a_won"] else 0.0 for g in recs]))
        big = cal[cal["n"] >= 25]
        if not big.empty:
            worst = big.loc[(big["pred"] - big["actual"]).abs().idxmax()]
            out["worstBin"] = {
                "bin": worst["bin"], "n": int(worst["n"]),
                "pred": round(float(worst["pred"]), 4),
                "actual": round(float(worst["actual"]), 4),
                "gap": round(abs(float(worst["pred"]) - float(worst["actual"])), 4),
            }

    comb = (baseline or {}).get("models", {}).get("combiner")
    if isinstance(comb, dict) and isinstance(comb.get("logloss"), (int, float)) \
            and np.isfinite(comb["logloss"]):
        out["baseline"] = {
            "logloss": round(float(comb["logloss"]), 4), "n": comb.get("n"),
            "window": (baseline or {}).get("window"),
            # dLogloss > 0 = live scoring worse than backtest (composition-confounded, context only)
            "dLogloss": round(live_ll - float(comb["logloss"]), 4) if live_ll is not None else None,
        }
    return out


def grade(tour: str, df: pd.DataFrame, *, status: dict | None = None) -> dict:
    """Read the log, score it against `df`'s results, write + return track.json."""
    log = _read_log(FORECAST_DIR / f"{tour}.jsonl", status=status)
    bridges = _forecast_match_bridges(tour, log)
    # A pre-v2 first-sighting and the later ID-backed migration row are one decision.
    # Keep the earliest provenance once and recover its registry ID from later evidence.
    first_matches: dict[str, dict] = {}
    for rec in sorted(
        (r for r in log if r.get("type") == "match"),
        key=lambda r: str(r.get("as_of") or ""),
    ):
        original_id = _match_key(rec)
        match_id = _effective_match_id(rec, bridges)
        if match_id in first_matches:
            continue
        normalized = {**rec, "match_id": match_id}
        if match_id != original_id:
            canonical_round = _round_from_match_id(match_id)
            if canonical_round:
                normalized["round"] = canonical_round
        event_id = _event_id_from_match_id(match_id)
        if event_id and not _clean_id(normalized.get("espnId")):
            normalized["espnId"] = event_id
        first_matches[match_id] = normalized
    matches = list(first_matches.values())
    tourns = [r for r in log if r.get("type") == "tournament"]
    graded = _grade_matches(matches, df)
    histories = _history_index(log, bridges)

    cal = []
    if graded:
        cal = calibration_table(
            np.array([g["p_a"] for g in graded]),
            np.array([1.0 if g["a_won"] else 0.0 for g in graded]),
        ).to_dict("records")

    by_surface = {}
    for s in SURFACES:
        gs = [g["p_winner"] for g in graded if g["surface"] == s]
        if gs:
            by_surface[s] = _score_or_empty(gs)

    by_month: dict = defaultdict(list)
    for g in graded:
        by_month[g["date"][:7]].append(g["p_winner"])
    by_month_out = [{"month": m, **_score_or_empty(v)} for m, v in sorted(by_month.items())]

    recent = []
    for g in sorted(graded, key=lambda x: x["date"], reverse=True)[:RECENT_N]:
        recent.append({
            "matchId": _match_key(g),
            "date": g["date"], "event": g["event"], "round": g["round"], "surface": g["surface"],
            "playerA": g["playerA"], "playerB": g["playerB"], "p": round(g["p_a"], 3),
            "actualWinner": g["actualWinner"], "hit": g["hit"],
            "forecast": _forecast_history(histories.get(_match_key(g)) or [], g["playerA"]),
        })

    performance = {
        "tour": tour,
        "lastUpdated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": PERFORMANCE_N,
        "method": "actual wins minus first-sighting expected wins; walkovers excluded",
        "players": _player_performance(graded),
    }

    out = {
        "tour": tour,
        "lastUpdated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matchForecasts": {
            "logged": len(matches), "graded": len(graded), "pending": len(matches) - len(graded),
            "overall": _score_or_empty([g["p_winner"] for g in graded]),
            "calibration": cal, "byMonth": by_month_out, "bySurface": by_surface,
            "recent": recent,
            "drift": _drift_block(graded, _read_json(output_dir(tour) / "accuracy.json")),
        },
        "tournamentOdds": _grade_tournaments(tourns, tour),
    }
    out_path = output_dir(tour) / "track.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    performance_path = output_dir(tour) / "performance.json"
    from ..artifact_lineage import write_produced_artifact_batch
    write_produced_artifact_batch(tour, (
        (
            out_path,
            json.dumps(out, ensure_ascii=False, indent=2).encode("utf-8"),
        ),
        (
            performance_path,
            json.dumps(performance, ensure_ascii=False, indent=2).encode("utf-8"),
        ),
    ))
    return out


def log_and_grade(tour: str, predictor, df: pd.DataFrame, *,
                  enriched: list[dict] | None = None,
                  status: dict | None = None) -> dict:
    """Pipeline entry point: log today's forecasts, then (re)grade the whole log."""
    # Hour-granular timestamps make snapshot retries idempotent while retaining the exact
    # quote-time ordering the Kalshi ledger needs. Older date-only lines remain valid.
    as_of = datetime.now(UTC).replace(minute=0, second=0, microsecond=0).isoformat()
    with timed(tour, "tracking.total"):
        with timed(tour, "tracking.log"):
            n = log_forecasts(
                tour, predictor, df,
                None if enriched is not None else load_upcoming(tour),
                as_of, enriched=enriched, status=status,
            )
        with timed(tour, "tracking.grade"):
            out = grade(tour, df, status=status)
    mf = out["matchForecasts"]
    print(f"  track/{tour}: +{n} logged, {mf['graded']} graded / {mf['pending']} pending; "
          f"tournament odds graded for {out['tournamentOdds']['events']} event(s)")
    return out
