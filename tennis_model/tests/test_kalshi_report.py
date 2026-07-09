"""Kalshi report: paired-stat math, scored-set filters, end-to-end render."""

import csv

import numpy as np
import pytest
import tennis_model.eval.kalshi_report as kr
from tennis_model.eval.kalshi_ledger import LEDGER_COLUMNS
from tennis_model.eval.kalshi_report import (
    build_report,
    load_ledger,
    paired_block,
    scored_set,
    segment_table,
)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(kr, "KALSHI_LEDGER_DIR", tmp_path / "ledger")
    monkeypatch.setattr(kr, "output_dir", lambda tour: tmp_path / "output" / tour)
    (tmp_path / "ledger").mkdir()
    return tmp_path


def _row(**kw):
    base = {c: "" for c in LEDGER_COLUMNS}
    base.update({
        "event_ticker": "KXATPMATCH-26JUL01AAABBB", "tour": "atp", "season": "2026",
        "occurrence_utc": "2026-07-01T13:00:00Z", "match_date": "2026-07-01",
        "event": "Wimbledon", "round": "R32", "surface": "Grass", "tier": "grand_slam",
        "best_of": "5", "player_a": "A Player", "player_b": "B Player",
        "rank_a": "5", "rank_b": "30", "rank_src": "results",
        "mid_a": "0.6500", "mid_b": "0.3500", "p_kalshi": "0.6500",
        "p_kalshi_t30": "0.6400", "spread_max": "0.0200", "price_kind": "candle",
        "p_model": "0.7000", "pred_source": "live",
        "match_status": "matched", "result_type": "completed",
        "winner": "A Player", "a_won": "1", "kalshi_result_a": "yes",
    })
    base.update(kw)
    return base


def _write(env, rows, tour="atp"):
    with open(env / "ledger" / f"{tour}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# paired_block math
# ---------------------------------------------------------------------------
def test_paired_block_matches_hand_formula():
    pm = np.array([0.8, 0.6, 0.7, 0.4])
    pk = np.array([0.7, 0.65, 0.6, 0.5])
    blk = paired_block(pm, pk)
    d = -np.log(pk) + np.log(pm)          # positive = model better
    assert abs(blk["d_ll"] - d.mean()) < 1e-12
    assert abs(blk["d_ll_se"] - d.std(ddof=1) / 2.0) < 1e-12
    db = (1 - pk) ** 2 - (1 - pm) ** 2
    assert abs(blk["d_brier"] - db.mean()) < 1e-12
    assert blk["n"] == 4 and blk["model"]["acc"] == 0.75


def test_paired_block_empty():
    assert paired_block(np.array([]), np.array([])) == {"n": 0}


# ---------------------------------------------------------------------------
# scored-set filters + segment edges
# ---------------------------------------------------------------------------
def test_scored_set_excludes_unscoreable_rows(env):
    rows = [
        _row(),
        _row(event_ticker="T2", result_type="retired"),          # excluded (primary)
        _row(event_ticker="T3", result_type="walkover"),
        _row(event_ticker="T4", price_kind="quote"),
        _row(event_ticker="T5", spread_max="0.2000"),            # too wide
        _row(event_ticker="T6", p_model=""),
        _row(event_ticker="T7", match_status="unmatched", a_won=""),
    ]
    _write(env, rows)
    df = load_ledger("atp")
    assert len(scored_set(df)) == 1
    assert len(scored_set(df, include_retired=True)) == 2
    # winner-orientation: a lost -> p flips
    lost = _row(event_ticker="T8", a_won="0", winner="B Player")
    _write(env, [lost])
    s = scored_set(load_ledger("atp"))
    assert abs(s["p_model_w"].iloc[0] - 0.30) < 1e-9


def test_segment_edges(env):
    rows = [
        _row(),                                                   # top-20 (rank 5)
        _row(event_ticker="T2", rank_a="", rank_b="", rank_src="",
             p_kalshi="0.5000", p_kalshi_t30=""),                 # unknown rank, fav 0.5
    ]
    _write(env, rows)
    s = scored_set(load_ledger("atp"))
    segs = {r["segment"]: r for r in segment_table(s)}
    assert segs["top-20 involved"]["n"] == 1
    assert segs["rank unknown"]["n"] == 1
    assert segs["kalshi favorite 0.5-0.6"]["n"] == 1              # 0.5 lands in first bucket
    assert "kalshi favorite 0.9-1.0" not in segs


# ---------------------------------------------------------------------------
# end-to-end render
# ---------------------------------------------------------------------------
def test_build_report_renders_and_writes_json(env):
    _write(env, [_row(), _row(event_ticker="T2", a_won="0", winner="B Player",
                              pred_source="backtest")])
    out = build_report(tours=("atp",))
    md = (env / "ledger" / "report.md").read_text(encoding="utf-8")
    assert "## Headline" in md and "## Segments" in md and "## QA" in md
    assert (env / "output" / "atp" / "kalshi.json").exists()
    assert out["headline"]["pooled"]["n"] == 2


def test_build_report_survives_empty_ledger(env):
    _write(env, [])
    out = build_report(tours=("atp",))
    assert out["headline"]["pooled"]["n"] == 0
    assert (env / "ledger" / "report.md").exists()


def test_build_report_survives_missing_csv(env):
    out = build_report(tours=("atp",))
    assert out["headline"]["pooled"]["n"] == 0


def test_build_report_emits_calibration_and_receipts(env):
    import json
    _write(env, [
        _row(event_ticker="BEST", p_model="0.6000", p_kalshi="0.4000"),   # model right, market wrong
        _row(event_ticker="MISS", p_model="0.4000", p_kalshi="0.6000"),   # model wrong, market right
        _row(event_ticker="AGREE"),                                       # both right (0.70/0.65)
    ])
    build_report(tours=("atp",))
    p = json.loads((env / "output" / "atp" / "kalshi.json").read_text(encoding="utf-8"))
    assert p["calibration"]["model"] and p["calibration"]["kalshi"]
    assert len(p["bestCalls"]) == 1 and p["bestCalls"][0]["winner"] == "A Player"
    assert p["bestCalls"][0]["pModel"] == 0.6 and p["bestCalls"][0]["pKalshi"] == 0.4
    assert len(p["worstMisses"]) == 1 and p["worstMisses"][0]["pModel"] == 0.4
    assert p["disagree"] == {"n": 2, "modelRight": 1}   # BEST + MISS disagree ≥0.1; model closer only on BEST
