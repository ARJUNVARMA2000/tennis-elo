"""Exact bracket evidence for reconciling provider round labels.

The scoreboard's round label is useful only until a released ordered bracket can identify
the same matchup.  This module keeps that join deliberately narrow: one stable ESPN event
id plus one unordered canonical pair must identify exactly one bracket round.  Anything
missing, unmatched, placeholder-shaped, or ambiguous returns ``None`` so callers preserve
the provider value and the independent output gate can still reject a disagreement.
"""

from __future__ import annotations

import json

from ..config import PLAYER_ALIASES, output_dir
from ..sim.bracket import is_real
from .names import name_key

BracketRoundIndex = dict[tuple[str, frozenset[str]], list[str]]


def player_identity_key(name: object) -> str:
    """Canonical identity key after the explicit aliases used by result ingestion."""
    key = name_key(name)
    return name_key(PLAYER_ALIASES.get(key, name))


def _event_id(value: object) -> str | None:
    """A stable ESPN id is a non-blank string; pandas missing values fail closed."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _player_pair(player_a: object, player_b: object) -> frozenset[str] | None:
    if not (is_real(player_a) and is_real(player_b)):
        return None
    pair = frozenset((player_identity_key(player_a), player_identity_key(player_b)))
    return pair if len(pair) == 2 and all(pair) else None


def build_bracket_round_index(brackets: object) -> BracketRoundIndex:
    """Index released bracket matchups by exact event id and canonical player pair."""
    index: BracketRoundIndex = {}
    if not isinstance(brackets, list):
        return index
    for event in brackets:
        if not isinstance(event, dict):
            continue
        event_id = _event_id(event.get("espnId"))
        if event_id is None:
            continue
        rounds = event.get("rounds")
        if not isinstance(rounds, list):
            continue
        for round_row in rounds:
            if not isinstance(round_row, dict):
                continue
            round_name = round_row.get("round")
            if not isinstance(round_name, str) or not round_name.strip():
                continue
            matches = round_row.get("matches")
            if not isinstance(matches, list):
                continue
            for match in matches:
                if not isinstance(match, dict):
                    continue
                pair = _player_pair(match.get("a"), match.get("b"))
                if pair is not None:
                    # Preserve occurrences, not just distinct labels. The same pair listed
                    # twice in one round is still ambiguous evidence and must not rewrite a
                    # provider row merely because both copies happen to carry the same text.
                    index.setdefault((event_id, pair), []).append(round_name.strip())
    return index


def load_bracket_round_index(tour: str) -> BracketRoundIndex:
    """Load the just-exported bracket artifact; unreadable state yields no evidence."""
    try:
        brackets = json.loads(
            (output_dir(tour) / "brackets.json").read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    return build_bracket_round_index(brackets)


def unique_bracket_round(index: BracketRoundIndex, event_id: object,
                         player_a: object, player_b: object) -> str | None:
    """Return the sole bracket round for an exact matchup, otherwise fail closed."""
    stable_id = _event_id(event_id)
    pair = _player_pair(player_a, player_b)
    if stable_id is None or pair is None:
        return None
    rounds = index.get((stable_id, pair))
    if not rounds or len(rounds) != 1:
        return None
    return next(iter(rounds))
