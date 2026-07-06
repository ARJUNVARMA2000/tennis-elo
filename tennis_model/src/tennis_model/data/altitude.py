"""Venue altitude table for the altitude feature experiment (Phase C).

A static, committed CSV (venue_altitude.csv, next to this module) maps geo.py's
normalized city keys to elevation in meters. Altitude is time-invariant, so one
lookup per venue covers 1980-present; like geo.py's country map, the table only
ever needs to be RIGHT, never complete — unknown venues resolve to None and the
feature records 0 (sea-level-ish, the overwhelming mode).

Build/refresh (one-off, ~300 geocoding calls):
  PYTHONPATH=src python -m tennis_model.data.altitude --build

Runtime: altitude_m("Bogota Open") -> 2582.0 via geo.city_key resolution, so
sponsor-prefixed variants resolve exactly like the home-advantage feature.

Geocoding: the free open-meteo geocoding API (returns elevation directly); each
candidate is accepted only if its ISO-3166 country matches the venue's IOC country
from geo.CITY_IOC — that disambiguates Halle/GER from Halle/BEL, Melbourne/AUS
from Melbourne/US, etc. Mismatches are logged and left out of the table.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from functools import cache
from pathlib import Path

from .geo import CITY_IOC, city_key

TABLE = Path(__file__).with_name("venue_altitude.csv")
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search?count=10&language=en&format=json&name={q}"

# IOC -> ISO-3166 alpha-2, for the countries appearing in geo.CITY_IOC.
_IOC_ISO2 = {
    "AUS": "AU", "GBR": "GB", "USA": "US", "FRA": "FR", "GER": "DE", "ITA": "IT",
    "ESP": "ES", "SUI": "CH", "AUT": "AT", "NED": "NL", "BEL": "BE", "SWE": "SE",
    "DEN": "DK", "CZE": "CZ", "SVK": "SK", "FIN": "FI", "POL": "PL", "RUS": "RU",
    "CRO": "HR", "SLO": "SI", "SRB": "RS", "BIH": "BA", "HUN": "HU", "ROU": "RO",
    "BUL": "BG", "GRE": "GR", "TUR": "TR", "POR": "PT", "LUX": "LU", "MON": "MC",
    "SMR": "SM", "EST": "EE", "LAT": "LV", "ISR": "IL", "QAT": "QA", "UAE": "AE",
    "KSA": "SA", "MAR": "MA", "TUN": "TN", "RSA": "ZA", "CHN": "CN", "HKG": "HK",
    "TPE": "TW", "JPN": "JP", "KOR": "KR", "IND": "IN", "VIE": "VN", "THA": "TH",
    "MAS": "MY", "SGP": "SG", "INA": "ID", "UZB": "UZ", "KAZ": "KZ", "AZE": "AZ",
    "NZL": "NZ", "MEX": "MX", "CAN": "CA", "COL": "CO", "ECU": "EC", "CHI": "CL",
    "ARG": "AR", "BRA": "BR", "URU": "UY", "PUR": "PR", "BER": "BM",
}

# City keys whose text is not directly geocodable: event names, suffixed variants,
# regions. Values are the geocoding query (city the event is/was played in).
_QUERY_ALIAS = {
    "australian open": "Melbourne", "us open": "New York", "roland garros": "Paris",
    "wimbledon": "London", "queen s club": "London", "queens club": "London",
    "queens": "London", "london olympics": "London",
    "indian wells masters": "Indian Wells", "miami masters": "Miami",
    "cincinnati masters": "Cincinnati", "paris masters": "Paris",
    "paris olympics": "Paris", "monte carlo masters": "Monte-Carlo",
    "monte carlo": "Monte-Carlo", "canada masters": "Toronto",
    "canadian open": "Toronto", "washington dc": "Washington",
    "german open": "Hamburg", "kremlin cup": "Moscow",
    "japan open": "Tokyo", "japan open tokyo": "Tokyo", "tokyo outdoor": "Tokyo",
    "tokyo indoor": "Tokyo", "tokyo japan open": "Tokyo", "tokyo nichirei": "Tokyo",
    "tokyo pan pacific": "Tokyo", "tokyo olympics": "Tokyo",
    "sydney outdoor": "Sydney", "sydney indoor": "Sydney", "sydney olympics": "Sydney",
    "stuttgart outdoor": "Stuttgart", "stuttgart indoor": "Stuttgart",
    "stuttgart masters": "Stuttgart", "hamburg masters": "Hamburg",
    "rome masters": "Rome", "madrid masters": "Madrid",
    "stockholm masters": "Stockholm", "shanghai masters": "Shanghai",
    "atlanta olympics": "Atlanta", "athens olympics": "Athens",
    "barcelona olympics": "Barcelona", "beijing olympics": "Beijing",
    "rio olympics": "Rio de Janeiro",
    "shenzhen finals": "Shenzhen", "cancun finals": "Cancun",
    "guadalajara finals": "Guadalajara", "fort worth finals": "Fort Worth",
    "murray river open": "Melbourne", "great ocean road open": "Melbourne",
    "gippsland trophy": "Melbourne", "yarra valley classic": "Melbourne",
    "phillip island trophy": "Melbourne", "grampians trophy": "Melbourne",
    "united cup": "Sydney", "atp cup": "Sydney",
    "s hertogenbosch": "Hertogenbosch", "rosmalen": "Rosmalen",
    "st poelten": "Sankt Polten", "poertschach": "Portschach",
    "maria lankowitz": "Maria Lankowitz", "styria": "Bad Waltersdorf",
    "serbia": "Belgrade", "sardinia": "Cagliari", "bahia": "Salvador",
    "costa do sauipe": "Mata de Sao Joao", "key biscayne": "Key Biscayne",
    "kugayama": "Tokyo", "ibaraki": "Mito", "oahu": "Honolulu",
    "hope island": "Hope Island", "mexico city": "Mexico City",
    "vina del mar": "Vina del Mar", "m rida": "Merida", "hilton head": "Hilton Head Island",
    "bol": "Bol", "cluj napoca": "Cluj-Napoca", "knokke heist": "Knokke-Heist",
    "winston salem": "Winston-Salem", "ho chi minh city": "Ho Chi Minh City",
    "nur sultan": "Astana", "delray beach": "Delray Beach", "ponte vedra beach": "Ponte Vedra Beach",
    "cabo san lucas": "Cabo San Lucas", "los cabos": "Cabo San Lucas",
    "kuala lumpur": "Kuala Lumpur", "new delhi": "New Delhi",
    "san jose": "San Jose", "santiago": "Santiago",
    "bangalore": "Bengaluru", "marrakech": "Marrakesh",
    "new york open": "Uniondale", "quebec city": "Quebec",
}
# Circuits/team events with no fixed venue: never geocode.
_SKIP = {"australia circuit", "mexico circuit", "world team cup",
         "world team championship", "grand slam cup"}


@cache
def _table() -> dict[str, float]:
    if not TABLE.exists():
        return {}
    with TABLE.open(encoding="utf-8") as f:
        return {r["city_key"]: float(r["elevation_m"]) for r in csv.DictReader(f)
                if r.get("elevation_m")}


def altitude_m(tourney_name: str) -> float | None:
    """Venue elevation in meters for a tournament name, or None if unknown."""
    key = city_key(tourney_name)
    return _table().get(key) if key is not None else None


# ---------------------------------------------------------------------------
# builder (offline, one-off)
# ---------------------------------------------------------------------------
def _geocode(query: str, iso2: str | None) -> dict | None:
    url = GEOCODE_URL.format(q=urllib.parse.quote(query))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "tennis_model"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 — builder is offline tooling; report and move on
        print(f"    geocode error for {query!r}: {e}")
        return None
    for res in data.get("results") or []:
        if iso2 is None or str(res.get("country_code", "")).upper() == iso2:
            return res
    return None


def build_table() -> None:
    rows, unresolved = [], []
    for key, ioc in sorted(CITY_IOC.items()):
        if key in _SKIP:
            continue
        query = _QUERY_ALIAS.get(key, key)
        res = _geocode(query, _IOC_ISO2.get(ioc))
        time.sleep(0.15)
        if res is None or res.get("elevation") is None:
            unresolved.append(key)
            print(f"  UNRESOLVED: {key!r} (query {query!r}, {ioc})")
            continue
        rows.append({"city_key": key, "ioc": ioc, "query": query,
                     "resolved_name": res.get("name"),
                     "lat": res.get("latitude"), "lon": res.get("longitude"),
                     "elevation_m": res.get("elevation")})
    with TABLE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} venues to {TABLE.name}; {len(unresolved)} unresolved")
    top = sorted(rows, key=lambda r: -float(r["elevation_m"]))[:12]
    print("highest venues:")
    for r in top:
        print(f"  {r['city_key']:<24}{r['ioc']:<5}{r['elevation_m']:>7.0f} m  ({r['resolved_name']})")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="regenerate venue_altitude.csv")
    args = ap.parse_args()
    if args.build:
        build_table()
    else:
        print(f"{len(_table())} venues loaded from {TABLE.name}")
