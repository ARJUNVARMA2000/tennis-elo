"""Benchmark the model against the betting market.

Joins the leakage-free walk-forward predictions (p_combiner per historical match) to
Tennis-Data closing odds and reports model vs market accuracy / log-loss / Brier on
the matched matches, plus the ROI of flat-staking the model's edge over the market.

The "market" line is coalesced PER ROW (Pinnacle when quoted, else Bet365, else the
book average) and the payload carries a per-year census of which book actually priced
the rows: tennis-data stopped carrying Pinnacle mid-January 2026, and a frame-wide
book pick silently froze the matched sample at the last Pinnacle row while the
scorecard still claimed a current window.

Uses the walk-forward OOS predictions (not final ratings) so the comparison is honest:
every model probability was generated before its match. `scorecard_from_oos` lets the
daily pipeline reuse the OOS frame it already computed (no second walk-forward).

Also fits an EVAL-ONLY market stacker sigma(a*logit(p_model) + b*logit(p_market) + c)
on the tune years and scores it on the validation years (betting track). Odds remain
a benchmark: nothing here feeds the product model, features, or exports.

Run:  PYTHONPATH=src python -m tennis_model.eval.compare [atp|wta]
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.odds import load_odds, market_prob, normalize_name
from ..eval.metrics import score
from ..model.train import load_or_build_features, walk_forward
from .tune import TUNE_YEARS, VAL_START

_ODDS_TAGS = ("ps", "b365", "avg")               # per-row preference order
_BOOK = {"ps": "Pinnacle", "b365": "Bet365", "avg": "book-average"}
RECENT_DAYS = 90                                  # era-matched slice for the scorecard


def _coalesce_odds(odds: pd.DataFrame) -> pd.DataFrame:
    """Collapse the per-book columns to one closing line per row (odds_w/odds_l),
    preferring Pinnacle, then Bet365, then the book average; `odds_src` records the
    book that priced each row. A row is kept as long as ANY book quoted it — a
    frame-wide book pick would drop every row the preferred book stopped covering."""
    if not any(f"odds_w_{t}" in odds for t in _ODDS_TAGS):
        raise ValueError("no odds columns found")
    out = odds.assign(odds_w=np.nan, odds_l=np.nan, odds_src=pd.NA)
    for tag in _ODDS_TAGS:
        w, l = f"odds_w_{tag}", f"odds_l_{tag}"
        if w not in odds or l not in odds:
            continue
        take = out["odds_w"].isna() & odds[w].notna() & odds[l].notna()
        out.loc[take, "odds_w"] = odds.loc[take, w]
        out.loc[take, "odds_l"] = odds.loc[take, l]
        out.loc[take, "odds_src"] = tag
    return out.dropna(subset=["odds_w", "odds_l"])


def _sources_block(merged: pd.DataFrame) -> dict:
    """Per-year census of the book behind each matched row, plus an honest label for
    the UI. The label collapses the common shapes ("all Pinnacle"; "Pinnacle until it
    left the feed, then X"); `byYear` is the ground truth."""
    by_year: dict[int, dict[str, int]] = {}
    for (y, t), n in merged.groupby(["year", "odds_src"], observed=True).size().items():
        by_year.setdefault(int(y), {})[str(t)] = int(n)
    maj = {y: max(c, key=c.get) for y, c in by_year.items()}
    books = set(maj.values())
    last_ps = max((y for y, b in maj.items() if b == "ps"), default=None)
    if books == {"ps"}:
        label = "Pinnacle closing odds"
    elif last_ps is not None and all(b != "ps" for y, b in maj.items() if y > last_ps):
        tail = {b for y, b in maj.items() if y > last_ps}
        names = "/".join(_BOOK[t] for t in _ODDS_TAGS if t in tail)
        label = f"Pinnacle close through {last_ps}, {names} close after"
    elif len(books) == 1:
        label = f"{_BOOK[books.pop()]} closing odds"
    else:
        label = "mixed-book closing odds"
    return {"preference": list(_ODDS_TAGS), "byYear": by_year, "label": label}


def _recent_block(merged: pd.DataFrame, model: np.ndarray, mkt: np.ndarray,
                  days: int = RECENT_DAYS, min_n: int = 30) -> dict | None:
    """Era-matched slice: paired model-vs-close on the trailing `days` of matched
    rows, so the scorecard can put the closing-line gap next to the (young) Kalshi
    window instead of only a multi-year average. kalshi_report convention:
    d = loss_market - loss_model per match, positive = model sharper."""
    last = merged["d"].max()
    m = (merged["d"] >= last - pd.Timedelta(days=days)).to_numpy()
    if int(m.sum()) < min_n:
        return None
    pm = np.clip(model[m], 1e-12, 1 - 1e-12)
    pk = np.clip(mkt[m], 1e-12, 1 - 1e-12)
    d = np.log(pm) - np.log(pk)                   # = (-log pk) - (-log pm)
    se = float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0
    return {"windowDays": days, "n": int(m.sum()),
            "from": str(merged.loc[m, "d"].min().date()), "to": str(last.date()),
            "model": {k: round(v, 4) for k, v in score(pm).items()},
            "market": {k: round(v, 4) for k, v in score(pk).items()},
            "dLl": round(float(d.mean()), 4), "dLlSe": round(se, 4)}


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def _flat_roi(p: np.ndarray, mkt: np.ndarray, odds_w: np.ndarray,
              edge_min: float = 0.05, stake: float = 100.0) -> dict:
    """Flat-stake the side where `p` disagrees with the market by > edge_min.
    Rows are winner-oriented: backing the actual winner cashes (odds_w - 1)*stake,
    backing the actual loser burns the stake."""
    edge = p - mkt
    bet_win, bet_lose = edge > edge_min, -edge > edge_min
    n = int(bet_win.sum() + bet_lose.sum())
    pnl = float((bet_win * (odds_w - 1.0) * stake - bet_lose * stake).sum())
    return {"nBets": n, "roi": round(pnl / (n * stake), 4) if n else None}


def _kelly_roi(p: np.ndarray, odds_w: np.ndarray, odds_l: np.ndarray,
               cap: float = 0.25, unit: float = 100.0) -> dict:
    """Per-match capped Kelly on any positive-EV side, fixed unit bankroll per match
    (no compounding — an ROI scorecard, not a bankroll simulation)."""
    f_w = np.clip((p * odds_w - 1.0) / (odds_w - 1.0), 0.0, cap) * unit
    f_l = np.clip(((1.0 - p) * odds_l - 1.0) / (odds_l - 1.0), 0.0, cap) * unit
    staked = float(f_w.sum() + f_l.sum())
    pnl = float((f_w * (odds_w - 1.0) - f_l).sum())
    return {"nBets": int(((f_w > 0) | (f_l > 0)).sum()),
            "roi": round(pnl / staked, 4) if staked else None}


def _stacker_block(merged: pd.DataFrame, model: np.ndarray, mkt: np.ndarray,
                   odds_w: np.ndarray, odds_l: np.ndarray,
                   edge_min: float, stake: float) -> dict | None:
    """Fit the eval-only stacker on TUNE_YEARS, score everything on VAL_START+.
    Returns None when either window is too thin to be meaningful."""
    yr = merged["year"].to_numpy()
    tm = (yr >= TUNE_YEARS[0]) & (yr <= TUNE_YEARS[1])
    vm = yr >= VAL_START
    if tm.sum() < 300 or vm.sum() < 100:
        return None
    from sklearn.linear_model import LogisticRegression
    flip = np.arange(int(tm.sum())) % 2 == 1          # break winner-orientation
    pm = np.where(flip, 1.0 - model[tm], model[tm])
    mk = np.where(flip, 1.0 - mkt[tm], mkt[tm])
    lr = LogisticRegression(C=1e4, solver="lbfgs")
    lr.fit(np.column_stack([_logit(pm), _logit(mk)]), np.where(flip, 0, 1))
    p_stack = lr.predict_proba(
        np.column_stack([_logit(model[vm]), _logit(mkt[vm])]))[:, 1]
    ow_v, ol_v, mk_v = odds_w[vm], odds_l[vm], mkt[vm]
    return {
        "fit": {"a_model": round(float(lr.coef_[0][0]), 3),
                "b_market": round(float(lr.coef_[0][1]), 3),
                "c": round(float(lr.intercept_[0]), 3),
                "tuneYears": list(TUNE_YEARS), "valStart": VAL_START,
                "nTune": int(tm.sum()), "nVal": int(vm.sum())},
        "val": {"model": {k: round(v, 4) for k, v in score(model[vm]).items()},
                "market": {k: round(v, 4) for k, v in score(mk_v).items()},
                "stack": {k: round(v, 4) for k, v in score(p_stack).items()}},
        "bettingVal": {
            "flatModel": _flat_roi(model[vm], mk_v, ow_v, edge_min, stake),
            "flatStack": _flat_roi(p_stack, mk_v, ow_v, edge_min, stake),
            "kellyModel": _kelly_roi(model[vm], ow_v, ol_v),
            "kellyStack": _kelly_roi(p_stack, ow_v, ol_v),
        },
    }


def scorecard_from_oos(tour: str, oos: pd.DataFrame, edge_min: float = 0.05,
                       stake: float = 100.0) -> dict:
    """Model-vs-market scorecard from an existing walk-forward OOS frame."""
    start, end = int(oos["year"].min()), int(oos["year"].max())
    oos = oos.assign(w_key=oos["winner_name"].map(normalize_name),
                     l_key=oos["loser_name"].map(normalize_name),
                     d=oos["date"].dt.normalize())

    odds = load_odds(tour, years=range(start, end + 1))
    odds = _coalesce_odds(odds.assign(d=odds["date"].dt.normalize()))

    # join on winner/loser keys within a few days (tournament dates can differ by source)
    merged = oos.merge(odds[["d", "w_key", "l_key", "odds_w", "odds_l", "odds_src"]],
                       on=["w_key", "l_key"], suffixes=("", "_o"))
    merged = merged[(merged["d"] - merged["d_o"]).abs() <= pd.Timedelta(days=4)]
    merged = merged.drop_duplicates(subset=["d", "w_key", "l_key"])
    if merged.empty:
        return {"matched": 0, "note": "no name/date matches — check odds files"}

    odds_w = merged["odds_w"].to_numpy(dtype=float)
    odds_l = merged["odds_l"].to_numpy(dtype=float)
    mkt = market_prob(odds_w, odds_l)                                 # P(winner)
    model = merged["p_combiner"].to_numpy()

    sc = {
        "tour": tour, "years": [start, end],
        "matched": int(len(merged)),
        # oosEnd vs lastMatchedDate is the health-gate staleness signal: matched odds
        # trailing the scored matches by months means a book left the feed again
        "oosEnd": str(oos["d"].max().date()),
        "lastMatchedDate": str(merged["d"].max().date()),
        "sources": _sources_block(merged),
        "model": {k: round(v, 4) for k, v in score(model).items()},
        "market": {k: round(v, 4) for k, v in score(mkt).items()},
    }
    recent = _recent_block(merged, model, mkt)
    if recent is not None:
        sc["recent"] = recent

    # Flat-stake the favourite side where the model disagrees enough with the market.
    edge = model - mkt
    bet_win = edge > edge_min                       # back the (actual) winner
    bet_lose = -edge > edge_min                     # back the (actual) loser
    pnl = (bet_win * (odds_w - 1.0) * stake
           - bet_lose * stake).sum()  # winner side cashes, loser side loses stake
    # loser-side winners: when we backed the loser they lose -> -stake already; we never cash those
    n_bets = int(bet_win.sum() + bet_lose.sum())
    staked = n_bets * stake
    sc["betting"] = {
        "edgeMin": edge_min, "nBets": n_bets,
        "roi": round(float(pnl / staked), 4) if staked else None,
        "note": "flat stake on model edge vs market; illustrative, closing odds",
    }

    # eval-only betting track: stacker fit on tune years, scored on validation years
    stack = _stacker_block(merged, model, mkt, odds_w, odds_l, edge_min, stake)
    if stack is not None:
        sc["stack"] = stack
    return sc


def build_scorecard(tour: str = "atp", start: int = 2012, end: int | None = None,
                    edge_min: float = 0.05, stake: float = 100.0) -> dict:
    feat = load_or_build_features(tour=tour)
    oos = walk_forward(feat, start_test=start, end_test=end)
    return scorecard_from_oos(tour, oos, edge_min=edge_min, stake=stake)


if __name__ == "__main__":
    import json
    import sys
    tour = sys.argv[1] if len(sys.argv) > 1 else "atp"
    try:
        print(json.dumps(build_scorecard(tour), indent=2))
    except FileNotFoundError as e:
        print(e)
