"""Kalshi client parsing: event pairing, rules extraction, quote selection.

All fixture-driven — no network. The fixtures mirror real API shapes captured
2026-07-06 (see fixtures/kalshi_markets_sample.json header comment).
"""

import json
from pathlib import Path

from tennis_model.data.kalshi import (
    _dollars,
    _epoch,
    pair_events,
    parse_rules,
    select_prematch_quotes,
)

FIX = Path(__file__).parent / "fixtures"
MARKETS = json.loads((FIX / "kalshi_markets_sample.json").read_text(encoding="utf-8"))["markets"]
CANDLES = json.loads((FIX / "kalshi_candles_sample.json").read_text(encoding="utf-8"))
OCC = CANDLES["occurrence_ts"]


# ---------------------------------------------------------------------------
# pair_events
# ---------------------------------------------------------------------------
def test_pair_events_groups_and_orders_by_name_key():
    events, skipped = pair_events(MARKETS)
    assert set(events) == {"KXATPMATCH-26JUL08COBFER", "KXWTAMATCH-26JUN22MBOKEY"}
    cob = events["KXATPMATCH-26JUL08COBFER"]
    assert cob["a"]["yes_sub_title"] == "Arthur Fery"        # "arthur..." < "flavio..."
    assert cob["b"]["yes_sub_title"] == "Flavio Cobolli"
    # accents + hyphens fold before ordering: "lourdes carle muller" < "madison keys"
    wta = events["KXWTAMATCH-26JUN22MBOKEY"]
    assert wta["a"]["yes_sub_title"] == "Lourdes Carlé-Müller"


def test_pair_events_skips_non_singles_with_reasons():
    _, skipped = pair_events(MARKETS)
    assert "KXATPMATCH-26JUL01ORPHAN" in skipped          # one market only
    assert "KXATPMATCH-26JUL02DOUBLS" in skipped          # "/" in player names
    assert all(skipped.values())                          # every skip carries a reason


def test_pair_events_dedups_markets_seen_in_both_sweeps():
    events, _ = pair_events(MARKETS + MARKETS[:2])        # settled + open overlap
    assert "KXATPMATCH-26JUL08COBFER" in events


# ---------------------------------------------------------------------------
# parse_rules
# ---------------------------------------------------------------------------
def test_parse_rules_extracts_tournament_and_round():
    out = parse_rules(MARKETS[0]["rules_primary"])
    assert out == {"tournament": "Wimbledon", "round": "QF"}
    out = parse_rules(MARKETS[2]["rules_primary"])
    assert out == {"tournament": "Eastbourne", "round": "R16"}


def test_parse_rules_semifinal_not_swallowed_by_final():
    txt = ("If A wins the A vs B professional tennis match in the 2026 Halle "
           "Men Singles Semifinal after a ball has been played, then yes.")
    assert parse_rules(txt)["round"] == "SF"


def test_parse_rules_garbage_is_none_none():
    assert parse_rules("malformed") == {"tournament": None, "round": None}
    assert parse_rules(None) == {"tournament": None, "round": None}


# ---------------------------------------------------------------------------
# quote selection / scalar helpers
# ---------------------------------------------------------------------------
def test_prematch_quote_is_last_two_sided_candle_at_t5():
    q = select_prematch_quotes(CANDLES["candlesticks"], OCC)
    assert abs(q["mid"] - 0.665) < 1e-9                   # zero-volume candle at T-7m
    assert abs(q["spread"] - 0.01) < 1e-9
    assert q["ts"] == OCC - 420
    assert abs(q["mid_t30"] - 0.64) < 1e-9                # two-sided candle at T-31m


def test_prematch_quote_never_picks_inside_lead_or_in_play():
    q = select_prematch_quotes(CANDLES["candlesticks"], OCC)
    assert q["mid"] < 0.7                                 # not the T-2m (.71) or in-play (.91)


def test_prematch_quote_none_when_no_two_sided_book():
    one_sided = [c for c in CANDLES["candlesticks"] if "yes_ask" not in c]
    assert select_prematch_quotes(one_sided, OCC) is None
    assert select_prematch_quotes([], OCC) is None


def _carry(ts, bid, ask):
    return {"end_period_ts": ts,
            "yes_bid": {"close_dollars": f"{bid:.4f}"},
            "yes_ask": {"close_dollars": f"{ask:.4f}"}}


def test_settled_extreme_carry_at_window_edge_is_rejected():
    """The include_latest_before_start synthetic carry (candle at/before the window
    start) can smuggle a SETTLED book into an empty window when the anchor day
    postdates the match — mid pinned ~0.995 on the actual winner. Reject it; a quiet
    overnight carry with a live two-sided mid stays scorable."""
    window_start = OCC - 4 * 3600
    assert select_prematch_quotes([_carry(window_start, 0.99, 1.00)], OCC) is None
    q = select_prematch_quotes([_carry(window_start, 0.60, 0.62)], OCC)
    assert q is not None and abs(q["mid"] - 0.61) < 1e-9


def test_extreme_mid_inside_window_still_quotes():
    """Extremity alone is not a leak — a genuine morning book can sit at 0.99+.
    Only the pre-window carry + settled-extreme combination is rejected."""
    q = select_prematch_quotes([_carry(OCC - 3600, 0.99, 1.00)], OCC)
    assert q is not None and abs(q["mid"] - 0.995) < 1e-9


def test_dollars_and_epoch():
    assert _dollars("0.7000") == 0.7
    assert _dollars("") is None and _dollars(None) is None
    assert _epoch("1970-01-01T00:00:00Z") == 0
    assert _epoch("2026-07-06T13:00:00Z") == 1783342800   # UTC regardless of local tz
    assert _epoch("garbage") is None


# --- wall-clock budget (2026-07-27) ------------------------------------------------------

def test_time_budget_soft_fails_instead_of_hanging():
    """Every Kalshi retry is individually patient — one `_get` can spend ~420s on 429s —
    and a refresh makes hundreds of calls, so with no ceiling a rate-limiting Kalshi stalls
    the caller for hours. Run 30227056240 sat 4h in the hourly quick refresh and, via the
    deploy concurrency group, blocked every refresh behind it. An expired budget must
    return None (the soft-fail every caller already handles), not raise and not sleep."""
    import time as _time

    from tennis_model.data import kalshi

    calls = []
    orig_urlopen = kalshi.urllib.request.urlopen
    orig_sleep = kalshi.time.sleep
    try:
        kalshi.urllib.request.urlopen = lambda *a, **k: calls.append(1)  # would TypeError
        kalshi.time.sleep = lambda s: calls.append(("slept", s))
        with kalshi.time_budget(0):                      # already spent
            t0 = _time.monotonic()
            assert kalshi._get("/markets", {"x": 1}) is None
            assert _time.monotonic() - t0 < 1.0, "spent budget must return immediately"
        assert calls == [], f"expired budget still hit the network/slept: {calls}"
    finally:
        kalshi.urllib.request.urlopen = orig_urlopen
        kalshi.time.sleep = orig_sleep
    # and the budget is scoped: leaving the block restores the previous (unbounded) state
    assert kalshi._DEADLINE is None
    assert not kalshi._budget_spent()
    print("ok test_time_budget_soft_fails_instead_of_hanging")


def test_time_budget_nests_and_restores():
    """`None` means unbounded (CLI/tests); a nested block must not leak its deadline."""
    from tennis_model.data import kalshi
    with kalshi.time_budget(None):
        assert kalshi._DEADLINE is None
        with kalshi.time_budget(120):
            assert kalshi._DEADLINE is not None and not kalshi._budget_spent()
        assert kalshi._DEADLINE is None
    assert kalshi._DEADLINE is None
    print("ok test_time_budget_nests_and_restores")


def test_time_budget_caps_inflight_timeout_and_retry_sleep(monkeypatch):
    """A deadline checked only before ``urlopen`` is not a wall-clock bound: the final
    request can still take 30s and a 429 can then sleep another 120s. Both waits must be
    clipped to the time actually remaining in the enclosing refresh budget."""
    from tennis_model.data import kalshi

    clock = [100.0]
    timeouts, sleeps = [], []

    def rate_limited(_request, timeout):
        timeouts.append(timeout)
        raise kalshi.urllib.error.HTTPError("https://example.test", 429, "slow", {}, None)

    def advance(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(kalshi.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(kalshi.time, "sleep", advance)
    monkeypatch.setattr(kalshi.urllib.request, "urlopen", rate_limited)

    with kalshi.time_budget(5):
        assert kalshi._get("/markets") is None

    assert timeouts == [5.0]
    assert sleeps == [5.0]
    assert clock[0] == 105.0


def test_refresh_snapshots_reports_total_transport_and_budget_degradation(
        tmp_path, monkeypatch):
    from tennis_model.data import kalshi

    monkeypatch.setattr(kalshi, "kalshi_dir", lambda tour: tmp_path / tour)
    monkeypatch.setattr(kalshi, "fetch_markets", lambda *_args, **_kwargs: None)
    status: dict = {}
    with kalshi.time_budget(0):
        snapshots = kalshi.refresh_snapshots("atp", status=status)
        assert kalshi.budget_spent()

    assert snapshots["events"] == {}
    assert status == {
        "sweepsAttempted": 2,
        "sweepsSucceeded": 0,
        "failedSweeps": ["settled", "open"],
        "budgetSpent": True,
    }
