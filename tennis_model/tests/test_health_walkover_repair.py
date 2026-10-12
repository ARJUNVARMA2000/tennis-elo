"""Captured Shanghai walkover: source status survives CSV and bracket publication."""
import copy
import io
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.config import PLAYER_ALIASES
from tennis_model.data.names import name_key
from tennis_model.data.scores import parse_score
from tennis_model.sim.bracket import bracket_rounds, price_bracket
from test_health import _healthy_data, _oc

from tennis_model.data import health, live

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/shanghai_walkover_20261012.json').read_text())
CODES = {'output.bracket.score_invalid', 'output.bracket.walkover_invalid'}


def _findings(bracket):
    data = _healthy_data()
    data['brackets'] = [bracket]
    return health.output_findings('atp', _oc(data=data), pd.Timestamp('2026-10-12'))


def _match(bracket):
    return next(m for r in bracket['rounds'] for m in r['matches']
                if {m['a'], m['b']} == {'Alex de Minaur', 'Alex Molcan'})


def test_captured_walkover_source_csv_producer_and_gate():
    broken = copy.deepcopy(CAPTURE['publicBracket'])
    assert _match(broken)['score'] == 'nan'
    assert _match(broken)['p'] is not None
    hits = [f for f in _findings(broken) if f.code in CODES]
    assert len(hits) == 1 and hits[0].code == 'output.bracket.score_invalid'
    assert health._gate_blocks(hits[0])

    frame = live.parse_events([CAPTURE['event']], 'mens')
    # Exercise the actual empty-string -> CSV -> float NaN boundary behind the bug.
    frame = pd.read_csv(io.StringIO(frame.to_csv(index=False)))
    row = frame[(frame.winner_name == 'Alex de Minaur') & (frame.loser_name == 'Alex Molcan')].iloc[0]
    assert row['round'] == 'R64' and row['score'] == 'W/O'
    assert parse_score(row['score']).walkover
    assert parse_score(float('nan')).walkover  # no change to existing model exclusion
    retired = frame[(frame.winner_name == 'Adrian Mannarino')
                    & (frame.loser_name == 'Nikoloz Basilashvili')].iloc[0]
    assert retired['score'] == '6-3 2-2 RET'
    assert not parse_score(retired['score']).completed
    for col in ('winner_name', 'loser_name'):
        frame[col] = frame[col].map(lambda n: PLAYER_ALIASES.get(name_key(n), n))
    slots = [m[s] for m in broken['rounds'][0]['matches'] for s in ('a', 'b')]
    rounds = bracket_rounds(slots, frame.to_dict('records'))
    price_bracket(rounds, lambda a, b: .7, lambda a, b: .8)
    fixed = {**broken, 'rounds': rounds}
    m = _match(fixed)
    assert m[m['winner']] == 'Alex de Minaur'
    assert m['score'] == 'W/O'
    assert m['p'] is m['probSource'] is m['upset'] is None
    retirement = next(m for r in rounds for m in r['matches']
                      if {m['a'], m['b']} == {'Adrian Mannarino', 'Nikoloz Basilashvili'})
    assert retirement['score'] == '6-3 2-2 RET'
    assert retirement[retirement['winner']] == 'Adrian Mannarino'
    assert not CODES & {f.code for f in _findings(fixed)}
    assert sum(m['winner'] is not None for r in rounds for m in r['matches']) == 112


@pytest.mark.parametrize('score', [float('nan'), 0, '', 'nan', ' NaN ', 'None', 'null', '<NA>'])
def test_missing_score_cannot_leak_or_imply_walkover(score):
    broken = copy.deepcopy(CAPTURE['publicBracket'])
    _match(broken)['score'] = score
    hits = [f for f in _findings(broken) if f.code == 'output.bracket.score_invalid']
    assert len(hits) == 1 and health._gate_blocks(hits[0])
    rounds = bracket_rounds(['Alex de Minaur', 'Alex Molcan'], [
        {'winner_name': 'Alex de Minaur', 'loser_name': 'Alex Molcan', 'score': score}])
    assert rounds[0]['matches'][0]['score'] is None


@pytest.mark.parametrize('change', [{'p': .8, 'probSource': 'logged'}, {'winner': None},
                                   {'upset': False}, {'probSource': 'model'}])
def test_gate_rejects_priced_or_undecided_walkover(change):
    b = copy.deepcopy(CAPTURE['publicBracket'])
    _match(b).update(score='W/O', p=None, probSource=None, upset=None)
    assert not CODES & {f.code for f in _findings(b)}
    _match(b).update(change)
    hits = [f for f in _findings(b) if f.code == 'output.bracket.walkover_invalid']
    assert len(hits) == 1 and health._gate_blocks(hits[0])


def test_only_explicit_walkover_status_supplies_walkover_score():
    event = copy.deepcopy(CAPTURE['event'])
    comp = next(c for c in event['groupings'][0]['competitions']
                if c['status']['type'].get('name') == 'STATUS_WALKOVER')
    comp['status']['type']['name'] = 'STATUS_FINAL'
    frame = live.parse_events([event], 'mens')
    row = frame[(frame.winner_name == 'Alex de Minaur') & (frame.loser_name == 'Alex Molcan')].iloc[0]
    assert row['score'] == ''  # absence alone is not factual walkover evidence
