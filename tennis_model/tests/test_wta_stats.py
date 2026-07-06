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
    orig = (ws.stats_dir, ws.fresh_dir, ws.historical_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "stats").mkdir()
            (base / "fresh").mkdir()
            (base / "historical").mkdir()
            ws.stats_dir = lambda tour: base / "stats"
            ws.fresh_dir = lambda tour: base / "fresh"
            ws.historical_dir = lambda tour: base / "historical"

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
        ws.stats_dir, ws.fresh_dir, ws.historical_dir = orig
    assert n == 2 and n_empty == 2
    assert set(merged["score"]) == {"6-1 6-1", "6-3 6-3"}, merged
    assert leftovers == []                       # atomic write left no temp file behind
    print("ok test_write_year_merges_and_is_atomic")


def test_scrape_year_tolerates_minority_dead_endpoints():
    """Old seasons carry a few permanently-404 event endpoints; a minority must be
    skipped loudly (additive merge), while a majority still raises (real outage)."""
    def events(n):
        return [{"id": i, "name": f"E{i}", "year": 2016, "level": "WTA500",
                 "surface": "Hard", "indoor": "O", "start": "2016-01-01",
                 "end": "2016-01-08", "draw": 32} for i in range(n)]

    orig = (ws.fetch_tournaments, ws.scrape_tournament)
    try:
        ws.fetch_tournaments = lambda year: events(10)
        # 2 dead endpoints out of 10 -> tolerated (max(2, 10//5) = 2 threshold... 2 is not > 2)
        def two_dead(ev):
            if ev["id"] < 2:
                raise RuntimeError("dead endpoint")
            return [{"tourney_id": f"2016-W{ev['id']}", "winner_name": "A",
                     "loser_name": "B", "score": "6-1 6-1"}]
        ws.scrape_tournament = two_dead
        df = ws.scrape_year(2016)
        assert len(df) == 8, len(df)

        # 5 dead out of 10 -> majority-ish: must raise, not silently produce a husk
        def five_dead(ev):
            if ev["id"] < 5:
                raise RuntimeError("dead endpoint")
            return [{"tourney_id": f"2016-W{ev['id']}", "winner_name": "A",
                     "loser_name": "B", "score": "6-1 6-1"}]
        ws.scrape_tournament = five_dead
        try:
            ws.scrape_year(2016)
            raise AssertionError("expected RuntimeError on majority hard-fail")
        except RuntimeError as e:
            assert "outage" in str(e)
    finally:
        ws.fetch_tournaments, ws.scrape_tournament = orig
    print("ok test_scrape_year_tolerates_minority_dead_endpoints")


def test_enrich_inherits_from_historical_archive():
    """Backfill years have no fresh overlay: rankings/age/bios must be inherited
    from the frozen historical archive's duplicate of the same match instead
    (the API returns neither rankings nor per-match age)."""
    orig = (ws.stats_dir, ws.fresh_dir, ws.historical_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for n in ("stats", "fresh", "historical"):
                (base / n).mkdir()
            ws.stats_dir = lambda tour: base / "stats"
            ws.fresh_dir = lambda tour: base / "fresh"
            ws.historical_dir = lambda tour: base / "historical"

            pd.DataFrame({
                "winner_name": ["Serena Williams"], "loser_name": ["Angelique Kerber"],
                "winner_rank": [1], "loser_rank": [10],
                "winner_rank_points": [9000], "loser_rank_points": [3000],
                "winner_age": [34.5], "loser_age": [28.0],
                "winner_hand": ["R"], "loser_hand": ["L"],
                "winner_ht": [175], "loser_ht": [173],
                "score": ["6-4 3-6 6-4"],
            }).to_csv(base / "historical" / "2016.csv", index=False)

            scraped = pd.DataFrame({
                "winner_name": ["Serena Williams"], "loser_name": ["Angelique Kerber"],
                "winner_rank": [None], "loser_rank": [None],
                "winner_rank_points": [None], "loser_rank_points": [None],
                "winner_age": [None], "loser_age": [None],
                "winner_hand": [None], "loser_hand": [None],
                "winner_ht": [None], "loser_ht": [None],
                "score": ["6-4 3-6 6-4"],
            })
            out = ws._enrich_from_local(scraped, 2016)
    finally:
        ws.stats_dir, ws.fresh_dir, ws.historical_dir = orig
    row = out.iloc[0]
    assert row["winner_rank"] == 1 and row["loser_rank"] == 10
    assert row["winner_rank_points"] == 9000
    assert row["winner_age"] == 34.5 and row["loser_hand"] == "L"
    assert row["winner_ht"] == 175
    print("ok test_enrich_inherits_from_historical_archive")


if __name__ == "__main__":
    test_round_label()
    test_paged_stops_on_paging_blind_endpoint()
    test_paged_short_page_ends_walk()
    test_paged_runaway_cap_raises()
    test_write_year_merges_and_is_atomic()
    test_scrape_year_tolerates_minority_dead_endpoints()
    test_enrich_inherits_from_historical_archive()
    print("\nALL PASSED")
