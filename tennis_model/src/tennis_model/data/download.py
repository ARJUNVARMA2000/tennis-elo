"""Download match CSVs per tour and source kind.

  kind="historical"  full-schema archive (serve stats), occasional refresh
  kind="fresh"       results-only overlay, pulled ~weekly (current + previous year)

Two transports tried in order so the same code works locally, in CI, and behind a
proxy that blocks raw.githubusercontent.com:
  1. plain HTTPS GET of the raw file
  2. the authenticated GitHub API via the `gh` CLI (`Accept: application/vnd.github.raw`)
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from ..config import (
    FIRST_YEAR,
    FRESH_SOURCE,
    HISTORICAL_SOURCE,
    fresh_dir,
    historical_dir,
)


def _source(tour: str, kind: str) -> dict:
    return (HISTORICAL_SOURCE if kind == "historical" else FRESH_SOURCE)[tour]


def _dir(tour: str, kind: str):
    return historical_dir(tour) if kind == "historical" else fresh_dir(tour)


def _via_https(url: str) -> bytes | None:
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "tennis_model"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        return data if data else None
    except Exception:
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


def download_year(tour: str, kind: str, year: int) -> bool:
    src = _source(tour, kind)
    data = _via_https(src["raw"].format(year=year)) or _via_gh(src["repo"], src["path"].format(year=year))
    if not data or len(data) < 100:
        return False
    d = _dir(tour, kind)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{year}.csv").write_bytes(data)
    return True


def download(tour: str, kind: str = "fresh", years=None) -> list[int]:
    """Fetch the given years (default: recent two for fresh, full archive for historical)."""
    this_year = datetime.now(timezone.utc).year
    if years is None:
        years = [this_year - 1, this_year] if kind == "fresh" else range(FIRST_YEAR, this_year + 1)
    done = [y for y in years if download_year(tour, kind, y)]
    print(f"  {tour}/{kind}: downloaded {len(done)} year file(s)")
    return done


def download_fresh(tours=("atp", "wta")) -> None:
    """Weekly refresh: pull the results-only overlay for both tours."""
    for t in tours:
        download(t, "fresh")


def download_all(tours=("atp", "wta")) -> None:
    """Full bootstrap (used by CI / a fresh clone): historical + fresh + live + charting."""
    for t in tours:
        download(t, "historical")
        download(t, "fresh")
    from .live import download_live
    download_live(tours)                 # ESPN same-day overlay (best-effort)
    from .charting import download_charting
    download_charting()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="all")
    ap.add_argument("--kind", default="fresh", choices=["fresh", "historical", "live", "all"])
    args = ap.parse_args()
    tours = ("atp", "wta") if args.tour == "all" else (args.tour,)
    if args.kind == "all":
        download_all(tours)
    elif args.kind == "live":
        from .live import download_live
        download_live(tours)
    else:
        for t in tours:
            download(t, args.kind)
