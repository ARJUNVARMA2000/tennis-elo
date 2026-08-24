"""Production-shape replays for recurring data-health incidents.

The manifest supplies only the incident delta.  Each variant is laid over the same
minimal, internally consistent output/source generation and then crosses the same final
filesystem readers and finding functions used by the health sentinel.  The paired clean
variant is load-bearing: it proves the expected code comes from the historical defect,
not from a permanently-red synthetic fixture.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path, PurePosixPath

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import tennis_model.data.health as health
from test_health import _healthy_data, _healthy_shards

MANIFEST_PATH = Path(__file__).parent / "fixtures" / "health_incident_replays.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
CASES = MANIFEST["cases"]

_CASE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
_ALLOWED_ROOTS = frozenset({"output", "live", "fresh"})
_ALLOWED_OPS = frozenset({"set_json", "write_json", "write_text"})


def _safe_target(target: object) -> bool:
    if not isinstance(target, str):
        return False
    path = PurePosixPath(target)
    return (
        not path.is_absolute()
        and path.as_posix() == target
        and len(path.parts) >= 2
        and path.parts[0] in _ALLOWED_ROOTS
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def test_incident_replay_manifest_contract() -> None:
    assert MANIFEST["schema"] == "health-incident-replay-v1"
    assert len(CASES) == 6
    ids = [case["id"] for case in CASES]
    codes = [case["expected"]["code"] for case in CASES]
    assert len(ids) == len(set(ids)) and all(_CASE_ID_RE.fullmatch(case_id) for case_id in ids)
    assert len(codes) == len(set(codes)), "one manifest case owns each stable incident code"

    for case in CASES:
        assert isinstance(case.get("description"), str) and case["description"].strip()
        assert case["tour"] in {"atp", "wta"}
        assert case["seam"] in {"source", "output"}
        assert pd.notna(pd.to_datetime(case["asOf"], errors="coerce"))

        history = case["history"]
        assert isinstance(history.get("issues"), list)
        assert all(isinstance(issue, int) and issue > 0 for issue in history["issues"])
        assert history.get("commits") and all(
            isinstance(commit, str) and _COMMIT_RE.fullmatch(commit)
            for commit in history["commits"]
        )

        expected = case["expected"]
        assert set(expected) == {"code", "severity", "scope", "entity", "channel"}
        assert expected["severity"] in {"error", "warning", "info"}
        assert expected["scope"] == case["seam"]
        assert expected["code"].startswith(f"{expected['scope']}.")
        assert isinstance(expected["entity"], str) and expected["entity"].strip()
        assert expected["channel"] in {"predeploy", "sentinel", "informational"}

        assert set(case["variants"]) == {"broken", "clean"}
        for variant in case["variants"].values():
            assert set(variant) == {"patches"}
            assert isinstance(variant["patches"], list) and variant["patches"]
            for patch in variant["patches"]:
                assert patch.get("op") in _ALLOWED_OPS
                assert _safe_target(patch.get("target"))
                suffix = PurePosixPath(patch["target"]).suffix
                if patch["op"] == "write_text":
                    assert suffix == ".csv" and isinstance(patch.get("value"), str)
                else:
                    assert suffix == ".json"
                if patch["op"] == "set_json":
                    assert isinstance(patch.get("pointer"), str)
                    assert patch["pointer"].startswith("/")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _clean_receipt(tour: str, as_of: str) -> dict:
    return {
        "schema": "espn-acquisition-v1",
        "tour": tour,
        "completedAt": f"{as_of}T12:00:00Z",
        "status": "success",
        "eventCount": 1,
        "queries": {"attempted": 28, "succeeded": 28, "failed": 0},
        "overlay": {
            "status": "updated",
            "updatedFiles": ["live.csv", "fields.json", "upcoming.csv"],
            "retainedFiles": [],
            "lastGoodAt": f"{as_of}T12:00:00Z",
        },
    }


def _materialize_base(root: Path, tour: str, as_of: str) -> None:
    data = copy.deepcopy(_healthy_data())
    shards = copy.deepcopy(_healthy_shards())
    threshold = health.WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None
    generation_date = (pd.Timestamp(as_of) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    generation = f"{generation_date}T04:30:00Z"

    data["meta"].update(
        dualStateThreshold=threshold,
        dualStateReady=threshold is not None,
        lastUpdated=f"{as_of}T00:00:00Z",
        modelTrainedAt=generation,
    )
    for index_name in ("matrix-index", "profile-index", "scenario-index"):
        data[index_name]["generation"] = generation
    for shard in shards.values():
        shard["generation"] = generation
    data["method"]["tour"] = tour
    data["method"]["stateGate"].update(
        enabled=threshold is not None,
        minMainMatches=threshold,
    )
    data["event_coverage"].update(tour=tour, buildDate=as_of)
    data["performance"]["tour"] = tour
    if tour == "wta":
        for tournament in data["tournaments"]:
            tournament["level"] = "WTA 250"
        for bracket in data["brackets"]:
            bracket["level"] = "WTA 250"
    upcoming = copy.deepcopy(data["upcoming"][0])
    upcoming.update(
        matchId="v2|espn:1-2026|2026|R32|p0|p1",
        espnId="1-2026",
        date=as_of,
        round="R32",
        surface="Grass",
        bestOf=3,
        level="WTA 250" if tour == "wta" else "ATP 250",
    )
    detail = {
        "matchId": upcoming["matchId"],
        "components": upcoming.pop("components"),
        "evidence": upcoming.pop("evidence"),
        "forecast": upcoming.pop("forecast", None),
    }
    event_file = "upcoming-event-replay.json"
    evidence_file = "upcoming-evidence-replay.json"
    data["upcoming-index"] = {
        "schema": "upcoming-v2",
        "schemaVersion": 2,
        "generation": generation,
        "count": 1,
        "events": [
            {
                "name": "Test Open",
                "espnId": "1-2026",
                "surface": "Grass",
                "level": "WTA 250" if tour == "wta" else "ATP 250",
                "count": 1,
                "file": event_file,
                "evidenceFile": evidence_file,
            }
        ],
        "highlights": [],
    }
    shards[event_file] = {
        "schema": "upcoming-event-v1",
        "generation": generation,
        "matches": [upcoming],
    }
    shards[evidence_file] = {
        "schema": "upcoming-evidence-v1",
        "generation": generation,
        "details": [detail],
    }
    data["ratings_history"] = {}
    data["draws"] = {"field": [], "bestOf": {}, "surfaces": []}

    output = root / "output" / tour
    for stem in (*health._REQUIRED_OUTPUTS, *health._OPTIONAL_OUTPUTS):
        if stem in data:
            _write_json(output / f"{stem}.json", data[stem])
    for filename, shard in shards.items():
        _write_json(output / filename, shard)

    live = root / "live" / tour
    _write_json(live / "tournament_draws.json", {})
    _write_json(live / "espn_acquisition.json", _clean_receipt(tour, as_of))

    fresh = root / "fresh" / tour
    fresh.mkdir(parents=True, exist_ok=True)
    stamp = pd.Timestamp(as_of)
    (fresh / f"{stamp.year}.csv").write_text(
        f"tourney_date\n{stamp.year}/{stamp.month}/{stamp.day}\n", encoding="utf-8"
    )

    charting = root / "charting"
    charting.mkdir(parents=True, exist_ok=True)
    (charting / f"charting-{health._GENDER[tour]}-stats-Overview.csv").write_text(
        f"match_id\n{stamp.strftime('%Y%m%d')}-replay\n", encoding="utf-8"
    )


def _target_path(root: Path, tour: str, target: str) -> Path:
    assert _safe_target(target)
    parts = PurePosixPath(target).parts
    return root / parts[0] / tour / Path(*parts[1:])


def _pointer_token(raw: str) -> str:
    return raw.replace("~1", "/").replace("~0", "~")


def _set_json_pointer(document: object, pointer: str, value: object) -> None:
    tokens = [_pointer_token(token) for token in pointer[1:].split("/")]
    parent = document
    for token in tokens[:-1]:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    final = tokens[-1]
    if isinstance(parent, list):
        parent[int(final)] = value
    else:
        parent[final] = value


def _apply_patch(root: Path, tour: str, patch: dict) -> None:
    target = _target_path(root, tour, patch["target"])
    operation = patch["op"]
    if operation == "write_text":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(patch["value"], encoding="utf-8")
    elif operation == "write_json":
        _write_json(target, patch["value"])
    else:
        document = json.loads(target.read_text(encoding="utf-8"))
        _set_json_pointer(document, patch["pointer"], patch["value"])
        _write_json(target, document)


def _bind_filesystem(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(health, "OUTPUT_DIR", root / "output")
    monkeypatch.setattr(health, "DATA_DIR", root / "data")
    monkeypatch.setattr(health, "WEB_DATA_DIR", root / "web")
    monkeypatch.setattr(health, "CHARTING_DIR", root / "charting")
    monkeypatch.setattr(health, "output_dir", lambda tour: root / "output" / tour)
    monkeypatch.setattr(health, "live_dir", lambda tour: root / "live" / tour)
    monkeypatch.setattr(health, "fresh_dir", lambda tour: root / "fresh" / tour)


def _source_frame(as_of: str) -> pd.DataFrame:
    # At least 100 rows avoids the intentionally-informational early-season coverage note.
    return pd.DataFrame(
        {
            "date": pd.to_datetime([as_of] * 100),
            "completed": [True] * 100,
            "has_stats": [True] * 100,
        }
    )


def _run_variant(
    case: dict,
    variant: str,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[health.HealthFinding], list[str], object]:
    tour, as_of = case["tour"], case["asOf"]
    _materialize_base(root, tour, as_of)
    for patch in case["variants"][variant]["patches"]:
        _apply_patch(root, tour, patch)
    _bind_filesystem(monkeypatch, root)
    now = pd.Timestamp(as_of)

    if case["seam"] == "source":
        state = health._tour_health_from_frame(tour, _source_frame(as_of), now)
        findings = health.source_findings(tour, state, now)
        legacy = health.problems(tour, state, now)
    else:
        state = health.read_outputs(tour)
        previous = case.get("previousOutput")
        findings = health.output_findings(tour, state, now, previous)
        legacy = health.output_problems(tour, state, now, previous)

    assert legacy == [finding.message for finding in findings if finding.severity != "info"]
    return findings, legacy, state


def _run_predeploy_gate(
    case: dict,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, dict]:
    """Cross the real CLI gate/report seam at the replay's historical observation date."""
    _bind_filesystem(monkeypatch, root)
    fixed_now = pd.Timestamp(f"{case['asOf']}T12:00:00Z").to_pydatetime()

    class _FixedDatetime:
        @staticmethod
        def now(tz=None):
            return fixed_now.replace(tzinfo=None) if tz is None else fixed_now.astimezone(tz)

    report_path = root / "predeploy-gate.json"
    monkeypatch.setattr(health, "datetime", _FixedDatetime)
    monkeypatch.setattr(health, "TOURS", (case["tour"],))
    monkeypatch.setattr(
        health,
        "_lineage_observation",
        lambda **_kwargs: ({}, {case["tour"]: []}),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["health", "--gate", "--gate-report", str(report_path)],
    )
    result = health.main()
    return result, json.loads(report_path.read_text(encoding="utf-8"))


def _run_sentinel(
    case: dict,
    root: Path,
    replay_state: object,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, dict]:
    """Cross the real sentinel serialization/write path with the minimized replay state."""
    _bind_filesystem(monkeypatch, root)
    now = pd.Timestamp(case["asOf"])
    fixed_now = pd.Timestamp(f"{case['asOf']}T12:00:00Z").to_pydatetime()

    class _FixedDatetime:
        @staticmethod
        def now(tz=None):
            return fixed_now.replace(tzinfo=None) if tz is None else fixed_now.astimezone(tz)

    if case["seam"] == "source":
        source_state = copy.deepcopy(replay_state)
    else:
        source_state = health._tour_health_from_frame(
            case["tour"], _source_frame(case["asOf"]), now
        )

    previous_output = case.get("previousOutput")
    report_path = root / "output" / "health.json"
    if previous_output is not None:
        _write_json(
            report_path,
            {
                "tours": {case["tour"]: {"output": previous_output}},
                "findings": [],
            },
        )

    monkeypatch.setattr(health, "datetime", _FixedDatetime)
    monkeypatch.setattr(health, "TOURS", (case["tour"],))
    monkeypatch.setattr(
        health,
        "_lineage_observation",
        lambda **_kwargs: ({}, {case["tour"]: []}),
    )
    monkeypatch.setattr(
        health,
        "tour_health",
        lambda _tour, _now: copy.deepcopy(source_state),
    )
    monkeypatch.setattr(sys, "argv", ["health"])
    result = health.main()
    return result, json.loads(report_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_incident_replay_bites_only_broken_variant(
    case: dict,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken, _broken_legacy, broken_state = _run_variant(
        case, "broken", tmp_path / "broken", monkeypatch
    )
    clean, _clean_legacy, clean_state = _run_variant(
        case, "clean", tmp_path / "clean", monkeypatch
    )
    expected = case["expected"]

    hits = [finding for finding in broken if finding.code == expected["code"]]
    assert len(hits) == 1, [finding.as_dict() for finding in broken]
    assert not any(finding.code == expected["code"] for finding in clean), [
        finding.as_dict() for finding in clean
    ]
    assert not [finding.as_dict() for finding in clean if finding.severity != "info"], [
        finding.as_dict() for finding in clean
    ]
    hit = hits[0]
    assert (hit.code, hit.severity, hit.scope, hit.entity) == (
        expected["code"],
        expected["severity"],
        expected["scope"],
        expected["entity"],
    )
    assert hit.fingerprint.startswith("hf1:") and len(hit.fingerprint) == 68

    if expected["channel"] == "predeploy":
        broken_result, broken_report = _run_predeploy_gate(
            case, tmp_path / "broken", monkeypatch
        )
        clean_result, clean_report = _run_predeploy_gate(
            case, tmp_path / "clean", monkeypatch
        )
        expected_bucket = "blocking" if expected["severity"] == "error" else "advisory"
        other_bucket = "advisory" if expected_bucket == "blocking" else "blocking"

        assert broken_report["schema"] == "predeploy-gate-v1"
        assert [
            item for item in broken_report[expected_bucket]
            if item["finding"]["code"] == expected["code"]
        ]
        assert not [
            item for item in broken_report[other_bucket]
            if item["finding"]["code"] == expected["code"]
        ]
        assert broken_result == (1 if expected_bucket == "blocking" else 0)
        assert clean_result == 0
        assert clean_report["blocking"] == []
        assert not [
            item for bucket in ("blocking", "advisory")
            for item in clean_report[bucket]
            if item["finding"]["code"] == expected["code"]
        ]
    else:
        broken_result, broken_report = _run_sentinel(
            case, tmp_path / "broken", broken_state, monkeypatch
        )
        clean_result, clean_report = _run_sentinel(
            case, tmp_path / "clean", clean_state, monkeypatch
        )
        report_hits = [
            finding for finding in broken_report["findings"]
            if finding["code"] == expected["code"]
        ]

        assert broken_result == clean_result == 0
        assert len(report_hits) == 1
        assert (
            report_hits[0]["code"],
            report_hits[0]["severity"],
            report_hits[0]["scope"],
            report_hits[0]["entity"],
        ) == (
            expected["code"],
            expected["severity"],
            expected["scope"],
            expected["entity"],
        )
        assert broken_report["ok"] is (expected["channel"] == "informational")
        assert clean_report["ok"] is True
        assert not [
            finding for finding in clean_report["findings"]
            if finding["severity"] != "info"
        ]

    # The population comparator is deliberately unavailable to the stateless predeploy gate.
    if expected["channel"] == "sentinel" and expected["code"].startswith("output.population."):
        gate_findings = health.output_findings(
            case["tour"], broken_state, pd.Timestamp(case["asOf"]), prev=None
        )
        assert not any(finding.code == expected["code"] for finding in gate_findings)
