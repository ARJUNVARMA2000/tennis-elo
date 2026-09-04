"""Benchmarks invariants extracted without changing gate semantics."""

from __future__ import annotations

import math

import pandas as pd

from ...config import (
    TENNIS_ABSTRACT_US_OPEN_FROZEN,
)
from .common import _UUID4_RE, _add_finding, _plain_int, _player_identity_key


def _check_tennis_abstract_benchmark(out: list, tour: str, payload: dict) -> None:
    """An optional benchmark may be absent, but emitted bytes must be safe and honest."""
    entity = "artifact:tennis-abstract.json"
    errors: list[str] = []
    expected = TENNIS_ABSTRACT_US_OPEN_FROZEN.get(tour) or {}
    expected_url = (
        "https://www.tennisabstract.com/current/2026USOpenMenForecast.html"
        if tour == "atp"
        else "https://www.tennisabstract.com/current/2026USOpenWomenForecast.html"
    )
    direction = "tennisAbstract-minus-deuce; positive favors DEUCE"
    stage_order = ["R64", "R32", "R16", "QF", "SF", "F", "W"]

    def count(value: object) -> bool:
        return _plain_int(value) and value >= 0

    def finite(value: object) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )

    def metric_block(
        value: object, *, expected_n: int, max_brier: float = 1.0
    ) -> bool:
        if not isinstance(value, dict) or value.get("n") != expected_n:
            return False
        logloss, brier = value.get("logloss"), value.get("brier")
        if expected_n == 0:
            return logloss is None and brier is None
        return (
            finite(logloss)
            and float(logloss) >= 0
            and finite(brier)
            and 0 <= float(brier) <= max_brier
        )

    def paired_block(
        value: object,
        *,
        expected_n: int,
        allow_naive_se: bool = True,
    ) -> bool:
        if (
            not isinstance(value, dict)
            or value.get("n") != expected_n
            or value.get("direction") != direction
        ):
            return False
        deltas = (value.get("loglossDelta"), value.get("brierDelta"))
        standard_errors = (value.get("seLogloss"), value.get("seBrier"))
        if expected_n == 0:
            return all(item is None for item in (*deltas, *standard_errors))
        if not all(finite(item) for item in deltas):
            return False
        if not allow_naive_se or expected_n == 1:
            return all(item is None for item in standard_errors)
        return all(finite(item) and float(item) >= 0 for item in standard_errors)

    def count_block(value: object, *, total: int) -> tuple[int, int] | None:
        if not isinstance(value, dict):
            return None
        values = [value.get(key) for key in ("eligible", "graded", "pending", "excluded")]
        if not all(count(item) for item in values):
            return None
        eligible, graded, pending, excluded = values
        if eligible != graded + pending or eligible + excluded != total:
            return None
        return graded, pending

    benchmark = payload.get("benchmark")
    if payload.get("schema") != "tennis-abstract-benchmark-v1":
        errors.append("schema")
    if not isinstance(benchmark, dict) or any((
        benchmark.get("id") != "tennis-abstract",
        benchmark.get("name") != "Tennis Abstract",
        benchmark.get("tour") != tour,
        benchmark.get("event") != "US Open",
        benchmark.get("espnId") != "189-2026",
        benchmark.get("season") != 2026,
    )):
        errors.append("benchmark identity")

    source = payload.get("source")
    if not isinstance(source, dict) or any((
        source.get("name") != "Tennis Abstract",
        source.get("url") != expected_url,
        source.get("capturedAt") != expected.get("capturedAt"),
        source.get("normalizedSha256") != expected.get("normalizedSha256"),
    )):
        errors.append("frozen source identity")

    caveats = payload.get("caveats")
    if (
        not isinstance(caveats, list)
        or not caveats
        or any(not isinstance(value, str) or not value.strip() for value in caveats)
        or not any("after Day 1" in value or "post-start" in value for value in caveats)
        or not any("One tournament" in value and "descriptive" in value for value in caveats)
    ):
        errors.append("benchmark caveats")

    capture = payload.get("capture")
    if not isinstance(capture, dict) or any((
        capture.get("classification") != "first-post-start-capture",
        capture.get("eventTimezone") != "America/New_York",
        capture.get("captureLocalDate") != "2026-08-30",
        capture.get("eligibleMatchProof")
        != "saved scheduledDate is strictly after captureLocalDate",
    )):
        errors.append("capture classification")

    receipts = payload.get("receipts")
    if not isinstance(receipts, dict) or set(receipts) != {
        "sourceNormalizedSha256", "predictorArtifactId", "predictorTrainedAt",
        "forecastMalformedLinesSkipped",
    }:
        errors.append("receipts")
    else:
        trained = pd.to_datetime(receipts.get("predictorTrainedAt"), errors="coerce", utc=True)
        captured = pd.to_datetime(expected.get("capturedAt"), errors="coerce", utc=True)
        if (
            receipts.get("sourceNormalizedSha256") != expected.get("normalizedSha256")
            or not isinstance(receipts.get("predictorArtifactId"), str)
            or _UUID4_RE.fullmatch(receipts["predictorArtifactId"]) is None
            or pd.isna(trained)
            or pd.isna(captured)
            or trained > captured
            or not count(receipts.get("forecastMalformedLinesSkipped"))
        ):
            errors.append("receipt identity")

    match = payload.get("matchComparison")
    match_counts = count_block(match, total=64)
    match_pending = None
    if match_counts is None:
        errors.append("match counts")
    else:
        graded, match_pending = match_counts
        if not metric_block(match.get("deuce"), expected_n=graded):
            errors.append("DEUCE match metrics")
        if not metric_block(match.get("tennisAbstract"), expected_n=graded):
            errors.append("Tennis Abstract match metrics")
        if not paired_block(match.get("paired"), expected_n=graded):
            errors.append("paired match metrics")
        reasons = match.get("exclusionReasons")
        if (
            not isinstance(reasons, dict)
            or any(not isinstance(key, str) or not count(value) or value <= 0
                   for key, value in reasons.items())
            or sum(reasons.values()) != match.get("excluded")
        ):
            errors.append("match exclusion reasons")
        rounds = match.get("byRound")
        if not isinstance(rounds, list) or len(rounds) != 1:
            errors.append("match round coverage")
        else:
            round_row = rounds[0]
            round_counts = count_block(round_row, total=64)
            if (
                round_counts != match_counts
                or round_row.get("round") != "R128"
                or not metric_block(round_row.get("deuce"), expected_n=graded)
                or not metric_block(round_row.get("tennisAbstract"), expected_n=graded)
                or not paired_block(round_row.get("paired"), expected_n=graded)
            ):
                errors.append("match round contract")

    reach = payload.get("reachComparison")
    stage_pending_total = None
    if not isinstance(reach, dict) or any((
        reach.get("fieldSize") != 128,
        reach.get("fieldAligned") is not True,
        reach.get("exclusionReasons") != {},
    )):
        errors.append("reach field identity")
    else:
        stages = reach.get("stages")
        if not isinstance(stages, list) or [
            row.get("stage") if isinstance(row, dict) else None for row in stages
        ] != stage_order:
            errors.append("reach stages")
        else:
            stage_pending_total = 0
            scored_stages = 0
            resolved_counts = []
            for row in stages:
                counts = count_block(row, total=128)
                if counts is None:
                    errors.append(f"reach stage {row.get('stage')!r} counts")
                    continue
                graded, pending = counts
                resolved_counts.append(graded)
                stage_pending_total += pending
                scored_stages += int(graded > 0)
                reasons = row.get("exclusionReasons")
                if (
                    row.get("n") != 128
                    or row.get("resolved") != graded
                    or not metric_block(row.get("deuce"), expected_n=graded)
                    or not metric_block(row.get("tennisAbstract"), expected_n=graded)
                    # Reach outcomes share one bracket; the producer and browser omit
                    # independent-sample SEs for every stage, including graded n >= 2.
                    or not paired_block(
                        row.get("paired"), expected_n=graded, allow_naive_se=False,
                    )
                    or not isinstance(reasons, dict)
                    or any(not isinstance(key, str) or not count(value) or value <= 0
                           for key, value in reasons.items())
                    or sum(reasons.values()) != row.get("excluded")
                ):
                    errors.append(f"reach stage {row.get('stage')!r}")
            if any(
                earlier < later
                for earlier, later in zip(
                    resolved_counts, resolved_counts[1:], strict=False
                )
            ):
                errors.append("reach resolved monotonicity")
            macro = reach.get("macro")
            if scored_stages == 0:
                if macro is not None:
                    errors.append("empty reach macro")
            elif not isinstance(macro, dict) or any((
                macro.get("n") != scored_stages,
                macro.get("stages") != scored_stages,
                macro.get("weighting") != "equal-stage",
                not metric_block(macro.get("deuce"), expected_n=scored_stages),
                not metric_block(macro.get("tennisAbstract"), expected_n=scored_stages),
                not paired_block(
                    macro.get("paired"), expected_n=scored_stages,
                    allow_naive_se=False,
                ),
                not isinstance(macro.get("uncertainty"), str),
            )):
                errors.append("reach macro")
            champion = reach.get("champion")
            winner_resolved = stages[-1].get("resolved") == 128
            if champion is None:
                if winner_resolved:
                    errors.append("champion distribution missing")
            elif (
                not isinstance(champion, dict)
                or champion.get("status") != "graded"
                or champion.get("n") != 1
                or champion.get("resolved") != 1
                or not isinstance(champion.get("champion"), str)
                or not metric_block(
                    champion.get("deuce"), expected_n=1, max_brier=2.0
                )
                or not metric_block(
                    champion.get("tennisAbstract"), expected_n=1, max_brier=2.0
                )
                or not paired_block(
                    champion.get("paired"), expected_n=1,
                    allow_naive_se=False,
                )
            ):
                errors.append("champion distribution")

    status = payload.get("status")
    if match_pending is not None and stage_pending_total is not None:
        expected_status = "accruing" if match_pending + stage_pending_total else "complete"
        if status != expected_status:
            errors.append("status lifecycle")
    elif status not in {"accruing", "complete", "unavailable"}:
        errors.append("status")

    if errors:
        _add_finding(
            out,
            "output.tennis_abstract.contract_invalid",
            f"{tour}: tennis-abstract.json benchmark contract is malformed",
            severity="error",
            entity=entity,
            evidence={"problems": sorted(set(errors))},
        )

def _check_kalshi_ledger(out: list, tour: str, rows: list[dict]) -> None:
    """The Kalshi scorecard's scored rows must be morning-anchored PRE-match quotes of
    correctly-joined results (audit 2026-07-09: in-play occurrence-anchored prints, a
    settled-book carry scored as a 0.995 'favorite', and a rematch mis-join double-
    scoring one result all reached the deployed scorecard). One invariant per class."""
    from ...eval.kalshi_ledger import PREMATCH_UTC_HOUR
    from ..kalshi import CANDLE_LOOKBACK_S, EXTREME_CARRY_MID
    seen: dict[tuple, str] = {}
    for r in rows:
        if not (r.get("match_status") == "matched"
                and r.get("result_type") == "completed"
                and r.get("price_kind") == "candle"
                and r.get("p_model") and r.get("p_kalshi")):
            continue
        tick, rd = r.get("event_ticker", "?"), r.get("result_date", "")
        ts = pd.to_datetime(r.get("price_ts"), utc=True, errors="coerce")
        anchor = pd.to_datetime(rd, utc=True, errors="coerce")
        if pd.isna(ts) or pd.isna(anchor):
            _add_finding(
                out, "output.kalshi_ledger.timestamp_invalid",
                f"{tour}: kalshi ledger scored row {tick} lacks a parseable "
                f"price_ts/result_date ({r.get('price_ts')!r}, {rd!r})",
                severity="error", entity=f"kalshi:{tick}",
                evidence={"priceTs": repr(r.get("price_ts")), "resultDate": repr(rd)})
        else:
            anchor += pd.Timedelta(hours=PREMATCH_UTC_HOUR)
            if ts > anchor:
                _add_finding(
                    out, "output.kalshi_ledger.quote_after_anchor",
                    f"{tour}: kalshi ledger scored row {tick} quoted after its "
                    f"08:00 anchor ({r.get('price_ts')} > {rd} 08:00Z) — "
                    f"occurrence-anchored/in-play print",
                    severity="error", entity=f"kalshi:{tick}",
                    evidence={"priceTs": str(r.get("price_ts")), "resultDate": str(rd),
                              "anchorHourUtc": PREMATCH_UTC_HOUR})
            elif ts <= anchor - pd.Timedelta(seconds=CANDLE_LOOKBACK_S):
                mids = []
                for c in ("mid_a", "mid_b"):
                    try:
                        mids.append(float(r.get(c) or ""))
                    except ValueError:
                        pass
                if any(not (1 - EXTREME_CARRY_MID < m < EXTREME_CARRY_MID) for m in mids):
                    _add_finding(
                        out, "output.kalshi_ledger.settled_quote_carried",
                        f"{tour}: kalshi ledger scored row {tick} carries a "
                        f"settled-extreme window-edge quote (mids {mids}) — "
                        f"post-result carry print",
                        severity="error", entity=f"kalshi:{tick}",
                        evidence={"mids": mids, "extremeCarryMid": EXTREME_CARRY_MID})
        ka_res, a_won = r.get("kalshi_result_a"), r.get("a_won")
        if (ka_res in ("yes", "no") and a_won in ("0", "1")
                and (ka_res == "yes") != (a_won == "1")):
            _add_finding(
                out, "output.kalshi_ledger.settlement_mismatch",
                f"{tour}: kalshi ledger scored row {tick} settlement "
                f"contradicts its joined result — mis-joined match",
                severity="error", entity=f"kalshi:{tick}",
                evidence={"kalshiResultA": ka_res, "aWon": a_won})
        key = (frozenset((r.get("player_a", ""), r.get("player_b", ""))), rd)
        if key in seen:
            _add_finding(
                out, "output.kalshi_ledger.result_scored_twice",
                f"{tour}: kalshi ledger scores one result twice "
                f"({seen[key]} and {tick}, {rd})",
                severity="error",
                entity=f"result:{':'.join(sorted(_player_identity_key(p) for p in key[0]))}:{rd}",
                evidence={"tickers": [seen[key], tick], "resultDate": str(rd)})
        else:
            seen[key] = tick
