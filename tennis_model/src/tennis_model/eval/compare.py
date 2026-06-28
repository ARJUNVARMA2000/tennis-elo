"""Benchmark the model against the betting market.

Joins the leakage-free walk-forward predictions (p_combiner per historical match) to
Tennis-Data closing odds and reports model vs market accuracy / log-loss / Brier on
the matched matches, plus the ROI of flat-staking the model's edge over the market.

Uses the walk-forward OOS predictions (not final ratings) so the comparison is honest:
every model probability was generated before its match.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.odds import load_odds, market_prob, normalize_name
from ..eval.metrics import score
from ..model.train import load_or_build_features, walk_forward


def _odds_cols(odds: pd.DataFrame):
    for tag in ("ps", "b365", "avg"):
        if f"odds_w_{tag}" in odds:
            return f"odds_w_{tag}", f"odds_l_{tag}"
    raise ValueError("no odds columns found")


def build_scorecard(start: int = 2012, end: int = 2025, edge_min: float = 0.05,
                    stake: float = 100.0) -> dict:
    feat = load_or_build_features()
    oos = walk_forward(feat, start_test=start, end_test=end)
    oos = oos.assign(w_key=oos["winner_name"].map(normalize_name),
                     l_key=oos["loser_name"].map(normalize_name),
                     d=oos["date"].dt.normalize())

    odds = load_odds(years=range(start, end + 1))
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
        "matched": int(len(merged)),
        "model": {k: round(v, 4) for k, v in score(model).items()},
        "market": {k: round(v, 4) for k, v in score(mkt).items()},
    }

    # Flat-stake the favourite side where the model disagrees enough with the market.
    edge = model - mkt
    bet_win = edge > edge_min                       # back the (actual) winner
    bet_lose = -edge > edge_min                     # back the (actual) loser
    pnl = (bet_win * (merged[ow].to_numpy() - 1.0) * stake
           - bet_lose * stake).sum() + (bet_lose * 0)  # winner side cashes, loser side loses stake
    # loser-side winners: when we backed the loser they lose -> -stake already; we never cash those
    n_bets = int(bet_win.sum() + bet_lose.sum())
    staked = n_bets * stake
    sc["betting"] = {
        "edgeMin": edge_min, "nBets": n_bets,
        "roi": round(float(pnl / staked), 4) if staked else None,
        "note": "flat stake on model edge vs market; illustrative, closing odds",
    }
    return sc


if __name__ == "__main__":
    import json
    try:
        print(json.dumps(build_scorecard(), indent=2))
    except FileNotFoundError as e:
        print(e)
