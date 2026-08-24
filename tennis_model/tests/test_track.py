"""Unit checks for eval/track — fully synthetic (no model, no network).

Runnable directly (`python tests/test_track.py`) or under pytest. Covers match
grading + metrics, calibration shape, dedup/idempotency, and tournament champion
grading. The forecast log and the output dir are redirected to a temp area.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.eval.track as track


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
class _FakeElo:
    def __init__(self, names):
        self.overall = {n: 1500.0 for n in names}


class _FakePredictor:
    """Constant-probability stand-in so logging needs no trained model."""
    def __init__(self, names, p=0.6):
        self.elo = _FakeElo(names)
        self._p = p

    def win_prob(self, a, b, surface=None, best_of=None, event=None):
        return self._p


def _results_df(rows):
    """rows: list of (winner, loser, date, surface)."""
    return pd.DataFrame([
        {"winner_name": w, "loser_name": l, "date": pd.Timestamp(d),
         "surface_b": s, "completed": True}
        for (w, l, d, s) in rows
    ])


def _setup(tmp):
    track.FORECAST_DIR = tmp / "forecast_log"
    track.FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    out = tmp / "output"
    out.mkdir(parents=True, exist_ok=True)
    track.output_dir = lambda tour: out          # redirect reads/writes
    return out


def _write_log(records):
    path = track.FORECAST_DIR / "atp.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


def _write_bracket(out, rounds, espn_id="123"):
    (out / "brackets.json").write_text(json.dumps([{
        "name": "TestOpen",
        "espnId": espn_id,
        "rounds": [
            {"round": rnd, "matches": [{"a": a, "b": b} for a, b in matches]}
            for rnd, matches in rounds
        ],
    }]), encoding="utf-8")


def _match(a, b, p, as_of="2026-06-01", surface="Hard", event="TestOpen", rnd="QF",
           version="test", espn_id=None):
    return {"type": "match", "as_of": as_of, "tour": "atp", "event": event,
            "espnId": espn_id,
            "round": rnd, "surface": surface, "best_of": 3, "season": 2026,
            "playerA": a, "playerB": b, "p": p, "model_version": version}


def _graded(p, won, date="2026-06-15", version="0.1.0"):
    """A _grade_matches-shaped record, as _drift_block consumes them."""
    return {"model_version": version, "date": date, "p_a": p, "a_won": won,
            "p_winner": p if won else 1.0 - p}


def _graded_batch(n, p, wins, **kw):
    return [_graded(p, i < wins, **kw) for i in range(n)]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def test_match_grading_and_brier():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([
            _match("Alice", "Bob", 0.70),     # Alice wins  -> p_winner 0.70, hit True
            _match("Cara", "Dana", 0.40),     # Cara wins   -> p_winner 0.40, hit False
            _match("Evan", "Finn", 0.55),     # Finn wins   -> p_winner 0.45, hit False
        ])
        df = _results_df([
            ("Alice", "Bob", "2026-06-03", "Hard"),
            ("Cara", "Dana", "2026-06-05", "Hard"),
            ("Finn", "Evan", "2026-06-04", "Hard"),
        ])
        out = track.grade("atp", df)
        mf = out["matchForecasts"]
        assert mf["graded"] == 3 and mf["pending"] == 0, mf
        expected_brier = np.mean([(1 - 0.70) ** 2, (1 - 0.40) ** 2, (1 - 0.45) ** 2])
        assert abs(mf["overall"]["brier"] - expected_brier) < 1e-9, (mf["overall"], expected_brier)
        # accuracy: only Alice's call was correct (0.70 > 0.5 and she won)
        assert abs(mf["overall"]["acc"] - 1 / 3) < 1e-9, mf["overall"]
        hits = {(g["playerA"], g["hit"]) for g in mf["recent"]}
        assert ("Alice", True) in hits and ("Cara", False) in hits, hits
        print("ok test_match_grading_and_brier")


def test_hourly_utc_forecast_grades_against_date_only_results():
    """Hourly snapshots added an offset-aware timestamp while normalized match dates
    remain naive; the first-sighting grading contract must continue to resolve."""
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([_match("Alice", "Bob", 0.7, as_of="2026-06-01T08:00:00+00:00")])
        out = track.grade("atp", _results_df([("Alice", "Bob", "2026-06-03", "Hard")]))
        assert out["matchForecasts"]["graded"] == 1


def test_pending_outside_window():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([_match("Alice", "Bob", 0.7, as_of="2026-06-01")])
        # result 60 days later -> outside the 21-day join window -> stays pending
        df = _results_df([("Alice", "Bob", "2026-08-01", "Hard")])
        out = track.grade("atp", df)
        assert out["matchForecasts"]["graded"] == 0, out["matchForecasts"]
        print("ok test_pending_outside_window")


def test_calibration_shape():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([_match(f"A{i}", f"B{i}", 0.5 + 0.04 * i) for i in range(8)])
        df = _results_df([(f"A{i}", f"B{i}", "2026-06-02", "Hard") for i in range(8)])
        out = track.grade("atp", df)
        cal = out["matchForecasts"]["calibration"]
        assert cal and all({"bin", "n", "pred", "actual"} <= set(c) for c in cal), cal
        print("ok test_calibration_shape")


def test_dedup_idempotent():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        (out / "tournaments.json").write_text("[]", encoding="utf-8")
        pred = _FakePredictor(["Alice", "Bob"])
        up = pd.DataFrame([{"tourney_name": "TestOpen", "tourney_date": "2026-06-01",
                            "round": "QF", "playerA": "Alice", "playerB": "Bob"}])
        df = _results_df([("Zeta", "Yan", "2026-06-01", "Hard")])  # unrelated
        n1 = track.log_forecasts("atp", pred, df, up, "2026-06-01")
        n2 = track.log_forecasts("atp", pred, df, up, "2026-06-01")  # same hour retry
        n3 = track.log_forecasts("atp", pred, df, up, "2026-06-02")  # later snapshot
        lines = track._read_log(track.FORECAST_DIR / "atp.jsonl")
        assert n1 == 2 and n2 == 0 and n3 == 1 and len(lines) == 3
        assert sum(r["type"] == "match" for r in lines) == 1
        assert sum(r["type"] == "match_snapshot" for r in lines) == 2
        print("ok test_dedup_idempotent")


def test_movement_keeps_first_sighting_and_current_probability():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        first = _match("Alice", "Bob", 0.55, as_of="2026-06-01T08:00:00+00:00")
        snap = {**first, "type": "match_snapshot", "as_of": "2026-06-02T08:00:00+00:00",
                "p": 0.61}
        _write_log([first, snap])
        row = {"event": "TestOpen", "date": "2026-06-03", "round": "QF",
               "playerA": "Alice", "playerB": "Bob", "pA": 0.64}
        movement = track.movement_for_upcoming("atp", [row])[track.movement_key(row)]
        assert movement["first"] == 0.55 and movement["current"] == 0.64
        assert movement["delta"] == 0.09 and movement["snapshots"] == 2


def test_match_identity_and_timeline_are_orientation_safe():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        first = _match("Alice", "Bob", 0.7, as_of="2026-06-01T08:00:00+00:00",
                       event="Sponsor Open", espn_id="123")
        same_hour = {**first, "type": "match_snapshot", "components": {"combiner": 0.7}}
        later = {**first, "type": "match_snapshot", "as_of": "2026-06-01T12:00:00+00:00",
                 "p": 0.66, "components": {"combiner": 0.66}}
        _write_log([first, same_hour, later])
        # Feed orientation and sponsor title both changed; espnId makes this the same match.
        row = {"event": "City Open", "espnId": "123", "date": "2026-06-02", "round": "QF",
               "playerA": "Bob", "playerB": "Alice", "pA": 0.36}
        movement = track.movement_for_upcoming("atp", [row])[track.movement_key(row)]
        assert movement["first"] == 0.3 and movement["current"] == 0.36
        assert movement["snapshots"] == 2  # first + same-hour snapshot is one observation
        assert movement["timeline"][1]["p"] == 0.34
        assert movement["timeline"][1]["components"]["combiner"] == 0.34


def test_bracket_round_bridge_preserves_first_sighting_and_persists():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        (out / "tournaments.json").write_text("[]", encoding="utf-8")
        _write_bracket(out, [("R32", [("Alice", "Bob")])])

        first = _match(
            "Alice", "Bob", 0.55, as_of="2026-06-01T08:00:00+00:00",
            rnd="R64", espn_id="123",
        )
        first["match_id"] = track.match_identity(first)
        failed_snapshot = {**first, "type": "match_snapshot", "p": 0.57}
        _write_log([first, failed_snapshot])

        current = {
            "event": "TestOpen", "espnId": "123", "date": "2026-06-02",
            "round": "R32", "surface": "Hard", "best_of": 3,
            "playerA": "Alice", "playerB": "Bob", "pA": 0.61,
        }
        empty_results = _results_df([])
        added = track.log_forecasts(
            "atp", None, empty_results, None, "2026-06-02T08:00:00+00:00",
            enriched=[current],
        )
        retry = track.log_forecasts(
            "atp", None, empty_results, None, "2026-06-02T08:00:00+00:00",
            enriched=[current],
        )
        lines = track._read_log(track.FORECAST_DIR / "atp.jsonl")
        canonical_id = track.match_identity({**current, "season": 2026})

        assert added == 2 and retry == 0  # durable bridge + one new hourly snapshot
        assert sum(r["type"] == "match" for r in lines) == 1
        assert sum(r["type"] == "match_snapshot" for r in lines) == 2
        markers = [r for r in lines if r["type"] == "match_identity_bridge"]
        assert len(markers) == 1
        assert markers[0]["from_match_id"] == first["match_id"]
        assert markers[0]["to_match_id"] == canonical_id
        assert markers[0]["round"] == "R32"

        # The marker remains authoritative after the live bracket artifact ages out.
        (out / "brackets.json").write_text("[]", encoding="utf-8")
        movement = track.movement_for_upcoming("atp", [
            {**current, "pA": 0.64},
        ])[track.movement_key(current)]
        assert movement["first"] == 0.55 and movement["current"] == 0.64
        assert movement["firstAsOf"] == "2026-06-01T08:00:00+00:00"
        assert movement["snapshots"] == 2
        assert sum(point["firstSighting"] for point in movement["timeline"]) == 1

        results = _results_df([("Alice", "Bob", "2026-06-03", "Hard")])
        results["espn_id"] = "123"
        results["round"] = "R32"
        graded = track.grade("atp", results)["matchForecasts"]
        assert graded["logged"] == 1 and graded["graded"] == 1 and graded["pending"] == 0
        assert graded["recent"][0]["matchId"] == canonical_id
        assert graded["recent"][0]["round"] == "R32"
        assert graded["recent"][0]["forecast"]["first"] == 0.55
        assert graded["recent"][0]["forecast"]["snapshots"] == 2


def test_bracket_round_bridge_canonicalizes_explicit_player_alias_in_id():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        (out / "tournaments.json").write_text("[]", encoding="utf-8")
        _write_bracket(out, [("R32", [("Diego Dedura", "Alice")])])

        cached = _match(
            "Diego Dedura-Palomero", "Alice", 0.6,
            as_of="2026-06-01T08:00:00+00:00", rnd="R64", espn_id="123",
        )
        cached["match_id"] = track.match_identity(cached)
        _write_log([cached])
        current = {
            "event": "TestOpen", "espnId": "123", "date": "2026-06-02",
            "round": "R32", "surface": "Hard", "best_of": 3,
            "playerA": "Diego Dedura", "playerB": "Alice", "pA": 0.63,
        }
        added = track.log_forecasts(
            "atp", None, _results_df([]), None, "2026-06-02T08:00:00+00:00",
            enriched=[current],
        )
        lines = track._read_log(track.FORECAST_DIR / "atp.jsonl")
        canonical_id = track.match_identity({**current, "season": 2026})
        marker = next(r for r in lines if r["type"] == "match_identity_bridge")

        assert added == 2 and sum(r["type"] == "match" for r in lines) == 1
        assert marker["to_match_id"] == canonical_id
        assert "diego dedura palomero" not in marker["to_match_id"]
        movement = track.movement_for_upcoming("atp", [current])[canonical_id]
        assert movement["first"] == 0.6 and movement["current"] == 0.63

        results = _results_df([("Diego Dedura", "Alice", "2026-06-03", "Hard")])
        results["espn_id"] = "123"
        assert track.grade("atp", results)["matchForecasts"]["graded"] == 1


def test_persisted_round_bridge_survives_transitive_legacy_id_chain():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        (out / "tournaments.json").write_text("[]", encoding="utf-8")
        _write_bracket(out, [("R32", [("Alice", "Bob")])])

        legacy = _match(
            "Alice", "Bob", 0.54, as_of="2026-06-01T08:00:00+00:00",
            event="Sponsor Open", rnd="R64",
        )
        identified_snapshot = {
            **legacy,
            "type": "match_snapshot",
            "as_of": "2026-06-02T08:00:00+00:00",
            "event": "City Open",
            "espnId": "123",
            "p": 0.58,
        }
        _write_log([legacy, identified_snapshot])
        current = {
            "event": "TestOpen", "espnId": "123", "date": "2026-06-03",
            "round": "R32", "surface": "Hard", "best_of": 3,
            "playerA": "Alice", "playerB": "Bob", "pA": 0.62,
        }
        added = track.log_forecasts(
            "atp", None, _results_df([]), None, "2026-06-03T08:00:00+00:00",
            enriched=[current],
        )
        lines = track._read_log(track.FORECAST_DIR / "atp.jsonl")
        marker = next(r for r in lines if r["type"] == "match_identity_bridge")
        wrong_explicit_id = track.match_identity(identified_snapshot)
        canonical_id = track.match_identity({**current, "season": 2026})
        assert added == 2 and sum(r["type"] == "match" for r in lines) == 1
        assert marker["from_match_id"] == wrong_explicit_id
        assert marker["to_match_id"] == canonical_id

        (out / "brackets.json").write_text("[]", encoding="utf-8")
        movement = track.movement_for_upcoming("atp", [current])[canonical_id]
        assert movement["first"] == 0.54 and movement["snapshots"] == 3
        results = _results_df([("Alice", "Bob", "2026-06-04", "Hard")])
        results["espn_id"] = "123"
        graded = track.grade("atp", results)["matchForecasts"]
        assert graded["logged"] == 1 and graded["graded"] == 1
        assert graded["recent"][0]["round"] == "R32"


def test_bracket_round_bridge_fails_closed_without_unique_knockout_evidence():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        missing_id = _match("Alice", "Bob", 0.55, rnd="R64")
        unmatched = _match("Alice", "Cara", 0.55, rnd="R64", espn_id="123")
        _write_bracket(out, [("R32", [("Alice", "Bob")])])
        assert track._bracket_round_bridges("atp", [missing_id, unmatched]) == {}

        cached = _match("Alice", "Bob", 0.55, rnd="R64", espn_id="123")
        cached["match_id"] = track.match_identity(cached)
        malformed = {**cached, "match_id": "not-a-match-id"}
        other_pair = _match("Alice", "Cara", 0.55, rnd="R64", espn_id="123")
        mismatched = {**cached, "match_id": track.match_identity(other_pair)}
        assert track._bracket_round_bridges("atp", [malformed, mismatched]) == {}

        # A round-robin meeting plus a knockout rematch cannot identify which meeting
        # ESPN's poisoned R64 cache row represented, even though the event id is stable.
        _write_bracket(out, [
            ("RR", [("Alice", "Bob")]),
            ("F", [("Alice", "Bob")]),
        ])
        assert track._bracket_round_bridges("atp", [cached]) == {}

        # A lone non-knockout occurrence is not eligible either.
        _write_bracket(out, [("RR", [("Alice", "Bob")])])
        assert track._bracket_round_bridges("atp", [cached]) == {}


def test_conflicting_persisted_round_bridges_fail_closed():
    cached = _match("Alice", "Bob", 0.55, rnd="R64", espn_id="123")
    cached["match_id"] = track.match_identity(cached)
    r32 = track.match_identity({**cached, "match_id": None, "round": "R32"})
    r16 = track.match_identity({**cached, "match_id": None, "round": "R16"})
    marker = lambda target: {
        "type": "match_identity_bridge",
        "bridge_version": "bracket-round-v1",
        "evidence": "unique_knockout_bracket_round",
        "from_match_id": cached["match_id"],
        "to_match_id": target,
    }
    records = [cached, marker(r32), marker(r16)]
    assert track._persisted_round_bridges(records) == {}
    assert track._reconciled_round_bridges(
        records, {cached["match_id"]: r32}) == {}


def test_legacy_first_sighting_bridges_to_unique_registry_match():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        legacy = _match(
            "Alice", "Bob", 0.55, as_of="2026-06-01T08:00:00+00:00",
            event="Sponsor Open",
        )
        identified = {
            **legacy, "type": "match_snapshot", "event": "City Open", "espnId": "123",
            "as_of": "2026-06-02T08:00:00+00:00", "p": 0.61,
        }
        migration_duplicate = {
            **identified, "type": "match", "as_of": "2026-06-02T12:00:00+00:00", "p": 0.63,
        }
        _write_log([legacy, identified, migration_duplicate])

        row = {"event": "Another Title", "espnId": "123", "date": "2026-06-03",
               "round": "QF", "playerA": "Alice", "playerB": "Bob", "pA": 0.64}
        movement = track.movement_for_upcoming("atp", [row])[track.movement_key(row)]
        assert movement["first"] == 0.55 and movement["current"] == 0.64
        assert sum(point["firstSighting"] for point in movement["timeline"]) == 1

        result = track.grade(
            "atp", _results_df([("Alice", "Bob", "2026-06-03", "Hard")])
        )["matchForecasts"]
        assert result["logged"] == 1 and result["graded"] == 1
        assert result["recent"][0]["matchId"].startswith("v2|espn:123|")
        assert result["recent"][0]["forecast"]["first"] == 0.55


def test_legacy_bridge_fails_closed_when_evidence_is_ambiguous():
    legacy_a = _match("Alice", "Bob", 0.55, event="Sponsor Open")
    legacy_b = _match("Alice", "Bob", 0.57, event="City Open")
    explicit = {**legacy_a, "type": "match_snapshot", "espnId": "123",
                "as_of": "2026-06-02"}
    assert track._legacy_match_bridges([legacy_a, legacy_b, explicit]) == {}

    explicit_other = {**explicit, "espnId": "456"}
    assert track._legacy_match_bridges([legacy_a, explicit, explicit_other]) == {}


def test_ambiguous_pair_rematch_is_not_guessed_without_event_id():
    with tempfile.TemporaryDirectory() as d:
        _setup(Path(d))
        _write_log([_match("Alice", "Bob", 0.7)])
        df = _results_df([
            ("Alice", "Bob", "2026-06-03", "Hard"),
            ("Bob", "Alice", "2026-06-10", "Hard"),
        ])
        assert track.grade("atp", df)["matchForecasts"]["graded"] == 0


def test_performance_uses_first_sightings_and_excludes_walkovers():
    graded = [
        {**_match("Alice", "Bob", 0.7), "date": "2026-06-03", "p_a": 0.7,
         "a_won": True, "walkover": False},
        {**_match("Alice", "Cara", 0.4), "date": "2026-06-04", "p_a": 0.4,
         "a_won": False, "walkover": True},
    ]
    perf = {r["name"]: r for r in track._player_performance(graded)}
    assert perf["Alice"]["n"] == 1 and perf["Alice"]["delta"] == 0.3
    assert "Cara" not in perf


def test_tournament_grading():
    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        # two daily snapshots of an in-progress event; champion turns out to be Bob
        snap = lambda as_of, bob_p: {
            "type": "tournament", "as_of": as_of, "tour": "atp", "event": "TestCup",
            "season": 2026, "projection": [
                {"name": "Alice", "champion": 0.50}, {"name": "Bob", "champion": bob_p}],
            "modelFavorite": "Alice", "model_version": "test"}
        _write_log([snap("2026-06-01", 0.30), snap("2026-06-03", 0.45)])
        (out / "tournaments.json").write_text(json.dumps([
            {"name": "TestCup", "status": "completed", "champion": "Bob",
             "end": "2026-06-04"}]), encoding="utf-8")
        res = track.grade("atp", _results_df([]))["tournamentOdds"]
        assert res["events"] == 1, res
        # champion Brier = mean((1-0.30)^2, (1-0.45)^2), reported rounded to 4dp
        exp = np.mean([(1 - 0.30) ** 2, (1 - 0.45) ** 2])
        assert abs(res["championBrier"] - exp) < 1e-4, (res, exp)
        # favourite was Alice, champion Bob -> not picked
        assert res["recent"][0]["favoritePicked"] is False, res["recent"][0]
        print("ok test_tournament_grading")


def test_drift_calibrated_is_ok():
    # 200 forecasts at p=0.7, exactly 140 hit: realized logloss == forecast entropy
    # by construction, so d == 0 -> "ok" with |t| ~ 0.
    dr = track._drift_block(_graded_batch(200, 0.7, 140), None, current_version="0.1.0")
    assert dr["status"] == "ok", dr
    assert dr["n"] == 200 and abs(dr["d"]) < 1e-9, dr
    assert abs(dr["t"]) < 1.0, dr
    assert abs(dr["logloss"] - dr["expectedLogloss"]) < 1e-9, dr
    assert dr["baseline"] is None, dr
    print("ok test_drift_calibrated_is_ok")


def test_drift_overconfident_flags():
    # says 75%, hits 55% -> d ~ +0.22 nats, t ~ 5.7: the re-tune signal must fire,
    # and the sign convention is positive-when-overconfident.
    dr = track._drift_block(_graded_batch(200, 0.75, 110), None, current_version="0.1.0")
    assert dr["status"] == "drift", dr
    assert dr["d"] > 0.2 and dr["t"] >= 5, dr
    # symmetric luck (underconfident window) must NEVER fire — one-sided by design
    lucky = track._drift_block(_graded_batch(200, 0.75, 180), None, current_version="0.1.0")
    assert lucky["status"] == "ok" and lucky["d"] < 0, lucky
    print("ok test_drift_overconfident_flags")


def test_drift_below_min_n_insufficient():
    dr = track._drift_block(_graded_batch(30, 0.9, 3), None, current_version="0.1.0")
    assert dr["status"] == "insufficient" and dr["n"] == 30, dr
    assert dr["d"] is None and dr["se"] is None and dr["t"] is None, dr
    assert dr["logloss"] is None and dr["worstBin"] is None, dr
    assert track._drift_block([], None, current_version="0.1.0")["status"] == "insufficient"
    print("ok test_drift_below_min_n_insufficient")


def test_drift_window_and_version_filter():
    recs = (_graded_batch(160, 0.7, 112, date="2026-06-15")            # in window
            + _graded_batch(100, 0.6, 20, date="2026-02-15")           # 120d stale -> out
            + _graded_batch(100, 0.6, 20, date="2026-06-15", version="0.0.9"))  # old model
    dr = track._drift_block(recs, None, current_version="0.1.0")
    assert dr["n"] == 160, dr                       # both stale + old-version excluded
    assert dr["status"] == "ok", dr                 # the excluded overconfident junk can't latch it
    assert dr["modelVersion"] == "0.1.0", dr
    print("ok test_drift_window_and_version_filter")


def test_drift_grade_end_to_end_json_safe():
    def _no_nan(tok):
        raise ValueError(f"non-finite {tok} in shipped track.json")

    with tempfile.TemporaryDirectory() as d:
        out = _setup(Path(d))
        # empty log + no accuracy.json: insufficient, baseline null, file NaN-free
        _write_log([])
        track.grade("atp", _results_df([]))
        shipped = json.loads((out / "track.json").read_text(encoding="utf-8"),
                             parse_constant=_no_nan)
        dr = shipped["matchForecasts"]["drift"]
        assert dr["status"] == "insufficient" and dr["baseline"] is None, dr

        # 200 graded current-version forecasts at p=0.7 (140 hit) + a synthetic baseline
        (out / "accuracy.json").write_text(json.dumps({
            "window": "2016-2026",
            "models": {"combiner": {"n": 28648, "acc": 0.68,
                                    "logloss": 0.5826, "brier": 0.2001}},
        }), encoding="utf-8")
        _write_log([_match(f"A{i}", f"B{i}", 0.7, version=track.__version__)
                    for i in range(200)])
        df = _results_df([(f"A{i}", f"B{i}", "2026-06-02", "Hard") if i < 140
                          else (f"B{i}", f"A{i}", "2026-06-02", "Hard")
                          for i in range(200)])
        track.grade("atp", df)
        shipped = json.loads((out / "track.json").read_text(encoding="utf-8"),
                             parse_constant=_no_nan)
        dr = shipped["matchForecasts"]["drift"]
        assert dr["status"] == "ok" and dr["n"] == 200, dr
        assert dr["baseline"]["logloss"] == 0.5826, dr
        # dLogloss = live (== entropy(0.7) = 0.6109) - backtest baseline, +ve = live worse
        assert abs(dr["baseline"]["dLogloss"] - (0.6109 - 0.5826)) < 1e-3, dr
        assert dr["baseline"]["window"] == "2016-2026", dr
        print("ok test_drift_grade_end_to_end_json_safe")


if __name__ == "__main__":
    test_match_grading_and_brier()
    test_pending_outside_window()
    test_calibration_shape()
    test_dedup_idempotent()
    test_tournament_grading()
    test_drift_calibrated_is_ok()
    test_drift_overconfident_flags()
    test_drift_below_min_n_insufficient()
    test_drift_window_and_version_filter()
    test_drift_grade_end_to_end_json_safe()
    print("\nALL PASSED")
