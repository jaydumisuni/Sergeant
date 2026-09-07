from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib

import pytest

from main_review.external_evidence_provenance import (
    AuthenticatedProvenanceProof,
    ControlLineageFacts,
    ExternalEvidenceProvenanceRecord,
    ExternalReviewLaneRequirement,
    IndependenceState,
    ProvenanceVerifierAuthorization,
    ProvenanceVerifierState,
    evaluate_external_review_census,
)
from main_review.owner_risk import (
    BusinessRiskDecision,
    BusinessRiskDecisionRecord,
    EngineeringVerdict,
    EngineeringVerdictRecord,
    OwnerRiskError,
)
from main_review.qualification_authority import (
    AuthenticatedIssuer,
    GenesisQualificationPackage,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityError,
    QualificationAuthorityRegistry,
    QualificationClosureProof,
    QualificationIssuerAuthorization,
    admit_qualification_attestation,
    evaluate_genesis_exit_gate,
    qualification_verification_secret_digest,
)


ZERO = "0" * 64
ONE = "1" * 64
TWO = "2" * 64
THREE = "3" * 64
FOUR = "4" * 64
FIVE = "5" * 64
SIX = "6" * 64
SEVEN = "7" * 64
EIGHT = "8" * 64
NINE = "9" * 64
ISSUER_SECRET = b"sae30-closeout-issuer-secret-2026"
PROVENANCE_SECRET = b"sae30-closeout-provenance-secret"


def _qualified_fixture():
    authorization = QualificationIssuerAuthorization.create(
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
        authentication_secret_digest=qualification_verification_secret_digest(ISSUER_SECRET),
        state=IssuerState.ACTIVE,
    )
    registry = QualificationAuthorityRegistry.create(generation="qar-gen-1", issuers=(authorization,))
    now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    attestation = QualificationAttestation.create(
        subject_id=THREE,
        artifact_family="acr-foundation",
        domain="typescript.express-route.v1",
        artifact_generation="acr-gen-1",
        acr_generation="registry-gen-1",
        qualification_protocol_generation="sae30-v1",
        evidence_root_id=FOUR,
        proof_class="bounded-hostile-qualification",
        closure_grade="EXACT",
        independence_state="INDEPENDENT",
        qualification_lineage_id=FIVE,
        authenticated_provenance_id=SIX,
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        issuer_identity="owner-root-qualification",
        issuer_generation="issuer-gen-1",
    )
    authenticated = AuthenticatedIssuer.issue_verifier_proof(
        issuer_identity="owner-root-qualification",
        key_id=ONE,
        namespace="sergeant-qualification-attestation-v1",
        issuer_generation="issuer-gen-1",
        registry_generation="qar-gen-1",
        attestation_id=attestation.attestation_id,
        verification_secret=ISSUER_SECRET,
    )
    closure = QualificationClosureProof.issue_verifier_proof(
        attestation_id=attestation.attestation_id,
        evidence_root_id=FOUR,
        judge_admission_id=ONE,
        qualification_protocol_closure_id=TWO,
        evidence_closure_id=THREE,
        external_review_census_id=EIGHT,
        independence_proof_id=NINE,
        judge_admitted=True,
        qualification_protocol_closed=True,
        evidence_closed=True,
        external_lanes_closed=True,
        independence_verified=True,
        verification_secret=ISSUER_SECRET,
    )
    expected = dict(
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
        expected_registry_generation="qar-gen-1",
        now=now,
    )
    return registry, attestation, authenticated, closure, expected


def _admit(registry, attestation, authenticated, closure, expected, **overrides):
    return admit_qualification_attestation(
        registry=registry,
        attestation=attestation,
        authenticated_issuer=authenticated,
        closure_proof=closure,
        issuer_verification_secret=ISSUER_SECRET,
        **{**expected, **overrides},
    )


def test_qualification_campaign_rejects_generation_domain_replay_and_open_closure() -> None:
    registry, attestation, authenticated, closure, expected = _qualified_fixture()
    qualification, consumed = _admit(registry, attestation, authenticated, closure, expected)
    assert qualification.state == "QUALIFIED"

    with pytest.raises(QualificationAuthorityError, match="replay"):
        _admit(consumed, attestation, authenticated, closure, expected)
    with pytest.raises(QualificationAuthorityError):
        _admit(registry, attestation, authenticated, closure, expected, domain="python.call.v1")
    with pytest.raises(QualificationAuthorityError, match="registry generation"):
        _admit(registry, attestation, authenticated, closure, expected, expected_registry_generation="qar-gen-2")

    open_closure = QualificationClosureProof.issue_verifier_proof(
        attestation_id=attestation.attestation_id,
        evidence_root_id=FOUR,
        judge_admission_id=ONE,
        qualification_protocol_closure_id=TWO,
        evidence_closure_id=THREE,
        external_review_census_id=EIGHT,
        independence_proof_id=NINE,
        judge_admitted=True,
        qualification_protocol_closed=True,
        evidence_closed=True,
        external_lanes_closed=False,
        independence_verified=True,
        verification_secret=ISSUER_SECRET,
    )
    with pytest.raises(QualificationAuthorityError, match="closure is incomplete"):
        _admit(registry, attestation, authenticated, open_closure, expected)


def _external_record(*, evidence_id: str, source_class: str, facts: ControlLineageFacts, authenticated: bool):
    authorization = ProvenanceVerifierAuthorization.create(
        verifier_identity="external-platform-verifier",
        verifier_generation="pv-gen-1",
        key_id=SEVEN,
        verification_secret_digest=hashlib.sha256(PROVENANCE_SECRET).hexdigest(),
        state=ProvenanceVerifierState.ACTIVE,
    )
    principal = f"reviewer-{source_class}-{evidence_id[0]}"
    proof = None
    secret = None
    if authenticated:
        proof = AuthenticatedProvenanceProof.issue(
            evidence_id=evidence_id,
            source_principal_id=principal,
            source_authority_generation="source-gen-1",
            lineage_facts=facts,
            verifier_identity=authorization.verifier_identity,
            verifier_generation=authorization.verifier_generation,
            verification_secret=PROVENANCE_SECRET,
        )
        secret = PROVENANCE_SECRET
    return ExternalEvidenceProvenanceRecord.create(
        evidence_id=evidence_id,
        evidence_digest=evidence_id,
        review_world_id=ZERO,
        source_principal_id=principal,
        authenticated_source_provenance="signed-platform-submission",
        source_organization=f"org-{source_class}",
        source_class=source_class,
        source_authority_generation="source-gen-1",
        creation_generation="2026-09-07T10:00:00Z",
        candidate_authoring_relationship="separate",
        qualification_corpus_relationship="separate",
        candidate_infrastructure_relationship="separate",
        reviewer_tool_lineage="human-reviewer",
        prompt_controller="source-principal",
        input_selector="source-principal",
        finding_selector="source-principal",
        provenance_verification_method="platform-hmac-verifier",
        control_lineage_facts=facts,
        provenance_authorization=authorization,
        authenticated_provenance_proof=proof,
        provenance_verification_secret=secret,
    )


def test_external_campaign_preserves_unknown_and_excludes_ineligible_records() -> None:
    independent = ControlLineageFacts.create(
        source_separate=True,
        authoring_separate=True,
        corpus_separate=True,
        infrastructure_separate=True,
        prompt_control_separate=True,
        input_selection_separate=True,
        finding_selection_separate=True,
    )
    dependent = ControlLineageFacts.create(
        **{**independent.to_payload(), "prompt_control_separate": False}
    )
    unknown = _external_record(evidence_id=FOUR, source_class="unknown", facts=independent, authenticated=False)
    assert unknown.independence_state is IndependenceState.UNKNOWN_INDEPENDENCE

    records = (
        _external_record(evidence_id=ONE, source_class="contractor", facts=independent, authenticated=True),
        _external_record(evidence_id=TWO, source_class="academic", facts=independent, authenticated=True),
        _external_record(evidence_id=THREE, source_class="candidate", facts=dependent, authenticated=True),
        unknown,
    )
    requirement = ExternalReviewLaneRequirement.create(
        lane_id="genesis-hostile", minimum_instances=2, minimum_source_classes=2
    )
    census = evaluate_external_review_census(records=records, requirements=(requirement,))
    assert census.satisfied is True
    assert census.eligible_independent_evidence_ids == (ONE, TWO)
    assert census.lanes[0].source_classes == ("academic", "contractor")


def test_genesis_campaign_keeps_sae170_as_the_only_exit_authority() -> None:
    complete = GenesisQualificationPackage.create(
        review_world_id=ONE,
        required_qualification_ids=(TWO, THREE),
        present_qualification_ids=(TWO, THREE),
        external_review_census_id=FOUR,
        external_review_census_satisfied=True,
        founding_final_proof_id=FIVE,
        generation="genesis-gen-1",
    )
    assert evaluate_genesis_exit_gate(package=complete, authority_node="SAE-30").authorized is False
    assert evaluate_genesis_exit_gate(package=complete, authority_node="SAE-170").authorized is True

    incomplete = GenesisQualificationPackage.create(
        review_world_id=ONE,
        required_qualification_ids=(TWO, THREE),
        present_qualification_ids=(TWO,),
        external_review_census_id=FOUR,
        external_review_census_satisfied=True,
        founding_final_proof_id=FIVE,
        generation="genesis-gen-1",
    )
    assert evaluate_genesis_exit_gate(package=incomplete, authority_node="SAE-170").authorized is False


def test_owner_risk_campaign_cannot_launder_business_acceptance_into_engineering_pass() -> None:
    engineering = EngineeringVerdictRecord.create(
        review_world_id=ZERO,
        evidence_root_id=ONE,
        sergeant_authority_id=TWO,
        verdict=EngineeringVerdict.NEEDS_WORK,
    )
    risk = BusinessRiskDecisionRecord.create(
        engineering_verdict_id=engineering.record_id,
        owner_authority_id=THREE,
        decision=BusinessRiskDecision.ACCEPT,
        rationale="Owner accepts commercial timing risk without changing engineering truth.",
    )
    assert risk.decision.value == "SHIP_WITH_ACCEPTED_RISK"
    assert engineering.verdict is EngineeringVerdict.NEEDS_WORK
    with pytest.raises(OwnerRiskError, match="engineering verdict"):
        EngineeringVerdictRecord.create(
            review_world_id=ZERO,
            evidence_root_id=ONE,
            sergeant_authority_id=TWO,
            verdict=BusinessRiskDecision.ACCEPT,  # type: ignore[arg-type]
        )
