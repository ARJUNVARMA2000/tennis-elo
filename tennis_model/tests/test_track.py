"""Unit checks for eval/track — fully synthetic (no model, no network).

Runnable directly (`python tests/test_track.py`) or under pytest. Covers match
grading + metrics, calibration shape, dedup/idempotency, and tournament champion
grading. The forecast log and the output dir are redirected to a temp area.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.eval.track as track


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
class _FakeElo:
    def __init__(self, names):
        self.overall = {n: 1500.0 for n in names}


class _FakePredictor:
    """Constant-probability stand-in so logging needs no trained model."""
    def __init__(self, names, p=0.6):
        self.elo = _FakeElo(names)
        self._p = p

    def win_prob(self, a, b, surface=None, best_of=None):
        return self._p


def _results_df(rows):
    """rows: list of (winner, loser, date, surface)."""
    return pd.DataFrame([
        {"winner_name": w, "loser_name": l, "date": pd.Timestamp(d),
         "surface_b": s, "completed": True}
        for (w, l, d, s) in rows
    ])


def _setup(tmp):
    track.FORECAST_DIR = tmp / "forecast_log"
    track.FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    out = tmp / "output"
    out.mkdir(parents=True, exist_ok=True)
    track.output_dir = lambda tour: out          # redirect reads/writes
    return out


def _write_log(records):
    path = track.FORECAST_DIR / "atp.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _match(a, b, p, as_of="2026-06-01", surface="Hard", event="TestOpen", rnd="QF"):
    return {"type": "match", "as_of": as_of, "tour": "atp", "event": event,
            "round": rnd, "surface": surface, "best_of": 3, "season": 2026,
            "playerA": a, "playerB": b, "p": p, "model_version": "test"}


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def test_match_grading_and_brier():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([
            _match("Alice", "Bob", 0.70),     # Alice wins  -> p_winner 0.70, hit True
            _match("Cara", "Dana", 0.40),     # Cara wins   -> p_winner 0.40, hit False
            _match("Evan", "Finn", 0.55),     # Finn wins   -> p_winner 0.45, hit False
        ])
        df = _results_df([
            ("Alice", "Bob", "2026-06-03", "Hard"),
            ("Cara", "Dana", "2026-06-05", "Hard"),
            ("Finn", "Evan", "2026-06-04", "Hard"),
        ])
        out = track.grade("atp", df)
        mf = out["matchForecasts"]
        assert mf["graded"] == 3 and mf["pending"] == 0, mf
        expected_brier = np.mean([(1 - 0.70) ** 2, (1 - 0.40) ** 2, (1 - 0.45) ** 2])
        assert abs(mf["overall"]["brier"] - expected_brier) < 1e-9, (mf["overall"], expected_brier)
        # accuracy: only Alice's call was correct (0.70 > 0.5 and she won)
        assert abs(mf["overall"]["acc"] - 1 / 3) < 1e-9, mf["overall"]
        hits = {(g["playerA"], g["hit"]) for g in mf["recent"]}
        assert ("Alice", True) in hits and ("Cara", False) in hits, hits
        print("ok test_match_grading_and_brier")


def test_pending_outside_window():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([_match("Alice", "Bob", 0.7, as_of="2026-06-01")])
        # result 60 days later -> outside the 21-day join window -> stays pending
        df = _results_df([("Alice", "Bob", "2026-08-01", "Hard")])
        out = track.grade("atp", df)
        assert out["matchForecasts"]["graded"] == 0, out["matchForecasts"]
        print("ok test_pending_outside_window")


def test_calibration_shape():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([_match(f"A{i}", f"B{i}", 0.5 + 0.04 * i) for i in range(8)])
        df = _results_df([(f"A{i}", f"B{i}", "2026-06-02", "Hard") for i in range(8)])
        out = track.grade("atp", df)
        cal = out["matchForecasts"]["calibration"]
        assert cal and all({"bin", "n", "pred", "actual"} <= set(c) for c in cal), cal
        print("ok test_calibration_shape")


def test_dedup_idempotent():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        (out / "tournaments.json").write_text("[]", encoding="utf-8")
        pred = _FakePredictor(["Alice", "Bob"])
        up = pd.DataFrame([{"tourney_name": "TestOpen", "tourney_date": "2026-06-01",
                            "round": "QF", "playerA": "Alice", "playerB": "Bob"}])
        df = _results_df([("Zeta", "Yan", "2026-06-01", "Hard")])  # unrelated
        n1 = track.log_forecasts("atp", pred, df, up, "2026-06-01")
        n2 = track.log_forecasts("atp", pred, df, up, "2026-06-02")  # same matchup, next day
        lines = track._read_log(track.FORECAST_DIR / "atp.jsonl")
        assert n1 == 1 and n2 == 0 and len(lines) == 1, (n1, n2, len(lines))
        print("ok test_dedup_idempotent")


def test_tournament_grading():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        # two daily snapshots of an in-progress event; champion turns out to be Bob
        snap = lambda as_of, bob_p: {
            "type": "tournament", "as_of": as_of, "tour": "atp", "event": "TestCup",
            "season": 2026, "projection": [
                {"name": "Alice", "champion": 0.50}, {"name": "Bob", "champion": bob_p}],
            "modelFavorite": "Alice", "model_version": "test"}
        _write_log([snap("2026-06-01", 0.30), snap("2026-06-03", 0.45)])
        (out / "tournaments.json").write_text(json.dumps([
            {"name": "TestCup", "status": "completed", "champion": "Bob",
             "end": "2026-06-04"}]), encoding="utf-8")
        res = track.grade("atp", _results_df([]))["tournamentOdds"]
        assert res["events"] == 1, res
        # champion Brier = mean((1-0.30)^2, (1-0.45)^2), reported rounded to 4dp
        exp = np.mean([(1 - 0.30) ** 2, (1 - 0.45) ** 2])
        assert abs(res["championBrier"] - exp) < 1e-4, (res, exp)
        # favourite was Alice, champion Bob -> not picked
        assert res["recent"][0]["favoritePicked"] is False, res["recent"][0]
        print("ok test_tournament_grading")


if __name__ == "__main__":
    test_match_grading_and_brier()
    test_pending_outside_window()
    test_calibration_shape()
    test_dedup_idempotent()
    test_tournament_grading()
    print("\nALL PASSED")
