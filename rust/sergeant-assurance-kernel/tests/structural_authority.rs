use sergeant_assurance_kernel::{
    evaluate_structural_capsule, AuthorityRecord, ClosedCollection, QualificationAttestation,
    QualificationRegistry, StructuralAssuranceCapsule, ADMISSIBLE, INADMISSIBLE,
};

fn id(ch: char) -> String {
    ch.to_string().repeat(64)
}

fn authority(ch: char, generation: &str) -> AuthorityRecord {
    AuthorityRecord {
        id: id(ch),
        generation: generation.into(),
        revoked: false,
    }
}

fn attestation(subject: &AuthorityRecord, issuer: char) -> QualificationAttestation {
    QualificationAttestation {
        id: subject.id.clone(),
        subject_id: subject.id.clone(),
        subject_generation: subject.generation.clone(),
        issuer_id: id(issuer),
        revoked: false,
    }
}

fn closed(ch: char, generation: &str, members: &[char]) -> ClosedCollection {
    let collection_authority = authority(ch, generation);
    let values: Vec<String> = members.iter().map(|c| id(*c)).collect();
    ClosedCollection {
        authority: collection_authority.clone(),
        members: values.clone(),
        expected_members: values,
        certificate: authority('e', generation),
        certificate_subject_id: collection_authority.id.clone(),
        source_basis_id: id('0'),
    }
}

fn capsule() -> StructuralAssuranceCapsule {
    let generation = "sae-r2-g1";
    let review_world = authority('a', generation);
    let rab = authority('b', generation);
    let proof_world = authority('e', generation);
    let mut falsifier_frontier = closed('d', generation, &['1', '2']);
    let mut active_contracts = closed('3', generation, &['4', '5']);
    let mut applicable_instances = closed('6', generation, &['7', '8']);
    let mut expected_obligations = closed('9', generation, &['a', 'b']);
    let mut authority_premises = closed('c', generation, &['d', 'e']);
    let mut capability_passports = closed('1', generation, &['2', '3']);
    let mut provenance = closed('4', generation, &['5']);

    let registry = QualificationRegistry {
        authority: authority('0', generation),
        authorized_issuers: vec![id('7')],
    };
    let review_world_scope_id = id('8');
    let review_world_rab_id = rab.id.clone();
    active_contracts.source_basis_id = review_world.id.clone();
    applicable_instances.source_basis_id = active_contracts.authority.id.clone();
    expected_obligations.source_basis_id = applicable_instances.authority.id.clone();
    authority_premises.source_basis_id = expected_obligations.authority.id.clone();
    capability_passports.source_basis_id = registry.authority.id.clone();
    falsifier_frontier.source_basis_id = expected_obligations.authority.id.clone();
    provenance.source_basis_id = review_world.id.clone();

    let subjects = [
        &review_world,
        &rab,
        &proof_world,
        &falsifier_frontier.authority,
        &active_contracts.authority,
        &applicable_instances.authority,
        &expected_obligations.authority,
        &authority_premises.authority,
        &capability_passports.authority,
        &provenance.authority,
    ];

    StructuralAssuranceCapsule {
        subject_generation: generation.into(),
        current_generation: generation.into(),
        qualification_registry: registry,
        attestations: subjects.iter().map(|s| attestation(s, '7')).collect(),
        review_world_rab_id,
        review_world_scope_id: review_world_scope_id.clone(),
        review_world: review_world.clone(),
        rab,
        rab_scope_id: review_world_scope_id,
        active_contracts,
        applicable_instances,
        expected_obligations: expected_obligations.clone(),
        authority_premises,
        capability_passports,
        proof_world_review_world_id: review_world.id.clone(),
        proof_world_expected_obligations_id: expected_obligations.authority.id.clone(),
        proof_world,
        falsifier_expected_obligations_id: expected_obligations.authority.id.clone(),
        falsifier_frontier,
        provenance,
        required_external_sources: 1,
        external_source_ids: vec![id('9')],
        unknowns_present: false,
        python_expected_list_authority: false,
        shared_implementation_claim: false,
    }
}

#[test]
fn exact_structural_capsule_is_admissible() {
    assert_eq!(evaluate_structural_capsule(&capsule()), ADMISSIBLE);
}

#[test]
fn fabricated_qualification_is_rejected() {
    let mut c = capsule();
    c.attestations[0].subject_id = id('0');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn unauthorized_qualification_issuer_is_rejected() {
    let mut c = capsule();
    c.attestations[0].issuer_id = id('8');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn incomplete_collection_is_rejected() {
    let mut c = capsule();
    c.expected_obligations.members.pop();
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn duplicated_member_cannot_fake_exact_set_closure() {
    let mut c = capsule();
    c.active_contracts
        .members
        .push(c.active_contracts.members[0].clone());
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn wrong_generation_authority_is_rejected() {
    let mut c = capsule();
    c.proof_world.generation = "stale".into();
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn revoked_authority_is_rejected() {
    let mut c = capsule();
    c.rab.revoked = true;
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn missing_attestation_is_rejected() {
    let mut c = capsule();
    c.attestations.pop();
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn review_world_must_bind_exact_rab_and_scope() {
    let mut c = capsule();
    c.review_world_rab_id = id('8');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
    let mut c = capsule();
    c.rab_scope_id = id('9');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn proof_world_and_falsifier_frontier_must_bind_expected_authority() {
    let mut c = capsule();
    c.proof_world_review_world_id = id('8');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
    let mut c = capsule();
    c.proof_world_expected_obligations_id = id('8');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
    let mut c = capsule();
    c.falsifier_expected_obligations_id = id('8');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn closure_certificates_must_bind_collection_and_source_basis() {
    let mut c = capsule();
    c.expected_obligations.certificate_subject_id = id('8');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
    let mut c = capsule();
    c.expected_obligations.source_basis_id = id('8');
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}

#[test]
fn external_provenance_cardinality_is_exact() {
    let mut c = capsule();
    c.required_external_sources = 2;
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
    let mut c = capsule();
    c.external_source_ids.push(c.external_source_ids[0].clone());
    assert_eq!(evaluate_structural_capsule(&c), INADMISSIBLE);
}
