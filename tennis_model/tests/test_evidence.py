from __future__ import annotations

import numpy as np
import tennis_model.model.predict as predict
from tennis_model.model.features import H2HState
from tennis_model.model.predict import EVIDENCE_GROUPS, TennisPredictor


class _Elo:
    overall = {"A": 1, "B": 1}
    n = {"A": 50, "B": 40}
    last_date = np.datetime64("2026-08-10")
    last_played = {"A": np.datetime64("2026-08-09"), "B": np.datetime64("2026-08-05")}

    def blended(self, name, surface): return 1800.0 if name == "A" else 1700.0
    def elo(self, name): return 1790.0 if name == "A" else 1710.0
    def surface_elo(self, name, surface): return 1810.0 if name == "A" else 1690.0
    def win_prob(self, a, b, surface, best_of=3): return 0.62
    def form_delta(self, name, asof, days=None): return 20.0 if name == "A" else -10.0


class _Srv:
    gsp = {"A": 1000.0, "B": 900.0}
    def point_probs(self, a, b, surface, event=None): return 0.64, 0.61
    def serve_skill(self, name, surface): return 0.02 if name == "A" else -0.01
    def return_skill(self, name, surface): return 0.01 if name == "A" else -0.01


class _Clf:
    def predict_proba(self, frame):
        z = (0.003 * frame["elo_diff"].to_numpy()
             + 0.5 * frame["logit_p_point"].to_numpy()
             + 0.02 * frame["rest_diff"].to_numpy()
             + 0.1 * frame["h2h_diff"].to_numpy()
             + 0.2 * frame["home_flag_diff"].to_numpy())
        p = 1.0 / (1.0 + np.exp(-z))
        return np.column_stack((1.0 - p, p))


class _Iso:
    def predict(self, values): return np.asarray(values)


def _predictor():
    ctx = H2HState(
        {("A", "B"): [2, 1]}, {(('A', 'B'), "Hard"): [1, 0]},
        {"A": [1, 1, 0], "B": [0, 1, 0]},
        {"A": [(np.datetime64("2026-08-09"), 28)],
         "B": [(np.datetime64("2026-08-04"), 20)]},
    )
    meta = {"A": {"rank_points": 3000, "age": 25, "ht": 185, "hand": "R", "ioc": "USA"},
            "B": {"rank_points": 2000, "age": 27, "ht": 188, "hand": "L", "ioc": "ESP"}}
    return TennisPredictor(_Clf(), _Iso(), _Elo(), _Srv(), ctx, meta, tour="atp")


def test_scheduled_date_mirrors_rest_and_recent_workload(monkeypatch):
    monkeypatch.setattr(predict, "build_profiles", lambda tour: {})
    row = _predictor()._feature_dict(
        "A", "B", "Hard", 3, False, 1.0, 5, as_of="2026-08-10",
    )
    assert row["rest_diff"] == -4.0  # one day for A versus five for B
    assert row["fatigue_diff"] == 8.0  # both matches fall inside the tuned 14-day window


def test_evidence_is_grouped_ranked_and_explicitly_noncausal(monkeypatch):
    monkeypatch.setattr(predict, "build_profiles", lambda tour: {})
    evidence = _predictor().prediction_evidence(
        "A", "B", "Hard", as_of="2026-08-10", event="US Open", round_order=5,
    )
    assert {signal["key"] for signal in evidence["signals"]} == set(EVIDENCE_GROUPS)
    available = [s for s in evidence["signals"] if s["available"]]
    assert [abs(s["impactPp"]) for s in available] == sorted(
        [abs(s["impactPp"]) for s in available], reverse=True)
    assert "not causation" in evidence["note"]
    assert next(s for s in evidence["signals"] if s["key"] == "home")["supports"] == "A"
    assert next(s for s in evidence["signals"] if s["key"] == "style")["available"] is False


def test_evidence_matrices_reverse_sign_and_availability(monkeypatch):
    monkeypatch.setattr(predict, "build_profiles", lambda tour: {})
    matrices = _predictor().prediction_evidence_matrices(["A", "B"], "Hard")
    for matrix in matrices["effects"].values():
        assert matrix[0, 1] == -matrix[1, 0]
        assert matrix[0, 0] == 0.0
    assert matrices["available"]["h2h"][0, 1] == 1.0
    assert matrices["available"]["style"][0, 1] == 0.0
