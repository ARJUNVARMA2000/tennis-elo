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
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ..config import (
    DATA_DIR,
    HEALTH_CHARTING_COVERAGE_NOTE_DAYS,
    HEALTH_MAX_BUILD_AGE_DAYS,
    HEALTH_MAX_FORECAST_AGE_DAYS,
    HEALTH_MAX_FRESH_AGE_DAYS,
    HEALTH_MAX_FUTURE_DATE_DAYS,
    HEALTH_MAX_LIVERANK_NULL_FRAC,
    HEALTH_MAX_MARKET_LAG_DAYS,
    HEALTH_MAX_MODEL_AGE_DAYS,
    HEALTH_MAX_RESULT_AGE_DAYS,
    HEALTH_MAX_STATS_AGE_DAYS,
    HEALTH_MIN_MATCHES,
    HEALTH_MIN_STATS_FRACTION,
    HEALTH_OFFSEASON_RELAX_DAYS,
    MATCH_POPULATION_VERSION,
    MAX_FUTURE_MATCH_DAYS,
    OUTPUT_DIR,
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
    STAGE_STATUS_FILENAME,
    STAGE_STATUS_SCHEMA,
    validate_stage_status,
)
from .charting import _GENDER, CHARTING_DIR
from .health_checks.benchmarks import (
    _check_kalshi_ledger as _check_kalshi_ledger,
)
from .health_checks.benchmarks import (
    _check_tennis_abstract_benchmark as _check_tennis_abstract_benchmark,
)
from .health_checks.common import (
    _BELOW_TIER as _BELOW_TIER,
)
from .health_checks.common import (
    _BYE_DRAW_SIZES as _BYE_DRAW_SIZES,
)
from .health_checks.common import (
    _CANONICAL_SURFACES as _CANONICAL_SURFACES,
)
from .health_checks.common import (
    _DRAW_STATES as _DRAW_STATES,
)
from .health_checks.common import (
    _EVIDENCE_KEYS as _EVIDENCE_KEYS,
)
from .health_checks.common import (
    _FINDING_CODE_RE as _FINDING_CODE_RE,
)
from .health_checks.common import (
    _FINDING_SCOPES as _FINDING_SCOPES,
)
from .health_checks.common import (
    _FINDING_SEVERITIES as _FINDING_SEVERITIES,
)
from .health_checks.common import (
    _REACH_ORDER as _REACH_ORDER,
)
from .health_checks.common import (
    _STATUSES as _STATUSES,
)
from .health_checks.common import (
    _UUID4_RE as _UUID4_RE,
)
from .health_checks.common import (
    _WATCH_WEIGHTS as _WATCH_WEIGHTS,
)
from .health_checks.common import (
    FINDING_SCHEMA as FINDING_SCHEMA,
)
from .health_checks.common import (
    GATE_BLOCKING_TIERS as GATE_BLOCKING_TIERS,
)
from .health_checks.common import (
    HealthFinding as HealthFinding,
)
from .health_checks.common import (
    _add_finding as _add_finding,
)
from .health_checks.common import (
    _age_days as _age_days,
)
from .health_checks.common import (
    _event_entity as _event_entity,
)
from .health_checks.common import (
    _event_evidence_matches as _event_evidence_matches,
)
from .health_checks.common import (
    _event_provider_entity as _event_provider_entity,
)
from .health_checks.common import (
    _event_real_player_keys as _event_real_player_keys,
)
from .health_checks.common import (
    _event_stable_entity as _event_stable_entity,
)
from .health_checks.common import (
    _finding_messages as _finding_messages,
)
from .health_checks.common import (
    _FindingCollector as _FindingCollector,
)
from .health_checks.common import (
    _finite_between as _finite_between,
)
from .health_checks.common import (
    _flag_placeholders as _flag_placeholders,
)
from .health_checks.common import (
    _identity_value as _identity_value,
)
from .health_checks.common import (
    _is_prob as _is_prob,
)
from .health_checks.common import (
    _is_real_name as _is_real_name,
)
from .health_checks.common import (
    _match_entity as _match_entity,
)
from .health_checks.common import (
    _norm_name as _norm_name,
)
from .health_checks.common import (
    _plain_int as _plain_int,
)
from .health_checks.common import (
    _player_identity_key as _player_identity_key,
)
from .health_checks.common import (
    _pow2 as _pow2,
)
from .health_checks.common import (
    _real_draw_size_ok as _real_draw_size_ok,
)
from .health_checks.common import (
    _remembered_bracket_event_entities as _remembered_bracket_event_entities,
)
from .health_checks.common import (
    _square_matrix as _square_matrix,
)
from .health_checks.common import (
    _tier_blocks as _tier_blocks,
)
from .health_checks.common import (
    _tier_severity as _tier_severity,
)
from .health_checks.common import (
    _tiered as _tiered,
)
from .health_checks.draws import (
    _DRAW_SOURCE_HOSTS as _DRAW_SOURCE_HOSTS,
)
from .health_checks.draws import (
    _check_bracket_upcoming_probability_parity as _check_bracket_upcoming_probability_parity,
)
from .health_checks.draws import (
    _check_brackets as _check_brackets,
)
from .health_checks.draws import (
    _check_projection as _check_projection,
)
from .health_checks.draws import (
    _check_tournament as _check_tournament,
)
from .health_checks.predictions import (
    _check_forecast_history as _check_forecast_history,
)
from .health_checks.predictions import (
    _check_matrix as _check_matrix,
)
from .health_checks.predictions import (
    _check_matrix_evidence as _check_matrix_evidence,
)
from .health_checks.predictions import (
    _check_matrix_shards as _check_matrix_shards,
)
from .health_checks.predictions import (
    _check_performance as _check_performance,
)
from .health_checks.predictions import (
    _check_prediction_evidence as _check_prediction_evidence,
)
from .health_checks.predictions import (
    _check_profile_shards as _check_profile_shards,
)
from .health_checks.predictions import (
    _check_scenarios as _check_scenarios,
)
from .health_checks.predictions import (
    _check_upcoming_shards as _check_upcoming_shards,
)
from .health_checks.predictions import (
    _check_watch_ranking as _check_watch_ranking,
)
from .health_checks.products import (
    _check_event_coverage as _check_event_coverage,
)
from .health_checks.products import (
    _check_method as _check_method,
)
from .health_checks.products import (
    _check_pipeline_stage_status as _check_pipeline_stage_status,
)
from .health_checks.products import (
    _public_stage_error_type as _public_stage_error_type,
)
from .health_checks.products import (
    _stage_success_overdue as _stage_success_overdue,
)
from .health_checks.release import lineage_observation
from .participants import is_real_participant
from .results import load_matches

FINDING_ISSUE_BODY_MAX_CHARS = 60_000










def _lineage_observation(*, require_accepted: bool) -> tuple[dict, dict[str, list[HealthFinding]]]:
    return lineage_observation(OUTPUT_DIR, TOURS, require_accepted=require_accepted)


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
_OPTIONAL_OUTPUTS = ("accuracy", "track", "market", "tennis-abstract")





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
        if isinstance(br, list):
            _check_bracket_upcoming_probability_parity(out, tour, br, up)

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

    tennis_abstract = data.get("tennis-abstract")
    if isinstance(tennis_abstract, dict):
        _check_tennis_abstract_benchmark(out, tour, tennis_abstract)

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
