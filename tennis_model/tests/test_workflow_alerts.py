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
MODE_SCRIPT = REPO / ".github" / "scripts" / "decide-mode.sh"
ALIAS_SCRIPT = REPO / ".github" / "scripts" / "open-alias-pr.sh"
WORKFLOW = REPO / ".github" / "workflows" / "refresh.yml"
ALIAS_WORKFLOW = REPO / ".github" / "workflows" / "propose-aliases.yml"

# Windows dev boxes may lack bash; CI (ubuntu-latest) never does, which is where it counts.
_BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(_BASH is None, reason="bash unavailable (non-CI Windows shell)")

# `GH_FAIL_LIST=1` makes only `issue list` fail, standing in for the GitHub API 504 that
# redded run 30106835566 after a perfectly clean deploy.
_GH_STUB = """#!/usr/bin/env bash
echo "$1 $2" >> "$GH_CALLS"
if [ "$1 $2" = "issue list" ]; then
  if [ "${GH_FAIL_LIST:-}" = "1" ]; then
    echo 'non-200 OK status code: 504 Gateway Timeout' >&2
    exit 1
  fi
  echo "$FAKE_EXISTING"
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


def test_workflow_invokes_this_script():
    """Guards against the script drifting out of use: if refresh.yml stops calling it,
    every test above would keep passing while testing dead code."""
    assert SCRIPT.exists(), f"missing {SCRIPT}"
    assert DATA_SCRIPT.exists(), f"missing {DATA_SCRIPT}"
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert ".github/scripts/report-deploy-health.sh" in wf
    assert ".github/scripts/report-data-health.sh" in wf
    assert MODE_SCRIPT.exists(), f"missing {MODE_SCRIPT}"
    assert ".github/scripts/decide-mode.sh" in wf
    assert "if: always()" in wf, "the never-ran guard only matters under if: always()"


def test_no_alert_logic_is_left_inline_in_the_workflow():
    """AGENTS.md: alert branching lives in .github/scripts/ so it is reachable by this
    file. An inline `gh issue create` is by definition untested branching."""
    wf = WORKFLOW.read_text(encoding="utf-8")
    for forbidden in ("gh issue create", "gh issue close", "gh issue comment"):
        assert forbidden not in wf, f"{forbidden!r} is inline in refresh.yml — move it to a script"


# --- the alias proposer's PR script ------------------------------------------------------

def _run_alias(config_changed: bool, body: str | None = "## proposals\n- something\n"):
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
        env = {**os.environ, "PATH": f"{tmp}{os.pathsep}{os.environ.get('PATH', '')}",
               "GH_CALLS": str(calls), "FAKE_EXISTING": "", "GH_FAIL_LIST": "",
               "BODY_FILE": str(body_file), "DRY_RUN": "1", "BRANCH": "alias/test"}
        p = subprocess.run([_BASH, str(ALIAS_SCRIPT)], cwd=repo, env=env,
                           capture_output=True, text=True, timeout=60)
        return p.returncode, [ln for ln in calls.read_text(encoding="utf-8").splitlines() if ln], \
            cfg.read_text(encoding="utf-8")


def test_a_quiet_week_opens_nothing():
    """The overwhelmingly common outcome. No config change means no branch, no PR, and no
    `gh` call at all — a weekly "nothing to report" PR would be noise that trains the
    reviewer to close without reading."""
    code, calls, _ = _run_alias(config_changed=False)
    assert code == 0 and calls == []


def test_a_patch_without_its_evidence_is_discarded_not_opened():
    """The proposer writes the patch and the body in the same run; a patch with no body
    means the body step died. Opening it anyway would put an unreviewable model-authored
    config change in front of a human with nothing to check it against."""
    code, calls, config = _run_alias(config_changed=True, body=None)
    assert code == 0 and calls == []
    assert config == "PLAYER_ALIASES = {}\n", "the unreviewable edit was left in the tree"


def test_a_real_proposal_reaches_the_pr_branch():
    code, _, _ = _run_alias(config_changed=True)
    assert code == 0


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
    assert "anthropic" not in pinned
    assert (REPO / "tennis_model" / "requirements-propose.txt").exists()


if __name__ == "__main__":
    if _BASH is None:
        print("bash unavailable — skipping")
        sys.exit(0)
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("\nALL PASSED")
