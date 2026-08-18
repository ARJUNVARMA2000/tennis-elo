from __future__ import annotations

import numpy as np
import pytest
from tennis_model.sim.bracket import bracket_rounds
from tennis_model.sim.exact import exact_from_slots, propagate_rounds, title_leverage, validate_matrix

PLAYERS = ["A", "B", "C", "D"]
P = np.array([
    [0.5, 0.6, 0.7, 0.8],
    [0.4, 0.5, 0.55, 0.65],
    [0.3, 0.45, 0.5, 0.6],
    [0.2, 0.35, 0.4, 0.5],
])


def test_exact_four_player_probability_conservation_and_known_result():
    rounds = bracket_rounds(PLAYERS, [{
        "winner_name": "A", "loser_name": "B", "round": "SF", "score": "6-4 6-4",
    }])
    result = propagate_rounds(rounds, PLAYERS, P, event_id="event-1")

    assert result["reach"]["A"]["F"] == 1.0
    assert result["reach"]["C"]["F"] == pytest.approx(0.6)
    assert sum(result["champion"].values()) == pytest.approx(1.0)
    assert result["lockableMatchIds"] == ["event-1:r0:m1"]


def test_bye_advances_exactly_and_reach_is_monotone():
    players = ["A", "B", "C"]
    p = P[:3, :3]
    result = exact_from_slots(["A", None, "B", "C"], players, p)
    assert result["reach"]["A"]["SF"] == 1.0
    assert result["reach"]["A"]["F"] == 1.0
    assert result["reach"]["B"]["F"] == pytest.approx(0.55)
    for values in result["reach"].values():
        seq = [values.get(name, 0.0) for name in ("SF", "F", "Champion")]
        assert seq == sorted(seq, reverse=True)


def test_lock_changes_title_distribution_and_tv_leverage():
    rounds = bracket_rounds(PLAYERS, [])
    leverage = title_leverage(rounds, PLAYERS, P, event_id="event-1")
    match = leverage["event-1:r0:m0"]
    assert match["playerA"] == "A" and match["playerB"] == "B"
    assert match["value"] > 0
    assert sum(match["championIfA"].values()) == pytest.approx(1.0)
    assert sum(match["championIfB"].values()) == pytest.approx(1.0)


def test_future_projected_match_cannot_be_locked():
    rounds = bracket_rounds(PLAYERS, [])
    with pytest.raises(ValueError, match="invalid lock"):
        propagate_rounds(
            rounds, PLAYERS, P, event_id="event-1", locks={"event-1:r1:m0": "A"}
        )


def test_matrix_contract_rejects_non_complementary_values():
    bad = P.copy()
    bad[1, 0] = 0.3
    with pytest.raises(ValueError, match=r"P\(a,b\)"):
        validate_matrix(PLAYERS, bad)


def test_json_list_matrix_uses_the_same_exact_contract():
    rounds = bracket_rounds(PLAYERS, [])
    result = propagate_rounds(rounds, PLAYERS, P.tolist(), event_id="event-1")
    assert sum(result["champion"].values()) == pytest.approx(1.0)
