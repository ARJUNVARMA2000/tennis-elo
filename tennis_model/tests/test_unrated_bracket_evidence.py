"""Ankara newcomers remain factual, while missing known-player odds still block."""

import copy
import json
from pathlib import Path

import pytest
from tennis_model.data.health_checks.common import _FindingCollector
from tennis_model.data.health_checks.draws import _check_brackets
from tennis_model.data.names import name_key
from tennis_model.sim.bracket import bracket_rounds, is_real
from tennis_model.sim.tournaments import _price_event_bracket
from test_health import _healthy_bracket
from test_tournament_status import _Pred

from tennis_model import config

INCIDENT = json.loads((Path(__file__).parent / "fixtures/ankara_deploy_incident.json").read_text())
NEWCOMERS = {"Aysegul Mert", "Alya Naz Altinel"}
CODES = {"output.bracket.pending_probability_missing", "output.bracket.unrated_evidence_invalid"}


def findings(bracket, rated):
    out = _FindingCollector("output", "wta")
    _check_brackets(out, "wta", [bracket], [], rated_players=rated)
    return [f for f in out.findings if f.code in CODES]


def test_ankara_capture_prices_known_players_and_proves_newcomer_unavailability():
    canonical = lambda n: config.PLAYER_ALIASES.get(name_key(n), n)
    source_slots = [m[s] for m in INCIDENT["matches"] for s in ("a", "b")]
    source_slots = [n if is_real(n) else f"Qualifier {i}" for i, n in enumerate(source_slots)]
    rated = sorted({canonical(n) for n in source_slots if is_real(n)} - NEWCOMERS)
    predictor = _Pred({n: 1500 + i * 10 for i, n in enumerate(rated)})
    for broken in (True, False):
        slots = [n if broken and n == "Tian Fangran" else canonical(n) for n in source_slots]
        card = {**_healthy_bracket(), **{k: INCIDENT[k] for k in ("name", "espnId", "start", "end")},
                "status": "upcoming", "champion": None, "runnerUp": None,
                "drawSize": 32, "bracketSize": 32, "bracket": bracket_rounds(slots, [])}
        _price_event_bracket(predictor, card, [])
        card["rounds"] = card["bracket"]
        hits = findings(card, rated)
        if broken:
            assert {f.code for f in hits} == CODES
            assert all("tian" in f.entity for f in hits)
        else:
            assert hits == []
            unavailable = [m for m in card["rounds"][0]["matches"]
                           if m["p"] is None and is_real(m["a"]) and is_real(m["b"])]
            assert {n for m in unavailable for n in m["unratedPlayers"]} == NEWCOMERS
            assert len(unavailable) == 2
            tian, = [m for m in card["rounds"][0]["matches"] if "Fangran Tian" in (m["a"], m["b"])]
            assert tian["probSource"] == "model" and 0 < tian["p"] < 1
            # Bare absence still fails. The annotation is load-bearing evidence.
            for m in unavailable:
                m.pop("unratedPlayers")
            assert len(findings(card, rated)) == 2


@pytest.mark.parametrize("defect", [None, "missing_inventory", "malformed_inventory", "rated",
                                  "wrong_player", "reversed", "priced", "completed"])
def test_no_history_exception_rejects_forged_stale_and_ambiguous_evidence(defect):
    br = _healthy_bracket()
    br.update(status="live", champion=None)
    match = br["rounds"][-1]["matches"][0]
    match.update(a="New Entrant", winner=None, score=None, p=None, probSource=None,
                 upset=None, unratedPlayers=["New Entrant"])
    rated = ["A", "B", "C", "D"]
    if defect == "missing_inventory":
        rated = None
    elif defect == "malformed_inventory":
        rated = ["A", {}]
    elif defect == "rated":
        rated.append("New Entrant")
    elif defect == "wrong_player":
        match["unratedPlayers"] = ["C"]
    elif defect == "reversed":
        rated.append("Entrant New")
    elif defect == "priced":
        match.update(p=0.5, probSource="model")
    elif defect == "completed":
        match.update(winner="a", score="6-2 6-1")
    hits = findings(br, rated)
    assert bool(hits) is (defect is not None)
    if defect:
        assert any(f.code == "output.bracket.unrated_evidence_invalid" for f in hits)


def test_repricing_removes_stale_no_history_annotation():
    card = {**_healthy_bracket(), "bracket": bracket_rounds(["New Entrant", "C"], [])}
    _price_event_bracket(_Pred({"C": 1700}), card, [])
    m = card["bracket"][0]["matches"][0]
    assert m["unratedPlayers"] == ["New Entrant"]
    _price_event_bracket(_Pred({"C": 1700, "New Entrant": 1500}), card, [])
    assert "unratedPlayers" not in m and m["probSource"] == "model"
    assert findings({**copy.deepcopy(card), "rounds": card["bracket"]}, ["C", "New Entrant"]) == []
