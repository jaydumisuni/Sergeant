from __future__ import annotations

import pytest

from main_review.semantic_mutation import (
    MutationCampaignError,
    MutationKind,
    MutationProbe,
    SemanticMutationCampaign,
)


def make(kind: MutationKind, *, killed: bool = True) -> MutationProbe:
    no_op = kind is MutationKind.NO_OP_DETECTION
    baseline = f"world:{kind.value}:baseline"
    return MutationProbe.create(
        mutant_id=f"required:{kind.value}",
        kind=kind,
        baseline_identity=baseline,
        mutated_identity=baseline if no_op else f"world:{kind.value}:mutated",
        killed=killed,
        detector=f"qualified-detector:{kind.value}",
    )


def test_qualification_inventory_kills_every_required_mutation_family() -> None:
    result = SemanticMutationCampaign.create(
        probes=[make(kind) for kind in MutationKind]
    ).evaluate()
    assert result.qualified
    assert len(result.killed_mutants) == 8
    assert result.surviving_mutants == ()
    assert result.missing_required_kinds == ()


def test_qualification_fails_if_authority_or_recovery_mutant_survives() -> None:
    for survivor in (MutationKind.AUTHORITY_SUBSTITUTION, MutationKind.RECOVERY_BREAKAGE):
        probes = [make(kind, killed=(kind is not survivor)) for kind in MutationKind]
        result = SemanticMutationCampaign.create(probes=probes).evaluate()
        assert not result.qualified
        assert result.surviving_mutants == (f"required:{survivor.value}",)


def test_qualification_fails_if_evidence_or_binding_mutant_is_omitted() -> None:
    for missing in (MutationKind.EVIDENCE_OMISSION, MutationKind.MISSING_BINDING_OR_MEMBER):
        result = SemanticMutationCampaign.create(
            probes=[make(kind) for kind in MutationKind if kind is not missing]
        ).evaluate()
        assert not result.qualified
        assert missing.value in result.missing_required_kinds


def test_qualification_distinguishes_material_mutation_from_no_op_detection() -> None:
    with pytest.raises(MutationCampaignError, match="material mutant is a no-op"):
        MutationProbe.create(
            mutant_id="bad:route",
            kind=MutationKind.ROUTE_ADDITION,
            baseline_identity="world",
            mutated_identity="world",
            killed=True,
            detector="route-detector",
        )
    with pytest.raises(MutationCampaignError, match="no-op detector mutant changed semantics"):
        MutationProbe.create(
            mutant_id="bad:no-op",
            kind=MutationKind.NO_OP_DETECTION,
            baseline_identity="world",
            mutated_identity="different-world",
            killed=True,
            detector="noop-detector",
        )
