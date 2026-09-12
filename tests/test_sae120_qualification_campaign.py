from __future__ import annotations

import json
from pathlib import Path
import pytest

from main_review.facility_gradient import FacilityContract, FacilityError, FacilityKind, FacilityRequirement, Availability, evaluate_facility_requirement

ROOT = Path(__file__).resolve().parents[1]


def h(ch: str) -> str:
    return ch * 64


def make(kind: FacilityKind, caps=("repository_read",), *, writes=False, approved=False):
    return FacilityContract.create(kind=kind, facility_generation=f"{kind.value}-g1",
        acr_authority_id=h("a"), judge_authority_id=h("b"), rust_authority_id=h("c"), pass_law_id=h("d"),
        capabilities=caps, writes_enabled=writes, owner_write_approved=approved)


def test_required_candidate_inventory_and_law_manifest_are_present():
    manifest = json.loads((ROOT / "docs/133-sae120-facility-gradient-candidate-manifest.json").read_text())
    for rel in manifest["required_surfaces"]:
        assert (ROOT / rel).is_file(), rel
    assert manifest["law"]["same_acr_judge_rust_pass_law_across_facilities"] is True
    assert manifest["law"]["missing_required_facility_yields_unknown_not_weaker_pass"] is True


def test_github_is_read_only_and_local_write_is_owner_gated():
    with pytest.raises(FacilityError):
        make(FacilityKind.GITHUB, writes=True, approved=True)
    with pytest.raises(FacilityError):
        make(FacilityKind.LOCAL, writes=True, approved=False)
    assert make(FacilityKind.LOCAL, writes=True, approved=True).owner_write_approved is True


def test_richer_local_facility_cannot_change_assurance_law():
    github = make(FacilityKind.GITHUB)
    local = make(FacilityKind.LOCAL, caps=("formal_tools", "repository_read", "runtime_tests", "symbols"))
    assert FacilityContract.require_same_law((github, local)) == github.law_identity
    assert local.verdict_semantics_authority_gain is False


def test_missing_required_facility_or_capability_is_unknown_not_pass():
    github = make(FacilityKind.GITHUB)
    result = evaluate_facility_requirement(FacilityRequirement.create(kind=FacilityKind.GITHUB, capability="symbols"), (github,))
    assert result.availability is Availability.UNKNOWN
    assert result.can_support_pass is False
