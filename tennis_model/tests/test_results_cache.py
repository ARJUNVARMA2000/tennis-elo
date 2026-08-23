"""Persistent schema-normalized historical-frame cache."""

from __future__ import annotations

import time

import pandas as pd
from pandas.testing import assert_frame_equal

from tennis_model.data import results


def _write(path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_normalized_history_cache_hits_and_invalidates(monkeypatch, tmp_path):
    raw = tmp_path / "historical"
    cache = tmp_path / "cache"
    source = raw / "2024.csv"
    _write(source, [{"tourney_name": "One", "winner_name": "A", "loser_name": "B"}])
    monkeypatch.setattr(results, "historical_dir", lambda tour: raw)
    monkeypatch.setattr(results, "NORMALIZED_HISTORY_CACHE_DIR", cache)

    cold = results._read_historical("atp")
    original_reader = results._read_dir
    monkeypatch.setattr(results, "_read_dir", lambda path: (_ for _ in ()).throw(
        AssertionError("cache hit re-read CSV")))
    warm = results._read_historical("atp")
    assert_frame_equal(cold, warm, check_dtype=True, check_exact=True)

    monkeypatch.setattr(results, "_read_dir", original_reader)
    time.sleep(0.002)
    _write(source, [
        {"tourney_name": "One", "winner_name": "A", "loser_name": "B"},
        {"tourney_name": "Two", "winner_name": "C", "loser_name": "D"},
    ])
    fresh = results._read_historical("atp")
    assert len(fresh) == 2


def test_corrupt_normalized_history_cache_is_a_miss(monkeypatch, tmp_path):
    raw = tmp_path / "historical"
    cache = tmp_path / "cache"
    _write(raw / "2024.csv", [
        {"tourney_name": "One", "winner_name": "A", "loser_name": "B"},
    ])
    monkeypatch.setattr(results, "historical_dir", lambda tour: raw)
    monkeypatch.setattr(results, "NORMALIZED_HISTORY_CACHE_DIR", cache)
    cache.mkdir(parents=True)
    (cache / "atp.pkl").write_bytes(b"not a pickle")

    frame = results._read_historical("atp")
    assert len(frame) == 1
    assert isinstance(pd.read_pickle(cache / "atp.pkl")["frame"], pd.DataFrame)


def test_normalized_match_cache_preserves_frame_attrs_and_rejects_stale_key(
        monkeypatch, tmp_path):
    monkeypatch.setattr(results, "NORMALIZED_MATCH_CACHE_DIR", tmp_path)
    frame = pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01"]),
        "winner_name": ["A"], "loser_name": ["B"],
    })
    frame.attrs["excluded_wta125_matches"] = 3
    results._write_normalized_matches("wta", False, "fingerprint-a", frame)

    warm = results._read_normalized_matches("wta", False, "fingerprint-a")
    assert warm is not None
    assert_frame_equal(frame, warm, check_dtype=True, check_exact=True)
    assert warm.attrs == frame.attrs
    assert results._read_normalized_matches("wta", False, "fingerprint-b") is None

    results._normalized_match_cache_path("wta", False).write_bytes(b"broken")
    assert results._read_normalized_matches("wta", False, "fingerprint-a") is None
