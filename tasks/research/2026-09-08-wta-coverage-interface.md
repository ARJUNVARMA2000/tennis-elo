# WTA coverage and order observations — bounded implementation contract

From accepted `e10757f`, user continuation authorizes a concrete external WTA calendar
planner and order observer. Frozen packages, prior collectors/evaluators and models stay
unchanged. Eight source responses retained: calendar; WTA order module; current
and 2025 Guadalajara order pages; corresponding WTA match snapshots; current WTA-rendered
US Open order and its fresh paired WTA match snapshot. The last pair is a new WTA format
witness, not a repeated US Open publisher feed.

## Calendar capacity

Use the official catalogue's explicit event ID/year, main-tour level, start/end dates,
status, cancellation metadata and actual singles draw size. Deduplicate identical ID/year
rows; conflicting duplicates invalidate their event. Do not count WTA 125, team competitions,
cancelled events or unknown/invalid metadata. Validate the full bounded page inventory;
the actual response reports `numPages: 0` and 31 entries, so validate row count/page size
instead of assuming that zero pages means no data. Multi-page/partial responses cannot
support a complete calendar claim.

A date-based 30-day window is a planning envelope, not the evaluator's timed registration.
Separate future events wholly within the window, partial future events and already-started
events. A knockout draw with N actual entrants has at most N-1 played matches; byes are
not extra matches. Do not prorate partial events or infer remaining matches from calendar
status. Report started-event capacity as unknown unless separately supported by a retained
same-edition result snapshot. The existing US Open snapshot supplies a separate seven-slot
observation; keep its original source time and do not silently add a full 127-match draw.

Report whole-draw ceilings and exclusions, not expected eligible pairs or statistical power.
The initial actual future inventory gives 116 slots in four fully contained events plus
95 slots in partially contained Beijing. Those 211 slots are an optimistic ceiling, not
211 available observations. Model timing/identity and normal-result gates still apply.

## WTA order parsing and source agreement

Use the exact `tournament-oop/order-of-play` widget's numeric event/year and date range.
Hero headings and event-name slugs are not identity keys: historical URLs can display
current evergreen header information. Parse inert official day comments/templates without
executing JavaScript. Keep match occurrence keys by edition, day and MatchID; rescheduled
matches can appear on several days. Duplicate same-day occurrences remain explicit.

Associate each match card with an existing main-singles WTA API row by MatchID and verify
its widget/class edition, source player IDs per side, printed round and provider status. Doubles,
qualifying and unresolved participants are exclusions. Preserve all page/API raw receipts
and observation times. A historical API response may have replaced original schedule
fields with completion data; never reconstruct earlier labels from completed records.

Only the first listed match in a court group can inherit an explicit court-start label.
Convert that label using its explicit date and numeric UTC offset, requiring agreement
with the widget offset and the API's explicitly zoned schedule timestamp. A later match
with no dedicated published time is sequence-only. Missing/render-error court clocks,
placeholder offset `0`, ambiguous match qualifiers, conflicting clocks or status changes
produce unresolved time observations, never invented bounds. Numeric offsets are publisher
claims, not independent venue/clock verification. Explicit not-before support is not
qualified by these samples and is not inferred from API field names.

Future Guadalajara currently has no order widget days and an empty match list: report
`unpublished`, not zero scheduled matches or a complete absence snapshot. Successful
HTML transport with no recognized widget, failed JSON, partial payloads and a stale
pair are gaps. Preserve failures and original bytes. No retry or alternate URL fallback.

## Operations, versions and tests

Provide create-only manual collection and retrospective intake of verified captures,
plus history over explicitly supplied archives. Retain changed times, day/court/order,
opponents/rounds/status, missing occurrences and reappearances; incomplete/unpublished
snapshots cannot delete prior observations. A conflict across any version persists.
Compare occurrence sets between collections: two days retained in one page are not
two temporal revisions. Carry explicit player/round contradictions into the history even
when they exclude a row; compare player-to-ID mappings independently of source side order.
Absence coverage is limited to the admitted API main-singles population, not every draw slot.
Use existing filesystem/receipt primitives and the existing WTA JSON transport; add
only the WTA HTML transport and source-specific interpretation.

Tests use exact current/historical samples and synthetic negatives: calendar pagination,
duplicate/cancelled events, 28/96-player byes, boundary/partial windows; header/widget
edition mismatch, comment parsing, cross-day repeats, same-day duplicates, identity,
court-start versus sequence, offset/clock disagreements, unpublished state, transport
errors, immutable versions and unchanged timing-gate refusal. Retained intake is labelled
retrospective even when original sources were observed before scheduled play.

All outputs remain schedule observations/planning only. No forecasts, live producer,
actual-start proof, evaluation export, training copy, fit or production deployment.
