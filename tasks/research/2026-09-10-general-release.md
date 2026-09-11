# General correctness release — September 10, 2026

Status: authorized integration and validation in progress. The user approved the
focused release with “Okay push then”; this is not a predictive-candidate adoption.

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

Final validation, evaluation, deployment and live-generation receipts will be appended
after completion. No predictive improvement is claimed from this integration alone.


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
2016–2026, with no archive-integrity findings. Current feeds are being refreshed
in isolated staging before both tours are rebuilt.


### Cross-runtime contract review

Review found the copied JavaScript verifier and its fixture still expected chronology
v1 while the Python producer uses v2. The verifier now requires v2; its healthy fixture
reads the Python declaration, and an explicit v1 case must fail. **360 web tests**, lint
and type checks pass after the repair. This change does not alter fitted model inputs.
The live-site check remains required on actual generated artifacts.
