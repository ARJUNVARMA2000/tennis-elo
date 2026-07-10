"""Bookmaker odds from Tennis-Data.co.uk, for benchmarking the model vs the market.

One spreadsheet per tour-year with Pinnacle (PSW/PSL) and Bet365 (B365W/B365L)
closing odds, in per-tour subdirs (data/raw/odds/{atp,wta}). Names there are
"Lastname F." while ours are "First Last", so both sides are normalised to a
"lastname firstinitial" key for joining.

Odds are a BENCHMARK, never a model input: downloads soft-fail (a missing year
warns; it never reddens the build). The daily workflow refreshes the current and
previous year; the archive years live in the release snapshot.

Run:  PYTHONPATH=src python -m tennis_model.data.odds [--tour all] [--archive]
"""

from __future__ import annotations

import glob
import re
import unicodedata
from datetime import UTC, datetime

import pandas as pd

from ..config import ODDS_SOURCE, TOURS, odds_dir


def normalize_name(name: str) -> str:
    """'Jannik Sinner' or 'Sinner J.' -> 'sinner j' (best-effort join key)."""
    if not isinstance(name, str) or not name.strip():
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    s = s.replace(".", " ").replace("-", " ").lower()
    toks = [t for t in re.split(r"\s+", s) if t]
    if not toks:
        return ""
    # "Sinner J" form: last token is a single-letter initial
    if len(toks[-1]) == 1:
        return f"{' '.join(toks[:-1])} {toks[-1]}"
    # "Jannik Sinner" form: first token is the given name
    return f"{' '.join(toks[1:])} {toks[0][0]}"


def download_odds(tour: str, years) -> list:
    import urllib.request
    d = odds_dir(tour)
    d.mkdir(parents=True, exist_ok=True)
    done = []
    for y in years:
        try:
            url = ODDS_SOURCE[tour].format(year=y)
            req = urllib.request.Request(url, headers={"User-Agent": "tennis_model"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) < 10_000:                 # error page, not a spreadsheet
                raise ValueError(f"suspiciously small payload ({len(data)} bytes)")
            (d / f"{y}.xlsx").write_bytes(data)
            done.append(y)
        except Exception as e:                     # noqa: BLE001 — benchmark, soft-fail
            print(f"  odds {tour}/{y}: {e} (drop {y}.xlsx into {d} manually)")
    return done


def load_odds(tour: str = "atp", years=None) -> pd.DataFrame:
    """Standardised odds frame: date, surface, best_of, winner/loser keys, odds."""
    d = odds_dir(tour)
    files = sorted(glob.glob(str(d / "*.xlsx")) + glob.glob(str(d / "*.csv")))
    if not files:
        raise FileNotFoundError(
            f"No odds files in {d}; run `python -m tennis_model.data.odds --tour {tour}`.")
    frames = []
    for f in files:
        raw = pd.read_excel(f) if f.endswith("xlsx") else pd.read_csv(f)
        frames.append(raw)
    raw = pd.concat(frames, ignore_index=True)

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw.get("Date"), errors="coerce")
    out["surface"] = raw.get("Surface")
    out["best_of"] = pd.to_numeric(raw.get("Best of"), errors="coerce").fillna(3).astype(int)
    out["w_key"] = raw.get("Winner").map(normalize_name)
    out["l_key"] = raw.get("Loser").map(normalize_name)
    # extract every book's columns; the per-row preference (ps -> b365 -> avg) is
    # applied at eval time (eval/compare._coalesce_odds) — Pinnacle left the feed
    # in Jan 2026, so a load-time pick would strand every later row
    for w, l, tag in [("PSW", "PSL", "ps"), ("B365W", "B365L", "b365"), ("AvgW", "AvgL", "avg")]:
        if w in raw and l in raw:
            out[f"odds_w_{tag}"] = pd.to_numeric(raw[w], errors="coerce")
            out[f"odds_l_{tag}"] = pd.to_numeric(raw[l], errors="coerce")
    if years:
        out = out[out["date"].dt.year.isin(set(years))]
    return out.dropna(subset=["date", "w_key", "l_key"])


def market_prob(odds_w, odds_l):
    """Vig-removed implied probability that the (actual) winner wins."""
    iw, il = 1.0 / odds_w, 1.0 / odds_l
    return iw / (iw + il)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="all")
    ap.add_argument("--archive", action="store_true",
                    help="pull the full archive (ATP 2001+, WTA 2007+), not just recent years")
    args = ap.parse_args()
    this_year = datetime.now(UTC).year
    for t in (TOURS if args.tour == "all" else (args.tour,)):
        first = (2001 if t == "atp" else 2007) if args.archive else this_year - 1
        done = download_odds(t, range(first, this_year + 1))
        print(f"  odds/{t}: downloaded {len(done)} year file(s)")
