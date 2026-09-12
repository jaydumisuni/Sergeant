from main_review.relational_assurance import RelationKind, RelationProbe, RelationalAssuranceCampaign

def make(kind: RelationKind, *, holds: bool = True) -> RelationProbe:
    return RelationProbe.create(probe_id=f"required:{kind.value}", kind=kind, left_identity=f"left:{kind.value}", right_identity=f"right:{kind.value}", relation_holds=holds, equivalent=(kind is RelationKind.PYTHON_VS_RUST), detector=f"detector:{kind.value}")

def test_qualification_covers_all_required_relations():
    result=RelationalAssuranceCampaign.create(probes=[make(k) for k in RelationKind]).evaluate()
    assert result.qualified
    assert len(result.passed_relations)==7
    assert result.failed_relations==()
    assert result.missing_required_kinds==()

def test_qualification_fails_for_authority_world_mismatch():
    probes=[make(k, holds=(k is not RelationKind.AUTHORIZED_VS_UNAUTHORIZED_WORLD)) for k in RelationKind]
    result=RelationalAssuranceCampaign.create(probes=probes).evaluate()
    assert not result.qualified
    assert "required:authorized_vs_unauthorized_world" in result.failed_relations

def test_qualification_fails_for_effect_set_mismatch():
    probes=[make(k, holds=(k is not RelationKind.EXPECTED_VS_OBSERVED_EFFECT_SET)) for k in RelationKind]
    result=RelationalAssuranceCampaign.create(probes=probes).evaluate()
    assert not result.qualified
    assert "required:expected_vs_observed_effect_set" in result.failed_relations
