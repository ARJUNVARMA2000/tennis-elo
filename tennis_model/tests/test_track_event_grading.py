"""An unrelated result cannot settle a known event forecast."""

import pandas as pd
from tennis_model.eval import track
from test_health import NOW, _healthy_data, _oc

from tennis_model.data import health


def test_known_cross_event_result_remains_pending_then_correct_result_grades():
    forecast = dict(
        playerA="Arthur Fils",
        playerB="Taylor Fritz",
        espnId="23-2026",
        round="QF",
        event="Swiss Indoors Basel",
        as_of="2026-11-04",
        p=0.56,
    )
    wrong = dict(
        date=pd.Timestamp("2026-11-05"),
        winner_name="Taylor Fritz",
        loser_name="Arthur Fils",
        completed=True,
        espn_id="13-2026",
        round="R16",
    )
    assert track._grade_matches([forecast], pd.DataFrame([wrong])) == []
    correct = {**wrong, "espn_id": "23-2026", "round": "QF"}
    graded = track._grade_matches([forecast], pd.DataFrame([wrong, correct]))
    assert len(graded) == 1 and graded[0]["resultEspnId"] == "23-2026"


def test_grading_gate_rejects_cross_event_evidence_and_incomplete_coverage():
    data = _healthy_data()
    mf = data["track"]["matchForecasts"]
    mf["graded"] = 1
    mf["gradingEvidence"] = [dict(matchId="one", forecastEventId="23-2026", resultEventId="13-2026")]
    code = "output.forecast.grading_identity_invalid"
    hits = [f for f in health.output_findings("atp", _oc(data=data), NOW) if f.code == code]
    assert hits and health._gate_blocks(hits[0])
    mf["gradingEvidence"][0]["resultEventId"] = "23-2026"
    assert not any(f.code == code for f in health.output_findings("atp", _oc(data=data), NOW))
    mf["gradingEvidence"] = []
    assert any(f.code == code for f in health.output_findings("atp", _oc(data=data), NOW))
