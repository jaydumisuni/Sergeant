from __future__ import annotations

import pytest

from main_review.semantic_mutation import (
    MutationCampaignError,
    MutationKind,
    MutationProbe,
    SemanticMutationCampaign,
)


def probe(kind: MutationKind, *, killed: bool = True, changed: bool | None = None) -> MutationProbe:
    if changed is None:
        changed = kind is not MutationKind.NO_OP_DETECTION
    baseline = f"baseline:{kind.value}"
    mutated = f"mutated:{kind.value}" if changed else baseline
    return MutationProbe.create(
        mutant_id=f"mutant:{kind.value}",
        kind=kind,
        baseline_identity=baseline,
        mutated_identity=mutated,
        killed=killed,
        detector=f"detector:{kind.value}",
    )


def complete_campaign() -> SemanticMutationCampaign:
    return SemanticMutationCampaign.create(probes=[probe(kind) for kind in MutationKind])


def test_complete_required_semantic_mutation_campaign_qualifies() -> None:
    result = complete_campaign().evaluate()
    assert result.qualified is True
    assert result.surviving_mutants == ()
    assert result.missing_required_kinds == ()
    assert set(result.killed_mutants) == {f"mutant:{kind.value}" for kind in MutationKind}


@pytest.mark.parametrize("missing", list(MutationKind))
def test_missing_required_mutant_fails_closed(missing: MutationKind) -> None:
    campaign = SemanticMutationCampaign.create(
        probes=[probe(kind) for kind in MutationKind if kind is not missing]
    )
    result = campaign.evaluate()
    assert result.qualified is False
    assert result.missing_required_kinds == (missing.value,)


@pytest.mark.parametrize("survivor", list(MutationKind))
def test_any_required_surviving_mutant_is_qualification_failure(survivor: MutationKind) -> None:
    probes = [probe(kind, killed=(kind is not survivor)) for kind in MutationKind]
    result = SemanticMutationCampaign.create(probes=probes).evaluate()
    assert result.qualified is False
    assert result.surviving_mutants == (f"mutant:{survivor.value}",)


def test_duplicate_mutant_identity_is_rejected() -> None:
    first = probe(MutationKind.GUARD_DELETION)
    duplicate = MutationProbe.create(
        mutant_id=first.mutant_id,
        kind=MutationKind.AUTHORITY_SUBSTITUTION,
        baseline_identity="baseline:authority",
        mutated_identity="mutated:authority",
        killed=True,
        detector="detector:authority",
    )
    with pytest.raises(MutationCampaignError, match="duplicate mutant identity"):
        SemanticMutationCampaign.create(probes=[first, duplicate])


def test_material_mutant_cannot_be_a_no_op() -> None:
    with pytest.raises(MutationCampaignError, match="material mutant is a no-op"):
        probe(MutationKind.ROUTE_ADDITION, changed=False)


def test_no_op_detection_mutant_must_be_a_no_op() -> None:
    with pytest.raises(MutationCampaignError, match="no-op detector mutant changed semantics"):
        probe(MutationKind.NO_OP_DETECTION, changed=True)


def test_detector_identity_is_required_and_canonical() -> None:
    with pytest.raises(MutationCampaignError, match="detector must be canonical"):
        MutationProbe.create(
            mutant_id="mutant:x",
            kind=MutationKind.EVIDENCE_OMISSION,
            baseline_identity="baseline:x",
            mutated_identity="mutated:x",
            killed=True,
            detector=" ",
        )


def test_required_inventory_is_exact_and_stable() -> None:
    assert tuple(kind.value for kind in MutationKind) == (
        "guard_deletion",
        "authority_substitution",
        "route_addition",
        "missing_binding_or_member",
        "recovery_breakage",
        "generation_or_state_mutation",
        "evidence_omission",
        "no_op_detection",
    )
