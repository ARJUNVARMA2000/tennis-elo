# Core round — 2026-07-02 (P0/P1/E1/E2 + eval-side market stacker)

Continues [tuning-results-2026-07-02.md](tuning-results-2026-07-02.md). Same protocol:
Optuna TPE, tune 2010–19 / validate 2020+, paired d±SE gate (`d_tune > 0 AND
d_val > −1·SE`), full walk-forward 2010–2026 arbiter under the pinned stack
(pandas 3.0.3 / sklearn 1.9.0 / xgboost 3.3.0 — verified locally before sweeping).

## Question settled up front: "detailed modelling, maybe ditching Elo?"

Assessed by two independent code-grounded reviews before this round. **The production
model already IS XGBoost** — Elo and the Markov point model are its feature generators.
Documented SKIPs (so this doesn't get re-litigated):

- **End-to-end single model / player-embedding NNs**: Elo is the compressed sufficient
  statistic of the opponent graph (median pair meets <2×; trees can't propagate
  strength through the graph). Embeddings at ~45k matches/tour are well-estimated only
  for ~100 stars. Literature (Kovalchik 2016; Sipko & Knottenbelt) finds nothing
  beating dynamic-K Elo + market from public data. Expected ≤ 0 here.
- **Glicko-2**: rating deviation is already proxied (exp_diff, log_min_matches,
  layoff flags) and the tuned inactivity K-boost mimics RD growth. Kovalchik found
  dynamic-K Elo beats Glicko variants in tennis outright.
- **WHR / Bradley-Terry+covariates / set-level Elo**: leakage-free WHR ≈ dynamic-K
  Elo; BT+covariates is structurally what XGB-on-Elo-diffs already is; the tuned MOV
  multiplier already extracts the margin signal.
- **Set-level dataset widening / margin auxiliary targets**: sets within a match are
  heavily correlated (~2.5× rows ≈ 1.3–1.6× effective); expected margin is a
  near-monotone transform of win prob.
- **Odds as a model feature**: deliberate standing policy (data/odds.py, README).
  Breaks inference parity (the draw simulator prices hypothetical matchups that have
  no closing odds) and makes the market benchmark circular. Betting is instead served
  by the eval-side stacker below.

Calibration anchor for this round's expectations: the last successful feature round
bought 0.0001–0.0003 Brier; the Elo re-tune bought 0.0007. ATP headroom to the
bookmaker is ~0.0024 Brier total.

## Work landed

- **P1 — FeatureParams refactor + parity-trap fix.** `predict.py` imported
  LAYOFF_DAYS/PEAK_AGE at module load (import-bound copies, per-tour tuning
  impossible, pickles silent about their constants). Now: frozen `FeatureParams`
  (fatigue_window_days / layoff_days / peak_age / winrate_window / ret_window_days)
  in config + `feat_params_for(tour)` + `FEAT_PARAM_OVERRIDES`; the predictor carries
  its `fp` (old-pickle tolerant); form window moved onto `EloParams.form_days`.
  **Bit-identical gate passed both tours** (ATP exactly; WTA values identical, dtype
  metadata differs because its cache predates the pandas-3 pin — normalizes at next
  rebuild). New tune group `feat` scores candidates through the FULL walk-forward
  under the adopted combiner, so the component-vs-arbiter gap is absent by
  construction.
- **E1 — box-score decomposition features** (6 new ANTISYM, 41 → 47): bp_clutch
  (bp-save rate vs own expected level — the pressure signal the iid Markov chain
  ignores), ace_rate, df_rate, first_in (shrunk deviations from league rates, own
  denominators per stat), minutes14 (minutes-based workload, games×league-pace fill),
  ret_recent (retired-mid-match ≤60d injury proxy). Smoke on real ATP data: Isner
  ace +12.8pp, Nadal ace −2.5pp, Medvedev df +1.3pp — the rates separate archetypes.
  predict.py mirrors all six (key-set parity test enforces).
- **E2 — cross-surface transfer Elo**: `EloParams.xsurf` — a result on surface s also
  moves the other surface ratings by xsurf × the surface-s update. 0 (default) is
  bit-identical to the incumbent walk (unit-tested).
- **P0 — WTA combiner min_child_weight bound 50 → 400** (sat at the old bound) +
  TPE anchored at the incumbent config via enqueue_trial.
- **S1 — eval-only market stacker** in `eval/compare.py`:
  σ(a·logit(p_model) + b·logit(p_market) + c), fit on tune years, scored on
  validation years only; flat-stake + capped-Kelly ROI vs closing odds. Product
  model/exports untouched — the odds-as-benchmark policy stands.

## Sweeps / gates (results fill in as they land)

| item | study/gate | status |
|---|---|---|
| P0 WTA mcw extension | `wta_xgb_mcw` 200 trials + --validate | **ADOPTED** |
| P1 feat sweep ATP | `atp_feat` 150 trials + --validate | **REJECTED (tune-overfit, 5/5)** |
| P1 feat sweep WTA | `wta_feat` 150 trials + --validate | **REJECTED (directional overfit)** |
| E1 box-score features | match-paired walk-forward A/B, both tours | **REJECTED (block)** |
| E1b workload pair only | minutes14+ret_recent subset A/B | **REJECTED — E1 closed** |
| E2 xsurf WTA | `wta_elo_xsurf` 400 trials + gate + arbiter | **ADOPTED** |
| E2 xsurf ATP | `atp_elo_xsurf` + gate + arbiter | **ADOPTED** |

**E2 WTA component gate — all five top configs PASS decisively** (baseline tune
0.60958 / val 0.61588): best d_tune +0.00270±0.00055, d_val +0.00178–0.00214
(~3 SE). A coherent NEW Elo geometry, not a ridge wobble: xsurf 0.15–0.19 (every
result now feeds all surface ratings), surface_blend 0.375→~0.62 (surface ratings
are better-informed so the blend can trust them), k_scale ~100→~320 with
k_offset 5→1.5 / k_shape 0.2→0.37, surface_k_scale 130→45, retirements
down-weighted (ret_k_mult ~0.72 — previously measured irrelevant WITHOUT
transfer), tier anchors (0.93,0.68)→(~1.22,~0.81). Component gains this size
(10× the ATP-SR rejection's) go to the full-pipeline arbiter: plateau center
k320/1.5/0.37, sk45/0.40, blend 0.62, mov 0.22/1.65, ret 0.72, inact 86/0.16,
xsurf 0.17, anchors (1.22, 0.81).

**ADOPTED — E2 WTA full-pipeline arbiter** (both sides rebuilt from one shared
data load — raw data drifted +16 matches mid-evening, so the cached-frame pairing
was replaced by a same-df rebuild): acc 0.6822→**0.6841**, LL 0.5892→**0.5889**,
Brier 0.2024→**0.2023**; d_tune +0.00060±0.00045, d_val −0.00032±0.00059 (inside
1 SE), d_full +0.00026±0.00036. With the decisive component gate, adopted into
`ELO_PARAM_OVERRIDES["wta"]` + `TIER_ANCHORS["wta"]=(1.22, 0.81)`. WTA acc is now
~0.684 — within 0.006 of the bookmaker's 0.690, from 0.670 two days ago.
| S1 stacker numbers | compare.py on real OOS, both tours | **DONE — ATP stack beats market** |

**S1 — eval-only market stacker (validation years 2020+, matched odds rows).**
ATP (10,042 val rows): model 0.2065 / market 0.2016 / **stack 0.1996 Brier** —
the model's orthogonal signal (a_model 0.33, b_market 0.75) IMPROVES on closing
odds when blended: the Kovalchik ensemble result, achieved. WTA (9,822): model
0.2033 / market 0.1984 / stack 0.2004 — between the inputs, no market beat.
Paper betting ROI vs closing odds (illustrative only): ATP flat-stack +19.4%
(629 bets) / Kelly-stack +11.0%; model-alone +1.1…+3.1% both tours. CAVEATS:
closing-odds fills, no limits/slippage, and the stack-disagreement bets
concentrate in odd corners — audit those 629 ATP bets for odds-join/RET
artifacts before believing the number (follow-up). Product path untouched.

**P0 gate — all five top `wta_xgb_mcw` configs PASS on both windows** (baseline
tune 0.58791 / val 0.59318): best-val #129 d_tune +0.00066±0.00024,
d_val +0.00108±0.00030. The search moved to a NEW plateau, not just past the old
bound: depth 7, mcw 63–89 (old bound 50 was mildly binding; the new 400 bound is
not), subsample/colsample ≈0.75/0.75, reg_alpha 2.4–7.8 (incumbent 0.002!),
reg_lambda ~0.1, lr ~0.03. TPE anchored at the incumbent (trial 0 = baseline)
makes the comparison honest. Plateau center (geomeans on log params): lr 0.03,
depth 7, mcw 70, subsample 0.77, colsample 0.75, alpha 5.0, lambda 0.1, gamma 5e-4,
cap 2000.

**ADOPTED — full 2010–2026 arbiter vs the prior adopted config:**
acc 0.6811→**0.6821**, LL 0.5898→**0.5892**, Brier 0.2027→**0.2024**;
d_tune +0.00034±0.00024, d_val **+0.00100±0.00036** (~2.8 SE), d_full
+0.00058±0.00020. Now in `config.py XGB_PARAM_OVERRIDES["wta"]`. WTA's gap to the
bookmaker Brier (~0.196) narrows 0.2027→0.2024. Note for later gates this round:
the WTA "before" is now 0.6821/0.5892/0.2024, and the WTA feat sweep searched
under the pre-adoption combiner (its gate re-scores under the adopted one — same
precedent as searching under unpinned xgboost).

**ADOPTED — E2 ATP** (`atp_elo_xsurf`, 5/5 component gate at 3–4 SE: d_tune
+0.0017, d_val +0.0011–0.0024; arbiter both windows positive: d_tune
+0.00018±0.00033, d_val +0.00041±0.00040): acc 0.6878→**0.6883**, LL
0.5787→**0.5785**, Brier 0.1984→**0.1983**. Plateau center k145/5/0.21,
sk52/0.33, blend 0.63, mov 0.22/2.0, inact 400/0.44, bo5 1.28 (re-converged
independently — robust), xsurf 0.27, anchors (0.91, 0.89) — ATP tier weighting
flattens almost completely under transfer. Both tours now carry the
cross-surface geometry.

**REJECTED — ATP feat sweep (5/5 tune-overfit).** Every top config improved tune
(+0.0013–0.0015, e.g. fatigue window ~29d / layoff ~40–64d / peak age ~28 /
form ~150–170d / winrate window ~25) but regressed validation beyond 1 SE
(d_val −0.00061…−0.00155, SE ≈0.0004). Third instance of the same ATP pattern
(combiner sweep, SR re-sweep, now feat): tune-window gains on ATP do not
transfer; the hand-picked defaults validate better. Incumbents stand.

**REJECTED — WTA feat sweep (spirit over letter).** Gated under the
newly-adopted production config (P0 combiner + E2 elo): 2/5 configs formally pass
(best #131 d_tune +0.00114±0.00038, d_val −0.00040±0.00047 — inside 1 SE), but
ALL FIVE regress validation (−0.0004…−0.0011) — directionally consistent
overfit, and the post-adoption baseline (tune 0.58791→0.58697) had already
absorbed part of the candidates' signal. A passer with negative expected
validation value does not go to a 30-minute arbiter. FeatureParams sweeps are
now closed on both tours; the refactor's structural value (parity trap fixed,
constants tunable, `feat` group built) stands.

**REJECTED — E1 as a six-feature block.** Match-paired full walk-forward A/B
(identical rows/fold seeds; before = FEATURES minus the six, after = full):
ATP d_tune +0.00018±0.00022, d_val **−0.00038±0.00025** (validation regression
beyond 1 SE); WTA d_tune **−0.00080±0.00023** (tune regression), d_val
+0.00068±0.00037 (inconsistent sign across windows = noise + capacity cost).
Full-window ATP 0.5788→0.5788 LL — the trees spend ~0.005–0.011 importance per new
feature without net signal, confirming the collinearity warning: the decomposition
(ace/df/first-in/bp) is largely absorbed by the opponent-adjusted spw% walk.

**REJECTED — E1b workload/injury pair alone** (the one pre-declared subset:
minutes14 + ret_recent). ATP d_tune −0.00016±0.00017 / d_val −0.00031±0.00019
(worse on both windows); WTA d_tune −0.00057±0.00019 / d_val +0.00097±0.00026
(tune regression; the val-only gain with a tune regression is exactly the
regime-specific-noise pattern the gate exists to reject). **E1 is closed and the
code fully reverted** — walk accumulators, feature emission, predict mirrors, and
tests — so the daily walk pays no cost for unused signals; a rejection note in
features.py's ANTISYM comment marks the tombstone. Suite 71 green, ruff clean,
bit-identical gate re-passed after the revert.

## Final walk-forward (2010–2026, adopted config, fresh data)

| tour | model | acc | logloss | brier |
|---|---|---|---|---|
| ATP | Elo blended (xsurf) | 0.672 | 0.5973 | 0.2062 |
| ATP | Point model | 0.657 | 0.6035 | 0.2093 |
| ATP | **XGB combiner** | **0.688** | **0.5785** | **0.1983** |
| WTA | Elo blended (xsurf) | 0.663 | 0.6095 | 0.2111 |
| WTA | Point model | 0.646 | 0.6166 | 0.2147 |
| WTA | **XGB combiner** | **0.684** | **0.5889** | **0.2023** |

Anchors: Weighted Elo 0.664 / 0.212; bookmaker ≈0.690 / 0.196. 45,762 ATP /
42,348 WTA matches. Standalone Elo Brier improved from the transfer geometry
alone (ATP 0.2069→0.2062, WTA 0.2123→0.2111).

**Round summary vs yesterday's headline** (ATP 0.688/0.1984, WTA 0.681/0.2032):
ATP Brier −0.0001 (0.1983); WTA acc +0.003 (0.684), Brier −0.0009 (0.2023).
Since the July-1 baseline: ATP 0.678→0.688 acc / 0.2022→0.1983 Brier; WTA
0.670→0.684 / 0.2065→0.2023. Gaps to the bookmaker: ATP 0.002 acc / 0.0023
Brier; WTA 0.006 / 0.0063.

## Deferred (next candidates)

P2 home advantage (ioc backfill + ~300-entry tourney→country map; pair coverage
99.5%+ verified feasible), P3 adaptive per-player surface blend (blend_n50), E3
event-speed serve baseline (per-tourney_id shrunk priors), A5 challenger ingestion
(needs a load-time gate in results.py — the flag currently gates downloads only),
ATP combiner re-sweep only if this round changes the ATP feature frame.
