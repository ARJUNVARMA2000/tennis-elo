"""Behavioral and temporal contracts for the isolated uncertainty prototype."""

import copy

import numpy as np
import pandas as pd
import pytest
from tennis_model.ratings.dynamic import (
    DYNAMIC_FEATURE,
    DynamicParams,
    DynamicState,
    attach_dynamic,
    run_dynamic,
)


def history():
    return pd.DataFrame(
        {
            "date": pd.date_range("2015-01-01", periods=8),
            "winner_name": ["A", "B", "A", "C", "A", "B", "A", "C"],
            "loser_name": ["B", "C", "C", "A", "B", "C", "C", "B"],
            "surface_b": ["Hard", "Clay", "Grass", "Hard", "Hard", "Clay", "Grass", "Hard"],
            "completed": [True] * 8,
            "walkover": [False] * 8,
            "tier_k": [1.0] * 8,
            "round_order": [1] * 8,
            "draw_level": ["main"] * 8,
        }
    )


def test_prior_exchange_and_surface_learning():
    state = DynamicState()
    assert state.win_prob("A", "B", as_of="2020-01-01") == pytest.approx(0.5, abs=1e-15)
    for day in pd.date_range("2020-01-01", periods=20):
        state.observe("A", "B", "Hard", as_of=day)
    hard = state.win_prob("A", "B", "Hard", as_of=day)
    clay = state.win_prob("A", "B", "Clay", as_of=day)
    assert 0.5 < clay < hard and hard > 0.85
    for surface in ("Hard", "Clay", "Grass"):
        assert state.win_prob("A", "B", surface, as_of=day) + state.win_prob(
            "B", "A", surface, as_of=day
        ) == pytest.approx(1.0, abs=1e-14)


def test_inactivity_is_a_copied_uncertainty_change_without_mean_drift():
    state = DynamicState(DynamicParams(1.0, 0.001))
    state.observe("A", "B", "Hard", as_of="2020-01-01")
    before = copy.deepcopy(state.to_dict())
    early = state.view("A", "2020-01-01")
    late = state.view("A", "2021-01-01")
    np.testing.assert_array_equal(early.mean, late.mean)
    np.testing.assert_allclose(late.covariance - early.covariance, 0.366 * np.diag([1.0, 0.25, 0.25, 0.25]), atol=1e-14)
    assert state.win_prob("A", "B", as_of="2021-01-01") < state.win_prob("A", "B", as_of="2020-01-01")
    late.mean[:] = 100
    assert state.to_dict() == before


def test_zero_weight_and_unknown_queries_do_not_change_state():
    state = DynamicState()
    before = state.to_dict()
    state.win_prob("Unknown A", "Unknown B", as_of="2025-01-01")
    state.observe("A", "B", "Hard", as_of="2025-01-01", weight=0)
    assert state.to_dict() == before


def test_save_load_and_continued_walk_parity(tmp_path):
    data = history()
    state, all_features = run_dynamic(data)
    prefix, features = run_dynamic(data.iloc[:4])
    path = tmp_path / "state.json"
    prefix.save(path)
    loaded = DynamicState.load(path)
    pd.testing.assert_frame_equal(features, all_features.iloc[:4])
    for row in data.iloc[4:].itertuples():
        assert (
            loaded.win_prob(row.winner_name, row.loser_name, row.surface_b, as_of=row.date)
            == all_features.loc[row.Index, "p_dynamic"]
        )
        loaded.observe(row.winner_name, row.loser_name, row.surface_b, as_of=row.date)
    assert loaded.to_dict() == state.to_dict()
    with pytest.raises(FileExistsError):
        prefix.save(path)


def test_current_outcome_and_future_records_cannot_change_past_features():
    data = history()
    _, original = run_dynamic(data)
    changed = data.copy()
    changed.loc[4, ["winner_name", "loser_name"]] = data.loc[4, ["loser_name", "winner_name"]].to_numpy()
    _, other = run_dynamic(changed)
    np.testing.assert_array_equal(original.loc[:3, "p_dynamic"], other.loc[:3, "p_dynamic"])
    assert original.loc[4, "p_dynamic"] + other.loc[4, "p_dynamic"] == pytest.approx(1.0, abs=1e-14)
    assert not np.array_equal(original.loc[5:, "p_dynamic"], other.loc[5:, "p_dynamic"])
    _, repeat = run_dynamic(data)
    pd.testing.assert_frame_equal(original, repeat, check_exact=True)


def test_saved_state_rejects_backwards_queries_and_bad_history():
    state, _ = run_dynamic(history())
    with pytest.raises(ValueError, match="cutoff"):
        state.win_prob("A", "B", as_of="2014-01-01")
    with pytest.raises(ValueError, match="nondecreasing"):
        run_dynamic(history().iloc[::-1])
    bad = history()
    bad.loc[2, "date"] = pd.NaT
    with pytest.raises(ValueError, match="finite"):
        run_dynamic(bad)


def test_self_match_is_rejected_instead_of_becoming_training_evidence():
    bad = history()
    bad.loc[3, "loser_name"] = bad.loc[3, "winner_name"]
    with pytest.raises(ValueError, match="different players"):
        run_dynamic(bad)


def test_positive_definite_covariance_after_long_mixed_replay():
    state = DynamicState(DynamicParams(0.5, 0.000001))
    names = ["A", "B", "C", "D"]
    rng = np.random.default_rng(13)
    for i in range(600):
        a, b = rng.choice(names, 2, replace=False)
        state.observe(
            a,
            b,
            ("Hard", "Clay", "Grass")[i % 3],
            as_of=pd.Timestamp("2020-01-01") + pd.Timedelta(days=i // 4),
            weight=0.72 if i % 7 == 0 else 1.0,
        )
    for player in state.players.values():
        assert np.linalg.eigvalsh(player.covariance).min() > 0
    assert DynamicState.from_dict(state.to_dict()).to_dict() == state.to_dict()


@pytest.mark.parametrize("sigma,q", [(0, 0), (-1, 0), (1, -1), (np.nan, 0), (1, np.inf)])
def test_invalid_parameters_fail(sigma, q):
    with pytest.raises(ValueError):
        DynamicParams(sigma, q)


@pytest.mark.parametrize("mutation", ["schema", "covariance", "future", "nan"])
def test_corrupt_saved_state_rejected(mutation):
    state, _ = run_dynamic(history())
    value = state.to_dict()
    if mutation == "schema":
        value["schema"] = "production-predictor"
    if mutation == "covariance":
        value["players"]["A"]["covariance"][0][0] = -1
    if mutation == "future":
        value["players"]["A"]["day"] = value["lastDay"] + 1
    if mutation == "nan":
        value["players"]["A"]["mean"][0] = float("nan")
    with pytest.raises(ValueError):
        DynamicState.from_dict(value)


def test_disabled_path_exact_and_selected_state_identity():
    data = history()
    _, main = run_dynamic(data)
    _, lower = run_dynamic(data, DynamicParams(0.5, 0.001))
    base = data.copy()
    base["uses_lower_state"] = [True, False] * 4
    pd.testing.assert_frame_equal(attach_dynamic(base, None, enabled=False), base, check_exact=True)
    out = attach_dynamic(base, main, lower)
    mask = base.uses_lower_state
    np.testing.assert_array_equal(out.loc[mask, DYNAMIC_FEATURE], lower.loc[mask, DYNAMIC_FEATURE])
    np.testing.assert_array_equal(out.loc[~mask, DYNAMIC_FEATURE], main.loc[~mask, DYNAMIC_FEATURE])
    pd.testing.assert_frame_equal(out.drop(columns=DYNAMIC_FEATURE), base, check_exact=True)
    changed = lower.copy()
    changed.loc[0, "winner_name"] = "Wrong player"
    with pytest.raises(ValueError, match="winner_name"):
        attach_dynamic(base, main, changed)


def test_walk_retirement_weight_matches_declared_wta_policy():
    data = history().iloc[:2].copy()
    data.loc[0, "completed"] = False
    state, _ = run_dynamic(data)
    expected = DynamicState()
    for row in data.itertuples():
        expected.observe(
            row.winner_name, row.loser_name, row.surface_b, as_of=row.date, weight=0.72 if not row.completed else 1.0
        )
    assert expected.to_dict() == state.to_dict()


@pytest.mark.parametrize("variance", [0.05, 2.5, 4.0, 4.001, 10.0, 100.0])
def test_projected_moments_match_independent_adaptive_integration(variance):
    from scipy.integrate import quad
    from scipy.special import expit
    from tennis_model.ratings.dynamic import _moments

    for mean, weight in [(-5.0, 0.72), (2.0, 1.0), (0.0, 1.25)]:

        def integrate(fn):
            return quad(lambda z: fn(z) * np.exp(-z * z / 2) / np.sqrt(2 * np.pi), -12, 12, epsabs=1e-12, epsrel=1e-12)[
                0
            ]

        def likelihood(z, mean=mean, weight=weight):
            return expit(mean + np.sqrt(variance) * z) ** weight

        probability = integrate(lambda z, mean=mean: expit(mean + np.sqrt(variance) * z))
        mass = integrate(likelihood)
        first = integrate(lambda z: z * likelihood(z)) / mass
        second = integrate(lambda z: z * z * likelihood(z)) / mass
        expected = (probability, mean + np.sqrt(variance) * first, variance * (second - first * first))
        np.testing.assert_allclose(_moments(mean, variance, weight), expected, rtol=1e-8, atol=1e-9)
