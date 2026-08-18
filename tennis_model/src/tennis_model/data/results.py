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
    MAX_FUTURE_MATCH_DAYS,
    MONTH_SURFACE,
    PLAYER_ALIASES,
    ROUND_ORDER,
    SURFACE_MAP,
    TIER_ANCHORS,
    TIER_K_MULT,
    TIER_NAMES,
    fresh_dir,
    historical_dir,
    live_dir,
    lower_dir,
    stats_dir,
)
from .surface import wiki_categories_by_event_id, wiki_surface_lookup


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

from .scores import parse_score

# Canonical column set every loaded frame is reindexed to, so downstream code never
# hits a missing column regardless of which source (full vs results-only) it came from.
_STAT_COLS = [f"{s}_{c}" for s in ("w", "l")
              for c in ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")]
CANON = [
    # `espn_id` is present only on live-overlay rows (the archive predates it and always
    # will), so it is a HINT, never a key: it is deliberately absent from both dedup subsets
    # below, and consumers take the modal non-null value per event rather than expecting it
    # on every row. Adding it here just means no reader hits a missing column.
    "tourney_id", "espn_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor",
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


def _read_lower(tour: str) -> pd.DataFrame:
    """Challenger + tour-qualifying overlay (A5 experiment, INCLUDE_CHALLENGERS).

    Challenger files keep their 'C' level; qualifying rows are stamped level 'Q'
    (challenger-tier K via TIER_NAMES — a slam Q1 between challenger-strength
    players must not update at slam K). `draw_level` marks every row so the
    arbiter and exports can separate them from the main-draw eval set.
    """
    frames = []
    for f in sorted(glob.glob(str(lower_dir(tour) / "*.csv"))):
        df = pd.read_csv(f, encoding="utf-8-sig", low_memory=False)
        df = df.reindex(columns=[c for c in set(CANON) | set(df.columns)])
        if f.endswith("_atp_quali.csv"):
            df["draw_level"] = "qual"
            df["tourney_level"] = "Q"
        elif f.endswith("_wta_lower.csv"):
            # The first-party WTA file intentionally mixes WTA 125 main draws and
            # tour/125 qualifying.  Its content-level stamp is authoritative; never
            # flatten the latter into ``chall`` merely because they share a file.
            stamped = df.get("draw_level", pd.Series(pd.NA, index=df.index))
            df["draw_level"] = stamped.where(stamped.isin(("chall", "qual")), "chall")
            df.loc[df["draw_level"].eq("qual"), "tourney_level"] = "Q"
        else:
            df["draw_level"] = "chall"
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=[*CANON, "draw_level"])
    out = pd.concat(frames, ignore_index=True)
    return out.reindex(columns=sorted(set(out.columns), key=str))


def _parse_dates(s: pd.Series) -> pd.Series:
    """Handle both YYYYMMDD (historical) and YYYY/M/D (fresh overlay)."""
    s = s.astype("string").str.strip()
    d = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    miss = d.isna() & s.notna()
    if miss.any():
        # format="mixed" infers per element (same result as no format) but WITHOUT the
        # "Could not infer format" UserWarning that otherwise prints on every pipeline run.
        d.loc[miss] = pd.to_datetime(s[miss].str.replace("/", "-", regex=False),
                                     format="mixed", errors="coerce")
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
    # Aliases first. The per-key pass below can only merge spellings that SHARE a key, so a
    # variant differing by a dropped/added surname ('Daniel Merida Aguilar' vs the archive's
    # 'Daniel Merida') survives it as a second person. Resolving those up front also means
    # the frequency/source preference below is computed on already-merged counts.
    for who in ("winner_name", "loser_name"):
        df[who] = df[who].map(lambda x: PLAYER_ALIASES.get(_name_key(x), x))
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


def _reconcile_exact_live_result(df: pd.DataFrame) -> pd.DataFrame:
    """Carry ESPN event identity and round across an exact result disagreement.

    A round is normally part of match identity because the same opponents can meet
    twice at one event.  It cannot be trusted as the *only* separator across providers,
    though: a bye-heavy draw can make one provider call the same match R64 and another
    R32.  The safe bridge is deliberately narrow: same ordered players, local calendar
    date and games-only score; exactly one row per source; and exactly one live ESPN row
    carrying the stable event id.  More than one row from any source makes the bucket
    ambiguous (for example a round-robin/final rematch), so it is left untouched.

    The live round is safe to apply only at this seam because ``live._draw_size`` has
    already resolved it from every populated stage.  ``fixtures.json`` carries the same
    ``espn_id`` afterward, and the output gate independently checks its round against the
    authoritative shipped bracket.  Thus an exact conflict heals automatically when all
    three agree and still blocks before deploy if the live inference is ever wrong again.
    """
    if df.empty or not {"__src", "espn_id", "date"}.issubset(df.columns):
        return df
    score_key = df["score"].map(_score_key)
    usable = score_key.ne("")
    evidence = (df["winner_name"].astype(str) + "|" + df["loser_name"].astype(str)
                + "|" + df["date"].astype(str) + "|" + score_key)
    out = df.copy()
    for _, group in out.loc[usable].groupby(evidence.loc[usable], sort=False):
        if len(group) < 2 or group["__src"].nunique() != len(group):
            continue
        live_rows = group[(group["__src"] == 3) & group["espn_id"].notna()]
        ids = group["espn_id"].dropna().astype(str).str.strip()
        if len(live_rows) != 1 or ids.nunique() != 1 or not ids.iloc[0]:
            continue
        out.loc[group.index, "espn_id"] = ids.iloc[0]
        raw_round = live_rows.iloc[0].get("round")
        live_round = raw_round.strip().upper() if isinstance(raw_round, str) else ""
        if live_round:
            out.loc[group.index, "round"] = live_round
    return out


def _stamp_draw_level(df: pd.DataFrame) -> pd.DataFrame:
    """Mark every row main / chall / qual, deriving from CONTENT before provenance.

    `_read_lower` stamps the rows it reads out of `lower_dir`, which used to be the only
    labelling — so lower-tier rows arriving through any OTHER directory silently inherited
    "main". They do: the ATP serve-stats source ships `<year>_challenger.csv` into
    `stats_dir`, and because the stats overlay outranks the lower overlay in the dedup
    preference, its unlabelled copy WON. 42k of the 72k ATP rows the combiner treated as
    main draw for 2016-26 were Challengers — the exact challenger-dominated mix the A5
    experiment measured as a REJECT, reintroduced through a back door (2026-07-25).

    `tourney_level` says what a match is regardless of which file carried it, so trust that
    first and fall back to "main". Ratings are unaffected either way (the walks see every
    row, and tier K already keys off `tourney_level`); this only decides what the combiner
    trains and is scored on.
    """
    lvl = (df["tourney_level"].astype("string").str.strip()
           if "tourney_level" in df.columns else pd.Series(pd.NA, index=df.index, dtype="string"))
    stamped = (df["draw_level"] if "draw_level" in df.columns
               else pd.Series(pd.NA, index=df.index, dtype=object))
    derived = pd.Series(pd.NA, index=df.index, dtype=object)
    derived[lvl.isin(("C", "WTA125"))] = "chall"
    derived[lvl.eq("Q")] = "qual"
    df["draw_level"] = stamped.combine_first(derived).fillna("main")
    return df


_WTA_MODEL_LEVEL = {
    "Grand Slam": "GrandSlam",
    "Tour Finals": "WTAFinals",
    "Olympics": "Olympics",
    "Davis/BJK Cup": "DavisCup",
    "United Cup": "UnitedCup",
    "WTA 1000": "WTA1000",
    "WTA 500": "WTA500",
    "WTA 250": "WTA250",
    "WTA 125": "WTA125",
    "WTA Tour": "A",
}

# Private dataframe-attrs sidecar: exact post-dedup rows withheld from model state but
# retained as factual event evidence. A list of records (rather than a nested DataFrame)
# keeps attrs equality/copy semantics predictable across pandas operations.
_POLICY_EVENT_ROWS_ATTR = "_policy_excluded_event_rows"


def _stamp_live_result_policy(tour: str, live: pd.DataFrame) -> pd.DataFrame:
    """Classify WTA live rows by ``espnId`` and mark policy-excluded results.

    ESPN's WTA scoreboard mixes tour events and WTA 125s. The latter are intentionally
    excluded by ``INCLUDE_WTA_125`` because no lower-tier source covers the tune window,
    but the live overlay used to bypass that decision. Its rolling 14-day file therefore
    added 125 results temporarily and removed them in batches when an event aged out.

    Rows stay in this frame as identity hints until de-duplication: a stable-source copy of
    the same match must inherit its ESPN id even when the live result itself is not eligible
    for the model. Unique excluded rows are dropped only after both dedup passes. Unknown
    tiers are withheld under the same conservative policy; uncertainty cannot silently opt
    a lower-tier population into a model whose config opted it out.
    """
    live = live.copy()
    live["__policy_excluded"] = False
    live.attrs["excluded_wta125_matches"] = 0
    live.attrs["excluded_unclassified_wta_live_matches"] = 0
    live.attrs["excluded_wta125_event_ids"] = ()
    live.attrs["excluded_unclassified_wta_event_ids"] = ()
    if tour != "wta" or live.empty:
        return live

    levels_by_id = wiki_categories_by_event_id(tour)
    event_ids = live["espn_id"].astype("string").str.strip()
    levels = event_ids.map(levels_by_id)
    model_levels = levels.map(_WTA_MODEL_LEVEL)
    live["tourney_level"] = model_levels.where(model_levels.notna(), live["tourney_level"])

    from .. import config as _cfg
    if _cfg.INCLUDE_WTA_125:
        return live

    is_125 = levels.eq("WTA 125")
    unclassified = levels.isna()
    live["__policy_excluded"] = is_125 | unclassified
    live.attrs["excluded_wta125_event_ids"] = tuple(sorted(set(event_ids[is_125].dropna())))
    live.attrs["excluded_unclassified_wta_event_ids"] = tuple(
        sorted(set(event_ids[unclassified].dropna())))
    if is_125.any() or unclassified.any():
        print(f"  results/wta: withheld {int(is_125.sum())} WTA 125 and "
              f"{int(unclassified.sum())} unclassified live row(s) from model ingestion")
    return live


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
    live = _stamp_live_result_policy(tour, _read_dir(live_dir(tour)))
    excluded_125_ids = set(live.attrs.get("excluded_wta125_event_ids", ()))
    excluded_unknown_ids = set(live.attrs.get("excluded_unclassified_wta_event_ids", ()))
    live_levels_by_id = {}
    if tour == "wta":
        live_levels_by_id = (
            live.dropna(subset=["espn_id", "tourney_level"])
            .drop_duplicates("espn_id", keep="last")
            .set_index("espn_id")["tourney_level"].to_dict()
        )
    hist["__src"], stats["__src"], fresh["__src"], live["__src"] = 0, 1, 2, 3
    frames = [hist, stats, fresh, live]
    from .. import config as _cfg
    include_lower = ((_cfg.INCLUDE_CHALLENGERS and tour == "atp")
                     or (_cfg.INCLUDE_WTA_LOWER_STATE and tour == "wta"))
    # Always read lower files as population CLASSIFICATION evidence.  A higher-priority
    # archive copy of the same match may be stamped as main; if the lower copy is omitted
    # entirely when the state flag is off, that mislabeled survivor leaks into the baseline
    # combiner/eval set.  Unique lower rows are filtered after dedup unless include_lower is
    # enabled, so evidence does not imply state admission.
    low = _read_lower(tour)
    if len(low):
        low["__src"] = 4
        frames.append(low)
    df = pd.concat(frames, ignore_index=True)
    df = _stamp_draw_level(df)
    df["date"] = _parse_dates(df["tourney_date"])
    df = df[df["date"].notna() & df["winner_name"].notna() & df["loser_name"].notna()].copy()
    df = _repair_corrupt_final_years(df)
    df = _drop_impossible_dates(df)
    df = _canonicalize_names(df)
    df = _reconcile_exact_live_result(df)

    def _fill_espn_id(frame: pd.DataFrame, k: pd.Series) -> pd.DataFrame:
        """Carry `espn_id` onto every row of a match BEFORE a dedup picks its survivor.

        The id rides on ESPN live rows only — and those are exactly the rows dedup drops,
        having no serve stats and the latest source rank. But the id describes the EVENT, not
        whichever row happened to win, so losing it there costs the tournament its identity.
        On 2026-07-28 that shipped the WTA board a 12-player "Washington Dc" fragment beside
        the full 28-draw "Mubadala DC Open" — one tournament, two cards, two different
        favourites — because the surviving archive rows had no id left to resolve.
        """
        if "espn_id" not in frame.columns or not frame["espn_id"].notna().any():
            return frame
        src = frame.loc[frame["espn_id"].notna()]
        m = dict(zip(k.loc[src.index], src["espn_id"]))
        frame["espn_id"] = frame["espn_id"].where(frame["espn_id"].notna(), k.map(m))
        return frame

    has_stats = pd.to_numeric(df["w_svpt"], errors="coerce").notna()
    # Year and round are part of the key: rivalries repeat identical scorelines across
    # seasons, and even within one season. Sources agree on both while dates themselves can
    # drift from an event start stamp to the match's actual day. Without round, Fritz's
    # 2026 Delray R16 win over Jodar (7-6 6-4) erased their Washington final with the exact
    # same score, then inherited Washington's ESPN id before the live row disappeared.
    base_key = (df["winner_name"].astype(str) + "|" + df["loser_name"].astype(str)
                + "|" + df["date"].dt.year.astype(str) + "|" + df["score"].map(_score_key))
    round_key = df["round"].astype("string").fillna("").str.strip().str.upper()

    def _only_round(values: pd.Series) -> str:
        known = values[values.ne("")].unique()
        return str(known[0]) if len(known) == 1 else ""

    # Some overlays omit `round` while another copy of the SAME match supplies it. Treat an
    # empty value as a wildcard only when its exact-date bucket (preferred), or its entire
    # old-key bucket, has one unambiguous known round. Otherwise keep it separate: guessing
    # which of two real rematches it belongs to would silently delete evidence again.
    by_day = round_key.groupby(base_key + "|" + df["date"].astype(str)).transform(_only_round)
    round_key = round_key.mask(round_key.eq("") & by_day.ne(""), by_day)
    by_group = round_key.groupby(base_key).transform(_only_round)
    round_key = round_key.mask(round_key.eq("") & by_group.ne(""), by_group)
    df["__key"] = base_key + "|" + round_key
    # Content-level lower provenance must survive source-preference deduplication.  The
    # lower overlay loses to the historical/stats copy by design, but its role/tier is a
    # fact about the match population rather than a source-quality field.
    role_rank = df["draw_level"].map({"main": 0, "chall": 1, "qual": 2}).fillna(0)
    group_role = role_rank.groupby(df["__key"]).transform("max").map(
        {0: "main", 1: "chall", 2: "qual"})
    lower_tier = df["tourney_level"].where(df["draw_level"].ne("main"))
    lower_tier = lower_tier.groupby(df["__key"]).transform("first")
    df["draw_level"] = group_role
    df["tourney_level"] = df["tourney_level"].where(group_role.eq("main"), lower_tier)
    # prefer rows that have stats, then the earlier (cleaner) source
    df = _fill_espn_id(df, df["__key"])
    df = df.assign(__hs=has_stats.astype(int)).sort_values(["__hs", "__src"], ascending=[False, True])
    df = df.drop_duplicates(subset="__key", keep="first")
    # second pass: the same ordered pair on the same calendar day in the same round is
    # one match, however the sources disagree on score formatting or event naming — keep
    # the preferred row. Round must be part of the key: archive sources stamp every match
    # with the tournament START date, so a round-robin meeting and a final rematch at the
    # same event share a date (e.g. Federer d. Hewitt twice at the 2004 Masters Cup)
    df = _fill_espn_id(df, df["winner_name"].astype(str) + "|" + df["loser_name"].astype(str)
                       + "|" + df["date"].astype(str) + "|" + df["round"].astype(str))
    df = df.drop_duplicates(subset=["winner_name", "loser_name", "date", "round"], keep="first")
    event_ids = df["espn_id"].astype("string").str.strip()
    # An earlier-source duplicate can win de-duplication after inheriting only the live
    # ESPN id. Carry the id-derived tier as well so the event-facing partition retains
    # the authoritative WTA category even when the preferred archive row did not have it.
    live_levels = event_ids.map(live_levels_by_id)
    df["tourney_level"] = live_levels.where(live_levels.notna(), df["tourney_level"])
    excluded_125 = event_ids.isin(excluded_125_ids)
    excluded_unknown = event_ids.isin(excluded_unknown_ids)
    excluded = excluded_125 | excluded_unknown
    if "__policy_excluded" in df:
        excluded |= df["__policy_excluded"].fillna(False).astype(bool)
    policy_audit = {
        # Counts are taken after de-duplication, so they equal the actual model-population
        # cleanup (including an earlier-source duplicate that inherited the live row's id).
        "excluded_wta125_matches": int(excluded_125.sum()),
        "excluded_unclassified_wta_live_matches": int(excluded_unknown.sum()),
        # The rating population and the tournament board answer different questions.
        # Keep the exact complementary partition so the exporter can still observe starts,
        # eliminations and finals without ever walking these rows through model state.
        _POLICY_EVENT_ROWS_ATTR: df.loc[excluded].drop(
            columns=["__hs", "__key", "__src", "__policy_excluded"],
            errors="ignore").to_dict("records"),
    }
    df = df.loc[~excluded].drop(
        columns=["__hs", "__key", "__src", "__policy_excluded"], errors="ignore")
    if not include_lower:
        df = df[df["draw_level"].eq("main")]
    df.attrs.update(policy_audit)
    return df


def _backfill_bios(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing hand/height/country on (fresh) rows from each player's known values."""
    hand, ht, ioc = {}, {}, {}
    for who in ("winner", "loser"):
        for nm, h, t, io in zip(df[f"{who}_name"], df[f"{who}_hand"],
                                df[f"{who}_ht"], df[f"{who}_ioc"]):
            if isinstance(h, str) and nm not in hand:
                hand[nm] = h
            if pd.notna(t) and nm not in ht:
                ht[nm] = t
            if isinstance(io, str) and nm not in ioc:
                ioc[nm] = io
    for who in ("winner", "loser"):
        df[f"{who}_hand"] = df[f"{who}_hand"].where(df[f"{who}_hand"].notna(),
                                                    df[f"{who}_name"].map(hand))
        df[f"{who}_ht"] = df[f"{who}_ht"].where(df[f"{who}_ht"].notna(),
                                                df[f"{who}_name"].map(ht))
        df[f"{who}_ioc"] = df[f"{who}_ioc"].where(df[f"{who}_ioc"].notna(),
                                                  df[f"{who}_name"].map(ioc))
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


def _drop_impossible_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows dated implausibly far in the future — a match cannot be played then.

    A single mistyped year in an upstream row is enough to corrupt every date-relative
    quantity downstream, because most of them are anchored on the dataset's MAX date
    rather than on today: `elo.last_date`, the ACTIVE_DAYS active-player window, form
    windows, age advancement. On 2026-07-25 the WTA fresh overlay carried the Iasi final
    as `2029/7/20`; last_date jumped three years, the 550-day active window then held
    only the two players in that one row, and the WTA export shipped 2 players instead of
    200 (crashing build_draws on the resulting 2-slot bracket). One bad cell, whole tour.

    Deliberately a wide horizon, not `> today`: the live overlay legitimately carries
    scheduled matches up to 12 days out (live.fetch_events days_fwd), so a strict cutoff
    would silently drop real fixtures. MAX_FUTURE_MATCH_DAYS clears those by 5x while
    still catching the realistic corruption, which is a year typo (>=365 days off).

    Never silent: the drop is printed, because a source that starts emitting bad dates is
    a source to go and look at, and health.py's future-date check reports the same class
    from the other side (it sees the shipped max date, so it also covers any path that
    bypasses this filter).
    """
    if "date" not in df.columns or not len(df):
        return df
    horizon = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize() \
        + pd.Timedelta(days=MAX_FUTURE_MATCH_DAYS)
    bad = df["date"] > horizon
    n = int(bad.sum())
    if n:
        worst = df.loc[bad, "date"].max().date()
        print(f"  results: dropped {n} row(s) dated beyond {horizon.date()} "
              f"(latest {worst}) — upstream date corruption")
    return df[~bad]


def _repair_corrupt_final_years(df: pd.DataFrame) -> pd.DataFrame:
    """Repair a far-future final's YEAR only when the bracket topology proves it.

    The fresh WTA feed carried Iasi's final as 2029/7/20. Dropping it protects model state,
    but permanently loses a factual champion once ESPN's rolling result window expires.
    A narrow repair is possible without trusting an event-name join: inside the SAME raw
    source and its exact source-native event group, the final's two players must be exactly
    the two unique semifinal winners in one and only one prior season, and keeping the
    original month/day in that season must place the final 1-7 days after those semifinals.

    Anything less certain remains untouched and is dropped by ``_drop_impossible_dates``.
    """
    required = {"date", "round", "tourney_name", "winner_name", "loser_name", "__src"}
    if df.empty or not required.issubset(df.columns):
        return df
    horizon = (pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
               + pd.Timedelta(days=MAX_FUTURE_MATCH_DAYS))
    candidates = df.index[(df["date"] > horizon) & df["round"].astype(str).str.upper().eq("F")]
    if candidates.empty:
        return df

    out = df.copy()
    repaired = 0
    for idx in candidates:
        row = out.loc[idx]
        peers = out[
            out["__src"].eq(row["__src"])
            & out["tourney_name"].eq(row["tourney_name"])
            & out["date"].notna()
            & out["date"].le(horizon)
        ]
        semis = peers[peers["round"].astype(str).str.upper().eq("SF")]
        final_players = {_name_key(row["winner_name"]), _name_key(row["loser_name"])} - {""}
        if len(final_players) != 2:
            continue
        possible: list[pd.Timestamp] = []
        for season in sorted(set(semis["date"].dt.year.astype(int))):
            try:
                corrected = pd.Timestamp(row["date"]).replace(year=season)
            except ValueError:  # e.g. a leap-day typo into a non-leap inferred season
                continue
            edition_semis = semis[
                semis["date"].lt(corrected)
                & semis["date"].ge(corrected - pd.Timedelta(days=7))
            ]
            winners = {_name_key(name) for name in edition_semis["winner_name"]} - {""}
            if winners == final_players and corrected <= horizon:
                possible.append(corrected)
        if len(possible) != 1:
            continue
        corrected = possible[0]
        out.at[idx, "date"] = corrected
        out.at[idx, "tourney_date"] = str(corrected.date())
        repaired += 1
    if repaired:
        print(f"  results: repaired {repaired} far-future final year(s) from "
              "source-native semifinal topology")
    return out


def clean(df: pd.DataFrame, tour: str | None = None) -> pd.DataFrame:
    """Add derived/normalised columns (robust to columns absent in the fresh schema)."""
    df = df.copy()
    if "date" not in df:
        df["date"] = _parse_dates(df["tourney_date"])
    df = df[df["date"].notna() & df["winner_name"].notna() & df["loser_name"].notna()]
    df = _drop_impossible_dates(df)

    df = _backfill_event_attrs(df)
    # surface: archive-backfilled value -> Wikipedia main-article surface (live/new events whose
    # sponsor name misses the archive) -> season-by-month fallback.
    # `surface_src` records WHICH tier answered. Consumers re-derive an event's surface from
    # these rows and feed it back as the authoritative "archive" value; without provenance a
    # month GUESS gets recycled as though it were a fact, which is self-fulfilling — it is
    # why the DC Open stayed on Grass while its Wikipedia infobox said Hard.
    surf = df["surface"]
    src = pd.Series(None, index=df.index, dtype=object)
    src[surf.notna()] = "archive"
    if tour and surf.isna().any():
        names = df.loc[surf.isna(), "tourney_name"].astype(str).unique()
        wiki = df["tourney_name"].astype(str).map(wiki_surface_lookup(tour, names))
        filled = surf.isna() & wiki.notna()
        surf = surf.where(surf.notna(), wiki)
        src[filled] = "wiki"
    guessed = surf.isna()
    surf = surf.where(surf.notna(), df["date"].dt.month.map(MONTH_SURFACE))
    src[guessed] = "month"
    df["surface_src"] = src
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


# Seasons with a documented, permanent shortfall. Excluded from the thinness check so a
# real hole is never lost in the noise of a known one.
_SHORT_SEASONS = {2020}          # COVID: both tours suspended ~March-August
_THIN_SEASON_FRAC = 0.6          # a completed season under 60% of the recent median
_THIN_LOOKBACK = 12              # completed seasons considered


def thin_seasons(df: pd.DataFrame) -> list[int]:
    """Completed seasons carrying far fewer matches than their neighbours.

    This is the signature of a source that is present but INCOMPLETE, which nothing else
    catches: the row count is the only thing that moves, every metric computed on it stays
    perfectly plausible, and the health gate only ever sees the shipped JSON. It has now
    cost two rounds of wrong numbers (2026-07-25) — challenger rows doubling the ATP
    combiner's population, and a local checkout missing the WTA serve-stats backfill that
    lives only in the `data-archive` release asset, which `download` cannot fetch. Both
    times the tell was `n`, spotted by hand against an older reference.

    Deliberately a warning, not an error: a genuinely thin season is sometimes the truth
    (an upstream that really is truncated), and refusing to load would take the site down
    over a data-quality issue the operator may already know about.
    """
    if "date" not in df.columns or df.empty:
        return []
    years = df["date"].dt.year
    current = int(years.max())                    # partial by definition — never judged
    counts = years[years < current].value_counts()
    considered = sorted(counts.index)[-_THIN_LOOKBACK:]
    ref = [int(counts[y]) for y in considered if y not in _SHORT_SEASONS]
    if len(ref) < 3:                              # too little history to have an opinion
        return []
    median = sorted(ref)[len(ref) // 2]
    return [int(y) for y in considered
            if y not in _SHORT_SEASONS and counts[y] < _THIN_SEASON_FRAC * median]


def load_matches(tour: str = "atp") -> pd.DataFrame:
    """Top-level entry: merge sources, clean, backfill bios, chronologically sort."""
    merged = merge_sources(tour)
    policy_audit = dict(merged.attrs)
    df = clean(merged, tour=tour)
    df = _backfill_bios(df)
    df["tour"] = tour
    df = chronological(df)
    df.attrs.update(policy_audit)
    thin = thin_seasons(df)
    if thin:
        counts = df["date"].dt.year.value_counts()
        detail = ", ".join(f"{y}: {int(counts[y])}" for y in thin)
        print(f"  WARNING/{tour}: season(s) look incomplete ({detail}) — a source is likely "
              f"missing. If this is a local checkout, bootstrap the release snapshot first "
              f"(see tennis_model/README.md Usage); `download` alone does not fetch it. "
              f"Metrics measured now are on LESS data than production has.")
    return df


def event_match_view(model_df: pd.DataFrame, tour: str) -> pd.DataFrame:
    """Return results used for tournament lifecycle, including policy-excluded live rows.

    ``model_df`` remains the adopted rating/training population. ESPN WTA 125 and
    unclassified rows withheld from that population still carry factual event state: play
    began, who was eliminated, and who won the final. ``merge_sources`` stores its exact
    post-dedup excluded partition in attrs; this function cleans and appends only that small
    sidecar for the two event consumers (coverage and tournament cards).
    """
    records = model_df.attrs.get(_POLICY_EVENT_ROWS_ATTR, ())
    if not records:
        return model_df

    event_only = clean(pd.DataFrame.from_records(records), tour=tour)
    event_only["tour"] = tour
    event_only = chronological(event_only)

    # Do not propagate the private row payload into the derived view. Preserve only the
    # scalar audit attrs; build_meta continues to receive model_df, never this frame.
    attrs = {key: value for key, value in model_df.attrs.items()
             if key != _POLICY_EVENT_ROWS_ATTR}
    eligible = model_df.copy(deep=False)
    eligible.attrs = {}
    event_only.attrs = {}
    combined = chronological(pd.concat([eligible, event_only], ignore_index=True))
    combined.attrs.update(attrs)
    return combined


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
