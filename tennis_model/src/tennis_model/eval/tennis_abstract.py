"""Capture Tennis Abstract tournament forecasts as immutable evaluation evidence.

Tennis Abstract publishes static, legacy HTML tables whose contents are replaced as a
tournament advances.  This module is deliberately evaluation-only: it parses and
validates those tables, computes a hash over forecast content (not capture metadata),
and stores a new immutable bundle only when the forecast changes.

The configured URLs are external inputs, never model features.  Network failures,
HTTP 304 responses, and invalid replacement pages leave the last-good bundle intact.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urljoin, urlparse

SNAPSHOT_SCHEMA = "tennis-abstract-forecast-v1"
RECEIPT_SCHEMA = "tennis-abstract-forecast-receipt-v1"
LATEST_SCHEMA = "tennis-abstract-forecast-latest-v1"

PROVIDER = "Tennis Abstract"
USER_AGENT = "DEUCE-Tennis-Forecast-Benchmark/1.0 (evaluation capture)"
MAX_HTML_BYTES = 2_000_000

# Each displayed value is rounded to one decimal percentage point.  The maximum
# error per value is therefore half of 0.1%, expressed on the [0, 1] scale.
PERCENT_ROUNDING_UNIT = 0.001
PERCENT_ROUNDING_HALF = PERCENT_ROUNDING_UNIT / 2

DISPLAY_ROUNDS = ("R64", "R32", "R16", "QF", "SF", "F", "W")
EXPECTED_ROUND_TOTALS = {
    "R64": 64.0,
    "R32": 32.0,
    "R16": 16.0,
    "QF": 8.0,
    "SF": 4.0,
    "F": 2.0,
    "W": 1.0,
}


class ForecastParseError(ValueError):
    """The external page did not satisfy the forecast-table contract."""


class SnapshotError(RuntimeError):
    """A snapshot bundle or last-good pointer is malformed."""


class SnapshotCollisionError(SnapshotError):
    """An immutable snapshot path already contains different bytes."""


@dataclass(frozen=True)
class ForecastSource:
    tour: str
    espn_id: str
    event: str
    season: int
    url: str
    player_script: str


FORECAST_SOURCES: dict[tuple[str, str], ForecastSource] = {
    ("atp", "189-2026"): ForecastSource(
        tour="atp",
        espn_id="189-2026",
        event="US Open",
        season=2026,
        url="https://www.tennisabstract.com/current/2026USOpenMenForecast.html",
        player_script="player.cgi",
    ),
    ("wta", "189-2026"): ForecastSource(
        tour="wta",
        espn_id="189-2026",
        event="US Open",
        season=2026,
        url="https://www.tennisabstract.com/current/2026USOpenWomenForecast.html",
        player_script="wplayer.cgi",
    ),
}
# Short public alias for callers that treat the configuration as a registry.
SOURCES = FORECAST_SOURCES


@dataclass(frozen=True)
class FetchResult:
    status: Literal["ok", "not_modified", "error"]
    url: str
    fetched_at: str
    body: bytes | None = None
    http_status: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class SnapshotWriteResult:
    status: Literal["written", "unchanged"]
    normalized_sha256: str
    captured_at: str
    snapshot_dir: Path
    normalized_path: Path
    raw_path: Path
    receipt_path: Path
    latest_path: Path


@dataclass(frozen=True)
class SnapshotRefreshResult:
    status: Literal["written", "unchanged", "not_modified", "error"]
    fetch: FetchResult
    write: SnapshotWriteResult | None
    latest: dict | None
    error: str | None = None


@dataclass
class _Anchor:
    href: str
    text: list[str]


@dataclass
class _Cell:
    text: list[str]
    anchors: list[_Anchor]


@dataclass
class _Row:
    cells: list[_Cell]


def source_for(tour: str, espn_id: str = "189-2026") -> ForecastSource:
    """Return one explicitly configured evaluation source."""
    try:
        return FORECAST_SOURCES[(tour.lower(), str(espn_id))]
    except KeyError as exc:
        raise KeyError(f"no Tennis Abstract source for {tour!r} / {espn_id!r}") from exc


def _clean_text(parts: list[str] | str) -> str:
    text = "".join(parts) if isinstance(parts, list) else parts
    return " ".join(text.replace("\xa0", " ").split())


class _ForecastTableParser(HTMLParser):
    """Collect legacy table rows while ignoring the page's nested navigation tables."""

    def __init__(self, source: ForecastSource):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.rows: list[tuple[list[str], _Anchor, list[str]]] = []
        self.errors: list[str] = []
        self._row_stack: list[_Row] = []
        self._cell_stack: list[tuple[_Row, _Cell]] = []
        self._anchor_stack: list[_Anchor] = []
        self._rounds: tuple[str, ...] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row_stack.append(_Row(cells=[]))
        elif tag in {"td", "th"} and self._row_stack:
            row = self._row_stack[-1]
            cell = _Cell(text=[], anchors=[])
            row.cells.append(cell)
            self._cell_stack.append((row, cell))
        elif tag == "a" and self._cell_stack:
            href = dict(attrs).get("href") or ""
            anchor = _Anchor(href=href.strip(), text=[])
            self._cell_stack[-1][1].anchors.append(anchor)
            self._anchor_stack.append(anchor)
        elif tag == "br" and self._cell_stack:
            self._cell_stack[-1][1].text.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._anchor_stack:
            self._anchor_stack.pop()
        elif tag in {"td", "th"} and self._cell_stack:
            self._cell_stack.pop()
        elif tag == "tr" and self._row_stack:
            self._process_row(self._row_stack.pop())

    def handle_data(self, data: str) -> None:
        if self._cell_stack:
            self._cell_stack[-1][1].text.append(data)
        if self._anchor_stack:
            self._anchor_stack[-1].text.append(data)

    def _process_row(self, row: _Row) -> None:
        cells = [_clean_text(cell.text) for cell in row.cells]
        header_rounds = tuple(cell for cell in cells if cell in DISPLAY_ROUNDS)
        if any(cell.casefold() == "player" for cell in cells) and header_rounds:
            if header_rounds not in tuple(
                DISPLAY_ROUNDS[start:] for start in range(len(DISPLAY_ROUNDS))
            ):
                self.errors.append(f"non-contiguous round header {header_rounds!r}")
            elif self._rounds is not None and header_rounds != self._rounds:
                self.errors.append(
                    f"inconsistent round headers {self._rounds!r} and {header_rounds!r}"
                )
            else:
                self._rounds = header_rounds

        anchors = [anchor for cell in row.cells for anchor in cell.anchors if _is_player_href(
            anchor.href, self.source
        )]
        probability_cells = [cell for cell in cells if _PERCENT_RE.fullmatch(cell)]
        if not probability_cells:
            return
        if len(anchors) != 1:
            # The outer page-layout row contains the entire nested forecast table.  Only
            # direct player rows have one player-profile anchor and probability cells.
            return
        if self._rounds is None:
            self.errors.append(f"player row {_clean_text(anchors[0].text)!r} precedes a header")
            return
        self.rows.append((cells, anchors[0], probability_cells))


_PERCENT_RE = re.compile(r"(?:0|[1-9]\d*)(?:\.\d+)?%")
_COUNTRY_RE = re.compile(r"\(([A-Z]{3})\)\s*$")
_PREFIX_TOKEN_RE = re.compile(r"\(([^()]*)\)")


def _source_host(url: str) -> str:
    return (urlparse(url).hostname or "").removeprefix("www.").lower()


def _is_player_href(href: str, source: ForecastSource) -> bool:
    if not href:
        return False
    absolute = urljoin(source.url, href)
    parsed = urlparse(absolute)
    if parsed.scheme != "https" or _source_host(absolute) != _source_host(source.url):
        return False
    if parsed.path != f"/cgi-bin/{source.player_script}" or parsed.fragment:
        return False
    player_ids = parse_qs(parsed.query, keep_blank_values=True).get("p", [])
    return len(player_ids) == 1 and bool(player_ids[0].strip())


def _capture_iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid capture timestamp {value!r}") from exc
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise TypeError("capture timestamp must be a datetime, ISO string, or None")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("capture timestamp must be timezone-aware")
    return parsed.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _player_metadata(cells: list[str], anchor: _Anchor, source: ForecastSource) -> dict:
    name = _clean_text(anchor.text)
    if not name:
        raise ForecastParseError("player anchor has no name")
    player_cell = next((cell for cell in cells if name in cell), "")
    country_match = _COUNTRY_RE.search(player_cell)
    if country_match is None:
        raise ForecastParseError(f"{name}: missing trailing three-letter country")

    name_at = player_cell.find(name)
    prefix = player_cell[:name_at] if name_at >= 0 else ""
    seed: int | None = None
    entries: list[str] = []
    for token in _PREFIX_TOKEN_RE.findall(prefix):
        token = token.strip()
        if token.isdigit():
            if seed is not None:
                raise ForecastParseError(f"{name}: multiple seed tokens")
            seed = int(token)
            if seed <= 0:
                raise ForecastParseError(f"{name}: invalid seed {seed}")
        elif token:
            entries.append(token.upper())

    href = urljoin(source.url, anchor.href)
    return {
        "name": name,
        "href": href,
        "country": country_match.group(1),
        "seed": seed,
        "entry": "/".join(entries) if entries else None,
    }


def parse_forecast_html(
    html: str | bytes,
    source: ForecastSource,
    *,
    captured_at: datetime | str | None = None,
) -> dict:
    """Parse and validate one static Tennis Abstract draw-forecast page.

    Player rows are selected structurally: exactly one tour-appropriate profile anchor
    plus percentage-only cells beneath a recognized round header.  ``drawPosition`` is
    the one-based document order after header and spacer rows are removed.
    """
    if isinstance(html, bytes):
        try:
            text = html.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ForecastParseError("forecast page is not valid UTF-8") from exc
    elif isinstance(html, str):
        text = html
    else:
        raise TypeError("html must be str or bytes")

    parser = _ForecastTableParser(source)
    parser.feed(text)
    parser.close()
    if parser.errors:
        raise ForecastParseError("; ".join(parser.errors))
    if parser._rounds is None:
        raise ForecastParseError("no recognized forecast round header")

    players = []
    for position, (cells, anchor, raw_probabilities) in enumerate(parser.rows, start=1):
        if len(raw_probabilities) != len(parser._rounds):
            name = _clean_text(anchor.text) or "unknown player"
            raise ForecastParseError(
                f"{name}: {len(raw_probabilities)} probabilities for "
                f"{len(parser._rounds)} rounds"
            )
        metadata = _player_metadata(cells, anchor, source)
        probabilities = {
            round_name: float(Decimal(value.removesuffix("%")) / Decimal(100))
            for round_name, value in zip(parser._rounds, raw_probabilities, strict=True)
        }
        players.append({
            "drawPosition": position,
            **metadata,
            "probabilities": probabilities,
        })

    source_payload = {"provider": PROVIDER, "url": source.url}
    capture = _capture_iso(captured_at)
    if capture is not None:
        source_payload["capturedAt"] = capture
    snapshot = {
        "schema": SNAPSHOT_SCHEMA,
        "event": source.event,
        "season": source.season,
        "tour": source.tour,
        "espnId": source.espn_id,
        "source": source_payload,
        "rounds": list(parser._rounds),
        "players": players,
    }
    validate_forecast(snapshot, source)
    return snapshot


def validate_forecast(snapshot: dict, source: ForecastSource) -> None:
    """Fail closed on identity, draw geometry, probability, and rounding invariants."""
    if not isinstance(snapshot, dict):
        raise ForecastParseError("snapshot must be an object")
    snapshot_fields = {
        "schema", "event", "season", "tour", "espnId", "source", "rounds", "players"
    }
    if set(snapshot) != snapshot_fields:
        raise ForecastParseError("snapshot fields do not match the normalized schema")
    identity = (
        snapshot.get("schema"),
        snapshot.get("event"),
        snapshot.get("season"),
        snapshot.get("tour"),
        snapshot.get("espnId"),
    )
    expected_identity = (
        SNAPSHOT_SCHEMA,
        source.event,
        source.season,
        source.tour,
        source.espn_id,
    )
    if identity != expected_identity:
        raise ForecastParseError(
            f"snapshot identity {identity!r} does not match source {expected_identity!r}"
        )

    source_payload = snapshot.get("source")
    if not isinstance(source_payload, dict):
        raise ForecastParseError("source metadata must be an object")
    if set(source_payload) not in (
        {"provider", "url"},
        {"provider", "url", "capturedAt"},
    ):
        raise ForecastParseError("source fields do not match the normalized schema")
    if source_payload.get("provider") != PROVIDER or source_payload.get("url") != source.url:
        raise ForecastParseError("source provider or URL does not match configuration")
    if "capturedAt" in source_payload:
        try:
            _capture_iso(source_payload["capturedAt"])
        except (TypeError, ValueError) as exc:
            raise ForecastParseError(str(exc)) from exc

    rounds = snapshot.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        raise ForecastParseError("rounds must be a non-empty list")
    round_tuple = tuple(rounds)
    if round_tuple not in tuple(
        DISPLAY_ROUNDS[start:] for start in range(len(DISPLAY_ROUNDS))
    ):
        raise ForecastParseError(f"rounds must be a contiguous suffix of {DISPLAY_ROUNDS!r}")

    players = snapshot.get("players")
    if not isinstance(players, list):
        raise ForecastParseError("players must be a list")
    expected_players = int(EXPECTED_ROUND_TOTALS[rounds[0]] * 2)
    if len(players) != expected_players:
        raise ForecastParseError(
            f"{rounds[0]} table has {len(players)} players; expected {expected_players}"
        )

    names: set[str] = set()
    hrefs: set[str] = set()
    for expected_position, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            raise ForecastParseError(f"player {expected_position} is not an object")
        if set(player) != {
            "drawPosition", "name", "href", "country", "seed", "entry", "probabilities"
        }:
            raise ForecastParseError(
                f"player {expected_position} fields do not match the normalized schema"
            )
        if player.get("drawPosition") != expected_position:
            raise ForecastParseError(
                f"draw positions must be consecutive and one-based (expected {expected_position})"
            )
        name = player.get("name")
        href = player.get("href")
        country = player.get("country")
        if not isinstance(name, str) or not name.strip():
            raise ForecastParseError(f"player {expected_position} has no name")
        if not isinstance(href, str) or not _is_player_href(href, source):
            raise ForecastParseError(f"{name}: invalid player profile href")
        if not isinstance(country, str) or _COUNTRY_RE.fullmatch(f"({country})") is None:
            raise ForecastParseError(f"{name}: invalid country {country!r}")
        seed = player.get("seed")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int) or seed <= 0):
            raise ForecastParseError(f"{name}: invalid seed {seed!r}")
        entry = player.get("entry")
        if entry is not None and (not isinstance(entry, str) or not entry.strip()):
            raise ForecastParseError(f"{name}: invalid entry {entry!r}")

        name_key = _clean_text(name).casefold()
        href_key = href.casefold()
        if name_key in names:
            raise ForecastParseError(f"duplicate player name {name!r}")
        if href_key in hrefs:
            raise ForecastParseError(f"duplicate player href {href!r}")
        names.add(name_key)
        hrefs.add(href_key)

        probabilities = player.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != set(rounds):
            raise ForecastParseError(f"{name}: probability rounds do not match header")
        previous = math.inf
        for round_name in rounds:
            probability = probabilities[round_name]
            if (
                isinstance(probability, bool)
                or not isinstance(probability, (int, float))
                or not math.isfinite(probability)
                or not 0 <= probability <= 1
            ):
                raise ForecastParseError(
                    f"{name} {round_name}: probability {probability!r} is outside [0, 1]"
                )
            if probability > previous:
                raise ForecastParseError(
                    f"{name}: reach probability increases from {previous} to "
                    f"{probability} at {round_name}"
                )
            previous = probability

    tolerance = len(players) * PERCENT_ROUNDING_HALF + 1e-12
    for round_name in rounds:
        actual = math.fsum(player["probabilities"][round_name] for player in players)
        expected = EXPECTED_ROUND_TOTALS[round_name]
        if abs(actual - expected) > tolerance:
            raise ForecastParseError(
                f"{round_name} probability mass is {actual:.6f}; expected {expected:.1f} "
                f"within rounded-table tolerance {tolerance:.6f}"
            )

    first_round = rounds[0]
    pair_tolerance = PERCENT_ROUNDING_UNIT + 1e-12
    for offset in range(0, len(players), 2):
        pair_mass = math.fsum(
            players[index]["probabilities"][first_round]
            for index in (offset, offset + 1)
        )
        if abs(pair_mass - 1.0) > pair_tolerance:
            raise ForecastParseError(
                f"{first_round} adjacent pair {offset + 1}/{offset + 2} mass is "
                f"{pair_mass:.6f}; expected 1 within {pair_tolerance:.3f}"
            )


def _content_payload(snapshot: dict) -> dict:
    """Return the stable forecast projection; capture/transport metadata is excluded."""
    source_payload = snapshot["source"]
    return {
        "schema": snapshot["schema"],
        "event": snapshot["event"],
        "season": snapshot["season"],
        "tour": snapshot["tour"],
        "espnId": snapshot["espnId"],
        "source": {
            "provider": source_payload["provider"],
            "url": source_payload["url"],
        },
        "rounds": snapshot["rounds"],
        "players": snapshot["players"],
    }


def _json_bytes(payload: dict) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def normalized_sha256(snapshot: dict) -> str:
    """Hash deterministic normalized forecast content, excluding capture time."""
    return hashlib.sha256(_json_bytes(_content_payload(snapshot))).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def fetch_forecast(
    source: ForecastSource,
    *,
    etag: str | None = None,
    last_modified: str | None = None,
    timeout: float = 30,
    opener: Callable = urllib.request.urlopen,
    clock: Callable[[], datetime] = _utc_now,
) -> FetchResult:
    """Conditionally fetch a page; all transport failures become explicit soft results."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    request = urllib.request.Request(source.url, headers=headers)

    def observed_at() -> str:
        value = _capture_iso(clock())
        assert value is not None
        return value

    try:
        with opener(request, timeout=timeout) as response:
            status = response.getcode()
            response_etag = response.headers.get("ETag") or etag
            response_modified = response.headers.get("Last-Modified") or last_modified
            if status == 304:
                return FetchResult(
                    status="not_modified",
                    url=source.url,
                    fetched_at=observed_at(),
                    http_status=304,
                    etag=response_etag,
                    last_modified=response_modified,
                )
            if status is not None and not 200 <= status < 300:
                return FetchResult(
                    status="error",
                    url=source.url,
                    fetched_at=observed_at(),
                    http_status=status,
                    etag=etag,
                    last_modified=last_modified,
                    error=f"HTTP {status}",
                )
            body = response.read(MAX_HTML_BYTES + 1)
            fetched_at = observed_at()
            if len(body) > MAX_HTML_BYTES:
                return FetchResult(
                    status="error",
                    url=source.url,
                    fetched_at=fetched_at,
                    http_status=status,
                    etag=etag,
                    last_modified=last_modified,
                    error=f"response exceeds {MAX_HTML_BYTES} bytes",
                )
            return FetchResult(
                status="ok",
                url=source.url,
                fetched_at=fetched_at,
                body=body,
                http_status=status,
                etag=response_etag,
                last_modified=response_modified,
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return FetchResult(
                status="not_modified",
                url=source.url,
                fetched_at=observed_at(),
                http_status=304,
                etag=exc.headers.get("ETag") or etag,
                last_modified=exc.headers.get("Last-Modified") or last_modified,
            )
        error = f"HTTP {exc.code}: {exc.reason}"
        http_status = exc.code
    except Exception as exc:  # noqa: BLE001 - best-effort external evaluation source
        error = f"{type(exc).__name__}: {exc}"
        http_status = None
    return FetchResult(
        status="error",
        url=source.url,
        fetched_at=observed_at(),
        http_status=http_status,
        etag=etag,
        last_modified=last_modified,
        error=error,
    )


def _event_root(root: Path | str, source: ForecastSource) -> Path:
    return Path(root) / source.tour / source.espn_id


def _latest_path(root: Path | str, source: ForecastSource) -> Path:
    return _event_root(root, source) / "latest.json"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SnapshotError(f"{path} is not a JSON object")
    return value


def load_latest(root: Path | str, source: ForecastSource) -> dict | None:
    """Load and validate the complete last-good bundle, or ``None`` if absent."""
    path = _latest_path(root, source)
    if not path.exists():
        return None
    latest = _read_json(path)
    required = {
        "schema",
        "tour",
        "espnId",
        "capturedAt",
        "normalizedSha256",
        "snapshotDir",
        "normalizedPath",
        "rawPath",
        "receiptPath",
    }
    if set(latest) - (required | {"etag", "lastModified"}) or not required <= set(latest):
        raise SnapshotError(f"{path} has an invalid latest-pointer shape")
    if (
        latest["schema"] != LATEST_SCHEMA
        or latest["tour"] != source.tour
        or latest["espnId"] != source.espn_id
        or not re.fullmatch(r"[0-9a-f]{64}", str(latest["normalizedSha256"]))
    ):
        raise SnapshotError(f"{path} has invalid identity or digest")
    try:
        _capture_iso(latest["capturedAt"])
    except (TypeError, ValueError) as exc:
        raise SnapshotError(f"{path} has invalid capture time") from exc
    if latest.get("etag") is not None and not isinstance(latest["etag"], str):
        raise SnapshotError(f"{path} has invalid ETag")
    if latest.get("lastModified") is not None and not isinstance(
        latest["lastModified"], str
    ):
        raise SnapshotError(f"{path} has invalid Last-Modified value")

    relative_dir = latest["snapshotDir"]
    expected_paths = _relative_bundle_paths(Path(str(relative_dir)).name)
    if (
        not isinstance(relative_dir, str)
        or tuple(latest[key] for key in ("snapshotDir", "normalizedPath", "rawPath", "receiptPath"))
        != expected_paths
    ):
        raise SnapshotError(f"{path} contains inconsistent bundle paths")
    bundle = _bundle_from_latest(root, source, latest)
    receipt = _validate_bundle(bundle, source, latest["normalizedSha256"])
    if receipt.get("capturedAt") != latest["capturedAt"]:
        raise SnapshotError(f"{path} capture time does not match its receipt")
    return latest


def _relative_bundle_paths(snapshot_id: str) -> tuple[str, str, str, str]:
    snapshot_dir = f"snapshots/{snapshot_id}"
    return (
        snapshot_dir,
        f"{snapshot_dir}/normalized.json",
        f"{snapshot_dir}/raw.html",
        f"{snapshot_dir}/receipt.json",
    )


def _bundle_from_latest(root: Path | str, source: ForecastSource, latest: dict) -> Path:
    event_root = _event_root(root, source)
    expected_prefix = "snapshots/"
    relative = latest["snapshotDir"]
    if (
        not isinstance(relative, str)
        or not relative.startswith(expected_prefix)
        or Path(relative).is_absolute()
        or ".." in Path(relative).parts
    ):
        raise SnapshotError("latest pointer contains an unsafe snapshot path")
    return event_root / relative


def _validate_bundle(
    bundle: Path,
    source: ForecastSource,
    expected_hash: str,
    *,
    expected_snapshot: dict | None = None,
) -> dict:
    normalized_path = bundle / "normalized.json"
    raw_path = bundle / "raw.html"
    receipt_path = bundle / "receipt.json"
    if not bundle.is_dir() or not normalized_path.is_file() or not raw_path.is_file() or not receipt_path.is_file():
        raise SnapshotCollisionError(f"incomplete immutable snapshot bundle {bundle}")
    stored_snapshot = _read_json(normalized_path)
    try:
        validate_forecast(stored_snapshot, source)
    except ForecastParseError as exc:
        raise SnapshotCollisionError(f"invalid immutable normalized snapshot {bundle}: {exc}") from exc
    if normalized_sha256(stored_snapshot) != expected_hash:
        raise SnapshotCollisionError(f"normalized hash collision at {bundle}")
    if expected_snapshot is not None and _json_bytes(stored_snapshot) != _json_bytes(expected_snapshot):
        raise SnapshotCollisionError(f"normalized snapshot bytes differ at {bundle}")

    receipt = _read_json(receipt_path)
    raw = raw_path.read_bytes()
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or receipt.get("tour") != source.tour
        or receipt.get("espnId") != source.espn_id
        or receipt.get("sourceUrl") != source.url
        or receipt.get("normalizedSha256") != expected_hash
        or receipt.get("rawSha256") != hashlib.sha256(raw).hexdigest()
        or receipt.get("rawBytes") != len(raw)
        or receipt.get("capturedAt") != stored_snapshot["source"].get("capturedAt")
    ):
        raise SnapshotCollisionError(f"receipt/raw collision at {bundle}")
    return receipt


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            os.fchmod(handle.fileno(), 0o644)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _cleanup_bundle(directory: Path) -> None:
    for name in ("normalized.json", "raw.html", "receipt.json"):
        path = directory / name
        if path.exists():
            path.unlink()
    if directory.exists():
        directory.rmdir()


def _write_result(
    status: Literal["written", "unchanged"],
    event_root: Path,
    latest: dict,
) -> SnapshotWriteResult:
    bundle = event_root / latest["snapshotDir"]
    return SnapshotWriteResult(
        status=status,
        normalized_sha256=latest["normalizedSha256"],
        captured_at=latest["capturedAt"],
        snapshot_dir=bundle,
        normalized_path=event_root / latest["normalizedPath"],
        raw_path=event_root / latest["rawPath"],
        receipt_path=event_root / latest["receiptPath"],
        latest_path=event_root / "latest.json",
    )


def store_snapshot(
    root: Path | str,
    source: ForecastSource,
    snapshot: dict,
    raw: bytes,
    *,
    captured_at: datetime | str | None = None,
    etag: str | None = None,
    last_modified: str | None = None,
    http_status: int | None = 200,
) -> SnapshotWriteResult:
    """Atomically append one immutable bundle when forecast content changes.

    The mutable ``latest.json`` file is only a pointer to a fully formed bundle.  An
    unchanged fetch does not rewrite either the bundle or pointer, preserving the first
    observation time for that forecast state.
    """
    if not isinstance(raw, bytes):
        raise TypeError("raw forecast receipt must be bytes")
    normalized = json.loads(json.dumps(snapshot, ensure_ascii=False))
    capture = _capture_iso(captured_at or normalized.get("source", {}).get("capturedAt"))
    if capture is None:
        raise ValueError("a capture timestamp is required to store a snapshot")
    if not isinstance(normalized.get("source"), dict):
        raise ForecastParseError("source metadata must be an object")
    normalized["source"]["capturedAt"] = capture
    validate_forecast(normalized, source)
    digest = normalized_sha256(normalized)
    raw_snapshot = parse_forecast_html(raw, source, captured_at=capture)
    if normalized_sha256(raw_snapshot) != digest:
        raise ForecastParseError("raw receipt does not match normalized forecast content")

    event_root = _event_root(root, source)
    latest_path = event_root / "latest.json"
    prior = load_latest(root, source)
    if prior is not None:
        if prior["normalizedSha256"] == digest:
            return _write_result("unchanged", event_root, prior)

    timestamp_slug = capture.replace("-", "").replace(":", "").replace(".", "")
    snapshot_id = f"{timestamp_slug}--{digest}"
    relative_dir, relative_normalized, relative_raw, relative_receipt = (
        _relative_bundle_paths(snapshot_id)
    )
    bundle = event_root / relative_dir
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "provider": PROVIDER,
        "tour": source.tour,
        "espnId": source.espn_id,
        "event": source.event,
        "season": source.season,
        "sourceUrl": source.url,
        "capturedAt": capture,
        "httpStatus": http_status,
        "etag": etag,
        "lastModified": last_modified,
        "normalizedSha256": digest,
        "rawSha256": hashlib.sha256(raw).hexdigest(),
        "rawBytes": len(raw),
    }

    snapshots_dir = event_root / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{snapshot_id}.", dir=snapshots_dir))
    try:
        (temporary / "normalized.json").write_bytes(_json_bytes(normalized))
        (temporary / "raw.html").write_bytes(raw)
        (temporary / "receipt.json").write_bytes(_json_bytes(receipt))
        try:
            os.rename(temporary, bundle)
        except OSError:
            if not bundle.exists():
                raise
            _validate_bundle(bundle, source, digest, expected_snapshot=normalized)
            existing_receipt = _read_json(bundle / "receipt.json")
            if existing_receipt != receipt or (bundle / "raw.html").read_bytes() != raw:
                raise SnapshotCollisionError(
                    f"immutable snapshot collision at {bundle}"
                ) from None
    finally:
        if temporary.exists():
            _cleanup_bundle(temporary)

    _validate_bundle(bundle, source, digest, expected_snapshot=normalized)
    latest = {
        "schema": LATEST_SCHEMA,
        "tour": source.tour,
        "espnId": source.espn_id,
        "capturedAt": capture,
        "normalizedSha256": digest,
        "snapshotDir": relative_dir,
        "normalizedPath": relative_normalized,
        "rawPath": relative_raw,
        "receiptPath": relative_receipt,
        "etag": etag,
        "lastModified": last_modified,
    }
    _atomic_write(latest_path, _json_bytes(latest))
    return _write_result("written", event_root, latest)


def refresh_snapshot(
    root: Path | str,
    source: ForecastSource,
    *,
    timeout: float = 30,
    opener: Callable = urllib.request.urlopen,
    clock: Callable[[], datetime] = _utc_now,
) -> SnapshotRefreshResult:
    """Fetch, parse, and store while retaining the exact last-good state on failure."""
    latest = load_latest(root, source)
    fetched = fetch_forecast(
        source,
        etag=latest.get("etag") if latest else None,
        last_modified=latest.get("lastModified") if latest else None,
        timeout=timeout,
        opener=opener,
        clock=clock,
    )
    if fetched.status == "not_modified":
        if latest is None:
            return SnapshotRefreshResult(
                status="error",
                fetch=fetched,
                write=None,
                latest=None,
                error="received HTTP 304 without a last-good snapshot",
            )
        return SnapshotRefreshResult(
            status="not_modified", fetch=fetched, write=None, latest=latest
        )
    if fetched.status == "error":
        return SnapshotRefreshResult(
            status="error",
            fetch=fetched,
            write=None,
            latest=latest,
            error=fetched.error,
        )
    assert fetched.body is not None
    try:
        snapshot = parse_forecast_html(
            fetched.body,
            source,
            captured_at=fetched.fetched_at,
        )
    except ForecastParseError as exc:
        return SnapshotRefreshResult(
            status="error",
            fetch=fetched,
            write=None,
            latest=latest,
            error=f"invalid forecast page: {exc}",
        )
    write = store_snapshot(
        root,
        source,
        snapshot,
        fetched.body,
        etag=fetched.etag,
        last_modified=fetched.last_modified,
        http_status=fetched.http_status,
    )
    return SnapshotRefreshResult(
        status=write.status,
        fetch=fetched,
        write=write,
        latest=load_latest(root, source),
    )
