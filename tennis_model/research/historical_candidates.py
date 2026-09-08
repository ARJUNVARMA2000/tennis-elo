"""Two registered historical mechanisms; no production default is changed.

The absence transform is the same function for historical and saved-state queries.
The capped point state inherits the existing prediction-time read/decay/probability
methods, so saved state and walk-time scores share their entire query path.
"""

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd
from tennis_model.eval.protocol import require_paired
from tennis_model.model.features import _logit
from tennis_model.points.serve_return import (
    ServeReturnParams,
    ServeReturnState,
    run_serve_return,
    sr_params_for,
)

ABSENCE_COLUMNS = ["rest_diff", "log_days_since_diff", "layoff_flag_diff"]


@dataclass
class AppearanceState:
    seen: set = field(default_factory=set)
    through: pd.Timestamp | None = None

    def unknown(self, a, b, date):
        date = pd.Timestamp(date)
        if pd.isna(date) or (self.through is not None and date < self.through):
            raise ValueError("appearance state cannot query before its stored history")
        return a not in self.seen or b not in self.seen

    def observe(self, a, b, date):
        self.unknown(a, b, date)
        if not isinstance(a, str) or not isinstance(b, str) or not a or not b or a == b:
            raise ValueError("invalid appearance identity")
        self.seen.update([a, b])
        self.through = pd.Timestamp(date)

    def transform_query(self, frame, a, b, date):
        if len(frame) != 1:
            raise ValueError("one matchup required")
        return neutral_absence(frame, [self.unknown(a, b, date)])


def appearance_flags(history, state=None):
    state = AppearanceState() if state is None else state
    flags = []
    for row in history.itertuples(index=False):
        flags.append(state.unknown(row.winner_name, row.loser_name, row.date))
        state.observe(row.winner_name, row.loser_name, row.date)
    return state, np.asarray(flags, dtype=bool)


def neutral_absence(frame, unknown):
    unknown = np.asarray(unknown)
    if unknown.dtype != bool or unknown.shape != (len(frame),):
        raise ValueError("explicit aligned boolean appearance mask required")
    out = frame.copy()
    out.loc[unknown, ABSENCE_COLUMNS] = 0
    return out


@dataclass(frozen=True)
class CappedParams(ServeReturnParams):
    cap: float = 80.0

    def __post_init__(self):
        if isinstance(self.cap, bool) or not np.isfinite(self.cap) or self.cap <= 0:
            raise ValueError("cap must be finite and positive")


class CappedServeState(ServeReturnState):
    def __post_init__(self):
        super().__post_init__()
        if not isinstance(self.params, CappedParams):
            raise ValueError("capped state requires explicit capped parameters")

    def _add(self, name, surf, svpt, adj_spw, rpt, adj_rpw):
        # Rates are unchanged; only the observation's evidence mass is bounded.
        super()._add(name, surf, min(svpt, self.params.cap), adj_spw, min(rpt, self.params.cap), adj_rpw)


def capped_walk(history, tour, cap, *, baseline=None):
    params = CappedParams(**asdict(sr_params_for(tour)), cap=cap)
    return run_serve_return(history, params=params, baseline_df=baseline, state_class=CappedServeState)


def attach_capped(features, history, signal):
    main = history.draw_level.eq("main").to_numpy()
    if len(signal) != len(history):
        raise ValueError("point walk is not aligned with history")
    require_paired(
        features, history.loc[main].assign(round_order=features.round_order.to_numpy()).reset_index(drop=True)
    )
    s = signal.loc[main].reset_index(drop=True)
    out = features.copy()
    out["p_point"] = s.p_point.to_numpy()
    out["logit_p_point"] = _logit(s.p_point.to_numpy())
    out["serve_skill_diff"] = (s.w_serve_skill - s.l_serve_skill).to_numpy()
    out["return_skill_diff"] = (s.w_return_skill - s.l_return_skill).to_numpy()
    out["log_min_srv_pts"] = np.log1p(np.minimum(s.w_srv_pts, s.l_srv_pts)).to_numpy()
    return out
