"""Offline replays of the four blockers in production refresh 34853624801."""

import copy
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from tennis_model.data.alias_proposer import build_evidence, falsify
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import draws_official as official
from tennis_model.data import draws_wiki as wiki
from tennis_model.data import health, results

FIXTURES = Path(__file__).parent / "fixtures"
INCIDENT = json.loads((FIXTURES / "september_deploy_incident.json").read_text())


def test_sp_open_short_name_metadata_and_draw_locators(monkeypatch):
    calls = []

    def article(title):
        calls.append(title)
        assert title == "2026 SP Open"
        return "| surface = [[Hardcourt]]\n| category = [[WTA 250]]\n"

    monkeypatch.setattr(wiki, "_wikitext", article)
    assert wiki._anchor("SP Open") is None
    assert wiki.event_meta("SP Open", 2026, "wta") == ("Hard", "WTA 250")
    assert calls == ["2026 SP Open"]
    assert wiki.resolve_title("Renamed Sponsor", 2026, "wta", "1005-2026") == (
        "2026 SP Open – Singles")
    assert wiki.resolve_title("SP Open", 2026, "atp", "1005-2026") is None
    with monkeypatch.context() as before:
        before.setattr(wiki, "WIKI_TITLE_OVERRIDES", {})
        assert wiki.event_meta("SP Open", 2026, "wta") == (None, None)


@pytest.mark.parametrize("defect", [None, "dates", "field"])
def test_sp_open_official_locator_still_requires_calendar_and_field(monkeypatch, tmp_path, defect):
    incident = INCIDENT["spOpen"]
    meta = dict(incident["meta"], name="Renamed Sponsor")
    field = incident["field"]
    if defect == "dates":
        meta.update(start="2026-08-01", end="2026-08-07")
    elif defect == "field":
        field = [f"Unrelated Player {i}" for i in range(32)]
    monkeypatch.setattr(official, "wta_catalog", lambda year: ())
    monkeypatch.setattr(official, "live_dir", lambda tour: tmp_path)
    monkeypatch.setattr(official, "_download", lambda url, path: url.encode())
    monkeypatch.setattr(official, "extract_pdf_text", lambda body: (
        (FIXTURES / "sp_open_2026_official.txt").read_text()))
    draw, rejected = official.fetch_official_draw("wta", 2026, meta, {}, field)
    if defect:
        assert draw is None and rejected
    else:
        assert not rejected
        assert draw["sourceId"] == "1139"
        assert draw["evidencePlayers"] == draw["evidenceFieldPlayers"] == 32
        assert draw["sourceStart"] == "2026-09-14"
        assert draw["sourceEnd"] == "2026-09-20"
        with monkeypatch.context() as before:
            before.setattr(official, "OFFICIAL_DRAW_ID_OVERRIDES", {})
            assert official.fetch_official_draw("wta", 2026, meta, {}, field)[0] is None


def test_gao_identity_joins_history_and_passes_falsifier():
    frame = pd.DataFrame({
        "winner_name": ["Xinyu Gao", "Gao Xinyu"],
        "loser_name": ["Francisca Jorge", "Francisca Jorge"],
        "winner_id": ["322925", "322925"], "__src": [0, 2],
    })
    proposal = dict(kind="player_alias", tour="wta", variant="Gao Xinyu",
                    canonical="Xinyu Gao", same_person=True)
    asked = {("player_alias", "wta", ("Gao Xinyu", "Xinyu Gao")): True}
    assert falsify(proposal, asked, build_evidence(frame)) is None
    assert results._canonicalize_names(frame).winner_name.tolist() == ["Xinyu Gao"] * 2


def test_sp_open_metadata_and_coverage_broken_and_clean_gate_replay(monkeypatch):
    from tennis_model.data.event_coverage import finalize_event_coverage

    from tennis_model.data import surface

    incident = INCIDENT["spOpen"]
    meta = incident["meta"]
    manifest = {
        "version": 1, "tour": "wta", "buildDate": "2026-09-14",
        "events": [{**meta, "key": "espn:1005-2026", "evidence": ["scheduled"],
                    "players": incident["field"]}],
    }
    draw = official.parse_official_text((FIXTURES / "sp_open_2026_official.txt").read_text())
    predictor = _Pred({name: 1700.0 for name in draw["slots"]})
    monkeypatch.setattr(surface, "wiki_categories_by_event_id", lambda tour: {})
    codes = {"output.tournament.surface_guessed", "output.tournament.tier_unresolved",
             "output.event_coverage.shell_only"}
    for broken in (True, False):
        monkeypatch.setattr(surface, "wiki_surface_map", lambda tour, broken=broken: (
            {} if broken else {"SP Open": "Hard"}))
        monkeypatch.setattr(surface, "wiki_category_map", lambda tour, broken=broken: (
            {} if broken else {"SP Open": "WTA 250"}))
        cards = [] if broken else [tournaments.project_upcoming(
            predictor, "SP Open", {**draw, **meta}, "wta", pd.DataFrame(), set(),
            lambda name: name, espn_id=meta["espnId"])]
        coverage = finalize_event_coverage(copy.deepcopy(manifest), cards)
        data = _healthy_data()
        data.update(tournaments=cards, brackets=[], event_coverage=coverage)
        hits = {f.code for f in health.output_findings(
            "wta", _oc(data=data), pd.Timestamp("2026-09-14"))} & codes
        assert hits == (codes if broken else set())
        if not broken:
            assert cards[0]["status"] == "upcoming"
            assert cards[0]["drawSize"] == 32 and cards[0]["projection"]
            assert coverage["shellKeys"] == []


@pytest.mark.parametrize("event, variant, canonical, opponent", [
    ("caldas", "Gao Xinyu", "Xinyu Gao", "Francisca Jorge"),
    ("valencia", "Joelle Lilly Sophie Steur", "Joelle Steur", "Charo Esquiva Banuls"),
])
def test_pending_probability_broken_and_clean_producer_gate_replay(
        monkeypatch, event, variant, canonical, opponent):
    draw = INCIDENT[event]
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    names = [canonical if name == variant else name for name in draw["slots"]]
    predictor = _Pred({name: 1500 + i * 10 for i, name in enumerate(names)})
    monkeypatch.setattr(tournaments, "_load_fields", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming_bounds", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_tournament_draws", lambda tour: {draw["espnId"]: draw})
    monkeypatch.setattr(tournaments, "load_registry", lambda tour: {"events": {}})
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "wiki"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "WTA 125")
    from tennis_model.eval import track
    monkeypatch.setattr(track, "_read_log", lambda path: [])

    for broken in (True, False):
        aliases = dict(config.PLAYER_ALIASES)
        if broken:
            aliases.pop(results._name_key(variant), None)
        monkeypatch.setattr(tournaments, "PLAYER_ALIASES", aliases)
        card, = tournaments.build_tournaments(predictor, frame, "wta")
        bracket = {**card, "rounds": card["bracket"]}
        data = copy.deepcopy(_healthy_data())
        data.update(tournaments=[card], brackets=[bracket])
        findings = health.output_findings("wta", _oc(data=data), pd.Timestamp("2026-09-14"))
        hits = [f for f in findings if f.code == "output.bracket.pending_probability_missing"]
        match = next(m for m in card["bracket"][0]["matches"] if opponent in (m["a"], m["b"]))
        if broken:
            assert len(hits) == 1
            assert set(hits[0].evidence["players"]) == {opponent, variant}
            assert match["p"] is None
        else:
            assert not hits
            assert canonical in (match["a"], match["b"])
            assert match["p"] == pytest.approx(round(predictor.win_prob(match["a"], match["b"]), 4))
            assert match["probSource"] == "model"


@pytest.mark.parametrize("tour, day, warns", [
    ("atp", "2026-09-13", True), ("atp", "2026-09-14", False),
    ("atp", "2026-09-22", False), ("atp", "2026-09-23", True),
    ("wta", "2026-09-14", True), ("atp", "2027-09-14", True),
])
def test_no_active_advisory_respects_only_the_verified_tour_gap(tour, day, warns):
    data = _healthy_data()
    data["tournaments"] = [t for t in data["tournaments"] if t["status"] == "completed"]
    codes = {f.code for f in health.output_findings(tour, _oc(data=data), pd.Timestamp(day))}
    assert ("output.tournament.no_active_event" in codes) is warns


def test_schedule_gap_preserves_missing_event_empty_board_and_staleness_checks(monkeypatch):
    data = _healthy_data()
    data["tournaments"] = [t for t in data["tournaments"] if t["status"] == "completed"]
    data["event_coverage"]["buildDate"] = "2026-09-14"
    data["event_coverage"]["events"][0].update(start="2026-09-14", end="2026-09-20")
    now = pd.Timestamp("2026-09-14")
    codes = {f.code for f in health.output_findings("atp", _oc(data=data), now)}
    assert "output.tournament.no_active_event" not in codes
    assert "output.event_coverage.missing_card" in codes
    assert "output.model.training_stale" in codes
    data["tournaments"] = []
    assert "output.tournament.board_empty" in {
        f.code for f in health.output_findings("atp", _oc(data=data), now)}
    # Before the dated calendar evidence, even a completed retained board raised #65.
    data["tournaments"] = [_healthy_data()["tournaments"][-1]]
    monkeypatch.setattr(health, "HEALTH_SCHEDULE_GAPS", {})
    assert "output.tournament.no_active_event" in {
        f.code for f in health.output_findings("atp", _oc(data=data), now)}
