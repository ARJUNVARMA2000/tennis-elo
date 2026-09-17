import numpy as np
import pandas as pd
import pytest
from historical_errors import diagnose, oriented


def sample():
    return pd.DataFrame(
        {
            "year": [2010, 2011, 2012, 2013],
            "date": pd.to_datetime(["2010-01-01", "2011-01-01", "2012-01-01", "2013-01-01"]),
            "winner_name": ["A", "B", "A", "B"],
            "loser_name": ["B", "A", "B", "A"],
            "round_order": [1] * 4,
            "p_combiner": [0.8, 0.4, 0.6, 0.9],
            "log_min_matches": np.log1p([0, 32, 128, 512]),
            "max_days_since": [1, 20, 80, 400],
            "log_min_srv_pts": np.log1p([0, 1, 100, 1000]),
            "tier_k": [1.0] * 4,
            "round": ["R32"] * 4,
            "surf_hard": [1] * 4,
            "surf_clay": [0] * 4,
            "surf_grass": [0] * 4,
            "uses_lower_state": [False, True, False, True],
        }
    )


def test_orientation_uses_players_not_winner_position():
    o = oriented(sample())
    np.testing.assert_allclose(o.p_a, [0.8, 0.6, 0.6, 0.1])
    np.testing.assert_array_equal(o.y_a, [1, 0, 1, 0])
    np.testing.assert_allclose(o.logloss, -np.log(sample().p_combiner))
    # Rename both players to reverse the canonical slot; losses/confidence must agree.
    f = sample().replace({"winner_name": {"A": "Z", "B": "Y"}, "loser_name": {"A": "Z", "B": "Y"}})
    reverse = oriented(f)
    np.testing.assert_allclose(reverse.p_a, 1 - o.p_a)
    np.testing.assert_allclose(reverse.y_a, 1 - o.y_a)
    np.testing.assert_allclose(reverse.confidence, o.confidence)
    np.testing.assert_allclose(reverse.correct, o.correct)


@pytest.mark.parametrize("year", [2009, 2020, 2026])
def test_refuses_outside_tuning_years(year):
    f = sample()
    f.loc[0, "year"] = year
    with pytest.raises(ValueError, match="2010-2019"):
        oriented(f)


@pytest.mark.parametrize("p", [0, 1, float("nan"), float("inf")])
def test_refuses_invalid_probability(p):
    f = sample()
    f.loc[0, "p_combiner"] = p
    with pytest.raises(ValueError, match="probabilities"):
        oriented(f)


def test_count_boundary_and_missing_bins_preserve_population():
    result = diagnose(sample())
    r = result[result.window.eq("tune")]
    cells = r[r.slice.str.startswith("experience:")]
    assert cells.n.sum() == 4
    assert cells[cells.slice.str.startswith("experience:[")].n.tolist() == [1, 1, 1, 1]
    assert r.loc[r.slice.eq("all"), "accuracy"].iloc[0] == 0.75


def test_duplicate_match_rejected():
    f = sample()
    f = pd.concat([f, f.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError):
        oriented(f)
