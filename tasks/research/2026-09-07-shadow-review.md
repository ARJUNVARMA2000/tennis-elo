# Offline uncertainty candidate — engineering acceptance and next steps

**The saved WTA shadow is implemented and its engineering checks pass.** It reproduces
all 42,422 frozen historical predictions exactly. The additional query/storage cost is
modest on this machine. This supplies no new performance evidence: the previously
measured gain remains small and uncertain, and production adoption remains deferred.
The corrected 42-column research incumbent stays current. Nothing was deployed.

Read the [full measurements and hashes](2026-09-07-shadow-result.json),
[interface recorded before implementation](2026-09-07-shadow-interface.md), and
[fresh-data confirmation plan](2026-09-07-shadow-confirmation-plan.md).
The [September 6 verdict](2026-09-06-dynamic-screen-review.md) remains the statistical
result: validation log loss 0.597198487 → 0.596958494, d +0.000239993 ± 0.000127945;
its week-bootstrap interval crosses zero and winner accuracy declines by 0.173 pp.

## What was implemented

The normal predictor now has two shared dispatch points: its ordered feature columns
and calibrated probability function. Scalar, component, evidence, draw and matrix paths
all use them. Defaults retain the exact 42-column production model; the explicit
`DynamicShadowPredictor` uses the registered WTA-only 43-column schema. The selected
parameters remain sigma0=1, q=0.0001, with main-count threshold 32. Both Gaussian states
are saved and the selected state is queried at the supplied date without mutation.
Earlier-than-saved-state queries fail. The dated matrix wrapper now forwards `as_of`.

`build_shadow_inputs` builds both existing and dynamic state bundles from explicit
frozen input frames. `fit_shadow_predictor` uses main-only completed 1991+ rows,
the existing final seed and five bags; the last 365 days are the calibration holdout.
The actual final split has 92,226 core and 2,446 calibration rows, boundary 2025-09-05.
No threshold, candidate parameter, original feature or evaluator was retuned.

A separate `.shadow` artifact has a strict bounded JSON header and exact pickle bytes
inside one atomically replaced file. It binds runtime/libraries, the unchanged base
contract, research feature/state schemas, fixed parameters, package-source hash,
selection and both input identities before deserialization. After loading, it checks
concrete predictor fields, all five boosters/calibration, ordinary states, Gaussian
covariances, parameters, player counts and state dates. Missing or wrong dynamic state
cannot silently become a cold state. It reuses existing secure filesystem primitives
and requires an explicit research destination and trusted root. Ordinary artifact
loaders keep their strict production format/type requirements.

The seven existing evidence groups remain conditional sensitivities of the actual
combiner while holding the dynamic signal fixed; no public UI was added.

## Measured cost

| Measurement | Corrected incumbent | Offline shadow |
|---|---:|---:|
| Single probability, median of 50 warm queries | 4.73 ms | 4.82 ms |
| 30-player matrix, median of 7 warm queries | 62.54 ms | 69.31 ms |
| Fitted model file | 25.80 MB | 29.12 MB |

The matrix increase is approximately 10.8%
(6.77 ms); the scalar difference is
0.09 ms. Raw timing samples and p90s are in the JSON.
Storage compares the incumbent pickle payload with the complete shadow file, including
its header; MB is decimal. This is a warm local measurement, not a concurrency/service SLA.

Full feature/state building took 35.31 seconds;
all 17 historical fold reproductions took 63.57 seconds;
the final five-bag fit took 3.91 seconds. Save and strict load took
0.71/0.58 seconds. The registered real-data acceptance
completed in 119.19 seconds. These measurements make the engineering burden
concrete, but cannot establish that the small historical gain will persist.

## Verification and its exact scope

- **1,352 full-suite tests passed** in 125.68 seconds; **88 focused tests passed**;
  full lint passed. All 76 existing test files are byte-identical to the prior candidate.
- All **43 OOS feature columns and both raw/calibrated probabilities** reproduce the
  frozen candidate on all **42,422 rows / 17 folds**. The parameter selection stayed fixed.
- Strict saved/unsaved predictions match across Hard, Clay and Grass. All 435 pairwise
  scalar/component/matrix comparisons, exchange and permutation checks pass; maximum
  error is 1.11e-16. Fifteen evidence pairs agree with the batch sensitivity path.
- Ordinary ATP and WTA artifacts retain their 42-column schemas and reproduce the
  untouched reference process's features, components, evidence and 30-player matrices
  exactly on all three surfaces. ATP was not widened or retrained.
- Both state branches are exercised on current named players: Rybakina–Sabalenka uses
  main counts 445/577; Rybakina–Tena Lukas uses lower state because Lukas has 8 main
  observations. The dynamic feature and scalar/matrix/exchange outputs agree exactly.
- Three full historical prefixes end before the first later main match after the 2009,
  2017 and 2025 year ends. Main/enriched prefix rows are 85,268/85,268;
  107,555/109,223; and 127,154/141,753. All **43 prefix feature columns** are invariant
  to future append, and all **43 saved-versus-unsaved query features** match exactly.
  The **19 learned-state query features**, including the new dynamic signal, match the
  subsequent walk row with zero error. The probes reuse the present fitted combiner
  only for structural QA; they are not historical forecast scores.

Those scopes are intentionally different. Historical match records supply rankings
and ages that can differ from a previously frozen player-metadata snapshot. After
normalizing missing indoor flags consistently, the three saved historical queries
match 40, 42 and 40 of the 43 later match-row features; remaining differences are
`rankpts_diff`, `age_diff` and `peak_age_dev_diff`. The new dynamic feature is exact.
This is inherited snapshot behavior, shared with the incumbent. A fixed-artifact pilot
will measure frozen metadata/state behavior; daily updates would be a different policy.
Do not describe these checks as all-43-feature equality to every historical match record.

The first temporal diagnostic used `bool(NaN)`, which incorrectly made two missing
indoor values true. `context-check-001` reloaded the same immutable artifacts, normalized
those contexts to the training neutral value and separated the residual metadata gaps.
No model, outcome or source input was changed. The earlier diagnostic is preserved.
The first new unit fixture omitted a required surface argument; it was corrected before
fitting. Four caches replaced by full tests were preserved and restored before acceptance.

## Preservation and exact resume locations

Research root: `/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Implementation checkout: `worktrees/dynamic-shadow`, branch `codex/model-dynamic-shadow`.
Source/test commit: `250693cffacc6bc086d7c1abe209f2f30f9a93a9`.
Freeze: `c50b69e13921cc4f3bb59eb975aea27e9c4a732c9a4746ed69c2f4b14f196828`.

Accepted artifact: `runs/dynamic-shadow/acceptance-001/candidate.shadow`.
Artifact SHA-256: `24fe25bfdb461b507f3a36db9f9b10a9787f8f3731f62f5d1aeda80a3dff1113`.
The required provenance is in that run's completion record and the full result JSON.
Loading needs both that expected provenance and the explicit artifact-directory trusted root;
there is no implicit production/default shadow path.

Final preservation verifies the original checkout, coordinator, Phase 4, maintenance,
and selected-candidate data; the shadow data is also exact. There are seven distinct
copies of each of 18,791 original input files. All 25,826 read-only snapshot files and
56 Phase 3, 77 Phase 4, 104 maintenance and 61 selected-candidate run files remain exact.
Protected source inventories, evaluator, existing tests, program, workflows and web
remain unchanged. The new result JSON hashes all **37 files** in this round's run directory.
Private drivers are retained under `tools/` and hashed; they are not committed as source.

To verify this implementation without fitting, use the preserved coordinator interpreter:

```bash
cd /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/dynamic-shadow/tennis_model
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python -m tennis_model.eval.research_run verify --freeze /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/dynamic-shadow/implementation-freeze.json
```

Do not rerun the exclusive `acceptance-001`, `temporal-001`, `context-check-001` or
`control-001` directories. No further fitting is required to reproduce this handoff.

## Next implementation and dependencies

The offline serving phase is complete. The next work is the [mixed-format future-data
runner and confirmation plan](2026-09-07-shadow-confirmation-plan.md): add a typed
artifact adapter and real mixed-format capture/grade tests in a new checkout, freeze
that runner, migrate/rebuild the fixed candidate under its source identity with exact
reproduction, then register a real prospective interval before its first observation.
The current prospective runner accepts only production-format artifacts and correctly
rejects this shadow. Never bypass its loader or rewrite an old registration.

Runner adapter/schema work must precede capture integration. Source/cadence review and
endpoint-report design can proceed independently. Activation waits for the tested runner,
verified pair and a real future interval. No collector, registration or automation is active.
The proposed 30-day / 200-pair pilot checks reliability; it is far too small to confidently
resolve the observed tiny gain under the historical variance. More fresh data and elapsed
time are now the evidential constraint; repeating the parameter grid is not confirmation.

Population/foundation correctness repairs can be reviewed for production separately
from uncertainty adoption. Neither was merged, pushed or deployed in this phase. The
original checkout receives only the detailed review, plans, evidence and appended logs.
