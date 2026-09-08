# US Open schedule observation contract — v1

Authorized by “Build on official feeds and keep going.” This implements U0–U1 of
the accepted free-source handoff, outside the frozen model and evaluator packages.

## Acquisition and provenance

`research/usopen_schedule.py` accepts an explicit edition (2000–2100) and tournament
day (1–60). A manual `collect` invocation creates a new directory, then makes at most
two requests: the canonical `www.usopen.org` schedule catalogue and its selected
released day. The daily URL must equal the edition/day-specific official URL. No
redirects, retries, accounts, PDFs, scripts or arbitrary URLs are fetched. Unreleased
days and failed catalogues stop the second request. Each request has a pre-request
attempt record, exact bounded bytes and a hashed receipt, including failures.

Files are create-only within a descriptor-validated trusted root. Interrupted folders
remain incomplete and cannot be replayed as successful collection. Receipt time is
acquisition time; source `epoch`, `releaseTime`, `lastWrite` and HTTP clocks are retained
as hints. None proves first publication or actual play. Historical imports must match
the committed byte/receipt manifest of the three previously retained JSON samples;
their provenance is explicitly retrospective import, with original acquisition times.

## Normalization and coverage

The source is US Open WTA main-draw singles (`WS`), keyed by edition and match ID,
with two distinct real WTA player IDs, round code/label, court, session and order.
No ESPN/model joins occur. Validate the catalogue and daily long date labels, explicit
edition and weekday, and every court epoch against its printed New York clock/date.
Catalogue epoch disagreement is retained as an anomaly and never changes the date.
Reject duplicate IDs, sessions or orders; record malformed rows and population exclusions.
The intentional blank and catalogue's explicit null-day practice link are excluded separately.
A partial/invalid payload is never an
authoritative absence snapshot. Catalogue row count disagreement and stale/missing HTTP
clock evidence disable absence comparison; preserved valid observations remain auditable.

Keep `explicit-not-before`, `first-match-session-start` and `sequence-only` separate.
Ambiguous comments/conjunctions or invalid clock text suppress the normalized time and
record a reason. A later match with no explicit time has no inferred timestamp. All
observations carry source URL, raw/receipt digest, path, original timing/status strings,
acquisition time and `actualStartVerified: false`. PDF text extraction is not used;
the prior four-page visual review supplies the recorded semantic check only.

## Revisions and evaluation boundary

`history` verifies and re-derives reports from explicitly supplied immutable collections,
sorts by acquisition time, and retains every version. Its report states its input list;
it cannot claim to include unsupplied acquisitions. It detects participant/round reuse
across days, earlier times, other time changes, court/session/order/date changes, status
or cancellation-text changes, and disappearance/reappearance within the same day.
Failed, unreleased, stale or partial updates are reported as gaps, never deletions.
Identity conflicts remain flagged even if a later update reverts. Disappearance means
absent from the supplied complete order, not confirmed cancellation. Cancellation text
is an observation, not a qualified terminal result. Ordering ties are marked ambiguous.

No output has the accepted time-evidence schema; no live producer registration, model
fit, forecast, actual-start lower bound, evaluation export or production integration is
added. `time_evidence.check_mode()` remains unchanged. A manual real revision check is
limited to one catalogue/day-17 pair after tests pass. An unattended cadence and a
qualified timing premise remain separate future work.

## Verification and closeout

Use exact gzip fixtures of the three retained JSON responses with raw/receipt hashes.
Test the real six WTA rows and source anomalies; synthetic mutations exercise revisions,
malformed identity, timezone/edition conflict, stale/missing data, HTTP errors, HTML,
partial bodies, immutable publication, symlink/output boundaries and evaluator refusal.
Replay both retained orders, then the bounded live pair if feasible. Preserve all 526
previous run files, 91 frozen package files, model artifacts and completed checkouts.
Record focused tests, exact revision findings, limitations and next-session commands;
commit research and mirror documents/logs only to the original checkout.
