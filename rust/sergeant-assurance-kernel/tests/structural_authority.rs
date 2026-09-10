use sergeant_assurance_kernel::{
    evaluate_structural_capsule, AuthorityRecord, ClosedCollection, QualificationAttestation,
    QualificationRegistry, StructuralAssuranceCapsule, ADMISSIBLE, INADMISSIBLE,
};

fn id(ch: char) -> String { ch.to_string().repeat(64) }

fn authority(ch: char, generation: &str) -> AuthorityRecord {
    AuthorityRecord { id: id(ch), generation: generation.into(), revoked: false }
}

fn attestation(subject: &AuthorityRecord, issuer: char) -> QualificationAttestation {
    QualificationAttestation {
        id: id('f'),
        subject_id: subject.id.clone(),
        subject_generation: subject.generation.clone(),
        issuer_id: id(issuer),
        revoked: false,
    }
}

fn closed(ch: char, generation: &str, members: &[char]) -> ClosedCollection {
    let authority = authority(ch, generation);
    let values: Vec<String> = members.iter().map(|c| id(*c)).collect();
    ClosedCollection {
        authority,
        members: values.clone(),
        expected_members: values,
        certificate: authority('e', generation),
    }
}

fn capsule() -> StructuralAssuranceCapsule {
    let generation = "sae-r2-g1";
    let review_world = authority('a', generation);
    let rab = authority('b', generation);
    let proof_world = authority('c', generation);
    let falsifier_frontier = closed('d', generation, &['1', '2']);
    let active_contracts = closed('3', generation, &['4', '5']);
    let applicable_instances = closed('6', generation, &['7', '8']);
    let expected_obligations = closed('9', generation, &['a', 'b']);
    let authority_premises = closed('c', generation, &['d', 'e']);
    let capability_passports = closed('1', generation, &['2', '3']);
    let provenance = closed('4', generation, &['5']);

    let registry = QualificationRegistry {
        authority: authority('6', generation),
        authorized_issuers: vec![id('7')],
    };

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
        review_world,
        rab,
        active_contracts,
        applicable_instances,
        expected_obligations,
        authority_premises,
        capability_passports,
        proof_world,
        falsifier_frontier,
        provenance,
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
    c.active_contracts.members.push(c.active_contracts.members[0].clone());
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
