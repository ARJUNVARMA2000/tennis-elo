# Historical predictive experiments — completed September 8, 2026

**Keep the corrected incumbent.** Two new mechanisms were tested in three registered
variants. None earned advancement to later-year validation under the rule fixed before
fitting. This round produced actual predictive experiments and negative results; no
model improvement or adoption is claimed.

All three trials used the same **26,794 WTA matches from 2010–2019**, identical main-draw
membership, five bags, annual walk-forward folds, calibration policy and threshold-32
state routing. The corrected 42-column reference reproduced bit-for-bit before fitting.
Its tuning log loss is **0.590649156**, accuracy **67.959245%**, Brier **0.203055578**.

## What we tried, what improved and what failed

Positive ΔLL means incumbent loss minus candidate loss, so positive is better. Accuracy
changes are percentage points. ± is paired match standard error, not a confidence interval.

| Trial | Candidate log loss | ΔLL ± SE | Accuracy change | Positive years | Decision |
|---|---:|---:|---:|---:|---|
| Neutralize artificial absence for first recorded appearances | 0.590710586 | −0.000061430 ± 0.000096304 | +0.014929 pp | 4/10 | Reject: worse tune loss |
| Cap one match's serve/return evidence at 40 points | 0.590564901 | +0.000084255 ± 0.000118810 | +0.003732 pp | 6/10 | Decline: gain fails temporal stability |
| Same evidence cap at 80 points | 0.590674249 | −0.000025093 ± 0.000065230 | −0.026125 pp | 4/10 | Reject: worse tune loss |

The 40-point cap's small average gain came from the earlier tuning years: ΔLL
**+0.000297468** in 2010–2014, followed by **−0.000130844** in 2015–2019. The other two
variants also lost in the later tuning half. The 40-point cap improved only one net
winner classification; the absence transform improved four, and the 80-point cap lost
seven. These are tiny changes, not evidence of a new reliable advantage.

| Trial | Tune week-bootstrap 95% interval for ΔLL | Candidate Brier |
|---|---|---:|
| Absence neutralization | [−0.000272195, +0.000142799] | 0.203075641 |
| 40-point cap | [−0.000165695, +0.000320061] | 0.203018426 |
| 80-point cap | [−0.000169678, +0.000123649] | 0.203066355 |

All intervals include zero. Week blocks account for some dependence but not all repeated
player dependence; these tuning estimates are descriptive and subject to selection.
Exact metrics and all ten years per trial are in the [comparison CSV](2026-09-08-historical-comparison.csv)
and [year table](2026-09-08-historical-years.csv).

**2020+ candidate results: not evaluated for every trial.** The shortlist required positive
tune ΔLL, at least six positive tuning years, and positive pooled ΔLL in both tuning
halves. No variant passed all three. Therefore no finalist, no full later-year arbiter,
no ATP trial and no production fit ran. This is the planned stopping rule, not missing
work. The standing adoption gate was not changed or exercised on these candidates.

## Errors that motivated the experiments

The diagnostic script refuses rows outside 2010–2019 and orients player A by canonical
name independently of the outcome. Its bins and initial slice list were fixed before
their results. Selected-state experience and prior serving evidence are pre-match
quantities; current-match stats were not used as predictors.

| Tune slice | Matches | Mean favorite probability | Actual favorite win rate | Interpretation |
|---|---:|---:|---:|---|
| All matches | 26,794 | 68.0323% | 67.9592% | Aggregate calibration is already close. |
| First recorded appearance by either player | 696 | 71.3455% | 77.5862% | Underconfidence in 8/10 tuning years; a targeted hypothesis, not proof of cause. |
| Both players recorded before, absence ≥365 days | 668 | 72.2513% | 74.1018% | The large inactivity bin mixes different populations. |
| Minimum prior serving evidence 100–1,000 points | 8,198 | 68.8536% | 67.5897% | Moderate overconfidence motivated a test of long-match evidence influence. |

The existing context walk assigns 365 days to a player with no previous record. The
first experiment set the pair's rest/log-days/layoff inputs to neutral when either
participant was unseen, preserving known returners. This used an explicit appearance
state and added no model column. Its failure shows that an intuitive encoding change
does not automatically improve prediction; do not ship it as a proven repair.

The second mechanism capped each player-match's contribution to global and surface
serve/return accumulators while preserving observed point rates, decay and the original
prior population. About 30% of historical main player-match service totals exceeded
80 points. A cap changes the relative influence of long and short matches; it is not
the rejected combiner tier/recency weighting or a global shrinkage sweep. The motivation
was weaker than the first experiment's: the slice does not prove that within-match
point dependence caused its error. The trials failed to establish a stable benefit.

Full initial and refined tables are retained in [diagnostics](2026-09-08-historical-diagnostics.csv)
and [first-appearance refinement](2026-09-08-historical-refined-diagnostics.csv). All inspected
slices, including empty and unfavorable cells, remain recorded. The shortlist rejected
closed calibration, missingness-indicator, serve-count-asymmetry and margin/latent-strength
families before fitting. No third mechanism was invented to fill a quota.

## Implementation and checks

Research checkout `.research/2026-09-06-model-foundation/worktrees/historical-errors`,
branch `codex/model-historical-errors`, base `0214834`. Experimental code/tests were
committed at `3d8ce38`, lint formatting at `814def6` before the experimental freeze.
Per-trial ledger commits are `d8b95b2`, `620ae4b`, `2724a9b`; Git was rechecked before
writing this review. All hypothesis/parameter/selection rules preceded the first fit.

- `research/historical_errors.py`: fixed tune-only diagnostics with orientation and
  population-boundary tests.
- `research/historical_candidates.py`: appearance-state query mirror and a serialized
  capped serve/return state using the existing prediction-time methods.
- `points/serve_return.py`: one optional state-class construction hook; its default
  remains the incumbent class. No production configuration value changed.
- **60 focused tests passed in 1.06 seconds**, including **24 new tests**, plus lint.
  The full suite was not rerun; no candidate reached adoption.
- **20 real-data parity/control checks** passed. Default and identity-cap point columns
  reproduce exactly. Both capped states' serialized 2009/2015/2018 cutoff queries match
  subsequent walk outputs with zero measured error. Appearance-state continuation is
  exact through the same cutoffs in both main and enriched histories.

The reference replay took 37.96 seconds. Candidate trials took 40.11, 45.84 and 45.81
seconds including their preparation. The round started **14:50:33 UTC**; numerical
closeout completed **15:09:02 UTC**, within the declared three-hour cap. No post-result
parameter expansion or new validation view occurred.

## Preservation and next use

The [result manifest](2026-09-08-historical-error-result.json) records **664** protected
prior files verified, both frozen models unchanged, and fifteen prior accepted checkouts
clean. This round adds **32** retained run files, for **696** next-phase protected files.
Of the 91 frozen package files, 90 remain identical and the one explicit state-construction
hook differs only in this isolated experimental checkout. All other 383 prior tracked
program/web/workflow files match. Its 33 inherited data files remain exact; no raw-training
copy was made. Large external inventories were last fully checked at
2026-09-08T01:58:44.035725+00:00, not rehashed here.

Keep both tested mechanisms closed under this regime. More variants of their thresholds
would be a new search, not completion of this round. A future round needs a materially
different, tuning-supported hypothesis and its own frozen shortlist. The persistent
first-appearance error is a useful diagnostic; it is not permission to assume another
missingness feature or source purchase will fix it. Live confirmation remains separate.
There is no new predictor to deploy, no new live-data acquisition, and no automation.
