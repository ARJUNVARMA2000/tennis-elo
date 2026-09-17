# Phase 1 data and timing audit — 2026-09-06

Read with the [implementation review](2026-09-06-phase1-review.md),
[bounded census](2026-09-06-phase1-coverage.csv), and
[machine-readable evidence](2026-09-06-phase1-data-audit.json).
This is a read-only audit of the Phase 0 archive, not a data refresh or an acquisition.

## Population and denominators

The normal loader in the unmodified A checkout reconstructed 284,893 ATP enriched
rows and 146,078 WTA enriched rows. Data-through dates are 2026-09-05 and 2026-09-06,
respectively; 2026 is partial. Their normalized fingerprints reproduce Phase 0.
The audit uses the complete frames, not the one-row main caches preserved from the
original project. Main means normalized `draw_level=main`; lower roles are reported
separately. Main-draw observed counts alone cannot establish coverage.

For serving statistics, valid means `has_stats`, positive finite service-point totals
for both players, and finite nonnegative first/second-serve points won whose sum does
not exceed service points. There are 50 ATP and 5 WTA `has_stats` rows failing that
definition in the complete enriched archive. This is a check on the quantities used
by the serve estimator, not a certification of every box-score field.

| Tour/year, main draw | Observed | Completed | Valid serve stats | Completed with valid stats |
|---|---:|---:|---:|---:|
| ATP 2024 | 3,157 | 3,037 | 3,096 | 2,998 |
| ATP 2025 | 2,938 | 2,809 | 2,664 | 2,562 |
| WTA 2024 | 2,121 | 2,078 | 2,109 | 2,077 |
| WTA 2025 | 2,492 | 2,402 | 2,006 | 2,002 |

The CSV adds qualifying/Challenger/125 roles and 2023/partial-2026. The JSON separates
walkovers and other noncompleted rows and reports player/source-ID presence. Normalized
rows do not retain source provenance or an identity-confidence score. ID presence is
not a substitute for correct identity. Expected complete-calendar counts for ATP,
other WTA years and lower tiers remain **unknown**, rather than inferred from observed
row counts or a nominal draw size.

## Independent WTA checks

The independent denominator comes from the frozen first-party WTA calendar and finished
singles match-list responses, rather than the normalized results being audited. Match
keys are year/event ID/match ID plus the real pair. When those IDs are unavailable,
require the exact normalized pair, round and calendar date overlap; search adjacent
calendar years because an early-January event can start in December. Exact-ID matches
take precedence. Multiple candidates remain ambiguous. No event-name similarity is used.

| Catalogue | Calendar events seen | Events with finished lists | Finished singles listed | Matched | Unmatched | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|
| WTA 2024 | 53 | 51 | 2,193 | 1,629 | 555 | 9 |
| WTA 2025 | 51 | 50 | 2,336 | 2,322 | 12 | 2 |

These are **catalogued finished results**, not the model's completed-only scoring
population. The source's `MatchState=F` and winner marker do not establish retirement/
walkover eligibility. All listed rows have parseable match timestamps, but the audit
does not establish historical publication times. Player aliases, uncertain date bases,
status/score interpretation and duplicate records still require adjudication. The
counts above are unmatched under the declared matching policy, not 555 certified
newly admissible matches.

The 2024 catalogue has 127 unmatched rows each at Roland Garros (903) and the US Open
(905), 93 at Madrid (1038), 89 at Rome (709), 85 at Miami (902), and 29 at Auckland
(1049). Those IDs and raw match lists provide a concrete results-recovery sample.
No unmatched 2024 row has cached statistics with positive service denominators for
both players. Thus the presence of match metadata does not imply available box scores.

Among uniquely matched 2025 rows, 313 have no normalized serve statistics: 125 at the
Australian Open, 124 at Roland Garros, 63 at Wimbledon and 1 at the US Open. None of
those 313 has a cached whole-match statistics record with positive denominators for
both players. One of the 12 unmatched 2025 rows has positive cached denominators;
that alone does not certify a valid/admissible box score. Investigate that single
case before changing merge rules or estimating recoverable volume.

No finished list was found in the preserved catalogue for United Cup in either year
or Wimbledon 2024. This is a limitation of the cached denominator, not proof those
events were absent from the model. An earlier diagnostic restricted observed rows to
the calendar year and overstated 2025 missing results by 36; the final audit includes
adjacent years. Its earlier 2024 matched/ambiguous split is superseded by the table.

## Lower-tier evidence already available

For each player, find their first observed main-draw date, then count strictly earlier
lower-tier player appearances. Same-day appearances do not qualify. The counts are
player appearances, so one match may supply evidence for two future main entrants.

| Tour | Players with lower evidence before observed main debut | Earlier player appearances | Debut 2010–19 | Debut 2020+ |
|---|---:|---:|---:|---:|
| ATP | 1,091 | 27,225 | 500 | 330 |
| WTA | 331 | 1,781 | 77 | 254 |

This demonstrates relevance of lower data, not incremental benefit of another source.
Archive coverage is left-truncated, so first observed main appearance is not necessarily
a career debut. ATP players outside the two listed windows debuted before 2010.
Existing WTA first-party lower history begins in 2016; do not advertise 2010 coverage.

## Blocking timing repair: B3-R1

The historical CSV path interprets `tourney_date` as `date`. The WTA statistics adapter
uses `MatchTimeStamp` when syntactically present and otherwise the event start, but
discards which basis was used. ESPN uses competition dates. Normalized chronological
ordering sorts date before event/round. A mixture can therefore put a later round
before an earlier round from the same event and player.

The bounded knockout audit found seven one-day ATP inversions in 2024, across events
341, 4787 and 6242. For example, Michelsen's semifinal loss to Bonzi is stored on
November 3, before his quarterfinal win over Yunchaokete Bu on November 4. Shapovalov's
Belgrade final is similarly stored before his quarterfinal. The current walk ingests
the later-round outcome first; fixing league priors does not repair Elo, player serve,
H2H or fatigue chronology. This is a **blocker before baseline evaluation**.

An eighth ATP candidate is event 2026-416 / Ben Shelton with a 26-day gap; retain it
as an unresolved event/date-identity candidate, not a confirmed within-edition error.
No WTA knockout inversion was found by this bounded test. That is not proof of valid
WTA chronology: same-day, cross-event and unknown-time cases are outside its detection.
The initial unqualified event-ID grouping also joined different years of bare `Rome`;
the final diagnostic groups by year and event, and keeps long-gap cases separate.

Required repair before the Phase 2 freeze:

1. Preserve source, source match/event identity, event edition, and the original date
   basis through normalization. Keep played time and observation/availability time
   separate. Do not assign fabricated hours or treat tournament start as result time.
2. Reconcile the seven concrete inversions against the raw source rows; use verified
   played dates where available. Otherwise adopt an explicit conservative within-event
   order/availability policy that cannot put later-round results into earlier forecasts.
3. Investigate the 2026-416 identity candidate independently. Date-overlap/player evidence
   must support any join. A calendar-year label alone does not identify an edition.
4. Add failure fixtures covering mixed date bases, same-day batches, overlapping events,
   and these actual rows. Test all affected walk-time/prediction-time state mirrors.
5. Supply verified `stats_available_at` and `stats_availability_basis` to the new serve
   prior, or explicitly retain/explain exclusion. Reconcile population/version changes,
   rerun normalized identity and feature checks, then freeze a **new** baseline input
   manifest while preserving Phase 0.

At present neither frozen normalized frame has an availability/basis column. Therefore
the new prior admits **zero** real historical observations and uses its fixed 0.62
initialization. This is an honest fail-closed implementation, not a deployable estimate
or a claim of improved forecast quality. Style reconstruction excludes the target day
but remains retrospective by played date because MCP publication timing is unknown.

Calibration policy is also documented: research annual folds calibrate on the preceding
calendar year, with a small-sample fallback that can reuse training rows; production
uses a rolling last-365-day calibration split. Phase 1 changes neither schedule nor
calibrator fitting. Exact-hour fatigue, travel and calibration-policy experiments stay
in the later backlog.

## Acquisition queue and source capabilities

| Priority | Work | Evidence, scope and cost |
|---|---|---|
| 0 | Repair date/provenance and prior availability | Mandatory before scoring. Uses frozen raw evidence first; no new feed required to reproduce the defect. |
| 1 | WTA missing **results** recovery pilot | Adjudicate a bounded 2024 event sample by stable IDs, scores and status. Metadata exists even when statistics are zero. Keep staging separate from the frozen baseline. |
| 2 | WTA main-draw serving-stat sample | Probe the 2025 Slam gaps against a distinct source. Cached WTA responses do not recover the 313 matched gaps. Require nonzero, internally consistent samples before expanding. |
| 3 | Extend relevant lower history | Target players/periods absent before main debut, especially the tune years. WTA 125/qualifying are already partially present; generic volume is not evidence of incremental coverage. |
| 4 | ATP main/stat gaps and older lower history | ATP 2025 has 247 completed main matches without valid serve stats. Establish an independent event/match denominator before attributing source failure. |
| 5 | ITF or a paid point feed | Coverage, stable IDs, historical timing and permitted use remain unverified. Obtain a representative sample and maintenance-cost estimate before any purchase. |

TML's own repository now directs current data access to its website and describes GitHub
as a historical/technical reference; it does not establish completeness for our frozen
files. [TML primary source](https://github.com/Tennismylife/TML-Database).
The configured historical WTA mirror is a separate analysis repository, not a verified
current official feed. [Mirror repository](https://github.com/zeldao08/tennis_players_analysis).
MCP supplies match metadata and contributed chart statistics; those files alone do not
establish when a historical chart was publicly available.
[MCP primary source](https://github.com/JeffSackmann/tennis_MatchChartingProject).
These pages were checked on 2026-09-06; none was ingested into model inputs.

The local WTA adapter supports main, qualifying and 125 roles, event/match/player IDs,
and incremental cached fetches. Its historical lower cache starts in 2016. Repository
operating guidance records rate limiting after roughly 2,000 calls and requires
one-year-at-a-time backfills; no new rate-limit experiment was performed. ITF coverage
and a reliable result-only historical ingest path remain unverified.

Recommended initial data hypothesis: adjudicated missing WTA main results, with
identical scored keys and protected priors between arms. **A 2024-only addition cannot
pass the unchanged strictly-positive tune-2010–19 gate.** First establish comparable
recoverable tune-period evidence before registering an adoption experiment, or review
a proven population correctness repair before establishing the corrected baseline.
Do not waive the gate, quietly enlarge the scored population, or call a validation-only
repair an accepted model improvement. Acquisition confidence is currently higher for
recoverable result records than for recoverable serve statistics; predictive benefit
has not been measured.

## Reproduction and limits

Private row manifests live at
`.research/2026-09-06-model-foundation/runs/phase1/data-audit-fast/` in the original
project. The final read-only driver is `tools/phase1-data-audit-fast.py` under the same
run root; its hash is in the committed JSON. Run it from worktree A's `tennis_model`
with its own Python runtime and `PYTHONPATH=src`. It writes only private audit outputs.
The JSON also includes the reviewed identity/completion and candidate classifications.

This audit does not certify all event identities, full calendars, all score statuses,
historical data availability, or an acquisition yield. Slow exploratory census passes
were stopped and replaced with a vectorized audit; failed diagnostics are not research
trials and no performance-based candidate selection occurred.
