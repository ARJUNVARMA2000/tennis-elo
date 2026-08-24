"""Source-aware participant and draw-slot classification.

Providers use the same short tokens for different things.  A linked Wikipedia ``WC`` is
the display text for a real player, an official-PDF ``WC`` prefix is an entry code attached
to a real name, and an unlinked bare ``WC`` is an unresolved wildcard seat.  Likewise,
``None`` is a bye in an opening bracket but an unknown participant in a later-round shell or
ESPN athlete record.  This module is the one vocabulary boundary for those distinctions;
consumers should ask it whether a value names a player instead of growing local word sets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ParticipantKind(StrEnum):
    REAL_PLAYER = "real_player"
    QUALIFIER = "qualifier"
    LUCKY_LOSER = "lucky_loser"
    WILDCARD = "wildcard"
    ALTERNATE = "alternate"
    BYE = "bye"
    UNRESOLVED = "unresolved"


class ParticipantSource(StrEnum):
    CANONICAL = "canonical"
    ESPN = "espn"
    WIKIPEDIA = "wikipedia"
    OFFICIAL = "official"


class ParticipantContext(StrEnum):
    PARTICIPANT = "participant"
    ATHLETE = "athlete"
    OPENING_DRAW_SLOT = "opening_draw_slot"
    LATER_DRAW_SLOT = "later_draw_slot"
    LINKED_IDENTITY = "linked_identity"


_PLACEHOLDER_KINDS = frozenset({
    ParticipantKind.QUALIFIER,
    ParticipantKind.LUCKY_LOSER,
    ParticipantKind.WILDCARD,
    ParticipantKind.ALTERNATE,
    ParticipantKind.UNRESOLVED,
})
_NUMBER = r"(?:\s*(?:(?:\#|no\.?\s*)?\d+|\(\s*\d+\s*\)))?"
_COMBINED_RE = re.compile(
    rf"^(?:q|qualifier)/(?:ll|lucky\s+loser){_NUMBER}$",
)
_QUALIFIER_RE = re.compile(rf"^(?:q|qualifier|qualifying){_NUMBER}$")
_LUCKY_LOSER_RE = re.compile(rf"^(?:ll|lucky\s+loser){_NUMBER}$")
_WILDCARD_RE = re.compile(
    rf"^(?:(?:qualifier/)?(?:wc|wild\s*card)){_NUMBER}$"
)
_ALTERNATE_RE = re.compile(rf"^(?:(?:qualifier/)?(?:alt|alternate)){_NUMBER}$")
_BYE_RE = re.compile(rf"^bye{_NUMBER}$")
_UNRESOLVED_RE = re.compile(
    rf"^(?:qualifier/unresolved"
    rf"|(?:tbd|tba)(?:\s*(?:[-–—:/]\s*)?(?:opponent|player|winner))?"
    rf"|unknown|unresolved|pending|awaiting(?:\s+(?:winner|opponent))?){_NUMBER}$",
)
_PLACEHOLDER_LABEL = {
    ParticipantKind.QUALIFIER: "Qualifier",
    ParticipantKind.LUCKY_LOSER: "Lucky Loser",
    ParticipantKind.WILDCARD: "Wildcard",
    ParticipantKind.ALTERNATE: "Alternate",
    ParticipantKind.UNRESOLVED: "Unresolved",
}
_SERIALIZED_PLACEHOLDER_LABEL = {
    ParticipantKind.QUALIFIER: "Qualifier",
    ParticipantKind.LUCKY_LOSER: "Lucky Loser",
    # The compatibility envelope is intentionally semantically redundant. Pre-Round-3
    # Python and browser releases only understood strings beginning ``Qualifier`` or
    # ``Lucky Loser``; keeping that prefix makes a warmed cache safe after rollback while
    # current readers recover and display the role after the slash.
    ParticipantKind.WILDCARD: "Qualifier/Wildcard",
    ParticipantKind.ALTERNATE: "Qualifier/Alternate",
    ParticipantKind.UNRESOLVED: "Qualifier/Unresolved",
}


@dataclass(frozen=True, slots=True)
class ParticipantClassification:
    """Typed interpretation plus the provider context that made it valid."""

    kind: ParticipantKind
    source: ParticipantSource
    context: ParticipantContext
    raw: object
    normalized: str

    @property
    def is_real(self) -> bool:
        return self.kind is ParticipantKind.REAL_PLAYER

    @property
    def is_placeholder(self) -> bool:
        return self.kind in _PLACEHOLDER_KINDS

    @property
    def is_numbered_placeholder(self) -> bool:
        return self.is_placeholder and bool(
            re.search(r"(?:\d+|\(\s*\d+\s*\))$", self.normalized)
        )


def _normalized(value: object) -> str:
    if not isinstance(value, str):
        return ""
    # PDF extraction emits presentation ligatures, and provider dialects vary only in slash
    # spacing.  Normalize those before semantic classification, then retain ``raw`` for display.
    text = value.replace("ﬁ", "fi").replace("ﬂ", "fl").casefold().strip()
    text = " ".join(text.split())
    return re.sub(r"\s*/\s*", "/", text)


def classify_participant(
    value: object,
    *,
    source: ParticipantSource | str = ParticipantSource.CANONICAL,
    context: ParticipantContext | str = ParticipantContext.PARTICIPANT,
    provider_id: object = None,
) -> ParticipantClassification:
    """Classify one participant value under explicit provider/slot semantics.

    Unknown non-empty strings are real names: provider vocabularies are closed, while player
    names are not. A Wiki link target supplies the identity rather than its display text (for
    example ``[[Wang Xiyu|WC]]``), but a target that is itself only a reserved role word remains
    a placeholder because that distinction cannot survive the string-only artifact contract.
    ESPN athlete id ``0`` is the provider's pseudo-athlete sentinel.
    """
    source = ParticipantSource(source)
    context = ParticipantContext(context)
    normalized = _normalized(value)

    if source is ParticipantSource.ESPN and str(provider_id).strip() == "0":
        kind = ParticipantKind.UNRESOLVED
    elif value is None:
        kind = (ParticipantKind.BYE
                if context is ParticipantContext.OPENING_DRAW_SLOT
                else ParticipantKind.UNRESOLVED)
    elif not normalized:
        kind = ParticipantKind.UNRESOLVED
    elif _COMBINED_RE.fullmatch(normalized):
        # Q/LL says that the final entrant role is not known yet; choosing either named role
        # would discard provider information.
        kind = ParticipantKind.UNRESOLVED
    elif _QUALIFIER_RE.fullmatch(normalized):
        kind = ParticipantKind.QUALIFIER
    elif _LUCKY_LOSER_RE.fullmatch(normalized):
        kind = ParticipantKind.LUCKY_LOSER
    elif _WILDCARD_RE.fullmatch(normalized):
        kind = ParticipantKind.WILDCARD
    elif _ALTERNATE_RE.fullmatch(normalized):
        kind = ParticipantKind.ALTERNATE
    elif _BYE_RE.fullmatch(normalized):
        kind = ParticipantKind.BYE
    elif _UNRESOLVED_RE.fullmatch(normalized):
        kind = ParticipantKind.UNRESOLVED
    else:
        kind = ParticipantKind.REAL_PLAYER
    return ParticipantClassification(kind, source, context, value, normalized)


def is_real_participant(
    value: object,
    *,
    source: ParticipantSource | str = ParticipantSource.CANONICAL,
    context: ParticipantContext | str = ParticipantContext.PARTICIPANT,
    provider_id: object = None,
) -> bool:
    return classify_participant(
        value, source=source, context=context, provider_id=provider_id,
    ).is_real


def placeholder_label(kind: ParticipantKind | str) -> str:
    """Canonical display label for an unresolved entrant role."""
    kind = ParticipantKind(kind)
    if kind not in _PLACEHOLDER_LABEL:
        raise ValueError(f"{kind.value} is not an unresolved entrant kind")
    return _PLACEHOLDER_LABEL[kind]


def canonical_placeholder(kind: ParticipantKind | str, ordinal: int) -> str:
    """Unique, rollback-safe seat label retaining the provider's participant role."""
    kind = ParticipantKind(kind)
    if kind not in _SERIALIZED_PLACEHOLDER_LABEL:
        raise ValueError(f"{kind.value} is not an unresolved entrant kind")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("placeholder ordinal must be a positive integer")
    return f"{_SERIALIZED_PLACEHOLDER_LABEL[kind]} {ordinal}"


def draw_is_settled(
    slots,
    expected_entrants: object = None,
    *,
    require_expected: bool = False,
    source: ParticipantSource | str = ParticipantSource.CANONICAL,
) -> bool:
    """Whether an opening draw names distinct real entrants plus legitimate byes."""
    if not isinstance(slots, (list, tuple)) or not slots:
        return False
    classified = [classify_participant(
        value, source=source, context=ParticipantContext.OPENING_DRAW_SLOT,
    ) for value in slots]
    if any(item.kind not in {ParticipantKind.REAL_PLAYER, ParticipantKind.BYE}
           for item in classified):
        return False
    real = [item for item in classified if item.is_real]
    if not real:
        return False
    identities = [item.normalized for item in real]
    if len(set(identities)) != len(identities):
        return False

    if expected_entrants is None:
        return not require_expected
    try:
        expected = int(expected_entrants)
    except (TypeError, ValueError, OverflowError):
        return False
    if isinstance(expected_entrants, bool) or expected <= 0:
        return False
    return len(real) == expected


def draw_is_meaningful(
    values,
    total: object = None,
    *,
    source: ParticipantSource | str = ParticipantSource.CANONICAL,
    context: ParticipantContext | str = ParticipantContext.OPENING_DRAW_SLOT,
) -> bool:
    """Established shipping policy: at least half the advertised entrants are real."""
    if not isinstance(values, (list, tuple)) or not values:
        return False
    if total is None:
        denominator = len(values)
    else:
        try:
            denominator = int(total)
        except (TypeError, ValueError, OverflowError):
            return False
        if isinstance(total, bool):
            return False
    if denominator <= 0:
        return False
    real = sum(is_real_participant(value, source=source, context=context) for value in values)
    return real * 2 >= denominator


__all__ = [
    "ParticipantClassification",
    "ParticipantContext",
    "ParticipantKind",
    "ParticipantSource",
    "canonical_placeholder",
    "classify_participant",
    "draw_is_meaningful",
    "draw_is_settled",
    "is_real_participant",
    "placeholder_label",
]
