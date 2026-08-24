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

from tennis_model.data.bracket_rounds import (
    build_bracket_round_index,
    unique_bracket_round,
)
from tennis_model.model.upcoming import enrich_upcoming, event_attrs

# The events below resolve surface without any on-disk Wikipedia cache: "Wimbledon" via the
# archive tier (surface_b in _df()), and the absent "Mystery Cup" via the season-by-month
# fallback — so these stay hermetic; the wiki tier has dedicated coverage in test_surface.py.
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
                          _up([("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Novak Djokovic")]), "atp")
    assert len(out) == 1
    r = out[0]
    assert (r["playerA"], r["playerB"], r["round"]) == ("Carlos Alcaraz", "Novak Djokovic", "SF")
    assert r["surface"] == "Grass" and r["best_of"] == 5          # inferred from the event rows
    assert 0.5 < r["pA"] < 1.0                                    # Alcaraz favoured over Djokovic


def test_enrich_passes_stable_event_id_to_tier_resolution(monkeypatch):
    from tennis_model.model import upcoming as upcoming_module

    seen = []

    def level(tour, event, archive_level=None, event_id=None):
        seen.append((tour, event, event_id))
        return "Masters 1000"

    monkeypatch.setattr(upcoming_module, "resolve_level", level)
    rows = pd.DataFrame([{
        "tourney_name": "Toronto", "espn_id": "421-2026",
        "tourney_date": "2026-08-04", "round": "R64",
        "playerA": "Carlos Alcaraz", "playerB": "Novak Djokovic",
    }])
    out = enrich_upcoming(_Pred(), _df(), rows, "atp")
    assert out[0]["level"] == "Masters 1000"
    assert seen == [("atp", "Toronto", "421-2026")]


def test_enrich_reconciles_round_before_prediction_context(capsys):
    """The ordered bracket outranks ESPN's lagging label before context is assembled."""
    calls = []

    class _ContextPred(_Pred):
        def prediction_components(self, a, b, **kwargs):
            calls.append(("components", kwargs["round_order"]))
            return {"eloBlend": 0.61, "pointModel": 0.62, "combiner": 0.63}

        def prediction_evidence(self, a, b, **kwargs):
            calls.append(("evidence", kwargs["round_order"]))
            return {"roundOrder": kwargs["round_order"]}

    brackets = [{
        "espnId": "363-2026",
        "rounds": [{
            "round": "R32",
            "matches": [{"a": "Carlos Alcaraz", "b": "Novak Djokovic"}],
        }],
    }]
    rows = pd.DataFrame([{
        "tourney_name": "Winston-Salem Open", "espn_id": "363-2026",
        "tourney_date": "2026-08-23", "round": "R64",
        "playerA": "Carlos Alcaraz", "playerB": "Novak Djokovic",
    }])

    out = enrich_upcoming(
        _ContextPred(), _df(), rows, "atp",
        bracket_index=build_bracket_round_index(brackets),
    )

    assert out[0]["round"] == "R32"
    assert calls == [("components", 3), ("evidence", 3)]
    logged = capsys.readouterr().out
    assert "upcoming 363-2026" in logged and "R64->R32" in logged


def test_bracket_round_reconciliation_fails_closed():
    brackets = [{
        "espnId": "363-2026",
        "rounds": [
            {"round": "R32", "matches": [
                {"a": "Diego Dedura-Palomero", "b": "Novak Djokovic"},
                {"a": "Qualifier 1", "b": "Jannik Sinner"},
                {"a": "Novak Djokovic", "b": "Jannik Sinner"},
                {"a": "Jannik Sinner", "b": "Novak Djokovic"},
            ]},
            # The repeated pair makes this event/pair ambiguous by construction.
            {"round": "SF", "matches": [
                {"a": "Carlos Alcaraz", "b": "Jannik Sinner"},
            ]},
            {"round": "F", "matches": [
                {"a": "Jannik Sinner", "b": "Carlos Alcaraz"},
            ]},
        ],
    }]
    index = build_bracket_round_index(brackets)

    # Explicit aliases and orientation both canonicalize to one exact pair.
    assert unique_bracket_round(
        index, "363-2026", "Novak Djokovic", "Diego Dedura") == "R32"
    # Missing id, mismatched id/pair, placeholders, self-pairs and multi-round matches
    # produce no evidence; callers retain the provider label for the output gate to audit.
    assert unique_bracket_round(index, None, "Diego Dedura", "Novak Djokovic") is None
    assert unique_bracket_round(index, float("nan"), "Diego Dedura", "Novak Djokovic") is None
    assert unique_bracket_round(index, "other", "Diego Dedura", "Novak Djokovic") is None
    assert unique_bracket_round(index, "363-2026", "Nobody", "Novak Djokovic") is None
    assert unique_bracket_round(index, "363-2026", "Qualifier 1", "Jannik Sinner") is None
    assert unique_bracket_round(index, "363-2026", "Jannik Sinner", "Jannik Sinner") is None
    assert unique_bracket_round(index, "363-2026", "Novak Djokovic", "Jannik Sinner") is None
    assert unique_bracket_round(index, "363-2026", "Carlos Alcaraz", "Jannik Sinner") is None


def test_name_resolution_and_month_fallback():
    # lower-case names resolve (accent/case-insensitive); an event absent from the frame
    # falls back to the season-by-month surface (July -> Grass) and best-of-3.
    out = enrich_upcoming(_Pred(), _df(),
                          _up([("Mystery Cup", "2026-07-10", "F", "carlos alcaraz", "jannik sinner")]), "atp")
    assert len(out) == 1 and out[0]["surface"] == "Grass" and out[0]["best_of"] == 3


def test_drops_unknown_and_self_pairs():
    out = enrich_upcoming(_Pred(), _df(), _up([
        ("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Nobody McUnknown"),  # unknown B
        ("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Carlos Alcaraz"),     # self-pair
    ]), "atp")
    assert out == []


def test_empty_and_none_upcoming():
    assert enrich_upcoming(_Pred(), _df(), None, "atp") == []
    assert enrich_upcoming(_Pred(), _df(), _up([]), "atp") == []


def test_pa_is_orientation_correct():
    # flipping A/B flips pA to (1 - pA): the two sides are a consistent single number
    fwd = enrich_upcoming(_Pred(), _df(),
                          _up([("Wimbledon", "2026-07-10", "SF", "Carlos Alcaraz", "Novak Djokovic")]), "atp")[0]["pA"]
    rev = enrich_upcoming(_Pred(), _df(),
                          _up([("Wimbledon", "2026-07-10", "SF", "Novak Djokovic", "Carlos Alcaraz")]), "atp")[0]["pA"]
    assert abs(fwd + rev - 1.0) < 1e-9


def test_event_attrs_infers_else_none():
    assert event_attrs(_df(), "Wimbledon") == ("Grass", 5)
    assert event_attrs(_df(), "Some Other Event") == (None, None)
    assert event_attrs(pd.DataFrame(), "Wimbledon") == (None, None)   # no columns -> no crash


def test_upcoming_dedup_keys_on_the_event_id_when_both_rows_have_one(tmp_path, monkeypatch):
    """The ESPN feed and the Wikipedia overlay name the same event differently, so the same
    first-round matchup only ever collapsed when the two happened to agree on the title."""
    from tennis_model.model import upcoming as up

    from tennis_model.data import draws

    # `load_upcoming` imports the draw overlay INSIDE the function, so it must be patched
    # on its own module — patching the attribute on `upcoming` is a silent no-op.
    monkeypatch.setattr(up, "live_dir", lambda tour: tmp_path)

    def _overlay(rows):
        monkeypatch.setattr(
            draws,
            "tournament_draw_upcoming_rows",
            lambda tour, *, status=None: rows,
        )

    (tmp_path / "upcoming.csv").write_text(
        "tourney_name,espn_id,tourney_date,round,playerA,playerB\n"
        "Mubadala DC Open,888-2026,2026-07-27,R32,A Player,B Player\n", encoding="utf-8")
    # the wiki overlay carries the SAME matchup under the older sponsor title
    _overlay([{"tourney_name": "Mubadala Citi DC Open", "espn_id": "888-2026",
               "tourney_date": "2026-07-27", "round": "R32",
               "playerA": "A Player", "playerB": "B Player"}])
    df = up.load_upcoming("atp")
    assert len(df) == 1, df[["tourney_name", "playerA", "playerB"]].to_dict("records")

    # with no ids on either side it still collapses by name, exactly as before
    (tmp_path / "upcoming.csv").write_text(
        "tourney_name,tourney_date,round,playerA,playerB\n"
        "Same Open,2026-07-27,R32,A Player,B Player\n", encoding="utf-8")
    _overlay([{"tourney_name": "Same Open", "tourney_date": "2026-07-27", "round": "R32",
               "playerA": "B Player", "playerB": "A Player"}])
    assert len(up.load_upcoming("atp")) == 1

    # two genuinely different events sharing a matchup are NOT collapsed
    (tmp_path / "upcoming.csv").write_text(
        "tourney_name,espn_id,tourney_date,round,playerA,playerB\n"
        "Open One,1-2026,2026-07-27,R32,A Player,B Player\n"
        "Open Two,2-2026,2026-07-27,R32,A Player,B Player\n", encoding="utf-8")
    _overlay([])
    assert len(up.load_upcoming("atp")) == 2
    print("ok test_upcoming_dedup_keys_on_the_event_id_when_both_rows_have_one")


def test_upcoming_reports_corrupt_or_failed_sources_without_discarding_fallback(
        tmp_path, monkeypatch):
    from tennis_model.model import upcoming as up

    from tennis_model.data import draws

    monkeypatch.setattr(up, "live_dir", lambda _tour: tmp_path)
    (tmp_path / "upcoming.csv").write_text(
        "tourney_name,espn_id,tourney_date,round,playerA,playerB\n"
        "Fallback Open,7-2026,2026-08-24,R32,A Player,B Player\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        draws,
        "tournament_draw_upcoming_rows",
        lambda _tour, *, status=None: (
            _ for _ in ()
        ).throw(RuntimeError("draw provider unavailable")),
    )
    status: dict = {}
    frame = up.load_upcoming("atp", status=status)
    assert frame["tourney_name"].tolist() == ["Fallback Open"]
    assert status == {
        "failures": [{"source": "complete-draw", "errorType": "RuntimeError"}]
    }

    (tmp_path / "upcoming.csv").write_text("wrong,columns\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(
        draws, "tournament_draw_upcoming_rows", lambda _tour, *, status=None: [])
    status = {}
    assert up.load_upcoming("atp", status=status).empty
    assert status == {
        "failures": [{"source": "espn-upcoming", "errorType": "SchemaError"}]
    }

    monkeypatch.setattr(
        up.pd,
        "read_csv",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(UnicodeError("bad bytes")),
    )
    status = {}
    assert up.load_upcoming("atp", status=status).empty
    assert status == {
        "failures": [{"source": "espn-upcoming", "errorType": "UnicodeError"}]
    }


if __name__ == "__main__":
    test_enrich_resolves_infers_and_prices()
    test_name_resolution_and_month_fallback()
    test_drops_unknown_and_self_pairs()
    test_empty_and_none_upcoming()
    test_pa_is_orientation_correct()
    test_event_attrs_infers_else_none()
    print("\nALL PASSED")
