"""Benchmark the model against the betting market.

Joins the leakage-free walk-forward predictions (p_combiner per historical match) to
Tennis-Data closing odds and reports model vs market accuracy / log-loss / Brier on
the matched matches, plus the ROI of flat-staking the model's edge over the market.

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


def _odds_cols(odds: pd.DataFrame):
    for tag in ("ps", "b365", "avg"):
        if f"odds_w_{tag}" in odds:
            return f"odds_w_{tag}", f"odds_l_{tag}"
    raise ValueError("no odds columns found")


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
    ow, ol = _odds_cols(odds)
    odds = odds.assign(d=odds["date"].dt.normalize()).dropna(subset=[ow, ol])

    # join on winner/loser keys within a few days (tournament dates can differ by source)
    merged = oos.merge(odds[["d", "w_key", "l_key", ow, ol]], on=["w_key", "l_key"],
                       suffixes=("", "_o"))
    merged = merged[(merged["d"] - merged["d_o"]).abs() <= pd.Timedelta(days=4)]
    merged = merged.drop_duplicates(subset=["d", "w_key", "l_key"])
    if merged.empty:
        return {"matched": 0, "note": "no name/date matches — check odds files"}

    mkt = market_prob(merged[ow].to_numpy(), merged[ol].to_numpy())   # P(winner)
    model = merged["p_combiner"].to_numpy()

    sc = {
        "tour": tour, "years": [start, end],
        "matched": int(len(merged)),
        "model": {k: round(v, 4) for k, v in score(model).items()},
        "market": {k: round(v, 4) for k, v in score(mkt).items()},
    }

    # Flat-stake the favourite side where the model disagrees enough with the market.
    edge = model - mkt
    bet_win = edge > edge_min                       # back the (actual) winner
    bet_lose = -edge > edge_min                     # back the (actual) loser
    pnl = (bet_win * (merged[ow].to_numpy() - 1.0) * stake
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
    stack = _stacker_block(merged, model, mkt, merged[ow].to_numpy(),
                           merged[ol].to_numpy(), edge_min, stake)
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
