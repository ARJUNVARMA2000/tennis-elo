"""Project the model's title + round-by-round odds for the latest tournaments.

Recent matches are grouped into events (the fresh feed has no tourney_id, so we group
by name within a capture window wide enough to hold a two-week Slam). Each event is
Monte-Carlo'd over a bracket:

  - completed events  -> field = all participants, seeded by surface-blended Elo into a
    standard bracket; shows the model's pre-tournament title odds alongside the actual
    champion (did the favourite deliver?).
  - in-progress events -> field = players who haven't lost yet, seated by the ACTUAL
    remaining draw (the scheduled/in-progress matchups in upcoming.csv) so the round-by-
    round reach odds pair survivors by who really plays whom. Where the feed hasn't posted
    a full round yet, only the unknown downstream pairings fall back to rating seeding.

Completed events re-seed (rather than reconstruct the exact historical draw) because
pre-tournament title odds are dominated by field strength anyway; live events must honour
the real draw or the SF/F reach numbers are nonsense — two players who face each other in
the semis would otherwise both show >50% to reach the final.
"""

from __future__ import annotations

import difflib
import json

import pandas as pd

from ..config import live_dir
from ..data.results import _name_key
from ..data.surface import resolve_level, resolve_surface
from .draws import advance_slots, draw_status, live_draw, standard_seed_draw
from .simulate import simulate_tournament

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
    except Exception:  # noqa: BLE001 — missing/corrupt fields cache simply means no live field
        return {}


def _load_upcoming(tour: str) -> dict:
    """Scheduled/in-progress matchups {event: [(playerA, playerB), ...]} — the real
    current-round draw. Reshapes the shared upcoming.csv loader into per-event matchup
    pairs so the live projector pairs survivors by who actually plays whom, not by seeding."""
    from ..model.upcoming import load_upcoming
    out: dict = {}
    for r in load_upcoming(tour).itertuples(index=False):
        out.setdefault(str(r.tourney_name), []).append((str(r.playerA), str(r.playerB)))
    return out


def _load_wiki_draws(tour: str) -> dict:
    """Wikipedia ORDERED draws {event: {slots, seeds, bestOf, drawSize, start, end, ...}}
    written by data.draws_wiki.download_wiki_draws — the authoritative full bracket at
    release. Missing/corrupt file simply means no wiki draw is available (ESPN fallback)."""
    p = live_dir(tour) / "wiki_draws.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a missing/corrupt draw cache is a no-op, never fatal
        return {}


def _archive_attrs(df: pd.DataFrame, name: str) -> tuple:
    """(surface, tourney_level, best_of) for an event from PRIOR rows of the same
    tournament name (loose containment match) — lets a not-yet-started event inherit its
    real surface/tier/format from history. (None, None, None) if unseen in the archive."""
    if "tourney_name" not in df.columns:
        return None, None, None
    ek = str(name).lower()
    names = df["tourney_name"].astype(str)
    sub = df[names.str.lower().apply(lambda t: bool(t) and (t in ek or ek in t))]
    if sub.empty:
        return None, None, None
    surf = sub["surface_b"].mode() if "surface_b" in sub.columns else pd.Series([], dtype=object)
    bo = pd.to_numeric(sub["best_of"], errors="coerce").max() if "best_of" in sub.columns else None
    return (surf.iloc[0] if not surf.empty else None,
            _main_level_code(sub),
            int(bo) if pd.notna(bo) else None)


def _main_level_code(g: pd.DataFrame):
    """Modal tourney_level over MAIN-DRAW rows only. Qualifying rows (results.py stamps
    tourney_level='Q') can outnumber the main draw early in a Slam and would otherwise win the
    mode, mislabeling e.g. Wimbledon as 'Q'. Falls back to all rows when draw_level is absent
    (test frames) or has no main-draw rows; returns None when nothing is available."""
    if "tourney_level" not in g.columns:
        return None
    rows = g
    if "draw_level" in g.columns:
        main = g[g["draw_level"] == "main"]
        if not main.empty:
            rows = main
    m = rows["tourney_level"].mode()
    return m.iloc[0] if not m.empty else None


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
    return {"D": "Davis/BJK Cup", "O": "Olympics", "A": f"{t} Tour", "Q": f"{t} Tour"}.get(s, s)


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


def _norm_display(name: str) -> str:
    """Case/whitespace-insensitive event-name key. Mirrors data.health._norm_name so the
    producer collapses exactly the pairs the health gate would flag as a naming/dedup split."""
    return " ".join(str(name).split()).casefold()


def _dedup_by_display_name(entries: list, tour: str) -> list:
    """Keep one entry per display name. One real-world event can enter the list twice: the
    results feed carries it under its archive city name ('Bad Homburg') while the live/ESPN feed
    carries the SAME event under a sponsor title ('Bad Homburg Open powered by Solarwatt'), and
    _display_name collapses both to the same shown name. Shipping both is the naming/dedup split
    the health gate rejects (aliveCount/champion also disagree between the full record and the
    partial one). The fuller field is the more complete record of the event, so keep the larger
    drawSize; break ties toward a resolved level over the '<TOUR> Tour' fallback. A genuinely
    live event is carried by only one feed, so nothing collapses there."""
    fallback_level = f"{tour.upper()} Tour"

    def authority(t: dict) -> tuple:
        return (int(t.get("drawSize") or 0), t.get("level") != fallback_level)

    best: dict[str, dict] = {}
    for t in entries:
        key = _norm_display(t.get("name", ""))
        if key not in best or authority(t) > authority(best[key]):
            best[key] = t            # reassigning an existing key keeps its first-seen position
    return list(best.values())


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


def _simulate_projection(predictor, slots: list, surface: str, best_of: int,
                         name: str, n_sims: int, seed: int) -> tuple[list, str | None]:
    """Simulate a bracket -> (projection rows, model favourite). The odds-formatting shared
    by the live/completed and the pre-start (Wikipedia) paths, so it lives in one place."""
    sim = simulate_tournament(predictor, slots, surface=surface, best_of=best_of,
                              n_sims=n_sims, seed=seed, event=name)
    cols = set(sim.columns)
    proj = [{
        "name": r.player,
        "champion": round(float(r.Champion), 4),
        "final": round(float(r.F), 4) if "F" in cols else None,
        "sf": round(float(r.SF), 4) if "SF" in cols else None,
        # per-round reach odds (entry -> title) for the round-by-round forecast table
        "reach": {c: round(float(getattr(r, c)), 4) for c in ROUND_COLS if c in cols},
    } for r in sim.head(TOP_PROJECTION).itertuples(index=False)]
    return proj, (proj[0]["name"] if proj else None)


def _reconcile_wiki_names(slots: list, pool: list, resolve) -> dict:
    """Map Wikipedia draw slot names to the model-canonical identity, bridging the few
    spellings the accent/punct key can't — a transliteration (Alexander/Aleksandr Shevchenko),
    an extra given name (Daniel/Adolfo Daniel Vallejo), or CJK name order (Kwon Soon-woo /
    SoonWoo Kwon) — by matching the leftover against this event's OWN participant pool (the
    ESPN field + results names, which already resolve cleanly). Without it, a player who has
    really lost keeps a different identity from their ``eliminated`` entry and lingers "alive",
    freezing ``advance_slots`` at a stale early round while the true SF is already known.

    Returns ``{raw_slot_name: canonical}``. Safe by construction: exact-key hits map as before;
    only the residue that misses is matched, one-to-one, and only to a pool name that shares a
    name token (a surname), greedily by token overlap then string similarity. An unmatched slot
    is left to the caller's plain ``resolve()`` — never worse than before."""
    def toks(n: str) -> set:
        return set(_name_key(n).split())

    pool = [p for p in dict.fromkeys(pool) if isinstance(p, str) and p]
    pool_keys = {_name_key(resolve(p)) for p in pool}
    canon: dict = {}
    wiki_left: list = []
    for s in dict.fromkeys(x for x in slots if x):
        if _name_key(resolve(s)) in pool_keys:
            canon[s] = resolve(s)
        else:
            wiki_left.append(s)
    if not wiki_left:
        return canon
    matched = {_name_key(resolve(s)) for s in canon}
    pool_left = [p for p in pool if _name_key(resolve(p)) not in matched]
    pairs = []
    for s in wiki_left:
        for p in pool_left:
            shared = len(toks(s) & toks(p))
            if shared:                       # a shared token (surname) is the anchor
                ratio = difflib.SequenceMatcher(None, _name_key(s), _name_key(p)).ratio()
                pairs.append((shared, ratio, s, p))
    pairs.sort(key=lambda t: (t[0], t[1]), reverse=True)
    used_s: set = set()
    used_p: set = set()
    for _shared, _ratio, s, p in pairs:
        if s in used_s or p in used_p:
            continue
        canon[s] = resolve(p)
        used_s.add(s)
        used_p.add(p)
    return canon


def project_tournament(predictor, name: str, g: pd.DataFrame, tour: str,
                       known: set | None = None, top_set: set | None = None,
                       espn_fields: dict | None = None, resolve=None,
                       matchups: list | None = None, wiki_draw: dict | None = None,
                       n_sims: int = 8000, seed: int = 11) -> dict | None:
    # The ratings frame can include qualifying matches for state updates. Tournament
    # projections, however, describe the main draw only. ``draw_level`` filters modern lower-
    # ingestion rows, while the round filter also catches legacy/source rows whose Q1/Q2
    # matches were default-labelled "main". Once a Slam final appears, neither class may leak
    # into a >128-player completed field and pad it to an impossible 256-slot bracket.
    main = g
    if "draw_level" in g.columns:
        main_rows = g[g["draw_level"] == "main"]
        if not main_rows.empty:
            main = main_rows
    knockout = main[main["round"].isin(_KO_ROUNDS)]
    if not knockout.empty:
        main = knockout

    surface = main["surface_b"].mode().iloc[0]
    bo = pd.to_numeric(main["best_of"], errors="coerce").max()
    best_of = int(bo) if pd.notna(bo) else 3
    level = resolve_level(tour, name, archive_level=_level_label(_main_level_code(g), tour))

    eliminated = set(main["loser_name"])
    final_rows = main[main["round"] == "F"]
    completed = len(final_rows) > 0

    champ = runner = None
    if completed:
        fr = final_rows.sort_values("date").iloc[-1]
        champ, runner = fr["winner_name"], fr["loser_name"]
        field_pool = set(main["winner_name"]) | set(main["loser_name"])  # full main draw
    else:
        # Live: prefer ESPN's FULL main-draw field (incl. scheduled) so the Day-1
        # favourite reflects everyone still in the draw, not just those who've finished.
        ef = (espn_fields or {}).get(name)
        if ef and resolve and len(ef["field"]) >= 8:
            field_pool = {resolve(n) for n in ef["field"]}
            eliminated = {resolve(n) for n in ef["eliminated"]} | eliminated
        else:
            field_pool = set(g["winner_name"]) | set(g["loser_name"])

    # A released Wikipedia draw is the authoritative ORDERED bracket: it fixes the real
    # entrants (and the event's best-of — Tennis5 for slams) so the live board runs on the
    # actual draw, not a rating seed. Byes/qualifiers ride along in `slots` (None / distinct).
    resolved_wslots = None
    if wiki_draw and not completed and wiki_draw.get("slots") and resolve:
        # The wiki draw and ESPN's field/results name the SAME players in different spellings;
        # reconcile the residue the key can't bridge against this event's own field so an
        # eliminated player can't linger "alive" and freeze the fold at a stale early round.
        pool = list((ef or {}).get("field", [])) + list(g["loser_name"]) + list(g["winner_name"])
        wcanon = _reconcile_wiki_names(wiki_draw["slots"], pool, resolve)
        resolved_wslots = [(wcanon.get(s) or resolve(s)) if s else None for s in wiki_draw["slots"]]
        field_pool = {s for s in resolved_wslots if s is not None}
        best_of = int(wiki_draw.get("bestOf") or best_of)

    if len(field_pool) < 8:              # dedup-leftover fragment, not a real draw
        return None
    if top_set is not None and wiki_draw is None and len(field_pool & top_set) < 2:
        return None                      # sub-tour / ITF event; a wiki draw IS tour-level

    alive = field_pool - eliminated
    field = list(field_pool if completed else alive)
    if len(field) < 2:
        return None

    rank = lambda p: predictor.elo.blended(p, surface)
    if completed:              # retrospective: pre-tournament title odds over the full field
        slots = standard_seed_draw(sorted(field, key=rank, reverse=True))
        draw_state = "final"
    elif resolved_wslots is not None:    # live on the REAL ordered draw (exact all rounds)
        slots = advance_slots(resolved_wslots, eliminated)
        draw_state = "real"
    else:                      # live from ESPN's partial matchups (seed the unknown frontier)
        mus = matchups or []
        slots = live_draw(field, mus, rank)
        draw_state = draw_status(field, mus, rank)
    proj, favorite = _simulate_projection(predictor, slots, surface, best_of, name, n_sims, seed)

    return {
        "name": _display_name(name, known or set()), "surface": surface, "level": level, "bestOf": best_of,
        "start": str(g["date"].min().date()), "end": str(g["date"].max().date()),
        "status": "completed" if completed else "live", "drawStatus": draw_state,
        "drawSize": len(field_pool), "aliveCount": len(alive),
        "champion": champ, "runnerUp": runner,
        "modelFavorite": favorite,
        "favoritePicked": bool(completed and favorite == champ),
        "projection": proj,
    }


def project_upcoming(predictor, name: str, wd: dict, tour: str, df: pd.DataFrame,
                     known: set | None, resolve, n_sims: int = 8000, seed: int = 11) -> dict | None:
    """Pre-start projection for an event whose Wikipedia draw is out but which hasn't
    played a match yet (so it's absent from the results-driven event list). The full real
    bracket, no eliminations -> honest 'real' pre-tournament title odds from release."""
    wslots = [resolve(s) if s else None for s in (wd.get("slots") or [])]
    field_pool = {s for s in wslots if s is not None}
    if len(field_pool) < 8:
        return None
    surface, _lvl, bo = _archive_attrs(df, name)
    surface = resolve_surface(tour, name, wd.get("start") or "", archive_surface=surface)
    best_of = int(wd.get("bestOf") or bo or 3)
    level = resolve_level(tour, name)
    slots = advance_slots(wslots, set())
    proj, favorite = _simulate_projection(predictor, slots, surface, best_of, name, n_sims, seed)
    return {
        "name": _display_name(name, known or set()), "surface": surface, "level": level, "bestOf": best_of,
        "start": str(wd.get("start") or ""), "end": str(wd.get("end") or wd.get("start") or ""),
        "status": "upcoming", "drawStatus": "real",
        "drawSize": len(field_pool), "aliveCount": len(field_pool),
        "champion": None, "runnerUp": None,
        "modelFavorite": favorite, "favoritePicked": False,
        "projection": proj,
    }


_STATUS_ORDER = {"live": 0, "upcoming": 1, "completed": 2}


def build_tournaments(predictor, df: pd.DataFrame, tour: str, **kw) -> list:
    known = _known_names(df)
    top_set = set(sorted(predictor.elo.overall, key=predictor.elo.elo, reverse=True)[:100])
    espn_fields = _load_fields(tour)
    upcoming = _load_upcoming(tour)
    wiki = _load_wiki_draws(tour)
    # map ESPN player names onto the predictor's canonical spellings (accent/punct-insensitive)
    canon: dict = {}
    for k in predictor.elo.overall:
        canon.setdefault(_name_key(k), k)
    resolve = lambda n: canon.get(_name_key(n), n)
    out = []
    for name, g in recent_tournaments(df):
        matchups = [(resolve(a), resolve(b)) for a, b in upcoming.get(name, [])]
        t = project_tournament(predictor, name, g, tour, known=known, top_set=top_set,
                               espn_fields=espn_fields, resolve=resolve, matchups=matchups,
                               wiki_draw=wiki.get(name), **kw)
        if t:
            out.append(t)
    # Pre-start events: the Wikipedia draw is out but no match has been played yet, so the
    # results-driven list above hasn't surfaced them. Project the real bracket now — but
    # only for events that are actually upcoming: dedup by DISPLAY name (a completed event's
    # results-feed name differs from ESPN's sponsor name) and skip anything already over.
    seen = {t["name"] for t in out}
    dmax = df["date"].max() if not df.empty else None
    for name, wd in wiki.items():
        if _display_name(name, known) in seen or not wd.get("slots"):
            continue
        end = pd.to_datetime(wd.get("end") or wd.get("start"), errors="coerce")
        if dmax is not None and pd.notna(end) and end < dmax - pd.Timedelta(days=2):
            continue                         # already finished (its card is a completed one)
        t = project_upcoming(predictor, name, wd, tour, df, known, resolve, **kw)
        if t:
            out.append(t)
    # The results loop groups by RAW tourney_name, so an event whose live/ESPN feed uses a
    # sponsor title ('Bad Homburg Open powered by Solarwatt') and whose archive uses the city
    # ('Bad Homburg') enters twice, both collapsing to one display name. Keep one per name.
    out = _dedup_by_display_name(out, tour)
    # Live, then upcoming, then completed; within each group, most recent first.
    out.sort(key=lambda t: t["end"], reverse=True)
    out.sort(key=lambda t: _STATUS_ORDER.get(t["status"], 3))
    return out
