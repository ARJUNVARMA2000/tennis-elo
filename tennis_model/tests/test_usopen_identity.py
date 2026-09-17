"""Exact source identity witnesses; all mutations below are synthetic regression QA."""
import copy
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import pytest
import time_evidence
import usopen_identity as i
import usopen_schedule as u

FIXTURES = Path(__file__).parent / "fixtures/usopen_identity"


@pytest.fixture
def sources():
    values = []
    manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
    for name in ("draw-index", "draw-ws"):
        encoded = (FIXTURES / f"{name}.json.gz").read_bytes()
        assert hashlib.sha256(encoded).hexdigest() == manifest[name]["compressedSHA256"]
        raw = gzip.decompress(encoded)
        assert hashlib.sha256(raw).hexdigest() == manifest[name]["rawSHA256"]
        values.append(json.loads(raw))
    return [*values, *(i.retained_provider(name)[1] for name in ("espn", "wta"))]


def mid(sources, value="2501"):
    return next(r for r in sources[1]["matches"] if r["match_id"] == value)


def test_actual_broad_event_witness_and_strict_player_number_exclusions(sources):
    result = i.audit(*sources, year=2026)
    assert result["eventAccepted"]
    assert result["mapping"]["espnId"] == "189-2026" and result["mapping"]["wtaId"] == "905"
    assert result["eventEvidence"]["sharedCompleted"] == 119
    assert result["eventEvidence"]["officialClaimedCompleted"] == 120
    assert result["sourceRows"] == 127 and result["realOfficialRows"] == 124
    assert len(result["links"]) == 100
    counts = Counter(reason for row in result["exclusions"] for reason in row.get("reasons", [row.get("reason")]))
    assert counts["player-number-disagreement"] == 23
    assert counts["missing-provider-matchup"] == 1
    assert next(r for r in result["exclusions"] if r["sourceMatchId"] == "2118")["officialPlayerNumbers"]["venus williams"] == "230220"
    assert not result["readyForLiveEvaluation"] and not result["actualStartVerified"]
    with pytest.raises(ValueError, match="qualified live start"):
        time_evidence.check_mode(i.SCHEMA)


@pytest.mark.parametrize("mutation", ["duplicate-index", "host", "edition", "size", "missing-slot", "duplicate-id", "population", "round-label", "duplicate-pair"])
def test_wrong_or_ambiguous_draw_shape_fails_closed(sources, mutation):
    if mutation == "duplicate-index":
        sources[0]["draws"].append(copy.deepcopy(sources[0]["draws"][0]))
    elif mutation in {"host", "edition"}:
        sources[0]["draws"][0]["feed_url"] = i.endpoint(2025, "draw") if mutation == "edition" else "https://example.com/WS.json"
    elif mutation == "size":
        sources[1]["drawSize"] = "64"
    elif mutation == "missing-slot":
        sources[1]["matches"].pop()
    elif mutation == "duplicate-id":
        mid(sources, "2502")["match_id"] = "2501"
    elif mutation == "population":
        mid(sources)["eventCode"] = "WQ"
    elif mutation == "round-label":
        mid(sources)["roundName"] = "Final"
    else:
        row = mid(sources, "2502")
        for k in ("team1", "team2"):
            row[k] = copy.deepcopy(mid(sources)[k])
    with pytest.raises(ValueError):
        i.audit(*sources, year=2026)


def test_edition_and_preexisting_event_gate_are_preserved(sources):
    with pytest.raises(ValueError, match="edition"):
        i.audit(*sources, year=2025)
    event = copy.deepcopy(sources[2]["events"][0])
    event["id"] = "another-event"
    sources[2]["events"].append(event)
    result = i.audit(*sources, year=2026)
    assert not result["eventAccepted"] and not result["links"]


def test_event_names_and_generic_epochs_never_establish_identity_or_time(sources):
    sources[1]["eventName"] = "Changed Sponsor"
    sources[2]["events"][0]["name"] = "No shared title"
    for row in sources[1]["matches"]:
        row["epoch"], row["eventDay"] = -1, 50000
    result = i.audit(*sources, year=2026)
    assert result["eventAccepted"] and len(result["links"]) == 100
    assert all("actualStartedAt" not in r and "epoch" not in r for r in result["links"])


def test_weak_overlap_is_not_rescued_by_exact_event_names(sources):
    for row in sources[1]["matches"][:30]:
        row["team1"]["firstNameA"] += " Changed"
    result = i.audit(*sources, year=2026)
    assert not result["eventAccepted"] and not result["links"]
    assert result["issues"] == ["insufficient-completed-event-overlap"]


@pytest.mark.parametrize("mutation", ["replacement-id", "swapped-ids", "winner", "games", "winner-flags", "set-totals", "unknown-status", "unresolved-player"])
def test_local_contradictions_remain_visible_without_undoing_broad_event_evidence(sources, mutation):
    row = mid(sources, "2101")
    if mutation == "replacement-id":
        row["team2"]["idA"] = "wta999999"
    elif mutation == "swapped-ids":
        row["team1"]["idA"], row["team2"]["idA"] = row["team2"]["idA"], row["team1"]["idA"]
    elif mutation == "winner":
        row["winner"] = "2"
        for k in ("won", "totalSetsWon"):
            row["team1"][k], row["team2"][k] = row["team2"][k], row["team1"][k]
        for ss in row["scores"]["sets"]:
            ss.reverse()
    elif mutation == "games":
        row["scores"]["sets"][0][1]["score"] = 3
    elif mutation == "winner-flags":
        row["team2"]["won"] = True
    elif mutation == "set-totals":
        row["team1"]["totalSetsWon"] = 1
    elif mutation == "unknown-status":
        row["statusCode"] = "F"
    else:
        row["team1"]["idA"] = None
    result = i.audit(*sources, year=2026)
    assert result["eventAccepted"]
    assert not any(r["sourceMatchId"] == "2101" for r in result["links"])
    excluded = next(r for r in result["exclusions"] if r["sourceMatchId"] == "2101")
    if mutation in {"winner", "games"}:
        assert "terminal-result-conflict" in excluded["reasons"]
    elif mutation in {"swapped-ids", "replacement-id"}:
        assert "player-number-disagreement" in excluded["reasons"]


def test_swapping_source_sides_with_all_evidence_is_not_a_new_identity(sources):
    row = mid(sources, "2101")
    row["team1"], row["team2"] = row["team2"], row["team1"]
    row["winner"] = "2"
    for ss in row["scores"]["sets"]:
        ss.reverse()
    assert len(i.audit(*sources, year=2026)["links"]) == 100


def test_observed_provider_progression_is_retained_not_called_terminal_conflict(sources):
    result = i.audit(*sources, year=2026)
    lagged = [r for r in result["links"] if len(set(r["observedStatuses"].values())) > 1]
    assert len(lagged) == 1
    assert lagged[0]["observedStatuses"]["official"] == "completed"


def make_archives(tmp_path):
    manifest = json.loads((FIXTURES / "manifest.json").read_bytes())
    for name, entry in manifest.items():
        root = tmp_path / name
        root.mkdir()
        receipt = entry["receipt"]
        (root / "receipt.json").write_text(json.dumps(receipt))
        attempt = {k: receipt[k] for k in ("schema", "url", "requestedAt", "purpose")}
        (root / "attempt.json").write_text(json.dumps(attempt))
        (root / "response.bin").write_bytes(gzip.decompress((FIXTURES / f"{name}.json.gz").read_bytes()))


def test_real_capture_annotation_retains_old_clocks_and_excludes_all_conflicting_versions(tmp_path, sources):
    make_archives(tmp_path)
    for day in (16, 17):
        u.import_retained(tmp_path / f"day{day}", trusted_root=tmp_path, day=day)
    roots = [tmp_path / f"day{day}" for day in (16, 17)]
    result = i.run(tmp_path / "draw-index", tmp_path / "draw-ws", roots, trusted_root=tmp_path, year=2026)
    rows = result["scheduleAssociations"]["associations"]
    assert len(rows) == 6 and not result["scheduleAssociations"]["exclusions"]
    assert all(row["associationAvailableAt"] == "2026-09-08T04:32:09.560676+00:00" for row in rows)
    assert result["sourceReceipts"]["wta"]["receivedAt"] == "2026-09-08T00:27:12.491559+00:00"
    assert rows[0]["scheduleObservation"]["observedAtUTC"] < rows[0]["associationAvailableAt"]
    history = u.history(roots, trusted_root=tmp_path)
    key = "usopen:2026:2501"
    changed = copy.deepcopy(history["versions"][key][0])
    changed["playerIDs"][1] = "wta999999"
    history["versions"][key].extend([changed, copy.deepcopy(history["versions"][key][0])])
    linked = i.associate(history, result, evidence_at=result["evidenceAvailableAt"])
    assert key in linked["identityConflicts"]
    assert not any(r["scheduleObservation"]["sourceMatchKey"] == key for r in linked["associations"])
    assert linked["exclusions"][0]["versions"] == 3


@pytest.mark.parametrize("mutation", ["raw", "receipt-time", "url", "media", "partial"])
def test_unverified_draw_receipt_never_contributes_identity_evidence(tmp_path, mutation):
    make_archives(tmp_path)
    root = tmp_path / "draw-ws"
    if mutation == "raw":
        (root / "response.bin").write_bytes(b"bad")
    else:
        receipt = json.loads((root / "receipt.json").read_bytes())
        if mutation == "receipt-time":
            receipt["requestedAt"] = receipt["receivedAt"]
        elif mutation == "url":
            receipt["url"] = i.endpoint(2025, "draw")
        elif mutation == "media":
            receipt["headers"]["content-type"] = "text/html"
        else:
            receipt["rawComplete"] = False
        (root / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        i.read_draw(root, trusted_root=tmp_path, year=2026, kind="draw")
