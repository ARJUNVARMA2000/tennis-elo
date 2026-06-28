"""Core Elo math for tennis.

  - expected score:  E_a = 1 / (1 + 10^((R_b - R_a)/scale))
  - dynamic K:       K   = scale / (n + offset)^shape        (n = career matches)
  - margin weight:   mult = 1 + factor*ln(1 + game_diff), capped   ("Weighted Elo")

Surface ratings use their own (gentler) dynamic-K parameters because each surface
sees a fraction of a player's matches.
"""

from __future__ import annotations

import math

from ..config import (
    K_OFFSET,
    K_SCALE,
    K_SHAPE,
    MOV_CAP,
    MOV_FACTOR,
    RATING_SCALE,
    SURFACE_K_OFFSET,
    SURFACE_K_SCALE,
    SURFACE_K_SHAPE,
)


def expected_score(rating_a: float, rating_b: float) -> float:
    """Win probability of A vs B from their ratings (0..1)."""
    return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) / RATING_SCALE))


def dynamic_k(n_matches: int) -> float:
    """Overall-Elo update size for a player with `n_matches` career matches."""
    return K_SCALE / math.pow(n_matches + K_OFFSET, K_SHAPE)


def surface_k(n_matches: int) -> float:
    """Surface-Elo update size for a player with `n_matches` matches on that surface."""
    return SURFACE_K_SCALE / math.pow(n_matches + SURFACE_K_OFFSET, SURFACE_K_SHAPE)


def mov_multiplier(game_diff: int) -> float:
    """Margin-of-victory multiplier from the game margin (Weighted Elo).

    Logarithmic so a 6-0 6-0 demolition counts more than a 7-6 7-6 squeaker, but
    without letting blowouts dominate. Returns 1.0 for a dead-even margin.
    """
    gd = abs(int(game_diff))
    if gd <= 0:
        return 1.0
    return min(1.0 + MOV_FACTOR * math.log(1.0 + gd), MOV_CAP)
