"""Explicit research schema using the incumbent's folds, bags and calibration."""

import numpy as np
import pandas as pd
from historical_signals import SIGNALS
from tennis_model.eval.protocol import require_paired
from tennis_model.model.features import ANTISYM, FEATURES, make_oriented_xy, select_dual_state_features
from tennis_model.model.probability import paired_probability
from tennis_model.model.train import (
    BaggedClassifier,
    PlattCalibrator,
    _fit_fold,
    _xgb,
    full_xgb_params,
    xgb_params_for,
)


def columns(extra=()):
    if len(extra) > 1 or any(c not in SIGNALS for c in extra):
        raise ValueError("research schema permits one registered signal at a time")
    return [*FEATURES, *extra]


def checked(frame, extra=()):
    if list(frame.columns) != columns(extra) or not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("incorrect or non-finite signal schema")
    return frame


def oriented(frame, seed, extra=()):
    x, y = make_oriented_xy(frame, seed=seed)
    for name in extra:
        x[name] = frame[name].to_numpy() * np.where(y == 0, -1., 1.)
    return checked(x, extra), y


def reverse(frame, extra=()):
    out = checked(frame, extra).copy()
    out.loc[:, [*ANTISYM, *extra]] *= -1
    return out


def probability(clf, calibrator, frame, extra=()):
    checked(frame, extra)
    if not extra:
        return paired_probability(clf, calibrator, frame)
    if frame.empty:
        return np.empty(0, dtype=float)
    both = pd.concat([frame, reverse(frame, extra)], ignore_index=True)
    raw = np.asarray(clf.predict_proba(both), dtype=float)
    if raw.shape != (len(both), 2) or not np.isfinite(raw).all() or np.any((raw < 0) | (raw > 1)):
        raise ValueError("invalid classifier probability")
    p = np.asarray(calibrator.predict(raw[:, 1]), dtype=float)
    if p.shape != (len(both),) or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("invalid calibrated probability")
    return .5 * (p[:len(frame)] + (1 - p[len(frame):]))


def select_signals(base, enriched):
    out = select_dual_state_features(base, enriched, 32)
    mask = out.uses_lower_state
    out.loc[mask, list(SIGNALS)] = enriched.loc[mask, list(SIGNALS)].to_numpy()
    return out


def fit_fold(core, cal, seed, extra=(), tour="wta"):
    columns(extra)
    overrides = xgb_params_for(tour)
    if not extra:
        return _fit_fold(core, cal, seed=seed, calibrator="platt", n_bag=5,
                         xgb_overrides=overrides)
    xcal, ycal = oriented(cal, seed + 1, extra)
    clfs = []
    for k in range(5):
        xtr, ytr = oriented(core, seed + 100_000 * k, extra)
        clf = _xgb(**full_xgb_params(overrides, bag_index=k))
        clf.fit(xtr, ytr, sample_weight=None, eval_set=[(xcal, ycal)], verbose=False)
        clfs.append(clf)
    model = BaggedClassifier(clfs)
    calibration = PlattCalibrator().fit(model.predict_proba(xcal)[:, 1], ycal)
    return model, calibration


def walk_forward(base, selected, extra=(), tour="wta", end_test=2019):
    """Fit main rows only; new signals follow the same selected state as all inputs."""
    require_paired(base, selected)
    for frame in (base, selected):
        checked(frame[columns(extra)], extra)
        if not frame.draw_level.eq("main").all() or not frame.tour.eq(tour).all():
            raise ValueError("incorrect combiner population")
    if not base.completed.equals(selected.completed) or not base.year.equals(selected.year):
        raise ValueError("fitting/scoring populations differ")
    base = base[base.completed].reset_index(drop=True)
    selected = selected[selected.completed].reset_index(drop=True)
    chunks, folds = [], []
    for year in range(2010, end_test + 1):
        train = base[base.year.between(1991, year - 1)]
        test = selected[selected.year.eq(year)]
        if len(test) == 0 or len(train) < 5000:
            continue
        core, cal = train[train.year.lt(year - 1)], train[train.year.eq(year - 1)]
        reused = len(cal) < 500 or len(core) < 2000
        if reused:
            core, cal = train, train
        clf, calibration = fit_fold(core, cal, year, extra, tour)
        p = probability(clf, calibration, test[columns(extra)], extra)
        chunks.append(test.assign(p_combiner=p, p_raw=clf.predict_proba(test[columns(extra)])[:, 1],
                                  probability_policy="calibrated-pair-average-v1"))
        folds.append({"year": year, "train": len(train), "core": len(core), "calibration": len(cal),
                      "test": len(test), "warmupReuse": reused,
                      "bagBestIterations": [int(c.best_iteration) for c in clf.clfs]})
    if not chunks:
        raise ValueError("no scoreable research folds")
    return pd.concat(chunks, ignore_index=True), folds
