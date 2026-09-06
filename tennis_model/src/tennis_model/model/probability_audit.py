"""Bounded evidence from independent prediction entry points, ready for release wiring."""

import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from .probability import PROBABILITY_POLICY

AUDIT_SCHEMA = 'prediction-audit-v1'
AUDIT_FILENAME = 'prediction-audit.private'
AUDIT_TOLERANCE = 1e-12
MAX_AUDIT_PAIRS = 240


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def build_prediction_audit(predictor, players, contexts, *, source_generation):
    """Call scalar A/B and B/A independently, then compare actual matrix/permuted calls."""
    if not 2 <= len(players) <= 8 or len(set(players)) != len(players):
        raise ValueError('audit requires 2–8 unique players')
    if not contexts or len(contexts) * len(players) * (len(players)-1) // 2 > MAX_AUDIT_PAIRS:
        raise ValueError('audit context/pair count is empty or unbounded')
    evidence = []
    for context_index, context in enumerate(contexts):
        matrix = predictor.prediction_matrices(players, **context)['combiner']
        permutation = list(reversed(range(len(players))))
        permuted = predictor.prediction_matrices([players[i] for i in permutation], **context)['combiner']
        restored = permuted[np.ix_(permutation, permutation)]
        for i,a in enumerate(players):
            for j in range(i+1,len(players)):
                b = players[j]
                forward = predictor.win_prob(a,b,**context)
                reverse = predictor.win_prob(b,a,**context)
                component = predictor.prediction_components(a,b,**context)['combiner']
                evidence.append({'context':context_index,'a':a,'b':b,'forward':float(forward),
                    'reverse':float(reverse),'matrix':float(matrix[i,j]),'permuted':float(restored[i,j]),
                    'component':float(component)})
    return {'schema':AUDIT_SCHEMA,'policy':PROBABILITY_POLICY,
        'predictorArtifactId':predictor.artifact_id,'inferenceSchema':predictor.inference_schema_version,
        'sourceGeneration':source_generation,'observedAt':datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'players':list(players),'contexts':list(contexts),'contextFingerprint':_digest(contexts),
        'pairCount':len(evidence),'evidence':evidence,'evidenceDigest':_digest(evidence)}


def validate_prediction_audit(receipt, *, artifact_id, inference_schema, source_generation, now):
    """Recompute invariants from bounded witness rows; a boolean/max claim is insufficient."""
    fields = {'schema','policy','predictorArtifactId','inferenceSchema','sourceGeneration','observedAt',
              'players','contexts','contextFingerprint','pairCount','evidence','evidenceDigest'}
    if type(receipt) is not dict or set(receipt) != fields:
        raise ValueError('missing or malformed prediction audit')
    if (receipt['schema'] != AUDIT_SCHEMA or receipt['policy'] != PROBABILITY_POLICY
            or receipt['predictorArtifactId'] != artifact_id or receipt['inferenceSchema'] != inference_schema
            or not source_generation or receipt['sourceGeneration'] != source_generation):
        raise ValueError('prediction audit identity is stale')
    observed = datetime.fromisoformat(receipt['observedAt'])
    if observed.tzinfo is None or now.tzinfo is None:
        raise ValueError('prediction audit requires timezone-aware timestamps')
    age = (now - observed).total_seconds()
    if not 0 <= age <= 7200:
        raise ValueError('prediction audit timestamp is stale or in the future')
    rows, players, contexts = receipt['evidence'], receipt['players'], receipt['contexts']
    if type(players) is not list or not 2 <= len(players) <= 8 or len(set(players)) != len(players):
        raise ValueError('invalid prediction audit roster')
    if type(contexts) is not list or not contexts or type(rows) is not list:
        raise ValueError('prediction audit is empty')
    expected = {(k,a,b) for k in range(len(contexts)) for i,a in enumerate(players) for b in players[i+1:]}
    if not 1 <= len(expected) <= MAX_AUDIT_PAIRS or receipt['pairCount'] != len(expected) or len(rows) != len(expected):
        raise ValueError('prediction audit has missing/extra pairs')
    if receipt['contextFingerprint'] != _digest(contexts) or receipt['evidenceDigest'] != _digest(rows):
        raise ValueError('prediction audit content digest mismatch')
    seen = set()
    worst = 0.
    for row in rows:
        if type(row) is not dict or set(row) != {'context','a','b','forward','reverse','matrix','permuted','component'}:
            raise ValueError('prediction audit observation is malformed')
        key = (row['context'],row['a'],row['b'])
        if key not in expected or key in seen:
            raise ValueError('prediction audit pair identity mismatch')
        seen.add(key)
        values = [row[k] for k in ('forward','reverse','matrix','permuted','component')]
        if any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in values):
            raise ValueError('prediction audit probability is invalid')
        forward,reverse,matrix,permuted,component = values
        error = max(abs(forward+reverse-1),abs(forward-matrix),abs(matrix-permuted),abs(forward-component))
        worst = max(worst,error)
    if worst > AUDIT_TOLERANCE:
        raise ValueError(f'prediction exchange/path discrepancy: {worst:.6g}')
    return {'pairs':len(rows),'maxError':worst}


def write_prediction_audit(predictor, frame, players, path):
    """Full/quick shared producer; missing real input identity or branch coverage is fatal."""
    from ..artifact_lineage import _atomic_write_bytes

    normalized = frame.attrs.get('normalizedInputFingerprint')
    if not isinstance(normalized, str) or not normalized.startswith('nm'):
        raise ValueError('prediction audit requires normalized input identity')
    counts = predictor.elo.n
    names = sorted({p['name'] for p in players} | set(counts))
    threshold = predictor.dual_state_threshold
    if threshold is not None:
        hot = sorted((n for n in names if counts.get(n, 0) >= threshold), key=lambda n: (-counts[n], n))[:2]
        cold = sorted((n for n in names if counts.get(n, 0) < threshold), key=lambda n: (counts.get(n, 0), n))[:2]
        if len(hot) < 2 or not cold:
            raise ValueError('prediction audit cannot exercise both WTA state branches')
        roster = hot + cold
    else:
        roster = sorted(names, key=lambda n: (-counts.get(n, 0), n))[:4]
    as_of = datetime.now(UTC).date().isoformat()
    contexts = [{'surface':s, 'best_of':b, 'as_of':as_of}
                for s in ('Hard', 'Clay', 'Grass') for b in (3, 5)]
    generation = _digest({'normalizedInput':normalized, 'asOf':as_of,
                          'artifactId':predictor.artifact_id, 'contexts':contexts})
    receipt = build_prediction_audit(predictor, roster, contexts, source_generation=generation)
    validate_prediction_audit(receipt, artifact_id=predictor.artifact_id,
        inference_schema=predictor.inference_schema_version, source_generation=generation,
        now=datetime.now(UTC))
    raw = (json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()
    if len(raw) > 256 * 1024:
        raise ValueError('prediction audit exceeds private byte bound')
    path = Path(path)
    _atomic_write_bytes(path, raw, trusted_root=path.parent.parent)
    return {'predictionAuditSchema':AUDIT_SCHEMA, 'predictionAuditSourceGeneration':generation,
            'predictionAuditSHA256':hashlib.sha256(raw).hexdigest(),
            'predictionAuditObservedAt':receipt['observedAt'],
            'inferenceSchemaVersion':predictor.inference_schema_version}


def validate_audit_metadata(receipt, meta, *, now, raw_sha256=None):
    from .predict import INFERENCE_SCHEMA_VERSION

    if (meta.get('predictionAuditSchema') != AUDIT_SCHEMA
            or meta.get('inferenceSchemaVersion') != INFERENCE_SCHEMA_VERSION
            or not isinstance(receipt, dict)
            or meta.get('predictionAuditObservedAt') != receipt.get('observedAt')
            or (raw_sha256 is not None and meta.get('predictionAuditSHA256') != raw_sha256)):
        raise ValueError('prediction audit metadata/content binding mismatch')
    return validate_prediction_audit(receipt, artifact_id=meta.get('predictorArtifactId'),
        inference_schema=INFERENCE_SCHEMA_VERSION,
        source_generation=meta.get('predictionAuditSourceGeneration'), now=now)
