"""Walk the match history chronologically and maintain Elo ratings.

Produces two things from a single pass:
  - RatingState: final overall + per-surface ratings, match counts, last-played dates
  - a per-match feature frame of PRE-match ratings (computed before each update, so it
    is leakage-free) — reused by the backtest and the XGBoost feature builder.

Surface ratings are seeded from a player's current overall rating the first time they
appear on a surface, so a clay debut doesn't drag a strong player down to 1500.

The walk is fully parameterized by EloParams (see ratings/elo.py); the state carries
its params so prediction-time blending always matches how the ratings were built.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import DEFAULT_RATING, SURFACES, USE_MOV
from .elo import DEFAULT_PARAMS, EloParams, dynamic_k, expected_score, mov_multiplier, surface_k

_DAY = np.timedelta64(1, "D")


def _form_keep_days(params: EloParams) -> float:
    """Snapshot retention for the form feature: 4/3 of the window (>=120d) so the
    delta always finds a snapshot at least form_days old."""
    return max(120.0, getattr(params, "form_days", 90.0) * 4.0 / 3.0)


@dataclass
class RatingState:
    """Mutable rating store, advanced one match at a time."""

    params: EloParams = DEFAULT_PARAMS
    overall: dict = field(default_factory=dict)
    surface: dict = field(default_factory=lambda: {s: {} for s in SURFACES})
    n: dict = field(default_factory=dict)                 # career match counts
    n_surface: dict = field(default_factory=lambda: {s: {} for s in SURFACES})
    last_played: dict = field(default_factory=dict)
    history: dict = field(default_factory=dict)           # name -> [(month, elo)] monthly
    _hist_month: dict = field(default_factory=dict)
    _form: dict = field(default_factory=dict)             # name -> [(date, elo)] recent
    last_date = None

    # -- reads --------------------------------------------------------------
    def elo(self, name: str) -> float:
        return self.overall.get(name, DEFAULT_RATING)

    def surface_elo(self, name: str, surf: str) -> float:
        """Surface rating, seeded from overall on first appearance on that surface."""
        s = self.surface.get(surf, {})
        return s[name] if name in s else self.elo(name)

    @property
    def _params(self) -> EloParams:
        # tolerate RatingState pickles from before the params refactor (quick runs
        # load predictor.pkl built by an older full run)
        return getattr(self, "params", None) or DEFAULT_PARAMS

    def blended(self, name: str, surf: str) -> float:
        p = self._params
        b = p.surface_blend
        n50 = getattr(p, "blend_n50", 0.0)
        if n50 > 0:      # adaptive: debutants lean on overall, veterans on surface
            ns = self.n_surface.get(surf, {}).get(name, 0)
            b *= ns / (ns + n50)
        return (1.0 - b) * self.elo(name) + b * self.surface_elo(name, surf)

    def win_prob(self, a: str, b: str, surf: str, best_of: int = 3) -> float:
        """Blended, surface-aware win probability of A over B."""
        ds = self._params.bo5_scale if best_of == 5 else 1.0
        return expected_score(self.blended(a, surf), self.blended(b, surf),
                              self._params, diff_scale=ds)

    def form_delta(self, name: str, asof, days: float | None = None) -> float:
        """Overall-Elo change vs ~form_days ago (0 if no snapshot in the window).

        `days=None` reads the state's own params, so inference always matches how
        the walk recorded w_form90/l_form90 (old pickles fall back to 90)."""
        hist = getattr(self, "_form", {}).get(name)
        if not hist:
            return 0.0
        if days is None:
            days = getattr(self._params, "form_days", 90.0)
        cutoff = asof - days * _DAY
        past = None
        for d, r in hist:
            if d <= cutoff:
                past = r
            else:
                break
        return 0.0 if past is None else self.elo(name) - past


def run_elo(df: pd.DataFrame, use_mov: bool | None = None,
            params: EloParams | None = None) -> tuple[RatingState, pd.DataFrame]:
    """Single chronological pass. `df` must be cleaned + chronologically sorted.

    Returns (final RatingState, per-match pre-match feature frame aligned to df.index).
    """
    if use_mov is None:
        use_mov = USE_MOV
    p = params or DEFAULT_PARAMS
    st = RatingState(params=p)
    blend = p.surface_blend
    form_keep = _form_keep_days(p)
    xsurf = getattr(p, "xsurf", 0.0)
    blend_n50 = getattr(p, "blend_n50", 0.0)
    home_adv = getattr(p, "home_adv", 0.0)

    n = len(df)
    # Pre-allocate output columns (winner/loser oriented, pre-match values).
    cols = ["w_elo", "l_elo", "w_selo", "l_selo", "w_belo", "l_belo",
            "w_n", "l_n", "w_sn", "l_sn", "p_overall", "p_surface", "p_blend",
            "w_form90", "l_form90"]
    out = {c: np.empty(n, dtype=float) for c in cols}

    winners = df["winner_name"].to_numpy()
    losers = df["loser_name"].to_numpy()
    surfs = df["surface_b"].to_numpy()
    tier_ks = df["tier_k"].to_numpy()
    gdiffs = df["game_diff"].to_numpy()
    completed = df["completed"].to_numpy()
    walkovers = df["walkover"].to_numpy() if "walkover" in df else np.zeros(n, dtype=bool)
    best_ofs = (pd.to_numeric(df["best_of"], errors="coerce").fillna(3).to_numpy()
                if "best_of" in df else np.full(n, 3))
    dates = df["date"].to_numpy()
    months = dates.astype("datetime64[M]")

    # W2c home advantage: rating bonus for playing in your own country. Flags are
    # precomputed once (host from tournament name + year via data/geo.py).
    if home_adv > 0 and "tourney_name" in df and "winner_ioc" in df:
        from ..data.geo import IOC_ALIAS, host_ioc
        yrs = df["date"].dt.year.to_numpy()
        tnames = df["tourney_name"].to_numpy()
        _tour = str(df["tour"].iloc[0]) if "tour" in df and len(df) else None
        wio = df["winner_ioc"].map(lambda x: IOC_ALIAS.get(x, x)).to_numpy()
        lio = df["loser_ioc"].map(lambda x: IOC_ALIAS.get(x, x)).to_numpy()
        host = [host_ioc(nm, int(y), _tour) if isinstance(nm, str) else None
                for nm, y in zip(tnames, yrs)]
        w_hadv = np.array([home_adv if (h is not None and h == x) else 0.0
                           for h, x in zip(host, wio)])
        l_hadv = np.array([home_adv if (h is not None and h == x) else 0.0
                           for h, x in zip(host, lio)])
    else:
        w_hadv = l_hadv = np.zeros(n)

    for i in range(n):
        w, l, s = winners[i], losers[i], surfs[i]

        rw, rl = st.elo(w), st.elo(l)
        sw, sl = st.surface_elo(w, s), st.surface_elo(l, s)
        nw, nl = st.n.get(w, 0), st.n.get(l, 0)
        nsw, nsl = st.n_surface[s].get(w, 0), st.n_surface[s].get(l, 0)
        if blend_n50 > 0:   # adaptive blend, mirrored by RatingState.blended
            b_w = blend * nsw / (nsw + blend_n50)
            b_l = blend * nsl / (nsl + blend_n50)
        else:
            b_w = b_l = blend
        bw, bl = (1 - b_w) * rw + b_w * sw, (1 - b_l) * rl + b_l * sl
        ds = p.bo5_scale if best_ofs[i] == 5 else 1.0

        # --- record pre-match features (no leakage) ---
        # recorded probabilities stay VENUE-FREE so logit_p_blend keeps
        # train/inference parity (RatingState.win_prob knows no venue); the home
        # bonus enters only the UPDATE expectations below, de-biasing the ratings
        out["w_elo"][i], out["l_elo"][i] = rw, rl
        out["w_selo"][i], out["l_selo"][i] = sw, sl
        out["w_belo"][i], out["l_belo"][i] = bw, bl
        out["w_n"][i], out["l_n"][i] = nw, nl
        out["w_sn"][i], out["l_sn"][i] = nsw, nsl
        out["p_overall"][i] = expected_score(rw, rl, p, diff_scale=ds)
        out["p_surface"][i] = expected_score(sw, sl, p, diff_scale=ds)
        out["p_blend"][i] = expected_score(bw, bl, p, diff_scale=ds)
        out["w_form90"][i] = st.form_delta(w, dates[i])
        out["l_form90"][i] = st.form_delta(l, dates[i])

        # --- update ---
        if p.skip_walkovers and walkovers[i]:
            continue                       # nobody hit a ball: ratings, counts, dates untouched

        mov = mov_multiplier(gdiffs[i], p) if (use_mov and completed[i]) else 1.0
        tk = tier_ks[i]
        if not completed[i] and not walkovers[i]:
            tk *= p.ret_k_mult             # retirement/default: noisy, down-weighted

        kw, kl = dynamic_k(nw, p) * tk, dynamic_k(nl, p) * tk
        skw, skl = surface_k(nsw, p) * tk, surface_k(nsl, p) * tk
        if p.inact_days > 0:               # first match back from a long layoff moves fast

            def _boost(name: str, asof=dates[i]) -> float:   # bind the date, not the loop var
                last = st.last_played.get(name)
                if last is None:
                    return 1.0
                gap = (asof - last) / _DAY
                if gap <= p.inact_days:
                    return 1.0
                return 1.0 + p.inact_boost * min(gap / 365.0, 2.0)

            bw_, bl_ = _boost(w), _boost(l)
            kw, skw = kw * bw_, skw * bw_
            kl, skl = kl * bl_, skl * bl_

        # update expectation shares the (Bo5-scaled) recorded probabilities —
        # except under home_adv, where the expectation is venue-adjusted so a
        # home win moves the rating less (ratings become venue-neutral)
        hw, hl = w_hadv[i], l_hadv[i]
        if hw != 0.0 or hl != 0.0:
            e_overall = expected_score(rw + hw, rl + hl, p, diff_scale=ds)
            e_surf = expected_score(sw + hw, sl + hl, p, diff_scale=ds)
        else:
            e_overall = out["p_overall"][i]
            e_surf = out["p_surface"][i]
        st.overall[w] = rw + kw * mov * (1.0 - e_overall)
        st.overall[l] = rl + kl * mov * (0.0 - (1.0 - e_overall))
        st.surface[s][w] = sw + skw * mov * (1.0 - e_surf)
        st.surface[s][l] = sl + skl * mov * (0.0 - (1.0 - e_surf))
        if xsurf > 0:                      # cross-surface transfer (E2): other
            dw = xsurf * skw * mov * (1.0 - e_surf)   # surfaces get a fraction of
            dl = xsurf * skl * mov * (1.0 - e_surf)   # the surface-s update
            for s2 in SURFACES:
                if s2 != s:
                    st.surface[s2][w] = st.surface[s2].get(w, rw) + dw
                    st.surface[s2][l] = st.surface[s2].get(l, rl) - dl

        st.n[w], st.n[l] = nw + 1, nl + 1
        st.n_surface[s][w], st.n_surface[s][l] = nsw + 1, nsl + 1
        st.last_played[w] = st.last_played[l] = dates[i]

        # rolling snapshots: monthly (trends/profiles) + recent (form_days feature)
        m = months[i]
        cutoff = dates[i] - form_keep * _DAY
        for nm, rating in ((w, st.overall[w]), (l, st.overall[l])):
            if st._hist_month.get(nm) != m:
                st._hist_month[nm] = m
                st.history.setdefault(nm, []).append((str(m), round(rating)))
            f = st._form.setdefault(nm, [])
            f.append((dates[i], rating))
            while f and f[0][0] < cutoff:
                f.pop(0)

    st.last_date = dates[-1] if n else None
    feats = pd.DataFrame(out, index=df.index)
    feats["elo_diff"] = feats["w_belo"] - feats["l_belo"]
    return st, feats


def build_ratings(df: pd.DataFrame) -> RatingState:
    """Convenience: just the final ratings."""
    return run_elo(df)[0]


def leaderboard(st: RatingState, surface: str | None = None, top: int = 20,
                active_days: int = 365) -> pd.DataFrame:
    """Top active players by overall (or surface-blended) Elo.

    "Active" = played within `active_days` of the most recent match in the data.
    """
    if st.last_date is None:
        return pd.DataFrame()
    cutoff = st.last_date - np.timedelta64(active_days, "D")
    rows = []
    for name, last in st.last_played.items():
        if last < cutoff:
            continue
        rating = st.blended(name, surface) if surface else st.elo(name)
        rows.append((name, rating, st.elo(name),
                     st.surface_elo(name, surface) if surface else np.nan, st.n.get(name, 0)))
    lb = pd.DataFrame(rows, columns=["player", "rating", "overall", "surface_elo", "matches"])
    return lb.sort_values("rating", ascending=False).head(top).reset_index(drop=True)


if __name__ == "__main__":
    from ..data.results import load_matches
    df = load_matches()
    st, feats = run_elo(df)
    print("=== Top 20 (overall, active last 12 mo) ===")
    print(leaderboard(st, top=20).to_string(index=False))
    for surf in SURFACES:
        print(f"\n=== Top 10 {surf} (blended) ===")
        print(leaderboard(st, surface=surf, top=10)[["player", "rating", "matches"]].to_string(index=False))
