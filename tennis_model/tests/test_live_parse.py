"""Unit checks for data/live ESPN scoreboard parsing — canned fixture, no network.

Runnable directly (`python tests/test_live_parse.py`) or under pytest. Covers
round-label mapping, winner-perspective score strings, and parse_events /
parse_upcoming / parse_fields over a synthetic events payload mirroring ESPN's
schema (events -> groupings -> competitions -> competitors).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.live as live


# ---------------------------------------------------------------------------
# fixture builders (ESPN scoreboard schema)
# ---------------------------------------------------------------------------
def _completed(rnd, winner, w_sets, loser, l_sets, date="2026-06-08T13:00Z"):
    return {
        "status": {"type": {"state": "post", "completed": True}},
        "round": {"displayName": rnd},
        "date": date,
        "competitors": [
            {"winner": True, "athlete": {"displayName": winner},
             "linescores": [{"value": float(v)} for v in w_sets]},
            {"winner": False, "athlete": {"displayName": loser},
             "linescores": [{"value": float(v)} for v in l_sets]},
        ],
    }


def _pending(rnd, a, b, state="pre", date="2026-06-09T11:00Z"):
    return {
        "status": {"type": {"state": state, "completed": False}},
        "round": {"displayName": rnd},
        "date": date,
        "competitors": [
            {"athlete": ({"displayName": n} if n else {})} for n in (a, b)
        ],
    }


def _events():
    final = _completed("Final", "Aaron Ace", (6, 6), "Bob Baseline", (3, 4))
    semi = _completed("Semifinal", "Aaron Ace", (7, 6), "Carl Clay", (6, 4))
    qual = _completed("Qualifying - 1st Round", "Quinn Qual", (6, 6), "Q Two", (1, 1))
    test_open = {
        "id": "100", "shortName": "Test Open",
        "groupings": [
            {"grouping": {"slug": "mens-singles"},
             "competitions": [
                 final, semi,
                 dict(final),                                   # exact duplicate -> dedup
                 qual,                                          # qualifying -> dropped
                 _pending("Quarterfinal", "Aaron Ace", "Dave Drop", state="in"),
                 _pending("Quarterfinal", "Bob Baseline", "Carl Clay", state="pre"),
                 _pending("Quarterfinal", "Known Player", None, state="pre"),  # TBD
             ]},
            {"grouping": {"slug": "mens-doubles"},               # doubles -> dropped
             "competitions": [_completed("Final", "Duo One", (6, 6), "Duo Two", (2, 2))]},
            {"grouping": {"slug": "womens-singles"},             # other tour
             "competitions": [_completed("Final", "Wendy Winner", (6, 6),
                                         "Lucy Loser", (2, 2))]},
        ],
    }
    big_slam = {
        "id": "200", "name": "Big Slam",
        "groupings": [
            {"grouping": {"slug": "mens-singles"},
             "competitions": [
                 _completed("Round of 16", f"Winner {i}", (6, 6), f"Loser {i}", (3, 4))
                 for i in range(4)
             ]},
        ],
    }
    return [test_open, big_slam]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def test_round_label():
    assert live._round_label("Final") == "F"
    assert live._round_label("Semifinal") == "SF"
    assert live._round_label("Semifinals") == "SF"
    assert live._round_label("Quarterfinal") == "QF"
    assert live._round_label("Round of 16") == "R16"
    assert live._round_label("3rd Round") == "R32"
    assert live._round_label("2nd Round") == "R64"
    assert live._round_label("1st Round") == "R128"
    # qualifying always drops, even when it mentions a round number
    assert live._round_label("Qualifying - 1st Round") is None
    assert live._round_label("Qualifying") is None
    # unrecognised main-draw name -> generic round
    assert live._round_label("") == "R64"
    print("ok test_round_label")


def test_score_winner_perspective():
    # winner-perspective games, sets space-separated, tiebreak points never shown
    assert live._score([{"value": 6.0}, {"value": 7.0}],
                       [{"value": 3.0}, {"value": 6.0}]) == "6-3 7-6"
    # an unscored set (value None) is skipped rather than crashing
    assert live._score([{"value": 6}, {"value": None}],
                       [{"value": 3}, {"value": 2}]) == "6-3"
    assert live._score(None, None) == ""
    print("ok test_score_winner_perspective")


def test_parse_events_completed_singles_only():
    df = live.parse_events(_events(), "mens")
    assert len(df) == 6, df                      # 2 Test Open + 4 Big Slam, dup dropped
    to = df[df["tourney_name"] == "Test Open"]
    assert len(to) == 2 and set(to["round"]) == {"F", "SF"}, to
    f = to[to["round"] == "F"].iloc[0]
    assert f["winner_name"] == "Aaron Ace" and f["loser_name"] == "Bob Baseline"
    assert f["score"] == "6-3 6-4"
    assert f["tourney_date"] == "2026-06-08"     # YYYY-MM-DD prefix of the ISO stamp
    sf = to[to["round"] == "SF"].iloc[0]
    assert sf["score"] == "7-6 6-4"              # tiebreak points dropped
    # doubles / other tour / qualifying / unfinished never leak through
    names = set(df["winner_name"]) | set(df["loser_name"])
    assert not names & {"Duo One", "Wendy Winner", "Quinn Qual", "Dave Drop"}, names
    bs = df[df["tourney_name"] == "Big Slam"]
    assert len(bs) == 4 and set(bs["round"]) == {"R16"}, bs
    print("ok test_parse_events_completed_singles_only")


def test_parse_events_other_tour():
    df = live.parse_events(_events(), "womens")
    assert len(df) == 1, df
    assert df.iloc[0]["winner_name"] == "Wendy Winner"
    assert df.iloc[0]["loser_name"] == "Lucy Loser"
    print("ok test_parse_events_other_tour")


def test_parse_upcoming():
    up = live.parse_upcoming(_events(), "mens")
    assert len(up) == 2, up
    pairs = {(r.playerA, r.playerB) for r in up.itertuples()}
    assert ("Aaron Ace", "Dave Drop") in pairs        # in-progress kept
    assert ("Bob Baseline", "Carl Clay") in pairs     # scheduled kept
    # completed matches and TBD matchups are excluded
    assert "Known Player" not in {n for p in pairs for n in p}
    assert set(up["round"]) == {"QF"}
    print("ok test_parse_upcoming")


def test_parse_fields():
    fields = live.parse_fields(_events(), "mens")
    # Test Open has < 8 known players -> only Big Slam qualifies as a live field
    assert set(fields) == {"Big Slam"}, fields
    bs = fields["Big Slam"]
    assert bs["field"] == sorted([f"Winner {i}" for i in range(4)]
                                 + [f"Loser {i}" for i in range(4)])
    assert bs["eliminated"] == sorted(f"Loser {i}" for i in range(4))
    print("ok test_parse_fields")


if __name__ == "__main__":
    test_round_label()
    test_score_winner_perspective()
    test_parse_events_completed_singles_only()
    test_parse_events_other_tour()
    test_parse_upcoming()
    test_parse_fields()
    print("\nALL PASSED")
