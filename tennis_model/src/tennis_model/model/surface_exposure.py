"""The adopted WTA signal: completed same-surface exposure over 60 calendar days.

Queries precede observation in the declared retrospective row order. Equal-date
earlier rows count; this is not a claim about physical live-feed availability.
"""

from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SURFACE_FEATURE = "surface_recent_diff"
SURFACE_POLICY = "inclusive-60-day-completed-surface-count-pre-row-v1"
SURFACE_WINDOW_DAYS = 60


@dataclass
class SurfaceExposureState:
    exposure: dict = field(default_factory=dict)
    through: pd.Timestamp | None = None
    policy: str = SURFACE_POLICY
    population: str = "main"

    def _date(self, value):
        date = pd.Timestamp(value)
        if pd.isna(date) or (self.through is not None and date < self.through):
            raise ValueError("surface query/update precedes saved state or has missing date")
        return date

    def count(self, player, surface, as_of):
        date = self._date(as_of)
        return sum(s == surface for d, s in self.exposure.get(player, ())
                   if 0 <= (date-d).days <= SURFACE_WINDOW_DAYS)

    def query(self, a, b, surface, as_of):
        if a == b:
            raise ValueError("two distinct players required")
        return float(np.log1p(self.count(a, surface, as_of))
                     - np.log1p(self.count(b, surface, as_of)))

    def observe(self, winner, loser, surface, date, completed):
        date = self._date(date)
        if winner == loser:
            raise ValueError("two distinct players required")
        if completed:
            for name in (winner, loser):
                rows = self.exposure.setdefault(name, deque())
                rows.append((date, surface))
                while rows and (date-rows[0][0]).days > SURFACE_WINDOW_DAYS:
                    rows.popleft()
        self.through = date


def walk_surface_exposure(history, *, population="main"):
    if population not in {"main", "enriched"}:
        raise ValueError("invalid surface population")
    state = SurfaceExposureState(population=population)
    values = []
    for row in history.itertuples():
        values.append(state.query(row.winner_name, row.loser_name, row.surface_b, row.date))
        state.observe(row.winner_name, row.loser_name, row.surface_b, row.date, bool(row.completed))
    return state, pd.Series(values, index=history.index, name=SURFACE_FEATURE, dtype=float)


def validate_surface_state(state, cutoff, *, population="main"):
    """Validate the concrete saved history; malformed states cannot become neutral features."""
    if (type(state) is not SurfaceExposureState
            or set(vars(state)) != {"exposure", "through", "policy", "population"}
            or state.policy != SURFACE_POLICY or type(state.exposure) is not dict
            or population not in {"main", "enriched"} or state.population != population):
        raise ValueError("invalid surface state type/fields/policy")
    if state.through is not None and (type(state.through) is not pd.Timestamp or pd.isna(state.through)):
        raise ValueError("invalid surface state cutoff")
    if state.through != (pd.Timestamp(cutoff) if cutoff is not None else None):
        raise ValueError("surface cutoff differs from selected ordinary state")
    for player, rows in state.exposure.items():
        if (type(player) is not str or not player or type(rows) is not deque
                or rows.maxlen is not None or not rows or state.through is None):
            raise ValueError("invalid surface history")
        previous = None
        for row in rows:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError("invalid surface observation")
            date, surface = row
            if (type(date) is not pd.Timestamp or pd.isna(date) or date > state.through
                    or (previous is not None and date < previous)
                    or type(surface) is not str or not surface):
                raise ValueError("invalid surface date/order/value")
            previous = date
        if (rows[-1][0]-rows[0][0]).days > SURFACE_WINDOW_DAYS:
            raise ValueError("unpruned surface history")
