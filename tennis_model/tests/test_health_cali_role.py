"""Cali #188–191: a provider qualifying label must not erase a reviewed main result."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from reviewed_fixtures import empty_reviewed_scope
from tennis_model.data.names import name_key
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import events, health, live, results, source_audit, wta_stats

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/cali_role_20261103.json').read_text())
EID = '1007-2026'
NOW = CAPTURE['observedAt']


def bind(monkeypatch, tmp_path):
    empty_reviewed_scope(monkeypatch, tmp_path / 'reviewed')
    for kind in ('historical', 'stats', 'fresh', 'live', 'lower'):
        folder = tmp_path / kind
        folder.mkdir()
        monkeypatch.setattr(results, kind + '_dir', lambda tour, p=folder: p)
    monkeypatch.setattr(config, 'stats_dir', lambda tour: tmp_path / 'stats')
    monkeypatch.setattr(results, '_read_historical',
                        lambda tour: results._read_dir(tmp_path / 'historical'))
    monkeypatch.setattr(results, 'wiki_categories_by_event_id', lambda tour: {EID: 'WTA 125'})
    monkeypatch.setattr(results, 'wiki_surface_lookup', lambda *a: {})
    registry = {'events': {EID: {'names': [CAPTURE['event']['name'], CAPTURE['wtaEvent']['name']],
                                 'start': '2026-11-01', 'end': '2026-11-08'}}}
    for module in (events, tournaments):
        monkeypatch.setattr(module, 'load_registry', lambda tour: registry)
    event = copy.deepcopy(CAPTURE['event'])
    live.parse_events([event], 'womens').to_csv(tmp_path / 'live/live.csv', index=False)
    # Reconstruct the persisted bad row from the captured provider payload, even after
    # acquisition is repaired: the hourly path must heal existing caches too.
    row = wta_stats._stats_row(CAPTURE['wtaEvent'], CAPTURE['wtaMatch'], CAPTURE['stats'], 'qual')
    row.update(draw_level='qual', tourney_level='Q', round='Q1')
    # Explicit unrelated model history makes the population-parity check nonempty.
    control = {**row, 'tourney_id': '2026-W99', 'tourney_name': 'Synthetic control',
               'source_match_id': 'LS001', 'tourney_date': '20261001',
               'played_date': '2026-10-01', 'event_start': '2026-10-01', 'event_end': '2026-10-07',
               'winner_name': 'Control A', 'loser_name': 'Control B',
               'draw_level': 'main', 'tourney_level': 'WTA250', 'round': 'R32'}
    pd.DataFrame([control]).to_csv(tmp_path / 'historical/control.csv', index=False)
    qualifier = {**control, 'source_match_id': 'RS004', 'winner_name': 'Control C',
                 'loser_name': 'Control D', 'draw_level': 'qual', 'tourney_level': 'Q', 'round': 'Q1'}
    pd.DataFrame([row, qualifier]).to_csv(tmp_path / 'lower/2026_wta_lower.csv', index=False)
    monkeypatch.setattr(tournaments, '_load_fields', lambda tour: live.parse_fields([event], 'womens'))
    schedule = live.parse_upcoming([event], 'womens')
    pairs = [(r.playerA, r.playerB, r.round) for r in schedule.itertuples()]
    monkeypatch.setattr(tournaments, '_load_upcoming', lambda tour: {EID: pairs})
    monkeypatch.setattr(tournaments, '_load_upcoming_bounds', lambda tour: {})
    monkeypatch.setattr(tournaments, '_load_tournament_draws', lambda tour: {EID: CAPTURE['draw']})
    monkeypatch.setattr(tournaments, 'resolve_surface_info', lambda *a, **kw: ('Clay', 'official'))
    monkeypatch.setattr(tournaments, 'resolve_level', lambda *a, **kw: 'WTA 125')
    from tennis_model.eval import track
    monkeypatch.setattr(track, 'FORECAST_DIR', tmp_path / 'forecasts')
    return event, schedule


def project_and_gate(event, schedule, merged):
    view = results.event_match_view(merged, 'wta')
    field = next(iter(live.parse_fields([event], 'womens').values()))['field']
    names = {config.PLAYER_ALIASES.get(name_key(n), n) for n in field}
    cards = tournaments.build_tournaments(_Pred(dict.fromkeys(names, 1500)), view, 'wta',
                                           build_date=NOW[:10], n_sims=100)
    card, = [c for c in cards if c.get('espnId') == EID]
    raw, proof = source_audit.capture_source('wta', [event], NOW)
    data = _healthy_data()
    data['meta'].update(modelPlayerNames=sorted(names), tournamentSourceAudit=proof)
    data.update(tournaments=cards, brackets=[{**card, 'rounds': card['bracket']}],
                upcoming=[{'espnId': EID, 'round': r.round, 'playerA': r.playerA,
                           'playerB': r.playerB, 'pA': .5} for r in schedule.itertuples()])
    oc = _oc(data=data, draw_cache={EID: CAPTURE['draw']})
    oc['source_audit'] = {'state': 'valid', 'witness': json.loads(raw), 'proof': proof}
    hits = [f for f in health.output_findings('wta', oc, pd.Timestamp(NOW), observed_at=pd.Timestamp(NOW))
            if f.code.startswith('output.source_audit.') or f.code == 'output.bracket.scheduled_match_missing']
    assert all(health._gate_blocks(f) for f in hits)
    return card, hits


def test_captured_provider_conflicts_with_independent_main_draw():
    match = CAPTURE['wtaMatch']
    assert match['DrawLevelType'] == 'Q' and match['MatchID'] == 'RS007'
    assert (match['EventYear'], match['EventID']) == (2026, '1110')
    assert (match['PlayerIDA'], match['PlayerIDB']) == ('319305', '319796')
    assert match['ScoreString'] == '6-1,6-0'
    assert 'SINGLES MAIN DRAW' in CAPTURE['pdf']['text']
    slots = CAPTURE['draw']['slots']
    assert slots[2:4] == ['Carolina Alves', 'Maria Paulina Perez Garcia']
    parsed = live.parse_events([CAPTURE['event']], 'womens')
    row, = parsed.loc[parsed.winner_name.eq('Carolina Alves')].to_dict('records')
    assert row['round'] == 'R32' and row['score'] == '6-1 6-0'


def test_broken_cache_blocks_all_four_original_findings(monkeypatch, tmp_path):
    event, schedule = bind(monkeypatch, tmp_path)
    monkeypatch.setattr(results, 'WTA_MATCH_ROLE_REPAIRS', {}, raising=False)
    merged = results.merge_sources('wta', include_lower=True)
    card, hits = project_and_gate(event, schedule, merged)
    assert {f.code for f in hits} == {
        'output.source_audit.winner_mismatch', 'output.source_audit.score_mismatch',
        'output.source_audit.scheduled_pair_mismatch', 'output.bracket.scheduled_match_missing'}
    assert card['bracket'][0]['matches'][1]['winner'] is None


@pytest.mark.parametrize('include_lower', [False, True])
def test_warm_cache_repair_preserves_population_and_restores_progression(monkeypatch, tmp_path, include_lower):
    event, schedule = bind(monkeypatch, tmp_path)
    with monkeypatch.context() as broken:
        broken.setattr(results, 'WTA_MATCH_ROLE_REPAIRS', {}, raising=False)
        before = results.merge_sources('wta', include_lower=include_lower)
    for _ in range(2):
        merged = results.merge_sources('wta', include_lower=include_lower)
        # Both main-only and enriched model populations stay excluded from this 125.
        assert len(merged) == 1 + int(include_lower)
        pd.testing.assert_frame_equal(before, merged)
        card, hits = project_and_gate(event, schedule, merged)
        assert not hits, [(f.code, f.evidence) for f in hits]
        opening = card['bracket'][0]['matches'][1]
        assert opening['a'] == 'Carolina Alves' and opening['winner'] == 'a'
        assert opening['score'] == '6-1 6-0'
        next_match = card['bracket'][1]['matches'][0]
        assert {next_match['a'], next_match['b']} == {'Carolina Alves', 'Leolia Jeanjean'}
        assert next_match['winner'] is None and next_match['p'] is not None


def test_fresh_acquisition_and_resume_use_the_reviewed_role(monkeypatch):
    event, match = CAPTURE['wtaEvent'], CAPTURE['wtaMatch']
    monkeypatch.setattr(wta_stats, '_paged', lambda *a, **kw: [copy.deepcopy(match)])
    monkeypatch.setattr(wta_stats, '_get', lambda *a, **kw: [copy.deepcopy(CAPTURE['stats'])])
    roles = {}
    row, = wta_stats.scrape_tournament(event, scope='lower', observed_roles=roles)
    assert (row['draw_level'], row['tourney_level'], row['round']) == ('chall', 'WTA125', 'R32')
    assert roles['id:2026-W1110:RS007'] == ('chall', 'WTA125', 'R32')
    monkeypatch.setattr(wta_stats, '_get', lambda *a, **kw: pytest.fail('refetched immutable stats'))
    assert wta_stats.scrape_tournament(event, scope='lower', known_keys={'id:2026-W1110:RS007'}) == []


@pytest.mark.parametrize('field,value', [('year', 2025), ('id', 9999)])
def test_repair_does_not_reclassify_other_editions(field, value):
    event = {**CAPTURE['wtaEvent'], field: value}
    assert wta_stats._match_draw_level(event, CAPTURE['wtaMatch']) == 'qual'


def test_other_qualifying_matches_keep_their_role():
    match = {**CAPTURE['wtaMatch'], 'MatchID': 'RS004'}
    assert wta_stats._match_draw_level(CAPTURE['wtaEvent'], match) == 'qual'
    row = wta_stats._stats_row(CAPTURE['wtaEvent'], match, CAPTURE['stats'], 'qual')
    stamped = results._stamp_draw_level(pd.DataFrame([row]), tour='wta')
    assert stamped.iloc[0]['draw_level'] == 'qual' and stamped.iloc[0]['round'] == 'Q1'


@pytest.mark.parametrize('tour,edition,match_id,expected', [
    ('wta', '2026-W1110', 'RS007', 'chall'),
    ('wta', '2025-W1110', 'RS007', 'qual'),
    ('wta', '2026-W9999', 'RS007', 'qual'),
    ('wta', '2026-W1110', 'RS004', 'qual'),
    ('atp', '2026-W1110', 'RS007', 'qual'),
])
def test_cached_role_repair_is_bound_to_exact_tour_edition_and_match(tour, edition, match_id, expected):
    row = wta_stats._stats_row(CAPTURE['wtaEvent'], CAPTURE['wtaMatch'], CAPTURE['stats'], 'qual')
    row.update(tourney_id=edition, source_match_id=match_id, draw_level='qual', round='Q1')
    stamped = results._stamp_draw_level(pd.DataFrame([row]), tour=tour).iloc[0]
    assert stamped['draw_level'] == expected
    assert stamped['round'] == ('R32' if expected == 'chall' else 'Q1')
