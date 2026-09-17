"""Offline candidate parity and artifact rejection, prepared before fitting."""

import copy
import hashlib
import json
import pickle
import struct

import numpy as np
import pandas as pd
import pytest
import surface_artifact as sa
from historical_signals import SignalState
from signal_combiner import probability
from surface_candidate import COLUMNS, FEATURE, SurfaceCandidatePredictor
from tennis_model.model import artifact as a
from tennis_model.model.features import FEATURES, features_for
from tennis_model.model.predict import TennisPredictor
from tennis_model.model.probability import paired_probability
from tennis_model.model.train import BaggedClassifier, PlattCalibrator, production_xgb_params
from test_predictor_artifact import _valid_predictor
from xgboost import XGBClassifier

CONTEXT = {"surface": "Hard", "as_of": "2024-06-01"}


@pytest.fixture(scope="module")
def candidate():
    ordinary = _valid_predictor("wta")
    states = []
    for elo, repeats in ((ordinary.elo, (40, 3)), (ordinary.lower_elo, (60, 20))):
        state = SignalState()
        rows = []
        for count, pair, start in zip(repeats, (("A", "B"), ("C", "D")), ("2024-04-01", "2024-05-11"), strict=True):
            dates = pd.date_range(start, periods=count)
            rows.extend((date, *pair) for date in dates)
            for name in pair:
                elo.n[name] = count
                elo.last_played[name] = dates[-1].to_datetime64()
                elo.overall[name] = 1500 + count
        for date, winner, loser in sorted(rows):
            state.observe(winner, loser, "Hard", date, 0.6, True, 100, 200)
        elo.last_date = state.through.to_datetime64()
        ctx = ordinary.ctx if elo is ordinary.elo else ordinary.lower_ctx
        ctx.surface_exposure.through = pd.Timestamp(elo.last_date)
        states.append(state)
    rng = np.random.default_rng(751)
    frame = pd.DataFrame(rng.normal(size=(256, 43)), columns=COLUMNS)
    labels = (frame[FEATURE] + rng.normal(size=len(frame)) > 0).astype(int)
    models = []
    for i in range(5):
        model = XGBClassifier(**production_xgb_params("wta", bag_index=i))
        model.fit(frame.iloc[:128], labels.iloc[:128], eval_set=[(frame.iloc[128:], labels.iloc[128:])], verbose=False)
        models.append(model)
    bag = BaggedClassifier(models)
    calibration = PlattCalibrator().fit(bag.predict_proba(frame.iloc[128:])[:, 1], labels.iloc[128:])
    provenance = {key: "1" * 64 for key in sa.PROVENANCE_FIELDS}
    provenance.update(mainState=sa.state_receipt(states[0])["sha256"], lowerState=sa.state_receipt(states[1])["sha256"])
    return SurfaceCandidatePredictor(
        bag,
        calibration,
        ordinary.elo,
        ordinary.srv,
        ordinary.ctx,
        ordinary.meta,
        tour="wta",
        lower_elo=ordinary.lower_elo,
        lower_srv=ordinary.lower_srv,
        lower_ctx=ordinary.lower_ctx,
        dual_state_threshold=32,
        surface_main=states[0],
        surface_lower=states[1],
        surface_provenance=provenance,
    )


@pytest.fixture(scope="module")
def saved(candidate, tmp_path_factory):
    root = tmp_path_factory.mktemp("surface")
    dest = root / "candidate.surface"
    candidate.save(dest, trusted_root=root)
    return dest


def unpack(path):
    data = path.read_bytes()
    start = len(sa.MAGIC) + 4
    size = struct.unpack(">I", data[len(sa.MAGIC) : start])[0]
    return json.loads(data[start : start + size]), data[start + size :]


def repack(path, header, payload):
    header = json.dumps(header).encode()
    path.write_bytes(sa.MAGIC + struct.pack(">I", len(header)) + header + payload)


def test_all_routes_and_read_only_roundtrip(candidate, saved):
    loaded = SurfaceCandidatePredictor.load(
        saved, expected_provenance=candidate.surface_provenance, trusted_root=saved.parent
    )
    names = ["A", "B", "C", "D", "Unseen Alpha", "Unseen Beta"]
    before = pickle.dumps(loaded)
    for surface in ("Hard", "Clay", "Grass"):
        context = {**CONTEXT, "surface": surface}
        matrix = loaded.prediction_matrices(names, **context)["combiner"]
        np.testing.assert_array_equal(matrix, candidate.win_prob_matrix(names, **context))
        np.testing.assert_allclose(matrix + matrix.T, 1, rtol=0, atol=1e-15)
        order = [4, 2, 0, 5, 3, 1]
        permuted = loaded.win_prob_matrix([names[i] for i in order], **context)
        np.testing.assert_allclose(permuted, matrix[np.ix_(order, order)], rtol=0, atol=1e-15)
        effects = loaded.prediction_evidence_matrices(names, **context)
        for i, left in enumerate(names):
            for j, right in enumerate(names[i + 1 :], i + 1):
                frame = loaded.features(left, right, **context)
                pd.testing.assert_frame_equal(frame, candidate.features(left, right, **context))
                assert list(frame) == COLUMNS
                expected = probability(loaded.clf, loaded.iso, frame, (FEATURE,))[0]
                assert loaded.win_prob(left, right, **context) == matrix[i, j] == expected
                assert loaded.prediction_components(left, right, **context)["combiner"] == expected
                assert loaded.predict(left, right, **context)["p_a"] == round(expected, 4)
                evidence = loaded.prediction_evidence(left, right, **context)
                assert evidence["probabilityA"] == round(expected, 4)
                for signal in evidence["signals"]:
                    assert signal["impactPp"] == round(effects["effects"][signal["key"]][i, j] * 100, 2)
                assert loaded.win_prob(right, left, **context) + expected == pytest.approx(1, abs=1e-15)
    assert pickle.dumps(loaded) == before


def test_selected_states_expiry_and_ordinary_features(candidate):
    for pair, state in [
        (("A", "B"), candidate.surface_main),
        (("A", "C"), candidate.surface_lower),
        (("A", "Unseen Alpha"), candidate.surface_lower),
    ]:
        frame = candidate.features(*pair, **CONTEXT)
        ordinary = TennisPredictor._feature_dict(candidate, *pair, "Hard", 3, False, 1.0, 3, as_of=CONTEXT["as_of"])
        np.testing.assert_array_equal(frame[FEATURES].iloc[0], [ordinary[c] for c in FEATURES])
        assert frame[FEATURE].iloc[0] == state.query(*pair, "Hard", CONTEXT["as_of"])[FEATURE]
        assert candidate.features(*pair, as_of="2025-01-01")[FEATURE].iloc[0] == 0
    with pytest.raises(ValueError, match="precedes"):
        candidate.features("A", "C", as_of="2020-01-01")
    damaged = copy.copy(candidate)
    damaged.surface_lower = None
    with pytest.raises(RuntimeError, match="absent"):
        damaged.features("A", "C", **CONTEXT)


@pytest.mark.parametrize("tour", ["atp", "wta"])
def test_production_schema_and_probabilities_stay_exact(tour, tmp_path):
    predictor = _valid_predictor(tour)
    features = predictor.features("A", "B", **CONTEXT)
    expected = paired_probability(predictor.clf, predictor.iso, features)[0]
    assert list(features) == features_for(tour)
    assert len(features.columns) == (43 if tour == "wta" else 42)
    assert predictor.win_prob("A", "B", **CONTEXT) == expected
    path = tmp_path / "predictor.pkl"
    predictor.save(path)
    loaded = TennisPredictor.load(tour, path)
    assert loaded.win_prob_matrix(["A", "B"], **CONTEXT)[0, 1] == expected


@pytest.mark.parametrize(
    "corrupt",
    ["runtime", "schema", "features", "source", "provenance", "tour", "size", "hash", "state-receipt", "extra"],
)
def test_header_rejected_before_unpickling(candidate, saved, tmp_path, monkeypatch, corrupt):
    header, payload = unpack(saved)
    if corrupt == "runtime":
        header["python"]["major"] = 999
    elif corrupt == "schema":
        header["schema"] = "production"
    elif corrupt == "features":
        header["contract"]["features"].reverse()
    elif corrupt == "source":
        header["contract"]["sourceSHA256"] = "0" * 64
    elif corrupt == "provenance":
        header["provenance"]["selection"] = "0" * 64
    elif corrupt == "tour":
        header["tour"] = "atp"
    elif corrupt == "size":
        header["payloadBytes"] += 1
    elif corrupt == "hash":
        payload = payload[:-1] + bytes([payload[-1] ^ 1])
    elif corrupt == "state-receipt":
        header["states"]["main"]["sha256"] = "0" * 64
    elif corrupt == "extra":
        header["extra"] = True
    dest = tmp_path / "bad.surface"
    repack(dest, header, payload)
    monkeypatch.setattr(a, "_deserialize", lambda _: pytest.fail("deserialized invalid artifact"))
    with pytest.raises(a.PredictorArtifactError):
        SurfaceCandidatePredictor.load(dest, expected_provenance=candidate.surface_provenance, trusted_root=tmp_path)


@pytest.mark.parametrize("corrupt", ["missing", "none", "swapped", "future", "value", "booster", "identity"])
def test_resigned_payload_rejected(candidate, saved, tmp_path, corrupt):
    header, payload = unpack(saved)
    model = pickle.loads(payload)
    if corrupt == "missing":
        del model.surface_lower
    elif corrupt == "none":
        model.surface_lower = None
    elif corrupt == "swapped":
        model.surface_main, model.surface_lower = model.surface_lower, model.surface_main
    elif corrupt == "future":
        model.surface_main.through += pd.Timedelta(days=1)
    elif corrupt == "value":
        model.surface_main.exposure["A"].append((pd.Timestamp("2030-01-01"), "Hard"))
    elif corrupt == "booster":
        model.clf.clfs.pop()
    elif corrupt == "identity":
        model.surface_provenance["selection"] = "0" * 64
    payload = pickle.dumps(model)
    header.update(payloadBytes=len(payload), payloadSha256=hashlib.sha256(payload).hexdigest())
    dest = tmp_path / "bad.surface"
    repack(dest, header, payload)
    with pytest.raises(a.PredictorArtifactError):
        SurfaceCandidatePredictor.load(dest, expected_provenance=candidate.surface_provenance, trusted_root=tmp_path)


def test_production_loading_and_destinations_reject(candidate, saved, tmp_path, monkeypatch):
    with pytest.raises(a.PredictorArtifactError):
        a.validate_predictor_structure(candidate, "wta")
    monkeypatch.setattr(a, "_deserialize", lambda _: pytest.fail("production loaded candidate"))
    with pytest.raises(a.PredictorArtifactError):
        TennisPredictor.load("wta", saved)
    with pytest.raises(a.PredictorArtifactError):
        candidate.save(sa.OUTPUT_DIR / "candidate.surface", trusted_root=sa.OUTPUT_DIR)
    with pytest.raises(a.PredictorArtifactError):
        candidate.save(tmp_path / "predictor.pkl", trusted_root=tmp_path)


def test_path_and_atomic_write(candidate, saved, tmp_path, monkeypatch):
    external = tmp_path / "external"
    external.mkdir()
    link = tmp_path / "link"
    link.symlink_to(external, target_is_directory=True)
    with pytest.raises(a.PredictorArtifactError):
        candidate.save(link / "candidate.surface", trusted_root=link)
    assert not list(external.iterdir())
    with pytest.raises(a.PredictorArtifactError):
        SurfaceCandidatePredictor.load(saved, expected_provenance=candidate.surface_provenance, trusted_root=external)
    dest = tmp_path / "candidate.surface"
    dest.write_bytes(saved.read_bytes())
    before = dest.read_bytes()

    def fail_replace(*args, **kwargs):
        raise OSError("simulated interruption")

    monkeypatch.setattr(a.os, "replace", fail_replace)
    with pytest.raises(OSError, match="interruption"):
        candidate.save(dest, trusted_root=tmp_path)
    assert dest.read_bytes() == before
