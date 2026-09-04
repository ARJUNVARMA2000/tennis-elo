"""Prospective receipt contract: no forecast revisions, timing leakage, or unpaired scoring."""
from __future__ import annotations

import copy
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from tennis_model.eval import prospective as p

NOW = datetime(2026, 9, 4, 12, tzinfo=UTC)


@pytest.fixture
def experiment(tmp_path, monkeypatch):
    class Predictor:
        def __init__(self, name, prob):
            self.artifact_id = name
            self.trained_at = (NOW - timedelta(days=1)).isoformat()
            self.prob = prob
            self.elo = SimpleNamespace(overall={"Player A": 1800, "Player B": 1700})

        def prediction_components(self, a, b, **context):
            return {"combiner": self.prob if a == "Player A" else 1 - self.prob}

    models = {"incumbent": Predictor("incumbent-id", .6), "candidate": Predictor("candidate-id", .7)}
    monkeypatch.setattr(p, "_now", lambda: NOW)
    monkeypatch.setattr(p, "load_predictor_artifact", lambda path, tour, **kw: models[path.stem])

    def save(model, path, **kw):
        path.write_text(model.artifact_id)
        p.predictor_envelope_path(path).write_text(model.trained_at)

    monkeypatch.setattr(p, "save_predictor_artifact", save)
    root = tmp_path / "trial"
    p.register(root, tour="atp", hypothesis="Candidate improves future log loss", min_pairs=2,
               incumbent=tmp_path / "incumbent.pkl", candidate=tmp_path / "candidate.pkl")
    row = {"espnId": "99-2026", "season": 2026, "round": "R32", "status": "scheduled",
           "playerA": "Player A", "playerB": "Player B", "surface": "Hard", "bestOf": 3,
           "earliestStartAt": "2026-09-04T16:00:00+00:00",
           "context": {"event": "Test Open", "as_of": "2026-09-04T16:00:00+00:00",
                       "indoor": False, "tier_k": 1.0, "round_order": 3}}
    schedule = {"tour": "atp", "observedAt": NOW.isoformat(), "sourceUrl": "https://example.com/schedule",
                "matches": [row]}
    return root, schedule, models


def result_payload(schedule):
    row = {**schedule["matches"][0], "status": "completed", "winner": "Player A",
           "actualStartedAt": "2026-09-04T16:05:00+00:00", "finishedAt": "2026-09-04T18:00:00+00:00"}
    return {"tour": "atp", "observedAt": "2026-09-04T19:00:00+00:00",
            "sourceUrl": "https://example.com/results", "matches": [row]}


def test_first_sighting_is_immutable_and_pairing_ignores_names_and_orientation(experiment, monkeypatch):
    root, schedule, models = experiment
    assert p.capture(root, schedule) == {"captured": 1}
    original = next((root / "receipts").glob("*.json")).read_bytes()
    models["candidate"].prob = .99
    assert p.capture(root, schedule) == {"alreadyCaptured": 1}
    assert next((root / "receipts").glob("*.json")).read_bytes() == original
    result = result_payload(schedule)
    row = result["matches"][0]
    row["playerA"], row["playerB"] = row["playerB"], row["playerA"]
    row["context"]["event"] = "New Sponsor Open"
    monkeypatch.setattr(p, "_now", lambda: NOW + timedelta(hours=8))
    report = p.grade(root, result)
    assert report["graded"] == 1
    assert report["paired"]["brier"]["delta"] == pytest.approx(.07)
    assert report["paired"]["logloss"]["se"] is None
    assert not report["targetReached"]
    assert (root / "results" / f'{report["resultEvidence"]}.json').exists()


@pytest.mark.parametrize("change, reason", [
    ({"status": "live"}, "notScheduled"),
    ({"earliestStartAt": "2026-09-04T12:04:00+00:00"}, "tooLateOrUncertain"),
    ({"context": {}}, "missingContext"),
    ({"playerB": "Unknown Player"}, "unpriced"),
])
def test_capture_exclusions_remain_in_the_source_receipt(experiment, change, reason):
    root, schedule, _ = experiment
    schedule["matches"][0].update(change)
    assert p.capture(root, schedule) == {reason: 1}
    assert not list((root / "receipts").glob("*.json"))
    assert list((root / "observations").glob("*.json"))


def test_rejects_changed_artifacts_stale_schedules_and_duplicate_identity(experiment):
    root, schedule, _ = experiment
    duplicate = copy.deepcopy(schedule)
    duplicate["matches"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        p.capture(root, duplicate)
    stale = {**schedule, "observedAt": "2026-09-04T11:00:00+00:00"}
    with pytest.raises(ValueError, match="ten minutes"):
        p.capture(root, stale)
    (root / "candidate.pkl").write_text("changed")
    with pytest.raises(ValueError, match="artifacts changed"):
        p.capture(root, schedule)


@pytest.mark.parametrize("change, reason", [
    ({"actualStartedAt": "2026-09-04T11:59:00+00:00"}, "timingNotProved"),
    ({"actualStartedAt": None}, "missingActualTiming"),
    ({"status": "retired"}, "retired"),
    ({"status": "walkover"}, "walkover"),
    ({"winner": "Unrelated Player"}, "winnerMismatch"),
])
def test_grade_requires_actual_start_and_completed_real_match(experiment, monkeypatch, change, reason):
    root, schedule, _ = experiment
    p.capture(root, schedule)
    result = result_payload(schedule)
    result["matches"][0].update(change)
    monkeypatch.setattr(p, "_now", lambda: NOW + timedelta(hours=8))
    report = p.grade(root, result)
    assert report["graded"] == 0
    assert report["excluded"] == {reason: 1}
    assert report["paired"]["logloss"]["delta"] is None


def test_wrong_event_stays_pending_and_corrupt_receipt_fails_closed(experiment, monkeypatch):
    root, schedule, _ = experiment
    p.capture(root, schedule)
    result = result_payload(schedule)
    result["matches"][0]["espnId"] = "another-event"
    monkeypatch.setattr(p, "_now", lambda: NOW + timedelta(hours=8))
    assert p.grade(root, result)["pending"] == 1
    receipt = next((root / "receipts").glob("*.json"))
    data = json.loads(receipt.read_bytes())
    data["probabilities"]["candidate"] = .99
    receipt.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="integrity"):
        p.grade(root, result)


def test_refuses_late_registration_reuse_and_nonreal_identity(experiment, monkeypatch):
    root, schedule, _ = experiment
    with pytest.raises(FileExistsError):
        p.register(root, tour="atp", hypothesis="another", incumbent=root / "incumbent.pkl",
                   candidate=root / "candidate.pkl")
    with pytest.raises(ValueError, match="real players"):
        p.match_key({**schedule["matches"][0], "playerA": "Qualifier"}, "atp")
    monkeypatch.setattr(p, "_now", lambda: NOW + timedelta(days=31))
    with pytest.raises(ValueError, match="horizon"):
        p.capture(root, schedule)


def test_inference_crossing_start_boundary_never_gets_a_receipt(experiment, monkeypatch):
    root, schedule, models = experiment
    def delayed(*args, **kwargs):
        monkeypatch.setattr(p, "_now", lambda: NOW + timedelta(hours=4))
        return {"combiner": .7}
    models["candidate"].prediction_components = delayed
    assert p.capture(root, schedule) == {"tooLateOrUncertain": 1}
    assert not list((root / "receipts").glob("*.json"))
