"""Research temporal signals with explicit pre-row and saved-query state.

Uses the incumbent's retrospective row ordering, including prior rows sharing a
recorded date. This is not a claim that event-stamped records prove live availability.
Nothing here changes the production feature schema or saved predictor.
"""

from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

SIGNALS = ("recent_surprise_diff", "surface_recent_diff", "rank_trend_diff")


def valid_points(value):
    return value is not None and np.isfinite(value) and value > 0


@dataclass
class SignalState:
    recent: dict = field(default_factory=dict)
    exposure: dict = field(default_factory=dict)
    ranks: dict = field(default_factory=dict)
    through: pd.Timestamp | None = None

    def _date(self, as_of):
        date = pd.Timestamp(as_of)
        if pd.isna(date) or (self.through is not None and date < self.through):
            raise ValueError("signal query/update precedes saved state or has missing date")
        return date

    def _player(self, name, surface, date, current_points):
        recent = [r for d, r in self.recent.get(name, ())
                  if 0 <= (date - d).days <= 90]
        form = sum(recent) / (5 + len(recent))
        exposure = sum(s == surface for d, s in self.exposure.get(name, ())
                       if 0 <= (date - d).days <= 60)
        old = [p for d, p in self.ranks.get(name, ())
               if 90 <= (date - d).days <= 365]
        trend = (float(np.log1p(current_points) - np.log1p(old[-1]))
                 if old and valid_points(current_points) else None)
        return form, np.log1p(exposure), trend

    def query(self, a, b, surface, as_of, a_points=None, b_points=None):
        """Read-only query. Ranking inputs are explicit pre-match metadata."""
        date = self._date(as_of)
        if a == b:
            raise ValueError("two distinct players required")
        av = self._player(a, surface, date, a_points)
        bv = self._player(b, surface, date, b_points)
        return dict(zip(SIGNALS, [av[0] - bv[0], av[1] - bv[1],
                                 av[2] - bv[2] if av[2] is not None and bv[2] is not None else 0.0]))

    def observe(self, winner, loser, surface, date, p_winner, completed,
                winner_points=None, loser_points=None):
        date = self._date(date)
        if winner == loser or not np.isfinite(p_winner) or not 0 <= p_winner <= 1:
            raise ValueError("invalid result or pre-match probability")
        for name, points, residual in ((winner, winner_points, 1 - p_winner),
                                       (loser, loser_points, -(1 - p_winner))):
            if completed:
                self.recent.setdefault(name, deque(maxlen=10)).append((date, residual))
                exp = self.exposure.setdefault(name, deque())
                exp.append((date, surface))
                while exp and (date - exp[0][0]).days > 60:
                    exp.popleft()
            if valid_points(points):
                ranks = self.ranks.setdefault(name, deque())
                if ranks and ranks[-1][0] == date:
                    ranks.pop()
                ranks.append((date, float(points)))
                while ranks and (date - ranks[0][0]).days > 365:
                    ranks.popleft()
        self.through = date


def walk_signals(history, probabilities, state=None):
    """Emit before observing every row; caller supplies incumbent pre-match Elo p."""
    if len(history) != len(probabilities):
        raise ValueError("probability/history lengths differ")
    state = SignalState() if state is None else state
    values = []
    for row, p in zip(history.itertuples(), probabilities):
        values.append(state.query(row.winner_name, row.loser_name, row.surface_b, row.date,
                                  row.winner_rank_points, row.loser_rank_points))
        state.observe(row.winner_name, row.loser_name, row.surface_b, row.date, p,
                      bool(row.completed), row.winner_rank_points, row.loser_rank_points)
    return state, pd.DataFrame(values, index=history.index, columns=SIGNALS, dtype=float)


def attach_signals(features, history, signals):
    rows = history[history.draw_level.eq("main")].reset_index(drop=True)
    if len(rows) != len(features) or len(signals) != len(history):
        raise ValueError("signal population does not match feature frame")
    for col in ("winner_name", "loser_name", "date", "tourney_id", "round", "match_num"):
        if col in rows and col in features:
            pd.testing.assert_series_equal(rows[col], features[col].reset_index(drop=True),
                                           check_names=False, check_dtype=False)
    result = features.copy()
    result[list(SIGNALS)] = signals.loc[history.draw_level.eq("main")].to_numpy()
    return result
