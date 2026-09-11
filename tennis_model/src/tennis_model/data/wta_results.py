"""WTA result facts independent of optional serving statistics.

This adapter is deliberately stricter than a terminal match-state flag: a retirement
or walkover needs explicit outcome evidence. Unknowns are review leads, never silently
promoted to ordinary completed matches. No current player-profile fields are imported.
"""

from __future__ import annotations

import re

import pandas as pd

from .. import config
from .names import name_key


def canonical_name(value):
    return config.PLAYER_ALIASES.get(name_key(value), str(value).strip())


def numeric_id(value):
    text = str(value or '').strip()
    if not text.isdigit() or int(text) <= 0:
        raise ValueError(f'invalid provider identity: {value!r}')
    return str(int(text))


def same_edition(event, match, *, require_record=True):
    """Numeric IDs tolerate leading zeros, never conflicting years or folder guesses."""
    try:
        eid, year = numeric_id(event['id']), numeric_id(event['year'])
        for field, expected in (('EventID', eid), ('EventYear', year)):
            if match.get(field) in (None, '') and not require_record:
                continue  # old caches sometimes omitted record IDs; header is explicit
            if numeric_id(match.get(field)) != expected:
                return False
        return True
    except (KeyError, ValueError):
        return False


def estimated_start(match):
    return any(str(match.get(k, '')).strip().lower() in ('true', '1')
               for k in ('estimatedStartTime', 'isEstimatedStartTime'))


def timing(event, match):
    """Event bounds are usable even when the timestamp is an estimate."""
    start, end, played = (pd.to_datetime(v, errors='coerce') for v in (
        event.get('start'), event.get('end'), str(match.get('MatchTimeStamp') or '')[:10]))
    if pd.isna(start) or pd.isna(end) or not 0 <= (end - start).days <= 35:
        raise ValueError('invalid event bounds')
    known = not estimated_start(match) and pd.notna(played) and start <= played <= end
    return {'event_start': str(start.date()), 'event_end': str(end.date()),
            **({'played_date': str(played.date())} if known else {}),
            'date_evidence': f"wta-api:{numeric_id(event['year'])}-W{numeric_id(event['id'])}:{match.get('MatchID', '')}"}


def games(score):
    return ','.join(re.findall(r'\d+-\d+', re.sub(r'\(\d+\)', '', str(score))))


def completed_score(score):
    pairs = [tuple(map(int, pair.split('-'))) for pair in games(score).split(',') if pair]
    wins = losses = 0
    if len(pairs) not in (2, 3):
        return False
    for i, (a, b) in enumerate(pairs):
        if (a > b and ((a == 6 and b <= 4) or (a == 7 and b in (5, 6)))):
            wins += 1
        elif (b > a and ((b == 6 and a <= 4) or (b == 7 and a in (5, 6)))):
            losses += 1
        else:
            return False
        if (wins == 2 or losses == 2) and i != len(pairs) - 1:
            return False
    return wins == 2 and losses < 2


def normalize_result(event, match, *, outcome=None, score=None):
    """Return a result-only canonical row; raise with a review reason on invalid facts.

    Explicit outcome/score overrides are for reviewed second-provider evidence. Merely
    fetching a stats response cannot supply one. Caller must preserve that evidence.
    """
    from .wta_stats import _match_round, _normalized_level, _winner_first_score
    if not same_edition(event, match):
        raise ValueError('record/header edition conflict or missing identity')
    level = _normalized_level(event.get('level'))
    if (match.get('DrawMatchType') != 'S' or match.get('DrawLevelType') != 'M'
            or event.get('draw_level') != 'main' or level is None or level[1] != 'main'
            or level[0] not in config.TIER_NAMES):
        raise ValueError('not an explicit main-tour singles result')
    if match.get('MatchState') != 'F' or str(match.get('Winner')) not in ('2', '3'):
        raise ValueError('not a settled winner')
    mid = str(match.get('MatchID') or '').strip()
    if not mid:
        raise ValueError('missing source match identity')
    w, l = ('A', 'B') if str(match['Winner']) == '2' else ('B', 'A')
    names, ids = [], []
    for side in (w, l):
        first, last = match.get('PlayerNameFirst'+side), match.get('PlayerNameLast'+side)
        if not first or not last:
            raise ValueError('missing player identity')
        names.append(canonical_name(f'{first} {last}'))
        ids.append(numeric_id(match.get('PlayerID'+side)))
    if name_key(names[0]) == name_key(names[1]) or ids[0] == ids[1]:
        raise ValueError('invalid self-pair')
    rnd = _match_round(event, match, 'main')
    if rnd not in ('R128', 'R64', 'R32', 'R16', 'QF', 'SF', 'F'):
        raise ValueError('unresolved round')
    score = _winner_first_score(match, w == 'A') if score is None else score
    if outcome is None:
        # Do not use MatchState=F as evidence of completion; the score must prove it.
        outcome = 'completed' if completed_score(score) else 'unresolved'
    if outcome == 'completed':
        if not completed_score(score):
            raise ValueError('incoherent completed score')
    elif outcome == 'retirement':
        if not games(score):
            raise ValueError('retirement needs reviewed score evidence')
        score = re.sub(r'\s*RET\s*$', '', score).strip() + ' RET'
    elif outcome == 'walkover':
        score = 'W/O'
    else:
        raise ValueError('unresolved outcome')
    dates = {'played_date': None, **timing(event, match)}
    return {**dates, 'tourney_id': f"{numeric_id(event['year'])}-W{numeric_id(event['id'])}",
            'tourney_name': event['name'], 'surface': event['surface'],
            'indoor': event.get('indoor'), 'tourney_level': level[0],
            'draw_size': event['draw'], 'draw_level': 'main', 'best_of': 3,
            'tourney_date': (dates['played_date'] or dates['event_start']).replace('-', ''),
            'source_match_id': mid, 'winner_name': names[0], 'loser_name': names[1],
            'winner_id': ids[0], 'loser_id': ids[1], 'round': rnd, 'score': score,
            'result_outcome': outcome}
