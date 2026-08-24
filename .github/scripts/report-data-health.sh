#!/usr/bin/env bash
#
# Reconcile actionable structured health findings with one durable GitHub issue per
# stable finding fingerprint. The health producer owns finding identity and renders
# issue bodies; this script owns the remote issue lifecycle and workflow exit policy.
#
# Inputs (env):
#   MODE                 full | quick
#   HEALTH_REPORT        health.json consumed by the health CLI (default supplied there)
#   FINDING_SNAPSHOT     authoritative | partial; partial reports never prove recovery
#   FINDINGS_CMD         emits one JSON array of health-finding-v1 objects
#   FINDING_BODY_CMD     emits the body for FINDING_KEY, including key/revision markers
#   GITHUB_RUN_URL       link to this run (used in recovery comments)
#   GH_RETRY_SLEEP       issue-list retry backoff base seconds (default 3; tests use 0)
#   PYTHON_BIN           strict JSON helper (default python3)
#
# Actionable severities are error and warning. Info findings remain visible in
# health.json but never own an incident. Identity is read only from the hidden
# `data-health-key` marker, never from mutable prose or titles.
set -euo pipefail

FINDINGS_CMD="${FINDINGS_CMD:-python -m tennis_model.data.health --findings-json}"
FINDING_BODY_CMD="${FINDING_BODY_CMD:-python -m tennis_model.data.health --finding-body}"
GH_RETRY_SLEEP="${GH_RETRY_SLEEP:-3}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
FINDING_SNAPSHOT="${FINDING_SNAPSHOT:-authoritative}"
export FINDING_SNAPSHOT

set_represented() {
  if [ -n "${GITHUB_OUTPUT:-}" ]; then
    printf 'represented=%s\n' "$1" >> "$GITHUB_OUTPUT"
  fi
}
# Fail closed for ownership. True means every actionable fingerprint is represented
# by an observed/reopened/created issue (or, during migration only, the legacy aggregate).
set_represented false

if [ "${MODE:-}" != "full" ] && [ "${MODE:-}" != "quick" ]; then
  echo "::error::data-health reporter requires MODE=full or MODE=quick"
  exit 1
fi
if [ "$FINDING_SNAPSHOT" != "authoritative" ] && [ "$FINDING_SNAPSHOT" != "partial" ]; then
  echo "::error::data-health reporter requires FINDING_SNAPSHOT=authoritative or partial"
  exit 1
fi

WORK_DIR=$(mktemp -d "${RUNNER_TEMP:-/tmp}/data-health.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT
FINDINGS_JSON="$WORK_DIR/findings.json"
ISSUES_JSON="$WORK_DIR/issues.json"
DESIRED_DIR="$WORK_DIR/desired"
PLAN_DIR="$WORK_DIR/plan"

# Validate the producer contract before touching GitHub. Besides protecting the
# reporter from malformed JSON, duplicate fingerprints are fatal: choosing one would
# make independent incident recovery nondeterministic.
if ! /bin/bash -c "$FINDINGS_CMD" > "$FINDINGS_JSON"; then
  echo "::error::could not read structured data-health findings"
  exit 1
fi
if ! "$PYTHON_BIN" - "$FINDINGS_JSON" "$DESIRED_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path

source, target = Path(sys.argv[1]), Path(sys.argv[2])
try:
    payload = json.loads(source.read_text(encoding="utf-8"))
except (OSError, ValueError) as exc:
    raise SystemExit(f"invalid findings JSON: {exc}")
if not isinstance(payload, list):
    raise SystemExit("findings JSON must be an array")

key_re = re.compile(r"^hf1:[0-9a-f]{64}$")
rev_re = re.compile(r"^hr1:[0-9a-f]{64}$")
seen = set()
active = []
for index, finding in enumerate(payload):
    if not isinstance(finding, dict) or finding.get("schema") != "health-finding-v1":
        raise SystemExit(f"finding {index} has an invalid schema")
    key, revision = finding.get("fingerprint"), finding.get("revision")
    if not isinstance(key, str) or not key_re.fullmatch(key):
        raise SystemExit(f"finding {index} has an invalid fingerprint")
    if key in seen:
        raise SystemExit(f"duplicate finding fingerprint: {key}")
    seen.add(key)
    if not isinstance(revision, str) or not rev_re.fullmatch(revision):
        raise SystemExit(f"finding {index} has an invalid revision")
    severity = finding.get("severity")
    if severity not in {"error", "warning", "info"}:
        raise SystemExit(f"finding {index} has an invalid severity")
    for field in ("code", "scope", "message"):
        if not isinstance(finding.get(field), str) or not finding[field]:
            raise SystemExit(f"finding {index} has an invalid {field}")
    tour, entity, evidence = finding.get("tour"), finding.get("entity"), finding.get("evidence")
    if tour is not None and not isinstance(tour, str):
        raise SystemExit(f"finding {index} has an invalid tour")
    if entity is not None and not isinstance(entity, str):
        raise SystemExit(f"finding {index} has an invalid entity")
    if not isinstance(evidence, dict):
        raise SystemExit(f"finding {index} has invalid evidence")
    if severity != "info":
        active.append(finding)

target.mkdir(parents=True)
for index, finding in enumerate(sorted(active, key=lambda item: item["fingerprint"])):
    item = target / f"{index:04d}"
    item.mkdir()
    key = finding["fingerprint"]
    label = (finding.get("tour") or finding["scope"]).upper()
    entity = finding.get("entity") or "global"
    title = f"[data-health] {label} · {finding['code']} · {entity}"
    if len(title) > 220:
        title = title[:217] + "..."
    (item / "key").write_text(key, encoding="utf-8")
    (item / "revision").write_text(finding["revision"], encoding="utf-8")
    (item / "title").write_text(title, encoding="utf-8")
(target / "count").write_text(str(len(active)), encoding="utf-8")
PY
then
  echo "::error::structured data-health findings are malformed or ambiguous"
  exit 1
fi

list_issues() {
  local n=0
  while :; do
    if gh issue list --label data-health --state all --limit 1000 \
         --json number,title,state,body > "$ISSUES_JSON" 2>/dev/null; then
      return 0
    fi
    n=$((n + 1))
    [ "$n" -ge 3 ] && return 1
    sleep $((n * GH_RETRY_SLEEP))
  done
}

gh label create data-health --color B60205 \
  --description "Pipeline data-health failures" 2>/dev/null || true

if ! list_issues; then
  echo "::warning::could not reach the GitHub issues API after 3 tries"
  if [ "$(cat "$DESIRED_DIR/count")" -gt 0 ]; then
    echo "::error::data-health check failed — issues not reconciled (GitHub API unreachable)"
    exit 1
  fi
  echo "data health OK; open incident recovery deferred until the issues API returns"
  exit 0
fi

# Turn the desired set plus the one remote snapshot into a deterministic plan. Querying
# all states lets a recurrent finding reopen its original thread instead of creating a
# fresh issue. The lowest issue number is canonical if a lost API response ever produced
# duplicates; later open duplicates are closed after the canonical issue is safe.
if ! "$PYTHON_BIN" - "$DESIRED_DIR" "$ISSUES_JSON" "$PLAN_DIR" "$FINDING_SNAPSHOT" <<'PY'
import json
import re
import sys
from pathlib import Path

desired_dir, issues_path, plan = map(Path, sys.argv[1:4])
snapshot = sys.argv[4]
if snapshot not in {"authoritative", "partial"}:
    raise SystemExit("invalid finding snapshot kind")
try:
    issues = json.loads(issues_path.read_text(encoding="utf-8"))
except (OSError, ValueError) as exc:
    raise SystemExit(f"invalid issue-list JSON: {exc}")
if not isinstance(issues, list):
    raise SystemExit("issue-list response must be an array")

key_re = re.compile(r"<!--\s*data-health-key:\s*(hf1:[0-9a-f]{64})\s*-->")
rev_re = re.compile(r"<!--\s*data-health-revision:\s*(hr1:[0-9a-f]{64})\s*-->")
by_key = {}
legacy = []
seen_numbers = set()
for raw in issues:
    if not isinstance(raw, dict) or not isinstance(raw.get("number"), int):
        raise SystemExit("issue-list response contains a malformed issue")
    if raw["number"] in seen_numbers:
        raise SystemExit(f"issue-list response repeats issue #{raw['number']}")
    seen_numbers.add(raw["number"])
    state = str(raw.get("state", "")).lower()
    if state not in {"open", "closed"}:
        raise SystemExit(f"issue #{raw['number']} has an invalid state")
    if not isinstance(raw.get("title"), str) or not isinstance(raw.get("body"), str):
        raise SystemExit(f"issue #{raw['number']} has an unreadable title/body")
    body = raw["body"]
    keys = set(key_re.findall(body))
    revisions = set(rev_re.findall(body))
    if (len(keys) > 1 or len(revisions) > 1
            or ("data-health-key:" in body and len(keys) != 1)
            or (revisions and not keys)):
        raise SystemExit(f"issue #{raw['number']} has ambiguous health markers")
    match = key_re.search(body)
    issue = {"number": raw["number"], "state": state, "body": body}
    if match:
        issue["revision"] = next(iter(revisions), "")
        by_key.setdefault(match.group(1), []).append(issue)
    elif raw.get("title") == "Data-health check failed" and state == "open":
        legacy.append(raw["number"])

desired = {}
for item in sorted(desired_dir.iterdir()):
    if not item.is_dir():
        continue
    key = (item / "key").read_text(encoding="utf-8")
    desired[key] = {
        "revision": (item / "revision").read_text(encoding="utf-8"),
        "title": (item / "title").read_text(encoding="utf-8"),
    }

for directory in ("active", "resolved", "duplicates", "legacy"):
    (plan / directory).mkdir(parents=True, exist_ok=True)

def write_item(group, index, values):
    item = plan / group / f"{index:04d}"
    item.mkdir()
    for name, value in values.items():
        (item / name).write_text(str(value), encoding="utf-8")

active_index = resolved_index = duplicate_index = 0
for key, finding in sorted(desired.items()):
    matches = sorted(by_key.get(key, []), key=lambda issue: issue["number"])
    open_matches = [issue for issue in matches if issue["state"] == "open"]
    # An already-open thread owns the incident even if a lower-numbered historical
    # duplicate is closed. Reopening the old thread would manufacture a recurrence and
    # falsely red an unchanged quick run.
    canonical = (open_matches[0] if open_matches else matches[0]) if matches else None
    action = "create" if canonical is None else ("reopen" if canonical["state"] == "closed" else "open")
    values = {"key": key, "revision": finding["revision"], "title": finding["title"],
              "action": action, "number": canonical["number"] if canonical else "",
              "stored_revision": canonical.get("revision", "") if canonical else ""}
    write_item("active", active_index, values)
    active_index += 1
    for duplicate in matches:
        if duplicate is not canonical and duplicate["state"] == "open":
            write_item("duplicates", duplicate_index,
                       {"key": key, "number": duplicate["number"]})
            duplicate_index += 1

if snapshot == "authoritative":
    for key, matches in sorted(by_key.items()):
        if key in desired:
            continue
        canonical = min(matches, key=lambda issue: issue["number"])
        if canonical["state"] == "open":
            write_item("resolved", resolved_index,
                       {"key": key, "number": canonical["number"]})
            resolved_index += 1
        for duplicate in sorted(matches, key=lambda issue: issue["number"]):
            if duplicate is not canonical and duplicate["state"] == "open":
                write_item("duplicates", duplicate_index,
                           {"key": key, "number": duplicate["number"]})
                duplicate_index += 1

if snapshot == "authoritative":
    for index, number in enumerate(sorted(legacy)):
        write_item("legacy", index, {"number": number})
(plan / "legacy_count").write_text(str(len(legacy)), encoding="utf-8")
PY
then
  echo "::warning::GitHub returned a malformed data-health issue inventory"
  if [ "$(cat "$DESIRED_DIR/count")" -gt 0 ]; then
    echo "::error::data-health check failed — issues not reconciled (inventory unknown)"
    exit 1
  fi
  echo "data health OK; open incident recovery deferred until issue inventory is readable"
  exit 0
fi

render_body() {
  local key=$1 revision=$2 destination=$3
  if ! FINDING_KEY="$key" /bin/bash -c "$FINDING_BODY_CMD" > "$destination"; then
    echo "::error::could not render issue body for $key"
    return 1
  fi
  if ! "$PYTHON_BIN" - "$destination" "$key" "$revision" <<'PY'
import re
import sys
from pathlib import Path

body = Path(sys.argv[1]).read_text(encoding="utf-8")
key, revision = map(re.escape, sys.argv[2:])
if len(body) > 60_000:
    raise SystemExit("body exceeds the data-health issue budget")
if not re.search(r"<!--\s*data-health-key:\s*" + key + r"\s*-->", body):
    raise SystemExit("body has no matching data-health key marker")
if not re.search(r"<!--\s*data-health-revision:\s*" + revision + r"\s*-->", body):
    raise SystemExit("body has no matching data-health revision marker")
PY
  then
    echo "::error::issue body markers disagree with finding $key"
    return 1
  fi
}

active_count=$(cat "$DESIRED_DIR/count")
legacy_count=$(cat "$PLAN_DIR/legacy_count")
all_keyed=1
onset=0
mutation_warnings=0

shopt -s nullglob
for item in "$PLAN_DIR"/active/*; do
  key=$(cat "$item/key")
  revision=$(cat "$item/revision")
  title=$(cat "$item/title")
  action=$(cat "$item/action")
  number=$(cat "$item/number")
  stored_revision=$(cat "$item/stored_revision")
  body="$WORK_DIR/body-${key#hf1:}.md"

  if [ "$action" != "open" ] && [ "$legacy_count" -eq 0 ]; then
    onset=1
  fi

  case "$action" in
    create)
      if ! render_body "$key" "$revision" "$body" \
         || ! gh issue create --label data-health --title "$title" --body-file "$body"; then
        all_keyed=0
        echo "::error::could not create the data-health issue for $key"
      fi
      ;;
    reopen)
      if ! gh issue reopen "$number"; then
        all_keyed=0
        echo "::error::could not reopen data-health issue #$number for $key"
        continue
      fi
      if render_body "$key" "$revision" "$body"; then
        if ! gh issue comment "$number" --body-file "$body"; then
          mutation_warnings=1
          echo "::warning::reopened #$number but could not add recurrence evidence"
        elif ! gh issue edit "$number" --body-file "$body"; then
          mutation_warnings=1
          echo "::warning::reopened #$number but could not refresh its body"
        fi
      else
        mutation_warnings=1
      fi
      ;;
    open)
      if [ "$stored_revision" != "$revision" ] || [ "${MODE:-}" = "full" ]; then
        if render_body "$key" "$revision" "$body"; then
          if ! gh issue comment "$number" --body-file "$body"; then
            mutation_warnings=1
            echo "::warning::could not comment on continuing data-health issue #$number"
          elif [ "$stored_revision" != "$revision" ] \
               && ! gh issue edit "$number" --body-file "$body"; then
            mutation_warnings=1
            echo "::warning::could not refresh data-health issue #$number"
          fi
        else
          mutation_warnings=1
        fi
      fi
      ;;
    *)
      all_keyed=0
      echo "::error::unknown data-health reconciliation action $action"
      ;;
  esac
done

# The legacy aggregate remains the temporary owner until every active key has its own
# thread. Do not resolve any old incident before that condition holds.
if [ "$all_keyed" -eq 1 ]; then
  if [ "$FINDING_SNAPSHOT" = "authoritative" ]; then
    for item in "$PLAN_DIR"/resolved/*; do
      key=$(cat "$item/key")
      number=$(cat "$item/number")
      recovery="✅ Recovered: finding \`$key\` is absent from the current actionable finding set on $(date -u +%F)."
      if [ -n "${GITHUB_RUN_URL:-}" ]; then
        recovery=$(printf '%s\n\nRecovery run: %s' "$recovery" "$GITHUB_RUN_URL")
      fi
      if ! gh issue comment "$number" --body "$recovery" || ! gh issue close "$number"; then
        mutation_warnings=1
        echo "::warning::could not fully close recovered data-health issue #$number"
      fi
    done
  fi

  for item in "$PLAN_DIR"/duplicates/*; do
    key=$(cat "$item/key")
    number=$(cat "$item/number")
    if ! gh issue comment "$number" \
         --body "Closing duplicate automation thread for stable finding \`$key\`." \
       || ! gh issue close "$number"; then
      mutation_warnings=1
      echo "::warning::could not fully close duplicate data-health issue #$number"
    fi
  done

  if [ "$FINDING_SNAPSHOT" = "authoritative" ]; then
    for item in "$PLAN_DIR"/legacy/*; do
      number=$(cat "$item/number")
      if [ "$active_count" -eq 0 ]; then
        message="✅ Recovered: no actionable data-health findings remain. Migrating away from the legacy aggregate incident."
      else
        message="Migrated to stable per-finding data-health incidents; every active finding now has its own durable thread."
      fi
      if ! gh issue comment "$number" --body "$message" || ! gh issue close "$number"; then
        mutation_warnings=1
        echo "::warning::could not fully retire legacy data-health issue #$number"
      fi
    done
  fi
fi

if [ "$all_keyed" -eq 1 ] || [ "$legacy_count" -gt 0 ]; then
  set_represented true
fi

if [ "$active_count" -eq 0 ]; then
  if [ "$mutation_warnings" -eq 1 ]; then
    echo "::warning::data health is OK; issue cleanup will be retried"
  else
    echo "data health OK"
  fi
  exit 0
fi

if [ "$all_keyed" -eq 0 ] && [ "$legacy_count" -eq 0 ]; then
  echo "::error::data-health findings are active and at least one has no issue representation"
  exit 1
fi
if [ "${MODE:-}" = "full" ]; then
  echo "::error::data-health findings are active — see the per-finding data-health issues"
  exit 1
fi
if [ "$onset" -eq 1 ]; then
  echo "::error::new or recurrent data-health finding — see the per-finding issue"
  exit 1
fi
echo "::warning::data-health findings remain active — see the per-finding issues"
exit 0
