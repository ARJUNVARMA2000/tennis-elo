# Official draw identity audit — contract before implementation

This bounded continuation reuses the immutable schedule collector. Two schedule reads
at 04:31 UTC found no revisions and no released day after September 8. Two new official
draw reads returned the index and its WS draw. The work now removes an identity dependency
while later play/publication is pending; it does not qualify start times.

## Inputs and source boundary

An external `research/usopen_identity.py` audit consumes the exact, validated official
draw index/WS response and retained ESPN/WTA captures. Canonical official URL paths must
have the explicit edition and WS code. Require a unique WS index entry, bracket format,
128-player size, seven rounds and the complete 127-slot round census. Reject duplicate
match IDs and real matchup keys. Keep unresolved slots and malformed/contradictory rows
in exclusions. Generic draw epochs and event-day numbers do not become played timestamps.

Use the existing ESPN/WTA event audit unchanged. Corroborate the official draw with its
already uniquely selected event through at least eight and 80% of the larger completed
result population, requiring canonical real players, round, winner and winner-oriented
set games. Official edition must match the WTA edition. No event-name similarity or
hardcoded ESPN ID is used. Result agreement supports identity, not source independence
or an actual-start clock. A later draw snapshot must not freshen older provider receipts.

## Match links and contradictions

Only publish a match link when the draw, WTA and ESPN have a unique canonical pair/round,
and the US Open player numbers (explicit `wta` prefix) agree **per player** with WTA
PlayerID fields. This is a strict sample predicate, not a claim that the namespaces are
globally interchangeable. The actual initial comparison has 23 mismatching matchups;
retain their numbers and exclude them rather than proposing aliases or changing config.
Never modify identity tables outside their established proposer workflow.

Retain status differences as observations. A later completed draw against an older live
provider is a possible progression, not by itself a terminal conflict. Conflicting
normal terminal winner/games, malformed terminal scores or winner flags prevent the
affected link. Unknown terminal states remain unqualified. All affected match IDs and
reasons stay in the audit even if the broad event identity remains corroborated.

The schedule association entry point must replay trusted immutable collections first.
Each version is checked against its draw match ID, edition, round and per-player IDs.
An identity mismatch in any supplied version or retained history conflict excludes all
versions of that ID. Associate six sampled matches only if these checks pass. Preserve
every version's original receipt/time and compute a separate association-available time
no earlier than all contributing observations. Associations are retrospective and not
forecast/context donation or accepted evaluation input.

## Acceptance and non-goals

Test exact full response fixtures plus synthetic ID replacement, swapped IDs, changed
winner/score, duplicate IDs, wrong edition/population, unresolved slots, weak/ambiguous
event overlap, provider lag, provenance tampering and older schedule associations. Test
that event names do not join, and that even an accepted identity audit never qualifies
live time evidence. Reuse receipt/filesystem helpers; add no generic evaluator or transport
framework. Keep frozen model/package/source modules unchanged.

Primary timing-rule verification remains the accepted limitation: the Grand Slam rules
describe not-before scheduling and separately define commencement at first serve; they
also discuss changing schedules. Inferring actual play from a schedule requires a
compliance premise, not supplied by the API. No new start producer, live registration,
forecast, scheduled automation or performance result is authorized by this audit.
