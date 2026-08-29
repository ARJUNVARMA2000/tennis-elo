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


def _event(*, level="WTA500", draw_level="main"):
    return {"id": 99, "name": "Test Open", "year": 2025, "level": level,
            "draw_level": draw_level, "surface": "Hard", "indoor": "O",
            "start": "2025-01-01", "end": "2025-01-07", "draw": 32}


def _match(*, draw="Q", round_id="1", match_id="RS001"):
    return {
        "DrawMatchType": "S", "DrawLevelType": draw, "MatchState": "F",
        "MatchID": match_id, "RoundID": round_id, "Winner": "2",
        "PlayerNameFirstA": "Alice", "PlayerNameLastA": "Ace",
        "PlayerNameFirstB": "Bobbi", "PlayerNameLastB": "Backhand",
        "PlayerCountryA": "USA", "PlayerCountryB": "CAN",
        "PlayerIDA": "1", "PlayerIDB": "2", "EntryTypeA": "", "EntryTypeB": "",
        "SeedA": "", "SeedB": "", "MatchTimeStamp": "2025-01-02T10:00:00Z",
        "ScoreSet1A": "6", "ScoreSet1B": "4", "ScoreSet2A": "6", "ScoreSet2B": "3",
        "ScoreSet3A": "", "ScoreSet3B": "", "ScoreSet4A": "", "ScoreSet4B": "",
        "ScoreSet5A": "", "ScoreSet5B": "", "ScoreTbSet1": "", "ScoreTbSet2": "",
    }


def _stats():
    return {
        "setnum": 0,
        "totservplayeda": 60, "ptsplayed1stserva": 36, "ptswon1stserva": 25,
        "ptstotwonserva": 40, "acesa": 3, "dblflta": 2, "servgamesplayeda": 9,
        "breakptsconva": 2, "breakptsplayeda": 4,
        "totservplayedb": 58, "ptsplayed1stservb": 34, "ptswon1stservb": 20,
        "ptstotwonservb": 31, "acesb": 1, "dblfltb": 3, "servgamesplayedb": 9,
        "breakptsconvb": 3, "breakptsplayedb": 5,
    }


def test_round_label():
    assert ws._round_label("1", 32) == "R32"
    assert ws._round_label("Q", 32) == "QF"
    assert ws._round_label("S", 32) == "SF"
    assert ws._round_label("F", 32) == "F"
    assert ws._round_label("0", 32) is None
    print("ok test_round_label")


def test_legacy_and_current_125_levels_share_lower_role():
    assert ws._normalized_level("125K") == ("WTA125", "chall")
    assert ws._normalized_level("WTA 125") == ("WTA125", "chall")
    assert ws._normalized_level("Premier Mandatory") == ("WTA1000", "main")
    assert ws._normalized_level("ITF") is None


def test_fetch_scope_keeps_main_events_for_qualifying_and_deduplicates():
    items = [
        {"level": "WTA 500", "tournamentGroup": {"id": 1, "name": "Tour"},
         "year": 2025, "surface": "Hard", "inOutdoor": "O", "startDate": "2025-01-01",
         "endDate": "2025-01-07", "singlesDrawSize": 32},
        {"level": "WTA 500", "tournamentGroup": {"id": 1, "name": "Tour duplicate"},
         "year": 2025, "surface": "Hard", "inOutdoor": "O", "startDate": "2025-01-01",
         "endDate": "2025-01-07", "singlesDrawSize": 32},
        {"level": "125K", "tournamentGroup": {"id": 2, "name": "Lower"},
         "year": 2025, "surface": "Clay", "inOutdoor": "O", "startDate": "2025-02-01",
         "endDate": "2025-02-07", "singlesDrawSize": 32},
    ]
    orig = ws._paged
    try:
        ws._paged = lambda *args, **kwargs: items
        assert [e["id"] for e in ws.fetch_tournaments(2025, scope="main")] == [1]
        lower_scope = ws.fetch_tournaments(2025, scope="lower")
    finally:
        ws._paged = orig
    assert {e["id"] for e in lower_scope} == {1, 2}  # tour event retained for its Q draw
    assert {e["id"]: e["draw_level"] for e in lower_scope} == {1: "main", 2: "chall"}


def test_qualifying_row_is_explicit_state_only_schema():
    row = ws._stats_row(_event(), _match(), _stats(), "qual")
    assert row is not None
    assert row["draw_level"] == "qual" and row["tourney_level"] == "Q"
    assert row["round"] == "Q1" and row["source_match_id"] == "RS001"
    assert row["w_svpt"] == 60 and row["l_svpt"] == 58


def test_resume_key_skips_existing_match_before_stats_request():
    ev, match = _event(), _match()
    key = ws._match_key(ev, match, "qual")
    orig = (ws._paged, ws._get)
    try:
        ws._paged = lambda *args, **kwargs: [match]
        ws._get = lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("stats endpoint called despite known row"))
        assert ws.scrape_tournament(ev, scope="lower", known_keys={key}) == []
    finally:
        ws._paged, ws._get = orig


def test_download_reclassifies_known_source_id_without_refetching_stats():
    """A catalogue role correction moves cached stats both ways and is idempotent."""
    orig = (ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir,
            ws.fetch_tournaments, ws._paged, ws._get)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for name in ("stats", "lower", "fresh", "historical"):
                (base / name).mkdir()
            ws.stats_dir = lambda tour: base / "stats"
            ws.lower_dir = lambda tour: base / "lower"
            ws.fresh_dir = lambda tour: base / "fresh"
            ws.historical_dir = lambda tour: base / "historical"

            ev = _event()
            # LS ids can legitimately appear in either store; RS ids are a
            # qualifying-only provider family and have a separate ingestion guard.
            row = ws._stats_row(
                ev, _match(draw="M", match_id="LS001"), _stats(), "main"
            )
            assert row is not None
            pd.DataFrame([row]).to_csv(base / "stats" / "2025.csv", index=False)

            catalogue = [_match(draw="Q", round_id="", match_id="LS001")]
            ws.fetch_tournaments = lambda year, **kwargs: [ev]
            ws._paged = lambda *args, **kwargs: catalogue
            ws._get = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("role correction refetched immutable match stats"))

            # main scope still observes the now-qualifying catalogue row, moves its
            # cached stats to lower, and does not call the per-match stats endpoint.
            ws.download_wta_stats([2025], scope="main")
            main = pd.read_csv(base / "stats" / "2025.csv")
            lower = pd.read_csv(base / "lower" / "2025_wta_lower.csv")
            assert main.empty and len(lower) == 1
            assert lower.iloc[0]["draw_level"] == "qual"
            assert lower.iloc[0]["tourney_level"] == "Q"
            assert pd.isna(lower.iloc[0]["round"])
            assert lower.iloc[0]["w_svpt"] == 60

            # The reverse source correction reuses that same lower-file row.
            catalogue[:] = [_match(draw="M", match_id="LS001")]
            ws.download_wta_stats([2025], scope="main")
            main = pd.read_csv(base / "stats" / "2025.csv")
            lower = pd.read_csv(base / "lower" / "2025_wta_lower.csv")
            assert len(main) == 1 and lower.empty
            assert main.iloc[0]["draw_level"] == "main"
            assert main.iloc[0]["tourney_level"] == "WTA500"
            assert main.iloc[0]["round"] == "R32"
            assert main.iloc[0]["w_svpt"] == 60

            # Already-correct storage is a true no-op on a repeated catalogue walk.
            before = (base / "stats" / "2025.csv").read_bytes()
            ws.download_wta_stats([2025], scope="main")
            after = (base / "stats" / "2025.csv").read_bytes()
            assert after == before
    finally:
        (ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir,
         ws.fetch_tournaments, ws._paged, ws._get) = orig


def test_role_reclassification_interruption_preserves_stats_in_bridge_copy():
    """Every move is present in source and destination before final deletion. A failure
    on the first final replace may leave a duplicate, but never lose the only stats row."""
    orig = (ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir, ws.os.replace)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for name in ("stats", "lower", "fresh", "historical"):
                (base / name).mkdir()
            ws.stats_dir = lambda tour: base / "stats"
            ws.lower_dir = lambda tour: base / "lower"
            ws.fresh_dir = lambda tour: base / "fresh"
            ws.historical_dir = lambda tour: base / "historical"

            ev = _event()
            row = ws._stats_row(ev, _match(draw="M"), _stats(), "main")
            assert row is not None
            pd.DataFrame([row]).to_csv(base / "stats" / "2025.csv", index=False)
            key = ws._row_key(pd.Series(row))

            real_replace = ws.os.replace
            calls = 0

            def interrupted(source, destination):
                nonlocal calls
                calls += 1
                if calls == 3:  # both duplicate-preserving bridge files are installed
                    raise OSError("injected final-phase interruption")
                return real_replace(source, destination)

            ws.os.replace = interrupted
            try:
                ws._reclassify_existing(2025, {key: ("qual", "Q", None)})
                raise AssertionError("expected injected interruption")
            except OSError as exc:
                assert "injected" in str(exc)
            finally:
                ws.os.replace = real_replace

            main = pd.read_csv(base / "stats" / "2025.csv")
            lower = pd.read_csv(base / "lower" / "2025_wta_lower.csv")
            assert len(main) == len(lower) == 1
            assert main.iloc[0]["w_svpt"] == lower.iloc[0]["w_svpt"] == 60
            assert set((main.iloc[0]["draw_level"], lower.iloc[0]["draw_level"])) == {"qual"}

            # The next catalogue observation heals the recoverable duplicate exactly.
            assert ws._reclassify_existing(2025, {key: ("qual", "Q", None)}) == 1
            assert pd.read_csv(base / "stats" / "2025.csv").empty
            healed = pd.read_csv(base / "lower" / "2025_wta_lower.csv")
            assert len(healed) == 1 and healed.iloc[0]["w_svpt"] == 60
    finally:
        (ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir,
         ws.os.replace) = orig


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
            # refreshed scrape of the same W2 pair replaces its row; W1 is kept
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


def test_write_year_routes_lower_rows_and_never_shrinks_old_event():
    orig = (ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for name in ("stats", "lower", "fresh", "historical"):
                (base / name).mkdir()
            ws.stats_dir = lambda tour: base / "stats"
            ws.lower_dir = lambda tour: base / "lower"
            ws.fresh_dir = lambda tour: base / "fresh"
            ws.historical_dir = lambda tour: base / "historical"
            old = pd.DataFrame({
                "tourney_id": ["2025-W99"], "winner_name": ["Keep Me"],
                "loser_name": ["Old Row"], "round": ["Q1"], "score": ["6-4 6-4"],
                "draw_level": ["qual"], "tourney_level": ["Q"],
            })
            old.to_csv(base / "lower" / "2025_wta_lower.csv", index=False)
            new = pd.DataFrame({
                "tourney_id": ["2025-W99"], "winner_name": ["New Row"],
                "loser_name": ["Another"], "round": ["Q2"], "score": ["6-3 6-3"],
                "draw_level": ["qual"], "tourney_level": ["Q"],
            })
            assert ws.write_year(2025, new, lower=True) == 2
            out = pd.read_csv(base / "lower" / "2025_wta_lower.csv")
    finally:
        ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir = orig
    assert set(out["winner_name"]) == {"Keep Me", "New Row"}
    assert not (base / "stats" / "2025.csv").exists()


def test_backfill_rejects_multiple_years():
    try:
        ws._one_year([2024, 2025])
        raise AssertionError("expected singular-year guard")
    except ValueError as exc:
        assert "exactly one year" in str(exc)


def test_scrape_year_tolerates_minority_dead_endpoints():
    """Old seasons carry a few permanently-404 event endpoints; a minority must be
    skipped loudly (additive merge), while a majority still raises (real outage)."""
    def events(n):
        return [{"id": i, "name": f"E{i}", "year": 2016, "level": "WTA500",
                 "surface": "Hard", "indoor": "O", "start": "2016-01-01",
                 "end": "2016-01-08", "draw": 32} for i in range(n)]

    orig = (ws.fetch_tournaments, ws.scrape_tournament)
    try:
        ws.fetch_tournaments = lambda year, **kwargs: events(10)
        # 2 dead endpoints out of 10 -> tolerated (max(2, 10//5) = 2 threshold... 2 is not > 2)
        def two_dead(ev, **kwargs):
            if ev["id"] < 2:
                raise RuntimeError("dead endpoint")
            return [{"tourney_id": f"2016-W{ev['id']}", "winner_name": "A",
                     "loser_name": "B", "score": "6-1 6-1"}]
        ws.scrape_tournament = two_dead
        df = ws.scrape_year(2016)
        assert len(df) == 8, len(df)
        assert df.attrs["hard_failed_events"] == ("E0", "E1")

        # 5 dead out of 10 -> majority-ish: must raise, not silently produce a husk
        def five_dead(ev, **kwargs):
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


def test_complete_bootstrap_persists_partial_rows_but_refuses_completion():
    """A minority endpoint failure must not discard acquired rows or permit the
    caller to write its one-time completion marker."""
    orig = (ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir, ws.scrape_year)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            for name in ("stats", "lower", "fresh", "historical"):
                (base / name).mkdir()
            ws.stats_dir = lambda tour: base / "stats"
            ws.lower_dir = lambda tour: base / "lower"
            ws.fresh_dir = lambda tour: base / "fresh"
            ws.historical_dir = lambda tour: base / "historical"

            row = ws._stats_row(_event(), _match(), _stats(), "qual")
            assert row is not None
            partial = pd.DataFrame([row])
            partial.attrs["hard_failed_events"] = ("Interrupted Open",)
            ws.scrape_year = lambda *args, **kwargs: partial

            try:
                ws.download_wta_stats([2026], scope="all", require_complete=True)
                raise AssertionError("expected an incomplete-bootstrap failure")
            except RuntimeError as exc:
                assert "bootstrap incomplete" in str(exc)

            saved = pd.read_csv(base / "lower" / "2026_wta_lower.csv")
            assert len(saved) == 1
            assert saved.iloc[0]["winner_name"] == "Alice Ace"
    finally:
        (ws.stats_dir, ws.lower_dir, ws.fresh_dir, ws.historical_dir,
         ws.scrape_year) = orig


def test_scrape_year_aborts_immediately_on_transport_failure():
    """A throttle/outage is season-wide: do not misclassify it as a dead event and
    march on to manufacture a partial successful year."""
    events = [_event(), {**_event(), "id": 100, "name": "Never Reached"}]
    calls = []
    orig = (ws.fetch_tournaments, ws.scrape_tournament)
    try:
        ws.fetch_tournaments = lambda year, **kwargs: events

        def throttled(ev, **kwargs):
            calls.append(ev["id"])
            raise ws.WtaTransportError("429 wall")

        ws.scrape_tournament = throttled
        try:
            ws.scrape_year(2025, scope="lower")
            raise AssertionError("expected transport failure")
        except ws.WtaTransportError:
            pass
    finally:
        ws.fetch_tournaments, ws.scrape_tournament = orig
    assert calls == [99]


def test_scrape_year_does_not_call_deterministic_404s_an_outage():
    """Even a patchy historical season may have many cached 404 catalogue rows;
    unlike malformed/pagination failures, they must not trip the outage threshold."""
    events = [{**_event(), "id": i, "name": f"Missing {i}"} for i in range(10)]
    orig = (ws.fetch_tournaments, ws.scrape_tournament)
    try:
        ws.fetch_tournaments = lambda year, **kwargs: events
        ws.scrape_tournament = lambda ev, **kwargs: (_ for _ in ()).throw(
            ws.WtaMissingRecordError("cached 404"))
        out = ws.scrape_year(2019, scope="lower")
    finally:
        ws.fetch_tournaments, ws.scrape_tournament = orig
    assert out.empty


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
    test_complete_bootstrap_persists_partial_rows_but_refuses_completion()
    test_enrich_inherits_from_historical_archive()
    print("\nALL PASSED")
