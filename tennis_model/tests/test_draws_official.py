"""Official ATP/WTA draw parsing and evidence selection, fully offline."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data import draws_official as official


def _text(title="Test Open", dates="27 July — 1 August 2026", names=None):
    names = names or [f"Player {i}" for i in range(1, 33)]
    lines = [title, "TEST CITY", dates, "Main Draw Singles"]
    for i, name in enumerate(names, 1):
        if name is None:
            lines.append(f" {i}       Bye")
        else:
            given, surname = name.split(" ", 1)
            seed = "1   " if i == 1 else ""
            lines.append(f" {i}   {seed}{surname.upper()}, {given}          USA")
    return "\n".join(lines)


def test_parse_official_text_separates_entrants_from_bracket_width():
    names = [f"Player {i}" for i in range(1, 29)] + [None] * 4
    draw = official.parse_official_text(_text(names=names))
    assert draw is not None
    assert draw["drawSize"] == 28 and draw["bracketSize"] == 32
    assert draw["slots"][28:] == [None, None, None, None]
    assert draw["seeds"] == {"Player 1": 1}


def test_parse_official_text_numbers_repeated_unresolved_qualifier_slots():
    """Toronto's early 96-player PDF names every open qualifying seat `Qualifier`.

    Those seats are distinct entrants. Leaving the provider label duplicated makes the
    projector's set-backed field collapse them into one player (96 entrants -> 81), which
    produces an internally inconsistent bracket and blocks the deployment integrity gate.
    """
    lines = ["National Bank Open", "2 August — 14 August 2026", "Main Draw Singles"]
    for i in range(1, 129):
        if i <= 80:
            lines.append(f" {i}   PLAYER {i}, Test          USA")
        elif i <= 96:
            lines.append(f" {i}   Q   Qualifier")
        else:
            lines.append(f" {i}       Bye")

    draw = official.parse_official_text("\n".join(lines))

    assert draw is not None
    assert draw["drawSize"] == 96 and draw["bracketSize"] == 128
    assert draw["slots"][80:96] == [f"Qualifier {i}" for i in range(1, 17)]
    assert len(set(slot for slot in draw["slots"] if slot is not None)) == 96


def test_clipped_surname_without_comma_is_a_slot_and_reconciles_to_live_field():
    assert official._slot_line(" 17       6   VAN DE ZANDSCHULP…           NED") == (
        17, "Van De Zandschulp…", 6)
    slots, seeds, shared = official._reconcile_slots(
        ["Van De Zandschulp…", "Francis… Cerundolo"],
        {"Van De Zandschulp…": 6},
        ["Botic Van De Zandschulp", "Francisco Cerundolo"],
    )
    assert slots == ["Botic Van De Zandschulp", "Francisco Cerundolo"]
    assert seeds == {"Botic Van De Zandschulp": 6} and shared == 2


def test_provider_date_parser_handles_both_dialects_and_implicit_cross_month():
    assert official.parse_date_span("Mifel\n27 July — 1 August 2026", 2026)[1].isoformat() == "2026-08-01"
    assert official.parse_date_span("VanOpen\nJuly 26-1 2026 | Hard", 2026)[1].isoformat() == "2026-08-01"
    assert official.parse_date_span("DC\nJuly 27- August 2, 2026", 2026)[0].isoformat() == "2026-07-27"


def test_candidate_selection_rejects_adjacent_event_with_only_a_few_shared_players(monkeypatch, tmp_path):
    field = [f"Player {i}" for i in range(1, 29)]
    wrong = [*field[:5], *[f"Wrong {i}" for i in range(6, 33)]]
    right = [*field, None, None, None, None]
    texts = {"wrong": _text("Adjacent Open", names=wrong),
             "right": _text("Target Open", names=right)}
    monkeypatch.setattr(official, "wta_candidate_ids", lambda *args: [
        {"id": "wrong"}, {"id": "right"},
    ])
    monkeypatch.setattr(official, "live_dir", lambda tour: tmp_path)
    monkeypatch.setattr(official, "_download", lambda url, cache: url.encode())
    monkeypatch.setattr(official, "extract_pdf_text",
                        lambda body: texts["wrong" if b"wrong" in body else "right"])
    draw, rejected = official.fetch_official_draw(
        "wta", 2026,
        {"name": "Target", "espnId": "1-2026", "start": "2026-07-25", "end": "2026-08-03"},
        {}, field,
    )
    assert draw and draw["sourceId"] == "right"
    assert draw["evidencePlayers"] == 28 and draw["evidenceFieldPlayers"] == 28
    assert any("matches 5/28" in reason for reason in rejected)


def test_mifel_reviewed_locator_is_los_cabos_provider_id():
    candidates = official.atp_candidate_ids(
        2026,
        {"name": "Mifel Tennis Open by Telcel Oppo", "espnId": "424-2026",
         "start": "2026-07-25", "end": "2026-08-02"},
        {},
    )
    assert candidates[0]["id"] == "7480"
