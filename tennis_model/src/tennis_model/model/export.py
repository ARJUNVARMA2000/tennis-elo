"""Build every JSON artifact the web frontend consumes, for one tour.

Kept separate from pipeline orchestration so the export surface is easy to scan:
  players.json          ranking board (Elo + surface + serve/return + style)
  matrix-index.json     surface/format shard map for pairwise component probabilities
  matrix-*.json         one prediction matrix context per file (powers /predict + live)
  ratings_history.json   monthly Elo trajectories (powers /trends)
  profile-index.json    light all-player profile/style summaries
  profile-*.json        one player's history, recent form, and H2H dossier
  draws.json            current-top-field tournament projections per surface
  tournaments.json      latest real events: title odds + actual result (powers home)
  event_coverage.json   independent begun-event set + exact shipped membership
  brackets.json         the actual ordered draw round-by-round, priced (powers /bracket)
  scenario-index.json   stable event IDs -> lazy exact scenario shards
  scenario-*.json       geometry, pairwise matrix, baseline and title leverage
  upcoming-index.json   compact home highlights + references to lazy upcoming shards
  upcoming-event-*.json compact scheduled rows grouped by stable event identity
  upcoming-evidence-*.json prediction evidence + forecast history loaded on demand
  fixtures.json         latest results with the model's pre-match call + upset flags
  accuracy.json         walk-forward metrics, calibration, per-surface breakdown
  meta.json             metadata + headline backtest
  method.json           effective production parameters (powers /method's detail sections)
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from .. import __version__
from ..config import MATCH_POPULATION_VERSION, SURFACES, output_dir
from ..data.bracket_rounds import (
    BracketRoundIndex,
    build_bracket_round_index,
    unique_bracket_round,
)
from ..data.charting import build_profiles, name_key
from ..data.rankings import load_rankings
from ..data.results import summary
from ..timing import timed
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


def _write(tour: str, name: str, data, *, compact: bool = False) -> None:
    out = output_dir(tour)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / name, "w", encoding="utf-8") as f:
        options = {"separators": (",", ":")} if compact else {"indent": 2}
        json.dump(_finite(data), f, ensure_ascii=False, **options)


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


def _rounded_finite(mapping: dict, key: str, digits: int = 3) -> float | None:
    """Round an optional numeric field from either pandas data or strict JSON.

    Full exports see NaN for missing charting values; quick exports reload the same
    summaries after JSON has correctly converted those values to null/None.
    """
    value = mapping.get(key)
    return round(float(value), digits) if isinstance(value, (int, float)) and math.isfinite(value) else None


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
            "aggression": _rounded_finite(st, "style_aggression"),
            "serveDom": _rounded_finite(st, "style_serve_dom"),
            **_live_rank_fields(name, rankings),
        })
    rows.sort(key=lambda r: -r["elo"])
    for i, r in enumerate(rows, 1):
        r["eloRank"] = i
    return rows[:top]


def build_matrix(predictor, players: list, tour: str) -> dict:
    """Legacy in-memory shape retained for callers; new exports use per-context shards."""
    names = [p["name"] for p in players[:TOP_MATRIX]]
    formats = [3, 5] if tour == "atp" else [3]
    surfaces = {}
    for surf in SURFACES:
        surfaces[surf] = {}
        for bo in formats:
            P = predictor.win_prob_matrix(names, surface=surf, best_of=bo)
            surfaces[surf][str(bo)] = np.round(P, 3).tolist()
    return {"players": names, "formats": formats, "surfaces": surfaces}


def build_matrix_shards(predictor, players: list, tour: str,
                        generation: str) -> tuple[dict, dict[str, dict]]:
    """Small index + one surface/format shard carrying all honest model components."""
    names = [p["name"] for p in players[:TOP_MATRIX]]
    formats = [3, 5] if tour == "atp" else [3]
    refs: dict[str, dict[str, str]] = {}
    shards: dict[str, dict] = {}
    for surf in SURFACES:
        refs[surf] = {}
        for bo in formats:
            filename = f"matrix-{surf.lower()}-bo{bo}.json"
            matrices = predictor.prediction_matrices(names, surface=surf, best_of=bo)
            evidence = (predictor.prediction_evidence_matrices(
                names, surface=surf, best_of=bo)
                if hasattr(predictor, "prediction_evidence_matrices") else None)
            shards[filename] = {
                "generation": generation,
                "players": names,
                "surface": surf,
                "bestOf": bo,
                "components": {
                    key: np.round(value, 3).tolist() for key, value in matrices.items()
                },
            }
            if evidence:
                upper = np.triu_indices(len(names), 1)
                shards[filename]["evidence"] = {
                    "schema": "evidence-v1",
                    "encoding": "upper-triangle-bps-v1",
                    "effects": {
                        # Signed integer basis points: the upper triangle implies the
                        # antisymmetric lower half and avoids making a lazy predictor
                        # shard carry seven redundant square float matrices.
                        key: np.rint(np.asarray(value)[upper] * 10_000).astype(int).tolist()
                        for key, value in evidence["effects"].items()
                    },
                    # Only conditional availability needs a matrix. Surface Elo,
                    # serve/return, form and rest exist for every rated pair; a generic
                    # predictor has no event, so home is explicitly unavailable.
                    "available": {
                        key: np.asarray(evidence["available"][key], dtype=np.uint8)[upper].tolist()
                        for key in ("h2h", "style")
                    },
                    "homeAvailable": False,
                }
            refs[surf][str(bo)] = filename
    return ({"generation": generation, "players": names, "formats": formats,
             "surfaces": refs}, shards)


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


def _profile_filename(name: str) -> str:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
    return f"profile-{digest}.json"


def build_profile_shards(profiles: dict, generation: str) -> tuple[dict, dict[str, dict]]:
    """A light all-player style index plus one dossier file per player."""
    summaries, shards = [], {}
    for name, profile in profiles.items():
        filename = _profile_filename(name)
        summaries.append({
            "name": name,
            "file": filename,
            "eloRank": profile.get("eloRank"),
            "servePct": profile.get("servePct"),
            "returnPct": profile.get("returnPct"),
            "eloHard": profile.get("eloHard"),
            "eloClay": profile.get("eloClay"),
            "eloGrass": profile.get("eloGrass"),
            "style": profile.get("style") or {},
        })
        shards[filename] = {
            "generation": generation,
            "name": name,
            "history": profile.get("history") or [],
            "recent": profile.get("recent") or [],
            "h2h": profile.get("h2h") or [],
        }
    return {"generation": generation, "profiles": summaries}, shards


def _write_shards(tour: str, prefix: str, shards: dict[str, dict]) -> None:
    out = output_dir(tour)
    expected = set(shards)
    for old in out.glob(f"{prefix}-*.json"):
        if old.name != f"{prefix}-index.json" and old.name not in expected:
            old.unlink()
    for filename, payload in shards.items():
        # Matrix shards are machine-read numeric arrays. Pretty-printing adds nearly a
        # megabyte of indentation per selected context without improving inspectability.
        _write(tour, filename, payload, compact=prefix == "matrix")


def _clear_upcoming_outputs(tour: str) -> None:
    """Prevent a failed refresh from laundering the previous schedule as current."""
    for path in output_dir(tour).glob("upcoming*.json"):
        path.unlink()


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


def build_fixtures(df, predictor, n=60, *, tour: str | None = None,
                   bracket_index: BracketRoundIndex | None = None) -> list:
    """Latest completed matches with the model's pre-match probability + upset flag."""
    if bracket_index is None:
        bracket_index = {}
    d = df[df["completed"]].sort_values("date").tail(400)
    out = []
    for r in d.tail(n).iloc[::-1].itertuples(index=False):
        # model prob the actual winner wins, from the combiner (recompute, leakage-free at ranking time)
        p = predictor.win_prob(r.winner_name, r.loser_name, surface=r.surface_b,
                               best_of=int(r.best_of) if pd.notna(r.best_of) else 3,
                               event=r.tourney_name)
        # Derive the flag from the ROUNDED prob we actually ship, not from full-precision
        # `p`: a winner priced .4996 rounds to .500, and a card reading "50.0%" next to an
        # UPSET badge is wrong on its face — and blocks the gate, which can only re-derive
        # the flag from the number in the file.
        mp = round(p, 3)
        event_id = getattr(r, "espn_id", None)
        bracket_round = unique_bracket_round(
            bracket_index, event_id, r.winner_name, r.loser_name)
        if bracket_round is not None and str(r.round) != bracket_round:
            print(f"  round-reconcile/{tour or 'fixtures'}: completed {event_id} "
                  f"{r.winner_name!r} vs {r.loser_name!r} {r.round}->{bracket_round}")
        out.append({
            "date": pd.Timestamp(r.date).strftime("%Y-%m-%d"),
            "event": r.tourney_name,
            "espnId": event_id,
            "surface": r.surface_b,
            "round": bracket_round if bracket_round is not None else r.round,
            "winner": r.winner_name, "loser": r.loser_name, "score": r.score,
            "modelProb": mp, "upset": bool(mp < 0.5),
        })
    return out


_ROUND_DEPTH = {r: i for i, r in enumerate(["R128", "R64", "R32", "R16", "QF", "SF", "F"])}


def _load_scenario_products(tour: str) -> tuple[dict | None, dict[str, dict]]:
    out = output_dir(tour)
    try:
        index = json.loads((out / "scenario-index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None, {}
    shards = {}
    for ref in index.get("events") or []:
        filename = ref.get("file")
        if not isinstance(filename, str):
            continue
        try:
            shards[filename] = json.loads((out / filename).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
    return index, shards


def build_upcoming(predictor, df, tour: str, *, enriched: list[dict] | None = None) -> list:
    """Scheduled / in-progress matches with the model's current win prob (schedule board).

    Sourced from the live feed's upcoming.csv through the shared enricher (model.upcoming) —
    the same primitive the forecast log uses, so a matchup is priced identically in both.
    Event names are de-sponsored like the home board; rows are ordered soonest-first, then
    by round depth within a day."""
    from ..sim.tournaments import _display_name, _known_names
    known = _known_names(df)
    if enriched is None:
        from .upcoming import enrich_upcoming, load_upcoming
        enriched = enrich_upcoming(predictor, df, load_upcoming(tour), tour)
    from ..eval.track import movement_for_upcoming, movement_key
    movements = movement_for_upcoming(tour, enriched)
    rows = [{
        "event": _display_name(r["event"], known, tour=tour, event_id=r.get("espnId")),
        "espnId": r.get("espnId"),
        "date": r["date"], "round": r["round"],
        "surface": r["surface"], "bestOf": r["best_of"], "level": r["level"],
        "playerA": r["playerA"], "playerB": r["playerB"], "pA": round(r["pA"], 4),
        "components": r.get("components"),
        "evidence": r.get("evidence"),
        "forecast": movements.get(movement_key(r)),
    } for r in enriched]
    rows.sort(key=lambda m: (m["date"], _ROUND_DEPTH.get(m["round"], 9), m["event"]))
    from .watch import rank_upcoming
    scenario_index, scenario_shards = _load_scenario_products(tour)
    return rank_upcoming(
        rows, predictor, tour,
        scenario_index=scenario_index, scenario_shards=scenario_shards,
    )


UPCOMING_SCHEMA = "upcoming-v2"
UPCOMING_EVENT_SCHEMA = "upcoming-event-v1"
UPCOMING_EVIDENCE_SCHEMA = "upcoming-evidence-v1"
_UPCOMING_DETAIL_KEYS = ("components", "evidence", "forecast")


def _upcoming_match_id(row: dict) -> str:
    from ..eval.track import match_identity
    return match_identity(row)


def _upcoming_event_token(rows: list[dict]) -> str:
    event_id = str(rows[0].get("espnId") or "").strip()
    if event_id:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "-", event_id).strip("-")
        if safe:
            return safe
    evidence = "|".join((
        str(rows[0].get("event") or ""),
        str(rows[0].get("date") or ""),
        str(rows[0].get("surface") or ""),
    ))
    return hashlib.sha256(evidence.encode()).hexdigest()[:12]


def _upcoming_base_row(row: dict, *, highlight: bool = False) -> dict:
    base = {key: value for key, value in row.items() if key not in _UPCOMING_DETAIL_KEYS}
    base["matchId"] = _upcoming_match_id(row)
    if highlight and isinstance(base.get("watch"), dict):
        base["watch"] = {"score": base["watch"].get("score")}
    return base


def build_upcoming_shards(rows: list[dict], generation: str) -> tuple[dict, dict[str, dict]]:
    """Split one decorated upcoming snapshot without changing its row semantics.

    The home index carries only the next three rows per event plus the five highest watch
    ranks. Full schedule rows live per event; the heavy components/evidence/timeline payload
    is keyed separately by the exact match identity and fetched only when requested.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        key = (str(row.get("espnId") or ""), str(row.get("event") or ""))
        groups.setdefault(key, []).append(row)

    refs = []
    shards: dict[str, dict] = {}
    highlight_ids: set[str] = set()
    for event_rows in groups.values():
        token = _upcoming_event_token(event_rows)
        event_file = f"upcoming-event-{token}.json"
        evidence_file = f"upcoming-evidence-{token}.json"
        base_rows = [_upcoming_base_row(row) for row in event_rows]
        details = [{
            "matchId": base["matchId"],
            **{key: row.get(key) for key in _UPCOMING_DETAIL_KEYS},
        } for row, base in zip(event_rows, base_rows)]
        event_meta = {
            "name": event_rows[0].get("event"),
            "espnId": event_rows[0].get("espnId"),
            "surface": event_rows[0].get("surface"),
            "level": event_rows[0].get("level"),
        }
        shards[event_file] = {
            "schema": UPCOMING_EVENT_SCHEMA,
            "generation": generation,
            "event": event_meta,
            "matches": base_rows,
        }
        shards[evidence_file] = {
            "schema": UPCOMING_EVIDENCE_SCHEMA,
            "generation": generation,
            "event": event_meta,
            "details": details,
        }
        refs.append({
            **event_meta,
            "count": len(event_rows),
            "file": event_file,
            "evidenceFile": evidence_file,
        })
        highlight_ids.update(base["matchId"] for base in base_rows[:3])

    watch = sorted(
        (row for row in rows if isinstance(row.get("watchRank"), int)),
        key=lambda row: row["watchRank"],
    )[:5]
    highlight_ids.update(_upcoming_match_id(row) for row in watch)
    highlights = [
        _upcoming_base_row(row, highlight=True)
        for row in rows if _upcoming_match_id(row) in highlight_ids
    ]
    index = {
        "schema": UPCOMING_SCHEMA,
        "schemaVersion": 2,
        "generation": generation,
        "count": len(rows),
        "events": refs,
        "highlights": highlights,
    }
    return index, shards


def export_forecast_products(tour: str, predictor, df, *,
                             enriched: list[dict] | None = None) -> None:
    """Refresh products whose source of truth is written after the main export.

    `log_and_grade` appends the current hourly observation and writes performance.json.
    Rebuilding these small artifacts afterward prevents the schedule from remaining one
    refresh behind and joins expectation detail into the already-lazy profile dossiers.
    """
    generation = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with timed(tour, "upcoming.decorate_and_shard"):
        upcoming = build_upcoming(predictor, df, tour, enriched=enriched)
        upcoming_index, upcoming_shards = build_upcoming_shards(upcoming, generation)
        _write(tour, "upcoming-index.json", upcoming_index)
        _write_shards(tour, "upcoming", upcoming_shards)
        legacy = output_dir(tour) / "upcoming.json"
        if legacy.exists():
            legacy.unlink()

    out = output_dir(tour)
    perf_path, index_path = out / "performance.json", out / "profile-index.json"
    if not perf_path.exists() or not index_path.exists():
        return
    try:
        performance = json.loads(perf_path.read_text(encoding="utf-8"))
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return
    by_name = {p.get("name"): p for p in performance.get("players") or [] if p.get("name")}
    for profile_summary in index.get("profiles") or []:
        perf = by_name.get(profile_summary.get("name"))
        profile_summary["performance"] = ({
            k: perf[k] for k in ("n", "wins", "expectedWins", "delta")
        } if perf else None)
        filename = profile_summary.get("file")
        if not isinstance(filename, str):
            continue
        path = out / filename
        try:
            detail = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        detail["performance"] = perf
        _write(tour, filename, detail)
    _write(tour, "profile-index.json", index)
    _write(tour, "performance.json", {
        **{k: performance.get(k) for k in ("tour", "lastUpdated", "window", "method")},
        "players": [
            {k: row.get(k) for k in ("name", "n", "wins", "expectedWins", "delta")}
            for row in performance.get("players") or []
        ],
    })


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


def build_meta(df, players, accuracy, trained_at: str | None = None,
               model_population_version: int | None = None,
               dual_state_threshold: int | None = None,
               dual_state_ready: bool = False) -> dict:
    """`lastUpdated` is when this JSON was written; `modelTrainedAt` is when the predictor
    behind it was trained. They diverge on every quick refresh — which republishes the
    saved pickle — so only the latter can reveal a daily retrain that has been failing.
    The model population version likewise comes from the pickle, never from current config."""
    s = summary(df)
    levels = (df["tourney_level"].astype("string").str.replace(r"\s+", "", regex=True)
              if "tourney_level" in df else pd.Series(dtype="string"))
    return {
        "tour": df["tour"].iloc[0] if "tour" in df else "atp",
        "lastUpdated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "modelTrainedAt": trained_at,
        "dataThrough": s["date_max"], "modelVersion": __version__,
        "matchPopulationVersion": MATCH_POPULATION_VERSION,
        # Unlike the data-policy version above, this comes from inside predictor.pkl.
        # Their equality proves cached rating state was walked over the rows now claimed.
        "modelPopulationVersion": model_population_version,
        # Predictor-derived, unlike method.json's config declaration.  Their health-gate
        # agreement proves a quick/full export actually carries the adopted secondary state.
        "dualStateThreshold": dual_state_threshold,
        "dualStateReady": bool(dual_state_ready),
        "matches": s["matches"], "players": s["players"], "activePlayers": len(players),
        # Audited by the pre-deploy gate. INCLUDE_WTA_125 is false; any non-zero value
        # means another ingestion path bypassed that adopted population policy.
        "wta125Matches": int(levels.eq("WTA125").sum()),
        "excludedWta125Matches": int(df.attrs.get("excluded_wta125_matches", 0)),
        "excludedUnclassifiedWtaLiveMatches": int(
            df.attrs.get("excluded_unclassified_wta_live_matches", 0)),
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
    hardcode these numbers in page copy (see the 2026-07-09 tasks/lessons/web.md entry). A
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
        WTA_DUAL_STATE_GATE_THRESHOLD,
        WTA_LOWER_STATE_FIRST_YEAR,
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
        "stateGate": {
            "enabled": bool(tour == "wta" and WTA_DUAL_STATE_GATE_THRESHOLD is not None),
            "minMainMatches": (WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None),
            "lowerStateFirstYear": (WTA_LOWER_STATE_FIRST_YEAR if tour == "wta" else None),
            "trainingPopulation": "main-only",
            "enrichedRows": ["qualifying", "wta125"] if tour == "wta" else [],
        },
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


def build_brackets_payload(tournaments: list) -> list:
    """Split each event's ordered bracket into its own payload and stamp ``hasBracket`` on
    the tournaments entry (mutates ``tournaments`` in place). Keeps tournaments.json small —
    the home page fetches it every visit — while /bracket loads brackets.json on demand.

    A tournaments entry has a bracket iff a released ordered draw exists. ``drawStatus ==
    "real"`` is overloaded (the ESPN-frontier path returns "real"
    with no ordered draw), so presence can't be inferred from it — ``hasBracket`` is explicit.
    """
    brackets = []
    for t in tournaments:
        rounds = t.pop("bracket", None)
        size = t.pop("bracketSize", None)
        source = t.pop("drawSource", None)
        source_id = t.pop("drawSourceId", None)
        source_url = t.pop("drawSourceUrl", None)
        source_start = t.pop("drawSourceStart", None)
        source_end = t.pop("drawSourceEnd", None)
        evidence_players = t.pop("drawEvidencePlayers", None)
        evidence_field_players = t.pop("drawEvidenceFieldPlayers", None)
        t["hasBracket"] = bool(rounds)
        if not rounds:
            continue
        brackets.append({
            "name": t.get("name"), "surface": t.get("surface"), "level": t.get("level"),
            "bestOf": t.get("bestOf"), "start": t.get("start"), "end": t.get("end"),
            "status": t.get("status"), "espnId": t.get("espnId"),
            "drawSize": t.get("drawSize"), "bracketSize": size,
            "champion": t.get("champion"), "runnerUp": t.get("runnerUp"),
            "drawSource": source, "drawSourceId": source_id, "drawSourceUrl": source_url,
            "drawSourceStart": source_start, "drawSourceEnd": source_end,
            "drawEvidencePlayers": evidence_players,
            "drawEvidenceFieldPlayers": evidence_field_players,
            "scenario": t.get("scenario"),
            "scenarioFile": t.pop("scenarioFile", None),  # pre-v1 compatibility
            "rounds": rounds,
        })
    return brackets


def build_scenario_shards(predictor, brackets: list, tournaments: list,
                          generation: str) -> tuple[dict, dict[str, dict]]:
    """Build lazy exact-scenario payloads for safely identified released draws.

    A missing stable event ID, unresolved placeholder, or unrated entrant withholds only
    that optional shard.  The factual bracket remains available; an interactive matrix is
    never guessed from a display name or a default-rated ghost.
    """
    import re

    from ..sim.bracket import is_real
    from ..sim.exact import (
        SCENARIO_SCHEMA,
        propagate_rounds,
        rounds_players,
        title_leverage,
    )
    from ..sim.scenarios import exact_bracket as legacy_exact_bracket

    model_generation = getattr(predictor, "trained_at", None)
    rated = set(getattr(predictor.elo, "overall", {}))
    by_id = {str(t.get("espnId")): t for t in tournaments if t.get("espnId")}
    refs = []
    shards: dict[str, dict] = {}
    for event in brackets:
        event_id = str(event.get("espnId") or "").strip()
        rounds = event.get("rounds") or event.get("bracket") or []
        players = rounds_players(rounds)
        if event.get("status") == "completed" or not event_id or not rounds or not players:
            continue
        if any(not is_real(player) or player not in rated for player in players):
            continue
        try:
            matrices = predictor.prediction_matrices(
                players,
                surface=event.get("surface") or "Hard",
                best_of=int(event.get("bestOf") or 3),
                event=event.get("name"),
            )
            # The rounded matrix is the public scenario contract. Propagate from those
            # exact values so Python exports, the browser runtime, and the integrity gate
            # cannot disagree at the sixth decimal after serialization.
            matrices = {
                key: np.round(np.asarray(value, dtype=float), 6)
                for key, value in matrices.items()
            }
            matrix = matrices["combiner"]
            baseline = propagate_rounds(
                rounds, players, matrix, event_id=event_id)
            leverage = title_leverage(
                rounds, players, matrix, event_id=event_id)
        except (KeyError, TypeError, ValueError):
            continue

        safe_id = re.sub(r"[^A-Za-z0-9._-]+", "-", event_id).strip("-")
        if not safe_id:
            continue
        filename = f"scenario-{safe_id}.json"
        geometry = []
        for round_index, round_row in enumerate(rounds):
            geometry.append({
                "round": round_row.get("round"),
                "matches": [
                    {
                        **match,
                        "id": f"{event_id}:r{round_index}:m{match_index}",
                        "settledWinner": (
                            match.get("a") if match.get("winner") == "a"
                            else match.get("b") if match.get("winner") == "b"
                            else None
                        ),
                    }
                    for match_index, match in enumerate(round_row.get("matches") or [])
                ],
            })
        shard = {
            "schema": SCENARIO_SCHEMA,
            "schemaVersion": 1,
            "generation": generation,
            "modelGeneration": model_generation,
            "event": {
                "espnId": event_id, "name": event.get("name"),
                "surface": event.get("surface"), "bestOf": event.get("bestOf"),
                "status": event.get("status"), "drawSize": event.get("drawSize"),
                "bracketSize": event.get("bracketSize"),
            },
            "players": players,
            "matrix": matrix.tolist(),
            # Compatibility fields consumed by the first forecast/scenario UI. The
            # stable v1 fields above/below are authoritative for new consumers.
            "matrices": {
                key: value.tolist()
                for key, value in matrices.items()
            },
            "rounds": rounds,
            "base": legacy_exact_bracket(
                rounds, players, matrix.tolist()),
            "geometry": geometry,
            "baseline": baseline,
            "titleLeverage": leverage,
        }
        shards[filename] = shard
        event["scenario"] = {
            "file": filename, "generation": generation,
            "modelGeneration": model_generation,
        }
        event["scenarioFile"] = filename
        refs.append({
            "espnId": event_id, "name": event.get("name"), "file": filename,
            "generation": generation, "modelGeneration": model_generation,
            "lockableMatches": len(baseline.get("lockableMatchIds") or []),
        })
        tournament = by_id.get(event_id)
        if tournament is not None:
            tournament["scenario"] = dict(event["scenario"])
    return ({"schema": SCENARIO_SCHEMA, "schemaVersion": 1,
             "generation": generation, "events": refs}, shards)


def build_event_outputs(predictor, df: pd.DataFrame, tour: str) -> tuple[dict, list]:
    """Build event artifacts from factual lifecycle evidence, not only model rows.

    The model dataframe intentionally excludes WTA 125 results, while the board must still
    know that those tournaments started or completed. Keep this split at one export seam so
    profiles, fixtures, metadata and every trained state continue to use ``df`` unchanged.
    """
    from ..data import event_coverage, results
    from ..sim import tournaments

    with timed(tour, "event_projection"):
        event_df = results.event_match_view(df, tour)
        coverage = event_coverage.build_event_coverage(event_df, tour)
        cards = tournaments.build_tournaments(predictor, event_df, tour)
        coverage = event_coverage.finalize_event_coverage(coverage, cards)
    return coverage, cards


def _static_outputs_present(tour: str) -> bool:
    out = output_dir(tour)
    required = ("matrix-index.json", "profile-index.json", "ratings_history.json",
                "draws.json", "method.json")
    if any(not (out / name).exists() for name in required):
        return False
    try:
        matrix = json.loads((out / "matrix-index.json").read_text())
        profiles = json.loads((out / "profile-index.json").read_text())
        refs = [f for byfmt in (matrix.get("surfaces") or {}).values()
                for f in (byfmt or {}).values()]
        refs += [p.get("file") for p in (profiles.get("profiles") or [])]
        return all(isinstance(name, str) and (out / name).exists() for name in refs)
    except (OSError, ValueError, TypeError):
        return False


def _cached_profile_styles(tour: str) -> dict:
    path = output_dir(tour) / "profile-index.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return {name_key(p.get("name")): p.get("style") or {}
            for p in payload.get("profiles") or [] if p.get("name")}


def export_all(tour, df, elo, srv, meta, predictor, oos=None, *, full: bool = True) -> None:
    """Write every frontend JSON for one tour.

    Works in two modes: a full run passes a fresh walk-forward `oos` (rebuilds
    accuracy.json); a quick refresh passes oos=None and reuses the saved predictor's
    states (elo/srv/meta) — accuracy.json is left to persist from the last full run.
    """
    _clear_upcoming_outputs(tour)
    static = full or not _static_outputs_present(tour)
    build_generation = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    mcp = build_profiles(tour) if static else _cached_profile_styles(tour)
    rankings = load_rankings(tour)
    players = build_players(elo, srv, meta, mcp, rankings, ctx=getattr(predictor, "ctx", None))
    if rankings:   # drift tripwire: a sudden drop in CI logs = source name-format change
        matched = sum(1 for p in players if p["liveRank"] is not None)
        print(f"  rankings/{tour}: matched {matched}/{len(players)} exported players")
    accuracy = build_accuracy(oos) if oos is not None else {}

    _write(tour, "players.json", players)
    if static:
        generation = getattr(predictor, "trained_at", None) or build_generation
        matrix_index, matrix_shards = build_matrix_shards(
            predictor, players, tour, generation)
        _write(tour, "matrix-index.json", matrix_index)
        _write_shards(tour, "matrix", matrix_shards)
        _write(tour, "ratings_history.json", build_history(elo, players))
        profiles = build_profiles_json(df, elo, srv, meta, mcp, players)
        profile_index, profile_shards = build_profile_shards(profiles, generation)
        _write(tour, "profile-index.json", profile_index)
        _write_shards(tour, "profile", profile_shards)
        _write(tour, "draws.json", build_draws(predictor, players, tour))
        for legacy in ("matrix.json", "profiles.json"):
            path = output_dir(tour) / legacy
            if path.exists():
                path.unlink()
    coverage, ts = build_event_outputs(predictor, df, tour)
    with timed(tour, "scenario_generation"):
        scenario_index, scenario_shards = build_scenario_shards(
            predictor, ts, ts, build_generation)
    _write(tour, "scenario-index.json", scenario_index)
    _write_shards(tour, "scenario", scenario_shards)
    brackets = build_brackets_payload(ts)   # pops bracket/size/url, stamps hasBracket
    _write(tour, "brackets.json", brackets)
    _write(tour, "tournaments.json", ts)
    _write(tour, "event_coverage.json", coverage)
    _write(tour, "fixtures.json", build_fixtures(
        df, predictor, tour=tour,
        bracket_index=build_bracket_round_index(brackets),
    ))
    if accuracy:
        _write(tour, "accuracy.json", accuracy)
    # Legacy attributes degrade to unknown rather than crashing. Quick mode normally rebuilds
    # an unknown population version first; the output gate independently rejects one.
    _write(tour, "meta.json", build_meta(
        df, players, accuracy,
        getattr(predictor, "trained_at", None),
        getattr(predictor, "_match_population_version", None),
        getattr(predictor, "_dual_state_threshold", None),
        getattr(predictor, "_has_lower_state", False),
    ))
    if static:
        _write(tour, "method.json", build_method(tour))
    print(f"  exported JSON for {tour} ({len(players)} players)"
          f"{' [full artifacts]' if static else ' [volatile only]'})")
