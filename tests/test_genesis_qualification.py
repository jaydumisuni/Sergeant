from __future__ import annotations

import hashlib
import pytest

from main_review.external_evidence_provenance import (
    AuthenticatedProvenanceProof,
    ControlLineageFacts,
    ExternalEvidenceProvenanceRecord,
    ProvenanceVerifierAuthorization,
    ProvenanceVerifierState,
)
from main_review.genesis_qualification import GenesisQualificationError, qualify_genesis_package


CANONICAL_NODES = {
    "SAE-100": "73541e17e8ef7c208d2bfa91012695b6917e549b",
    "SAE-110": "1ba0fbbafc9423ed9b098137e0669fe941b052d0",
    "SAE-120": "e29ffbcd6aad7336e5827cbb1e6469be398cf730",
    "SAE-130A": "97c2d939df51a21828a6ea96f05458207ac0793c",
    "SAE-130B": "7af19145d13e173a9fe727cd3977c483aa4c8057",
    "SAE-130C": "4b3a59117c6ccfac5d6d6d47f795cb4333566b69",
    "SAE-130D": "948c450e15f71f3823be0df1fedf27650edec067",
    "SAE-130E": "a889f512662e0b1d62a81582025677276967806d",
    "SAE-140": "126eeea5a70a0723a1bfb65b2a5dbeb6a84cf2e0",
    "SPIKE-EXT": "5a42072517efef7c1e621f12a99e9e2cbf610281",
}

BASE = {
    "candidate_generation": "candidate-sha",
    "rab_generation": "rab-sha",
    "acr_generation": "acr-sha",
    "rust_generation": "rust-sha",
    "review_world_id": hashlib.sha256(b"world").hexdigest(),
    "required_proven_nodes": dict(CANONICAL_NODES),
    "preservation_proof": True,
    "model_blackout_proof": True,
    "cpu_proof": True,
    "historical_replay": True,
    "clean_controls": True,
    "mutation_families": {
        key: True
        for key in ("omission", "undercount", "cardinality", "acr", "material_input", "falsifier", "authority", "common_mode")
    },
    "unrelated_transfer": True,
    "eepr_complete": True,
    "residual_unknowns": [],
    "external_evidence": [],
}


def _canonical_eepr(*, independent: bool) -> ExternalEvidenceProvenanceRecord:
    secret = b"0123456789abcdef"
    facts = ControlLineageFacts.create(
        source_separate=True,
        authoring_separate=True if independent else False,
        corpus_separate=True,
        infrastructure_separate=True,
        prompt_control_separate=True,
        input_selection_separate=True,
        finding_selection_separate=True,
    )
    verifier = "external-verifier"
    verifier_generation = "verifier-generation"
    authorization = ProvenanceVerifierAuthorization.create(
        verifier_identity=verifier,
        verifier_generation=verifier_generation,
        key_id=hashlib.sha256(b"key").hexdigest(),
        verification_secret_digest=hashlib.sha256(secret).hexdigest(),
        state=ProvenanceVerifierState.ACTIVE,
    )
    evidence_id = hashlib.sha256(b"evidence").hexdigest()
    proof = AuthenticatedProvenanceProof.issue(
        evidence_id=evidence_id,
        source_principal_id="external-principal",
        source_authority_generation="external-generation",
        lineage_facts=facts,
        verifier_identity=verifier,
        verifier_generation=verifier_generation,
        verification_secret=secret,
    )
    return ExternalEvidenceProvenanceRecord.create(
        evidence_id=evidence_id,
        evidence_digest=hashlib.sha256(b"payload").hexdigest(),
        review_world_id=hashlib.sha256(b"world").hexdigest(),
        source_principal_id="external-principal",
        authenticated_source_provenance="external-attestation",
        source_organization="external-org",
        source_class="independent-human-review",
        source_authority_generation="external-generation",
        creation_generation="external-creation",
        candidate_authoring_relationship="separate",
        qualification_corpus_relationship="separate",
        candidate_infrastructure_relationship="separate",
        reviewer_tool_lineage="independent-tooling",
        prompt_controller="external",
        input_selector="external",
        finding_selector="external",
        provenance_verification_method="hmac",
        control_lineage_facts=facts,
        provenance_authorization=authorization,
        authenticated_provenance_proof=proof,
        provenance_verification_secret=secret,
    )


def test_missing_independent_lane_stays_genesis_provisional():
    out = qualify_genesis_package(BASE)
    assert out["state"] == "GENESIS_PROVISIONAL"
    assert out["qualified"] is False
    assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]
    assert out["authority_gain"] == []


def test_owner_controlled_lineage_cannot_fill_independent_lane():
    row = dict(BASE, external_evidence=[_canonical_eepr(independent=False)])
    out = qualify_genesis_package(row)
    assert out["qualified"] is False
    assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]


def test_authenticated_canonical_independent_lane_can_qualify_when_everything_else_is_closed():
    row = dict(BASE, external_evidence=[_canonical_eepr(independent=True)])
    out = qualify_genesis_package(row)
    assert out["qualified"] is True
    assert out["state"] == "GENESIS_QUALIFICATION_PACKAGE_CANDIDATE"
    assert out["authority_gain"] == []


@pytest.mark.parametrize(
    "field",
    ["preservation_proof", "model_blackout_proof", "cpu_proof", "historical_replay", "clean_controls", "unrelated_transfer", "eepr_complete"],
)
def test_required_proof_families_fail_closed(field):
    row = dict(BASE)
    row[field] = False
    with pytest.raises(GenesisQualificationError):
        qualify_genesis_package(row)


def test_all_required_mutation_families_are_mandatory():
    row = dict(BASE)
    row["mutation_families"] = {"omission": True}
    with pytest.raises(GenesisQualificationError):
        qualify_genesis_package(row)


def test_mandatory_unknown_leaves_genesis_provisional_even_with_external_lane():
    row = dict(
        BASE,
        external_evidence=[_canonical_eepr(independent=True)],
        residual_unknowns=["mandatory: unresolved corpus gap"],
    )
    out = qualify_genesis_package(row)
    assert out["qualified"] is False and out["state"] == "GENESIS_PROVISIONAL"
    assert "MANDATORY_UNKNOWN" in out["blockers"]


def test_required_nodes_reject_noncanonical_generation_values():
    row = dict(BASE)
    row["required_proven_nodes"] = dict(CANONICAL_NODES)
    row["required_proven_nodes"]["SAE-140"] = "wrong"
    with pytest.raises(GenesisQualificationError):
        qualify_genesis_package(row)


@pytest.mark.parametrize(
    "field,bad",
    [
        ("required_proven_nodes", ["not-a-mapping"]),
        ("mutation_families", ["not-a-mapping"]),
        ("external_evidence", ["not-a-record"]),
    ],
)
def test_malformed_nested_shapes_raise_genesis_error(field, bad):
    row = dict(BASE)
    row[field] = bad
    with pytest.raises(GenesisQualificationError):
        qualify_genesis_package(row)


def test_package_booleans_cannot_forge_independent_lane():
    row = dict(BASE)
    row["external_evidence"] = [
        {
            "source_id": "forged",
            "authenticated": True,
            "materially_independent": True,
            "owner_controlled": False,
            "evidence_digest": "sha256:abc",
        }
    ]
    with pytest.raises(GenesisQualificationError):
        qualify_genesis_package(row)


def test_generation_identifiers_must_be_typed_and_bound_into_result():
    row = dict(BASE, candidate_generation=12345)
    with pytest.raises(GenesisQualificationError):
        qualify_genesis_package(row)

    valid = dict(BASE, external_evidence=[_canonical_eepr(independent=True)])
    out = qualify_genesis_package(valid)
    assert out["generation_bindings"] == {
        key: valid[key] for key in ("candidate_generation", "rab_generation", "acr_generation", "rust_generation")
    }
    assert out["generation_bindings_digest"]


def test_external_review_census_is_derived_instead_of_trusting_completion_boolean():
    record = _canonical_eepr(independent=True)
    row = dict(BASE, external_evidence=[record, record])
    with pytest.raises(GenesisQualificationError, match="census"):
        qualify_genesis_package(row)


def test_external_evidence_must_match_exact_review_world():
    row = dict(BASE, external_evidence=[_canonical_eepr(independent=True)])
    row["review_world_id"] = hashlib.sha256(b"different-world").hexdigest()
    out = qualify_genesis_package(row)
    assert out["qualified"] is False
    assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]


def test_spike_ext_prerequisite_is_bound_to_immutable_blob_identity():
    from main_review.genesis_qualification import REQUIRED_PROVEN_NODE_BINDINGS
    assert REQUIRED_PROVEN_NODE_BINDINGS["SPIKE-EXT"] == "5a42072517efef7c1e621f12a99e9e2cbf610281"
