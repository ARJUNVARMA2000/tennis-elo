"""Unit checks for points/serve_return — fully synthetic (no data, no network).

Runnable directly (`python tests/test_serve_return.py`) or under pytest. Pins the
E3 event-speed baseline contract: event_shrinkage=0 reproduces the incumbent walk
exactly; >0 learns per-event offsets from serve-pct residuals and de-biases the
credited skills.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.points.serve_return import DEFAULT_SR_PARAMS, run_serve_return


def _df(rows):
    """rows: (winner, loser, event, spw_frac, date). Both players serve 100 points
    and win spw_frac of them — a symmetric match at a venue of that speed."""
    out = []
    for (w, l, ev, spw, d) in rows:
        out.append({
            "winner_name": w, "loser_name": l, "tourney_name": ev,
            "surface_b": "Hard", "date": pd.Timestamp(d), "best_of": 3,
            "has_stats": True, "completed": True,
            "w_svpt": 100.0, "l_svpt": 100.0,
            "w_1stWon": spw * 60.0, "w_2ndWon": spw * 40.0,
            "l_1stWon": spw * 60.0, "l_2ndWon": spw * 40.0,
        })
    return pd.DataFrame(out)


def _rows():
    # alternating venues: a slow court (55% serve) and a fast court (75% serve);
    # distinct player pairs so no player-skill story explains the split
    rows = []
    for k in range(6):
        d1, d2 = f"2025-0{k + 1}-05", f"2025-0{k + 1}-12"
        rows.append((f"S{k}a", f"S{k}b", "Slow Open", 0.55, d1))
        rows.append((f"F{k}a", f"F{k}b", "Fast Open", 0.75, d2))
    rows.append(("Xa", "Xb", "Fast Open", 0.75, "2025-07-05"))
    return rows


def test_event_off_is_bit_identical():
    df = _df(_rows())
    _, f0 = run_serve_return(df)
    _, f1 = run_serve_return(df, params=replace(DEFAULT_SR_PARAMS, event_shrinkage=0.0))
    assert (f0 == f1).all().all()
    print("ok test_event_off_is_bit_identical")


def test_event_offset_learns_court_speed():
    from tennis_model.points.serve_return import serve_averages
    df = _df(_rows())
    _, base = run_serve_return(df)
    k = 500.0
    st_e, ev = run_serve_return(df, params=replace(DEFAULT_SR_PARAMS, event_shrinkage=k))
    last = len(df) - 1                     # debutants at the fast event
    # exact estimator contract: 6 fast matches, all debutant pairs (skills = 0 at
    # their only match), so the shrunk offset is (0.75 - league_base) * P/(P + k)
    # with P = 1200 accumulated service points — the FULL venue delta, shrunk
    # toward 0, not half of it (the exp_pool-includes-off regression)
    lg, _bases = serve_averages(df)
    exp_off = (0.75 - lg) * 1200.0 / (1200.0 + k)
    assert abs(ev.loc[last, "pa_serve"] - (lg + exp_off)) < 1e-9
    assert abs(ev.loc[last, "pb_serve"] - (lg + exp_off)) < 1e-9
    assert ev.loc[last, "pa_serve"] > base.loc[last, "pa_serve"] + 0.01
    # symmetric shift -> match probability stays ~even
    assert abs(ev.loc[last, "p_point"] - 0.5) < 1e-6
    # prediction-time mirror: the final state applies the same estimator (post-walk,
    # so the 7th fast match's 200 points are in: P = 1400)
    exp_off_state = (0.75 - lg) * 1400.0 / (1400.0 + k)
    pa, pb = st_e.point_probs("NewA", "NewB", "Hard", event="Fast Open")
    assert abs(pa - (lg + exp_off_state)) < 1e-9
    assert abs(pb - (lg + exp_off_state)) < 1e-9
    assert st_e.point_probs("NewA", "NewB", "Hard")[0] == lg      # no event -> neutral
    # credited serve skill is de-biased: the fast-event regulars' serve skills no
    # longer inflate relative to slow-event regulars with identical raw numbers
    st_b, _ = run_serve_return(df)
    gap_base = st_b.global_serve_skill("F5a") - st_b.global_serve_skill("S5a")
    gap_ev = st_e.global_serve_skill("F5a") - st_e.global_serve_skill("S5a")
    assert gap_ev < gap_base
    print("ok test_event_offset_learns_court_speed")


if __name__ == "__main__":
    test_event_off_is_bit_identical()
    test_event_offset_learns_court_speed()
    print("\nALL PASSED")
