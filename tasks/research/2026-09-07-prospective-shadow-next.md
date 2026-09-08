# Resume here — source adapter, evidence audit, then future collection

Status: the mixed-format runner, 59 new tests and exact saved-candidate migration are
complete. No live experiment or collector exists. Do not redo the selected grid,
walk-forward gate, offline shadow implementation or migration. The engineering work
is not independent evidence that the candidate improves prediction.

## Locate and verify the completed work

Research root:
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation` (called `R` below).
Current checkout: `R/worktrees/prospective-shadow`, branch
`codex/model-prospective-shadow`. Implementation commit:
`89002bc909c16a06c734c921f8889e0c865c8ac3`. The subsequent documentation commit contains
this handoff. Read the tail of `tasks/todo.md`, the latest review/result JSON and
`2026-09-07-prospective-shadow-interface.md`, then reconcile `git log` and status.
The original `/Users/varma/Projects/DEUCE` checkout has documentation only.

Preserve coordinator, phase4, maintenance, dynamic-screen, dynamic-shadow, the latest
checkout, all exclusive runs and the read-only snapshot. The research runner's freeze
is `R/runs/prospective-shadow/implementation-freeze.json`, contract SHA-256
`969eb8eeb77d09f051ee52c415eb2d15e5ffa7d138e9b4149166e51eda3a355c`.
No new dependencies are needed. Use the preserved runtime, from the latest checkout's
`tennis_model` directory:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src \
uv run --offline --no-project \
  --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python \
  python -m tennis_model.eval.prospective_shadow --help
```

The incumbent is `R/runs/maintenance/wta-final-001/predictor.pkl` and its `.envelope`.
The candidate is `R/runs/prospective-shadow/migration-001/candidate.shadow`;
SHA-256 `43dd88b1461913f11b90b6d2aa6aa82f7bbfe3ba7ad597d978c6a46b73d45fcc`.
Use all five hashes in `R/runs/prospective-shadow/provenance.json` as caller-pinned
provenance. The final trees, calibrator, dynamic states and outputs on all 129,209
selected rows are identical to the accepted old artifact. Only the source version,
artifact ID and training metadata changed. Both versions enforce their own source
contracts; never hand-edit a header, patch a loader or disable a check.

## D0 — plan and preserve before new implementation

Append a new scoped plan to the live todo tail. A source adapter is independent of
model tuning and does not require a new candidate search. Build transport tooling
outside the frozen `src/tennis_model` package, with its own version/hash, while importing
the unchanged runner. If package code must change, create a separate checkout/version,
finish tests and freeze it, then perform another explicit exact migration. Adding any
Python or JSON file under that package changes the shadow source contract.

Retain an exclusive directory for the source audit, raw responses, request/response
receipts, parser version, tests and failures. Do not overwrite existing inputs or
pretend historical caches were observed today. No agents are authorized by this plan;
independent workstreams below describe dependencies, not delegation permission.

## D1 — establish a trustworthy acquisition contract

Review primary provider documentation and actual scheduled, live and settled objects.
Start with the existing ESPN and WTA acquisition paths, without assuming their date
fields meet this protocol. Local findings already established:

| Existing path | What it supplies | Gap for this experiment |
|---|---|---|
| `data/live.py::parse_upcoming` | Real participants, ESPN event ID, round, local date; includes pre and in-progress objects | Drops exact status/time distinction; no defensible start lower bound or complete context |
| `data/live.py::parse_events` | Completed winner/loser, event ID, round, date, score | No independently verified actual start/finish timestamps |
| Live acquisition `completedAt` | Local fetch completion | Is not match completion |
| `data/wta_results.py::timing` | Event bounds and sometimes a played date, respecting estimate flags | Does not certify actual start or finish |

For each candidate field, record the provider, URL, raw field path, timezone, meaning,
status-dependent changes, estimate flags, evidence and explicit limitations. Keep the
same actual match across pre/live/final samples. Test delayed starts, schedule revisions,
a timezone/date boundary, retirements/walkovers, participant replacements and changed
sponsor titles. Join by corroborated event identity; WTA event IDs need an independently
validated mapping to ESPN IDs. Never use sponsor string similarity.

A defensible `earliestStartAt` must not exceed actual start. Missing or estimated
scheduled time is not proof. Venue-day midnight with an established timezone is a
possible conservative lower bound only when the actual playing date is defensible and
capture precedes it by more than five minutes. Scheduled and settled timestamps must
retain their evidenced meanings; source coverage is not semantic validation.

The current runner requires actual start and finish evidence. If a source only gives
observation intervals or mutable estimates, do not rename those values `actualStartedAt`
or `finishedAt`. Document the gap. Any alternative interval-evidence protocol needs an
explicit new contract and tests before activation. Avoid paid feeds, credentials or
new dependencies unless they become necessary and are separately authorized.

Deliverable: a source readiness report with exact field mappings, raw example hashes,
coverage/exclusion counts and a pass/fail decision for every required field.

## D2 — implement and test the external adapter

The adapter produces bounded JSON batches accepted by the frozen runner. Use the
schedule/result structures in `tasks/research/PROSPECTIVE.md`, with `tour="wta"` and
`bestOf=3`; the new runner is stricter than the old one. It must emit:

- A locally recorded `observedAt` after the response was received, exact HTTPS
  `sourceUrl`, tour and at most 2,048 matches. Preserve raw response bytes/hash and
  request/receive times in an auditable acquisition receipt; extra batch metadata is
  retained by the runner.
- Per-match stable ESPN event ID, explicit season, canonical main-draw round and exact
  real player names mapped to both models. Preserve ambiguity instead of guessing.
- Schedule status, defensible earliest start, surface, best-of-three and factual
  `context`: event display/context name, `as_of` equal to earliest start, exact boolean
  indoor flag, positive finite tier factor and canonical round order. No blanket
  default context values merely to get an eligible pair.
- For normally completed results, winner and independently supported actual start and
  finish. Distinguish retirement, walkover, withdrawal and cancellation. Preserve
  unresolved rows as pending; exclude unsupported completion timing.

Tests should use retained raw source fixtures and assert every transformation and
exclusion. Include duplicate identities, aliases/replacements, timezone conversion,
wrong tour/doubles/qualifying, estimated time flags, unknown statuses, source failures,
empty responses and stale observation timestamps. No networking in unit tests.
Exercise adapter output through the real frozen mixed-format runner in a separately
labeled synthetic QA directory. Keep any synthetic chronology out of real audit data.

## D3 — observe source reliability before model-pilot activation

D1's semantic inspection and D2's implementation can inform each other; report design
and source transport tests can proceed independently. D3 requires the tested adapter.
Collect only factual source audit receipts until a verified pre/live/final lifecycle
has been seen with sufficient timing/context coverage. This is a source audit, not a
backfilled forecast experiment. Missing samples remain missing.

Choose and record an explicit acquisition cadence based on source limits and match
coverage; five-minute polling is only a candidate schedule, not an established limit
or active automation. Fresh transport receipt age must stay within ten minutes at
prediction completion. Record fetch failures, stale feeds, clock issues and effective
coverage; retries must not fabricate an earlier receipt. Validate on the actual host
that will run collection. No capture scheduler has been installed by this phase.

D3 output should say whether activation is supportable, which source hosts and adapter
version are fixed, what evidence proves timing, and how the chosen cadence is achieved.

## D4 — register an actual future pilot and collect

Requires D1–D3, unchanged valid fitted artifacts and an actual working execution cadence.
Register once using local current time in a new private directory. Do not reuse
`migration-001/synthetic-qa`: its two matches and future grading clocks are invented QA.
The fixed protocol is 30 days of capture, 200 minimum settled pairs, then seven days
of settlement intake. No early stop or extension based on score or count.

Create a verified source configuration JSON with exactly `scheduleHost`, `resultHost`,
`timingEvidence` and `cadence`; include the audit and adapter hashes in its descriptions.
The following are **command shapes only, not an instruction to activate before D1–D3**.
Run from the latest checkout's `tennis_model` directory, using the runtime prefix above:

```text
python -m tennis_model.eval.prospective_shadow --trusted-root R register R/runs/NEW-LIVE-PILOT \
  --incumbent R/runs/maintenance/wta-final-001/predictor.pkl \
  --candidate R/runs/prospective-shadow/migration-001/candidate.shadow \
  --provenance R/runs/prospective-shadow/provenance.json \
  --sources R/runs/SOURCE-AUDIT/verified-sources.json \
  --hypothesis 'The fixed selected WTA uncertainty candidate improves common-pair log loss.' \
  --evidence-kind live

python -m tennis_model.eval.prospective_shadow --trusted-root R capture R/runs/NEW-LIVE-PILOT R/runs/SOURCE-AUDIT/current-schedule.json
python -m tennis_model.eval.prospective_shadow --trusted-root R grade R/runs/NEW-LIVE-PILOT R/runs/SOURCE-AUDIT/current-results.json
python -m tennis_model.eval.prospective_shadow --trusted-root R report R/runs/NEW-LIVE-PILOT
```

Replace `R` and placeholders with verified absolute paths. Parent directories must
already exist; the pilot directory must not. Keep model payloads, source evidence and
receipts private and durable. Never place them in production output or the web mirror.
There is no public timestamp override. Frozen files cannot be updated during a pilot.
If daily updating models/states are desired, design that as a separately registered
policy; these artifacts deliberately retain their September 6 input cutoff.

## D5 — endpoint interpretation

At the registered settlement deadline, generate and preserve `endpoint.json`. Further
result intake is rejected, even if it would improve coverage. Report all captured,
pending, excluded, conflicted and scored pairs; inspect unsuccessful/underfilled pilots
too. Separate operational reliability from effect estimation. Do not silently correct
conflicted outcomes or change the protocol mid-pilot; retain and explain them.

Review common-pair log loss/Brier, accuracy tradeoff, naive and week/event uncertainty,
state staleness and source exclusions. The existing historical validation interval
crosses zero under week resampling. Two hundred matches cannot reliably resolve the
observed gain of about 0.00024 log loss: real fresh data and elapsed time remain needed.
A positive pilot mean or the minimum count does not authorize model adoption.

Production integration of the factual repairs remains a separate release effort:
current merge review, appropriate full pipeline and both integrity gates, regenerated
web mirror, deliberate push and post-deploy verification. Nothing in this handoff
asserts that those research changes are deployed.
