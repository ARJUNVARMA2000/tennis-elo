# Tuning results — 2026-07-06 (autoresearch round R2: widened-layoff probe + ideation fan-out harvest)

Second round under `tasks/research/PROGRAM.md` (ledger ids R2-*). Branch
`research/2026-07-06` fast-forwarded to base `cf241f8`; started 22:10 EDT, budget 8 h.
Protocol unchanged: tune 2010–2019 / validation 2020+; Tier-1 component sweeps screen,
the full bagged arbiter (`_verdict`, per-year paired-d table) decides. Data frozen; no
downloads. Incumbent at round start: ATP 0.6958 acc / 0.5700 LL / 0.1947 Brier,
WTA 0.6836 / (post-fp1) / 0.2015.

## Round-zero ideation fan-out

Backlog held one OPEN idea (fp3) → the <2-OPEN trigger fired. Three read-only scouts
(data gaps / feature families / methodology) proposed 18 candidates; triage against
the do-not-retry table and rejection docs kept 8 (appended to `ideas.md` as items
6–13: eloSx, sconf, mty, h2hr, tierw, seedf, retd, pooled) and discarded 9:

- **sr_form_trend** (serve-skill 30-day trend) — new rolling state + high WTA noise
  risk for a speculative mechanism; simplicity bias.
- **h2h_surface_ratio** — monotone recombination of columns already in the frame;
  XGB gains nothing new to split on.
- **srv_pts_asymmetry** — subsumed by log_min_srv_pts + exp_diff.
- **convex Elo/combiner blend** — adjacent to rejected LR raw-blend (W3b); scout's
  own EV estimate straddles zero; adds a production component.
- **Brier-aligned early stopping** — sub-gate-threshold EV; requires full hyperparam
  re-tune to compare fairly, so cost ≫ plausible gain.
- **missingness indicators** — redundant with experience/count features already in
  the frame; "is_newcomer by another name".
- **UNFINISHED-GAMES depth** — strictly weaker variant of retd (kept as item 12).
- **TIEBREAK-POINTS clutch** — ultra-sparse (~30% of matches), noisy, weak main
  effect at best.
- **SURFACE-SERVE-BASELINE re-enable** — do-not-retry (E3, 4th ATP component-pass /
  arbiter-veto); the A5 shift does not reopen it (scout concurred: BLOCKED).

One scout premise was corrected during triage: the combiner window is already
expanding-from-1991 (`train.py:240`), so "rolling→expanding" is moot; the salvaged
knob is the `min_train_year` floor (ideas.md item 8, mty).

## Experiments

**REJECTED — R2-001 fp3, WTA feat re-sweep in the widened layoff space (`_fp3`).**
The post-R1 harness maintenance widened `layoff_days` 365→730 because the adopted
value (360) sat at the old ceiling. Answer: the ceiling was not binding. The
incumbent anchor (#0) is unbeaten; the best challenger (#5, layoff 695) is
d_tune +0.00038±0.00022 / **d_val −0.00027±0.00034** (worst year 2021 t=−4.3), and
the nearest same-family config (#17, layoff 493) is d_tune −0.00000 — the
"layoff flag off" region is flat, exactly as the fp1 adoption assumed. Tier-1
sweep 20 trials, 22:12–22:33; no Tier-2 spent (formal PASS declined on direction).

**REJECTED — R2-002 eloSx, explicit overall-minus-surface Elo gap column
(`elo_osgap_diff`, commit `1f06d9b`, reverted).** Top-ranked ideation survivor: give
the trees the surface-dampening term `elo_overall_diff − elo_surface_diff` explicitly
instead of via paired splits. Bagged arbiter, both tours, base arm = incumbent
feature list on the identical frame (bit-reproduces the R0-000 baseline):
- ATP: d_tune **−0.00028±0.00011**, d_val **−0.00038±0.00010**, 6/17 years positive
  — the column actively hurts.
- WTA (the mechanism's motivating tour): d_tune −0.00002±0.00010 (noise), d_val
  **−0.00032±0.00014**, 9/17 flapping.
Reading: linear recombinations of columns the model already sees add capacity cost
without signal — the same shape as the E1 box-score rejection. This narrows the
surviving feature ideas to ones that surface genuinely NEW state (sconf's per-surface
counts qualify; further pure-algebra transforms do not). Clock 22:36–22:51.

**REJECTED — R2-003 sconf, symmetric surface-sample gate (`log_min_surf_matches`,
commit `d328688`, reverted).** The strongest surviving feature idea: surface
genuinely NEW state (per-surface match counts, tracked by RatingState but never
surfaced) as a min-gate so trees can down-weight `elo_surface_diff` on thin surface
history — the exact analog of the adopted `log_min_matches`/`log1p_h2h_total`
pattern. WTA arm (mechanism's motivating tour): d_tune +0.00013±0.00009 (noise),
**d_val −0.00045±0.00012 (−3.75 SE)** — and the per-year table is the cleanest
tune-era-only signature yet: positive 2012–2019, negative EVERY year 2021+ (2021
t=−4.1). Fifth instance of the tune-overfit shape. ATP arm skipped: with the
motivating tour hard-failing validation, no ATP outcome could produce an adoption,
and the capacity-cost prior from R2-002 makes a positive surprise unlikely. The
antisymmetric `w_sn/l_sn` diff variant is presumed dominated and stays shelved.
Clock 22:55–23:00.

**REJECTED — R2-004 mty, combiner training-window floor (driver-only, nothing to
revert).** `walk_forward(min_train_year=2000/2005)` vs the incumbent 1991 on WTA
(data reaches 1980; 56k of 129k frame rows predate 2000). Floor 2000: **d_tune
−0.00100±0.00029** (gate dead), d_val +0.00056±0.00034; floor 2005 strictly worse
(d_tune −0.00212). The per-year gradient is the useful residue: early test years
lose the most training data and hurt hardest (2012–15 t≈−2.5), while 2024–26 are
positive (t>+2.4) — distribution drift is real, but hard truncation overpays for
it, and the graded alternative (recency weighting) is already closed (W1d).
Tier-0 side-result: the R2-002 and R2-003 WTA base arms are bit-identical —
frame build + bagged walk reproducibility reconfirmed. Clock 23:02–23:07.

**REJECTED — R2-005 tierw, per-tier sample weighting in combiner folds
(driver-only, nothing to revert).** sample_weight = mean-normalized `tier_k^α`
injected via a `_fit_fold` monkeypatch, WTA. α=2: d_tune −0.00046±0.00014, d_val
−0.00047±0.00017, **2/17 years positive** — uniformly harmful; α=4 monotonically
worse (d_tune −0.00128). Upweighting slams/masters is dead on arrival for the LL
gate. Side observation: accuracy *improved* (+0.17pp val) while LL degraded —
tier emphasis sharpens the classifier but miscalibrates its probabilities. The
importance-weighting family is now 0-for-2 (with W1d recency weighting).
Clock 23:09–23:14.
