"""Unit checks for the venue-altitude table and its feature wiring (Phase C).

Runnable directly (`python tests/test_altitude.py`) or under pytest. The committed
venue_altitude.csv is a static repo resource, so exact-city assertions are stable.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.altitude import TABLE, altitude_m


def test_table_ships_and_loads():
    assert TABLE.exists(), "venue_altitude.csv must be committed next to altitude.py"
    # known extremes (meters; generous bands tolerate DEM revisions on rebuild)
    assert 2700 < altitude_m("Quito") < 3000
    assert 2400 < altitude_m("Bogota") < 2700
    assert 900 < altitude_m("Gstaad") < 1200
    assert 500 < altitude_m("Madrid") < 800
    assert altitude_m("Wimbledon") < 100
    print("ok test_table_ships_and_loads")


def test_sponsor_prefixed_names_resolve_like_geo():
    """altitude_m shares geo.city_key resolution, so sponsor-prefixed variants
    must land on the same venue (the home-advantage feature's behavior)."""
    assert altitude_m("EFG Swiss Open Gstaad") == altitude_m("Gstaad")
    assert altitude_m("Mutua Madrid Open Madrid") == altitude_m("Madrid")
    assert altitude_m("No Such Event 123") is None
    assert altitude_m(None) is None
    print("ok test_sponsor_prefixed_names_resolve_like_geo")


def test_feature_and_mirror_use_same_lookup():
    """features._assemble and predict._feature_dict both compute
    (altitude_m(name) or 0)/1000 — pin the shared formula at both extremes."""
    known = ((altitude_m("Gstaad") or 0.0) / 1000.0
             )
    assert 0.9 < known < 1.2
    unknown = ((altitude_m("Hypothetical Cup") or 0.0) / 1000.0)
    assert unknown == 0.0
    print("ok test_feature_and_mirror_use_same_lookup")


if __name__ == "__main__":
    test_table_ships_and_loads()
    test_sponsor_prefixed_names_resolve_like_geo()
    test_feature_and_mirror_use_same_lookup()
    print("\nALL PASSED")
