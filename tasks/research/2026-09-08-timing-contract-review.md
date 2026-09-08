# Official timing contract review — September 8, 2026

**Decision: the public WTA event stream remains useful but unqualified as physical
start evidence.** Four retained primary-document reads did not establish the missing
field-to-physical-event mapping and UTC error bound. No live producer or model change
is justified by this round. The deliverable is a completed evidence review and a
[concrete calibration and implementation protocol](2026-09-08-timing-calibration-protocol.md).

## Primary evidence, with limits

| Source | What the reviewed material establishes | What it does not establish |
|---|---|---|
| [2026 ITF duties and procedures](https://www.itftennis.com/media/2509/duties-procedures-for-officials-2026.pdf), PDF/printed pp. 5, 18, 32–34 | A match commences at first serve. A fixed visible tournament clock is designated. Scorecards record set start/end times; handheld scoring enters points before announcements. Device operating instructions are referenced to the officiating portal/on-site. | Public WTA `InProgress.Timestamp` semantics; device/server timestamp origin; UTC synchronization, drift, operator delay, or a numerical error bound. These 2026 instructions do not prove 2025 device behavior/compliance. |
| [2026 WTA rules, July 27 version](https://photoresources.wtatennis.com/wta/document/2026/08/10/f7e04e05-20c2-4f22-979c-3bbfdb3aa778/2026-WTA-Rulebook-7-27-2026-.pdf), PDF pp. 343/345/353/404, printed pp. 340/342/350/401 | Main-tour provisions cover an official visible clock, prompt handheld scoring, tablet-controlled serve clocks, and designated/not-before times for specified late-round matches. These are the main-tour sections, not the later WTA 125 duplicates. | The serve countdown is not an independently calibrated UTC clock. Scheduling rules do not map a JSON field to actual start. No public field-specific accuracy bound was established. |
| [WTA–Stats Perform announcement](https://www.wtatennis.com/news/3812740/stats-perform-extends-exclusive-official-rights-partnership-with-the-wta), 2023 | Describes official data rights and both an umpire feed and a more detailed in-venue feed. | Which stream, transformation or clock generates the retained public WTA payload. A second website may share upstream data; publisher diversity alone is not independence. |
| [Stats Perform MA21 documentation](https://developers.statsperform.com/feed-ma21-tennis-predictions), published June 25, 2026, matchInfo table | Distinguishes `officialStartDate`, `actualStartDate` and `lastUpdated`, documents UTC values and UUID fixture identity, and requires OAuth for service access. | A namespace/provenance bridge to WTA's public PascalCase fields, or a physical timing error guarantee. No service request, account or provider-prediction ingestion was performed. |

The two current PDFs were searched for whole-word UTC, `synchron`, `timestamp`, and
`InProgress`; no matches were found. Relevant whole pages were rendered and visually
checked, including their printed page numbers. This bounded search is not proof that
no public clock contract exists. A third-party scorer-manual mirror was excluded from
the authoritative evidence; no portal login was attempted.

## Mapping to the retained Guadalajara evidence

The existing auditor and full raw records, not documentation labels, establish these
retrospective observations:

| Field/observation | Final LS001 | Semifinal LS002 | Permitted interpretation |
|---|---|---|---|
| Tournament/edition | 2075/2025 | 2075/2025 | Same source namespace and completed singles identities corroborated against retained order/API evidence. |
| Reported initial InProgress | Sept 14, 21:09:00.403Z | Sept 13, 22:08:12.887Z | Reported transition only; not a qualified first-serve instant. |
| API MatchTimeStamp precedes InProgress | 1,283.073 seconds | 1,421.560 seconds | These main API timestamps cannot be substituted for reported InProgress. |
| Events / scoring records | 185 / 119 | 220 / 136 | Real retained records. Both final game scores agree with the completed-match API. |
| Terminal F event | Absent | Absent | Last scoring state remains P; completed score agreement does not create an absent terminal transition. |

`TimestampLocal`, `Timestamp`, `MatchTime`, `referenceTimeAsLocalTime` and millisecond
precision may support internal checks. Their agreement does not establish independent
accuracy. The prior synthetic common ten-minute shift still passes arithmetic while
remaining ineligible. `FirstServe` on a scoring record is not a physical match-start
timestamp. The WTA bundle's coarse LIVE includes pre-play states.

**Remaining qualification chain:** physical first serve → observable trigger → producer
clock with documented uncertainty → exported field and correction history → exact match
identity → immutable receipt. The rules support the target event. The public source
supports reported markers. The middle of this chain is unresolved.

## What can now move forward

1. Use an independently timed first-serve witness for one exact match, following the
   protocol. Begin with evidence feasibility before writing an adapter. Unbounded
   broadcast delay or an uncalibrated local clock cannot produce an eligible interval.
2. Independently, retain real event versions during covered play and examine corrections,
   repeated start markers, disappearing indices and terminal behavior. Existing adapters
   already handle initial source capture and single-array audit; do not rebuild them.
3. Only with qualifying evidence, implement a separately versioned witness producer and
   future registration. Historical fixtures remain calibration material. A finite sample
   of small offsets is not a universal clock-error guarantee.

More model fits do not resolve this particular evidence gap. Waiting helps only if it
produces new schedules, live versions, qualifying witnesses or prospective pairs. No
change to the original candidate verdict or performance estimate is claimed here.

## Acceptance and preservation

Base `27cc95af1cb72aa56b316a6fcea30771a3d18094`; checkout
`.research/2026-09-06-model-foundation/worktrees/timing-contract`, branch
`codex/model-timing-contract`. Existing event code remains at `f355253`; this is a
documentation/evidence round with no new program or test implementation.

The [result manifest](2026-09-08-timing-contract-result.json) records four successful
bounded reads, nine visually inspected PDF pages and two offline event-report replays.
At **2026-09-08T14:03:31.807592+00:00**, all **635** protected prior run files, **91** frozen
package files, both model payloads and **384** prior program/web/workflow files matched.
Fourteen prior accepted checkouts were clean; 33 inherited tracked data files were the
only data files in this checkout. The 29 new run files bring the next protection total
to **664**. Source copies, renderings and receipts are local research evidence.

No suite was rerun because program/test code is unchanged. The prior 296 focused passes
in 11.34 seconds belong to the WTA lifecycle round. Large external training/snapshot
inventories were last fully verified at **2026-09-08T01:58:44.035725+00:00** and were not
rehashed here. Git history was reconciled with the inherited implementation before this
review. Candidate and incumbent hashes remain unchanged. Original DEUCE receives only
documents/logs; no forecasts, fits, training copies, account, unattended collector, live
pilot or production change occurred.
