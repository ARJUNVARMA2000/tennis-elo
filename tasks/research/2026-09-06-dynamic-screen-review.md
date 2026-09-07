# Round 4 completion — repaired reference and uncertainty-model verdict

The population repair, eight-setting uncertainty screen and conditional full arbiter
are complete. The selected WTA candidate **passes the unchanged historical gate**.
Its gain is small and not independently confirmed: retain it for further research,
**defer production adoption**, and keep the corrected 42-column research incumbent.
Production code/data have not been deployed or changed by this work.

This follows the [maintenance review](2026-09-06-maintenance-review.md) and the
[registration written before candidate outcomes](2026-09-06-dynamic-screen-registration.md).
The [full result JSON](2026-09-06-dynamic-result.json) contains exact measurements,
the final preservation receipt and hashes of all 61 files in the candidate run directory.
Compact tables: [eight trials](2026-09-06-dynamic-trials.csv),
[metrics](2026-09-06-dynamic-metrics.csv), [years](2026-09-06-dynamic-years.csv), and
[fixed slices](2026-09-06-dynamic-slices.csv). The slice CSV covers all 2010–2026 rows,
not just validation. `ledger.tsv` indexes every trial and the arbiter; the immutable
JSON registrations preceded fitting, while this TSV index was appended afterward.

## Research completed and measured result

Maintenance restored 255 real WTA results and removed 23 duplicate copies plus one
exact invalid self-match. It also corrected timing/availability evidence and rebuilt
both incumbents. The earlier Phase 4 absence counts are superseded; 528 reviewed
catalogue results are not 528 newly added matches. The normalized WTA main population
is 129,209 rows, with 146,309 rows in its lower-enriched history. ATP stays unchanged.
See the maintenance review for outcomes, source hashes, revised counts and exclusions.

The new research adapter adds one antisymmetric `logit_p_dynamic` column to the
existing 42. Its filtered Gaussian strength has global and surface components and
uncertainty that grows during inactivity. The representation, original grid, main-only
fitting population, five bags, calibration policy and threshold-32 selected state were
fixed before screening. No evaluator, dependency, original feature, threshold or
production code path was changed for the candidate.

All eight settings scored the same 26,794 tune-era matches. Positive delta means lower
candidate log loss. Standard errors below are naive paired SEs.

| Initial standard deviation | Daily transition variance | Tune delta ± SE | Decision |
|---:|---:|---:|---|
| 0.5 | 0.000001 | +0.000158361 ± 0.000105939 | Screened |
| 0.5 | 0.00001 | +0.000165526 ± 0.000094424 | Screened |
| 0.5 | 0.0001 | +0.000186466 ± 0.000100333 | Screened |
| 0.5 | 0.001 | +0.000132387 ± 0.000201419 | Screened |
| 1.0 | 0.000001 | +0.000057790 ± 0.000086699 | Screened |
| 1.0 | 0.00001 | −0.000064030 ± 0.000079950 | Screened |
| **1.0** | **0.0001** | **+0.000302865 ± 0.000104815** | **Selected** |
| 1.0 | 0.001 | +0.000282949 ± 0.000212103 | Screened |

The grid took 426.88 seconds against the registered 45-minute cap. Selection was saved
at 2026-09-07 03:27:38 UTC before any candidate validation score was opened. The chosen
setting then ran the full 2010–2026 arbiter in 76.04 seconds. Its tune probabilities
reproduced the selected trial bit-for-bit.

| Window | Paired matches | Incumbent log loss | Candidate log loss | Delta ± naive SE |
|---|---:|---:|---:|---:|
| Tune, 2010–2019 | 26,794 | 0.590649156 | 0.590346291 | +0.000302865 ± 0.000104815 |
| Validation, 2020+ | 15,628 | 0.597198487 | 0.596958494 | +0.000239993 ± 0.000127945 |
| Full | 42,422 | 0.593061889 | 0.592782185 | +0.000279704 ± 0.000081266 |

Both gate inequalities pass: d_tune > 0 and d_validation > −SE_naive. Validation is
positive in five of seven years; the full result is positive in 12 of 17 years.
The validation week-bootstrap SE is 0.000124976 and its 95% interval is
[−0.000014885, +0.000481873], which crosses zero. Event clustering remains unavailable
for validation/full because 411 event identities are missing: one in 2024, 399 in 2025
and 11 in 2026. No matches were dropped or synthetic event groups invented.

The primary loss and Brier improve, but accuracy declines. Validation Brier changes
from 0.206109726 to 0.206024272; accuracy changes from 67.3759% to 67.2031%—27 fewer
correct winner classifications. Stronger years include 2024 and partial 2026, while
2023 and 2025 are negative. The gain does not justify a claim of uniform improvement.
The program's simplicity bias therefore matters: a production integration would add
state and a per-tour feature schema for a small, uncertain benefit. Historical gate
pass and production adoption are separate decisions here.

## Verification and preservation

- Full candidate suite: **1,325 passed** in 140.56 seconds. Focused state/adapter suite:
  **31 passed**. Existing state tests and evaluator assertions remain unchanged.
- Dynamic state was replayed over complete 1980–2026 histories: 129,209 main rows and
  146,309 enriched rows, approximately five seconds per walk. Covariances remained valid.
- Three serialized cutoffs per arm—2009, 2015 and 2018 year ends—each continued 40
  matches exactly. All 240 continued predictions matched; maximum exchange error was
  2.22e-16. Queries did not mutate saved states.
- All original feature columns remain exact after attachment on 129,209 main rows.
  The incumbent selects enriched state on 46,971 of those rows. Disabled five-bag
  2010 and 2018 predictions exactly reproduce the maintenance reference.
- The maintenance final artifacts separately pass strict envelope loading, every OOS
  feature column, 435-pair exchange tests, first/last-fold reproduction and full-prefix
  temporal/pending-prior checks. No state-only prototype bypasses the production loader.
- Final preservation verifies original/coordinator/Phase 4/maintenance data, six distinct
  copies of each original input, all 25,826 snapshot files, and 56 Phase 3, 77 Phase 4
  and 104 maintenance run artifacts. Protected source inventories and candidate freeze
  remain exact. Candidate raw inputs are unchanged.

The first final preservation attempt found four disposable caches replaced by tests:
two empty historical caches and two tiny fixture match caches. Their bytes were preserved
under `test-cache-evidence-001`, then restored from the hash-verified reference copy.
The final candidate data inventory is exact. Scoring read independently hash-pinned
population and feature artifacts, never those test caches; predictions and raw evidence
were unchanged. `cache-restoration.json` records this cleanup explicitly.

## Exact resume locations and immutable identities

Research root: `/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.

| Purpose | Checkout / branch | Code or review commit |
|---|---|---|
| Protected Phase 3 reference | `worktrees/coordinator` / `codex/model-foundation` | `c5cd366` (implementation `8be9d74`) |
| Protected Phase 4 preparation | `worktrees/phase4` / `codex/model-phase4` | `51c9eb1` |
| Corrected research incumbent | `worktrees/maintenance` / `codex/model-population-repair` | code `1fbe42a`, review `975379b` |
| Uncertainty candidate | `worktrees/dynamic-screen` / `codex/model-dynamic-screen` | code/registration `8c4792f` |

Maintenance freeze:
`1f531e2bf3ebb5e771a798e3eee3376a09794e94f721cd04f6230076a612c7ac`.
Candidate freeze:
`20bdae999b8d235028af72a8160276b850211ecd38d4a9ec15a6948f84d93185`.
Selection SHA-256:
`85ba263dbdf914cba8a824f4df9346cc4e1ec22925db9f4115fc7d3cf25158f4`.
The candidate package differs from maintenance only by `model/dynamic_research.py`;
all raw inputs, runtime/configuration, incumbent schemas, cutoffs and evaluator files
match. See `runs/dynamic-continuation/freeze-difference.json`.

The private run directory contains `parity-001`, `tune-01` through `tune-08`,
`selection.json`, `arbiter-001`, and `preservation.json`. Drivers remain private under
`tools/`; their hashes are in registrations and the result JSON. Do not reuse these
exclusive run directories or rerun the grid because this candidate has now seen validation.

To verify the candidate without fitting:

```bash
cd /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/dynamic-screen/tennis_model
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python -m tennis_model.eval.research_run verify --freeze /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/dynamic-continuation/candidate-freeze.json
```

## Remaining work, dependencies and implementation boundaries

1. **Keep the research incumbent fixed.** Preserve both references and all trial outcomes.
   Do not expand this grid, alter the acceptance inequality, or choose another setting
   using the already observed validation years. Any materially different hypothesis
   needs a new registration. No admissible optional-data candidate emerged in Phase 4;
   restoring factual results was maintenance and is already included in the reference.
2. **Prepare a shadow candidate only if continuing this family.** In another checkout,
   build a WTA-specific 43-column final combiner with the fixed selected parameters,
   both Gaussian state bundles, and an explicit research artifact envelope. Preserve
   ATP's 42-column schema and exact probabilities; a global zero-valued extra column
   would still change tree column sampling. Use the frozen full arbiter probabilities
   as the reproduction target. Profile actual query/matrix latency before accepting the
   permanent complexity. This is offline implementation; it need not activate collection.
3. **Mirror state through every serving path.** `model/features.py` and `model/train.py`
   need explicit per-tour schemas; `model/predict.py` must select the same main/lower
   dynamic state, use the requested date without mutation, and provide the new feature.
   Put any adopted parameter overrides in `config.py`. Extend `model/artifact.py` with
   strict state/schema/parameter/population binding and a deliberate version transition.
   Missing dynamic state must reject loading, not silently become a cold state. Add
   serialized past-cutoff and all-feature query parity plus scalar/component/matrix,
   exchange and permutation checks. These implementation and artifact tasks can overlap
   only after the schema/state interface is written down and files are disjoint.
4. **Future confirmation is a distinct phase.** Register a fresh timestamped cohort and
   fixed stopping/interpretation rules before its first candidate forecast. Existing
   retrospective rows cannot be relabeled as prospective evidence. A short pilot will
   mainly test reliability; it may be too small to resolve this tiny accuracy-of-probability
   gain. Independent cohort design can proceed alongside the offline serving work, but
   activation depends on a verified saved candidate. No collector, reminder or automation
   has been activated, and no future dates have been manufactured.
5. **Production integration remains separate.** Decide whether the gain justifies the
   extra state after the above evidence. The tested foundation/population correctness
   repairs can be reviewed independently of uncertainty adoption. Before any merge or
   deployment, reconcile current Git history, run applicable full pipeline/gate tests,
   regenerate the web data mirror and verify the deployed result through the established
   gates. This round neither pushed nor merged to production.

No input was needed to complete this round. Phase 4 and its conditional Phase 5 are
finished; fresh future-data confirmation and production integration are not finished.
