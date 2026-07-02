# Tuning results — 2026-07-02 (B8: combiner sweep + point re-sweep)

Continues the metrics progression in [baseline-2026-07-01.md](baseline-2026-07-01.md).
Harness: `eval/tune.py` (Optuna TPE, resumable SQLite under `tennis_model/data/output/tuning/`).
Protocol: tune window 2010–2019 (all the optimizer sees), validation 2020–2026 (scored
once per top config); adopt only if tune improves AND validation does not regress by
more than one paired SE of per-match log-loss. All gate numbers re-scored under the
pinned production stack (pandas 3.0.3 / sklearn 1.9.0 / xgboost 3.3.0); xgb trials are
match-paired via deterministic fold seeds; the point objective scores every trial on a
fixed reference serve-sample mask.

## Sweeps run

| study | trials | objective | baseline (tune) | best (tune) |
|---|---|---|---|---|
| atp_xgb | 400 | p_combiner LL, full walk-forward 2010–19 | 0.57078 | 0.56993 |
| wta_xgb | 400 | " | 0.58950 | 0.58792 |
| atp_point_xwide | 250 | p_point LL, fixed ref mask | 0.58856 | 0.58834 |
| wta_point_xwide | 250 | " (surface shrinkage range → 10k) | 0.60984 | 0.60982 |

## Adoption decisions (paired d ± SE, validation window)

**ADOPTED — WTA combiner** (new per-tour `XGB_PARAM_OVERRIDES` in config): plateau
center of five passing configs, anchored on trial #145 —
`lr 0.025, max_depth 7, min_child_weight 50, subsample 0.58, colsample_bytree 0.87,
reg_alpha 0.002, reg_lambda 0.8, gamma 0.08, n_estimators cap 2000 (early stopping
governs)`. Gate: d_tune +0.00145±0.00034, d_val **+0.00046±0.00041** — improves both
windows. Note: `min_child_weight` sat at the search bound (50); a follow-up sweep
could extend the range (expected yield: small).

**REJECTED (by the arbiter) — ATP serve/return constants.** 220/660/1900 passed the
component-level gate on both windows (d_tune +0.00022±0.00014, d_val
+0.00025±0.00019), but the full-pipeline walk-forward disagreed: combiner LL
0.5788→0.5791, acc 0.688→0.686 after retraining on the shifted features. A point-model
gain this small does not survive the combiner; the incumbents (200/600/1400) stand.
Lesson encoded in config comment: component gates screen candidates, the full
walk-forward decides.

**REJECTED — ATP combiner sweep.** All five top configs improve tune
(+0.0004…+0.0009) but regress validation beyond ~1 SE (d_val −0.00028…−0.00081,
SE ≈0.00028) — tune-window overfit; the incumbent hardcoded params validate better
than anything the search found. Kept as the honest negative result.

**REJECTED — WTA point re-sweep.** Best improvement +0.00003±0.00005 = noise. The
extended shrinkage range (3000→10000) settles the open question from yesterday's
adoption: the optimum near 3191 is statistically indistinguishable from the adopted
3000 — the old bound was not binding performance; plateau confirmed.

## Final walk-forward (2010–2026, production stack)

45,744 ATP / 42,332 WTA matches (dedup-fixed data). XGB combiner rows:

| tour | config | acc | logloss | brier |
|---|---|---|---|---|
| ATP | before (= after: nothing adopted) | 0.688 | 0.5788 | **0.1984** |
| WTA | before | 0.679 | 0.5909 | 0.2032 |
| WTA | **after (adopted combiner)** | **0.681** | **0.5898** | **0.2027** |

Anchors: bookmaker ≈0.690 acc / 0.196 Brier. ATP now sits 0.002 acc / 0.0024 Brier
from the bookmaker; the WTA adoption closes its gap by ~8% (0.2032→0.2027 vs 0.196).
(Yesterday's headline ATP 0.1984/0.686, WTA 0.2033/0.678 was measured on
pre-dedup-fix data under the unpinned stack; today's "before" re-establishes the
like-for-like comparison point — ATP acc 0.686→0.688 came from the dedup fix +
restored matches, not from tuning.)

## Environment note

Sweeps searched under xgboost 3.1.3 (local, pre-pin); every gate decision and the
final table were re-scored under the pinned production stack. The dedup fix
(+~181 restored matches) landed between yesterday's baseline and these runs, so the
"before" walk-forward re-establishes the comparison point on identical data.

## Next candidates (Phase 2C)

- FeatureParams: promote FATIGUE_WINDOW_DAYS/LAYOFF_DAYS/PEAK_AGE/form windows into
  the tunable surface (fixes the import-bound predict.py parity trap at the same time)
- Adaptive per-player surface blend; home advantage (winner_ioc + tourney country)
- A5 challenger ingestion experiment (INCLUDE_CHALLENGERS)
- WTA combiner min_child_weight range extension (bound sat at 50)
