# Physical start calibration and conditional implementation protocol

Status: **design ready; no independently qualified witness exists yet.** This document
specifies what must be measured and then implemented. It does not declare a source
qualified, create a registration, or authorize a purchase, provider contact, automation
or model adoption. Read the [evidence review](2026-09-08-timing-contract-review.md) first.

## Workstreams and dependencies

| Step | Concrete output | Depends on | Can proceed alongside |
|---|---|---|---|
| A. Witness feasibility | One raw physical first-serve observation with an independent UTC anchor and defensible clock/delay bounds; otherwise a recorded failure reason | Access to an admissible observation of the exact match | B |
| B. Live source versions | Immutable pre-play, in-play and completed snapshots with identity and all revisions preserved | Published current-edition match IDs and actual play | A; C after the first useful pair |
| C. Revision interpretation | Observed version diffs and tested handling of correction/deletion/restart cases | At least two real versions from B | Remaining A/B collection |
| D. Witness adapter | Audited external module, immutable evidence schema and adversarial tests | A succeeds; field/identity contract fixed; relevant C behavior understood | Coverage recalculation |
| E. Registration readiness | Qualified producer version plus feasible calendar/collection coverage | B–D complete and coverage adequate | Nothing that can backdate a forecast |
| F. Prospective evaluation | Fixed 30-day capture, day-37 settlement; paired scores and uncertainty | New future registration from E | Normal production remains independent |

These are parallel workstreams, not a request to launch agents or unattended jobs.
Start with A/B evidence. Do not implement D speculatively or repeat broad provider
searches because the external witness is unavailable.

## A. Obtain a usable physical observation

1. Fix tournament ID, edition, singles category, round, court and both real players.
   Preserve the source MatchID and independently confirm the observation shows that
   exact matchup. An edition is mandatory: 2025 `LS001` is not a discovered 2026 match.
2. Identify the first physical serve from uninterrupted context, including the lead-in.
   Do not select the first point won, first visible score update, a resumed segment or
   the first serve after an edited replay cut. Record the frame/sample bracket that
   contains the ball strike, including sampling/annotation uncertainty.
3. Establish UTC independently of the WTA event clock. Retain the synchronization
   evidence, measurement method, before/after checks, uncertainty/drift calculation,
   timestamp resolution, and any clock steps. A label saying UTC or a device file's
   creation time does not establish accuracy. A second scoreboard using the same
   supplier is not independent evidence.
4. If observing a broadcast, independently bound end-to-end delay for the actual
   observation, including production, distribution, buffering and playback. A generic
   claimed latency or player buffer reading alone does not measure that chain. Do not
   align the stream to the WTA timestamp being tested; that makes calibration circular.
   Replays with unknown delay fail. Direct observation can use zero broadcast delay
   only where the observation setup supports it; sensor/annotation error still counts.
5. Preserve the admissibly obtained raw witness or stable source reference with its
   digest, exact frame/sample locator, observation time, clock evidence and identity
   provenance. Record rejection reasons when any required evidence is missing. Avoid
   downloading restricted media or inventing a timestamp to complete the form.

For a display/observation clock bracket `[r_low, r_high]`, independently bounded clock
error `±c`, and delay `[d_low, d_high]`, the physical start interval is:

```text
S_low  = r_low  - c - d_high
S_high = r_high + c - d_low
```

Use consistent UTC units. The clock bound must cover the whole observation; the bracket
must include all frame/annotation uncertainty. A missing/unbounded term means no finite
qualified interval. This is an interval calculation, not an estimated fixed fudge factor.

For reported WTA marker `p`, its signed error relative to this witness is:

```text
reported_minus_physical ∈ [p - S_high, p - S_low]
```

Store signed bounds, source version and event index. Report sample errors descriptively.
One successful witness validates the procedure for that case only. Additional witnesses
should cover venues/devices/operators where known, normal and interrupted play, restarts,
corrections and clock transitions. An observed maximum error in a finite sample does
not certify an unseen future maximum. Prefer per-match independently justified intervals
until broader producer qualification has a defensible documented basis.

## B/C. Capture lifecycle versions and learn actual correction behavior

Use accepted `wta_orders.py` and `wta_event_audit.py` in the isolated research checkout.
The next collection must use a newly named destination. After a justified publication
check, discover the current edition's resolved main-singles IDs from the official order
and match API. Build event URLs using the already observed service contract; do not guess
draw positions. The 2025 final and semifinal are replay fixtures only.

For an initial manual session, set a maximum of eight retained HTTP reads: two for a
fresh page/API pair, one pre-play and one in-play event read for a selected match, then
two page/API completion reads and one final event read, with one contingency read only
if a concrete response warrants it. This is a proposed budget, not an active schedule.
Do not poll rapidly to fill it. Preserve 404s, rate limits, empty bodies and identity
replacements, stop on access/rate-limit boundaries, and do not retry without a new reason.
If the relevant stages have already passed, record that missingness and choose a future
opportunity instead of reconstructing an alleged pre-play capture.

Compare whole arrays, matched by source edition/match and event index only within that
identity. Record additions, removals, changed type/attributes/times, order regressions
and changes to the initial InProgress. An index is not presumed globally unique. Preserve
both old and new payloads and receipts; a rewritten current view is not a revision log.
Repeated InProgress after a suspension cannot replace original start. Different final
scores, participant changes or disjoint clock claims are conflicts, not averaging inputs.

The current single-array auditor has no cross-version contract. Add a version comparison
module only after real versions support its behavior. Unknown states remain explicit
findings. Neither a final point still marked P nor an API completion label supplies a
missing terminal event. Source observations without A remain engineering evidence.

## D. Exact conditional implementation scope

When A succeeds, add a new external `tennis_model/research/physical_start_witness.py`
and `tests/test_physical_start_witness.py` (proposed names; neither exists yet). Keep the
frozen package and model bytes untouched. Define the schema before code:

- Exact matchup identity, source/edition/MatchID and the independently supported linkage.
- Raw witness and calibration references/digests, capture/observation/intake times and
  the actual availability time of every required supporting claim.
- Physical-event identification and bracket, all error/delay bounds with evidence and
  scope, resulting UTC interval, producer/version/code hash and rejection reasons.
- Provenance graph that makes common upstream clocks visible; source URL diversity alone
  must never pass an independence check. Incomplete claims remain incomplete.
- Create-only write/read contract, bounded input, trusted-root/symlink and tamper checks,
  consistent with existing research evidence modules.

Unit and integration tests must cover absent/unbounded clock or video delay; circular
provenance; edited replay or resumed-match ambiguity; reversed/nonfinite intervals;
wrong event/edition/players; tampering; clock steps; late supporting evidence; precision
and strict eligibility boundaries. Mutation fixtures demonstrate rejection only; they
cannot qualify a live producer. Include one real retained witness derivation and a
full synthetic fitted-artifact end-to-end QA run with separate destinations.

Only after review of the real evidence and those checks should a new audited version of
`time_evidence.py` / `prospective_bounds.py` recognize the narrowly scoped producer.
Preserve rejection of unsupported schemas. Register that code for a **future** run;
never monkeypatch an existing registration, reinterpret old forecasts or promote the
2025 retrospective samples into prospective results.

## E/F. Unchanged evaluation conditions

The accepted primary grading requirement remains:

```text
forecast_capture + 5 minutes < original_schedule_lower <= S_low
```

All existing capture freshness checks, schedule-revision and identity exclusions,
completion upper-bound consistency, evidence intake deadlines, conservative combination
of compatible intervals and week-boundary handling still apply. Read the actual
[time-evidence contract](2026-09-07-time-evidence-interface.md) and code before changing
anything; this document does not replace them.

Keep 30 capture days, day-37 settlement and the 200-pair adequacy rule. Recalculate the
calendar immediately before registration, then account for unresolved players, schedule
labels, witness availability, delays and missing results. The older 116 full-window slots
plus 95 partial-Beijing slots are a ceiling, not eligible pairs or statistical power.
Without enough forecast/witness pairs, report insufficiency. Do not extend a failed run
after seeing its results or weaken first-serve evidence to increase sample size.

No start producer currently satisfies D/E. If A cannot be sourced and B is not yet
observable, finish that bounded session with the external dependencies recorded. More
boilerplate audits or model fits do not substitute for the missing measurement.
