"""Replay Paris's eight Q/SE seats through parsing, warm cache, producer and gate.

The fixture is explicitly reconstructed from the later official draw and issue evidence,
not represented as the original failed provider acquisition.
"""
import copy
import json
import re
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _Pred

from tennis_model.data import draws, draws_official, health, participants, source_audit

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/paris_special_exempt_20261031.json').read_text())
NOW = '2026-10-31T17:00:00Z'
ROLE = 'Qualifier / Special Exempt'
GEOMETRY = {'output.tournament.draw_geometry_invalid', 'output.bracket.geometry_invalid'}
SCHEDULE = {'output.source_audit.entrant_missing', 'output.source_audit.scheduled_pair_mismatch',
            'output.bracket.scheduled_match_missing'}


def _official_text():
    lines = ['Rolex Paris Masters', '2 November — 8 November 2026', 'Main Draw Singles']
    for pos, name in enumerate(FIXTURE['draw']['slots'], 1):
        if name is None:
            label = 'Bye'
        elif name == ROLE:
            label = ROLE
        else:
            given, surname = name.split(' ', 1)
            label = f'{surname.upper()}, {given}'
        lines.append(f' {pos}   {label}          FRA')
    return '\n'.join(lines)


def _build(monkeypatch, tmp_path, cold, live=False):
    raw = copy.deepcopy(FIXTURE['draw'])
    if cold:
        raw.update(draws_official.parse_official_text(_official_text()))
    names = {n for n in FIXTURE['draw']['slots'] if n and n != ROLE} | {'Jan-Lennard Struff'}
    _, _, shared = draws_official._reconcile_slots(raw['slots'], raw['seeds'], names)
    raw.update(evidencePlayers=shared, evidenceFieldPlayers=len(names))
    (tmp_path / draws.CACHE_FILE).write_text(json.dumps({'13-2026': raw}))
    monkeypatch.setattr(draws, 'live_dir', lambda tour: tmp_path)
    draw = draws.load_tournament_draws('atp')['13-2026']
    field = {'espnId': '13-2026', 'field': sorted(names),
             'eliminated': ['Hubert Hurkacz'] if live else []}
    monkeypatch.setattr(tournaments, '_load_fields', lambda tour: {'Different sponsor': field})
    monkeypatch.setattr(tournaments, '_load_upcoming', lambda tour: {
        '13-2026': [('Arthur Gea', 'Jan-Lennard Struff', 'R64')]})
    monkeypatch.setattr(tournaments, '_load_upcoming_bounds', lambda tour: {})
    monkeypatch.setattr(tournaments, 'load_registry', lambda tour: {'events': {}})
    monkeypatch.setattr(tournaments, 'resolve_surface_info', lambda *a, **kw: ('Hard', 'wiki'))
    monkeypatch.setattr(tournaments, 'resolve_level', lambda *a, **kw: 'Masters 1000')
    from tennis_model.eval import track
    monkeypatch.setattr(track, '_read_log', lambda path: [])
    frame = pd.DataFrame(columns=['tourney_name', 'date', 'round'])
    now = NOW
    if live:
        now = '2026-11-02T17:00:00Z'
        frame = pd.DataFrame([{
            'tourney_name': raw['name'], 'espn_id': '13-2026',
            'date': pd.Timestamp('2026-11-02'), 'round': 'R64',
            'winner_name': 'Lorenzo Musetti', 'loser_name': 'Hubert Hurkacz',
            'score': '6-4 6-4', 'surface_b': 'Hard', 'surface_src': 'wiki',
            'best_of': 3, 'tourney_level': 'M', 'draw_level': 'main',
        }])
    card, = tournaments.build_tournaments(
        _Pred(dict.fromkeys(names, 1500)), frame, 'atp', build_date=now[:10], n_sims=32)
    data = _healthy_data()
    event = {'id': '13-2026', 'name': 'Rolex Paris Masters',
             'date': '2026-11-02', 'endDate': '2026-11-08', 'groupings': [{
                 'grouping': {'slug': 'mens-singles'}, 'competitions': [{
                     'id': 'paris-gea-struff', 'round': {'id': '1'},
                     'status': {'type': {'state': 'pre', 'completed': False}},
                     'competitors': [{'athlete': {'displayName': name}}
                                     for name in FIXTURE['provenance']['scheduledPair']],
                 }],
             }]}
    raw_source, proof = source_audit.capture_source('atp', [event], now)
    data['meta'].update(modelPlayerNames=sorted(names), tournamentSourceAudit=proof)
    data.update(tournaments=[{**card, 'hasBracket': True}],
                brackets=[{**card, 'rounds': card['bracket']}],
                upcoming=[{'espnId': '13-2026', 'event': 'Different sponsor', 'round': 'R64',
                           'playerA': 'Arthur Gea', 'playerB': 'Jan-Lennard Struff', 'pA': .5}])
    oc = _oc(data=data, draw_cache={'13-2026': draw})
    oc['source_audit'] = {'state': 'valid', 'witness': json.loads(raw_source), 'proof': proof}
    findings = health.output_findings('atp', oc, pd.Timestamp(now), observed_at=pd.Timestamp(now))
    relevant = [f for f in findings if f.code.startswith((
        'output.tournament.', 'output.bracket.', 'output.source_audit.'))]
    return card, relevant, draw


@pytest.mark.parametrize('cold', [False, True])
@pytest.mark.parametrize('live', [False, True])
def test_paris_broken_and_clean_producer_gate_replay(monkeypatch, tmp_path, cold, live):
    assert FIXTURE['draw']['slots'].count(ROLE) == 8
    with monkeypatch.context() as broken:
        # Executable previous vocabulary, shared by parser, projector and gate.
        broken.setattr(participants, '_COMBINED_RE', re.compile(
            rf'^(?:q|qualifier)/(?:ll|lucky\s+loser){participants._NUMBER}$'))
        card, findings, _ = _build(broken, tmp_path, cold, live)
        assert card['drawSize'] == 49
        assert GEOMETRY | SCHEDULE | {'output.source_audit.duplicate_entrant'} <= {
            f.code for f in findings}
        assert all(health._gate_blocks(f) for f in findings)

    card, findings, draw = _build(monkeypatch, tmp_path, cold, live)
    assert not findings
    assert card['drawSize'] == 56 and card['bracketSize'] == 64
    assert card['status'] == ('live' if live else 'upcoming') and card['drawStatus'] == 'real'
    assert not draws._draw_is_settled(draw)
    ordered = [m[s] for m in card['bracket'][0]['matches'] for s in ('a', 'b')]
    assert sum(n is None for n in ordered) == 8
    assert len({n for n in ordered if n is not None}) == 56
    assert ordered[34:36] == ['Jan-Lennard Struff', 'Arthur Gea']
    assert card['bracket'][0]['matches'][17]['p'] == .5
    assert card['bracket'][0]['matches'][17]['winner'] is None
    # The two adjacent unknown qualifiers remain distinct and receive no invented price.
    assert ordered[20] != ordered[21]
    assert card['bracket'][0]['matches'][10]['p'] is None
    assert sum(m['winner'] is not None for m in card['bracket'][0]['matches']) == 8 + int(live)
    assert _build(monkeypatch, tmp_path, cold, live)[0] == card
