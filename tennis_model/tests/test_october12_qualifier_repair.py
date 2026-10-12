"""Lisboa's released draw still had four qualifiers after ESPN named their matches."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.data.names import name_key
from tennis_model.model import upcoming
from tennis_model.sim import tournaments
from tennis_model.sim.bracket import is_real, resolve_scheduled_placeholders
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import health, results, surface

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/lisboa_qualifiers_20261012.json').read_text())
CODE = 'output.bracket.scheduled_match_missing'
EXPECTED = {9: 'Mathilde Lollia', 14: 'Gina Feistel', 19: 'Raluka Serban', 20: 'Adrienn Nagy'}


def _build(monkeypatch, live=False, edit=None):
    rows = copy.deepcopy(CAPTURE['upcoming'])
    if edit:
        for row in rows:
            row.update(edit)
    monkeypatch.setattr(upcoming, 'load_upcoming', lambda tour: pd.DataFrame(rows))
    monkeypatch.setattr(tournaments, '_load_upcoming_bounds', lambda tour: {})
    monkeypatch.setattr(tournaments, '_load_tournament_draws', lambda tour: {'1079-2026': CAPTURE['draw']})
    monkeypatch.setattr(tournaments, '_load_fields', lambda tour: {'Renamed sponsor': CAPTURE['field']})
    monkeypatch.setattr(tournaments, 'load_registry', lambda tour: {'events': {}})
    monkeypatch.setattr(tournaments, 'resolve_surface_info', lambda *a, **kw: ('Clay', 'wiki'))
    monkeypatch.setattr(tournaments, 'resolve_level', lambda *a, **kw: 'WTA 125')
    from tennis_model.eval import track
    monkeypatch.setattr(track, '_read_log', lambda path: [])
    names = {config.PLAYER_ALIASES.get(name_key(n), n) for n in CAPTURE['field']['field']}
    predictor = _Pred(dict.fromkeys(names, 1500))
    frame = pd.DataFrame(CAPTURE['results'])
    frame['date'] = pd.to_datetime(frame.tourney_date)
    frame = frame.assign(surface_b='Clay', surface_src='wiki', best_of=3,
                         tourney_level='125', draw_level='chall')
    if not live:
        frame = frame.iloc[:0]
    card, = tournaments.build_tournaments(predictor, frame, 'wta',
                                          build_date='2026-10-12', n_sims=32)
    data = _healthy_data()
    data['meta']['modelPlayerNames'] = sorted(names)
    data.update(brackets=[{**card, 'rounds': card['bracket']}], tournaments=[card],
                upcoming=[{'espnId': r['espn_id'], 'event': 'Another sponsor',
                           'round': r['round'], 'playerA': r['playerA'], 'playerB': r['playerB'],
                           'pA': .5} for r in rows])
    findings = health.output_findings('wta', _oc(data=data), pd.Timestamp('2026-10-12'))
    return card, findings


@pytest.mark.parametrize('live', [False, True])
def test_captured_qualifiers_reach_prestart_and_live_producer_and_gate(monkeypatch, live):
    assert len(CAPTURE['draw']['slots']) == 32
    assert [p + 1 for p in EXPECTED] == CAPTURE['officialDraw']['unresolvedPositions']
    with monkeypatch.context() as broken:
        broken.setattr(tournaments, 'resolve_scheduled_placeholders', lambda slots, pairs: slots)
        _, findings = _build(broken, live)
        hits = [f for f in findings if f.code == CODE]
        assert len(hits) == 4 and all(health._gate_blocks(f) for f in hits)
    card, findings = _build(monkeypatch, live)
    assert card['status'] == ('live' if live else 'upcoming')
    assert card['drawSize'] == 32
    assert not {CODE, 'output.bracket.upcoming_probability_mismatch',
                'output.bracket.pending_probability_missing'} & {f.code for f in findings}
    matches = card['bracket'][0]['matches']
    for pos, name in EXPECTED.items():
        match = matches[pos // 2]
        assert match['b' if pos % 2 else 'a'] == name
        assert match['winner'] is None and match['p'] == .5
    assert sum(m['winner'] is not None for m in matches) == (len(CAPTURE['results']) if live else 0)
    assert all(not is_real(CAPTURE['draw']['slots'][pos]) for pos in EXPECTED)


@pytest.mark.parametrize('edit', [{'round': 'Q2'}, {'round': 'R16'}, {'round': ''},
                                  {'espn_id': 'other-2026'},
                                  {'espn_id': 'other-2026', 'tourney_name': 'Another event'}])
def test_only_same_event_opening_round_can_fill_slots(monkeypatch, edit):
    card, _ = _build(monkeypatch, edit=edit)
    for pos in EXPECTED:
        match = card['bracket'][0]['matches'][pos // 2]
        assert not is_real(match['b' if pos % 2 else 'a'])
        assert match['winner'] is None and match['p'] is None


def test_ambiguous_duplicate_incumbent_and_bye_seats_stay_unchanged():
    slots = ['A', 'Qualifier 1', 'B', 'Qualifier 2', 'C', None, 'D', 'E']
    for pairs in [[('A', 'X'), ('A', 'Y')], [('A', 'X'), ('B', 'X')],
                  [('A', 'X'), ('C', 'X')],
                  [('A', 'D')], [('C', 'X')], [('D', 'X')], [('A', 'Qualifier 3')]]:
        assert resolve_scheduled_placeholders(slots, pairs) == slots
    assert resolve_scheduled_placeholders(slots, [('A', 'X'), ('X', 'A')])[1] == 'X'


def test_reviewed_mallorca_tier_reaches_ingestion_without_admitting_125_rows(monkeypatch):
    from tennis_model.data import events
    monkeypatch.setattr(events, 'load_registry', lambda tour: {'events': {}})
    monkeypatch.setattr(surface, 'wiki_category_map', lambda tour: {})
    monkeypatch.setattr(config, 'INCLUDE_WTA_125', False)
    frame = pd.DataFrame(CAPTURE['mallorcaResults'])
    assert len(frame) == 5
    with monkeypatch.context() as broken:
        broken.setattr(surface, 'EVENT_TIER_BY_ID', {})
        old = results._stamp_live_result_policy('wta', frame)
        assert old.attrs['excluded_unclassified_wta_event_ids'] == ('1020-2026',)
    fixed = results._stamp_live_result_policy('wta', frame)
    assert fixed['__policy_excluded'].all()
    assert fixed.attrs['excluded_unclassified_wta_event_ids'] == ()
    assert fixed.attrs['excluded_wta125_event_ids'] == ('1020-2026',)
    for stamped, expected in [(old, True), (fixed, False)]:
        data = _healthy_data()
        unknown = stamped.attrs['excluded_unclassified_wta_event_ids']
        data['meta']['excludedUnclassifiedWtaLiveMatches'] = int(stamped.espn_id.isin(unknown).sum())
        findings = health.output_findings('wta', _oc(data=data), pd.Timestamp('2026-10-12'))
        assert any(f.code == 'output.population.unclassified_live_withheld' for f in findings) == expected
    assert '1020-2026' not in surface.wiki_categories_by_event_id('atp')
    assert '1020-2025' not in surface.wiki_categories_by_event_id('wta')
