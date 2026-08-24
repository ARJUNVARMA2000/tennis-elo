"""Canonical participant/slot vocabulary across every live draw provider."""

from __future__ import annotations

import sys
from pathlib import Path

import mwparserfromhell
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.participants import (
    ParticipantContext,
    ParticipantKind,
    ParticipantSource,
    canonical_placeholder,
    classify_participant,
    draw_is_meaningful,
    draw_is_settled,
)


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        ("Jannik Sinner", ParticipantKind.REAL_PLAYER),
        ("Qualifier", ParticipantKind.QUALIFIER),
        (" qualifier  #12 ", ParticipantKind.QUALIFIER),
        ("Qualifier (12)", ParticipantKind.QUALIFIER),
        ("Q 4", ParticipantKind.QUALIFIER),
        ("Lucky Loser", ParticipantKind.LUCKY_LOSER),
        ("LL 3", ParticipantKind.LUCKY_LOSER),
        ("Wildcard", ParticipantKind.WILDCARD),
        ("Wild Card 2", ParticipantKind.WILDCARD),
        ("WC", ParticipantKind.WILDCARD),
        ("Qualifier/Wildcard 2", ParticipantKind.WILDCARD),
        ("Alternate", ParticipantKind.ALTERNATE),
        ("ALT 5", ParticipantKind.ALTERNATE),
        ("Qualifier / Alternate 5", ParticipantKind.ALTERNATE),
        ("Bye", ParticipantKind.BYE),
        ("TBD", ParticipantKind.UNRESOLVED),
        ("TBA 2", ParticipantKind.UNRESOLVED),
        ("TBD opponent", ParticipantKind.UNRESOLVED),
        ("TBA - player", ParticipantKind.UNRESOLVED),
        ("Qualifier/Unresolved 3", ParticipantKind.UNRESOLVED),
        ("Qualifier / Lucky Loser", ParticipantKind.UNRESOLVED),
        ("Qualiﬁer/LL", ParticipantKind.UNRESOLVED),
        ("", ParticipantKind.UNRESOLVED),
        (None, ParticipantKind.UNRESOLVED),
    ],
)
def test_canonical_vocabulary_including_numbered_and_null_slots(value, kind):
    classified = classify_participant(value)
    assert classified.kind is kind
    assert classified.is_real is (kind is ParticipantKind.REAL_PLAYER)


def test_provider_context_preserves_identity_and_null_semantics():
    # Wikipedia uses link targets as identity: a WC display pointing to a real target is real.
    linked_player = classify_participant(
        "Wang Xiyu",
        source=ParticipantSource.WIKIPEDIA,
        context=ParticipantContext.LINKED_IDENTITY,
    )
    linked_reserved = classify_participant(
        "Wildcard",
        source=ParticipantSource.WIKIPEDIA,
        context=ParticipantContext.LINKED_IDENTITY,
    )
    assert linked_player.kind is ParticipantKind.REAL_PLAYER
    assert linked_reserved.kind is ParticipantKind.WILDCARD

    # Null means a real bye only in the opening draw. ESPN/mid-draw nulls are unresolved.
    assert classify_participant(
        None, context=ParticipantContext.OPENING_DRAW_SLOT,
    ).kind is ParticipantKind.BYE
    assert classify_participant(
        None, context=ParticipantContext.LATER_DRAW_SLOT,
    ).kind is ParticipantKind.UNRESOLVED
    assert classify_participant(
        None, source=ParticipantSource.ESPN,
        context=ParticipantContext.ATHLETE,
    ).kind is ParticipantKind.UNRESOLVED

    # ESPN uses athlete id 0 for a pseudo-participant even if display text looks name-like.
    assert classify_participant(
        "Jane Doe",
        source=ParticipantSource.ESPN,
        context=ParticipantContext.ATHLETE,
        provider_id=0,
    ).kind is ParticipantKind.UNRESOLVED
    assert classify_participant(
        "Jane Doe",
        source=ParticipantSource.ESPN,
        context=ParticipantContext.ATHLETE,
        provider_id="123",
    ).kind is ParticipantKind.REAL_PLAYER


def test_placeholder_labels_preserve_provider_meaning_and_unique_seats():
    assert classify_participant("Qualifier 2").is_numbered_placeholder
    assert classify_participant("Qualifier (12)").is_numbered_placeholder
    assert not classify_participant("Qualifier").is_numbered_placeholder
    assert canonical_placeholder(ParticipantKind.QUALIFIER, 2) == "Qualifier 2"
    assert canonical_placeholder(ParticipantKind.LUCKY_LOSER, 2) == "Lucky Loser 2"
    assert canonical_placeholder(ParticipantKind.WILDCARD, 2) == "Qualifier/Wildcard 2"
    assert canonical_placeholder(ParticipantKind.ALTERNATE, 2) == "Qualifier/Alternate 2"
    assert canonical_placeholder(ParticipantKind.UNRESOLVED, 2) == "Qualifier/Unresolved 2"
    with pytest.raises(ValueError):
        canonical_placeholder(ParticipantKind.REAL_PLAYER, 1)
    with pytest.raises(ValueError):
        canonical_placeholder(ParticipantKind.BYE, 1)


def test_serialized_placeholders_are_safe_under_the_pre_round_3_python_policy():
    """A warmed cache must remain non-real if production rolls back one release."""
    legacy_prefixes = ("qualifier", "lucky loser", "bye", "tbd", "tba")

    def legacy_is_real(value):
        return (isinstance(value, str) and value.strip() != ""
                and not value.strip().casefold().startswith(legacy_prefixes))

    for kind in ParticipantKind:
        if kind in {ParticipantKind.REAL_PLAYER, ParticipantKind.BYE}:
            continue
        serialized = canonical_placeholder(kind, 3)
        assert not legacy_is_real(serialized), (kind, serialized)
        assert classify_participant(serialized).kind is kind


@pytest.mark.parametrize(
    "placeholder",
    ["Qualifier 1", "Lucky Loser 1", "Wildcard 1", "Alternate 1", "Unresolved 1", "TBD"],
)
def test_settled_policy_rejects_every_placeholder_kind(placeholder):
    assert not draw_is_settled(["A", "B", placeholder, None], expected_entrants=3)


def test_settled_policy_distinguishes_byes_null_holes_and_duplicate_people():
    assert draw_is_settled(["A", "B", "C", None], expected_entrants=3)
    assert not draw_is_settled(["A", "B", None, None], expected_entrants=3)
    assert not draw_is_settled(["A", "A", "B", None], expected_entrants=3)
    assert draw_is_settled(["A", "B", "C", None])
    assert not draw_is_settled(["A", "B", "C", None], require_expected=True)
    assert not draw_is_settled([], expected_entrants=0)


def test_meaningful_policy_uses_the_same_real_participant_boundary():
    mixed = ["A", "B", "Qualifier 1", "Lucky Loser 1"]
    assert draw_is_meaningful(mixed)  # exactly half is the established shipping boundary
    assert not draw_is_meaningful(["A", "Wildcard 1", "Alternate 1", "Unresolved 1"])
    assert draw_is_meaningful(["A", "B", None, None], total=4)
    assert not draw_is_meaningful(["A", "B", None, None], total=5)
    assert not draw_is_meaningful([], total=0)


def test_cross_provider_classification_retains_real_named_wildcards():
    from tennis_model.data.draws_official import parse_official_text
    from tennis_model.data.draws_wiki import _slot_name

    linked = mwparserfromhell.parse("[[Wang Xiyu|WC]]")
    assert _slot_name(linked) == "Wang Xiyu"

    lines = ["Test Open", "August 1 — August 7 2026", "Main Draw Singles"]
    for index in range(1, 9):
        marker = "WC   " if index == 1 else ""
        lines.append(f" {index}   {marker}PLAYER {index}, Test          USA")
    draw = parse_official_text("\n".join(lines))
    assert draw is not None
    assert draw["slots"][0] == "Test Player 1"
    assert classify_participant(
        draw["slots"][0], source=ParticipantSource.OFFICIAL,
        context=ParticipantContext.OPENING_DRAW_SLOT,
    ).kind is ParticipantKind.REAL_PLAYER
