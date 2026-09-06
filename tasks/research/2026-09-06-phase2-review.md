# Phase 2 integration, timing repair and freeze — 2026-09-06

**Maintenance is complete and the evaluator is frozen. Full corrected baseline fits and
predictive improvement measurements are Phase 3.** The known B3-R1 inversions are
resolved under an explicit retrospective chronology policy. This does not certify
historical publication times or every archived played date.

The user authorized this continuation with “Okay keep going.” Implementation remains
on `codex/model-foundation`, based on `8080e34`, in:

`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator`

The main checkout stays on `codex/model-research-preparation` with documentation only.
No production merge, push, deployment, data refresh, parameter search, dependency change,
or full real-data model fit occurred. The source comparisons used the frozen archive;
the only network-enabled build step fetched the site's existing Google Fonts.

Read [machine evidence](2026-09-06-phase2-result.json),
[bounded changed-date/evidence rows](2026-09-06-phase2-date-corrections.csv), then the
[overall plan](2026-09-06-model-research-plan.md). The
[Phase 1 review](2026-09-06-phase1-review.md) and its acquisition queue remain historical
context; their statements about pending Phase 2 integration are superseded here.

## What changed and why

Paths below are relative to the coordinator's `tennis_model/src/tennis_model`.

| Area | Implementation and completed check |
|---|---|
| Timing and provenance | New `data/chronology.py`; `data/results.py` retains selected source/file, recorded date/event ID, played date, verified event bounds, date basis, evidence and edition identity. Evidence is attached before selection and resolved after existing deduplication. Selected membership is unchanged. Both normalized cache schemas are now 2. |
| Proven ATP defects | Per-tour repairs in `config.py`: three exact 2024 editions have 17 conflicting start stamps; the exact Shelton–Nava Munich result has one wrong event ID. No event-name similarity joins. |
| WTA evidence | Exact event ID, source match ID, canonical pair and games-only score recover first-party dates from the already-frozen response cache. Ambiguous donors are excluded. `data/wta_stats.py` preserves timing on future adapter rows; no collector ran. |
| Coherent event order | Partially recovered WTA editions retain one event/round basis if uniquely verified bounds support it. A uniform archive stamp exactly one day before the calendar is retained as an archive stamp. Played dates stay separate. This avoids introducing mixed-date inversions in Bol 2016/17, Zhengzhou 2017 and Limoges 2019. |
| Temporal state mirror | `points/serve_return.py` now serializes pending event-end observations and advances a copied query view strictly after availability. `model/artifact.py` validates that queue. Also corrected `data/style_history.py` to use normalized alias-table keys. |
| Inference boundary | `model/predict.py` uses schema **5**, including the chronology policy and pending-state contract. Old schema-3/4 predictors must rebuild normally. Match population version remains **6**, supported by exact membership checks. |
| Full/quick integration | `model/export.py` calls the actual independent probability receipt writer in both modes and rejects unresolved chronology before export. The receipt binds artifact UUID, normalized-input generation, contexts and observed time; public metadata binds its exact private bytes. |
| Release and gates | `artifact_lineage.py` validates/carries `prediction-audit.private` and excludes it from the public mirror. A schema-5 private model still requires its receipt when public markers are stripped. `data/health.py` rejects invalid/missing/stale probability evidence and chronology contract/coverage. `web/scripts/verify-deploy.mjs` validates the public binding and requires exact 404s for the private path on both tours. |
| Evaluation and runner | `eval/protocol.py` reports source/tour/date-basis slices and source edition blocks, with missing slices explicit. New `eval/research_run.py` registers immutable attempts, checks frozen raw/code/config/runtime identity before and after execution, records failure/completion separately, and offers the adopted five-bag ATP/WTA baseline paths. |

Accepted historical releases are checked against their own generation time during carry;
publication health checks freshness against the current time. This lets an accepted old
cache remain carryable without permitting a stale receipt to authorize a new publication.
The chronology summary is an operational contract backed by producer frame checks,
not independent proof of unknown historical timestamps.

## Source investigation and final replay

The ATP archive has conflicting Sunday/Monday event stamps in both historical and stats
files. Primary records establish Belgrade 3–9 November, Metz 3–9 November and
Winston-Salem 18–24 August 2024. See the
[ATP Belgrade archive](https://www.atptour.com/en/scores/archive/london/4787/2024/results),
[official Metz draw](https://www.moselle-open.com/wp-content/uploads/2024/11/ilovepdf_merged.pdf),
and [ATP 2024 calendar](https://www.atptour.com/en/scores/results-archive?year=2024).
The [ATP Shelton–Nava report](https://www.atptour.com/en/news/shelton-nava-munich-2026-monday/)
corroborates the exact 13 April 2026 pair/score: Munich is `2026-308`, not Rome `2026-416`.

WTA cached-provider timestamp dates and calendar bounds are evidence of calendar timing;
they do not reconstruct when a historical file became publicly available. Dates without
that evidence remain explicitly unknown. Availability is after the entire declared day.
The existing retrospective player-state walk still uses event/round order where necessary.

| Frozen population | Selected matches | Played-date walk basis | Event-start walk basis | Unknown walk basis | Unresolved inversions |
|---|---:|---:|---:|---:|---:|
| ATP including adopted lower state | 284,893 | 255 | 137 | 284,501 | 0 |
| WTA main | 128,978 | 235 | 20 | 128,723 | 0 |
| WTA including lower state | 146,078 | 6,815 | 124 | 139,139 | 0 |

All three selected match multisets match the Phase 0 reproduction, comparing original
date/event ID, players, score, round, match number, source match ID and role. Exact
before/after hashes are in the result JSON. The WTA main rows have identical ordered
identities, dates, date bases and availability in both state populations.

ATP has **118 actual date changes**: 17 reviewed event-start repairs and 101 exact-result
ESPN played-date transfers; it has one event-ID change. WTA has **32 actual date changes**,
all from exact-result ESPN timing transfers. The 91 WTA `mixed-date-bases-event-start`
annotations record partial played-date recovery being returned to a coherent event order;
they are not 91 additional changes to the original archive dates. The CSV distinguishes
actual date/ID changes from these annotations.

Timing-qualified valid complete stats observations number 268 for the ATP walk population,
239 for WTA main, and 6,923 for the WTA enriched population. **The adopted WTA prior uses
the same main population in both states**, so the enriched count does not mean 6,923
observations enter its league prior. Unknown-time exclusions remain substantial; the
first-party subset is selective, and its value must be measured in Phase 3.

Initial standard-loader rebuild times were 62.56 seconds ATP, 93.58 seconds WTA main and
53.09 seconds WTA enriched. The replay JSON also records the slightly longer total
normalization/identity-audit duration. No source bytes were edited.

## Validation and limits

- Full Python suite: **1,258 passed in 135.68 seconds**. The subsequent JSON-canonicalization
  fix in the runner passed its four focused regressions plus the real CLI freeze/readback.
  Integer config keys must be canonicalized in their persisted form before hashing.
- Ruff and diff checks passed. Web: **359 tests / 27 files passed**, TypeScript passed,
  ESLint had zero errors and nine existing warnings in unchanged UI files. The production
  build passed after allowing its existing Google Fonts fetch; the initial restricted
  build failed only on that fetch. No deployment was attempted.
- Producer-generated full/quick receipts pass health; missing/tampered files fail. Strict
  release tests cover carrying private bytes, public removal, stripped markers and stale
  bindings. The live verifier's local fixtures cover invalid metadata and private exposure.
- Real ATP 371-row and WTA-main 8-row temporal samples preserve their feature prefixes.
  Eighteen state features agree exactly with serialized prediction-time queries, with
  zero stored-state mutation. The WTA sample exercises five pending prior observations.
- A real WTA 76-row enriched / 8-row main sample exercises the actual threshold-32 lower
  branch: both prefixes are exact and all 18 checked selected-state features agree with
  the serialized dual-state predictor, maximum error **0**.
- These are bounded state probes plus fitted synthetic artifact tests. **Normal real-data
  fitted schema-5 artifacts and the 435-pair checks are still required in Phase 3.** No
  accuracy, Brier, log-loss gain, or candidate adoption is claimed.

The Phase 0 snapshot still has 25,826 files and manifest SHA-256
`8636748e1012a1fa1f5a31ea0cdd52f414acfaa78ca5123931e24d1c86473cb9`.
The original project's data and every worktree's raw/output data are unchanged. All six
roots retain distinct data-file inodes; no worktree data symlinks were introduced. Only
isolated derived caches changed. The three newly rebuilt population caches and historical
caches were saved privately and restored after tests; unused caches still rebuild through
the normal fingerprint guard.

## Frozen contract

The accepted file is **`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase2/evaluator-freeze-v2.json`**.
The earlier `evaluator-freeze.json` is a rejected draft retained to document the JSON
integer-key readback failure; do not use it. The `-v2` suffix is an attempt name, not a
change to the `research-freeze-v1` format.

- Full contract SHA-256: `add41de4629703455fad849c59dfc21a82fa569f13e91970417894127615217d`
- Raw-input inventory SHA-256: `40cea9552a51ef7fc1f90dca47e4c5be7fa87987b0d73f5f4b96837bd86387bd`
- Model/evaluator source inventory SHA-256: `0e10742cfc0c12b28055e270936965cacb47a8065b9001e949b35f54fc9e0a1b`
- Data cutoff: ATP 2026-09-05; WTA enriched state 2026-09-06 (WTA main ends 2026-09-05).
- Runtime: Python 3.13.14; NumPy 2.5.0, pandas 3.0.3, scikit-learn 1.9.0, XGBoost 3.3.0.
  The private freeze includes every raw/source inventory entry, effective tour settings,
  feature order, policies and runtime. Dependencies were not installed or changed here.

Freeze verification is an input/code/runtime guard, not a new adoption gate. Existing
criteria remain positive tune delta (2010–19) and validation delta greater than minus one
paired naive standard error (2020+). Week/event block diagnostics supplement that gate.
The known temporal limits above are part of the frozen definition.

## Exact next-session sequence — Phase 3

Use the coordinator checkout and its existing isolated runtime. Do not use the main
checkout's old implementation, old feature caches, or production predictor as the corrected
baseline. Do not edit evaluator/model/config, fetch inputs or tune parameters during these
runs. An identity mismatch is a stop-and-investigate condition, not a reason to overwrite
the freeze. Existing run directories are immutable; use a new numbered attempt for retry.

```bash
cd /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model
export UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv
export PYTHONPATH=src
uv run --offline --no-project --python .venv/bin/python python -m tennis_model.eval.research_run verify --freeze /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase2/evaluator-freeze-v2.json
uv run --offline --no-project --python .venv/bin/python python -m tennis_model.eval.research_run baseline --tour atp --freeze /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase2/evaluator-freeze-v2.json --run-dir /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase3/atp-baseline-001
uv run --offline --no-project --python .venv/bin/python python -m tennis_model.eval.research_run baseline --tour wta --freeze /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase2/evaluator-freeze-v2.json --run-dir /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase3/wta-baseline-001
```

Run ATP then WTA **sequentially**. The runner explicitly starts at 2010, ends at the frozen
cutoff year and uses five bags. WTA fits the unchanged main combiner once per fold and
selects enriched test state below threshold 32; it saves the main reference and asserts
protected-row probability equality. A plain WTA `walk_forward` is not the incumbent.
`pipeline --backtest` alone still uses the production backtest window and is not a
replacement for this research recipe.

Each attempt writes `registration.json` before fitting, then either `completion.json` or
`failure.json`; a registration without completion is interrupted/incomplete. Preserve all
attempts, logs and OOS files. The runner records scored keys, yearly coverage, exclusions,
source/date-basis counts, metrics and OOS bytes. It does not tune, deploy, refresh data,
automatically adopt a candidate or manage a global multi-trial scheduler.

After those runs:

1. Inspect scoreable-year coverage and every exclusion, then report log loss, Brier,
   accuracy, calibration and the fixed slices. Use identical row keys for comparisons;
   distinguish measurement corrections from a newly improved model.
2. Fit normal final predictors with `fit_predictor(tour, save=False)`, save each under a
   **new private Phase 3 run directory**, and load through `TennisPredictor.load(tour, path)`.
   Register these fits with `run_registered`; never overwrite the production artifacts.
   They use final-model rolling calibration, unlike yearly OOS folds.
3. Repeat the original top-30-liveRank / 435-pair exchange probe from plan §15 through
   the validated loader, with the saved archive roster and explicit surface/format/date.
   Exercise both WTA branches, matrix permutations and independent scalar/component
   calls; record discrepancies, artifact UUIDs, inference cost and receipt validation.
4. Derive the diagnostic report from these frozen outputs. Reporting and read-only source
   acquisition design can proceed while sequential fitting runs. Source ingestion, candidate
   trials and collectors wait for their later planned phases; no background task was started.
5. Pre-register the next data/model hypotheses, budgets, targets and negative controls.
   Keep the Phase 1 acquisition findings (including unverified expected denominators) as
   proposals until source coverage and paired eligibility are actually demonstrated.

The private reproducibility scripts are under the run root's `tools/`; logs are under
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/.research/phase0/logs/phase2-*`. They are diagnostic helpers, not committed model
code. The durable implementation, tests, policy, result JSON and bounded CSV are committed
with this review. Publication remains a separate later step.
