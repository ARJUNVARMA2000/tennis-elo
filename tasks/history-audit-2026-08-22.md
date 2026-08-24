# Historical incidents and one-off-fix automation audit

Audited through strict production `origin/master` at `479b6c9` (2026-08-24): all 330 commits from
inception are accounted for. The original commit-by-commit audit stopped at `b1b8579`; the exact
nine-commit Aug 23 reconciliation and 13-commit Round 3/4 reconciliation appear below. The follow-up
commit containing this final reconciliation is documentation-only and necessarily excluded from
its own parent-history count.

### Current reconciliation (2026-08-24)

Rounds 1A-1C shipped in `339287b`, the ESPN round-identity follow-up shipped in `6692cfe`, and
Rounds 2A-2B shipped in `9f6bd41`. Together they close the original four highest-priority gaps:
terminal workflow/gate incident reporting, a non-ratcheting population baseline, same-run ESPN
acquisition receipts, and stable per-finding health identity with production-shaped replay tests.
Round 3 shipped through merge `1bcfe1b`. Round 4A then migrated the legacy cache through strict
predictor envelopes and an observed exact two-tour lineage graph; production FULL `32759935577`
created the parent release and QUICK `32761968258` proved exact cache carry. Round 4B shipped as
`7ba7b78` with documentation head `479b6c9`; production run `32762789376` removed the legacy mirror,
made lineage blocking, and passed mandatory accepted-graph verification with all private probes.

## Executive conclusion

The project has already done the most important thing right: most serious one-time repairs were
eventually converted into a reusable invariant, provenance field, deterministic identity rule,
pre-deploy gate, post-deploy verifier, or tested CI helper. At the original cutoff, the remaining
gap was less "we need more checks" than "some existing failures lose their identity or never reach
the issue system." Rounds 1 and 2 closed that gap; Rounds 3 and 4 standardized stage evidence,
participant state, browser execution, pre-unpickle predictor integrity, and exact accepted release
lineage. The remaining proposals are lower-priority liveness and transport/I/O guardrails, not a
known repeated production defect left behind as a one-off repair.

The original audit identified four findings for immediate action; all four are now shipped:

1. **Pipeline and gate failures had no immediate durable incident path.** GitHub returned 96
   failed runs in the audited period; 91 were `refresh.yml`. Twenty-seven failures were repeated
   executions of only three gate-blocked SHAs. A failed pipeline or pre-deploy gate skips the data
   health reporter; the deploy reporter correctly no-ops because verification never ran. The only
   durable fallback is the 26-hour watchdog, and successful QUICK runs can hide a FULL-only failure.
2. **Health findings had no stable identity.** `source_checks()` was structured, but
   `output_problems()` returned prose, `_gate_blocks()` inferred severity from substrings, and one
   mutable `data-health` issue was reused for every symptom. Issues #10, #14, and #15 each changed
   meaning while open.
3. **The population-drop baseline ratcheted after a bad run.** Issue #21 reported ATP matches
   `284445 -> 284393`; no restoration commit or data update occurred. The next run compared against
   284393 and auto-closed. The baseline must remain at the last accepted high-water value until
   recovery or an explicit population-version change.
4. **A total ESPN acquisition failure could stay green.** The August outage was visible in logs for
   roughly 13 refreshes, but `download_live()` caught the error and returned no tour result. The
   health system learned only later from stale tournament state. Acquisition needs a same-run
   success/failure receipt.

The original audit itself changed no production code. Its subsequent implementation and production
evidence are recorded in `tasks/todo.md` and summarized in this reconciliation.

## Scope and accounting

Every one of the original 308 production commits through `b1b8579` was inspected or placed in an
explicit non-substantive bucket; the nine later commits through `b6b1511` and 13 Round 3/4 commits
through `479b6c9` were then reconciled the same way. GitHub issues, PR-number gaps, issue comments,
workflow outcomes, representative failed-run logs, both production gates, their tests, live
manifests, and the topic lesson files were reconciled with the commit history.

| Range | Commits | Accounting |
|---|---:|---|
| `316a209..b220ed5` | 128 | 35 fixes/hardening, 33 feature/refactor/model, 46 routine/docs/research/data, 14 merges |
| late July 9 bridge | 4 | `4646488`, `04756c3`, `006c963`, `8f0e41e`; export/UI/explorer/IA features |
| July 10-31 | 110 | 78 substantive, 16 generated-data, 12 docs, 2 runtime bumps, 2 monitoring drills |
| August 1-22 | 66 | 27 fixes, 8 product/architecture features, 1 alias adoption, 21 generated-data, 9 docs |
| Post-cutoff, Aug 23 | 9 | 3 substantive/product/hardening; 6 routine/docs/generated/style |
| Round 3/4, Aug 24 | 13 | 7 substantive/product/hardening; 2 generated-data, 3 docs, 1 merge |
| **Total** | **330** | **196 substantive/product/hardening; 134 routine/docs/data/research/merge/drill/style** |

The post-cutoff ledger is exact:

- Substantive: `339287b` (Rounds 1A-1C and broader reliability hardening), `6692cfe` (ESPN
  bracket-evidenced round reconciliation), and `9f6bd41` (Rounds 2A-2B).
- Routine/docs/generated/style: `28661bb`, `11dbebc`, `f373fd7`, `b1db0d4`, `b744c99`, and
  `b6b1511`.

The Aug 24 ledger is also exact: `bbe3d0b`, `0f310f2`, `c3253e0`, `372f5f8`, `f0fb206`,
`eedc38c`, and `7ba7b78` are substantive; `af78c69` and `a388bb3` are generated evaluation data;
`2f5fef9`, `c56e50b`, and `479b6c9` are documentation; `1bcfe1b` is the Round 3 merge.

At the original cutoff, the commit-message test heuristic was already strong: 88 subjects began
with `fix`, and 77 of those touched a test path in the same commit. The 11 exceptions are mostly
dependency/lock repairs, data
healing, docs/visual corrections, or coverage arriving in an adjacent commit. A blanket "fix must
touch tests" rule would be noisy; executable incident/invariant coverage is a better standard.

GitHub numbering is also fully reconciled: #1 and #16 are pull requests, not missing incidents.
At the original cutoff there were 20 closed issues: 14 `data-health`, 5 `deploy-health`, and 1
`watchdog`. Three post-cutoff `pipeline-health` incidents (#23-#25) and the 18 Round 4 production
findings (#26-#43) bring the incident total to 41, all closed. Original median closure time was about
1.6 hours overall (5.1 hours for data health and 55 minutes for deploy health), but closure was not
always recovery—#21 is the counterexample that Round 1B standardized. Round 4's incidents closed
only after the responsible invariant passed in production.

## Reliability evolution

### Foundation and first hardening: June 28-July 9

The first phase built the model, web product, evaluator, quick refresh, and research arbiter. Its
important repairs established patterns that still matter:

- `61c696e` fixed six cross-layer failures together: swallowed market output errors, same-day
  rematch deletion, walk/inference feature parity, stale quick schemas, offseason/empty health, and
  bounded atomic WTA paging.
- `b80be18` standardized player identity keys and cross-language contracts; `283ebeb` repaired
  duplicate logs; `0daa043` removed TBD pseudo-athletes.
- `0568648` bounded quick Kalshi work; `b3da577` introduced output health; `e0e2b34`, `9f9d474`, and
  `c142c98` repaired surface, tier, and round semantics.
- Issue #2's Bad Homburg duplicate was detected about 20 seconds after deploy, repaired by
  `37aeb3d`/`98cb766`, and corrected live roughly 11 hours later. The original one-off display-name
  repair was later superseded by the ESPN-id registry and alias workflow; adding fuzzy-name tables
  would regress that design.
- `5291ebc` stopped non-finite JSON from blanking the browser; `70038fd` added the pre-deploy gate;
  `605ff12` immediately corrected a false gate on intentional nullable round fields.

The phase's recurring weakness was testing helper-shaped inputs while serialized predictors,
browser JSON, or combined production inputs exercised a different seam.

### Monitoring, identity, and lifecycle: July 10-31

This phase introduced the health/watchdog system and then repeatedly hardened its domain model:

- `995b4bc` added hourly freshness and the 26-hour workflow watchdog. `422bd00` moved dedup truth
  away from a success-only cache, `ea1e678` made checks dependency-aware, and `a0d5342` made source
  checks structured.
- The Wimbledon sequence (`2651a95`, `e7e189e`, `36bc49a`, `ab0bc18`) required four production
  repairs because legacy qualifying labels, completed-event state, and authoritative cached fields
  were not replayed together. Later draw gates then needed legitimate bye sizes (`d67cb62`),
  canonical accents (`aa7c8f6`), and placeholder-aware geometry (`693fbea`).
- `a3cf9ed` added live deployment verification. Issues #7/#8 exposed false attribution when an
  upstream failure skipped the verifier; `41a3341` distinguished skipped from failed, and
  `6945d07` moved reporter branching into a tested shell helper.
- `6ba2e95` standardized validated downloads, UNKNOWN alert transport, and real-player evidence;
  `00a30ee` added a future-date bound; `53faee1` separated model training age from build age;
  `9f9ad46` replaced unreliable cron-string inference with a tested mode selector.
- `c0a0182` added end-to-end external-I/O budgets after a four-hour quick run. `9544223` made model
  persistence survive later-stage failure and saved caches on red paths.
- The event-identity chain (`832e2df`, `8bec202`, `da8231c`, `8c9d05b`, `252439f`) moved from sponsor
  names to modal ESPN ids plus evidence. `d9c7435` aligned cache lifetime with consumer lifetime;
  `b8ec851` added calendar completion; `4e47f57` added independent exact-once event coverage so a
  vanished tournament could finally be detected.
- `1fa2fcb`, `3e75263`, and `5765ba7` converted manual alias discovery into deterministic proposal,
  model-assisted adjudication, record-based falsification, and a human-reviewed PR.
- `684999e` consolidated official draw provenance, shared ESPN acquisition, bounded Kalshi work,
  final-ledger sanitization, stage timing, cached-web gates, dependency caches, and immutable Actions.

The durable lesson was that validity must be checked on the final artifact, absence needs an
independent manifest, and cache validity must include identity, provenance, and lifecycle—not just
parseability or complete-looking geometry.

### Production semantics and active-event evidence: August 1-22

August exposed the same classes at more realistic product seams:

- `9c17a08`, `83e3b3e`, `6dff794`, and `51e16a8` repaired WTA population policy, event-only lifecycle
  evidence, year-wide dedup/finals/tiers, and one-day fragments.
- `d09cea0` distinguished total ESPN failure from a quiet week, but the caller still caught and
  printed the failure without producing a same-run health receipt; Round 1C later closed that seam.
- `cf4de59` and `29b3c0c` were explicit withdrawal stopgaps. `853deb9` replaced them with
  evidence-derived withdrawal handling—the right pattern for converting a one-off into a rule.
- `a8f7dd7`, `0b2cc03`, `d34ab0c`, `c752e97`, `6b1de8c`, and `1d593f3` progressively standardized
  provider slot vocabulary, adjacent-event rejection, and active draw-field revalidation.
- `28c1715`/`babcdf1` introduced date provenance after a tournament-start stamp looked like a stale
  live feed. `3bfc541` made the verifier retry and suppress dependent cascade diagnoses.
- `7ac8aa9` corrected a real Firebase mutable-cache defect with `no-cache, no-store`; this is distinct
  from the transport-only noise in issues #18 and #20.
- `638d02c` added independent Cincinnati live-integrity checks; `e92be62` versioned population
  changes; `49d43bd` replaced a calendar-age guess with direct MCP transport/schema receipts and
  atomic last-good behavior.

## Complete GitHub incident ledger

| Issue | Signal and outcome | Systemic status |
|---|---|---|
| #2 | Bad Homburg duplicated across feeds; `37aeb3d` selected the fuller record | Superseded by ESPN-id registry/evidence joins and alias workflow |
| #3 | Fresh-overlay warning stormed because red runs did not persist dedup state | Fixed by open-issue dedup (`422bd00`) and dependency-aware checks (`ea1e678`) |
| #4 | Intentional watchdog "never ran" drill | Canary passed; no product defect |
| #5 | Intentional 40-day charting threshold drill | Canary passed; threshold restored by `d864e56` |
| #6 | No WTA live/upcoming tournament | Naturally recovered; calendar-backed expected-event/progress checking remains incomplete |
| #7, #8 | Skipped verifier was reported as a live Firebase failure | Fixed by outcome typing and tested reporter (`41a3341`, `6945d07`) |
| #9 | DC/Memphis looked merged because 20 generic qualifiers counted as shared players | Fixed by real-participant evidence (`6ba2e95`) |
| #10 | Began as WTA match-count loss, then accumulated unrelated stuck-live/alive/placeholder findings | Underlying event defects fixed; thread proves need for per-finding identity |
| #11 | Mifel title/tier wrong | Fixed in `68e452a`; metadata validation retained |
| #12 | Generali remained upcoming and Kitzbuhel split | Fixed by lifecycle invariants and the ESPN-id/evidence/cache chain |
| #13 | Coverage shells restored events but lost recorded finals | Fixed by non-conflicting final retention (`42dc9be`) |
| #14 | Began as WTA count loss, then rotated through lifecycle, tier, and split-event findings | Fix chain `9c17a08` -> `83e3b3e` -> `6dff794` -> `51e16a8`; per-finding identity standardized in Round 2A |
| #15 | Future 2029 WTA row, then a Warsaw withdrawal | Fixed by `0b2cc03`/`29b3c0c`; standardized by `853deb9` |
| #17 | Hagen start-date provenance looked like stalled live play | Fixed by `28c1715`/`babcdf1`; progress-based liveness remains a gap |
| #18 | One aborted GET fabricated 13 downstream canonical failures | Transport/cascade noise; fixed by dependency-aware retry (`3bfc541`) |
| #19 | Bare mutable Firebase cache keys timed out while query variants returned | Real cache configuration defect; fixed by `7ac8aa9` |
| #20 | Same-SHA first attempt had unrelated aborted GETs; retry passed | Transport/rollout noise; no distinct product fix |
| #21 | ATP count fell 52 rows and issue auto-closed next run without restoration | Fixed by the version-keyed non-ratcheting high-water baseline in Round 1B (`339287b`) |
| #22 | 91-day charting content age was treated as transport failure | Fixed by direct transport/schema health and last-good input (`49d43bd`) |
| #23 | First Round 1 deploy failed reusable tests on Ruff import ordering | New terminal push-tests reporter opened the exact incident and closed it after `11dbebc` recovered |
| #24, #25 | Winston-Salem upcoming rounds disagreed with complete-bracket rounds and blocked two quick deploys | New gate reporter preserved the exact findings; bracket-evidence reconciliation `6692cfe` standardized the repair and both lifecycles closed |

At the original cutoff, the issue system detected user-visible output problems quickly but
confused an issue label with an incident identity. Round 2A replaced that mutable bucket with one
lifecycle per stable finding fingerprint, so recovery now means that exact symptom disappeared.

## Workflow-failure audit

GitHub returned 96 failed workflow runs for the audited history:

- 91 `refresh`, 2 test, 2 alias proposer, and 1 watchdog;
- 62 scheduled, 29 push-triggered, and 5 manual dispatches;
- 16 repeated failures on `51849cf`, 7 on `772e5d4`, and 4 on `aa7c8f6`—27 repeat runs across
  three SHAs.

Representative run `31631055085` had green tests and then blocked WTA Cincinnati because a 95-real
player field disagreed with a 96-slot bracket/draw-size contract. The gate did its safety job: the
wrong artifact never deployed. But it then skipped `Data health check` and `Report data health`;
`Report deploy health` correctly saw `skipped` and did nothing. No issue captured the exact gate
finding. The same blind path applies to pipeline/build failures, and a master-push test failure can
prevent the refresh job—and any in-job reporter—from starting at all.

At the audit cutoff, the daily watchdog could not be the primary answer. It asked only whether
*any* refresh succeeded in 26 hours, so hourly QUICK success could mask a broken FULL retrain. Its
issue branching also lived inline in `.github/workflows/watchdog.yml`, while the meta-test scanned
only `refresh.yml`. Round 1A added mode-specific terminal reporting, extracted the watchdog helper,
and expanded the tested no-inline-issue-mutation contract. Issues #23-#25 then exercised that path
against real push-test and gate failures and recovered exactly.

## Recurring failure classes and present coverage

| Failure class | Repeated evidence | What now exists | Residual gap |
|---|---|---|---|
| Event/player identity | #2, #9-15; sponsor renames, aliases, placeholders, lost ids | ESPN-id registry, evidence joins, alias proposer/falsifier, exact-once coverage, source-attachment uniqueness, shared participant-role vocabulary | No reproduced open defect after Round 3 |
| Event/draw lifecycle | Wimbledon retry chain, stale settled draws, withdrawals, lost finals, #43 | Calendar lifecycle, active revalidation, official provenance, pre-deploy geometry/live integrity, incident replays, unique scheduled-opponent replacement evidence | Start-stamped events still lack progress-based liveness |
| Source acquisition | LFS pointers, future dates, ESPN outage, MCP age | Payload validation, bounded retry, direct MCP and ESPN per-tour receipts, atomic last-good | No reproduced open defect after Round 1C |
| Cache/artifact validity | Old predictor schemas, alias/population changes, draw and Firebase caches | Pre-unpickle envelope/hash/runtime/config/state validation, pending markers, strict accepted two-tour manifest, exact cache carry, no-store serving | No reproduced open defect after Round 4 |
| Gate semantics | Bye sizes, accents, placeholders, shipped-vs-raw probability, tier severity | Typed findings/fingerprints, production replay corpus, pre-deploy gate, exact terminal reporter | No reproduced open defect after Round 2 |
| CI control flow | Cron attribution, `bash -e`, skipped verifier, red cache persistence, I/O budgets | Tested mode/push/report/watchdog scripts, terminal mode-specific issues, durable stage receipts, unconditional cache save, 75-minute cap | A workflow GitHub never starts still depends on platform-native visibility |
| Deploy/browser behavior | Header ordering, canonical cascade, mutable cache, global scroll | Deterministic real-browser CI, post-deploy verifier, mandatory exact graph/hash/MIME/index closure, bounded exact-404 probes | Transport-only second confirmation remains open |
| Model/evaluation integrity | Walk/inference parity, stale artifacts, population changes, market budget, #26-#42 | Full arbiter, parity/replay tests, schema/population/alias versions, bounded Kalshi, predictor-generation retry identity, strict envelopes and accepted lineage | No reproduced open defect after Round 4 |

## One-off fixes that were successfully standardized

These should be maintained, not reimplemented:

- **Bad Homburg/name dedup -> event identity system:** modal ESPN ids, evidence-based joins, cache keys,
  coverage manifests, and weekly alias proposals replaced fuzzy display-name repair.
- **Missing events -> independent presence contract:** `event_coverage.json`, exact-once producer checks,
  web partition preservation, and post-deploy membership parity detect absence independently.
- **Manual withdrawals -> evidence-derived active-field handling:** Warsaw/Cincinnati overrides became
  field comparison plus whole-artifact refresh; Winston-Salem added unique same-event scheduled-
  opponent continuity for pre-match replacements without weakening absence/ambiguity guards.
- **"Complete" cache shortcuts -> provenance-aware revalidation:** settled geometry alone no longer
  proves identity or active immutability.
- **Inline alert guesses -> typed/tested reporters:** data/deploy/pipeline/watchdog issue matrices
  now distinguish failure, skip, recovery, and API UNKNOWN; Round 1A brought the final watchdog
  branch under the same tested helper contract.
- **One-sided freshness -> source contracts:** future-date bounds and direct acquisition/schema
  receipts replaced calendar-age guesses where cadence is not guaranteed.
- **Invisible model staleness -> enforced artifact envelope:** trained-at, feature/schema, alias, and
  population versions still force controlled QUICK rebuilds, while Round 4 now rejects missing or
  mismatched bytes/runtime/config/model/state before pickle deserialization.
- **Unbounded best effort -> explicit I/O budgets:** Kalshi, Wikipedia, downloads, jobs, and verifier
  calls acquired bounded attempts/deadlines and last-good semantics.
- **Component validation -> accepted release gates:** output integrity and live serving now bind the
  semantic gate, exact two-tour manifest, every declared byte/hash/MIME/index edge, and every known
  private or omitted optional path Firebase must not serve.

## Ranked automation opportunities

| Priority | Proposal | Current status | False-positive / maintenance risk |
|---|---|---|---|
| P0 | Unified `pipeline-health` reporter: exact in-job stage outcomes plus terminal workflow job | **Live — Round 1A** | Low; skipped/unknown are typed and deploy-health remains separate |
| P0 | Non-ratcheting population high-water baseline keyed by population version | **Live — Round 1B** | Low; explicit version is the intentional reset |
| P0 | ESPN per-tour acquisition receipt surfaced through health | **Live — Round 1C** | Low; absence and transport failure remain distinct |
| P0 | Extract/test watchdog reporter and scan every workflow for inline issue mutation | **Live — Round 1A** | Very low; behavior-preserving refactor |
| P1 | Stable `HealthFinding {code,severity,tour,entity,evidence}` plus fingerprint lifecycle | **Live — Round 2A** | Compatibility prose remains during migration |
| P1 | Production-shape incident replay corpus with broken and clean controls | **Live — Round 2B** | Fixture upkeep is the ongoing cost |
| P1 | Durable stage-status ledger using the active timing seam | **Live — Round 3A** | Product/evaluation criticality is explicit |
| P1 | Canonical participant/draw-state classifier | **Live — Round 3B** | Source/context-specific policy is retained |
| P2 | Run the existing real browser scroll/interaction smoke in CI | **Live — Round 3C** | Narrow deterministic fixture bounds runtime and flakes |
| P1 | Pre-unpickle predictor envelope/checksum and exact two-tour public-data graph lineage | **Live — Round 4A migration + Round 4B enforcement** | Descriptor-bound roots and exact negative probes keep the contract fail-closed |
| P2 | Transport-only second verifier confirmation | Open; existing retry handles most cases | Low, but retries already solve most of the class |
| P2 | Static external-I/O contract audit | Open | Useful guardrail; lower urgency than known artifact gaps |

### Rules that are not worth adding

- Do not require every `fix:` commit to modify a test file; path-touch is not proof that the test
  bites, and legitimate data/dependency/docs exceptions make the rule gameable.
- Do not add fuzzy event-name joins or more hand-kept aliases to the hourly pipeline. Keep ids as
  hints, evidence-based joins, and the proposer/falsifier contract.
- Do not solve cadence problems by repeatedly changing age thresholds. Capture transport, schema,
  and last-success evidence.
- Do not make a new blocking check from a synthetic helper case alone. Replay a production-shaped
  broken and clean control, then run it advisory/shadow before promotion.

## Implementation slate

This is deliberately small enough to review and land without colliding with the current model,
latency, sharding, and US Open work.

### Round 1A — surface workflow and gate failures

- Add stable ids to pipeline/retrain/gate/build/deploy steps in `.github/workflows/refresh.yml`.
- Have `tennis_model.data.health --gate` optionally write an ephemeral structured gate report; never
  overwrite the deployed `health.json` on a blocked build.
- Add `.github/scripts/report-pipeline-health.sh` for exact stage outcomes, dedup, recovery, API
  UNKNOWN, QUICK/FULL semantics, and the gate report body.
- Add a terminal `report-workflow-health` job with `needs: [tests, refresh]` and `if: always()` so a
  push-test failure, skipped refresh, timeout, or runner/setup failure is still surfaced.
- Extract watchdog branching into `.github/scripts/report-watchdog.sh`; expand the meta-test to scan
  every workflow for inline `gh issue create/comment/close`.
- Pin the outcome matrix in `tennis_model/tests/test_workflow_alerts.py` with a stubbed `gh`.

### Round 1B — make recovery truthful

- Preserve `highWaterMatches` plus `MATCH_POPULATION_VERSION` per tour across reports.
- Advance high water only on an equal/higher accepted population; reset only when the explicit
  population version changes.
- Add a regression that runs the same 52-row drop twice and proves the second report still fails,
  plus recovery and version-reset controls in `tennis_model/tests/test_health.py`.

### Round 1C — page total ESPN acquisition failure

- Return per-tour acquisition outcome/provenance from `data/live.py::download_live()`.
- Propagate it through `data/download.py` and quick `pipeline.py` into an atomic source receipt.
- Add a stable health check that distinguishes successful empty responses, partial query failure,
  total transport failure, and a retained last-good overlay.
- Cover parser/acquisition, pipeline propagation, health, and reporter behavior in
  `test_live_parse.py`, `test_pipeline_guard.py`, `test_health.py`, and
  `test_workflow_alerts.py`.

Round 1 shipped in `339287b`. Round 2 introduced stable finding codes and the incident replay
manifest in `9f6bd41`. Round 3 shipped the participant-state, stage-ledger, and browser safeguards
through `1bcfe1b`. Round 4A migrated envelopes and accepted lineage through `c3253e0`; fixes
`372f5f8`, `f0fb206`, and `eedc38c` standardized the production findings it surfaced; strict
flag-free enforcement shipped in `7ba7b78` and was verified by run `32762789376`.

## Reconciliation with post-audit work

The US Open source-identity repair, WTA dual-state gate, and latency/sharding/cache work inspected in
the original dirty tree shipped together in `339287b`; none was counted as production before that
commit. Round 3 extended their existing timing and health seams rather than adding a parallel
instrumentation framework. Round 4 likewise extended the two existing gates: its production
failures became predictor-generation, forecast-history, and scheduled-replacement invariants rather
than exceptions, while preserving source-attachment and model-adoption contracts.

## Commit coverage ledger

This compact ledger proves that routine churn was separated rather than silently skipped.

### Inception through `b220ed5` — 128 commits

Substantive fixes/hardening (35):

`cb79cc9 08b9942 4c8a545 61c696e b80be18 f511e2d 8642b37 21bcdde 283ebeb 76bb728
0daa043 47befdf 2490d22 824d4aa 0568648 f2071d0 b3da577 e0e2b34 d90e811 b37af3a
8e479fe 9f9d474 ffcfe7b c142c98 6b30c43 37aeb3d 5291ebc eeedab8 eea770f f243e56
70038fd 605ff12 6c575d4 1c2274e b90218f`

Feature/refactor/model adoption (33):

`316a209 dc83360 635ef63 8d4d9b4 4bf142c 30c3451 f23049a 7bbceb2 e8942ed 21265bc
0341407 d45eeaa 9c809a8 f9edbdd a7c12c0 cfaec48 bc61d1c 5c4d012 5180300 fec0fb1
3f3f475 ddc82f0 c363bd4 89ca0d5 ce9c7bc 60b5a9f 209c8d2 2de1d4c f50db51 2500c10
78ceedf baf9e1d 855c8a9`

Routine/generated/docs/research (46):

`b50508b ff1f601 1347f94 0070636 99c19f8 915dbe6 37ba970 73bf82b 99fe5d9 33e4a1b
c39ebdb 03e6894 e78a4ba 49d539d 16a278f 5de001d bddc053 386e98b 7e0a6c7 d887c36
761cab8 6a03a78 17e4e52 bf5c03c b8ff8d4 9342e82 874cbb7 ae873e2 e7b43ca 267050a
53225b8 07bac5e 090bc35 c20caa3 c22d3ef 3bae460 bdcbbbe ff9c148 9cbf05b 3dcb34a
d989a76 d54466a e3b9ad2 742d323 ff18d4c 71cf0cb`

Merges (14):

`cf241f8 ece0c9d 27ad910 254a216 6a77517 98cb766 d3099f4 0c766de 706f828 d2cf5b6
a941c9a 631710c 24ca9b0 b220ed5`

Late-July-9 bridge (4): `4646488 04756c3 006c963 8f0e41e`.

### July 10-31 — 110 commits

The contiguous range `48863bc..e81a54f` contains 78 substantive changes described in the chronology
and incident map above. The 32 non-substantive commits are explicitly:

- Generated data (16): `48863bc ce7eacf 5ae9f37 902fc5a 8c2eb92 6fde196 d61e187
  52203fc 2f2c7c6 10a1158 8c28113 4a59571 8af2c39 2cbe3ec 1b7ddc9 4d7bfea`.
- Documentation follow-ups (12): `e50488b ed0cd54 735bc5d f509fec 39db592 9be3274
  f79a70b 030d01b d0a5964 d9793d4 e528af7 e81a54f`.
- Actions runtime bumps (2): `5a7b056 1e7ed22`.
- Intentional monitoring drills (2): `05da8e9 d864e56`.

### August 1-22 — 66 commits

- Aug 1: `bf5cdbc` data; `7ff211d` live/labels fix; `d58ea3e` product; `d34ab0c` draw parser.
- Aug 2-3: `54241e0`, `43662db` data; `edfc3d5`, `a766cf2` product; `9c17a08` WTA fix;
  `1e566c6` docs.
- Aug 4: `83e3b3e`, `c6d6f91`, `6dff794`, `51e16a8` fixes; `483d241` data;
  `df87734`, `ea63b9a` docs.
- Aug 5-6: `df3e2bc`, `031aedd` data; `d09cea0` ESPN fix; `f2562a4` docs.
- Aug 7: `cf4de59`, `a8f7dd7`, `0b2cc03`, `29b3c0c` fixes; `967a13a` alias adoption;
  `6e02aa4` data; `9007290` docs.
- Aug 8: `853deb9`, `839fc37`, `28c1715`, `babcdf1` fixes; `2659951` data.
- Aug 9-11: `d50a6c9`, `512bf79`, `8f542bb` data.
- Aug 12: `3bfc541`, `7ac8aa9` fixes; `bfa3ad9`, `51849cf` product; `bf00604` data.
- Aug 13-14: `c752e97`, `6b1de8c`, `387effa`, `1d593f3` draw fixes; `0accd3c` data.
- Aug 15-16: `1e345cd` web fix; `fdb2252`, `8f954da` data.
- Aug 17: `638d02c`, `e92be62` fixes; `8abe7d7`, `941d866` product; `6c2fe48` data;
  `b31486f`, `b461549` docs.
- Aug 18-19: `05ef44a`, `69c9278` data; `c08c3d8`, `49d43bd` fixes.
- Aug 20: `aba6387` data; `7bd5ebe`, `8519492` docs; `0a58938` product.
- Aug 21-22: `96a07c9`, `b1b8579` data only.

### August 24 Round 3/4 reconciliation — 13 commits

- Round 3: `bbe3d0b` implemented the safeguards, `1bcfe1b` merged them to production, and `2f5fef9`
  recorded the deployment.
- Round 4 migration: `0f310f2` added the shadow, `c56e50b` specified the enforcement gate, and
  `c3253e0` closed the reopened filesystem/durability findings.
- Production-discovered standardization: `372f5f8` distinguished same-hour generations,
  `f0fb206` preserved every same-hour transition, and `eedc38c` inferred uniquely scheduled draw
  replacements before first ball.
- Enforcement: `7ba7b78` removed compatibility fallback and made exact accepted releases mandatory;
  `479b6c9` recorded the observed FULL/QUICK migration.
- Routine generated evaluation updates: `af78c69` and `a388bb3`.

These 13 are included in the 330-commit production total above.

## Current rollout decision

Rounds 1-4 are complete and live through production head `479b6c9` (330 commits before this final
documentation reconciliation). Round 4A's parentless FULL `32759935577` and cache-restored child
QUICK `32761968258` established release `036b14e5-c320-4a14-83bf-375b4bfb1319`, preserved ATP/WTA
predictor UUIDs, and proved exact carry. Strict Round 4B run `32762789376` then restored that cache,
published child `4c207c28-240d-427f-95a3-f048f99af392`, passed the blocking gate and mandatory
453-artifact graph verifier with 16 exact private-path 404s, saved
`tennis-data-32762789376-1`, and left live health `ok=true` with zero open issue. Local and CI gates
passed 1,098 Python tests, 322 web tests, Ruff, TypeScript, Actionlint, the 24-route build, and real-
browser smoke. Only the explicitly lower-priority progress-liveness, second transport confirmation,
and static external-I/O audit proposals remain; no Round 4 compatibility fallback remains live.
