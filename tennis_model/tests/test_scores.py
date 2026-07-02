"""Unit checks for data/scores.parse_score — the completed/walkover flags feed the
rating walk, dedup keys and the health sentinel everywhere.

Runnable directly (`python tests/test_scores.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.scores import game_diff, parse_score


def test_straight_sets_completed():
    r = parse_score("6-2 6-1")
    assert r.completed and not r.walkover
    assert r.winner_games == 12 and r.loser_games == 3 and r.sets == 2
    assert game_diff(r) == 9
    print("ok test_straight_sets_completed")


def test_tiebreak_digits_ignored_in_games():
    r = parse_score("7-6(4) 6-3")
    assert r.completed and r.winner_games == 13 and r.loser_games == 9
    print("ok test_tiebreak_digits_ignored_in_games")


def test_retirement_not_completed_not_walkover():
    r = parse_score("6-3 3-2 RET")
    assert not r.completed and not r.walkover
    assert r.winner_games == 9 and r.loser_games == 5    # games still counted
    print("ok test_retirement_not_completed_not_walkover")


def test_pure_walkover():
    r = parse_score("W/O")
    assert r.walkover and not r.completed and r.sets == 0
    print("ok test_pure_walkover")


def test_missing_score_is_walkover_sentinel():
    for bad in (None, "", "   ", float("nan")):
        r = parse_score(bad)
        assert r.walkover and not r.completed, bad
    print("ok test_missing_score_is_walkover_sentinel")


def test_super_tiebreak_bracket_skipped():
    r = parse_score("2-6 6-3 [10-7]")
    assert r.completed and r.sets == 2                  # bracket fragment is not a set
    assert r.winner_games == 8 and r.loser_games == 9   # deciding-TB wins can trail on games
    print("ok test_super_tiebreak_bracket_skipped")


if __name__ == "__main__":
    test_straight_sets_completed()
    test_tiebreak_digits_ignored_in_games()
    test_retirement_not_completed_not_walkover()
    test_pure_walkover()
    test_missing_score_is_walkover_sentinel()
    test_super_tiebreak_bracket_skipped()
    print("\nALL PASSED")
