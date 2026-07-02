"""Quick-mode schema guard: a cached predictor trained on an older feature schema
must be detected (and rebuilt) instead of crashing inside XGBoost mid-refresh.

Runnable directly (`python tests/test_pipeline_guard.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.pipeline as pipeline
from tennis_model.model.features import FEATURES


class _Booster:
    def __init__(self, names):
        self.feature_names = names


class _Clf:
    def __init__(self, names):
        self._b = _Booster(names)

    def get_booster(self):
        return self._b


class _P:
    def __init__(self, clf):
        self.clf = clf


def test_predictor_schema_guard():
    assert pipeline._predictor_current(_P(_Clf(list(FEATURES))))
    assert not pipeline._predictor_current(_P(_Clf(list(FEATURES)[:-2])))       # stale cache
    assert not pipeline._predictor_current(_P(_Clf(list(FEATURES)[::-1])))      # order matters

    class _Opaque:
        def get_booster(self):
            raise AttributeError("no booster")

    assert pipeline._predictor_current(_P(_Opaque()))    # un-introspectable: assume current
    print("ok test_predictor_schema_guard")


if __name__ == "__main__":
    test_predictor_schema_guard()
    print("\nALL PASSED")
