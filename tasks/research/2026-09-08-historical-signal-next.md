# Resume after historical signal experiments

## September 11 completion supersedes the historical next steps below

The population-8 compatibility check and saved-serving assessment are complete.
The fixed WTA surface candidate passes the historical, exact parity and serving-cost
gates. Accepted checkout: `codex/wta-surface-serving` at
`a6771f8f10d299493706b11c90eeb062f5c753cb`, based on accepted production `dda948c`.

Read [the final assessment](2026-09-11-wta-surface-serving.md),
[full-precision results](2026-09-11-wta-surface-result.json), and
[the new production integration handoff](2026-09-11-wta-surface-next.md).
Those documents replace the uncompleted serving instructions and older population-7
artifact references below. Production remains the deployed 42-feature incumbent;
the newly saved research candidate is separate and has not been deployed.

Next: implement the supported WTA 43-feature training/artifact/export paths, cache
recovery and release gates using the fixed candidate. No more numerical candidate
selection or final fit into the accepted evidence directories is needed. The detailed
handoff gives P0–P4 dependencies, exact file locations, validation and release criteria.
Preserve 770 accepted evidence files and 18 accepted research heads in the next round.

## Historical handoff retained for provenance

The bounded numerical round is complete. **SIGNAL-02 passes the WTA historical gate**;
ATP fails its own tune gate. The model is a research candidate, not a deployed predictor.
Read the review, comparison/year CSVs, shortlist and result manifest beside this file.
The immediate next task is serving implementation of this fixed WTA candidate; no new
predictive hypothesis or timing-source survey is required for that work.

## Exact state to resume

### September 10 production integration supersedes the checkout base below

The general correctness release has been pushed as
`c5dc31e2d17a312114efd0f246f81213ef9e4c30`; deployment acceptance is recorded in
[the release receipt](2026-09-10-general-release.md). Check that receipt before
continuing. Create the next implementation checkout from the latest accepted
`origin/master`, with population **8** and inference schema **5**, rather than from
the older historical-signals tip. The older tip and artifacts below remain the
immutable evidence for the completed experiment, not the new production base.

Port only the fixed WTA surface signal and its required research/serving helpers.
Preserve the production recovery, identity, chronology, benchmark and release-gate
fixes. Do not merge the older research branches wholesale or load their population-7
artifacts as production predictors. Keep the 60-day feature definition, five bags,
threshold32 and model settings fixed.

Because the combined production population and corrected baseline differ from the
original experiment, first register a compatibility check against that baseline.
Rebuild the incumbent/candidate on the same frozen population-8 inputs, evaluate
2010–2019, and apply the existing advancement rule before checking 2020+. Keep this
separate from the preserved original results; do not change the signal in response
to later-year results. Saved-route parity and serving-cost acceptance below still
apply before any future adoption. This release does not adopt the surface candidate.

`R = /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Latest checkout `R/worktrees/historical-signals`, branch `codex/model-historical-signals`.
Base `c658c7149676a2e1f6032a1440e68f904bd692e6`; source freeze `755342d`.
Resolve the branch's final acceptance tip before creating another isolated checkout.
Original DEUCE receives only documents/logs. No new final predictor artifact exists.

Continue using the corrected maintenance WTA incumbent:
`R/runs/maintenance/wta-final-001/predictor.pkl`, SHA256
`8cf280c43f813a6944244d585248af8d5fcbc1ff628e535f98d4e10866730e34`.
The older uncertainty shadow is separate and remains unchanged:
`R/runs/prospective-shadow/migration-001/candidate.shadow`, SHA256
`43dd88b1461913f11b90b6d2aa6aa82f7bbfe3ba7ad597d978c6a46b73d45fcc`.
Do not combine the two 43-column candidates or use one as the other's reference.

Preservation: combine `R/runs/historical-signals/protected-run-files.json` (696 files)
with this round manifest's 37 `runFiles` for **733**. Verify the sixteen prior checkout
heads in setup/result and add this round's final accepted tip as the seventeenth.
The entire inherited production package is unchanged from historical-errors, whose
sole difference from the older frozen package is the default-preserving point-state hook.

## Reconstruct the actual experiments

`R/runs/historical-signals` contains setup/protected manifests, diagnostic registration
and source hashes, diagnostics.csv, prepared.pkl, recovered diagnostic summary plus its
retained partial JSON, shortlist registration, experiment freeze, real parity receipt,
focused-test output, and:

- `baseline-replay-001`: exact 26,794-row control.
- `tune-01`, `tune-02`, `tune-03`: separate form/surface/rank trials, each with a registration,
  OOS pickle and full metric/fold receipt.
- `selection.json`: locks SIGNAL-02 before new validation.
- `arbiter-wta-001`, `arbiter-atp-001`: full OOS, final temporal states and frozen paired reports.
- comparison.csv, years.csv, uncertainty.json, acceptance.json: independently re-derived results.

Private create-only drivers: `R/tools/historical-signal-diagnose.py`,
`historical-signal-experiments.py`, `historical-signal-record.py`,
`historical-signal-closeout.py`. Their hashes are retained. Do not rerun into accepted
output directories. The experiment driver reuses only verified input loading/metrics
from the preserved `historical-experiments.py`; its hash is part of the freeze.

Inputs remain in `R/runs/maintenance`: `population-004/wta-main.pkl`,
`wta-enriched.pkl`, `wta-final-001/features-main.pkl`, `features-enriched.pkl` and
`wta-baseline-001/oos.pkl`, verified against their population/final/baseline receipts.
ATP uses enriched history with its incumbent prior policy; no new prior population was used.
Keep pre-2010 rows for state/training; never use later-year errors to redefine these signals.

From the new checkout's `tennis_model` directory, the existing offline runtime is:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src:research uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python -m pytest -q tests/test_historical_signals.py tests/test_historical_errors.py tests/test_historical_candidates.py tests/test_temporal_features.py tests/test_features.py tests/test_probability.py tests/test_research_protocol.py
```

## Next implementation, in dependency order

1. **Freeze serving acceptance before editing.** Append a plan; create an isolated checkout
   from this round's accepted tip. Verify the 733 files and reference artifacts. Fix the
   candidate to `FEATURES + ['surface_recent_diff']`, exact 60-day completed-match count,
   WTA threshold32, five bags, unchanged model parameters/calibration. No predictive sweep.
2. **Build an explicit saved WTA candidate.** `research/historical_signals.py` already
   provides the state/query mirror; `research/signal_combiner.py` supplies orientation,
   paired probability and five-bag fold fitting. Reuse the structure of
   `src/tennis_model/model/dynamic_shadow.py`, especially its `_feature_dict`,
   `feature_columns`, `_combiner_probability` dispatch and final split, while using a new
   surface-specific schema/provenance. The existing uncertainty artifact validator is
   deliberately specific; do not relabel a surface artifact as a dynamic shadow.
3. **Fit once and retain a separate artifact.** Fit only main-state completed WTA rows
   since 1991, with the incumbent final split (last 365 days calibration) and
   `train.FINAL_TRAIN_SEED`. Carry both main and enriched temporal states. Select the
   matching signal state using `TennisPredictor._states_for` for each matchup, including
   unknown/new players. The ordinary 42 columns come from the same selected bundle.
   Surface queries need names, current surface and as-of date; rank metadata is irrelevant
   to this selected feature. If storing only surface state to reduce size, require exact
   equivalence with the frozen full SignalState on real prefixes and all queries.
4. **Prove serving parity before changing defaults.** Test scalar probability, predict,
   component/evidence output, pair matrices, evidence matrices, serialization/reload,
   player-swap complementarity, unseen players, inactivity and both state routes.
   Match all 43 query features before/after save; distinguish historical learned-state
   parity from current metadata snapshots. Preserve default ATP/WTA artifact behavior.
   Verify exact frozen OOS replay if any training/adapter implementation is moved.
5. **Measure cost and make an explicit adoption decision.** Benchmark representative
   singles and 30-player matrices, artifact size and memory against the corrected incumbent.
   Run focused and applicable full tests. Record the modest gain and its validation week95
   interval [−0.000132157, +0.001177076]; passing the historical gate is not certainty.
   Do not change production defaults merely because the research artifact can load.

Steps 2–4 depend on 1; 3 depends on 2, and full saved-predictor route checks depend on 3.
Test fixtures and the cost-measurement harness can be prepared alongside the wrapper,
then executed against the same frozen artifact. Documentary review of the already fixed
ranking-trend runner-up can run independently, but a new model-comparison round requires
its own registration. No parallel agents are implicitly authorized by this description.

## Remaining research, separate from serving

- **Ranking trend remains eligible, not rejected.** It gained 0.000392500 ± 0.000121949
  in tune, with 8/10 positive years and both halves positive. It lost the registered
  finalist ranking. No 2020+ prediction for it was computed. Preserve that distinction;
  do not silently add a fallback validation or surface-plus-rank combination here.
- **Recent form failed consistency.** It gained 0.000230527 pooled, but only 5/10 years;
  its week95 barely crosses zero. Do not reinterpret that as a replacement-qualified model.
- **ATP surface setting failed tune.** Positive later-year performance cannot override
  the fixed gate. No immediate ATP deployment or parameter expansion.
- **Prospective timing remains independent.** Existing source evidence and uncertainty
  shadow are preserved. Serving implementation can proceed without resolving the physical
  timing gap; future trusted observations would strengthen confirmation of any adoption.
