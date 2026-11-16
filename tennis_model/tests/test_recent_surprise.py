"""Pre-row history, saved queries and inference parity for ATP residual form."""

import copy
import pickle
from collections import deque

import numpy as np
import pandas as pd
import pytest
from tennis_model.model.recent_surprise import (
    SURPRISE_FEATURE,
    RecentSurpriseState,
    validate_surprise_state,
    walk_recent_surprise,
)
from test_probability import predictor


@pytest.mark.parametrize("schema,current,invalid", [
    (6, True, False), (6, False, False), (5, False, False),
    (5, True, True), (7, True, True), (7, False, True),
    ("6", True, True), (None, False, False),
])
def test_atp_timeline_migration_uses_canonical_schema(schema, current, invalid):
    from tennis_model.data.health import _FindingCollector
    from tennis_model.data.health_checks.predictions import _check_forecast_history
    from tennis_model.eval.track import _forecast_history

    current_id = "11111111-1111-4111-8111-111111111111"
    old_id = "22222222-2222-4222-8222-222222222222"
    model = predictor()
    evidence = model.prediction_evidence("Alfa One", "Bravo Two", as_of="2026-08-01")
    record = {"type": "match", "playerA": "Alfa One", "playerB": "Bravo Two",
              "p": evidence["probabilityA"], "as_of": "2026-08-01T00:00:00Z", "evidence": evidence,
              "predictor_artifact_id": current_id if current else old_id}
    if schema is not None:
        record["inference_schema_version"] = schema
    original = copy.deepcopy(record)
    history = _forecast_history([record], "Alfa One")
    assert record == original
    out = _FindingCollector("output", "atp")
    _check_forecast_history(out, "atp", "incident", history, current_predictor_id=current_id)
    codes = {f.code for f in out.findings}
    assert ("output.forecast.inference_schema_invalid" in codes) is invalid
    if not invalid:
        assert not out.findings


def history():
    return pd.DataFrame(
        dict(
            date=pd.to_datetime(["2025-01-01", "2025-01-01", "2025-04-01"]),
            winner_name=["A", "C", "A"],
            loser_name=["B", "A", "B"],
            completed=[True, True, False],
        )
    )


def test_pre_row_semantics_same_day_and_inclusive_boundary():
    state, values = walk_recent_surprise(history(), [0.8, 0.3, 0.99])
    expected = (-0.5 / 7) - (-0.2 / 6)
    np.testing.assert_allclose(values, [0.0, -0.2 / 6, expected], rtol=0, atol=1e-15)
    before = pickle.dumps(state)
    assert state.query("A", "B", "2025-04-01") == pytest.approx(expected)
    assert state.query("B", "A", "2025-04-01") == pytest.approx(-expected)
    assert state.query("A", "B", "2025-04-02") == 0
    assert state.query("Unknown", "Other", "2025-04-01") == 0
    assert pickle.dumps(state) == before
    with pytest.raises(ValueError, match="precedes"):
        state.query("A", "B", "2025-03-31")


def test_prefix_pickle_resume_and_ten_result_cap():
    rows = history()
    p = [0.8, 0.3, 0.99]
    _, all_values = walk_recent_surprise(rows, p)
    state, first = walk_recent_surprise(rows.iloc[:1], p[:1])
    restored = pickle.loads(pickle.dumps(state))
    _, tail = walk_recent_surprise(rows.iloc[1:], p[1:], restored)
    np.testing.assert_array_equal(pd.concat([first, tail]), all_values)
    for _ in range(12):
        restored.observe("A", "B", "2025-04-01", 0.5, True)
    assert len(restored.recent["A"]) == 10
    assert restored.value("A", "2025-04-01") == pytest.approx(5 / 15)
    validate_surprise_state(restored, pd.Timestamp("2025-04-01"))


@pytest.mark.parametrize("damage", ["missing", "policy", "cutoff", "nonfinite", "wrong_type"])
def test_malformed_saved_state_is_rejected(damage):
    state, _ = walk_recent_surprise(history(), [0.8, 0.3, 0.99])
    if damage == "missing":
        state = None
    elif damage == "policy":
        state.policy = "different"
    elif damage == "cutoff":
        state.through = pd.Timestamp("2025-04-02")
    elif damage == "nonfinite":
        state.recent["A"] = deque([(pd.NaT, float("nan"))], maxlen=10)
    else:
        state.recent["A"] = list(state.recent["A"])
    with pytest.raises(ValueError):
        validate_surprise_state(state, pd.Timestamp("2025-04-01"))


def test_nonzero_state_reaches_actual_prediction_features_without_mutation():
    model = predictor("atp")
    state = RecentSurpriseState()
    state.observe("Alfa One", "Bravo Two", "2026-08-01", 0.8, True)
    model.ctx.recent_surprise = state
    before = copy.deepcopy(state)
    row = model.features("Alfa One", "Bravo Two", as_of="2026-08-01")
    assert row.iloc[0][SURPRISE_FEATURE] == pytest.approx(0.4 / 6)
    assert model.features("Bravo Two", "Alfa One", as_of="2026-08-01").iloc[0][SURPRISE_FEATURE] == pytest.approx(
        -0.4 / 6
    )
    assert state == before
