"""Preserve adopted rating inputs across Actions-cache eviction and recovery.

The WTA qualifying/125 archive is acquired separately from daily current-season
updates. Losing an older year can silently remove otherwise eligible draw entrants.
Restore only absent files, so recovery never rolls a warm live/current-year cache back.
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from ..config import DATA_DIR, WTA_DUAL_STATE_GATE_THRESHOLD, WTA_LOWER_STATE_FIRST_YEAR

SNAPSHOT_DIRS = (
    "raw/atp/historical", "raw/atp/stats", "raw/atp/lower",
    "raw/wta/historical", "raw/wta/stats", "raw/wta/lower",
    "raw/atp/live", "raw/wta/live", "raw/charting", "raw/odds", "raw/kalshi",
)


def missing_lower_history(directory: Path, *, year: int | None = None) -> list[int]:
    """Missing/empty/malformed completed seasons required by the adopted WTA state."""
    if WTA_DUAL_STATE_GATE_THRESHOLD is None:
        return []
    current = year if year is not None else datetime.now(UTC).year
    missing = []
    for season in range(WTA_LOWER_STATE_FIRST_YEAR, current):
        path = directory / f"{season}_wta_lower.csv"
        try:
            if path.is_symlink():
                raise ValueError("symlink is not an archive input")
            with path.open(encoding="utf-8", newline="") as stream:
                rows = csv.DictReader(stream)
                row = next(rows)
                if not all(row.get(key) for key in (
                        "tourney_date", "winner_name", "loser_name", "draw_level")):
                    raise ValueError("missing lower-state columns/row")
        except (OSError, ValueError, StopIteration, csv.Error):
            missing.append(season)
    return missing


def archive_problems(root: Path, *, year: int | None = None) -> list[str]:
    problems = []
    for relative in ("raw/atp/historical/2020.csv", "raw/wta/stats/2024.csv"):
        if not (root / relative).is_file() or not (root / relative).stat().st_size:
            problems.append(relative)
    for relative in ("raw/atp/live", "raw/wta/live"):
        if not (root / relative).is_dir():
            problems.append(relative)
    problems.extend(f"raw/wta/lower/{season}_wta_lower.csv" for season in
                    missing_lower_history(root / "raw/wta/lower", year=year))
    return problems


def create_archive(root: Path, destination: Path, *, year: int | None = None) -> None:
    problems = archive_problems(root, year=year)
    if problems:
        raise ValueError(f"refusing incomplete recovery snapshot: {', '.join(problems)}")
    with tarfile.open(destination, "w:gz") as archive:
        for relative in SNAPSHOT_DIRS:
            path = root / relative
            if path.is_dir():
                archive.add(path, arcname=relative)


def restore_archive(root: Path, source: Path, *, year: int | None = None) -> None:
    missing = archive_problems(root, year=year)
    with tempfile.TemporaryDirectory(prefix="deuce-archive-") as temporary:
        staged = Path(temporary)
        with tarfile.open(source, "r:gz") as archive:
            members = archive.getmembers()
            if any(not (member.isfile() or member.isdir()) for member in members):
                raise ValueError("recovery snapshot contains a link or special file")
            if any(not any(member.name == name or member.name.startswith(name + "/")
                           for name in SNAPSHOT_DIRS) for member in members):
                raise ValueError("recovery snapshot contains an unexpected path")
            archive.extractall(staged, members=members, filter="data")
        problems = archive_problems(staged, year=year)
        if problems:
            raise ValueError(f"recovery snapshot is incomplete: {', '.join(problems)}")
        # Revoke before the first input write. A crash must not leave an accepted old
        # predictor paired with newly restored history; quick mode rebuilds a missing pkl.
        if any(name.startswith("raw/wta/lower/") for name in missing):
            (root / "output/wta/predictor.pkl").unlink(missing_ok=True)
        for relative in SNAPSHOT_DIRS:
            directory = staged / relative
            if not directory.is_dir():
                continue
            (root / relative).mkdir(parents=True, exist_ok=True)
            for path in sorted(directory.rglob("*")):
                target = root / path.relative_to(staged)
                if path.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                elif not target.exists() or str(path.relative_to(staged)) in missing:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    fd, temporary_path = tempfile.mkstemp(dir=target.parent)
                    try:
                        with os.fdopen(fd, "wb") as stream, path.open("rb") as src:
                            shutil.copyfileobj(src, stream)
                        os.replace(temporary_path, target)
                    finally:
                        Path(temporary_path).unlink(missing_ok=True)
        remaining = archive_problems(root, year=year)
        if remaining:
            raise ValueError(f"recovery remains incomplete: {', '.join(remaining)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "create", "restore"))
    parser.add_argument("archive", nargs="?", type=Path)
    args = parser.parse_args()
    if args.action == "check":
        problems = archive_problems(DATA_DIR)
        if problems:
            print("missing recovery inputs: " + ", ".join(problems))
            raise SystemExit(1)
    elif args.archive is None:
        parser.error("create/restore requires an archive path")
    elif args.action == "create":
        create_archive(DATA_DIR, args.archive)
    else:
        restore_archive(DATA_DIR, args.archive)


if __name__ == "__main__":
    main()
