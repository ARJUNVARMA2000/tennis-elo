# Next round — historical predictive errors and bounded model experiments

Status: **planned, not executed**. The user's September 8 direction makes historical
predictive improvement the next priority. Live source research remains a separate
confirmation dependency and must not displace this round. This plan supersedes the
timing-contract handoff's recommendation about what to do next; its factual findings
and strict prospective timing rules remain intact.

## Reference and objective

Start with the corrected **42-column WTA research incumbent**, not the deferred
43-column uncertainty candidate and not the original production checkout's older model.
Use the unchanged main-draw population, threshold-32 state selection, five bags and
annual walk-forward procedure. ATP is required for a tour-agnostic mechanism; a WTA-only
hypothesis must declare that scope before its results. Keep both incumbent artifacts
fixed throughout the round so every candidate has the same reference.

The [maintenance review](2026-09-06-maintenance-review.md) and
[dynamic experiment review](2026-09-06-dynamic-screen-review.md) establish this baseline.
The most recent predictive experiment selected eight uncertainty settings on tuning
years, then deferred adoption after the full gate despite a small gain. Subsequent
serving/source rounds did not test another model-improvement hypothesis. Do not reopen
that exposed grid or relabel its implementation work as a new accuracy experiment.

Research root `R = /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Verified existing input locations:

- `R/runs/maintenance/{wta,atp}-baseline-001/oos.pkl`: saved walk-forward predictions.
- Adjacent `registration.json` and `completion.json`: prediction hashes and run identity.
- `R/runs/maintenance/reference-freeze.json`: corrected baseline contract.
- `R/runs/maintenance/wta-baseline-001/wta-main-reference.pkl`: preserved main-only arm.
- `R/runs/maintenance/{wta,atp}-final-001/`: saved final fitted artifacts, for serving
  parity, **not** for predicting their own historical training matches.

Latest accepted source checkout is `R/worktrees/timing-contract`, commit
`0214834d535654bd92da28180c0d74fb6d33b41b`. It preserves the accepted model source plus
external research adapters. Execution should create a new isolated `codex/` branch
from this tip, with a newly named run directory and a regime-specific cache. Resolve
history again first. Original DEUCE continues to receive documents/logs only.

## H0. Reproduce the reference before diagnosing it

Verify the 664 retained run files, the frozen model/package contracts and prior accepted
checkouts using the timing-contract result manifest. Do not overwrite those runs or
copy large training inventories merely to begin diagnostics. Record which large external
inventories were actually rehashed; their last recorded full check was September 8 at
01:58:44 UTC. Use uv and the existing coordinator interpreter; no downloads or installs.

Verify the selected OOS bytes against their completion receipts before loading. Derive
the tune-only view immediately (`2010 <= year <= 2019`); diagnostics must never print
or analyze later-year slices. Check exact keys, probability range, missingness, unique
membership and the known baseline score. The previous WTA tuning set had 26,794 matches;
any mismatch needs explanation before testing a candidate. Never score old matches
with the final all-history fitted predictor.

## H1. Diagnose systematic probability errors using tuning years only

Write a reusable external diagnostic script and retain machine-readable tables. Fix
the slice definitions before inspecting their error results. Inspect a small set of
interpretable, prediction-time quantities: probability/confidence, surface, round/tier,
main-versus-enriched state route, experience and inactivity, and available serve-stat
coverage. Add a slice only when its historical availability and source can be verified.
Do not use eventual ranking, winner-specific context or post-match statistics as inputs.

Winner-oriented OOS rows require special care. Convert to a deterministic player-A
orientation chosen independently of the outcome; transform both probability and label.
Otherwise a calibration plot with every label equal to one is meaningless. Use
antisymmetric feature transformations where needed and test orientation invariance.

For each bin/slice report match count, years represented, mean prediction, observed win
rate, calibration residual, log loss, Brier, accuracy and loss contribution. Also show
per-year stability. Distinguish poor absolute scores in intrinsically difficult matches
from repeatable miscalibration or missing predictive information. Report sparse/missing
cells explicitly; don't turn a small or single-year extreme into a hypothesis.

These are exploratory diagnostics, not significance tests proving model improvement.
Use fixed year-based stability checks inside 2010–2019; they are also historically
reused data, not newly untouched samples. Preserve every inspected slice and its count
so selection is visible.

## H2. Select two or three genuinely distinct hypotheses

Choose mechanisms **after H1**, rather than promising feature names without evidence.
Each candidate needs: the observed error, expected direction, mechanism, affected
population, source availability, exact intervention, parity burden and falsifying result.

Audit each against [ideas.md](ideas.md), its linked rejection documents and the later
September reviews. A renamed parameter sweep or recombination is not a new hypothesis.
Reopening a closed question requires a material changed premise explicitly recorded
before fitting. If fewer than two defensible hypotheses survive, report that result
rather than inventing experiments to fill a quota.

Freeze the whole shortlist, variants, trial order, budgets and selection rule before
any new candidate 2020+ result is examined. Suggested scope: at most **three mechanisms,
two fixed variants each**, all selected on 2010–2019. This is a ceiling, not an obligation
to run six fits. No Bayesian/general hyperparameter sweep, new data acquisition or
expansion in response to later-year outcomes.

## H3. Run bounded historical experiments

Use the existing frozen evaluator and paired arbiter primitives; do not modify `eval/`,
the adoption inequalities, population or established assertions during the round.
Proposed wall-clock cap: **three hours total**, with a 45-minute diagnostic/selection
checkpoint and at most 30 minutes of screening per mechanism. Record actual clocks
before each experiment. Finish an in-flight arbiter, and classify remaining items as
not run if the budget is exhausted. An implementation that cannot meet parity within
scope is blocked/declined, not given a weaker test.

Build both arms on identical admitted match keys, folds, bagging and calibration policy.
Retain every tune OOS output and negative result. A walk-time feature needs its serving
state mirror and serialized parity test in the same commit. New data/state must respect
delayed availability and the protected-row contract; where appropriate require exact
pre-intervention predictions. Reuse a reference only after verifying its full regime
matches, not just its parameter names.

Run different hypotheses and full arbiters sequentially. Independent read-only analysis
can overlap once inputs and outputs are fixed; two tours of one eligible hypothesis may
use the standing program's bounded component parallelism. This plan does not request
subagents. Do not share writable caches across experiments.

Select **at most one overall finalist** using tune log-loss gain, year consistency and
complexity, with the rule written before screening. Lock its exact code/configuration
before the first new 2020+ candidate evaluation. No positive tune result means no
validation run. Report unselected candidates' later-year columns as “not evaluated”.

## H4. Validate once, report uncertainty, keep or decline

For the locked finalist, run the complete unchanged walk-forward arbiter. Report absolute
incumbent/candidate log loss, accuracy and Brier, paired differences and per-year results.
Define positive log-loss delta as `incumbent loss - candidate loss`; accuracy delta is
`candidate accuracy - incumbent accuracy`, in percentage points. Include the paired
match SE used by the gate and a week-cluster interval as a dependence sensitivity check.
Use event clustering only with verified event identities; report missing coverage rather
than inventing groups or silently dropping rows.

The formal gate stays `d_tune > 0 AND d_val > -SE_val`. Passing it is not proof of a
material improvement: the existing simplicity/consistency review can still decline
replacement. In particular, don't hide a classification loss behind a probability-loss
gain, or let one favorable year dominate the conclusion. Keep the incumbent on noise,
fragile gains, failed parity or unjustified serving complexity.

**2020+ is already-examined validation**, not a fresh holdout. Selecting on tuning years
and inspecting the locked finalist once limits additional feedback, but cannot erase
earlier research exposure. Record this limitation explicitly. Genuine future confirmation
continues when admissible evidence is available; it is not a prerequisite for running
this historical research round. No merge, deployment or new live registration is part
of this plan.

## Deliverable and completion criteria

One results document and a CSV, with this primary table:

| Hypothesis / exact variant | Supporting tune error | Paired N | Tune ΔLL ± SE | 2020+ ΔLL ± SE and cluster interval | Δaccuracy (pp) | Years improved / evaluated | Verdict and reason |
|---|---|---:|---:|---|---:|---|---|
| Populate after actual execution | No invented findings | — | — | Not evaluated until finalist locked | — | — | Not run / rejected / declined / qualified for review |

Include every attempted variant, crashes/timeouts and pre-fit exclusions. Adjacent
tables hold absolute metrics, tune/validation accuracy and Brier, full per-year values,
runtime and artifact hashes. Separate formal gate outcome from replacement recommendation.
The conclusion must answer: what we tried, what improved, what failed, by how much, and
whether any candidate earned replacement. “No improvement” is a complete result.

No experiment has run under this plan. Planning reconciled original Git at `08c8f58`
and accepted research Git at `0214834`; baseline locations and backlog were checked.
