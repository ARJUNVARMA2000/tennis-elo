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
from pathlib import Path

import pandas as pd

from ..config import (
    DEFAULT_TIER_K_MULT,
    ROUND_ORDER,
    SURFACE_MAP,
    TIER_ANCHORS,
    TIER_K_MULT,
    TIER_NAMES,
    fresh_dir,
    historical_dir,
    live_dir,
    stats_dir,
)


def tier_mults(tour: str | None) -> tuple[dict, float]:
    """(tier -> K multiplier, default) for a tour: TIER_K_MULT rescaled linearly
    between the tour's tuned (grand_slam, challenger) anchors, if adopted."""
    anchors = TIER_ANCHORS.get(tour or "")
    if not anchors:
        return TIER_K_MULT, DEFAULT_TIER_K_MULT
    gs, ch = anchors
    lo, hi = min(TIER_K_MULT.values()), max(TIER_K_MULT.values())
    scale = lambda v: ch + (v - lo) / (hi - lo) * (gs - ch)
    return {k: scale(v) for k, v in TIER_K_MULT.items()}, scale(DEFAULT_TIER_K_MULT)

# Surface by calendar month — the tennis season's surface swings — used only as a
# fallback for live (ESPN) rows whose sponsor-named event isn't in the archive.
_MONTH_SURFACE = {1: "Hard", 2: "Hard", 3: "Hard", 4: "Clay", 5: "Clay", 6: "Grass",
                  7: "Grass", 8: "Hard", 9: "Hard", 10: "Hard", 11: "Hard", 12: "Hard"}
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
    """Games-only normalization: drop tiebreak digits, RET/W-O markers and 0-0
    placeholder sets so the same match keys identically across sources that format
    retirements differently ('6-3 3-2 RET' vs '6-3 3-2 0-0 RET')."""
    if not isinstance(score, str):
        return ""
    pairs = re.findall(r"\d+-\d+", re.sub(r"\(\d+\)", "", score))
    return ",".join(p for p in pairs if p != "0-0")


# single shared implementation (kept importable here as results._name_key — the
# established path used by wta_stats, odds joins and the tests)
from .names import name_key as _name_key  # noqa: E402


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
    """Concatenate historical + stats + fresh + live for a tour and de-dup.

    Preference (lower __src wins a duplicate match): historical archive (serve stats +
    clean names, frozen upstreams) > stats overlay (same full schema, updated daily —
    TML site for ATP, scraped for WTA) > fresh mirror (results, clean city names) >
    live ESPN overlay (same-day, but sponsor names / no surface). Rows carrying serve
    stats always beat results-only duplicates regardless of source (see the __hs sort),
    so the stats overlay fills every match the frozen archive is missing.
    """
    hist = _read_dir(historical_dir(tour))
    stats = _read_dir(stats_dir(tour))
    fresh = _read_dir(fresh_dir(tour))
    live = _read_dir(live_dir(tour))
    hist["__src"], stats["__src"], fresh["__src"], live["__src"] = 0, 1, 2, 3
    df = pd.concat([hist, stats, fresh, live], ignore_index=True)
    df["date"] = _parse_dates(df["tourney_date"])
    df = df[df["date"].notna() & df["winner_name"].notna() & df["loser_name"].notna()].copy()
    df = _canonicalize_names(df)

    has_stats = pd.to_numeric(df["w_svpt"], errors="coerce").notna()
    # year is part of the key: rivalries repeat identical scorelines across seasons,
    # and sources agree on year (dates themselves can drift a day between sources)
    df["__key"] = (df["winner_name"].astype(str) + "|" + df["loser_name"].astype(str)
                   + "|" + df["date"].dt.year.astype(str) + "|" + df["score"].map(_score_key))
    # prefer rows that have stats, then the earlier (cleaner) source
    df = df.assign(__hs=has_stats.astype(int)).sort_values(["__hs", "__src"], ascending=[False, True])
    df = df.drop_duplicates(subset="__key", keep="first")
    # second pass: the same ordered pair on the same calendar day in the same round is
    # one match, however the sources disagree on score formatting or event naming — keep
    # the preferred row. Round must be part of the key: archive sources stamp every match
    # with the tournament START date, so a round-robin meeting and a final rematch at the
    # same event share a date (e.g. Federer d. Hewitt twice at the 2004 Masters Cup)
    df = df.drop_duplicates(subset=["winner_name", "loser_name", "date", "round"], keep="first")
    return df.drop(columns=["__hs", "__key", "__src"])


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


def _backfill_event_attrs(df: pd.DataFrame) -> pd.DataFrame:
    """Fill surface / tourney_level / best_of on rows that lack them (ESPN live rows)
    from each tournament's known rows in the archive, matched by name."""
    for col in ("surface", "tourney_level", "best_of"):
        present = df[df[col].notna()]
        if present.empty:
            continue
        modal = present.groupby("tourney_name")[col].agg(
            lambda s: s.mode().iloc[0] if not s.mode().empty else None)
        df[col] = df[col].where(df[col].notna(), df["tourney_name"].map(modal))
    return df


def clean(df: pd.DataFrame, tour: str | None = None) -> pd.DataFrame:
    """Add derived/normalised columns (robust to columns absent in the fresh schema)."""
    df = df.copy()
    if "date" not in df:
        df["date"] = _parse_dates(df["tourney_date"])
    df = df[df["date"].notna() & df["winner_name"].notna() & df["loser_name"].notna()]

    df = _backfill_event_attrs(df)
    # surface: prefer the (now backfilled) value; else fall back to the season's surface
    surf = df["surface"].where(df["surface"].notna(), df["date"].dt.month.map(_MONTH_SURFACE))
    df["surface_b"] = surf.map(SURFACE_MAP).fillna(surf).fillna("Hard")
    df["tier"] = df["tourney_level"].map(_tier_name)
    mults, default_mult = tier_mults(tour)
    df["tier_k"] = df["tier"].map(mults).fillna(default_mult)
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
    df = clean(merge_sources(tour), tour=tour)
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
