"""Issue #68: future-dated results must not evict a still-retained event."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.eval import track
from tennis_model.model import export
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model.data import event_coverage, health, results

INCIDENT = json.loads((Path(__file__).parent / "fixtures" /
                       "monterrey_retention_incident.json").read_text())


def _frame():
    frame = pd.DataFrame([*INCIDENT["matches"], INCIDENT["futureResult"]])
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


@pytest.mark.parametrize("broken", [True, False])
def test_monterrey_retention_producer_to_gate(monkeypatch, broken):
    frame = _frame()
    names = set(frame.winner_name) | set(frame.loser_name)
    predictor = _Pred({name: 1700.0 for name in names})
    draw = INCIDENT["draw"]
    registry = INCIDENT["registry"]
    build_coverage = event_coverage.build_event_coverage
    build_cards = tournaments.build_tournaments
    monkeypatch.setattr(results, "event_match_view", lambda df, tour: df)
    monkeypatch.setattr(event_coverage, "build_event_coverage", lambda df, tour: build_coverage(
        df, tour, build_date=INCIDENT["asOf"], registry=registry,
        draws={draw["espnId"]: draw}, upcoming_df=pd.DataFrame()))
    monkeypatch.setattr(tournaments, "_load_fields", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming_bounds", lambda tour: {})
    monkeypatch.setattr(tournaments, "_load_tournament_draws",
                        lambda tour: {draw["espnId"]: draw})
    monkeypatch.setattr(tournaments, "load_registry", lambda tour: registry)
    monkeypatch.setattr(track, "_read_log", lambda path: [])
    if broken:
        # Replay the old exporter: selection/identity use the frame's September 17
        # maximum instead of the coverage generation's September 15 build date.
        monkeypatch.setattr(tournaments, "build_tournaments",
                            lambda predictor, df, tour, **kw: build_cards(predictor, df, tour))

    coverage, cards = export.build_event_outputs(predictor, frame, "wta")
    card, = [c for c in cards if c.get("espnId") == "341-2026"]
    data = _healthy_data()
    data.update(tournaments=cards, brackets=[], event_coverage=coverage)
    hits = [f for f in health.output_findings(
        "wta", _oc(data=data), pd.Timestamp(INCIDENT["asOf"]))
        if f.code == "output.event_coverage.shell_only"]
    if broken:
        assert len(hits) == 1 and hits[0].entity == "espn:341-2026"
        assert coverage["shellKeys"] == ["espn:341-2026"]
        assert card["coverageOnly"]
    else:
        assert not hits and coverage["shellKeys"] == []
        assert not card["coverageOnly"]
        assert card["status"] == "completed"
        assert card["champion"] == "Diane Parry"
        assert card["runnerUp"] == "Elise Mertens"
        assert card["drawSize"] == 28 and card["mainDrawMatchCount"] == 27
        assert card["projection"] and card["bracket"]


@pytest.mark.parametrize("build_date, retained", [
    ("2026-09-15", True), ("2026-09-16", True), ("2026-09-17", False),
])
@pytest.mark.parametrize("latest", ["2026-09-13", "2026-09-17"])
def test_retention_boundary_agrees_with_coverage(build_date, retained, latest):
    frame = _frame()
    frame.loc[frame.espn_id == "1024-2026", "date"] = pd.Timestamp(latest)
    selected = dict(tournaments.recent_tournaments(frame, build_date=build_date))
    coverage = event_coverage.build_event_coverage(
        frame, "wta", build_date=build_date, registry=INCIDENT["registry"],
        draws={"341-2026": INCIDENT["draw"]}, upcoming_df=pd.DataFrame())
    expected = {event["espnId"] for event in coverage["events"]}
    assert ("Monterrey" in selected) is retained
    assert ("341-2026" in expected) is retained
    if retained:
        assert len(selected["Monterrey"]) == 27
        assert selected["Monterrey"].date.min() == pd.Timestamp("2026-08-24")
