"""Replay the source-order switch behind Shanghai's recurring missing result chain."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.data.alias_proposer import build_evidence, falsify
from tennis_model.data.health_checks.common import _FindingCollector
from tennis_model.data.names import name_key
from tennis_model.sim import tournaments
from test_tournament_status import _Pred

from tennis_model import config
from tennis_model.data import events, live, results, source_audit

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/shanghai_split_identity_20261017.json').read_text())
NOW = '2026-10-17T15:00:00Z'
EID = '315-2026'
REGISTRY = {'events': {EID: {'names': ['Shanghai', 'Rolex Shanghai Masters'],
                            'start': '2026-10-05', 'end': '2026-10-19'}}}


def snapshot(after_semis):
    event = copy.deepcopy(CAPTURE['event'])
    if not after_semis:
        event['groupings'][0]['competitions'] = [
            c for c in event['groupings'][0]['competitions'] if c['round']['id'] != '7']
        # Replay the earlier stage using the captured source facts: the two semis
        # were still scheduled. This changes which source group has the latest result.
        for c in event['groupings'][0]['competitions']:
            if c['round']['id'] == '6':
                c['status']['type'].update(completed=False, state='pre')
                for athlete in c['competitors']:
                    athlete.pop('winner', None)
                    athlete['linescores'] = []
    return event


def prepare(monkeypatch, tmp_path, event):
    for kind in ('historical', 'stats', 'fresh', 'live', 'lower'):
        folder = tmp_path / kind
        folder.mkdir(exist_ok=True)
        monkeypatch.setattr(results, kind + '_dir', lambda tour, p=folder: p)
    monkeypatch.setattr(results, '_read_historical', lambda tour: results._read_dir(tmp_path / 'historical'))
    monkeypatch.setattr(events, 'load_registry', lambda tour: REGISTRY)
    pd.DataFrame(CAPTURE['freshRows']).to_csv(tmp_path / 'fresh/2026.csv', index=False)
    live.parse_events([event], 'mens').to_csv(tmp_path / 'live/live.csv', index=False)
    monkeypatch.setattr(tournaments, 'load_registry', lambda tour: REGISTRY)
    monkeypatch.setattr(tournaments, '_load_fields', lambda tour: live.parse_fields([event], 'mens'))
    schedule = live.parse_upcoming([event], 'mens')
    pairs = [(r.playerA, r.playerB, r.round) for r in schedule.itertuples()]
    monkeypatch.setattr(tournaments, '_load_upcoming', lambda tour: {EID: pairs})
    monkeypatch.setattr(tournaments, '_load_upcoming_bounds', lambda tour: {})
    monkeypatch.setattr(tournaments, '_load_tournament_draws', lambda tour: {EID: CAPTURE['draw']})
    monkeypatch.setattr(tournaments, 'resolve_surface_info', lambda *a, **kw: ('Hard', 'official'))
    monkeypatch.setattr(tournaments, 'resolve_level', lambda *a, **kw: 'ATP 1000')
    return schedule


def project(merged):
    frame = merged.assign(surface_b='Hard', best_of=3)
    names = set(frame.winner_name) | set(frame.loser_name)
    predictor = _Pred(dict.fromkeys(names, 1500))
    cards = tournaments.build_tournaments(predictor, frame, 'atp', build_date='2026-10-17')
    card, = [c for c in cards if c.get('espnId') == EID]
    return card, sorted(names)


def audit(card, names, event, schedule):
    raw, proof = source_audit.capture_source('atp', [event], NOW)
    bracket = {**card, 'rounds': card['bracket']}
    data = {'meta': {'modelPlayerNames': names, 'tournamentSourceAudit': proof},
            'tournaments': [card], 'brackets': [bracket],
            'upcoming': [{'espnId': EID, 'round': r.round, 'playerA': r.playerA,
                          'playerB': r.playerB} for r in schedule.itertuples()]}
    out = _FindingCollector('output', 'atp')
    source_audit.check_source(out, 'atp', {'state': 'valid', 'witness': json.loads(raw), 'proof': proof},
                              data, {EID: CAPTURE['draw']}, NOW)
    return out.findings


def opening(card):
    return next(m for m in card['bracket'][0]['matches'] if m['a'] == 'Luca Van Assche')


def test_captured_alias_is_supported_by_official_id_and_full_retained_history():
    review = CAPTURE['identityReview']
    evidence = build_evidence(pd.DataFrame(CAPTURE['historyRows']))
    assert evidence.counts['bu yunchaokete'] == 7
    assert evidence.counts['yunchaokete bu'] == 428
    assert evidence.stable_ids['yunchaokete bu'] == {'Y09V'}
    assert falsify(review, {('player_alias', 'atp', ('Bu Yunchaokete', 'Yunchaokete Bu')): True}, evidence) is None
    assert config.PLAYER_ALIASES['bu yunchaokete'] == 'Yunchaokete Bu'


def test_unreviewed_split_reproduces_failure_then_apparent_recovery(monkeypatch, tmp_path):
    monkeypatch.delitem(config.PLAYER_ALIASES, 'bu yunchaokete')
    for after_semis in (False, True):
        event = snapshot(after_semis)
        schedule = prepare(monkeypatch, tmp_path, event)
        merged = results.merge_sources('atp', include_lower=False)
        card, names = project(merged)
        match = opening(card)
        assert match['winner'] == ('b' if after_semis else None)
        hits = audit(card, names, event, schedule)
        codes = {f.code for f in hits}
        # Even the apparently recovered bracket still exposes the split identity.
        assert 'output.source_audit.player_identity_unresolved' in codes
        assert ('output.source_audit.result_missing' in codes) is (not after_semis)


@pytest.mark.parametrize('after_semis', [False, True])
def test_repaired_real_merge_is_stable_across_repeated_refreshes(monkeypatch, tmp_path, after_semis):
    event = snapshot(after_semis)
    schedule = prepare(monkeypatch, tmp_path, event)
    for _ in range(2):
        merged = results.merge_sources('atp', include_lower=False)
        card, names = project(merged)
        assert 'Bu Yunchaokete' not in names
        match = opening(card)
        assert match['b'] == 'Yunchaokete Bu' and match['winner'] == 'b'
        assert match['score'] == '7-6(3) 6-3'
        assert card['mainDrawMatchCount'] == (94 if after_semis else 92)
        assert not audit(card, names, event, schedule)
        # Unrelated completed results survive; every public result is source-audited.
        assert merged.winner_name.ne(merged.loser_name).all()
        assert not merged.duplicated(['winner_name', 'loser_name', 'round']).any()
        assert name_key(live._athlete_name({'athlete': {'displayName': 'Bu Yunchaokete'}})) == 'yunchaokete bu'
