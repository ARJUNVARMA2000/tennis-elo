"""Data-health sentinel: stable machine findings for quiet pipeline failures.

Two layers are surfaced in data/output/health.json and red the daily build under --strict:
  * source freshness (tour_health/problems) — a scraper silently froze and the newest
    match/serve-stats row stopped advancing. The TML GitHub freeze of Jan 2026 went
    unnoticed for months precisely because every downloader failure was silent.
  * produced output (read_outputs/output_problems) — the JSON the web actually reads
    (counts, tournaments, matches, predictions) is missing, stale, or internally
    inconsistent even though the sources looked fine.

Every invariant emits ``health-finding-v1``: code/scope/tour/entity define a stable
fingerprint, while severity/evidence/message define its mutable revision. The workflow
runs this without --strict on every daily/full and hourly/quick run, then reconciles one
durable GitHub issue per actionable fingerprint. Quick runs red only for onset/recurrence;
standing findings stay green and independently close on recovery. Info findings remain
visible without alarming. Legacy prose lists and --issue-body remain during migration.

--gate is the PRE-deploy guard the workflow runs before publishing: it fails (exit 1) only
on produced-output integrity problems (not source freshness), so an internally-inconsistent
build (e.g. impossible reach odds, a live event naming a champion) can never reach the site;
a failure keeps the last good deploy live. It never writes health.json.

Run:  PYTHONPATH=src python -m tennis_model.data.health
      [--strict | --issue-body | --findings-json | --finding-body
       | --gate [--gate-report PATH]]
"""

from __future__ import annotations

import csv
import glob
import hashlib
import itertools
import json
import os
import re
import shutil
import urllib.parse
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from ..config import (
    DATA_DIR,
    HEALTH_CHARTING_COVERAGE_NOTE_DAYS,
    HEALTH_MAX_BUILD_AGE_DAYS,
    HEALTH_MAX_FORECAST_AGE_DAYS,
    HEALTH_MAX_FRESH_AGE_DAYS,
    HEALTH_MAX_FUTURE_DATE_DAYS,
    HEALTH_MAX_LIVE_EVENT_AGE_DAYS,
    HEALTH_MAX_LIVERANK_NULL_FRAC,
    HEALTH_MAX_MARKET_LAG_DAYS,
    HEALTH_MAX_MODEL_AGE_DAYS,
    HEALTH_MAX_RESULT_AGE_DAYS,
    HEALTH_MAX_STATS_AGE_DAYS,
    HEALTH_MAX_UPCOMING_START_LAG_DAYS,
    HEALTH_MIN_MATCHES,
    HEALTH_MIN_STATS_FRACTION,
    HEALTH_OFFSEASON_RELAX_DAYS,
    MATCH_POPULATION_VERSION,
    MAX_FUTURE_MATCH_DAYS,
    OUTPUT_DIR,
    PLAYER_ALIASES,
    SURFACE_MAP,
    TOURS,
    WEB_DATA_DIR,
    WTA_DUAL_STATE_GATE_THRESHOLD,
    fresh_dir,
    historical_dir,
    live_dir,
    lower_dir,
    output_dir,
    stats_dir,
)
from ..model.features import FEATURES
from ..timing import (
    PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS,
    PRODUCT_STAGE_NAMES,
    STAGE_STATUS_FILENAME,
    STAGE_STATUS_SCHEMA,
    validate_stage_status,
)
from .charting import _GENDER, CHARTING_DIR
from .names import name_key
from .participants import classify_participant, is_real_participant
from .results import load_matches
from .surface import LEVEL_VOCAB

FINDING_SCHEMA = "health-finding-v1"
FINDING_ISSUE_BODY_MAX_CHARS = 60_000
_FINDING_CODE_RE = re.compile(r"^(source|output|cross)(?:\.[a-z][a-z0-9_]*){2,}$")
_UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_FINDING_SEVERITIES = frozenset({"error", "warning", "info"})
_FINDING_SCOPES = frozenset({"source", "output", "cross"})


@dataclass(frozen=True, slots=True)
class HealthFinding:
    """Stable machine identity plus mutable human evidence for one health invariant.

    Fingerprints deliberately exclude severity, evidence, and prose: an age moving from 9d
    to 10d, a wording cleanup, or warning-to-error promotion is one continuing incident.
    ``revision`` captures those mutable fields so reporters may update that same incident.
    """

    code: str
    severity: Literal["error", "warning", "info"]
    scope: Literal["source", "output", "cross"]
    tour: str | None
    entity: str | None
    evidence: dict
    message: str

    def __post_init__(self) -> None:
        if not _FINDING_CODE_RE.fullmatch(self.code):
            raise ValueError(f"invalid health finding code {self.code!r}")
        if self.severity not in _FINDING_SEVERITIES:
            raise ValueError(f"invalid health finding severity {self.severity!r}")
        if self.scope not in _FINDING_SCOPES or not self.code.startswith(f"{self.scope}."):
            raise ValueError("health finding scope/code mismatch")
        if self.tour not in (*TOURS, None):
            raise ValueError(f"invalid health finding tour {self.tour!r}")
        if self.scope == "cross" and self.tour is not None:
            raise ValueError("cross-tour finding cannot name one tour")
        if self.scope != "cross" and self.tour is None:
            raise ValueError("source/output finding must name a tour")
        if self.entity is not None and (not isinstance(self.entity, str) or not self.entity.strip()):
            raise ValueError("health finding entity must be a non-empty string or null")
        if not isinstance(self.evidence, dict) or not isinstance(self.message, str) or not self.message:
            raise ValueError("health finding evidence/message is malformed")
        try:
            json.dumps(self.evidence, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("health finding evidence is not strict JSON") from exc

    @property
    def fingerprint(self) -> str:
        identity = [FINDING_SCHEMA, self.code, self.scope, self.tour, self.entity]
        raw = json.dumps(identity, separators=(",", ":"), ensure_ascii=False).encode()
        return f"hf1:{hashlib.sha256(raw).hexdigest()}"

    @property
    def revision(self) -> str:
        content = [self.severity, self.evidence, self.message]
        raw = json.dumps(content, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
        return f"hr1:{hashlib.sha256(raw).hexdigest()}"

    def as_dict(self) -> dict:
        return {
            "schema": FINDING_SCHEMA,
            "fingerprint": self.fingerprint,
            "revision": self.revision,
            "code": self.code,
            "severity": self.severity,
            "scope": self.scope,
            "tour": self.tour,
            "entity": self.entity,
            "evidence": self.evidence,
            "message": self.message,
        }


class _FindingCollector:
    def __init__(self, scope: str, tour: str | None):
        self.scope = scope
        self.tour = tour
        self.findings: list[HealthFinding] = []


def _add_finding(out, code: str, message: str, *, severity: str = "error",
                 entity: str | None = None, evidence: dict | None = None,
                 scope: str | None = None, tour: str | None = None) -> None:
    """Emit typed findings in production while preserving helper tests using plain lists."""
    if isinstance(out, _FindingCollector):
        out.findings.append(HealthFinding(
            code=code,
            severity=severity,
            scope=scope or out.scope,
            tour=tour if tour is not None else out.tour,
            entity=entity,
            evidence=evidence or {},
            message=message,
        ))
    else:
        out.append(message)


def _finding_messages(findings: list[HealthFinding], *, actionable_only: bool = True) -> list[str]:
    return [finding.message for finding in findings
            if not actionable_only or finding.severity != "info"]


def _lineage_observation(*, require_accepted: bool) -> tuple[dict, dict[str, list[HealthFinding]]]:
    """Inspect the whole release once and translate issues into blocking typed findings.

    The pre-deploy gate calls this with ``require_accepted=False`` because acceptance is
    written only after that gate succeeds. Authoritative health requires the private
    receipt. Raw parser/IO detail remains private; the public contract carries only a
    stable reason, safe relative artifact path, and state. Global release issues are
    attached to both tours because one shared manifest owns both payloads.
    """
    from ..artifact_lineage import AcceptedRelease, inspect_release

    state = inspect_release(
        OUTPUT_DIR,
        require_accepted=require_accepted,
    )
    accepted = state.release if isinstance(state.release, AcceptedRelease) else None
    release = accepted.release if accepted is not None else state.release
    summary = {
        "schema": "artifact-lineage-v1",
        "status": state.state,
        "releaseId": release.release_id if release is not None else None,
        "manifestSha256": release.manifest_sha256 if release is not None else None,
        "tours": list(TOURS),
    }
    by_tour: dict[str, list[HealthFinding]] = {tour: [] for tour in TOURS}
    for issue in state.issues:
        affected = (issue.tour,) if issue.tour in TOURS else tuple(TOURS)
        for tour in affected:
            reason = issue.reason.value
            path = issue.path
            by_tour[tour].append(HealthFinding(
                code=issue.code,
                severity="error",
                scope="output",
                tour=tour,
                entity=path or "release",
                evidence={"state": state.state, "reason": reason, "path": path},
                message=(
                    f"{tour.upper()} release lineage: "
                    f"{reason.replace('-', ' ')}"
                    + (f" ({path})" if path else "")
                ),
            ))
    return summary, by_tour


def _write_json_atomic(path, payload: object) -> None:
    """Write JSON without ever exposing a partial file to the next workflow step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _offseason(now: pd.Timestamp) -> bool:
    # the season effectively ends mid-November (Finals/Davis Cup), not December — relax
    # the age/emptiness gates from Nov 21 so the quiet weeks don't red the build
    return now.month == 12 or (now.month == 11 and now.day > 20)


# ---------------------------------------------------------------------------
# Source freshness (are the scrapers still advancing?)
# ---------------------------------------------------------------------------
def charting_date_max(tour: str):
    """Newest charted match date from the MCP stats-Overview file (the file
    build_profiles() anchors on — an empty Overview means no style profiles at all).
    match_id encodes the date as a YYYYMMDD prefix. IO seam (patched in tests)."""
    f = CHARTING_DIR / f"charting-{_GENDER[tour]}-stats-Overview.csv"
    if not f.exists():
        return None
    try:
        ids = pd.read_csv(f, usecols=["match_id"], encoding="utf-8-sig")["match_id"]
    except (ValueError, OSError):
        return None
    m = pd.to_datetime(ids.astype(str).str[:8], format="%Y%m%d", errors="coerce").max()
    return m if pd.notna(m) else None


def _fresh_dates(tour: str):
    """Parsed tourney_date series from the fresh overlay's newest year file (or None)."""
    files = sorted(glob.glob(str(fresh_dir(tour) / "*.csv")))   # per-year names sort lexically
    if not files:
        return None
    from .results import _parse_dates  # handles the overlay's YYYY/M/D format
    try:
        s = pd.read_csv(files[-1], usecols=["tourney_date"], encoding="utf-8-sig")["tourney_date"]
    except (ValueError, OSError):
        return None
    return _parse_dates(s)


def _credible_horizon(now: pd.Timestamp | None):
    """The latest date a real match could carry, or None when we have no clock to judge by."""
    if now is None:
        return None
    return (now.tz_localize(None) if now.tzinfo else now) + pd.Timedelta(days=MAX_FUTURE_MATCH_DAYS)


def fresh_date_max(tour: str, now: pd.Timestamp | None = None):
    """Newest CREDIBLE tourney_date in the fresh overlay's newest year file.

    Checked directly because the merged result_age_days can't see this source freeze — the
    ESPN live overlay keeps the merged maximum current. IO seam (patched in tests).

    Future-dated rows are excluded, and that exclusion is the whole point of the argument.
    Age is `now - max`, so ONE corrupt future row pins this negative forever and the
    staleness gate above it can never fire again — a one-sided bound on a signed quantity
    is not a bound. The WTA overlay carried the Iasi final as 2029/7/20 from 2026-07-20;
    `fresh_age_days` read -1078 against a 14-day limit and reported ok for three weeks,
    so the freeze alarm for that source was dead the entire time. `_drop_impossible_dates`
    protects the model population from the same row, which is exactly why the merged
    `date_max` check cannot stand in for this one — it never sees the corruption.
    """
    dates = _fresh_dates(tour)
    if dates is None:
        return None
    horizon = _credible_horizon(now)
    if horizon is not None:
        dates = dates[dates <= horizon]
    m = dates.max() if len(dates) else pd.NaT
    return m if pd.notna(m) else None


def fresh_future_date_max(tour: str, now: pd.Timestamp | None = None):
    """Newest fresh-overlay date BEYOND the credible horizon, or None if the file is clean.

    The corruption `fresh_date_max` filters out still has to be reported, or fixing the
    staleness signal would simply hide the bad row instead. IO seam (patched in tests).
    """
    horizon = _credible_horizon(now)
    dates = _fresh_dates(tour)
    if dates is None or horizon is None:
        return None
    beyond = dates[dates > horizon]
    m = beyond.max() if len(beyond) else pd.NaT
    return m if pd.notna(m) else None


def _health_input_fingerprint(tour: str) -> str:
    """Cheap same-run identity for every file the source-health summary reads."""
    files = []
    for root in (historical_dir(tour), stats_dir(tour), fresh_dir(tour),
                 lower_dir(tour), live_dir(tour)):
        files.extend(root.glob("*.csv"))
    # A total ESPN failure intentionally retains every CSV. The receipt must still bust a
    # same-day source manifest or that successful old manifest would mask today's outage.
    files.append(live_dir(tour) / "espn_acquisition.json")
    files.append(CHARTING_DIR / f"charting-{_GENDER[tour]}-stats-Overview.csv")
    rows = []
    for path in sorted(set(files)):
        try:
            st = path.stat()
        except OSError:
            if path.name == "espn_acquisition.json":
                rows.append(f"{path}:missing")
            continue
        rows.append(f"{path}:{st.st_size}:{st.st_mtime_ns}")
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def _espn_acquisition(tour: str) -> dict:
    """Load and minimally validate the same-run ESPN acquisition receipt."""
    path = live_dir(tour) / "espn_acquisition.json"
    if not path.exists():
        return {"status": "missing"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        queries = payload.get("queries")
        overlay = payload.get("overlay")
        allowed = {"success", "success_empty", "partial_query_failure",
                   "total_transport_failure"}
        if (not isinstance(payload, dict)
                or payload.get("schema") != "espn-acquisition-v1"
                or payload.get("tour") != tour
                or payload.get("status") not in allowed
                or not isinstance(queries, dict)
                or not all(_plain_int(queries.get(key)) and queries[key] >= 0
                           for key in ("attempted", "succeeded", "failed"))
                or queries["attempted"] < 1
                or queries["attempted"] != queries["succeeded"] + queries["failed"]
                or not _plain_int(payload.get("eventCount"))
                or payload["eventCount"] < 0
                or not isinstance(overlay, dict)
                or overlay.get("status") not in {
                    "updated", "partially_updated", "retained_last_good", "unavailable",
                }
                or not isinstance(overlay.get("updatedFiles"), list)
                or not isinstance(overlay.get("retainedFiles"), list)):
            raise ValueError("receipt contract mismatch")
        status = payload["status"]
        attempted, succeeded, failed = (queries[key]
                                         for key in ("attempted", "succeeded", "failed"))
        events = payload["eventCount"]
        consistent = {
            "success": failed == 0 and succeeded == attempted and events > 0,
            "success_empty": failed == 0 and succeeded == attempted and events == 0,
            "partial_query_failure": 0 < failed < attempted and succeeded > 0,
            "total_transport_failure": failed == attempted and succeeded == 0,
        }[status]
        if not consistent:
            raise ValueError("receipt status/count mismatch")
        return payload
    except (OSError, ValueError, AttributeError, TypeError):
        return {"status": "malformed"}


def _tour_health_from_frame(tour: str, df: pd.DataFrame, now: pd.Timestamp) -> dict:
    completed = df[df["completed"]]
    stats_rows = df[df["has_stats"]]
    cur = df[df["date"].dt.year == now.year]
    # empty slices give NaT maxima — report None (flagged by problems()) rather than crash
    date_max = df["date"].max() if len(df) else pd.NaT
    res_max = completed["date"].max() if len(completed) else pd.NaT
    stat_max = stats_rows["date"].max() if len(stats_rows) else pd.NaT
    fr_max, ch_max = fresh_date_max(tour, now), charting_date_max(tour)
    fr_future = fresh_future_date_max(tour, now)
    return {
        "fresh_future_date_max": str(fr_future.date()) if fr_future is not None else None,
        "matches": int(len(df)),
        "date_max": str(date_max.date()) if pd.notna(date_max) else None,
        "result_age_days": int((now - res_max).days) if pd.notna(res_max) else None,
        "stats_date_max": str(stat_max.date()) if pd.notna(stat_max) else None,
        "stats_age_days": int((now - stat_max).days) if pd.notna(stat_max) else None,
        "cur_year_matches": int(len(cur)),
        "cur_year_stats_fraction": round(float(cur["has_stats"].mean()), 4) if len(cur) else None,
        "fresh_date_max": str(fr_max.date()) if fr_max is not None else None,
        "fresh_age_days": int((now - fr_max).days) if fr_max is not None else None,
        "charting_date_max": str(ch_max.date()) if ch_max is not None else None,
        "charting_age_days": int((now - ch_max).days) if ch_max is not None else None,
        "espn_acquisition": _espn_acquisition(tour),
    }


def write_health_manifest(tour: str, df: pd.DataFrame,
                          now: pd.Timestamp | None = None) -> dict:
    """Persist the source summary from the pipeline's already-normalized frame."""
    now = now if now is not None else pd.Timestamp(datetime.now(UTC).date())
    health = _tour_health_from_frame(tour, df, now)
    payload = {
        "schema": 1,
        "asOfDate": str(now.date()),
        "inputFingerprint": _health_input_fingerprint(tour),
        "health": health,
    }
    path = OUTPUT_DIR / tour / "health-source.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return health


def tour_health(tour: str, now: pd.Timestamp) -> dict:
    manifest = OUTPUT_DIR / tour / "health-source.json"
    if manifest.exists():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            if (payload.get("schema") == 1
                    and payload.get("asOfDate") == str(now.date())
                    and payload.get("inputFingerprint") == _health_input_fingerprint(tour)
                    and isinstance(payload.get("health"), dict)):
                print(f"  health/{tour}: reused pipeline source manifest")
                return payload["health"]
        except (OSError, ValueError):
            pass
    return _tour_health_from_frame(tour, load_matches(tour), now)


def source_checks(tour: str, h: dict, now: pd.Timestamp) -> list[dict]:
    """Structured verdicts for the raw-source freshness checks — the single source of
    truth: problems() derives its alert strings from these rows, and the (hidden)
    /health page renders them, so the two can never drift. Each row:
      {key, label, value, limit, unit, date, ok, note, noteLevel, problem}
    `problem` is a hard failure. `noteLevel` distinguishes actionable degradation from
    benign context; both stay visible without forcing presentation code to parse prose."""
    offseason = _offseason(now)
    max_result = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_RESULT_AGE_DAYS
    max_stats = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_STATS_AGE_DAYS
    min_frac = HEALTH_MIN_STATS_FRACTION.get(tour, 0.0)

    def row(key, label, value, limit, unit="d", date=None, note=None, problem=None,
            note_level="degraded"):
        return {"key": key, "label": label, "value": value, "limit": limit, "unit": unit,
                "date": date, "ok": problem is None, "note": note,
                "noteLevel": note_level if note else None, "problem": problem}

    rows = []
    res_age = h["result_age_days"]
    rows.append(row(
        "results", "Match results (merged)", res_age, max_result,
        problem=(f"{tour}: no completed matches loaded" if res_age is None
                 else f"{tour}: newest completed match is {res_age}d old (max {max_result})"
                 if res_age > max_result else None)))
    # A future-dated row is corruption, not staleness, and the age check above structurally
    # cannot see it: result_age_days goes NEGATIVE and sails under its maximum. It is also
    # disproportionately destructive, because the date-relative windows downstream anchor on
    # the dataset's MAX date rather than on today — one mistyped year in the WTA fresh overlay
    # (Iasi final as 2029/7/20, seen 2026-07-25) moved elo.last_date three years out, and the
    # ACTIVE_DAYS window then held only the two players in that single row, so the tour
    # exported 2 players instead of 200. results.py drops these at ingest, which also means
    # this check sees the population AFTER that filter and so cannot catch a bad row in a
    # source file — the per-source `fresh_future` check below is what covers that. This one
    # is the backstop for corruption reaching the merged population by some other path.
    dmax = pd.Timestamp(h["date_max"]) if h.get("date_max") else None
    future_days = int((dmax - now).days) if dmax is not None else None
    rows.append(row(
        "future_dates", "Newest match date", future_days, HEALTH_MAX_FUTURE_DATE_DAYS,
        date=h.get("date_max"),
        problem=(f"{tour}: newest match is dated {h['date_max']}, {future_days}d in the FUTURE "
                 f"(max {HEALTH_MAX_FUTURE_DATE_DAYS}) — upstream date corruption"
                 if future_days is not None and future_days > HEALTH_MAX_FUTURE_DATE_DAYS
                 else None)))
    if min_frac > 0:
        stats_age = h["stats_age_days"]
        rows.append(row(
            "stats", "Serve-stats overlay", stats_age, max_stats, date=h.get("stats_date_max"),
            problem=(f"{tour}: newest serve-stats row is {stats_age}d old (max {max_stats})"
                     if stats_age is None or stats_age > max_stats else None)))
        frac = h["cur_year_stats_fraction"]
        rows.append(row(
            "coverage", "Season stats coverage", frac, min_frac, unit="frac",
            note=("season too young to judge (under 100 matches)"
                  if frac is not None and h["cur_year_matches"] < 100 else None),
            note_level="info",
            problem=(f"{tour}: current-season stats coverage {frac:.0%} < {min_frac:.0%}"
                     if frac is not None and h["cur_year_matches"] >= 100 and frac < min_frac
                     else None)))
    # Per-source freshness: the merged result_age above can't see ONE frozen source (the
    # ESPN live overlay keeps the merged max current), so the silent sources get their own
    # age gates. The fresh overlay updates ~weekly, so it legitimately lags the season
    # restart — extend ITS relaxation through mid-January (not _offseason itself, which
    # would wrongly relax the result-age/liveRank/emptiness checks during the live
    # January swing).
    jan_grace = now.month == 1 and now.day < 15
    max_fresh = HEALTH_OFFSEASON_RELAX_DAYS if (offseason or jan_grace) else HEALTH_MAX_FRESH_AGE_DAYS
    # The fresh overlay is a redundancy layer for RESULTS: while the full-schema stats
    # overlay is current (gated above), results/ranks/stats all still flow, so a frozen
    # fresh overlay starves nothing and its gate stays quiet. TennisCourtLog froze its ATP
    # file on 2026-06-22 with the TML site daily-fresh — an unactionable standing red (no
    # replacement mirror exists); and a completed-events-only weekly updater legitimately
    # exceeds 14d during every slam fortnight. The freeze alarm fires only when the fresh
    # overlay is the freshest non-live source left — i.e. the stats overlay is stale too.
    stats_current = h["stats_age_days"] is not None and h["stats_age_days"] <= max_stats
    fresh_age = h["fresh_age_days"]
    shadowed = fresh_age is not None and fresh_age > max_fresh and stats_current
    rows.append(row(
        "fresh", "Results overlay (fresh)", fresh_age, max_fresh, date=h.get("fresh_date_max"),
        note_level="info",
        note=("frozen upstream, but shadowed — the serve-stats overlay is current, so "
              "results/ranks/stats all still flow" if shadowed else None),
        problem=(f"{tour}: fresh overlay has no loadable results" if fresh_age is None
                 else f"{tour}: newest fresh-overlay result is {fresh_age}d old "
                 f"(max {max_fresh}) — the results overlay source may have frozen"
                 if fresh_age > max_fresh and not stats_current else None)))
    # The corrupt rows `fresh_date_max` now filters out still have to be named, or fixing the
    # staleness signal would just hide them. This reads the RAW overlay, which is the only
    # place the corruption survives: `_drop_impossible_dates` strips it before it can reach
    # the merged `date_max` the future_dates check above looks at, so that check has never
    # been able to see a bad row arriving by this path.
    # Reported as a NOTE, not a problem, because by the time it gets here the row is fully
    # handled: `_repair_corrupt_final_years` puts a provable far-future final back in its real
    # season, `_drop_impossible_dates` removes anything it could not prove, and `fresh_date_max`
    # above now excludes it from the age signal. A standing red on an upstream typo nobody here
    # can edit is the trap this repo already learned once — the daily full run reds on ANY
    # problem regardless of the hourly dedup, so it would page every morning, forever, about
    # something already fixed three ways. Visible on /health is the right severity.
    fr_future = h.get("fresh_future_date_max")
    rows.append(row(
        "fresh_future", "Fresh overlay date sanity", 1 if fr_future else 0, 0,
        unit="rows", date=fr_future, note_level="info",
        note=(f"upstream year typo: a result dated {fr_future}. Excluded from the model "
              f"population and from the freshness age beside it, and repaired into its real "
              f"season where the bracket topology proves the year" if fr_future else None)))
    ch_age = h["charting_age_days"]
    rows.append(row(
        "charting", "Match charting (MCP)", ch_age, HEALTH_CHARTING_COVERAGE_NOTE_DAYS,
        date=h.get("charting_date_max"), note_level="info",
        note=(f"volunteer batch source; newest charted match is {ch_age}d old "
              f"(coverage note after {HEALTH_CHARTING_COVERAGE_NOTE_DAYS}d)"
              if ch_age is not None and ch_age > HEALTH_CHARTING_COVERAGE_NOTE_DAYS
              else None),
        problem=(f"{tour}: charting files missing/unreadable (style features degraded)"
                 if ch_age is None else None)))
    acquisition = h.get("espn_acquisition")
    if isinstance(acquisition, dict):
        status = acquisition.get("status")
        queries = acquisition.get("queries") if isinstance(acquisition.get("queries"), dict) else {}
        attempted = queries.get("attempted")
        failed = queries.get("failed")
        overlay = acquisition.get("overlay") if isinstance(acquisition.get("overlay"), dict) else {}
        overlay_status = overlay.get("status")
        retained = overlay_status == "retained_last_good"
        problem = None
        note = None
        if status == "malformed":
            problem = f"{tour}: ESPN scoreboard acquisition receipt is malformed/incompatible"
        elif status == "total_transport_failure":
            disposition = ("retained last-good live overlay" if retained
                           else "no prior live overlay available")
            problem = (f"{tour}: ESPN scoreboard acquisition failed for all {attempted} queries "
                       f"— {disposition}")
        elif overlay.get("processingFailureType"):
            if overlay_status == "partially_updated":
                disposition = "left an explicitly partial overlay update"
            else:
                disposition = ("retained last-good live overlay" if retained
                               else "no prior live overlay available")
            problem = (f"{tour}: ESPN live overlay processing failed after acquisition "
                       f"({overlay['processingFailureType']}) — {disposition}")
        elif status == "partial_query_failure":
            succeeded = queries.get("succeeded")
            if (_plain_int(succeeded) and _plain_int(failed) and failed >= succeeded):
                if overlay_status == "partially_updated":
                    disposition = "left an explicitly partial overlay update"
                elif overlay_status == "updated":
                    disposition = "wrote a degraded live overlay"
                else:
                    disposition = ("retained last-good live overlay" if retained
                                   else "no prior live overlay available")
                problem = (f"{tour}: ESPN scoreboard acquisition severely degraded "
                           f"({failed} of {attempted} queries failed) — {disposition}")
            else:
                note = (f"ESPN answered {succeeded} of {attempted} scoreboard queries; "
                        f"{failed} failed query(s) are recorded")
        elif status == "success_empty":
            note = "ESPN answered every scoreboard query; the acquisition window contained 0 events"
        elif status == "missing":
            note = "receipt not present in this legacy cache; the next data refresh will create it"
        rows.append(row(
            "espn_acquisition", "ESPN scoreboard acquisition", failed, 0,
            unit="", date=acquisition.get("completedAt"), note=note, problem=problem,
            note_level=("degraded" if status == "partial_query_failure" else "info")))
    return rows


def source_findings(tour: str, h: dict, now: pd.Timestamp) -> list[HealthFinding]:
    """Typed source verdicts derived from the already-structured source-check rows."""
    rows = source_checks(tour, h, now)
    acquisition = h.get("espn_acquisition") if isinstance(h.get("espn_acquisition"), dict) else {}
    entities = {
        "results": f"merged-results:{tour}",
        "future_dates": f"merged-results:{tour}",
        "stats": f"serve-stats:{tour}",
        "coverage": f"serve-stats:{tour}",
        "fresh": f"fresh-overlay:{tour}",
        "fresh_future": f"fresh-overlay:{tour}",
        "charting": f"match-charting:{tour}",
        "espn_acquisition": f"espn-scoreboard:{tour}",
    }
    problem_codes = {
        "future_dates": "source.results.future_date",
        "stats": "source.stats.stale",
        "coverage": "source.stats.coverage_low",
        "charting": "source.charting.unavailable",
    }
    note_codes = {
        "coverage": "source.stats.coverage_pending",
        "fresh": "source.fresh_overlay.shadowed",
        "fresh_future": "source.fresh_overlay.future_date",
        "charting": "source.charting.coverage_age",
    }
    findings: list[HealthFinding] = []
    for row in rows:
        key = row["key"]
        if key == "espn_acquisition":
            queries = acquisition.get("queries") if isinstance(
                acquisition.get("queries"), dict) else {}
            overlay = acquisition.get("overlay") if isinstance(
                acquisition.get("overlay"), dict) else {}
            evidence = {
                "status": acquisition.get("status"),
                "eventCount": acquisition.get("eventCount"),
                "queries": {
                    name: queries.get(name)
                    for name in ("attempted", "succeeded", "failed", "featuredSucceeded")
                },
                "overlay": {
                    "status": overlay.get("status"),
                    "processingFailureType": overlay.get("processingFailureType"),
                    "updatedFiles": sorted(map(str, overlay.get("updatedFiles") or []))
                    if isinstance(overlay.get("updatedFiles"), list) else None,
                    "retainedFiles": sorted(map(str, overlay.get("retainedFiles") or []))
                    if isinstance(overlay.get("retainedFiles"), list) else None,
                },
            }
            evidence["queries"]["failedKeys"] = (
                sorted(map(str, queries.get("failedKeys") or []))
                if isinstance(queries.get("failedKeys"), list) else None)
            evidence["queries"]["failureTypes"] = (
                {str(name): queries["failureTypes"][name]
                 for name in sorted(queries["failureTypes"], key=str)}
                if isinstance(queries.get("failureTypes"), dict) else None)
        else:
            evidence = {name: row.get(name) for name in ("value", "limit", "unit", "date")
                        if row.get(name) is None
                        or isinstance(row.get(name), (str, int, float, bool))}
        if row.get("problem"):
            if key == "results":
                code = ("source.results.unavailable" if row.get("value") is None
                        else "source.results.stale")
            elif key == "fresh":
                code = ("source.fresh_overlay.unavailable" if row.get("value") is None
                        else "source.fresh_overlay.stale")
            elif key == "espn_acquisition":
                status = acquisition.get("status")
                code = {
                    "malformed": "source.espn.receipt_malformed",
                    "total_transport_failure": "source.espn.total_transport_failure",
                    "partial_query_failure": "source.espn.severe_partial_failure",
                }.get(status, "source.espn.processing_failure")
            else:
                code = problem_codes[key]
            findings.append(HealthFinding(
                code=code, severity="error", scope="source", tour=tour,
                entity=entities[key], evidence=evidence, message=row["problem"]))
        elif row.get("note"):
            if key == "espn_acquisition":
                status = acquisition.get("status")
                code = {
                    "partial_query_failure": "source.espn.partial_query_failure",
                    "success_empty": "source.espn.success_empty",
                    "missing": "source.espn.receipt_missing",
                }.get(status, "source.espn.status_note")
            else:
                code = note_codes[key]
            severity = "warning" if row.get("noteLevel") == "degraded" else "info"
            findings.append(HealthFinding(
                code=code, severity=severity, scope="source", tour=tour,
                entity=entities[key], evidence=evidence,
                message=f"{tour}: {row['label']}: {row['note']}"))
    return findings


def problems(tour: str, h: dict, now: pd.Timestamp) -> list[str]:
    return _finding_messages(source_findings(tour, h, now))


# ---------------------------------------------------------------------------
# Produced-output validation (does the JSON the web reads make sense?)
# ---------------------------------------------------------------------------
# The web reads these per tour; the first group must always exist and parse, the second
# is best-effort (accuracy is backtest-only, track needs graded forecasts).
_REQUIRED_OUTPUTS = ("meta", "players", "tournaments", "event_coverage", "brackets", "upcoming-index",
                     "matrix-index", "ratings_history", "profile-index", "draws", "fixtures", "method",
                     "scenario-index", "performance")
_OPTIONAL_OUTPUTS = ("accuracy", "track", "market")
_EVIDENCE_KEYS = (
    "surfaceElo", "serveReturn", "form", "rest", "home", "h2h", "style",
)
_WATCH_WEIGHTS = {
    "closeness": 30, "quality": 25, "styleContrast": 15,
    "stakes": 15, "titleLeverage": 15,
}


def _is_real_name(x: object) -> bool:
    """True if the shared provider-aware vocabulary says this names an actual player."""
    return is_real_participant(x)

_STATUSES = {"live", "upcoming", "completed"}
_DRAW_STATES = {"real", "partial", "seeded", "final", "unavailable"}
_REACH_ORDER = ("R128", "R64", "R32", "R16", "QF", "SF", "F", "Champion")

# Suffix `_tiered` stamps on a board-quality problem below the 500 tier (see GATE_BLOCKING_TIERS).
_BELOW_TIER = " [below the 500 tier — advisory]"

# The pre-deploy --gate blocks a deploy only on problems that make the shipped site WRONG
# (impossible numbers, structural breaks, missing/corrupt required JSON). A thin or quirky
# schedule/rankings feed is worth flagging but not worth freezing the site over, so these
# markers stay ADVISORY — reported by the gate but left to the non-blocking post-deploy
# sentinel. New checks default to blocking (the safe direction).
_GATE_ADVISORY = (
    "same event more than once",   # YoY sponsor-rename / dedup split (schedule cosmetic)
    "one event under two names",
    "no live/upcoming event",      # a genuine quiet week can leave the board thin
    "is empty",                    # tournaments.json / reconstructed upcoming feed empty
    "liveRank",                    # rankings source drifted (site still correct on model odds)
    "outputs last built",          # build-age; can't legitimately fire right after a build
    "model last retrained",        # retrain liveness; a stale model still forecasts — freezing
                                   # the site would strand it on an even staler deploy
    "market.json odds coverage",   # benchmark-card staleness; odds are never a build dependency
    "forecast drift",              # model-decay advisory; a re-tune recommendation must never block a deploy
    "forecast log last advanced",  # eval-artifact liveness; never a build dependency
    "unclassified live match(es) withheld",  # conservative WTA population filtering;
                                              # visible, but stale results beat policy leakage
    # Board-quality problems are TIER-AWARE via `_tiered`: 500-and-above blocks while the
    # long tail warns. The original stuck-live, many-alive, and placeholder exemptions were
    # removed after their producer fixes stayed quiet through successive real refreshes.
    # The producer now withholds odds entirely below a real majority, so on a clean build
    # the placeholder checks cannot fire at any tier.
    # NB: "is a month-of-year guess" is deliberately NOT listed — it is TIER-AWARE via
    # `_tiered`, so it blocks on a 500-or-above (where a guessed surface misprices a marquee
    # event, as it did the DC Open) and carries the _BELOW_TIER suffix elsewhere, because for
    # a brand-new small event with no archive row and no article yet a guess is all there is.
    # Cross-tour surface disagreement: at least one side is wrong, but which one is not
    # knowable here, and freezing both boards over it helps nobody.
    "surface split across tours",
    # A tier we could not resolve at all is tier-aware through `_tiered`. A real generic
    # small-event card gets the normal below-tier suffix; a coverage shell forces blocking.
    # Started but still labelled upcoming. ESPN start dates include qualifying, so a couple
    # of days of lag is normal and a Slam's whole quali week is normal.
    "has not flipped live",
    # Run-over-run bracket loss: prev-based, so `--gate` (prev=None) can never see it anyway.
    "lost its bracket since the previous run",
    # Calendar-complete without a final. The card is honest about not knowing the champion —
    # far better than the alternative it replaced, which was sitting "live" for nine days.
    "completed without a recorded final",
    # Stamped by `_tiered` on board-quality problems below the 500 tier.
    _BELOW_TIER.strip(),
)

# Canonical shipped surfaces — SURFACE_MAP's VALUES (Carpet folds to Hard), so this can
# never drift from what `results.clean` is able to produce.
_CANONICAL_SURFACES = frozenset(SURFACE_MAP.values())


# Tier-aware severity for BOARD-QUALITY problems (a wrong surface, a placeholder projection,
# a card that never flipped live). The marquee events are the ones that must never ship wrong;
# the long tail warns instead, so one obscure 125 cannot freeze the whole site the way a
# single ATP fixtures row froze it for 16 hours on 2026-07-27. Structural problems (corrupt
# JSON, aliveCount > drawSize, a non-canonical surface VALUE) ignore tier and always block.
# Olympics and Davis/BJK Cup are deliberately NOT here: both are marquee but have atypical
# team formats, making them the likeliest spurious blockers, and they are rare enough that
# advisory plus the post-deploy sentinel is adequate.
GATE_BLOCKING_TIERS = frozenset({
    "Grand Slam", "Tour Finals", "Masters 1000", "WTA 1000", "ATP 500", "WTA 500",
})


def _tier_blocks(level: object) -> bool:
    """True when an event's tier is senior enough that board-quality problems block."""
    return str(level) in GATE_BLOCKING_TIERS


def _tiered(problem: str, level: object, *, force: bool = False) -> str:
    """Stamp a board-quality problem advisory unless the event is 500-or-above.

    The suffix remains for legacy prose consumers and explains the decision in logs; typed
    emitters pair it with ``_tier_severity`` and the production gate reads that severity.
    Coverage-only cards set ``force`` because their unresolved tier cannot be evidence that
    a co-located defect is unimportant."""
    return problem if force or _tier_blocks(level) else problem + _BELOW_TIER


def _tier_severity(level: object, *, force: bool = False) -> str:
    """Typed counterpart to the legacy explanatory suffix added by ``_tiered``."""
    return "error" if force or _tier_blocks(level) else "warning"


def _gate_blocks(finding: HealthFinding | dict | str) -> bool:
    """Compatibility predicate; production passes a typed finding, never prose.

    String support remains temporarily for the historical unit suite and third-party callers.
    New gate code must classify at emission and pass ``HealthFinding``/serialized finding data.
    """
    if isinstance(finding, HealthFinding):
        return finding.severity == "error"
    if isinstance(finding, dict):
        severity = finding.get("severity")
        if severity not in _FINDING_SEVERITIES:
            raise ValueError("gate received malformed serialized finding")
        return severity == "error"
    return not any(marker in finding for marker in _GATE_ADVISORY)


def _reject_nonfinite(token: str):
    """parse_constant hook: json.loads accepts NaN/Infinity by default, but the browser's
    JSON.parse rejects them — a NaN that slips into a shipped file blanks the page, not
    errors. Treat such a file as unparseable here so the gate catches what the browser will."""
    raise ValueError(f"non-finite JSON constant {token!r}")


def read_outputs(tour: str) -> dict:
    """Load a tour's produced JSON + forecast log. IO seam (monkeypatched in tests).

    Returns {"data": {stem: parsed}, "missing": [required stems absent],
             "corrupt": [stems present but unparseable OR carrying NaN/Infinity],
             "stage_status": {"state": "missing"|"malformed"|"valid", ...},
             "draw_cache_status": {
                 "state": "missing"|"malformed"|"unreadable"|"degraded"|"valid"},
             "forecast": {"lines": int, "max_as_of": str|None} | None,
             "kalshi_ledger": [row dicts] | None}.
    """
    d = output_dir(tour)
    data, missing, corrupt = {}, [], []
    for stem in _REQUIRED_OUTPUTS + _OPTIONAL_OUTPUTS:
        f = d / f"{stem}.json"
        if not f.exists():
            if stem in _REQUIRED_OUTPUTS:
                missing.append(stem)
            continue
        try:
            data[stem] = json.loads(f.read_text(), parse_constant=_reject_nonfinite)
        except (ValueError, OSError):
            corrupt.append(stem)
    stage_status: dict = {"state": "missing"}
    stage_path = d / STAGE_STATUS_FILENAME
    if stage_path.exists():
        try:
            stage_payload = json.loads(
                stage_path.read_text(encoding="utf-8"), parse_constant=_reject_nonfinite)
            stage_status = {"state": "valid", "receipt": validate_stage_status(
                stage_payload, tour)}
        except (ValueError, OSError, TypeError) as exc:
            stage_status = {
                "state": "malformed",
                "errorType": type(exc).__name__,
                "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            }
    shards, missing_files, corrupt_files = {}, [], []
    refs = []
    matrix_index = data.get("matrix-index")
    if isinstance(matrix_index, dict):
        surfaces = matrix_index.get("surfaces")
        if isinstance(surfaces, dict):
            refs.extend(name for byfmt in surfaces.values()
                        if isinstance(byfmt, dict) for name in byfmt.values())
    profile_index = data.get("profile-index")
    if isinstance(profile_index, dict):
        refs.extend(p.get("file") for p in (profile_index.get("profiles") or [])
                    if isinstance(p, dict))
    scenario_index = data.get("scenario-index")
    if isinstance(scenario_index, dict):
        refs.extend(e.get("file") for e in (scenario_index.get("events") or [])
                    if isinstance(e, dict))
    upcoming_index = data.get("upcoming-index")
    if isinstance(upcoming_index, dict):
        for event in upcoming_index.get("events") or []:
            if isinstance(event, dict):
                refs.extend((event.get("file"), event.get("evidenceFile")))
    unique_refs = []
    seen_refs = set()
    for filename in sorted(refs, key=str):
        marker = (type(filename).__name__, repr(filename))
        if marker not in seen_refs:
            seen_refs.add(marker)
            unique_refs.append(filename)
    for filename in unique_refs:
        safe = (isinstance(filename, str) and filename.endswith(".json")
                and "/" not in filename and "\\" not in filename
                and filename not in (".", ".."))
        if not safe:
            missing_files.append(str(filename))
            continue
        path = d / filename
        if not path.exists():
            missing_files.append(filename)
            continue
        try:
            shards[filename] = json.loads(
                path.read_text(), parse_constant=_reject_nonfinite)
        except (ValueError, OSError):
            corrupt_files.append(filename)
    if isinstance(upcoming_index, dict):
        upcoming = []
        for event in upcoming_index.get("events") or []:
            if not isinstance(event, dict):
                continue
            event_shard = shards.get(event.get("file"))
            evidence_shard = shards.get(event.get("evidenceFile"))
            if not isinstance(event_shard, dict) or not isinstance(evidence_shard, dict):
                continue
            details = {
                detail.get("matchId"): detail
                for detail in (evidence_shard.get("details") or [])
                if isinstance(detail, dict) and detail.get("matchId")
            }
            for match in event_shard.get("matches") or []:
                if not isinstance(match, dict):
                    continue
                detail = details.get(match.get("matchId")) or {}
                upcoming.append({**match, **{
                    key: detail.get(key) for key in ("components", "evidence", "forecast")
                }})
        data["upcoming"] = upcoming
    draw_cache = None
    draw_cache_status: dict = {"state": "missing"}
    draw_cache_path = live_dir(tour) / "tournament_draws.json"
    try:
        parsed = json.loads(
            draw_cache_path.read_text(), parse_constant=_reject_nonfinite)
        if not isinstance(parsed, dict):
            raise TypeError("tournament_draws.json must contain an object")
        draw_cache = parsed
        draw_cache_status = {"state": "valid"}
    except FileNotFoundError:
        pass
    except OSError as exc:
        draw_cache_status = {
            "state": "unreadable", "errorType": type(exc).__name__}
    except (TypeError, ValueError) as exc:
        draw_cache_status = {
            "state": "malformed", "errorType": type(exc).__name__}
    from .draws import draw_cache_refresh_failures
    refresh_failures = draw_cache_refresh_failures(tour, directory=live_dir(tour))
    if refresh_failures:
        if draw_cache_status["state"] in {"missing", "valid"}:
            draw_cache_status = {
                "state": "degraded", "failures": refresh_failures}
        else:
            draw_cache_status["refreshFailures"] = refresh_failures
    forecast = None
    fc = DATA_DIR / "forecast_log" / f"{tour}.jsonl"
    if fc.exists():
        try:
            lines = [ln for ln in fc.read_text().splitlines() if ln.strip()]
            as_ofs = []
            for ln in lines:
                try:
                    as_ofs.append(json.loads(ln).get("as_of"))
                except ValueError:
                    pass
            forecast = {"lines": len(lines),
                        "max_as_of": max([a for a in as_ofs if a], default=None)}
        except OSError:
            forecast = None
    ledger = None
    lf = DATA_DIR / "kalshi_ledger" / f"{tour}.csv"
    if lf.exists():
        try:
            with open(lf, newline="", encoding="utf-8") as f:
                ledger = [dict(r) for r in csv.DictReader(f)]
        except OSError:
            ledger = None
    return {"data": data, "missing": missing, "corrupt": corrupt,
            "shards": shards, "missing_files": missing_files,
            "corrupt_files": corrupt_files,
            "draw_cache": draw_cache, "draw_cache_status": draw_cache_status,
            "forecast": forecast, "kalshi_ledger": ledger,
            "stage_status": stage_status}


def _is_prob(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0.0 <= float(x) <= 1.0


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _population_high_water(tour: str, meta: dict, prev: dict | None) -> tuple[int | None, int | None]:
    """Return the durable accepted match-count baseline and its population version.

    The raw ``matches`` snapshot is allowed to fall so the report describes what actually
    shipped; this separate high-water pair is not.  A population-version boundary is the
    sole reset.  Legacy reports migrate from their raw pair so rollout cannot silently grant
    a one-run amnesty to an already-regressed population.
    """
    floor = HEALTH_MIN_MATCHES.get(tour, 0)
    previous = prev or {}
    high = previous.get("high_water_matches")
    high_version = previous.get("high_water_match_population_version")
    if not (_plain_int(high) and high >= floor and _plain_int(high_version)):
        high = previous.get("matches")
        high_version = previous.get("match_population_version")
        if not (_plain_int(high) and high >= floor and _plain_int(high_version)):
            high, high_version = None, None

    current = meta.get("matches")
    current_version = meta.get("matchPopulationVersion")
    model_version = meta.get("modelPopulationVersion")
    current_valid = (
        _plain_int(current) and current >= floor
        and _plain_int(current_version) and _plain_int(model_version)
        and current_version == MATCH_POPULATION_VERSION
        and model_version == current_version
    )
    if not current_valid:
        return high, high_version
    if high is None or high_version != current_version:
        return current, current_version
    return max(high, current), current_version


def _forecast_high_water(current: object, prev: dict | None) -> int | None:
    """Durable append-only forecast-log baseline, seeded from legacy report state."""
    previous = prev or {}
    high = previous.get("forecast_high_water_lines")
    if not (_plain_int(high) and high >= 0):
        legacy = previous.get("forecast_lines")
        high = legacy if _plain_int(legacy) and legacy >= 0 else None
    if _plain_int(current) and current >= 0:
        return current if high is None else max(high, current)
    return high


# players.json enrichment fields that must be valid probabilities when present
_PLAYER_PCT_FIELDS = ("winRate10",
                      "servePctHard", "servePctClay", "servePctGrass",
                      "returnPctHard", "returnPctClay", "returnPctGrass")


def _pow2(n) -> bool:
    return isinstance(n, int) and n >= 2 and (n & (n - 1)) == 0


# Standard bye-carrying draw sizes: 28 (32-bracket, 4 byes — most ATP/WTA 250/500s),
# 24 (32-bracket, 8 byes), 48/56 (64-bracket Masters/500s), 96 (128-bracket IW/Miami/
# Madrid/Rome). The wiki bracket parser guarantees the SLOTS are a power of two
# (draws_wiki._parse_bracket); drawSize counts entrants, so byes make it one of these.
_BYE_DRAW_SIZES = frozenset({24, 28, 48, 56, 96})
_DRAW_SOURCE_HOSTS = {
    "atp": "www.protennislive.com",
    "wta": "wtafiles.wtatennis.com",
    "wikipedia": "en.wikipedia.org",
}


def _real_draw_size_ok(n) -> bool:
    return _pow2(n) or n in _BYE_DRAW_SIZES


def _age_days(iso, now: pd.Timestamp):
    ts = pd.to_datetime(iso, utc=True, errors="coerce") if iso else pd.NaT
    if pd.isna(ts):
        return None
    now_utc = now if now.tzinfo else now.tz_localize("UTC")
    return int((now_utc - ts).days)


def _flag_placeholders(out: list, tour: str, where: str, names, *, entity: str,
                       allow_numbered: bool = False) -> None:
    bad: set[str] = set()
    for name in names:
        if not isinstance(name, str):
            continue
        participant = classify_participant(name)
        if participant.is_real:
            continue
        if allow_numbered and participant.is_numbered_placeholder:
            continue
        bad.add(name)
    ordered = sorted(bad)
    if ordered:
        _add_finding(
            out, "output.participant.placeholder_name",
            f"{tour}: {where} contains placeholder name(s) {ordered}",
            severity="error", entity=entity,
            evidence={"where": where, "names": ordered})


def _check_matrix(out: list, tour: str, mx: dict) -> None:
    players = mx.get("players") or []
    n = len(players)
    for surf, byfmt in (mx.get("surfaces") or {}).items():
        if not isinstance(byfmt, dict):
            continue
        for fmt, m in byfmt.items():
            if (not isinstance(m, list) or len(m) != n
                    or any(not isinstance(r, list) or len(r) != n for r in m)):
                _add_finding(
                    out, "output.matrix.geometry_invalid",
                    f"{tour}: matrix[{surf}][{fmt}] is not {n}x{n}",
                    severity="error", entity=f"matrix:{surf}:{fmt}",
                    evidence={"surface": str(surf), "format": str(fmt),
                              "expectedSize": n})
                continue
            if n == 0:
                _add_finding(
                    out, "output.matrix.roster_empty",
                    f"{tour}: matrix[{surf}][{fmt}] has no players",
                    severity="error", entity=f"matrix:{surf}:{fmt}",
                    evidence={"surface": str(surf), "format": str(fmt)})
                continue
            # sample corners + the top-left 2x2 — enough to catch a systemic break
            # (all-out-of-range, transposed, un-normalised) without scanning ~14k cells
            for i, j in {(0, 0), (0, min(1, n - 1)), (n - 1, 0), (n - 1, n - 1)}:
                if not _is_prob(m[i][j]):
                    _add_finding(
                        out, "output.matrix.probability_invalid",
                        f"{tour}: matrix[{surf}][{fmt}][{i}][{j}]={m[i][j]!r} out of [0,1]",
                        severity="error", entity=f"matrix:{surf}:{fmt}:{i}:{j}",
                        evidence={"surface": str(surf), "format": str(fmt),
                                  "row": i, "column": j, "value": repr(m[i][j])})
            if n >= 2:
                if abs(m[0][0] - 0.5) > 1e-6:
                    _add_finding(
                        out, "output.matrix.diagonal_invalid",
                        f"{tour}: matrix[{surf}][{fmt}] diagonal != 0.5 ({m[0][0]})",
                        severity="error", entity=f"matrix:{surf}:{fmt}",
                        evidence={"surface": str(surf), "format": str(fmt),
                                  "value": float(m[0][0])})
                if abs(m[0][1] + m[1][0] - 1.0) > 1e-3:
                    _add_finding(
                        out, "output.matrix.antisymmetry_invalid",
                        f"{tour}: matrix[{surf}][{fmt}] not antisymmetric "
                        f"({m[0][1]}+{m[1][0]})",
                        severity="error", entity=f"matrix:{surf}:{fmt}",
                        evidence={"surface": str(surf), "format": str(fmt),
                                  "forward": float(m[0][1]), "reverse": float(m[1][0])})


def _check_matrix_shards(out: list, tour: str, index: dict, shards: dict) -> None:
    players = index.get("players")
    generation = index.get("generation")
    expected_components = {"eloBlend", "pointModel", "combiner"}
    if not generation:
        _add_finding(
            out, "output.matrix_index.generation_missing",
            f"{tour}: matrix-index.json is missing generation",
            severity="error", entity="artifact:matrix-index.json", evidence={})
    if not isinstance(players, list) or not players or any(not p for p in players):
        _add_finding(
            out, "output.matrix_index.roster_invalid",
            f"{tour}: matrix-index.json has an empty/malformed player roster",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"valueType": type(players).__name__})
        players = players if isinstance(players, list) else []
    elif len(set(players)) != len(players):
        _add_finding(
            out, "output.matrix_index.roster_duplicate",
            f"{tour}: matrix-index.json has duplicate players",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"players": len(players), "uniquePlayers": len(set(players))})
    formats = index.get("formats")
    if not isinstance(formats, list) or not formats:
        _add_finding(
            out, "output.matrix_index.formats_invalid",
            f"{tour}: matrix-index.json has no formats",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"valueType": type(formats).__name__})
    surfaces = index.get("surfaces")
    if not isinstance(surfaces, dict) or not surfaces:
        # Avoid the generic advisory marker "is empty": a shard index with no context
        # makes the predictor unusable and must block, unlike a quiet schedule feed.
        _add_finding(
            out, "output.matrix_index.surfaces_invalid",
            f"{tour}: matrix-index.json surfaces is missing/malformed",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"valueType": type(surfaces).__name__})
        return
    for surface, byfmt in surfaces.items():
        if not isinstance(byfmt, dict):
            _add_finding(
                out, "output.matrix_index.format_map_invalid",
                f"{tour}: matrix-index {surface!r} format map is malformed",
                severity="error", entity=f"matrix-index:{surface}",
                evidence={"surface": str(surface), "valueType": type(byfmt).__name__})
            continue
        for fmt, filename in byfmt.items():
            shard = shards.get(filename)
            if not isinstance(shard, dict):
                continue  # missing/corrupt has its own exact-file problem
            if shard.get("generation") != generation:
                _add_finding(
                    out, "output.matrix_shard.generation_mismatch",
                    f"{tour}: {filename} generation disagrees with matrix-index.json",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"expected": generation, "actual": shard.get("generation")})
            if shard.get("players") != players:
                _add_finding(
                    out, "output.matrix_shard.roster_mismatch",
                    f"{tour}: {filename} player order disagrees with matrix-index.json",
                    severity="error", entity=f"artifact:{filename}", evidence={})
            if shard.get("surface") != surface or str(shard.get("bestOf")) != str(fmt):
                _add_finding(
                    out, "output.matrix_shard.context_mismatch",
                    f"{tour}: {filename} context disagrees with matrix-index.json",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"expectedSurface": str(surface), "expectedBestOf": str(fmt),
                              "actualSurface": shard.get("surface"),
                              "actualBestOf": shard.get("bestOf")})
            components = shard.get("components")
            if not isinstance(components, dict):
                _add_finding(
                    out, "output.matrix_shard.components_invalid",
                    f"{tour}: {filename} components is malformed",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"valueType": type(components).__name__})
                continue
            if set(components) != expected_components:
                _add_finding(
                    out, "output.matrix_shard.component_set_mismatch",
                    f"{tour}: {filename} component set {sorted(components)} "
                    f"!= {sorted(expected_components)}",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"actual": sorted(components),
                              "expected": sorted(expected_components)})
            for component, matrix in components.items():
                _check_matrix(out, tour, {
                    "players": players,
                    "surfaces": {surface: {f"{fmt}/{component}": matrix}},
                })
            _check_matrix_evidence(out, tour, str(filename), shard.get("evidence"), len(players))


def _square_matrix(value: object, n: int) -> bool:
    return (isinstance(value, list) and len(value) == n
            and all(isinstance(row, list) and len(row) == n for row in value))


def _finite_between(value: object, low: float, high: float) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and low <= float(value) <= high)


def _check_matrix_evidence(out: list, tour: str, filename: str,
                           evidence: object, n: int) -> None:
    """Arbitrary-pair evidence must share the matrix roster and signed orientation."""
    if not isinstance(evidence, dict) or evidence.get("schema") != "evidence-v1":
        _add_finding(
            out, "output.matrix_evidence.payload_invalid",
            f"{tour}: {filename} evidence-v1 payload is missing/malformed",
            severity="error", entity=f"artifact:{filename}",
            evidence={"valueType": type(evidence).__name__})
        return
    effects = evidence.get("effects")
    if not isinstance(effects, dict) or set(effects) != set(_EVIDENCE_KEYS):
        _add_finding(
            out, "output.matrix_evidence.signal_set_invalid",
            f"{tour}: {filename} evidence signal set is malformed",
            severity="error", entity=f"artifact:{filename}",
            evidence={"expected": sorted(_EVIDENCE_KEYS),
                      "actual": sorted(map(str, effects)) if isinstance(effects, dict) else None})
        return
    packed = evidence.get("encoding") == "upper-triangle-bps-v1"
    packed_size = n * (n - 1) // 2
    for key, matrix in effects.items():
        if packed:
            if (not isinstance(matrix, list) or len(matrix) != packed_size
                    or any(not isinstance(value, int) or isinstance(value, bool)
                           or not -10_000 <= value <= 10_000 for value in matrix)):
                _add_finding(
                    out, "output.matrix_evidence.packed_signal_invalid",
                    f"{tour}: {filename} packed evidence[{key}] is malformed",
                    severity="error", entity=f"artifact:{filename}#signal:{key}",
                    evidence={"signal": str(key), "expectedSize": packed_size})
            continue
        if not _square_matrix(matrix, n):
            _add_finding(
                out, "output.matrix_evidence.geometry_invalid",
                f"{tour}: {filename} evidence[{key}] is not {n}x{n}",
                severity="error", entity=f"artifact:{filename}#signal:{key}",
                evidence={"signal": str(key), "expectedSize": n})
            continue
        bad = False
        for i in range(n):
            if not _finite_between(matrix[i][i], 0.0, 0.0):
                bad = True
                break
            for j in range(i + 1, n):
                if (not _finite_between(matrix[i][j], -1.0, 1.0)
                        or not _finite_between(matrix[j][i], -1.0, 1.0)
                        or abs(float(matrix[i][j]) + float(matrix[j][i])) > 2e-4):
                    bad = True
                    break
            if bad:
                break
        if bad:
            _add_finding(
                out, "output.matrix_evidence.antisymmetry_invalid",
                f"{tour}: {filename} evidence[{key}] is non-finite/non-antisymmetric",
                severity="error", entity=f"artifact:{filename}#signal:{key}",
                evidence={"signal": str(key)})
    available = evidence.get("available")
    if not isinstance(available, dict) or set(available) != {"h2h", "style"}:
        _add_finding(
            out, "output.matrix_evidence.availability_invalid",
            f"{tour}: {filename} conditional evidence availability is malformed",
            severity="error", entity=f"artifact:{filename}", evidence={})
    else:
        for key, matrix in available.items():
            if packed:
                valid = (isinstance(matrix, list) and len(matrix) == packed_size
                         and all(value in (0, 1) for value in matrix))
            else:
                valid = (_square_matrix(matrix, n) and all(
                    value in (0, 1) for row in matrix for value in row))
            if not valid:
                _add_finding(
                    out, "output.matrix_evidence.availability_signal_invalid",
                    f"{tour}: {filename} evidence availability[{key}] is malformed",
                    severity="error", entity=f"artifact:{filename}#availability:{key}",
                    evidence={"signal": str(key)})
    if evidence.get("homeAvailable") is not False:
        _add_finding(
            out, "output.matrix_evidence.home_context_invalid",
            f"{tour}: {filename} generic matchup evidence claims home context",
            severity="error", entity=f"artifact:{filename}",
            evidence={"homeAvailable": repr(evidence.get("homeAvailable"))})


def _check_prediction_evidence(out: list, tour: str, label: str, evidence: object,
                               player_a: object = None, player_b: object = None,
                               probability_a: object = None, *, entity: str | None = None) -> None:
    """Validate the seven grouped signals and their explicit non-causal contract."""
    finding_entity = entity or _match_entity(
        {}, player_a=player_a, player_b=player_b)
    if not isinstance(evidence, dict) or evidence.get("schema") != "evidence-v1":
        _add_finding(
            out, "output.prediction_evidence.payload_invalid",
            f"{tour}: {label} prediction evidence is missing/malformed",
            severity="error", entity=finding_entity,
            evidence={"valueType": type(evidence).__name__})
        return
    a, b = evidence.get("playerA"), evidence.get("playerB")
    if player_a is not None and (a != player_a or b != player_b):
        _add_finding(
            out, "output.prediction_evidence.orientation_mismatch",
            f"{tour}: {label} evidence orientation disagrees with matchup",
            severity="error", entity=finding_entity,
            evidence={"expectedPlayerA": repr(player_a), "expectedPlayerB": repr(player_b),
                      "actualPlayerA": repr(a), "actualPlayerB": repr(b)})
    if not _is_prob(evidence.get("probabilityA")):
        _add_finding(
            out, "output.prediction_evidence.probability_invalid",
            f"{tour}: {label} evidence probability is outside [0,1]",
            severity="error", entity=finding_entity,
            evidence={"value": repr(evidence.get("probabilityA"))})
    elif _is_prob(probability_a) and abs(float(evidence["probabilityA"]) - float(probability_a)) > 1e-4:
        _add_finding(
            out, "output.prediction_evidence.probability_mismatch",
            f"{tour}: {label} evidence probability disagrees with published call",
            severity="error", entity=finding_entity,
            evidence={"evidenceProbability": float(evidence["probabilityA"]),
                      "publishedProbability": float(probability_a)})
    note = str(evidence.get("note") or "").lower()
    if "evidence" not in note or "not causation" not in note:
        _add_finding(
            out, "output.prediction_evidence.disclaimer_missing",
            f"{tour}: {label} evidence omits the non-causal disclaimer",
            severity="error", entity=finding_entity, evidence={})
    signals = evidence.get("signals")
    if not isinstance(signals, list) or len(signals) != len(_EVIDENCE_KEYS):
        _add_finding(
            out, "output.prediction_evidence.signal_list_invalid",
            f"{tour}: {label} evidence signal list is malformed",
            severity="error", entity=finding_entity,
            evidence={"expectedCount": len(_EVIDENCE_KEYS),
                      "actualCount": len(signals) if isinstance(signals, list) else None})
        return
    keys = [signal.get("key") for signal in signals if isinstance(signal, dict)]
    if len(keys) != len(signals) or set(keys) != set(_EVIDENCE_KEYS):
        _add_finding(
            out, "output.prediction_evidence.signal_keys_invalid",
            f"{tour}: {label} evidence signal keys are missing/duplicated",
            severity="error", entity=finding_entity,
            evidence={"expected": sorted(_EVIDENCE_KEYS), "actual": list(map(str, keys))})
        return
    available_strengths = []
    unavailable_seen = False
    for signal in signals:
        available = signal.get("available")
        impact = signal.get("impactPp")
        supports = signal.get("supports")
        if not isinstance(available, bool) or not _finite_between(impact, -100.0, 100.0):
            _add_finding(
                out, "output.prediction_evidence.signal_value_invalid",
                f"{tour}: {label} evidence signal {signal.get('key')} has invalid availability/impact",
                severity="error", entity=f"{finding_entity}#signal:{signal.get('key')}",
                evidence={"signal": str(signal.get("key")), "available": repr(available),
                          "impactPp": repr(impact)})
        if supports not in (None, a, b):
            _add_finding(
                out, "output.prediction_evidence.support_unknown",
                f"{tour}: {label} evidence signal {signal.get('key')} supports an unknown player",
                severity="error", entity=f"{finding_entity}#signal:{signal.get('key')}",
                evidence={"signal": str(signal.get("key")), "supports": repr(supports)})
        if not isinstance(signal.get("facts"), dict):
            _add_finding(
                out, "output.prediction_evidence.facts_invalid",
                f"{tour}: {label} evidence signal {signal.get('key')} facts are malformed",
                severity="error", entity=f"{finding_entity}#signal:{signal.get('key')}",
                evidence={"signal": str(signal.get("key"))})
        if available:
            if unavailable_seen:
                _add_finding(
                    out, "output.prediction_evidence.availability_order_invalid",
                    f"{tour}: {label} strongest evidence is not ranked before unavailable signals",
                    severity="error", entity=finding_entity, evidence={})
            if _finite_between(impact, -100.0, 100.0):
                available_strengths.append(abs(float(impact)))
        else:
            unavailable_seen = True
    if available_strengths != sorted(available_strengths, reverse=True):
        _add_finding(
            out, "output.prediction_evidence.strength_order_invalid",
            f"{tour}: {label} available evidence is not strongest-first",
            severity="error", entity=finding_entity,
            evidence={"strengths": available_strengths})


def _check_profile_shards(out: list, tour: str, index: dict, shards: dict,
                          players: list | None) -> None:
    rows = index.get("profiles") or []
    if not isinstance(rows, list):
        _add_finding(
            out, "output.profile_index.roster_invalid",
            f"{tour}: profile-index.json profiles is not a list",
            severity="error", entity="artifact:profile-index.json",
            evidence={"valueType": type(rows).__name__})
        return
    names = [p.get("name") for p in rows if isinstance(p, dict)]
    files = [p.get("file") for p in rows if isinstance(p, dict)]
    if len(set(names)) != len(names) or any(not name for name in names):
        _add_finding(
            out, "output.profile_index.player_identity_invalid",
            f"{tour}: profile-index.json has duplicate/null player names",
            severity="error", entity="artifact:profile-index.json",
            evidence={"rows": len(rows), "uniqueNames": len(set(names))})
    if len(set(files)) != len(files) or any(not filename for filename in files):
        _add_finding(
            out, "output.profile_index.shard_identity_invalid",
            f"{tour}: profile-index.json has duplicate/null shard files",
            severity="error", entity="artifact:profile-index.json",
            evidence={"rows": len(rows), "uniqueFiles": len(set(files))})
    if isinstance(players, list) and names != [p.get("name") for p in players]:
        _add_finding(
            out, "output.profile_index.roster_mismatch",
            f"{tour}: profile-index.json roster/order disagrees with players.json",
            severity="error", entity="artifact:profile-index.json", evidence={})
    generation = index.get("generation")
    if not generation:
        _add_finding(
            out, "output.profile_index.generation_missing",
            f"{tour}: profile-index.json is missing generation",
            severity="error", entity="artifact:profile-index.json", evidence={})
    for summary in rows:
        if not isinstance(summary, dict):
            continue
        filename = summary.get("file")
        shard = shards.get(filename)
        if not isinstance(shard, dict):
            continue
        if shard.get("generation") != generation:
            _add_finding(
                out, "output.profile_shard.generation_mismatch",
                f"{tour}: {filename} generation disagrees with profile-index.json",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": generation, "actual": shard.get("generation")})
        if shard.get("name") != summary.get("name"):
            _add_finding(
                out, "output.profile_shard.player_mismatch",
                f"{tour}: {filename} names {shard.get('name')!r}, expected "
                f"{summary.get('name')!r}",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": repr(summary.get("name")),
                          "actual": repr(shard.get("name"))})


def _check_forecast_history(out: list, tour: str, label: str, forecast: object,
                            current: object | None = None, *, entity: str | None = None) -> None:
    """A visible timeline must be ordered, de-duplicated, and agree with its summary."""
    if not isinstance(forecast, dict):
        return
    finding_entity = entity or _match_entity(
        forecast,
        player_a=forecast.get("playerA"),
        player_b=forecast.get("playerB"),
    )
    timeline = forecast.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        _add_finding(
            out, "output.forecast.timeline_missing",
            f"{tour}: {label} forecast timeline is missing/empty",
            severity="error", entity=finding_entity,
            evidence={"valueType": type(timeline).__name__})
        return
    points = [point for point in timeline if isinstance(point, dict)]
    stamps = [str(point.get("asOf") or "") for point in points]
    hours = [stamp[:13] for stamp in stamps]
    generations: list[str] = []
    invalid_generations: list[dict] = []
    for index, point in enumerate(points):
        raw_generation = point.get("predictorArtifactId")
        if raw_generation is None:
            generations.append("legacy")
        elif isinstance(raw_generation, str) and _UUID4_RE.fullmatch(raw_generation):
            generations.append(raw_generation)
        else:
            generations.append(f"invalid:{index}")
            invalid_generations.append({
                "index": index,
                "value": repr(raw_generation),
            })
    generation_keys = list(zip(hours, generations, strict=True))
    if len(stamps) != len(timeline) or any(not stamp for stamp in stamps):
        _add_finding(
            out, "output.forecast.timestamp_missing",
            f"{tour}: {label} forecast timeline has a missing timestamp",
            severity="error", entity=finding_entity,
            evidence={"observations": len(timeline), "timestamps": len(stamps)})
    elif stamps != sorted(stamps) or len(generation_keys) != len(set(generation_keys)):
        _add_finding(
            out, "output.forecast.timeline_order_invalid",
            f"{tour}: {label} forecast timeline is unordered or repeats one predictor "
            "generation within a UTC hour",
            severity="error", entity=finding_entity,
            evidence={"timestamps": stamps, "predictorArtifactIds": generations})
    if invalid_generations:
        _add_finding(
            out, "output.forecast.predictor_generation_invalid",
            f"{tour}: {label} forecast timeline has an invalid predictor generation",
            severity="error", entity=finding_entity,
            evidence={"values": invalid_generations})
    probs = [point.get("p") for point in timeline if isinstance(point, dict)]
    if any(not _is_prob(p) for p in probs):
        _add_finding(
            out, "output.forecast.probability_invalid",
            f"{tour}: {label} forecast timeline has probability outside [0,1]",
            severity="error", entity=finding_entity,
            evidence={"values": [repr(p) for p in probs if not _is_prob(p)]})
        return
    if forecast.get("snapshots") != len(timeline):
        _add_finding(
            out, "output.forecast.snapshot_count_mismatch",
            f"{tour}: {label} forecast snapshots={forecast.get('snapshots')!r} "
            f"but timeline has {len(timeline)} observations",
            severity="error", entity=finding_entity,
            evidence={"declared": repr(forecast.get("snapshots")),
                      "actual": len(timeline)})
    if probs and isinstance(forecast.get("first"), (int, float)) \
            and abs(float(forecast["first"]) - float(probs[0])) > 1e-4:
        _add_finding(
            out, "output.forecast.first_probability_mismatch",
            f"{tour}: {label} forecast first disagrees with timeline",
            severity="error", entity=finding_entity,
            evidence={"summary": float(forecast["first"]), "timeline": float(probs[0])})
    expected_current = current if _is_prob(current) else forecast.get("current")
    if probs and _is_prob(expected_current) and abs(float(expected_current) - float(probs[-1])) > 1e-4:
        _add_finding(
            out, "output.forecast.current_probability_mismatch",
            f"{tour}: {label} current probability disagrees with latest saved observation",
            severity="error", entity=finding_entity,
            evidence={"summary": float(expected_current), "timeline": float(probs[-1])})
    if _is_prob(forecast.get("first")) and _is_prob(forecast.get("current")):
        delta = float(forecast["current"]) - float(forecast["first"])
        if not isinstance(forecast.get("delta"), (int, float)) or abs(delta - float(forecast["delta"])) > 1e-4:
            _add_finding(
                out, "output.forecast.delta_mismatch",
                f"{tour}: {label} forecast delta disagrees with first/current",
                severity="error", entity=finding_entity,
                evidence={"expected": delta, "actual": repr(forecast.get("delta"))})
    for index, point in enumerate(timeline):
        if isinstance(point, dict) and point.get("evidence") is not None:
            evidence = point["evidence"]
            _check_prediction_evidence(
                out, tour, f"{label} timeline point {index}", evidence,
                evidence.get("playerA") if isinstance(evidence, dict) else None,
                evidence.get("playerB") if isinstance(evidence, dict) else None,
                point.get("p"),
                entity=finding_entity,
            )


def _check_performance(out: list, tour: str, performance: dict, profile_index: object,
                       shards: dict) -> None:
    rows, window = performance.get("players"), performance.get("window")
    if not isinstance(rows, list) or not isinstance(window, int) or window < 1:
        _add_finding(
            out, "output.performance.contract_invalid",
            f"{tour}: performance.json players/window is malformed",
            severity="error", entity="artifact:performance.json",
            evidence={"playersType": type(rows).__name__, "window": repr(window)})
        return
    names = [row.get("name") for row in rows if isinstance(row, dict)]
    if len(names) != len(rows) or len(names) != len(set(names)) or any(not name for name in names):
        _add_finding(
            out, "output.performance.player_identity_invalid",
            f"{tour}: performance.json has malformed/duplicate player names",
            severity="error", entity="artifact:performance.json",
            evidence={"rows": len(rows), "names": len(names),
                      "uniqueNames": len(set(names))})
    by_name = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name, n, wins, expected, delta = (row.get(k) for k in
                                          ("name", "n", "wins", "expectedWins", "delta"))
        if not (isinstance(n, int) and 0 <= n <= window and isinstance(wins, int)
                and 0 <= wins <= n and isinstance(expected, (int, float)) and 0 <= expected <= n
                and isinstance(delta, (int, float)) and abs(float(delta) - (wins - float(expected))) <= 0.002):
            _add_finding(
                out, "output.performance.summary_invalid",
                f"{tour}: performance.json summary for {name!r} is inconsistent",
                severity="error", entity=f"player:{_player_identity_key(name)}",
                evidence={"n": repr(n), "wins": repr(wins),
                          "expectedWins": repr(expected), "delta": repr(delta),
                          "window": window})
            continue
        by_name[name] = row
    if not isinstance(profile_index, dict):
        return
    for summary in profile_index.get("profiles") or []:
        if not isinstance(summary, dict):
            continue
        perf = by_name.get(summary.get("name"))
        shipped_summary = summary.get("performance")
        expected_summary = ({k: perf.get(k) for k in ("n", "wins", "expectedWins", "delta")}
                            if perf else None)
        if shipped_summary != expected_summary:
            _add_finding(
                out, "output.performance.profile_summary_mismatch",
                f"{tour}: profile expectation summary disagrees for {summary.get('name')!r}",
                severity="error", entity=f"player:{_player_identity_key(summary.get('name'))}",
                evidence={"expected": expected_summary,
                          "actual": shipped_summary if isinstance(shipped_summary, dict)
                          else repr(shipped_summary)})
        detail = shards.get(summary.get("file"))
        if not isinstance(detail, dict):
            continue
        detail_perf = detail.get("performance")
        if not perf:
            if detail_perf is not None:
                _add_finding(
                    out, "output.performance.orphan_profile_detail",
                    f"{tour}: profile expectation detail exists without summary for "
                    f"{summary.get('name')!r}",
                    severity="error",
                    entity=f"player:{_player_identity_key(summary.get('name'))}", evidence={})
            continue
        if not isinstance(detail_perf, dict):
            _add_finding(
                out, "output.performance.profile_detail_missing",
                f"{tour}: profile expectation detail missing for {summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}", evidence={})
            continue
        if any(detail_perf.get(k) != perf.get(k) for k in ("n", "wins", "expectedWins", "delta")):
            _add_finding(
                out, "output.performance.profile_detail_mismatch",
                f"{tour}: profile expectation detail disagrees for {summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}", evidence={})
        decisions = detail_perf.get("recent")
        if not isinstance(decisions, list) or len(decisions) != perf["n"]:
            _add_finding(
                out, "output.performance.evidence_count_mismatch",
                f"{tour}: profile expectation evidence count disagrees for {summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}",
                evidence={"expected": perf["n"],
                          "actual": len(decisions) if isinstance(decisions, list) else None})
            continue
        ids = [decision.get("matchId") for decision in decisions if isinstance(decision, dict)]
        if len(ids) != len(set(ids)) or any(not str(match_id).startswith("v2|") for match_id in ids):
            _add_finding(
                out, "output.performance.match_identity_invalid",
                f"{tour}: profile expectation evidence has duplicate/legacy match IDs for "
                f"{summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}",
                evidence={"matchIds": list(map(str, ids))})
        for decision in decisions:
            if not isinstance(decision, dict) or not _is_prob(decision.get("p")):
                _add_finding(
                    out, "output.performance.probability_invalid",
                    f"{tour}: profile expectation evidence probability is invalid",
                    severity="error",
                    entity=f"player:{_player_identity_key(summary.get('name'))}",
                    evidence={"value": repr(decision.get("p"))
                              if isinstance(decision, dict) else repr(decision)})
                break
            expected_residual = (1.0 if decision.get("won") is True else 0.0) - decision["p"]
            if not isinstance(decision.get("residual"), (int, float)) \
                    or abs(expected_residual - decision["residual"]) > 1e-4:
                _add_finding(
                    out, "output.performance.residual_invalid",
                    f"{tour}: profile expectation residual is inconsistent",
                    severity="error",
                    entity=_match_entity(
                        decision,
                        player_a=summary.get("name"),
                        player_b=decision.get("opponent"),
                    ),
                    evidence={"expected": expected_residual,
                              "actual": repr(decision.get("residual"))})
                break


def _check_scenarios(out: list, tour: str, index: dict, shards: dict,
                     brackets: object) -> None:
    from ..sim.exact import propagate_rounds, validate_matrix
    from ..sim.scenarios import exact_bracket

    generation = index.get("generation")
    if (index.get("schema") != "scenario-v1" or index.get("schemaVersion") != 1
            or not generation or not isinstance(index.get("events"), list)):
        _add_finding(
            out, "output.scenario_index.contract_invalid",
            f"{tour}: scenario-index.json schema/events is malformed",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"schema": repr(index.get("schema")),
                      "schemaVersion": repr(index.get("schemaVersion")),
                      "generation": repr(generation),
                      "eventsType": type(index.get("events")).__name__})
        return
    refs_by_file = {
        entry.get("file"): entry for entry in index["events"] if isinstance(entry, dict)
    }
    refs = set(refs_by_file)
    event_ids = [str(entry.get("espnId") or "") for entry in index["events"]
                 if isinstance(entry, dict)]
    if (len(refs) != len(index["events"]) or None in refs
            or len(event_ids) != len(set(event_ids)) or any(not event_id for event_id in event_ids)):
        _add_finding(
            out, "output.scenario_index.shard_identity_invalid",
            f"{tour}: scenario-index.json repeats or omits shard files",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"events": len(index["events"]), "uniqueFiles": len(refs),
                      "eventIds": event_ids})
    if any(entry.get("generation") != generation for entry in refs_by_file.values()):
        _add_finding(
            out, "output.scenario_index.generation_mismatch",
            f"{tour}: scenario-index.json event generation is inconsistent",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"generation": generation})
    bracket_refs = {
        ((event.get("scenario") or {}).get("file") or event.get("scenarioFile"))
        for event in (brackets or []) if isinstance(event, dict)
        and event.get("status") in ("live", "upcoming")
        and ((event.get("scenario") or {}).get("file") or event.get("scenarioFile"))
    }
    if bracket_refs != refs:
        _add_finding(
            out, "output.scenario_index.bracket_reference_mismatch",
            f"{tour}: scenario-index.json files disagree with unsettled brackets",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"indexFiles": sorted(map(str, refs)),
                      "bracketFiles": sorted(map(str, bracket_refs))})
    for filename in refs:
        shard = shards.get(filename)
        if not isinstance(shard, dict):
            continue
        ref = refs_by_file[filename]
        players, matrices, rounds = shard.get("players"), shard.get("matrices"), shard.get("rounds")
        event = shard.get("event") or {}
        event_id = str(event.get("espnId") or "")
        if (shard.get("schema") != "scenario-v1" or shard.get("schemaVersion") != 1
                or shard.get("generation") != generation
                or event_id != str(ref.get("espnId") or "")
                or shard.get("modelGeneration") != ref.get("modelGeneration")
                or not isinstance(players, list) or len(set(players)) != len(players) \
                or not isinstance(matrices, dict) or not isinstance(rounds, list) or not rounds):
            _add_finding(
                out, "output.scenario_shard.contract_invalid",
                f"{tour}: {filename} scenario structure is malformed",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expectedEspnId": str(ref.get("espnId") or ""),
                          "actualEspnId": event_id})
            continue
        n = len(players)
        bad_matrix = False
        for component in ("eloBlend", "pointModel", "combiner"):
            matrix = matrices.get(component)
            if not _square_matrix(matrix, n):
                bad_matrix = True
                break
            for i in range(n):
                for j in range(n):
                    if (not _is_prob(matrix[i][j])
                            or abs(float(matrix[i][j]) + float(matrix[j][i]) - 1.0) > 2e-5):
                        bad_matrix = True
                        break
        if bad_matrix:
            _add_finding(
                out, "output.scenario_shard.matrix_invalid",
                f"{tour}: {filename} scenario matrices are malformed/non-antisymmetric",
                severity="error", entity=f"artifact:{filename}",
                evidence={"players": n})
            continue
        if shard.get("matrix") != matrices["combiner"]:
            _add_finding(
                out, "output.scenario_shard.authoritative_matrix_mismatch",
                f"{tour}: {filename} authoritative matrix disagrees with combiner",
                severity="error", entity=f"artifact:{filename}", evidence={})
            continue
        try:
            validate_matrix(players, shard["matrix"], atol=2e-5)
            expected_baseline = propagate_rounds(
                rounds, players, shard["matrix"], event_id=event_id)
        except (TypeError, ValueError) as exc:
            _add_finding(
                out, "output.scenario_shard.exact_contract_invalid",
                f"{tour}: {filename} exact scenario contract failed ({exc})",
                severity="error", entity=f"artifact:{filename}",
                evidence={"failureType": type(exc).__name__})
            continue
        if shard.get("baseline") != expected_baseline:
            _add_finding(
                out, "output.scenario_shard.baseline_mismatch",
                f"{tour}: {filename} baseline disagrees with exact propagation",
                severity="error", entity=f"artifact:{filename}", evidence={})
        expected_legacy = exact_bracket(rounds, players, matrices["combiner"])
        if shard.get("base") != expected_legacy:
            _add_finding(
                out, "output.scenario_shard.base_forecast_mismatch",
                f"{tour}: {filename} base forecast disagrees with exact propagation",
                severity="error", entity=f"artifact:{filename}", evidence={})
        geometry = shard.get("geometry")
        expected_ids = [match["id"] for rnd in expected_baseline["rounds"] for match in rnd["matches"]]
        geometry_ids = [match.get("id") for rnd in geometry or []
                        for match in (rnd.get("matches") or []) if isinstance(match, dict)]
        if not isinstance(geometry, list) or geometry_ids != expected_ids:
            _add_finding(
                out, "output.scenario_shard.geometry_invalid",
                f"{tour}: {filename} stable match geometry is malformed",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expectedMatchIds": expected_ids,
                          "actualMatchIds": list(map(str, geometry_ids))})
        lockable = set(expected_baseline["lockableMatchIds"])
        if ref.get("lockableMatches") != len(lockable):
            _add_finding(
                out, "output.scenario_shard.lockable_count_mismatch",
                f"{tour}: {filename} lockable-match count disagrees with scenario index",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": len(lockable), "actual": ref.get("lockableMatches")})
        leverage = shard.get("titleLeverage")
        if not isinstance(leverage, dict) or set(leverage) != lockable:
            _add_finding(
                out, "output.scenario_shard.title_leverage_keys_mismatch",
                f"{tour}: {filename} title-leverage keys disagree with real unresolved matches",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": sorted(map(str, lockable)),
                          "actual": sorted(map(str, leverage))
                          if isinstance(leverage, dict) else None})
        else:
            for match_id, row in leverage.items():
                if (not isinstance(row, dict) or not _is_prob(row.get("value"))
                        or not row.get("playerA") or not row.get("playerB")):
                    _add_finding(
                        out, "output.scenario_shard.title_leverage_invalid",
                        f"{tour}: {filename} title leverage {match_id} is malformed",
                        severity="error", entity=f"match:{match_id}",
                        evidence={"artifact": str(filename)})
                    break


def _check_upcoming_shards(out: list, tour: str, index: dict, shards: dict) -> None:
    """Validate the lazy upcoming graph before reconstructed rows reach existing checks."""
    generation = index.get("generation")
    events = index.get("events")
    highlights = index.get("highlights")
    if (index.get("schema") != "upcoming-v2" or index.get("schemaVersion") != 2
            or not generation or not isinstance(events, list)
            or not isinstance(highlights, list)
            or not isinstance(index.get("count"), int)):
        _add_finding(
            out, "output.upcoming_index.contract_invalid",
            f"{tour}: upcoming-index.json schema/events is malformed",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"schema": repr(index.get("schema")),
                      "schemaVersion": repr(index.get("schemaVersion")),
                      "generation": repr(generation)})
        return

    event_files, evidence_files, event_keys = [], [], []
    base_ids: list[str] = []
    total = 0
    for ref in events:
        if not isinstance(ref, dict):
            _add_finding(
                out, "output.upcoming_index.event_reference_invalid",
                f"{tour}: upcoming-index.json contains a malformed event reference",
                severity="error", entity="artifact:upcoming-index.json",
                evidence={"value": repr(ref)})
            continue
        event_file, evidence_file = ref.get("file"), ref.get("evidenceFile")
        event_files.append(event_file)
        evidence_files.append(evidence_file)
        event_id = str(ref.get("espnId") or "").strip()
        event_keys.append(("id", event_id) if event_id else ("name", str(ref.get("name") or "")))
        event_shard, evidence_shard = shards.get(event_file), shards.get(evidence_file)
        if not isinstance(event_shard, dict) or not isinstance(evidence_shard, dict):
            continue  # read_outputs reports the exact missing/corrupt filename
        matches, details = event_shard.get("matches"), evidence_shard.get("details")
        if (event_shard.get("schema") != "upcoming-event-v1"
                or evidence_shard.get("schema") != "upcoming-evidence-v1"
                or event_shard.get("generation") != generation
                or evidence_shard.get("generation") != generation
                or not isinstance(matches, list) or not isinstance(details, list)):
            _add_finding(
                out, "output.upcoming_shard.contract_invalid",
                f"{tour}: upcoming shards for {ref.get('name')!r} are malformed",
                severity="error",
                entity=_event_entity(ref),
                evidence={"eventFile": repr(event_file),
                          "evidenceFile": repr(evidence_file)})
            continue
        match_ids = [row.get("matchId") for row in matches if isinstance(row, dict)]
        detail_ids = [row.get("matchId") for row in details if isinstance(row, dict)]
        if (len(match_ids) != len(matches) or len(set(match_ids)) != len(match_ids)
                or any(not isinstance(match_id, str) or not match_id for match_id in match_ids)
                or len(detail_ids) != len(details) or len(set(detail_ids)) != len(detail_ids)
                or set(match_ids) != set(detail_ids)):
            _add_finding(
                out, "output.upcoming_shard.match_identity_mismatch",
                f"{tour}: upcoming match/detail identities disagree for {ref.get('name')!r}",
                severity="error",
                entity=_event_entity(ref),
                evidence={"matchIds": list(map(str, match_ids)),
                          "detailIds": list(map(str, detail_ids))})
        if ref.get("count") != len(matches):
            _add_finding(
                out, "output.upcoming_shard.count_mismatch",
                f"{tour}: upcoming shard count disagrees for {ref.get('name')!r}",
                severity="error",
                entity=_event_entity(ref),
                evidence={"declared": ref.get("count"), "actual": len(matches)})
        base_ids.extend(match_ids)
        total += len(matches)

    if (len(set(event_files)) != len(event_files) or len(set(evidence_files)) != len(evidence_files)
            or len(set(event_keys)) != len(event_keys) or any(key[1] == "" for key in event_keys)):
        _add_finding(
            out, "output.upcoming_index.event_identity_invalid",
            f"{tour}: upcoming-index.json repeats or omits event shard identity",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"eventFiles": list(map(str, event_files)),
                      "evidenceFiles": list(map(str, evidence_files)),
                      "eventKeys": [[str(a), str(b)] for a, b in event_keys]})
    if len(set(base_ids)) != len(base_ids):
        _add_finding(
            out, "output.upcoming_index.match_identity_duplicate",
            f"{tour}: upcoming match identity appears in more than one event shard",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"matchIds": base_ids})
    if total != index.get("count"):
        _add_finding(
            out, "output.upcoming_index.count_mismatch",
            f"{tour}: upcoming-index.json count={index.get('count')} but shards contain {total}",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"declared": index.get("count"), "actual": total})

    highlight_ids = [row.get("matchId") for row in highlights if isinstance(row, dict)]
    if (len(highlight_ids) != len(highlights) or len(set(highlight_ids)) != len(highlight_ids)
            or not set(highlight_ids).issubset(set(base_ids))
            or any(any(key in row for key in ("components", "evidence", "forecast"))
                   for row in highlights if isinstance(row, dict))):
        _add_finding(
            out, "output.upcoming_index.highlights_invalid",
            f"{tour}: upcoming-index.json highlights are duplicated, unknown, or heavy",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"highlightIds": list(map(str, highlight_ids))})


def _check_watch_ranking(out: list, tour: str, upcoming: list,
                         scenario_index: object, shards: dict) -> None:
    """Pin the transparent score math and its stable exact-leverage join."""
    expected_leverage = {}
    if isinstance(scenario_index, dict):
        generation = scenario_index.get("generation")
        for ref in scenario_index.get("events") or []:
            if not isinstance(ref, dict) or ref.get("generation") != generation:
                continue
            shard = shards.get(ref.get("file"))
            if not isinstance(shard, dict) or shard.get("generation") != generation:
                continue
            rounds = {
                match.get("id"): str(rnd.get("round") or "")
                for rnd in shard.get("geometry") or [] if isinstance(rnd, dict)
                for match in rnd.get("matches") or [] if isinstance(match, dict)
            }
            for match_id, row in (shard.get("titleLeverage") or {}).items():
                if not isinstance(row, dict) or not _is_prob(row.get("value")):
                    continue
                pair = frozenset((_player_identity_key(row.get("playerA")),
                                  _player_identity_key(row.get("playerB"))))
                expected_leverage[(str(ref.get("espnId") or ""), pair,
                                   rounds.get(match_id, ""))] = float(row["value"]) * 100.0

    ranks = []
    for match in upcoming:
        label = f"upcoming {match.get('playerA')!r} vs {match.get('playerB')!r}"
        match_entity = _match_entity(
            match,
            player_a=match.get("playerA"),
            player_b=match.get("playerB"),
        )
        watch, rank = match.get("watch"), match.get("watchRank")
        if not isinstance(watch, dict) or watch.get("schema") != "watch-v1":
            _add_finding(
                out, "output.watch_score.contract_invalid",
                f"{tour}: {label} watch-v1 score is missing/malformed",
                severity="error", entity=match_entity,
                evidence={"valueType": type(watch).__name__})
            continue
        if not isinstance(rank, int) or isinstance(rank, bool):
            _add_finding(
                out, "output.watch_score.rank_invalid",
                f"{tour}: {label} watchRank is missing/malformed",
                severity="error", entity=match_entity, evidence={"rank": repr(rank)})
        else:
            ranks.append((rank, watch.get("score")))
        if watch.get("weights") != _WATCH_WEIGHTS:
            _add_finding(
                out, "output.watch_score.weights_mismatch",
                f"{tour}: {label} watch weights disagree with watch-v1",
                severity="error", entity=match_entity,
                evidence={"expected": _WATCH_WEIGHTS,
                          "actual": watch.get("weights")
                          if isinstance(watch.get("weights"), dict)
                          else repr(watch.get("weights"))})
        factors = watch.get("factors")
        if not isinstance(factors, dict) or set(factors) != set(_WATCH_WEIGHTS):
            _add_finding(
                out, "output.watch_score.factor_set_invalid",
                f"{tour}: {label} watch factors are missing/duplicated",
                severity="error", entity=match_entity,
                evidence={"expected": sorted(_WATCH_WEIGHTS),
                          "actual": sorted(map(str, factors))
                          if isinstance(factors, dict) else None})
            continue
        available_count = 0
        weighted = 0.0
        for key, weight in _WATCH_WEIGHTS.items():
            factor = factors.get(key)
            if (not isinstance(factor, dict) or not isinstance(factor.get("available"), bool)
                    or not _finite_between(factor.get("score"), 0.0, 100.0)):
                _add_finding(
                    out, "output.watch_score.factor_invalid",
                    f"{tour}: {label} watch factor {key} is invalid",
                    severity="error", entity=f"{match_entity}#factor:{key}",
                    evidence={"factor": key, "value": repr(factor)})
                continue
            available_count += int(factor["available"])
            weighted += weight * float(factor["score"]) / 100.0
            if key in ("closeness", "quality", "stakes") and not factor["available"]:
                _add_finding(
                    out, "output.watch_score.required_factor_unavailable",
                    f"{tour}: {label} required watch factor {key} is unavailable",
                    severity="error", entity=f"{match_entity}#factor:{key}",
                    evidence={"factor": key})
            if not factor["available"] and float(factor["score"]) != 0.0:
                _add_finding(
                    out, "output.watch_score.unavailable_factor_bonus",
                    f"{tour}: {label} unavailable watch factor {key} received a bonus",
                    severity="error", entity=f"{match_entity}#factor:{key}",
                    evidence={"factor": key, "score": float(factor["score"])})
        if watch.get("coverage") != available_count:
            _add_finding(
                out, "output.watch_score.coverage_mismatch",
                f"{tour}: {label} watch coverage disagrees with available factors",
                severity="error", entity=match_entity,
                evidence={"expected": available_count, "actual": watch.get("coverage")})
        if (not _finite_between(watch.get("score"), 0.0, 100.0)
                or abs(float(watch["score"]) - weighted) > 0.11):
            _add_finding(
                out, "output.watch_score.total_mismatch",
                f"{tour}: {label} watch score disagrees with weighted factors",
                severity="error", entity=match_entity,
                evidence={"expected": weighted, "actual": repr(watch.get("score"))})

        pair = frozenset((_player_identity_key(match.get("playerA")),
                          _player_identity_key(match.get("playerB"))))
        leverage = expected_leverage.get((str(match.get("espnId") or ""), pair,
                                          str(match.get("round") or "")))
        title = factors.get("titleLeverage")
        if isinstance(title, dict):
            if leverage is None and title.get("available"):
                _add_finding(
                    out, "output.watch_score.title_leverage_orphan",
                    f"{tour}: {label} title leverage lacks same-generation exact evidence",
                    severity="error", entity=match_entity, evidence={})
            elif leverage is not None and (not title.get("available")
                                           or abs(float(title.get("score", -1)) - leverage) > 0.11):
                _add_finding(
                    out, "output.watch_score.title_leverage_mismatch",
                    f"{tour}: {label} title leverage disagrees with exact scenario",
                    severity="error", entity=match_entity,
                    evidence={"expected": leverage, "actual": repr(title.get("score"))})
    if len(ranks) == len(upcoming):
        ordered = sorted(ranks)
        if [rank for rank, _ in ordered] != list(range(1, len(upcoming) + 1)):
            _add_finding(
                out, "output.watch_score.ranking_not_contiguous",
                f"{tour}: upcoming watchRank is not contiguous 1..{len(upcoming)}",
                severity="error", entity="artifact:upcoming-index.json",
                evidence={"ranks": [rank for rank, _ in ordered],
                          "expectedCount": len(upcoming)})
        scores = [float(score) for _, score in ordered if _finite_between(score, 0.0, 100.0)]
        if len(scores) == len(ordered) and scores != sorted(scores, reverse=True):
            _add_finding(
                out, "output.watch_score.ranking_order_invalid",
                f"{tour}: upcoming watchRank is not score-descending",
                severity="error", entity="artifact:upcoming-index.json",
                evidence={"scores": scores})


def _check_projection(out: list, tour: str, name, proj: list, *, event_entity: str) -> None:
    for p in proj:
        who = p.get("name")
        entity = f"{event_entity}#player:{_player_identity_key(who)}"
        c, f, s = p.get("champion"), p.get("final"), p.get("sf")
        for k, v in (("champion", c), ("final", f), ("sf", s)):
            # None is deliberate: the live projector (sim/tournaments.py) sets a round field
            # to None once that round is already DETERMINED ("SF" not in cols -> sf=None for a
            # finalist who is past the semis). That degrades gracefully in the UI; only a
            # PRESENT-but-out-of-range value is a real problem.
            if v is not None and not _is_prob(v):
                _add_finding(
                    out, "output.projection.probability_invalid",
                    f"{tour}: {name!r} {who!r} {k}={v!r} out of [0,1]",
                    severity="error", entity=f"{entity}#stage:{k}",
                    evidence={"stage": k, "value": repr(v)})
        if _is_prob(c) and _is_prob(f) and _is_prob(s) and (c > f + 1e-6 or f > s + 1e-6):
            _add_finding(
                out, "output.projection.stage_order_invalid",
                f"{tour}: {name!r} {who!r} champion<=final<=sf violated ({c},{f},{s})",
                severity="error", entity=entity,
                evidence={"champion": float(c), "final": float(f), "sf": float(s)})
        seq = [p["reach"][k] for k in _REACH_ORDER if isinstance(p.get("reach"), dict) and k in p["reach"]]
        if any(not _is_prob(v) for v in seq):
            _add_finding(
                out, "output.projection.reach_probability_invalid",
                f"{tour}: {name!r} {who!r} reach probability out of [0,1]",
                severity="error", entity=entity,
                evidence={"values": [repr(v) for v in seq]})
        elif any(seq[i] < seq[i + 1] - 1e-6 for i in range(len(seq) - 1)):
            _add_finding(
                out, "output.projection.reach_order_invalid",
                f"{tour}: {name!r} {who!r} reach odds not monotonically non-increasing",
                severity="error", entity=entity,
                evidence={"values": [float(v) for v in seq]})


def _check_tournament(out: list, tour: str, t: dict, now: pd.Timestamp | None = None) -> None:
    name, status = t.get("name"), t.get("status")
    force = bool(t.get("coverageOnly"))
    event_entity = _event_entity(t)
    ds, size, alive, champ = t.get("drawStatus"), t.get("drawSize"), t.get("aliveCount"), t.get("champion")
    if status not in _STATUSES:
        _add_finding(
            out, "output.tournament.status_invalid",
            f"{tour}: tournament {name!r} has bad status {status!r}",
            severity="error", entity=event_entity,
            evidence={"status": repr(status)})
    if ds is None:
        _add_finding(
            out, "output.tournament.draw_status_missing",
            f"{tour}: tournament {name!r} missing drawStatus",
            severity="error", entity=event_entity, evidence={})
    elif ds not in _DRAW_STATES:
        _add_finding(
            out, "output.tournament.draw_status_invalid",
            f"{tour}: tournament {name!r} has bad drawStatus {ds!r}",
            severity="error", entity=event_entity,
            evidence={"drawStatus": repr(ds)})
    if isinstance(size, int) and isinstance(alive, int) and alive > size:
        _add_finding(
            out, "output.tournament.alive_count_invalid",
            f"{tour}: tournament {name!r} aliveCount {alive} > drawSize {size}",
            severity="error", entity=event_entity,
            evidence={"aliveCount": alive, "drawSize": size})
    if isinstance(size, int) and size > 128:
        _add_finding(
            out, "output.tournament.draw_size_excessive",
            f"{tour}: tournament {name!r} drawSize {size} exceeds the maximum 128-player draw",
            severity="error", entity=event_entity,
            evidence={"drawSize": size, "maximum": 128})
    # a real bracket seats a STANDARD draw size — a power of two, or a sanctioned
    # bye-draw (28/48/56/96...; Gstaad's 28-draw blocked a deploy on 2026-07-10 when this
    # demanded strict powers of two). A leaked 'TBD' (128 -> 129, 28 -> 29) or a name-
    # resolution loss (28 -> 27) still lands outside the set and blocks. completed/
    # partial/seeded/completed sizes can be non-standard because drawSize counts entrants,
    # but no tour-level singles draw can exceed 128.
    if ds == "real" and isinstance(size, int) and not _real_draw_size_ok(size):
        _add_finding(
            out, "output.tournament.draw_geometry_invalid",
            f"{tour}: tournament {name!r} real draw size {size} is not a standard "
            f"bracket size (power of two or bye-draw {sorted(_BYE_DRAW_SIZES)})",
            severity="error", entity=event_entity,
            evidence={"drawSize": size, "allowedByeDrawSizes": sorted(_BYE_DRAW_SIZES)})
    if status == "completed" and not champ:
        # An event can now be called over by its CALENDAR when the results feed never
        # delivered a final (sim/tournaments: Iasi sat "live" for nine days waiting for one).
        # That card is honest — the champion is genuinely unknown — so it is advisory. A
        # completed card with no champion and no such explanation is still a builder bug.
        if t.get("finalRecorded") is False:
            _add_finding(
                out, "output.tournament.final_missing",
                f"{tour}: completed tournament {name!r} completed without a recorded "
                f"final — its calendar says it is over but no final arrived, so the "
                f"champion is unknown",
                severity="warning", entity=event_entity,
                evidence={"finalRecorded": False})
        else:
            _add_finding(
                out, "output.tournament.champion_missing",
                f"{tour}: completed tournament {name!r} has no champion",
                severity="error", entity=event_entity, evidence={})
    if status in ("live", "upcoming") and champ:
        _add_finding(
            out, "output.tournament.champion_premature",
            f"{tour}: {status} tournament {name!r} already names champion {champ!r}",
            severity="error", entity=event_entity,
            evidence={"status": status, "champion": repr(champ)})
    # An entrant of a live ordered draw that the feed no longer lists in the event has left
    # without losing, or is spelled two ways. Nothing else catches either: eliminations come
    # from loser rows, so a withdrawal leaves no evidence at all, and Felix Auger-Aliassime
    # sat at 14.3% as Toronto's FAVOURITE having never hit a ball there. The producer derives
    # this after reconciling the draw against the feed (sim/tournaments.py) because only it
    # can tell the two apart; the gate's job is to refuse to ship the result.
    missing = t.get("drawnNotInField")
    if isinstance(missing, list) and missing:
        _add_finding(
            out, "output.tournament.withdrawn_player_projected",
            _tiered(f"{tour}: live tournament {name!r} still has {len(missing)} drawn "
                    f"player(s) the feed no longer lists in the event "
                    f"({', '.join(map(str, missing[:4]))}) — they withdrew without "
                    f"losing, or the draw and the feed spell them differently; either "
                    f"way the board is showing someone who is not in the tournament",
                    t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"players": list(map(str, missing)), "level": repr(t.get("level"))})
    # A live event that has stopped absorbing results is wrong in one of two ways, and the
    # gate cannot tell them apart from `end` alone, so it must not assert either: the event
    # ENDED and lost its final, freezing it live (Iasi showed live with 3 alive nine days
    # after it finished, 2026-07-27), or it is genuinely still playing and the results feed
    # has gone blind (2026-08-05: ESPN began 403-ing the live overlay, and Toronto kept
    # showing Zverev alive at 21% to win for three days after Griekspoor knocked him out).
    # The second is why this cannot be left to the tour-wide `results` freshness check —
    # that limit is 5 days and is dominated by events that have already finished, so one
    # stalled tournament never moves it. Both failures ship a board asserting that beaten
    # players are still alive, which is the thing a user actually sees.
    # `dateBasis == "start"` means the producer proved these rows carry ONE tournament stamp
    # rather than match dates (sim/tournaments._date_basis), so `end` is the event's start and
    # ageing it measures nothing. Hagen shipped 28 rows across R32/R16/QF all dated 08-03 and
    # read as five days idle while it was playing its quarter-finals. Skipped rather than given
    # a longer limit: the signal is absent, not coarse, and a slack limit would pretend
    # otherwise. Every card whose dates ARE match dates keeps the full-strength check — the
    # exemption has to be earned per card, or one bad feed would blind the whole invariant.
    if status == "live" and now is not None and t.get("dateBasis") != "start":
        age = _age_days(t.get("end"), now)
        if age is not None and age > HEALTH_MAX_LIVE_EVENT_AGE_DAYS:
            _add_finding(
                out, "output.tournament.live_progress_stale",
                _tiered(f"{tour}: live tournament {name!r} last played {age}d ago "
                        f"(max {HEALTH_MAX_LIVE_EVENT_AGE_DAYS}) — either its final "
                        f"never arrived and it is stuck 'live', or its results feed has "
                        f"stalled and eliminated players are still shown as alive",
                        t.get("level"), force=force),
                severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
                evidence={"ageDays": age, "maxDays": HEALTH_MAX_LIVE_EVENT_AGE_DAYS,
                          "lastPlayed": t.get("end"), "level": repr(t.get("level"))})
    # The mirror image: an event still labelled "upcoming" after its own dates have passed.
    # Ending while never having gone live is impossible — the results simply never joined, so
    # the card is inviting clicks on odds for a tournament that is already over. Tier-aware:
    # marquee events must not ship in that state; the long tail warns.
    if status == "upcoming" and now is not None:
        end_age = _age_days(t.get("end"), now)
        start_age = _age_days(t.get("start"), now)
        if end_age is not None and end_age > 0:
            _add_finding(
                out, "output.tournament.upcoming_after_end",
                _tiered(f"{tour}: upcoming tournament {name!r} already ended "
                        f"({t.get('end')}, {end_age}d ago) but never went live — its "
                        f"results are not joining", t.get("level"), force=force),
                severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
                evidence={"end": t.get("end"), "ageDays": end_age,
                          "level": repr(t.get("level"))})
        elif start_age is not None and start_age > HEALTH_MAX_UPCOMING_START_LAG_DAYS:
            # Advisory at every tier: ESPN start dates include qualifying, so a main draw
            # legitimately reads "upcoming" for a day or two — and a Slam for a whole week.
            _add_finding(
                out, "output.tournament.live_transition_late",
                f"{tour}: upcoming tournament {name!r} started {t.get('start')} "
                f"({start_age}d ago, max {HEALTH_MAX_UPCOMING_START_LAG_DAYS}) but "
                f"has not flipped live",
                severity="warning", entity=event_entity,
                evidence={"start": t.get("start"), "ageDays": start_age,
                          "maxDays": HEALTH_MAX_UPCOMING_START_LAG_DAYS})
    # A finished event has exactly one player left standing. Palermo shipped as completed
    # WITH a champion and aliveCount 32 of 32: the authoritative draw supplied the field
    # while the results supplied the eliminations, and the two never joined. Settled-draw
    # refreshes now prevent that producer failure; regressions follow the tier policy.
    if status == "completed" and champ and isinstance(alive, int) and alive > 1:
        _add_finding(
            out, "output.tournament.completed_alive_count_invalid",
            _tiered(f"{tour}: completed tournament {name!r} names champion {champ!r} "
                    f"but still reports {alive} players alive (expected 1)",
                    t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"champion": repr(champ), "aliveCount": alive, "expected": 1,
                      "level": repr(t.get("level"))})
    # `_flag_placeholders` matches a fixed word set, so the NUMBERED form ("Qualifier 30")
    # slipped through and shipped as Palermo's modelFavorite. Use the same predicate the
    # draw machinery uses to decide whether a slot names a real player.
    fav = t.get("modelFavorite")
    if fav is not None and not _is_real_name(fav):
        _add_finding(
            out, "output.tournament.favorite_placeholder",
            _tiered(f"{tour}: tournament {name!r} modelFavorite {fav!r} is a draw "
                    f"placeholder", t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"modelFavorite": repr(fav), "level": repr(t.get("level"))})
    # Surface. A non-canonical value is a builder bug (the card, the per-surface Elo blend
    # and the /style page all key off this string), so it blocks. A month-of-year GUESS is
    # tier-aware — it is what shipped the DC Open, a hard court, priced on grass Elo, but for
    # a genuinely new small event it can be the only answer we have.
    sfc, lvl = t.get("surface"), t.get("level")
    if sfc is None:
        _add_finding(
            out, "output.tournament.surface_missing",
            f"{tour}: tournament {name!r} has no surface",
            severity="error", entity=event_entity, evidence={})
    elif sfc not in _CANONICAL_SURFACES:
        _add_finding(
            out, "output.tournament.surface_invalid",
            f"{tour}: tournament {name!r} surface {sfc!r} is not a canonical surface "
            f"({'/'.join(sorted(_CANONICAL_SURFACES))})",
            severity="error", entity=event_entity,
            evidence={"surface": repr(sfc), "allowed": sorted(_CANONICAL_SURFACES)})
    if status in ("live", "upcoming") and t.get("surfaceSource") == "month":
        _add_finding(
            out, "output.tournament.surface_guessed",
            _tiered(f"{tour}: {status} tournament {name!r} surface {sfc!r} is a "
                    f"month-of-year guess — no archive or Wikipedia surface resolved",
                    lvl, force=force),
            severity=_tier_severity(lvl, force=force), entity=event_entity,
            evidence={"surface": repr(sfc), "surfaceSource": "month",
                      "level": repr(lvl)})
    # Match format drives the model's win transform. ATP Slams alone are best-of-five;
    # every WTA card and every non-Slam ATP card is best-of-three. A generic tier is
    # deliberately skipped because the resolver has not established which rule applies.
    generic_level = f"{tour.upper()} Tour"
    if lvl != generic_level:
        expected_best_of = 5 if tour == "atp" and lvl == "Grand Slam" else 3
        if t.get("bestOf") != expected_best_of:
            _add_finding(
                out, "output.tournament.match_format_invalid",
                _tiered(f"{tour}: tournament {name!r} bestOf={t.get('bestOf')!r} "
                        f"does not match {lvl!r} (expected {expected_best_of})",
                        lvl, force=force),
                severity=_tier_severity(lvl, force=force), entity=event_entity,
                evidence={"bestOf": repr(t.get("bestOf")), "expected": expected_best_of,
                          "level": repr(lvl)})
    # Level. A tier outside the vocabulary is a builder bug — some source's dialect reached a
    # card verbatim ("ATP 250 series", "C") — so it blocks regardless of tier. A tier from the
    # WRONG TOUR is the same bug with a sharper symptom: the ATP board shipped Generali Open
    # as "WTA 125" because a substring tag matched "men" inside "tournaments".
    if lvl is not None and lvl not in LEVEL_VOCAB.get(tour, frozenset()):
        other = "wta" if tour == "atp" else "atp"
        if lvl in LEVEL_VOCAB.get(other, frozenset()):
            _add_finding(
                out, "output.tournament.level_wrong_tour",
                f"{tour}: tournament {name!r} level {lvl!r} belongs to the other tour",
                severity="error", entity=event_entity,
                evidence={"name": str(name), "level": str(lvl),
                          "otherTour": other, "coverageKey": t.get("coverageKey"),
                          "espnId": t.get("espnId")})
        else:
            _add_finding(
                out, "output.tournament.level_invalid",
                f"{tour}: tournament {name!r} level {lvl!r} is not in the "
                f"{tour.upper()} level vocabulary",
                severity="error", entity=event_entity,
                evidence={"name": str(name), "level": str(lvl),
                          "allowed": sorted(LEVEL_VOCAB.get(tour, frozenset())),
                          "coverageKey": t.get("coverageKey"), "espnId": t.get("espnId")})
    elif lvl == generic_level:
        _add_finding(
            out, "output.tournament.tier_unresolved",
            _tiered(f"{tour}: {status} tournament {name!r} tier did not resolve "
                    f"(shows the generic {lvl!r})", lvl, force=force),
            severity=_tier_severity(lvl, force=force), entity=event_entity,
            evidence={"status": str(status), "level": str(lvl),
                      "name": str(name), "coverageKey": t.get("coverageKey"),
                      "espnId": t.get("espnId")})

    proj = t.get("projection") or []
    _check_projection(out, tour, name, proj, event_entity=event_entity)
    # `_flag_placeholders` tests exact membership of a fixed word set, so the NUMBERED form
    # ("Qualifier 30") walked straight through it — 22 of DC's 24 projected "players" were
    # qualifiers and nothing fired. Use the same `is_real` predicate the draw machinery and
    # the modelFavorite check use, so producer and gate cannot disagree about what a real
    # entrant is. Bracket SLOTS legitimately carry "Qualifier N"; a PROJECTION ROW never can.
    ghosts = sorted({p.get("name") for p in proj if not _is_real_name(p.get("name"))})
    if ghosts:
        shown = ", ".join(repr(g) for g in ghosts[:3]) + (" …" if len(ghosts) > 3 else "")
        _add_finding(
            out, "output.tournament.projection_placeholder",
            _tiered(f"{tour}: tournament {name!r} projection names {len(ghosts)} draw "
                    f"placeholder(s) as players ({shown})", t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"players": [repr(g) for g in ghosts],
                      "level": repr(t.get("level"))})


def _check_brackets(out: list, tour: str, brackets: list, tournaments) -> None:
    """The /bracket payload must be a structurally-sound single-elim draw consistent with
    tournaments.json. A displayed bracket is reconstructed by folding an ordered draw
    forward and joining results (sim/bracket.py); the failure classes are a fold that
    doesn't halve, a winner not fed to the next round, a live event whose final is already
    decided, a prob out of range, or a champion that disagrees with tournaments.json."""
    from ..data.draws_official import official_dates_match
    from ..data.results import _name_key
    from ..sim.draws import SIZE_NAME
    # Cross-artifact joins use provider identity, never mutable sponsor/display titles.
    # A single ESPN event can be renamed between the tournament card and bracket build;
    # conversely, two different ESPN events can legitimately share the same display name.
    # Older/id-less artifacts may still join, including when ESPN identity reached only
    # one of the two payloads, but only when one candidate has BOTH date overlap and at
    # least two shared real players. Two conflicting provider identities can never be
    # overridden by that evidence, and a date window alone is not identity.
    tournament_rows = ([(index, tournament)
                        for index, tournament in enumerate(tournaments)
                        if isinstance(tournament, dict)]
                       if isinstance(tournaments, list) else [])
    tournaments_by_identity: dict[str, list[tuple[int, dict]]] = {}
    for index, tournament in tournament_rows:
        stable_entity = _event_stable_entity(tournament)
        if stable_entity:
            tournaments_by_identity.setdefault(stable_entity, []).append((index, tournament))
    matched_tournament_indexes: set[int] = set()
    bracket_matches: list[tuple[str, str, bool]] = []
    source_attachments: dict[str, dict] = {}
    for index, ev in enumerate(brackets):
        if not isinstance(ev, dict):
            _add_finding(
                out, "output.bracket.entry_invalid",
                f"{tour}: brackets.json has a non-object entry",
                severity="error", entity="artifact:brackets.json",
                evidence={"index": index, "valueType": type(ev).__name__})
            continue
        name = ev.get("name")
        event_entity = _event_entity(ev)
        stable_entity = _event_stable_entity(ev)
        provider_entity = _event_provider_entity(ev)
        exact_matches = tournaments_by_identity.get(stable_entity, []) if stable_entity else []
        if exact_matches:
            matches = exact_matches
        else:
            matches = [
                (tournament_index, tournament)
                for tournament_index, tournament in tournament_rows
                # The exact-identity branch above already handled equal provider IDs.
                # If both remaining rows carry provider IDs, they conflict and no amount
                # of circumstantial date/player evidence may join them. Evidence fallback
                # is reserved for pairs where at least one side is genuinely provider-idless.
                if not (provider_entity and _event_provider_entity(tournament))
                and _event_evidence_matches(ev, tournament)
            ]
            if len(matches) != 1:
                matches = []
        t = matches[0][1] if matches else None
        # When only tournaments.json received the provider identity, use that resolved
        # identity for every bracket finding. Otherwise a sponsor/date-derived bracket
        # fingerprint would churn even though the evidence join proved the ESPN event.
        if t is not None and provider_entity is None:
            event_entity = _event_provider_entity(t) or event_entity
        matched_tournament_indexes.update(index for index, _ in matches)
        bracket_matches.append((event_entity, _norm_name(name), t is not None))
        rounds = ev.get("rounds")
        size = ev.get("bracketSize")
        status = ev.get("status")
        if not isinstance(rounds, list) or not rounds:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} has no rounds",
                severity="error", entity=event_entity,
                evidence={"roundsType": type(rounds).__name__})
            continue
        if status not in _STATUSES:
            _add_finding(
                out, "output.bracket.status_invalid",
                f"{tour}: bracket {name!r} has bad status {status!r}",
                severity="error", entity=event_entity,
                evidence={"status": repr(status)})

        # Provenance is part of a published bracket, not optional decoration. It makes the
        # first-party/Wikipedia fallback observable and prevents a source-specific field from
        # silently becoming authoritative again. Official artifacts additionally carry the
        # date/player evidence that attached the provider id to this ESPN event.
        source, source_id, source_url = (
            ev.get("drawSource"), ev.get("drawSourceId"), ev.get("drawSourceUrl"))
        espn_id = str(ev.get("espnId") or "")
        if espn_id and source in _DRAW_SOURCE_HOSTS and (source_id or source_url):
            source_attachments[str(index)] = {
                "name": name, "espnId": espn_id, "source": source,
                "sourceId": source_id, "sourceUrl": source_url,
            }
        if source not in _DRAW_SOURCE_HOSTS:
            _add_finding(
                out, "output.bracket.draw_source_invalid",
                f"{tour}: bracket {name!r} has invalid drawSource {source!r}",
                severity="error", entity=event_entity,
                evidence={"drawSource": repr(source)})
        if not source_id:
            _add_finding(
                out, "output.bracket.draw_source_id_missing",
                f"{tour}: bracket {name!r} is missing drawSourceId",
                severity="error", entity=event_entity, evidence={})
        host = urllib.parse.urlparse(str(source_url or "")).hostname
        if source in _DRAW_SOURCE_HOSTS and host != _DRAW_SOURCE_HOSTS[source]:
            _add_finding(
                out, "output.bracket.draw_source_host_invalid",
                f"{tour}: bracket {name!r} drawSource {source!r} has URL host "
                f"{host!r} (expected {_DRAW_SOURCE_HOSTS[source]!r})",
                severity="error", entity=event_entity,
                evidence={"source": str(source), "actualHost": repr(host),
                          "expectedHost": _DRAW_SOURCE_HOSTS[source]})
        if source in ("atp", "wta"):
            if not espn_id:
                _add_finding(
                    out, "output.bracket.espn_provenance_missing",
                    f"{tour}: bracket {name!r} official draw is missing espnId provenance",
                    severity="error", entity=event_entity, evidence={})
            if source != tour:
                _add_finding(
                    out, "output.bracket.official_source_wrong_tour",
                    f"{tour}: bracket {name!r} uses the other tour's official source {source!r}",
                    severity="error", entity=event_entity,
                    evidence={"source": str(source)})
            evidence = ev.get("drawEvidencePlayers")
            field_evidence = ev.get("drawEvidenceFieldPlayers")
            if (not isinstance(evidence, int) or not isinstance(field_evidence, int)
                    or field_evidence < 2 or evidence < 2 or evidence * 4 < field_evidence * 3):
                _add_finding(
                    out, "output.bracket.field_evidence_insufficient",
                    f"{tour}: bracket {name!r} official draw matches only "
                    f"{evidence!r}/{field_evidence!r} event players (minimum 75%)",
                    severity="error", entity=event_entity,
                    evidence={"matchedPlayers": repr(evidence),
                              "fieldPlayers": repr(field_evidence), "minimumFraction": 0.75})
            if not official_dates_match(
                    ev.get("start"), ev.get("end") or ev.get("start"),
                    ev.get("drawSourceStart"), ev.get("drawSourceEnd")):
                _add_finding(
                    out, "output.bracket.calendar_evidence_insufficient",
                    f"{tour}: bracket {name!r} official draw calendar overlap is too small for "
                    f"the tournament ({ev.get('drawSourceStart')}..{ev.get('drawSourceEnd')} "
                    f"vs {ev.get('start')}..{ev.get('end')})",
                    severity="error", entity=event_entity,
                    evidence={"drawStart": ev.get("drawSourceStart"),
                              "drawEnd": ev.get("drawSourceEnd"), "eventStart": ev.get("start"),
                              "eventEnd": ev.get("end")})

        # structure: power-of-two size, rounds halve to a single final, labels match width
        if not _pow2(size):
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} bracketSize {size!r} is not a power of two",
                severity="error", entity=event_entity,
                evidence={"bracketSize": repr(size), "reason": "not_power_of_two"})
        r0 = rounds[0].get("matches") or []
        if isinstance(size, int) and 2 * len(r0) != size:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} round 0 has {len(r0)} matches (expected {size // 2})",
                severity="error", entity=event_entity,
                evidence={"round": 0, "matches": len(r0), "expected": size // 2})
        for k in range(len(rounds) - 1):
            a, b = len(rounds[k].get("matches") or []), len(rounds[k + 1].get("matches") or [])
            if b * 2 != a:
                _add_finding(
                    out, "output.bracket.geometry_invalid",
                    f"{tour}: bracket {name!r} round {k} has {a} matches, next has {b} (must halve)",
                    severity="error", entity=event_entity,
                    evidence={"round": k, "matches": a, "nextMatches": b})
        if len(rounds[-1].get("matches") or []) != 1:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} final round is not a single match",
                severity="error", entity=event_entity,
                evidence={"finalMatches": len(rounds[-1].get("matches") or [])})
        for rnd in rounds:
            ms = rnd.get("matches") or []
            want = SIZE_NAME.get(2 * len(ms))
            if want and rnd.get("round") != want:
                _add_finding(
                    out, "output.bracket.geometry_invalid",
                    f"{tour}: bracket {name!r} round {rnd.get('round')!r} mislabelled "
                    f"(expected {want!r} for {len(ms)} matches)",
                    severity="error", entity=event_entity,
                    evidence={"actualRound": repr(rnd.get("round")), "expectedRound": want,
                              "matches": len(ms)})

        # drawSize: count round-0 slots the way tournaments.json drawSize does — field_pool is
        # the non-null complete-draw slots, which INCLUDES unresolved qualifier placeholders (an
        # early-captured draw legitimately carries them; the frozen-wiki capture never backfills
        # the names). Only byes (null) are excluded on both sides. Excluding placeholders here
        # would false-positive against drawSize (Gstaad's early draw, 2026-07-13).
        nonbye0 = [p for m in r0 for p in (m.get("a"), m.get("b")) if p is not None]
        ds = ev.get("drawSize")
        if isinstance(ds, int) and len(nonbye0) != ds:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} has {len(nonbye0)} round-0 slots but drawSize {ds}",
                severity="error", entity=event_entity,
                evidence={"roundZeroSlots": len(nonbye0), "drawSize": ds})
        if t and isinstance(t.get("drawSize"), int) and ds != t.get("drawSize"):
            _add_finding(
                out, "output.bracket.tournament_draw_size_mismatch",
                f"{tour}: bracket {name!r} drawSize {ds} != tournaments.json {t.get('drawSize')}",
                severity="error", entity=event_entity,
                evidence={"bracketDrawSize": ds, "tournamentDrawSize": t.get("drawSize")})

        # final decidedness mirrors the tournament rule (no live event names a champion)
        final_m = (rounds[-1].get("matches") or [{}])[0]
        fw = final_m.get("winner")
        if status == "completed" and fw is None:
            _add_finding(
                out, "output.bracket.completed_final_undecided",
                f"{tour}: completed bracket {name!r} final match is undecided",
                severity="error", entity=event_entity, evidence={})
        if status in ("live", "upcoming") and fw is not None:
            _add_finding(
                out, "output.bracket.final_decided_prematurely",
                f"{tour}: {status} bracket {name!r} final match already decided",
                severity="error", entity=event_entity,
                evidence={"status": status, "winner": repr(fw)})

        # per-match: winner validity, prob range, prob/source presence, upset orientation,
        # and feeder consistency (a decided winner must seat in the right next-round slot)
        for k, rnd in enumerate(rounds):
            ms = rnd.get("matches") or []
            for j, m in enumerate(ms):
                match_entity = _match_entity(
                    m,
                    event_entity=event_entity,
                    player_a=m.get("a"),
                    player_b=m.get("b"),
                    fallback=f"round:{k}:match:{j}",
                )
                w = m.get("winner")
                if w not in ("a", "b", None):
                    _add_finding(
                        out, "output.bracket.winner_value_invalid",
                        f"{tour}: bracket {name!r} winner {w!r} not in a/b/null",
                        severity="error", entity=match_entity,
                        evidence={"winner": repr(w)})
                elif w in ("a", "b") and not m.get(w):
                    _add_finding(
                        out, "output.bracket.winner_side_missing",
                        f"{tour}: bracket {name!r} decided match has null winning side {w!r}",
                        severity="error", entity=match_entity,
                        evidence={"winner": w})
                p, src = m.get("p"), m.get("probSource")
                if p is not None and not _is_prob(p):
                    _add_finding(
                        out, "output.bracket.probability_invalid",
                        f"{tour}: bracket {name!r} match p={p!r} out of [0,1]",
                        severity="error", entity=match_entity,
                        evidence={"probability": repr(p)})
                if src not in ("logged", "model", None):
                    _add_finding(
                        out, "output.bracket.probability_source_invalid",
                        f"{tour}: bracket {name!r} probSource {src!r} invalid",
                        severity="error", entity=match_entity,
                        evidence={"probabilitySource": repr(src)})
                if (p is None) != (src is None):
                    _add_finding(
                        out, "output.bracket.probability_source_mismatch",
                        f"{tour}: bracket {name!r} p/probSource presence mismatch (p={p!r}, src={src!r})",
                        severity="error", entity=match_entity,
                        evidence={"probability": repr(p), "probabilitySource": repr(src)})
                up = m.get("upset")
                if up is not None and p is not None and w in ("a", "b"):
                    won_p = p if w == "a" else 1.0 - p
                    if bool(up) != (won_p < 0.5):
                        _add_finding(
                            out, "output.bracket.upset_flag_mismatch",
                            f"{tour}: bracket {name!r} upset flag disagrees with p ({p})",
                            severity="error", entity=match_entity,
                            evidence={"probability": p, "winner": w, "upset": repr(up)})
                if w in ("a", "b") and k + 1 < len(rounds):
                    won = m.get(w)
                    nxt_ms = rounds[k + 1].get("matches") or []
                    nxt = nxt_ms[j // 2] if j // 2 < len(nxt_ms) else None
                    side = (nxt.get("a") if j % 2 == 0 else nxt.get("b")) if nxt else None
                    if side is not None and won is not None and _norm_name(side) != _norm_name(won):
                        _add_finding(
                            out, "output.bracket.advancement_mismatch",
                            f"{tour}: bracket {name!r} round {k} winner {won!r} not fed to next round (found {side!r})",
                            severity="error", entity=match_entity,
                            evidence={"round": k, "winner": repr(won),
                                      "nextRoundPlayer": repr(side)})

        # champion agrees with this payload AND tournaments.json. Compare on the
        # accent/punct-insensitive name key, not casefold: the bracket slot carries the
        # elo-canonical spelling while `champion` comes from the results winner_name, so a
        # champion with a diacritic (Nosková vs Noskova) is the SAME player, not a mismatch.
        if status == "completed" and fw in ("a", "b"):
            champ = final_m.get(fw)
            if ev.get("champion") and champ and _name_key(champ) != _name_key(ev.get("champion")):
                _add_finding(
                    out, "output.bracket.champion_mismatch",
                    f"{tour}: bracket {name!r} final winner {champ!r} != champion {ev.get('champion')!r}",
                    severity="error", entity=event_entity,
                    evidence={"finalWinner": repr(champ),
                              "bracketChampion": repr(ev.get("champion"))})
            if t and t.get("champion") and champ and _name_key(champ) != _name_key(t.get("champion")):
                _add_finding(
                    out, "output.bracket.tournament_champion_mismatch",
                    f"{tour}: bracket {name!r} champion {champ!r} != tournaments.json {t.get('champion')!r}",
                    severity="error", entity=event_entity,
                    evidence={"bracketChampion": repr(champ),
                              "tournamentChampion": repr(t.get("champion"))})

        _flag_placeholders(out, tour, f"bracket {name!r}",
                           (p for rnd in rounds for m in (rnd.get("matches") or [])
                            for p in (m.get("a"), m.get("b"))),
                           entity=event_entity, allow_numbered=True)

    from .draws import duplicate_draw_source_incidents
    for identity, detail in duplicate_draw_source_incidents(source_attachments):
        _add_finding(
            out, "output.draw_source.duplicate_attachment",
            f"{tour}: brackets.json {detail}",
            severity="error", entity=f"draw-source:{identity}",
            evidence={"artifact": "brackets.json", "detail": detail})

    # cross-presence: hasBracket <=> a brackets.json entry (both directions)
    if isinstance(tournaments, list):
        for index, t in tournament_rows:
            if t.get("hasBracket") and index not in matched_tournament_indexes:
                _add_finding(
                    out, "output.bracket.entry_missing",
                    f"{tour}: tournaments.json {t.get('name')!r} hasBracket but no brackets.json entry",
                    severity="error", entity=_event_entity(t), evidence={})
    if tournament_rows:
        for event_entity, normalized_name, matched in bracket_matches:
            if not matched:
                _add_finding(
                    out, "output.bracket.tournament_missing",
                    f"{tour}: brackets.json entry {normalized_name!r} "
                    "has no tournaments.json event",
                    severity="error", entity=event_entity, evidence={})


def _check_kalshi_ledger(out: list, tour: str, rows: list[dict]) -> None:
    """The Kalshi scorecard's scored rows must be morning-anchored PRE-match quotes of
    correctly-joined results (audit 2026-07-09: in-play occurrence-anchored prints, a
    settled-book carry scored as a 0.995 'favorite', and a rematch mis-join double-
    scoring one result all reached the deployed scorecard). One invariant per class."""
    from ..eval.kalshi_ledger import PREMATCH_UTC_HOUR
    from .kalshi import CANDLE_LOOKBACK_S, EXTREME_CARRY_MID
    seen: dict[tuple, str] = {}
    for r in rows:
        if not (r.get("match_status") == "matched"
                and r.get("result_type") == "completed"
                and r.get("price_kind") == "candle"
                and r.get("p_model") and r.get("p_kalshi")):
            continue
        tick, rd = r.get("event_ticker", "?"), r.get("result_date", "")
        ts = pd.to_datetime(r.get("price_ts"), utc=True, errors="coerce")
        anchor = pd.to_datetime(rd, utc=True, errors="coerce")
        if pd.isna(ts) or pd.isna(anchor):
            _add_finding(
                out, "output.kalshi_ledger.timestamp_invalid",
                f"{tour}: kalshi ledger scored row {tick} lacks a parseable "
                f"price_ts/result_date ({r.get('price_ts')!r}, {rd!r})",
                severity="error", entity=f"kalshi:{tick}",
                evidence={"priceTs": repr(r.get("price_ts")), "resultDate": repr(rd)})
        else:
            anchor += pd.Timedelta(hours=PREMATCH_UTC_HOUR)
            if ts > anchor:
                _add_finding(
                    out, "output.kalshi_ledger.quote_after_anchor",
                    f"{tour}: kalshi ledger scored row {tick} quoted after its "
                    f"08:00 anchor ({r.get('price_ts')} > {rd} 08:00Z) — "
                    f"occurrence-anchored/in-play print",
                    severity="error", entity=f"kalshi:{tick}",
                    evidence={"priceTs": str(r.get("price_ts")), "resultDate": str(rd),
                              "anchorHourUtc": PREMATCH_UTC_HOUR})
            elif ts <= anchor - pd.Timedelta(seconds=CANDLE_LOOKBACK_S):
                mids = []
                for c in ("mid_a", "mid_b"):
                    try:
                        mids.append(float(r.get(c) or ""))
                    except ValueError:
                        pass
                if any(not (1 - EXTREME_CARRY_MID < m < EXTREME_CARRY_MID) for m in mids):
                    _add_finding(
                        out, "output.kalshi_ledger.settled_quote_carried",
                        f"{tour}: kalshi ledger scored row {tick} carries a "
                        f"settled-extreme window-edge quote (mids {mids}) — "
                        f"post-result carry print",
                        severity="error", entity=f"kalshi:{tick}",
                        evidence={"mids": mids, "extremeCarryMid": EXTREME_CARRY_MID})
        ka_res, a_won = r.get("kalshi_result_a"), r.get("a_won")
        if (ka_res in ("yes", "no") and a_won in ("0", "1")
                and (ka_res == "yes") != (a_won == "1")):
            _add_finding(
                out, "output.kalshi_ledger.settlement_mismatch",
                f"{tour}: kalshi ledger scored row {tick} settlement "
                f"contradicts its joined result — mis-joined match",
                severity="error", entity=f"kalshi:{tick}",
                evidence={"kalshiResultA": ka_res, "aWon": a_won})
        key = (frozenset((r.get("player_a", ""), r.get("player_b", ""))), rd)
        if key in seen:
            _add_finding(
                out, "output.kalshi_ledger.result_scored_twice",
                f"{tour}: kalshi ledger scores one result twice "
                f"({seen[key]} and {tick}, {rd})",
                severity="error",
                entity=f"result:{':'.join(sorted(_player_identity_key(p) for p in key[0]))}:{rd}",
                evidence={"tickers": [seen[key], tick], "resultDate": str(rd)})
        else:
            seen[key] = tick


def _norm_name(name: str) -> str:
    return " ".join(str(name).split()).casefold()


def _player_identity_key(name: object) -> str:
    """Name key after the same explicit identity aliases used by result ingestion."""
    key = name_key(name)
    return name_key(PLAYER_ALIASES.get(key, name))


def _identity_value(value: object) -> str:
    """Return a provider identity scalar without manufacturing IDs from nulls."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        return ""
    text = str(value).strip()
    return "" if text.casefold() in {"nan", "none", "null"} else text


def _event_entity(event: dict) -> str:
    """Stable event identity for finding fingerprints; display names are evidence only."""
    espn_id = next((value for value in (
        _identity_value(event.get("espnId")),
        _identity_value(event.get("espn_id")),
    ) if value), "")
    if espn_id:
        return f"espn:{espn_id}"
    coverage_key = _identity_value(event.get("coverageKey"))
    if coverage_key:
        if coverage_key.casefold().startswith("espn:"):
            return f"espn:{coverage_key.split(':', 1)[1]}"
        return f"coverage:{coverage_key}"
    draw_source_id = _identity_value(event.get("drawSourceId"))
    if draw_source_id:
        source = _identity_value(event.get("drawSource")) or "provider"
        return f"draw:{source}:{draw_source_id}"
    start = _identity_value(event.get("start"))
    end = _identity_value(event.get("end"))
    if start or end:
        return f"event-window:{start}:{end}"
    return "event:unidentified"


def _event_provider_entity(event: dict) -> str | None:
    """Exact event identity usable across tournament and bracket artifacts.

    ``drawSourceId`` identifies the source draw and deliberately exists only in the
    bracket payload, so it remains a useful finding identity but is not a cross-artifact
    event key. ESPN identity can arrive directly or through an ``espn:`` coverage key.
    """
    espn_id = next((value for value in (
        _identity_value(event.get("espnId")),
        _identity_value(event.get("espn_id")),
    ) if value), "")
    if espn_id:
        return f"espn:{espn_id}"
    coverage_key = _identity_value(event.get("coverageKey"))
    if coverage_key.casefold().startswith("espn:"):
        return _event_entity({"coverageKey": coverage_key})
    return None


def _event_stable_entity(event: dict) -> str | None:
    """Non-window identity that can conclusively match when both artifacts carry it."""
    entity = _event_entity(event)
    if entity == "event:unidentified" or entity.startswith("event-window:"):
        return None
    return entity


def _event_real_player_keys(event: dict) -> set[str]:
    """Canonical real-player evidence carried by either event artifact."""
    players = {
        row.get("name")
        for row in (event.get("projection") or [])
        if isinstance(row, dict)
    }
    players |= {event.get("champion"), event.get("runnerUp")}
    for rounds_key in ("rounds", "bracket"):
        for rnd in event.get(rounds_key) or []:
            if not isinstance(rnd, dict):
                continue
            for match in rnd.get("matches") or []:
                if isinstance(match, dict):
                    players |= {match.get("a"), match.get("b")}
    return {_player_identity_key(player) for player in players if _is_real_name(player)}


def _event_evidence_matches(bracket: dict, tournament: dict) -> bool:
    """Evidence join when at least one event artifact lacks an ESPN identity."""
    from ..data.draws_official import official_dates_match

    if not official_dates_match(
            bracket.get("start"), bracket.get("end") or bracket.get("start"),
            tournament.get("start"), tournament.get("end") or tournament.get("start")):
        return False
    return len(_event_real_player_keys(bracket) & _event_real_player_keys(tournament)) >= 2


def _remembered_bracket_event_entities(tournaments: object,
                                        prev: dict | None) -> dict[str, str]:
    """Keep a bracket-loss baseline until its event leaves the active board.

    A missing bracket must remain missing on the second run rather than disappearing from
    the baseline and falsely recovering. Legacy display-name state is bridged for rollout;
    all newly persisted identity is provider/event based.
    """
    cards = tournaments if isinstance(tournaments, list) else []
    active = {
        _event_entity(card): card for card in cards
        if isinstance(card, dict) and card.get("name")
        and card.get("status") in ("live", "upcoming")
    }
    previous = prev or {}
    raw_entities = previous.get("bracket_event_entities") or {}
    prior_entities = set(raw_entities) if isinstance(raw_entities, (dict, list)) else set()
    legacy_names = set(previous.get("bracket_events") or [])
    remembered: dict[str, str] = {}
    for entity, card in active.items():
        if card.get("hasBracket"):
            remembered[entity] = str(card["name"])
        elif entity in prior_entities:
            remembered[entity] = (str(raw_entities.get(entity))
                                  if isinstance(raw_entities, dict)
                                  and raw_entities.get(entity) else str(card["name"]))
        elif _norm_name(card.get("name")) in legacy_names:
            remembered[entity] = str(card["name"])
    return remembered


def _match_entity(match: dict, *, event_entity: str | None = None,
                  player_a: object = None, player_b: object = None,
                  fallback: str = "unidentified") -> str:
    """Prefer a match ID; otherwise bind an unordered canonical pair to its event."""
    match_id = next((value for value in (
        _identity_value(match.get("matchId")),
        _identity_value(match.get("match_id")),
        _identity_value(match.get("id")),
    ) if value), "")
    if match_id:
        return f"match:{match_id}"
    base = event_entity or _event_entity(match)
    if base == "event:unidentified":
        date = _identity_value(match.get("date"))
        if date:
            base = f"event-date:{date}"
    pair = sorted(filter(None, (
        _player_identity_key(player_a),
        _player_identity_key(player_b),
    )))
    if pair:
        return f"{base}#players:{':'.join(pair)}"
    return f"{base}#{fallback}"


def cross_tour_findings(outputs: dict) -> list[HealthFinding]:
    """Typed findings only visible with BOTH tours' boards in hand.

    A combined event is one venue, one week, one court — the DC Open and every Slam ship a
    card on each tour. When those two cards disagree about the surface, at least one of them
    is provably wrong, and no per-tour check can ever see it: on 2026-07-27 both tours shipped
    the DC Open as Grass in the middle of the hard-court swing and every single-tour invariant
    passed. Advisory, because which side is wrong is not knowable from here.

    ``outputs`` is ``{tour: read_outputs(tour)}``. Combined ATP/WTA cards share ESPN's
    event registry ID. Display names are never a join key because sponsor titles can differ
    across tours or change mid-event; id-less cards are skipped rather than guessed.
    """
    per: dict[str, dict] = {}
    for tour, oc in sorted(outputs.items()):
        for t in ((oc.get("data") or {}).get("tournaments") or []):
            event_id = _identity_value(t.get("espnId")) if isinstance(t, dict) else ""
            if event_id:
                per.setdefault(event_id, {})[tour] = t
    out = _FindingCollector("cross", None)
    for event_id, cards in sorted(per.items()):
        if len(cards) < 2:
            continue
        ta, tb = sorted(cards)
        a, b = cards[ta], cards[tb]
        sa, sb = a.get("surface"), b.get("surface")
        if sa and sb and sa != sb:
            _add_finding(
                out, "cross.tournament.surface_mismatch",
                f"{ta}/{tb}: tournament {a.get('name')!r} surface split across tours "
                f"({ta}={sa}, {tb}={sb}) — one board is wrong about the court",
                severity="warning", entity=f"espn:{event_id}",
                evidence={"tours": [ta, tb], "surfaces": {ta: sa, tb: sb},
                          "espnId": event_id,
                          "names": {ta: str(a.get("name") or ""),
                                    tb: str(b.get("name") or "")}})
    return out.findings


def cross_tour_problems(outputs: dict) -> list[str]:
    """Compatibility strings for callers not yet consuming health-finding-v1."""
    return _finding_messages(cross_tour_findings(outputs))


def _overlap_days(a: dict, b: dict) -> int:
    """Days two tournaments' [start,end] ranges overlap (ISO dates sort lexically).
    <=0 means they only touch at a boundary or are disjoint."""
    sa, ea, sb, eb = a.get("start"), a.get("end"), b.get("start"), b.get("end")
    if not (sa and ea and sb and eb):
        return 0
    lo, hi = max(sa, sb), min(ea, eb)
    if hi < lo:
        return 0
    return (pd.Timestamp(hi) - pd.Timestamp(lo)).days


def _tournament_name_problems(out: list, tour: str, ts: list) -> None:
    """Tournament names churn year-over-year (sponsor renames, new events); a rename the
    pipeline doesn't reconcile splits one event into two rows. Two symptoms, both bugs:
      A) the exact same name twice in one snapshot (a dedup/naming split), and
      B) two DIFFERENTLY-named, identity-unknown events that overlap in dates AND share
         players — usually one event under two names. Distinct stable ids are stronger
         evidence and bypass this fallback: successive tournament calendar ranges can
         overlap while players legally move between them (Toronto/Washington 2026).

    (B) counts only slots naming a REAL player, via the same `is_real` predicate the draw
    machinery uses to fill them. Unresolved slots are `Qualifier 1..N`, numbered per draw,
    so every pair of concurrent events with open qualifying "shares" a dozen identical
    strings that are not players at all. That false-positived on 2026-07-24 (issue #9):
    Washington ('Mubadala Citi DC Open', WTA 500) and Memphis (WTA 250) run the same week
    with entirely different fields — Pegula/Svitolina vs Alexandrova/Golubic — and were
    reported as one event under two names on 20 shared `Qualifier N` placeholders and zero
    shared players. Same class as the drawSize/placeholder trap above: a name-set invariant
    must exclude the slots that do not name anyone.
    """
    named = [t for t in ts if isinstance(t, dict) and t.get("name")]
    dup = {k for k, n in Counter(_norm_name(t["name"]) for t in named).items() if n > 1}
    for key in sorted(dup):
        duplicated = [t for t in named if _norm_name(t["name"]) == key]
        names = sorted({t["name"] for t in duplicated})
        starts = sorted(str(t.get("start") or "") for t in duplicated)
        entities = sorted({_event_entity(t) for t in duplicated})
        _add_finding(
            out, "output.tournament.possible_duplicate_card",
            f"{tour}: tournaments.json lists the same event more than once "
            f"({', '.join(names)}) — a naming/dedup split",
            severity="warning", entity=f"duplicate-event:{'|'.join(entities)}",
            evidence={"names": names, "starts": starts, "reason": "duplicate_name"})

    def _real_field(t: dict) -> set:
        return {p.get("name") for p in t.get("projection", [])
                if is_real_participant(p.get("name"))}

    for a, b in itertools.combinations(named, 2):
        if _norm_name(a["name"]) == _norm_name(b["name"]) or _overlap_days(a, b) < 2:
            continue
        aid, bid = a.get("espnId"), b.get("espnId")
        if aid and bid and str(aid) != str(bid):
            continue                       # stable identity outranks a name/player heuristic
        fa, fb = _real_field(a), _real_field(b)
        shared = fa & fb
        # Two rules, because dropping the placeholders also dropped the counts: >=3 shared
        # is the robust signal once a draw is filled, but a rename caught the day the draw
        # is released may only have 2 names in it yet — and there, one field being wholly
        # contained in the other is just as impossible for distinct events. Both need >=2
        # real names, or an all-qualifier draw would be "contained" in everything.
        split = len(shared) >= 3 or (
            min(len(fa), len(fb)) >= 2 and (shared == fa or shared == fb))
        if split:
            pair_key = "|".join(sorted({_event_entity(a), _event_entity(b)}))
            _add_finding(
                out, "output.tournament.possible_duplicate_card",
                f"{tour}: {a['name']!r} and {b['name']!r} overlap in dates and share "
                f"{len(shared)} players — likely one event under two names (YoY rename?)",
                severity="warning",
                entity=f"event-pair:{pair_key}",
                evidence={"names": [str(a["name"]), str(b["name"])],
                          "sharedPlayers": sorted(map(str, shared)),
                          "overlapDays": _overlap_days(a, b)})


def _check_method(out: list, tour: str, method: dict, meta: dict | None) -> None:
    """method.json publishes the effective production parameters to the /method page.
    Sanity only — never pin tuned values here (those live in test_export.py); the gate
    catches a build that would render impossible constants or drift from meta.json."""
    required = ["elo", "serveReturn", "context", "tiers", "combiner", "protocol"]
    if tour == "wta":
        required.append("stateGate")
    missing = [k for k in required
               if not isinstance(method.get(k), dict)]
    if missing:
        _add_finding(
            out, "output.method.section_missing",
            f"{tour}: method.json missing section(s) {', '.join(missing)}",
            severity="error", entity="artifact:method.json",
            evidence={"sections": missing})
        return
    if method.get("tour") != tour:
        _add_finding(
            out, "output.method.tour_mismatch",
            f"{tour}: method.json says tour={method.get('tour')!r}",
            severity="error", entity="artifact:method.json",
            evidence={"expected": tour, "actual": repr(method.get("tour"))})
    elo = method["elo"]
    for key, ok in (("ratingScale", lambda v: v > 0), ("kScale", lambda v: v > 0),
                    ("surfaceBlend", lambda v: 0 <= v <= 1), ("movCap", lambda v: v >= 1)):
        v = elo.get(key)
        if not isinstance(v, (int, float)) or not ok(v):
            _add_finding(
                out, "output.method.elo_parameter_invalid",
                f"{tour}: method.json elo.{key}={v!r} out of range",
                severity="error", entity=f"artifact:method.json#elo:{key}",
                evidence={"parameter": key, "value": repr(v)})
    mults = method["tiers"].get("kMult")
    if not isinstance(mults, dict) or not mults or \
            any(not isinstance(v, (int, float)) or not 0.3 < v < 2.0 for v in mults.values()):
        _add_finding(
            out, "output.method.tier_multiplier_invalid",
            f"{tour}: method.json tiers.kMult implausible ({mults!r})",
            severity="error", entity="artifact:method.json#tiers:kMult",
            evidence={"value": repr(mults)})
    comb = method["combiner"]
    nfeat = comb.get("featureCount")
    if nfeat != len(FEATURES):
        _add_finding(
            out, "output.method.feature_count_invalid",
            f"{tour}: method.json featureCount {nfeat} != {len(FEATURES)} (schema drift)",
            severity="error", entity="artifact:method.json#combiner:featureCount",
            evidence={"actual": nfeat, "expected": len(FEATURES)})
    feats = (meta or {}).get("features")
    if isinstance(feats, list) and nfeat != len(feats):
        _add_finding(
            out, "output.method.meta_feature_count_mismatch",
            f"{tour}: method.json featureCount {nfeat} != meta.features {len(feats)}",
            severity="error", entity="artifact:method.json#combiner:featureCount",
            evidence={"methodCount": nfeat, "metaCount": len(feats)})
    if not isinstance(comb.get("nBag"), int) or comb["nBag"] < 1:
        _add_finding(
            out, "output.method.bag_count_invalid",
            f"{tour}: method.json combiner.nBag={comb.get('nBag')!r} invalid",
            severity="error", entity="artifact:method.json#combiner:nBag",
            evidence={"value": repr(comb.get("nBag"))})
    if tour == "wta":
        gate = method["stateGate"]
        expected = WTA_DUAL_STATE_GATE_THRESHOLD
        if gate.get("enabled") is not (expected is not None):
            _add_finding(
                out, "output.method.state_gate_enabled_mismatch",
                f"{tour}: method.json stateGate.enabled={gate.get('enabled')!r} "
                f"does not match config",
                severity="error", entity="artifact:method.json#stateGate:enabled",
                evidence={"actual": repr(gate.get("enabled")),
                          "expected": expected is not None})
        if gate.get("minMainMatches") != expected:
            _add_finding(
                out, "output.method.state_gate_threshold_mismatch",
                f"{tour}: method.json stateGate.minMainMatches="
                f"{gate.get('minMainMatches')!r} (expected {expected!r})",
                severity="error", entity="artifact:method.json#stateGate:minMainMatches",
                evidence={"actual": repr(gate.get("minMainMatches")),
                          "expected": repr(expected)})
        if gate.get("trainingPopulation") != "main-only":
            _add_finding(
                out, "output.method.state_gate_population_mismatch",
                f"{tour}: method.json stateGate training population is not main-only",
                severity="error", entity="artifact:method.json#stateGate:trainingPopulation",
                evidence={"actual": repr(gate.get("trainingPopulation")),
                          "expected": "main-only"})


def _coverage_summary(coverage: object, tournaments: object) -> dict:
    """Exact expected + shipped key lists embedded in health.json for live parity checks."""
    events = coverage.get("events") if isinstance(coverage, dict) else []
    cards = tournaments if isinstance(tournaments, list) else []
    return {
        "expectedKeys": sorted(str(e.get("key")) for e in (events or [])
                               if isinstance(e, dict) and e.get("key")),
        "shippedKeys": sorted(str(t.get("coverageKey")) for t in cards
                              if isinstance(t, dict) and t.get("coverageKey")),
    }


def _check_event_coverage(out: list, tour: str, coverage: dict, tournaments: list) -> None:
    """Every independently observed begun event occurs exactly once on the board."""
    if coverage.get("version") != 1:
        _add_finding(
            out, "output.event_coverage.version_invalid",
            f"{tour}: event_coverage.json version {coverage.get('version')!r} is not 1",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"actual": repr(coverage.get("version")), "expected": 1})
    if coverage.get("tour") != tour:
        _add_finding(
            out, "output.event_coverage.tour_mismatch",
            f"{tour}: event_coverage.json says tour={coverage.get('tour')!r}",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"actual": repr(coverage.get("tour")), "expected": tour})
    events = coverage.get("events")
    if not isinstance(events, list):
        _add_finding(
            out, "output.event_coverage.events_invalid",
            f"{tour}: event_coverage.json events is not a list",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"valueType": type(events).__name__})
        return

    expected: dict[str, list[str]] = {}
    malformed = 0
    for event in events:
        if not isinstance(event, dict) or not event.get("key") or not event.get("name"):
            malformed += 1
            continue
        expected.setdefault(str(event["key"]), []).append(str(event["name"]))
    if malformed:
        _add_finding(
            out, "output.event_coverage.expected_event_invalid",
            f"{tour}: event_coverage.json has {malformed} malformed expected event(s)",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"malformedEvents": malformed})
    for key, names in sorted(expected.items()):
        if len(names) > 1:
            _add_finding(
                out, "output.event_coverage.expected_key_duplicate",
                f"{tour}: event_coverage.json repeats coverage key {key} "
                f"for {len(names)} expected events",
                severity="error", entity=_event_entity({"coverageKey": key}),
                evidence={"coverageKey": key, "eventNames": names})

    shipped = Counter()
    shell_names: dict[str, str] = {}
    missing_keys = []
    for card in tournaments:
        if not isinstance(card, dict):
            continue
        key = card.get("coverageKey")
        if not key:
            missing_keys.append(card.get("name"))
        else:
            shipped[str(key)] += 1
            if card.get("coverageOnly"):
                shell_names[str(key)] = str(card.get("name"))
    if missing_keys:
        shown = ", ".join(repr(n) for n in missing_keys[:3])
        _add_finding(
            out, "output.event_coverage.card_key_missing",
            f"{tour}: tournaments.json has {len(missing_keys)} card(s) without a "
            f"coverageKey ({shown})",
            severity="error", entity="artifact:tournaments.json",
            evidence={"eventNames": [str(name) for name in missing_keys]})

    for key, names in sorted(expected.items()):
        count = shipped[key]
        name = names[0]
        if count == 0:
            _add_finding(
                out, "output.event_coverage.missing_card",
                f"{tour}: begun tournament {name!r} (coverage key {key}) is missing "
                f"from tournaments.json",
                severity="error", entity=_event_entity({"coverageKey": key}),
                evidence={"name": name, "coverageKey": key})
        elif count > 1:
            _add_finding(
                out, "output.event_coverage.card_duplicate",
                f"{tour}: begun tournament {name!r} coverage key {key} appears "
                f"{count} times in tournaments.json",
                severity="error", entity=_event_entity({"coverageKey": key}),
                evidence={"eventName": name, "coverageKey": key, "count": count})

    recorded = coverage.get("shippedKeys")
    actual = sorted(key for key, count in shipped.items() for _ in range(count))
    if not isinstance(recorded, list) or sorted(str(k) for k in recorded) != actual:
        _add_finding(
            out, "output.event_coverage.shipped_keys_mismatch",
            f"{tour}: event_coverage.json shippedKeys does not match tournaments.json",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"recorded": list(map(str, recorded)) if isinstance(recorded, list) else None,
                      "actual": actual})

    recorded_shells = coverage.get("shellKeys")
    actual_shells = sorted(shell_names)
    if not isinstance(recorded_shells, list) or sorted({str(k) for k in recorded_shells}) != actual_shells:
        _add_finding(
            out, "output.event_coverage.shell_keys_mismatch",
            f"{tour}: event_coverage.json shellKeys does not match coverageOnly cards",
            severity="error", entity="artifact:event_coverage.json",
            evidence={"recorded": list(map(str, recorded_shells))
                      if isinstance(recorded_shells, list) else None,
                      "actual": actual_shells})
    for key in actual_shells:
        _add_finding(
            out, "output.event_coverage.shell_only",
            f"{tour}: begun tournament {shell_names[key]!r} (coverage key {key}) is "
            f"represented only by a coverage shell",
            severity="error", entity=_event_entity({"coverageKey": key}),
            evidence={"eventName": shell_names[key], "coverageKey": key})


def _stage_success_overdue(value: object, observed_at: pd.Timestamp) -> bool:
    stamp = pd.to_datetime(value, utc=True, errors="coerce") if value else pd.NaT
    if pd.isna(stamp):
        return False
    now_utc = observed_at if observed_at.tzinfo else observed_at.tz_localize("UTC")
    return now_utc - stamp > pd.Timedelta(hours=PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS)


def _public_stage_error_type(value: object) -> str:
    """Safe, stable public category; detailed exception prose stays in the private receipt."""
    text = str(value or "StageError")
    return text if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,119}", text) else "StageError"


def _check_pipeline_stage_status(
    out: _FindingCollector,
    tour: str,
    snapshot: object,
    observed_at: pd.Timestamp,
    *,
    expected: bool,
) -> None:
    """Surface durable soft-fail outcomes without turning them into deploy blockers."""
    if not isinstance(snapshot, dict) or snapshot.get("state") == "missing":
        # Rollout/fresh clones have no receipt until the first attempted stage. Absence alone
        # proves failure only after meta declares that this producer version owns the receipt.
        if expected:
            _add_finding(
                out,
                "output.pipeline_stage.receipt_missing",
                f"{tour}: expected private {STAGE_STATUS_FILENAME} is missing",
                severity="warning",
                entity=f"artifact:{STAGE_STATUS_FILENAME}",
                evidence={"expectedSchema": STAGE_STATUS_SCHEMA},
            )
        return
    if snapshot.get("state") != "valid":
        _add_finding(
            out,
            "output.pipeline_stage.receipt_malformed",
            f"{tour}: {STAGE_STATUS_FILENAME} is present but malformed",
            severity="warning",
            entity=f"artifact:{STAGE_STATUS_FILENAME}",
            evidence={
                "errorType": _public_stage_error_type(snapshot.get("errorType")),
            },
        )
        return

    receipt = snapshot.get("receipt") or {}
    if expected:
        missing_stages = sorted(PRODUCT_STAGE_NAMES - set(receipt.get("stages") or {}))
        if missing_stages:
            _add_finding(
                out,
                "output.pipeline_stage.receipt_incomplete",
                f"{tour}: {STAGE_STATUS_FILENAME} lacks expected product stage(s) "
                f"{missing_stages}",
                severity="warning",
                entity=f"artifact:{STAGE_STATUS_FILENAME}",
                evidence={"missingStages": missing_stages},
            )
    for stage, record in sorted((receipt.get("stages") or {}).items()):
        criticality = record["criticality"]
        if record["outcome"] == "failure":
            error_type = _public_stage_error_type(record["error"].get("type"))
            evidence = {
                "criticality": criticality,
                "errorType": error_type,
            }
            _add_finding(
                out,
                "output.pipeline_stage.current_failure",
                f"{tour}: pipeline stage {stage!r} most recently failed ({error_type})",
                severity="warning" if criticality == "product" else "info",
                entity=f"pipeline-stage:{stage}",
                evidence=evidence,
            )
            # One continuing failure is one incident. Per-attempt timestamps, duration,
            # inputs, and detailed errors remain private so an hourly retry neither leaks
            # provider detail nor churns the public issue revision.
            continue

        if criticality != "product":
            continue
        if _stage_success_overdue(record.get("lastSuccessAt"), observed_at):
            _add_finding(
                out,
                "output.pipeline_stage.success_overdue",
                f"{tour}: product pipeline stage {stage!r} has not succeeded within "
                f"{PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS}h",
                severity="warning",
                entity=f"pipeline-stage:{stage}",
                evidence={
                    "lastSuccessAt": record["lastSuccessAt"],
                    "maxHours": PRODUCT_STAGE_MAX_SUCCESS_AGE_HOURS,
                    "lastSuccessInputFingerprint": record["lastSuccessInputFingerprint"],
                },
            )


def output_findings(tour: str, oc: dict, now: pd.Timestamp,
                    prev: dict | None = None, *,
                    observed_at: pd.Timestamp | None = None) -> list[HealthFinding]:
    """Typed produced-artifact findings; pure for one read_outputs() snapshot."""
    out = _FindingCollector("output", tour)
    data = oc.get("data", {})
    prev = prev or {}
    meta = data.get("meta")
    _check_pipeline_stage_status(
        out,
        tour,
        oc.get("stage_status"),
        observed_at if observed_at is not None else now,
        expected=isinstance(meta, dict) and meta.get("stageStatusSchema") == STAGE_STATUS_SCHEMA,
    )
    for stem in oc.get("missing", []):
        _add_finding(out, "output.artifact.required_missing", f"{tour}: {stem}.json missing",
                     entity=f"artifact:{stem}.json", evidence={"artifact": f"{stem}.json"})
    for stem in oc.get("corrupt", []):
        _add_finding(out, "output.artifact.required_unparseable",
                     f"{tour}: {stem}.json is present but unparseable",
                     entity=f"artifact:{stem}.json", evidence={"artifact": f"{stem}.json"})
    for filename in oc.get("missing_files", []):
        _add_finding(out, "output.artifact.referenced_missing",
                     f"{tour}: referenced artifact {filename!r} missing or unsafe",
                     entity=f"artifact:{filename}", evidence={"artifact": filename})
    for filename in oc.get("corrupt_files", []):
        _add_finding(out, "output.artifact.referenced_unparseable",
                     f"{tour}: referenced artifact {filename!r} is unparseable",
                     entity=f"artifact:{filename}", evidence={"artifact": filename})
    draw_cache_status = oc.get("draw_cache_status")
    if (isinstance(draw_cache_status, dict)
            and draw_cache_status.get("state") in {
                "degraded", "malformed", "unreadable"}):
        state = str(draw_cache_status["state"])
        evidence = {"state": state}
        if draw_cache_status.get("errorType"):
            evidence["errorType"] = str(draw_cache_status["errorType"])
        failures = draw_cache_status.get("failures") or []
        if failures:
            evidence["failureTypes"] = sorted({
                f"{item.get('source')}:{item.get('errorType')}"
                for item in failures if isinstance(item, dict)
            })
        _add_finding(
            out,
            "output.draw_cache.invalid",
            f"{tour}: tournament_draws.json is present but {state}",
            severity="warning",
            entity="artifact:tournament_draws.json",
            evidence=evidence,
        )
    draw_cache = oc.get("draw_cache")
    if isinstance(draw_cache, dict):
        from .draws import duplicate_draw_source_incidents
        for identity, detail in duplicate_draw_source_incidents(draw_cache):
            _add_finding(out, "output.draw_source.duplicate_attachment",
                         f"{tour}: tournament_draws.json {detail}",
                         entity=f"draw-source:{identity}", evidence={"detail": detail})
    offseason = _offseason(now)

    if isinstance(meta, dict):
        feats = meta.get("features")
        nfeat = len(feats) if isinstance(feats, list) else None
        if nfeat != len(FEATURES):
            _add_finding(out, "output.meta.feature_count_mismatch",
                         f"{tour}: meta.features has {nfeat} entries (expected {len(FEATURES)})",
                         entity="artifact:meta.json", evidence={"actual": nfeat, "expected": len(FEATURES)})
        if isinstance(feats, list) and any(
                any(token in str(feature).lower() for token in ("expect", "performance", "residual"))
                for feature in feats):
            _add_finding(out, "output.meta.display_feature_leak",
                         f"{tour}: display-only expectation metric leaked into meta.features",
                         entity="artifact:meta.json")
        n = meta.get("matches")
        population_version = meta.get("matchPopulationVersion")
        if not _plain_int(population_version) or population_version != MATCH_POPULATION_VERSION:
            _add_finding(out, "output.population.match_version_mismatch",
                         f"{tour}: meta.matchPopulationVersion={population_version!r} "
                         f"(expected {MATCH_POPULATION_VERSION})",
                         entity=f"match-population:{tour}",
                         evidence={"actual": population_version, "expected": MATCH_POPULATION_VERSION})
        model_population_version = meta.get("modelPopulationVersion")
        if (not _plain_int(model_population_version)
                or model_population_version != MATCH_POPULATION_VERSION):
            _add_finding(out, "output.population.model_version_mismatch",
                         f"{tour}: meta.modelPopulationVersion={model_population_version!r} "
                         f"does not match current population {MATCH_POPULATION_VERSION}",
                         entity=f"match-population:{tour}", evidence={
                             "actual": model_population_version, "expected": MATCH_POPULATION_VERSION})
        if tour == "wta":
            expected_gate = WTA_DUAL_STATE_GATE_THRESHOLD
            if ("dualStateThreshold" not in meta
                    or meta.get("dualStateThreshold") != expected_gate):
                _add_finding(out, "output.population.dual_state_threshold_mismatch",
                             f"{tour}: meta.dualStateThreshold="
                             f"{meta.get('dualStateThreshold')!r} (expected {expected_gate!r})",
                             entity="model-population:wta", evidence={
                                 "actual": meta.get("dualStateThreshold"), "expected": expected_gate})
            expected_ready = expected_gate is not None
            if meta.get("dualStateReady") is not expected_ready:
                _add_finding(out, "output.population.dual_state_ready_mismatch",
                             f"{tour}: meta.dualStateReady={meta.get('dualStateReady')!r} "
                             f"(expected {expected_ready!r})", entity="model-population:wta",
                             evidence={"actual": meta.get("dualStateReady"),
                                       "expected": expected_ready})
        floor = HEALTH_MIN_MATCHES.get(tour, 0)
        if not _plain_int(n) or n < floor:
            _add_finding(out, "output.population.match_count_below_floor",
                         f"{tour}: meta.matches {n} below floor {floor}",
                         entity=f"match-population:v{population_version}",
                         evidence={"matches": n, "floor": floor, "version": population_version})
        else:
            high, high_version = _population_high_water(tour, meta, prev)
            if (high_version == population_version == model_population_version
                    and _plain_int(high) and n < high - 50):
                _add_finding(out, "output.population.match_count_drop",
                             f"{tour}: meta.matches dropped {high} -> {n}",
                             entity=f"match-population:v{population_version}",
                             evidence={"highWater": high, "matches": n,
                                       "version": population_version})
        if tour == "wta":
            wta125 = meta.get("wta125Matches")
            if not isinstance(wta125, int) or isinstance(wta125, bool):
                _add_finding(out, "output.population.wta125_audit_missing",
                             "wta: meta.wta125Matches missing/unparseable",
                             entity="model-population:wta")
            elif wta125 != 0:
                _add_finding(out, "output.population.wta125_policy_leak",
                             f"wta: model contains {wta125} WTA 125 match(es) while "
                             "INCLUDE_WTA_125 is disabled", entity="model-population:wta",
                             evidence={"matches": wta125})
            excluded_125 = meta.get("excludedWta125Matches")
            excluded_unknown = meta.get("excludedUnclassifiedWtaLiveMatches")
            for field, value in (("excludedWta125Matches", excluded_125),
                                 ("excludedUnclassifiedWtaLiveMatches", excluded_unknown)):
                if (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                    _add_finding(out, "output.population.exclusion_audit_invalid",
                                 f"wta: meta.{field} missing/invalid ({value!r})",
                                 entity=f"meta:{field}", evidence={"value": value})
            if isinstance(excluded_unknown, int) and excluded_unknown > 0:
                _add_finding(out, "output.population.unclassified_live_withheld",
                             f"wta: {excluded_unknown} unclassified live match(es) withheld "
                             "from model ingestion", severity="warning",
                             entity="model-population:wta", evidence={"matches": excluded_unknown})
        ap, players = meta.get("activePlayers"), data.get("players")
        if isinstance(players, list) and ap is not None and len(players) != ap:
            _add_finding(out, "output.players.active_count_mismatch",
                         f"{tour}: players.json has {len(players)} rows but meta.activePlayers={ap}",
                         entity="artifact:players.json", evidence={"rows": len(players), "active": ap})
        age = _age_days(meta.get("lastUpdated"), now)
        if age is None:
            _add_finding(out, "output.meta.build_timestamp_invalid",
                         f"{tour}: meta.lastUpdated missing/unparseable ({meta.get('lastUpdated')!r})",
                         entity="artifact:meta.json", evidence={"lastUpdated": meta.get("lastUpdated")})
        elif age > HEALTH_MAX_BUILD_AGE_DAYS:
            _add_finding(out, "output.meta.build_stale",
                         f"{tour}: outputs last built {age}d ago (max {HEALTH_MAX_BUILD_AGE_DAYS})",
                         severity="warning", entity="artifact-generation",
                         evidence={"ageDays": age, "maxDays": HEALTH_MAX_BUILD_AGE_DAYS})
        # Retrain liveness. The check above cannot see this: the hourly quick refresh
        # rewrites lastUpdated while reusing the saved predictor, so a daily retrain that
        # has been red for days keeps shipping a freshly-stamped site off a rotting model
        # (2026-07-19..24). A missing stamp means a pickle predating it — stay silent
        # rather than alert on every tour until the next full run fills it in.
        trained = _age_days(meta.get("modelTrainedAt"), now)
        if trained is not None and trained > HEALTH_MAX_MODEL_AGE_DAYS:
            _add_finding(out, "output.model.training_stale",
                         f"{tour}: model last retrained {trained}d ago "
                         f"(max {HEALTH_MAX_MODEL_AGE_DAYS}) — the daily full run is failing while "
                         f"the quick refresh keeps deploying", severity="warning",
                         entity=f"predictor:{tour}", evidence={
                             "ageDays": trained, "maxDays": HEALTH_MAX_MODEL_AGE_DAYS})

    method = data.get("method")
    if isinstance(method, dict):
        _check_method(out, tour, method, meta if isinstance(meta, dict) else None)

    players = data.get("players")
    if isinstance(players, list) and players:
        if [p.get("eloRank") for p in players] != list(range(1, len(players) + 1)):
            _add_finding(out, "output.players.rank_order_invalid",
                         f"{tour}: players.json eloRank not contiguous 1..{len(players)}",
                         entity="artifact:players.json", evidence={"players": len(players)})
        if any(not p.get("name") or p.get("elo") is None for p in players):
            _add_finding(out, "output.players.required_field_missing",
                         f"{tour}: players.json has a null name or elo",
                         entity="artifact:players.json")
        _flag_placeholders(
            out, tour, "players.json", (p.get("name") for p in players),
            entity="artifact:players.json",
        )
        # enrichment fields are nullable by design (old snapshots lack the keys), but a
        # PRESENT value must be sane: a units slip (64.2 for 0.642) or junk height would
        # ship wrong numbers to every board that renders them
        bad_h = [(p.get("name"), p.get("heightCm")) for p in players
                 if p.get("heightCm") is not None
                 and not (isinstance(p.get("heightCm"), int) and 140 <= p["heightCm"] <= 225)]
        if bad_h:
            _add_finding(out, "output.players.height_invalid",
                         f"{tour}: players.json heightCm implausible for {len(bad_h)} player(s), "
                         f"e.g. {bad_h[0][0]!r}={bad_h[0][1]!r} (expect int in 140..225)",
                         entity="artifact:players.json", evidence={"count": len(bad_h),
                                                                    "example": list(bad_h[0])})
        bad_pct = [(p.get("name"), k, p.get(k)) for p in players for k in _PLAYER_PCT_FIELDS
                   if p.get(k) is not None and not _is_prob(p.get(k))]
        if bad_pct:
            n0, k0, v0 = bad_pct[0]
            _add_finding(out, "output.players.percentage_invalid",
                         f"{tour}: players.json {k0}={v0!r} for {n0!r} out of [0,1] "
                         f"({len(bad_pct)} bad value(s))", entity="artifact:players.json",
                         evidence={"count": len(bad_pct), "player": n0, "field": k0, "value": v0})
        if not offseason:
            frac = sum(1 for p in players if p.get("liveRank") is None) / len(players)
            if frac > HEALTH_MAX_LIVERANK_NULL_FRAC:
                _add_finding(out, "output.players.live_rank_coverage_low",
                             f"{tour}: {frac:.0%} of top players have no liveRank "
                             f"(max {HEALTH_MAX_LIVERANK_NULL_FRAC:.0%}) — rankings source may have drifted",
                             severity="warning", entity="artifact:players.json",
                             evidence={"fraction": frac, "maxFraction": HEALTH_MAX_LIVERANK_NULL_FRAC})

    matrix_index = data.get("matrix-index")
    if isinstance(matrix_index, dict):
        _check_matrix_shards(out, tour, matrix_index, oc.get("shards") or {})
        if (isinstance(meta, dict) and meta.get("modelTrainedAt")
                and matrix_index.get("generation") != meta.get("modelTrainedAt")):
            _add_finding(out, "output.generation.matrix_mismatch",
                         f"{tour}: matrix-index.json generation disagrees with meta.modelTrainedAt",
                         entity="artifact:matrix-index.json")
    profile_index = data.get("profile-index")
    if isinstance(profile_index, dict):
        _check_profile_shards(out, tour, profile_index, oc.get("shards") or {}, players)
        if (isinstance(meta, dict) and meta.get("modelTrainedAt")
                and profile_index.get("generation") != meta.get("modelTrainedAt")):
            _add_finding(out, "output.generation.profile_mismatch",
                         f"{tour}: profile-index.json generation disagrees with meta.modelTrainedAt",
                         entity="artifact:profile-index.json")

    ts = data.get("tournaments")
    event_ranges: dict[str, tuple[pd.Timestamp, pd.Timestamp, str]] = {}
    if isinstance(ts, list):
        if not ts and not offseason:
            _add_finding(out, "output.tournament.board_empty",
                         f"{tour}: tournaments.json is empty", severity="warning",
                         entity="artifact:tournaments.json")
        elif ts and not offseason and not any(t.get("status") in ("live", "upcoming") for t in ts):
            _add_finding(out, "output.tournament.no_active_event",
                         f"{tour}: tournaments.json has no live/upcoming event", severity="warning",
                         entity="artifact:tournaments.json")
        for t in ts:
            if isinstance(t, dict):
                _check_tournament(out, tour, t, now)
        # One identity, one card. Two cards sharing an espnId is the duplicate-event class
        # made checkable at last: on 2026-07-28 the WTA board shipped a 12-player "Washington
        # Dc" fragment beside the full "Mubadala DC Open" — one tournament, two cards, two
        # different favourites. BLOCKING, because `_coalesce_groups` merges before projecting,
        # so a duplicate reaching here means that merge failed and one card is built on a
        # partial event. Verified against the live board before landing: zero duplicates.
        ids: dict = {}
        for t in ts:
            if isinstance(t, dict) and t.get("espnId"):
                ids.setdefault(str(t["espnId"]), []).append(t.get("name"))
        for eid, names in sorted(ids.items()):
            if len(names) > 1:
                shown = ", ".join(repr(n) for n in names)
                _add_finding(out, "output.tournament.duplicate_card",
                             f"{tour}: espnId {eid} ships on {len(names)} cards ({shown}) — "
                             f"one event projected twice, so at least one is a partial record",
                             entity=f"espn:{eid}", evidence={"espnId": eid, "names": names})
        for t in ts:
            if not isinstance(t, dict) or not t.get("espnId"):
                continue
            start = pd.to_datetime(t.get("start"), errors="coerce")
            end = pd.to_datetime(t.get("end"), errors="coerce")
            if pd.notna(start) and pd.notna(end):
                event_ranges[str(t["espnId"])] = (start, end, str(t.get("name") or ""))
        # A live event that HAD a bracket and now doesn't: the cached complete draw pinning
        # its field has gone. That is the 2026-07-27 Wimbledon class — the draw aged out of
        # the ESPN discovery window, the field fell back to a noisy results union and padded
        # to an impossible 256-slot bracket, taking the whole board down. Losing the bracket
        # is the visible early warning. Sentinel-only by construction: `--gate` passes
        # prev=None, so this can never block a deploy, only tell a human.
        live_cards = {
            _event_entity(t): t for t in ts
            if isinstance(t, dict) and t.get("name")
            and t.get("status") in ("live", "upcoming")
        }
        has_now = {
            _event_entity(t) for t in ts
            if isinstance(t, dict) and t.get("name") and t.get("hasBracket")
        }
        previous_entities = prev.get("bracket_event_entities") or {}
        was_entities = set(previous_entities)
        lost_entities = (was_entities & set(live_cards)) - has_now
        if not was_entities:
            # One-release bridge from the legacy display-name state. Identity for the finding
            # still comes from the current card; sponsor prose is used only to locate it.
            was_names = set(prev.get("bracket_events") or [])
            lost_entities = {
                entity for entity, card in live_cards.items()
                if _norm_name(card.get("name")) in was_names and entity not in has_now
            }
        for gone_entity in sorted(lost_entities):
            gone = live_cards[gone_entity].get("name")
            if gone:
                _add_finding(out, "output.tournament.bracket_lost",
                             f"{tour}: live tournament {gone!r} lost its bracket since the "
                             f"previous run — its cached complete draw may have aged out",
                             severity="warning", entity=gone_entity,
                             evidence={
                                 "previousName": previous_entities.get(gone_entity)
                                 if isinstance(previous_entities, dict) else None,
                                 "currentName": gone,
                             })
        _tournament_name_problems(out, tour, ts)

    coverage = data.get("event_coverage")
    if isinstance(coverage, dict) and isinstance(ts, list):
        _check_event_coverage(out, tour, coverage, ts)

    br = data.get("brackets")
    bracket_rounds: dict[tuple[str, frozenset[str]], set[str]] = {}
    if isinstance(br, list):
        _check_brackets(out, tour, br, ts if isinstance(ts, list) else None)
        # One stable event id + exact real-player pair locates a factual bracket round.
        # Build this once for both scheduled and completed-match cross-artifact checks.
        for event in br:
            if not isinstance(event, dict) or not event.get("espnId"):
                continue
            eid = str(event["espnId"])
            for rnd in event.get("rounds") or []:
                round_name = str(rnd.get("round") or "")
                for match in rnd.get("matches") or []:
                    a, b = match.get("a"), match.get("b")
                    if not (_is_real_name(a) and _is_real_name(b)):
                        continue
                    pair = frozenset((_player_identity_key(a), _player_identity_key(b)))
                    if len(pair) == 2:
                        bracket_rounds.setdefault((eid, pair), set()).add(round_name)

    scenario_index = data.get("scenario-index")
    if isinstance(scenario_index, dict):
        _check_scenarios(out, tour, scenario_index, oc.get("shards") or {}, br)

    upcoming_index = data.get("upcoming-index")
    if isinstance(upcoming_index, dict):
        _check_upcoming_shards(out, tour, upcoming_index, oc.get("shards") or {})

    up = data.get("upcoming")
    if isinstance(up, list):
        if not up and not offseason:
            _add_finding(out, "output.upcoming.feed_empty",
                         f"{tour}: upcoming feed is empty", severity="warning",
                         entity="artifact:upcoming.json")
        for m in up:
            match_entity = _match_entity(
                m,
                player_a=m.get("playerA"),
                player_b=m.get("playerB"),
            )
            if m.get("playerA") and m.get("playerA") == m.get("playerB"):
                _add_finding(out, "output.upcoming.identical_players",
                             f"{tour}: upcoming feed row has identical players ({m.get('playerA')!r})",
                             entity=match_entity)
            if not _is_prob(m.get("pA")):
                _add_finding(out, "output.upcoming.probability_invalid",
                             f"{tour}: upcoming feed pA={m.get('pA')!r} out of [0,1]",
                             entity=match_entity, evidence={"pA": m.get("pA")})
            components = m.get("components")
            if (not isinstance(components, dict)
                    or set(components) != {"eloBlend", "pointModel", "combiner"}
                    or any(not _is_prob(value) for value in components.values())):
                _add_finding(out, "output.upcoming.components_invalid",
                             f"{tour}: upcoming prediction components are missing/malformed",
                             entity=match_entity)
            elif abs(float(components["combiner"]) - float(m.get("pA", -1))) > 1e-4:
                _add_finding(out, "output.upcoming.combiner_mismatch",
                             f"{tour}: upcoming combiner component disagrees with pA",
                             entity=match_entity, evidence={
                                 "combiner": components["combiner"], "pA": m.get("pA")})
            _check_prediction_evidence(
                out, tour, f"upcoming {m.get('playerA')!r} vs {m.get('playerB')!r}",
                m.get("evidence"), m.get("playerA"), m.get("playerB"), m.get("pA"),
                entity=match_entity,
            )
            if m.get("forecast") is not None:
                _check_forecast_history(
                    out, tour, f"upcoming {m.get('playerA')!r} vs {m.get('playerB')!r}",
                    m.get("forecast"), current=m.get("pA"), entity=match_entity)
            eid = str(m.get("espnId") or "")
            day = pd.to_datetime(m.get("date"), errors="coerce")
            if eid in event_ranges and pd.notna(day):
                start, end, event_name = event_ranges[eid]
                if day < start or day > end:
                    _add_finding(out, "output.upcoming.date_outside_event",
                                 f"{tour}: upcoming match on {m.get('date')} falls outside "
                                 f"{event_name!r} event bounds {start.date()}..{end.date()} "
                                 f"(espnId {eid})", entity=match_entity, evidence={
                                     "date": m.get("date"), "start": str(start.date()),
                                     "end": str(end.date()), "espnId": eid})
        _flag_placeholders(
            out, tour, "upcoming feed",
            (n for m in up for n in (m.get("playerA"), m.get("playerB"))),
            entity="artifact:upcoming.json",
        )
        _check_watch_ranking(out, tour, up, scenario_index, oc.get("shards") or {})

        # The complete bracket and scoreboard upcoming feed are independent artifacts,
        # joined only on stable ESPN event identity. When an exact real-player pair appears
        # once in that event's bracket, its bracket round is factual. This catches draw-size
        # inference shifts such as Cincinnati 2026 (R16 shipped for an R32 pairing).
        if bracket_rounds:
            for match in up:
                eid = str(match.get("espnId") or "")
                a, b = match.get("playerA"), match.get("playerB")
                if not eid or not (_is_real_name(a) and _is_real_name(b)):
                    continue
                rounds = bracket_rounds.get(
                    (eid, frozenset((_player_identity_key(a), _player_identity_key(b)))))
                if rounds and len(rounds) == 1:
                    bracket_round = next(iter(rounds))
                    upcoming_round = str(match.get("round") or "")
                    if upcoming_round and upcoming_round != bracket_round:
                        _add_finding(out, "output.upcoming.bracket_round_mismatch",
                                     f"{tour}: upcoming round {upcoming_round} disagrees with "
                                     f"bracket round {bracket_round} for {a!r} vs {b!r} "
                                     f"(espnId {eid})", entity=_match_entity(
                                         match, event_entity=f"espn:{eid}",
                                         player_a=a, player_b=b),
                                     evidence={"upcomingRound": upcoming_round,
                                               "bracketRound": bracket_round})

    fx = data.get("fixtures")
    if isinstance(fx, list):
        seen_fixtures: dict[tuple[str, str, str], list[dict]] = {}
        for f in fx:
            mp = f.get("modelProb")
            fixture_entity = _match_entity(
                f,
                player_a=f.get("winner"),
                player_b=f.get("loser"),
            )
            if not _is_prob(mp):
                _add_finding(out, "output.fixture.probability_invalid",
                             f"{tour}: fixtures.json modelProb={mp!r} out of [0,1]",
                             entity=fixture_entity, evidence={"modelProb": mp})
            elif bool(f.get("upset")) != (mp < 0.5):
                _add_finding(out, "output.fixture.upset_flag_mismatch",
                             f"{tour}: fixtures.json upset flag disagrees with modelProb ({mp})",
                             entity=fixture_entity, evidence={"modelProb": mp,
                                                               "upset": f.get("upset")})
            # Cross-source copies can disagree on sponsor title, round, score and tiebreak
            # detail. The same ordered pair cannot complete twice on one calendar date
            # unless a round-robin event legitimately rematches them in a later round. Keep
            # that one exception explicit: same event name, distinct known rounds.
            date, winner, loser = f.get("date"), f.get("winner"), f.get("loser")
            key = (str(date or ""), _player_identity_key(winner), _player_identity_key(loser))
            priors = seen_fixtures.setdefault(key, []) if all(key) else []
            prior = next((old for old in priors
                          if not (_norm_name(old.get("event")) == _norm_name(f.get("event"))
                                  and old.get("round") and f.get("round")
                                  and old.get("round") != f.get("round"))), None)
            if prior is not None:
                _add_finding(out, "output.fixture.duplicate_completed_match",
                             f"{tour}: fixtures.json duplicates one completed fixture "
                             f"({winner!r} d. {loser!r} on {date}; "
                             f"{prior.get('event')!r} and {f.get('event')!r})",
                             entity=fixture_entity, evidence={"date": date,
                                                               "events": [prior.get("event"),
                                                                          f.get("event")]})
            if all(key):
                priors.append(f)
            eid = str(f.get("espnId") or "")
            day = pd.to_datetime(f.get("date"), errors="coerce")
            if eid in event_ranges and pd.notna(day):
                start, end, event_name = event_ranges[eid]
                if day < start or day > end:
                    _add_finding(out, "output.fixture.date_outside_event",
                                 f"{tour}: completed fixture on {f.get('date')} falls outside "
                                 f"{event_name!r} event bounds {start.date()}..{end.date()} "
                                 f"(espnId {eid})", entity=fixture_entity, evidence={
                                     "date": f.get("date"), "start": str(start.date()),
                                     "end": str(end.date()), "espnId": eid})
            if eid and _is_real_name(winner) and _is_real_name(loser):
                rounds = bracket_rounds.get(
                    (eid, frozenset((_player_identity_key(winner),
                                     _player_identity_key(loser)))))
                if rounds and len(rounds) == 1:
                    bracket_round = next(iter(rounds))
                    fixture_round = str(f.get("round") or "")
                    if fixture_round and fixture_round != bracket_round:
                        _add_finding(out, "output.fixture.bracket_round_mismatch",
                                     f"{tour}: fixture round {fixture_round} disagrees with "
                                     f"bracket round {bracket_round} for {winner!r} vs "
                                     f"{loser!r} (espnId {eid})", entity=fixture_entity,
                                     evidence={"fixtureRound": fixture_round,
                                               "bracketRound": bracket_round})

    fc = oc.get("forecast")
    forecast_baseline = _forecast_high_water(None, prev)
    if fc is None and forecast_baseline is not None:
        # Treat disappearance as the terminal form of the same append-only regression,
        # rather than opening a second incident when a shrunken file is subsequently lost.
        # With no persisted baseline an absent log is still a legitimate fresh-clone state.
        _add_finding(out, "output.forecast_log.shrank",
                     f"{tour}: forecast log disappeared after reaching "
                     f"{forecast_baseline} lines",
                     entity=f"forecast-log:{tour}", evidence={
                         "highWaterLines": forecast_baseline,
                         "lines": 0,
                         "artifactState": "absent",
                     })
    elif (fc is not None and _plain_int(fc.get("lines"))
          and forecast_baseline is not None and fc["lines"] < forecast_baseline):
        _add_finding(out, "output.forecast_log.shrank",
                     f"{tour}: forecast log shrank {forecast_baseline} -> {fc['lines']} lines",
                     entity=f"forecast-log:{tour}", evidence={
                         "highWaterLines": forecast_baseline, "lines": fc["lines"]})
    if fc is not None:
        # liveness: the log appends on every run while any upcoming match exists, so a
        # present-but-frozen max(as_of) means the track step is silently failing (or the
        # daily persist push keeps losing). An absent log / empty max stays silent — a
        # fresh clone is legitimate. Gate-ADVISORY: eval history is never a build dependency.
        fc_age = _age_days(fc.get("max_as_of"), now)
        max_fc = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_FORECAST_AGE_DAYS
        if fc_age is not None and fc_age > max_fc:
            _add_finding(out, "output.forecast_log.stale",
                         f"{tour}: forecast log last advanced {fc_age}d ago (max {max_fc}) "
                         f"— the track step may be silently failing", severity="warning",
                         entity=f"forecast-log:{tour}", evidence={
                             "ageDays": fc_age, "maxDays": max_fc})

    kl = oc.get("kalshi_ledger")
    if isinstance(kl, list):
        _check_kalshi_ledger(out, tour, kl)

    tr = data.get("track")
    if isinstance(tr, dict):
        mf = tr.get("matchForecasts") or {}
        g, p, lg = mf.get("graded"), mf.get("pending"), mf.get("logged")
        if all(isinstance(x, int) for x in (g, p, lg)) and g + p != lg:
            _add_finding(out, "output.tracking.count_mismatch",
                         f"{tour}: track.json graded+pending ({g}+{p}) != logged ({lg})",
                         entity=f"forecast-tracking:{tour}", evidence={
                             "graded": g, "pending": p, "logged": lg})
        for call in mf.get("recent") or []:
            if isinstance(call, dict) and call.get("forecast") is not None:
                _check_forecast_history(
                    out, tour, f"completed {call.get('playerA')!r} vs {call.get('playerB')!r}",
                    call.get("forecast"), entity=_match_entity(
                        call,
                        player_a=call.get("playerA"),
                        player_b=call.get("playerB"),
                    ))
        # Model-decay advisory: track.py owns the thresholds (config DRIFT_*) and ships the
        # verdict; we only surface it. Advisory, never deploy-blocking — like market lag,
        # a re-tune recommendation is a benchmark signal, not a build dependency.
        dr = mf.get("drift")
        if isinstance(dr, dict) and dr.get("status") == "drift":
            _add_finding(out, "output.model.forecast_drift",
                         f"{tour}: forecast drift over last {dr.get('n')} graded "
                         f"({dr.get('windowDays')}d): live logloss {dr.get('logloss')} vs "
                         f"self-expected {dr.get('expectedLogloss')} (d=+{dr.get('d')}, "
                         f"t={dr.get('t')}) — model scoring worse than its stated confidence; "
                         f"re-tune recommended", severity="warning", entity=f"predictor:{tour}",
                         evidence={key: dr.get(key) for key in (
                             "n", "windowDays", "logloss", "expectedLogloss", "d", "t")})

    performance = data.get("performance")
    if isinstance(performance, dict):
        _check_performance(out, tour, performance, data.get("profile-index"),
                           oc.get("shards") or {})

    mk = data.get("market")
    if isinstance(mk, dict):
        # matched-odds window trailing the scored matches by months = a book left the
        # odds feed and the benchmark silently froze mid-window (Pinnacle, Jan 2026).
        # Advisory, not deploy-blocking: odds are a benchmark, never a build dependency.
        # Both dates come from the same build, so this needs no off-season relaxation.
        oos_end = pd.to_datetime(mk.get("oosEnd"), errors="coerce")
        last = pd.to_datetime(mk.get("lastMatchedDate"), errors="coerce")
        if pd.notna(oos_end) and pd.notna(last):
            lag = int((oos_end - last).days)
            if lag > HEALTH_MAX_MARKET_LAG_DAYS:
                _add_finding(out, "output.market.coverage_stale",
                             f"{tour}: market.json odds coverage ends {mk['lastMatchedDate']} but "
                             f"scored matches run to {mk['oosEnd']} ({lag}d gap, max "
                             f"{HEALTH_MAX_MARKET_LAG_DAYS}) — did the odds feed drop a book?",
                             severity="warning", entity=f"market-benchmark:{tour}", evidence={
                                 "lastMatchedDate": mk["lastMatchedDate"], "oosEnd": mk["oosEnd"],
                                 "lagDays": lag, "maxDays": HEALTH_MAX_MARKET_LAG_DAYS})

    return out.findings


def output_problems(tour: str, oc: dict, now: pd.Timestamp,
                    prev: dict | None = None) -> list[str]:
    """Legacy prose compatibility wrapper around ``output_findings``."""
    return _finding_messages(output_findings(tour, oc, now, prev))


def _serialize_findings(findings: list[HealthFinding]) -> list[dict]:
    """Coalesce repeated observations sharing one stable incident identity."""
    groups: dict[str, list[HealthFinding]] = {}
    for finding in findings:
        groups.setdefault(finding.fingerprint, []).append(finding)
    serialized = []
    rank = {"info": 0, "warning": 1, "error": 2}
    for fingerprint in sorted(groups):
        group = groups[fingerprint]
        if len(group) == 1:
            serialized.append(group[0].as_dict())
            continue
        first = group[0]
        severity = max((finding.severity for finding in group), key=rank.__getitem__)
        messages = sorted({finding.message for finding in group})
        occurrences = sorted(
            (finding.evidence for finding in group),
            key=lambda evidence: json.dumps(
                evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
        combined = HealthFinding(
            code=first.code, severity=severity, scope=first.scope, tour=first.tour,
            entity=first.entity,
            evidence={"occurrences": occurrences},
            message="\n".join(messages),
        )
        serialized.append(combined.as_dict())
    return serialized


def _structured_findings(report: dict, *, actionable_only: bool = False) -> list[dict]:
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    valid = []
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("schema") != FINDING_SCHEMA:
            continue
        try:
            typed = HealthFinding(
                code=finding["code"], severity=finding["severity"], scope=finding["scope"],
                tour=finding.get("tour"), entity=finding.get("entity"),
                evidence=finding["evidence"], message=finding["message"],
            )
        except (KeyError, TypeError, ValueError):
            continue
        canonical = typed.as_dict()
        if (finding.get("fingerprint") != canonical["fingerprint"]
                or finding.get("revision") != canonical["revision"]):
            continue
        valid.append(canonical)
    return ([finding for finding in valid if finding["severity"] != "info"]
            if actionable_only else valid)


def _finding_transitions(current: list[dict], previous: list[dict]) -> dict[str, list[str]]:
    cur = {finding["fingerprint"]: finding for finding in current
           if finding.get("severity") != "info"}
    old = {finding["fingerprint"]: finding for finding in previous
           if finding.get("severity") != "info"}
    return {
        "activated": sorted(cur.keys() - old.keys()),
        "updated": sorted(key for key in cur.keys() & old.keys()
                          if cur[key].get("revision") != old[key].get("revision")),
        "resolved": sorted(old.keys() - cur.keys()),
    }


def format_issue_body(report: dict, run_url: str | None = None,
                      health_url: str | None = None) -> str:
    """Markdown for the `data-health` GitHub issue — includes a ready-to-paste fix prompt."""
    probs: list[str] = []
    for h in report.get("tours", {}).values():
        probs += h.get("problems", [])
        probs += (h.get("output") or {}).get("problems", [])
    lines = [f"The pipeline **data health check failed** on {report.get('generated', '?')}.",
             "", "### Problems"]
    shown, extra = probs[:50], max(0, len(probs) - 50)   # cap: a systemic break can flag many
    lines += [f"- {p}" for p in shown] or ["- (no detail — see run logs)"]
    if extra:
        lines.append(f"- …and {extra} more")
    if run_url:
        lines += ["", f"Failing run: {run_url}"]
    if health_url:
        lines += ["", f"Live status page: {health_url}"]
    summary = "; ".join(probs) if probs else "see run logs"
    lines += [
        "", "### Fix it in a new session",
        "Open a new Claude Code session and paste:", "",
        f"> Investigate and resolve the `data-health` issue. The pipeline health check "
        f"flagged: {summary}. Reproduce locally with `cd tennis_model && PYTHONPATH=src "
        f"python -m tennis_model.data.health`, then read `src/tennis_model/data/health.py` "
        f"(`problems()` / `output_problems()`) and the failing tour's `data/output/<tour>/*.json`.",
    ]
    return "\n".join(lines)


def format_finding_issue_body(finding: dict, report: dict, run_url: str | None = None,
                              health_url: str | None = None) -> str:
    """One durable GitHub issue body, keyed independently from mutable evidence/prose."""
    key, revision = finding["fingerprint"], finding["revision"]
    observed_at = report.get("generated") or report.get("generatedAt") or "?"
    message = str(finding["message"])
    if len(message) > 8_000:
        message = f"{message[:8_000]}\n… truncated ({len(message) - 8_000} characters omitted)"
    evidence = json.dumps(finding.get("evidence") or {}, indent=2, sort_keys=True,
                          ensure_ascii=False, allow_nan=False)
    if len(evidence) > 40_000:
        omitted = len(evidence) - 40_000
        evidence = f"{evidence[:40_000]}\n… truncated ({omitted} characters omitted)"
    lines = [
        f"<!-- data-health-key: {key} -->",
        f"<!-- data-health-revision: {revision} -->",
        "",
        f"The pipeline observed **{finding['code']}** on {observed_at}.",
        "",
        f"- Severity: `{finding['severity']}`",
        f"- Scope: `{finding['scope']}`",
        f"- Tour: `{finding.get('tour') or 'cross-tour'}`",
        f"- Entity: `{finding.get('entity') or 'global'}`",
        "",
        "### Observation",
        "",
        message,
        "",
        "### Evidence",
        "",
        "```json",
        evidence,
        "```",
    ]
    if run_url:
        lines += ["", f"Observed run: {str(run_url)[:2_048]}"]
    if health_url:
        lines += ["", f"Live status page: {str(health_url)[:2_048]}"]
    lines += [
        "", "### Fix it in a new session", "",
        f"> Investigate and resolve health finding `{finding['code']}` for "
        f"`{finding.get('entity') or 'global'}`. Reproduce with `cd tennis_model && "
        "PYTHONPATH=src python -m tennis_model.data.health`, then repair the producer and "
        "add a broken+clean incident replay before changing the invariant.",
    ]
    body = "\n".join(lines)
    if len(body) > FINDING_ISSUE_BODY_MAX_CHARS:
        # Defense in depth for future fields: never let a huge observation make the
        # incident itself unreportable. Markers and repair context are always retained.
        overflow = len(body) - FINDING_ISSUE_BODY_MAX_CHARS
        marker = f"\n… final body cap applied ({overflow} characters omitted) …\n"
        tail_chars = 12_000
        head_chars = FINDING_ISSUE_BODY_MAX_CHARS - tail_chars - len(marker)
        body = body[:head_chars] + marker + body[-tail_chars:]
    return body


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit non-zero on any problem")
    ap.add_argument("--issue-body", action="store_true",
                    help="print a GitHub-issue body from the existing health.json (empty if ok)")
    ap.add_argument("--findings-json", action="store_true",
                    help="print the validated structured finding list from health.json")
    ap.add_argument("--finding-body", action="store_true",
                    help="print one finding issue body selected by FINDING_KEY")
    ap.add_argument("--gate", action="store_true",
                    help="pre-deploy gate: exit non-zero on any produced-OUTPUT integrity "
                         "problem (not source freshness / run-over-run deltas); does not write "
                         "health.json — run BEFORE deploy so a wrong build can't ship")
    ap.add_argument("--gate-report", type=Path,
                    help="with --gate, atomically write a structured blocking/advisory report")
    args = ap.parse_args()

    health_path = Path(os.environ.get("HEALTH_REPORT") or OUTPUT_DIR / "health.json")

    if args.gate_report is not None and not args.gate:
        ap.error("--gate-report requires --gate")

    if args.findings_json or args.finding_body:
        try:
            report = json.loads(health_path.read_text())
            raw = report.get("findings")
            findings = _structured_findings(report)
            findings_ok = report.get("findingsOk", report.get("ok"))
            snapshot = report.get("findingSnapshot")
            expected_snapshot = os.environ.get("FINDING_SNAPSHOT")
            if (report.get("findingSchema") != FINDING_SCHEMA or not isinstance(raw, list)
                    or len(findings) != len(raw)
                    or len({finding["fingerprint"] for finding in findings}) != len(findings)
                    or snapshot not in {"authoritative", "partial"}
                    or (expected_snapshot is not None and snapshot != expected_snapshot)
                    or not isinstance(findings_ok, bool)
                    or findings_ok != (not any(
                        finding["severity"] != "info" for finding in findings))):
                raise ValueError("structured finding contract mismatch")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            print(f"::error::could not load structured health findings: {exc}")
            return 1
        if args.findings_json:
            print(json.dumps(findings, separators=(",", ":"), ensure_ascii=False,
                             allow_nan=False))
            return 0
        key = os.environ.get("FINDING_KEY")
        finding = next((item for item in findings if item["fingerprint"] == key), None)
        if finding is None:
            print(f"::error::health finding {key!r} is not active")
            return 1
        print(format_finding_issue_body(
            finding, report, run_url=os.environ.get("GITHUB_RUN_URL"),
            health_url=os.environ.get("HEALTH_PAGE_URL")))
        return 0

    if args.issue_body:
        if not health_path.exists():
            return 0
        report = json.loads(health_path.read_text())
        if not report.get("ok", True):
            print(format_issue_body(report, run_url=os.environ.get("GITHUB_RUN_URL"),
                                    health_url=os.environ.get("HEALTH_PAGE_URL")))
        return 0

    if args.gate:
        # Pre-deploy integrity gate. Fails ONLY on internally-inconsistent produced output —
        # impossible odds, aliveCount>drawSize, a non-standard-size "real" draw, a live event
        # already naming a champion, placeholder-name leaks, missing/corrupt required JSON, a
        # broken win matrix, upset-flag disagreements, ... Deliberately absolute (prev=None):
        # source freshness and run-over-run deltas are NOT gated here — those stay best-effort
        # and are reported by the post-deploy sentinel. Never writes health.json (leaves the
        # sentinel's prev-snapshot/issue flow untouched). A failure keeps the last good deploy
        # live rather than shipping a wrong one; a stale-but-correct site beats a fresh-wrong one.
        observed_at = pd.Timestamp(datetime.now(UTC))
        now = observed_at.normalize().tz_localize(None)
        blocking: list[dict] = []
        advisory: list[dict] = []
        gate_findings: list[HealthFinding] = []
        outs = {tour: read_outputs(tour) for tour in TOURS}
        _, lineage_findings = _lineage_observation(require_accepted=False)
        for tour in TOURS:
            tour_findings = output_findings(
                tour, outs[tour], now, prev=None, observed_at=observed_at
            ) + lineage_findings[tour]
            for finding in tour_findings:
                gate_findings.append(finding)
                item = {"scope": tour, "problem": finding.message,
                        "finding": finding.as_dict()}
                if _gate_blocks(finding):
                    blocking.append(item)
                    print(f"  GATE/{tour}: BLOCK {finding.message}")
                else:
                    advisory.append(item)
                    print(f"  GATE/{tour}: warn  {finding.message}  "
                          "(advisory — post-deploy sentinel handles it)")
        for finding in cross_tour_findings(outs):
            gate_findings.append(finding)
            item = {"scope": "cross", "problem": finding.message,
                    "finding": finding.as_dict()}
            if _gate_blocks(finding):
                blocking.append(item)
                print(f"  GATE/cross: BLOCK {finding.message}")
            else:
                advisory.append(item)
                print(f"  GATE/cross: warn  {finding.message}  "
                      "(advisory — post-deploy sentinel handles it)")
        if args.gate_report is not None:
            try:
                sentinel_paths = {
                    health_path.resolve(),
                    (WEB_DATA_DIR / "health.json").resolve(),
                }
                if args.gate_report.resolve() in sentinel_paths:
                    raise ValueError("gate report path must not alias either health.json sentinel")
                _write_json_atomic(args.gate_report, {
                    "schema": "predeploy-gate-v1",
                    "generatedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "ok": not blocking,
                    "findingSchema": FINDING_SCHEMA,
                    # The gate intentionally omits source freshness and prev-based checks.
                    # Reporters may update findings present here, but absence is not recovery.
                    "findingSnapshot": "partial",
                    "findingsOk": not any(
                        finding.severity != "info" for finding in gate_findings),
                    "findings": _serialize_findings(gate_findings),
                    "blocking": blocking,
                    "advisory": advisory,
                })
            except (OSError, ValueError) as exc:
                print(f"::error::could not write structured gate report: {exc}")
                return 1
        if blocking:
            print(f"::error::pre-deploy integrity gate failed — {len(blocking)} blocking problem(s); "
                  f"deploy blocked, last good deploy stays live")
            return 1
        print("pre-deploy integrity gate passed (no deploy-blocking integrity problem)")
        return 0

    prev = None
    if health_path.exists():
        try:
            prev = json.loads(health_path.read_text())
        except ValueError:
            prev = None

    observed_at = pd.Timestamp(datetime.now(UTC))
    now = observed_at.normalize().tz_localize(None)
    # `generated` stays day-granular (problem strings key off it for dedup); generatedAt
    # is the precise stamp the /health page shows and ages client-side.
    report, all_problems = {"generated": str(now.date()),
                            "generatedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "findingSchema": FINDING_SCHEMA,
                            "findingSnapshot": "authoritative",
                            "eventCoverage": {}, "tours": {}}, []
    all_findings: list[HealthFinding] = []
    outs = {tour: read_outputs(tour) for tour in TOURS}
    lineage_summary, lineage_findings = _lineage_observation(require_accepted=True)
    report["artifactLineage"] = lineage_summary
    # Cross-tour problems belong to no single tour; attach them to the first only for the
    # legacy nested prose flow. Their canonical structured copy remains scope=cross.
    cross_findings = cross_tour_findings(outs)
    for tour in TOURS:
        h = tour_health(tour, now)
        checks = source_checks(tour, h, now)
        source_typed = source_findings(tour, h, now)
        p = _finding_messages(source_typed)
        prev_out = ((prev or {}).get("tours", {}).get(tour, {}) or {}).get("output") or {}
        oc = outs[tour]
        output_typed = output_findings(
            tour, oc, now, prev_out, observed_at=observed_at
        ) + lineage_findings[tour]
        nested_cross = cross_findings if tour == TOURS[0] else []
        op = _finding_messages(output_typed + nested_cross)
        meta = oc["data"].get("meta") or {}
        high_water, high_water_version = _population_high_water(tour, meta, prev_out)
        h["checks"] = checks
        h["problems"] = p
        h["findings"] = _serialize_findings(source_typed)
        h["output"] = {
            "matches": meta.get("matches"),
            "match_population_version": meta.get("matchPopulationVersion"),
            "high_water_matches": high_water,
            "high_water_match_population_version": high_water_version,
            "model_population_version": meta.get("modelPopulationVersion"),
            "wta125_matches": meta.get("wta125Matches"),
            "excluded_wta125_matches": meta.get("excludedWta125Matches"),
            "excluded_unclassified_wta_live_matches":
                meta.get("excludedUnclassifiedWtaLiveMatches"),
            "model_trained_at": meta.get("modelTrainedAt"),
            "forecast_lines": (oc["forecast"] or {}).get("lines"),
            "forecast_high_water_lines": _forecast_high_water(
                (oc["forecast"] or {}).get("lines"), prev_out),
            "forecast_max_as_of": (oc["forecast"] or {}).get("max_as_of"),
            # Feeds the lost-bracket sentinel on the NEXT run (see output_problems).
            "bracket_events": sorted(
                _norm_name(t["name"])
                for t in (oc["data"].get("tournaments") or [])
                if isinstance(t, dict) and t.get("name") and t.get("hasBracket")),
            "bracket_event_entities": _remembered_bracket_event_entities(
                oc["data"].get("tournaments"), prev_out),
            "problems": op,
            "findings": _serialize_findings(output_typed + nested_cross),
        }
        report["eventCoverage"][tour] = _coverage_summary(
            oc["data"].get("event_coverage"), oc["data"].get("tournaments"))
        report["tours"][tour] = h
        all_problems += p + op
        all_findings += source_typed + output_typed + nested_cross
        print(f"  health/{tour}: results to {h['date_max']}, stats to {h['stats_date_max']}, "
              f"season stats {h['cur_year_stats_fraction']}; {len(op)} output problem(s)")
    report["findings"] = _serialize_findings(all_findings)
    active = [finding for finding in report["findings"] if finding["severity"] != "info"]
    previous_findings = _structured_findings(prev or {})
    report["findingTransitions"] = _finding_transitions(
        report["findings"], previous_findings)
    report["ok"] = not active
    # Mutable evidence has its own revision/update transition, but cannot become a new
    # incident merely because an age/count or wording changed.
    current_state = sorted((finding["fingerprint"], finding["severity"])
                           for finding in active)
    previous_state = sorted((finding["fingerprint"], finding["severity"])
                            for finding in previous_findings
                            if finding["severity"] != "info")
    report["findings_changed"] = current_state != previous_state
    report["problems_changed"] = report["findings_changed"]  # compatibility alias

    _write_json_atomic(health_path, report)
    # Mirror for the (hidden) /health page — the CI check step runs before the site
    # build, so the deploy ships this run's report. Best-effort: a checkout without
    # web/ (or a read-only mount) must never break the sentinel itself.
    try:
        WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy(health_path, WEB_DATA_DIR / "health.json")
    except OSError as e:
        print(f"  (health.json web mirror skipped: {e})")
    for pr in all_problems:
        print(f"  HEALTH: {pr}")
    if args.strict and active:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
