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
SEVEN = "7" * 64
EIGHT = "8" * 64
NINE = "9" * 64
QUALIFICATION_SECRET = b"sae30-qualification-verifier-secret-2026"
PROVENANCE_SECRET = b"sae30-provenance-verifier-secret-2026"


def _load_contract():
    assert importlib.util.find_spec("main_review.qualification_authority") is not None
    assert importlib.util.find_spec("main_review.external_evidence_provenance") is not None
    assert importlib.util.find_spec("main_review.owner_risk") is not None
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
    )
    from main_review.qualification_authority import (
        AuthenticatedIssuer,
        GenesisActivationRecord,
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
    return locals()


def _qualification_fixture(q, *, issuer_state=None):
    issuer_state = issuer_state or q["IssuerState"].ACTIVE
    authorization = q["QualificationIssuerAuthorization"].create(
        issuer_identity="owner-root-qualification", key_id=ONE,
        namespace="sergeant-qualification-attestation-v1", issuer_generation="issuer-gen-1",
        artifact_families=("acr-foundation",), domains=("typescript.express-route.v1",),
        proof_classes=("bounded-hostile-qualification",), closure_grades=("EXACT",),
        allowed_independence_states=("INDEPENDENT",), control_lineage_id=TWO,
        authentication_secret_digest=q["qualification_verification_secret_digest"](QUALIFICATION_SECRET),
        state=issuer_state,
    )
    registry = q["QualificationAuthorityRegistry"].create(generation="qar-gen-1", issuers=(authorization,))
    now = datetime(2026, 9, 7, 10, 0, tzinfo=timezone.utc)
    attestation = q["QualificationAttestation"].create(
        subject_id=THREE, artifact_family="acr-foundation", domain="typescript.express-route.v1",
        artifact_generation="acr-gen-1", acr_generation="registry-gen-1",
        qualification_protocol_generation="sae30-v1", evidence_root_id=FOUR,
        proof_class="bounded-hostile-qualification", closure_grade="EXACT",
        independence_state="INDEPENDENT", qualification_lineage_id=SIX,
        authenticated_provenance_id=ZERO, issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1), issuer_identity="owner-root-qualification",
        issuer_generation="issuer-gen-1",
    )
    expected = dict(
        subject_id=THREE, artifact_family="acr-foundation", domain="typescript.express-route.v1",
        artifact_generation="acr-gen-1", acr_generation="registry-gen-1",
        qualification_protocol_generation="sae30-v1", evidence_root_id=FOUR,
        independence_state="INDEPENDENT", qualification_lineage_id=SIX,
        authenticated_provenance_id=ZERO, candidate_control_lineage_id=FIVE,
        expected_registry_generation="qar-gen-1", now=now,
    )
    return registry, attestation, expected


def _authenticated_issuer(q, attestation, *, secret=QUALIFICATION_SECRET, registry_generation="qar-gen-1"):
    return q["AuthenticatedIssuer"].issue_verifier_proof(
        issuer_identity="owner-root-qualification", key_id=ONE,
        namespace="sergeant-qualification-attestation-v1", issuer_generation="issuer-gen-1",
        registry_generation=registry_generation, attestation_id=attestation.attestation_id,
        verification_secret=secret,
    )


def _closure(q, attestation, *, secret=QUALIFICATION_SECRET, **flags):
    states = dict(judge_admitted=True, qualification_protocol_closed=True, evidence_closed=True,
                  external_lanes_closed=True, independence_verified=True)
    states.update(flags)
    return q["QualificationClosureProof"].issue_verifier_proof(
        attestation_id=attestation.attestation_id, evidence_root_id=attestation.evidence_root_id,
        judge_admission_id=ONE, qualification_protocol_closure_id=TWO, evidence_closure_id=THREE,
        external_review_census_id=EIGHT, independence_proof_id=NINE,
        verification_secret=secret, **states,
    )


def _admit(q, registry, attestation, expected, *, authenticated=None, closure=None, secret=QUALIFICATION_SECRET, **overrides):
    args = {**expected, **overrides}
    return q["admit_qualification_attestation"](
        registry=registry, attestation=attestation,
        authenticated_issuer=authenticated or _authenticated_issuer(q, attestation, secret=secret),
        closure_proof=closure or _closure(q, attestation, secret=secret),
        issuer_verification_secret=secret, **args,
    )


def test_qualification_is_derived_only_from_trusted_registry_verifier_and_closed_proof() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    qualification, consumed = _admit(q, registry, attestation, expected)
    assert qualification.state == "QUALIFIED"
    assert qualification.attestation_id == attestation.attestation_id
    assert qualification.issuer_authorization_id in consumed.authority_ids
    assert attestation.attestation_id in consumed.consumed_attestation_ids
    assert qualification.closure_proof_id == _closure(q, attestation).proof_id


def test_copyable_issuer_fields_without_verifier_mac_cannot_authenticate() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    forged = q["AuthenticatedIssuer"](
        "sergeant.authenticated-issuer.v2", "owner-root-qualification", ONE,
        "sergeant-qualification-attestation-v1", "issuer-gen-1", "qar-gen-1",
        attestation.attestation_id, ZERO,
    )
    with pytest.raises(q["QualificationAuthorityError"], match="verifier-authentic"):
        _admit(q, registry, attestation, expected, authenticated=forged)


def test_wrong_verifier_secret_cannot_authenticate_issuer_or_proof() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    wrong = b"different-verifier-secret-material-2026"
    forged_auth = _authenticated_issuer(q, attestation, secret=wrong)
    forged_closure = _closure(q, attestation, secret=wrong)
    with pytest.raises(q["QualificationAuthorityError"], match="not trusted"):
        _admit(q, registry, attestation, expected, authenticated=forged_auth, closure=forged_closure, secret=wrong)


def test_judge_protocol_evidence_external_and_independence_closure_are_all_mandatory() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    for field in ("judge_admitted", "qualification_protocol_closed", "evidence_closed", "external_lanes_closed", "independence_verified"):
        closure = _closure(q, attestation, **{field: False})
        with pytest.raises(q["QualificationAuthorityError"], match="closure is incomplete"):
            _admit(q, registry, attestation, expected, closure=closure)


def test_payload_cannot_spoof_issuer_identity_or_generation() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    for field, value in (("issuer_identity", "candidate"), ("issuer_generation", "issuer-gen-2")):
        forged = q["QualificationAttestation"].create(**{**attestation.constructor_fields(), field: value})
        with pytest.raises(q["QualificationAuthorityError"]):
            _admit(q, registry, forged, expected)


def test_replay_future_issue_exact_expiry_revocation_and_registry_currentness_fail_closed() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    _, consumed = _admit(q, registry, attestation, expected)
    with pytest.raises(q["QualificationAuthorityError"], match="replay"):
        _admit(q, consumed, attestation, expected)
    for issued_at, expires_at in (
        (expected["now"] + timedelta(seconds=1), expected["now"] + timedelta(hours=1)),
        (expected["now"] - timedelta(hours=1), expected["now"]),
    ):
        temporal = q["QualificationAttestation"].create(**{**attestation.constructor_fields(), "issued_at": issued_at, "expires_at": expires_at})
        with pytest.raises(q["QualificationAuthorityError"]):
            _admit(q, registry, temporal, expected)
    revoked = registry.with_revoked_attestation_ids((attestation.attestation_id,))
    with pytest.raises(q["QualificationAuthorityError"], match="revoked"):
        _admit(q, revoked, attestation, expected)
    with pytest.raises(q["QualificationAuthorityError"], match="registry generation"):
        _admit(q, registry, attestation, expected, expected_registry_generation="qar-gen-2")


def test_wrong_subject_domain_generations_evidence_or_ceiling_cannot_qualify() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    mutations = {
        "subject_id": SEVEN, "domain": "python.call.v1", "artifact_generation": "acr-gen-2",
        "acr_generation": "registry-gen-2", "qualification_protocol_generation": "sae30-v2",
        "evidence_root_id": SEVEN, "independence_state": "NOT_INDEPENDENT",
        "qualification_lineage_id": SEVEN, "authenticated_provenance_id": SEVEN,
        "proof_class": "heuristic", "closure_grade": "PARTIAL",
    }
    for field, value in mutations.items():
        if field in {"proof_class", "closure_grade"}:
            bad_attestation = q["QualificationAttestation"].create(**{**attestation.constructor_fields(), field: value})
            bad_expected = expected
        else:
            bad_attestation = attestation
            bad_expected = {**expected, field: value}
        with pytest.raises(q["QualificationAuthorityError"]):
            _admit(q, registry, bad_attestation, bad_expected)


def test_candidate_control_lineage_cannot_be_qualification_issuer_lineage() -> None:
    q = _load_contract()
    registry, attestation, expected = _qualification_fixture(q)
    with pytest.raises(q["QualificationAuthorityError"], match="candidate-controlled"):
        _admit(q, registry, attestation, expected, candidate_control_lineage_id=TWO)


def _provenance_auth(q):
    return q["ProvenanceVerifierAuthorization"].create(
        verifier_identity="external-platform-verifier", verifier_generation="pv-gen-1", key_id=SEVEN,
        verification_secret_digest=__import__("hashlib").sha256(PROVENANCE_SECRET).hexdigest(),
        state=q["ProvenanceVerifierState"].ACTIVE,
    )


def _eepr(q, *, evidence_id: str, source_class: str, facts, authenticated=True):
    principal = f"reviewer-{source_class}-{evidence_id[0]}"
    authorization = _provenance_auth(q)
    proof = None
    secret = None
    if authenticated:
        proof = q["AuthenticatedProvenanceProof"].issue(
            evidence_id=evidence_id, source_principal_id=principal, source_authority_generation="source-gen-1",
            lineage_facts=facts, verifier_identity=authorization.verifier_identity,
            verifier_generation=authorization.verifier_generation, verification_secret=PROVENANCE_SECRET,
        )
        secret = PROVENANCE_SECRET
    return q["ExternalEvidenceProvenanceRecord"].create(
        evidence_id=evidence_id, evidence_digest=evidence_id, review_world_id=ZERO,
        source_principal_id=principal, authenticated_source_provenance="signed-platform-submission",
        source_organization=f"org-{source_class}-{evidence_id[0]}", source_class=source_class,
        source_authority_generation="source-gen-1", creation_generation="2026-09-07T10:00:00Z",
        candidate_authoring_relationship="separate", qualification_corpus_relationship="separate",
        candidate_infrastructure_relationship="separate", reviewer_tool_lineage="human-reviewer",
        prompt_controller="source-principal", input_selector="source-principal", finding_selector="source-principal",
        provenance_verification_method="platform-hmac-verifier", control_lineage_facts=facts,
        provenance_authorization=authorization, authenticated_provenance_proof=proof,
        provenance_verification_secret=secret,
    )


def test_eepr_independence_requires_authenticated_control_lineage_not_self_declaration() -> None:
    q = _load_contract()
    independent = q["ControlLineageFacts"].create(
        source_separate=True, authoring_separate=True, corpus_separate=True, infrastructure_separate=True,
        prompt_control_separate=True, input_selection_separate=True, finding_selection_separate=True,
    )
    dependent = q["ControlLineageFacts"].create(**{**independent.to_payload(), "prompt_control_separate": False})
    unknown = q["ControlLineageFacts"].create(**{**independent.to_payload(), "finding_selection_separate": None})
    assert _eepr(q, evidence_id=ONE, source_class="contractor", facts=independent).independence_state is q["IndependenceState"].INDEPENDENT
    assert _eepr(q, evidence_id=TWO, source_class="contractor", facts=dependent).independence_state is q["IndependenceState"].NOT_INDEPENDENT
    assert _eepr(q, evidence_id=THREE, source_class="contractor", facts=unknown).independence_state is q["IndependenceState"].UNKNOWN_INDEPENDENCE
    unauthenticated = _eepr(q, evidence_id=FOUR, source_class="contractor", facts=independent, authenticated=False)
    assert unauthenticated.provenance_authenticated is False
    assert unauthenticated.independence_state is q["IndependenceState"].UNKNOWN_INDEPENDENCE


def test_external_review_census_excludes_not_independent_and_unauthenticated_records() -> None:
    q = _load_contract()
    independent = q["ControlLineageFacts"].create(
        source_separate=True, authoring_separate=True, corpus_separate=True, infrastructure_separate=True,
        prompt_control_separate=True, input_selection_separate=True, finding_selection_separate=True,
    )
    dependent = q["ControlLineageFacts"].create(**{**independent.to_payload(), "input_selection_separate": False})
    records = (
        _eepr(q, evidence_id=ONE, source_class="contractor", facts=independent),
        _eepr(q, evidence_id=TWO, source_class="academic", facts=independent),
        _eepr(q, evidence_id=THREE, source_class="candidate", facts=dependent),
        _eepr(q, evidence_id=FOUR, source_class="spoofed", facts=independent, authenticated=False),
    )
    requirement = q["ExternalReviewLaneRequirement"].create(lane_id="genesis-hostile", minimum_instances=2, minimum_source_classes=2)
    census = q["evaluate_external_review_census"](records=records, requirements=(requirement,))
    assert census.satisfied is True
    assert census.lanes[0].independent_instances == 2
    assert census.lanes[0].source_classes == ("academic", "contractor")
    assert census.eligible_independent_evidence_ids == (ONE, TWO)


def test_owner_business_risk_is_structurally_disjoint_from_engineering_truth() -> None:
    q = _load_contract()
    engineering = q["EngineeringVerdictRecord"].create(review_world_id=ZERO, evidence_root_id=ONE, sergeant_authority_id=TWO, verdict=q["EngineeringVerdict"].NEEDS_WORK)
    risk = q["BusinessRiskDecisionRecord"].create(
        engineering_verdict_id=engineering.record_id, owner_authority_id=THREE,
        decision=q["BusinessRiskDecision"].ACCEPT, rationale="ship for business reasons without rewriting engineering truth",
    )
    assert engineering.verdict is q["EngineeringVerdict"].NEEDS_WORK
    assert risk.engineering_verdict_id == engineering.record_id
    assert not hasattr(risk, "evidence_root_id")
    assert not hasattr(risk, "qualification_id")
    assert not hasattr(risk, "verdict")


def test_sae170_authority_fence_is_independently_load_bearing() -> None:
    q = _load_contract()
    complete = q["GenesisQualificationPackage"].create(
        review_world_id=ZERO, required_qualification_ids=(ONE, TWO), present_qualification_ids=(ONE, TWO),
        external_review_census_id=THREE, external_review_census_satisfied=True,
        founding_final_proof_id=FOUR, generation="genesis-gen-1",
    )
    wrong = q["evaluate_genesis_exit_gate"](package=complete, authority_node="SAE-30")
    assert wrong.authorized is False
    assert any("SAE-170" in blocker for blocker in wrong.blockers)
    with pytest.raises(q["QualificationAuthorityError"]):
        q["GenesisActivationRecord"].create(package=complete, exit_gate=wrong, activation_class="founding-generation", consumed_activation_classes=())


def test_genesis_incomplete_package_remains_provisional() -> None:
    q = _load_contract()
    package = q["GenesisQualificationPackage"].create(
        review_world_id=ZERO, required_qualification_ids=(ONE, TWO), present_qualification_ids=(ONE,),
        external_review_census_id=THREE, external_review_census_satisfied=False,
        founding_final_proof_id=None, generation="genesis-gen-1",
    )
    assert package.state == "GENESIS_PROVISIONAL"
    assert q["evaluate_genesis_exit_gate"](package=package, authority_node="SAE-170").authorized is False
