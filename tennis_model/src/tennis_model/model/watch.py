"""Transparent product ranking for upcoming matches worth watching.

This is not a learned model and does not change win probabilities.  Five bounded,
user-visible factors are combined with versioned editorial weights; missing optional
evidence earns no bonus and is carried as unavailable.
"""

from __future__ import annotations

from bisect import bisect_right
from math import isfinite

from ..config import ROUND_ORDER
from ..data.charting import STYLE_FEATURES, build_profiles, name_key

WATCH_SCHEMA = "watch-v1"
WATCH_WEIGHTS = {
    "closeness": 0.30,
    "quality": 0.25,
    "styleContrast": 0.15,
    "stakes": 0.15,
    "titleLeverage": 0.15,
}

_ROUND_SCORE = {
    "R128": 15.0, "R64": 25.0, "R32": 40.0, "R16": 55.0,
    "QF": 70.0, "SF": 85.0, "F": 100.0,
}


def _percentile(value: float, population: list[float]) -> float:
    if not population:
        return 0.0
    ordered = sorted(float(v) for v in population if isfinite(float(v)))
    if not ordered:
        return 0.0
    return 100.0 * bisect_right(ordered, float(value)) / len(ordered)


def _tier_score(level: object) -> float:
    text = str(level or "").lower()
    if "grand slam" in text:
        return 100.0
    if "finals" in text or "olympic" in text:
        return 95.0
    if "1000" in text or "masters" in text:
        return 90.0
    if "500" in text:
        return 70.0
    if "250" in text or "united cup" in text:
        return 55.0
    if "125" in text or "challenger" in text:
        return 35.0
    if "davis" in text or "bjk" in text:
        return 65.0
    return 45.0


def _scenario_leverage(rows: list[dict], scenario_index: dict | None,
                       scenario_shards: dict[str, dict] | None) -> dict[tuple, float]:
    """Map stable event + unordered pair + round to exact title-leverage values."""
    if not scenario_index or not scenario_shards:
        return {}
    generation = scenario_index.get("generation")
    allowed = {
        str(ref.get("espnId")): ref
        for ref in scenario_index.get("events") or []
        if ref.get("espnId") and ref.get("generation") == generation
    }
    out = {}
    for event_id, ref in allowed.items():
        shard = scenario_shards.get(str(ref.get("file")))
        if not shard or shard.get("generation") != generation:
            continue
        round_by_id = {
            match.get("id"): round_row.get("round")
            for round_row in shard.get("geometry") or []
            for match in round_row.get("matches") or []
        }
        for match_id, item in (shard.get("titleLeverage") or {}).items():
            a, b, value = item.get("playerA"), item.get("playerB"), item.get("value")
            if not a or not b or not isinstance(value, (int, float)):
                continue
            pair = tuple(sorted((name_key(a), name_key(b))))
            out[(event_id, pair, str(round_by_id.get(match_id) or ""))] = float(value)
    return out


def rank_upcoming(rows: list[dict], predictor, tour: str, *,
                  scenario_index: dict | None = None,
                  scenario_shards: dict[str, dict] | None = None) -> list[dict]:
    """Decorate rows with a watch score/rank without changing their input order."""
    if not rows:
        return rows
    if not hasattr(predictor, "elo"):
        return rows  # lightweight/legacy test doubles; production predictors always carry state
    active = list(getattr(predictor.elo, "overall", {}))
    surface_pop = {
        surface: [float(predictor.elo.blended(name, surface)) for name in active]
        for surface in {str(row.get("surface") or "Hard") for row in rows}
    }
    profiles = getattr(predictor, "_style_profiles_cache", None)
    if profiles is None:
        profiles = build_profiles(tour)
        predictor._style_profiles_cache = profiles
    style_pop = {
        key: [float(profile[key]) for profile in profiles.values()
              if isinstance(profile.get(key), (int, float)) and isfinite(float(profile[key]))]
        for key in STYLE_FEATURES
    }
    leverage = _scenario_leverage(rows, scenario_index, scenario_shards)

    for row in rows:
        a, b = row["playerA"], row["playerB"]
        p = float(row["pA"])
        surface = str(row.get("surface") or "Hard")
        close = max(0.0, min(100.0, 100.0 * (1.0 - 2.0 * abs(p - 0.5))))
        elo_a = float(predictor.elo.blended(a, surface))
        elo_b = float(predictor.elo.blended(b, surface))
        quality = (_percentile(elo_a, surface_pop[surface])
                   + _percentile(elo_b, surface_pop[surface])) / 2.0

        pa, pb = profiles.get(name_key(a)), profiles.get(name_key(b))
        style_diffs = []
        if pa and pb:
            for key in STYLE_FEATURES:
                va, vb = pa.get(key), pb.get(key)
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)) \
                        and isfinite(float(va)) and isfinite(float(vb)):
                    style_diffs.append(abs(
                        _percentile(float(va), style_pop[key])
                        - _percentile(float(vb), style_pop[key])
                    ))
        style_available = len(style_diffs) >= 4
        style_score = sum(style_diffs) / len(style_diffs) if style_available else 0.0

        round_score = _ROUND_SCORE.get(str(row.get("round")), 20.0)
        tier_score = _tier_score(row.get("level"))
        stakes = (round_score + tier_score) / 2.0

        event_id = str(row.get("espnId") or "")
        pair = tuple(sorted((name_key(a), name_key(b))))
        key = (event_id, pair, str(row.get("round") or ""))
        leverage_available = key in leverage
        leverage_score = max(0.0, min(100.0, 100.0 * leverage.get(key, 0.0)))

        values = {
            "closeness": close, "quality": quality, "styleContrast": style_score,
            "stakes": stakes, "titleLeverage": leverage_score,
        }
        total = sum(WATCH_WEIGHTS[name] * value for name, value in values.items())
        row["watch"] = {
            "schema": WATCH_SCHEMA,
            "score": round(total, 1),
            "weights": {key: int(value * 100) for key, value in WATCH_WEIGHTS.items()},
            "factors": {
                "closeness": {"score": round(close, 1), "available": True,
                              "detail": f"{max(p, 1-p):.1%}–{min(p, 1-p):.1%}"},
                "quality": {"score": round(quality, 1), "available": True,
                            "detail": {"eloA": round(elo_a, 1), "eloB": round(elo_b, 1)}},
                "styleContrast": {"score": round(style_score, 1),
                                  "available": style_available,
                                  "detail": {"dimensions": len(style_diffs)}},
                "stakes": {"score": round(stakes, 1), "available": True,
                           "detail": {"tier": round(tier_score, 1),
                                      "round": round(round_score, 1)}},
                "titleLeverage": {"score": round(leverage_score, 1),
                                  "available": leverage_available,
                                  "detail": "exact conditional title-distribution swing"
                                  if leverage_available else None},
            },
            "coverage": sum((True, True, style_available, True, leverage_available)),
        }

    ordered = sorted(
        range(len(rows)),
        key=lambda i: (
            -float(rows[i]["watch"]["score"]), str(rows[i].get("date") or ""),
            str(rows[i].get("espnId") or ""),
            -int(ROUND_ORDER.get(str(rows[i].get("round")), 0)),
            tuple(sorted((name_key(rows[i]["playerA"]), name_key(rows[i]["playerB"])))),
        ),
    )
    for rank, index in enumerate(ordered, start=1):
        rows[index]["watchRank"] = rank
    return rows
