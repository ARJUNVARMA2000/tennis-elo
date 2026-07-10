"""Quick-mode staleness guard: a cached predictor trained on an older feature schema
must be detected (and rebuilt) instead of crashing inside XGBoost mid-refresh, and
one carrying FeatureParams that differ from the tour's current config must be
rebuilt instead of serving inference mismatched to its training frame.

Runnable directly (`python tests/test_pipeline_guard.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.pipeline as pipeline
from tennis_model.model.features import FEATURES, FeatureParams
from tennis_model.model.predict import TennisPredictor


class _Booster:
    def __init__(self, names):
        self.feature_names = names


class _Clf:
    def __init__(self, names):
        self._b = _Booster(names)

    def get_booster(self):
        return self._b


def _pred(clf, tour="atp") -> TennisPredictor:
    return TennisPredictor(clf=clf, iso=None, elo=None, srv=None, ctx=None,
                           meta={}, tour=tour)


def test_predictor_schema_guard():
    assert pipeline._predictor_current(_pred(_Clf(list(FEATURES))), "atp")
    assert not pipeline._predictor_current(_pred(_Clf(list(FEATURES)[:-2])), "atp")   # stale cache
    assert not pipeline._predictor_current(_pred(_Clf(list(FEATURES)[::-1])), "atp")  # order matters

    class _Opaque:
        def get_booster(self):
            raise AttributeError("no booster")

    assert pipeline._predictor_current(_pred(_Opaque()), "atp")   # un-introspectable: assume current
    print("ok test_predictor_schema_guard")


def test_predictor_feat_param_guard():
    """FeatureParams drift must trigger a quick-mode rebuild: pickles that shipped
    with fp=None (pipeline.build_tour pre-fix) heal on the next hourly run, and a
    FEAT_PARAM_OVERRIDES change can't keep serving a combiner trained on the old
    thresholds."""
    assert pipeline._predictor_current(_pred(_Clf(list(FEATURES)), "wta"), "wta")   # fresh build

    shipped = _pred(_Clf(list(FEATURES)), "wta")
    shipped.fp = None                                # what pipeline.build_tour used to pickle
    assert not pipeline._predictor_current(shipped, "wta")

    legacy = _pred(_Clf(list(FEATURES)), "atp")
    del legacy.fp                                    # pre-refactor pickle
    assert pipeline._predictor_current(legacy, "atp")   # defaults == atp params: no needless rebuild

    drift = _pred(_Clf(list(FEATURES)), "wta")
    drift.fp = FeatureParams(peak_age=99.0)          # config moved since this pickle was trained
    assert not pipeline._predictor_current(drift, "wta")

    # a cross-tour pickle mixup self-reports the wrong tour; the explicit arg catches it
    assert not pipeline._predictor_current(_pred(_Clf(list(FEATURES)), "wta"), "atp")
    print("ok test_predictor_feat_param_guard")


if __name__ == "__main__":
    test_predictor_schema_guard()
    test_predictor_feat_param_guard()
    print("\nALL PASSED")
