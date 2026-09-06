# Phase 1 implementation and handoff — 2026-09-06

**Phase 1's component implementation and bounded audit are finished. Integration and
baseline evaluation are not finished.** The timing audit proved an additional blocker,
**B3-R1: mixed date bases can ingest later-round outcomes before earlier-round matches**.
Resolve it before Phase 2's evaluator freeze or Phase 3's corrected baseline. No claim
of predictive improvement is made from the passing correctness tests.

User authorization was “Continue to phase 1 then.” This work is pre-round maintenance
on `codex/model-foundation`, based on `c68c321`, in the isolated coordinator checkout:

`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator`

The original checkout remains on `codex/model-research-preparation`; its documentation
will point here. Do not run the new code against the original output directory. The
production branch was not changed, and nothing was pushed or deployed. Four worktrees
were prepared in Phase 0; no additional agents were launched in Phase 1.

Read next: [data/timing audit and acquisition queue](2026-09-06-phase1-data-audit.md),
[machine evidence](2026-09-06-phase1-result.json),
[temporal replay receipt](2026-09-06-phase1-temporal-checks.json), then the
[overall plan](2026-09-06-model-research-plan.md) and `PROGRAM.md`.

## What is implemented

Paths in this table are relative to the coordinator's `tennis_model/src/tennis_model`.

| Area | Implementation | Contract |
|---|---|---|
| Pair probability | `model/probability.py`; consumers in `model/predict.py`, `model/train.py` | One calibrated two-orientation batch; `q(A,B)=(g(A,B)+1-g(B,A))/2`. Finite probabilities, exact feature order and antisymmetric/context partition. |
| Prediction entry points | Scalar, component, evidence, neutralized evidence, matrix and evidence-matrix calls | Same context gives the same probability. Roster permutation and direct reverse calls are tested independently; WTA selects the same complete bundle under exchange. |
| Historical charting | `data/style_history.py`, `model/features.py` | Match-ID/metadata joins, strict prior-day queries, explicit invalid/ambiguous exclusions; existing eight definitions and threshold preserved. |
| Saved charting | `StyleSnapshot`, `model/predict.py` | Frozen values, counts, cutoff, identity and source hash. No current global profile-cache read at prediction time. |
| Serve priors | `points/serve_prior.py`, `points/serve_return.py` | Chronological sufficient statistics from completed valid rows with an explicit availability basis; same-day exclusion and population controls. Empty prior is fixed 0.62. |
| Serve query parity | `ServeReturnState.at()` | Read-only decay to prediction date, including point counts; no mutation of saved accumulators. |
| Saved-model validation | `model/artifact.py` | Inference schema **4**, exact new temporal state/policy checks, finite counts and source identity. Existing pre-unpickle envelope checks remain intact. |
| Evaluator | `eval/protocol.py`, `eval/ab_data.py`, `eval/metrics.py`, train outputs | Canonical outcome-independent legacy orientation, explicit legacy labels, exact scored-key/order pairing, fixed block uncertainty and unchanged adoption inequality. |
| Cache identity | `model/feature_cache.py`, `model/train.py` | Schema 2 plus content hashes for raw/source files, effective feature/rating/serve params, config, runtime, date and policies. Legacy caches miss; builds recheck identity before atomic save. |
| Gate component | `model/probability_audit.py`, `data/health.py` | Bounded independent scalar/reverse/component/matrix/permuted witness, bound to artifact/schema/input generation/time; typed rejection after the rollout marker is present. |

Production fitting and calibration schedules, hyperparameters, feature names, bag count,
WTA threshold 32 and historical population admission are unchanged. The standard and
WTA state-gated walk-forward prediction outputs use the shared probability helper.
The optional stacked-calibration research branch also averages its two forecast
orientations; it does not yet emit the legacy-orientation diagnostic columns. Remaining
raw classifier calls are fitting/calibration, raw-score diagnostics or helper internals.

## Temporal decisions and their limits

Style policy is `mcp-retrospective-played-date-strict-before-v1`. With date-only evidence,
all charts on the prediction date are excluded. Exact duplicates collapse; conflicting
metadata IDs or conflicting per-player statistic rows are excluded and counted. The
snapshot retains counts even below the 200-service-point profile threshold. Historical
publication dates remain unknown, so this is a retrospective reconstruction, not a
certified forecast-availability history. Future observation receipts have not been
activated; that is a collector/integration dependency, not evidence we already have.

Serve-prior policy is `available-date-strict-before-v1`. Inputs require
`stats_available_at` and `stats_availability_basis` (`observed`, `played_date`, or
`event_end`). The adapter supplying those fields must justify the basis; accepting a
label is not a proof of source timing. Unknown/invalid availability is excluded rather
than replaced by tournament start. The current normalized archive supplies neither
field, so **all real prior observations are excluded and the prior remains 0.62**.
This behavior must be resolved or explicitly accepted in the pre-baseline review;
do not silently deploy it as a tuned league estimate.

The moving-baseline algebra preserves absolute opponent-adjusted point sums. If `S`
is adjusted serve points won, `N` is decayed points and `k` is shrinkage, the global
skill is `(S - current_baseline*N)/(N+k)`. Changing the baseline recenters existing
evidence without pretending old points were accumulated at the new baseline or
re-estimating old opponents using future information. Return and surface adjustments
use the corresponding centers. Prefix tests exercise this directly. Player updates
still follow normalized order; the separate B3-R1 defect therefore remains material.

The saved prior includes global/surface won/played totals, last admitted day, population
policy and exclusion counters. Explicit main-only baseline frames protect WTA priors
from added lower-state rows. Saved prediction queries decay player evidence to the
requested date without updating prior totals or mutating saved state.

## Evaluator contract prepared, not frozen

`paired-temporal-foundation-v1` retains tune 2010–19 / validation 2020+, positive paired
log-loss delta and the exact existing gate: `d_tune > 0` and `d_val > -SE`. A separate
`positiveValidationDelta` flag prevents calling a negative validation delta an improvement.
Naive paired SE and yearly tables remain; week and event block bootstraps use seed
20260906 and 2,000 replicates. Partial 2026 appears as its own year; the experiment
manifest must record the actual data-through cutoff. Event IDs/date bases need B3-R1;
these blocks do not remove all repeated-player dependence.

Legacy diagnostics choose canonical player identity before predicting, then convert
to winner probability. `p_legacy_winnerfirst` is explicitly forensic. Average loss over
the two legacy directions is reported separately from averaging their probabilities.
Archived winner-first metrics must not be treated as comparable corrected scores.

Slices currently cover surface, low main experience, selected WTA lower state, both
top 50, outside top 50, inactivity over 120 days, and absence of prior player serving
evidence when their columns exist. Reports are normally per tour. **Source-stratified
coverage cannot yet be reported honestly because normalized source provenance is
missing.** Complete that slice after B3-R1 preserves provenance; report missing slice
fields explicitly when freezing the final evaluator.

The manifest helper creates a new immutable JSON path and supports hypothesis, parent,
input/evaluator hashes, settings, trial budget, start/end clock, costs, versions,
interventions, match keys, exclusions, OOS paths, results, verdict and rationale. It is
a recording API, not an automatically wired research-run launcher: the runner must
populate required evidence before starting a real trial and write a separate completion
record. No experiment was registered, fitted, scored or adopted here. Tiny classifier
fits inside existing/new artifact tests are test fixtures only. Optuna is still absent
from the preserved runtime; dependency installation was not attempted.

## Validation and preserved state

- Final Python suite: **1,230 passed in 43.16 seconds** (43.33 seconds including wrapper).
- Ruff and `git diff --check`: passed. The public web contract was not changed, so web
  validation has not been rerun and is required when the Phase 2 rollout touches it.
- Asymmetric model fixtures exercise both tours, formats, surfaces, context, scalar/
  batch/evidence parity and WTA branches. They reproduce the original defect when
  bypassing the correction; the independent witness detects it even when a matrix
  was filled with complementary values.
- Populated style/prior state round-trips through the strict fitted-artifact loader.
  Tampered totals, missing surface baselines, wrong policies, stale style identity and
  impossible threshold/count combinations are rejected.
- Real MCP prefix replay at 2024-01-01 matches a history built without future charts
  on both tours. Current evidence covers 1,002 ATP / 730 WTA players, with 482 / 338
  meeting the profile threshold. Exclusions are in the temporal receipt.
- Real serve replay uses 500 enriched rows per tour starting in 2019. ATP's 219-row
  prefix and WTA's 293-row prefix match the corresponding full-frame features. Saved
  state predicts the next dated row with maximum absolute discrepancy **0.0** for both
  tours, without state mutation. Priors admit zero points, as explained above. Combined
  real style/serve diagnostic time was 3.81 seconds; this is not a full model rebuild.
- Preserved snapshot SHA-256 remains
  `8636748e1012a1fa1f5a31ea0cdd52f414acfaa78ca5123931e24d1c86473cb9`.
  All 25,826 snapshot files verified, original project data unchanged, and raw/model
  outputs unchanged across all worktrees. Four test-modified coordinator caches were
  restored. A retains its four normal-loader reconstructions; B/C remain untouched.
  Distinct data inodes across original/snapshot/four worktrees were checked again.

Logs and larger receipts are private under the run root, especially
`worktrees/coordinator/.research/phase0/logs/phase1-final-tests.log`,
`runs/phase1/`, and `runs/phase1/data-audit-fast/`. The committed result JSON indexes
their hashes. Git was reconciled at `c68c321` before this report: no concurrent
implementation commits appeared, and `f4a221b` still differs from assessed `e170298`
only by the already-recorded deployment documentation.

## Exact remaining work, in dependency order

1. **B3-R1 timing/provenance repair.** Follow the five concrete steps and raw examples
   in the data audit. This is newly required pre-baseline correctness work, not an
   optional fatigue feature. Preserve and document any resulting population change.
2. **Finish the private probability receipt rollout.** Phase 1 built the receipt and
   gate component; producer/release wiring remains in Phase 2's planned shared integration.
   At present `output_findings()` requires the receipt only when metadata contains
   `predictionAuditSchema`. No current export emits that marker or receipt, so the
   new invariant is **not yet operationally enforced**. Do not describe it as shipped.
3. In `model/export.py`/`pipeline.py`, emit a fresh validated receipt for both full and
   quick builds, with a real input-generation fingerprint and exact predictor ID/schema.
   Use deterministic bounded players/contexts covering both WTA gate branches and
   actual direct reverse calls. Fail closed on absent/empty/stale evidence after rollout.
4. Integrate the private receipt into `artifact_lineage.py` copying/verification rules;
   exclude it from the public mirror. Add the public metadata binding and exact private
   path probe in `web/scripts/verify-deploy.mjs`, plus corresponding Python and web tests.
   Existing lineage rules do not automatically carry this new private file.
5. Complete source-coverage slices and manifest-runner integration, declare the corrected
   availability policy/data-through dates, and hash/freeze the integrated evaluator,
   config, runtime and inputs. Test producer-generated receipts, both build modes and
   missing/stale/empty/modified witnesses. Run relevant Python and web checks.
6. **Phase 3 only after that freeze:** rebuild the actual five-bag ATP and threshold-32
   dual-state WTA baselines sequentially. Regenerate schema-4 predictors through the
   normal fit/save path, then rerun the real 435-pair probes with inference timing.
   Old schema-3 predictors are correctly rejected by the new loader; they were not
   forcibly migrated or unpickled around the contract. Their Phase 0 diagnostics remain
   preserved. Therefore the plan's corrected real-artifact 435-pair acceptance check
   remains outstanding until compatible predictors exist.
7. Review paired errors and register the first data/model experiment. Follow the data
   audit's warning: a validation-only 2024 acquisition cannot satisfy a strictly positive
   tune delta. There is no accepted numerical candidate, deployment or collector yet.

Timing repair and receipt integration can be developed in separate isolated roots;
data acquisition research can proceed alongside them. Their schema/normalization/
pipeline merges, evaluator freeze and numerical arbiters must be sequential. Do not
let another worker refresh the frozen inputs or write the coordinator's outputs.

Resume with these local checks, after inspecting the current task-log tail:

```bash
cd /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator
git status --short
git log -5 --oneline
cd tennis_model
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src \
  uv run --offline --no-project --python .venv/bin/python python -m pytest -q
../.research/phase0/bin/ruff check .
```

A new test run may rewrite the isolated normalized test caches; it must not modify the
original project or Phase 0 snapshot. No full training command is authorized by merely
running these checks. The next requested phase should begin with B3-R1 and the shared
integration checklist, not a tuning sweep.
