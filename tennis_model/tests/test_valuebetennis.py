"""Source intake, identity and attribution regressions for the odds supplement."""

import io
import json

import pandas as pd
import pytest
from tennis_model.eval import compare
from test_compare import _odds, _oos
from test_health import NOW, _healthy_data, _oc

from tennis_model.data import health
from tennis_model.data import valuebetennis as vb


def payload(**changes):
    rows = []
    for genre in ("atp", "wta"):
        rows.append(
            dict(
                match_id=genre + "1",
                date="2025-06-01 12:00:00",
                genre=genre,
                categorie="Main tour",
                surface="dur",
                tour=5,
                joueur1="Alfa One",
                joueur2="Xray Nine",
                joueur1_id="1",
                joueur2_id="2",
                vainqueur_id="1",
                cote1_cloture=1.6,
                cote2_cloture=2.4,
                score="6-4 6-4",
                **{},
            )
        )
    rows[0].update(changes)
    return pd.DataFrame(rows).to_csv(sep=";", index=False).encode()


@pytest.mark.parametrize(
    "changes",
    [
        dict(cote1_cloture=1),
        dict(cote1_cloture=float("inf")),
        dict(categorie="ITF"),
        dict(tour=1),
        dict(score="w/o"),
        dict(score="6-4 RET"),
        dict(vainqueur_id="3"),
        dict(joueur2_id="1"),
    ],
)
def test_ineligible_rows_cannot_price_a_main_match(changes):
    assert vb.parse(payload(**changes), "atp", 2025).empty


def test_future_and_wrong_season_reject_the_source_generation():
    for date in ["2027-01-01", "not a date", "2025-12-31"]:
        with pytest.raises(ValueError):
            vb.parse(payload(date=date), "atp", 2025, now=pd.Timestamp("2025-06-02", tz="UTC"))


def test_winner_orientation_and_duplicate_conflicts():
    rows = pd.read_csv(io.BytesIO(payload(vainqueur_id="2")), sep=";")
    parsed = vb.parse(rows.to_csv(sep=";", index=False).encode(), "atp", 2025)
    assert parsed.iloc[0].winner_key == "xray nine" and parsed.iloc[0].odds_w == 2.4
    rows = pd.concat([rows, rows.iloc[:1].assign(score="7-6 6-4")])
    assert vb.parse(rows.to_csv(sep=";", index=False).encode(), "atp", 2025).empty


def test_provider_indoor_hard_dialect_preserves_late_season_coverage():
    row = vb.parse(payload(surface="dur intérieur"), "atp", 2025)
    assert row.iloc[0].surface == "Hard"


def test_atomic_generation_and_digest_binding(tmp_path, monkeypatch):
    monkeypatch.setattr(vb, "ODDS_DIR", tmp_path)
    monkeypatch.setattr(vb.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(payload()))
    vb.download(2025)
    receipt = tmp_path / "valuebetennis/2025.receipt.json"
    original = receipt.read_bytes()
    assert len(vb.load("atp", [2025])) == 1
    monkeypatch.setattr(vb.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(b"<html>error</html>"))
    with pytest.raises(ValueError):
        vb.download(2025)
    assert receipt.read_bytes() == original and len(vb.load("atp", [2025])) == 1
    digest = json.loads(original)["sha256"]
    (receipt.parent / "objects" / f"{digest}.csv").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="digest"):
        vb.load("atp", [2025])


def test_supplement_preserves_legacy_precedence_and_extends_coverage(monkeypatch):
    oos = _oos()
    oos["surface"] = "Hard"
    oos["year"] = 2025
    oos["date"] = pd.to_datetime(["2025-06-01", "2025-06-02", "2025-06-03"])
    extra = vb.parse(payload(), "atp", 2025)
    extra = pd.concat(
        [
            extra,
            extra.assign(
                date=pd.Timestamp("2025-06-03"),
                winner_key="charlie three",
                loser_key="zulu seven",
                provider_match_id="new2",
            ),
        ],
        ignore_index=True,
    )
    extra.attrs["receipts"] = [dict(sha256="a" * 64, license="CC BY 4.0")]
    monkeypatch.setattr(vb, "load", lambda *a: extra)
    monkeypatch.setattr(compare, "load_odds", lambda *a, **kw: _odds(oos).iloc[:2])
    sc = compare.scorecard_from_oos("atp", oos)
    assert sc["matched"] == 3 and sc["lastMatchedDate"] == "2025-06-03"
    assert sc["sources"]["providers"] == {"tennis-data": 2, "valuebetennis": 1}
    data = _healthy_data()
    data["market"] = sc
    assert not any(
        f.code == "output.market.provider_provenance_invalid"
        for f in health.output_findings("atp", _oc(data=data), NOW)
    )
    del sc["sources"]["attribution"]
    hit = [
        f
        for f in health.output_findings("atp", _oc(data=data), NOW)
        if f.code == "output.market.provider_provenance_invalid"
    ]
    assert hit and health._gate_blocks(hit[0])


def test_supplement_works_without_legacy_files_and_rejects_ambiguous_rematches(monkeypatch):
    oos = _oos().iloc[:1].copy()
    oos["surface"] = "Hard"
    oos["year"] = 2025
    oos["date"] = pd.Timestamp("2025-06-01")
    extra = vb.parse(payload(), "atp", 2025)
    monkeypatch.setattr(vb, "load", lambda *a: extra)

    def absent(*a, **kw):
        raise FileNotFoundError

    monkeypatch.setattr(compare, "load_odds", absent)
    scorecard = compare.scorecard_from_oos("atp", oos)
    assert scorecard["matched"] == 1
    assert scorecard["sources"]["label"] == "Valuebetennis-recorded Pinnacle closing odds"
    # One independently observed quote must never settle two model decisions.
    rematch = pd.concat([oos, oos.assign(date=pd.Timestamp("2025-06-02"))])
    assert compare.scorecard_from_oos("atp", rematch)["matched"] == 0
    # Initials collide under the historical provider's key; full names must agree.
    collision = oos.assign(winner_name="Alfred One")
    assert compare.scorecard_from_oos("atp", collision)["matched"] == 0
