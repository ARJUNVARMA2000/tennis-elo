# Next session — maintenance before finishing Phase 4 screening

This is a concrete maintenance design triggered by the Phase 4 stop condition. **It has
not been implemented.** The uncertainty prototype is tested but not selected or adopted.
Read the [Phase 4 review](2026-09-06-phase4-review.md), its result JSON and the original
[preregistration](2026-09-06-phase4-preregistration.md) before making changes.

## Workspace and immutable references

Project: `/Users/varma/Projects/DEUCE` (documentation-only handoff branch).
Implementation: `/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/phase4`,
branch `codex/model-phase4`. Record its current commit and dirty state before continuing.
Preserve coordinator `codex/model-foundation` at `c5cd366`, implementation `8be9d74`.
Keep all prior run directories and the read-only Phase 0 snapshot unchanged.

Run root: `/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
The old reference contract is `add41de4629703455fad849c59dfc21a82fa569f13e91970417894127615217d`.
The Phase 4 implementation snapshot is `runs/phase4/implementation-freeze.json`; it changes
only `ratings/dynamic.py` and is not an eligible candidate freeze. Do not overwrite either.

Use the preserved coordinator runtime, with no package installation:

```bash
cd /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/phase4/tennis_model
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python -m pytest -q
```

The working directory and `PYTHONPATH=src` are required. Never run normalizer rebuilds
concurrently with tests that can replace caches. Use fresh exclusive attempt directories.
No push to master, deployment, paid feed purchase, messages, or prospective activation
is included in this handoff. Existing evaluator rules and assertions remain unchanged.

## Sequence and independent work

| Step | Requires | Work that can proceed independently | Exit |
|---|---|---|---|
| M0: register maintenance and evidence fixtures | Read this handoff | Review prototype API/tests | Exact scope, source/cutoff hashes and plan recorded |
| M1a: result-ledger adapter | M0 | M1b self-match and date evidence review | Validated results independent of optional statistics |
| M1b: identity/outcome/date adjudication | M0 | M1a adapter design | Explicit dispositions, no fabricated dates/opponents |
| M2: merge and integrity gates | M1a + M1b | Documentation and read-only reviews | No duplicates/regressions; missing expected records block |
| M3: versioned reference | M2 tests + frozen inputs | Read-only reporting | Full rebuilt incumbent and real artifact checks pass |
| M4: finish Phase 4 prototype screening | M3 | Read-only reporting | Full-history parity, eight tune-only results, <=1 candidate |
| Phase 5 | M4 selection | Read-only reporting | Full paired arbiter verdict |

Parallel means independent implementation/data-review work with disjoint files. Do not
run fitting jobs concurrently or edit frozen inputs during a fit. Do not launch other
agents unless separately authorized. Complete and log one numerical decision at a time.

## M0 — register a distinct correctness repair

- [ ] Append checkable maintenance steps to `tasks/todo.md`, with the continuation request
      as authorization. Prefer a new maintenance branch/checkout from reviewed Phase 4 code
      if preserving the prototype preparation branch; copy data with distinct files.
- [ ] Save raw, package, evaluator-only, runtime, policy and cutoff hashes. Confirm no
      unrelated changes. Retain Phase 3 predictions for historical comparison only.
- [ ] Read `data/wta_stats.py`, `data/results.py`, `data/chronology.py`, `data/events.py`,
      `data/health.py:output_findings`, `tests/test_health*.py` and relevant lessons.
- [ ] Create small provider fixtures from the preserved evidence, carrying original hashes.
      Include a valid completed result with no stats, retirement with empty WTA score,
      walkover, cross-year repeated match ID, zero-padded ID and the verified Sherif alias.

## M1a — factual results must not depend on box scores

- [ ] Add a result-record normalizer/ledger separate from optional serving-stat extraction.
      Start with cached WTA main singles; do not automatically ingest doubles, qualifying,
      WTA125, unknown roles or all historical calendar rows.
- [ ] Key by explicit event edition plus numeric provider event ID and source match ID,
      with canonical player identities. Reconcile header/record year and ID; conflicting
      identity is quarantined. A cache folder or display title cannot establish identity.
- [ ] Use the Phase 4 row CSVs as evidence, not a blind acceptance list. At least 491
      absent completed results have second-provider corroboration. The 22 other complete
      score cases in the five affected events need explicit identity review. Preserve
      the rest of the full audit as leads; do not broaden the repair without logging it.
- [ ] Preserve raw outcome, set scores, source URL/hash, provider IDs, retrieval time,
      event bounds and timing basis. Admit ordinary completed results only with coherent
      winner/score/round/role. Preserve retirements and walkovers as their own outcomes
      under the existing training/scoring policies. Do not infer completed from `F` alone.
- [ ] Keep serving denominators null when absent. A future successful stats response
      enriches the existing match; it must not add a second result. Resuming acquisition
      of result-only rows must still attempt missing stats when appropriate.
- [ ] Use an explicit source integration path and precedence in `merge_sources`; do not
      simply emit result-only rows into the higher-priority stats CSV and discard better
      fresh-source retirement markers or factual metadata. Test both acquisition orders.
- [ ] Keep acquisition staged and one year at a time, record pagination and actual yield,
      stop on 429, preserve existing evidence. A live update path can reuse the existing
      calendar/match-list adapter after its result/stat separation is tested.

## M1b — self-match and timing evidence

- [ ] Resolve the raw 1980-04-30 Berkeley R16 record (`1980.csv:2597`, both IDs 200358).
      Search independent draw/result evidence for the true pair; never guess an opponent
      or add a general name-reordering rule. If it cannot be reconstructed, record a
      reviewed exclusion/quarantine with a stable source key and reason.
- [ ] Audit both tours for the same invalid self-pair class before freezing. The new
      dynamic walk already rejects same-player matchups; preserve that invariant.
- [ ] Review the WTA `estimatedStartTime` / `isEstimatedStartTime` flags. Existing
      chronology accepts bounded `MatchTimeStamp` dates without checking these flags.
      Many audited records set them true. Determine what reliable played-day evidence
      exists, distinguish schedule estimates from actual timing, and use conservative
      recorded/event-bound semantics where exact time is not evidenced.
- [ ] Keep historical publication time unknown unless supported by actual archived
      availability evidence. Retrieval now does not prove a model could have seen it then.
      Preserve past-only priors and their pending observation queues from Phase 2.
- [ ] Add timing-boundary tests and saved-state parity for any changed date/availability
      semantics. Never use the newly fetched latest profiles as historical player metadata.

## M2 — integration, population boundary and independent gates

- [ ] Integrate only reviewed rows/dispositions. Compare old/new normalized membership,
      source survivors, roles, dates and completeness at every source seam. Repeated
      real matches must survive; ambiguous joins must not silently collapse.
- [ ] Add an independently derived expected-result ledger/coverage receipt to the build.
      It must enumerate eligible expected keys from provider evidence and explain each
      admitted, duplicated, excluded or unresolved record. Counting only output survivors
      cannot detect omission; a nominal `draw_size - 1` is not a complete denominator.
- [ ] Extend typed pre-upload `output_findings()` with stable blocking findings for missing
      expected admitted results and invalid self-pairs. Carry the validated receipt through
      the relevant full/quick build paths. An absent/stale receipt must not silently pass.
      Implement tests that delete one valid result, omit an entire event, and corrupt a
      player pair while leaving ordinary row totals/metadata otherwise plausible.
- [ ] Keep legitimate quarantines/exclusions explicit and visible; unknown expected
      coverage is unknown, not zero missing. Keep existing release lineage enforcement.
- [ ] Increment `MATCH_POPULATION_VERSION` from 6 at the reviewed membership change;
      verify no intervening commit has already used the next value. Preserve old artifacts.
      If timing/state/schema changes require a separate version, make it explicit too.
- [ ] Test source completeness, dedup, aliases, outcomes, chronology, main/lower roles,
      health findings, population-version transitions and strict artifact compatibility.
      If any deployed consumer changes, extend the appropriate serving gate as well.

## M3 — establish the new incumbent before testing improvements

- [ ] Freeze repaired inputs and exact corrected code in a new contract and new run root.
      No download during scoring. Ensure `eval/`, adoption inequalities, thresholds,
      calibrator and tree/bag settings have not changed.
- [ ] Rebuild incumbent features, then ATP and actual-policy WTA baselines sequentially,
      five bags, all scoreable years 2010 onward, same declared data cutoffs. If a
      tour-independent timing/identity change affects ATP, both tours are mandatory.
- [ ] Report coverage expansion/removals separately. Compare old/new incumbent on exact
      common keys; never subtract headline losses from different match populations.
      Call this maintenance/reference change, not an adopted model gain.
- [ ] Repeat strict saved final-predictor reload, past cutoff/pending-prior parity,
      main/lower gate and feature-matrix parity, and 435-pair exchange checks. Retain
      unavailable event-cluster intervals where identities remain genuinely unknown.
- [ ] Re-run Git history and reconcile docs, metrics and source versions. Commit the
      tested maintenance implementation and a complete new-reference handoff.

## M4 — finish Phase 4, then Phase 5

- [ ] Re-run `ratings.dynamic.run_dynamic` on the complete repaired history. The passing
      1991–2019 cold-start replay in Phase 4 was QA only; do not reuse it as full history.
- [ ] Recheck source/identity alignment, query serialization, three real cutoffs, baseline
      threshold-32 selection and disabled exact feature/probability parity.
- [ ] Implement a registered 43-column research combiner adapter with exactly one new
      antisymmetric `logit_p_dynamic` column. Keep orientation seeds, train/cal splits,
      bag settings and paired probability logic identical; do not mutate the frozen
      evaluator to accept the feature. A new candidate schema/contract must be explicit.
      The existing `attach_dynamic` helper supplies the column but does not fit a model.
- [ ] Run exactly eight tune-only settings sequentially: sigma0 {0.5,1.0} crossed with
      q {1e-6,1e-5,1e-4,1e-3}; surface variances remain one quarter global. Budget 45 min,
      preserve every attempt, choose at most one before any candidate validation score.
      The original representation and grid were not changed after viewing outcomes.
- [ ] With no tune improvement, reject the family. Otherwise Phase 5 runs the full
      five-bag paired arbiter against the new incumbent; gate remains d_tune > 0 and
      d_val > -SE_naive. Report week clustering and predeclared slices separately.
- [ ] No data candidate is currently admissible. Do not redo no-yield 2025 stats requests
      or promote 2024 restoration as optional enrichment. Any new source pilot needs
      a distinct evidence-backed path and tune-era relevance.
- [ ] Phase 6 future confirmation and Phase 7 production integration remain separate;
      no prototype JSON may bypass the normal artifact loader to reach the product.
