"""Unit checks for model/train.py calibrators + fold determinism — fully synthetic.

Runnable directly (`python tests/test_train.py`) or under pytest. The determinism
test is same-process/same-machine only (no cross-platform golden numbers).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.model.features import ANTISYM, FEATURES, SYMMETRIC
from tennis_model.model.train import (
    IdentityCalibrator,
    IsotonicCalibrator,
    PlattCalibrator,
    _fit_fold,
    _orient_for_cal,
)


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def test_platt_monotone_and_improves_overconfident():
    rng = np.random.default_rng(0)
    p_true = rng.uniform(0.05, 0.95, 6000)
    z = np.log(p_true / (1 - p_true))
    p_raw = _sigmoid(2.5 * z)                    # overconfident distortion of the truth
    y = (rng.random(6000) < p_true).astype(int)
    cal = PlattCalibrator().fit(p_raw, y)
    grid = np.linspace(0.01, 0.99, 99)
    out = cal.predict(grid)
    assert np.all(np.diff(out) >= 0)             # monotone
    assert np.all((out > 0) & (out < 1))
    brier_raw = np.mean((p_raw - y) ** 2)
    brier_cal = np.mean((cal.predict(p_raw) - y) ** 2)
    assert brier_cal < brier_raw                 # fixes the overconfidence
    print("ok test_platt_monotone_and_improves_overconfident")


def test_platt_near_identity_on_calibrated_input():
    rng = np.random.default_rng(1)
    p = rng.uniform(0.05, 0.95, 8000)
    y = (rng.random(8000) < p).astype(int)
    cal = PlattCalibrator().fit(p, y)
    assert np.mean(np.abs(cal.predict(p) - p)) < 0.02
    print("ok test_platt_near_identity_on_calibrated_input")


def test_isotonic_monotone_and_clips():
    rng = np.random.default_rng(2)
    p = rng.uniform(0, 1, 4000)
    y = (rng.random(4000) < p).astype(int)
    cal = IsotonicCalibrator().fit(p, y)
    grid = np.linspace(0, 1, 101)
    out = cal.predict(grid)
    assert np.all(np.diff(out) >= -1e-12)
    lo, hi = cal.predict(np.array([-0.5, 1.5]))  # out-of-range inputs clip finitely
    assert 0.0 <= lo <= 1.0 and 0.0 <= hi <= 1.0
    print("ok test_isotonic_monotone_and_clips")


def test_identity_roundtrip_and_chainable():
    p = np.array([0.1, 0.5, 0.9])
    cal = IdentityCalibrator().fit(p, np.array([0, 1, 1]))   # fit returns self
    assert np.array_equal(cal.predict(p), p)
    print("ok test_identity_roundtrip_and_chainable")


def test_orient_for_cal_alternating_flip():
    p, y = _orient_for_cal(np.array([0.8, 0.8, 0.8, 0.8]))
    assert np.allclose(p, [0.8, 0.2, 0.8, 0.2])
    assert list(y) == [1, 0, 1, 0]
    print("ok test_orient_for_cal_alternating_flip")


def _synthetic_feat(n=2200, seed=3) -> pd.DataFrame:
    """Winner-oriented frame with a mild elo_diff signal so early stopping engages."""
    rng = np.random.default_rng(seed)
    f = pd.DataFrame({c: rng.normal(size=n) for c in ANTISYM})
    for c in SYMMETRIC:
        f[c] = rng.uniform(0, 1, n)
    f["elo_diff"] = np.abs(f["elo_diff"]) + 0.3          # winners rate higher on average
    f["year"] = np.where(np.arange(n) < n * 0.8, 2020, 2021)
    f["completed"] = True
    return f


def test_fit_fold_deterministic():
    """Two identical fits must agree bit-for-bit — the lock on random_state plus the
    seeded orientation flips (regression guard for anyone dropping the XGB seed)."""
    feat = _synthetic_feat()
    core, cal = feat[feat["year"] == 2020], feat[feat["year"] == 2021]
    clf1, cal1 = _fit_fold(core, cal, seed=7)
    clf2, cal2 = _fit_fold(core, cal, seed=7)
    X = feat[FEATURES].iloc[:200]
    p1, p2 = clf1.predict_proba(X)[:, 1], clf2.predict_proba(X)[:, 1]
    assert np.array_equal(p1, p2)
    assert np.array_equal(cal1.predict(p1), cal2.predict(p2))
    print("ok test_fit_fold_deterministic")


def test_xgb_params_for_reads_adopted_overrides():
    from tennis_model.model.train import xgb_params_for
    wta = xgb_params_for("wta")
    assert wta and wta["max_depth"] == 7          # the adopted WTA combiner config
    assert xgb_params_for("atp") == {}            # ATP sweep rejected: defaults stand
    assert xgb_params_for("wta") is not xgb_params_for("wta")   # defensive copy
    print("ok test_xgb_params_for_reads_adopted_overrides")


def test_fit_fold_respects_overrides():
    feat = _synthetic_feat(seed=4)
    core, cal = feat[feat["year"] == 2020], feat[feat["year"] == 2021]
    clf, _ = _fit_fold(core, cal, seed=7, xgb_overrides={"max_depth": 2, "n_estimators": 30})
    assert clf.get_params()["max_depth"] == 2
    assert clf.get_params()["n_estimators"] == 30
    print("ok test_fit_fold_respects_overrides")


if __name__ == "__main__":
    test_platt_monotone_and_improves_overconfident()
    test_platt_near_identity_on_calibrated_input()
    test_isotonic_monotone_and_clips()
    test_identity_roundtrip_and_chainable()
    test_orient_for_cal_alternating_flip()
    test_fit_fold_deterministic()
    test_fit_fold_respects_overrides()
    print("\nALL PASSED")
