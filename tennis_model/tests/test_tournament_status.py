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

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.sim.tournaments import project_tournament, project_upcoming

_R = {f"P{i}": 2000.0 - 30.0 * i for i in range(16)}   # P0 strongest .. P15 weakest


class _Pred:
    class _Elo:
        def __init__(self, r):
            self.r = r

        def blended(self, name, surf):
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


if __name__ == "__main__":
    test_status_real_partial_seeded_final_from_espn()
    test_wiki_draw_makes_a_seeded_board_real()
    test_prestart_upcoming_projection_from_wiki()
    print("\nALL PASSED")
