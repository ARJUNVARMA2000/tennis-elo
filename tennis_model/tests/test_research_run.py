"""The run guard rejects drift before fitting and cannot launder an interrupted trial."""

import json

import pytest
from tennis_model.eval import research_run as runner


def fixture_freeze(tmp_path, monkeypatch):
    contract = {'inputsSHA256':'a'*64, 'evaluatorSHA256':'b'*64,
                'tours':{'integer-key-table':{2:'two',10:'ten'}}}
    monkeypatch.setattr(runner, 'current_contract', lambda: contract.copy())
    path = tmp_path / 'freeze.json'
    runner.create_freeze(path, data_through={'atp':'2026-09-05','wta':'2026-09-06'})
    return path, contract


def test_drift_stops_before_execution_and_success_cannot_be_overwritten(tmp_path, monkeypatch):
    path, contract = fixture_freeze(tmp_path, monkeypatch)
    seen = []
    kwargs = dict(hypothesis='test', settings={}, execute=lambda *a: (seen.append(1) or {'n':2}))
    directory = tmp_path / 'run'
    contract['inputsSHA256'] = 'c'*64
    with pytest.raises(ValueError, match='changed'):
        runner.run_registered(path, directory, **kwargs)
    assert not seen and not directory.exists()
    contract['inputsSHA256'] = 'a'*64
    assert runner.run_registered(path, directory, **kwargs) == {'n':2}
    assert json.loads((directory/'registration.json').read_text())['status'] == 'registered'
    assert (directory/'completion.json').exists()
    with pytest.raises(FileExistsError):
        runner.run_registered(path, directory, **kwargs)
    assert seen == [1]


def test_midrun_drift_and_interruption_leave_failure_without_completion(tmp_path, monkeypatch):
    path, contract = fixture_freeze(tmp_path, monkeypatch)

    def changed(*args):
        contract['evaluatorSHA256'] = 'c'*64
        return {'claimed':'success'}

    with pytest.raises(ValueError, match='changed'):
        runner.run_registered(path, tmp_path/'drift', hypothesis='test', settings={}, execute=changed)
    assert (tmp_path/'drift/failure.json').exists()
    assert not (tmp_path/'drift/completion.json').exists()
    contract['evaluatorSHA256'] = 'b'*64

    def interrupted(*args):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        runner.run_registered(path, tmp_path/'interrupted', hypothesis='test', settings={}, execute=interrupted)
    assert json.loads((tmp_path/'interrupted/failure.json').read_text())['errorType'] == 'KeyboardInterrupt'
    assert not (tmp_path/'interrupted/completion.json').exists()


@pytest.mark.parametrize('tour', ['atp', 'wta'])
def test_baseline_calls_full_window_five_bags_and_actual_wta_gate(tmp_path, monkeypatch, tour):
    import pandas as pd
    from tennis_model.eval import ab_data
    from tennis_model.model import features, train

    frame = pd.DataFrame({'date':pd.to_datetime(['2010-01-01','2020-01-01']),
        'winner_name':['A','C'], 'loser_name':['B','D'], 'round_order':[1,1],
        'draw_level':['main','main'], 'completed':[True,True], 'p_combiner':[.55,.6],
        'source_kind':['historical','stats'], 'date_basis':['unknown','played_date']})
    calls = []
    monkeypatch.setattr(features, 'build_feature_frame', lambda **kw:frame.copy())
    monkeypatch.setattr(ab_data, '_build_dual_feature_frames', lambda tour:(frame.copy(),frame.copy()))

    def walk(rows, **kwargs):
        calls.append(kwargs)
        return rows.copy()

    def gate(base, enriched, thresholds, **kwargs):
        assert thresholds == (None, 32)
        calls.append(kwargs)
        incumbent = base.assign(uses_lower_state=[False, True])
        incumbent.loc[1, 'p_combiner'] = .65
        return {None:base, 32:incumbent}

    monkeypatch.setattr(train, 'walk_forward', walk)
    monkeypatch.setattr(train, 'walk_forward_state_gate', gate)
    result = runner.baseline(tour, tmp_path, {'dataThrough':{tour:'2026-09-06'}})
    assert result['n'] == 2 and result['unscoredEligible'] == 0
    assert calls[0]['start_test'] == 2010 and calls[0]['end_test'] == 2026
    assert calls[0]['n_bag'] == 5
    assert (tmp_path/'oos.pkl').exists()
    assert (tmp_path/'wta-main-reference.pkl').exists() == (tour == 'wta')
