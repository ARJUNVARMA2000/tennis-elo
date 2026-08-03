"""Quick-mode staleness guard: a cached predictor trained on an older feature schema
must be detected (and rebuilt) instead of crashing inside XGBoost mid-refresh, and
one carrying FeatureParams that differ from the tour's current config must be
rebuilt instead of serving inference mismatched to its training frame. The same
applies to player aliases: a renamed match frame cannot reuse split rating states.

Runnable directly (`python tests/test_pipeline_guard.py`) or under pytest.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import tennis_model.pipeline as pipeline
from tennis_model.config import MATCH_POPULATION_VERSION
from tennis_model.model.features import FEATURES, FeatureParams
from tennis_model.model.predict import TennisPredictor


class _Booster:
    def __init__(self, names):
        self.feature_names = names


class _Clf:
    def __init__(self, names):
        self._b = _Booster(names)

    def get_booster(self):
        return self._b


def _pred(clf, tour="atp") -> TennisPredictor:
    return TennisPredictor(clf=clf, iso=None, elo=None, srv=None, ctx=None,
                           meta={}, tour=tour)


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
    monkeypatch.setattr(
        kalshi,
        "refresh_snapshots",
        lambda tour, recent_days=None: snapshots.append((tour, recent_days)),
    )
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
    monkeypatch.setattr(
        kalshi,
        "refresh_snapshots",
        lambda tour, recent_days=None: snapshots.append((tour, recent_days)),
    )
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

    def snapshots(tour, recent_days=None):
        seen.append(("snapshot", tour, recent_days))
        if tour == "atp":
            raise RuntimeError("temporary ATP market failure")

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
    assert calls == [
        ("atp_stats", {"full": False, "retries": 1}),
        ("live", ("atp", "wta")),
        ("draws", ("atp", "wta"), shared_events),
        ("rankings", ("atp", "wta")),
        ("build", "atp"),
        ("build", "wta"),
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
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
