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
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

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
if [ "$1 $2" = "issue list" ]; then
  if [ "${GH_FAIL_LIST:-}" = "1" ]; then
    echo 'non-200 OK status code: 504 Gateway Timeout' >&2
    exit 1
  fi
  case "$*" in
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


def _run_script(script: Path, extra_env: dict, existing: str = "", fail_list: bool = False):
    """Run an alert script with a stubbed `gh`. Returns (exit_code, [gh subcommands])."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "gh").write_text(_GH_STUB, encoding="utf-8", newline="\n")
        (tmp / "gh").chmod(0o755)
        calls = tmp / "calls.txt"
        calls.write_text("", encoding="utf-8")
        env = {
            **os.environ,
            "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}",
            "GH_CALLS": str(calls),
            "FAKE_EXISTING": existing,
            "GH_FAIL_LIST": "1" if fail_list else "",
            "GH_RETRY_SLEEP": "0",          # keep the retry path instant under test
            "GITHUB_RUN_URL": "https://example/run",
            **extra_env,
        }
        p = subprocess.run([_BASH, str(script)], env=env, capture_output=True,
                           text=True, timeout=60)
        return p.returncode, [ln for ln in calls.read_text(encoding="utf-8").splitlines() if ln]


def _run(outcome: str, existing: str = "", mode: str = "full", verify_log: str | None = None,
         fail_list: bool = False):
    return _run_script(SCRIPT, {
        "OUTCOME": outcome,
        "MODE": mode,
        "SITE_URL": "https://deuce-forecast.web.app",
        "VERIFY_LOG": verify_log or "/nonexistent/missing.log",
    }, existing=existing, fail_list=fail_list)


def _run_data(ok: str, existing: str = "", mode: str = "full", changed: str = "True",
              fail_list: bool = False):
    return _run_script(DATA_SCRIPT, {
        "OK": ok,
        "CHANGED": changed,
        "MODE": mode,
        "HEALTH_PAGE_URL": "https://deuce-forecast.web.app/health/",
        # the real command needs the package + a built health.json; the body content is
        # not what this file tests (the branch logic is)
        "HEALTH_BODY_CMD": "echo fake-health-body",
    }, existing=existing, fail_list=fail_list)


def _run_with_step_output(script: Path, env: dict, *, existing: str = "", fail_list: bool = False):
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        output_path = f.name
    try:
        code, calls = _run_script(
            script, {**env, "GITHUB_OUTPUT": output_path}, existing=existing,
            fail_list=fail_list)
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
                 "bootstrap", "mode", "gate", "health", "setup_node", "restore_next",
                 "build", "deploy", "verifydeploy", "reportdata", "reportdeploy", "savecache"):
        values[name] = "success"
    if kind == "full":
        values.update(download="success", retrain="success", persist="success", snapshot="success")
    elif kind == "quick-data":
        values["quick"] = "success"
    elif kind == "quick-web":
        values["mirror"] = "success"
    values.update(overrides)
    return "\n".join(f"{name}={values[name]}" for name in names.split())


def _outputs(value: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in value.splitlines() if "=" in line)


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
    code, calls = _run_data("True", fail_list=True)
    assert code == 0, "an API 504 redded a run whose data health was fine"
    assert "issue create" not in calls and "issue close" not in calls


def test_data_api_outage_on_failing_data_still_reds_but_files_nothing():
    code, calls = _run_data("False", fail_list=True)
    assert code == 1
    assert "issue create" not in calls and "issue comment" not in calls


def test_specialist_reporters_publish_actual_issue_representation():
    data_env = {"OK": "False", "CHANGED": "True", "MODE": "full",
                "HEALTH_BODY_CMD": "echo body", "HEALTH_PAGE_URL": "https://example/health"}
    code, _, output = _run_with_step_output(DATA_SCRIPT, data_env)
    assert code == 1 and output == {"represented": "true"}
    code, _, output = _run_with_step_output(DATA_SCRIPT, data_env, fail_list=True)
    assert code == 1 and output == {"represented": "false"}
    code, _, output = _run_with_step_output(
        DATA_SCRIPT, {**data_env, "HEALTH_BODY_CMD": "false"})
    assert code != 0 and output == {"represented": "false"}

    deploy_env = {"OUTCOME": "failure", "MODE": "full", "SITE_URL": "https://example"}
    code, _, output = _run_with_step_output(SCRIPT, deploy_env)
    assert code == 1 and output == {"represented": "true"}
    code, _, output = _run_with_step_output(SCRIPT, deploy_env, fail_list=True)
    assert code == 1 and output == {"represented": "false"}


# --- the data-health alert matrix (was inline in refresh.yml, untested) -------------------

def test_data_health_ok_with_no_issue_is_quiet():
    code, calls = _run_data("True")
    assert code == 0
    assert calls == ["label create", "issue list"]


def test_data_health_ok_closes_an_open_issue():
    """Recovery auto-closes within the hour, on any mode."""
    for mode in ("full", "quick"):
        code, calls = _run_data("True", existing="9", mode=mode)
        assert code == 0
        assert calls == ["label create", "issue list", "issue comment", "issue close"]


def test_data_health_failure_opens_an_issue_and_reds_the_run():
    """Onset: one issue, one email, run goes red — on quick runs too."""
    for mode in ("full", "quick"):
        code, calls = _run_data("False", mode=mode)
        assert code == 1, f"onset on {mode} must red"
        assert calls == ["label create", "issue list", "issue create"]


def test_data_health_standing_failure_comments_and_reds_on_full():
    """The daily heartbeat."""
    code, calls = _run_data("False", existing="9", mode="full", changed="False")
    assert code == 1
    assert calls == ["label create", "issue list", "issue comment"]


def test_data_health_standing_failure_stays_green_on_unchanged_quick():
    """A red quick job never saves the data cache, so the prev health.json feeding
    problems_changed would stay stale and every hourly run would re-red."""
    code, calls = _run_data("False", existing="9", mode="quick", changed="False")
    assert code == 0
    assert calls == ["label create", "issue list"]          # no comment, no duplicate issue


def test_data_health_standing_failure_comments_once_when_the_problem_set_changes():
    """A NEW problem on top of a standing one must still be recorded, without redding."""
    code, calls = _run_data("False", existing="9", mode="quick", changed="True")
    assert code == 0
    assert calls == ["label create", "issue list", "issue comment"]


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
            extra_env={"GATE_REPORT": report})
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
    code, calls, output, _, _ = _run_pipeline(kind="full", outcomes=failed, fail_list=True)
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


def test_web_push_keeps_both_integrity_gates_and_uses_cached_mirror():
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert "steps.scope.outputs.scope != 'web'" in wf
    assert "steps.scope.outputs.scope == 'web'" in wf
    assert "python -m tennis_model.data.health --gate" in wf
    assert "python -m tennis_model.data.health" in wf
    assert "Verify live Firebase deploy" in wf


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
