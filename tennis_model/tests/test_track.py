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

    def win_prob(self, a, b, surface=None, best_of=None, event=None):
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


def _match(a, b, p, as_of="2026-06-01", surface="Hard", event="TestOpen", rnd="QF",
           version="test"):
    return {"type": "match", "as_of": as_of, "tour": "atp", "event": event,
            "round": rnd, "surface": surface, "best_of": 3, "season": 2026,
            "playerA": a, "playerB": b, "p": p, "model_version": version}


def _graded(p, won, date="2026-06-15", version="0.1.0"):
    """A _grade_matches-shaped record, as _drift_block consumes them."""
    return {"model_version": version, "date": date, "p_a": p, "a_won": won,
            "p_winner": p if won else 1.0 - p}


def _graded_batch(n, p, wins, **kw):
    return [_graded(p, i < wins, **kw) for i in range(n)]


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


def test_drift_calibrated_is_ok():
    # 200 forecasts at p=0.7, exactly 140 hit: realized logloss == forecast entropy
    # by construction, so d == 0 -> "ok" with |t| ~ 0.
    dr = track._drift_block(_graded_batch(200, 0.7, 140), None, current_version="0.1.0")
    assert dr["status"] == "ok", dr
    assert dr["n"] == 200 and abs(dr["d"]) < 1e-9, dr
    assert abs(dr["t"]) < 1.0, dr
    assert abs(dr["logloss"] - dr["expectedLogloss"]) < 1e-9, dr
    assert dr["baseline"] is None, dr
    print("ok test_drift_calibrated_is_ok")


def test_drift_overconfident_flags():
    # says 75%, hits 55% -> d ~ +0.22 nats, t ~ 5.7: the re-tune signal must fire,
    # and the sign convention is positive-when-overconfident.
    dr = track._drift_block(_graded_batch(200, 0.75, 110), None, current_version="0.1.0")
    assert dr["status"] == "drift", dr
    assert dr["d"] > 0.2 and dr["t"] >= 5, dr
    # symmetric luck (underconfident window) must NEVER fire — one-sided by design
    lucky = track._drift_block(_graded_batch(200, 0.75, 180), None, current_version="0.1.0")
    assert lucky["status"] == "ok" and lucky["d"] < 0, lucky
    print("ok test_drift_overconfident_flags")


def test_drift_below_min_n_insufficient():
    dr = track._drift_block(_graded_batch(30, 0.9, 3), None, current_version="0.1.0")
    assert dr["status"] == "insufficient" and dr["n"] == 30, dr
    assert dr["d"] is None and dr["se"] is None and dr["t"] is None, dr
    assert dr["logloss"] is None and dr["worstBin"] is None, dr
    assert track._drift_block([], None, current_version="0.1.0")["status"] == "insufficient"
    print("ok test_drift_below_min_n_insufficient")


def test_drift_window_and_version_filter():
    recs = (_graded_batch(160, 0.7, 112, date="2026-06-15")            # in window
            + _graded_batch(100, 0.6, 20, date="2026-02-15")           # 120d stale -> out
            + _graded_batch(100, 0.6, 20, date="2026-06-15", version="0.0.9"))  # old model
    dr = track._drift_block(recs, None, current_version="0.1.0")
    assert dr["n"] == 160, dr                       # both stale + old-version excluded
    assert dr["status"] == "ok", dr                 # the excluded overconfident junk can't latch it
    assert dr["modelVersion"] == "0.1.0", dr
    print("ok test_drift_window_and_version_filter")


def test_drift_grade_end_to_end_json_safe():
    def _no_nan(tok):
        raise ValueError(f"non-finite {tok} in shipped track.json")

    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        # empty log + no accuracy.json: insufficient, baseline null, file NaN-free
        _write_log([])
        track.grade("atp", _results_df([]))
        shipped = json.loads((out / "track.json").read_text(encoding="utf-8"),
                             parse_constant=_no_nan)
        dr = shipped["matchForecasts"]["drift"]
        assert dr["status"] == "insufficient" and dr["baseline"] is None, dr

        # 200 graded current-version forecasts at p=0.7 (140 hit) + a synthetic baseline
        (out / "accuracy.json").write_text(json.dumps({
            "window": "2016-2026",
            "models": {"combiner": {"n": 28648, "acc": 0.68,
                                    "logloss": 0.5826, "brier": 0.2001}},
        }), encoding="utf-8")
        _write_log([_match(f"A{i}", f"B{i}", 0.7, version=track.__version__)
                    for i in range(200)])
        df = _results_df([(f"A{i}", f"B{i}", "2026-06-02", "Hard") if i < 140
                          else (f"B{i}", f"A{i}", "2026-06-02", "Hard")
                          for i in range(200)])
        track.grade("atp", df)
        shipped = json.loads((out / "track.json").read_text(encoding="utf-8"),
                             parse_constant=_no_nan)
        dr = shipped["matchForecasts"]["drift"]
        assert dr["status"] == "ok" and dr["n"] == 200, dr
        assert dr["baseline"]["logloss"] == 0.5826, dr
        # dLogloss = live (== entropy(0.7) = 0.6109) - backtest baseline, +ve = live worse
        assert abs(dr["baseline"]["dLogloss"] - (0.6109 - 0.5826)) < 1e-3, dr
        assert dr["baseline"]["window"] == "2016-2026", dr
        print("ok test_drift_grade_end_to_end_json_safe")


if __name__ == "__main__":
    test_match_grading_and_brier()
    test_pending_outside_window()
    test_calibration_shape()
    test_dedup_idempotent()
    test_tournament_grading()
    test_drift_calibrated_is_ok()
    test_drift_overconfident_flags()
    test_drift_below_min_n_insufficient()
    test_drift_window_and_version_filter()
    test_drift_grade_end_to_end_json_safe()
    print("\nALL PASSED")
