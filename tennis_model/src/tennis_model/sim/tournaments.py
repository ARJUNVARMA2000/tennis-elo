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

from ..config import EVENT_CALENDAR_COMPLETE_GRACE_DAYS, live_dir
from ..data.event_coverage import cached_draw_identity_aliases
from ..data.events import EventResolver, display_event_name, is_event_id, load_registry
from ..data.results import _name_key
from ..data.surface import resolve_level, resolve_surface_info
from .bracket import bracket_is_meaningful, bracket_rounds, is_real, oriented_logged, price_bracket
from .draws import advance_slots, draw_status, live_draw, standard_seed_draw
from .simulate import simulate_tournament

_KO_ROUNDS = {"R128", "R64", "R32", "R16", "QF", "SF", "F"}
ROUND_COLS = ["R128", "R64", "R32", "R16", "QF", "SF", "F", "Champion"]  # reach-prob columns, entry -> title
TOP_PROJECTION = 24          # players kept in each event's odds list
KNOWN_DRAW_SIZE = {"Grand Slam": 128}


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
    """Scheduled/in-progress matchups, keyed BOTH ways: ``{event_name_or_id: [(a, b), ...]}``.

    Reshapes the shared upcoming.csv loader into per-event matchup pairs so the live
    projector pairs survivors by who actually plays whom, not by seeding. Rows carrying an
    ``espn_id`` are indexed under it as well as under their display name, so a lookup
    succeeds whichever identity the caller resolved."""
    from ..model.upcoming import load_upcoming
    out: dict = {}
    for r in load_upcoming(tour).itertuples(index=False):
        pair = (str(r.playerA), str(r.playerB))
        out.setdefault(str(r.tourney_name), []).append(pair)
        eid = getattr(r, "espn_id", None)
        if eid is not None and str(eid) != "nan" and str(eid):
            out.setdefault(str(eid), []).append(pair)
    return out


def _split_by_key(mapping: dict) -> tuple[dict, dict]:
    """Split a cache into ``(by_id, by_name)``, classifying EVERY key independently.

    Both formats coexist during the migration — a cache written before the re-key is
    name-keyed, one written after is id-keyed, and a tour whose downloader soft-failed can
    leave the two files in different shapes. Per-file assumptions break on exactly that.
    An entry that is name-keyed but carries an ``espnId`` inside is indexed under BOTH, which
    is what lets a draw cached under yesterday's sponsor title still be found today."""
    by_id: dict = {}
    by_name: dict = {}
    for k, v in (mapping or {}).items():
        if is_event_id(k):
            by_id[str(k)] = v
        else:
            by_name[str(k)] = v
            eid = v.get("espnId") if isinstance(v, dict) else None
            if eid:
                by_id.setdefault(str(eid), v)
    return by_id, by_name


def _lookup(by_id: dict, by_name: dict, eid: str | None, name: str):
    """Cache entry for an event, preferring its stable id over its display name."""
    if eid and eid in by_id:
        return by_id[eid]
    return by_name.get(str(name))


# Inclusive date spans: zero means the two records share one observed match day. A transient
# provider fragment can last only that day; the shared-player + exact-match requirements below
# carry the identity proof, while disjoint and merely adjacent spans remain ineligible.
COALESCE_MIN_OVERLAP_DAYS = 0
COALESCE_MIN_SHARED_PLAYERS = 3
COALESCE_MIN_SHARED_PAIRS = 1


def _main_draw_ko_rows(g: pd.DataFrame) -> pd.DataFrame:
    """Rows eligible to prove event identity or populate a tournament card."""
    if "winner_name" not in g.columns:
        return g.iloc[0:0]
    main = g
    if "draw_level" in g.columns:
        rows = g[g["draw_level"] == "main"]
        main = rows if not rows.empty else g
    if "round" in main.columns:
        ko = main[main["round"].isin(_KO_ROUNDS)]
        main = ko if not ko.empty else main
    return main


def _real_players(g: pd.DataFrame) -> set:
    """This group's real MAIN-DRAW participants — the only names that are identity evidence.

    Two filters, both load-bearing. Placeholders are numbered per draw, so two concurrent
    events "share" every Qualifier N and none of them means anything (issue #9). And
    QUALIFYING rows are excluded: a player who loses qualifying at one event and plays the
    main draw at another the same week appears in both, so counting them could manufacture
    three "shared players" between a Challenger and a main-tour event in the same city — and
    merging two genuinely different tournaments corrupts a projection, not just a label."""
    main = _main_draw_ko_rows(g)
    if main.empty:
        return set()
    return {n for n in set(main["winner_name"]) | set(main["loser_name"]) if is_real(n)}


def _real_match_pairs(g: pd.DataFrame) -> set[tuple[str, str]]:
    """Canonical unordered matchups from exactly the rows :func:`_real_players` trusts."""
    main = _main_draw_ko_rows(g)
    if main.empty or not {"winner_name", "loser_name"} <= set(main.columns):
        return set()
    return {
        tuple(sorted((_name_key(winner), _name_key(loser))))
        for winner, loser in zip(main["winner_name"], main["loser_name"])
        if is_real(winner) and is_real(loser)
    }


def _one_match_per_player_round(main: pd.DataFrame) -> pd.DataFrame:
    """Keep the first source-ordered match involving each player in each knockout round.

    A single-elimination player cannot play twice in one round. Duplicate source rows can
    spell one side differently, but the unchanged opponent still proves the duplication.
    The Olympic bronze-medal match is safe: feeds may label both medal matches ``F``, but
    their four players are distinct, so both survive this rule.
    """
    required = {"round", "winner_name", "loser_name"}
    if main.empty or not required <= set(main.columns):
        return main
    seen: dict[str, set[str]] = {}
    keep: list[bool] = []
    for round_name, winner, loser in zip(
            main["round"], main["winner_name"], main["loser_name"]):
        players = {_name_key(winner), _name_key(loser)} - {""}
        used = seen.setdefault(str(round_name), set())
        duplicate = bool(players & used)
        keep.append(not duplicate)
        if not duplicate:
            used.update(players)
    return main.loc[keep]


def _spans_overlap_days(a: pd.DataFrame, b: pd.DataFrame) -> int:
    lo = max(a["date"].min(), b["date"].min())
    hi = min(a["date"].max(), b["date"].max())
    return (hi - lo).days if pd.notna(lo) and pd.notna(hi) and hi >= lo else -1


def _coalesce_groups(events: list, resolver) -> list:
    """Fold the groups that are the SAME tournament into one, before anything is projected.

    `recent_tournaments` groups by raw `tourney_name`, so one real event enters twice
    whenever its sources disagree about the title: the results feed carries the archive city
    ("Bad Homburg") while ESPN carries the sponsor version ("Bad Homburg Open powered by
    Solarwatt"). On 2026-07-09 that shipped TWO WTA cards for one tournament, the second a
    nine-player fragment with champion and runner-up swapped. Deduping the CARDS afterwards
    only ever hid it — one of the two projections was still built on half an event.

    Two ways in. Groups resolving to the same espnId are the same event by definition. An
    id-less group joins one on evidence instead: a real date overlap, shared real players,
    AND at least one shared main-draw matchup. A shared week is insufficient: Wimbledon and
    Nordea overlap on the calendar and share entrants who play both in succession. This is
    deliberately the same shared-pair rule used by event coverage; no string rule is involved,
    which is the point: "Bastad" and "Nordea Open" share no substring at all.

    Ambiguity never merges. An id-less group matching two id-bearing ones is left alone,
    because a wrong merge corrupts a projection rather than merely mislabelling a card."""
    resolved = [(name, g, _group_event_id(g, name, resolver)) for name, g in events]
    by_id: dict = {}
    idless: list = []
    for name, g, eid in resolved:
        (by_id.setdefault(eid, []).append((name, g)) if eid else idless.append((name, g)))

    # Snapshot the ID-BEARING keys before folding anything in. Searching `by_id` live would
    # let an id-less group match a synthetic entry added by an EARLIER id-less group, quietly
    # merging two unidentified events in an order-dependent way — not what this claims to do.
    id_keys = list(by_id)
    for i, (name, g) in enumerate(idless):
        players = _real_players(g)
        pairs = _real_match_pairs(g)
        hits = [eid for eid in id_keys
                if any(_spans_overlap_days(g, mg) >= COALESCE_MIN_OVERLAP_DAYS
                       and len(players & _real_players(mg)) >= COALESCE_MIN_SHARED_PLAYERS
                       and len(pairs & _real_match_pairs(mg)) >= COALESCE_MIN_SHARED_PAIRS
                       for _n, mg in by_id[eid])]
        if len(hits) == 1:
            by_id[hits[0]].append((name, g))
        else:
            # Its own event. The key carries the index as well as the name: two id-less groups
            # whose names merely NORMALISE alike ("Bad Homburg" / "Bad  Homburg" from different
            # feeds) would otherwise collide and one would vanish from the board entirely.
            by_id[f"__name__{i}__{_norm_display(name)}"] = [(name, g)]

    out = []
    for key, members in by_id.items():
        if len(members) == 1:
            (name, g), = members
            out.append((name, g, None if key.startswith("__name__") else key))
            continue
        # One event, several partial records: concatenate, then take the name of the FULLEST
        # member — the more complete record is the better basis for archive-name lookups.
        frames = [g for _n, g in members]
        best = max(members, key=lambda m: len(m[1]))[0]
        merged = pd.concat(frames, ignore_index=True)
        if {"winner_name", "loser_name", "round"} <= set(merged.columns):
            merged = merged.drop_duplicates(subset=["winner_name", "loser_name", "round"])
        out.append((best, merged, None if key.startswith("__name__") else key))
    return out


def _scheduled_end(eid: str | None, name: str, resolver,
                   draws_by_id: dict, draws_by_name: dict) -> str | None:
    """The event's SCHEDULED end date, from the registry or its cached draw.

    Distinct from the card's `end`, which is just the last match actually recorded — the very
    thing that is missing when a final never arrives. Only a source that knows the calendar
    can say an event is over."""
    entry = (resolver.entry(eid) if (resolver and eid) else None) or {}
    end = entry.get("end")
    if end:
        return str(end)
    draw = _lookup(draws_by_id, draws_by_name, eid, name) or {}
    return str(draw.get("end") or "") or None


def _fields_view(by_id: dict, by_name: dict, eid: str | None, name: str) -> dict | None:
    """A one-entry ``{name: field}`` view of whatever the ID resolved to.

    `project_tournament` does its own ``.get(name)`` on this dict; handing it a view keyed by
    the name it will ask for lets the RESOLUTION move to ids without touching that function's
    signature — or the tests that call it with a plain dict."""
    hit = _lookup(by_id, by_name, eid, name)
    return {str(name): hit} if hit else None


def _group_event_id(g: pd.DataFrame, name: str, resolver) -> str | None:
    """This event's ESPN id: the modal non-null ``espn_id`` on its rows, else name lookup.

    Modal rather than "the id on any row" because the merge prefers stat-bearing archive
    rows, which predate the id entirely — the surviving row for a match often has none."""
    if "espn_id" in g.columns:
        ids = g["espn_id"].dropna()
        ids = ids[ids.astype(str).str.strip().ne("")]
        if not ids.empty:
            m = ids.astype(str).mode()
            if not m.empty:
                return m.iloc[0]
    return resolver.id_of(name) if resolver else None


def _load_tournament_draws(tour: str) -> dict:
    """Complete ordered draws with source-neutral provenance; ESPN is the partial fallback."""
    from ..data.draws import load_tournament_draws
    return load_tournament_draws(tour)


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
    surf, _src = _known_surface(sub)
    bo = pd.to_numeric(sub["best_of"], errors="coerce").max() if "best_of" in sub.columns else None
    return (surf,
            _main_level_code(sub),
            int(bo) if pd.notna(bo) else None)


def _known_surface(rows: pd.DataFrame) -> tuple[str | None, str | None]:
    """``(surface, source)`` over rows whose surface is KNOWN — never a month-of-year guess.

    `results.clean` stamps `surface_src`; a "month" row carries a season guess, not a fact.
    Returning one here would hand it back to `resolve_surface_info` as the authoritative
    archive value, short-circuiting the Wikipedia tier that actually knows the answer. The
    row's OWN source is carried out rather than relabelled "archive": `surfaceSource` decides
    whether a wrong surface blocks the deploy, so it has to say where the value really came
    from. Frames without the column (unit-test fixtures) keep the old behaviour."""
    if "surface_b" not in rows.columns:
        return None, None
    known = rows[rows["surface_src"] != "month"] if "surface_src" in rows.columns else rows
    m = known["surface_b"].mode()
    if m.empty:
        return None, None
    val = m.iloc[0]
    if "surface_src" not in known.columns:
        return val, "archive"
    s = known.loc[known["surface_b"] == val, "surface_src"].mode()
    return val, (s.iloc[0] if not s.empty else "archive")


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
    if df is None or not {"tourney_level", "tourney_name"} <= set(df.columns):
        return set()
    return set(df.loc[df["tourney_level"].notna(), "tourney_name"].dropna().astype(str).unique())


def _display_name(name: str, known: set, *, tour: str = "", event_id: str | None = None,
                  identity_names: set | None = None) -> str:
    """Prefer a familiar archive/city label over an ESPN sponsor title.

    Stable identity evidence can connect unrelated strings; otherwise the conservative
    containment cleanup still handles titles such as 'Lexus Eastbourne Open'.
    """
    return display_event_name(
        tour, name, event_id, identity_names=identity_names or (), known_names=known)


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
                       recent_days: int = 18, max_events: int | None = None) -> list:
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
    kept = events if max_events is None else events[:max_events]
    return [(n, g) for n, g, _ in kept]


def projection_is_meaningful(field_pool) -> bool:
    """Whether title odds over this field describe players, or mostly placeholders.

    Deliberately the SAME majority rule as `sim.bracket.bracket_is_meaningful`, on the same
    `is_real` predicate: a card whose bracket is withheld as noise must not still publish
    odds computed from that noise. Unresolved `Qualifier N` slots are unknown to the rating
    pool, so each one enters the simulation at DEFAULT_RATING — on 2026-07-27 the DC Open
    shipped 22 of 24 projected "players" as qualifiers and inflated the real favourite to
    53-56% against a field of ghosts."""
    field = list(field_pool or [])
    if not field:
        return False
    return sum(1 for x in field if is_real(x)) * 2 >= len(field)


def _simulate_projection(predictor, slots: list, surface: str, best_of: int,
                         name: str, n_sims: int, seed: int) -> tuple[list, str | None]:
    """Simulate a bracket -> (projection rows, model favourite). The odds-formatting shared
    by the live/completed and pre-start complete-draw paths, so it lives in one place.

    Placeholder entrants stay IN the simulation — they occupy real draw slots and a real
    player's path genuinely runs through them — but are never PUBLISHED as rows: a
    "Qualifier 13" line with title odds is not a fact about anybody. Odds are not
    renormalised over the survivors; each published number is still that player's true
    marginal given what the draw currently knows."""
    sim = simulate_tournament(predictor, slots, surface=surface, best_of=best_of,
                              n_sims=n_sims, seed=seed, event=name)
    cols = set(sim.columns)
    sim = sim[[is_real(p) for p in sim["player"]]] if "player" in sim.columns else sim
    proj = [{
        "name": r.player,
        "champion": round(float(r.Champion), 4),
        "final": round(float(r.F), 4) if "F" in cols else None,
        "sf": round(float(r.SF), 4) if "SF" in cols else None,
        # per-round reach odds (entry -> title) for the round-by-round forecast table
        "reach": {c: round(float(getattr(r, c)), 4) for c in ROUND_COLS if c in cols},
    } for r in sim.head(TOP_PROJECTION).itertuples(index=False)]
    return proj, (proj[0]["name"] if proj else None)


def _reconcile_draw_names(slots: list, pool: list, resolve) -> dict:
    """Map provider draw slot names to the model-canonical identity, bridging the few
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
    draw_left: list = []
    for s in dict.fromkeys(x for x in slots if x):
        if _name_key(resolve(s)) in pool_keys:
            canon[s] = resolve(s)
        else:
            draw_left.append(s)
    if not draw_left:
        return canon
    matched = {_name_key(resolve(s)) for s in canon}
    pool_left = [p for p in pool if _name_key(resolve(p)) not in matched]
    pairs = []
    for s in draw_left:
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
                       matchups: list | None = None, tournament_draw: dict | None = None,
                       archive_hint: str | None = None, espn_id: str | None = None,
                       event_end: str | None = None, dmax=None,
                       n_sims: int = 8000, seed: int = 11) -> dict | None:
    # The ratings frame can include qualifying matches for state updates. Tournament
    # projections, however, describe the main draw only. ``draw_level`` filters modern lower-
    # ingestion rows, while the round filter also catches legacy/source rows whose Q1/Q2
    # matches were default-labelled "main". Once a Slam final appears, neither class may leak
    # into a >128-player completed field and pad it to an impossible 256-slot bracket.
    main = _one_match_per_player_round(_main_draw_ko_rows(g))
    display_name = _display_name(
        name, known or set(), tour=tour, event_id=espn_id,
        identity_names=_known_names(g) - {name},
    )

    # One chain, shared with the pre-start path: this event's KNOWN rows -> prior editions
    # (archive_hint) -> Wikipedia infobox -> month guess. Taking `surface_b.mode()` outright
    # was the live half of the split that let an event change surface the day it started.
    surface, surface_src = _known_surface(main)
    if surface is None:
        surface, surface_src = resolve_surface_info(
            tour, name, str(g["date"].min().date()), archive_surface=archive_hint)
    bo = pd.to_numeric(main["best_of"], errors="coerce").max()
    best_of = int(bo) if pd.notna(bo) else 3
    level = resolve_level(
        tour, name, archive_level=_level_label(_main_level_code(g), tour), event_id=espn_id,
    )

    eliminated = set(main["loser_name"])
    final_rows = main[main["round"] == "F"]
    has_final = len(final_rows) > 0
    # An event should not need a round-"F" row to be over. Completion keyed ONLY on that row
    # strands an event at the top of the board forever whenever the results feed drops its
    # final: Iasi sat "live" with three players alive for NINE DAYS after it ended, and
    # Hamburg for two (2026-07-27). If the calendar says it is finished and nothing is still
    # scheduled, it is finished — we just cannot name the champion.
    #
    # Anchored on the DATA's max date, not on today: a frozen pipeline must not start
    # declaring live events complete simply because wall-clock moved on.
    calendar_over = False
    if not has_final and event_end and dmax is not None and not matchups:
        end_ts = pd.to_datetime(event_end, errors="coerce")
        calendar_over = bool(pd.notna(end_ts) and pd.notna(dmax)
                             and end_ts + pd.Timedelta(days=EVENT_CALENDAR_COMPLETE_GRACE_DAYS)
                             < dmax)
    completed = has_final or calendar_over

    champ = runner = None
    ef = (espn_fields or {}).get(name)
    if completed:
        if has_final:
            fr = final_rows.sort_values("date").iloc[-1]
            champ, runner = fr["winner_name"], fr["loser_name"]
        field_pool = set(main["winner_name"]) | set(main["loser_name"])  # full main draw
    else:
        # Live: prefer ESPN's FULL main-draw field (incl. scheduled) so the Day-1
        # favourite reflects everyone still in the draw, not just those who've finished.
        if ef and resolve and len(ef["field"]) >= 8:
            field_pool = {resolve(n) for n in ef["field"]}
            eliminated = {resolve(n) for n in ef["eliminated"]} | eliminated
        else:
            field_pool = set(g["winner_name"]) | set(g["loser_name"])

    # A released complete draw is the authoritative ORDERED bracket: it fixes the real
    # entrants (and the event's best-of) so the live board runs on the
    # actual draw, not a rating seed. Byes/qualifiers ride along in `slots` (None / distinct).
    resolved_draw_slots = None
    resolved_seeds: dict = {}
    if tournament_draw and tournament_draw.get("slots") and resolve:
        # The complete draw and ESPN's field/results name the SAME players in different spellings;
        # reconcile the residue the key can't bridge against this event's own field so an
        # eliminated player can't linger "alive" and freeze the fold at a stale early round.
        pool = list((ef or {}).get("field", [])) + list(g["loser_name"]) + list(g["winner_name"])
        draw_canon = _reconcile_draw_names(tournament_draw["slots"], pool, resolve)
        resolved_draw_slots = [
            (draw_canon.get(slot) or resolve(slot)) if slot else None
            for slot in tournament_draw["slots"]
        ]
        resolved_seeds = {(draw_canon.get(player) or resolve(player)): seed
                          for player, seed in (tournament_draw.get("seeds") or {}).items()}
        # The complete draw remains the authoritative population after completion too.
        # The results frame can retain a handful of qualifier/alternate spellings in rows
        # labelled as knockout rounds; discarding the known draw at the final recreated a
        # 133-player Wimbledon field and padded it to an impossible 256-slot bracket.
        field_pool = {slot for slot in resolved_draw_slots if slot is not None}
        best_of = int(tournament_draw.get("bestOf") or best_of)

    if len(field_pool) < 8:              # dedup-leftover fragment, not a real draw
        return None
    if (top_set is not None and tournament_draw is None and not espn_id
            and len(field_pool & top_set) < 2):
        return None                      # id-less sub-tour / ITF event; ESPN id proves tour scope

    # A finished knockout has exactly one player left standing: the champion. Deriving that
    # by set subtraction makes it hostage to name hygiene on BOTH sides — Umag shipped
    # aliveCount 2 because one entrant appeared under two spellings so the loser identity
    # never cancelled the winner one, and Palermo shipped 32 of 32 because a frozen
    # placeholder draw supplied a field no results row could match. Both are fixed at their
    # sources (config.PLAYER_ALIASES, draws._draw_is_settled); stating this one
    # structurally means a future name split degrades the projection without also publishing
    # a self-contradictory card.
    still_in = field_pool - eliminated
    alive = {champ} if (completed and champ) else still_in
    field = list(field_pool if completed else still_in)
    if len(field) < 2:
        return None

    rank = lambda p: predictor.elo.blended(p, surface)
    if completed:              # retrospective: pre-tournament title odds over the full field
        slots = standard_seed_draw(sorted(field, key=rank, reverse=True))
        draw_state = "final"
    elif resolved_draw_slots is not None:    # live on the REAL ordered draw (exact all rounds)
        slots = advance_slots(resolved_draw_slots, eliminated)
        draw_state = "real"
    else:                      # live from ESPN's partial matchups (seed the unknown frontier)
        mus = matchups or []
        slots = live_draw(field, mus, rank)
        draw_state = draw_status(field, mus, rank)
    known_draw_size = KNOWN_DRAW_SIZE.get(level)
    invalid_field = bool(known_draw_size and len(field_pool) > known_draw_size)
    if len(slots) > 128 or invalid_field:
        if completed:
            # A settled tournament is a record, not a forecast. If its noisy source union
            # cannot be seated, retain only facts we can prove and make the unreliable field
            # explicit. Known tier geometry (a Grand Slam is 128) is authoritative; unknown
            # tiers stay unknown rather than publishing a bogus 129/152-player draw.
            return {
                "name": display_name,
                "surface": surface,
                "level": level,
                "bestOf": best_of,
                "start": str(g["date"].min().date()),
                "end": str(g["date"].max().date()),
                "status": "completed",
                "drawStatus": "final",
                "espnId": espn_id,
                "surfaceSource": surface_src,
                "finalRecorded": bool(has_final),
                "drawSize": known_draw_size,
                "aliveCount": 1,
                "champion": champ,
                "runnerUp": runner,
                "modelFavorite": None,
                "favoritePicked": False,
                "projection": [],
                "fieldUnreliable": True,
                "bracket": None,
                "bracketSize": None,
                "drawSource": (tournament_draw or {}).get("source"),
                "drawSourceId": (tournament_draw or {}).get("sourceId"),
                "drawSourceUrl": (tournament_draw or {}).get("sourceUrl"),
                "drawSourceStart": (tournament_draw or {}).get("sourceStart"),
                "drawSourceEnd": (tournament_draw or {}).get("sourceEnd"),
                "drawEvidencePlayers": (tournament_draw or {}).get("evidencePlayers"),
                "drawEvidenceFieldPlayers": (tournament_draw or {}).get("evidenceFieldPlayers"),
            }
        raise ValueError(
            f"{tour} tournament {name!r}: invalid {len(slots)}-slot bracket "
            f"(field={len(field_pool)}, alive={len(still_in)}, completed={completed}, "
            f"draw_state={draw_state}, draw_slots={len(resolved_draw_slots or [])})"
        )
    # Withhold odds entirely while placeholders hold the draw: a favourite computed against a
    # field of default-rated ghosts is not a weaker estimate, it is a wrong one. Completed
    # events are exempt — their field is the real participant list by definition.
    if completed or projection_is_meaningful(field_pool):
        proj, favorite = _simulate_projection(predictor, slots, surface, best_of, name,
                                              n_sims, seed)
    else:
        proj, favorite = [], None

    # The ACTUAL ordered bracket (real draw only): rounds joined to results, unpriced here —
    # build_tournaments prices it once the forecast log is loaded. Frontier-fold-free.
    bracket = None
    if resolved_draw_slots is not None:
        rcols = [c for c in ("winner_name", "loser_name", "score", "round") if c in main.columns]
        recs = main[rcols].to_dict("records") if not main.empty else []
        bracket = bracket_rounds(resolved_draw_slots, recs, resolved_seeds)
        if not bracket_is_meaningful(bracket, len(field_pool)):
            bracket = None                       # mostly-placeholder early draw -> not worth showing
        elif completed and bracket[-1]["matches"][0].get("winner") is None:
            # A real-player-complete cache can still carry stale ordering from an early
            # article capture. The factual event record remains valid, but advertising an
            # ordered bracket that cannot reproduce its recorded final is dishonest. Keep
            # the strict serving invariant and withhold this optional artifact instead.
            print(f"  {tour} {name!r}: withheld cached bracket — completed final did not reconcile")
            bracket = None

    return {
        "name": display_name, "surface": surface, "level": level, "bestOf": best_of,
        "start": str(g["date"].min().date()), "end": str(g["date"].max().date()),
        "status": "completed" if completed else "live", "drawStatus": draw_state,
        "espnId": espn_id, "surfaceSource": surface_src,
        # False on a completed card means "the calendar says it is over, but the final never
        # arrived" — the champion is genuinely unknown, not a builder bug.
        "finalRecorded": bool(has_final),
        "drawSize": len(field_pool), "aliveCount": len(alive),
        "champion": champ, "runnerUp": runner,
        "modelFavorite": favorite,
        "favoritePicked": bool(completed and favorite == champ),
        "projection": proj,
        "bracket": bracket,
        "bracketSize": len(resolved_draw_slots) if bracket is not None else None,
        "drawSource": (tournament_draw or {}).get("source"),
        "drawSourceId": (tournament_draw or {}).get("sourceId"),
        "drawSourceUrl": (tournament_draw or {}).get("sourceUrl"),
        "drawSourceStart": (tournament_draw or {}).get("sourceStart"),
        "drawSourceEnd": (tournament_draw or {}).get("sourceEnd"),
        "drawEvidencePlayers": (tournament_draw or {}).get("evidencePlayers"),
        "drawEvidenceFieldPlayers": (tournament_draw or {}).get("evidenceFieldPlayers"),
    }


def project_upcoming(predictor, name: str, wd: dict, tour: str, df: pd.DataFrame,
                     known: set | None, resolve, espn_id: str | None = None,
                     n_sims: int = 8000, seed: int = 11) -> dict | None:
    """Pre-start projection for an event whose complete draw is out but which hasn't
    played a match yet (so it's absent from the results-driven event list). The full real
    bracket, no eliminations -> honest 'real' pre-tournament title odds from release."""
    wslots = [resolve(s) if s else None for s in (wd.get("slots") or [])]
    field_pool = {s for s in wslots if s is not None}
    if len(field_pool) < 8:
        return None
    surface, _lvl, bo = _archive_attrs(df, name)
    surface, surface_src = resolve_surface_info(tour, name, wd.get("start") or "",
                                                archive_surface=surface)
    best_of = int(wd.get("bestOf") or bo or 3)
    level = resolve_level(tour, name, event_id=espn_id)
    slots = advance_slots(wslots, set())
    # Same rule as the live path: an early capture that is mostly "Qualifier N" ships as a
    # schedule card (name/dates/surface/tier/drawSize) with no odds, until qualifying resolves.
    if projection_is_meaningful(field_pool):
        proj, favorite = _simulate_projection(predictor, slots, surface, best_of, name,
                                              n_sims, seed)
    else:
        proj, favorite = [], None
    rseeds = {resolve(k): v for k, v in (wd.get("seeds") or {}).items()}
    bracket = bracket_rounds(wslots, [], rseeds)     # released draw, no results yet -> all pending
    if not bracket_is_meaningful(bracket, len(field_pool)):
        bracket = None                               # mostly-placeholder early draw -> not worth showing
    return {
        "name": _display_name(name, known or set(), tour=tour, event_id=espn_id),
        "surface": surface, "level": level, "bestOf": best_of,
        "start": str(wd.get("start") or ""), "end": str(wd.get("end") or wd.get("start") or ""),
        "status": "upcoming", "drawStatus": "real",
        "espnId": espn_id, "surfaceSource": surface_src,
        "drawSize": len(field_pool), "aliveCount": len(field_pool),
        "champion": None, "runnerUp": None,
        "modelFavorite": favorite, "favoritePicked": False,
        "projection": proj,
        "bracket": bracket, "bracketSize": len(wslots),
        "drawSource": wd.get("source"),
        "drawSourceId": wd.get("sourceId"),
        "drawSourceUrl": wd.get("sourceUrl"),
        "drawSourceStart": wd.get("sourceStart"),
        "drawSourceEnd": wd.get("sourceEnd"),
        "drawEvidencePlayers": wd.get("evidencePlayers"),
        "drawEvidenceFieldPlayers": wd.get("evidenceFieldPlayers"),
    }


_STATUS_ORDER = {"live": 0, "upcoming": 1, "completed": 2}


def _price_event_bracket(predictor, t: dict, match_lines: list) -> None:
    """Fill p/probSource/upset on ``t['bracket']``: the logged pre-match forecast for a
    completed match (leakage-free — a recompute would use post-match ratings), the current
    model for a pending match (so the bracket and the schedule board agree)."""
    br = t.get("bracket")
    if not br:
        return
    start = pd.to_datetime(t.get("start"), errors="coerce")
    end = pd.to_datetime(t.get("end"), errors="coerce")
    lo = start - pd.Timedelta(days=2) if pd.notna(start) else None
    hi = end + pd.Timedelta(days=1) if pd.notna(end) else None
    index: dict = {}
    for r in match_lines:
        pa, pb, p = r.get("playerA"), r.get("playerB"), r.get("p")
        if not pa or not pb or p is None:
            continue
        as_of = pd.to_datetime(r.get("as_of"), errors="coerce")
        if lo is not None and pd.notna(as_of) and (as_of < lo or as_of > hi):
            continue                                     # a rematch in another window can't collide
        index.setdefault(frozenset((_name_key(pa), _name_key(pb))), (pa, p))

    rated = predictor.elo.overall
    surface, best_of, name = t.get("surface"), t.get("bestOf"), t.get("name")

    def price_fn(a, b):
        if a in rated and b in rated:
            return predictor.win_prob(a, b, surface=surface, best_of=best_of, event=name)
        return None

    price_bracket(br, price_fn, lambda a, b: oriented_logged(index, a, b))


def build_tournaments(predictor, df: pd.DataFrame, tour: str, **kw) -> list:
    known = _known_names(df)
    top_set = set(sorted(predictor.elo.overall, key=predictor.elo.elo, reverse=True)[:100])
    espn_fields = _load_fields(tour)
    upcoming = _load_upcoming(tour)
    draws = _load_tournament_draws(tour)
    # map ESPN player names onto the predictor's canonical spellings (accent/punct-insensitive)
    canon: dict = {}
    for k in predictor.elo.overall:
        canon.setdefault(_name_key(k), k)
    resolve = lambda n: canon.get(_name_key(n), n)
    # Identity layer: the registry plus every id a cache already carries INSIDE an entry. That
    # `extra` seeding is load-bearing, not decorative — ESPN renamed the DC Open mid-event by
    # inserting a word ("Citi"), which no containment rule can bridge and which the registry
    # never saw under the old title; the espnId stamped in the cached draw is what recovers it.
    resolver = EventResolver(load_registry(tour), extra=[
        (str(v.get("name") or k), v["espnId"])
        for src in (draws, espn_fields) for k, v in (src or {}).items()
        if isinstance(v, dict) and v.get("espnId")]
        + cached_draw_identity_aliases(
            df, draws, ref=df["date"].max() if not df.empty else None))
    draws_by_id, draws_by_name = _split_by_key(draws)
    fields_by_id, fields_by_name = _split_by_key(espn_fields)
    up_by_id, up_by_name = _split_by_key(upcoming)
    out = []
    for name, g, eid in _coalesce_groups(recent_tournaments(df), resolver):
        matchups = [(resolve(a), resolve(b))
                    for a, b in (_lookup(up_by_id, up_by_name, eid, name) or [])]
        try:
            t = project_tournament(predictor, name, g, tour, known=known, top_set=top_set,
                                   espn_fields=_fields_view(fields_by_id, fields_by_name,
                                                            eid, name),
                                   resolve=resolve, matchups=matchups,
                                   tournament_draw=_lookup(draws_by_id, draws_by_name, eid, name),
                                   archive_hint=_archive_attrs(df, name)[0],
                                   espn_id=eid,
                                   event_end=_scheduled_end(eid, name, resolver,
                                                            draws_by_id, draws_by_name),
                                   dmax=df["date"].max() if not df.empty else None, **kw)
        except ValueError as e:
            # One unprojectable event must not cost the whole board. The >128-slot guard
            # inside project_tournament is a real signal — a leaked qualifier padding a
            # completed Slam field to 256 — but raising it here took the ENTIRE pipeline
            # down: no export, no deploy, and every queued refresh behind it stalled. That
            # happened twice (WTA Wimbledon on 2026-07-11 and again on 07-27, once the
            # cached complete draw aged out of the ESPN discovery sweep and stopped pinning the
            # field). The 07-11 fix leaned on that cache being present, which it cannot be
            # forever. Skip the event, say so loudly, and let the rest of the board ship;
            # data/health.py still validates whatever we do publish.
            print(f"::warning::{tour} tournament {name!r} skipped — {e}")
            continue
        if t:
            out.append(t)
    # Pre-start events: a complete draw is out but no match has been played yet, so the
    # results-driven list above hasn't surfaced them. Project the real bracket now — but
    # only for events that are actually upcoming: dedup by DISPLAY name (a completed event's
    # results-feed name differs from ESPN's sponsor name) and skip anything already over.
    # Recognise an already-projected event by ID as well as by display name: after a rename
    # the draw cache key and the board's name no longer match, and a name-only check shipped
    # the same tournament twice.
    seen = {t["name"] for t in out}
    seen_ids = {t.get("espnId") for t in out if t.get("espnId")}
    dmax = df["date"].max() if not df.empty else None
    for key, wd in draws.items():
        name = str(wd.get("name") or key)
        wd_id = str(wd.get("espnId") or "") or (key if is_event_id(key) else None)
        if wd_id and wd_id in seen_ids:
            continue
        if _display_name(name, known, tour=tour, event_id=wd_id) in seen or not wd.get("slots"):
            continue
        end = pd.to_datetime(wd.get("end") or wd.get("start"), errors="coerce")
        if dmax is not None and pd.notna(end) and end < dmax - pd.Timedelta(days=2):
            continue                         # already finished (its card is a completed one)
        t = project_upcoming(predictor, name, wd, tour, df, known, resolve,
                             espn_id=wd_id or resolver.id_of(name), **kw)
        if t:
            out.append(t)
    # The results loop groups by RAW tourney_name, so an event whose live/ESPN feed uses a
    # sponsor title ('Bad Homburg Open powered by Solarwatt') and whose archive uses the city
    # ('Bad Homburg') enters twice, both collapsing to one display name. Keep one per name.
    out = _dedup_by_display_name(out, tour)
    # Live, then upcoming, then completed; within each group, most recent first.
    out.sort(key=lambda t: t["end"], reverse=True)
    out.sort(key=lambda t: _STATUS_ORDER.get(t["status"], 3))
    # Price each real bracket once, off the append-only forecast log (canonical reader).
    from ..eval.track import FORECAST_DIR, _read_log
    match_lines = [r for r in _read_log(FORECAST_DIR / f"{tour}.jsonl") if r.get("type") == "match"]
    for t in out:
        _price_event_bracket(predictor, t, match_lines)
    return out
