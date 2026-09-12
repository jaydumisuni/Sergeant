from __future__ import annotations
import json
from pathlib import Path
import pytest
from main_review.assurance_learning import ALLOWED_TYPES, FORBIDDEN_EFFECTS, LearningContractError, qualify_learning_proposals
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/"docs/156-sae140-assurance-learning-candidate.md"
MANIFEST=ROOT/"docs/157-sae140-assurance-learning-candidate-manifest.json"
BASE={"lesson_id":"L","evidence_id":"E","proposal_type":"detector","source":"teacher_prosecutor_defender","negative_controls_passed":True,"transfer_passed":True,"hidden_holdout_passed":True,"owner_promotion_required":True,"requested_effects":["propose_detector_improvement"]}

def test_required_inventory_and_roadmap_families_exist():
 assert DOC.is_file() and MANIFEST.is_file() and (ROOT/"main_review/assurance_learning.py").is_file()
 m=json.loads(MANIFEST.read_text())
 assert set(m["proposal_families"])==ALLOWED_TYPES
 assert set(m["forbidden_authority_effects"])==FORBIDDEN_EFFECTS

def test_learning_campaign_preserves_proposal_only_authority():
 rows=[]
 for i,kind in enumerate(sorted(ALLOWED_TYPES)):
  p=dict(BASE,lesson_id=f"L{i}",evidence_id=f"E{i}",proposal_type=kind)
  rows.append(p)
 out=qualify_learning_proposals(rows)
 assert out["qualified"] is True and out["authority_gain"]==[]
 assert out["auto_merge"] is False and out["auto_promote"] is False

def test_escape_feedback_is_consumed_without_revival_or_promotion():
 p=dict(BASE,feedback=["qualification_escape","provenance_escape"],proposal_type="evidence")
 out=qualify_learning_proposals([p])
 assert out["proposals"][0]["feedback"]==["qualification_escape","provenance_escape"]
 with pytest.raises(LearningContractError): qualify_learning_proposals([p],terminally_rejected={("L","E")})

def test_owner_risk_acceptance_never_becomes_engineering_truth():
 p=dict(BASE,owner_risk_acceptance=True)
 out=qualify_learning_proposals([p])
 assert out["owner_risk_acceptance_consumed_as_truth"] is False
