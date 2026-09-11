# Fixed WTA surface candidate after the correctness release

Status: tuning and fixed 2020+ validation accepted; saved-predictor assessment in progress.
This is one compatibility experiment followed by serving assessment. Production remains
the accepted 42-feature model.

## Reproducible starting point

- Production base: `dda948c8dfb0b2bb4d2ad0d205508d4e66cd7ef8`.
- Numerical implementation freeze: `61d822c` on `codex/wta-surface-serving`.
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

## Serving acceptance, registered before measurement

If validation passes, fit one separate 43-feature WTA artifact using the incumbent
final split (last 365 days calibration), final seed and main-only training population.
Keep the main/enriched signal states alongside the corresponding ordinary states.
One common inference dispatch must supply the 43 columns across every prediction
route; ordinary predictors must retain their exact 42-column behavior.

Use an explicit surface artifact schema outside production output. Its bounded header
pins runtime, code, parameters, ordered features, inputs, selection and both temporal
states before deserialization; typed structure and state receipts are rechecked afterward.
Production readers and destinations must reject it. Check interruption, symlinks,
wrong provenance, tampered bytes, altered states and swapped state bundles.

Test scalar, component, grouped-evidence, score-distribution and matrix routes, both
WTA state selections, new players, inactivity, reversal/permutation, and exact save/load
equality. Compare all 43 query features across serialization and the ordinary 42 against
the reference's selected bundle. Distinguish this from historical metadata equality.

The serving registration fixes 30 representative players: 20 with main experience
and 10 eligible for the lower state, chosen by match counts with name tie-breaks.
Measure all three surfaces, 100 scalar pairs, two warm-ups and nine measured rounds,
alternating candidate/reference order. Report median/p95 latency, artifact bytes and
three fresh-process memory measurements. Median latency, artifact bytes and peak
process memory must each stay within 2x the paired reference. The adoption recommendation
must account for both numerical uncertainty and these implementation costs.

## Commands and continuation

Run from the implementation checkout's `tennis_model` directory with
`UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv`, `PYTHONPATH=src:research`, and
the existing runtime at
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python`.
Use `uv run --offline --no-project --python <runtime> python research/surface_experiment.py
<mode> --run <evidence-directory>`. Modes are `register`, `prepare`, `tune`, `validation`
and `verify`. Registrations and run directories are create-only; do not overwrite them.

Numerical source hashes remain frozen until validation completes. Serving code will
have a later, separate freeze. Preserve the completed numerical evidence when adding
that code. `serving-registration.json` and the prepared draft artifact tests are in
the evidence directory. Do not deploy or merge an old research branch wholesale.

## Review

Serving implementation passes 80 focused tests and the full 1,359-test Python suite;
repository Ruff and whitespace checks pass. Real prepared states pass structural
preflight and share the ordinary states' 2026-09-10 cutoff. The final two fits,
real saved-route parity, cost measurements and recommendation remain pending.
