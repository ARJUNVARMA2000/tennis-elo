#!/usr/bin/env bash
# Trustworthy CI-run watcher. `gh run watch` exits 0 on CANCELLED runs (it watches,
# it doesn't judge) and its backgrounded form can drop out mid-run — both produced
# false "deploy succeeded" conclusions. This polls the API and exits 0 ONLY on
# conclusion == success.
#
# Usage: scripts/ci-watch.sh <run-id>       (get ids from: gh run list)
set -euo pipefail
run_id="${1:?usage: ci-watch.sh <run-id>}"

while :; do
  line=$(gh run view "$run_id" --json status,conclusion \
           --jq '.status + " " + (.conclusion // "-")')
  status=${line%% *}
  conclusion=${line##* }
  if [ "$status" = "completed" ]; then
    break
  fi
  sleep 20
done

echo "run $run_id finished: $conclusion"
[ "$conclusion" = "success" ]
