"""Issue #70: a same-score qualifying rematch cannot consume Caldas's R16."""

import json
from pathlib import Path

import pandas as pd
import pytest
from reviewed_fixtures import empty_reviewed_scope
from tennis_model.sim import tournaments
from test_event_population_view import _Predictor
from test_health import _healthy_data, _oc

from tennis_model import config
from tennis_model.data import health, results

INCIDENT = json.loads((Path(__file__).parent / 'fixtures/caldas_rematch_incident.json').read_text())


def _sources(monkeypatch, tmp_path):
    empty_reviewed_scope(monkeypatch, tmp_path / 'reviewed')
    for name in ('historical', 'stats', 'fresh', 'live', 'lower'):
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.setattr(results, name + '_dir', lambda tour, d=directory: d)
    monkeypatch.setattr(config, 'stats_dir', lambda tour: tmp_path / 'stats')
    monkeypatch.setattr(results, 'NORMALIZED_HISTORY_CACHE_DIR', tmp_path / 'history-cache')
    monkeypatch.setattr(results, 'wiki_categories_by_event_id', lambda tour: {'1024-2026': 'WTA 125'})
    monkeypatch.setattr(results, 'wiki_surface_lookup', lambda *args: {})
    pd.DataFrame(INCIDENT['liveResults']).to_csv(tmp_path / 'live/live.csv', index=False)
    pd.DataFrame([INCIDENT['priorQualifying']]).dropna(axis=1, how='all').to_csv(tmp_path / 'lower/2026_wta_lower.csv', index=False)
    pd.DataFrame([{
        'tourney_id': '2026-W999', 'tourney_name': 'Independent Event',
        'tourney_date': '20260601', 'winner_name': 'Unrelated Winner',
        'loser_name': 'Unrelated Loser', 'score': '6-0 6-0', 'surface': 'Hard',
        'tourney_level': 'A', 'best_of': 3,
    }]).to_csv(tmp_path / 'stats/2026.csv', index=False)


def test_caldas_rematch_preserves_qualifying_and_unrelated_identity(monkeypatch, tmp_path):
    _sources(monkeypatch, tmp_path)
    model = results.merge_sources('wta', include_lower=True)
    prior = model[model.winner_name.eq('Susan Bandecchi')]
    assert len(prior) == 1
    assert prior.iloc[0].date == pd.Timestamp('2026-08-26')
    assert prior.iloc[0].draw_level == 'qual'
    assert pd.isna(prior.iloc[0].espn_id)
    unrelated = model[model.winner_name.eq('Unrelated Winner')]
    assert len(unrelated) == 1 and unrelated.espn_id.isna().all()
    event = pd.DataFrame(model.attrs[results._POLICY_EVENT_ROWS_ATTR])
    assert len(event) == len(INCIDENT['liveResults'])
    assert event.espn_id.eq('1024-2026').all()
    feeder = event[event.winner_name.eq('Susan Bandecchi') & event.loser_name.eq('Viktoria Hruncakova')]
    assert len(feeder) == 1
    assert feeder.iloc[0]['round'] == 'R16' and feeder.iloc[0].draw_level == 'chall'
    assert feeder.iloc[0].date == pd.Timestamp('2026-09-16')


@pytest.mark.parametrize('broken', [True, False])
def test_caldas_source_to_bracket_gate_replay(monkeypatch, tmp_path, broken):
    _sources(monkeypatch, tmp_path)
    model = results.merge_sources('wta', include_lower=True)
    records = model.attrs[results._POLICY_EVENT_ROWS_ATTR]
    if broken:
        # Observed old merge: qualifying payload takes the current event/day,
        # then the projector excludes it from the main draw.
        for row in records:
            if row['winner_name'] == 'Susan Bandecchi' and row['loser_name'] == 'Viktoria Hruncakova':
                row.update(round=None, draw_level='qual')
    model = results.clean(model, 'wta')
    model['tour'] = 'wta'
    event = results.event_match_view(model, 'wta')
    event = event[event.espn_id.eq('1024-2026')]
    card = tournaments.project_tournament(
        _Predictor(set(INCIDENT['draw']['slots'])), 'Caldas da Rainha Ladies Open', event, 'wta',
        resolve=lambda name: name, tournament_draw=INCIDENT['draw'],
        espn_id='1024-2026', event_start='2026-09-14', event_end='2026-09-20',
        dmax=pd.Timestamp(INCIDENT['asOf']),
    )
    assert card is not None
    data = _healthy_data()
    data.update(brackets=[{'espnId': '1024-2026', 'status': 'live', 'rounds': card['bracket']}],
                upcoming=[INCIDENT['scheduled']])
    hits = [f for f in health.output_findings('wta', _oc(data=data), pd.Timestamp(INCIDENT['asOf']))
            if f.code == 'output.bracket.scheduled_match_missing']
    if broken:
        assert len(hits) == 1
        assert hits[0].evidence['players'] == ['lisa pigato', 'susan bandecchi']
    else:
        assert not hits
        qf = next(r for r in card['bracket'] if r['round'] == 'QF')
        assert any({m['a'], m['b']} == {'Lisa Pigato', 'Susan Bandecchi'} for m in qf['matches'])


def test_unknown_round_keys_cannot_donate_identity_to_unrelated_rows(monkeypatch, tmp_path):
    _sources(monkeypatch, tmp_path)
    live = pd.read_csv(tmp_path / 'live/live.csv')
    live.loc[0, 'round'] = None
    live.to_csv(tmp_path / 'live/live.csv', index=False)
    model = results.merge_sources('wta', include_lower=True)
    unrelated = model[model.winner_name.eq('Unrelated Winner')]
    assert len(unrelated) == 1 and unrelated.espn_id.isna().all()
