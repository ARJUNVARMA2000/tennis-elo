#!/usr/bin/env bash
#
# Turn the health.json written by the pre-build check into an actionable alert: a single
# `data-health` GitHub issue carrying the specific problems + a ready-to-paste fix prompt,
# dedup'd so a standing failure alerts once (not 24x/day), auto-closed on recovery, and
# redding the run so GitHub also emails the owner. Sibling of report-deploy-health.sh.
#
# Lives as a script rather than an inline `run:` block so it can be exercised directly by
# tests/test_workflow_alerts.py against a stubbed `gh` — the branch logic here decides
# whether the owner gets paged and whether the run goes red, and CLAUDE.md requires it be
# reachable by a test. It was the last inline alert block in refresh.yml.
#
# Inputs (env):
#   OK              health.json `ok`, as Python repr: True | False
#   CHANGED         health.json `problems_changed`: True | False (hourly comment throttle)
#   MODE            full | quick — the refresh mode
#   HEALTH_PAGE_URL live status page, quoted in the issue body
#   GITHUB_RUN_URL  link back to the failing run
#   HEALTH_BODY_CMD command that writes the issue body to stdout
#                   (default: the real generator; tests override it)
#   GH_RETRY_SLEEP  base backoff seconds for the issue-list retry (default 3; tests use 0)
#
# Dedup rules:
#   * pass + open issue  -> close it (recovery, any mode)
#   * fail + no issue    -> create + red (one email at onset, any mode)
#   * fail + open issue  -> full run: comment + red (the daily heartbeat);
#                           quick run: comment only if the problem set CHANGED, then stay
#                           GREEN (the open issue IS the alert). A red quick job never
#                           saves the data cache, so the prev health.json feeding
#                           problems_changed would stay stale and every hourly run would
#                           re-red — the storm this dedup exists to prevent.
set -e

HEALTH_BODY_CMD="${HEALTH_BODY_CMD:-python -m tennis_model.data.health --issue-body}"
GH_RETRY_SLEEP="${GH_RETRY_SLEEP:-3}"

# A 504 from the GitHub API is not a data problem, and must not be reported as one.
# `EXISTING=$(gh issue list ...)` used to run unguarded under `bash -e`, so one API blip
# redded a run in which everything real had PASSED — run 30106835566: integrity gate
# passed, 0 output problems on both tours, deploy succeeded, live verification OK, and
# then both report steps died on `504 Gateway Timeout` from `gh issue list`. Same false-
# alarm class as the skipped-verification bug in report-deploy-health.sh: the alerting
# reporting a failure it never observed. Retry, then report the list as UNKNOWN and let
# the caller decide — never conflate "cannot reach GitHub" with "the data is bad".
list_existing() {
  local out n=0
  while :; do
    if out=$(gh issue list --label data-health --state open \
               --json number --jq '.[0].number // empty' 2>/dev/null); then
      printf '%s' "$out"
      return 0
    fi
    n=$((n + 1))
    [ "$n" -ge 3 ] && return 1
    sleep $((n * GH_RETRY_SLEEP))
  done
}

gh label create data-health --color B60205 \
  --description "Pipeline data-health failures" 2>/dev/null || true

if EXISTING=$(list_existing); then
  LISTED=1
else
  EXISTING=""; LISTED=0
  echo "::warning::could not reach the GitHub issues API after 3 tries"
fi

if [ "${OK:-}" = "True" ]; then
  # Healthy. If the API is unreachable we simply cannot see an issue to close; the next
  # run closes it. Nothing here justifies redding a green pipeline.
  if [ -n "$EXISTING" ]; then
    gh issue comment "$EXISTING" \
      --body "✅ Recovered: the data-health check passed on $(date -u +%F). Closing." || true
    gh issue close "$EXISTING" || true
  fi
  echo "data health OK"
  exit 0
fi

# Failing for real from here on: the run SHOULD go red even if GitHub is unreachable,
# but without an issue list we cannot tell "no issue yet" from "issue already open", and
# guessing creates a duplicate thread every hour. Red the run, skip the write.
if [ "$LISTED" = "0" ]; then
  echo "::error::data-health check failed — issue not filed (GitHub API unreachable)"
  exit 1
fi

$HEALTH_BODY_CMD > /tmp/health-body.md

if [ -z "$EXISTING" ]; then
  gh issue create --label data-health \
    --title "Data-health check failed" --body-file /tmp/health-body.md
  echo "::error::data-health check failed — see the data-health issue"
  exit 1
fi
if [ "${MODE:-}" = "full" ] || [ "${CHANGED:-}" = "True" ]; then
  gh issue comment "$EXISTING" --body-file /tmp/health-body.md
  echo "commented on existing data-health issue #$EXISTING"
fi
if [ "${MODE:-}" = "full" ]; then
  echo "::error::data-health check failed — see the data-health issue"
  exit 1
fi
echo "::warning::data-health still failing — see the open data-health issue #$EXISTING"
exit 0
