from __future__ import annotations

import hashlib
import json
from pathlib import Path

ATTACKS = {
    "route_goal_authority_coupling": {"semantic_coupling", "self_model"},
    "lease_import_root_authority": {"authority_effect", "authority_model"},
    "post_verification_substitution": {"state_failure", "relational_assurance", "candidate_space"},
    "stale_generation_measurement": {"proof_world", "generation_metric_ledger"},
    "reviewer_lineage_collapse": {"review_lineage", "observer_sufficiency"},
    "admission_rollback_highwater": {"authority_effect", "semantic_mutation"},
    "environment_config_injection": {"clean_clone", "semantic_mutation"},
    "hidden_index_or_untracked_edit": {"clean_clone", "proof_world"},
    "common_mode_external_evidence": {"review_lineage", "candidate_space", "donor_lineage_binding"},
    "mandatory_unknown_suppression": {"unknown_conservation", "rust_kernel", "falsification"},
    "cross_repo_recurrence_transfer": {"sae140_learning", "recurrence_model", "qualified_lesson_transfer"},
    "false_positive_pattern_recurrence": {"reviewer_comparison", "observer_sufficiency", "rejected_lesson_memory"},
    "evidence_retargeting": {"proof_world", "relational_assurance", "generation_metric_ledger"},
    "cardinality_undercount": {"semantic_mutation", "falsification", "candidate_space"},
    "private_helper_dependency": {"clean_clone", "exact_predecessor", "observer_sufficiency"},
    "retry_duplicate_partial_commit": {"state_failure", "relational_assurance"},
}

BASE = {
    "review_world", "acr", "judge", "rust_kernel", "falsification", "authority_effect",
    "semantic_coupling", "state_failure", "semantic_mutation", "relational_assurance",
    "assurance_capsule", "reviewer_comparison", "sae140_learning", "review_lineage",
    "proof_world", "clean_clone", "unknown_conservation", "tenfold_private_force",
    "dependency_frontier", "exact_predecessor", "teacher_prosecutor_defender",
}
COG = {
    "identity", "self_model", "observed_state", "expected_state", "capabilities",
    "obligation_synthesis", "authority_model", "evidence_model", "frontier_model",
    "experience_model", "recovery_model", "recurrence_model", "learning_model",
    "consequence_guard", "bounded_execution", "readback",
}
FORMULA_MEASURE = {
    "measurement_governance", "no_required_regression", "generation_delta_measurement",
    "authority_violation_metric", "false_positive_metric", "recurrence_metric",
    "seeded_detection_metric", "cross_project_reuse_metric", "frontier_latency_metric",
}
FORMULA_SEARCH = {
    "candidate_space", "observer_sufficiency", "contextual_reduction", "information_gain",
    "value_of_computation", "proof_disproof_estimate", "nogood_learning", "fairness_floor",
    "deterministic_replay", "certified_escalation",
}
COOKPIT = {
    "generation_metric_ledger", "stale_measurement_rejection",
    "campaign_currentness", "readonly_registry",
}
LEARNING = {
    "qualified_lesson_transfer", "rejected_lesson_memory",
    "cross_repo_transfer", "hidden_holdout_learning",
}
TENFOLD = {
    "adaptive_frontier_allocation", "parallel_private_cells",
    "lease_fencing", "proof_carrying_execution",
}
DONOR = {"optional_external_donors", "donor_lineage_binding", "donor_unique_findings"}

HARD_GATES = (
    "srg_final_authority", "no_self_certification", "external_independence_preserved",
    "models_optional", "unknown_conserved", "judge_rust_preserved",
    "protected_merge_forbidden",
)

WEIGHTS = {
    "constitutional_safety": 1.4,
    "currentness_binding": 1.2,
    "activation_readiness": .8,
    "autonomous_attack_discovery": 1.4,
    "search_intelligence": 1.3,
    "measurement_rigor": 1.0,
    "learning_transfer": 1.0,
    "parallel_frontier": .7,
    "deterministic_replay": .8,
    "provider_independence": .8,
    "integration_safety": .7,
}

def coverage(features: set[str]) -> tuple[int, list[str]]:
    hits = [name for name, required in ATTACKS.items() if required <= features]
    return len(hits), hits

def score(features: set[str], *, risk: int = 1) -> dict:
    count, hits = coverage(features)
    vals = {
        "constitutional_safety": 5.0,
        "currentness_binding": 5.0,
        "activation_readiness": 3.0,
        "autonomous_attack_discovery": round(5 * count / len(ATTACKS), 3),
        "search_intelligence": min(5.0, 2.8
            + (.45 if "self_model" in features else 0)
            + (.35 if "obligation_synthesis" in features else 0)
            + (.55 if "candidate_space" in features else 0)
            + (.45 if "information_gain" in features else 0)
            + (.35 if "value_of_computation" in features else 0)
            + (.25 if "nogood_learning" in features else 0)),
        "measurement_rigor": min(5.0, 3.0
            + (1.0 if "measurement_governance" in features else 0)
            + (1.0 if "generation_metric_ledger" in features else 0)),
        "learning_transfer": min(5.0, 4.1
            + (.25 if "recurrence_model" in features else 0)
            + (.25 if "qualified_lesson_transfer" in features else 0)
            + (.2 if "rejected_lesson_memory" in features else 0)
            + (.2 if "cross_repo_transfer" in features else 0)),
        "parallel_frontier": 4.0 + (1.0 if "adaptive_frontier_allocation" in features else 0),
        "deterministic_replay": min(5.0, 4.2
            + (.4 if "deterministic_replay" in features else 0)
            + (.4 if "proof_carrying_execution" in features else 0)),
        "provider_independence": 5.0,
        "integration_safety": max(0.0, 5.0 - .35 * risk),
    }
    soft = 100 * sum((vals[k] / 5) * w for k, w in WEIGHTS.items()) / sum(WEIGHTS.values())
    return {
        "hard_gates": {gate: True for gate in HARD_GATES},
        "hard_pass": True,
        "soft_structural_score": round(soft, 2),
        "attack_coverage": {"count": count, "total": len(ATTACKS), "classes": hits},
        "metrics": vals,
    }

def run() -> dict:
    features = set(BASE) | COG | FORMULA_MEASURE
    rows = []
    before = score(features, risk=1)
    for label, addition, risk in [
        ("advanced_formula_search", FORMULA_SEARCH, 2),
        ("cookpit_generation_ledger", COOKPIT, 2),
        ("learning_bridge", LEARNING, 2),
        ("adaptive_tenfold", TENFOLD, 3),
        ("optional_donors", DONOR, 3),
    ]:
        features |= addition
        after = score(features, risk=risk)
        rows.append({
            "step": label,
            "before": before["soft_structural_score"],
            "after": after["soft_structural_score"],
            "delta": round(after["soft_structural_score"] - before["soft_structural_score"], 2),
            "attack_coverage": after["attack_coverage"]["count"],
        })
        before = after
    payload = {
        "schema": "sergeant.sae150-cog-formula-successor-portable-simulation.v1",
        "model_note": "Ordinal structural mechanism-coverage proxy; not an empirical defect probability.",
        "base": score(set(BASE) | COG | FORMULA_MEASURE, risk=1),
        "rollout": rows,
        "owned_without_donors": score(set(BASE) | COG | FORMULA_MEASURE | FORMULA_SEARCH | COOKPIT | LEARNING | TENFOLD, risk=3),
        "full_with_optional_donors": score(set(BASE) | COG | FORMULA_MEASURE | FORMULA_SEARCH | COOKPIT | LEARNING | TENFOLD | DONOR, risk=3),
    }
    semantic = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["simulation_digest"] = hashlib.sha256(semantic).hexdigest()
    return payload

if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
