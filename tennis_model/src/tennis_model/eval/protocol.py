"""Predeclared research diagnostics; the standing adoption inequality is unchanged."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import TUNE_YEARS, VAL_START
from ..data.names import name_key
from ..model.features import ANTISYM, FEATURES
from ..model.probability import calibrated_probability, reverse_features

PROTOCOL_VERSION = 'paired-temporal-foundation-v1'
BLOCK_SEED = 20260906
BLOCK_REPLICATES = 2000
SLICE_MIN_MAIN_MATCHES = 32
SLICE_INACTIVITY_DAYS = 120
PAIR_COLUMNS = ('date','winner_name','loser_name','round_order')
OPTIONAL_PAIR_COLUMNS = ('tour','tourney_id','round','match_num','source_match_id','draw_level')


def require_paired(base, candidate):
    columns = list(PAIR_COLUMNS) + [c for c in OPTIONAL_PAIR_COLUMNS if c in base or c in candidate]
    if any(c not in base or c not in candidate for c in columns):
        raise ValueError('paired evaluation requires identical match identity columns')
    left, right = base[columns].reset_index(drop=True), candidate[columns].reset_index(drop=True)
    if left.duplicated().any() or right.duplicated().any():
        raise ValueError('paired match identity is not unique')
    if not left.equals(right):
        raise ValueError('paired match identities/order differ')
    return columns


def legacy_orientation_diagnostics(clf, calibrator, frame):
    """Choose the canonical player slot before calling the model; convert labels afterward."""
    a, b = frame.winner_name.map(name_key), frame.loser_name.map(name_key)
    if a.eq(b).any() or a.eq('').any() or b.eq('').any():
        raise ValueError('canonical player identities are missing or collide')
    swap = a.gt(b).to_numpy()
    canonical = frame[FEATURES].copy()
    canonical.loc[swap, ANTISYM] = -canonical.loc[swap, ANTISYM]
    cp = calibrated_probability(clf, calibrator, canonical)
    forward = calibrated_probability(clf, calibrator, frame[FEATURES])
    reverse = calibrated_probability(clf, calibrator, reverse_features(frame[FEATURES]))
    return {
        'p_legacy_canonical': np.where(swap, 1 - cp, cp),
        'p_legacy_winnerfirst': forward,
        'legacy_two_direction_loss': -.5 * (np.log(np.clip(forward, 1e-12, 1-1e-12))
                                           + np.log(np.clip(1-reverse, 1e-12, 1-1e-12))),
    }


def block_uncertainty(delta, blocks, *, seed=BLOCK_SEED, replicates=BLOCK_REPLICATES):
    """Resample complete blocks, retaining match weighting despite varying block size."""
    d = np.asarray(delta, dtype=float)
    if not len(d) or not np.isfinite(d).all() or len(blocks) != len(d):
        raise ValueError('invalid block uncertainty inputs')
    labels = pd.Series(list(blocks), dtype=object)
    if labels.isna().any():
        return {'n':len(d), 'blocks':None, 'status':'missing-block-identity'}
    codes, names = pd.factorize(labels)
    groups = len(names)
    if groups < 2:
        return {'n':len(d), 'blocks':groups, 'status':'insufficient-blocks'}
    sums = np.bincount(codes, weights=d)
    counts = np.bincount(codes)
    rng = np.random.default_rng(seed)
    means = np.empty(replicates)
    for i in range(replicates):
        chosen = rng.integers(groups, size=groups)
        means[i] = sums[chosen].sum() / counts[chosen].sum()
    return {'n':len(d), 'blocks':groups, 'status':'ok', 'mean':float(d.mean()),
            'bootstrapSE':float(means.std(ddof=1)), 'percentile95':np.quantile(means,[.025,.975]).tolist(),
            'seed':seed, 'replicates':replicates}


def paired_report(base, candidate):
    columns = require_paired(base, candidate)
    bp, cp = (f.p_combiner.to_numpy(dtype=float) for f in (base,candidate))
    if not np.isfinite([bp,cp]).all() or np.any((bp<0)|(bp>1)|(cp<0)|(cp>1)):
        raise ValueError('invalid paired forecast probabilities')
    d = np.log(np.clip(cp,1e-12,1-1e-12)) - np.log(np.clip(bp,1e-12,1-1e-12))
    years = pd.to_datetime(base.date).dt.year.to_numpy()
    windows = {'tune':(years>=TUNE_YEARS[0])&(years<=TUNE_YEARS[1]), 'validation':years>=VAL_START,
               'full':np.ones(len(d),bool)}
    windows.update({f'year-{y}':years==y for y in sorted(set(years))})
    weeks = pd.to_datetime(base.date).dt.to_period('W-SUN').astype(str).to_numpy()
    event_column = 'event_edition' if 'event_edition' in base else 'tourney_id'
    events = (base[event_column].astype('string').to_numpy() if event_column in base else None)
    out = {'protocol':PROTOCOL_VERSION, 'pairColumns':columns, 'windows':{},
           'limitations':['Event IDs are source event identities; date provenance needs the timing audit.',
                         'Week/event blocks do not remove all repeated-player dependence.']}
    for name, mask in windows.items():
        dd = d[mask]
        if not len(dd):
            out['windows'][name] = {'n':0}
            continue
        out['windows'][name] = {'n':len(dd),'deltaLogloss':float(dd.mean()),
            'naiveSE':float(dd.std(ddof=1)/np.sqrt(len(dd))) if len(dd)>1 else None,
            'week':block_uncertainty(dd,weeks[mask]),
            'event':block_uncertainty(dd,events[mask]) if events is not None else {'status':'missing-block-identity'}}
    masks = {}
    out['unavailableSlices'] = []
    for column, values in (('tour', ('atp', 'wta')),
                           ('source_kind', ('historical', 'stats', 'fresh', 'live', 'lower')),
                           ('date_basis', ('played_date', 'event_start', 'unknown'))):
        if column not in base:
            out['unavailableSlices'].append(column)
        else:
            for value in values:
                masks[f'{column}:{value}'] = base[column].eq(value).to_numpy()
    for s in ('hard','clay','grass'):
        if f'surf_{s}' in base:
            masks[s] = base[f'surf_{s}'].eq(1).to_numpy()
    if {'winner_state_matches','loser_state_matches'} <= set(base):
        masks['low-main-experience'] = base[['winner_state_matches','loser_state_matches']].min(axis=1).lt(SLICE_MIN_MAIN_MATCHES).to_numpy()
    if 'uses_lower_state' in candidate:
        masks['selected-wta-lower'] = candidate.uses_lower_state.to_numpy(dtype=bool)
    if {'winner_rank','loser_rank'} <= set(base):
        ranks = base[['winner_rank','loser_rank']]
        masks['both-top-50'] = ranks.le(50).all(axis=1).to_numpy()
        masks['outside-top-50'] = ranks.gt(50).any(axis=1).to_numpy()
    if 'max_days_since' in base:
        masks['inactive-120d'] = base.max_days_since.gt(SLICE_INACTIVITY_DAYS).to_numpy()
    if 'log_min_srv_pts' in base:
        masks['no-prior-serve-evidence'] = base.log_min_srv_pts.eq(0).to_numpy()
    out['slices'] = {name:{'n':int(mask.sum()), 'deltaLogloss':float(d[mask].mean()) if mask.any() else None}
                     for name,mask in masks.items()}
    tune, val = out['windows']['tune'], out['windows']['validation']
    out['gatePass'] = bool(tune.get('deltaLogloss',0)>0 and val.get('naiveSE') is not None
                           and val['deltaLogloss'] > -val['naiveSE'])
    out['positiveValidationDelta'] = bool(val.get('deltaLogloss',0)>0)
    return out


def write_experiment_manifest(path, *, hypothesis, parent_sha, inputs_sha256, evaluator_sha256,
                              data_through, settings, trial_budget, started_at, oos_paths,
                              status='registered', results=None, interventions=(), costs=None,
                              versions=None, match_keys=(), exclusions=None, ended_at=None,
                              verdict=None, rationale=None):
    """Create a new record without overwriting an existing registration or historical ledger."""
    record = {'schema':PROTOCOL_VERSION, 'hypothesis':hypothesis, 'parentSHA':parent_sha,
              'inputsSHA256':inputs_sha256, 'evaluatorSHA256':evaluator_sha256,
              'dataThrough':data_through, 'settings':settings, 'trialBudget':trial_budget,
              'startedAt':started_at, 'oosPaths':list(oos_paths), 'status':status,
              'results':results, 'manualInterventions':list(interventions), 'costs':costs,
              'versions':versions, 'matchKeys':list(match_keys), 'exclusions':exclusions,
              'endedAt':ended_at, 'verdict':verdict, 'rationale':rationale,
              'tuneYears':list(TUNE_YEARS), 'validationStart':VAL_START,
              'blockSeed':BLOCK_SEED, 'blockReplicates':BLOCK_REPLICATES}
    encoded = json.dumps(record, sort_keys=True, indent=2, allow_nan=False)+'\n'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        f.write(encoded)
    return hashlib.sha256(encoded.encode()).hexdigest()
