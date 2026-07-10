"""Kalshi prediction-market client: public market data for the evaluation ledger.

Kalshi data is a BENCHMARK, never a model input — this module is a dumb API client
that knows nothing about our predictions (the join lives in eval/kalshi_ledger.py),
and tests/test_kalshi_purity.py pins that no model code ever imports it.

Market anatomy (verified against the live API 2026-07-06): one event per match
(KXATPMATCH-26JUL08COBFER), TWO binary markets per event — one per player, full name
in yes_sub_title, tournament + round inside rules_primary. Markets trade IN-PLAY, so
a settled market's last price is worthless (~0.99); the pre-match price is
reconstructed from 1-minute candlesticks: mid of yes bid/ask at T-5 min before
occurrence_datetime (scheduled start), plus a T-30 quote kept as an early-start leak
sentinel. Candlesticks remain fetchable after settlement (with a /historical fallback
once markets age out), so missed runs self-heal and the cache is rebuildable.

Snapshot cache: data/raw/kalshi/<tour>/snapshots.json, one entry per event. A price
extracted from candles is FROZEN (never refetched); open-market quotes stay
provisional until settlement. All fetches soft-fail to None — a Kalshi outage must
never break the build (data/odds.py doctrine).

Run:  PYTHONPATH=src python -m tennis_model.data.kalshi --tour all
      [--backfill-since 2026-04-30]   full history walk instead of incremental
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from ..config import TOURS, kalshi_dir
from .names import name_key

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = {"atp": "KXATPMATCH", "wta": "KXWTAMATCH"}
HEADERS = {"User-Agent": "tennis_model (research; model-vs-market evaluation)"}

PAUSE_S = 0.25          # spacing between requests (wta_stats.py convention)
RETRIES = 5
LEAD_S = 5 * 60         # primary pre-match quote: last candle <= T-5 min
LEAD_T30_S = 30 * 60    # sentinel quote at T-30 min (early-start leak detector)
CANDLE_LOOKBACK_S = 4 * 3600   # how far before scheduled start to request candles
GIVE_UP_DAYS = 14       # no usable candle this long after start -> freeze kind="none"
EXTREME_CARRY_MID = 0.99   # a pre-window carry candle at/beyond this mid is a settled
                           # print, not a tradable line (audit 2026-07-09: six post-result
                           # 04:00 carries scored 0.995 "favorites" the close had at 0.32-0.72)

# Kalshi spelling -> our canonical spelling, keyed and valued via name_key(). Additive
# (rankings.py ALIASES pattern): grow it from the report's unmatched-names table.
KALSHI_ALIASES: dict[str, str] = {
    "martin damm jr": "martin damm",
    "marcelo tomas barrios vera": "tomas barrios vera",
}


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------
def _get(path: str, params: dict | None = None) -> dict | None:
    """GET BASE+path -> parsed JSON; None on any persistent failure (soft-fail).

    404 is a deterministic None (used to trigger the /historical fallback); 429
    gets a patient cool-down; other errors back off exponentially.
    """
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            time.sleep(PAUSE_S)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(min(120, 30 * (attempt + 1)) if e.code == 429 else 2 ** attempt)
        except Exception:  # noqa: BLE001 — network/JSON: retry, then give up soft
            time.sleep(2 ** attempt)
    return None


# ---------------------------------------------------------------------------
# Parsing helpers (pure; unit-tested on fixtures)
# ---------------------------------------------------------------------------
def _dollars(x: object) -> float | None:
    """Kalshi money fields are decimal strings ('0.7000'); '' / None -> None."""
    try:
        return float(x) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _epoch(iso: object) -> int | None:
    """ISO-8601 (Z suffix) -> epoch seconds, UTC-safe. None on garbage."""
    try:
        return int(datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except (TypeError, ValueError):
        return None


# Longest-first so "Semifinal" never matches the "Final" entry.
_ROUND_WORDS = [
    ("round of 128", "R128"), ("round of 64", "R64"), ("round of 32", "R32"),
    ("round of 16", "R16"), ("quarterfinal", "QF"), ("semifinal", "SF"),
    ("round robin", "RR"), ("final", "F"),
]
# Longest first: "women singles".endswith("men singles") — women's variants must win.
_GENDER_TOKENS = ("women's singles", "womens singles", "women singles",
                  "men's singles", "mens singles", "men singles")


def parse_rules(rules_primary: object) -> dict:
    """Best-effort {'tournament', 'round'} from rules_primary. Tiebreaker only —
    unparsed values are None, never a hard key."""
    out: dict = {"tournament": None, "round": None}
    text = str(rules_primary or "")
    marker = " professional tennis match in the "
    if marker not in text:
        return out
    rest = text.split(marker, 1)[1]
    for stop in (" after a ball has been played", ",", "."):
        if stop in rest:
            rest = rest.split(stop, 1)[0]
    rest = rest.strip()
    if rest[:4].isdigit():                       # leading season year
        rest = rest[4:].strip()
    low = rest.lower()
    for word, code in _ROUND_WORDS:
        if low.endswith(word):
            out["round"] = code
            rest, low = rest[: -len(word)].strip(), low[: -len(word)].strip()
            break
    for tok in _GENDER_TOKENS:
        if low.endswith(tok):
            rest = rest[: -len(tok)].strip()
            break
    out["tournament"] = rest or None
    return out


def pair_events(markets: list[dict]) -> tuple[dict, dict]:
    """Group raw market objects into per-event pairs.

    Returns (events, skipped): events maps event_ticker -> {'a': mkt, 'b': mkt}
    with a/b ordered by name_key(yes_sub_title); anything that is not a clean
    two-market singles event lands in skipped with a reason (lesson 5 — never
    drop silently).
    """
    by_event: dict[str, list[dict]] = {}
    for m in markets:
        by_event.setdefault(m.get("event_ticker", ""), []).append(m)

    events: dict[str, dict] = {}
    skipped: dict[str, str] = {}
    for ev, ms in by_event.items():
        if not ev:
            continue
        # the same market can appear in both the settled and open sweeps
        ms = list({m.get("ticker"): m for m in ms}.values())
        if len(ms) != 2:
            skipped[ev] = f"{len(ms)} markets (expected 2)"
            continue
        names = [str(m.get("yes_sub_title") or "") for m in ms]
        if any("/" in n or not n.strip() for n in names):
            skipped[ev] = f"non-singles or blank names: {names}"
            continue
        if name_key(names[0]) == name_key(names[1]):
            skipped[ev] = f"duplicate player names: {names}"
            continue
        a, b = sorted(ms, key=lambda m: name_key(str(m.get("yes_sub_title"))))
        events[ev] = {"a": a, "b": b}
    return events, skipped


def _quote_at(candles: list[dict], cutoff_ts: int,
              window_start_ts: int | None = None) -> dict | None:
    """Last candle at/before cutoff carrying a two-sided book -> {'mid','spread','ts'}.

    A candle at/before window_start_ts is the include_latest_before_start synthetic
    carry — the last book state BEFORE the whole fetch window. When the anchor day
    postdates the match (a result-source date shift), that carry is the SETTLED book:
    mid pinned ~0.995 on the actual winner. A real morning line is never both
    window-stale and settled-extreme, so such a carry is rejected (caller degrades)."""
    best = None
    for c in candles:
        ts = c.get("end_period_ts")
        if not isinstance(ts, (int, float)) or ts > cutoff_ts:
            continue
        bid = _dollars((c.get("yes_bid") or {}).get("close_dollars"))
        ask = _dollars((c.get("yes_ask") or {}).get("close_dollars"))
        if bid is None or ask is None or ask <= 0:
            continue
        if best is None or ts > best["ts"]:
            best = {"mid": (bid + ask) / 2.0, "spread": ask - bid, "ts": int(ts)}
    if (best is not None and window_start_ts is not None
            and best["ts"] <= window_start_ts
            and not (1 - EXTREME_CARRY_MID < best["mid"] < EXTREME_CARRY_MID)):
        return None
    return best


def select_prematch_quotes(candles: list[dict], occurrence_ts: int) -> dict | None:
    """Primary (T-5) + sentinel (T-30) quotes from one market's candles; None if the
    primary cutoff has no two-sided candle (thin market, bad window, or a settled
    extreme-carry print — see _quote_at)."""
    window_start = occurrence_ts - CANDLE_LOOKBACK_S
    main = _quote_at(candles, occurrence_ts - LEAD_S, window_start_ts=window_start)
    if main is None:
        return None
    t30 = _quote_at(candles, occurrence_ts - LEAD_T30_S, window_start_ts=window_start)
    return {"mid": main["mid"], "spread": main["spread"], "ts": main["ts"],
            "mid_t30": t30["mid"] if t30 else None}


# ---------------------------------------------------------------------------
# Fetch stages
# ---------------------------------------------------------------------------
def fetch_markets(tour: str, status: str, frozen: set[str] | None = None,
                  since: str | None = None) -> list[dict] | None:
    """All markets of a series/status via cursor pagination; None on fetch failure.

    Early stops (incremental daily cost = 1-2 pages): a page whose every
    event_ticker is already frozen in the cache, or — when `since` is given —
    a page whose every market opened before it (backfill lower bound).
    """
    out: list[dict] = []
    cursor = None
    while True:
        params = {"series_ticker": SERIES[tour], "status": status, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        page = _get("/markets", params)
        if page is None:
            return None if not out else out          # partial haul still usable
        ms = page.get("markets", [])
        out.extend(ms)
        cursor = page.get("cursor")
        if not cursor or not ms:
            break
        if frozen and all(m.get("event_ticker") in frozen for m in ms):
            break
        if since and all(str(m.get("open_time", "")) < since for m in ms):
            break
    return out


def fetch_prematch_quotes(tour: str, ticker: str, occurrence_ts: int) -> dict | None:
    """Candle-derived pre-match quotes for one market (historical fallback on 404)."""
    params = {"start_ts": occurrence_ts - CANDLE_LOOKBACK_S, "end_ts": occurrence_ts,
              "period_interval": 1,
              # prepends a synthetic candle carrying the last book state before the
              # window, so a quiet overnight stretch still yields a quote
              "include_latest_before_start": "true"}
    resp = _get(f"/series/{SERIES[tour]}/markets/{ticker}/candlesticks", params)
    if resp is None:                                 # aged past the historical cutoff
        resp = _get(f"/historical/markets/{ticker}/candlesticks", params)
    if resp is None:
        return None
    return select_prematch_quotes(resp.get("candlesticks", []), occurrence_ts)


# ---------------------------------------------------------------------------
# Snapshot cache
# ---------------------------------------------------------------------------
def _market_meta(m: dict) -> dict:
    return {
        "ticker": m.get("ticker"),
        "name": str(m.get("yes_sub_title") or ""),
        "result": m.get("result") or "",
        "volume": _dollars(m.get("volume_fp")) or 0.0,
        "oi": _dollars(m.get("open_interest_fp")) or 0.0,
        "liquidity": _dollars(m.get("liquidity_dollars")) or 0.0,
        "yes_bid": _dollars(m.get("yes_bid_dollars")),
        "yes_ask": _dollars(m.get("yes_ask_dollars")),
    }


def load_snapshots(tour: str) -> dict:
    """Cache dict from the last run; a fresh skeleton when absent or corrupt."""
    p = kalshi_dir(tour) / "snapshots.json"
    try:
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(d.get("events"), dict):
                return d
    except Exception:  # noqa: BLE001 — corrupt cache: rebuild from the API
        pass
    return {"updated": None, "events": {}, "skipped": {}}


def _provisional_quote(ma: dict, mb: dict) -> dict:
    """Top-of-book mids from live market objects (pre-match, kind='quote')."""
    quote = {"kind": "quote", "ts": None, "mid_a": None, "mid_b": None,
             "mid_a_t30": None, "mid_b_t30": None, "spread_max": None}
    mids, spreads = [], []
    for m in (ma, mb):
        bid, ask = m.get("yes_bid"), m.get("yes_ask")
        if bid is None or ask is None or ask <= 0:
            return {**quote, "kind": "none"}
        mids.append((bid + ask) / 2.0)
        spreads.append(ask - bid)
    return {**quote, "mid_a": mids[0], "mid_b": mids[1], "spread_max": max(spreads)}


def refresh_snapshots(tour: str, backfill_since: str | None = None,
                      recent_days: int | None = None) -> dict:
    """Fetch settled + open markets, pair them, finalize pre-match prices from
    candles for events past their scheduled start. Returns the updated cache.

    `recent_days` caps the candlestick backfill to events that started within that
    many days — used on the hourly quick run so a cold snapshot cache does NOT
    trigger the full ~15-min historical backfill inline (the committed ledger CSVs
    already carry that history; the daily full run does the unbounded backfill).
    """
    snaps = load_snapshots(tour)
    events, skipped = snaps["events"], snaps.setdefault("skipped", {})
    frozen = {ev for ev, e in events.items()
              if (e.get("price") or {}).get("kind") in ("candle", "none")}

    raw: list[dict] = []
    for status in ("settled", "open"):
        got = fetch_markets(tour, status,
                            frozen=None if backfill_since else frozen,
                            since=backfill_since)
        if got is None:
            print(f"  kalshi/{tour}: {status} sweep failed — keeping cache")
        else:
            raw.extend(got)

    paired, skip_now = pair_events(raw)
    skipped.update(skip_now)

    now_ts = int(datetime.now(UTC).timestamp())
    n_new = n_frozen = 0
    for ev, pair in paired.items():
        ma, mb = _market_meta(pair["a"]), _market_meta(pair["b"])
        occurrence = pair["a"].get("occurrence_datetime") or pair["a"].get(
            "expected_expiration_time")
        entry = events.get(ev) or {}
        if ev not in events:
            n_new += 1
        prev_price = entry.get("price") or {}
        entry.update({
            "occurrence": occurrence,
            "status": pair["a"].get("status") or "",
            "a": ma, "b": mb,
            "rules": parse_rules(pair["a"].get("rules_primary")),
            "price": prev_price,
        })
        events[ev] = entry

        if prev_price.get("kind") in ("candle", "none"):
            continue                                  # frozen — never refetched
        occ_ts = _epoch(occurrence)
        if occ_ts is None:
            entry["price"] = {"kind": "none"}
            continue
        if occ_ts > now_ts:                           # upcoming: provisional top-of-book
            entry["price"] = _provisional_quote(ma, mb)
            continue
        if recent_days is not None and now_ts - occ_ts > recent_days * 86400:
            continue                                  # deep backfill deferred to the full
                                                      # run; committed ledger carries these
        qa = fetch_prematch_quotes(tour, ma["ticker"], occ_ts)
        qb = fetch_prematch_quotes(tour, mb["ticker"], occ_ts)
        if qa and qb:
            entry["price"] = {
                "kind": "candle",
                "ts": datetime.fromtimestamp(max(qa["ts"], qb["ts"]), UTC)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
                "mid_a": qa["mid"], "mid_b": qb["mid"],
                "mid_a_t30": qa["mid_t30"], "mid_b_t30": qb["mid_t30"],
                "spread_max": max(qa["spread"], qb["spread"]),
            }
            n_frozen += 1
        elif now_ts - occ_ts > GIVE_UP_DAYS * 86400:  # thin market, never quotable
            entry["price"] = {"kind": "none"}

    snaps["updated"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    d = kalshi_dir(tour)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "snapshots.json.tmp"
    tmp.write_text(json.dumps(snaps, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, d / "snapshots.json")
    print(f"  kalshi/{tour}: {len(events)} events cached "
          f"(+{n_new} new, {n_frozen} prices frozen, {len(skipped)} skipped)")
    return snaps


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="all", help="atp | wta | all")
    ap.add_argument("--backfill-since", default=None,
                    help="walk the full settled history back to this ISO date")
    args = ap.parse_args()
    for t in (TOURS if args.tour == "all" else [args.tour]):
        refresh_snapshots(t, backfill_since=args.backfill_since)
