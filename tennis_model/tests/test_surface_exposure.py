"""The adopted WTA surface feature must survive every production boundary."""

import copy
import json
import pickle
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from tennis_model.model import artifact
from tennis_model.model.features import FEATURES, antisymmetric_for, features_for, inference_schema_for
from tennis_model.model.predict import TennisPredictor
from tennis_model.model.surface_exposure import (
    SURFACE_FEATURE,
    SURFACE_POLICY,
    SurfaceExposureState,
    validate_surface_state,
    walk_surface_exposure,
)
from test_predictor_artifact import _resign_mutated_payload, _valid_predictor


def test_pre_row_count_completed_boundary_and_no_query_mutation():
    history = pd.DataFrame({
        "date": pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-02", "2025-03-02", "2025-03-03"]),
        "winner_name": ["A"]*5, "loser_name": ["B", "C", "D", "C", "D"],
        "surface_b": ["Hard", "Hard", "Clay", "Hard", "Hard"],
        "completed": [True, False, True, False, True],
    })
    state, values = walk_surface_exposure(history)
    # Same-date earlier completed row counts. Incomplete rows do not add exposure;
    # January 1 is included at day 60 (March 2) and excluded at day 61.
    np.testing.assert_array_equal(values, [0., np.log1p(1), 0., np.log1p(1), 0.])
    before = pickle.dumps(state)
    assert state.query("A", "Unseen", "Hard", "2025-03-04") == np.log1p(1)
    assert state.query("Unseen", "Other", "Hard", "2025-03-04") == 0
    assert state.query("A", "Unseen", "Hard", "2025-05-03") == 0
    assert pickle.dumps(state) == before
    with pytest.raises(ValueError, match="precedes"):
        state.query("A", "B", "Hard", "2025-03-01")
    with pytest.raises(ValueError, match="distinct"):
        state.query("A", "A", "Hard", "2025-03-03")


def test_supported_tour_contract_matches_live_verifier():
    script = Path(__file__).resolve().parents[2]/"web/scripts/model-contract.mjs"
    contracts = json.loads(script.read_text().split("export const MODEL_CONTRACTS = ")[1].rstrip(";\n"))
    for tour in ("atp", "wta"):
        assert contracts[tour] == {"inferenceSchema": inference_schema_for(tour), "features": features_for(tour)}
    assert features_for("atp") == FEATURES
    assert features_for("wta") == [*FEATURES, SURFACE_FEATURE]
    assert SURFACE_FEATURE in antisymmetric_for("wta")
    assert SURFACE_FEATURE not in antisymmetric_for("atp")


@pytest.mark.parametrize("schema,generation,current_signal,expected_error", [
    (None, "old", False, False), (5, "old", False, False),
    (6, "old", True, False), (6, "current", True, False),
    (None, "current", True, False),
    (6, "old", False, True), (None, "current", False, True),
    (5, "current", False, True), (7, "old", True, True),
])
def test_forecast_generation_evidence_migration(surface_predictor, schema, generation,
                                              current_signal, expected_error):
    from tennis_model.data.health import _FindingCollector
    from tennis_model.data.health_checks.predictions import _check_forecast_history
    from tennis_model.eval.track import _forecast_history

    current_id = "11111111-1111-4111-8111-111111111111"
    old_id = "22222222-2222-4222-8222-222222222222"
    evidence = surface_predictor.prediction_evidence("A", "B", as_of="2025-06-01")
    if not current_signal:
        evidence["signals"] = [s for s in evidence["signals"] if s["key"] != "recentSurface"]
    record = {"type": "match", "playerA": "A", "playerB": "B", "p": evidence["probabilityA"],
              "as_of": "2025-06-01T00:00:00Z", "evidence": evidence,
              "predictor_artifact_id": current_id if generation == "current" else old_id}
    if schema is not None:
        record["inference_schema_version"] = schema
    before = copy.deepcopy(record)
    history = _forecast_history([record], "A")
    assert record == before
    if schema is not None:
        assert history["timeline"][0]["inferenceSchemaVersion"] == schema
    out = _FindingCollector("output", "wta")
    _check_forecast_history(out, "wta", "test", history, current_predictor_id=current_id)
    assert bool(out.findings) is expected_error
    if expected_error:
        assert any(f.code in {"output.prediction_evidence.signal_list_invalid",
                              "output.forecast.inference_schema_invalid"} for f in out.findings)


def test_surface_history_reversal_preserves_original_record(surface_predictor):
    from tennis_model.eval.track import _forecast_history

    evidence = surface_predictor.prediction_evidence("A", "B", as_of="2025-06-01")
    record = {"type": "match", "playerA": "A", "playerB": "B", "p": evidence["probabilityA"],
              "as_of": "2025-06-01T00:00:00Z", "evidence": evidence,
              "inference_schema_version": 6}
    before = copy.deepcopy(record)
    history = _forecast_history([record], "B")
    original = next(s["facts"] for s in evidence["signals"] if s["key"] == "recentSurface")
    reversed_facts = next(s["facts"] for s in history["timeline"][0]["evidence"]["signals"]
                          if s["key"] == "recentSurface")
    assert reversed_facts["matchesA"] == original["matchesB"]
    assert reversed_facts["matchesB"] == original["matchesA"]
    assert reversed_facts["logCountDifference"] == -original["logCountDifference"]
    assert record == before


@pytest.fixture(scope="module")
def surface_predictor():
    model = _valid_predictor("wta")
    for elo, ctx, repeats in ((model.elo, model.ctx, 2), (model.lower_elo, model.lower_ctx, 5)):
        elo.n.update(A=40, B=40, C=2)
        elo.last_date = np.datetime64("2025-06-01")
        state = SurfaceExposureState(population="main" if ctx is model.ctx else "enriched")
        for date in pd.date_range("2025-05-01", periods=repeats):
            state.observe("A", "C", "Hard", date, True)
        state.observe("B", "C", "Clay", "2025-06-01", True)
        ctx.surface_exposure = state
    return model


def test_selected_bundle_and_saved_routes(surface_predictor, tmp_path):
    model = surface_predictor
    path = tmp_path/"predictor.pkl"
    model.save(path)
    loaded = TennisPredictor.load("wta", path)
    before = pickle.dumps(loaded)
    assert loaded.features("A", "B")[SURFACE_FEATURE].iloc[0] == np.log1p(2)
    assert loaded.features("A", "Unseen")[SURFACE_FEATURE].iloc[0] == np.log1p(5)
    assert loaded.features("A", "B", as_of="2025-08-02")[SURFACE_FEATURE].iloc[0] == 0
    names = ["A", "B", "C", "Unseen"]
    for surface in ("Hard", "Clay", "Grass"):
        context = {"surface": surface, "as_of": "2025-06-01"}
        matrix = loaded.win_prob_matrix(names, **context)
        np.testing.assert_array_equal(matrix, model.win_prob_matrix(names, **context))
        np.testing.assert_allclose(matrix+matrix.T, 1, rtol=0, atol=1e-15)
        effects = loaded.prediction_evidence_matrices(names, **context)
        for i, a in enumerate(names):
            for j, b in enumerate(names[i+1:], i+1):
                assert loaded.win_prob(a,b,**context) == matrix[i,j]
                assert loaded.prediction_components(a,b,**context)["combiner"] == matrix[i,j]
                pd.testing.assert_frame_equal(loaded.features(a,b,**context),model.features(a,b,**context))
                signal = next(s for s in loaded.prediction_evidence(a,b,**context)["signals"] if s["key"] == "recentSurface")
                assert signal["impactPp"] == round(effects["effects"]["recentSurface"][i,j]*100,2)
    assert pickle.dumps(loaded) == before
    contract = artifact.predictor_contract("wta")
    assert contract["inference"]["schemaVersion"] == 6
    assert contract["inference"]["surfaceExposurePolicy"] == SURFACE_POLICY
    assert len(contract["features"]) == 43


@pytest.mark.parametrize("damage", ["absent", "policy", "cutoff", "order", "nonfinite", "type", "swapped"])
def test_tampered_saved_surface_state_rejected(surface_predictor, tmp_path, damage):
    path = tmp_path/"predictor.pkl"
    surface_predictor.save(path)

    def mutate(model):
        state = model.lower_ctx.surface_exposure
        if damage == "absent":
            del model.lower_ctx.surface_exposure
        elif damage == "policy":
            state.policy = "different-window"
        elif damage == "cutoff":
            state.through += pd.Timedelta(days=1)
        elif damage == "order":
            state.exposure["A"].reverse()
        elif damage == "nonfinite":
            state.exposure["A"].append((pd.NaT, "Hard"))
        elif damage == "swapped":
            model.ctx.surface_exposure, model.lower_ctx.surface_exposure = model.lower_ctx.surface_exposure, model.ctx.surface_exposure
        else:
            state.exposure["A"] = list(state.exposure["A"])

    _resign_mutated_payload(path, mutate)
    with pytest.raises(artifact.PredictorArtifactError):
        TennisPredictor.load("wta", path)


def test_old_wta_contract_rejected_before_deserialization(surface_predictor, tmp_path, monkeypatch):
    path = tmp_path/"predictor.pkl"
    surface_predictor.save(path)
    envelope_path = artifact.predictor_envelope_path(path)
    envelope = json.loads(envelope_path.read_text())
    envelope["contract"]["features"] = FEATURES
    envelope["contract"]["inference"]["schemaVersion"] = 5
    envelope_path.write_text(json.dumps(envelope))
    monkeypatch.setattr(artifact, "_deserialize", lambda _: pytest.fail("deserialized stale WTA model"))
    with pytest.raises(artifact.PredictorArtifactError):
        TennisPredictor.load("wta",path)


def test_surface_state_date_and_shape_validation():
    state = SurfaceExposureState({"A": deque([(pd.Timestamp("2025-01-01"), "Hard")])}, pd.Timestamp("2025-01-01"))
    validate_surface_state(state, np.datetime64("2025-01-01"))
    broken = copy.deepcopy(state)
    broken.exposure["A"].append((pd.Timestamp("2025-03-10"), "Hard"))
    with pytest.raises(ValueError):
        validate_surface_state(broken, state.through)


@pytest.mark.parametrize("tour", ["atp", "wta"])
def test_output_gate_rejects_wrong_feature_order_and_tour_schema(tour):
    from tennis_model.data.health import output_findings
    from test_health import NOW, _oc
    output = _oc()
    meta = output["data"]["meta"]
    meta.update(features=features_for(tour), inferenceSchemaVersion=inference_schema_for(tour))
    codes = lambda: {f.code for f in output_findings(tour, output, NOW)}
    assert "output.meta.feature_schema_mismatch" not in codes()
    assert "output.meta.inference_schema_mismatch" not in codes()
    meta["features"].reverse()
    assert "output.meta.feature_schema_mismatch" in codes()
    meta["inferenceSchemaVersion"] = 5 if tour == "wta" else 6
    assert "output.meta.inference_schema_mismatch" in codes()


def test_wta_matrix_gate_requires_recent_surface_evidence():
    from tennis_model.data.health_checks.common import _FindingCollector
    from tennis_model.data.health_checks.predictions import _check_matrix_evidence
    from test_health import _healthy_shards
    evidence = copy.deepcopy(_healthy_shards()["matrix-hard-bo3.json"]["evidence"])
    findings = _FindingCollector("output", "wta")
    _check_matrix_evidence(findings, "wta", "matrix-hard-bo3.json", evidence, 3)
    assert any(f.code == "output.matrix_evidence.signal_set_invalid" for f in findings.findings)
    evidence["effects"]["recentSurface"] = copy.deepcopy(evidence["effects"]["form"])
    findings = _FindingCollector("output", "wta")
    _check_matrix_evidence(findings, "wta", "matrix-hard-bo3.json", evidence, 3)
    assert not findings.findings
