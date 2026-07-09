"""Tournament display level derivation — main-draw rows decide an event's level, so qualifying
rows (results.py stamps tourney_level='Q') can't win the mode and mislabel a Slam. Guards the
ATP-Wimbledon-shows-'Q' bug. Fully synthetic; runnable directly or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.sim.tournaments import _level_label, _main_level_code


def _frame(rows):
    return pd.DataFrame(rows)


def test_main_draw_beats_more_numerous_qualifying():
    # A live Slam: 4 main-draw "G" rows but 12 qualifying "Q" rows — a naive mode picks "Q".
    rows = [dict(tourney_level="G", draw_level="main") for _ in range(4)]
    rows += [dict(tourney_level="Q", draw_level="qual") for _ in range(12)]
    g = _frame(rows)
    assert _main_level_code(g) == "G"
    assert _level_label(_main_level_code(g), "atp") == "Grand Slam"


def test_no_draw_level_column_falls_back_to_plain_mode():
    # Test-style frames carry no draw_level column — behave like the old plain mode.
    g = _frame([dict(tourney_level="250") for _ in range(8)])
    assert _level_label(_main_level_code(g), "atp") == "ATP 250"


def test_all_qualifying_never_renders_raw_q():
    # Only qualifying rows present: fall back to their mode ("Q"), but render a generic tour
    # label, never the raw "Q".
    g = _frame([dict(tourney_level="Q", draw_level="qual") for _ in range(5)])
    assert _main_level_code(g) == "Q"
    assert _level_label(_main_level_code(g), "wta") == "WTA Tour"


def test_missing_tourney_level_column():
    assert _main_level_code(_frame([{"round": "R64"}])) is None
    assert _level_label(None, "atp") == "ATP Tour"


def test_level_label_q_safety_case():
    assert _level_label("Q", "atp") == "ATP Tour"
    assert _level_label("Q", "wta") == "WTA Tour"


if __name__ == "__main__":
    for _fn in (
        test_main_draw_beats_more_numerous_qualifying,
        test_no_draw_level_column_falls_back_to_plain_mode,
        test_all_qualifying_never_renders_raw_q,
        test_missing_tourney_level_column,
        test_level_label_q_safety_case,
    ):
        _fn()
        print("ok", _fn.__name__)
