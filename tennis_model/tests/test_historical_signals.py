import pickle

import numpy as np
import pandas as pd
import pytest
from historical_signals import SIGNALS, SignalState, attach_signals, walk_signals
from signal_combiner import columns, oriented, probability, reverse
from tennis_model.model.features import FEATURES, make_oriented_xy


def history():
    return pd.DataFrame({
        "winner_name": ["A", "B", "A", "A"], "loser_name": ["B", "A", "B", "B"],
        "date": pd.to_datetime(["2010-01-01", "2010-01-02", "2010-04-02", "2010-04-03"]),
        "surface_b": ["Clay", "Hard", "Hard", "Hard"], "completed": [True, False, True, True],
        "winner_rank_points": [100., 200., 200., 200.],
        "loser_rank_points": [200., 100., 200., 200.], "draw_level": ["main"] * 4,
    })


def test_walk_queries_before_result_and_excludes_unfinished_from_form():
    _, f = walk_signals(history(), [.8, .3, .6, .7])
    np.testing.assert_array_equal(f.iloc[0], np.zeros(3))
    assert f.recent_surprise_diff.iloc[1] == pytest.approx(-.4 / 6)
    # The old completed result expired; the unfinished row contributes no form.
    assert f.recent_surprise_diff.iloc[2] == 0
    assert f.surface_recent_diff.iloc[2] == 0
    assert f.rank_trend_diff.iloc[2] == pytest.approx(np.log(201 / 101))


def test_prefix_serialization_and_continuation():
    h = history(); p = [.8, .3, .6, .7]
    full, expected = walk_signals(h, p)
    part, first = walk_signals(h.iloc[:2], p[:2])
    restored = pickle.loads(pickle.dumps(part))
    restored, last = walk_signals(h.iloc[2:], p[2:], restored)
    pd.testing.assert_frame_equal(pd.concat([first, last]), expected)
    assert restored.query("A", "B", "Hard", "2010-04-04", 200, 200) == full.query(
        "A", "B", "Hard", "2010-04-04", 200, 200)


def test_future_results_do_not_change_prefix():
    h = history(); _, first = walk_signals(h, [.8, .3, .6, .7])
    h.loc[3, ["winner_name", "loser_name"]] = ["C", "D"]
    _, second = walk_signals(h, [.8, .3, .6, .1])
    pd.testing.assert_frame_equal(first.iloc[:3], second.iloc[:3])


def test_query_is_read_only_antisymmetric_and_expires():
    state = SignalState()
    state.observe("A", "C", "Clay", "2010-01-01", .8, True, 100, 100)
    state.observe("A", "C", "Clay", "2010-04-01", .6, True, 200, 100)
    before = pickle.dumps(state)
    a = state.query("A", "C", "Clay", "2010-04-02", 200, 100)
    b = state.query("C", "A", "Clay", "2010-04-02", 100, 200)
    np.testing.assert_allclose(list(a.values()), -np.array(list(b.values())))
    assert state.query("A", "C", "Clay", "2012-01-01", 300, 100) == dict.fromkeys(SIGNALS, 0)
    assert pickle.dumps(state) == before


def test_recent_surface_is_temporal_and_surface_specific():
    state = SignalState()
    state.observe("A", "C", "Clay", "2010-01-01", .8, True)
    state.observe("B", "D", "Hard", "2010-01-02", .6, True)
    assert state.query("A", "B", "Clay", "2010-01-03")["surface_recent_diff"] == np.log(2)
    assert state.query("A", "B", "Hard", "2010-01-03")["surface_recent_diff"] == -np.log(2)
    assert state.query("A", "B", "Grass", "2010-01-03")["surface_recent_diff"] == 0


def test_recent_form_is_opponent_adjusted_and_last_ten():
    state = SignalState()
    for day in range(1, 13):
        state.observe("A", "C", "Clay", f"2010-01-{day:02}", .9 if day < 3 else .6, True)
        state.observe("B", "D", "Clay", f"2010-01-{day:02}", .8, True)
    result = state.query("A", "B", "Clay", "2010-01-13")
    assert result["recent_surprise_diff"] == pytest.approx((10 * .4 - 10 * .2) / 15)


@pytest.mark.parametrize("points", [None, np.nan, 0, -1])
def test_missing_rank_pair_is_neutral(points):
    state, _ = walk_signals(history(), [.8, .3, .6, .7])
    assert state.query("A", "B", "Hard", "2010-04-04", points, 200)["rank_trend_diff"] == 0


def test_invalid_order_and_identity_rejected():
    state, _ = walk_signals(history(), [.8, .3, .6, .7])
    with pytest.raises(ValueError, match="precedes"):
        state.query("A", "B", "Hard", "2009-01-01")
    with pytest.raises(ValueError, match="distinct"):
        state.query("A", "A", "Hard", "2010-04-04")
    with pytest.raises(ValueError, match="lengths"):
        walk_signals(history(), [.8])


def test_attacher_refuses_misaligned_match_identity():
    h = history(); _, signals = walk_signals(h, [.8, .3, .6, .7])
    base = h.drop(columns="surface_b")
    assert list(attach_signals(base, h, signals).columns[-3:]) == list(SIGNALS)
    base.loc[0, "winner_name"] = "someone else"
    with pytest.raises(AssertionError):
        attach_signals(base, h, signals)


@pytest.mark.parametrize("extra", [(), *(tuple([s]) for s in SIGNALS)])
def test_orientation_mirrors_incumbent(extra):
    f = pd.DataFrame(np.arange(20 * len(FEATURES)).reshape(20, -1) / 100, columns=FEATURES)
    for s in SIGNALS:
        f[s] = np.arange(20) / 10
    x, y = oriented(f, 2010, extra)
    old, oldy = make_oriented_xy(f, seed=2010)
    pd.testing.assert_frame_equal(x[FEATURES], old)
    np.testing.assert_array_equal(y, oldy)
    for s in extra:
        np.testing.assert_array_equal(x[s], f[s] * np.where(y, 1, -1))
    pd.testing.assert_frame_equal(reverse(reverse(x, extra), extra), x)


def test_calibrated_pair_symmetry_with_asymmetric_classifier():
    extra = (SIGNALS[0],)
    f = pd.DataFrame(np.zeros((4, 43)), columns=columns(extra))
    f[extra[0]] = [-.8, -.1, .3, .7]

    class Classifier:
        def predict_proba(self, x):
            p = .6 + .1 * x[extra[0]].to_numpy()
            return np.column_stack([1 - p, p])

    class Calibration:
        def predict(self, p):
            return p ** 2

    p = probability(Classifier(), Calibration(), f, extra)
    q = probability(Classifier(), Calibration(), reverse(f, extra), extra)
    np.testing.assert_allclose(p + q, 1, atol=1e-15)
    assert probability(Classifier(), Calibration(), f.iloc[:0], extra).size == 0
    with pytest.raises(ValueError, match="one registered"):
        columns(SIGNALS)
