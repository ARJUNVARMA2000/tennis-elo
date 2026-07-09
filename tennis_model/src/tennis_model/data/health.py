"""Data-health sentinel: fail loudly when the pipeline quietly stops making sense.

Two layers, both surfaced in data/output/health.json and both reddening the daily
build under --strict:
  * source freshness (tour_health/problems) — a scraper silently froze and the newest
    match/serve-stats row stopped advancing. The TML GitHub freeze of Jan 2026 went
    unnoticed for months precisely because every downloader failure was silent.
  * produced output (read_outputs/output_problems) — the JSON the web actually reads
    (counts, tournaments, matches, predictions) is missing, stale, or internally
    inconsistent even though the sources looked fine.

The daily workflow runs this without --strict (always writes health.json, exit 0) and a
follow-up step reads health.json to open/close a `data-health` GitHub issue and red the
run. --issue-body prints that issue's Markdown; --strict is kept for local use.

Run:  PYTHONPATH=src python -m tennis_model.data.health [--strict | --issue-body]
"""

from __future__ import annotations

import itertools
import json
import os
from collections import Counter
from datetime import UTC, datetime

import pandas as pd

from ..config import (
    DATA_DIR,
    HEALTH_MAX_BUILD_AGE_DAYS,
    HEALTH_MAX_LIVERANK_NULL_FRAC,
    HEALTH_MAX_RESULT_AGE_DAYS,
    HEALTH_MAX_STATS_AGE_DAYS,
    HEALTH_MIN_MATCHES,
    HEALTH_MIN_STATS_FRACTION,
    HEALTH_OFFSEASON_RELAX_DAYS,
    OUTPUT_DIR,
    TOURS,
    output_dir,
)
from ..model.features import FEATURES
from .results import load_matches


def _offseason(now: pd.Timestamp) -> bool:
    # the season effectively ends mid-November (Finals/Davis Cup), not December — relax
    # the age/emptiness gates from Nov 21 so the quiet weeks don't red the build
    return now.month == 12 or (now.month == 11 and now.day > 20)


# ---------------------------------------------------------------------------
# Source freshness (are the scrapers still advancing?)
# ---------------------------------------------------------------------------
def tour_health(tour: str, now: pd.Timestamp) -> dict:
    df = load_matches(tour)
    completed = df[df["completed"]]
    stats_rows = df[df["has_stats"]]
    cur = df[df["date"].dt.year == now.year]
    # empty slices give NaT maxima — report None (flagged by problems()) rather than crash
    date_max = df["date"].max() if len(df) else pd.NaT
    res_max = completed["date"].max() if len(completed) else pd.NaT
    stat_max = stats_rows["date"].max() if len(stats_rows) else pd.NaT
    return {
        "matches": int(len(df)),
        "date_max": str(date_max.date()) if pd.notna(date_max) else None,
        "result_age_days": int((now - res_max).days) if pd.notna(res_max) else None,
        "stats_date_max": str(stat_max.date()) if pd.notna(stat_max) else None,
        "stats_age_days": int((now - stat_max).days) if pd.notna(stat_max) else None,
        "cur_year_matches": int(len(cur)),
        "cur_year_stats_fraction": round(float(cur["has_stats"].mean()), 4) if len(cur) else None,
    }


def problems(tour: str, h: dict, now: pd.Timestamp) -> list[str]:
    offseason = _offseason(now)
    max_result = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_RESULT_AGE_DAYS
    max_stats = HEALTH_OFFSEASON_RELAX_DAYS if offseason else HEALTH_MAX_STATS_AGE_DAYS
    min_frac = HEALTH_MIN_STATS_FRACTION.get(tour, 0.0)
    out = []
    if h["result_age_days"] is None:
        out.append(f"{tour}: no completed matches loaded")
    elif h["result_age_days"] > max_result:
        out.append(f"{tour}: newest completed match is {h['result_age_days']}d old (max {max_result})")
    if min_frac > 0:
        if h["stats_age_days"] is None or h["stats_age_days"] > max_stats:
            out.append(f"{tour}: newest serve-stats row is {h['stats_age_days']}d old (max {max_stats})")
        frac = h["cur_year_stats_fraction"]
        if frac is not None and h["cur_year_matches"] >= 100 and frac < min_frac:
            out.append(f"{tour}: current-season stats coverage {frac:.0%} < {min_frac:.0%}")
    return out


# ---------------------------------------------------------------------------
# Produced-output validation (does the JSON the web reads make sense?)
# ---------------------------------------------------------------------------
# The web reads these per tour; the first group must always exist and parse, the second
# is best-effort (accuracy is backtest-only, track needs graded forecasts).
_REQUIRED_OUTPUTS = ("meta", "players", "tournaments", "upcoming", "matrix",
                     "ratings_history", "profiles", "draws", "fixtures")
_OPTIONAL_OUTPUTS = ("accuracy", "track")
_PLACEHOLDER_NAMES = {"tbd", "tba", "bye", "qualifier"}   # mirror data/live.py
_STATUSES = {"live", "upcoming", "completed"}
_DRAW_STATES = {"real", "partial", "seeded", "final"}
_REACH_ORDER = ("R128", "R64", "R32", "R16", "QF", "SF", "F", "Champion")


def read_outputs(tour: str) -> dict:
    """Load a tour's produced JSON + forecast log. IO seam (monkeypatched in tests).

    Returns {"data": {stem: parsed}, "missing": [required stems absent],
             "corrupt": [stems present but unparseable],
             "forecast": {"lines": int, "max_as_of": str|None} | None}.
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
            data[stem] = json.loads(f.read_text())
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
    return {"data": data, "missing": missing, "corrupt": corrupt, "forecast": forecast}


def _is_prob(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0.0 <= float(x) <= 1.0


def _pow2(n) -> bool:
    return isinstance(n, int) and n >= 2 and (n & (n - 1)) == 0


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
            if not _is_prob(v):
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
    # a real bracket is a true power-of-two draw; a leaked 'TBD' turns 128 into 129.
    # completed/partial/seeded sizes are len(field_pool) and legitimately non-power-of-two.
    if ds == "real" and isinstance(size, int) and not _pow2(size):
        out.append(f"{tour}: tournament {name!r} real draw size {size} is not a power of two")
    if status == "completed" and not champ:
        out.append(f"{tour}: completed tournament {name!r} has no champion")
    if status in ("live", "upcoming") and champ:
        out.append(f"{tour}: {status} tournament {name!r} already names champion {champ!r}")
    proj = t.get("projection") or []
    _check_projection(out, tour, name, proj)
    _flag_placeholders(out, tour, f"tournament {name!r}", (p.get("name") for p in proj))


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

    players = data.get("players")
    if isinstance(players, list) and players:
        if [p.get("eloRank") for p in players] != list(range(1, len(players) + 1)):
            out.append(f"{tour}: players.json eloRank not contiguous 1..{len(players)}")
        if any(not p.get("name") or p.get("elo") is None for p in players):
            out.append(f"{tour}: players.json has a null name or elo")
        _flag_placeholders(out, tour, "players.json", (p.get("name") for p in players))
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

    tr = data.get("track")
    if isinstance(tr, dict):
        mf = tr.get("matchForecasts") or {}
        g, p, lg = mf.get("graded"), mf.get("pending"), mf.get("logged")
        if all(isinstance(x, int) for x in (g, p, lg)) and g + p != lg:
            out.append(f"{tour}: track.json graded+pending ({g}+{p}) != logged ({lg})")

    return out


def format_issue_body(report: dict, run_url: str | None = None) -> str:
    """Markdown for the `data-health` GitHub issue — includes a ready-to-paste fix prompt."""
    probs: list[str] = []
    for h in report.get("tours", {}).values():
        probs += h.get("problems", [])
        probs += (h.get("output") or {}).get("problems", [])
    lines = [f"The daily pipeline **data health check failed** on {report.get('generated', '?')}.",
             "", "### Problems"]
    shown, extra = probs[:50], max(0, len(probs) - 50)   # cap: a systemic break can flag many
    lines += [f"- {p}" for p in shown] or ["- (no detail — see run logs)"]
    if extra:
        lines.append(f"- …and {extra} more")
    if run_url:
        lines += ["", f"Failing run: {run_url}"]
    summary = "; ".join(probs) if probs else "see run logs"
    lines += [
        "", "### Fix it in a new session",
        "Open a new Claude Code session and paste:", "",
        f"> Investigate and resolve the `data-health` issue. The daily pipeline health check "
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
    args = ap.parse_args()

    health_path = OUTPUT_DIR / "health.json"

    if args.issue_body:
        if not health_path.exists():
            return 0
        report = json.loads(health_path.read_text())
        if not report.get("ok", True):
            print(format_issue_body(report, run_url=os.environ.get("GITHUB_RUN_URL")))
        return 0

    prev = None
    if health_path.exists():
        try:
            prev = json.loads(health_path.read_text())
        except ValueError:
            prev = None

    now = pd.Timestamp(datetime.now(UTC).date())
    report, all_problems = {"generated": str(now.date()), "tours": {}}, []
    for tour in TOURS:
        h = tour_health(tour, now)
        p = problems(tour, h, now)
        prev_out = ((prev or {}).get("tours", {}).get(tour, {}) or {}).get("output") or {}
        oc = read_outputs(tour)
        op = output_problems(tour, oc, now, prev_out)
        meta = oc["data"].get("meta") or {}
        h["problems"] = p
        h["output"] = {
            "matches": meta.get("matches"),
            "forecast_lines": (oc["forecast"] or {}).get("lines"),
            "problems": op,
        }
        report["tours"][tour] = h
        all_problems += p + op
        print(f"  health/{tour}: results to {h['date_max']}, stats to {h['stats_date_max']}, "
              f"season stats {h['cur_year_stats_fraction']}; {len(op)} output problem(s)")
    report["ok"] = not all_problems

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    health_path.write_text(json.dumps(report, indent=2))
    for pr in all_problems:
        print(f"  HEALTH: {pr}")
    if args.strict and all_problems:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
