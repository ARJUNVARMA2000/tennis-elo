"""Explicit offline saved predictor for the fixed WTA surface exposure candidate."""

from itertools import combinations

import numpy as np
import pandas as pd
from signal_combiner import checked, columns, fit_fold, probability
from tennis_model.config import WTA_DUAL_STATE_GATE_THRESHOLD
from tennis_model.model.predict import TennisPredictor
from tennis_model.model.train import FINAL_TRAIN_SEED

FEATURE = "surface_recent_diff"
COLUMNS = columns((FEATURE,))
SCHEMA = "wta-surface-candidate-v1"


class SurfaceCandidatePredictor(TennisPredictor):
    """The surface state follows the exact same main/lower selector as other inputs."""

    def __init__(self, *args, surface_main, surface_lower, surface_provenance, **kwargs):
        if kwargs.get("tour") != "wta":
            raise ValueError("surface candidate is WTA-only")
        super().__init__(*args, **kwargs)
        if self._dual_state_threshold != WTA_DUAL_STATE_GATE_THRESHOLD:
            raise ValueError("surface candidate requires threshold32")
        if surface_main is None or surface_lower is None:
            raise ValueError("surface candidate requires both states")
        self.surface_main, self.surface_lower = surface_main, surface_lower
        self.surface_provenance = dict(surface_provenance)

    @property
    def feature_columns(self):
        return COLUMNS

    def _combiner_probability(self, frame):
        return probability(self.clf, self.iso, frame, (FEATURE,))

    def _feature_dict(self, a, b, surface, best_of, indoor, tier_k, round_order,
                      event=None, as_of=None):
        elo = self._states_for(a, b)[0]
        state = self.surface_lower if elo is self.lower_elo else self.surface_main
        if state is None:
            raise RuntimeError("selected surface state is absent")
        date = as_of if as_of is not None else elo.last_date
        value = state.query(a, b, surface, date)[FEATURE]
        row = super()._feature_dict(a, b, surface, best_of, indoor, tier_k, round_order,
                                    event=event, as_of=date)
        row[FEATURE] = float(value)
        return row

    def prediction_evidence(self, a, b, *args, **kwargs):
        result = super().prediction_evidence(a, b, *args, **kwargs)
        frame = self.features(a, b, *args, **kwargs)
        neutral = frame.copy()
        neutral[FEATURE] = 0.0
        delta = float(self._combiner_probability(frame)[0]-self._combiner_probability(neutral)[0])*100
        result["signals"].append({
            "key": "recentSurface", "available": True,
            "supports": a if delta > .005 else b if delta < -.005 else None,
            "impactPp": round(delta, 2),
            "facts": {"windowDays": 60, "logCountDifference": float(frame[FEATURE].iloc[0]),
                      "state": "enriched" if self._states_for(a, b)[0] is self.lower_elo else "main"},
        })
        result["signals"].sort(key=lambda item: (-abs(item["impactPp"]) if item["available"] else 1., item["key"]))
        return result

    def prediction_evidence_matrices(self, players, *args, **kwargs):
        result = super().prediction_evidence_matrices(players, *args, **kwargs)
        n = len(players)
        effects, available = np.zeros((n, n)), np.zeros((n, n))
        pairs = list(combinations(range(n), 2))
        if pairs:
            frame = pd.concat([self.features(players[i], players[j], *args, **kwargs)
                               for i, j in pairs], ignore_index=True)
            neutral = frame.copy()
            neutral[FEATURE] = 0.0
            delta = self._combiner_probability(frame)-self._combiner_probability(neutral)
            for (i, j), value in zip(pairs, delta, strict=True):
                effects[i, j], effects[j, i] = value, -value
                available[i, j] = available[j, i] = 1.
        result["effects"]["recentSurface"] = effects
        result["available"]["recentSurface"] = available
        return result

    def save(self, path, *, trusted_root):
        from surface_artifact import save_surface
        save_surface(self, path, trusted_root=trusted_root)

    @staticmethod
    def load(path, *, expected_provenance, trusted_root):
        from surface_artifact import load_surface
        return load_surface(path, expected_provenance=expected_provenance, trusted_root=trusted_root)


def fit_surface_predictor(inputs, *, provenance):
    """One normal final fit; only the registered 43-column schema differs."""
    frame = inputs["frames"]["main"]
    if not frame.tour.eq("wta").all() or not frame.draw_level.eq("main").all():
        raise ValueError("surface final fit requires WTA main rows")
    checked(frame[COLUMNS], (FEATURE,))
    completed = frame[frame.completed & frame.year.ge(1991)]
    cutoff = completed.date.max()-pd.Timedelta(days=365)
    core, cal = completed[completed.date.lt(cutoff)], completed[completed.date.ge(cutoff)]
    if core.empty or cal.empty:
        raise ValueError("surface final fit requires disjoint training/calibration rows")
    clf, calibration = fit_fold(core, cal, FINAL_TRAIN_SEED, (FEATURE,), tour="wta")
    ordinary = inputs["ordinary"]
    return SurfaceCandidatePredictor(
        clf, calibration, ordinary.elo, ordinary.srv, ordinary.ctx, ordinary.meta,
        tour="wta", lower_elo=ordinary.lower_elo, lower_srv=ordinary.lower_srv,
        lower_ctx=ordinary.lower_ctx, dual_state_threshold=WTA_DUAL_STATE_GATE_THRESHOLD,
        surface_main=inputs["states"]["main"], surface_lower=inputs["states"]["enriched"],
        surface_provenance=provenance,
    )
