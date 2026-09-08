# Match-start source review — bounded public sample

The source investigation is complete; **no live start producer is qualified**. The
US Open publishes point start/end fields, but one of two sampled match histories is
internally inconsistent. WTA's point-history endpoint returns 404 for both matches;
its event endpoint returns no events. This is evidence about these records, not a
claim that all free tennis data is unusable. No model/evaluator code was changed.

The user confirmed they have no tennis data-provider access and asked whether it is
paid. Ongoing Sportradar access is commercial; its documented trial is free. No
account, trial, purchase or provider contact was initiated. The next free investigation
is a concrete published order-of-play lower bound, not another generic timing layer.

## Scope and reproduction

Research root `R` is
`/Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Checkout `R/worktrees/start-source`, branch `codex/model-start-source`, starts from
`129f811514cfd6b2a44edc087c42b26b45a475d4`. The accepted evaluator implementation
remains `10c07ee726632f7186522e423205d661169123ce`.

There were **18 explicit HTTP reads**, 2026-09-08 02:27:24–02:39:52 UTC (September 7
locally): 16 HTTP 200 and two 404. These counts exclude browser search/documentation
retrieval. Requests were bounded at 20 seconds and 8 MiB, without redirects, retries
or credentials. Exact raw bodies, including empty/error/wrong-media responses, are
retained in exclusive directories under `R/runs/start-source`. Each receipt records
request/receive times, URL, status, selected headers, byte count and SHA-256.

The [result JSON](2026-09-07-start-source-result.json) contains every receipt and the
offline census. Private drivers `R/tools/start-source-probe.py` and
`R/tools/start-source-analyze.py` are fingerprinted there. The analysis was run with
`uv run --offline --no-project` using the preserved coordinator Python runtime. It
reads retained bytes only and never emits timing claims or model forecasts. To repeat
the analysis, use a new output filename in a copied driver; `analysis.json` is exclusive
and must remain intact. Repeating it requires no further network reads.

## US Open: explicit fields, incomplete qualification

The public [match page](https://www.usopen.org/en_US/scores/stats/2117.html) links the
application bundle. Its
[configuration](https://www.usopen.org/en_US/json/gen/config_web.json) identifies
`scoringData.matchHistory.path` as
`/en_US/scores/feeds/2026/slamtracker/history/<matchId>C.json`.
We followed those observed paths, rather than guessing an undocumented API shape.

| Preserved observation | Pegula–Ruse | Sonmez–Gauff |
|---|---|---|
| US Open match ID | 2117 | 2148 |
| WTA match ID | LS74124878 | LS74124830 |
| WTA player IDs, source order | 316956 / 320408 | 326907 / 328560 |
| Round and result | R1, 6–3 6–2 | R1, 3–6 4–6 |
| Point rows | 125 | 118 |
| Start greater than end | 0 | **114** |
| Start-time regressions | 0 | 4 |
| First point's reported start UTC | Aug 30, 16:13:37 | Sep 1, 23:15:42 |

The raw point histories are
[2117](https://www.usopen.org/en_US/scores/feeds/2026/slamtracker/history/2117C.json)
and [2148](https://www.usopen.org/en_US/scores/feeds/2026/slamtracker/history/2148C.json).
Both start with two untimed arrival/warm-up rows (`EpochTimeStart/End = "0"`). Their
first real point has `PointID = "010101"`, `ServeNumber = "1"` and an end seven
seconds after its reported start. The first point's plausibility does not establish
the feed's clock accuracy or field semantics.

For 2148, the largest start-minus-end discrepancy is **86,398 seconds**. Start values
regress at points `010304`, `010706`, `010802`, `020102`; end values do not regress.
Across every point in each match, `EpochTimeStart - parsed(ElapsedTime)` equals the
first point's epoch exactly, even for the corrupted rows. Their agreement therefore
does not provide independent clock validation. The generating algorithm is unknown.
Do not repair these values by subtracting a day or deriving starts from playing duration.

The two
[completed-match](https://www.usopen.org/en_US/scores/feeds/2026/completed_matches/matches/2117.json)
[records](https://www.usopen.org/en_US/scores/feeds/2026/completed_matches/matches/2148.json)
agree with the retained WTA sample on player IDs, round and ordered set scores. That
WTA sample remains an earlier observation, not a fresh fetch. The completed-record
`epoch`, interpreted as milliseconds, is 13,027 and 13,193 seconds before the first
point respectively. Another completed-match feed uses a seconds-valued document epoch
and a different event code. None of these generic epochs was qualified as actual start.
These two identity witnesses also do not satisfy a general event-mapping qualification.

The configuration's separate `/api/tennis/matches/match/2117` path returned HTTP 200
with the exact HTML application shell, not JSON. It was recorded as wrong media and
not retried. HTTP success alone is not successful data acquisition.

No primary field dictionary or clock-error contract was established. Integer seconds
do not imply ±1-second physical accuracy. The mixed `ServeNumber` values require a
definition of first-serve versus second-serve/point-start behavior before general use.
No pre-play → live → completed lifecycle or revision behavior was witnessed here.

## WTA: real endpoint discovery, absent sample coverage

The [official scores page](https://www.wtatennis.com/tournaments/905/us-open/2026/scores)
loads `resources/v7.50.44/scripts/bundle-es.js`, which imports `match-centre.js`.
That module uses `store.js` and `tournament-player-service.js`; the latter constructs
`/tennis/tournaments/{group}/{year}/matches/{matchId}/{type}` on `api.wtatennis.com`.
The page supplies the public API base, and the service uses the public `account: wta`
header already used by the existing adapter.

For **both** WTA IDs in the table, `/point-by-point` returned HTTP 404 with zero bytes.
`/events` returned HTTP 200 with `Events: []`, empty players, and the 905/2026 tournament
metadata. The two event responses are byte-identical. This does not establish coverage
outside these US Open matches or outside Grand Slams.

The UI knows richer statuses, including players arrived, warm-up, restarted and time
announced. It also formats point timestamps into durations. These code paths do not
constitute an observed timestamped start event. Embedded debug fixtures in the bundle
are not live match records. No production adapter was broadened based on them.

## Licensed alternative and cost

Sportradar's [timeline reference](https://developer.sportradar.com/tennis/reference/sport-event-timeline)
describes timestamped timeline events. Its
[live retrieval guide](https://developer.sportradar.com/tennis/docs/tennis-ig-live-match-retrieval)
distinguishes `match_started`, `first_serve`, points and match end, and requires checking
per-match coverage and reconciling event revisions by ID. This is a more explicit
interface candidate; no authenticated payload, required coverage or clock-error
guarantee has been verified. Scheduled `start_time` is not a substitute.

The [account documentation](https://developer.sportradar.com/tennis/docs/ig-account-maintenance)
specifies a free 30-day trial with a default 1,000 requests per rolling 30 days and
1 QPS. Production access is for customers. No tennis subscription price was verified.
The existing pilot design collects for 30 days and settles through day 37, so a trial
started at registration would expire before its final intake. Access duration and a
request budget must be resolved before starting it; the trial is not automatically
sufficient. Buying access alone would not qualify the source or prove model improvement.

## Verification and decision

The offline census and preservation checks passed at 02:44:00 UTC:

- All **443 prior run files** match their saved hashes; all 18 new raw bodies match
  their receipts. Both frozen model payloads match their accepted hashes.
- All **91 frozen package files** match the implementation freeze. All **354 tracked
  program/web/workflow files**, including evaluator and tests, match the time-evidence
  checkout. Eight completed research checkouts remain clean at their recorded commits.
- No new training-input copy exists. The new checkout contains only 33 inherited,
  byte-identical tracked data artifacts. A first private preservation assertion wrongly
  treated any `data/` directory as a training copy; it was corrected to check actual
  membership. `local-setup-notes.json` preserves that failure; it was not a model failure.
- The full training/snapshot inventories were last verified at 01:58:44 UTC in the
  previous phase and were **not** rehashed in this documentation-only phase.

No tests or fitting were rerun because implementation and tests are unchanged. The
previous 231 focused tests and 1,411 earlier full-suite tests remain historical results,
not new checks. No forecast, performance estimate, live registration, collector, merge,
push or deployment was produced. The corrected 42-column incumbent remains current;
the fixed 43-column candidate remains deferred.

S0 is complete with an exact source gap. Conditional S1 is resolved without a producer;
its prerequisite failed. S2 records this review, preservation and the
[specific next-step plan](2026-09-07-start-source-next.md). Public order-of-play
qualification remains untested; do not describe the free-source search as exhaustive.
