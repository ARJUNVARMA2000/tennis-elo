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
from datetime import UTC, datetime
from pathlib import Path

from ..config import (
    FIRST_YEAR,
    FRESH_SOURCE,
    HISTORICAL_SOURCE,
    INCLUDE_CHALLENGERS,
    LOWER_TIER_FIRST_YEAR,
    TML_STATS_SOURCE,
    fresh_dir,
    historical_dir,
    lower_dir,
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
        except Exception:  # noqa: BLE001 — transient transport error: retry, then gh fallback
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
    except Exception:  # noqa: BLE001 — gh CLI absent/broken: transport unavailable, caller falls back
        return None


def _valid_csv(data: bytes, required: set[str]) -> bool:
    """A payload only counts as a match CSV if it parses and has the required columns
    (an upstream 200-with-HTML-error-page fails here instead of clobbering data)."""
    if not data or len(data) < 100:
        return False
    try:
        import pandas as pd
        head = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", nrows=5)
    except Exception:  # noqa: BLE001 — unparseable payload is by definition not a valid CSV
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


def download(tour: str, kind: str = "fresh", years=None,
             retry_rounds: int = 2, retry_budget_s: float = 90.0) -> tuple[list[int], list[int]]:
    """Fetch the given years (default: recent two for fresh, full archive for historical).
    Returns (done, failed) so callers can escalate failures (see --strict).

    Failed years get `retry_rounds` extra passes with exponential backoff. A brief
    upstream outage fails every year requested in the same instant — and BOTH tours'
    `fresh` files live in one repo, so a single bad minute reds the whole daily retrain
    (run 29812819613, which self-healed an hour later untouched). One transport miss
    should cost a backoff, not the day's model. Bounded by a wall-clock budget as well
    as a round count: a genuinely dead source must cost one slow pass, not `rounds` full
    passes over a 47-year archive that is never going to answer.
    """
    this_year = datetime.now(UTC).year
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
    deadline = time.monotonic() + retry_budget_s
    for r in range(retry_rounds):
        if not failed or time.monotonic() >= deadline:
            break
        time.sleep(min(2 ** r, max(0.0, deadline - time.monotonic())))
        retrying, failed = failed, []
        for y in retrying:
            if time.monotonic() >= deadline:   # out of budget: leave the rest failed
                failed.append(y)
                continue
            if download_year(tour, kind, y):
                done.append(y)
                print(f"  {tour}/{kind}: {y} recovered on retry {r + 1}")
            else:
                failed.append(y)
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
    this_year = datetime.now(UTC).year
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


def download_lower(full: bool = False) -> tuple[list[str], list[str]]:
    """ATP challenger + tour-qualifying overlay from the TML site (A5 experiment,
    gated by INCLUDE_CHALLENGERS at the call sites).

    full=True pulls every year from LOWER_TIER_FIRST_YEAR (bootstrap / weekly
    repair); otherwise the current year plus the in-progress-challengers file.
    Files land in lower_dir("atp") under their basename (the quali files live in an
    atp_quali/ subdir upstream). Returns (done, failed) file names.
    """
    src = TML_STATS_SOURCE
    this_year = datetime.now(UTC).year
    years = range(LOWER_TIER_FIRST_YEAR, this_year + 1) if full else [this_year]
    q_first = src.get("quali_first_year", LOWER_TIER_FIRST_YEAR)
    names = ([src["challenger_file"].format(year=y) for y in years]
             + [src["quali_file"].format(year=y) for y in years if y >= q_first]
             + [src["ongoing_challenger_file"]])
    d = lower_dir("atp")
    done, failed = [], []
    for name in names:
        data = _via_https(src["data_url"].format(name=name))
        if _valid_csv(data, _REQUIRED_STATS):
            _atomic_write(d / name.split("/")[-1], data)
            done.append(name)
        else:
            failed.append(name)
    msg = f"  atp/lower: downloaded {len(done)} file(s) from TML site"
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
    from .. import config as _cfg
    if _cfg.INCLUDE_CHALLENGERS:               # read at call time (patchable)
        _, f = download_lower(full=True)
        if f:
            failures["atp/lower"] = f
    try:
        from .wta_stats import download_wta_stats
        download_wta_stats(incremental=True)   # staleness is caught by data/health.py
    except Exception as e:                      # noqa: BLE001 — scraper must not kill the build
        print(f"  wta/stats: scrape failed ({e})")
        failures["wta/stats"] = [str(e)]
    from .live import download_live
    download_live(tours)                 # ESPN same-day overlay (best-effort)
    from .draws_wiki import download_wiki_draws
    download_wiki_draws(tours)           # authoritative full draws at release (best-effort)
    from .rankings import download_rankings
    download_rankings(tours)             # official live ranks (best-effort, not strict-fatal)
    from .charting import download_charting
    download_charting()
    return failures


def strict_fatal(failures: dict[str, list], this_year: int) -> list[str]:
    """Which download failures should red a --strict run: any stats-overlay failure,
    plus current-year files from other sources — frozen archive years are immutable
    and covered by the release-asset snapshot."""
    return [f"{src}:{i}" for src, items in failures.items()
            for i in items if "stats" in src or str(this_year) in str(i)]


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="all")
    ap.add_argument("--kind", default="fresh",
                    choices=["fresh", "historical", "stats", "lower", "live", "wiki", "all"])
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any current-year or stats download failed")
    args = ap.parse_args()
    tours = ("atp", "wta") if args.tour == "all" else (args.tour,)
    this_year = datetime.now(UTC).year
    strict_failures: list[str] = []
    if args.kind == "all":
        strict_failures += strict_fatal(download_all(tours), this_year)
    elif args.kind == "live":
        from .draws_wiki import download_wiki_draws
        from .live import download_live
        from .rankings import download_rankings
        download_live(tours)
        download_wiki_draws(tours)
        download_rankings(tours)
    elif args.kind == "wiki":
        from .draws_wiki import download_wiki_draws
        download_wiki_draws(tours)
    elif args.kind == "stats":
        _, f = download_tml_stats(full=True)
        strict_failures += [f"atp/stats:{i}" for i in f]
        from .wta_stats import download_wta_stats
        download_wta_stats(incremental=True)
    elif args.kind == "lower":
        # explicit CLI use bootstraps the archive regardless of the experiment gate
        download_lower(full=True)
    else:
        for t in tours:
            _, f = download(t, args.kind)
            strict_failures += [f"{t}/{args.kind}:{y}" for y in f if y == this_year]
    if args.strict and strict_failures:
        print(f"STRICT: {len(strict_failures)} critical download failure(s): {strict_failures}")
        sys.exit(1)
