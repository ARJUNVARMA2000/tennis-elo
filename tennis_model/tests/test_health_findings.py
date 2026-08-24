"""Contract tests for stable, typed data-health findings.

These deliberately treat prose and evidence as mutable presentation. Incident identity,
gate policy, and reporter hand-off must remain stable when either changes.
"""

from __future__ import annotations

import json
import math
import sys

import pytest

from tennis_model.data import health


def _finding(**overrides) -> health.HealthFinding:
    values = {
        "code": "output.tournament.duplicate_card",
        "severity": "error",
        "scope": "output",
        "tour": "atp",
        "entity": "espn:888-2026",
        "evidence": {"count": 2},
        "message": "atp: duplicate tournament card",
    }
    values.update(overrides)
    return health.HealthFinding(**values)


def test_fingerprint_is_identity_only_and_revision_tracks_mutable_observation():
    original = _finding()
    rewritten = _finding(
        severity="warning",
        evidence={"count": 3, "names": ["A", "B"]},
        message="wording changed completely",
    )

    assert rewritten.fingerprint == original.fingerprint
    assert rewritten.revision != original.revision


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("code", "output.tournament.other_code"),
        ("tour", "wta"),
        ("entity", "espn:999-2026"),
    ],
)
def test_identity_fields_change_the_fingerprint(field, value):
    assert _finding(**{field: value}).fingerprint != _finding().fingerprint


@pytest.mark.parametrize(
    "overrides",
    [
        {"code": "tournament_duplicate"},
        {"code": "source.tournament.duplicate_card", "scope": "output"},
        {"severity": "critical"},
        {"tour": "itf"},
        {"tour": None},
        {"entity": ""},
        {"message": ""},
        {"evidence": []},
        {"evidence": {"value": math.nan}},
    ],
)
def test_invalid_findings_fail_at_the_producer_boundary(overrides):
    with pytest.raises(ValueError):
        _finding(**overrides)


def test_cross_findings_have_no_single_tour_and_use_cross_code_namespace():
    finding = _finding(
        code="cross.tournament.surface_split",
        scope="cross",
        tour=None,
        entity="espn:888-2026",
    )
    assert finding.as_dict()["tour"] is None
    with pytest.raises(ValueError):
        _finding(code="cross.tournament.surface_split", scope="cross", tour="atp")


def test_typed_gate_policy_does_not_depend_on_message_substrings():
    formerly_advisory_words = "same event more than once; no live/upcoming event; is empty"
    assert health._gate_blocks(_finding(message=formerly_advisory_words))
    assert not health._gate_blocks(_finding(severity="warning", message="catastrophic corruption"))
    assert not health._gate_blocks(_finding(severity="info", message="catastrophic corruption"))


def test_duplicate_observations_coalesce_under_one_fingerprint():
    first = _finding(evidence={"name": "A"}, message="first observation")
    second = _finding(evidence={"name": "B"}, message="second observation")
    serialized = health._serialize_findings([first, second])

    assert len(serialized) == 1
    assert serialized[0]["fingerprint"] == first.fingerprint
    assert serialized[0]["evidence"] == {
        "occurrences": [{"name": "A"}, {"name": "B"}],
    }
    assert health._serialize_findings([second, first])[0]["revision"] == serialized[0]["revision"]


def test_structured_report_reader_rejects_forged_identity_and_revision():
    raw = _finding().as_dict()
    report = {"findings": [raw]}
    assert health._structured_findings(report) == [raw]

    forged_identity = {**raw, "fingerprint": "hf1:" + "0" * 64}
    assert health._structured_findings({"findings": [forged_identity]}) == []

    forged_revision = {**raw, "revision": "hr1:" + "0" * 64}
    assert health._structured_findings({"findings": [forged_revision]}) == []


def test_transitions_distinguish_onset_update_and_recovery():
    old = _finding().as_dict()
    updated = _finding(evidence={"count": 3}).as_dict()
    added = _finding(
        code="output.bracket.geometry_invalid",
        entity="bracket:888-2026",
    ).as_dict()

    transitions = health._finding_transitions([updated, added], [old])
    assert transitions == {
        "activated": [added["fingerprint"]],
        "updated": [old["fingerprint"]],
        "resolved": [],
    }
    assert health._finding_transitions([], [old])["resolved"] == [old["fingerprint"]]


def test_informational_findings_are_not_actionable_transitions():
    info = _finding(severity="info").as_dict()
    assert health._finding_transitions([info], []) == {
        "activated": [], "updated": [], "resolved": [],
    }


def _write_report(path, findings: list[dict], *, ok: bool) -> None:
    path.write_text(json.dumps({
        "generated": "2026-08-23",
        "findingSchema": health.FINDING_SCHEMA,
        "findingSnapshot": "authoritative",
        "ok": ok,
        "findings": findings,
    }), encoding="utf-8")


def test_real_findings_cli_round_trip_and_body_markers(tmp_path, monkeypatch, capsys):
    finding = _finding().as_dict()
    report_path = tmp_path / "health.json"
    _write_report(report_path, [finding], ok=False)
    monkeypatch.setenv("HEALTH_REPORT", str(report_path))
    monkeypatch.setenv("FINDING_SNAPSHOT", "authoritative")

    monkeypatch.setattr(sys, "argv", ["health", "--findings-json"])
    assert health.main() == 0
    assert json.loads(capsys.readouterr().out) == [finding]

    monkeypatch.setenv("FINDING_KEY", finding["fingerprint"])
    monkeypatch.setattr(sys, "argv", ["health", "--finding-body"])
    assert health.main() == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == [
        f"<!-- data-health-key: {finding['fingerprint']} -->",
        f"<!-- data-health-revision: {finding['revision']} -->",
    ]

    monkeypatch.setenv("FINDING_KEY", "hf1:" + "f" * 64)
    assert health.main() == 1
    assert "is not active" in capsys.readouterr().out


def test_findings_cli_accepts_the_typed_predeploy_gate_report(tmp_path, monkeypatch, capsys):
    finding = _finding().as_dict()
    report_path = tmp_path / "predeploy-gate.json"
    report_path.write_text(json.dumps({
        "schema": "predeploy-gate-v1",
        "generatedAt": "2026-08-23T12:00:00Z",
        "ok": False,
        "findingSchema": health.FINDING_SCHEMA,
        "findingSnapshot": "partial",
        "findingsOk": False,
        "findings": [finding],
        "blocking": [{"scope": "atp", "problem": finding["message"],
                      "finding": finding}],
        "advisory": [],
    }), encoding="utf-8")
    monkeypatch.setenv("HEALTH_REPORT", str(report_path))
    monkeypatch.setenv("FINDING_SNAPSHOT", "partial")
    monkeypatch.setattr(sys, "argv", ["health", "--findings-json"])

    assert health.main() == 0
    assert json.loads(capsys.readouterr().out) == [finding]

    monkeypatch.setenv("FINDING_SNAPSHOT", "authoritative")
    assert health.main() == 1
    assert "structured health findings" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("findings", "ok"),
    [
        ([], False),
        ([_finding().as_dict()], True),
        ([_finding().as_dict() | {"fingerprint": "hf1:" + "0" * 64}], False),
    ],
)
def test_findings_cli_rejects_corrupt_or_ok_mismatched_reports(
    findings, ok, tmp_path, monkeypatch, capsys,
):
    report_path = tmp_path / "health.json"
    _write_report(report_path, findings, ok=ok)
    monkeypatch.setenv("HEALTH_REPORT", str(report_path))
    monkeypatch.setattr(sys, "argv", ["health", "--findings-json"])

    assert health.main() == 1
    assert "structured health findings" in capsys.readouterr().out


def test_finding_issue_body_is_bounded_without_losing_identity_markers():
    finding = _finding(
        evidence={"rows": ["x" * 500 for _ in range(500)]},
        message="observation " * 20_000,
    ).as_dict()
    body = health.format_finding_issue_body(
        finding, {"generated": "2026-08-23"},
        run_url="https://example/run", health_url="https://example/health",
    )

    assert len(body) <= health.FINDING_ISSUE_BODY_MAX_CHARS
    assert body.splitlines()[:2] == [
        f"<!-- data-health-key: {finding['fingerprint']} -->",
        f"<!-- data-health-revision: {finding['revision']} -->",
    ]
    assert "truncated" in body
