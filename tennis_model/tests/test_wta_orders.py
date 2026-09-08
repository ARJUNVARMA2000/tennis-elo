"""Exact official witnesses; all source mutations and later times are synthetic QA."""
import copy
import gzip
import hashlib
import http.client
import io
import json
import urllib.error
from collections import Counter
from datetime import datetime
from email.message import Message
from pathlib import Path

import prospective_sources as p
import pytest
import time_evidence
import wta_orders as o

F = Path(__file__).parent / 'fixtures/wta_orders'
MANIFEST = json.loads((F / 'manifest.json').read_bytes())


def fixture(name):
    entry = copy.deepcopy(MANIFEST[name])
    encoded = (F / f'{name}.gz').read_bytes()
    assert hashlib.sha256(encoded).hexdigest() == entry['compressedSHA256']
    raw = gzip.decompress(encoded)
    assert hashlib.sha256(raw).hexdigest() == entry['rawSHA256']
    return entry, raw


def pair(kind='live'):
    names = {'live': ('wta-live-order-page', 'wta-live-matches'),
             'old': ('guadalajara-2025-page', 'guadalajara-2025-matches'),
             'future': ('guadalajara-page', 'guadalajara-2026-matches')}[kind]
    (pe, raw), (ae, body) = [fixture(n) for n in names]
    return raw, json.loads(body), {**pe['receipt'], 'outcome': 'ok'}, ae['receipt']


def extract(values):
    raw, api, pr, ar = values
    return o.normalize(raw, api, page_receipt=pr, api_receipt=ar)


def materialize(tmp_path):
    for name in MANIFEST:
        entry, raw = fixture(name)
        root = tmp_path / name
        root.mkdir()
        for field in ('receipt', 'attempt'):
            (root / f'{field}.json').write_text(json.dumps(entry[field]))
        (root / 'response.bin').write_bytes(raw)


def intake(tmp_path, label, kind='live'):
    names = {'live': ('wta-live-order-page', 'wta-live-matches'),
             'old': ('guadalajara-2025-page', 'guadalajara-2025-matches'),
             'future': ('guadalajara-page', 'guadalajara-2026-matches')}[kind]
    return o.ingest(tmp_path / label, *(tmp_path / n for n in names), trusted_root=tmp_path)


def test_current_exact_times_and_population_do_not_inherit_later_court_start():
    result = extract(pair())
    assert result['pageRows'] == 299 and len(result['observations']) == 124
    assert len(result['exclusions']) == 175 and result['completeForAbsenceComparison']
    assert Counter(r['publishedTimeKind'] for r in result['observations']) == {
        'historical-or-nonscheduled': 120, 'sequence-only': 2,
        'unresolved-time': 1, 'first-match-court-start': 1}
    rows = {r['sourceMatchId']: r for r in result['observations']}
    assert rows['LS73992552']['publishedTimeUTC'] == '2026-09-08T15:30:00+00:00'
    assert rows['LS73992554']['publishedTimeUTC'] is None
    assert o._time(rows['LS73992554']['apiScheduleField']) == o._time('2026-09-08T23:00:00+00:00')
    assert all(not r['actualStartVerified'] for r in result['observations'])
    assert not result['firstPublicationEstablished']
    with pytest.raises(ValueError, match='qualified live start'):
        time_evidence.check_mode(o.SCHEMA)


def test_completed_archive_preserves_comments_cross_day_occurrences_and_lost_labels():
    result = extract(pair('old'))
    assert result['pageRows'] == 65 and len(result['observations']) == 31
    assert len({r['sourceMatchKey'] for r in result['observations']}) == 27
    assert all(r['publishedTimeUTC'] is None for r in result['observations'])
    assert result['completeForAbsenceComparison']
    assert {r['publishedTimeKind'] for r in result['observations']} == {'historical-or-nonscheduled'}


def test_future_is_unpublished_not_authoritative_empty():
    result = extract(pair('future'))
    assert result['outcome'] == 'unpublished' and result['pageRows'] == 0
    assert not result['completeForAbsenceComparison'] and not result['observations']


@pytest.mark.parametrize('url', [
    'http://www.wtatennis.com/tournaments/905/us-open/2026/order-of-play',
    'https://example.com/tournaments/905/us-open/2026/order-of-play',
    'https://www.wtatennis.com/tournaments/905/us-open/2026/order-of-play?x=1',
    'https://www.wtatennis.com/tournaments/905/us-open/2026/order-of-play#x',
    'https://www.wtatennis.com/tournaments/0/us-open/2026/order-of-play'])
def test_only_explicit_official_edition_urls(url):
    with pytest.raises(ValueError):
        o.page_identity(url)


@pytest.mark.parametrize('mutation', ['edition', 'missing-widget', 'same-day-duplicate', 'conflicting-marker', 'empty-without-marker'])
def test_actual_html_structure_failures(mutation):
    values = list(pair())
    raw = values[0]
    if mutation == 'edition':
        raw = raw.replace(b'data-tournament-id="905"', b'data-tournament-id="906"')
    elif mutation == 'missing-widget':
        raw = raw.replace(b'tournament-oop/order-of-play', b'unknown-widget')
    elif mutation == 'same-day-duplicate':
        raw = raw.replace(b'LS73992554', b'LS73992552')
    elif mutation == 'conflicting-marker':
        raw = raw.replace(b'Arthur Ashe Stadium', b'Order of Play Not Available Yet')
    else:
        values = list(pair('future'))
        raw = values[0].replace(b'Order of Play Not Available Yet', b'Unknown response')
    values[0] = raw
    with pytest.raises(ValueError):
        extract(values)


@pytest.mark.parametrize('mutation', ['offset', 'placeholder', 'clock-date', 'clock-value', 'api-clock', 'dedicated', 'status', 'player', 'round', 'stale'])
def test_source_disagreements_never_invent_start_or_exhaustive_identity(monkeypatch, mutation):
    values = list(pair())
    parsed = o.parse_page(values[0], '905', 2026)
    row = next(r for r in parsed['occurrences'] if r['sourceMatchId'] == 'LS73992552')
    if mutation == 'offset':
        row['courtClock']['data-utc-offset'] = '+0100'
    elif mutation == 'placeholder':
        row['courtClock']['data-utc-offset'] = parsed['utcOffsetText'] = '0'
    elif mutation == 'clock-date':
        row['courtClock']['data-date'] = '2026-09-09'
    elif mutation == 'clock-value':
        row['courtClock']['data-start-time'] = 'about noon'
    elif mutation == 'api-clock':
        next(r for r in values[1]['matches'] if r['MatchID'] == row['sourceMatchId'])['MatchTimeStamp'] = '2026-09-08T16:30:00+00:00'
    elif mutation == 'dedicated':
        row['dedicatedClockUnqualified'] = True
    elif mutation == 'status':
        row['pageStatus'] = 'C'
    elif mutation == 'player':
        row['playerLinks'][0] = ['/players/999999/synthetic-player']
    elif mutation == 'round':
        row['pageRound'] = 'Final'
    else:
        values[2]['headers']['age'] = '601'
    monkeypatch.setattr(o, 'parse_page', lambda *args: parsed)
    result = extract(values)
    found = [r for r in result['observations'] if r['sourceMatchId'] == row['sourceMatchId']]
    if mutation in {'player', 'round'}:
        assert not found and not result['completeForAbsenceComparison']
    elif mutation == 'stale':
        assert not result['completeForAbsenceComparison']
    else:
        assert found[0]['publishedTimeUTC'] is None and found[0]['publishedTimeKind'] == 'unresolved-time'
        if mutation == 'status':
            assert not result['completeForAbsenceComparison']


def test_real_intake_replay_hashes_create_only_and_unpublished_gap(tmp_path):
    materialize(tmp_path)
    live = intake(tmp_path, 'live')
    old = intake(tmp_path, 'old', 'old')
    intake(tmp_path, 'future', 'future')
    history = o.history([tmp_path / n for n in ('live', 'old', 'future')], trusted_root=tmp_path)
    assert len(history['versions']) == 151 and not history['changes'] and not history['identityConflicts']
    assert len(history['gaps']) == 1
    assert live['provenance'] == 'retrospective-intake' and len(old['report']['observations']) == 31
    assert live == o.read_collection(tmp_path / 'live', trusted_root=tmp_path)
    with pytest.raises((ValueError, FileExistsError)):
        intake(tmp_path, 'live')
    with pytest.raises(ValueError):
        o.history([tmp_path / 'live'] * 2, trusted_root=tmp_path)
    raw = tmp_path / 'wta-live-order-page/response.bin'
    raw.write_bytes(raw.read_bytes() + b' ')
    with pytest.raises(ValueError, match='integrity'):
        o.read_collection(tmp_path / 'live', trusted_root=tmp_path)


def synthetic_history(monkeypatch, tmp_path, reports):
    saved = {}
    for n, report in enumerate(reports):
        report['observedAt'] = f'2026-09-08T06:{n:02}:00+00:00'
        saved[str(tmp_path / str(n))] = {'report': report, 'sha256': str(n)}
    monkeypatch.setattr(o, 'read_collection', lambda path, **kwargs: saved[str(path)])
    return o.history([Path(k) for k in saved], trusted_root=tmp_path)


def test_cross_day_repeat_is_not_temporal_revision(monkeypatch, tmp_path):
    report = extract(pair('old'))
    result = synthetic_history(monkeypatch, tmp_path, [report, copy.deepcopy(report)])
    assert not result['changes'] and not result['identityConflicts']
    assert sum(len(v) for v in result['versions'].values()) == 62


def test_history_revisions_absence_reappearance_and_earlier_time(monkeypatch, tmp_path):
    first = extract(pair())
    first['observations'] = [next(r for r in first['observations'] if r['sourceMatchId'] == 'LS73992552')]
    second, absent = copy.deepcopy(first), copy.deepcopy(first)
    second['observations'][0].update(court='Synthetic court', publishedTimeUTC='2026-09-08T15:00:00+00:00')
    absent['observations'] = []
    result = synthetic_history(monkeypatch, tmp_path, [first, second, absent, copy.deepcopy(first)])
    assert Counter(c['kind'] for c in result['changes']) == {
        'fields-changed': 2, 'earlier-published-time': 1,
        'absent-from-complete-source-pair': 1, 'added-or-reappeared': 1}


@pytest.mark.parametrize('reason', ['page/API-player-identity-disagreement', 'page/API-round-disagreement'])
def test_contradictory_exclusions_remain_in_history_after_positive_returns(monkeypatch, tmp_path, reason):
    first = extract(pair())
    second = copy.deepcopy(first)
    second['observations'] = [r for r in second['observations'] if r['sourceMatchId'] != 'LS73992552']
    second['exclusions'].append({'sourceMatchId': 'LS73992552', 'reason': reason})
    second['completeForAbsenceComparison'] = False
    result = synthetic_history(monkeypatch, tmp_path, [first, second, copy.deepcopy(first)])
    assert result['identityConflicts'] == ['wta:905:2026:LS73992552']
    assert not any(c['kind'] == 'absent-from-complete-source-pair' for c in result['changes'])


def test_source_side_swap_preserves_player_mapping_but_replaced_id_conflicts(monkeypatch, tmp_path):
    first = extract(pair())
    first['observations'] = [first['observations'][0]]
    swapped = copy.deepcopy(first)
    for k in ('players', 'playerIDs'):
        swapped['observations'][0][k].reverse()
    assert not synthetic_history(monkeypatch, tmp_path, [first, swapped])['identityConflicts']
    swapped['observations'][0]['playerIDs'][0] = '999999'
    assert synthetic_history(monkeypatch, tmp_path, [first, swapped])['identityConflicts']


class Response(io.BytesIO):
    def __init__(self, raw, url, status=200, headers=None):
        super().__init__(raw)
        self.url, self.status = url, status
        self.headers = Message()
        for k, v in (headers or {'content-type': 'text/html', 'content-length': str(len(raw)),
                                'date': 'Tue, 08 Sep 2026 06:00:00 GMT'}).items():
            self.headers[k] = v

    def geturl(self):
        return self.url


def transport(monkeypatch, responses):
    requests = []
    class Opener:
        def open(self, request, timeout):
            requests.append(request)
            assert timeout == 25 and request.get_header('Accept-encoding') == 'identity'
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
    monkeypatch.setattr(o.urllib.request, 'build_opener', lambda *a: Opener())
    monkeypatch.setattr(p, '_now', lambda: datetime.fromisoformat('2026-09-08T06:00:00+00:00'))
    return requests


@pytest.mark.parametrize('failure', ['http', 'redirect', 'timeout', 'partial', 'media', 'length', 'oversize'])
def test_failed_transports_are_retained_once(monkeypatch, tmp_path, failure):
    url = pair()[2]['url']
    response = Response(b'body', url)
    if failure == 'http':
        response = urllib.error.HTTPError(url, 503, 'unavailable', response.headers, io.BytesIO(b'body'))
    elif failure == 'redirect':
        response.url = 'https://example.com/redirect'
    elif failure == 'timeout':
        response = TimeoutError('synthetic timeout')
    elif failure == 'partial':
        response = http.client.IncompleteRead(b'body', 100)
    elif failure == 'media':
        response.headers.replace_header('content-type', 'application/json')
    elif failure == 'length':
        response.headers.replace_header('content-length', '100')
    else:
        monkeypatch.setattr(p, 'MAX_BODY', 3)
    requests = transport(monkeypatch, [response])
    receipt, body = o.fetch_page(tmp_path / 'capture', trusted_root=tmp_path, url=url)
    assert receipt['outcome'] == 'failed' and body is None and len(requests) == 1
    assert (tmp_path / 'capture/attempt.json').exists() and (tmp_path / 'capture/response.bin').exists()


def test_collect_malformed_html_stops_before_api_and_preserves_gap(monkeypatch, tmp_path):
    url = pair()[2]['url']
    requests = transport(monkeypatch, [Response(b'<html>unknown</html>', url)])
    result = o.collect(tmp_path / 'collection', trusted_root=tmp_path, url=url)
    assert len(requests) == 1 and result['report']['outcome'] == 'gap'
    assert result['apiRoot'] is None and not result['report']['observations']


def test_collect_valid_widget_fetches_paired_api_only_once(monkeypatch, tmp_path):
    materialize(tmp_path)
    raw, api, pr, ar = pair('future')
    requests = transport(monkeypatch, [Response(raw, pr['url'])])
    calls = []
    def api_fetch(root, **kwargs):
        calls.append(kwargs)
        root.mkdir()
        for name in ('attempt.json', 'receipt.json', 'response.bin'):
            (root / name).write_bytes((tmp_path / 'guadalajara-2026-matches' / name).read_bytes())
    monkeypatch.setattr(p, 'fetch_once', api_fetch)
    result = o.collect(tmp_path / 'collection', trusted_root=tmp_path, url=pr['url'])
    assert len(requests) == len(calls) == 1
    assert calls[0]['event'] == '2075' and calls[0]['year'] == 2026
    assert result['report']['outcome'] == 'unpublished'


def test_filesystem_output_guards(tmp_path, monkeypatch):
    materialize(tmp_path)
    monkeypatch.setattr(o.u, 'OUTPUT_DIR', tmp_path / 'production')
    with pytest.raises(ValueError):
        intake(tmp_path, 'production/nested')
    link = tmp_path / 'linked'
    link.symlink_to(tmp_path / 'guadalajara-page', target_is_directory=True)
    with pytest.raises(p.a.PredictorArtifactError):
        o.read_inspection(link, trusted_root=tmp_path, media='text/html')


@pytest.mark.parametrize('mutation', ['edition', 'dates', 'missing-api-card', 'unpublished-with-matches'])
def test_paired_api_identity_and_incomplete_page(monkeypatch, mutation):
    values = list(pair())
    if mutation == 'unpublished-with-matches':
        values[0], _, values[2], _ = pair('future')
        values[1]['tournament']['tournamentGroup']['id'] = 2075
        values[1]['tournament']['startDate'] = '2026-09-13'
        values[1]['tournament']['endDate'] = '2026-09-19'
    elif mutation == 'edition':
        values[1]['tournament']['year'] = 2025
    elif mutation == 'dates':
        values[1]['tournament']['endDate'] = '2026-09-12'
    else:
        parsed = o.parse_page(values[0], '905', 2026)
        parsed['occurrences'] = [r for r in parsed['occurrences'] if r['sourceMatchId'] != 'LS73992552']
        monkeypatch.setattr(o, 'parse_page', lambda *args: parsed)
        result = extract(values)
        assert result['missingAPIMainMatchIDsFromPage'] == ['LS73992552']
        assert not result['completeForAbsenceComparison']
        return
    with pytest.raises(ValueError):
        extract(values)


def test_rehashed_derived_edit_is_detected_by_replay(tmp_path):
    materialize(tmp_path)
    saved = intake(tmp_path, 'live')
    saved['report']['observations'][0]['publishedTimeUTC'] = '2026-09-08T12:00:00+00:00'
    body = {k: v for k, v in saved.items() if k != 'sha256'}
    (tmp_path / 'live/collection.json').write_bytes(o._bytes({**body, 'sha256': o._digest(body)}))
    with pytest.raises(ValueError, match='replay integrity'):
        o.read_collection(tmp_path / 'live', trusted_root=tmp_path)
