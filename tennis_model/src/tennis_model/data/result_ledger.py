"""Hash-pinned reviewed input and independent normalized-population checks."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import pandas as pd

from .. import config
from .names import name_key
from .wta_results import canonical_name, games, normalize_result

LEDGER_DIR = Path(__file__).with_name('reviewed')
RECEIPT_SCHEMA = 'result-integrity-v1'


def load_ledger(tour):
    raw = (LEDGER_DIR / f'{tour}.json').read_bytes()  # missing is an error, never empty scope
    expected = config.REVIEWED_RESULTS[tour]
    if hashlib.sha256(raw).hexdigest() != expected['sha256']:
        raise ValueError(f'{tour}: reviewed result ledger changed without a policy review')
    identity = json.dumps([expected, config.MATCH_POPULATION_VERSION, config.PLAYER_ALIASES], sort_keys=True)
    return deepcopy(_decode_ledger(raw, tour, identity))


@lru_cache(maxsize=4)
def _decode_ledger(raw, tour, identity):
    expected = config.REVIEWED_RESULTS[tour]
    ledger = json.loads(raw)
    records = ledger['records']
    if (ledger.get('schema') != 'reviewed-results-v1' or ledger.get('tour') != tour
            or ledger.get('populationVersion') != config.MATCH_POPULATION_VERSION
            or len(records) != expected['records']
            or len({r['key'] for r in records}) != len(records)):
        raise ValueError('invalid reviewed result ledger contract')
    for record in records:
        if record['decision'] != 'admit':
            raise ValueError('unknown reviewed result disposition')
        evidence = record['wta']
        row = normalize_result(evidence['event'], evidence['match'], outcome=record['outcome'],
                               score=record['row']['score'])
        if row != {k:v for k,v in record['row'].items() if k != 'espn_id'}:
            raise ValueError(f"reviewed result normalization drift: {record['key']}")
    return ledger


def result_frame(tour):
    from .results import CANON
    ledger = load_ledger(tour)
    rows = [{**r['row'], 'reviewed_result_key': r['key'],
             'source_file': f'reviewed/{tour}.json'} for r in ledger['records']]
    out = pd.DataFrame(rows)
    return out.reindex(columns=sorted(set(CANON) | set(out.columns)))


def partition_reviewed_duplicates(frame, match_keys):
    """Attach a reviewed result only to copies from its proven edition.

    Identical winner/loser/round/games can recur in the same season. In particular,
    Swiatek beat Cirstea 6-1 6-1 in both Doha and Madrid's 2024 R32. A result donor
    must not move Doha to Madrid or collapse the two historical rows. This partition
    changes only groups with an independently reviewed donor; unreviewed groups retain
    their prior keys and are not certified as complete by this scoped ledger.
    """
    out = match_keys.copy()
    reviewed = frame[frame.source_kind.eq('reviewed')]
    if reviewed.empty:
        return out
    touched = frame[match_keys.isin(match_keys.loc[reviewed.index])]
    for broad_key, group in touched.groupby(match_keys.loc[touched.index], sort=False):
        donors = group[group.source_kind.eq('reviewed')].to_dict('records')
        for idx, row in group.iterrows():
            options = []
            for donor in donors:
                start, end = pd.Timestamp(donor['event_start']), pd.Timestamp(donor['event_end'])
                day = pd.Timestamp(row['date'])
                eid = row.get('espn_id')
                if pd.notna(eid) and str(eid) != donor['espn_id']:
                    continue
                native = re.fullmatch(r'(\d{4})-W?0*(\d+)', str(row.get('tourney_id')))
                expected = re.fullmatch(r'(\d{4})-W?0*(\d+)', donor['tourney_id'])
                same_native = native is not None and native.groups() == expected.groups()
                if native is not None and not same_native:
                    continue
                # The archive can use the uniform stamp immediately before the calendar.
                # Admit that case only with the matching numeric edition, never a title.
                in_span = start <= day <= end or (same_native and day == start-pd.Timedelta(days=1))
                if in_span:
                    options.append(donor['reviewed_result_key'])
            if len(options) > 1:
                raise ValueError('ambiguous reviewed event identity in result deduplication')
            suffix = options[0] if options else 'outside-reviewed-editions'
            out.loc[idx] = f'{broad_key}|{suffix}'
    return out


def self_pair_mask(frame):
    if frame.empty:
        return pd.Series(False, index=frame.index)
    a = frame.winner_name.fillna('').map(lambda n: name_key(canonical_name(n)))
    b = frame.loser_name.fillna('').map(lambda n: name_key(canonical_name(n)))
    invalid = a.ne('') & a.eq(b)
    if {'winner_id', 'loser_id'}.issubset(frame):
        wa = pd.to_numeric(frame.winner_id, errors='coerce')
        la = pd.to_numeric(frame.loser_id, errors='coerce')
        invalid |= wa.gt(0) & wa.eq(la)
    return invalid


def apply_quarantines(frame, tour):
    """Exclude only reviewed exact source rows; never guess an opponent or skip in scoring."""
    excluded = pd.Series(False, index=frame.index)
    for q in load_ledger(tour)['quarantines']:
        mask = pd.Series(True, index=frame.index)
        for key, value in q['match'].items():
            if key not in frame:
                mask &= False
            elif key == 'date':
                mask &= frame[key].eq(pd.Timestamp(value))
            elif key == 'match_num':
                mask &= pd.to_numeric(frame[key], errors='coerce').eq(value)
            else:
                mask &= frame[key].eq(value)
        excluded |= mask
    out = frame.loc[~excluded].copy()
    if self_pair_mask(out).any():
        raise ValueError('unreviewed invalid self-pair in source population')
    return out


def _identity(row):
    return (name_key(canonical_name(row['winner_name'])),
            name_key(canonical_name(row['loser_name'])), str(row['round']), games(row['score']))


def _within_reviewed_event(row, expected, start, end):
    day = pd.Timestamp(row['date'])
    if start <= day <= end:
        return True
    # resolve_dates deliberately retains a uniform archive stamp one day before
    # the official calendar. It is event ordering, never an actual played day.
    return (day == start - pd.Timedelta(days=1) and row.get('date_basis') == 'event_start'
            and pd.Timestamp(row.get('recorded_date')) == day
            and pd.Timestamp(row.get('event_start')) == start
            and pd.Timestamp(row.get('event_end')) == end
            and isinstance(row.get('date_evidence'), str) and bool(row['date_evidence'])
            and str(row.get('espn_id')) == expected['espn_id'])


def coverage_receipt(frame, tour, *, ledger=None):
    """Compare actual survivors to independently enumerated expected result identities.

    A source-survivor tag is not proof. Require pair, winner, round, games, event span
    and main role; an available ESPN event ID must agree. Multiple matches stay errors.
    """
    ledger = load_ledger(tour) if ledger is None else ledger
    candidates = {}
    if ledger['records'] and not frame.empty:
        scope_years = {int(r['wta']['event']['year']) for r in ledger['records']}
        dates = pd.to_datetime(frame.date, errors='coerce')
        subset = frame.loc[dates.dt.year.isin(scope_years)]
        for row in subset.to_dict('records'):
            candidates.setdefault(_identity(row), []).append(row)
    missing, ambiguous, conflicting = [], [], []
    verified = 0
    for record in ledger['records']:
        expected = record['row']
        start, end = pd.Timestamp(expected['event_start']), pd.Timestamp(expected['event_end'])
        matches = [r for r in candidates.get(_identity(expected), [])
                   if _within_reviewed_event(r, expected, start, end)]
        compatible = []
        for r in matches:
            eid = r.get('espn_id')
            if (r.get('draw_level') != 'main'
                    or (pd.notna(eid) and str(eid) != expected['espn_id'])
                    or ('RET' in str(r['score']).upper()) != (record['outcome'] == 'retirement')
                    or ('W/O' in str(r['score']).upper()) != (record['outcome'] == 'walkover')):
                continue
            compatible.append(r)
        if len(matches) > 1:
            ambiguous.append(record['key'])
        elif len(compatible) == 1:
            verified += 1
        elif matches:
            conflicting.append(record['key'])
        else:
            missing.append(record['key'])
    return {'schema': RECEIPT_SCHEMA, 'tour': tour,
            'populationVersion': config.MATCH_POPULATION_VERSION,
            'ledgerSHA256': config.REVIEWED_RESULTS[tour]['sha256'],
            'checkedMatches': len(frame), 'selfPairs': int(self_pair_mask(frame).sum()),
            'expectedResults': len(ledger['records']), 'verifiedResults': verified,
            'missingKeys': missing, 'conflictingKeys': conflicting, 'ambiguousKeys': ambiguous,
            'reviewedQuarantines': len(ledger['quarantines']),
            'coverageScope': ledger['coverage'], 'otherCoverage': 'unknown'}


def validate_receipt(receipt, tour, matches):
    """Pure stable failure classes, also used by the typed output gate."""
    if not isinstance(receipt, dict):
        return ['contract_invalid']
    expected = config.REVIEWED_RESULTS[tour]
    errors = []
    if not (receipt.get('schema') == RECEIPT_SCHEMA and receipt.get('tour') == tour
            and receipt.get('populationVersion') == config.MATCH_POPULATION_VERSION
            and receipt.get('ledgerSHA256') == expected['sha256']
            and type(receipt.get('checkedMatches')) is int and receipt['checkedMatches'] == matches
            and type(receipt.get('expectedResults')) is int and receipt['expectedResults'] == expected['records']
            and type(receipt.get('reviewedQuarantines')) is int and receipt['reviewedQuarantines'] == expected['quarantines']
            and receipt.get('otherCoverage') == 'unknown'):
        errors.append('contract_invalid')
    if type(receipt.get('selfPairs')) is not int or receipt['selfPairs'] != 0:
        errors.append('invalid_self_pair')
    if (type(receipt.get('verifiedResults')) is not int
            or receipt['verifiedResults'] != expected['records']
            or any(receipt.get(k) != [] for k in ('missingKeys','conflictingKeys','ambiguousKeys'))):
        errors.append('expected_results_missing')
    return errors


def require_result_integrity(frame, tour):
    receipt = coverage_receipt(frame, tour)
    failures = validate_receipt(receipt, tour, len(frame))
    if failures:
        detail = {k:(v[:3] if isinstance(v, list) else v) for k,v in receipt.items()}
        raise ValueError(f'Result integrity failed: {failures}; {detail}')
    return receipt
