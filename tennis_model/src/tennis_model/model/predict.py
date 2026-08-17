"""Single-match predictor: the trained combiner + final rating states.

Builds the exact FEATURES vector for an arbitrary (A, B, surface, format) matchup
and returns a calibrated P(A beats B) plus a set-score distribution from the point
model. Context features that need live match conditions (rest, in-tournament fatigue)
are set neutral for hypothetical matchups; head-to-head comes from career history.
"""

from __future__ import annotations

import math
import pickle
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from ..config import MATCH_POPULATION_VERSION, PLAYER_ALIASES, output_dir
from ..data.charting import STYLE_FEATURES, build_profiles, name_key
from ..points.markov import match_win_prob, score_distribution
from .features import DEFAULT_FEAT_PARAMS, FEATURES, build_predictor_inputs, feat_params_for
from .train import train_final


def predictor_path(tour: str = "atp"):
    return output_dir(tour) / "predictor.pkl"


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _num(x, default=np.nan) -> float:
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


class TennisPredictor:
    def __init__(self, clf, iso, elo, srv, ctx, meta, tour="atp", fp=None):
        self.clf, self.iso = clf, iso
        self.elo, self.srv, self.ctx, self.meta = elo, srv, ctx, meta
        self.tour = tour
        # FeatureParams the training frame was built with; derived from the tour when
        # omitted so no construction site can silently fall back to config defaults
        # (pipeline.build_tour once shipped WTA pickles with fp=None)
        self.fp = fp if fp is not None else feat_params_for(tour)
        # The ratings walk consumes already-canonicalized names. A quick refresh restoring
        # this pickle after PLAYER_ALIASES changes must rebuild those states rather than
        # pair a renamed match frame with the old split identities.
        self.player_aliases = tuple(sorted(PLAYER_ALIASES.items()))
        # Rating state is the result of walking the adopted match population. A quick
        # refresh may reuse it only while that population contract is unchanged; otherwise
        # the cached model must be rebuilt before its outputs can claim the new version.
        self.match_population_version = MATCH_POPULATION_VERSION
        # When this model was trained. Derived here rather than at the call sites (both of
        # them construct straight out of train_final) so no path can ship an unstamped
        # pickle — same reasoning as `fp` above. It rides INSIDE the pickle on purpose: the
        # file mtime is laundered by an actions/cache restore, and every JSON export stamps
        # itself with now(), so this is the only honest record of model age.
        self.trained_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    @property
    def _fp(self):
        # tolerate pickles from before the FeatureParams refactor
        return getattr(self, "fp", None) or DEFAULT_FEAT_PARAMS

    @property
    def _trained_at(self) -> str | None:
        """None for pickles predating the stamp — the next full retrain fills it in."""
        return getattr(self, "trained_at", None)

    @property
    def _player_aliases(self) -> tuple:
        """Empty for legacy pickles, which deliberately makes the quick guard rebuild."""
        return getattr(self, "player_aliases", ())

    @property
    def _match_population_version(self) -> int | None:
        """None for legacy pickles, which deliberately makes the quick guard rebuild."""
        return getattr(self, "match_population_version", None)

    def _home_flag(self, a: str, b: str, event: str | None) -> float:
        """home_flag_diff for a real match at a known event (0 for hypotheticals)."""
        if not event:
            return 0.0
        from ..data.geo import IOC_ALIAS, host_ioc
        asof = self.elo.last_date
        # year-dependent hosts (Olympics, Tour Finals) resolve with the data's
        # newest year — correct for live forecasts, approximate only across a
        # year boundary for a year-keyed event (negligible in practice)
        year = pd.Timestamp(asof).year if asof is not None else pd.Timestamp.now().year
        host = host_ioc(str(event), int(year), self.tour)
        if host is None:
            return 0.0
        ia = self.meta.get(a, {}).get("ioc")
        ib = self.meta.get(b, {}).get("ioc")
        ia, ib = IOC_ALIAS.get(ia, ia), IOC_ALIAS.get(ib, ib)
        return float(int(host == ia) - int(host == ib))

    # -- feature construction (must mirror features._assemble, winner-slot = A) ----
    def _feature_dict(self, a: str, b: str, surface: str, best_of: int,
                      indoor: bool, tier_k: float, round_order: int,
                      event: str | None = None) -> dict:
        elo, srv, ctx, meta = self.elo, self.srv, self.ctx, self.meta
        ma, mb = meta.get(a, {}), meta.get(b, {})

        belo_a, belo_b = elo.blended(a, surface), elo.blended(b, surface)
        p_blend = elo.win_prob(a, b, surface, best_of=best_of)   # Bo5-scale parity
        pa, pb = srv.point_probs(a, b, surface, event=event)     # event-speed parity
        p_point = match_win_prob(pa, pb, best_of)
        rpa, rpb = _num(ma.get("rank_points")), _num(mb.get("rank_points"))
        h2a, h2b = ctx.record(a, b)
        h2sa, h2sb = ctx.record_surface(a, b, surface)

        # layoff/form relative to the newest match in the data (~today in production)
        asof = elo.last_date
        def _days_since(name):
            last = elo.last_played.get(name)
            return float((asof - last) / np.timedelta64(1, "D")) if last is not None else 365.0
        da, db = _days_since(a), _days_since(b)
        age_a, age_b = _num(ma.get("age")), _num(mb.get("age"))
        ht_a, ht_b = _num(ma.get("ht")), _num(mb.get("ht"))
        fp = self._fp

        row = {
            "elo_diff": belo_a - belo_b,
            "elo_overall_diff": elo.elo(a) - elo.elo(b),
            "elo_surface_diff": elo.surface_elo(a, surface) - elo.surface_elo(b, surface),
            "logit_p_blend": _logit(p_blend),
            "logit_p_point": _logit(p_point),
            "serve_skill_diff": srv.serve_skill(a, surface) - srv.serve_skill(b, surface),
            "return_skill_diff": srv.return_skill(a, surface) - srv.return_skill(b, surface),
            "rankpts_diff": math.log((np.nan_to_num(rpa) + 1) / (np.nan_to_num(rpb) + 1))
            if np.isfinite(rpa) and np.isfinite(rpb) else 0.0,
            "exp_diff": math.log(elo.n.get(a, 0) + 1) - math.log(elo.n.get(b, 0) + 1),
            # training fills the pair DIFFERENCE with 0 when either side is missing
            # (features._assemble .fillna(0) after the subtraction) — mirror that here
            "age_diff": age_a - age_b if np.isfinite(age_a) and np.isfinite(age_b) else 0.0,
            "ht_diff": ht_a - ht_b if np.isfinite(ht_a) and np.isfinite(ht_b) else 0.0,
            "hand_matchup": int(ma.get("hand") == "L") - int(mb.get("hand") == "L"),
            "rest_diff": 0.0,
            "fatigue_diff": 0.0,
            "h2h_diff": h2a - h2b,
            "log_days_since_diff": math.log1p(da) - math.log1p(db),
            "layoff_flag_diff": int(da > fp.layoff_days) - int(db > fp.layoff_days),
            "form90_diff": elo.form_delta(a, asof) - elo.form_delta(b, asof),
            "winrate10_diff": ctx.winrate10(a) - ctx.winrate10(b),
            "h2h_surface_diff": h2sa - h2sb,
            "entry_q_diff": 0.0,               # entry method unknown for hypotheticals
            # neutral for hypotheticals; real matches pass event= for the venue
            "home_flag_diff": self._home_flag(a, b, event),
            "peak_age_dev_diff": (abs(age_a - fp.peak_age) - abs(age_b - fp.peak_age)
                                  if np.isfinite(age_a) and np.isfinite(age_b) else 0.0),
            "best_of": best_of,
            "is_indoor": int(bool(indoor)),
            "tier_k": tier_k,
            "round_order": round_order,
            "surf_hard": int(surface == "Hard"),
            "surf_clay": int(surface == "Clay"),
            "surf_grass": int(surface == "Grass"),
            "log_min_srv_pts": math.log1p(min(srv.gsp.get(a, 0.0), srv.gsp.get(b, 0.0))),
            "log_min_matches": math.log1p(min(elo.n.get(a, 0), elo.n.get(b, 0))),
            "log1p_h2h_total": math.log1p(h2a + h2b),
        }
        # MCP tactical-style diffs (0 unless both players are profiled)
        # Matrix export calls this thousands of times. MCP profiles are immutable during one
        # predictor lifetime, so loading/parsing them per pair made the old matrix build spend
        # most of its time repeating identical work.
        profiles = getattr(self, "_style_profiles_cache", None)
        if profiles is None:
            profiles = build_profiles(self.tour)
            self._style_profiles_cache = profiles
        ka, kb = name_key(a), name_key(b)
        row["has_style"] = int(ka in profiles and kb in profiles)
        for s in STYLE_FEATURES:
            diff = 0.0
            if row["has_style"]:
                va, vb = profiles[ka].get(s, np.nan), profiles[kb].get(s, np.nan)
                diff = float(va - vb) if (va == va and vb == vb) else 0.0
            row[s + "_diff"] = diff
        return row

    def features(self, a: str, b: str, surface: str = "Hard", best_of: int = 3,
                 indoor: bool = False, tier_k: float = 1.0, round_order: int = 3,
                 event: str | None = None) -> pd.DataFrame:
        row = self._feature_dict(a, b, surface, best_of, indoor, tier_k, round_order,
                                 event=event)
        return pd.DataFrame([[row[c] for c in FEATURES]], columns=FEATURES)

    # -- predictions ---------------------------------------------------------------
    def win_prob(self, a: str, b: str, **kw) -> float:
        raw = self.clf.predict_proba(self.features(a, b, **kw))[:, 1]
        return float(self.iso.predict(raw)[0])

    @staticmethod
    def _prob_from_logit(value: float) -> float:
        return 1.0 / (1.0 + math.exp(-float(value)))

    def prediction_components(self, a: str, b: str, surface: str = "Hard",
                              best_of: int = 3, indoor: bool = False,
                              tier_k: float = 1.0, round_order: int = 3,
                              event: str | None = None) -> dict[str, float]:
        """The two model inputs and calibrated combiner for one matchup.

        These are component probabilities, not feature attribution: they show where the
        independently useful Elo and point models land before the combiner uses them with
        the remaining context features.
        """
        row = self._feature_dict(a, b, surface, best_of, indoor, tier_k, round_order,
                                 event=event)
        X = pd.DataFrame([[row[c] for c in FEATURES]], columns=FEATURES)
        raw = self.clf.predict_proba(X)[:, 1]
        return {
            "eloBlend": self._prob_from_logit(row["logit_p_blend"]),
            "pointModel": self._prob_from_logit(row["logit_p_point"]),
            "combiner": float(self.iso.predict(raw)[0]),
        }

    def prediction_matrices(self, players: list, surface: str = "Hard", best_of: int = 3,
                            indoor: bool = False, tier_k: float = 1.0,
                            round_order: int = 3, event: str | None = None):
        """Batched antisymmetric matrices for Elo, point model, and final combiner."""
        n = len(players)
        out = {name: np.full((n, n), 0.5)
               for name in ("eloBlend", "pointModel", "combiner")}
        if n < 2:
            return out
        ii, jj, rows = [], [], []
        for i in range(n):
            for j in range(i + 1, n):
                rows.append(self._feature_dict(players[i], players[j], surface, best_of,
                                               indoor, tier_k, round_order, event=event))
                ii.append(i)
                jj.append(j)
        X = pd.DataFrame(rows, columns=FEATURES)
        values = {
            "eloBlend": np.array([self._prob_from_logit(r["logit_p_blend"]) for r in rows]),
            "pointModel": np.array([self._prob_from_logit(r["logit_p_point"]) for r in rows]),
            "combiner": self.iso.predict(self.clf.predict_proba(X)[:, 1]),
        }
        ia, ja = np.array(ii), np.array(jj)
        for name, probs in values.items():
            out[name][ia, ja] = probs
            out[name][ja, ia] = 1.0 - probs
        return out

    def win_prob_matrix(self, players: list, surface: str = "Hard", best_of: int = 3,
                        indoor: bool = False, tier_k: float = 1.0, round_order: int = 3,
                        event: str | None = None):
        """Pairwise P(i beats j) matrix, antisymmetrised so P[i,j] = 1 - P[j,i].

        Builds the upper triangle in one batched prediction (the hot path for the
        Monte Carlo draw simulator).
        """
        return self.prediction_matrices(
            players, surface=surface, best_of=best_of, indoor=indoor,
            tier_k=tier_k, round_order=round_order, event=event,
        )["combiner"]

    def predict(self, a: str, b: str, surface: str = "Hard", best_of: int = 3, **kw) -> dict:
        components = self.prediction_components(a, b, surface=surface, best_of=best_of, **kw)
        p = components["combiner"]
        dist = score_distribution(p, best_of)          # consistent with the combiner prob
        return {
            "a": a, "b": b, "surface": surface, "best_of": best_of,
            "p_a": round(p, 4), "p_b": round(1 - p, 4),
            "p_blend": round(components["eloBlend"], 4),
            "p_point": round(components["pointModel"], 4),
            "set_dist": {k: round(v, 3) for k, v in dist.items()},
        }

    # -- persistence ---------------------------------------------------------------
    def save(self, path=None) -> None:
        path = path or predictor_path(self.tour)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(self, fh)

    @staticmethod
    def load(tour: str = "atp", path=None) -> TennisPredictor:
        path = path or predictor_path(tour)
        with open(path, "rb") as fh:
            return pickle.load(fh)


def fit_predictor(tour: str = "atp", save: bool = True) -> TennisPredictor:
    """Build states + train the production combiner, returning a ready predictor."""
    from .train import xgb_params_for
    feat, elo, srv, ctx, meta = build_predictor_inputs(tour=tour)
    clf, iso, _ = train_final(feat, xgb_overrides=xgb_params_for(tour))
    pred = TennisPredictor(clf, iso, elo, srv, ctx, meta, tour=tour)
    if save:
        pred.save()
    return pred


if __name__ == "__main__":
    import sys
    tour = sys.argv[1] if len(sys.argv) > 1 else "atp"
    pred = fit_predictor(tour)
    print("Saved predictor. Example matchups:\n")
    examples = [
        ("Carlos Alcaraz", "Novak Djokovic", "Clay", 5),
        ("Carlos Alcaraz", "Novak Djokovic", "Grass", 5),
        ("Jannik Sinner", "Carlos Alcaraz", "Hard", 5),
        ("Jannik Sinner", "Carlos Alcaraz", "Hard", 3),
    ]
    for a, b, surf, bo in examples:
        r = pred.predict(a, b, surface=surf, best_of=bo)
        print(f"{a} vs {b}  [{surf}, Bo{bo}]  P({a})={r['p_a']:.3f}  "
              f"(elo {r['p_blend']:.3f}, point {r['p_point']:.3f})  dist={r['set_dist']}")
