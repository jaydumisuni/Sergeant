from __future__ import annotations

import pytest

from main_review.facility_gradient import (
    Availability,
    FacilityContract,
    FacilityError,
    FacilityKind,
    FacilityRequirement,
    evaluate_facility_requirement,
)


def h(ch: str) -> str:
    return ch * 64


def contract(kind: FacilityKind, *, writes: bool = False, approved: bool = False, capabilities=("repository_read",)) -> FacilityContract:
    return FacilityContract.create(
        kind=kind,
        facility_generation=f"{kind.value}-g1",
        acr_authority_id=h("a"), judge_authority_id=h("b"), rust_authority_id=h("c"), pass_law_id=h("d"),
        capabilities=capabilities,
        writes_enabled=writes,
        owner_write_approved=approved,
    )


def test_github_is_read_only_and_cannot_claim_owner_write_approval():
    value = contract(FacilityKind.GITHUB)
    assert value.writes_enabled is False
    with pytest.raises(FacilityError, match="GitHub.*read-only"):
        contract(FacilityKind.GITHUB, writes=True, approved=True)


def test_local_write_requires_explicit_owner_approval():
    with pytest.raises(FacilityError, match="owner approval"):
        contract(FacilityKind.LOCAL, writes=True, approved=False)
    local = contract(FacilityKind.LOCAL, writes=True, approved=True, capabilities=("repository_read", "runtime_tests"))
    assert local.writes_enabled is True
    assert local.owner_write_approved is True


def test_all_facilities_must_bind_one_assurance_law():
    github = contract(FacilityKind.GITHUB)
    local = contract(FacilityKind.LOCAL)
    assert github.law_identity == local.law_identity
    with pytest.raises(FacilityError, match="assurance law"):
        FacilityContract.require_same_law((github, local.with_pass_law(h("9"))))


def test_missing_required_facility_or_capability_is_unknown_never_weaker_pass():
    github = contract(FacilityKind.GITHUB)
    requirement = FacilityRequirement.create(kind=FacilityKind.GITHUB, capability="symbols")
    result = evaluate_facility_requirement(requirement, (github,))
    assert result.availability is Availability.UNKNOWN
    assert result.can_support_pass is False

    local_only = contract(FacilityKind.LOCAL, capabilities=("symbols",))
    missing_github = evaluate_facility_requirement(requirement, (local_only,))
    assert missing_github.availability is Availability.UNKNOWN
    assert missing_github.can_support_pass is False


def test_richer_local_evidence_cannot_change_verdict_semantics():
    github = contract(FacilityKind.GITHUB, capabilities=("repository_read",))
    local = contract(FacilityKind.LOCAL, capabilities=("formal_tools", "repository_read", "runtime_tests", "symbols"))
    FacilityContract.require_same_law((github, local))
    assert local.pass_law_id == github.pass_law_id
    assert set(local.capabilities) > set(github.capabilities)
    assert local.verdict_semantics_authority_gain is False
