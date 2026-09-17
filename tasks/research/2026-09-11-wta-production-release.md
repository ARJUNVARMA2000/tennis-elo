# WTA surface exposure production integration — September 11, 2026

Status: **locally validated; production deployment held for the unavailable ATP
statistics source.** Implementation and all local release checks below are complete. **This branch has not been deployed.** The user’s
“Keep going” authorized the P0–P4 integration work in `tasks/todo.md`. A new production
push will be a separate, concrete release decision after the checks below.

Follow-up: `2026-09-11-wta-readiness.md` records a newer successful incumbent refresh,
the continuing provider outage, and a correction to the handoff's CI description.
The source-readiness hold is our release recommendation; the existing workflow can
deploy validated retained data after a failed download and report that failure afterward.

## Fixed candidate and scope

WTA adds `surface_recent_diff`: `log1p(countA) - log1p(countB)` for completed
same-surface matches in the inclusive preceding 60 calendar days. Counts are queried
before observing each row in the declared retrospective order. Earlier rows on the
same date may count; this does not establish actual historical feed availability.

The implementation retains the accepted main-only fitting frame, five bags, orientation
seeds, final calibration split, tuned parameters and threshold32 state selector. Each
main/enriched context owns its matching surface history and explicit population tag.
WTA uses 43 ordered features and inference schema6. ATP retains 42/schema5. Both
production constructors, all prediction/evidence routes, strict saved models, caches,
exports and both release gates use explicit tour contracts. No research class is loaded
by production, and older WTA artifacts fail compatibility preflight.

The comparison below was already selected and assessed in the preceding fixed-candidate
round. This integration does not select a new hypothesis or reuse validation for tuning.

| Period | Matches | Reference log loss | Surface log loss | Improvement ± paired SE | Positive years | Accuracy change |
|---|---:|---:|---:|---:|---:|---:|
| Tuning 2010–2019 | 26,794 | 0.590693 | 0.589883 | +0.000810 ± 0.000209 | 8/10 | −0.0261 percentage points |
| Later years 2020–2026, partial 2026 | 15,632 | 0.596920 | 0.596359 | +0.000561 ± 0.000321 | 5/7 | −0.0128 percentage points |

Week-block 95% intervals are [0.000374, 0.001272] for tuning and
[−0.000146, 0.001255] for later years. The latter includes zero. Event-block uncertainty
is unavailable because that evaluation lacks the necessary block identity. These later
years have been inspected in prior research and are not an untouched holdout. The
standing arbiter passed; this is a small probability-quality gain, not an accuracy jump.

## Provenance and preservation

- Integration worktree: `.research/2026-09-11-wta-surface-production`, branch
  `codex/wta-surface-production`, based on accepted production `dda948c`.
- Production implementation: `9091769`; subsequent population-tag validation: `2c95275`.
- Accepted research source remains `a6771f8f10d299493706b11c90eeb062f5c753cb` in
  `.research/2026-09-11-wta-surface-serving`; its inputs/results remain immutable.
- Current private evidence and runnable verification drivers:
  `.research/2026-09-11-wta-production-evidence/`.
- Setup verified 770 prior evidence files and 18 accepted checkout heads, then copied
  and verified all 294 frozen raw files before the independent current-source refresh.

`feature-port.json` records exact equality of all 43 columns on both 129,228-row aligned
frames and the selected frame. Every retained surface history matched, along with 2,400
queries. Unused experimental form/rank state was removed only after this proof.
`replay-completion.json` records all **42,426** exact candidate probabilities across
17 annual folds and 36 exact witnesses from the accepted saved ATP model.

That numerical replay froze source `9091769`. `state-binding-proof.json` is the explicit
later bridge to `2c95275`: the train/orientation/probability implementations are unchanged,
and complete walks over 129,228 main and 146,424 enriched rows reproduce the same counts
and features while tagging the two states. The old ported-input pickle predates the tags
and is retained as evidence only; it is not a deployable production artifact.

## Verification completed before current full build

- Production Python3.12 and existing pinned requirements: 1,333 tests passed. The later
  population-tag/swap change passed 74 focused tests, including the new swap case.
- Web: 374 tests, lint and type checking passed. The production web build and all
  10 fixture browser checks passed. Ruff and whitespace checks passed.
- Earlier failures are retained: stale 42-feature fixtures were corrected; a new gate
  test now uses the typed finding collector; a dependency-directory symlink prevented
  the first local build; restricted font access prevented the second. The real copied
  dependency directory and network-enabled ordinary build passed without config changes.

## Current-source and production observations

The archival refresh completed historical and fresh year files, then repeatedly timed
out at `stats.tennismylife.org`. It was interrupted after ten minutes rather than
continuing the long per-file retry loop. A separate current-only one-attempt refresh
also failed to obtain `2026.csv` and `2026_challenger.csv`. Their prior hash-verified cached
bytes were retained. WTA official statistics, live results/draws, rankings and charting
refreshed successfully; raw recovery checks passed. See `source-refresh-bounded.json`.
This is **not** a successful strict all-source refresh, and no freshness timestamp was
fabricated for cached data.

The existing production run `34622692767` also logged ATP statistics download failures.
Its deployment completed but the post-deploy verifier reported a cacheable homepage
header. A fresh read later returned `no-cache, no-store`; a read-only run of the accepted
production verifier passed all **22/22** checks. This observation did not deploy this
candidate or change hosting configuration. Logs and live health are retained separately.

## Current release checks and decision

The actual full build completed under Python3.12.13 at 17:59:54 UTC. ATP has
285,406 state-history rows, 42 features/schema5, artifact
`227e0145-2000-4f90-8b52-5e90f0c38e20`. WTA has 129,229 main-history rows,
43/schema6, artifact `8a8b36a0-9829-4fd3-b44a-558916d0450c`. Both saved artifacts
reproduce their exported probability witnesses exactly. Full release
`c8f9a590-1256-4026-921c-8bb3b4b91562` passes the corrected semantic gate and
local accepted publication; the mirror verifies 462 exact artifacts and 18 absent paths.

The first real gate rejected 917 old WTA timeline observations: their original model
emitted seven evidence groups, whereas the new current model requires eight. Commit
`d75b7ef` stamps new logged/timeline observations with their inference schema and
validates old schema5 or exact unstamped legacy histories separately. The current
predictor generation remains strict even inside a timeline. It also fixes backend
reversal of surface counts and their signed difference. Old records are not rewritten.
All 223 focused migration/forecast/gate tests pass; the original failed gate is retained.
The earlier full clean-checkout suite passed 1,334 tests; a final clean suite after this
boundary correction is recorded below. Training/state/prediction modules and saved
predictor bytes remain identical to the actual full fit.

Quick refresh, recovery, current-data browser/HTTP checks and active-player costs
all passed. Their final receipts and the release decision follow below.

Rollback source is accepted `dda948c`. Rolling back a WTA schema6 release requires
rebuilding or restoring a compatible schema5 WTA artifact; never pair old source with
the new WTA saved model. The unchanged ATP schema remains supported.


## Final local release verification

- Final functional source `d75b7ef`: **1,344 tests** pass in a clean Python3.12 checkout
  (88.41 seconds), without local raw-data dependencies. Web remains **374 tests** plus
  lint/types, and repository Ruff/whitespace checks pass.
- Quick release `52326d78-0959-4cf8-b0ca-340e9321971a` passes the semantic gate and
  accepted mirror. It reused both exact predictor files: no fit, model-ID change or byte
  change. Strict saved replay passes 36 ATP and 36 WTA probability witnesses.
- The post-fit source bridge names only health, prediction-gate and forecast-log modules.
  Training, states, prediction, calibration and artifact-contract modules are unchanged
  from the full fit. All 13 exported surface timeline points match their immutable
  recorded evidence after orientation. A separate mutation of a real current-generation
  timeline proves that removing its surface group is rejected by the complete output gate.
- Accepted-cache restoration reloaded both strict models. Raw archive restoration
  recovered **290 files**, including all 11 WTA lower-history seasons 2016–2026, with
  byte equality and no archive problems.
- Current-data web build passed; **36/36** desktop/mobile route checks passed. The focused
  two-tour check confirms the WTA surface card and correct counts fit both viewports,
  and ATP has no extra surface card. Its first attempt omitted opening the existing
  disclosure; the corrected browser action passed. Screenshots and failed log remain.
- The actual local HTTP server verified **462 exact artifacts and 18 absent paths**.
  This is local serving evidence, not a new production deployment. The test server was
  stopped before timing measurements.

The normal pipeline's current 2016–2026 backtest covers 29,080 ATP matches
(log loss 0.588582, accuracy 67.7613%, Brier 0.202554) and 26,424 WTA matches
(log loss 0.599257, accuracy 67.0432%, Brier 0.206905). These are build verification
metrics over a different window from the fixed-candidate comparison above, not a
second candidate-selection result or an additional independent validation claim.

## Active-player serving cost

The cohort is fixed before measurement: 20 experienced main-state players and 10
eligible enriched-state players, all active within 365 days of the saved cutoff,
selected deterministically by Elo and name. The reference is refitted on the identical
ordinary inputs with the original 42-column source, five bags and calibration split.
All ordinary query features match exactly across the two arms.

Five alternating fresh-process repetitions each contain one warmup and three measured
rounds, giving 15 measured batches per arm/workload. No fit, browser test or other test
workload competed during measurement. Times below are medians for the complete batch.

| Workload | 42-feature reference | 43-feature candidate | Median increase | p95 ratio |
|---|---:|---:|---:|---:|
| 100 individual predictions | 466.5 ms | 484.7 ms | 3.9% | 1.121× |
| Three 30-player probability matrices | 191.3 ms | 211.7 ms | 10.6% | 1.114× |
| 25 individual explanations | 888.6 ms | 1028.0 ms | 15.7% | 1.145× |
| Three 30-player explanation matrices | 318.0 ms | 361.9 ms | 13.8% | 1.137× |

Saved payload: 25.85 MB → 26.97 MB (**+4.3%**). Median peak process memory:
638.5 MB → 677.8 MB (**+6.2%**). All latency, size and memory ratios passed the
registered 2× limits. This is a local fixed active-player workload, not production
traffic weighting or network end-to-end latency.

The first cost attempt failed during warmup because the old convenience matrix method
lacks a dated-query argument. Both arms were then measured through their shared dated
`prediction_matrices` route; no model code, cohort, rounds or acceptance limit changed.
The failed attempt and successful `active-cost-002/` raw measurements are retained.

## Preservation and production decision

All **770** prior evidence files and **18** accepted checkout heads were verified again.
Nine locally generated forecast/benchmark files were preserved with hashes in E's
`generated-records/`; accepted production ledger files were restored before committing
the source branch. Those private generated records belong with the verified local
release; they must not be committed as though they were production forecasts.

The final remote check still found accepted `origin/master` at `dda948c`. A final
15-second check of the ATP statistics endpoint again timed out. The earlier current-only
fetch and production job also failed to fetch its current ATP files. The completed local
gates used cached ATP statistics through September 7 and results through September 9;
WTA statistics/results reached September 11. No source freshness was fabricated.

**Recommendation: retain the incumbent in production until the normal strict source
refresh can pass.** The candidate has earned a small retrospective improvement and
passed local integration, artifact, recovery, serving and cost checks. That does not
justify bypassing the source step or treating local validation as deployment. No source
branch was pushed or merged into `master` in this round.

The exact next steps, runtime commands, immutable evidence locations and authorization
boundary are in [the release handoff](2026-09-11-wta-production-next.md). Trusted
prospective confirmation remains separate; no new hypothesis or parameter sweep is
needed to close this integration.
