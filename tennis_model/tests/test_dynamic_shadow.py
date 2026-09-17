"""Saved research model, shared serving routes and strict rejection boundaries."""

import copy
import hashlib
import json
import pickle
import struct
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from tennis_model.model import artifact as a
from tennis_model.model import dynamic_research as dr
from tennis_model.model import shadow_artifact as sa
from tennis_model.model.dynamic_shadow import DynamicShadowPredictor
from tennis_model.model.features import FEATURES
from tennis_model.model.predict import TennisPredictor
from tennis_model.model.probability import paired_probability
from tennis_model.model.train import BaggedClassifier, PlattCalibrator, production_xgb_params
from tennis_model.ratings.dynamic import DynamicState
from test_predictor_artifact import _valid_predictor
from xgboost import XGBClassifier

PROVENANCE = {key: str(i) * 64 for i, key in enumerate(sorted(sa.PROVENANCE_FIELDS), 1)}
CONTEXT = {"surface": "Hard", "as_of": "2025-06-01"}


@pytest.fixture(scope="module")
def shadow():
    ordinary = _valid_predictor("wta")
    states = []
    for elo, repeats in ((ordinary.elo, (40, 3)), (ordinary.lower_elo, (60, 40))):
        dynamic = DynamicState()
        for count, pair in zip(repeats, (("A", "B"), ("C", "D")), strict=True):
            for day in pd.date_range("2024-01-01" if pair[0] == "A" else "2024-06-01", periods=count):
                dynamic.observe(*pair, "Hard", as_of=day)
            for name in pair:
                elo.n[name] = count
                elo.last_played[name] = day.to_datetime64()
                elo.overall[name] = 1500 + dynamic.players[name].mean[0] * 100
        elo.last_date = day.to_datetime64()
        states.append(dynamic)
    rng = np.random.default_rng(751)
    x = pd.DataFrame(rng.normal(size=(256, 43)), columns=dr.COLUMNS)
    y = (x.iloc[:, -1] + rng.normal(size=len(x)) > 0).astype(int)
    models = []
    for i in range(5):
        model = XGBClassifier(**production_xgb_params("wta", bag_index=i))
        model.fit(x.iloc[:128], y.iloc[:128], eval_set=[(x.iloc[128:], y.iloc[128:])], verbose=False)
        models.append(model)
    bag = BaggedClassifier(models)
    calibration = PlattCalibrator().fit(bag.predict_proba(x.iloc[128:])[:, 1], y.iloc[128:])
    return DynamicShadowPredictor(
        bag, calibration, ordinary.elo, ordinary.srv, ordinary.ctx, ordinary.meta,
        tour="wta", lower_elo=ordinary.lower_elo, lower_srv=ordinary.lower_srv,
        lower_ctx=ordinary.lower_ctx, dual_state_threshold=32,
        dynamic_main=states[0], dynamic_lower=states[1], shadow_provenance=PROVENANCE,
    )


@pytest.fixture(scope="module")
def saved(shadow, tmp_path_factory):
    directory = tmp_path_factory.mktemp("dynamic-shadow")
    path = directory / "candidate.shadow"
    shadow.save(path, trusted_root=directory)
    return path


def unpack(path):
    content = path.read_bytes()
    size = struct.unpack(">I", content[len(sa.MAGIC):len(sa.MAGIC)+4])[0]
    start = len(sa.MAGIC) + 4
    return json.loads(content[start:start+size]), content[start+size:]


def repack(path, header, payload):
    encoded = json.dumps(header).encode()
    path.write_bytes(sa.MAGIC + struct.pack(">I", len(encoded)) + encoded + payload)


def test_all_prediction_paths_agree_after_strict_roundtrip(shadow, saved):
    loaded = DynamicShadowPredictor.load(saved, expected_provenance=PROVENANCE, trusted_root=saved.parent)
    names = ["A", "B", "C", "D"]
    before = pickle.dumps(loaded)
    original = shadow.prediction_matrices(names, **CONTEXT)["combiner"]
    matrix = loaded.prediction_matrices(names, **CONTEXT)["combiner"]
    np.testing.assert_array_equal(matrix, original)
    np.testing.assert_array_equal(loaded.win_prob_matrix(names, **CONTEXT), matrix)
    np.testing.assert_allclose(matrix + matrix.T, 1, rtol=0, atol=1e-15)
    order = [2, 0, 3, 1]
    permutation = loaded.prediction_matrices([names[i] for i in order], **CONTEXT)["combiner"]
    np.testing.assert_allclose(permutation, matrix[np.ix_(order, order)], rtol=0, atol=1e-15)
    effects = loaded.prediction_evidence_matrices(names, **CONTEXT)
    for i in range(4):
        for j in range(i+1, 4):
            left, right = names[i], names[j]
            feature = loaded.features(left, right, **CONTEXT)
            assert list(feature) == dr.COLUMNS
            expected = dr.probability(loaded.clf, loaded.iso, feature)[0]
            assert loaded.win_prob(left, right, **CONTEXT) == expected == matrix[i, j]
            assert loaded.prediction_components(left, right, **CONTEXT)["combiner"] == expected
            assert loaded.predict(left, right, **CONTEXT)["p_a"] == round(expected, 4)
            evidence = loaded.prediction_evidence(left, right, **CONTEXT)
            assert evidence["probabilityA"] == round(expected, 4)
            for signal in evidence["signals"]:
                assert signal["impactPp"] == round(effects["effects"][signal["key"]][i, j] * 100, 2)
    assert pickle.dumps(loaded) == before


def test_selected_dynamic_state_dates_and_original_features(shadow):
    for pair, state in [(('A', 'B'), shadow.dynamic_main), (('A', 'C'), shadow.dynamic_lower)]:
        frame = shadow.features(*pair, **CONTEXT)
        original = TennisPredictor._feature_dict(shadow, *pair, "Hard", 3, False, 1.0, 3,
                                                as_of=CONTEXT["as_of"])
        np.testing.assert_array_equal(frame[FEATURES].iloc[0], [original[c] for c in FEATURES])
        p = state.win_prob(*pair, as_of=CONTEXT["as_of"])
        assert frame[dr.DYNAMIC_FEATURE].iloc[0] == np.log(p/(1-p))
        with pytest.raises(ValueError, match="precedes"):
            shadow.features(*pair, as_of="2020-01-01")


@pytest.mark.parametrize("tour", ["atp", "wta"])
def test_ordinary_schema_and_probabilities_stay_exact(tour, tmp_path):
    predictor = _valid_predictor(tour)
    feature = predictor.features("A", "B", **CONTEXT)
    assert list(feature) == FEATURES and len(FEATURES) == 42
    expected = paired_probability(predictor.clf, predictor.iso, feature)[0]
    assert predictor.win_prob("A", "B", **CONTEXT) == expected
    predictor.save(tmp_path / "predictor.pkl")
    restored = TennisPredictor.load(tour, tmp_path / "predictor.pkl")
    assert restored.win_prob("A", "B", **CONTEXT) == expected
    assert restored.prediction_components("A", "B", **CONTEXT)["combiner"] == expected
    assert restored.win_prob_matrix(["A", "B"], **CONTEXT)[0, 1] == expected


@pytest.mark.parametrize("corrupt", ["runtime", "schema", "features", "config", "source", "provenance",
                                     "extra", "tour", "size", "hash", "state-receipt"])
def test_incompatible_header_rejected_before_deserialization(saved, tmp_path, monkeypatch, corrupt):
    header, payload = unpack(saved)
    if corrupt == "runtime":
        header["python"]["major"] = 999
    elif corrupt == "schema":
        header["schema"] = "production"
    elif corrupt == "features":
        header["contract"]["features"].reverse()
    elif corrupt == "config":
        header["contract"]["dynamicParams"]["q"] = 0.1
    elif corrupt == "source":
        header["contract"]["sourceSHA256"] = "0" * 64
    elif corrupt == "provenance":
        header["provenance"]["selection"] = "0" * 64
    elif corrupt == "extra":
        header["unregistered"] = True
    elif corrupt == "tour":
        header["tour"] = "atp"
    elif corrupt == "size":
        header["payloadBytes"] += 1
    elif corrupt == "hash":
        payload = payload[:-1] + bytes([payload[-1] ^ 1])
    elif corrupt == "state-receipt":
        del header["states"]["lower"]
    path = tmp_path / "bad.shadow"
    repack(path, header, payload)
    monkeypatch.setattr(a, "_deserialize", lambda _: pytest.fail("unpickled incompatible shadow"))
    with pytest.raises(a.PredictorArtifactError):
        DynamicShadowPredictor.load(path, expected_provenance=PROVENANCE, trusted_root=tmp_path)


@pytest.mark.parametrize("corrupt", ["missing", "none", "params", "covariance", "players", "cutoff",
                                     "swapped", "booster", "identity"])
def test_resigned_invalid_payload_still_fails_structure(saved, tmp_path, corrupt):
    header, payload = unpack(saved)
    predictor = pickle.loads(payload)
    if corrupt == "missing":
        del predictor.dynamic_lower
    elif corrupt == "none":
        predictor.dynamic_lower = None
    elif corrupt == "params":
        predictor.dynamic_main.params = replace(predictor.dynamic_main.params, q=0.1)
    elif corrupt == "covariance":
        predictor.dynamic_main.players["A"].covariance[0, 0] = -1
    elif corrupt == "players":
        del predictor.dynamic_main.players["A"]
    elif corrupt == "cutoff":
        predictor.dynamic_main.last_day += 1
    elif corrupt == "swapped":
        predictor.dynamic_main, predictor.dynamic_lower = predictor.dynamic_lower, predictor.dynamic_main
    elif corrupt == "booster":
        predictor.clf.clfs.pop()
    elif corrupt == "identity":
        predictor.shadow_provenance["selection"] = "0" * 64
    payload = pickle.dumps(predictor)
    header["payloadBytes"], header["payloadSha256"] = len(payload), hashlib.sha256(payload).hexdigest()
    path = tmp_path / "bad.shadow"
    repack(path, header, payload)
    with pytest.raises(a.PredictorArtifactError):
        DynamicShadowPredictor.load(path, expected_provenance=PROVENANCE, trusted_root=tmp_path)


def test_cross_format_loading_and_production_destinations_reject(shadow, saved, tmp_path, monkeypatch):
    with pytest.raises(a.PredictorArtifactError):
        a.validate_predictor_structure(shadow, "wta")
    monkeypatch.setattr(a, "_deserialize", lambda _: pytest.fail("production deserialized shadow"))
    with pytest.raises(a.PredictorArtifactError):
        TennisPredictor.load("wta", saved)
    with pytest.raises(a.PredictorArtifactError):
        shadow.save(sa.OUTPUT_DIR / "candidate.shadow", trusted_root=sa.OUTPUT_DIR)
    with pytest.raises(a.PredictorArtifactError):
        shadow.save(tmp_path / "predictor.pkl", trusted_root=tmp_path)


def test_symlink_trusted_root_and_interrupted_write(saved, shadow, tmp_path, monkeypatch):
    external = tmp_path / "external"
    external.mkdir()
    link = tmp_path / "link"
    link.symlink_to(external, target_is_directory=True)
    with pytest.raises(a.PredictorArtifactError):
        shadow.save(link / "candidate.shadow", trusted_root=link)
    assert not list(external.iterdir())
    with pytest.raises(a.PredictorArtifactError):
        DynamicShadowPredictor.load(saved, expected_provenance=PROVENANCE, trusted_root=external)
    path = tmp_path / "candidate.shadow"
    path.write_bytes(saved.read_bytes())
    before = path.read_bytes()
    def fail_replace(*args, **kwargs):
        raise OSError("simulated interruption before atomic replace")
    monkeypatch.setattr(a.os, "replace", fail_replace)
    with pytest.raises(OSError, match="interruption"):
        shadow.save(path, trusted_root=tmp_path)
    assert path.read_bytes() == before
    assert not list(tmp_path.glob("*.tmp*"))


def test_missing_selected_state_never_falls_back(shadow):
    damaged = copy.copy(shadow)
    damaged.dynamic_lower = None
    with pytest.raises(RuntimeError, match="absent"):
        damaged.features("A", "C", **CONTEXT)
