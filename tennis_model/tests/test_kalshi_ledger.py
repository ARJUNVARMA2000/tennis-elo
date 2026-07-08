"""Kalshi ledger: orientation invariance, join windows, upsert freezing.

Synthetic snapshots + result frames; the forecast log and ledger paths are
redirected to tmp_path — no network, no real data dirs touched.
"""

import json

import pandas as pd
import pytest
import tennis_model.eval.kalshi_ledger as kl
from tennis_model.eval.kalshi_ledger import build_rows, devig, refresh_ledger, upsert

TOUR = "atp"


def _snap_event(ticker="KXATPMATCH-26JUL08COBFER", occ="2026-07-08T13:00:00Z",
                name_a="Flavio Cobolli", name_b="Arthur Fery",
                mid_a=0.70, mid_b=0.31, result_a="yes", result_b="no",
                rules=None, kind="candle"):
    """One snapshot entry in data/kalshi.py's stored order (a/b as given here —
    build_rows must re-sort by name_key itself)."""
    def _tick(name):        # real tickers are per-player (-COB), not positional
        return f"{ticker}-{name.split()[-1][:3].upper()}"
    return {
        "occurrence": occ, "status": "settled",
        "a": {"ticker": _tick(name_a), "name": name_a, "result": result_a,
              "volume": 100.0, "oi": 50.0, "liquidity": 0.0},
        "b": {"ticker": _tick(name_b), "name": name_b, "result": result_b,
              "volume": 60.0, "oi": 30.0, "liquidity": 0.0},
        "rules": rules or {"tournament": "Wimbledon", "round": "QF"},
        "price": {"kind": kind, "ts": "2026-07-08T12:55:00Z",
                  "mid_a": mid_a, "mid_b": mid_b,
                  "mid_a_t30": mid_a, "mid_b_t30": mid_b, "spread_max": 0.01},
    }


def _snaps(*events):
    return {"events": {e["a"]["ticker"].rsplit("-", 1)[0]: e for e in events},
            "skipped": {}}


def _df(rows):
    base = {"winner_rank": 10.0, "loser_rank": 20.0, "tourney_name": "Wimbledon",
            "round": "QF", "surface_b": "Grass", "tier": "grand_slam", "best_of": 5,
            "completed": True, "walkover": False}
    return pd.DataFrame([{**base, **r} for r in rows]).assign(
        date=lambda d: pd.to_datetime(d["date"]))


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Redirect ledger + forecast-log paths and neutralize the live-ranks fallback."""
    monkeypatch.setattr(kl, "KALSHI_LEDGER_DIR", tmp_path / "ledger")
    monkeypatch.setattr(kl, "FORECAST_DIR", tmp_path / "forecast_log")
    monkeypatch.setattr(kl, "load_rankings", lambda tour: {})
    (tmp_path / "forecast_log").mkdir()
    return tmp_path


def _write_log(env, records):
    p = env / "forecast_log" / f"{TOUR}.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


WIMBLEDON = [{"date": "2026-06-29", "winner_name": "Flavio Cobolli",
              "loser_name": "Arthur Fery"}]     # archive rows carry the START date


# ---------------------------------------------------------------------------
# Orientation + de-vig
# ---------------------------------------------------------------------------
def test_devig_complements():
    assert abs(devig(0.66, 0.36) + devig(0.36, 0.66) - 1.0) < 1e-12


def test_orientation_invariant_to_input_order(env):
    """Swapping Kalshi listing order AND forecast-log A/B yields the identical row."""
    df = _df(WIMBLEDON)
    _write_log(env, [{"type": "match", "as_of": "2026-07-06", "playerA": "Flavio Cobolli",
                      "playerB": "Arthur Fery", "p": 0.68, "model_version": "0.1.0"}])
    fwd = build_rows(TOUR, _snaps(_snap_event()), df)[0]

    _write_log(env, [{"type": "match", "as_of": "2026-07-06", "playerA": "Arthur Fery",
                      "playerB": "Flavio Cobolli", "p": 0.32, "model_version": "0.1.0"}])
    swapped = build_rows(TOUR, _snaps(_snap_event(
        name_a="Arthur Fery", name_b="Flavio Cobolli", mid_a=0.31, mid_b=0.70,
        result_a="no", result_b="yes")), df)[0]

    # player_a = smaller name_key = Arthur Fery in both worlds
    assert fwd["player_a"] == swapped["player_a"] == "Arthur Fery"
    assert fwd == swapped
    assert fwd["p_model"] == "0.3200"                      # oriented to Fery
    assert abs(float(fwd["p_kalshi"]) - 0.31 / 1.01) < 1e-4    # CSV stores 4dp
    assert fwd["a_won"] == "0" and fwd["winner"] == "Flavio Cobolli"
    assert fwd["kalshi_result_a"] == "no"


def test_placeholder_dated_market_joins_result_days_later(env):
    """Kalshi creates markets at draw time — play can trail occurrence by ~a week."""
    rows = build_rows(TOUR, _snaps(_snap_event(occ="2026-05-16T10:00:00Z")),
                      _df([{**WIMBLEDON[0], "date": "2026-05-22"}]))
    assert rows[0]["match_status"] == "matched"


def test_requote_anchors_to_morning_of_match_day_once(env, monkeypatch):
    """Every matched row's scoring quote is fetched at 08:00 UTC on the result
    row's date (Kalshi's occurrence timestamps mutate on settled markets), and
    never again once the ledger row is candle-frozen."""
    import tennis_model.data.kalshi as kal
    calls = []
    def fake_quotes(tour, ticker, cutoff):
        calls.append((ticker, cutoff))
        return {"mid": 0.55, "mid_t30": 0.54, "spread": 0.02, "ts": cutoff - 300}
    monkeypatch.setattr(kal, "fetch_prematch_quotes", fake_quotes)
    monkeypatch.setattr(kl, "load_snapshots",
                        lambda tour: _snaps(_snap_event(occ="2026-05-16T10:00:00Z")))
    df = _df([{**WIMBLEDON[0], "date": "2026-05-22"}])

    refresh_ledger(TOUR, df)
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert row["mid_a"] == "0.5500" and row["p_kalshi"] == "0.5000"
    assert len(calls) == 2                               # one per market
    assert calls[0][1] == int(pd.Timestamp("2026-05-22 08:00", tz="UTC").timestamp())

    refresh_ledger(TOUR, df)                             # frozen -> no refetch
    assert len(calls) == 2


def test_requote_failure_degrades_price_never_scores_occurrence_quote(env, monkeypatch):
    import tennis_model.data.kalshi as kal
    monkeypatch.setattr(kal, "fetch_prematch_quotes", lambda *a: None)
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(_snap_event()))
    refresh_ledger(TOUR, _df(WIMBLEDON))
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert row["price_kind"] == "none" and row["p_kalshi"] == "" and row["mid_a"] == ""


def test_slam_final_start_dated_result_still_joins(env):
    """Archive rows are dated at TOURNAMENT START — a final 13 days later must join."""
    rows = build_rows(TOUR, _snaps(_snap_event(occ="2026-07-12T14:00:00Z",
                                               rules={"tournament": "Wimbledon",
                                                      "round": "F"})),
                      _df([{**WIMBLEDON[0], "round": "F"}]))
    assert rows[0]["match_status"] == "matched"
    assert rows[0]["result_date"] == "2026-06-29"


# ---------------------------------------------------------------------------
# Result typing / rank fallback
# ---------------------------------------------------------------------------
def test_scalar_settlement_is_cancelled_not_unmatched(env):
    """result='scalar' = fair-price settlement = match never happened."""
    snaps = _snaps(_snap_event(occ="2026-05-01T10:00:00Z",
                               result_a="scalar", result_b="scalar"))
    row = build_rows(TOUR, snaps, _df([{**WIMBLEDON[0], "winner_name": "Someone",
                                        "loser_name": "Else"}]))[0]
    assert (row["match_status"], row["result_type"]) == ("cancelled", "cancelled")


def test_kalshi_alias_applies_to_join(env, monkeypatch):
    monkeypatch.setitem(kl.KALSHI_ALIASES, "flavio cobolli jr", "flavio cobolli")
    row = build_rows(TOUR, _snaps(_snap_event(name_a="Flavio Cobolli Jr")),
                     _df(WIMBLEDON))[0]
    assert row["match_status"] == "matched" and row["player_b"] == "Flavio Cobolli"


def test_walkover_and_retirement_classification(env):
    df = _df([{**WIMBLEDON[0], "completed": False, "walkover": True}])
    assert build_rows(TOUR, _snaps(_snap_event()), df)[0]["result_type"] == "walkover"
    df = _df([{**WIMBLEDON[0], "completed": False, "walkover": False}])
    assert build_rows(TOUR, _snaps(_snap_event()), df)[0]["result_type"] == "retired"


def test_rank_fallback_to_live_rankings(env, monkeypatch):
    df = _df([{**WIMBLEDON[0], "winner_rank": float("nan"), "loser_rank": float("nan")}])
    monkeypatch.setattr(kl, "load_rankings",
                        lambda tour: {"arthur fery": {"rank": 41}})
    row = build_rows(TOUR, _snaps(_snap_event()), df)[0]
    assert (row["rank_a"], row["rank_src"]) == ("41", "live")
    assert row["rank_b"] == ""                             # Cobolli in neither source


def test_ranks_map_to_oriented_sides(env):
    row = build_rows(TOUR, _snaps(_snap_event()), _df(WIMBLEDON))[0]
    assert row["rank_a"] == "20" and row["rank_b"] == "10"  # Fery lost (rank 20)


# ---------------------------------------------------------------------------
# p_model precedence + rematch disambiguation
# ---------------------------------------------------------------------------
def test_live_forecast_beats_backtest(env):
    _write_log(env, [{"type": "match", "as_of": "2026-07-06", "playerA": "Flavio Cobolli",
                      "playerB": "Arthur Fery", "p": 0.68, "model_version": "0.1.0"}])
    oos = pd.DataFrame({"date": [pd.Timestamp("2026-06-29")],
                        "winner_name": ["Flavio Cobolli"], "loser_name": ["Arthur Fery"],
                        "p_combiner": [0.61]})
    row = build_rows(TOUR, _snaps(_snap_event()), _df(WIMBLEDON), oos=oos)[0]
    assert (row["pred_source"], row["p_model"]) == ("live", "0.3200")


def test_backtest_fills_pre_log_era(env):
    oos = pd.DataFrame({"date": [pd.Timestamp("2026-06-29")],
                        "winner_name": ["Flavio Cobolli"], "loser_name": ["Arthur Fery"],
                        "p_combiner": [0.61]})
    row = build_rows(TOUR, _snaps(_snap_event()), _df(WIMBLEDON), oos=oos)[0]
    assert (row["pred_source"], row["p_model"]) == ("backtest", "0.3900")


def test_rematch_disambiguated_by_tournament_then_ambiguous_on_tie(env):
    two = _df([{**WIMBLEDON[0], "date": "2026-06-22", "tourney_name": "Eastbourne",
                "round": "R16", "tier": "atp250"},
               WIMBLEDON[0]])
    row = build_rows(TOUR, _snaps(_snap_event(occ="2026-07-01T13:00:00Z")), two)[0]
    assert (row["match_status"], row["event"]) == ("matched", "Wimbledon")

    tie = _df([WIMBLEDON[0], {**WIMBLEDON[0], "winner_name": "Arthur Fery",
                              "loser_name": "Flavio Cobolli"}])
    row = build_rows(TOUR, _snaps(_snap_event(occ="2026-07-01T13:00:00Z",
                                              rules={"tournament": None, "round": None})),
                     tie)[0]
    assert row["match_status"] == "ambiguous" and row["p_kalshi"] != ""


# ---------------------------------------------------------------------------
# Upsert: idempotency + frozen fields
# ---------------------------------------------------------------------------
def test_upsert_idempotent_bytes(env):
    rows = build_rows(TOUR, _snaps(_snap_event()), _df(WIMBLEDON))
    upsert(TOUR, rows)
    path = kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv"
    first = path.read_bytes()
    upsert(TOUR, rows)
    assert path.read_bytes() == first


def test_upsert_freezes_candle_price_and_matched_result(env):
    upsert(TOUR, build_rows(TOUR, _snaps(_snap_event()), _df(WIMBLEDON)))
    # upstream drift: price degrades to a provisional quote, result row vanishes
    drifted = build_rows(TOUR, _snaps(_snap_event(mid_a=0.99, mid_b=0.01, kind="quote")),
                         _df([{**WIMBLEDON[0], "winner_name": "Somebody Else",
                               "loser_name": "Nobody Here"}]))
    upsert(TOUR, drifted)
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert row["price_kind"] == "candle" and row["mid_a"] == "0.3100"
    assert row["match_status"] == "matched" and row["winner"] == "Flavio Cobolli"


def test_refresh_ledger_counts(env, monkeypatch):
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(_snap_event()))
    stats = refresh_ledger(TOUR, _df(WIMBLEDON), requote=False)
    # matched with a candle price but no p_model (no log, no OOS) -> not yet scoreable
    assert stats["total"] == 1 and stats["matched"] == 1 and stats["scoreable"] == 0

    _write_log(env, [{"type": "match", "as_of": "2026-07-06", "playerA": "Flavio Cobolli",
                      "playerB": "Arthur Fery", "p": 0.68, "model_version": "0.1.0"}])
    assert refresh_ledger(TOUR, _df(WIMBLEDON), requote=False)["scoreable"] == 1
