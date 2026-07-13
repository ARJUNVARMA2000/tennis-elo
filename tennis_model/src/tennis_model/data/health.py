"""Data-health sentinel: fail loudly when the pipeline quietly stops making sense.

Two layers, both surfaced in data/output/health.json and both reddening the daily
build under --strict:
  * source freshness (tour_health/problems) — a scraper silently froze and the newest
    match/serve-stats row stopped advancing. The TML GitHub freeze of Jan 2026 went
    unnoticed for months precisely because every downloader failure was silent.
  * produced output (read_outputs/output_problems) — the JSON the web actually reads
    (counts, tournaments, matches, predictions) is missing, stale, or internally
    inconsistent even though the sources looked fine.

The workflow runs this without --strict on EVERY run — daily full and hourly quick —
(always writes health.json, exit 0) and a follow-up step reads health.json to open/close
a `data-health` GitHub issue and red the run. Quick runs red only when they OPEN the
issue; while it stands they stay green, commenting only when the problem set changed
(problems_changed), so a standing failure alerts once, not hourly. --issue-body prints
that issue's Markdown; --strict is kept for local use.

--gate is the PRE-deploy guard the workflow runs before publishing: it fails (exit 1) only
on produced-output integrity problems (not source freshness), so an internally-inconsistent
build (e.g. impossible reach odds, a live event naming a champion) can never reach the site;
a failure keeps the last good deploy live. It never writes health.json.

Run:  PYTHONPATH=src python -m tennis_model.data.health [--strict | --issue-body | --gate]
"""

from __future__ import annotations

import csv
import glob
import itertools
import json
import os
import shutil
from collections import Counter
from datetime import UTC, datetime

import pandas as pd

from ..config import (
    DATA_DIR,
    HEALTH_MAX_BUILD_AGE_DAYS,
    HEALTH_MAX_CHARTING_AGE_DAYS,
    HEALTH_MAX_FORECAST_AGE_DAYS,
    HEALTH_MAX_FRESH_AGE_DAYS,
    HEALTH_MAX_LIVERANK_NULL_FRAC,
    HEALTH_MAX_MARKET_LAG_DAYS,
    HEALTH_MAX_RESULT_AGE_DAYS,
    HEALTH_MAX_STATS_AGE_DAYS,
    HEALTH_MIN_MATCHES,
    HEALTH_MIN_STATS_FRACTION,
    HEALTH_OFFSEASON_RELAX_DAYS,
    OUTPUT_DIR,
    TOURS,
    WEB_DATA_DIR,
    fresh_dir,
    output_dir,
)
from ..model.features import FEATURES
from .charting import _GENDER, CHARTING_DIR
from .results import load_matches


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


def fresh_date_max(tour: str):
    """Newest tourney_date in the fresh overlay's newest year file. Checked directly
    because the merged result_age_days can't see this source freeze — the ESPN live
    overlay keeps the merged maximum current. IO seam (patched in tests)."""
    files = sorted(glob.glob(str(fresh_dir(tour) / "*.csv")))   # per-year names sort lexically
    if not files:
        return None
    from .results import _parse_dates  # handles the overlay's YYYY/M/D format
    try:
        s = pd.read_csv(files[-1], usecols=["tourney_date"], encoding="utf-8-sig")["tourney_date"]
    except (ValueError, OSError):
        return None
    m = _parse_dates(s).max()
    return m if pd.notna(m) else None


def tour_health(tour: str, now: pd.Timestamp) -> dict:
    df = load_matches(tour)
    completed = df[df["completed"]]
    stats_rows = df[df["has_stats"]]
    cur = df[df["date"].dt.year == now.year]
    # empty slices give NaT maxima — report None (flagged by problems()) rather than crash
    date_max = df["date"].max() if len(df) else pd.NaT
    res_max = completed["date"].max() if len(completed) else pd.NaT
    stat_max = stats_rows["date"].max() if len(stats_rows) else pd.NaT
    fr_max, ch_max = fresh_date_max(tour), charting_date_max(tour)
    return {
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
    }


def source_checks(tour: str, h: dict, now: pd.Timestamp) -> list[dict]:
    """Structured verdicts for the raw-source freshness checks — the single source of
    truth: problems() derives its alert strings from these rows, and the (hidden)
    /health page renders them, so the two can never drift. Each row:
      {key, label, value, limit, unit, date, ok, note, problem}
    `problem` is the alert string (None when ok); `note` carries context for a row that
    is over its limit but deliberately not alarmed (a shadowed redundancy layer)."""
    offseason = _offseason(now)
    max_result = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_RESULT_AGE_DAYS
    max_stats = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_STATS_AGE_DAYS
    min_frac = HEALTH_MIN_STATS_FRACTION.get(tour, 0.0)

    def row(key, label, value, limit, unit="d", date=None, note=None, problem=None):
        return {"key": key, "label": label, "value": value, "limit": limit, "unit": unit,
                "date": date, "ok": problem is None, "note": note, "problem": problem}

    rows = []
    res_age = h["result_age_days"]
    rows.append(row(
        "results", "Match results (merged)", res_age, max_result,
        problem=(f"{tour}: no completed matches loaded" if res_age is None
                 else f"{tour}: newest completed match is {res_age}d old (max {max_result})"
                 if res_age > max_result else None)))
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
        note=("frozen upstream, but shadowed — the serve-stats overlay is current, so "
              "results/ranks/stats all still flow" if shadowed else None),
        problem=(f"{tour}: fresh overlay has no loadable results" if fresh_age is None
                 else f"{tour}: newest fresh-overlay result is {fresh_age}d old "
                 f"(max {max_fresh}) — the results overlay source may have frozen"
                 if fresh_age > max_fresh and not stats_current else None)))
    ch_age = h["charting_age_days"]
    rows.append(row(
        "charting", "Match charting (MCP)", ch_age, HEALTH_MAX_CHARTING_AGE_DAYS,
        date=h.get("charting_date_max"),
        problem=(f"{tour}: charting files missing/unreadable (style features degraded)"
                 if ch_age is None
                 else f"{tour}: newest charted match is {ch_age}d old "
                 f"(max {HEALTH_MAX_CHARTING_AGE_DAYS}) — the MCP source may have moved/frozen"
                 if ch_age > HEALTH_MAX_CHARTING_AGE_DAYS else None)))
    return rows


def problems(tour: str, h: dict, now: pd.Timestamp) -> list[str]:
    return [r["problem"] for r in source_checks(tour, h, now) if r["problem"]]


# ---------------------------------------------------------------------------
# Produced-output validation (does the JSON the web reads make sense?)
# ---------------------------------------------------------------------------
# The web reads these per tour; the first group must always exist and parse, the second
# is best-effort (accuracy is backtest-only, track needs graded forecasts).
_REQUIRED_OUTPUTS = ("meta", "players", "tournaments", "brackets", "upcoming", "matrix",
                     "ratings_history", "profiles", "draws", "fixtures", "method")
_OPTIONAL_OUTPUTS = ("accuracy", "track", "market")
_PLACEHOLDER_NAMES = {"tbd", "tba", "bye", "qualifier"}   # mirror data/live.py
_STATUSES = {"live", "upcoming", "completed"}
_DRAW_STATES = {"real", "partial", "seeded", "final"}
_REACH_ORDER = ("R128", "R64", "R32", "R16", "QF", "SF", "F", "Champion")

# The pre-deploy --gate blocks a deploy only on problems that make the shipped site WRONG
# (impossible numbers, structural breaks, missing/corrupt required JSON). A thin or quirky
# schedule/rankings feed is worth flagging but not worth freezing the site over, so these
# markers stay ADVISORY — reported by the gate but left to the non-blocking post-deploy
# sentinel. New checks default to blocking (the safe direction).
_GATE_ADVISORY = (
    "same event more than once",   # YoY sponsor-rename / dedup split (schedule cosmetic)
    "one event under two names",
    "no live/upcoming event",      # a genuine quiet week can leave the board thin
    "is empty",                    # tournaments.json / upcoming.json empty
    "liveRank",                    # rankings source drifted (site still correct on model odds)
    "outputs last built",          # build-age; can't legitimately fire right after a build
    "market.json odds coverage",   # benchmark-card staleness; odds are never a build dependency
    "forecast drift",              # model-decay advisory; a re-tune recommendation must never block a deploy
    "forecast log last advanced",  # eval-artifact liveness; never a build dependency
)


def _gate_blocks(problem: str) -> bool:
    """True if this output problem should BLOCK the deploy (vs. warn-but-ship)."""
    return not any(marker in problem for marker in _GATE_ADVISORY)


def _reject_nonfinite(token: str):
    """parse_constant hook: json.loads accepts NaN/Infinity by default, but the browser's
    JSON.parse rejects them — a NaN that slips into a shipped file blanks the page, not
    errors. Treat such a file as unparseable here so the gate catches what the browser will."""
    raise ValueError(f"non-finite JSON constant {token!r}")


def read_outputs(tour: str) -> dict:
    """Load a tour's produced JSON + forecast log. IO seam (monkeypatched in tests).

    Returns {"data": {stem: parsed}, "missing": [required stems absent],
             "corrupt": [stems present but unparseable OR carrying NaN/Infinity],
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
            "forecast": forecast, "kalshi_ledger": ledger}


def _is_prob(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0.0 <= float(x) <= 1.0


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


def _real_draw_size_ok(n) -> bool:
    return _pow2(n) or n in _BYE_DRAW_SIZES


def _age_days(iso, now: pd.Timestamp):
    ts = pd.to_datetime(iso, utc=True, errors="coerce") if iso else pd.NaT
    if pd.isna(ts):
        return None
    now_utc = now if now.tzinfo else now.tz_localize("UTC")
    return int((now_utc - ts).days)


def _flag_placeholders(out: list, tour: str, where: str, names) -> None:
    bad = sorted({n for n in names if isinstance(n, str) and n.strip().lower() in _PLACEHOLDER_NAMES})
    if bad:
        out.append(f"{tour}: {where} contains placeholder name(s) {bad}")


def _check_matrix(out: list, tour: str, mx: dict) -> None:
    players = mx.get("players") or []
    n = len(players)
    for surf, byfmt in (mx.get("surfaces") or {}).items():
        if not isinstance(byfmt, dict):
            continue
        for fmt, m in byfmt.items():
            if not isinstance(m, list) or len(m) != n or any(len(r) != n for r in m):
                out.append(f"{tour}: matrix[{surf}][{fmt}] is not {n}x{n}")
                continue
            # sample corners + the top-left 2x2 — enough to catch a systemic break
            # (all-out-of-range, transposed, un-normalised) without scanning ~14k cells
            for i, j in {(0, 0), (0, min(1, n - 1)), (n - 1, 0), (n - 1, n - 1)}:
                if not _is_prob(m[i][j]):
                    out.append(f"{tour}: matrix[{surf}][{fmt}][{i}][{j}]={m[i][j]!r} out of [0,1]")
            if n >= 2:
                if abs(m[0][0] - 0.5) > 1e-6:
                    out.append(f"{tour}: matrix[{surf}][{fmt}] diagonal != 0.5 ({m[0][0]})")
                if abs(m[0][1] + m[1][0] - 1.0) > 1e-3:
                    out.append(f"{tour}: matrix[{surf}][{fmt}] not antisymmetric "
                               f"({m[0][1]}+{m[1][0]})")


def _check_projection(out: list, tour: str, name, proj: list) -> None:
    for p in proj:
        who = p.get("name")
        c, f, s = p.get("champion"), p.get("final"), p.get("sf")
        for k, v in (("champion", c), ("final", f), ("sf", s)):
            # None is deliberate: the live projector (sim/tournaments.py) sets a round field
            # to None once that round is already DETERMINED ("SF" not in cols -> sf=None for a
            # finalist who is past the semis). That degrades gracefully in the UI; only a
            # PRESENT-but-out-of-range value is a real problem.
            if v is not None and not _is_prob(v):
                out.append(f"{tour}: {name!r} {who!r} {k}={v!r} out of [0,1]")
        if _is_prob(c) and _is_prob(f) and _is_prob(s) and (c > f + 1e-6 or f > s + 1e-6):
            out.append(f"{tour}: {name!r} {who!r} champion<=final<=sf violated ({c},{f},{s})")
        seq = [p["reach"][k] for k in _REACH_ORDER if isinstance(p.get("reach"), dict) and k in p["reach"]]
        if any(not _is_prob(v) for v in seq):
            out.append(f"{tour}: {name!r} {who!r} reach probability out of [0,1]")
        elif any(seq[i] < seq[i + 1] - 1e-6 for i in range(len(seq) - 1)):
            out.append(f"{tour}: {name!r} {who!r} reach odds not monotonically non-increasing")


def _check_tournament(out: list, tour: str, t: dict) -> None:
    name, status = t.get("name"), t.get("status")
    ds, size, alive, champ = t.get("drawStatus"), t.get("drawSize"), t.get("aliveCount"), t.get("champion")
    if status not in _STATUSES:
        out.append(f"{tour}: tournament {name!r} has bad status {status!r}")
    if ds is None:
        out.append(f"{tour}: tournament {name!r} missing drawStatus")
    elif ds not in _DRAW_STATES:
        out.append(f"{tour}: tournament {name!r} has bad drawStatus {ds!r}")
    if isinstance(size, int) and isinstance(alive, int) and alive > size:
        out.append(f"{tour}: tournament {name!r} aliveCount {alive} > drawSize {size}")
    if isinstance(size, int) and size > 128:
        out.append(f"{tour}: tournament {name!r} drawSize {size} exceeds the maximum 128-player draw")
    # a real bracket seats a STANDARD draw size — a power of two, or a sanctioned
    # bye-draw (28/48/56/96...; Gstaad's 28-draw blocked a deploy on 2026-07-10 when this
    # demanded strict powers of two). A leaked 'TBD' (128 -> 129, 28 -> 29) or a name-
    # resolution loss (28 -> 27) still lands outside the set and blocks. completed/
    # partial/seeded/completed sizes can be non-standard because drawSize counts entrants,
    # but no tour-level singles draw can exceed 128.
    if ds == "real" and isinstance(size, int) and not _real_draw_size_ok(size):
        out.append(f"{tour}: tournament {name!r} real draw size {size} is not a standard "
                   f"bracket size (power of two or bye-draw {sorted(_BYE_DRAW_SIZES)})")
    if status == "completed" and not champ:
        out.append(f"{tour}: completed tournament {name!r} has no champion")
    if status in ("live", "upcoming") and champ:
        out.append(f"{tour}: {status} tournament {name!r} already names champion {champ!r}")
    proj = t.get("projection") or []
    _check_projection(out, tour, name, proj)
    _flag_placeholders(out, tour, f"tournament {name!r}", (p.get("name") for p in proj))


def _check_brackets(out: list, tour: str, brackets: list, tournaments) -> None:
    """The /bracket payload must be a structurally-sound single-elim draw consistent with
    tournaments.json. A displayed bracket is reconstructed by folding an ordered draw
    forward and joining results (sim/bracket.py); the failure classes are a fold that
    doesn't halve, a winner not fed to the next round, a live event whose final is already
    decided, a prob out of range, or a champion that disagrees with tournaments.json."""
    from ..data.results import _name_key
    from ..sim.draws import SIZE_NAME
    tmap = ({_norm_name(t.get("name")): t for t in tournaments
             if isinstance(t, dict) and t.get("name")} if isinstance(tournaments, list) else {})
    seen: set = set()
    for ev in brackets:
        if not isinstance(ev, dict):
            out.append(f"{tour}: brackets.json has a non-object entry")
            continue
        name = ev.get("name")
        seen.add(_norm_name(name))
        rounds = ev.get("rounds")
        size = ev.get("bracketSize")
        status = ev.get("status")
        if not isinstance(rounds, list) or not rounds:
            out.append(f"{tour}: bracket {name!r} has no rounds")
            continue
        if status not in _STATUSES:
            out.append(f"{tour}: bracket {name!r} has bad status {status!r}")

        # structure: power-of-two size, rounds halve to a single final, labels match width
        if not _pow2(size):
            out.append(f"{tour}: bracket {name!r} bracketSize {size!r} is not a power of two")
        r0 = rounds[0].get("matches") or []
        if isinstance(size, int) and 2 * len(r0) != size:
            out.append(f"{tour}: bracket {name!r} round 0 has {len(r0)} matches (expected {size // 2})")
        for k in range(len(rounds) - 1):
            a, b = len(rounds[k].get("matches") or []), len(rounds[k + 1].get("matches") or [])
            if b * 2 != a:
                out.append(f"{tour}: bracket {name!r} round {k} has {a} matches, next has {b} (must halve)")
        if len(rounds[-1].get("matches") or []) != 1:
            out.append(f"{tour}: bracket {name!r} final round is not a single match")
        for rnd in rounds:
            ms = rnd.get("matches") or []
            want = SIZE_NAME.get(2 * len(ms))
            if want and rnd.get("round") != want:
                out.append(f"{tour}: bracket {name!r} round {rnd.get('round')!r} mislabelled "
                           f"(expected {want!r} for {len(ms)} matches)")

        # drawSize: non-null round-0 participants == this drawSize == tournaments.json drawSize
        real0 = [p for m in r0 for p in (m.get("a"), m.get("b")) if isinstance(p, str) and p.strip()]
        real0 = [p for p in real0 if not p.strip().lower().startswith(("qualifier", "lucky loser"))]
        ds = ev.get("drawSize")
        if isinstance(ds, int) and len(real0) != ds:
            out.append(f"{tour}: bracket {name!r} has {len(real0)} round-0 players but drawSize {ds}")
        t = tmap.get(_norm_name(name))
        if t and isinstance(t.get("drawSize"), int) and ds != t.get("drawSize"):
            out.append(f"{tour}: bracket {name!r} drawSize {ds} != tournaments.json {t.get('drawSize')}")

        # final decidedness mirrors the tournament rule (no live event names a champion)
        final_m = (rounds[-1].get("matches") or [{}])[0]
        fw = final_m.get("winner")
        if status == "completed" and fw is None:
            out.append(f"{tour}: completed bracket {name!r} final match is undecided")
        if status in ("live", "upcoming") and fw is not None:
            out.append(f"{tour}: {status} bracket {name!r} final match already decided")

        # per-match: winner validity, prob range, prob/source presence, upset orientation,
        # and feeder consistency (a decided winner must seat in the right next-round slot)
        for k, rnd in enumerate(rounds):
            ms = rnd.get("matches") or []
            for j, m in enumerate(ms):
                w = m.get("winner")
                if w not in ("a", "b", None):
                    out.append(f"{tour}: bracket {name!r} winner {w!r} not in a/b/null")
                elif w in ("a", "b") and not m.get(w):
                    out.append(f"{tour}: bracket {name!r} decided match has null winning side {w!r}")
                p, src = m.get("p"), m.get("probSource")
                if p is not None and not _is_prob(p):
                    out.append(f"{tour}: bracket {name!r} match p={p!r} out of [0,1]")
                if src not in ("logged", "model", None):
                    out.append(f"{tour}: bracket {name!r} probSource {src!r} invalid")
                if (p is None) != (src is None):
                    out.append(f"{tour}: bracket {name!r} p/probSource presence mismatch (p={p!r}, src={src!r})")
                up = m.get("upset")
                if up is not None and p is not None and w in ("a", "b"):
                    won_p = p if w == "a" else 1.0 - p
                    if bool(up) != (won_p < 0.5):
                        out.append(f"{tour}: bracket {name!r} upset flag disagrees with p ({p})")
                if w in ("a", "b") and k + 1 < len(rounds):
                    won = m.get(w)
                    nxt_ms = rounds[k + 1].get("matches") or []
                    nxt = nxt_ms[j // 2] if j // 2 < len(nxt_ms) else None
                    side = (nxt.get("a") if j % 2 == 0 else nxt.get("b")) if nxt else None
                    if side is not None and won is not None and _norm_name(side) != _norm_name(won):
                        out.append(f"{tour}: bracket {name!r} round {k} winner {won!r} not fed to next round (found {side!r})")

        # champion agrees with this payload AND tournaments.json. Compare on the
        # accent/punct-insensitive name key, not casefold: the bracket slot carries the
        # elo-canonical spelling while `champion` comes from the results winner_name, so a
        # champion with a diacritic (Nosková vs Noskova) is the SAME player, not a mismatch.
        if status == "completed" and fw in ("a", "b"):
            champ = final_m.get(fw)
            if ev.get("champion") and champ and _name_key(champ) != _name_key(ev.get("champion")):
                out.append(f"{tour}: bracket {name!r} final winner {champ!r} != champion {ev.get('champion')!r}")
            if t and t.get("champion") and champ and _name_key(champ) != _name_key(t.get("champion")):
                out.append(f"{tour}: bracket {name!r} champion {champ!r} != tournaments.json {t.get('champion')!r}")

        _flag_placeholders(out, tour, f"bracket {name!r}",
                           (p for rnd in rounds for m in (rnd.get("matches") or [])
                            for p in (m.get("a"), m.get("b"))))

    # cross-presence: hasBracket <=> a brackets.json entry (both directions)
    if isinstance(tournaments, list):
        for t in tournaments:
            if isinstance(t, dict) and t.get("hasBracket") and _norm_name(t.get("name")) not in seen:
                out.append(f"{tour}: tournaments.json {t.get('name')!r} hasBracket but no brackets.json entry")
    if tmap:
        for nm in seen:
            if nm not in tmap:
                out.append(f"{tour}: brackets.json entry {nm!r} has no tournaments.json event")


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
            out.append(f"{tour}: kalshi ledger scored row {tick} lacks a parseable "
                       f"price_ts/result_date ({r.get('price_ts')!r}, {rd!r})")
        else:
            anchor += pd.Timedelta(hours=PREMATCH_UTC_HOUR)
            if ts > anchor:
                out.append(f"{tour}: kalshi ledger scored row {tick} quoted after its "
                           f"08:00 anchor ({r.get('price_ts')} > {rd} 08:00Z) — "
                           f"occurrence-anchored/in-play print")
            elif ts <= anchor - pd.Timedelta(seconds=CANDLE_LOOKBACK_S):
                mids = []
                for c in ("mid_a", "mid_b"):
                    try:
                        mids.append(float(r.get(c) or ""))
                    except ValueError:
                        pass
                if any(not (1 - EXTREME_CARRY_MID < m < EXTREME_CARRY_MID) for m in mids):
                    out.append(f"{tour}: kalshi ledger scored row {tick} carries a "
                               f"settled-extreme window-edge quote (mids {mids}) — "
                               f"post-result carry print")
        ka_res, a_won = r.get("kalshi_result_a"), r.get("a_won")
        if (ka_res in ("yes", "no") and a_won in ("0", "1")
                and (ka_res == "yes") != (a_won == "1")):
            out.append(f"{tour}: kalshi ledger scored row {tick} settlement "
                       f"contradicts its joined result — mis-joined match")
        key = (frozenset((r.get("player_a", ""), r.get("player_b", ""))), rd)
        if key in seen:
            out.append(f"{tour}: kalshi ledger scores one result twice "
                       f"({seen[key]} and {tick}, {rd})")
        else:
            seen[key] = tick


def _norm_name(name: str) -> str:
    return " ".join(str(name).split()).casefold()


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
      B) two DIFFERENTLY-named events that overlap in dates AND share players — impossible
         for distinct events (a player plays one event per week), so it's one event under
         two names. Concurrent-but-distinct events (e.g. Eastbourne+Mallorca) share no
         players, so they don't trip it."""
    named = [t for t in ts if isinstance(t, dict) and t.get("name")]
    dup = {k for k, n in Counter(_norm_name(t["name"]) for t in named).items() if n > 1}
    for key in sorted(dup):
        names = sorted({t["name"] for t in named if _norm_name(t["name"]) == key})
        out.append(f"{tour}: tournaments.json lists the same event more than once "
                   f"({', '.join(names)}) — a naming/dedup split")
    for a, b in itertools.combinations(named, 2):
        if _norm_name(a["name"]) == _norm_name(b["name"]) or _overlap_days(a, b) < 2:
            continue
        shared = {p.get("name") for p in a.get("projection", [])} & \
                 {p.get("name") for p in b.get("projection", [])}
        if len(shared) >= 3:
            out.append(f"{tour}: {a['name']!r} and {b['name']!r} overlap in dates and share "
                       f"{len(shared)} players — likely one event under two names (YoY rename?)")


def _check_method(out: list, tour: str, method: dict, meta: dict | None) -> None:
    """method.json publishes the effective production parameters to the /method page.
    Sanity only — never pin tuned values here (those live in test_export.py); the gate
    catches a build that would render impossible constants or drift from meta.json."""
    missing = [k for k in ("elo", "serveReturn", "context", "tiers", "combiner", "protocol")
               if not isinstance(method.get(k), dict)]
    if missing:
        out.append(f"{tour}: method.json missing section(s) {', '.join(missing)}")
        return
    if method.get("tour") != tour:
        out.append(f"{tour}: method.json says tour={method.get('tour')!r}")
    elo = method["elo"]
    for key, ok in (("ratingScale", lambda v: v > 0), ("kScale", lambda v: v > 0),
                    ("surfaceBlend", lambda v: 0 <= v <= 1), ("movCap", lambda v: v >= 1)):
        v = elo.get(key)
        if not isinstance(v, (int, float)) or not ok(v):
            out.append(f"{tour}: method.json elo.{key}={v!r} out of range")
    mults = method["tiers"].get("kMult")
    if not isinstance(mults, dict) or not mults or \
            any(not isinstance(v, (int, float)) or not 0.3 < v < 2.0 for v in mults.values()):
        out.append(f"{tour}: method.json tiers.kMult implausible ({mults!r})")
    comb = method["combiner"]
    nfeat = comb.get("featureCount")
    if nfeat != len(FEATURES):
        out.append(f"{tour}: method.json featureCount {nfeat} != {len(FEATURES)} (schema drift)")
    feats = (meta or {}).get("features")
    if isinstance(feats, list) and nfeat != len(feats):
        out.append(f"{tour}: method.json featureCount {nfeat} != meta.features {len(feats)}")
    if not isinstance(comb.get("nBag"), int) or comb["nBag"] < 1:
        out.append(f"{tour}: method.json combiner.nBag={comb.get('nBag')!r} invalid")


def output_problems(tour: str, oc: dict, now: pd.Timestamp, prev: dict | None = None) -> list[str]:
    """Pure given a read_outputs() dict; prev is the previous run's output snapshot
    ({"matches", "forecast_lines"}) for monotonicity, or None on the first run."""
    out: list[str] = []
    data = oc.get("data", {})
    prev = prev or {}
    for stem in oc.get("missing", []):
        out.append(f"{tour}: {stem}.json missing")
    for stem in oc.get("corrupt", []):
        out.append(f"{tour}: {stem}.json is present but unparseable")
    offseason = _offseason(now)

    meta = data.get("meta")
    if isinstance(meta, dict):
        feats = meta.get("features")
        nfeat = len(feats) if isinstance(feats, list) else None
        if nfeat != len(FEATURES):
            out.append(f"{tour}: meta.features has {nfeat} entries (expected {len(FEATURES)})")
        n = meta.get("matches")
        floor = HEALTH_MIN_MATCHES.get(tour, 0)
        if not isinstance(n, int) or n < floor:
            out.append(f"{tour}: meta.matches {n} below floor {floor}")
        elif isinstance(prev.get("matches"), int) and n < prev["matches"] - 50:
            out.append(f"{tour}: meta.matches dropped {prev['matches']} -> {n}")
        ap, players = meta.get("activePlayers"), data.get("players")
        if isinstance(players, list) and ap is not None and len(players) != ap:
            out.append(f"{tour}: players.json has {len(players)} rows but meta.activePlayers={ap}")
        age = _age_days(meta.get("lastUpdated"), now)
        if age is None:
            out.append(f"{tour}: meta.lastUpdated missing/unparseable ({meta.get('lastUpdated')!r})")
        elif age > HEALTH_MAX_BUILD_AGE_DAYS:
            out.append(f"{tour}: outputs last built {age}d ago (max {HEALTH_MAX_BUILD_AGE_DAYS})")

    method = data.get("method")
    if isinstance(method, dict):
        _check_method(out, tour, method, meta if isinstance(meta, dict) else None)

    players = data.get("players")
    if isinstance(players, list) and players:
        if [p.get("eloRank") for p in players] != list(range(1, len(players) + 1)):
            out.append(f"{tour}: players.json eloRank not contiguous 1..{len(players)}")
        if any(not p.get("name") or p.get("elo") is None for p in players):
            out.append(f"{tour}: players.json has a null name or elo")
        _flag_placeholders(out, tour, "players.json", (p.get("name") for p in players))
        # enrichment fields are nullable by design (old snapshots lack the keys), but a
        # PRESENT value must be sane: a units slip (64.2 for 0.642) or junk height would
        # ship wrong numbers to every board that renders them
        bad_h = [(p.get("name"), p.get("heightCm")) for p in players
                 if p.get("heightCm") is not None
                 and not (isinstance(p.get("heightCm"), int) and 140 <= p["heightCm"] <= 225)]
        if bad_h:
            out.append(f"{tour}: players.json heightCm implausible for {len(bad_h)} player(s), "
                       f"e.g. {bad_h[0][0]!r}={bad_h[0][1]!r} (expect int in 140..225)")
        bad_pct = [(p.get("name"), k, p.get(k)) for p in players for k in _PLAYER_PCT_FIELDS
                   if p.get(k) is not None and not _is_prob(p.get(k))]
        if bad_pct:
            n0, k0, v0 = bad_pct[0]
            out.append(f"{tour}: players.json {k0}={v0!r} for {n0!r} out of [0,1] "
                       f"({len(bad_pct)} bad value(s))")
        if not offseason:
            frac = sum(1 for p in players if p.get("liveRank") is None) / len(players)
            if frac > HEALTH_MAX_LIVERANK_NULL_FRAC:
                out.append(f"{tour}: {frac:.0%} of top players have no liveRank "
                           f"(max {HEALTH_MAX_LIVERANK_NULL_FRAC:.0%}) — rankings source may have drifted")

    mx = data.get("matrix")
    if isinstance(mx, dict):
        _check_matrix(out, tour, mx)

    ts = data.get("tournaments")
    if isinstance(ts, list):
        if not ts and not offseason:
            out.append(f"{tour}: tournaments.json is empty")
        elif ts and not offseason and not any(t.get("status") in ("live", "upcoming") for t in ts):
            out.append(f"{tour}: tournaments.json has no live/upcoming event")
        for t in ts:
            if isinstance(t, dict):
                _check_tournament(out, tour, t)
        _tournament_name_problems(out, tour, ts)

    br = data.get("brackets")
    if isinstance(br, list):
        _check_brackets(out, tour, br, ts if isinstance(ts, list) else None)

    up = data.get("upcoming")
    if isinstance(up, list):
        if not up and not offseason:
            out.append(f"{tour}: upcoming.json is empty")
        for m in up:
            if m.get("playerA") and m.get("playerA") == m.get("playerB"):
                out.append(f"{tour}: upcoming.json row has identical players ({m.get('playerA')!r})")
            if not _is_prob(m.get("pA")):
                out.append(f"{tour}: upcoming.json pA={m.get('pA')!r} out of [0,1]")
        _flag_placeholders(out, tour, "upcoming.json",
                           (n for m in up for n in (m.get("playerA"), m.get("playerB"))))

    fx = data.get("fixtures")
    if isinstance(fx, list):
        for f in fx:
            mp = f.get("modelProb")
            if not _is_prob(mp):
                out.append(f"{tour}: fixtures.json modelProb={mp!r} out of [0,1]")
            elif bool(f.get("upset")) != (mp < 0.5):
                out.append(f"{tour}: fixtures.json upset flag disagrees with modelProb ({mp})")

    fc = oc.get("forecast")
    if fc is not None and isinstance(prev.get("forecast_lines"), int) and fc["lines"] < prev["forecast_lines"]:
        out.append(f"{tour}: forecast log shrank {prev['forecast_lines']} -> {fc['lines']} lines")
    if fc is not None:
        # liveness: the log appends on every run while any upcoming match exists, so a
        # present-but-frozen max(as_of) means the track step is silently failing (or the
        # daily persist push keeps losing). An absent log / empty max stays silent — a
        # fresh clone is legitimate. Gate-ADVISORY: eval history is never a build dependency.
        fc_age = _age_days(fc.get("max_as_of"), now)
        max_fc = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_FORECAST_AGE_DAYS
        if fc_age is not None and fc_age > max_fc:
            out.append(f"{tour}: forecast log last advanced {fc_age}d ago (max {max_fc}) "
                       f"— the track step may be silently failing")

    kl = oc.get("kalshi_ledger")
    if isinstance(kl, list):
        _check_kalshi_ledger(out, tour, kl)

    tr = data.get("track")
    if isinstance(tr, dict):
        mf = tr.get("matchForecasts") or {}
        g, p, lg = mf.get("graded"), mf.get("pending"), mf.get("logged")
        if all(isinstance(x, int) for x in (g, p, lg)) and g + p != lg:
            out.append(f"{tour}: track.json graded+pending ({g}+{p}) != logged ({lg})")
        # Model-decay advisory: track.py owns the thresholds (config DRIFT_*) and ships the
        # verdict; we only surface it. Advisory, never deploy-blocking — like market lag,
        # a re-tune recommendation is a benchmark signal, not a build dependency.
        dr = mf.get("drift")
        if isinstance(dr, dict) and dr.get("status") == "drift":
            out.append(f"{tour}: forecast drift over last {dr.get('n')} graded "
                       f"({dr.get('windowDays')}d): live logloss {dr.get('logloss')} vs "
                       f"self-expected {dr.get('expectedLogloss')} (d=+{dr.get('d')}, "
                       f"t={dr.get('t')}) — model scoring worse than its stated confidence; "
                       f"re-tune recommended")

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
                out.append(f"{tour}: market.json odds coverage ends {mk['lastMatchedDate']} but "
                           f"scored matches run to {mk['oosEnd']} ({lag}d gap, max "
                           f"{HEALTH_MAX_MARKET_LAG_DAYS}) — did the odds feed drop a book?")

    return out


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


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="exit non-zero on any problem")
    ap.add_argument("--issue-body", action="store_true",
                    help="print a GitHub-issue body from the existing health.json (empty if ok)")
    ap.add_argument("--gate", action="store_true",
                    help="pre-deploy gate: exit non-zero on any produced-OUTPUT integrity "
                         "problem (not source freshness / run-over-run deltas); does not write "
                         "health.json — run BEFORE deploy so a wrong build can't ship")
    args = ap.parse_args()

    health_path = OUTPUT_DIR / "health.json"

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
        now = pd.Timestamp(datetime.now(UTC).date())
        blocking: list[str] = []
        for tour in TOURS:
            for pr in output_problems(tour, read_outputs(tour), now, prev=None):
                if _gate_blocks(pr):
                    blocking.append(pr)
                    print(f"  GATE/{tour}: BLOCK {pr}")
                else:
                    print(f"  GATE/{tour}: warn  {pr}  (advisory — post-deploy sentinel handles it)")
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

    now = pd.Timestamp(datetime.now(UTC).date())
    # `generated` stays day-granular (problem strings key off it for dedup); generatedAt
    # is the precise stamp the /health page shows and ages client-side.
    report, all_problems = {"generated": str(now.date()),
                            "generatedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "tours": {}}, []
    for tour in TOURS:
        h = tour_health(tour, now)
        checks = source_checks(tour, h, now)
        p = [r["problem"] for r in checks if r["problem"]]
        prev_out = ((prev or {}).get("tours", {}).get(tour, {}) or {}).get("output") or {}
        oc = read_outputs(tour)
        op = output_problems(tour, oc, now, prev_out)
        meta = oc["data"].get("meta") or {}
        h["checks"] = checks
        h["problems"] = p
        h["output"] = {
            "matches": meta.get("matches"),
            "forecast_lines": (oc["forecast"] or {}).get("lines"),
            "forecast_max_as_of": (oc["forecast"] or {}).get("max_as_of"),
            "problems": op,
        }
        report["tours"][tour] = h
        all_problems += p + op
        print(f"  health/{tour}: results to {h['date_max']}, stats to {h['stats_date_max']}, "
              f"season stats {h['cur_year_stats_fraction']}; {len(op)} output problem(s)")
    report["ok"] = not all_problems
    # Issue-traffic dedup for the hourly sentinel: the report step only comments/reds a
    # quick run when the problem set CHANGED (day-granular `now` keeps age strings stable
    # within a UTC day, so this flaps at most once per day, not hourly).
    prev_problems = sorted(p for t in ((prev or {}).get("tours") or {}).values()
                           for p in (t.get("problems") or []) + ((t.get("output") or {}).get("problems") or []))
    report["problems_changed"] = sorted(all_problems) != prev_problems

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    health_path.write_text(json.dumps(report, indent=2))
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
    if args.strict and all_problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
