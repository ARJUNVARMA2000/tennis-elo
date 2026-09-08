# Typed time evidence — evaluator accepted, start producer still required

Implemented at `10c07ee726632f7186522e423205d661169123ce` on
`codex/model-time-evidence`, in
`.research/2026-09-06-model-foundation/worktrees/time-evidence`. Git was reconciled
against the completed source-audit checkout before final reporting. This phase changes
measurement engineering, not model parameters or the historical adoption decision.

**The exact-finish requirement is removed in a separate evaluator version.** A normal
completed-result observation supplies a finish upper bound; actual-start evidence must
still establish that the paired forecast finished more than five minutes before play.
The new evaluator accepts typed start intervals and explicit timestamp error bounds,
retains contradictory evidence, and pins its external implementation in registration.

## What now works

`tennis_model/research/prospective_bounds.py` implements `prospective-bounds-v2`.
It reuses the frozen runner's filesystem/model/identity/context helpers and owns its
version-specific receipts, capture, grading and reporting. This keeps the saved model
package hash unchanged. V1 does not read v2 registrations; old registrations and QA
remain immutable. External code hashes cover this runner, `time_evidence.py` and the
unchanged acquisition adapter. Both strict artifact loaders and provenance remain.

`time_evidence.py` implements conservative interval arithmetic. Timestamp error expands
an actual-start event outwards. A lower bound is required; first observed live play,
schedules, not-before labels and completion observations cannot substitute for it.
Disjoint start claims conflict. Overlapping complete claims use their conservative
union; a completion upper bound can tighten the start upper edge but cannot strengthen
its lower edge. Equality at the five-minute boundary fails. Partial claims cannot be
assembled into a fictitious complete observation.

Completion observations from successive updates need not have equal timestamps. The
earliest supported upper bound remains valid. Conflicting terminal status, winner or
supplied score excludes the pair. The new source producer also retains disagreement
between terminal provider records instead of silently dropping those records from an
update. It carries each provider's participant/round identity even when that row is
not a jointly confirmed normal result. A reused provider match ID or earlier schedule
revision excludes affected forecasts while retaining their original receipts.

The fixed 30-day capture interval, seven-day settlement grace, ten-minute schedule
freshness check, 200-pair coverage threshold, first forecast and post-inference clock
checks remain. An actual-start interval spanning a UTC calendar week leaves overall
and event statistics usable, but withholds week-block uncertainty for the full sample;
the evaluator does not assign an invented week to that match.

**No live start producer is qualified.** Registration defaults to `live` and explicitly
refuses it before creating files. Only an explicit `synthetic-qa` registration is
available. This is an engineering acceptance boundary, not a live research result.
Adding a validated start producer requires a new external code version and registration,
not another model fit or migration while package code remains unchanged.

## Primary research and actual source evidence

The [2026 Grand Slam rulebook](https://www.itftennis.com/media/5986/grand-slam-rulebook-2026-f2.pdf),
printed pages 9 and 18, describes not-before scheduling and match commencement at first
serve. The [2026 WTA rulebook](https://photoresources.wtatennis.com/wta/document/2026/08/10/f7e04e05-20c2-4f22-979c-3bbfdb3aa778/2026-WTA-Rulebook-7-27-2026-.pdf),
printed page 401, requires designated or not-before times for specified late-round
matches. These scheduling rules do not establish a field-level API timing contract or
prove that every sampled schedule is unrevised. A published official-order evidence
path remains worth validating; the code does not silently treat it as qualified.

No new live scoreboard requests were necessary this phase. The deterministic completion
producer reread the exact accepted ESPN/WTA raw responses from the preceding phase:

- **119 normally completed results** produce corroborated completion upper bounds.
- **246 provider identity rows** remain available for replacement detection.
- **Zero provider-result conflicts** were present in this retained pair of responses.
- **Zero verified start bounds** were produced.

The corroborated observation time remains **September 8, 2026, 00:48:17.709639 UTC**,
the later of the two original receipts. Conversion did not refresh that time. The new
batch retains raw-body and acquisition-receipt hashes and source mapping evidence.
These are historical source observations, not 119 prospective predictions.

## Validation

**58 new tests** passed; **231 combined targeted tests passed in 9.92 seconds**, including
the existing acquisition, mixed-format runner, shadow and strict-artifact suites.
Full source/research/test lint passed. The frozen package and all **82 preexisting
tracked test/fixture files** remain byte-identical. The earlier 1,411-test full-suite
result belongs to the runner migration phase; it was not rerun this phase.

Tests cover precision and timezone arithmetic; missing/reversed/future/unsupported
bounds; strict margins; partial updates; conflicting intervals/results; terminal source
disagreement; earlier schedules and identity-only replacements; source-body tampering;
cross-week grouping; post-inference and intake-deadline races; role/provenance/code/policy
changes; symlink destinations; first receipts; and immutable endpoints.

One full-size acceptance completed at **01:57:53.541433 UTC**, taking **10.86 seconds**:

- The unchanged incumbent and candidate loaded strictly, with **no fitting**.
- Two explicitly invented matchups exercised main and lower-state prediction branches.
  Their probabilities exactly matched direct calls to the same full-size models.
- Both forecasts were captured. Missing start proof initially excluded one completed
  result; complete typed updates then accumulated **1 → 2** graded pairs.
- A retry preserved the first forecast and did not duplicate the result batch.
- The simulated endpoint was stable and rejected late intake. Live registration failed
  before creating a directory.

The QA registration used actual local time; subsequent capture/settlement clocks,
matchups and outcomes were simulated. Every QA experiment is labeled `synthetic-qa`.
The retained real completion batch was audited separately and was not admitted as a
fresh source observation into that QA registration. No QA forecast may be upgraded or
later scored as a live pilot.

Initial local launch mistakes used a wrong relative working directory and an absent
test filename; they failed before that work ran. The missing-file test log is retained,
then the corrected combined selection passed. Early new tests passed while lint issues
were still being corrected; the committed source passed both. Full-size acceptance ran
once successfully. These were command setup errors, not failed model experiments.

## Preservation and remaining work

All 415 protected prior run files, 25,826 read-only snapshot files, seven protected data
inventories and eight distinct copies of each of the 18,791 original input files were
verified. The frozen runner contract, model package, original adapter, PROGRAM,
workflows and web remain unchanged. No new training-data copy, dependencies, model fit,
parameter selection, source polling, scheduler, merge, push or deployment occurred.

The remaining dependency is a **validated start-evidence producer and actual collection
cadence**. Do not build another generic evaluator or repeat acceptance merely because
start data is unavailable. The next-session plan specifies the bounded source work and
what must change before activation. The corrected incumbent remains current and
candidate adoption remains deferred: this phase adds no independent performance evidence.

See [the measurement record](2026-09-07-time-evidence-result.json) and
[the exact next-session handoff](2026-09-07-time-evidence-next.md).
