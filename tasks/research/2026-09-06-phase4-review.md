# Phase 4 — source audit and uncertainty prototype

Status: **preparation completed to the registered correctness stop; candidate screening
is deferred. No candidate was selected, adopted, or deployed.** The missing-result audit
proved a population defect, so the Phase 4 preregistration requires maintenance and a new
reference before model comparisons. A second defect prevents full-history dynamic replay.

Continue with the [maintenance and resume plan](2026-09-06-phase4-maintenance-plan.md).
Exact counts, checks, hashes and private attempt paths are in
[phase4-result.json](2026-09-06-phase4-result.json).

## What changed

Implementation lives in the separate `codex/model-phase4` checkout at
`.research/2026-09-06-model-foundation/worktrees/phase4`, branched from coordinator
`c5cd3669d94fb93b7b0914e96bb28253d9e990a4`. The coordinator retains the Phase 3 baseline.
The original checkout receives only this documentation handoff.

The only package addition is `tennis_model/ratings/dynamic.py`: a research-only filtered
Gaussian strength state, its JSON query-time mirror and one optional `logit_p_dynamic`
feature. There are no production imports or changes to the evaluator, 42 incumbent
features, configuration, dependency versions, strict schema-5 predictor loader, inputs,
output JSON, web app or deployment. The separate implementation freeze is a preparation
snapshot, **not** an admissible scored candidate or replacement baseline.

## Result completeness

The accepted audit is `runs/phase4/adjudication-003`. It reads the preserved 2024/2025
WTA caches and the corrected normalized frame. It uses event edition and numeric provider
ID, verified player aliases, exact match IDs, and actual player pairs within event dates.
It does not join event names. Conflicting score, round, role, winner and repeated identity
are separate dispositions. A finished marker alone does not certify a completed match.

The corrected 2024 cached universe has 2,192 finished singles records: 522 absent
(515 with a legal completed score, seven with incomplete scores), 1,649 present,
13 ambiguous, one round conflict and seven score conflicts. These are audit dispositions,
not a claim that the cached calendar itself is complete. The six registered event samples:

| 2024 WTA event | Absent, complete score | Absent, unresolved score | Present | Other conflict |
|---|---:|---:|---:|---:|
| Roland Garros 903 | 125 | 2 | 0 | 0 |
| US Open 905 | 122 | 5 | 0 | 0 |
| Madrid 1038 | 93 | 0 | 1 | 0 |
| Rome 709 | 88 | 0 | 3 | 1 |
| Miami 902 | 85 | 0 | 3 | 0 |
| Auckland 1049 | 0 | 0 | 31 | 0 |

Five staged ESPN historical scoreboards corroborate **491 absent completed results**
(119 RG, 115 US Open, 90 Madrid, 86 Rome, 81 Miami), with the same canonical pair,
winner, round and games score. This is a conservative verified minimum; 22 other
complete-score rows in those five events remain unmatched by the second-provider
identity policy. Several use unresolved provider name variants; no fuzzy aliases were
invented. Two absent complete-score rows are outside the six-event pilot. The two
providers may share upstream information; this is publication corroboration, not proof
of independent data generation.

The seven incomplete WTA score records remain outside that 491 count. ESPN explicitly
marks five retirements and one walkover; one remains unmatched. Preserve the separate
outcome evidence, even where its score disagrees with WTA's empty string. Do not turn
all seven into ordinary completed training examples.

The current source path explains the omission: `wta_stats._stats_row` emits nothing
without usable serving statistics, and `scrape_tournament` skips such responses. The
results merger reads those emitted CSVs, not a complete historical match-list ledger.
Its assumption that the stats overlay fills every archived gap is false for these rows.
Restoring their results is data maintenance, not evidence that a model has improved.

The [official US Open draw](https://www.wtatennis.com/tournaments/905/us-open/2024/draws)
also supplies a public result witness. Machine-readable provider responses, request URLs,
byte hashes and the actual pair-level checks are retained in research staging.

## Corrections to the earlier audit

The Phase 1 figure of 555 unmatched 2024 rows was a lead, not an acceptance list.
A cache directory called `2024` also contains 2025 Auckland/Brisbane editions. Provider
match IDs repeat across years. Audit on the record's event year and reconcile the event
header; never infer edition from the directory. Numeric IDs can be zero-padded (`0902`
versus `902`), and verified name aliases must be applied at both sides of the join.
The original Phase 1 artifacts remain preserved; this review supersedes their interpretation.

The positive-stat 2025 “missing” case is Jessica Pegula–Mayar Sherif Ahmed Abdelaziz,
US Open `LS63131461`. It already exists with statistics under the verified Sherif alias.
It supplies no new usable row. The corrected full 2025 audit has seven absent rows,
16 ambiguous rows and seven score conflicts; those outside the pilot remain leads.

## Acquisition feasibility

The fixed completed-match sample has five 2025 missing-stat matches each at the Australian
Open, Roland Garros and Wimbledon. US Open has zero eligible completed missing-stat rows
in this matched subset; its remaining missing-stat entry is not an ordinary completed
match. All **15/15** sampled completed results were corroborated in ESPN's historical
scoreboards, but **0/15** had serving statistics: both competitors' statistics arrays were
empty. This demonstrates zero yield from that endpoint, not from every possible ESPN
product. A TNT match-page check also exposed no usable denominators. Do not reclassify
an HTTP 200 or a match header as a recovered box score.

A bounded 2015 WTA pilot fully paged 673 calendar entries and identified six WTA125 events.
The two earliest (1077 and 1083) returned HTTP 200 with zero match records. No earlier
history for a named main-tour entrant was demonstrated. The remaining four events and
other sources were not exhausted; the result is limited no-yield evidence, not proof
that pre-2016 history does not exist. No ITF integration or paid acquisition was started.

All requests were sequential and staged outside model inputs. No 429 occurred. There is
no admissible data candidate: current recovery is population maintenance, the serving
pilot produced no usable totals, and earlier history was not demonstrated. A 2024/2025-only
optional intervention would also have zero effect on the unchanged 2010–19 tune gate.

## Uncertainty prototype and checks

Each player has global logit strength plus Hard/Clay/Grass deviations, with mean zero and
prior covariance `sigma0² diag(1,.25,.25,.25)`. Elapsed days add
`q * days * diag(1,.25,.25,.25)` to a copied covariance without mean drift. Match probability
integrates the logistic function over the projected Gaussian strength difference.
After the result, a powered logistic likelihood is moment-matched and projected back to
both players. Within-player covariance is retained; cross-player posterior covariance
is deliberately discarded. The likelihood power uses the existing tier weight and WTA
retirement multiplier 0.72, with the incumbent walkover policy. No future smoothing or
new historical ranking initialization is used.

The first 20-node integration had 0.03031 absolute probability error at mean -2 / variance
100 against an independent numerical reference. Before any outcome scoring, it was replaced
by 64-node Hermite integration at variance <=4 and adaptive integration above that boundary.
Tests compare both probability and posterior moments with independent integration.

The real full-history attempt correctly failed on one raw self-match:
`data/raw/wta/historical/1980.csv:2597`, event `1980-1040`, 1980-04-30,
Marcie Louie versus Marcie Louie, both source IDs `200358`, score `6-2 4-4 RET`.
No opponent was invented and the row was not silently skipped.

A separately registered, cold-initialized **contiguous 1991–2019 interval** passed:

- Main replay: 81,314 rows / 3,346 players, 2.780 seconds.
- Enriched replay: 85,299 rows / 3,652 players, 2.909 seconds.
- Three saved cutoffs per arm (end-2009, end-2015, end-2018), 40 continued rows each:
  all 240 probabilities exactly match the walk; maximum exchange error 2.22e-16.
- All 81,314 original feature rows remain exact after attachment; threshold-32 selection
  uses the incumbent's main-only counts. No alternative gate or feature representation.
- Disabled incumbent path: 2010 five-bag refit, 2,702 probabilities bit-identical to
  Phase 3; fitting took 2.725 seconds. This is a baseline reproduction, not a candidate fit.
- 108 targeted tests passed in 2.69 seconds, including 25 prototype tests; lint passed.

This certifies the bounded interval and the disabled path, **not** full-history candidate
readiness. No eight-setting search, candidate loss comparison, validation selection or
new production predictor occurred. The registered grid remains unchanged for after
maintenance. The limited replay must never be relabeled as a full-history model experiment.

## Preservation and remaining work

All original project data, all coordinator data, snapshot bytes and Phase 3 run artifacts
were rechecked. Candidate raw inputs and outputs are unchanged; only two disposable WTA
normalized caches changed. Each copied data file has a distinct inode. The new package
source contract differs only by the isolated dynamic module.

Next: adjudicate and repair population defects, add independent completeness/self-match
gates, review estimated timestamp semantics, create a versioned population/reference,
then repeat full-history parity and run the eight tune-only settings. Phase 5 full
candidate evaluation, Phase 6 future confirmation and Phase 7 integration remain later
work. Follow the linked maintenance plan for exact sequencing and completion gates.
