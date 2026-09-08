# Source adapter contract — before implementation

Implement `tennis_model/research/prospective_sources.py`, outside the frozen package.
No source/model/evaluator changes or fitting. Current evidence consists of an ESPN
scoreboard and WTA US Open catalogue/matches, each captured once with true local times,
plus one preserved sandbox DNS failure. Inspection is not model observation.

Transport has explicit ESPN-current/WTA-match endpoints, bounded JSON bytes, single
attempts, no redirects, a timeout, local request/receive timestamps and monotonic
elapsed time. Save raw bytes and bounded metadata including HTTP Date/Age/cache headers
before publishing a final integrity receipt. Preserve non-200, timeout, malformed,
oversized and interrupted attempts; never fall back to cached data as fresh. Reject
symlink paths through the existing filesystem helpers. No arbitrary URL fetch option,
credentials, pagination/backfill loop or scheduler. Record HTTP age without claiming it
proves the provider's match-level freshness.

Offline audit reads exact retained bytes and records raw source locations. It handles
women's singles separately from other groups; qualifying is not main draw. Round IDs
alone cannot establish draw size. Match identity includes source edition and match ID;
provider duplicates, participant changes and ambiguous rounds are explicit failures.
Map WTA/ESPN events only through compatible edition bounds and at least eight unique
completed main-draw results agreeing on canonical pair, round, winner and games score,
covering >=80% of each provider's normally completed main-draw population. Sponsor
names are not join keys. Early/partial events may remain unmapped; report this coverage
limitation, and never loosen it after looking at model scores.

For a mapped main-tour event, WTA supplies draw size, surface and I/O setting; use the
existing tour tier/round configuration. Schedule candidates require both providers
scheduled with the same real pair and round, WTA's explicit zoned NotBeforeISOTime,
false estimate indication, and agreement between normalized WTA/ESPN schedule stamps
and the not-before bound. Missing or conflicting fields stay excluded. This is a
provisional field mapping; lifecycle semantics are not yet independently validated.
No arbitrary default context or event-name join.

Completed results can supply canonical winner and score, but this version has no
verified actual-start/finish mapping. Preserve that missing proof and explicitly label
all completion evidence unscoreable. Never manufacture finish from fetch time, elapsed
play duration, or the last update timestamp. Build diagnostic runner-compatible batch
shapes, but the live-export entry point must refuse activation while timing semantics
and a real pre/live/post lifecycle remain unverified. Synthetic integration tests may
exercise draft candidates under an explicit QA registration; no production forecasts.

A lifecycle report compares retained snapshots by exact source match ID and also
tracks event/round/pair collision and replacement evidence. It records status, schedule,
score and identity changes, including regressions and source divergence; it never
turns first/last observation into an exact actual start or finish. No disappearance is
implicitly a cancellation. Repeated identical snapshots are not a complete lifecycle.

Test raw provider fixtures with immutable provenance plus explicitly synthetic negative
variations. Freshness, HTTP failure, bounds, source shape, canonical identity, round and
scope, timezone/not-before parsing, conflicting clocks, missing actual timing and
frozen-runner integration are required. Final acceptance uses a second bounded live
sample under the tested adapter and compares it with the first actual observations.
If no valid pre/live/post series or actual timing exists, D3/D4 remain unmet and the
handoff must state the precise additional evidence/protocol work needed.
