"""Guangzhou qualifying must join Wong's official name to the same rated history."""
import copy
import json
from pathlib import Path

import pandas as pd
from reviewed_fixtures import empty_reviewed_scope
from tennis_model.data.alias_proposer import build_evidence, falsify, player_questions
from test_health import _healthy_data, _oc

from tennis_model import config
from tennis_model.data import events, health, results, source_audit

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/guangzhou_wong_identity_20261023.json').read_text())
CANONICAL = 'Hong Yi Cody Wong'
VARIANT = 'Wong Hong Yi Cody'
KEY = 'wong hong yi cody'


def test_captured_qualifier_blocks_split_rated_names_then_passes_reviewed_alias(monkeypatch):
    event = copy.deepcopy(CAPTURE['event'])
    comp = next(c for c in event['groupings'][0]['competitions']
                if any(a['athlete'].get('displayName') == CANONICAL for a in c['competitors']))
    assert comp['round']['id'] == '11'
    assert not comp['status']['type']['completed']
    raw, proof = source_audit.capture_source('wta', [event], CAPTURE['observedAt'])
    data = _healthy_data()
    data['meta'].update(tournamentSourceAudit=proof, modelPlayerNames=[CANONICAL, VARIANT])
    data.update(tournaments=[{'espnId': event['id'], 'status': 'upcoming'}], brackets=[], upcoming=[])
    oc = _oc(data=data)
    oc['source_audit'] = {'state': 'valid', 'witness': json.loads(raw), 'proof': proof}

    def findings():
        return [f for f in health.output_findings('wta', oc, pd.Timestamp(CAPTURE['observedAt']))
                if f.code.startswith('output.source_audit.')]

    with monkeypatch.context() as broken:
        broken.delitem(config.PLAYER_ALIASES, KEY)
        hit, = findings()
        assert hit.code == 'output.source_audit.player_identity_unresolved'
        assert hit.entity == 'espn:232-2026#player:hong yi cody wong'
        assert hit.evidence == {'player': CANONICAL, 'candidates': [VARIANT], 'role': 'qualifying'}
        assert health._gate_blocks(hit)
    data['meta']['modelPlayerNames'] = [CANONICAL]
    assert not findings()
    assert not findings()  # repeated refresh keeps the independent qualifier check clean


def test_reviewed_identity_has_matching_official_result_and_survives_falsifier(monkeypatch):
    frame = pd.DataFrame(CAPTURE['historyRows']).fillna('')
    evidence = build_evidence(frame)
    assert evidence.counts['hong yi cody wong'] == 16
    assert evidence.counts[KEY] == 1
    review = CAPTURE['identityReview']
    with monkeypatch.context() as before_review:
        before_review.delitem(config.PLAYER_ALIASES, KEY)
        questions = player_questions(evidence, 'wta')
    question, = [q for q in questions if q.subject == tuple(sorted((VARIANT, CANONICAL)))]
    assert 'different order' in question.context
    asked = {question.key: question}
    assert falsify(review, asked, evidence) is None
    official = frame[(frame.capturedSource == 'stats/2025.csv') & (frame.loser_name == CANONICAL)].iloc[0]
    mirror = frame[frame.loser_name == VARIANT].iloc[0]
    assert official.loser_id == review['wtaId'] == '326723'
    for key, expected in [('winner_name', 'Viktoria Morvayova'), ('score', '6-1 6-0'),
                          ('tourney_name', 'Hong Kong'), ('round', 'R32')]:
        assert official[key] == mirror[key] == expected


def test_real_merge_collapses_the_duplicate_result_and_preserves_other_history(monkeypatch, tmp_path):
    empty_reviewed_scope(monkeypatch, tmp_path / 'reviewed')
    for kind in ('historical', 'stats', 'fresh', 'live', 'lower'):
        folder = tmp_path / kind
        folder.mkdir()
        monkeypatch.setattr(results, kind + '_dir', lambda tour, p=folder: p)
        rows = [r for r in CAPTURE['historyRows'] if r['capturedSource'].startswith(kind + '/')]
        if rows:
            pd.DataFrame(rows).to_csv(folder / 'captured.csv', index=False)
    monkeypatch.setattr(results, '_read_historical', lambda tour: results._read_dir(tmp_path / 'historical'))
    monkeypatch.setattr(events, 'load_registry', lambda tour: {'events': {}})
    with monkeypatch.context() as broken:
        broken.delitem(config.PLAYER_ALIASES, KEY)
        before = results.merge_sources('wta', include_lower=True)
    after = results.merge_sources('wta', include_lower=True)
    repeated = results.merge_sources('wta', include_lower=True)
    assert VARIANT in set(before.loser_name)
    assert len(before) == len(after) + 1
    assert VARIANT not in set(after.winner_name) | set(after.loser_name)
    assert (after.winner_name != after.loser_name).all()
    assert len(after[(after.winner_name == 'Viktoria Morvayova') & (after.loser_name == CANONICAL)]) == 1
    unaffected = before[before.loser_name != VARIANT]
    columns = ['winner_name', 'loser_name', 'score', 'round', 'date']
    key = ['date', 'winner_name', 'loser_name']
    pd.testing.assert_frame_equal(unaffected[columns].sort_values(key).reset_index(drop=True),
                                  after[columns].sort_values(key).reset_index(drop=True))
    pd.testing.assert_frame_equal(after, repeated)
