import numpy as np
import pandas as pd
import pytest
from tennis_model.model import dynamic_research as dr
from tennis_model.model.features import FEATURES, make_oriented_xy
from tennis_model.model.probability import paired_probability


def features(n=30):
    values = np.random.default_rng(18).normal(size=(n, 43))
    return pd.DataFrame(values, columns=dr.COLUMNS, index=np.arange(n)*2)


class Classifier:
    best_iteration = 3

    def predict_proba(self, x):
        p = 1/(1+np.exp(-(x.elo_diff.to_numpy() + 0.6)))
        return np.column_stack([1-p, p])


class Calibrator:
    def predict(self, p):
        return p**0.8


def test_orientation_preserves_incumbent_columns_and_adds_one_signed_signal():
    frame = features()
    frame["surface_recent_diff"] = np.arange(len(frame))
    before = frame.copy()
    x, y = dr.oriented(frame, 2010)
    original, original_y = make_oriented_xy(frame[FEATURES], seed=2010)
    pd.testing.assert_frame_equal(x[FEATURES], original, check_exact=True)
    np.testing.assert_array_equal(y, original_y)
    np.testing.assert_array_equal(x[dr.DYNAMIC_FEATURE], frame[dr.DYNAMIC_FEATURE]*np.where(y==0,-1,1))
    pd.testing.assert_frame_equal(dr.reverse(dr.reverse(x)), x, check_exact=True)
    pd.testing.assert_frame_equal(frame, before, check_exact=True)
    assert len(FEATURES) == 42 and dr.DYNAMIC_FEATURE not in FEATURES


def test_probability_exchanges_exactly_and_disabled_path_matches_incumbent():
    frame = features()
    before = frame.copy()
    clf, cal = Classifier(), Calibrator()
    forward = dr.probability(clf, cal, frame)
    backward = dr.probability(clf, cal, dr.reverse(frame))
    np.testing.assert_allclose(forward+backward, 1, rtol=0, atol=1e-15)
    np.testing.assert_array_equal(dr.probability(clf, cal, frame[FEATURES], enabled=False),
                                  paired_probability(clf, cal, frame[FEATURES]))
    pd.testing.assert_frame_equal(frame, before, check_exact=True)


@pytest.mark.parametrize('corruption', ['missing', 'reordered', 'nonfinite'])
def test_research_schema_is_strict_and_is_rejected_by_production(corruption):
    frame = features()
    with pytest.raises(ValueError, match='exact ordered feature schema'):
        paired_probability(Classifier(), Calibrator(), frame)
    if corruption == 'missing':
        frame = frame[FEATURES]
    elif corruption == 'reordered':
        frame = frame[dr.COLUMNS[::-1]]
    else:
        frame.iloc[0, -1] = np.nan
    with pytest.raises(ValueError):
        dr.probability(Classifier(), Calibrator(), frame)


def test_walk_fits_main_state_and_scores_only_paired_selected_state(monkeypatch):
    frame = features(5103).reset_index(drop=True)
    frame['year'] = [2008]*4500+[2009]*600+[2010]*3
    frame['date'] = pd.to_datetime(frame.year.astype(str)+'-01-01')
    frame['winner_name'] = [f'A{i}' for i in range(len(frame))]
    frame['loser_name'] = 'B'
    frame['round_order'] = 1
    frame['tour'], frame['draw_level'], frame['completed'] = 'wta', 'main', True
    selected = frame.copy()
    selected[dr.SIGNED_COLUMNS] += 10
    calls = []

    def fit(core, cal, seed):
        pd.testing.assert_frame_equal(core, frame.iloc[:4500], check_exact=True)
        pd.testing.assert_frame_equal(cal, frame.iloc[4500:5100], check_exact=True)
        assert seed == 2010
        clf = Classifier()
        clf.clfs = [Classifier() for _ in range(5)]
        calls.append(seed)
        return clf, Calibrator()

    monkeypatch.setattr(dr, 'fit_fold', fit)
    out, folds = dr.walk_forward(frame, selected, end_test=2010)
    assert calls == [2010]
    pd.testing.assert_frame_equal(out[dr.COLUMNS], selected.iloc[-3:][dr.COLUMNS].reset_index(drop=True))
    assert folds[0]['core'] == 4500 and folds[0]['calibration'] == 600
    assert not folds[0]['warmupReuse']
    bad = selected.copy()
    bad.loc[0, 'draw_level'] = 'qual'
    with pytest.raises(ValueError):
        dr.walk_forward(frame, bad, end_test=2010)
