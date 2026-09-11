# General correctness release — September 10, 2026

Status: **deployed and independently verified** on September 11, 2026 UTC
(September 10 in New York). The user approved the focused release with “Okay push
then”; this is not a predictive-candidate adoption. The production receipt and
remaining separate research work are recorded at the end of this report.

## Scope and provenance

The release starts from production `749f5992be0cb60d2099ea1b808685edece2faae`.
The reviewed functional patch is the maintenance difference from `c68c321` to
`975379b`, sourced from `8080e34`, `8be9d74` and `1fbe42a`, excluding the experimental
dynamic-rating module/tests. Production recovery, workflow logic, Xiaodi You,
Sherif and Barranquilla fixes remain included. No tuned parameter, 42-feature
vocabulary, five-bag fit policy or WTA threshold32 change is intended.

This includes pair-complementary calibrated probabilities across prediction routes;
chronological serve priors and dated style state with saved-query parity; exact
date/event repairs; reviewed missing WTA results; strict model/input identity;
and private probability receipts enforced before publication and checked after deploy.
Corrections can change predictions. The surface/ranking/form and uncertainty
experiments, point caps and prospective collectors remain outside this release.

Production and research had separately used population version 7. Their combined
population is **8**, with inference schema **5**. Both reviewed ledgers were migrated
to version 8 without changing any records, quarantine or source evidence. SHA256:

- ATP: `4ef5cc7a2728b28263b9c5678759a951f4828460394c18507cbc924abf949f6e`.
- WTA: `e7101928a764d10ad45d1b23154d6a977323f4349c55dbc97d7320478d3894b4`.
- Combined alias table: `6af385561455c43baf3d26c0c205d1409a53b3308db382d08293f62091fdecb2`.

The WTA ledger contains 528 expected results across five reviewed 2024 catalogues
and one quarantined unresolved self-pair. Its per-record primary-source URLs and
evidence remain in `tennis_model/src/tennis_model/data/reviewed/wta.json`.
The exact chronology corrections are recorded in
[the retained CSV](2026-09-06-phase2-date-corrections.csv). Event evidence came from
[the ATP archive](https://www.atptour.com/en/scores/results-archive?year=2024),
[the Metz draw](https://www.moselle-open.com/wp-content/uploads/2024/11/ilovepdf_merged.pdf)
and [the Shelton–Nava Munich report](https://www.atptour.com/en/news/shelton-nava-munich-2026-monday/).
These records support retrospective dates, not historical feed-publication times.

## Inputs, validation and rollback

The recovery archive was retrieved from the existing GitHub `data-archive` release.
Its SHA256 is `355ecaa24e811dc525463d0d1d872dd4a28b7929f88f46a12527309bc7a11bab`.
The latest successful production install log, run `34538372465`, confirms all
committed Python dependency pins. Dependencies remain unchanged.

Private local evidence is retained in `.research/2026-09-10-general-release-evidence/`,
including the recovery archive, previous live release/meta/health, and validation logs.
The known previous production source is `749f599`. A rollback must rebuild compatible
schema-3/population-7 artifacts from the retained recovery inputs; it must not reuse
the new schema-5 model files with old code.

Final validation, evaluation, deployment and live-generation receipts follow.
No predictive improvement is claimed from this integration alone.


## Pre-rebuild validation

The clean-source suite passes **1,312 tests**, without a developer raw archive.
The exact locked web install passes **359 tests**, lint (nine existing warnings,
zero errors), type checking, production build and **10/10 browser route/viewport
checks**. The complete repository Ruff check and diff whitespace check pass.

The workflow mode decision now checks both saved predictor envelopes and bytes.
A missing/stale/incompatible tour promotes a requested quick run to full, so a
schema/population migration regenerates accuracy alongside the model. Existing
workflow branches and both-tour migration cases pass; alert logic is unchanged.
Recovery restored 246 source files, including all 11 WTA lower-history seasons
2016–2026, with no archive-integrity findings. Current feeds were refreshed
in isolated staging before both tours were rebuilt.


### Cross-runtime contract review

Review found the copied JavaScript verifier and its fixture still expected chronology
v1 while the Python producer uses v2. The verifier now requires v2; its healthy fixture
reads the Python declaration, and an explicit v1 case must fail. **360 web tests**, lint
and type checks pass after the repair. This change does not alter fitted model inputs.
The live-site check remains required on actual generated artifacts.


## Rebuilt historical measurements

All 17 annual folds were evaluated with five bags and the unchanged tour settings.
The normal full pipeline produced 2016–2026 predictions; retained identical feature
frames supplied the six earlier tuning folds. This avoids rerunning or selecting on
later folds. Refreshed source data includes partial 2026 coverage. These local results
use Python 3.13.14 and the committed primary dependency pins; production rebuilds on
CI's Python 3.12 runtime. Exact local dependency versions are retained privately.

| Tour/window | Matches | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| ATP all | 46,205 | 0.573974 | 0.196343 | 69.221% |
| ATP 2010–2019 | 28,357 | 0.562589 | 0.191364 | 70.411% |
| ATP 2020+ | 17,848 | 0.592062 | 0.204254 | 67.330% |
| WTA all | 42,425 | 0.592987 | 0.204151 | 67.728% |
| WTA 2010–2019 | 26,794 | 0.590693 | 0.203075 | 67.978% |
| WTA 2020+ | 15,631 | 0.596920 | 0.205996 | 67.299% |

[All years and uncertainty diagnostics](2026-09-10-general-release-metrics.json)
include a same-fit comparison against the legacy canonical-name orientation. They do
not treat the old winner-first headline scores as an honest baseline. Both READMEs now
report the corrected results and timing limitations instead of those old scores.

Against the accepted corrected maintenance baseline, on identical match keys:

| Tour/window | Common matches | Log-loss improvement ± paired SE |
|---|---:|---:|
| ATP tune | 28,357 | 0.000000 ± 0.000000 |
| ATP validation | 17,775 | −0.000015 ± 0.000045 |
| WTA tune | 26,794 | −0.000044 ± 0.000036 |
| WTA validation | 15,610 | +0.000128 ± 0.000103 |

Positive means lower loss. These changes combine refreshed sources, corrected identities
and restored production history; they are not a new hypothesis or adoption result.
Every unmatched old/new scoring key is in 2026 (ATP 63 old/73 new keys, WTA 18/21);
changed dates/names can change a key, so these are not counts of lost/added real-world
matches. Exact keys and the [common-row comparison](2026-09-10-general-release-reference-comparison.json)
are retained. All 28,357 ATP tuning probabilities match the maintenance reference exactly.

### Saved-model and benchmark integration

The first full run rebuilt 285,406 ATP input rows (including lower-tier history) and
129,227 WTA main/export rows, with valid
reviewed-result and chronology receipts. Strict reload reproduced all **36 independent
probability witnesses per tour exactly** across scalar, reversed, component, matrix and
permuted-matrix routes.

It also exposed a durable benchmark integration failure: a prior Tennis Abstract ledger
row used `xin yu wang` in its immutable match ID, while the corrected identity resolves
to `xinyu wang`. The reader now validates the original transition digest, event, season,
round and exact canonical pair before returning an identity-normalized copy. Original
records and probabilities remain unchanged; unproven timing remains excluded. Tests cover
the committed WTA record, settled-result preservation, idempotent append, digest tampering
and rejection of unrelated players/events/rounds/seasons. **1,319 Python tests pass** after
this fix. The full pipeline was rerun to recover the benchmark before publication.


## Local publication acceptance

The repeat full pipeline completed successfully, including the repaired WTA Tennis Abstract
benchmark (45 eligible/graded matches, 19 excluded). The normal full-run predictions for
both tours were exactly equal to the first run, including match identities and probabilities.
Canonical winner comparison also preserves settled results when a reviewed alias changes
only their display name; the focused 36-test benchmark suite passes.

The full and quick integrity gates both report **zero findings**. Full release
`0c471065-fee3-4ff7-9294-78b7a6e53a5f` was accepted and mirrored. Its successor quick release
`3b403003-0add-4762-9797-2d3c7e5cf446` was accepted and mirrored, retaining the same model IDs:
ATP `cc8f9de4-080a-4c3e-a138-1adf336958f0`, WTA `196116c0-5e5f-453f-b2fb-6a68dae79626`.
Strict reload replayed all 36 probability witnesses per tour after both runs.

An actual accepted-cache copy into a new directory passed validation and strict predictor
loads for both tours. The JavaScript deployment verifier checked the actual public mirror:
**462 artifact hashes and 18 required absent paths**, including both private probability
receipts. The final site build succeeded against real release data; **8/8 desktop/mobile
route checks** passed, in addition to the earlier **10/10 fixture route/interaction checks**.
The health writer reports no output problems for either tour.

Local verification-generated forecast and benchmark updates were preserved as private
evidence and removed from the release's source diff. Production CI must generate its own
published observations. Existing production ledgers and frozen forecast evidence remain
unchanged in the pushed source. No raw cache, model pickle or experimental candidate is
included. Fresh `origin/master` remains `749f599` before the push.

## Production acceptance

Source `c5dc31e2d17a312114efd0f246f81213ef9e4c30` was pushed to `master`.
[Production run 34549366788](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/34549366788)
completed successfully: both test jobs, refresh and terminal workflow-health reporting.
CI passed **1,318 Python tests** (one macOS `/tmp` alias test skipped on Linux),
**360 web tests** and **10 browser route/viewport checks**, plus lint, types and build.
The same nine pre-existing web lint warnings remain; no lint errors were introduced.

The new saved-artifact guard selected **full** because the old cached contract was
incompatible. Both models were rebuilt on Python 3.12.14, the pre-deploy integrity
gate passed, and publication reported no issues. The prior artifact graph was also
incompatible with the new contract, so the full run created a parentless accepted
graph. Production-generated forecast/benchmark evidence was persisted by bot commit
`00c123b`; that commit changes only generated data, not the deployed source code.

The [live site](https://deuce-forecast.web.app) was independently verified against
the deployed health generation **2026-09-11T01:45:36Z**. Both CI's exact-build check
and a separate post-deploy check passed **22/22**: **462 exact artifact hashes**, **18
required absent paths**, 424 shard references, nine begun events, route/cache/MIME
behavior and the public prediction/UI contracts. Both model metadata producers point
to the exact pushed source SHA, rather than the later bot data commit.

- Accepted full release: `482db1ef-70bb-4d1c-8672-b004a63b458e`.
- Manifest SHA256: `f3b4aa396c4acf1c0123d36f28f6ee8e140c373472d6f776043b2f390ff8851a`.
- ATP model: `50b99b70-f87e-4b13-ab89-93c2ab8f6bb0`, trained at
  `2026-09-11T01:21:28Z`; 285,406 input matches, results through September 9.
- WTA model: `7879edcb-b3e3-4861-b0f3-4b8da81922bd`, trained at
  `2026-09-11T01:42:48Z`; 129,228 input matches, results through September 10.

Both tours serve population **8**, inference schema **5**, chronology policy **v2**
and the unchanged **42 features**. WTA keeps threshold **32**, both states ready,
all **528** reviewed results verified and the existing single quarantine. No self-pairs,
missing/conflicting reviewed keys or chronology inversions were reported. Independent
probability-audit metadata is present; the private receipt files are not publicly served.

Live health is `ok: true`, with **zero warnings/errors**. Three informational source
notices were already present before this release: volunteer charting ages of 113/110
days and the frozen ATP results overlay that is covered by the current serve-stats
feed. These are retained source limitations, not deployment failures. The independent
receipt explicitly records them; it does not claim that all informational findings
are absent. The production integrity and serving gates were not weakened.

[Machine-readable deployment receipt](2026-09-10-general-release-deployment.json)
records these IDs and checks. Private evidence includes `production-deploy.log`,
`production-run.json`, `independent-live-verification.log`, fetched live health/meta/
manifest bytes and `production-source-receipt.json`. This completes the scoped release.

## Remaining work for the next research session

The fixed WTA `surface_recent_diff` candidate remains separate and undeployed.
Its original accepted research tip is `1f3920aa6f1edb538a1d33e1d149b3d507086206`
on `codex/model-historical-signals`, with source freeze `755342d`. The root research
checkout retains `tasks/research/2026-09-08-historical-signal-next.md` and its original
results. Preserve that evidence, including the modest historical gain and uncertainty.

Start a new isolated implementation checkout from the latest accepted `origin/master`,
not from the old research tip. Port the fixed 60-day surface feature and required
helpers while retaining this release's production repairs. Do not merge all research
branches or reuse population-7 artifacts as production predictors. Register and rerun
the fixed incumbent/candidate comparison on identical population-8 inputs: tune
2010–2019 first, then apply the established advancement rule before evaluating 2020+.
No re-selection using later-year results. Saved-predictor route parity, serialization,
both WTA state routes, serving cost and an explicit adoption decision remain required.
No new candidate, tuned parameter or prospective collector was adopted by this push.
