"""Chronological league priors; unknown information times never admit statistics."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import SURFACES

PRIOR_POLICY = "available-date-strict-before-v1"
AVAILABILITY_BASES = ("observed", "played_date", "event_end")


@dataclass
class ServePriorState:
    points: float = 0.
    won: float = 0.
    surface_points: dict = field(default_factory=dict)
    surface_won: dict = field(default_factory=dict)
    last_admitted_cutoff: str | None = None
    policy: str = PRIOR_POLICY
    population_policy: str = "walk-population"
    excluded_unknown_time: int = 0
    excluded_invalid_stats: int = 0

    def before(self, cutoff=None):
        """Read without updating; explicit historical queries cannot precede saved evidence."""
        if cutoff is not None and self.last_admitted_cutoff is not None:
            if pd.Timestamp(cutoff).normalize() <= pd.Timestamp(self.last_admitted_cutoff):
                raise ValueError("prior snapshot contains evidence at or after the cutoff")
        avg = self.won / self.points if self.points else .62
        return avg, {s: self.surface_won.get(s, 0.) / self.surface_points[s]
                     if self.surface_points.get(s, 0.) else avg for s in SURFACES}

    def observe(self, surface, points, won, available_at):
        if surface not in SURFACES or not np.isfinite([points, won]).all() or not 0 <= won <= points or points <= 0:
            raise ValueError("invalid prior observation")
        date = pd.Timestamp(available_at).normalize()
        if pd.isna(date) or (self.last_admitted_cutoff is not None
                           and date < pd.Timestamp(self.last_admitted_cutoff)):
            raise ValueError("prior observations must have chronological information dates")
        self.points += float(points)
        self.won += float(won)
        self.surface_points[surface] = self.surface_points.get(surface, 0.) + float(points)
        self.surface_won[surface] = self.surface_won.get(surface, 0.) + float(won)
        self.last_admitted_cutoff = str(date.date())


def valid_stat_mask(df):
    fields = [f"{who}_{key}" for who in ("w", "l") for key in ("svpt", "1stWon", "2ndWon")]
    numeric = df[fields].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(numeric.to_numpy()).all(axis=1)
    for who in ("w", "l"):
        points = numeric[f"{who}_svpt"]
        first, second = numeric[f"{who}_1stWon"], numeric[f"{who}_2ndWon"]
        valid &= (points > 0) & (first >= 0) & (second >= 0) & (first + second <= points)
    return np.asarray(valid, dtype=bool) & df.has_stats.fillna(False).to_numpy(dtype=bool)


def prior_observations(df, state):
    """Explicit date+basis required; legacy tourney_date is deliberately insufficient.

    Producers must establish the bound: an observed receipt, a verified played day,
    or a verified event-end day. This reader never infers one from a source label.
    Date-only observations become available after that entire day.
    """
    valid = valid_stat_mask(df)
    complete = df.get("completed", pd.Series(False, index=df.index)).fillna(False).to_numpy(dtype=bool)
    eligible = valid & complete
    state.excluded_invalid_stats = int((df.has_stats.fillna(False).to_numpy(dtype=bool) & ~valid).sum())
    available = pd.to_datetime(df.get("stats_available_at", pd.Series(pd.NaT, index=df.index)),
                               errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    basis = df.get("stats_availability_basis", pd.Series("unknown", index=df.index))
    known = available.notna().to_numpy() & basis.isin(AVAILABILITY_BASES).to_numpy()
    # A claimed availability date before the supplied date is never a valid bound.
    known &= (available >= pd.to_datetime(df.date).dt.normalize()).to_numpy()
    state.excluded_unknown_time = int((eligible & ~known).sum())
    rows = []
    for i in np.flatnonzero(eligible & known):
        r = df.iloc[i]
        if r.surface_b not in SURFACES:
            continue
        rows.append((available.iloc[i], str(r.surface_b), float(r.w_svpt + r.l_svpt),
                     float(r.w_1stWon + r.w_2ndWon + r.l_1stWon + r.l_2ndWon)))
    return sorted(rows)
