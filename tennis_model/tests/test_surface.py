"""Court-surface resolution — fully offline (fixture wikitext + a tmp cache, no network).

Pins the fix for clay events mislabeled Grass: the infobox surface parser (main-article
``surface=`` -> canonical, Carpet -> Hard), the priority chain archive -> Wikipedia cache ->
month fallback, and the end-to-end loader behaviour — a July sponsor-named clay event reads
Clay from the cached Wikipedia surface instead of the July=Grass month guess.

Runnable directly (`python tests/test_surface.py`) or under pytest.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.draws_wiki import _parse_surface
from tennis_model.data.results import clean

from tennis_model.data import surface as surf


def test_parse_surface_reads_infobox_and_canonicalizes():
    # the surface lives in the main article's infobox, e.g. `| surface=[[Clay court|Clay]]`
    assert _parse_surface("| surface=[[Clay court|Clay]] / outdoor") == "Clay"
    assert _parse_surface("|surface = [[Grass court|Grass]]") == "Grass"
    assert _parse_surface("| surface = [[Hard court|Hard]] ([[indoor]])") == "Hard"
    assert _parse_surface("| Surface=[[Carpet court|Carpet]]") == "Hard"   # Carpet folds to Hard
    assert _parse_surface("| surface = Clay") == "Clay"                    # bare value, no wikilink
    # scoping: a "Grass" that isn't the surface field must NOT be read as the surface
    assert _parse_surface("| location = Grass Valley, USA") is None
    assert _parse_surface("no infobox here at all") is None
    # first surface field without a known keyword is skipped; a later valid one wins
    assert _parse_surface("| surface=TBD\n| surface=[[Clay court|Clay]]") == "Clay"
    print("ok test_parse_surface_reads_infobox_and_canonicalizes")


def test_wiki_surface_map_reads_and_degrades():
    orig = surf.live_dir
    try:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            surf.live_dir = lambda tour: tmp
            # missing cache -> empty map / None (a fresh checkout degrades to the month fallback)
            assert surf.wiki_surface_map("wta") == {}
            assert surf.wiki_surface("wta", "Nordea Open") is None
            (tmp / "wiki_surface.json").write_text(
                json.dumps({"Nordea Open": "Clay"}), encoding="utf-8")
            assert surf.wiki_surface_map("wta") == {"Nordea Open": "Clay"}
            assert surf.wiki_surface("wta", "Nordea Open") == "Clay"
            # a corrupt cache never raises — it reads as empty
            (tmp / "wiki_surface.json").write_text("{ not json", encoding="utf-8")
            assert surf.wiki_surface_map("wta") == {}
    finally:
        surf.live_dir = orig
    print("ok test_wiki_surface_map_reads_and_degrades")


def test_resolve_surface_priority():
    orig = surf.wiki_surface_map
    try:
        surf.wiki_surface_map = lambda tour: {"Nordea Open": "Clay"}
        # 1. a real archive value is authoritative — the cache is not consulted
        assert surf.resolve_surface("wta", "Nordea Open", "2026-07-06", archive_surface="Hard") == "Hard"
        # 2. no archive -> Wikipedia cache
        assert surf.resolve_surface("wta", "Nordea Open", "2026-07-06") == "Clay"
        # 3. no archive, not cached -> month fallback (July -> Grass, February -> Hard)
        assert surf.resolve_surface("wta", "Unknown Event", "2026-07-06") == "Grass"
        assert surf.resolve_surface("wta", "Unknown Event", "2026-02-01") == "Hard"
    finally:
        surf.wiki_surface_map = orig
    print("ok test_resolve_surface_priority")


def _row(**over):
    """A minimal ESPN-style live row (surface unknown) that survives results.clean."""
    base = {"tourney_name": "Nordea Open", "date": pd.Timestamp("2026-07-06"),
            "tourney_date": "2026-07-06", "surface": None, "tourney_level": None,
            "best_of": None, "round": "R32", "indoor": "O",
            "winner_name": "A Player", "loser_name": "B Player", "score": "6-4 6-3",
            "w_svpt": None, "l_svpt": None}
    base.update(over)
    return base


def _surface_b(cache, **over):
    orig = surf.live_dir
    try:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            if cache is not None:
                (tmp / "wiki_surface.json").write_text(json.dumps(cache), encoding="utf-8")
            surf.live_dir = lambda tour: tmp
            out = clean(pd.DataFrame([_row(**over)]), tour="wta")
    finally:
        surf.live_dir = orig
    return out["surface_b"].iloc[0]


def test_loader_backfills_surface_from_wiki_cache_else_month():
    # July "Nordea Open" (clay) is absent from this synthetic archive. Without a cache it falls
    # to the July month guess (Grass — the bug); with the wiki cache it reads the true Clay.
    assert _surface_b(None) == "Grass"                                 # month fallback (bug shape)
    assert _surface_b({"Nordea Open": "Clay"}) == "Clay"               # wiki cache beats the month
    # a real surface already on the row stays authoritative (cache not consulted)
    assert _surface_b({"Nordea Open": "Clay"}, surface="Hard") == "Hard"
    print("ok test_loader_backfills_surface_from_wiki_cache_else_month")


if __name__ == "__main__":
    test_parse_surface_reads_infobox_and_canonicalizes()
    test_wiki_surface_map_reads_and_degrades()
    test_resolve_surface_priority()
    test_loader_backfills_surface_from_wiki_cache_else_month()
    print("\nALL PASSED")
