"""Unit checks for the WTA stats scraper's pure/parse layers — no network.

Runnable directly (`python tests/test_wta_stats.py`) or under pytest. All HTTP goes
through wta_stats._get, which is swapped for canned responses (save/restore pattern).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.wta_stats as ws


def test_round_label():
    assert ws._round_label("1", 32) == "R32"
    assert ws._round_label("Q", 32) == "QF"
    assert ws._round_label("S", 32) == "SF"
    assert ws._round_label("F", 32) == "F"
    assert ws._round_label("0", 32) is None
    print("ok test_round_label")


def test_paged_stops_on_paging_blind_endpoint():
    """An endpoint that ignores page params returns the identical page forever —
    the repeated first-item signature must end the walk after one page."""
    orig = ws._get
    try:
        ws._get = lambda path, params=None, **kw: {"matches": [{"id": 1}] * 100}
        out = ws._paged("x", "matches")
    finally:
        ws._get = orig
    assert len(out) == 100
    print("ok test_paged_stops_on_paging_blind_endpoint")


def test_paged_short_page_ends_walk():
    pages = [{"matches": [{"id": i} for i in range(100)]},
             {"matches": [{"id": 200}]}]
    orig = ws._get
    try:
        ws._get = lambda path, params=None, **kw: pages[min(params["page"], 1)]
        out = ws._paged("x", "matches")
    finally:
        ws._get = orig
    assert len(out) == 101
    print("ok test_paged_short_page_ends_walk")


def test_paged_runaway_cap_raises():
    """Ever-changing full pages (unstable ordering on a paging-blind endpoint) must
    hit the hard page cap and raise instead of looping until the CI timeout."""
    calls = {"n": 0}

    def fake(path, params=None, **kw):
        calls["n"] += 1
        return {"matches": [{"id": calls["n"] * 1000 + i} for i in range(100)]}

    orig = ws._get
    try:
        ws._get = fake
        try:
            ws._paged("x", "matches")
            raised = False
        except RuntimeError as e:
            raised = "runaway" in str(e)
    finally:
        ws._get = orig
    assert raised and calls["n"] == 50, calls
    print("ok test_paged_runaway_cap_raises")


def test_write_year_merges_and_is_atomic():
    orig = (ws.stats_dir, ws.fresh_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "stats").mkdir()
            (base / "fresh").mkdir()
            ws.stats_dir = lambda tour: base / "stats"
            ws.fresh_dir = lambda tour: base / "fresh"

            old = pd.DataFrame({"tourney_id": ["2026-W1", "2026-W2"],
                                "winner_name": ["A", "B"], "loser_name": ["X", "Y"],
                                "score": ["6-1 6-1", "6-2 6-2"]})
            old.to_csv(base / "stats" / "2026.csv", index=False)
            # refreshed scrape of W2 replaces its rows; W1 is kept
            new = pd.DataFrame({"tourney_id": ["2026-W2"], "winner_name": ["B"],
                                "loser_name": ["Y"], "score": ["6-3 6-3"]})
            n = ws.write_year(2026, new)
            merged = pd.read_csv(base / "stats" / "2026.csv")
            leftovers = list((base / "stats").glob("*.tmp"))
            # empty incremental scrape: no-op that reports the existing count
            n_empty = ws.write_year(2026, pd.DataFrame())
    finally:
        ws.stats_dir, ws.fresh_dir = orig
    assert n == 2 and n_empty == 2
    assert set(merged["score"]) == {"6-1 6-1", "6-3 6-3"}, merged
    assert leftovers == []                       # atomic write left no temp file behind
    print("ok test_write_year_merges_and_is_atomic")


if __name__ == "__main__":
    test_round_label()
    test_paged_stops_on_paging_blind_endpoint()
    test_paged_short_page_ends_walk()
    test_paged_runaway_cap_raises()
    test_write_year_merges_and_is_atomic()
    print("\nALL PASSED")
