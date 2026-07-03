# Autoresearch round — 2026-07-02 evening

Continues [tuning-results-2026-07-02-core-round.md](tuning-results-2026-07-02-core-round.md).
Protocol unchanged: paired per-match log-loss d±SE, gate `d_tune > 0 AND d_val > −1·SE`
(tune 2010–19, validation 2020+), full 2010–2026 walk-forward as arbiter, pinned stack
(pandas 3.0.3 / sklearn 1.9.0 / xgboost 3.3.0). Data frozen all round (no downloads);
feature caches of 2026-07-02 19:35/19:45. Combiner-side experiments run the full walk
ONCE per variant and split the same OOS rows into the two windows — fold seeds are
deterministic, so every variant scores identical rows in identical order.

Starting point: ATP 0.688 acc / 0.5785 LL / 0.1983 Brier; WTA 0.684 / 0.5889 / 0.2023.
Bookmaker anchor ≈ 0.690 / 0.196.

## Wave 1 — combiner mechanics (opt-in knobs in train.py, incumbent-default)

New infrastructure: `_fit_fold(n_bag=, sample_weight=)` + `BaggedClassifier` (k=0
member = incumbent fit, bit-identical at n_bag=1), `walk_forward(n_bag=,
weight_halflife=)`, `cal="stacked"` (StackedCalibrator: Platt on
[logit(p_raw), logit(p_blend), logit(p_point)]). Monotone constraints need no code
(pass through xgb_overrides).

| variant | ATP d_tune | ATP d_val | WTA d_tune | WTA d_val | verdict |
|---|---|---|---|---|---|
| bag5 (5 seed-varied fits, averaged) | +0.00174±0.00028 | +0.00042±0.00029 | +0.00093±0.00030 | +0.00074±0.00035 | **PASS both tours** |
| mono (12 monotone constraints) | −0.00034 | −0.00125±0.00039 | −0.00061 | −0.00130±0.00047 | REJECTED |
| stacked calibration | −0.00062 | −0.00429±0.00044 | −0.00485 | −0.00944±0.00057 | REJECTED |
| rec5 (5y halflife recency weights) | +0.00075 | −0.00161±0.00053 | −0.00127 | −0.00197 | REJECTED |
| rec10 | +0.00079±0.00029 | +0.00010±0.00038 | −0.00036 | −0.00149 | ATP-only pass; testing under bag5 |
| rec20 | +0.00068±0.00024 | +0.00015±0.00030 | +0.00020 | −0.00055 | ATP-only pass; testing under bag5 |

- **bag5**: full-window LL ATP 0.57845→0.57721, Brier 0.1983→0.1978; WTA
  0.58889→0.58803, 0.2023→0.2020. Pure variance reduction — the strongest single
  gain available at zero data cost. WTA acc dips 0.6841→0.6827 while LL/Brier
  improve (averaging softens coin-flip rows); the protocol's target metric is LL.
- **mono REJECTED**: even the 12 "obviously" monotone features (elo diffs, logits,
  skill diffs, form/winrate, h2h) regress validation on BOTH tours — the trees
  evidently use real non-monotone structure (e.g. big elo_diff × low confidence
  interactions).
- **stacked cal REJECTED** decisively: re-fitting component blend weights on one
  calibration season adds variance, badly on WTA (−0.009 val). Plain Platt stands.
  (Two-season Platt was skipped by design: ty−2 rows are in-sample for the fold
  model → biased calibration; pooled-OOS already lost in B6.)
- **recency weights**: ATP mildly likes 10–20y halflife on the tune window but val
  is flat; WTA negative everywhere. Only adoptable if it still helps under bagging
  (bag5rec10/bag5rec20 runs below); WTA is out.

**W1 conclusion — ADOPTED: bag5 (config.N_BAG=5), nothing else.**
- bag10 vs bag5: d_full −0.00004±0.00007 — saturated at 5; bag5 is production
  (train_final/walk_forward default to config.N_BAG; tune.py objectives pass
  n_bag=1 explicitly so sweeps stay cheap; +BaggedClassifier contract test).
- bag5rec10 vs bag5: gate FAIL (d_val −0.00031±0.00024).
- bag5rec20 vs bag5: formal PASS declined (spirit over letter): d_val
  +0.00008±0.00016 ≈ zero expected validation value, val acc 0.6737→0.6729 and
  full acc 0.6887→0.6883 both regress, and the tune-heavy shape repeats the ATP
  pattern that produced three prior tune-overfit rejections. Recency weighting is
  additionally a nonstationarity bet. REJECTED both tours; the knob stays in
  walk_forward for future rounds.
- WTA confirmations: bag5rec10 −0.00069 / bag5rec20 −0.00017 full-window vs bag5
  (rejection confirmed on both tours). WTA bag10 vs bag5 is a formal pass declined:
  d_val +0.00016±0.00013 (~1 SE) but val acc −0.17pp (0.6769→0.6752), 2× production
  train cost, and ATP bag10 regressed val — a per-tour N_BAG split isn't worth it.

## Wave 2b — home advantage (P2)

Implemented: `data/geo.py` (host_ioc: team-tie parsing "…: FRA vs GER" with
neutral-finals exclusion, year-dependent events (Olympics/Tour Finals/WTA Finals/…),
~230-name city→IOC map incl. 1991–2009 training-era names, sponsor-prefix substring
fallback), ioc backfill in results._backfill_bios, `home_flag_diff` ANTISYM feature,
predict.py neutral mirror (0.0 — venue unknown for hypotheticals). +6 unit tests.
Gate: nohome-vs-home paired walk-forward on one rebuilt frame (the nohome side
reproduced the cached-frame baseline LL exactly — bridge intact).

**ATP home — PASS**: d_tune +0.00056±0.00037, d_val +0.00043±0.00038 (consistent
across windows, not the ATP tune-overfit pattern), full LL 0.57845→0.57794, Brier
0.1983→0.1981. Feature coverage: 30% of rows have exactly one home player;
importance rank 8/42 (0.0136) — the trees use it.

**WTA home — PASS decisively**: d_tune +0.00172±0.00029 (6 SE), d_val
+0.00088±0.00038 (2.3 SE); validation ACCURACY +0.36pp (0.6787→0.6823); full LL
0.58889→0.58748, Brier 0.2023→0.2017; importance rank 5/42. **home_flag_diff
ADOPTED both tours** (42 features). Post-adoption geo audit: host mapped for 99.3%
(ATP) / 98.2% (WTA) of 1991+ rows; the audit's fixable holes (Tennis Masters Cup /
ATP World Championships aliases, Virginia Slims Championships, Mumbai/New Delhi,
Helsinki, Palm Springs/San Antonio, Brasília/Salvador/Maceió/Bahia, Sun City/
Durban, Split, Liège, Styria, Merano, Ho Chi Minh City, Oahu, Albuquerque) were
added before the candidate runs; the residue is tiny ITF satellites + Laver Cup
(neutral by design).

**bag10 vs bag5 — no**: d_full −0.00004±0.00007, val slightly negative. Variance
reduction saturates at ~5 members; bag5 is the production setting (half the cost).

## Wave 2a — adaptive surface blend (P3)

Implemented: `EloParams.blend_n50` — per-player surface-blend weight scaled by
n_s/(n_s+n50) (0 = incumbent, bit-identical unit-tested); mirrored in
RatingState.blended. tune.py: blend_n50 ∈ [0, 100] in the elo space; baseline_cfg
now enqueues the FULL incumbent as the TPE anchor (previously only tier anchors).

**REJECTED on BOTH tours by the searches themselves**: after 400 `_ablend` trials
per tour, the best config IS the enqueued incumbent (blend_n50=0.0) — no trial in
either study beat the anchor, and the top-5 all sit at blend_n50 ≈ 0. Mechanism:
under cross-surface transfer every result already informs every surface rating,
so debutant surface ratings aren't noisy enough to need count-gating — the blend
gate double-corrects. The knob stays in EloParams (default 0). Side benefit
retained: elo-group sweeps now anchor TPE at the FULL incumbent config (trial 0 =
the adopted config exactly), which these studies validated (trial 0 reproduced
the baseline to the digit on both tours).

## Candidate configs (bag5 + home_flag_diff)

**ATP candidate vs baseline — PASS**: d_tune +0.00219±0.00043 (5 SE), d_val
+0.00118±0.00042 (2.8 SE); full 2010–2026: acc 0.6883→**0.6897**, LL
0.57845→**0.57665**, Brier 0.1983→**0.1976**. The acc gap to the bookmaker
(≈0.690) is essentially closed; Brier gap 0.0023→0.0016.

~~WTA candidate (pre-fix geo): d_val +0.00179 (4 SE), Brier →0.2014~~ — RETRACTED:
these numbers were inflated by the Fed Cup tie mislabeling (below); the flags
partially encoded tie outcomes. Kept struck-through as the honest record of why
the adversarial review mattered.

**Re-measured on the FIXED geo map** (Fed/BJK ties neutral, DC finals reversals
special-cased — see review section):

- **ATP home (clean) — PASS, stronger than pre-fix**: d_tune +0.00059±0.00036,
  d_val **+0.00134±0.00037** (3.6 SE), val acc 0.6729→0.6753.
- **WTA home (clean) — PASS, honest-sized**: d_tune +0.00018±0.00021, d_val
  +0.00034±0.00030, val acc 0.6787→0.6806 (+0.19pp). The pre-fix −0.00141 LL
  "gain" was ~5× inflated by outcome-correlated tie flags. Marginal value under
  bagging ≈ 0 (cand-vs-bag5 d_val +0.00002) but costs nothing and keeps the
  feature frame uniform across tours → kept.
- **ATP candidate (bag5+home) vs base — PASS**: d_tune +0.00229±0.00042, d_val
  +0.00147±0.00042; full acc 0.6883→**0.6900**, LL 0.57845→**0.57647**, Brier
  0.1983→**0.1975**. ATP sits AT the bookmaker's ~0.690 accuracy anchor.
- **WTA candidate vs base — PASS**: d_tune +0.00112±0.00033, d_val
  +0.00076±0.00039; full LL 0.58889→**0.58790**, Brier 0.2023→**0.2019**; acc
  0.6841→0.6827 (bagging softens coin-flip rows — the calibration/LL gain is the
  protocol's target; noted honestly).

**BOTH CANDIDATES ADOPTED** (config.N_BAG=5 + home_flag_diff are the production
defaults; predict/track/export/sim thread the venue for real matches).

Round vs this morning: ATP Brier 0.1983→0.1975 (+0.17pp acc), WTA 0.2023→0.2019
(−0.14pp acc, LL −0.0010). Since the July-1 baseline: ATP 0.2022→0.1975, WTA
0.2065→0.2019.

## Adversarial review round (multi-agent, 28 agents; 24 raw → 14 confirmed)

A 4-dimension review of the day's diff (leakage/orientation, bit-identity/parity,
geo correctness, harness/stats), each finding adversarially verified. All 14
confirmed findings fixed; the important ones:

- **WTA Fed Cup tie names carry NO host order** (single-venue weeks pre-1995 and
  in zone groups; even WG home/away ties ordered arbitrarily, often winner-first).
  ~11k WTA rows (~8% of training) had mislabeled — potentially outcome-correlated —
  home flags. Fix: tie convention only for "Davis Cup …" names; Fed/BJK ties
  neutral. **All home/candidate numbers re-measured on the fixed map** (the ATP
  Davis Cup file verified host-first 1982–2018, with the two source reversals —
  2016 Zagreb, 2017 Lille — special-cased).
- **E3 estimator converged to HALF the true venue offset** (the residual was
  measured against an expectation that already contained the current offset) and
  used an unweighted two-player mean vs a svpt-weighted raw pool. Fixed (off-free,
  svpt-weighted expectation; exact-value unit test); the `_espd` sweeps that had
  started on the broken math were discarded and relaunched.
- **E3 accumulators now live on ServeReturnState** with `point_probs(event=)` /
  `event_offset()` mirrors — without this, adopting event_shrinkage would have
  silently broken train/inference parity (walk-time p_point venue-aware, pickled
  state venue-blind).
- **home_adv parity**: the walk now records VENUE-FREE probabilities (parity with
  RatingState.win_prob) and applies the home bonus only to update expectations —
  ratings de-bias without a train/serve feature skew.
- **Stale-cache schema guard** in load_or_build_features (the next xgb sweep would
  have crashed on the pre-home cache); `random_state` in xgb_overrides honored as
  the bag-0 seed; CLI slam sim threads the event; ToC 2012 = Sofia; "East
  Hanover" ≠ Hanover; ATP Birmingham = Alabama (host_ioc gained a tour param).

Suite 91 green, ruff clean after all fixes.

## Wave 3 — event-speed serve baseline (E3)

Implemented in serve_return.py: `ServeReturnParams.event_shrinkage` (0 = off,
bit-identical unit-tested). Per-(normalized tourney_name, surface) accumulator of
pooled serve-pct residuals vs expectation (base + offset + mean skill edge); the
shrunk offset shifts BOTH players' serve probs at that event and de-biases the
credited serve/return skills (fast-court numbers no longer inflate serve skill).
Subsumes an indoor/outdoor split (indoor events learn positive offsets). Sweeps:
`_espd` point-group, event_shrinkage ∈ [200, 5e5] log (5e5 ≈ off; a slam accrues
~4e4 svc pts/yr). Point baseline_cfg now returns the true incumbent and tune()
clamps the enqueued anchor's event_shrinkage into the space. (First `_espd`
launch discarded — it searched the pre-review halved estimator; relaunched on
the fixed math.)

**WTA — REJECTED (noise)**: 250 fixed-math trials, best +0.00002 over baseline
with event_shrinkage ≈ 158k (≈ off) and the other params at the incumbent. The
event-speed dimension is flat for WTA; same verdict as the `_xwide` plateau.

**ATP — component gate 5/5 PASS, then REJECTED by the arbiter** (fourth ATP
instance of this exact pattern). Component: baseline tune 0.58856 / val 0.61440;
best #219 d_tune +0.00021±0.00016, d_val +0.00035±0.00021; tight plateau (form_hl
219–236, shrink 654–722, surf_shrink 1949–2159, event_shrink 9.7k–12.8k — a real
event effect, unlike WTA). Arbiter under the plateau center (227/685/2090/11000),
bag5 + home, paired vs cand: combiner LL 0.57647→0.57695, d_tune −0.00030±0.00011,
d_val **−0.00075±0.00013** — worse on BOTH windows after the combiner retrains on
the shifted serve features. The trees already extract venue speed better through
is_indoor/surface/context than through event-adjusted p_point. **E3 closed both
tours**; the event_shrinkage code stays (default off, exact-value unit tests,
state-mirrored inference).

## W2c — Elo-level home bonus (`_home` sweeps, post-review venue-free recording)

`EloParams.home_adv` adds rating points to the home player in the UPDATE
expectation only (recorded probabilities stay venue-free for parity — review fix).
400-trial sweeps with home_adv ∈ [0, 120] + the full prior space, anchored at the
incumbent:

**REJECTED on BOTH tours by the searches**: the anchor (home_adv=0) is the best
of 400 trials on each tour. The combiner's home_flag_diff carries the venue
signal; venue-adjusted rating updates don't improve the walk itself. Notable:
three consecutive 400-trial elo sweeps per tour (xsurf round → `_ablend` →
`_home`) now converge on the identical config — the Elo geometry is a confirmed
plateau; further elo-space sweeps are not worth compute until the space itself
changes.

## Probe round on top of the adopted candidate (bag5 + home, fixed geo)

All paired against `cand` on identical rows; ATP verdicts:

- **Rejected ATP combiner configs, retried under bagging** (top-5 of the `atp_xgb`
  study): every one repeats the tune-positive / val-negative ATP pattern even
  bagged (best: #114 d_tune +0.00051, d_val −0.00011). The 2026-07-02 rejection
  stands; bagging does not rescue them. ATP keeps the `_xgb()` defaults.
- **Base-margin boosting from the Elo prior** (base_margin = logit_p_blend, trees
  learn the residual): d_tune +0.00057±0.00029, d_val **−0.00053±0.00033** —
  textbook overfit shape. REJECTED.
- **Beta calibration** (LR on [ln p, −ln(1−p)] replacing Platt): fails the LL gate
  (d_tune −0.00021) but showed a tempting +0.37pp val accuracy. Robustness check
  killed it: only 9/17 years improve (swings ±1pp), the gain concentrates in the
  partial 2026 season (+3.0pp on 1,650 rows), and every changed call sits at
  p ∈ [0.49, 0.50] — season-unstable threshold jitter, not signal. REJECTED.
- **LR raw-blend — REJECTED both tours.** ATP w=0.2 formal pass at +0.0001–0.0002
  (val acc dips); WTA w=0.1 is exactly zero (d_tune +0.00000) and w=0.2 negative.
  A permanent extra production component (LR fit + blend in every fold and the
  final model) is not worth ≤0.0002 on one tour with zero on the other.

WTA study-config retries under bag+home (top-5 of `wta_xgb_mcw`): all declined.
Two formal passers (#193 d_val +0.00037±0.00012, #191 +0.00032) have ZERO
tune-window movement (+0.00001 / −0.00003) — the val-only-gain shape the
protocol's precedents treat as regime noise (E1b), and the incumbent was itself
adopted as the plateau center of this exact study. Incumbent stands.

WTA beta calibration: REJECTED (fails gate; tune acc −0.8pp — worse than ATP).
WTA base-margin: formal pass at noise (d_tune +0.00024±0.00024 ≈1 SE, d_val
+0.00002 ≈ 0); with ATP's overfit-shaped rejection, base-margin is dead both
tours. **Probe round complete: every probe on top of the candidate rejected —
the adopted set stays bag5 + home_flag_diff.**

## Final walk-forward (2010–2026, adopted config: bag5 + home, fixed geo)

| tour | model | acc | logloss | brier |
|---|---|---|---|---|
| ATP | Elo blended (xsurf) | 0.671 | 0.5973 | 0.2062 |
| ATP | Point model | 0.649 | 0.6035 | 0.2093 |
| ATP | **XGB combiner** | **0.690** | **0.5765** | **0.1975** |
| WTA | Elo blended (xsurf) | 0.662 | 0.6095 | 0.2111 |
| WTA | Point model | 0.636 | 0.6166 | 0.2147 |
| WTA | **XGB combiner** | **0.683** | **0.5879** | **0.2019** |

45,762 ATP / 42,348 WTA matches. Bookmaker anchor ≈ 0.690 acc / 0.196 Brier.
Gaps: ATP **0.000 acc** / 0.0015 Brier (was 0.002 / 0.0023 this morning); WTA
0.007 acc / 0.0059 Brier (was 0.006 / 0.0063). Production verified end-to-end:
fit_predictor (85s, BaggedClassifier), pickle reload, venue-threaded prediction
(Alcaraz at Madrid +2.8pp vs neutral clay), 16.4 MB predictor.pkl; the pipeline's
stale-schema guard now delegates through BaggedClassifier.get_booster().

## Round summary

Adopted (commit 9db1f8d): **seed-bagged combiner (N_BAG=5)** and **home advantage
(home_flag_diff + venue threading)**. Rejected with documented evidence: monotone
constraints, stacked calibration, recency weighting (incl. under bagging), bag10,
adaptive surface blend (both tours, by the searches), Elo home bonus (both tours,
by the searches), event-speed baseline (WTA noise / ATP arbiter veto), LR
raw-blend, beta calibration (year-unstable threshold jitter), base-margin
boosting, rejected-config retries under bagging (both tours), A5 challengers
(no tune-window data). The adversarial review (28 agents, 14 confirmed findings)
caught the Fed Cup host mislabeling before it shipped inside an adopted feature —
the WTA home gain measured on the broken map was 5× inflated by outcome-correlated
flags.

Since the July-1 baseline: ATP 0.678→0.690 acc / 0.2022→0.1975 Brier; WTA
0.670→0.683 / 0.2065→0.2019.

## A5 challenger ingestion — SKIPPED (data unavailable for the tune window)

TML challenger files start 2018; the fresh mirror (LuckyLoser91) carries no
qual_chall files; spot-checked Sackmann forks lack them; GitHub code search needs
auth. Without 2010–19 challenger matches, the adoption gate has no power: the tune
window would score unchanged inputs while validation shifts regime at 2018 — any
measured difference is exactly the untestable-regime pattern the protocol rejects.
Revisit only if a full qual_chall archive surfaces. (Tech-debt note stands: the
INCLUDE_CHALLENGERS flag gates downloads only; results.py would also need a
load-time gate.)
