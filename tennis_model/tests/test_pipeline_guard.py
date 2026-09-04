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
from tennis_model.model.features import FEATURES
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


def test_predictor_current_delegates_to_the_shared_strict_guard(monkeypatch):
    from tennis_model.model import artifact
    from tennis_model.model.artifact import (
        PredictorArtifactError,
        PredictorArtifactReason,
    )

    predictor = object()
    calls = []

    def accept(value, tour):
        calls.append((value, tour))

    monkeypatch.setattr(artifact, "validate_predictor_structure", accept)
    assert pipeline._predictor_current(predictor, "atp")
    assert calls == [(predictor, "atp")]

    def reject(*_args, **_kwargs):
        raise PredictorArtifactError(PredictorArtifactReason.BOOSTER_INVALID)

    monkeypatch.setattr(artifact, "validate_predictor_structure", reject)
    assert not pipeline._predictor_current(predictor, "atp")


def test_predictor_schema_guard_is_fail_closed_for_unfitted_or_opaque_stubs():
    """The old guard assumed an unreadable booster was current; Round 4A rebuilds it."""
    assert not pipeline._predictor_current(_pred(_Clf(list(FEATURES))), "atp")

    class _Opaque:
        def get_booster(self):
            raise AttributeError("no booster")

    assert not pipeline._predictor_current(_pred(_Opaque()), "atp")


@pytest.mark.parametrize(
    "reason_name",
    [
        "ENVELOPE_MISSING_FOR_CURRENT_PAYLOAD",
        "PAYLOAD_CHECKSUM_MISMATCH",
        "PENDING_IO",
    ],
)
def test_quick_rebuilds_when_artifact_load_rejects_cache(monkeypatch, reason_name):
    from tennis_model.model.artifact import (
        PredictorArtifactError,
        PredictorArtifactReason,
    )

    frame = object()
    rebuilt = object()
    calls = []
    monkeypatch.setattr(pipeline, "load_matches", lambda _tour: frame)
    monkeypatch.setattr(pipeline, "_health_manifest", lambda *_args: None)

    def reject(_tour):
        raise PredictorArtifactError(getattr(PredictorArtifactReason, reason_name))

    monkeypatch.setattr(pipeline.TennisPredictor, "load", staticmethod(reject))
    monkeypatch.setattr(
        pipeline,
        "build_tour",
        lambda tour, do_backtest, **kwargs: calls.append(
            (tour, do_backtest, kwargs)
        ) or rebuilt,
    )

    assert pipeline.build_tour_quick("atp") is rebuilt
    assert calls == [(
        "atp",
        False,
        {"run_kalshi": False, "refresh_tennis_abstract": False},
    )]


def test_player_aliases_are_versioned_with_the_match_population():
    """Changing a canonical identity can collapse rows across sources. Make that change
    advance the explicit population boundary so health does not compare the rebuilt count
    with an incompatible pre-alias deploy (while same-version drops remain alarmed)."""
    payload = json.dumps(sorted(PLAYER_ALIASES.items()), ensure_ascii=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
    assert (MATCH_POPULATION_VERSION, fingerprint) == (
        5,
        "a9c17b6eeb8082dd4aaa267f88e9f429d793fa7d0ef3e5d1560567ec5507eb1d",
    ), "PLAYER_ALIASES changed: advance MATCH_POPULATION_VERSION and update this contract"


def test_alias_stale_quick_rebuild_defers_kalshi_to_shared_budget(monkeypatch):
    """Alias drift still rebuilds the ratings state, but the tour builder returns its
    frame without starting a private Kalshi allowance. The quick caller owns one shared
    benchmark budget after every tour's forecast output is ready."""
    import tennis_model.data.kalshi as kalshi
    import tennis_model.eval.kalshi_ledger as kalshi_ledger

    frame = object()
    saved, budgets, snapshots, ledgers, benchmarks = [], [], [], [], []
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
    monkeypatch.setattr(
        pipeline,
        "_tennis_abstract_benchmark",
        lambda tour, *_args, refresh_external: benchmarks.append(
            (tour, refresh_external)
        ),
    )
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
    assert benchmarks == [("atp", False)]

    saved.clear()
    budgets.clear()
    snapshots.clear()
    ledgers.clear()
    benchmarks.clear()
    pipeline.build_tour("atp", do_backtest=False)

    assert saved == ["atp"]
    assert budgets == [pipeline.KALSHI_FULL_BUDGET_S]
    assert snapshots == [("atp", None)]
    assert ledgers == [("atp", frame, None, True)]
    assert benchmarks == [("atp", True)]


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
    monkeypatch.setattr(pipeline, "_predictor_current", lambda predictor, tour: True)
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
        pipeline,
        "_tennis_abstract_benchmark",
        lambda tour, predictor, df, *, refresh_external: calls.append(
            ("benchmark", refresh_external)
        ),
    )
    monkeypatch.setattr(
        pipeline, "_forecast_products",
        lambda tour, predictor, df, rows: calls.append(("forecast", rows)),
    )

    assert pipeline.build_tour_quick("atp") is frame
    export_call = next(call for call in calls if call[0] == "export")
    assert export_call[2]["full"] is False
    assert export_call[2]["oos"] is None
    assert ("health", "atp", frame) in calls
    assert calls.count(("prepare", "atp")) == 1
    assert ("track", enriched) in calls and ("forecast", enriched) in calls
    assert ("benchmark", False) in calls

    calls.clear()
    assert pipeline.build_tour_quick("atp", force_static=True) is frame
    bootstrap_export = next(call for call in calls if call[0] == "export")
    assert bootstrap_export[2]["full"] is True
    assert bootstrap_export[2]["oos"] is None


def test_quick_tour_exports_overlap_and_preserve_requested_mapping(monkeypatch, tmp_path):
    import threading

    barrier = threading.Barrier(2)
    active, peak = 0, 0
    lock = threading.Lock()

    def build(tour, **kwargs):
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
        pipeline,
        "build_tour_quick",
        lambda tour, **kwargs: calls.append(tour) or f"{tour}-frame",
    )
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
    monkeypatch.setattr(pipeline, "_tennis_abstract_benchmark", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline, "_forecast_products", lambda *args: None)

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
    context, carried = object(), object()
    plan = pipeline._ReleasePlan(context=context, carried=carried, bootstrap=False)
    monkeypatch.setattr(
        pipeline,
        "_begin_release",
        lambda mode: calls.append(("lineage-begin", mode)) or plan,
    )
    monkeypatch.setattr(
        pipeline,
        "_seal_release",
        lambda got, got_plan, produced: calls.append(
            ("lineage-seal", got, got_plan, produced.snapshot())
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "build_tour_quick",
        lambda tour, **kwargs: calls.append(
            ("build", tour, kwargs.get("force_static"))
        ) or frames[tour],
    )
    monkeypatch.setattr(
        pipeline,
        "_quick_kalshi",
        lambda tours, got: calls.append(("kalshi", tuple(tours), got)),
    )
    monkeypatch.setattr(
        pipeline,
        "_kalshi_report",
        lambda tours: calls.append(("report", tuple(tours))),
    )
    monkeypatch.setattr(
        pipeline,
        "_unbless_partial_output",
        lambda: calls.append(("partial-unbless",)),
    )

    monkeypatch.setattr(sys, "argv", ["pipeline", "--tour", "all", "--quick"])
    pipeline.main()
    assert calls[:4] == [
        ("atp_stats", {"full": False, "retries": 1}),
        ("live", ("atp", "wta")),
        ("draws", ("atp", "wta"), shared_events),
        ("rankings", ("atp", "wta")),
    ]
    assert calls[4] == ("lineage-begin", "quick")
    assert set(calls[5:7]) == {
        ("build", "atp", False), ("build", "wta", False)
    }
    assert calls[7:9] == [
        ("kalshi", ("atp", "wta"), frames),
        ("report", ("atp", "wta")),
    ]
    seal = calls[9]
    assert seal[:3] == ("lineage-seal", frames, plan)
    assert seal[3] == {"atp": (), "wta": ()}

    calls.clear()
    bootstrap_plan = pipeline._ReleasePlan(
        context=context,
        carried=None,
        bootstrap=True,
    )
    monkeypatch.setattr(
        pipeline,
        "_begin_release",
        lambda mode: calls.append(("lineage-begin", mode)) or bootstrap_plan,
    )
    pipeline.main()
    assert {
        call for call in calls if call[0] == "build"
    } == {
        ("build", "atp", True),
        ("build", "wta", True),
    }
    assert next(call for call in calls if call[0] == "lineage-seal")[2] is bootstrap_plan

    calls.clear()
    monkeypatch.setattr(sys, "argv", ["pipeline", "--tour", "wta", "--quick"])
    pipeline.main()
    assert not any(call[0] == "atp_stats" for call in calls)
    assert ("partial-unbless",) in calls
    assert ("build", "wta", False) in calls
    assert not any(call[0].startswith("lineage-") for call in calls)
    assert ("report", ("wta",)) in calls
    assert not hasattr(pipeline, "_mirror")


def test_full_all_uses_one_parent_release_and_never_worker_publishes(monkeypatch):
    calls = []
    context, carried = object(), object()
    plan = pipeline._ReleasePlan(context=context, carried=carried, bootstrap=False)
    frames = {"atp": object(), "wta": object()}
    monkeypatch.setattr(
        pipeline,
        "_begin_release",
        lambda mode: calls.append(("begin", mode)) or plan,
    )
    monkeypatch.setattr(
        pipeline,
        "build_tour",
        lambda tour, backtest, **kwargs: calls.append(
            ("build", tour, backtest, kwargs)
        ) or frames[tour],
    )
    monkeypatch.setattr(
        pipeline,
        "_kalshi_report",
        lambda tours: calls.append(("report", tuple(tours))),
    )
    monkeypatch.setattr(
        pipeline,
        "_seal_release",
        lambda got, got_plan, produced: calls.append(
            ("seal", got, got_plan, produced.snapshot())
        ),
    )
    monkeypatch.setattr(sys, "argv", ["pipeline", "--tour", "all", "--backtest"])

    pipeline.main()

    assert calls[:4] == [
        ("begin", "full"),
        ("build", "atp", True, {}),
        ("build", "wta", True, {}),
        ("report", ("atp", "wta")),
    ]
    assert calls[4][:3] == ("seal", frames, plan)
    assert calls[4][3] == {"atp": (), "wta": ()}


def test_invalid_tour_stops_before_download_build_or_pointer_mutation(
    monkeypatch,
    tmp_path,
):
    root = tmp_path / "output"
    root.mkdir()
    manifest = root / "release-manifest.json"
    receipt = root / "release-accepted.private"
    manifest.write_bytes(b"existing manifest")
    receipt.write_bytes(b"existing receipt")
    calls = []
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", root)
    monkeypatch.setattr(
        pipeline,
        "_unbless_partial_output",
        lambda: calls.append("unbless"),
    )
    monkeypatch.setattr(
        pipeline,
        "build_tour",
        lambda *_args, **_kwargs: calls.append("build"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["pipeline", "--tour", "apt", "--quick", "--download"],
    )

    with pytest.raises(SystemExit) as caught:
        pipeline.main()

    assert caught.value.code == 2
    assert calls == []
    assert manifest.read_bytes() == b"existing manifest"
    assert receipt.read_bytes() == b"existing receipt"


def test_begin_release_keeps_an_exact_accepted_quick_parent(monkeypatch):
    from types import SimpleNamespace

    from tennis_model import artifact_lineage as lineage

    parent_id = "11111111-1111-4111-8111-111111111111"
    accepted = SimpleNamespace(release_id=parent_id)
    carried = SimpleNamespace(accepted=accepted)
    unblessed = []
    monkeypatch.setattr(
        lineage,
        "carry_forward_release",
        lambda source, destination: carried,
    )
    monkeypatch.setattr(
        lineage,
        "unbless_release_for_mutation",
        lambda root: unblessed.append(root),
    )

    plan = pipeline._begin_release("quick")

    assert plan.carried is carried
    assert not plan.bootstrap
    assert plan.context.mode == "quick"
    assert plan.context.parent == parent_id
    assert unblessed == [pipeline.OUTPUT_DIR]


@pytest.mark.parametrize("requested_mode", ["full", "quick"])
def test_begin_release_cold_cache_initializes_parentless_full_bootstrap(
    monkeypatch, tmp_path, requested_mode
):
    output_parent = tmp_path / "data"
    output_parent.mkdir()
    output_root = output_parent / "output"
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output_root)

    plan = pipeline._begin_release(requested_mode)

    assert plan.bootstrap and plan.carried is None
    assert plan.context.mode == "full"
    assert plan.context.parent is None
    assert {path.name for path in output_root.iterdir()} == {"atp", "wta"}


def test_single_tour_cold_cache_initializes_root_before_revocation(
    monkeypatch, tmp_path
):
    output_parent = tmp_path / "data"
    output_parent.mkdir()
    output_root = output_parent / "output"
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", output_root)

    pipeline._unbless_partial_output()

    assert {path.name for path in output_root.iterdir()} == {"atp", "wta"}


@pytest.mark.parametrize(
    "reason",
    [
        "MANIFEST_MISSING",
        "ACCEPTANCE_INVALID",
        "ARTIFACT_MISMATCH",
    ],
)
def test_begin_release_promotes_missing_or_corrupt_quick_to_parentless_full(
    monkeypatch, reason
):
    from tennis_model import artifact_lineage as lineage

    def reject(*_args):
        raise lineage.ArtifactLineageError(
            getattr(lineage.LineageReason, reason),
            "broken cached lineage",
        )

    unblessed = []
    monkeypatch.setattr(lineage, "carry_forward_release", reject)
    monkeypatch.setattr(
        lineage,
        "unbless_release_for_mutation",
        lambda root: unblessed.append(root),
    )

    plan = pipeline._begin_release("quick")

    assert plan.bootstrap and plan.carried is None
    assert plan.context.mode == "full"
    assert plan.context.parent is None
    assert unblessed == [pipeline.OUTPUT_DIR]


@pytest.mark.parametrize("reason", ["PATH_INVALID", "IO_ERROR"])
def test_begin_release_propagates_unsafe_parent_failures(monkeypatch, reason):
    from tennis_model import artifact_lineage as lineage

    def reject(*_args):
        raise lineage.ArtifactLineageError(
            getattr(lineage.LineageReason, reason),
            "unsafe cached lineage",
        )

    monkeypatch.setattr(lineage, "carry_forward_release", reject)
    monkeypatch.setattr(
        lineage,
        "unbless_release_for_mutation",
        lambda _root: pytest.fail("unsafe parent must fail before pointer mutation"),
    )

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        pipeline._begin_release("quick")
    assert caught.value.reason == getattr(lineage.LineageReason, reason)


def test_begin_release_propagates_pointer_revocation_failure(monkeypatch):
    from tennis_model import artifact_lineage as lineage

    monkeypatch.setattr(
        lineage,
        "carry_forward_release",
        lambda *_args: (_ for _ in ()).throw(lineage.ArtifactLineageError(
            lineage.LineageReason.MANIFEST_MISSING,
            "no parent",
        )),
    )
    monkeypatch.setattr(
        lineage,
        "unbless_release_for_mutation",
        lambda _root: (_ for _ in ()).throw(OSError("cannot revoke")),
    )

    with pytest.raises(OSError, match="cannot revoke"):
        pipeline._begin_release("quick")


def test_bootstrap_removes_only_optional_artifacts_without_current_proof(
    monkeypatch, tmp_path
):
    from tennis_model import artifact_lineage as lineage

    root = tmp_path / "output"
    monkeypatch.setattr(pipeline, "OUTPUT_DIR", root)
    monkeypatch.setattr(pipeline, "output_dir", lambda tour: root / tour)
    for tour in lineage.TOURS:
        directory = root / tour
        directory.mkdir(parents=True)
        for filename in lineage.OPTIONAL_EVALUATION_FILES:
            (directory / filename).write_text("{}", encoding="utf-8")

    class _Produced:
        @staticmethod
        def snapshot():
            return {
                "atp": ("atp/accuracy.json",),
                "wta": ("wta/track.json",),
            }

    pipeline._remove_unproduced_bootstrap_evaluations(_Produced())

    assert (root / "atp" / "accuracy.json").exists()
    assert (root / "wta" / "track.json").exists()
    assert not (root / "atp" / "track.json").exists()
    assert not (root / "wta" / "accuracy.json").exists()
    for tour, proved in (("atp", "accuracy.json"), ("wta", "track.json")):
        assert {
            path.name for path in (root / tour).glob("*.json")
        } == {proved}


def test_seal_release_propagates_draft_failure(monkeypatch):
    from types import SimpleNamespace

    from tennis_model import artifact_lineage as lineage

    artifact_id = "11111111-1111-4111-8111-111111111111"
    context = lineage.begin_release("full")
    plan = pipeline._ReleasePlan(context=context, carried=None, bootstrap=False)
    frames = {
        tour: SimpleNamespace(
            attrs={pipeline._FRAME_PREDICTOR_ARTIFACT_ID: artifact_id}
        )
        for tour in lineage.TOURS
    }
    monkeypatch.setattr(pipeline, "_producer_revision", lambda: "git:" + "a" * 40)
    monkeypatch.setattr(pipeline, "_release_source_identity", lambda *args, **kwargs: {})

    def reject(*_args, **_kwargs):
        raise lineage.ArtifactLineageError(
            lineage.LineageReason.GRAPH_INVALID,
            "draft failed",
        )

    monkeypatch.setattr(lineage, "draft_tour_release", reject)
    produced = SimpleNamespace(snapshot=lambda _tour: ())

    with pytest.raises(lineage.ArtifactLineageError) as caught:
        pipeline._seal_release(frames, plan, produced)
    assert caught.value.reason == lineage.LineageReason.GRAPH_INVALID


def test_release_source_identity_binds_registry_fields_time_and_producer(
    monkeypatch, tmp_path
):
    """The whole-tour fingerprint covers direct simulation/event inputs too.

    These caches are not derivable from the normalized match fingerprint: changing
    either can change brackets, tournament coverage, and forecasts without touching a
    match row.  Time and producer revision also distinguish byte-changing generation
    runs whose external inputs happen to be identical.
    """
    live = tmp_path / "live" / "atp"
    live.mkdir(parents=True)
    (live / "rankings.json").write_text("[]")
    (live / "fields.json").write_text('{"event": ["A"]}')
    (live / "events.json").write_text('[{"espnId": 1}]')
    monkeypatch.setattr(pipeline, "live_dir", lambda _tour: live)

    class _Frame:
        attrs = {"normalizedInputFingerprint": "normalized-v1"}
        columns = ()
        dtypes = ()

        def __len__(self):
            return 0

    frame = _Frame()
    pipeline._bind_frame_release_stage_input(
        frame,
        "forecastProducts",
        {"outputs": {"performance.json": {"sha256": "4" * 64}}},
    )
    first = pipeline._release_source_identity(
        "atp",
        frame,
        "full",
        release_created_at="2026-08-24T12:00:00Z",
        producer_revision="git:" + "a" * 40,
        accepted_parent={"releaseId": "parent-a", "manifestSha256": "1" * 64},
    )
    assert first["releaseCreatedAt"] == "2026-08-24T12:00:00Z"
    assert first["producerRevision"] == "git:" + "a" * 40
    assert first["acceptedParent"]["manifestSha256"] == "1" * 64
    assert first["fields"]["state"] == "present"
    assert first["events"]["state"] == "present"

    (live / "fields.json").write_text('{"event": ["B"]}')
    second = pipeline._release_source_identity(
        "atp",
        frame,
        "full",
        release_created_at="2026-08-24T12:00:00Z",
        producer_revision="git:" + "a" * 40,
        accepted_parent={"releaseId": "parent-a", "manifestSha256": "1" * 64},
    )
    assert second["fields"]["sha256"] != first["fields"]["sha256"]
    assert second["events"] == first["events"]
    from tennis_model.artifact_lineage import source_fingerprint
    assert source_fingerprint(first) != source_fingerprint(second)

    different_parent = dict(second)
    different_parent["acceptedParent"] = {
        "releaseId": "parent-b", "manifestSha256": "2" * 64
    }
    assert source_fingerprint(different_parent) != source_fingerprint(second)
    for key, value in (
        ("releaseCreatedAt", "2026-08-24T12:00:01Z"),
        ("producerRevision", "git:" + "b" * 40),
    ):
        changed = dict(second)
        changed[key] = value
        assert source_fingerprint(changed) != source_fingerprint(second)
    changed_event = dict(second)
    changed_event["events"] = dict(second["events"], sha256="3" * 64)
    assert source_fingerprint(changed_event) != source_fingerprint(second)
    assert source_fingerprint(second) == source_fingerprint(dict(second))

    pipeline._bind_frame_release_stage_input(
        frame,
        "forecastProducts",
        {"outputs": {"performance.json": {"sha256": "5" * 64}}},
    )
    stale_input_changed = pipeline._release_source_identity(
        "atp",
        frame,
        "full",
        release_created_at="2026-08-24T12:00:00Z",
        producer_revision="git:" + "a" * 40,
        accepted_parent=None,
    )
    bootstrap_baseline = dict(second, acceptedParent=None)
    assert stale_input_changed["stageInputs"] != bootstrap_baseline["stageInputs"]
    assert source_fingerprint(stale_input_changed) != source_fingerprint(
        bootstrap_baseline
    )


def test_producer_revision_prefers_ci_sha_and_hashes_local_source(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_SHA", "A" * 40)
    assert pipeline._producer_revision(tmp_path) == "git:" + "a" * 40

    monkeypatch.setenv("GITHUB_SHA", "a" * 40 + "\n")
    fallback = tmp_path / "fallback"
    fallback.mkdir()
    (fallback / "only.py").write_text("VALUE = 1\n")
    assert pipeline._producer_revision(fallback).startswith("src1:")

    monkeypatch.delenv("GITHUB_SHA")
    package = tmp_path / "package"
    (package / "nested").mkdir(parents=True)
    (package / "a.py").write_text("VALUE = 1\n")
    (package / "nested" / "b.py").write_text("VALUE = 2\n")
    first = pipeline._producer_revision(package)
    assert first.startswith("src1:")
    assert first == pipeline._producer_revision(package)

    (package / "nested" / "b.py").write_text("VALUE = 3\n")
    assert pipeline._producer_revision(package) != first
    changed_python = pipeline._producer_revision(package)

    (package / "ignored.txt").write_text("not runtime input\n")
    assert pipeline._producer_revision(package) == changed_python
    (package / "venue.csv").write_text("venue,value\nA,1\n")
    with_resource = pipeline._producer_revision(package)
    assert with_resource != changed_python
    (package / "venue.csv").write_text("venue,value\nA,2\n")
    assert pipeline._producer_revision(package) != with_resource




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
            pl._track, pl._tennis_abstract_benchmark, pl._kalshi)
    try:
        pl.load_matches = lambda tour: "df"
        pl.build_predictor_inputs = lambda df: ("feat", "elo", "srv", "ctx", "meta")
        pl.main_rows = lambda feat: feat
        pl.train_final = lambda feat, **k: ("clf", "iso", None)
        pl.TennisPredictor = _Pred
        pl.export_all = lambda *a, **k: None
        pl._market_scorecard = lambda *a, **k: None
        pl._track = lambda *a, **k: None
        pl._tennis_abstract_benchmark = lambda *a, **k: None
        pl._kalshi = lambda *a, **k: None

        def _boom(*a, **k):
            raise KeyError(256)          # the real 2026-07-11 crash shape
        pl.walk_forward = _boom

        pl.build_tour("atp", do_backtest=True)      # must NOT raise
        assert saved.get("yes"), "predictor.save() was skipped after a backtest failure"
    finally:
        (pl.load_matches, pl.build_predictor_inputs, pl.main_rows, pl.walk_forward,
         pl.train_final, pl.TennisPredictor, pl.export_all, pl._market_scorecard,
         pl._track, pl._tennis_abstract_benchmark, pl._kalshi) = orig
    print("ok test_a_failing_backtest_does_not_cost_the_ratings_walk")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
