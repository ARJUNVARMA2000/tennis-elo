"""Wikipedia draw parsing — fully offline (fixture wikitext, no network).

Pins the pieces that make "download the whole draw at release" correct: the ORDERED
bracket is stitched from the `-Compact-` section templates (late-round summary brackets
ignored), seed byes become (player, None), qualifier/undetermined slots are kept distinct,
and best-of comes from the Tennis3/Tennis5 template family. Also covers title resolution's
distinctive-anchor guard (so "... Open ... singles" can't resolve to the wrong Open) and
the first-round rows the schedule board / forecast log consume.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mwparserfromhell
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data import draws_wiki as dw
from tennis_model.data.draws_wiki import _anchor, _parse_bracket, _rows_from_draws, _slot_name

# An 8-leaf compact section (Tennis5 = best-of-5) with a seed BYE in the first match
# (leaves 1,2 absent; the seed rides in RD2-team01), plus a non-compact summary bracket
# that MUST be ignored, and a "(tennis)" disambiguator that must be stripped.
FIXTURE = """
{{4TeamBracket-Tennis3 | RD1-team01=[[Ignore Summary]] | RD1-team02=[[Ignore Two]] }}
{{8TeamBracket-Compact-Tennis5-Byes
| RD1-seed03=3
| RD1-team03=[[Player C]]
| RD1-team04=[[Player D (tennis)|P Player D]]
| RD1-team05=[[Player E]]
| RD1-team06=[[Player F]]
| RD1-team07=[[Player G]]
| RD1-team08=[[Player H]]
| RD2-team01=[[Player A]]
}}
"""


def test_parse_bracket_orders_sections_handles_bye_and_bestof():
    d = _parse_bracket(FIXTURE)
    assert d is not None
    # leaves 1,2 absent -> bye seat (Player A, None); the rest are the ordered R1 pairs.
    assert d["slots"] == ["Player A", None, "Player C", "Player D", "Player E",
                          "Player F", "Player G", "Player H"]
    assert d["bestOf"] == 5                 # Tennis5 family
    assert d["seeds"] == {"Player C": 3}
    # the non-compact 4TeamBracket summary was ignored (no "Ignore Summary" leak)
    assert "Ignore Summary" not in d["slots"]
    print("ok test_parse_bracket_orders_sections_handles_bye_and_bestof")


def test_parse_bracket_qualifiers_are_distinct_and_not_a_power_of_two_is_none():
    q = """
    {{4TeamBracket-Compact-Tennis3
    | RD1-team01=Qualifier | RD1-team02=[[Player X]]
    | RD1-team03=[[Player Y]] | RD1-team04=Q
    }}
    """
    d = _parse_bracket(q)
    assert d["slots"] == ["Qualifier 1", "Player X", "Player Y", "Qualifier 2"]  # unique
    assert d["bestOf"] == 3
    # mismatched section sizes don't stitch to a power of two -> rejected (no draw)
    four = "{{4TeamBracket-Compact-Tennis3|RD1-team01=[[A]]|RD1-team02=[[B]]|RD1-team03=[[C]]|RD1-team04=[[D]]}}"
    eight = "{{8TeamBracket-Compact-Tennis3|" + "|".join(f"RD1-team{i:02d}=[[E{i}]]" for i in range(1, 9)) + "}}"
    assert _parse_bracket(four + eight) is None          # 4 + 8 = 12, not a power of two
    assert _parse_bracket("no bracket templates here") is None
    print("ok test_parse_bracket_qualifiers_are_distinct_and_not_a_power_of_two_is_none")


def test_slot_name_strips_disambiguator_and_reads_byes():
    def val(s):
        return mwparserfromhell.parse(s)
    assert _slot_name(val("[[Pedro Martínez (tennis)|P Martínez]]")) == "Pedro Martínez"
    assert _slot_name(val("[[Jannik Sinner]]")) == "Jannik Sinner"
    assert _slot_name(val("Bye")) is None
    assert _slot_name(val("Qualifier")) == "Qualifier"
    assert _slot_name(val("")) == "Qualifier"          # empty slot -> placeholder, not a bye
    print("ok test_slot_name_strips_disambiguator_and_reads_byes")


def test_anchor_rejects_generic_only_names():
    # the distinctive token (city/name), never a generic word like "Open"
    assert _anchor("Winston-Salem Open") == "winston"
    assert _anchor("Swiss Open Gstaad") == "gstaad"
    assert _anchor("Cincinnati Open") == "cincinnati"
    assert _anchor("US Open") is None                   # all-generic -> explicit locator required
    print("ok test_anchor_rejects_generic_only_names")


def test_generic_only_draw_requires_exact_espn_locator(monkeypatch):
    """The unanchored 2026 US Open search returned whichever same-year Slam ranked first:
    French Open for ATP and Wimbledon for WTA. It must never call search without an anchor."""
    monkeypatch.setattr(dw, "WIKI_DRAW_TITLE_OVERRIDES", {
        "atp": {"189-2026": "2026 US Open – Men's singles"},
        "wta": {"189-2026": "2026 US Open – Women's singles"},
    })
    monkeypatch.setattr(
        dw, "_search_title",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unsafe search called")))

    assert dw.resolve_title("US Open", 2026, "wta") is None
    assert dw.resolve_title("US Open", 2026, "wta", "189-2026") == (
        "2026 US Open – Women's singles")
    assert dw.resolve_title("US Open", 2026, "atp", "189-2026") == (
        "2026 US Open – Men's singles")


def test_title_search_rejects_wrong_gender_before_accepting_the_event(monkeypatch):
    monkeypatch.setattr(dw, "_get", lambda _params: {"query": {"search": [
        {"title": "2026 Cincinnati Open – Men's singles"},
        {"title": "2026 Cincinnati Open – Women's singles"},
    ]}})
    assert dw._search_title(
        "2026 Cincinnati Open Women's singles", 2026, "cincinnati", "women",
    ) == "2026 Cincinnati Open – Women's singles"


def test_rows_from_draws_skips_byes_and_qualifiers():
    draws = {"Test Cup": {"start": "2026-08-01",
                          "slots": ["A", "B", "C", None, "Qualifier 1", "D", "E", "F"]}}
    rows = _rows_from_draws(draws)
    pairs = {(r["playerA"], r["playerB"]) for r in rows}
    assert pairs == {("A", "B"), ("E", "F")}            # (C,None) bye + (Q,D) qualifier dropped
    assert all(r["round"] == "QF" and r["tourney_date"] == "2026-08-01" for r in rows)  # 8 slots
    print("ok test_rows_from_draws_skips_byes_and_qualifiers")


def test_rows_from_draws_only_prestart_events():
    """A draw is only surfaced on the schedule board before the event starts; once under
    way, ESPN's live feed owns the round (else finished R1 matches would replay)."""
    draws = {"Future": {"start": "2026-08-20", "slots": ["A", "B", "C", "D"]},
             "Running": {"start": "2026-08-01", "slots": ["E", "F", "G", "H"]}}
    events = {r["tourney_name"] for r in _rows_from_draws(draws, today="2026-08-10")}
    assert events == {"Future"}                          # "Running" (already started) skipped
    assert {r["tourney_name"] for r in _rows_from_draws(draws)} == {"Future", "Running"}  # no clock -> all
    print("ok test_rows_from_draws_only_prestart_events")


def test_draw_is_settled_gates_the_forever_cache():
    """The cache skip used to be `if cached slots: keep it`, on the theory that a released
    draw never changes. It does when it was captured BEFORE qualifying resolved: Palermo and
    Generali Open froze with `Qualifier N` slots, which no results row can match, so their
    finished cards shipped 32-of-32 alive and a modelFavorite of 'Qualifier 6'."""
    from tennis_model.data.draws_wiki import _draw_is_settled

    assert _draw_is_settled(["A", "B", None, "C"], draw_size=3)  # one legitimate bye
    # Early draw captures can encode unresolved qualifiers as nulls too. The published
    # entrant count distinguishes those holes from a real bye allocation.
    incomplete_28 = [f"P{i}" for i in range(27)] + [None] * 5
    assert not _draw_is_settled(incomplete_28, draw_size=28)
    assert not _draw_is_settled(["A", "Qualifier 6", "B", "C"])   # must re-fetch
    assert not _draw_is_settled(["A", "Lucky Loser", "B"])
    assert not _draw_is_settled([None, None])               # nothing real -> not a draw
    assert not _draw_is_settled([])
    assert not _draw_is_settled(None)
    print("ok test_draw_is_settled_gates_the_forever_cache")


def test_a_draw_outlives_the_discovery_window_that_found_it(tmp_path, monkeypatch):
    """The 256-slot Wimbledon crash, at its source.

    The cache was rebuilt each run from the events ESPN currently lists, so a draw was
    DELETED the moment ESPN stopped mentioning its event — while `build_tournaments` keeps
    projecting that event for weeks (a 40-day window). The draw vanished from under a live
    consumer, the field lost its anchor, fell back to a noisy results union and padded to an
    impossible 256-slot bracket, taking the whole board down. Twice: the 2026-07-11 fix made
    the cache authoritative, which only made the 07-27 deletion worse."""
    from tennis_model.data import draws_wiki as dw

    slots = [f"P{i}" for i in range(16)]
    (tmp_path / "wiki_draws.json").write_text(json.dumps({
        # a settled draw for an event ESPN no longer lists, still inside its retention window
        "Wimbledon": {"slots": slots, "seeds": {}, "bestOf": 5,
                      "start": "2026-06-29", "end": "2026-07-12"},
        # ...and one long past it
        "Ancient Open": {"slots": slots, "seeds": {}, "bestOf": 3,
                         "start": "2026-01-05", "end": "2026-01-11"},
    }), encoding="utf-8")
    # `download_wiki_draws` imports fetch_events / parse_event_meta / update_registry INSIDE
    # the function, so they must be patched on their OWN modules — patching them on
    # draws_wiki is a silent no-op that lets the test hit the real ESPN API (which is exactly
    # what happened the first time this was written: the run took 8.6s).
    from tennis_model.data import events as ev_mod
    from tennis_model.data import live as live_mod

    monkeypatch.setattr(dw, "live_dir", lambda tour: tmp_path)
    monkeypatch.setattr(dw, "_download_wiki_meta", lambda *a, **k: None)
    monkeypatch.setattr(live_mod, "fetch_events", lambda tour: [])
    monkeypatch.setattr(live_mod, "parse_event_meta", lambda evs: {})
    monkeypatch.setattr(ev_mod, "update_registry", lambda *a, **k: None)
    # ESPN now lists NOTHING — the old code would write an empty cache and lose both draws
    monkeypatch.setattr(dw, "_retention_cutoff",
                        lambda now=None: "2026-07-01")     # pin "today - 45d"
    dw.download_wiki_draws(["atp"])

    out = json.loads((tmp_path / "wiki_draws.json").read_text(encoding="utf-8"))
    assert "Wimbledon" in out, "a draw was deleted while its event was still projectable"
    assert out["Wimbledon"]["slots"] == slots
    assert "Ancient Open" not in out, "retention never expires"
    print("ok test_a_draw_outlives_the_discovery_window_that_found_it")


def test_registry_backfills_a_recent_draw_missing_from_the_cache(tmp_path, monkeypatch):
    """Carry-forward cannot recover bytes already lost. A recent registry event absent from
    the cache must be fetched even after it disappears from ESPN's current sweep."""
    from tennis_model.data import draws_wiki as dw
    from tennis_model.data import events as ev_mod
    from tennis_model.data import live as live_mod

    registry = {"events": {"188-2026": {
        "name": "Wimbledon", "names": ["The Championships", "Wimbledon"],
        "start": "2026-06-29", "end": "2026-07-12",
    }}}
    calls: list[str] = []

    def fetch(name, year, tour, meta):
        calls.append(name)
        if name == "Wimbledon":
            return {"slots": [f"P{i}" for i in range(128)], "seeds": {}, "bestOf": 5,
                    "start": meta["start"], "end": meta["end"],
                    "espnId": meta["espnId"]}
        return None

    monkeypatch.setattr(dw, "live_dir", lambda tour: tmp_path)
    monkeypatch.setattr(dw, "_download_wiki_meta", lambda *a, **k: None)
    monkeypatch.setattr(dw, "fetch_draw", fetch)
    monkeypatch.setattr(dw, "_registry_backfill_cutoff", lambda now=None: "2026-06-18",
                        raising=False)
    monkeypatch.setattr(live_mod, "fetch_events", lambda tour: [])
    monkeypatch.setattr(live_mod, "parse_event_meta", lambda events: {})
    monkeypatch.setattr(ev_mod, "update_registry", lambda *a, **k: registry)
    monkeypatch.setattr(ev_mod, "load_registry", lambda *a, **k: registry)

    dw.download_wiki_draws(["atp"])

    out = json.loads((tmp_path / "wiki_draws.json").read_text(encoding="utf-8"))
    assert calls == ["Wimbledon"]
    assert out["Wimbledon"]["espnId"] == "188-2026"
    assert len(out["Wimbledon"]["slots"]) == 128


def test_retention_keeps_facts_but_does_not_resurrect_a_rejected_tier(tmp_path, monkeypatch):
    """The two rules meet here and the drop must win. Retention exists so an event leaving
    ESPN's window cannot delete what we know about it — but a tier that is no longer sayable
    in this tour's vocabulary is not knowledge, it is the "WTA 125 on the ATP board" poison,
    and carrying it forward would undo the very drop that clears it."""
    from tennis_model.data import draws_wiki as dw

    (tmp_path / "wiki_surface.json").write_text(json.dumps({"Gone Open": "Clay"}),
                                                encoding="utf-8")
    (tmp_path / "wiki_category.json").write_text(json.dumps({
        "Gone Open": "ATP 250",        # valid for atp -> a fact, kept
        "Poisoned Open": "WTA 125",    # the other tour's tier -> dropped, not carried
    }), encoding="utf-8")
    monkeypatch.setattr(dw, "event_meta", lambda name, year, tour: (None, None))
    dw._download_wiki_meta("atp", tmp_path, {})            # ESPN lists neither event now

    surf = json.loads((tmp_path / "wiki_surface.json").read_text(encoding="utf-8"))
    cat = json.loads((tmp_path / "wiki_category.json").read_text(encoding="utf-8"))
    assert surf["Gone Open"] == "Clay"          # a surface never changes; keep it
    assert cat["Gone Open"] == "ATP 250"
    assert "Poisoned Open" not in cat, "retention resurrected a rejected cross-tour tier"
    print("ok test_retention_keeps_facts_but_does_not_resurrect_a_rejected_tier")


def test_get_retries_rate_limits_and_honours_retry_after(monkeypatch):
    """This module had NO backoff, alone among the repo's rate-limited fetchers. A single 429
    meant a missing surface, which falls through to the month-of-year guess — and on a
    500-tier event that now blocks the deploy."""
    import io
    import urllib.error

    from tennis_model.data import draws_wiki as dw

    slept, calls = [], {"n": 0}
    monkeypatch.setattr(dw.time, "sleep", lambda s: slept.append(s))

    def _flaky(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError("u", 429, "Too Many Requests",
                                         {"Retry-After": "7"}, None)
        return io.BytesIO(b'{"ok": true}')

    monkeypatch.setattr(dw.urllib.request, "urlopen",
                        lambda req, timeout=None: _CM(_flaky(req, timeout)))
    assert dw._get({"action": "query"}) == {"ok": True}
    assert calls["n"] == 2 and slept == [7.0], (calls, slept)

    # a permanent error is NOT retried — it is the caller's to handle on the first attempt
    calls["n"] = 0
    def _gone(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    monkeypatch.setattr(dw.urllib.request, "urlopen", _gone)
    with pytest.raises(urllib.error.HTTPError):
        dw._get({"action": "query"})
    assert calls["n"] == 1
    print("ok test_get_retries_rate_limits_and_honours_retry_after")


def test_wiki_meta_resolves_both_fields_in_one_pass(tmp_path, monkeypatch):
    """Surface and tier live on the SAME article; two separate sweeps re-resolved the title
    and each walked their own candidate loop — ~30 calls per unresolved event, hourly."""
    from tennis_model.data import draws_wiki as dw

    calls = []
    monkeypatch.setattr(dw, "event_meta",
                        lambda name, year, tour: calls.append(name) or ("Hard", "ATP 500"))
    dw._download_wiki_meta("atp", tmp_path, {"DC Open": {"start": "2026-07-27"}})
    assert calls == ["DC Open"], calls               # ONE resolution for both fields
    assert json.loads((tmp_path / "wiki_surface.json").read_text())["DC Open"] == "Hard"
    assert json.loads((tmp_path / "wiki_category.json").read_text())["DC Open"] == "ATP 500"
    # both cached -> no fetch at all next run
    calls.clear()
    dw._download_wiki_meta("atp", tmp_path, {"DC Open": {"start": "2026-07-27"}})
    assert calls == []


def test_wiki_meta_throttles_a_persistent_miss_but_not_an_imminent_event(tmp_path, monkeypatch):
    """A miss is never cached as a VALUE (the article may still be written), but re-asking
    hourly for an event weeks away is what made the fan-out expensive. Stamp the attempt and
    skip it for the rest of the day — unless the event starts within a couple of days."""
    from tennis_model.data import draws_wiki as dw

    calls = []
    monkeypatch.setattr(dw, "event_meta",
                        lambda name, year, tour: calls.append(name) or (None, None))
    far = {"Faraway Open": {"start": "2026-12-01"}}
    dw._download_wiki_meta("atp", tmp_path, far)
    assert calls == ["Faraway Open"]
    assert json.loads((tmp_path / "wiki_meta_misses.json").read_text())["Faraway Open"]
    calls.clear()
    dw._download_wiki_meta("atp", tmp_path, far)     # same day -> throttled
    assert calls == []
    # an event starting within the imminent window is retried every run regardless
    from datetime import UTC, datetime
    soon = {"Soon Open": {"start": datetime.now(UTC).strftime("%Y-%m-%d")}}
    dw._download_wiki_meta("atp", tmp_path, soon)
    calls.clear()
    dw._download_wiki_meta("atp", tmp_path, soon)
    assert calls == ["Soon Open"], calls
    print("ok test_wiki_meta_throttles_a_persistent_miss_but_not_an_imminent_event")


class _CM:
    """Minimal context-manager wrapper so a stubbed urlopen can stand in for the real one."""

    def __init__(self, fh):
        self._fh = fh

    def __enter__(self):
        return self._fh

    def __exit__(self, *a):
        return False


if __name__ == "__main__":
    test_draw_is_settled_gates_the_forever_cache()
    test_parse_bracket_orders_sections_handles_bye_and_bestof()
    test_parse_bracket_qualifiers_are_distinct_and_not_a_power_of_two_is_none()
    test_slot_name_strips_disambiguator_and_reads_byes()
    test_anchor_rejects_generic_only_names()
    test_rows_from_draws_skips_byes_and_qualifiers()
    test_rows_from_draws_only_prestart_events()
    print("\nALL PASSED")
