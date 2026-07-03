"""Vectorised Monte Carlo simulation of a single-elimination draw.

Given a pairwise win-probability matrix and a bracket order, all simulations advance
in parallel as NumPy arrays: each round pairs adjacent slots, draws winners against
the matrix, and tallies how often each player reaches each round. Byes (None slots)
auto-advance their opponent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import DEFAULT_N_SIMS
from .draws import SIZE_NAME, standard_seed_draw


def simulate_bracket(P: np.ndarray, n_sims: int = DEFAULT_N_SIMS, seed: int = 0,
                     bye_mask: np.ndarray | None = None) -> np.ndarray:
    """Return reach[player, k] = P(reach the round with n/2^k players). k=0 is entry."""
    n = P.shape[0]
    rounds = int(np.log2(n))
    rng = np.random.default_rng(seed)

    reach = np.zeros((n, rounds + 1))
    alive0 = (~bye_mask) if bye_mask is not None else np.ones(n, dtype=bool)
    reach[:, 0] = np.where(alive0, n_sims, 0)

    cur = np.tile(np.arange(n), (n_sims, 1))     # (n_sims, width)
    width = n
    for k in range(rounds):
        width //= 2
        a, b = cur[:, 0::2], cur[:, 1::2]
        pa = P[a, b]                              # P(a beats b) per pair per sim
        winners = np.where(rng.random((n_sims, width)) < pa, a, b)
        idx, counts = np.unique(winners, return_counts=True)
        reach[idx, k + 1] += counts
        cur = winners
    return reach / n_sims


def simulate_tournament(predictor, slots: list, surface: str = "Hard", best_of: int = 3,
                        n_sims: int = DEFAULT_N_SIMS, seed: int = 0,
                        indoor: bool = False, tier_k: float = 1.0,
                        event: str | None = None) -> pd.DataFrame:
    """Simulate a bracket given as a list of player names (None = bye)."""
    # Map byes to a sentinel that loses to everyone.
    bye_mask = np.array([p is None for p in slots])
    real = [p if p is not None else "__BYE__" for p in slots]
    uniq = list(dict.fromkeys(real))             # de-dup while keeping order
    P_small = predictor.win_prob_matrix(
        [u for u in uniq if u != "__BYE__"], surface, best_of, indoor, tier_k,
        event=event)
    name_to_small = {u: i for i, u in enumerate([u for u in uniq if u != "__BYE__"])}

    n = len(slots)
    P = np.full((n, n), 0.5)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            ai, aj = slots[i], slots[j]
            if aj is None:                       # opponent is a bye -> i always advances
                P[i, j] = 1.0
            elif ai is None:
                P[i, j] = 0.0
            else:
                P[i, j] = P_small[name_to_small[ai], name_to_small[aj]]

    reach = simulate_bracket(P, n_sims=n_sims, seed=seed, bye_mask=bye_mask)

    sizes = [n // (2 ** k) for k in range(reach.shape[1])]
    cols = {SIZE_NAME[s]: reach[:, k] for k, s in enumerate(sizes)}
    out = pd.DataFrame({"player": slots, **cols})
    out = out[out["player"].notna()].reset_index(drop=True)
    return out.sort_values("Champion", ascending=False).reset_index(drop=True)


def project_field(predictor, players: list, surface: str = "Hard", best_of: int = 3,
                  ratings=None, n_sims: int = DEFAULT_N_SIMS, seed: int = 0,
                  event: str | None = None) -> pd.DataFrame:
    """Convenience: seed a field by Elo and simulate the standard bracket."""
    rank = ratings or (lambda p: predictor.elo.blended(p, surface))
    ordered = sorted(players, key=rank, reverse=True)
    slots = standard_seed_draw(ordered)
    return simulate_tournament(predictor, slots, surface=surface, best_of=best_of,
                               n_sims=n_sims, seed=seed, event=event)
