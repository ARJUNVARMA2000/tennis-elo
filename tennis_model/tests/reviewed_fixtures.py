"""Explicit reviewed-input universe for existing synthetic source/output tests."""

import hashlib
import json

from tennis_model import config
from tennis_model.data import result_ledger


def empty_reviewed_scope(monkeypatch, directory):
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for tour in ('atp', 'wta'):
        doc = {'schema':'reviewed-results-v1', 'tour':tour,
               'populationVersion':config.MATCH_POPULATION_VERSION,
               'coverage':'Explicit empty review scope in a synthetic test universe.',
               'records':[], 'quarantines':[]}
        raw = json.dumps(doc).encode()
        (directory / f'{tour}.json').write_bytes(raw)
        manifest[tour] = {'sha256':hashlib.sha256(raw).hexdigest(), 'records':0, 'quarantines':0}
    monkeypatch.setattr(result_ledger, 'LEDGER_DIR', directory)
    monkeypatch.setattr(config, 'REVIEWED_RESULTS', manifest)
