#!/usr/bin/env bash
#
# Turn the post-deploy verification into an actionable alert: a single `deploy-health`
# GitHub issue, dedup'd so a standing failure alerts once (not 24x/day) and auto-closed
# on recovery. Mirrors "Report data health" in refresh.yml.
#
# Lives as a script rather than an inline `run:` block so it can be exercised directly by
# tests/test_workflow_alerts.py against a stubbed `gh` — the branch logic here decides
# whether the owner gets paged, and it is not reachable by any other test in the repo.
#
# Inputs (env):
#   OUTCOME         the `verifydeploy` step outcome: success | failure | skipped | cancelled
#   MODE            full | quick — the refresh mode, used to throttle the failure heartbeat
#   SITE_URL        public site URL, quoted in the issue body
#   GITHUB_RUN_URL  link back to the failing run
#   VERIFY_LOG      optional override of the verifier's log path (default /tmp/verify-deploy.log)
#
# Dedup rules:
#   * pass + open issue  -> close it (recovery, any mode)
#   * fail + no issue    -> create + red (one email at onset, any mode)
#   * fail + open issue  -> full run: comment + red (daily heartbeat);
#                           quick run: stay GREEN, no comment (the open issue IS the alert —
#                           a red quick job would skip the cache save and a silent comment
#                           every hour would spam the thread).
#   * never ran          -> no-op (see the guard below).
set -e

VERIFY_LOG="${VERIFY_LOG:-/tmp/verify-deploy.log}"

# The calling step is `if: always()`, so it also fires when the verification never RAN —
# an earlier step (refresh / gate / build / deploy) failed, or the run was cancelled, so
# the step outcome is `skipped`/`cancelled` rather than `failure`. That says nothing about
# what the live site is serving: the previous deploy is still up and healthy. Alerting here
# would file a "the deploy may be serving stale/broken content" issue — with an empty log
# block, since the verifier never ran to write one — for what is really an upstream pipeline
# failure, misdirecting the diagnosis away from the step that actually broke (repro: run
# 29812819613, where the `--strict` data download failed and this blamed the live site).
# Only a real `failure` implicates the site; anything else bows out, leaving any open issue
# standing (we cannot claim a recovery we never verified).
if [ "${OUTCOME:-}" != "success" ] && [ "${OUTCOME:-}" != "failure" ]; then
  echo "deploy verification did not run (outcome: ${OUTCOME:-none}) — no deploy-health signal"
  exit 0
fi

gh label create deploy-health --color B60205 \
  --description "Live Firebase deploy verification failures" 2>/dev/null || true
EXISTING=$(gh issue list --label deploy-health --state open --json number --jq '.[0].number // empty')

if [ "$OUTCOME" = "success" ]; then
  if [ -n "$EXISTING" ]; then
    gh issue comment "$EXISTING" \
      --body "✅ Recovered: live deploy verification passed on $(date -u +%F). Closing." || true
    gh issue close "$EXISTING" || true
  fi
  echo "deploy verification OK"
  exit 0
fi

{
  echo "The post-deploy verification of the live site **failed** — the deploy may be"
  echo "serving stale/broken content. Checks and details:"
  echo
  echo "Live site: ${SITE_URL:-unknown}"
  echo "Failing run: ${GITHUB_RUN_URL:-unknown}"
  echo
  echo '```'
  tail -c 6000 "$VERIFY_LOG" 2>/dev/null || echo "(no verify-deploy.log captured)"
  echo '```'
} > /tmp/deploy-health-body.md

if [ -z "$EXISTING" ]; then
  gh issue create --label deploy-health \
    --title "Live deploy verification failed" --body-file /tmp/deploy-health-body.md
  echo "::error::live deploy verification failed — see the deploy-health issue"
  exit 1
fi
if [ "${MODE:-}" = "full" ]; then
  gh issue comment "$EXISTING" --body-file /tmp/deploy-health-body.md
  echo "::error::live deploy verification still failing — see deploy-health issue #$EXISTING"
  exit 1
fi
echo "::warning::live deploy verification still failing — see open deploy-health issue #$EXISTING"
exit 0
