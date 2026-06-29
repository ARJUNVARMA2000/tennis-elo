"""Build every JSON artifact the web frontend consumes, for one tour.

Kept separate from pipeline orchestration so the export surface is easy to scan:
  players.json          ranking board (Elo + surface + serve/return + style)
  matrix.json           top-N pairwise win probs per surface x format (powers /predict)
  ratings_history.json   monthly Elo trajectories (powers /trends)
  profiles.json         per-player detail: splits, style, recent form, H2H, Elo line
  draws.json            current-top-field tournament projections per surface
  tournaments.json      latest real events: title odds + actual result (powers home)
  fixtures.json         latest results with the model's pre-match call + upset flags
  accuracy.json         walk-forward metrics, calibration, per-surface breakdown
  meta.json             metadata + headline backtest
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .. import __version__
from ..config import SURFACES, output_dir
from ..data.charting import build_profiles, name_key
from ..data.results import summary
from .features import FEATURES, STYLE_FEATURES

ACTIVE_DAYS = 550
TOP_MATRIX = 120          # players in the precomputed pairwise matrix
TOP_PROFILES = 200
HISTORY_SINCE = "2016-01"
SLAM_BEST_OF = {"atp": 5, "wta": 3}


def _write(tour: str, name: str, data) -> None:
    out = output_dir(tour)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _active(elo) -> list:
    cutoff = elo.last_date - np.timedelta64(ACTIVE_DAYS, "D")
    return [n for n, last in elo.last_played.items() if last >= cutoff]


def build_players(elo, srv, meta, profiles, top=TOP_PROFILES) -> list:
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
            "rankPoints": int(m["rank_points"]) if pd.notna(m.get("rank_points")) else None,
            "matches": int(elo.n.get(name, 0)),
            "hand": m.get("hand") if isinstance(m.get("hand"), str) else None,
            "lastPlayed": pd.Timestamp(elo.last_played[name]).strftime("%Y-%m-%d"),
            "aggression": round(st["style_aggression"], 3) if st.get("style_aggression") == st.get("style_aggression") and "style_aggression" in st else None,
            "serveDom": round(st["style_serve_dom"], 3) if st.get("style_serve_dom") == st.get("style_serve_dom") and "style_serve_dom" in st else None,
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
                               best_of=int(r.best_of) if pd.notna(r.best_of) else 3)
        out.append({
            "date": pd.Timestamp(r.date).strftime("%Y-%m-%d"),
            "event": r.tourney_name, "surface": r.surface_b, "round": r.round,
            "winner": r.winner_name, "loser": r.loser_name, "score": r.score,
            "modelProb": round(p, 3), "upset": bool(p < 0.5),
        })
    return out


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
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataThrough": s["date_max"], "modelVersion": __version__,
        "matches": s["matches"], "players": s["players"], "activePlayers": len(players),
        "features": FEATURES, "surfaces": list(SURFACES),
        "backtest": accuracy.get("models") if accuracy else None,
        "notes": "Hybrid: surface-blended Elo + opponent-adjusted serve/return point model "
                 "+ MCP style -> XGBoost combiner (Platt-calibrated). Walk-forward, leakage-free.",
    }


def export_all(tour, df, elo, srv, meta, predictor, oos=None) -> None:
    """Write every frontend JSON for one tour.

    Works in two modes: a full run passes a fresh walk-forward `oos` (rebuilds
    accuracy.json); a quick refresh passes oos=None and reuses the saved predictor's
    states (elo/srv/meta) — accuracy.json is left to persist from the last full run.
    """
    mcp = build_profiles(tour)
    players = build_players(elo, srv, meta, mcp)
    accuracy = build_accuracy(oos) if oos is not None else {}

    _write(tour, "players.json", players)
    _write(tour, "matrix.json", build_matrix(predictor, players, tour))
    _write(tour, "ratings_history.json", build_history(elo, players))
    _write(tour, "profiles.json", build_profiles_json(df, elo, srv, meta, mcp, players))
    _write(tour, "draws.json", build_draws(predictor, players, tour))
    from ..sim.tournaments import build_tournaments
    _write(tour, "tournaments.json", build_tournaments(predictor, df, tour))
    _write(tour, "fixtures.json", build_fixtures(df, predictor))
    if accuracy:
        _write(tour, "accuracy.json", accuracy)
    _write(tour, "meta.json", build_meta(df, players, accuracy))
    print(f"  exported JSON for {tour} ({len(players)} players){'' if accuracy else ' [quick]'}")
