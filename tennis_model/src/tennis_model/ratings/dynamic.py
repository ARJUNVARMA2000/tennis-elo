"""Research-only filtered Gaussian strength; never imported by the production pipeline.

Global plus surface deviations provide partial pooling. A deterministic quadrature
update moment-matches a powered logistic likelihood and discards cross-player
posterior covariance. This approximation does not reconstruct real publication times;
the caller supplies the same declared retrospective ordering as the incumbent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import quad_vec

from ..config import SURFACES
from .elo import params_for

_NODES, _WEIGHTS = np.polynomial.hermite.hermgauss(64)
_WEIGHTS = _WEIGHTS / np.sqrt(np.pi)
_SHARING = np.diag([1.0, 0.25, 0.25, 0.25])
_DESIGNS = {s: np.array([1.0, float(i == 0), float(i == 1), float(i == 2)]) for i, s in enumerate(SURFACES)}
STATE_SCHEMA = "dynamic-strength-research-v1"
DYNAMIC_FEATURE = "logit_p_dynamic"
_IDENTITY = (
    "date",
    "winner_name",
    "loser_name",
    "round_order",
    "tour",
    "tourney_id",
    "round",
    "match_num",
    "source_match_id",
    "draw_level",
)


def _moments(mean: float, variance: float, weight: float):
    """Logistic-normal prediction and powered-likelihood posterior moments.

    Fixed Hermite integration is accurate for the narrow distributions. Broad
    distributions use adaptive normal-coordinate integration: a small fixed grid
    otherwise misses the sigmoid transition after long inactivity. The omitted
    normal tails beyond 12 standard deviations have mass below 4e-33.
    """
    if variance <= 4:
        points = mean + np.sqrt(2 * variance) * _NODES
        log_win = -np.logaddexp(0.0, -points)
        probability = float(_WEIGHTS @ np.exp(log_win))
        if weight == 0:
            return probability, mean, variance
        log_mass = np.log(_WEIGHTS) + weight * log_win
        mass = np.exp(log_mass - log_mass.max())
        mass /= mass.sum()
        posterior_mean = float(mass @ points)
        posterior_variance = float(mass @ (points - posterior_mean) ** 2)
    else:

        def integrand(z):
            log_win = -np.logaddexp(0.0, -(mean + np.sqrt(variance) * z))
            likelihood = np.exp(weight * log_win)
            density = np.exp(-z * z / 2) / np.sqrt(2 * np.pi)
            return density * np.array([np.exp(log_win), likelihood, z * likelihood, z * z * likelihood])

        moments, error = quad_vec(integrand, -12, 12, epsabs=1e-11, epsrel=1e-11)
        probability, mass, first, second = moments
        if not np.isfinite(moments).all() or mass <= 1e-12 or error > 1e-8:
            raise ValueError("dynamic quadrature cannot resolve the projected likelihood")
        posterior_mean = mean + np.sqrt(variance) * first / mass
        posterior_variance = variance * (second / mass - (first / mass) ** 2)
    if not np.isfinite([probability, posterior_mean, posterior_variance]).all() or posterior_variance <= 0:
        raise ValueError("invalid dynamic quadrature moments")
    return float(probability), float(posterior_mean), float(posterior_variance)


def _day(value) -> int:
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("dynamic state requires a finite date")
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("UTC").tz_localize(None)
    return int(stamp.to_datetime64().astype("datetime64[D]").astype(int))


@dataclass(frozen=True)
class DynamicParams:
    sigma0: float = 1.0
    q: float = 0.0001

    def __post_init__(self):
        if not np.isfinite([self.sigma0, self.q]).all() or self.sigma0 <= 0 or self.q < 0:
            raise ValueError("invalid dynamic prior/transition parameters")


@dataclass
class PlayerGaussian:
    mean: np.ndarray
    covariance: np.ndarray
    day: int
    matches: int


@dataclass
class DynamicState:
    params: DynamicParams = field(default_factory=DynamicParams)
    players: dict[str, PlayerGaussian] = field(default_factory=dict)
    last_day: int | None = None

    def _view(self, name: str, day: int) -> PlayerGaussian:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("dynamic player name is empty")
        old = self.players.get(name)
        if old is None:
            return PlayerGaussian(np.zeros(4), self.params.sigma0**2 * _SHARING, day, 0)
        if day < old.day:
            raise ValueError("dynamic player query precedes its observations")
        return PlayerGaussian(
            old.mean.copy(), old.covariance + self.params.q * (day - old.day) * _SHARING, day, old.matches
        )

    def view(self, name: str, as_of) -> PlayerGaussian:
        day = _day(as_of)
        if self.last_day is not None and day < self.last_day:
            raise ValueError("dynamic query precedes the saved state cutoff")
        return self._view(name, day)

    def _pair(self, a, b, surface, as_of):
        if a == b:
            raise ValueError("dynamic matchup requires different players")
        if surface not in _DESIGNS:
            raise ValueError("unknown dynamic surface")
        day = _day(as_of)
        if self.last_day is not None and day < self.last_day:
            raise ValueError("dynamic query precedes the saved state cutoff")
        left, right = self._view(a, day), self._view(b, day)
        design = _DESIGNS[surface]
        mean = float(design @ (left.mean - right.mean))
        variance = float(design @ (left.covariance + right.covariance) @ design)
        if not np.isfinite([mean, variance]).all() or variance <= 0:
            raise ValueError("invalid dynamic projected moments")
        return day, left, right, design, mean, variance

    def win_prob(self, a: str, b: str, surface: str = "Hard", *, as_of) -> float:
        *_, mean, variance = self._pair(a, b, surface, as_of)
        return _moments(mean, variance, 0)[0]

    def observe(self, winner: str, loser: str, surface: str, *, as_of, weight: float = 1.0) -> None:
        if not np.isfinite(weight) or weight < 0:
            raise ValueError("invalid dynamic observation weight")
        day, left, right, design, mean, variance = self._pair(winner, loser, surface, as_of)
        if weight == 0:
            return
        _, posterior_mean, posterior_variance = _moments(mean, variance, weight)
        mean_scale = (posterior_mean - mean) / variance
        variance_scale = (posterior_variance - variance) / variance**2
        for name, old, direction in ((winner, left, 1.0), (loser, right, -1.0)):
            projection = old.covariance @ design
            covariance = old.covariance + variance_scale * np.outer(projection, projection)
            covariance = 0.5 * (covariance + covariance.T)
            self.players[name] = PlayerGaussian(
                old.mean + direction * projection * mean_scale, covariance, day, old.matches + 1
            )
        self.last_day = day

    def to_dict(self) -> dict:
        return {
            "schema": STATE_SCHEMA,
            "params": asdict(self.params),
            "lastDay": self.last_day,
            "players": {
                name: {"mean": p.mean.tolist(), "covariance": p.covariance.tolist(), "day": p.day, "matches": p.matches}
                for name, p in sorted(self.players.items())
            },
        }

    @classmethod
    def from_dict(cls, value: dict) -> DynamicState:
        if (
            type(value) is not dict
            or set(value) != {"schema", "params", "lastDay", "players"}
            or value["schema"] != STATE_SCHEMA
            or type(value["players"]) is not dict
        ):
            raise ValueError("invalid research dynamic state schema")
        if type(value["params"]) is not dict or set(value["params"]) != {"sigma0", "q"}:
            raise ValueError("invalid research dynamic parameters")
        state = cls(DynamicParams(**value["params"]))
        last = value["lastDay"]
        if last is not None and type(last) is not int:
            raise ValueError("invalid dynamic cutoff")
        state.last_day = last
        for name, p in value["players"].items():
            if (
                not isinstance(name, str)
                or not name.strip()
                or type(p) is not dict
                or set(p) != {"mean", "covariance", "day", "matches"}
            ):
                raise ValueError("invalid dynamic player record")
            mean, cov = np.asarray(p["mean"], dtype=float), np.asarray(p["covariance"], dtype=float)
            if (
                mean.shape != (4,)
                or cov.shape != (4, 4)
                or not np.isfinite(mean).all()
                or not np.isfinite(cov).all()
                or not np.allclose(cov, cov.T, rtol=0, atol=1e-12)
                or np.linalg.eigvalsh(cov).min() <= 0
                or type(p["matches"]) is not int
                or p["matches"] < 1
                or type(p["day"]) is not int
                or last is None
                or p["day"] > last
            ):
                raise ValueError("invalid dynamic player moments/cutoff")
            state.players[name] = PlayerGaussian(mean.copy(), cov.copy(), p["day"], p["matches"])
        return state

    def save(self, path) -> None:
        value = self.to_dict()
        self.from_dict(value)
        with Path(path).open("x") as f:
            json.dump(value, f, sort_keys=True, allow_nan=False)
            f.write("\n")

    @classmethod
    def load(cls, path) -> DynamicState:
        return cls.from_dict(json.loads(Path(path).read_text()))


def run_dynamic(
    frame: pd.DataFrame, params: DynamicParams | None = None, *, tour: str = "wta"
) -> tuple[DynamicState, pd.DataFrame]:
    """Emit pre-row probability from exactly the supplied history; no state smoothing."""
    if tour != "wta":
        raise ValueError("initial dynamic research is registered for WTA only")
    required = {"date", "winner_name", "loser_name", "surface_b", "completed", "tier_k"}
    if not required <= set(frame):
        raise ValueError("dynamic walk is missing required match columns")
    if frame.date.isna().any() or not frame.date.is_monotonic_increasing:
        raise ValueError("dynamic history must have finite nondecreasing dates")
    from ..data.chronology import require_chronology

    require_chronology(frame)
    state = DynamicState(params or DynamicParams())
    elo_params = params_for(tour)
    probabilities = np.empty(len(frame))
    for i, row in enumerate(frame.itertuples(index=False)):
        probabilities[i] = state.win_prob(row.winner_name, row.loser_name, row.surface_b, as_of=row.date)
        walkover = bool(getattr(row, "walkover", False))
        if elo_params.skip_walkovers and walkover:
            continue
        weight = float(row.tier_k)
        if not row.completed and not walkover:
            weight *= elo_params.ret_k_mult
        state.observe(row.winner_name, row.loser_name, row.surface_b, as_of=row.date, weight=weight)
    clipped = np.clip(probabilities, 1e-12, 1 - 1e-12)
    features = frame[[c for c in _IDENTITY if c in frame]].copy()
    features["p_dynamic"] = probabilities
    features[DYNAMIC_FEATURE] = np.log(clipped / (1 - clipped))
    return state, features


def attach_dynamic(
    base: pd.DataFrame,
    main_dynamic: pd.DataFrame | None,
    lower_dynamic: pd.DataFrame | None = None,
    *,
    enabled: bool = True,
) -> pd.DataFrame:
    """Attach the single experimental signal to an already row-aligned incumbent frame."""
    if not enabled:
        return base.copy()
    if main_dynamic is None or not base.index.equals(main_dynamic.index):
        raise ValueError("dynamic main rows are not aligned")

    def check_identity(other):
        for column in _IDENTITY:
            if column in base and (column not in other or not base[column].equals(other[column])):
                raise ValueError(f"dynamic rows differ at {column}")

    check_identity(main_dynamic)
    values = main_dynamic[DYNAMIC_FEATURE].to_numpy(copy=True)
    if "uses_lower_state" in base:
        if lower_dynamic is None or not base.index.equals(lower_dynamic.index):
            raise ValueError("dynamic lower rows are not aligned")
        check_identity(lower_dynamic)
        mask = base.uses_lower_state.to_numpy(dtype=bool)
        values[mask] = lower_dynamic.loc[mask, DYNAMIC_FEATURE].to_numpy()
    if not np.isfinite(values).all():
        raise ValueError("non-finite dynamic signal")
    out = base.copy()
    out[DYNAMIC_FEATURE] = values
    return out
