"""End-to-end pipeline: data -> ratings -> point model -> combiner -> JSON + model.

Run:  PYTHONPATH=src python -m tennis_model.pipeline --tour all [--download] [--backtest]

For each tour it builds the production predictor (data/output/<tour>/predictor.pkl)
and writes the full set of frontend JSON artifacts (see model/export.py). The web app
reads data/output/<tour>/*.json; copies are mirrored into web/public/data/<tour>/.
"""

from __future__ import annotations

import argparse
import shutil
from datetime import UTC

from .config import MODEL_DIR, TOURS, output_dir
from .data.results import load_matches
from .model.export import export_all
from .model.features import FEATURES, build_predictor_inputs, main_rows
from .model.predict import TennisPredictor
from .model.train import train_final, walk_forward, xgb_params_for

WEB_DATA_DIR = MODEL_DIR.parent / "web" / "public" / "data"


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


QUICK_KALSHI_DAYS = 4   # hourly run only backfills candles for the last few days; the
                        # committed ledger carries older history, the daily run the rest


def _kalshi(tour: str, df, oos, recent_days=None) -> None:
    """Kalshi eval ledger: capture market snapshots, upsert the CSV. Best-effort:
    Kalshi is a benchmark, never a build dependency (report runs after both tours).
    `recent_days` bounds the candlestick backfill so a cold cache on the hourly quick
    run can't stall on the full historical sweep."""
    try:
        from .data.kalshi import refresh_snapshots
        from .eval.kalshi_ledger import refresh_ledger
        refresh_snapshots(tour, recent_days=recent_days)
        refresh_ledger(tour, df, oos=oos)
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  kalshi/{tour}: skipped ({e})")


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


def build_tour(tour: str, do_backtest: bool) -> None:
    """Full build: re-walk ratings, retrain the combiner, write every JSON (daily)."""
    print(f"\n=== {tour.upper()} === loading matches + building features...")
    df = load_matches(tour)
    feat, elo, srv, ctx, meta = build_predictor_inputs(df)
    feat = main_rows(feat)   # combiner never sees lower-tier rows (A5 ratings-only)

    oos = None
    if do_backtest:
        from datetime import datetime
        print("  walk-forward backtest...")
        oos = walk_forward(feat, start_test=2016, end_test=datetime.now(UTC).year,
                           xgb_overrides=xgb_params_for(tour))

    print("  training production combiner...")
    clf, iso, _ = train_final(feat, xgb_overrides=xgb_params_for(tour))
    predictor = TennisPredictor(clf, iso, elo, srv, ctx, meta, tour=tour)
    predictor.save()

    export_all(tour, df, elo, srv, meta, predictor, oos=oos)
    if oos is not None:
        _market_scorecard(tour, oos)
    _track(tour, predictor, df)                  # logs upcoming forecasts first, so
    _kalshi(tour, df, oos)                       # the ledger can price them (live)
    _mirror(tour)


def _market_scorecard(tour: str, oos) -> None:
    """Model-vs-Pinnacle scorecard from the just-computed OOS predictions (writes
    market.json). Best-effort: odds are a benchmark, never a build dependency."""
    try:
        import json

        from .eval.compare import scorecard_from_oos
        sc = scorecard_from_oos(tour, oos)
        (output_dir(tour) / "market.json").write_text(json.dumps(sc, indent=2))
        print(f"  market/{tour}: matched={sc.get('matched')} "
              f"model={sc.get('model', {}).get('brier')} market={sc.get('market', {}).get('brier')}")
    except Exception as e:                                   # noqa: BLE001 — never fatal
        print(f"  market/{tour}: skipped ({e})")


def _predictor_current(predictor) -> bool:
    """True unless the saved combiner was trained on a different feature schema
    (e.g. a cached predictor.pkl predating a feature addition — scoring it against
    freshly assembled frames would crash inside XGBoost)."""
    try:
        trained = list(predictor.clf.get_booster().feature_names or [])
    except Exception:                                        # noqa: BLE001 — can't introspect: assume current
        return True
    return trained == list(FEATURES)


def build_tour_quick(tour: str) -> None:
    """Quick refresh (intra-day): reuse the saved predictor's states, re-pull live
    results, regenerate JSON. No re-walk, no retrain (~1-2 min). accuracy.json is left
    to persist from the last full run (the workflow caches data/output)."""
    print(f"\n=== {tour.upper()} [quick] === live refresh from saved model...")
    df = load_matches(tour)
    predictor = TennisPredictor.load(tour)
    if not _predictor_current(predictor):
        print("  quick: saved predictor has a stale feature schema -> full rebuild")
        build_tour(tour, do_backtest=False)
        return
    export_all(tour, df, predictor.elo, predictor.srv, predictor.meta, predictor, oos=None)
    _track(tour, predictor, df)                  # refreshes the forecast log first, so the
    _kalshi(tour, df, oos=None, recent_days=QUICK_KALSHI_DAYS)   # ledger prices live matches
    _mirror(tour)                                # (bounded backfill keeps the hourly run fast)


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
        from .data.draws_wiki import download_wiki_draws
        from .data.live import download_live
        from .data.rankings import download_rankings
        download_live(tours)        # ESPN same-day overlay is the whole point of a quick run
        download_wiki_draws(tours)  # authoritative full draws at release (best-effort)
        download_rankings(tours)    # official live ranks (best-effort, keeps last good file)
        for tour in tours:
            build_tour_quick(tour)
        _kalshi_report(tours)       # republish kalshi.json hourly from the fresh ledger
        return

    if args.download:
        from .data.download import download_fresh
        from .data.draws_wiki import download_wiki_draws
        from .data.live import download_live
        from .data.rankings import download_rankings
        download_fresh(tours)
        download_live(tours)        # ESPN same-day overlay so current events are current
        download_wiki_draws(tours)  # authoritative full draws at release (best-effort)
        download_rankings(tours)

    for tour in tours:
        build_tour(tour, args.backtest)

    _kalshi_report(tours)


if __name__ == "__main__":
    main()
