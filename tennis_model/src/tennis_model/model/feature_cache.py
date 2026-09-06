"""Content and policy identity for derived research feature frames."""

import hashlib
import importlib.metadata
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .. import config
from ..data.style_history import STYLE_POLICY, STYLE_VERSION
from ..points.serve_prior import PRIOR_POLICY
from ..points.serve_return import sr_params_for
from ..ratings.elo import params_for
from .features import ANTISYM, FEATURES, SYMMETRIC, feat_params_for

FEATURE_CACHE_SCHEMA = 2


def _inventory(root):
    rows = []
    if not root.exists():
        return rows
    for p in sorted(root.rglob('*')):
        if p.is_symlink():
            raise ValueError(f"feature input contains a symlink: {p}")
        if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'):
            rows.append((str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()))
    return rows


def feature_cache_contract(tour):
    """Conservative identity: all frozen raw inputs and source definitions, no path/mtime reuse.

    Includes runtime overrides separately from source bytes. Hashing extra raw sources
    costs a cache miss rather than allowing an untracked feature dependency to leak in.
    """
    constants = {}
    for key, value in vars(config).items():
        if not key.isupper() or isinstance(value, Path):
            continue
        try:
            json.dumps(value, allow_nan=False, sort_keys=True)
        except (TypeError, ValueError):
            continue
        constants[key] = value
    return {
        'schema': FEATURE_CACHE_SCHEMA, 'tour': tour,
        'features': FEATURES, 'antisymmetric': ANTISYM, 'symmetric': SYMMETRIC,
        'featureParams': asdict(feat_params_for(tour)), 'eloParams': asdict(params_for(tour)),
        'serveParams': asdict(sr_params_for(tour)), 'config': constants,
        'stylePolicy': STYLE_POLICY, 'styleVersion': STYLE_VERSION, 'priorPolicy': PRIOR_POLICY,
        'python': list(sys.version_info[:3]),
        'libraries': {p: importlib.metadata.version(p) for p in ('pandas','numpy','scikit-learn','xgboost')},
        'asOfDay': datetime.now(UTC).date().isoformat(),
        'raw': _inventory(config.RAW_DIR),
        'source': _inventory(Path(__file__).resolve().parents[1]),
    }


def feature_cache_identity(tour):
    contract = feature_cache_contract(tour)
    return hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()
