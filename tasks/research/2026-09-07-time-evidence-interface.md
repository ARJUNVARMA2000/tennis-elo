# Prospective bounds v2 — contract fixed before implementation

This is a separately versioned external evaluator in `tennis_model/research/`, based
on the accepted v1 runner. The frozen package, v1 receipts and fitted model bytes stay
unchanged. Code hashes of the external runner, evidence module and source adapter are
part of registration, alongside the unchanged strict model contracts. No refit.

## Supported meanings and readiness

An explicit actual-start event with a declared symmetric error bound gives an interval;
an independently measured actual-start interval already has lower/upper endpoints.
Both require a producer, exact matchup key, evidence observation time and source digest.
An observed normal completion supplies a finish upper bound, not an exact finish time.
No scheduled timestamp, not-before label, first observed live score, HTTP Date/Age or
reported playing duration is accepted as actual-start proof by this implementation.

Only the synthetic start producer is qualified in this version. `live` registration
must fail before creating files; adding a live producer requires a new audited code
version and a future registration. This is an explicit remaining integration dependency,
not an assertion that real timing can never be obtained. QA registration is never live.

A deterministic ESPN/WTA completion producer reads existing validated captures, applies
the accepted event/match/result mapping, and preserves both source receipt hashes and
raw body hashes. Use the later response receipt time as the corroborated completion
upper bound. The original acquisition timestamps remain unchanged; conversion time
cannot freshen them. This producer does not create start evidence. It excludes all
rows that fail the existing normally completed agreement rule, retaining audit counts.

## Eligibility and conflicts

At capture, the unchanged five-minute/ten-minute checks use the provisional schedule
lower time and the post-inference clock. At grading, require independently supported
`capture + 5 minutes < original schedule lower <= actual-start lower` and a consistent
start interval no later than the observed completion upper bound. Equality fails.
Evidence observations must be no later than batch observation/intake; intake closes
exactly at registration + 37 days. Keep the 30-day capture window and 200-pair adequacy
check. Completion receipt after the deadline is not admissible, even for older matches.

Start evidence is typed: exact-with-error or explicit interval. Invalid, unqualified,
wrong-identity, future, reversed or contradictory claims fail closed. Several complete
claims may corroborate; they never repair a partial claim by assembling invented fields.
Disjoint start intervals conflict. Use their conservative union for eligibility after
checking consistency. Repeated completion observations can have different timestamps;
use the earliest supported completion upper bound. A bound does not move later on retry.
Any terminal-status, winner or supplied-score conflict excludes the pair. Missing start
proof is explicit, not pending once a normal completed result exists.

Preserve schedule revisions and provider identity replacements: an earlier schedule for
an already captured matchup invalidates its schedule proof; a provider match ID reused
for another participant/round excludes both affected matchups. Keep all evidence.

Week grouping remains based on actual start, but an interval crossing a UTC calendar
week cannot identify that block. Such pairs remain in overall/event statistics; report
week uncertainty as unavailable for the entire sample until every graded start interval
has a single known week. Do not silently move uncertain matches into a chosen week.

## Engineering and acceptance

Create-only registration/forecast/result/endpoint files, strict role loaders, first
forecast preservation, post-inference clock checks, source-host checks, accumulated
partial updates, bounded JSON, symlink protections and fixed endpoint reporting remain.
Use a separate schema; v1 readers reject v2. No monkeypatching of the frozen runner in
production code. The external evaluator can reuse frozen filesystem/model helpers,
but owns its schema and timing-specific capture/grade/report interpretation.

Test boundary/offset/precision arithmetic, unsupported claims, completion observation
updates, source/raw tampering, revisions, identity replacement, stale/future clocks,
late intake, cross-week intervals, role/provenance/code changes and immutable endpoints.
Run a real fitted-artifact synthetic experiment end to end; separately report actual
source completion coverage and zero verified starts. Preserve old outputs and hashes.

## Primary research behind this choice

The 2026 Grand Slam rulebook, printed page 9, describes consecutive and not-before
scheduling and says a released order should remain unchanged. Printed page 18 defines
match commencement at the first serve. This supports a possible official-order evidence
path but is not a field-level API contract or a guarantee against revised schedules.
[Official Grand Slam rules](https://www.itftennis.com/media/5986/grand-slam-rulebook-2026-f2.pdf).

The 2026 WTA rulebook's media standards, printed page 401, require designated starts or
not-before times for specified late-round matches. That establishes scheduling usage,
not actual-start semantics for ESPN/WTA JSON fields.
[Official WTA rules](https://photoresources.wtatennis.com/wta/document/2026/08/10/f7e04e05-20c2-4f22-979c-3bbfdb3aa778/2026-WTA-Rulebook-7-27-2026-.pdf).

These are paraphrases of primary documents inspected this session. No assertion about
an unobserved rule exception or a paid provider's coverage is made. No new live feed
poll is needed to establish the completion bound from already retained raw responses.
