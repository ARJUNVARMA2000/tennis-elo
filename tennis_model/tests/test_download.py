"""Unit checks for the download layer's pure logic — no network.

Runnable directly (`python tests/test_download.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.download as dl


def test_strict_fatal_rules():
    """The strict gate reds the build only for failures that threaten current data:
    any stats-overlay failure, plus current-year files elsewhere. Frozen archive
    years are immutable and covered by the release snapshot. (The first CI run went
    red on exactly this logic — keep it pinned.)"""
    fails = {
        "wta/historical": [2019, 2026],
        "atp/fresh": [2026],
        "atp/stats": ["2018.csv"],
        "wta/stats": ["WTA API unreachable after 5 retries"],
    }
    out = dl.strict_fatal(fails, this_year=2026)
    assert "wta/historical:2026" in out
    assert "wta/historical:2019" not in out          # archive year: snapshot covers it
    assert "atp/fresh:2026" in out
    assert "atp/stats:2018.csv" in out               # stats overlay: always fatal
    assert any(s.startswith("wta/stats:") for s in out)
    assert dl.strict_fatal({}, 2026) == []
    print("ok test_strict_fatal_rules")


def test_valid_csv_schema_gate():
    good = b"tourney_date,winner_name,loser_name,score,w_svpt,l_svpt\n20260101,A,B,6-1 6-1,50,40\n" * 3
    html = b"<html><body>error page that is long enough to pass the size check ....</body></html>" * 3
    base_only = b"tourney_date,winner_name,loser_name,score\n20260101,A,B,6-1 6-1\n" * 5
    assert dl._valid_csv(good, dl._REQUIRED_STATS)
    assert not dl._valid_csv(html, dl._REQUIRED_STATS)
    assert not dl._valid_csv(base_only, dl._REQUIRED_STATS)   # stats columns required
    assert dl._valid_csv(base_only, dl._REQUIRED_BASE)
    assert not dl._valid_csv(b"tiny", dl._REQUIRED_BASE)
    print("ok test_valid_csv_schema_gate")


def test_download_clamps_to_source_last_year():
    """Frozen archives declare last_year — the downloader must never request files
    that cannot exist upstream (they would trip the strict gate; the first CI run
    failed on WTA 2025/2026)."""
    attempted = []
    orig_dy, orig_src = dl.download_year, dl.HISTORICAL_SOURCE
    try:
        dl.download_year = lambda tour, kind, y: attempted.append(y) or True
        dl.HISTORICAL_SOURCE = {"wta": {**orig_src["wta"], "last_year": 2024}}
        done, failed = dl.download("wta", "historical")
    finally:
        dl.download_year, dl.HISTORICAL_SOURCE = orig_dy, orig_src
    assert max(attempted) == 2024 and not failed
    print("ok test_download_clamps_to_source_last_year")


if __name__ == "__main__":
    test_strict_fatal_rules()
    test_valid_csv_schema_gate()
    test_download_clamps_to_source_last_year()
    print("\nALL PASSED")
