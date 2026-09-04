"""Products invariants extracted without changing gate semantics."""

from __future__ import annotations

import re
from collections import Counter

import pandas as pd

from ...config import (
    WTA_DUAL_STATE_GATE_THRESHOLD,
)
from ...model.features import FEATURES
from ...timing import (
    PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS,
    PRODUCT_STAGE_NAMES,
    STAGE_STATUS_FILENAME,
    STAGE_STATUS_SCHEMA,
)
from .common import _add_finding, _event_entity, _FindingCollector


def _check_method(out: list, tour: str, method: dict, meta: dict | None) -> None:
    """method.json publishes the effective production parameters to the /method page.
    Sanity only — never pin tuned values here (those live in test_export.py); the gate
    catches a build that would render impossible constants or drift from meta.json."""
    required = ["elo", "serveReturn", "context", "tiers", "combiner", "protocol"]
    if tour == "wta":
        required.append("stateGate")
    missing = [k for k in required
               if not isinstance(method.get(k), dict)]
    if missing:
        _add_finding(
            out, "output.method.section_missing",
            f"{tour}: method.json missing section(s) {', '.join(missing)}",
            severity="error", entity="artifact:method.json",
            evidence={"sections": missing})
        return
    if method.get("tour") != tour:
        _add_finding(
            out, "output.method.tour_mismatch",
            f"{tour}: method.json says tour={method.get('tour')!r}",
            severity="error", entity="artifact:method.json",
            evidence={"expected": tour, "actual": repr(method.get("tour"))})
    elo = method["elo"]
    for key, ok in (("ratingScale", lambda v: v > 0), ("kScale", lambda v: v > 0),
                    ("surfaceBlend", lambda v: 0 <= v <= 1), ("movCap", lambda v: v >= 1)):
        v = elo.get(key)
        if not isinstance(v, (int, float)) or not ok(v):
            _add_finding(
                out, "output.method.elo_parameter_invalid",
                f"{tour}: method.json elo.{key}={v!r} out of range",
                severity="error", entity=f"artifact:method.json#elo:{key}",
                evidence={"parameter": key, "value": repr(v)})
    mults = method["tiers"].get("kMult")
    if not isinstance(mults, dict) or not mults or \
            any(not isinstance(v, (int, float)) or not 0.3 < v < 2.0 for v in mults.values()):
        _add_finding(
            out, "output.method.tier_multiplier_invalid",
            f"{tour}: method.json tiers.kMult implausible ({mults!r})",
            severity="error", entity="artifact:method.json#tiers:kMult",
            evidence={"value": repr(mults)})
    comb = method["combiner"]
    nfeat = comb.get("featureCount")
    if nfeat != len(FEATURES):
        _add_finding(
            out, "output.method.feature_count_invalid",
            f"{tour}: method.json featureCount {nfeat} != {len(FEATURES)} (schema drift)",
            severity="error", entity="artifact:method.json#combiner:featureCount",
            evidence={"actual": nfeat, "expected": len(FEATURES)})
    feats = (meta or {}).get("features")
    if isinstance(feats, list) and nfeat != len(feats):
        _add_finding(
            out, "output.method.meta_feature_count_mismatch",
            f"{tour}: method.json featureCount {nfeat} != meta.features {len(feats)}",
            severity="error", entity="artifact:method.json#combiner:featureCount",
            evidence={"methodCount": nfeat, "metaCount": len(feats)})
    if not isinstance(comb.get("nBag"), int) or comb["nBag"] < 1:
        _add_finding(
            out, "output.method.bag_count_invalid",
            f"{tour}: method.json combiner.nBag={comb.get('nBag')!r} invalid",
            severity="error", entity="artifact:method.json#combiner:nBag",
            evidence={"value": repr(comb.get("nBag"))})
    if tour == "wta":
        gate = method["stateGate"]
        expected = WTA_DUAL_STATE_GATE_THRESHOLD
        if gate.get("enabled") is not (expected is not None):
            _add_finding(
                out, "output.method.state_gate_enabled_mismatch",
                f"{tour}: method.json stateGate.enabled={gate.get('enabled')!r} "
                f"does not match config",
                severity="error", entity="artifact:method.json#stateGate:enabled",
                evidence={"actual": repr(gate.get("enabled")),
                          "expected": expected is not None})
        if gate.get("minMainMatches") != expected:
            _add_finding(
                out, "output.method.state_gate_threshold_mismatch",
                f"{tour}: method.json stateGate.minMainMatches="
                f"{gate.get('minMainMatches')!r} (expected {expected!r})",
                severity="error", entity="artifact:method.json#stateGate:minMainMatches",
                evidence={"actual": repr(gate.get("minMainMatches")),
                          "expected": repr(expected)})
        if gate.get("trainingPopulation") != "main-only":
            _add_finding(
                out, "output.method.state_gate_population_mismatch",
                f"{tour}: method.json stateGate training population is not main-only",
                severity="error", entity="artifact:method.json#stateGate:trainingPopulation",
                evidence={"actual": repr(gate.get("trainingPopulation")),
                          "expected": "main-only"})

def _check_event_coverage(out: list, tour: str, coverage: dict, tournaments: list) -> None:
    """Every independently observed begun event occurs exactly once on the board."""
    if coverage.get("version") != 1:
        _add_finding(
            out, "output.event_coverage.version_invalid",
            f"{tour}: event_coverage.json version {coverage.get('version')!r} is not 1",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"actual": repr(coverage.get("version")), "expected": 1})
    if coverage.get("tour") != tour:
        _add_finding(
            out, "output.event_coverage.tour_mismatch",
            f"{tour}: event_coverage.json says tour={coverage.get('tour')!r}",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"actual": repr(coverage.get("tour")), "expected": tour})
    events = coverage.get("events")
    if not isinstance(events, list):
        _add_finding(
            out, "output.event_coverage.events_invalid",
            f"{tour}: event_coverage.json events is not a list",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"valueType": type(events).__name__})
        return

    expected: dict[str, list[str]] = {}
    malformed = 0
    for event in events:
        if not isinstance(event, dict) or not event.get("key") or not event.get("name"):
            malformed += 1
            continue
        expected.setdefault(str(event["key"]), []).append(str(event["name"]))
    if malformed:
        _add_finding(
            out, "output.event_coverage.expected_event_invalid",
            f"{tour}: event_coverage.json has {malformed} malformed expected event(s)",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"malformedEvents": malformed})
    for key, names in sorted(expected.items()):
        if len(names) > 1:
            _add_finding(
                out, "output.event_coverage.expected_key_duplicate",
                f"{tour}: event_coverage.json repeats coverage key {key} "
                f"for {len(names)} expected events",
                severity="error", entity=_event_entity({"coverageKey": key}),
                evidence={"coverageKey": key, "eventNames": names})

    shipped = Counter()
    shell_names: dict[str, str] = {}
    missing_keys = []
    for card in tournaments:
        if not isinstance(card, dict):
            continue
        key = card.get("coverageKey")
        if not key:
            missing_keys.append(card.get("name"))
        else:
            shipped[str(key)] += 1
            if card.get("coverageOnly"):
                shell_names[str(key)] = str(card.get("name"))
    if missing_keys:
        shown = ", ".join(repr(n) for n in missing_keys[:3])
        _add_finding(
            out, "output.event_coverage.card_key_missing",
            f"{tour}: tournaments.json has {len(missing_keys)} card(s) without a "
            f"coverageKey ({shown})",
            severity="error", entity="artifact:tournaments.json",
            evidence={"eventNames": [str(name) for name in missing_keys]})

    for key, names in sorted(expected.items()):
        count = shipped[key]
        name = names[0]
        if count == 0:
            _add_finding(
                out, "output.event_coverage.missing_card",
                f"{tour}: begun tournament {name!r} (coverage key {key}) is missing "
                f"from tournaments.json",
                severity="error", entity=_event_entity({"coverageKey": key}),
                evidence={"name": name, "coverageKey": key})
        elif count > 1:
            _add_finding(
                out, "output.event_coverage.card_duplicate",
                f"{tour}: begun tournament {name!r} coverage key {key} appears "
                f"{count} times in tournaments.json",
                severity="error", entity=_event_entity({"coverageKey": key}),
                evidence={"eventName": name, "coverageKey": key, "count": count})

    recorded = coverage.get("shippedKeys")
    actual = sorted(key for key, count in shipped.items() for _ in range(count))
    if not isinstance(recorded, list) or sorted(str(k) for k in recorded) != actual:
        _add_finding(
            out, "output.event_coverage.shipped_keys_mismatch",
            f"{tour}: event_coverage.json shippedKeys does not match tournaments.json",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"recorded": list(map(str, recorded)) if isinstance(recorded, list) else None,
                      "actual": actual})

    recorded_shells = coverage.get("shellKeys")
    actual_shells = sorted(shell_names)
    if not isinstance(recorded_shells, list) or sorted({str(k) for k in recorded_shells}) != actual_shells:
        _add_finding(
            out, "output.event_coverage.shell_keys_mismatch",
            f"{tour}: event_coverage.json shellKeys does not match coverageOnly cards",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"recorded": list(map(str, recorded_shells))
                      if isinstance(recorded_shells, list) else None,
                      "actual": actual_shells})
    for key in actual_shells:
        _add_finding(
            out, "output.event_coverage.shell_only",
            f"{tour}: begun tournament {shell_names[key]!r} (coverage key {key}) is "
            f"represented only by a coverage shell",
            severity="error", entity=_event_entity({"coverageKey": key}),
            evidence={"eventName": shell_names[key], "coverageKey": key})

def _stage_success_overdue(value: object, observed_at: pd.Timestamp) -> bool:
    stamp = pd.to_datetime(value, utc=True, errors="coerce") if value else pd.NaT
    if pd.isna(stamp):
        return False
    now_utc = observed_at if observed_at.tzinfo else observed_at.tz_localize("UTC")
    return now_utc - stamp > pd.Timedelta(hours=PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS)

def _public_stage_error_type(value: object) -> str:
    """Safe, stable public category; detailed exception prose stays in the private receipt."""
    text = str(value or "StageError")
    return text if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,119}", text) else "StageError"

def _check_pipeline_stage_status(
    out: _FindingCollector,
    tour: str,
    snapshot: object,
    observed_at: pd.Timestamp,
    *,
    expected: bool,
) -> None:
    """Surface durable soft-fail outcomes without turning them into deploy blockers."""
    if not isinstance(snapshot, dict) or snapshot.get("state") == "missing":
        # Rollout/fresh clones have no receipt until the first attempted stage. Absence alone
        # proves failure only after meta declares that this producer version owns the receipt.
        if expected:
            _add_finding(
                out,
                "output.pipeline_stage.receipt_missing",
                f"{tour}: expected private {STAGE_STATUS_FILENAME} is missing",
                severity="warning",
                entity=f"artifact:{STAGE_STATUS_FILENAME}",
                evidence={"expectedSchema": STAGE_STATUS_SCHEMA},
            )
        return
    if snapshot.get("state") != "valid":
        _add_finding(
            out,
            "output.pipeline_stage.receipt_malformed",
            f"{tour}: {STAGE_STATUS_FILENAME} is present but malformed",
            severity="warning",
            entity=f"artifact:{STAGE_STATUS_FILENAME}",
            evidence={
                "errorType": _public_stage_error_type(snapshot.get("errorType")),
            },
        )
        return

    receipt = snapshot.get("receipt") or {}
    if expected:
        missing_stages = sorted(PRODUCT_STAGE_NAMES - set(receipt.get("stages") or {}))
        if missing_stages:
            _add_finding(
                out,
                "output.pipeline_stage.receipt_incomplete",
                f"{tour}: {STAGE_STATUS_FILENAME} lacks expected product stage(s) "
                f"{missing_stages}",
                severity="warning",
                entity=f"artifact:{STAGE_STATUS_FILENAME}",
                evidence={"missingStages": missing_stages},
            )
    for stage, record in sorted((receipt.get("stages") or {}).items()):
        criticality = record["criticality"]
        if record["outcome"] == "failure":
            error_type = _public_stage_error_type(record["error"].get("type"))
            evidence = {
                "criticality": criticality,
                "errorType": error_type,
            }
            _add_finding(
                out,
                "output.pipeline_stage.current_failure",
                f"{tour}: pipeline stage {stage!r} most recently failed ({error_type})",
                severity="warning" if criticality == "product" else "info",
                entity=f"pipeline-stage:{stage}",
                evidence=evidence,
            )
            # One continuing failure is one incident. Per-attempt timestamps, duration,
            # inputs, and detailed errors remain private so an hourly retry neither leaks
            # provider detail nor churns the public issue revision.
            continue

        if criticality != "product":
            continue
        if _stage_success_overdue(record.get("lastSuccessAt"), observed_at):
            _add_finding(
                out,
                "output.pipeline_stage.success_overdue",
                f"{tour}: product pipeline stage {stage!r} has not succeeded within "
                f"{PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS}h",
                severity="warning",
                entity=f"pipeline-stage:{stage}",
                evidence={
                    "lastSuccessAt": record["lastSuccessAt"],
                    "maxHours": PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS,
                    "lastSuccessInputFingerprint": record["lastSuccessInputFingerprint"],
                },
            )
