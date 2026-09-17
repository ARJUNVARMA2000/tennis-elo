# Handoff after the population-8 WTA surface assessment

Read `2026-09-11-wta-surface-serving.md` and its result manifest first. The fixed
candidate has completed its numerical experiment. Do not repeat the rejected sweeps
or select another feature using the validation results. The next implementation is
production integration of this specific candidate, conditional on the recorded
serving decision; this document is a plan, not a deployment receipt.

## Exact state

- Production base used here: `dda948c8dfb0b2bb4d2ad0d205508d4e66cd7ef8`.
- Research checkout: `/Users/varma/Projects/DEUCE/.research/2026-09-11-wta-surface-serving`,
  branch `codex/wta-surface-serving`. Resolve its final acceptance tip before work.
- Numerical source freeze: `61d822c`; serving source freeze: `0583aa0`.
- Evidence root: `/Users/varma/Projects/DEUCE/.research/2026-09-11-wta-surface-evidence`.
  `registration.json`, `serving-registration.json` and `serving-freeze.json` pin rules,
  inputs and source. `prepared/`, `tune/`, `validation/` and `final/` are create-only
  accepted artifacts; retain them unchanged, including all logs and raw timings.
- Earlier evidence remains under `.research/2026-09-06-model-foundation`;
  `setup.json` records the 733 protected files and 17 immutable accepted checkout heads.
  Add this round's final result manifest and checkout tip to future preservation checks.
- Final candidate is `final/candidate.surface`, model ID
  `03be4ad7-a36d-45cc-bd9d-280f3e1e24af`, SHA256
  `5f48d8e2a16b17ad0c1747d830d0b438aa77c22a9b6654858cb2eb5fd9c8b0ea`.
  Reference is `final/reference.pkl` plus its `.envelope`, model ID
  `35e71d0c-cac3-42f6-b002-af213f07b4d5`. This is a fresh paired offline reference,
  not the deployed artifact ID. `final/provenance.json` is required to load the candidate.
- Local artifacts pin Python 3.13 and the frozen libraries. Production CI uses Python
  3.12. Build compatible production artifacts in CI; never upload these research pickles
  or relax runtime validation to make them load.

The exact selected feature is the difference in `log1p` completed same-surface match
counts over an inclusive 60-day window. Five bags, WTA threshold32, tuned constants,
pair orientation/calibration and main-only fitting remain fixed. Only the surface
column is fitted; retained form/rank state is not another candidate. Historical
same-date ordering does not establish physical live feed availability.

## Remaining implementation, in dependency order

### P0 — freeze the production integration baseline

- [ ] Fetch and inspect current `origin/master`, including bot data/identity/recovery
  changes since `dda948c`. Create a new `codex/` integration worktree from accepted
  production, preserving all current release fixes. Append this plan to its todo log.
- [ ] Verify this round's result hashes, final saved files and prior preservation
  manifest before copying anything. Record new input/code/runtime manifests.
- [ ] Carry only the fixed candidate and needed hooks. Do not merge the old research
  branches wholesale. No new signal selection or hyperparameter search belongs here.

### P1 — make the feature a supported WTA training and state contract

- [ ] Move the selected state/query and fitting behavior from
  `research/historical_signals.py`, `signal_combiner.py`, `surface_candidate.py` into
  supported modules under `tennis_model/src/tennis_model/model/`. Keep the existing
  frozen research modules available for the comparison oracle.
- [ ] Add explicit tour-specific ordered feature and signed-feature contracts:
  ATP retains its current 42 features; WTA has the original 42 plus
  `surface_recent_diff`. Do not append a WTA-only column to a shared global list.
- [ ] Extend `model/features.py`'s `build_dual_state_inputs` and selected-state path
  to return the matching main/enriched surface states. Train only main completed
  rows; select the same bundle as `_states_for` when either player has fewer than
  32 main matches. Unknown players must use that same selector. Query before observe,
  include the exact 60-day boundary, and keep queries read-only.
- [ ] Extend `model/train.py`'s ordinary and gated walk-forward/final builders with
  the explicit tour schema. Preserve five bags, orientation seeds, paired averaging,
  calibration and the 1991 training start. Use the normal 365-day final calibration
  split. State-only compaction is optional and needs exact equivalence tests first.
- [ ] Preserve all prediction dispatch hooks already tested in `model/predict.py`.
  Both `fit_predictor()` and `pipeline.build_tour()` currently construct an ordinary
  `TennisPredictor`; update both through one supported factory, with no research
  import needed by scheduled production jobs.

### P2 — persist, export and recover the correct tour contract

- [ ] Extend `model/artifact.py` with exact tour-specific class/field/feature/state
  validation. Declare a new production contract/schema and pin the surface policy.
  Reject an older WTA 42-feature artifact before deserialization or as incompatible;
  preserve strict ATP validation and explicit rejection of the research `.surface`.
- [ ] Update current-artifact preflight and full/quick recovery so an old WTA cache
  triggers a full rebuild. Serialize both surface states with matching ordinary
  cutoffs and validate them against the fitted feature schema. Keep bounded reads,
  source/provenance checks and atomic writes; do not broaden to arbitrary subclasses.
- [ ] Update `pipeline.py` receipt identities and backtest contract, feature caches,
  `model/export.py` metadata/evidence output, and the two release gates. At this base,
  `data/health.py` checks feature count against global `FEATURES`; and
  `web/scripts/verify-deploy.mjs` explicitly requires inference schema 5 in its audit
  checks. Replace those assumptions with explicit supported tour contracts and tests.
- [ ] Bind published matrix/scalar/evidence outputs to the same predictor ID and
  state cutoff. Review the new `recentSurface` evidence group in the web consumer;
  if shown, give it a plain-language label and correct availability semantics.
- [ ] Regenerate `web/public/data/` through the accepted mirror path. Preserve release
  allowlists and prove that research files, provenance receipts and private pickles
  cannot enter public output. Keep the existing CI alert scripts and tests intact.

### P3 — prove equivalence and release readiness

- [ ] Before fitting on newer data, replay the original frozen population with the
  production implementation. Require exact selected features and fold probabilities
  against this round's `tune/` and `validation/`, across all 17 years. Any intentional
  numerical difference needs a separately registered arbiter; do not silently accept it.
- [ ] Repeat query/save/load/scalar/component/evidence/matrix/reversal/permutation
  checks for both state paths, unseen players, day 60/61 boundaries, retirements and
  all supported context arguments. Preserve ATP outputs and 42-feature behavior.
- [ ] Run the full Python suite and repository lint. Run web tests/lint/types/build
  and browser checks when metadata/evidence or web consumers change. Extend the gate
  regression for every new stale/mismatched state or published-contract failure class.
- [ ] Build both tours on current frozen production inputs in the deployment runtime,
  then validate full and quick runs, actual saved reload, accepted-cache restoration,
  model/receipt identity, mirror hashes and live-serving checks against a local server.
- [ ] Recheck serving costs on current active-player scalar, matrix and evidence
  workloads. This round's registered workload includes inactive count-selected players
  and measures scalar and probability matrices, not an end-to-end live workload.

### P4 — concrete production decision and release

- [ ] Record the final diff, model IDs, frozen evidence, validation receipts, limitations
  and rollback revision. Recommend WTA adoption only after P1–P3 pass. Keep ATP as-is.
- [ ] Reconcile the latest remote changes without discarding production ledger updates.
  A `master` push is a production deployment. Establish authorization for that specific
  release before pushing; do not infer it merely from possession of a research artifact.
- [ ] After an authorized push, follow the production workflow and independently verify
  the live generation, metadata, required/absent artifacts and both tour model IDs.
  Append the deployment receipt or exact rollback/failure outcome.

P0 precedes all implementation. P1's schema/state contract precedes P2; gate/export
test preparation can overlap with P1 once that contract is fixed. P3 follows P1/P2;
model-independent web checks can run alongside Python checks, but measure serving
costs without a competing fit/test workload. P4 depends on all previous acceptance
checks. These are work dependencies, not a request to launch parallel agents.

## Verification commands and evidence reuse

Run from the accepted research checkout's `tennis_model` directory:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src:research uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python -m pytest -q
```

`research/surface_assessment.py` provides `freeze`, `fit`, `verify`, `benchmark` and
internal `memory` modes. `research/surface_experiment.py` provides the numerical
registration/preparation/tuning/validation driver. Their outputs are create-only:
read the accepted receipts rather than rerunning into their directories. The original
numerical `verify` checks the pre-serving source inventory and will intentionally
reject the later serving implementation. `surface_assessment.verify_freeze()` is the
explicit verified bridge between those two source freezes. `prepared()` separately
checks all prepared input hashes; final loaders check saved artifact hashes/contracts.

No more final fits are needed to close this offline round. Trusted prospective
confirmation remains independent; existing timing-source limitations have not been
resolved by this retrospective and serving assessment. The ranking runner-up remains
unvalidated on 2020+, recent form failed its consistency rule, and ATP surface failed
its tuning rule. Do not reinterpret or combine those results here.
