"""Unit checks for points/markov — fully synthetic (no data, no network).

Runnable directly (`python tests/test_markov.py`) or under pytest. Covers the
point -> game -> set -> match hierarchy: hold-probability amplification, set-prob
symmetry, the set-score distribution, Bo5 edge compounding, and the
match-prob <-> set-prob round trip.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.points.markov import (
    hold_prob,
    match_prob,
    match_win_prob,
    score_distribution,
    set_prob,
    set_prob_from_match,
)


def test_hold_prob():
    # a 50/50 point makes the game a coin flip — exactly 0.5, no server edge to amplify
    assert abs(float(hold_prob(0.5)) - 0.5) < 1e-12
    # above 0.5 the server's per-point edge is AMPLIFIED at game level (p < hold < 1)
    ps = [0.55, 0.60, 0.64, 0.70, 0.80]
    hs = [float(hold_prob(p)) for p in ps]
    for p, h in zip(ps, hs):
        assert p < h < 1.0, (p, h)
    # monotone in the point probability
    assert all(b > a for a, b in zip(hs, hs[1:])), hs
    print("ok test_hold_prob")


def test_set_prob_symmetry():
    # equal serve skills -> even set
    assert abs(set_prob(0.64, 0.64) - 0.5) < 1e-9
    # complementarity: P(A wins set) + P(B wins set) == 1
    assert abs(set_prob(0.68, 0.61) + set_prob(0.61, 0.68) - 1.0) < 1e-9
    # the better server is favoured
    assert set_prob(0.70, 0.60) > 0.5
    print("ok test_set_prob_symmetry")


def test_match_prob_distribution():
    for bo in (3, 5):
        out = match_prob(0.67, 0.62, best_of=bo)
        dist = out["set_dist"]
        need = bo // 2 + 1
        assert len(dist) == 2 * need, dist                    # A/B x each losing-set count
        assert abs(sum(dist.values()) - 1.0) < 1e-9, dist     # proper distribution
        a_mass = sum(v for k, v in dist.items() if k.startswith("A"))
        assert abs(a_mass - out["p"]) < 1e-12, (a_mass, out["p"])
        assert 0.5 < out["p"] < 1.0
    # equal skills -> even match
    assert abs(match_prob(0.64, 0.64)["p"] - 0.5) < 1e-9
    print("ok test_match_prob_distribution")


def test_bo5_amplifies_edge():
    p3 = match_win_prob(0.67, 0.62, best_of=3)
    p5 = match_win_prob(0.67, 0.62, best_of=5)
    # a per-point edge compounds over more sets
    assert 0.5 < p3 < p5, (p3, p5)
    # mirror image: the underdog is hurt by the longer format
    assert match_win_prob(0.62, 0.67, best_of=5) < match_win_prob(0.62, 0.67, best_of=3) < 0.5
    print("ok test_bo5_amplifies_edge")


def test_set_match_round_trip():
    for bo in (3, 5):
        out = match_prob(0.66, 0.63, best_of=bo)
        # inverting the match prob recovers the per-set prob that produced it
        sa = set_prob_from_match(out["p"], best_of=bo)
        assert abs(sa - out["set_prob"]) < 1e-6, (bo, sa, out["set_prob"])
        # and the back-solved scoreline distribution agrees with the headline prob
        dist = score_distribution(out["p"], best_of=bo)
        assert abs(sum(dist.values()) - 1.0) < 1e-9, dist
        a_mass = sum(v for k, v in dist.items() if k.startswith("A"))
        assert abs(a_mass - out["p"]) < 1e-6, (a_mass, out["p"])
    print("ok test_set_match_round_trip")


if __name__ == "__main__":
    test_hold_prob()
    test_set_prob_symmetry()
    test_match_prob_distribution()
    test_bo5_amplifies_edge()
    test_set_match_round_trip()
    print("\nALL PASSED")
