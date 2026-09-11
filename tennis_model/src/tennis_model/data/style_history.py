"""MCP profiles as of a played-date cutoff, independent of current global profiles.

Historical publication timestamps are unavailable. This retrospective policy excludes
the entire prediction day but does not claim charts were published by their played date.
"""

from __future__ import annotations

import hashlib
import json
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd

from ..config import MATCH_POPULATION_VERSION, PLAYER_ALIASES
from . import charting
from .names import name_key

STYLE_POLICY = "mcp-retrospective-played-date-strict-before-v1"
STYLE_VERSION = 1
TABLES = (("stats-Overview", "Total"), ("stats-ServeBasics", "Total"),
          ("stats-ServeDirection", "Total"), ("stats-NetPoints", "NetPoints"),
          ("stats-SnV", "SnV"), ("stats-ReturnDepth", "Total"), ("stats-KeyPointsServe", "BP"))


def identity_version() -> str:
    return hashlib.sha256(json.dumps([MATCH_POPULATION_VERSION, sorted(PLAYER_ALIASES.items())]).encode()).hexdigest()


def _key(name) -> str:
    return name_key(PLAYER_ALIASES.get(name_key(name), str(name)))


def _values(tables):
    o, b, s, n, v, r, k = (tables.get(name, {}) for name, _ in TABLES)
    sp, rp = o.get("serve_pts", 0), o.get("return_pts", 0)
    if sp < charting.MIN_SERVE_PTS:
        return None
    winners, errors = o.get("winners", 0), o.get("unforced", 0)
    fh, bh = o.get("winners_fh", 0), o.get("winners_bh", 0)
    serve_win = (o.get("first_won", 0) + o.get("second_won", 0)) / sp
    vals = (
        (o.get("aces", 0) + b.get("unret", 0)) / sp,
        charting._entropy(np.array([s.get(c, 0) for c in
            ("deuce_wide", "deuce_middle", "deuce_t", "ad_wide", "ad_middle", "ad_t")])),
        n.get("net_pts", 0) / (sp + rp), v.get("snv_pts", 0) / sp,
        winners / (winners + errors) if winners + errors else np.nan,
        fh / (fh + bh) if fh + bh else np.nan,
        (r.get("deep", 0) + r.get("very_deep", 0)) / r["returnable"] if r.get("returnable") else np.nan,
        k["pts_won"] / k["pts"] - serve_win if k.get("pts") else np.nan,
    )
    return tuple(float(v) if np.isfinite(v) else None for v in vals)


@dataclass(frozen=True)
class StyleSnapshot:
    """Immutable, pickle-safe values/counts; profile() returns a defensive copy."""

    tour: str
    cutoff: str
    source_fingerprint: str
    identity_version: str
    # (canonical key, eight values, serve points, chart count)
    profiles: tuple = ()
    policy: str = STYLE_POLICY
    version: int = STYLE_VERSION

    def profile(self, player_key: str) -> dict:
        i = bisect_left(self.profiles, (player_key,))
        if i == len(self.profiles) or self.profiles[i][0] != player_key:
            return {}
        values = self.profiles[i][1]
        return dict(zip(charting.STYLE_FEATURES, values)) if values is not None else {}

    def counts(self, player_key: str) -> tuple[float, int]:
        i = bisect_left(self.profiles, (player_key,))
        return self.profiles[i][2:] if i < len(self.profiles) and self.profiles[i][0] == player_key else (0., 0)


class StyleHistory:
    """Per-player profile revisions keyed by played day, queried strictly before."""

    def __init__(self, tour, metadata, tables, fingerprint="synthetic"):
        self.tour, self.fingerprint = tour, fingerprint
        self.identity = identity_version()
        self.histories = {}
        self.exclusions = {}
        if metadata.empty:
            if any(not f.empty for f in tables.values()):
                raise ValueError("chart statistics have no match metadata")
            return
        metadata = metadata.drop_duplicates(["match_id", "Date", "Player 1", "Player 2"])
        ambiguous = metadata.match_id.isna() | metadata.match_id.duplicated(keep=False)
        self.exclusions["ambiguousMetadataRows"] = int(ambiguous.sum())
        metadata = metadata.loc[~ambiguous].copy()
        dates = pd.to_datetime(metadata["Date"].astype(str), format="%Y%m%d", errors="coerce")
        if dates.isna().any():
            self.exclusions["invalidDateRows"] = int(dates.isna().sum())
            metadata = metadata.loc[dates.notna()]
            dates = dates.loc[dates.notna()]
        meta = {str(mid): (day, {_key(a), _key(b)}) for mid, day, a, b in
                zip(metadata.match_id, dates, metadata["Player 1"], metadata["Player 2"])}
        records = {}
        ambiguous_matches = set()
        for table, selector in TABLES:
            frame = tables.get(table, pd.DataFrame())
            if frame.empty:
                continue
            rowcol = "set" if "set" in frame else "row"
            frame = frame.loc[frame[rowcol].astype(str).eq(selector)].copy()
            frame["key"] = frame.player.map(_key)
            frame = frame.drop_duplicates()
            duplicate = frame.duplicated(["match_id", "key"], keep=False)
            ambiguous_matches.update(frame.loc[duplicate, "match_id"].astype(str))
            self.exclusions[table + ":conflictingRows"] = int(duplicate.sum())
            columns = list(frame.select_dtypes("number").columns)
            for row in frame.to_dict("records"):
                mid, key = str(row["match_id"]), row["key"]
                if mid not in meta or key not in meta[mid][1]:
                    self.exclusions[table] = self.exclusions.get(table, 0) + 1
                    continue  # unjoined evidence is excluded, counted and never inferred by names
                values = {c: float(row[c]) for c in columns if pd.notna(row[c])}
                if any(not np.isfinite(v) or v < 0 for v in values.values()):
                    raise ValueError(f"invalid chart counts in {table}")
                records.setdefault((meta[mid][0], mid, key), {})[table] = values
        totals, counts = {}, {}
        self.exclusions["conflictingMatches"] = len(ambiguous_matches)
        for (day, _mid, key), values in sorted(records.items()):
            if _mid in ambiguous_matches:
                continue
            # A partial chart lacking overview cannot establish a profile/count.
            if "stats-Overview" not in values:
                self.exclusions["withoutOverview"] = self.exclusions.get("withoutOverview", 0) + 1
                continue
            sums = totals.setdefault(key, {})
            for table, fields in values.items():
                acc = sums.setdefault(table, {})
                for c, value in fields.items():
                    acc[c] = acc.get(c, 0.) + value
            counts[key] = counts.get(key, 0) + 1
            profile = _values(sums)
            self.histories.setdefault(key, []).append((day.value, profile,
                sums["stats-Overview"].get("serve_pts", 0.), counts[key]))

    def entry_before(self, key, cutoff):
        history = self.histories.get(key, ())
        # Bisection compares only the timestamp, never profile values containing None.
        i = bisect_left(history, pd.Timestamp(cutoff).normalize().value, key=lambda x: x[0])
        return history[i - 1][1:] if i else (None, 0., 0)

    def snapshot(self, cutoff) -> StyleSnapshot:
        rows = []
        for key in sorted(self.histories):
            values, points, count = self.entry_before(key, cutoff)
            if count:
                rows.append((key, values, points, count))
        return StyleSnapshot(self.tour, str(pd.Timestamp(cutoff).normalize().date()),
                             self.fingerprint, self.identity, tuple(rows))

    def pair_features(self, matches) -> pd.DataFrame:
        out = []
        for date, a, b in zip(matches.date, matches.winner_name, matches.loser_name):
            av, *_ = self.entry_before(_key(a), date)
            bv, *_ = self.entry_before(_key(b), date)
            has = av is not None and bv is not None
            row = {"has_style": int(has)}
            row.update({s + "_diff": float(x - y) if x is not None and y is not None else 0.
                        for s, x, y in zip(charting.STYLE_FEATURES,
                            av if has else (None,) * 8, bv if has else (None,) * 8)})
            out.append(row)
        return pd.DataFrame(out, index=matches.index,
                            columns=["has_style"] + [s + "_diff" for s in charting.STYLE_FEATURES])


def source_fingerprint(tour):
    digest = hashlib.sha256()
    for name in ("matches", *(table for table, _ in TABLES)):
        path = charting.CHARTING_DIR / f"charting-{charting._GENDER[tour]}-{name}.csv"
        digest.update(path.name.encode())
        digest.update(path.read_bytes() if path.exists() else b"MISSING")
    return digest.hexdigest()


@lru_cache(maxsize=4)
def _load(tour, fingerprint, identity):
    history = StyleHistory(tour, charting._read(tour, "matches"),
                           {name: charting._read(tour, name) for name, _ in TABLES}, fingerprint)
    if source_fingerprint(tour) != fingerprint or history.identity != identity:
        raise ValueError("chart inputs changed while building history")
    return history


def load_style_history(tour):
    return _load(tour, source_fingerprint(tour), identity_version())
