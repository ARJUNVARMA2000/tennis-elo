"""Captured Lu/China Open identities, including a real lucky-loser replacement."""

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.data.alias_proposer import build_evidence, falsify
from tennis_model.data.live import _athlete_name
from tennis_model.data.names import name_key
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import health, results

CAPTURE = json.loads((Path(__file__).parent / "fixtures/september30_identity_incident.json").read_text())
IDENTITY = "output.bracket.player_identity_unresolved"
UNRATED = "output.bracket.unrated_evidence_invalid"


def _canonical(name):
    return config.PLAYER_ALIASES.get(name_key(name), name)


def _project(monkeypatch, names, rated, canonical=_canonical):
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "wiki"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "WTA 125")
    others = [f"Opponent {i}" for i in range(6)]
    inventory = rated + others
    predictor = _Pred({n: 1500 for n in inventory})
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    card = tournaments.project_upcoming(
        predictor, "Jingshan Tennis Open", {"slots": names + others, "start": "2026-09-30"},
        "wta", frame, set(), canonical, espn_id="1028-2026")
    tournaments._price_event_bracket(predictor, card, [])
    data = copy.deepcopy(_healthy_data())
    data["meta"]["modelPlayerNames"] = inventory
    data.update(tournaments=[card], brackets=[{**card, "rounds": card["bracket"]}])
    findings = health.output_findings("wta", _oc(data=data), pd.Timestamp("2026-09-30"))
    return card, findings


@pytest.mark.parametrize("opponent", ["Alexandra Shubladze", "Qualifier 1"])
def test_hyphenated_lu_is_caught_before_pairing_and_joins_history(monkeypatch, opponent):
    captured = CAPTURE["jingshanBracket"]["rounds"][1]["matches"]
    assert any(m["a"] == "Alexandra Shubladze" and m["b"] == "Lu Jia-Jing" for m in captured)
    rated = ["Jia Jing Lu", "Alexandra Shubladze"]
    broken, findings = _project(monkeypatch, ["Lu Jia-Jing", opponent], rated, lambda n: n)
    hits = [f for f in findings if f.code == IDENTITY]
    assert len(hits) == 1 and health._gate_blocks(hits[0])
    assert hits[0].evidence == {"player": "Lu Jia-Jing", "ratedCandidates": ["Jia Jing Lu"]}
    if opponent == "Alexandra Shubladze":
        assert UNRATED in {f.code for f in findings}
        assert broken["bracket"][0]["matches"][0]["p"] is None
    clean, findings = _project(monkeypatch, ["Lu Jia-Jing", opponent], rated)
    assert not {IDENTITY, UNRATED, "output.bracket.pending_probability_missing"} & {f.code for f in findings}
    match = clean["bracket"][0]["matches"][0]
    assert match["a"] == "Jia Jing Lu"
    assert (match.get("p") is not None) == (opponent == "Alexandra Shubladze")


@pytest.mark.parametrize("variant,canonical", [("Lu Jia-Jing", "Jia Jing Lu"), ("Yexin Ma", "Ye Xin Ma")])
def test_reviewed_aliases_collapse_retained_history_without_chains(variant, canonical):
    assert CAPTURE["history"][canonical]["appearances"] > 0
    frame = pd.DataFrame({"winner_name": [canonical, variant],
                          "loser_name": ["Other A", "Other B"], "__src": [0, 2]})
    proposal = dict(kind="player_alias", tour="wta", variant=variant, canonical=canonical, same_person=True)
    assert falsify(proposal, {("player_alias", "wta", tuple(sorted((variant, canonical)))): True},
                   build_evidence(frame)) is None
    assert results._canonicalize_names(frame).winner_name.tolist() == [canonical, canonical]
    assert name_key(canonical) not in config.PLAYER_ALIASES


def test_captured_china_lucky_loser_replaces_sherif_in_the_scheduled_slot():
    old = CAPTURE["chinaBracket"]
    slots = [_canonical(m[side]) if m[side] else None for m in old["rounds"][0]["matches"]
             for side in ("a", "b")]
    new = next(d for d in CAPTURE["officialDraws"] if d["tour"] == "wta" and d["id"] == "959-2026")
    current = [_canonical(n) if n else None for n in new["slots"]]
    # The producer reconciles harmless accents, PDF ligatures and hyphens by name_key.
    old_by_key = {name_key(n): n for n in slots if n}
    current = [old_by_key.get(name_key(n), n) if n else None for n in current]
    source = next(m for m in CAPTURE["matches"]
                  if {p["name"] for p in m["players"]} == {"Ma YeXin", "Polina Kudermetova"})
    pairing = tuple(_athlete_name({"athlete": {"displayName": p["name"], "id": p["id"]}})
                    for p in source["players"])
    assert set(pairing) == {"Ye Xin Ma", "Polina Kudermetova"}
    assert slots[90:92] == ["Mayar Sherif", "Polina Kudermetova"]
    assert current[90:92] == ["Ye Xin Ma", "Polina Kudermetova"]
    derived, unresolved = tournaments._derive_withdrawals(slots, set(current) - {None}, [], [pairing])
    assert derived == {"Mayar Sherif": "Ye Xin Ma"} and unresolved == []


def test_newcomer_lin_name_is_consistent_but_does_not_acquire_a_forecast(monkeypatch):
    source = next(m for m in CAPTURE["matches"] if any(p["name"] == "Yu Jun Lin" for p in m["players"]))
    assert {p["name"] for p in source["players"]} == {"Yu Jun Lin", "Storm Hunter"}
    assert CAPTURE["history"]["Yu Jun Lin"]["appearances"] == 0
    card, findings = _project(monkeypatch, ["Lin Yujun", "Storm Hunter"], ["Storm Hunter"])
    match = card["bracket"][0]["matches"][0]
    assert match["a"] == "Yu Jun Lin" and match["p"] is None
    assert match["unratedPlayers"] == ["Yu Jun Lin"]
    assert not {IDENTITY, UNRATED, "output.bracket.pending_probability_missing"} & {f.code for f in findings}


def test_accent_and_hyphen_equivalent_rated_names_cannot_claim_no_history(monkeypatch):
    # Exact identity normalization also guards the no-history escape hatch itself.
    _, findings = _project(monkeypatch, ["Jia-Jing Lú", "Alexandra Shubladze"],
                           ["Jia Jing Lu", "Alexandra Shubladze"], lambda n: n)
    assert UNRATED in {f.code for f in findings}


def test_china_official_id_is_probed_before_calendar_city_candidates(monkeypatch):
    from tennis_model.data import draws_official

    # The actual WTA catalogue calls this event BEIJING, after seven nearby entries.
    nearby = [dict(id=str(i), name=f"City {i}", start="2026-09-27", end="2026-10-04")
              for i in range(7)]
    nearby.append(dict(id="1020", name="BEIJING", start="2026-09-30", end="2026-10-11"))
    monkeypatch.setattr(draws_official, "wta_catalog", lambda year: tuple(nearby))
    candidates = draws_official.wta_candidate_ids(2026, {
        "name": "China Open", "espnId": "959-2026", "start": "2026-09-27", "end": "2026-10-12"})
    assert candidates[0]["id"] == "1020"
    assert sum(c["id"] == "1020" for c in candidates) == 1


@pytest.mark.parametrize("scheduled", [False, True])
def test_prestart_cached_draw_replacement_and_gate(monkeypatch, scheduled):
    old = CAPTURE["chinaBracket"]
    slots = [m[s] for m in old["rounds"][0]["matches"] for s in ("a", "b")]
    old_field = {_canonical(p) for p in slots if p}
    current_field = sorted(old_field - {"Mayar Sherif"} | {"Ye Xin Ma"})
    predictor = _Pred({n: 1500 for n in old_field | set(current_field)})
    draw = {k: old[k] for k in ("name", "espnId", "start", "end")}
    draw.update(slots=slots, source="wikipedia", sourceUrl=old["drawSourceUrl"])
    # Different source display names must still join by the stable edition ID.
    monkeypatch.setattr(tournaments, "_load_fields", lambda tour: {
        "Sponsor title": {"espnId": "959-2026", "field": current_field, "eliminated": []}})
    monkeypatch.setattr(tournaments, "_load_upcoming", lambda tour: {
        "959-2026": [("Ma YeXin", "Polina Kudermetova")] if scheduled else []})
    monkeypatch.setattr(tournaments, "_load_upcoming_bounds", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_tournament_draws", lambda tour: {"959-2026": draw})
    monkeypatch.setattr(tournaments, "load_registry", lambda tour: {"events": {}})
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "wiki"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "WTA 1000")
    from tennis_model.eval import track
    monkeypatch.setattr(track, "_read_log", lambda path: [])
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    card, = tournaments.build_tournaments(predictor, frame, "wta")
    match = card["bracket"][0]["matches"][45]
    assert (match["a"], match["b"]) == (
        "Ye Xin Ma" if scheduled else "Mayar Sherif", "Polina Kudermetova")
    assert match["winner"] is None and match["p"] == 0.5
    assert card["drawSize"] == 96
    data = _healthy_data()
    data.update(brackets=[{**card, "rounds": card["bracket"]}], upcoming=[{
        "espnId": "959-2026", "event": "Another sponsor title", "round": "R128",
        "playerA": "Ma YeXin", "playerB": "Polina Kudermetova", "pA": 0.5}])
    def missing(d):
        return [f for f in health.output_findings("wta", _oc(data=d), pd.Timestamp("2026-09-30"))
                if f.code == "output.bracket.scheduled_match_missing"]
    assert bool(missing(data)) is not scheduled
    for change in [dict(round="Q3"), dict(espnId="other-2026"),
                   dict(playerA="Unrelated A", playerB="Unrelated B")]:
        unrelated = copy.deepcopy(data)
        unrelated["upcoming"][0].update(change)
        assert missing(unrelated) == []


def test_prestart_partial_field_does_not_invent_a_walkover(monkeypatch):
    # ESPN may not yet name the full field. Only a corroborated replacement may move a slot.
    monkeypatch.setattr(tournaments, "resolve_surface_info", lambda *a, **kw: ("Hard", "wiki"))
    monkeypatch.setattr(tournaments, "resolve_level", lambda *a, **kw: "WTA 1000")
    names = ["Mayar Sherif", "Polina Kudermetova"] + [f"Opponent {i}" for i in range(6)]
    predictor = _Pred({n: 1500 for n in names})
    frame = pd.DataFrame({"date": pd.to_datetime([]), "tourney_name": [], "round": []})
    card = tournaments.project_upcoming(
        predictor, "China Open", {"slots": names, "start": "2026-09-30"}, "wta", frame,
        set(), _canonical, espn_id="959-2026", espn_field=names[1:],
        matchups=[("Opponent 0", "Opponent 1")])
    match = card["bracket"][0]["matches"][0]
    assert match["a"] == "Mayar Sherif" and match["winner"] is None
