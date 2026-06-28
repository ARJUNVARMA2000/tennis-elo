"""Per-player serve & return skill — surface-specific and opponent-adjusted.

For every match we know each player's service-points-won % and, from the opponent's
serve, their return-points-won %. We track time-decayed skill at two levels:

  * **global** skill, shrunk toward the tour league average, and
  * **per-surface** skill, shrunk toward the player's *own global* skill (a two-level
    hierarchical prior), so a clay specialist's grass rating doesn't overreact to a
    handful of grass matches.

Both are **opponent-adjusted** (strength-of-schedule): when we ingest a match we shift
the credited serve%/return% by the opponent's current return/serve skill, so dominating
an elite returner counts more than the same numbers against a weak one. All estimates
use only past matches, so the walk is leakage-free.

A match on surface *s* gives
    p(A serving) = base[s] + serve_skill_A(s) - return_skill_B(s)
which feeds the hierarchical Markov model for the match probability. League and surface
baselines are computed from the data, so the model is tour-agnostic (ATP ~0.64, WTA ~0.56).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import (
    FORM_HALFLIFE_DAYS,
    SERVE_SHRINKAGE_POINTS,
    SURFACE_SERVE_SHRINKAGE,
    SURFACES,
)
from .markov import P_CLIP, match_win_prob

_DAY = np.timedelta64(1, "D")


def serve_averages(df: pd.DataFrame) -> tuple[float, dict]:
    """League-average service-points-won overall and per surface (computed from data)."""
    s = df[df["has_stats"]]
    served = s["w_svpt"] + s["l_svpt"]
    won = s["w_1stWon"] + s["w_2ndWon"] + s["l_1stWon"] + s["l_2ndWon"]
    overall = float(won.sum() / served.sum()) if served.sum() else 0.62
    base = {}
    for surf in SURFACES:
        m = s["surface_b"] == surf
        base[surf] = float(won[m].sum() / served[m].sum()) if m.any() else overall
    return overall, base


@dataclass
class ServeReturnState:
    """Time-decayed, opponent-adjusted serve/return accumulators per player."""

    avg: float = 0.62                                    # league serve-points-won
    base: dict = field(default_factory=dict)             # surface -> serve%
    # global accumulators
    gsw: dict = field(default_factory=dict); gsp: dict = field(default_factory=dict)
    grw: dict = field(default_factory=dict); grp: dict = field(default_factory=dict)
    # per-surface accumulators (surface -> player -> value)
    ssw: dict = field(default_factory=dict); ssp: dict = field(default_factory=dict)
    srw: dict = field(default_factory=dict); srp: dict = field(default_factory=dict)
    t_last: dict = field(default_factory=dict)

    def __post_init__(self):
        for d in (self.ssw, self.ssp, self.srw, self.srp):
            for s in SURFACES:
                d.setdefault(s, {})

    @property
    def avg_ret(self) -> float:
        return 1.0 - self.avg

    def _decay_to(self, name: str, t) -> None:
        prev = self.t_last.get(name)
        if prev is not None:
            dt = (t - prev) / _DAY
            if dt > 0:
                f = 0.5 ** (dt / FORM_HALFLIFE_DAYS)
                for d in (self.gsw, self.gsp, self.grw, self.grp):
                    if name in d:
                        d[name] *= f
                for dd in (self.ssw, self.ssp, self.srw, self.srp):
                    for s in SURFACES:
                        if name in dd[s]:
                            dd[s][name] *= f
        self.t_last[name] = t

    # -- skills -------------------------------------------------------------
    def global_serve_skill(self, name: str) -> float:
        sp = self.gsp.get(name, 0.0)
        return (self.gsw.get(name, 0.0) + self.avg * SERVE_SHRINKAGE_POINTS) / (sp + SERVE_SHRINKAGE_POINTS) - self.avg

    def global_return_skill(self, name: str) -> float:
        rp = self.grp.get(name, 0.0)
        return (self.grw.get(name, 0.0) + self.avg_ret * SERVE_SHRINKAGE_POINTS) / (rp + SERVE_SHRINKAGE_POINTS) - self.avg_ret

    def serve_skill(self, name: str, surf: str | None = None) -> float:
        """Surface-specific serve skill (relative to the surface baseline), shrunk
        toward the player's global skill. Falls back to global when surf is None."""
        if surf is None or surf not in self.base:
            return self.global_serve_skill(name)
        bs = self.base[surf]
        prior = bs + self.global_serve_skill(name)               # player's global level, on this surface
        sp = self.ssp[surf].get(name, 0.0)
        return (self.ssw[surf].get(name, 0.0) + prior * SURFACE_SERVE_SHRINKAGE) / (sp + SURFACE_SERVE_SHRINKAGE) - bs

    def return_skill(self, name: str, surf: str | None = None) -> float:
        if surf is None or surf not in self.base:
            return self.global_return_skill(name)
        br = 1.0 - self.base[surf]
        prior = br + self.global_return_skill(name)
        rp = self.srp[surf].get(name, 0.0)
        return (self.srw[surf].get(name, 0.0) + prior * SURFACE_SERVE_SHRINKAGE) / (rp + SURFACE_SERVE_SHRINKAGE) - br

    def point_probs(self, a: str, b: str, surf: str) -> tuple[float, float]:
        base = self.base.get(surf, self.avg)
        pa = base + self.serve_skill(a, surf) - self.return_skill(b, surf)
        pb = base + self.serve_skill(b, surf) - self.return_skill(a, surf)
        clip = lambda x: min(max(x, P_CLIP[0]), P_CLIP[1])
        return clip(pa), clip(pb)

    def match_prob(self, a: str, b: str, surf: str, best_of: int = 3) -> float:
        pa, pb = self.point_probs(a, b, surf)
        return match_win_prob(pa, pb, best_of)

    # -- updates ------------------------------------------------------------
    def _add(self, name: str, surf: str, svpt: float, adj_spw: float, rpt: float, adj_rpw: float) -> None:
        self.gsw[name] = self.gsw.get(name, 0.0) + adj_spw * svpt
        self.gsp[name] = self.gsp.get(name, 0.0) + svpt
        self.grw[name] = self.grw.get(name, 0.0) + adj_rpw * rpt
        self.grp[name] = self.grp.get(name, 0.0) + rpt
        self.ssw[surf][name] = self.ssw[surf].get(name, 0.0) + adj_spw * svpt
        self.ssp[surf][name] = self.ssp[surf].get(name, 0.0) + svpt
        self.srw[surf][name] = self.srw[surf].get(name, 0.0) + adj_rpw * rpt
        self.srp[surf][name] = self.srp[surf].get(name, 0.0) + rpt


def run_serve_return(df: pd.DataFrame) -> tuple[ServeReturnState, pd.DataFrame]:
    """Chronological pass: record pre-match (surface) skills + point-model probability."""
    avg, base = serve_averages(df)
    st = ServeReturnState(avg=avg, base=base)
    n = len(df)
    cols = ["w_serve_skill", "l_serve_skill", "w_return_skill", "l_return_skill",
            "w_srv_pts", "l_srv_pts", "pa_serve", "pb_serve", "p_point"]
    out = {c: np.empty(n, dtype=float) for c in cols}

    winners = df["winner_name"].to_numpy(); losers = df["loser_name"].to_numpy()
    surfs = df["surface_b"].to_numpy(); dates = df["date"].to_numpy()
    best_of = pd.to_numeric(df["best_of"], errors="coerce").fillna(3).astype(int).to_numpy()
    has_stats = df["has_stats"].to_numpy()
    g = lambda c: pd.to_numeric(df[c], errors="coerce").to_numpy()
    w_svpt, l_svpt = g("w_svpt"), g("l_svpt")
    w_1w, w_2w = g("w_1stWon"), g("w_2ndWon")
    l_1w, l_2w = g("l_1stWon"), g("l_2ndWon")

    for i in range(n):
        w, l, s, t = winners[i], losers[i], surfs[i], dates[i]
        st._decay_to(w, t); st._decay_to(l, t)

        # pre-match skills (surface-specific for prediction; global for SoS adjustment)
        ss_w, ss_l = st.serve_skill(w, s), st.serve_skill(l, s)
        rs_w, rs_l = st.return_skill(w, s), st.return_skill(l, s)
        gss_w, gss_l = st.global_serve_skill(w), st.global_serve_skill(l)
        grs_w, grs_l = st.global_return_skill(w), st.global_return_skill(l)
        b = st.base.get(s, st.avg)
        pa = min(max(b + ss_w - rs_l, P_CLIP[0]), P_CLIP[1])
        pb = min(max(b + ss_l - rs_w, P_CLIP[0]), P_CLIP[1])

        out["w_serve_skill"][i], out["l_serve_skill"][i] = ss_w, ss_l
        out["w_return_skill"][i], out["l_return_skill"][i] = rs_w, rs_l
        out["w_srv_pts"][i], out["l_srv_pts"][i] = st.gsp.get(w, 0.0), st.gsp.get(l, 0.0)
        out["pa_serve"][i], out["pb_serve"][i] = pa, pb
        out["p_point"][i] = match_win_prob(pa, pb, int(best_of[i]))

        if has_stats[i] and w_svpt[i] > 0 and l_svpt[i] > 0:
            wsw, lsw = w_1w[i] + w_2w[i], l_1w[i] + l_2w[i]
            # opponent-adjusted: shift raw % by the opponent's global return/serve skill
            st._add(w, s, w_svpt[i], (wsw / w_svpt[i]) + grs_l,
                    l_svpt[i], ((l_svpt[i] - lsw) / l_svpt[i]) + gss_l)
            st._add(l, s, l_svpt[i], (lsw / l_svpt[i]) + grs_w,
                    w_svpt[i], ((w_svpt[i] - wsw) / w_svpt[i]) + gss_w)

    feats = pd.DataFrame(out, index=df.index)
    feats["serve_skill_diff"] = feats["w_serve_skill"] - feats["l_serve_skill"]
    feats["return_skill_diff"] = feats["w_return_skill"] - feats["l_return_skill"]
    return st, feats


if __name__ == "__main__":
    import sys
    from ..data.results import load_matches
    tour = sys.argv[1] if len(sys.argv) > 1 else "atp"
    df = load_matches(tour)
    st, feats = run_serve_return(df)
    print(f"[{tour}] league serve avg = {st.avg:.3f}; surface base =",
          {k: round(v, 3) for k, v in st.base.items()})
    for p in ["John Isner", "Novak Djokovic", "Rafael Nadal", "Carlos Alcaraz",
              "Aryna Sabalenka", "Iga Swiatek"]:
        if p in st.gsp:
            print(f"{p:18s} serve%={st.avg + st.global_serve_skill(p):.3f}  "
                  f"return%={st.avg_ret + st.global_return_skill(p):.3f}  | "
                  f"grass serve%={st.base.get('Grass', st.avg) + st.serve_skill(p, 'Grass'):.3f}  "
                  f"clay serve%={st.base.get('Clay', st.avg) + st.serve_skill(p, 'Clay'):.3f}")
