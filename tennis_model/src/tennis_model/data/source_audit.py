"""Compare the provider witness with public artifacts without calling ingestion parsers."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from ..config import PLAYER_ALIASES
from .health_checks.common import _add_finding
from .names import name_key
from .participants import is_real_participant

SCHEMA = 'tournament-source-audit-v1'
MAX_AGE_HOURS = 6


def capture_source(tour: str, events: list, observed_at: str) -> tuple[bytes, dict]:
    raw = json.dumps({'schema': SCHEMA, 'tour': tour, 'observedAt': observed_at,
                      'events': events}, ensure_ascii=False, allow_nan=False).encode()
    return raw, {'sha256': hashlib.sha256(raw).hexdigest(), 'observedAt': observed_at}


def read_source(directory: Path, tour: str) -> dict:
    try:
        raw = (directory / 'source_audit.json').read_bytes()
        witness = json.loads(raw)
        receipt = json.loads((directory / 'espn_acquisition.json').read_text())
        proof = receipt['sourceAudit']
        if (witness['schema'] != SCHEMA or witness['tour'] != tour
                or receipt['tour'] != tour
                or proof['sha256'] != hashlib.sha256(raw).hexdigest()
                or proof['observedAt'] != witness['observedAt']
                or receipt['completedAt'] != witness['observedAt']
                or not isinstance(witness['events'], list)
                or receipt['eventCount'] != len(witness['events'])):
            raise ValueError('source witness does not match this acquisition')
        return {'state': 'valid', 'witness': witness, 'proof': proof}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'state': 'invalid', 'reason': type(exc).__name__}


def _key(name):
    key = name_key(name) if isinstance(name, str) else ''
    return name_key(PLAYER_ALIASES.get(key, name)) if key else ''


def _pair(a, b):
    return tuple(sorted((_key(a), _key(b))))


def _games(score):
    return [p for p in re.findall(r'\d+-\d+', re.sub(r'\(\d+\)', '', str(score or '')))
            if p != '0-0']


def _utc(value):
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError('missing timestamp')
    return stamp.tz_localize('UTC') if stamp.tzinfo is None else stamp.tz_convert('UTC')


def check_source(out, tour, source, data, draw_cache, now):
    def fail(code, eid='source', **evidence):
        entity = f'espn:{eid}'
        if evidence.get('players'):
            entity += '#' + str(evidence.get('round', '')) + ':' + '|'.join(sorted(_key(n) for n in evidence['players']))
        elif evidence.get('player'):
            entity += '#player:' + _key(evidence['player'])
        elif evidence.get('slot'):
            entity += '#slot:' + str(evidence['slot'])
        _add_finding(out, 'output.source_audit.' + code,
                     f'{tour}: source tournament audit {code.replace("_", " ")} ({eid})',
                     severity='error', entity=entity, evidence=evidence)

    if not isinstance(source, dict) or source.get('state') != 'valid':
        fail('witness_invalid')
        return
    if not isinstance(data.get('meta'), dict) or any(
            not isinstance(data.get(key, []), list) for key in ('tournaments', 'brackets', 'upcoming')):
        fail('candidate_malformed')
        return
    witness = source.get('witness')
    if (data.get('meta') or {}).get('tournamentSourceAudit') != source.get('proof') or not source.get('proof'):
        fail('generation_mismatch')
        return
    try:
        age = (_utc(now) - _utc(witness['observedAt'])).total_seconds() / 3600
        if (witness['schema'] != SCHEMA or witness['tour'] != tour
                or not isinstance(witness['events'], list) or not -0.1 <= age <= MAX_AGE_HOURS):
            raise ValueError('incompatible or stale witness')
    except (KeyError, ValueError, TypeError, OverflowError):
        fail('witness_invalid')
        return
    inventory = (data.get('meta') or {}).get('modelPlayerNames')
    if not isinstance(inventory, list) or not inventory or not all(isinstance(n, str) for n in inventory):
        fail('inventory_missing')
        return
    rated = {name_key(n) for n in inventory}
    tokens = defaultdict(list)
    for n in inventory:
        tokens[tuple(sorted(name_key(n).split()))].append(n)
    reviewed = set()

    def identity(n, eid, role):
        k = _key(n)
        candidates = tokens.get(tuple(sorted(k.split())), [])
        if is_real_participant(n) and k not in rated and candidates and (eid, k) not in reviewed:
            reviewed.add((eid, k))
            fail('player_identity_unresolved', eid, player=n, candidates=candidates, role=role)

    cards = {str(e.get('espnId')): e for e in data.get('tournaments', []) if isinstance(e, dict)}
    brackets = {str(e.get('espnId')): e for e in data.get('brackets', []) if isinstance(e, dict)}
    upcoming = defaultdict(list)
    for m in data.get('upcoming', []):
        upcoming[str(m.get('espnId'))].append(m)
    source_ids = {str(e.get('id')) for e in witness['events'] if isinstance(e, dict)}
    for eid, card in cards.items():
        if card.get('espnId') and card.get('status') in ('live', 'upcoming') and eid not in source_ids:
            fail('event_unwitnessed', eid)
    slug = 'mens-singles' if tour == 'atp' else 'womens-singles'
    for ev in witness['events']:
        if not isinstance(ev, dict) or not ev.get('id'):
            fail('witness_invalid')
            continue
        eid = str(ev['id'])
        bracket = brackets.get(eid)
        card = cards.get(eid)
        active = (card or {}).get('status') in ('live', 'upcoming')
        try:
            active |= _utc(ev.get('date')).date() <= _utc(now).date() <= _utc(ev.get('endDate')).date()
        except (TypeError, ValueError):
            pass
        if not active:
            continue
        try:
            _check_event(ev, eid, card, bracket, upcoming[eid], (draw_cache or {}).get(eid, {}),
                         slug, rated, identity, fail)
        except (AttributeError, TypeError, KeyError, ValueError, OverflowError, IndexError):
            fail('event_malformed', eid)


def _check_event(ev, eid, card, bracket, schedule, cached, slug, rated, identity, fail):
    comps = [c for g in ev.get('groupings', []) if g.get('grouping', {}).get('slug') == slug
             for c in g.get('competitions', [])]
    main, qual = [], []
    for c in comps:
        rnd = c.get('round') or {}
        qualifying = ('qual' in str(rnd.get('displayName', '')).lower()
                      or str(rnd.get('id')) in ('11', '12', '13', '14'))
        (qual if qualifying else main).append(c)
    qual_losers = {_key(a.get('athlete', {}).get('displayName')) for c in qual
                   if c.get('status', {}).get('type', {}).get('completed')
                   for a in c.get('competitors', []) if a.get('winner') is False}
    for c in qual:
        for a in c.get('competitors', []):
            n = a.get('athlete', {}).get('displayName')
            if _key(n) not in qual_losers:
                identity(n, eid, 'qualifying')
    field = {a.get('athlete', {}).get('displayName') for c in main for a in c.get('competitors', [])
             if is_real_participant(a.get('athlete', {}).get('displayName'))}
    for n in field:
        identity(n, eid, 'main-draw')
    for n in cached.get('slots', []):
        identity(n, eid, 'cached-draw')
    if not field:
        return
    if not card:
        fail('event_missing', eid, name=ev.get('name') or ev.get('shortName'))
        return
    bm = defaultdict(list)
    if bracket:
        ordered = [m.get(s) for m in bracket['rounds'][0]['matches'] for s in ('a', 'b')]
        seats = [n for n in ordered if is_real_participant(n)]
        field_keys = {_key(n) for n in field}
        # Exact identities only. A withdrawn cached entrant or clipped official spelling
        # cannot disprove a replacement/name expansion corroborated by current pairings.
        for position, original in enumerate(cached.get('slots', [])):
            if position >= len(ordered):
                fail('draw_slot_mismatch', eid, slot=position + 1)
                break
            if (original is None and ordered[position] is not None) or (
                    is_real_participant(original) and _key(original) in field_keys
                    and _key(original) != _key(ordered[position])):
                fail('draw_slot_mismatch', eid, slot=position + 1,
                     expected=original, actual=ordered[position])
        counts = Counter(_key(n) for n in seats)
        for key, count in counts.items():
            if count > 1:
                fail('duplicate_entrant', eid, player=key, count=count)
        for n in seats:
            identity(n, eid, 'public-draw')
        for n in field:
            if _key(n) not in counts:
                fail('entrant_missing', eid, player=n)
        for rnd in bracket['rounds']:
            for m in rnd['matches']:
                if is_real_participant(m.get('a')) and is_real_participant(m.get('b')):
                    bm[(rnd['round'], _pair(m['a'], m['b']))].append(m)
    sm = defaultdict(list)
    for m in schedule:
        sm[(m.get('round'), _pair(m.get('playerA'), m.get('playerB')))].append(m)
    for key, rows in sm.items():
        if len(rows) > 1:
            fail('duplicate_match', eid, round=key[0], players=list(key[1]))
    counts = Counter(str(c.get('round', {}).get('id')) for c in main)
    size = max([2 * n * 2 ** (int(r) - 1) for r, n in counts.items()
                if r in ('1', '2', '3', '4')], default=0)
    size = 1 << (size - 1).bit_length() if size else 0
    size = (bracket or {}).get('bracketSize') or size
    pending, completed = set(), set()
    for c in main:
        athletes = c.get('competitors') or []
        if len(athletes) != 2:
            continue
        names = [a.get('athlete', {}).get('displayName') for a in athletes]
        if not all(is_real_participant(n) for n in names):
            continue
        rid = str(c.get('round', {}).get('id'))
        if rid in ('1', '2', '3', '4') and size:
            stage = size >> (int(rid) - 1)
            rnd = {8: 'QF', 4: 'SF', 2: 'F'}.get(stage, f'R{stage}')
        else:
            rnd = {'5': 'QF', '6': 'SF', '7': 'F'}.get(rid)
        if rnd is None:
            fail('round_unresolved', eid, matchId=c.get('id'))
            continue
        pair = _pair(*names)
        if len(set(pair)) != 2:
            fail('self_match', eid, players=names)
            continue
        key = (rnd, pair)
        status = c.get('status', {}).get('type', {})
        if status.get('state') not in ('pre', 'in', 'post') or not isinstance(status.get('completed'), bool):
            fail('event_malformed', eid, matchId=c.get('id'))
            continue
        matches = bm.get(key, [])
        if status.get('completed'):
            completed.add(key)
            winners = [a for a in athletes if a.get('winner') is True]
            if len(winners) != 1:
                fail('winner_unresolved', eid, players=names)
                continue
            winner = winners[0]
            if bracket and len(matches) != 1:
                fail('result_missing', eid, round=rnd, players=names)
                continue
            if not matches:
                continue  # coverage-only card has no bracket to compare
            m = matches[0]
            if m.get('winner') not in ('a', 'b') or _key(m.get(m.get('winner'))) != _key(winner['athlete']['displayName']):
                fail('winner_mismatch', eid, round=rnd, players=names)
            loser = next(a for a in athletes if a is not winner)
            games = [f"{int(w['value'])}-{int(l['value'])}" for w, l in
                     zip(winner.get('linescores') or [], loser.get('linescores') or [])]
            expected = ' '.join(games)
            if games and _games(m.get('score')) != _games(expected):
                fail('score_mismatch', eid, players=names, expected=expected, actual=m.get('score'))
            marker = {'STATUS_WALKOVER': 'W/O', 'STATUS_RETIRED': 'RET'}.get(status.get('name'))
            if marker and marker not in str(m.get('score') or '').upper():
                fail('outcome_mismatch', eid, players=names, expected=marker, actual=m.get('score'))
        elif status.get('state') in ('pre', 'in'):
            pending.add(key)
            if bracket and (len(matches) != 1 or matches[0].get('winner') is not None):
                fail('scheduled_pair_mismatch', eid, round=rnd, players=names)
            # A genuine newcomer may be factual but unpriced; rated variants block above.
            if all(_key(n) in rated for n in names) and len(sm.get(key, [])) != 1:
                fail('scheduled_match_missing', eid, round=rnd, players=names)
    for key in completed & sm.keys():
        fail('completed_match_scheduled', eid, round=key[0], players=list(key[1]))
    # Extra projected pairs are legitimate before the feed names their opponents.
    for key in sm.keys() - pending - completed:
        participants = {n for r, pair in pending | completed if r == key[0] for n in pair}
        if set(key[1]) & participants:
            fail('opponent_mismatch', eid, round=key[0], players=list(key[1]))
