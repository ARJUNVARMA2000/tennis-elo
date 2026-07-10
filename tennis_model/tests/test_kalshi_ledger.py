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


# ---------------------------------------------------------------------------
# Quote-timing + join-capture leaks (audit 2026-07-09)
# ---------------------------------------------------------------------------
def _no_results():
    return _df(WIMBLEDON).iloc[0:0]


def test_pending_race_occurrence_freeze_is_requoted_when_matched(env, monkeypatch):
    """A row candle-frozen while PENDING carries the snapshot's occurrence-anchored
    quote (T-5 before scheduled start — in-play whenever play starts early). Once
    the result joins, the requoter must re-anchor it to 08:00 UTC on the result
    date; the frozen-price policy must not shield the stale print."""
    import tennis_model.data.kalshi as kal
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(_snap_event()))

    refresh_ledger(TOUR, _no_results(), requote=True)     # no result yet: not matched
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert row["match_status"] != "matched"
    assert (row["price_kind"], row["price_ts"]) == ("candle", "2026-07-08T12:55:00Z")

    calls = []
    def fake_quotes(tour, ticker, cutoff):
        calls.append(cutoff)
        return {"mid": 0.55, "mid_t30": 0.54, "spread": 0.02, "ts": cutoff - 300}
    monkeypatch.setattr(kal, "fetch_prematch_quotes", fake_quotes)
    refresh_ledger(TOUR, _df([{**WIMBLEDON[0], "date": "2026-07-08"}]))
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert row["match_status"] == "matched"
    assert calls[0] == int(pd.Timestamp("2026-07-08 08:00", tz="UTC").timestamp())
    assert row["mid_a"] == "0.5500" and row["price_ts"] == "2026-07-08T07:55:00Z"


def test_pending_race_requote_failure_degrades_over_frozen_print(env, monkeypatch):
    """If the anchor re-quote returns no valid book (thin morning, or the settled
    extreme-carry veto), the row degrades to price_kind=none — the previously
    frozen occurrence quote must not survive the upsert and get scored."""
    import tennis_model.data.kalshi as kal
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(_snap_event()))
    refresh_ledger(TOUR, _no_results(), requote=True)
    monkeypatch.setattr(kal, "fetch_prematch_quotes", lambda *a: None)
    refresh_ledger(TOUR, _df([{**WIMBLEDON[0], "date": "2026-07-08"}]))
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert row["match_status"] == "matched"
    assert (row["price_kind"], row["p_kalshi"], row["price_ts"]) == ("none", "", "")


def test_requote_falls_back_to_frozen_match_when_results_source_gaps(env, monkeypatch):
    """A transient results-source gap must not strand an occurrence-anchored quote:
    when the fresh run cannot re-match the row but the frozen prior match survives
    the merge, the requoter re-anchors using the FROZEN identity's result_date."""
    import tennis_model.data.kalshi as kal
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(_snap_event()))
    refresh_ledger(TOUR, _no_results(), requote=True)          # pending, 12:55Z frozen
    refresh_ledger(TOUR, _df([{**WIMBLEDON[0], "date": "2026-07-08"}]),
                   requote=False)                              # matched, quote stranded
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert (row["match_status"], row["price_ts"]) == ("matched", "2026-07-08T12:55:00Z")

    calls = []
    def fake_quotes(tour, ticker, cutoff):
        calls.append(cutoff)
        return {"mid": 0.55, "mid_t30": None, "spread": 0.02, "ts": cutoff - 300}
    monkeypatch.setattr(kal, "fetch_prematch_quotes", fake_quotes)
    refresh_ledger(TOUR, _no_results(), requote=True)          # results source gapped
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert calls[0] == int(pd.Timestamp("2026-07-08 08:00", tz="UTC").timestamp())
    assert (row["match_status"], row["result_date"]) == ("matched", "2026-07-08")
    assert row["price_ts"] == "2026-07-08T07:55:00Z" and row["mid_a"] == "0.5500"


def test_market_cannot_bind_result_claimed_by_another_ticker(env, monkeypatch):
    """One result row, one ticker: a market listed for a future rematch must not
    match (and double-score) the pair's previous result already in the ledger."""
    halle = _snap_event(ticker="KXATPMATCH-26JUN20COBFER", occ="2026-06-20T13:00:00Z",
                        rules={"tournament": "Halle", "round": "SF"})
    df_halle = _df([{**WIMBLEDON[0], "date": "2026-06-20", "tourney_name": "Halle",
                     "round": "SF", "tier": "atp500"}])
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(halle))
    refresh_ledger(TOUR, df_halle, requote=False)         # Halle result now claimed

    wimbledon = _snap_event(occ="2026-07-08T16:10:00Z")   # rematch market lists
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(halle, wimbledon))
    refresh_ledger(TOUR, df_halle, requote=False)         # its own result not ingested yet
    led = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")
    assert led["KXATPMATCH-26JUN20COBFER"]["result_date"] == "2026-06-20"
    assert led["KXATPMATCH-26JUL08COBFER"]["match_status"] != "matched"

    # the real rematch result lands -> the new ticker binds IT, the old row untouched
    df_both = _df([{**WIMBLEDON[0], "date": "2026-06-20", "tourney_name": "Halle",
                    "round": "SF", "tier": "atp500"},
                   {**WIMBLEDON[0], "date": "2026-07-08"}])
    refresh_ledger(TOUR, df_both, requote=False)
    led = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")
    assert led["KXATPMATCH-26JUL08COBFER"]["match_status"] == "matched"
    assert led["KXATPMATCH-26JUL08COBFER"]["result_date"] == "2026-07-08"
    assert led["KXATPMATCH-26JUN20COBFER"]["result_date"] == "2026-06-20"


def test_stale_capture_vetoed_by_tournament_rule(env):
    """A market whose sole in-window candidate is a weeks-old result of the same
    pair at a DIFFERENT event must not match: far-forward joins are legit only for
    tournament-start-dated archive rows, which agree with the parsed tournament."""
    halle_only = _df([{**WIMBLEDON[0], "date": "2026-06-20", "tourney_name": "Halle",
                       "round": "SF", "tier": "atp500"}])
    row = build_rows(TOUR, _snaps(_snap_event(occ="2026-07-08T16:10:00Z")), halle_only)[0]
    assert row["match_status"] != "matched"


def test_settlement_disagreement_never_freezes(env):
    """If Kalshi settled the market for the OTHER player, the joined result is
    provably wrong (stale capture / alias collision): ambiguous, never matched."""
    snaps = _snaps(_snap_event(result_a="no", result_b="yes"))    # Kalshi: Fery won
    row = build_rows(TOUR, snaps, _df(WIMBLEDON))[0]              # frame: Cobolli won
    assert (row["match_status"], row["result_type"]) == ("ambiguous", "pending")
    assert row["winner"] == "" and row["a_won"] == ""


def test_frozen_stale_capture_heals_and_rebinds(env, monkeypatch):
    """A previously-FROZEN wrong join (Kalshi settlement contradicts the joined
    result — the Wimbledon-market-frozen-to-Halle-result chimera) is unfrozen on
    the next run and re-binds to the real result once it exists."""
    import tennis_model.data.kalshi as kal
    bad = {c: "" for c in kl.LEDGER_COLUMNS}
    bad.update({
        "event_ticker": "KXATPMATCH-26JUL08COBFER", "tour": TOUR, "season": "2026",
        "occurrence_utc": "2026-07-08T16:10:00Z", "match_date": "2026-07-08",
        "event": "Halle", "round": "SF",
        "player_a": "Arthur Fery", "player_b": "Flavio Cobolli",
        "ticker_a": "KXATPMATCH-26JUL08COBFER-FER",
        "ticker_b": "KXATPMATCH-26JUL08COBFER-COB",
        "mid_a": "0.3100", "mid_b": "0.7000", "p_kalshi": "0.3069",
        "price_ts": "2026-07-08T07:55:00Z", "price_kind": "candle",
        "p_model": "0.3200", "pred_source": "live", "model_version": "0.1.0",
        "model_as_of": "2026-07-07",
        "match_status": "matched", "result_type": "completed",
        "winner": "Flavio Cobolli", "a_won": "0", "result_date": "2026-06-20",
        "kalshi_result_a": "yes",           # settled for Fery, joined result says Cobolli
    })
    upsert(TOUR, [bad])

    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(
        _snap_event(occ="2026-07-08T16:10:00Z", result_a="no", result_b="yes")))
    monkeypatch.setattr(kal, "fetch_prematch_quotes",
                        lambda tour, ticker, cutoff: {"mid": 0.45, "mid_t30": None,
                                                      "spread": 0.02, "ts": cutoff - 300})
    qf = _df([{**WIMBLEDON[0], "date": "2026-07-08",
               "winner_name": "Arthur Fery", "loser_name": "Flavio Cobolli"}])
    refresh_ledger(TOUR, qf)
    row = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")["KXATPMATCH-26JUL08COBFER"]
    assert (row["match_status"], row["result_date"]) == ("matched", "2026-07-08")
    assert (row["winner"], row["a_won"], row["event"]) == ("Arthur Fery", "1", "Wimbledon")
    assert row["price_ts"] == "2026-07-08T07:55:00Z" and row["p_kalshi"] == "0.5000"


def test_duplicate_claim_heals_farther_ticker(env, monkeypatch):
    """Two frozen tickers holding the same (pair, result_date) — a relist duplicate
    or stale capture that predates the claim guard — keep only the closest-
    occurrence one; the loser re-resolves without the claim and stays unmatched."""
    rows = []
    for tick, occ in [("KXATPMATCH-26JUN20COBFER", "2026-06-20T13:00:00Z"),
                      ("KXATPMATCH-26JUL08COBFER", "2026-07-08T16:10:00Z")]:
        r = {c: "" for c in kl.LEDGER_COLUMNS}
        r.update({
            "event_ticker": tick, "tour": TOUR, "season": "2026",
            "occurrence_utc": occ, "match_date": occ[:10],
            "event": "Halle", "round": "SF",
            "player_a": "Arthur Fery", "player_b": "Flavio Cobolli",
            "ticker_a": f"{tick}-FER", "ticker_b": f"{tick}-COB",
            "mid_a": "0.4500", "mid_b": "0.5500", "p_kalshi": "0.4500",
            "price_ts": "2026-06-20T07:55:00Z", "price_kind": "candle",
            "match_status": "matched", "result_type": "completed",
            "winner": "Flavio Cobolli", "a_won": "0", "result_date": "2026-06-20",
            "kalshi_result_a": "no",
        })
        rows.append(r)
    upsert(TOUR, rows)

    halle = _snap_event(ticker="KXATPMATCH-26JUN20COBFER", occ="2026-06-20T13:00:00Z",
                        rules={"tournament": "Halle", "round": "SF"})
    wim = _snap_event(occ="2026-07-08T16:10:00Z")
    monkeypatch.setattr(kl, "load_snapshots", lambda tour: _snaps(halle, wim))
    df_halle = _df([{**WIMBLEDON[0], "date": "2026-06-20", "tourney_name": "Halle",
                     "round": "SF", "tier": "atp500"}])
    refresh_ledger(TOUR, df_halle, requote=False)
    led = kl._read_ledger(kl.KALSHI_LEDGER_DIR / f"{TOUR}.csv")
    assert led["KXATPMATCH-26JUN20COBFER"]["match_status"] == "matched"
    assert led["KXATPMATCH-26JUN20COBFER"]["result_date"] == "2026-06-20"
    assert led["KXATPMATCH-26JUL08COBFER"]["match_status"] != "matched"
