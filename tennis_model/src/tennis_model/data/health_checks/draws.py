"""Draws invariants extracted without changing gate semantics."""

from __future__ import annotations

import urllib.parse

import pandas as pd

from ...config import (
    HEALTH_MAX_LIVE_EVENT_AGE_DAYS,
    HEALTH_MAX_SLAM_UPCOMING_START_LAG_DAYS,
    HEALTH_MAX_UPCOMING_START_LAG_DAYS,
)
from ..surface import LEVEL_VOCAB
from .common import (
    _BYE_DRAW_SIZES,
    _CANONICAL_SURFACES,
    _DRAW_STATES,
    _REACH_ORDER,
    _STATUSES,
    _add_finding,
    _age_days,
    _event_entity,
    _event_evidence_matches,
    _event_provider_entity,
    _event_stable_entity,
    _flag_placeholders,
    _is_prob,
    _is_real_name,
    _match_entity,
    _norm_name,
    _player_identity_key,
    _pow2,
    _real_draw_size_ok,
    _tier_severity,
    _tiered,
)

_DRAW_SOURCE_HOSTS = {
    "atp": "www.protennislive.com",
    "wta": "wtafiles.wtatennis.com",
    "wikipedia": "en.wikipedia.org",
}

def _check_projection(out: list, tour: str, name, proj: list, *, event_entity: str) -> None:
    for p in proj:
        who = p.get("name")
        entity = f"{event_entity}#player:{_player_identity_key(who)}"
        c, f, s = p.get("champion"), p.get("final"), p.get("sf")
        for k, v in (("champion", c), ("final", f), ("sf", s)):
            # None is deliberate: the live projector (sim/tournaments.py) sets a round field
            # to None once that round is already DETERMINED ("SF" not in cols -> sf=None for a
            # finalist who is past the semis). That degrades gracefully in the UI; only a
            # PRESENT-but-out-of-range value is a real problem.
            if v is not None and not _is_prob(v):
                _add_finding(
                    out, "output.projection.probability_invalid",
                    f"{tour}: {name!r} {who!r} {k}={v!r} out of [0,1]",
                    severity="error", entity=f"{entity}#stage:{k}",
                    evidence={"stage": k, "value": repr(v)})
        if _is_prob(c) and _is_prob(f) and _is_prob(s) and (c > f + 1e-6 or f > s + 1e-6):
            _add_finding(
                out, "output.projection.stage_order_invalid",
                f"{tour}: {name!r} {who!r} champion<=final<=sf violated ({c},{f},{s})",
                severity="error", entity=entity,
                evidence={"champion": float(c), "final": float(f), "sf": float(s)})
        seq = [p["reach"][k] for k in _REACH_ORDER if isinstance(p.get("reach"), dict) and k in p["reach"]]
        if any(not _is_prob(v) for v in seq):
            _add_finding(
                out, "output.projection.reach_probability_invalid",
                f"{tour}: {name!r} {who!r} reach probability out of [0,1]",
                severity="error", entity=entity,
                evidence={"values": [repr(v) for v in seq]})
        elif any(seq[i] < seq[i + 1] - 1e-6 for i in range(len(seq) - 1)):
            _add_finding(
                out, "output.projection.reach_order_invalid",
                f"{tour}: {name!r} {who!r} reach odds not monotonically non-increasing",
                severity="error", entity=entity,
                evidence={"values": [float(v) for v in seq]})

def _check_tournament(out: list, tour: str, t: dict, now: pd.Timestamp | None = None) -> None:
    name, status = t.get("name"), t.get("status")
    force = bool(t.get("coverageOnly"))
    event_entity = _event_entity(t)
    ds, size, alive, champ = t.get("drawStatus"), t.get("drawSize"), t.get("aliveCount"), t.get("champion")
    main_draw_matches = t.get("mainDrawMatchCount")
    if not force:
        if (not isinstance(main_draw_matches, int) or isinstance(main_draw_matches, bool)
                or main_draw_matches < 0):
            _add_finding(
                out, "output.tournament.main_draw_match_count_invalid",
                f"{tour}: tournament {name!r} mainDrawMatchCount "
                f"{main_draw_matches!r} is missing or invalid",
                severity="error", entity=event_entity,
                evidence={"mainDrawMatchCount": repr(main_draw_matches)})
        elif status == "live" and main_draw_matches == 0:
            _add_finding(
                out, "output.tournament.live_without_main_draw",
                f"{tour}: live tournament {name!r} has no observed main-draw matches — "
                "qualifying results cannot start the main-draw lifecycle",
                severity="error", entity=event_entity,
                evidence={"mainDrawMatchCount": 0, "status": "live"})
    if status not in _STATUSES:
        _add_finding(
            out, "output.tournament.status_invalid",
            f"{tour}: tournament {name!r} has bad status {status!r}",
            severity="error", entity=event_entity,
            evidence={"status": repr(status)})
    if ds is None:
        _add_finding(
            out, "output.tournament.draw_status_missing",
            f"{tour}: tournament {name!r} missing drawStatus",
            severity="error", entity=event_entity, evidence={})
    elif ds not in _DRAW_STATES:
        _add_finding(
            out, "output.tournament.draw_status_invalid",
            f"{tour}: tournament {name!r} has bad drawStatus {ds!r}",
            severity="error", entity=event_entity,
            evidence={"drawStatus": repr(ds)})
    if isinstance(size, int) and isinstance(alive, int) and alive > size:
        _add_finding(
            out, "output.tournament.alive_count_invalid",
            f"{tour}: tournament {name!r} aliveCount {alive} > drawSize {size}",
            severity="error", entity=event_entity,
            evidence={"aliveCount": alive, "drawSize": size})
    if isinstance(size, int) and size > 128:
        _add_finding(
            out, "output.tournament.draw_size_excessive",
            f"{tour}: tournament {name!r} drawSize {size} exceeds the maximum 128-player draw",
            severity="error", entity=event_entity,
            evidence={"drawSize": size, "maximum": 128})
    # a real bracket seats a STANDARD draw size — a power of two, or a sanctioned
    # bye-draw (28/48/56/96...; Gstaad's 28-draw blocked a deploy on 2026-07-10 when this
    # demanded strict powers of two). A leaked 'TBD' (128 -> 129, 28 -> 29) or a name-
    # resolution loss (28 -> 27) still lands outside the set and blocks. completed/
    # partial/seeded/completed sizes can be non-standard because drawSize counts entrants,
    # but no tour-level singles draw can exceed 128.
    if ds == "real" and isinstance(size, int) and not _real_draw_size_ok(size):
        _add_finding(
            out, "output.tournament.draw_geometry_invalid",
            f"{tour}: tournament {name!r} real draw size {size} is not a standard "
            f"bracket size (power of two or bye-draw {sorted(_BYE_DRAW_SIZES)})",
            severity="error", entity=event_entity,
            evidence={"drawSize": size, "allowedByeDrawSizes": sorted(_BYE_DRAW_SIZES)})
    if status == "completed" and not champ:
        # An event can now be called over by its CALENDAR when the results feed never
        # delivered a final (sim/tournaments: Iasi sat "live" for nine days waiting for one).
        # That card is honest — the champion is genuinely unknown — so it is advisory. A
        # completed card with no champion and no such explanation is still a builder bug.
        if t.get("finalRecorded") is False:
            _add_finding(
                out, "output.tournament.final_missing",
                f"{tour}: completed tournament {name!r} completed without a recorded "
                f"final — its calendar says it is over but no final arrived, so the "
                f"champion is unknown",
                severity="warning", entity=event_entity,
                evidence={"finalRecorded": False})
        else:
            _add_finding(
                out, "output.tournament.champion_missing",
                f"{tour}: completed tournament {name!r} has no champion",
                severity="error", entity=event_entity, evidence={})
    if status in ("live", "upcoming") and champ:
        _add_finding(
            out, "output.tournament.champion_premature",
            f"{tour}: {status} tournament {name!r} already names champion {champ!r}",
            severity="error", entity=event_entity,
            evidence={"status": status, "champion": repr(champ)})
    # An entrant of a live ordered draw that the feed no longer lists in the event has left
    # without losing, or is spelled two ways. Nothing else catches either: eliminations come
    # from loser rows, so a withdrawal leaves no evidence at all, and Felix Auger-Aliassime
    # sat at 14.3% as Toronto's FAVOURITE having never hit a ball there. The producer derives
    # this after reconciling the draw against the feed (sim/tournaments.py) because only it
    # can tell the two apart; the gate's job is to refuse to ship the result.
    missing = t.get("drawnNotInField")
    if isinstance(missing, list) and missing:
        _add_finding(
            out, "output.tournament.withdrawn_player_projected",
            _tiered(f"{tour}: live tournament {name!r} still has {len(missing)} drawn "
                    f"player(s) the feed no longer lists in the event "
                    f"({', '.join(map(str, missing[:4]))}) — they withdrew without "
                    f"losing, or the draw and the feed spell them differently; either "
                    f"way the board is showing someone who is not in the tournament",
                    t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"players": list(map(str, missing)), "level": repr(t.get("level"))})
    # A live event that has stopped absorbing results is wrong in one of two ways, and the
    # gate cannot tell them apart from `end` alone, so it must not assert either: the event
    # ENDED and lost its final, freezing it live (Iasi showed live with 3 alive nine days
    # after it finished, 2026-07-27), or it is genuinely still playing and the results feed
    # has gone blind (2026-08-05: ESPN began 403-ing the live overlay, and Toronto kept
    # showing Zverev alive at 21% to win for three days after Griekspoor knocked him out).
    # The second is why this cannot be left to the tour-wide `results` freshness check —
    # that limit is 5 days and is dominated by events that have already finished, so one
    # stalled tournament never moves it. Both failures ship a board asserting that beaten
    # players are still alive, which is the thing a user actually sees.
    # `dateBasis == "start"` means the producer proved these rows carry ONE tournament stamp
    # rather than match dates (sim/tournaments._date_basis), so `end` is the event's start and
    # ageing it measures nothing. Hagen shipped 28 rows across R32/R16/QF all dated 08-03 and
    # read as five days idle while it was playing its quarter-finals. Skipped rather than given
    # a longer limit: the signal is absent, not coarse, and a slack limit would pretend
    # otherwise. Every card whose dates ARE match dates keeps the full-strength check — the
    # exemption has to be earned per card, or one bad feed would blind the whole invariant.
    if status == "live" and now is not None and t.get("dateBasis") != "start":
        age = _age_days(t.get("end"), now)
        if age is not None and age > HEALTH_MAX_LIVE_EVENT_AGE_DAYS:
            _add_finding(
                out, "output.tournament.live_progress_stale",
                _tiered(f"{tour}: live tournament {name!r} last played {age}d ago "
                        f"(max {HEALTH_MAX_LIVE_EVENT_AGE_DAYS}) — either its final "
                        f"never arrived and it is stuck 'live', or its results feed has "
                        f"stalled and eliminated players are still shown as alive",
                        t.get("level"), force=force),
                severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
                evidence={"ageDays": age, "maxDays": HEALTH_MAX_LIVE_EVENT_AGE_DAYS,
                          "lastPlayed": t.get("end"), "level": repr(t.get("level"))})
    # The mirror image: an event still labelled "upcoming" after its own dates have passed.
    # Ending while never having gone live is impossible — the results simply never joined, so
    # the card is inviting clicks on odds for a tournament that is already over. Tier-aware:
    # marquee events must not ship in that state; the long tail warns.
    if status == "upcoming" and now is not None:
        end_age = _age_days(t.get("end"), now)
        start_age = _age_days(t.get("start"), now)
        max_start_lag = (HEALTH_MAX_SLAM_UPCOMING_START_LAG_DAYS
                         if t.get("level") == "Grand Slam"
                         else HEALTH_MAX_UPCOMING_START_LAG_DAYS)
        if end_age is not None and end_age > 0:
            _add_finding(
                out, "output.tournament.upcoming_after_end",
                _tiered(f"{tour}: upcoming tournament {name!r} already ended "
                        f"({t.get('end')}, {end_age}d ago) but never went live — its "
                        f"results are not joining", t.get("level"), force=force),
                severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
                evidence={"end": t.get("end"), "ageDays": end_age,
                          "level": repr(t.get("level"))})
        elif start_age is not None and start_age > max_start_lag:
            # Advisory at every tier: ESPN start dates include qualifying, so a main draw
            # legitimately reads "upcoming" for a day or two — and a Slam for a whole week.
            _add_finding(
                out, "output.tournament.live_transition_late",
                f"{tour}: upcoming tournament {name!r} started {t.get('start')} "
                f"({start_age}d ago, max {max_start_lag}) but "
                f"has not flipped live",
                severity="warning", entity=event_entity,
                evidence={"start": t.get("start"), "ageDays": start_age,
                          "maxDays": max_start_lag})
    # A finished event has exactly one player left standing. Palermo shipped as completed
    # WITH a champion and aliveCount 32 of 32: the authoritative draw supplied the field
    # while the results supplied the eliminations, and the two never joined. Settled-draw
    # refreshes now prevent that producer failure; regressions follow the tier policy.
    if status == "completed" and champ and isinstance(alive, int) and alive > 1:
        _add_finding(
            out, "output.tournament.completed_alive_count_invalid",
            _tiered(f"{tour}: completed tournament {name!r} names champion {champ!r} "
                    f"but still reports {alive} players alive (expected 1)",
                    t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"champion": repr(champ), "aliveCount": alive, "expected": 1,
                      "level": repr(t.get("level"))})
    # `_flag_placeholders` matches a fixed word set, so the NUMBERED form ("Qualifier 30")
    # slipped through and shipped as Palermo's modelFavorite. Use the same predicate the
    # draw machinery uses to decide whether a slot names a real player.
    fav = t.get("modelFavorite")
    if fav is not None and not _is_real_name(fav):
        _add_finding(
            out, "output.tournament.favorite_placeholder",
            _tiered(f"{tour}: tournament {name!r} modelFavorite {fav!r} is a draw "
                    f"placeholder", t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"modelFavorite": repr(fav), "level": repr(t.get("level"))})
    # Surface. A non-canonical value is a builder bug (the card, the per-surface Elo blend
    # and the /style page all key off this string), so it blocks. A month-of-year GUESS is
    # tier-aware — it is what shipped the DC Open, a hard court, priced on grass Elo, but for
    # a genuinely new small event it can be the only answer we have.
    sfc, lvl = t.get("surface"), t.get("level")
    if sfc is None:
        _add_finding(
            out, "output.tournament.surface_missing",
            f"{tour}: tournament {name!r} has no surface",
            severity="error", entity=event_entity, evidence={})
    elif sfc not in _CANONICAL_SURFACES:
        _add_finding(
            out, "output.tournament.surface_invalid",
            f"{tour}: tournament {name!r} surface {sfc!r} is not a canonical surface "
            f"({'/'.join(sorted(_CANONICAL_SURFACES))})",
            severity="error", entity=event_entity,
            evidence={"surface": repr(sfc), "allowed": sorted(_CANONICAL_SURFACES)})
    if status in ("live", "upcoming") and t.get("surfaceSource") == "month":
        _add_finding(
            out, "output.tournament.surface_guessed",
            _tiered(f"{tour}: {status} tournament {name!r} surface {sfc!r} is a "
                    f"month-of-year guess — no archive or Wikipedia surface resolved",
                    lvl, force=force),
            severity=_tier_severity(lvl, force=force), entity=event_entity,
            evidence={"surface": repr(sfc), "surfaceSource": "month",
                      "level": repr(lvl)})
    # Match format drives the model's win transform. ATP Slams alone are best-of-five;
    # every WTA card and every non-Slam ATP card is best-of-three. A generic tier is
    # deliberately skipped because the resolver has not established which rule applies.
    generic_level = f"{tour.upper()} Tour"
    if lvl != generic_level:
        expected_best_of = 5 if tour == "atp" and lvl == "Grand Slam" else 3
        if t.get("bestOf") != expected_best_of:
            _add_finding(
                out, "output.tournament.match_format_invalid",
                _tiered(f"{tour}: tournament {name!r} bestOf={t.get('bestOf')!r} "
                        f"does not match {lvl!r} (expected {expected_best_of})",
                        lvl, force=force),
                severity=_tier_severity(lvl, force=force), entity=event_entity,
                evidence={"bestOf": repr(t.get("bestOf")), "expected": expected_best_of,
                          "level": repr(lvl)})
    # Level. A tier outside the vocabulary is a builder bug — some source's dialect reached a
    # card verbatim ("ATP 250 series", "C") — so it blocks regardless of tier. A tier from the
    # WRONG TOUR is the same bug with a sharper symptom: the ATP board shipped Generali Open
    # as "WTA 125" because a substring tag matched "men" inside "tournaments".
    if lvl is not None and lvl not in LEVEL_VOCAB.get(tour, frozenset()):
        other = "wta" if tour == "atp" else "atp"
        if lvl in LEVEL_VOCAB.get(other, frozenset()):
            _add_finding(
                out, "output.tournament.level_wrong_tour",
                f"{tour}: tournament {name!r} level {lvl!r} belongs to the other tour",
                severity="error", entity=event_entity,
                evidence={"name": str(name), "level": str(lvl),
                          "otherTour": other, "coverageKey": t.get("coverageKey"),
                          "espnId": t.get("espnId")})
        else:
            _add_finding(
                out, "output.tournament.level_invalid",
                f"{tour}: tournament {name!r} level {lvl!r} is not in the "
                f"{tour.upper()} level vocabulary",
                severity="error", entity=event_entity,
                evidence={"name": str(name), "level": str(lvl),
                          "allowed": sorted(LEVEL_VOCAB.get(tour, frozenset())),
                          "coverageKey": t.get("coverageKey"), "espnId": t.get("espnId")})
    elif lvl == generic_level:
        _add_finding(
            out, "output.tournament.tier_unresolved",
            _tiered(f"{tour}: {status} tournament {name!r} tier did not resolve "
                    f"(shows the generic {lvl!r})", lvl, force=force),
            severity=_tier_severity(lvl, force=force), entity=event_entity,
            evidence={"status": str(status), "level": str(lvl),
                      "name": str(name), "coverageKey": t.get("coverageKey"),
                      "espnId": t.get("espnId")})

    proj = t.get("projection") or []
    _check_projection(out, tour, name, proj, event_entity=event_entity)
    # `_flag_placeholders` tests exact membership of a fixed word set, so the NUMBERED form
    # ("Qualifier 30") walked straight through it — 22 of DC's 24 projected "players" were
    # qualifiers and nothing fired. Use the same `is_real` predicate the draw machinery and
    # the modelFavorite check use, so producer and gate cannot disagree about what a real
    # entrant is. Bracket SLOTS legitimately carry "Qualifier N"; a PROJECTION ROW never can.
    ghosts = sorted({p.get("name") for p in proj if not _is_real_name(p.get("name"))})
    if ghosts:
        shown = ", ".join(repr(g) for g in ghosts[:3]) + (" …" if len(ghosts) > 3 else "")
        _add_finding(
            out, "output.tournament.projection_placeholder",
            _tiered(f"{tour}: tournament {name!r} projection names {len(ghosts)} draw "
                    f"placeholder(s) as players ({shown})", t.get("level"), force=force),
            severity=_tier_severity(t.get("level"), force=force), entity=event_entity,
            evidence={"players": [repr(g) for g in ghosts],
                      "level": repr(t.get("level"))})

def _check_bracket_upcoming_probability_parity(
    out: list,
    tour: str,
    brackets: list,
    upcoming: list,
) -> None:
    """Require one pending match to carry one probability across bracket and schedule.

    Identity is the stable ESPN event ID plus factual bracket round plus canonical unordered
    player pair. Display names are deliberately absent from the key. Completed bracket
    prices are locked historical snapshots and therefore outside this current-price check.
    """
    pending: dict[tuple[str, str, frozenset[str]], list[dict]] = {}
    for event in brackets:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("espnId") or "").strip()
        if not event_id:
            continue
        for rnd in event.get("rounds") or []:
            round_name = str(rnd.get("round") or "").strip()
            for match in rnd.get("matches") or []:
                a, b = match.get("a"), match.get("b")
                if (match.get("winner") is not None
                        or not (_is_real_name(a) and _is_real_name(b))):
                    continue
                pair = frozenset((_player_identity_key(a), _player_identity_key(b)))
                if round_name and len(pair) == 2:
                    pending.setdefault((event_id, round_name, pair), []).append(match)

    for match in upcoming:
        if not isinstance(match, dict):
            continue
        event_id = str(match.get("espnId") or "").strip()
        round_name = str(match.get("round") or "").strip()
        a, b = match.get("playerA"), match.get("playerB")
        if not event_id or not round_name or not (_is_real_name(a) and _is_real_name(b)):
            continue
        pair = frozenset((_player_identity_key(a), _player_identity_key(b)))
        hits = pending.get((event_id, round_name, pair), [])
        if len(hits) != 1 or not _is_prob(match.get("pA")):
            continue
        bracket_match = hits[0]
        bracket_a = bracket_match.get("a")
        upcoming_p = float(match["pA"])
        expected = (upcoming_p if _player_identity_key(bracket_a) == _player_identity_key(a)
                    else 1.0 - upcoming_p)
        bracket_p = bracket_match.get("p")
        source = bracket_match.get("probSource")
        if (source != "model" or not _is_prob(bracket_p)
                or abs(float(bracket_p) - expected) > 1.1e-4):
            _add_finding(
                out, "output.bracket.upcoming_probability_mismatch",
                f"{tour}: bracket and schedule probabilities disagree for {a!r} vs "
                f"{b!r} in {round_name} (espnId {event_id})",
                severity="error",
                entity=_match_entity(
                    match, event_entity=f"espn:{event_id}", player_a=a, player_b=b),
                evidence={
                    "bracketProbabilityA": repr(bracket_p),
                    "expectedBracketProbabilityA": round(expected, 4),
                    "scheduleProbabilityA": upcoming_p,
                    "bracketProbabilitySource": repr(source),
                    "round": round_name,
                },
            )

def _check_brackets(out: list, tour: str, brackets: list, tournaments) -> None:
    """The /bracket payload must be a structurally-sound single-elim draw consistent with
    tournaments.json. A displayed bracket is reconstructed by folding an ordered draw
    forward and joining results (sim/bracket.py); the failure classes are a fold that
    doesn't halve, a winner not fed to the next round, a live event whose final is already
    decided, a prob out of range, or a champion that disagrees with tournaments.json."""
    from ...data.draws_official import official_dates_match
    from ...data.results import _name_key
    from ...sim.draws import SIZE_NAME
    # Cross-artifact joins use provider identity, never mutable sponsor/display titles.
    # A single ESPN event can be renamed between the tournament card and bracket build;
    # conversely, two different ESPN events can legitimately share the same display name.
    # Older/id-less artifacts may still join, including when ESPN identity reached only
    # one of the two payloads, but only when one candidate has BOTH date overlap and at
    # least two shared real players. Two conflicting provider identities can never be
    # overridden by that evidence, and a date window alone is not identity.
    tournament_rows = ([(index, tournament)
                        for index, tournament in enumerate(tournaments)
                        if isinstance(tournament, dict)]
                       if isinstance(tournaments, list) else [])
    tournaments_by_identity: dict[str, list[tuple[int, dict]]] = {}
    for index, tournament in tournament_rows:
        stable_entity = _event_stable_entity(tournament)
        if stable_entity:
            tournaments_by_identity.setdefault(stable_entity, []).append((index, tournament))
    matched_tournament_indexes: set[int] = set()
    bracket_matches: list[tuple[str, str, bool]] = []
    source_attachments: dict[str, dict] = {}
    for index, ev in enumerate(brackets):
        if not isinstance(ev, dict):
            _add_finding(
                out, "output.bracket.entry_invalid",
                f"{tour}: brackets.json has a non-object entry",
                severity="error", entity="artifact:brackets.json",
                evidence={"index": index, "valueType": type(ev).__name__})
            continue
        name = ev.get("name")
        event_entity = _event_entity(ev)
        stable_entity = _event_stable_entity(ev)
        provider_entity = _event_provider_entity(ev)
        exact_matches = tournaments_by_identity.get(stable_entity, []) if stable_entity else []
        if exact_matches:
            matches = exact_matches
        else:
            matches = [
                (tournament_index, tournament)
                for tournament_index, tournament in tournament_rows
                # The exact-identity branch above already handled equal provider IDs.
                # If both remaining rows carry provider IDs, they conflict and no amount
                # of circumstantial date/player evidence may join them. Evidence fallback
                # is reserved for pairs where at least one side is genuinely provider-idless.
                if not (provider_entity and _event_provider_entity(tournament))
                and _event_evidence_matches(ev, tournament)
            ]
            if len(matches) != 1:
                matches = []
        t = matches[0][1] if matches else None
        # When only tournaments.json received the provider identity, use that resolved
        # identity for every bracket finding. Otherwise a sponsor/date-derived bracket
        # fingerprint would churn even though the evidence join proved the ESPN event.
        if t is not None and provider_entity is None:
            event_entity = _event_provider_entity(t) or event_entity
        matched_tournament_indexes.update(index for index, _ in matches)
        bracket_matches.append((event_entity, _norm_name(name), t is not None))
        rounds = ev.get("rounds")
        size = ev.get("bracketSize")
        status = ev.get("status")
        if not isinstance(rounds, list) or not rounds:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} has no rounds",
                severity="error", entity=event_entity,
                evidence={"roundsType": type(rounds).__name__})
            continue
        if status not in _STATUSES:
            _add_finding(
                out, "output.bracket.status_invalid",
                f"{tour}: bracket {name!r} has bad status {status!r}",
                severity="error", entity=event_entity,
                evidence={"status": repr(status)})

        # Provenance is part of a published bracket, not optional decoration. It makes the
        # first-party/Wikipedia fallback observable and prevents a source-specific field from
        # silently becoming authoritative again. Official artifacts additionally carry the
        # date/player evidence that attached the provider id to this ESPN event.
        source, source_id, source_url = (
            ev.get("drawSource"), ev.get("drawSourceId"), ev.get("drawSourceUrl"))
        espn_id = str(ev.get("espnId") or "")
        if espn_id and source in _DRAW_SOURCE_HOSTS and (source_id or source_url):
            source_attachments[str(index)] = {
                "name": name, "espnId": espn_id, "source": source,
                "sourceId": source_id, "sourceUrl": source_url,
            }
        if source not in _DRAW_SOURCE_HOSTS:
            _add_finding(
                out, "output.bracket.draw_source_invalid",
                f"{tour}: bracket {name!r} has invalid drawSource {source!r}",
                severity="error", entity=event_entity,
                evidence={"drawSource": repr(source)})
        if not source_id:
            _add_finding(
                out, "output.bracket.draw_source_id_missing",
                f"{tour}: bracket {name!r} is missing drawSourceId",
                severity="error", entity=event_entity, evidence={})
        host = urllib.parse.urlparse(str(source_url or "")).hostname
        if source in _DRAW_SOURCE_HOSTS and host != _DRAW_SOURCE_HOSTS[source]:
            _add_finding(
                out, "output.bracket.draw_source_host_invalid",
                f"{tour}: bracket {name!r} drawSource {source!r} has URL host "
                f"{host!r} (expected {_DRAW_SOURCE_HOSTS[source]!r})",
                severity="error", entity=event_entity,
                evidence={"source": str(source), "actualHost": repr(host),
                          "expectedHost": _DRAW_SOURCE_HOSTS[source]})
        if source in ("atp", "wta"):
            if not espn_id:
                _add_finding(
                    out, "output.bracket.espn_provenance_missing",
                    f"{tour}: bracket {name!r} official draw is missing espnId provenance",
                    severity="error", entity=event_entity, evidence={})
            if source != tour:
                _add_finding(
                    out, "output.bracket.official_source_wrong_tour",
                    f"{tour}: bracket {name!r} uses the other tour's official source {source!r}",
                    severity="error", entity=event_entity,
                    evidence={"source": str(source)})
            evidence = ev.get("drawEvidencePlayers")
            field_evidence = ev.get("drawEvidenceFieldPlayers")
            if (not isinstance(evidence, int) or not isinstance(field_evidence, int)
                    or field_evidence < 2 or evidence < 2 or evidence * 4 < field_evidence * 3):
                _add_finding(
                    out, "output.bracket.field_evidence_insufficient",
                    f"{tour}: bracket {name!r} official draw matches only "
                    f"{evidence!r}/{field_evidence!r} event players (minimum 75%)",
                    severity="error", entity=event_entity,
                    evidence={"matchedPlayers": repr(evidence),
                              "fieldPlayers": repr(field_evidence), "minimumFraction": 0.75})
            if not official_dates_match(
                    ev.get("start"), ev.get("end") or ev.get("start"),
                    ev.get("drawSourceStart"), ev.get("drawSourceEnd")):
                _add_finding(
                    out, "output.bracket.calendar_evidence_insufficient",
                    f"{tour}: bracket {name!r} official draw calendar overlap is too small for "
                    f"the tournament ({ev.get('drawSourceStart')}..{ev.get('drawSourceEnd')} "
                    f"vs {ev.get('start')}..{ev.get('end')})",
                    severity="error", entity=event_entity,
                    evidence={"drawStart": ev.get("drawSourceStart"),
                              "drawEnd": ev.get("drawSourceEnd"), "eventStart": ev.get("start"),
                              "eventEnd": ev.get("end")})

        # structure: power-of-two size, rounds halve to a single final, labels match width
        if not _pow2(size):
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} bracketSize {size!r} is not a power of two",
                severity="error", entity=event_entity,
                evidence={"bracketSize": repr(size), "reason": "not_power_of_two"})
        r0 = rounds[0].get("matches") or []
        if isinstance(size, int) and 2 * len(r0) != size:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} round 0 has {len(r0)} matches (expected {size // 2})",
                severity="error", entity=event_entity,
                evidence={"round": 0, "matches": len(r0), "expected": size // 2})
        for k in range(len(rounds) - 1):
            a, b = len(rounds[k].get("matches") or []), len(rounds[k + 1].get("matches") or [])
            if b * 2 != a:
                _add_finding(
                    out, "output.bracket.geometry_invalid",
                    f"{tour}: bracket {name!r} round {k} has {a} matches, next has {b} (must halve)",
                    severity="error", entity=event_entity,
                    evidence={"round": k, "matches": a, "nextMatches": b})
        if len(rounds[-1].get("matches") or []) != 1:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} final round is not a single match",
                severity="error", entity=event_entity,
                evidence={"finalMatches": len(rounds[-1].get("matches") or [])})
        for rnd in rounds:
            ms = rnd.get("matches") or []
            want = SIZE_NAME.get(2 * len(ms))
            if want and rnd.get("round") != want:
                _add_finding(
                    out, "output.bracket.geometry_invalid",
                    f"{tour}: bracket {name!r} round {rnd.get('round')!r} mislabelled "
                    f"(expected {want!r} for {len(ms)} matches)",
                    severity="error", entity=event_entity,
                    evidence={"actualRound": repr(rnd.get("round")), "expectedRound": want,
                              "matches": len(ms)})

        # Lifecycle count and draw progression come from independent artifacts. A positive
        # self-reported count alone is not proof that the main draw started: on 2026-08-28
        # nine WTA US Open qualifying rows claimed main/R128 while none joined a node in the
        # released draw. Require at least one decided match between two real draw occupants
        # before a bracket-backed card may call itself live. Every retained result row must
        # have such a node; bracket-only walkovers can make decided progress larger than the
        # observed-row count, so the safe relation is count <= decided draw matches.
        decided_real = sum(
            1
            for rnd in rounds
            for match in (rnd.get("matches") or [])
            if match.get("winner") in ("a", "b")
            and _is_real_name(match.get("a"))
            and _is_real_name(match.get("b"))
        )
        if (t and t.get("status") == "live"
                and isinstance(t.get("mainDrawMatchCount"), int)
                and not isinstance(t.get("mainDrawMatchCount"), bool)
                and t.get("mainDrawMatchCount") > decided_real):
            _add_finding(
                out, "output.bracket.live_without_draw_progress",
                f"{tour}: live tournament {name!r} reports "
                f"{t.get('mainDrawMatchCount')} main-draw result(s), but its released "
                f"bracket corroborates only {decided_real} decided match(es) between "
                "two real entrants",
                severity="error", entity=event_entity,
                evidence={
                    "mainDrawMatchCount": t.get("mainDrawMatchCount"),
                    "decidedRealBracketMatches": decided_real,
                    "status": "live",
                })

        # drawSize: count round-0 slots the way tournaments.json drawSize does — field_pool is
        # the non-null complete-draw slots, which INCLUDES unresolved qualifier placeholders (an
        # early-captured draw legitimately carries them; the frozen-wiki capture never backfills
        # the names). Only byes (null) are excluded on both sides. Excluding placeholders here
        # would false-positive against drawSize (Gstaad's early draw, 2026-07-13).
        nonbye0 = [p for m in r0 for p in (m.get("a"), m.get("b")) if p is not None]
        settled_draw = bool(nonbye0) and all(_is_real_name(player) for player in nonbye0)
        ds = ev.get("drawSize")
        if isinstance(ds, int) and len(nonbye0) != ds:
            _add_finding(
                out, "output.bracket.geometry_invalid",
                f"{tour}: bracket {name!r} has {len(nonbye0)} round-0 slots but drawSize {ds}",
                severity="error", entity=event_entity,
                evidence={"roundZeroSlots": len(nonbye0), "drawSize": ds})
        if t and isinstance(t.get("drawSize"), int) and ds != t.get("drawSize"):
            _add_finding(
                out, "output.bracket.tournament_draw_size_mismatch",
                f"{tour}: bracket {name!r} drawSize {ds} != tournaments.json {t.get('drawSize')}",
                severity="error", entity=event_entity,
                evidence={"bracketDrawSize": ds, "tournamentDrawSize": t.get("drawSize")})

        # final decidedness mirrors the tournament rule (no live event names a champion)
        final_m = (rounds[-1].get("matches") or [{}])[0]
        fw = final_m.get("winner")
        if status == "completed" and fw is None:
            _add_finding(
                out, "output.bracket.completed_final_undecided",
                f"{tour}: completed bracket {name!r} final match is undecided",
                severity="error", entity=event_entity, evidence={})
        if status in ("live", "upcoming") and fw is not None:
            _add_finding(
                out, "output.bracket.final_decided_prematurely",
                f"{tour}: {status} bracket {name!r} final match already decided",
                severity="error", entity=event_entity,
                evidence={"status": status, "winner": repr(fw)})

        # per-match: winner validity, prob range, prob/source presence, upset orientation,
        # and feeder consistency (a decided winner must seat in the right next-round slot)
        for k, rnd in enumerate(rounds):
            ms = rnd.get("matches") or []
            for j, m in enumerate(ms):
                match_entity = _match_entity(
                    m,
                    event_entity=event_entity,
                    player_a=m.get("a"),
                    player_b=m.get("b"),
                    fallback=f"round:{k}:match:{j}",
                )
                w = m.get("winner")
                if w not in ("a", "b", None):
                    _add_finding(
                        out, "output.bracket.winner_value_invalid",
                        f"{tour}: bracket {name!r} winner {w!r} not in a/b/null",
                        severity="error", entity=match_entity,
                        evidence={"winner": repr(w)})
                elif w in ("a", "b") and not m.get(w):
                    _add_finding(
                        out, "output.bracket.winner_side_missing",
                        f"{tour}: bracket {name!r} decided match has null winning side {w!r}",
                        severity="error", entity=match_entity,
                        evidence={"winner": w})
                p, src = m.get("p"), m.get("probSource")
                if p is not None and not _is_prob(p):
                    _add_finding(
                        out, "output.bracket.probability_invalid",
                        f"{tour}: bracket {name!r} match p={p!r} out of [0,1]",
                        severity="error", entity=match_entity,
                        evidence={"probability": repr(p)})
                if src not in ("logged", "model", None):
                    _add_finding(
                        out, "output.bracket.probability_source_invalid",
                        f"{tour}: bracket {name!r} probSource {src!r} invalid",
                        severity="error", entity=match_entity,
                        evidence={"probabilitySource": repr(src)})
                if (p is None) != (src is None):
                    _add_finding(
                        out, "output.bracket.probability_source_mismatch",
                        f"{tour}: bracket {name!r} p/probSource presence mismatch (p={p!r}, src={src!r})",
                        severity="error", entity=match_entity,
                        evidence={"probability": repr(p), "probabilitySource": repr(src)})
                if (settled_draw and w is None and p is None
                        and _is_real_name(m.get("a")) and _is_real_name(m.get("b"))):
                    _add_finding(
                        out, "output.bracket.pending_probability_missing",
                        f"{tour}: bracket {name!r} has no model probability for pending "
                        f"real entrants {m.get('a')!r} vs {m.get('b')!r}",
                        severity="error", entity=match_entity,
                        evidence={"round": rnd.get("round"),
                                  "players": [m.get("a"), m.get("b")]})
                up = m.get("upset")
                if up is not None and p is not None and w in ("a", "b"):
                    won_p = p if w == "a" else 1.0 - p
                    if bool(up) != (won_p < 0.5):
                        _add_finding(
                            out, "output.bracket.upset_flag_mismatch",
                            f"{tour}: bracket {name!r} upset flag disagrees with p ({p})",
                            severity="error", entity=match_entity,
                            evidence={"probability": p, "winner": w, "upset": repr(up)})
                if w in ("a", "b") and k + 1 < len(rounds):
                    won = m.get(w)
                    nxt_ms = rounds[k + 1].get("matches") or []
                    nxt = nxt_ms[j // 2] if j // 2 < len(nxt_ms) else None
                    side = (nxt.get("a") if j % 2 == 0 else nxt.get("b")) if nxt else None
                    if side is not None and won is not None and _norm_name(side) != _norm_name(won):
                        _add_finding(
                            out, "output.bracket.advancement_mismatch",
                            f"{tour}: bracket {name!r} round {k} winner {won!r} not fed to next round (found {side!r})",
                            severity="error", entity=match_entity,
                            evidence={"round": k, "winner": repr(won),
                                      "nextRoundPlayer": repr(side)})

        # champion agrees with this payload AND tournaments.json. Compare on the
        # accent/punct-insensitive name key, not casefold: the bracket slot carries the
        # elo-canonical spelling while `champion` comes from the results winner_name, so a
        # champion with a diacritic (Nosková vs Noskova) is the SAME player, not a mismatch.
        if status == "completed" and fw in ("a", "b"):
            champ = final_m.get(fw)
            if ev.get("champion") and champ and _name_key(champ) != _name_key(ev.get("champion")):
                _add_finding(
                    out, "output.bracket.champion_mismatch",
                    f"{tour}: bracket {name!r} final winner {champ!r} != champion {ev.get('champion')!r}",
                    severity="error", entity=event_entity,
                    evidence={"finalWinner": repr(champ),
                              "bracketChampion": repr(ev.get("champion"))})
            if t and t.get("champion") and champ and _name_key(champ) != _name_key(t.get("champion")):
                _add_finding(
                    out, "output.bracket.tournament_champion_mismatch",
                    f"{tour}: bracket {name!r} champion {champ!r} != tournaments.json {t.get('champion')!r}",
                    severity="error", entity=event_entity,
                    evidence={"bracketChampion": repr(champ),
                              "tournamentChampion": repr(t.get("champion"))})

        _flag_placeholders(out, tour, f"bracket {name!r}",
                           (p for rnd in rounds for m in (rnd.get("matches") or [])
                            for p in (m.get("a"), m.get("b"))),
                           entity=event_entity, allow_numbered=True)

    from ..draws import duplicate_draw_source_incidents
    for identity, detail in duplicate_draw_source_incidents(source_attachments):
        _add_finding(
            out, "output.draw_source.duplicate_attachment",
            f"{tour}: brackets.json {detail}",
            severity="error", entity=f"draw-source:{identity}",
            evidence={"artifact": "brackets.json", "detail": detail})

    # cross-presence: hasBracket <=> a brackets.json entry (both directions)
    if isinstance(tournaments, list):
        for index, t in tournament_rows:
            if t.get("hasBracket") and index not in matched_tournament_indexes:
                _add_finding(
                    out, "output.bracket.entry_missing",
                    f"{tour}: tournaments.json {t.get('name')!r} hasBracket but no brackets.json entry",
                    severity="error", entity=_event_entity(t), evidence={})
    if tournament_rows:
        for event_entity, normalized_name, matched in bracket_matches:
            if not matched:
                _add_finding(
                    out, "output.bracket.tournament_missing",
                    f"{tour}: brackets.json entry {normalized_name!r} "
                    "has no tournaments.json event",
                    severity="error", entity=event_entity, evidence={})
