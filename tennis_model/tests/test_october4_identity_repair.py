"""Replay Suzhou's blocked identities and Shanghai qualifying near misses."""

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

CAPTURES = [json.loads((Path(__file__).parent / f"fixtures/{name}.json").read_text())
            for name in ("october4_identity_incident", "october4_shanghai_identity_incident")]
CASES = [(capture, review) for capture in CAPTURES for review in capture["identityReview"]]
CODES = {"output.bracket.player_identity_unresolved", "output.bracket.unrated_evidence_invalid",
         "output.bracket.pending_probability_missing"}


@pytest.mark.parametrize("capture,review", CASES)
@pytest.mark.parametrize("unknown_opponent", [False, True])
def test_source_identity_replays_producer_and_gate(monkeypatch, capture, review, unknown_opponent):
    variant, canonical = review["variant"], review["canonical"]
    tour = review["tour"]
    source = next(m for m in capture["matches"] if variant in m["players"])
    opponent = next(p for p in source["players"] if p != variant)
    # Independent official ordered draw corroborates the exact pending opponent.
    slots = capture["officialSlots"]
    index = slots.index(canonical)
    assert slots[index ^ 1] == opponent
    others = [f"Opponent {i}" for i in range(6)]
    inventory = [canonical, opponent] + others
    predictor = _Pred({n: 1500 for n in inventory})
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "official"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "WTA 125" if tour == "wta" else "ATP 1000")
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    for repaired in (False, True):
        canonicalize = (lambda n: config.PLAYER_ALIASES.get(name_key(n), n)) if repaired else lambda n: n
        card = tournaments.project_upcoming(
            predictor, capture["name"],
            {"slots": [variant, "Qualifier 1" if unknown_opponent else opponent] + others,
             "start": "2026-10-05"}, tour, frame, set(), canonicalize,
            espn_id=capture["espnId"])
        tournaments._price_event_bracket(predictor, card, [])
        data = _healthy_data()
        data["meta"]["modelPlayerNames"] = inventory
        data.update(tournaments=[card], brackets=[{**card, "rounds": card["bracket"]}])
        findings = health.output_findings(tour, _oc(data=data), pd.Timestamp("2026-10-04"))
        hits = [f for f in findings if f.code in CODES]
        match = card["bracket"][0]["matches"][0]
        if repaired:
            assert hits == []
            assert match["a"] == canonical
            assert (match["p"] is not None) == (not unknown_opponent)
        else:
            assert "output.bracket.player_identity_unresolved" in {f.code for f in hits}
            assert all(health._gate_blocks(f) for f in hits)
            assert match["p"] is None
            if not unknown_opponent:
                assert {f.code for f in hits} == CODES


@pytest.mark.parametrize("capture,review", CASES)
def test_aliases_pass_retained_evidence_and_collapse_history(capture, review):
    variant, canonical = review["variant"], review["canonical"]
    tour = review["tour"]
    frame = pd.DataFrame(capture["historyRows"]).fillna("")
    evidence = build_evidence(frame)
    assert evidence.counts[name_key(canonical)] == review["counts"][canonical] > 0
    assert falsify(review, {("player_alias", tour, tuple(sorted((variant, canonical)))): True},
                   evidence) is None
    incoming = pd.DataFrame({"winner_name": [variant, canonical],
                             "loser_name": ["Other A", "Other B"], "__src": [0, 2]})
    assert results._canonicalize_names(incoming).winner_name.tolist() == [canonical, canonical]
    assert name_key(canonical) not in config.PLAYER_ALIASES
