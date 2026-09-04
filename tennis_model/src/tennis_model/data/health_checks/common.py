"""Common invariants extracted without changing gate semantics."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from ...config import (
    PLAYER_ALIASES,
    SURFACE_MAP,
    TOURS,
)
from ..names import name_key
from ..participants import classify_participant, is_real_participant

FINDING_SCHEMA = "health-finding-v1"

_FINDING_CODE_RE = re.compile(r"^(source|output|cross)(?:\.[a-z][a-z0-9_]*){2,}$")

_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)

_FINDING_SEVERITIES = frozenset({"error", "warning", "info"})

_FINDING_SCOPES = frozenset({"source", "output", "cross"})

@dataclass(frozen=True, slots=True)
class HealthFinding:
    """Stable machine identity plus mutable human evidence for one health invariant.

    Fingerprints deliberately exclude severity, evidence, and prose: an age moving from 9d
    to 10d, a wording cleanup, or warning-to-error promotion is one continuing incident.
    ``revision`` captures those mutable fields so reporters may update that same incident.
    """

    code: str
    severity: Literal["error", "warning", "info"]
    scope: Literal["source", "output", "cross"]
    tour: str | None
    entity: str | None
    evidence: dict
    message: str

    def __post_init__(self) -> None:
        if not _FINDING_CODE_RE.fullmatch(self.code):
            raise ValueError(f"invalid health finding code {self.code!r}")
        if self.severity not in _FINDING_SEVERITIES:
            raise ValueError(f"invalid health finding severity {self.severity!r}")
        if self.scope not in _FINDING_SCOPES or not self.code.startswith(f"{self.scope}."):
            raise ValueError("health finding scope/code mismatch")
        if self.tour not in (*TOURS, None):
            raise ValueError(f"invalid health finding tour {self.tour!r}")
        if self.scope == "cross" and self.tour is not None:
            raise ValueError("cross-tour finding cannot name one tour")
        if self.scope != "cross" and self.tour is None:
            raise ValueError("source/output finding must name a tour")
        if self.entity is not None and (not isinstance(self.entity, str) or not self.entity.strip()):
            raise ValueError("health finding entity must be a non-empty string or null")
        if not isinstance(self.evidence, dict) or not isinstance(self.message, str) or not self.message:
            raise ValueError("health finding evidence/message is malformed")
        try:
            json.dumps(self.evidence, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("health finding evidence is not strict JSON") from exc

    @property
    def fingerprint(self) -> str:
        identity = [FINDING_SCHEMA, self.code, self.scope, self.tour, self.entity]
        raw = json.dumps(identity, separators=(",", ":"), ensure_ascii=False).encode()
        return f"hf1:{hashlib.sha256(raw).hexdigest()}"

    @property
    def revision(self) -> str:
        content = [self.severity, self.evidence, self.message]
        raw = json.dumps(content, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
        return f"hr1:{hashlib.sha256(raw).hexdigest()}"

    def as_dict(self) -> dict:
        return {
            "schema": FINDING_SCHEMA,
            "fingerprint": self.fingerprint,
            "revision": self.revision,
            "code": self.code,
            "severity": self.severity,
            "scope": self.scope,
            "tour": self.tour,
            "entity": self.entity,
            "evidence": self.evidence,
            "message": self.message,
        }

class _FindingCollector:
    def __init__(self, scope: str, tour: str | None):
        self.scope = scope
        self.tour = tour
        self.findings: list[HealthFinding] = []

def _add_finding(out, code: str, message: str, *, severity: str = "error",
                 entity: str | None = None, evidence: dict | None = None,
                 scope: str | None = None, tour: str | None = None) -> None:
    """Emit typed findings in production while preserving helper tests using plain lists."""
    if isinstance(out, _FindingCollector):
        out.findings.append(HealthFinding(
            code=code,
            severity=severity,
            scope=scope or out.scope,
            tour=tour if tour is not None else out.tour,
            entity=entity,
            evidence=evidence or {},
            message=message,
        ))
    else:
        out.append(message)

def _finding_messages(findings: list[HealthFinding], *, actionable_only: bool = True) -> list[str]:
    return [finding.message for finding in findings
            if not actionable_only or finding.severity != "info"]

_EVIDENCE_KEYS = (
    "surfaceElo", "serveReturn", "form", "rest", "home", "h2h", "style",
)

_WATCH_WEIGHTS = {
    "closeness": 30, "quality": 25, "styleContrast": 15,
    "stakes": 15, "titleLeverage": 15,
}

def _is_real_name(x: object) -> bool:
    """True if the shared provider-aware vocabulary says this names an actual player."""
    return is_real_participant(x)

_STATUSES = {"live", "upcoming", "completed"}

_DRAW_STATES = {"real", "partial", "seeded", "final", "unavailable"}

_REACH_ORDER = ("R128", "R64", "R32", "R16", "QF", "SF", "F", "Champion")

# Suffix `_tiered` stamps on a board-quality problem below the 500 tier (see GATE_BLOCKING_TIERS).
_BELOW_TIER = " [below the 500 tier — advisory]"

# Canonical shipped surfaces — SURFACE_MAP's VALUES (Carpet folds to Hard), so this can
# never drift from what `results.clean` is able to produce.
_CANONICAL_SURFACES = frozenset(SURFACE_MAP.values())

# Tier-aware severity for BOARD-QUALITY problems (a wrong surface, a placeholder projection,
# a card that never flipped live). The marquee events are the ones that must never ship wrong;
# the long tail warns instead, so one obscure 125 cannot freeze the whole site the way a
# single ATP fixtures row froze it for 16 hours on 2026-07-27. Structural problems (corrupt
# JSON, aliveCount > drawSize, a non-canonical surface VALUE) ignore tier and always block.
# Olympics and Davis/BJK Cup are deliberately NOT here: both are marquee but have atypical
# team formats, making them the likeliest spurious blockers, and they are rare enough that
# advisory plus the post-deploy sentinel is adequate.
GATE_BLOCKING_TIERS = frozenset({
    "Grand Slam", "Tour Finals", "Masters 1000", "WTA 1000", "ATP 500", "WTA 500",
})

def _tier_blocks(level: object) -> bool:
    """True when an event's tier is senior enough that board-quality problems block."""
    return str(level) in GATE_BLOCKING_TIERS

def _tiered(problem: str, level: object, *, force: bool = False) -> str:
    """Stamp a board-quality problem advisory unless the event is 500-or-above.

    The suffix remains for legacy prose consumers and explains the decision in logs; typed
    emitters pair it with ``_tier_severity`` and the production gate reads that severity.
    Coverage-only cards set ``force`` because their unresolved tier cannot be evidence that
    a co-located defect is unimportant."""
    return problem if force or _tier_blocks(level) else problem + _BELOW_TIER

def _tier_severity(level: object, *, force: bool = False) -> str:
    """Typed counterpart to the legacy explanatory suffix added by ``_tiered``."""
    return "error" if force or _tier_blocks(level) else "warning"

def _is_prob(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0.0 <= float(x) <= 1.0

def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)

def _pow2(n) -> bool:
    return isinstance(n, int) and n >= 2 and (n & (n - 1)) == 0

# Standard bye-carrying draw sizes: 28 (32-bracket, 4 byes — most ATP/WTA 250/500s),
# 24 (32-bracket, 8 byes), 48/56 (64-bracket Masters/500s), 96 (128-bracket IW/Miami/
# Madrid/Rome). The wiki bracket parser guarantees the SLOTS are a power of two
# (draws_wiki._parse_bracket); drawSize counts entrants, so byes make it one of these.
_BYE_DRAW_SIZES = frozenset({24, 28, 48, 56, 96})

def _real_draw_size_ok(n) -> bool:
    return _pow2(n) or n in _BYE_DRAW_SIZES

def _age_days(iso, now: pd.Timestamp):
    ts = pd.to_datetime(iso, utc=True, errors="coerce") if iso else pd.NaT
    if pd.isna(ts):
        return None
    now_utc = now if now.tzinfo else now.tz_localize("UTC")
    return int((now_utc - ts).days)

def _flag_placeholders(out: list, tour: str, where: str, names, *, entity: str,
                       allow_numbered: bool = False) -> None:
    bad: set[str] = set()
    for name in names:
        if not isinstance(name, str):
            continue
        participant = classify_participant(name)
        if participant.is_real:
            continue
        if allow_numbered and participant.is_numbered_placeholder:
            continue
        bad.add(name)
    ordered = sorted(bad)
    if ordered:
        _add_finding(
            out, "output.participant.placeholder_name",
            f"{tour}: {where} contains placeholder name(s) {ordered}",
            severity="error", entity=entity,
            evidence={"where": where, "names": ordered})

def _square_matrix(value: object, n: int) -> bool:
    return (isinstance(value, list) and len(value) == n
            and all(isinstance(row, list) and len(row) == n for row in value))

def _finite_between(value: object, low: float, high: float) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and low <= float(value) <= high)

def _norm_name(name: str) -> str:
    return " ".join(str(name).split()).casefold()

def _player_identity_key(name: object) -> str:
    """Name key after the same explicit identity aliases used by result ingestion."""
    key = name_key(name)
    return name_key(PLAYER_ALIASES.get(key, name))

def _identity_value(value: object) -> str:
    """Return a provider identity scalar without manufacturing IDs from nulls."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"nan", "none", "null"} else text

def _event_entity(event: dict) -> str:
    """Stable event identity for finding fingerprints; display names are evidence only."""
    espn_id = next((value for value in (
        _identity_value(event.get("espnId")),
        _identity_value(event.get("espn_id")),
    ) if value), "")
    if espn_id:
        return f"espn:{espn_id}"
    coverage_key = _identity_value(event.get("coverageKey"))
    if coverage_key:
        if coverage_key.casefold().startswith("espn:"):
            return f"espn:{coverage_key.split(':', 1)[1]}"
        return f"coverage:{coverage_key}"
    draw_source_id = _identity_value(event.get("drawSourceId"))
    if draw_source_id:
        source = _identity_value(event.get("drawSource")) or "provider"
        return f"draw:{source}:{draw_source_id}"
    start = _identity_value(event.get("start"))
    end = _identity_value(event.get("end"))
    if start or end:
        return f"event-window:{start}:{end}"
    return "event:unidentified"

def _event_provider_entity(event: dict) -> str | None:
    """Exact event identity usable across tournament and bracket artifacts.

    ``drawSourceId`` identifies the source draw and deliberately exists only in the
    bracket payload, so it remains a useful finding identity but is not a cross-artifact
    event key. ESPN identity can arrive directly or through an ``espn:`` coverage key.
    """
    espn_id = next((value for value in (
        _identity_value(event.get("espnId")),
        _identity_value(event.get("espn_id")),
    ) if value), "")
    if espn_id:
        return f"espn:{espn_id}"
    coverage_key = _identity_value(event.get("coverageKey"))
    if coverage_key.casefold().startswith("espn:"):
        return _event_entity({"coverageKey": coverage_key})
    return None

def _event_stable_entity(event: dict) -> str | None:
    """Non-window identity that can conclusively match when both artifacts carry it."""
    entity = _event_entity(event)
    if entity == "event:unidentified" or entity.startswith("event-window:"):
        return None
    return entity

def _event_real_player_keys(event: dict) -> set[str]:
    """Canonical real-player evidence carried by either event artifact."""
    players = {
        row.get("name")
        for row in (event.get("projection") or [])
        if isinstance(row, dict)
    }
    players |= {event.get("champion"), event.get("runnerUp")}
    for rounds_key in ("rounds", "bracket"):
        for rnd in event.get(rounds_key) or []:
            if not isinstance(rnd, dict):
                continue
            for match in rnd.get("matches") or []:
                if isinstance(match, dict):
                    players |= {match.get("a"), match.get("b")}
    return {_player_identity_key(player) for player in players if _is_real_name(player)}

def _event_evidence_matches(bracket: dict, tournament: dict) -> bool:
    """Evidence join when at least one event artifact lacks an ESPN identity."""
    from ...data.draws_official import official_dates_match

    if not official_dates_match(
            bracket.get("start"), bracket.get("end") or bracket.get("start"),
            tournament.get("start"), tournament.get("end") or tournament.get("start")):
        return False
    return len(_event_real_player_keys(bracket) & _event_real_player_keys(tournament)) >= 2

def _remembered_bracket_event_entities(tournaments: object,
                                        prev: dict | None) -> dict[str, str]:
    """Keep a bracket-loss baseline until its event leaves the active board.

    A missing bracket must remain missing on the second run rather than disappearing from
    the baseline and falsely recovering. Legacy display-name state is bridged for rollout;
    all newly persisted identity is provider/event based.
    """
    cards = tournaments if isinstance(tournaments, list) else []
    active = {
        _event_entity(card): card for card in cards
        if isinstance(card, dict) and card.get("name")
        and card.get("status") in ("live", "upcoming")
    }
    previous = prev or {}
    raw_entities = previous.get("bracket_event_entities") or {}
    prior_entities = set(raw_entities) if isinstance(raw_entities, (dict, list)) else set()
    legacy_names = set(previous.get("bracket_events") or [])
    remembered: dict[str, str] = {}
    for entity, card in active.items():
        if card.get("hasBracket"):
            remembered[entity] = str(card["name"])
        elif entity in prior_entities:
            remembered[entity] = (str(raw_entities.get(entity))
                                  if isinstance(raw_entities, dict)
                                  and raw_entities.get(entity) else str(card["name"]))
        elif _norm_name(card.get("name")) in legacy_names:
            remembered[entity] = str(card["name"])
    return remembered

def _match_entity(match: dict, *, event_entity: str | None = None,
                  player_a: object = None, player_b: object = None,
                  fallback: str = "unidentified") -> str:
    """Prefer a match ID; otherwise bind an unordered canonical pair to its event."""
    match_id = next((value for value in (
        _identity_value(match.get("matchId")),
        _identity_value(match.get("match_id")),
        _identity_value(match.get("id")),
    ) if value), "")
    if match_id:
        return f"match:{match_id}"
    base = event_entity or _event_entity(match)
    if base == "event:unidentified":
        date = _identity_value(match.get("date"))
        if date:
            base = f"event-date:{date}"
    pair = sorted(filter(None, (
        _player_identity_key(player_a),
        _player_identity_key(player_b),
    )))
    if pair:
        return f"{base}#players:{':'.join(pair)}"
    return f"{base}#{fallback}"
