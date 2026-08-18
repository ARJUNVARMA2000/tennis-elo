"""Exact probability propagation for a fixed single-elimination bracket.

The Monte Carlo simulator remains useful for hypothetical fields, but a released real
draw has fixed geometry and can be integrated exactly.  This module is deliberately
model-agnostic: callers provide the ordered player list and its pairwise probability
matrix.  The same round/match contract is mirrored in ``web/lib/scenario.ts``.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

import numpy as np

from .bracket import bracket_rounds
from .draws import SIZE_NAME

SCENARIO_SCHEMA = "scenario-v1"


def _finite_probability(value: object) -> float:
    try:
        p = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"non-numeric pairwise probability: {value!r}") from exc
    if not np.isfinite(p) or not 0.0 <= p <= 1.0:
        raise ValueError(f"pairwise probability outside [0, 1]: {value!r}")
    return p


def validate_matrix(players: list[str], matrix: np.ndarray, *, atol: float = 1e-9) -> None:
    """Validate the square, complementary pairwise contract used by both runtimes."""
    p = np.asarray(matrix, dtype=float)
    n = len(players)
    if len(set(players)) != n:
        raise ValueError("scenario players must be unique")
    if p.shape != (n, n):
        raise ValueError(f"matrix shape {p.shape} does not match {n} players")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("matrix contains a non-finite or out-of-bounds probability")
    if not np.allclose(np.diag(p), 0.5, atol=atol):
        raise ValueError("matrix diagonal must be 0.5")
    if not np.allclose(p + p.T, 1.0, atol=atol):
        raise ValueError("matrix must satisfy P(a,b) + P(b,a) = 1")


def _candidates(dist: dict[str, float]) -> list[dict]:
    return [
        {"name": name, "p": round(float(p), 8)}
        for name, p in sorted(dist.items(), key=lambda item: (-item[1], item[0]))
        if p > 1e-12
    ]


def _winner_distribution(
    side_a: dict[str, float],
    side_b: dict[str, float],
    index: dict[str, int],
    matrix: np.ndarray,
) -> dict[str, float]:
    if not side_a:
        return dict(side_b)
    if not side_b:
        return dict(side_a)
    out: dict[str, float] = defaultdict(float)
    for a, pa in side_a.items():
        for b, pb in side_b.items():
            mass = float(pa) * float(pb)
            if a == b:  # structurally impossible in a sound draw, but conserve mass safely
                out[a] += mass
                continue
            p_a = _finite_probability(matrix[index[a], index[b]])
            out[a] += mass * p_a
            out[b] += mass * (1.0 - p_a)
    return dict(out)


def _named_winner(match: dict) -> str | None:
    side = match.get("winner")
    if side == "a":
        return match.get("a")
    if side == "b":
        return match.get("b")
    return None


def propagate_rounds(
    rounds: list[dict],
    players: list[str],
    matrix: np.ndarray,
    *,
    event_id: str,
    locks: dict[str, str] | None = None,
) -> dict:
    """Propagate a released draw, respecting settled winners and optional user locks.

    Locks are accepted only for baseline matchups whose two sides are already known with
    certainty.  Future projected matchups are intentionally not editable: a user cannot
    lock a match whose participants themselves depend on earlier hypothetical outcomes.
    """
    matrix = np.asarray(matrix, dtype=float)
    validate_matrix(players, matrix)
    if not rounds or not rounds[0].get("matches"):
        raise ValueError("scenario requires at least one bracket round")
    index = {name: i for i, name in enumerate(players)}
    first_slots = [
        match.get(side)
        for match in rounds[0]["matches"]
        for side in ("a", "b")
    ]
    for slot in first_slots:
        if slot is not None and slot not in index:
            raise ValueError(f"unmodelled bracket slot: {slot!r}")

    current = [{slot: 1.0} if slot is not None else {} for slot in first_slots]
    lock_map = dict(locks or {})
    reach: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    states: list[dict] = []
    baseline_lockable: set[str] = set()

    for round_index, round_row in enumerate(rounds):
        matches = round_row.get("matches") or []
        if len(current) != len(matches) * 2:
            raise ValueError("round geometry does not match its feeder count")
        next_round: list[dict[str, float]] = []
        state_matches = []
        for match_index, match in enumerate(matches):
            side_a = dict(current[2 * match_index])
            side_b = dict(current[2 * match_index + 1])
            match_id = f"{event_id}:r{round_index}:m{match_index}"
            for name, p in (*side_a.items(), *side_b.items()):
                reach[name][str(round_row.get("round"))] += float(p)

            settled = _named_winner(match)
            certain_a = next(iter(side_a)) if len(side_a) == 1 and next(iter(side_a.values())) == 1 else None
            certain_b = next(iter(side_b)) if len(side_b) == 1 and next(iter(side_b.values())) == 1 else None
            # A projected downstream slot can become certain after an upstream lock, but it
            # is not a currently scheduled matchup.  Require the source bracket itself to
            # name both sides before exposing an editable result.
            lockable = bool(
                not settled
                and certain_a
                and certain_b
                and certain_a != certain_b
                and match.get("a") == certain_a
                and match.get("b") == certain_b
            )
            if lockable:
                baseline_lockable.add(match_id)

            locked = lock_map.get(match_id)
            if locked is not None:
                if not lockable or locked not in {certain_a, certain_b}:
                    raise ValueError(f"invalid lock {match_id}={locked!r}")
                winner_dist = {locked: 1.0}
            elif settled is not None:
                if settled not in side_a and settled not in side_b:
                    raise ValueError(f"settled winner {settled!r} is not in match {match_id}")
                winner_dist = {settled: 1.0}
            else:
                winner_dist = _winner_distribution(side_a, side_b, index, matrix)

            total = sum(winner_dist.values())
            if winner_dist and not np.isclose(total, 1.0, atol=1e-9):
                raise ValueError(f"probability mass {total} at {match_id}")
            next_round.append(winner_dist)
            state_matches.append({
                "id": match_id,
                "a": match.get("a"),
                "b": match.get("b"),
                "settledWinner": settled,
                "lockable": lockable,
                "lockedWinner": locked,
                "sideA": _candidates(side_a),
                "sideB": _candidates(side_b),
                "winnerCandidates": _candidates(winner_dist),
                "projectedWinner": (_candidates(winner_dist)[0]["name"] if winner_dist else None),
            })
        states.append({"round": round_row.get("round"), "matches": state_matches})
        current = next_round

    champion = current[0] if len(current) == 1 else {}
    for name, p in champion.items():
        reach[name]["Champion"] += float(p)
    return {
        "rounds": states,
        "reach": {
            name: {round_name: round(float(p), 8) for round_name, p in values.items()}
            for name, values in reach.items()
        },
        "champion": {name: round(float(p), 8) for name, p in champion.items()},
        "lockableMatchIds": sorted(baseline_lockable),
    }


def exact_from_slots(slots: list[str | None], players: list[str], matrix: np.ndarray) -> dict:
    """Exact reach/title odds for a fixed ordered field with no played results."""
    n = len(slots)
    if n < 2 or n & (n - 1):
        raise ValueError("slot count must be a power of two")
    rounds = bracket_rounds(slots, [])
    return propagate_rounds(rounds, players, matrix, event_id="field")


def title_leverage(
    rounds: list[dict], players: list[str], matrix: np.ndarray, *, event_id: str
) -> dict[str, dict]:
    """Conditional title-distribution leverage for every currently lockable match."""
    baseline = propagate_rounds(rounds, players, matrix, event_id=event_id)
    lookup = {
        match["id"]: match
        for round_row in baseline["rounds"]
        for match in round_row["matches"]
        if match["lockable"]
    }
    out = {}
    for match_id, match in lookup.items():
        a, b = match["a"], match["b"]
        if not isinstance(a, str) or not isinstance(b, str):
            continue
        champion_a = propagate_rounds(
            rounds, players, matrix, event_id=event_id, locks={match_id: a}
        )["champion"]
        champion_b = propagate_rounds(
            rounds, players, matrix, event_id=event_id, locks={match_id: b}
        )["champion"]
        field = set(champion_a) | set(champion_b)
        tv = 0.5 * sum(abs(champion_a.get(p, 0.0) - champion_b.get(p, 0.0)) for p in field)
        out[match_id] = {
            "playerA": a,
            "playerB": b,
            "value": round(float(tv), 8),
            "championIfA": champion_a,
            "championIfB": champion_b,
        }
    return out


def rounds_players(rounds: Iterable[dict]) -> list[str]:
    """Unique first-round names in draw order (byes omitted)."""
    rows = list(rounds)
    if not rows:
        return []
    return list(dict.fromkeys(
        name
        for match in rows[0].get("matches") or []
        for name in (match.get("a"), match.get("b"))
        if isinstance(name, str) and name
    ))


def reach_columns(slot_count: int) -> list[str]:
    """Round labels for an exact slot field, entry through champion."""
    cols = []
    width = slot_count
    while width >= 1:
        cols.append(SIZE_NAME[width])
        width //= 2
    return cols
