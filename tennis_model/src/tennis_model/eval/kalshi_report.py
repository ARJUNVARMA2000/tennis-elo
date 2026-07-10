"""Model-vs-Kalshi segmented scorecard from the evaluation ledger.

Reads data/kalshi_ledger/{tour}.csv and writes
  data/kalshi_ledger/report.md          committed daily — the human scoreboard
  data/output/{tour}/kalshi.json        mirrored to the web dir (future dashboard)

Scored set: matched, completed (no walkovers/retirements — consistent with every
other scorecard in the repo), candle-frozen pre-match price, both probabilities
present, spread_max <= 0.10. Paired stats follow the tune.py arbiter convention:
d_i = loss_kalshi_i - loss_model_i, d ± SE with SE = std(ddof=1)/sqrt(n) —
POSITIVE d = model better than Kalshi.

Coverage caveat baked into the report: Kalshi lists a favorite-heavy subset of
matches, so these numbers are not comparable to the closing-line market.json scorecard;
and with months of data, narrow segments are noise — every row carries n and SE,
rows under N_FLAG are flagged.

Run:  PYTHONPATH=src python -m tennis_model.eval.kalshi_report
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from ..config import KALSHI_LEDGER_DIR, TOURS, output_dir
from .metrics import EPS, calibration_table, score

MAX_SPREAD = 0.10        # wider than 10c pre-match = too thin to call a market price
N_FLAG = 50              # segment rows below this n are flagged as small-sample
DISAGREE_BIG = 0.10      # "big disagreement" threshold for the head-to-head cut

_NUM = ["mid_a", "mid_b", "p_kalshi", "p_kalshi_t30", "spread_max", "volume_total",
        "rank_a", "rank_b", "p_model", "a_won"]


# ---------------------------------------------------------------------------
# Loading / scoring primitives
# ---------------------------------------------------------------------------
def load_ledger(tour: str) -> pd.DataFrame:
    p = KALSHI_LEDGER_DIR / f"{tour}.csv"
    if not p.exists():
        return pd.DataFrame(columns=["tour", "match_status", "result_type",
                                     "price_kind", *_NUM])
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    for c in _NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def scored_set(df: pd.DataFrame, include_retired: bool = False) -> pd.DataFrame:
    ok_result = ["completed", "retired"] if include_retired else ["completed"]
    m = ((df["match_status"] == "matched") & df["result_type"].isin(ok_result)
         & (df["price_kind"] == "candle") & df["p_model"].notna()
         & df["p_kalshi"].notna() & (df["spread_max"] <= MAX_SPREAD))
    out = df[m].copy()
    won = out["a_won"] == 1
    out["p_model_w"] = np.where(won, out["p_model"], 1.0 - out["p_model"])
    out["p_kalshi_w"] = np.where(won, out["p_kalshi"], 1.0 - out["p_kalshi"])
    return out


def paired_block(p_model_w: np.ndarray, p_kalshi_w: np.ndarray) -> dict:
    """Absolute levels + paired d ± SE for one row set (winner-oriented vectors)."""
    pm = np.clip(np.asarray(p_model_w, dtype=float), EPS, 1 - EPS)
    pk = np.clip(np.asarray(p_kalshi_w, dtype=float), EPS, 1 - EPS)
    n = len(pm)
    if n == 0:
        return {"n": 0}
    d_ll = -np.log(pk) - (-np.log(pm))
    d_br = (1 - pk) ** 2 - (1 - pm) ** 2
    def _se(d):
        return float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0
    out = {"n": n, "model": score(pm), "kalshi": score(pk),
           "d_ll": float(d_ll.mean()), "d_ll_se": _se(d_ll),
           "d_brier": float(d_br.mean()), "d_brier_se": _se(d_br),
           "d_acc": float(np.mean(pm > 0.5) - np.mean(pk > 0.5))}
    out["t"] = out["d_ll"] / out["d_ll_se"] if out["d_ll_se"] > 0 else 0.0
    return out


# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------
def _round_group(r: str) -> str:
    return {"R128": "early (R128-R64)", "R64": "early (R128-R64)",
            "R32": "mid (R32-R16)", "R16": "mid (R32-R16)",
            "QF": "late (QF-F)", "SF": "late (QF-F)", "F": "late (QF-F)",
            "RR": "round robin"}.get(str(r), "other/qual")


def segment_masks(s: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    """(label, boolean mask) per segment cut, computed on a scored-set frame."""
    best = s[["rank_a", "rank_b"]].min(axis=1)
    worst = s[["rank_a", "rank_b"]].max(axis=1)   # NaN if either rank missing
    fav = np.maximum(s["p_kalshi"], 1.0 - s["p_kalshi"])
    dis = (s["p_model"] - s["p_kalshi"]).abs()
    segs: list[tuple[str, pd.Series]] = [
        ("pred_source: live", s["pred_source"] == "live"),
        ("pred_source: backtest", s["pred_source"] == "backtest"),
        ("top-20 involved", best <= 20),
        ("no top-20 player", best > 20),
        ("both inside top-50", worst <= 50),
        ("someone outside top-50", worst > 50),
        ("rank unknown", best.isna()),
    ]
    segs += [(f"best rank {lab}", (best >= lo) & (best <= hi))
             for lab, lo, hi in [("1-10", 1, 10), ("11-20", 11, 20), ("21-50", 21, 50),
                                 ("51-100", 51, 100), ("100+", 101, 9999)]]
    segs += [(f"kalshi favorite {lo:.1f}-{hi:.1f}", (fav >= lo) & (fav < hi))
             for lo, hi in [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]]
    segs += [(f"surface: {v}", s["surface"] == v) for v in ("Hard", "Clay", "Grass")]
    segs += [(f"tier: {v}", s["tier"] == v)
             for v in sorted(x for x in s["tier"].unique() if x)]
    rg = s["round"].map(_round_group)
    segs += [(f"round {v}", rg == v) for v in sorted(rg.unique())]
    segs += [(f"month {v}", s["match_date"].str[:7] == v)
             for v in sorted(s["match_date"].str[:7].unique())]
    segs += [("agree (<0.05)", dis < 0.05),
             ("mild disagree (0.05-0.10)", (dis >= 0.05) & (dis < DISAGREE_BIG)),
             (f"big disagree (>={DISAGREE_BIG})", dis >= DISAGREE_BIG)]
    segs += [(f"tour: {v}", s["tour"] == v) for v in sorted(s["tour"].unique())]
    return segs


def segment_table(s: pd.DataFrame) -> list[dict]:
    rows = []
    for label, mask in segment_masks(s):
        sub = s[mask.fillna(False).astype(bool)]
        if len(sub) == 0:
            continue
        blk = paired_block(sub["p_model_w"].to_numpy(), sub["p_kalshi_w"].to_numpy())
        rows.append({"segment": label, **blk})
    return rows


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------
def _coverage(df: pd.DataFrame) -> dict:
    return {
        "events": int(len(df)),
        "matched": int((df["match_status"] == "matched").sum()),
        "pending": int((df["match_status"] == "pending").sum()),
        "unmatched": int((df["match_status"] == "unmatched").sum()),
        "cancelled": int((df["match_status"] == "cancelled").sum()),
        "ambiguous": int((df["match_status"] == "ambiguous").sum()),
        "walkovers": int((df["result_type"] == "walkover").sum()),
        "retirements": int((df["result_type"] == "retired").sum()),
        "no_price": int((df["price_kind"] != "candle").sum()),
        "date_range": [df["match_date"].min() or None, df["match_date"].max() or None]
        if len(df) else [None, None],
    }


def _qa(df: pd.DataFrame, s: pd.DataFrame) -> dict:
    both = s[s["p_kalshi_t30"].notna()]
    dv = (both["p_kalshi"] - both["p_kalshi_t30"]).abs()
    unmatched = df[df["match_status"] == "unmatched"]
    # qualifying markets can be unmatchable for structural reasons (no WTA quali
    # results source) — keep them out of the alias-hunting name list. NB: Kalshi
    # labels slam qualifying by draw size ("Round of 128" a week before the main
    # draw), so the event breakdown below is the signal for structural clusters.
    is_quali = unmatched["event"].str.lower().str.contains("qualification", na=False)
    n_quali = int(is_quali.sum())
    unmatched = unmatched[~is_quali]
    by_event = unmatched.groupby("event").size().sort_values(ascending=False)
    names = sorted(set(unmatched["player_a"]) | set(unmatched["player_b"]))
    disagree = (df["kalshi_result_a"].isin(["yes", "no"])
                & df["a_won"].notna() & (df["result_type"] == "completed")
                & ((df["kalshi_result_a"] == "yes") != (df["a_won"] == 1)))
    return {
        "t30_n": int(len(both)),
        "t30_mean_abs": float(dv.mean()) if len(both) else None,
        "t30_p95_abs": float(dv.quantile(0.95)) if len(both) else None,
        "t30_over_05": int((dv > 0.05).sum()),
        "unmatched_quali": n_quali,
        "unmatched_by_event": {str(k): int(v) for k, v in by_event.head(8).items()},
        "unmatched_names": names[:40],
        "settlement_disagreements": int(disagree.sum()),
    }


def _fmt_d(v: float, se: float) -> str:
    return f"{v:+.4f} ±{se:.4f}"


def _seg_md(rows: list[dict]) -> list[str]:
    out = ["| segment | n | d_ll ±SE | d_brier ±SE | t | acc model | acc kalshi | |",
           "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        flag = " ⚠ small n" if r["n"] < N_FLAG else ""
        out.append(f"| {r['segment']} | {r['n']} | {_fmt_d(r['d_ll'], r['d_ll_se'])} "
                   f"| {_fmt_d(r['d_brier'], r['d_brier_se'])} | {r['t']:+.1f} "
                   f"| {r['model']['acc']:.3f} | {r['kalshi']['acc']:.3f} |{flag} |")
    return out


def _calibration_pair(s: pd.DataFrame) -> dict:
    """A-oriented reliability tables (predicted vs realized) for model and market
    on the scored set — outcome-independent, so no randomization needed."""
    lab = (s["a_won"] == 1).to_numpy().astype(float)
    return {"model": calibration_table(s["p_model"].to_numpy(), lab).to_dict("records"),
            "kalshi": calibration_table(s["p_kalshi"].to_numpy(), lab).to_dict("records")}


def _receipts(s: pd.DataFrame, k: int = 6) -> dict:
    """Matches where model and market landed on opposite sides of 0.5: best calls
    (model right, market wrong) and worst misses (vice-versa), each probability
    oriented to the eventual winner; plus the big-disagreement head-to-head."""
    won = s["a_won"] == 1
    t = s.assign(pm_w=np.where(won, s["p_model"], 1.0 - s["p_model"]),
                 pk_w=np.where(won, s["p_kalshi"], 1.0 - s["p_kalshi"]))

    def rows(sub: pd.DataFrame) -> list[dict]:
        return [{
            "date": r.match_date, "tour": r.tour, "event": r.event, "round": r.round,
            "winner": r.winner,
            "loser": r.player_b if r.winner == r.player_a else r.player_a,
            "pModel": round(float(r.pm_w), 3), "pKalshi": round(float(r.pk_w), 3),
            "predSource": r.pred_source,
        } for r in sub.itertuples(index=False)]

    best = t[(t.pm_w > 0.5) & (t.pk_w < 0.5)].sort_values("pk_w")
    worst = t[(t.pm_w < 0.5) & (t.pk_w > 0.5)].sort_values("pm_w")
    big = t[(t["p_model"] - t["p_kalshi"]).abs() >= DISAGREE_BIG]
    return {
        "bestCalls": rows(best.head(k)),
        "worstMisses": rows(worst.head(k)),
        "disagree": {"n": int(len(big)), "modelRight": int((big.pm_w > big.pk_w).sum())},
    }


def build_report(tours=TOURS) -> dict:
    """Write report.md + per-tour kalshi.json; returns the pooled summary dict."""
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    ledgers = {t: load_ledger(t) for t in tours}
    pooled = pd.concat(ledgers.values(), ignore_index=True) if ledgers else pd.DataFrame()
    s_all = scored_set(pooled) if len(pooled) else pooled
    md = [
        "# Model vs Kalshi — match-by-match scorecard", "",
        f"_Generated {now}. Positive d = model better than Kalshi (paired per-match; "
        f"SE = std/√n, tune.py convention). Kalshi price = de-vigged bid/ask mid at "
        f"08:00 UTC on match day (morning-of line — always pre-match; Kalshi's own "
        f"start timestamps mutate on settled markets and cannot be trusted), from "
        f"1-min candlesticks; markets with spread > {MAX_SPREAD:.2f} excluded. Do "
        "not compare these numbers to the closing-line scorecard "
        "(market.json): different price time, different match mix._", "",
        "## Coverage", "",
        "| tour | events | matched | pending | unmatched | cancelled | ambiguous "
        "| walkovers | retirements | no price | range |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t, df in ledgers.items():
        c = _coverage(df)
        md.append(f"| {t} | {c['events']} | {c['matched']} | {c['pending']} "
                  f"| {c['unmatched']} | {c['cancelled']} | {c['ambiguous']} "
                  f"| {c['walkovers']} | {c['retirements']} | {c['no_price']} "
                  f"| {c['date_range'][0]}..{c['date_range'][1]} |")

    md += ["", "## Headline (scored set)", "",
           "| slice | n | model LL | kalshi LL | d_ll ±SE | d_brier ±SE "
           "| acc model | acc kalshi |", "|---|---|---|---|---|---|---|---|"]
    headline: dict = {}
    slices = [("pooled", s_all)] + [(t, scored_set(df)) for t, df in ledgers.items()]
    slices += [(f"pooled/{src}", s_all[s_all["pred_source"] == src])
               for src in ("live", "backtest")] if len(s_all) else []
    for label, s in slices:
        blk = paired_block(s["p_model_w"].to_numpy(), s["p_kalshi_w"].to_numpy()) \
            if len(s) else {"n": 0}
        headline[label] = blk
        if blk["n"]:
            md.append(f"| {label} | {blk['n']} | {blk['model']['logloss']:.4f} "
                      f"| {blk['kalshi']['logloss']:.4f} | {_fmt_d(blk['d_ll'], blk['d_ll_se'])} "
                      f"| {_fmt_d(blk['d_brier'], blk['d_brier_se'])} "
                      f"| {blk['model']['acc']:.3f} | {blk['kalshi']['acc']:.3f} |")
        else:
            md.append(f"| {label} | 0 | | | | | | |")

    segs = segment_table(s_all) if len(s_all) else []
    md += ["", "## Segments (pooled)", ""] + _seg_md(segs)

    # Big-disagreement head-to-head: who was closer to the actual winner?
    if len(s_all):
        big = s_all[(s_all["p_model"] - s_all["p_kalshi"]).abs() >= DISAGREE_BIG]
        model_closer = int((big["p_model_w"] > big["p_kalshi_w"]).sum())
        md += ["", f"When they disagree by >= {DISAGREE_BIG}: model closer to the "
               f"outcome in **{model_closer}/{len(big)}** matches."]

    if len(s_all):
        md += ["", "## Calibration (A = alphabetical player, outcome-independent)", ""]
        for who, col in [("Model", "p_model"), ("Kalshi", "p_kalshi")]:
            tbl = calibration_table(s_all[col].to_numpy(),
                                    (s_all["a_won"] == 1).to_numpy().astype(float))
            md += [f"### {who}", "", "| bin | n | pred | actual |", "|---|---|---|---|"]
            md += [f"| {r['bin']} | {r['n']} | {r['pred']:.3f} | {r['actual']:.3f} |"
                   for r in tbl.to_dict("records")]
            md.append("")

    ranked = sorted([r for r in segs if r["n"] >= 10], key=lambda r: r["t"], reverse=True)
    md += ["## Where we win / where we lose (by t, n >= 10)", ""]
    md += _seg_md(ranked[:8]) + ["", "…worst:", ""] + _seg_md(ranked[-8:])

    qa = _qa(pooled, s_all) if len(pooled) else {}
    ret = {"n": 0}
    if len(pooled):
        s_ret = scored_set(pooled, include_retired=True)
        if len(s_ret):
            ret = paired_block(s_ret["p_model_w"].to_numpy(), s_ret["p_kalshi_w"].to_numpy())
    md += ["", "## QA / leak sentinel", ""]
    if qa:
        md += [f"- T-5 vs T-30 price divergence: n={qa['t30_n']}, "
               f"mean |Δ|={qa['t30_mean_abs']:.4f}, p95={qa['t30_p95_abs']:.4f}, "
               f">0.05 in {qa['t30_over_05']} rows (systemic divergence ⇒ early starts "
               "leaking in-play info ⇒ flip LEAD_MIN to 30)."
               if qa["t30_n"] else "- T-5 vs T-30 divergence: no rows with both quotes.",
               f"- Our winner vs Kalshi settlement disagreements: "
               f"{qa['settlement_disagreements']} (join bugs surface here).",
               f"- Sensitivity incl. retirements: n={ret['n']}"
               + (f", d_ll {_fmt_d(ret['d_ll'], ret['d_ll_se'])}" if ret["n"] else ""),
               f"- Unmatched qualifying markets: {qa['unmatched_quali']} "
               "(structural — no qualifying results source for that tour/era).",
               "- Unmatched by event (clusters = structural gaps, singletons = "
               f"alias candidates): {qa['unmatched_by_event'] or 'none'}",
               f"- Unmatched Kalshi names, main draw ({len(qa['unmatched_names'])}): "
               + (", ".join(qa["unmatched_names"]) or "none")]

    KALSHI_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    (KALSHI_LEDGER_DIR / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    for t, df in ledgers.items():
        s = scored_set(df)
        payload = {
            "tour": t, "lastUpdated": now, "coverage": _coverage(df),
            "headline": paired_block(s["p_model_w"].to_numpy(),
                                     s["p_kalshi_w"].to_numpy()) if len(s) else {"n": 0},
            "segments": segment_table(s) if len(s) else [],
            "calibration": _calibration_pair(s) if len(s) else {"model": [], "kalshi": []},
            **(_receipts(s) if len(s)
               else {"bestCalls": [], "worstMisses": [], "disagree": {"n": 0, "modelRight": 0}}),
        }
        d = output_dir(t)
        d.mkdir(parents=True, exist_ok=True)
        (d / "kalshi.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"  kalshi-report: {headline.get('pooled', {}).get('n', 0)} scored matches "
          f"-> {KALSHI_LEDGER_DIR / 'report.md'}")
    return {"headline": headline, "segments": segs, "qa": qa}


if __name__ == "__main__":
    build_report()
