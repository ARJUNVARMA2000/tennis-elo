"""_verdict per-year tripwire: exact pinned values on a synthetic paired frame."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.eval.ab_data import (  # noqa: E402
    _assert_unaffected_parity,
    _focused_wta_slices,
    _kalshi_outside_top50_keys,
    _verdict,
)


def _frames():
    """Per-row d = llb - lla = ln(p_arm / p_base), so p_arm = p_base * exp(d)
    gives exact per-year paired deltas by construction."""
    years, d = [], []
    for y, (d1, d2) in [(2010, (0.01, 0.03)),    # mean +0.02 (tune window)
                        (2011, (-0.02, -0.04)),  # mean -0.03 (tune window)
                        (2020, (0.05, 0.07))]:   # mean +0.06 (val window)
        years += [y] * 4
        d += [d1, d2, d1, d2]
    p_base = np.full(len(d), 0.5)
    base = pd.DataFrame({"year": years, "p_combiner": p_base})
    arm = pd.DataFrame({"year": years, "p_combiner": p_base * np.exp(d)})
    return base, arm


def test_verdict_per_year_table_exact(capsys):
    _verdict(*_frames())
    out = capsys.readouterr().out
    # per-year means are exact; SE of [x, y, x, y] is |x-y|/(2*sqrt(3)) = 0.00577
    assert "2010: +0.02000±0.00577" in out
    assert "2011: -0.03000±0.00577" in out
    assert "2020: +0.06000±0.00577" in out
    assert "per-year: 2/3 positive, max |d| = 0.06000" in out


def test_verdict_gate_line_format(capsys):
    """The loop parses the GATE line; pin it. d_tune = mean(2010+2011 rows) = -0.005
    fails d_tune > 0, so the honest verdict here is REJECT."""
    _verdict(*_frames())
    out = capsys.readouterr().out
    assert "GATE: d_tune=-0.00500  d_val=+0.06000" in out
    assert "-> REJECT" in out


def test_wta_focused_slices_use_ranks_and_frozen_kalshi_membership(capsys):
    base = pd.DataFrame({
        "winner_name": ["Alpha One", "Charlie Three", "Echo Five"],
        "loser_name": ["Bravo Two", "Delta Four", "Foxtrot Six"],
        "date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"]),
        "year": [2025, 2025, 2025],
        "winner_rank": [10, 51, np.nan], "loser_rank": [20, 7, 60],
        "p_combiner": [0.5, 0.5, 0.5],
    })
    arm = base.copy()
    arm["p_combiner"] = [0.51, 0.52, 0.53]
    frozen = pd.DataFrame({
        "player_a": ["Delta Four", "Alpha One"],
        "player_b": ["Charlie Three", "Bravo Two"],
        "result_date": ["2025-01-02", "2025-01-01"],
        "rank_a": [7, 10], "rank_b": [51, 20],
    })

    keys = _kalshi_outside_top50_keys(frozen)
    assert len(keys) == 1
    _focused_wta_slices(base, arm, kalshi=frozen)
    out = capsys.readouterr().out
    assert "both players inside top 50            n=    1" in out
    assert "someone outside top 50                n=    2" in out
    assert "frozen Kalshi + outside top 50        n=    1" in out


def test_state_only_parity_guard_rejects_pre_effect_drift():
    base = pd.DataFrame({"year": [2015, 2016], "p_combiner": [0.6, 0.7]})
    same_pre = pd.DataFrame({"year": [2015, 2016], "p_combiner": [0.6, 0.71]})
    _assert_unaffected_parity(base, same_pre, 2016)

    drift = pd.DataFrame({"year": [2015, 2016], "p_combiner": [0.6001, 0.71]})
    try:
        _assert_unaffected_parity(base, drift, 2016)
        raise AssertionError("expected pre-effect parity failure")
    except AssertionError as exc:
        assert "pre-2016" in str(exc)
