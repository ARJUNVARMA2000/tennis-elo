"""Offline hyperparameter tuning for the rating walkers and the combiner (never in CI).

Objectives per group:
  group=elo    log-loss of p_blend     (one run_elo pass per trial, ~5-10 s)
  group=point  log-loss of p_point     (one run_serve_return pass per trial, scored on
                                        a FIXED reference serve-sample mask so every
                                        trial sees identical rows)
  group=xgb    log-loss of p_combiner  (full walk-forward over the tune window per
                                        trial — minutes, run overnight; folds/seeds are
                                        deterministic so trials are match-paired)
  group=feat   log-loss of p_combiner  (FeatureParams + form_days: Elo/context walks
                                        re-run per trial, then a full walk-forward
                                        UNDER the adopted combiner params — the
                                        component-vs-arbiter gap is absent by
                                        construction; ~2-2.5 min/trial)

Protocol (anti-overfitting):
  * TUNE window: test years 2010-2019 — the only thing the optimizer ever sees.
  * VALIDATION window: 2020-latest — evaluated once per group via --validate on the
    top configs; adopt only if tune improves AND validation does not regress by more
    than one paired standard error, on BOTH tours. --validate prints d ± SE from
    per-match paired log-loss vectors.
  * Adopt round plateau-center values by hand-editing config.py (the dataclass
    defaults read from config, so a single edit re-tunes production; xgb values go
    to the _xgb() defaults in model/train.py).

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

from ..config import OUTPUT_DIR, TIER_K_MULT
from ..data.results import load_matches
from ..points.serve_return import run_serve_return
from ..ratings.build import run_elo

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
    """Loads a tour's data once; each evaluation is one walker/backtest pass + log-loss."""

    def __init__(self, tour: str, group: str, years: tuple[int, int] = TUNE_YEARS):
        self.tour, self.group = tour, group
        self.years = years
        if group == "xgb":
            from ..model.features import main_rows
            from ..model.train import load_or_build_features
            # combiner regime = main rows only (A5 ratings-only adoption)
            self.feat = main_rows(load_or_build_features(tour=tour))
            return
        self.df = load_matches(tour)
        yr = self.df["date"].dt.year
        # lower-tier rows (A5) inform every walk but are never SCORED — objectives
        # must stay comparable to the arbiter's main-draw eval set
        main = ((self.df["draw_level"] == "main").to_numpy()
                if "draw_level" in self.df.columns else True)
        self.mask = (self.df["completed"].to_numpy() & main
                     & (yr >= years[0]).to_numpy() & (yr <= years[1]).to_numpy())
        self.vmask = self.df["completed"].to_numpy() & main & (yr >= VAL_START).to_numpy()
        if group == "feat":
            # serve/return params are fixed across trials — run that walk once
            from ..model.train import xgb_params_for
            from ..points.serve_return import run_serve_return, sr_params_for
            _, self.srv_feats = run_serve_return(self.df, params=sr_params_for(tour))
            self.adopted_xgb = xgb_params_for(tour)
        if group == "point":
            # fixed reference serve-sample mask: the srv-pts accumulators DECAY with the
            # trial's halflife, so a per-trial filter scores different trials on
            # different rows (a selection artifact) and breaks match-pairing for d±SE
            from ..points.serve_return import run_serve_return, sr_params_for
            _, ref = run_serve_return(self.df, params=sr_params_for(tour))
            self.ref_srv_ok = ((ref["w_srv_pts"].to_numpy() >= MIN_SRV_PTS)
                               & (ref["l_srv_pts"].to_numpy() >= MIN_SRV_PTS))

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
                # E2 cross-surface transfer; space changed -> fresh --tag required
                xsurf=s("xsurf", 0.0, 0.5),
                # P3 adaptive surface blend (0 = incumbent fixed blend); space
                # changed -> fresh --tag required (`_ablend`)
                blend_n50=s("blend_n50", 0.0, 100.0),
                # W2c Elo home advantage (rating points; 0 = off); space changed
                # again -> `_home` tag
                home_adv=s("home_adv", 0.0, 120.0),
                gs_mult=s("gs_mult", 0.9, 1.3),
                chall_mult=s("chall_mult", 0.6, 1.1),
            )
        if self.group == "xgb":
            return dict(
                learning_rate=s("learning_rate", 0.01, 0.10, log=True),
                max_depth=trial.suggest_int("max_depth", 3, 7),
                # WTA's adopted optimum sat AT the old 50 ceiling; range extended so
                # the bound can't bind again. NOTE: changed range ⇒ fresh --tag
                min_child_weight=s("min_child_weight", 1.0, 400.0, log=True),
                subsample=s("subsample", 0.50, 1.00),
                colsample_bytree=s("colsample_bytree", 0.50, 1.00),
                reg_alpha=s("reg_alpha", 1e-3, 10.0, log=True),
                reg_lambda=s("reg_lambda", 0.03, 30.0, log=True),
                gamma=s("gamma", 1e-4, 5.0, log=True),
            )
        if self.group == "feat":
            return dict(
                fatigue_window_days=s("fatigue_window_days", 3.0, 45.0),
                layoff_days=s("layoff_days", 30.0, 365.0),
                peak_age=s("peak_age", 23.0, 29.0),
                form_days=s("form_days", 30.0, 240.0),
                winrate_window=trial.suggest_int("winrate_window", 5, 30),
            )
        return dict(
            form_halflife_days=s("form_halflife_days", 60, 1500, log=True),
            serve_shrinkage_points=s("serve_shrinkage_points", 50, 2000, log=True),
            # WTA's optimum sat AT the old 3000 ceiling (adopted value == bound), so
            # the range extends to 10k — near-infinite shrinkage = global-only serve.
            # NOTE: a changed range can't resume an old study; use a fresh --tag
            surface_serve_shrinkage=s("surface_serve_shrinkage", 30, 10000, log=True),
            # E3 event-speed baseline; 5e5 ≈ off (a slam accrues ~4e4 pts/year).
            # Space changed -> fresh --tag (`_espd`)
            event_shrinkage=s("event_shrinkage", 200.0, 500000.0, log=True),
        )

    # -- evaluation ----------------------------------------------------------
    def evaluate_vec(self, cfg: dict, window: str = "tune") -> np.ndarray:
        """Per-match -log(p) over the window's FIXED row set (identical rows in
        identical order for every config, so vectors from two configs pair up)."""
        from ..points.serve_return import sr_params_for
        from ..ratings.elo import params_for
        if self.group == "xgb":
            from ..model.train import walk_forward
            overrides = dict(cfg)
            # high cap so the lr x trees frontier is governed by early stopping
            overrides.setdefault("n_estimators", 2000)
            start, end = (self.years if window == "tune"
                          else (VAL_START, int(self.feat["year"].max())))
            # n_bag=1: sweeps search the single fit for speed; gates/arbiters
            # re-score bagged (config.N_BAG) outside the study
            oos = walk_forward(self.feat, start_test=start, end_test=end,
                               xgb_overrides=overrides, verbose=False, n_bag=1)
            return -np.log(np.clip(oos["p_combiner"].to_numpy(), 1e-12, None))
        if self.group == "feat":
            from ..model.features import FeatureParams, _assemble, main_rows, run_context
            from ..model.train import walk_forward
            cfg = dict(cfg)
            elo_p = replace(params_for(self.tour), form_days=cfg.pop("form_days"))
            _, elo = run_elo(self.df, params=elo_p)
            fp = FeatureParams(**cfg)
            _, ctx = run_context(self.df, params=fp)
            feat = main_rows(_assemble(self.df.join(elo).join(self.srv_feats).join(ctx),
                                       params=fp))
            start, end = (self.years if window == "tune"
                          else (VAL_START, int(feat["year"].max())))
            oos = walk_forward(feat, start_test=start, end_test=end,
                               xgb_overrides=self.adopted_xgb, verbose=False, n_bag=1)
            return -np.log(np.clip(oos["p_combiner"].to_numpy(), 1e-12, None))
        m = self.mask if window == "tune" else self.vmask
        if self.group == "elo":
            cfg = dict(cfg)
            gs, ch = cfg.pop("gs_mult", None), cfg.pop("chall_mult", None)
            tiers = _tier_map(TIER_K_MULT["grand_slam"] if gs is None else gs,
                              TIER_K_MULT["challenger"] if ch is None else ch)
            # overwrite tier_k in place — every trial re-assigns the full column, and
            # run_elo only reads, so no copy of the 150k-row frame is needed per trial
            self.df["tier_k"] = self.df["tier"].map(tiers).fillna(tiers["atp250"])
            # skip_walkovers measured slightly WORSE on both tours (a withdrawal is
            # weak evidence of injury/decline), so the walk keeps updating on them
            params = replace(params_for(self.tour), **cfg)
            _, feats = run_elo(self.df, params=params)
            p = feats["p_blend"].to_numpy()[m]
        else:
            params = replace(sr_params_for(self.tour), **cfg)
            _, feats = run_serve_return(self.df, params=params)
            p = feats["p_point"].to_numpy()[m & self.ref_srv_ok]
        return -np.log(np.clip(p, 1e-12, None))

    def evaluate(self, cfg: dict, window: str = "tune") -> float:
        return float(np.mean(self.evaluate_vec(cfg, window)))

    def baseline_cfg(self) -> dict:
        """The currently adopted config, expressed in this group's parameter space."""
        if self.group == "elo":
            from ..config import TIER_ANCHORS
            from ..ratings.elo import params_for
            gs, ch = TIER_ANCHORS.get(self.tour) or (TIER_K_MULT["grand_slam"],
                                                     TIER_K_MULT["challenger"])
            p = params_for(self.tour)
            # the FULL incumbent (not just the tier anchors), so the enqueued TPE
            # anchor trial really is the adopted config
            return dict(k_scale=p.k_scale, k_offset=p.k_offset, k_shape=p.k_shape,
                        surface_k_scale=p.surface_k_scale,
                        surface_k_shape=p.surface_k_shape,
                        surface_blend=p.surface_blend,
                        mov_factor=p.mov_factor, mov_cap=p.mov_cap,
                        ret_k_mult=p.ret_k_mult, inact_days=max(p.inact_days, 60.0),
                        inact_boost=p.inact_boost, bo5_scale=p.bo5_scale,
                        xsurf=p.xsurf, blend_n50=p.blend_n50, home_adv=p.home_adv,
                        gs_mult=gs, chall_mult=ch)
        if self.group == "xgb":
            from ..model.train import xgb_params_for
            return xgb_params_for(self.tour)   # adopted per-tour combiner overrides
        if self.group == "feat":
            from ..model.features import feat_params_for
            from ..ratings.elo import params_for
            fp = feat_params_for(self.tour)
            return dict(fatigue_window_days=fp.fatigue_window_days,
                        layoff_days=fp.layoff_days, peak_age=fp.peak_age,
                        winrate_window=fp.winrate_window,
                        form_days=params_for(self.tour).form_days)
        from ..points.serve_return import sr_params_for
        p = sr_params_for(self.tour)
        return dict(form_halflife_days=p.form_halflife_days,
                    serve_shrinkage_points=p.serve_shrinkage_points,
                    surface_serve_shrinkage=p.surface_serve_shrinkage,
                    event_shrinkage=p.event_shrinkage)

    def baseline(self) -> dict:
        """Current adopted config's scores on tune and validation windows."""
        cfg = self.baseline_cfg()
        return {"tune": self.evaluate(dict(cfg), "tune"),
                "val": self.evaluate(dict(cfg), "val")}


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
        # anchor TPE at the incumbent so the search starts from the adopted config
        anchor = {k: v for k, v in obj.baseline_cfg().items() if k != "n_estimators"}
        if anchor.get("event_shrinkage", 1) <= 0:      # 0 = off, outside the log
            anchor["event_shrinkage"] = 500000.0       # space; ~off within it
        if anchor and not study.trials:
            study.enqueue_trial(anchor)

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

            def suggest_int(self, name, lo, hi, log=False):
                if log:
                    return int(round(np.exp(rng.uniform(np.log(lo), np.log(hi)))))
                return int(rng.integers(lo, hi + 1))

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
    """Score the study's top configs on the untouched validation window.

    Both windows are RE-scored per config (not read from the study) so every number
    comes from the same fixed row set as the baseline, and the adoption gate's
    paired d ± SE is computed from per-match log-loss differences. Gate: d_tune > 0
    AND d_val > -1*SE, on both tours."""
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    name = f"{tour}_{group}{tag}"
    study = optuna.load_study(study_name=name,
                              storage=f"sqlite:///{TUNE_DIR / f'{name}.db'}")
    obj = Objective(tour, group)
    base_tune = obj.evaluate_vec(obj.baseline_cfg(), "tune")
    base_val = obj.evaluate_vec(obj.baseline_cfg(), "val")
    print(f"[{tour}/{group}] baseline: tune={base_tune.mean():.5f}  val={base_val.mean():.5f}")
    done = [t for t in study.trials if t.value is not None]
    for t in sorted(done, key=lambda t: t.value)[:top]:
        tune_vec = obj.evaluate_vec(dict(t.params), "tune")
        val_vec = obj.evaluate_vec(dict(t.params), "val")
        dt, dv = base_tune - tune_vec, base_val - val_vec
        se_t = float(dt.std(ddof=1) / np.sqrt(len(dt)))
        se_v = float(dv.std(ddof=1) / np.sqrt(len(dv)))
        gate = "PASS" if dt.mean() > 0 and dv.mean() > -se_v else "no"
        print(f"  #{t.number}: tune={tune_vec.mean():.5f}  val={val_vec.mean():.5f}  "
              f"d_tune={dt.mean():+.5f}±{se_t:.5f}  d_val={dv.mean():+.5f}±{se_v:.5f}  gate={gate}")
        print(f"    {json.dumps({k: round(v, 4) for k, v in t.params.items()})}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="atp", choices=["atp", "wta"])
    ap.add_argument("--group", default="elo", choices=["elo", "point", "xgb", "feat"])
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--top", type=int, default=5, help="configs to score in --validate")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tag", default="", help="study-name suffix (e.g. _wide)")
    args = ap.parse_args()
    if args.validate:
        validate(args.tour, args.group, top=args.top, tag=args.tag)
    else:
        tune(args.tour, args.group, args.trials, seed=args.seed, tag=args.tag)
