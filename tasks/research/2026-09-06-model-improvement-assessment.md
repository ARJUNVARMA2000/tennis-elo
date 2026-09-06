# Model improvement assessment — 2026-09-06

Assessment of DEUCE at `e170298`, responding to whether more data, compute, or research
time could improve forecasts. This is a proposal, not an adoption result. No candidate
was trained and no model, evaluator, production artifact, or deployment was changed.
The source review and diagnostics below precede any implementation round.

The strongest next investment is a trustworthy measurement baseline and consistent
predictions, followed by targeted data acquisition and a different player-state model.
Repeated searches around the current parameter settings have low expected value.

## Evidence found in this assessment

### Player order changes the probability

Loaded both saved production predictors through `TennisPredictor.load`, retaining the
strict artifact checks. For each tour, selected the first 30 players by non-null
`liveRank` in the local exported `players.json` and evaluated all 435 unordered pairs
in both directions. Context was identical: Hard, best-of-three, outdoor, tier weight
1, round order 3, no named event, as of 2026-09-06. These are hypothetical matchups,
not an accuracy test or a claim about a particular published match card.

Measured `abs(P(A beats B) + P(B beats A) - 1)`:

| Tour | Mean discrepancy | 95th percentile | Maximum |
|---|---:|---:|---:|
| ATP | 0.973 percentage points | 2.342 pp | 4.683 pp |
| WTA | 1.466 percentage points | 3.678 pp | 6.632 pp |

ATP example: Djokovic–Jodar gives 0.587307 for Djokovic when he is first and
0.365867 for Jodar when Jodar is first, implying 0.634133 for Djokovic. WTA's
largest example was Cirstea–Eala (0.507552 forward, 0.426127 reverse).

`model/predict.py:305` directly evaluates the supplied orientation. The matrix path
evaluates one triangle and complements it; that creates complementary cells inside
one matrix without proving invariance when the player list is reordered. Training
randomly flips orientations but does not impose exact symmetry.

Candidate: average the two complementary directional predictions, or explicitly
constrain training/calibration to respect exchange of players. Compare the alternatives
under an orientation-neutral evaluator, verify all inference paths and matrix
permutations, and extend the appropriate output gate. Consistency is a demonstrated
defect; improvement in future predictive loss remains to be measured.

### Historical evaluation uses information beyond its cutoff

- `model/features.py:502` attaches the same current MCP profile to each historical
  row. `data/charting.py:127` sums per-match records over a player's whole available
  career, without filtering by the prediction date. This includes performance-related
  quantities, not just static biographical attributes. Profile availability itself can
  also carry future information.
- `points/serve_return.py:201` computes league/surface serve priors from the full
  supplied frame before the chronological walk. Supplying an identical baseline frame
  protects an A/B experiment from population-induced prior changes, but does not make
  that full-history prior available at each earlier prediction date.

These are identifiable look-ahead paths. Their effect on reported performance has
not been quantified. Rebuild profiles from strictly earlier evidence, and use a
pre-evaluation frozen prior or a chronological prior update. Where historical source
publication times are unavailable, distinguish reconstruction by match date from a
fully documented real-time information set. Add a test that appending future evidence
cannot change past features or forecasts. Correct the measurement protocol and
re-establish its baseline before freezing the next experiment round; do not alter the
measurement instrument mid-experiment. An honest corrected score may be worse.

### Data gaps remain, but coverage percentages are not completeness

Local normalized data inspected with lower-state acquisition enabled:

| Tour | Main rows | Lower-tier rows | Lower history begins |
|---|---:|---:|---:|
| ATP | 153,480 | 131,413 | 2005 |
| WTA | 128,978 | 17,100 | 2016 |

Serve-stat availability among recorded main-draw rows was 90.7% ATP and 80.5% WTA
in 2025, and 94.1% ATP and 96.6% WTA in partial 2026. These denominators include
non-completed rows; identify normally completed, stats-eligible missing matches before
estimating acquisition yield. WTA 2024 has 99.4% availability among 2,121 recorded
rows: that percentage cannot establish that all matches were acquired. Use an independent
event/draw census to measure missing whole matches as well as missing fields.

A second census restricted to rows marked completed gives 2025 serve-stat availability
of 91.2% ATP (2,809 matches) and 83.4% WTA (2,402 matches). Partial 2026 is 94.5%
ATP (2,187 matches) and 99.4% WTA (1,991 matches). WTA 2024 reaches 100% among its
2,078 completed rows, again illustrating why an independent completeness census matters.
These results put missing 2025 WTA statistics ahead of a blanket 2026 WTA stats top-up.

The July data experiment provides the strongest historical evidence for useful new
data: adding about 130,000 ATP lower-tier matches to player states, while keeping
combiner training on main draws, reported validation log-loss improvement
0.00756 ± 0.00100. The corresponding all-row training variant failed. Treat these as
historical results under the then-current evaluation, not freshly verified performance
of the current tip. See `tasks/tuning-results-2026-07-05-data-round.md`.

### Small gains require substantial evidence

Recomputed the saved, row-aligned WTA threshold-32 experiment from
`ab_gated_wta_base.pkl` and `ab_gated_wta_t32.pkl`. On its 2020+ window through
2026-08-17: 15,247 pairs, mean log-loss improvement 0.00098225, per-pair difference
SD 0.08142659, naive paired SE 0.00065944. The mean is about 1.49 SE from zero.

If the effect and variance stayed the same and pairs were independent, about 27,488
pairs would put the expected mean two SE from zero. This is an illustrative precision
calculation, not a power guarantee. Player/event dependence and future distribution
changes require additional treatment. A 200-match prospective comparison is useful for
operational verification and large regressions, not reliable confirmation of this effect.

The existing gate permits `d_val > -SE`; a pass can include a small validation loss.
Keep the established adoption protocol, but describe it accurately and supplement it
with predeclared independent confirmation. Repeated use of 2020+ for model selection
does not make it an untouched final test. Add event/week block uncertainty checks,
retain failed trials, and assess at predeclared endpoints.

## Research priorities after correcting the baseline

1. **Target missing player history.** Audit WTA qualifying/125 and potentially ITF
   evidence, ATP lower-tier holes, and missing completed-match serve statistics.
   Rank sources by coverage of players who enter the forecast population, historical
   availability, reliable identity, and sustainable future updates. Test state-only
   additions on identical scored matches, preserve the established-player protection,
   and separately measure missing-player coverage. Do not infer gains from row count.

2. **Model uncertainty and changing ability directly.** Prototype a dynamic Bayesian
   rating or serve/return model that estimates both strength and uncertainty. It can
   distinguish a well-observed veteran from an equally rated newcomer, increase
   uncertainty after inactivity, and learn how quickly ability changes. Current Elo
   already has dynamic K, inactivity adjustments and form features, so the hypothesis
   must be improved uncertainty propagation, not merely another inactivity flag.
   First test replacement state estimates; then test whether a small ensemble contributes
   independent predictive information. This is a hypothesis, not evidence that Glicko or
   Bayesian models necessarily beat the current hybrid.

3. **Use point outcomes more faithfully.** The existing serve model compresses box
   scores into decayed opponent-adjusted averages. A hierarchical likelihood can learn
   serve and return strength jointly and allow match-level variation rather than
   treating every observed point as equally informative. Rich point sequences are most
   compelling for set-score and in-play targets; basic win forecasting may improve
   without a new point-by-point feed. Evaluate score distributions with their own proper
   loss and reconstruct historical state for tournament evaluations.

4. **Audit timing before richer context.** Historical `date` is derived from
   `tourney_date`; source-specific semantics need checking before interpreting rest
   and fatigue as exact elapsed days. Test historical reconstruction against the
   production rolling calibration and update policy. Add actual match times, travel,
   conditions or independently timestamped absence evidence only if both historical and
   prediction-time coverage are credible. Injury flags, minutes, simple event speed,
   altitude, and generic context expansions already have rejection precedents.

5. **Try different combiners only with a mechanism.** A structurally different model
   or a small blend with different errors is worth a bounded comparison. Bigger trees,
   more seed bags, raw rank, recency weighting and cross-tour pooling are low priorities
   given this repository's rejection history. Do not reopen closed trials without a
   stated change in data, representation or objective. Correcting the baseline can
   justify selected rechecks, not indiscriminate repetition.

## Allocation and sequence

First complete the measurement/consistency audit and reproduce a corrected incumbent.
Next produce paired error slices by tour, experience, surface, recency and source
coverage, including comparable same-match external forecasts where available. Choose
one data hypothesis and one uncertainty-model hypothesis from those diagnostics, with
fixed candidate budgets, identical populations, and explicit stopping rules. Implement
and evaluate them sequentially so each result has a stable incumbent.

Before buying a feed, obtain a representative historical sample and estimate how many
relevant matches and genuinely new pre-match signals it adds. Before buying compute,
profile the proposed experiment. The ledger records arbiters of roughly seven to eight
minutes in earlier rounds; that is historical timing, not a current runtime guarantee.
The stronger constraint so far has been useful hypotheses and trustworthy new evidence.

Use the existing prospective framework for compatible frozen artifacts, recognizing
that it freezes player state as well as parameters. A comparison of daily updating
systems needs a separately specified registered update policy and cutoff-safe state
updates. Freeze the rules; do not mistake stale state for the production policy.

For tracking AI research progress, record fixed-data gain per research hour and compute
cost separately from gains due to new data and from prospective performance. Record
model/tool versions and human interventions, and retain every attempt. Faster historical
hill climbing alone does not establish faster improvement on future matches.

## External methodological context

- [Dwork et al., Generalization in Adaptive Data Analysis and Holdout Reuse](https://proceedings.neurips.cc/paper_files/paper/2015/hash/bad5f33780c42f2588878a9d07405083-Abstract.html)
  explains why adaptive reuse can overfit a holdout; it does not prove a particular
  degree of bias in DEUCE.
- [Ingram, A point-based Bayesian hierarchical model](https://martiningram.github.io/papers/bayes_point_based.pdf)
  models time-varying serve/return abilities with partial pooling. Its published tennis
  results motivate an experiment, not a numerical comparison across different datasets.
- [Ingram, Gaussian Process Priors for Dynamic Paired Comparison Modelling](https://arxiv.org/abs/1902.07378)
  provides another concrete dynamic-model approach.
- [Glickman's Glicko-2 specification](https://www.glicko.net/glicko/glicko2.pdf)
  illustrates explicit rating uncertainty and volatility.

## Review

Source and Git history were reconciled at `e170298`. Diagnostics loaded validated
predictors, measured both orientations and inspected local data and saved paired
experimental outputs. No new backtest, model adoption, dependency change, purchase,
scheduled collector, or deployment was performed. The pre-existing deployment task
remains a separate active item; this proposal does not change its completion state.

### Follow-up handoff plan

The subsequent [implementation and research plan](2026-09-06-model-research-plan.md)
records exact phases, parallel ownership, dependencies, proposed interfaces, acceptance
tests, reproduction recipes and next-session instructions. The accompanying
[evidence JSON](2026-09-06-model-assessment-evidence.json) records the observed diagnostics
and fingerprints of the still-available local artifacts. The separate bracket deployment
has since completed and was documented in `f4a221b`; its model code is unchanged from
the assessed `e170298`. The assessment's historical observations remain as recorded above.
