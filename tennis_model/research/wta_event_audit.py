"""Audit reported WTA event timelines; never export actual-start evidence."""
import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import prospective_sources as p
import wta_orders as o
from tennis_model.eval.prospective import _bytes, _digest, _time

SCHEMA = 'wta-event-timeline-audit-v1'
STATES = frozenset('UCWPSDMREFLwpTg')  # Explicit WTA bundle state codes, not coarse LIVE.
REASONS = {'OnCourt': 'C', 'PlayersArrived': 'g', 'Warmup': 'W', 'InProgress': 'P',
           'TimeAnnouncementAfterChangeoverOrSetBreak': 'T'}
SCORING = frozenset({'Point', 'Ace', 'DoubleFault'})
TYPES = SCORING | {'Fault', 'Let', 'StateIndicator', 'PhysioCalled', 'PhysioCallCancelled',
                   'MedicalTreatment', 'ToiletBreak'}


def source_identity(url):
    parts = urlsplit(url)
    match = re.fullmatch(r'/tennis/tournaments/([1-9][0-9]{0,7})/([0-9]{4})/matches/(LS[0-9]+)/(?P<kind>events|point-by-point)', parts.path)
    if (parts.scheme != 'https' or parts.netloc != 'api.wtatennis.com' or parts.query or parts.fragment or not match):
        raise ValueError('explicit official WTA event endpoint required')
    event, year = match[1], int(match[2])
    p.endpoint('wta', event=event, year=year)
    return event, year, match[3], match['kind']


def read_capture(root, *, trusted_root):
    root = Path(root)
    receipt = p._json(p._read(root / 'receipt.json', trusted_root))
    attempt = p._json(p._read(root / 'attempt.json', trusted_root))
    source_identity(receipt['url'])
    if (receipt.get('schema') != 'wta-lifecycle-inspection-v1'
            or any(receipt.get(k) != v for k, v in attempt.items()) or not attempt.get('requestedAt')):
        raise ValueError('inspection receipt/request mismatch')
    raw = p._read(root / 'response.bin', trusted_root)
    if (len(raw) != receipt.get('rawBytes') or hashlib.sha256(raw).hexdigest() != receipt.get('rawSHA256')
            or _time(receipt['receivedAt']) < _time(receipt['requestedAt'])):
        raise ValueError('event capture byte/clock integrity failure')
    verified = {**receipt, 'sha256': _digest(receipt)}
    if receipt.get('status') != 200 or receipt.get('error'):
        return {**verified, 'outcome': 'failed'}, None
    headers = receipt.get('headers', {})
    if (receipt.get('responseUrl') != receipt['url'] or receipt.get('rawComplete') is not True
            or len(raw) > p.MAX_BODY or headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json'
            or headers.get('content-encoding', 'identity').lower() != 'identity'):
        raise ValueError('invalid event transport')
    length = headers.get('content-length')
    if length is not None and (not re.fullmatch(r'[0-9]+', length) or int(length) != len(raw)):
        raise ValueError('incomplete event body')
    return {**verified, 'outcome': 'ok'}, p._json(raw)


def _offset(value):
    if type(value) is not str or not re.fullmatch(r'[+-](?:0[0-9]|1[0-4])[0-5][0-9]', value):
        raise ValueError('explicit corroborated numeric offset required')
    minutes = int(value[1:3]) * 60 + int(value[3:])
    if minutes > 840:
        raise ValueError('offset outside supported range')
    return timezone(timedelta(minutes=minutes if value[0] == '+' else -minutes))


def _games(value):
    if type(value) is not str or not re.fullmatch(r'\d+-\d+(?:\(\d+\))?(?:[ ,]+\d+-\d+(?:\(\d+\))?)*', value):
        raise ValueError('unrecognized full game score')
    return [[int(a), int(b)] for a, b in re.findall(r'(\d+)-(\d+)', value)]


def _marker(row):
    return {k: row.get(k) for k in ('Index', 'Name', 'Timestamp', 'TimestampLocal', 'LastUpdated',
                                   'MatchTime', 'MatchState', 'MatchScore', 'GameScore', 'Attributes')}


def audit(payload, api, order, *, event, year, match_id, observed_at, utc_offset):
    event, observed = str(event), _time(observed_at)
    tournament, rows, _, _ = p._wta(api)
    header = payload.get('Tournament', {})
    expected_header = {'tournamentGroup': {'id': event}, 'year': year}
    for item in (tournament, header):
        if (str(item.get('tournamentGroup', {}).get('id')) != expected_header['tournamentGroup']['id']
                or item.get('year') != year):
            raise ValueError('timeline/API edition disagreement')
    if any(header.get(k) != tournament.get(k) for k in ('startDate', 'endDate', 'singlesDrawSize', 'level')):
        raise ValueError('timeline/API tournament metadata disagreement')
    matches = [r for r in rows if r['sourceMatchId'] == match_id]
    if len(matches) != 1:
        raise ValueError('requested match is not one admitted API main single')
    match = matches[0]
    if order.get('event') != event or order.get('year') != year:
        raise ValueError('order edition disagreement')
    occurrences = [r for r in order['observations'] if r['sourceMatchId'] == match_id]
    identity = {str(match['raw']['PlayerID' + side]): name for side, name in zip(('A', 'B'), match['names'])}
    if not occurrences or any(r['round'] != match['round'] or dict(zip(r['playerIDs'], r['players'])) != identity for r in occurrences):
        raise ValueError('order/API player or round disagreement')
    tz = _offset(utc_offset)
    days = {date.fromisoformat(r['pageDate']) for r in occurrences}
    raw_events = payload.get('Events')
    if type(raw_events) is not list or len(raw_events) > 20000:
        raise ValueError('bounded event list required')
    base = {'event': event, 'year': year, 'sourceMatchId': match_id, 'sourceMatchKey': f'wta:{event}:{year}:{match_id}',
            'playersByID': identity, 'round': match['round'], 'apiStatus': match['status'],
            'observedAt': observed.isoformat(), 'sourceOffsetText': utc_offset,
            'qualification': 'reported-event-timeline-only', 'actualStartVerified': False,
            'physicalClockErrorSeconds': None, 'liveLifecycleObserved': False, 'readyForLiveEvaluation': False,
            'rawEvents': len(raw_events), 'completePhysicalTimelineEstablished': False}
    if not raw_events:
        return {**base, 'outcome': 'unavailable', 'findings': [{'code': 'empty-event-list'}],
                'internallyConsistent': False, 'reportedStartMarker': None}
    findings = []
    def finding(code, index=None):
        findings.append({'code': code, **({'index': index} if index is not None else {})})
    players = payload.get('Players')
    if type(players) is not dict or set(players) != set(identity):
        finding('player-inventory-disagreement')
    else:
        for pid, info in players.items():
            if (type(info) is not dict or str(info.get('id')) != pid
                    or p.canonical_name(info.get('fullName', '')) != identity[pid]
                    or p.canonical_name(f"{info.get('firstName', '')} {info.get('lastName', '')}") != identity[pid]):
                finding('player-name-id-disagreement')
    previous_index, previous_time, parsed, indices = None, None, [], set()
    for number, row in enumerate(raw_events):
        try:
            if type(row) is not dict or type(row.get('Attributes')) is not dict:
                raise ValueError('event object required')
            attrs, index = row['Attributes'], row['Index']
            if type(index) is not int or index < 0 or type(attrs.get('index')) is not int or attrs['index'] != index:
                raise ValueError('invalid index attributes')
            if index in indices or (previous_index is not None and index <= previous_index):
                finding('duplicate-or-regressing-index', index)
            indices.add(index)
            previous_index = index
            if str(row['EventID']) != event or type(row['EventYear']) is not int or row['EventYear'] != year or row['MatchID'] != match_id:
                finding('event-row-identity-disagreement', index)
            if type(row.get('CourtID')) is not int or row['CourtID'] <= 0:
                finding('invalid-court-id', index)
            if row.get('Name') not in TYPES or row.get('MatchState') not in STATES:
                finding('unsupported-event-kind-or-state', index)
            # MedicalTreatment in the real feed omits the duplicate type field.
            if 'type' in attrs and attrs['type'] != row.get('Name'):
                finding('event-type-disagreement', index)
            for field, target in [('set', 'Set'), ('game', 'Game'), ('score', 'GameScore')]:
                if field in attrs and attrs[field] != row.get(target):
                    finding('duplicate-attribute-disagreement', index)
            if row['Name'] == 'StateIndicator' and REASONS.get(attrs.get('reason')) != row.get('MatchState'):
                finding('unsupported-or-conflicting-state-reason', index)
            if str(row.get('PlayerId')) not in {'0', *identity}:
                finding('event-player-id-disagreement', index)
            for field in ('player', 'server', 'receiver'):
                if field in attrs and str(attrs[field]) not in identity:
                    finding('attribute-player-id-disagreement', index)
            if 'player' in attrs and str(attrs['player']) != str(row.get('PlayerId')):
                finding('player-attribute-disagreement', index)
            if 'server' in attrs and 'receiver' in attrs and attrs['server'] == attrs['receiver']:
                finding('self-service-pair', index)
            if 'firstServe' in attrs and type(attrs['firstServe']) is not bool:
                finding('ambiguous-service-flag', index)
            if row['Name'] in SCORING and any(k not in attrs for k in ('player', 'server', 'receiver', 'firstServe')):
                finding('incomplete-scoring-identity', index)
            stamp, updated = _time(row['Timestamp']), _time(row['LastUpdated'])
            if stamp > observed or updated > observed or updated < stamp:
                finding('event-update-clock-conflict', index)
            if previous_time is not None and stamp < previous_time:
                finding('event-time-regression', index)
            previous_time = stamp
            local = datetime.fromisoformat(row['TimestampLocal'])
            if local.tzinfo is not None or local.replace(tzinfo=tz) != stamp:
                finding('local-utc-clock-conflict', index)
            if not min(days) <= local.date() <= max(days):
                finding('event-outside-observed-order-days', index)
            if 'referenceTimeAsLocalTime' in attrs:
                ref = datetime.fromisoformat(attrs['referenceTimeAsLocalTime'])
                if ref.tzinfo is not None or ref != local.replace(microsecond=0):
                    finding('reference-local-clock-conflict', index)
            elapsed = row['MatchTime']
            if type(elapsed) is not str or not re.fullmatch(r'[0-9]{2}:[0-5][0-9]:[0-5][0-9]', elapsed):
                raise ValueError('invalid elapsed field')
            h, m, s = map(int, elapsed.split(':'))
            parsed.append((row, stamp, h * 3600 + m * 60 + s))
        except (KeyError, TypeError, ValueError, AttributeError):
            finding('malformed-event-record', number)
    starts = [r for r in raw_events if type(r) is dict and type(r.get('Attributes')) is dict
              and r.get('Name') == 'StateIndicator' and r['Attributes'].get('reason') == 'InProgress']
    transitions = [r for r, _, _ in parsed if r['Name'] == 'StateIndicator']
    scoring = [r for r, _, _ in parsed if r['Name'] in SCORING]
    marker = _marker(starts[0]) if len(starts) == 1 else None
    if len(starts) != 1:
        finding('missing-or-multiple-initial-progress-markers')
    elif any(starts[0].get(k) != v for k, v in {'MatchState': 'P', 'Set': 1, 'Game': 1,
                                              'GameScore': '0-0', 'MatchScore': '0-0', 'MatchTime': '00:00:00'}.items()):
        finding('invalid-initial-progress-marker')
    initial = [r['Attributes'].get('reason') for r in transitions if r['Attributes'].get('reason') in {'OnCourt', 'PlayersArrived', 'Warmup', 'InProgress'}]
    if initial != ['OnCourt', 'PlayersArrived', 'Warmup', 'InProgress']:
        finding('incomplete-or-reordered-initial-sequence')
    if not scoring:
        finding('no-observed-scoring-event')
    elif marker:
        try:
            if scoring[0]['Index'] <= marker['Index'] or _time(scoring[0]['Timestamp']) <= _time(marker['Timestamp']):
                finding('scoring-not-after-initial-marker')
        except (TypeError, ValueError):
            finding('unreadable-initial-marker')
    score_agreement, residuals, gap = None, [], None
    if scoring and match['status'] == 'completed':
        try:
            games = _games(match['score'])
            if match['winner'] != match['names'][0]:
                games = [r[::-1] for r in games]
            score_agreement = _games(scoring[-1]['MatchScore']) == games
        except ValueError:
            score_agreement = False
        if not score_agreement:
            finding('last-scoring-result-disagreement')
    if marker:
        try:
            start = _time(marker['Timestamp'])
            residuals = [(stamp - start).total_seconds() - elapsed for _, stamp, elapsed in parsed if stamp >= start]
            if residuals and (min(residuals) <= -1 or max(residuals) >= 1):
                finding('elapsed-clock-arithmetic-disagreement')
            gap = (start - _time(match['raw']['MatchTimeStamp'])).total_seconds()
        except (KeyError, ValueError, TypeError):
            finding('unreadable-reported-marker-or-api-clock')
    return {**base, 'outcome': 'observed' if not findings else 'inconsistent',
            'findings': findings, 'internallyConsistent': not findings, 'reportedStartMarker': marker,
            'reportedStartMarkerInternallySupported': bool(marker and not findings),
            'transitions': [_marker(r) for r in transitions], 'firstScoringEvent': _marker(scoring[0]) if scoring else None,
            'lastObservedEvent': _marker(raw_events[-1]) if type(raw_events[-1]) is dict else None,
            'scoringEvents': len(scoring), 'eventTypeCounts': dict(Counter(r['Name'] for r, _, _ in parsed)),
            'lastScoringResultAgreesWithAPI': score_agreement,
            'terminalStateObserved': any(r['MatchState'] == 'F' for r, _, _ in parsed),
            'elapsedResidualSeconds': {'min': round(min(residuals), 6), 'max': round(max(residuals), 6)} if residuals else None,
            'apiTimestampToReportedProgressSeconds': gap}


def run(event_root, order_root, *, trusted_root):
    receipt, payload = read_capture(event_root, trusted_root=trusted_root)
    event, year, match_id, kind = source_identity(receipt['url'])
    if kind != 'events':
        raise ValueError('timeline audit requires an events source')
    saved = o.read_collection(order_root, trusted_root=trusted_root)
    ar, api = p.read_capture(saved['apiRoot'], trusted_root=trusted_root)
    pr, raw_page = o.read_inspection(saved['pageRoot'], trusted_root=trusted_root, media='text/html')
    parsed = o.parse_page(raw_page, event, year)
    observed = max(_time(r['receivedAt']) for r in (receipt, ar, pr)).isoformat()
    report = audit(payload, api, saved['report'], event=event, year=year, match_id=match_id,
                   observed_at=receipt['receivedAt'], utc_offset=parsed['utcOffsetText']) if payload is not None else {
                       'outcome': 'gap', 'findings': [{'code': 'failed-event-transport'}],
                       'observedAt': observed, 'actualStartVerified': False, 'readyForLiveEvaluation': False}
    report['evidenceAvailableAt'] = observed
    return {'schema': SCHEMA, 'eventRoot': str(Path(event_root).absolute()), 'orderRoot': str(Path(order_root).absolute()),
            'provenance': 'retrospective-audit', 'eventReceiptSHA256': receipt['sha256'],
            'orderCollectionSHA256': saved['sha256'], 'sourceReceipts': {'events': receipt, 'api': ar, 'page': pr}, 'report': report}


def write_audit(output, event_root, order_root, *, trusted_root):
    if p.a._absolute_without_symlink_resolution(output).is_relative_to(p.a._absolute_without_symlink_resolution(o.u.OUTPUT_DIR)):
        raise ValueError('event audits cannot enter production output')
    result = run(event_root, order_root, trusted_root=trusted_root)
    p._write(output, _bytes({**result, 'sha256': _digest(result)}), trusted_root)
    return read_audit(output, trusted_root=trusted_root)


def read_audit(path, *, trusted_root):
    saved = p._json(p._read(path, trusted_root))
    body = {k: v for k, v in saved.items() if k != 'sha256'}
    if saved.get('schema') != SCHEMA or saved.get('sha256') != _digest(body):
        raise ValueError('event audit integrity failure')
    if body != run(saved['eventRoot'], saved['orderRoot'], trusted_root=trusted_root):
        raise ValueError('event audit replay disagreement')
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('events', type=Path)
    parser.add_argument('order', type=Path)
    parser.add_argument('--trusted-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = write_audit(args.output, args.events, args.order, trusted_root=args.trusted_root)['report']
    print(json.dumps({k: report.get(k) for k in ('outcome', 'rawEvents', 'scoringEvents', 'findings', 'actualStartVerified')}))


if __name__ == '__main__':
    main()
