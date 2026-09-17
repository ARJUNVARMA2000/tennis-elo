# Phase 3 — corrected baseline and saved-model acceptance

Status: **complete; no candidate search or adoption.** Both tours were evaluated
sequentially, then fitted through the normal final-predictor path and checked after
strict save/load. Implementation remains `8be9d74a5ba3d3411c92e9c89d0a3dbfb47dbcfe`
in the isolated coordinator on `codex/model-foundation`. No model code, evaluator,
configuration, dependency, raw input or production output changed in this phase.

The next work is the [Phase 4 preregistration](2026-09-06-phase4-preregistration.md).
Full measurements, identities, costs and file hashes are in
[phase3-result.json](2026-09-06-phase3-result.json). The compact tables are
[metrics](2026-09-06-phase3-metrics.csv) and [fixed slices](2026-09-06-phase3-slices.csv).

## Corrected reference

Five bags, adopted per-tour settings, annual walk-forward folds 2010–2026, Platt
calibration on the preceding year. Every one of the 17 years is scored for both tours;
none needed the early-fold training/calibration reuse fallback. 2026 is partial.
ATP includes lower history in its state; WTA fits each combiner on unchanged main
features and selects enriched test state below the existing main-count threshold 32.

| Tour / window | Matches | Log loss | Brier | Accuracy |
|---|---:|---:|---:|---:|
| ATP 2010–2026 | 46,195 | 0.573954 | 0.196334 | 69.212% |
| ATP tune 2010–2019 | 28,357 | 0.562589 | 0.191364 | 70.411% |
| ATP validation 2020+ | 17,838 | 0.592021 | 0.204236 | 67.306% |
| WTA 2010–2026 | 42,197 | 0.593586 | 0.204403 | 67.648% |
| WTA tune 2010–2019 | 26,794 | 0.590712 | 0.203081 | 67.941% |
| WTA validation 2020+ | 15,403 | 0.598585 | 0.206703 | 67.140% |

Every eligible completed main match **in the frozen selected population** was scored:
zero unexplained exclusions and exact unique match identities. This does not establish
that the selected population contains every real-world match. The Phase 1 independent
WTA catalogue still has unresolved completeness findings.

The private disposition CSVs classify every ATP selected row and every WTA main row,
in this precedence order: non-main, not completed, before 2010, after cutoff, scored.
ATP: 131,413 state-only lower rows, 4,274 non-completed main rows, 103,011 older
completed main rows, and 46,195 scored. WTA main: 3,465 non-completed, 83,316 older
completed, and 42,197 scored. No rows lie after the registered cutoffs. WTA's separate
17,100 lower rows feed only its enriched state. Lower role and source-kind counts are
different classifications and must not be substituted for each other.

## What changed in measurement

Probabilities now average the two independently calibrated player orientations. Holding
these corrected feature frames and fitted models fixed, the paired change versus the
legacy **canonical-name** orientation is:

| Tour | Tune delta log loss ± naive SE | Validation delta ± naive SE |
|---|---:|---:|
| ATP | +0.000697 ± 0.000184 | +0.000608 ± 0.000223 |
| WTA | +0.000656 ± 0.000196 | +0.000136 ± 0.000176 |

Positive means lower loss. These isolate the exchange-policy measurement, not the
combined effect of all temporal corrections, runtime differences or data changes since
the older production artifacts. They are not a newly selected candidate's gains.

Feeding the known winner first into the asymmetric legacy path gives spuriously better
validation losses: ATP 0.580145 and WTA 0.590754. Those numbers cannot serve as honest
reference forecasts. Do not compare old winner-first headline scores directly with the
new table and describe the difference as model regression or improvement.

The existing WTA threshold-32 path versus its corrected main-only reference gives
tune delta **+0.00050337 ± 0.00022856** and validation delta
**+0.00127134 ± 0.00068521**. This satisfies the unchanged historical gate, but it
is an incumbent remeasurement, not a new threshold choice. Validation week-bootstrap
SE is 0.00073675; its 95% interval is [−0.00006764, +0.00277731]. All 29,503 protected
OOS probabilities and all 16,003 pre-2016 OOS probabilities are exactly unchanged.
12,694 OOS rows select the lower branch, including 4,599 validation rows.

## Calibration and remaining evidence gaps

Reliability bins use canonical-name slot A selected before observing the outcome,
one observation per match. Validation ten-bin ECE is 0.00909 ATP and 0.00556 WTA;
these are descriptive bin summaries, not independent tests of calibration.

| Validation favourites with forecast ≥80% | Matches | Mean confidence | Win rate |
|---|---:|---:|---:|
| ATP overall | 3,333 | 86.98% | 86.89% |
| WTA overall | 2,535 | 86.13% | 86.82% |
| WTA low main experience | 952 | 86.51% | 88.13% |
| WTA inactive >120 days | 481 | 86.66% | 88.57% |

These measurements do not support blanket confidence reduction. ATP's no-prior-serve
subset has 128 such favourites averaging 89.19% and winning 84.38%; that small sample
is an exploratory lead, not an established mechanism. Fixed-slice raw losses reflect
match difficulty as well as model errors. WTA grass (1,590 validation matches,
LL 0.61832) and both-top-50 (3,438, LL 0.63117) are useful diagnostics, not proven
sources of removable error. The combiner still improves on both component probabilities
on the same validation rows: ATP component losses 0.60556 / 0.60769; WTA 0.60958 / 0.61019.

Observed WTA serving-stat coverage is 2,077/2,078 in 2024 and 2,003/2,402 in 2025.
The first fraction must be read alongside the unresolved 2024 result gaps; the second
means 399 scored rows lack stats. The Phase 1 figure of 313 concerns a separately
matched catalogue subset, and none of those 313 has usable cached two-player serving
denominators. Acquisition yield remains unknown. The new plan starts with adjudication
and a positive source sample, rather than assuming more scraping will help.

Limitations retained explicitly:

- Event identities are absent for 196 ATP rows (114 live, 82 fresh) and 411 WTA rows
  (404 fresh, 7 live). The fixed evaluator correctly returns unavailable event-block
  uncertainty for full/validation windows. Tune event blocks and all week blocks are
  available. Missing rows are retained; no synthetic grouping or silent deletion was used.
- The frozen slice named `low-main-experience` uses ATP's enriched state counts,
  including lower history. WTA counts are main-only. Cross-tour slice semantics differ.
- OOS date bases: ATP 45,849 unknown / 249 played / 97 event-start; WTA 41,951 unknown /
  233 played / 13 event-start. The benchmark is retrospective event/round ordering;
  historical publication times have not been reconstructed. It is not a certified
  real-time forecast archive.
- No external forecast archive with verified identical pairs, outcomes and horizon was
  available for comparison. The literature bookmaker Brier figure is not a ceiling.
- These validation diagnostics have been observed. Future experiments need tune-only
  selection and independent prospective confirmation, not a claim of untouched validation.

## Real saved artifacts and reproduction

`fit_predictor(tour, save=False)` ran once per tour. Each five-bag schema-5 predictor
was saved to a new private directory and read with `TennisPredictor.load(tour, path)`.
The strict envelope/runtime/state checks remained enabled. The normal final fits use
a 365-day rolling calibration window, not the annual OOS folds: cutoff 2025-09-05;
ATP core/calibration counts 107,207 / 2,788, WTA 92,001 / 2,446.

The private driver wraps the two input builders only to retain and time their unchanged
return values; it calls each original once with unchanged arguments, returns the same
object, and restores the function afterward. No fitted probabilities or parameters are
modified. This allows the independent final-fit feature rebuild to verify all 42 model
columns on all 46,195 ATP and 42,197 WTA scored rows **exactly**. WTA's main/enriched
feature prefix is also exact across 101,848 pre-2016 historical main rows.

Only the first and last folds were refitted for determinism: ATP 2,907 / 2,187 rows;
WTA 2,702 / 1,991. All five saved probability/diagnostic columns matched bit-for-bit.
This establishes repeatability in this frozen runtime, not cross-platform bit identity.

The preserved Phase 0 top-30-liveRank roster gives 435 pairs per tour. Context is Hard,
best-of-three, outdoor, tier 1, round 3, no named venue, as-of 2026-09-06. Independent
scalar A/B and B/A, component, matrix and seeded-permutation calls agreed with maximum
error **1.11e-16** on both tours; pre-save/post-load matrices were exactly equal.

The real receipt producer additionally checked six surface/format contexts (Hard,
Clay, Grass × best-of-three/five), with 36 pair-context observations per tour. WTA
exercised 6 main and 30 lower-branch observations. Private bytes, metadata, artifact UUID,
input generation and timestamps validated at creation. These are archived research
receipts, not permission to publish stale receipts later.

The internal unpaired calibrated classifiers still have mean/max exchange gaps of
0.9865/4.6371 percentage points ATP and 1.4769/7.3811 WTA. The served pair-average APIs
remove those gaps. These raw probes are not directly comparable to older differently
fitted artifacts and are not runtime benchmarks of the corrected APIs.

| Measured seconds | ATP | WTA |
|---|---:|---:|
| Full baseline, including feature construction | 160.45 | 115.86 |
| Independent feature rebuild during final fit | 53.18 | 27.93 |
| Normal final fit, including that rebuild | 58.76 | 34.00 |
| Save and validated load | 0.92 | 0.77 |
| 435-pair multi-interface probe | 11.40 | 7.86 |
| Two-fold deterministic reproduction | 14.86 | 6.16 |

These are measured local costs, not estimates. Read-only diagnostic reporting overlapped
part of the ATP final fit; all model fits themselves ran sequentially. No full baseline
was rerun just for repetition. No source tests were changed. The private drivers passed
syntax/Ruff checks and all real execution assertions; the unchanged Phase 2 product test
suite was not rerun, avoiding unrelated normalized-cache churn.

## Exact artifacts and next-session use

Run root:
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase3`

- `atp-baseline-001/` and `wta-baseline-001/`: registration, completion, full `oos.pkl`;
  WTA also has `wta-main-reference.pkl`. Every registration completed; no failed attempts.
- `atp-final-001/` and `wta-final-001/`: private predictor/envelope, full captured feature
  frames, population-disposition CSV, 435-pair CSV, producer witness and its validation.
  Their `oos.pkl` files contain only the two reproduced folds, not the full baseline.
- `diagnostics-001/`: scores, calibration bins, canonical/paired comparisons, raw exchange
  probes, actual stats coverage, scored keys and missing-event-identity CSVs.
- `logs/` plus `preservation.json`: execution logs and preservation evidence.

Predictor UUIDs: ATP `11ff928d-87d7-42ac-95d0-db281c0b1e24`;
WTA `56a00be7-37d0-41e2-94da-fa2d0fb22139`. Complete payload/envelope/OOS/driver hashes
are in the committed JSON. Do not raw-unpickle predictors or overwrite these run folders.

The accepted freeze remains
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase2/evaluator-freeze-v2.json`,
contract `add41de4629703455fad849c59dfc21a82fa569f13e91970417894127615217d`.
ATP input cutoff is 2026-09-05; WTA enriched cutoff is 2026-09-06 while its main rows end
2026-09-05. Runtime remains Python 3.13.14, NumPy 2.5.0, pandas 3.0.3, scikit-learn
1.9.0 and XGBoost 3.3.0. The private drivers are
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/tools/phase3-final.py`
and `phase3-diagnostics.py` in that same directory. Scratch drivers are intentionally uncommitted.

To verify, run from the coordinator's `tennis_model/` directory:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src \
uv run --offline --no-project --python .venv/bin/python python -m tennis_model.eval.research_run verify \
  --freeze /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/phase2/evaluator-freeze-v2.json
```

Do not rerun Phase 3 by default. Read the Phase 4 preregistration, verify artifact hashes,
then establish a separate candidate/staging boundary. A new source or source-code change
requires a declared new contract, not bypassing this freeze. Phase 4 source adjudication
and uncertainty design may overlap; numerical searches and Phase 5 arbiters remain sequential.

The preserved snapshot's 25,826 files and original project data still match their Phase 0
inventory. All six data roots have distinct file identities; raw/output bytes in all four
worktrees are unchanged. The isolation helper's old Phase 0 normalized comparison is
explicitly excluded from the Phase 3 preservation record; current feature parity is proved
by the real final-fit replays above. No source refresh, candidate adoption, push, collector
or deployment occurred.
