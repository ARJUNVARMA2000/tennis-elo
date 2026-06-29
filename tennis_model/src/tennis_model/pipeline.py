"""End-to-end pipeline: data -> ratings -> point model -> combiner -> JSON + model.

Run:  PYTHONPATH=src python -m tennis_model.pipeline --tour all [--download] [--backtest]

For each tour it builds the production predictor (data/output/<tour>/predictor.pkl)
and writes the full set of frontend JSON artifacts (see model/export.py). The web app
reads data/output/<tour>/*.json; copies are mirrored into web/public/data/<tour>/.
"""

from __future__ import annotations

import argparse
import shutil

from .config import MODEL_DIR, TOURS, output_dir
from .data.results import load_matches
from .model.export import export_all
from .model.features import build_predictor_inputs
from .model.predict import TennisPredictor
from .model.train import train_final, walk_forward

WEB_DATA_DIR = MODEL_DIR.parent / "web" / "public" / "data"


def _mirror(tour: str) -> None:
    """Copy a tour's JSON outputs into the web app's public dir."""
    src, dst = output_dir(tour), WEB_DATA_DIR / tour
    dst.mkdir(parents=True, exist_ok=True)
    for j in src.glob("*.json"):
        shutil.copy(j, dst / j.name)


def build_tour(tour: str, do_backtest: bool) -> None:
    """Full build: re-walk ratings, retrain the combiner, write every JSON (daily)."""
    print(f"\n=== {tour.upper()} === loading matches + building features...")
    df = load_matches(tour)
    feat, elo, srv, ctx, meta = build_predictor_inputs(df)

    oos = None
    if do_backtest:
        print("  walk-forward backtest...")
        oos = walk_forward(feat, start_test=2016, end_test=2025)

    print("  training production combiner...")
    clf, iso, _ = train_final(feat)
    predictor = TennisPredictor(clf, iso, elo, srv, ctx, meta, tour=tour)
    predictor.save()

    export_all(tour, df, elo, srv, meta, predictor, oos=oos)
    _mirror(tour)


def build_tour_quick(tour: str) -> None:
    """Quick refresh (intra-day): reuse the saved predictor's states, re-pull live
    results, regenerate JSON. No re-walk, no retrain (~1-2 min). accuracy.json is left
    to persist from the last full run (the workflow caches data/output)."""
    print(f"\n=== {tour.upper()} [quick] === live refresh from saved model...")
    df = load_matches(tour)
    predictor = TennisPredictor.load(tour)
    export_all(tour, df, predictor.elo, predictor.srv, predictor.meta, predictor, oos=None)
    _mirror(tour)


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
        from .data.live import download_live
        download_live(tours)        # ESPN same-day overlay is the whole point of a quick run
        for tour in tours:
            build_tour_quick(tour)
        return

    if args.download:
        from .data.download import download_fresh
        from .data.live import download_live
        download_fresh(tours)
        download_live(tours)        # ESPN same-day overlay so current events are current

    for tour in tours:
        build_tour(tour, args.backtest)


if __name__ == "__main__":
    main()
