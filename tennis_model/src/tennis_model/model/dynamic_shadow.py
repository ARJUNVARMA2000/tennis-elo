"""Explicit offline WTA predictor for the fixed, already evaluated candidate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..config import DYNAMIC_SHADOW_PARAM_OVERRIDES, WTA_DUAL_STATE_GATE_THRESHOLD
from ..ratings.dynamic import DYNAMIC_FEATURE, DynamicParams, attach_dynamic, run_dynamic
from . import dynamic_research as dr
from .features import DualStateInputs, build_dual_state_inputs, select_dual_state_features
from .predict import EVIDENCE_GROUPS, TennisPredictor
from .train import FINAL_TRAIN_SEED

SHADOW_SCHEMA = "wta-dynamic-shadow-v1"


def shadow_params() -> DynamicParams:
    return DynamicParams(**DYNAMIC_SHADOW_PARAM_OVERRIDES["wta"])


@dataclass
class ShadowInputs:
    ordinary: DualStateInputs
    dynamic_main: object
    dynamic_lower: object
    base_features: pd.DataFrame
    selected_features: pd.DataFrame


def build_shadow_inputs(main: pd.DataFrame, enriched: pd.DataFrame) -> ShadowInputs:
    """Walk explicit frozen inputs; lower rows never enter combiner fitting."""
    for frame in (main, enriched):
        if frame.empty or "tour" not in frame or not frame.tour.eq("wta").all():
            raise ValueError("shadow inputs must be nonempty WTA histories")
    main, enriched = main.reset_index(drop=True), enriched.reset_index(drop=True)
    ordinary = build_dual_state_inputs(main, enriched, tour="wta")
    dynamic_main, main_signal = run_dynamic(main, shadow_params())
    dynamic_lower, lower_signal = run_dynamic(enriched, shadow_params())
    lower_signal = lower_signal.loc[enriched.draw_level.eq("main")].reset_index(drop=True)
    selected = select_dual_state_features(
        ordinary.base_features, ordinary.enriched_features, WTA_DUAL_STATE_GATE_THRESHOLD
    )
    return ShadowInputs(
        ordinary, dynamic_main, dynamic_lower,
        attach_dynamic(ordinary.base_features, main_signal),
        attach_dynamic(selected, main_signal, lower_signal),
    )


class DynamicShadowPredictor(TennisPredictor):
    """All ordinary prediction routes dispatch through one explicit research schema."""

    def __init__(self, *args, dynamic_main, dynamic_lower, shadow_provenance, **kwargs):
        if kwargs.get("tour") != "wta":
            raise ValueError("dynamic shadow is WTA-only")
        super().__init__(*args, **kwargs)
        if self._dual_state_threshold != WTA_DUAL_STATE_GATE_THRESHOLD:
            raise ValueError("shadow requires the registered WTA state selector")
        if dynamic_main is None or dynamic_lower is None:
            raise ValueError("shadow requires both dynamic states")
        self.dynamic_main, self.dynamic_lower = dynamic_main, dynamic_lower
        self.shadow_provenance = dict(shadow_provenance)

    @property
    def feature_columns(self):
        return dr.COLUMNS

    @property
    def evidence_groups(self):
        """Keep the frozen dynamic experiment independent of later surface adoption."""
        return EVIDENCE_GROUPS

    def _combiner_probability(self, frame):
        return dr.probability(self.clf, self.iso, frame)

    def _feature_dict(self, a, b, surface, best_of, indoor, tier_k, round_order,
                      event=None, as_of=None):
        elo = self._states_for(a, b)[0]
        state = self.dynamic_lower if elo is self.lower_elo else self.dynamic_main
        if state is None:
            raise RuntimeError("selected shadow state is absent")
        date = as_of if as_of is not None else elo.last_date
        probability = state.win_prob(a, b, surface, as_of=date)
        row = super()._feature_dict(a, b, surface, best_of, indoor, tier_k, round_order,
                                    event=event, as_of=date)
        p = np.clip(probability, 1e-12, 1 - 1e-12)
        row[DYNAMIC_FEATURE] = float(np.log(p / (1 - p)))
        return row

    def save(self, path, *, trusted_root):
        from .shadow_artifact import save_shadow
        save_shadow(self, path, trusted_root=trusted_root)

    @staticmethod
    def load(path, *, expected_provenance, trusted_root):
        from .shadow_artifact import load_shadow
        return load_shadow(path, expected_provenance=expected_provenance,
                           trusted_root=trusted_root)


def fit_shadow_predictor(inputs: ShadowInputs, *, provenance) -> DynamicShadowPredictor:
    """Fixed final split/seed; this fit does not reevaluate or select parameters."""
    frame = inputs.base_features
    if not frame.tour.eq("wta").all() or not frame.draw_level.eq("main").all():
        raise ValueError("shadow final combiner fits only WTA main rows")
    dr.checked(frame[dr.COLUMNS])
    completed = frame[frame.completed & frame.year.ge(1991)]
    cutoff = completed.date.max() - pd.Timedelta(days=365)
    core, cal = completed[completed.date.lt(cutoff)], completed[completed.date.ge(cutoff)]
    if core.empty or cal.empty:
        raise ValueError("shadow final fit needs disjoint core and calibration rows")
    clf, calibration = dr.fit_fold(core, cal, FINAL_TRAIN_SEED)
    ordinary = inputs.ordinary
    return DynamicShadowPredictor(
        clf, calibration, ordinary.elo, ordinary.srv, ordinary.ctx, ordinary.meta,
        tour="wta", lower_elo=ordinary.lower_elo, lower_srv=ordinary.lower_srv,
        lower_ctx=ordinary.lower_ctx, dual_state_threshold=WTA_DUAL_STATE_GATE_THRESHOLD,
        dynamic_main=inputs.dynamic_main, dynamic_lower=inputs.dynamic_lower,
        shadow_provenance=provenance,
    )
