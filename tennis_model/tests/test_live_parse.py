"""Unit checks for data/live ESPN scoreboard parsing — canned fixture, no network.

Runnable directly (`python tests/test_live_parse.py`) or under pytest. Covers
round-label mapping, winner-perspective score strings, and parse_events /
parse_upcoming / parse_fields over a synthetic events payload mirroring ESPN's
schema (events -> groupings -> competitions -> competitors).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.live as live


# ---------------------------------------------------------------------------
# fixture builders (ESPN scoreboard schema)
# ---------------------------------------------------------------------------
def _completed(rnd, winner, w_sets, loser, l_sets, date="2026-06-08T13:00Z"):
    return {
        "status": {"type": {"state": "post", "completed": True}},
        "round": {"displayName": rnd},
        "date": date,
        "competitors": [
            {"winner": True, "athlete": {"displayName": winner},
             "linescores": [{"value": float(v)} for v in w_sets]},
            {"winner": False, "athlete": {"displayName": loser},
             "linescores": [{"value": float(v)} for v in l_sets]},
        ],
    }


def _pending(rnd, a, b, state="pre", date="2026-06-09T11:00Z"):
    return {
        "status": {"type": {"state": state, "completed": False}},
        "round": {"displayName": rnd},
        "date": date,
        "competitors": [
            {"athlete": ({"displayName": n} if n else {})} for n in (a, b)
        ],
    }


def _mens_round(rid, disp, n, completed=True):
    """n ESPN competitions in one main-draw round, tagged with ESPN's numeric round id
    (1-4 numbered, 5/6/7 = QF/SF/F) — mirrors the real scoreboard payload."""
    comps = []
    for i in range(n):
        w, ls = f"W{rid}_{i}", f"L{rid}_{i}"
        comps.append({
            "status": {"type": {"state": "post" if completed else "pre",
                                 "completed": completed}},
            "round": {"id": str(rid), "displayName": disp},
            "date": "2026-07-01T12:00Z",
            "competitors": [
                {"winner": True, "athlete": {"displayName": w},
                 "linescores": [{"value": 6.0}]},
                {"winner": False, "athlete": {"displayName": ls},
                 "linescores": [{"value": 3.0}]},
            ] if completed else [
                {"athlete": {"displayName": w}}, {"athlete": {"displayName": ls}},
            ],
        })
    return comps


def _events():
    final = _completed("Final", "Aaron Ace", (6, 6), "Bob Baseline", (3, 4))
    semi = _completed("Semifinal", "Aaron Ace", (7, 6), "Carl Clay", (6, 4))
    qual = _completed("Qualifying - 1st Round", "Quinn Qual", (6, 6), "Q Two", (1, 1))
    test_open = {
        "id": "100", "shortName": "Test Open",
        "groupings": [
            {"grouping": {"slug": "mens-singles"},
             "competitions": [
                 final, semi,
                 dict(final),                                   # exact duplicate -> dedup
                 qual,                                          # qualifying -> dropped
                 _pending("Quarterfinal", "Aaron Ace", "Dave Drop", state="in"),
                 _pending("Quarterfinal", "Bob Baseline", "Carl Clay", state="pre"),
                 _pending("Quarterfinal", "Known Player", None, state="pre"),  # TBD
             ]},
            {"grouping": {"slug": "mens-doubles"},               # doubles -> dropped
             "competitions": [_completed("Final", "Duo One", (6, 6), "Duo Two", (2, 2))]},
            {"grouping": {"slug": "womens-singles"},             # other tour
             "competitions": [_completed("Final", "Wendy Winner", (6, 6),
                                         "Lucy Loser", (2, 2))]},
        ],
    }
    big_slam = {
        "id": "200", "name": "Big Slam",
        "groupings": [
            {"grouping": {"slug": "mens-singles"},
             "competitions": [
                 _completed("Round of 16", f"Winner {i}", (6, 6), f"Loser {i}", (3, 4))
                 for i in range(4)
             ] + [
                 # ESPN's placeholder pseudo-athlete for an undetermined opponent: a
                 # scheduled QF awaiting a prior result, and a not-yet-drawn shell
                 # match. Neither "TBD" may enter the field (129-player Slam bug).
                 _pending("Quarterfinal", "Winner 0", "TBD", state="pre"),
                 _pending("Quarterfinal", "TBD", "TBD", state="pre"),
             ]},
        ],
    }
    return [test_open, big_slam]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def test_round_label():
    assert live._round_label("Final") == "F"
    assert live._round_label("Semifinal") == "SF"
    assert live._round_label("Semifinals") == "SF"
    assert live._round_label("Quarterfinal") == "QF"
    assert live._round_label("Round of 16") == "R16"
    assert live._round_label("3rd Round") == "R32"
    assert live._round_label("2nd Round") == "R64"
    assert live._round_label("1st Round") == "R128"
    # qualifying always drops, even when it mentions a round number
    assert live._round_label("Qualifying - 1st Round") is None
    assert live._round_label("Qualifying") is None
    # unrecognised main-draw name -> generic round
    assert live._round_label("") == "R64"
    print("ok test_round_label")


def test_draw_size():
    # 128-draw Slam: opening round has 64 matches -> draw 128
    slam = (_mens_round(1, "Round 1", 64) + _mens_round(2, "Round 2", 32)
            + _mens_round(5, "Quarterfinal", 4))
    assert live._draw_size(slam) == 128
    # 32-draw event: opening round has 16 matches -> draw 32
    assert live._draw_size(_mens_round(1, "Round 1", 16) + _mens_round(2, "Round 2", 8)) == 32
    # byes: a 28-player field (12 opening matches) still brackets as 32
    assert live._draw_size(_mens_round(1, "Round 1", 12)) == 32
    # Cincinnati's 96-player field occupies a 128-slot bracket: round 1 has only the
    # 32 non-bye matches, while round 2 has 32 more. Looking only at the largest raw
    # round count incorrectly calls this a 64-draw and shifts every label one round late.
    cincy = (_mens_round(1, "Round 1", 32) + _mens_round(2, "Round 2", 32)
             + _mens_round(3, "Round 3", 16))
    assert live._draw_size(cincy) == 128
    # QF/SF/F ids never size the draw; no numbered rounds -> unknown (0)
    assert live._draw_size(_mens_round(5, "Quarterfinal", 4)) == 0
    assert live._draw_size([]) == 0
    print("ok test_draw_size")


def test_round_code_draw_relative():
    # THE BUG: ESPN labels Slam main-draw rounds "Round 1".."Round 4" (ids 1-4), which the
    # old name map collapsed to R64. They must resolve against draw size instead.
    for rid, disp, code in [(1, "Round 1", "R128"), (2, "Round 2", "R64"),
                            (3, "Round 3", "R32"), (4, "Round 4", "R16")]:
        assert live._round_code({"id": str(rid), "displayName": disp}, 128) == code
    # the SAME labels are earlier rounds at a 32-draw event
    assert live._round_code({"id": "1", "displayName": "Round 1"}, 32) == "R32"
    assert live._round_code({"id": "2", "displayName": "Round 2"}, 32) == "R16"
    # QF/SF/F are draw-agnostic (ids 5/6/7, resolved by name) — never touched by the numbered path
    assert live._round_code({"id": "5", "displayName": "Quarterfinal"}, 128) == "QF"
    assert live._round_code({"id": "6", "displayName": "Semifinal"}, 32) == "SF"
    assert live._round_code({"id": "7", "displayName": "Final"}, 128) == "F"
    # qualifying dropped even carrying a numeric id
    assert live._round_code({"id": "11", "displayName": "Qualifying 1st Round"}, 128) is None
    # unknown draw -> graceful fall back to the name map (id-less / legacy payloads)
    assert live._round_code({"displayName": "Round of 16"}, 0) == "R16"
    print("ok test_round_code_draw_relative")


def test_parse_events_slam_rounds_not_all_r64():
    # end-to-end regression: a real-shaped 128-draw must yield R128/R64/R32/R16, not four
    # buckets of "R64" (the symptom the deployed fixtures showed during Wimbledon).
    from collections import Counter
    comps = (_mens_round(1, "Round 1", 64) + _mens_round(2, "Round 2", 32)
             + _mens_round(3, "Round 3", 16) + _mens_round(4, "Round 4", 8)
             + _mens_round(5, "Quarterfinal", 4))
    ev = {"id": "900", "name": "Grand Slam",
          "groupings": [{"grouping": {"slug": "mens-singles"}, "competitions": comps}]}
    df = live.parse_events([ev], "mens")
    assert Counter(df["round"]) == {"R128": 64, "R64": 32, "R32": 16, "R16": 8, "QF": 4}
    print("ok test_parse_events_slam_rounds_not_all_r64")


def test_parse_events_bye_heavy_draw_uses_every_numbered_stage():
    """The 2026 Cincinnati payload has 32 matches in BOTH rounds 1 and 2. Round 2's
    position proves a 128-slot bracket even though the 96-player field has only 32
    opening-round matches; otherwise its current Round 3 ships as R16 instead of R32."""
    from collections import Counter
    comps = (_mens_round(1, "Round 1", 32) + _mens_round(2, "Round 2", 32)
             + _mens_round(3, "Round 3", 16))
    ev = {"id": "718-2026", "shortName": "Cincinnati Open",
          "venue": {"displayName": "Cincinnati, USA"},
          "groupings": [{"grouping": {"slug": "mens-singles"}, "competitions": comps}]}
    df = live.parse_events([ev], "mens")
    assert Counter(df["round"]) == {"R128": 32, "R64": 32, "R32": 16}
    print("ok test_parse_events_bye_heavy_draw_uses_every_numbered_stage")


def test_score_winner_perspective():
    # winner-perspective games, sets space-separated, tiebreak points never shown
    assert live._score([{"value": 6.0}, {"value": 7.0}],
                       [{"value": 3.0}, {"value": 6.0}]) == "6-3 7-6"
    # an unscored set (value None) is skipped rather than crashing
    assert live._score([{"value": 6}, {"value": None}],
                       [{"value": 3}, {"value": 2}]) == "6-3"
    assert live._score(None, None) == ""
    print("ok test_score_winner_perspective")


def test_parse_events_completed_singles_only():
    df = live.parse_events(_events(), "mens")
    assert len(df) == 6, df                      # 2 Test Open + 4 Big Slam, dup dropped
    to = df[df["tourney_name"] == "Test Open"]
    assert len(to) == 2 and set(to["round"]) == {"F", "SF"}, to
    f = to[to["round"] == "F"].iloc[0]
    assert f["winner_name"] == "Aaron Ace" and f["loser_name"] == "Bob Baseline"
    assert f["score"] == "6-3 6-4"
    assert f["tourney_date"] == "2026-06-08"     # YYYY-MM-DD prefix of the ISO stamp
    sf = to[to["round"] == "SF"].iloc[0]
    assert sf["score"] == "7-6 6-4"              # tiebreak points dropped
    # doubles / other tour / qualifying / unfinished never leak through
    names = set(df["winner_name"]) | set(df["loser_name"])
    assert not names & {"Duo One", "Wendy Winner", "Quinn Qual", "Dave Drop"}, names
    bs = df[df["tourney_name"] == "Big Slam"]
    assert len(bs) == 4 and set(bs["round"]) == {"R16"}, bs
    print("ok test_parse_events_completed_singles_only")


def test_parse_events_other_tour():
    df = live.parse_events(_events(), "womens")
    assert len(df) == 1, df
    assert df.iloc[0]["winner_name"] == "Wendy Winner"
    assert df.iloc[0]["loser_name"] == "Lucy Loser"
    print("ok test_parse_events_other_tour")


def test_parse_upcoming():
    up = live.parse_upcoming(_events(), "mens")
    assert len(up) == 2, up
    pairs = {(r.playerA, r.playerB) for r in up.itertuples()}
    assert ("Aaron Ace", "Dave Drop") in pairs        # in-progress kept
    assert ("Bob Baseline", "Carl Clay") in pairs     # scheduled kept
    # completed matches and TBD matchups are excluded
    names = {n for p in pairs for n in p}
    assert "Known Player" not in names
    assert "TBD" not in names                         # placeholder never a matchup side
    assert set(up["round"]) == {"QF"}
    print("ok test_parse_upcoming")


def test_espn_timestamps_use_the_tournament_local_calendar_date():
    """ESPN timestamps are UTC instants. Cincinnati's Sunday-night matches cross
    midnight UTC, so slicing the ISO string displayed Monday for a Sunday result."""
    completed = _completed("Final", "Aaron Ace", (6, 6), "Bob Baseline", (3, 4),
                           date="2026-08-17T02:00Z")
    pending = _pending("Final", "Carl Clay", "Dave Drop",
                       date="2026-08-18T01:30Z")
    ev = {"id": "718-2026", "shortName": "Cincinnati Open",
          "venue": {"displayName": "Cincinnati, USA"},
          "date": "2026-08-11T04:00Z", "endDate": "2026-08-24T03:59Z",
          "groupings": [{"grouping": {"slug": "mens-singles"},
                         "competitions": [completed, pending]}]}

    assert live.parse_events([ev], "mens").iloc[0]["tourney_date"] == "2026-08-16"
    assert live.parse_upcoming([ev], "mens").iloc[0]["tourney_date"] == "2026-08-17"
    assert live.parse_event_meta([ev])["Cincinnati Open"] == {
        "espnId": "718-2026", "start": "2026-08-11", "end": "2026-08-23"}

    # An unknown venue stays deterministic and preserves the old UTC-date fallback.
    unknown = dict(ev, id="999-2026", shortName="Unknown Open", venue={})
    assert live.parse_events([unknown], "mens").iloc[0]["tourney_date"] == "2026-08-17"
    print("ok test_espn_timestamps_use_the_tournament_local_calendar_date")


def test_parse_fields():
    fields = live.parse_fields(_events(), "mens")
    # Test Open has < 8 known players -> only Big Slam qualifies as a live field
    assert set(fields) == {"Big Slam"}, fields
    bs = fields["Big Slam"]
    # exactly the 8 real players — the scheduled-match "TBD" placeholder must not
    # inflate the field (regression: Wimbledon 2026 showed a "129 draw")
    assert bs["field"] == sorted([f"Winner {i}" for i in range(4)]
                                 + [f"Loser {i}" for i in range(4)])
    assert bs["eliminated"] == sorted(f"Loser {i}" for i in range(4))
    print("ok test_parse_fields")


def test_every_parsed_row_carries_the_stable_event_id():
    """`tourney_name` is a sponsor title that churns mid-event — ESPN dropped "Citi" from the
    DC Open on 2026-07-27 and orphaned every cache keyed on the name. The id does not churn,
    and ESPN has always sent it; it was extracted once to dedup a fetch and thrown away."""
    evs = _events()
    df = live.parse_events(evs, "mens")
    assert "espn_id" in df.columns
    assert set(df.loc[df["tourney_name"] == "Test Open", "espn_id"]) == {"100"}
    assert set(df.loc[df["tourney_name"] == "Big Slam", "espn_id"]) == {"200"}
    assert df["espn_id"].notna().all()

    up = live.parse_upcoming(evs, "mens")
    assert "espn_id" in up.columns and up["espn_id"].notna().all()
    assert set(up["espn_id"]) == {"100"}

    # fields stay NAME-keyed for now (readers flip in B3) but carry the id inside, so a
    # rename can be bridged the way wiki_draws entries already allow
    fields = live.parse_fields(evs, "mens")
    assert fields["Big Slam"]["espnId"] == "200"

    # ...and the id is a HINT, never a dedup key: the exact-duplicate final still collapses
    assert len(df[(df["tourney_name"] == "Test Open") & (df["round"] == "F")]) == 1
    print("ok test_every_parsed_row_carries_the_stable_event_id")


def test_placeholder_names_dropped():
    # the shared competitor->name gate: placeholder pseudo-athletes map to None
    for nm in ("TBD", "tbd", " TBD ", "TBA", "Bye", "Qualifier"):
        assert live._athlete_name({"athlete": {"displayName": nm}}) is None, nm
    assert live._athlete_name({"athlete": {"displayName": "Aaron Ace"}}) == "Aaron Ace"
    # Verified aliases apply at the common ESPN boundary, so upcoming/fields/results all
    # resolve after the duplicate rating identity is removed by a full rebuild.
    assert live._athlete_name({"athlete": {"displayName": "Zhang Shuai"}}) == "Shuai Zhang"
    assert live._athlete_name({"athlete": {"displayName": "Wang Xiyu"}}) == "Xiyu Wang"
    assert live._athlete_name({"athlete": {"displayName": "Catherine McNally"}}) == "Caty Mcnally"
    assert live._athlete_name({"athlete": {}}) is None
    assert live._athlete_name(None) is None
    print("ok test_placeholder_names_dropped")


def _sweep_len() -> int:
    """How many queries fetch_events issues: the featured call plus the day sweep."""
    return 1 + len(range(-12, 15))


def test_total_scoreboard_failure_is_raised_not_reported_as_a_quiet_week(monkeypatch):
    """Regression for 2026-08-04..07. ESPN began 403-ing this client's User-Agent, so every
    query below raised, `fetch_events` swallowed all of them and returned [], and the caller
    printed "no completed matches found" — the same line a genuinely idle day prints. The
    overlay stayed blind through ~13 refresh runs while a Masters played out, and the board
    kept showing players who had already lost. An empty result must mean ESPN answered and
    had nothing, never that nobody answered."""
    calls = []

    def _always_403(tour, datestr=None):
        calls.append(datestr)
        raise OSError("HTTP Error 403: Forbidden")

    monkeypatch.setattr(live, "_fetch", _always_403)
    try:
        live.fetch_events("atp")
    except live.ScoreboardUnavailable as e:
        assert "403" in str(e), e
    else:
        raise AssertionError("a total transport failure must not look like an empty scoreboard")
    assert len(calls) == _sweep_len(), calls
    print("ok test_total_scoreboard_failure_is_raised_not_reported_as_a_quiet_week")


def test_one_bad_query_still_yields_the_rest(monkeypatch):
    """The tolerance that made the outage invisible is still correct for a single bad day —
    only the all-failed case is a transport outage."""
    def _one_bad(tour, datestr=None):
        if datestr is None:
            raise OSError("HTTP Error 500")
        return [{"id": "421-2026", "shortName": "Toronto"}]

    monkeypatch.setattr(live, "_fetch", _one_bad)
    evs = live.fetch_events("atp")
    assert [e["id"] for e in evs] == ["421-2026"], evs
    print("ok test_one_bad_query_still_yields_the_rest")


def test_a_genuinely_empty_scoreboard_is_not_an_error(monkeypatch):
    """The off-season / rest-day case must stay silent — the point is to separate the two."""
    monkeypatch.setattr(live, "_fetch", lambda tour, datestr=None: [])
    assert live.fetch_events("atp") == []
    print("ok test_a_genuinely_empty_scoreboard_is_not_an_error")


def test_acquisition_fact_distinguishes_partial_and_success_empty(monkeypatch):
    monkeypatch.setattr(live, "_fetch", lambda tour, datestr=None: [])
    events, receipt, error = live._acquire_events("atp")
    assert events == [] and error is None
    assert receipt["status"] == "success_empty"
    assert receipt["queries"] == {
        "attempted": _sweep_len(), "succeeded": _sweep_len(), "failed": 0,
        "featuredSucceeded": True, "failedKeys": [], "failureTypes": {},
    }

    def _partial(tour, datestr=None):
        if datestr is None:
            raise OSError("featured down")
        return [{"id": "421-2026"}]

    monkeypatch.setattr(live, "_fetch", _partial)
    events, receipt, error = live._acquire_events("atp")
    assert [event["id"] for event in events] == ["421-2026"]
    assert receipt["status"] == "partial_query_failure"
    assert receipt["queries"]["failed"] == 1
    assert receipt["queries"]["failedKeys"] == ["featured"]
    assert type(error).__name__ == "OSError"


def test_download_writes_total_failure_receipt_and_preserves_last_good(tmp_path, monkeypatch):
    directory = tmp_path / "atp"
    directory.mkdir()
    old = directory / "live.csv"
    old.write_bytes(b"old,last,good\n")
    monkeypatch.setattr(live, "live_dir", lambda tour: directory)

    def _down(tour, datestr=None):
        raise OSError("HTTP 503")

    monkeypatch.setattr(live, "_fetch", _down)
    result = live.download_live(("atp",))
    receipt = json.loads((directory / "espn_acquisition.json").read_text(encoding="utf-8"))
    assert result == {"atp": []}       # tells the draw stage not to repeat the doomed sweep
    assert receipt["status"] == "total_transport_failure"
    assert receipt["queries"]["failed"] == _sweep_len()
    assert receipt["overlay"]["status"] == "retained_last_good"
    assert receipt["overlay"]["retainedFiles"] == ["live.csv"]
    assert old.read_bytes() == b"old,last,good\n"


def test_severe_partial_sweep_retains_overlay_then_total_outage_keeps_it(tmp_path, monkeypatch):
    directory = tmp_path / "atp"; directory.mkdir()
    originals = {
        "live.csv": b"old-live\n",
        "fields.json": b'{"old":true}',
        "upcoming.csv": b"old-upcoming\n",
    }
    for name, payload in originals.items():
        (directory / name).write_bytes(payload)
    (directory / "espn_acquisition.json").write_text(json.dumps({
        "overlay": {"lastGoodAt": "2026-08-19T07:00:00Z"},
    }), encoding="utf-8")
    partial = {
        "schema": "espn-acquisition-v1", "tour": "atp", "source": "test",
        "attemptedAt": "2026-08-23T10:00:00Z", "completedAt": "2026-08-23T10:00:01Z",
        "status": "partial_query_failure",
        "queries": {"attempted": 28, "succeeded": 1, "failed": 27,
                    "featuredSucceeded": False, "failedKeys": ["featured"],
                    "failureTypes": {"OSError": 27}},
        "eventCount": 1,
    }
    total = {
        **partial,
        "attemptedAt": "2026-08-23T11:00:00Z", "completedAt": "2026-08-23T11:00:01Z",
        "status": "total_transport_failure",
        "queries": {**partial["queries"], "succeeded": 0, "failed": 28},
        "eventCount": 0,
    }
    acquisitions = iter([
        ([{"id": "would-overwrite-everything"}], partial, OSError()),
        ([], total, OSError()),
    ])
    monkeypatch.setattr(live, "live_dir", lambda tour: directory)
    monkeypatch.setattr(live, "_acquire_events", lambda tour: next(acquisitions))
    monkeypatch.setattr(live, "parse_events",
                        lambda *args: (_ for _ in ()).throw(AssertionError("must retain")))

    assert live.download_live(("atp",)) == {"atp": []}
    first = json.loads((directory / "espn_acquisition.json").read_text(encoding="utf-8"))
    assert first["status"] == "partial_query_failure"
    assert first["overlay"]["status"] == "retained_last_good"
    assert first["overlay"]["lastGoodAt"] == "2026-08-19T07:00:00Z"
    assert {name: (directory / name).read_bytes() for name in originals} == originals

    assert live.download_live(("atp",)) == {"atp": []}
    second = json.loads((directory / "espn_acquisition.json").read_text(encoding="utf-8"))
    assert second["status"] == "total_transport_failure"
    assert second["overlay"]["status"] == "retained_last_good"
    assert second["overlay"]["lastGoodAt"] == "2026-08-19T07:00:00Z"
    assert {name: (directory / name).read_bytes() for name in originals} == originals


def test_receipt_recovery_replaces_failure_atomically(tmp_path, monkeypatch):
    directory = tmp_path / "atp"; directory.mkdir()
    path = directory / "espn_acquisition.json"
    path.write_text('{"old":"failure"}', encoding="utf-8")
    monkeypatch.setattr(live, "live_dir", lambda tour: directory)
    monkeypatch.setattr(live, "_fetch", lambda tour, datestr=None: [])
    monkeypatch.setattr("tennis_model.data.events.update_registry", lambda tour, meta: None)
    result = live.download_live(("atp",))
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert result == {"atp": []} and receipt["status"] == "success_empty"
    assert not list(directory.glob(".*.tmp"))

    old = path.read_bytes()
    monkeypatch.setattr(live, "_fetch", lambda tour, datestr=None: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(live.os, "replace", lambda src, dst: (_ for _ in ()).throw(OSError("disk")))
    try:
        live.download_live(("atp",))
    except OSError as exc:
        assert "disk" in str(exc)
    else:
        raise AssertionError("a receipt publication failure must fail the refresh")
    assert path.read_bytes() == old


def test_atomic_overlay_write_preserves_old_target_on_mid_write_failure(tmp_path):
    target = tmp_path / "live.csv"
    target.write_bytes(b"old-good\n")

    def _partial_then_fail(staged):
        staged.write_bytes(b"truncated-new")
        raise OSError("writer stopped")

    try:
        live._write_atomic(target, _partial_then_fail)
    except OSError as exc:
        assert "writer stopped" in str(exc)
    else:
        raise AssertionError("mid-write failure was swallowed")
    assert target.read_bytes() == b"old-good\n"
    assert not list(tmp_path.glob(".*.tmp"))


def test_mixed_overlay_generation_is_explicit_and_keeps_prior_last_good(tmp_path, monkeypatch):
    import pandas as pd
    directory = tmp_path / "atp"; directory.mkdir()
    (directory / "live.csv").write_text("old-live\n", encoding="utf-8")
    (directory / "fields.json").write_text('{"old":true}', encoding="utf-8")
    (directory / "espn_acquisition.json").write_text(json.dumps({
        "overlay": {"lastGoodAt": "2026-08-22T10:00:00Z"},
    }), encoding="utf-8")
    acquisition = {
        "schema": "espn-acquisition-v1", "tour": "atp", "source": "test",
        "attemptedAt": "2026-08-23T10:00:00Z", "completedAt": "2026-08-23T10:00:01Z",
        "status": "success", "queries": {"attempted": 28, "succeeded": 28, "failed": 0,
        "featuredSucceeded": True, "failedKeys": [], "failureTypes": {}}, "eventCount": 1,
    }
    monkeypatch.setattr(live, "live_dir", lambda tour: directory)
    monkeypatch.setattr(live, "_acquire_events",
                        lambda tour: ([{"id": "1"}], dict(acquisition), None))
    monkeypatch.setattr(live, "parse_events", lambda events, gender: pd.DataFrame([{
        "tourney_name": "New", "tourney_date": "2026-08-23",
    }]))
    monkeypatch.setattr(live, "parse_fields", lambda events, gender: {"New": {"field": []}})
    monkeypatch.setattr(live, "parse_upcoming", lambda events, gender: pd.DataFrame())
    monkeypatch.setattr("tennis_model.data.events.update_registry", lambda tour, meta: None)
    monkeypatch.setattr(live, "_write_fields",
                        lambda path, fields: (_ for _ in ()).throw(OSError("fields disk")))
    live.download_live(("atp",))
    receipt = json.loads((directory / "espn_acquisition.json").read_text(encoding="utf-8"))
    assert "New" in (directory / "live.csv").read_text(encoding="utf-8")
    assert (directory / "fields.json").read_text(encoding="utf-8") == '{"old":true}'
    assert receipt["overlay"]["status"] == "partially_updated"
    assert receipt["overlay"]["updatedFiles"] == ["live.csv"]
    assert receipt["overlay"]["retainedFiles"] == ["fields.json"]
    assert receipt["overlay"]["lastGoodAt"] == "2026-08-22T10:00:00Z"
    assert receipt["overlay"]["processingFailureType"] == "OSError"


def test_normal_partial_overlay_refresh_keeps_prior_last_good(tmp_path, monkeypatch):
    import pandas as pd
    directory = tmp_path / "atp"; directory.mkdir()
    (directory / "live.csv").write_text("old-live\n", encoding="utf-8")
    (directory / "fields.json").write_text('{"old":true}', encoding="utf-8")
    (directory / "espn_acquisition.json").write_text(json.dumps({
        "overlay": {"lastGoodAt": "2026-08-21T08:00:00Z"},
    }), encoding="utf-8")
    acquisition = {
        "schema": "espn-acquisition-v1", "tour": "atp", "source": "test",
        "attemptedAt": "2026-08-23T10:00:00Z", "completedAt": "2026-08-23T10:00:01Z",
        "status": "success", "queries": {"attempted": 28, "succeeded": 28, "failed": 0,
        "featuredSucceeded": True, "failedKeys": [], "failureTypes": {}}, "eventCount": 1,
    }
    monkeypatch.setattr(live, "live_dir", lambda tour: directory)
    monkeypatch.setattr(live, "_acquire_events",
                        lambda tour: ([{"id": "1"}], dict(acquisition), None))
    monkeypatch.setattr(live, "parse_events", lambda events, gender: pd.DataFrame([{
        "tourney_name": "New", "tourney_date": "2026-08-23",
    }]))
    monkeypatch.setattr(live, "parse_fields", lambda events, gender: {})
    monkeypatch.setattr(live, "parse_upcoming", lambda events, gender: pd.DataFrame())
    monkeypatch.setattr("tennis_model.data.events.update_registry", lambda tour, meta: None)

    live.download_live(("atp",))

    receipt = json.loads((directory / "espn_acquisition.json").read_text(encoding="utf-8"))
    assert "New" in (directory / "live.csv").read_text(encoding="utf-8")
    assert (directory / "fields.json").read_text(encoding="utf-8") == '{"old":true}'
    assert receipt["overlay"]["status"] == "partially_updated"
    assert receipt["overlay"]["updatedFiles"] == ["live.csv"]
    assert receipt["overlay"]["retainedFiles"] == ["fields.json"]
    assert receipt["overlay"]["lastGoodAt"] == "2026-08-21T08:00:00Z"


def test_mild_partial_acquisition_cannot_advance_last_good(tmp_path, monkeypatch):
    import pandas as pd
    directory = tmp_path / "atp"; directory.mkdir()
    for name in ("live.csv", "fields.json", "upcoming.csv"):
        (directory / name).write_text("old\n", encoding="utf-8")
    (directory / "espn_acquisition.json").write_text(json.dumps({
        "overlay": {"lastGoodAt": "2026-08-18T06:00:00Z"},
    }), encoding="utf-8")
    acquisition = {
        "schema": "espn-acquisition-v1", "tour": "atp", "source": "test",
        "attemptedAt": "2026-08-23T10:00:00Z", "completedAt": "2026-08-23T10:00:01Z",
        "status": "partial_query_failure",
        "queries": {"attempted": 28, "succeeded": 27, "failed": 1,
                    "featuredSucceeded": False, "failedKeys": ["featured"],
                    "failureTypes": {"OSError": 1}},
        "eventCount": 1,
    }
    monkeypatch.setattr(live, "live_dir", lambda tour: directory)
    monkeypatch.setattr(live, "_acquire_events",
                        lambda tour: ([{"id": "1"}], dict(acquisition), OSError()))
    monkeypatch.setattr(live, "parse_events", lambda events, gender: pd.DataFrame([{
        "tourney_name": "New", "tourney_date": "2026-08-23",
    }]))
    monkeypatch.setattr(live, "parse_fields", lambda events, gender: {"New": {"field": []}})
    monkeypatch.setattr(live, "parse_upcoming", lambda events, gender: pd.DataFrame([{
        "tourney_name": "New",
    }]))
    monkeypatch.setattr("tennis_model.data.events.update_registry", lambda tour, meta: None)

    live.download_live(("atp",))

    receipt = json.loads((directory / "espn_acquisition.json").read_text(encoding="utf-8"))
    assert receipt["overlay"]["status"] == "updated"
    assert receipt["overlay"]["lastGoodAt"] == "2026-08-18T06:00:00Z"


def test_success_empty_does_not_refresh_retained_overlay_age(tmp_path, monkeypatch):
    directory = tmp_path / "atp"; directory.mkdir()
    (directory / "live.csv").write_text("old-live\n", encoding="utf-8")
    (directory / "espn_acquisition.json").write_text(json.dumps({
        "overlay": {"lastGoodAt": "2026-08-20T09:00:00Z"},
    }), encoding="utf-8")
    monkeypatch.setattr(live, "live_dir", lambda tour: directory)
    monkeypatch.setattr(live, "_fetch", lambda tour, datestr=None: [])
    monkeypatch.setattr("tennis_model.data.events.update_registry", lambda tour, meta: None)
    live.download_live(("atp",))
    receipt = json.loads((directory / "espn_acquisition.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "success_empty"
    assert receipt["overlay"]["status"] == "retained_last_good"
    assert receipt["overlay"]["lastGoodAt"] == "2026-08-20T09:00:00Z"


def test_http_200_without_an_events_list_is_not_success_empty(monkeypatch):
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"leagues": []}'

    monkeypatch.setattr(live.urllib.request, "urlopen", lambda request, timeout: _Response())
    try:
        live._fetch("atp")
    except ValueError as exc:
        assert "events list" in str(exc)
    else:
        raise AssertionError("malformed 200 response was treated as a quiet scoreboard")


def test_http_200_with_unkeyed_events_is_a_schema_failure(monkeypatch):
    class _Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"events": [{"shortName": "Unknown"}]}'

    monkeypatch.setattr(live.urllib.request, "urlopen", lambda request, timeout: _Response())
    try:
        live._fetch("atp")
    except ValueError as exc:
        assert "stable id" in str(exc)
    else:
        raise AssertionError("unkeyed event was discarded as if the scoreboard were empty")


def test_scoreboard_uses_the_host_that_serves_a_custom_user_agent():
    """`site.api.espn.com` 403s any custom User-Agent since 2026-08-04 and took both tours'
    overlay down; `site.web.api.espn.com` serves the identical payload. Locking the host
    here so the shorter one cannot be restored as a tidy-up."""
    assert "site.web.api.espn.com" in live.SCOREBOARD, live.SCOREBOARD
    print("ok test_scoreboard_uses_the_host_that_serves_a_custom_user_agent")


if __name__ == "__main__":
    test_round_label()
    test_draw_size()
    test_round_code_draw_relative()
    test_parse_events_slam_rounds_not_all_r64()
    test_score_winner_perspective()
    test_parse_events_completed_singles_only()
    test_parse_events_other_tour()
    test_parse_upcoming()
    test_parse_fields()
    test_placeholder_names_dropped()
    print("\nALL PASSED")
