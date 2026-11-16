"""Research-only 43-column adapter, prepared before the first numerical trial.

The ordinary schema and evaluator remain unchanged. Disabling this adapter delegates
to the incumbent's own orientation, fitting and probability functions exactly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tennis_model.eval.protocol import require_paired
from tennis_model.model.features import ANTISYM, FEATURES, SYMMETRIC
from tennis_model.model.train import (
    BaggedClassifier,
    PlattCalibrator,
    _xgb,
    full_xgb_params,
    xgb_params_for,
)
from tennis_model.ratings.dynamic import DYNAMIC_FEATURE

SCHEMA = 'dynamic-combiner-research-v1'
COLUMNS = [*FEATURES, DYNAMIC_FEATURE]
SIGNED_COLUMNS = [*ANTISYM, DYNAMIC_FEATURE]


def frozen_oriented_xy(frame, seed):
    """The registered 42-column reference, independent of later production schemas."""
    flip = np.random.default_rng(seed).random(len(frame)) < .5
    sign = np.where(flip, -1., 1.)
    x = pd.DataFrame(index=frame.index)
    for column in ANTISYM:
        x[column] = frame[column].to_numpy() * sign
    for column in SYMMETRIC:
        x[column] = frame[column].to_numpy()
    return x[FEATURES], np.where(flip, 0, 1).astype(int)


def checked(frame):
    if (not isinstance(frame, pd.DataFrame) or list(frame.columns) != COLUMNS
            or len(FEATURES) != 42 or len(set(COLUMNS)) != 43):
        raise ValueError('research probability input requires the exact 43-column schema')
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError('non-finite research features')
    return frame


def oriented(frame, seed, *, enabled=True):
    original, y = frozen_oriented_xy(frame[FEATURES], seed=seed)
    if not enabled:
        return original, y
    out = original.copy()
    out[DYNAMIC_FEATURE] = frame[DYNAMIC_FEATURE].to_numpy() * np.where(y == 0, -1.0, 1.0)
    return checked(out), y


def reverse(frame):
    out = checked(frame).copy()
    out.loc[:, SIGNED_COLUMNS] = -out[SIGNED_COLUMNS]
    return out


def probability(clf, calibrator, frame, *, enabled=True):
    if enabled:
        forward = checked(frame)
    else:
        if list(frame.columns) != FEATURES or not np.isfinite(frame.to_numpy(dtype=float)).all():
            raise ValueError('invalid frozen reference schema')
        forward = frame
    if forward.empty:
        return np.empty(0, dtype=np.float64)
    backward = reverse(forward) if enabled else forward.copy()
    if not enabled:
        backward.loc[:, ANTISYM] *= -1
    both = pd.concat([forward, backward], ignore_index=True)
    raw = np.asarray(clf.predict_proba(both), dtype=np.float64)
    if raw.shape != (len(both), 2) or not np.isfinite(raw).all() or np.any((raw < 0) | (raw > 1)):
        raise ValueError('invalid research classifier probabilities')
    p = np.asarray(calibrator.predict(raw[:, 1]), dtype=np.float64)
    if p.shape != (len(both),) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('invalid research calibrated probabilities')
    n = len(forward)
    return 0.5 * (p[:n] + (1.0 - p[n:]))


def fit_fold(core, cal, seed, *, enabled=True, n_bag=5, tour='wta'):
    overrides = xgb_params_for(tour)
    if enabled and n_bag != 5:
        raise ValueError('registered dynamic research requires five bags')
    xcal, ycal = oriented(cal, seed + 1, enabled=enabled)
    clfs = []
    for k in range(n_bag):
        xtr, ytr = oriented(core, seed + 100_000 * k, enabled=enabled)
        clf = _xgb(**full_xgb_params(overrides, bag_index=k))
        clf.fit(xtr, ytr, sample_weight=None, eval_set=[(xcal, ycal)], verbose=False)
        clfs.append(clf)
    model = clfs[0] if n_bag == 1 else BaggedClassifier(clfs)
    calibration = PlattCalibrator().fit(model.predict_proba(xcal)[:, 1], ycal)
    return model, calibration


def walk_forward(base, selected, *, start_test=2010, end_test=2019):
    """Fit only main-state rows; score the unchanged threshold-32 selected state."""
    require_paired(base, selected)
    for frame in (base, selected):
        if not frame.draw_level.eq('main').all() or not frame.tour.eq('wta').all():
            raise ValueError('research combiner requires WTA main rows')
        checked(frame[COLUMNS])
    if not base.completed.equals(selected.completed) or not base.year.equals(selected.year):
        raise ValueError('research fitting/scoring populations differ')
    base = base[base.completed].reset_index(drop=True)
    selected = selected[selected.completed].reset_index(drop=True)
    chunks, folds = [], []
    for year in range(start_test, end_test + 1):
        train = base[base.year.between(1991, year-1)]
        test = selected[selected.year.eq(year)]
        if len(test) == 0 or len(train) < 5000:
            continue
        core, cal = train[train.year.lt(year-1)], train[train.year.eq(year-1)]
        reused = len(cal) < 500 or len(core) < 2000
        if reused:
            core, cal = train, train
        clf, calibration = fit_fold(core, cal, year)
        p = probability(clf, calibration, test[COLUMNS])
        chunks.append(test.assign(p_combiner=p, p_raw=clf.predict_proba(test[COLUMNS])[:, 1],
                                  probability_policy='calibrated-pair-average-v1'))
        folds.append({'year': year, 'train': len(train), 'core': len(core),
                      'calibration': len(cal), 'test': len(test), 'warmupReuse': reused,
                      'bagBestIterations': [int(c.best_iteration) for c in clf.clfs]})
    if not chunks:
        raise ValueError('no scoreable research folds')
    return pd.concat(chunks, ignore_index=True), folds
