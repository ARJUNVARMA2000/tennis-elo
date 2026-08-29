"""Single-match predictor: the trained combiner + final rating states.

Builds the exact FEATURES vector for an arbitrary (A, B, surface, format) matchup
and returns a calibrated P(A beats B) plus a set-score distribution from the point
model. Context features that need live match conditions (rest, in-tournament fatigue)
are set neutral for hypothetical matchups; head-to-head comes from career history.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from ..config import (
    MATCH_POPULATION_VERSION,
    PLAYER_ALIASES,
    WTA_DUAL_STATE_GATE_THRESHOLD,
    output_dir,
)
from ..data.charting import STYLE_FEATURES, build_profiles, name_key
from ..data.results import load_matches
from ..points.markov import match_win_prob, score_distribution
from .features import (
    DEFAULT_FEAT_PARAMS,
    FEATURES,
    STYLE_DIFFS,
    build_dual_state_inputs,
    build_predictor_inputs,
    feat_params_for,
    use_lower_state,
)
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


def can_predict_match(predictor, a: str, b: str) -> bool:
    """Whether both entrants exist in the rating bundle inference would select.

    WTA's adopted cold-start gate deliberately selects the lower-enriched state when
    either entrant has fewer than the frozen number of main-draw matches.  Exporters
    must test membership in that selected bundle, not always in ``predictor.elo``;
    otherwise the lower state can improve backtests while lower-only draw entrants are
    still withheld in production.  Lightweight test/legacy predictors without the
    selector retain the historical main-state membership contract.
    """
    states_for = getattr(predictor, "_states_for", None)
    if callable(states_for):
        state = states_for(a, b)[0]
    else:
        main = getattr(predictor, "elo", None)
        threshold = getattr(
            predictor, "_dual_state_threshold",
            getattr(predictor, "dual_state_threshold", None),
        )
        counts = getattr(main, "n", {})
        state = (getattr(predictor, "lower_elo", None)
                 if use_lower_state(counts.get(a, 0), counts.get(b, 0), threshold)
                 else main)
    rated = getattr(state, "overall", {})
    return a in rated and b in rated


def predictor_player_names(predictor) -> tuple[str, ...]:
    """Canonical names available in any prediction-time rating bundle."""
    names: dict[str, None] = {}
    for attr in ("elo", "lower_elo"):
        state = getattr(predictor, attr, None)
        for name in getattr(state, "overall", {}):
            names.setdefault(str(name), None)
    return tuple(names)


EVIDENCE_GROUPS: dict[str, tuple[str, ...]] = {
    "surfaceElo": ("elo_diff", "elo_overall_diff", "elo_surface_diff", "logit_p_blend"),
    "serveReturn": ("logit_p_point", "serve_skill_diff", "return_skill_diff"),
    "form": ("form90_diff", "winrate10_diff"),
    "rest": ("rest_diff", "fatigue_diff", "log_days_since_diff", "layoff_flag_diff"),
    "home": ("home_flag_diff",),
    "h2h": ("h2h_diff", "h2h_surface_diff", "log1p_h2h_total"),
    "style": tuple(STYLE_DIFFS),
}
INFERENCE_SCHEMA_VERSION = 3


class TennisPredictor:
    def __init__(self, clf, iso, elo, srv, ctx, meta, tour="atp", fp=None, *,
                 lower_elo=None, lower_srv=None, lower_ctx=None,
                 dual_state_threshold: int | None = None):
        self.clf, self.iso = clf, iso
        self.elo, self.srv, self.ctx, self.meta = elo, srv, ctx, meta
        self.tour = tour
        self.lower_elo, self.lower_srv, self.lower_ctx = lower_elo, lower_srv, lower_ctx
        self.dual_state_threshold = dual_state_threshold
        if dual_state_threshold is not None:
            if tour != "wta":
                raise ValueError("dual-state inference is WTA-only")
            if any(state is None for state in (lower_elo, lower_srv, lower_ctx)):
                raise ValueError("an enabled dual-state gate requires all three lower states")
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
        # Bump when prediction-time state/semantics change without changing FEATURES.
        # Quick mode must not reuse a pickle whose context lacks the rest/fatigue mirror.
        self.inference_schema_version = INFERENCE_SCHEMA_VERSION
        # When this model was trained. Derived here rather than at the call sites (both of
        # them construct straight out of train_final) so no path can ship an unstamped
        # pickle — same reasoning as `fp` above. It rides INSIDE the pickle on purpose: the
        # file mtime is laundered by an actions/cache restore, and every JSON export stamps
        # itself with now(), so this is the only honest record of model age.
        self.trained_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        # Stable identity for this trained generation.  It is intentionally independent
        # from the envelope's payload digest: the UUID can ride inside the plain pickle
        # without creating a circular hash, while SHA-256 binds the exact serialized bytes.
        self.artifact_id = str(uuid.uuid4())

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

    @property
    def _inference_schema_version(self) -> int | None:
        return getattr(self, "inference_schema_version", None)

    @property
    def _dual_state_threshold(self) -> int | None:
        return getattr(self, "dual_state_threshold", None)

    @property
    def _has_lower_state(self) -> bool:
        return all(getattr(self, name, None) is not None
                   for name in ("lower_elo", "lower_srv", "lower_ctx"))

    def _states_for(self, a: str, b: str):
        """One complete state bundle selected from MAIN-only pre-match evidence."""
        threshold = self._dual_state_threshold
        if use_lower_state(self.elo.n.get(a, 0), self.elo.n.get(b, 0), threshold):
            if not self._has_lower_state:
                raise RuntimeError("dual-state gate is enabled but enriched state is absent")
            return self.lower_elo, self.lower_srv, self.lower_ctx
        return self.elo, self.srv, self.ctx

    def _home_context(self, a: str, b: str, event: str | None, as_of=None) -> dict:
        """Host evidence for a real match; hypotheticals remain explicitly unavailable."""
        if not event:
            return {"available": False, "hostIoc": None, "playerAHome": False,
                    "playerBHome": False, "diff": 0.0}
        from ..data.geo import IOC_ALIAS, host_ioc
        ref = as_of if as_of is not None else self.elo.last_date
        year = pd.Timestamp(ref).year if ref is not None else pd.Timestamp.now().year
        host = host_ioc(str(event), int(year), self.tour)
        if host is None:
            return {"available": False, "hostIoc": None, "playerAHome": False,
                    "playerBHome": False, "diff": 0.0}
        ia = self.meta.get(a, {}).get("ioc")
        ib = self.meta.get(b, {}).get("ioc")
        ia, ib = IOC_ALIAS.get(ia, ia), IOC_ALIAS.get(ib, ib)
        a_home, b_home = host == ia, host == ib
        return {"available": True, "hostIoc": host, "playerAHome": a_home,
                "playerBHome": b_home, "diff": float(int(a_home) - int(b_home))}

    def _home_flag(self, a: str, b: str, event: str | None, as_of=None) -> float:
        return float(self._home_context(a, b, event, as_of)["diff"])

    # -- feature construction (must mirror features._assemble, winner-slot = A) ----
    def _feature_dict(self, a: str, b: str, surface: str, best_of: int,
                      indoor: bool, tier_k: float, round_order: int,
                      event: str | None = None, as_of=None) -> dict:
        elo, srv, ctx = self._states_for(a, b)
        meta = self.meta
        ma, mb = meta.get(a, {}), meta.get(b, {})

        belo_a, belo_b = elo.blended(a, surface), elo.blended(b, surface)
        p_blend = elo.win_prob(a, b, surface, best_of=best_of)   # Bo5-scale parity
        pa, pb = srv.point_probs(a, b, surface, event=event)     # event-speed parity
        p_point = match_win_prob(pa, pb, best_of)
        rpa, rpb = _num(ma.get("rank_points")), _num(mb.get("rank_points"))
        h2a, h2b = ctx.record(a, b)
        h2sa, h2sb = ctx.record_surface(a, b, surface)

        # A scheduled match supplies its competition date; generic matrix/predictor calls
        # use the rating walk's latest factual date. This mirrors the training row's date.
        asof = np.datetime64(pd.Timestamp(as_of if as_of is not None else elo.last_date).to_datetime64())
        def _days_since(name):
            last = elo.last_played.get(name)
            return max(0.0, float((asof - last) / np.timedelta64(1, "D"))) if last is not None else 365.0
        da, db = _days_since(a), _days_since(b)
        workload = getattr(ctx, "workload", None)
        wa = float(workload(a, asof, self._fp.fatigue_window_days)) if workload else 0.0
        wb = float(workload(b, asof, self._fp.fatigue_window_days)) if workload else 0.0
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
            "rest_diff": float(np.clip(da - db, -60, 60)),
            "fatigue_diff": wa - wb,
            "h2h_diff": h2a - h2b,
            "log_days_since_diff": math.log1p(da) - math.log1p(db),
            "layoff_flag_diff": int(da > fp.layoff_days) - int(db > fp.layoff_days),
            "form90_diff": elo.form_delta(a, asof) - elo.form_delta(b, asof),
            "winrate10_diff": ctx.winrate10(a) - ctx.winrate10(b),
            "h2h_surface_diff": h2sa - h2sb,
            "entry_q_diff": 0.0,               # entry method unknown for hypotheticals
            # neutral for hypotheticals; real matches pass event= for the venue
            "home_flag_diff": self._home_flag(a, b, event, asof),
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
                 event: str | None = None, as_of=None) -> pd.DataFrame:
        row = self._feature_dict(a, b, surface, best_of, indoor, tier_k, round_order,
                                 event=event, as_of=as_of)
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
                              event: str | None = None, as_of=None) -> dict[str, float]:
        """The two model inputs and calibrated combiner for one matchup.

        These are component probabilities, not feature attribution: they show where the
        independently useful Elo and point models land before the combiner uses them with
        the remaining context features.
        """
        row = self._feature_dict(a, b, surface, best_of, indoor, tier_k, round_order,
                                 event=event, as_of=as_of)
        X = pd.DataFrame([[row[c] for c in FEATURES]], columns=FEATURES)
        raw = self.clf.predict_proba(X)[:, 1]
        return {
            "eloBlend": self._prob_from_logit(row["logit_p_blend"]),
            "pointModel": self._prob_from_logit(row["logit_p_point"]),
            "combiner": float(self.iso.predict(raw)[0]),
        }

    def prediction_evidence(self, a: str, b: str, surface: str = "Hard",
                            best_of: int = 3, indoor: bool = False,
                            tier_k: float = 1.0, round_order: int = 3,
                            event: str | None = None, as_of=None) -> dict:
        """Grouped local model sensitivities plus the facts that produced them.

        Each signed value is ``P(A) - P(A with that input group neutralised)`` under
        the actual calibrated ensemble. It is model evidence, not a causal explanation;
        groups interact and their values are deliberately not presented as additive.
        """
        row = self._feature_dict(
            a, b, surface, best_of, indoor, tier_k, round_order,
            event=event, as_of=as_of,
        )
        elo, srv, ctx = self._states_for(a, b)
        frame = pd.DataFrame([[row[c] for c in FEATURES]], columns=FEATURES)
        base = float(self.iso.predict(self.clf.predict_proba(frame)[:, 1])[0])
        ref = np.datetime64(pd.Timestamp(
            as_of if as_of is not None else elo.last_date).to_datetime64())

        def days_since(name: str) -> float | None:
            last = elo.last_played.get(name)
            return max(0.0, float((ref - last) / np.timedelta64(1, "D"))) if last is not None else None

        h2a, h2b = ctx.record(a, b)
        h2sa, h2sb = ctx.record_surface(a, b, surface)
        workload = getattr(ctx, "workload", None)
        work_a = float(workload(a, ref, self._fp.fatigue_window_days)) if workload else None
        work_b = float(workload(b, ref, self._fp.fatigue_window_days)) if workload else None
        home = self._home_context(a, b, event, ref)
        profiles = getattr(self, "_style_profiles_cache", None)
        if profiles is None:
            profiles = build_profiles(self.tour)
            self._style_profiles_cache = profiles
        profile_a, profile_b = profiles.get(name_key(a)), profiles.get(name_key(b))
        contrasts = []
        if profile_a and profile_b:
            for key in STYLE_FEATURES:
                va, vb = profile_a.get(key), profile_b.get(key)
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)) \
                        and np.isfinite(va) and np.isfinite(vb):
                    contrasts.append({"key": key, "a": round(float(va), 4),
                                      "b": round(float(vb), 4),
                                      "diff": round(float(va) - float(vb), 4)})
            contrasts.sort(key=lambda item: (-abs(item["diff"]), item["key"]))

        facts = {
            "surfaceElo": {
                "surface": surface,
                "a": round(float(elo.blended(a, surface)), 1),
                "b": round(float(elo.blended(b, surface)), 1),
                "gap": round(float(row["elo_diff"]), 1),
            },
            "serveReturn": {
                "pointProbabilityA": round(self._prob_from_logit(row["logit_p_point"]), 4),
                "serveEdge": round(float(row["serve_skill_diff"]), 4),
                "returnEdge": round(float(row["return_skill_diff"]), 4),
            },
            "form": {
                "form90A": round(float(elo.form_delta(a, ref)), 2),
                "form90B": round(float(elo.form_delta(b, ref)), 2),
                "recentWinRateA": round(float(ctx.winrate10(a)), 3),
                "recentWinRateB": round(float(ctx.winrate10(b)), 3),
            },
            "rest": {
                "daysSinceA": round(days_since(a), 1) if days_since(a) is not None else None,
                "daysSinceB": round(days_since(b), 1) if days_since(b) is not None else None,
                "workloadA": round(work_a, 1) if work_a is not None else None,
                "workloadB": round(work_b, 1) if work_b is not None else None,
            },
            "home": home,
            "h2h": {
                "winsA": int(h2a), "winsB": int(h2b),
                "surfaceWinsA": int(h2sa), "surfaceWinsB": int(h2sb),
            },
            "style": {"contrasts": contrasts[:3]},
        }
        available = {
            "surfaceElo": True,
            "serveReturn": True,
            "form": True,
            "rest": days_since(a) is not None and days_since(b) is not None,
            "home": bool(home["available"]),
            "h2h": (h2a + h2b) > 0,
            "style": bool(row["has_style"] and contrasts),
        }
        signals = []
        for key, columns in EVIDENCE_GROUPS.items():
            neutral = frame.copy()
            neutral.loc[:, list(columns)] = 0.0
            without = float(self.iso.predict(self.clf.predict_proba(neutral)[:, 1])[0])
            delta_pp = (base - without) * 100.0
            signals.append({
                "key": key,
                "available": bool(available[key]),
                "supports": a if delta_pp > 0.005 else b if delta_pp < -0.005 else None,
                "impactPp": round(delta_pp, 2),
                "facts": facts[key],
            })
        signals.sort(key=lambda item: (-abs(item["impactPp"]) if item["available"] else 1.0,
                                       item["key"]))
        return {
            "schema": "evidence-v1",
            "playerA": a, "playerB": b, "asOf": str(pd.Timestamp(ref).date()),
            "probabilityA": round(base, 4),
            "signals": signals,
            "note": "Grouped model sensitivity; evidence, not causation; groups need not add up.",
        }

    def prediction_matrices(self, players: list, surface: str = "Hard", best_of: int = 3,
                            indoor: bool = False, tier_k: float = 1.0,
                            round_order: int = 3, event: str | None = None, as_of=None):
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
                                               indoor, tier_k, round_order, event=event,
                                               as_of=as_of))
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

    def prediction_evidence_matrices(self, players: list, surface: str = "Hard",
                                     best_of: int = 3, indoor: bool = False,
                                     tier_k: float = 1.0, round_order: int = 3,
                                     event: str | None = None, as_of=None) -> dict:
        """Batched signed group sensitivities for the static arbitrary-pair predictor."""
        n = len(players)
        effects = {key: np.zeros((n, n), dtype=float) for key in EVIDENCE_GROUPS}
        availability = {key: np.zeros((n, n), dtype=float) for key in EVIDENCE_GROUPS}
        if n < 2:
            return {"effects": effects, "available": availability}
        ii, jj, rows = [], [], []
        for i in range(n):
            for j in range(i + 1, n):
                rows.append(self._feature_dict(
                    players[i], players[j], surface, best_of, indoor, tier_k,
                    round_order, event=event, as_of=as_of,
                ))
                ii.append(i)
                jj.append(j)
        frame = pd.DataFrame(rows, columns=FEATURES)
        base = self.iso.predict(self.clf.predict_proba(frame)[:, 1])
        ia, ja = np.asarray(ii), np.asarray(jj)
        for key, columns in EVIDENCE_GROUPS.items():
            neutral = frame.copy()
            neutral.loc[:, list(columns)] = 0.0
            without = self.iso.predict(self.clf.predict_proba(neutral)[:, 1])
            delta = np.asarray(base) - np.asarray(without)
            effects[key][ia, ja] = delta
            effects[key][ja, ia] = -delta
            if key == "style":
                avail = frame["has_style"].to_numpy(dtype=float)
            elif key == "h2h":
                avail = (frame["log1p_h2h_total"].to_numpy() > 0).astype(float)
            elif key == "home":
                avail = np.full(len(frame), float(bool(event)))
            else:
                avail = np.ones(len(frame), dtype=float)
            availability[key][ia, ja] = avail
            availability[key][ja, ia] = avail
        return {"effects": effects, "available": availability}

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
        from .artifact import save_predictor_artifact

        path = path or predictor_path(self.tour)
        save_predictor_artifact(self, path)

    @staticmethod
    def load(tour: str = "atp", path=None) -> TennisPredictor:
        from .artifact import load_predictor_artifact

        path = path or predictor_path(tour)
        return load_predictor_artifact(path, tour)


def fit_predictor(tour: str = "atp", save: bool = True) -> TennisPredictor:
    """Build states + train the production combiner, returning a ready predictor."""
    from .train import xgb_params_for
    threshold = WTA_DUAL_STATE_GATE_THRESHOLD if tour == "wta" else None
    dual = None
    if threshold is not None:
        main_df = load_matches(tour, include_lower=False)
        enriched_df = load_matches(tour, include_lower=True)
        dual = build_dual_state_inputs(main_df, enriched_df, tour=tour)
        feat, elo, srv, ctx, meta = (
            dual.base_features, dual.elo, dual.srv, dual.ctx, dual.meta)
    else:
        feat, elo, srv, ctx, meta = build_predictor_inputs(tour=tour)
    clf, iso, _ = train_final(feat, xgb_overrides=xgb_params_for(tour))
    pred = TennisPredictor(
        clf, iso, elo, srv, ctx, meta, tour=tour,
        lower_elo=dual.lower_elo if dual else None,
        lower_srv=dual.lower_srv if dual else None,
        lower_ctx=dual.lower_ctx if dual else None,
        dual_state_threshold=threshold,
    )
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
