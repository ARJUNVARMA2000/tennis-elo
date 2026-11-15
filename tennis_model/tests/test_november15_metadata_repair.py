"""Replay November 15 metadata failures using reconstructed published-release inputs.

The fixture identifies the original public artifacts and independently reviewed official
facts. It is deliberately not labelled a capture of original ESPN/WTA provider bytes.
"""

import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.data.participants import is_real_participant
from tennis_model.model import upcoming
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _g, _Pred

from tennis_model import config
from tennis_model.data import event_coverage, events, health, results, surface

REPLAY = json.loads((Path(__file__).parent / "fixtures/november15_metadata_reconstruction.json").read_text())
NOW = pd.Timestamp("2026-11-15")
METADATA_CODES = {"output.tournament.surface_guessed", "output.tournament.tier_unresolved"}


@pytest.fixture
def offline_metadata(monkeypatch):
    monkeypatch.setattr(surface, "wiki_surface_map", lambda tour: {})
    monkeypatch.setattr(surface, "wiki_category_map", lambda tour: {})
    monkeypatch.setattr(events, "load_registry", lambda tour: {"events": {}})


def _metadata_findings(tour, card):
    data = _healthy_data()
    data["tournaments"] = [card]
    return {f.code for f in health.output_findings(tour, _oc(data=data), NOW)
            if f.code in METADATA_CODES and card["espnId"] in f.entity}


def test_reviewed_metadata_overrides_stale_sources_only_for_exact_tour_and_edition(offline_metadata, monkeypatch):
    monkeypatch.setattr(surface, "wiki_category_map", lambda tour: {"Any sponsor": "Grand Slam"})
    assert surface.resolve_level("wta", "Any sponsor", "G", "904-2026") == "WTA 125"
    assert surface.resolve_level("atp", "Any sponsor", "G", "339-2026") == "Tour Finals"
    assert surface.resolve_surface_info("wta", "Any sponsor", "2026-11-16", "Hard", "904-2026") == (
        "Clay", "reviewed")
    for tour, event_id in [("atp", "904-2026"), ("wta", "904-2027"), ("wta", None),
                           ("wta", "339-2026"), ("atp", "339-2027")]:
        assert surface.resolve_level(tour, "Any sponsor", "G", event_id) == "Grand Slam"
        assert surface.resolve_surface_info(tour, "Any sponsor", "2026-11-16", "Hard", event_id) == (
            "Hard", "archive")


def test_colina_draw_projection_live_shell_and_schedule_use_clay_and_125(offline_metadata, monkeypatch):
    draw = REPLAY["lpDraw"]
    names = {name for name in draw["slots"] if is_real_participant(name)}
    predictor = _Pred(dict.fromkeys(names, 1600.0))
    archive = pd.DataFrame()
    seen_surfaces = []
    original_matrix = predictor.win_prob_matrix

    def matrix(players, **kwargs):
        seen_surfaces.append(kwargs["surface"])
        return original_matrix(players, **kwargs)

    monkeypatch.setattr(predictor, "win_prob_matrix", matrix)

    def project():
        return tournaments.project_upcoming(
            predictor, draw["name"], draw, "wta", archive, set(), lambda n: n,
            espn_id=draw["espnId"], n_sims=64)

    # Missing source metadata really produced Hard and WTA Tour for the published draw.
    with monkeypatch.context() as broken:
        broken.setattr(surface, "EVENT_TIER_BY_ID", {})
        broken.setattr(surface, "EVENT_SURFACE_BY_ID", {})
        wrong = project()
        assert wrong["surface"] == "Hard" and wrong["surfaceSource"] == "month"
        assert wrong["level"] == "WTA Tour"
        assert _metadata_findings("wta", wrong) == METADATA_CODES

    seen_surfaces.clear()
    card = project()
    assert card["surface"] == "Clay" and card["surfaceSource"] == "reviewed"
    assert card["level"] == "WTA 125"
    assert card["drawSize"] == 32 and len(card["bracket"][0]["matches"]) == 16
    assert seen_surfaces and set(seen_surfaces) == {"Clay"}
    assert not _metadata_findings("wta", card)

    # The live path and a projection-failure shell must use the same exact edition facts.
    live = tournaments.project_tournament(
        _Pred({f"P{i}": 1500 for i in range(16)}), draw["name"], _g(), "wta",
        espn_id=draw["espnId"], n_sims=32)
    shell = event_coverage._coverage_shell({
        "key": "espn:" + draw["espnId"], "name": draw["name"], "espnId": draw["espnId"],
        "start": draw["start"], "end": draw["end"],
        "surface": "Hard", "surfaceSource": "archive", "archiveLevel": "WTA 250",
    }, "2026-11-16", "wta")
    for output in (live, shell):
        assert output["surface"] == "Clay" and output["level"] == "WTA 125"

    seen_contexts = []

    def components(a, b, **context):
        seen_contexts.append(context)
        return {"eloBlend": 0.5, "pointModel": 0.5, "combiner": 0.5}

    monkeypatch.setattr(predictor, "prediction_components", components, raising=False)
    scheduled = pd.DataFrame([
        {"tourney_name": draw["name"], "espn_id": draw["espnId"], "tourney_date": "2026-11-16",
         "round": "R32", "playerA": a, "playerB": b}
        for a, b in zip(draw["slots"][::2], draw["slots"][1::2])
        if is_real_participant(a) and is_real_participant(b)
    ])
    priced = upcoming.enrich_upcoming(predictor, archive, scheduled, "wta", bracket_index={})
    assert len(priced) == 12
    assert {row["surface"] for row in priced} == {"Clay"}
    assert {row["level"] for row in priced} == {"WTA 125"}
    mults, _ = results.tier_mults("wta")
    assert seen_contexts and {ctx["surface"] for ctx in seen_contexts} == {"Clay"}
    assert {ctx["tier_k"] for ctx in seen_contexts} == {mults["challenger"]}


def test_colina_review_classifies_future_live_rows_without_admitting_125_population(offline_metadata, monkeypatch):
    monkeypatch.setattr(config, "INCLUDE_WTA_125", False)
    # Synthetic future result tests classification only; it does not claim a match occurred.
    row = pd.DataFrame([{"espn_id": "904-2026", "tourney_level": None}])
    stamped = results._stamp_live_result_policy("wta", row)
    assert stamped["__policy_excluded"].all()
    assert stamped["tourney_level"].tolist() == ["WTA125"]
    assert stamped.attrs["excluded_wta125_event_ids"] == ("904-2026",)
    assert stamped.attrs["excluded_unclassified_wta_event_ids"] == ()
    assert "904-2026" not in surface.wiki_categories_by_event_id("atp")
    assert "904-2027" not in surface.wiki_categories_by_event_id("wta")


def test_atp_group_stage_card_resolves_tier_with_wikipedia_unavailable(offline_metadata, monkeypatch):
    monkeypatch.setattr(surface, "wiki_surface_map", lambda tour: {"Nitto ATP Finals": "Hard"})
    source = {"witness": {"events": [REPLAY["atpSourceEvent"]]}}

    def cards():
        output = []
        event_coverage.add_round_robin_cards(output, source, "atp", "2026-11-15")
        return output

    with monkeypatch.context() as broken:
        broken.setattr(surface, "EVENT_TIER_BY_ID", {})
        wrong, = cards()
        assert wrong["level"] == "ATP Tour"
        assert _metadata_findings("atp", wrong) == {"output.tournament.tier_unresolved"}
    fixed, = cards()
    assert fixed["level"] == "Tour Finals" and fixed["surface"] == "Hard"
    assert fixed["drawStatus"] == "round-robin" and fixed["drawSize"] == 8
    assert len(fixed["roundRobinFixtures"]) == 12
    assert not _metadata_findings("atp", fixed)
