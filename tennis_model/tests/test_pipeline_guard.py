"""Quick-mode staleness guard: a cached predictor trained on an older feature schema
must be detected (and rebuilt) instead of crashing inside XGBoost mid-refresh, and
one carrying FeatureParams that differ from the tour's current config must be
rebuilt instead of serving inference mismatched to its training frame. The same
applies to player aliases: a renamed match frame cannot reuse split rating states.

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


def test_predictor_player_alias_guard():
    fresh = _pred(_Clf(list(FEATURES)), "atp")
    assert pipeline._predictor_current(fresh, "atp")

    stale = _pred(_Clf(list(FEATURES)), "atp")
    stale.player_aliases = ()
    assert not pipeline._predictor_current(stale, "atp")

    legacy = _pred(_Clf(list(FEATURES)), "atp")
    del legacy.player_aliases
    assert not pipeline._predictor_current(legacy, "atp")
    print("ok test_predictor_player_alias_guard")




# --- the ratings walk must survive a failing backtest (2026-07-25) -----------------------

def test_a_failing_backtest_does_not_cost_the_ratings_walk():
    """`walk_forward` produces accuracy.json — reported metrics, nothing the shipped model
    depends on — but it runs BEFORE train_final, so an exception in it used to abort
    build_tour before `predictor.save()`. A completed re-walk of 283k matches was thrown
    away over a reporting artifact, and (because a red job never saved the data cache) the
    next run restored the OLD model. Ratings must survive it."""
    import tennis_model.pipeline as pl

    saved = {}

    class _Pred:
        def __init__(self, *a, **k):
            self.elo = self.srv = self.meta = None
        def save(self):
            saved["yes"] = True

    orig = (pl.load_matches, pl.build_predictor_inputs, pl.main_rows, pl.walk_forward,
            pl.train_final, pl.TennisPredictor, pl.export_all, pl._market_scorecard,
            pl._track, pl._kalshi, pl._mirror)
    try:
        pl.load_matches = lambda tour: "df"
        pl.build_predictor_inputs = lambda df: ("feat", "elo", "srv", "ctx", "meta")
        pl.main_rows = lambda feat: feat
        pl.train_final = lambda feat, **k: ("clf", "iso", None)
        pl.TennisPredictor = _Pred
        pl.export_all = lambda *a, **k: None
        pl._market_scorecard = lambda *a, **k: None
        pl._track = lambda *a, **k: None
        pl._kalshi = lambda *a, **k: None
        pl._mirror = lambda *a, **k: None

        def _boom(*a, **k):
            raise KeyError(256)          # the real 2026-07-11 crash shape
        pl.walk_forward = _boom

        pl.build_tour("atp", do_backtest=True)      # must NOT raise
        assert saved.get("yes"), "predictor.save() was skipped after a backtest failure"
    finally:
        (pl.load_matches, pl.build_predictor_inputs, pl.main_rows, pl.walk_forward,
         pl.train_final, pl.TennisPredictor, pl.export_all, pl._market_scorecard,
         pl._track, pl._kalshi, pl._mirror) = orig
    print("ok test_a_failing_backtest_does_not_cost_the_ratings_walk")


if __name__ == "__main__":
    test_predictor_schema_guard()
    test_predictor_feat_param_guard()
    test_a_failing_backtest_does_not_cost_the_ratings_walk()
    print("\nALL PASSED")
