# Fixed WTA surface candidate after the correctness release

Status: **offline assessment complete; advance this fixed WTA candidate to production
integration.** The candidate passes the registered historical, parity and serving-cost
gates. Its gain is modest and uncertain on later years. Production remains the accepted
42-feature model until the separate integration and release checks are completed.

| What we tried | Result | Decision |
|---|---|---|
| Fixed WTA 60-day surface-exposure feature on population 8 | Tune log-loss gain +0.000809949 ± 0.000208925 SE; 8/10 years and both halves positive | Pass |
| Same locked candidate on 2020–2026 partial | Gain +0.000561397 ± 0.000321075 SE; 5/7 years positive; week95 includes zero | Pass standing arbiter, with uncertainty |
| Separate saved 43-feature predictor | 252 real matchup contexts, exact save/load and scalar/matrix parity | Pass |
| Registered serving cost | 1.035x scalar time, 1.308x matrix time, 1.166x artifact bytes, 1.214x peak memory | Pass all 2x limits |
| Winner accuracy | −0.0261pp tune, −0.0128pp validation | No accuracy improvement |

No additional hypothesis, parameter setting or ATP candidate was tried this round.
This assessment rechecks the previously selected surface candidate against the newly
accepted production population and establishes its saved-serving behavior.

## Reproducible starting point

- Production base: `dda948c8dfb0b2bb4d2ad0d205508d4e66cd7ef8`.
- Numerical implementation freeze: `61d822c` on `codex/wta-surface-serving`.
- Serving implementation freeze: `0583aa0` on the same branch.
- Implementation checkout: `.research/2026-09-11-wta-surface-serving`.
- Private evidence: `.research/2026-09-11-wta-surface-evidence`.
- Original candidate evidence: accepted `1f3920a`, source freeze `755342d`, retained
  in `.research/2026-09-06-model-foundation/runs/historical-signals`.

All 733 protected files and 17 accepted historical research heads were checked before
work. The current experiment copied and hashed 294 raw-input files from the accepted
release checkout. It acquired no new data. Production's unmodified loader produced
129,228 main WTA rows and 146,424 enriched rows. Lower-tier rows update the secondary
state; only completed main rows enter combiner fitting and scoring. The numerical
registration verifies code and raw hashes throughout the experiment.

`surface_recent_diff` remains exactly the previously selected signal: the difference
between the players' `log1p` counts of completed matches on the current surface during
an inclusive 60-day window. Query before observing each chronological row; earlier
same-date rows follow the incumbent retrospective order. This is not proof of live
feed-publication timing. No ranking or form feature is fitted in this round.

Keep five bags, WTA threshold32, existing tour settings, calibrated pair averaging and
the 1991 training start. Advance from 2010–2019 only when pooled log loss improves,
both five-year halves improve and at least six years improve. The full arbiter keeps
the existing inequality: positive tuning improvement and validation improvement
greater than minus its paired standard error. Validation years have been used before;
do not describe them as an untouched holdout.

## Current numerical evidence

Six serialized signal-state queries after 2009, 2015 and 2018 matched the corresponding
historical walk rows exactly, across main and enriched histories. The ordinary control
reproduced all 26,794 accepted-release tuning probabilities exactly.

| 2010–2019 | Incumbent | Fixed surface candidate | Change |
|---|---:|---:|---:|
| Log loss | 0.590693064 | 0.589883115 | +0.000809949 improvement |
| Brier | 0.203075155 | 0.202708232 | +0.000366923 improvement |
| Accuracy | 67.9779% | 67.9518% | −0.0261 percentage points |

Paired log-loss SE is 0.000208925; week-block 95% interval is
[0.000373632, 0.001272041]. Eight of ten years improve. The 2010–2014 improvement is
0.000573485; 2015–2019 improves 0.001048506. This qualifies the fixed candidate for
the registered validation step, not production adoption. Raw OOS probabilities,
fold membership and all year/block diagnostics are retained in `tune/`.

| 2020–2026 partial | Incumbent | Fixed surface candidate | Change |
|---|---:|---:|---:|
| Log loss | 0.596919900 | 0.596358503 | +0.000561397 improvement |
| Brier | 0.205996102 | 0.205768722 | +0.000227381 improvement |
| Accuracy | 67.3010% | 67.2883% | −0.0128 percentage points |

Validation has 15,632 matches, with five of seven years improving. Paired log-loss SE
is 0.000321075; week-block 95% interval is [−0.000146335, 0.001254939], which includes
zero. Event-block uncertainty is unavailable because event identity is missing.
Both models replayed the tuning probabilities exactly. The candidate passes the
standing full arbiter; this modest probability-quality gain does not establish an
accuracy improvement or certain future benefit. The current population includes one
additional 2026 match compared with the earlier release evaluation.

## Saved serving implementation and acceptance

The reference and candidate were each fitted once after validation passed, using
92,252 core rows and 2,424 calibration rows with a 2025-09-10 calibration cutoff,
final seed 12345 and five bags. Both use main-only completed rows since 1991. The
paired fits took 10.64 seconds. Main/enriched signal states are retained with the
corresponding ordinary states, both through 2026-09-10. One common inference dispatch
supplies the 43 columns across prediction routes; ordinary ATP/WTA predictors retain
their 42-column behavior.

The explicit surface artifact schema stays outside production output. Its bounded header
pins runtime, code, parameters, ordered features, inputs, selection and both temporal
states before deserialization; typed structure and state receipts are rechecked afterward.
Production readers and destinations reject it. Tests cover interruption, symlinks,
wrong provenance, tampered bytes, altered states and swapped state bundles. The added
production-module hooks are default-preserving; the scheduled pipeline never imports
the research candidate.

The real saved-predictor check passed 252 matchup contexts across three surfaces and
three dates (state date, +1 and +61 days), including 27 main-state and 225 enriched-state
queries. All 43 features match across serialization; the ordinary 42 match the paired
reference exactly. Scalar, components, `predict`, grouped evidence and matrix results
agree; reversal/permutation checks pass at 1e-15 tolerance. Unseen-player and inactivity
queries pass and do not mutate saved state. Six earlier real historical-prefix checks
are separate evidence for the temporal signal mirror, not current metadata equality.

The serving registration fixes 30 representative players: 20 with main experience
and 10 eligible for the lower state, chosen by match counts with name tie-breaks.
Measurements used all three surfaces, 100 scalar pairs, two warm-ups and nine measured
rounds, alternating candidate/reference order. Each model has 900 scalar and 27 matrix
measurements, plus three fresh-process peak-memory measurements. The count-selected
cohort includes inactive players; it is not a traffic-weighted workload. No fit/test
workload ran concurrently with timing measurements.

| Cost | Reference | Candidate | Candidate/reference |
|---|---:|---:|---:|
| Scalar median | 5.255 ms | 5.439 ms | 1.035x |
| Scalar p95 | 5.533 ms | 5.756 ms | 1.040x |
| 30-player matrix median | 56.791 ms | 74.261 ms | 1.308x |
| 30-player matrix p95 | 57.599 ms | 78.590 ms | 1.364x |
| Saved artifact bytes | 25,628,872 | 29,872,026 | 1.166x |
| Maximum of three fresh-process peaks | 466.30 MiB | 566.28 MiB | 1.214x |

All registered median-latency, artifact-size and peak-memory ratios are below 2x.
Artifact comparison includes the reference's envelope. Memory is total process peak,
not incremental model allocation. The candidate retains the original full signal
state (including unused form/rank histories); compacting it is optional future work
and would require exact equivalence. Evidence-route/end-to-end production latency
was not measured. The result manifest retains every timing, cohort and receipt hash.

The saved candidate is `final/candidate.surface`, ID
`03be4ad7-a36d-45cc-bd9d-280f3e1e24af`, SHA256
`5f48d8e2a16b17ad0c1747d830d0b438aa77c22a9b6654858cb2eb5fd9c8b0ea`.
The paired offline reference ID is `35e71d0c-cac3-42f6-b002-af213f07b4d5`; it does
not replace the deployed reference. Both artifacts and their provenance remain private.

## Commands and continuation

Run from the implementation checkout's `tennis_model` directory with
`UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv`, `PYTHONPATH=src:research`, and
the existing runtime at
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python`.
Use `uv run --offline --no-project --python <runtime> python research/surface_experiment.py
<mode> --run <evidence-directory>`. Modes are `register`, `prepare`, `tune`, `validation`
and `verify`. Registrations and run directories are create-only; do not overwrite them.

Numerical source was frozen through validation. The later serving freeze explicitly
permits only the two default-preserving changes to existing runtime modules,
`model/predict.py` and `model/artifact.py`, plus the newly added research code. The
assessment driver verifies that bridge and the completed numerical/input receipts.
The numerical driver's original `verify` intentionally rejects this later source
inventory. Do not rerun create-only modes into accepted output directories.

Local artifacts use Python 3.13, NumPy 2.5.0, pandas 3.0.3, scikit-learn 1.9.0 and
XGBoost 3.3.0. Production must rebuild with its pinned runtime; these saved local
pickles are not deployment inputs.

Detailed next-session implementation, dependencies, exact artifacts and commands are
in [the integration handoff](2026-09-11-wta-surface-next.md). Full-precision pooled,
half-window and annual metrics are in
[`2026-09-11-wta-surface-comparison.csv`](2026-09-11-wta-surface-comparison.csv);
[`2026-09-11-wta-surface-result.json`](2026-09-11-wta-surface-result.json) records
the decision, model IDs, preservation, source freezes and all 37 new evidence-file hashes.

## Review

All C0–C6 work is complete. Eighty focused tests and the full 1,359-test Python suite
passed; repository Ruff and whitespace checks passed. Final preservation rechecked
all 733 prior files, 17 accepted checkout heads, 294 source/copied raw files, the
unchanged original signal helpers, prepared/numerical/final artifacts and frozen
serving source. There was no failed numerical trial or refit in this round.

Recommend advancing the fixed WTA candidate to production integration because it
meets the existing model gate and has acceptable measured cost. Keep the live
incumbent until the supported training/artifact/export paths, cache recovery and
full/quick/publication/live gates are integrated and verified. Later-year uncertainty,
the small accuracy decrease and the retrospective timing limitation remain explicit.
This recommendation does not imply a production push occurred. No production data,
model default or deployment changed during this offline assessment.
