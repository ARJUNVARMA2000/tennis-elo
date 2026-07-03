"""Unit checks for data/geo.py — tournament host-country resolution (P2).

Runnable directly (`python tests/test_geo.py`) or under pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tennis_model.data.geo import _norm, host_ioc


def test_city_map_and_variants():
    assert host_ioc("Roland Garros", 2023) == "FRA"
    assert host_ioc("US Open", 2019) == "USA"
    assert host_ioc("Us Open", 2015) == "USA"                 # case variant
    assert host_ioc("Winston-Salem", 2018) == "USA"           # hyphen variant
    for v in ("'s-Hertogenbosch", "s Hertogenbosch", "S-Hertogenbosch",
              "'S-Hertogenbosch", "s-Hertogenbosch"):
        assert host_ioc(v, 2016) == "NED", v
    assert host_ioc("Adelaide 2", 2022) == "AUS"              # split-event suffix
    assert host_ioc("Hua Hin #2", 2023) == "THA"
    assert host_ioc("Guadalajara 500", 2024) == "MEX"
    assert host_ioc("Queen's Club", 2021) == "GBR"
    assert host_ioc("Monte Carlo Masters", 2019) == "MON"
    print("ok test_city_map_and_variants")


def test_sponsor_prefix_fallback():
    assert host_ioc("Lexus Nottingham Open", 2025) == "GBR"
    assert host_ioc("Bad Homburg Open powered by Solarwatt", 2024) == "GER"
    assert host_ioc("VANDA Pharmaceuticals Berlin Tennis Open", 2025) == "GER"
    assert host_ioc("Internazionali Femminili Di Brescia", 2023) == "ITA"
    print("ok test_sponsor_prefix_fallback")


def test_team_ties():
    assert host_ioc("Davis Cup G1 R1: FRA vs GER", 2014) == "FRA"   # ATP: first hosts
    assert host_ioc("Davis Cup G2 ITA vs KOR", 1999) == "ITA"       # no-colon variant
    # the WTA Fed Cup / BJK Cup file carries NO host order (single-venue weeks,
    # arbitrary/winner-first ordering) -> always neutral
    assert host_ioc("Fed Cup G2 RR: PER vs BOL", 2017) is None
    assert host_ioc("Fed Cup WG F: FRA vs AUS", 2019) is None       # played in Perth
    assert host_ioc("BJK Cup Playoffs: KAZ vs ARG", 2023) is None
    # post-2019 finals weeks are neutral venues -> None even with team codes
    assert host_ioc("Davis Cup Finals: RUS vs ESP", 2021) is None
    assert host_ioc("BJK Cup Finals: SUI vs AUS", 2022) is None
    # the two source-reversed Davis Cup finals are special-cased to the real host
    assert host_ioc("Davis Cup WG F: ARG vs CRO", 2016) == "CRO"    # Zagreb
    assert host_ioc("Davis Cup WG F: BEL vs FRA", 2017) == "FRA"    # Lille
    assert host_ioc("Davis Cup WG F: FRA vs SUI", 2014) == "FRA"    # Lille, host-first
    print("ok test_team_ties")


def test_year_dependent_events():
    assert host_ioc("Olympics", 2012) == "GBR"
    assert host_ioc("Olympics", 2016) == "BRA"
    assert host_ioc("Tokyo Olympics", 2021) == "JPN"
    assert host_ioc("Tour Finals", 2015) == "GBR"
    assert host_ioc("Tour Finals", 2022) == "ITA"
    assert host_ioc("Masters Cup", 2004) == "USA"
    assert host_ioc("WTA Finals", 2014) == "SGP"
    assert host_ioc("WTA Finals", 2025) == "KSA"
    assert host_ioc("Next Gen Finals", 2019) == "ITA"
    assert host_ioc("Next Gen Finals", 2024) == "KSA"
    assert host_ioc("Tournament of Champions", 2011) == "INA"       # Bali
    assert host_ioc("Tournament of Champions", 2012) == "BUL"       # Sofia from 2012
    print("ok test_year_dependent_events")


def test_ambiguous_names():
    # ATP "Birmingham" is Birmingham, Alabama; the WTA event is Edgbaston, England
    assert host_ioc("Birmingham", 1994, "atp") == "USA"
    assert host_ioc("Birmingham", 2024, "wta") == "GBR"
    assert host_ioc("Birmingham", 2024) == "GBR"                    # tourless default
    # "East Hanover" (New Jersey) must not substring-match Hanover, Germany
    assert host_ioc("East Hanover", 1984, "wta") == "USA"
    print("ok test_ambiguous_names")


def test_unknown_is_none():
    assert host_ioc("Laver Cup", 2023) is None                # rotating team event
    assert host_ioc("Some Unknown Challenger", 2020) is None
    assert host_ioc("", 2020) is None
    assert _norm("Cluj-Napoca 2") == "cluj napoca"
    print("ok test_unknown_is_none")


if __name__ == "__main__":
    test_city_map_and_variants()
    test_sponsor_prefix_fallback()
    test_team_ties()
    test_year_dependent_events()
    test_ambiguous_names()
    test_unknown_is_none()
    print("\nALL PASSED")
