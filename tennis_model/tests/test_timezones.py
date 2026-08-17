"""Unit checks for the committed venue -> IANA timezone table."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.timezones import TABLE, local_date, timezone_name


def test_committed_timezone_table_has_broad_venue_coverage():
    assert TABLE.exists()
    with TABLE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 300
    assert timezone_name("Cincinnati Open") == "America/New_York"
    assert timezone_name("Wimbledon") == "Europe/London"
    assert timezone_name("Australian Open") == "Australia/Melbourne"


def test_local_date_converts_aware_instants_and_falls_back_safely():
    assert local_date("2026-08-17T02:00Z", "Cincinnati, USA") == "2026-08-16"
    assert local_date("2026-08-17T02:00Z", "No Such Event") == "2026-08-17"
    assert local_date("2026-08-17", "Cincinnati") == "2026-08-17"
    assert local_date(None, "Cincinnati") == ""
