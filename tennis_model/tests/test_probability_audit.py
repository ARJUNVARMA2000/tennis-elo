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
        'predictorArtifactId':pred.artifact_id,'predictionAuditSourceGeneration':'frozen-input'}}}
    code = 'output.prediction.independent_audit_invalid'
    now = pd.Timestamp.now(tz='UTC')
    assert code in {f.code for f in output_findings('atp',outputs,now)}
    outputs['prediction_audit'] = receipt
    assert code not in {f.code for f in output_findings('atp',outputs,now)}
    outputs['data']['meta']['predictorArtifactId'] = 'another-model'
    assert code in {f.code for f in output_findings('atp',outputs,now)}
