"""Unit checks for the download layer's pure logic — no network.

Runnable directly (`python tests/test_download.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.charting as charting
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
        "charting": ["charting-m-stats-Overview.csv"],
    }
    out = dl.strict_fatal(fails, this_year=2026)
    assert "wta/historical:2026" in out
    assert "wta/historical:2019" not in out          # archive year: snapshot covers it
    assert "atp/fresh:2026" in out
    assert "atp/stats:2018.csv" in out               # stats overlay: always fatal
    assert any(s.startswith("wta/stats:") for s in out)
    assert "charting:charting-m-stats-Overview.csv" in out
    assert dl.strict_fatal({}, 2026) == []
    print("ok test_strict_fatal_rules")


def test_charting_download_validates_falls_back_and_reports_failures(monkeypatch, tmp_path):
    """A 200-with-garbage must fall through to GitHub, while an exhausted file is named
    for the daily source-download alert and cannot clobber its last good copy."""
    good = (b"match_id,player,set,serve_pts\n"
            + b"20260521-M-Test-R1-A-B,A,Total,50\n" * 4)
    garbage = b"<html><body>upstream error page</body></html>" * 4
    monkeypatch.setattr(charting, "CHARTING_DIR", tmp_path)
    monkeypatch.setattr(charting, "_CHARTING_FILES", ["stats-Overview"])
    monkeypatch.setattr(charting, "_via_https", lambda filename: garbage)
    monkeypatch.setattr(
        charting, "_via_gh",
        lambda filename: good if filename.startswith("charting-m-") else garbage,
    )
    old = tmp_path / "charting-w-stats-Overview.csv"
    old.write_bytes(b"last-good")

    done, failed = charting.download_charting()

    assert done == ["charting-m-stats-Overview.csv"]
    assert failed == ["charting-w-stats-Overview.csv"]
    assert (tmp_path / done[0]).read_bytes() == good
    assert old.read_bytes() == b"last-good"
    print("ok test_charting_download_validates_falls_back_and_reports_failures")


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


_LFS_POINTER = (b"version https://git-lfs.github.com/spec/v1\n"
                b"oid sha256:99852ba35fbfa59b19888984ab7682f940cf50e75a49ffe1ecf6f8295f40ddd8\n"
                b"size 164611\n")
_REAL_CSV = b"tourney_date,winner_name,loser_name,score\n20260104,A,B,6-1 6-1\n" * 5


def test_lfs_pointer_is_recognised_and_not_mistaken_for_data():
    """The 131-byte pointer is truthy and >100 bytes, so only an explicit check catches it."""
    assert dl._is_lfs_pointer(_LFS_POINTER)
    assert dl._is_lfs_pointer(b"\n  " + _LFS_POINTER)          # leading whitespace
    assert not dl._is_lfs_pointer(_REAL_CSV)
    assert not dl._is_lfs_pointer(b"")
    assert not dl._is_lfs_pointer(None)
    assert not dl._valid_csv(_LFS_POINTER, dl._REQUIRED_BASE)  # and it never passes as a CSV
    print("ok test_lfs_pointer_is_recognised_and_not_mistaken_for_data")


def test_lfs_media_url_derives_from_the_raw_url():
    raw = "https://raw.githubusercontent.com/Owner/Repo/main/tennis_atp/atp_matches_2026.csv"
    assert dl._lfs_media_url(raw) == (
        "https://media.githubusercontent.com/media/Owner/Repo/main/tennis_atp/atp_matches_2026.csv")
    assert dl._lfs_media_url("https://stats.tennismylife.org/2026.csv") is None
    print("ok test_lfs_media_url_derives_from_the_raw_url")


def _stub_transports(fetched: list, responses: dict, gh: bytes | None = None):
    """Patch download.py's two transports; record every URL/repo actually hit."""
    def https(url, retries=1):
        fetched.append(url)
        return responses.get(url)

    def via_gh(repo, path):
        fetched.append(f"gh:{repo}/{path}")
        return gh

    return https, via_gh


def _run_download_year(responses, gh=None, kind="fresh"):
    fetched: list[str] = []
    https, via_gh = _stub_transports(fetched, responses, gh)
    orig = dl._via_https, dl._via_gh, dl._atomic_write
    written: list = []
    try:
        dl._via_https, dl._via_gh = https, via_gh
        dl._atomic_write = lambda path, data: written.append((path, data))
        ok = dl.download_year("atp", kind, 2026)
    finally:
        dl._via_https, dl._via_gh, dl._atomic_write = orig
    return ok, fetched, written


def test_download_year_resolves_an_lfs_pointer_via_the_media_endpoint():
    """The regression that broke every daily retrain from 2026-07-20: raw.githubusercontent
    answers 200 with an LFS pointer, so the file must be re-fetched from the media host."""
    raw = dl.FRESH_SOURCE["atp"]["raw"].format(year=2026)
    media = dl._lfs_media_url(raw)
    ok, fetched, written = _run_download_year({raw: _LFS_POINTER, media: _REAL_CSV})
    assert ok, "an LFS-backed source must still download"
    assert fetched == [raw, media]           # media tried, and gh never needed
    assert written and written[0][1] == _REAL_CSV
    print("ok test_download_year_resolves_an_lfs_pointer_via_the_media_endpoint")


def test_download_year_falls_through_a_200_with_garbage_to_the_gh_transport():
    """A transport answering 200 with the WRONG BYTES must not end the chain — the old
    `_via_https(...) or _via_gh(...)` only fell through on a None, so an HTML error page
    (or a pointer) silently skipped the authenticated fallback."""
    raw = dl.FRESH_SOURCE["atp"]["raw"].format(year=2026)
    html = b"<html><body>502 Bad Gateway, padded well past the size floor ....</body></html>" * 3
    ok, fetched, written = _run_download_year({raw: html}, gh=_REAL_CSV)
    assert ok
    assert any(u.startswith("gh:") for u in fetched), fetched
    assert written and written[0][1] == _REAL_CSV
    print("ok test_download_year_falls_through_a_200_with_garbage_to_the_gh_transport")


def test_download_year_reports_failure_when_every_transport_is_bad():
    """`failed` must stay truthful for the strict gate — no transport may fake a success."""
    raw = dl.FRESH_SOURCE["atp"]["raw"].format(year=2026)
    media = dl._lfs_media_url(raw)
    ok, fetched, written = _run_download_year({raw: _LFS_POINTER, media: _LFS_POINTER}, gh=None)
    assert not ok and written == []          # nothing clobbered the good on-disk file
    assert any(u.startswith("gh:") for u in fetched), fetched
    print("ok test_download_year_reports_failure_when_every_transport_is_bad")


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
    # pytest supplies monkeypatch/tmp_path for the charting downloader regression.
    test_valid_csv_schema_gate()
    test_lfs_pointer_is_recognised_and_not_mistaken_for_data()
    test_lfs_media_url_derives_from_the_raw_url()
    test_download_year_resolves_an_lfs_pointer_via_the_media_endpoint()
    test_download_year_falls_through_a_200_with_garbage_to_the_gh_transport()
    test_download_year_reports_failure_when_every_transport_is_bad()
    test_download_clamps_to_source_last_year()
    test_download_success_path_never_sleeps()
    test_download_recovers_transient_failure()
    test_download_retry_is_bounded_by_rounds()
    test_download_retry_budget_bounds_a_dead_archive()
    print("\nALL PASSED")
