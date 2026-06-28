"""Walk the match history chronologically and maintain Elo ratings.

Produces two things from a single pass:
  - RatingState: final overall + per-surface ratings, match counts, last-played dates
  - a per-match feature frame of PRE-match ratings (computed before each update, so it
    is leakage-free) — reused by the backtest and the XGBoost feature builder.

Surface ratings are seeded from a player's current overall rating the first time they
appear on a surface, so a clay debut doesn't drag a strong player down to 1500.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..config import DEFAULT_RATING, SURFACES, SURFACE_BLEND, USE_MOV
from .elo import dynamic_k, expected_score, mov_multiplier, surface_k


@dataclass
class RatingState:
    """Mutable rating store, advanced one match at a time."""

    overall: dict = field(default_factory=dict)
    surface: dict = field(default_factory=lambda: {s: {} for s in SURFACES})
    n: dict = field(default_factory=dict)                 # career match counts
    n_surface: dict = field(default_factory=lambda: {s: {} for s in SURFACES})
    last_played: dict = field(default_factory=dict)
    history: dict = field(default_factory=dict)           # name -> [(month, elo)] monthly
    _hist_month: dict = field(default_factory=dict)
    last_date = None

    # -- reads --------------------------------------------------------------
    def elo(self, name: str) -> float:
        return self.overall.get(name, DEFAULT_RATING)

    def surface_elo(self, name: str, surf: str) -> float:
        """Surface rating, seeded from overall on first appearance on that surface."""
        s = self.surface.get(surf, {})
        return s[name] if name in s else self.elo(name)

    def blended(self, name: str, surf: str) -> float:
        return (1.0 - SURFACE_BLEND) * self.elo(name) + SURFACE_BLEND * self.surface_elo(name, surf)

    def win_prob(self, a: str, b: str, surf: str) -> float:
        """Blended, surface-aware win probability of A over B."""
        return expected_score(self.blended(a, surf), self.blended(b, surf))


def run_elo(df: pd.DataFrame, use_mov: bool | None = None) -> tuple[RatingState, pd.DataFrame]:
    """Single chronological pass. `df` must be cleaned + chronologically sorted.

    Returns (final RatingState, per-match pre-match feature frame aligned to df.index).
    """
    if use_mov is None:
        use_mov = USE_MOV
    st = RatingState()

    n = len(df)
    # Pre-allocate output columns (winner/loser oriented, pre-match values).
    cols = ["w_elo", "l_elo", "w_selo", "l_selo", "w_belo", "l_belo",
            "w_n", "l_n", "w_sn", "l_sn", "p_overall", "p_surface", "p_blend"]
    out = {c: np.empty(n, dtype=float) for c in cols}

    winners = df["winner_name"].to_numpy()
    losers = df["loser_name"].to_numpy()
    surfs = df["surface_b"].to_numpy()
    tier_ks = df["tier_k"].to_numpy()
    gdiffs = df["game_diff"].to_numpy()
    completed = df["completed"].to_numpy()
    dates = df["date"].to_numpy()
    months = dates.astype("datetime64[M]")

    for i in range(n):
        w, l, s = winners[i], losers[i], surfs[i]

        rw, rl = st.elo(w), st.elo(l)
        sw, sl = st.surface_elo(w, s), st.surface_elo(l, s)
        bw, bl = (1 - SURFACE_BLEND) * rw + SURFACE_BLEND * sw, (1 - SURFACE_BLEND) * rl + SURFACE_BLEND * sl
        nw, nl = st.n.get(w, 0), st.n.get(l, 0)
        nsw, nsl = st.n_surface[s].get(w, 0), st.n_surface[s].get(l, 0)

        # --- record pre-match features (no leakage) ---
        out["w_elo"][i], out["l_elo"][i] = rw, rl
        out["w_selo"][i], out["l_selo"][i] = sw, sl
        out["w_belo"][i], out["l_belo"][i] = bw, bl
        out["w_n"][i], out["l_n"][i] = nw, nl
        out["w_sn"][i], out["l_sn"][i] = nsw, nsl
        out["p_overall"][i] = expected_score(rw, rl)
        out["p_surface"][i] = expected_score(sw, sl)
        out["p_blend"][i] = expected_score(bw, bl)

        # --- update ---
        mov = mov_multiplier(gdiffs[i]) if (use_mov and completed[i]) else 1.0
        tk = tier_ks[i]

        e_overall = out["p_overall"][i]
        kw, kl = dynamic_k(nw) * tk, dynamic_k(nl) * tk
        st.overall[w] = rw + kw * mov * (1.0 - e_overall)
        st.overall[l] = rl + kl * mov * (0.0 - (1.0 - e_overall))

        e_surf = out["p_surface"][i]
        skw, skl = surface_k(nsw) * tk, surface_k(nsl) * tk
        st.surface[s][w] = sw + skw * mov * (1.0 - e_surf)
        st.surface[s][l] = sl + skl * mov * (0.0 - (1.0 - e_surf))

        st.n[w], st.n[l] = nw + 1, nl + 1
        st.n_surface[s][w], st.n_surface[s][l] = nsw + 1, nsl + 1
        st.last_played[w] = st.last_played[l] = dates[i]

        # monthly Elo snapshot per player (for trends / profile charts)
        m = months[i]
        for nm, rating in ((w, st.overall[w]), (l, st.overall[l])):
            if st._hist_month.get(nm) != m:
                st._hist_month[nm] = m
                st.history.setdefault(nm, []).append((str(m), round(rating)))

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
