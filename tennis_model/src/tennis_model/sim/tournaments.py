"""Project the model's title odds for the latest tournaments.

Recent matches are grouped into events (the fresh feed has no tourney_id, so we group
by name within a capture window wide enough to hold a two-week Slam). For each event we
seed its field by surface-blended Elo into a standard bracket and Monte-Carlo it:

  - completed events  -> field = all participants; show the model's pre-tournament title
    odds alongside the actual champion (did the favourite deliver?).
  - in-progress events -> field = players who haven't lost yet; live title odds.

Re-seeding (rather than reconstructing the exact draw) keeps this robust to the fresh
feed's missing match_num / data gaps; title odds are dominated by field strength anyway.
"""

from __future__ import annotations

import json

import pandas as pd

from ..config import live_dir
from ..data.results import _name_key
from .simulate import project_field

_KO_ROUNDS = {"R128", "R64", "R32", "R16", "QF", "SF", "F"}
ROUND_COLS = ["R128", "R64", "R32", "R16", "QF", "SF", "F", "Champion"]  # reach-prob columns, entry -> title
TOP_PROJECTION = 24          # players kept in each event's odds list


def _load_fields(tour: str) -> dict:
    """ESPN per-event {field, eliminated} written by data.live.download_live (if present)."""
    p = live_dir(tour) / "fields.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _level_label(lv: object, tour: str) -> str:
    s = str(lv)
    t = tour.upper()
    if s in ("nan", "None", ""):
        return f"{t} Tour"
    if s in ("G", "Grand", "GrandSlam") or "grand" in s.lower():
        return "Grand Slam"
    if s == "F":
        return "Tour Finals"
    if s == "M" or s.endswith("1000"):
        return "Masters 1000"
    for n in ("1000", "500", "250", "125"):
        if s.endswith(n):
            return f"{t} {n}"
    return {"D": "Davis/BJK Cup", "O": "Olympics", "A": f"{t} Tour"}.get(s, s)


def _known_names(df: pd.DataFrame) -> set:
    """Tournament names that come from the archive (have a real level), for de-sponsoring."""
    return set(df.loc[df["tourney_level"].notna(), "tourney_name"].dropna().astype(str).unique())


def _display_name(name: str, known: set) -> str:
    """Prefer a clean archive name (city) embedded in an ESPN sponsor title.

    e.g. 'Lexus Eastbourne Open' -> 'Eastbourne', 'Vanda Pharmaceuticals Mallorca
    Championships' -> 'Mallorca'. Falls back to the original name.
    """
    low = name.lower()
    best = None
    for kn in known:
        k = kn.lower()
        if len(k) >= 5 and k in low and (best is None or len(k) > len(best)):
            best = kn
    return best or name


def recent_tournaments(df: pd.DataFrame, within_days: int = 40,
                       recent_days: int = 18, max_events: int = 14) -> list:
    """(name, sub_df) for single-elim events ending within `recent_days` of the data."""
    dmax = df["date"].max()
    win = df[df["date"] >= dmax - pd.Timedelta(days=within_days)]
    events = []
    for name, g in win.groupby("tourney_name"):
        if not (set(g["round"].dropna()) & _KO_ROUNDS):
            continue                                  # skip round-robin / team events
        end = g["date"].max()
        if (dmax - end).days > recent_days:
            continue
        events.append((str(name), g.copy(), end))
    events.sort(key=lambda e: e[2], reverse=True)
    return [(n, g) for n, g, _ in events[:max_events]]


def project_tournament(predictor, name: str, g: pd.DataFrame, tour: str,
                       known: set | None = None, top_set: set | None = None,
                       espn_fields: dict | None = None, resolve=None,
                       n_sims: int = 8000, seed: int = 11) -> dict | None:
    surface = g["surface_b"].mode().iloc[0]
    bo = pd.to_numeric(g["best_of"], errors="coerce").max()
    best_of = int(bo) if pd.notna(bo) else 3
    level = _level_label(g["tourney_level"].mode().iloc[0] if g["tourney_level"].notna().any() else "", tour)

    eliminated = set(g["loser_name"])
    final_rows = g[g["round"] == "F"]
    completed = len(final_rows) > 0

    champ = runner = None
    if completed:
        fr = final_rows.sort_values("date").iloc[-1]
        champ, runner = fr["winner_name"], fr["loser_name"]
        field_pool = set(g["winner_name"]) | set(g["loser_name"])     # full field (all played)
    else:
        # Live: prefer ESPN's FULL main-draw field (incl. scheduled) so the Day-1
        # favourite reflects everyone still in the draw, not just those who've finished.
        ef = (espn_fields or {}).get(name)
        if ef and resolve and len(ef["field"]) >= 8:
            field_pool = {resolve(n) for n in ef["field"]}
            eliminated = {resolve(n) for n in ef["eliminated"]} | eliminated
        else:
            field_pool = set(g["winner_name"]) | set(g["loser_name"])

    if len(field_pool) < 8:              # dedup-leftover fragment, not a real draw
        return None
    if top_set is not None and len(field_pool & top_set) < 2:
        return None                      # sub-tour / ITF event (no tour-strength field)

    alive = field_pool - eliminated
    field = list(field_pool if completed else alive)
    if len(field) < 2:
        return None

    elo = predictor.elo
    field = sorted(field, key=lambda p: elo.blended(p, surface), reverse=True)
    sim = project_field(predictor, field, surface=surface, best_of=best_of,
                        n_sims=n_sims, seed=seed)
    cols = set(sim.columns)
    proj = [{
        "name": r.player,
        "champion": round(float(r.Champion), 4),
        "final": round(float(r.F), 4) if "F" in cols else None,
        "sf": round(float(r.SF), 4) if "SF" in cols else None,
        # per-round reach odds (entry -> title) for the round-by-round forecast table
        "reach": {c: round(float(getattr(r, c)), 4) for c in ROUND_COLS if c in cols},
    } for r in sim.head(TOP_PROJECTION).itertuples(index=False)]
    favorite = proj[0]["name"] if proj else None

    return {
        "name": _display_name(name, known or set()), "surface": surface, "level": level, "bestOf": best_of,
        "start": str(g["date"].min().date()), "end": str(g["date"].max().date()),
        "status": "completed" if completed else "live",
        "drawSize": len(field_pool), "aliveCount": len(alive),
        "champion": champ, "runnerUp": runner,
        "modelFavorite": favorite,
        "favoritePicked": bool(completed and favorite == champ),
        "projection": proj,
    }


def build_tournaments(predictor, df: pd.DataFrame, tour: str, **kw) -> list:
    known = _known_names(df)
    top_set = set(sorted(predictor.elo.overall, key=predictor.elo.elo, reverse=True)[:100])
    espn_fields = _load_fields(tour)
    # map ESPN player names onto the predictor's canonical spellings (accent/punct-insensitive)
    canon: dict = {}
    for k in predictor.elo.overall:
        canon.setdefault(_name_key(k), k)
    resolve = lambda n: canon.get(_name_key(n), n)
    out = []
    for name, g in recent_tournaments(df):
        t = project_tournament(predictor, name, g, tour, known=known, top_set=top_set,
                               espn_fields=espn_fields, resolve=resolve, **kw)
        if t:
            out.append(t)
    # Live (in-progress) events lead the board; within each group, most recent first.
    out.sort(key=lambda t: t["end"], reverse=True)
    out.sort(key=lambda t: t["status"] != "live")
    return out
