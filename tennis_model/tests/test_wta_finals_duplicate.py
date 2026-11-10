"""Replay the November 10 WTA Finals fixture blocker (#196 and #197)."""

import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from reviewed_fixtures import empty_reviewed_scope
from tennis_model.model import export
from test_health import _healthy_data, _oc

from tennis_model import config
from tennis_model.data import events, health, live, results, wta_results, wta_stats

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/wta_finals_duplicate_20261110.json').read_text())
EID = '382-2026'
WTA_KEY = ('2026-W808', 'LS010')
NOW = pd.Timestamp('2026-11-10T18:12:58Z')


@pytest.fixture
def replay(monkeypatch, tmp_path):
    empty_reviewed_scope(monkeypatch, tmp_path / 'reviewed')
    for kind in ('historical', 'stats', 'fresh', 'live', 'lower'):
        folder = tmp_path / kind
        folder.mkdir()
        monkeypatch.setattr(results, kind + '_dir', lambda tour, p=folder: p)
    monkeypatch.setattr(config, 'stats_dir', lambda tour: tmp_path / 'stats')
    monkeypatch.setattr(results, '_read_historical', lambda tour: results._read_dir(tmp_path / 'historical'))
    monkeypatch.setattr(results, 'wiki_categories_by_event_id', lambda tour: {EID: 'Tour Finals'})
    monkeypatch.setattr(events, 'load_registry', lambda tour: {'events': {
        EID: {'start': '2026-11-08', 'end': '2026-11-15'}}})
    live.parse_events([CAPTURE['espnEvent']], 'womens').to_csv(tmp_path / 'live/live.csv', index=False)
    stats = wta_stats._stats_row(CAPTURE['wtaEvent'], CAPTURE['wtaMatch'], CAPTURE['wtaStats'])
    # Reconstruct the retained row that was written before the provider round repair.
    stats['round'] = 'QF'
    assert stats['score'] == '6-2 6-4'
    pd.DataFrame([stats]).to_csv(tmp_path / 'stats/2026.csv', index=False)

    def run(*, shadow=None, include_lower=False, scoreboard=True):
        rows = pd.DataFrame(CAPTURE['mirrorRows'])
        if shadow:
            for column, value in shadow.items():
                rows.loc[1, column] = value
        rows.to_csv(tmp_path / 'fresh/2026.csv', index=False)
        if not scoreboard:
            (tmp_path / 'live/live.csv').unlink()
        with monkeypatch.context() as scope:
            if scoreboard:
                # Exercise the independent reconciliation path for future mirror copies
                # whose provider match IDs have never been reviewed.
                repairs = {k: v for k, v in config.WTA_MATCH_ROLE_REPAIRS.items() if k != WTA_KEY}
                scope.setattr(results, 'WTA_MATCH_ROLE_REPAIRS', repairs)
            merged = results.clean(results.merge_sources('wta', include_lower=include_lower), 'wta')
        data = _healthy_data()
        data['fixtures'] = export._finite(export.build_fixtures(
            merged, SimpleNamespace(win_prob=lambda *a, **k: .6), tour='wta'))
        duplicate_findings = [f for f in health.output_findings('wta', _oc(data=data), NOW)
                              if f.code == 'output.fixture.duplicate_completed_match'
                              and health._gate_blocks(f)]
        return merged, data['fixtures'], duplicate_findings

    return run


@pytest.mark.parametrize('include_lower', [False, True])
def test_finals_duplicate_collapses_to_the_witnessed_group_result(replay, include_lower):
    merged, fixtures, blockers = replay(include_lower=include_lower)
    assert not blockers, [(f.entity, f.message) for f in blockers]
    row, = merged.itertuples(index=False)
    assert (row.source_match_id, row.has_stats, row.w_svpt) == ('LS010', True, 65)
    fixture, = fixtures
    assert (fixture['espnId'], fixture['round'], fixture['date'], fixture['score']) == (
        EID, 'RR', '2026-11-08', '6-2 6-4')


def test_mirror_rows_with_different_payloads_still_block(replay):
    _, _, blockers = replay(shadow={'winner_rank': '9'})
    assert {f.entity for f in blockers} == {
        f'espn:{EID}#players:linda noskova:marta kostyuk',
        'event-date:2026-11-08#players:linda noskova:marta kostyuk',
    }


def test_mirror_rows_with_distinct_known_rounds_keep_the_later_round(replay):
    # Event-start dates can match even when the players meet again in the final.
    _, fixtures, _ = replay(shadow={'round': 'F'})
    assert {'RR', 'F'} <= {f['round'] for f in fixtures}


def test_reviewed_group_round_survives_after_scoreboard_rollover(replay):
    merged, fixtures, blockers = replay(scoreboard=False)
    assert not blockers
    row, = merged.itertuples(index=False)
    assert (row.source_match_id, row.has_stats, row.round) == ('LS010', True, 'RR')
    fixture, = fixtures
    assert (fixture['round'], fixture['score']) == ('RR', '6-2 6-4')


def test_wta_result_acquisition_preserves_the_reviewed_round():
    event, match = CAPTURE['wtaEvent'], CAPTURE['wtaMatch']
    assert wta_results.normalize_result(event, match)['round'] == 'RR'
    assert wta_stats._stats_row(event, match, CAPTURE['wtaStats'])['round'] == 'RR'
    assert wta_stats._match_round(event, {**match, 'MatchID': 'LS002', 'RoundID': 'S'}, 'main') == 'SF'
    assert wta_stats._match_round({**event, 'year': 2025}, match, 'main') == 'QF'
