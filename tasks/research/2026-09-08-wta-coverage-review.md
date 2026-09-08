# WTA coverage and official orders — review

Accepted source/test implementation: `b6df856dffa0f397b17f79b7511fe3bc5ff730f1`,
branch `codex/model-wta-coverage`, based on accepted `e10757f`. Git was reconciled before
this report. The implementation lives in the isolated `worktrees/wta-coverage` checkout;
original DEUCE receives documents and append-only logs. This phase advances data collection
and coverage planning. It provides no new model-performance estimate or adopted candidate.

Read the [contract](2026-09-08-wta-coverage-interface.md),
[acceptance manifest](2026-09-08-wta-coverage-result.json) and
[exact continuation](2026-09-08-wta-coverage-next.md).

## What the official calendar supports

The [official WTA calendar API](https://api.wtatennis.com/tennis/tournaments/?from=2026-09-01&to=2026-10-31&page=0&pageSize=100)
was retained at 2026-09-08 05:33:25.497502 UTC. It contains 31 editions, with a real
`numPages: 0` alongside `numEntries: 31`; this is not an empty response. Its explicit
ID/year, current dates, category, status, cancellation metadata and draw sizes supply
this date-based planning window: **September 8 inclusive through October 8 exclusive**.

| WTA event / edition | Level | Official dates | Singles entrants | Whole-draw ceiling | Window scope |
| --- | --- | --- | ---: | ---: | --- |
| 2075 / 2026, Guadalajara | WTA500 | Sep 13–19 | 28 | 27 | Fully contained future |
| 1139 / 2026, São Paulo | WTA250 | Sep 14–20 | 32 | 31 | Fully contained future |
| 1024 / 2026, Seoul | WTA250 | Sep 21–27 | 32 | 31 | Fully contained future |
| 1152 / 2026, Singapore | WTA500 | Sep 21–27 | 28 | 27 | Fully contained future |
| 1020 / 2026, Beijing | WTA1000 | Sep 30–Oct 11 | 96 | 95 | Partially contained future |
| 905 / 2026, US Open | Grand Slam | Aug 30–Sep 13 | 128 | 127 entire draw | Already underway; remaining unknown from calendar |

Four fully contained future tournaments offer at most **116** matches. Including the
entire Beijing draw gives an optimistic ceiling of **211**, although Beijing finishes
outside the window. No prorating or claim that all 95 Beijing matches fall inside it.
A 28-player draw supplies 27 matches, not 31; a 96-player draw supplies 95, not 127.
WTA125/team/cancelled/invalid/conflicting editions cannot inflate main-tour coverage.
Edition-specific cancellation is checked; a `customStatus2020` flag does not cancel 2026.

The 200-pair pilot threshold remains a coverage requirement, not a power calculation.
Even perfect collection of all fully contained events is insufficient. The 211 ceiling
leaves little room for unobserved schedules, timing/identity exclusions, withdrawals or
other ineligible results. It is not 211 usable observations. The older US Open draw's
seven pending slots remain separately dated evidence in the prior review; this planner
does not replace that with the entire ongoing draw. No pilot clock was registered here.

## Actual source research and adapter behavior

Eight retained HTTP responses, all successful, exhausted the bounded acquisition plan:
calendar; WTA order JavaScript module; Guadalajara 2026 and 2025 order pages; matching
2026 and 2025 WTA APIs; current WTA-rendered US Open order and a fresh paired WTA API.
Primary page research also used web browsing; “eight” counts retained adapter/probe
responses, not every web-tool request. Exact requests, headers, times, hashes and bytes
are in `R/runs/wta-coverage`; `R` is defined in the continuation handoff.

The [Guadalajara 2026 order](https://www.wtatennis.com/tournaments/2075/guadalajara/2026/order-of-play)
was unpublished at 05:34:09 UTC, paired with an empty API at 05:35:38 UTC. Its exact
widget identifies 2075/2026 and September 13–19, while offset `0` is unqualified.
The output is **unpublished**, not an authoritative zero-match schedule. No publication
time was promised by this source.

The [2025 Guadalajara order](https://www.wtatennis.com/tournaments/2075/guadalajara/2025/order-of-play)
provided released structure: nine day sections, 65 match occurrences, 59 unique MatchIDs.
The paired API has 59 matches, including 27 admitted main singles. There are 31 main-singles
page occurrences for those 27 matches because four are listed on two days; all 31 are
historical/nonscheduled and have no retained original start label. The page's six cross-day
repeat IDs across all populations are `LS008`, `LD015`, `LS015`, `LS026`, `LS017`, `RS026`.
A single snapshot cannot prove when those schedules changed. It must not be converted into
a temporal revision history. Completed API timestamps cannot reconstruct missing labels.
The inspected historical URL used the current `guadalajara` slug, while the observed year
selector used `guadalajara-500`; the returned widget's actual ID/year, not the slug, is the key.

The [current WTA US Open order](https://www.wtatennis.com/tournaments/905/us-open/2026/order-of-play)
was retained at 05:37:00.778430 UTC and paired with WTA API bytes at 05:41:23.049109 UTC.
It is a new WTA HTML-format witness, not another acquisition from the previously accepted
USOpen.org JSON collector. The page contains 16 days and 299 distinct match occurrences;
the API has 296 total rows and admits 124 main singles. Page/API identity and round checks
admit those 124; 175 other page occurrences stay outside this admitted population.
Both captures pass freshness at their acquisition time. This is not a claim they stay fresh.

Of the 124 singles, 120 are historical/nonscheduled. The remaining observations are:

| MatchID | Page day/court/order | Retained timing interpretation |
| --- | --- | --- |
| LS73992552 | Sep 8, Arthur Ashe, first | Printed 11:30 AM and offset −0400 agree with API: 15:30 UTC court start |
| LS73992554 | Sep 8, Arthur Ashe, second | Sequence-only; the API's separately zoned 23:00 UTC schedule is retained but not promoted to a printed clock |
| LS73992540 | Sep 9, Court TBC, first | Unresolved: no valid printed court clock |
| LS73992542 | Sep 9, Court TBC, second | Sequence-only |

Only a first-listed match may inherit its court's start label. Numeric offset, page date,
widget edition, printed round, MatchID, player IDs and API scheduled state/time must agree.
No dedicated-match or explicit-not-before semantics were qualified by these samples.
The WTA script converts `.js-start-time` attributes and expands commented court templates;
those comments are parsed inertly. Renderer error scripts are never executed. Zero-padded
`0905` card classes are accepted only when numerically identical to widget/API event 905.

All rows remain **schedule observations**. No actual-start bounds, first-publication proof,
forecast export or context donation is produced. The unchanged time-evidence gate refuses
this schema as a qualified live start source. Absent entries can only be compared between
complete, fresh source pairs for the admitted API main-singles population. Failed, stale,
unpublished, incomplete or tied-time captures cannot prove disappearance. Explicit player
or round contradictions persist in history even after a later positive observation.

## Implementation, validation and preservation

`research/wta_orders.py` adds create-only HTML capture, verified retrospective intake,
source-specific parsing and history over explicitly supplied collections. It reuses
`prospective_sources.py` for JSON transport and artifact primitives; older collectors,
identity tables, packages and evaluators are unchanged. There are no automatic retries,
redirect fallbacks or running schedules. `research/wta_calendar.py` produces bounded
planning ceilings from an exact calendar capture. Seven compressed fixtures retain exact
HTML/JSON samples and their provenance; the exploratory JS module remains in private runs.

**237 focused tests passed in 8.63 seconds**, including **62 new tests**. Checks cover real
fixtures, population/window boundaries, byes, source edition/round/ID disagreement, explicit
clock requirements, cross-day repeats, absent/reappearing observations, persistent identity
conflicts, partial/failed HTTP transport, immutable archives, filesystem guards, replay
integrity and unchanged timing-gate refusal. Lint and five real offline CLI operations pass.
The first test run exposed whitespace normalization and two test-expectation errors; the
validation record preserves those development outcomes. They are not failed model trials.

Real CLI intake creates three immutable collections, then reproduces 155 occurrences for
151 unique main-singles matches across two editions, zero observed temporal revisions and
one unpublished gap. The third collection contains no matches. These are retrospective
annotations using original source receipt times, not newly acquired prospective forecasts.

At acceptance (2026-09-08 05:55:11.812780 UTC), all **572** protected prior run files,
**91** frozen package files, both model payloads and **365** prior program/web/workflow
files matched. All twelve completed prior checkouts were clean. Only 33 inherited tracked
data files exist in the new checkout; there is no raw-training copy. Full external training
and snapshot inventories were last rehashed at 01:58:44.035725 UTC and were not repeated.
This round retains **34** run files, raising the next protected inventory to **606**.

Candidate adoption is still deferred. No fit, performance estimate, account, payment,
provider contact, unattended collection, live pilot, production merge/push or deploy.
The next useful dependencies are publication/progression and defensible timing evidence;
another immediate duplicate acquisition would not resolve them.
