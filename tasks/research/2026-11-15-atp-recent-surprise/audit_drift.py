"""Replay immutable forecasts against a frozen canonical result frame; emit diagnostics.

Run with PYTHONPATH=tennis_model/src and --results PICKLE --forecasts DIRECTORY.
No production data or forecast history is rewritten.
"""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from tennis_model.eval import track

parser = argparse.ArgumentParser()
parser.add_argument("--results", type=Path, required=True)
parser.add_argument("--forecasts", type=Path, required=True)
args = parser.parse_args()
frame = pd.read_pickle(args.results)
graded = []
first = []
original_grade = track._grade_matches


def capture(matches, results):
    first.extend(matches)
    graded.extend(original_grade(matches, results))
    return graded


track._grade_matches = capture
track.FORECAST_DIR = args.forecasts
with tempfile.TemporaryDirectory() as temporary:
    track.output_dir = lambda tour: Path(temporary) / tour
    report = track.grade("atp", frame)

records = pd.DataFrame(graded)
records = records[records.model_version.eq(track.__version__)].copy()
records["date"] = pd.to_datetime(records.date)
records = records[records.date.ge(records.date.max() - pd.Timedelta(days=90))].copy()
p = records.p_a.clip(1e-12, 1 - 1e-12)
records["excess"] = -np.log(records.p_winner.clip(1e-12, 1 - 1e-12)) + p * np.log(p) + (1-p) * np.log(1-p)
records["confidence"] = pd.cut(np.maximum(p, 1-p), [0.49, 0.6, 0.7, 0.8, 0.9, 1.0]).astype(str)
records["horizon"] = (records.date - pd.to_datetime(records.as_of, utc=True, format="ISO8601").dt.tz_localize(None)).dt.days
records["horizon"] = pd.cut(records.horizon, [-2, 0, 2, 7, 21]).astype(str)
records["year"] = records.date.dt.year.astype(str)
records["cohort"] = records.get("predictor_artifact_id", pd.Series(index=records.index, dtype=str)).fillna("legacy-unidentified")
tiers = {}
for row in frame.itertuples():
    key = (pd.Timestamp(row.date).strftime("%Y-%m-%d"),
           frozenset((track.player_identity_key(row.winner_name), track.player_identity_key(row.loser_name))),
           track._clean_id(row.espn_id))
    if pd.notna(row.tier):
        tiers.setdefault(key, set()).add(str(row.tier))


def result_tier(row):
    key = (row.date.strftime("%Y-%m-%d"),
           frozenset((track.player_identity_key(row.playerA), track.player_identity_key(row.playerB))),
           track._clean_id(row.resultEspnId))
    values = tiers.get(key, set())
    return next(iter(values)) if len(values) == 1 else "unresolved"


records["tier"] = records.apply(result_tier, axis=1)


def metric(group):
    return {"n": len(group), "d": float(group.excess.mean()),
            "se": float(group.excess.std(ddof=1) / np.sqrt(len(group))) if len(group) > 1 else None}


result = {
    "inputs": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in [args.results, args.forecasts / "atp.jsonl"]},
    "resultRows": len(frame), "firstSightings": len(first), "graded": len(graded),
    "uniqueFirstSightings": len({r["match_id"] for r in first}) == len(first),
    "walkoversInWindow": int(records.walkover.sum()),
    "knownEventContradictions": sum(bool(r.get("espnId") and r.get("resultEspnId")
                                         and r["espnId"] != r["resultEspnId"]) for r in graded),
    "monitor": report["matchForecasts"]["drift"],
    "slices": {column: {str(key): metric(group) for key, group in records.groupby(column)}
               for column in ["confidence", "surface", "tier", "horizon", "year", "cohort"]},
    "limitations": ["Tier is reconstructed only from unambiguous result date/player-pair/event identity, not forecast-time metadata.",
                    "Horizon uses source result calendar dates, not independently observed first-serve times.",
                    "Slice SE assumes independent matches; repeated players/events can add dependence.",
                    "This refreshed-source replay is not the exact prior production result snapshot."],
}
print(json.dumps(result, indent=2))
