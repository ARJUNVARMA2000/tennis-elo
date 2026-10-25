"""Issue #174: the announced qualifier must join Zongyu Li's retained WTA history."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from reviewed_fixtures import empty_reviewed_scope
from tennis_model.data.alias_proposer import build_evidence, falsify, player_questions
from test_health import _healthy_data, _oc

from tennis_model import config
from tennis_model.data import events, health, live, results, source_audit

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/valle_daosta_li_identity_20261025.json').read_text())
CANONICAL = 'Zongyu Li'
VARIANT = 'Li Zongyu'
KEY = 'li zongyu'


@pytest.mark.parametrize('inventory', [[CANONICAL], [CANONICAL, VARIANT]])
def test_captured_qualifier_blocks_unreviewed_identity_then_passes_alias(monkeypatch, inventory):
    event = copy.deepcopy(CAPTURE['event'])
    comp, = event['groupings'][0]['competitions']
    assert event['id'] == '1081-2026'
    assert comp['round']['id'] == '14'
    assert not comp['status']['type']['completed']
    assert any(a['athlete']['displayName'] == VARIANT for a in comp['competitors'])
    raw, proof = source_audit.capture_source('wta', [event], CAPTURE['observedAt'])
    data = _healthy_data()
    data['meta'].update(tournamentSourceAudit=proof, modelPlayerNames=inventory)
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
        assert hit.entity == 'espn:1081-2026#player:li zongyu'
        assert hit.evidence == {'player': VARIANT, 'candidates': [CANONICAL], 'role': 'qualifying'}
        assert health._gate_blocks(hit)
    data['meta']['modelPlayerNames'] = [CANONICAL]
    assert not findings()
    assert not findings()  # a repeated refresh still audits the pending qualifier


def test_official_identity_and_exact_historical_result_corroborate_alias(monkeypatch):
    espn, wta = CAPTURE['espnPlayer'], CAPTURE['wtaPlayer']
    assert espn['id'] == '13680'
    assert str(wta['id']) == '331259'
    assert (espn['firstName'], espn['lastName']) == (wta['firstName'], wta['lastName']) == ('Zongyu', 'Li')
    assert pd.to_datetime(espn['displayDOB'], dayfirst=True) == pd.Timestamp(wta['dateOfBirth'])
    comp, = CAPTURE['historyEvent']['groupings'][0]['competitions']
    loser, = [a for a in comp['competitors'] if a['winner'] is False]
    winner, = [a for a in comp['competitors'] if a['winner'] is True]
    assert loser['id'] == espn['id'] and loser['athlete']['displayName'] == VARIANT
    assert comp['notes'][0]['text'] == 'Xiaodi You (CHN) bt Zongyu Li (CHN) 6-3 7-5'
    official = CAPTURE['historyRows'][0]
    assert official['loser_id'] == str(wta['id'])
    assert official['winner_name'] == live._athlete_name(winner) == 'Xiaodi You'
    score = ' '.join(f"{int(a['value'])}-{int(b['value'])}"
                     for a, b in zip(winner['linescores'], loser['linescores']))
    assert score == official['score'] == '6-3 7-5'
    assert official['tourney_name'] == 'Ningbo' and official['tourney_date'] == '20230923'
    assert live._athlete_name(loser) == CANONICAL

    frame = pd.DataFrame(CAPTURE['historyRows'])
    variant = dict(official, loser_name=VARIANT)
    evidence = build_evidence(pd.concat([frame, pd.DataFrame([variant])], ignore_index=True))
    with monkeypatch.context() as unreviewed:
        unreviewed.delitem(config.PLAYER_ALIASES, KEY)
        questions = player_questions(evidence, 'wta')
    question, = [q for q in questions if q.subject == tuple(sorted((VARIANT, CANONICAL)))]
    assert 'different order' in question.context
    assert falsify(CAPTURE['identityReview'], {question.key: question}, evidence) is None


def test_shared_ingest_preserves_history_and_collapses_reordered_cached_result(monkeypatch, tmp_path):
    empty_reviewed_scope(monkeypatch, tmp_path / 'reviewed')
    for kind in ('historical', 'stats', 'fresh', 'live', 'lower'):
        folder = tmp_path / kind
        folder.mkdir()
        monkeypatch.setattr(results, kind + '_dir', lambda tour, p=folder: p)
    # Chronology reads its evidence through config, separately from results' imports.
    monkeypatch.setattr(config, 'stats_dir', lambda tour: tmp_path / 'stats')
    pd.DataFrame(CAPTURE['historyRows']).to_csv(tmp_path / 'lower/history_wta_lower.csv', index=False)
    # A cached second source may already carry the provider spelling; shared ingest
    # must repair it as well as newly parsed athletes, before deduplication and rating.
    variant = dict(CAPTURE['historyRows'][0], loser_name=VARIANT)
    pd.DataFrame([variant]).to_csv(tmp_path / 'lower/cached_wta_lower.csv', index=False)
    monkeypatch.setattr(results, '_read_historical', lambda tour: results._read_dir(tmp_path / 'historical'))
    monkeypatch.setattr(events, 'load_registry', lambda tour: {'events': {}})
    with monkeypatch.context() as broken:
        broken.delitem(config.PLAYER_ALIASES, KEY)
        before = results.merge_sources('wta', include_lower=True)
    after = results.merge_sources('wta', include_lower=True)
    assert len(before) == len(after) + 1
    assert len(after) == len(CAPTURE['historyRows']) == 11
    assert VARIANT in set(before.loser_name)
    assert VARIANT not in set(after.winner_name) | set(after.loser_name)
    assert (after.winner_name != after.loser_name).all()
    columns = ['winner_name', 'loser_name', 'date', 'round', 'score', 'draw_level']
    order = ['date', 'winner_name', 'loser_name']
    pd.testing.assert_frame_equal(
        before.loc[before.loser_name != VARIANT, columns].sort_values(order).reset_index(drop=True),
        after[columns].sort_values(order).reset_index(drop=True))
    pd.testing.assert_frame_equal(after, results.merge_sources('wta', include_lower=True))
