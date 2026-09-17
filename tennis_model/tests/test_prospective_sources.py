"""Exact public response fixtures and explicitly synthetic negative/transport cases."""
import copy
import gzip
import hashlib
import io
import json
import urllib.error
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path

import prospective_sources as p
import pytest
from tennis_model.eval import prospective_shadow as ps
from tennis_model.model import artifact as a
from test_dynamic_shadow import shadow  # noqa: F401

FIXTURES = Path(__file__).parent / 'fixtures/prospective_sources'


@pytest.fixture
def payloads():
    manifest = json.loads((FIXTURES/'manifest.json').read_text())
    values = []
    for name in ('espn','wta'):
        encoded = (FIXTURES/f'{name}.json.gz').read_bytes()
        raw = gzip.decompress(encoded)
        assert hashlib.sha256(encoded).hexdigest() == manifest[name]['compressedSHA256']
        assert hashlib.sha256(raw).hexdigest() == manifest[name]['rawSHA256']
        values.append(json.loads(raw))
    return values


def scheduled(payload):
    return next(m for m in payload['matches'] if m.get('MatchID') == 'LS73992552')


def test_exact_real_census_mapping_and_unverified_timing(payloads):
    result = p.audit(*payloads)
    assert result['mapping']['espnId'] == '189-2026'
    assert result['mapping']['wtaId'] == '905'
    assert result['mapping']['sharedCompleted'] == 119
    assert result['wtaMainRealRows'] == result['espnMainRealRows'] == 123
    assert len(result['scheduleCandidates']) == 2
    assert len(result['resultCandidates']) == 119
    assert result['actualTimedResults'] == 0 and not result['readyForLive']
    assert result['scheduleFieldComparisons'] == {'n':119,'equal':66,'minSeconds':-300.,'maxSeconds':85800.}
    assert {r['earliestStartAt'] for r in result['scheduleCandidates']} == {'2026-09-08T15:30:00+00:00','2026-09-08T23:00:00+00:00'}
    assert result['espnExcluded']['qualifying'] == 112
    assert all('actualStartedAt' not in r and 'finishedAt' not in r for r in result['resultCandidates'])
    with pytest.raises(ValueError,match='live export unavailable'):
        p.export_live(result)


def test_mapping_ignores_sponsor_and_requires_unique_event_evidence(payloads):
    payloads[0]['events'][0]['name'] = 'Completely Changed Sponsor'
    assert p.audit(*payloads)['mapping']['sharedCompleted'] == 119
    duplicate = copy.deepcopy(payloads[0]['events'][0])
    duplicate['id'] = 'different-event'
    payloads[0]['events'].append(duplicate)
    assert p.audit(*payloads)['issues'] == ['event-mapping-unproven-or-ambiguous']


@pytest.mark.parametrize('change',['edition','duplicates','self-id','qualifying','doubles','unknown-round','wrong-population'])
def test_scope_identity_and_edition_guards(payloads,change):
    row = scheduled(payloads[1])
    if change == 'edition':
        row['EventYear'] = 2025
        with pytest.raises(ValueError,match='edition conflict'):
            p.audit(*payloads)
    elif change == 'duplicates':
        payloads[1]['matches'].append(copy.deepcopy(row))
        with pytest.raises(ValueError,match='duplicate'):
            p.audit(*payloads)
    elif change == 'wrong-population':
        payloads[1]['tournament']['level'] = 'WTA 125'
        with pytest.raises(ValueError,match='main-tour'):
            p.audit(*payloads)
    else:
        if change == 'self-id':
            row['PlayerIDB'] = row['PlayerIDA']
        elif change == 'qualifying':
            row['DrawLevelType'] = 'Q'
        elif change == 'doubles':
            row['DrawMatchType'] = 'D'
        else:
            row['RoundID'] = 'unknown'
        assert len(p.audit(*payloads)['scheduleCandidates']) == 1


@pytest.mark.parametrize('field,value,reason',[
    ('NotBeforeISOTime',None,'missing-zoned-not-before'),
    ('NotBeforeISOTime','11:30','missing-zoned-not-before'),
    ('NotBeforeISOTime','12:30-0400','conflicting-schedule-times'),
    ('isEstimatedStartTime',True,'estimated-or-unknown-start'),
    ('estimatedStartTime','false','estimated-or-unknown-start'),
    ('estimatedStartTime',0,'estimated-or-unknown-start'),
])
def test_estimates_and_conflicting_lower_bounds_never_convert(payloads,field,value,reason):
    scheduled(payloads[1])[field] = value
    result = p.audit(*payloads)
    assert len(result['scheduleCandidates']) == 1
    assert result['conversionExclusions'][reason] == 1


def test_timezone_rollover_and_missing_context(payloads):
    row = scheduled(payloads[1])
    row['MatchTimeStamp'] = '2026-09-09T01:30+10:00'
    row['NotBeforeISOTime'] = '11:30-0400'
    assert p.audit(*payloads)['scheduleCandidates'][0]['earliestStartAt'] == '2026-09-08T15:30:00+00:00'
    payloads[1]['tournament']['inOutdoor'] = None
    assert not p.audit(*payloads)['scheduleCandidates']


def test_round_labels_and_non_power_of_two_draws():
    assert p._round({'id':'2','displayName':'Round 2'},96,provider='espn') == 'R64'
    assert p._round('2',28,provider='wta') == 'R16'
    with pytest.raises(ValueError,match='ambiguous'):
        p._round({'id':'5','displayName':'Semifinal'},128,provider='espn')
    with pytest.raises(ValueError,match='unknown'):
        p._round({'id':'99','displayName':'Round'},32,provider='espn')


class Response(io.BytesIO):
    def __init__(self,raw,status=200,headers=None,url=None):
        super().__init__(raw)
        self.status = status
        self.headers = Message()
        for key,value in (headers or {'content-type':'application/json','content-length':str(len(raw)),
                                      'date':'Tue, 08 Sep 2026 01:00:00 GMT'}).items():
            self.headers[key] = value
        self.url = url or p.endpoint('espn')
    def geturl(self):
        return self.url


def transport(monkeypatch,response):
    class Opener:
        def open(self,request,timeout):
            assert timeout == 25
            assert request.get_header('Accept-encoding') == 'identity'
            if isinstance(response,Exception):
                raise response
            return response
    monkeypatch.setattr(p.urllib.request,'build_opener',lambda *args:Opener())
    monkeypatch.setattr(p,'_now',lambda:datetime(2026,9,8,1,tzinfo=UTC))


def test_transport_publishes_exact_bytes_and_exclusive_receipt(tmp_path,monkeypatch):
    raw = b'{"events":[]}'
    transport(monkeypatch,Response(raw))
    root = tmp_path/'attempt'
    receipt = p.fetch_once(root,trusted_root=tmp_path,source='espn')
    assert receipt['outcome'] == 'ok' and receipt['rawComplete']
    assert (root/'response.bin').read_bytes() == raw
    loaded,payload = p.read_capture(root,trusted_root=tmp_path)
    assert loaded == receipt and payload == {'events':[]}
    assert p.freshness(receipt)['ready']
    with pytest.raises(FileExistsError):
        p.fetch_once(root,trusted_root=tmp_path,source='espn')
    (root/'response.bin').write_bytes(b'bad')
    with pytest.raises(ValueError,match='integrity'):
        p.read_capture(root,trusted_root=tmp_path)


@pytest.mark.parametrize('kind',['dns','timeout','429','redirect','media','encoding','duplicate-json','size','length'])
def test_transport_failures_are_durable_and_never_fresh(tmp_path,monkeypatch,kind):
    response = Response(b'{"events":[]}')
    if kind == 'dns':
        response = urllib.error.URLError('unavailable')
    elif kind == 'timeout':
        response = TimeoutError('timed out')
    elif kind == '429':
        response.status = 429
        response.headers['retry-after'] = '60'
    elif kind == 'redirect':
        response.url = 'https://different.example.org/private'
    elif kind == 'media':
        response.headers.replace_header('content-type','text/html')
    elif kind == 'encoding':
        response.headers['content-encoding'] = 'gzip'
    elif kind == 'duplicate-json':
        response = Response(b'{"events":[],"events":[]}')
    elif kind == 'size':
        monkeypatch.setattr(p,'MAX_BODY',10)
    else:
        response.headers.replace_header('content-length','1')
    transport(monkeypatch,response)
    root = tmp_path/'attempt'
    receipt = p.fetch_once(root,trusted_root=tmp_path,source='espn')
    assert receipt['outcome'] == 'failed'
    assert (root/'response.bin').exists()
    assert not p.freshness(receipt)['ready']
    with pytest.raises(ValueError,match='attempt failed'):
        p.read_capture(root,trusted_root=tmp_path)


def test_symlink_parent_rejected_without_external_mutation(tmp_path,monkeypatch):
    transport(monkeypatch,Response(b'{}'))
    outside = tmp_path/'outside'
    outside.mkdir()
    link = tmp_path/'link'
    link.symlink_to(outside,target_is_directory=True)
    with pytest.raises(a.PredictorArtifactError):
        p.fetch_once(link/'attempt',trusted_root=tmp_path,source='espn')
    assert not list(outside.iterdir())


def test_interrupted_publication_leaves_attempt_and_raw_without_final_receipt(tmp_path,monkeypatch):
    transport(monkeypatch,Response(b'{}'))
    original = p.write_json
    def crash(path,*args,**kwargs):
        if path.name == 'receipt.json':
            raise OSError('interrupted')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(p,'write_json',crash)
    root = tmp_path/'attempt'
    with pytest.raises(OSError):
        p.fetch_once(root,trusted_root=tmp_path,source='espn')
    assert (root/'attempt.json').exists() and (root/'response.bin').exists()
    assert not (root/'receipt.json').exists()
    with pytest.raises(a.PredictorArtifactError):
        p.read_capture(root,trusted_root=tmp_path)


@pytest.mark.parametrize('change',['age','future-date','missing-date','old-observation','future-observation'])
def test_http_and_observation_freshness_are_distinct(tmp_path,monkeypatch,change):
    transport(monkeypatch,Response(b'{}'))
    receipt = p.fetch_once(tmp_path/'attempt',trusted_root=tmp_path,source='espn')
    if change == 'age':
        receipt['headers']['age'] = '601'
    elif change == 'future-date':
        receipt['headers']['date'] = 'Wed, 09 Sep 2026 01:00:00 GMT'
    elif change == 'missing-date':
        receipt['headers'].pop('date')
    elif change == 'old-observation':
        receipt['receivedAt'] = '2026-09-08T00:00:00Z'
    else:
        receipt['receivedAt'] = '2026-09-09T00:00:00Z'
    assert not p.freshness(receipt)['ready']
    assert not p.freshness(receipt)['matchLevelFreshnessVerified']


def test_wrong_response_edition_and_arbitrary_endpoints_rejected(tmp_path,monkeypatch,payloads):
    with pytest.raises(ValueError):
        p.endpoint('https://external.example.org')
    with pytest.raises(ValueError):
        p.endpoint('wta',event='../secrets',year=2026)
    raw = json.dumps(payloads[1]).encode()
    transport(monkeypatch,Response(raw,url=p.endpoint('wta',event='999',year=2026)))
    with pytest.raises(ValueError,match='edition differs'):
        p.fetch_once(tmp_path/'attempt',trusted_root=tmp_path,source='wta',event='999',year=2026)


def observation(i):
    return {'source':'wta','receivedAt':f'2026-09-08T0{i}:00:00Z','sha256':str(i)*64}


def test_lifecycle_changes_are_not_actual_times_and_replacements_are_conflicts(payloads):
    first = copy.deepcopy(payloads[1])
    second,third = copy.deepcopy(first),copy.deepcopy(first)
    scheduled(second)['MatchState'] = 'P'
    scheduled(third)['MatchState'] = 'F'
    report = p.lifecycle([(observation(1),first),(observation(2),second),(observation(3),third)])
    assert report['counts']['completePreLiveTerminal'] == 1
    assert not report['actualTimingInferred']
    scheduled(third)['PlayerNameLastB'] = 'Changed Player'
    changed = p.lifecycle([(observation(1),first),(observation(2),second),(observation(3),third)])
    assert changed['counts'].get('completePreLiveTerminal',0) == 0
    assert changed['counts']['identityOrStatusConflict'] == 1
    regressed = p.lifecycle([(observation(1),third),(observation(2),first)])
    assert any(r['statusRegression'] for r in regressed['changed'])


def test_duplicate_lifecycle_snapshot_match_rejected(payloads):
    payloads[1]['matches'].append(copy.deepcopy(scheduled(payloads[1])))
    with pytest.raises(ValueError,match='duplicate'):
        p.lifecycle([(observation(1),payloads[1])])


def test_repeated_identical_snapshots_do_not_establish_lifecycle(payloads):
    result = p.lifecycle([(observation(1),payloads[1]),(observation(2),payloads[1])])
    assert not result['changed']
    assert result['counts'].get('completePreLiveTerminal',0) == 0


def test_draft_batches_retain_original_time_and_no_fabricated_timing(payloads):
    analysis = p.audit(*payloads)
    r = {'receivedAt':'2026-09-08T00:27:12Z','url':p.endpoint('wta',event='905',year=2026),'sha256':'a'*64}
    batches = p.draft_batches(analysis,r,r)
    assert batches['schedule']['observedAt'] == r['receivedAt']
    assert not batches['schedule']['readyForLive']
    assert all('finishedAt' not in row for row in batches['results']['matches'])
    row = batches['schedule']['matches'][0]
    assert ps._context(row) is not None
    assert ps.match_key(row,'wta')


def test_diagnostic_adapter_batch_through_real_mixed_format_runner(payloads,tmp_path,monkeypatch,request):
    # Import fixture providers explicitly; forecast/outcome/time substitutions are synthetic QA.
    from test_dynamic_shadow import PROVENANCE
    from test_predictor_artifact import _valid_predictor
    shadow_model = request.getfixturevalue('shadow')
    model = _valid_predictor('wta')
    for field in ('elo','lower_elo','srv','lower_srv','ctx','lower_ctx','meta'):
        setattr(model,field,copy.deepcopy(getattr(shadow_model,field)))
    inc, cand = tmp_path/'incumbent.pkl',tmp_path/'candidate.shadow'
    a.save_predictor_artifact(model,inc,trusted_root=tmp_path)
    shadow_model.save(cand,trusted_root=tmp_path)
    now = [datetime.now(UTC)+timedelta(seconds=1)]
    monkeypatch.setattr(ps,'_now',lambda:now[0])
    root = tmp_path/'synthetic-qa'
    ps.register(root,trusted_root=tmp_path,incumbent=inc,candidate=cand,provenance=PROVENANCE,
                hypothesis='Synthetic adapter integration only',evidence_kind='synthetic-qa',
                sources={'scheduleHost':'api.wtatennis.com','resultHost':'api.wtatennis.com',
                         'timingEvidence':'Synthetic fixtures only','cadence':'Unit test'})
    r = {'receivedAt':now[0].isoformat(),'url':p.endpoint('wta',event='905',year=2026),'sha256':'a'*64}
    batch = p.draft_batches(p.audit(*payloads),r,r)['schedule']
    row = batch['matches'][0]
    batch['matches'] = [row]
    start = (now[0]+timedelta(hours=2)).isoformat()
    row.update(playerA='A',playerB='B',earliestStartAt=start)
    row['context']['as_of'] = start
    assert ps.capture(root,batch,trusted_root=tmp_path) == {'captured':1}
    now[0] += timedelta(hours=4)
    unsupported = {**batch,'observedAt':now[0].isoformat(),'matches':[{**row,'status':'completed','winner':'A'}]}
    report = ps.grade(root,unsupported,trusted_root=tmp_path)
    assert report['evidenceKind'] == 'synthetic-qa'
    assert report['graded'] == 0 and report['excluded'] == {'missingActualTiming':1}


def test_failed_fetch_cli_returns_failure_status(monkeypatch,capsys,tmp_path):
    import sys
    monkeypatch.setattr(sys,'argv',['sources','--trusted-root',str(tmp_path),'fetch','espn',str(tmp_path/'attempt')])
    monkeypatch.setattr(p,'fetch_once',lambda **kwargs:{'outcome':'failed','detail':'HTTP failure'})
    with pytest.raises(SystemExit) as stopped:
        p.main()
    assert stopped.value.code == 1
    assert 'HTTP failure' in capsys.readouterr().out


def test_audit_never_writes_production_output(tmp_path,monkeypatch):
    monkeypatch.setattr(p,'OUTPUT_DIR',tmp_path/'output')
    with pytest.raises(ValueError,match='production output'):
        p.fetch_once(tmp_path/'output'/'attempt',trusted_root=tmp_path,source='espn')
    assert not (tmp_path/'output').exists()
