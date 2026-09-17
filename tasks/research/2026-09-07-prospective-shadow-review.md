# Mixed-format runner and exact candidate migration — completed

The separately versioned WTA comparison runner is implemented and verified at
`89002bc909c16a06c734c921f8889e0c865c8ac3`, in
`.research/2026-09-06-model-foundation/worktrees/prospective-shadow`, branch
`codex/model-prospective-shadow`. It starts from the preserved `64d62de` shadow checkout.
Git was reconciled after the tests and real artifact acceptance. This review is dated
September 7 local time; the migration completed September 8 at 00:13:52 UTC.

**Engineering acceptance passes. Adoption remains deferred. No live pilot, source
collector, scheduled task or production deployment was activated.** The corrected
42-column research incumbent remains current. Exact reproduction and the synthetic
checks below provide no additional evidence of predictive improvement.

## What changed

Added `tennis_model/src/tennis_model/eval/prospective_shadow.py` and
`tennis_model/tests/test_prospective_shadow.py`. Every existing package source and all
77 preexisting test files remain byte-identical, including the old production-only
prospective runner and the walk-forward arbiter. The new module has no production
importer, web integration or workflow. The pre-edit decisions are in
[the interface contract](2026-09-07-prospective-shadow-interface.md).

The new runner requires a strict ordinary WTA incumbent plus the explicit saved
43-column shadow. Its caller pins the five provenance hashes and a private trusted
root. It validates source models, copies exact payload/envelope bytes into a new
exclusive experiment directory, validates those copies, and publishes registration
last. Registration binds file hashes, artifact IDs, training times, both state cutoffs,
formats, runtime, source/model contracts and observation-source configuration. A failed
registration directory remains diagnostic; it cannot capture or be reused.

The protocol is fixed in this version: **30 days of capture, 200 minimum settled pairs,
seven more days of settlement intake**. Minimum count is a coverage check; it cannot
extend the endpoint or trigger early stopping. Models and states remain fixed. The
registration records `live` or `synthetic-qa`, a written hypothesis, schedule/result
HTTPS hosts, timing-evidence description and execution cadence. These declarations
pin the intended acquisition method; they do not prove a provider's timing semantics.

Capture preserves bounded valid observations even when all rows are excluded. It joins
by ESPN event ID, season, canonical main-draw round and unordered canonical real-player
pair. Both arms receive identical complete context and must know both players in their
selected state. WTA best-of-three is required. The lower bound on start must be inside
the capture window; inference must finish more than five minutes beforehand. Schedule
observations must remain no more than ten minutes old through inference. The local
clock is checked after both predictions. Retries preserve the first paired receipt;
source observations and attempt/exclusion counts remain available.

Grading accumulates every accepted result batch. A later small batch cannot make an
already settled match disappear. Pending updates cannot erase a terminal outcome.
Missing timing can later be supplied in a complete source observation. Inconsistent
terminal statuses, winners or supplied actual timestamps exclude the match as
`conflictingResults`, retaining all claims for review. Retirements, walkovers,
withdrawals and cancellations are excluded. A scored match needs actual start and
finish proof that corroborates the original lower bound and five-minute margin.
A result observation must arrive before the registered settlement deadline.

Reports revalidate the frozen artifacts and evidence links, and include common-pair
log loss, Brier, winner accuracy, paired naive SE and week/event block uncertainty.
Accuracy ties count half; all deltas are incumbent minus candidate, so their direction
is explicitly different for accuracy versus losses. Reports also expose pending and
excluded matches, capture attempts, unfinished observations, sample adequacy and fixed
model/state staleness. After settlement closes, a create-only endpoint receipt is
published; subsequent reporting must reproduce it. No automatic adoption follows it.

Evidence I/O uses bounded, digest-checked JSON and the existing descriptor-based
no-symlink filesystem primitives. A per-experiment process lock serializes operations;
create-only publication preserves first observations and forecasts across retries.
Interrupted publication leaves no partial accepted receipt. Receipts are integrity
checks in a trusted local research directory, not third-party digital signatures.

## Tests and real artifact acceptance

- 59 new tests cover real distinct fitted mixed-format artifacts, both state branches,
  wrong formats/provenance, damaged state, frozen-file mutation on all entry points,
  context/identity/source/timing rejection, inference delay, concurrent capture,
  first-receipt preservation, accumulated/conflicting/partial results, endpoint closure,
  failed registration, symlinks, missing evidence, publication interruption and bounds.
- Focused selection: **145 passed in 6.82 seconds**. Full Python suite:
  **1,411 passed in 146.83 seconds**. Full source/test lint passed.
- All 77 old test files and all old package sources are exact. The full suite replaced
  four disposable normalized caches; their test bytes were preserved privately before
  restoring the sealed copies. No source data or previous experiment was revised.

Adding a module changes the shadow format's full package source hash. The accepted old
artifact was therefore loaded in its unchanged old checkout to produce an exclusive
control; the new implementation was committed and frozen before fitting. Both source
versions reject the other's shadow artifact, and the reverse check explicitly proves
rejection before deserialization. No envelope was rewritten or validation bypassed.

The new freeze is
`969eb8eeb77d09f051ee52c415eb2d15e5ffa7d138e9b4149166e51eda3a355c`.
The input cutoffs remain ATP 2026-09-05 and WTA 2026-09-06. The same WTA selection,
main/enriched sealed frames, sigma0=1, q=0.0001, threshold32, five bags, seed and
calibration split were retained. This was a single registered migration fit.

Acceptance proves:

- Complete main and selected feature frames match the old frames exactly: **129,209
  rows each, all 43 columns**, with no population or feature changes.
- All five fitted booster byte hashes, calibrator serialization and both dynamic-state
  receipts match the old model. Raw forward and paired calibrated fitted outputs on
  **all 129,209 selected rows** are bit-for-bit identical. These fitted outputs are
  migration witnesses, not out-of-sample estimates.
- Six 30-player matrices match exactly: Hard/Clay/Grass on September 7 and October 7,
  each containing 435 unordered pairs. The old all-17-fold OOS reproduction remains
  the historical acceptance evidence; it was not rerun or re-counted as confirmation.
- Feature rebuild took **35.96s**; the fixed final fit took **3.92s**.

The rebuilt artifact is
`runs/prospective-shadow/migration-001/candidate.shadow` under the research root. Its
SHA-256 is `43dd88b1461913f11b90b6d2aa6aa82f7bbfe3ba7ad597d978c6a46b73d45fcc`;
artifact ID is `4c0c716b-7af3-48a9-a24c-f06a3d59431a`, trained at
`2026-09-08T00:13:38Z`. Caller-pinned provenance is saved as
`runs/prospective-shadow/provenance.json`. The incumbent remains
`runs/maintenance/wta-final-001/predictor.pkl` with its strict `.envelope` sibling.

The full-size models were registered in `migration-001/synthetic-qa`. Invented schedule
and outcome fixtures exercised Rybakina–Sabalenka (main state) and Rybakina–Lukas (lower
state). Both were captured, a retry preserved the first receipt, successive result
batches accumulated one then two graded pairs, and a simulated endpoint was stable and
rejected late intake. Every registration/report says `synthetic-qa`; there are **zero
real forecasts or fresh outcomes**. Future grading clocks exist only in the private QA
driver. Do not run this synthetic directory as a live pilot; its future timestamps are
simulated. Read its saved endpoint only as QA evidence.

## Source readiness and remaining work

Read-only inspection found no production data adapter emitting `earliestStartAt`,
`actualStartedAt` or `finishedAt` for this protocol. `data/live.py::parse_upcoming`
combines scheduled and in-progress rows and reduces provider time to a local date.
`parse_events` likewise exports a date and completed result, without actual start/finish
proof. Its acquisition receipt's `completedAt` means fetch completion, not match finish.
`data/wta_results.py::timing` uses bounded event dates and, when permitted by estimate
flags, a played date; it does not certify an actual start/finish interval. No new
provider calls were made in this phase, and no claim is made about current API semantics.

**Next is the source adapter and an observation audit, then an actual future pilot.**
The exact implementation order, interface, commands and open decisions are in
[the next-session handoff](2026-09-07-prospective-shadow-next.md). Existing CSVs and
retrospective caches must not be relabeled as fresh source observations. The runner
and migrated model need no retuning or repetition while those dependencies are built.

The selected candidate's historical validation effect remains
+0.00023999 ±0.00012794 paired naive SE on 15,628 matches; the week-block interval crosses
zero and winner accuracy fell by 27 matches. A 200-pair pilot is chiefly an operational
check and initial fresh estimate, not adequate power for such a small effect. See
[the unchanged confirmation design](2026-09-07-shadow-confirmation-plan.md).

## Preservation and records

The original checkout, five completed research checkouts and new input copy match their
inventories. All 18,791 original input files have eight distinct filesystem copies,
including the read-only snapshot. All 25,826 snapshot files were verified. Protected
run-file checks cover 56 Phase 3, 77 Phase 4, 104 maintenance, 61 selected-model and 37
old-shadow files. Existing package sources, tests, PROGRAM, workflows and web remain
exact. The new source/input freeze verifies after acceptance.

[The result JSON](2026-09-07-prospective-shadow-result.json) records exact commits,
provenance, tests, migration and synthetic receipts, preservation counts, private driver
hashes and all files under `runs/prospective-shadow`. Keep every exclusive run directory,
including controls and synthetic evidence. Only documents and append-only log additions
are mirrored to the original checkout. Nothing was merged, pushed or deployed.
