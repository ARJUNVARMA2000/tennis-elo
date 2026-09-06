from copy import deepcopy
from datetime import UTC, datetime

import pytest
from tennis_model.model.probability import calibrated_probability
from tennis_model.model.probability_audit import build_prediction_audit, validate_prediction_audit
from test_probability import predictor


def audit(pred):
    return build_prediction_audit(pred,['Alfa One','Bravo Two','Charlie Three'],
        [{'surface':'Hard','best_of':3},{'surface':'Clay','best_of':5}],source_generation='frozen-input')


def validate(pred,receipt):
    return validate_prediction_audit(receipt,artifact_id=pred.artifact_id,
        inference_schema=pred.inference_schema_version,source_generation='frozen-input',now=datetime.now(UTC))


def test_independent_witness_rejects_original_defect_even_with_complementary_matrix(monkeypatch):
    pred=predictor()
    receipt=audit(pred)
    assert validate(pred,receipt)['pairs']==6
    monkeypatch.setattr(pred,'win_prob',lambda a,b,**kw:float(calibrated_probability(pred.clf,pred.iso,pred.features(a,b,**kw))[0]))
    matrix=pred.prediction_matrices(['Alfa One','Bravo Two'])['combiner']
    assert matrix[0,1]+matrix[1,0]==1
    with pytest.raises(ValueError,match='discrepancy'):
        validate(pred,audit(pred))


@pytest.mark.parametrize('mutate',[
    lambda r:r.update(predictorArtifactId='wrong'),
    lambda r:r.update(sourceGeneration='old'),
    lambda r:r.update(observedAt='2000-01-01T00:00:00+00:00'),
    lambda r:r.update(observedAt='2026-09-06T00:00:00'),
    lambda r:r.update(pairCount=0),
    lambda r:r['evidence'].pop(),
    lambda r:r.update(evidenceDigest='wrong'),
    lambda r:r.update(evidence=[]),
])
def test_audit_rejects_stale_empty_or_modified_receipts(mutate):
    pred=predictor()
    receipt=deepcopy(audit(pred))
    mutate(receipt)
    with pytest.raises(ValueError):
        validate(pred,receipt)


def test_output_gate_requires_independent_receipt_after_declared_rollout():
    import pandas as pd
    from tennis_model.data.health import output_findings
    from tennis_model.model.probability_audit import AUDIT_SCHEMA

    pred = predictor()
    receipt = audit(pred)
    outputs = {'data':{'meta':{'predictionAuditSchema':AUDIT_SCHEMA,
        'inferenceSchemaVersion':pred.inference_schema_version,
        'predictionAuditObservedAt':receipt['observedAt'],
        'predictorArtifactId':pred.artifact_id,'predictionAuditSourceGeneration':'frozen-input'}}}
    code = 'output.prediction.independent_audit_invalid'
    now = pd.Timestamp.now(tz='UTC')
    assert code in {f.code for f in output_findings('atp',outputs,now)}
    outputs['prediction_audit'] = receipt
    assert code not in {f.code for f in output_findings('atp',outputs,now)}
    outputs['data']['meta']['predictorArtifactId'] = 'another-model'
    assert code in {f.code for f in output_findings('atp',outputs,now)}


@pytest.mark.parametrize('tour,lower', [('atp', False), ('wta', True)])
def test_real_writer_binds_input_artifact_and_private_bytes(tmp_path, tour, lower):
    import hashlib
    import json

    import pandas as pd
    from tennis_model.model.probability_audit import (
        AUDIT_FILENAME,
        validate_audit_metadata,
        write_prediction_audit,
    )

    pred = predictor(tour, lower)
    frame = pd.DataFrame()
    frame.attrs['normalizedInputFingerprint'] = 'nm2:' + 'a' * 64
    path = tmp_path / tour / AUDIT_FILENAME
    path.parent.mkdir()
    meta = write_prediction_audit(pred, frame, [], path)
    raw = path.read_bytes()
    receipt = json.loads(raw)
    meta['predictorArtifactId'] = pred.artifact_id
    assert validate_audit_metadata(receipt, meta, now=datetime.now(UTC),
        raw_sha256=hashlib.sha256(raw).hexdigest())['pairs'] == 18
    if lower:
        counts = [pred.elo.n[n] for n in receipt['players']]
        assert sum(n >= 32 for n in counts) == 2 and min(counts) < 32
    frame.attrs['normalizedInputFingerprint'] = 'nm2:' + 'b' * 64
    assert write_prediction_audit(pred, frame, [], path)['predictionAuditSourceGeneration'] != meta['predictionAuditSourceGeneration']
    with pytest.raises(ValueError, match='binding'):
        validate_audit_metadata(receipt, meta, now=datetime.now(UTC), raw_sha256='0'*64)
    frame.attrs.clear()
    with pytest.raises(ValueError, match='input identity'):
        write_prediction_audit(pred, frame, [], path)


def test_private_writer_rejects_symlinked_tour_before_external_write(tmp_path):
    import pandas as pd
    from tennis_model.artifact_lineage import ArtifactLineageError
    from tennis_model.model.probability_audit import AUDIT_FILENAME, write_prediction_audit

    outside = tmp_path / 'outside'; outside.mkdir()
    root = tmp_path / 'output'; root.mkdir()
    (root / 'atp').symlink_to(outside, target_is_directory=True)
    frame = pd.DataFrame()
    frame.attrs['normalizedInputFingerprint'] = 'nm2:' + 'a' * 64
    with pytest.raises(ArtifactLineageError):
        write_prediction_audit(predictor(), frame, [], root / 'atp' / AUDIT_FILENAME)
    assert not list(outside.iterdir())
