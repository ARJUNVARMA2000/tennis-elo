"""Fitted-artifact integration of the separately registered bounds evaluator."""

import copy
import math
from datetime import UTC, datetime, timedelta

import prospective_bounds as pb
import pytest
from tennis_model.eval import prospective_shadow as v1
from test_dynamic_shadow import shadow  # noqa: F401
from test_prospective_shadow import PROVENANCE, SOURCES, pair, schedule  # noqa: F401
from test_time_evidence import claim, completion


@pytest.fixture
def clock(monkeypatch):
    now = [datetime.now(UTC) + timedelta(seconds=2)]
    monkeypatch.setattr(pb, "_now", lambda: now[0])
    return now


def register(root, pair, **overrides):  # noqa: F811 - imported pytest fixture
    args = dict(
        trusted_root=root.parent.parent,
        incumbent=pair / "incumbent.pkl",
        candidate=pair / "candidate.shadow",
        provenance=PROVENANCE,
        hypothesis="Synthetic bounds QA only",
        sources=SOURCES,
        evidence_kind="synthetic-qa",
    )
    args.update(overrides)
    return pb.register(root, **args)


@pytest.fixture
def experiment(tmp_path, pair, clock):  # noqa: F811 - imported pytest fixture
    root = tmp_path / "pilot"
    register(root, pair)
    return root


def capture(root, batch):
    return pb.capture(root, batch, trusted_root=root.parent)


def grade(root, batch):
    return pb.grade(root, batch, trusted_root=root.parent)


def report(root):
    return pb.report(root, trusted_root=root.parent)


def result(batch, clock, *, exact=False):
    row = copy.deepcopy(batch["matches"][0])
    row.update(status="completed", winner=row["playerA"], score="6-3 6-4")
    start = row["earliestStartAt"]
    row["startEvidence"] = claim(
        row,
        kind="actual-start" if exact else "actual-start-interval",
        lower=start,
        upper=(pb._time(start) + timedelta(minutes=2)).isoformat(),
    )
    row["startEvidence"]["observedAt"] = clock[0].isoformat()
    row["completionEvidence"] = completion(row, clock[0])
    return {
        "tour": "wta",
        "observedAt": clock[0].isoformat(),
        "sourceUrl": "https://results.example.org/results",
        "matches": [row],
    }


def test_accumulated_results_first_forecast_and_fixed_endpoint(experiment, clock):
    first, second = schedule(clock), schedule(clock, "456", ("A", "C"))
    assert capture(experiment, first) == {"captured": 1} and capture(experiment, second) == {"captured": 1}
    key = pb.match_key(first["matches"][0], "wta")
    path = experiment / "receipts" / f"{key}.json"
    before = path.read_bytes()
    assert capture(experiment, first) == {"alreadyCaptured": 1} and path.read_bytes() == before
    clock[0] += timedelta(hours=4)
    assert grade(experiment, result(first, clock, exact=True))["graded"] == 1
    update = result(second, clock)
    final = grade(experiment, update)
    assert (final["graded"], final["pending"], final["resultBatches"]) == (2, 0, 2)
    assert grade(experiment, update)["resultBatches"] == 2
    p = pb._read(path, experiment)["probabilities"]["incumbent"]
    item = next(row for row in final["pairs"] if row["matchKey"] == key)
    assert item["scores"]["incumbent"]["logloss"] == pytest.approx(-math.log(p))
    assert item["timeProof"]["startLowerAt"] == pb._time(first["matches"][0]["earliestStartAt"]).isoformat()
    assert "finishedAt" not in item["timeProof"]
    registration = pb._read(experiment / "registration.json", experiment)
    clock[0] = pb._time(registration["settleUntil"])
    endpoint = report(experiment)
    saved = (experiment / "endpoint.json").read_bytes()
    assert endpoint["final"] and endpoint["graded"] == 2 and endpoint["evidenceKind"] == "synthetic-qa"
    with pytest.raises(ValueError, match="closed"):
        grade(experiment, update)
    clock[0] += timedelta(days=2)
    assert report(experiment) == endpoint and (experiment / "endpoint.json").read_bytes() == saved


def test_live_refused_before_files_and_schemas_separate(tmp_path, pair, experiment):  # noqa: F811
    target = tmp_path / "live"
    with pytest.raises(ValueError, match="no qualified live"):
        register(target, pair, evidence_kind="live")
    assert not target.exists()
    with pytest.raises(ValueError, match="schema"):
        v1.report(experiment, trusted_root=experiment.parent)


@pytest.mark.parametrize("change", ["code", "artifact", "mode", "policy"])
def test_registration_pins_code_artifacts_policy(experiment, monkeypatch, change):
    if change == "code":
        original = pb._contract

        def altered():
            value = original()
            value["external"]["time_evidence.py"] = "0" * 64
            return value

        monkeypatch.setattr(pb, "_contract", altered)
    elif change == "artifact":
        with (experiment / "candidate.shadow").open("ab") as f:
            f.write(b"bad")
    else:
        value = pb._read(experiment / "registration.json", experiment)
        value.pop("sha256")
        if change == "mode":
            value["evidenceKind"] = "live"
        else:
            value["policy"]["marginMinutes"] = 0
        (experiment / "registration.json").write_bytes(pb._bytes({**value, "sha256": pb._digest(value)}))
    with pytest.raises(ValueError):
        report(experiment)


@pytest.mark.parametrize(
    "change,expected",
    [
        ("earlier", "scheduleMovedEarlier"),
        ("identity", "sourceIdentityChanged"),
        ("retired", "conflictingResults"),
        ("winner", "conflictingResults"),
        ("score", "conflictingResults"),
    ],
)
def test_later_evidence_retained_and_conflicts_excluded(experiment, clock, change, expected):
    first = schedule(clock)
    first["matches"][0]["sourceEvidence"] = {"wtaMatchId": "abc"}
    capture(experiment, first)
    if change in {"earlier", "identity"}:
        revised = copy.deepcopy(first)
        if change == "earlier":
            start = (clock[0] + timedelta(hours=1)).isoformat()
            revised["matches"][0]["earliestStartAt"] = start
            revised["matches"][0]["context"]["as_of"] = start
        else:
            revised["matches"][0]["playerB"] = "C"
        capture(experiment, revised)
    clock[0] += timedelta(hours=4)
    original = result(first, clock)
    before = grade(experiment, original)
    if change in {"retired", "winner", "score"}:
        changed = copy.deepcopy(original)
        row = changed["matches"][0]
        if change == "retired":
            row["status"] = "retired"
        elif change == "winner":
            row["winner"] = "B"
        else:
            row["score"] = "6-0 6-0"
        before = grade(experiment, changed)
    assert before["excluded"][expected] >= 1 and before["graded"] == 0
    assert len(list((experiment / "results").glob("*.json"))) >= 1


def test_completion_only_excluded_until_start_claim(experiment, clock):
    scheduled = schedule(clock)
    capture(experiment, scheduled)
    clock[0] += timedelta(hours=4)
    complete = result(scheduled, clock)
    partial = copy.deepcopy(complete)
    partial["matches"][0].pop("startEvidence")
    assert grade(experiment, partial)["excluded"] == {"missingStartProof": 1}
    assert grade(experiment, complete)["graded"] == 1


def test_cross_week_interval_keeps_score_withholds_week_block(experiment, clock):
    sunday = clock[0] + timedelta(days=(6 - clock[0].weekday()) % 7 + 7)
    start = sunday.replace(hour=23, minute=59, second=0, microsecond=0)
    scheduled = schedule(clock)
    scheduled["matches"][0]["earliestStartAt"] = start.isoformat()
    scheduled["matches"][0]["context"]["as_of"] = start.isoformat()
    capture(experiment, scheduled)
    clock[0] = start + timedelta(hours=2)
    value = grade(experiment, result(scheduled, clock))
    assert value["graded"] == 1 and value["pairs"][0]["week"] is None
    assert value["paired"]["logloss"]["blocks"]["week"]["status"] == "ambiguous-start-week"
    assert value["paired"]["logloss"]["blocks"]["event"]["status"] != "ambiguous-start-week"


@pytest.mark.parametrize("change", ["stale", "future", "host", "duplicate"])
def test_source_admission_stays_strict(experiment, clock, change):
    scheduled = schedule(clock)
    if change == "stale":
        clock[0] += timedelta(minutes=11)
    elif change == "future":
        scheduled["observedAt"] = (clock[0] + timedelta(seconds=1)).isoformat()
    elif change == "host":
        scheduled["sourceUrl"] = "https://unregistered.example.org/source"
    else:
        scheduled["matches"] *= 2
    with pytest.raises(ValueError):
        capture(experiment, scheduled)
    assert not list((experiment / "receipts").glob("*.json"))


def test_post_inference_margin_checked(experiment, clock, monkeypatch):
    scheduled = schedule(clock)
    start = (clock[0] + timedelta(minutes=6)).isoformat()
    scheduled["matches"][0]["earliestStartAt"] = start
    scheduled["matches"][0]["context"]["as_of"] = start
    load = pb._models

    def slow(root, registration):
        models = load(root, registration)
        model = models["candidate"]
        predict = model.prediction_components

        def infer(*args, **kwargs):
            value = predict(*args, **kwargs)
            clock[0] += timedelta(minutes=2)
            return value

        model.prediction_components = infer
        return models

    monkeypatch.setattr(pb, "_models", slow)
    assert capture(experiment, scheduled) == {"tooLateOrUncertain": 1}
    assert not list((experiment / "receipts").glob("*.json"))


def test_identity_only_source_change_invalidates_old_forecast(experiment, clock):
    scheduled = schedule(clock)
    scheduled["matches"][0]["sourceEvidence"] = {"wtaMatchId": "source-1"}
    capture(experiment, scheduled)
    clock[0] += timedelta(hours=4)
    batch = result(scheduled, clock)
    assert grade(experiment, batch)["graded"] == 1
    changed = copy.deepcopy(batch["matches"][0])
    changed["playerB"] = "C"
    update = {**batch, "matches": [], "sourceIdentityRows": [changed]}
    final = grade(experiment, update)
    assert final["graded"] == 0 and final["excluded"] == {"sourceIdentityChanged": 1}


@pytest.mark.parametrize("case", ["wrong-format", "wrong-provenance"])
def test_role_and_provenance_rejected_before_experiment(tmp_path, pair, case):  # noqa: F811
    root = tmp_path / "invalid"
    overrides = (
        {"incumbent": pair / "candidate.shadow"}
        if case == "wrong-format"
        else {"provenance": {**PROVENANCE, "selection": "0" * 64}}
    )
    with pytest.raises(pb.a.PredictorArtifactError):
        register(root, pair, **overrides)
    assert not root.exists()


def test_result_intake_crossing_deadline_does_not_publish(experiment, clock, monkeypatch):
    registration = pb._read(experiment / "registration.json", experiment)
    deadline = pb._time(registration["settleUntil"])
    clock[0] = deadline - timedelta(seconds=1)
    batch = {
        "tour": "wta",
        "observedAt": clock[0].isoformat(),
        "sourceUrl": "https://results.example.org/results",
        "matches": [],
    }
    original = pb._batch

    def delayed(*args):
        value = original(*args)
        clock[0] = deadline
        return value

    monkeypatch.setattr(pb, "_batch", delayed)
    with pytest.raises(ValueError, match="closed"):
        grade(experiment, batch)
    assert not list((experiment / "results").glob("*.json"))


def test_symlink_forecast_destination_rejected_without_replacing_target(experiment, clock, tmp_path):
    batch = schedule(clock)
    target = tmp_path / "protected"
    target.write_text("preserve")
    key = pb.match_key(batch["matches"][0], "wta")
    (experiment / "receipts" / f"{key}.json").symlink_to(target)
    with pytest.raises(pb.a.PredictorArtifactError):
        capture(experiment, batch)
    assert target.read_text() == "preserve"
