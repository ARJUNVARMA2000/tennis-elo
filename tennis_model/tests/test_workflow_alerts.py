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
WORKFLOW = REPO / ".github" / "workflows" / "refresh.yml"

# Windows dev boxes may lack bash; CI (ubuntu-latest) never does, which is where it counts.
_BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(_BASH is None, reason="bash unavailable (non-CI Windows shell)")

_GH_STUB = """#!/usr/bin/env bash
echo "$1 $2" >> "$GH_CALLS"
if [ "$1 $2" = "issue list" ]; then echo "$FAKE_EXISTING"; fi
exit 0
"""


def _run(outcome: str, existing: str = "", mode: str = "full", verify_log: str | None = None):
    """Run the alert script with a stubbed `gh`. Returns (exit_code, [gh subcommands])."""
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
            "OUTCOME": outcome,
            "MODE": mode,
            "SITE_URL": "https://deuce-forecast.web.app",
            "GITHUB_RUN_URL": "https://example/run",
            "VERIFY_LOG": verify_log or str(tmp / "missing.log"),
        }
        p = subprocess.run([_BASH, str(SCRIPT)], env=env, capture_output=True,
                           text=True, timeout=60)
        return p.returncode, [ln for ln in calls.read_text(encoding="utf-8").splitlines() if ln]


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


# --- the script must actually be the one CI runs -----------------------------------------

def test_workflow_invokes_this_script():
    """Guards against the script drifting out of use: if refresh.yml stops calling it,
    every test above would keep passing while testing dead code."""
    assert SCRIPT.exists(), f"missing {SCRIPT}"
    wf = WORKFLOW.read_text(encoding="utf-8")
    assert ".github/scripts/report-deploy-health.sh" in wf
    assert "if: always()" in wf, "the never-ran guard only matters under if: always()"


if __name__ == "__main__":
    if _BASH is None:
        print("bash unavailable — skipping")
        sys.exit(0)
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
    print("\nALL PASSED")
