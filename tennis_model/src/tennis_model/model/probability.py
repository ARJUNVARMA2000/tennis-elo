"""One probability contract for calibrated, player-exchange-consistent forecasts."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .features import SYMMETRIC, antisymmetric_for, features_for, frame_tour

PROBABILITY_POLICY = "calibrated-pair-average-v1"


def _checked(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("probability input must be a feature frame")
    columns = features_for(frame_tour(frame))
    signed = antisymmetric_for(frame_tour(frame))
    if list(frame.columns) != columns:
        raise ValueError("probability input must have the exact ordered feature schema")
    if (len(set(columns)) != len(columns) or set(signed) & set(SYMMETRIC)
            or set(signed) | set(SYMMETRIC) != set(columns)):
        raise ValueError("feature orientation partition is invalid")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("probability features must be finite")
    return frame


def reverse_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Swap player slots without changing context, order, index or the caller's frame."""
    out = _checked(frame).copy()
    signed = antisymmetric_for(frame_tour(out))
    out.loc[:, signed] = -out[signed]
    return out


def calibrated_probability(clf, calibrator, frame: pd.DataFrame) -> np.ndarray:
    """Unaveraged legacy probability; retained for explicitly labeled diagnostics."""
    frame = _checked(frame)
    if frame.empty:
        return np.empty(0, dtype=np.float64)
    raw = np.asarray(clf.predict_proba(frame), dtype=np.float64)
    if raw.shape != (len(frame), 2) or not np.isfinite(raw).all():
        raise ValueError("classifier returned malformed probabilities")
    if np.any((raw < 0) | (raw > 1)):
        raise ValueError("classifier probabilities are outside [0, 1]")
    p = np.asarray(calibrator.predict(raw[:, 1]), dtype=np.float64)
    if p.shape != (len(frame),) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("calibrator returned invalid probabilities")
    return p


def paired_probability(clf, calibrator, forward_features: pd.DataFrame,
                       reverse_features: pd.DataFrame | None = None) -> np.ndarray:
    """Average calibrated P(A,B) and 1-P(B,A); no fitting, state updates or clipping.

    Explicit reverse rows let callers test independently constructed swapped inputs.
    Endpoint probabilities remain valid; metric code owns its declared log clipping.
    """
    forward = _checked(forward_features)
    if reverse_features is None:
        reverse = forward.copy()
        signed = antisymmetric_for(frame_tour(forward))
        reverse.loc[:, signed] = -reverse[signed]
    else:
        reverse = _checked(reverse_features)
        if list(reverse) != list(forward):
            raise ValueError("forward and reverse feature schemas differ")
    if len(reverse) != len(forward):
        raise ValueError("forward and reverse probability rows must be paired")
    both = pd.concat([forward, reverse], ignore_index=True)
    p = calibrated_probability(clf, calibrator, both)
    n = len(forward)
    return 0.5 * (p[:n] + (1.0 - p[n:]))
