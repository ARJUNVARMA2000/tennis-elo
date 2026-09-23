"""Captured pending pairs must join rated identities before the release gate."""

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.data.alias_proposer import build_evidence, falsify
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import health, results

INCIDENT = json.loads(
    (Path(__file__).parent / "fixtures/september23_deploy_incident.json").read_text())
ALIASES = [
    ("atp", "Cui Jie", "Jie Cui", "C0AJ"),
    ("atp", "Sun Fajing", "Fajing Sun", "SX90"),
]
CODES = {"output.bracket.pending_probability_missing", "output.bracket.unrated_evidence_invalid"}


@pytest.mark.parametrize("tour,variant,canonical,player_id", ALIASES)
def test_captured_identity_joins_retained_history(tour, variant, canonical, player_id):
    assert any(p["name"] == variant for m in INCIDENT["matches"] for p in m["players"])
    frame = pd.DataFrame({
        "winner_name": [canonical, variant], "loser_name": ["Opponent A", "Opponent B"],
        "winner_id": [player_id, ""], "__src": [0, 2],
    })
    proposal = dict(kind="player_alias", tour=tour, variant=variant,
                    canonical=canonical, same_person=True)
    asked = {("player_alias", tour, tuple(sorted((variant, canonical)))): True}
    assert falsify(proposal, asked, build_evidence(frame)) is None
    assert results._canonicalize_names(frame).winner_name.tolist() == [canonical] * 2


@pytest.mark.parametrize("source", [m for m in INCIDENT["matches"] if not m["completed"]],
                         ids=lambda m: m["matchId"])
def test_pending_source_pair_broken_and_clean_producer_gate(monkeypatch, source):
    # Isolate each captured pair in a small draw with unresolved neighboring slots.
    # This is a replay harness, not a claim about the source's full draw order.
    names = [p["name"] for p in source["players"]]
    reviewed = {variant: canonical for _, variant, canonical, _ in ALIASES}
    rated = [reviewed.get(n, n) for n in names]
    rated += ["Opponent A", "Opponent B", "Opponent C", "Opponent D"]
    predictor = _Pred({n: 1550 + i * 100 for i, n in enumerate(rated)})
    draw = {k: source[k] for k in ("name", "espnId", "start", "end")}
    draw.update(slots=names + ["Qualifier 1", "Qualifier 2"] + rated[2:],
                drawSize=8, bracketSize=8,
                source="espn", sourceUrl=source["sourceUrl"], status="partial")
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    monkeypatch.setattr(tournaments, "_load_fields", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming_bounds", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_tournament_draws", lambda tour: {draw["espnId"]: draw})
    monkeypatch.setattr(tournaments, "load_registry", lambda tour: {"events": {}})
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "wiki"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "250")
    from tennis_model.eval import track
    monkeypatch.setattr(track, "_read_log", lambda path: [])

    for broken in (True, False):
        aliases = dict(config.PLAYER_ALIASES)
        if broken:
            for _, variant, _, _ in ALIASES:
                aliases.pop(results._name_key(variant), None)
        monkeypatch.setattr(tournaments, "PLAYER_ALIASES", aliases)
        card, = tournaments.build_tournaments(predictor, frame, source["tour"])
        data = copy.deepcopy(_healthy_data())
        data["meta"]["modelPlayerNames"] = rated
        data.update(tournaments=[card], brackets=[{**card, "rounds": card["bracket"]}])
        hits = [f for f in health.output_findings(
            source["tour"], _oc(data=data), pd.Timestamp(INCIDENT["sourceDate"]))
            if f.code in CODES]
        match = card["bracket"][0]["matches"][0]
        if broken:
            assert {f.code for f in hits} == CODES
            assert all(health._gate_blocks(f) for f in hits)
            assert match["p"] is None and match["unratedPlayers"]
        else:
            assert hits == []
            assert {match["a"], match["b"]} == set(rated[:2])
            assert match["p"] == pytest.approx(round(predictor.win_prob(*rated[:2]), 4))
            assert match["probSource"] == "model" and "unratedPlayers" not in match
            unresolved = card["bracket"][0]["matches"][1]
            assert unresolved["p"] is None and unresolved["probSource"] is None
