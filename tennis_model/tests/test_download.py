"""Unit checks for the download layer's pure logic — no network.

Runnable directly (`python tests/test_download.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.download as dl


def test_strict_fatal_rules():
    """The strict gate reds the build only for failures that threaten current data:
    any stats-overlay failure, plus current-year files elsewhere. Frozen archive
    years are immutable and covered by the release snapshot. (The first CI run went
    red on exactly this logic — keep it pinned.)"""
    fails = {
        "wta/historical": [2019, 2026],
        "atp/fresh": [2026],
        "atp/stats": ["2018.csv"],
        "wta/stats": ["WTA API unreachable after 5 retries"],
    }
    out = dl.strict_fatal(fails, this_year=2026)
    assert "wta/historical:2026" in out
    assert "wta/historical:2019" not in out          # archive year: snapshot covers it
    assert "atp/fresh:2026" in out
    assert "atp/stats:2018.csv" in out               # stats overlay: always fatal
    assert any(s.startswith("wta/stats:") for s in out)
    assert dl.strict_fatal({}, 2026) == []
    print("ok test_strict_fatal_rules")


def test_valid_csv_schema_gate():
    good = b"tourney_date,winner_name,loser_name,score,w_svpt,l_svpt\n20260101,A,B,6-1 6-1,50,40\n" * 3
    html = b"<html><body>error page that is long enough to pass the size check ....</body></html>" * 3
    base_only = b"tourney_date,winner_name,loser_name,score\n20260101,A,B,6-1 6-1\n" * 5
    assert dl._valid_csv(good, dl._REQUIRED_STATS)
    assert not dl._valid_csv(html, dl._REQUIRED_STATS)
    assert not dl._valid_csv(base_only, dl._REQUIRED_STATS)   # stats columns required
    assert dl._valid_csv(base_only, dl._REQUIRED_BASE)
    assert not dl._valid_csv(b"tiny", dl._REQUIRED_BASE)
    print("ok test_valid_csv_schema_gate")


def test_download_clamps_to_source_last_year():
    """Frozen archives declare last_year — the downloader must never request files
    that cannot exist upstream (they would trip the strict gate; the first CI run
    failed on WTA 2025/2026)."""
    attempted = []
    orig_dy, orig_src = dl.download_year, dl.HISTORICAL_SOURCE
    try:
        dl.download_year = lambda tour, kind, y: attempted.append(y) or True
        dl.HISTORICAL_SOURCE = {"wta": {**orig_src["wta"], "last_year": 2024}}
        done, failed = dl.download("wta", "historical")
    finally:
        dl.download_year, dl.HISTORICAL_SOURCE = orig_dy, orig_src
    assert max(attempted) == 2024 and not failed
    print("ok test_download_clamps_to_source_last_year")


class _FakeClock:
    """Stand-in for download.py's `time` module: sleeps advance a virtual clock instead
    of blocking, so the backoff/budget paths run at full speed and are assertable."""

    def __init__(self):
        self.now = 0.0
        self.slept: list[float] = []

    def sleep(self, s):
        self.slept.append(s)
        self.now += s

    def monotonic(self):
        return self.now


def _run_download(fake_year, *, clock=None, **kw):
    """Call dl.download with download_year and the clock stubbed out."""
    clock = clock or _FakeClock()
    orig_dy, orig_time = dl.download_year, dl.time
    try:
        dl.download_year, dl.time = fake_year, clock
        return (*dl.download(**kw), clock)
    finally:
        dl.download_year, dl.time = orig_dy, orig_time


def test_download_success_path_never_sleeps():
    """The common case must cost nothing: one fetch per year, zero backoff."""
    calls = []
    done, failed, clock = _run_download(
        lambda tour, kind, y: calls.append(y) or True,
        tour="atp", kind="fresh", years=[2025, 2026],
    )
    assert done == [2025, 2026] and failed == []
    assert calls == [2025, 2026]          # no redundant refetch
    assert clock.slept == []              # no backoff on the happy path
    print("ok test_download_success_path_never_sleeps")


def test_download_recovers_transient_failure():
    """A blip that fails every year in one instant (both tours' `fresh` files live in
    ONE repo — run 29812819613) must be retried, not allowed to red the daily retrain."""
    calls = []

    def flaky(tour, kind, y):
        calls.append(y)
        return calls.count(y) > 1          # first attempt fails, retry succeeds

    done, failed, clock = _run_download(
        flaky, tour="atp", kind="fresh", years=[2025, 2026],
    )
    assert failed == [] and sorted(done) == [2025, 2026]
    assert clock.slept == [1]              # exactly one backoff round was needed
    print("ok test_download_recovers_transient_failure")


def test_download_retry_is_bounded_by_rounds():
    """A source that is genuinely down still fails — with a capped number of attempts
    and exponential backoff, so `failed` stays truthful for the strict gate."""
    calls = []
    done, failed, clock = _run_download(
        lambda tour, kind, y: calls.append(y) and False,
        tour="atp", kind="fresh", years=[2026], retry_rounds=2,
    )
    assert done == [] and failed == [2026]
    assert len(calls) == 3                 # initial pass + 2 retry rounds, no more
    assert clock.slept == [1, 2]           # exponential, not a busy loop
    print("ok test_download_retry_is_bounded_by_rounds")


def test_download_retry_budget_bounds_a_dead_archive():
    """The wall-clock budget is what keeps a dead 47-year archive from costing three
    full passes: retries stop when the budget is spent, and every year stays failed."""
    years = list(range(1980, 2027))        # 47-year historical archive
    clock = _FakeClock()
    calls = []

    def dead(tour, kind, y):
        calls.append(y)
        clock.now += 30.0                  # each attempt burns real time upstream
        return False

    done, failed, _ = _run_download(
        dead, clock=clock, tour="wta", kind="historical",
        years=years, retry_rounds=2, retry_budget_s=90.0,
    )
    assert done == [] and sorted(failed) == years        # nothing silently dropped
    assert len(calls) < 2 * len(years)                   # budget cut the retry short
    print("ok test_download_retry_budget_bounds_a_dead_archive")


if __name__ == "__main__":
    test_strict_fatal_rules()
    test_valid_csv_schema_gate()
    test_download_clamps_to_source_last_year()
    test_download_success_path_never_sleeps()
    test_download_recovers_transient_failure()
    test_download_retry_is_bounded_by_rounds()
    test_download_retry_budget_bounds_a_dead_archive()
    print("\nALL PASSED")
