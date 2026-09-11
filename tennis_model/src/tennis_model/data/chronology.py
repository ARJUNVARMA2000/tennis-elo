"""Auditable retrospective dates: verified played days, event bounds, or explicit unknowns.

Event-start dates support only the archive's event/round ordering, not a claim of exact
played time. Historical publication times are not reconstructed from today's files.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .. import config
from .names import name_key

CHRONOLOGY_POLICY = 'retrospective-verified-date-or-recorded-event-round-v2'
TIMING_COLUMNS = ('played_date', 'event_start', 'event_end', 'date_evidence')


def _key(value):
    return name_key(config.PLAYER_ALIASES.get(name_key(value), value))


def _games(value):
    return ','.join(x for x in re.findall(r'\d+-\d+', re.sub(r'\(\d+\)', '', str(value))) if x != '0-0')


def _cache_fingerprint(root):
    h = hashlib.sha256()
    for p in sorted(root.glob('*/*.json')):
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()


@lru_cache(maxsize=2)
def _wta_evidence(root_text, fingerprint):
    """Only explicit exact-ID records with unique metadata and bounded played dates."""
    root = Path(root_text)
    from .wta_results import estimated_start, numeric_id, same_edition
    candidates = {}
    for p in sorted(root.glob('*/*.json')):
        value = json.loads(p.read_text())
        if not isinstance(value, dict) or not value.get('matches'):
            continue
        t = value.get('tournament', {})
        group, year = t.get('tournamentGroup', {}), t.get('year')
        if not group.get('id') or not isinstance(year, int):
            continue
        start = pd.to_datetime(t.get('startDate'), errors='coerce')
        end = pd.to_datetime(t.get('endDate'), errors='coerce')
        if pd.isna(start) or pd.isna(end) or not 0 <= (end-start).days <= 35:
            continue
        for m in value['matches']:
            if not same_edition({'id':group['id'], 'year':year}, m, require_record=False):
                continue
            if m.get('DrawMatchType') != 'S' or m.get('MatchState') != 'F' or str(m.get('Winner')) not in ('2', '3'):
                continue
            a_won = str(m['Winner']) == '2'
            w, l = ('A', 'B') if a_won else ('B', 'A')
            names = tuple(_key(f"{m.get('PlayerNameFirst'+x, '')} {m.get('PlayerNameLast'+x, '')}") for x in (w, l))
            if not all(names) or names[0] == names[1] or not m.get('MatchID'):
                continue
            played = pd.to_datetime(str(m.get('MatchTimeStamp') or '')[:10], errors='coerce')
            known = not estimated_start(m) and pd.notna(played) and start <= played <= end
            sets = []
            for i in range(1, 6):
                x, y = m.get(f'ScoreSet{i}{w}'), m.get(f'ScoreSet{i}{l}')
                if x is None or y is None or str(x) == '' or str(y) == '':
                    break
                sets.append(f'{x}-{y}')
            score = _games(' '.join(sets))
            if not score:
                continue
            key = (f"{year}-W{numeric_id(group['id'])}", str(m['MatchID']), *names, score)
            record = (str(played.date()) if known else None, str(start.date()), str(end.date()))
            candidates.setdefault(key, set()).add(record)
    if _cache_fingerprint(root) != fingerprint:
        raise ValueError('WTA timing evidence changed during read')
    result = {}
    for key, records in candidates.items():
        bounds = {r[1:] for r in records}
        if len(bounds) != 1:
            continue
        days = {r[0] for r in records}
        day = next(iter(days)) if len(days) == 1 else None
        result[key] = (day, *next(iter(bounds)), f'wta-httpcache:{fingerprint}')
    return result


def annotate_sources(frame, tour):
    """Attach evidence without changing date or dedup membership; called before selection."""
    out = frame.copy()
    out['recorded_date'] = out['date']
    out['recorded_event_id'] = out.tourney_id
    out['date_basis'] = 'unknown'
    for c in TIMING_COLUMNS:
        if c not in out:
            out[c] = pd.NaT if c != 'date_evidence' else None
    for c in ('played_date', 'event_start', 'event_end'):
        out[c] = pd.to_datetime(out[c], errors='coerce')
    # The ESPN adapter already converts the competition timestamp to venue-local date.
    live = out.source_kind.eq('live') & out.espn_id.notna()
    out.loc[live, 'played_date'] = out.loc[live, 'date']
    out.loc[live, 'date_evidence'] = 'espn-competition-local-date'
    if tour == 'wta':
        root = config.stats_dir('wta') / '_httpcache'
        evidence = _wta_evidence(str(root), _cache_fingerprint(root))
        mids = out.get('source_match_id', pd.Series('', index=out.index)).fillna('').astype(str)
        keys = zip(out.tourney_id.astype(str), mids, out.winner_name.map(_key),
                   out.loser_name.map(_key), out.score.map(_games))
        rows = [evidence.get(key) for key in keys]
        matched = pd.Series([row is not None for row in rows], index=out.index)
        for i, c in enumerate(TIMING_COLUMNS):
            values = pd.Series([row[i] if row else None for row in rows], index=out.index)
            if c != 'date_evidence':
                values = pd.to_datetime(values, errors='coerce')
            out[c] = values.combine_first(out[c])
            # Explicit estimated or conflicting timing retracts an old cache's claim.
            if c == 'played_date':
                out.loc[matched, c] = values.loc[matched]
    return out


def carry_timing_evidence(frame, match_keys):
    """Unique exact-result-group timing survives payload preference; conflicts stay unknown."""
    out = frame.copy()
    known = out.date_evidence.notna() & (
        out.played_date.notna() | (out.event_start.notna() & out.event_end.notna()))
    donors = out.loc[known].copy()
    if donors.empty:
        return out
    donors['_key'] = match_keys.loc[donors.index]
    counts = donors.groupby('_key').played_date.nunique()
    bounds = donors.groupby('_key')[['event_start', 'event_end']].nunique()
    conflict_keys = counts[counts.gt(1)].index.union(bounds.index[bounds.gt(1).any(axis=1)])
    # Prefer a real played day, but preserve event-bound-only evidence too.
    donors = donors[~donors['_key'].isin(conflict_keys)]
    donors = donors.sort_values('played_date', na_position='last').drop_duplicates('_key')
    if not donors.empty:
        for c in TIMING_COLUMNS:
            mapping = donors.set_index('_key')[c]
            out[c] = match_keys.map(mapping).combine_first(out[c])
    # Conflicting known played days must not survive just because one payload won.
    conflict = match_keys.isin(conflict_keys)
    out.loc[conflict, ['played_date', 'event_start', 'event_end']] = pd.NaT
    out.loc[conflict, 'date_evidence'] = None
    return out


def resolve_dates(frame, tour):
    """Apply reviewed repairs after dedup; preserve every selected match and original value."""
    out = frame.copy()
    out['date_correction'] = None
    if tour == 'atp':
        for eid, (start, end, alternate) in config.ATP_EVENT_START_REPAIRS.items():
            mask = out.tourney_id.eq(eid) & out.recorded_date.isin(pd.to_datetime([start, alternate])) & out.played_date.isna()
            out.loc[mask, 'date'] = pd.Timestamp(start)
            out.loc[mask, 'event_start'] = pd.Timestamp(start)
            out.loc[mask, 'event_end'] = pd.Timestamp(end)
            out.loc[mask, 'date_basis'] = 'event_start'
            out.loc[mask, 'date_evidence'] = f'reviewed-atp-event:{eid}'
            out.loc[mask & out.recorded_date.ne(pd.Timestamp(start)), 'date_correction'] = 'conflicting-event-start'
        for bad, day, winner, loser, score, correct in config.ATP_MATCH_EVENT_REPAIRS:
            mask = (out.tourney_id.eq(bad) & out.recorded_date.eq(pd.Timestamp(day))
                    & out.winner_name.map(_key).eq(winner) & out.loser_name.map(_key).eq(loser)
                    & out.score.map(_games).eq(score))
            out.loc[mask, 'tourney_id'] = correct
            out.loc[mask, 'date_correction'] = 'exact-result-event-id'
            out.loc[mask, 'played_date'] = pd.Timestamp(day)
            out.loc[mask, 'date_evidence'] = 'atp:shelton-nava-munich-2026-monday'
    played = out.played_date.notna() & out.date_evidence.notna()
    out.loc[played, 'date'] = out.loc[played, 'played_date']
    out.loc[played, 'date_basis'] = 'played_date'
    if tour == 'wta':
        # Partial recovery must not create new mixed-date inversions. A unique exact
        # result donor anchors an edition, provided every selected row is in its span.
        for _, group in out.groupby('tourney_id', sort=False):
            bounds = group[['event_start', 'event_end']].dropna().drop_duplicates()
            if len(bounds) != 1 or group.played_date.notna().all():
                continue
            start, end = bounds.iloc[0]
            anchor = start
            # Some archives use the Monday edition stamp while the verified calendar
            # starts Tuesday (Bol 2016/17). Retain that uniform archive stamp for
            # round ordering only; it is never a played date or availability time.
            uniform_stamp = (group.recorded_date.nunique() == 1
                             and group.recorded_date.notna().all()
                             and group.recorded_date.iloc[0] == start - pd.Timedelta(days=1))
            if uniform_stamp:
                anchor = group.recorded_date.iloc[0]
            elif not group.recorded_date.between(start, end).all():
                continue
            idx = group.index
            changed = idx[out.loc[idx, 'date'].ne(anchor)]
            out.loc[idx, 'date'] = anchor
            out.loc[idx, 'date_basis'] = 'event_start'
            out.loc[idx, 'event_start'] = start
            out.loc[idx, 'event_end'] = end
            out.loc[idx, 'date_evidence'] = group.date_evidence.dropna().iloc[0]
            out.loc[changed, 'date_correction'] = 'mixed-date-bases-event-start'
    bounded = out.event_end.notna() & out.date_evidence.notna()
    out['stats_available_at'] = out.played_date.where(played, out.event_end.where(bounded))
    out['stats_availability_basis'] = np.where(played, 'played_date', np.where(bounded, 'event_end', 'unknown'))
    out['chronology_policy'] = CHRONOLOGY_POLICY
    # Edition identity uses an explicit source year when present, never fuzzy event names.
    year = out.tourney_id.astype('string').str.extract(r'^(\d{4})-', expand=False).fillna(out.date.dt.year.astype(str))
    out['event_edition'] = tour + ':' + year + ':' + out.tourney_id.astype('string')
    return out


def round_date_inversions(frame):
    """Bounded diagnostic; ambiguous identities/dates cannot be certified by this test."""
    if 'event_edition' not in frame or frame.empty:
        return []
    ko = frame[frame['round'].isin(['R128', 'R64', 'R32', 'R16', 'QF', 'SF', 'F'])]
    cols = ['event_edition', 'date', 'round_order', 'winner_name', 'loser_name']
    people = pd.concat([ko[cols].assign(player=ko.winner_name), ko[cols].assign(player=ko.loser_name)])
    keys = ['event_edition', 'player']
    people = people.dropna(subset=keys+['date', 'round_order']).sort_values(keys+['date', 'round_order']).reset_index(drop=True)
    if people.empty:
        return []
    high = people.groupby(keys).round_order.cummax()
    people['peak'] = np.where(people.round_order.eq(high), people.index, np.nan)
    peak = people.groupby(keys).peak.ffill().astype(int)
    previous = people.loc[peak].reset_index(drop=True)
    bad = people.round_order.lt(high) & people.date.gt(previous.date)
    return people.loc[bad, cols+['player']].to_dict('records')


def require_chronology(frame):
    findings = round_date_inversions(frame)
    if findings:
        raise ValueError(f'Unresolved within-edition round/date inversions: {findings[:3]}')
