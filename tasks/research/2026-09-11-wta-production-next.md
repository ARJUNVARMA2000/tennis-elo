# WTA surface release handoff — September 11, 2026

Read `2026-09-11-wta-production-release.md` and the matching result JSON first.
This is a fixed-candidate integration, not a new experiment-selection round.
The remaining decision is deployment readiness. All times in the evidence are UTC.

## Where the work lives

- Original checkout `/Users/varma/Projects/DEUCE`, branch
  `codex/model-research-preparation`: plans/results only; do not implement on its old source.
- Implementation `/Users/varma/Projects/DEUCE/.research/2026-09-11-wta-surface-production`,
  branch `codex/wta-surface-production`, based on accepted `dda948c`.
- Final functional source: `d75b7ef`, following `9091769` and `2c95275`.
- Current evidence/drivers: `.research/2026-09-11-wta-production-evidence/` (E below).
- Frozen accepted research: `.research/2026-09-11-wta-surface-serving` at
  `a6771f8f10d299493706b11c90eeb062f5c753cb`; its evidence is
  `.research/2026-09-11-wta-surface-evidence/`. Keep both immutable.
- Ordinary pre-integration reference source: `.research/2026-09-10-general-release`
  at `dda948c`. The cost reference was fitted into E, not into that checkout.

E's completed directories/files are create-only evidence. Do not rerun drivers into
them, overwrite failed attempts, or infer unrun work from the presence of a script.
Use the final result manifest and completion receipts to identify successful runs.

## What is already settled

The WTA feature, five bags, final calibration split, orientation, parameters and
threshold32 selector are fixed. ATP remains 42/schema5; WTA is 43/schema6. Both
surface states are serialized and tagged main/enriched. Their query policy is inclusive
60-day completed same-surface counts before observing the retrospective row.

The production implementation exactly reproduced all 42,426 accepted WTA probabilities
across 17 annual folds. `state-binding-proof.json` bridges the later population tags;
`post-fit-source-bridge.json` bridges the final gate/timeline correction and proves
both production predictor files stayed byte-identical through the actual quick run.
Do not repeat the numerical selection or claim a pristine holdout: the reused later
years' week-block interval includes zero and live timing remains unproven.

Both actual full and quick builds completed. Their gates, strict saved probability
witnesses, accepted mirrors, recovery and browser/HTTP checks are recorded in the report.
The final source passed 1,344 tests in a clean Python3.12 checkout. Historical timelines
have an explicit legacy schema path; current-generation WTA evidence still requires all
eight groups. New observations carry their inference schema. Do not rewrite old logs
or remove this distinction to make a migration pass.

## Remaining release steps, in order

1. **Recheck the ATP statistics source.** The current-only fetch and production job
   both reported TML failures; the local full build used verified cached ATP statistics.
   First make a bounded connectivity/data check. Once reachable, run the normal
   `python -m tennis_model.data.download --kind all --strict` successfully in a fresh
   release staging area. Do not remove `--strict`, synthesize freshness, or replace the
   statistics source with a results-only feed to force publication.
2. **Refresh the accepted remote base.** Fetch `origin/master`, inspect new source and
   bot ledger commits, and reconcile them into a fresh release checkout. Preserve the
   current production forecast/benchmark history. Local candidate-generated records
   are retained privately in E and deliberately excluded from the implementation commit.
3. **Confirm the concrete production push is authorized.** The earlier “Okay push then”
   covered the completed general correctness release. This release replaces the WTA
   model. Present the final report/diff and source-readiness result before requesting
   any remaining deployment approval; ordinary implementation/checks need no new approval.
4. **Release with normal gates.** The changed WTA artifact contract must promote an old
   cached WTA predictor to a full retrain. Build fresh Linux/Python3.12 artifacts in CI;
   never upload these local research/release pickles. Keep pre-upload integrity and
   accepted-publication checks, then follow the production workflow after an authorized
   `master` push. A failed strict source step must leave the prior site live.
5. **Verify live acceptance.** Use the new live verifier against the expected deployment
   health/generation; confirm ATP42/schema5, WTA43/schema6, actual predictor IDs, the full
   artifact graph and private-path exclusions. Record the workflow URL, final commit,
   release/model IDs and result. The local verification is not proof of a future deploy.

These steps are sequential except ordinary independent test preparation. Do not launch
new parameter sweeps, adopt the rejected ATP surface candidate, change threshold32,
or validate the unselected ranking runner-up as part of this release.

## Local evidence and reproduction

Run Python from the implementation's `tennis_model` directory using `PYTHONPATH=src`:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src \
uv run --offline --no-project --python 3.12 --with-requirements requirements.txt python ...
```

The initial equivalence replay used the pinned research Python3.13 environment; the
actual full/quick builds, saved models and cost reference used pinned Python3.12.
Strict artifacts intentionally reject the wrong interpreter/library contract.

- `run-release-build.py NEW_DIRECTORY full|quick`: runs the normal pipeline while
  retaining source/raw/runtime manifests, actual feature frames and actual OOS outputs.
  Full/quick acceptance evidence is in `full-001/` and `quick-001/`.
- `verify-saved.py RUN_DIRECTORY`: checks actual saved probability witnesses; do not
  replace an existing run's receipt. `verify-integration-bridge.py` and
  `verify-timeline-exports.py` record the post-fit and timeline parity proofs.
- `full-input-raw/`: frozen full-build match/state inputs. All match/state inputs and 293 files in total matched pre-build hashes; the one
  changed ATP benchmark-cache path is disclosed
  in `full-input-snapshot.json`. `full-output/` preserves the accepted full output.
- `recovered-release/`, `current-raw-archive.tar.gz`, `recovered-raw/`: actual recovery
  exercise, with `recovery-proof.json`. They are evidence, not the live cache.
- `verify-mirror.mjs`, `verify-local-serving.mjs`, `verify-surface-ui.mjs`: recorded
  public mirror, actual local HTTP, and two-tour desktop/mobile evidence checks. The
  focused UI check opens the existing Model evidence disclosure before inspecting it.
- `active-cost-registration.json`, `active-cohort.json`, `active-cost-summary.json`:
  fixed active-player comparison. `prepare-active-reference.py` removes only the surface
  column/state from the retained dual inputs; `fit-active-reference.py` must run under the
  unchanged old source. `run-active-cost.py NEW_DIRECTORY` alternates fresh processes.
  Both arms use the shared dated `prediction_matrices` route because the old convenience
  wrapper lacks `as_of`. The first attempt failed in warmup; no measurements were accepted.
- `final-preservation.json` and the result manifest cover the retained evidence/heads.

Rollback reference is accepted `dda948c`, with compatible schema5 WTA artifacts. A source
rollback alone must not reuse schema6 WTA state. Keep the previously accepted production
cache/receipts available when doing the eventual deployment.
