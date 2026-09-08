# WTA event timeline audit — bounded contract

From accepted `781d37b`, preserve all models, accepted source adapters and evaluators.
Current WTA order re-capture at 13:32:46 UTC has no revision across 124 admitted singles.
The two selected Guadalajara 2025 `/events` responses contain 185 and 220 records,
including explicit OnCourt, PlayersArrived, Warmup, InProgress and scoring events.
Both `/point-by-point` responses are empty 404s. The initial six-read budget is exhausted.

Implement one external, read-only `research/wta_event_audit.py`. It reads verified retained
inspection receipts, the accepted WTA match capture, and an accepted order collection
for edition/day/offset corroboration. It emits an immutable audit; no new network driver,
generic evaluator, forecast export, actual-start producer or model package change.

## Identity and source integrity

- Exact official API endpoint identity: numeric event, year, explicit main-singles MatchID,
  and `/events`. Verify original attempt/receipt fields, original byte hash and length,
  complete identity-encoded JSON, transport status, original acquisition clock and bounded
  size. Failure remains a gap; an empty event list is unavailable, never a complete history.
- Match the tournament headers across events, match list and order widget. Join on actual
  IDs and edition, not title. Admit only an already-normalized main-singles API match.
  Verify each `Players` key/id and canonical full name against the API player-to-ID mapping.
  Verify every event's match/event/year and any player/server/receiver references.
- Match round and identity must agree with every relevant order occurrence. Retain all
  occurrence dates; source-side swaps preserve a player-to-ID mapping. Do not infer aliases.
- Preserve original source receipt times/digests. Retrospective derivation cannot freshen
  source observation or create prospective first-publication evidence.

## Temporal falsifier and interpretation

Audit all records; never keep just one plausible start row. Index gaps are allowed, but
repeated/regressing indices, regressing UTC timestamps, updates before event time, future
claims, invalid/offset-free clocks, wrong local/UTC conversion, conflicting reference times,
unknown states/types, inconsistent duplicate attribute fields and illegal player references
remain explicit findings. Use the order widget's explicit numeric offset only as a source
claim; it is not independent venue-clock verification. Keep a narrowly bounded event-day
window spanning any retained order occurrences, including UTC midnight rollover.

Require a unique initial InProgress/P event at set 1/game 1, zero scores and zero MatchTime,
preceded in order by OnCourt, PlayersArrived and Warmup, then a real scoring event. Missing,
multiple, malformed or out-of-order initial transitions never yield an internally supported
reported-start marker. Preserve the reported marker for inspection separately from admission.
No sequence or a complete retrospective array establishes a live observed lifecycle.

`Point`, `Ace` and `DoubleFault` are scoring events; `firstServe` is per-point service
information, not the timestamp of the match's first physical serve. Fault/Let and break/
medical events remain separate. The actual samples' last scoring events still have state
P; absence of a final F state must not be silently repaired from the completed API.
Compare a completed API's winner-first game score to the final observed event score in
API player order; a mismatch is explicit, while a matching score is corroboration within
this publisher, not an independent result producer.

Report raw `Timestamp`, `TimestampLocal`, `LastUpdated`, `MatchTime`, state/reason and index
for transition markers; first scoring and final events; elapsed-clock residual range;
API MatchTimeStamp-to-InProgress gap; final-score agreement; and findings. An elapsed clock
within a second of event timestamps is algebraic consistency, not a ±1s accuracy contract.
The feed exposes fractional seconds but this does not establish physical accuracy or
operator/reporting delay. WTA's retained bundle classifies OnCourt and Warmup as LIVE;
LIVE alone is not equivalent to the first serve.

## Tests and immutable outputs

Use both exact event responses, both retained 404s and existing match/order fixtures.
Test edition, match, per-player identity, source side swaps, failed/empty timelines,
malformed/duplicate/shifted clocks, date rollover, missing/multiple/late initial markers,
ambiguous firstServe booleans, score disagreement and unchanged evaluator refusal.
Verify tampered raw bodies and derivations cannot replay successfully; outputs are
create-only and guarded from production paths/symlinks. Run focused existing source/bounds
tests as well as new cases. No full model retrain or dependency install is required.

Every output has actualStartVerified=false and readyForLiveEvaluation=false. No actual
start interval/error budget is synthesized. Further qualification requires independent
physical-time semantics and uncertainty plus new observed pre-play/live/terminal receipts.
