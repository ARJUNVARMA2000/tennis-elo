"""Strict, network-free checks for the Tennis Abstract forecast snapshotter."""

from __future__ import annotations

import json
import urllib.error
from datetime import UTC, datetime

import pytest
import tennis_model.eval.tennis_abstract as ta

ATP = ta.source_for("atp")
WTA = ta.source_for("wta")


def _header(rounds):
    return "<tr><td>Player</td><td>&nbsp;</td>" + "".join(
        f"<td align=right>&nbsp;&nbsp;{round_name}</td>" for round_name in rounds
    ) + "</tr>"


def _row(source, name, country, probabilities, prefix="", absolute=False):
    player_id = name.replace(" ", "")
    href = f"/cgi-bin/{source.player_script}?p={player_id}"
    if absolute:
        href = f"https://www.tennisabstract.com{href}"
    return (
        f"<tr><td>{prefix}<a href='{href}'>{name}</a> ({country})</td>"
        "<td align=right>&nbsp;&nbsp;&nbsp;</td>"
        + "".join(f"<td align=right>&nbsp;&nbsp;{value}%</td>" for value in probabilities)
        + "</tr>"
    )


def _fixture(source, rounds, rows, repeat_every=None):
    body = [_header(rounds)]
    for index, row in enumerate(rows, start=1):
        body.append(row)
        if repeat_every and index < len(rows) and index % repeat_every == 0:
            body.append("<tr><td></td><td>&nbsp;</td></tr>")
            body.append(_header(rounds))
    # Navigation/profile links outside forecast rows must never be mistaken for players.
    other_script = "wplayer.cgi" if source.tour == "atp" else "player.cgi"
    return (
        "<html><body><table><tr><td>Players</td>"
        f"<td><a href='/cgi-bin/{source.player_script}?p=MenuPlayer'>Menu Player</a></td>"
        f"<td><a href='/cgi-bin/{other_script}?p=WrongTour'>Wrong Tour</a></td>"
        "</tr></table><table cellpadding=2 cellspacing=0>"
        + "".join(body)
        + "</table></body></html>"
    )


def _reduced_html(source=ATP):
    rows = [
        _row(source, "Alpha One", "USA", ("60.0", "35.0"), "(1)", absolute=True),
        _row(source, "Beta Two", "FRA", ("40.0", "15.0"), "(Q)"),
        _row(source, "Gamma Three", "GBR", ("25.0", "10.0"), "(WC)"),
        _row(source, "Delta Four", "ESP", ("75.0", "40.0"), "(LL)"),
    ]
    return _fixture(source, ("F", "W"), rows, repeat_every=2)


def _full_128_html():
    rounds = ("R64", "R32", "R16", "QF", "SF", "F", "W")
    values = ("50.0", "25.0", "12.5", "6.2", "3.1", "1.6", "0.8")
    rows = []
    for position in range(1, 129):
        prefix = f"({position})" if position <= 32 else "(Q)" if position == 33 else ""
        rows.append(_row(ATP, f"Player {position:03d}", "USA", values, prefix))
    return _fixture(ATP, rounds, rows, repeat_every=8)


class _Response:
    def __init__(self, body=b"", status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status

    def read(self, size=-1):
        return self.body[:size]


def _time(hour=0):
    return datetime(2026, 8, 31, hour, 55, 47, 502000, tzinfo=UTC)


def test_configured_sources_are_keyed_by_tour_and_stable_espn_id():
    assert set(ta.SOURCES) == {("atp", "189-2026"), ("wta", "189-2026")}
    assert ATP.url.endswith("2026USOpenMenForecast.html")
    assert WTA.url.endswith("2026USOpenWomenForecast.html")
    assert ATP.player_script == "player.cgi"
    assert WTA.player_script == "wplayer.cgi"
    with pytest.raises(KeyError, match="no Tennis Abstract source"):
        ta.source_for("atp", "not-an-event")


def test_parse_preserves_metadata_and_one_based_draw_order():
    snapshot = ta.parse_forecast_html(_reduced_html(), ATP, captured_at=_time())

    assert snapshot["rounds"] == ["F", "W"]
    assert snapshot["source"] == {
        "provider": "Tennis Abstract",
        "url": ATP.url,
        "capturedAt": "2026-08-31T00:55:47.502000Z",
    }
    assert [player["drawPosition"] for player in snapshot["players"]] == [1, 2, 3, 4]
    assert snapshot["players"][0] == {
        "drawPosition": 1,
        "name": "Alpha One",
        "href": "https://www.tennisabstract.com/cgi-bin/player.cgi?p=AlphaOne",
        "country": "USA",
        "seed": 1,
        "entry": None,
        "probabilities": {"F": 0.6, "W": 0.35},
    }
    assert [player["entry"] for player in snapshot["players"]] == [None, "Q", "WC", "LL"]


def test_parse_supports_wta_and_later_winner_only_table():
    html = _fixture(WTA, ("W",), [
        _row(WTA, "Winner Maybe", "POL", ("55.0",), "(3)"),
        _row(WTA, "Other Player", "CZE", ("45.0",), "(WC)"),
    ])
    snapshot = ta.parse_forecast_html(html, WTA)

    assert snapshot["rounds"] == ["W"]
    assert len(snapshot["players"]) == 2
    assert snapshot["players"][0]["href"].endswith("wplayer.cgi?p=WinnerMaybe")
    assert snapshot["players"][1]["entry"] == "WC"


def test_parse_accepts_current_128_by_7_rounded_table():
    snapshot = ta.parse_forecast_html(_full_128_html(), ATP)

    assert snapshot["rounds"] == ["R64", "R32", "R16", "QF", "SF", "F", "W"]
    assert len(snapshot["players"]) == 128
    assert snapshot["players"][32]["entry"] == "Q"
    assert snapshot["players"][-1]["drawPosition"] == 128


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("35.0%", "100.1%", "outside \\[0, 1\\]"),
        ("35.0%", "65.0%", "reach probability increases"),
        ("35.0%", "30.0%", "W probability mass"),
    ],
)
def test_validation_rejects_bounds_monotonicity_and_column_mass(old, new, message):
    html = _reduced_html().replace(old, new, 1)
    with pytest.raises(ta.ForecastParseError, match=message):
        ta.parse_forecast_html(html, ATP)


def test_validation_rejects_bad_adjacent_pair_even_when_column_total_is_right():
    html = _reduced_html()
    html = html.replace("60.0%", "50.0%", 1).replace("25.0%", "50.0%", 1)
    html = html.replace("75.0%", "60.0%", 1)
    # F masses remain 2.0 overall, but the adjacent pairs are 0.9 and 1.1.
    with pytest.raises(ta.ForecastParseError, match="adjacent pair 1/2 mass"):
        ta.parse_forecast_html(html, ATP)


def test_validation_rejects_duplicates_and_inconsistent_headers():
    duplicate = _reduced_html().replace("Beta Two", "Alpha One").replace(
        "p=BetaTwo", "p=AlphaOne"
    )
    with pytest.raises(ta.ForecastParseError, match="duplicate player name"):
        ta.parse_forecast_html(duplicate, ATP)

    inconsistent = _reduced_html().replace(_header(("F", "W")), _header(("W",)), 1)
    with pytest.raises(ta.ForecastParseError, match="inconsistent round headers"):
        ta.parse_forecast_html(inconsistent, ATP)


def test_validation_rejects_missing_probability_and_wrong_tour_anchors():
    missing = _reduced_html().replace("35.0%", "n/a", 1)
    with pytest.raises(ta.ForecastParseError, match="1 probabilities for 2 rounds"):
        ta.parse_forecast_html(missing, ATP)

    wrong_tour = _reduced_html().replace("player.cgi", "wplayer.cgi")
    with pytest.raises(ta.ForecastParseError, match="has 0 players"):
        ta.parse_forecast_html(wrong_tour, ATP)


def test_normalized_hash_is_deterministic_and_ignores_capture_time():
    first = ta.parse_forecast_html(_reduced_html(), ATP, captured_at=_time(0))
    second = ta.parse_forecast_html(_reduced_html(), ATP, captured_at=_time(1))
    assert first["source"]["capturedAt"] != second["source"]["capturedAt"]
    assert ta.normalized_sha256(first) == ta.normalized_sha256(second)

    second["players"][0]["probabilities"] = {"W": 0.36, "F": 0.61}
    second["players"][1]["probabilities"] = {"W": 0.14, "F": 0.39}
    ta.validate_forecast(second, ATP)
    assert ta.normalized_sha256(first) != ta.normalized_sha256(second)


def test_fetch_sets_identifying_conditionals_and_returns_body():
    seen = {}

    def opener(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return _Response(
            b"<html>ok</html>",
            headers={"ETag": '"forecast-2"', "Last-Modified": "Sun, 30 Aug 2026 23:00:00 GMT"},
        )

    result = ta.fetch_forecast(
        ATP,
        etag='"forecast-1"',
        last_modified="Sun, 30 Aug 2026 22:00:00 GMT",
        timeout=7,
        opener=opener,
        clock=lambda: _time(),
    )

    request = seen["request"]
    assert result.status == "ok" and result.body == b"<html>ok</html>"
    assert result.etag == '"forecast-2"'
    assert seen["timeout"] == 7
    assert request.get_header("User-agent") == ta.USER_AGENT
    assert request.get_header("If-none-match") == '"forecast-1"'
    assert request.get_header("If-modified-since") == "Sun, 30 Aug 2026 22:00:00 GMT"


def test_fetch_returns_soft_304_and_transport_error():
    def not_modified(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            304,
            "Not Modified",
            {"ETag": '"same"'},
            None,
        )

    result = ta.fetch_forecast(
        ATP, etag='"old"', opener=not_modified, clock=lambda: _time()
    )
    assert result.status == "not_modified"
    assert result.http_status == 304 and result.etag == '"same"'

    def unavailable(request, timeout):
        raise urllib.error.URLError("temporary DNS failure")

    result = ta.fetch_forecast(
        ATP, etag='"old"', opener=unavailable, clock=lambda: _time()
    )
    assert result.status == "error"
    assert "temporary DNS failure" in result.error
    assert result.etag == '"old"'


def test_store_is_immutable_idempotent_and_tracks_only_changes(tmp_path):
    html = _reduced_html()
    first_snapshot = ta.parse_forecast_html(html, ATP, captured_at=_time(0))
    first = ta.store_snapshot(
        tmp_path,
        ATP,
        first_snapshot,
        html.encode(),
        etag='"one"',
        last_modified="first",
    )
    first_raw = first.raw_path.read_bytes()
    first_receipt = first.receipt_path.read_bytes()
    first_latest = first.latest_path.read_bytes()

    same_snapshot = ta.parse_forecast_html(html, ATP, captured_at=_time(1))
    same = ta.store_snapshot(
        tmp_path,
        ATP,
        same_snapshot,
        html.encode() + b"\n",
        etag='"same-content-new-http"',
    )
    assert same.status == "unchanged"
    assert same.snapshot_dir == first.snapshot_dir
    assert same.captured_at == first.captured_at
    assert first.raw_path.read_bytes() == first_raw
    assert first.receipt_path.read_bytes() == first_receipt
    assert first.latest_path.read_bytes() == first_latest
    assert len(list((tmp_path / "atp" / ATP.espn_id / "snapshots").iterdir())) == 1

    changed_html = html.replace("60.0%", "61.0%", 1).replace("40.0%", "39.0%", 1)
    changed_html = changed_html.replace("35.0%", "36.0%", 1).replace("15.0%", "14.0%", 1)
    changed_snapshot = ta.parse_forecast_html(changed_html, ATP, captured_at=_time(2))
    changed = ta.store_snapshot(tmp_path, ATP, changed_snapshot, changed_html.encode())
    assert changed.status == "written"
    assert changed.normalized_sha256 != first.normalized_sha256
    assert changed.snapshot_dir != first.snapshot_dir
    assert len(list((tmp_path / "atp" / ATP.espn_id / "snapshots").iterdir())) == 2
    latest = ta.load_latest(tmp_path, ATP)
    assert latest["normalizedSha256"] == changed.normalized_sha256
    assert json.loads(changed.normalized_path.read_text())["source"]["capturedAt"] == (
        "2026-08-31T02:55:47.502000Z"
    )

    # A later reversion is a new observation because its hash differs from latest,
    # even though the same forecast content existed earlier in the history.
    reverted_snapshot = ta.parse_forecast_html(html, ATP, captured_at=_time(3))
    reverted = ta.store_snapshot(tmp_path, ATP, reverted_snapshot, html.encode())
    assert reverted.status == "written"
    assert reverted.normalized_sha256 == first.normalized_sha256
    assert reverted.snapshot_dir not in {first.snapshot_dir, changed.snapshot_dir}


def test_store_detects_corruption_instead_of_overwriting(tmp_path):
    html = _reduced_html()
    snapshot = ta.parse_forecast_html(html, ATP, captured_at=_time())
    written = ta.store_snapshot(tmp_path, ATP, snapshot, html.encode())
    written.normalized_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ta.SnapshotCollisionError, match="invalid immutable normalized"):
        ta.store_snapshot(tmp_path, ATP, snapshot, html.encode())
    assert written.normalized_path.read_text(encoding="utf-8") == "{}\n"


def test_refresh_retains_last_good_on_304_network_and_parse_failures(tmp_path):
    html = _reduced_html().encode()
    requests = []

    def first_opener(request, timeout):
        requests.append(request)
        return _Response(
            html,
            headers={"ETag": '"good"', "Last-Modified": "Sun, 30 Aug 2026 23:00:00 GMT"},
        )

    first = ta.refresh_snapshot(tmp_path, ATP, opener=first_opener, clock=lambda: _time())
    assert first.status == "written"
    latest_path = tmp_path / "atp" / ATP.espn_id / "latest.json"
    latest_bytes = latest_path.read_bytes()

    def not_modified(request, timeout):
        requests.append(request)
        raise urllib.error.HTTPError(request.full_url, 304, "same", {}, None)

    unchanged = ta.refresh_snapshot(
        tmp_path, ATP, opener=not_modified, clock=lambda: _time(1)
    )
    assert unchanged.status == "not_modified"
    assert requests[-1].get_header("If-none-match") == '"good"'
    assert requests[-1].get_header("If-modified-since") == (
        "Sun, 30 Aug 2026 23:00:00 GMT"
    )
    assert latest_path.read_bytes() == latest_bytes

    def network_error(request, timeout):
        raise urllib.error.URLError("offline")

    failed = ta.refresh_snapshot(
        tmp_path, ATP, opener=network_error, clock=lambda: _time(2)
    )
    assert failed.status == "error" and "offline" in failed.error
    assert failed.latest["normalizedSha256"] == first.write.normalized_sha256
    assert latest_path.read_bytes() == latest_bytes

    def invalid_page(request, timeout):
        return _Response(b"<html>challenge page</html>", headers={"ETag": '"bad"'})

    invalid = ta.refresh_snapshot(
        tmp_path, ATP, opener=invalid_page, clock=lambda: _time(3)
    )
    assert invalid.status == "error" and "invalid forecast page" in invalid.error
    assert latest_path.read_bytes() == latest_bytes


def test_refresh_rejects_304_without_a_last_good_snapshot(tmp_path):
    def not_modified(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 304, "same", {}, None)

    result = ta.refresh_snapshot(
        tmp_path, ATP, opener=not_modified, clock=lambda: _time()
    )
    assert result.status == "error"
    assert result.latest is None
    assert result.error == "received HTTP 304 without a last-good snapshot"
