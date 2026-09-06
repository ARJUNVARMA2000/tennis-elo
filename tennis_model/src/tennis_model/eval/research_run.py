"""Immutable registrations and frozen-input guards for the corrected baseline runs.

The CLI never downloads, publishes, or tunes. Each tour gets a separate run directory.
A failed/interrupted directory is evidence: retain it and register a new attempt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from ..model.feature_cache import feature_cache_contract
from .protocol import PROTOCOL_VERSION, require_paired, write_experiment_manifest

FREEZE_SCHEMA = 'research-freeze-v1'


def _digest(value):
    # Config tables contain integer keys. Canonicalize their persisted JSON form
    # before sorting, so a save/read cycle cannot change the contract's digest.
    persisted = json.loads(json.dumps(value, allow_nan=False))
    return hashlib.sha256(json.dumps(persisted, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _now():
    return datetime.now(UTC).isoformat()


def _write_new(path, value):
    encoded = json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n'
    with Path(path).open('x') as stream:
        stream.write(encoded)


def current_contract():
    # The raw files have a fixed cutoff. Today's date is operational metadata rather
    # than evaluator identity: advancing the wall clock must not thaw a frozen round.
    contracts = {tour: feature_cache_contract(tour) for tour in ('atp', 'wta')}
    for contract in contracts.values():
        contract.pop('asOfDay')
    first = contracts['atp']
    return {'protocol': PROTOCOL_VERSION, 'inputsSHA256': _digest(first['raw']),
            'evaluatorSHA256': _digest(first['source']),
            'rawInventory': first['raw'], 'sourceInventory': first['source'],
            'tours': {tour: {k:v for k,v in c.items() if k not in ('raw', 'source')}
                      for tour, c in contracts.items()}}


def create_freeze(path, *, data_through):
    if set(data_through) != {'atp', 'wta'}:
        raise ValueError('freeze requires both tour cutoffs')
    for day in data_through.values():
        datetime.strptime(day, '%Y-%m-%d')
    contract = current_contract()
    record = {'schema': FREEZE_SCHEMA, 'createdAt': _now(), 'dataThrough': data_through,
              'contractSHA256': _digest(contract), 'contract': contract}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_new(path, record)
    return record


def verify_freeze(path):
    freeze = json.loads(Path(path).read_text())
    if (freeze.get('schema') != FREEZE_SCHEMA
            or freeze.get('contractSHA256') != _digest(freeze.get('contract'))):
        raise ValueError('invalid research freeze')
    if _digest(current_contract()) != freeze['contractSHA256']:
        raise ValueError('frozen inputs, code, configuration, or runtime changed')
    return freeze


def run_registered(freeze_path, run_dir, *, hypothesis, settings, execute,
                   trial_budget=1):
    """One exclusive attempt; checks before execution and before accepting its result.

    `execute(run_dir, freeze)` returns a JSON-compatible result. A mid-run mutation
    or exception records failure and never produces completion.json. Hard interruption
    leaves registration.json alone, which explicitly means incomplete, not successful.
    """
    if not isinstance(trial_budget, int) or trial_budget < 1:
        raise ValueError('trial budget must be positive')
    freeze = verify_freeze(freeze_path)
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[4]
    parent = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    contract = freeze['contract']
    started = _now()
    write_experiment_manifest(run_dir / 'registration.json', hypothesis=hypothesis,
        parent_sha=parent, inputs_sha256=contract['inputsSHA256'],
        evaluator_sha256=contract['evaluatorSHA256'], data_through=freeze['dataThrough'],
        settings={**settings, 'freezeSHA256':freeze['contractSHA256']}, trial_budget=trial_budget,
        started_at=started, oos_paths=['oos.pkl'], versions=contract['tours'])
    clock = time.monotonic()
    try:
        result = execute(run_dir, freeze)
        verify_freeze(freeze_path)
        _write_new(run_dir / 'completion.json', {'status':'complete', 'endedAt':_now(),
            'wallSeconds':time.monotonic()-clock, 'results':result,
            'freezeSHA256':freeze['contractSHA256']})
        return result
    except BaseException as exc:
        _write_new(run_dir / 'failure.json', {'status':'failed', 'endedAt':_now(),
            'wallSeconds':time.monotonic()-clock, 'errorType':type(exc).__name__,
            'error':str(exc), 'freezeSHA256':freeze['contractSHA256']})
        raise


def baseline(tour, run_dir, freeze):
    """Unchanged adopted five-bag policy, all scoreable folds from 2010 through cutoff."""
    import numpy as np
    import pandas as pd

    from ..config import N_BAG, WTA_DUAL_STATE_GATE_THRESHOLD
    from ..model.features import build_feature_frame, main_rows
    from ..model.train import walk_forward, walk_forward_state_gate, xgb_params_for
    from .ab_data import _build_dual_feature_frames
    from .metrics import score

    if N_BAG != 5:
        raise ValueError('corrected incumbent registration requires five bags')
    cutoff = pd.Timestamp(freeze['dataThrough'][tour])
    args = dict(start_test=2010, end_test=cutoff.year, n_bag=5,
                xgb_overrides=xgb_params_for(tour))
    if tour == 'wta':
        base, enriched = _build_dual_feature_frames(tour)
        threshold = WTA_DUAL_STATE_GATE_THRESHOLD
        if threshold != 32:
            raise ValueError('corrected WTA incumbent requires threshold 32')
        frames = (base, enriched)
    else:
        base = main_rows(build_feature_frame(tour=tour))
        frames = (base,)
    if any(frame.date.max() > cutoff for frame in frames):
        raise ValueError('feature population exceeds the registered data cutoff')
    if tour == 'wta':
        arms = walk_forward_state_gate(base, enriched, (None, threshold), **args)
        oos = arms[threshold]
        require_paired(arms[None], oos)
        protected = ~oos.uses_lower_state.astype(bool)
        if not np.array_equal(arms[None].loc[protected, 'p_combiner'], oos.loc[protected, 'p_combiner']):
            raise ValueError('WTA protected main-state probabilities changed')
        arms[None].to_pickle(run_dir / 'wta-main-reference.pkl')
    else:
        oos = walk_forward(base, **args)
    keys = require_paired(oos, oos)
    oos.to_pickle(run_dir / 'oos.pkl')
    year_counts = oos.date.dt.year.value_counts().sort_index().to_dict()
    expected = base[base.completed & base.date.dt.year.ge(2010) & base.date.le(cutoff)]
    return {'tour':tour, 'n':len(oos), 'metrics':score(oos.p_combiner.to_numpy()),
            'scoredByYear':{str(k):int(v) for k,v in year_counts.items()},
            'eligibleMainCompleted':len(expected), 'unscoredEligible':len(expected)-len(oos),
            'pairColumns':keys, 'scoredKeysSHA256':hashlib.sha256(oos[keys].to_csv(index=False).encode()).hexdigest(),
            'oosSHA256':hashlib.sha256((run_dir / 'oos.pkl').read_bytes()).hexdigest(),
            'sourceCounts':{str(k):int(v) for k,v in oos.source_kind.value_counts().items()},
            'dateBasisCounts':{str(k):int(v) for k,v in oos.date_basis.value_counts().items()},
            'limitations':['Retrospective event/round dates include unknown played times.',
                           'Historical publication availability is not reconstructed.',
                           'This establishes the incumbent; it is not a candidate adoption.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    freeze = commands.add_parser('freeze')
    freeze.add_argument('--path', type=Path, required=True)
    freeze.add_argument('--atp-through', required=True)
    freeze.add_argument('--wta-through', required=True)
    verify = commands.add_parser('verify')
    verify.add_argument('--freeze', type=Path, required=True)
    run = commands.add_parser('baseline')
    run.add_argument('--freeze', type=Path, required=True)
    run.add_argument('--tour', choices=('atp', 'wta'), required=True)
    run.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'freeze':
        result = create_freeze(args.path, data_through={'atp':args.atp_through, 'wta':args.wta_through})
    elif args.command == 'verify':
        result = verify_freeze(args.freeze)
    else:
        result = run_registered(args.freeze, args.run_dir,
            hypothesis=f'Corrected {args.tour.upper()} incumbent; no tuning or adoption claim.',
            settings={'tour':args.tour, 'startTest':2010, 'nBag':5, 'calibrator':'platt',
                      'wtaThreshold':32 if args.tour == 'wta' else None},
            execute=lambda directory, frozen: baseline(args.tour, directory, frozen))
    print(json.dumps({k:v for k,v in result.items() if k != 'contract'}, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
