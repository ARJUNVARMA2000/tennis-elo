"""Kalshi-vs-model evaluation ledger: one CSV row per Kalshi tennis match event.

Joins the Kalshi snapshot cache (data/kalshi.py) to our results frame and our own
pre-match probabilities, and upserts data/kalshi_ledger/{tour}.csv — the durable,
repo-committed record the scorecard (eval/kalshi_report.py) is built from.

Orientation invariant: player_a is ALWAYS the player whose name_key sorts first.
Every probability is re-oriented to that convention at write time — the forecast
log's A/B order, Kalshi's listing order and the winner/loser order are inputs to
re-orient FROM, never the row's identity.

Where p_model comes from (precedence: live > backtest > blank):
  live      forecast_log/{tour}.jsonl — the probability frozen at first sighting,
            before the result existed (eval/track.py).
  backtest  walk-forward OOS p_combiner — used to backfill the pre-log era
            (Kalshi history starts 2026-04-30; the log starts 2026-06-29). Honest
            walk-forward, but computed with TODAY'S model code — the report must
            always split by pred_source.

Frozen-field policy on upsert: candle prices, matched identity/result fields and a
live p_model never change once written; everything else refreshes each run.

Run:  PYTHONPATH=src python -m tennis_model.eval.kalshi_ledger --tour all
      [--backfill]   also compute walk-forward OOS probs for the pre-log era (slow)
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from datetime import UTC, date, datetime

import pandas as pd

from .. import __version__
from ..config import KALSHI_LEDGER_DIR, TOURS
from ..data.kalshi import (
    CANDLE_LOOKBACK_S,
    EXTREME_CARRY_MID,
    KALSHI_ALIASES,
    _epoch,
    load_snapshots,
)
from ..data.names import name_key
from ..data.rankings import load_rankings
from .track import FORECAST_DIR, _norm_event, _read_log

KALSHI_ERA_START = "2026-04-01"     # ignore results older than the first Kalshi market
JOIN_MIN_D, JOIN_MAX_D = -8, 21     # occurrence minus result date, asymmetric both
                                    # ways: archive rows carry the TOURNAMENT START
                                    # date (a slam final's row is ~13 days early),
                                    # while Kalshi creates markets at draw time with
                                    # a placeholder start — actual play runs up to
                                    # ~7 days after occurrence (verified backfill
                                    # gap cluster at -5..-7)
JOIN_SUSPECT_D = 3                  # a result more than this many days before occurrence
                                    # is legit ONLY as a tournament-start-dated archive
                                    # row, so it must agree with the market's parsed
                                    # tournament rule (audit 2026-07-09: a Wimbledon-QF
                                    # market froze the same pair's 18-day-old Halle
                                    # result — the market listed before its match was
                                    # played and the old result was the only candidate)
PENDING_GRACE_D = 3                 # no result this soon after start = pending, not unmatched
FORECAST_MIN_D, FORECAST_MAX_D = -1, 21   # occurrence minus forecast as_of (track.py)

LEDGER_COLUMNS = [
    "event_ticker", "tour", "season", "occurrence_utc", "match_date",
    "event", "round", "surface", "tier", "best_of",
    "player_a", "player_b", "rank_a", "rank_b", "rank_src", "ticker_a", "ticker_b",
    "mid_a", "mid_b", "p_kalshi", "p_kalshi_t30", "spread_max", "price_ts",
    "price_kind", "volume_total", "oi_total", "liquidity",
    "p_model", "pred_source", "model_version", "model_as_of",
    "match_status", "result_type", "winner", "a_won", "result_date", "kalshi_result_a",
]
# never overwritten once set (see module docstring)
_FROZEN_PRICE = ["mid_a", "mid_b", "p_kalshi", "p_kalshi_t30", "spread_max",
                 "price_ts", "price_kind", "volume_total", "oi_total", "liquidity"]
_FROZEN_MATCH = ["event", "round", "surface", "tier", "best_of",
                 "player_a", "player_b", "rank_a", "rank_b", "rank_src",
                 "match_status", "result_type", "winner", "a_won", "result_date"]
_FROZEN_PRED = ["p_model", "pred_source", "model_version", "model_as_of"]


def devig(mid_a: float, mid_b: float) -> float:
    """Two-market implied probability of A, normalized so A+B sums to 1."""
    return mid_a / (mid_a + mid_b)


def _f(x: object, dp: int = 4) -> str:
    """Float -> fixed-dp string; ''/None/NaN -> '' (CSV cells are plain strings)."""
    if x is None or x == "":
        return ""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return ""
    return "" if pd.isna(v) else f"{v:.{dp}f}"


def _i(x: object) -> str:
    try:
        v = float(x)
        return "" if pd.isna(v) else str(int(v))
    except (TypeError, ValueError):
        return ""


def _alias(key: str) -> str:
    return KALSHI_ALIASES.get(key, key)


# ---------------------------------------------------------------------------
# Indexes (results / forecast log / OOS)
# ---------------------------------------------------------------------------
def _result_index(df: pd.DataFrame) -> dict:
    """frozenset(name-key pair) -> [result-row dicts], Kalshi-era rows only.

    ALL rows, not just completed — walkovers and retirements must be labellable."""
    era = df[df["date"] >= pd.Timestamp(KALSHI_ERA_START)]
    idx: dict = defaultdict(list)
    for r in era.itertuples(index=False):
        wk, lk = name_key(r.winner_name), name_key(r.loser_name)
        if not wk or not lk or wk == lk:
            continue
        idx[frozenset((wk, lk))].append({
            "date": pd.Timestamp(r.date), "winner": r.winner_name, "loser": r.loser_name,
            "winner_rank": getattr(r, "winner_rank", None),
            "loser_rank": getattr(r, "loser_rank", None),
            "event": str(getattr(r, "tourney_name", "") or ""),
            "round": str(getattr(r, "round", "") or ""),
            "surface": str(getattr(r, "surface_b", "") or ""),
            "tier": str(getattr(r, "tier", "") or ""),
            "best_of": getattr(r, "best_of", None),
            "completed": bool(getattr(r, "completed", False)),
            "walkover": bool(getattr(r, "walkover", False)),
        })
    return idx


def _forecast_index(tour: str) -> dict:
    """frozenset(pair) -> [{as_of, playerA, p, model_version}] from the forecast log."""
    idx: dict = defaultdict(list)
    for r in _read_log(FORECAST_DIR / f"{tour}.jsonl"):
        if r.get("type") != "match" or "p" not in r:
            continue
        ka, kb = name_key(r.get("playerA")), name_key(r.get("playerB"))
        if ka and kb and ka != kb:
            idx[frozenset((ka, kb))].append(r)
    return idx


def _oos_index(oos: pd.DataFrame | None) -> dict:
    """(winner_key, loser_key, date) -> winner-oriented p_combiner."""
    if oos is None or len(oos) == 0 or "p_combiner" not in oos:
        return {}
    era = oos[oos["date"] >= pd.Timestamp(KALSHI_ERA_START)]
    return {(name_key(w), name_key(l), pd.Timestamp(d).date()): float(p)
            for w, l, d, p in zip(era["winner_name"], era["loser_name"],
                                  era["date"], era["p_combiner"])}


# ---------------------------------------------------------------------------
# Join pieces
# ---------------------------------------------------------------------------
def _match_result(cands: list[dict], occ: date, rules: dict,
                  claimed: dict | None = None, ticker: str = "") -> tuple[dict | None, bool]:
    """Pick the result row for one Kalshi event -> (row | None, ambiguous).

    claimed maps result_date iso -> the ticker already holding that result in the
    ledger: one result row, one ticker — a candidate claimed elsewhere is invisible
    here (rematch relists / stale captures can otherwise double-score one match).
    Far-forward candidates (result more than JOIN_SUSPECT_D days before occurrence)
    are legit only as tournament-start-dated archive rows, so when the market names
    a tournament they must agree with it — the tiebreaker becomes a validator."""
    valid = [c for c in cands if JOIN_MIN_D <= (occ - c["date"].date()).days <= JOIN_MAX_D]
    if claimed:
        valid = [c for c in valid
                 if claimed.get(c["date"].strftime("%Y-%m-%d")) in (None, ticker)]
    rk = _norm_event(rules["tournament"]) if rules.get("tournament") else ""
    if rk:
        def _stale_capture(c: dict) -> bool:
            if (occ - c["date"].date()).days <= JOIN_SUSPECT_D:
                return False
            ck = _norm_event(c["event"])
            return not (ck and (ck in rk or rk in ck))
        valid = [c for c in valid if not _stale_capture(c)]
    if not valid:
        return None, False
    if len(valid) > 1 and rules.get("tournament"):
        rk = _norm_event(rules["tournament"])
        by_event = [c for c in valid
                    if rk and (_norm_event(c["event"]) in rk or rk in _norm_event(c["event"]))]
        valid = by_event or valid
    if len(valid) > 1 and rules.get("round"):
        by_round = [c for c in valid if c["round"] == rules["round"]]
        valid = by_round or valid
    if len(valid) > 1:
        days = [abs((occ - c["date"].date()).days) for c in valid]
        best = min(days)
        closest = [c for c, d in zip(valid, days) if d == best]
        if len(closest) > 1:
            return None, True                        # tie we cannot break -> ambiguous
        valid = closest
    return valid[0], False


def _pick_forecast(cands: list[dict], occ: date) -> dict | None:
    """Earliest in-window forecast-log record (first sighting = genuinely pre-match)."""
    valid = [r for r in cands
             if FORECAST_MIN_D <= (occ - date.fromisoformat(str(r["as_of"]))).days
             <= FORECAST_MAX_D]
    return min(valid, key=lambda r: str(r["as_of"])) if valid else None


def _rank_for(res: dict | None, key: str, live_ranks: dict) -> tuple[str, str]:
    """(rank, source) for one player: matched result row first, live scrape fallback."""
    if res is not None:
        col = "winner_rank" if name_key(res["winner"]) == key else "loser_rank"
        r = _i(res.get(col))
        if r:
            return r, "results"
    live = live_ranks.get(key)
    if live and live.get("rank"):
        return str(int(live["rank"])), "live"
    return "", ""


# ---------------------------------------------------------------------------
# Row assembly
# ---------------------------------------------------------------------------
def _occ_date(e: dict) -> date | None:
    try:
        return datetime.fromisoformat(
            str(e.get("occurrence") or "").replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _oriented(e: dict) -> tuple:
    """Sorted-side view of one snapshot event: (a, b, ka, kb, price, mids, t30s)."""
    a, b = e["a"], e["b"]
    ka, kb = _alias(name_key(a["name"])), _alias(name_key(b["name"]))
    price = e.get("price") or {}
    mid_a, mid_b = price.get("mid_a"), price.get("mid_b")
    t30_a, t30_b = price.get("mid_a_t30"), price.get("mid_b_t30")
    if ka > kb:          # unsorted snapshot / aliasing flipped the order: swap sides,
        a, b, ka, kb = b, a, kb, ka                  # prices travel with their player
        mid_a, mid_b, t30_a, t30_b = mid_b, mid_a, t30_b, t30_a
    return a, b, ka, kb, price, mid_a, mid_b, t30_a, t30_b


def _healed_tickers(prior: dict) -> set[str]:
    """Previously-frozen matched rows whose join is PROVABLY wrong, released from the
    frozen-field policy for one run so they can re-match and re-quote under current
    rules: (a) Kalshi's own settlement contradicts the joined completed result, or
    (b) two tickers hold the same (pair, result_date) — a rematch relist / stale
    capture; the one farther from the result (then the later occurrence) loses.
    Deliberately narrow: only objective wrongness heals — window/rule heuristics never
    unfreeze a row on their own, so archive-dated joins stay stable."""
    healed: set[str] = set()
    by_claim: dict[tuple, list] = defaultdict(list)
    for tick, r in prior.items():
        if r.get("match_status") != "matched" or not r.get("result_date"):
            continue
        ka_res, a_won = r.get("kalshi_result_a"), r.get("a_won")
        if (r.get("result_type") == "completed" and ka_res in ("yes", "no")
                and a_won in ("0", "1") and (ka_res == "yes") != (a_won == "1")):
            healed.add(tick)
            continue
        pk = frozenset((_alias(name_key(r.get("player_a") or "")),
                        _alias(name_key(r.get("player_b") or ""))))
        if len(pk) != 2:
            continue
        try:
            occ = datetime.fromisoformat(
                str(r.get("occurrence_utc") or "").replace("Z", "+00:00")).date()
            gap = abs((occ - date.fromisoformat(r["result_date"])).days)
        except ValueError:
            gap = 9999
        by_claim[(pk, r["result_date"])].append(
            (gap, str(r.get("occurrence_utc") or ""), tick))
    for lst in by_claim.values():
        if len(lst) > 1:
            lst.sort()
            healed.update(t for _, _, t in lst[1:])
    return healed


def build_rows(tour: str, snaps: dict, df: pd.DataFrame,
               oos: pd.DataFrame | None = None,
               prior: dict | None = None) -> list[dict]:
    """One ledger row dict (all-string values, pinned columns) per snapshot event.

    prior (the existing ledger, ticker -> row dict) contributes result CLAIMS: a
    result row already matched by one ticker is invisible to every other ticker, so
    a market listed for a future rematch can never bind (and double-score) the
    pair's previous result. Healed tickers' claims are ignored."""
    res_idx = _result_index(df)
    fc_idx = _forecast_index(tour)
    oos_idx = _oos_index(oos)
    live_ranks = load_rankings(tour)
    today = datetime.now(UTC).date()

    prior = prior or {}
    healed = _healed_tickers(prior)
    claims_by_pair: dict[frozenset, dict[str, str]] = defaultdict(dict)
    for tick, r in prior.items():
        if tick in healed or r.get("match_status") != "matched" or not r.get("result_date"):
            continue
        pk = frozenset((_alias(name_key(r.get("player_a") or "")),
                        _alias(name_key(r.get("player_b") or ""))))
        if len(pk) == 2:
            claims_by_pair[pk][r["result_date"]] = tick

    # pass 1: propose a result join per event (prior claims + settlement consistency)
    prepared: list[tuple] = []
    for ev, e in sorted(snaps.get("events", {}).items()):
        occ = _occ_date(e)
        if occ is None:
            continue                                 # no scheduled time: not usable
        a, _b, ka, kb, *_ = _oriented(e)
        res, ambiguous = _match_result(res_idx.get(frozenset((ka, kb)), []), occ,
                                       e.get("rules") or {},
                                       claimed=claims_by_pair.get(frozenset((ka, kb))),
                                       ticker=ev)
        if res is not None and res["completed"] and not res["walkover"]:
            ka_res = str(a.get("result") or "")
            if ka_res in ("yes", "no") and \
                    (ka_res == "yes") != (name_key(res["winner"]) == ka):
                # Kalshi's own settlement contradicts the joined result: a provably
                # wrong join (stale-rematch capture / alias collision) — never freeze
                res, ambiguous = None, True
        prepared.append([ev, e, occ, res, ambiguous])

    # pass 1b: intra-run dedupe — one result row, one ticker (closest occurrence wins)
    contenders: dict[tuple, list] = defaultdict(list)
    for i, (ev, e, occ, res, _amb) in enumerate(prepared):
        if res is None:
            continue
        _a, _b, ka, kb, *_ = _oriented(e)
        key = (frozenset((ka, kb)), res["date"].strftime("%Y-%m-%d"))
        contenders[key].append(
            (abs((occ - res["date"].date()).days), str(e.get("occurrence") or ""), ev, i))
    for lst in contenders.values():
        if len(lst) > 1:
            lst.sort()
            for *_, i in lst[1:]:
                prepared[i][3], prepared[i][4] = None, True

    # pass 2: assemble rows
    rows = []
    for ev, e, occ, res, ambiguous in prepared:
        occurrence = str(e.get("occurrence") or "")
        a, b, ka, kb, price, mid_a, mid_b, t30_a, t30_b = _oriented(e)

        if res is not None:
            status = "matched"
            a_name = res["winner"] if name_key(res["winner"]) == ka else res["loser"]
            b_name = res["loser"] if a_name == res["winner"] else res["winner"]
            a_won = name_key(res["winner"]) == ka
            rtype = ("walkover" if res["walkover"]
                     else "completed" if res["completed"] else "retired")
        elif "scalar" in (a.get("result"), b.get("result")):
            # Kalshi settled to a fair price: the match never happened (pre-match
            # withdrawal). Correctly absent from our frame — not an alias problem.
            status, rtype = "cancelled", "cancelled"
            a_name, b_name, a_won = a["name"], b["name"], None
        else:
            status = ("ambiguous" if ambiguous
                      else "pending" if (today - occ).days <= PENDING_GRACE_D
                      else "unmatched")
            a_name, b_name, a_won, rtype = a["name"], b["name"], None, "pending"

        # our probability: frozen live forecast first, walk-forward backfill second
        p_model = src = version = as_of = ""
        fc = _pick_forecast(fc_idx.get(frozenset((ka, kb)), []), occ)
        if fc is not None:
            p = float(fc["p"])
            p_model = _f(p if name_key(fc["playerA"]) == ka else 1.0 - p)
            src, version, as_of = "live", str(fc.get("model_version", "")), str(fc["as_of"])
        elif res is not None:
            p = oos_idx.get((name_key(res["winner"]), name_key(res["loser"]),
                             res["date"].date()))
            if p is not None:
                p_model = _f(p if a_won else 1.0 - p)
                src, version, as_of = "backtest", __version__, today.isoformat()

        rank_a, rank_src = _rank_for(res, ka, live_ranks)
        rank_b, rank_src_b = _rank_for(res, kb, live_ranks)
        rows.append({
            "event_ticker": ev, "tour": tour, "season": str(occ.year),
            "occurrence_utc": occurrence, "match_date": occ.isoformat(),
            "event": res["event"] if res else (e.get("rules") or {}).get("tournament") or "",
            "round": res["round"] if res else (e.get("rules") or {}).get("round") or "",
            "surface": res["surface"] if res else "",
            "tier": res["tier"] if res else "",
            "best_of": _i(res["best_of"]) if res else "",
            "player_a": a_name, "player_b": b_name,
            "rank_a": rank_a, "rank_b": rank_b,
            "rank_src": rank_src or rank_src_b,
            "ticker_a": str(a.get("ticker") or ""), "ticker_b": str(b.get("ticker") or ""),
            "mid_a": _f(mid_a), "mid_b": _f(mid_b),
            "p_kalshi": _f(devig(mid_a, mid_b)) if mid_a and mid_b else "",
            "p_kalshi_t30": _f(devig(t30_a, t30_b)) if t30_a and t30_b else "",
            "spread_max": _f(price.get("spread_max")),
            "price_ts": str(price.get("ts") or ""),
            "price_kind": str(price.get("kind") or "none"),
            "volume_total": _f(a.get("volume", 0) + b.get("volume", 0), 2),
            "oi_total": _f(a.get("oi", 0) + b.get("oi", 0), 2),
            "liquidity": _f(a.get("liquidity", 0) + b.get("liquidity", 0), 2),
            "p_model": p_model, "pred_source": src,
            "model_version": version, "model_as_of": as_of,
            "match_status": status, "result_type": rtype,
            "winner": res["winner"] if res else "",
            "a_won": "" if a_won is None else str(int(a_won)),
            "result_date": res["date"].strftime("%Y-%m-%d") if res else "",
            "kalshi_result_a": str(a.get("result") or ""),
        })
    return rows


# ---------------------------------------------------------------------------
# CSV upsert
# ---------------------------------------------------------------------------
def _read_ledger(path) -> dict:
    if not path.exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["event_ticker"]: dict(r) for r in csv.DictReader(f)}


def upsert(tour: str, rows: list[dict], healed: set[str] | None = None) -> dict:
    """Merge fresh rows into the ledger CSV under the frozen-field policy.

    Two sanctioned overrides of that policy: a `healed` ticker (provably-wrong prior
    join, see _healed_tickers) loses ALL freeze protection so the fresh row is
    authoritative; and a row marked _requoted by the 08:00 anchor requoter replaces a
    frozen price — the requoter is the only writer allowed to do that."""
    path = KALSHI_LEDGER_DIR / f"{tour}.csv"
    old = _read_ledger(path)
    merged = dict(old)
    healed = healed or set()
    n_new = 0
    for row in rows:
        prev = old.get(row["event_ticker"])
        if prev is None:
            n_new += 1
        elif row["event_ticker"] not in healed:
            if prev.get("price_kind") == "candle" and not row.get("_requoted"):
                row = {**row, **{c: prev[c] for c in _FROZEN_PRICE if c in prev}}
            if prev.get("match_status") == "matched":
                row = {**row, **{c: prev[c] for c in _FROZEN_MATCH if c in prev}}
            # p_model is write-once (the ledger is a record, not a live estimate);
            # the only allowed upgrade is backtest -> live (in practice never fires)
            prev_src = prev.get("pred_source")
            if prev_src and not (prev_src == "backtest"
                                 and row.get("pred_source") == "live"):
                row = {**row, **{c: prev[c] for c in _FROZEN_PRED if c in prev}}
        merged[row["event_ticker"]] = {c: row.get(c, "") for c in LEDGER_COLUMNS}

    KALSHI_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    out = sorted(merged.values(), key=lambda r: (r["occurrence_utc"], r["event_ticker"]))
    tmp = path.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    os.replace(tmp, path)

    matched = sum(1 for r in out if r["match_status"] == "matched")
    return {"total": len(out), "new": n_new, "matched": matched,
            "unmatched": sum(1 for r in out if r["match_status"] == "unmatched"),
            "pending": sum(1 for r in out if r["match_status"] == "pending"),
            "scoreable": sum(1 for r in out if r["match_status"] == "matched"
                             and r["result_type"] == "completed"
                             and r["price_kind"] == "candle"
                             and r["p_model"] and r["p_kalshi"])}


PREMATCH_UTC_HOUR = 8   # scoring quote = mid at 08:00 UTC on the result row's date.
# Why not Kalshi's occurrence_datetime: the field MUTATES over the market lifecycle —
# accurate-looking estimate while open, but on settled markets it drifts to ~the
# determination time (verified: close_time lands seconds after it), so "T-5 before
# occurrence" was sometimes the final in-play price. The result row's date is ours
# and immutable; 08:00 UTC precedes every first ball in this era's event footprint
# (earliest starts ~10:00 local European time), and for tournament-start-dated
# archive rows it is simply earlier still — stale-safe, never post-start.


def _scoring_quote_ok(prev: dict) -> bool:
    """True if a ledger row's frozen candle price is already a valid SCORING quote:
    matched, timestamped inside the morning fetch window of its own result_date, and
    not a settled-extreme carry print. Rows frozen while pending carry the snapshot's
    occurrence-anchored quote (the pending-race escape: possibly in-play), and a
    price_ts after the anchor means exactly that — both fail, so the requoter
    re-fetches them at 08:00 once the row is matched."""
    if prev.get("price_kind") != "candle" or prev.get("match_status") != "matched":
        return False
    rd = prev.get("result_date")
    ts = _epoch(prev.get("price_ts"))
    if not rd or ts is None:
        return False
    try:
        anchor = int(datetime.fromisoformat(
            f"{rd}T{PREMATCH_UTC_HOUR:02d}:00:00+00:00").timestamp())
    except ValueError:
        return False
    if ts > anchor:
        return False
    if ts <= anchor - CANDLE_LOOKBACK_S:
        for c in ("mid_a", "mid_b"):
            try:
                m = float(prev.get(c) or "")
            except ValueError:
                continue
            if not (1 - EXTREME_CARRY_MID < m < EXTREME_CARRY_MID):
                return False
    return True


def _requote_matched(tour: str, rows: list[dict], prior: dict | None = None,
                     healed: set[str] | None = None) -> int:
    """Fetch the 08:00 scoring quote for every matched row not already carrying one.

    The skip set is anchor-validated (_scoring_quote_ok), not merely candle-frozen:
    a pending-race occurrence-anchored freeze, a post-anchor print or a settled
    carry gets re-fetched at the true morning anchor. The match identity used is
    the one that will SURVIVE the merge — the frozen prior match when there is one
    (a transient results-source gap must not strand a bad quote behind a fresh
    unmatched row), else the fresh match. Touched rows are marked _requoted so
    upsert lets the fresh price supersede the frozen one; valid morning quotes are
    never refetched, keeping daily runs incremental."""
    from ..data.kalshi import fetch_prematch_quotes
    if prior is None:
        prior = _read_ledger(KALSHI_LEDGER_DIR / f"{tour}.csv")
    healed = healed or set()
    ok = {t for t, r in prior.items() if _scoring_quote_ok(r)}
    n = 0
    for row in rows:
        prev = prior.get(row["event_ticker"]) or {}
        prev_kept = row["event_ticker"] not in healed
        eff = (prev if prev_kept and prev.get("match_status") == "matched"
               else row if row["match_status"] == "matched" else None)
        has_candle = (row["price_kind"] == "candle"
                      or (prev_kept and prev.get("price_kind") == "candle"))
        if (eff is None or not has_candle or not eff.get("result_date")
                or (prev_kept and row["event_ticker"] in ok)):
            continue
        cutoff = int(datetime.fromisoformat(
            f"{eff['result_date']}T{PREMATCH_UTC_HOUR:02d}:00:00+00:00").timestamp())
        qa = fetch_prematch_quotes(tour, row["ticker_a"], cutoff)
        qb = fetch_prematch_quotes(tour, row["ticker_b"], cutoff)
        row["_requoted"] = "1"
        if not (qa and qb):
            # never score the occurrence-anchored quote (possibly in-play): degrade
            # the row; snapshots re-supply a candle next run, so this retries daily
            row.update({c: "" for c in ("mid_a", "mid_b", "p_kalshi", "p_kalshi_t30",
                                        "spread_max", "price_ts")})
            row["price_kind"] = "none"
            continue
        row.update({
            "mid_a": _f(qa["mid"]), "mid_b": _f(qb["mid"]),
            "p_kalshi": _f(devig(qa["mid"], qb["mid"])),
            "p_kalshi_t30": _f(devig(qa["mid_t30"], qb["mid_t30"]))
            if qa["mid_t30"] and qb["mid_t30"] else "",
            "spread_max": _f(max(qa["spread"], qb["spread"])),
            "price_ts": datetime.fromtimestamp(max(qa["ts"], qb["ts"]), UTC)
                                .strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
        n += 1
    return n


def refresh_ledger(tour: str, df: pd.DataFrame, oos: pd.DataFrame | None = None,
                   requote: bool = True) -> dict:
    """Pipeline entry point: snapshot cache -> rows -> CSV. Returns upsert counts."""
    prior = _read_ledger(KALSHI_LEDGER_DIR / f"{tour}.csv")
    healed = _healed_tickers(prior)
    if healed:
        print(f"  kalshi-ledger/{tour}: unfreezing {len(healed)} provably-wrong "
              f"match(es): {', '.join(sorted(healed)[:4])}"
              f"{', ...' if len(healed) > 4 else ''}")
    rows = build_rows(tour, load_snapshots(tour), df, oos=oos, prior=prior)
    if requote:
        n = _requote_matched(tour, rows, prior=prior, healed=healed)
        if n:
            print(f"  kalshi-ledger/{tour}: fetched {n} morning-of scoring quotes")
    stats = upsert(tour, rows, healed=healed)
    print(f"  kalshi-ledger/{tour}: {stats['total']} rows (+{stats['new']} new), "
          f"{stats['matched']} matched / {stats['unmatched']} unmatched / "
          f"{stats['pending']} pending; {stats['scoreable']} scoreable")
    return stats


if __name__ == "__main__":
    import argparse

    from ..data.results import load_matches

    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="all", help="atp | wta | all")
    ap.add_argument("--backfill", action="store_true",
                    help="walk-forward the current season for backtest-era p_model")
    args = ap.parse_args()
    for t in (TOURS if args.tour == "all" else [args.tour]):
        frame = load_matches(t)
        oos_frame = None
        if args.backfill:
            from ..model.features import build_predictor_inputs, main_rows
            from ..model.train import walk_forward, xgb_params_for
            print(f"  kalshi-ledger/{t}: walk-forward for the backfill era...")
            feat, *_ = build_predictor_inputs(frame)
            year = datetime.now(UTC).year
            oos_frame = walk_forward(main_rows(feat), start_test=year, end_test=year,
                                     xgb_overrides=xgb_params_for(t), verbose=False)
        refresh_ledger(t, frame, oos=oos_frame)
