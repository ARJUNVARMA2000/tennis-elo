# WTA uncertainty continuation — registration before candidate outcomes

Continue the original Phase 4 representation and eight-setting grid after the reviewed
population repair. The maintenance reference is implementation
`1fbe42a3e5c900b6b76594032e5f46b1054adbaa`, freeze
`1f531e2bf3ebb5e771a798e3eee3376a09794e94f721cd04f6230076a612c7ac`.
Its WTA incumbent scores 42,422 completed main results. The new checkout is
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/dynamic-screen`,
branch `codex/model-dynamic-screen`, with 18,791 byte-identical, distinct copied inputs.
No production code path imports the new adapter.

`ratings/dynamic.py` remains unchanged from Phase 4: filtered global and three surface
Gaussian components, quarter-scaled surface prior/transition variances, powered logistic
observations and deterministic quadrature. It discards cross-player posterior covariance.
Existing retrospective chronology, tier weights, retirement multiplier and walkover
policy remain. There is no smoothing or initialization from future outcomes/profiles.

`model/dynamic_research.py` defines `dynamic-combiner-research-v1`: the original ordered
42 features plus `logit_p_dynamic` as the last, antisymmetric column. Production schema
validation rejects this input. Disabled orientation, fitting and probability routes
delegate to the incumbent functions. Enabled probabilities use the same average of
calibrated forward and reversed-player predictions, with no extra clipping or tuning.

For each annual fold, fit only completed main-state rows from 1991 through the preceding
year. Core training excludes the calibration year, calibration uses that immediately
preceding year, and the incumbent's fewer-than-500/fewer-than-2,000 warm-up fallback
remains. Five bags retain orientation seeds year + 100,000*k, calibration orientation
seed year + 1, adopted WTA tree parameters, tree seeds, early stopping and Platt fit.
Score the same threshold-32 selected state as the incumbent; main counts and all
original feature columns/identities remain baseline-owned. Only the added dynamic
signal follows the selected main/enriched branch. Thresholds are not searched.

The full suite passes 1,325 tests; the focused state/adapter suite passes 31. Existing
Phase 4 state tests and evaluator assertions are unchanged. Initial test attempts are
retained: an incorrect test filename, then a new synthetic fixture that accidentally
changed round identity while perturbing features. The fixture now changes only signed
signals, and the pairing guard remains strict. The new tests live in
`tests/test_dynamic_combiner.py`; the existing `test_dynamic_research.py` is intact.

Before fitting, create a new candidate freeze and run full-history state parity on
both WTA populations. Check saved/loaded cutoffs 2009-12-31, 2015-12-31 and 2018-12-31,
40 continued results per cutoff/arm, nondestructive queries, exact feature attachment,
and disabled five-bag 2010/2018 probabilities versus maintenance. The 2018 fold also
exercises the lower-state selection. No candidate losses are reported by these probes.

Run these eight tune-only settings in this exact order:

| Trial | Initial global standard deviation | Daily global transition variance |
|---|---:|---:|
| 1 | 0.5 | 0.000001 |
| 2 | 0.5 | 0.00001 |
| 3 | 0.5 | 0.0001 |
| 4 | 0.5 | 0.001 |
| 5 | 1.0 | 0.000001 |
| 6 | 1.0 | 0.00001 |
| 7 | 1.0 | 0.0001 |
| 8 | 1.0 | 0.001 |

Keep full pre-2010 warm-up; candidate fitting/scoring sees only 2010–2019 test years
during screening. The 45-minute cap prevents starting another trial after expiry.
A failed or incomplete grid stops selection for review. Every trial has an exclusive
registration and completion/failure record; no earlier attempt is overwritten.
Select the greatest strictly positive mean tune log-loss delta, with earlier grid order
breaking exact ties. Otherwise reject the family without candidate validation scores.

If one setting qualifies, freeze `selection.json` before the full arbiter. Use all
2010–2026 scoreable rows through the unchanged WTA cutoff 2026-09-06, five bags, and the
existing paired evaluator. Require bit-exact reproduction of the selected tune
probabilities. The acceptance inequality remains d_tune > 0 and d_validation > −SE_naive.
Report validation sign, week clustering, event clustering availability and predefined
slices separately. An event-identity gap must not be filled with invented groups.

Private run root: `runs/dynamic-continuation` beneath the research root. Drivers are
`tools/dynamic_screen.py` and `tools/dynamic_parity.py`, whose exact hashes enter each
registration. They verify maintenance population/frame/prediction hashes before use.
The candidate freeze must have exactly the maintenance raw-input hash and only the
declared package addition. All numerics run sequentially. Future confirmation and
production integration remain separate; no deployment or prospective collection is
authorized by this screen.
