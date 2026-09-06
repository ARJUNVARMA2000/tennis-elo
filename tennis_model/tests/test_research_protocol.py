"""The evaluator cannot hide orientation, pairing, or cache-identity drift."""

import json
import os

import numpy as np
import pandas as pd
import pytest
from tennis_model.eval.protocol import (
    block_uncertainty,
    legacy_orientation_diagnostics,
    paired_report,
    require_paired,
    write_experiment_manifest,
)
from tennis_model.model.feature_cache import feature_cache_identity
from tennis_model.model.probability import paired_probability
from test_probability import predictor


def test_canonical_legacy_is_not_winner_first_or_the_corrected_average():
    pred = predictor()
    a, b = 'Charlie Three', 'Alfa One'
    frame = pred.features(a,b).assign(winner_name=a,loser_name=b)
    diag = legacy_orientation_diagnostics(pred.clf,pred.iso,frame)
    expected = 1 - pred.iso.predict(pred.clf.predict_proba(pred.features(b,a))[:,1])
    np.testing.assert_array_equal(diag['p_legacy_canonical'],expected)
    assert not np.allclose(expected,diag['p_legacy_winnerfirst'])
    assert not np.allclose(expected,paired_probability(pred.clf,pred.iso,frame[pred.features(a,b).columns]))
    with pytest.raises(ValueError,match='collide'):
        legacy_orientation_diagnostics(pred.clf,pred.iso,frame.assign(loser_name=a))


def paired_frames():
    base = pd.DataFrame({'date':pd.to_datetime(['2019-01-01','2019-02-01','2020-01-01','2020-02-01']),
        'winner_name':['A','C','E','G'],'loser_name':['B','D','F','H'], 'round_order':[1]*4,
        'tourney_id':['2019-1','2019-2','2020-1','2020-2'], 'p_combiner':[.5]*4})
    arm = base.copy()
    arm['p_combiner'] = .5 * np.exp([.01,.03,-.001,.002])
    return base,arm


def test_pairing_and_block_diagnostics_are_reproducible():
    base,arm=paired_frames()
    report=paired_report(base,arm)
    assert report == paired_report(base,arm)
    assert report['windows']['validation']['n'] == 2
    assert report['windows']['validation']['deltaLogloss'] == pytest.approx(.0005)
    assert report['gatePass'] and report['positiveValidationDelta']
    assert report['windows']['validation']['event']['blocks'] == 2
    with pytest.raises(ValueError,match='differ'):
        require_paired(base,arm.iloc[::-1])
    with pytest.raises(ValueError,match='unique'):
        require_paired(pd.concat([base,base]),pd.concat([arm,arm]))
    with pytest.raises(ValueError,match='columns'):
        require_paired(base,arm.drop(columns='tourney_id'))
    assert block_uncertainty([1.,2.],['same','same'])['status'] == 'insufficient-blocks'


def test_gate_pass_does_not_imply_positive_validation_effect():
    base,arm=paired_frames()
    arm['p_combiner'] = .5 * np.exp([.01,.03,-.02,.01])
    report = paired_report(base,arm)
    assert report['gatePass']
    assert not report['positiveValidationDelta']


def test_feature_cache_tracks_content_and_runtime_feature_overrides(monkeypatch,tmp_path):
    from tennis_model import config

    monkeypatch.setattr(config,'RAW_DIR',tmp_path)
    p=tmp_path/'inputs.csv'
    p.write_text('a,b\n1,2\n')
    stamp=p.stat().st_mtime_ns
    first=feature_cache_identity('atp')
    os.utime(p,ns=(stamp+10000,stamp+10000))
    assert feature_cache_identity('atp') == first
    p.write_text('a,b\n1,3\n')
    os.utime(p,ns=(stamp,stamp))
    changed=feature_cache_identity('atp')
    assert changed != first
    monkeypatch.setattr(config,'FEAT_PARAM_OVERRIDES',{'atp':{'layoff_days':87.}})
    assert feature_cache_identity('atp') != changed


def test_old_feature_cache_is_rebuilt_then_current_identity_reused(monkeypatch,tmp_path):
    from tennis_model.model import feature_cache, train
    from tennis_model.model.features import FEATURES

    monkeypatch.setattr(train,'OUTPUT_DIR',tmp_path)
    monkeypatch.setattr(feature_cache,'feature_cache_identity',lambda tour:'frozen-test-input')
    frame=pd.DataFrame({c:[0.] for c in FEATURES})
    frame.to_pickle(train._cache_path('atp'))  # old schema-only cache must miss
    calls=[]
    monkeypatch.setattr(train,'build_feature_frame',lambda **kw:(calls.append(kw) or frame))
    pd.testing.assert_frame_equal(train.load_or_build_features(tour='atp'),frame)
    pd.testing.assert_frame_equal(train.load_or_build_features(tour='atp'),frame)
    assert len(calls)==1


def test_experiment_registration_is_explicit_and_cannot_overwrite(tmp_path):
    path=tmp_path/'experiment.json'
    kwargs=dict(hypothesis='synthetic correctness check',parent_sha='a'*40,inputs_sha256='b'*64,
        evaluator_sha256='c'*64,data_through='2026-09-06',settings={},trial_budget=1,
        started_at='2026-09-06T00:00:00Z',oos_paths=[])
    assert len(write_experiment_manifest(path,**kwargs))==64
    record=json.loads(path.read_text())
    assert record['tuneYears']==[2010,2019] and record['validationStart']==2020
    with pytest.raises(FileExistsError):
        write_experiment_manifest(path,**kwargs)
