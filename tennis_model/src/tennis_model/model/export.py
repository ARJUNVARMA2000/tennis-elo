"""Build every JSON artifact the web frontend consumes, for one tour.

Kept separate from pipeline orchestration so the export surface is easy to scan:
  players.json          ranking board (Elo + surface + serve/return + style)
  matrix.json           top-N pairwise win probs per surface x format (powers /predict)
  ratings_history.json   monthly Elo trajectories (powers /trends)
  profiles.json         per-player detail: splits, style, recent form, H2H, Elo line
  draws.json            current-top-field tournament projections per surface
  tournaments.json      latest real events: title odds + actual result (powers home)
  upcoming.json         scheduled matches + the model's current win prob (powers /schedule)
  fixtures.json         latest results with the model's pre-match call + upset flags
  accuracy.json         walk-forward metrics, calibration, per-surface breakdown
  meta.json             metadata + headline backtest
  method.json           effective production parameters (powers /method's detail sections)
"""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .. import __version__
from ..config import SURFACES, output_dir
from ..data.charting import build_profiles, name_key
from ..data.rankings import load_rankings
from ..data.results import summary
from .features import FEATURES, STYLE_FEATURES

ACTIVE_DAYS = 550
TOP_MATRIX = 120          # players in the precomputed pairwise matrix
TOP_PROFILES = 200
HISTORY_SINCE = "2016-01"
SLAM_BEST_OF = {"atp": 5, "wta": 3}


def _finite(x):
    """Replace non-finite floats (NaN/±Inf) with None, recursively. A missing value
    reaches here as float('nan') (e.g. a scoreless match's `score`); json.dump would
    emit the bare token `NaN`, which is valid Python-JSON but the browser's strict
    JSON.parse rejects — the whole file fails to parse and the page renders blank.
    null is a valid, frontend-handled stand-in, so sanitise at the single write seam."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_finite(v) for v in x]
    return x


def _write(tour: str, name: str, data) -> None:
    out = output_dir(tour)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / name, "w", encoding="utf-8") as f:
        json.dump(_finite(data), f, ensure_ascii=False, indent=2)


def _active(elo) -> list:
    cutoff = elo.last_date - np.timedelta64(ACTIVE_DAYS, "D")
    return [n for n, last in elo.last_played.items() if last >= cutoff]


def _current_age(m: dict, ref) -> int | None:
    """Latest known age, advanced to `ref` (dataset's most recent date). Fresh live
    rows carry no age, so the last observed value can be a year or two old."""
    age = m.get("age")
    if not pd.notna(age):
        return None
    asof = m.get("age_asof")
    if asof is not None and pd.notna(asof):
        age += max(0.0, (pd.Timestamp(ref) - pd.Timestamp(asof)).days / 365.25)
    return int(age)


def _with_token_order_keys(rankings: dict) -> dict:
    """Also index each ranked player by alphabetically-sorted name tokens, so
    surname-first source forms still join (Xinyu Wang vs the model's Wang Xinyu).
    setdefault keeps real keys authoritative over fallback ones."""
    out = dict(rankings)
    for k, v in rankings.items():
        out.setdefault(" ".join(sorted(k.split())), v)
    return out


def _live_rank_fields(name: str, rankings: dict) -> dict:
    """liveRank/liveRankDelta from the scraped official live rankings (data.rankings),
    joined by the shared name_key; both None when the player isn't matched."""
    k = name_key(name)
    lr = rankings.get(k) or rankings.get(" ".join(sorted(k.split())))
    return {"liveRank": lr["rank"] if lr else None,
            "liveRankDelta": lr.get("delta") if lr else None}


def _win_rate10(ctx, name: str) -> float | None:
    """Win rate over the last <=10 tracked results, or None when nothing is tracked.

    Slices [-10:] explicitly: the underlying deque holds the tour's tuned
    winrate_window (23 on WTA), which would silently change what "10" means."""
    res = ctx.last_results(name)[-10:] if ctx is not None else []
    return round(sum(res) / len(res), 3) if res else None


def build_players(elo, srv, meta, profiles, rankings=None, ctx=None, top=TOP_PROFILES) -> list:
    rankings = _with_token_order_keys(rankings or {})
    rows = []
    for name in _active(elo):
        m = meta.get(name, {})
        st = profiles.get(name_key(name), {})
        rows.append({
            "name": name,
            "elo": round(elo.elo(name)),
            "eloHard": round(elo.surface_elo(name, "Hard")),
            "eloClay": round(elo.surface_elo(name, "Clay")),
            "eloGrass": round(elo.surface_elo(name, "Grass")),
            "servePct": round(srv.avg + srv.global_serve_skill(name), 3),
            "returnPct": round(srv.avg_ret + srv.global_return_skill(name), 3),
            **{f"servePct{s}": round(srv.base.get(s, srv.avg) + srv.serve_skill(name, s), 3)
               for s in SURFACES},
            **{f"returnPct{s}": round((1.0 - srv.base.get(s, srv.avg)) + srv.return_skill(name, s), 3)
               for s in SURFACES},
            # display windows are EXPLICIT (90d / last-10): the states' own tuned
            # windows differ per tour (WTA form_days=65, winrate_window=23) and
            # would silently break what the field names promise
            "form90": round(elo.form_delta(name, elo.last_date, days=90.0)),
            "winRate10": _win_rate10(ctx, name),
            "heightCm": int(m["ht"]) if pd.notna(m.get("ht")) else None,
            "rankPoints": int(m["rank_points"]) if pd.notna(m.get("rank_points")) else None,
            "matches": int(elo.n.get(name, 0)),
            "hand": m.get("hand") if isinstance(m.get("hand"), str) else None,
            "age": _current_age(m, elo.last_date),
            "country": m.get("ioc") if isinstance(m.get("ioc"), str) else None,
            "lastPlayed": pd.Timestamp(elo.last_played[name]).strftime("%Y-%m-%d"),
            "aggression": round(st["style_aggression"], 3) if st.get("style_aggression") == st.get("style_aggression") and "style_aggression" in st else None,
            "serveDom": round(st["style_serve_dom"], 3) if st.get("style_serve_dom") == st.get("style_serve_dom") and "style_serve_dom" in st else None,
            **_live_rank_fields(name, rankings),
        })
    rows.sort(key=lambda r: -r["elo"])
    for i, r in enumerate(rows, 1):
        r["eloRank"] = i
    return rows[:top]


def build_matrix(predictor, players: list, tour: str) -> dict:
    names = [p["name"] for p in players[:TOP_MATRIX]]
    formats = [3, 5] if tour == "atp" else [3]
    surfaces = {}
    for surf in SURFACES:
        surfaces[surf] = {}
        for bo in formats:
            P = predictor.win_prob_matrix(names, surface=surf, best_of=bo)
            surfaces[surf][str(bo)] = np.round(P, 3).tolist()
    return {"players": names, "formats": formats, "surfaces": surfaces}


def build_history(elo, players: list) -> dict:
    keep = {p["name"] for p in players[:80]}
    hist = {}
    for name in keep:
        pts = [[m, e] for m, e in elo.history.get(name, []) if m >= HISTORY_SINCE]
        if len(pts) >= 3:
            hist[name] = pts
    return hist


def _recent_and_h2h(df: pd.DataFrame, names: set) -> tuple[dict, dict]:
    """Last-10 results and head-to-head tallies for the given players."""
    recent = defaultdict(list)
    h2h = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # player -> opp -> [wins, losses]
    sub = df[df["winner_name"].isin(names) | df["loser_name"].isin(names)]
    for r in sub.itertuples(index=False):
        w, l = r.winner_name, r.loser_name
        d = pd.Timestamp(r.date).strftime("%Y-%m-%d")
        if w in names:
            recent[w].append({"date": d, "opp": l, "surface": r.surface_b, "won": True,
                              "score": r.score, "event": r.tourney_name})
            h2h[w][l][0] += 1
        if l in names:
            recent[l].append({"date": d, "opp": w, "surface": r.surface_b, "won": False,
                              "score": r.score, "event": r.tourney_name})
            h2h[l][w][1] += 1
    last10 = {k: v[-10:][::-1] for k, v in recent.items()}
    top_h2h = {}
    for p, opps in h2h.items():
        ranked = sorted(opps.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:8]
        top_h2h[p] = [{"opp": o, "w": rec[0], "l": rec[1]} for o, rec in ranked]
    return last10, top_h2h


def build_profiles_json(df, elo, srv, meta, mcp, players: list) -> dict:
    names = {p["name"] for p in players}
    recent, h2h = _recent_and_h2h(df, names)
    out = {}
    for p in players:
        name = p["name"]
        st = mcp.get(name_key(name), {})
        out[name] = {
            **p,
            "style": {k: (round(st[k], 3) if k in st and st[k] == st[k] else None) for k in STYLE_FEATURES},
            "history": [[m, e] for m, e in elo.history.get(name, []) if m >= HISTORY_SINCE],
            "recent": recent.get(name, []),
            "h2h": h2h.get(name, []),
        }
    return out


def build_draws(predictor, players: list, tour: str) -> dict:
    """Project a 32-player current-top field on each surface (Slam format for the tour)."""
    from ..sim.simulate import project_field
    field = [p["name"] for p in players[:32]]
    bo = SLAM_BEST_OF[tour]
    draws = {}
    for surf in SURFACES:
        sim = project_field(predictor, field, surface=surf, best_of=bo, n_sims=10000, seed=7)
        draws[surf] = [
            {"name": r.player, "champion": round(float(r.Champion), 4),
             "final": round(float(r.F), 4), "sf": round(float(r.SF), 4)}
            for r in sim.head(16).itertuples(index=False)
        ]
    return {"field": field, "bestOf": bo, "surfaces": draws}


def build_fixtures(df, predictor, n=60) -> list:
    """Latest completed matches with the model's pre-match probability + upset flag."""
    d = df[df["completed"]].sort_values("date").tail(400)
    out = []
    for r in d.tail(n).iloc[::-1].itertuples(index=False):
        # model prob the actual winner wins, from the combiner (recompute, leakage-free at ranking time)
        p = predictor.win_prob(r.winner_name, r.loser_name, surface=r.surface_b,
                               best_of=int(r.best_of) if pd.notna(r.best_of) else 3,
                               event=r.tourney_name)
        out.append({
            "date": pd.Timestamp(r.date).strftime("%Y-%m-%d"),
            "event": r.tourney_name, "surface": r.surface_b, "round": r.round,
            "winner": r.winner_name, "loser": r.loser_name, "score": r.score,
            "modelProb": round(p, 3), "upset": bool(p < 0.5),
        })
    return out


_ROUND_DEPTH = {r: i for i, r in enumerate(["R128", "R64", "R32", "R16", "QF", "SF", "F"])}


def build_upcoming(predictor, df, tour: str) -> list:
    """Scheduled / in-progress matches with the model's current win prob (schedule board).

    Sourced from the live feed's upcoming.csv through the shared enricher (model.upcoming) —
    the same primitive the forecast log uses, so a matchup is priced identically in both.
    Event names are de-sponsored like the home board; rows are ordered soonest-first, then
    by round depth within a day."""
    from ..sim.tournaments import _display_name, _known_names
    from .upcoming import enrich_upcoming, load_upcoming
    known = _known_names(df)
    rows = [{
        "event": _display_name(r["event"], known), "date": r["date"], "round": r["round"],
        "surface": r["surface"], "bestOf": r["best_of"], "level": r["level"],
        "playerA": r["playerA"], "playerB": r["playerB"], "pA": round(r["pA"], 4),
    } for r in enrich_upcoming(predictor, df, load_upcoming(tour), tour)]
    rows.sort(key=lambda m: (m["date"], _ROUND_DEPTH.get(m["round"], 9), m["event"]))
    return rows


def build_accuracy(oos: pd.DataFrame) -> dict:
    from ..eval.metrics import calibration_table, score, winner_oriented
    out = {"window": f"{int(oos['year'].min())}-{int(oos['year'].max())}", "n": int(len(oos))}
    out["models"] = {k: {kk: round(vv, 4) for kk, vv in score(oos[c].to_numpy()).items()}
                     for k, c in [("eloBlend", "p_blend"), ("pointModel", "p_point"), ("combiner", "p_combiner")]}
    out["marketAnchor"] = {"acc": 0.690, "brier": 0.196}
    wf = np.arange(len(oos)) % 2 == 0
    p_a, lab = winner_oriented(oos["p_combiner"].to_numpy(), wf)
    out["calibration"] = calibration_table(p_a, lab).to_dict("records")
    out["bySurface"] = {s: round(score(g["p_combiner"].to_numpy())["brier"], 4)
                        for s, g in oos.join(_surface_of(oos)).groupby("surface_b")} if "surface_b" in oos else {}
    return out


def _surface_of(oos):  # oos lacks surface; return empty to skip gracefully
    return pd.DataFrame(index=oos.index)


def build_meta(df, players, accuracy) -> dict:
    s = summary(df)
    return {
        "tour": df["tour"].iloc[0] if "tour" in df else "atp",
        "lastUpdated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataThrough": s["date_max"], "modelVersion": __version__,
        "matches": s["matches"], "players": s["players"], "activePlayers": len(players),
        "features": FEATURES, "surfaces": list(SURFACES),
        "backtest": accuracy.get("models") if accuracy else None,
        "notes": "Hybrid: surface-blended Elo + opponent-adjusted serve/return point model "
                 "+ MCP style -> XGBoost combiner (Platt-calibrated). Walk-forward, leakage-free.",
    }


def _camel(d: dict) -> dict:
    """snake_case keys -> camelCase (dataclass asdict() output -> export convention)."""
    return {re.sub(r"_(\w)", lambda m: m.group(1).upper(), k): v for k, v in d.items()}


def build_method(tour: str) -> dict:
    """Effective production parameters for the /method page's detail sections.

    Pure config: sources only the *_params_for accessors + config constants, so both
    the full and quick paths always publish the CURRENT production intent — never
    hardcode these numbers in page copy (see the 2026-07-09 lessons.md entry). A
    just-retuned config can briefly lead a stale predictor.pkl on the quick path;
    the daily full retrain (and the FeatureParams drift guard) closes that window.
    """
    from dataclasses import asdict

    from ..config import (
        BACKTEST_START_YEAR,
        DEFAULT_RATING,
        N_BAG,
        TIER_ANCHORS,
        TUNE_YEARS,
        VAL_START,
    )
    from ..data.results import tier_mults
    from ..points.markov import P_CLIP
    from ..points.serve_return import sr_params_for
    from ..ratings.elo import params_for
    from .features import ANTISYM, STYLE_DIFFS, SYMMETRIC, feat_params_for
    from .train import EARLY_STOPPING_ROUNDS, effective_xgb_params

    anchors = TIER_ANCHORS.get(tour)
    mults, default_mult = tier_mults(tour)
    return {
        "tour": tour,
        "modelVersion": __version__,
        "defaultRating": DEFAULT_RATING,
        "surfaces": list(SURFACES),
        "elo": _camel(asdict(params_for(tour))),
        "tiers": {
            "anchors": list(anchors) if anchors else None,
            "kMult": mults,
            "default": default_mult,
        },
        "serveReturn": {**_camel(asdict(sr_params_for(tour))), "pClip": list(P_CLIP)},
        "context": _camel(asdict(feat_params_for(tour))),
        "combiner": {
            "algorithm": "xgboost",
            "nBag": N_BAG,
            "calibration": "platt",
            "earlyStoppingRounds": EARLY_STOPPING_ROUNDS,
            "xgb": _camel(effective_xgb_params(tour)),
            "featureCount": len(FEATURES),
            "featureGroups": {
                "antisymmetric": len(ANTISYM) - len(STYLE_DIFFS),
                "style": len(STYLE_DIFFS),
                "symmetric": len(SYMMETRIC),
            },
        },
        "protocol": {
            "backtestStartYear": BACKTEST_START_YEAR,
            "tuneYears": list(TUNE_YEARS),
            "valStartYear": VAL_START,
        },
    }


def export_all(tour, df, elo, srv, meta, predictor, oos=None) -> None:
    """Write every frontend JSON for one tour.

    Works in two modes: a full run passes a fresh walk-forward `oos` (rebuilds
    accuracy.json); a quick refresh passes oos=None and reuses the saved predictor's
    states (elo/srv/meta) — accuracy.json is left to persist from the last full run.
    """
    mcp = build_profiles(tour)
    rankings = load_rankings(tour)
    players = build_players(elo, srv, meta, mcp, rankings, ctx=getattr(predictor, "ctx", None))
    if rankings:   # drift tripwire: a sudden drop in CI logs = source name-format change
        matched = sum(1 for p in players if p["liveRank"] is not None)
        print(f"  rankings/{tour}: matched {matched}/{len(players)} exported players")
    accuracy = build_accuracy(oos) if oos is not None else {}

    _write(tour, "players.json", players)
    _write(tour, "matrix.json", build_matrix(predictor, players, tour))
    _write(tour, "ratings_history.json", build_history(elo, players))
    _write(tour, "profiles.json", build_profiles_json(df, elo, srv, meta, mcp, players))
    _write(tour, "draws.json", build_draws(predictor, players, tour))
    from ..sim.tournaments import build_tournaments
    _write(tour, "tournaments.json", build_tournaments(predictor, df, tour))
    _write(tour, "upcoming.json", build_upcoming(predictor, df, tour))
    _write(tour, "fixtures.json", build_fixtures(df, predictor))
    if accuracy:
        _write(tour, "accuracy.json", accuracy)
    _write(tour, "meta.json", build_meta(df, players, accuracy))
    _write(tour, "method.json", build_method(tour))
    print(f"  exported JSON for {tour} ({len(players)} players){'' if accuracy else ' [quick]'}")
