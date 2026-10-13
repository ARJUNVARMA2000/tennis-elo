"""A preferred mirror score cannot erase independently witnessed retirements."""
import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from tennis_model.data.health_checks.common import _FindingCollector

from tennis_model.data import events, live, results, source_audit

CAPTURE = json.loads((Path(__file__).parent / 'fixtures/beijing_retirement_merge_20261012.json').read_text())
NOW = '2026-10-12T21:00:00Z'
REGISTRY = {'events': {'959-2026': {'start': '2026-09-27', 'end': '2026-10-12'}}}


def frames():
    fresh = pd.DataFrame(CAPTURE['freshRows']).assign(source_kind='fresh', espn_id=None)
    parsed = live.parse_events([CAPTURE['event']], 'womens')
    parsed = parsed[parsed.score.str.contains('RET')].assign(source_kind='live')
    frame = pd.concat([fresh, parsed], ignore_index=True)
    frame['date'] = pd.to_datetime(frame.tourney_date.astype(str).str.replace('/', '-'))
    keys = frame.winner_name + '|' + frame.loser_name + '|' + frame['round'] + '|' + frame.score.map(results._score_key)
    return frame, keys


def audit(bracket, now=NOW):
    raw, proof = source_audit.capture_source('wta', [CAPTURE['event']], now)
    names = [m[s] for m in bracket['rounds'][0]['matches'] for s in ('a', 'b') if m[s]]
    data = {'meta': {'modelPlayerNames': names, 'tournamentSourceAudit': proof},
            'tournaments': [bracket], 'brackets': [bracket], 'upcoming': []}
    out = _FindingCollector('output', 'wta')
    source_audit.check_source(out, 'wta', {'state': 'valid', 'witness': json.loads(raw), 'proof': proof},
                              data, {}, now)
    return out.findings


def test_captured_mirror_retirements_survive_real_merge_and_clear_unchanged_gate(tmp_path, monkeypatch):
    frame, _ = frames()
    for folder in ('historical', 'stats', 'fresh', 'live', 'lower'):
        path = tmp_path / folder
        path.mkdir()
        monkeypatch.setattr(results, folder + '_dir', lambda tour, p=path: p)
    monkeypatch.setattr(results, '_read_historical', lambda tour: results._read_dir(tmp_path / 'historical'))
    monkeypatch.setattr(events, 'load_registry', lambda tour: REGISTRY)
    monkeypatch.setattr(results, 'wiki_categories_by_event_id', lambda tour: {'959-2026': 'WTA 1000'})
    for kind in ('fresh', 'live'):
        frame[frame.source_kind.eq(kind)].drop(columns=['source_kind', 'date']).to_csv(tmp_path / kind / '2026.csv', index=False)
    merged = results.merge_sources('wta')
    rows = merged[merged.date.dt.year.eq(2026)]
    assert len(rows) == 3
    assert set(rows.source_kind) == {'fresh'}
    assert rows.score.str.endswith(' RET').all()
    assert '6-7(4) 6-4 3-0 RET' in set(rows.score)
    bracket = copy.deepcopy(CAPTURE['publicBracket'])
    broken = audit(bracket)
    assert len(broken) == 3 and all(f.code.endswith('outcome_mismatch') for f in broken)
    for row in rows.itertuples():
        matches = [m for r in bracket['rounds'] for m in r['matches']
                   if {m['a'], m['b']} == {row.winner_name, row.loser_name}]
        assert len(matches) == 1
        matches[0]['score'] = row.score
    assert not audit(bracket)


def test_published_completed_bracket_does_not_age_out_at_midnight():
    findings = audit(CAPTURE['publicBracket'], now='2026-10-13T01:00:00Z')
    assert len(findings) == 3
    assert all(f.code.endswith('outcome_mismatch') for f in findings)


@pytest.mark.parametrize('fault', ['other_date', 'other_id', 'duplicate_live', 'no_bounds', 'conflicting_outcome'])
def test_outcome_donation_refuses_unproven_or_ambiguous_matches(fault):
    frame, keys = frames()
    registry = copy.deepcopy(REGISTRY)
    original = frame.loc[0, 'score']
    if fault == 'other_date':
        frame.loc[0, 'date'] = pd.Timestamp('2026-08-01')
    elif fault == 'other_id':
        frame.loc[0, 'espn_id'] = '381-2026'
    elif fault == 'duplicate_live':
        frame = pd.concat([frame, frame.iloc[[3]]], ignore_index=True)
        keys = pd.concat([keys, keys.iloc[[3]]], ignore_index=True)
    elif fault == 'no_bounds':
        registry = {}
    else:
        original += ' DEF'
        frame.loc[0, 'score'] = original
    assert results._carry_live_outcomes(frame, keys, registry).loc[0, 'score'] == original


def test_explicit_walkover_survives_an_empty_preferred_score():
    frame, _ = frames()
    frame = frame.loc[[0, 3]].copy()
    frame.loc[0, 'score'] = None
    frame.loc[3, 'score'] = 'W/O'
    keys = frame.winner_name + '|' + frame.loser_name + '|' + frame['round'] + '|' + frame.score.map(results._score_key)
    assert results._carry_live_outcomes(frame, keys, REGISTRY).loc[0, 'score'] == 'W/O'
