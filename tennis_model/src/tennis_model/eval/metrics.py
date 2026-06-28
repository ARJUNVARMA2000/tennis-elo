"""Shared scoring metrics for probabilistic match predictions.

Convention: `p` is the model's pre-match probability that the player who actually
won the match would win. Accuracy / log-loss / Brier are invariant to which player
is listed first, so this winner-oriented form is unbiased. Calibration needs a
50/50 label split, so callers pass randomized-orientation (p, label) pairs.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12


def accuracy(p: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    return float(np.mean((p > 0.5) + 0.5 * (p == 0.5)))


def log_loss(p: np.ndarray) -> float:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return float(-np.mean(np.log(p)))


def brier(p: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    return float(np.mean((1.0 - p) ** 2))


def score(p: np.ndarray) -> dict:
    return {"n": int(len(p)), "acc": accuracy(p), "logloss": log_loss(p), "brier": brier(p)}


def calibration_table(p_a: np.ndarray, label: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Reliability table: predicted vs empirical win-rate across probability bins.

    `p_a` = P(player A wins) under a 50/50 A/B orientation; `label` = 1 if A won.
    """
    p_a = np.asarray(p_a, dtype=float)
    label = np.asarray(label, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(p_a, edges) - 1, 0, bins - 1)
    rows = []
    for b in range(bins):
        m = idx == b
        if not m.any():
            continue
        rows.append({
            "bin": f"{edges[b]:.1f}-{edges[b+1]:.1f}",
            "n": int(m.sum()),
            "pred": float(p_a[m].mean()),
            "actual": float(label[m].mean()),
        })
    return pd.DataFrame(rows)


def winner_oriented(p_blend: np.ndarray, winner_first: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert winner-oriented probs into randomized A/B orientation for calibration.

    `winner_first[i]` is True when player A == the winner for row i; we flip the rest.
    Returns (p_a, label) where label = 1 iff A won.
    """
    p_blend = np.asarray(p_blend, dtype=float)
    winner_first = np.asarray(winner_first, dtype=bool)
    p_a = np.where(winner_first, p_blend, 1.0 - p_blend)
    label = winner_first.astype(float)
    return p_a, label
