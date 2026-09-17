"""Exact calendar and synthetic planning-boundary/coverage regressions."""
import copy
import gzip
import json
from pathlib import Path

import pytest
import wta_calendar as c

F = Path(__file__).parent / 'fixtures/wta_orders'


@pytest.fixture
def payload():
    return json.loads(gzip.decompress((F / 'calendar-001.gz').read_bytes()))


def test_real_calendar_uses_entrants_and_distinguishes_whole_partial_ongoing(payload):
    result = c.capacity(payload, start='2026-09-08')
    assert result['windowEndExclusiveDate'] == '2026-10-08'
    assert result['futureWholeDrawCeilings'] == {'fully-contained-future': 116, 'partial-future': 95}
    assert result['optimisticFutureCeiling'] == 211 and result['ongoingRemainingUnknown'] == ['905']
    assert not result['partialEventsProrated'] and result['guaranteedEligiblePairs'] == 0
    assert not result['readyForLiveEvaluation']
    rows = {r['event']: r for r in result['events']}
    assert rows['2075']['wholeDrawCeiling'] == 27 and rows['1020']['wholeDrawCeiling'] == 95
    assert rows['905']['remainingCeilingFromCalendar'] is None
    assert len(result['events']) == 6


@pytest.mark.parametrize('field,value', [('numPages', 2), ('page', 1), ('numEntries', 30), ('pageSize', 20), ('pageSize', 101)])
def test_partial_calendar_cannot_claim_complete_inventory(payload, field, value):
    payload['pageInfo'][field] = value
    with pytest.raises(ValueError):
        c.capacity(payload, start='2026-09-08')


@pytest.mark.parametrize('kind', ['identical', 'conflicting', 'cancelled', 'unknown-status', 'draw', 'edition'])
def test_duplicate_and_invalid_editions_never_inflate_capacity(payload, kind):
    row = next(r for r in payload['content'] if r['tournamentGroup']['id'] == 2075)
    if kind in {'identical', 'conflicting'}:
        other = copy.deepcopy(row)
        if kind == 'conflicting':
            other['singlesDrawSize'] = 32
        payload['content'].append(other)
        payload['pageInfo']['numEntries'] += 1
    elif kind == 'cancelled':
        row['tournamentGroup'].setdefault('metadata', {})['cancelledSeasons'] = '2025,2026'
    elif kind == 'unknown-status':
        row['status'] = 'unknown'
    elif kind == 'draw':
        row['singlesDrawSize'] = 32.5
    else:
        row['year'] = 2025
    result = c.capacity(payload, start='2026-09-08')
    assert result['optimisticFutureCeiling'] == (211 if kind == 'identical' else 184)


def test_end_exclusive_start_inclusive_and_old_cancellation_not_current(payload):
    row = copy.deepcopy(next(r for r in payload['content'] if r['tournamentGroup']['id'] == 2075))
    row.update(startDate='2026-09-08', endDate='2026-10-08')
    # Use a bounded synthetic event to test both boundaries within the event duration contract.
    row['endDate'] = '2026-09-09'
    row['tournamentGroup']['metadata']['customStatus2020'] = 'CANCELLED'
    body = {'content': [row], 'pageInfo': {'page': 0, 'numPages': 0, 'numEntries': 1, 'pageSize': 100}}
    assert c.capacity(body, start='2026-09-08', days=1)['futureWholeDrawCeilings']['partial-future'] == 27
    assert c.capacity(body, start='2026-09-08', days=2)['futureWholeDrawCeilings']['partial-future'] == 0
    assert c.capacity(body, start='2026-09-07', days=1)['optimisticFutureCeiling'] == 0


@pytest.mark.parametrize('days', [0, 91, True, 1.5])
def test_window_is_explicit_and_bounded(payload, days):
    with pytest.raises(ValueError):
        c.capacity(payload, start='2026-09-08', days=days)


def test_read_calendar_requires_original_source_and_query_coverage(tmp_path):
    entry = json.loads((F / 'manifest.json').read_bytes())['calendar-001']
    root = tmp_path / 'calendar'
    root.mkdir()
    for field in ('receipt', 'attempt'):
        (root / f'{field}.json').write_text(json.dumps(entry[field]))
    (root / 'response.bin').write_bytes(gzip.decompress((F / 'calendar-001.gz').read_bytes()))
    assert c.read_capacity(root, trusted_root=tmp_path, start='2026-09-08')['optimisticFutureCeiling'] == 211
    with pytest.raises(ValueError, match='planning endpoint'):
        c.read_capacity(root, trusted_root=tmp_path, start='2026-09-08', days=90)
    for field in ('receipt', 'attempt'):
        entry[field]['url'] = entry[field]['url'].replace('api.wtatennis.com', 'example.com')
        if field == 'receipt':
            entry[field]['responseUrl'] = entry[field]['url']
        (root / f'{field}.json').write_text(json.dumps(entry[field]))
    with pytest.raises(ValueError, match='unrecognized calendar source'):
        c.read_capacity(root, trusted_root=tmp_path, start='2026-09-08')
