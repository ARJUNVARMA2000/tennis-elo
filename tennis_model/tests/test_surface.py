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


def test_parse_surface_reads_one_word_link_targets():
    """`[[Hardcourt|Hard (outdoor)]]` — the field capture stops at the pipe, so the parser
    only ever sees the link TARGET, and hard courts spell it as ONE word. A bare \\bHard\\b
    could not match inside "Hardcourt", so every hard-court event resolved to no surface and
    fell through to the month guess: the DC Open, a hard court, shipped priced on grass Elo
    on both tours (2026-07-27)."""
    assert _parse_surface("| surface     = [[Hardcourt|Hard (outdoor)]]") == "Hard"
    assert _parse_surface("| surface = [[Hardcourt]]") == "Hard"
    assert _parse_surface("| surface = Hardcourt (indoor)") == "Hard"
    assert _parse_surface("| surface = [[Clay courts|Clay]]") == "Clay"
    # ...and the link TARGET need not name the surface at all — Memphis puts it in the
    # DISPLAY text behind a generic target, so the field must be read to end of line.
    assert _parse_surface("| surface=[[Tennis court#outdoor courts|Hard]] / outdoor") == "Hard"
    # the guard against reading a stray word still holds — "court" is optional, not a licence
    assert _parse_surface("| surface = Hardy Athletic Club") is None
    assert _parse_surface("| surface = Grasshopper Club") is None
    print("ok test_parse_surface_reads_one_word_link_targets")


def test_resolve_surface_info_reports_provenance():
    orig = surf.wiki_surface_map
    try:
        surf.wiki_surface_map = lambda tour: {"Nordea Open": "Clay"}
        assert surf.resolve_surface_info("wta", "Nordea Open", "2026-07-06",
                                         archive_surface="Hard") == ("Hard", "archive")
        assert surf.resolve_surface_info("wta", "Nordea Open", "2026-07-06") == ("Clay", "wiki")
        assert surf.resolve_surface_info("wta", "Unknown Event", "2026-07-06") == ("Grass", "month")
    finally:
        surf.wiki_surface_map = orig
    print("ok test_resolve_surface_info_reports_provenance")


def test_wiki_lookup_is_tolerant_so_surface_cannot_flip_on_start_day():
    """The pre-start path matched the archive loosely while the live path matched exactly,
    so one event could change surface the day it started — WTA Memphis read Hard while
    upcoming and flipped to a July Grass guess on day one. Both paths now share this lookup."""
    orig = surf.wiki_surface_map
    try:
        surf.wiki_surface_map = lambda tour: {"The Memphis Classic": "Hard"}
        # cache holds the sponsor title; the board shows the de-sponsored city
        assert surf.wiki_surface("wta", "The Memphis Classic") == "Hard"   # exact
        assert surf.wiki_surface("wta", "the  memphis   classic") == "Hard"  # normalised
        assert surf.wiki_surface("wta", "Memphis Classic") == "Hard"       # containment
        assert surf.resolve_surface_info("wta", "Memphis Classic", "2026-07-27")[0] == "Hard"
        # too-short and unrelated keys must NOT match by containment
        assert surf.wiki_surface("wta", "Rome") is None
        # an ambiguous hit resolves to None rather than guessing
        surf.wiki_surface_map = lambda tour: {"Open Sud Clay": "Clay", "Open Sud Hard": "Hard"}
        assert surf.wiki_surface("atp", "Open Sud") is None
    finally:
        surf.wiki_surface_map = orig
    print("ok test_wiki_lookup_is_tolerant_so_surface_cannot_flip_on_start_day")


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


def test_normalize_level_folds_every_source_dialect():
    """Three sources, three dialects, all of which used to ship RAW: one board carried
    'ATP 250 series', 'ATP 250' and 'C' as if they were different tiers."""
    n = surf.normalize_level
    assert n("ATP 250 series", "atp") == "ATP 250"          # wiki display prose
    assert n("ATP Tour Masters 1000", "atp") == "Masters 1000"
    assert n("WTA 125 tournaments", "wta") == "WTA 125"
    assert n("C", "atp") == "Challenger"                     # archive single-letter codes
    assert n("G", "wta") == "Grand Slam"
    assert n("F", "atp") == "Tour Finals"
    assert n("M", "wta") == "WTA 1000"                       # tour-relative
    assert n("M", "atp") == "Masters 1000"
    assert n("250", "wta") == "WTA 250"                      # curated bare numbers
    assert n("A", "atp") == n("Q", "atp") == "ATP Tour"
    assert n(None, "atp") is None and n("nan", "atp") is None
    assert n("Some Exhibition", "atp") is None               # unknown -> None, never a guess
    # every value the normaliser emits must be sayable in that tour's vocabulary
    for tour in ("atp", "wta"):
        for raw in ("ATP 250 series", "C", "G", "F", "M", "O", "D", "250", "125",
                    "WTA 1000", "Grand Slam", "United Cup", "A"):
            v = n(raw, tour)
            assert v is None or v in surf.LEVEL_VOCAB[tour], (tour, raw, v)
    print("ok test_normalize_level_folds_every_source_dialect")


def test_resolve_level_normalizes_whichever_branch_wins():
    orig = surf.wiki_category_map
    try:
        surf.wiki_category_map = lambda tour: {"Generali Open": "ATP 250 series"}
        # wiki branch is normalised, not passed through raw
        assert surf.resolve_level("atp", "Generali Open") == "ATP 250"
        # archive branch too — "C" used to ship verbatim on the card
        assert surf.resolve_level("atp", "Generali Open", archive_level="C") == "Challenger"
        # a generic archive level does not win; the wiki branch still gets its turn
        assert surf.resolve_level("atp", "Generali Open", archive_level="ATP Tour") == "ATP 250"
        # nothing resolves -> the generic, never an unreadable string
        surf.wiki_category_map = lambda tour: {}
        assert surf.resolve_level("atp", "Totally Unknown Cup") == "ATP Tour"
    finally:
        surf.wiki_category_map = orig
    print("ok test_resolve_level_normalizes_whichever_branch_wins")


def _row(**over):
    """A minimal ESPN-style live row (surface unknown) that survives results.clean."""
    base = {"tourney_name": "Nordea Open", "date": pd.Timestamp("2026-07-06"),
            "tourney_date": "2026-07-06", "surface": None, "tourney_level": None,
            "best_of": None, "round": "R32", "indoor": "O",
            "winner_name": "A Player", "loser_name": "B Player", "score": "6-4 6-3",
            "w_svpt": None, "l_svpt": None}
    base.update(over)
    return base


def _cleaned(cache, **over):
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
    return out


def _surface_b(cache, **over):
    return _cleaned(cache, **over)["surface_b"].iloc[0]


def test_loader_stamps_surface_provenance():
    """Every row records WHICH tier answered, so a consumer can refuse to recycle a month
    guess as though the archive had asserted it."""
    assert _cleaned(None)["surface_src"].iloc[0] == "month"
    assert _cleaned({"Nordea Open": "Clay"})["surface_src"].iloc[0] == "wiki"
    assert _cleaned({"Nordea Open": "Clay"}, surface="Hard")["surface_src"].iloc[0] == "archive"
    print("ok test_loader_stamps_surface_provenance")


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
    test_parse_surface_reads_one_word_link_targets()
    test_resolve_surface_info_reports_provenance()
    test_wiki_lookup_is_tolerant_so_surface_cannot_flip_on_start_day()
    test_wiki_surface_map_reads_and_degrades()
    test_resolve_surface_priority()
    test_loader_stamps_surface_provenance()
    test_loader_backfills_surface_from_wiki_cache_else_month()
    print("\nALL PASSED")
