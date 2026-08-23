#!/usr/bin/env bash
# Report failures that happen outside the data-health and deploy-health contracts.
#
# REPORT_CONTEXT=refresh consumes STAGE_OUTCOMES (one id=outcome per line) from the
# refresh job. REPORT_CONTEXT=workflow is the terminal-job backstop for test failures,
# timeouts, runner loss, and a missing in-job reporter. Incidents are keyed by run kind so
# an hourly quick success can never close a broken full retrain.
set -u

GH_RETRY_SLEEP="${GH_RETRY_SLEEP:-3}"
REPORT_CONTEXT="${REPORT_CONTEXT:-refresh}"
BODY_FILE="${RUNNER_TEMP:-/tmp}/pipeline-health-body.md"

write_result() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'handled=%s\n' "$1" >> "$GITHUB_OUTPUT"
    printf 'state=%s\n' "$2" >> "$GITHUB_OUTPUT"
  fi
}

run_key() {
  case "${MODE:-}:${PUSH_SCOPE:-}" in
    full:*) printf 'full' ;;
    quick:web) printf 'quick-web' ;;
    quick:*) printf 'quick-data' ;;
    *) printf 'workflow' ;;
  esac
}

list_existing() {
  local key="$1" out n=0 scope_label="pipeline-health-$1"
  while :; do
    if out=$(gh issue list --label pipeline-health --label "$scope_label" --state open \
               --limit 100 --json number --jq '.[0].number // empty' 2>/dev/null); then
      printf '%s' "$out"
      return 0
    fi
    n=$((n + 1))
    [ "$n" -ge 3 ] && return 1
    sleep $((n * GH_RETRY_SLEEP))
  done
}

make_body() {
  local key="$1" summary="$2"
  {
    printf '<!-- pipeline-health-key: %s -->\n' "$key"
    printf 'The **%s** pipeline path failed outside the data/deploy health reporters.\n\n' "$key"
    printf 'Run: %s\n\n' "${GITHUB_RUN_URL:-unknown}"
    printf '### Failed or missing stages\n%s\n' "$summary"
    if [ -n "${GATE_REPORT:-}" ] && [ -f "$GATE_REPORT" ]; then
      printf '\n### Pre-deploy gate report\n```json\n'
      if ! python3 - "$GATE_REPORT" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as source:
    report = json.load(source)
blocking = report.get("blocking") if isinstance(report.get("blocking"), list) else []
advisory = report.get("advisory") if isinstance(report.get("advisory"), list) else []
focused = {
    "schema": report.get("schema"),
    "ok": report.get("ok"),
    "blocking": blocking[:50],
    "blockingOmitted": max(0, len(blocking) - 50),
    "advisory": advisory[:10],
    "advisoryOmitted": max(0, len(advisory) - 10),
}
print(json.dumps(focused, indent=2))
PY
      then
        printf '(gate report unreadable; beginning follows)\n'
        head -c 4000 "$GATE_REPORT" 2>/dev/null || true
      fi
      printf '\n```\n'
    elif printf '%s' "$summary" | grep -q 'gate'; then
      printf '\n_Pre-deploy gate report was missing or unreadable._\n'
    fi
  } > "$BODY_FILE"
}

reconcile() {
  local key="$1" state="$2" summary="$3"
  local existing listed=1 scope_label="pipeline-health-$key"
  gh label create pipeline-health --color B60205 \
    --description "Refresh workflow pipeline failures" 2>/dev/null || true
  gh label create "$scope_label" --color D93F0B \
    --description "Pipeline health scope: $key" 2>/dev/null || true
  if ! existing=$(list_existing "$key"); then
    existing=""; listed=0
    echo "::warning::could not reach the GitHub issues API after 3 tries"
  fi

  if [ "$state" = "healthy" ]; then
    if [ "$listed" = "1" ] && [ -n "$existing" ]; then
      gh issue comment "$existing" \
        --body "✅ Recovered: the $key pipeline path completed successfully. Closing." || true
      gh issue close "$existing" || true
    fi
    echo "pipeline health OK ($key)"
    return 0
  fi

  if [ "$listed" = "0" ]; then
    echo "::error::$key pipeline failed — issue not filed (GitHub API unreachable)"
    return 2
  fi
  make_body "$key" "$summary"
  if [ -z "$existing" ]; then
    if ! gh issue create --label pipeline-health --label "$scope_label" \
        --title "Pipeline failure ($key)" --body-file "$BODY_FILE"; then
      echo "::error::$key pipeline failed and its issue could not be created"
      return 2
    fi
  elif [ "$key" = "full" ] || [ "$key" = "push-tests" ] || [ "$key" = "workflow" ]; then
    if ! gh issue comment "$existing" --body-file "$BODY_FILE"; then
      echo "::error::$key pipeline failed and its issue could not be updated"
      return 2
    fi
  else
    echo "pipeline failure still represented by open issue #$existing ($key)"
  fi
  echo "::error::$key pipeline path failed — see the pipeline-health issue"
  return 1
}

stage_outcome() {
  local wanted="$1" name outcome
  while IFS='=' read -r name outcome; do
    if [ "$name" = "$wanted" ]; then
      printf '%s' "$outcome"
      return 0
    fi
  done <<< "${STAGE_OUTCOMES:-}"
  return 0
}

refresh_report() {
  local key outcome name failures="" missing="" required owned=0 state=healthy
  key=$(run_key)

  # First name actual roots. Downstream skips after a known root are noise, not more causes.
  while IFS='=' read -r name outcome; do
    case "$name" in
      verifydeploy|reportdata|reportdeploy) continue ;;
      failpersist|faildownload|reportpipeline) continue ;;
    esac
    case "$outcome" in
      failure|cancelled) failures="${failures}- ${name}: ${outcome}\n" ;;
    esac
  done <<< "${STAGE_OUTCOMES:-}"

  if [ "$(stage_outcome reportdata)" = "failure" ]; then
    if [ "${DATA_REPRESENTED:-}" = "true" ]; then
      owned=1
    else
      failures="${failures}- reportdata: failed before representing data-health\n"
    fi
  fi
  if [ "$(stage_outcome verifydeploy)" = "failure" ] \
      || [ "$(stage_outcome reportdeploy)" = "failure" ]; then
    if [ "${DEPLOY_REPRESENTED:-}" = "true" ]; then
      owned=1
    else
      failures="${failures}- reportdeploy: deploy-health failure was not represented\n"
    fi
  fi

  required="checkout scope setup_python install_python restore_data bootstrap mode gate health setup_node restore_next build deploy verifydeploy reportdata reportdeploy savecache"
  case "$key" in
    full) required="$required download retrain persist snapshot" ;;
    quick-data) required="$required quick" ;;
    quick-web) required="$required mirror" ;;
    workflow) failures="${failures}- mode/scope: unavailable or invalid\n" ;;
  esac

  if [ -z "$failures" ]; then
    for name in $required; do
      outcome=$(stage_outcome "$name")
      case "$name:$outcome" in
        verifydeploy:success|verifydeploy:failure|reportdata:success|reportdata:failure|reportdeploy:success|reportdeploy:failure) ;;
        *:success) ;;
        *) missing="${missing}- ${name}: ${outcome:-missing}\n" ;;
      esac
    done
  fi
  failures="${failures}${missing}"

  if [ -z "$failures" ]; then
    [ "$owned" = "1" ] && state=owned
    if reconcile "$key" healthy ""; then
      write_result true "$state"
      return 0
    fi
    # Healthy + issue API UNKNOWN is not evidence of a pipeline failure.
    write_result true "$state"
    return 0
  fi

  reconcile "$key" failure "$(printf '%b' "$failures")"
  local rc=$?
  if [ "$rc" = "1" ]; then
    write_result true failure
  else
    write_result false failure
  fi
  return 1
}

workflow_report() {
  local key summary
  # The reusable tests job is intentionally skipped off-push. On a push, any non-success
  # blocks refresh and is the one root incident—do not also blame a skipped refresh.
  if [ "${EVENT_NAME:-}" = "push" ]; then
    if [ "${TESTS_RESULT:-}" != "success" ]; then
      reconcile push-tests failure "- reusable tests job: ${TESTS_RESULT:-missing}" || true
      return 1
    fi
    reconcile push-tests healthy "" || true
  fi

  if [ "${IN_JOB_HANDLED:-}" = "true" ]; then
    # Only an actually successful job whose in-job classification was healthy can prove a
    # generic pre-mode incident recovered. A handled pipeline failure, specialist-owned red
    # run, post-action failure, or cancellation must leave that incident standing.
    case "${IN_JOB_STATE:-}" in
      failure|owned) return 0 ;;
      healthy)
        if [ "${REFRESH_RESULT:-}" = "success" ]; then
          reconcile workflow healthy "" || true
          return 0
        fi
        key=$(run_key)
        reconcile "$key" failure \
          "- refresh post-actions/job result: ${REFRESH_RESULT:-missing} after a healthy tail reporter" || true
        return 1
        ;;
      *)
        key=$(run_key)
        reconcile "$key" failure "- in-job reporter returned an unknown state" || true
        return 1
        ;;
    esac
  fi
  key=$(run_key)
  case "${REFRESH_RESULT:-}" in
    success)
      summary="- in-job pipeline reporter: missing despite a successful refresh job"
      reconcile "$key" failure "$summary" || true
      return 1
      ;;
    failure|cancelled|skipped)
      summary="- refresh job: ${REFRESH_RESULT}\n- in-job pipeline reporter: did not reconcile the run"
      reconcile "$key" failure "$(printf '%b' "$summary")" || true
      return 1
      ;;
    *)
      summary="- refresh job result: ${REFRESH_RESULT:-missing}"
      reconcile "$key" failure "$summary" || true
      return 1
      ;;
  esac
}

case "$REPORT_CONTEXT" in
  refresh) refresh_report ;;
  workflow) workflow_report ;;
  *) echo "::error::unknown pipeline report context: $REPORT_CONTEXT"; write_result false failure; exit 1 ;;
esac
