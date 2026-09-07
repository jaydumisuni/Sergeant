from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util

import pytest


ZERO = "0" * 64
ONE = "1" * 64
TWO = "2" * 64
THREE = "3" * 64
FOUR = "4" * 64
FIVE = "5" * 64
SIX = "6" * 64


def _load_contract():
    assert importlib.util.find_spec("main_review.qualification_authority") is not None, "SAE-30 qualification authority substrate is missing"
    assert importlib.util.find_spec("main_review.external_evidence_provenance") is not None, "SAE-30 EEPR substrate is missing"
    assert importlib.util.find_spec("main_review.owner_risk") is not None, "SAE-30 owner-risk substrate is missing"
    from main_review.external_evidence_provenance import (
        ControlLineageFacts,
        ExternalEvidenceProvenanceRecord,
        ExternalReviewLaneRequirement,
        IndependenceState,
        evaluate_external_review_census,
    )
    from main_review.owner_risk import (
        BusinessRiskDecision,
        BusinessRiskDecisionRecord,
        EngineeringVerdict,
        EngineeringVerdictRecord,
    )
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
    return locals()


def _qualification_fixture(contract):
    q = contract
    authorization = q["QualificationIssuerAuthorization"].create(
        issuer_identity="owner-root-qualification",
        key_id=ONE,
        namespace="sergeant-qualification-attestation-v1",
        issuer_generation="issuer-gen-1",
        artifact_families=("acr-foundation",),
        domains=("typescript.express-route.v1",),
        proof_classes=("bounded-hostile-qualification",),
        closure_grades=("EXACT",),
        control_lineage_id=TWO,
        state=q["IssuerState"].ACTIVE,
    )
    registry = q["QualificationAuthorityRegistry"].create(
        generation="qar-gen-1",
        issuers=(authorization,),
    )
    authenticated = q["AuthenticatedIssuer"].create(
        issuer_identity="owner-root-qualification",
        key_id=ONE,
        namespace="sergeant-qualification-attestation-v1",
        issuer_generation="issuer-gen-1",
    )
    now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    attestation = q["QualificationAttestation"].create(
        subject_id=THREE,
        artifact_family="acr-foundation",
        domain="typescript.express-route.v1",
        artifact_generation="acr-gen-1",
        acr_generation="registry-gen-1",
        qualification_protocol_generation="sae30-v1",
        evidence_root_id=FOUR,
        proof_class="bounded-hostile-qualification",
        closure_grade="EXACT",
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        issuer_identity="owner-root-qualification",
        issuer_generation="issuer-gen-1",
    )
    expected = dict(
        subject_id=THREE,
        artifact_family="acr-foundation",
        domain="typescript.express-route.v1",
        artifact_generation="acr-gen-1",
        acr_generation="registry-gen-1",
        qualification_protocol_generation="sae30-v1",
        evidence_root_id=FOUR,
        candidate_control_lineage_id=FIVE,
        now=now,
    )
    return registry, authenticated, attestation, expected


def test_qualification_is_derived_only_from_trusted_registry_and_authenticated_issuer() -> None:
    q = _load_contract()
    registry, authenticated, attestation, expected = _qualification_fixture(q)
    qualification, consumed = q["admit_qualification_attestation"](
        registry=registry,
        attestation=attestation,
        authenticated_issuer=authenticated,
        **expected,
    )
    assert qualification.state == "QUALIFIED"
    assert qualification.attestation_id == attestation.attestation_id
    assert qualification.issuer_authorization_id in consumed.authority_ids
    assert attestation.attestation_id in consumed.consumed_attestation_ids


def test_payload_cannot_spoof_issuer_identity_or_generation() -> None:
    q = _load_contract()
    registry, authenticated, attestation, expected = _qualification_fixture(q)
    for field, value in (("issuer_identity", "candidate"), ("issuer_generation", "issuer-gen-2")):
        forged = q["QualificationAttestation"].create(**{
            **attestation.constructor_fields(),
            field: value,
        })
        with pytest.raises(q["QualificationAuthorityError"]):
            q["admit_qualification_attestation"](
                registry=registry,
                attestation=forged,
                authenticated_issuer=authenticated,
                **expected,
            )


def test_replay_future_issue_exact_expiry_and_revocation_fail_closed() -> None:
    q = _load_contract()
    registry, authenticated, attestation, expected = _qualification_fixture(q)
    _, consumed = q["admit_qualification_attestation"](
        registry=registry, attestation=attestation, authenticated_issuer=authenticated, **expected
    )
    with pytest.raises(q["QualificationAuthorityError"], match="replay"):
        q["admit_qualification_attestation"](
            registry=consumed, attestation=attestation, authenticated_issuer=authenticated, **expected
        )
    for issued_at, expires_at in (
        (expected["now"] + timedelta(seconds=1), expected["now"] + timedelta(hours=1)),
        (expected["now"] - timedelta(hours=1), expected["now"]),
    ):
        temporal = q["QualificationAttestation"].create(**{
            **attestation.constructor_fields(), "issued_at": issued_at, "expires_at": expires_at,
        })
        with pytest.raises(q["QualificationAuthorityError"]):
            q["admit_qualification_attestation"](
                registry=registry, attestation=temporal, authenticated_issuer=authenticated, **expected
            )
    revoked = registry.with_revoked_attestation_ids((attestation.attestation_id,))
    with pytest.raises(q["QualificationAuthorityError"], match="revoked"):
        q["admit_qualification_attestation"](
            registry=revoked, attestation=attestation, authenticated_issuer=authenticated, **expected
        )


def test_wrong_subject_domain_generations_evidence_or_ceiling_cannot_qualify() -> None:
    q = _load_contract()
    registry, authenticated, attestation, expected = _qualification_fixture(q)
    mutations = {
        "subject_id": SIX,
        "domain": "python.call.v1",
        "artifact_generation": "acr-gen-2",
        "acr_generation": "registry-gen-2",
        "qualification_protocol_generation": "sae30-v2",
        "evidence_root_id": SIX,
        "proof_class": "heuristic",
        "closure_grade": "PARTIAL",
    }
    for field, value in mutations.items():
        if field in {"proof_class", "closure_grade"}:
            bad_attestation = q["QualificationAttestation"].create(**{**attestation.constructor_fields(), field: value})
            bad_expected = expected
        else:
            bad_attestation = attestation
            bad_expected = {**expected, field: value}
        with pytest.raises(q["QualificationAuthorityError"]):
            q["admit_qualification_attestation"](
                registry=registry,
                attestation=bad_attestation,
                authenticated_issuer=authenticated,
                **bad_expected,
            )


def test_candidate_control_lineage_cannot_be_qualification_issuer_lineage() -> None:
    q = _load_contract()
    registry, authenticated, attestation, expected = _qualification_fixture(q)
    with pytest.raises(q["QualificationAuthorityError"], match="candidate-controlled"):
        q["admit_qualification_attestation"](
            registry=registry,
            attestation=attestation,
            authenticated_issuer=authenticated,
            **{**expected, "candidate_control_lineage_id": TWO},
        )


def _eepr(q, *, evidence_id: str, source_class: str, facts):
    return q["ExternalEvidenceProvenanceRecord"].create(
        evidence_id=evidence_id,
        evidence_digest=evidence_id,
        review_world_id=ZERO,
        source_principal_id=f"reviewer-{source_class}-{evidence_id[0]}",
        authenticated_source_provenance="signed-platform-submission",
        source_organization=f"org-{source_class}-{evidence_id[0]}",
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
        provenance_verification_method="platform-signature+sha256",
        control_lineage_facts=facts,
    )


def test_eepr_independence_is_derived_from_control_lineage_not_self_declared() -> None:
    q = _load_contract()
    independent = q["ControlLineageFacts"].create(
        source_separate=True, authoring_separate=True, corpus_separate=True,
        infrastructure_separate=True, prompt_control_separate=True,
        input_selection_separate=True, finding_selection_separate=True,
    )
    dependent = q["ControlLineageFacts"].create(**{
        **independent.to_payload(), "prompt_control_separate": False,
    })
    unknown = q["ControlLineageFacts"].create(**{
        **independent.to_payload(), "finding_selection_separate": None,
    })
    assert _eepr(q, evidence_id=ONE, source_class="contractor", facts=independent).independence_state is q["IndependenceState"].INDEPENDENT
    assert _eepr(q, evidence_id=TWO, source_class="contractor", facts=dependent).independence_state is q["IndependenceState"].NOT_INDEPENDENT
    assert _eepr(q, evidence_id=THREE, source_class="contractor", facts=unknown).independence_state is q["IndependenceState"].UNKNOWN_INDEPENDENCE


def test_external_review_census_counts_only_independent_records_and_source_classes() -> None:
    q = _load_contract()
    facts = q["ControlLineageFacts"].create(
        source_separate=True, authoring_separate=True, corpus_separate=True,
        infrastructure_separate=True, prompt_control_separate=True,
        input_selection_separate=True, finding_selection_separate=True,
    )
    records = (
        _eepr(q, evidence_id=ONE, source_class="contractor", facts=facts),
        _eepr(q, evidence_id=TWO, source_class="academic", facts=facts),
    )
    requirement = q["ExternalReviewLaneRequirement"].create(
        lane_id="genesis-hostile", minimum_instances=2, minimum_source_classes=2
    )
    census = q["evaluate_external_review_census"](records=records, requirements=(requirement,))
    assert census.satisfied is True
    assert census.lanes[0].independent_instances == 2
    assert census.lanes[0].source_classes == ("academic", "contractor")


def test_owner_business_risk_is_structurally_disjoint_from_engineering_truth() -> None:
    q = _load_contract()
    engineering = q["EngineeringVerdictRecord"].create(
        review_world_id=ZERO,
        evidence_root_id=ONE,
        sergeant_authority_id=TWO,
        verdict=q["EngineeringVerdict"].NEEDS_WORK,
    )
    risk = q["BusinessRiskDecisionRecord"].create(
        engineering_verdict_id=engineering.record_id,
        owner_authority_id=THREE,
        decision=q["BusinessRiskDecision"].ACCEPT,
        rationale="ship for business reasons without rewriting engineering truth",
    )
    assert engineering.verdict is q["EngineeringVerdict"].NEEDS_WORK
    assert risk.engineering_verdict_id == engineering.record_id
    assert not hasattr(risk, "evidence_root_id")
    assert not hasattr(risk, "qualification_id")
    assert not hasattr(risk, "verdict")


def test_genesis_remains_provisional_and_cannot_activate_before_sae170() -> None:
    q = _load_contract()
    package = q["GenesisQualificationPackage"].create(
        review_world_id=ZERO,
        required_qualification_ids=(ONE, TWO),
        present_qualification_ids=(ONE,),
        external_review_census_id=THREE,
        external_review_census_satisfied=False,
        founding_final_proof_id=None,
        generation="genesis-gen-1",
    )
    assert package.state == "GENESIS_PROVISIONAL"
    gate = q["evaluate_genesis_exit_gate"](package=package, authority_node="SAE-30")
    assert gate.authorized is False
    with pytest.raises(q["QualificationAuthorityError"]):
        q["GenesisActivationRecord"].create(
            package=package,
            exit_gate=gate,
            activation_class="founding-generation",
            consumed_activation_classes=(),
        )
