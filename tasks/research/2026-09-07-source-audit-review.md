# Source adapter and timing audit — engineering complete, live readiness unmet

The external acquisition/audit adapter is implemented at
`c9b5b17bc7cbb78816bc5fbf8c75ceb2ee83d561` on `codex/model-source-audit`, in
`.research/2026-09-06-model-foundation/worktrees/source-audit`. Initial implementation
was `65b79d6`; the final commit adds failure exit status, production-output rejection
and a linear lifecycle scan. Git was reconciled after acceptance. Dates in filenames
refer to September 7 local time; acquisitions occurred September 8 UTC.

**This phase successfully built and tested source acquisition and diagnostic conversion.
It did not establish live-pilot readiness.** No source adapter can manufacture the actual
start/finish evidence required by the currently frozen runner. The audit exposed a
measurement-design assumption in the preceding plan: exact finish time is not inherently
needed to score a prediction, while defensible proof that capture preceded play is
essential. The next work should explicitly revise the evidence contract to use supported
time bounds, or validate a provider with actual event timestamps. Do not repeatedly
refit the unchanged model or relax timestamp meanings silently.

## What was implemented

Added `tennis_model/research/prospective_sources.py`, outside `src/tennis_model`, plus
42 tests and compressed exact provider fixtures with a provenance manifest. The entire
model package, old prospective runner, selected parameters and artifacts remain exact.
No model fit or extra training-data copy was needed. The old shadow artifact still
loads under its unchanged source contract in this checkout.

The transport has explicit ESPN-current and WTA-edition endpoints, a 25-second timeout,
an eight-MiB response limit, no redirect following, no retries or cached fallback, and
no credentials. It saves an exclusive attempt receipt, exact bounded body bytes and
final integrity receipt. Metadata includes true local request/receive timestamps,
monotonic elapsed time, status, Date/Age/cache/media headers, body completeness and
adapter hash. Files publish atomically without replacement through no-symlink parent
checks. HTTP, parse and transport failures remain visible; the CLI returns failure
status. Source receipts cannot be written into this checkout's production output.
HTTP age and observation age are checked separately, and neither is presented as proof
of the provider's match-level update latency.

The deterministic audit excludes other tours/groups, doubles, qualifying, lower-tier
WTA populations, unknown rounds, placeholders and invalid identities. It uses explicit
WTA draw size for draw-relative rounds, requires distinct provider player IDs, and
rejects duplicate match identities. Event mapping uses edition bounds and at least
eight unique completed pair/round/winner/games agreements covering at least 80% of
both providers' normally completed, parseable main-draw results. Sponsor names do not
join anything. This conservative rule can leave early or incomplete events unmapped;
it is a declared coverage limitation, not a general event-registry replacement.

Draft schedules require a shared scheduled matchup, an explicit zoned WTA
`NotBeforeISOTime`, a false estimate flag with no conflicting flag, valid ESPN time,
and agreement between the normalized WTA timestamp, ESPN date/startDate and not-before
bound. Factual surface, indoor/outdoor, tier and round context are mandatory. The
adapter handles timezone offsets and date rollover, and retains exclusions.

**Those drafts are diagnostic candidates, not approved live exports.** The live-export
entry point refuses activation. Completed draft results deliberately omit
`actualStartedAt` and `finishedAt`: no mapping for those fields has been validated.
Observation timestamps are never substituted for match timestamps. Draft batches retain
the original acquisition times and source receipt hashes; they cannot make old inputs
fresh. Do not manually pipe them into a live registration to bypass the readiness result.

Lifecycle comparison follows exact provider/event/year/match IDs. It records participant,
round, status, score and timestamp changes, rejects duplicated source IDs, and prevents
identity changes or status regressions from counting as a complete pre/live/terminal
sequence. A disappearing row is not declared cancelled, and first/last observation is
not renamed actual start/finish. No collector or scheduler is part of the module.

## Primary evidence actually inspected

Six successful public HTTP reads were made: initial ESPN, WTA tournament catalogue,
WTA matches, one WTA completed-match statistics response, then a second ESPN and WTA
match response through the tested adapter. One initial sandbox DNS failure is preserved
separately; it was a local network restriction, not evidence of a provider outage.
No backfill, page-walking loop, paid feed or account access occurred.

The [ESPN WTA scoreboard](https://site.web.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard?limit=300)
was captured at **00:26:27.699355** and **00:48:10.433894 UTC** on September 8.
The [WTA US Open match response](https://api.wtatennis.com/tennis/tournaments/905/2026/matches?page=0&pageSize=100)
was captured at **00:27:12.491559** and **00:48:17.709639 UTC**. These URLs are mutable;
the private receipts and exact body hashes in the result JSON preserve the observations.

The WTA response returned 296 rows despite the page-size query; this is an observed
response count, not a claim about documented pagination or overall event completeness.
124 rows explicitly describe main-draw singles; one has an unknown opponent. The
corresponding ESPN main draw also has 123 real-player matchups after scope/identity
filtering. Exactly **119 normally completed results agree** on canonical players,
round, winner and games score. They corroborate WTA event **905 / 2026** with ESPN
**189-2026**. Other contemporary ESPN events are rejected as mapping candidates.
These are source-membership facts, not new model-performance observations.

| Evidence | Observation | Consequence |
|---|---|---|
| ESPN `date`, `startDate`, `timeValid` | Present on scheduled and completed rows | Do not infer actual start from field name or flag |
| WTA `MatchTimeStamp` | Present on all 124 main singles rows | Must respect estimate flags and status-specific semantics |
| Estimate flags | 79 of 124 main rows have a true estimate indication | Cannot certify actual time merely because a timestamp exists |
| WTA `LastUpdated`, `MatchTimeTotal` | Null on all 124 main singles rows | Cannot recover actual finish from these fields |
| WTA `NotBeforeISOTime` | Present on four upcoming rows | Two yield consistent, real-player diagnostic candidates; other rows remain excluded |
| Two providers' completed-match time fields | 66 of 119 equal; signed ESPN-minus-WTA differences range −300 to +85,800 seconds | Agreement on results does not validate time semantics |
| Actual start and finish proof | Zero verified result rows | Current runner cannot score these as prospective completed pairs |

The two provisional schedules are Sabalenka–Noskova at 15:30 UTC and Pegula–Navarro at
23:00 UTC on September 8. They are **audit observations, not recommendations or live
forecasts**. Another not-before-bearing row has an unresolved opponent; the remaining
real pair fails ESPN time confirmation and also exhibits inconsistent schedule fields.
No missing context or time was filled merely to increase the candidate count.

The single [WTA statistics response inspected](https://api.wtatennis.com/tennis/tournaments/905/2026/matches/LS74124882/stats)
contains a whole-match statistics row with empty `settime`, not actual start/finish
stamps. This is a one-match finding, not proof that no WTA endpoint can ever provide
such evidence. The official [WTA scores page](https://www.wtatennis.com/scores) is a
score UI, not a field-level API timing contract; targeted documentation searches did
not establish the required meanings. The attempted official order-of-play PDF lookup
returned no readable content and was not used as proof.

For a possible alternative, Sportradar's primary
[tennis timeline documentation](https://developer.sportradar.com/tennis/reference/sport-event-timeline)
defines timestamped timeline events, including `match_started`, and separately describes
estimated/confirmed scheduled time. The interface requires an API key. No account,
trial, purchase, API call or coverage guarantee was made for that provider. Its docs
support a candidate avenue, not live readiness for this project.

## Tests and acceptance

- **42 new tests** cover exact real fixtures and synthetic mutations: identity/scope,
  event mapping, estimates, round ambiguity, timezone rollover, context, failure status,
  DNS/timeout/429/redirect/media/encoding/JSON/size/length failures, exclusive publication,
  symlinks, interruption, cache age, lifecycle replacements/regressions and output bounds.
- **187 focused tests passed in 7.45 seconds**, including the existing prospective,
  shadow and strict-artifact suites. Full source/research/test lint passed. All 78
  preexisting test files and every file in the frozen model package are unchanged.
  The prior full-package run remains 1,411 passing tests; it was not unnecessarily
  repeated for this external-only addition.
- The two final real fetches succeeded in about **0.31s** (ESPN) and **2.74s** (WTA),
  preserving approximately 1.97 MB and 346 KB respectively. At acceptance their HTTP
  ages were about 135 and 127 seconds, within the ten-minute acquisition bound.
  Match-level freshness remains explicitly unverified.
- Comparing the two actual observations found **four changed provider match records**,
  corresponding to three real matches. Changes were scores; the Gauff–Jovic match
  appears independently in both feeds. No full pre/live/terminal lifecycle was observed.
  The lifecycle census has 344 provider identities, including placeholders and other
  ESPN event populations; it is not 344 eligible pilot matches.
- The unchanged full-size incumbent and candidate loaded strictly and processed two
  diagnostic schedule drafts inside an explicitly `synthetic-qa` experiment. Both
  forecasts were captured, zero were graded and both remained pending against the
  independently acquired completed-result batch. A separate real-fitted unit test
  confirms that a matching completed result without actual timing is excluded.
  **There is no live registration or fresh model-performance result.**

The private acceptance driver's QA registration clock was simulated before the source
receipts solely to exercise the frozen runner. Every experiment receipt says
`synthetic-qa`; it must never be reused, upgraded, or later scored as a real pilot.
Actual acquisition receipts retain their real local timestamps. A first acceptance
launch used the wrong working-directory-relative script path and failed before the
driver existed or an experiment was created; its log is retained. The corrected launch
completed once in `acceptance-001`; no model fitting or source reselection was involved.

## Remaining work and preservation

The source adapter/audit phase is complete as a diagnostic implementation. **Live source qualification and pilot activation from the earlier activation
handoff remain unmet.** This phase’s D3 readiness assessment and D4 documentation
handoff are complete; neither counts as source qualification. The most useful next
scope is a separately versioned time-evidence protocol: allow proven bounds where
mathematically sufficient, retain strict pre-play proof, and validate the evidence
producer before any real registration. The next-session handoff gives the exact work
and acceptance requirements. More elapsed time alone cannot fill a field a feed never
supplies; neither should a protocol demand an exact timestamp when an explicitly
represented and validated bound would suffice.

All six completed research checkouts and original data inventories were checked. The
existing eight distinct copies of 18,791 original inputs and all 25,826 read-only
snapshot files remain intact; no ninth training copy was needed. All 377 protected
prior run files match their recorded hashes. Model sources, prior tests, PROGRAM,
workflows and web are unchanged, and the prior runner freeze verifies. No merge, push,
deployment, paid source or scheduled automation occurred.

See [measurements and hashes](2026-09-07-source-audit-result.json) and
[the next-session plan](2026-09-07-source-audit-next.md). Keep all private observations,
failed attempts, QA artifacts and drivers. The original checkout receives only documents
and append-only log additions.
