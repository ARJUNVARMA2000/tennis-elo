"""Pure Tennis Abstract-vs-DEUCE tournament forecast scoring.

The fetcher and append-only ledger deliberately live elsewhere.  This module accepts a
normalized external snapshot, in-memory forecast-log records, and in-memory outcomes and
returns a deterministic public report.  It performs no I/O.

The comparison is intentionally narrow:

* external match probabilities come only from adjacent 1-based draw positions and the
  snapshot's first displayed reach stage;
* names match only through the repository's exact canonical/alias key;
* events match only through ``espnId`` (never their mutable display names);
* a DEUCE quote is the latest append-only ``match``/``match_snapshot`` observation at or
  before the external capture;
* a match is eligible only when an exact start timestamp proves the capture preceded play,
  or when the caller supplies its exact canonical match id in ``eligible_match_ids``.

Match probabilities are rounded to the external display resolution (0.001) before both
systems are scored.  Log loss clips those displayed probabilities to 0.0005..0.9995, so a
published rounded zero remains a strong, finite claim.  Paired deltas are always
Tennis-Abstract-minus-DEUCE: positive values favour DEUCE.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from statistics import fmean, stdev

from ..data.bracket_rounds import player_identity_key
from . import track

REPORT_SCHEMA = "tennis-abstract-benchmark-v1"
DISPLAY_DIGITS = 3
LOG_LOSS_MIN = 0.0005
PAIR_MASS_TOLERANCE = 0.002

_STAGE_ORDER = ("R128", "R64", "R32", "R16", "QF", "SF", "F", "W")
_STAGE_INDEX = {stage: index for index, stage in enumerate(_STAGE_ORDER)}
_STAGE_ALIASES = {
    "CHAMPION": "W",
    "WINNER": "W",
    "TITLE": "W",
    "W": "W",
}


def _clean_id(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value if value and value.lower() not in {"nan", "none", "null"} else None


def _stage(value: object) -> str | None:
    raw = re.sub(r"[^A-Z0-9]", "", str(value or "").upper())
    raw = _STAGE_ALIASES.get(raw, raw)
    return raw if raw in _STAGE_INDEX else None


def _match_round(first_stage: object) -> str | None:
    stage = _stage(first_stage)
    if stage is None:
        return None
    index = _STAGE_INDEX[stage]
    return _STAGE_ORDER[index - 1] if index > 0 else None


def _finite_probability(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        return None
    return probability


def _display_probability(value: object) -> float | None:
    probability = _finite_probability(value)
    if probability is None:
        return None
    quantum = Decimal(1).scaleb(-DISPLAY_DIGITS)
    return float(Decimal(str(probability)).quantize(quantum, rounding=ROUND_HALF_UP))


def _parse_instant(value: object) -> datetime | None:
    """Parse an exact timezone-aware instant; date-only/naive values fail closed."""
    if isinstance(value, datetime):
        instant = value
    elif isinstance(value, str) and "T" in value:
        try:
            instant = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if instant.tzinfo is None or instant.utcoffset() is None:
        return None
    return instant.astimezone(UTC)


def _records(value: object) -> list[dict]:
    """Accept records, a DataFrame-like value, or ``None`` without mutating callers."""
    if value is None:
        return []
    if hasattr(value, "to_dict") and not isinstance(value, Mapping):
        try:
            return [dict(row) for row in value.to_dict("records")]
        except (TypeError, ValueError):
            return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [dict(row) for row in value if isinstance(row, Mapping)]
    return []


def _season(record: Mapping, fallback: object = None) -> int | None:
    for value in (record.get("season"), record.get("date"), record.get("as_of"), fallback):
        text = str(value or "")
        if len(text) >= 4 and text[:4].isdigit():
            return int(text[:4])
    return None


def _canonical_match_id(
    *, espn_id: str, season: int, round_name: str, player_a: object, player_b: object,
) -> str | None:
    pair = sorted((player_identity_key(player_a), player_identity_key(player_b)))
    if len(set(pair)) != 2 or not all(pair):
        return None
    return f"{track.MATCH_ID_VERSION}|espn:{espn_id}|{season}|{round_name}|{pair[0]}|{pair[1]}"


def _match_id_parts(value: object) -> tuple[str, int, str] | None:
    if not isinstance(value, str):
        return None
    parts = value.split("|", 5)
    if len(parts) != 6 or parts[0] != track.MATCH_ID_VERSION:
        return None
    if not parts[1].startswith("espn:") or not parts[1][5:]:
        return None
    if not parts[2].isdigit():
        return None
    round_name = _stage(parts[3])
    if round_name is None or round_name == "W":
        return None
    return parts[1][5:], int(parts[2]), round_name


def _snapshot_meta(snapshot: Mapping) -> tuple[str | None, int | None, str | None, datetime | None]:
    source = snapshot.get("source")
    source = source if isinstance(source, Mapping) else {}
    espn_id = _clean_id(snapshot.get("espnId", snapshot.get("espn_id")))
    season = _season(snapshot)
    captured_text = source.get("capturedAt", snapshot.get("capturedAt"))
    return espn_id, season, captured_text if isinstance(captured_text, str) else None, _parse_instant(captured_text)


def _snapshot_pairs(snapshot: Mapping) -> tuple[list[dict], list[dict]]:
    """Resolve valid adjacent draw pairs plus match-level structural exclusions."""
    rounds = snapshot.get("rounds")
    players = snapshot.get("players")
    first_stage = _stage(rounds[0]) if isinstance(rounds, list) and rounds else None
    round_name = _match_round(first_stage)
    players = players if isinstance(players, list) else []
    total = max(1, (len(players) + 1) // 2) if players else 0

    positioned: list[tuple[int, dict]] = []
    for raw in players:
        if not isinstance(raw, Mapping):
            return [], [{"status": "excluded", "reason": "draw_position_invalid", "round": round_name}
                        for _ in range(total)]
        position = raw.get("drawPosition")
        if isinstance(position, bool) or not isinstance(position, int) or position < 1:
            return [], [{"status": "excluded", "reason": "draw_position_invalid", "round": round_name}
                        for _ in range(total)]
        positioned.append((position, dict(raw)))
    if len({position for position, _ in positioned}) != len(positioned):
        return [], [{"status": "excluded", "reason": "draw_position_invalid", "round": round_name}
                    for _ in range(total)]
    if first_stage is None or round_name is None:
        return [], [{"status": "excluded", "reason": "first_stage_invalid", "round": None}
                    for _ in range(total)]

    canonical_counts = Counter(player_identity_key(player.get("name")) for _, player in positioned)
    groups: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for position, player in positioned:
        groups[position if position % 2 else position - 1].append((position, player))

    pairs: list[dict] = []
    errors: list[dict] = []
    for start in sorted(groups):
        group = sorted(groups[start], key=lambda item: item[0])
        if [position for position, _ in group] != [start, start + 1] or start % 2 == 0:
            errors.append({"status": "excluded", "reason": "adjacent_pair_missing", "round": round_name})
            continue
        (position_a, player_a), (position_b, player_b) = group
        key_a = player_identity_key(player_a.get("name"))
        key_b = player_identity_key(player_b.get("name"))
        if (not key_a or not key_b or key_a == key_b
                or canonical_counts[key_a] != 1 or canonical_counts[key_b] != 1):
            errors.append({
                "status": "excluded", "reason": "player_identity_ambiguous", "round": round_name,
                "drawPositions": [position_a, position_b],
            })
            continue
        probabilities_a = player_a.get("probabilities")
        probabilities_b = player_b.get("probabilities")
        p_a = _finite_probability(
            probabilities_a.get(first_stage) if isinstance(probabilities_a, Mapping) else None)
        p_b = _finite_probability(
            probabilities_b.get(first_stage) if isinstance(probabilities_b, Mapping) else None)
        reason = None
        if p_a is None or p_b is None:
            reason = "external_probability_malformed"
        elif abs((p_a + p_b) - 1.0) > PAIR_MASS_TOLERANCE + 1e-12:
            reason = "external_pair_mass_invalid"
        pair = {
            "round": round_name,
            "firstStage": first_stage,
            "drawPositions": [position_a, position_b],
            "playerA": player_a.get("name"),
            "playerB": player_b.get("name"),
            "keyA": key_a,
            "keyB": key_b,
            "pair": frozenset((key_a, key_b)),
            "pTennisAbstract": _display_probability(p_a),
        }
        if reason:
            errors.append({**pair, "status": "excluded", "reason": reason})
        else:
            pairs.append(pair)
    return pairs, errors


def snapshot_match_ids(snapshot: Mapping) -> list[str]:
    """Return canonical IDs callers may use for explicit pre-start eligibility proof."""
    espn_id, season, _, _ = _snapshot_meta(snapshot)
    if espn_id is None or season is None:
        return []
    pairs, _ = _snapshot_pairs(snapshot)
    ids = [
        _canonical_match_id(
            espn_id=espn_id, season=season, round_name=pair["round"],
            player_a=pair["playerA"], player_b=pair["playerB"],
        )
        for pair in pairs
    ]
    return sorted(match_id for match_id in ids if match_id is not None)


def _pure_track_bridges(records: list[dict]) -> dict[str, str]:
    """Use append-only track bridges without consulting the current bracket on disk."""
    legacy = track._legacy_match_bridges(records)
    persisted = track._persisted_round_bridge_candidates(records)
    candidates: dict[str, set[str]] = defaultdict(set)
    for source, target in legacy.items():
        candidates[source].add(target)
    for source, targets in persisted.items():
        candidates[source].update(targets)
    return {
        source: next(iter(targets))
        for source, targets in candidates.items()
        if len(targets) == 1
    }


def _record_identity(record: Mapping, bridges: Mapping[str, str]) -> tuple[str | None, int | None, str | None]:
    try:
        effective = track._effective_match_id(dict(record), dict(bridges))
    except (KeyError, TypeError, ValueError):
        effective = str(record.get("match_id") or "")
    parts = _match_id_parts(effective)
    if parts is not None:
        return parts
    event_id = _clean_id(record.get("espnId", record.get("espn_id")))
    round_name = _stage(record.get("round"))
    return event_id, _season(record), round_name


def _record_pair(record: Mapping) -> frozenset[str] | None:
    if record.get("winner_name") is not None or record.get("loser_name") is not None:
        names = (record.get("winner_name"), record.get("loser_name"))
    elif record.get("winner") is not None or record.get("loser") is not None:
        names = (record.get("winner"), record.get("loser"))
    else:
        names = (record.get("playerA", record.get("player_a")),
                 record.get("playerB", record.get("player_b")))
    pair = frozenset(player_identity_key(name) for name in names)
    return pair if len(pair) == 2 and all(pair) else None


def _select_deuce_quote(
    pair: Mapping, records: list[dict], *, espn_id: str, season: int,
    captured_at: datetime, bridges: Mapping[str, str],
) -> tuple[dict | None, str | None]:
    exact: list[tuple[datetime, int, dict]] = []
    malformed_time = False
    shared_player = False
    for index, record in enumerate(records):
        if record.get("type") not in {"match", "match_snapshot"}:
            continue
        event, record_season, round_name = _record_identity(record, bridges)
        if (event, record_season, round_name) != (espn_id, season, pair["round"]):
            continue
        record_pair = _record_pair(record)
        if record_pair != pair["pair"]:
            if record_pair and record_pair & pair["pair"]:
                shared_player = True
            continue
        instant = _parse_instant(record.get("as_of"))
        if instant is None:
            malformed_time = True
            continue
        if instant <= captured_at:
            exact.append((instant, index, record))
    if malformed_time:
        return None, "deuce_quote_timestamp_malformed"
    if not exact:
        return None, "deuce_pair_mismatch" if shared_player else "deuce_quote_missing"
    _, _, quote = max(exact, key=lambda row: (row[0], row[1]))
    probability = _finite_probability(quote.get("p"))
    if probability is None:
        return None, "deuce_probability_malformed"
    key_a = player_identity_key(quote.get("playerA"))
    key_b = player_identity_key(quote.get("playerB"))
    if pair["keyA"] == key_a:
        oriented = probability
    elif pair["keyA"] == key_b:
        oriented = 1.0 - probability
    else:
        return None, "deuce_pair_mismatch"
    return {"p": _display_probability(oriented), "asOf": quote.get("as_of")}, None


def _result_type(record: Mapping) -> str:
    raw = str(record.get("resultType", record.get("result_type", "")) or "").lower()
    score = str(record.get("score") or "").strip().lower()
    if (
        bool(record.get("walkover"))
        or raw in {"walkover", "w/o", "wo"}
        or score in {"walkover", "w/o", "wo"}
    ):
        return "walkover"
    if (
        bool(record.get("retired"))
        or raw in {"retired", "retirement", "ret", "abd"}
        or re.search(r"(?:^|\s)(?:ret|retired|abd)(?:$|\s)", score) is not None
    ):
        return "retirement"
    return "completed"


def _winner(record: Mapping) -> object:
    return record.get("winner_name", record.get("winner", record.get("actualWinner")))


def _is_completed(record: Mapping) -> bool:
    status = str(record.get("status", record.get("match_status", "")) or "").lower()
    if status in {"scheduled", "pending", "upcoming", "in_progress", "live"}:
        return False
    if not player_identity_key(_winner(record)):
        return False
    if _result_type(record) in {"walkover", "retirement"}:
        return True
    return record.get("completed") is not False


def _result_candidates(
    pair: Mapping, results: list[dict], *, espn_id: str, season: int,
) -> tuple[list[dict], bool]:
    exact: list[dict] = []
    shared = False
    for record in results:
        event, record_season, round_name = _record_identity(record, {})
        if (event, record_season, round_name) != (espn_id, season, pair["round"]):
            continue
        record_pair = _record_pair(record)
        if record_pair == pair["pair"]:
            exact.append(record)
        elif record_pair and record_pair & pair["pair"]:
            shared = True
    return exact, shared


def _eligible_ids(value: object) -> set[str]:
    if isinstance(value, Mapping):
        return {str(key) for key, allowed in value.items() if allowed}
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        return {str(item) for item in value}
    return set()


def _timing_eligibility(
    *, match_id: str, candidates: list[dict], captured_at: datetime,
    eligible_ids: set[str],
) -> tuple[bool, str | None]:
    start_values = [
        record.get("startedAt", record.get("startTime", record.get("start_time")))
        for record in candidates
    ]
    parsed = {_parse_instant(value) for value in start_values if value not in (None, "")}
    parsed.discard(None)
    if len(parsed) > 1:
        return False, "start_time_ambiguous"
    if len(parsed) == 1:
        start = next(iter(parsed))
        if captured_at >= start:
            return False, "capture_not_prestart"
        return True, None
    if match_id in eligible_ids:
        return True, None
    if any(value not in (None, "") for value in start_values):
        return False, "start_time_malformed"
    return False, "prestart_timing_unproven"


def _resolved_outcome(candidates: list[dict]) -> tuple[dict | None, str | None]:
    completed = [record for record in candidates if _is_completed(record)]
    if not completed:
        return None, None
    signatures = {
        (player_identity_key(_winner(record)), _result_type(record)) for record in completed
    }
    if len(signatures) != 1:
        return None, "result_ambiguous"
    return completed[-1], None


def evaluate_matches(
    snapshot: Mapping,
    forecast_records: object,
    results: object,
    *,
    eligible_match_ids: object = None,
    include_retirements: bool = False,
) -> list[dict]:
    """Return deterministic match rows used by the compact public adapter."""
    records = _records(forecast_records)
    result_rows = _records(results)
    espn_id, season, _, captured_at = _snapshot_meta(snapshot)
    pairs, errors = _snapshot_pairs(snapshot)
    if espn_id is None or season is None:
        reason = "event_identity_missing"
        return [{**row, "reason": reason} for row in (errors or [
            {"status": "excluded", "round": pair.get("round")} for pair in pairs
        ])]
    if captured_at is None:
        reason = "capture_timestamp_malformed"
        return errors + [{**pair, "status": "excluded", "reason": reason} for pair in pairs]

    bridges = _pure_track_bridges(records)
    allowed_ids = _eligible_ids(eligible_match_ids)
    out = list(errors)
    for pair in pairs:
        match_id = _canonical_match_id(
            espn_id=espn_id, season=season, round_name=pair["round"],
            player_a=pair["playerA"], player_b=pair["playerB"],
        )
        row = {**pair, "matchId": match_id}
        candidates, shared_result = _result_candidates(
            pair, result_rows, espn_id=espn_id, season=season)
        eligible, reason = _timing_eligibility(
            match_id=str(match_id), candidates=candidates, captured_at=captured_at,
            eligible_ids=allowed_ids,
        )
        if not eligible:
            out.append({**row, "status": "excluded", "reason": reason})
            continue
        quote, reason = _select_deuce_quote(
            pair, records, espn_id=espn_id, season=season,
            captured_at=captured_at, bridges=bridges,
        )
        if quote is None:
            out.append({**row, "status": "excluded", "reason": reason})
            continue
        outcome, reason = _resolved_outcome(candidates)
        if reason:
            out.append({**row, "status": "excluded", "reason": reason, "pDeuce": quote["p"]})
            continue
        if outcome is None:
            if shared_result:
                out.append({**row, "status": "excluded", "reason": "result_pair_mismatch",
                            "pDeuce": quote["p"]})
            else:
                out.append({**row, "status": "pending", "pDeuce": quote["p"],
                            "deuceAsOf": quote["asOf"]})
            continue
        kind = _result_type(outcome)
        winner_key = player_identity_key(_winner(outcome))
        settled = {
            "winner": _winner(outcome),
            "aWon": winner_key == pair["keyA"],
            "resultType": kind,
            "deuceAsOf": quote["asOf"],
        }
        if kind == "walkover":
            out.append({
                **row, "status": "excluded", "reason": "walkover",
                "pDeuce": quote["p"], **settled,
            })
            continue
        if kind == "retirement" and not include_retirements:
            out.append({
                **row, "status": "excluded", "reason": "retirement",
                "pDeuce": quote["p"], **settled,
            })
            continue
        if winner_key not in pair["pair"]:
            out.append({**row, "status": "excluded", "reason": "result_pair_mismatch",
                        "pDeuce": quote["p"]})
            continue
        out.append({
            **row,
            "status": "graded",
            "pDeuce": quote["p"],
            "deuceAsOf": quote["asOf"],
            "winner": _winner(outcome),
            "aWon": winner_key == pair["keyA"],
            "resultType": kind,
        })
    return sorted(
        out,
        key=lambda row: (
            row.get("drawPositions", [10**9])[0],
            str(row.get("matchId") or ""),
            str(row.get("reason") or ""),
        ),
    )


def _binary_loss(probability: float, outcome: bool) -> tuple[float, float]:
    clipped = min(1.0 - LOG_LOSS_MIN, max(LOG_LOSS_MIN, probability))
    probability_of_outcome = clipped if outcome else 1.0 - clipped
    return -math.log(probability_of_outcome), (probability - float(outcome)) ** 2


def _score_matches(rows: list[dict]) -> dict:
    graded = [row for row in rows if row.get("status") == "graded"]
    losses: dict[str, list[tuple[float, float]]] = {"deuce": [], "tennisAbstract": []}
    delta_ll: list[float] = []
    delta_brier: list[float] = []
    for row in graded:
        outcome = bool(row["aWon"])
        deuce = _binary_loss(float(row["pDeuce"]), outcome)
        external = _binary_loss(float(row["pTennisAbstract"]), outcome)
        losses["deuce"].append(deuce)
        losses["tennisAbstract"].append(external)
        delta_ll.append(external[0] - deuce[0])
        delta_brier.append(external[1] - deuce[1])

    def absolute(label: str) -> dict:
        values = losses[label]
        return {
            "n": len(values),
            "logloss": fmean(value[0] for value in values) if values else None,
            "brier": fmean(value[1] for value in values) if values else None,
        }

    def se(values: list[float]) -> float | None:
        if len(values) < 2:
            return None
        return stdev(values) / math.sqrt(len(values))

    return {
        "deuce": absolute("deuce"),
        "tennisAbstract": absolute("tennisAbstract"),
        "paired": {
            "n": len(graded),
            "direction": "tennisAbstract-minus-deuce; positive favors DEUCE",
            "loglossDelta": fmean(delta_ll) if delta_ll else None,
            "seLogloss": se(delta_ll),
            "brierDelta": fmean(delta_brier) if delta_brier else None,
            "seBrier": se(delta_brier),
        },
    }


def _match_comparison(rows: list[dict]) -> dict:
    scored = _score_matches(rows)
    eligible = sum(row.get("status") in {"graded", "pending"} for row in rows)
    excluded = [row for row in rows if row.get("status") == "excluded"]
    rounds = sorted(
        {str(row["round"]) for row in rows if row.get("round")},
        key=lambda value: _STAGE_INDEX.get(value, 99),
    )
    by_round = []
    for round_name in rounds:
        subset = [row for row in rows if row.get("round") == round_name]
        block = _score_matches(subset)
        by_round.append({
            "round": round_name,
            "eligible": sum(row.get("status") in {"graded", "pending"} for row in subset),
            "graded": sum(row.get("status") == "graded" for row in subset),
            "pending": sum(row.get("status") == "pending" for row in subset),
            "excluded": sum(row.get("status") == "excluded" for row in subset),
            **block,
        })
    return {
        "eligible": eligible,
        "graded": sum(row.get("status") == "graded" for row in rows),
        "pending": sum(row.get("status") == "pending" for row in rows),
        "excluded": len(excluded),
        **scored,
        "byRound": by_round,
        "exclusionReasons": dict(sorted(Counter(
            str(row.get("reason") or "unknown") for row in excluded
        ).items())),
    }


def _probability_rows(value: object) -> tuple[dict[str, dict], set[str]]:
    """Canonicalize normalized snapshots or DEUCE projection/reach rows exactly."""
    if isinstance(value, Mapping) and isinstance(value.get("players"), list):
        raw_rows = value["players"]
    elif isinstance(value, Mapping) and isinstance(value.get("projection"), list):
        raw_rows = value["projection"]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        raw_rows = value
    elif isinstance(value, Mapping):
        raw_rows = [
            {"name": name, "probabilities": probabilities}
            for name, probabilities in value.items()
        ]
    else:
        raw_rows = []

    grouped: dict[str, list[dict]] = defaultdict(list)
    for raw in raw_rows:
        if not isinstance(raw, Mapping):
            continue
        name = raw.get("name", raw.get("player"))
        key = player_identity_key(name)
        probabilities = raw.get("probabilities", raw.get("reach"))
        probabilities = dict(probabilities) if isinstance(probabilities, Mapping) else {}
        if "W" not in probabilities:
            champion = raw.get("champion", raw.get("Champion"))
            if champion is not None:
                probabilities["W"] = champion
        normalized: dict[str, object] = {}
        for label, probability in probabilities.items():
            stage = _stage(label)
            if stage is not None:
                normalized[stage] = probability
        if key:
            grouped[key].append({"name": name, "probabilities": normalized})
    ambiguous = {key for key, rows in grouped.items() if len(rows) != 1}
    return {key: rows[0] for key, rows in grouped.items() if len(rows) == 1}, ambiguous


def _event_result_rows(snapshot: Mapping, results: object) -> list[dict]:
    espn_id, season, _, _ = _snapshot_meta(snapshot)
    if espn_id is None or season is None:
        return []
    out = []
    for record in _records(results):
        event, record_season, round_name = _record_identity(record, {})
        if event == espn_id and record_season == season and round_name in _STAGE_INDEX:
            out.append(record)
    return out


def _derived_stage_outcomes(snapshot: Mapping, results: object) -> tuple[dict[str, dict[str, bool]], str | None]:
    """Derive only advancement facts proven by completed exact-event results."""
    known: dict[str, dict[str, bool]] = defaultdict(dict)
    champion = None
    for record in _event_result_rows(snapshot, results):
        if not _is_completed(record):
            continue
        round_name = _stage(record.get("round"))
        if round_name is None or round_name == "W":
            continue
        pair = _record_pair(record)
        winner = player_identity_key(_winner(record))
        if pair is None or winner not in pair:
            continue
        loser = next(key for key in pair if key != winner)
        round_index = _STAGE_INDEX[round_name]
        for key in pair:
            for stage in _STAGE_ORDER[:round_index + 1]:
                known[key][stage] = True
        for stage in _STAGE_ORDER[round_index + 1:]:
            known[loser][stage] = False
        if round_index + 1 < len(_STAGE_ORDER):
            known[winner][_STAGE_ORDER[round_index + 1]] = True
        if round_name == "F":
            champion = winner
    return dict(known), champion


def _explicit_stage_outcomes(value: object) -> tuple[dict[str, dict[str, bool]], str | None]:
    if not isinstance(value, Mapping):
        return {}, None
    champion = value.get("champion") if isinstance(value.get("champion"), str) else None
    raw = value.get("players", value)
    out: dict[str, dict[str, bool]] = {}
    if isinstance(raw, Mapping):
        for name, stages in raw.items():
            if name == "champion" or not isinstance(stages, Mapping):
                continue
            key = player_identity_key(name)
            normalized = {
                stage: bool(outcome)
                for label, outcome in stages.items()
                if (stage := _stage(label)) is not None and isinstance(outcome, bool)
            }
            if key and normalized:
                out[key] = normalized
    return out, champion


def _score_binary_vectors(probabilities: list[float], outcomes: list[bool]) -> dict:
    values = [_binary_loss(probability, outcome) for probability, outcome in zip(probabilities, outcomes)]
    return {
        "n": len(values),
        "logloss": fmean(value[0] for value in values) if values else None,
        "brier": fmean(value[1] for value in values) if values else None,
    }


def _reach_comparison(
    snapshot: Mapping,
    deuce_stage_probabilities: object,
    results: object,
    *,
    stage_outcomes: object = None,
    champion: object = None,
) -> dict:
    external, external_ambiguous = _probability_rows(snapshot)
    deuce, deuce_ambiguous = _probability_rows(deuce_stage_probabilities)
    reasons = Counter()
    if external_ambiguous:
        reasons["external_player_identity_ambiguous"] = len(external_ambiguous)
    if deuce_ambiguous:
        reasons["deuce_player_identity_ambiguous"] = len(deuce_ambiguous)
    missing_deuce = set(external) - set(deuce)
    extra_deuce = set(deuce) - set(external)
    if missing_deuce:
        reasons["deuce_field_player_missing"] = len(missing_deuce)
    if extra_deuce:
        reasons["deuce_field_player_extra"] = len(extra_deuce)

    rounds = snapshot.get("rounds")
    stages = [_stage(label) for label in rounds] if isinstance(rounds, list) else []
    stages = [stage for stage in stages if stage is not None]
    derived, derived_champion = _derived_stage_outcomes(snapshot, results)
    explicit, explicit_champion = _explicit_stage_outcomes(stage_outcomes)
    for key, values in explicit.items():
        derived.setdefault(key, {}).update(values)
    champion_key = player_identity_key(champion or explicit_champion or derived_champion)

    stage_rows = []
    full_field = not reasons and bool(external) and set(external) == set(deuce)
    if full_field:
        for stage in stages:
            p_deuce: list[float] = []
            p_external: list[float] = []
            labels: list[bool] = []
            stage_reasons = Counter()
            pending = 0
            for key in sorted(external):
                ext_raw = external[key]["probabilities"].get(stage)
                deu_raw = deuce[key]["probabilities"].get(stage)
                ext_p = _display_probability(ext_raw)
                deu_p = _display_probability(deu_raw)
                if ext_p is None:
                    stage_reasons["external_probability_malformed"] += 1
                    continue
                if deu_p is None:
                    stage_reasons["deuce_probability_malformed"] += 1
                    continue
                outcome = derived.get(key, {}).get(stage)
                if not isinstance(outcome, bool):
                    pending += 1
                    continue
                p_external.append(ext_p)
                p_deuce.append(deu_p)
                labels.append(outcome)
            deuce_score = _score_binary_vectors(p_deuce, labels)
            external_score = _score_binary_vectors(p_external, labels)
            stage_rows.append({
                "stage": stage,
                "n": len(external),
                "resolved": len(labels),
                "eligible": len(external) - sum(stage_reasons.values()),
                "graded": len(labels),
                "pending": pending,
                "excluded": sum(stage_reasons.values()),
                "deuce": deuce_score,
                "tennisAbstract": external_score,
                "paired": {
                    "n": len(labels),
                    "direction": "tennisAbstract-minus-deuce; positive favors DEUCE",
                    "loglossDelta": (
                        external_score["logloss"] - deuce_score["logloss"] if labels else None),
                    "brierDelta": (
                        external_score["brier"] - deuce_score["brier"] if labels else None),
                    "seLogloss": None,
                    "seBrier": None,
                },
                "exclusionReasons": dict(sorted(stage_reasons.items())),
            })

    scored_stages = [row for row in stage_rows if row["graded"]]
    macro = {
        "n": len(scored_stages),
        "stages": len(scored_stages),
        "weighting": "equal-stage",
        "deuce": {
            "n": len(scored_stages),
            "logloss": fmean(row["deuce"]["logloss"] for row in scored_stages)
            if scored_stages else None,
            "brier": fmean(row["deuce"]["brier"] for row in scored_stages)
            if scored_stages else None,
        },
        "tennisAbstract": {
            "n": len(scored_stages),
            "logloss": fmean(row["tennisAbstract"]["logloss"] for row in scored_stages)
            if scored_stages else None,
            "brier": fmean(row["tennisAbstract"]["brier"] for row in scored_stages)
            if scored_stages else None,
        },
        "paired": {
            "n": len(scored_stages),
            "direction": "tennisAbstract-minus-deuce; positive favors DEUCE",
            "loglossDelta": fmean(row["paired"]["loglossDelta"] for row in scored_stages)
            if scored_stages else None,
            "brierDelta": fmean(row["paired"]["brierDelta"] for row in scored_stages)
            if scored_stages else None,
            "seLogloss": None,
            "seBrier": None,
        },
        "uncertainty": "No naive SE: player-stage outcomes are nested within one tournament.",
    }

    champion_block = None
    if full_field:
        p_deuce: dict[str, float] = {}
        p_external: dict[str, float] = {}
        invalid = False
        for key in sorted(external):
            ext_p = _display_probability(external[key]["probabilities"].get("W"))
            deu_p = _display_probability(deuce[key]["probabilities"].get("W"))
            if ext_p is None or deu_p is None:
                invalid = True
                break
            p_external[key] = ext_p
            p_deuce[key] = deu_p
        if invalid:
            champion_block = {"status": "unavailable", "reason": "champion_probability_malformed"}
        elif not champion_key:
            champion_block = {"status": "pending"}
        elif champion_key not in external:
            champion_block = {"status": "unavailable", "reason": "champion_field_mismatch"}
        else:
            def categorical(probabilities: dict[str, float]) -> dict:
                winner_probability = probabilities[champion_key]
                clipped = min(1.0 - LOG_LOSS_MIN, max(LOG_LOSS_MIN, winner_probability))
                return {
                    "n": 1,
                    "logloss": -math.log(clipped),
                    "brier": sum(
                        (probability - float(key == champion_key)) ** 2
                        for key, probability in probabilities.items()
                    ),
                    "championProbability": winner_probability,
                    "categoricalLogScore": -math.log(clipped),
                    "multiclassBrier": sum(
                        (probability - float(key == champion_key)) ** 2
                        for key, probability in probabilities.items()
                    ),
                    "probabilityMass": sum(probabilities.values()),
                }
            deu = categorical(p_deuce)
            ext = categorical(p_external)
            champion_block = {
                "status": "graded",
                "n": 1,
                "resolved": 1,
                "champion": next(
                    row["name"] for key, row in external.items() if key == champion_key),
                "deuce": deu,
                "tennisAbstract": ext,
                "paired": {
                    "n": 1,
                    "direction": "tennisAbstract-minus-deuce; positive favors DEUCE",
                    "loglossDelta": ext["logloss"] - deu["logloss"],
                    "brierDelta": ext["brier"] - deu["brier"],
                    "seLogloss": None,
                    "seBrier": None,
                    "categoricalLogScoreDelta": (
                        ext["categoricalLogScore"] - deu["categoricalLogScore"]),
                    "multiclassBrierDelta": ext["multiclassBrier"] - deu["multiclassBrier"],
                },
            }

    out = {
        "fieldSize": len(external),
        "fieldAligned": full_field,
        "stages": stage_rows,
        "exclusionReasons": dict(sorted(reasons.items())),
    }
    if scored_stages:
        out["macro"] = macro
    # The public contract treats ``champion`` as an optional scored aggregate.  A
    # status-only/null placeholder would invalidate the fail-soft browser guard, so omit it
    # until the tournament supplies a resolvable champion and two full distributions.
    if isinstance(champion_block, Mapping) and champion_block.get("status") == "graded":
        out["champion"] = champion_block
    return out


def _public_source(snapshot: Mapping) -> dict:
    source = snapshot.get("source")
    if isinstance(source, Mapping):
        name = source.get("name", source.get("provider", "Tennis Abstract"))
        values = {key: source.get(key) for key in (
            "url", "capturedAt", "lastModified", "etag", "normalizedSha256"
        )}
    else:
        name = source if isinstance(source, str) and source else "Tennis Abstract"
        values = {
            "url": snapshot.get("url"),
            "capturedAt": snapshot.get("capturedAt"),
            "lastModified": snapshot.get("lastModified"),
            "etag": snapshot.get("etag"),
            "normalizedSha256": snapshot.get("normalizedSha256"),
        }
    return {"name": name, **{key: value for key, value in values.items() if value is not None}}


def _public_status(match_comparison: Mapping, reach_comparison: Mapping | None = None) -> str:
    """Map deterministic report state onto the public three-value lifecycle."""
    has_work = bool(match_comparison.get("eligible") or match_comparison.get("graded"))
    pending = int(match_comparison.get("pending") or 0)
    resolved = int(match_comparison.get("graded") or 0)
    if reach_comparison:
        stages = reach_comparison.get("stages") or []
        has_work = has_work or bool(stages)
        pending += sum(int(stage.get("pending") or 0) for stage in stages)
        resolved += sum(int(stage.get("resolved") or 0) for stage in stages)
        champion_block = reach_comparison.get("champion")
        if isinstance(champion_block, Mapping) and champion_block.get("status") == "pending":
            pending += 1
    if not has_work and not resolved:
        return "unavailable"
    return "accruing" if pending else "complete"


def build_public_report(
    snapshot: Mapping,
    forecast_records: object,
    results: object,
    *,
    eligible_match_ids: object = None,
    deuce_stage_probabilities: object = None,
    stage_outcomes: object = None,
    champion: object = None,
    include_retirements: bool = False,
    evaluated_match_rows: object = None,
) -> dict:
    """Build the deterministic web-facing comparison artifact.

    ``eligible_match_ids`` must contain values returned by :func:`snapshot_match_ids` when
    outcome rows do not carry an exact timezone-aware match start.  It is deliberately not
    inferred from a calendar date.
    """
    rows = (
        _records(evaluated_match_rows)
        if evaluated_match_rows is not None
        else evaluate_matches(
            snapshot, forecast_records, results,
            eligible_match_ids=eligible_match_ids,
            include_retirements=include_retirements,
        )
    )
    match_comparison = _match_comparison(rows)
    benchmark = {
        "id": "tennis-abstract",
        "name": "Tennis Abstract",
        "tour": str(snapshot.get("tour") or "").lower() or None,
        "event": snapshot.get("event"),
        "espnId": _clean_id(snapshot.get("espnId", snapshot.get("espn_id"))),
        "season": _season(snapshot),
    }
    report = {
        "schema": REPORT_SCHEMA,
        "benchmark": benchmark,
        "status": _public_status(match_comparison),
        "source": _public_source(snapshot),
        "matchComparison": match_comparison,
        "caveats": [
            "Only exact espnId, round, canonical player-pair, and draw-position evidence is used; no fuzzy name or event matching.",
            "Match scores use the latest DEUCE quote available by the external capture and require proof that the capture preceded match start.",
            "Both match probabilities are rounded to 0.001; log loss clips displayed probabilities to 0.0005..0.9995.",
            "Walkovers and, by default, retirements are excluded from primary match scores; replacement or withdrawal pair mismatches fail closed.",
            "Paired deltas are Tennis-Abstract-minus-DEUCE; positive values favour DEUCE.",
        ],
    }
    if deuce_stage_probabilities is not None:
        report["reachComparison"] = _reach_comparison(
            snapshot, deuce_stage_probabilities, results,
            stage_outcomes=stage_outcomes, champion=champion,
        )
        report["status"] = _public_status(match_comparison, report["reachComparison"])
        report["caveats"].append(
            "Reach-stage macro scores weight stages equally; no SE is computed from nested player-stage outcomes in a single tournament."
        )
    return report


def build_report(*args, **kwargs) -> dict:
    """Backward-friendly pure alias for :func:`build_public_report`."""
    return build_public_report(*args, **kwargs)
