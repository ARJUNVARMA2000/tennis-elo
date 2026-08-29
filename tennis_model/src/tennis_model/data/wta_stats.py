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

Run:  PYTHONPATH=src python -m tennis_model.data.wta_stats --year 2025
      PYTHONPATH=src python -m tennis_model.data.wta_stats --year 2025 --scope lower
      PYTHONPATH=src python -m tennis_model.data.wta_stats --incremental   (daily main draw)
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

from ..config import fresh_dir, historical_dir, lower_dir, stats_dir
from .httpcache import ResponseCache
from .results import CANON, _name_key, _score_key

BASE = "https://api.wtatennis.com/tennis"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; tennis_model personal analytics)",
           "Accept": "application/json", "account": "wta"}
PAUSE_S = 0.25                 # politeness gap between requests
RETRIES = 5                    # long backfills WILL hit transient failures/throttles
INCREMENTAL_DAYS = 21          # re-fetch tournaments ending within this window

# API tournament levels -> the vocabulary TIER_NAMES already maps (spaces stripped).
_SKIP_LEVELS = {"ITF", "", None}
_LEVEL_MAP = {
    "GrandSlam": "Grand Slam", "BillieJeanKingCup": "DavisCup",
    "FedCup": "DavisCup", "OlympicGames": "Olympics",
    # Legacy WTA vocabulary used before the 2021 tier rename.
    "PremierMandatory": "WTA1000", "Premier5": "WTA1000",
    "Premier": "WTA500", "International": "WTA250",
    "Finals": "Finals",
    # The API renamed 125K -> WTA 125 without changing its model role.
    "125K": "WTA125", "WTA125": "WTA125",
}
_SCOPES = {"main", "lower", "all"}


# Resume cache for completed-season backfills; set ONLY by download_wta_stats for
# years strictly before the current one. Current-season and incremental fetches
# always hit the network (their upstream data still changes).
_CACHE: ResponseCache | None = None


class WtaTransportError(RuntimeError):
    """Retry-exhausted transport failure; abort the year but keep its response cache."""


class WtaMissingRecordError(RuntimeError):
    """Deterministic upstream 404; a coverage hole, not evidence of an outage."""


def _get(path: str, params: dict | None = None, retries: int = RETRIES,
         raise_on_failure: bool = False):
    """GET with patient exponential backoff. Returns None only after all retries —
    callers that must not truncate silently should use _get_or_raise."""
    url = f"{BASE}{path}"
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    if _CACHE is not None:
        hit, cached = _CACHE.get(url)
        if hit:
            return cached           # no PAUSE_S: a fully-cached rerun takes seconds
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            time.sleep(PAUSE_S)
            if _CACHE is not None:
                _CACHE.put(url, data)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                if _CACHE is not None:
                    _CACHE.put(url, None)   # deterministic 404s are cacheable too
                return None          # deterministic: the record does not exist upstream
            if attempt == retries - 1:
                if raise_on_failure:
                    raise WtaTransportError(
                        f"WTA API HTTP {e.code} after {retries} attempts: {path}") from e
                return None
            # 429: the API wants a real cool-down, not a quick retry
            time.sleep(min(120, 30 * (attempt + 1)) if e.code == 429 else 2 ** attempt)
        except Exception as e:  # noqa: BLE001 — transient network error: retry or surface
            if attempt == retries - 1:
                if raise_on_failure:
                    raise WtaTransportError(
                        f"WTA API unreachable after {retries} attempts: {path}") from e
                return None
            time.sleep(2 ** attempt)
    return None


def _get_or_raise(path: str, params: dict | None = None):
    d = _get(path, params, raise_on_failure=True)
    if d is None:
        raise WtaMissingRecordError(f"WTA API has no record for: {path}")
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


def _normalized_level(raw: object) -> tuple[str, str] | None:
    """Return (canonical level, draw-level role), or None for non-model ITFs."""
    level = re.sub(r"\s+", "", str(raw or ""))
    if raw in _SKIP_LEVELS or level == "ITF":
        return None
    canonical = _LEVEL_MAP.get(level, level)
    return canonical, ("chall" if canonical == "WTA125" else "main")


def fetch_tournaments(year: int, scope: str = "main") -> list[dict]:
    """WTA tournaments for one season, classified by model-population role.

    ``main`` excludes 125s. ``lower`` and ``all`` retain every tour/125 event because
    qualifying lives inside the parent event's match list; `scrape_tournament` then
    selects only the requested match roles. Duplicate API catalogue rows are collapsed
    by stable tournament id + edition before any match calls.
    """
    if scope not in _SCOPES:
        raise ValueError(f"unknown WTA scrape scope {scope!r}")
    items = _paged("/tournaments/", "content",
                   {"from": f"{year}-01-01", "to": f"{year}-12-31"})
    out: dict[tuple[str, int], dict] = {}
    for t in items:
        classified = _normalized_level(t.get("level"))
        if classified is None:
            continue
        level, draw_level = classified
        if scope == "main" and draw_level != "main":
            continue
        ev = {
            "id": t["tournamentGroup"]["id"],
            "name": str(t["tournamentGroup"].get("name") or "").title(),
            "year": t["year"],
            "level": level,
            "draw_level": draw_level,
            "surface": t.get("surface"),
            "indoor": t.get("inOutdoor"),                     # "I" / "O"
            "start": t.get("startDate"), "end": t.get("endDate"),
            "draw": t.get("singlesDrawSize") or 0,
        }
        out[(str(ev["id"]), int(ev["year"]))] = ev
    return list(out.values())


def _round_label(round_id: str, draw: int) -> str | None:
    if round_id in ("F", "S", "Q"):
        return {"F": "F", "S": "SF", "Q": "QF"}[round_id]
    if not str(round_id).isdigit() or not draw or int(round_id) < 1:
        return None                        # RoundID 0 = round-robin/unlabeled
    size = 2 ** (draw - 1).bit_length()                       # next power of two
    size >>= int(round_id) - 1                                # field size at this round
    return f"R{size}" if size >= 16 else {8: "QF", 4: "SF", 2: "F"}.get(size)


def _match_draw_level(ev: dict, match: dict) -> str | None:
    """Classify one singles match independently of the directory it will use."""
    if match.get("DrawMatchType") != "S":
        return None
    level = str(match.get("DrawLevelType") or "")
    if level == "Q":
        return "qual"
    if level == "M":
        return str(ev.get("draw_level") or "main")
    return None


def _match_round(ev: dict, match: dict, draw_level: str | None) -> str | None:
    """Canonical round from the current catalogue, preserving unknown qualifying stage."""
    round_id = str(match.get("RoundID") or "")
    if draw_level == "qual" and round_id.isdigit():
        return f"Q{round_id}"
    return _round_label(round_id, int(ev["draw"] or 0))


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


def _stats_row(ev: dict, m: dict, st: dict, draw_level: str | None = None) -> dict | None:
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
    draw_level = draw_level or _match_draw_level(ev, m) or "main"
    round_label = (f"Q{m.get('RoundID')}" if draw_level == "qual"
                   and str(m.get("RoundID") or "").isdigit()
                   else _round_label(str(m.get("RoundID")), int(ev["draw"] or 0)))
    row.update({
        "tourney_id": f"{ev['year']}-W{ev['id']}",
        "tourney_name": ev["name"], "surface": ev["surface"], "indoor": ev["indoor"],
        "tourney_level": "Q" if draw_level == "qual" else ev["level"],
        "draw_level": draw_level, "source_match_id": str(m.get("MatchID") or ""),
        "draw_size": ev["draw"] or None,
        "tourney_date": date.replace("-", ""),
        "match_num": None, "best_of": 3,
        "round": round_label,
        "score": _winner_first_score(m, a_won),
        "winner_name": f"{wf} {wl}", "loser_name": f"{lf} {ll}",
        "winner_ioc": m.get(f"PlayerCountry{w.upper()}"), "loser_ioc": m.get(f"PlayerCountry{l.upper()}"),
        "winner_id": m.get(f"PlayerID{w.upper()}"), "loser_id": m.get(f"PlayerID{l.upper()}"),
        "winner_entry": m.get(f"EntryType{w.upper()}") or None,
        "loser_entry": m.get(f"EntryType{l.upper()}") or None,
        "winner_seed": m.get(f"Seed{w.upper()}") or None, "loser_seed": m.get(f"Seed{l.upper()}") or None,
    })
    return row


def _row_key(row: dict | pd.Series) -> str:
    """Stable source identity for resume skips and non-regressive union writes."""
    get = row.get
    source_id = str(get("source_match_id") or "").strip()
    if source_id and source_id.lower() != "nan":
        return f"id:{str(get('tourney_id') or '')}:{source_id}"
    return "|".join((
        str(get("tourney_id") or ""), _name_key(get("winner_name")),
        _name_key(get("loser_name")), str(get("round") or "").strip().upper(),
    ))


def _match_key(ev: dict, match: dict, draw_level: str) -> str:
    """Build the same fallback key as `_row_key` before fetching match stats."""
    a_won = str(match.get("Winner")) == "2"
    if str(match.get("Winner")) not in ("2", "3"):
        return ""
    w, l = ("A", "B") if a_won else ("B", "A")
    round_label = _match_round(ev, match, draw_level)
    row = {
        "tourney_id": f"{ev['year']}-W{ev['id']}",
        "winner_name": f"{match.get(f'PlayerNameFirst{w}') or ''} "
                       f"{match.get(f'PlayerNameLast{w}') or ''}",
        "loser_name": f"{match.get(f'PlayerNameFirst{l}') or ''} "
                      f"{match.get(f'PlayerNameLast{l}') or ''}",
        "score": _winner_first_score(match, a_won), "round": round_label,
    }
    row["winner_name"] = row["winner_name"].strip()
    row["loser_name"] = row["loser_name"].strip()
    return _row_key(row)


def scrape_tournament(ev: dict, scope: str = "main",
                      known_keys: set[str] | None = None,
                      observed_roles: dict[str, tuple[str, str, str | None]] | None = None
                      ) -> list[dict]:
    if scope not in _SCOPES:
        raise ValueError(f"unknown WTA scrape scope {scope!r}")
    matches = _paged(f"/tournaments/{ev['id']}/{ev['year']}/matches", "matches")
    rows = []
    for m in matches:
        draw_level = _match_draw_level(ev, m)
        source_id = str(m.get("MatchID") or "").strip()
        source_key = (f"id:{ev['year']}-W{ev['id']}:{source_id}" if source_id else "")
        if observed_roles is not None and source_key and draw_level is not None:
            # The match catalogue is the source of truth for draw role.  Keep this
            # evidence even when the requested scope excludes the match: a row already
            # on disk may need to move between the main and lower overlays without
            # spending another stats request.
            observed_roles[source_key] = (
                draw_level,
                "Q" if draw_level == "qual" else str(ev["level"]),
                _match_round(ev, m, draw_level),
            )
        wanted = ((scope in ("main", "all") and draw_level == "main")
                  or (scope in ("lower", "all") and draw_level in ("chall", "qual")))
        if not wanted:
            continue
        if m.get("MatchState") != "F":
            continue
        fallback_key = _match_key(ev, m, str(draw_level))
        if known_keys is not None and ((source_key and source_key in known_keys)
                                       or fallback_key in known_keys):
            continue                       # immutable row already on disk: do not re-spend API budget
        st = _get(f"/tournaments/{ev['id']}/{ev['year']}/matches/{m['MatchID']}/stats",
                  raise_on_failure=True)
        st0 = next((s for s in st or [] if s.get("setnum") == 0), None)
        if not st0:
            continue
        row = _stats_row(ev, m, st0, draw_level)
        if row:
            rows.append(row)
    return rows


# columns a scraped row can inherit from a local duplicate of the same match
_ENRICH_COLS = ("winner_rank", "loser_rank", "winner_rank_points", "loser_rank_points",
                "winner_age", "loser_age", "winner_ht", "loser_ht",
                "winner_hand", "loser_hand")


def _enrich_from_local(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Inherit rankings/bios (and RET-marked scores) from local duplicates of the
    same match — the fresh overlay first, then the frozen historical archive (the
    only local source for backfill years, where no fresh file exists). Scraped rows
    out-rank both in the merge, so anything only they carry would otherwise be lost
    (rankings, per-match age — the API returns neither)."""
    if df.empty:
        return df
    df["__k"] = df["winner_name"].map(_name_key) + "|" + df["loser_name"].map(_name_key)
    for f in (fresh_dir("wta") / f"{year}.csv", historical_dir("wta") / f"{year}.csv"):
        if not f.exists():
            continue
        loc = pd.read_csv(f, low_memory=False, encoding="utf-8-sig")
        loc["__k"] = loc["winner_name"].map(_name_key) + "|" + loc["loser_name"].map(_name_key)
        loc = loc.drop_duplicates("__k", keep="last")          # latest meeting wins
        idx = loc.set_index("__k")
        for col in _ENRICH_COLS:
            if col in loc.columns:
                df[col] = df[col].where(df[col].notna(), df["__k"].map(idx[col]))
        # keep the local RET/W-O marker so parse_score flags retirements correctly —
        # but only when the games agree (the pair may have met twice in the year, and
        # a rematch's marker must not overwrite this meeting's score)
        loc_score = df["__k"].map(idx["score"]) if "score" in loc.columns else None
        if loc_score is not None:
            ret = loc_score.astype(str).str.contains("RET|W/O|DEF|ABN|ABD", case=False, na=False)
            same = [
                bool(r) and (_score_key(fs).startswith(_score_key(ms))
                             or _score_key(ms).startswith(_score_key(fs)))
                for r, fs, ms in zip(ret, loc_score.astype(str), df["score"].astype(str))
            ]
            df.loc[same, "score"] = loc_score[same]
    return df.drop(columns="__k")


def scrape_year(year: int, since: datetime | None = None, scope: str = "main",
                known_keys: set[str] | None = None,
                observed_roles: dict[str, tuple[str, str, str | None]] | None = None
                ) -> pd.DataFrame:
    if scope not in _SCOPES:
        raise ValueError(f"unknown WTA scrape scope {scope!r}")
    events = fetch_tournaments(year, scope=scope)
    if since is not None:
        events = [e for e in events
                  if e["end"] and pd.Timestamp(e["end"]) >= pd.Timestamp(since.date())]
    print(f"    wta/stats {year}: {len(events)} tour-level events", flush=True)
    rows: list[dict] = []
    empty: list[str] = []
    missing: list[str] = []
    dead: list[str] = []
    for ev in events:
        try:
            got = scrape_tournament(ev, scope=scope, known_keys=known_keys,
                                    observed_roles=observed_roles)
        except WtaTransportError:
            # A rate-limit wall/outage affects every remaining event.  Abort immediately;
            # the completed-season response cache makes the next singular-year run resume.
            raise
        except WtaMissingRecordError as e:
            # Historical catalogue rows commonly point at editions the detail API no
            # longer serves.  A cached 404 is deterministic source coverage, never a
            # season-wide outage signal.
            print(f"    wta/stats {year} {ev['name']}: MISSING ({e})", flush=True)
            missing.append(ev["name"])
            continue
        except RuntimeError as e:
            # a single permanently-dead event endpoint (old seasons have a few)
            # must not kill the season — the merge is purely additive. A MAJORITY
            # of failures is a real outage/throttle storm and still raises below.
            print(f"    wta/stats {year} {ev['name']}: HARD FAIL ({e})", flush=True)
            dead.append(ev["name"])
            continue
        rows += got
        if not got:
            empty.append(ev["name"])
        if got:
            print(f"    wta/stats {year} {ev['name']}: {len(got)} matches", flush=True)
    if dead and len(dead) > max(2, len(events) // 5):
        raise RuntimeError(f"WTA API: {len(dead)}/{len(events)} events hard-failed "
                           f"for {year} — treating as an outage, not data absence")
    if empty:
        print(f"    wta/stats {year}: 0 stat rows for {len(empty)} event(s): "
              f"{', '.join(empty[:8])}{'...' if len(empty) > 8 else ''}", flush=True)
    if missing:
        print(f"    wta/stats {year}: {len(missing)} deterministic missing event endpoint(s)",
              flush=True)
    # Plain construction: rows carry CANON keys plus extras (entry/seed) that the
    # loader's reindex-with-extras keeps for the combiner's qualifier feature. Preserve
    # tolerated per-event failures as machine-readable completion evidence: a current-
    # season bootstrap can persist all successful rows, then refuse to bless the season
    # as complete until a later resumable pass recovers every transient hard failure.
    result = (pd.DataFrame(rows) if rows else
              pd.DataFrame(columns=[*CANON, "draw_level", "source_match_id"]))
    result.attrs["hard_failed_events"] = tuple(dead)
    return result


def _year_path(year: int, lower: bool = False):
    return ((lower_dir("wta") / f"{year}_wta_lower.csv") if lower
            else (stats_dir("wta") / f"{year}.csv"))


def _existing_keys(year: int, lower: bool = False) -> set[str]:
    path = _year_path(year, lower=lower)
    if not path.exists():
        return set()
    old = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
    return {_row_key(r) for _, r in old.iterrows()}


def _reclassify_existing(year: int,
                         observed_roles: dict[str, tuple[str, str, str | None]]) -> int:
    """Move cached source rows to the role currently reported by the catalogue.

    Match stats are immutable enough to reuse, but WTA occasionally corrects
    ``DrawLevelType`` after first publication.  Only exact source-match ids are
    eligible here; unrelated and legacy fallback-key rows remain in their original
    files. Role, tier, and round all follow the current catalogue. A duplicate-preserving
    bridge is installed before either source copy is removed, so interruption can leave a
    recoverable duplicate but cannot lose the only stats-bearing row. A second run is a
    no-op once metadata and physical file agree with the catalogue.
    """
    if not observed_roles:
        return 0

    main_path, lower_path = _year_path(year), _year_path(year, lower=True)
    frames: list[pd.DataFrame] = []
    for path, is_lower in ((main_path, False), (lower_path, True)):
        if not path.exists():
            continue
        frame = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
        frame["__origin_lower"] = is_lower
        frames.append(frame)
    if not frames:
        return 0

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["__key"] = [_row_key(row) for _, row in combined.iterrows()]
    combined["__target_lower"] = combined["__origin_lower"]
    key_indices: dict[str, list[int]] = {}
    for idx, key in combined["__key"].items():
        if key in observed_roles:
            key_indices.setdefault(key, []).append(idx)

    changed: set[str] = set()
    drop_indices: list[int] = []

    def _value(value) -> str:
        return "" if pd.isna(value) else str(value)

    for key, indices in key_indices.items():
        # A prior interrupted/manual repair may have left a row in both files.  Keep
        # one copy, then route it from the same catalogue evidence as the normal case.
        keep = indices[-1]
        if len(indices) > 1:
            drop_indices.extend(indices[:-1])
            changed.add(key)
        draw_level, tourney_level, round_label = observed_roles[key]
        target_lower = draw_level != "main"
        if (bool(combined.at[keep, "__origin_lower"]) != target_lower
                or _value(combined.at[keep, "draw_level"]
                          if "draw_level" in combined else None) != draw_level
                or _value(combined.at[keep, "tourney_level"]
                          if "tourney_level" in combined else None) != tourney_level
                or _value(combined.at[keep, "round"]
                          if "round" in combined else None) != _value(round_label)):
            changed.add(key)
        combined.at[keep, "draw_level"] = draw_level
        combined.at[keep, "tourney_level"] = tourney_level
        combined.at[keep, "round"] = round_label
        combined.at[keep, "__target_lower"] = target_lower

    if not changed:
        return 0
    if drop_indices:
        combined = combined.drop(index=drop_indices)

    helpers = ["__origin_lower", "__key", "__target_lower"]

    def _public(mask: pd.Series) -> pd.DataFrame:
        return combined.loc[mask].drop(columns=helpers).copy()

    target_lower = combined["__target_lower"].astype(bool)
    origin_lower = combined["__origin_lower"].astype(bool)
    final_frames = {
        main_path: _public(~target_lower),
        lower_path: _public(target_lower),
    }
    # Movers exist in both source and destination during the bridge phase. Every metadata
    # value is already corrected, so even a process failure leaves exact-key duplicates that
    # merge_sources can safely collapse, never a deleted stats record or stale main role.
    bridge_frames = {
        main_path: _public((~target_lower) | (~origin_lower)),
        lower_path: _public(target_lower | origin_lower),
    }

    staged = []
    try:
        for phase, frames_by_path in (("bridge", bridge_frames), ("final", final_frames)):
            phase_staged = []
            for path, frame in frames_by_path.items():
                if not path.exists() and frame.empty:
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(f".csv.role.{phase}.tmp")
                frame.to_csv(tmp, index=False)
                phase_staged.append((tmp, path))
                staged.append((tmp, path))
            for tmp, path in phase_staged:
                os.replace(tmp, path)
    finally:
        for tmp, _ in staged:
            if tmp.exists():
                tmp.unlink()
    return len(changed)


def write_year(year: int, df_new: pd.DataFrame, *, lower: bool = False) -> int:
    """Union valid rows into one overlay without regressing a partially served event.

    The old implementation replaced every row of an event whenever a refresh returned
    at least one row.  A transient per-match zero/404 could therefore shrink an otherwise
    good tournament.  Source match id is the preferred key; legacy rows fall back to the
    canonical event/pair/round identity used by the resume skip.
    """
    d = lower_dir("wta") if lower else stats_dir("wta")
    d.mkdir(parents=True, exist_ok=True)
    path = _year_path(year, lower=lower)
    if path.exists():
        old = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
        if df_new.empty:
            return len(old)
        df_new = pd.concat([old, df_new], ignore_index=True, sort=False)
    if df_new.empty:
        return 0
    level = df_new.get("draw_level", pd.Series("main", index=df_new.index)).fillna("main")
    df_new = df_new[level.ne("main") if lower else level.eq("main")].copy()
    df_new["__key"] = [_row_key(r) for _, r in df_new.iterrows()]
    df_new = df_new.drop_duplicates("__key", keep="last").drop(columns="__key")
    df_new = _enrich_from_local(df_new, year)
    tmp = path.with_suffix(".csv.tmp")   # atomic: a crash mid-write must not corrupt the year file
    df_new.to_csv(tmp, index=False)
    os.replace(tmp, path)
    return len(df_new)


def _one_year(years) -> int:
    now = datetime.now(UTC)
    if years is None:
        return now.year
    years = list(years)
    if len(years) != 1:
        raise ValueError("WTA backfills accept exactly one year per run")
    return int(years[0])


def download_wta_stats(years=None, incremental: bool = False, scope: str = "main",
                       require_complete: bool = False) -> None:
    global _CACHE
    now = datetime.now(UTC)
    year = _one_year(years)
    if scope not in _SCOPES:
        raise ValueError(f"unknown WTA scrape scope {scope!r}")
    since = now - timedelta(days=INCREMENTAL_DAYS) if incremental else None
    # Completed seasons are immutable enough for resumable acquisition: cache their
    # successful responses so a throttled/crashed rerun starts where it stopped.
    # Delete this one year's cache explicitly when probing a later upstream repair.
    use_cache = year < now.year and not incremental
    _CACHE = (ResponseCache(stats_dir("wta") / "_httpcache" / str(year))
              if use_cache else None)
    # Read both stores for every scope.  If a known id is currently in the wrong
    # store, the catalogue can reclassify its cached stats instead of refetching them.
    known = _existing_keys(year, lower=False) | _existing_keys(year, lower=True)
    observed_roles: dict[str, tuple[str, str, str | None]] = {}
    try:
        scraped = scrape_year(year, since=since, scope=scope, known_keys=known,
                              observed_roles=observed_roles)
        hard_failed_events = tuple(scraped.attrs.get("hard_failed_events", ()))
        reclassified = _reclassify_existing(year, observed_roles)
        if reclassified:
            print(f"    wta/stats {year}: reclassified {reclassified} cached row(s)",
                  flush=True)
        roles = scraped.get("draw_level", pd.Series("main", index=scraped.index)).fillna("main")
        main = scraped[roles.eq("main")]
        lower_rows = scraped[roles.ne("main")]
        n_main = (write_year(year, main, lower=False) if scope in ("main", "all")
                  else (len(pd.read_csv(_year_path(year))) if _year_path(year).exists() else 0))
        n_lower = (write_year(year, lower_rows, lower=True) if scope in ("lower", "all")
                   else (len(pd.read_csv(_year_path(year, True)))
                         if _year_path(year, True).exists() else 0))
    finally:
        _CACHE = None
    print(f"  wta/stats: {year} main={n_main} lower={n_lower} rows (scope={scope})",
          flush=True)
    if require_complete and hard_failed_events:
        names = ", ".join(hard_failed_events[:8])
        suffix = "..." if len(hard_failed_events) > 8 else ""
        raise RuntimeError(
            f"WTA API: current-season bootstrap incomplete; {len(hard_failed_events)} "
            f"event(s) hard-failed ({names}{suffix}); successful rows were retained for retry"
        )


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None,
                    help="one season only (completed-season backfills are deliberately singular)")
    ap.add_argument("--incremental", action="store_true",
                    help="only re-fetch tournaments ending in the last ~3 weeks")
    ap.add_argument("--scope", choices=sorted(_SCOPES), default="main",
                    help="main draw, lower-state rows (qualifying/125), or both")
    args = ap.parse_args()
    download_wta_stats([args.year] if args.year is not None else None,
                       incremental=args.incremental, scope=args.scope)
