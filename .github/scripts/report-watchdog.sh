#!/usr/bin/env bash
# Check refresh.yml liveness and reconcile the deduplicated watchdog issue.
set -u

GH_RETRY_SLEEP="${GH_RETRY_SLEEP:-3}"
WINDOW_H="${WINDOW_H:-26}"
BODY_FILE="${RUNNER_TEMP:-/tmp}/watchdog-body.md"

last_success() {
  local out n=0
  while :; do
    if out=$(gh api "repos/${GITHUB_REPOSITORY}/actions/workflows/refresh.yml/runs?status=success&per_page=1" \
               --jq '.workflow_runs[0].run_started_at // empty' 2>/dev/null); then
      printf '%s' "$out"
      return 0
    fi
    n=$((n + 1))
    [ "$n" -ge 3 ] && return 1
    sleep $((n * GH_RETRY_SLEEP))
  done
}

list_existing() {
  local out n=0
  while :; do
    if out=$(gh issue list -R "$GITHUB_REPOSITORY" --label watchdog --state open \
               --json number --jq '.[0].number // empty' 2>/dev/null); then
      printf '%s' "$out"
      return 0
    fi
    n=$((n + 1))
    [ "$n" -ge 3 ] && return 1
    sleep $((n * GH_RETRY_SLEEP))
  done
}

case "$WINDOW_H" in
  ''|*[!0-9]*)
    echo "::error::watchdog window is invalid (${WINDOW_H:-empty}); liveness is UNKNOWN"
    exit 1
    ;;
esac

if ! LAST=$(last_success); then
  echo "::error::could not query refresh workflow runs after 3 tries; liveness is UNKNOWN"
  exit 1
fi

NOW="${NOW_EPOCH:-$(date -u +%s)}"
case "$NOW" in
  ''|*[!0-9]*)
    echo "::error::watchdog clock is invalid; liveness is UNKNOWN"
    exit 1
    ;;
esac

if [ -n "$LAST" ]; then
  LAST_EPOCH=$(python3 -c \
    'from datetime import datetime; import sys; print(int(datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")).timestamp()))' \
    "$LAST" 2>/dev/null) || {
      echo "::error::latest refresh timestamp is malformed; liveness is UNKNOWN"
      exit 1
    }
  AGE_S=$((NOW - LAST_EPOCH))
  [ "$AGE_S" -lt 0 ] && {
    echo "::error::latest refresh timestamp is in the future; liveness is UNKNOWN"
    exit 1
  }
else
  AGE_S=3599996400
fi
AGE_H=$((AGE_S / 3600))
WINDOW_S=$((10#$WINDOW_H * 3600))
echo "last successful refresh run: ${LAST:-never} (${AGE_H}h ago, window ${WINDOW_H}h)"

gh label create watchdog --color B60205 -R "$GITHUB_REPOSITORY" \
  --description "refresh.yml liveness failures" 2>/dev/null || true
if EXISTING=$(list_existing); then
  LISTED=1
else
  EXISTING=""; LISTED=0
  echo "::warning::could not reach the GitHub issues API after 3 tries"
fi

if [ "$AGE_S" -le "$WINDOW_S" ]; then
  if [ "$LISTED" = "1" ] && [ -n "$EXISTING" ]; then
    gh issue comment "$EXISTING" -R "$GITHUB_REPOSITORY" \
      --body "✅ Recovered: refresh succeeded ${AGE_H}h ago. Closing." || true
    gh issue close "$EXISTING" -R "$GITHUB_REPOSITORY" || true
  fi
  exit 0
fi

if [ "$LISTED" = "0" ]; then
  echo "::error::refresh.yml is stale, but no issue was written because GitHub issues are UNKNOWN"
  exit 1
fi

{
  printf 'refresh.yml has had **no successful run in %sh** (max %sh). Last success: %s.\n\n' \
    "$AGE_H" "$WINDOW_H" "${LAST:-never}"
  printf 'Check the workflow page: https://github.com/%s/actions/workflows/refresh.yml — it may be disabled, failing before the health steps, or its cron dropped.\n\n' \
    "$GITHUB_REPOSITORY"
  printf 'Failing watchdog run: %s\n\n' "${GITHUB_RUN_URL:-unknown}"
  printf 'Live status page (last shipped report): %s\n' "${HEALTH_URL:-unknown}"
} > "$BODY_FILE"

if [ -n "$EXISTING" ]; then
  gh issue comment "$EXISTING" -R "$GITHUB_REPOSITORY" --body-file "$BODY_FILE"
else
  gh issue create -R "$GITHUB_REPOSITORY" --label watchdog \
    --title "Pipeline liveness: refresh.yml has not succeeded in ${AGE_H}h" \
    --body-file "$BODY_FILE"
fi
echo "::error::refresh.yml liveness check failed"
exit 1
