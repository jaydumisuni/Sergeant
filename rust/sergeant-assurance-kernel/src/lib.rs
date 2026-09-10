//! SAE-R2 independent constitutional admissibility kernel.
//!
//! The authoritative path derives admissibility from typed frozen authority
//! structures.  It does not accept aggregate or component qualification booleans.

use std::collections::BTreeSet;

pub const ADMISSIBLE: &str = "ADMISSIBLE";
pub const INADMISSIBLE: &str = "INADMISSIBLE";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AuthorityRecord {
    pub id: String,
    pub generation: String,
    pub revoked: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QualificationAttestation {
    pub id: String,
    pub subject_id: String,
    pub subject_generation: String,
    pub issuer_id: String,
    pub revoked: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QualificationRegistry {
    pub authority: AuthorityRecord,
    pub authorized_issuers: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClosedCollection {
    pub authority: AuthorityRecord,
    pub members: Vec<String>,
    pub expected_members: Vec<String>,
    pub certificate: AuthorityRecord,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralAssuranceCapsule {
    pub subject_generation: String,
    pub current_generation: String,
    pub qualification_registry: QualificationRegistry,
    pub attestations: Vec<QualificationAttestation>,
    pub review_world: AuthorityRecord,
    pub rab: AuthorityRecord,
    pub active_contracts: ClosedCollection,
    pub applicable_instances: ClosedCollection,
    pub expected_obligations: ClosedCollection,
    pub authority_premises: ClosedCollection,
    pub capability_passports: ClosedCollection,
    pub proof_world: AuthorityRecord,
    pub falsifier_frontier: ClosedCollection,
    pub provenance: ClosedCollection,
    pub unknowns_present: bool,
    pub python_expected_list_authority: bool,
    pub shared_implementation_claim: bool,
}

fn is_full_authority_id(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

fn valid_authority(record: &AuthorityRecord, generation: &str) -> bool {
    is_full_authority_id(&record.id)
        && !record.generation.is_empty()
        && record.generation == generation
        && !record.revoked
}

fn exact_unique_set(actual: &[String], expected: &[String]) -> bool {
    if actual.iter().any(|id| !is_full_authority_id(id))
        || expected.iter().any(|id| !is_full_authority_id(id))
    {
        return false;
    }
    let actual_set: BTreeSet<_> = actual.iter().collect();
    let expected_set: BTreeSet<_> = expected.iter().collect();
    actual_set.len() == actual.len()
        && expected_set.len() == expected.len()
        && actual_set == expected_set
}

fn valid_closed_collection(value: &ClosedCollection, generation: &str) -> bool {
    valid_authority(&value.authority, generation)
        && valid_authority(&value.certificate, generation)
        && exact_unique_set(&value.members, &value.expected_members)
}

fn valid_registry(registry: &QualificationRegistry, generation: &str) -> bool {
    if !valid_authority(&registry.authority, generation)
        || registry.authorized_issuers.is_empty()
        || registry
            .authorized_issuers
            .iter()
            .any(|issuer| !is_full_authority_id(issuer))
    {
        return false;
    }
    let issuers: BTreeSet<_> = registry.authorized_issuers.iter().collect();
    issuers.len() == registry.authorized_issuers.len()
}

fn subject_ids(capsule: &StructuralAssuranceCapsule) -> Vec<&str> {
    vec![
        capsule.review_world.id.as_str(),
        capsule.rab.id.as_str(),
        capsule.active_contracts.authority.id.as_str(),
        capsule.applicable_instances.authority.id.as_str(),
        capsule.expected_obligations.authority.id.as_str(),
        capsule.authority_premises.authority.id.as_str(),
        capsule.capability_passports.authority.id.as_str(),
        capsule.proof_world.id.as_str(),
        capsule.falsifier_frontier.authority.id.as_str(),
        capsule.provenance.authority.id.as_str(),
    ]
}

fn qualifications_are_derived(capsule: &StructuralAssuranceCapsule) -> bool {
    let authorized: BTreeSet<_> = capsule
        .qualification_registry
        .authorized_issuers
        .iter()
        .map(String::as_str)
        .collect();

    let mut seen_subjects = BTreeSet::new();
    let mut seen_attestations = BTreeSet::new();
    for attestation in &capsule.attestations {
        if !is_full_authority_id(&attestation.id)
            || !is_full_authority_id(&attestation.subject_id)
            || !is_full_authority_id(&attestation.issuer_id)
            || attestation.subject_generation != capsule.current_generation
            || !authorized.contains(attestation.issuer_id.as_str())
            || attestation.revoked
            || !seen_attestations.insert(attestation.id.as_str())
            || !seen_subjects.insert(attestation.subject_id.as_str())
        {
            return false;
        }
    }

    let required: BTreeSet<_> = subject_ids(capsule).into_iter().collect();
    seen_subjects == required
}

pub fn evaluate_structural_capsule(capsule: &StructuralAssuranceCapsule) -> &'static str {
    if capsule.subject_generation.is_empty()
        || capsule.subject_generation != capsule.current_generation
        || capsule.unknowns_present
        || capsule.python_expected_list_authority
        || capsule.shared_implementation_claim
    {
        return INADMISSIBLE;
    }

    let generation = capsule.current_generation.as_str();
    if !valid_registry(&capsule.qualification_registry, generation)
        || !valid_authority(&capsule.review_world, generation)
        || !valid_authority(&capsule.rab, generation)
        || !valid_closed_collection(&capsule.active_contracts, generation)
        || !valid_closed_collection(&capsule.applicable_instances, generation)
        || !valid_closed_collection(&capsule.expected_obligations, generation)
        || !valid_closed_collection(&capsule.authority_premises, generation)
        || !valid_closed_collection(&capsule.capability_passports, generation)
        || !valid_authority(&capsule.proof_world, generation)
        || !valid_closed_collection(&capsule.falsifier_frontier, generation)
        || !valid_closed_collection(&capsule.provenance, generation)
        || !qualifications_are_derived(capsule)
    {
        return INADMISSIBLE;
    }

    ADMISSIBLE
}

#[cfg(test)]
mod tests {
    use super::*;

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
    fn closed(ch: char, generation: &str, members: &[char]) -> ClosedCollection {
        let values: Vec<String> = members.iter().map(|c| id(*c)).collect();
        ClosedCollection {
            authority: authority(ch, generation),
            members: values.clone(),
            expected_members: values,
            certificate: authority('e', generation),
        }
    }
    fn capsule() -> StructuralAssuranceCapsule {
        let g = "sae-r2-g1";
        let review_world = authority('a', g);
        let rab = authority('b', g);
        let active_contracts = closed('3', g, &['4', '5']);
        let applicable_instances = closed('6', g, &['7', '8']);
        let expected_obligations = closed('9', g, &['a', 'b']);
        let authority_premises = closed('c', g, &['d', 'e']);
        let capability_passports = closed('1', g, &['2', '3']);
        let proof_world = authority('e', g);
        let falsifier_frontier = closed('d', g, &['1', '2']);
        let provenance = closed('4', g, &['5']);
        let registry = QualificationRegistry {
            authority: authority('0', g),
            authorized_issuers: vec![id('7')],
        };
        let subjects = [
            &review_world,
            &rab,
            &active_contracts.authority,
            &applicable_instances.authority,
            &expected_obligations.authority,
            &authority_premises.authority,
            &capability_passports.authority,
            &proof_world,
            &falsifier_frontier.authority,
            &provenance.authority,
        ];
        let attestations = subjects
            .iter()
            .map(|subject| QualificationAttestation {
                id: subject.id.clone(),
                subject_id: subject.id.clone(),
                subject_generation: subject.generation.clone(),
                issuer_id: id('7'),
                revoked: false,
            })
            .collect();
        StructuralAssuranceCapsule {
            subject_generation: g.into(),
            current_generation: g.into(),
            qualification_registry: registry,
            attestations,
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
    fn complete_structural_capsule_is_admissible() {
        assert_eq!(evaluate_structural_capsule(&capsule()), ADMISSIBLE);
    }

    #[test]
    fn unknown_and_stale_generation_fail_closed() {
        let mut unknown = capsule();
        unknown.unknowns_present = true;
        assert_eq!(evaluate_structural_capsule(&unknown), INADMISSIBLE);
        let mut stale = capsule();
        stale.proof_world.generation = "old".into();
        assert_eq!(evaluate_structural_capsule(&stale), INADMISSIBLE);
    }

    #[test]
    fn qualification_is_derived_not_asserted() {
        let mut forged = capsule();
        forged.attestations[0].subject_id = id('0');
        assert_eq!(evaluate_structural_capsule(&forged), INADMISSIBLE);
        let mut unauthorized = capsule();
        unauthorized.attestations[0].issuer_id = id('8');
        assert_eq!(evaluate_structural_capsule(&unauthorized), INADMISSIBLE);
    }

    #[test]
    fn collection_closure_is_exact_and_unique() {
        let mut missing = capsule();
        missing.expected_obligations.members.pop();
        assert_eq!(evaluate_structural_capsule(&missing), INADMISSIBLE);
        let mut duplicate = capsule();
        duplicate
            .active_contracts
            .members
            .push(duplicate.active_contracts.members[0].clone());
        assert_eq!(evaluate_structural_capsule(&duplicate), INADMISSIBLE);
    }
}
