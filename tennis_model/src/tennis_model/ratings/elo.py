"""Core Elo math for tennis.

  - expected score:  E_a = 1 / (1 + 10^((R_b - R_a)/scale))
  - dynamic K:       K   = scale / (n + offset)^shape        (n = career matches)
  - margin weight:   mult = 1 + factor*ln(1 + game_diff), capped   ("Weighted Elo")

Surface ratings use their own (gentler) dynamic-K parameters because each surface
sees a fraction of a player's matches.

All knobs live on the frozen `EloParams` dataclass whose defaults are read from
config — production behavior is a plain `EloParams()`, while the offline tuning
harness (eval/tune.py) passes candidate parameter sets without touching config.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..config import (
    BLEND_N50,
    BO5_SCALE,
    FORM_DAYS,
    HOME_ADV,
    INACT_BOOST,
    INACT_DAYS,
    K_OFFSET,
    K_SCALE,
    K_SHAPE,
    MOV_CAP,
    MOV_FACTOR,
    RATING_SCALE,
    RET_K_MULT,
    SKIP_WALKOVERS,
    SURFACE_BLEND,
    SURFACE_K_OFFSET,
    SURFACE_K_SCALE,
    SURFACE_K_SHAPE,
    XSURF_TRANSFER,
)


@dataclass(frozen=True)
class EloParams:
    """Every tunable knob of the rating walk (defaults = config = production)."""

    rating_scale: float = RATING_SCALE
    k_scale: float = K_SCALE
    k_offset: float = K_OFFSET
    k_shape: float = K_SHAPE
    surface_k_scale: float = SURFACE_K_SCALE
    surface_k_offset: float = SURFACE_K_OFFSET
    surface_k_shape: float = SURFACE_K_SHAPE
    surface_blend: float = SURFACE_BLEND
    mov_factor: float = MOV_FACTOR
    mov_cap: float = MOV_CAP
    skip_walkovers: bool = SKIP_WALKOVERS   # walkover = zero on-court information
    ret_k_mult: float = RET_K_MULT          # retirement/default K down-weight
    inact_days: float = INACT_DAYS          # layoff K-boost threshold (0 = off)
    inact_boost: float = INACT_BOOST
    bo5_scale: float = BO5_SCALE            # rating-diff scale for best-of-5
    form_days: float = FORM_DAYS            # window for the form90 momentum feature
    xsurf: float = XSURF_TRANSFER           # cross-surface transfer weight (0 = off)
    blend_n50: float = BLEND_N50            # adaptive-blend half-saturation (0 = off)
    home_adv: float = HOME_ADV              # home-country rating bonus (0 = off)


DEFAULT_PARAMS = EloParams()


def params_for(tour: str) -> EloParams:
    """The tour's EloParams: shared defaults + the tour's tuned overrides."""
    from ..config import ELO_PARAM_OVERRIDES
    return EloParams(**ELO_PARAM_OVERRIDES.get(tour, {}))


def expected_score(rating_a: float, rating_b: float,
                   params: EloParams = DEFAULT_PARAMS, diff_scale: float = 1.0) -> float:
    """Win probability of A vs B from their ratings (0..1). `diff_scale` stretches
    the rating difference (used for the best-of-5 adjustment)."""
    return 1.0 / (1.0 + math.pow(10.0, (rating_b - rating_a) * diff_scale / params.rating_scale))


def dynamic_k(n_matches: int, params: EloParams = DEFAULT_PARAMS) -> float:
    """Overall-Elo update size for a player with `n_matches` career matches."""
    return params.k_scale / math.pow(n_matches + params.k_offset, params.k_shape)


def surface_k(n_matches: int, params: EloParams = DEFAULT_PARAMS) -> float:
    """Surface-Elo update size for a player with `n_matches` matches on that surface."""
    return params.surface_k_scale / math.pow(n_matches + params.surface_k_offset,
                                             params.surface_k_shape)


def mov_multiplier(game_diff: int, params: EloParams = DEFAULT_PARAMS) -> float:
    """Margin-of-victory multiplier from the game margin (Weighted Elo).

    Logarithmic so a 6-0 6-0 demolition counts more than a 7-6 7-6 squeaker, but
    without letting blowouts dominate. Returns 1.0 for a dead-even margin.
    """
    gd = abs(int(game_diff))
    if gd <= 0:
        return 1.0
    return min(1.0 + params.mov_factor * math.log(1.0 + gd), params.mov_cap)
