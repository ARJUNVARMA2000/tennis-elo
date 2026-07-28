"""Unit checks for data/results name-keying + source merging — fully synthetic.

Runnable directly (`python tests/test_names_merge.py`) or under pytest. Covers the
accent/punctuation-insensitive name key, canonicalisation preferring the historical
spelling, and the three-source merge/dedup (historical > fresh > live), with the
source dirs redirected to a temp area (same pattern as test_track).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.results as results


# ---------------------------------------------------------------------------
# name / score keys
# ---------------------------------------------------------------------------
def test_name_key_folds_accents_and_punct():
    k = results._name_key
    # accents fold, hyphens become spaces -> same key across sources
    assert k("Félix Auger-Aliassime") == k("Felix Auger Aliassime") == "felix auger aliassime"
    # case-insensitive
    assert k("FÉLIX AUGER-ALIASSIME") == k("felix auger-aliassime")
    # apostrophes / periods / backticks fold too
    assert k("O'Connell") == k("O Connell") == k("o.connell")
    # whitespace collapses
    assert k("  Novak    Djokovic ") == "novak djokovic"
    # non-strings map to the empty key
    assert k(None) == "" and k(3.14) == ""
    print("ok test_name_key_folds_accents_and_punct")


def test_name_key_single_implementation():
    """Anti-re-drift lock: every consumer must hold THE SAME function object from
    data/names.py — a re-copied implementation fails this even if byte-identical."""
    import tennis_model.data.charting as charting
    import tennis_model.data.names as names
    assert results._name_key is names.name_key
    assert charting.name_key is names.name_key
    print("ok test_name_key_single_implementation")


def test_name_key_shared_fixture():
    """The fixture is also consumed by the web test suite against the TS port of
    name_key (web/lib/live.ts) — it is the cross-language parity tripwire."""
    import json
    fixture = Path(__file__).parent / "fixtures" / "name_key_cases.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    assert len(cases) >= 15
    for case in cases:
        assert results._name_key(case["name"]) == case["key"], case
    print("ok test_name_key_shared_fixture")


def test_score_key_ignores_tiebreak_points():
    sk = results._score_key
    assert sk("7-6(4) 6-3") == sk("7-6 6-3") == "7-6,6-3"
    # retirement formatting differs across sources: markers and 0-0 placeholder
    # sets are ignored so the same match keys identically
    assert sk("6-3 3-2 RET") == sk("6-3 3-2") == sk("6-3 3-2 0-0 RET") == "6-3,3-2"
    assert sk(None) == ""
    print("ok test_score_key_ignores_tiebreak_points")


def test_canonicalize_prefers_historical_spelling():
    # the plain (fresh/live) spelling is MORE frequent, but the historical (__src=0)
    # spelling must still win the canonical vote
    df = pd.DataFrame({
        "winner_name": ["Félix Auger-Aliassime", "Felix Auger Aliassime",
                        "Felix Auger Aliassime"],
        "loser_name": ["Casper Ruud", "Casper Ruud", "Novak Djokovic"],
        "__src": [0, 1, 2],
    })
    out = results._canonicalize_names(df.copy())
    assert set(out["winner_name"]) == {"Félix Auger-Aliassime"}, set(out["winner_name"])
    assert set(out["loser_name"]) == {"Casper Ruud", "Novak Djokovic"}
    print("ok test_canonicalize_prefers_historical_spelling")


def test_canonicalize_merges_a_dropped_surname_via_alias():
    """A variant that differs by MORE than accents/punct has a different `_name_key`, so the
    per-key vote cannot merge it. Umag 2026 shipped 'Daniel Merida' (champion) and 'Daniel
    Merida Aguilar' as two people: drawSize 29 for a 28-draw, aliveCount 2 on a finished
    event, and the champion's title odds split across both identities."""
    df = pd.DataFrame({
        "winner_name": ["Daniel Merida", "Daniel Merida Aguilar"],
        "loser_name": ["Daniel Merida Aguilar", "Vit Kopriva"],
        "__src": [0, 2],
    })
    out = results._canonicalize_names(df.copy())
    names = set(out["winner_name"]) | set(out["loser_name"])
    assert "Daniel Merida Aguilar" not in names, names
    assert "Daniel Merida" in names
    # the alias key is the accent/punct-folded form, so a differently-punctuated variant folds too
    df2 = pd.DataFrame({"winner_name": ["Daniel  Merida-Aguilar"], "loser_name": ["X Y"],
                        "__src": [2]})
    assert set(results._canonicalize_names(df2.copy())["winner_name"]) == {"Daniel Merida"}
    print("ok test_canonicalize_merges_a_dropped_surname_via_alias")


# ---------------------------------------------------------------------------
# merge / dedup
# ---------------------------------------------------------------------------
def _write_csv(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_merge_dedup_prefers_stat_bearing_row():
    orig = (results.historical_dir, results.stats_dir, results.fresh_dir,
            results.live_dir, results.lower_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            hist, stats, fresh, live, lower = (base / "historical", base / "stats",
                                               base / "fresh", base / "live",
                                               base / "lower")
            for p in (hist, stats, fresh, live, lower):
                p.mkdir(parents=True, exist_ok=True)
            results.historical_dir = lambda tour: hist       # redirect (as in test_track)
            results.stats_dir = lambda tour: stats
            results.fresh_dir = lambda tour: fresh
            results.live_dir = lambda tour: live
            results.lower_dir = lambda tour: lower

            # historical: full schema (serve stats), accented spelling, YYYYMMDD dates
            _write_csv(hist / "2026.csv",
                "tourney_name,tourney_date,winner_name,loser_name,score,w_svpt,l_svpt\n"
                "Test Open,20260601,Félix Auger-Aliassime,Casper Ruud,7-6(4) 6-3,70,65\n")
            # fresh: results-only; row 1 duplicates the historical match (no stats),
            # row 2 is fresh-only and must survive
            _write_csv(fresh / "2026.csv",
                "tourney_name,tourney_date,winner_name,loser_name,score\n"
                "Test Open,2026/6/1,Felix Auger Aliassime,Casper Ruud,7-6(4) 6-3\n"
                "Test Open,2026/6/2,Casper Ruud,Novak Djokovic,6-4 6-4\n")
            # live (ESPN): duplicate again — plain spelling AND tiebreak points dropped
            # from the score — plus an ESPN-only result that must survive
            _write_csv(live / "live.csv",
                "tourney_name,tourney_date,winner_name,loser_name,score\n"
                "Test Open,2026-06-01,Felix Auger Aliassime,Casper Ruud,7-6 6-3\n"
                "Test Open,2026-06-03,Jannik Sinner,Felix Auger Aliassime,6-3 6-4\n")

            df = results.merge_sources("atp")
    finally:
        (results.historical_dir, results.stats_dir,
         results.fresh_dir, results.live_dir, results.lower_dir) = orig

    # 4 duplicate-collapsed rows -> 3 distinct matches
    assert len(df) == 3, df[["winner_name", "loser_name", "score"]]

    # the triplicated match kept the stat-bearing historical row (stats + full score)
    faa = df[(df["winner_name"] == "Félix Auger-Aliassime")
             & (df["loser_name"] == "Casper Ruud")]
    assert len(faa) == 1, df[["winner_name", "loser_name"]]
    assert float(faa["w_svpt"].iloc[0]) == 70.0
    assert faa["score"].iloc[0] == "7-6(4) 6-3"

    # the ESPN-only result survives, with its name canonicalised to the historical
    # spelling
    sinner = df[df["winner_name"] == "Jannik Sinner"]
    assert len(sinner) == 1
    assert sinner["loser_name"].iloc[0] == "Félix Auger-Aliassime"

    # the fresh-only result survives too
    assert ((df["winner_name"] == "Casper Ruud")
            & (df["loser_name"] == "Novak Djokovic")).sum() == 1
    print("ok test_merge_dedup_prefers_stat_bearing_row")


def test_espn_id_rides_along_without_changing_the_dedup_winner():
    """`espn_id` exists only on live-overlay rows — the archive predates it and always will —
    so it must be a HINT, never a key. This pins that the merge is behaviourally identical
    with the column present: the same three rows survive, and the triplicated match still
    keeps the stat-bearing HISTORICAL row, which carries no id at all."""
    orig = (results.historical_dir, results.stats_dir, results.fresh_dir,
            results.live_dir, results.lower_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            hist, stats, fresh, live, lower = (base / "historical", base / "stats",
                                               base / "fresh", base / "live", base / "lower")
            for p in (hist, stats, fresh, live, lower):
                p.mkdir(parents=True, exist_ok=True)
            results.historical_dir = lambda tour: hist
            results.stats_dir = lambda tour: stats
            results.fresh_dir = lambda tour: fresh
            results.live_dir = lambda tour: live
            results.lower_dir = lambda tour: lower

            _write_csv(hist / "2026.csv",                       # no espn_id column at all
                "tourney_name,tourney_date,winner_name,loser_name,score,w_svpt,l_svpt\n"
                "Test Open,20260601,Félix Auger-Aliassime,Casper Ruud,7-6(4) 6-3,70,65\n")
            _write_csv(fresh / "2026.csv",
                "tourney_name,tourney_date,winner_name,loser_name,score\n"
                "Test Open,2026/6/1,Felix Auger Aliassime,Casper Ruud,7-6(4) 6-3\n")
            # the live duplicate is the ONLY row with an id, and under a RENAMED event title
            _write_csv(live / "live.csv",
                "tourney_name,espn_id,tourney_date,winner_name,loser_name,score\n"
                "Test Open presented by Sponsor,100-2026,2026-06-01,"
                "Felix Auger Aliassime,Casper Ruud,7-6 6-3\n")

            df = results.merge_sources("atp")
    finally:
        (results.historical_dir, results.stats_dir,
         results.fresh_dir, results.live_dir, results.lower_dir) = orig

    assert "espn_id" in df.columns
    assert len(df) == 1, df[["tourney_name", "winner_name", "score"]]
    row = df.iloc[0]
    # the historical row still wins on merit (stats + full score) — the id did not tip it,
    # and the surviving row therefore has NO id, which is exactly why consumers must take
    # the modal non-null value per event rather than reading it off any single row
    # the historical row still wins on merit — the id did not tip the choice...
    assert float(row["w_svpt"]) == 70.0 and row["score"] == "7-6(4) 6-3"
    # ...but it INHERITS the id from the ESPN duplicate that was dropped. The id describes
    # the EVENT, not whichever row happened to survive; losing it there is what left the WTA
    # board shipping a 12-player "Washington Dc" fragment beside the full "Mubadala DC Open"
    # (2026-07-28) — one tournament, two cards, two different favourites.
    assert row["espn_id"] == "100-2026", row["espn_id"]
    print("ok test_espn_id_rides_along_without_changing_the_dedup_winner")


def test_the_surviving_group_keeps_the_id_when_sources_name_the_event_differently():
    """The live 2026-07-28 split, reproduced. The fresh feed calls it "Washington Dc" and
    ESPN calls it "Mubadala DC Open"; dedup keys ignore tourney_name, so the ESPN rows are
    dropped as duplicates and their id went with them. The board then had no way to know the
    two were one event and shipped both — a 12-player fragment beside the real 28-draw."""
    orig = (results.historical_dir, results.stats_dir, results.fresh_dir,
            results.live_dir, results.lower_dir)
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
            # fresh feed: the archive city name, no id, and it WINS the dedup (earlier source)
            _write_csv(dirs["fresh"] / "2026.csv",
                "tourney_name,tourney_date,winner_name,loser_name,score\n"
                "Washington Dc,2026/7/27,A Player,B Player,6-4 6-4\n"
                "Washington Dc,2026/7/27,C Player,D Player,7-5 6-3\n")
            # ESPN: same two matches under the sponsor title, carrying the id
            _write_csv(dirs["live"] / "live.csv",
                "tourney_name,espn_id,tourney_date,winner_name,loser_name,score\n"
                "Mubadala DC Open,888-2026,2026-07-27,A Player,B Player,6-4 6-4\n"
                "Mubadala DC Open,888-2026,2026-07-27,C Player,D Player,7-5 6-3\n")
            df = results.merge_sources("atp")
    finally:
        (results.historical_dir, results.stats_dir,
         results.fresh_dir, results.live_dir, results.lower_dir) = orig

    assert len(df) == 2, df[["tourney_name", "winner_name"]]      # one event, not two
    assert set(df["tourney_name"]) == {"Washington Dc"}           # the fresh name still wins
    assert set(df["espn_id"]) == {"888-2026"}, set(df["espn_id"])  # ...but keeps the identity
    print("ok test_the_surviving_group_keeps_the_id_when_sources_name_the_event_differently")


def test_espn_id_column_exists_even_when_no_source_supplies_it():
    """`_read_dir` already keeps whatever extra columns a CSV happens to carry, so a live.csv
    with an id would surface one regardless. What listing it in CANON guarantees is the case
    that actually bites: an ARCHIVE-ONLY frame (an off-week, a fresh clone, any tour whose
    live overlay failed) must still expose the column, so a consumer reading it never hits a
    KeyError."""
    orig = (results.historical_dir, results.stats_dir, results.fresh_dir,
            results.live_dir, results.lower_dir)
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
            _write_csv(dirs["historical"] / "2026.csv",     # no espn_id anywhere on disk
                "tourney_name,tourney_date,winner_name,loser_name,score\n"
                "Test Open,20260601,A Player,B Player,6-4 6-4\n")
            df = results.merge_sources("atp")
    finally:
        (results.historical_dir, results.stats_dir,
         results.fresh_dir, results.live_dir, results.lower_dir) = orig
    assert "espn_id" in df.columns, df.columns.tolist()
    assert df["espn_id"].isna().all()
    print("ok test_espn_id_column_exists_even_when_no_source_supplies_it")


def test_same_day_rematch_survives_dedup():
    """Archive sources stamp every match with the tournament START date, so a
    round-robin meeting and a final rematch share (pair, date). The same-day dedup
    pass must key on round too (regression: it silently dropped ~181 real matches,
    e.g. Federer d. Hewitt twice at the 2004 Masters Cup)."""
    orig = (results.historical_dir, results.stats_dir, results.fresh_dir,
            results.live_dir, results.lower_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            hist, stats, fresh, live, lower = (base / "historical", base / "stats",
                                               base / "fresh", base / "live",
                                               base / "lower")
            for p in (hist, stats, fresh, live, lower):
                p.mkdir(parents=True, exist_ok=True)
            results.historical_dir = lambda tour: hist
            results.stats_dir = lambda tour: stats
            results.fresh_dir = lambda tour: fresh
            results.live_dir = lambda tour: live
            results.lower_dir = lambda tour: lower

            # RR meeting + final rematch, both stamped with the event start date
            _write_csv(hist / "2004.csv",
                "tourney_name,tourney_date,winner_name,loser_name,round,score,w_svpt,l_svpt\n"
                "Masters Cup,20041114,Roger Federer,Lleyton Hewitt,RR,6-3 6-4,55,50\n"
                "Masters Cup,20041114,Roger Federer,Lleyton Hewitt,F,6-3 6-2,60,52\n")
            # a fresh duplicate of the FINAL whose score disagrees on games (the case
            # the same-day pass exists for) — must collapse into the historical row
            _write_csv(fresh / "2004.csv",
                "tourney_name,tourney_date,winner_name,loser_name,round,score\n"
                "Masters Cup,2004/11/14,Roger Federer,Lleyton Hewitt,F,6-3 5-2 RET\n")

            df = results.merge_sources("atp")
    finally:
        (results.historical_dir, results.stats_dir,
         results.fresh_dir, results.live_dir, results.lower_dir) = orig

    pair = df[(df["winner_name"] == "Roger Federer") & (df["loser_name"] == "Lleyton Hewitt")]
    assert len(pair) == 2, pair[["round", "score"]]           # RR and F both survive
    assert set(pair["round"]) == {"RR", "F"}
    fin = pair[pair["round"] == "F"]
    assert fin["score"].iloc[0] == "6-3 6-2"                  # stat-bearing row won the dup
    print("ok test_same_day_rematch_survives_dedup")


def test_future_dated_row_is_dropped_at_ingest():
    """One mistyped year is enough to corrupt every date-relative quantity downstream,
    because they anchor on the dataset's MAX date, not on today. The WTA fresh overlay
    carried the Iasi final as `2029/7/20` on 2026-07-25; elo.last_date jumped three years,
    the 550-day active-player window then held only the two players in that row, and the
    tour exported 2 players instead of 200 (crashing build_draws on a 2-slot bracket).

    A near-future row must SURVIVE — the live overlay legitimately carries scheduled
    matches ~12 days out, and silently dropping real fixtures would be its own bug.
    """
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    soon = (today + pd.Timedelta(days=5)).strftime("%Y/%m/%d")
    corrupt = (today + pd.Timedelta(days=3 * 365)).strftime("%Y/%m/%d")
    orig = (results.historical_dir, results.stats_dir, results.fresh_dir,
            results.live_dir, results.lower_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            hist, stats, fresh, live, lower = (base / "historical", base / "stats",
                                               base / "fresh", base / "live",
                                               base / "lower")
            for p in (hist, stats, fresh, live, lower):
                p.mkdir(parents=True, exist_ok=True)
            results.historical_dir = lambda tour: hist
            results.stats_dir = lambda tour: stats
            results.fresh_dir = lambda tour: fresh
            results.live_dir = lambda tour: live
            results.lower_dir = lambda tour: lower

            _write_csv(fresh / "2026.csv",
                "tourney_name,tourney_date,winner_name,loser_name,score\n"
                f"Iasi,{soon},Elina Svitolina,Jessica Pegula,6-4 6-4\n"
                f"Iasi,{corrupt},Mayar Sherif,Paula Badosa,6-4 4-0 RET\n")

            df = results.merge_sources("wta")
    finally:
        (results.historical_dir, results.stats_dir,
         results.fresh_dir, results.live_dir, results.lower_dir) = orig

    names = set(df["winner_name"]) | set(df["loser_name"])
    assert "Mayar Sherif" not in names and "Paula Badosa" not in names, sorted(names)
    assert "Elina Svitolina" in names, sorted(names)          # scheduled row survives
    assert df["date"].max() < today + pd.Timedelta(days=60)
    print("ok test_future_dated_row_is_dropped_at_ingest")


if __name__ == "__main__":
    test_name_key_folds_accents_and_punct()
    test_score_key_ignores_tiebreak_points()
    test_canonicalize_prefers_historical_spelling()
    test_canonicalize_merges_a_dropped_surname_via_alias()
    test_merge_dedup_prefers_stat_bearing_row()
    test_same_day_rematch_survives_dedup()
    test_future_dated_row_is_dropped_at_ingest()
    print("\nALL PASSED")
