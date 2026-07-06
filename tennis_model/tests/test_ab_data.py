"""_verdict per-year tripwire: exact pinned values on a synthetic paired frame."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.eval.ab_data import _verdict  # noqa: E402


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
