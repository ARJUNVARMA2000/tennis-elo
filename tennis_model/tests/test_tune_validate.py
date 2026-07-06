"""_per_year_line: exact pinned values (the Tier-1 per-year tripwire summary)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.eval.tune import _per_year_line  # noqa: E402


def test_per_year_line_exact():
    # 2020: d = [0.01, 0.03]*2 -> mean +0.02; 2021: [-0.02, -0.04]*2 -> mean -0.03
    # SE of [x, y, x, y] = |x-y| / (2*sqrt(3)) = 0.0057735 -> t = -0.03/SE = -5.196
    years = np.array([2020] * 4 + [2021] * 4)
    d = np.array([0.01, 0.03, 0.01, 0.03, -0.02, -0.04, -0.02, -0.04])
    assert _per_year_line(d, years) == "1/2 pos, worst 2021 -0.03000 (t=-5.2)"


def test_per_year_line_all_positive():
    years = np.array([2020] * 3 + [2021] * 3)
    d = np.array([0.01, 0.02, 0.03, 0.001, 0.002, 0.003])
    line = _per_year_line(d, years)
    assert line.startswith("2/2 pos, worst 2021 +0.00200")
