from __future__ import annotations

from datetime import datetime, timedelta, timezone

from main_review.assurance_contract_registry import (
    ACRContract,
    ACRRegistry,
    ApplicabilityContext,
    ApplicabilityPredicate,
    BoundedDomain,
    CardinalitySpec,
    ClosureGrade,
    CollectionRequirement,
    CollectionSemantics,
    ContractRequirement,
    ExternalReviewLane,
    NegativeApplicabilityBurden,
)
from main_review.assurance_ledger import (
    JudgeAssuranceLedger,
    LedgerEpistemicState,
    LedgerRecord,
    LedgerRecordKind,
)
from main_review.capability_qualification import CapabilityPassport, analyze_bounded_indirect_calls
from main_review.contract_closure import ContractInstanceEnumeration, compile_contract_closure
from main_review.contract_closure_protocol import qualify_contract_closure
from main_review.proof_world import (
    Assumption,
    EvidenceProof,
    MaterialInputProof,
    ProofClass,
    WorldCoordinates,
)
from main_review.proof_world_authority import (
    EVIDENCE_ARTIFACT_FAMILY,
    EVIDENCE_DOMAIN,
    EVIDENCE_QUALIFICATION_GENERATION,
    ProofWorldAuthority,
    bind_evidence_proof_authority,
    bind_proof_world_authority,
)
from main_review.qualification_authority import (
    AuthenticatedIssuer,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityRegistry,
    QualificationClosureProof,
    QualificationIssuerAuthorization,
    admit_qualification_attestation,
    qualification_verification_secret_digest,
)
from main_review.review_authority_bundle import RABAuthorization, RABComponent, ReviewAuthorityBundle
from main_review.review_world import GitHubDiffIdentity, GitHubReviewWorld, ReviewScope, sha256_id
from main_review.semantic_capability_protocol import (
    ARTIFACT_GENERATION,
    COMMON_MODE_LINEAGE_ID,
    CONTROL_LINEAGE_ID,
    FRAMEWORK_GENERATION,
    FRAMEWORK_LINEAGE_ID,
    IMPLEMENTATION_LINEAGE_ID,
    PARSER_GENERATION,
    PARSER_LINEAGE_ID,
    PROOF_CEILING,
    QUALIFICATION_PROTOCOL_GENERATION,
    qualify_bounded_literal_dispatch,
    qualified_domain,
)
from tests.semantic_oracle.bounded_call_oracle import HOLDOUT_FIXTURE


ISSUER_SECRET = sha256_id({"fixture": "sae80-independent-issuer"}).encode("ascii")
KEY_ID = sha256_id({"sae80": "issuer-key"})
ISSUER_CONTROL = sha256_id({"sae80": "independent-issuer-control"})
CANDIDATE_CONTROL = sha256_id({"sae80": "candidate-control"})
BASE_COMMIT = "a" * 40
BASE_TREE = "b" * 40
HEAD_COMMIT = "c" * 40
HEAD_TREE = "d" * 40
DEFAULT_PROOF_CLASSES = ("mechanical", "exhaustive-oracle", "heuristic")


def contract(
    contract_id: str,
    *,
    obligation: str = "authz-preserved",
    material_inputs: tuple[str, ...] = ("router-config", "policy-file"),
    proof_classes: tuple[str, ...] = DEFAULT_PROOF_CLASSES,
) -> ACRContract:
    return ACRContract.create(
        contract_id=contract_id,
        generation="sae80-contract-gen-1",
        domain=BoundedDomain.create(
            domain_id="python.web-route.sae80-proof-world.v1",
            generation="sae80-domain-gen-1",
            dimensions={"max_routes": 16, "max_material_inputs": 8},
        ),
        applicability=ApplicabilityPredicate.all_of(
            ApplicabilityPredicate.fact_equals("language", "python"),
            ApplicabilityPredicate.fact_equals("framework", "flask"),
        ),
        bound_subject_variables=("route",),
        semantic_carrier_families=("routes",),
        consumer_interpretation_families=("router",),
        affected_relation_families=("route_to_handler",),
        collections=(
            CollectionRequirement.create(
                "routes",
                CollectionSemantics.SET,
                CardinalitySpec.bounded_n(16),
                ClosureGrade.EXACT,
            ),
        ),
        mandatory_premises=(ContractRequirement.create("route-discovery", ClosureGrade.EXACT),),
        repeated_authority_premise_families=("review-world",),
        mandatory_obligations=(ContractRequirement.create(obligation, ClosureGrade.EXACT),),
        admissible_proof_classes=proof_classes,
        material_inputs=tuple(ContractRequirement.create(name, ClosureGrade.EXACT) for name in material_inputs),
        coherence_rules=(
            "same-candidate-generation",
            "same-framework-generation",
            "same-provider-generation",
            "same-dependency-generation",
        ),
        temporal_rules=("evidence-not-older-than-world",),
        mandatory_falsifier_families=("delete-policy",),
        required_independence=("qualification-corpus-independent",),
        permitted_capabilities=("python.bounded-literal-dispatch.v1",),
        negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),
        external_review_lanes=(ExternalReviewLane.create("hostile-external", 1),),
        unsupported_fallback="UNKNOWN",
    )


def qualified_fixture(
    *,
    overlapping: bool = False,
    proof_classes: tuple[str, ...] = DEFAULT_PROOF_CLASSES,
):
    first = contract("primary-authz", proof_classes=proof_classes)
    contracts = [first]
    if overlapping:
        contracts.append(
            contract(
                "secondary-authz",
                material_inputs=("policy-file", "audit-schema"),
                proof_classes=proof_classes,
            )
        )
    registry = ACRRegistry.create(generation="sae80-acr-gen-1", contracts=tuple(contracts))
    contexts = {
        item.contract_id: ApplicabilityContext.exact({"language": "python", "framework": "flask"})
        for item in contracts
    }
    enumerations = {
        item.contract_id: ContractInstanceEnumeration.create(
            contract=item,
            bindings=({"route": "/admin"},),
            closure=ClosureGrade.EXACT,
            source_basis_id=sha256_id({"sae80-instance-basis": item.contract_id}),
        )
        for item in contracts
    }
    closure = compile_contract_closure(
        registry=registry,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match={},
    )
    qualified = qualify_contract_closure(
        registry=registry,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match={},
        result=closure,
    )
    return qualified, closure.expected_obligations[0], registry


def _issuer() -> QualificationIssuerAuthorization:
    return QualificationIssuerAuthorization.create(
        issuer_identity="sae80-independent-qualification",
        key_id=KEY_ID,
        namespace="sergeant-qualification-attestation-v1",
        issuer_generation="sae80-issuer-gen-1",
        artifact_families=(EVIDENCE_ARTIFACT_FAMILY,),
        domains=(EVIDENCE_DOMAIN,),
        proof_classes=DEFAULT_PROOF_CLASSES,
        closure_grades=(
            ClosureGrade.EXACT.value,
            ClosureGrade.CONSERVATIVE_SUPERSET.value,
            ClosureGrade.PARTIAL.value,
        ),
        allowed_independence_states=("INDEPENDENT",),
        control_lineage_id=ISSUER_CONTROL,
        authentication_secret_digest=qualification_verification_secret_digest(ISSUER_SECRET),
        state=IssuerState.ACTIVE,
    )


def _semantic_capability():
    passport = CapabilityPassport.create(
        capability_name="python-bounded-literal-dispatch",
        domain=qualified_domain(),
        artifact_generation=ARTIFACT_GENERATION,
        parser_generation=PARSER_GENERATION,
        framework_generation=FRAMEWORK_GENERATION,
        qualification_protocol_generation=QUALIFICATION_PROTOCOL_GENERATION,
        proof_ceiling=PROOF_CEILING,
        closure_ceiling=ClosureGrade.EXACT,
        implementation_lineage_id=IMPLEMENTATION_LINEAGE_ID,
        parser_lineage_id=PARSER_LINEAGE_ID,
        framework_lineage_id=FRAMEWORK_LINEAGE_ID,
        common_mode_lineage_id=COMMON_MODE_LINEAGE_ID,
        control_lineage_id=CONTROL_LINEAGE_ID,
    )
    evaluation = analyze_bounded_indirect_calls(HOLDOUT_FIXTURE.source, passport=passport)
    qualified = qualify_bounded_literal_dispatch(passport=passport, evaluation=evaluation)
    return passport, evaluation, qualified


def authority_fixture(qualified, registry, *, epoch: int = 42) -> tuple[ProofWorldAuthority, WorldCoordinates]:
    qreg = QualificationAuthorityRegistry.create(
        generation="sae80-qualification-registry-gen-1",
        issuers=(_issuer(),),
    )
    rab = ReviewAuthorityBundle.create(
        acr_generation=RABComponent.active(
            name="acr_generation",
            generation=registry.generation,
            content_id=registry.registry_id,
            authority_domain="sergeant-assurance",
        ),
        qualification_authority_registry=RABComponent.active(
            name="qualification_authority_registry",
            generation=qreg.generation,
            content_id=qreg.registry_id,
            authority_domain="sergeant-assurance",
        ),
    )
    scope = ReviewScope.repository()
    diff = GitHubDiffIdentity.create(
        repository="jaydumisuni/Sergeant",
        base_commit=BASE_COMMIT,
        base_tree=BASE_TREE,
        head_commit=HEAD_COMMIT,
        head_tree=HEAD_TREE,
        scope=scope,
    )
    review_world = GitHubReviewWorld.create(
        repository="jaydumisuni/Sergeant",
        pr_number=198,
        diff=diff,
        scope=scope,
        review_mode="head",
        rab_id=rab.rab_id,
        review_generation="sae80-review-world-gen-1",
    )
    rab_authorization = RABAuthorization.authorized(
        rab.rab_id,
        "sae80-rab-authorization-gen-1",
        "SAE-10 PROVEN root authorization",
    )
    record = LedgerRecord.create(
        kind=LedgerRecordKind.REVIEW_WORLD,
        review_world_id=review_world.review_world_id,
        rab_id=rab.rab_id,
        scope_id=scope.scope_id,
        generation="sae80-review-world-record-gen-1",
        occurrence=0,
        epistemic_state=LedgerEpistemicState.TRUE,
        authority_refs=(rab.rab_id,),
        payload={"review_world_id": review_world.review_world_id},
    )
    ledger = JudgeAssuranceLedger.create(
        review_world_id=review_world.review_world_id,
        rab_id=rab.rab_id,
        generation="sae80-ledger-gen-1",
        records=(record,),
    )
    passport, evaluation, semantic = _semantic_capability()
    authority = bind_proof_world_authority(
        review_world=review_world,
        rab=rab,
        rab_authorization=rab_authorization,
        ledger=ledger,
        qualification_registry=qreg,
        acr_registry=registry,
        capability_passport=passport,
        capability_evaluation=evaluation,
        semantic_capability=semantic,
        qualified_contract_closure=qualified,
        epoch=epoch,
    )
    return authority, WorldCoordinates.from_authority(authority)


def material(name: str, *, closure: ClosureGrade = ClosureGrade.EXACT) -> MaterialInputProof:
    return MaterialInputProof.create(
        family=name,
        closure=closure,
        basis_id=sha256_id({"material-input": name, "generation": 1}),
    )


def evidence(
    obligation,
    world: WorldCoordinates,
    world_authority: ProofWorldAuthority,
    *,
    proof_class: ProofClass = ProofClass.MECHANICAL,
    claimed_closure: ClosureGrade = ClosureGrade.EXACT,
    materials: tuple[str, ...] = ("router-config", "policy-file"),
    claims: dict[str, object] | None = None,
    assumptions: tuple[Assumption, ...] = (),
    epoch: int | None = None,
) -> EvidenceProof:
    claims = claims or {"authz:/admin": "preserved"}
    observed = world.epoch if epoch is None else epoch
    basis_id = sha256_id(
        {
            "evidence": obligation.obligation_id,
            "proof_class": proof_class.value,
            "epoch": observed,
            "materials": list(materials),
            "claims": claims,
        }
    )
    issuer = world_authority.qualification_registry.issuers[0]
    now = datetime(2026, 9, 9, 7, 0, tzinfo=timezone.utc)
    ceiling = (
        ClosureGrade.CONSERVATIVE_SUPERSET
        if proof_class is ProofClass.HEURISTIC
        else ClosureGrade.EXACT
    )
    attestation = QualificationAttestation.create(
        subject_id=obligation.obligation_id,
        artifact_family=EVIDENCE_ARTIFACT_FAMILY,
        domain=EVIDENCE_DOMAIN,
        artifact_generation=world_authority.candidate_generation,
        acr_generation=world_authority.acr_registry.generation,
        qualification_protocol_generation=EVIDENCE_QUALIFICATION_GENERATION,
        evidence_root_id=basis_id,
        proof_class=proof_class.value,
        closure_grade=ceiling.value,
        independence_state="INDEPENDENT",
        qualification_lineage_id=sha256_id({"sae80-qualification": basis_id}),
        authenticated_provenance_id=sha256_id({"sae80-provenance": basis_id}),
        issued_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(hours=1),
        issuer_identity=issuer.issuer_identity,
        issuer_generation=issuer.issuer_generation,
    )
    authenticated = AuthenticatedIssuer.issue_verifier_proof(
        issuer_identity=issuer.issuer_identity,
        key_id=issuer.key_id,
        namespace=issuer.namespace,
        issuer_generation=issuer.issuer_generation,
        registry_generation=world_authority.qualification_registry.generation,
        attestation_id=attestation.attestation_id,
        verification_secret=ISSUER_SECRET,
    )
    closure = QualificationClosureProof.issue_verifier_proof(
        attestation_id=attestation.attestation_id,
        evidence_root_id=basis_id,
        judge_admission_id=sha256_id({"judge": basis_id}),
        qualification_protocol_closure_id=sha256_id({"protocol": basis_id}),
        evidence_closure_id=sha256_id({"closure": basis_id}),
        external_review_census_id=sha256_id({"external": basis_id}),
        independence_proof_id=sha256_id({"independence": basis_id}),
        judge_admitted=True,
        qualification_protocol_closed=True,
        evidence_closed=True,
        external_lanes_closed=True,
        independence_verified=True,
        verification_secret=ISSUER_SECRET,
    )
    qualification, _ = admit_qualification_attestation(
        registry=world_authority.qualification_registry,
        attestation=attestation,
        authenticated_issuer=authenticated,
        closure_proof=closure,
        issuer_verification_secret=ISSUER_SECRET,
        expected_registry_generation=world_authority.qualification_registry.generation,
        subject_id=attestation.subject_id,
        artifact_family=attestation.artifact_family,
        domain=attestation.domain,
        artifact_generation=attestation.artifact_generation,
        acr_generation=attestation.acr_generation,
        qualification_protocol_generation=attestation.qualification_protocol_generation,
        evidence_root_id=basis_id,
        independence_state=attestation.independence_state,
        qualification_lineage_id=attestation.qualification_lineage_id,
        authenticated_provenance_id=attestation.authenticated_provenance_id,
        candidate_control_lineage_id=CANDIDATE_CONTROL,
        now=now,
    )
    proof_authority = bind_evidence_proof_authority(
        world_authority=world_authority,
        obligation_id=obligation.obligation_id,
        evidence_basis_id=basis_id,
        attestation=attestation,
        qualification=qualification,
        authenticated_issuer=authenticated,
        closure_proof=closure,
        issuer_verification_secret=ISSUER_SECRET,
        expected_registry_generation=world_authority.qualification_registry.generation,
        candidate_control_lineage_id=CANDIDATE_CONTROL,
        now=now,
    )
    return EvidenceProof.create(
        proof_class=proof_class,
        claimed_closure=claimed_closure,
        obligation_id=obligation.obligation_id,
        contract_instance_ids=tuple(origin.contract_instance_id for origin in obligation.provenance),
        world=world,
        material_inputs=tuple(material(name) for name in materials),
        claims=claims,
        assumptions=assumptions,
        observed_epoch=observed,
        evidence_basis_id=basis_id,
        proof_authority=proof_authority,
        world_authority=world_authority,
    )
