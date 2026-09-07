"""Reviewed source completeness must survive omission, dedup and optional box scores."""

import copy
import json

import pandas as pd
import pytest

from tennis_model import config
from tennis_model.data import chronology, results, wta_results, wta_stats
from tennis_model.data import result_ledger as ledger


def example(outcome='completed'):
    doc = ledger.load_ledger('wta')
    return copy.deepcopy(next(r for r in doc['records'] if r['outcome'] == outcome))


def population():
    frame = ledger.result_frame('wta')
    frame['date'] = pd.to_datetime(frame.tourney_date, format='%Y%m%d')
    return frame


def test_all_reviewed_inputs_normalize_without_stats_and_keep_roles_and_outcomes():
    doc = ledger.load_ledger('wta')
    frame = population()
    assert len(doc['records']) == len(frame) == 528
    assert frame.result_outcome.value_counts().to_dict() == {'completed':521, 'retirement':6, 'walkover':1}
    assert frame[['w_svpt', 'l_svpt']].isna().all().all()
    assert set(frame.tourney_level) == {'WTA1000','Grand Slam'}
    assert frame.draw_level.eq('main').all()
    assert frame.winner_age.isna().all() and frame.winner_ioc.isna().all()
    assert ledger.validate_receipt(ledger.coverage_receipt(frame, 'wta'), 'wta', len(frame)) == []


@pytest.mark.parametrize('edit', ['row', 'event', 'self', 'role', 'outcome', 'duplicate'])
def test_expected_receipt_detects_omission_and_corruption_with_plausible_totals(edit):
    frame = population()
    if edit == 'row':
        frame.loc[0, 'winner_name'] = 'Unrelated Player'  # ordinary total remains unchanged
    elif edit == 'event':
        frame.loc[frame.tourney_id.eq(frame.tourney_id.iloc[0]), 'winner_name'] = 'Unrelated Player'
    elif edit == 'self':
        frame.loc[0, 'loser_name'] = frame.loc[0, 'winner_name']
    elif edit == 'role':
        frame.loc[0, 'draw_level'] = 'qual'
    elif edit == 'outcome':
        idx = frame.index[frame.result_outcome.eq('retirement')][0]
        frame.loc[idx, 'score'] = frame.loc[idx, 'score'].replace(' RET','')
    else:
        frame = pd.concat([frame, frame.iloc[:1]], ignore_index=True)
    receipt = ledger.coverage_receipt(frame, 'wta')
    assert 'expected_results_missing' in ledger.validate_receipt(receipt, 'wta', len(frame))
    if edit == 'self':
        assert 'invalid_self_pair' in ledger.validate_receipt(receipt, 'wta', len(frame))


@pytest.mark.parametrize('corruption',[None,'played-date','two-days','wrong-edition','no-evidence'])
def test_documented_archive_start_anchor_is_not_a_missing_result(corruption):
    frame=population()
    start=pd.Timestamp(frame.loc[0,'event_start'])
    stamp=start-pd.Timedelta(days=1)
    frame.loc[0,'date']=stamp
    frame.loc[0,'recorded_date']=stamp
    frame.loc[0,'date_basis']='event_start'
    frame.loc[0,'date_evidence']='verified-exact-result'
    if corruption=='played-date':
        frame.loc[0,'date_basis']='played_date'
    if corruption=='two-days':
        frame.loc[0,'date']=stamp-pd.Timedelta(days=1)
    if corruption=='wrong-edition':
        frame.loc[0,'espn_id']='870-2024'
    if corruption=='no-evidence':
        frame.loc[0,'date_evidence']=None
    receipt=ledger.coverage_receipt(frame,'wta')
    assert (receipt['verifiedResults']==528) is (corruption is None)


def test_reviewed_xinyu_alias_preserves_distinct_xiyu_player():
    assert wta_results.canonical_name('Xin Yu Wang')=='Xinyu Wang'
    assert wta_results.canonical_name('Xiyu Wang')=='Xiyu Wang'


@pytest.mark.parametrize('field,value', [('EventYear',2025),('EventID','999'),('EventID',None)])
def test_record_identity_cannot_be_overridden_by_cache_folder_or_header(field,value):
    r = example()
    r['wta']['match'][field] = value
    with pytest.raises(ValueError, match='edition'):
        wta_results.normalize_result(r['wta']['event'], r['wta']['match'])


def test_zero_padded_provider_id_and_verified_sherif_alias():
    r = next(r for r in ledger.load_ledger('wta')['records']
             if 'Sherif' in r['row']['winner_name'])
    m = {**r['wta']['match'], 'EventID':'000'+str(r['wta']['event']['id'])}
    row = wta_results.normalize_result(r['wta']['event'],m)
    assert row['winner_name'] == 'Mayar Sherif'
    assert row['tourney_id'] == r['row']['tourney_id']


@pytest.mark.parametrize('field,value', [('DrawLevelType','Q'),('DrawMatchType','D'),('Winner','0')])
def test_unknown_outcome_and_wrong_population_need_review(field,value):
    r = example()
    r['wta']['match'][field] = value
    with pytest.raises(ValueError):
        wta_results.normalize_result(r['wta']['event'],r['wta']['match'])
    r = example('retirement')
    with pytest.raises(ValueError, match='outcome'):
        wta_results.normalize_result(r['wta']['event'],r['wta']['match'])


def test_numeric_zero_games_are_not_missing_stats_or_missing_score():
    r = example()
    m = {**r['wta']['match'], 'ScoreSet1A':6, 'ScoreSet1B':0,
         'ScoreSet2A':6, 'ScoreSet2B':0, 'ScoreSet3A':'', 'ScoreSet3B':''}
    row = wta_results.normalize_result(r['wta']['event'],m)
    assert wta_results.games(row['score']) == '6-0,6-0'


def test_result_capture_precedes_known_stat_skip_and_missing_stats_still_attempted(monkeypatch):
    r = example();ev,m = r['wta']['event'],r['wta']['match']
    monkeypatch.setattr(wta_stats,'_paged',lambda *args:[m])
    calls=[]
    monkeypatch.setattr(wta_stats,'_get',lambda *a,**kw:calls.append(a) or [])
    captured=[]
    assert wta_stats.scrape_tournament(ev, result_records=captured) == []
    assert len(captured)==len(calls)==1
    assert captured[0]['decision']=='eligible'
    known={f"id:{r['row']['tourney_id']}:{m['MatchID']}"}
    assert wta_stats.scrape_tournament(ev, known_keys=known, result_records=captured)==[]
    assert len(captured)==2 and len(calls)==1


@pytest.mark.parametrize('stats_first', [True,False])
def test_reviewed_result_and_stats_are_one_match_in_either_acquisition_order(monkeypatch,tmp_path,stats_first):
    r = example('retirement')
    reviewed=pd.DataFrame([{**r['row'], 'reviewed_result_key':r['key']}])
    reviewed=reviewed.reindex(columns=sorted(set(results.CANON)|set(reviewed.columns)))
    stats=reviewed.assign(w_svpt=60,l_svpt=65,score=r['row']['score'].replace(' RET',''))
    empty=pd.DataFrame(columns=results.CANON)
    monkeypatch.setattr(config,'stats_dir',lambda tour:tmp_path)
    monkeypatch.setattr(results,'_read_historical',lambda tour:empty.copy())
    monkeypatch.setattr(results,'_read_lower',lambda tour:empty.copy())
    seen={'stats':stats_first,'results':not stats_first}
    monkeypatch.setattr(results,'_read_dir',lambda path:stats.copy() if seen['stats'] and path==results.stats_dir('wta') else empty.copy())
    monkeypatch.setattr(ledger,'result_frame',lambda tour:reviewed.copy() if seen['results'] else empty.copy())
    first=results.merge_sources('wta')
    assert len(first)==1
    seen.update(stats=True,results=True)
    final=results.merge_sources('wta')
    assert len(final)==1 and final.w_svpt.iloc[0]==60
    assert final.score.iloc[0].endswith(' RET')


def test_same_score_same_round_rematches_keep_distinct_reviewed_editions(monkeypatch,tmp_path):
    record=next(r for r in ledger.load_ledger('wta')['records']
                if r['row']['winner_name']=='Iga Swiatek' and r['row']['loser_name']=='Sorana Cirstea')
    reviewed=pd.DataFrame([{**record['row'], 'reviewed_result_key':record['key']}])
    reviewed=reviewed.reindex(columns=sorted(set(results.CANON)|set(reviewed.columns)))
    madrid={**record['row'], 'tourney_id':'2024-1038', 'tourney_date':'20240422',
            'played_date':None, 'event_start':None, 'event_end':None, 'date_evidence':None,
            'espn_id':None, 'w_svpt':60, 'l_svpt':65, 'source_match_id':None}
    doha={**madrid, 'tourney_id':'2024-1003', 'tourney_date':'20240212'}
    hist=pd.DataFrame([doha,madrid]).reindex(columns=reviewed.columns)
    empty=pd.DataFrame(columns=results.CANON)
    monkeypatch.setattr(config,'stats_dir',lambda tour:tmp_path)
    monkeypatch.setattr(results,'_read_historical',lambda tour:hist.copy())
    monkeypatch.setattr(results,'_read_lower',lambda tour:empty.copy())
    monkeypatch.setattr(results,'_read_dir',lambda path:empty.copy())
    monkeypatch.setattr(ledger,'result_frame',lambda tour:reviewed.copy())
    merged=results.merge_sources('wta').sort_values('date')
    assert len(merged)==2
    assert list(merged.tourney_id)==['2024-1003','2024-1038']
    assert merged.date.iloc[0]==pd.Timestamp('2024-02-12')
    assert pd.isna(merged.espn_id.iloc[0])
    assert merged.espn_id.iloc[1]=='413-2024'


def test_exact_quarantine_does_not_mask_a_new_self_pair():
    q=ledger.load_ledger('wta')['quarantines'][0]['match']
    frame=pd.DataFrame([q]);frame['date']=pd.to_datetime(frame.date)
    assert ledger.apply_quarantines(frame,'wta').empty
    frame['match_num']=18
    with pytest.raises(ValueError,match='unreviewed invalid self-pair'):
        ledger.apply_quarantines(frame,'wta')


def test_same_valid_provider_id_is_invalid_even_when_display_names_differ():
    frame = population().iloc[:1].copy()
    frame['loser_id'] = frame.winner_id
    assert ledger.self_pair_mask(frame).all()
    with pytest.raises(ValueError, match='unreviewed invalid self-pair'):
        ledger.apply_quarantines(frame,'wta')


@pytest.mark.parametrize('mode',['absent','changed'])
def test_ledger_cannot_be_deleted_or_replaced_with_empty_scope(monkeypatch,tmp_path,mode):
    monkeypatch.setattr(ledger,'LEDGER_DIR',tmp_path)
    if mode=='changed':
        (tmp_path/'wta.json').write_text(json.dumps({'records':[]}))
    with pytest.raises((OSError,ValueError)):
        ledger.load_ledger('wta')


@pytest.mark.parametrize('full',[True,False])
def test_both_export_paths_stop_before_any_writes_when_one_result_is_missing(monkeypatch,full):
    from tennis_model.model import export
    frame=population().iloc[1:].copy()
    monkeypatch.setattr(export,'_clear_upcoming_outputs',lambda *a:pytest.fail('write before guard'))
    with pytest.raises(ValueError,match='Result integrity failed'):
        export.export_all('wta',frame,None,None,None,None,full=full)


def test_typed_gate_blocks_absent_stale_and_corrupt_receipts():
    from tennis_model.data.health import output_findings
    frame=population();receipt=ledger.coverage_receipt(frame,'wta')
    for change,reason in [(None,'contract_invalid'),({'ledgerSHA256':'0'*64},'contract_invalid'),
                          ({'selfPairs':1},'invalid_self_pair'),({'verifiedResults':527},'expected_results_missing')]:
        current=None if change is None else {**receipt,**change}
        meta={'matches':len(frame),'matchPopulationVersion':7,'resultIntegrity':current}
        findings=output_findings('wta',{'data':{'meta':meta}},pd.Timestamp('2026-09-06'))
        assert f'output.results.{reason}' in {f.code for f in findings}


@pytest.mark.parametrize('flag',['estimatedStartTime','isEstimatedStartTime'])
def test_estimated_timestamp_retracts_old_claim_and_retains_bounds(monkeypatch,tmp_path,flag):
    r=example();ev=r['wta']['event'];m={**r['wta']['match'],flag:True}
    cache=tmp_path/'_httpcache/1999';cache.mkdir(parents=True)  # folder year is irrelevant
    value={'tournament':{'tournamentGroup':{'id':ev['id']},'year':ev['year'],
                        'startDate':ev['start'],'endDate':ev['end']},'matches':[m]}
    (cache/'evidence.json').write_text(json.dumps(value))
    monkeypatch.setattr(config,'stats_dir',lambda tour:tmp_path)
    frame=pd.DataFrame([r['row']]).assign(date=pd.Timestamp(ev['start']),source_kind='stats')
    assert pd.notna(frame.played_date.iloc[0])
    annotated=chronology.annotate_sources(frame,'wta')
    assert annotated.played_date.isna().all()
    resolved=chronology.resolve_dates(annotated,'wta')
    assert resolved.stats_availability_basis.iloc[0]=='event_end'
    assert resolved.stats_available_at.iloc[0]==pd.Timestamp(ev['end'])
    assert resolved.date_basis.iloc[0]=='event_start'
    assert 'played_date' not in wta_results.timing(ev,m)


def test_bound_only_timing_survives_stats_source_preference():
    f=pd.DataFrame({'played_date':[pd.NaT,pd.NaT],
                    'event_start':[pd.NaT,pd.Timestamp('2024-01-01')],
                    'event_end':[pd.NaT,pd.Timestamp('2024-01-07')],
                    'date_evidence':[None,'reviewed-source']})
    out=chronology.carry_timing_evidence(f,pd.Series(['same','same']))
    assert out.played_date.isna().all()
    assert out.event_end.eq(pd.Timestamp('2024-01-07')).all()


def test_conflicting_event_bounds_do_not_pick_a_source_arbitrarily():
    f=pd.DataFrame({'played_date':[pd.NaT,pd.NaT],
                    'event_start':pd.to_datetime(['2024-01-01','2024-01-02']),
                    'event_end':pd.to_datetime(['2024-01-07','2024-01-08']),
                    'date_evidence':['first-source','second-source']})
    out=chronology.carry_timing_evidence(f,pd.Series(['same','same']))
    assert out[['played_date','event_start','event_end']].isna().all().all()
    assert out.date_evidence.isna().all()
