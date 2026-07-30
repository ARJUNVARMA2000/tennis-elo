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
    base = {"source": "atp", "evidencePlayers": 21, "evidenceFieldPlayers": 28}
    assert draws._official_evidence_is_valid(base, "atp")
    assert not draws._official_evidence_is_valid({**base, "evidencePlayers": 20}, "atp")
    assert not draws._official_evidence_is_valid({**base, "source": "wta"}, "atp")


def test_upcoming_rows_use_entry_name_and_stable_event_id():
    payload = {"424-2026": {
        "name": "Mifel Tennis Open", "espnId": "424-2026", "start": "2026-08-01",
        "slots": ["A", "B", "C", None, "Qualifier 1", "D", "E", "F"],
    }}
    rows = draws._rows_from_draws(payload, today="2026-07-30")
    assert {(row["playerA"], row["playerB"]) for row in rows} == {("A", "B"), ("E", "F")}
    assert all(row["tourney_name"] == "Mifel Tennis Open" for row in rows)
    assert all(row["espn_id"] == "424-2026" for row in rows)
