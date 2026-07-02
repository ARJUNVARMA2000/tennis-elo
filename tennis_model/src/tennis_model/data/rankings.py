"""Official live rankings scraped from live-tennis.eu (server-rendered table id=u868).

The pages 403 non-browser user agents and sit behind Cloudflare, which may challenge
datacenter IPs, so the scrape is best-effort like data/live.py: any failure (block,
layout drift, thin parse) prints a skip note and KEEPS the previous rankings.json —
live_dir is carried in the CI data cache, so the site degrades to hours-stale official
ranks, never to a broken build. The hourly quick run is the retry loop.

Row cells after tag-stripping (verified 2026-07):
  [0]=rank  [1]=career-high marker  [2]=''  [3]=name  [4]=age  [5]=country
  [6]=points  [7]=rank +/- vs last official release  [8]=points +/-  [9+]=tournament
Some rows are shorter (player not in an event); ad/header rows fail the digit gates.

Run:  PYTHONPATH=src python -m tennis_model.data.rankings
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser

from ..config import TOURS, live_dir
from .names import name_key

URLS = {
    "atp": "https://live-tennis.eu/en/atp-live-ranking",
    "wta": "https://live-tennis.eu/en/wta-live-ranking",
}
# A real browser UA is required (plain clients get 403).
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
TABLE_ID = "u868"
MIN_ROWS = 100        # a Cloudflare challenge page parses to ~0 rows -> fails closed

# ø/đ/ł don't NFKD-decompose, so the shared name_key can't fold them (Møller vs Moller);
# fold them source-side before keying. The model side never carries them (ASCII archive).
_LATIN_FOLD = str.maketrans({"ø": "o", "Ø": "O", "đ": "d", "Đ": "D", "ł": "l", "Ł": "L", "ß": "ss"})

# Model-side spellings that no mechanical rule reconciles with live-tennis.eu's:
# source key -> EXTRA key indexed for the same player (additive, because players.json
# can carry the same human under two spellings from different data sources — e.g. both
# "Daniel Merida" and "Daniel Merida Aguilar" — and both rows should get the rank).
# Grown from observed misses; the "matched N/200" export log line flags new ones.
ALIASES = {
    "aleksandr shevchenko": "alexander shevchenko",
    "daniel merida": "daniel merida aguilar",
    "christopher o connell": "christopher oconnell",
    "andy andrade": "andres andrade",
    "ludmilla samsonova": "liudmila samsonova",
    "yulia starodubtseva": "yuliia starodubtseva",
    "caty mcnally": "catherine mcnally",
    "tyra grant": "tyra caterina grant",
    "tiantsoa rakotomanga rajaonah": "tiantsoa sarah rakotomanga rajaonah",
}


def _source_key(name: str) -> str:
    """Join key for a live-tennis.eu display name (shared name_key after Latin fold)."""
    return name_key(name.translate(_LATIN_FOLD))


def _fetch(tour: str) -> str:
    req = urllib.request.Request(URLS[tour], headers={
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


class _RankingTable(HTMLParser):
    """Collects the text of every <td> that is a DIRECT cell of the id=u868 table.

    The page nests whole <table>s inside header cells (tab menu), so a depth counter
    gates collection to depth 1; nested-table text is dropped. HTMLParser handles the
    minified unquoted attributes (<table id=u868>) and, with convert_charrefs on,
    delivers &nbsp; as \xa0 which we fold to a space.
    """

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._depth = 0                      # 0 = outside u868, 1 = direct children
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self._depth:
                self._depth += 1
            elif dict(attrs).get("id") == TABLE_ID:
                self._depth = 1
        elif self._depth == 1 and tag == "tr":
            self._row = []
        elif self._depth == 1 and tag in ("td", "th"):
            self._cell = []

    def handle_endtag(self, tag):
        if tag == "table" and self._depth:
            self._depth -= 1
            if self._depth == 0:
                self._row = None
                self._cell = None
        elif self._depth == 1 and tag in ("td", "th") and self._cell is not None:
            if self._row is not None:
                self._row.append("".join(self._cell).replace("\xa0", " ").strip())
            self._cell = None
        elif self._depth == 1 and tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._depth == 1 and self._cell is not None:
            self._cell.append(data)


def parse_rankings(html: str) -> list[dict]:
    """Table rows -> [{rank, name, points, delta}] in document (rank-ascending) order.

    delta is the rank change vs the last official release (None when blank). Header,
    separator and short rows fail the digit gates and are skipped.
    """
    p = _RankingTable()
    p.feed(html)
    out = []
    for cells in p.rows:
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        name = cells[3].strip()
        pts = cells[6].replace(",", "").strip()
        if not name or not pts.isdigit():
            continue
        delta = int(cells[7]) if len(cells) > 7 and re.fullmatch(r"[+-]\d+", cells[7].strip()) else None
        out.append({"rank": int(cells[0]), "name": name, "points": int(pts), "delta": delta})
    return out


def _validate(rows: list[dict]) -> None:
    if len(rows) < MIN_ROWS:
        raise ValueError(f"only {len(rows)} rows parsed (layout change or challenge page?)")
    if rows[0]["rank"] != 1:
        raise ValueError(f"first rank is {rows[0]['rank']}, expected 1")


def download_rankings(tours=TOURS) -> None:
    for tour in tours:
        try:
            rows = parse_rankings(_fetch(tour))
            _validate(rows)
        except Exception as e:  # noqa: BLE001 — best-effort, never build-fatal
            print(f"  rankings/{tour}: skipped ({e}) — keeping previous file")
            continue
        players: dict[str, dict] = {}
        for r in rows:
            k = _source_key(r["name"])
            if k in players:               # rank-ascending order: first seen = better rank
                continue
            players[k] = r
        for src, extra in ALIASES.items():   # index known alternate spellings under both keys
            if src in players:
                players.setdefault(extra, players[src])
        d = live_dir(tour)
        d.mkdir(parents=True, exist_ok=True)
        payload = {"fetched": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "source": URLS[tour], "players": players}
        tmp = d / "rankings.json.tmp"
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, d / "rankings.json")
        print(f"  rankings/{tour}: {len(players)} players (No.1 {rows[0]['name']}) "
              f"-> {d / 'rankings.json'}")


def load_rankings(tour: str) -> dict:
    """players dict from the last good rankings.json; {} when absent or corrupt."""
    p = live_dir(tour) / "rankings.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("players", {}) if p.exists() else {}
    except Exception:  # noqa: BLE001
        return {}


if __name__ == "__main__":
    download_rankings()
