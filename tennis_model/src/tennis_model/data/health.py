"""Data-freshness sentinel: fail loudly when a source quietly stops updating.

Writes data/output/health.json (surfaced to the web app if wanted) and, with
--strict, exits non-zero when any threshold breaks so the daily workflow turns red
and GitHub emails the owner — the TML GitHub freeze of Jan 2026 went unnoticed for
months precisely because every downloader failure was silent.

Run:  PYTHONPATH=src python -m tennis_model.data.health [--strict]
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pandas as pd

from ..config import (
    HEALTH_MAX_RESULT_AGE_DAYS,
    HEALTH_MAX_STATS_AGE_DAYS,
    HEALTH_MIN_STATS_FRACTION,
    HEALTH_OFFSEASON_RELAX_DAYS,
    OUTPUT_DIR,
    TOURS,
)
from .results import load_matches


def tour_health(tour: str, now: pd.Timestamp) -> dict:
    df = load_matches(tour)
    completed = df[df["completed"]]
    stats_rows = df[df["has_stats"]]
    cur = df[df["date"].dt.year == now.year]
    # empty slices give NaT maxima — report None (flagged by problems()) rather than crash
    date_max = df["date"].max() if len(df) else pd.NaT
    res_max = completed["date"].max() if len(completed) else pd.NaT
    stat_max = stats_rows["date"].max() if len(stats_rows) else pd.NaT
    return {
        "matches": int(len(df)),
        "date_max": str(date_max.date()) if pd.notna(date_max) else None,
        "result_age_days": int((now - res_max).days) if pd.notna(res_max) else None,
        "stats_date_max": str(stat_max.date()) if pd.notna(stat_max) else None,
        "stats_age_days": int((now - stat_max).days) if pd.notna(stat_max) else None,
        "cur_year_matches": int(len(cur)),
        "cur_year_stats_fraction": round(float(cur["has_stats"].mean()), 4) if len(cur) else None,
    }


def problems(tour: str, h: dict, now: pd.Timestamp) -> list[str]:
    # the season effectively ends mid-November (Finals/Davis Cup), not December —
    # relax the age gates from Nov 21 so the quiet weeks don't red the build
    offseason = now.month == 12 or (now.month == 11 and now.day > 20)
    max_result = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_RESULT_AGE_DAYS
    max_stats = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_STATS_AGE_DAYS
    min_frac = HEALTH_MIN_STATS_FRACTION.get(tour, 0.0)
    out = []
    if h["result_age_days"] is None:
        out.append(f"{tour}: no completed matches loaded")
    elif h["result_age_days"] > max_result:
        out.append(f"{tour}: newest completed match is {h['result_age_days']}d old (max {max_result})")
    if min_frac > 0:
        if h["stats_age_days"] is None or h["stats_age_days"] > max_stats:
            out.append(f"{tour}: newest serve-stats row is {h['stats_age_days']}d old (max {max_stats})")
        frac = h["cur_year_stats_fraction"]
        if frac is not None and h["cur_year_matches"] >= 100 and frac < min_frac:
            out.append(f"{tour}: current-season stats coverage {frac:.0%} < {min_frac:.0%}")
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit non-zero on any problem")
    args = ap.parse_args()

    now = pd.Timestamp(datetime.now(UTC).date())
    report, all_problems = {"generated": str(now.date()), "tours": {}}, []
    for tour in TOURS:
        h = tour_health(tour, now)
        p = problems(tour, h, now)
        h["problems"] = p
        report["tours"][tour] = h
        all_problems += p
        print(f"  health/{tour}: results to {h['date_max']}, stats to {h['stats_date_max']}, "
              f"season stats {h['cur_year_stats_fraction']}")
    report["ok"] = not all_problems

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "health.json").write_text(json.dumps(report, indent=2))
    for p in all_problems:
        print(f"  HEALTH: {p}")
    if args.strict and all_problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
