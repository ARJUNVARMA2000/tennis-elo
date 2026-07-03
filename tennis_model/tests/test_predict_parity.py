"""Train/inference feature-parity checks for TennisPredictor — stub states, no data.

Runnable directly (`python tests/test_predict_parity.py`) or under pytest. The
predictor's _feature_dict hand-mirrors features._assemble; these tests pin the two
cheapest, highest-value contracts: the key set matches FEATURES exactly, and the
missing-bio semantics match training (pair difference -> 0 when either side is
missing, as _assemble's .fillna(0) after the subtraction does).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.model.predict as predict
from tennis_model.model.features import FEATURES
from tennis_model.model.predict import TennisPredictor


class _Elo:
    def __init__(self):
        self.n = {"Alfa One": 10, "Bravo Two": 8}
        self.last_played = {"Alfa One": np.datetime64("2026-06-25"),
                            "Bravo Two": np.datetime64("2026-06-28")}
        self.last_date = np.datetime64("2026-07-01")

    def blended(self, name, surf):
        return 1550.0 if name == "Alfa One" else 1500.0

    def win_prob(self, a, b, surf, best_of=3):
        return 0.55

    def elo(self, name):
        return 1540.0 if name == "Alfa One" else 1500.0

    def surface_elo(self, name, surf):
        return 1560.0 if name == "Alfa One" else 1500.0

    def form_delta(self, name, asof, days=None):
        return 0.02 if name == "Alfa One" else -0.01


class _Srv:
    gsp = {"Alfa One": 500.0, "Bravo Two": 400.0}

    def point_probs(self, a, b, surf, event=None):
        return 0.64, 0.62

    def serve_skill(self, name, surf):
        return 0.01 if name == "Alfa One" else -0.01

    def return_skill(self, name, surf):
        return -0.005 if name == "Alfa One" else 0.005


class _Ctx:
    def record(self, a, b):
        return (2, 1)

    def record_surface(self, a, b, surf):
        return (1, 0)

    def winrate10(self, name):
        return 0.6 if name == "Alfa One" else 0.5


def _predictor(meta) -> TennisPredictor:
    return TennisPredictor(clf=None, iso=None, elo=_Elo(), srv=_Srv(), ctx=_Ctx(),
                           meta=meta, tour="atp")


def _with_no_profiles(fn):
    orig = predict.build_profiles
    try:
        predict.build_profiles = lambda tour: {}
        return fn()
    finally:
        predict.build_profiles = orig


def test_feature_dict_keys_match_FEATURES():
    """Any feature added to FEATURES but not mirrored here (or vice versa) must fail
    loudly — the batched matrix path would otherwise feed silent NaN columns."""
    meta = {"Alfa One": {"age": 24.0, "ht": 185.0, "hand": "R", "rank_points": 3000},
            "Bravo Two": {"age": 27.0, "ht": 190.0, "hand": "L", "rank_points": 1500}}
    row = _with_no_profiles(lambda: _predictor(meta)._feature_dict(
        "Alfa One", "Bravo Two", "Hard", 3, False, 1.0, 3))
    assert set(row) == set(FEATURES), (set(row) ^ set(FEATURES))
    f = _with_no_profiles(lambda: _predictor(meta).features("Alfa One", "Bravo Two"))
    assert list(f.columns) == list(FEATURES)
    print("ok test_feature_dict_keys_match_FEATURES")


def test_missing_bio_matches_training_semantics():
    """Training fills the pair DIFFERENCE with 0 when either side is missing —
    inference must not degrade to +/-(known value) (regression: one missing age
    yielded age_diff=-24, one missing height ht_diff=+185)."""
    meta = {"Alfa One": {"age": 24.0, "ht": 185.0, "hand": "R", "rank_points": 3000},
            "Bravo Two": {"hand": "L", "rank_points": 1500}}          # no age, no ht
    row = _with_no_profiles(lambda: _predictor(meta)._feature_dict(
        "Alfa One", "Bravo Two", "Hard", 3, False, 1.0, 3))
    assert row["age_diff"] == 0.0
    assert row["ht_diff"] == 0.0
    assert row["peak_age_dev_diff"] == 0.0
    # both known -> real differences
    meta["Bravo Two"].update(age=27.0, ht=190.0)
    row = _with_no_profiles(lambda: _predictor(meta)._feature_dict(
        "Alfa One", "Bravo Two", "Hard", 3, False, 1.0, 3))
    assert row["age_diff"] == -3.0 and row["ht_diff"] == -5.0
    print("ok test_missing_bio_matches_training_semantics")


def test_feature_params_thread_to_inference():
    """The predictor must apply its OWN FeatureParams (fp) — the module constants it
    used to import at load time could never see a tuned override. Old pickles
    (no fp attribute) fall back to the config defaults."""
    from tennis_model.model.features import FeatureParams
    meta = {"Alfa One": {"age": 24.0, "ht": 185.0, "hand": "R", "rank_points": 3000},
            "Bravo Two": {"age": 27.0, "ht": 190.0, "hand": "L", "rank_points": 1500}}
    # _Elo stub: Alfa idle 6 days, Bravo idle 3 days as of 2026-07-01
    pred = TennisPredictor(clf=None, iso=None, elo=_Elo(), srv=_Srv(), ctx=_Ctx(),
                           meta=meta, tour="atp",
                           fp=FeatureParams(layoff_days=5.0, peak_age=27.0))
    row = _with_no_profiles(lambda: pred._feature_dict(
        "Alfa One", "Bravo Two", "Hard", 3, False, 1.0, 3))
    assert row["layoff_flag_diff"] == 1                    # 6d > 5; 3d is not
    assert np.isclose(row["peak_age_dev_diff"], 3.0)       # |24-27| - |27-27|

    legacy = _predictor(meta)
    del legacy.fp                                          # simulate a pre-refactor pickle
    row = _with_no_profiles(lambda: legacy._feature_dict(
        "Alfa One", "Bravo Two", "Hard", 3, False, 1.0, 3))
    assert row["layoff_flag_diff"] == 0                    # config default: 120d
    assert np.isclose(row["peak_age_dev_diff"], 2.0)       # |24-26.5| - |27-26.5|
    print("ok test_feature_params_thread_to_inference")


def test_home_flag_threads_event():
    """Real matches pass event=; the venue's host country sets home_flag_diff.
    Hypotheticals (no event) and unmapped events stay neutral."""
    meta = {"Alfa One": {"age": 24.0, "ht": 185.0, "hand": "R", "rank_points": 3000,
                         "ioc": "GBR"},
            "Bravo Two": {"age": 27.0, "ht": 190.0, "hand": "L", "rank_points": 1500,
                          "ioc": "USA"}}
    pred = _predictor(meta)
    fd = lambda **kw: _with_no_profiles(lambda: pred._feature_dict(
        "Alfa One", "Bravo Two", "Hard", 3, False, 1.0, 3, **kw))
    assert fd()["home_flag_diff"] == 0.0                       # hypothetical
    assert fd(event="Wimbledon")["home_flag_diff"] == 1.0      # GBR at home
    assert fd(event="US Open")["home_flag_diff"] == -1.0       # USA at home
    assert fd(event="Mystery Invitational")["home_flag_diff"] == 0.0
    print("ok test_home_flag_threads_event")


if __name__ == "__main__":
    test_feature_dict_keys_match_FEATURES()
    test_missing_bio_matches_training_semantics()
    test_feature_params_thread_to_inference()
    test_home_flag_threads_event()
    print("\nALL PASSED")
