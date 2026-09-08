# Resume here — obtain start evidence, not another evaluator

Read `2026-09-07-time-evidence-review.md`, its result JSON and interface; inspect the
live todo tail, relevant lessons and Git history. The source adapter, completion-bound
producer and separately versioned bounds evaluator are implemented and accepted.
Do not repeat model fitting, migration, parameter search or generic timing-framework work.

## Exact state and runtime

Research root `R`:
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Latest checkout `R/worktrees/time-evidence`, branch `codex/model-time-evidence`.
Implementation/tests: `10c07ee726632f7186522e423205d661169123ce`.
Modules: `tennis_model/research/prospective_bounds.py`, `time_evidence.py`, and the
unchanged `prospective_sources.py`. New tests: 58; combined: 231 passed in 9.92s;
full source/research/test lint passed. All 82 old tracked test/fixture files are exact.

From that checkout's `tennis_model` directory, use the preserved runtime:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src:research \
uv run --offline --no-project \
  --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python \
  python research/prospective_bounds.py --help
```

Do not prefix paths with `tennis_model/` again after entering it. Source modules exist
only in research checkouts; the original root has documentation, not these modules.
Resolve test files before invoking a combined selection.

Frozen artifact pair:

- Incumbent: `R/runs/maintenance/wta-final-001/predictor.pkl` and `.envelope`, payload SHA
  `8cf280c43f813a6944244d585248af8d5fcbc1ff628e535f98d4e10866730e34`.
- Candidate: `R/runs/prospective-shadow/migration-001/candidate.shadow`, SHA
  `43dd88b1461913f11b90b6d2aa6aa82f7bbfe3ba7ad597d978c6a46b73d45fcc`.
- Caller-pinned provenance: `R/runs/prospective-shadow/provenance.json`.
- Model-package/input freeze: `R/runs/prospective-shadow/implementation-freeze.json`,
  contract digest `969eb8eeb77d09f051ee52c415eb2d15e5ffa7d138e9b4149166e51eda3a355c`.

External evaluator hashes are additionally pinned in each v2 registration; they are
not covered by the shadow package hash. Adding a producer can leave fitted models
unchanged, but cannot silently change an existing registered evaluator.

## S0 — select a feasible start-evidence source

Append a bounded source-qualification plan before editing. The current live producer
set is empty: `time_evidence.check_mode()` permits only explicit `synthetic-qa`.
This is deliberate. Do not remove it just because completion bounds now work.

Investigate one concrete source path at a time, using primary documentation and a small
actual sample saved in new exclusive acquisition directories:

1. Public official match timeline/point feed with an explicitly defined actual match-start
   event and known timestamp precision. Inspect WTA/US Open first-party pages/endpoints;
   verify the response, not a field name inferred from search results. Reuse the bounded
   acquisition/receipt design for any newly justified endpoint.
2. An official published order of play providing a defensible hard lower bound, paired
   with independent start upper evidence. The inspected rules support not-before
   scheduling but do not themselves qualify the API field. Establish publication time,
   matchup/round, edition, timezone, earlier-revision handling and what the event actually
   guarantees. Make any schedule-compliance assumptions explicit; do not call an
   assumption deterministic actual-start proof or weaken the primary confirmation claim.
3. If public evidence remains insufficient, an already available licensed timeline feed.
   Primary Sportradar tennis timeline docs describe timestamped `match_started` events,
   but no key, coverage or precision contract has been verified here. Do not create an
   account, start a trial or buy access. State the exact missing access/coverage decision
   if it is required; do not work around access controls or manufacture substitute times.

A source observation of live play supplies a start **upper** bound. It does not by
itself prove pre-match capture. A pre-play status needs a justified effective observation
time and delivery-lag bound; HTTP Date/Age and average empirical lag are insufficient
for a deterministic bound. Playing duration subtracted from receive time is invalid.

S0 succeeds with an explicit producer mapping and its evidence assumptions, or ends
with a precise data/access gap. If no feasible producer is found, stop adding generic
code and report that gap. More evaluator layers do not produce missing observations.

## S1 — qualify and implement that producer

S1 depends on S0. Use a new checkout from the accepted time-evidence tip; keep completed
checkouts and every old raw response, model and QA run immutable. No training-data copy
is needed for an external source addition.

Add a producer to the external evidence module only with a field-level contract and
real fixture provenance. Qualified actual-start events provide an interval that includes
measurement precision. A schedule-derived lower bound, if justified, must have its own
honest evidence type/producer; do not label it an observed actual-start event.

Bind endpoint configuration, semantics/precision, source identities and qualification
record in the new registration. Keep raw captures linked to any derived claim. Qualification
must exercise pre/live/terminal transitions, offsets, earlier schedule changes, postponed
matches, stale/missing responses, participant replacements and conflicting results.
The prior two source observations showed score changes but no complete lifecycle.

The existing completion producer already validates both receipts/raw bodies, maps the
event through completed-match evidence, supplies 119 completion bounds on the preserved
sample, and carries 246 provider identity rows. Conflicting terminal results must remain
explicit exclusions. One completed source versus a still-live source is not two terminal
claims; preserve that distinction. Do not erase past contradictions on a later retry.

Extend tests in the qualified producer's actual failure cases and prove strict full-size
artifact integration. New external code changes invalidate older external registrations;
start a new one. Changing package code would trigger a separate formal model migration,
which is unnecessary for the currently planned source-only integration.

## S2 — activate and evaluate a real future interval

Requires S1's verified source and an actual registered acquisition cadence. The cadence
cannot merely be prose in `sources`. A user request for scheduling should use the app
automation tool; no background shell loop or collector is currently active.

Use actual local registration time, future source observations, fixed artifacts and a
new private live experiment. Preserve the first paired forecast and exact factual
context. Capture for 30 days, settle through day 37, and treat 200 pairs as coverage
adequacy rather than an outcome-driven stopping rule. Pre-play eligibility remains
`captured + 5 minutes < schedule lower <= independently supported start lower`.
A result observation can bound finish above, but cannot justify the start lower edge.

The existing `R/runs/time-evidence/acceptance-001/synthetic-qa` used two invented
matchups, simulated capture/settlement clocks and invented outcomes. It scored 2 pairs
for engineering QA only. Its actual registration timestamp does not make the subsequent
simulated evidence real. Never upgrade it, reuse its results, or grade prior source-audit
QA as a live experiment. The retained completion audit is also not fresh forecast data.

Report paired loss/Brier/accuracy, event/week uncertainty and missing/contradictory timing
coverage at the fixed endpoint. Week uncertainty is unavailable when any scored start
interval crosses a UTC week; overall/event scores remain. The historical gain is small
and still uncertain; an operational pilot does not automatically justify adoption.

## Dependencies and closeout

S0 precedes producer implementation. Real lifecycle observations can accumulate alongside
implementation only after their source and acquisition plan are defined. Live activation
requires both tested code and real source/cadence qualification. No agents are authorized
by this document, and no production merge or deploy is implicit.

Preserve all eight completed research checkouts, original data, the read-only snapshot
and private runs/drivers. Current preservation covered 415 prior run files; add this
phase's result JSON `runFiles` to the next inventory. Append todo/ledger/lessons, reconcile
Git before citing facts, commit research changes, and mirror only documents and append-only
logs to the original checkout. Do not rebuild the same model to demonstrate more progress.
