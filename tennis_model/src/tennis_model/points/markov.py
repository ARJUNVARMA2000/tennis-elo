"""Hierarchical tennis Markov model: point -> game -> tiebreak -> set -> match.

Given each player's probability of winning a point on their own serve, this computes
the match win probability and the distribution over set scores, for best-of-3 or
best-of-5. This is the tennis analog of the soccer model's Dixon-Coles scoreline
matrix: it turns a per-point edge into a full match-outcome distribution, and it is
what makes Bo3-vs-Bo5 fall out correctly (a per-point edge compounds over more sets).

Assumptions (standard, and matching modern rules):
  - points within a game/tiebreak are i.i.d. given the server
  - a set is first-to-6, win by 2, with a 7-point tiebreak at 6-6 (no advantage sets)
  - sets are independent; serve-first alternates between sets (a sub-0.5% effect)
The scalar set/tiebreak solvers are cached on rounded inputs so scoring 150k matches
is fast.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

P_CLIP = (0.05, 0.95)
_TB_CAP = 40        # tiebreak score cap; mass beyond this is < 1e-9


def hold_prob(p: float | np.ndarray):
    """Probability the server wins a game given per-point serve-win prob `p`."""
    p = np.asarray(p, dtype=float)
    q = 1.0 - p
    deuce = np.divide(p * p, p * p + q * q, out=np.full_like(p, 0.5), where=(p * p + q * q) > 0)
    g = p**4 * (1 + 4 * q + 10 * q * q) + 20 * p**3 * q**3 * deuce
    return g


@lru_cache(maxsize=400_000)
def _tb_win(pf: float, po: float) -> float:
    """P(first server wins a 7-point tiebreak). `pf`/`po` = serve-win prob of the
    first server / the other player. First server serves 1 point, then they alternate
    in pairs (A, B,B, A,A, ...)."""
    memo: dict = {}

    def rec(a: int, b: int) -> float:
        if a >= 7 and a - b >= 2:
            return 1.0
        if b >= 7 and b - a >= 2:
            return 0.0
        if a + b >= _TB_CAP:
            return 0.5
        key = (a, b)
        if key in memo:
            return memo[key]
        k = a + b
        server_is_first = (((k + 1) // 2) % 2) == 0
        win_pt = pf if server_is_first else (1.0 - po)
        v = win_pt * rec(a + 1, b) + (1.0 - win_pt) * rec(a, b + 1)
        memo[key] = v
        return v

    return rec(0, 0)


@lru_cache(maxsize=400_000)
def _set_win(pf: float, po: float) -> float:
    """P(the player who serves first wins the set). `pf`/`po` = that player's / the
    opponent's serve-win prob."""
    hf = float(hold_prob(pf))
    ho = float(hold_prob(po))
    memo: dict = {}

    def rec(ga: int, gb: int) -> float:
        if ga >= 6 and ga - gb >= 2:
            return 1.0
        if gb >= 6 and gb - ga >= 2:
            return 0.0
        if ga == 6 and gb == 6:
            return _tb_win(pf, po)        # first server opens the tiebreak too
        key = (ga, gb)
        if key in memo:
            return memo[key]
        first_serves_this_game = ((ga + gb) % 2) == 0
        gw = hf if first_serves_this_game else (1.0 - ho)   # P(first server wins this game)
        v = gw * rec(ga + 1, gb) + (1.0 - gw) * rec(ga, gb + 1)
        memo[key] = v
        return v

    return rec(0, 0)


def set_prob(pa: float, pb: float, round_to: int = 4) -> float:
    """P(A wins a set), averaging over who serves first (a tiny, symmetric effect)."""
    pa = min(max(pa, P_CLIP[0]), P_CLIP[1])
    pb = min(max(pb, P_CLIP[0]), P_CLIP[1])
    a, b = round(pa, round_to), round(pb, round_to)
    a_first = _set_win(a, b)
    b_first = 1.0 - _set_win(b, a)
    return 0.5 * a_first + 0.5 * b_first


def _set_score_dist(sa: float, best_of: int) -> dict:
    """Distribution over final set scores given per-set win prob `sa` (independent sets)."""
    need = best_of // 2 + 1          # sets to win (2 for Bo3, 3 for Bo5)
    sb = 1.0 - sa
    dist = {}
    # A wins need-k, losing j sets: C(need-1+j, j) * sa^need * sb^j
    from math import comb
    for j in range(need):            # sets the loser takes
        dist[f"A {need}-{j}"] = comb(need - 1 + j, j) * sa**need * sb**j
        dist[f"B {need}-{j}"] = comb(need - 1 + j, j) * sb**need * sa**j
    return dist


def match_prob(pa: float, pb: float, best_of: int = 3) -> dict:
    """Full match outcome from per-point serve-win probs.

    Returns {p: P(A wins match), set_dist: {score: prob}, set_prob: P(A wins a set)}.
    """
    sa = set_prob(pa, pb)
    dist = _set_score_dist(sa, best_of)
    p_match = sum(v for k, v in dist.items() if k.startswith("A"))
    return {"p": p_match, "set_prob": sa, "set_dist": dist}


def match_win_prob(pa: float, pb: float, best_of: int = 3) -> float:
    """Just P(A wins the match) — the hot path for batch scoring."""
    return match_prob(pa, pb, best_of)["p"]


def _match_p_from_set(sa: float, best_of: int) -> float:
    need = best_of // 2 + 1
    from math import comb
    return sum(comb(need - 1 + j, j) * sa**need * (1 - sa) ** j for j in range(need))


def set_prob_from_match(p_match: float, best_of: int = 3) -> float:
    """Invert: the per-set win prob that yields match win prob `p_match` (bisection)."""
    lo, hi = 1e-4, 1 - 1e-4
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if _match_p_from_set(mid, best_of) < p_match:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def score_distribution(p_match: float, best_of: int = 3) -> dict:
    """Set-score distribution consistent with a given match win prob `p_match`.

    Used to make the displayed scoreline distribution agree with the combiner's
    headline probability (rather than the raw point model's), by back-solving the
    implied per-set edge.
    """
    sa = set_prob_from_match(p_match, best_of)
    return {k: float(v) for k, v in _set_score_dist(sa, best_of).items()}
