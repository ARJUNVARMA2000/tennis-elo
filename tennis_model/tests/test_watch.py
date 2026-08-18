from __future__ import annotations

from types import SimpleNamespace

import tennis_model.model.watch as watch


class _Elo:
    overall = {"A": 1, "B": 1, "C": 1, "D": 1}

    def blended(self, name, surface):
        return {"A": 1900, "B": 1850, "C": 1600, "D": 1500}[name]


def _row(a, b, p, *, event="One", event_id="e1", rnd="SF", level="ATP 500"):
    return {
        "event": event, "espnId": event_id, "date": "2026-08-18", "round": rnd,
        "surface": "Hard", "bestOf": 3, "level": level,
        "playerA": a, "playerB": b, "pA": p,
    }


def _styles():
    return {
        watch.name_key(name): {key: base + i * 0.01 for i, key in enumerate(watch.STYLE_FEATURES)}
        for name, base in (("A", 0.8), ("B", 0.2), ("C", 0.5), ("D", 0.48))
    }


def test_watch_score_ranks_without_reordering_and_exposes_factors(monkeypatch):
    monkeypatch.setattr(watch, "build_profiles", lambda tour: _styles())
    predictor = SimpleNamespace(elo=_Elo())
    rows = [_row("C", "D", 0.51, event="Soon"), _row("A", "B", 0.53, event="Big")]
    original = list(rows)
    out = watch.rank_upcoming(rows, predictor, "atp")
    assert out == original  # same objects/order; chronology is not replaced by the ranking
    assert out[1]["watchRank"] == 1
    assert out[1]["watch"]["factors"]["styleContrast"]["available"] is True
    assert out[0]["watch"]["factors"]["titleLeverage"]["available"] is False
    assert set(out[0]["watch"]["factors"]) == set(watch.WATCH_WEIGHTS)


def test_exact_title_leverage_joins_by_generation_event_pair_and_round(monkeypatch):
    monkeypatch.setattr(watch, "build_profiles", lambda tour: _styles())
    predictor = SimpleNamespace(elo=_Elo())
    row = _row("A", "B", 0.5)
    index = {"generation": "g1", "events": [{
        "espnId": "e1", "file": "scenario-e1.json", "generation": "g1",
    }]}
    shard = {
        "generation": "g1",
        "geometry": [{"round": "SF", "matches": [{"id": "e1:r0:m0"}]}],
        "titleLeverage": {"e1:r0:m0": {"playerA": "A", "playerB": "B", "value": 0.42}},
    }
    out = watch.rank_upcoming(
        [row], predictor, "atp", scenario_index=index,
        scenario_shards={"scenario-e1.json": shard},
    )[0]
    factor = out["watch"]["factors"]["titleLeverage"]
    assert factor == {"score": 42.0, "available": True,
                      "detail": "exact conditional title-distribution swing"}

    stale = {**shard, "generation": "old"}
    out2 = watch.rank_upcoming(
        [_row("A", "B", 0.5)], predictor, "atp", scenario_index=index,
        scenario_shards={"scenario-e1.json": stale},
    )[0]
    assert out2["watch"]["factors"]["titleLeverage"]["available"] is False


def test_missing_style_gets_no_silent_average_bonus(monkeypatch):
    monkeypatch.setattr(watch, "build_profiles", lambda tour: {})
    row = watch.rank_upcoming([_row("A", "B", 0.5)], SimpleNamespace(elo=_Elo()), "atp")[0]
    factor = row["watch"]["factors"]["styleContrast"]
    assert factor["available"] is False and factor["score"] == 0.0
    assert row["watch"]["coverage"] == 3
