"""Real WTA timelines plus explicitly synthetic corruption/identity regressions."""
import copy
import gzip
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import test_wta_orders as orders_fixture
import time_evidence
import wta_event_audit as e

F = Path(__file__).parent / 'fixtures/wta_events'
MANIFEST = json.loads((F / 'manifest.json').read_bytes())


def fixture(label):
    entry = copy.deepcopy(MANIFEST[label])
    encoded = (F / f'{label}.gz').read_bytes()
    assert hashlib.sha256(encoded).hexdigest() == entry['compressedSHA256']
    raw = gzip.decompress(encoded)
    assert hashlib.sha256(raw).hexdigest() == entry['rawSHA256']
    return entry, raw


@pytest.fixture
def values():
    _, raw = fixture('final-events')
    original = orders_fixture.pair('old')
    return json.loads(raw), original[1], orders_fixture.extract(original)


def audit(values, match_id='LS001', **kwargs):
    return e.audit(*values, event='2075', year=2025, match_id=match_id,
                   observed_at=kwargs.pop('observed_at', MANIFEST['final-events']['receipt']['receivedAt']),
                   utc_offset=kwargs.pop('utc_offset', '-0600'), **kwargs)


def codes(result):
    return {f['code'] for f in result['findings']}


@pytest.mark.parametrize('label,mid,total,points,gap', [
    ('final-events', 'LS001', 185, 119, 1283.073),
    ('semifinal-events', 'LS002', 220, 136, 1421.56)])
def test_real_timelines_include_full_initial_stages_and_midnight_rollover(values, label, mid, total, points, gap):
    values = list(values)
    values[0] = json.loads(fixture(label)[1])
    result = audit(values, mid)
    assert result['outcome'] == 'observed' and result['internallyConsistent']
    assert not result['findings'] and result['rawEvents'] == total and result['scoringEvents'] == points
    assert result['apiTimestampToReportedProgressSeconds'] == pytest.approx(gap)
    assert result['lastScoringResultAgreesWithAPI'] and not result['terminalStateObserved']
    assert result['reportedStartMarkerInternallySupported']
    assert result['reportedStartMarker']['Index'] == 8 and result['reportedStartMarker']['MatchState'] == 'P'
    assert result['elapsedResidualSeconds']['min'] > -1 and result['elapsedResidualSeconds']['max'] < 1
    if mid == 'LS002':
        assert result['lastObservedEvent']['Timestamp'].startswith('2025-09-14T00:00:58')
        assert result['lastObservedEvent']['TimestampLocal'].startswith('2025-09-13T18:00:58')
    else:
        medical = next(r for r in values[0]['Events'] if r['Index'] == 281)
        assert 'type' not in medical['Attributes']  # Real optional duplicate field.
    assert not result['actualStartVerified'] and not result['readyForLiveEvaluation']
    assert result['physicalClockErrorSeconds'] is None and not result['liveLifecycleObserved']
    with pytest.raises(ValueError, match='qualified live start'):
        time_evidence.check_mode(e.SCHEMA)


@pytest.mark.parametrize('kind', ['event-header', 'api-header', 'header-dates', 'order-edition', 'order-round', 'order-identity', 'no-order-match', 'no-api-match'])
def test_edition_and_match_identity_require_all_sources(values, kind):
    payload, api, order = values
    if kind == 'event-header':
        payload['Tournament']['year'] = 2026
    elif kind == 'api-header':
        api['tournament']['year'] = 2026
    elif kind == 'header-dates':
        payload['Tournament']['endDate'] = '2025-09-15'
    elif kind == 'order-edition':
        order['event'] = '9999'
    elif kind in {'order-round', 'order-identity'}:
        row = next(r for r in order['observations'] if r['sourceMatchId'] == 'LS001')
        if kind == 'order-round':
            row['round'] = 'SF'
        else:
            row['playerIDs'][0] = '999999'
    elif kind == 'no-order-match':
        order['observations'] = [r for r in order['observations'] if r['sourceMatchId'] != 'LS001']
    else:
        api['matches'] = [r for r in api['matches'] if r['MatchID'] != 'LS001']
    with pytest.raises(ValueError):
        audit(values)


@pytest.mark.parametrize('kind,expected', [
    ('player-key', 'player-inventory-disagreement'), ('player-name', 'player-name-id-disagreement'),
    ('row-event', 'event-row-identity-disagreement'), ('row-match', 'event-row-identity-disagreement'),
    ('duplicate-index', 'duplicate-or-regressing-index'), ('attribute-index', 'malformed-event-record'),
    ('name', 'event-type-disagreement'), ('unknown-state', 'unsupported-event-kind-or-state'),
    ('reason', 'unsupported-or-conflicting-state-reason'), ('attribute-score', 'duplicate-attribute-disagreement'),
    ('row-player', 'event-player-id-disagreement'), ('attribute-player', 'attribute-player-id-disagreement'),
    ('server-equals-receiver', 'self-service-pair'), ('service-flag', 'ambiguous-service-flag'),
    ('missing-scorer', 'incomplete-scoring-identity'), ('time-regression', 'event-time-regression'),
    ('update-before-time', 'event-update-clock-conflict'), ('local-zone', 'local-utc-clock-conflict'),
    ('local-reference', 'reference-local-clock-conflict'), ('offset-free', 'malformed-event-record'),
    ('elapsed', 'elapsed-clock-arithmetic-disagreement'), ('wrong-elapsed-type', 'malformed-event-record'),
    ('bad-marker-clock', 'unreadable-initial-marker'), ('malformed-row', 'malformed-event-record'),
    ('missing-name', 'malformed-event-record'), ('last-score', 'last-scoring-result-disagreement')])
def test_entire_event_record_falsifier_keeps_adverse_evidence(values, kind, expected):
    payload = values[0]
    row = payload['Events'][4]
    if kind == 'player-key':
        payload['Players']['999999'] = payload['Players'].pop('332285')
    elif kind == 'player-name':
        payload['Players']['332285']['fullName'] = 'Synthetic Replacement'
    elif kind == 'row-event':
        row['EventYear'] = 2026
    elif kind == 'row-match':
        row['MatchID'] = 'LS002'
    elif kind == 'duplicate-index':
        row['Index'] = row['Attributes']['index'] = 8
    elif kind == 'attribute-index':
        row['Attributes']['index'] = 11
    elif kind == 'name':
        row['Attributes']['type'] = 'Ace'
    elif kind == 'unknown-state':
        row['MatchState'] = '?'
    elif kind == 'reason':
        payload['Events'][3]['Attributes']['reason'] = 'UndocumentedStage'
    elif kind == 'attribute-score':
        row['Attributes']['score'] = '40-0'
    elif kind == 'row-player':
        row['PlayerId'] = 999999
    elif kind == 'attribute-player':
        row['Attributes']['player'] = '999999'
    elif kind == 'server-equals-receiver':
        row['Attributes']['server'] = row['Attributes']['receiver']
    elif kind == 'service-flag':
        row['Attributes']['firstServe'] = 'true'
    elif kind == 'missing-scorer':
        row['Attributes'].pop('server')
    elif kind == 'time-regression':
        row['Timestamp'] = '2025-09-14T21:08:00+00:00'
    elif kind == 'update-before-time':
        row['LastUpdated'] = '2025-09-14T21:08:00+00:00'
    elif kind == 'local-zone':
        row['TimestampLocal'] += '-06:00'
    elif kind == 'local-reference':
        payload['Events'][3]['Attributes']['referenceTimeAsLocalTime'] = '2025-09-14T15:00:00'
    elif kind == 'offset-free':
        row['Timestamp'] = '2025-09-14T21:09:32.93'
    elif kind == 'elapsed':
        row['MatchTime'] = '00:00:10'
    elif kind == 'wrong-elapsed-type':
        row['MatchTime'] = 32
    elif kind == 'bad-marker-clock':
        payload['Events'][3]['Timestamp'] = 'not a clock'
    elif kind == 'malformed-row':
        payload['Events'][4] = None
    elif kind == 'missing-name':
        payload['Events'][3].pop('Name')
    else:
        payload['Events'][-1]['MatchScore'] = '4-6,3-6'
    result = audit(values)
    assert expected in codes(result) and not result['internallyConsistent']
    assert not result['reportedStartMarkerInternallySupported']
    assert not result['actualStartVerified']


@pytest.mark.parametrize('kind', ['missing-progress', 'duplicate-progress', 'nonzero-start', 'late-start', 'missing-warmup', 'no-points'])
def test_initial_sequence_is_explicit_and_unique(values, kind):
    rows = values[0]['Events']
    if kind == 'missing-progress':
        rows.pop(3)
    elif kind == 'duplicate-progress':
        rows.insert(4, copy.deepcopy(rows[3]))
    elif kind == 'nonzero-start':
        rows[3]['GameScore'] = '15-0'
    elif kind == 'late-start':
        rows[3], rows[4] = rows[4], rows[3]
    elif kind == 'missing-warmup':
        rows.pop(2)
    else:
        values[0]['Events'] = [r for r in rows if r['Name'] not in e.SCORING]
    result = audit(values)
    assert not result['reportedStartMarkerInternallySupported'] and result['findings']


def shift_clock_fields(payload, delta):
    for row in payload['Events']:
        for key in ('Timestamp', 'TimestampLocal', 'LastUpdated'):
            row[key] = (datetime.fromisoformat(row[key]) + delta).isoformat()
        attrs = row['Attributes']
        if 'referenceTimeAsLocalTime' in attrs:
            attrs['referenceTimeAsLocalTime'] = (datetime.fromisoformat(attrs['referenceTimeAsLocalTime']) + delta).isoformat()


def test_same_clock_shift_can_pass_internal_arithmetic_without_physical_qualification(values):
    original = audit(values)
    shift_clock_fields(values[0], timedelta(minutes=10))
    shifted = audit(values)
    assert shifted['internallyConsistent'] and shifted['elapsedResidualSeconds'] == original['elapsedResidualSeconds']
    assert shifted['apiTimestampToReportedProgressSeconds'] == pytest.approx(original['apiTimestampToReportedProgressSeconds'] + 600)
    assert not shifted['actualStartVerified'] and shifted['physicalClockErrorSeconds'] is None


def test_wrong_local_day_and_future_claim_are_not_repaired_by_clock_agreement(values):
    shift_clock_fields(values[0], timedelta(days=1))
    result = audit(values, observed_at='2025-09-14T23:00:00+00:00')
    assert {'event-outside-observed-order-days', 'event-update-clock-conflict'} <= codes(result)


def test_first_serve_flag_is_not_a_physical_first_serve_timestamp(values):
    values[0]['Events'][4]['Attributes']['firstServe'] = False
    result = audit(values)
    assert result['internallyConsistent'] and not result['actualStartVerified']
    assert result['firstScoringEvent']['Timestamp'] != result['reportedStartMarker']['Timestamp']


def test_both_source_sides_can_swap_without_changing_player_identity(values):
    raw = next(r for r in values[1]['matches'] if r['MatchID'] == 'LS001')
    for key in list(raw):
        if key.endswith('A') and key[:-1] + 'B' in raw:
            other = key[:-1] + 'B'
            raw[key], raw[other] = raw[other], raw[key]
    raw['Winner'] = '2'
    for row in values[0]['Events']:
        row['MatchScore'] = ','.join(f'{b}-{a}' for a, b in e._games(row['MatchScore']))
    assert audit(values)['internallyConsistent']


def test_empty_events_are_unavailable_not_a_complete_start_history(values):
    values[0]['Events'], values[0]['Players'] = [], {}
    result = audit(values)
    assert result['outcome'] == 'unavailable' and not result['internallyConsistent']
    assert result['reportedStartMarker'] is None


@pytest.mark.parametrize('offset', ['0', '-06:00', '+1459', None])
def test_offset_must_be_explicit_and_bounded(values, offset):
    with pytest.raises(ValueError):
        audit(values, utc_offset=offset)


def materialize(tmp_path):
    orders_fixture.materialize(tmp_path)
    orders_fixture.intake(tmp_path, 'order', 'old')
    for name in MANIFEST:
        entry, raw = fixture(name)
        root = tmp_path / name
        root.mkdir()
        for field in ('attempt', 'receipt'):
            (root / f'{field}.json').write_text(json.dumps(entry[field]))
        (root / 'response.bin').write_bytes(raw)


def test_exact_receipts_failures_replay_and_create_only_outputs(tmp_path):
    materialize(tmp_path)
    for label in ('final-points', 'semifinal-points'):
        receipt, body = e.read_capture(tmp_path / label, trusted_root=tmp_path)
        assert receipt['status'] == 404 and receipt['outcome'] == 'failed' and body is None
        assert receipt['rawBytes'] == 0
    output = tmp_path / 'audit.json'
    saved = e.write_audit(output, tmp_path / 'final-events', tmp_path / 'order', trusted_root=tmp_path)
    assert saved == e.read_audit(output, trusted_root=tmp_path)
    assert saved['report']['observedAt'] == MANIFEST['final-events']['receipt']['receivedAt']
    assert saved['provenance'] == 'retrospective-audit'
    with pytest.raises((ValueError, OSError, e.p.a.PredictorArtifactError)):
        e.write_audit(output, tmp_path / 'final-events', tmp_path / 'order', trusted_root=tmp_path)
    body = {k: v for k, v in saved.items() if k != 'sha256'}
    body['report']['actualStartVerified'] = True
    output.write_bytes(e._bytes({**body, 'sha256': e._digest(body)}))
    with pytest.raises(ValueError, match='replay disagreement'):
        e.read_audit(output, trusted_root=tmp_path)


@pytest.mark.parametrize('kind', ['raw', 'media', 'length', 'url', 'future-clock', 'attempt'])
def test_source_capture_integrity_cannot_be_bypassed(tmp_path, kind):
    materialize(tmp_path)
    root = tmp_path / 'final-events'
    receipt = json.loads((root / 'receipt.json').read_bytes())
    if kind == 'raw':
        (root / 'response.bin').write_bytes(b'{}')
    elif kind == 'media':
        receipt['headers']['content-type'] = 'text/html'
    elif kind == 'length':
        receipt['headers']['content-length'] = '1'
    elif kind == 'url':
        receipt['url'] = receipt['url'].replace('api.wtatennis.com', 'example.com')
    elif kind == 'future-clock':
        receipt['receivedAt'] = '2020-01-01T00:00:00+00:00'
    else:
        receipt['requestedAt'] = '2026-09-08T00:00:00+00:00'
    (root / 'receipt.json').write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        e.read_capture(root, trusted_root=tmp_path)


def test_failed_event_source_is_gap_and_production_symlinks_are_refused(tmp_path, monkeypatch):
    materialize(tmp_path)
    receipt_path = tmp_path / 'final-events/receipt.json'
    receipt = json.loads(receipt_path.read_bytes())
    receipt['status'] = 503
    receipt_path.write_text(json.dumps(receipt))
    assert e.run(tmp_path / 'final-events', tmp_path / 'order', trusted_root=tmp_path)['report']['outcome'] == 'gap'
    monkeypatch.setattr(e.o.u, 'OUTPUT_DIR', tmp_path / 'production')
    with pytest.raises(ValueError, match='production'):
        e.write_audit(tmp_path / 'production/audit.json', tmp_path / 'final-events', tmp_path / 'order', trusted_root=tmp_path)
    link = tmp_path / 'linked'
    link.symlink_to(tmp_path / 'final-events', target_is_directory=True)
    with pytest.raises(e.p.a.PredictorArtifactError):
        e.read_capture(link, trusted_root=tmp_path)
