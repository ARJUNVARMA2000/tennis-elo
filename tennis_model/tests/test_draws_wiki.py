"""Wikipedia draw parsing — fully offline (fixture wikitext, no network).

Pins the pieces that make "download the whole draw at release" correct: the ORDERED
bracket is stitched from the `-Compact-` section templates (late-round summary brackets
ignored), seed byes become (player, None), qualifier/undetermined slots are kept distinct,
and best-of comes from the Tennis3/Tennis5 template family. Also covers title resolution's
distinctive-anchor guard (so "... Open ... singles" can't resolve to the wrong Open) and
the first-round rows the schedule board / forecast log consume.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mwparserfromhell

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
    assert _anchor("US Open") is None                   # all-generic -> no anchor (fall through)
    print("ok test_anchor_rejects_generic_only_names")


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


if __name__ == "__main__":
    test_parse_bracket_orders_sections_handles_bye_and_bestof()
    test_parse_bracket_qualifiers_are_distinct_and_not_a_power_of_two_is_none()
    test_slot_name_strips_disambiguator_and_reads_byes()
    test_anchor_rejects_generic_only_names()
    test_rows_from_draws_skips_byes_and_qualifiers()
    test_rows_from_draws_only_prestart_events()
    print("\nALL PASSED")
