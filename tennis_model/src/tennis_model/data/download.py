"""Download match CSVs per tour and source kind.

  kind="historical"  full-schema archive (serve stats), frozen upstreams, rare refresh
  kind="stats"       full-schema overlay from the TML site (ATP), updated daily
  kind="fresh"       results-only overlay, pulled ~weekly (current + previous year)

Two transports tried in order so the same code works locally, in CI, and behind a
proxy that blocks raw.githubusercontent.com:
  1. plain HTTPS GET of the raw file
  2. the authenticated GitHub API via the `gh` CLI (`Accept: application/vnd.github.raw`)
     (GitHub-hosted sources only — the TML site has no gh fallback and instead retries)

Every payload is schema-validated before it replaces an existing file, and the write
is atomic — a source that starts returning error pages can never clobber good data.
"""

from __future__ import annotations

import io
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from ..config import (
    FIRST_YEAR,
    FRESH_SOURCE,
    HISTORICAL_SOURCE,
    INCLUDE_CHALLENGERS,
    TML_STATS_SOURCE,
    fresh_dir,
    historical_dir,
    stats_dir,
)

# Columns any usable match CSV must carry; full-schema sources must also carry stats.
_REQUIRED_BASE = {"tourney_date", "winner_name", "loser_name", "score"}
_REQUIRED_STATS = _REQUIRED_BASE | {"w_svpt", "l_svpt"}


def _source(tour: str, kind: str) -> dict:
    return (HISTORICAL_SOURCE if kind == "historical" else FRESH_SOURCE)[tour]


def _dir(tour: str, kind: str):
    return historical_dir(tour) if kind == "historical" else fresh_dir(tour)


def _via_https(url: str, retries: int = 3) -> bytes | None:
    import urllib.request
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tennis_model"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if data:
                return data
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return None


def _via_gh(repo: str, path: str) -> bytes | None:
    try:
        out = subprocess.run(
            ["gh", "api", "-H", "Accept: application/vnd.github.raw",
             f"repos/{repo}/contents/{path}"],
            capture_output=True, timeout=60,
        )
        return out.stdout if out.returncode == 0 and out.stdout else None
    except Exception:
        return None


def _valid_csv(data: bytes, required: set[str]) -> bool:
    """A payload only counts as a match CSV if it parses and has the required columns
    (an upstream 200-with-HTML-error-page fails here instead of clobbering data)."""
    if not data or len(data) < 100:
        return False
    try:
        import pandas as pd
        head = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", nrows=5)
    except Exception:
        return False
    return required.issubset(set(head.columns))


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def download_year(tour: str, kind: str, year: int) -> bool:
    src = _source(tour, kind)
    data = _via_https(src["raw"].format(year=year), retries=1) or _via_gh(src["repo"], src["path"].format(year=year))
    required = _REQUIRED_STATS if kind == "historical" else _REQUIRED_BASE
    if not _valid_csv(data, required):
        return False
    _atomic_write(_dir(tour, kind) / f"{year}.csv", data)
    return True


def download(tour: str, kind: str = "fresh", years=None) -> tuple[list[int], list[int]]:
    """Fetch the given years (default: recent two for fresh, full archive for historical).
    Returns (done, failed) so callers can escalate failures (see --strict)."""
    this_year = datetime.now(timezone.utc).year
    if years is None:
        if kind == "fresh":
            years = [this_year - 1, this_year]
        else:
            # frozen archives end at a known year — requesting later files would only
            # produce guaranteed failures that trip the strict gate
            last = min(_source(tour, kind).get("last_year", this_year), this_year)
            years = range(FIRST_YEAR, last + 1)
    done, failed = [], []
    for y in years:
        (done if download_year(tour, kind, y) else failed).append(y)
    msg = f"  {tour}/{kind}: downloaded {len(done)} year file(s)"
    if failed:
        msg += f", FAILED {len(failed)}: {failed}"
    print(msg)
    return done, failed


def download_tml_stats(full: bool = False,
                       include_challengers: bool = INCLUDE_CHALLENGERS) -> tuple[list[str], list[str]]:
    """ATP full-schema overlay from stats.tennismylife.org (daily-updated year CSVs).

    full=True re-pulls every year from first_year (bootstrap / weekly repair);
    otherwise only the current year — retro corrections land via the weekly full run.
    Returns (done, failed) file names.
    """
    src = TML_STATS_SOURCE
    this_year = datetime.now(timezone.utc).year
    years = range(src["first_year"], this_year + 1) if full else [this_year]
    names = [src["year_file"].format(year=y) for y in years]
    if include_challengers:
        names += [src["challenger_file"].format(year=y) for y in years]
    d = stats_dir("atp")
    done, failed = [], []
    for name in names:
        data = _via_https(src["data_url"].format(name=name))
        if _valid_csv(data, _REQUIRED_STATS):
            _atomic_write(d / name, data)
            done.append(name)
        else:
            failed.append(name)
    msg = f"  atp/stats: downloaded {len(done)} file(s) from TML site"
    if failed:
        msg += f", FAILED {len(failed)}: {failed}"
    print(msg)
    return done, failed


def download_fresh(tours=("atp", "wta")) -> None:
    """Weekly refresh: pull the results-only overlay for both tours."""
    for t in tours:
        download(t, "fresh")


def download_all(tours=("atp", "wta")) -> dict[str, list]:
    """Full bootstrap (used by CI / a fresh clone): historical + stats + fresh + live
    + charting. Returns {source: failed_items} for the strict health gate."""
    failures: dict[str, list] = {}
    for t in tours:
        _, f = download(t, "historical")
        if f:
            failures[f"{t}/historical"] = f
        _, f = download(t, "fresh")
        if f:
            failures[f"{t}/fresh"] = f
    _, f = download_tml_stats(full=True)
    if f:
        failures["atp/stats"] = f
    try:
        from .wta_stats import download_wta_stats
        download_wta_stats(incremental=True)   # staleness is caught by data/health.py
    except Exception as e:                      # noqa: BLE001 — scraper must not kill the build
        print(f"  wta/stats: scrape failed ({e})")
        failures["wta/stats"] = [str(e)]
    from .live import download_live
    download_live(tours)                 # ESPN same-day overlay (best-effort)
    from .charting import download_charting
    download_charting()
    return failures


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="all")
    ap.add_argument("--kind", default="fresh",
                    choices=["fresh", "historical", "stats", "live", "all"])
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any current-year or stats download failed")
    args = ap.parse_args()
    tours = ("atp", "wta") if args.tour == "all" else (args.tour,)
    this_year = datetime.now(timezone.utc).year
    strict_failures: list[str] = []
    if args.kind == "all":
        fails = download_all(tours)
        for src_name, items in fails.items():
            # only current-year (or stats-overlay) failures are fatal: the archive
            # years are immutable and covered by the release-asset snapshot
            fatal = [i for i in items if "stats" in src_name or str(this_year) in str(i)]
            strict_failures += [f"{src_name}:{i}" for i in fatal]
    elif args.kind == "live":
        from .live import download_live
        download_live(tours)
    elif args.kind == "stats":
        _, f = download_tml_stats(full=True)
        strict_failures += [f"atp/stats:{i}" for i in f]
        from .wta_stats import download_wta_stats
        download_wta_stats(incremental=True)
    else:
        for t in tours:
            _, f = download(t, args.kind)
            strict_failures += [f"{t}/{args.kind}:{y}" for y in f if y == this_year]
    if args.strict and strict_failures:
        print(f"STRICT: {len(strict_failures)} critical download failure(s): {strict_failures}")
        sys.exit(1)
