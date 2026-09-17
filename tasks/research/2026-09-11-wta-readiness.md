# WTA release readiness follow-up — September 11, 2026

The WTA implementation remains locally validated and staged. **No model release was
pushed.** The ATP provider still cannot be reached, and its public GitHub archive is
too old to replace the retained statistics. The incumbent's latest scheduled refresh
and a separate live verification both passed. Evidence completed at 19:58:59 UTC.

## What this continuation established

| Check | Observed result | Consequence |
|---|---|---|
| Current ATP main, Challenger and file-list endpoints | All timed out before an HTTP response | Source readiness has not recovered |
| Explicit IPv4 and production User-Agent | Same connection failure | Neither change supplies a working transport |
| Public GitHub copy of 2026 main-tour data | 137 rows; latest tournament date January 17; last commit January 17 | Reject as a current fallback |
| Retained main-tour statistics file | 2,132 rows; latest tournament-start date August 30 | Do not overwrite with the older GitHub payload |
| Provider website source | File list points back to the same host; no current season CSV in its complete public repository tree | No verified alternate host found in the provider's published paths |
| Scheduled production refresh | Successful quick run; ATP current-file download still 0/2 | Serving success does not demonstrate source recovery |
| Independent live verification | 22/22 checks; 462 accepted artifacts | Incumbent release is serving correctly |
| Accepted integration evidence | All 1,675 file hashes match | Earlier model, build and cost evidence preserved |

The source probes resolve DNS but never establish a TCP connection. The payload parser
and User-Agent handling are therefore not the observed failure point. Both GitHub and
the live DEUCE site answered normally. The scheduled GitHub runner independently logged
the same two ATP file failures. These observations support a provider reachability
problem; they do not identify the provider's internal cause or prove global downtime.

The GitHub file passes the expected column shape and includes serve counts, so schema
validation alone would not make it a safe current replacement. Its date and row count
rule it out. Tournament-start dates in these CSVs are not match-completion timestamps:
the August 30 raw-file maximum and September 7 merged statistics date are different
fields with different meanings.

Primary upstream evidence: [provider migration notice](https://github.com/Tennismylife/TML-Database#readme),
[January 17 update](https://github.com/Tennismylife/TML-Database/commit/9d86c28d91d67c44828058e2ab85909e661671cd),
and [provider file-list implementation](https://github.com/Tennismylife/TML-Website/blob/main/app/api/data-files/route.ts).
The inspected route blob is `a6b5fc4bbcb76f34d4f821a7a4e0eb304ddfd03d`; its retained
copy and the untruncated repository-tree response are in the evidence directory.

## Correction to the previous release handoff

The earlier statement that a failed strict download would leave the previous site live
was incorrect. At both accepted `dda948c` and the integration source, the full download
step has `continue-on-error: true`. It retains previously validated files, permits the
retrain and integrity-gated deployment, then fails the workflow in a trailing source
failure step. Quick mode skips full strict acquisition. This behavior is deliberate.

The recommendation to wait for successful source acquisition is a **release decision
for this new model**, not an existing CI gate or a claim that current data fails the
production health policy. ATP statistics are four days old, within the existing
16-day limit, and reported season coverage is 98.12%. No workflow change, gate removal,
retry expansion, freshness relabeling or substitute feed was implemented in this round.
The successful scheduled quick run must not be called a successful full source refresh.

## Production receipt

- Source and freshly fetched `origin/master`: `dda948c8dfb0b2bb4d2ad0d205508d4e66cd7ef8`.
- [Run 34640536421](https://github.com/ARJUNVARMA2000/tennis-elo/actions/runs/34640536421):
  scheduled quick refresh, concluded success at 19:56:28 UTC; full strict step skipped.
- Health generated at `2026-09-11T19:54:50Z`, `ok: true`, no tour/output problems.
- Accepted release `48eda73e-6b73-486c-8d03-84a60ef21adf`; manifest SHA256
  `aa8aca40181ed1e96e58ae53f5cf1dbaf21c02ad1b3c75ab12b79cf841af34c4`.
- ATP predictor `50b99b70-f87e-4b13-ab89-93c2ab8f6bb0`, schema5/42 features.
- WTA predictor `7879edcb-b3e3-4861-b0f3-4b8da81922bd`, schema5/42 features.
- ATP merged results/statistics through September 9/7; WTA through September 10/10.
  These are the observed production values, not the later local integration snapshot.
- The independent verifier used the incumbent checkout and pinned captured health;
  separately retained meta files match the accepted manifest hashes.

## Exact next actions

1. Recheck the configured ATP main/Challenger CSVs and file-list endpoint with bounded
   requests in a **new** evidence directory. Parse and inspect current payloads when they
   return; an HTTP success alone is insufficient. No continuous polling was scheduled.
2. After connectivity recovers, create fresh staging from the then-current remote base,
   incorporate the completed integration, and preserve the latest production ledgers.
   Run normal `python -m tennis_model.data.download --kind all --strict` under the pinned
   Python3.12 environment. Record a successful completion rather than inferring it from
   a quick run. No full retry or new staging copy was needed while connectivity failed
   and the remote base was unchanged in this continuation.
3. Present the concrete source-ready WTA release for the remaining deployment decision.
   A choice to deploy earlier on retained data would be an explicit revision to the hold
   recommendation, not a repaired source or an automatically enforced CI restriction.
4. After authorization, publish through the normal production workflow and follow its
   actual full retrain, pre-upload gate, accepted publication and live verification.
   The WTA schema change should force a full run via saved-contract preflight. CI must
   fit its own Linux/Python3.12 artifacts; local evidence pickles are not deployment files.
5. Record the deployed commit, job, release and actual model IDs. Expect ATP42/schema5
   and WTA43/schema6. Reconcile the remote again immediately before any push.

Rollback source remains accepted `dda948c` with a compatible schema5 WTA model. Capture
the then-current accepted cache and ledgers before deployment. The public raw recovery
asset observed here is 48,831,635 bytes, updated September 8 at 00:15:48 UTC, SHA256
`355ecaa24e811dc525463d0d1d872dd4a28b7929f88f46a12527309bc7a11bab`.
This is an observed raw-data archive, **not** a newly tested predictor rollback snapshot.
Do not pair old code with a schema6 predictor or promise a source-only instant rollback.

## Handoff and preservation

The implementation checkout is `.research/2026-09-11-wta-surface-production`, with
functional source `d75b7ef` and accepted integration head `3c8d418` before this
documentation-only follow-up. No numerical module, runtime dependency, output or source
ledger was changed; the prior 1,344 Python/374 web test results still describe the same
functional code. Re-running those suites was unnecessary for these documentation changes.

New private evidence is `.research/2026-09-11-wta-release-readiness/`; the companion
`2026-09-11-wta-readiness-result.json` inventories it. `probe.py` and `complete.py`
are executed diagnostics, not unrun plans. All completed evidence directories remain
create-only; copy/adapt drivers into a new directory for a future check. The original
integration result and its 1,675 evidence files were verified without rewriting them.
