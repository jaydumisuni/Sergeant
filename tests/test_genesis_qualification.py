from __future__ import annotations
import pytest
from main_review.genesis_qualification import GenesisQualificationError, qualify_genesis_package

BASE={
 "candidate_generation":"candidate-sha",
 "rab_generation":"rab-sha",
 "acr_generation":"acr-sha",
 "rust_generation":"rust-sha",
 "required_proven_nodes":{k:"proven" for k in ["SAE-100","SAE-110","SAE-120","SAE-130A","SAE-130B","SAE-130C","SAE-130D","SAE-130E","SAE-140","SPIKE-EXT"]},
 "preservation_proof":True,"model_blackout_proof":True,"cpu_proof":True,"historical_replay":True,"clean_controls":True,
 "mutation_families":{k:True for k in ["omission","undercount","cardinality","acr","material_input","falsifier","authority","common_mode"]},
 "unrelated_transfer":True,"eepr_complete":True,"external_review_instance_census_complete":True,
 "residual_unknowns":[],"external_evidence":[],
}

def test_missing_independent_lane_stays_genesis_provisional():
 out=qualify_genesis_package(BASE)
 assert out["state"]=="GENESIS_PROVISIONAL"
 assert out["qualified"] is False
 assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]
 assert out["authority_gain"]==[]

def test_owner_or_ai_controlled_review_cannot_fill_independent_lane():
 row=dict(BASE,external_evidence=[{"source_id":"owner-ai","authenticated":True,"materially_independent":False,"owner_controlled":True}])
 out=qualify_genesis_package(row)
 assert out["qualified"] is False
 assert "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE" in out["blockers"]

def test_authenticated_materially_independent_lane_can_qualify_when_everything_else_is_closed():
 row=dict(BASE,external_evidence=[{"source_id":"independent-reviewer-1","authenticated":True,"materially_independent":True,"owner_controlled":False,"evidence_digest":"sha256:abc"}])
 out=qualify_genesis_package(row)
 assert out["qualified"] is True
 assert out["state"]=="GENESIS_QUALIFICATION_PACKAGE_CANDIDATE"
 assert out["authority_gain"]==[]

@pytest.mark.parametrize("field",["preservation_proof","model_blackout_proof","cpu_proof","historical_replay","clean_controls","unrelated_transfer","eepr_complete","external_review_instance_census_complete"])
def test_required_proof_families_fail_closed(field):
 row=dict(BASE); row[field]=False
 with pytest.raises(GenesisQualificationError): qualify_genesis_package(row)

def test_all_required_mutation_families_are_mandatory():
 row=dict(BASE); row["mutation_families"]={"omission":True}
 with pytest.raises(GenesisQualificationError): qualify_genesis_package(row)

def test_mandatory_unknown_leaves_genesis_provisional_even_with_external_lane():
 row=dict(BASE,external_evidence=[{"source_id":"independent-reviewer-1","authenticated":True,"materially_independent":True,"owner_controlled":False,"evidence_digest":"sha256:abc"}],residual_unknowns=["mandatory: unresolved corpus gap"])
 out=qualify_genesis_package(row)
 assert out["qualified"] is False and out["state"]=="GENESIS_PROVISIONAL"
 assert "MANDATORY_UNKNOWN" in out["blockers"]
