"""Load and clean match data into one tidy, chronologically sortable frame per tour.

Each tour merges two sources (see config): a full-schema HISTORICAL archive (with
serve stats) and a results-only FRESH overlay (kept current ~weekly). They are
normalised to a common schema, concatenated, and de-duplicated — preferring the
row that carries serve stats — so the point model sees stats where available while
Elo/rank stay current to last week.
"""

from __future__ import annotations

import glob
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import (
    DEFAULT_TIER_K_MULT,
    ROUND_ORDER,
    SURFACE_MAP,
    TIER_K_MULT,
    TIER_NAMES,
    fresh_dir,
    historical_dir,
)
from .scores import parse_score

# Canonical column set every loaded frame is reindexed to, so downstream code never
# hits a missing column regardless of which source (full vs results-only) it came from.
_STAT_COLS = [f"{s}_{c}" for s in ("w", "l")
              for c in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")]
CANON = [
    "tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor",
    "tourney_date", "match_num", "round", "best_of", "score", "minutes",
    "winner_name", "loser_name", "winner_hand", "loser_hand", "winner_ht", "loser_ht",
    "winner_age", "loser_age", "winner_ioc", "loser_ioc", "winner_id", "loser_id",
    "winner_rank", "loser_rank", "winner_rank_points", "loser_rank_points",
] + _STAT_COLS


def _read_dir(d: Path) -> pd.DataFrame:
    files = sorted(glob.glob(str(d / "*.csv")))
    frames = []
    for f in files:
        df = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
        df = df.reindex(columns=[c for c in set(CANON) | set(df.columns)])  # keep extras, ensure canon
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=CANON)
    out = pd.concat(frames, ignore_index=True)
    return out.reindex(columns=sorted(set(CANON) | set(out.columns), key=str))


def _parse_dates(s: pd.Series) -> pd.Series:
    """Handle both YYYYMMDD (historical) and YYYY/M/D (fresh overlay)."""
    s = s.astype("string").str.strip()
    d = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    miss = d.isna() & s.notna()
    if miss.any():
        d.loc[miss] = pd.to_datetime(s[miss].str.replace("/", "-", regex=False), errors="coerce")
    return d


def _score_key(score: object) -> str:
    if not isinstance(score, str):
        return ""
    return re.sub(r"\(\d+\)", "", score).replace(" ", "").strip()


def _name_key(name: object) -> str:
    """Accent/punctuation-insensitive key so the same player matches across sources."""
    if not isinstance(name, str):
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c))
    s = re.sub(r"[-.'`]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def _canonicalize_names(df: pd.DataFrame) -> pd.DataFrame:
    """Unify spellings across sources (e.g. 'Felix Auger Aliassime' -> 'Felix
    Auger-Aliassime') by mapping every name to one canonical spelling per key,
    preferring the historical (Sackmann) spelling, then the most frequent."""
    rec = pd.DataFrame({
        "name": pd.concat([df["winner_name"], df["loser_name"]], ignore_index=True),
        "src": pd.concat([df["__src"], df["__src"]], ignore_index=True),
    })
    rec["key"] = rec["name"].map(_name_key)
    rec = rec[rec["key"] != ""]
    grp = rec.groupby(["key", "name", "src"]).size().reset_index(name="n")
    grp = grp.sort_values(["key", "src", "n"], ascending=[True, True, False])
    canon = grp.drop_duplicates("key", keep="first").set_index("key")["name"].to_dict()
    for who in ("winner_name", "loser_name"):
        df[who] = df[who].map(lambda x: canon.get(_name_key(x), x))
    return df


def merge_sources(tour: str) -> pd.DataFrame:
    """Concatenate historical + fresh for a tour and de-dup, preferring stat-bearing rows."""
    hist = _read_dir(historical_dir(tour))
    fresh = _read_dir(fresh_dir(tour))
    hist["__src"] = 0          # historical first => wins de-dup ties (it carries serve stats)
    fresh["__src"] = 1
    df = pd.concat([hist, fresh], ignore_index=True)
    df["date"] = _parse_dates(df["tourney_date"])
    df = df[df["date"].notna() & df["winner_name"].notna() & df["loser_name"].notna()].copy()
    df = _canonicalize_names(df)

    has_stats = pd.to_numeric(df["w_svpt"], errors="coerce").notna()
    df["__key"] = (df["winner_name"].astype(str) + "|" + df["loser_name"].astype(str)
                   + "|" + df["score"].map(_score_key))
    # prefer rows that have stats, then the historical source
    df = df.assign(__hs=has_stats.astype(int)).sort_values(["__hs", "__src"], ascending=[False, True])
    df = df.drop_duplicates(subset="__key", keep="first").drop(columns=["__hs", "__key", "__src"])
    return df


def _backfill_bios(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing hand/height on (fresh) rows from each player's known values."""
    hand, ht = {}, {}
    for who in ("winner", "loser"):
        for nm, h, t in zip(df[f"{who}_name"], df[f"{who}_hand"], df[f"{who}_ht"]):
            if isinstance(h, str) and nm not in hand:
                hand[nm] = h
            if pd.notna(t) and nm not in ht:
                ht[nm] = t
    for who in ("winner", "loser"):
        df[f"{who}_hand"] = df[f"{who}_hand"].where(df[f"{who}_hand"].notna(),
                                                    df[f"{who}_name"].map(hand))
        df[f"{who}_ht"] = df[f"{who}_ht"].where(df[f"{who}_ht"].notna(),
                                                df[f"{who}_name"].map(ht))
    return df


def _tier_name(level: object) -> str:
    return TIER_NAMES.get(str(level), "atp250")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived/normalised columns (robust to columns absent in the fresh schema)."""
    df = df.copy()
    if "date" not in df:
        df["date"] = _parse_dates(df["tourney_date"])
    df = df[df["date"].notna() & df["winner_name"].notna() & df["loser_name"].notna()]

    df["surface_b"] = df["surface"].map(SURFACE_MAP).fillna("Hard")
    df["tier"] = df["tourney_level"].map(_tier_name)
    df["tier_k"] = df["tier"].map(TIER_K_MULT).fillna(DEFAULT_TIER_K_MULT)
    df["round_order"] = df["round"].map(ROUND_ORDER).fillna(3).astype(int)
    df["is_indoor"] = df["indoor"].map({"I": True, "O": False})

    parsed = df["score"].map(parse_score)
    df["w_games"] = [p.winner_games for p in parsed]
    df["l_games"] = [p.loser_games for p in parsed]
    df["completed"] = [p.completed for p in parsed]
    df["walkover"] = [p.walkover for p in parsed]
    df["game_diff"] = df["w_games"] - df["l_games"]

    svpt = pd.to_numeric(df["w_svpt"], errors="coerce")
    df["w_svpt"] = svpt
    df["l_svpt"] = pd.to_numeric(df["l_svpt"], errors="coerce")
    df["has_stats"] = df["w_svpt"].notna() & df["l_svpt"].notna() & (df["w_svpt"] > 0)
    return df


def chronological(df: pd.DataFrame) -> pd.DataFrame:
    """Sort matches in true playing order (date, tournament, round, match number)."""
    tid = df["tourney_id"].where(df["tourney_id"].notna(), df["tourney_name"])
    mn = pd.to_numeric(df["match_num"], errors="coerce").fillna(0)
    return df.assign(_tid=tid.astype(str), _mn=mn).sort_values(
        ["date", "_tid", "round_order", "_mn"]
    ).drop(columns=["_tid", "_mn"]).reset_index(drop=True)


def load_matches(tour: str = "atp") -> pd.DataFrame:
    """Top-level entry: merge sources, clean, backfill bios, chronologically sort."""
    df = clean(merge_sources(tour))
    df = _backfill_bios(df)
    df["tour"] = tour
    return chronological(df)


def summary(df: pd.DataFrame) -> dict:
    """Compact integrity summary (used by the pipeline + ad-hoc checks)."""
    return {
        "matches": int(len(df)),
        "date_min": str(df["date"].min().date()),
        "date_max": str(df["date"].max().date()),
        "players": int(pd.concat([df["winner_name"], df["loser_name"]]).nunique()),
        "with_stats": float(df["has_stats"].mean()),
        "completed": float(df["completed"].mean()),
        "surfaces": dict(df["surface_b"].value_counts()),
    }


if __name__ == "__main__":
    import json
    import sys
    tour = sys.argv[1] if len(sys.argv) > 1 else "atp"
    m = load_matches(tour)
    print(f"[{tour}]", json.dumps(summary(m), indent=2, default=str))
