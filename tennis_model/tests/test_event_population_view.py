"""The model population and tournament-lifecycle evidence are deliberately distinct."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.sim.tournaments import project_tournament

from tennis_model.data import results


class _Predictor:
    class _Elo:
        def __init__(self, players):
            self.overall = {name: 2000.0 - i * 20 for i, name in enumerate(players)}

        def blended(self, name, _surface):
            return self.overall.get(name, 1500.0)

        def elo(self, name):
            return self.overall.get(name, 1500.0)

    def __init__(self, players):
        self.elo = self._Elo(players)

    def win_prob_matrix(self, players, *_args, **_kwargs):
        n = len(players)
        matrix = np.full((n, n), 0.5)
        for i in range(n):
            for j in range(n):
                if i != j:
                    delta = self.elo.elo(players[i]) - self.elo.elo(players[j])
                    matrix[i, j] = 1.0 / (1.0 + 10.0 ** (-delta / 400.0))
        return matrix


def _match(day, rnd, winner, loser, *, level="WTA125", event_id="125-2026"):
    row = {column: None for column in results.CANON}
    row.update({
        "espn_id": event_id,
        "tourney_name": "Completed 125",
        "tourney_level": level,
        "tourney_date": day,
        "date": pd.Timestamp(day),
        "round": rnd,
        "best_of": 3,
        "score": "6-3 6-4",
        "winner_name": winner,
        "loser_name": loser,
        "surface": "Clay",
        "draw_level": "chall" if level == "WTA125" else "main",
    })
    return row


def test_policy_excluded_final_completes_board_card_without_entering_model():
    players = [f"P{i}" for i in range(8)]
    excluded = [
        _match("2026-08-01", "QF", "P0", "P7"),
        _match("2026-08-01", "QF", "P1", "P6"),
        _match("2026-08-01", "QF", "P2", "P5"),
        _match("2026-08-01", "QF", "P3", "P4"),
        _match("2026-08-02", "SF", "P0", "P3"),
        _match("2026-08-02", "SF", "P1", "P2"),
        _match("2026-08-03", "F", "P0", "P1"),
    ]
    eligible = _match(
        "2026-08-04", "R32", "Tour A", "Tour B",
        level="WTA250", event_id="250-2026",
    )
    model = results.clean(pd.DataFrame([eligible]), tour="wta")
    model["tour"] = "wta"
    model.attrs[results._POLICY_EVENT_ROWS_ATTR] = excluded

    event_view = results.event_match_view(model, "wta")

    assert len(model) == 1 and not model["tourney_level"].eq("WTA125").any()
    event = event_view[event_view["espn_id"] == "125-2026"]
    assert len(event) == 7 and event["round"].eq("F").sum() == 1

    card = project_tournament(
        _Predictor(players), "Completed 125", event, "wta",
        known=set(), top_set=None, resolve=lambda name: name,
        tournament_draw={"slots": players, "seeds": {}, "bestOf": 3},
        espn_id="125-2026", event_end="2026-08-03",
        dmax=event_view["date"].max(), n_sims=20, seed=1,
    )
    assert card["status"] == "completed"
    assert card["champion"] == "P0" and card["runnerUp"] == "P1"
    assert card["aliveCount"] == 1 and card["finalRecorded"] is True
