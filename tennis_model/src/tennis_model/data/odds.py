"""Bookmaker odds from Tennis-Data.co.uk, for benchmarking the model vs the market.

One spreadsheet per year with Pinnacle (PSW/PSL) and Bet365 (B365W/B365L) closing
odds. Names there are "Lastname F." while ours are "First Last", so both sides are
normalised to a "lastname firstinitial" key for joining. Download uses plain HTTPS
(works off a normal connection; this repo's sandbox blocks non-GitHub hosts, so in
that case drop the files into data/raw/odds/ manually).
"""

from __future__ import annotations

import glob
import re
import unicodedata
from datetime import datetime, timezone

import pandas as pd

from ..config import ODDS_BASE_URL, ODDS_DIR


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


def download_odds(years) -> list:
    import urllib.request
    ODDS_DIR.mkdir(parents=True, exist_ok=True)
    done = []
    for y in years:
        try:
            url = ODDS_BASE_URL.format(year=y).replace(".zip", ".xlsx")
            req = urllib.request.Request(url, headers={"User-Agent": "tennis_model"})
            with urllib.request.urlopen(req, timeout=30) as r:
                (ODDS_DIR / f"{y}.xlsx").write_bytes(r.read())
            done.append(y)
        except Exception as e:
            print(f"  odds {y}: {e} (drop {y}.xlsx into {ODDS_DIR} manually)")
    return done


def load_odds(years=None) -> pd.DataFrame:
    """Standardised odds frame: date, surface, best_of, winner/loser keys, odds."""
    files = sorted(glob.glob(str(ODDS_DIR / "*.xlsx")) + glob.glob(str(ODDS_DIR / "*.csv")))
    if not files:
        raise FileNotFoundError(f"No odds files in {ODDS_DIR}; run download_odds() on a connected machine.")
    frames = []
    for f in files:
        d = pd.read_excel(f) if f.endswith("xlsx") else pd.read_csv(f)
        frames.append(d)
    raw = pd.concat(frames, ignore_index=True)

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw.get("Date"), errors="coerce")
    out["surface"] = raw.get("Surface")
    out["best_of"] = pd.to_numeric(raw.get("Best of"), errors="coerce").fillna(3).astype(int)
    out["w_key"] = raw.get("Winner").map(normalize_name)
    out["l_key"] = raw.get("Loser").map(normalize_name)
    # prefer Pinnacle, fall back to Bet365, then market average
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
    yrs = range(2015, datetime.now(timezone.utc).year + 1)
    print("Downloaded:", download_odds(yrs))
