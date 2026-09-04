"""Predictions invariants extracted without changing gate semantics."""

from __future__ import annotations

from .common import (
    _EVIDENCE_KEYS,
    _UUID4_RE,
    _WATCH_WEIGHTS,
    _add_finding,
    _event_entity,
    _finite_between,
    _is_prob,
    _match_entity,
    _player_identity_key,
    _square_matrix,
)


def _check_matrix(out: list, tour: str, mx: dict) -> None:
    players = mx.get("players") or []
    n = len(players)
    for surf, byfmt in (mx.get("surfaces") or {}).items():
        if not isinstance(byfmt, dict):
            continue
        for fmt, m in byfmt.items():
            if (not isinstance(m, list) or len(m) != n
                    or any(not isinstance(r, list) or len(r) != n for r in m)):
                _add_finding(
                    out, "output.matrix.geometry_invalid",
                    f"{tour}: matrix[{surf}][{fmt}] is not {n}x{n}",
                    severity="error", entity=f"matrix:{surf}:{fmt}",
                    evidence={"surface": str(surf), "format": str(fmt),
                              "expectedSize": n})
                continue
            if n == 0:
                _add_finding(
                    out, "output.matrix.roster_empty",
                    f"{tour}: matrix[{surf}][{fmt}] has no players",
                    severity="error", entity=f"matrix:{surf}:{fmt}",
                    evidence={"surface": str(surf), "format": str(fmt)})
                continue
            # sample corners + the top-left 2x2 — enough to catch a systemic break
            # (all-out-of-range, transposed, un-normalised) without scanning ~14k cells
            for i, j in {(0, 0), (0, min(1, n - 1)), (n - 1, 0), (n - 1, n - 1)}:
                if not _is_prob(m[i][j]):
                    _add_finding(
                        out, "output.matrix.probability_invalid",
                        f"{tour}: matrix[{surf}][{fmt}][{i}][{j}]={m[i][j]!r} out of [0,1]",
                        severity="error", entity=f"matrix:{surf}:{fmt}:{i}:{j}",
                        evidence={"surface": str(surf), "format": str(fmt),
                                  "row": i, "column": j, "value": repr(m[i][j])})
            if n >= 2:
                if abs(m[0][0] - 0.5) > 1e-6:
                    _add_finding(
                        out, "output.matrix.diagonal_invalid",
                        f"{tour}: matrix[{surf}][{fmt}] diagonal != 0.5 ({m[0][0]})",
                        severity="error", entity=f"matrix:{surf}:{fmt}",
                        evidence={"surface": str(surf), "format": str(fmt),
                                  "value": float(m[0][0])})
                if abs(m[0][1] + m[1][0] - 1.0) > 1e-3:
                    _add_finding(
                        out, "output.matrix.antisymmetry_invalid",
                        f"{tour}: matrix[{surf}][{fmt}] not antisymmetric "
                        f"({m[0][1]}+{m[1][0]})",
                        severity="error", entity=f"matrix:{surf}:{fmt}",
                        evidence={"surface": str(surf), "format": str(fmt),
                                  "forward": float(m[0][1]), "reverse": float(m[1][0])})

def _check_matrix_shards(out: list, tour: str, index: dict, shards: dict) -> None:
    players = index.get("players")
    generation = index.get("generation")
    expected_components = {"eloBlend", "pointModel", "combiner"}
    if not generation:
        _add_finding(
            out, "output.matrix_index.generation_missing",
            f"{tour}: matrix-index.json is missing generation",
            severity="error", entity="artifact:matrix-index.json", evidence={})
    if not isinstance(players, list) or not players or any(not p for p in players):
        _add_finding(
            out, "output.matrix_index.roster_invalid",
            f"{tour}: matrix-index.json has an empty/malformed player roster",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"valueType": type(players).__name__})
        players = players if isinstance(players, list) else []
    elif len(set(players)) != len(players):
        _add_finding(
            out, "output.matrix_index.roster_duplicate",
            f"{tour}: matrix-index.json has duplicate players",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"players": len(players), "uniquePlayers": len(set(players))})
    formats = index.get("formats")
    if not isinstance(formats, list) or not formats:
        _add_finding(
            out, "output.matrix_index.formats_invalid",
            f"{tour}: matrix-index.json has no formats",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"valueType": type(formats).__name__})
    surfaces = index.get("surfaces")
    if not isinstance(surfaces, dict) or not surfaces:
        # Avoid the generic advisory marker "is empty": a shard index with no context
        # makes the predictor unusable and must block, unlike a quiet schedule feed.
        _add_finding(
            out, "output.matrix_index.surfaces_invalid",
            f"{tour}: matrix-index.json surfaces is missing/malformed",
            severity="error", entity="artifact:matrix-index.json",
            evidence={"valueType": type(surfaces).__name__})
        return
    for surface, byfmt in surfaces.items():
        if not isinstance(byfmt, dict):
            _add_finding(
                out, "output.matrix_index.format_map_invalid",
                f"{tour}: matrix-index {surface!r} format map is malformed",
                severity="error", entity=f"matrix-index:{surface}",
                evidence={"surface": str(surface), "valueType": type(byfmt).__name__})
            continue
        for fmt, filename in byfmt.items():
            shard = shards.get(filename)
            if not isinstance(shard, dict):
                continue  # missing/corrupt has its own exact-file problem
            if shard.get("generation") != generation:
                _add_finding(
                    out, "output.matrix_shard.generation_mismatch",
                    f"{tour}: {filename} generation disagrees with matrix-index.json",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"expected": generation, "actual": shard.get("generation")})
            if shard.get("players") != players:
                _add_finding(
                    out, "output.matrix_shard.roster_mismatch",
                    f"{tour}: {filename} player order disagrees with matrix-index.json",
                    severity="error", entity=f"artifact:{filename}", evidence={})
            if shard.get("surface") != surface or str(shard.get("bestOf")) != str(fmt):
                _add_finding(
                    out, "output.matrix_shard.context_mismatch",
                    f"{tour}: {filename} context disagrees with matrix-index.json",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"expectedSurface": str(surface), "expectedBestOf": str(fmt),
                              "actualSurface": shard.get("surface"),
                              "actualBestOf": shard.get("bestOf")})
            components = shard.get("components")
            if not isinstance(components, dict):
                _add_finding(
                    out, "output.matrix_shard.components_invalid",
                    f"{tour}: {filename} components is malformed",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"valueType": type(components).__name__})
                continue
            if set(components) != expected_components:
                _add_finding(
                    out, "output.matrix_shard.component_set_mismatch",
                    f"{tour}: {filename} component set {sorted(components)} "
                    f"!= {sorted(expected_components)}",
                    severity="error", entity=f"artifact:{filename}",
                    evidence={"actual": sorted(components),
                              "expected": sorted(expected_components)})
            for component, matrix in components.items():
                _check_matrix(out, tour, {
                    "players": players,
                    "surfaces": {surface: {f"{fmt}/{component}": matrix}},
                })
            _check_matrix_evidence(out, tour, str(filename), shard.get("evidence"), len(players))

def _check_matrix_evidence(out: list, tour: str, filename: str,
                           evidence: object, n: int) -> None:
    """Arbitrary-pair evidence must share the matrix roster and signed orientation."""
    if not isinstance(evidence, dict) or evidence.get("schema") != "evidence-v1":
        _add_finding(
            out, "output.matrix_evidence.payload_invalid",
            f"{tour}: {filename} evidence-v1 payload is missing/malformed",
            severity="error", entity=f"artifact:{filename}",
            evidence={"valueType": type(evidence).__name__})
        return
    effects = evidence.get("effects")
    if not isinstance(effects, dict) or set(effects) != set(_EVIDENCE_KEYS):
        _add_finding(
            out, "output.matrix_evidence.signal_set_invalid",
            f"{tour}: {filename} evidence signal set is malformed",
            severity="error", entity=f"artifact:{filename}",
            evidence={"expected": sorted(_EVIDENCE_KEYS),
                      "actual": sorted(map(str, effects)) if isinstance(effects, dict) else None})
        return
    packed = evidence.get("encoding") == "upper-triangle-bps-v1"
    packed_size = n * (n - 1) // 2
    for key, matrix in effects.items():
        if packed:
            if (not isinstance(matrix, list) or len(matrix) != packed_size
                    or any(not isinstance(value, int) or isinstance(value, bool)
                           or not -10_000 <= value <= 10_000 for value in matrix)):
                _add_finding(
                    out, "output.matrix_evidence.packed_signal_invalid",
                    f"{tour}: {filename} packed evidence[{key}] is malformed",
                    severity="error", entity=f"artifact:{filename}#signal:{key}",
                    evidence={"signal": str(key), "expectedSize": packed_size})
            continue
        if not _square_matrix(matrix, n):
            _add_finding(
                out, "output.matrix_evidence.geometry_invalid",
                f"{tour}: {filename} evidence[{key}] is not {n}x{n}",
                severity="error", entity=f"artifact:{filename}#signal:{key}",
                evidence={"signal": str(key), "expectedSize": n})
            continue
        bad = False
        for i in range(n):
            if not _finite_between(matrix[i][i], 0.0, 0.0):
                bad = True
                break
            for j in range(i + 1, n):
                if (not _finite_between(matrix[i][j], -1.0, 1.0)
                        or not _finite_between(matrix[j][i], -1.0, 1.0)
                        or abs(float(matrix[i][j]) + float(matrix[j][i])) > 2e-4):
                    bad = True
                    break
            if bad:
                break
        if bad:
            _add_finding(
                out, "output.matrix_evidence.antisymmetry_invalid",
                f"{tour}: {filename} evidence[{key}] is non-finite/non-antisymmetric",
                severity="error", entity=f"artifact:{filename}#signal:{key}",
                evidence={"signal": str(key)})
    available = evidence.get("available")
    if not isinstance(available, dict) or set(available) != {"h2h", "style"}:
        _add_finding(
            out, "output.matrix_evidence.availability_invalid",
            f"{tour}: {filename} conditional evidence availability is malformed",
            severity="error", entity=f"artifact:{filename}", evidence={})
    else:
        for key, matrix in available.items():
            if packed:
                valid = (isinstance(matrix, list) and len(matrix) == packed_size
                         and all(value in (0, 1) for value in matrix))
            else:
                valid = (_square_matrix(matrix, n) and all(
                    value in (0, 1) for row in matrix for value in row))
            if not valid:
                _add_finding(
                    out, "output.matrix_evidence.availability_signal_invalid",
                    f"{tour}: {filename} evidence availability[{key}] is malformed",
                    severity="error", entity=f"artifact:{filename}#availability:{key}",
                    evidence={"signal": str(key)})
    if evidence.get("homeAvailable") is not False:
        _add_finding(
            out, "output.matrix_evidence.home_context_invalid",
            f"{tour}: {filename} generic matchup evidence claims home context",
            severity="error", entity=f"artifact:{filename}",
            evidence={"homeAvailable": repr(evidence.get("homeAvailable"))})

def _check_prediction_evidence(out: list, tour: str, label: str, evidence: object,
                               player_a: object = None, player_b: object = None,
                               probability_a: object = None, *, entity: str | None = None) -> None:
    """Validate the seven grouped signals and their explicit non-causal contract."""
    finding_entity = entity or _match_entity(
        {}, player_a=player_a, player_b=player_b)
    if not isinstance(evidence, dict) or evidence.get("schema") != "evidence-v1":
        _add_finding(
            out, "output.prediction_evidence.payload_invalid",
            f"{tour}: {label} prediction evidence is missing/malformed",
            severity="error", entity=finding_entity,
            evidence={"valueType": type(evidence).__name__})
        return
    a, b = evidence.get("playerA"), evidence.get("playerB")
    if player_a is not None and (a != player_a or b != player_b):
        _add_finding(
            out, "output.prediction_evidence.orientation_mismatch",
            f"{tour}: {label} evidence orientation disagrees with matchup",
            severity="error", entity=finding_entity,
            evidence={"expectedPlayerA": repr(player_a), "expectedPlayerB": repr(player_b),
                      "actualPlayerA": repr(a), "actualPlayerB": repr(b)})
    if not _is_prob(evidence.get("probabilityA")):
        _add_finding(
            out, "output.prediction_evidence.probability_invalid",
            f"{tour}: {label} evidence probability is outside [0,1]",
            severity="error", entity=finding_entity,
            evidence={"value": repr(evidence.get("probabilityA"))})
    elif _is_prob(probability_a) and abs(float(evidence["probabilityA"]) - float(probability_a)) > 1e-4:
        _add_finding(
            out, "output.prediction_evidence.probability_mismatch",
            f"{tour}: {label} evidence probability disagrees with published call",
            severity="error", entity=finding_entity,
            evidence={"evidenceProbability": float(evidence["probabilityA"]),
                      "publishedProbability": float(probability_a)})
    note = str(evidence.get("note") or "").lower()
    if "evidence" not in note or "not causation" not in note:
        _add_finding(
            out, "output.prediction_evidence.disclaimer_missing",
            f"{tour}: {label} evidence omits the non-causal disclaimer",
            severity="error", entity=finding_entity, evidence={})
    signals = evidence.get("signals")
    if not isinstance(signals, list) or len(signals) != len(_EVIDENCE_KEYS):
        _add_finding(
            out, "output.prediction_evidence.signal_list_invalid",
            f"{tour}: {label} evidence signal list is malformed",
            severity="error", entity=finding_entity,
            evidence={"expectedCount": len(_EVIDENCE_KEYS),
                      "actualCount": len(signals) if isinstance(signals, list) else None})
        return
    keys = [signal.get("key") for signal in signals if isinstance(signal, dict)]
    if len(keys) != len(signals) or set(keys) != set(_EVIDENCE_KEYS):
        _add_finding(
            out, "output.prediction_evidence.signal_keys_invalid",
            f"{tour}: {label} evidence signal keys are missing/duplicated",
            severity="error", entity=finding_entity,
            evidence={"expected": sorted(_EVIDENCE_KEYS), "actual": list(map(str, keys))})
        return
    available_strengths = []
    unavailable_seen = False
    for signal in signals:
        available = signal.get("available")
        impact = signal.get("impactPp")
        supports = signal.get("supports")
        if not isinstance(available, bool) or not _finite_between(impact, -100.0, 100.0):
            _add_finding(
                out, "output.prediction_evidence.signal_value_invalid",
                f"{tour}: {label} evidence signal {signal.get('key')} has invalid availability/impact",
                severity="error", entity=f"{finding_entity}#signal:{signal.get('key')}",
                evidence={"signal": str(signal.get("key")), "available": repr(available),
                          "impactPp": repr(impact)})
        if supports not in (None, a, b):
            _add_finding(
                out, "output.prediction_evidence.support_unknown",
                f"{tour}: {label} evidence signal {signal.get('key')} supports an unknown player",
                severity="error", entity=f"{finding_entity}#signal:{signal.get('key')}",
                evidence={"signal": str(signal.get("key")), "supports": repr(supports)})
        if not isinstance(signal.get("facts"), dict):
            _add_finding(
                out, "output.prediction_evidence.facts_invalid",
                f"{tour}: {label} evidence signal {signal.get('key')} facts are malformed",
                severity="error", entity=f"{finding_entity}#signal:{signal.get('key')}",
                evidence={"signal": str(signal.get("key"))})
        if available:
            if unavailable_seen:
                _add_finding(
                    out, "output.prediction_evidence.availability_order_invalid",
                    f"{tour}: {label} strongest evidence is not ranked before unavailable signals",
                    severity="error", entity=finding_entity, evidence={})
            if _finite_between(impact, -100.0, 100.0):
                available_strengths.append(abs(float(impact)))
        else:
            unavailable_seen = True
    if available_strengths != sorted(available_strengths, reverse=True):
        _add_finding(
            out, "output.prediction_evidence.strength_order_invalid",
            f"{tour}: {label} available evidence is not strongest-first",
            severity="error", entity=finding_entity,
            evidence={"strengths": available_strengths})

def _check_profile_shards(out: list, tour: str, index: dict, shards: dict,
                          players: list | None) -> None:
    rows = index.get("profiles") or []
    if not isinstance(rows, list):
        _add_finding(
            out, "output.profile_index.roster_invalid",
            f"{tour}: profile-index.json profiles is not a list",
            severity="error", entity="artifact:profile-index.json",
            evidence={"valueType": type(rows).__name__})
        return
    names = [p.get("name") for p in rows if isinstance(p, dict)]
    files = [p.get("file") for p in rows if isinstance(p, dict)]
    if len(set(names)) != len(names) or any(not name for name in names):
        _add_finding(
            out, "output.profile_index.player_identity_invalid",
            f"{tour}: profile-index.json has duplicate/null player names",
            severity="error", entity="artifact:profile-index.json",
            evidence={"rows": len(rows), "uniqueNames": len(set(names))})
    if len(set(files)) != len(files) or any(not filename for filename in files):
        _add_finding(
            out, "output.profile_index.shard_identity_invalid",
            f"{tour}: profile-index.json has duplicate/null shard files",
            severity="error", entity="artifact:profile-index.json",
            evidence={"rows": len(rows), "uniqueFiles": len(set(files))})
    if isinstance(players, list) and names != [p.get("name") for p in players]:
        _add_finding(
            out, "output.profile_index.roster_mismatch",
            f"{tour}: profile-index.json roster/order disagrees with players.json",
            severity="error", entity="artifact:profile-index.json", evidence={})
    generation = index.get("generation")
    if not generation:
        _add_finding(
            out, "output.profile_index.generation_missing",
            f"{tour}: profile-index.json is missing generation",
            severity="error", entity="artifact:profile-index.json", evidence={})
    for summary in rows:
        if not isinstance(summary, dict):
            continue
        filename = summary.get("file")
        shard = shards.get(filename)
        if not isinstance(shard, dict):
            continue
        if shard.get("generation") != generation:
            _add_finding(
                out, "output.profile_shard.generation_mismatch",
                f"{tour}: {filename} generation disagrees with profile-index.json",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": generation, "actual": shard.get("generation")})
        if shard.get("name") != summary.get("name"):
            _add_finding(
                out, "output.profile_shard.player_mismatch",
                f"{tour}: {filename} names {shard.get('name')!r}, expected "
                f"{summary.get('name')!r}",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": repr(summary.get("name")),
                          "actual": repr(shard.get("name"))})

def _check_forecast_history(out: list, tour: str, label: str, forecast: object,
                            current: object | None = None, *, entity: str | None = None) -> None:
    """A visible timeline must be ordered, de-duplicated, and agree with its summary."""
    if not isinstance(forecast, dict):
        return
    finding_entity = entity or _match_entity(
        forecast,
        player_a=forecast.get("playerA"),
        player_b=forecast.get("playerB"),
    )
    timeline = forecast.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        _add_finding(
            out, "output.forecast.timeline_missing",
            f"{tour}: {label} forecast timeline is missing/empty",
            severity="error", entity=finding_entity,
            evidence={"valueType": type(timeline).__name__})
        return
    points = [point for point in timeline if isinstance(point, dict)]
    stamps = [str(point.get("asOf") or "") for point in points]
    hours = [stamp[:13] for stamp in stamps]
    generations: list[str] = []
    invalid_generations: list[dict] = []
    for index, point in enumerate(points):
        raw_generation = point.get("predictorArtifactId")
        if raw_generation is None:
            generations.append("legacy")
        elif isinstance(raw_generation, str) and _UUID4_RE.fullmatch(raw_generation):
            generations.append(raw_generation)
        else:
            generations.append(f"invalid:{index}")
            invalid_generations.append({
                "index": index,
                "value": repr(raw_generation),
            })
    generation_keys = list(zip(hours, generations, strict=True))
    if len(stamps) != len(timeline) or any(not stamp for stamp in stamps):
        _add_finding(
            out, "output.forecast.timestamp_missing",
            f"{tour}: {label} forecast timeline has a missing timestamp",
            severity="error", entity=finding_entity,
            evidence={"observations": len(timeline), "timestamps": len(stamps)})
    elif stamps != sorted(stamps) or len(generation_keys) != len(set(generation_keys)):
        _add_finding(
            out, "output.forecast.timeline_order_invalid",
            f"{tour}: {label} forecast timeline is unordered or repeats one predictor "
            "generation within a UTC hour",
            severity="error", entity=finding_entity,
            evidence={"timestamps": stamps, "predictorArtifactIds": generations})
    if invalid_generations:
        _add_finding(
            out, "output.forecast.predictor_generation_invalid",
            f"{tour}: {label} forecast timeline has an invalid predictor generation",
            severity="error", entity=finding_entity,
            evidence={"values": invalid_generations})
    probs = [point.get("p") for point in timeline if isinstance(point, dict)]
    if any(not _is_prob(p) for p in probs):
        _add_finding(
            out, "output.forecast.probability_invalid",
            f"{tour}: {label} forecast timeline has probability outside [0,1]",
            severity="error", entity=finding_entity,
            evidence={"values": [repr(p) for p in probs if not _is_prob(p)]})
        return
    if forecast.get("snapshots") != len(timeline):
        _add_finding(
            out, "output.forecast.snapshot_count_mismatch",
            f"{tour}: {label} forecast snapshots={forecast.get('snapshots')!r} "
            f"but timeline has {len(timeline)} observations",
            severity="error", entity=finding_entity,
            evidence={"declared": repr(forecast.get("snapshots")),
                      "actual": len(timeline)})
    if probs and isinstance(forecast.get("first"), (int, float)) \
            and abs(float(forecast["first"]) - float(probs[0])) > 1e-4:
        _add_finding(
            out, "output.forecast.first_probability_mismatch",
            f"{tour}: {label} forecast first disagrees with timeline",
            severity="error", entity=finding_entity,
            evidence={"summary": float(forecast["first"]), "timeline": float(probs[0])})
    expected_current = current if _is_prob(current) else forecast.get("current")
    if probs and _is_prob(expected_current) and abs(float(expected_current) - float(probs[-1])) > 1e-4:
        _add_finding(
            out, "output.forecast.current_probability_mismatch",
            f"{tour}: {label} current probability disagrees with latest saved observation",
            severity="error", entity=finding_entity,
            evidence={"summary": float(expected_current), "timeline": float(probs[-1])})
    if _is_prob(forecast.get("first")) and _is_prob(forecast.get("current")):
        delta = float(forecast["current"]) - float(forecast["first"])
        if not isinstance(forecast.get("delta"), (int, float)) or abs(delta - float(forecast["delta"])) > 1e-4:
            _add_finding(
                out, "output.forecast.delta_mismatch",
                f"{tour}: {label} forecast delta disagrees with first/current",
                severity="error", entity=finding_entity,
                evidence={"expected": delta, "actual": repr(forecast.get("delta"))})
    for index, point in enumerate(timeline):
        if isinstance(point, dict) and point.get("evidence") is not None:
            evidence = point["evidence"]
            _check_prediction_evidence(
                out, tour, f"{label} timeline point {index}", evidence,
                evidence.get("playerA") if isinstance(evidence, dict) else None,
                evidence.get("playerB") if isinstance(evidence, dict) else None,
                point.get("p"),
                entity=finding_entity,
            )

def _check_performance(out: list, tour: str, performance: dict, profile_index: object,
                       shards: dict) -> None:
    rows, window = performance.get("players"), performance.get("window")
    if not isinstance(rows, list) or not isinstance(window, int) or window < 1:
        _add_finding(
            out, "output.performance.contract_invalid",
            f"{tour}: performance.json players/window is malformed",
            severity="error", entity="artifact:performance.json",
            evidence={"playersType": type(rows).__name__, "window": repr(window)})
        return
    names = [row.get("name") for row in rows if isinstance(row, dict)]
    if len(names) != len(rows) or len(names) != len(set(names)) or any(not name for name in names):
        _add_finding(
            out, "output.performance.player_identity_invalid",
            f"{tour}: performance.json has malformed/duplicate player names",
            severity="error", entity="artifact:performance.json",
            evidence={"rows": len(rows), "names": len(names),
                      "uniqueNames": len(set(names))})
    by_name = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name, n, wins, expected, delta = (row.get(k) for k in
                                          ("name", "n", "wins", "expectedWins", "delta"))
        if not (isinstance(n, int) and 0 <= n <= window and isinstance(wins, int)
                and 0 <= wins <= n and isinstance(expected, (int, float)) and 0 <= expected <= n
                and isinstance(delta, (int, float)) and abs(float(delta) - (wins - float(expected))) <= 0.002):
            _add_finding(
                out, "output.performance.summary_invalid",
                f"{tour}: performance.json summary for {name!r} is inconsistent",
                severity="error", entity=f"player:{_player_identity_key(name)}",
                evidence={"n": repr(n), "wins": repr(wins),
                          "expectedWins": repr(expected), "delta": repr(delta),
                          "window": window})
            continue
        by_name[name] = row
    if not isinstance(profile_index, dict):
        return
    for summary in profile_index.get("profiles") or []:
        if not isinstance(summary, dict):
            continue
        perf = by_name.get(summary.get("name"))
        shipped_summary = summary.get("performance")
        expected_summary = ({k: perf.get(k) for k in ("n", "wins", "expectedWins", "delta")}
                            if perf else None)
        if shipped_summary != expected_summary:
            _add_finding(
                out, "output.performance.profile_summary_mismatch",
                f"{tour}: profile expectation summary disagrees for {summary.get('name')!r}",
                severity="error", entity=f"player:{_player_identity_key(summary.get('name'))}",
                evidence={"expected": expected_summary,
                          "actual": shipped_summary if isinstance(shipped_summary, dict)
                          else repr(shipped_summary)})
        detail = shards.get(summary.get("file"))
        if not isinstance(detail, dict):
            continue
        detail_perf = detail.get("performance")
        if not perf:
            if detail_perf is not None:
                _add_finding(
                    out, "output.performance.orphan_profile_detail",
                    f"{tour}: profile expectation detail exists without summary for "
                    f"{summary.get('name')!r}",
                    severity="error",
                    entity=f"player:{_player_identity_key(summary.get('name'))}", evidence={})
            continue
        if not isinstance(detail_perf, dict):
            _add_finding(
                out, "output.performance.profile_detail_missing",
                f"{tour}: profile expectation detail missing for {summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}", evidence={})
            continue
        if any(detail_perf.get(k) != perf.get(k) for k in ("n", "wins", "expectedWins", "delta")):
            _add_finding(
                out, "output.performance.profile_detail_mismatch",
                f"{tour}: profile expectation detail disagrees for {summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}", evidence={})
        decisions = detail_perf.get("recent")
        if not isinstance(decisions, list) or len(decisions) != perf["n"]:
            _add_finding(
                out, "output.performance.evidence_count_mismatch",
                f"{tour}: profile expectation evidence count disagrees for {summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}",
                evidence={"expected": perf["n"],
                          "actual": len(decisions) if isinstance(decisions, list) else None})
            continue
        ids = [decision.get("matchId") for decision in decisions if isinstance(decision, dict)]
        if len(ids) != len(set(ids)) or any(not str(match_id).startswith("v2|") for match_id in ids):
            _add_finding(
                out, "output.performance.match_identity_invalid",
                f"{tour}: profile expectation evidence has duplicate/legacy match IDs for "
                f"{summary.get('name')!r}",
                severity="error",
                entity=f"player:{_player_identity_key(summary.get('name'))}",
                evidence={"matchIds": list(map(str, ids))})
        for decision in decisions:
            if not isinstance(decision, dict) or not _is_prob(decision.get("p")):
                _add_finding(
                    out, "output.performance.probability_invalid",
                    f"{tour}: profile expectation evidence probability is invalid",
                    severity="error",
                    entity=f"player:{_player_identity_key(summary.get('name'))}",
                    evidence={"value": repr(decision.get("p"))
                              if isinstance(decision, dict) else repr(decision)})
                break
            expected_residual = (1.0 if decision.get("won") is True else 0.0) - decision["p"]
            if not isinstance(decision.get("residual"), (int, float)) \
                    or abs(expected_residual - decision["residual"]) > 1e-4:
                _add_finding(
                    out, "output.performance.residual_invalid",
                    f"{tour}: profile expectation residual is inconsistent",
                    severity="error",
                    entity=_match_entity(
                        decision,
                        player_a=summary.get("name"),
                        player_b=decision.get("opponent"),
                    ),
                    evidence={"expected": expected_residual,
                              "actual": repr(decision.get("residual"))})
                break

def _check_scenarios(out: list, tour: str, index: dict, shards: dict,
                     brackets: object) -> None:
    from ...sim.exact import propagate_rounds, validate_matrix
    from ...sim.scenarios import exact_bracket

    generation = index.get("generation")
    if (index.get("schema") != "scenario-v1" or index.get("schemaVersion") != 1
            or not generation or not isinstance(index.get("events"), list)):
        _add_finding(
            out, "output.scenario_index.contract_invalid",
            f"{tour}: scenario-index.json schema/events is malformed",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"schema": repr(index.get("schema")),
                      "schemaVersion": repr(index.get("schemaVersion")),
                      "generation": repr(generation),
                      "eventsType": type(index.get("events")).__name__})
        return
    refs_by_file = {
        entry.get("file"): entry for entry in index["events"] if isinstance(entry, dict)
    }
    refs = set(refs_by_file)
    event_ids = [str(entry.get("espnId") or "") for entry in index["events"]
                 if isinstance(entry, dict)]
    if (len(refs) != len(index["events"]) or None in refs
            or len(event_ids) != len(set(event_ids)) or any(not event_id for event_id in event_ids)):
        _add_finding(
            out, "output.scenario_index.shard_identity_invalid",
            f"{tour}: scenario-index.json repeats or omits shard files",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"events": len(index["events"]), "uniqueFiles": len(refs),
                      "eventIds": event_ids})
    if any(entry.get("generation") != generation for entry in refs_by_file.values()):
        _add_finding(
            out, "output.scenario_index.generation_mismatch",
            f"{tour}: scenario-index.json event generation is inconsistent",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"generation": generation})
    bracket_refs = {
        ((event.get("scenario") or {}).get("file") or event.get("scenarioFile"))
        for event in (brackets or []) if isinstance(event, dict)
        and event.get("status") in ("live", "upcoming")
        and ((event.get("scenario") or {}).get("file") or event.get("scenarioFile"))
    }
    if bracket_refs != refs:
        _add_finding(
            out, "output.scenario_index.bracket_reference_mismatch",
            f"{tour}: scenario-index.json files disagree with unsettled brackets",
            severity="error", entity="artifact:scenario-index.json",
            evidence={"indexFiles": sorted(map(str, refs)),
                      "bracketFiles": sorted(map(str, bracket_refs))})
    for filename in refs:
        shard = shards.get(filename)
        if not isinstance(shard, dict):
            continue
        ref = refs_by_file[filename]
        players, matrices, rounds = shard.get("players"), shard.get("matrices"), shard.get("rounds")
        event = shard.get("event") or {}
        event_id = str(event.get("espnId") or "")
        if (shard.get("schema") != "scenario-v1" or shard.get("schemaVersion") != 1
                or shard.get("generation") != generation
                or event_id != str(ref.get("espnId") or "")
                or shard.get("modelGeneration") != ref.get("modelGeneration")
                or not isinstance(players, list) or len(set(players)) != len(players) \
                or not isinstance(matrices, dict) or not isinstance(rounds, list) or not rounds):
            _add_finding(
                out, "output.scenario_shard.contract_invalid",
                f"{tour}: {filename} scenario structure is malformed",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expectedEspnId": str(ref.get("espnId") or ""),
                          "actualEspnId": event_id})
            continue
        n = len(players)
        bad_matrix = False
        for component in ("eloBlend", "pointModel", "combiner"):
            matrix = matrices.get(component)
            if not _square_matrix(matrix, n):
                bad_matrix = True
                break
            for i in range(n):
                for j in range(n):
                    if (not _is_prob(matrix[i][j])
                            or abs(float(matrix[i][j]) + float(matrix[j][i]) - 1.0) > 2e-5):
                        bad_matrix = True
                        break
        if bad_matrix:
            _add_finding(
                out, "output.scenario_shard.matrix_invalid",
                f"{tour}: {filename} scenario matrices are malformed/non-antisymmetric",
                severity="error", entity=f"artifact:{filename}",
                evidence={"players": n})
            continue
        if shard.get("matrix") != matrices["combiner"]:
            _add_finding(
                out, "output.scenario_shard.authoritative_matrix_mismatch",
                f"{tour}: {filename} authoritative matrix disagrees with combiner",
                severity="error", entity=f"artifact:{filename}", evidence={})
            continue
        try:
            validate_matrix(players, shard["matrix"], atol=2e-5)
            expected_baseline = propagate_rounds(
                rounds, players, shard["matrix"], event_id=event_id)
        except (TypeError, ValueError) as exc:
            _add_finding(
                out, "output.scenario_shard.exact_contract_invalid",
                f"{tour}: {filename} exact scenario contract failed ({exc})",
                severity="error", entity=f"artifact:{filename}",
                evidence={"failureType": type(exc).__name__})
            continue
        if shard.get("baseline") != expected_baseline:
            _add_finding(
                out, "output.scenario_shard.baseline_mismatch",
                f"{tour}: {filename} baseline disagrees with exact propagation",
                severity="error", entity=f"artifact:{filename}", evidence={})
        expected_legacy = exact_bracket(rounds, players, matrices["combiner"])
        if shard.get("base") != expected_legacy:
            _add_finding(
                out, "output.scenario_shard.base_forecast_mismatch",
                f"{tour}: {filename} base forecast disagrees with exact propagation",
                severity="error", entity=f"artifact:{filename}", evidence={})
        geometry = shard.get("geometry")
        expected_ids = [match["id"] for rnd in expected_baseline["rounds"] for match in rnd["matches"]]
        geometry_ids = [match.get("id") for rnd in geometry or []
                        for match in (rnd.get("matches") or []) if isinstance(match, dict)]
        if not isinstance(geometry, list) or geometry_ids != expected_ids:
            _add_finding(
                out, "output.scenario_shard.geometry_invalid",
                f"{tour}: {filename} stable match geometry is malformed",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expectedMatchIds": expected_ids,
                          "actualMatchIds": list(map(str, geometry_ids))})
        lockable = set(expected_baseline["lockableMatchIds"])
        if ref.get("lockableMatches") != len(lockable):
            _add_finding(
                out, "output.scenario_shard.lockable_count_mismatch",
                f"{tour}: {filename} lockable-match count disagrees with scenario index",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": len(lockable), "actual": ref.get("lockableMatches")})
        leverage = shard.get("titleLeverage")
        if not isinstance(leverage, dict) or set(leverage) != lockable:
            _add_finding(
                out, "output.scenario_shard.title_leverage_keys_mismatch",
                f"{tour}: {filename} title-leverage keys disagree with real unresolved matches",
                severity="error", entity=f"artifact:{filename}",
                evidence={"expected": sorted(map(str, lockable)),
                          "actual": sorted(map(str, leverage))
                          if isinstance(leverage, dict) else None})
        else:
            for match_id, row in leverage.items():
                if (not isinstance(row, dict) or not _is_prob(row.get("value"))
                        or not row.get("playerA") or not row.get("playerB")):
                    _add_finding(
                        out, "output.scenario_shard.title_leverage_invalid",
                        f"{tour}: {filename} title leverage {match_id} is malformed",
                        severity="error", entity=f"match:{match_id}",
                        evidence={"artifact": str(filename)})
                    break

def _check_upcoming_shards(out: list, tour: str, index: dict, shards: dict) -> None:
    """Validate the lazy upcoming graph before reconstructed rows reach existing checks."""
    generation = index.get("generation")
    events = index.get("events")
    highlights = index.get("highlights")
    if (index.get("schema") != "upcoming-v2" or index.get("schemaVersion") != 2
            or not generation or not isinstance(events, list)
            or not isinstance(highlights, list)
            or not isinstance(index.get("count"), int)):
        _add_finding(
            out, "output.upcoming_index.contract_invalid",
            f"{tour}: upcoming-index.json schema/events is malformed",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"schema": repr(index.get("schema")),
                      "schemaVersion": repr(index.get("schemaVersion")),
                      "generation": repr(generation)})
        return

    event_files, evidence_files, event_keys = [], [], []
    base_ids: list[str] = []
    total = 0
    for ref in events:
        if not isinstance(ref, dict):
            _add_finding(
                out, "output.upcoming_index.event_reference_invalid",
                f"{tour}: upcoming-index.json contains a malformed event reference",
                severity="error", entity="artifact:upcoming-index.json",
                evidence={"value": repr(ref)})
            continue
        event_file, evidence_file = ref.get("file"), ref.get("evidenceFile")
        event_files.append(event_file)
        evidence_files.append(evidence_file)
        event_id = str(ref.get("espnId") or "").strip()
        event_keys.append(("id", event_id) if event_id else ("name", str(ref.get("name") or "")))
        event_shard, evidence_shard = shards.get(event_file), shards.get(evidence_file)
        if not isinstance(event_shard, dict) or not isinstance(evidence_shard, dict):
            continue  # read_outputs reports the exact missing/corrupt filename
        matches, details = event_shard.get("matches"), evidence_shard.get("details")
        if (event_shard.get("schema") != "upcoming-event-v1"
                or evidence_shard.get("schema") != "upcoming-evidence-v1"
                or event_shard.get("generation") != generation
                or evidence_shard.get("generation") != generation
                or not isinstance(matches, list) or not isinstance(details, list)):
            _add_finding(
                out, "output.upcoming_shard.contract_invalid",
                f"{tour}: upcoming shards for {ref.get('name')!r} are malformed",
                severity="error",
                entity=_event_entity(ref),
                evidence={"eventFile": repr(event_file),
                          "evidenceFile": repr(evidence_file)})
            continue
        match_ids = [row.get("matchId") for row in matches if isinstance(row, dict)]
        detail_ids = [row.get("matchId") for row in details if isinstance(row, dict)]
        if (len(match_ids) != len(matches) or len(set(match_ids)) != len(match_ids)
                or any(not isinstance(match_id, str) or not match_id for match_id in match_ids)
                or len(detail_ids) != len(details) or len(set(detail_ids)) != len(detail_ids)
                or set(match_ids) != set(detail_ids)):
            _add_finding(
                out, "output.upcoming_shard.match_identity_mismatch",
                f"{tour}: upcoming match/detail identities disagree for {ref.get('name')!r}",
                severity="error",
                entity=_event_entity(ref),
                evidence={"matchIds": list(map(str, match_ids)),
                          "detailIds": list(map(str, detail_ids))})
        if ref.get("count") != len(matches):
            _add_finding(
                out, "output.upcoming_shard.count_mismatch",
                f"{tour}: upcoming shard count disagrees for {ref.get('name')!r}",
                severity="error",
                entity=_event_entity(ref),
                evidence={"declared": ref.get("count"), "actual": len(matches)})
        base_ids.extend(match_ids)
        total += len(matches)

    if (len(set(event_files)) != len(event_files) or len(set(evidence_files)) != len(evidence_files)
            or len(set(event_keys)) != len(event_keys) or any(key[1] == "" for key in event_keys)):
        _add_finding(
            out, "output.upcoming_index.event_identity_invalid",
            f"{tour}: upcoming-index.json repeats or omits event shard identity",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"eventFiles": list(map(str, event_files)),
                      "evidenceFiles": list(map(str, evidence_files)),
                      "eventKeys": [[str(a), str(b)] for a, b in event_keys]})
    if len(set(base_ids)) != len(base_ids):
        _add_finding(
            out, "output.upcoming_index.match_identity_duplicate",
            f"{tour}: upcoming match identity appears in more than one event shard",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"matchIds": base_ids})
    if total != index.get("count"):
        _add_finding(
            out, "output.upcoming_index.count_mismatch",
            f"{tour}: upcoming-index.json count={index.get('count')} but shards contain {total}",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"declared": index.get("count"), "actual": total})

    highlight_ids = [row.get("matchId") for row in highlights if isinstance(row, dict)]
    if (len(highlight_ids) != len(highlights) or len(set(highlight_ids)) != len(highlight_ids)
            or not set(highlight_ids).issubset(set(base_ids))
            or any(any(key in row for key in ("components", "evidence", "forecast"))
                   for row in highlights if isinstance(row, dict))):
        _add_finding(
            out, "output.upcoming_index.highlights_invalid",
            f"{tour}: upcoming-index.json highlights are duplicated, unknown, or heavy",
            severity="error", entity="artifact:upcoming-index.json",
            evidence={"highlightIds": list(map(str, highlight_ids))})

def _check_watch_ranking(out: list, tour: str, upcoming: list,
                         scenario_index: object, shards: dict) -> None:
    """Pin the transparent score math and its stable exact-leverage join."""
    expected_leverage = {}
    if isinstance(scenario_index, dict):
        generation = scenario_index.get("generation")
        for ref in scenario_index.get("events") or []:
            if not isinstance(ref, dict) or ref.get("generation") != generation:
                continue
            shard = shards.get(ref.get("file"))
            if not isinstance(shard, dict) or shard.get("generation") != generation:
                continue
            rounds = {
                match.get("id"): str(rnd.get("round") or "")
                for rnd in shard.get("geometry") or [] if isinstance(rnd, dict)
                for match in rnd.get("matches") or [] if isinstance(match, dict)
            }
            for match_id, row in (shard.get("titleLeverage") or {}).items():
                if not isinstance(row, dict) or not _is_prob(row.get("value")):
                    continue
                pair = frozenset((_player_identity_key(row.get("playerA")),
                                  _player_identity_key(row.get("playerB"))))
                expected_leverage[(str(ref.get("espnId") or ""), pair,
                                   rounds.get(match_id, ""))] = float(row["value"]) * 100.0

    ranks = []
    for match in upcoming:
        label = f"upcoming {match.get('playerA')!r} vs {match.get('playerB')!r}"
        match_entity = _match_entity(
            match,
            player_a=match.get("playerA"),
            player_b=match.get("playerB"),
        )
        watch, rank = match.get("watch"), match.get("watchRank")
        if not isinstance(watch, dict) or watch.get("schema") != "watch-v1":
            _add_finding(
                out, "output.watch_score.contract_invalid",
                f"{tour}: {label} watch-v1 score is missing/malformed",
                severity="error", entity=match_entity,
                evidence={"valueType": type(watch).__name__})
            continue
        if not isinstance(rank, int) or isinstance(rank, bool):
            _add_finding(
                out, "output.watch_score.rank_invalid",
                f"{tour}: {label} watchRank is missing/malformed",
                severity="error", entity=match_entity, evidence={"rank": repr(rank)})
        else:
            ranks.append((rank, watch.get("score")))
        if watch.get("weights") != _WATCH_WEIGHTS:
            _add_finding(
                out, "output.watch_score.weights_mismatch",
                f"{tour}: {label} watch weights disagree with watch-v1",
                severity="error", entity=match_entity,
                evidence={"expected": _WATCH_WEIGHTS,
                          "actual": watch.get("weights")
                          if isinstance(watch.get("weights"), dict)
                          else repr(watch.get("weights"))})
        factors = watch.get("factors")
        if not isinstance(factors, dict) or set(factors) != set(_WATCH_WEIGHTS):
            _add_finding(
                out, "output.watch_score.factor_set_invalid",
                f"{tour}: {label} watch factors are missing/duplicated",
                severity="error", entity=match_entity,
                evidence={"expected": sorted(_WATCH_WEIGHTS),
                          "actual": sorted(map(str, factors))
                          if isinstance(factors, dict) else None})
            continue
        available_count = 0
        weighted = 0.0
        for key, weight in _WATCH_WEIGHTS.items():
            factor = factors.get(key)
            if (not isinstance(factor, dict) or not isinstance(factor.get("available"), bool)
                    or not _finite_between(factor.get("score"), 0.0, 100.0)):
                _add_finding(
                    out, "output.watch_score.factor_invalid",
                    f"{tour}: {label} watch factor {key} is invalid",
                    severity="error", entity=f"{match_entity}#factor:{key}",
                    evidence={"factor": key, "value": repr(factor)})
                continue
            available_count += int(factor["available"])
            weighted += weight * float(factor["score"]) / 100.0
            if key in ("closeness", "quality", "stakes") and not factor["available"]:
                _add_finding(
                    out, "output.watch_score.required_factor_unavailable",
                    f"{tour}: {label} required watch factor {key} is unavailable",
                    severity="error", entity=f"{match_entity}#factor:{key}",
                    evidence={"factor": key})
            if not factor["available"] and float(factor["score"]) != 0.0:
                _add_finding(
                    out, "output.watch_score.unavailable_factor_bonus",
                    f"{tour}: {label} unavailable watch factor {key} received a bonus",
                    severity="error", entity=f"{match_entity}#factor:{key}",
                    evidence={"factor": key, "score": float(factor["score"])})
        if watch.get("coverage") != available_count:
            _add_finding(
                out, "output.watch_score.coverage_mismatch",
                f"{tour}: {label} watch coverage disagrees with available factors",
                severity="error", entity=match_entity,
                evidence={"expected": available_count, "actual": watch.get("coverage")})
        if (not _finite_between(watch.get("score"), 0.0, 100.0)
                or abs(float(watch["score"]) - weighted) > 0.11):
            _add_finding(
                out, "output.watch_score.total_mismatch",
                f"{tour}: {label} watch score disagrees with weighted factors",
                severity="error", entity=match_entity,
                evidence={"expected": weighted, "actual": repr(watch.get("score"))})

        pair = frozenset((_player_identity_key(match.get("playerA")),
                          _player_identity_key(match.get("playerB"))))
        leverage = expected_leverage.get((str(match.get("espnId") or ""), pair,
                                          str(match.get("round") or "")))
        title = factors.get("titleLeverage")
        if isinstance(title, dict):
            if leverage is None and title.get("available"):
                _add_finding(
                    out, "output.watch_score.title_leverage_orphan",
                    f"{tour}: {label} title leverage lacks same-generation exact evidence",
                    severity="error", entity=match_entity, evidence={})
            elif leverage is not None and (not title.get("available")
                                           or abs(float(title.get("score", -1)) - leverage) > 0.11):
                _add_finding(
                    out, "output.watch_score.title_leverage_mismatch",
                    f"{tour}: {label} title leverage disagrees with exact scenario",
                    severity="error", entity=match_entity,
                    evidence={"expected": leverage, "actual": repr(title.get("score"))})
    if len(ranks) == len(upcoming):
        ordered = sorted(ranks)
        if [rank for rank, _ in ordered] != list(range(1, len(upcoming) + 1)):
            _add_finding(
                out, "output.watch_score.ranking_not_contiguous",
                f"{tour}: upcoming watchRank is not contiguous 1..{len(upcoming)}",
                severity="error", entity="artifact:upcoming-index.json",
                evidence={"ranks": [rank for rank, _ in ordered],
                          "expectedCount": len(upcoming)})
        scores = [float(score) for _, score in ordered if _finite_between(score, 0.0, 100.0)]
        if len(scores) == len(ordered) and scores != sorted(scores, reverse=True):
            _add_finding(
                out, "output.watch_score.ranking_order_invalid",
                f"{tour}: upcoming watchRank is not score-descending",
                severity="error", entity="artifact:upcoming-index.json",
                evidence={"scores": scores})
