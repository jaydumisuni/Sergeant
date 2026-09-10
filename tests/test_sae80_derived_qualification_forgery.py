from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from main_review.assurance_contract_registry import ClosureGrade
from main_review.proof_world_authority import (
    EVIDENCE_ARTIFACT_FAMILY,
    EVIDENCE_DOMAIN,
    EVIDENCE_QUALIFICATION_GENERATION,
    ProofWorldAuthorityError,
    bind_evidence_proof_authority,
    validate_evidence_proof_authority,
)
from main_review.qualification_authority import DerivedQualification, QualificationAttestation
from main_review.review_world import sha256_id
from tests.sae80_authority_fixtures import authority_fixture
from tests.test_sae80_authority_hardening import _fixture


def test_public_hash_cannot_forge_sae30_qualification_without_verifier_authentication() -> None:
    registry, qualified_closure, obligation = _fixture()
    authority, _ = authority_fixture(qualified_closure, registry)
    issuer = authority.qualification_registry.issuers[0]
    evidence_basis_id = sha256_id({"sae80-forged-evidence": obligation.obligation_id})
    qualification_lineage_id = sha256_id({"sae80-forged-lineage": obligation.obligation_id})
    authenticated_provenance_id = sha256_id({"sae80-forged-provenance": obligation.obligation_id})
    now = datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc)

    # The attacker can construct the public attestation record, but deliberately
    # has no issuer verification secret, AuthenticatedIssuer MAC, or closure-proof MAC.
    attestation = QualificationAttestation.create(
        subject_id=obligation.obligation_id,
        artifact_family=EVIDENCE_ARTIFACT_FAMILY,
        domain=EVIDENCE_DOMAIN,
        artifact_generation=authority.candidate_generation,
        acr_generation=registry.generation,
        qualification_protocol_generation=EVIDENCE_QUALIFICATION_GENERATION,
        evidence_root_id=evidence_basis_id,
        proof_class="mechanical",
        closure_grade=ClosureGrade.EXACT.value,
        independence_state="INDEPENDENT",
        qualification_lineage_id=qualification_lineage_id,
        authenticated_provenance_id=authenticated_provenance_id,
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        issuer_identity=issuer.issuer_identity,
        issuer_generation=issuer.issuer_generation,
    )

    fake_closure_proof_id = sha256_id({"attacker": "has-no-verifier-mac"})
    body = {
        "schema_version": "sergeant.derived-qualification.v3",
        "subject_id": attestation.subject_id,
        "artifact_family": attestation.artifact_family,
        "domain": attestation.domain,
        "artifact_generation": attestation.artifact_generation,
        "attestation_id": attestation.attestation_id,
        "issuer_authorization_id": issuer.authorization_id,
        "evidence_root_id": attestation.evidence_root_id,
        "independence_state": attestation.independence_state,
        "qualification_lineage_id": attestation.qualification_lineage_id,
        "authenticated_provenance_id": attestation.authenticated_provenance_id,
        "closure_proof_id": fake_closure_proof_id,
        "state": "QUALIFIED",
    }
    forged = DerivedQualification(
        "QUALIFIED",
        attestation.subject_id,
        attestation.artifact_family,
        attestation.domain,
        attestation.artifact_generation,
        attestation.attestation_id,
        issuer.authorization_id,
        attestation.evidence_root_id,
        attestation.independence_state,
        attestation.qualification_lineage_id,
        attestation.authenticated_provenance_id,
        fake_closure_proof_id,
        sha256_id(body),
    )

    with pytest.raises(ProofWorldAuthorityError, match="authentic|admission|closure|qualification"):
        bind_evidence_proof_authority(
            world_authority=authority,
            obligation_id=obligation.obligation_id,
            evidence_basis_id=evidence_basis_id,
            attestation=attestation,
            qualification=forged,
        )


def test_reconstructed_evidence_authority_loses_verifier_admission_capability() -> None:
    from dataclasses import replace
    from tests.sae80_authority_fixtures import authority_fixture, evidence, qualified_fixture

    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    proof_evidence = evidence(obligation, world, authority)
    reconstructed = replace(proof_evidence.proof_authority)

    with pytest.raises(ProofWorldAuthorityError, match="verifier-authentic|admission"):
        validate_evidence_proof_authority(reconstructed, world_authority=authority)
