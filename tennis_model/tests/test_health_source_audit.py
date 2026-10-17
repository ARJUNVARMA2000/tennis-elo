"""Independent source witness must catch jointly corrupted public artifacts."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.config import PLAYER_ALIASES
from tennis_model.data.names import name_key
from tennis_model.sim.bracket import bracket_rounds, price_bracket
from test_health import _healthy_data, _oc

from tennis_model.data import health, live, source_audit

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/shanghai_walkover_20261012.json').read_text())
NOW = '2026-10-12T20:30:00Z'
PREFIX = 'output.source_audit.'


def baseline():
    event = copy.deepcopy(CAPTURE['event'])
    raw, proof = source_audit.capture_source('atp', [event], NOW)
    bracket = copy.deepcopy(CAPTURE['publicBracket'])
    slots = [m[s] for m in bracket['rounds'][0]['matches'] for s in ('a', 'b')]
    slots = [PLAYER_ALIASES.get(name_key(n), n) if n else n for n in slots]
    frame = live.parse_events([event], 'mens')
    for col in ('winner_name', 'loser_name'):
        frame[col] = frame[col].map(lambda n: PLAYER_ALIASES.get(name_key(n), n))
    bracket['rounds'] = bracket_rounds(slots, frame.to_dict('records'))
    price_bracket(bracket['rounds'], lambda a, b: .7, lambda a, b: .6)
    data = _healthy_data()
    data['meta'].update(modelPlayerNames=sorted(n for n in slots if n), tournamentSourceAudit=proof)
    data['brackets'] = [bracket]
    data['tournaments'] = [{**bracket, 'hasBracket': True}]
    data['upcoming'] = [{'espnId': r['espn_id'], 'round': r['round'],
                         'playerA': r['playerA'], 'playerB': r['playerB'], 'pA': .7}
                        for r in live.parse_upcoming([event], 'mens').to_dict('records')]
    oc = _oc(data=data)
    oc['source_audit'] = {'state': 'valid', 'witness': json.loads(raw), 'proof': proof}
    return oc


def findings(oc):
    hits = [f for f in health.output_findings('atp', oc, pd.Timestamp(NOW), observed_at=pd.Timestamp(NOW))
            if f.code.startswith(PREFIX)]
    assert all(health._gate_blocks(f) for f in hits)
    return {f.code.removeprefix(PREFIX) for f in hits}


def test_captured_96_entrant_80_result_eight_pending_baseline():
    assert not findings(baseline())


@pytest.mark.parametrize('kind,code', [
    ('remove_both', 'scheduled_match_missing'), ('wrong_opponent', 'scheduled_pair_mismatch'),
    ('wrong_round', 'scheduled_pair_mismatch'), ('wrong_winner', 'winner_mismatch'),
    ('wrong_score', 'score_mismatch'), ('lost_retirement', 'outcome_mismatch'),
    ('lost_walkover', 'outcome_mismatch'), ('duplicate_match', 'duplicate_match'),
    ('duplicate_entrant', 'duplicate_entrant'), ('completed_schedule', 'completed_match_scheduled'),
    ('missing_event', 'event_missing'), ('wrong_event_id', 'event_unwitnessed'),
    ('empty_source', 'event_unwitnessed'), ('missing_inventory', 'inventory_missing'),
    ('wrong_generation', 'generation_mismatch'), ('stale', 'witness_invalid'),
    ('missing_witness', 'witness_invalid'),
])
def test_broken_public_and_source_twins_block(kind, code):
    oc = baseline(); data = oc['data']; bracket = data['brackets'][0]
    pending = next(r for r in bracket['rounds'] if r['round'] == 'R16')['matches']
    first = pending[0]; pair = {first['a'], first['b']}
    done = next(m for r in bracket['rounds'] for m in r['matches'] if m.get('score') == '6-3 2-2 RET')
    if kind == 'remove_both':
        data['upcoming'] = [m for m in data['upcoming'] if {m['playerA'], m['playerB']} != pair]
        first['b'] = 'Qualifier 1'
    elif kind == 'wrong_opponent':
        first['b'], pending[1]['b'] = pending[1]['b'], first['b']
    elif kind == 'wrong_round':
        bracket['rounds'][3]['round'] = 'QF'
    elif kind == 'wrong_winner':
        done['winner'] = 'b' if done['winner'] == 'a' else 'a'
    elif kind == 'wrong_score':
        done['score'] = '6-1 6-0'
    elif kind == 'lost_retirement':
        done['score'] = '6-3 2-2'
    elif kind == 'lost_walkover':
        next(m for r in bracket['rounds'] for m in r['matches'] if m.get('score') == 'W/O')['score'] = None
    elif kind == 'duplicate_match':
        data['upcoming'].append(copy.deepcopy(data['upcoming'][0]))
    elif kind == 'duplicate_entrant':
        bracket['rounds'][0]['matches'][1]['a'] = bracket['rounds'][0]['matches'][0]['a']
    elif kind == 'completed_schedule':
        data['upcoming'].append({'espnId': '315-2026', 'round': 'R128',
                                 'playerA': done['a'], 'playerB': done['b'], 'pA': .5})
    elif kind == 'missing_event':
        data['tournaments'] = []
        oc['source_audit']['witness']['events'][0].update(date='2026-10-07', endDate='2026-10-18')
    elif kind == 'wrong_event_id':
        data['tournaments'][0]['espnId'] = 'other-2026'
    elif kind == 'empty_source':
        oc['source_audit']['witness']['events'] = []
    elif kind == 'missing_inventory':
        data['meta'].pop('modelPlayerNames')
    elif kind == 'wrong_generation':
        data['meta']['tournamentSourceAudit'] = {'sha256': 'old'}
    elif kind == 'stale':
        oc['source_audit']['witness']['observedAt'] = '2026-10-12T12:00:00Z'
    elif kind == 'missing_witness':
        oc['source_audit'] = {'state': 'invalid'}
    assert code in findings(oc)


def test_raw_and_cached_names_checked_but_newcomers_and_eliminated_qualifiers_allowed():
    oc = baseline()
    comps = oc['source_audit']['witness']['events'][0]['groupings'][0]['competitions']
    comp = copy.deepcopy(next(c for c in comps if c['round'].get('id') == '11'))
    comp['status']['type'].update(completed=False, state='pre')
    comp['competitors'][0]['athlete']['displayName'] = 'Minaur Alex de'
    comps.append(comp)
    assert 'player_identity_unresolved' in findings(oc)
    comp['competitors'][0]['athlete']['displayName'] = 'Genuine Newcomer'
    assert not findings(oc)
    comp['competitors'][0]['athlete']['displayName'] = 'Minaur Alex de'
    comp['competitors'][0]['winner'] = False
    comp['status']['type'].update(completed=True, state='post')
    assert not findings(oc)  # eliminated qualifiers do not manufacture main-draw incidents
    oc['draw_cache'] = {'315-2026': {'slots': ['Minaur Alex-de', 'Qualifier 1']}}
    assert 'player_identity_unresolved' in findings(oc)


def test_sponsor_rename_and_tiebreak_details_are_not_identity_changes():
    oc = baseline()
    oc['data']['tournaments'][0]['name'] = 'New sponsor'
    for r in oc['data']['brackets'][0]['rounds']:
        for m in r['matches']:
            if isinstance(m.get('score'), str):
                m['score'] = m['score'].replace('7-6', '7-6(5)')
    assert not findings(oc)


@pytest.mark.parametrize('fault', ['absent', 'corrupt', 'hash', 'tour', 'capture', 'count'])
def test_source_reader_rejects_missing_corrupt_and_mixed_acquisitions(tmp_path, fault):
    raw, proof = source_audit.capture_source('atp', [CAPTURE['event']], NOW)
    receipt = {'tour': 'atp', 'completedAt': NOW, 'eventCount': 1, 'sourceAudit': proof}
    (tmp_path / 'source_audit.json').write_bytes(raw)
    (tmp_path / 'espn_acquisition.json').write_text(json.dumps(receipt))
    assert source_audit.read_source(tmp_path, 'atp')['state'] == 'valid'
    if fault == 'absent':
        (tmp_path / 'source_audit.json').unlink()
    elif fault == 'corrupt':
        (tmp_path / 'source_audit.json').write_text('{')
    else:
        if fault == 'hash':
            receipt['sourceAudit']['sha256'] = 'wrong'
        if fault == 'tour':
            receipt['tour'] = 'wta'
        if fault == 'capture':
            receipt['completedAt'] = '2026-10-11T12:00:00Z'
        if fault == 'count':
            receipt['eventCount'] = 0
        (tmp_path / 'espn_acquisition.json').write_text(json.dumps(receipt))
    assert source_audit.read_source(tmp_path, 'atp')['state'] == 'invalid'


def test_download_captures_before_ingestion_mutates_names(tmp_path, monkeypatch):
    event = copy.deepcopy(CAPTURE['event'])
    monkeypatch.setattr(live, 'live_dir', lambda tour: tmp_path)
    monkeypatch.setattr(live, '_acquire_events', lambda tour: ([event], {
        'tour': tour, 'completedAt': NOW, 'eventCount': 1, 'status': 'success',
        'queries': {'succeeded': 1, 'failed': 0}}, None))
    original = live.parse_events
    def mutate(events, gender):
        events[0]['shortName'] = 'Changed by ingestion'
        return original(events, gender)
    monkeypatch.setattr(live, 'parse_events', mutate)
    monkeypatch.setattr('tennis_model.data.events.update_registry', lambda *a: None)
    live.download_live(('atp',))
    captured = source_audit.read_source(tmp_path, 'atp')
    assert captured['state'] == 'valid'
    assert captured['witness']['events'][0]['shortName'] == CAPTURE['event']['shortName']


def test_cache_order_detects_swapped_intact_pairs_before_later_opponents_exist():
    oc = baseline()
    opening = oc['data']['brackets'][0]['rounds'][0]['matches']
    slots = [m[s] for m in opening for s in ('a', 'b')]
    oc['draw_cache'] = {'315-2026': {'slots': slots}}
    assert not findings(oc)
    opening[1], opening[2] = opening[2], opening[1]
    assert 'draw_slot_mismatch' in findings(oc)


def test_genuine_unrated_pending_player_is_not_a_missing_forecast():
    oc = baseline()
    # Model inventory is independent of factual seating; genuinely unseen people remain.
    oc['data']['meta']['modelPlayerNames'].remove('Alexander Zverev')
    oc['data']['upcoming'] = [m for m in oc['data']['upcoming']
                              if 'Alexander Zverev' not in (m['playerA'], m['playerB'])]
    assert not findings(oc)


def test_source_snapshot_required_by_real_output_reader(tmp_path, monkeypatch):
    monkeypatch.setattr(health, 'live_dir', lambda tour: tmp_path / tour)
    monkeypatch.setattr(health, 'output_dir', lambda tour: tmp_path / 'out' / tour)
    snapshot = health.read_outputs('atp')
    assert snapshot['source_audit']['state'] == 'invalid'
    assert 'witness_invalid' in findings(snapshot)


def test_full_and_quick_share_export_and_unconditional_prepublication_gate():
    root = Path(__file__).resolve().parents[2]
    workflow = (root / '.github/workflows/refresh.yml').read_text()
    gate = workflow.split('      - name: Pre-deploy integrity gate\n', 1)[1].split('      - name:', 1)[0]
    assert 'if:' not in gate
    assert 'tennis_model.data.health --gate' in gate
    assert workflow.index('Pre-deploy integrity gate') < workflow.index('Publish accepted release data')
    assert workflow.index('Publish accepted release data') < workflow.index('      - name: Deploy to Firebase Hosting')
