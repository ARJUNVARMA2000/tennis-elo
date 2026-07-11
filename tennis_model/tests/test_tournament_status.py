"""drawStatus propagation through project_tournament / project_upcoming (synthetic, no net).

Pins the honest label the web reads: a live event runs "real" when its draw is known
(Wikipedia slots, or ESPN matchups that seat the whole frontier), "partial"/"seeded" when
only some / none of the frontier is posted, and "final" once complete. A Wikipedia draw
turns an otherwise-"seeded" board "real" and surfaces a not-yet-started event as "upcoming".
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.sim.tournaments import (
    _dedup_by_display_name,
    build_tournaments,
    project_tournament,
    project_upcoming,
)

_R = {f"P{i}": 2000.0 - 30.0 * i for i in range(16)}   # P0 strongest .. P15 weakest


class _Pred:
    class _Elo:
        def __init__(self, r):
            self.r = r
            self.overall = dict(r)          # names -> rating (build_tournaments' top_set source)

        def blended(self, name, surf):
            return self.r.get(name, 1500.0)

        def elo(self, name):
            return self.r.get(name, 1500.0)

    def __init__(self, r):
        self.elo = self._Elo(r)

    def win_prob_matrix(self, players, surface="Hard", best_of=3,
                        indoor=False, tier_k=1.0, event=None):
        n = len(players)
        P = np.full((n, n), 0.5)
        for i in range(n):
            for j in range(n):
                if i != j:
                    d = self.elo.r.get(players[i], 1500.0) - self.elo.r.get(players[j], 1500.0)
                    P[i, j] = 1.0 / (1.0 + 10.0 ** (-d / 400.0))
        return P


_PRED = _Pred(_R)


def _g(add_final=False):
    """A live 'Test Open': 8 first-round results (P0..P7 beat P8..P15), no final."""
    rows = [dict(tourney_name="Test Open", date=pd.Timestamp("2026-08-03"), round="R64",
                 winner_name=f"P{i}", loser_name=f"P{8 + i}", surface_b="Hard",
                 best_of=3, tourney_level="250") for i in range(8)]
    if add_final:
        rows.append(dict(tourney_name="Test Open", date=pd.Timestamp("2026-08-09"), round="F",
                         winner_name="P0", loser_name="P1", surface_b="Hard",
                         best_of=3, tourney_level="250"))
    return pd.DataFrame(rows)


def _project(matchups, wiki_draw=None, add_final=False):
    return project_tournament(_PRED, "Test Open", _g(add_final), "atp", known=set(),
                              top_set=None, espn_fields=None, resolve=lambda n: n,
                              matchups=matchups, wiki_draw=wiki_draw, n_sims=200, seed=1)


def test_status_real_partial_seeded_final_from_espn():
    alive_pairs = [("P0", "P1"), ("P2", "P3"), ("P4", "P5"), ("P6", "P7")]
    assert _project(alive_pairs)["drawStatus"] == "real"      # full frontier posted
    assert _project([("P0", "P1")])["drawStatus"] == "partial"  # 1 pair + 6 singles = 7 units
    assert _project([])["drawStatus"] == "seeded"             # nothing posted -> rating seed
    fin = _project([], add_final=True)
    assert fin["status"] == "completed" and fin["drawStatus"] == "final"
    print("ok test_status_real_partial_seeded_final_from_espn")


def test_completed_projection_excludes_qualifying_field():
    """A completed Slam still projects its 128-player main draw, not qualifying rows."""
    rows = []
    for i in range(64):
        rows.append(dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-01"),
                         round="R128", winner_name=f"M{i}", loser_name=f"M{64 + i}",
                         surface_b="Grass", best_of=3, tourney_level="G", draw_level="main"))
    rows.append(dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-11"),
                     round="F", winner_name="M0", loser_name="M1", surface_b="Grass",
                     best_of=3, tourney_level="G", draw_level="main"))
    for i in range(20):
        rows.append(dict(tourney_name="Test Slam", date=pd.Timestamp("2026-06-25"),
                         round="Q1", winner_name=f"Q{i}", loser_name=f"Q{20 + i}",
                         surface_b="Grass", best_of=3, tourney_level="Q",
                         draw_level="main"))  # legacy/source default: provenance is unreliable

    t = project_tournament(_PRED, "Test Slam", pd.DataFrame(rows), "wta", known=set(),
                           top_set=None, n_sims=10, seed=1)
    assert t["status"] == "completed" and t["drawSize"] == 128
    assert t["champion"] == "M0" and all(p["name"].startswith("M") for p in t["projection"])
    print("ok test_completed_projection_excludes_qualifying_field")


def test_oversized_projection_error_names_event_and_source_state():
    """An invalid source grouping must fail with actionable context, not KeyError: 256."""
    rows = [dict(tourney_name="Merged Event", date=pd.Timestamp("2026-07-01"),
                 round="R128", winner_name=f"P{i}", loser_name=f"P{65 + i}",
                 surface_b="Hard", best_of=3, tourney_level="250", draw_level="main")
            for i in range(65)]
    rows.append(dict(tourney_name="Merged Event", date=pd.Timestamp("2026-07-11"),
                     round="F", winner_name="P0", loser_name="P1", surface_b="Hard",
                     best_of=3, tourney_level="250", draw_level="main"))
    with pytest.raises(ValueError, match=(
            r"wta tournament 'Merged Event': invalid 256-slot bracket .*"
            r"field=130.*completed=True.*draw_state=final.*wiki_slots=0")):
        project_tournament(_PRED, "Merged Event", pd.DataFrame(rows), "wta", known=set(),
                           top_set=None, n_sims=10, seed=1)
    print("ok test_oversized_projection_error_names_event_and_source_state")


def test_wiki_draw_makes_a_seeded_board_real():
    """Same event, no ESPN matchups (-> would be 'seeded'), but a Wikipedia ordered draw is
    available: the board runs on the real bracket and reports 'real'."""
    wslots = []
    for i in range(8):                     # (winner, loser) pairs consistent with _g()
        wslots += [f"P{i}", f"P{8 + i}"]
    t = _project([], wiki_draw={"slots": wslots, "bestOf": 3})
    assert t["status"] == "live" and t["drawStatus"] == "real"
    assert _project([])["drawStatus"] == "seeded"            # contrast: without the wiki draw
    print("ok test_wiki_draw_makes_a_seeded_board_real")


def test_prestart_upcoming_projection_from_wiki():
    wd = {"slots": [f"P{i}" for i in range(16)], "bestOf": 3,
          "start": "2026-08-10", "end": "2026-08-16"}
    t = project_upcoming(_PRED, "Future Open", wd, "atp", pd.DataFrame(), set(),
                         lambda n: n, n_sims=200, seed=1)
    assert t["status"] == "upcoming" and t["drawStatus"] == "real"
    assert t["drawSize"] == 16 and t["aliveCount"] == 16 and t["champion"] is None
    assert t["modelFavorite"] == "P0" and t["projection"][0]["name"] == "P0"   # strongest leads
    print("ok test_prestart_upcoming_projection_from_wiki")


def test_dedup_by_display_name_keeps_fuller_draw():
    """The naming/dedup split that reddened the daily refresh: the same event under an archive
    city name and an ESPN sponsor title, collapsed by _display_name to one shown name. Keep the
    fuller-draw archive record and drop the partial live fragment, whichever order they arrive;
    never collapse two genuinely distinct events that merely run the same week."""
    archive = {"name": "Bad Homburg", "level": "WTA 500", "drawSize": 28,
               "champion": "Naomi Osaka", "status": "completed"}
    fragment = {"name": "Bad Homburg", "level": "WTA Tour", "drawSize": 9,
                "champion": "Karolina Muchova", "status": "completed"}
    for entries in ([archive, fragment], [fragment, archive]):
        kept = _dedup_by_display_name(entries, "wta")
        assert len(kept) == 1
        assert kept[0]["drawSize"] == 28 and kept[0]["champion"] == "Naomi Osaka"
    both = _dedup_by_display_name(
        [{"name": "Eastbourne", "level": "WTA 500", "drawSize": 28},
         {"name": "Mallorca", "level": "WTA 250", "drawSize": 28}], "wta")
    assert len(both) == 2
    print("ok test_dedup_by_display_name_keeps_fuller_draw")


def test_build_tournaments_collapses_archive_and_sponsor_feed():
    """End-to-end: one event reaching build_tournaments under BOTH its archive city name and the
    live/ESPN sponsor title must ship as ONE entry — the fuller archive draw, not the partial
    live fragment (whose champion/aliveCount disagree). Reproduces the real Bad Homburg split."""
    from tennis_model.sim import tournaments as T
    end = pd.Timestamp("2026-06-27")
    rows = []
    # Archive feed: full 'Bad Homburg', 16-player completed draw, champion P0.
    for i in range(8):
        rows.append(dict(tourney_name="Bad Homburg", date=end - pd.Timedelta(days=6),
                         round="R32", winner_name=f"P{i}", loser_name=f"P{8 + i}",
                         surface_b="Grass", best_of=3, tourney_level="500"))
    rows.append(dict(tourney_name="Bad Homburg", date=end, round="F",
                     winner_name="P0", loser_name="P1", surface_b="Grass",
                     best_of=3, tourney_level="500"))
    # Live/ESPN feed: SAME event, sponsor title, 8-player fragment, SWAPPED champion (P2).
    spon = "Bad Homburg Open powered by Solarwatt"
    for a, b in [("P0", "P4"), ("P1", "P5"), ("P2", "P6"), ("P3", "P7")]:
        rows.append(dict(tourney_name=spon, date=end - pd.Timedelta(days=1), round="QF",
                         winner_name=a, loser_name=b, surface_b="Grass", best_of=3,
                         tourney_level=float("nan")))
    rows.append(dict(tourney_name=spon, date=end, round="F", winner_name="P2",
                     loser_name="P0", surface_b="Grass", best_of=3, tourney_level=float("nan")))
    df = pd.DataFrame(rows)

    saved = (T._load_fields, T._load_upcoming, T._load_wiki_draws)
    T._load_fields = lambda tour: {}
    T._load_upcoming = lambda tour: {}
    T._load_wiki_draws = lambda tour: {}
    try:
        out = build_tournaments(_PRED, df, "wta", n_sims=200, seed=1)
    finally:
        T._load_fields, T._load_upcoming, T._load_wiki_draws = saved

    homburg = [t for t in out if t["name"] == "Bad Homburg"]
    assert len(homburg) == 1, [t["name"] for t in out]       # not the duplicate pair
    assert homburg[0]["drawSize"] == 16 and homburg[0]["champion"] == "P0"   # archive, not fragment
    print("ok test_build_tournaments_collapses_archive_and_sponsor_feed")


if __name__ == "__main__":
    test_status_real_partial_seeded_final_from_espn()
    test_completed_projection_excludes_qualifying_field()
    test_oversized_projection_error_names_event_and_source_state()
    test_wiki_draw_makes_a_seeded_board_real()
    test_prestart_upcoming_projection_from_wiki()
    test_dedup_by_display_name_keeps_fuller_draw()
    test_build_tournaments_collapses_archive_and_sponsor_feed()
    print("\nALL PASSED")
