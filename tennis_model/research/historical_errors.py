"""Fixed, tune-only error diagnostics from verified winner-oriented OOS records."""

import numpy as np
import pandas as pd
from tennis_model.data.names import name_key
from tennis_model.eval.protocol import require_paired

SLICE_SPEC = {
    "favorite_probability": [0.5, 0.6, 0.7, 0.8, 0.9, 1.000000001],
    "player_a_probability": [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.000000001],
    "experience": [0, 32, 128, 512, float("inf")],
    "inactivity_days": [0, 14, 60, 120, 365, float("inf")],
    "prior_serve_points": [0, 1, 100, 1000, 10000, float("inf")],
    "surface": ["hard", "clay", "grass"],
    "round": ["R128", "R64", "R32", "R16", "QF", "SF", "F", "RR"],
    "tier_k": [0, 0.9, 1.1, 1.4, float("inf")],
}


def oriented(frame):
    if frame.empty or not frame.year.between(2010, 2019).all():
        raise ValueError("diagnostics require nonempty 2010-2019 rows only")
    require_paired(frame, frame)
    a = frame.winner_name.map(name_key)
    b = frame.loser_name.map(name_key)
    if a.eq(b).any() or a.eq("").any() or b.eq("").any():
        raise ValueError("invalid canonical player identity")
    p = frame.p_combiner.to_numpy(dtype=float)
    if not np.isfinite(p).all() or not ((p > 0) & (p < 1)).all():
        raise ValueError("invalid probabilities")
    y = a.lt(b).to_numpy(dtype=float)
    pa = np.where(y, p, 1 - p)
    confidence = np.maximum(pa, 1 - pa)
    correct = np.where(pa >= 0.5, y, 1 - y)
    return pd.DataFrame(
        {
            "year": frame.year.to_numpy(),
            "p_a": pa,
            "y_a": y,
            "confidence": confidence,
            "correct": correct,
            "logloss": -np.log(p),
            "brier": (1 - p) ** 2,
        }
    )


def masks(frame, observations):
    result = {"all": np.ones(len(frame), dtype=bool)}
    values = {
        "favorite_probability": observations.confidence,
        "player_a_probability": observations.p_a,
        "experience": np.expm1(frame.log_min_matches),
        "inactivity_days": frame.max_days_since,
        "prior_serve_points": np.expm1(frame.log_min_srv_pts),
        "tier_k": frame.tier_k,
    }
    for name, series in values.items():
        series = np.asarray(series, dtype=float)
        # Undo tiny exp(log1p(n)) floating error around count boundaries.
        if name in ("experience", "prior_serve_points"):
            series = np.round(series, 7)
        edges = SLICE_SPEC[name]
        for low, high in zip(edges, edges[1:]):
            result[f"{name}:[{low},{high})"] = (series >= low) & (series < high)
        result[f"{name}:missing"] = ~np.isfinite(series)
    known = np.zeros(len(frame), bool)
    for name in SLICE_SPEC["surface"]:
        mask = frame[f"surf_{name}"].eq(1).to_numpy()
        result[f"surface:{name}"] = mask
        known |= mask
    result["surface:other"] = ~known
    for value in SLICE_SPEC["round"]:
        result[f"round:{value}"] = frame["round"].eq(value).to_numpy()
    result["round:other"] = ~frame["round"].isin(SLICE_SPEC["round"]).to_numpy()
    lower = frame.uses_lower_state.to_numpy(dtype=bool)
    result["state:enriched"] = lower
    result["state:main"] = ~lower
    return result


def summarize(obs, total):
    if obs.empty:
        return {"n": 0, "years": 0}
    residual = obs.y_a - obs.p_a
    favorite_residual = obs.correct - obs.confidence
    return {
        "n": len(obs),
        "years": obs.year.nunique(),
        "meanProbabilityA": obs.p_a.mean(),
        "observedWinRateA": obs.y_a.mean(),
        "calibrationResidualA": residual.mean(),
        "meanFavoriteProbability": obs.confidence.mean(),
        "accuracy": obs.correct.mean(),
        "favoriteResidual": favorite_residual.mean(),
        "favoriteResidualNaiveSE": favorite_residual.std(ddof=1) / np.sqrt(len(obs)) if len(obs) > 1 else np.nan,
        "logloss": obs.logloss.mean(),
        "brier": obs.brier.mean(),
        "lossContribution": obs.logloss.sum() / total,
    }


def diagnose(frame):
    frame = frame.reset_index(drop=True)
    obs = oriented(frame)
    rows = []
    for label, mask in masks(frame, obs).items():
        for year in ["tune", *range(2010, 2020)]:
            selected = mask if year == "tune" else mask & obs.year.eq(year).to_numpy()
            rows.append({"slice": label, "window": str(year), **summarize(obs.loc[selected], len(obs))})
    return pd.DataFrame(rows)
