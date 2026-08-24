"""Behavioural checks for the CI alert shell in .github/scripts/ — no network, no real `gh`.

The alert scripts decide whether the owner gets paged and whether a run goes red. That
logic used to live inline in refresh.yml where nothing could reach it, and it shipped a
bug: a *skipped* verification (upstream step died, so the deploy never happened) was read
as "the live site is broken", filing an issue that blamed Firebase for a data-download
failure and buried the real error (run 29812819613). These tests pin the outcome matrix so
that class cannot come back.

Each case runs the real script under `bash` with a stubbed `gh` on PATH, then asserts the
exit code (does the run go red?) and the exact `gh` subcommands invoked (does the owner get
paged, and how?). Runnable directly (`python tests/test_workflow_alerts.py`) or under pytest.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from tennis_model.data import health as data_health

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / ".github" / "scripts" / "report-deploy-health.sh"
DATA_SCRIPT = REPO / ".github" / "scripts" / "report-data-health.sh"
PIPELINE_SCRIPT = REPO / ".github" / "scripts" / "report-pipeline-health.sh"
WATCHDOG_SCRIPT = REPO / ".github" / "scripts" / "report-watchdog.sh"
MODE_SCRIPT = REPO / ".github" / "scripts" / "decide-mode.sh"
SCOPE_SCRIPT = REPO / ".github" / "scripts" / "decide-push-scope.sh"
ALIAS_SCRIPT = REPO / ".github" / "scripts" / "open-alias-pr.sh"
WORKFLOW = REPO / ".github" / "workflows" / "refresh.yml"
ALIAS_WORKFLOW = REPO / ".github" / "workflows" / "propose-aliases.yml"
TEST_WORKFLOW = REPO / ".github" / "workflows" / "test.yml"
WATCHDOG_WORKFLOW = REPO / ".github" / "workflows" / "watchdog.yml"

# Windows dev boxes may lack bash; CI (ubuntu-latest) never does, which is where it counts.
_BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(_BASH is None, reason="bash unavailable (non-CI Windows shell)")

# `GH_FAIL_LIST=1` makes only `issue list` fail, standing in for the GitHub API 504 that
# redded run 30106835566 after a perfectly clean deploy.
_GH_STUB = """#!/usr/bin/env bash
echo "$1 $2" >> "$GH_CALLS"
if [ -n "${GH_CALLS_FULL:-}" ]; then
  printf '%q ' "$@" >> "$GH_CALLS_FULL"
  printf '\n' >> "$GH_CALLS_FULL"
fi
if [ "$1" = "api" ]; then
  if [ "${GH_FAIL_API:-}" = "1" ]; then
    echo 'non-200 OK status code: 504 Gateway Timeout' >&2
    exit 1
  fi
  echo "${FAKE_LAST_SUCCESS:-}"
  exit 0
fi
if [ "$1 $2" = "pr create" ] && [ "${GH_FAIL_PR:-}" = "1" ]; then
  echo 'pull request create failed: GraphQL: GitHub Actions is not permitted to create or approve pull requests (createPullRequest)' >&2
  exit 1
fi
if [ "$1 $2" = "issue create" ] && [ "${GH_FAIL_CREATE:-}" = "1" ]; then
  echo 'issue create failed: 503 Service Unavailable' >&2
  exit 1
fi
if [ "$1 $2" = "issue reopen" ] && [ "${GH_FAIL_REOPEN:-}" = "1" ]; then
  echo 'issue reopen failed: 503 Service Unavailable' >&2
  exit 1
fi
if [ "$1 $2" = "issue comment" ] && [ "${GH_FAIL_COMMENT:-}" = "1" ]; then
  echo 'issue comment failed: 503 Service Unavailable' >&2
  exit 1
fi
if [ "$1 $2" = "issue edit" ] && [ "${GH_FAIL_EDIT:-}" = "1" ]; then
  echo 'issue edit failed: 503 Service Unavailable' >&2
  exit 1
fi
if [ "$1 $2" = "issue close" ] && [ "${GH_FAIL_CLOSE:-}" = "1" ]; then
  echo 'issue close failed: 503 Service Unavailable' >&2
  exit 1
fi
if [ "$1 $2" = "issue list" ]; then
  if [ "${GH_FAIL_LIST:-}" = "1" ]; then
    echo 'non-200 OK status code: 504 Gateway Timeout' >&2
    exit 1
  fi
  case "$*" in
    *"--label data-health"*) echo "${FAKE_DATA_ISSUES_JSON:-[]}" ;;
    *pipeline-health-full*) echo "${FAKE_PIPELINE_FULL:-$FAKE_EXISTING}" ;;
    *pipeline-health-quick-data*) echo "${FAKE_PIPELINE_QUICK_DATA:-$FAKE_EXISTING}" ;;
    *pipeline-health-quick-web*) echo "${FAKE_PIPELINE_QUICK_WEB:-$FAKE_EXISTING}" ;;
    *pipeline-health-push-tests*) echo "${FAKE_PIPELINE_PUSH_TESTS:-$FAKE_EXISTING}" ;;
    *pipeline-health-workflow*) echo "${FAKE_PIPELINE_WORKFLOW:-$FAKE_EXISTING}" ;;
    *watchdog*) echo "${FAKE_WATCHDOG_EXISTING:-$FAKE_EXISTING}" ;;
    *) echo "$FAKE_EXISTING" ;;
  esac
fi
exit 0
"""


def _run_script(script: Path, extra_env: dict, existing: str = "", fail_list: bool = False,
                full_calls: list[str] | None = None):
    """Run an alert script with a stubbed `gh`. Returns (exit_code, [gh subcommands])."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "gh").write_text(_GH_STUB, encoding="utf-8", newline="\n")
        (tmp / "gh").chmod(0o755)
        calls = tmp / "calls.txt"
        calls.write_text("", encoding="utf-8")
        detailed = tmp / "calls-full.txt"
        detailed.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}",
            "GH_CALLS": str(calls),
            "GH_CALLS_FULL": str(detailed),
            "FAKE_EXISTING": existing,
            "GH_FAIL_LIST": "1" if fail_list else "",
            "GH_RETRY_SLEEP": "0",          # keep the retry path instant under test
            "GITHUB_RUN_URL": "https://example/run",
            **extra_env,
        }
        p = subprocess.run([_BASH, str(script)], env=env, capture_output=True,
                           text=True, timeout=60)
        if full_calls is not None:
            full_calls.extend(
                line for line in detailed.read_text(encoding="utf-8").splitlines() if line)
        return p.returncode, [ln for ln in calls.read_text(encoding="utf-8").splitlines() if ln]


def _run(outcome: str, existing: str = "", mode: str = "full", verify_log: str | None = None,
         fail_list: bool = False):
    return _run_script(SCRIPT, {
        "OUTCOME": outcome,
        "MODE": mode,
        "SITE_URL": "https://deuce-forecast.web.app",
        "VERIFY_LOG": verify_log or "/nonexistent/missing.log",
    }, existing=existing, fail_list=fail_list)


_KEY_A = "hf1:" + "a" * 64
_KEY_B = "hf1:" + "b" * 64
_REV_A = "hr1:" + "1" * 64
_REV_B = "hr1:" + "2" * 64
_REV_C = "hr1:" + "3" * 64


def _finding(key: str = _KEY_A, revision: str = _REV_A, *, severity: str = "error",
             code: str = "source.results.stale", tour: str | None = "atp",
             entity: str = "merged-results:atp", evidence: dict | None = None) -> dict:
    return {
        "schema": "health-finding-v1", "fingerprint": key, "revision": revision,
        "code": code, "severity": severity,
        "scope": "cross" if tour is None else code.split(".", 1)[0],
        "tour": tour, "entity": entity, "evidence": evidence or {"ageDays": 9},
        "message": f"{tour or 'cross'}: fixture finding {code}",
    }


def _data_issue(number: int, key: str = _KEY_A, revision: str = _REV_A,
                *, state: str = "OPEN", title: str | None = None) -> dict:
    return {
        "number": number, "state": state,
        "title": title or "[data-health] ATP structured finding",
        "body": (f"<!-- data-health-key: {key} -->\n"
                 f"<!-- data-health-revision: {revision} -->\nbody"),
    }


def _legacy_issue(number: int = 9, *, state: str = "OPEN") -> dict:
    return {"number": number, "state": state, "title": "Data-health check failed",
            "body": "legacy aggregate body"}


def _run_data(findings: list[dict] | object, *, issues: list[dict] | None = None,
              mode: str = "full", fail_list: bool = False, with_output: bool = False,
              extra_env: dict | None = None, full_calls: list[str] | None = None):
    """Run the structured reporter with real JSON/body contracts and a stubbed gh."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        findings_path = tmp / "findings.json"
        if isinstance(findings, str):
            findings_path.write_text(findings, encoding="utf-8")
        else:
            findings_path.write_text(json.dumps(findings), encoding="utf-8")
        body_helper = tmp / "body.py"
        body_helper.write_text(
            """import json, os, sys
items = json.load(open(sys.argv[1], encoding='utf-8'))
item = next(x for x in items if x['fingerprint'] == os.environ['FINDING_KEY'])
if os.environ.get('FAKE_BODY_MISMATCH') == '1':
    item = {**item, 'fingerprint': 'hf1:' + '0' * 64}
print(f\"<!-- data-health-key: {item['fingerprint']} -->\")
print(f\"<!-- data-health-revision: {item['revision']} -->\")
print(item['message'])
if os.environ.get('FAKE_BODY_OVERSIZE') == '1':
    print('x' * 60_001)
""", encoding="utf-8", newline="\n")
        env = {
            "MODE": mode,
            "HEALTH_PAGE_URL": "https://deuce-forecast.web.app/health/",
            "FINDINGS_CMD": f"cat {shlex.quote(str(findings_path))}",
            "FINDING_BODY_CMD": (f"{shlex.quote(sys.executable)} "
                                 f"{shlex.quote(str(body_helper))} "
                                 f"{shlex.quote(str(findings_path))}"),
            "FAKE_DATA_ISSUES_JSON": json.dumps(issues or []),
            "PYTHON_BIN": sys.executable,
            **(extra_env or {}),
        }
        if not with_output:
            return _run_script(
                DATA_SCRIPT, env, fail_list=fail_list, full_calls=full_calls)
        return _run_with_step_output(
            DATA_SCRIPT, env, fail_list=fail_list, full_calls=full_calls)


def _run_with_step_output(script: Path, env: dict, *, existing: str = "", fail_list: bool = False,
                          full_calls: list[str] | None = None):
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        output_path = f.name
    try:
        code, calls = _run_script(
            script, {**env, "GITHUB_OUTPUT": output_path}, existing=existing,
            fail_list=fail_list, full_calls=full_calls)
        output = Path(output_path).read_text(encoding="utf-8")
    finally:
        os.unlink(output_path)
    return code, calls, _outputs(output)


def _stage_outcomes(kind: str = "full", **overrides: str) -> str:
    names = ("checkout scope setup_python install_python restore_data bootstrap mode download "
             "retrain quick gate mirror persist health setup_node restore_next build deploy "
             "verifydeploy snapshot reportdata reportdeploy savecache failpersist faildownload")
    values = {name: "skipped" for name in names.split()}
    for name in ("checkout", "scope", "setup_python", "install_python", "restore_data",
                 "bootstrap", "mode", "gate", "mirror", "health", "setup_node", "restore_next",
                 "build", "deploy", "verifydeploy", "reportdata", "reportdeploy", "savecache"):
        values[name] = "success"
    if kind == "full":
        values.update(download="success", retrain="success", persist="success", snapshot="success")
    elif kind == "quick-data":
        values["quick"] = "success"
    elif kind == "quick-web":
        pass
    values.update(overrides)
    return "\n".join(f"{name}={values[name]}" for name in names.split())


def _outputs(value: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in value.splitlines() if "=" in line)


def _full_argv(calls: list[str]) -> list[list[str]]:
    """Undo the stub's Bash `%q` logging so assertions can inspect exact targets/flags."""
    return [shlex.split(call) for call in calls]


def _run_pipeline(*, context: str = "refresh", kind: str = "full",
                  outcomes: str | None = None, existing_by_key: dict[str, str] | None = None,
                  fail_list: bool = False, extra_env: dict | None = None):
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "gh").write_text(_GH_STUB, encoding="utf-8", newline="\n")
        (tmp / "gh").chmod(0o755)
        calls = tmp / "calls.txt"; calls.write_text("", encoding="utf-8")
        output = tmp / "output"; output.write_text("", encoding="utf-8")
        mode, scope = {
            "full": ("full", "data"),
            "quick-data": ("quick", "data"),
            "quick-web": ("quick", "web"),
            "workflow": ("", ""),
        }[kind]
        existing_by_key = existing_by_key or {}
        env = {
            **os.environ,
            "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}",
            "GH_CALLS": str(calls), "FAKE_EXISTING": "",
            "GH_FAIL_LIST": "1" if fail_list else "", "GH_RETRY_SLEEP": "0",
            "REPORT_CONTEXT": context, "MODE": mode, "PUSH_SCOPE": scope,
            "DATA_REPRESENTED": "true", "DEPLOY_REPRESENTED": "true",
            "STAGE_OUTCOMES": outcomes or _stage_outcomes(kind),
            "GITHUB_OUTPUT": str(output), "RUNNER_TEMP": str(tmp),
            "GITHUB_RUN_URL": "https://example/run",
            "FAKE_PIPELINE_FULL": existing_by_key.get("full", ""),
            "FAKE_PIPELINE_QUICK_DATA": existing_by_key.get("quick-data", ""),
            "FAKE_PIPELINE_QUICK_WEB": existing_by_key.get("quick-web", ""),
            "FAKE_PIPELINE_PUSH_TESTS": existing_by_key.get("push-tests", ""),
            "FAKE_PIPELINE_WORKFLOW": existing_by_key.get("workflow", ""),
            **(extra_env or {}),
        }
        p = subprocess.run([_BASH, str(PIPELINE_SCRIPT)], env=env, capture_output=True,
                           text=True, timeout=60)
        body = tmp / "pipeline-health-body.md"
        return (p.returncode,
                [ln for ln in calls.read_text(encoding="utf-8").splitlines() if ln],
                output.read_text(encoding="utf-8"),
                body.read_text(encoding="utf-8") if body.exists() else "",
                p.stdout + p.stderr)


def _run_watchdog(*, last: str = "2026-08-23T10:00:00Z", now: int = 1787482800,
                  existing: str = "", fail_api: bool = False, fail_list: bool = False,
                  window: str = "26"):
    return _run_script(WATCHDOG_SCRIPT, {
        "GITHUB_REPOSITORY": "owner/repo", "WINDOW_H": window,
        "NOW_EPOCH": str(now), "FAKE_LAST_SUCCESS": last,
        "FAKE_WATCHDOG_EXISTING": existing,
        "GH_FAIL_API": "1" if fail_api else "",
        "HEALTH_URL": "https://example/health/",
        "RUNNER_TEMP": tempfile.gettempdir(),
    }, existing=existing, fail_list=fail_list)


# --- the regression this file exists for -------------------------------------------------

def test_never_ran_outcomes_do_not_touch_the_alert():
    """`skipped`/`cancelled`/unset mean the verification never RAN — an upstream step died
    or the run was cancelled. The live site is not implicated, so the script must stay
    silent: no issue, no red, and crucially no `gh` call at all. Reading `!= success` as
    "broken" is exactly what filed the bogus issue in run 29812819613."""
    for outcome in ("skipped", "cancelled", ""):
        for existing in ("", "8"):
            code, calls = _run(outcome, existing=existing)
            assert code == 0, f"{outcome!r} (issue={existing!r}) redded the run"
            assert calls == [], f"{outcome!r} (issue={existing!r}) paged the owner: {calls}"


def test_never_ran_leaves_an_open_issue_standing():
    """A recovery we never verified must not be claimed: no close, no comment."""
    code, calls = _run("skipped", existing="8")
    assert code == 0
    assert not any("close" in c or "comment" in c for c in calls)


# --- the paths that must keep working ----------------------------------------------------

def test_success_with_no_issue_is_quiet():
    code, calls = _run("success")
    assert code == 0
    assert calls == ["label create", "issue list"]      # looked, found nothing, done


def test_success_closes_an_open_issue():
    """Recovery auto-closes, so a fixed site does not leave a stale alert open."""
    code, calls = _run("success", existing="8")
    assert code == 0
    assert calls == ["label create", "issue list", "issue comment", "issue close"]


def test_failure_opens_an_issue_and_reds_the_run():
    """Onset: one issue, one email, run goes red."""
    code, calls = _run("failure")
    assert code == 1
    assert calls == ["label create", "issue list", "issue create"]


def test_failure_with_open_issue_comments_and_reds_on_full():
    """The daily heartbeat on a standing failure."""
    code, calls = _run("failure", existing="8", mode="full")
    assert code == 1
    assert calls == ["label create", "issue list", "issue comment"]


def test_failure_with_open_issue_stays_green_and_silent_on_quick():
    """Hourly quick runs must not spam the thread or red the job — a red quick run skips
    the data-cache save, which is the storm this dedup exists to prevent."""
    code, calls = _run("failure", existing="8", mode="quick")
    assert code == 0
    assert calls == ["label create", "issue list"]      # no comment
    assert "issue create" not in calls                  # and never a duplicate issue


def test_failure_body_includes_the_verifier_log_when_present():
    """The issue must carry the verifier's own output — the empty ``` block in issue #8 is
    what made the real cause unfindable."""
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False,
                                     encoding="utf-8", newline="\n") as f:
        f.write("routes 200: FAIL (503 on /method/)\n")
        log = f.name
    try:
        code, _ = _run("failure", verify_log=log)
        assert code == 1
        body = Path("/tmp/deploy-health-body.md")
        if body.exists():                                # written by the script under bash
            assert "503 on /method/" in body.read_text(encoding="utf-8")
    finally:
        os.unlink(log)


# --- a GitHub API outage must not be reported as a broken site / bad data -----------------

def test_api_outage_on_a_passing_deploy_stays_green():
    """The regression from run 30106835566: gate passed, 0 output problems, deploy verified
    OK — then `gh issue list` 504'd and, unguarded under `bash -e`, redded the whole run.
    A transport failure is not a signal about the site."""
    code, calls = _run("success", fail_list=True)
    assert code == 0, "an API 504 redded a run whose deploy verified OK"
    assert calls == ["label create", "issue list", "issue list", "issue list"]   # retried


def test_api_outage_on_a_failing_deploy_still_reds_but_files_nothing():
    """The failure is real, so the run must go red — but with no issue list we cannot tell
    "none yet" from "already open", and guessing opens a duplicate thread every hour."""
    code, calls = _run("failure", fail_list=True)
    assert code == 1
    assert "issue create" not in calls and "issue comment" not in calls


def test_data_api_outage_on_healthy_data_stays_green():
    code, calls = _run_data([], fail_list=True)
    assert code == 0, "an API 504 redded a run whose data health was fine"
    assert "issue create" not in calls and "issue close" not in calls


def test_data_api_outage_on_failing_data_still_reds_but_files_nothing():
    code, calls = _run_data([_finding()], fail_list=True)
    assert code == 1
    assert "issue create" not in calls and "issue comment" not in calls


def test_data_malformed_issue_inventory_is_unknown_not_a_healthy_false_red():
    code, calls = _run_data([], extra_env={"FAKE_DATA_ISSUES_JSON": "not json"})
    assert code == 0
    assert calls == ["label create", "issue list"]


def test_data_malformed_issue_inventory_still_reds_active_findings_without_mutation():
    code, calls = _run_data(
        [_finding()], extra_env={"FAKE_DATA_ISSUES_JSON": "not json"})
    assert code == 1
    assert calls == ["label create", "issue list"]


@pytest.mark.parametrize(
    "issues",
    [
        [{"number": 7, "state": "OPEN", "title": "x", "body": None}],
        [_data_issue(7), _data_issue(7)],
        [{
            "number": 7,
            "state": "OPEN",
            "title": "ambiguous",
            "body": (
                f"<!-- data-health-key: {_KEY_A} -->\n"
                f"<!-- data-health-key: {_KEY_B} -->\n"
                f"<!-- data-health-revision: {_REV_A} -->"
            ),
        }],
        [{
            "number": 7,
            "state": "OPEN",
            "title": "malformed marker",
            "body": f"<!-- data-health-key: not-a-key -->\n"
                    f"<!-- data-health-revision: {_REV_A} -->",
        }],
    ],
)
def test_data_ambiguous_issue_inventory_never_creates_a_duplicate(issues):
    code, calls = _run_data([_finding()], issues=issues)
    assert code == 1
    assert calls == ["label create", "issue list"]


def test_specialist_reporters_publish_actual_issue_representation():
    code, _, output = _run_data([_finding()], with_output=True)
    assert code == 1 and output == {"represented": "true"}
    code, _, output = _run_data([_finding()], with_output=True, fail_list=True)
    assert code == 1 and output == {"represented": "false"}

    deploy_env = {"OUTCOME": "failure", "MODE": "full", "SITE_URL": "https://example"}
    code, _, output = _run_with_step_output(SCRIPT, deploy_env)
    assert code == 1 and output == {"represented": "true"}
    code, _, output = _run_with_step_output(SCRIPT, deploy_env, fail_list=True)
    assert code == 1 and output == {"represented": "false"}


# --- per-finding data-health desired-state reconciliation ---------------------------------

def test_data_reporter_crosses_the_real_health_cli_contract(tmp_path):
    typed = data_health.HealthFinding(
        code="source.results.stale", severity="error", scope="source", tour="atp",
        entity="merged-results:atp", evidence={"ageDays": 9},
        message="atp: newest completed match is 9d old",
    ).as_dict()
    report_path = tmp_path / "health.json"
    report_path.write_text(json.dumps({
        "generated": "2026-08-23",
        "findingSchema": data_health.FINDING_SCHEMA,
        "findingSnapshot": "authoritative",
        "ok": False,
        "findings": [typed],
    }), encoding="utf-8")
    python = shlex.quote(sys.executable)
    module = f"{python} -m tennis_model.data.health"
    detailed: list[str] = []

    code, calls = _run_script(DATA_SCRIPT, {
        "MODE": "quick",
        "HEALTH_REPORT": str(report_path),
        "FINDING_SNAPSHOT": "authoritative",
        "HEALTH_PAGE_URL": "https://deuce-forecast.web.app/health/",
        "PYTHONPATH": str(REPO / "tennis_model" / "src"),
        "FINDINGS_CMD": f"{module} --findings-json",
        "FINDING_BODY_CMD": f"{module} --finding-body",
        "PYTHON_BIN": sys.executable,
        "FAKE_DATA_ISSUES_JSON": "[]",
    }, full_calls=detailed)

    assert code == 1 and calls == ["label create", "issue list", "issue create"]
    create = next(argv for argv in _full_argv(detailed) if argv[:2] == ["issue", "create"])
    assert typed["code"] in create[5] and typed["entity"] in create[5]

def test_data_health_ok_with_no_issue_is_quiet():
    code, calls = _run_data([])
    assert code == 0
    assert calls == ["label create", "issue list"]


def test_data_health_rejects_unknown_mode_before_github_mutation():
    code, calls, output = _run_data([], mode="unexpected", with_output=True)
    assert code == 1 and calls == [] and output == {"represented": "false"}


def test_data_health_info_findings_do_not_open_or_keep_incidents_alive():
    code, calls = _run_data([_finding(severity="info")], issues=[_data_issue(9)])
    assert code == 0
    assert calls == ["label create", "issue list", "issue comment", "issue close"]


def test_data_health_failure_opens_an_issue_and_reds_the_run():
    """Onset: one issue, one email, run goes red — on quick runs too."""
    for mode in ("full", "quick"):
        code, calls = _run_data([_finding()], mode=mode)
        assert code == 1, f"onset on {mode} must red"
        assert calls == ["label create", "issue list", "issue create"]


def test_data_health_create_uses_exact_keyed_title_label_and_body_file():
    detailed: list[str] = []
    code, _calls = _run_data([_finding()], mode="quick", full_calls=detailed)
    assert code == 1
    create = next(argv for argv in _full_argv(detailed) if argv[:2] == ["issue", "create"])
    assert create[:4] == ["issue", "create", "--label", "data-health"]
    assert create[4:6] == ["--title", "[data-health] ATP · source.results.stale · merged-results:atp"]
    assert create[6] == "--body-file" and Path(create[7]).name.startswith("body-")


def test_data_health_body_marker_mismatch_is_unrepresented_and_never_creates():
    code, calls, output = _run_data(
        [_finding()], mode="quick", with_output=True,
        extra_env={"FAKE_BODY_MISMATCH": "1"})
    assert code == 1 and output == {"represented": "false"}
    assert calls == ["label create", "issue list"]


def test_data_health_oversized_body_is_unrepresented_and_never_creates():
    code, calls, output = _run_data(
        [_finding()], mode="quick", with_output=True,
        extra_env={"FAKE_BODY_OVERSIZE": "1"})
    assert code == 1 and output == {"represented": "false"}
    assert calls == ["label create", "issue list"]


def test_data_health_standing_failure_comments_and_reds_on_full():
    """The daily heartbeat."""
    code, calls = _run_data([_finding()], issues=[_data_issue(9)], mode="full")
    assert code == 1
    assert calls == ["label create", "issue list", "issue comment"]


def test_data_health_standing_failure_stays_green_on_unchanged_quick():
    """Identity lives in the fingerprint, so unchanged quick runs are silent."""
    code, calls = _run_data([_finding()], issues=[_data_issue(9)], mode="quick")
    assert code == 0
    assert calls == ["label create", "issue list"]


def test_data_health_evidence_revision_updates_one_issue_without_new_onset():
    current = _finding(revision=_REV_B, evidence={"ageDays": 10})
    code, calls = _run_data([current], issues=[_data_issue(9, revision=_REV_A)], mode="quick")
    assert code == 0
    assert calls == ["label create", "issue list", "issue comment", "issue edit"]


def test_data_health_revision_edit_failure_stays_represented_and_retries_later():
    detailed: list[str] = []
    current = _finding(revision=_REV_B, evidence={"ageDays": 10})
    code, calls, output = _run_data(
        [current], issues=[_data_issue(9, revision=_REV_A)], mode="quick",
        with_output=True, extra_env={"GH_FAIL_EDIT": "1"}, full_calls=detailed)
    assert code == 0 and output == {"represented": "true"}
    assert calls == ["label create", "issue list", "issue comment", "issue edit"]
    argv = _full_argv(detailed)
    assert next(call for call in argv if call[:2] == ["issue", "comment"])[2] == "9"
    edit = next(call for call in argv if call[:2] == ["issue", "edit"])
    assert edit[2] == "9" and edit[3] == "--body-file"


def test_data_health_multi_finding_recovery_is_independent():
    findings = [_finding(), _finding(_KEY_B, _REV_B, code="output.meta.missing",
                                     entity="meta:wta", tour="wta")]
    issues = [_data_issue(10), _data_issue(11, _KEY_B, _REV_B)]
    code, calls = _run_data(findings, issues=issues, mode="quick")
    assert code == 0 and calls == ["label create", "issue list"]

    code, calls = _run_data([findings[1]], issues=issues, mode="quick")
    assert code == 0
    assert calls == ["label create", "issue list", "issue comment", "issue close"]


def test_partial_gate_snapshot_dedupes_present_key_without_resolving_absent_incidents():
    gate = _finding(
        _KEY_B, _REV_B, code="output.meta.missing", entity="meta:wta", tour="wta")
    issues = [
        _legacy_issue(8),
        _data_issue(9, _KEY_A, _REV_A),  # unrelated source-health incident
        _data_issue(10, _KEY_B, _REV_B),
        _data_issue(11, _KEY_B, _REV_B),  # duplicate of the present gate finding
    ]
    detailed: list[str] = []

    code, calls, output = _run_data(
        [gate], issues=issues, mode="quick", with_output=True,
        extra_env={"FINDING_SNAPSHOT": "partial"}, full_calls=detailed)

    assert code == 0 and output == {"represented": "true"}
    assert calls == ["label create", "issue list", "issue comment", "issue close"]
    mutations = [argv for argv in _full_argv(detailed)
                 if argv[:2] in (["issue", "comment"], ["issue", "close"])]
    assert [argv[2] for argv in mutations] == ["11", "11"]
    assert all("Recovered:" not in " ".join(argv) for argv in mutations)


def test_data_health_recurrence_reopens_the_original_issue():
    code, calls = _run_data([_finding()], issues=[_data_issue(12, state="CLOSED")],
                            mode="quick")
    assert code == 1
    assert calls == ["label create", "issue list", "issue reopen", "issue comment",
                     "issue edit"]
    assert "issue create" not in calls


def test_data_health_reopen_failure_is_unrepresented_and_red():
    detailed: list[str] = []
    code, calls, output = _run_data(
        [_finding()], issues=[_data_issue(12, state="CLOSED")], mode="quick",
        with_output=True, extra_env={"GH_FAIL_REOPEN": "1"}, full_calls=detailed)
    assert code == 1 and output == {"represented": "false"}
    assert calls == ["label create", "issue list", "issue reopen"]
    assert next(call for call in _full_argv(detailed)
                if call[:2] == ["issue", "reopen"]) == ["issue", "reopen", "12"]


def test_data_health_open_duplicate_outranks_lower_closed_history():
    issues = [
        _data_issue(5, state="CLOSED"),
        _data_issue(10, state="OPEN"),
    ]
    code, calls = _run_data([_finding()], issues=issues, mode="quick")
    assert code == 0
    assert calls == ["label create", "issue list"]


def test_data_health_legacy_migration_creates_keys_before_retiring_aggregate():
    findings = [_finding(), _finding(_KEY_B, _REV_B, code="output.meta.missing",
                                     entity="meta:wta", tour="wta")]
    code, calls = _run_data(findings, issues=[_legacy_issue()], mode="quick")
    assert code == 0, "migration of an already-represented failure is not a new onset"
    assert calls == ["label create", "issue list", "issue create", "issue create",
                     "issue comment", "issue close"]


def test_data_health_failed_migration_keeps_legacy_as_the_owner():
    code, calls, output = _run_data(
        [_finding()], issues=[_legacy_issue()], mode="quick", with_output=True,
        extra_env={"GH_FAIL_CREATE": "1"})
    assert code == 0 and output == {"represented": "true"}
    assert calls == ["label create", "issue list", "issue create"]
    assert "issue close" not in calls, "legacy owner was retired before keyed creation"


def test_data_health_unrepresented_create_failure_reds_and_publishes_false():
    code, calls, output = _run_data(
        [_finding()], mode="quick", with_output=True,
        extra_env={"GH_FAIL_CREATE": "1"})
    assert code == 1 and output == {"represented": "false"}
    assert calls == ["label create", "issue list", "issue create"]


def test_data_health_clean_run_retires_the_legacy_aggregate():
    code, calls = _run_data([], issues=[_legacy_issue()], mode="quick")
    assert code == 0
    assert calls == ["label create", "issue list", "issue comment", "issue close"]


def test_data_health_recovery_close_failure_stays_green_and_defers_cleanup():
    detailed: list[str] = []
    code, calls, output = _run_data(
        [], issues=[_data_issue(9)], mode="quick", with_output=True,
        extra_env={"GH_FAIL_CLOSE": "1"}, full_calls=detailed)
    assert code == 0 and output == {"represented": "true"}
    assert calls == ["label create", "issue list", "issue comment", "issue close"]
    assert next(call for call in _full_argv(detailed)
                if call[:2] == ["issue", "close"]) == ["issue", "close", "9"]


@pytest.mark.parametrize("payload", ["not json", {}, [_finding(), _finding()]])
def test_data_health_malformed_or_duplicate_manifest_reds_without_issue_mutation(payload):
    code, calls = _run_data(payload)
    assert code == 1
    assert calls == []


# --- pipeline/workflow failures that the two specialist reporters do not own -------------

def test_pipeline_reporter_accepts_each_expected_run_shape():
    for kind in ("full", "quick-data", "quick-web"):
        code, calls, output, _, log = _run_pipeline(kind=kind)
        assert code == 0, (kind, log)
        assert _outputs(output) == {"handled": "true", "state": "healthy"}
        assert calls == ["label create", "label create", "issue list"]


def test_pipeline_failure_opens_a_mode_keyed_issue_with_gate_evidence():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8", newline="\n") as f:
        f.write('{"schema":"predeploy-gate-v1","blocking":[{"problem":"bad odds"}]}')
        report = f.name
    try:
        outcomes = _stage_outcomes("full", gate="failure", health="skipped", build="skipped",
                                   deploy="skipped", verifydeploy="skipped",
                                   reportdata="skipped", reportdeploy="success")
        code, calls, output, body, _ = _run_pipeline(
            kind="full", outcomes=outcomes, extra_env={"GATE_REPORT": report})
    finally:
        os.unlink(report)
    assert code == 1 and _outputs(output) == {"handled": "true", "state": "failure"}
    assert calls == ["label create", "label create", "issue list", "issue create"]
    assert "pipeline-health-key: full" in body and "gate: failure" in body
    assert "bad odds" in body


@pytest.mark.parametrize(("kind", "report_outcome"), [
    ("full", "failure"),
    ("quick-data", "failure"),
    ("quick-data", "success"),
    ("quick-web", "failure"),
])
def test_typed_gate_findings_are_owned_without_a_duplicate_pipeline_issue(kind, report_outcome):
    skipped = {
        "gate": "failure", "health": "skipped", "setup_node": "skipped",
        "restore_next": "skipped", "build": "skipped", "deploy": "skipped",
        "verifydeploy": "skipped", "snapshot": "skipped", "persist": "skipped",
        "mirror": "skipped", "reportdata": report_outcome,
    }
    code, calls, output, body, log = _run_pipeline(
        kind=kind, outcomes=_stage_outcomes(kind, **skipped),
        extra_env={"DATA_REPRESENTED": "true"})

    assert code == 0, log
    assert _outputs(output) == {"handled": "true", "state": "owned"}
    assert calls == []
    assert body == ""


def test_owned_gate_failure_cannot_close_an_unverified_generic_pipeline_incident():
    outcomes = _stage_outcomes(
        "full", gate="failure", health="skipped", setup_node="skipped",
        restore_next="skipped", build="skipped", deploy="skipped",
        verifydeploy="skipped", snapshot="skipped", persist="skipped",
        reportdata="failure")
    code, calls, output, body, log = _run_pipeline(
        kind="full", outcomes=outcomes, existing_by_key={"full": "44"},
        extra_env={"DATA_REPRESENTED": "true"})

    assert code == 0, log
    assert _outputs(output) == {"handled": "true", "state": "owned"}
    assert calls == []
    assert body == ""


def test_unrepresented_gate_failure_still_falls_back_to_pipeline_issue():
    outcomes = _stage_outcomes(
        "quick-data", gate="failure", health="skipped", setup_node="skipped",
        restore_next="skipped", build="skipped", deploy="skipped",
        verifydeploy="skipped", reportdata="failure")
    code, calls, output, body, _ = _run_pipeline(
        kind="quick-data", outcomes=outcomes,
        extra_env={"DATA_REPRESENTED": "false"})
    assert code == 1 and _outputs(output) == {"handled": "true", "state": "failure"}
    assert calls[-1] == "issue create" and "gate: failure" in body


def test_pipeline_issue_prioritizes_blockers_in_an_oversized_gate_report():
    payload = {
        "schema": "predeploy-gate-v1", "ok": False,
        "blocking": [{"scope": "atp", "problem": "ROOT BLOCKER"}],
        "advisory": [{"scope": "atp", "problem": f"advisory-{i}-" + "x" * 300}
                     for i in range(100)],
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8", newline="\n") as f:
        json.dump(payload, f)
        report = f.name
    try:
        code, _, _, body, _ = _run_pipeline(
            kind="full", outcomes=_stage_outcomes("full", gate="failure"),
            extra_env={"GATE_REPORT": report, "DATA_REPRESENTED": "false"})
    finally:
        os.unlink(report)
    assert code == 1 and "ROOT BLOCKER" in body
    assert '"advisoryOmitted": 90' in body
    assert "advisory-99" not in body


def test_standing_pipeline_failure_comments_on_full_but_not_hourly_quick():
    failed_full = _stage_outcomes("full", retrain="failure")
    code, calls, output, _, _ = _run_pipeline(
        kind="full", outcomes=failed_full, existing_by_key={"full": "31"})
    assert (code == 1 and _outputs(output) == {"handled": "true", "state": "failure"}
            and calls[-1] == "issue comment")
    failed_quick = _stage_outcomes("quick-data", quick="failure")
    code, calls, output, _, _ = _run_pipeline(
        kind="quick-data", outcomes=failed_quick,
        existing_by_key={"quick-data": "32"})
    assert code == 1 and _outputs(output) == {"handled": "true", "state": "failure"}
    assert "issue comment" not in calls and "issue create" not in calls


def test_unexpected_required_skip_is_a_pipeline_failure():
    outcomes = _stage_outcomes("quick-data", build="skipped")
    code, _, _, body, _ = _run_pipeline(kind="quick-data", outcomes=outcomes)
    assert code == 1 and "build: skipped" in body

    # Publication now owns every mode, not only a web-only push. A skipped lineage/
    # legacy mirror must never be mistaken for a healthy data refresh.
    outcomes = _stage_outcomes("full", mirror="skipped")
    code, _, _, body, _ = _run_pipeline(kind="full", outcomes=outcomes)
    assert code == 1 and "mirror: skipped" in body


def test_data_and_deploy_failures_keep_their_existing_issue_owners():
    owned = _stage_outcomes("quick-data", verifydeploy="failure", reportdeploy="failure",
                              reportdata="failure")
    code, calls, output, _, log = _run_pipeline(kind="quick-data", outcomes=owned)
    assert code == 0, log
    assert _outputs(output) == {"handled": "true", "state": "owned"}
    assert "issue create" not in calls


def test_unrepresented_specialist_reporter_failure_falls_back_to_pipeline_health():
    data_failed = _stage_outcomes("quick-data", reportdata="failure")
    code, _, output, body, _ = _run_pipeline(
        kind="quick-data", outcomes=data_failed, extra_env={"DATA_REPRESENTED": "false"})
    assert code == 1 and _outputs(output)["state"] == "failure"
    assert "failed before representing data-health" in body

    deploy_failed = _stage_outcomes("quick-data", verifydeploy="failure",
                                    reportdeploy="failure")
    code, _, output, body, _ = _run_pipeline(
        kind="quick-data", outcomes=deploy_failed,
        extra_env={"DEPLOY_REPRESENTED": "false"})
    assert code == 1 and _outputs(output)["state"] == "failure"
    assert "deploy-health failure was not represented" in body


def test_quick_recovery_cannot_close_a_full_pipeline_incident():
    code, calls, _, _, _ = _run_pipeline(
        kind="quick-data", existing_by_key={"full": "41"})
    assert code == 0
    assert "issue comment" not in calls and "issue close" not in calls
    code, calls, _, _, _ = _run_pipeline(kind="full", existing_by_key={"full": "41"})
    assert code == 0 and calls[-2:] == ["issue comment", "issue close"]


def test_pipeline_issue_api_unknown_preserves_signal_without_guessing():
    code, calls, output, _, _ = _run_pipeline(kind="full", fail_list=True)
    assert code == 0 and _outputs(output) == {"handled": "true", "state": "healthy"}
    assert calls.count("issue list") == 3 and "issue close" not in calls
    failed = _stage_outcomes("full", gate="failure")
    code, calls, output, _, _ = _run_pipeline(
        kind="full", outcomes=failed, fail_list=True,
        extra_env={"DATA_REPRESENTED": "false"})
    assert code == 1 and _outputs(output) == {"handled": "false", "state": "failure"}
    assert "issue create" not in calls and "issue comment" not in calls


def test_terminal_reporter_routes_push_test_failures_without_blaming_refresh():
    code, calls, _, body, _ = _run_pipeline(
        context="workflow", kind="workflow",
        extra_env={"EVENT_NAME": "push", "TESTS_RESULT": "failure",
                   "REFRESH_RESULT": "skipped", "IN_JOB_HANDLED": ""})
    assert code == 1 and "pipeline-health-key: push-tests" in body
    assert calls.count("issue create") == 1


def test_terminal_reporter_closes_test_incident_then_honours_in_job_handled():
    code, calls, _, _, _ = _run_pipeline(
        context="workflow", kind="quick-data", existing_by_key={"push-tests": "52"},
        extra_env={"EVENT_NAME": "push", "TESTS_RESULT": "success",
                   "REFRESH_RESULT": "failure", "IN_JOB_HANDLED": "true",
                   "IN_JOB_STATE": "failure"})
    assert code == 0
    assert ["issue comment", "issue close"] == calls[-2:]


def test_terminal_reporter_keys_an_unhandled_timeout_by_surviving_mode():
    code, _, _, body, _ = _run_pipeline(
        context="workflow", kind="full",
        extra_env={"EVENT_NAME": "schedule", "TESTS_RESULT": "skipped",
                   "REFRESH_RESULT": "failure", "IN_JOB_HANDLED": ""})
    assert code == 1 and "pipeline-health-key: full" in body
    # A later quick path handled itself and must not touch that full incident.
    code, calls, _, _, _ = _run_pipeline(
        context="workflow", kind="quick-data", existing_by_key={"full": "61"},
        extra_env={"EVENT_NAME": "schedule", "TESTS_RESULT": "skipped",
                   "REFRESH_RESULT": "success", "IN_JOB_HANDLED": "true",
                   "IN_JOB_STATE": "healthy"})
    assert code == 0
    assert "issue comment" not in calls and "issue close" not in calls


def test_terminal_closes_generic_incident_only_after_a_clean_success():
    common = {"EVENT_NAME": "schedule", "TESTS_RESULT": "skipped",
              "IN_JOB_HANDLED": "true"}
    code, calls, _, _, _ = _run_pipeline(
        context="workflow", kind="workflow", existing_by_key={"workflow": "71"},
        extra_env={**common, "REFRESH_RESULT": "failure", "IN_JOB_STATE": "failure"})
    assert code == 0 and "issue close" not in calls
    code, calls, _, _, _ = _run_pipeline(
        context="workflow", kind="quick-data", existing_by_key={"workflow": "71"},
        extra_env={**common, "REFRESH_RESULT": "failure", "IN_JOB_STATE": "owned"})
    assert code == 0 and "issue close" not in calls       # specialist-owned red
    code, calls, _, body, _ = _run_pipeline(
        context="workflow", kind="quick-data",
        extra_env={**common, "REFRESH_RESULT": "failure", "IN_JOB_STATE": "healthy"})
    assert code == 1 and calls[-1] == "issue create"
    assert "post-actions/job result" in body
    code, calls, _, _, _ = _run_pipeline(
        context="workflow", kind="quick-data", existing_by_key={"workflow": "71"},
        extra_env={**common, "REFRESH_RESULT": "success", "IN_JOB_STATE": "healthy"})
    assert code == 0 and calls[-2:] == ["issue comment", "issue close"]


# --- extracted watchdog ---------------------------------------------------------------

def test_watchdog_fresh_closes_and_stale_opens():
    code, calls = _run_watchdog(last="1970-01-01T00:00:00Z", now=3600,
                                window="1", existing="7")
    assert code == 0 and calls[-2:] == ["issue comment", "issue close"]
    code, calls = _run_watchdog(last="1970-01-01T00:00:00Z", now=3601,
                                window="0")
    assert code == 1 and calls[-1] == "issue create"
    code, calls = _run_watchdog(last="", existing="8")
    assert code == 1 and calls[-1] == "issue comment"
    code, _ = _run_watchdog(last="1970-01-01T00:00:00Z", now=26 * 3600, window="26")
    assert code == 0
    code, calls = _run_watchdog(last="1970-01-01T00:00:00Z",
                                now=26 * 3600 + 1, window="26")
    assert code == 1 and calls[-1] == "issue create"


def test_watchdog_transport_unknown_never_claims_a_liveness_failure():
    code, calls = _run_watchdog(fail_api=True)
    assert code == 1 and calls == ["api repos/owner/repo/actions/workflows/refresh.yml/runs?status=success&per_page=1"] * 3
    code, calls = _run_watchdog(last="1970-01-01T00:00:00Z", now=0,
                                fail_list=True)
    assert code == 0 and calls.count("issue list") == 3
    assert "issue close" not in calls
    code, calls = _run_watchdog(last="", fail_list=True)
    assert code == 1 and "issue create" not in calls and "issue comment" not in calls


def test_watchdog_rejects_malformed_inputs_without_touching_issues():
    code, calls = _run_watchdog(window="oops")
    assert code == 1 and calls == []
    code, calls = _run_watchdog(last="not-a-timestamp")
    assert code == 1 and all(call.startswith("api ") for call in calls)


# --- the scripts must actually be the ones CI runs ---------------------------------------

# --- mode selection (decide-mode.sh) -----------------------------------------------------
#
# The second inline-shell regression, found 2026-07-25. `Decide mode` compared
# github.event.schedule to "0 6 * * *"; GitHub attributed the run occupying the daily slot
# to the HOURLY cron string instead, so the FULL branch never fired on 07-21..07-25 and the
# only successful full retrain in that window was a hand-dispatched one. Same lesson as the
# alert scripts: shell that decides something this important needs a test.

def _run_mode(event: str, hour: str = "06", dispatch: str = "auto", predictor: bool = True,
              last_full: str | None = None, today: str = "2026-07-26"):
    """Run the real decide-mode.sh; returns (exit_code, selected_mode).

    `last_full` is the date in the marker file the retrain step writes (None = no marker)."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "gh_out"
        out.write_text("", encoding="utf-8")
        pkl = Path(td) / "predictor.pkl"
        if predictor:
            pkl.write_text("x", encoding="utf-8")
        marker = Path(td) / ".last_full_run"
        if last_full:
            marker.write_text(last_full + "\n", encoding="utf-8")
        env = {**os.environ, "EVENT_NAME": event, "DISPATCH_MODE": dispatch,
               "NOW_HOUR": hour, "NOW_DATE": today, "MARKER": str(marker),
               "PREDICTOR": str(pkl), "GITHUB_OUTPUT": str(out)}
        p = subprocess.run([_BASH, str(MODE_SCRIPT)], env=env, capture_output=True,
                           text=True, timeout=60)
        modes = [ln.split("=", 1)[1] for ln in out.read_text(encoding="utf-8").splitlines()
                 if ln.startswith("mode=")]
        return p.returncode, (modes[-1] if modes else None)


def test_the_first_scheduled_run_after_the_slot_retrains():
    """Delivery jitter must not cost the day's retrain. The previous attempt required a run
    to land exactly in hour 06 and missed on its very first day: on 2026-07-26 GitHub
    delivered scheduled runs at 04:02, 07:05 and 08:03 and NOTHING in hour 06, so the model
    went 35h without retraining. Replay that exact sequence."""
    assert _run_mode("schedule", hour="04") == (0, "quick")          # before the slot
    assert _run_mode("schedule", hour="07") == (0, "full")           # first one after it
    # ...and once claimed, the rest of the day stays cheap
    assert _run_mode("schedule", hour="08", last_full="2026-07-26") == (0, "quick")


def test_the_slot_is_claimed_exactly_once_per_day():
    """A full run costs ~30 min and takes the deploy with it if it fails, so the marker must
    make this at-most-once-daily — no hourly storm, whatever GitHub does."""
    for hour in ("06", "07", "12", "23"):
        assert _run_mode("schedule", hour=hour, last_full="2026-07-26") == (0, "quick"), hour
    # yesterday's marker does not satisfy today
    assert _run_mode("schedule", hour="06", last_full="2026-07-25") == (0, "full")
    # a fresh cache (no marker at all) retrains at the first opportunity
    assert _run_mode("schedule", hour="09", last_full=None) == (0, "full")


def test_hours_08_and_09_do_not_abort_as_bad_octal():
    """`[ 08 -ge 06 ]` is a base-10 trap: bash reads a leading zero as octal, 8 and 9 are
    invalid digits, and under `set -e` the script would die instead of deciding."""
    for hour in ("08", "09"):
        code, mode = _run_mode("schedule", hour=hour)
        assert code == 0 and mode == "full", (hour, code, mode)


def test_runs_before_the_slot_stay_quick():
    """The small hours are ordinary hourly refreshes — retraining then would just move the
    outage, not remove it."""
    for hour in ("00", "03", "05"):
        assert _run_mode("schedule", hour=hour) == (0, "quick"), hour


def test_mode_does_not_depend_on_which_cron_github_blames():
    """The whole point: the decision reads the clock, so the script has no input for a cron
    string at all. If someone reintroduces one, this fails."""
    # comments explain the bug on purpose; only executable lines must be free of it
    code = [ln for ln in MODE_SCRIPT.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]
    assert not any("event.schedule" in ln or "0 6 * * *" in ln for ln in code), \
        "decide-mode.sh is keying off the cron string again — that is the bug"
    assert "event.schedule" not in WORKFLOW.read_text(encoding="utf-8")


def test_dispatch_input_overrides_the_slot_in_both_directions():
    for hour, want in (("06", "quick"), ("13", "quick")):
        assert _run_mode("workflow_dispatch", hour=hour, dispatch="quick") == (0, want)
    for hour in ("06", "13"):
        assert _run_mode("workflow_dispatch", hour=hour, dispatch="full") == (0, "full")
    # "auto" defers to the slot rule; a dispatch is not a scheduled run, so it stays quick
    assert _run_mode("workflow_dispatch", hour="06", dispatch="auto") == (0, "quick")


def test_missing_predictor_forces_a_full_build():
    """First run, or an evicted cache: there is no model to refresh from."""
    code, mode = _run_mode("schedule", hour="13", predictor=False)
    assert code == 0 and mode == "full", (code, mode)
    # ...but an explicit `quick` dispatch with no model must not be honoured into a crash
    assert _run_mode("workflow_dispatch", dispatch="quick", predictor=False) == (0, "full")


def test_push_runs_stay_quick():
    """A push deploys code, not a retrain — the daily slot owns that."""
    assert _run_mode("push", hour="06") == (0, "quick")


# --- the daily ratings walk must be hard to lose (2026-07-25) ----------------------------
#
# CI has no PyYAML, so these read the workflow as text — same approach as the two guards
# below. Each pins a property that a real incident took away.

def _step_blocks() -> dict:
    """{step name: its YAML block} — split on the `- name:` boundaries, no yaml dep."""
    import re
    wf = WORKFLOW.read_text(encoding="utf-8")
    parts = re.split(r"\n      - name: ", wf)
    return {p.split("\n", 1)[0].strip(): p for p in parts[1:]}


def test_a_failed_download_cannot_skip_the_retrain():
    """The five-day outage (2026-07-19..24). Downloads and the retrain shared one `run:`
    block, and a `run:` block is `bash -e`, so a non-zero `--strict` exit aborted it
    before the pipeline line ever ran. They must be separate steps, and the retrain must
    not be conditioned on the download succeeding."""
    steps = _step_blocks()
    dl = next((b for n, b in steps.items() if n.startswith("Download sources")), None)
    rt = next((b for n, b in steps.items() if n.startswith("Full retrain")), None)
    assert dl and rt, f"expected separate download + retrain steps, got {list(steps)}"

    # the exact regression: never both commands in one shell block
    assert "tennis_model.pipeline" not in dl, "download and retrain are in one run: block again"
    assert "data.download" not in rt

    # a download failure must not stop the job, and must not gate the retrain
    assert "continue-on-error: true" in dl, "a failed download aborts the job again"
    assert "steps.download" not in rt, "the retrain is gated on the download again"


def test_the_retrain_step_claims_the_day_before_running():
    """decide-mode.sh reads a date marker to use the daily slot exactly once. If the retrain
    step stops writing it, every scheduled run after 06:00Z would retrain — a ~30-minute job
    every hour, each one able to block the deploy. Written BEFORE the pipeline so a crash
    cannot retry all day either."""
    rt = next((b for n, b in _step_blocks().items() if n.startswith("Full retrain")), None)
    assert rt and ".last_full_run" in rt, "the retrain step no longer claims the day"
    body = rt[rt.index("run:"):]
    assert body.index(".last_full_run") < body.index("tennis_model.pipeline"), \
        "the marker must be written BEFORE the pipeline, not after it succeeds"
    assert ".last_full_run" in MODE_SCRIPT.read_text(encoding="utf-8")


def test_a_failed_download_still_reds_the_run():
    """Non-fatal must not mean unreported: a trailing step escalates after the deploy,
    the same shape the forecast-log push already uses."""
    steps = _step_blocks()
    tail = next((b for n, b in steps.items() if n.startswith("Fail if source downloads")), None)
    assert tail, "nothing reds the run on an incomplete download"
    assert "steps.download.outcome == 'failure'" in tail
    assert "exit 1" in tail


def test_the_data_cache_is_saved_even_when_the_run_fails():
    """`actions/cache` only saves on a green job, so an export crash / blocked gate /
    deploy hiccup discarded a ratings walk that had already completed and written
    predictor.pkl — and the next run restored the OLD model, freezing ratings for as long
    as the late-stage bug lasted. Restore and save are split so save can be if: always()."""
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert "actions/cache/restore@" in wf and "actions/cache/save@" in wf, \
        "cache is a single actions/cache step again — it will not save on a red run"
    save = next((b for n, b in _step_blocks().items() if n.startswith("Save data cache")), None)
    assert save and "if: always()" in save, "the cache save is conditional again"


def test_release_snapshot_preserves_live_identity_and_draw_caches():
    """The live cache is the only durable carrier for old draw and ESPN identity evidence;
    one Actions-cache eviction must restore it alongside the historical archive."""
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert "raw/atp/live raw/wta/live" in wf
    assert "tennis_model/data/raw/atp/live" in wf
    assert "tennis_model/data/raw/wta/live" in wf


def test_workflow_invokes_this_script():
    """Guards against the script drifting out of use: if refresh.yml stops calling it,
    every test above would keep passing while testing dead code."""
    assert SCRIPT.exists(), f"missing {SCRIPT}"
    assert DATA_SCRIPT.exists(), f"missing {DATA_SCRIPT}"
    assert PIPELINE_SCRIPT.exists(), f"missing {PIPELINE_SCRIPT}"
    assert WATCHDOG_SCRIPT.exists(), f"missing {WATCHDOG_SCRIPT}"
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert ".github/scripts/report-deploy-health.sh" in wf
    assert ".github/scripts/report-data-health.sh" in wf
    report_block = wf[wf.index("- name: Report data health"):wf.index("- name: Report deploy health")]
    assert "steps.health.outcome == 'success' || steps.gate.outcome == 'failure'" in report_block
    assert "predeploy-gate.json" in report_block and "data/output/health.json" in report_block
    assert "FINDING_SNAPSHOT:" in report_block
    assert "steps.gate.outcome == 'failure' && 'partial' || 'authoritative'" in report_block
    assert "OK=$(" not in report_block and "CHANGED=$(" not in report_block
    data_script = DATA_SCRIPT.read_text(encoding="utf-8")
    assert "--findings-json" in data_script and "--finding-body" in data_script
    assert ".github/scripts/report-pipeline-health.sh" in wf
    assert MODE_SCRIPT.exists(), f"missing {MODE_SCRIPT}"
    assert ".github/scripts/decide-mode.sh" in wf
    assert SCOPE_SCRIPT.exists(), f"missing {SCOPE_SCRIPT}"
    assert ".github/scripts/decide-push-scope.sh" in wf
    assert "if: always()" in wf, "the never-ran guard only matters under if: always()"
    watchdog = WATCHDOG_WORKFLOW.read_text(encoding="utf-8")
    assert "actions/checkout@" in watchdog
    assert "contents: read" in watchdog
    assert ".github/scripts/report-watchdog.sh" in watchdog


def test_live_verifier_pipeline_propagates_failure():
    """tee must not turn a failed Node verifier into a green workflow step."""
    block = next((b for n, b in _step_blocks().items() if n == "Verify live Firebase deploy"), None)
    assert block and "set -o pipefail" in block
    assert "node scripts/verify-deploy.mjs 2>&1 | tee /tmp/verify-deploy.log" in block


def _run_scope(event: str, files: list[str]) -> str:
    with tempfile.TemporaryDirectory() as td:
        output = Path(td) / "output"
        env = {
            **os.environ,
            "EVENT_NAME": event,
            "CHANGED_FILES": "\n".join(files),
            "GITHUB_OUTPUT": str(output),
        }
        p = subprocess.run([_BASH, str(SCOPE_SCRIPT)], cwd=REPO, env=env,
                           capture_output=True, text=True, timeout=30)
        assert p.returncode == 0, p.stderr
        return output.read_text(encoding="utf-8").strip()


def test_push_scope_only_skips_data_refresh_for_web_and_neutral_docs():
    assert _run_scope("schedule", ["web/app/page.tsx"]) == "scope=data"
    assert _run_scope("push", ["web/app/page.tsx"]) == "scope=web"
    assert _run_scope("push", ["web/app/page.tsx", "tasks/todo.md"]) == "scope=web"
    assert _run_scope("push", ["firebase.json"]) == "scope=web"
    assert _run_scope("push", ["web/app/page.tsx", "tennis_model/src/x.py"]) == "scope=data"


def test_master_deploy_is_test_gated_and_docs_do_not_trigger_it():
    wf = WORKFLOW.read_text(encoding="utf-8")
    tests = TEST_WORKFLOW.read_text(encoding="utf-8")
    assert "paths-ignore:" in wf and "tasks/**" in wf
    assert "uses: ./.github/workflows/test.yml" in wf
    assert "needs: tests" in wf
    assert "needs.tests.result == 'success'" in wf
    assert "workflow_call:" in tests
    assert "branches-ignore: [master]" in tests


def test_pipeline_reporters_cover_the_job_tail_and_terminal_failures():
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert "pipeline_health_handled: ${{ steps.reportpipeline.outputs.handled }}" in wf
    assert "pipeline_health_state: ${{ steps.reportpipeline.outputs.state }}" in wf
    assert wf.index("id: savecache") < wf.index("id: reportpipeline")
    assert "id: reportpipeline\n        if: always()" in wf
    terminal = wf[wf.index("  report-workflow-health:"):]
    assert "needs: [tests, refresh]" in terminal
    assert "if: ${{ always() }}" in terminal
    assert "IN_JOB_HANDLED: ${{ needs.refresh.outputs.pipeline_health_handled }}" in terminal
    assert "IN_JOB_STATE: ${{ needs.refresh.outputs.pipeline_health_state }}" in terminal
    assert "DATA_REPRESENTED: ${{ steps.reportdata.outputs.represented }}" in wf
    assert "DEPLOY_REPRESENTED: ${{ steps.reportdeploy.outputs.represented }}" in wf


def test_publication_is_fail_closed_and_web_uses_only_accepted_cached_lineage():
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert "steps.scope.outputs.scope != 'web'" in wf
    assert "python -m tennis_model.data.health --gate" in wf
    assert "python -m tennis_model.data.health" in wf
    assert "Verify live Firebase deploy" in wf
    publication = wf[
        wf.index("      - name: Publish accepted release data"):
        wf.index("      # Durably persist the append-only forecast log")
    ]
    assert "set -euo pipefail" in publication
    assert "PUBLICATION_SCOPE: ${{ steps.scope.outputs.scope }}" in publication
    assert 'case "$PUBLICATION_SCOPE" in' in publication
    web_case = publication[publication.index("            web)"):
                           publication.index("            data)")]
    data_case = publication[publication.index("            data)"):
                            publication.index("            *)")]
    assert "python -m tennis_model.artifact_lineage publish --scope web" in web_case
    assert "--semantic-gate-passed" not in web_case and "--validator" not in web_case
    assert "python -m tennis_model.artifact_lineage publish --scope data" in data_case
    assert "--semantic-gate-passed --validator predeploy-integrity-gate-v1" in data_case
    assert "refusing publication for unknown push scope" in publication
    for forbidden in (
        "continue-on-error", "shadow", "legacy", "fallback", "|| true", "cp ", "find ",
    ):
        assert forbidden not in publication
    assert wf.index("id: gate") < wf.index("id: mirror") < wf.index("id: health")
    assert "find \"tennis_model/data/output/$tour\"" not in wf


def test_deploy_inputs_are_cached_and_firebase_tooling_is_immutable():
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert "cache: pip" in wf
    assert "cache: npm" in wf
    assert "path: web/.next/cache" in wf
    assert "firebaseToolsVersion: \"15.25.0\"" in wf
    assert "FirebaseExtended/action-hosting-deploy@500ac625ca2dd40cbd15f7659af953801858032a" in wf


def test_no_alert_logic_is_left_inline_in_the_workflow():
    """AGENTS.md: alert branching lives in .github/scripts/ so it is reachable by this
    file. An inline `gh issue create` is by definition untested branching."""
    for path in sorted((REPO / ".github" / "workflows").glob("*.y*ml")):
        wf = path.read_text(encoding="utf-8")
        for forbidden in ("gh issue create", "gh issue close", "gh issue comment"):
            assert forbidden not in wf, \
                f"{forbidden!r} is inline in {path.name} — move it to a script"


# --- the alias proposer's PR script ------------------------------------------------------

def _run_alias(config_changed: bool, body: str | None = "## proposals\n- something\n",
               dry_run: bool = True, fail_pr: bool = False):
    """Run open-alias-pr.sh inside a throwaway git repo, so `git diff` is real."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "gh").write_text(_GH_STUB, encoding="utf-8", newline="\n")
        (tmp / "gh").chmod(0o755)
        calls = tmp / "calls.txt"
        calls.write_text("", encoding="utf-8")
        repo = tmp / "repo"
        (repo / "tennis_model" / "src" / "tennis_model").mkdir(parents=True)
        cfg = repo / "tennis_model" / "src" / "tennis_model" / "config.py"
        cfg.write_text("PLAYER_ALIASES = {}\n", encoding="utf-8", newline="\n")
        for cmd in (["init", "-q", "-b", "master"], ["add", "-A"],
                    ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"]):
            subprocess.run(["git", *cmd], cwd=repo, check=True, capture_output=True)
        if config_changed:
            cfg.write_text('PLAYER_ALIASES = {"a b c": "A B"}\n', encoding="utf-8", newline="\n")
        body_file = tmp / "body.md"
        if body is not None:
            body_file.write_text(body, encoding="utf-8", newline="\n")
        if not dry_run:                       # give the push a real remote to land on
            bare = tmp / "origin.git"
            subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True,
                           capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=repo,
                           check=True, capture_output=True)
        env = {**os.environ, "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}",
               "GH_CALLS": str(calls), "FAKE_EXISTING": "", "GH_FAIL_LIST": "",
               "GH_FAIL_PR": "1" if fail_pr else "",
               "BODY_FILE": str(body_file), "BRANCH": "alias/test",
               "DRY_RUN": "1" if dry_run else ""}
        p = subprocess.run([_BASH, str(ALIAS_SCRIPT)], cwd=repo, env=env,
                           capture_output=True, text=True, timeout=60)
        return p.returncode, [ln for ln in calls.read_text(encoding="utf-8").splitlines() if ln], \
            cfg.read_text(encoding="utf-8"), p.stdout + p.stderr


def test_a_quiet_week_opens_nothing():
    """The overwhelmingly common outcome. No config change means no branch, no PR, and no
    `gh` call at all — a weekly "nothing to report" PR would be noise that trains the
    reviewer to close without reading."""
    code, calls, _, _ = _run_alias(config_changed=False)
    assert code == 0 and calls == []


def test_a_patch_without_its_evidence_is_discarded_not_opened():
    """The proposer writes the patch and the body in the same run; a patch with no body
    means the body step died. Opening it anyway would put an unreviewable model-authored
    config change in front of a human with nothing to check it against."""
    code, calls, config, _ = _run_alias(config_changed=True, body=None)
    assert code == 0 and calls == []
    assert config == "PLAYER_ALIASES = {}\n", "the unreviewable edit was left in the tree"


def test_a_real_proposal_reaches_the_pr_branch():
    code, _, _, _ = _run_alias(config_changed=True)
    assert code == 0


def test_a_directly_invoked_script_stays_executable():
    """A script a workflow runs WITHOUT an interpreter dies with exit 126 if it loses its
    executable bit, and nothing local catches it: the file still runs fine under `bash x.sh`,
    ruff and pytest never look at the mode, and `git diff` shows only the content change.

    Editing open-alias-pr.sh on 2026-08-07 silently dropped 100755 -> 100644 and the next
    dispatch failed with "Permission denied" — the same job the edit was fixing. Most scripts
    here are invoked as `bash <path>`, where the mode is irrelevant; this pins the ones where
    it is load-bearing, discovered from the workflows rather than listed by hand."""
    import re
    direct = set()
    for wf in sorted((REPO / ".github" / "workflows").glob("*.yml")):
        direct |= set(re.findall(r"run:\s*(\.github/scripts/[\w.-]+\.sh)",
                                 wf.read_text(encoding="utf-8")))
    assert direct, "no directly-invoked script found — has the invocation style changed?"
    listed = subprocess.run(["git", "ls-files", "-s", *sorted(direct)], cwd=REPO,
                            capture_output=True, text=True, check=True).stdout
    for line in listed.splitlines():
        mode, path = line.split(" ", 1)[0], line.split("\t")[-1]
        assert mode == "100755", (
            f"{path} is invoked without an interpreter but is mode {mode} — it will fail "
            f"with exit 126. Fix with: git update-index --chmod=+x {path}")
    print("ok test_a_directly_invoked_script_stays_executable")


def test_a_refused_pr_stays_green_and_says_where_the_branch_is():
    """Found 2026-08-07. The 08-03 run produced two genuine falsifier-surviving proposals,
    pushed the branch fine, then died on `gh pr create` because "Allow GitHub Actions to
    create and approve pull requests" is off for this repo — a setting no workflow can change
    from inside a run. `set -e` turned that into a red weekly job and a raw GraphQL error,
    breaking this script's own documented contract that every branch exits 0, and the pushed
    branch went unnoticed for four days. The proposals are only unannounced, never lost, so
    the run must stay green and name the branch."""
    code, calls, _, out = _run_alias(config_changed=True, dry_run=False, fail_pr=True)
    assert code == 0, f"a permissions refusal must not red the weekly job:\n{out}"
    assert "pr create" in calls, calls
    assert "pr merge" not in calls, "still never merges, even on the fallback path"
    assert "compare/master...alias/test" in out, f"the pushed branch must be named:\n{out}"
    print("ok test_a_refused_pr_stays_green_and_says_where_the_branch_is")


def test_the_proposer_can_never_merge_its_own_pr():
    """master IS production in this repo (push == deploy, no review in front of it). A bot
    that could merge would deploy a model-authored config edit with no human in the loop —
    the single thing the whole propose->falsify->PR design exists to prevent."""
    # Comments are stripped: the script explains in prose why it never merges, and a naive
    # substring check would flag its own documentation.
    script = "\n".join(ln for ln in ALIAS_SCRIPT.read_text(encoding="utf-8").splitlines()
                       if not ln.lstrip().startswith("#"))
    assert "gh pr create" in script
    assert "gh pr merge" not in script
    assert "--auto" not in script and "--admin" not in script
    wf = ALIAS_WORKFLOW.read_text(encoding="utf-8")
    assert "gh pr merge" not in wf and "gh pr create" not in wf, \
        "PR logic is inline in the workflow again — move it to the script"


def test_the_proposer_never_writes_the_pipeline_cache():
    """It restores the data cache to read the match frame. If it ever SAVED one, a proposer
    run could hand the hourly pipeline a cache it never validated."""
    wf = ALIAS_WORKFLOW.read_text(encoding="utf-8")
    assert "actions/cache/restore@" in wf
    assert "actions/cache/save@" not in wf and "uses: actions/cache@" not in wf


def test_the_llm_dependency_stays_out_of_the_pinned_pipeline_requirements():
    """requirements.txt pins exist so the retrain is reproducible and its pickles load
    across runs. The proposer's client must never ride along into that install."""
    pinned = (REPO / "tennis_model" / "requirements.txt").read_text(encoding="utf-8")
    proposer = (REPO / "tennis_model" / "requirements-propose.txt").read_text(
        encoding="utf-8")
    workflow = ALIAS_WORKFLOW.read_text(encoding="utf-8")
    assert "anthropic" not in pinned and "openrouter" not in pinned
    assert "anthropic" not in proposer.lower(), \
        "the proposer uses OpenRouter's HTTP API directly; the Anthropic SDK came back"
    assert "OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}" in workflow
    assert "ANTHROPIC_API_KEY" not in workflow


def test_the_openrouter_credential_is_never_embedded_in_tracked_proposer_files():
    """The workflow may name the secret, but neither it nor the transport may carry a key.

    OpenRouter's current key prefix gives this a deterministic check instead of relying on
    reviewers to spot a long hexadecimal value in YAML or Python.
    """
    paths = [
        ALIAS_WORKFLOW,
        REPO / "tennis_model" / "requirements-propose.txt",
        REPO / "tennis_model" / "src" / "tennis_model" / "data" / "alias_proposer.py",
    ]
    for path in paths:
        assert "sk-or-v1-" not in path.read_text(encoding="utf-8"), path


if __name__ == "__main__":
    if _BASH is None:
        print("bash unavailable — skipping")
        sys.exit(0)
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("\nALL PASSED")
