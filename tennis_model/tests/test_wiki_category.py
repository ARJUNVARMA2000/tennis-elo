"""Wikipedia tier/category scrape + level resolution for the schedule board's tier chips.
Fully synthetic: fixture wikitext for `_parse_category`, a monkeypatched wiki cache for
`resolve_level` — no network. Runnable directly or under pytest.
"""

from __future__ import annotations

import json
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


def test_parse_category_never_returns_the_other_tours_tier():
    """The ATP board shipped Generali Open as "WTA 125".

    Two holes. (1) A LONE link was returned unconditionally, so an ATP lookup that landed on
    the WTA article of a combined event took that tour's tier. (2) The tour tags were plain
    substrings, and "men" is inside "tournaMENts" — so `[[WTA 125 tournaments|WTA 125]]`
    matched the ATP tags outright. None is the right answer; the caller then falls back."""
    # (1) a WTA-only article asked for atp
    assert _parse_category(_PALERMO, "wta") == "WTA 125"      # still right for its own tour
    assert _parse_category(_PALERMO, "atp") is None
    # (2) the substring trap, isolated: nothing here is ATP's
    wta_only = "{{x|category=[[WTA 250 tournaments|WTA 250]] (women)}}"
    assert _parse_category(wta_only, "wta") == "WTA 250"
    assert _parse_category(wta_only, "atp") is None
    atp_only = "{{x|category=[[ATP 500 tournaments|ATP 500]] (men)}}"
    assert _parse_category(atp_only, "atp") == "ATP 500"
    assert _parse_category(atp_only, "wta") is None
    # a tour-neutral single link is still ours by elimination (a Slam's (ITF) link)
    assert _parse_category(_WIMBLEDON, "atp") == "Grand Slam"
    # ...and one neutral link beside an explicitly-other-tour one resolves by elimination
    mixed = "{{x|category=[[Grand Slam (tennis)|Grand Slam]]<br />[[WTA 1000]] (WTA)}}"
    assert _parse_category(mixed, "atp") == "Grand Slam"
    assert _parse_category(mixed, "wta") == "WTA 1000"


def test_parse_category_untagged_multi_link_refuses_to_guess():
    """Two untagged links say nothing about which tour they describe; `picks[0]` is just
    whichever the editor typed first, which is not evidence."""
    untagged = "{{x|category=[[Some Series]]<br />[[Another Series]]}}"
    assert _parse_category(untagged, "atp") is None
    assert _parse_category(untagged, "wta") is None


def test_category_cache_refetches_a_poisoned_cross_tour_value(tmp_path, monkeypatch):
    """"Already resolved — keep it" pinned the other tour's tier forever.

    Same first-capture-wins trap `_draw_is_settled` fixes for draws: a value cached before the
    tour gate existed ("WTA 125" on the ATP board) would never be revisited. A cached tier is
    kept only while it is still sayable in this tour's vocabulary."""
    from tennis_model.data import draws_wiki as dw

    (tmp_path / "wiki_category.json").write_text(json.dumps({
        "Generali Open": "WTA 125",          # poisoned — not an ATP tier
        "Swiss Open Gstaad": "ATP 250",      # valid — must be kept without a re-fetch
    }), encoding="utf-8")
    # both events already have a surface, so only the TIER decides whether we re-fetch
    (tmp_path / "wiki_surface.json").write_text(json.dumps({
        "Generali Open": "Clay", "Swiss Open Gstaad": "Clay"}), encoding="utf-8")
    calls = []

    def _fake(name, year, tour):
        calls.append(name)
        return "Clay", "ATP 250 series"

    monkeypatch.setattr(dw, "event_meta", _fake)
    meta = {"Generali Open": {"start": "2026-07-20"},
            "Swiss Open Gstaad": {"start": "2026-07-13"}}
    dw._download_wiki_meta("atp", tmp_path, meta)

    out = json.loads((tmp_path / "wiki_category.json").read_text(encoding="utf-8"))
    assert calls == ["Generali Open"], calls          # only the poisoned entry re-fetched
    assert out["Generali Open"] == "ATP 250 series"
    assert out["Swiss Open Gstaad"] == "ATP 250"
    # a re-fetch that yields nothing DROPS the bad value rather than carrying it forward —
    # no cached tier (which falls through to archive/fallback) beats the wrong tour's tier
    (tmp_path / "wiki_category.json").write_text(json.dumps({
        "Generali Open": "WTA 125", "Swiss Open Gstaad": "ATP 250"}), encoding="utf-8")
    monkeypatch.setattr(dw, "event_meta", lambda name, year, tour: (None, None))
    dw._download_wiki_meta("atp", tmp_path, meta)
    out = json.loads((tmp_path / "wiki_category.json").read_text(encoding="utf-8"))
    assert "Generali Open" not in out
    assert out["Swiss Open Gstaad"] == "ATP 250"     # a still-valid entry is untouched


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
                test_parse_category_absent_returns_none,
                test_parse_category_never_returns_the_other_tours_tier,
                test_parse_category_untagged_multi_link_refuses_to_guess):
        _fn()
        print("ok", _fn.__name__)
    print("(resolve_level tests need pytest's monkeypatch)")
