"""Source-neutral tournament-draw cache, migration, and overlay rows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data import draws


def test_legacy_wikipedia_cache_migrates_to_generic_provenance(tmp_path, monkeypatch):
    legacy = {"Old Sponsor Open": {
        "espnId": "7-2026", "slots": [f"P{i}" for i in range(28)] + [None] * 4,
        "seeds": {"P0": 1}, "bestOf": 3, "drawSize": 32,
        "title": "2026 Old Open – Singles", "url": "https://en.wikipedia.org/wiki/Old",
    }}
    (tmp_path / "wiki_draws.json").write_text(json.dumps(legacy), encoding="utf-8")
    monkeypatch.setattr(draws, "live_dir", lambda tour: tmp_path)
    migrated = draws.load_tournament_draws("atp")
    entry = migrated["7-2026"]
    assert entry["name"] == "Old Sponsor Open"
    assert entry["drawSize"] == 28 and entry["bracketSize"] == 32
    assert entry["source"] == "wikipedia"
    assert entry["sourceId"] == "2026 Old Open – Singles"
    assert entry["sourceUrl"].startswith("https://en.wikipedia.org/")


def test_official_cache_requires_strong_attachment_evidence():
    base = {"source": "atp", "evidencePlayers": 21, "evidenceFieldPlayers": 28,
            "start": "2026-08-01", "end": "2026-08-14",
            "sourceStart": "2026-08-01", "sourceEnd": "2026-08-13"}
    assert draws._official_evidence_is_valid(base, "atp")
    assert not draws._official_evidence_is_valid({**base, "evidencePlayers": 20}, "atp")
    assert not draws._official_evidence_is_valid({**base, "source": "wta"}, "atp")
    assert not draws._official_evidence_is_valid(
        {**base, "start": "2026-08-11", "end": "2026-08-24"}, "atp")


def test_settled_draw_requires_distinct_entrants():
    clean = {"slots": [f"Player {i}" for i in range(8)], "drawSize": 8}
    assert draws._draw_is_settled(clean)
    assert not draws._draw_is_settled(
        {"slots": ["Anna Bondar", "Anna Bondar", *[f"Player {i}" for i in range(6)]],
         "drawSize": 8})


def _official_draw(players, *, end="2099-08-23"):
    return {
        "name": "Cincinnati Open", "espnId": "718-2099", "source": "atp",
        "sourceId": "422", "sourceUrl": "https://example.test/422.pdf",
        "slots": list(players), "seeds": {}, "bestOf": 3,
        "drawSize": len(players), "bracketSize": len(players),
        "start": "2099-08-13", "end": end,
        "sourceStart": "2099-08-13", "sourceEnd": end,
        "evidencePlayers": len(players), "evidenceFieldPlayers": len(players),
    }


def test_active_settled_official_draw_refreshes_when_field_membership_changes(monkeypatch):
    """Cincinnati 2026 source 422 was revised after Griekspoor withdrew and the draw was
    re-seated. Geometry stayed settled, so field drift must invalidate immutability."""
    from tennis_model.data import draws_official

    stale = _official_draw(["Tallon Griekspoor", *[f"Player {i}" for i in range(1, 8)]])
    current_players = ["Replacement Player", *[f"Player {i}" for i in range(1, 8)]]
    current = _official_draw(current_players)
    monkeypatch.setattr(draws, "_field_evidence", lambda tour, name, meta: current_players)
    calls = []

    def fetch(tour, year, meta, registry, evidence):
        calls.append((tour, year, meta["espnId"], evidence))
        return current, []

    monkeypatch.setattr(draws_official, "fetch_official_draw", fetch)
    resolved, rejected = draws._resolve_one(
        "atp", "Cincinnati Open",
        {"espnId": "718-2099", "start": "2099-08-13", "end": "2099-08-23"},
        {"sourceIds": {"atp": "422"}}, stale)

    assert calls == [("atp", 2099, "718-2099", current_players)]
    assert resolved["slots"] == current_players and rejected == []


def test_active_settled_official_draw_skips_provider_when_field_is_unchanged(monkeypatch):
    from tennis_model.data import draws_official

    players = [f"Player {i}" for i in range(8)]
    cached = _official_draw(players)
    monkeypatch.setattr(draws, "_field_evidence", lambda tour, name, meta: players)
    monkeypatch.setattr(
        draws_official, "fetch_official_draw",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("provider called")))

    resolved, rejected = draws._resolve_one(
        "atp", "Cincinnati Open",
        {"espnId": "718-2099", "start": "2099-08-13", "end": "2099-08-23"},
        {"sourceIds": {"atp": "422"}}, cached)

    assert resolved["slots"] == players and rejected == []


def test_upcoming_rows_use_entry_name_and_stable_event_id():
    payload = {"424-2026": {
        "name": "Mifel Tennis Open", "espnId": "424-2026", "start": "2026-08-01",
        "slots": ["A", "B", "C", None, "Qualifier 1", "D", "E", "F"],
    }}
    rows = draws._rows_from_draws(payload, today="2026-07-30")
    assert {(row["playerA"], row["playerB"]) for row in rows} == {("A", "B"), ("E", "F")}
    assert all(row["tourney_name"] == "Mifel Tennis Open" for row in rows)
    assert all(row["espn_id"] == "424-2026" for row in rows)
