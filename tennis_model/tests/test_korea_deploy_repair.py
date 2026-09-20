"""Captured Korea Open names, draw seats, and producer-to-release-gate replays."""

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
    (Path(__file__).parent / "fixtures/korea_open_deploy_incident.json").read_text())
ALIASES = (("Yuan Yue", "Yue Yuan", "324325"), ("Yao Xinxin", "Xinxin Yao", "331361"))


@pytest.mark.parametrize("variant,canonical,wta_id", ALIASES)
def test_korea_alias_joins_source_name_to_existing_wta_history(variant, canonical, wta_id):
    # Canonical WTA ids from retained stats/history; ESPN ids have their own namespace.
    source_players = [p for m in INCIDENT["sourceMatches"] for p in m["players"]]
    assert any(p["name"] == variant for p in source_players)
    frame = pd.DataFrame({
        "winner_name": [canonical, variant], "loser_name": ["Opponent A", "Opponent B"],
        "winner_id": [wta_id, ""], "__src": [0, 2],
    })
    proposal = dict(kind="player_alias", tour="wta", variant=variant,
                    canonical=canonical, same_person=True)
    asked = {("player_alias", "wta", tuple(sorted((variant, canonical)))): True}
    assert falsify(proposal, asked, build_evidence(frame)) is None
    assert results._canonicalize_names(frame).winner_name.tolist() == [canonical] * 2


@pytest.mark.parametrize("early", [False, True])
def test_korea_missing_odds_broken_and_clean_producer_gate_replay(monkeypatch, early):
    draw = copy.deepcopy(INCIDENT["draw"])
    if early:
        draw["slots"] = INCIDENT["earlySlots"]
        draw.update(evidencePlayers=28, evidenceFieldPlayers=28)
    names = [config.PLAYER_ALIASES.get(results._name_key(n), n) for n in draw["slots"]
             if not n.startswith("Qualifier ")]
    predictor = _Pred({name: 1500 + i * 10 for i, name in enumerate(names)})
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    monkeypatch.setattr(tournaments, "_load_fields", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming_bounds", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_tournament_draws", lambda tour: {draw["espnId"]: draw})
    monkeypatch.setattr(tournaments, "load_registry", lambda tour: {"events": {}})
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "wiki"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "WTA 250")
    from tennis_model.eval import track
    monkeypatch.setattr(track, "_read_log", lambda path: [])

    for broken in (True, False):
        aliases = dict(config.PLAYER_ALIASES)
        if broken:
            for variant, _, _ in ALIASES:
                aliases.pop(results._name_key(variant), None)
        monkeypatch.setattr(tournaments, "PLAYER_ALIASES", aliases)
        card, = tournaments.build_tournaments(predictor, frame, "wta")
        data = copy.deepcopy(_healthy_data())
        data.update(tournaments=[card], brackets=[{**card, "rounds": card["bracket"]}])
        hits = [f for f in health.output_findings(
            "wta", _oc(data=data), pd.Timestamp("2026-09-20"))
            if f.code == "output.bracket.pending_probability_missing"]
        if broken:
            expected = [{"Yuan Yue", "Dayeon Back"}]
            if not early:
                expected.append({"Yao Xinxin", "Maya Joint"})
            assert [set(f.evidence["players"]) for f in hits] == expected
            assert all(health._gate_blocks(f) for f in hits)
        else:
            assert not hits
            matches = card["bracket"][0]["matches"]
            assert len(matches) == 16
            for match in matches:
                if any(str(match[s]).startswith("Qualifier ") for s in ("a", "b")):
                    assert match["p"] is None and match["probSource"] is None
                else:
                    assert match["p"] == pytest.approx(
                        round(predictor.win_prob(match["a"], match["b"]), 4))
                    assert match["probSource"] == "model"
            assert {"Yue Yuan", "Dayeon Back"} in [{m["a"], m["b"]} for m in matches]
            if not early:
                assert {"Xinxin Yao", "Maya Joint"} in [{m["a"], m["b"]} for m in matches]
