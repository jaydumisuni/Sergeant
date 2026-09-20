from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
import hashlib
import pytest

from main_review.external_evidence_provenance import (
    AuthenticatedProvenanceProof,
    ControlLineageFacts,
    ExternalEvidenceProvenanceRecord,
    IndependenceState,
    ProvenanceVerifierAuthorization,
    ProvenanceVerifierState,
)
from main_review.genesis_qualification import (
    GENESIS_LANE_RATIFICATION_MANIFEST,
    GENESIS_LANE_RATIFICATION_MANIFEST_BLOB,
    GENESIS_LANE_RATIFICATION_MERGE,
    PROVENANCE_VERIFIER_ARTIFACT_FAMILY,
    PROVENANCE_VERIFIER_CLOSURE_GRADE,
    PROVENANCE_VERIFIER_DOMAIN,
    PROVENANCE_VERIFIER_NAMESPACE,
    PROVENANCE_VERIFIER_PROOF_CLASS,
    GenesisQualificationError,
    qualify_genesis_package,
)
from main_review.qualification_authority import (
    AuthenticatedIssuer,
    GenesisQualificationPackage,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityRegistry,
    QualificationClosureProof,
    QualificationIssuerAuthorization,
    admit_qualification_attestation,
    qualification_verification_secret_digest,
)


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

WORLD = hashlib.sha256(b"world").hexdigest()
OTHER_WORLD = hashlib.sha256(b"other-world").hexdigest()
CANDIDATE = "c" * 40
RAB = hashlib.sha256(b"rab").hexdigest()
PROTOCOL = "sae150-protocol-v1"
MUTATION_FAMILIES = ("omission", "undercount", "cardinality", "acr", "material_input", "falsifier", "authority", "common_mode")
OBLIGATIONS = (
    "preservation_proof", "model_blackout_proof", "cpu_proof", "historical_replay", "clean_controls",
    "unrelated_transfer", "independent_hidden_cases", "independent_hostile_implementation_review",
    *(f"mutation.{family}" for family in MUTATION_FAMILIES),
)
LEGACY_BOOLEAN_CLAIMS = (
    "preservation_proof", "model_blackout_proof", "cpu_proof", "historical_replay", "clean_controls",
    "unrelated_transfer", "eepr_complete",
)

VERIFIER_SECRET = hashlib.sha256(b'test-only-rooted-provenance-verifier').digest()
SELF_MINTED_SECRET = hashlib.sha256(b'test-only-self-minted-verifier').digest()


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _verifier(identity: str, secret: bytes) -> ProvenanceVerifierAuthorization:
    return ProvenanceVerifierAuthorization.create(
        verifier_identity=identity,
        verifier_generation="verifier-gen-1",
        key_id=_digest(f"{identity}-key"),
        verification_secret_digest=hashlib.sha256(secret).hexdigest(),
        state=ProvenanceVerifierState.ACTIVE,
    )


ROOTED_VERIFIER = _verifier("owner-root-provenance-verifier", VERIFIER_SECRET)
SELF_MINTED_VERIFIER = _verifier("candidate-provenance-verifier", SELF_MINTED_SECRET)
CANDIDATE_CONTROL_LINEAGE_ID = _digest("candidate-lineage")
PROVENANCE_VERIFIER_CONTROL_LINEAGE_ID = _digest("rooted-provenance-verifier-lineage")
ROOTED_VERIFIER_ISSUER = QualificationIssuerAuthorization.create(
    issuer_identity=ROOTED_VERIFIER.verifier_identity,
    key_id=ROOTED_VERIFIER.key_id,
    namespace=PROVENANCE_VERIFIER_NAMESPACE,
    issuer_generation=ROOTED_VERIFIER.verifier_generation,
    artifact_families=(PROVENANCE_VERIFIER_ARTIFACT_FAMILY,),
    domains=(PROVENANCE_VERIFIER_DOMAIN,),
    proof_classes=(PROVENANCE_VERIFIER_PROOF_CLASS,),
    closure_grades=(PROVENANCE_VERIFIER_CLOSURE_GRADE,),
    allowed_independence_states=(IndependenceState.INDEPENDENT.value,),
    control_lineage_id=PROVENANCE_VERIFIER_CONTROL_LINEAGE_ID,
    authentication_secret_digest=ROOTED_VERIFIER.verification_secret_digest,
    state=IssuerState.ACTIVE,
)


def _eepr(label, source_class, *, verifier=ROOTED_VERIFIER, secret=VERIFIER_SECRET, authenticated=True, independent=True):
    evidence_id = _digest(label)
    principal = f"{label}-principal"
    facts = ControlLineageFacts.create(
        source_separate=True, authoring_separate=independent, corpus_separate=True,
        infrastructure_separate=True, prompt_control_separate=True,
        input_selection_separate=True, finding_selection_separate=True,
    )
    proof = None
    if authenticated:
        proof = AuthenticatedProvenanceProof.issue(
            evidence_id=evidence_id, source_principal_id=principal,
            source_authority_generation="external-generation", lineage_facts=facts,
            verifier_identity=verifier.verifier_identity, verifier_generation=verifier.verifier_generation,
            verification_secret=secret,
        )
    record = ExternalEvidenceProvenanceRecord.create(
        evidence_id=evidence_id, evidence_digest=_digest(f"{label}-payload"), review_world_id=WORLD,
        source_principal_id=principal, authenticated_source_provenance="external-attestation",
        source_organization=f"{label}-org", source_class=source_class,
        source_authority_generation="external-generation", creation_generation="external-creation",
        candidate_authoring_relationship="separate", qualification_corpus_relationship="separate",
        candidate_infrastructure_relationship="separate", reviewer_tool_lineage="independent-tooling",
        prompt_controller="external", input_selector="external", finding_selector="external",
        provenance_verification_method="hmac", control_lineage_facts=facts,
        provenance_authorization=verifier if authenticated else None,
        authenticated_provenance_proof=proof,
        provenance_verification_secret=secret if authenticated else None,
    )
    return record, proof


ISSUER_SECRET = b"sae150-qualification-issuer-secret"
ISSUER_TIME = datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc)
ISSUER = dict(
    issuer_identity="owner-root-qualification", key_id=_digest("issuer-key"),
    namespace="sergeant-qualification-attestation-v1", issuer_generation="issuer-gen-1",
)


def _admitted(obligations=OBLIGATIONS, *, subject=WORLD, independence="INDEPENDENT", admit=True):
    """Admit one attestation per obligation through the canonical SAE-30 admission path."""
    authorization = QualificationIssuerAuthorization.create(
        **ISSUER,
        artifact_families=tuple(f"sergeant.genesis.{obligation}" for obligation in OBLIGATIONS),
        domains=("sergeant.genesis.v1",), proof_classes=("bounded-hostile-qualification",),
        closure_grades=("EXACT",), allowed_independence_states=("INDEPENDENT", "NOT_INDEPENDENT"),
        control_lineage_id=_digest("issuer-lineage"),
        authentication_secret_digest=qualification_verification_secret_digest(ISSUER_SECRET),
        state=IssuerState.ACTIVE,
    )
    registry = QualificationAuthorityRegistry.create(
        generation="qar-gen-1",
        issuers=(authorization, ROOTED_VERIFIER_ISSUER),
    )
    attestations = []
    derived = []
    for obligation in obligations:
        bound = dict(
            subject_id=subject, artifact_family=f"sergeant.genesis.{obligation}", domain="sergeant.genesis.v1",
            artifact_generation=CANDIDATE, acr_generation="acr-gen-1", qualification_protocol_generation=PROTOCOL,
            evidence_root_id=_digest(f"evidence-root:{obligation}"), independence_state=independence,
            qualification_lineage_id=_digest("qualification-lineage"),
            authenticated_provenance_id=_digest("qualification-provenance"),
        )
        attestation = QualificationAttestation.create(
            **bound, proof_class="bounded-hostile-qualification", closure_grade="EXACT",
            issued_at=ISSUER_TIME - timedelta(minutes=1), expires_at=ISSUER_TIME + timedelta(hours=1),
            issuer_identity=ISSUER["issuer_identity"], issuer_generation=ISSUER["issuer_generation"],
        )
        if admit:
            authenticated = AuthenticatedIssuer.issue_verifier_proof(
                **ISSUER, registry_generation=registry.generation,
                attestation_id=attestation.attestation_id, verification_secret=ISSUER_SECRET,
            )
            closure = QualificationClosureProof.issue_verifier_proof(
                attestation_id=attestation.attestation_id, evidence_root_id=bound["evidence_root_id"],
                judge_admission_id=_digest("judge"), qualification_protocol_closure_id=_digest("protocol-closure"),
                evidence_closure_id=_digest("evidence-closure"), external_review_census_id=_digest("census"),
                independence_proof_id=_digest("independence"), judge_admitted=True,
                qualification_protocol_closed=True, evidence_closed=True, external_lanes_closed=True,
                independence_verified=True, verification_secret=ISSUER_SECRET,
            )
            qualification, registry = admit_qualification_attestation(
                registry=registry, attestation=attestation, authenticated_issuer=authenticated,
                closure_proof=closure, issuer_verification_secret=ISSUER_SECRET,
                expected_registry_generation=registry.generation, **bound,
                candidate_control_lineage_id=_digest("candidate-lineage"), now=ISSUER_TIME,
            )
            derived.append(qualification)
        attestations.append(attestation)
    return tuple(attestations), registry, tuple(derived)


ATTESTATIONS, REGISTRY, DERIVED_QUALIFICATIONS = _admitted()
DEFAULT_EVIDENCE = (_eepr("contractor-review", "SC-1"), _eepr("scoped-saas-hostile-engagement", "SC-6"))


def closed_package(*, evidence=DEFAULT_EVIDENCE, attestations=None, **overrides):
    package = {
        "candidate_generation": CANDIDATE, "rab_generation": RAB, "acr_generation": "acr-gen-1",
        "rust_generation": "rust-gen-1", "qualification_protocol_generation": PROTOCOL,
        "review_world_id": WORLD, "required_proven_nodes": dict(CANONICAL_NODES),
        "qualification_attestations": list(ATTESTATIONS if attestations is None else attestations),
        "surviving_mutants": [],
        "external_evidence": [record for record, _ in evidence],
        "external_evidence_proofs": {record.evidence_id: proof for record, proof in evidence if proof is not None},
        "residual_unknowns": [], "limitations": [],
    }
    package.update(overrides)
    return package


def qualify(
    package,
    *,
    verifiers=((ROOTED_VERIFIER, VERIFIER_SECRET),),
    registry=REGISTRY,
    derived=DERIVED_QUALIFICATIONS,
    trusted_evidence_bindings=None,
    candidate_lineage=CANDIDATE_CONTROL_LINEAGE_ID,
):
    if trusted_evidence_bindings is None:
        trusted_evidence_bindings = {
            record.evidence_id: record.eepr_id
            for record in package.get("external_evidence", ())
            if isinstance(record, ExternalEvidenceProvenanceRecord)
        }
    return qualify_genesis_package(
        package, trusted_provenance_verifiers=verifiers,
        qualification_registry=registry, admitted_qualifications=derived,
        candidate_control_lineage_id=candidate_lineage,
        trusted_generation_bindings={
            "candidate_generation": CANDIDATE, "rab_generation": RAB, "acr_generation": "acr-gen-1",
            "rust_generation": "rust-gen-1", "qualification_protocol_generation": PROTOCOL,
        },
        trusted_external_evidence_bindings=trusted_evidence_bindings,
    )


def test_missing_independent_lane_stays_genesis_provisional():
    out = qualify(closed_package(evidence=()))
    assert out["state"] == "GENESIS_PROVISIONAL"
    assert out["qualified"] is False
    assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]
    assert out["authority_gain"] == []


def test_owner_controlled_lineage_cannot_fill_independent_lane():
    out = qualify(closed_package(evidence=[_eepr("owner-hostile-review", "SC-1", independent=False)]))
    assert out["qualified"] is False
    assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]


def test_mandatory_unknown_leaves_genesis_provisional_even_with_external_lane():
    out = qualify(closed_package(residual_unknowns=["mandatory: unresolved corpus gap"]))
    assert out["qualified"] is False and out["state"] == "GENESIS_PROVISIONAL"
    assert "MANDATORY_UNKNOWN" in out["blockers"]


def test_required_nodes_reject_noncanonical_generation_values():
    nodes = dict(CANONICAL_NODES)
    nodes["SAE-140"] = "wrong"
    with pytest.raises(GenesisQualificationError):
        qualify(closed_package(required_proven_nodes=nodes))


@pytest.mark.parametrize(
    "field,bad",
    [
        ("required_proven_nodes", ["not-a-mapping"]),
        ("qualification_attestations", ["not-an-attestation"]),
        ("external_evidence", ["not-a-record"]),
        ("external_evidence_proofs", ["not-a-mapping"]),
    ],
)
def test_malformed_nested_shapes_raise_genesis_error(field, bad):
    with pytest.raises(GenesisQualificationError):
        qualify(closed_package(**{field: bad}))


def test_package_booleans_cannot_forge_independent_lane():
    forged = {
        "source_id": "forged",
        "authenticated": True,
        "materially_independent": True,
        "owner_controlled": False,
        "evidence_digest": "sha256:abc",
    }
    with pytest.raises(GenesisQualificationError):
        qualify(closed_package(external_evidence=[forged]))


def test_generation_identifiers_must_be_typed_and_bound_into_result():
    with pytest.raises(GenesisQualificationError):
        qualify(closed_package(candidate_generation=12345))

    valid = closed_package()
    out = qualify(valid)
    assert out["generation_bindings"] == {
        key: valid[key]
        for key in ("candidate_generation", "rab_generation", "acr_generation", "rust_generation", "qualification_protocol_generation")
    }
    assert out["generation_bindings_digest"]


def test_external_review_census_is_derived_instead_of_trusting_completion_boolean():
    with pytest.raises(GenesisQualificationError, match="census"):
        qualify(closed_package(evidence=(DEFAULT_EVIDENCE[0], DEFAULT_EVIDENCE[0])))


def test_external_evidence_must_match_exact_review_world():
    out = qualify(closed_package(review_world_id=OTHER_WORLD))
    assert out["qualified"] is False
    assert "EXTERNAL_EVIDENCE_REVIEW_WORLD_MISMATCH" in out["blockers"]
    assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]


def test_spike_ext_prerequisite_is_bound_to_immutable_blob_identity():
    from main_review.genesis_qualification import REQUIRED_PROVEN_NODE_BINDINGS
    assert REQUIRED_PROVEN_NODE_BINDINGS["SPIKE-EXT"] == "5a42072517efef7c1e621f12a99e9e2cbf610281"


# --- Hostile-review repair regressions (review of 005e5b684b7ae37ca129b86f9f78345e65e2342d) ---------

def test_fully_rooted_package_reaches_candidate_without_authority_gain():
    out = qualify(closed_package())
    assert out["qualified"] is True, out["blockers"]
    assert out["state"] == "GENESIS_QUALIFICATION_PACKAGE_CANDIDATE"
    assert out["authority_gain"] == [] and out["activation_authorized"] is False


def test_trust_anchors_default_to_fail_closed():
    out = qualify_genesis_package(closed_package())
    assert out["qualified"] is False
    assert {
        "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED",
        "QUALIFICATION_OBLIGATION_OPEN:cpu_proof",
    } <= set(out["blockers"])
    assert "GENESIS_LANE_CARDINALITY_UNRATIFIED" not in out["blockers"]


# F1 -- the independent lane must be re-verified, not trusted from record fields.

def test_directly_constructed_eepr_cannot_forge_independent_lane():
    forged = []
    for label, source_class in (("forged-a", "SC-1"), ("forged-b", "SC-6")):
        record, _ = _eepr(label, source_class, authenticated=False)
        forged.append((dataclasses.replace(
            record, provenance_authenticated=True,
            provenance_verifier_authorization_id=ROOTED_VERIFIER.authorization_id,
            independence_state=IndependenceState.INDEPENDENT,
        ), None))
    out = qualify(closed_package(evidence=forged))
    assert out["qualified"] is False
    assert "EXTERNAL_PROVENANCE_UNVERIFIED" in out["blockers"]


def test_self_minted_verifier_is_not_rooted_provenance_authority():
    evidence = [
        _eepr(label, source_class, verifier=SELF_MINTED_VERIFIER, secret=SELF_MINTED_SECRET)
        for label, source_class in (("self-a", "SC-1"), ("self-b", "SC-6"))
    ]
    out = qualify(closed_package(evidence=evidence))
    assert out["qualified"] is False
    assert "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED" in out["blockers"]


# F2 -- lane cardinality is not candidate-authored and never below the SPIKE-EXT 2/2 floor.

def test_single_independent_eepr_cannot_satisfy_canonical_ratified_census():
    out = qualify(closed_package(evidence=DEFAULT_EVIDENCE[:1]))
    assert out["qualified"] is False
    assert "EXTERNAL_REVIEW_CENSUS_INCOMPLETE" in out["blockers"]


@pytest.mark.parametrize("source_class", ["SC-5", "independent-human-review"])
def test_non_accepted_source_class_does_not_count_toward_census(source_class):
    evidence = (DEFAULT_EVIDENCE[0], _eepr("second-review", source_class))
    out = qualify(closed_package(evidence=evidence))
    assert out["qualified"] is False
    assert "EXTERNAL_REVIEW_CENSUS_INCOMPLETE" in out["blockers"]


def test_genesis_lane_cardinality_is_ratified_by_exact_guarded_merge():
    out = qualify(closed_package())
    assert out["external_review_lane_cardinality_ratified"] is True
    assert out["external_review_lane_authority"] == {
        "merge_commit": GENESIS_LANE_RATIFICATION_MERGE,
        "manifest_path": GENESIS_LANE_RATIFICATION_MANIFEST,
        "manifest_blob": GENESIS_LANE_RATIFICATION_MANIFEST_BLOB,
    }
    assert "GENESIS_LANE_CARDINALITY_UNRATIFIED" not in out["blockers"]


# F3 -- caller booleans carry no authority; obligations close only through admitted qualification.

def test_caller_boolean_obligation_claims_have_no_authority():
    package = closed_package(attestations=())
    package.update({field: True for field in LEGACY_BOOLEAN_CLAIMS})
    package["mutation_families"] = {family: True for family in MUTATION_FAMILIES}
    out = qualify(package)
    assert out["qualified"] is False
    for obligation in OBLIGATIONS:
        assert f"QUALIFICATION_OBLIGATION_OPEN:{obligation}" in out["blockers"]


def test_unadmitted_attestations_do_not_close_obligations():
    attestations, registry, derived = _admitted(admit=False)
    out = qualify(closed_package(attestations=attestations), registry=registry, derived=derived)
    assert out["qualified"] is False
    assert "QUALIFICATION_OBLIGATION_OPEN:cpu_proof" in out["blockers"]


def test_missing_trusted_registry_leaves_obligations_open():
    out = qualify(closed_package(), registry=None)
    assert out["qualified"] is False
    assert "QUALIFICATION_OBLIGATION_OPEN:preservation_proof" in out["blockers"]


def test_attestation_for_another_review_world_does_not_close_obligation():
    attestations, registry, derived = _admitted(subject=OTHER_WORLD)
    out = qualify(closed_package(attestations=attestations), registry=registry, derived=derived)
    assert out["qualified"] is False
    assert "QUALIFICATION_OBLIGATION_OPEN:historical_replay" in out["blockers"]


def test_surviving_required_mutant_leaves_genesis_provisional():
    out = qualify(closed_package(surviving_mutants=["mutation.omission/m-17"]))
    assert out["qualified"] is False
    assert "SURVIVING_REQUIRED_MUTANT" in out["blockers"]


def test_suspended_issuer_cannot_close_admitted_obligations():
    attestations, registry, derived = _admitted()
    active = registry.issuers[0]
    suspended = QualificationIssuerAuthorization.create(
        issuer_identity=active.issuer_identity, key_id=active.key_id, namespace=active.namespace,
        issuer_generation=active.issuer_generation, artifact_families=active.artifact_families,
        domains=active.domains, proof_classes=active.proof_classes, closure_grades=active.closure_grades,
        allowed_independence_states=active.allowed_independence_states,
        control_lineage_id=active.control_lineage_id,
        authentication_secret_digest=active.authentication_secret_digest, state=IssuerState.SUSPENDED,
    )
    suspended_registry = QualificationAuthorityRegistry.create(
        generation=registry.generation, issuers=(suspended,),
        consumed_attestation_ids=registry.consumed_attestation_ids,
    )
    out = qualify(closed_package(attestations=attestations), registry=suspended_registry, derived=derived)
    assert out["qualified"] is False
    assert "QUALIFICATION_OBLIGATION_OPEN:preservation_proof" in out["blockers"]


def test_attestation_for_other_candidate_generation_cannot_close_obligation():
    attestations, registry, derived = _admitted()
    original = attestations[0]
    fields = original.constructor_fields()
    fields["artifact_generation"] = "d" * 40
    forged = QualificationAttestation.create(**fields)
    altered = (forged, *attestations[1:])
    consumed = tuple(forged.attestation_id if item == original.attestation_id else item for item in registry.consumed_attestation_ids)
    forged_registry = QualificationAuthorityRegistry.create(
        generation=registry.generation, issuers=registry.issuers, consumed_attestation_ids=consumed,
    )
    out = qualify(closed_package(attestations=altered), registry=forged_registry, derived=derived)
    assert out["qualified"] is False
    assert "QUALIFICATION_OBLIGATION_OPEN:preservation_proof" in out["blockers"]


# F4 -- one immutable canonical package identity with a digest over the whole package.

def test_result_emits_canonical_genesis_package_and_full_package_digest():
    out = qualify(closed_package())
    package = out["genesis_package"]
    assert isinstance(package, GenesisQualificationPackage)
    assert out["package_id"] == package.package_id
    assert package.review_world_id == WORLD and package.state == "GENESIS_PROVISIONAL"
    assert package.external_review_census_id == out["external_review_census_id"]
    assert set(package.present_qualification_ids) == set(package.required_qualification_ids)
    limited = qualify(closed_package(limitations=["bounded to the Python review domain"]))
    assert limited["package_digest"] != out["package_digest"]


@pytest.mark.parametrize(
    "field,bad",
    [("candidate_generation", "candidate-sha"), ("rab_generation", "rab-sha"), ("acr_generation", "latest")],
)
def test_generation_identities_must_be_canonical(field, bad):
    with pytest.raises(GenesisQualificationError):
        qualify(closed_package(**{field: bad}))


# F5 -- docs/58 section 14 package obligations.

@pytest.mark.parametrize("field", ["qualification_protocol_generation", "limitations"])
def test_protocol_generation_and_limitations_are_mandatory(field):
    package = closed_package()
    del package[field]
    with pytest.raises(GenesisQualificationError):
        qualify(package)


@pytest.mark.parametrize("obligation", ["independent_hidden_cases", "independent_hostile_implementation_review"])
def test_hidden_cases_and_hostile_review_are_mandatory_obligations(obligation):
    attestations, registry, derived = _admitted(tuple(item for item in OBLIGATIONS if item != obligation))
    out = qualify(closed_package(attestations=attestations), registry=registry, derived=derived)
    assert out["qualified"] is False
    assert f"QUALIFICATION_OBLIGATION_OPEN:{obligation}" in out["blockers"]


def test_independent_obligations_require_independent_qualification():
    attestations, registry, derived = _admitted(independence="NOT_INDEPENDENT")
    out = qualify(closed_package(attestations=attestations), registry=registry, derived=derived)
    assert out["qualified"] is False
    assert "QUALIFICATION_OBLIGATION_OPEN:independent_hostile_implementation_review" in out["blockers"]
    assert "QUALIFICATION_OBLIGATION_OPEN:cpu_proof" not in out["blockers"]


def test_required_obligation_inventory_is_exact():
    from main_review.genesis_qualification import REQUIRED_QUALIFICATION_OBLIGATIONS
    assert tuple(REQUIRED_QUALIFICATION_OBLIGATIONS) == OBLIGATIONS


# F6 -- UNKNOWN is conserved; the caller cannot label it away.

@pytest.mark.parametrize("unknown", ["corpus gap unresolved", "Mandatory - corpus gap", "mandatory : corpus gap"])
def test_every_residual_unknown_blocks(unknown):
    out = qualify(closed_package(residual_unknowns=[unknown]))
    assert out["qualified"] is False
    assert "MANDATORY_UNKNOWN" in out["blockers"]


def test_unknown_independence_evidence_is_conserved_and_reported():
    unknown = _eepr("unauthenticated-review", "SC-4", authenticated=False)
    out = qualify(closed_package(evidence=(*DEFAULT_EVIDENCE, unknown)))
    assert out["qualified"] is False
    assert "MANDATORY_UNKNOWN" in out["blockers"]
    assert f"UNKNOWN_INDEPENDENCE:{unknown[0].evidence_id}" in out["residual_unknowns"]
    dispositions = {row["evidence_id"]: row for row in out["external_evidence_dispositions"]}
    assert dispositions[unknown[0].evidence_id]["independence_state"] == "UNKNOWN_INDEPENDENCE"
    assert dispositions[unknown[0].evidence_id]["counted"] is False


# F7 -- prerequisite bindings carry an explicit git object kind.

def test_proven_node_bindings_are_type_tagged():
    from main_review.genesis_qualification import PROVEN_NODE_BINDING_KINDS, REQUIRED_PROVEN_NODE_BINDINGS
    assert set(PROVEN_NODE_BINDING_KINDS) == set(REQUIRED_PROVEN_NODE_BINDINGS)
    assert PROVEN_NODE_BINDING_KINDS["SPIKE-EXT"] == "blob"
    assert {kind for node, kind in PROVEN_NODE_BINDING_KINDS.items() if node != "SPIKE-EXT"} == {"commit"}

# --- Supervisor exact-head regressions for review of 6310dcc834f216258105cef1ed582252aa2ce720 ---

def test_sae150_trusted_evidence_binding_rejects_retargeted_eepr_claims():
    record, proof = _eepr("claims-bound", "SC-1")
    assert proof is not None
    forged = ExternalEvidenceProvenanceRecord.create(
        evidence_id=record.evidence_id, evidence_digest=record.evidence_digest, review_world_id=OTHER_WORLD,
        source_principal_id=record.source_principal_id, authenticated_source_provenance=record.authenticated_source_provenance,
        source_organization=record.source_organization, source_class="SC-6",
        source_authority_generation=record.source_authority_generation, creation_generation=record.creation_generation,
        candidate_authoring_relationship=record.candidate_authoring_relationship,
        qualification_corpus_relationship=record.qualification_corpus_relationship,
        candidate_infrastructure_relationship=record.candidate_infrastructure_relationship,
        reviewer_tool_lineage=record.reviewer_tool_lineage, prompt_controller=record.prompt_controller,
        input_selector=record.input_selector, finding_selector=record.finding_selector,
        provenance_verification_method=record.provenance_verification_method, control_lineage_facts=record.control_lineage_facts,
        provenance_authorization=ROOTED_VERIFIER, authenticated_provenance_proof=proof,
        provenance_verification_secret=VERIFIER_SECRET,
    )
    assert forged.provenance_authenticated is True  # SAE-30 legacy proof alone does not bind these claims.
    package = closed_package(evidence=((forged, proof), DEFAULT_EVIDENCE[1]))
    out = qualify(package, trusted_evidence_bindings={
        record.evidence_id: record.eepr_id,
        DEFAULT_EVIDENCE[1][0].evidence_id: DEFAULT_EVIDENCE[1][0].eepr_id,
    })
    assert out["qualified"] is False
    assert f"EXTERNAL_EVIDENCE_CLAIMS_UNTRUSTED:{record.evidence_id}" in out["blockers"]


def test_consumed_but_never_admitted_attestations_do_not_close_obligations():
    attestations, registry, derived = _admitted(admit=False)
    replay_only = QualificationAuthorityRegistry.create(
        generation=registry.generation,
        issuers=registry.issuers,
        consumed_attestation_ids=tuple(item.attestation_id for item in attestations),
    )
    out = qualify(closed_package(attestations=attestations), registry=replay_only, derived=derived)
    assert out["qualified"] is False
    assert "QUALIFICATION_OBLIGATION_OPEN:preservation_proof" in out["blockers"]


@pytest.mark.parametrize("field,value", [("rab_generation", _digest("different-rab")), ("rust_generation", "rust-gen-2")])
def test_declared_rab_and_rust_generations_require_trusted_exact_binding(field, value):
    out = qualify(closed_package(**{field: value}))
    assert out["qualified"] is False
    assert f"UNTRUSTED_GENERATION_BINDING:{field}" in out["blockers"]


def test_canonical_genesis_package_identity_changes_with_full_qualification_digest():
    base = qualify(closed_package())
    limited = qualify(closed_package(limitations=["bounded to the Python review domain"]))
    assert base["package_digest"] != limited["package_digest"]
    assert base["package_id"] != limited["package_id"]


def _registry_with_provenance_issuer(issuer):
    qualification_issuers = tuple(
        item for item in REGISTRY.issuers
        if item.issuer_identity != ROOTED_VERIFIER.verifier_identity
    )
    return QualificationAuthorityRegistry.create(
        generation=REGISTRY.generation,
        issuers=(*qualification_issuers, issuer),
        consumed_attestation_ids=REGISTRY.consumed_attestation_ids,
        revoked_attestation_ids=REGISTRY.revoked_attestation_ids,
    )


def test_provenance_verifier_requires_sae30_registry_root():
    unrooted = QualificationAuthorityRegistry.create(
        generation=REGISTRY.generation,
        issuers=tuple(
            item for item in REGISTRY.issuers
            if item.issuer_identity != ROOTED_VERIFIER.verifier_identity
        ),
        consumed_attestation_ids=REGISTRY.consumed_attestation_ids,
        revoked_attestation_ids=REGISTRY.revoked_attestation_ids,
    )
    out = qualify(closed_package(), registry=unrooted)
    assert out["qualified"] is False
    assert "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED" in out["blockers"]


def test_candidate_control_lineage_cannot_root_its_own_provenance_verifier():
    out = qualify(
        closed_package(),
        candidate_lineage=PROVENANCE_VERIFIER_CONTROL_LINEAGE_ID,
    )
    assert out["qualified"] is False
    assert "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED" in out["blockers"]


def test_suspended_registry_provenance_verifier_fails_closed():
    suspended = QualificationIssuerAuthorization.create(
        issuer_identity=ROOTED_VERIFIER.verifier_identity,
        key_id=ROOTED_VERIFIER.key_id,
        namespace=PROVENANCE_VERIFIER_NAMESPACE,
        issuer_generation=ROOTED_VERIFIER.verifier_generation,
        artifact_families=(PROVENANCE_VERIFIER_ARTIFACT_FAMILY,),
        domains=(PROVENANCE_VERIFIER_DOMAIN,),
        proof_classes=(PROVENANCE_VERIFIER_PROOF_CLASS,),
        closure_grades=(PROVENANCE_VERIFIER_CLOSURE_GRADE,),
        allowed_independence_states=(IndependenceState.INDEPENDENT.value,),
        control_lineage_id=PROVENANCE_VERIFIER_CONTROL_LINEAGE_ID,
        authentication_secret_digest=ROOTED_VERIFIER.verification_secret_digest,
        state=IssuerState.SUSPENDED,
    )
    out = qualify(closed_package(), registry=_registry_with_provenance_issuer(suspended))
    assert out["qualified"] is False
    assert "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED" in out["blockers"]


def test_registry_provenance_verifier_key_mismatch_fails_closed():
    mismatched = QualificationIssuerAuthorization.create(
        issuer_identity=ROOTED_VERIFIER.verifier_identity,
        key_id=_digest("different-verifier-key"),
        namespace=PROVENANCE_VERIFIER_NAMESPACE,
        issuer_generation=ROOTED_VERIFIER.verifier_generation,
        artifact_families=(PROVENANCE_VERIFIER_ARTIFACT_FAMILY,),
        domains=(PROVENANCE_VERIFIER_DOMAIN,),
        proof_classes=(PROVENANCE_VERIFIER_PROOF_CLASS,),
        closure_grades=(PROVENANCE_VERIFIER_CLOSURE_GRADE,),
        allowed_independence_states=(IndependenceState.INDEPENDENT.value,),
        control_lineage_id=PROVENANCE_VERIFIER_CONTROL_LINEAGE_ID,
        authentication_secret_digest=ROOTED_VERIFIER.verification_secret_digest,
        state=IssuerState.ACTIVE,
    )
    out = qualify(closed_package(), registry=_registry_with_provenance_issuer(mismatched))
    assert out["qualified"] is False
    assert "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED" in out["blockers"]


def test_registry_provenance_verifier_namespace_mismatch_fails_closed():
    mismatched = QualificationIssuerAuthorization.create(
        issuer_identity=ROOTED_VERIFIER.verifier_identity,
        key_id=ROOTED_VERIFIER.key_id,
        namespace="unrelated-qualification-namespace",
        issuer_generation=ROOTED_VERIFIER.verifier_generation,
        artifact_families=(PROVENANCE_VERIFIER_ARTIFACT_FAMILY,),
        domains=(PROVENANCE_VERIFIER_DOMAIN,),
        proof_classes=(PROVENANCE_VERIFIER_PROOF_CLASS,),
        closure_grades=(PROVENANCE_VERIFIER_CLOSURE_GRADE,),
        allowed_independence_states=(IndependenceState.INDEPENDENT.value,),
        control_lineage_id=PROVENANCE_VERIFIER_CONTROL_LINEAGE_ID,
        authentication_secret_digest=ROOTED_VERIFIER.verification_secret_digest,
        state=IssuerState.ACTIVE,
    )
    out = qualify(closed_package(), registry=_registry_with_provenance_issuer(mismatched))
    assert out["qualified"] is False
    assert "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED" in out["blockers"]


def test_caller_cannot_supply_or_weaken_ratified_genesis_lane():
    with pytest.raises(TypeError, match="ratified_external_review_lanes"):
        qualify_genesis_package(
            closed_package(),
            ratified_external_review_lanes=(),
        )
