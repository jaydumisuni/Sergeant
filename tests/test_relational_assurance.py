import pytest

from main_review.relational_assurance import (
    RelationKind, RelationProbe, RelationalAssuranceCampaign, RelationalAssuranceError,
)


def probe(kind, left="left:v1", right="right:v2", equivalent=None):
    if equivalent is None:
        equivalent = kind is RelationKind.PYTHON_VS_RUST
    return RelationProbe.create(
        probe_id=f"p-{kind.value}", kind=kind, left_identity=left, right_identity=right,
        relation_holds=True, equivalent=equivalent, detector="detector:v1",
    )


def test_all_required_relations_qualify():
    campaign = RelationalAssuranceCampaign.create(probes=[probe(k, equivalent=(k is RelationKind.PYTHON_VS_RUST)) for k in RelationKind])
    result = campaign.evaluate()
    assert result.qualified is True
    assert result.failed_relations == ()
    assert result.missing_required_kinds == ()


def test_missing_required_relation_fails_closed():
    campaign = RelationalAssuranceCampaign.create(probes=[probe(k) for k in RelationKind if k is not RelationKind.SINGLE_EXECUTION_VS_RETRY])
    result = campaign.evaluate()
    assert result.qualified is False
    assert "single_execution_vs_retry" in result.missing_required_kinds


def test_failed_relation_fails_qualification():
    values=[probe(k) for k in RelationKind]
    bad=values[0]
    values[0]=RelationProbe.create(probe_id=bad.probe_id, kind=bad.kind, left_identity=bad.left_identity, right_identity=bad.right_identity, relation_holds=False, equivalent=False, detector=bad.detector)
    result=RelationalAssuranceCampaign.create(probes=values).evaluate()
    assert result.qualified is False
    assert bad.probe_id in result.failed_relations

@pytest.mark.parametrize("kind", list(RelationKind))
def test_material_relations_reject_identical_worlds_except_cross_runtime(kind):
    if kind is RelationKind.PYTHON_VS_RUST:
        assert probe(kind, left="semantics:v1", right="semantics:v1", equivalent=True).equivalent
    else:
        with pytest.raises(RelationalAssuranceError):
            probe(kind, left="same:v1", right="same:v1")

def test_cross_runtime_requires_declared_semantic_equivalence():
    with pytest.raises(RelationalAssuranceError):
        probe(RelationKind.PYTHON_VS_RUST, equivalent=False)

def test_duplicate_relation_identity_fails_closed():
    p=probe(RelationKind.OLD_VS_NEW)
    with pytest.raises(RelationalAssuranceError):
        RelationalAssuranceCampaign.create(probes=[p,p])

def test_noncanonical_identity_fails_closed():
    with pytest.raises(RelationalAssuranceError):
        RelationProbe.create(probe_id=" p ", kind=RelationKind.OLD_VS_NEW, left_identity="a", right_identity="b", relation_holds=True, equivalent=False, detector="d")
