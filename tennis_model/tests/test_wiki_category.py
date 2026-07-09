"""Wikipedia tier/category scrape + level resolution for the schedule board's tier chips.
Fully synthetic: fixture wikitext for `_parse_category`, a monkeypatched wiki cache for
`resolve_level` — no network. Runnable directly or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.draws_wiki import _parse_category

from tennis_model.data import surface

# Real infobox `category=` shapes: single (ITF) link, combined ATP+WTA split by <br>, and omitted.
_WIMBLEDON = "{{TennisEventInfo|2025|Wimbledon\n| category = [[Grand Slam (tennis)|Grand Slam]] (ITF)\n| surface=[[Grass court|Grass]]}}"
_MIAMI = "{{Infobox tennis event|2025|Miami Open\n|category=[[ATP Masters 1000 tournaments|ATP Masters 1000]] (ATP)<br />[[WTA 1000 tournaments|WTA 1000]] (WTA)}}"
_EASTBOURNE = "{{TennisEventInfo|2025|Eastbourne Open\n|category=[[ATP 250 tournaments|ATP 250]] (men)<br>[[WTA 250 tournaments|WTA 250]] (women)}}"
_SWEDISH = "{{Infobox tennis event|2025|Swedish Open|\n| surface=[[Clay court|Clay]] / outdoor\n| venue=[[Bastad Tennis Stadium]]}}"
# Bare link (no `|display` alias) — the raw target must be cleaned to "WTA 125".
_PALERMO = "{{Infobox tennis event|2025|Palermo Ladies Open\n|category=[[WTA 125 tournaments]]}}"


def test_parse_category_single_link_slam():
    assert _parse_category(_WIMBLEDON, "atp") == "Grand Slam"
    assert _parse_category(_WIMBLEDON, "wta") == "Grand Slam"


def test_parse_category_combined_picks_by_tour():
    assert _parse_category(_MIAMI, "atp") == "ATP Masters 1000"
    assert _parse_category(_MIAMI, "wta") == "WTA 1000"
    assert _parse_category(_EASTBOURNE, "atp") == "ATP 250"
    assert _parse_category(_EASTBOURNE, "wta") == "WTA 250"


def test_parse_category_absent_returns_none():
    assert _parse_category(_SWEDISH, "wta") is None
    assert _parse_category("", "wta") is None


def test_parse_category_bare_link_target_cleaned():
    assert _parse_category(_PALERMO, "wta") == "WTA 125"
    assert _parse_category("{{x|category=[[Grand Slam (tennis)]]}}", "atp") == "Grand Slam"


def test_resolve_level_fallback(monkeypatch):
    # No wiki category -> curated fallback (numeric -> "{TOUR} 250"); unlisted -> generic.
    monkeypatch.setattr(surface, "wiki_category", lambda tour, event: None)
    assert surface.resolve_level("wta", "Nordea Open") == "WTA 250"
    assert surface.resolve_level("atp", "Nordea Open") == "ATP 250"
    assert surface.resolve_level("wta", "Unlisted Event") == "WTA Tour"
    # a fallback key inside a giant sponsor name still matches (substring)
    assert surface.resolve_level("wta", "Cerity Partners Hall of Fame Open for the Van Alen Cup") == "WTA 250"


def test_resolve_level_wiki_beats_fallback(monkeypatch):
    monkeypatch.setattr(surface, "wiki_category", lambda tour, event: "WTA 500")
    assert surface.resolve_level("wta", "Nordea Open") == "WTA 500"


def test_resolve_level_archive_first(monkeypatch):
    monkeypatch.setattr(surface, "wiki_category", lambda tour, event: "WTA 500")
    assert surface.resolve_level("wta", "X", archive_level="Grand Slam") == "Grand Slam"
    # a generic archive level is not trusted -> defers to wiki/fallback
    assert surface.resolve_level("wta", "X", archive_level="WTA Tour") == "WTA 500"


if __name__ == "__main__":
    for _fn in (test_parse_category_single_link_slam, test_parse_category_combined_picks_by_tour,
                test_parse_category_absent_returns_none):
        _fn()
        print("ok", _fn.__name__)
    print("(resolve_level tests need pytest's monkeypatch)")
