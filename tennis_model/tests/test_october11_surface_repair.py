"""Mallorca 2026 is clay: historical names and cached articles described the grass event."""
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.model import upcoming
from tennis_model.sim import tournaments
from test_health import _healthy_data, _oc
from test_tournament_status import _g, _Pred

from tennis_model.data import event_coverage, health, surface

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/mallorca_surface_20261011.json').read_text())
CODE = 'output.event.reviewed_surface_mismatch'


def test_reviewed_surface_is_exact_tour_and_edition_scoped(monkeypatch):
    monkeypatch.setattr(surface, 'wiki_surface', lambda *args: 'Grass')
    assert surface.resolve_surface_info('wta', 'Any sponsor', '2026-10-12',
                                       'Grass', '1020-2026') == ('Clay', 'reviewed')
    for tour, eid in [('atp', '1020-2026'), ('wta', '1020-2027'), ('wta', None)]:
        assert surface.resolve_surface(tour, 'Mallorca', '2026-10-12',
                                       'Grass', eid) == 'Grass'


def test_mallorca_surface_reaches_upcoming_live_shell_and_schedule(monkeypatch):
    draw = CAPTURE['draw']
    archive = pd.DataFrame([{'tourney_name': 'Mallorca', 'surface_b': 'Grass',
                             'best_of': 3, 'tourney_level': '250'}])
    names = {n for n in draw['slots'] if not n.startswith('Qualifier')}
    predictor = _Pred(dict.fromkeys(names, 1500))
    seen = []
    original_matrix = predictor.win_prob_matrix

    def matrix(players, **kwargs):
        seen.append(kwargs['surface'])
        return original_matrix(players, **kwargs)

    monkeypatch.setattr(predictor, 'win_prob_matrix', matrix)
    monkeypatch.setattr(surface, 'wiki_surface', lambda *args: 'Grass')
    # Replay the observed producer error, then pass its card through the new gate.
    with monkeypatch.context() as broken:
        broken.setattr(surface, 'EVENT_SURFACE_BY_ID', {})
        wrong = tournaments.project_upcoming(
            predictor, draw['name'], draw, 'wta', archive, set(), lambda n: n,
            espn_id='1020-2026', n_sims=32)
        assert wrong['surface'] == 'Grass'
        data = _healthy_data()
        data['tournaments'] = [wrong]
        assert any(f.code == CODE and f.severity == 'error' for f in health.output_findings(
            'wta', _oc(data=data), pd.Timestamp('2026-10-11')))
    seen.clear()
    card = tournaments.project_upcoming(
        predictor, draw['name'], draw, 'wta', archive, set(), lambda n: n,
        espn_id='1020-2026', n_sims=32)
    assert card['surface'] == 'Clay' and card['surfaceSource'] == 'reviewed'
    assert seen and set(seen) == {'Clay'}

    # Once play begins, even a Grass row inherited from stale archive metadata is corrected.
    live = _g().assign(surface_b='Grass')
    card = tournaments.project_tournament(
        _Pred({f'P{i}': 1500 for i in range(16)}), draw['name'], live, 'wta',
        espn_id='1020-2026', n_sims=32)
    assert card['surface'] == 'Clay' and card['surfaceSource'] == 'reviewed'
    shell = event_coverage._coverage_shell(
        {'key': 'espn:1020-2026', 'name': draw['name'], 'espnId': '1020-2026', 'surface': 'Grass',
         'surfaceSource': 'archive', 'start': '2026-10-12', 'end': '2026-10-18'},
        '2026-10-12', 'wta')
    assert shell['surface'] == 'Clay'

    rows = upcoming.enrich_upcoming(predictor, archive, pd.DataFrame(CAPTURE['espn']),
                                   'wta', bracket_index={})
    assert len(rows) == 13 and {r['surface'] for r in rows} == {'Clay'}


@pytest.mark.parametrize('artifact', ['tournaments', 'brackets', 'upcoming'])
def test_gate_blocks_reviewed_surface_mismatch_in_every_public_view(artifact):
    for value, blocked in [('Grass', True), ('Clay', False)]:
        data = _healthy_data()
        data[artifact][0]['espnId'] = '1020-2026'
        data[artifact][0]['surface'] = value
        findings = health.output_findings('wta', _oc(data=data), pd.Timestamp('2026-10-11'))
        hits = [f for f in findings if f.code == CODE]
        assert bool(hits) == blocked
        if hits:
            assert hits[0].severity == 'error'
            assert hits[0].evidence['expected'] == CAPTURE['officialSurface']
        # Other tours and editions must never inherit the Mallorca correction.
        assert not any(f.code == CODE for f in health.output_findings(
            'atp', _oc(data=data), pd.Timestamp('2026-10-11')))
        data[artifact][0]['espnId'] = '1020-2027'
        assert not any(f.code == CODE for f in health.output_findings(
            'wta', _oc(data=data), pd.Timestamp('2026-10-11')))
