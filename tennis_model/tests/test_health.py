"""Unit checks for the data-freshness sentinel (data/health.py) — fully synthetic.

Runnable directly (`python tests/test_health.py`) or under pytest. problems() is pure
given a health dict; tour_health()/main() are exercised with load_matches redirected
(same save/restore pattern as test_track).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.health as health


def _h(result_age=1, stats_age=2, frac=0.9, n=500) -> dict:
    return {"result_age_days": result_age, "stats_age_days": stats_age,
            "cur_year_stats_fraction": frac, "cur_year_matches": n}


def test_problems_fresh_is_clean():
    assert health.problems("atp", _h(), pd.Timestamp("2026-07-01")) == []
    print("ok test_problems_fresh_is_clean")


def test_problems_stale_results_flagged():
    out = health.problems("atp", _h(result_age=10), pd.Timestamp("2026-07-01"))
    assert len(out) == 1 and "newest completed match" in out[0], out
    print("ok test_problems_stale_results_flagged")


def test_problems_offseason_relax_window():
    h = _h(result_age=20, stats_age=20)
    assert health.problems("atp", h, pd.Timestamp("2026-12-15")) == []
    # season effectively ends mid-November: late Nov must relax too (regression:
    # the relax used to start Dec 1, redding every build Nov 21-30)
    assert health.problems("atp", h, pd.Timestamp("2026-11-25")) == []
    assert health.problems("atp", h, pd.Timestamp("2026-11-10")) != []
    print("ok test_problems_offseason_relax_window")


def test_problems_missing_results_is_a_problem():
    out = health.problems("atp", _h(result_age=None), pd.Timestamp("2026-07-01"))
    assert any("no completed matches" in p for p in out), out
    print("ok test_problems_missing_results_is_a_problem")


def test_problems_coverage_gate_needs_volume():
    now = pd.Timestamp("2026-07-01")
    assert any("coverage" in p for p in health.problems("atp", _h(frac=0.3), now))
    # under 100 matches the season fraction is noise — not gated
    assert not any("coverage" in p
                   for p in health.problems("atp", _h(frac=0.3, n=50), now))
    print("ok test_problems_coverage_gate_needs_volume")


def test_tour_health_empty_frame_reports_none():
    """An empty tour must report None ages (flagged downstream), not crash on NaT."""
    orig = health.load_matches
    try:
        health.load_matches = lambda tour: pd.DataFrame(
            {"date": pd.to_datetime(pd.Series([], dtype="object")),
             "completed": pd.Series([], dtype=bool),
             "has_stats": pd.Series([], dtype=bool)})
        h = health.tour_health("atp", pd.Timestamp("2026-07-01"))
    finally:
        health.load_matches = orig
    assert h["matches"] == 0
    assert h["date_max"] is None and h["result_age_days"] is None
    assert any("no completed matches" in p
               for p in health.problems("atp", h, pd.Timestamp("2026-07-01")))
    print("ok test_tour_health_empty_frame_reports_none")


def test_main_strict_exit_code_and_report():
    stale = pd.DataFrame({"date": pd.to_datetime(["2026-01-01"]),
                          "completed": [True], "has_stats": [True]})
    orig = (health.load_matches, health.OUTPUT_DIR, health.TOURS, sys.argv)
    try:
        with tempfile.TemporaryDirectory() as d:
            health.load_matches = lambda tour: stale
            health.OUTPUT_DIR = Path(d)
            health.TOURS = ("atp",)
            sys.argv = ["health", "--strict"]
            rc_strict = health.main()
            report = json.loads((Path(d) / "health.json").read_text())
            sys.argv = ["health"]
            rc_soft = health.main()
    finally:
        health.load_matches, health.OUTPUT_DIR, health.TOURS, sys.argv = orig
    assert rc_strict == 1 and report["ok"] is False and report["tours"]["atp"]["problems"]
    assert rc_soft == 0                      # same problems, but only --strict reds the build
    print("ok test_main_strict_exit_code_and_report")


if __name__ == "__main__":
    test_problems_fresh_is_clean()
    test_problems_stale_results_flagged()
    test_problems_offseason_relax_window()
    test_problems_missing_results_is_a_problem()
    test_problems_coverage_gate_needs_volume()
    test_tour_health_empty_frame_reports_none()
    test_main_strict_exit_code_and_report()
    print("\nALL PASSED")
