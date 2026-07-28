"""Stable event identity (data/events.py) — fully offline, no network.

Pins the invariant that ends the largest bug family in this repo's history: display names
are for display, joins use espnId, and the name history is the alias table. The DC Open
rename on 2026-07-27 (ESPN dropped "Citi" mid-tournament, same id 888-2026) is replayed
directly, because that rename orphaned the cached draw and cost the event its bracket.

Runnable directly (`python tests/test_event_registry.py`) or under pytest.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data import events as ev

NOW = datetime(2026, 7, 28, tzinfo=UTC)


def _sandbox(fn):
    """Run fn(tmpdir) with live_dir redirected per tour into a temp area."""
    orig = ev.live_dir
    try:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            ev.live_dir = lambda tour: root / tour
            return fn(root)
    finally:
        ev.live_dir = orig


def _meta(name, eid, start="2026-07-25", end="2026-08-03"):
    return {name: {"espnId": eid, "start": start, "end": end}}


def test_rename_appends_to_the_alias_table():
    """The DC Open sequence. ESPN dropped "Citi" from the shortName mid-event while the id
    stayed 888-2026; every cache keyed on the name was orphaned. The registry must end with
    ONE event that answers to BOTH names."""
    def body(_root):
        ev.update_registry("atp", _meta("Mubadala Citi DC Open", "888-2026"), NOW)
        reg = ev.update_registry("atp", _meta("Mubadala DC Open", "888-2026"),
                                 NOW + timedelta(hours=2))
        assert list(reg["events"]) == ["888-2026"], reg["events"]
        e = reg["events"]["888-2026"]
        assert e["names"] == ["Mubadala Citi DC Open", "Mubadala DC Open"]
        assert e["name"] == "Mubadala DC Open"          # current title moves...
        r = ev.EventResolver(reg)
        assert r.id_of("Mubadala Citi DC Open") == "888-2026"   # ...the old one still resolves
        assert r.id_of("Mubadala DC Open") == "888-2026"
        # firstSeen is immutable, lastSeen advances
        assert e["firstSeen"] < e["lastSeen"]
    _sandbox(body)
    print("ok test_rename_appends_to_the_alias_table")


def test_dates_refresh_and_ids_without_a_name_are_ignored():
    def body(_root):
        ev.update_registry("atp", _meta("X Open", "1-2026", "2026-07-01", "2026-07-07"), NOW)
        reg = ev.update_registry("atp", _meta("X Open", "1-2026", "2026-07-02", "2026-07-09"),
                                 NOW)
        e = reg["events"]["1-2026"]
        assert (e["start"], e["end"]) == ("2026-07-02", "2026-07-09")   # ESPN corrects dates
        # an event with no id can't be keyed on; it is skipped, not crashed on
        reg = ev.update_registry("atp", {"No Id Open": {"espnId": None}}, NOW)
        assert list(reg["events"]) == ["1-2026"]
    _sandbox(body)
    print("ok test_dates_refresh_and_ids_without_a_name_are_ignored")


def test_prune_never_orphans_a_cached_draw():
    """The anti-Wimbledon rule. A cached draw outliving the entry that names it is exactly
    how the field lost its anchor and padded to an impossible 256-slot bracket, twice."""
    def body(root):
        stale = (NOW - timedelta(days=500)).strftime("%Y-%m-%dT%H:%M:%SZ")
        d = root / "atp"
        d.mkdir(parents=True, exist_ok=True)
        (d / "events.json").write_text(json.dumps({"version": 1, "events": {
            "11-2025": {"name": "Old Unreferenced", "names": ["Old Unreferenced"],
                        "firstSeen": stale, "lastSeen": stale},
            "22-2025": {"name": "Old But Cached", "names": ["Old But Cached"],
                        "firstSeen": stale, "lastSeen": stale},
        }}), encoding="utf-8")
        # a wiki draw still keys on 22-2025 -> it must survive however stale it looks
        (d / "wiki_draws.json").write_text(json.dumps({"22-2025": {"slots": ["A", "B"]}}),
                                           encoding="utf-8")
        reg = ev.update_registry("atp", _meta("New Open", "33-2026"), NOW)
        assert "22-2025" in reg["events"], "a referenced entry was pruned"
        assert "11-2025" not in reg["events"], "an unreferenced stale entry survived"
        assert "33-2026" in reg["events"]
        # an id referenced from INSIDE a cache value counts too (wiki_draws carries espnId)
        (d / "wiki_draws.json").write_text(
            json.dumps({"Some Name": {"slots": ["A"], "espnId": "11-2025"}}), encoding="utf-8")
        (d / "events.json").write_text(json.dumps({"version": 1, "events": {
            "11-2025": {"name": "Old", "names": ["Old"], "firstSeen": stale, "lastSeen": stale},
        }}), encoding="utf-8")
        reg = ev.update_registry("atp", {}, NOW)
        assert "11-2025" in reg["events"]
    _sandbox(body)
    print("ok test_prune_never_orphans_a_cached_draw")


def test_registries_are_per_tour_and_the_same_id_never_crosses():
    """A combined event is ONE id with two draws (888-2026 is the DC Open on both tours).
    Each file describes that tour's half; they must not bleed into each other."""
    def body(_root):
        ev.update_registry("atp", _meta("Mubadala DC Open", "888-2026"), NOW)
        ev.update_registry("wta", _meta("Mubadala Citi DC Open", "888-2026"), NOW)
        atp, wta = ev.load_registry("atp"), ev.load_registry("wta")
        assert atp["events"]["888-2026"]["name"] == "Mubadala DC Open"
        assert wta["events"]["888-2026"]["name"] == "Mubadala Citi DC Open"
        assert atp["events"]["888-2026"]["names"] == ["Mubadala DC Open"]
    _sandbox(body)
    print("ok test_registries_are_per_tour_and_the_same_id_never_crosses")


def test_missing_and_corrupt_registries_degrade_quietly():
    def body(root):
        assert ev.load_registry("atp") == {"version": 1, "events": {}}
        d = root / "atp"
        d.mkdir(parents=True, exist_ok=True)
        (d / "events.json").write_text("{ not json", encoding="utf-8")
        assert ev.load_registry("atp")["events"] == {}
        (d / "events.json").write_text(json.dumps(["a list, not a registry"]), encoding="utf-8")
        assert ev.load_registry("atp")["events"] == {}
        # ...and a corrupt file is simply rebuilt by the next sweep
        reg = ev.update_registry("atp", _meta("X Open", "1-2026"), NOW)
        assert list(reg["events"]) == ["1-2026"]
    _sandbox(body)
    print("ok test_missing_and_corrupt_registries_degrade_quietly")


def test_resolver_tiers_and_refusal_to_guess():
    """A wrong join is worse than no join — it merges two real tournaments into one card."""
    reg = {"events": {
        "1-2026": {"name": "Bad Homburg Open powered by Solarwatt",
                   "names": ["Bad Homburg", "Bad Homburg Open powered by Solarwatt"]},
        "2-2026": {"name": "Eastbourne Open", "names": ["Eastbourne Open"]},
    }}
    r = ev.EventResolver(reg)
    assert r.id_of("Bad Homburg") == "1-2026"                       # exact, over history
    assert r.id_of("  bad   homburg  ") == "1-2026"                 # normalised
    assert r.id_of("Bad Homburg Open") == "1-2026"                  # containment
    assert r.id_of("Nowhere Classic") is None
    assert r.id_of("Cup") is None and r.id_of("") is None           # too short to be evidence
    # ambiguity refuses rather than guessing
    amb = ev.EventResolver({"events": {
        "1-2026": {"name": "Open Sud de France", "names": ["Open Sud de France"]},
        "2-2026": {"name": "Open Sud Classic", "names": ["Open Sud Classic"]},
    }})
    assert amb.id_of("Open Sud") is None
    # `extra` lets a cache-only name resolve before the registry has seen it
    r2 = ev.EventResolver(reg, extra=[("Citi DC Open", "9-2026")])
    assert r2.id_of("Citi DC Open") == "9-2026"
    assert r.names_of("1-2026") == ["Bad Homburg", "Bad Homburg Open powered by Solarwatt"]
    assert r.current_name("1-2026") == "Bad Homburg Open powered by Solarwatt"
    assert r.entry("nope") is None
    print("ok test_resolver_tiers_and_refusal_to_guess")


def test_an_orphaned_cache_key_is_recovered_by_its_embedded_id_not_by_name():
    """The real DC recovery path, and why `extra` is load-bearing rather than decorative.

    ESPN renamed "Mubadala Citi DC Open" -> "Mubadala DC Open" — a word inserted in the
    MIDDLE, so neither containment direction bridges it, and the registry only ever saw the
    new name. `id_of` correctly refuses (guessing here would merge two tournaments). What
    recovers the orphaned cache entry is the espnId `draws_wiki` stamps INSIDE it: seed the
    resolver from the cache and the old key resolves. Verified against the real cached draw.
    """
    reg = {"events": {"888-2026": {"name": "Mubadala DC Open",
                                   "names": ["Mubadala DC Open"]}}}
    assert ev.EventResolver(reg).id_of("Mubadala Citi DC Open") is None
    cache = {"Mubadala Citi DC Open": {"slots": ["A", "B"], "espnId": "888-2026"}}
    seeded = ev.EventResolver(reg, extra=[(k, v["espnId"]) for k, v in cache.items()])
    assert seeded.id_of("Mubadala Citi DC Open") == "888-2026"
    # and the current name still resolves through the registry itself
    assert seeded.id_of("Mubadala DC Open") == "888-2026"
    print("ok test_an_orphaned_cache_key_is_recovered_by_its_embedded_id_not_by_name")


def test_is_event_id_tells_keys_apart():
    """Both cache formats coexist during the migration, so every reader must classify a key
    per entry rather than assuming a file is all one shape."""
    assert ev.is_event_id("888-2026") and ev.is_event_id("1-2025")
    assert not ev.is_event_id("Mubadala DC Open")
    assert not ev.is_event_id("Wimbledon") and not ev.is_event_id("")
    assert not ev.is_event_id("888")
    print("ok test_is_event_id_tells_keys_apart")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\n{len(fns)} passed")
