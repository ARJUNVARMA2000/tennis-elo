"""Unit checks for the A5 lower-tier (challenger + qualifying) ingestion gate.

Runnable directly (`python tests/test_lower_ingestion.py`) or under pytest. Covers:
the INCLUDE_CHALLENGERS load-time gate (off = bit-identical frame), draw_level
marking, the qualifying 'Q' tier stamp (challenger-strength K, never slam K),
Q-round chronological ordering before the main draw, and the downloader's
basename handling for the atp_quali/ subdir files.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.config as config
import tennis_model.data.download as download
import tennis_model.data.results as results

_HDR_FULL = "tourney_id,tourney_name,tourney_date,winner_name,loser_name,round,tourney_level,score,w_svpt,l_svpt\n"


def _write_csv(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _with_dirs(fn):
    """Run fn(base_path) with every source dir redirected into a temp area and the
    lower files pre-written (same redirection pattern as test_names_merge)."""
    orig = (results.historical_dir, results.stats_dir, results.fresh_dir,
            results.live_dir, results.lower_dir)
    orig_flag = config.INCLUDE_CHALLENGERS
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            dirs = {n: base / n for n in ("historical", "stats", "fresh", "live", "lower")}
            for p in dirs.values():
                p.mkdir(parents=True, exist_ok=True)
            results.historical_dir = lambda tour: dirs["historical"]
            results.stats_dir = lambda tour: dirs["stats"]
            results.fresh_dir = lambda tour: dirs["fresh"]
            results.live_dir = lambda tour: dirs["live"]
            results.lower_dir = lambda tour: dirs["lower"]

            # main-draw archive row
            _write_csv(dirs["historical"] / "2015.csv",
                _HDR_FULL
                + "2015-339,Brisbane,20150104,Roger Federer,Milos Raonic,F,250,6-4 6-4,60,55\n")
            # challenger main draw + the same match again in the ongoing file (dup)
            _write_csv(dirs["lower"] / "2015_challenger.csv",
                _HDR_FULL
                + "2015-7182,Happy Valley,20150111,Blaz Rola,Omar Jasika,R32,C,4-6 6-4 6-1,102,87\n")
            _write_csv(dirs["lower"] / "challenger_ongoing_tourneys.csv",
                _HDR_FULL
                + "2015-7182,Happy Valley,20150111,Blaz Rola,Omar Jasika,R32,C,4-6 6-4 6-1,102,87\n")
            # tour-event qualifying (parent level 250 upstream -> must become 'Q')
            _write_csv(dirs["lower"] / "2015_atp_quali.csv",
                _HDR_FULL
                + "2015-339,Brisbane,20150104,Tobias Kamke,Blake Mott,Q1,250,4-6 7-5 6-2,93,94\n")
            return fn(base)
    finally:
        (results.historical_dir, results.stats_dir, results.fresh_dir,
         results.live_dir, results.lower_dir) = orig
        config.INCLUDE_CHALLENGERS = orig_flag


def test_gate_off_excludes_lower_rows():
    def check(_base):
        config.INCLUDE_CHALLENGERS = False
        df = results.merge_sources("atp")
        assert len(df) == 1, df[["winner_name", "loser_name"]]
        assert set(df["draw_level"]) == {"main"}
        return df

    _with_dirs(check)
    print("ok test_gate_off_excludes_lower_rows")


def test_gate_on_marks_and_tiers_lower_rows():
    def check(_base):
        config.INCLUDE_CHALLENGERS = True
        df = results.clean(results.merge_sources("atp"), tour=None)
        # 1 main + 1 challenger (ongoing dup collapsed) + 1 quali
        assert len(df) == 3, df[["winner_name", "loser_name", "draw_level"]]
        assert dict(df["draw_level"].value_counts()) == {"main": 1, "chall": 1, "qual": 1}

        chall = df[df["draw_level"] == "chall"].iloc[0]
        assert chall["tourney_level"] == "C" and chall["tier"] == "challenger"

        # quali row: parent 250 level replaced by 'Q' -> challenger tier, NOT atp250
        qual = df[df["draw_level"] == "qual"].iloc[0]
        assert qual["tourney_level"] == "Q" and qual["tier"] == "challenger"
        # serve stats flow through (the point model consumes lower-tier rows too)
        assert bool(qual["has_stats"])

        # Q1 sorts strictly before the main-draw rounds of the same event
        assert qual["round_order"] < 0 < df[df["draw_level"] == "main"]["round_order"].iloc[0]
        srt = results.chronological(df)
        pos = {lvl: i for i, lvl in enumerate(srt["draw_level"])}
        assert pos["qual"] < pos["main"], srt[["draw_level", "round", "date"]]
        return df

    _with_dirs(check)
    print("ok test_gate_on_marks_and_tiers_lower_rows")


def test_load_matches_gate_off_has_no_draw_level_surprises():
    """With the flag off the frame still carries draw_level (all 'main') so
    downstream consumers (features carry-through, arbiter filter) never KeyError."""
    def check(_base):
        config.INCLUDE_CHALLENGERS = False
        df = results.load_matches("atp")
        assert "draw_level" in df.columns and set(df["draw_level"]) == {"main"}
        return df

    _with_dirs(check)
    print("ok test_load_matches_gate_off_has_no_draw_level_surprises")


def test_challenger_rows_from_the_stats_dir_are_not_treated_as_main_draw():
    """The 2026-07-25 production bug. `_read_lower` stamps only what it reads out of
    `lower_dir`, so a lower-tier row arriving through any other directory inherited
    "main" — and the ATP serve-stats source ships `<year>_challenger.csv` into
    `stats_dir`. Worse, the stats overlay OUTRANKS the lower overlay in the dedup
    preference, so its unlabelled copy won even when lower_dir had the same match
    stamped correctly. 42k of the 72k rows the ATP combiner scored as main draw for
    2016-26 were Challengers — the exact mix A5 measured as a REJECT."""
    def check(base: Path):
        config.INCLUDE_CHALLENGERS = True
        # same challenger match as lower_dir carries, but arriving via the stats overlay
        _write_csv(base / "stats" / "2015_challenger.csv",
            _HDR_FULL
            + "2015-7182,Happy Valley,20150111,Blaz Rola,Omar Jasika,R32,C,4-6 6-4 6-1,102,87\n")
        # ...and a challenger the stats overlay is the ONLY source for
        _write_csv(base / "stats" / "2016_challenger.csv",
            _HDR_FULL
            + "2016-7300,Ostrava,20160118,Jan Satral,Lukas Rosol,R16,C,6-3 6-2,70,64\n")
        df = results.clean(results.merge_sources("atp"))
        by_level = dict(df["draw_level"].value_counts())
        assert by_level.get("chall") == 2, df[["winner_name", "draw_level", "tourney_level"]]
        # the stats-only challenger must NOT be sitting in the combiner's eval set
        rosol = df[df["loser_name"] == "Lukas Rosol"].iloc[0]
        assert rosol["draw_level"] == "chall", dict(rosol)
        from tennis_model.model.features import main_rows
        assert "C" not in set(main_rows(df)["tourney_level"]), "Challenger leaked into main_rows"
        # and the tour-level row is untouched
        assert set(df[df["draw_level"] == "main"]["winner_name"]) == {"Roger Federer"}
    _with_dirs(check)
    print("ok test_challenger_rows_from_the_stats_dir_are_not_treated_as_main_draw")


def test_draw_level_derives_from_content_not_the_directory():
    """Guards the direction of the fix: an explicit stamp from the reader still wins, but
    an unstamped row is classified by what `tourney_level` says it is."""
    import pandas as pd
    df = pd.DataFrame({
        "tourney_level": ["C", "Q", "250", "G", None],
        "draw_level": [None, None, None, "chall", None],   # 4th: reader stamp must win
    })
    out = results._stamp_draw_level(df.copy())
    assert list(out["draw_level"]) == ["chall", "qual", "main", "chall", "main"], \
        list(out["draw_level"])
    # a frame with no tourney_level column at all degrades to main, never raises
    bare = results._stamp_draw_level(pd.DataFrame({"winner_name": ["A", "B"]}))
    assert list(bare["draw_level"]) == ["main", "main"]
    print("ok test_draw_level_derives_from_content_not_the_directory")


def test_download_lower_writes_basenames():
    """atp_quali/{year}_atp_quali.csv must land as its basename inside lower_dir."""
    payload = (_HDR_FULL
               + "2015-339,Brisbane,20150104,A Player,B Player,Q1,250,6-4 6-4,60,55\n").encode()
    orig_https, orig_dir = download._via_https, download.lower_dir
    try:
        with tempfile.TemporaryDirectory() as d:
            download._via_https = lambda url, retries=3: payload
            download.lower_dir = lambda tour: Path(d)
            done, failed = download.download_lower(full=False)
            assert not failed, failed
            names = sorted(p.name for p in Path(d).glob("*.csv"))
            assert all("/" not in n for n in names)
            assert any(n.endswith("_atp_quali.csv") for n in names), names
            assert "challenger_ongoing_tourneys.csv" in names, names
    finally:
        download._via_https, download.lower_dir = orig_https, orig_dir
    print("ok test_download_lower_writes_basenames")


if __name__ == "__main__":
    test_gate_off_excludes_lower_rows()
    test_gate_on_marks_and_tiers_lower_rows()
    test_load_matches_gate_off_has_no_draw_level_surprises()
    test_challenger_rows_from_the_stats_dir_are_not_treated_as_main_draw()
    test_draw_level_derives_from_content_not_the_directory()
    test_download_lower_writes_basenames()
    print("\nALL PASSED")
