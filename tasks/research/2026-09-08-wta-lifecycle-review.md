# Official WTA event timelines — accepted research

**WTA's own tournament event feed provides reported match stages and scoring events.**
The inspected Guadalajara 2025 final and semifinal have 405 records, including two explicit
InProgress markers. The new audit finds no internal clock or identity contradiction and
corroborates both final game scores. These remain reported events with unknown physical
clock error; no actual-start producer, forecast or live model evaluation was enabled.

Source/tests commit `f355253f75071cfedeafe15adf67898d52aa36e2`, isolated
`codex/model-wta-lifecycle`, based on accepted `781d37b`. Git was reconciled before this
report. Read the [contract](2026-09-08-wta-lifecycle-interface.md),
[acceptance manifest](2026-09-08-wta-lifecycle-result.json) and
[next-session handoff](2026-09-08-wta-lifecycle-next.md).

## Actual acquisitions

Six retained HTTP responses: four 200s and two empty 404s. This counts retained source
acquisitions, not primary web-page searches/retrievals. No retry or extra endpoint guessing.
Exact attempts, receipt times, headers, bytes and digests remain in
`R/runs/wta-lifecycle`, where `R` is the research root in the handoff.

1. The accepted WTA order collector acquired a current US Open HTML/API pair, completed
   at **2026-09-08 13:32:46.632425 UTC**. This is over seven hours after the previous pair.
   Both are fresh at acquisition; all 124 admitted main singles are unchanged. Comparing
   every available same-event WTA collection yields 248 occurrences, zero revisions,
   zero gaps and no identity conflicts. The pending timing distinctions are still one
   first-court label, two sequence-only observations and one unresolved first-court time.
2. Existing match/API/order fixtures established Guadalajara 2075/2025 and IDs `LS001`
   (Arango–Jovic final) and `LS002` (Jacquemot–Arango semifinal). The retained official
   player-service module constructs the exact per-match endpoint; the store explicitly
   requests `point-by-point`. No match ID, edition or URL shape was guessed.
3. Both `/events` reads succeeded, at 13:33:03.023510 and 13:33:34.005191 UTC.
   Both `/point-by-point` reads returned 404 with zero bytes. Failure records stay intact.
   This demonstrates event coverage for these two WTA tournament matches; it does not
   establish universal coverage or independent clock accuracy.

## What the event records establish

| Observation | Final LS001 | Semifinal LS002 |
| --- | --- | --- |
| Event records | 185 | 220 |
| Scoring events: Point + Ace | 119 | 136 |
| Reported OnCourt, UTC | Sep 14, 20:47:45.150 | Sep 13, 21:44:47.967 |
| Reported PlayersArrived, UTC | Sep 14, 21:02:06.957 | Sep 13, 22:01:00.707 |
| Reported Warmup, UTC | Sep 14, 21:04:18.557 | Sep 13, 22:03:27.893 |
| Reported InProgress, UTC | Sep 14, 21:09:00.403 | Sep 13, 22:08:12.887 |
| First scoring event, UTC | Sep 14, 21:09:32.930 | Sep 13, 22:08:57.393 |
| Final observed scoring event, UTC | Sep 14, 22:44:17.580 | Sep 14, 00:00:58.367 |
| Main API timestamp before InProgress | 1,283.073 seconds | 1,421.560 seconds |
| Elapsed arithmetic residual range | −0.396 to +0.590 seconds | −0.887 to +0.103 seconds |
| Final game score in API player order | Arango–Jovic 4–6, 1–6 | Jacquemot–Arango 4–6, 5–7 |
| Explicit terminal F event present | No | No |

Sources: [official final events](https://api.wtatennis.com/tennis/tournaments/2075/2025/matches/LS001/events)
and [official semifinal events](https://api.wtatennis.com/tennis/tournaments/2075/2025/matches/LS002/events),
with exact retained captures rather than mutable URLs as the reproduction inputs.
The WTA's [final report](https://www.wtatennis.com/news/4362990/jovic-becomes-youngest-champion-this-season-with-guadalajara-title)
corroborates Jovic's 6–4, 6–1 win and reports 1h35m duration; its
[semifinal report](https://www.wtatennis.com/news/4362543/arango-jovic-seek-gaudalajara-glory-and-first-wta-title)
corroborates Arango's 6–4, 7–5 win. Neither article supplies physical start-clock uncertainty.

All events agree on the exact match/edition and known WTA player IDs. Local timestamps
agree with their explicitly zoned counterparts using the historical order widget's −0600
claim. Semifinal UTC midnight rollover correctly remains September 13 locally. Indices
increase but skip values; timestamps do not regress; no update precedes its event timestamp.
Gaps in indices do not establish a complete physical history or justify inserting events.

The main match API's `MatchTimeStamp` is **21–24 minutes earlier** than the reported
InProgress marker and close to the reported OnCourt stage. This is a measured discrepancy,
not a universal definition of MatchTimeStamp. It must not become an actual-start timestamp.
The events' `MatchTime` roughly equals timestamp minus reported InProgress, but agreement
between derived fields does not independently constrain their error against physical play.

The retained WTA bundle explicitly maps OnCourt, Warmup and other detailed states into
coarse LIVE. LIVE therefore does not mean the first serve has happened. A per-point
`firstServe` boolean is service information; it is not an instant for the first physical
serve of the match. Both histories end on scoring rows still marked P, despite matching
completed results in the separate API. Keep event-state completeness and result agreement
separate; do not fabricate a final-state transition.

The final's medical-treatment record (index 281) legitimately omits the duplicate
`Attributes.type`. An initial audit incorrectly required it; interpretation was corrected
to check duplicate fields only when supplied, before the test run. The exact fixture
protects this case. The record includes medical treatment reason/location and remains
part of the clock/identity audit rather than being dropped to make chronology look clean.

## What changed and how it was verified

`tennis_model/research/wta_event_audit.py` is a **read-only external auditor** over verified
retained captures and an accepted order collection. It adds no network collector or
production pipeline dependency. It checks exact edition, per-player identity, round,
all event rows, duplicate fields, stage order, source offsets, event/update clocks,
initial zero-score InProgress marker, later scoring, and final-score agreement.
Unsupported or contradictory rows remain findings; no isolated plausible start can
rescue an inconsistent full history. Failed/empty sources remain gap/unavailable.

It writes create-only, hashed audits with replay validation, source receipts and separate
source observation/evidence-availability times. The inspected captures are retrospective;
one array containing several historical stages is not several live observations. No
model context or forecast evidence is donated from it.

**59 new tests passed in 2.88s; 296 combined focused tests passed in 11.34s.** Lint and three
actual offline CLI replays passed. Regressions include exact source data, missing/duplicate/
late start stages, arbitrary clock shifts, UTC rollover, malformed records, per-player
replacements, source-side swaps, result disagreement, 404s, archive tampering, filesystem
guards and the unchanged evaluator's refusal to admit this schema as a live start producer.
A synthetic common ten-minute timestamp shift still passes internal arithmetic while
remaining unqualified. This demonstrates why the auditor never assigns ±1s error from
fractional timestamp display or residual agreement.

At **2026-09-08 13:44:02.934236 UTC**, all **606** prior run files, **91** frozen package
files, both model payloads and **377** prior program/web/workflow files matched. Thirteen
accepted prior checkouts were clean. The new checkout has only 33 inherited tracked data
files and no raw-training copy. The 29 new retained run files raise next protection to
**635**. Large external training/snapshot inventories were last fully rehashed at
01:58:44.035725 UTC and were not repeated here.

No fit, model adoption, new performance estimate, account, payment, provider contact,
unattended collection, live pilot or production merge/push/deploy. This phase narrows the
next source work to a demonstrated WTA event stream and its precise missing qualification.
