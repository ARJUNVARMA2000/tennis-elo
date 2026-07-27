#!/usr/bin/env bash
# Decide whether this refresh run is a FULL retrain or a QUICK live refresh.
#
# This used to be an inline `run:` block that compared `github.event.schedule` against the
# literal "0 6 * * *". It silently stopped working: GitHub attributed the run occupying the
# daily 06:00 slot to the *hourly* cron string ("17 0-5,7-23 * * *") every day from at least
# 2026-07-21 to 07-25, so the FULL branch never once fired. The model was retrained only when
# a human dispatched it by hand, and nothing noticed, because the hourly quick refresh kept
# deploying a freshly-stamped site off an ageing pickle.
#
# The fix is to stop trusting which cron string GitHub says fired and read the clock instead:
# a scheduled run landing in the FULL_HOUR window is the daily retrain, however GitHub
# labelled it and however late it was delivered (the misfiring runs landed 06:30-06:43, all
# still hour 6). Deliberately NOT "retrain whenever the model is older than N hours": a
# persistently failing full run would then be retried every hour, and because a red full run
# blocks the deploy, the site would freeze instead of coasting on quick refreshes. Detecting
# a retrain that has stopped is the model-age watchdog's job (data/health.py), not this
# script's — mechanism here, detection there.
#
# Inputs (env):
#   EVENT_NAME     github.event_name
#   DISPATCH_MODE  github.event.inputs.mode ("auto" | "full" | "quick" | "")
#   NOW_HOUR       current UTC hour, zero-padded (injectable for tests)
#   FULL_HOUR      UTC hour of the daily retrain slot (default 06)
#   PREDICTOR      path to the saved predictor; absent -> nothing to refresh from -> full
# Output: prints "Selected mode: <mode>" and appends mode=<mode> to $GITHUB_OUTPUT if set.
set -euo pipefail

EVENT_NAME="${EVENT_NAME:-}"
DISPATCH_MODE="${DISPATCH_MODE:-auto}"
FULL_HOUR="${FULL_HOUR:-06}"
NOW_HOUR="${NOW_HOUR:-$(date -u +%H)}"
NOW_DATE="${NOW_DATE:-$(date -u +%F)}"
PREDICTOR="${PREDICTOR:-tennis_model/data/output/atp/predictor.pkl}"
# Written by the retrain step, carried between runs in the data cache.
MARKER="${MARKER:-tennis_model/data/output/.last_full_run}"

MODE=quick
WHY="default"

# The daily retrain: the FIRST scheduled run at or after FULL_HOUR on each UTC day.
#
# NOT "the run that lands exactly in hour FULL_HOUR" — that was the previous attempt and it
# missed on its first day. On 2026-07-26 GitHub delivered scheduled runs at 04:02, 07:05 and
# 08:03 and NOTHING in hour 06, so an equality test never matched and the model went 35h
# without a retrain. Scheduled delivery is not merely late, it drops slots entirely, so any
# rule keyed to a specific hour will keep missing.
#
# "At or after, once per day" is delivery-jitter-proof: whenever the first run after 06:00Z
# arrives, it retrains. The date marker is what stops that from becoming an hourly storm —
# a full run costs ~30 min and, on failure, takes the deploy with it, so at most one attempt
# per UTC day. The marker is written when the retrain STARTS (not when it succeeds), and the
# data cache now saves on red runs, so a crashing pipeline cannot retry all day either;
# a retrain that stays broken is the model-age watchdog's problem, not this script's.
LAST_FULL=""
[ -f "$MARKER" ] && LAST_FULL="$(tr -d '[:space:]' < "$MARKER")"
# 10# forces base 10 — "08" and "09" are invalid octal and would abort under set -e
if [ "$EVENT_NAME" = "schedule" ] \
   && [ "$((10#$NOW_HOUR))" -ge "$((10#$FULL_HOUR))" ] \
   && [ "$LAST_FULL" != "$NOW_DATE" ]; then
  MODE=full
  WHY="first scheduled run at/after ${FULL_HOUR}:00Z today (last full: ${LAST_FULL:-never})"
fi

# An explicit dispatch choice always wins over the slot.
if [ "$EVENT_NAME" = "workflow_dispatch" ] && [ "$DISPATCH_MODE" != "auto" ] && [ -n "$DISPATCH_MODE" ]; then
  MODE="$DISPATCH_MODE"
  WHY="workflow_dispatch input"
fi

# No saved model to refresh from yet (first run / evicted cache) -> must build one.
if [ "$MODE" = "quick" ] && [ ! -f "$PREDICTOR" ]; then
  MODE=full
  WHY="no saved predictor at $PREDICTOR"
fi

[ -n "${GITHUB_OUTPUT:-}" ] && echo "mode=$MODE" >> "$GITHUB_OUTPUT"
echo "Selected mode: $MODE (event=$EVENT_NAME hour=${NOW_HOUR}Z — $WHY)"
