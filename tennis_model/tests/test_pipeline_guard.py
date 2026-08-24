"""Quick-mode staleness guard: a cached predictor trained on an older feature schema
must be detected (and rebuilt) instead of crashing inside XGBoost mid-refresh, and
one carrying FeatureParams that differ from the tour's current config must be
rebuilt instead of serving inference mismatched to its training frame. The same
applies to player aliases: a renamed match frame cannot reuse split rating states.

Runnable directly (`python tests/test_pipeline_guard.py`) or under pytest.
"""

from __future__ import annotations

import hashlib
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.pipeline as pipeline
from tennis_model.config import (
    MATCH_POPULATION_VERSION,
    PLAYER_ALIASES,
    WTA_DUAL_STATE_GATE_THRESHOLD,
)
from tennis_model.model.features import FEATURES, FeatureParams
from tennis_model.model.predict import TennisPredictor

from tennis_model import timing


@pytest.fixture(autouse=True)
def _isolate_stage_receipts(monkeypatch, tmp_path):
    """Pipeline guard tests must never write operational receipts into real ignored data."""
    monkeypatch.setattr(timing, "output_dir", lambda tour: tmp_path / "output" / tour)


class _Booster:
    def __init__(self, names):
        self.feature_names = names


class _Clf:
    def __init__(self, names):
        self._b = _Booster(names)

    def get_booster(self):
        return self._b


def _pred(clf, tour="atp") -> TennisPredictor:
    dual = tour == "wta" and WTA_DUAL_STATE_GATE_THRESHOLD is not None
    return TennisPredictor(
        clf=clf, iso=None, elo=None, srv=None, ctx=None, meta={}, tour=tour,
        lower_elo=object() if dual else None,
        lower_srv=object() if dual else None,
        lower_ctx=object() if dual else None,
        dual_state_threshold=WTA_DUAL_STATE_GATE_THRESHOLD if dual else None,
    )


def test_predictor_schema_guard():
    assert pipeline._predictor_current(_pred(_Clf(list(FEATURES))), "atp")
    assert not pipeline._predictor_current(_pred(_Clf(list(FEATURES)[:-2])), "atp")   # stale cache
    assert not pipeline._predictor_current(_pred(_Clf(list(FEATURES)[::-1])), "atp")  # order matters

    class _Opaque:
        def get_booster(self):
            raise AttributeError("no booster")

    assert pipeline._predictor_current(_pred(_Opaque()), "atp")   # un-introspectable: assume current
    print("ok test_predictor_schema_guard")


def test_predictor_feat_param_guard():
    """FeatureParams drift must trigger a quick-mode rebuild: pickles that shipped
    with fp=None (pipeline.build_tour pre-fix) heal on the next hourly run, and a
    FEAT_PARAM_OVERRIDES change can't keep serving a combiner trained on the old
    thresholds."""
    assert pipeline._predictor_current(_pred(_Clf(list(FEATURES)), "wta"), "wta")   # fresh build

    shipped = _pred(_Clf(list(FEATURES)), "wta")
    shipped.fp = None                                # what pipeline.build_tour used to pickle
    assert not pipeline._predictor_current(shipped, "wta")

    legacy = _pred(_Clf(list(FEATURES)), "atp")
    del legacy.fp                                    # pre-refactor pickle
    assert pipeline._predictor_current(legacy, "atp")   # defaults == atp params: no needless rebuild

    drift = _pred(_Clf(list(FEATURES)), "wta")
    drift.fp = FeatureParams(peak_age=99.0)          # config moved since this pickle was trained
    assert not pipeline._predictor_current(drift, "wta")

    # a cross-tour pickle mixup self-reports the wrong tour; the explicit arg catches it
    assert not pipeline._predictor_current(_pred(_Clf(list(FEATURES)), "wta"), "atp")
    print("ok test_predictor_feat_param_guard")


def test_predictor_player_alias_guard():
    fresh = _pred(_Clf(list(FEATURES)), "atp")
    assert pipeline._predictor_current(fresh, "atp")

    stale = _pred(_Clf(list(FEATURES)), "atp")
    stale.player_aliases = ()
    assert not pipeline._predictor_current(stale, "atp")

    legacy = _pred(_Clf(list(FEATURES)), "atp")
    del legacy.player_aliases
    assert not pipeline._predictor_current(legacy, "atp")
    print("ok test_predictor_player_alias_guard")


def test_player_aliases_are_versioned_with_the_match_population():
    """Changing a canonical identity can collapse rows across sources. Make that change
    advance the explicit population boundary so health does not compare the rebuilt count
    with an incompatible pre-alias deploy (while same-version drops remain alarmed)."""
    payload = json.dumps(sorted(PLAYER_ALIASES.items()), ensure_ascii=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
    assert (MATCH_POPULATION_VERSION, fingerprint) == (
        4,
        "3d7719b3cfe88de5e1ff43b8a0c53b6e8555863046ef1589776a746fb1af6261",
    ), "PLAYER_ALIASES changed: advance MATCH_POPULATION_VERSION and update this contract"


def test_predictor_match_population_guard():
    """A quick export cannot reuse rating state walked over a different match
    population and then label the resulting JSON with the current population version."""
    fresh = _pred(_Clf(list(FEATURES)), "wta")
    assert pipeline._predictor_current(fresh, "wta")

    stale = _pred(_Clf(list(FEATURES)), "wta")
    stale.match_population_version = MATCH_POPULATION_VERSION - 1
    assert not pipeline._predictor_current(stale, "wta")

    legacy = _pred(_Clf(list(FEATURES)), "wta")
    del legacy.match_population_version
    assert not pipeline._predictor_current(legacy, "wta")
    print("ok test_predictor_match_population_guard")


def test_predictor_dual_state_guard():
    fresh = _pred(_Clf(list(FEATURES)), "wta")
    assert pipeline._predictor_current(fresh, "wta")

    disabled = _pred(_Clf(list(FEATURES)), "wta")
    disabled.dual_state_threshold = None
    assert not pipeline._predictor_current(disabled, "wta")

    partial = _pred(_Clf(list(FEATURES)), "wta")
    partial.lower_ctx = None
    assert not pipeline._predictor_current(partial, "wta")

    legacy = _pred(_Clf(list(FEATURES)), "wta")
    del legacy.dual_state_threshold
    assert not pipeline._predictor_current(legacy, "wta")


def test_alias_stale_quick_rebuild_defers_kalshi_to_shared_budget(monkeypatch):
    """Alias drift still rebuilds the ratings state, but the tour builder returns its
    frame without starting a private Kalshi allowance. The quick caller owns one shared
    benchmark budget after every tour's forecast output is ready."""
    import tennis_model.data.kalshi as kalshi
    import tennis_model.eval.kalshi_ledger as kalshi_ledger

    frame = object()
    saved, budgets, snapshots, ledgers = [], [], [], []
    stale = _pred(_Clf(list(FEATURES)), "atp")
    stale.player_aliases = ()

    class _RebuiltPredictor:
        @classmethod
        def load(cls, tour):
            return stale

        def __init__(self, *args, tour, **kwargs):
            self.elo, self.srv, self.meta = "elo", "srv", "meta"
            self.tour = tour

        def save(self):
            saved.append(self.tour)

    @contextmanager
    def _time_budget(seconds):
        budgets.append(seconds)
        yield

    monkeypatch.setattr(pipeline, "load_matches", lambda tour: frame)
    monkeypatch.setattr(
        pipeline,
        "build_predictor_inputs",
        lambda df: ("features", "elo", "srv", "ctx", "meta"),
    )
    monkeypatch.setattr(pipeline, "main_rows", lambda features: features)
    monkeypatch.setattr(pipeline, "train_final", lambda features, **kwargs: ("clf", "iso", None))
    monkeypatch.setattr(pipeline, "TennisPredictor", _RebuiltPredictor)
    monkeypatch.setattr(pipeline, "export_all", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline, "_track", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline, "_mirror", lambda *args, **kwargs: None)
    monkeypatch.setattr(kalshi, "time_budget", _time_budget)
    def refresh_snapshots(tour, recent_days=None, *, status=None):
        snapshots.append((tour, recent_days))
        if status is not None:
            status["sweepsSucceeded"] = 2

    monkeypatch.setattr(kalshi, "refresh_snapshots", refresh_snapshots)
    monkeypatch.setattr(
        kalshi_ledger,
        "refresh_ledger",
        lambda tour, df, oos=None, requote=True: ledgers.append((tour, df, oos, requote)),
    )

    assert pipeline.build_tour_quick("atp") is frame

    assert saved == ["atp"], "alias drift no longer triggered a complete predictor rebuild"
    assert budgets == []
    assert snapshots == []
    assert ledgers == []

    saved.clear()
    budgets.clear()
    snapshots.clear()
    ledgers.clear()
    pipeline.build_tour("atp", do_backtest=False)

    assert saved == ["atp"]
    assert budgets == [pipeline.KALSHI_FULL_BUDGET_S]
    assert snapshots == [("atp", None)]
    assert ledgers == [("atp", frame, None, True)]


def test_current_quick_export_reuses_model_bound_artifacts(monkeypatch):
    """The hourly path republishes only volatile outputs when its cached predictor is
    current; daily matrices/profiles/draws stay untouched behind ``full=False``."""
    frame = object()
    predictor = _pred(_Clf(list(FEATURES)), "atp")
    predictor.elo, predictor.srv, predictor.meta = "elo", "srv", "meta"
    calls = []

    monkeypatch.setattr(pipeline, "load_matches", lambda tour: frame)
    monkeypatch.setattr(pipeline, "_health_manifest", lambda tour, df: calls.append(("health", tour, df)))
    monkeypatch.setattr(pipeline.TennisPredictor, "load", lambda tour: predictor)
    monkeypatch.setattr(
        pipeline,
        "export_all",
        lambda *args, **kwargs: calls.append(("export", args, kwargs)),
    )
    enriched = [{"playerA": "A", "playerB": "B"}]
    monkeypatch.setattr(
        pipeline, "_prepare_upcoming",
        lambda tour, predictor, df: calls.append(("prepare", tour)) or enriched,
    )
    monkeypatch.setattr(
        pipeline, "_track",
        lambda tour, predictor, df, rows: calls.append(("track", rows)),
    )
    monkeypatch.setattr(
        pipeline, "_forecast_products",
        lambda tour, predictor, df, rows: calls.append(("forecast", rows)),
    )
    monkeypatch.setattr(pipeline, "_mirror", lambda *args: None)

    assert pipeline.build_tour_quick("atp") is frame
    export_call = next(call for call in calls if call[0] == "export")
    assert export_call[2]["full"] is False
    assert export_call[2]["oos"] is None
    assert ("health", "atp", frame) in calls
    assert calls.count(("prepare", "atp")) == 1
    assert ("track", enriched) in calls and ("forecast", enriched) in calls


def test_quick_tour_exports_overlap_and_preserve_requested_mapping(monkeypatch, tmp_path):
    import threading

    barrier = threading.Barrier(2)
    active, peak = 0, 0
    lock = threading.Lock()

    def build(tour):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        barrier.wait(timeout=2)
        with lock:
            active -= 1
        payload = f"{tour}-artifact"
        (tmp_path / f"{tour}.json").write_text(payload, encoding="utf-8")
        return f"{tour}-frame"

    monkeypatch.setattr(pipeline, "build_tour_quick", build)
    frames = pipeline._build_quick_tours(["atp", "wta"])
    assert peak == 2
    assert frames == {"atp": "atp-frame", "wta": "wta-frame"}
    parallel_artifacts = {
        tour: (tmp_path / f"{tour}.json").read_text(encoding="utf-8")
        for tour in ("atp", "wta")
    }
    assert parallel_artifacts == {"atp": "atp-artifact", "wta": "wta-artifact"}

    calls = []
    monkeypatch.setattr(
        pipeline, "build_tour_quick", lambda tour: calls.append(tour) or f"{tour}-frame")
    assert pipeline._build_quick_tours(["wta"]) == {"wta": "wta-frame"}
    assert calls == ["wta"]


def test_wta_full_build_keeps_main_exports_and_gates_secondary_state(monkeypatch):
    from types import SimpleNamespace

    threshold = WTA_DUAL_STATE_GATE_THRESHOLD
    main_df, enriched_df = object(), object()
    dual = SimpleNamespace(
        base_features="base-features", enriched_features="enriched-features",
        elo="main-elo", srv="main-srv", ctx="main-ctx", meta="main-meta",
        lower_elo="lower-elo", lower_srv="lower-srv", lower_ctx="lower-ctx",
    )
    calls, built = [], {}

    def _load(tour, include_lower=None):
        calls.append(("load", tour, include_lower))
        return enriched_df if include_lower else main_df

    class _Predictor:
        def __init__(self, *args, **kwargs):
            built["args"], built["kwargs"] = args, kwargs
            self.elo, self.srv, self.meta = args[2], args[3], args[5]
            self.trained_at = "now"

        def save(self):
            calls.append(("save",))

    monkeypatch.setattr(pipeline, "load_matches", _load)
    monkeypatch.setattr(pipeline, "_health_manifest", lambda tour, df: calls.append(("health", df)))
    monkeypatch.setattr(
        pipeline, "build_dual_state_inputs",
        lambda main, enriched, tour: dual,
    )
    monkeypatch.setattr(
        pipeline, "walk_forward_state_gate",
        lambda base, enriched, thresholds, **kwargs: {threshold: "gated-oos"},
    )
    monkeypatch.setattr(
        pipeline, "train_final",
        lambda feat, **kwargs: ("clf", "iso", None),
    )
    monkeypatch.setattr(pipeline, "TennisPredictor", _Predictor)
    monkeypatch.setattr(
        pipeline, "export_all",
        lambda *args, **kwargs: calls.append(("export", args, kwargs)),
    )
    monkeypatch.setattr(pipeline, "_market_scorecard", lambda *args: None)
    monkeypatch.setattr(pipeline, "_track", lambda *args: None)
    monkeypatch.setattr(pipeline, "_forecast_products", lambda *args: None)
    monkeypatch.setattr(pipeline, "_mirror", lambda *args: None)

    assert pipeline.build_tour("wta", do_backtest=True, run_kalshi=False) is main_df
    assert calls[:3] == [("load", "wta", False), ("health", main_df),
                         ("load", "wta", True)]
    assert built["args"][:6] == ("clf", "iso", "main-elo", "main-srv", "main-ctx",
                                  "main-meta")
    assert built["kwargs"]["lower_elo"] == "lower-elo"
    assert built["kwargs"]["lower_srv"] == "lower-srv"
    assert built["kwargs"]["lower_ctx"] == "lower-ctx"
    assert built["kwargs"]["dual_state_threshold"] == threshold
    exported = next(call for call in calls if call[0] == "export")
    assert exported[1][1] is main_df
    assert exported[2]["oos"] == "gated-oos"


def test_quick_kalshi_uses_one_budget_and_never_requotes(monkeypatch):
    import tennis_model.data.kalshi as kalshi
    import tennis_model.eval.kalshi_ledger as kalshi_ledger

    frames = {"atp": object(), "wta": object()}
    budgets, snapshots, ledgers = [], [], []

    @contextmanager
    def _time_budget(seconds):
        budgets.append(seconds)
        yield

    monkeypatch.setattr(kalshi, "time_budget", _time_budget)
    def refresh_snapshots(tour, recent_days=None, *, status=None):
        snapshots.append((tour, recent_days))
        if status is not None:
            status["sweepsSucceeded"] = 2

    monkeypatch.setattr(kalshi, "refresh_snapshots", refresh_snapshots)
    monkeypatch.setattr(
        kalshi_ledger,
        "refresh_ledger",
        lambda tour, df, oos=None, requote=True: ledgers.append((tour, df, oos, requote)),
    )

    pipeline._quick_kalshi(["atp", "wta"], frames)

    assert budgets == [pipeline.KALSHI_QUICK_BUDGET_S]
    assert snapshots == [
        ("atp", pipeline.QUICK_KALSHI_DAYS),
        ("wta", pipeline.QUICK_KALSHI_DAYS),
    ]
    assert ledgers == [
        ("atp", frames["atp"], None, False),
        ("wta", frames["wta"], None, False),
    ]


def test_quick_kalshi_failure_does_not_starve_the_other_tour(monkeypatch):
    import tennis_model.data.kalshi as kalshi
    import tennis_model.eval.kalshi_ledger as kalshi_ledger

    seen = []

    @contextmanager
    def _time_budget(_seconds):
        yield

    def snapshots(tour, recent_days=None, *, status=None):
        seen.append(("snapshot", tour, recent_days))
        if tour == "atp":
            raise RuntimeError("temporary ATP market failure")
        if status is not None:
            status["sweepsSucceeded"] = 2

    monkeypatch.setattr(kalshi, "time_budget", _time_budget)
    monkeypatch.setattr(kalshi, "refresh_snapshots", snapshots)
    monkeypatch.setattr(
        kalshi_ledger,
        "refresh_ledger",
        lambda tour, df, oos=None, requote=True: seen.append(("ledger", tour, requote)),
    )

    pipeline._quick_kalshi(["atp", "wta"], {"atp": object(), "wta": object()})

    assert seen == [
        ("snapshot", "atp", pipeline.QUICK_KALSHI_DAYS),
        ("snapshot", "wta", pipeline.QUICK_KALSHI_DAYS),
        ("ledger", "wta", False),
    ]


def test_download_layer_reuses_live_events_for_complete_draws(monkeypatch):
    import tennis_model.data.download as download
    import tennis_model.data.draws as draws
    import tennis_model.data.live as live

    tours = ("atp", "wta")
    shared = {"atp": [object()], "wta": [object()]}
    calls = []
    monkeypatch.setattr(live, "download_live", lambda got: calls.append(("live", got)) or shared)
    monkeypatch.setattr(
        draws,
        "download_tournament_draws",
        lambda got, events_by_tour=None: calls.append(("draws", got, events_by_tour)),
    )

    download._download_live_and_draws(tours)

    assert calls == [("live", tours), ("draws", tours, shared)]


def test_quick_refresh_updates_current_atp_stats_before_export(monkeypatch):
    """A cached current-year stats file can stop before a just-completed ATP final.
    Quick mode must refresh that lightweight overlay before loading/exporting matches;
    WTA's rate-limited stats API remains outside the hourly path."""
    import tennis_model.data.download as download
    import tennis_model.data.draws as draws
    import tennis_model.data.live as live
    import tennis_model.data.rankings as rankings

    calls = []
    monkeypatch.setattr(
        download,
        "download_tml_stats",
        lambda **kwargs: calls.append(("atp_stats", kwargs)) or ([], []),
    )
    shared_events = {"atp": [object()], "wta": [object()]}
    monkeypatch.setattr(
        live,
        "download_live",
        lambda tours: calls.append(("live", tuple(tours))) or shared_events,
    )
    monkeypatch.setattr(
        draws,
        "download_tournament_draws",
        lambda tours, events_by_tour=None: calls.append(
            ("draws", tuple(tours), events_by_tour)
        ),
    )
    monkeypatch.setattr(
        rankings,
        "download_rankings",
        lambda tours: calls.append(("rankings", tuple(tours))),
    )
    frames = {"atp": object(), "wta": object()}
    monkeypatch.setattr(
        pipeline,
        "build_tour_quick",
        lambda tour: calls.append(("build", tour)) or frames[tour],
    )
    monkeypatch.setattr(
        pipeline,
        "_quick_kalshi",
        lambda tours, got: calls.append(("kalshi", tuple(tours), got)),
    )
    monkeypatch.setattr(pipeline, "_kalshi_report", lambda tours: calls.append(("report", tuple(tours))))

    monkeypatch.setattr(sys, "argv", ["pipeline", "--tour", "all", "--quick"])
    pipeline.main()
    assert calls[:4] == [
        ("atp_stats", {"full": False, "retries": 1}),
        ("live", ("atp", "wta")),
        ("draws", ("atp", "wta"), shared_events),
        ("rankings", ("atp", "wta")),
    ]
    assert set(calls[4:6]) == {("build", "atp"), ("build", "wta")}
    assert calls[6:] == [
        ("kalshi", ("atp", "wta"), frames),
        ("report", ("atp", "wta")),
    ]

    calls.clear()
    monkeypatch.setattr(sys, "argv", ["pipeline", "--tour", "wta", "--quick"])
    pipeline.main()
    assert not any(call[0] == "atp_stats" for call in calls)
    assert ("build", "wta") in calls




# --- the ratings walk must survive a failing backtest (2026-07-25) -----------------------

def test_a_failing_backtest_does_not_cost_the_ratings_walk():
    """`walk_forward` produces accuracy.json — reported metrics, nothing the shipped model
    depends on — but it runs BEFORE train_final, so an exception in it used to abort
    build_tour before `predictor.save()`. A completed re-walk of 283k matches was thrown
    away over a reporting artifact, and (because a red job never saved the data cache) the
    next run restored the OLD model. Ratings must survive it."""
    import tennis_model.pipeline as pl

    saved = {}

    class _Pred:
        def __init__(self, *a, **k):
            self.elo = self.srv = self.meta = None
        def save(self):
            saved["yes"] = True

    orig = (pl.load_matches, pl.build_predictor_inputs, pl.main_rows, pl.walk_forward,
            pl.train_final, pl.TennisPredictor, pl.export_all, pl._market_scorecard,
            pl._track, pl._kalshi, pl._mirror)
    try:
        pl.load_matches = lambda tour: "df"
        pl.build_predictor_inputs = lambda df: ("feat", "elo", "srv", "ctx", "meta")
        pl.main_rows = lambda feat: feat
        pl.train_final = lambda feat, **k: ("clf", "iso", None)
        pl.TennisPredictor = _Pred
        pl.export_all = lambda *a, **k: None
        pl._market_scorecard = lambda *a, **k: None
        pl._track = lambda *a, **k: None
        pl._kalshi = lambda *a, **k: None
        pl._mirror = lambda *a, **k: None

        def _boom(*a, **k):
            raise KeyError(256)          # the real 2026-07-11 crash shape
        pl.walk_forward = _boom

        pl.build_tour("atp", do_backtest=True)      # must NOT raise
        assert saved.get("yes"), "predictor.save() was skipped after a backtest failure"
    finally:
        (pl.load_matches, pl.build_predictor_inputs, pl.main_rows, pl.walk_forward,
         pl.train_final, pl.TennisPredictor, pl.export_all, pl._market_scorecard,
         pl._track, pl._kalshi, pl._mirror) = orig
    print("ok test_a_failing_backtest_does_not_cost_the_ratings_walk")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
