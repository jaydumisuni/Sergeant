from __future__ import annotations

from main_review.learning_proof import PROOF_SCHEMA, run_verified_learning_proof


def test_verified_learning_proof_completes_full_chain() -> None:
    proof = run_verified_learning_proof()

    assert proof["schema_version"] == PROOF_SCHEMA
    assert proof["passed"] is True
    assert proof["accepted_event_count"] == 4
    assert proof["rejected_event_count"] == 4
    assert proof["recurrence_count"] >= 1
    assert proof["checks"]["later_mission_retrieved_experience"] is True
    assert proof["checks"]["similar_non_identical_issue_detected"] is True
    assert proof["checks"]["rejected_memory_not_recurrence_evidence"] is True
    assert proof["checks"]["cpl_officer_model_weapon_profiles_exist"] is True
    assert proof["checks"]["current_evidence_remains_authoritative"] is True
