from __future__ import annotations
import pytest
from main_review.assurance_learning import LearningContractError, qualify_learning_proposals

BASE={
 "lesson_id":"L1",
 "evidence_id":"E1",
 "proposal_type":"detector",
 "source":"teacher_prosecutor_defender",
 "negative_controls_passed":True,
 "transfer_passed":True,
 "hidden_holdout_passed":True,
 "owner_promotion_required":True,
 "requested_effects":["propose_detector_improvement"],
}

def proposal(**overrides):
 p=dict(BASE); p.update(overrides); return p

def test_qualified_learning_only_proposes_improvements():
 out=qualify_learning_proposals([proposal()])
 assert out["qualified"] is True
 assert out["proposals"][0]["proposal_type"]=="detector"
 assert out["authority_gain"]==[]
 assert out["auto_merge"] is False and out["auto_promote"] is False

@pytest.mark.parametrize("kind",["detector","acr","cardinality","closure","falsifier","mutation","capability","evidence","relation"])
def test_all_canonical_improvement_families_are_proposal_only(kind):
 out=qualify_learning_proposals([proposal(proposal_type=kind)])
 assert out["qualified"] is True and out["authority_gain"]==[]

@pytest.mark.parametrize("effect",["activate_acr","qualify_capability","rewrite_verdict","consume_owner_risk_acceptance_as_truth","self_promote","auto_merge"])
def test_forbidden_authority_effects_fail_closed(effect):
 with pytest.raises(LearningContractError): qualify_learning_proposals([proposal(requested_effects=[effect])])

def test_missing_teacher_prosecutor_defender_lineage_fails_closed():
 with pytest.raises(LearningContractError): qualify_learning_proposals([proposal(source="teacher_only")])

def test_negative_controls_transfer_and_hidden_holdout_are_mandatory():
 for field in ("negative_controls_passed","transfer_passed","hidden_holdout_passed"):
  with pytest.raises(LearningContractError): qualify_learning_proposals([proposal(**{field:False})])

def test_owner_controlled_promotion_is_mandatory_but_not_engineering_truth():
 with pytest.raises(LearningContractError): qualify_learning_proposals([proposal(owner_promotion_required=False)])
 out=qualify_learning_proposals([proposal(owner_risk_acceptance=True)])
 assert out["qualified"] is True and out["owner_risk_acceptance_consumed_as_truth"] is False

def test_escape_feedback_can_propose_without_promoting():
 out=qualify_learning_proposals([proposal(feedback=["qualification_escape","provenance_escape"],proposal_type="evidence")])
 assert out["qualified"] is True and out["proposals"][0]["feedback"]==["qualification_escape","provenance_escape"]
 assert out["authority_gain"]==[]

def test_terminally_rejected_lesson_cannot_revive_from_same_evidence():
 rejected={("L1","E1")}
 with pytest.raises(LearningContractError): qualify_learning_proposals([proposal()],terminally_rejected=rejected)

def test_distinct_evidence_may_create_new_proposal_after_prior_rejection():
 rejected={("L1","E0")}
 out=qualify_learning_proposals([proposal(evidence_id="E1")],terminally_rejected=rejected)
 assert out["qualified"] is True

def test_duplicate_lesson_evidence_pair_fails_closed():
 with pytest.raises(LearningContractError): qualify_learning_proposals([proposal(),proposal()])
