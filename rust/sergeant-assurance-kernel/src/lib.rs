//! SAE-R2 independent constitutional admissibility kernel.
//!
//! This crate is dependency-free and does not import the Python reference
//! implementation. It returns only ADMISSIBLE or INADMISSIBLE.

pub const ADMISSIBLE: &str = "ADMISSIBLE";
pub const INADMISSIBLE: &str = "INADMISSIBLE";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssuranceCapsule {
    pub review_world_id: String,
    pub rab_id: String,
    pub active_contracts_id: String,
    pub applicable_instances_id: String,
    pub expected_obligations_id: String,
    pub authority_premises_id: String,
    pub closure_certificate_id: String,
    pub capability_passports_id: String,
    pub proof_world_id: String,
    pub falsifier_frontier_id: String,
    pub provenance_id: String,
    pub subject_generation: String,
    pub current_generation: String,
    pub review_world_qualified: bool,
    pub rab_qualified: bool,
    pub active_contracts_complete: bool,
    pub applicable_instances_complete: bool,
    pub expected_obligations_complete: bool,
    pub authority_premises_typed: bool,
    pub closure_certificate_valid: bool,
    pub capability_passports_qualified: bool,
    pub proof_world_bound: bool,
    pub falsifier_frontier_complete: bool,
    pub provenance_bound: bool,
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

pub fn evaluate_capsule(capsule: &AssuranceCapsule) -> &'static str {
    let ids = [
        &capsule.review_world_id,
        &capsule.rab_id,
        &capsule.active_contracts_id,
        &capsule.applicable_instances_id,
        &capsule.expected_obligations_id,
        &capsule.authority_premises_id,
        &capsule.closure_certificate_id,
        &capsule.capability_passports_id,
        &capsule.proof_world_id,
        &capsule.falsifier_frontier_id,
        &capsule.provenance_id,
    ];
    if ids.iter().any(|value| !is_full_authority_id(value)) {
        return INADMISSIBLE;
    }
    let component_gates = [
        capsule.review_world_qualified,
        capsule.rab_qualified,
        capsule.active_contracts_complete,
        capsule.applicable_instances_complete,
        capsule.expected_obligations_complete,
        capsule.authority_premises_typed,
        capsule.closure_certificate_valid,
        capsule.capability_passports_qualified,
        capsule.proof_world_bound,
        capsule.falsifier_frontier_complete,
        capsule.provenance_bound,
    ];
    if component_gates.iter().any(|qualified| !qualified)
        || capsule.unknowns_present
        || capsule.python_expected_list_authority
        || capsule.shared_implementation_claim
        || capsule.subject_generation.is_empty()
        || capsule.subject_generation != capsule.current_generation
    {
        return INADMISSIBLE;
    }
    ADMISSIBLE
}

#[cfg(test)]
mod tests {
    use super::*;

    fn capsule() -> AssuranceCapsule {
        AssuranceCapsule {
            review_world_id: "a".repeat(64),
            rab_id: "b".repeat(64),
            active_contracts_id: "c".repeat(64),
            applicable_instances_id: "d".repeat(64),
            expected_obligations_id: "e".repeat(64),
            authority_premises_id: "f".repeat(64),
            closure_certificate_id: "a".repeat(64),
            capability_passports_id: "b".repeat(64),
            proof_world_id: "c".repeat(64),
            falsifier_frontier_id: "d".repeat(64),
            provenance_id: "e".repeat(64),
            subject_generation: "g90".into(),
            current_generation: "g90".into(),
            review_world_qualified: true,
            rab_qualified: true,
            active_contracts_complete: true,
            applicable_instances_complete: true,
            expected_obligations_complete: true,
            authority_premises_typed: true,
            closure_certificate_valid: true,
            capability_passports_qualified: true,
            proof_world_bound: true,
            falsifier_frontier_complete: true,
            provenance_bound: true,
            unknowns_present: false,
            python_expected_list_authority: false,
            shared_implementation_claim: false,
        }
    }

    #[test]
    fn complete_current_qualified_capsule_is_admissible() {
        assert_eq!(evaluate_capsule(&capsule()), ADMISSIBLE);
    }

    #[test]
    fn unknown_is_inadmissible() {
        let mut value = capsule();
        value.unknowns_present = true;
        assert_eq!(evaluate_capsule(&value), INADMISSIBLE);
    }

    #[test]
    fn python_expected_list_authority_is_inadmissible() {
        let mut value = capsule();
        value.python_expected_list_authority = true;
        assert_eq!(evaluate_capsule(&value), INADMISSIBLE);
    }

    #[test]
    fn shared_implementation_claim_is_inadmissible() {
        let mut value = capsule();
        value.shared_implementation_claim = true;
        assert_eq!(evaluate_capsule(&value), INADMISSIBLE);
    }

    #[test]
    fn stale_generation_is_inadmissible() {
        let mut value = capsule();
        value.subject_generation = "stale".into();
        assert_eq!(evaluate_capsule(&value), INADMISSIBLE);
    }

    #[test]
    fn truncated_authority_id_is_inadmissible() {
        let mut value = capsule();
        value.proof_world_id = "a".repeat(16);
        assert_eq!(evaluate_capsule(&value), INADMISSIBLE);
    }

    #[test]
    fn each_component_gate_fails_closed() {
        let mut cases = Vec::new();
        macro_rules! reject { ($field:ident) => {{ let mut v = capsule(); v.$field = false; cases.push(evaluate_capsule(&v)); }}; }
        reject!(review_world_qualified);
        reject!(rab_qualified);
        reject!(active_contracts_complete);
        reject!(applicable_instances_complete);
        reject!(expected_obligations_complete);
        reject!(authority_premises_typed);
        reject!(closure_certificate_valid);
        reject!(capability_passports_qualified);
        reject!(proof_world_bound);
        reject!(falsifier_frontier_complete);
        reject!(provenance_bound);
        assert!(cases.iter().all(|value| *value == INADMISSIBLE));
    }

    #[test]
    fn kernel_output_domain_is_exact() {
        let accepted = evaluate_capsule(&capsule());
        let mut rejected = capsule();
        rejected.provenance_bound = false;
        assert_eq!([accepted, evaluate_capsule(&rejected)], [ADMISSIBLE, INADMISSIBLE]);
    }
}
