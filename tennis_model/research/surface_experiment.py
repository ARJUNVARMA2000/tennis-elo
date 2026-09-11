"""Create-only compatibility experiment for the fixed WTA surface candidate.

Run register, prepare, tune, then (only after advancement) validation. The source
freeze covers all model/research code throughout numerical evaluation. Serving
implementation gets a subsequent freeze; it cannot rewrite these outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from historical_signals import attach_signals, walk_signals
from signal_combiner import select_signals, walk_forward
from tennis_model.config import MATCH_POPULATION_VERSION, N_BAG, WTA_DUAL_STATE_GATE_THRESHOLD
from tennis_model.data.results import load_matches
from tennis_model.eval.metrics import score
from tennis_model.eval.protocol import paired_report, require_paired
from tennis_model.model.artifact import _library_versions, _python_identity
from tennis_model.model.features import FEATURES, build_dual_state_inputs
from tennis_model.model.predict import INFERENCE_SCHEMA_VERSION
from tennis_model.ratings.build import run_elo
from tennis_model.ratings.elo import params_for

WORK = Path(__file__).resolve().parents[2]
FEATURE = "surface_recent_diff"


def now():
    return datetime.now(UTC).isoformat()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def dump(path, value):
    with Path(path).open("xb") as stream:
        pickle.dump(value, stream, protocol=pickle.HIGHEST_PROTOCOL)


def inventory():
    paths = [p for p in (WORK / "tennis_model/src/tennis_model").rglob("*")
             if p.is_file() and p.suffix in {".py", ".json"}]
    paths += list((WORK / "tennis_model/research").glob("*.py"))
    return {str(p.relative_to(WORK)): sha(p) for p in sorted(paths)}


def verify_raw(run):
    setup = read(run / "setup.json")
    root = WORK / "tennis_model/data/raw"
    actual = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}
    if actual != setup["rawFiles"]:
        raise ValueError("frozen raw inputs changed")


def verify(run):
    registration = read(run / "registration.json")
    if registration["sourceInventory"] != inventory():
        raise ValueError("numerical source freeze changed")
    if registration["setupSHA256"] != sha(run / "setup.json"):
        raise ValueError("setup changed")
    verify_raw(run)
    return registration


def register(run):
    verify_raw(run)
    assert (MATCH_POPULATION_VERSION, INFERENCE_SCHEMA_VERSION, N_BAG,
            WTA_DUAL_STATE_GATE_THRESHOLD) == (8, 5, 5, 32)
    write(run / "registration.json", {
        "schema": "wta-surface-population8-compatibility-v1", "registeredAt": now(),
        "baseCommit": read(run / "setup.json")["baseCommit"],
        "implementationCommit": subprocess.check_output(
            ["git", "-C", str(WORK), "rev-parse", "HEAD"], text=True).strip(),
        "setupSHA256": sha(run / "setup.json"), "sourceInventory": inventory(),
        "python": _python_identity(), "libraries": _library_versions(),
        "candidate": {"feature": FEATURE, "definition": "log1p(completed same-surface matches within inclusive 60 days), A minus B",
                      "rowPolicy": "query before every chronological row, including earlier same-date rows",
                      "features": [*FEATURES, FEATURE], "bags": 5, "threshold": 32},
        "trialBudget": 1, "tuneYears": [2010, 2019], "validationYears": [2020, 2026],
        "advancement": "positive pooled tune delta, both five-year halves positive, >=6 positive tune years",
        "arbiter": "positive tune delta; validation delta > -paired SE",
        "servingLimit": {"medianLatencyRatio": 2, "artifactBytesRatio": 2, "peakProcessMemoryRatio": 2},
        "limitations": ["2020+ validation has been used before; not an untouched holdout",
                        "retrospective row chronology does not establish historical feed publication time"],
    })


def prepare(run):
    verify(run)
    dest = run / "prepared"
    dest.mkdir()
    tick = time.monotonic()
    histories = {"main": load_matches("wta", include_lower=False),
                 "enriched": load_matches("wta", include_lower=True)}
    ordinary = build_dual_state_inputs(histories["main"], histories["enriched"], tour="wta")
    frames, states, parity = {}, {}, []
    for label, history in histories.items():
        print("SIGNAL", label, len(history), flush=True)
        _, elo = run_elo(history, params=params_for("wta"))
        states[label], values = walk_signals(history, elo.p_blend.to_numpy())
        features = ordinary.base_features if label == "main" else ordinary.enriched_features
        frames[label] = attach_signals(features, history, values)
        for year in (2009, 2015, 2018):
            n = int(history.date.dt.year.le(year).sum())
            state, _ = walk_signals(history.iloc[:n], elo.p_blend.iloc[:n].to_numpy())
            restored = pickle.loads(pickle.dumps(state))
            row = history.iloc[n]
            before = pickle.dumps(restored)
            actual = restored.query(row.winner_name, row.loser_name, row.surface_b, row.date,
                                    row.winner_rank_points, row.loser_rank_points)
            np.testing.assert_array_equal(list(actual.values()), values.iloc[n].to_numpy())
            assert pickle.dumps(restored) == before
            parity.append({"state": label, "cutoffYear": year, "maxQueryError": 0})
    selected = select_signals(frames["main"], frames["enriched"])
    for label, frame in histories.items():
        dump(dest / f"history-{label}.pkl", frame)
    dump(dest / "inputs.pkl", {"ordinary": ordinary, "frames": frames,
                               "selected": selected, "states": states})
    verify(run)
    write(dest / "completion.json", {"completedAt": now(), "wallSeconds": time.monotonic()-tick,
          "counts": {key: len(value) for key, value in histories.items()}, "parity": parity,
          "files": {p.name: sha(p) for p in dest.glob("*.pkl")}})


def prepared(run):
    receipt = read(run / "prepared/completion.json")
    for name, digest in receipt["files"].items():
        if sha(run / "prepared" / name) != digest:
            raise ValueError("prepared input changed")
    return pd.read_pickle(run / "prepared/inputs.pkl")


def comparison(base, candidate):
    require_paired(base, candidate)
    masks = {"tune": base.year.between(2010, 2019), "validation": base.year.ge(2020),
             "firstHalf": base.year.between(2010, 2014), "secondHalf": base.year.between(2015, 2019)}
    masks.update({str(year): base.year.eq(year) for year in sorted(base.year.unique())})
    metrics = {}
    for label, mask in masks.items():
        if not mask.any():
            continue
        bp, cp = base.loc[mask, "p_combiner"].to_numpy(), candidate.loc[mask, "p_combiner"].to_numpy()
        delta = np.log(np.clip(cp, 1e-12, 1-1e-12))-np.log(np.clip(bp, 1e-12, 1-1e-12))
        metrics[label] = {"incumbent": score(bp), "candidate": score(cp),
                          "deltaLogloss": float(delta.mean()),
                          "pairedSE": float(delta.std(ddof=1)/np.sqrt(len(delta))),
                          "accuracyDeltaPP": (score(cp)["acc"]-score(bp)["acc"])*100}
    return {"metrics": metrics, "pairedReport": paired_report(base, candidate)}


def experiment(run, validation=False):
    verify(run)
    if validation and not read(run / "tune/completion.json")["advance"]:
        raise ValueError("candidate did not advance")
    dest = run / ("validation" if validation else "tune")
    dest.mkdir()
    write(dest / "registration.json", {"startedAt": now(), "freezeSHA256": sha(run / "registration.json"),
                                      "validation": validation, "candidate": FEATURE})
    inputs = prepared(run)
    tick = time.monotonic()
    outputs, folds = {}, {}
    for label, extra in (("incumbent", ()), ("candidate", (FEATURE,))):
        print("FIT", label, "validation" if validation else "tune", flush=True)
        outputs[label], folds[label] = walk_forward(inputs["frames"]["main"], inputs["selected"],
                                                   extra, end_test=2026 if validation else 2019)
        dump(dest / f"{label}-oos.pkl", outputs[label])
        if validation:
            previous = pd.read_pickle(run / "tune" / f"{label}-oos.pkl")
            again = outputs[label][outputs[label].year.le(2019)].reset_index(drop=True)
            require_paired(previous, again)
            np.testing.assert_array_equal(previous.p_combiner, again.p_combiner)
    control = WORK.parent / "2026-09-10-general-release-evidence/wta-oos.pkl"
    assert sha(control) == read(run / "setup.json")["referenceOOS"]
    release = pd.read_pickle(control)
    release = release[release.year.between(2010, 2019)].reset_index(drop=True)
    current = outputs["incumbent"][outputs["incumbent"].year.between(2010, 2019)].reset_index(drop=True)
    require_paired(release, current)
    np.testing.assert_array_equal(release.p_combiner, current.p_combiner)
    result = comparison(outputs["incumbent"], outputs["candidate"])
    m = result["metrics"]
    positive = sum(m[str(y)]["deltaLogloss"] > 0 for y in range(2010, 2020))
    result.update({"completedAt": now(), "wallSeconds": time.monotonic()-tick, "folds": folds,
                   "positiveTuneYears": positive, "releaseTuneControlExact": True,
                   "tuneReplayExact": validation,
                   "advance": m["tune"]["deltaLogloss"] > 0 and positive >= 6
                   and m["firstHalf"]["deltaLogloss"] > 0 and m["secondHalf"]["deltaLogloss"] > 0,
                   "files": {p.name: sha(p) for p in dest.glob("*.pkl")}})
    verify(run)
    write(dest / "completion.json", result)
    print("COMPLETE", json.dumps({"tune": m["tune"], "validation": m.get("validation"),
                                  "advance": result["advance"], "gatePass": result["pairedReport"]["gatePass"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["register", "prepare", "tune", "validation", "verify"])
    parser.add_argument("--run", required=True, type=Path)
    args = parser.parse_args()
    if args.mode in {"tune", "validation"}:
        experiment(args.run, validation=args.mode == "validation")
    else:
        {"register": register, "prepare": prepare, "verify": verify}[args.mode](args.run)
