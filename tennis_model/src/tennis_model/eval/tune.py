"""Offline hyperparameter tuning for the rating walkers (never runs in CI).

Component-level objectives — much cheaper and sharper than retraining the combiner:
  group=elo    log-loss of p_blend   (one run_elo pass per trial, ~5-10 s)
  group=point  log-loss of p_point   (one run_serve_return pass per trial)

Protocol (anti-overfitting):
  * TUNE window: test years 2010-2019 — the only thing the optimizer ever sees.
  * VALIDATION window: 2020-latest — evaluated once per group via --validate on the
    top configs; adopt only if tune improves AND validation does not regress by more
    than one paired standard error, on BOTH tours.
  * Adopt round plateau-center values by hand-editing config.py (the dataclass
    defaults read from config, so a single edit re-tunes production).

Uses Optuna if installed (pip install optuna — resumable SQLite studies under
data/output/tuning/), else falls back to seeded random search.

Run:
  PYTHONPATH=src python -m tennis_model.eval.tune --tour atp --group elo --trials 400
  PYTHONPATH=src python -m tennis_model.eval.tune --tour atp --group elo --validate
"""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pandas as pd

from ..config import OUTPUT_DIR, TIER_K_MULT
from ..data.results import load_matches
from ..points.serve_return import ServeReturnParams, run_serve_return
from ..ratings.build import run_elo
from ..ratings.elo import EloParams

TUNE_YEARS = (2010, 2019)
VAL_START = 2020
MIN_SRV_PTS = 100          # point objective: both players need a real serve sample

TUNE_DIR = OUTPUT_DIR / "tuning"

# Tier multipliers are tuned through two anchors (slam & challenger); the middle
# tiers interpolate by their current position between the anchors — tuning all 8
# independently is the fastest way to overfit the backtest.
_T_LO, _T_HI = min(TIER_K_MULT.values()), max(TIER_K_MULT.values())


def _tier_map(gs_mult: float, chall_mult: float) -> dict:
    return {name: chall_mult + (v - _T_LO) / (_T_HI - _T_LO) * (gs_mult - chall_mult)
            for name, v in TIER_K_MULT.items()}


def _logloss(p: np.ndarray) -> float:
    return float(-np.mean(np.log(np.clip(p, 1e-12, None))))


class Objective:
    """Loads a tour's matches once; each __call__ is one walker pass + log-loss."""

    def __init__(self, tour: str, group: str, years: tuple[int, int] = TUNE_YEARS):
        self.tour, self.group = tour, group
        self.df = load_matches(tour)
        self.years = years
        yr = self.df["date"].dt.year
        self.mask = (self.df["completed"].to_numpy()
                     & (yr >= years[0]).to_numpy() & (yr <= years[1]).to_numpy())

    # -- parameter spaces ----------------------------------------------------
    def suggest(self, trial) -> dict:
        s = trial.suggest_float
        if self.group == "elo":
            return dict(
                k_scale=s("k_scale", 30, 400, log=True),
                k_offset=s("k_offset", 1, 30),
                k_shape=s("k_shape", 0.02, 0.60),
                surface_k_scale=s("surface_k_scale", 30, 300, log=True),
                surface_k_shape=s("surface_k_shape", 0.02, 0.60),
                surface_blend=s("surface_blend", 0.20, 0.80),
                mov_factor=s("mov_factor", 0.0, 0.60),
                mov_cap=s("mov_cap", 1.2, 2.5),
                ret_k_mult=s("ret_k_mult", 0.0, 1.0),
                inact_days=s("inact_days", 60, 540),
                inact_boost=s("inact_boost", 0.0, 1.5),
                bo5_scale=s("bo5_scale", 1.0, 1.3),
                gs_mult=s("gs_mult", 0.9, 1.3),
                chall_mult=s("chall_mult", 0.6, 1.1),
            )
        return dict(
            form_halflife_days=s("form_halflife_days", 60, 1500, log=True),
            serve_shrinkage_points=s("serve_shrinkage_points", 50, 2000, log=True),
            surface_serve_shrinkage=s("surface_serve_shrinkage", 30, 3000, log=True),
        )

    # -- evaluation ----------------------------------------------------------
    def evaluate(self, cfg: dict, mask: np.ndarray | None = None) -> float:
        from ..points.serve_return import sr_params_for
        from ..ratings.elo import params_for
        m = self.mask if mask is None else mask
        if self.group == "elo":
            cfg = dict(cfg)
            tiers = _tier_map(cfg.pop("gs_mult", None) or TIER_K_MULT["grand_slam"],
                              cfg.pop("chall_mult", None) or TIER_K_MULT["challenger"])
            df = self.df.copy()
            df["tier_k"] = df["tier"].map(tiers).fillna(tiers["atp250"])
            # skip_walkovers measured slightly WORSE on both tours (a withdrawal is
            # weak evidence of injury/decline), so the walk keeps updating on them
            params = replace(params_for(self.tour), **cfg)
            _, feats = run_elo(df, params=params)
            return _logloss(feats["p_blend"].to_numpy()[m])
        params = replace(sr_params_for(self.tour), **cfg)
        _, feats = run_serve_return(self.df, params=params)
        ok = m & (feats["w_srv_pts"].to_numpy() >= MIN_SRV_PTS) \
               & (feats["l_srv_pts"].to_numpy() >= MIN_SRV_PTS)
        return _logloss(feats["p_point"].to_numpy()[ok])

    def val_mask(self) -> np.ndarray:
        yr = self.df["date"].dt.year
        base = self.df["completed"].to_numpy() & (yr >= VAL_START).to_numpy()
        if self.group != "point":
            return base
        return base  # srv-pts filter applied inside evaluate for the point group

    def baseline(self) -> dict:
        """Current adopted config's scores on tune and validation windows."""
        cfg = {}
        if self.group == "elo":
            from ..config import TIER_ANCHORS
            gs, ch = TIER_ANCHORS.get(self.tour) or (TIER_K_MULT["grand_slam"],
                                                     TIER_K_MULT["challenger"])
            cfg = dict(gs_mult=gs, chall_mult=ch)
        return {"tune": self.evaluate(dict(cfg)),
                "val": self.evaluate(dict(cfg), mask=self.val_mask())}


def tune(tour: str, group: str, trials: int, seed: int = 7, tag: str = "") -> None:
    obj = Objective(tour, group)
    TUNE_DIR.mkdir(parents=True, exist_ok=True)
    base = obj.baseline()
    print(f"[{tour}/{group}] baseline: tune={base['tune']:.5f}  val={base['val']:.5f}")
    name = f"{tour}_{group}{tag}"

    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(
            study_name=name,
            storage=f"sqlite:///{TUNE_DIR / f'{name}.db'}",
            load_if_exists=True, direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=seed),
        )

        def _obj(trial):
            cfg = obj.suggest(trial)
            ll = obj.evaluate(cfg)
            if trial.number % 20 == 0:
                print(f"  trial {trial.number}: {ll:.5f} (best {study.best_value:.5f})"
                      if trial.number else f"  trial 0: {ll:.5f}")
            return ll

        study.optimize(_obj, n_trials=trials)
        print(f"[{tour}/{group}] best tune logloss: {study.best_value:.5f} "
              f"(baseline {base['tune']:.5f})")
        print(json.dumps(study.best_params, indent=2))
    except ImportError:
        print("optuna not installed -> seeded random search")
        rng = np.random.default_rng(seed)

        class _T:  # minimal trial shim for suggest()
            def suggest_float(self, name, lo, hi, log=False):
                return float(np.exp(rng.uniform(np.log(lo), np.log(hi))) if log
                             else rng.uniform(lo, hi))

        best, best_cfg = np.inf, None
        for i in range(trials):
            cfg = obj.suggest(_T())
            ll = obj.evaluate(cfg)
            if ll < best:
                best, best_cfg = ll, cfg
                print(f"  trial {i}: NEW BEST {ll:.5f}")
        print(f"[{tour}/{group}] best tune logloss: {best:.5f} (baseline {base['tune']:.5f})")
        print(json.dumps(best_cfg, indent=2))


def validate(tour: str, group: str, top: int = 5, tag: str = "") -> None:
    """Score the study's top configs on the untouched validation window."""
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    name = f"{tour}_{group}{tag}"
    study = optuna.load_study(study_name=name,
                              storage=f"sqlite:///{TUNE_DIR / f'{name}.db'}")
    obj = Objective(tour, group)
    base = obj.baseline()
    print(f"[{tour}/{group}] baseline: tune={base['tune']:.5f}  val={base['val']:.5f}")
    done = [t for t in study.trials if t.value is not None]
    for t in sorted(done, key=lambda t: t.value)[:top]:
        val = obj.evaluate(dict(t.params), mask=obj.val_mask())
        print(f"  #{t.number}: tune={t.value:.5f}  val={val:.5f}  "
              f"d_tune={base['tune'] - t.value:+.5f}  d_val={base['val'] - val:+.5f}")
        print(f"    {json.dumps({k: round(v, 4) for k, v in t.params.items()})}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="atp", choices=["atp", "wta"])
    ap.add_argument("--group", default="elo", choices=["elo", "point"])
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tag", default="", help="study-name suffix (e.g. _wide)")
    args = ap.parse_args()
    if args.validate:
        validate(args.tour, args.group, tag=args.tag)
    else:
        tune(args.tour, args.group, args.trials, seed=args.seed, tag=args.tag)
