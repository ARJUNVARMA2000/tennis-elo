"""Unit checks for data/rankings live-tennis.eu scraping — canned fixture, no network.

Runnable directly (`python tests/test_rankings_parse.py`) or under pytest. The fixture
live_rankings_sample.html is a trimmed copy of the real ATP page (minified, unquoted
attributes, nested header tables, &nbsp; entities, accented names) plus junk tables
outside id=u868. Covers the parser, the fail-closed validation, the keep-last-good
download contract, and the export-side liveRank merge.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.data.rankings as rankings

FIXTURE = Path(__file__).parent / "fixtures" / "live_rankings_sample.html"


def _synth_html(n=120, first_rank=1, dup_name=None):
    """Minified rows in the verified cell layout; comma-grouped points on purpose."""
    tr = ("<tr class=on1><td class=rk>{r}</td><td>CH</td><td></td><td>{name}</td>"
          "<td>25</td><td>USA</td><td>1,{pts}</td><td>{d}</td><td>-10</td></tr>")
    rows = "".join(tr.format(r=i, name=dup_name or f"Player {i}", pts=500 + i, d="+1")
                   for i in range(first_rank, first_rank + n))
    return f"<html><body><table id=u868><tbody>{rows}</tbody></table></body></html>"


def test_parse_real_fixture():
    got = rankings.parse_rankings(FIXTURE.read_text(encoding="utf-8"))
    assert len(got) == 8                                  # junk tables outside u868 dropped
    assert got[0] == {"rank": 1, "name": "Jannik Sinner", "points": 11550, "delta": None}
    assert got[3]["name"] == "Félix Auger-Aliassime"      # utf-8 accents survive
    assert got[4] == {"rank": 5, "name": "Alex de Minaur", "points": 4010, "delta": 1}
    assert got[5]["delta"] == -1
    assert [r["rank"] for r in got] == list(range(1, 9))  # document order = rank ascending


def test_parse_synthetic_edges():
    html = (
        "<table id=u868><thead><tr class=legend><td colspan=14>legend text</td></tr>"
        "<tr><td colspan=14><table><tr><td>nested tab menu</td></tr></table></td></tr></thead>"
        "<tbody>"
        "<tr><td>1</td><td>CH</td><td></td><td>A One</td><td>25</td><td>USA</td><td>1,234</td><td>+2</td><td>-5</td></tr>"
        "<tr><td>2</td><td>&nbsp;NCH&nbsp;(6)&nbsp;</td><td></td><td>B Two</td><td>22</td><td>FRA</td><td>900</td><td></td><td></td></tr>"
        "<tr><td>3</td><td></td><td></td><td>C Short</td><td>20</td></tr>"           # short row -> skipped
        "<tr><td>x</td><td></td><td></td><td>D Bad</td><td>20</td><td>GER</td><td>800</td></tr>"  # non-digit rank
        "</tbody></table>"
    )
    got = rankings.parse_rankings(html)
    assert got == [
        {"rank": 1, "name": "A One", "points": 1234, "delta": 2},   # comma stripped
        {"rank": 2, "name": "B Two", "points": 900, "delta": None},  # blank +/- -> None
    ]


def test_validate_fails_closed():
    ok = rankings.parse_rankings(_synth_html(n=120))
    rankings._validate(ok)                                            # 120 rows from #1: fine
    for bad in (rankings.parse_rankings(_synth_html(n=50)),           # thin (challenge page)
                rankings.parse_rankings(_synth_html(n=120, first_rank=2))):  # shifted table
        try:
            rankings._validate(bad)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass


def test_download_writes_keyed_by_name_key():
    orig = (rankings.live_dir, rankings._fetch)
    with tempfile.TemporaryDirectory() as td:
        try:
            rankings.live_dir = lambda tour: Path(td)
            rankings._fetch = lambda tour: _synth_html(n=120)
            rankings.download_rankings(("atp",))
            data = json.loads((Path(td) / "rankings.json").read_text(encoding="utf-8"))
            assert data["source"] == rankings.URLS["atp"]
            assert data["players"]["player 1"] == {"rank": 1, "name": "Player 1", "points": 1501, "delta": 1}
            assert len(data["players"]) == 120
            assert rankings.load_rankings("atp") == data["players"]

            # duplicate name key: rank-ascending order means first seen (better rank) wins
            rankings._fetch = lambda tour: _synth_html(n=120, dup_name="Same Guy")
            rankings.download_rankings(("atp",))
            dup = rankings.load_rankings("atp")
            assert dup == {"same guy": {"rank": 1, "name": "Same Guy", "points": 1501, "delta": 1}}
        finally:
            rankings.live_dir, rankings._fetch = orig


def test_download_keeps_previous_file_on_failure():
    orig = (rankings.live_dir, rankings._fetch)
    with tempfile.TemporaryDirectory() as td:
        try:
            rankings.live_dir = lambda tour: Path(td)
            good = '{"fetched": "2026-07-01T00:00:00Z", "players": {"a b": {"rank": 1}}}'
            (Path(td) / "rankings.json").write_text(good, encoding="utf-8")

            def boom(tour):
                raise OSError("403 blocked")
            rankings._fetch = boom
            rankings.download_rankings(("atp",))                       # must not raise
            assert (Path(td) / "rankings.json").read_text(encoding="utf-8") == good

            rankings._fetch = lambda tour: _synth_html(n=10)           # thin parse -> validate raises
            rankings.download_rankings(("atp",))
            assert (Path(td) / "rankings.json").read_text(encoding="utf-8") == good
        finally:
            rankings.live_dir, rankings._fetch = orig


def test_load_rankings_missing_and_corrupt():
    orig = rankings.live_dir
    with tempfile.TemporaryDirectory() as td:
        try:
            rankings.live_dir = lambda tour: Path(td)
            assert rankings.load_rankings("atp") == {}                 # missing
            (Path(td) / "rankings.json").write_text("{not json", encoding="utf-8")
            assert rankings.load_rankings("atp") == {}                 # corrupt
        finally:
            rankings.live_dir = orig


def test_source_key_folds_and_aliases():
    assert rankings._source_key("Elmer Møller") == "elmer moller"      # ø doesn't NFKD-fold
    assert rankings._source_key("Jannik Sinner") == "jannik sinner"    # passthrough

    # aliases are ADDITIVE at write time: both model spellings of the same human match
    orig = (rankings.live_dir, rankings._fetch)
    with tempfile.TemporaryDirectory() as td:
        try:
            rankings.live_dir = lambda tour: Path(td)
            rankings._fetch = lambda tour: _synth_html(n=120).replace("Player 120", "Caty McNally")
            rankings.download_rankings(("wta",))
            got = rankings.load_rankings("wta")
            assert got["caty mcnally"]["rank"] == 120
            assert got["catherine mcnally"] == got["caty mcnally"]
        finally:
            rankings.live_dir, rankings._fetch = orig


def test_export_live_rank_merge():
    from tennis_model.model.export import _live_rank_fields, _with_token_order_keys
    table = _with_token_order_keys({
        "felix auger aliassime": {"rank": 4, "name": "Félix Auger-Aliassime",
                                  "points": 4440, "delta": -2},
        "xinyu wang": {"rank": 40, "name": "Xinyu Wang", "points": 1400, "delta": None},
        "qinwen zheng": {"rank": 6, "name": "Qinwen Zheng", "points": 4900, "delta": 1},
    })
    hit = _live_rank_fields("Felix Auger-Aliassime", table)            # accent-insensitive join
    assert hit == {"liveRank": 4, "liveRankDelta": -2}
    # surname-first model names join via the sorted-token fallback, both directions
    assert _live_rank_fields("Wang Xinyu", table) == {"liveRank": 40, "liveRankDelta": None}
    assert _live_rank_fields("Zheng Qinwen", table) == {"liveRank": 6, "liveRankDelta": 1}
    miss = _live_rank_fields("Nobody Nowhere", table)
    assert miss == {"liveRank": None, "liveRankDelta": None}


if __name__ == "__main__":
    test_parse_real_fixture()
    print("ok test_parse_real_fixture")
    test_parse_synthetic_edges()
    print("ok test_parse_synthetic_edges")
    test_validate_fails_closed()
    print("ok test_validate_fails_closed")
    test_download_writes_keyed_by_name_key()
    print("ok test_download_writes_keyed_by_name_key")
    test_download_keeps_previous_file_on_failure()
    print("ok test_download_keeps_previous_file_on_failure")
    test_load_rankings_missing_and_corrupt()
    print("ok test_load_rankings_missing_and_corrupt")
    test_source_key_folds_and_aliases()
    print("ok test_source_key_folds_and_aliases")
    test_export_live_rank_merge()
    print("ok test_export_live_rank_merge")
