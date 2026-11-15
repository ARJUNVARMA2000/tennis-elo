"""Current-source replay of the March Austin draw attached to a November calendar."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from tennis_model.data import draws, draws_wiki, event_coverage, live

CAPTURE = json.loads((Path(__file__).parent / "fixtures/austin_wrong_edition_20261115.json").read_text())
TITLE = CAPTURE["singles"]["title"]
NOVEMBER = {"espnId": "1031-2026", "start": "2026-11-07", "end": "2026-11-15"}
MARCH = {"espnId": "1063-2026", "start": "2026-03-08", "end": "2026-03-14"}


class _Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 11, 15, 14, tzinfo=UTC)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


@pytest.fixture
def source(monkeypatch, tmp_path):
    articles = {CAPTURE[k]["title"]: CAPTURE[k]["wikitext"] for k in ("singles", "main")}
    monkeypatch.setattr(draws_wiki, "resolve_title", lambda *_args: TITLE)
    monkeypatch.setattr(draws_wiki, "_wikitext", lambda title: articles.get(title))
    monkeypatch.setattr(draws_wiki, "_download_wiki_meta", lambda *_args: None)
    monkeypatch.setattr(draws, "live_dir", lambda _tour: tmp_path)
    monkeypatch.setattr(draws, "datetime", _Clock)
    monkeypatch.setattr(draws_wiki, "datetime", _Clock)
    monkeypatch.setattr(draws, "_field_evidence", lambda *_args: [])
    monkeypatch.setattr(draws, "update_registry", lambda *_args: {"events": {}})
    monkeypatch.setattr(draws, "load_registry", lambda *_args: {"events": {}})
    return articles


def _old_draw(meta=NOVEMBER):
    raw = {
        **draws_wiki._parse_bracket(CAPTURE["singles"]["wikitext"]),
        **meta, "title": TITLE,
        "url": "https://en.wikipedia.org/wiki/2026_Austin_Challenger_%E2%80%93_Singles",
        "retrieved": "2026-11-10",
    }
    raw["drawSize"] = sum(slot is not None for slot in raw["slots"])
    return draws._normalize_entry("Austin 125", raw, legacy=True)


def test_source_dates_reject_same_year_wrong_edition_and_accept_real_march(source):
    assert draws_wiki.fetch_draw("Austin 125", 2026, "wta", NOVEMBER) is None
    real = draws_wiki.fetch_draw("Austin 125 2", 2026, "wta", MARCH)
    assert (real["sourceStart"], real["sourceEnd"]) == ("2026-03-09", "2026-03-14")
    assert (real["start"], real["end"]) == (MARCH["start"], MARCH["end"])
    assert real["slots"][:4] == ["Emma Navarro", "Lulu Sun", "Paula Badosa", "Elena-Gabriela Ruse"]


@pytest.mark.parametrize("date_field,year,expected", [
    ("date=9–14 March", 2026, ("2026-03-09", "2026-03-14")),
    ("date=9–14 March 2025", 2025, ("2025-03-09", "2025-03-14")),
    ("dates=27 October – 2 November 2026", 2026, ("2026-10-27", "2026-11-02")),
    ("date=September 28–October 4, 2026", 2026, ("2026-09-28", "2026-10-04")),
])
def test_source_dates_read_infobox_year_instead_of_requested_year(date_field, year, expected):
    raw = "{{Infobox tennis event|" + str(year) + "|Austin Challenger|" + date_field + "}}"
    assert draws_wiki._article_dates(raw, 2099) == expected


def test_missing_or_conflicting_independent_dates_cannot_borrow_espn_dates(source):
    source[CAPTURE["main"]["title"]] = "{{Infobox tennis event|2026|Austin Challenger|surface=Hard}}"
    assert draws_wiki.fetch_draw("Austin 125", 2026, "wta", MARCH) is None
    assert draws_wiki._article_dates(
        "{{Infobox tennis event|2025|Austin Challenger|date=9–14 March 2026}}", 2026) is None


def test_source_dates_support_the_retained_valle_tennis_event_info_header():
    # Current article captured on November 15; this is not the original acquisition.
    # https://en.wikipedia.org/wiki/2026_Valle_D%27Aosta_Ladies_Open
    raw = (Path(__file__).parent / "fixtures/valle_main_20261115.wiki").read_text()
    assert draws_wiki._article_dates(raw, 2026) == ("2026-10-26", "2026-11-01")


def test_source_title_year_cannot_be_replaced_by_requested_year(monkeypatch):
    raw = "{{Infobox tennis event|date=9–14 March}}"
    assert draws_wiki._draw_article_dates("2025 Austin Challenger", raw, 2026) == (
        "2025-03-09", "2025-03-14")


@pytest.mark.parametrize("previous", [None, "legacy", "contradictory"])
@pytest.mark.parametrize("end", ["2026-11-15", "2026-11-14"])
def test_wrong_edition_never_survives_current_or_ended_cache_shortcuts(source, previous, end):
    meta = {**NOVEMBER, "end": end}
    old = _old_draw(meta) if previous else None
    if previous == "contradictory":
        old.update(sourceStart="2026-03-09", sourceEnd="2026-03-14")
    entry, _rejected = draws._resolve_one("wta", "Austin 125", meta, {}, old)
    assert entry is None


def test_valid_ended_legacy_draw_upgrades_its_proof_before_cache_reuse(source):
    old = _old_draw(MARCH)
    upgraded, _rejected = draws._resolve_one("wta", "Austin 125 2", MARCH, {}, old)
    assert upgraded["slots"] == old["slots"]
    assert (upgraded["sourceStart"], upgraded["sourceEnd"]) == ("2026-03-09", "2026-03-14")
    assert "sourceStart" not in old


def test_valid_prestart_wikipedia_draw_keeps_its_schedule_and_slots(source, monkeypatch):
    monkeypatch.setattr(draws, "datetime", type("BeforeMarch", (datetime,), {
        "now": classmethod(lambda cls, tz=None: datetime(2026, 3, 7, tzinfo=UTC))}))
    entry, _rejected = draws._resolve_one("wta", "Austin 125 2", MARCH, {}, None)
    assert entry["espnId"] == "1063-2026"
    assert draws._wikipedia_evidence_is_valid(entry, "Austin 125 2", 2026, "wta", MARCH)
    schedule = draws._rows_from_draws({"1063-2026": entry}, today="2026-03-07")
    assert len(schedule) == 16
    assert schedule[0]["playerA"] == "Emma Navarro"


@pytest.mark.parametrize("legacy_file", [False, True])
def test_shared_offline_reader_quarantines_old_draw_and_preserves_espn_schedule(
        source, monkeypatch, tmp_path, legacy_file):
    from tennis_model.model import upcoming

    old = _old_draw()
    filename = draws.LEGACY_CACHE_FILE if legacy_file else draws.CACHE_FILE
    (tmp_path / filename).write_text(json.dumps({"1031-2026": old}))
    monkeypatch.setattr(upcoming, "live_dir", lambda _tour: tmp_path)
    pd.DataFrame([{
        "tourney_name": "WTA Finals", "espn_id": "382-2026", "tourney_date": "2026-11-15",
        "round": "F", "playerA": "Real Player A", "playerB": "Real Player B",
    }]).to_csv(tmp_path / "upcoming.csv", index=False)
    assert draws.load_tournament_draws("wta") == {}
    loaded = upcoming.load_upcoming("wta")
    assert list(loaded["espn_id"]) == ["382-2026"]
    assert draws.tournament_draw_upcoming_rows("wta") == []


def test_repeated_draw_refresh_removes_stolen_cache_without_inventing_begun_event(
        source, monkeypatch, tmp_path):
    from tennis_model.sim import tournaments
    from test_tournament_status import _Pred

    (tmp_path / draws.CACHE_FILE).write_text(json.dumps({"1031-2026": _old_draw()}))
    registry = {"events": {"1031-2026": {"name": "Austin 125", "names": ["Austin 125"], **NOVEMBER}}}
    monkeypatch.setattr(draws, "update_registry", lambda *_args: registry)
    monkeypatch.setattr(tournaments, "load_registry", lambda _tour: registry)
    monkeypatch.setattr(tournaments, "_load_fields", lambda _tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming", lambda _tour: {})
    monkeypatch.setattr(tournaments, "_load_upcoming_bounds", lambda _tour: {})
    frame = pd.DataFrame(columns=["date", "tourney_name", "round", "winner_name", "loser_name"])
    frame["date"] = pd.to_datetime(frame["date"])
    for _ in range(2):
        draws.download_tournament_draws(["wta"], events_by_tour={"wta": [copy.deepcopy(CAPTURE["espn"]["event"])]})
        assert json.loads((tmp_path / draws.CACHE_FILE).read_text()) == {}
        assert draws.load_tournament_draws("wta") == {}
        assert live.parse_fields([CAPTURE["espn"]["event"]], "womens") == {}
        assert tournaments.build_tournaments(_Pred({}), frame, "wta", build_date="2026-11-15") == []
        coverage = event_coverage.build_event_coverage(
            frame, "wta", build_date="2026-11-15", registry=registry, draws={},
            upcoming_df=pd.DataFrame())
        assert coverage["events"] == []


def test_unlisted_retained_legacy_draw_upgrades_proof_and_rejects_wrong_calendar(
        source, monkeypatch, tmp_path):
    # Same completed source is safe in March and wrong when relabelled as November.
    good = _old_draw(MARCH)
    bad = _old_draw(NOVEMBER)
    monkeypatch.setattr(draws, "_retained", lambda *_args: True)
    (tmp_path / draws.CACHE_FILE).write_text(json.dumps({"1063-2026": good, "1031-2026": bad}))
    draws.download_tournament_draws(["wta"], events_by_tour={"wta": []})
    persisted = json.loads((tmp_path / draws.CACHE_FILE).read_text())
    assert set(persisted) == {"1063-2026"}
    assert persisted["1063-2026"]["sourceStart"] == "2026-03-09"
    assert set(draws.load_tournament_draws("wta")) == {"1063-2026"}
