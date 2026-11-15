"""Public Austin incident replay and reviewed edition metadata gate controls."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from test_health import _healthy_data, _oc

from tennis_model.data import health

NOW = pd.Timestamp("2026-11-15")
CALENDAR_CODE = "output.bracket.calendar_evidence_insufficient"
TIER_CODE = "output.event.reviewed_tier_mismatch"
CAPTURE = json.loads((Path(__file__).parent / "fixtures/austin_public_draw_20261115.json").read_text())


def _calendar_findings(bracket, tournament=None):
    data = _healthy_data()
    data["brackets"] = [bracket]
    data["tournaments"] = [tournament or {**bracket, "hasBracket": True}]
    return [f for f in health.output_findings("wta", _oc(data=data), NOW)
            if f.code == CALENDAR_CODE]


@pytest.mark.parametrize("source_dates", [False, True])
def test_gate_rejects_published_austin_without_proof_or_with_its_real_march_dates(source_dates):
    bracket = copy.deepcopy(CAPTURE["bracket"])
    assert bracket["espnId"] == "1031-2026"
    assert bracket["drawSourceId"] == "2026 Austin Challenger – Singles"
    if source_dates:
        # Independently witnessed in the main article captured in the paired fixture.
        bracket.update(drawSourceStart="2026-03-09", drawSourceEnd="2026-03-14")
    findings = _calendar_findings(bracket)
    assert len(findings) == 1
    assert findings[0].entity == "espn:1031-2026"
    assert findings[0].severity == "error" and health._gate_blocks(findings[0])
    assert findings[0].evidence["source"] == "wikipedia"


def test_same_draw_with_its_actual_march_calendar_passes_the_calendar_gate():
    # This is a calendar control, not a reconstruction of March's settled results.
    bracket = copy.deepcopy(CAPTURE["bracket"])
    bracket.update(espnId="1063-2026", start="2026-03-08", end="2026-03-15",
                   drawSourceStart="2026-03-09", drawSourceEnd="2026-03-14")
    assert not _calendar_findings(bracket)


def test_gate_uses_the_matched_cards_scheduled_end_instead_of_last_result_date():
    bracket = copy.deepcopy(CAPTURE["bracket"])
    bracket.update(start="2026-03-07", end="2026-03-09",
                   drawSourceStart="2026-03-09", drawSourceEnd="2026-03-14")
    assert _calendar_findings(bracket)
    card = {**bracket, "scheduledEnd": "2026-03-15", "hasBracket": True}
    assert not _calendar_findings(bracket, card)


@pytest.mark.parametrize("artifact", ["tournaments", "brackets", "upcoming"])
@pytest.mark.parametrize("tour,event_id,expected,wrong", [
    ("atp", "339-2026", "Tour Finals", "ATP Tour"),
    ("wta", "904-2026", "WTA 125", "WTA Tour"),
])
def test_gate_rejects_reviewed_tier_drift_across_public_views(artifact, tour, event_id, expected, wrong):
    data = _healthy_data()
    row = data[artifact][0]
    row.update(espnId=event_id, level=wrong)
    findings = health.output_findings(tour, _oc(data=data), NOW)
    hits = [f for f in findings if f.code == TIER_CODE]
    assert len(hits) == 1
    assert hits[0].evidence == {"espnId": event_id, "expected": expected, "actual": [wrong]}
    assert hits[0].severity == "error" and health._gate_blocks(hits[0])
    row["level"] = expected
    assert not any(f.code == TIER_CODE for f in health.output_findings(tour, _oc(data=data), NOW))
    row.update(espnId=event_id.replace("2026", "2027"), level=wrong)
    assert not any(f.code == TIER_CODE for f in health.output_findings(tour, _oc(data=data), NOW))


@pytest.mark.parametrize("tour,event_id,level", [("wta", "339-2026", "WTA Tour"),
                                                 ("atp", "904-2026", "ATP Tour")])
def test_reviewed_tier_gate_does_not_borrow_the_other_tours_event(tour, event_id, level):
    data = _healthy_data()
    data["tournaments"][0].update(espnId=event_id, level=level)
    assert not any(f.code == TIER_CODE for f in health.output_findings(tour, _oc(data=data), NOW))
