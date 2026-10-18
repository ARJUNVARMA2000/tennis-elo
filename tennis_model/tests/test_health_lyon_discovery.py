"""Replay Lyon's real draw and empty same-name calendar listing through publication."""
import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.config import PLAYER_ALIASES
from tennis_model.data.health_checks.common import _FindingCollector
from tennis_model.data.names import name_key
from tennis_model.data.participants import is_real_participant
from tennis_model.sim import tournaments
from test_tournament_status import _Pred

from tennis_model.data import draws, draws_official, draws_wiki, events, health, live, source_audit

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/lyon_duplicate_listing_20261018.json').read_text())
NOW = CAPTURE['observedAt']
NAME = CAPTURE['events'][0]['name']
EID = '110-2026'
SHELL = '452-2026'


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 18, 22, 27, 45, tzinfo=UTC).astimezone(tz)


def bind(monkeypatch, tmp_path, observed):
    monkeypatch.setattr(draws, 'datetime', Clock)
    monkeypatch.setattr(events, 'datetime', Clock)
    for module in (draws, events, tournaments):
        monkeypatch.setattr(module, 'live_dir', lambda tour: tmp_path)
    (tmp_path / 'events.json').write_text(json.dumps(CAPTURE['registry']))
    (tmp_path / 'fields.json').write_text(json.dumps(live.parse_fields(observed, 'mens')))
    monkeypatch.setattr(draws_wiki, '_download_wiki_meta', lambda *args: None)
    monkeypatch.setattr(draws_official, 'fetch_official_draw', lambda *args: (None, ['captured fallback']))
    monkeypatch.setattr(draws_wiki, 'resolve_title', lambda *args: CAPTURE['draw']['title'])
    monkeypatch.setattr(draws_wiki, 'fetch_draw', lambda *args: copy.deepcopy(CAPTURE['draw']))
    monkeypatch.setattr(tournaments, 'resolve_surface_info', lambda *a, **kw: ('Hard', 'wikipedia'))
    monkeypatch.setattr(tournaments, 'resolve_level', lambda *a, **kw: 'ATP 250')
    schedule = live.parse_upcoming(observed, 'mens')
    schedule.to_csv(tmp_path / 'upcoming.csv', index=False)
    return schedule


def project_and_audit(observed, schedule, cache):
    names = {PLAYER_ALIASES.get(name_key(n), n)
             for entry in live.parse_fields(observed, 'mens').values() for n in entry['field']}
    names |= {PLAYER_ALIASES.get(name_key(n), n) for n in CAPTURE['draw']['slots']
              if is_real_participant(n)}
    frame = pd.DataFrame(columns=['date', 'tourney_name', 'winner_name', 'loser_name',
                                  'round', 'surface_b', 'best_of', 'tourney_level'])
    frame['date'] = pd.to_datetime(frame['date'])
    cards = tournaments.build_tournaments(_Pred(dict.fromkeys(names, 1500)), frame, 'atp',
                                           build_date='2026-10-18')
    raw, proof = source_audit.capture_source('atp', observed, NOW)
    data = {'meta': {'modelPlayerNames': sorted(names), 'tournamentSourceAudit': proof},
            'tournaments': cards,
            'brackets': [{**c, 'rounds': c['bracket']} for c in cards if c.get('bracket')],
            'upcoming': [{'espnId': r.espn_id, 'round': r.round,
                          'playerA': r.playerA, 'playerB': r.playerB, 'pA': .5}
                         for r in schedule.itertuples()]}
    out = _FindingCollector('output', 'atp')
    source_audit.check_source(out, 'atp',
                             {'state': 'valid', 'witness': json.loads(raw), 'proof': proof},
                             data, cache, NOW)
    assert all(health._gate_blocks(f) for f in out.findings)
    return cards, out.findings


@pytest.mark.parametrize('reverse', [False, True])
@pytest.mark.parametrize('shell_present', [False, True])
@pytest.mark.parametrize('warm', [False, True])
def test_lyon_discovery_survives_order_cache_and_shell_disappearance(
        monkeypatch, tmp_path, reverse, shell_present, warm):
    observed = copy.deepcopy(CAPTURE['events'] if shell_present else CAPTURE['events'][:1])
    if reverse:
        observed.reverse()
    schedule = bind(monkeypatch, tmp_path, observed)
    if warm:
        # A prior name-only discovery may have cached the draw under the empty ID.
        wrong = draws._normalize_entry(NAME, CAPTURE['draw'], legacy=True)
        wrong['espnId'] = SHELL
        (tmp_path / draws.CACHE_FILE).write_text(json.dumps({SHELL: wrong}))
    assert live.parse_event_meta(observed)[NAME]['espnId'] == EID
    for _ in range(2):
        draws.download_tournament_draws(['atp'], events_by_tour={'atp': observed})
        cache = draws.load_tournament_draws('atp')
        assert set(cache) == {EID}
        assert not draws.duplicate_draw_source_attachments(cache)
        cards, findings = project_and_audit(observed, schedule, cache)
        assert not findings, [(f.code, f.evidence) for f in findings]
        assert [c['espnId'] for c in cards] == [EID]
        assert cards[0]['bracketSize'] == 32
        assert cards[0]['drawSize'] == 28


def test_quarantined_duplicate_still_blocks_the_missing_real_event(monkeypatch, tmp_path):
    observed = copy.deepcopy(CAPTURE['events'])
    schedule = bind(monkeypatch, tmp_path, observed)
    draw = draws._normalize_entry(NAME, CAPTURE['draw'], legacy=True)
    broken = {eid: {**draw, 'espnId': eid} for eid in (EID, SHELL)}
    cache, duplicate_findings = draws._quarantine_duplicate_sources(broken)
    assert duplicate_findings and not cache
    (tmp_path / draws.CACHE_FILE).write_text(json.dumps(cache))
    cards, findings = project_and_audit(observed, schedule, cache)
    assert not cards
    assert [(f.code, f.entity) for f in findings] == [
        ('output.source_audit.event_missing', 'espn:' + EID)]


def test_same_name_cannot_supply_another_event_field_or_cached_draw(monkeypatch, tmp_path):
    bind(monkeypatch, tmp_path, CAPTURE['events'])
    real = {'espnId': EID, 'field': ['Player One', 'Player Two']}
    assert draws._lookup({NAME: real}, NAME, {'espnId': SHELL}) is None
    assert draws._field_evidence('atp', NAME, {'espnId': SHELL}) == []
    assert len(draws._field_evidence('atp', NAME, {'espnId': EID})) == 24  # four qualifiers unresolved


def test_registry_recovery_still_restores_an_event_with_its_own_field(monkeypatch, tmp_path):
    observed = CAPTURE['events']
    bind(monkeypatch, tmp_path, observed)
    events.update_registry('atp', live.parse_event_meta(observed))
    # The real listing ages out of discovery, but its ID-bound field remains.
    draws.download_tournament_draws(['atp'], events_by_tour={'atp': []})
    assert set(draws.load_tournament_draws('atp')) == {EID}


def test_populated_same_name_ids_are_not_merged_or_exempted_from_the_gate(monkeypatch, tmp_path):
    observed = copy.deepcopy(CAPTURE['events'])
    observed[1]['groupings'] = copy.deepcopy(observed[0]['groupings'])
    bind(monkeypatch, tmp_path, observed)
    # A second populated ID remains contradictory evidence; no calendar-shell
    # handling may teach the independent source gate to silently ignore it.
    schedule = live.parse_upcoming(observed[:1], 'mens')
    draws.download_tournament_draws(['atp'], events_by_tour={'atp': observed})
    cache = draws.load_tournament_draws('atp')
    _, findings = project_and_audit(observed, schedule, cache)
    assert any(f.code == 'output.source_audit.event_missing' and f.entity == 'espn:' + SHELL
               for f in findings)


def test_competition_preference_cannot_displace_a_different_edition():
    played, future = copy.deepcopy(CAPTURE['events'])
    future.update(date='2027-10-18T04:00Z', endDate='2027-10-26T03:59Z')
    assert live.parse_event_meta([future, played])[NAME]['espnId'] == SHELL
