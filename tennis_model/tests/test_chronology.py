"""Known source defects and conservative evidence rules, without source downloads."""

import json

import pandas as pd
import pytest
from tennis_model.data.chronology import (
    annotate_sources,
    carry_timing_evidence,
    require_chronology,
    resolve_dates,
)
from tennis_model.data.results import chronological, clean
from tennis_model.model.features import run_context

from tennis_model import config


def rows():
    return pd.DataFrame({
        'date':pd.to_datetime(['2024-11-03','2024-11-04']),
        'tourney_id':['2024-341']*2, 'tourney_name':['Metz']*2,
        'winner_name':['Benjamin Bonzi','Alex Michelsen'],
        'loser_name':['Alex Michelsen','Yunchaokete Bu'],
        'score':['4-6 6-0 7-5','6-4 6-3'], 'round':['SF','QF'],
        'round_order':[6,5], 'match_num':[1,2], 'source_kind':['historical']*2,
        'espn_id':[None]*2, 'completed':[True]*2, 'w_games':[17,12],
        'l_games':[11,7], 'surface_b':['Hard']*2,
    })


def test_exact_event_start_repair_preserves_raw_values_and_corrects_pre_match_state():
    raw=rows()
    corrected=chronological(resolve_dates(annotate_sources(raw,'atp'),'atp'))
    assert list(corrected['round']) == ['QF','SF']
    assert corrected.recorded_date.iloc[0] == pd.Timestamp('2024-11-04')
    assert set(corrected.date_basis) == {'event_start'}
    assert set(corrected.stats_available_at) == {pd.Timestamp('2024-11-09')}
    assert corrected.played_date.isna().all()
    require_chronology(corrected)
    bad=corrected.copy();bad['date']=bad.recorded_date
    with pytest.raises(ValueError,match='inversions'):
        require_chronology(bad)
    _, signals=run_context(corrected)
    assert signals.w_wr10.iloc[0] == .5  # QF does not ingest the later semifinal loss
    assert signals.l_wr10.iloc[1] == 1.  # semifinal sees the quarterfinal win
    future=pd.concat([raw,raw.iloc[:1].assign(tourney_id='2025-341',date=pd.Timestamp('2025-11-03'))])
    full=chronological(resolve_dates(annotate_sources(future,'atp'),'atp'))
    pd.testing.assert_frame_equal(corrected,full.iloc[:2])


def test_exact_wrong_event_id_requires_pair_date_score():
    frame=rows().iloc[:1].assign(tourney_id='2026-416',date=pd.Timestamp('2026-04-13'),
        winner_name='Ben Shelton',loser_name='Emilio Nava',score='7-6(4) 3-6 6-3')
    fixed=resolve_dates(annotate_sources(frame,'atp'),'atp')
    assert fixed.tourney_id.iloc[0]=='2026-308'
    assert fixed.recorded_event_id.iloc[0]=='2026-416'
    wrong=frame.assign(loser_name='Another Player')
    assert resolve_dates(annotate_sources(wrong,'atp'),'atp').tourney_id.iloc[0]=='2026-416'


@pytest.mark.parametrize('stamp', ['2025-01-01', '2024-12-31'])
def test_unique_wta_result_evidence_and_partial_edition_fallback(tmp_path,monkeypatch,stamp):
    monkeypatch.setattr(config,'stats_dir',lambda tour:tmp_path)
    cache=tmp_path/'_httpcache/2025';cache.mkdir(parents=True)
    payload={'tournament':{'year':2025,'tournamentGroup':{'id':123},
        'startDate':'2025-01-01','endDate':'2025-01-07'},'matches':[
        {'MatchID':'LS001','MatchState':'F','Winner':'2','DrawMatchType':'S',
         'MatchTimeStamp':'2025-01-03T12:00:00Z',
         'PlayerNameFirstA':'Alex','PlayerNameLastA':'Michelsen',
         'PlayerNameFirstB':'Yunchaokete','PlayerNameLastB':'Bu',
         'ScoreSet1A':'6','ScoreSet1B':'4','ScoreSet2A':'6','ScoreSet2B':'3'}]}
    (cache/'sample.json').write_text(json.dumps(payload))
    frame=rows().assign(tourney_id='2025-W123',date=pd.Timestamp(stamp),
                        source_match_id=['LS002','LS001'],source_kind='stats')
    annotated=annotate_sources(frame,'wta')
    assert annotated.played_date.notna().sum()==1
    resolved=resolve_dates(annotated,'wta')
    assert set(resolved.date_basis)=={'event_start'}
    assert resolved.played_date.notna().sum()==1
    assert set(resolved.date) == {pd.Timestamp(stamp)}
    assert list(resolved.stats_availability_basis)==['event_end','played_date']
    assert resolved.stats_available_at.iloc[0]==pd.Timestamp('2025-01-07')
    require_chronology(chronological(resolved))
    bad=frame.copy();bad.loc[1,'score']='6-1 6-2'
    assert annotate_sources(bad,'wta').played_date.isna().all()


def test_ambiguous_donor_days_are_excluded_and_no_evidence_is_unknown():
    f=annotate_sources(rows(),'atp')
    keys=pd.Series(['same','same'])
    f['played_date']=pd.to_datetime(['2024-11-06','2024-11-07'])
    f['date_evidence']='verified-source'
    carried=carry_timing_evidence(f,keys)
    assert carried.played_date.isna().all()
    unknown=resolve_dates(annotate_sources(rows().assign(tourney_id='2024-unknown'),'atp'),'atp')
    assert set(unknown.stats_availability_basis)=={'unknown'}
    assert unknown.stats_available_at.isna().all()


def test_schema_columns_survive_cleaning():
    f=rows().assign(tourney_date='20241103',surface='Hard',tourney_level='A',indoor='I',
                   w_svpt=60,l_svpt=60,best_of=3)
    f=resolve_dates(annotate_sources(f,'atp'),'atp')
    assert list(clean(f).recorded_date)==list(f.recorded_date)


@pytest.mark.parametrize('full', [True, False])
def test_unresolved_chronology_stops_every_export_before_writes(monkeypatch, full):
    from tennis_model.model import export

    frame = resolve_dates(annotate_sources(rows(),'atp'),'atp')
    frame['date'] = frame.recorded_date
    monkeypatch.setattr(export, '_clear_upcoming_outputs', lambda *a: pytest.fail('write before guard'))
    with pytest.raises(ValueError, match='inversions'):
        export.export_all('atp', frame, None, None, None, None, full=full)
