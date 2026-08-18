from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.sim.scenarios import exact_bracket


def _draw():
    return [
        {"round": "SF", "matches": [
            {"a": "A", "b": "B", "winner": "a"},
            {"a": "C", "b": "D", "winner": None},
        ]},
        {"round": "F", "matches": [
            {"a": "A", "b": None, "winner": None},
        ]},
    ]


def _matrix():
    # A 60% against everyone; C 70% against D. Antisymmetric by contract.
    return [
        [0.5, 0.6, 0.6, 0.6],
        [0.4, 0.5, 0.5, 0.5],
        [0.4, 0.5, 0.5, 0.7],
        [0.4, 0.5, 0.3, 0.5],
    ]


def test_exact_propagation_conditions_known_results():
    out = exact_bracket(_draw(), ["A", "B", "C", "D"], _matrix())
    champ = {row["name"]: row["p"] for row in out["champion"]}
    assert champ == {"A": 0.6, "C": 0.28, "D": 0.12}
    assert "B" not in champ
    assert out["nodes"][0]["matches"][0]["status"] == "confirmed"
    assert out["reach"]["A"]["F"] == 1.0


def test_forced_pick_recomputes_downstream_exactly_and_cannot_rewrite_history():
    out = exact_bracket(
        _draw(), ["A", "B", "C", "D"], _matrix(),
        forced={"0:0": "B", "0:1": "D"},
    )
    champ = {row["name"]: row["p"] for row in out["champion"]}
    assert champ == {"A": 0.6, "D": 0.4}  # confirmed A beats B overrides the scenario
    assert out["nodes"][0]["matches"][1]["status"] == "forced"
