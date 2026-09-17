"""Independent interval arithmetic and retained-source completion semantics."""

import copy
import gzip
from datetime import UTC, datetime, timedelta

import prospective_sources as source
import pytest
import time_evidence as te
from test_prospective_sources import FIXTURES, Response, transport

NOW = datetime(2026, 9, 8, 20, tzinfo=UTC)
ROW = {
    "espnId": "189-2026",
    "season": 2026,
    "round": "QF",
    "playerA": "A",
    "playerB": "B",
    "status": "completed",
    "winner": "A",
    "earliestStartAt": "2026-09-08T15:00:00Z",
}
BATCH = {"observedAt": NOW.isoformat()}


def claim(row=ROW, kind="actual-start-interval", lower="2026-09-08T15:00:00Z", upper="2026-09-08T15:02:00Z"):
    result = {
        "kind": kind,
        "producer": "synthetic-start-v1",
        "matchKey": te.match_key(row, "wta"),
        "sourceSHA256": "a" * 64,
        "observedAt": NOW.isoformat(),
    }
    if kind == "actual-start":
        result.update(at=lower, errorSeconds=0)
    else:
        result.update(lowerAt=lower, upperAt=upper)
    return result


def completion(row=ROW, observed=NOW):
    return {
        "kind": "completed-observation",
        "producer": "synthetic-completed-v1",
        "matchKey": te.match_key(row, "wta"),
        "sourceSHA256": "b" * 64,
        "observedAt": observed.isoformat(),
    }


def resolved(*rows, captured="2026-09-08T14:00:00Z"):
    return te.resolve(
        [(r, BATCH, str(i) * 64) for i, r in enumerate(rows)],
        original=ROW,
        captured_at=captured,
        evidence_kind="synthetic-qa",
    )


def complete_row():
    row = copy.deepcopy(ROW)
    row.update(startEvidence=claim(), completionEvidence=completion())
    return row


def test_precision_expands_outwards_with_offset():
    evidence = claim(kind="actual-start", lower="2026-09-08T11:00:00-04:00")
    evidence["errorSeconds"] = 30
    lo, hi = te.start_interval(evidence, ROW, BATCH, evidence_kind="synthetic-qa")
    assert lo == datetime(2026, 9, 8, 14, 59, 30, tzinfo=UTC)
    assert hi == datetime(2026, 9, 8, 15, 0, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "scheduled"),
        ("kind", "official-not-before"),
        ("kind", "first-observed-live"),
        ("kind", "start-upper-bound"),
        ("producer", "espn-startDate"),
        ("producer", "unknown"),
        ("matchKey", "c" * 64),
        ("sourceSHA256", "bad"),
        ("observedAt", "2026-09-09T00:00:00Z"),
        ("upperAt", "2026-09-08T14:00:00Z"),
        ("lowerAt", "2026-09-08"),
        ("lowerAt", None),
        ("upperAt", "2026-09-09T00:00:00Z"),
    ],
)
def test_unsupported_or_invalid_bounds_never_qualify(field, value):
    evidence = claim()
    evidence[field] = value
    with pytest.raises((ValueError, TypeError, AttributeError)):
        te.start_interval(evidence, ROW, BATCH, evidence_kind="synthetic-qa")


@pytest.mark.parametrize("error", [True, -1, 1.5, 3601, None])
def test_precision_requires_explicit_bounded_integer(error):
    evidence = claim(kind="actual-start")
    evidence["errorSeconds"] = error
    with pytest.raises(ValueError):
        te.start_interval(evidence, ROW, BATCH, evidence_kind="synthetic-qa")


@pytest.mark.parametrize("seconds,eligible", [(299, False), (300, False), (301, True)])
def test_strict_five_minute_boundary(seconds, eligible):
    captured = (datetime(2026, 9, 8, 15, tzinfo=UTC) - timedelta(seconds=seconds)).isoformat()
    result, reason = resolved(complete_row(), captured=captured)
    assert (result is not None) == eligible
    assert reason == (None if eligible else "timingNotProved")


def test_overlapping_intervals_use_union_and_completion_tightens_only_upper():
    first, second = complete_row(), complete_row()
    second["startEvidence"] = claim(lower="2026-09-08T15:01:00Z", upper="2026-09-08T15:04:00Z")
    second["completionEvidence"] = completion(observed=datetime(2026, 9, 8, 15, 3, tzinfo=UTC))
    value, reason = resolved(first, second)
    assert reason is None
    assert value["startLowerAt"] == "2026-09-08T15:00:00+00:00"
    assert value["startUpperAt"] == "2026-09-08T15:03:00+00:00"
    assert value["proof"]["finishUpperAt"] == "2026-09-08T15:03:00+00:00"


def test_disjoint_intervals_conflict():
    first, second = complete_row(), complete_row()
    second["startEvidence"] = claim(lower="2026-09-08T16:00:00Z", upper="2026-09-08T16:02:00Z")
    assert resolved(first, second)[1] == "conflictingStartIntervals"


def test_partial_claims_not_assembled_and_invalid_claims_not_ignored():
    first, second = complete_row(), complete_row()
    first.pop("startEvidence")
    second.pop("completionEvidence")
    assert resolved(first, second)[1] == "noCompleteTimingClaim"
    first["startEvidence"] = {"kind": "scheduled"}
    assert resolved(first, complete_row())[1] == "invalidTimeEvidence"


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"actualStartedAt": "2026-09-08T15:00:00Z"}, "legacyTimeFields"),
        ({"finishedAt": NOW.isoformat()}, "legacyTimeFields"),
        ({"startEvidence": None}, "missingStartProof"),
        ({"completionEvidence": None}, "missingCompletionProof"),
        ({"status": "retired"}, "retired"),
    ],
)
def test_missing_or_legacy_claims_explicit(change, reason):
    row = complete_row()
    row.update(change)
    assert resolved(row)[1] == reason


def test_completion_refresh_does_not_move_upper_bound_later():
    first, second = complete_row(), complete_row()
    first["completionEvidence"] = completion(observed=NOW - timedelta(hours=1))
    value, reason = resolved(first, second)
    assert reason is None and value["proof"]["finishUpperAt"] == (NOW - timedelta(hours=1)).isoformat()
    assert "finishedAt" not in value["proof"]


@pytest.fixture
def retained(tmp_path, monkeypatch):
    for name in ("espn", "wta"):
        raw = gzip.decompress((FIXTURES / f"{name}.json.gz").read_bytes())
        url = source.endpoint(name, **({"event": "905", "year": 2026} if name == "wta" else {}))
        transport(monkeypatch, Response(raw, url=url))
        source.fetch_once(
            tmp_path / name,
            trusted_root=tmp_path,
            source=name,
            **({"event": "905", "year": 2026} if name == "wta" else {}),
        )
    return tmp_path


def test_exact_results_supply_completion_bounds_without_start_proof(retained):
    batch = te.completed_batch(retained / "espn", retained / "wta", trusted_root=retained)
    assert len(batch["matches"]) == 119 and batch["startProofCount"] == 0 and not batch["readyForLive"]
    assert batch["observedAt"] == "2026-09-08T01:00:00+00:00"
    for row in batch["matches"]:
        assert "actualStartedAt" not in row and "finishedAt" not in row and "startEvidence" not in row
        assert (
            te.completion_bound(row["completionEvidence"], row, batch, evidence_kind="synthetic-qa").isoformat()
            == batch["observedAt"]
        )
    assert te.completed_batch(retained / "espn", retained / "wta", trusted_root=retained) == batch


def test_completion_tampering_and_swapped_provider_roles_fail(retained):
    with pytest.raises(ValueError, match="roles"):
        te.completed_batch(retained / "wta", retained / "espn", trusted_root=retained)
    batch = te.completed_batch(retained / "espn", retained / "wta", trusted_root=retained)
    row = batch["matches"][0]
    row["winner"] = row["playerB"] if row["winner"] == row["playerA"] else row["playerA"]
    with pytest.raises(ValueError, match="bundle"):
        te.completion_bound(row["completionEvidence"], row, batch, evidence_kind="synthetic-qa")
    with (retained / "espn/response.bin").open("ab") as f:
        f.write(b" ")
    with pytest.raises(ValueError, match="integrity"):
        te.completed_batch(retained / "espn", retained / "wta", trusted_root=retained)


def test_two_terminal_sources_disagree_explicitly_instead_of_disappearing(retained, monkeypatch):
    import json

    _, payload = source.read_capture(retained / "wta", trusted_root=retained)
    row = next(
        r
        for r in payload["matches"]
        if r.get("DrawMatchType") == "S"
        and r.get("DrawLevelType") == "M"
        and r.get("MatchState") == "F"
        and str(r.get("Winner")) in {"2", "3"}
    )
    row["Winner"] = "3" if str(row["Winner"]) == "2" else "2"
    raw = json.dumps(payload).encode()
    transport(monkeypatch, Response(raw, url=source.endpoint("wta", event="905", year=2026)))
    source.fetch_once(retained / "wta-changed", trusted_root=retained, source="wta", event="905", year=2026)
    batch = te.completed_batch(retained / "espn", retained / "wta-changed", trusted_root=retained)
    assert sum(r["status"] == "completed" for r in batch["matches"]) == 118
    conflicts = [r for r in batch["matches"] if r["status"] == "source-conflict"]
    assert len(conflicts) == 1 and "completionEvidence" not in conflicts[0]
    assert (
        te.resolve(
            [(conflicts[0], batch, "a" * 64)],
            original=conflicts[0],
            captured_at="2026-09-08T00:00:00Z",
            evidence_kind="synthetic-qa",
        )[1]
        == "sourceResultConflict"
    )
    assert len(batch["sourceIdentityRows"]) == 246


def test_earlier_completion_contradicts_later_start():
    row = complete_row()
    row["completionEvidence"] = completion(observed=datetime(2026, 9, 8, 14, 30, tzinfo=UTC))
    assert resolved(row)[1] == "timingNotProved"
