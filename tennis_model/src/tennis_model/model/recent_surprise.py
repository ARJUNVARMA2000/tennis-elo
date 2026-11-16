"""ATP opponent-adjusted recent form, emitted before each observed result."""

from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SURPRISE_FEATURE = "recent_surprise_diff"
SURPRISE_POLICY = "last-10-completed-90-day-elo-residual-sum-over-5-plus-n-pre-row-v1"


@dataclass
class RecentSurpriseState:
    recent: dict = field(default_factory=dict)
    through: pd.Timestamp | None = None
    policy: str = SURPRISE_POLICY

    def _date(self, value):
        date = pd.Timestamp(value)
        if pd.isna(date) or (self.through is not None and date < self.through):
            raise ValueError("recent surprise query/update precedes saved state")
        return date

    def value(self, player, as_of):
        date = self._date(as_of)
        values = [r for d, r in self.recent.get(player, ()) if 0 <= (date - d).days <= 90]
        return float(sum(values) / (5 + len(values)))

    def query(self, a, b, as_of):
        if a == b:
            raise ValueError("two distinct players required")
        return self.value(a, as_of) - self.value(b, as_of)

    def observe(self, winner, loser, date, p_winner, completed):
        date = self._date(date)
        if winner == loser or not np.isfinite(p_winner) or not 0 <= p_winner <= 1:
            raise ValueError("invalid pre-match probability or result")
        if completed:
            # Preserve the experiment's NumPy-scalar accumulation. Python 3.12+
            # uses compensated sum for native floats, which changes tiny residuals.
            p_winner = np.float64(p_winner)
            for player, residual in ((winner, 1 - p_winner), (loser, -(1 - p_winner))):
                self.recent.setdefault(player, deque(maxlen=10)).append((date, np.float64(residual)))
        self.through = date


def walk_recent_surprise(history, probabilities, state=None):
    if len(history) != len(probabilities):
        raise ValueError("probability/history lengths differ")
    state = RecentSurpriseState() if state is None else state
    values = []
    for row, p in zip(history.itertuples(), probabilities):
        values.append(state.query(row.winner_name, row.loser_name, row.date))
        state.observe(row.winner_name, row.loser_name, row.date, p, bool(row.completed))
    return state, pd.Series(values, index=history.index, name=SURPRISE_FEATURE, dtype=float)


def validate_surprise_state(state, cutoff):
    if (
        type(state) is not RecentSurpriseState
        or set(vars(state)) != {"recent", "through", "policy"}
        or state.policy != SURPRISE_POLICY
        or type(state.recent) is not dict
        or state.through != (pd.Timestamp(cutoff) if cutoff is not None else None)
    ):
        raise ValueError("invalid recent surprise state contract or cutoff")
    if state.through is not None and (type(state.through) is not pd.Timestamp or pd.isna(state.through)):
        raise ValueError("invalid recent surprise cutoff")
    for player, rows in state.recent.items():
        if type(player) is not str or not player or type(rows) is not deque or rows.maxlen != 10 or not rows:
            raise ValueError("invalid recent surprise history")
        previous = None
        for row in rows:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError("invalid recent surprise observation")
            date, residual = row
            if (
                type(date) is not pd.Timestamp
                or pd.isna(date)
                or state.through is None
                or date > state.through
                or (previous is not None and date < previous)
                or type(residual) is not np.float64
                or not np.isfinite(residual)
                or abs(residual) > 1
            ):
                raise ValueError("invalid recent surprise date/order/value")
            previous = date
