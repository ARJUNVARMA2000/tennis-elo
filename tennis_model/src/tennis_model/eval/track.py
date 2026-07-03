"""Forecast tracking: log point-in-time predictions, grade them against results.

The rest of the engine is overwrite-only — today's JSON replaces yesterday's, nothing
is kept. This module adds the one thing needed for forecast *validation* (as opposed to
live forecasting): an append-only log of predictions captured BEFORE matches resolve,
plus a grader that scores them once the actual results arrive.

  data/forecast_log/<tour>.jsonl   the log — the single source of truth that PERSISTS
                                   across daily runs (committed back by the workflow).
  data/output/<tour>/track.json    derived scorecard — regenerated every run, mirrored
                                   to the web app like every other artifact.

Two line types in the log:
  match       one upcoming matchup + P(playerA wins), logged once at first sighting so
              the probability is a genuine pre-result forecast (the model has not yet
              trained on the outcome).
  tournament  a daily snapshot of an in-progress event's title odds (odds evolve as the
              draw thins, so we keep one snapshot per event per day).

Grading joins logged matches to completed results by player-pair within a short date
window (a given pair rarely plays twice in three weeks), so it is robust to ESPN's
sponsor event names vs the archive's clean names. Unresolved logs stay `pending`.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .. import __version__
from ..config import DATA_DIR, SURFACES, live_dir, output_dir
from ..data.results import _name_key as nkey
from .metrics import calibration_table, score

FORECAST_DIR = DATA_DIR / "forecast_log"
JOIN_WINDOW_DAYS = 21          # max gap between forecast and the result it grades
RECENT_N = 60                  # graded decisions surfaced for the UI table

# Season-by-month fallback when an event's surface isn't yet in the match frame.
_MONTH_SURFACE = {1: "Hard", 2: "Hard", 3: "Hard", 4: "Clay", 5: "Clay", 6: "Grass",
                  7: "Grass", 8: "Hard", 9: "Hard", 10: "Hard", 11: "Hard", 12: "Hard"}


# ---------------------------------------------------------------------------
# Keys / small helpers
# ---------------------------------------------------------------------------
def _norm_event(name: object) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())[:18]


def _season(*candidates) -> int:
    for c in candidates:
        s = str(c) if c is not None else ""
        if len(s) >= 4 and s[:4].isdigit():
            return int(s[:4])
    return datetime.now(UTC).year


def _match_key(r: dict) -> str:
    a, b = sorted((nkey(r["playerA"]), nkey(r["playerB"])))
    return f"{a}|{b}|{_norm_event(r.get('event'))}|{r.get('round')}|{r.get('season')}"


def _tourn_key(r: dict) -> str:
    return f"{_norm_event(r.get('event'))}|{r.get('season')}|{r.get('as_of')}"


def _read_log(path) -> list:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _event_attrs(df: pd.DataFrame, event: str) -> tuple:
    """(surface, best_of) for an ESPN event name, taken from its rows in the match
    frame (matched by loose name containment). Returns (None, None) if not found."""
    if "tourney_name" not in df.columns or "surface_b" not in df.columns:
        return None, None
    ek = str(event).lower()
    names = df["tourney_name"].astype(str)
    mask = names.str.lower().apply(lambda t: bool(t) and (t in ek or ek in t))
    sub = df[mask]
    if sub.empty:
        return None, None
    surf = sub["surface_b"].mode()
    bo = pd.to_numeric(sub["best_of"], errors="coerce").max()
    return (surf.iloc[0] if not surf.empty else None,
            int(bo) if pd.notna(bo) else None)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def log_forecasts(tour: str, predictor, df: pd.DataFrame,
                  upcoming: pd.DataFrame | None, as_of: str) -> int:
    """Append new match + tournament forecasts to the log. Returns # records added.

    Idempotent: a matchup is logged once (first sighting locks the forecast), and a
    tournament once per day — so re-running the pipeline never duplicates lines.
    """
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    path = FORECAST_DIR / f"{tour}.jsonl"
    existing = _read_log(path)
    seen_match = {_match_key(r) for r in existing if r.get("type") == "match"}
    seen_tourn = {_tourn_key(r) for r in existing if r.get("type") == "tournament"}

    # resolve ESPN display names to the model's canonical spellings (else win_prob,
    # which keys off exact names, silently returns ~0.5 for unknown players).
    key2name = {nkey(n): n for n in predictor.elo.overall}
    new: list = []

    if upcoming is not None and not upcoming.empty:
        for r in upcoming.itertuples(index=False):
            a, b = key2name.get(nkey(r.playerA)), key2name.get(nkey(r.playerB))
            if not a or not b or nkey(a) == nkey(b):
                continue                                    # unknown player / same player
            surface, bo = _event_attrs(df, r.tourney_name)
            if surface is None:
                month = int(str(r.tourney_date)[5:7]) if str(r.tourney_date)[5:7].isdigit() else 1
                surface = _MONTH_SURFACE.get(month, "Hard")
            bo = bo or 3
            rec = {
                "type": "match", "as_of": as_of, "tour": tour,
                "event": str(r.tourney_name), "round": r.round,
                "surface": surface, "best_of": int(bo),
                "season": _season(r.tourney_date, as_of),
                "playerA": a, "playerB": b, "model_version": __version__,
            }
            k = _match_key(rec)
            if k in seen_match:
                continue
            rec["p"] = round(float(predictor.win_prob(
                a, b, surface=surface, best_of=int(bo), event=str(r.tourney_name))), 4)
            seen_match.add(k)
            new.append(rec)

    # tournament snapshots: reuse the title odds already computed for tournaments.json
    # (status == "live" only — completed events have no pre-result odds to log).
    tournaments = _read_json(output_dir(tour) / "tournaments.json") or []
    for ev in tournaments:
        if ev.get("status") != "live":
            continue
        rec = {
            "type": "tournament", "as_of": as_of, "tour": tour,
            "event": ev.get("name"), "season": _season(ev.get("end"), as_of),
            "surface": ev.get("surface"), "level": ev.get("level"),
            "modelFavorite": ev.get("modelFavorite"),
            "projection": ev.get("projection"), "model_version": __version__,
        }
        k = _tourn_key(rec)
        if k in seen_tourn:
            continue
        seen_tourn.add(k)
        new.append(rec)

    if new:
        with open(path, "a", encoding="utf-8") as f:
            for rec in new:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(new)


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------
def _grade_matches(matches: list, df: pd.DataFrame) -> list:
    """Join logged match forecasts to completed results; return graded records."""
    comp = df[df["completed"]] if "completed" in df else df
    index: dict = defaultdict(list)
    for row in comp.itertuples(index=False):
        wk, lk = nkey(row.winner_name), nkey(row.loser_name)
        index[frozenset((wk, lk))].append((pd.Timestamp(row.date), row.winner_name, row.loser_name))

    graded = []
    for r in matches:
        pair = frozenset((nkey(r["playerA"]), nkey(r["playerB"])))
        cands = index.get(pair)
        if not cands:
            continue                                        # not resolved yet -> pending
        as_of = pd.Timestamp(r["as_of"])
        valid = [c for c in cands if -1 <= (c[0] - as_of).days <= JOIN_WINDOW_DAYS]
        if not valid:
            continue
        date, winner, _loser = min(valid, key=lambda c: abs((c[0] - as_of).days))
        a_won = nkey(winner) == nkey(r["playerA"])
        p_a = float(r["p"])
        graded.append({
            **r, "date": date.strftime("%Y-%m-%d"), "actualWinner": winner,
            "p_a": p_a, "a_won": a_won,
            "p_winner": p_a if a_won else 1.0 - p_a,        # winner-oriented (metrics.score)
            "hit": (p_a > 0.5) == a_won,
        })
    return graded


def _grade_tournaments(tourns: list, tour: str) -> dict:
    """Score logged title-odds snapshots against the eventual champion of each event."""
    completed = {}
    for ev in (_read_json(output_dir(tour) / "tournaments.json") or []):
        if ev.get("status") == "completed" and ev.get("champion"):
            completed[_norm_event(ev.get("name"))] = ev

    by_event: dict = defaultdict(list)
    for r in tourns:
        by_event[(_norm_event(r.get("event")), r.get("season"))].append(r)

    events = []
    for (ek, _), snaps in by_event.items():
        ev = completed.get(ek)
        if not ev:
            continue                                        # not finished (or name miss)
        ck = nkey(ev["champion"])
        briers = []
        for s in snaps:
            proj = {nkey(p["name"]): p.get("champion", 0.0) for p in (s.get("projection") or [])}
            briers.append((1.0 - proj.get(ck, 0.0)) ** 2)   # champion-indicator Brier
        last = max(snaps, key=lambda s: s.get("as_of", ""))
        fav = (last.get("projection") or [{}])[0].get("name")
        events.append({
            "event": ev.get("name"), "end": ev.get("end"), "champion": ev["champion"],
            "modelFavorite": fav, "favoritePicked": bool(fav and nkey(fav) == ck),
            "championBrier": round(float(np.mean(briers)), 4), "snapshots": len(snaps),
        })

    if not events:
        return {"events": 0, "hitRate": None, "championBrier": None, "recent": []}
    return {
        "events": len(events),
        "hitRate": round(float(np.mean([e["favoritePicked"] for e in events])), 3),
        "championBrier": round(float(np.mean([e["championBrier"] for e in events])), 4),
        "recent": sorted(events, key=lambda e: e.get("end") or "", reverse=True)[:20],
    }


def _score_or_empty(probs: list) -> dict:
    return score(np.asarray(probs, dtype=float)) if probs else {"n": 0, "acc": None,
                                                                 "logloss": None, "brier": None}


def grade(tour: str, df: pd.DataFrame) -> dict:
    """Read the log, score it against `df`'s results, write + return track.json."""
    log = _read_log(FORECAST_DIR / f"{tour}.jsonl")
    matches = [r for r in log if r.get("type") == "match"]
    tourns = [r for r in log if r.get("type") == "tournament"]
    graded = _grade_matches(matches, df)

    cal = []
    if graded:
        cal = calibration_table(
            np.array([g["p_a"] for g in graded]),
            np.array([1.0 if g["a_won"] else 0.0 for g in graded]),
        ).to_dict("records")

    by_surface = {}
    for s in SURFACES:
        gs = [g["p_winner"] for g in graded if g["surface"] == s]
        if gs:
            by_surface[s] = _score_or_empty(gs)

    by_month: dict = defaultdict(list)
    for g in graded:
        by_month[g["date"][:7]].append(g["p_winner"])
    by_month_out = [{"month": m, **_score_or_empty(v)} for m, v in sorted(by_month.items())]

    recent = [{
        "date": g["date"], "event": g["event"], "round": g["round"], "surface": g["surface"],
        "playerA": g["playerA"], "playerB": g["playerB"], "p": round(g["p_a"], 3),
        "actualWinner": g["actualWinner"], "hit": g["hit"],
    } for g in sorted(graded, key=lambda x: x["date"], reverse=True)[:RECENT_N]]

    out = {
        "tour": tour,
        "lastUpdated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "matchForecasts": {
            "logged": len(matches), "graded": len(graded), "pending": len(matches) - len(graded),
            "overall": _score_or_empty([g["p_winner"] for g in graded]),
            "calibration": cal, "byMonth": by_month_out, "bySurface": by_surface,
            "recent": recent,
        },
        "tournamentOdds": _grade_tournaments(tourns, tour),
    }
    out_path = output_dir(tour) / "track.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _read_upcoming(tour: str) -> pd.DataFrame | None:
    path = live_dir(tour) / "upcoming.csv"
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, encoding="utf-8")
    except Exception:  # noqa: BLE001 — a corrupt/absent upcoming file must not break grading
        return None


def log_and_grade(tour: str, predictor, df: pd.DataFrame) -> dict:
    """Pipeline entry point: log today's forecasts, then (re)grade the whole log."""
    as_of = datetime.now(UTC).date().isoformat()
    n = log_forecasts(tour, predictor, df, _read_upcoming(tour), as_of)
    out = grade(tour, df)
    mf = out["matchForecasts"]
    print(f"  track/{tour}: +{n} logged, {mf['graded']} graded / {mf['pending']} pending; "
          f"tournament odds graded for {out['tournamentOdds']['events']} event(s)")
    return out
