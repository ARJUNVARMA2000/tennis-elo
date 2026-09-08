# Next session — collect published WTA orders and qualify timing

Read the [review](2026-09-08-wta-coverage-review.md),
[result manifest](2026-09-08-wta-coverage-result.json),
[contract](2026-09-08-wta-coverage-interface.md), prior identity/schedule/time-evidence
handoffs and the live todo tail. The WTA format adapter and initial coverage study are
complete. Continue from their acceptance tip rather than rebuilding them.

## Exact state

`R = /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Latest checkout: `R/worktrees/wta-coverage`, branch `codex/model-wta-coverage`, based on
`e10757fa432f08203642ef9e8fa784f77f906795`. Source/tests/contract implementation:
`b6df856dffa0f397b17f79b7511fe3bc5ff730f1`; resolve the branch's later docs acceptance tip
for the next isolated checkout. Original DEUCE mirrors documents/logs only. Do not edit
accepted implementation checkouts. Reconcile Git and append a new bounded plan before edits.

New source code is external under `tennis_model/research/`:

- `wta_orders.py`: `collect`, `ingest`, `read_collection`, `history`; manually acquires at
  most one official HTML page and one WTA API per call, with no retries or redirects.
- `wta_calendar.py`: `read_capacity` and CLI; reads the already-retained calendar. No
  general calendar network collector or recurring job was added.
- Source/test fixtures: `tests/fixtures/wta_orders/manifest.json` plus seven exact gzip
  bodies; synthetic mutations in 62 tests are regression QA, not observed revisions.

Accepted older code remains `usopen_schedule.py` at `cda5393`, `usopen_identity.py` at
`aab6ed0`, and the source/bounds modules. No current annotations are evaluator-ready.
The identity audit uses pinned legacy ESPN/WTA snapshots; do not silently treat those
as contemporaneous results. Identity tables still belong to the established proposer.

Current raw runs are `R/runs/wta-coverage`. Verify `result.json`'s 34 `runFiles`, its
`protected-run-files.json` containing 572 prior entries, the frozen packages/models and
all thirteen now-completed research checkouts before starting the next phase. Expected
next protected count: 606. Verify source hashes before deriving a new artifact.

Private drivers (preserve unchanged):
`R/tools/wta-coverage-probe.py`, `wta-coverage-replay.py`, `wta-coverage-verify.py`.
The probe has a fixed official-host allowlist and was used only for bounded research.
The replay/verification drivers create immutable outputs; rerunning them against their
existing destinations intentionally fails. Read existing collections directly, or use
new labelled destinations and a new driver. Never overwrite old receipts or timestamps.

## Next work and dependencies

1. **Actual publication/progression; wait for useful source change.** Guadalajara 2075/2026
   is scheduled September 13–19 and its last observed page/API pair at 05:35 UTC September 8
   was unpublished/empty. There is no verified release time. On a later justified manual
   check, use the exact observed official URL below; preserve another unpublished pair as
   a gap if that is still the state. Do not guess a released day's URL or create a recurring
   job. Existing US Open evidence may be advanced after a meaningful match stage using the
   accepted USOpen.org collector; its September 8 first listed start is 15:30 UTC, not proof
   of physical first serve. Avoid immediate overnight duplicates.

2. **Broader event acquisition, after source publication.** Prioritize Guadalajara (27
   possible main-singles matches), then São Paulo (31), Seoul (31), Singapore (27). Verify
   each actual official order URL and widget/API edition before acquisition; do not derive
   event identity from names/slugs. Do not bulk-fetch WTA125 or unrelated events. Current
   calendar IDs/dates and exact exclusions are in `capacity-001.json`. Beijing contributes
   up to 95 whole-draw matches but runs through October 11, beyond this planning window.
   Before any pilot registration, recompute a current date-based coverage plan, then use
   the evaluator's exact timed registration contract. Do not extend an already registered
   pilot opportunistically to reach 200; none is registered now.

3. **Timing qualification can be researched independently of publication.** The remaining
   gate is `capture + 5 minutes < original schedule lower <= independently supported
   actual-start lower`, with stable identity and subsequent eligible result evidence.
   Court-start labels and `MatchTimeStamp` agreement alone do not qualify actual play.
   Read the existing time-evidence/start-source work first; it already rejected generic
   epochs, derived elapsed-clock agreement and corrupt point chronology. A proposed free
   official source must supply field meaning, clock precision and real chronological
   witnesses, including revisions/contradictions. Implement a live producer only after
   that contract is evidenced. If no such premise is supportable, report the limit; more
   result rows or additional model fitting cannot repair missing pre-play evidence.

4. **Live integration depends on 1–3.** No live pilot or automatic collector is active.
   Preserve the 30-day collection / day-37 settlement and 200-pair coverage rules in the
   accepted contract. A model-performance comparison needs actual paired forecasts and
   a qualified timing producer. Keep the frozen incumbent and candidate intact. Reuse
   existing collector/runner/evaluator boundaries; do not invent forecasts for retained
   retrospective order pages. Any permitted future collection must record acquisition
   time separately from publication time and keep every adverse revision.

These are independent research dependencies, not authorization to spawn agents, buy
access, contact providers, create automations or deploy. User continuation authorizes
bounded implementation under the established workflow; no further account input is
currently required for the public WTA pages/API (the API uses public `account: wta`).

## Concrete replay and later manual capture

Run from the **owning checkout's `tennis_model` directory**, with `PYTHONPATH=src:research`.
Use the existing interpreter through uv; no dependency installation or training-data copy:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src:research \
uv run --offline --no-project \
--python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python \
python -m pytest -q tests/test_wta_orders.py tests/test_wta_calendar.py \
  tests/test_usopen_identity.py tests/test_usopen_schedule.py tests/test_prospective_sources.py \
  tests/test_time_evidence.py tests/test_prospective_bounds.py
```

Append the following arguments to that uv/interpreter prefix for a justified future
manual capture, using a fresh exclusive destination under the **new phase** run root:

```text
python research/wta_orders.py --trusted-root NEW_PHASE_RUN_ROOT collect NEW_COLLECTION_ROOT
  --url https://www.wtatennis.com/tournaments/2075/guadalajara/2026/order-of-play
```

This makes real HTTP requests and needs network permission. It is not an automatic cadence.
`unpublished` exits zero but leaves absence comparison false; `gap` exits one and preserves
raw failure evidence. `history ROOTS... --output NEW_JSON` re-verifies every supplied
collection. Pass a trusted root encompassing all supplied archives. Do not pass only the
newest snapshot or omit an adverse intermediate collection.

Existing read-only archives:
`intake-future`, `intake-historical`, `intake-current`, `order-history-001.json`,
`capacity-001.json`, `cli-replay.json`, `validation.json`, `acceptance.json`, all under
`R/runs/wta-coverage`. They replay 155 occurrences / 151 unique main-singles IDs,
zero temporal revisions and one unpublished gap. The historical cross-day repeats are
simultaneous page occurrences, not observed rescheduling times. Source receipts remain
at their September 8 acquisition times; do not replace them with replay time.

## Closure requirements

New failure classes belong in the relevant external source/bounds contract and tests;
no application data changed in this phase. Before a production change, the repository's
normal data-health and deployed-serving gates still apply. Do not weaken either.
Verify the 606 protected run files, 91 frozen package files, both model payloads and prior
tracked code; record precisely whether the large external inventories were rehashed.
They were last fully verified at 2026-09-08 01:58:44.035725 UTC, not at this phase's acceptance.
Append review/ledger/lessons, commit isolated research, then mirror documents/logs only
into original DEUCE. Use real observed timestamps and final Git facts; no claims of
adoption, live readiness, statistical improvement, merge, push or deployment without them.
