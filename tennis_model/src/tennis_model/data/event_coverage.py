"""Independent evidence that every begun tour event reaches ``tournaments.json``.

The tournament projector is intentionally forgiving: one malformed draw is skipped so it
cannot take down the whole board. That makes a second, independent enumeration essential —
otherwise the skip is indistinguishable from a quiet week. This module builds that expected
set from facts that exist before projection:

* a real main-draw knockout result; or
* a real-player scheduled/in-progress matchup dated no later than the build date.

Calendar entries and all-TBD draws are not proof that an event has begun. Stable ESPN ids are
the primary identity. Where no id exists, two source records join only on overlapping dates
plus at least two shared real players; names are display metadata, never join evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime

import pandas as pd

from ..config import live_dir
from .events import EventResolver, display_event_name, is_event_id, load_registry, norm_event_name
from .participants import is_real_participant
from .results import _name_key
from .surface import resolve_level, resolve_surface_info

COVERAGE_VERSION = 1
COVERAGE_RETENTION_DAYS = 18
_KO_ROUNDS = frozenset({"R128", "R64", "R32", "R16", "QF", "SF", "F"})
_MAIN_LEVELS = frozenset({
    "G", "M", "A", "F", "D", "O",
    "250", "500", "1000", "125",
    "ATP250", "ATP500", "ATP1000", "WTA125", "WTA250", "WTA500", "WTA1000",
    "GRAND SLAM", "MASTERS 1000", "TOUR FINALS", "OLYMPICS",
})


def _date(value) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce")
    return pd.Timestamp(parsed).normalize() if pd.notna(parsed) else None


def _iso(value) -> str | None:
    parsed = _date(value)
    return str(parsed.date()) if parsed is not None else None


def _real_name(value) -> bool:
    return is_real_participant(value)


def _event_id(values) -> str | None:
    ids = [str(v).strip() for v in values
           if v is not None and str(v).strip() and str(v).strip().lower() != "nan"]
    return Counter(ids).most_common(1)[0][0] if ids else None


def _main_tour_group(group: pd.DataFrame) -> bool:
    """Whether id-less results carry an explicit main-tour level.

    A stable ESPN event id is already enough. This fallback catches archive-era tour events
    without sweeping every Challenger/ITF result into a board whose projector deliberately
    does not promise that population.
    """
    values: set[str] = set()
    for column in ("tourney_level", "tier"):
        if column in group.columns:
            values |= {str(v).strip().upper() for v in group[column].dropna() if str(v).strip()}
    return bool(values & _MAIN_LEVELS)


def _registry_dates(registry: dict, event_id: str | None, start, end) -> tuple[str | None, str | None]:
    entry = ((registry.get("events") or {}).get(str(event_id)) or {}) if event_id else {}
    return (_iso(entry.get("start")) or _iso(start),
            _iso(entry.get("end")) or _iso(end) or _iso(start))


def _registry_name(registry: dict, event_id: str | None, fallback: str) -> str:
    entry = ((registry.get("events") or {}).get(str(event_id)) or {}) if event_id else {}
    return str(entry.get("name") or fallback)


def _registry_names(registry: dict, event_id: str | None, fallback: str) -> set[str]:
    entry = ((registry.get("events") or {}).get(str(event_id)) or {}) if event_id else {}
    return {str(name) for name in [fallback, entry.get("name"), *(entry.get("names") or [])]
            if name}


def _mode(group: pd.DataFrame, columns: tuple[str, ...]):
    for column in columns:
        if column not in group.columns:
            continue
        values = [value for value in group[column]
                  if value is not None and str(value).strip()
                  and str(value).strip().lower() not in {"nan", "none"}]
        if values:
            return Counter(values).most_common(1)[0][0]
    return None


def _result_attrs(group: pd.DataFrame) -> tuple[object, object, object, int | None]:
    """Tier, surface, provenance, and format evidence already present on result rows."""
    level = _mode(group, ("tourney_level", "tier"))
    surface_pairs = []
    if "surface_b" in group.columns:
        sources = (group["surface_src"] if "surface_src" in group.columns
                   else pd.Series("archive", index=group.index))
        surface_pairs = [
            (surface, source)
            for surface, source in zip(group["surface_b"], sources)
            if surface is not None and str(surface).strip()
            and str(surface).strip().lower() not in {"nan", "none"}
        ]
    # A real archive/wiki value outranks the month guess. Within one provenance tier, mode
    # preserves the same source-majority behavior used elsewhere in the results pipeline.
    trusted = [pair for pair in surface_pairs if str(pair[1]).lower() != "month"]
    surface, surface_source = (Counter(trusted or surface_pairs).most_common(1)[0][0]
                               if surface_pairs else (None, None))
    best_of = None
    if "best_of" in group.columns:
        values = pd.to_numeric(group["best_of"], errors="coerce").dropna()
        if not values.empty:
            best_of = int(values.mode().iloc[0])
    return level, surface, surface_source, best_of


def _cached_identity_extras(tour: str) -> list[tuple[str, str]]:
    """Name/id evidence retained in caches after the registry prunes an old event.

    This is how the projector still recovers Wimbledon as ``188-2026`` once the registry's
    retention window has elapsed; the independent manifest must not mint an id-less second
    identity for the same source evidence.
    """
    out: list[tuple[str, str]] = []
    for filename in ("fields.json", "tournament_draws.json", "wiki_draws.json"):
        path = live_dir(tour) / filename
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for key, value in (payload.items() if isinstance(payload, dict) else []):
            event_id = value.get("espnId") if isinstance(value, dict) else None
            if key and event_id:
                out.append((str(key), str(event_id)))
    return out


def _candidate(name: str, event_id: str | None, start, end, source: str,
               players, pairs, registry: dict, *, champion=None, runner_up=None,
               archive_level=None, surface=None, surface_source=None, best_of=None) -> dict:
    start_s, end_s = _registry_dates(registry, event_id, start, end)
    final_recorded = bool(_real_name(champion) and _real_name(runner_up))
    return {
        "espnId": event_id,
        "name": _registry_name(registry, event_id, name),
        "names": _registry_names(registry, event_id, str(name)),
        "start": start_s,
        "end": end_s,
        # Join evidence keeps the source-observed dates, not the broader ESPN calendar.
        # Adjacent events' qualifying calendars overlap and top players can enter both; using
        # those broad ranges merged Wimbledon into the following week's Gstaad/Umag fields.
        "evidenceStart": _iso(start),
        "evidenceEnd": _iso(end) or _iso(start),
        "evidence": {source},
        "players": {str(p) for p in players if _real_name(p)},
        "pairs": {tuple(sorted((_name_key(a), _name_key(b)))) for a, b in pairs
                  if _real_name(a) and _real_name(b)},
        "finalRecorded": final_recorded,
        "champion": str(champion) if final_recorded else None,
        "runnerUp": str(runner_up) if final_recorded else None,
        "archiveLevel": archive_level,
        "archiveNames": {str(name)} if source == "result" and archive_level is not None else set(),
        "surface": surface,
        "surfaceSource": surface_source,
        "bestOf": best_of,
    }


def _result_candidates(df: pd.DataFrame, ref: pd.Timestamp, resolver: EventResolver,
                       registry: dict) -> list[dict]:
    required = {"tourney_name", "date", "round", "winner_name", "loser_name"}
    if df is None or df.empty or not required.issubset(df.columns):
        return []
    frame = df.copy()
    frame["_coverage_date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    # Keep the full current-edition evidence (not just the final days): filtering rows to the
    # retention boundary first turned Wimbledon into a two-player, final-only "event". Forty
    # days matches the projector's capture window; the GROUP end decides retention.
    frame = frame[(frame["_coverage_date"] >= ref - pd.Timedelta(days=40))
                  & (frame["_coverage_date"] <= ref)
                  & frame["round"].isin(_KO_ROUNDS)]
    out: list[dict] = []
    for raw_name, group in frame.groupby("tourney_name", sort=False):
        if group["_coverage_date"].max() < ref - pd.Timedelta(days=COVERAGE_RETENTION_DAYS):
            continue
        if "draw_level" in group.columns:
            # Explicit qualifying provenance is evidence about the qualifying tournament,
            # never proof that its parent main draw has begun. Keep WTA 125/Challenger main
            # events (``chall``), but fail closed when an event group contains only ``qual``
            # rows. The former fallback-to-whole-group turned nine US Open Q1 results into
            # a live main-draw coverage shell on 2026-08-28.
            roles = group["draw_level"].fillna("main").astype(str).str.lower()
            group = group[roles.isin(("main", "chall"))]
            if group.empty:
                continue
        final_rows = group[group["round"] == "F"].sort_values("_coverage_date")
        champion = runner_up = None
        if not final_rows.empty:
            final = final_rows.iloc[-1]
            champion, runner_up = final["winner_name"], final["loser_name"]
        direct = _event_id(group["espn_id"] if "espn_id" in group.columns else [])
        event_id = direct or resolver.id_of(raw_name)
        if not event_id and not _main_tour_group(group):
            continue
        players = list(group["winner_name"]) + list(group["loser_name"])
        pairs = list(zip(group["winner_name"], group["loser_name"]))
        archive_level, surface, surface_source, best_of = _result_attrs(group)
        out.append(_candidate(str(raw_name), event_id, group["_coverage_date"].min(),
                              group["_coverage_date"].max(), "result", players, pairs, registry,
                              champion=champion, runner_up=runner_up,
                              archive_level=archive_level, surface=surface,
                              surface_source=surface_source, best_of=best_of))
    return out


def cached_draw_identity_aliases(
        df: pd.DataFrame, draws: dict, *, ref=None) -> list[tuple[str, str]]:
    """Prove id-less result names against ID-keyed complete draws.

    ESPN's rolling result file is the only match source that carries ``espnId``.  When an
    event ages out, an archive label such as ``Iasi`` can remain while the cached official
    draw is still keyed as ``874-2026``.  Names are deliberately irrelevant here: a result
    group earns the draw's id only when their date spans overlap, at least three real players
    agree, and at least two actual first-round matchups agree.  The plural matchup rule is
    load-bearing: Iasi and the adjacent Nordea event shared 13 players but only one match.
    Ambiguous evidence earns no alias.
    """
    if df is None or df.empty or "date" not in df.columns or not draws:
        return []
    ref_date = _date(ref)
    if ref_date is None:
        dates = pd.to_datetime(df.get("date"), errors="coerce")
        ref_date = pd.Timestamp(dates.max()).normalize() if dates.notna().any() else None
    if ref_date is None:
        return []

    empty_registry = {"events": {}}
    candidates = _result_candidates(df, ref_date, EventResolver(empty_registry), empty_registry)
    draw_evidence: list[tuple[str, pd.Timestamp, pd.Timestamp, set[str], set[tuple[str, str]]]] = []
    for key, entry in draws.items():
        if not isinstance(entry, dict):
            continue
        event_id = str(entry.get("espnId") or (key if is_event_id(key) else "")).strip()
        start, end = _date(entry.get("start")), _date(entry.get("end") or entry.get("start"))
        slots = list(entry.get("slots") or [])
        if not event_id or start is None or end is None or len(slots) < 8:
            continue
        players = {_name_key(slot) for slot in slots if _real_name(slot)}
        pairs = {
            tuple(sorted((_name_key(slots[i]), _name_key(slots[i + 1]))))
            for i in range(0, len(slots) - 1, 2)
            if _real_name(slots[i]) and _real_name(slots[i + 1])
        }
        draw_evidence.append((event_id, start, end, players, pairs))

    aliases: list[tuple[str, str]] = []
    for candidate in candidates:
        if candidate.get("espnId"):
            continue
        cstart = _date(candidate.get("evidenceStart"))
        cend = _date(candidate.get("evidenceEnd"))
        if cstart is None or cend is None:
            continue
        cplayers = {_name_key(player) for player in candidate.get("players") or []}
        cpairs = set(candidate.get("pairs") or ())
        hits = {
            event_id for event_id, start, end, players, pairs in draw_evidence
            if max(cstart, start) <= min(cend, end)
            and (min(cend, end) - max(cstart, start)).days >= 2
            and len(cplayers & players) >= 3
            and len(cpairs & pairs) >= 2
        }
        if len(hits) == 1:
            aliases.append((str(candidate["name"]), next(iter(hits))))
    return aliases


def _scheduled_candidates(upcoming: pd.DataFrame, ref: pd.Timestamp, resolver: EventResolver,
                          registry: dict) -> list[dict]:
    required = {"tourney_name", "tourney_date", "playerA", "playerB"}
    if upcoming is None or upcoming.empty or not required.issubset(upcoming.columns):
        return []
    frame = upcoming.copy()
    frame["_coverage_date"] = pd.to_datetime(frame["tourney_date"], errors="coerce").dt.normalize()
    frame = frame[(frame["_coverage_date"] >= ref - pd.Timedelta(days=COVERAGE_RETENTION_DAYS))
                  & (frame["_coverage_date"] <= ref)]
    frame = frame[[bool(_real_name(a) and _real_name(b))
                   for a, b in zip(frame["playerA"], frame["playerB"])]]
    if frame.empty:
        return []
    direct_ids = frame["espn_id"] if "espn_id" in frame.columns else pd.Series(None, index=frame.index)
    frame = frame.assign(_coverage_id=[
        (None if v is None or str(v).strip().lower() == "nan" else str(v).strip())
        for v in direct_ids
    ])
    # Group same-id sponsor variants together immediately; id-less rows remain name-local
    # until the evidence merge below proves that two names describe one event.
    frame["_coverage_group"] = [eid or f"name:{name}"
                                for eid, name in zip(frame["_coverage_id"], frame["tourney_name"])]
    out: list[dict] = []
    for _key, group in frame.groupby("_coverage_group", sort=False):
        raw_name = str(group["tourney_name"].iloc[0])
        direct = _event_id(group["_coverage_id"])
        event_id = direct or resolver.id_of(raw_name)
        players = list(group["playerA"]) + list(group["playerB"])
        pairs = list(zip(group["playerA"], group["playerB"]))
        candidate = _candidate(raw_name, event_id, group["_coverage_date"].min(),
                               group["_coverage_date"].max(), "scheduled", players, pairs, registry)
        candidate["names"] |= {str(n) for n in group["tourney_name"] if n}
        out.append(candidate)
    return out


def _overlaps(a: dict, b: dict, *, evidence: bool = False) -> bool:
    start_key, end_key = (("evidenceStart", "evidenceEnd") if evidence else ("start", "end"))
    sa, ea = _date(a.get(start_key)), _date(a.get(end_key))
    sb, eb = _date(b.get(start_key)), _date(b.get(end_key))
    return bool(sa is not None and ea is not None and sb is not None and eb is not None
                and max(sa, sb) <= min(ea, eb))


def _same_event(a: dict, b: dict) -> bool:
    aid, bid = a.get("espnId"), b.get("espnId")
    if aid and bid:
        return str(aid) == str(bid)
    if not _overlaps(a, b, evidence=True):
        return False
    # The two shared players must also form the same observed matchup. Merely sharing two
    # entrants is not enough across adjacent events: players who lose early at Wimbledon can
    # enter the next week's 125 while the calendars still overlap at their boundaries.
    return bool(set(a.get("pairs") or ()) & set(b.get("pairs") or ()))


def _merge_candidates(candidates: list[dict], tour: str, registry: dict) -> list[dict]:
    parent = list(range(len(candidates)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            ids = {str(candidates[k]["espnId"]) for k in range(len(candidates))
                   if find(k) in (ri, rj) and candidates[k].get("espnId")}
            if len(ids) > 1:
                return                 # an id-less bridge can never fuse two stable ids
            parent[rj] = ri

    for i, a in enumerate(candidates):
        for j in range(i + 1, len(candidates)):
            if _same_event(a, candidates[j]):
                union(i, j)

    groups: dict[int, list[dict]] = {}
    for i, candidate in enumerate(candidates):
        groups.setdefault(find(i), []).append(candidate)

    events: list[dict] = []
    for members in groups.values():
        ids = sorted({str(m["espnId"]) for m in members if m.get("espnId")})
        event_id = ids[0] if len(ids) == 1 else None
        names = sorted({n for m in members for n in m["names"]}, key=norm_event_name)
        players = sorted({p for m in members for p in m["players"]}, key=_name_key)
        pairs = sorted({pair for m in members for pair in m["pairs"]})
        finals = {
            (_name_key(m["champion"]), _name_key(m["runnerUp"])):
                (m["champion"], m["runnerUp"])
            for m in members if m.get("finalRecorded")
        }
        champion = runner_up = None
        if len(finals) == 1:
            champion, runner_up = next(iter(finals.values()))
        starts = [m["start"] for m in members if m.get("start")]
        ends = [m["end"] for m in members if m.get("end")]
        evidence_starts = [m["evidenceStart"] for m in members if m.get("evidenceStart")]
        evidence_ends = [m["evidenceEnd"] for m in members if m.get("evidenceEnd")]
        start, end = (min(starts) if starts else None), (max(ends) if ends else None)
        raw_display = _registry_name(registry, event_id, names[0] if names else "Unknown event")
        archive_names = {name for member in members for name in member.get("archiveNames", set())}
        display = display_event_name(
            tour, raw_display, event_id, identity_names=archive_names - {raw_display})
        archive_levels = [m.get("archiveLevel") for m in members if m.get("archiveLevel") is not None]
        best_of_values = [m.get("bestOf") for m in members if m.get("bestOf") is not None]
        surface_values = [(m.get("surface"), m.get("surfaceSource")) for m in members
                          if m.get("surface") is not None]
        trusted_surfaces = [pair for pair in surface_values if str(pair[1]).lower() != "month"]
        merged_surface = (Counter(trusted_surfaces or surface_values).most_common(1)[0][0]
                          if surface_values else (None, None))
        if event_id:
            key = f"espn:{event_id}"
        else:
            proof = "|".join([tour, start or "", end or ""] + sorted(_name_key(p) for p in players))
            key = "evidence:" + hashlib.sha256(proof.encode()).hexdigest()[:16]
        events.append({
            "key": key, "espnId": event_id, "name": display, "names": names,
            "start": start, "end": end,
            "evidenceStart": min(evidence_starts) if evidence_starts else start,
            "evidenceEnd": max(evidence_ends) if evidence_ends else end,
            "evidence": sorted({s for m in members for s in m["evidence"]}),
            "players": players, "matchPairs": [list(pair) for pair in pairs],
            # Preserve only one non-conflicting settled result. If two sources somehow claim
            # different finals, the shell stays unknown and the existing health invariant
            # raises the conflict instead of silently picking a champion.
            "finalRecorded": champion is not None,
            "champion": champion, "runnerUp": runner_up,
            "archiveLevel": (Counter(archive_levels).most_common(1)[0][0]
                             if archive_levels else None),
            "surface": merged_surface[0], "surfaceSource": merged_surface[1],
            "bestOf": (Counter(best_of_values).most_common(1)[0][0]
                       if best_of_values else None),
        })
    return sorted(events, key=lambda e: (e.get("start") or "", norm_event_name(e["name"])))


def build_event_coverage(df: pd.DataFrame, tour: str, *, build_date=None,
                         upcoming_df: pd.DataFrame | None = None,
                         registry: dict | None = None, draws: dict | None = None) -> dict:
    """Return the versioned expected-event manifest for one build."""
    ref = _date(build_date)
    if ref is None:
        ref = pd.Timestamp(datetime.now(UTC).date())
    use_cache_identities = registry is None
    registry = load_registry(tour) if registry is None else registry
    if draws is None and use_cache_identities:
        from .draws import load_tournament_draws
        draws = load_tournament_draws(tour)
    extras = list(_cached_identity_extras(tour) if use_cache_identities else ())
    extras += cached_draw_identity_aliases(df, draws or {}, ref=ref)
    resolver = EventResolver(registry, extra=extras)
    if upcoming_df is None:
        from ..model.upcoming import load_upcoming
        upcoming_df = load_upcoming(tour)
    candidates = _result_candidates(df, ref, resolver, registry)
    candidates += _scheduled_candidates(upcoming_df, ref, resolver, registry)
    return {
        "version": COVERAGE_VERSION,
        "tour": tour,
        "buildDate": str(ref.date()),
        "events": _merge_candidates(candidates, tour, registry),
    }


def _card_players(card: dict) -> set[str]:
    players = {p.get("name") for p in (card.get("projection") or []) if isinstance(p, dict)}
    players |= {card.get("champion"), card.get("runnerUp")}
    for rnd in card.get("bracket") or []:
        for match in rnd.get("matches") or []:
            players |= {match.get("a"), match.get("b")}
    return {str(p) for p in players if _real_name(p)}


def _card_matches_event(card: dict, event: dict) -> bool:
    card_id, event_id = card.get("espnId"), event.get("espnId")
    if card_id and event_id:
        return str(card_id) == str(event_id)
    if card_id or event_id or not _overlaps(card, event):
        return False
    cp = {_name_key(p) for p in _card_players(card)}
    ep = {_name_key(p) for p in event.get("players") or [] if _real_name(p)}
    return len(cp & ep) >= 2


def _untracked_card_key(card: dict, tour: str) -> str:
    proof = "|".join(str(x or "") for x in (
        tour, card.get("name"), card.get("start"), card.get("end"), card.get("status")))
    return "card:" + hashlib.sha256(proof.encode()).hexdigest()[:16]


def _coverage_shell(event: dict, build_date: str, tour: str) -> dict:
    """An honest presence-only card when simulation cannot safely describe the draw."""
    end = _date(event.get("end"))
    ref = _date(build_date)
    has_final = bool(event.get("finalRecorded") and event.get("champion")
                     and event.get("runnerUp"))
    completed = has_final or bool(end is not None and ref is not None and end < ref)
    generic = f"{tour.upper()} Tour"
    names = list(dict.fromkeys([*(event.get("names") or []), event.get("name")]))
    level = generic
    for name in names:
        candidate = resolve_level(
            tour, str(name), archive_level=event.get("archiveLevel"),
            event_id=event.get("espnId"),
        )
        if candidate != generic:
            level = candidate
            break

    surface = surface_source = None
    month_guess = None
    archive_surface = (event.get("surface")
                       if event.get("surfaceSource") == "archive" else None)
    for name in names:
        candidate, source = resolve_surface_info(
            tour, str(name), event.get("start") or build_date,
            archive_surface=archive_surface)
        if source != "month":
            surface, surface_source = candidate, source
            break
        month_guess = month_guess or (candidate, source)
    if surface is None and event.get("surface") is not None:
        surface, surface_source = event.get("surface"), event.get("surfaceSource")
    if surface is None and month_guess:
        surface, surface_source = month_guess

    try:
        best_of = int(event.get("bestOf"))
    except (TypeError, ValueError):
        best_of = 5 if tour == "atp" and level == "Grand Slam" else 3
    return {
        "name": event["name"], "surface": surface, "level": level, "bestOf": best_of,
        "start": event.get("start") or build_date, "end": event.get("end") or build_date,
        "status": "completed" if completed else "live",
        "drawStatus": "final" if has_final else "unavailable",
        "espnId": event.get("espnId"), "surfaceSource": surface_source,
        "finalRecorded": has_final if completed else None,
        "drawSize": None, "aliveCount": 1 if has_final else None,
        "champion": event.get("champion") if has_final else None,
        "runnerUp": event.get("runnerUp") if has_final else None,
        "modelFavorite": None, "favoritePicked": False, "projection": [],
        "bracket": None, "bracketSize": None,
        "drawSource": None, "drawSourceId": None, "drawSourceUrl": None,
        "drawSourceStart": None, "drawSourceEnd": None, "drawEvidencePlayers": None,
        "drawEvidenceFieldPlayers": None,
        "coverageKey": event["key"], "coverageOnly": True,
    }


def finalize_event_coverage(manifest: dict, tournaments: list[dict]) -> dict:
    """Stamp explicit keys, fill any projector gap with a shell, and finalize membership.

    Mutates ``tournaments`` because export immediately writes that same list. The returned
    manifest is JSON-ready and records the complete shipped key multiset for health/deploy
    parity checks.
    """
    events = list(manifest.get("events") or [])
    for card in tournaments:
        matches = [event for event in events if _card_matches_event(card, event)]
        if len(matches) == 1:
            card["coverageKey"] = matches[0]["key"]
        elif card.get("espnId"):
            card["coverageKey"] = f"espn:{card['espnId']}"
        else:
            card["coverageKey"] = _untracked_card_key(card, str(manifest.get("tour") or ""))
        card.setdefault("coverageOnly", False)

    counts = Counter(str(card.get("coverageKey")) for card in tournaments if card.get("coverageKey"))
    for event in events:
        if counts[event["key"]] == 0:
            tournaments.append(_coverage_shell(event, str(manifest.get("buildDate") or ""),
                                               str(manifest.get("tour") or "")))

    order = {"live": 0, "upcoming": 1, "completed": 2}
    tournaments.sort(key=lambda card: card.get("end") or "", reverse=True)
    tournaments.sort(key=lambda card: order.get(card.get("status"), 3))
    shipped = sorted(str(card["coverageKey"]) for card in tournaments if card.get("coverageKey"))
    shell_keys = sorted(str(card["coverageKey"]) for card in tournaments
                        if card.get("coverageKey") and card.get("coverageOnly"))
    return {**manifest, "shippedKeys": shipped, "shellKeys": shell_keys}
