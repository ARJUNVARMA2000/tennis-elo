# Next session — validate the demonstrated WTA event stream against physical time

Read the [review](2026-09-08-wta-lifecycle-review.md),
[result manifest](2026-09-08-wta-lifecycle-result.json),
[contract](2026-09-08-wta-lifecycle-interface.md), prior WTA coverage handoff and accepted
[time-evidence contract](2026-09-07-time-evidence-interface.md). The event-source audit is
implemented; do not repeat the six reads or rebuild the source/order adapters.

## Exact state and preserved artifacts

`R = /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Latest checkout `R/worktrees/wta-lifecycle`, branch `codex/model-wta-lifecycle`, based on
`781d37b5d23b737f20ef185a25f094d32e3675d8`. Source/tests/contract:
`f355253f75071cfedeafe15adf67898d52aa36e2`; resolve this branch's final acceptance tip for
the next isolated checkout. Leave accepted checkouts intact. Original DEUCE holds docs/logs only.

New module `tennis_model/research/wta_event_audit.py` provides `read_capture`, `audit`,
`run`, `write_audit`, `read_audit` and a read-only CLI. It accepts the preserved
`wta-lifecycle-inspection-v1` receipt contract, matches an `/events` URL to an existing
WTA API/order collection, and emits `wta-event-timeline-audit-v1`. The schema is refused
by the unchanged live-start evaluator. There is no new network collector or automatic job.
Four exact event/404 fixtures and their manifest are under `tests/fixtures/wta_events`;
existing WTA match/order fixtures are reused. Synthetic mutations in the 59 new tests are QA only.

Raw acquisitions are under `R/runs/wta-lifecycle`: `current-order-001/{page,api}`,
`final-events`, `semifinal-events`, `final-points`, `semifinal-points`. Derived artifacts:
`final-events-audit.json`, `semifinal-events-audit.json`, `order-history-001.json`,
`cli-replay.json`, `source-semantics-note.json`, validation logs and acceptance.
The result JSON lists 29 exact `runFiles`, while `protected-run-files.json` lists 606
previous files: **635 total next phase**, with fourteen accepted prior checkouts.

Private drivers under `R/tools/`: `wta-lifecycle-probe.py`, `wta-lifecycle-replay.py`,
`wta-lifecycle-verify.py`. Preserve all three. The probe is a bounded research reader,
not a live producer. Replay/verification create exclusive outputs; rerunning them into
old destinations should fail. Read existing outputs or use a new labelled run/driver.

Both frozen model hashes remain in the acceptance manifest. Incumbent stays the corrected
maintenance artifact; candidate adoption remains deferred. The 91-file package freeze,
older evaluators and source collectors are unchanged. No training copy, fit or new score.

## Research facts that change the next step

- The fresh US Open WTA pair at **13:32:46.632425 UTC September 8** is unchanged from
  05:41 UTC: 124 main singles, 248 versions over two collections, no revisions or gaps.
  Its first listed court start is 15:30 UTC. Do not immediately repeat the same pre-play
  fetch. Actual event progression can later justify a bounded observation.
- The two **Guadalajara 2025** `/events` sources contain 185/220 records, including a
  unique OnCourt → PlayersArrived → Warmup → InProgress sequence and 119/136 scoring
  records. Their source identities and final game scores agree with existing WTA data.
  Both `/point-by-point` sources are 404; no retry is useful without a new concrete lead.
- InProgress at 21:09:00.403 UTC September 14 and 22:08:12.887 UTC September 13 is a
  reported marker, not a qualified physical start. API MatchTimeStamp is 1,283.073 and
  1,421.560 seconds earlier. `TimestampLocal`/`MatchTime` consistency is not independence.
- Coarse WTA LIVE includes OnCourt and Warmup. Detailed MatchState P means PLAYING in
  the retained bundle, but the physical event semantics, operator delay and clock-error
  bound are still unverified. The final scoring records remain P, with no terminal F event.
- Exact-string source searches and two WTA news articles did not supply a clock contract.
  News corroborates results/duration only. This is a limited search result, not proof
  that documentation cannot exist. Preserve the distinction when explaining the blocker.

## Next work in dependency order

1. **Independent timing qualification is now a specific source problem.** Investigate
   what creates WTA `StateIndicator/InProgress`, the meaning of its `Timestamp` versus
   `LastUpdated` and `referenceTimeAsLocalTime`, and how its clock is synchronized and
   corrected. Start from these actual fields and the retained primary scripts. Do not
   reopen generic free-provider shopping or equate fractional seconds with accuracy.
   A useful independent witness must identify the same match and physical first serve
   against a clock with a defensible uncertainty. Broadcast duration, elapsed match clock
   or another view of the same API is insufficient by itself. Do not invent an error
   allowance, subtract an arbitrary margin, or silently weaken the accepted primary gate.

2. **Observe live versions when this source's covered tournament is playing.** Current
   evidence is retrospective 2025 data. Guadalajara 2075/2026 is scheduled September 13–19;
   its latest retained order/API was unpublished September 8 at 05:35 UTC. Use the
   accepted WTA order collector at the verified URL after a justified publication check.
   Only after it supplies actual resolved main-singles MatchIDs should their event URLs
   be constructed from the observed service contract. Do not reuse `LS001`/`LS002` from
   2025 as though they were already discovered 2026 matches. Define a small acquisition
   budget and retain empty, failure, correction and replacement responses. No unattended
   cadence is authorized or running. No source read may backdate a forecast.

3. **Once real versions exist, extend the event audit for observed revision behavior.**
   The current auditor validates one retained array against one order collection. It
   does not yet compare two event arrays, track deleted/replaced event indices, resolve
   corrections, or classify all possible state reasons. Add those behaviors only with
   a documented contract and relevant cases; retain adverse records and old receipts.
   Late repeated InProgress markers cannot replace the initial start. Unknown states
   remain findings rather than being silently coerced to PLAYING. If source collection
   becomes recurring later, use the app's automation tools only when requested.

4. **Live evaluation requires 1–3 plus prospective forecasts and sufficient coverage.**
   The unchanged primary test is `capture + 5 minutes < original schedule lower <=
   independently supported actual-start lower`. Only synthetic starts are qualified now.
   A newly qualified producer needs a new audited version and future registration; no
   retrospective promotion of these two matches. Keep the fixed 30-day capture/day-37
   settlement and 200-pair coverage rules. The existing date-based coverage study found
   only 116 fully contained future match slots plus 95 for partially contained Beijing;
   that ceiling is not 200 eligible pairs or a power calculation. Recalculate a current
   calendar before registration. No registration exists to extend or restart.

Steps 1 and future-source preparation can progress independently of a tournament's
publication, while actual lifecycle observations require real source changes. This does
not authorize subagents, paid accounts, provider contact, automations or a deployment.
No user credentials are needed for the public endpoints inspected here.

## Reproduction and closure

Run from the owning checkout's **tennis_model** directory, using uv and the existing
coordinator interpreter. For read-only replay with new output names, append these
arguments to the same uv/interpreter prefix documented in the previous handoff:

```text
python research/wta_event_audit.py EVENTS_CAPTURE_DIR ORDER_COLLECTION_DIR
  --trusted-root COMMON_RUNS_ROOT --output NEW_AUDIT_JSON
```

Use `R/runs/wta-coverage/intake-historical` as the accepted order collection for these
2025 fixtures and `R/runs` as the trusted root encompassing both phases. `run` re-verifies
all raw source bytes and the order derivation. Event observation time and the later
availability of supporting evidence are separate fields. The original source clocks
remain unchanged. Do not run private create-only drivers over old outputs.

The focused command uses `UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv`,
`PYTHONPATH=src:research`, `uv run --offline --no-project --python
R/worktrees/coordinator/tennis_model/.venv/bin/python python -m pytest -q`, then tests
`test_wta_event_audit.py`, `test_wta_orders.py`, `test_wta_calendar.py`,
`test_usopen_identity.py`, `test_usopen_schedule.py`, `test_prospective_sources.py`,
`test_time_evidence.py`, `test_prospective_bounds.py`, each under `tests/`.
Actual result: 296 passed in 11.34s. Lint and three actual offline CLIs passed; the old
full model suite was not rerun because only the external source audit changed.

Before closure, reconcile Git, verify 635 protected files, the frozen model/package
contracts and all accepted checkouts, and record exactly what was verified. Full large
training/snapshot inventories were last rehashed at 2026-09-08 01:58:44.035725 UTC.
Append review/ledger/lessons, commit isolated research, mirror only documents/logs and
confirm both checkouts clean. No new performance, physical-time qualification, model
adoption or production publication may be claimed without its actual evidence.
