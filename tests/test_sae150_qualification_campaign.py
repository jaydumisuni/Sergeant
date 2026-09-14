from __future__ import annotations
import json, subprocess
from pathlib import Path
from main_review.genesis_qualification import (
 ACCEPTED_EXTERNAL_SOURCE_CLASSES, LANE_CARDINALITY_FLOOR, LANE_SOURCE_CLASS_FLOOR, PROVEN_NODE_BINDING_KINDS,
 REQUIRED_MUTATIONS, REQUIRED_NODES, REQUIRED_PROVEN_NODE_BINDINGS, REQUIRED_QUALIFICATION_OBLIGATIONS, SPIKE_EXT_CLOSEOUT_MANIFEST,
)
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"docs/161-sae150-genesis-qualification-candidate-manifest.json"
SPIKE_EXT_SOURCING=ROOT/"docs/65-spike-ext-external-review-sourcing-feasibility-manifest.json"

def _git(*args): return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()
def _ensure_commit(ref):
 try: subprocess.check_call(["git","cat-file","-e",f"{ref}^{{commit}}"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError: subprocess.check_call(["git","fetch","--no-tags","--depth","1","origin",ref],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def test_required_inventory_and_dependency_generations_are_bound():
 m=json.loads(MANIFEST.read_text())
 for rel in m["required_surfaces"]: assert (ROOT/rel).is_file()
 assert set(m["proof_requires"])==set(REQUIRED_NODES)
 assert m["proof_requires"]==REQUIRED_PROVEN_NODE_BINDINGS
 assert set(m["required_mutation_families"])==set(REQUIRED_MUTATIONS)
 assert m["external_evidence_contract"]["record_type"]=="ExternalEvidenceProvenanceRecord"
 assert m["external_evidence_contract"]["package_boolean_claims_authoritative"] is False

def test_prerequisite_bindings_are_typed_and_resolve_in_git():
 m=json.loads(MANIFEST.read_text())
 assert m["proof_requires_object_kinds"]==PROVEN_NODE_BINDING_KINDS
 for node,oid in REQUIRED_PROVEN_NODE_BINDINGS.items():
  if PROVEN_NODE_BINDING_KINDS[node]=="commit": _ensure_commit(oid); assert _git("cat-file","-t",oid)=="commit"
 spike=m["spike_ext_binding"]
 assert spike=={"kind":"blob","path":SPIKE_EXT_CLOSEOUT_MANIFEST,"blob":REQUIRED_PROVEN_NODE_BINDINGS["SPIKE-EXT"],"anchored_at":m["base_main"]}
 _ensure_commit(m["base_main"])
 assert _git("rev-parse",f'{m["base_main"]}:{SPIKE_EXT_CLOSEOUT_MANIFEST}')==spike["blob"]
 assert _git("hash-object",SPIKE_EXT_CLOSEOUT_MANIFEST)==spike["blob"]

def test_lane_floor_is_anchored_to_spike_ext_not_candidate_authored():
 proposal=json.loads(SPIKE_EXT_SOURCING.read_text())
 cardinality=proposal["cardinality_proposal"]; classes={row["id"] for row in proposal["source_classes"]}
 assert LANE_CARDINALITY_FLOOR==cardinality["minimum"] and LANE_SOURCE_CLASS_FLOOR==cardinality["minimum_distinct_source_classes"]
 assert cardinality["excluded_source_class_for_cardinality_purposes"] not in ACCEPTED_EXTERNAL_SOURCE_CLASSES
 assert set(ACCEPTED_EXTERNAL_SOURCE_CLASSES)==classes-{cardinality["excluded_source_class_for_cardinality_purposes"]}

def test_manifest_records_repaired_authority_contract():
 m=json.loads(MANIFEST.read_text()); c=m["external_evidence_contract"]
 assert c["provenance_rederived_through_canonical_eepr_constructor"] is True
 assert c["trusted_provenance_verifiers_supplied_outside_package"] is True
 assert c["direct_record_construction_authoritative"] is False
 assert c["lane_cardinality_floor"]=={"minimum_instances":LANE_CARDINALITY_FLOOR,"minimum_distinct_source_classes":LANE_SOURCE_CLASS_FLOOR}
 assert c["accepted_source_classes"]==list(ACCEPTED_EXTERNAL_SOURCE_CLASSES) and c["lane_cardinality_ratified"] is False
 q=m["qualification_obligation_contract"]
 assert q["required_obligations"]==list(REQUIRED_QUALIFICATION_OBLIGATIONS) and q["caller_boolean_claims_authoritative"] is False
 assert q["surviving_required_mutant_blocks"] is True
 assert m["residual_unknown_policy"]=={"every_residual_unknown_blocks":True,"unknown_independence_conserved":True}
 assert m["package_identity"]=={"record_type":"GenesisQualificationPackage","full_package_digest":True}

def test_current_candidate_fails_closed_on_real_external_lane_gap():
 m=json.loads(MANIFEST.read_text())
 assert m["lifecycle_state"]=="GENESIS_PROVISIONAL"
 assert m["mandatory_independent_lane"]["required"] is True
 assert m["mandatory_independent_lane"]["currently_satisfied"] is False
 assert {"MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE","GENESIS_LANE_CARDINALITY_UNRATIFIED","EXTERNAL_PROVENANCE_VERIFIER_UNROOTED"}<=set(m["mandatory_independent_lane"]["open_blockers"])
 assert m["candidate_merge_authorized"] is False
 assert m["authority_gain"]=="none" and m["genesis_activated"] is False

def test_spike_ext_proven_artifact_itself_records_open_external_gap():
 assert _git("hash-object",SPIKE_EXT_CLOSEOUT_MANIFEST)==REQUIRED_PROVEN_NODE_BINDINGS["SPIKE-EXT"]
 spike=json.loads((ROOT/SPIKE_EXT_CLOSEOUT_MANIFEST).read_text())
 assert spike["lifecycle_state"]=="PROVEN"
 assert spike["sourcing_disposition"]["status"]=="OPEN_GAP"
 assert spike["sourcing_disposition"]["genesis_external_lane_satisfied"] is False
