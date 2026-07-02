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


def test_score_key_ignores_tiebreak_points():
    sk = results._score_key
    assert sk("7-6(4) 6-3") == sk("7-6 6-3") == "7-66-3"
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


# ---------------------------------------------------------------------------
# merge / dedup
# ---------------------------------------------------------------------------
def _write_csv(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_merge_dedup_prefers_stat_bearing_row():
    orig = (results.historical_dir, results.fresh_dir, results.live_dir)
    try:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            hist, fresh, live = base / "historical", base / "fresh", base / "live"
            for p in (hist, fresh, live):
                p.mkdir(parents=True, exist_ok=True)
            results.historical_dir = lambda tour: hist       # redirect (as in test_track)
            results.fresh_dir = lambda tour: fresh
            results.live_dir = lambda tour: live

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
        results.historical_dir, results.fresh_dir, results.live_dir = orig

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


if __name__ == "__main__":
    test_name_key_folds_accents_and_punct()
    test_score_key_ignores_tiebreak_points()
    test_canonicalize_prefers_historical_spelling()
    test_merge_dedup_prefers_stat_bearing_row()
    print("\nALL PASSED")
