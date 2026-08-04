"""drawStatus propagation through project_tournament / project_upcoming (synthetic, no net).

Pins the honest label the web reads: a live event runs "real" when its draw is known
(Wikipedia slots, or ESPN matchups that seat the whole frontier), "partial"/"seeded" when
only some / none of the frontier is posted, and "final" once complete. A Wikipedia draw
turns an otherwise-"seeded" board "real" and surfaces a not-yet-started event as "upcoming".
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.sim.bracket import is_real
from tennis_model.sim.tournaments import (
    _dedup_by_display_name,
    build_tournaments,
    project_tournament,
    project_upcoming,
)

_R = {f"P{i}": 2000.0 - 30.0 * i for i in range(16)}   # P0 strongest .. P15 weakest


class _Pred:
    class _Elo:
        def __init__(self, r):
            self.r = r
            self.overall = dict(r)          # names -> rating (build_tournaments' top_set source)

        def blended(self, name, surf):
            return self.r.get(name, 1500.0)

        def elo(self, name):
            return self.r.get(name, 1500.0)

    def __init__(self, r):
        self.elo = self._Elo(r)

    def win_prob_matrix(self, players, surface="Hard", best_of=3,
                        indoor=False, tier_k=1.0, event=None):
        n = len(players)
        P = np.full((n, n), 0.5)
        for i in range(n):
            for j in range(n):
                if i != j:
                    d = self.elo.r.get(players[i], 1500.0) - self.elo.r.get(players[j], 1500.0)
                    P[i, j] = 1.0 / (1.0 + 10.0 ** (-d / 400.0))
        return P


_PRED = _Pred(_R)


def _g(add_final=False):
    """A live 'Test Open': 8 first-round results (P0..P7 beat P8..P15), no final."""
    rows = [dict(tourney_name="Test Open", date=pd.Timestamp("2026-08-03"), round="R64",
                 winner_name=f"P{i}", loser_name=f"P{8 + i}", surface_b="Hard",
                 best_of=3, tourney_level="250") for i in range(8)]
    if add_final:
        rows.append(dict(tourney_name="Test Open", date=pd.Timestamp("2026-08-09"), round="F",
                         winner_name="P0", loser_name="P1", surface_b="Hard",
                         best_of=3, tourney_level="250"))
    return pd.DataFrame(rows)


def _project(matchups, wiki_draw=None, add_final=False):
    return project_tournament(_PRED, "Test Open", _g(add_final), "atp", known=set(),
                              top_set=None, espn_fields=None, resolve=lambda n: n,
                              matchups=matchups, tournament_draw=wiki_draw, n_sims=200, seed=1)


def test_status_real_partial_seeded_final_from_espn():
    alive_pairs = [("P0", "P1"), ("P2", "P3"), ("P4", "P5"), ("P6", "P7")]
    assert _project(alive_pairs)["drawStatus"] == "real"      # full frontier posted
    assert _project([("P0", "P1")])["drawStatus"] == "partial"  # 1 pair + 6 singles = 7 units
    assert _project([])["drawStatus"] == "seeded"             # nothing posted -> rating seed
    fin = _project([], add_final=True)
    assert fin["status"] == "completed" and fin["drawStatus"] == "final"
    print("ok test_status_real_partial_seeded_final_from_espn")


def test_live_and_upcoming_tier_resolution_receive_stable_id(monkeypatch):
    """Card builders must not discard the identity needed to bridge a sponsor rename."""
    from tennis_model.sim import tournaments as tournament_module

    calls = []

    def level(tour, name, archive_level=None, event_id=None):
        calls.append((tour, name, archive_level, event_id))
        return "Masters 1000"

    monkeypatch.setattr(tournament_module, "resolve_level", level)
    live = project_tournament(
        _PRED, "Toronto", _g(), "atp", known=set(), top_set=None,
        espn_fields=None, resolve=lambda name: name, matchups=[],
        espn_id="421-2026", n_sims=20, seed=1,
    )
    upcoming = project_upcoming(
        _PRED, "National Bank Open presented by Rogers",
        {"slots": list(_R)[:8], "start": "2026-08-02", "end": "2026-08-14"},
        "atp", _g(), known=set(), resolve=lambda name: name,
        espn_id="421-2026", n_sims=20, seed=1,
    )

    assert live["level"] == upcoming["level"] == "Masters 1000"
    assert [call[3] for call in calls] == ["421-2026", "421-2026"]
    print("ok test_live_and_upcoming_tier_resolution_receive_stable_id")


def _grp(name, players, start="2026-07-20", days=4, eid=None):
    """A results group: `players` pairs, one match per day from `start`."""
    rows = []
    for i, (w, l) in enumerate(players):
        rows.append(dict(tourney_name=name, espn_id=eid,
                         date=pd.Timestamp(start) + pd.Timedelta(days=i % days),
                         round="R32", winner_name=w, loser_name=l,
                         surface_b="Clay", best_of=3, tourney_level="250"))
    return pd.DataFrame(rows)


def test_coalesce_merges_one_event_split_across_two_names():
    """The Bad Homburg failure at its root. `recent_tournaments` groups by raw tourney_name,
    so one event enters TWICE when its sources disagree about the title — the results feed
    uses the archive city, ESPN the sponsor version. On 2026-07-09 that shipped two WTA cards
    for one tournament, the second a nine-player fragment with the finalists swapped.
    Deduping the CARDS afterwards hid it; one projection was still built on half an event."""
    from tennis_model.sim.tournaments import _coalesce_groups

    class _R:
        def id_of(self, name):
            return None

    shared = [("A Player", "B Player"), ("C Player", "D Player"), ("E Player", "F Player")]
    espn = ("Bad Homburg Open powered by Solarwatt",
            _grp("Bad Homburg Open powered by Solarwatt", shared, eid="1-2026"))
    archive = ("Bad Homburg", _grp("Bad Homburg", shared + [("G Player", "H Player")]))
    out = _coalesce_groups([espn, archive], _R())
    assert len(out) == 1, [n for n, _g, _e in out]
    name, merged, eid = out[0]
    assert eid == "1-2026"                      # identity survives the merge
    assert name == "Bad Homburg"                # the FULLER record names it
    assert len(_real_players_of(merged)) == 8   # both partial records, one event

    # two groups with the SAME id merge without needing any name or player evidence
    a = ("Nordea Open", _grp("Nordea Open", shared[:1], eid="306-2026"))
    b = ("Bastad", _grp("Bastad", [("Z One", "Z Two")], eid="306-2026"))
    out2 = _coalesce_groups([a, b], _R())
    assert len(out2) == 1 and out2[0][2] == "306-2026"
    print("ok test_coalesce_merges_one_event_split_across_two_names")


def test_coalesce_merges_one_day_transient_fragment_on_match_evidence():
    """A provider can briefly emit a second, id-less group for one event for only one day.

    Production did this to Toronto as ``Masters`` on 2026-08-04: the fragment shared real
    matches with ``421-2026`` but its zero-day span failed the old two-day minimum and shipped
    as a second generic-tier card. Same-day observations plus three shared real players and an
    exact matchup are sufficient identity evidence; names remain irrelevant.
    """
    from tennis_model.sim.tournaments import _coalesce_groups

    class _R:
        def id_of(self, name):
            return None

    stable_pairs = [
        ("A Player", "B Player"),
        ("C Player", "D Player"),
        ("E Player", "F Player"),
    ]
    stable = ("Stable Event", _grp(
        "Stable Event", stable_pairs, start="2026-08-04", days=1, eid="421-2026"))
    fragment = ("Unrelated Provider Label", _grp(
        "Unrelated Provider Label", stable_pairs[:2], start="2026-08-04", days=1))

    out = _coalesce_groups([stable, fragment], _R())

    assert len(out) == 1
    assert out[0][2] == "421-2026"
    assert len(out[0][1]) == len(stable_pairs)

    # Four shared entrants without one shared matchup are not identity evidence, even on
    # the same day. This protects concurrent events and makes the positive rule non-name-based.
    no_match = ("Other Event", _grp(
        "Other Event",
        [("A Player", "C Player"), ("B Player", "D Player")],
        start="2026-08-04", days=1,
    ))
    assert len(_coalesce_groups([stable, no_match], _R())) == 2
    print("ok test_coalesce_merges_one_day_transient_fragment_on_match_evidence")


def _real_players_of(g):
    from tennis_model.sim.tournaments import _real_players
    return _real_players(g)


def test_coalesce_refuses_to_merge_concurrent_distinct_events():
    """The negative control, and the reason a wrong merge is worse than none: it corrupts a
    projection rather than mislabelling a card. Two real tournaments running the same week
    cannot share three players — a player plays one event at a time — and placeholders are
    numbered PER DRAW, so 'sharing' Qualifier N is evidence of nothing (issue #9, where
    Washington and Memphis were reported as one renamed event over 20 shared placeholders)."""
    from tennis_model.sim.tournaments import _coalesce_groups

    class _R:
        def id_of(self, name):
            return None

    dc = ("Mubadala DC Open", _grp("Mubadala DC Open",
                                   [("A One", "A Two"), ("A Three", "A Four")],
                                   start="2026-07-27", eid="888-2026"))
    memphis = ("Memphis", _grp("Memphis", [("B One", "B Two"), ("B Three", "B Four")],
                               start="2026-07-27"))
    assert len(_coalesce_groups([dc, memphis], _R())) == 2      # disjoint fields -> separate

    # sharing only PLACEHOLDERS must not merge either
    ph = [(f"Qualifier {i}", f"Qualifier {i + 9}") for i in range(1, 5)]
    q1 = ("Event One", _grp("Event One", ph, start="2026-07-27", eid="1-2026"))
    q2 = ("Event Two", _grp("Event Two", ph, start="2026-07-27"))
    assert len(_coalesce_groups([q1, q2], _R())) == 2

    # an id-less group matching TWO id-bearing ones is ambiguous -> left alone
    shared = [("S One", "S Two"), ("S Three", "S Four"), ("S Five", "S Six")]
    e1 = ("Ev One", _grp("Ev One", shared, start="2026-07-20", eid="1-2026"))
    e2 = ("Ev Two", _grp("Ev Two", shared, start="2026-07-20", eid="2-2026"))
    orphan = ("Ev Orphan", _grp("Ev Orphan", shared, start="2026-07-20"))
    assert len(_coalesce_groups([e1, e2, orphan], _R())) == 3
    print("ok test_coalesce_refuses_to_merge_concurrent_distinct_events")


def test_coalesce_refuses_to_merge_events_that_share_players_but_no_match():
    """The WTA Wimbledon/Nordea production shape: an id-less completed Slam overlapped
    Nordea's ESPN calendar and shared nine players who entered both events in successive
    weeks, but not one actual matchup. Player overlap is not event identity."""
    from tennis_model.sim.tournaments import _coalesce_groups

    class _R:
        def id_of(self, name):
            return None

    shared = [f"Shared {i}" for i in range(9)]
    wimbledon_pairs = [(shared[i], f"Slam Opp {i}") for i in range(9)]
    nordea_pairs = [(shared[i], f"Nordea Opp {i}") for i in range(9)]
    wimbledon = ("Wimbledon", _grp("Wimbledon", wimbledon_pairs,
                                    start="2026-07-06", days=9))
    nordea = ("Nordea Open", _grp("Nordea Open", nordea_pairs,
                                  start="2026-07-11", days=9, eid="306-2026"))

    out = _coalesce_groups([wimbledon, nordea], _R())
    assert len(out) == 2, [(name, eid) for name, _g, eid in out]
    print("ok test_coalesce_refuses_to_merge_events_that_share_players_but_no_match")


def test_an_event_is_over_when_its_calendar_says_so_even_without_a_final():
    """Iasi sat 'live' with three players alive for NINE DAYS after it ended, and Hamburg for
    two, because completion keyed ONLY on a round-'F' row. A results feed that drops the final
    stranded the card at the top of the board forever. Anchored on the DATA's max date, not
    wall-clock: a frozen pipeline must not start declaring live events finished."""
    g = _g(add_final=False)                      # 8 R64 results, no final
    dmax = pd.Timestamp("2026-08-20")            # well past the event

    over = project_tournament(_PRED, "Test Open", g, "atp", known=set(), top_set=None,
                              espn_fields=None, resolve=lambda n: n, matchups=[],
                              event_end="2026-08-09", dmax=dmax, n_sims=60, seed=1)
    assert over["status"] == "completed"
    assert over["finalRecorded"] is False         # ...and it says so
    assert over["champion"] is None               # the champion is genuinely unknown
    assert over["aliveCount"] == 8                # no champion -> no structural collapse to 1

    # inside the grace window it is still live — a final can be a day late
    still = project_tournament(_PRED, "Test Open", g, "atp", known=set(), top_set=None,
                               espn_fields=None, resolve=lambda n: n, matchups=[],
                               event_end="2026-08-19", dmax=dmax, n_sims=60, seed=1)
    assert still["status"] == "live", still["status"]
    # a pending matchup means it is genuinely still running, whatever the calendar says
    busy = project_tournament(_PRED, "Test Open", g, "atp", known=set(), top_set=None,
                              espn_fields=None, resolve=lambda n: n,
                              matchups=[("P0", "P2")], event_end="2026-08-09", dmax=dmax,
                              n_sims=60, seed=1)
    assert busy["status"] == "live"
    # and a real final still wins outright, with finalRecorded True
    done = project_tournament(_PRED, "Test Open", _g(add_final=True), "atp", known=set(),
                              top_set=None, espn_fields=None, resolve=lambda n: n,
                              matchups=[], n_sims=60, seed=1)
    assert done["status"] == "completed" and done["finalRecorded"] is True
    assert done["champion"] == "P0" and done["aliveCount"] == 1
    print("ok test_an_event_is_over_when_its_calendar_says_so_even_without_a_final")


def test_coalesce_defects_found_in_review():
    """Three defects my own adversarial re-read caught before this shipped. Each is silent —
    none would have failed a test or shown up in a rebuild of this week's board."""
    from tennis_model.sim.tournaments import _coalesce_groups, _real_players

    class _R:
        def id_of(self, name):
            return None

    # (1) SILENT EVENT LOSS. Id-less groups were keyed by normalised display name and
    # ASSIGNED, not appended, so two feeds spelling one name differently collided and the
    # second overwrote the first — an event vanished from the board entirely.
    a = ("Bad Homburg", _grp("Bad Homburg", [("A One", "A Two")], start="2026-06-20"))
    b = ("Bad  Homburg", _grp("Bad  Homburg", [("B One", "B Two")], start="2026-06-20"))
    assert len(_coalesce_groups([a, b], _R())) == 2, "an event was silently dropped"

    # (2) ORDER-DEPENDENT MERGE. The hit search read `by_id` live, so an id-less group could
    # match a synthetic entry added by an EARLIER id-less group and merge two unidentified
    # events — undocumented, and dependent on iteration order.
    shared = [("S One", "S Two"), ("S Three", "S Four"), ("S Five", "S Six")]
    x = ("Ev X", _grp("Ev X", shared, start="2026-06-20"))
    y = ("Ev Y", _grp("Ev Y", shared, start="2026-06-20"))
    assert len(_coalesce_groups([x, y], _R())) == 2, "two id-less groups were merged"

    # (3) QUALIFYING ROWS AS FALSE EVIDENCE. A player who loses qualifying at one event and
    # plays the main draw at another the same week appears in both. Counting them could
    # manufacture three "shared players" between a Challenger and a main-tour event.
    q = pd.DataFrame([
        dict(tourney_name="E", date=pd.Timestamp("2026-07-20"), round="Q1",
             winner_name="Q Win", loser_name="Q Lose", draw_level="main"),
        dict(tourney_name="E", date=pd.Timestamp("2026-07-21"), round="R32",
             winner_name="Main One", loser_name="Main Two", draw_level="main"),
    ])
    assert _real_players(q) == {"Main One", "Main Two"}, _real_players(q)
    print("ok test_coalesce_defects_found_in_review")


def test_a_renamed_event_still_finds_its_cached_draw(tmp_path, monkeypatch):
    """The DC Open failure, end to end.

    ESPN renamed "Mubadala Citi DC Open" -> "Mubadala DC Open" mid-tournament while the id
    stayed 888-2026. Every cache keyed on the name was orphaned: `wiki.get(name)` missed, so
    draw provenance and `bracketSize` came back null and a live ATP/WTA 500 shipped with no draw at
    all. Resolution now goes through the id, recovered from the espnId stamped INSIDE the
    cached entry (name containment cannot bridge a word inserted mid-title).
    """
    from tennis_model.sim import tournaments as tsm

    slots = [f"P{i}" for i in range(16)]
    monkeypatch.setattr(tsm, "_load_tournament_draws", lambda tour: {
        "Mubadala Citi DC Open": {                       # OLD name — the orphaned key
            "slots": slots, "seeds": {}, "bestOf": 3, "espnId": "888-2026",
            "start": "2026-07-25", "end": "2026-08-03",
            "source": "wikipedia", "sourceId": "DC draw",
            "sourceUrl": "https://en.wikipedia.org/wiki/2026_Mubadala_Citi_DC_Open"},
    })
    monkeypatch.setattr(tsm, "_load_fields", lambda tour: {})
    monkeypatch.setattr(tsm, "_load_upcoming", lambda tour: {})
    # raising=False so this test still RUNS against a build without the identity layer, and
    # therefore fails on the real assertion (no bracket) rather than on a missing attribute
    monkeypatch.setattr(tsm, "load_registry", lambda tour: {"events": {}}, raising=False)
    # bracket PRICING is a separate concern (and needs a fuller predictor stub); this test is
    # about whether the cached draw is RESOLVED at all
    monkeypatch.setattr(tsm, "_price_event_bracket", lambda *a, **k: None)

    # the results frame carries the NEW name, and its rows carry the id
    rows = [dict(tourney_name="Mubadala DC Open", espn_id="888-2026",
                 date=pd.Timestamp("2026-07-27"), round="R16",
                 winner_name=f"P{i}", loser_name=f"P{8 + i}", surface_b="Hard",
                 best_of=3, tourney_level="500") for i in range(8)]
    out = build_tournaments(_PRED, pd.DataFrame(rows), "atp", n_sims=60, seed=1)
    card = next(t for t in out if "DC Open" in t["name"])
    # the substantive assertion first, so a build without the identity layer fails HERE —
    # on the draw being orphaned — rather than on a field it simply doesn't emit yet
    assert card["bracketSize"] == 16, card          # the draw was FOUND despite the rename
    assert card["drawSourceUrl"], "draw provenance lost — the cached entry was not resolved"
    assert card["drawStatus"] == "real"
    assert card["espnId"] == "888-2026"
    # ...and the same event is not ALSO emitted by the pre-start loop under its old name
    assert len([t for t in out if "DC Open" in t["name"]]) == 1, [t["name"] for t in out]
    print("ok test_a_renamed_event_still_finds_its_cached_draw")


def test_month_guessed_rows_never_pose_as_an_archive_surface():
    """A month-of-year guess must not be recycled as the authoritative archive value.

    `results.clean` stamps `surface_src`, but the live path took `surface_b.mode()` outright,
    so July's Grass guess became "the archive says Grass" and short-circuited the Wikipedia
    tier that knew the DC Open is a hard court — self-fulfilling, and it never healed."""
    from tennis_model.sim.tournaments import _known_surface

    guessed = pd.DataFrame({"surface_b": ["Grass", "Grass"], "surface_src": ["month", "month"]})
    assert _known_surface(guessed) == (None, None)    # nothing KNOWN -> defer to the chain
    mixed = pd.DataFrame({"surface_b": ["Grass", "Hard"], "surface_src": ["month", "wiki"]})
    # the known row wins over the guess AND reports its own provenance, not a blanket
    # "archive" — surfaceSource decides whether a wrong surface blocks the deploy
    assert _known_surface(mixed) == ("Hard", "wiki")
    real = pd.DataFrame({"surface_b": ["Clay"], "surface_src": ["archive"]})
    assert _known_surface(real) == ("Clay", "archive")
    # frames with no provenance column (fixtures, pre-upgrade caches) keep the old behaviour
    assert _known_surface(pd.DataFrame({"surface_b": ["Clay"]})) == ("Clay", "archive")
    assert _known_surface(pd.DataFrame({"other": [1]})) == (None, None)

    # ...and every caller must UNPACK it. _archive_attrs forwards its surface straight into
    # resolve_surface_info as archive_surface, so returning the pair whole shipped a literal
    # ('Hard', 'archive') tuple as WTA Memphis's surface — caught only by rebuilding real cards.
    from tennis_model.sim.tournaments import _archive_attrs
    frame = pd.DataFrame({"tourney_name": ["Memphis Classic"], "surface_b": ["Hard"],
                          "surface_src": ["archive"], "best_of": [3]})
    a_surf, _lvl, _bo = _archive_attrs(frame, "The Memphis Classic")
    assert a_surf == "Hard", a_surf
    assert isinstance(a_surf, str)
    print("ok test_month_guessed_rows_never_pose_as_an_archive_surface")


def test_placeholder_heavy_draw_withholds_odds_entirely():
    """A favourite computed against default-rated ghosts is not a weaker estimate, it is a
    wrong one: the DC Open shipped 22 of 24 projected "players" as `Qualifier N` and inflated
    the real favourite to 53-56%. Below a real majority the card ships schedule info only —
    the SAME threshold that already withholds the bracket, so the two cannot disagree."""
    from tennis_model.sim.tournaments import projection_is_meaningful

    assert projection_is_meaningful(["A", "B", "C", "D"])
    assert projection_is_meaningful(["A", "B", "Qualifier 1", "Qualifier 2"])   # exactly half
    assert not projection_is_meaningful(["A", "Qualifier 1", "Qualifier 2", "Qualifier 3"])
    assert not projection_is_meaningful([f"Qualifier {i}" for i in range(8)])
    assert not projection_is_meaningful([])

    # end to end: a mostly-placeholder wiki draw ships no odds and no favourite...
    ph = ["A", "B"] + [f"Qualifier {i}" for i in range(1, 15)]
    t = _project([], wiki_draw={"slots": ph, "seeds": {}, "bestOf": 3})
    assert t["projection"] == [] and t["modelFavorite"] is None
    assert t["drawSize"] == 16                       # the card still carries schedule facts
    # ...while a resolved draw prices normally and publishes only real names
    real = [f"P{i}" for i in range(16)]
    t2 = _project([], wiki_draw={"slots": real, "seeds": {}, "bestOf": 3})
    assert t2["projection"] and t2["modelFavorite"] in real
    assert all(is_real(p["name"]) for p in t2["projection"])
    print("ok test_placeholder_heavy_draw_withholds_odds_entirely")


def test_projection_rows_never_name_a_placeholder():
    """Even above the majority threshold, an unresolved slot must not appear AS a player —
    it still occupies a real draw slot in the simulation, it just isn't anybody."""
    slots = [f"P{i}" for i in range(12)] + [f"Qualifier {i}" for i in range(1, 5)]
    t = _project([], wiki_draw={"slots": slots, "seeds": {}, "bestOf": 3})
    assert t["projection"], "a majority-real draw should still be priced"
    names = [p["name"] for p in t["projection"]]
    assert all(is_real(n) for n in names), names
    assert is_real(t["modelFavorite"])
    print("ok test_projection_rows_never_name_a_placeholder")


def test_completed_event_reports_exactly_one_player_alive():
    """A finished knockout has one player standing. Deriving that by `field_pool -
    eliminated` depends on every entrant's two identities cancelling, which real data breaks:
    Umag shipped 2 (one player under two spellings) and Palermo 32 (a frozen placeholder
    draw). Even this synthetic fixture leaks 7 — P2..P7 win a round and never appear as a
    loser, because the middle rounds simply aren't in the frame."""
    fin = _project([], add_final=True)
    assert fin["status"] == "completed" and fin["champion"] == "P0"
    assert fin["aliveCount"] == 1, fin["aliveCount"]
    # the retrospective field is still the FULL draw, not just the survivor
    assert fin["drawSize"] == 16
    # a live event still counts survivors the ordinary way
    live = _project([])
    assert live["status"] == "live" and live["aliveCount"] == 8, live["aliveCount"]
    print("ok test_completed_event_reports_exactly_one_player_alive")


def test_completed_projection_excludes_qualifying_field():
    """A completed Slam still projects its 128-player main draw, not qualifying rows."""
    rows = []
    for i in range(64):
        rows.append(dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-01"),
                         round="R128", winner_name=f"M{i}", loser_name=f"M{64 + i}",
                         surface_b="Grass", best_of=3, tourney_level="G", draw_level="main"))
    rows.append(dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-11"),
                     round="F", winner_name="M0", loser_name="M1", surface_b="Grass",
                     best_of=3, tourney_level="G", draw_level="main"))
    for i in range(20):
        rows.append(dict(tourney_name="Test Slam", date=pd.Timestamp("2026-06-25"),
                         round="Q1", winner_name=f"Q{i}", loser_name=f"Q{20 + i}",
                         surface_b="Grass", best_of=3, tourney_level="Q",
                         draw_level="main"))  # legacy/source default: provenance is unreliable

    t = project_tournament(_PRED, "Test Slam", pd.DataFrame(rows), "wta", known=set(),
                           top_set=None, n_sims=10, seed=1)
    assert t["status"] == "completed" and t["drawSize"] == 128
    assert t["champion"] == "M0" and all(p["name"].startswith("M") for p in t["projection"])
    print("ok test_completed_projection_excludes_qualifying_field")


def test_completed_projection_keeps_authoritative_wiki_field():
    """Completion must not discard a known 128-player draw for a dirty 133-name frame."""
    rows = [dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-01"),
                 round="R128", winner_name=f"M{i}", loser_name=f"M{65 + i}",
                 surface_b="Grass", best_of=3, tourney_level="G", draw_level="main")
            for i in range(65)]
    rows += [
        dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-02"), round="R128",
             winner_name="Extra A", loser_name="Extra B", surface_b="Grass", best_of=3,
             tourney_level="G", draw_level="main"),
        dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-11"), round="F",
             winner_name="M0", loser_name="M1", surface_b="Grass", best_of=3,
             tourney_level="G", draw_level="main"),
    ]
    wiki = {"slots": [f"M{i}" for i in range(128)], "bestOf": 3}
    t = project_tournament(_PRED, "Test Slam", pd.DataFrame(rows), "wta", known=set(),
                           top_set=None, resolve=lambda n: n, tournament_draw=wiki,
                           n_sims=10, seed=1)
    assert t["status"] == "completed" and t["drawSize"] == 128
    assert t["champion"] == "M0" and all(p["name"].startswith("M") for p in t["projection"])
    print("ok test_completed_projection_keeps_authoritative_wiki_field")


def test_completed_projection_withholds_an_unreconciled_wiki_bracket():
    """A cached ordered draw can be real-player-complete yet have stale ordering. If its
    result fold cannot reach the recorded final, keep the factual card but do not publish an
    apparently authoritative bracket whose final the strict serving gate must reject."""
    rows = [
        dict(tourney_name="Test Open", date=pd.Timestamp("2026-07-01"), round=rnd,
             winner_name=winner, loser_name=loser, surface_b="Hard", best_of=3,
             tourney_level="250", draw_level="main")
        for rnd, winner, loser in (
            ("QF", "A", "B"), ("QF", "C", "D"), ("QF", "E", "F"), ("QF", "G", "H"),
            ("SF", "A", "C"), ("SF", "E", "G"), ("F", "A", "E"),
        )
    ]
    good = project_tournament(
        _PRED, "Test Open", pd.DataFrame(rows), "atp", known=set(), top_set=None,
        resolve=lambda n: n, tournament_draw={"slots": list("ABCDEFGH"), "bestOf": 3},
        n_sims=20, seed=1,
    )
    assert good["bracket"][-1]["matches"][0]["winner"] == "a"

    stale = project_tournament(
        _PRED, "Test Open", pd.DataFrame(rows), "atp", known=set(), top_set=None,
        resolve=lambda n: n, tournament_draw={"slots": ["A", "B", "C", "D", "E", "G", "F", "H"],
                                   "bestOf": 3},
        n_sims=20, seed=1,
    )
    assert stale["status"] == "completed" and stale["champion"] == "A"
    assert stale["bracket"] is None


def test_oversized_projection_error_names_event_and_source_state():
    """An invalid LIVE source grouping must fail with actionable context, not KeyError: 256."""
    rows = [dict(tourney_name="Merged Event", date=pd.Timestamp("2026-07-01"),
                 round="R128", winner_name=f"P{i}", loser_name=f"P{130 + i}",
                 surface_b="Hard", best_of=3, tourney_level="250", draw_level="main")
            for i in range(130)]
    with pytest.raises(ValueError, match=(
            r"wta tournament 'Merged Event': invalid 256-slot bracket .*"
            r"field=260.*completed=False.*draw_state=seeded.*draw_slots=0")):
        project_tournament(_PRED, "Merged Event", pd.DataFrame(rows), "wta", known=set(),
                           top_set=None, n_sims=10, seed=1)
    print("ok test_oversized_projection_error_names_event_and_source_state")


def test_completed_card_survives_an_unseatable_field():
    """A completed Slam is a factual record, not a forecast. If source noise leaves 130
    entrants, preserve its settled facts and hard 128 draw size without simulating it."""
    rows = [dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-01"),
                 round="R128", winner_name=f"P{i}", loser_name=f"P{65 + i}",
                 surface_b="Grass", best_of=5, tourney_level="G", draw_level="main")
            for i in range(65)]
    rows.append(dict(tourney_name="Test Slam", date=pd.Timestamp("2026-07-11"),
                     round="F", winner_name="P0", loser_name="P1", surface_b="Grass",
                     best_of=5, tourney_level="G", draw_level="main"))

    card = project_tournament(_PRED, "Test Slam", pd.DataFrame(rows), "atp", known=set(),
                              top_set=None, n_sims=10, seed=1)
    assert card["status"] == "completed" and card["drawStatus"] == "final"
    assert card["level"] == "Grand Slam" and card["surface"] == "Grass"
    assert card["bestOf"] == 5 and card["drawSize"] == 128
    assert card["champion"] == "P0" and card["runnerUp"] == "P1"
    assert card["aliveCount"] == 1 and card["fieldUnreliable"] is True
    assert card["projection"] == [] and card["modelFavorite"] is None
    print("ok test_completed_card_survives_an_unseatable_field")


def test_one_player_plays_one_match_per_round():
    """A duplicate source row under another spelling cannot add a phantom entrant."""
    rows = [dict(tourney_name="Test Open", date=pd.Timestamp("2026-07-01"),
                 round="R16", winner_name=f"P{i}", loser_name=f"P{8 + i}",
                 surface_b="Hard", best_of=3, tourney_level="250", draw_level="main")
            for i in range(8)]
    rows.insert(1, dict(tourney_name="Test Open", date=pd.Timestamp("2026-07-01"),
                        round="R16", winner_name="P0", loser_name="Phantom P Zero",
                        surface_b="Hard", best_of=3, tourney_level="250", draw_level="main"))
    rows.append(dict(tourney_name="Test Open", date=pd.Timestamp("2026-07-07"),
                     round="F", winner_name="P0", loser_name="P1", surface_b="Hard",
                     best_of=3, tourney_level="250", draw_level="main"))

    card = project_tournament(_PRED, "Test Open", pd.DataFrame(rows), "atp", known=set(),
                              top_set=None, n_sims=20, seed=1)
    assert card["drawSize"] == 16
    assert all(p["name"] != "Phantom P Zero" for p in card["projection"])
    print("ok test_one_player_plays_one_match_per_round")


def test_wiki_draw_makes_a_seeded_board_real():
    """Same event, no ESPN matchups (-> would be 'seeded'), but a Wikipedia ordered draw is
    available: the board runs on the real bracket and reports 'real'."""
    wslots = []
    for i in range(8):                     # (winner, loser) pairs consistent with _g()
        wslots += [f"P{i}", f"P{8 + i}"]
    t = _project([], wiki_draw={"slots": wslots, "bestOf": 3})
    assert t["status"] == "live" and t["drawStatus"] == "real"
    assert _project([])["drawStatus"] == "seeded"            # contrast: without the wiki draw
    print("ok test_wiki_draw_makes_a_seeded_board_real")


def test_prestart_upcoming_projection_from_wiki():
    wd = {"slots": [f"P{i}" for i in range(16)], "bestOf": 3,
          "start": "2026-08-10", "end": "2026-08-16"}
    t = project_upcoming(_PRED, "Future Open", wd, "atp", pd.DataFrame(), set(),
                         lambda n: n, n_sims=200, seed=1)
    assert t["status"] == "upcoming" and t["drawStatus"] == "real"
    assert t["drawSize"] == 16 and t["aliveCount"] == 16 and t["champion"] is None
    assert t["modelFavorite"] == "P0" and t["projection"][0]["name"] == "P0"   # strongest leads
    print("ok test_prestart_upcoming_projection_from_wiki")


@pytest.mark.parametrize(("tour", "expected"), [("atp", "Toronto"), ("wta", "Montreal")])
def test_canadian_masters_uses_familiar_city_name(tour, expected):
    """The shared ESPN sponsor title must not leak into either tour's public card."""
    wd = {"slots": [f"P{i}" for i in range(16)], "bestOf": 3,
          "start": "2026-08-02", "end": "2026-08-14"}
    t = project_upcoming(
        _PRED, "National Bank Open presented by Rogers", wd, tour,
        pd.DataFrame(), set(), lambda n: n, espn_id="421-2026", n_sims=20, seed=1,
    )
    assert t["name"] == expected
    print(f"ok test_canadian_masters_uses_familiar_city_name[{tour}]")


def test_dedup_by_display_name_keeps_fuller_draw():
    """The naming/dedup split that reddened the daily refresh: the same event under an archive
    city name and an ESPN sponsor title, collapsed by _display_name to one shown name. Keep the
    fuller-draw archive record and drop the partial live fragment, whichever order they arrive;
    never collapse two genuinely distinct events that merely run the same week."""
    archive = {"name": "Bad Homburg", "level": "WTA 500", "drawSize": 28,
               "champion": "Naomi Osaka", "status": "completed"}
    fragment = {"name": "Bad Homburg", "level": "WTA Tour", "drawSize": 9,
                "champion": "Karolina Muchova", "status": "completed"}
    for entries in ([archive, fragment], [fragment, archive]):
        kept = _dedup_by_display_name(entries, "wta")
        assert len(kept) == 1
        assert kept[0]["drawSize"] == 28 and kept[0]["champion"] == "Naomi Osaka"
    both = _dedup_by_display_name(
        [{"name": "Eastbourne", "level": "WTA 500", "drawSize": 28},
         {"name": "Mallorca", "level": "WTA 250", "drawSize": 28}], "wta")
    assert len(both) == 2
    print("ok test_dedup_by_display_name_keeps_fuller_draw")


def test_build_tournaments_collapses_archive_and_sponsor_feed():
    """End-to-end: one event reaching build_tournaments under BOTH its archive city name and the
    live/ESPN sponsor title must ship as ONE entry — the fuller archive draw, not the partial
    live fragment (whose champion/aliveCount disagree). Reproduces the real Bad Homburg split."""
    from tennis_model.sim import tournaments as T
    end = pd.Timestamp("2026-06-27")
    rows = []
    # Archive feed: full 'Bad Homburg', 16-player completed draw, champion P0.
    for i in range(8):
        rows.append(dict(tourney_name="Bad Homburg", date=end - pd.Timedelta(days=6),
                         round="R32", winner_name=f"P{i}", loser_name=f"P{8 + i}",
                         surface_b="Grass", best_of=3, tourney_level="500"))
    rows.append(dict(tourney_name="Bad Homburg", date=end, round="F",
                     winner_name="P0", loser_name="P1", surface_b="Grass",
                     best_of=3, tourney_level="500"))
    # Live/ESPN feed: SAME event, sponsor title, 8-player fragment, SWAPPED champion (P2).
    spon = "Bad Homburg Open powered by Solarwatt"
    for a, b in [("P0", "P4"), ("P1", "P5"), ("P2", "P6"), ("P3", "P7")]:
        rows.append(dict(tourney_name=spon, date=end - pd.Timedelta(days=1), round="QF",
                         winner_name=a, loser_name=b, surface_b="Grass", best_of=3,
                         tourney_level=float("nan")))
    rows.append(dict(tourney_name=spon, date=end, round="F", winner_name="P2",
                     loser_name="P0", surface_b="Grass", best_of=3, tourney_level=float("nan")))
    df = pd.DataFrame(rows)

    saved = (T._load_fields, T._load_upcoming, T._load_tournament_draws)
    T._load_fields = lambda tour: {}
    T._load_upcoming = lambda tour: {}
    T._load_tournament_draws = lambda tour: {}
    try:
        out = build_tournaments(_PRED, df, "wta", n_sims=200, seed=1)
    finally:
        T._load_fields, T._load_upcoming, T._load_tournament_draws = saved

    homburg = [t for t in out if t["name"] == "Bad Homburg"]
    assert len(homburg) == 1, [t["name"] for t in out]       # not the duplicate pair
    assert homburg[0]["drawSize"] == 16 and homburg[0]["champion"] == "P0"   # archive, not fragment
    print("ok test_build_tournaments_collapses_archive_and_sponsor_feed")


def test_build_tournaments_uses_cached_draw_evidence_after_live_rows_expire(monkeypatch):
    """When Iasi falls out of ESPN's result window, its stable rows retain only the
    archive city label.  The cached official draw must recover 874-2026 by dates, players,
    and real R32 matchups so the calendar can close the event instead of leaving it live."""
    from tennis_model.sim import tournaments as T

    slots = [f"I{i}" for i in range(32)]
    rows = [
        dict(tourney_name="Iasi", espn_id=None,
             date=pd.Timestamp("2026-07-13") + pd.Timedelta(days=i % 6),
             round="R32", winner_name=slots[2 * i], loser_name=slots[2 * i + 1],
             surface_b="Clay", surface_src="archive", best_of=3,
             tourney_level="WTA250", draw_level="main")
        for i in range(16)
    ]
    # Data-relative lifecycle decisions anchor on the tour's newest match, as production does.
    rows.append(dict(tourney_name="Current Open", espn_id="999-2026",
                     date=pd.Timestamp("2026-08-04"), round="R32",
                     winner_name="Current A", loser_name="Current B", surface_b="Hard",
                     surface_src="archive", best_of=3, tourney_level="WTA250",
                     draw_level="main"))
    df = pd.DataFrame(rows)
    draw = {
        "name": "Unicredit Iasi Open", "espnId": "874-2026",
        "start": "2026-07-12", "end": "2026-07-21", "slots": slots,
        "seeds": {}, "bestOf": 3, "drawSize": 32, "source": "wta",
    }
    registry = {"events": {"874-2026": {
        "name": "Unicredit Iasi Open", "names": ["Unicredit Iasi Open"],
        "start": "2026-07-12", "end": "2026-07-21",
    }}}
    monkeypatch.setattr(T, "_load_fields", lambda _tour: {})
    monkeypatch.setattr(T, "_load_upcoming", lambda _tour: {})
    monkeypatch.setattr(T, "_load_tournament_draws", lambda _tour: {"874-2026": draw})
    monkeypatch.setattr(T, "load_registry", lambda _tour: registry)
    rated = {name: 2000.0 - i for i, name in enumerate(slots + ["Current A", "Current B"])}

    cards = build_tournaments(_Pred(rated), df, "wta", n_sims=20, seed=1)

    iasi = next(card for card in cards if card["name"] == "Iasi")
    assert iasi["espnId"] == "874-2026"
    assert iasi["status"] == "completed" and iasi["finalRecorded"] is False
    assert iasi["level"] == "WTA 250" and iasi["surface"] == "Clay"


def test_one_unprojectable_event_does_not_take_down_the_whole_board():
    """The 2026-07-27 production outage. WTA Wimbledon, long completed, had a 129-player
    results union (a leaked qualifier) and no cached wiki draw left to pin the field — the
    >128-slot guard fired and the ValueError propagated out of build_tournaments, killing
    the export, the deploy, and every queued refresh behind it. The site sat on the previous
    evening's board through a Monday when a dozen events were starting.

    The guard is right; taking the pipeline down with it is not. A completed event now ships
    as a factual, explicitly field-unreliable record while every healthy event survives."""
    from tennis_model.sim import tournaments as T
    end = pd.Timestamp("2026-07-27")
    rows = []
    # a healthy 16-draw completed event that MUST survive
    for i in range(8):
        rows.append(dict(tourney_name="Good Open", date=end - pd.Timedelta(days=6),
                         round="R32", winner_name=f"P{i}", loser_name=f"P{8 + i}",
                         surface_b="Hard", best_of=3, tourney_level="250",
                         draw_level="main"))
    rows.append(dict(tourney_name="Good Open", date=end, round="F", winner_name="P0",
                     loser_name="P1", surface_b="Hard", best_of=3, tourney_level="250",
                     draw_level="main"))
    # the poisoned one: 130 distinct entrants on a completed draw -> pads past 128
    for i in range(65):
        rows.append(dict(tourney_name="Poisoned Slam", date=end - pd.Timedelta(days=8),
                         round="R128", winner_name=f"Q{i}", loser_name=f"Q{65 + i}",
                         surface_b="Grass", best_of=3, tourney_level="G",
                         draw_level="main"))
    rows.append(dict(tourney_name="Poisoned Slam", date=end - pd.Timedelta(days=1),
                     round="F", winner_name="Q0", loser_name="Q1", surface_b="Grass",
                     best_of=3, tourney_level="G", draw_level="main"))
    df = pd.DataFrame(rows)

    # every entrant must be RATED, or build_tournaments' top_set filter drops the event
    # before the bracket guard can fire (which is what made the first draft of this test
    # pass against the unfixed code — a green test that exercised nothing)
    rated = {f"P{i}": 2000.0 - 30.0 * i for i in range(16)}
    rated.update({f"Q{i}": 1900.0 - i for i in range(130)})
    pred = _Pred(rated)

    saved = (T._load_fields, T._load_upcoming, T._load_tournament_draws)
    T._load_fields = lambda tour: {}
    T._load_upcoming = lambda tour: {}
    T._load_tournament_draws = lambda tour: {}    # the cache has aged out, as it really had
    try:
        out = build_tournaments(pred, df, "wta", n_sims=50, seed=1)   # must NOT raise
    finally:
        T._load_fields, T._load_upcoming, T._load_tournament_draws = saved

    names = {t["name"] for t in out}
    assert "Good Open" in names, f"a healthy event was lost with the bad one: {names}"
    poisoned = next(t for t in out if t["name"] == "Poisoned Slam")
    assert poisoned["drawSize"] == 128 and poisoned["fieldUnreliable"] is True
    assert poisoned["projection"] == [] and poisoned["modelFavorite"] is None
    print("ok test_one_unprojectable_event_does_not_take_down_the_whole_board")

if __name__ == "__main__":
    test_status_real_partial_seeded_final_from_espn()
    test_completed_projection_excludes_qualifying_field()
    test_completed_projection_keeps_authoritative_wiki_field()
    test_oversized_projection_error_names_event_and_source_state()
    test_wiki_draw_makes_a_seeded_board_real()
    test_prestart_upcoming_projection_from_wiki()
    test_one_unprojectable_event_does_not_take_down_the_whole_board()
    test_dedup_by_display_name_keeps_fuller_draw()
    test_build_tournaments_collapses_archive_and_sponsor_feed()
    print("\nALL PASSED")
