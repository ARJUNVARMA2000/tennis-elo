"""Offline tournament-venue timezone lookup for ESPN calendar dates.

ESPN emits match times as UTC instants, while tennis results are dated in the
tournament's local calendar. ``venue_timezones.csv`` is a committed derivative of
the existing geocoded venue table, so the hourly refresh never depends on a geocoder.
Unknown venues deliberately retain the UTC date rather than guessing.

Build/refresh (offline, batched Open-Meteo coordinate lookups):
  PYTHONPATH=src python -m tennis_model.data.timezones --build
"""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .geo import city_key

TABLE = Path(__file__).with_name("venue_timezones.csv")
_VENUE_TABLE = Path(__file__).with_name("venue_altitude.csv")
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@cache
def _table() -> dict[str, str]:
    if not TABLE.exists():
        return {}
    with TABLE.open(encoding="utf-8") as f:
        return {r["city_key"]: r["timezone"] for r in csv.DictReader(f)
                if r.get("city_key") and r.get("timezone")}


def timezone_name(venue: str | None) -> str | None:
    """IANA timezone for a venue/event name, or ``None`` when it is unknown."""
    key = city_key(venue) if venue else None
    return _table().get(key) if key is not None else None


def local_date(stamp: object, venue: str | None) -> str:
    """Convert an ISO timestamp to the venue's calendar date.

    Missing/malformed timestamps and unknown venues preserve the old deterministic
    ``YYYY-MM-DD`` UTC-prefix behavior. ESPN timestamps are timezone-aware; a naive
    value is likewise left untouched rather than assigning it an invented zone.
    """
    raw = stamp if isinstance(stamp, str) else ""
    fallback = raw[:10]
    tz_name = timezone_name(venue)
    if not raw or not tz_name:
        return fallback
    try:
        instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if instant.tzinfo is None:
            return fallback
        return instant.astimezone(ZoneInfo(tz_name)).date().isoformat()
    except (ValueError, ZoneInfoNotFoundError):
        return fallback


def _fetch_timezones(rows: list[dict]) -> list[str]:
    params = urllib.parse.urlencode({
        "latitude": ",".join(str(r["lat"]) for r in rows),
        "longitude": ",".join(str(r["lon"]) for r in rows),
        "timezone": "auto",
        "forecast_days": 1,
    })
    req = urllib.request.Request(f"{_FORECAST_URL}?{params}",
                                 headers={"User-Agent": "tennis_model"})
    with urllib.request.urlopen(req, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload if isinstance(payload, list) else [payload]
    if len(results) != len(rows):
        raise RuntimeError(f"timezone lookup returned {len(results)} rows for {len(rows)} venues")
    return [str(result.get("timezone") or "") for result in results]


def build_table(batch_size: int = 50) -> None:
    """Regenerate the committed city-key -> IANA timezone table."""
    with _VENUE_TABLE.open(encoding="utf-8") as f:
        venues = [r for r in csv.DictReader(f) if r.get("lat") and r.get("lon")]
    out: list[dict[str, str]] = []
    for start in range(0, len(venues), batch_size):
        batch = venues[start:start + batch_size]
        zones = _fetch_timezones(batch)
        out.extend({"city_key": row["city_key"], "timezone": zone}
                   for row, zone in zip(batch, zones) if zone)
        print(f"  resolved {min(start + batch_size, len(venues))}/{len(venues)} venues")
    with TABLE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["city_key", "timezone"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    _table.cache_clear()
    print(f"wrote {len(out)} venues to {TABLE.name}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if args.build:
        build_table()
    else:
        print(f"{len(_table())} venues loaded from {TABLE.name}")
