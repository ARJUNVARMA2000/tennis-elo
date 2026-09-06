"""Exchange invariants exercise independently built inputs and public consumers."""

import numpy as np
import pandas as pd
import pytest
from tennis_model.model.features import ANTISYM, FEATURES, H2HState
from tennis_model.model.predict import TennisPredictor
from tennis_model.model.probability import paired_probability, reverse_features
from tennis_model.points.serve_return import ServeReturnState
from tennis_model.ratings.build import RatingState


class AsymmetricClassifier:
    def predict_proba(self, frame):
        z = .8 + .003 * frame.elo_diff.to_numpy() + .05 * frame.best_of.to_numpy()
        p = 1 / (1 + np.exp(-z))
        return np.column_stack([1 - p, p])


class AsymmetricCalibrator:
    def predict(self, p):
        return .08 + .86 * np.asarray(p)


def predictor(tour="atp", lower=False):
    elo = RatingState()
    elo.overall = {"Alfa One": 1650., "Bravo Two": 1550., "Charlie Three": 1450.}
    elo.n = {"Alfa One": 80, "Bravo Two": 100, "Charlie Three": 2}
    elo.last_date = np.datetime64("2026-08-01")
    srv = ServeReturnState(base={s: .62 for s in ("Hard", "Clay", "Grass")})
    ctx = H2HState({})
    kw = dict(lower_elo=elo, lower_srv=srv, lower_ctx=ctx, dual_state_threshold=32) if lower else {}
    pred = TennisPredictor(AsymmetricClassifier(), AsymmetricCalibrator(), elo, srv, ctx,
                           {}, tour=tour, **kw)
    pred._style_profiles_cache = {}
    return pred


@pytest.mark.parametrize("tour,lower", [("atp", False), ("wta", True)])
@pytest.mark.parametrize("surface,best_of,indoor", [("Hard", 3, False), ("Clay", 5, False),
                                                 ("Grass", 3, True)])
def test_actual_paths_exchange_permutation_and_evidence(tour, lower, surface, best_of, indoor):
    pred = predictor(tour, lower)
    names = ["Alfa One", "Bravo Two", "Charlie Three"]
    kw = dict(surface=surface, best_of=best_of, indoor=indoor, as_of="2026-08-05")
    matrix = pred.prediction_matrices(names, **kw)["combiner"]
    perm = [2, 0, 1]
    other = pred.prediction_matrices([names[i] for i in perm], **kw)["combiner"]
    np.testing.assert_allclose(other, matrix[np.ix_(perm, perm)], atol=1e-12, rtol=0)
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i == j:
                continue
            f, r = pred.features(a, b, **kw), pred.features(b, a, **kw)
            np.testing.assert_allclose(r, reverse_features(f), atol=1e-12, rtol=0)
            direct = pred.win_prob(a, b, **kw)
            assert direct + pred.win_prob(b, a, **kw) == pytest.approx(1., abs=1e-12)
            assert direct == pytest.approx(matrix[i, j], abs=1e-12)
            assert direct == paired_probability(pred.clf, pred.iso, f, r)[0]
            assert direct == pred.prediction_components(a, b, **kw)["combiner"]
            assert round(direct, 4) == pred.prediction_evidence(a, b, **kw)["probabilityA"]
    effects = pred.prediction_evidence_matrices(names, **kw)["effects"]
    reversed_effects = pred.prediction_evidence_matrices(names[::-1], **kw)["effects"]
    for key in effects:
        np.testing.assert_allclose(effects[key], reversed_effects[key][::-1, ::-1],
                                   atol=1e-12, rtol=0)


def test_asymmetric_fixture_reproduces_defect_and_uses_calibrated_average():
    pred = predictor()
    f = pred.features("Alfa One", "Bravo Two")
    r = pred.features("Bravo Two", "Alfa One")
    before = f.copy(deep=True)
    pf = pred.iso.predict(pred.clf.predict_proba(f)[:, 1])
    pr = pred.iso.predict(pred.clf.predict_proba(r)[:, 1])
    assert abs(float(pf[0] + pr[0]) - 1) > .1
    np.testing.assert_array_equal(paired_probability(pred.clf, pred.iso, f, r), .5 * (pf + 1 - pr))
    pd.testing.assert_frame_equal(f, before)
    assert set(ANTISYM) < set(FEATURES)


def test_probability_rejects_bad_schema_nonfinite_and_unpaired_rows():
    pred = predictor()
    f = pred.features("Alfa One", "Bravo Two")
    for bad in (f.iloc[:, ::-1], f.assign(elo_diff=np.nan), f.assign(elo_diff=np.inf)):
        with pytest.raises(ValueError):
            paired_probability(pred.clf, pred.iso, bad)
    with pytest.raises(ValueError, match="paired"):
        paired_probability(pred.clf, pred.iso, f, f.iloc[:0])
    assert paired_probability(pred.clf, pred.iso, f.iloc[:0]).size == 0
