# Tuning results — 2026-07-06 (autoresearch round R1: FeatureParams + post-A5 re-sweeps)

First round run under the codified harness (`tasks/research/PROGRAM.md`; ledger ids
R1-*). Branch `research/2026-07-06`, base `5180300`; started 08:14 EDT, budget 8 h.
Protocol: tune window 2010–2019 / validation 2020+; Tier-1 component sweeps (n_bag=1)
screen candidates, the full bagged 2010–2026 arbiter (`_verdict`, now with the
per-year paired-d table) decides. Data frozen for the round (feature caches of
2026-07-05/06); no downloads.

## Sweeps run (Tier 1)

| study | trials | objective | baseline (tune) | best (tune) |
|---|---|---|---|---|
| atp_feat_fp1 | 20 | p_combiner LL, adopted XGB, walk 2010–19 | 0.56406 | 0.56238 |
| wta_feat_fp1 | 20 | " | 0.58663 | 0.58574 |
| wta_xgb_pa5 | 12 | p_combiner LL, full walk-forward 2010–19 | 0.58605 | 0.58552 |
| wta_feat_fp2 | 20 | p_combiner LL, anchored at post-fp1 incumbent | 0.58605 | 0.58587 |
| atp_xgb_pa5 | 12 | p_combiner LL, full walk-forward 2010–19, post-A5 frame | 0.56406 | 0.56314 |

## Adoption decisions

**ADOPTED — WTA FeatureParams (`fec0fb1`).** First entries in `FEAT_PARAM_OVERRIDES`:
`fatigue_window_days 14→33, layoff_days 120→360 (~flag off), peak_age 26.5→24,
winrate_window 10→23`, plus `form_days 90→65` (ELO_PARAM_OVERRIDES). Sweep `_fp1`
produced one val-positive passer (#13, unbagged d_val +0.00037±0.00046); the rounded
config under the full bagged arbiter: **d_tune +0.00084±0.00027, d_val
+0.00085±0.00038** — validation gain equals tune gain, per-year 13/17 positive
(max |d| 0.00271, no flapping), val years 5/7, acc 0.6829→0.6836, Brier
0.2018→0.2015. Reading: the WTA layoff flag was mildly harmful (360d threshold
disables it), fatigue integrates over a longer window, peak age is earlier than the
ATP-derived default, and form decays faster.

**DECLINED — ATP FeatureParams.** Sweep `_fp1` passed 5/5 on the component gate with
a coherent cluster (d_tune +0.00168±0.00032, best val +0.00044±0.00033 unbagged), but
the bagged arbiter on the plateau center (fatigue 18, layoff 38, peak 28.7, form 210,
wr 26) showed the fourth ATP instance of tune-overfit: **d_tune +0.00109±0.00026,
d_val −0.00006±0.00026** — zero validation carry, val years 3/7 positive, 2024 at
t=−2.5, val acc 0.6826→0.6818. Formal gate PASS declined on direction; ATP keeps the
shared defaults.

**REJECTED — WTA combiner re-sweep post-A5+fp1 (`_pa5`).** The adopted params
(anchor trial #0) are effectively unbeaten on the new feature distribution: the best
challenger (#7) is a formal passer with negative validation (d_tune +0.00052±0.00029,
d_val −0.00029±0.00038) — the decline-on-direction family; no Tier-2 spent. Useful
negative: the combiner optimum did not move across two feature-distribution shifts
(A5 ingestion, fp1 constants).

**REJECTED — WTA feat re-sweep around the new incumbent (`_fp2`, self-generated).**
0/5 configs pass: the freshly adopted FeatureParams are unbeaten in their own
neighborhood (best challenger d_tune +0.00017±0.00022 = noise, d_val −0.00062).
Confirms fp1 is a local optimum rather than a knife-edge. (An initial wall-clock
stop declared after this experiment was retracted — it rested on a mis-estimated
elapsed time of ~7 h when the true elapsed was ~1.5 h; the harness should read the
clock, not accumulate duration guesses. The round continued.)

**REJECTED — ATP combiner re-sweep post-A5 (`_pa5`, self-generated).** The
re-examination was justified (all prior ATP xgb rejections predate the A5 frame
shift), and the answer is now regime-independent: best d_tune +0.00092±0.00024 with
ALL top-5 configs val-negative (−0.00002…−0.00073) — the fourth instance of the
identical shape. ATP keeps the `_xgb()` defaults; this plateau needs no fifth visit
unless the frame changes again materially.

Round ended on stop condition 3: ideas backlog exhausted + two consecutive
self-generated rejections (R1-005, R1-006), at ~2 h elapsed of the 8 h budget.

## Final walk-forward (2010–2026, production stack, bagged)

45,762 ATP / 42,513 WTA matches. XGB combiner rows (from the R1-003 arbiter arms —
identical frames and settings to production):

| tour | config | acc | logloss | brier |
|---|---|---|---|---|
| ATP | before = after (nothing adopted) | 0.6958 | 0.5700 | **0.1947** |
| WTA | before | 0.6829 | 0.5878 | 0.2018 |
| WTA | **after (adopted FeatureParams)** | **0.6836** | **0.5869** | **0.2015** |

Anchors: bookmaker ≈0.690 acc / 0.196 Brier. ATP holds its position ahead of the
anchor on both axes; the WTA adoption closes its Brier gap by ~5% (0.2018→0.2015 vs
0.196). Production rebuild (`--tour all --backtest`) verified at round end — see
todo.md review for the deployed-window (2016+) numbers.

## Method notes

- The per-year paired-d table (added to `_verdict` this round) separated the two
  fp1 arbiter outcomes cleanly: ATP's formal pass showed tune-years-only gains;
  WTA's showed a uniform lift. The tripwire is doing its job.
- The tuning feature cache (`_features_{tour}*.pkl`) is schema/regime-keyed but NOT
  param-keyed: after adopting a param that changes feature values, invalidate it or
  subsequent xgb sweeps tune against stale features. (Production unaffected — the
  pipeline builds frames fresh.) Cache was invalidated before `_pa5`.
- Baseline reproduction: the R1-003-atp base arm bit-matched the saved A5 arbiter
  pickle (full LL 0.56996) — walk determinism holds across sessions.
