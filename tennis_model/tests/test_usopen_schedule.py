"""Exact public schedule samples plus explicitly synthetic failure/revision cases."""
import copy
import http.client
import io
import json
import urllib.error
from collections import Counter
from datetime import datetime
from email.message import Message

import pytest
import time_evidence
import usopen_schedule as u
from tennis_model.model import artifact as a


@pytest.fixture
def samples():
    values = {}
    for name in ("uso-schedule-days", "uso-schedule-16", "uso-schedule-17"):
        entry, raw = u._fixture(name)
        receipt = {**entry["receipt"], "outcome": "ok", "sha256": "fixture-only"}
        values[name] = (receipt, json.loads(raw))
    return values


def extract(samples, day=17):
    cr, cp = samples["uso-schedule-days"]
    dr, dp = samples[f"uso-schedule-{day}"]
    return u.normalize(cp, dp, year=2026, day=day, receipt=dr, catalogue_receipt=cr)


def ws(samples, day=17):
    return [m for c in samples[f"uso-schedule-{day}"][1]["courts"] for m in c["matches"] if m.get("eventCode") == "WS"]


def test_real_sample_exact_rows_clocks_and_census(samples):
    a16, a17 = extract(samples, 16), extract(samples)
    rows = a16["observations"] + a17["observations"]
    assert [a16["coverage"]["allRows"], a17["coverage"]["allRows"]] == [72, 60]
    assert len(rows) == 6
    assert Counter(r["publishedTimeKind"] for r in rows) == {
        "first-match-session-start": 5, "explicit-not-before": 1}
    assert next(r for r in rows if r["sourceMatchId"] == "2408")["publishedTimeUTC"] == "2026-09-07T18:30:00+00:00"
    assert [(r["courtId"], r["session"], r["publishedTimeUTC"]) for r in a17["observations"]] == [
        ("AA", 1, "2026-09-08T15:30:00+00:00"), ("AA", 2, "2026-09-08T23:00:00+00:00")]
    assert a17["anomalies"] == ["catalogue-epoch-date-disagreement"]
    assert all(r["qualification"] == "schedule-observation-only" and not r["actualStartVerified"] for r in rows)
    assert any(e["reason"] == "intentional-blank" for e in a16["exclusions"])
    assert a16["coverage"]["completeForAbsenceComparison"] and a17["coverage"]["completeForAbsenceComparison"]


@pytest.mark.parametrize("mutation", ["duplicates", "bad-id", "edition", "timezone", "date", "session", "order", "html", "courts", "round-pair"])
def test_malformed_complete_orders_fail_closed(samples, mutation):
    payload = samples["uso-schedule-17"][1]
    row = ws(samples)[0]
    if mutation == "duplicates":
        ws(samples)[1]["match_id"] = row["match_id"]
    elif mutation == "bad-id":
        row["match_id"] = "../bad"
    elif mutation == "edition":
        payload["day"] = 18
    elif mutation == "timezone":
        payload["courts"][0]["startEpoch"] += 3600
    elif mutation == "date":
        payload["displayDate"] = "Day 10: Monday, September 8"
    elif mutation == "session":
        payload["courts"][1]["session"] = payload["courts"][0]["session"]
    elif mutation == "order":
        payload["courts"][0]["matches"][1]["order"] = 1
    elif mutation == "html":
        samples["uso-schedule-17"] = (samples["uso-schedule-17"][0], "<html>shell</html>")
    elif mutation == "courts":
        payload["courts"] = []
    else:
        other = ws(samples)[1]
        other["team1"], other["team2"] = copy.deepcopy(row["team1"]), copy.deepcopy(row["team2"])
    with pytest.raises(ValueError):
        extract(samples)


@pytest.mark.parametrize("mutation", ["self", "unresolved", "doubles", "missing-round", "count", "age", "no-http-date"])
def test_partial_or_stale_orders_never_prove_absence(samples, mutation):
    row = ws(samples)[0]
    if mutation == "self":
        row["team2"][0]["idA"] = row["team1"][0]["idA"]
    elif mutation == "unresolved":
        row["team2"][0]["idA"] = None
    elif mutation == "doubles":
        row["team2"][0]["idB"] = "wta123"
    elif mutation == "missing-round":
        row["roundCode"] = row["roundName"] = None
    elif mutation == "count":
        next(r for r in samples["uso-schedule-days"][1]["eventDays"] if r["tournDay"] == 17)["matchCount"] -= 1
    elif mutation == "age":
        samples["uso-schedule-17"][0]["headers"]["age"] = "601"
    else:
        samples["uso-schedule-17"][0]["headers"].pop("date")
    assert not extract(samples)["coverage"]["completeForAbsenceComparison"]


@pytest.mark.parametrize("mutation", ["sequence", "comment", "conjunction", "clock", "before-session"])
def test_uncertain_timing_never_invents_start(samples, mutation):
    row = ws(samples, 16)[-1]
    assert row["match_id"] == "2408"
    if mutation == "sequence":
        row["notBefore"] = None
    elif mutation in ("comment", "conjunction"):
        row[mutation] = "After previous match"
    elif mutation == "clock":
        row["notBefore"] = "about 3 pm"
    else:
        row["notBefore"] = "9:30 AM"
    result = next(r for r in extract(samples, 16)["observations"] if r["sourceMatchId"] == "2408")
    assert result["publishedTimeUTC"] is None
    assert result["publishedTimeKind"] == ("sequence-only" if mutation == "sequence" else "unresolved-time")


class Response(io.BytesIO):
    def __init__(self, raw, url, status=200, headers=None):
        super().__init__(raw)
        self.url, self.status = url, status
        self.headers = Message()
        for k, v in (headers or {"content-type": "application/json", "content-length": str(len(raw)),
                                "date": "Tue, 08 Sep 2026 04:00:00 GMT"}).items():
            self.headers[k] = v

    def geturl(self):
        return self.url


def transport(monkeypatch, responses, stamp="2026-09-08T04:00:00+00:00"):
    requests = []
    class Opener:
        def open(self, request, timeout):
            requests.append(request.full_url)
            assert timeout == 25 and request.get_header("Accept-encoding") == "identity"
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            assert request.full_url == response.geturl() or response.geturl().startswith("https://unexpected")
            return response
    monkeypatch.setattr(u.urllib.request, "build_opener", lambda *args: Opener())
    monkeypatch.setattr(u.p, "_now", lambda: datetime.fromisoformat(stamp))
    return requests


def acquisition(tmp_path, monkeypatch, samples, name, minute=0):
    stamp = f"2026-09-08T04:{minute:02}:00+00:00"
    responses = []
    for key, day in [("uso-schedule-days", None), ("uso-schedule-17", 17)]:
        raw = json.dumps(samples[key][1]).encode()
        response = Response(raw, u.endpoint(2026, day))
        response.headers.replace_header("date", datetime.fromisoformat(stamp).strftime("%a, %d %b %Y %H:%M:%S GMT"))
        responses.append(response)
    requests = transport(monkeypatch, responses, stamp)
    root = tmp_path / name
    result = u.collect(root, trusted_root=tmp_path, year=2026, day=17)
    assert len(requests) == 2 and result["report"]["outcome"] == "observed"
    return root


def test_real_retained_import_replays_exactly_and_is_immutable(tmp_path):
    first = u.import_retained(tmp_path / "day16", trusted_root=tmp_path, day=16)
    second = u.import_retained(tmp_path / "day17", trusted_root=tmp_path, day=17)
    assert first["report"]["coverage"]["WTAObservations"] == 4
    assert second["report"]["coverage"]["WTAObservations"] == 2
    result = u.history([tmp_path / "day17", tmp_path / "day16"], trusted_root=tmp_path)
    assert len(result["versions"]) == 6 and not result["revisions"]
    assert not result["gaps"] and not result["readyForLiveEvaluation"]
    with pytest.raises(FileExistsError):
        u.import_retained(tmp_path / "day16", trusted_root=tmp_path, day=16)
    with pytest.raises(ValueError, match="qualified live start"):
        time_evidence.check_mode(u.SCHEMA)


def test_revisions_keep_first_version_and_permanent_identity_conflicts(tmp_path, monkeypatch, samples):
    first = acquisition(tmp_path, monkeypatch, samples, "first")
    original = copy.deepcopy(samples)
    row = ws(samples)[0]
    row["team2"][0]["idA"] = "wta999999"
    row["roundCode"], row["roundName"] = "S", "Semifinals"
    row["notBefore"] = "12:30 PM"
    second = acquisition(tmp_path, monkeypatch, samples, "second", 1)
    third = acquisition(tmp_path, monkeypatch, original, "third", 2)
    result = u.history([third, first, second], trusted_root=tmp_path)
    key = "usopen:2026:2501"
    assert result["identityConflicts"] == [key]
    assert [r["playerIDs"][1] for r in result["versions"][key]] == ["wta329668", "wta999999", "wta329668"]
    assert any(r["kind"] == "earlier-published-time" for r in result["revisions"])
    assert u.read_collection(first, trusted_root=tmp_path)["report"]["observations"][0]["playerIDs"][1] == "wta329668"


def test_disappearance_reappearance_and_cancellation_text(tmp_path, monkeypatch, samples):
    first = acquisition(tmp_path, monkeypatch, samples, "first")
    original = copy.deepcopy(samples)
    samples["uso-schedule-17"][1]["courts"][0]["matches"].pop(0)
    listing = next(r for r in samples["uso-schedule-days"][1]["eventDays"] if r["tournDay"] == 17)
    listing["matchCount"] -= 1
    second = acquisition(tmp_path, monkeypatch, samples, "second", 1)
    ws(original)[0]["status"], ws(original)[0]["comment"] = "Cancelled", "Match cancelled"
    third = acquisition(tmp_path, monkeypatch, original, "third", 2)
    result = u.history([first, second, third], trusted_root=tmp_path)
    kinds = {r["kind"] for r in result["revisions"]}
    assert {"absent-from-complete-order", "reappeared-in-complete-order", "cancellation-text-observed"} <= kinds


@pytest.mark.parametrize("kind", ["dns", "timeout", "404", "429", "redirect", "media", "partial", "size", "length", "duplicate-json", "encoding"])
def test_transport_failures_are_durable(tmp_path, monkeypatch, kind):
    response = Response(b'{"eventDays":[]}', u.endpoint(2026))
    if kind == "dns":
        response = urllib.error.URLError("unavailable")
    elif kind == "timeout":
        response = TimeoutError("timeout")
    elif kind in {"404", "429"}:
        response.status = int(kind)
    elif kind == "redirect":
        response.url = "https://unexpected.example.org/feed"
    elif kind == "media":
        response.headers.replace_header("content-type", "text/html")
    elif kind == "partial":
        response.read = lambda limit: (_ for _ in ()).throw(http.client.IncompleteRead(b'{"eventDays":', 100))
    elif kind == "size":
        monkeypatch.setattr(u.p, "MAX_BODY", 4)
    elif kind == "length":
        response.headers.replace_header("content-length", "100")
    elif kind == "duplicate-json":
        response = Response(b'{"eventDays":[],"eventDays":[]}', u.endpoint(2026))
    else:
        response.headers["content-encoding"] = "gzip"
    requests = transport(monkeypatch, [response])
    root = tmp_path / "attempt"
    result = u.collect(root, trusted_root=tmp_path, year=2026, day=17)
    assert len(requests) == 1 and result["report"]["outcome"] == "gap"
    receipt, payload = u.read_capture(root / "catalogue", trusted_root=tmp_path)
    assert receipt["outcome"] == "failed" and payload is None
    assert (root / "catalogue/response.bin").exists()
    assert not (root / "daily").exists()


def test_unreleased_or_injected_endpoint_is_not_fetched(tmp_path, monkeypatch, samples):
    listing = next(r for r in samples["uso-schedule-days"][1]["eventDays"] if r["tournDay"] == 17)
    for i, mutation in enumerate(("unreleased", "host", "year", "duplicate")):
        payload = copy.deepcopy(samples["uso-schedule-days"][1])
        target = next(r for r in payload["eventDays"] if r["tournDay"] == 17)
        if mutation == "unreleased":
            target["released"] = False
        elif mutation == "duplicate":
            payload["eventDays"].append(listing)
        else:
            target["feedUrl"] = target["feedUrl"].replace("www.usopen.org", "attacker.example") if mutation == "host" else u.endpoint(2025, 17)
        requests = transport(monkeypatch, [Response(json.dumps(payload).encode(), u.endpoint(2026))])
        result = u.collect(tmp_path / str(i), trusted_root=tmp_path, year=2026, day=17)
        assert len(requests) == 1 and result["report"]["outcome"] == "gap"


def test_failed_stale_and_partial_updates_are_gaps_not_removals(tmp_path, monkeypatch, samples):
    first = acquisition(tmp_path, monkeypatch, samples, "first")
    transport(monkeypatch, [TimeoutError("timeout")], "2026-09-08T04:01:00+00:00")
    u.collect(tmp_path / "failed", trusted_root=tmp_path, year=2026, day=17)
    samples["uso-schedule-17"][1]["courts"][0]["matches"].pop(0)
    partial = acquisition(tmp_path, monkeypatch, samples, "partial", 2)
    result = u.history([first, tmp_path / "failed", partial], trusted_root=tmp_path)
    assert len(result["gaps"]) == 2
    assert not any(r["kind"] == "absent-from-complete-order" for r in result["revisions"])


def test_archive_tampering_and_interruption_rejected(tmp_path, monkeypatch):
    u.import_retained(tmp_path / "good", trusted_root=tmp_path, day=17)
    (tmp_path / "good/daily/response.bin").write_bytes(b"bad")
    with pytest.raises(ValueError, match="integrity"):
        u.read_collection(tmp_path / "good", trusted_root=tmp_path)
    original = u._save
    def crash(path, *args):
        if path.name == "receipt.json":
            raise OSError("interrupted")
        return original(path, *args)
    monkeypatch.setattr(u, "_save", crash)
    with pytest.raises(OSError, match="interrupted"):
        u.import_retained(tmp_path / "interrupted", trusted_root=tmp_path, day=17)
    assert (tmp_path / "interrupted/catalogue/attempt.json").exists()
    with pytest.raises(a.PredictorArtifactError):
        u.read_collection(tmp_path / "interrupted", trusted_root=tmp_path)


def test_filesystem_boundary_and_no_production_output(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(a.PredictorArtifactError):
        u.import_retained(tmp_path / "link/attempt", trusted_root=tmp_path, day=17)
    assert not list(outside.iterdir())
    monkeypatch.setattr(u, "OUTPUT_DIR", outside)
    with pytest.raises(ValueError, match="production"):
        u.import_retained(outside / "attempt", trusted_root=tmp_path, day=17)
    with pytest.raises(a.PredictorArtifactError):
        u.import_retained(tmp_path / "wrong-root", trusted_root=outside, day=17)


def test_same_time_versions_are_explicitly_ambiguous(tmp_path, monkeypatch, samples):
    first = acquisition(tmp_path, monkeypatch, samples, "first")
    second = acquisition(tmp_path, monkeypatch, samples, "second")
    result = u.history([first, second], trusted_root=tmp_path)
    assert any("ambiguous-acquisition-order" in gap["issues"] for gap in result["gaps"])
    assert len(result["versions"]["usopen:2026:2501"]) == 2
    with pytest.raises(ValueError, match="duplicate collection"):
        u.history([first, first], trusted_root=tmp_path)


def test_location_and_later_sequence_revision_cannot_retain_old_clock(tmp_path, monkeypatch, samples):
    first = acquisition(tmp_path, monkeypatch, samples, "first")
    court = samples["uso-schedule-17"][1]["courts"][0]
    court["courtId"], court["session"] = "NEW", 3
    for row in court["matches"]:
        row["courtId"] = "NEW"
        row["order"] += 1
    second = acquisition(tmp_path, monkeypatch, samples, "second", 1)
    result = u.history([first, second], trusted_root=tmp_path)
    versions = result["versions"]["usopen:2026:2501"]
    assert versions[0]["publishedTimeUTC"] and versions[1]["publishedTimeUTC"] is None
    change = next(r for r in result["revisions"] if r["sourceMatchKey"] == "usopen:2026:2501")
    assert {"courtId", "session", "order", "publishedTimeKind", "publishedTimeUTC"} <= set(change["fields"])


def test_catalogue_practice_link_is_ignored_but_unknown_null_day_is_not(samples):
    assert extract(samples)["coverage"]["WTAObservations"] == 2
    row = next(r for r in samples["uso-schedule-days"][1]["eventDays"] if r["tournDay"] is None)
    row["practice"] = False
    with pytest.raises(ValueError, match="catalogue day"):
        extract(samples)


def test_failed_daily_response_cannot_erase_prior_order(tmp_path, monkeypatch, samples):
    first = acquisition(tmp_path, monkeypatch, samples, "first")
    transport(monkeypatch, [Response(json.dumps(samples["uso-schedule-days"][1]).encode(), u.endpoint(2026)),
                           TimeoutError("daily timeout")], "2026-09-08T04:01:00+00:00")
    failed = u.collect(tmp_path / "failed", trusted_root=tmp_path, year=2026, day=17)
    assert failed["dailyReceipt"] and failed["report"]["outcome"] == "gap"
    result = u.history([first, tmp_path / "failed"], trusted_root=tmp_path)
    assert len(result["versions"]) == 2 and not result["revisions"] and len(result["gaps"]) == 1


def test_retrospective_receipt_cannot_upgrade_freshness(tmp_path):
    u.import_retained(tmp_path / "day17", trusted_root=tmp_path, day=17)
    path = tmp_path / "day17/daily/receipt.json"
    receipt = json.loads(path.read_bytes())
    receipt["headers"]["date"] = "Tue, 08 Sep 2026 03:00:00 GMT"
    receipt["sha256"] = u._digest({k: v for k, v in receipt.items() if k != "sha256"})
    path.write_bytes(u._bytes(receipt))
    with pytest.raises(ValueError, match="provenance"):
        u.read_capture(path.parent, trusted_root=tmp_path)
