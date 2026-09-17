# Continue from the implemented official schedule collector

Read the [review](2026-09-07-official-schedule-review.md),
[result manifest](2026-09-07-official-schedule-result.json),
[source contract](2026-09-07-official-schedule-interface.md), accepted
`2026-09-07-time-evidence-interface.md` and live todo tail. The user authorized building
on official feeds. The collector is implemented; do not rebuild it or repeat source shopping.

## Exact state

`R = /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation`.
Current implementation checkout: `R/worktrees/official-schedule`, branch
`codex/model-official-schedule`, source/tests commit
`cda539332c98f5983bf6950da999e74d03d02d5e`, from accepted free-source tip `64e7022`.
Use this branch's final acceptance tip as the base for any next isolated implementation
checkout; preserve completed checkouts. Original DEUCE receives documents/logs only.

Source file: `tennis_model/research/usopen_schedule.py`.
Tests: `tennis_model/tests/test_usopen_schedule.py`.
Fixtures: `tennis_model/tests/fixtures/usopen_schedule/` (three gzip files and manifest).
Existing `prospective_sources.py`, `time_evidence.py`, `prospective_bounds.py`, all frozen
package files, models, web and workflows are unchanged. No new dependencies.

Run root: `R/runs/official-schedule`. Each of `retained-16`, `retained-17`, `live-001`
has catalogue/daily attempt, raw, receipt files and a collection report. Retained imports
are labelled retrospective; `live-001` is a real network observation. The three history
reports and `acceptance.json` preserve replay results. There are 27 new files; add the
manifest's `runFiles` to its `protected-run-files.json` for 553 protected old files next round.

The current actual sample has 132 historical schedule rows, six WTA identities and eight
versions after the new check. The new daily response is byte-identical to the earlier one.
Zero real revisions, starts or forecasts were established. Don't describe synthetic
replacement/cancellation tests as observed source behavior.

## Commands and behavior

Run from the implementation checkout's **tennis_model directory**, with `PYTHONPATH=src:research`.
Use the preserved runtime, always through uv. Replace the absolute collector archive
destination with a new, nonexistent directory under the trusted run root on every call.
The examples below name a possible next destination, not an already authorized cadence.

```bash
export UV_CACHE_DIR=/private/tmp/deuce-research-coordinator-uv
export PYTHONPATH=src:research
uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python research/usopen_schedule.py --trusted-root /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/official-schedule collect /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/runs/official-schedule/live-002 --year 2026 --day 17
```

Only use that day while its edition/date are still the intended target. A different day
must be explicit. The collector checks the catalogue and refuses unreleased/invalid paths.
Do not guess the main-draw day from the tournament-day number. Requests are bounded to
25 seconds/8 MiB, with no retries or redirects. Network access may require the existing
read-only public-network approval path; do not change endpoints to bypass a refusal.

`history` takes explicit collection directories followed by `--output NEW_FILE`, with
the same global `--trusted-root`. Always include earlier applicable archives; the report
claims coverage only for supplied inputs. It verifies and re-derives reports from raw
receipts. An incomplete/interrupted archive fails replay instead of proving no matches.
`import-retained ROOT --day 16|17` can reproduce only the pinned 2026 samples and retains
their real old acquisition times. It cannot manufacture a fresh observation.

Focused regression command:

```bash
uv run --offline --no-project --python /Users/varma/Projects/DEUCE/.research/2026-09-06-model-foundation/worktrees/coordinator/tennis_model/.venv/bin/python python -m pytest -q tests/test_usopen_schedule.py tests/test_prospective_sources.py tests/test_time_evidence.py tests/test_prospective_bounds.py
```

Accepted result: 146 tests passed in 5.19 seconds; 46 are new. Ruff uses the preserved
`R/worktrees/coordinator/.research/phase0/bin/ruff`. No full-suite rerun is required for
more observations with unchanged code. Re-run tests when implementation changes justify it.

## Next bounded phase and dependencies

1. **Define the timing question first.** Record the next plan and actual intended dates.
   Prioritize a genuinely future explicit not-before WTA match on an official order.
   Current retained day-16 explicit match 2408 was already past when acquired; day-17
   matches 2501/2502 use session-start labels. Neither satisfies the missing premise.
2. **Collect real lifecycle versions.** Use the existing collector for a new released
   order, then subsequent versions at meaningfully separated event stages. Preserve
   changed, missing, stale and failed versions. This depends on real elapsed time and
   publication, not more computation. More immediate copies of the unchanged day-17
   bytes provide no new lifecycle evidence. Do not fabricate transitions from fixtures.
3. **In parallel with waiting for source publication, research the precise rule/field
   contract.** Use primary official material to establish what explicit not-before
   means and its applicability to the selected match. Source publication, tournament
   compliance and independent physical-start confirmation are different premises.
   No subagents are authorized merely by this dependency statement.
4. **Only if a defensible timing premise is obtained, design a producer amendment.**
   Reuse the existing external bounds evaluator. A real source requires an evidence
   contract, pinned producer hashes, lifecycle/identity tests and new preregistration.
   The six US Open IDs alone do not justify an ESPN event/model join. Apply the existing
   evidence-based identity contract before donating context; never join event names.
5. **If only an assumption-based lower bound is available, keep that separate.** A
   prospective operational or exploratory comparison can be planned with explicit
   assumptions before outcomes. It must not count toward the primary independent-start
   gate or alter the accepted main result after observing it. There is no such study yet.

The manual collector exists, but no unattended job is active. If the user asks for a
scheduled monitor/cadence, use the app automation tools and a concrete prompt listing
the exact collector, run root, dates, frequency and stopping rule. Keep quiet while
unchanged and notify only meaningful changes/failure/action. A scheduled source monitor
would still not activate a model evaluation automatically.

## Frozen evidence and stopping rules

Incumbent: `R/runs/maintenance/wta-final-001/predictor.pkl`, SHA
`8cf280c43f813a6944244d585248af8d5fcbc1ff628e535f98d4e10866730e34`.
Candidate: `R/runs/prospective-shadow/migration-001/candidate.shadow`, SHA
`43dd88b1461913f11b90b6d2aa6aa82f7bbfe3ba7ad597d978c6a46b73d45fcc`.
Freeze/provenance stay in `R/runs/prospective-shadow`. Live registration remains refused;
the accepted producer admits only synthetic QA. Completion evidence supplies 119 old
upper bounds, not qualified starts. Preserve strict pre-play ordering:
`capture + 5 minutes < original schedule lower <= independently supported actual-start lower`.
Keep the fixed 30-day capture/day-37 settlement endpoint; 200 pairs is coverage, not power.

Preserve 91 frozen package files, both payloads, every prior run, ten completed prior
checkouts and this accepted checkout. Do not refit, migrate, copy raw training data,
add a generic evaluator, create an account/trial, contact a provider or deploy to solve
the observation gap. Reconcile Git before documentation, append logs/lessons, commit
the next research round and mirror only documents/logs to the original checkout.
