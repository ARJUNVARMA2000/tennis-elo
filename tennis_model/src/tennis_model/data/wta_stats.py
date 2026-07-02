"""WTA serve-stats scraper — first-party api.wtatennis.com JSON endpoints.

The WTA historical snapshot died in May 2024 and no free bulk source carries WTA
serve stats since, so we assemble our own full-schema year CSVs:

  tournaments:  GET /tennis/tournaments/?from=Y-01-01&to=Y-12-31&page=..&pageSize=100
  matches:      GET /tennis/tournaments/{id}/{year}/matches?page=..&pageSize=100
  match stats:  GET /tennis/tournaments/{id}/{year}/matches/{matchId}/stats

Output: data/raw/wta/stats/{year}.csv in the canonical (Sackmann-style) schema, which
merge_sources() picks up as the src=1 "stats" overlay. Only rows whose stats fetch
succeeded are emitted — results-only coverage already comes from the fresh overlay,
and emitting stat-less rows here would out-rank the fresh rows that carry rankings.

Decoded API semantics (verified against 2026 Roland Garros + the 2024 snapshot):
  Winner: "2" = player A won, "3" = player B won
  RoundID: numeric from round 1, then "Q"/"S"/"F"; mapped to R128..QF/SF/F by draw size
  ScoreString: A-perspective sets "3-6,7-6(4),6-3"; we re-serialize winner-first
  stats record (setnum=0 = whole match): totservplayed=svpt, ptsplayed1stserv=1stIn,
  ptswon1stserv=1stWon, ptstotwonserv-ptswon1stserv=2ndWon, aces/dblflt,
  bpFaced(server A) = breakptsconvb+breakptsplayedb, bpSaved(A) = breakptsplayedb

Run:  PYTHONPATH=src python -m tennis_model.data.wta_stats --years 2024 2025 2026
      PYTHONPATH=src python -m tennis_model.data.wta_stats --incremental   (daily)
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

import pandas as pd

from ..config import INCLUDE_CHALLENGERS, fresh_dir, stats_dir
from .results import CANON, _name_key, _score_key

BASE = "https://api.wtatennis.com/tennis"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; tennis_model personal analytics)",
           "Accept": "application/json"}
PAUSE_S = 0.25                 # politeness gap between requests
RETRIES = 5                    # long backfills WILL hit transient failures/throttles
INCREMENTAL_DAYS = 21          # re-fetch tournaments ending within this window

# API tournament levels -> the vocabulary TIER_NAMES already maps (spaces stripped).
_SKIP_LEVELS = {"ITF", "", None}
_LEVEL_MAP = {"GrandSlam": "Grand Slam", "BillieJeanKingCup": "DavisCup",
              "FedCup": "DavisCup", "OlympicGames": "Olympics"}


def _get(path: str, params: dict | None = None, retries: int = RETRIES):
    """GET with patient exponential backoff. Returns None only after all retries —
    callers that must not truncate silently should use _get_or_raise."""
    url = f"{BASE}{path}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            time.sleep(PAUSE_S)
            return data
        except urllib.error.HTTPError as e:
            if attempt == retries - 1:
                return None
            # 429: the API wants a real cool-down, not a quick retry
            time.sleep(min(120, 30 * (attempt + 1)) if e.code == 429 else 2 ** attempt)
        except Exception:  # noqa: BLE001 — transient network error: back off and retry, then soft-None
            if attempt == retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None


def _get_or_raise(path: str, params: dict | None = None):
    d = _get(path, params)
    if d is None:
        raise RuntimeError(f"WTA API unreachable after {RETRIES} retries: {path}")
    return d


def _paged(path: str, key: str, params: dict | None = None, page_size: int = 100):
    """Paginate defensively: some endpoints ignore page/pageSize and return the full
    set every time, so a page whose first item repeats the previous page ends the walk
    (otherwise this would loop forever on large tournaments). A mid-walk network
    failure RAISES instead of silently truncating the season."""
    page, out, prev_sig = 0, [], None
    while True:
        d = _get_or_raise(path, {**(params or {}), "page": page, "pageSize": page_size})
        items = d.get(key) or []
        sig = json.dumps(items[:1], sort_keys=True, default=str)
        if not items or sig == prev_sig:
            return out
        out += items
        if len(items) < page_size:
            return out
        prev_sig = sig
        page += 1
        if page >= 50:  # paging-blind endpoint with unstable ordering would loop forever
            raise RuntimeError(f"WTA API pagination runaway on {path} ({len(out)} items)")


def fetch_tournaments(year: int) -> list[dict]:
    """Tour-level (non-ITF) tournaments of a season, with id/surface/level/dates."""
    items = _paged("/tournaments/", "content",
                   {"from": f"{year}-01-01", "to": f"{year}-12-31"})
    out = []
    for t in items:
        level = re.sub(r"\s+", "", str(t.get("level") or ""))
        if str(t.get("level")) in _SKIP_LEVELS or level in ("ITF",):
            continue
        if level == "WTA125" and not INCLUDE_CHALLENGERS:
            continue          # challenger-tier ingestion is a gated experiment (A5)
        out.append({
            "id": t["tournamentGroup"]["id"],
            "name": str(t["tournamentGroup"].get("name") or "").title(),
            "year": t["year"],
            "level": _LEVEL_MAP.get(level, level),
            "surface": t.get("surface"),
            "indoor": t.get("inOutdoor"),                     # "I" / "O"
            "start": t.get("startDate"), "end": t.get("endDate"),
            "draw": t.get("singlesDrawSize") or 0,
        })
    return out


def _round_label(round_id: str, draw: int) -> str | None:
    if round_id in ("F", "S", "Q"):
        return {"F": "F", "S": "SF", "Q": "QF"}[round_id]
    if not str(round_id).isdigit() or not draw or int(round_id) < 1:
        return None                        # RoundID 0 = round-robin/unlabeled
    size = 2 ** (draw - 1).bit_length()                       # next power of two
    size >>= int(round_id) - 1                                # field size at this round
    return f"R{size}" if size >= 16 else {8: "QF", 4: "SF", 2: "F"}.get(size)


def _winner_first_score(m: dict, a_won: bool) -> str:
    """Serialize per-set scores winner-first in canon format ('7-6(4) 6-3')."""
    sets = []
    for i in range(1, 6):
        ga, gb = str(m.get(f"ScoreSet{i}A") or ""), str(m.get(f"ScoreSet{i}B") or "")
        if not ga or not gb:
            break
        tb = str(m.get(f"ScoreTbSet{i}") or "")
        w, l = (ga, gb) if a_won else (gb, ga)
        sets.append(f"{w}-{l}({tb})" if tb else f"{w}-{l}")
    return " ".join(sets)


def _stats_row(ev: dict, m: dict, st: dict) -> dict | None:
    a_won = str(m.get("Winner")) == "2"
    if str(m.get("Winner")) not in ("2", "3"):
        return None
    w, l = ("a", "b") if a_won else ("b", "a")

    def n(field, side):
        v = st.get(f"{field}{side}")
        return None if v is None else float(v)

    row: dict = {c: None for c in CANON}
    for side, who in ((w, "w"), (l, "l")):
        svpt, first_in, first_won = n("totservplayed", side), n("ptsplayed1stserv", side), n("ptswon1stserv", side)
        tot_won = n("ptstotwonserv", side)
        if not svpt or svpt <= 0 or first_in is None or first_won is None or tot_won is None:
            return None
        opp = "b" if side == "a" else "a"
        if not (first_in <= svpt and first_won <= first_in and (tot_won - first_won) <= svpt - first_in):
            return None                                        # inconsistent -> drop stats row
        row[f"{who}_svpt"] = svpt
        row[f"{who}_1stIn"] = first_in
        row[f"{who}_1stWon"] = first_won
        row[f"{who}_2ndWon"] = tot_won - first_won
        row[f"{who}_ace"] = n("aces", side)
        row[f"{who}_df"] = n("dblflt", side)
        row[f"{who}_SvGms"] = n("servgamesplayed", side) or None
        bp_conv_opp, bp_open_opp = n("breakptsconv", opp), n("breakptsplayed", opp)
        if bp_conv_opp is not None and bp_open_opp is not None:
            row[f"{who}_bpFaced"] = bp_conv_opp + bp_open_opp
            row[f"{who}_bpSaved"] = bp_open_opp

    wf, wl = m.get(f"PlayerNameFirst{w.upper()}"), m.get(f"PlayerNameLast{w.upper()}")
    lf, ll = m.get(f"PlayerNameFirst{l.upper()}"), m.get(f"PlayerNameLast{l.upper()}")
    if not (wf and wl and lf and ll):
        return None
    # real match date (falls back to the tournament start date) — keeps the same-day
    # dedup pass and the rest/fatigue features honest
    ts = str(m.get("MatchTimeStamp") or "")[:10]
    date = ts if re.fullmatch(r"\d{4}-\d{2}-\d{2}", ts) else str(ev["start"])
    row.update({
        "tourney_id": f"{ev['year']}-W{ev['id']}",
        "tourney_name": ev["name"], "surface": ev["surface"], "indoor": ev["indoor"],
        "tourney_level": ev["level"], "draw_size": ev["draw"] or None,
        "tourney_date": date.replace("-", ""),
        "match_num": None, "best_of": 3,
        "round": _round_label(str(m.get("RoundID")), int(ev["draw"] or 0)),
        "score": _winner_first_score(m, a_won),
        "winner_name": f"{wf} {wl}", "loser_name": f"{lf} {ll}",
        "winner_ioc": m.get(f"PlayerCountry{w.upper()}"), "loser_ioc": m.get(f"PlayerCountry{l.upper()}"),
        "winner_id": m.get(f"PlayerID{w.upper()}"), "loser_id": m.get(f"PlayerID{l.upper()}"),
        "winner_entry": m.get(f"EntryType{w.upper()}") or None,
        "loser_entry": m.get(f"EntryType{l.upper()}") or None,
        "winner_seed": m.get(f"Seed{w.upper()}") or None, "loser_seed": m.get(f"Seed{l.upper()}") or None,
    })
    return row


def scrape_tournament(ev: dict) -> list[dict]:
    matches = _paged(f"/tournaments/{ev['id']}/{ev['year']}/matches", "matches")
    rows = []
    for m in matches:
        if m.get("DrawMatchType") != "S" or m.get("DrawLevelType") != "M":
            continue                                           # singles main draw only
        if m.get("MatchState") != "F":
            continue
        st = _get(f"/tournaments/{ev['id']}/{ev['year']}/matches/{m['MatchID']}/stats")
        st0 = next((s for s in st or [] if s.get("setnum") == 0), None)
        if not st0:
            continue
        row = _stats_row(ev, m, st0)
        if row:
            rows.append(row)
    return rows


def _enrich_from_fresh(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Inherit rankings (and RET-marked scores) from the fresh overlay's duplicate of
    the same match — scraped rows out-rank fresh rows in the merge, so anything the
    fresh row alone carries would otherwise be lost."""
    f = fresh_dir("wta") / f"{year}.csv"
    if not f.exists() or df.empty:
        return df
    fresh = pd.read_csv(f, low_memory=False, encoding="utf-8-sig")
    fresh["__k"] = fresh["winner_name"].map(_name_key) + "|" + fresh["loser_name"].map(_name_key)
    fresh = fresh.drop_duplicates("__k", keep="last")          # latest meeting wins
    df["__k"] = df["winner_name"].map(_name_key) + "|" + df["loser_name"].map(_name_key)
    idx = fresh.set_index("__k")
    for col in ("winner_rank", "loser_rank", "winner_rank_points", "loser_rank_points"):
        if col in fresh.columns:
            df[col] = df[col].where(df[col].notna(), df["__k"].map(idx[col]))
    # keep the fresh RET/W-O marker so parse_score flags retirements correctly —
    # but only when the games agree (the pair may have met twice in the year, and a
    # rematch's marker must not overwrite this meeting's score)
    fresh_score = df["__k"].map(idx["score"]) if "score" in fresh.columns else None
    if fresh_score is not None:
        ret = fresh_score.astype(str).str.contains("RET|W/O|DEF|ABN|ABD", case=False, na=False)
        same = [
            bool(r) and (_score_key(fs).startswith(_score_key(ms))
                         or _score_key(ms).startswith(_score_key(fs)))
            for r, fs, ms in zip(ret, fresh_score.astype(str), df["score"].astype(str))
        ]
        df.loc[same, "score"] = fresh_score[same]
    return df.drop(columns="__k")


def scrape_year(year: int, since: datetime | None = None) -> pd.DataFrame:
    events = fetch_tournaments(year)
    if since is not None:
        events = [e for e in events
                  if e["end"] and pd.Timestamp(e["end"]) >= pd.Timestamp(since.date())]
    print(f"    wta/stats {year}: {len(events)} tour-level events")
    rows: list[dict] = []
    empty: list[str] = []
    for ev in events:
        got = scrape_tournament(ev)
        rows += got
        if not got:
            empty.append(ev["name"])
        if got:
            print(f"    wta/stats {year} {ev['name']}: {len(got)} matches")
    if empty:
        print(f"    wta/stats {year}: 0 stat rows for {len(empty)} event(s): "
              f"{', '.join(empty[:8])}{'...' if len(empty) > 8 else ''}")
    # plain construction: rows carry CANON keys plus extras (entry/seed) that the
    # loader's reindex-with-extras keeps for the combiner's qualifier feature
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=CANON)


def write_year(year: int, df_new: pd.DataFrame) -> int:
    """Merge newly scraped rows into the year file (existing rows kept, refreshed
    tournaments replaced) and return the row count."""
    d = stats_dir("wta")
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{year}.csv"
    if path.exists() and not df_new.empty:
        old = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
        keep = old[~old["tourney_id"].isin(set(df_new["tourney_id"]))]
        if not INCLUDE_CHALLENGERS and "tourney_level" in keep.columns:
            keep = keep[keep["tourney_level"] != "WTA125"]
        df_new = pd.concat([keep, df_new], ignore_index=True)
    elif path.exists():
        return len(pd.read_csv(path, low_memory=False, encoding="utf-8-sig"))
    df_new = _enrich_from_fresh(df_new, year)
    tmp = path.with_suffix(".csv.tmp")   # atomic: a crash mid-write must not corrupt the year file
    df_new.to_csv(tmp, index=False)
    os.replace(tmp, path)
    return len(df_new)


def download_wta_stats(years=None, incremental: bool = False) -> None:
    now = datetime.now(UTC)
    if years is None:
        years = [now.year]
    since = now - timedelta(days=INCREMENTAL_DAYS) if incremental else None
    for y in years:
        n = write_year(y, scrape_year(y, since=since))
        print(f"  wta/stats: {y}.csv now {n} rows")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*", default=None)
    ap.add_argument("--incremental", action="store_true",
                    help="only re-fetch tournaments ending in the last ~3 weeks")
    args = ap.parse_args()
    download_wta_stats(args.years, incremental=args.incremental)
