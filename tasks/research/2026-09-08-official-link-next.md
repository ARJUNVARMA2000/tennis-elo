# Next session — use the identity audit; progress beyond one unchanged order

Read the [review](2026-09-08-official-link-review.md),
[manifest](2026-09-08-official-link-result.json),
[contract](2026-09-08-official-link-interface.md), the accepted schedule/time-evidence
interfaces and the live todo tail. Source shopping, schedule collection implementation
and this broad identity audit are complete. Do not rebuild them.

## Exact state and boundaries

`R = /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Latest checkout: `R/worktrees/official-link`, branch `codex/model-official-link`, based
on `70f5976`. Source/tests commit `aab6ed05d66bac514e5b6d3903cb7924b06b6aff`; use the
branch's final acceptance tip for the next isolated implementation checkout. Preserve
all earlier checkouts. The original DEUCE checkout mirrors documents/logs only.

Implemented modules in `tennis_model/research/`:

- `usopen_schedule.py` (`cda5393`): manual immutable catalogue/day collection and history.
- `usopen_identity.py` (`aab6ed0`): official draw event corroboration, strict match links
  and retrospective association with verified schedule histories.
- `prospective_sources.py`, `time_evidence.py`, `prospective_bounds.py`: unchanged
  accepted source/bounds work. Only synthetic start evidence is qualified.

The new audit's callable `run(index_root, draw_root, collections, trusted_root=..., year=...)`
verifies official draw captures in the retained `official-draw-inspection-v1` format,
uses pinned legacy ESPN/WTA fixtures, replays every supplied schedule collection and
emits annotations. It is intentionally **not** a fresh multi-provider result producer.
No event/context donation or evaluator input comes from these annotations.

`read_draw` is read-only; the phase's private `R/tools/official-link-probe.py` made the
two bounded draw reads. It has a fixed edition/URL allowlist and is not a general live
transport. If future fresh provider intake is justified, first specify its exact source
receipt contract and use existing `prospective_sources.read_capture()`; do not silently
make these pinned fixtures stand in for contemporary observations.

## Observed state and remaining dependencies

The September 8 order was unchanged at 04:31 UTC. Days 18–22 remained unpublished.
Across four saved collections there are ten schedule versions for six matches. No
revision lifecycle was witnessed. Current Sabalenka–Noskova and Pegula–Navarro rows
show session starts at 15:30 and 23:00 UTC. Do not assume these are actual first serves.

The full official WS draw at 04:32 UTC has 120 completed and seven pending slots.
Its 119 corroborated results establish event identity; strict player-ID predicates
admit 100 match links and all six sampled schedule matchups. Twenty-three matchups have
different player numbers; retain/exclude them, and do not edit identity tables or invent
aliases. One real matchup is absent from the older provider snapshot and three future
slots have unknown players. Later raw data must retain these unresolved histories.

The next phase has three distinct dependencies:

1. **Observe real event progression.** A bounded later check after a meaningful match
   stage can reuse the current collector. After publication, inspect the next actual
   day selected from the catalogue. Do not infer day numbers, fetch unreleased URLs,
   backdate captures or turn missing/error responses into an empty authoritative order.
   If still in the same overnight window, stop re-fetching identical bytes.
2. **Establish the start premise.** The rulebook does not provide independent actual-start
   evidence. See the review's exact primary source/page references. Qualify a source
   contract with observed lifecycle support, or record a separate assumption-based
   prospective protocol before outcomes. Neither path is implemented/registered. Do
   not weaken the accepted primary gate or retroactively grade these old observations.
3. **Expand official event coverage.** At most seven pending US Open matches remain;
   this collector cannot furnish a 200-pair pilot. Before scheduling a 30-day evaluation,
   scope at least the next main-tour official schedule source using existing WTA event
   registry/catalogue evidence, plus a realistic eligible-match count. Validate its
   explicit edition, population, timezone, not-before semantics and identities. Reuse
   source/receipt helpers, but do not force a different publisher into the US Open parser.
   A complete source-specific adapter is conditional on actual public samples, not on
   another generic scraping framework or a paid signup.

Work on the source contract and next-event coverage can proceed while waiting for play;
this is not authorization for subagents. No automation is active. If the user explicitly
asks for monitoring/scheduled collection, use the app automation tools with actual dates,
endpoints, a bounded cadence and stop condition. Notify only meaningful changes/failure.
A source-monitoring job does not automatically activate an evaluation.

## Replay and tests

Run from `R/worktrees/official-link/tennis_model`, with `PYTHONPATH=src:research` and
`UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv`. Use uv with the coordinator
runtime at `R/worktrees/coordinator/tennis_model/.venv/bin/python`; no install or training
copy is needed. Keep script paths relative to this directory, private drivers absolute.

```bash
uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python -m pytest -q tests/test_usopen_identity.py tests/test_usopen_schedule.py tests/test_prospective_sources.py tests/test_time_evidence.py tests/test_prospective_bounds.py
```

Accepted result: 175 passed in 5.32 seconds; 29 are new. Ruff passed. Additional
unchanged source observations do not require a full-suite rerun.

The identity CLI is `research/usopen_identity.py --trusted-root R/runs --year 2026
--index-root R/runs/official-link/draw-index --draw-root R/runs/official-link/draw-ws
--output NEW_FILE COLLECTION...`. Supply all four collection paths in this order or
any order (history sorts verified observation times):

1. `R/runs/official-schedule/retained-16`
2. `R/runs/official-schedule/retained-17`
3. `R/runs/official-schedule/live-001`
4. `R/runs/official-link/schedule-001`

`R` above is documentation notation: expand it to the absolute root before execution.
Use a new output path; publication is create-only. Existing result:
`R/runs/official-link/identity-audit-001.json`, with 100 links, 27 exclusions and ten
associations available no earlier than 04:32:09.560676 UTC. This is an evidence-availability
bound, not a claim that the audit program had already run at that moment.

## Preservation and closeout

The new run has 19 files. Add the result's `runFiles` to its protected manifest for
**572 previous files** next time. The 91 frozen package files, both models and 360
previous tracked program/web/workflow files were exact; eleven prior completed research
checkouts were clean. Preserve this accepted checkout too. Do not rerun private
create-only acceptance drivers over existing outputs.

Incumbent remains `R/runs/maintenance/wta-final-001/predictor.pkl`, SHA
`8cf280c43f813a6944244d585248af8d5fcbc1ff628e535f98d4e10866730e34`.
Candidate remains `R/runs/prospective-shadow/migration-001/candidate.shadow`, SHA
`43dd88b1461913f11b90b6d2aa6aa82f7bbfe3ba7ad597d978c6a46b73d45fcc`.
Freeze/provenance remain under `R/runs/prospective-shadow`. No fitting, migration,
training copy, account, trial or provider contact. No production merge/push/deploy.

The original fixed protocol remains 30-day capture, day-37 settlement and strict
`capture + 5 minutes < original schedule lower <= independently supported actual-start lower`.
The 200-pair threshold is coverage, not power. Full-size synthetic QA and old completion
bounds are preserved, but neither is fresh model-performance evidence. Append the next
plan before edits, reconcile Git before documentation, commit research and mirror only
documents/logs to the original checkout.
