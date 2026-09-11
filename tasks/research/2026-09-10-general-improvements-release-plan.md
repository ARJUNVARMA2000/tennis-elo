# General correctness release before further model integration

Status: **Recommended scope; integration and deployment have not started.** The user
asked whether general improvements should be pushed first. Recommendation: prepare and
release the general correctness work before integrating the new WTA surface candidate.
Do not merge the entire research history as a production release.

## Audit performed

Production uses `master`. Fetched `origin/master` is `749f599`, three daily evaluation/data
commits beyond local `master` (`f7d2e6e`); those newer commits contain no program changes.
The research-document checkout is `codex/model-research-preparation` at `4eb5d86` before
this planning entry. The latest accepted research implementation remains
`codex/model-historical-signals` at `1f3920a`.

Production already includes the September 7 WTA recovery/identity repair (`df4cf56`),
its regression isolation (`08871ca`), and subsequent alias/merge receipts. Research
branches predate those changes. Preserve production's `data/raw_archive.py`, lower-history
snapshot restoration, associated workflow calls, health checks, Xiaodi You alias and
Barranquilla event resolution, along with the latest accumulated evaluation records.

A merge preview of `origin/master` with `codex/model-population-repair` (`975379b`)
reports conflicts in `config.py`, `data/health.py`, `tests/test_pipeline_guard.py`,
`tasks/lessons.md` and `tasks/todo.md`. The preview changed neither branch nor checkout.
It is a diagnostic, not the proposed final merge: that research branch also contains
experimental uncertainty code that should be excluded from the release scope.

Both branches currently assign `MATCH_POPULATION_VERSION = 7` to different populations:
production's version includes the Xiaodi You identity repair, while research's restores
reviewed WTA results and merges Xin Yu Wang. The combined release needs a new version
(8 if still unused when implementation begins), both repairs and freshly built artifacts.
Research also changes the inference contract from schema 3 to 5. A code-only push using
the existing production or frozen research predictor files is not a verified migration.

## Proposed release contents

| Area | Include in the general release |
|---|---|
| Consistent probabilities | Calibrated probabilities agree under player exchange and across scalar, component, evidence and matrix routes. |
| Historical information use | Chronological serve priors, dated charting inputs, saved snapshots, pending evidence and non-mutating date-specific queries. |
| Data correctness | Reviewed missing WTA results, duplicate/self-match protection, exact event/date repairs, and independent expected-result checks. |
| Model/cache integrity | Input/schema/version identity, strict saved-model loading, cache invalidation and full/quick probability receipts. |
| Release checks | Pre-upload data/model invariants and the matching post-deploy checks, including exclusion of private audit files from public output. |
| Evidence | Relevant regression tests, source review records and concise deployment documentation. |

Primary implementation sources are `8080e34` (foundation), `8be9d74` (chronology/release
integration) and `1fbe42a` (reviewed population repair). Treat them as sources for a
dependency-complete reviewed patch, not a promise that three unexamined cherry-picks are
sufficient. Carry required tests and ledger files with their consumers. Keep the existing
42 feature names, five bags, tuned parameters and threshold32 state-selection policy.
These corrections can still change probabilities; they require complete model rebuilding.

Leave experimental surface/ranking/form features, uncertainty models and shadow artifacts,
rejected point caps, prospective collection tools and source investigations on their
research branches. Do not publish private runs, large local caches or saved research models
as part of “everything.” The WTA surface candidate remains a separate next implementation.

## Execution sequence

- [ ] Create an isolated `codex/` release branch from freshly fetched `origin/master`.
  Preserve every accepted research checkout and its retained evidence.
- [ ] Port the scoped general fixes, resolve overlapping production repairs, assign the
  combined population version and reconcile schema/cache/receipt migration as one change.
- [ ] Run the applicable full Python suite and web tests, lint, type checks and build.
  Extend regression cases for the combined identities/population and recovery behavior.
  Earlier research test passes are historical evidence, not a pass for this new branch.
- [ ] Rebuild both tours from verified current inputs in isolated output directories;
  verify strict reload, probability consistency, expected results, state parity and
  the unchanged walk-forward evaluation protocol. Separate population corrections from
  model-performance claims; compare common match identities where populations differ.
- [ ] Exercise full refresh, quick refresh, cache/release restoration and public mirroring.
  Run the pre-upload integrity gate on the actual rebuilt outputs, preserving private
  receipts without exposing them through the web mirror.
- [ ] Review the exact release diff, metrics and rollback target. Recheck the latest
  production head before merging. A push to `master` triggers production deployment.
- [ ] For the authorized release, monitor the full workflow and verify deployed serving
  with `web/scripts/verify-deploy.mjs`; record the deployed commit and model generation.
- [ ] Resume the fixed WTA surface-candidate integration against the accepted general
  release baseline, with explicit handling of any changed population/evaluation reference.

## Review of this planning task

Fetched current production metadata, reviewed the functional differences and maintenance
evidence, and performed a merge preview. No implementation branch was created, no models
were rebuilt, no new tests were run, and nothing was pushed or deployed. The recommendation
is a focused general release first; readiness must be established by the sequence above.
