"""Fit, verify and benchmark the registered offline candidate without publishing it."""

from __future__ import annotations

import argparse
import itertools
import json
import pickle
import resource
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from surface_artifact import state_receipt, surface_contract
from surface_candidate import COLUMNS, FEATURE, SurfaceCandidatePredictor, fit_surface_predictor
from surface_experiment import WORK, dump, inventory, now, prepared, read, sha, write
from tennis_model.model.features import FEATURES
from tennis_model.model.predict import TennisPredictor
from tennis_model.model.train import FINAL_TRAIN_SEED, train_final, xgb_params_for


def verify_files(run):
    receipt = read(run / "validation/completion.json")
    if not receipt["advance"] or not receipt["pairedReport"]["gatePass"] or not receipt["tuneReplayExact"]:
        raise ValueError("fixed candidate did not pass the registered arbiter")
    for stage in ("tune", "validation"):
        for file, digest in read(run / stage / "completion.json")["files"].items():
            if sha(run / stage / file) != digest:
                raise ValueError("numerical evidence changed")
    return receipt


def freeze(run):
    verify_files(run)
    original = read(run / "registration.json")["sourceInventory"]
    current = inventory()
    changed = [p for p, digest in original.items() if current.get(p) != digest]
    expected = ["tennis_model/src/tennis_model/model/artifact.py",
                "tennis_model/src/tennis_model/model/predict.py"]
    if sorted(changed) != sorted(expected):
        raise ValueError("unexpected numerical-source change during serving integration")
    write(run / "serving-freeze.json", {
        "frozenAt": now(), "sourceInventory": current,
        "implementationCommit": subprocess.check_output(["git", "-C", str(WORK), "rev-parse", "HEAD"], text=True).strip(),
        "numericalFreeze": sha(run / "registration.json"),
        "numericalCompletion": sha(run / "validation/completion.json"),
        "preparedCompletion": sha(run / "prepared/completion.json"),
        "criteria": sha(run / "serving-registration.json"),
        "changedExistingSources": changed, "contract": surface_contract(),
    })


def verify_freeze(run):
    record = read(run / "serving-freeze.json")
    if record["sourceInventory"] != inventory():
        raise ValueError("serving source freeze changed")
    for field, file in (("numericalFreeze", "registration.json"),
                        ("numericalCompletion", "validation/completion.json"),
                        ("preparedCompletion", "prepared/completion.json"),
                        ("criteria", "serving-registration.json")):
        if record[field] != sha(run / file):
            raise ValueError("serving input/criteria freeze changed")
    verify_files(run)
    return record


def fit(run):
    verify_freeze(run)
    inputs = prepared(run)
    final = run / "final"
    final.mkdir()
    provenance = {"numericalFreeze": sha(run / "registration.json"),
                  "servingFreeze": sha(run / "serving-freeze.json"),
                  "selection": sha(run / "validation/completion.json"),
                  "mainInput": sha(run / "prepared/history-main.pkl"),
                  "enrichedInput": sha(run / "prepared/history-enriched.pkl"),
                  "mainState": state_receipt(inputs["states"]["main"])["sha256"],
                  "lowerState": state_receipt(inputs["states"]["enriched"])["sha256"]}
    write(final / "provenance.json", provenance)
    tick = time.monotonic()
    ordinary = inputs["ordinary"]
    clf, calibration, _ = train_final(ordinary.base_features, xgb_overrides=xgb_params_for("wta"), n_bag=5)
    reference = TennisPredictor(clf, calibration, ordinary.elo, ordinary.srv, ordinary.ctx, ordinary.meta,
                                tour="wta", lower_elo=ordinary.lower_elo, lower_srv=ordinary.lower_srv,
                                lower_ctx=ordinary.lower_ctx, dual_state_threshold=32)
    candidate = fit_surface_predictor(inputs, provenance=provenance)
    # Retain the fitted objects before exercising serialization; a serialization bug
    # must not silently trigger another fit. These are private trusted recovery bytes.
    dump(final / "fitted-private.pkl", {"reference": reference, "candidate": candidate})
    reference.save(final / "reference.pkl")
    candidate.save(final / "candidate.surface", trusted_root=final)
    completed = ordinary.base_features.query("completed and year >= 1991")
    cutoff = completed.date.max()-pd.Timedelta(days=365)
    verify_freeze(run)
    write(final / "completion.json", {"completedAt": now(), "fitWallSeconds": time.monotonic()-tick,
          "finalSeed": FINAL_TRAIN_SEED, "coreRows": int(completed.date.lt(cutoff).sum()),
          "calibrationRows": int(completed.date.ge(cutoff).sum()), "calibrationCutoff": str(cutoff),
          "referenceArtifactId": reference.artifact_id, "candidateArtifactId": candidate.artifact_id,
          "files": {p.name: sha(p) for p in final.iterdir() if p.is_file()}})


def load(run, label):
    final = run / "final"
    receipt = read(final / "completion.json")
    names = ("reference.pkl", "reference.pkl.envelope") if label == "reference" else ("candidate.surface", "provenance.json")
    for name in names:
        if sha(final / name) != receipt["files"][name]:
            raise ValueError("final artifact bytes changed")
    if label == "reference":
        return TennisPredictor.load("wta", final / "reference.pkl")
    return SurfaceCandidatePredictor.load(final / "candidate.surface", trusted_root=final,
                                          expected_provenance=read(final / "provenance.json"))


def cohort(model):
    high = sorted((name for name, count in model.elo.n.items() if count >= 32),
                  key=lambda name: (-model.elo.n[name], name))[:20]
    low = sorted((name for name in model.lower_elo.n if model.elo.n.get(name, 0) < 32),
                 key=lambda name: (-model.lower_elo.n[name], name))[:10]
    names = high+low
    if len(names) != 30 or len(set(names)) != 30:
        raise ValueError("registered player cohorts unavailable")
    date = max(pd.Timestamp(model.elo.last_date), pd.Timestamp(model.lower_elo.last_date))
    return names, date


def verify_routes(run):
    verify_freeze(run)
    reference, candidate = load(run, "reference"), load(run, "candidate")
    original = pd.read_pickle(run / "final/fitted-private.pkl")["candidate"]
    names, date = cohort(candidate)
    # Include both selector routes plus explicit unobserved names in the route proof.
    sample = names[:3]+names[20:23]+["Unseen Alpha", "Unseen Beta"]
    before = pickle.dumps(candidate)
    checks, selected = 0, {"main": 0, "enriched": 0}
    for days in (0, 1, 61):
        for surface in ("Hard", "Clay", "Grass"):
            context = {"surface": surface, "as_of": date+pd.Timedelta(days=days)}
            matrix = candidate.win_prob_matrix(sample, **context)
            np.testing.assert_array_equal(matrix, original.win_prob_matrix(sample, **context))
            np.testing.assert_allclose(matrix+matrix.T, 1, rtol=0, atol=1e-15)
            order = [6, 2, 0, 7, 1, 5, 3, 4]
            permuted = candidate.win_prob_matrix([sample[i] for i in order], **context)
            np.testing.assert_allclose(permuted, matrix[np.ix_(order, order)], rtol=0, atol=1e-15)
            effects = candidate.prediction_evidence_matrices(sample, **context)
            for i, j in itertools.combinations(range(len(sample)), 2):
                left, right = sample[i], sample[j]
                features = candidate.features(left, right, **context)
                pd.testing.assert_frame_equal(features, original.features(left, right, **context))
                pd.testing.assert_frame_equal(features[FEATURES], reference.features(left, right, **context))
                assert list(features) == COLUMNS
                label = "enriched" if candidate._states_for(left, right)[0] is candidate.lower_elo else "main"
                selected[label] += 1
                state = candidate.surface_lower if label == "enriched" else candidate.surface_main
                assert features[FEATURE].iloc[0] == state.query(left, right, surface, context["as_of"])[FEATURE]
                if days == 61:
                    assert features[FEATURE].iloc[0] == 0
                probability = candidate.win_prob(left, right, **context)
                assert probability == matrix[i, j] == candidate.prediction_components(left, right, **context)["combiner"]
                assert candidate.predict(left, right, **context)["p_a"] == round(probability, 4)
                assert abs(probability+candidate.win_prob(right, left, **context)-1) <= 1e-15
                evidence = candidate.prediction_evidence(left, right, **context)
                assert evidence["probabilityA"] == round(probability, 4)
                for signal in evidence["signals"]:
                    assert signal["impactPp"] == round(effects["effects"][signal["key"]][i, j]*100, 2)
                checks += 1
    assert pickle.dumps(candidate) == before
    verify_freeze(run)
    write(run / "real-serving-parity.json", {"completedAt": now(), "matchupContexts": checks,
          "selectedStates": selected, "queryColumns": 43, "referenceColumnsExact": 42,
          "savedQueriesExact": True, "scalarMatrixExact": True, "queryNondestructive": True,
          "historyParity": read(run / "prepared/completion.json")["parity"], "players": sample})


def memory(run, label):
    model = load(run, label)
    names, date = cohort(model)
    for surface in ("Hard", "Clay", "Grass"):
        model.win_prob_matrix(names, surface=surface, as_of=date)
    scale = 1024**2 if sys.platform == "darwin" else 1024
    print(json.dumps({"label": label, "peakMiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/scale}))


def benchmark(run):
    verify_freeze(run)
    models = {label: load(run, label) for label in ("reference", "candidate")}
    names, date = cohort(models["candidate"])
    pairs = list(itertools.combinations(names, 2))[:100]
    values = {label: {"scalarMs": [], "matrixMs": []} for label in models}
    for index in range(11):
        order = ("reference", "candidate") if index % 2 == 0 else ("candidate", "reference")
        for label in order:
            model = models[label]
            for n, (left, right) in enumerate(pairs):
                tick = time.perf_counter()
                model.win_prob(left, right, surface=("Hard", "Clay", "Grass")[n % 3], as_of=date)
                if index >= 2:
                    values[label]["scalarMs"].append((time.perf_counter()-tick)*1000)
            for surface in ("Hard", "Clay", "Grass"):
                tick = time.perf_counter()
                model.win_prob_matrix(names, surface=surface, as_of=date)
                if index >= 2:
                    values[label]["matrixMs"].append((time.perf_counter()-tick)*1000)
    peaks = {label: [] for label in models}
    for _ in range(3):
        for label in models:
            result = subprocess.run(["uv", "run", "--offline", "--no-project", "--python", sys.executable,
                                     "python", str(Path(__file__).resolve()), "memory", "--run", str(run), "--label", label],
                                    cwd=WORK / "tennis_model", text=True, capture_output=True, check=True)
            peaks[label].append(json.loads(result.stdout)["peakMiB"])
    totals = {"reference": sum((run / "final" / name).stat().st_size for name in ("reference.pkl", "reference.pkl.envelope")),
              "candidate": (run / "final/candidate.surface").stat().st_size}
    summary = {label: {kind: {"n": len(samples), "median": float(np.median(samples)), "p95": float(np.quantile(samples, .95))}
                       for kind, samples in groups.items()} for label, groups in values.items()}
    ratios = {kind: summary["candidate"][kind]["median"]/summary["reference"][kind]["median"]
              for kind in ("scalarMs", "matrixMs")}
    ratios.update(artifactBytes=totals["candidate"]/totals["reference"],
                  peakProcessMiB=max(peaks["candidate"])/max(peaks["reference"]))
    verify_freeze(run)
    write(run / "serving-cost.json", {"completedAt": now(), "players": names, "asOf": str(date),
          "latency": summary, "artifactBytes": totals, "peakProcessMiB": peaks, "ratios": ratios,
          "passed": all(ratio <= 2 for ratio in ratios.values()), "rawTimings": values,
          "populationNote": "Fixed match-count-selected cohorts include inactive players; not a traffic-weighted workload"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["freeze", "fit", "verify", "benchmark", "memory"])
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--label", choices=["reference", "candidate"])
    args = parser.parse_args()
    if args.mode == "memory":
        memory(args.run, args.label)
    else:
        {"freeze": freeze, "fit": fit, "verify": verify_routes, "benchmark": benchmark}[args.mode](args.run)
