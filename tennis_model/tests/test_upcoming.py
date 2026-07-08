"""Shared upcoming-matchup enrichment — fully synthetic (no model, no network).

Runnable directly (`python tests/test_upcoming.py`) or under pytest. Pins the primitive
that BOTH the forecast log (eval.track) and the web schedule board (model.export) depend
on: resolve ESPN names -> canonical, infer the event's surface/best-of, price with
win_prob, and drop matchups the model can't speak to (unknown or self-paired players).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.model.upcoming import enrich_upcoming, event_attrs

_ELO = {"Carlos Alcaraz": 2100.0, "Jannik Sinner": 2080.0, "Novak Djokovic": 1990.0}


class _Elo:
    overall = _ELO


class _Pred:
    """Logistic-Elo stand-in: P(a beats b) from the rating gap, orientation-aware."""
    elo = _Elo()

    def win_prob(self, a, b, surface="Hard", best_of=3, event=None):
        return 1.0 / (1.0 + 10.0 ** (-(_ELO[a] - _ELO[b]) / 400.0))


def _df():
    # a two-row match frame the enricher infers surface/best-of from
    return pd.DataFrame([{"tourney_name": "Wimbledon", "surface_b": "Grass", "best_of": 5}] * 2)


def _up(rows):
    return pd.DataFrame(rows, columns=["tourney_name", "tourney_date", "round", "playerA", "playerB"])


def test_enrich_resolves_infers_and_prices():
    out = enrich_upcoming(_Pred(), _df(),
                          _up([("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Novak Djokovic")]))
    assert len(out) == 1
    r = out[0]
    assert (r["playerA"], r["playerB"], r["round"]) == ("Carlos Alcaraz", "Novak Djokovic", "SF")
    assert r["surface"] == "Grass" and r["best_of"] == 5          # inferred from the event rows
    assert 0.5 < r["pA"] < 1.0                                    # Alcaraz favoured over Djokovic


def test_name_resolution_and_month_fallback():
    # lower-case names resolve (accent/case-insensitive); an event absent from the frame
    # falls back to the season-by-month surface (July -> Grass) and best-of-3.
    out = enrich_upcoming(_Pred(), _df(),
                          _up([("Mystery Cup", "2026-07-10", "F", "carlos alcaraz", "jannik sinner")]))
    assert len(out) == 1 and out[0]["surface"] == "Grass" and out[0]["best_of"] == 3


def test_drops_unknown_and_self_pairs():
    out = enrich_upcoming(_Pred(), _df(), _up([
        ("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Nobody McUnknown"),  # unknown B
        ("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Carlos Alcaraz"),     # self-pair
    ]))
    assert out == []


def test_empty_and_none_upcoming():
    assert enrich_upcoming(_Pred(), _df(), None) == []
    assert enrich_upcoming(_Pred(), _df(), _up([])) == []


def test_pa_is_orientation_correct():
    # flipping A/B flips pA to (1 - pA): the two sides are a consistent single number
    fwd = enrich_upcoming(_Pred(), _df(),
                          _up([("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Novak Djokovic")]))[0]["pA"]
    rev = enrich_upcoming(_Pred(), _df(),
                          _up([("Wimbledon", "2026-07-10", "SF", "Novak Djokovic", "Carlos Alcaraz")]))[0]["pA"]
    assert abs(fwd + rev - 1.0) < 1e-9


def test_event_attrs_infers_else_none():
    assert event_attrs(_df(), "Wimbledon") == ("Grass", 5)
    assert event_attrs(_df(), "Some Other Event") == (None, None)
    assert event_attrs(pd.DataFrame(), "Wimbledon") == (None, None)   # no columns -> no crash


if __name__ == "__main__":
    test_enrich_resolves_infers_and_prices()
    test_name_resolution_and_month_fallback()
    test_drops_unknown_and_self_pairs()
    test_empty_and_none_upcoming()
    test_pa_is_orientation_correct()
    test_event_attrs_infers_else_none()
    print("\nALL PASSED")
