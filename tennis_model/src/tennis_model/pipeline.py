"""End-to-end pipeline: data -> ratings -> point model -> combiner -> JSON + model.

Run:  PYTHONPATH=src python -m tennis_model.pipeline --tour all [--download] [--backtest]

For each tour it builds the production predictor (data/output/<tour>/predictor.pkl)
and writes the full set of frontend JSON artifacts (see model/export.py). The web app
reads data/output/<tour>/*.json; copies are mirrored into web/public/data/<tour>/.
"""

from __future__ import annotations

import argparse
import shutil
import time
from contextlib import contextmanager
from datetime import UTC

from .config import PLAYER_ALIASES, TOURS, WEB_DATA_DIR, output_dir
from .data.results import load_matches
from .model.export import export_all
from .model.features import FEATURES, build_predictor_inputs, feat_params_for, main_rows
from .model.predict import TennisPredictor
from .model.train import train_final, walk_forward, xgb_params_for


def _mirror(tour: str) -> None:
    """Copy a tour's JSON outputs into the web app's public dir."""
    src, dst = output_dir(tour), WEB_DATA_DIR / tour
    dst.mkdir(parents=True, exist_ok=True)
    for j in src.glob("*.json"):
        shutil.copy(j, dst / j.name)


def _track(tour: str, predictor, df) -> None:
    """Log point-in-time forecasts + (re)grade them (writes track.json). Best-effort:
    a tracking failure must never break the build/deploy."""
    try:
        from .eval.track import log_and_grade
        log_and_grade(tour, predictor, df)
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  track/{tour}: skipped ({e})")


@contextmanager
def _stage(label: str):
    """Emit one unbuffered-friendly elapsed-time line around a pipeline stage."""
    started = time.monotonic()
    print(f"--- {label} started", flush=True)
    try:
        yield
    finally:
        print(f"--- {label} finished in {time.monotonic() - started:.1f}s", flush=True)


# One allowance shared by both tours. Morning-of historical requotes are deliberately
# daily-only; the hourly path captures new/open snapshots and repeats soon if the market
# API is slow. This benchmark never determines a forecast or deploy-gate verdict.
KALSHI_QUICK_BUDGET_S = 75
KALSHI_FULL_BUDGET_S = 1200    # daily run: 20 min for the historical backfill, which is
                               # resumable, so a slow day just finishes it tomorrow
QUICK_KALSHI_DAYS = 4   # hourly run only backfills candles for the last few days; the
                        # committed ledger carries older history, the daily run the rest


def _kalshi(tour: str, df, oos) -> None:
    """Kalshi eval ledger: capture market snapshots, upsert the CSV. Best-effort:
    Kalshi is a benchmark, never a build dependency (report runs after both tours).
    This daily path owns historical quote repair; the hourly helper below deliberately
    disables requotes and shares one smaller allowance across both tours."""
    try:
        from .data.kalshi import refresh_snapshots, time_budget
        from .eval.kalshi_ledger import refresh_ledger
        # The historical repair remains resumable, but even a rate-limited API cannot
        # monopolize the serialized deploy queue indefinitely.
        with time_budget(KALSHI_FULL_BUDGET_S):
            refresh_snapshots(tour)
            refresh_ledger(tour, df, oos=oos)
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  kalshi/{tour}: skipped ({e})")


def _quick_kalshi(tours, frames: dict) -> None:
    """Refresh the benchmark for all quick-run tours under one real wall-clock budget.

    Historical morning quote repair can issue hundreds of candle requests and is safe to
    defer to the daily full run because Kalshi is evaluation-only. New/open snapshots still
    refresh hourly and the cross-tour report is republished from whatever completed."""
    try:
        from .data.kalshi import refresh_snapshots, time_budget
        from .eval.kalshi_ledger import refresh_ledger

        with time_budget(KALSHI_QUICK_BUDGET_S):
            for tour in tours:
                try:
                    refresh_snapshots(tour, recent_days=QUICK_KALSHI_DAYS)
                    refresh_ledger(tour, frames[tour], oos=None, requote=False)
                except Exception as e:                         # noqa: BLE001 — per-tour soft fail
                    print(f"  kalshi/{tour}: skipped ({e})")
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  kalshi/quick: skipped ({e})")


def _kalshi_report(tours) -> None:
    """Regenerate the cross-tour Kalshi scorecard (kalshi.json + report.md) from the
    ledger CSVs, then re-mirror so the fresh kalshi.json reaches web/public/data (the
    first _mirror ran before the report existed). Reads the committed CSVs, so it also
    republishes kalshi.json on quick runs / after a data-cache eviction. Best-effort."""
    try:
        from .eval.kalshi_report import build_report
        build_report()
        for tour in tours:
            _mirror(tour)
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  kalshi-report: skipped ({e})")


def build_tour(tour: str, do_backtest: bool, *, run_kalshi: bool = True):
    """Full build: re-walk ratings, retrain the combiner, write every JSON (daily).
    ``run_kalshi=False`` is used only by a quick-mode compatibility rebuild so the
    caller can keep both tours under the shared hourly benchmark budget."""
    print(f"\n=== {tour.upper()} === loading matches + building features...")
    df = load_matches(tour)
    feat, elo, srv, ctx, meta = build_predictor_inputs(df)
    feat = main_rows(feat)   # combiner never sees lower-tier rows (A5 ratings-only)

    oos = None
    if do_backtest:
        from datetime import datetime
        print("  walk-forward backtest...")
        # Best-effort, like _market_scorecard and _kalshi below: this produces
        # accuracy.json (reported metrics) and NOTHING the shipped model depends on — but
        # it runs before train_final, so an exception here used to abort build_tour before
        # predictor.save(), throwing away a completed ratings walk over a reporting
        # artifact. accuracy.json simply persists from the previous full run.
        try:
            oos = walk_forward(feat, start_test=2016, end_test=datetime.now(UTC).year,
                               xgb_overrides=xgb_params_for(tour))
        except Exception as e:                               # noqa: BLE001 — metrics only
            print(f"  backtest: SKIPPED ({type(e).__name__}: {e}) — accuracy.json keeps "
                  f"the previous run's values; the retrain continues")

    print("  training production combiner...")
    clf, iso, _ = train_final(feat, xgb_overrides=xgb_params_for(tour))
    predictor = TennisPredictor(clf, iso, elo, srv, ctx, meta, tour=tour)
    predictor.save()

    export_all(tour, df, elo, srv, meta, predictor, oos=oos)
    if oos is not None:
        _market_scorecard(tour, oos)
    _track(tour, predictor, df)                  # logs upcoming forecasts first, so
    if run_kalshi:
        _kalshi(tour, df, oos)                         # daily historical benchmark repair
    _mirror(tour)
    return df


def _market_scorecard(tour: str, oos) -> None:
    """Model-vs-closing-line scorecard from the just-computed OOS predictions (writes
    market.json). Best-effort: odds are a benchmark, never a build dependency."""
    try:
        import json

        from .eval.compare import scorecard_from_oos
        sc = scorecard_from_oos(tour, oos)
        (output_dir(tour) / "market.json").write_text(json.dumps(sc, indent=2))
        print(f"  market/{tour}: matched={sc.get('matched')} "
              f"model={sc.get('model', {}).get('brier')} market={sc.get('market', {}).get('brier')} "
              f"lastMatched={sc.get('lastMatchedDate')}")
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  market/{tour}: skipped ({e})")


def _predictor_current(predictor, tour: str) -> bool:
    """True unless the saved predictor is stale: trained on a different feature
    schema (e.g. a cached predictor.pkl predating a feature addition — scoring it
    against freshly assembled frames would crash inside XGBoost), or carrying
    FeatureParams that differ from the tour's current config — its combiner was
    trained on frames built with other thresholds (e.g. a pickle that shipped with
    fp=None, or one predating a FEAT_PARAM_OVERRIDES adoption)."""
    try:
        trained = list(predictor.clf.get_booster().feature_names or [])
        if trained != list(FEATURES):
            return False
    except Exception:                                        # noqa: BLE001 — can't introspect: assume schema-current
        pass
    try:
        if predictor._fp != feat_params_for(tour):
            return False
    except Exception:                                        # noqa: BLE001 — foreign fp shape (cross-version pickle): rebuild
        return False
    try:
        return predictor._player_aliases == tuple(sorted(PLAYER_ALIASES.items()))
    except Exception:                                        # noqa: BLE001 — legacy/foreign pickle: rebuild
        return False


def build_tour_quick(tour: str):
    """Quick refresh (intra-day): reuse the saved predictor's states, re-pull live
    results, regenerate JSON. No re-walk, no retrain (~1-2 min). accuracy.json is left
    to persist from the last full run (the workflow caches data/output)."""
    print(f"\n=== {tour.upper()} [quick] === live refresh from saved model...")
    df = load_matches(tour)
    predictor = TennisPredictor.load(tour)
    if not _predictor_current(predictor, tour):
        print("  quick: saved predictor is stale (feature schema, FeatureParams, or player "
              "aliases) -> full rebuild")
        return build_tour(tour, do_backtest=False, run_kalshi=False)
    export_all(tour, df, predictor.elo, predictor.srv, predictor.meta, predictor, oos=None)
    _track(tour, predictor, df)
    _mirror(tour)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tour", default="atp", help="atp | wta | all")
    ap.add_argument("--download", action="store_true", help="fetch latest results overlay first")
    ap.add_argument("--backtest", action="store_true", help="run walk-forward metrics + accuracy.json")
    ap.add_argument("--quick", action="store_true",
                    help="fast refresh: re-pull live results + regenerate JSON from the saved model")
    args = ap.parse_args()
    tours = list(TOURS) if args.tour == "all" else [args.tour]

    if args.quick:
        from .data.download import download_tml_stats
        from .data.draws import download_tournament_draws
        from .data.live import download_live
        from .data.rankings import download_rankings
        # ESPN's live window drops an event soon after its final. Refresh the lightweight
        # current-year ATP overlay first so a quick run cannot keep reconstructing a
        # completed bracket from a cache that stopped before the final (Kitzbuhel, 2026).
        # One attempt keeps an unavailable stats host bounded; atomic writes preserve the
        # cached file on failure. WTA's rate-limited stats backfill remains daily-only.
        if "atp" in tours:
            with _stage("current ATP stats"):
                download_tml_stats(full=False, retries=1)
        with _stage("ESPN live results"):
            events_by_tour = download_live(tours)
        with _stage("complete tournament draws"):
            download_tournament_draws(tours, events_by_tour=events_by_tour)
        with _stage("live rankings"):
            download_rankings(tours)
        frames = {}
        for tour in tours:
            with _stage(f"{tour.upper()} forecast export"):
                frames[tour] = build_tour_quick(tour)
        with _stage("Kalshi quick benchmark"):
            _quick_kalshi(tours, frames)
        with _stage("Kalshi report"):
            _kalshi_report(tours)
        return

    if args.download:
        from .data.download import download_fresh
        from .data.draws import download_tournament_draws
        from .data.live import download_live
        from .data.rankings import download_rankings
        download_fresh(tours)
        events_by_tour = download_live(tours)  # ESPN same-day overlay; also feeds draw discovery
        download_tournament_draws(tours, events_by_tour=events_by_tour)
        download_rankings(tours)

    for tour in tours:
        build_tour(tour, args.backtest)

    _kalshi_report(tours)


if __name__ == "__main__":
    main()
