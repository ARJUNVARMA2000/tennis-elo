# Official schedule collector — implementation accepted

The free US Open route is now implemented and tested. Implementation commit:
`cda539332c98f5983bf6950da999e74d03d02d5e`, branch `codex/model-official-schedule`, based
on `64e70227281c1433a825fa7032a131c9a95ceb12`. Git was reconciled before this review.
The original checkout continues to receive documents and append-only logs only.

Read the [collection contract](2026-09-07-official-schedule-interface.md),
[acceptance manifest](2026-09-07-official-schedule-result.json) and
[next-session handoff](2026-09-07-official-schedule-next.md).

## What works

`tennis_model/research/usopen_schedule.py` provides manual collection, exact retained
sample import and history reporting. It fetches at most two public JSON documents per
invocation: the official catalogue and one explicitly selected released order. URL,
edition, date, venue clocks and source identities are checked. Redirects and arbitrary
URLs are refused; a failed catalogue stops the daily request.

Each new directory preserves attempts, exact response bytes, hashed receipts and a
reproducible collection report. Existing archives cannot be overwritten. History verifies
those archives and retains all supplied versions, source links, original timestamps,
coverage exclusions and failures. It detects earlier times, opponent/round replacement,
court/session/order changes, cancellation text and missing/reappearing matches. Identity
conflicts remain visible after a reversion. A failed, stale, malformed or incomplete
update cannot establish disappearance. A missing row is not automatically a cancellation.

The three exact JSON samples are committed as small compressed test fixtures, with
raw and receipt provenance. Imports retain their original observation times and are
explicitly labelled retrospective. This is not a new historical training-data copy.
No PDF parser was added: the earlier four-page visual check remains the semantic evidence;
encoded PDF text is not reliable input for this source.

## Real check and evidence limits

Both retained orders replay successfully: 132 source rows, six WTA singles observations,
one explicit not-before and five first-match session starts. The day-17 catalogue epoch
still points to the prior date; the displayed date and court clocks establish the
schedule date, and the discrepancy is reported rather than silently repaired.

One new collection made exactly two successful public reads. The day-17 response was
received at **2026-09-08 03:25:15.926970 UTC** (September 7 in New York). Its 60 source
rows include the same two WTA matches, and its raw bytes exactly match the earlier daily
response. The combined history has six distinct WTA matches and eight preserved versions,
with zero observed revisions and zero gaps. A real revision lifecycle has therefore
**not** been witnessed; revision behavior is covered by explicitly synthetic mutations.

The two current rows use first-session starts. They do not establish independently
verified actual starts. No forecast, model result, new start bound, live registration,
scoreboard join or performance claim was created. The accepted evaluator and
`time_evidence.check_mode()` are unchanged. No unattended collection or live pilot is active.

## Verification

- **146 focused tests passed in 5.19 seconds**, including 46 new collector tests and
  existing source, time-evidence and bounds tests. Ruff and whitespace checks passed.
- Real retained imports, archive replay and the history CLI passed. The fresh public
  check succeeded through the same collector; there were no retries or additional reads.
- Tests cover the actual catalogue practice link, wrong catalogue epoch, intentional
  blank, mixed populations, two sessions on one court, timing distinctions, malformed or
  reused identities, revisions/reversions, missing matches, HTTP/media/partial failures,
  provenance tampering, interruption and filesystem/output boundaries.
- During development, the first fixture run exposed the catalogue's null-day practice
  link (18 failed, 24 passed). It is now explicitly excluded; unrelated invalid day rows
  still fail closed. An initial helper import/path inspection and lint issues were also
  corrected before acceptance. These were development failures, not research results.

At **2026-09-08 03:27:18.941405 UTC**, verification confirmed all 526 previous run files,
91 frozen package files, both model payloads and all 354 preexisting tracked files under
the program/web/workflow trees were byte-identical. Ten completed research checkouts
remained clean. This checkout has only the 33 inherited tracked data files, with no raw
training directory or new training copy. Full original training/snapshot inventories were
last verified at 01:58:44 UTC; that expensive check was not repeated in this source-only phase.

The current phase adds 27 retained run files; their hashes are in the result manifest.
The next protected inventory contains **553 files**. The verification driver is retained
at `R/tools/official-schedule-verify.py`, with its hash in the manifest.

## Decision and remaining work

U0–U1 implementation and U3 preservation are complete; U2's bounded real acquisition
also succeeded. The operational schedule source is useful now. The next substantive
research step is a future order with explicit not-before semantics, subsequent real
versions, and a justified timing premise. More retries of this unchanged order cannot
supply that evidence. A schedule-based exploratory study would require a separately
recorded assumption and preregistration; it cannot silently replace the primary gate.

There was no model fit, dependency change, account, purchase, provider contact, production
merge, push or deployment. The model candidate remains deferred; this improves data
collection and auditability, not measured prediction quality.
