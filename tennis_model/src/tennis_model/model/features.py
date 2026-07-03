"""Assemble the leakage-free feature frame that the XGBoost combiner consumes.

Three chronological passes produce PRE-match signals:
  - run_elo            -> surface-blended Elo (+ overall/surface, counts)
  - run_serve_return   -> serve/return skill + hierarchical point-model probability
  - run_context (here) -> rest, recent workload (fatigue), head-to-head

Everything is recorded winner-oriented (A = winner). Anti-symmetric features are
stored as A-minus-B differences (and probabilities as logits) so that producing a
balanced training set is just a sign flip on a random half of the rows — which is
what stops the model from trivially learning "player A always wins".
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import config as _config
from ..data.charting import STYLE_FEATURES, build_profiles, name_key
from ..data.geo import IOC_ALIAS, host_ioc
from ..data.results import load_matches
from ..points.serve_return import run_serve_return
from ..ratings.build import run_elo

_DAY = np.timedelta64(1, "D")


class H2HState:
    """Final context store (head-to-head, surface H2H, recent form) for inference."""

    def __init__(self, h2h: dict, h2h_surface: dict | None = None,
                 last10: dict | None = None):
        self._h2h = h2h
        self._h2h_surface = h2h_surface or {}
        self._last10 = last10 or {}

    def record(self, a: str, b: str) -> tuple[int, int]:
        """(a_wins, b_wins) between a and b."""
        key = (a, b) if a < b else (b, a)
        rec = self._h2h.get(key, [0, 0])
        return (rec[0], rec[1]) if a < b else (rec[1], rec[0])

    def record_surface(self, a: str, b: str, surf: str) -> tuple[int, int]:
        """(a_wins, b_wins) between a and b on `surf` only."""
        key = ((a, b) if a < b else (b, a), surf)
        rec = getattr(self, "_h2h_surface", {}).get(key, [0, 0])
        return (rec[0], rec[1]) if a < b else (rec[1], rec[0])

    def winrate10(self, name: str) -> float:
        """Win rate over the player's last <=10 completed matches (0.5 if none)."""
        dq = getattr(self, "_last10", {}).get(name)
        return float(sum(dq) / len(dq)) if dq else 0.5

# MCP tactical-style diffs (anti-symmetric); 0 when a player lacks a charted profile.
STYLE_DIFFS = [s + "_diff" for s in STYLE_FEATURES]
# Features that flip sign when we swap A<->B (A-minus-B differences / logit-probs).
ANTISYM = [
    "elo_diff", "elo_overall_diff", "elo_surface_diff",
    "logit_p_blend", "logit_p_point",
    "serve_skill_diff", "return_skill_diff",
    "rankpts_diff", "exp_diff", "age_diff", "ht_diff",
    "hand_matchup", "rest_diff", "fatigue_diff", "h2h_diff",
    # layoff (rest_diff is clipped at +-60d, so long absences need their own signal)
    "log_days_since_diff", "layoff_flag_diff",
    # short-term form (veterans' small K under-reflects hot/cold streaks)
    "form90_diff", "winrate10_diff",
    # rivalry & profile
    "h2h_surface_diff", "entry_q_diff", "peak_age_dev_diff",
    # home advantage (P2): playing in your own country (crowd, familiarity, and for
    # team ties the host's choice of ground); 0 when the venue is unknown/neutral
    "home_flag_diff",
    # E1 box-score decomposition (bp_clutch/ace/df/first-in/minutes14/ret_recent)
    # was tried and REJECTED by the paired walk-forward gate on both tours
    # (2026-07-02 core round): the opponent-adjusted spw% walk already compresses
    # the box score; the extra dimensions cost capacity without net signal.
] + STYLE_DIFFS
# Features that are unchanged by the swap (match context / symmetric confidence).
SYMMETRIC = [
    "best_of", "is_indoor", "tier_k", "round_order",
    "surf_hard", "surf_clay", "surf_grass",
    "log_min_srv_pts", "log_min_matches", "has_style",
    "log1p_h2h_total",              # lets the trees gate how much to trust h2h_diff
]
FEATURES = ANTISYM + SYMMETRIC


@dataclass(frozen=True)
class FeatureParams:
    """Tunable context/feature constants (defaults = config = production).

    Carried on the TennisPredictor (`fp`) so inference always applies the same
    thresholds the training frame was built with — module-level constants were
    import-bound copies that a tune-time override could never reach.
    (form_days lives on EloParams: the Elo walk computes that feature.)
    """

    fatigue_window_days: float = _config.FATIGUE_WINDOW_DAYS
    layoff_days: float = _config.LAYOFF_DAYS
    peak_age: float = _config.PEAK_AGE
    winrate_window: int = _config.WINRATE_WINDOW


DEFAULT_FEAT_PARAMS = FeatureParams()


def feat_params_for(tour: str) -> FeatureParams:
    """The tour's FeatureParams: shared defaults + the tour's tuned overrides."""
    from ..config import FEAT_PARAM_OVERRIDES
    return FeatureParams(**FEAT_PARAM_OVERRIDES.get(tour, {}))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def run_context(df: pd.DataFrame,
                params: FeatureParams = DEFAULT_FEAT_PARAMS) -> pd.DataFrame:
    """Rest, recent workload, head-to-head (career + surface), last-N form — pre-match."""
    n = len(df)
    out = {c: np.zeros(n, dtype=float) for c in
           ["w_days_since", "l_days_since", "w_fat", "l_fat", "w_h2h", "l_h2h",
            "w_h2h_s", "l_h2h_s", "w_wr10", "l_wr10"]}

    wr_window = int(params.winrate_window)
    last_date: dict = {}
    recent: dict = defaultdict(deque)          # player -> deque[(date, games_played)]
    h2h: dict = defaultdict(lambda: [0, 0])    # (a,b) sorted -> [wins_a, wins_b]
    h2h_s: dict = defaultdict(lambda: [0, 0])  # ((a,b) sorted, surface) -> [wins]
    last10: dict = defaultdict(lambda: deque(maxlen=wr_window))  # player -> 1/0 results

    winners = df["winner_name"].to_numpy()
    losers = df["loser_name"].to_numpy()
    dates = df["date"].to_numpy()
    surfs = df["surface_b"].to_numpy()
    completed = df["completed"].to_numpy()
    games = (df["w_games"] + df["l_games"]).to_numpy()

    def workload(name, t):
        dq = recent[name]
        while dq and (t - dq[0][0]) / _DAY > params.fatigue_window_days:
            dq.popleft()
        return sum(g for _, g in dq)

    def wr10(name):
        dq = last10[name]
        return sum(dq) / len(dq) if dq else 0.5

    for i in range(n):
        w, l, t, s = winners[i], losers[i], dates[i], surfs[i]
        out["w_days_since"][i] = (t - last_date[w]) / _DAY if w in last_date else 365.0
        out["l_days_since"][i] = (t - last_date[l]) / _DAY if l in last_date else 365.0
        out["w_fat"][i] = workload(w, t)
        out["l_fat"][i] = workload(l, t)
        out["w_wr10"][i], out["l_wr10"][i] = wr10(w), wr10(l)
        key = (w, l) if w < l else (l, w)
        rec, rec_s = h2h[key], h2h_s[(key, s)]
        if w < l:
            out["w_h2h"][i], out["l_h2h"][i] = rec[0], rec[1]
            out["w_h2h_s"][i], out["l_h2h_s"][i] = rec_s[0], rec_s[1]
        else:
            out["w_h2h"][i], out["l_h2h"][i] = rec[1], rec[0]
            out["w_h2h_s"][i], out["l_h2h_s"][i] = rec_s[1], rec_s[0]

        # update
        gp = games[i]
        last_date[w] = last_date[l] = t
        recent[w].append((t, gp)); recent[l].append((t, gp))
        if completed[i]:                       # walkovers/retirements say little of form
            last10[w].append(1); last10[l].append(0)
        idx = 0 if w < l else 1
        rec[idx] += 1
        rec_s[idx] += 1

    return H2HState(dict(h2h), dict(h2h_s), dict(last10)), pd.DataFrame(out, index=df.index)


def _run_all(df: pd.DataFrame):
    """Run the three chronological passes and assemble features; keep the states."""
    from ..points.serve_return import sr_params_for
    from ..ratings.elo import params_for
    tour = str(df["tour"].iloc[0]) if "tour" in df and len(df) else "atp"
    fp = feat_params_for(tour)
    elo_state, elo = run_elo(df, params=params_for(tour))
    srv_state, srv = run_serve_return(df, params=sr_params_for(tour))
    ctx_state, ctx = run_context(df, params=fp)
    d = df.join(elo).join(srv).join(ctx)
    return _assemble(d, params=fp), elo_state, srv_state, ctx_state


def build_feature_frame(df: pd.DataFrame | None = None, tour: str = "atp") -> pd.DataFrame:
    """Run all passes and produce the winner-oriented feature frame (+ id columns)."""
    if df is None:
        df = load_matches(tour)
    return _run_all(df)[0]


def player_meta(df: pd.DataFrame) -> dict:
    """Latest-known rank points, age, height, hand and country per player.

    Keeps the most recent *non-null* value per field, so a fresh ESPN live row that
    lacks bio data doesn't blank out a player who has it. `age` is stored with the
    date it was observed (`age_asof`) so callers can advance it to the present — fresh
    rows carry no age, so the latest known age is often a year or two stale.
    """
    meta: dict = {}
    fields = ("rank_points", "age", "ht", "hand", "ioc")
    cols = ["date",
            "winner_name", "winner_rank_points", "winner_age", "winner_ht", "winner_hand", "winner_ioc",
            "loser_name", "loser_rank_points", "loser_age", "loser_ht", "loser_hand", "loser_ioc"]
    for row in df[cols].sort_values("date").itertuples(index=False):
        date = row[0]
        for nm, *vals in ((row[1], *row[2:7]), (row[7], *row[8:13])):
            m = meta.setdefault(nm, {})
            for k, v in zip(fields, vals):
                if pd.notna(v):
                    m[k] = v
                    if k == "age":
                        m["age_asof"] = date
    return meta


def build_predictor_inputs(df: pd.DataFrame | None = None, tour: str = "atp"):
    """Everything the TennisPredictor needs: features (for training) + final states + meta."""
    if df is None:
        df = load_matches(tour)
    f, elo_state, srv_state, ctx_state = _run_all(df)
    return f, elo_state, srv_state, ctx_state, player_meta(df)


def _assemble(d: pd.DataFrame,
              params: FeatureParams = DEFAULT_FEAT_PARAMS) -> pd.DataFrame:
    """Build the winner-oriented feature columns from the joined walk outputs."""
    f = pd.DataFrame(index=d.index)
    # anti-symmetric (A = winner)
    f["elo_diff"] = d["elo_diff"]
    f["elo_overall_diff"] = d["w_elo"] - d["l_elo"]
    f["elo_surface_diff"] = d["w_selo"] - d["l_selo"]
    f["logit_p_blend"] = _logit(d["p_blend"].to_numpy())
    f["logit_p_point"] = _logit(d["p_point"].to_numpy())
    f["serve_skill_diff"] = d["serve_skill_diff"]
    f["return_skill_diff"] = d["return_skill_diff"]
    wp = pd.to_numeric(d["winner_rank_points"], errors="coerce")
    lp = pd.to_numeric(d["loser_rank_points"], errors="coerce")
    f["rankpts_diff"] = (np.log((wp + 1) / (lp + 1))).fillna(0.0)
    f["exp_diff"] = np.log(d["w_n"] + 1) - np.log(d["l_n"] + 1)
    f["age_diff"] = (pd.to_numeric(d["winner_age"], errors="coerce")
                     - pd.to_numeric(d["loser_age"], errors="coerce")).fillna(0.0)
    f["ht_diff"] = (pd.to_numeric(d["winner_ht"], errors="coerce")
                    - pd.to_numeric(d["loser_ht"], errors="coerce")).fillna(0.0)
    wl = (d["winner_hand"] == "L").astype(int)
    ll = (d["loser_hand"] == "L").astype(int)
    f["hand_matchup"] = wl - ll
    f["rest_diff"] = np.clip(d["w_days_since"] - d["l_days_since"], -60, 60)
    f["fatigue_diff"] = d["w_fat"] - d["l_fat"]
    f["h2h_diff"] = d["w_h2h"] - d["l_h2h"]

    # layoff: rest_diff's clip destroys long-absence information — restore it
    f["log_days_since_diff"] = np.log1p(d["w_days_since"]) - np.log1p(d["l_days_since"])
    f["layoff_flag_diff"] = ((d["w_days_since"] > params.layoff_days).astype(int)
                             - (d["l_days_since"] > params.layoff_days).astype(int))
    # short-term form
    f["form90_diff"] = d["w_form90"] - d["l_form90"]
    f["winrate10_diff"] = d["w_wr10"] - d["l_wr10"]
    # rivalry & profile
    f["h2h_surface_diff"] = d["w_h2h_s"] - d["l_h2h_s"]
    w_q = d.get("winner_entry", pd.Series(index=d.index, dtype=object)).isin(("Q", "LL"))
    l_q = d.get("loser_entry", pd.Series(index=d.index, dtype=object)).isin(("Q", "LL"))
    f["entry_q_diff"] = w_q.astype(int) - l_q.astype(int)
    wa = pd.to_numeric(d["winner_age"], errors="coerce")
    la = pd.to_numeric(d["loser_age"], errors="coerce")
    f["peak_age_dev_diff"] = ((wa - params.peak_age).abs()
                              - (la - params.peak_age).abs()).fillna(0.0)
    # home advantage (P2): host country from the tournament name + year
    empty = pd.Series(index=d.index, dtype=object)
    names_s = d.get("tourney_name", empty)
    yrs = d["date"].dt.year.to_numpy()
    _tour = str(d["tour"].iloc[0]) if "tour" in d and len(d) else None
    host = [host_ioc(nm, int(y), _tour) if isinstance(nm, str) else None
            for nm, y in zip(names_s.to_numpy(), yrs)]
    wio = d.get("winner_ioc", empty).map(lambda x: IOC_ALIAS.get(x, x)).to_numpy()
    lio = d.get("loser_ioc", empty).map(lambda x: IOC_ALIAS.get(x, x)).to_numpy()
    f["home_flag_diff"] = [(0 if h is None else int(h == w) - int(h == lo))
                           for h, w, lo in zip(host, wio, lio)]

    # symmetric context + confidence
    f["best_of"] = pd.to_numeric(d["best_of"], errors="coerce").fillna(3)
    f["is_indoor"] = d["is_indoor"].map({True: 1, False: 0}).fillna(0)
    f["tier_k"] = d["tier_k"]
    f["round_order"] = d["round_order"]
    f["surf_hard"] = (d["surface_b"] == "Hard").astype(int)
    f["surf_clay"] = (d["surface_b"] == "Clay").astype(int)
    f["surf_grass"] = (d["surface_b"] == "Grass").astype(int)
    f["log_min_srv_pts"] = np.log1p(np.minimum(d["w_srv_pts"], d["l_srv_pts"]))
    f["log_min_matches"] = np.log1p(np.minimum(d["w_n"], d["l_n"]))
    f["log1p_h2h_total"] = np.log1p(d["w_h2h"] + d["l_h2h"])

    # MCP tactical-style diffs (0 unless both players have a charted profile)
    tour = str(d["tour"].iloc[0]) if "tour" in d and len(d) else "atp"
    profiles = build_profiles(tour)
    wk = d["winner_name"].map(name_key)
    lk = d["loser_name"].map(name_key)
    f["has_style"] = (wk.isin(profiles) & lk.isin(profiles)).astype(int)
    for s in STYLE_FEATURES:
        wv = wk.map(lambda k, s=s: profiles.get(k, {}).get(s, np.nan)).astype(float)
        lv = lk.map(lambda k, s=s: profiles.get(k, {}).get(s, np.nan)).astype(float)
        f[s + "_diff"] = (wv - lv).where(f["has_style"] == 1, 0.0).fillna(0.0)

    # carry-through id/baseline columns
    f["date"] = d["date"]
    f["year"] = d["date"].dt.year
    f["completed"] = d["completed"]
    f["p_blend"] = d["p_blend"]
    f["p_point"] = d["p_point"]
    f["winner_name"] = d["winner_name"]
    f["loser_name"] = d["loser_name"]
    return f


def make_oriented_xy(feat: pd.DataFrame, seed: int = 0) -> tuple[pd.DataFrame, np.ndarray]:
    """Balanced (X, y): randomly swap A<->B on half the rows so y is ~50/50.

    Anti-symmetric features negate; logit-probs negate (== p -> 1-p); context stays.
    """
    rng = np.random.default_rng(seed)
    flip = rng.random(len(feat)) < 0.5
    X = pd.DataFrame(index=feat.index)
    sign = np.where(flip, -1.0, 1.0)
    for c in ANTISYM:
        X[c] = feat[c].to_numpy() * sign
    for c in SYMMETRIC:
        X[c] = feat[c].to_numpy()
    y = np.where(flip, 0, 1).astype(int)
    return X[FEATURES], y


if __name__ == "__main__":
    f = build_feature_frame()
    print(f"Feature frame: {len(f):,} rows, {len(FEATURES)} model features")
    print("Features:", FEATURES)
    print(f.tail(3)[["date", "winner_name", "loser_name", "elo_diff", "logit_p_point",
                     "h2h_diff", "rest_diff"]].to_string(index=False))
