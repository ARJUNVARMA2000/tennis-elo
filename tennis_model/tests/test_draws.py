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


def _wikipedia_draw(source_id: str, source_url: str) -> dict:
    return {
        "name": "US Open", "espnId": "189-2026", "source": "wikipedia",
        "sourceId": source_id, "sourceUrl": source_url,
        "slots": [f"Player {i}" for i in range(8)], "seeds": {}, "bestOf": 3,
        "drawSize": 8, "bracketSize": 8,
        "start": "2026-08-25", "end": "9999-09-13",
    }


def test_active_settled_wikipedia_draw_is_quarantined_when_identity_drifted(monkeypatch):
    """A complete Wimbledon field was cached under US Open's ESPN id. Settled geometry
    must not bypass active event identity, and the missing real article must yield no draw."""
    from tennis_model.data import draws_official, draws_wiki

    wrong = _wikipedia_draw(
        "2026 Wimbledon Championships – Women's singles",
        "https://en.wikipedia.org/wiki/2026_Wimbledon_Championships_%E2%80%93_Women%27s_singles",
    )
    monkeypatch.setattr(draws, "_field_evidence", lambda *args: [])
    monkeypatch.setattr(draws_official, "fetch_official_draw", lambda *args: (None, []))
    monkeypatch.setattr(draws_wiki, "fetch_draw", lambda *args: None)

    resolved, rejected = draws._resolve_one(
        "wta", "US Open",
        {"espnId": "189-2026", "start": "2026-08-25", "end": "9999-09-13"},
        {}, wrong)

    assert resolved is None
    assert any("cache identity does not match" in reason for reason in rejected)


def test_active_settled_wikipedia_draw_reuses_only_exact_current_identity(monkeypatch):
    from tennis_model.data import draws_official, draws_wiki

    title = "2026 US Open – Women's singles"
    correct = _wikipedia_draw(
        title,
        "https://en.wikipedia.org/wiki/2026_US_Open_%E2%80%93_Women%27s_singles",
    )
    monkeypatch.setattr(draws, "_field_evidence", lambda *args: [])
    monkeypatch.setattr(draws_official, "fetch_official_draw", lambda *args: (None, []))
    monkeypatch.setattr(
        draws_wiki, "fetch_draw",
        lambda *args: (_ for _ in ()).throw(AssertionError("settled exact cache refetched")))

    resolved, _rejected = draws._resolve_one(
        "wta", "US Open",
        {"espnId": "189-2026", "start": "2026-08-25", "end": "9999-09-13"},
        {}, correct)

    assert resolved["sourceId"] == title


def test_duplicate_draw_source_attachments_are_quarantined():
    duplicate = {
        "source": "wikipedia", "sourceId": "2026 Wimbledon – Women's singles",
        "sourceUrl": "https://en.wikipedia.org/wiki/2026_Wimbledon_Women",
        "slots": [f"P{i}" for i in range(8)],
    }
    payload = {
        "188-2026": {**duplicate, "espnId": "188-2026", "name": "Wimbledon"},
        "189-2026": {**duplicate, "espnId": "189-2026", "name": "US Open"},
        "718-2026": {**duplicate, "espnId": "718-2026", "name": "Cincinnati",
                     "sourceId": "2026 Cincinnati – Women's singles",
                     "sourceUrl": "https://en.wikipedia.org/wiki/2026_Cincinnati_Women"},
    }

    clean, findings = draws._quarantine_duplicate_sources(payload)
    assert set(clean) == {"718-2026"}
    assert len(findings) == 1
    assert "188-2026" in findings[0] and "189-2026" in findings[0]
    assert draws.duplicate_draw_source_incidents(payload)[0][0] == (
        "wikipedia:2026 wimbledon – women's singles"
    )


def test_rejected_current_cache_entry_is_not_restored_by_retention(tmp_path, monkeypatch):
    """Rejecting US Open in `_resolve_one` was insufficient: the later retention loop added
    its bad cached row back because it was recent. Current-but-rejected ids must stay absent."""
    from tennis_model.data import draws_wiki, live

    wrong = _wikipedia_draw(
        "2026 Wimbledon Championships – Women's singles",
        "https://en.wikipedia.org/wiki/2026_Wimbledon_Women",
    )
    old = {
        **wrong, "name": "Wimbledon", "espnId": "188-2026",
        "start": "2026-06-22", "end": "9999-07-13",
    }
    (tmp_path / draws.CACHE_FILE).write_text(json.dumps({
        "188-2026": old,
        "189-2026": wrong,
    }), encoding="utf-8")
    meta = {"US Open": {
        "espnId": "189-2026", "start": "2026-08-25", "end": "9999-09-13",
    }}

    monkeypatch.setattr(draws, "live_dir", lambda _tour: tmp_path)
    monkeypatch.setattr(draws, "update_registry", lambda *_args: {"events": {}})
    monkeypatch.setattr(draws, "load_registry", lambda *_args: {"events": {}})
    monkeypatch.setattr(draws, "_resolve_one", lambda *_args: (None, ["rejected"]))
    monkeypatch.setattr(live, "parse_event_meta", lambda _events: meta)
    monkeypatch.setattr(draws_wiki, "_download_wiki_meta", lambda *_args: None)

    draws.download_tournament_draws(["wta"], events_by_tour={"wta": []})

    persisted = json.loads((tmp_path / draws.CACHE_FILE).read_text(encoding="utf-8"))
    assert set(persisted) == {"188-2026"}


def test_duplicate_only_cache_is_overwritten_with_empty_quarantine(tmp_path, monkeypatch):
    from tennis_model.data import draws_wiki, live

    duplicate = {
        "source": "wikipedia", "sourceId": "Wrong draw",
        "sourceUrl": "https://en.wikipedia.org/wiki/Wrong_draw",
        "slots": [f"P{i}" for i in range(8)], "drawSize": 8,
        "start": "2026-08-01", "end": "9999-09-01",
    }
    (tmp_path / draws.CACHE_FILE).write_text(json.dumps({
        "1-2026": {**duplicate, "espnId": "1-2026", "name": "One"},
        "2-2026": {**duplicate, "espnId": "2-2026", "name": "Two"},
    }), encoding="utf-8")

    monkeypatch.setattr(draws, "live_dir", lambda _tour: tmp_path)
    monkeypatch.setattr(draws, "update_registry", lambda *_args: {"events": {}})
    monkeypatch.setattr(draws, "load_registry", lambda *_args: {"events": {}})
    monkeypatch.setattr(live, "parse_event_meta", lambda _events: {})
    monkeypatch.setattr(draws_wiki, "_download_wiki_meta", lambda *_args: None)

    draws.download_tournament_draws(["wta"], events_by_tour={"wta": []})

    assert json.loads((tmp_path / draws.CACHE_FILE).read_text(encoding="utf-8")) == {}


def test_upcoming_rows_use_entry_name_and_stable_event_id():
    payload = {"424-2026": {
        "name": "Mifel Tennis Open", "espnId": "424-2026", "start": "2026-08-01",
        "slots": ["A", "B", "C", None, "Qualifier 1", "D", "E", "F"],
    }}
    rows = draws._rows_from_draws(payload, today="2026-07-30")
    assert {(row["playerA"], row["playerB"]) for row in rows} == {("A", "B"), ("E", "F")}
    assert all(row["tourney_name"] == "Mifel Tennis Open" for row in rows)
    assert all(row["espn_id"] == "424-2026" for row in rows)
