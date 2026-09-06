# Phase 4 preparation — registered next work after Phase 3

Status: **registered preparation plan; implementation has not started.** Both Phase 3
baselines and real saved-artifact checks passed. No candidate has run.

Read the [Phase 3 review](2026-09-06-phase3-review.md) and
[machine-readable results](2026-09-06-phase3-result.json) for the accepted reference.

The corrected reference uses implementation `8be9d74` and freeze contract
`add41de4629703455fad849c59dfc21a82fa569f13e91970417894127615217d`.
Read the Phase 3 review/result, Phase 1 data audit, current `PROGRAM.md`, and the
do-not-retry table in `ideas.md` before implementation. The old headline scores and
literature bookmaker anchor are not headroom estimates for these rows.

## Decisions from the measurements

1. Put source completeness first. WTA 2024 has only 2,078 scored matches despite
   99.95% observed-row serving-stat coverage. Phase 1 independently found 555 unmatched
   catalogued results, not 555 verified missing eligible matches. A nearly complete
   statistics percentage over an incomplete population is misleading.
2. WTA 2025 has 399 scored matches without serving stats; 313 belong to the separately
   matched first-party audit subset. These are different denominators. The existing cache
   has no positive whole-match serving denominators for those 313 cases. Do not re-scrape
   the same endpoint and assume it will fill them.
3. Preserve the existing WTA lower-state gate. Corrected validation improvement versus
   main-only is +0.00127134 ± 0.00068521 naive SE; week-bootstrap SE is 0.00073675 and
   its 95% interval crosses zero. It is useful incumbent evidence, not decisive independent
   confirmation. All 29,503 protected rows and 16,003 pre-2016 rows are exactly unchanged.
4. Do not treat global overconfidence as established. WTA validation favourites priced
   at 80% or higher average 86.13% and win 86.82%. Its low-main-experience subset averages
   86.51% and wins 88.13% over 952 such matches. An indiscriminate uncertainty discount
   could worsen this. Any uncertainty prototype must earn a tune-era signal.
5. High raw loss in WTA grass or top-50 matchups is not evidence of removable error;
   those matches can simply be harder. These remain diagnostic slices, not selection
   objectives. ATP's named low-main-experience slice actually uses enriched state counts;
   do not compare that slice directly with WTA's main-only counts.

## Sequence and parallel work

| Step | Depends on | Can overlap | Completion condition |
|---|---|---|---|
| P4-0: establish candidate workspaces and immutable registrations | Phase 3 completed | Nothing writes baseline inputs | Baseline hashes verified; distinct candidate/staging paths recorded |
| P4-A1: source/result adjudication | P4-0 | P4-B1 design and synthetic checks | Every sampled row has a reasoned disposition and provenance |
| P4-A2: bounded source acquisition | A1 demonstrates a real gap and viable source | B1; reporting | Positive-denominator sample or explicit no-yield result |
| P4-A3: freeze one data candidate | A1/A2 plus tune-period relevance | B1 implementation | Candidate manifest, exact common keys, no-intervention parity |
| P4-B1: uncertainty state design and parity | P4-0 | A1/A2/A3 | One declared representation, temporal/state tests and measured runtime |
| P4-B2: tune-only bounded screening | B1 | Read-only documentation | At most 8 registered settings, one selected before validation |
| P5-A: full data arbiter | A3 | Read-only reporting only | Completed paired verdict or explicit no admissible candidate |
| P5-B: full uncertainty arbiter | B2 and P5-A decision | Read-only reporting only | Compared with actual incumbent after P5-A |

Numerical searches and full arbiters stay sequential. Parallel work means independent
staging/design work; it does not authorize competing edits or simultaneous fitting.
No prospective collector, external messages, paid feed purchase or deployment is included.

## P4-0 — preserve the measurement boundary

- [ ] Keep the coordinator baseline code/data and Phase 3 runs unchanged. Create a
      separate candidate checkout from the reviewed Phase 3 coordinator commit; copy
      inputs with distinct files, never symlink writable data back to the baseline.
- [ ] Append checkable steps and the current authorization to that checkout's todo tail.
      Record exact branch, source/input/runtime hashes and an exclusive attempt directory.
- [ ] Keep `eval/`, `PROGRAM.md`, existing test assertions and adoption inequalities
      unchanged. The current freeze's field called `evaluatorSHA256` hashes the entire
      package, not just `eval/`; candidate code changes therefore require their own new
      contract, with explicitly declared differences and separately verified identical
      evaluator files. Never overwrite or relax the Phase 2 freeze to accept a candidate.
- [ ] Candidate artifacts/frames have their own manifests. Retain Phase 3 OOS as the
      common campaign reference; verify byte hashes before using them. A changed cutoff
      or scoring population requires a fresh paired reference, not headline subtraction.
- [ ] Before any code experiment, establish that its disabled path reproduces the
      incumbent. For data experiments, a no-op staged input must reproduce identical
      normalized membership, features and probabilities.

## P4-A1 — result completeness pilot (90 minutes, no numerical search)

Hypothesis: some apparently absent WTA 2024 main results are recoverable from already
cached first-party match records; their admission or state effects are not yet established.

- [ ] Start with event IDs 903 and 905 in 2024 (127 unmatched catalogue rows each in the
      Phase 1 audit). Recompute matching against the Phase 2 corrected normalized frame;
      the earlier unmatched count is an audit lead, not a current acceptance list.
- [ ] Use `data/wta_stats.py`, `data/results.py`, `data/events.py` and
      `data/chronology.py` as the current contracts. Join on year/event/match ID and real
      player pair; only use the declared exact-pair/round/date-overlap fallback when IDs
      are unavailable. Inspect adjacent calendar years; never use event-name similarity.
- [ ] Adjudicate completed, retired, walkover, duplicate, ambiguous identity, date conflict,
      already present, genuinely absent and unresolved cases separately. Preserve original
      bytes/file hash, normalized player IDs, source IDs, score, role, played/date basis,
      first-available evidence and retrieval time. Retrieval today is not historical availability.
- [ ] Emit row-level CSV/JSON and counts with explicit denominators. Then extend to the
      remaining four named Phase 1 event samples only if the first two resolve cleanly.
- [ ] If a proven population correctness defect exists, stop candidate scoring and record
      a maintenance design: preserve old artifacts, repair with a population-version boundary
      when membership changes, add integrity tests, and establish a new paired baseline.
      Do not present restoration of omitted factual results as an arbiter-approved model gain.
- [ ] If this is optional state enrichment instead, count affected incumbent match keys
      separately in 2010–19 and 2020+. A 2024-only intervention has zero tune effect and
      cannot pass the unchanged strictly-positive tune gate. Find justified historical
      coverage or record the candidate ineligible; do not spend an arbiter to discover this.

## P4-A2 — serving-stat and older-history feasibility (60 minutes per source pilot)

Hypothesis: a distinct source can recover valid two-player serve totals for proven gaps,
or useful strictly earlier lower history for currently cold entrants.

- [ ] Inspect the one unmatched 2025 cached result with positive denominators identified
      by Phase 1. Resolve its identity, outcome and role before calling it usable.
- [ ] For the 313 matched 2025 gaps, take a fixed sample of up to five per Slam (all if
      fewer exist). Record exact selected IDs before querying a distinct source. A successful
      response needs both players, the completed result and positive internally consistent
      serving denominators, not a 200 response or a populated match header.
- [ ] Acquisition must run only in staging, one year at a time using validated existing
      adapter contracts. Record requests, failures, 429s, bytes, elapsed time and usable
      unique rows. Stop on rate limiting; do not add concurrency or retry indefinitely.
- [ ] A lower-history alternative must identify a missing event universe and demonstrate
      strictly earlier evidence for named main entrants. Existing WTA lower history starts
      in 2016; missing pre-2016 rows are not inferred from the current cache's absence.
- [ ] Require a viable ongoing update path before expansion. With no positive sample,
      return a documented no-yield result. ITF integration and paid feeds stay separate.

## P4-A3 — exactly one data candidate (60-minute preparation budget)

- [ ] Register the source, years, admission rules, immutable staged-input hashes, expected
      affected keys, target slice, exclusions and all manually adjudicated cases.
- [ ] First isolate state effects on identical scored matches and an unchanged combiner
      training/calibration path. WTA main counts and threshold 32 remain baseline-owned;
      only the declared enriched-state path may change. Freeze league/surface priors to
      the same admitted main population. An optional new main-result row cannot quietly
      enter combiner fitting or the shared priors through a helper's default.
- [ ] Prove no-op input parity, exact pre-intervention probabilities, exact protected-WTA
      probabilities and no query-before-availability effect. Record newly forecastable
      matches separately from the paired score. If the design cannot preserve these,
      register a different experiment before fitting rather than relabel it afterward.
- [ ] Add serialization/cutoff parity for any new state or availability metadata. A data
      candidate is not complete merely because the normalizer accepts its rows.
- [ ] Freeze one candidate for P5-A, or record why none is admissible. No gate/threshold
      sweep, missing-value policy sweep or broad retraining variant is bundled into it.

## P4-B1 — uncertainty prototype (four-hour implementation cap before re-planning)

Hypothesis: filtered strength and uncertainty can improve learning from sparse or changing
player histories beyond the incumbent's dynamic K/form features. This is exploratory;
Phase 3 does not establish that uncertainty shrinkage is beneficial.

- [ ] Start WTA-only, with a past-filtered per-player global mean plus three surface
      deviations and a small covariance state. Shared global strength gives surface partial
      pooling; uncertainty increases with elapsed days before the next observation.
- [ ] Before fitting, write down the observation likelihood, approximate update, prior,
      transition, surface covariance, same-day ordering, retirement/walkover policy and
      cold-player behavior. Prefer one transparent Gaussian/logistic filtering approximation
      implemented with existing numerical dependencies. State any ignored opponent
      covariance explicitly. Never smooth earlier player states using later outcomes.
- [ ] Keep the existing result/role and retrospective chronology policies. Do not use
      current rankings, current chart profiles or future event statistics to initialize a
      historical state. Respect WTA's existing main/enriched state selection.
- [ ] Commit one representation before screening: one complementary antisymmetric
      `logit_p_dynamic` signal, with the rest of the feature set and fitted-policy settings
      unchanged. Do not compare replacement, blending and many extra uncertainty columns
      and report only the winner. Any departure needs a new registration before measurement.
- [ ] Add tests for equal-player symmetry, exchange, deterministic replay, updates after
      outcomes only, uncertainty growth without mean drift during inactivity, covariance
      validity, a future-row perturbation leaving the past unchanged, and the disabled
      path exactly matching the incumbent. Disabled means bypassing the new model path,
      not assuming an added zero feature leaves column-sampled trees unchanged.
- [ ] Supply a query-time state mirror and real cutoff/serialization parity before full
      evaluation. Prototype privately; new state/feature contracts cannot be loaded by
      disabling the strict schema-5 artifact checks. Plan a versioned integration only
      if the candidate earns it.
- [ ] Profile a representative replay and one fitting fold. Stop and re-plan if the
      implementation exceeds the declared cap or cannot replay within practical budgets.

## P4-B2 / Phase 5 — screening and decisions

Use exactly eight tune-only settings: initial global standard deviation in logit units
`sigma0 ∈ {0.5, 1.0}` crossed with daily global transition variance
`q ∈ {0.000001, 0.00001, 0.0001, 0.001}`. Surface prior and transition variances are
fixed at one quarter of the corresponding global variance; all initial means are zero.
These are proposed settings, not fitted estimates. Record the filtering equations and
likelihood approximation before the first replay; do not expand the grid after seeing
results. If design review invalidates these units or ranges, supersede this registration
explicitly before any numerical screening. Budget 45 minutes;
use the measured clock, preserve every setting and failure. Pick one on 2010–19 only.
If the prototype cannot beat its declared tune reference, reject it without opening
validation. Component improvement is only screening evidence, never adoption.

Full arbiter budget: 20 minutes per tour/candidate initially, recalibrated only from a
recorded profiling result before starting. Five bags, all scoreable years 2010–2026,
same keys/cutoff and corrected pair probabilities. Tour-agnostic changes require both
tours. Retain campaign-reference and current-incumbent comparisons if P5-A changes it.

Report paired delta with positive meaning improvement, naive SE, fixed week/event
bootstrap, per-year outcomes and all predeclared slices. The formal inequality remains
`d_tune > 0` and `d_val > -SE_naive`; report validation sign and stability separately.
An event bootstrap currently cannot cover 196 ATP / 411 WTA unidentified event rows.
Resolve IDs through independent evidence as a separately reviewed metadata change, or
retain the explicit unavailable result. Never drop those rows or invent event groups
to produce a cleaner interval. Week clustering remains available.

Do not retry rejected Elo geometry, recency weighting, training truncation, pooled-tour
models or calibration families merely because the reference measurement changed. A
different mechanism or data regime must be written down first. Validation diagnostics
have now been observed: they support hypothesis design but are not a fresh holdout.
Independent future confirmation remains Phase 6 and requires its own capture protocol.
