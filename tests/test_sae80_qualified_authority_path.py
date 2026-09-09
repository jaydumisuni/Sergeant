from __future__ import annotations

from datetime import datetime, timezone

import main_review.proof_world as pw
from main_review.assurance_contract_registry import ClosureGrade
from main_review.qualification_authority import (
    AuthenticatedIssuer,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityRegistry,
    QualificationClosureProof,
    QualificationIssuerAuthorization,
    qualification_verification_secret_digest,
)
from main_review.review_authority_bundle import (
    RABAuthorization,
    RABAuthorizationSet,
    ReviewAuthorityBundle,
)
from main_review.review_world import GitHubDiffIdentity, GitHubReviewWorld, ReviewScope, sha256_id
from tests.test_sae80_authority_hardening import _fixture, _material


def _review_authority():
    bundle = ReviewAuthorityBundle.create()
    authorization = RABAuthorization.authorized(bundle.rab_id, "auth-g1", "sae80-test-root")
    authorization_set = RABAuthorizationSet.create((authorization,))
    scope = ReviewScope.repository()
    diff = GitHubDiffIdentity.create(
        repository="jaydumisuni/sergeant",
        base_commit="1" * 40,
        base_tree="2" * 40,
        head_commit="3" * 40,
        head_tree="4" * 40,
        scope=scope,
    )
    review_world = GitHubReviewWorld.create(
        repository="jaydumisuni/sergeant",
        pr_number=198,
        diff=diff,
        scope=scope,
        review_mode="head",
        rab_id=bundle.rab_id,
        review_generation="sae80-review-gen-1",
    )
    return bundle, authorization_set, review_world


def test_sae10_sae30_sae70_authority_can_issue_exact_mechanical_proof_world() -> None:
    bind_world = getattr(pw, "bind_qualified_world", None)
    create_evidence = getattr(pw, "create_qualified_evidence", None)
    assert callable(bind_world), "SAE-80 must expose qualified Review World binding"
    assert callable(create_evidence), "SAE-80 must expose provenance-qualified evidence construction"

    registry, qualified_closure, obligation = _fixture()
    bundle, authorization_set, review_world = _review_authority()
    qualified_world = bind_world(
        review_world=review_world,
        current_world=review_world,
        rab_bundle=bundle,
        rab_authorizations=authorization_set,
        qualified_closure=qualified_closure,
        registry=registry,
        epoch=42,
    )

    secret = b"sae80-verifier-secret-32-bytes!!"
    issuer_control = sha256_id({"sae80": "issuer-control"})
    issuer = QualificationIssuerAuthorization.create(
        issuer_identity="sae80-proof-issuer",
        key_id=sha256_id({"sae80": "issuer-key"}),
        namespace="sergeant.sae80.evidence",
        issuer_generation="issuer-g1",
        artifact_families=("sae80-evidence-proof",),
        domains=(obligation.family,),
        proof_classes=("mechanical",),
        closure_grades=("EXACT",),
        allowed_independence_states=("INDEPENDENT",),
        control_lineage_id=issuer_control,
        authentication_secret_digest=qualification_verification_secret_digest(secret),
        state=IssuerState.ACTIVE,
    )
    qualification_registry = QualificationAuthorityRegistry.create(
        generation="sae80-qar-g1",
        issuers=(issuer,),
    )
    evidence_basis_id = sha256_id({"sae80": "qualified-evidence", "obligation": obligation.obligation_id})
    qualification_lineage_id = sha256_id({"sae80": "qualification-lineage"})
    authenticated_provenance_id = sha256_id({"sae80": "authenticated-provenance"})
    now = datetime(2026, 9, 9, 7, 0, tzinfo=timezone.utc)
    attestation = QualificationAttestation.create(
        subject_id=evidence_basis_id,
        artifact_family="sae80-evidence-proof",
        domain=obligation.family,
        artifact_generation=qualified_world.authority_id,
        acr_generation=registry.generation,
        qualification_protocol_generation="sae80-evidence-qualification-v1",
        evidence_root_id=evidence_basis_id,
        proof_class="mechanical",
        closure_grade="EXACT",
        independence_state="INDEPENDENT",
        qualification_lineage_id=qualification_lineage_id,
        authenticated_provenance_id=authenticated_provenance_id,
        issued_at=datetime(2026, 9, 9, 6, 0, tzinfo=timezone.utc),
        expires_at=datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc),
        issuer_identity=issuer.issuer_identity,
        issuer_generation=issuer.issuer_generation,
    )
    authenticated_issuer = AuthenticatedIssuer.issue_verifier_proof(
        issuer_identity=issuer.issuer_identity,
        key_id=issuer.key_id,
        namespace=issuer.namespace,
        issuer_generation=issuer.issuer_generation,
        registry_generation=qualification_registry.generation,
        attestation_id=attestation.attestation_id,
        verification_secret=secret,
    )
    closure_proof = QualificationClosureProof.issue_verifier_proof(
        attestation_id=attestation.attestation_id,
        evidence_root_id=evidence_basis_id,
        judge_admission_id=sha256_id({"sae80": "judge-admission"}),
        qualification_protocol_closure_id=sha256_id({"sae80": "protocol-closure"}),
        evidence_closure_id=sha256_id({"sae80": "evidence-closure"}),
        external_review_census_id=sha256_id({"sae80": "external-census"}),
        independence_proof_id=sha256_id({"sae80": "independence-proof"}),
        judge_admitted=True,
        qualification_protocol_closed=True,
        evidence_closed=True,
        external_lanes_closed=True,
        independence_verified=True,
        verification_secret=secret,
    )

    evidence, consumed_registry = create_evidence(
        claimed_closure=ClosureGrade.EXACT,
        obligation_id=obligation.obligation_id,
        contract_instance_ids=tuple(origin.contract_instance_id for origin in obligation.provenance),
        world=qualified_world,
        material_inputs=(_material(),),
        claims={"authz:/admin": "preserved"},
        assumptions=(),
        observed_epoch=42,
        evidence_basis_id=evidence_basis_id,
        qualification_registry=qualification_registry,
        attestation=attestation,
        authenticated_issuer=authenticated_issuer,
        closure_proof=closure_proof,
        issuer_verification_secret=secret,
        expected_registry_generation=qualification_registry.generation,
        qualification_lineage_id=qualification_lineage_id,
        authenticated_provenance_id=authenticated_provenance_id,
        candidate_control_lineage_id=sha256_id({"sae80": "candidate-control"}),
        now=now,
    )
    assert attestation.attestation_id in consumed_registry.consumed_attestation_ids
    assert evidence.proof_class is pw.ProofClass.MECHANICAL

    proof = pw.compile_proof_world(
        qualified_closure=qualified_closure,
        expected_obligation=obligation,
        registry=registry,
        world=qualified_world,
        evidence=(evidence,),
    )
    assert proof.grade is ClosureGrade.EXACT
    assert proof.blockers == ()
    assert proof.validate() == proof
