"""Response cache for completed-season backfills: storage semantics + _get wiring."""

import json
import urllib.request

import pytest
from tennis_model.data.httpcache import ResponseCache

from tennis_model.data import wta_stats as ws


def test_roundtrip_and_miss(tmp_path):
    c = ResponseCache(tmp_path)
    hit, val = c.get("https://x/a")
    assert (hit, val) == (False, None)
    c.put("https://x/a", {"rows": [1, 2]})
    assert c.get("https://x/a") == (True, {"rows": [1, 2]})


def test_404_sentinel_distinct_from_miss(tmp_path):
    c = ResponseCache(tmp_path)
    c.put("https://x/gone", None)
    hit, val = c.get("https://x/gone")
    assert hit is True and val is None      # cached 404: no re-fetch on rerun
    assert c.get("https://x/other") == (False, None)


def test_corrupt_entry_is_a_miss(tmp_path):
    c = ResponseCache(tmp_path)
    c.put("https://x/a", {"ok": 1})
    c._path("https://x/a").write_text("{truncated", encoding="utf-8")
    assert c.get("https://x/a") == (False, None)


def test_get_serves_cache_without_network(tmp_path, monkeypatch):
    cache = ResponseCache(tmp_path)
    url = f"{ws.BASE}/tournaments/?a=1"
    cache.put(url, {"content": ["cached"]})
    monkeypatch.setattr(ws, "_CACHE", cache)

    def boom(*a, **k):
        raise AssertionError("network hit despite cache")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert ws._get("/tournaments/", {"a": 1}) == {"content": ["cached"]}


def test_get_populates_cache_on_success(tmp_path, monkeypatch):
    cache = ResponseCache(tmp_path)
    monkeypatch.setattr(ws, "_CACHE", cache)
    monkeypatch.setattr(ws.time, "sleep", lambda s: None)
    payload = json.dumps({"content": ["fresh"]}).encode()

    class Resp:
        def read(self):
            return payload
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Resp())
    assert ws._get("/tournaments/", {"a": 2}) == {"content": ["fresh"]}
    url = f"{ws.BASE}/tournaments/?a=2"
    assert cache.get(url) == (True, {"content": ["fresh"]})


def test_transient_failure_not_cached(tmp_path, monkeypatch):
    cache = ResponseCache(tmp_path)
    monkeypatch.setattr(ws, "_CACHE", cache)
    monkeypatch.setattr(ws.time, "sleep", lambda s: None)

    def flaky(*a, **k):
        raise OSError("connection reset")

    monkeypatch.setattr(urllib.request, "urlopen", flaky)
    assert ws._get("/tournaments/", {"a": 3}, retries=2) is None
    url = f"{ws.BASE}/tournaments/?a=3"
    assert cache.get(url) == (False, None)   # a retry-exhausted None must NOT persist


@pytest.mark.parametrize("year_offset,incremental,expect_cache", [
    (-1, False, True),    # completed season, full backfill -> cached
    (0, False, False),    # current season -> never cached
    (-1, True, False),    # incremental refresh -> never cached
])
def test_cache_enabled_only_for_completed_full_backfills(
        tmp_path, monkeypatch, year_offset, incremental, expect_cache):
    seen = {}

    def fake_scrape(year, since=None):
        seen["cache"] = ws._CACHE
        import pandas as pd
        return pd.DataFrame(columns=ws.CANON)

    monkeypatch.setattr(ws, "scrape_year", fake_scrape)
    monkeypatch.setattr(ws, "write_year", lambda y, df: 0)
    monkeypatch.setattr(ws, "stats_dir", lambda tour: tmp_path)
    from datetime import UTC, datetime
    y = datetime.now(UTC).year + year_offset
    ws.download_wta_stats([y], incremental=incremental)
    assert (seen["cache"] is not None) is expect_cache
    assert ws._CACHE is None   # always reset afterwards
