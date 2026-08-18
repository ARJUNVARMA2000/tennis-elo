"""Exact, deterministic bracket propagation for the interactive scenario lab.

Monte Carlo remains useful for large exploratory simulations, but a user forcing one
winner expects an immediate and repeatable answer. This module folds probability
distributions through the released draw exactly, conditioning completed results and any
user-selected winners to probability one.
"""

from __future__ import annotations

from collections import defaultdict

from .bracket import is_real


def _winner_name(match: dict) -> str | None:
    side = match.get("winner")
    return match.get(side) if side in ("a", "b") else None


def _combine(left: dict[str, float], right: dict[str, float], players: list[str], matrix: list,
             fixed: str | None = None) -> dict[str, float]:
    possible = set(left) | set(right)
    if fixed:
        # A confirmed result is evidence, not a forecast. A user scenario is the same
        # conditional statement. Keep stale-source resilience: the named winner remains
        # authoritative even if an upstream draw gap omitted them from `possible`.
        return {fixed: 1.0}
    if not left:
        return dict(right)
    if not right:
        return dict(left)
    index = {name: i for i, name in enumerate(players)}
    out: dict[str, float] = defaultdict(float)
    for a, p_left in left.items():
        for b, p_right in right.items():
            joint = p_left * p_right
            if a == b:
                out[a] += joint
                continue
            ia, ib = index.get(a), index.get(b)
            p = float(matrix[ia][ib]) if ia is not None and ib is not None else 0.5
            out[a] += joint * p
            out[b] += joint * (1.0 - p)
    total = sum(out.values())
    return {name: value / total for name, value in out.items()} if total > 0 else {
        name: 1.0 / len(possible) for name in possible
    }


def exact_bracket(rounds: list[dict], players: list[str], matrix: list[list[float]],
                  forced: dict[str, str] | None = None) -> dict:
    """Return exact node candidates, reach odds, and champion odds.

    `forced` keys use ``"<round-index>:<match-index>"``. Completed winners in the draw
    always take precedence; scenarios cannot rewrite history.
    """
    if not rounds:
        return {"nodes": [], "reach": {}, "champion": []}
    forced = forced or {}
    leaves = []
    for match in rounds[0].get("matches") or []:
        leaves.extend([
            {match.get("a"): 1.0} if is_real(match.get("a")) else {},
            {match.get("b"): 1.0} if is_real(match.get("b")) else {},
        ])

    current = leaves
    reach: dict[str, dict[str, float]] = {name: {"Entry": 1.0} for name in players}
    nodes = []
    for round_index, rnd in enumerate(rounds):
        next_nodes = []
        node_rows = []
        matches = rnd.get("matches") or []
        for match_index, match in enumerate(matches):
            left = current[2 * match_index] if 2 * match_index < len(current) else {}
            right = current[2 * match_index + 1] if 2 * match_index + 1 < len(current) else {}
            confirmed = _winner_name(match)
            selected = confirmed or forced.get(f"{round_index}:{match_index}")
            dist = _combine(left, right, players, matrix, fixed=selected)
            next_nodes.append(dist)
            candidates = [{"name": name, "p": round(p, 6)} for name, p in
                          sorted(dist.items(), key=lambda item: (-item[1], item[0]))]
            node_rows.append({
                "key": f"{round_index}:{match_index}", "round": rnd.get("round"),
                "matchIndex": match_index,
                "status": "confirmed" if confirmed else "forced" if selected else "projected",
                "winner": selected, "candidates": candidates,
            })
        next_label = (rounds[round_index + 1].get("round")
                      if round_index + 1 < len(rounds) else "Champion")
        for dist in next_nodes:
            for name, p in dist.items():
                reach.setdefault(name, {"Entry": 1.0})[next_label] = round(p, 6)
        nodes.append({"round": rnd.get("round"), "matches": node_rows})
        current = next_nodes

    champion = nodes[-1]["matches"][0]["candidates"] if nodes[-1]["matches"] else []
    return {"nodes": nodes, "reach": reach, "champion": champion}
