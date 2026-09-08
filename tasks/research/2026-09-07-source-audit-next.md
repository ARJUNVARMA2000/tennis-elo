# Resume here — repair the prospective time-evidence contract

The source acquisition/audit adapter is complete. Live-pilot readiness is not. Read
`2026-09-07-source-audit-review.md`, its result JSON, the source interface, current
`tasks/todo.md` tail, and then reconcile Git. Do not repeat model fitting, the selected
parameter sweep, migration, or the finished source census.

## Exact current state

Research root `R` is
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
The latest checkout is `R/worktrees/source-audit`, branch `codex/model-source-audit`.
Final implementation: `c9b5b17bc7cbb78816bc5fbf8c75ceb2ee83d561`.
External module: `tennis_model/research/prospective_sources.py`, SHA-256
`a0c73268af8c615f56cd2c14fd0e850c1a41d05a7bbce1a62cd18d9e790b33fb`.
It has 42 new tests; 187 focused tests passed in 7.45 seconds, with full lint passing.
The entire model package and all 78 preexisting tests are unchanged.

Use the preserved runtime from this checkout's `tennis_model` directory:

```bash
UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv PYTHONPATH=src:research \
uv run --offline --no-project \
  --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python \
  python research/prospective_sources.py --help
```

The artifact pair remains exactly the previous phase's:
`R/runs/maintenance/wta-final-001/predictor.pkl` with `.envelope`, and
`R/runs/prospective-shadow/migration-001/candidate.shadow`, SHA-256
`43dd88b1461913f11b90b6d2aa6aa82f7bbfe3ba7ad597d978c6a46b73d45fcc`.
Caller-pinned provenance is `R/runs/prospective-shadow/provenance.json`.
The package/inputs freeze remains
`969eb8eeb77d09f051ee52c415eb2d15e5ffa7d138e9b4149166e51eda3a355c`.
No ninth training-data copy, model fit or new candidate selection occurred.

## Why the old activation plan cannot simply proceed

The frozen prospective runner requires `actualStartedAt` and `finishedAt`. The current
public ESPN/WTA samples provide useful schedules, results and sometimes not-before
fields, but no validated actual start/finish mapping. WTA last-update/duration fields
are absent in the sampled main draw, and schedule-like timestamps disagree on 53 of
119 common completed matches. A field called `startDate`, a false estimate flag, a
fetch completion time or an observed score change is not sufficient proof.

The code therefore refuses live export. Removing that guard and copying a scheduled
or locally observed timestamp into an actual-time field would violate the contract.
The right next step is an explicit measurement-design change, prepared before any
real forecast outcomes are examined. Exact finish time may be unnecessary: a trustworthy
completed-result observation can provide a finish upper bound. Proof that both models
finished before actual play still needs a defensible start lower bound.

## R0 — specify sufficient evidence before changing code

Append a scoped plan and write a versioned time-evidence contract with examples and
counterexamples. Keep forecast capture time, announced not-before time, actual-start
proof, source update time, receive time and observed-completed time as distinct fields.
Do not use one generic `timestamp` or rename a bound as an exact time.

The essential inequality remains:

`paired forecast finished + 5 minutes < defensible actual-start lower bound`.

A start upper bound is not enough. First observed live play only proves that play has
started by then; it does not prove the forecast was pre-match. Similarly, subtracting
a reported playing duration from a first observed completed time does not recover
actual start because feed delay, interruptions and duration semantics are unresolved.

Candidate evidence classes to evaluate:

1. **A provider's explicit actual match-start event**, with documented semantics and
   timestamp precision. Round any uncertainty conservatively when deriving the lower
   bound. Primary Sportradar timeline docs describe `match_started` events with times,
   but no key/coverage has been validated here. No account or paid feed is authorized
   merely by this plan. A keyed source would require available access and coverage QA.
2. **An independently supported time interval or hard not-before bound.** Identify
   exactly what proves its lower edge. A scheduled estimate alone is not proof.
   An official not-before statement needs a validated date/timezone and a policy for
   earlier rescheduling; the source audit has not established those semantics yet.
3. **Timestamped pre-play observations with a justified delivery-lag bound.** This is
   only usable if the provider observation's effective time and maximum lag are known.
   HTTP Date/Age describes transport caching, not hidden upstream scoring delay.
   Empirical average lag is not a guaranteed upper bound. If such assumptions are used,
   register them explicitly, quantify sensitivity and avoid claiming deterministic proof.

For completion, investigate a typed `completedObservedAt` upper bound backed by a
preserved, timely, normally completed source response with an unambiguous winner.
Keep the seven-day intake deadline fixed. This can remove an unnecessary exact-finish
requirement without weakening pre-play proof. Define how conflicting outcomes,
retirements, corrections, source lag and timing contradictions invalidate a pair.

R0 deliverable: an explicit feasible evidence policy and field mapping, or a precise
list of missing facts. Do not implement a permissive schema merely because a provider
has not supplied the original fields.

## R1 — validate the evidence producer against real observations

Reuse the tested adapter to capture a small bounded factual source audit, in new
exclusive attempt folders. Its CLI is one-shot, not a scheduler. Example command shape:

```text
python research/prospective_sources.py --trusted-root R fetch espn R/runs/source-audit/NEW-ESPN-ATTEMPT
python research/prospective_sources.py --trusted-root R fetch wta R/runs/source-audit/NEW-WTA-ATTEMPT --event 905 --year 2026
python research/prospective_sources.py --trusted-root R audit R/runs/source-audit/NEW-ESPN-ATTEMPT R/runs/source-audit/NEW-WTA-ATTEMPT
```

Replace placeholders with verified absolute paths and the actually relevant event/year.
Read event identities from the provider first; do not infer them from sponsor names.
Existing source responses are retained under `R/runs/source-audit` and must not be
reused as new observations. Inspect `attempt.json`, `receipt.json`, `response.bin` and
exit status. A folder lacking a final receipt is incomplete; use a new name for retries.
No current cadence or watch is active. If later asked to schedule collection, use the
app's automation tool with a precise source-audit prompt and meaningful-change reporting;
do not invent an unattended shell loop or silently start a model pilot.

The completed sample has two ESPN and two WTA observations about 21 minutes apart.
Four provider records changed score, but no complete scheduled→live→terminal sequence
was witnessed. The same Gauff–Jovic match occurs in both feeds; their updates differ.
Collect missing lifecycle evidence only as time actually elapses. State transitions
must preserve event, season, round and participant identity. Include delayed starts,
earlier schedule changes, walkovers/retirements, missing observations and stale caches.
No disappearance is a result. The 344-identity lifecycle census includes other ESPN
events and placeholders; it is not a main-tour pilot sample count.

## R2 — implement a separate prospective protocol version

R2 depends on R0's evidence definitions. The completion-upper-bound implementation can
be developed while R1 validates start proof, but activation requires both.

Prefer an explicitly versioned external runner/evidence module if it can reuse the
unchanged strict model loaders and prediction methods without weakening their checks.
Bind its own code, adapter version, policy, source configuration and artifact hashes
in registration; external code is not covered by the shadow's package hash. Keep v1
registrations and receipts immutable. Never make a v1 reader silently interpret new
bound fields, mutate a v1 policy mid-pilot, or reuse a QA experiment as live.

If package code must change, use a fresh checkout, finish tests, freeze it and perform
an explicit fixed-model migration. Adding package Python/JSON changes the saved shadow
source contract. No parameter search is needed; preserve exact fitted outputs and state.

Preserve the first paired forecast, identical factual context, selected-state player
eligibility, five-minute margin, post-inference clock, ten-minute source age, fixed
30-day capture horizon, 200 minimum-pair coverage check and seven-day settlement grace.
Continue accumulated result reporting and conflict exclusions. The time evidence version
must be the only research-design change. No automatic adoption or outcome-driven stop.

Add integration/negative tests that prove:

- Exact versus interval evidence is typed and cannot be interchanged accidentally.
- Only a supported lower bound establishes pre-play capture; upper bounds and missing
  latency assumptions fail. Equality at the five-minute boundary remains ineligible.
- Schedule revisions, identities, offsets/date rollover, stale/future observations,
  conflicting bounds and post-start captures are rejected or explicitly excluded.
- Completion observations are preserved as upper bounds, never invented exact finish
  times; received-after-deadline evidence cannot enter the endpoint.
- Wrong-format/provenance/model bytes still fail before use; first forecast, partial
  result updates, terminal conflicts and endpoint receipts remain immutable.
- Real fitted artifacts process synthetic time-evidence fixtures end to end, and the
  accepted package/source/artifact contracts remain exact or migrate explicitly.

## R3 — qualify the source, then start a real future pilot

Requires the tested new evidence version, verified timing producer and a working,
registered acquisition cadence. Capture source failures and missing/ambiguous cases;
record coverage loss from requiring at least eight completed mapping witnesses. Early
events can remain unmapped. Do not loosen identity thresholds after seeing scores.

Use a new private live registration with actual local time, fixed models and written
hypothesis. Keep every prior `synthetic-qa` folder excluded. The full-size source QA
used a simulated registration clock and contains two diagnostic captures, zero graded
pairs and no independent model-performance result. It must never be upgraded or reused.

Evaluate at the fixed endpoint, not when the score becomes favorable. Report loss,
Brier, accuracy, paired uncertainty, block uncertainty, source exclusions and state
staleness. A 200-pair pilot remains primarily an operational test for a historical gain
of about 0.00024 log loss. More data and real elapsed time are required for independent
confirmation; more fitting cannot create it. Production integration stays separate.

## Preservation and session closeout

No agents are authorized by this handoff alone. Preserve all seven completed research
checkouts (coordinator through source-audit), original files, the read-only snapshot,
all protected run records and private drivers. Keep new audit data outside training
inputs and production output. Append completion/limitations to todo and the research
ledger; add lessons for actual new failure patterns. Reconcile Git before final docs,
commit the research work, and mirror only documents and append-only log additions to
the original checkout. Never imply that committed research code is deployed.
