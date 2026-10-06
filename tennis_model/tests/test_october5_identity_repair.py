"""Shanghai's complete released draw catches an identity beside an unknown qualifier."""

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.data.alias_proposer import build_evidence, falsify
from tennis_model.data.names import name_key
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import health, results

CAPTURE = json.loads((Path(__file__).parent / "fixtures/october5_shanghai_identity_incident.json").read_text())
CODES = {"output.bracket.player_identity_unresolved", "output.bracket.unrated_evidence_invalid",
         "output.bracket.pending_probability_missing"}


@pytest.mark.parametrize("qualifier_assigned", [False, True])
def test_complete_shanghai_draw_catches_wu_before_opponent_is_assigned(monkeypatch, qualifier_assigned):
    draw = copy.deepcopy(CAPTURE["draw"])
    assert len(draw["slots"]) == 128 and draw["drawSize"] == 96
    assert CAPTURE["officialIdentitySlot"] == {
        "position": 3, "name": "Yibing Wu", "opponent": "Qualifier 1"}
    assert draw["slots"][2:4] == ["Wu Yibing", "Qualifier 1"]
    if qualifier_assigned:
        # A rated qualifier is a counterfactual settlement, not a claimed source pairing.
        draw["slots"][3] = "Rigele Te"
    canonical = lambda n: config.PLAYER_ALIASES.get(name_key(n), n)
    inventory = [canonical(n) for n in draw["slots"] if n and not n.startswith("Qualifier")]
    predictor = _Pred({n: 1500 for n in inventory})
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "official"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "ATP 1000")
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    draw["start"] = CAPTURE["start"]
    for repaired in (False, True):
        resolve = canonical if repaired else lambda n: n if n == "Wu Yibing" else canonical(n)
        card = tournaments.project_upcoming(predictor, CAPTURE["name"], draw, "atp", frame,
                                            set(), resolve, espn_id=CAPTURE["espnId"])
        tournaments._price_event_bracket(predictor, card, [])
        data = _healthy_data()
        data["meta"]["modelPlayerNames"] = inventory
        data.update(tournaments=[card], brackets=[{**card, "rounds": card["bracket"]}])
        findings = health.output_findings("atp", _oc(data=data), pd.Timestamp("2026-10-06"))
        hits = [f for f in findings if f.code in CODES]
        match = card["bracket"][0]["matches"][1]
        assert card["drawSize"] == 96
        if repaired:
            assert hits == []
            assert match["a"] == "Yibing Wu"
            assert (match["p"] is not None) == qualifier_assigned
        else:
            assert all(health._gate_blocks(f) for f in hits)
            identity, = [f for f in hits if f.code == "output.bracket.player_identity_unresolved"]
            assert identity.evidence == {"player": "Wu Yibing", "ratedCandidates": ["Yibing Wu"]}
            assert {f.code for f in hits} == (CODES if qualifier_assigned else {identity.code})


def test_wu_alias_matches_official_atp_id_and_retained_history():
    review = CAPTURE["identityReview"]
    frame = pd.DataFrame(CAPTURE["historyRows"]).fillna("")
    evidence = build_evidence(frame)
    assert evidence.counts["wu yibing"] == review["counts"]["Wu Yibing"] == 4
    assert evidence.counts["yibing wu"] == review["counts"]["Yibing Wu"] == 371
    assert evidence.stable_ids["yibing wu"] == {review["atpId"]} == {"WB32"}
    assert falsify(review, {("player_alias", "atp", ("Wu Yibing", "Yibing Wu")): True}, evidence) is None
    normalized = results._canonicalize_names(frame.assign(__src=0))
    assert "Wu Yibing" not in set(normalized.winner_name) | set(normalized.loser_name)
    assert (normalized.winner_name != normalized.loser_name).all()
    assert "yibing wu" not in config.PLAYER_ALIASES
