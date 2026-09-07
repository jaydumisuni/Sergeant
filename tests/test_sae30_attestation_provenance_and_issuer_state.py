from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from main_review.qualification_authority import (
    AuthenticatedIssuer,
    GenesisActivationRecord,
    GenesisQualificationPackage,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityError,
    QualificationAuthorityRegistry,
    QualificationIssuerAuthorization,
    admit_qualification_attestation,
    evaluate_genesis_exit_gate,
)


ONE = "1" * 64
TWO = "2" * 64
THREE = "3" * 64
FOUR = "4" * 64
FIVE = "5" * 64
SIX = "6" * 64
SEVEN = "7" * 64


def _authorization(state: IssuerState = IssuerState.ACTIVE):
    return QualificationIssuerAuthorization.create(
        issuer_identity="owner-root-qualification",
        key_id=ONE,
        namespace="sergeant-qualification-attestation-v1",
        issuer_generation="issuer-gen-1",
        artifact_families=("acr-foundation",),
        domains=("typescript.express-route.v1",),
        proof_classes=("bounded-hostile-qualification",),
        closure_grades=("EXACT",),
        allowed_independence_states=("INDEPENDENT",),
        control_lineage_id=TWO,
        state=state,
    )


def _attestation(*, independence_state: str = "INDEPENDENT"):
    now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    return QualificationAttestation.create(
        subject_id=THREE,
        artifact_family="acr-foundation",
        domain="typescript.express-route.v1",
        artifact_generation="acr-gen-1",
        acr_generation="registry-gen-1",
        qualification_protocol_generation="sae30-v1",
        evidence_root_id=FOUR,
        proof_class="bounded-hostile-qualification",
        closure_grade="EXACT",
        independence_state=independence_state,
        qualification_lineage_id=FIVE,
        authenticated_provenance_id=SIX,
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        issuer_identity="owner-root-qualification",
        issuer_generation="issuer-gen-1",
    ), now


def _admit(registry, attestation, now):
    return admit_qualification_attestation(
        registry=registry,
        attestation=attestation,
        authenticated_issuer=AuthenticatedIssuer.create(
            issuer_identity="owner-root-qualification",
            key_id=ONE,
            namespace="sergeant-qualification-attestation-v1",
            issuer_generation="issuer-gen-1",
        ),
        subject_id=THREE,
        artifact_family="acr-foundation",
        domain="typescript.express-route.v1",
        artifact_generation="acr-gen-1",
        acr_generation="registry-gen-1",
        qualification_protocol_generation="sae30-v1",
        evidence_root_id=FOUR,
        independence_state="INDEPENDENT",
        qualification_lineage_id=FIVE,
        authenticated_provenance_id=SIX,
        candidate_control_lineage_id=SEVEN,
        now=now,
    )


def test_attestation_binds_independence_lineage_and_authenticated_provenance() -> None:
    authorization = _authorization()
    registry = QualificationAuthorityRegistry.create(generation="qar-gen-1", issuers=(authorization,))
    attestation, now = _attestation()
    qualification, _ = _admit(registry, attestation, now)
    assert qualification.independence_state == "INDEPENDENT"
    assert qualification.qualification_lineage_id == FIVE
    assert qualification.authenticated_provenance_id == SIX


def test_independence_constraint_is_issuer_authorization_not_payload_choice() -> None:
    authorization = _authorization()
    registry = QualificationAuthorityRegistry.create(generation="qar-gen-1", issuers=(authorization,))
    attestation, now = _attestation(independence_state="NOT_INDEPENDENT")
    with pytest.raises(QualificationAuthorityError, match="independence"):
        _admit(registry, attestation, now)


def test_suspended_and_revoked_issuer_generations_fail_closed() -> None:
    attestation, now = _attestation()
    for state in (IssuerState.SUSPENDED, IssuerState.REVOKED):
        registry = QualificationAuthorityRegistry.create(generation="qar-gen-1", issuers=(_authorization(state),))
        with pytest.raises(QualificationAuthorityError, match="suspended or revoked"):
            _admit(registry, attestation, now)


def test_genesis_activation_class_is_one_time_after_future_authorized_exit() -> None:
    package = GenesisQualificationPackage.create(
        review_world_id=ONE,
        required_qualification_ids=(TWO, THREE),
        present_qualification_ids=(TWO, THREE),
        external_review_census_id=FOUR,
        external_review_census_satisfied=True,
        founding_final_proof_id=FIVE,
        generation="genesis-gen-1",
    )
    gate = evaluate_genesis_exit_gate(package=package, authority_node="SAE-170")
    assert gate.authorized is True
    record = GenesisActivationRecord.create(
        package=package,
        exit_gate=gate,
        activation_class="founding-generation",
        consumed_activation_classes=(),
    )
    assert record.activation_class == "founding-generation"
    with pytest.raises(QualificationAuthorityError, match="already been consumed"):
        GenesisActivationRecord.create(
            package=package,
            exit_gate=gate,
            activation_class="founding-generation",
            consumed_activation_classes=("founding-generation",),
        )
