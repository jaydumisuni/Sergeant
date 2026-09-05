from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/83-sae20-acr-authoring-audit-candidate-manifest.json"
BASE = "e4cd5af49823a97451a998a3ae553a1cefb2d97d"
SAE00_CLOSEOUT = "5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910"
PREVIOUS_HEAD = "61f82eaa14478c409d684017663edccf6ee311e8"

def _load() -> dict: return json.loads(MANIFEST.read_text(encoding="utf-8"))
def _blob(path: str) -> str: return subprocess.check_output(["git", "hash-object", path], cwd=ROOT, text=True).strip()

def test_sae20_candidate_lifecycle_and_dependency_boundary() -> None:
    m=_load(); assert m["node"]=="SAE-20" and m["lifecycle_state"]=="CANDIDATE" and m["construction_base"]==BASE
    assert m["proof_requires"]==["SAE-00"] and m["sae00_proven_authority"]["closeout_merge"]==SAE00_CLOSEOUT
    assert m["normal_verdict_authority"] is False and m["produces_now"]==[] and m["produces_if_proven"]==["QUALIFIED_ACR_FOUNDATION"]

def test_sae20_candidate_binds_every_declared_content_blob() -> None:
    for path,expected in _load()["content_blobs"].items(): assert _blob(path)==expected,path

def test_sae20_candidate_binds_frozen_authority_blobs() -> None:
    for entry in _load()["authority_sources"].values(): assert _blob(entry["path"])==entry["blob_sha"]

def test_sae20_candidate_does_not_self_qualify_or_fabricate_sae30() -> None:
    b=_load()["qualification_boundary"]; assert b["candidate_self_qualification_allowed"] is False; assert b["audit_clean_means_qualified"] is False; assert b["sae30_qualification_authority_fabricated"] is False; assert b["genesis_activated"] is False; assert b["dependent_nodes_auto_qualified"] is False; assert b["dependent_nodes_auto_proven"] is False

def test_sae20_candidate_authoring_attack_roster_is_complete() -> None:
    attacks=set(_load()["authoring_audit_attack_families"])
    required={"profile_noncanonical_or_malformed","audit_scope_mismatch","applicability_omission","applicability_semantics_mismatch","semantic_carrier_omission","consumer_interpretation_omission","affected_relation_omission","collection_semantics_or_cardinality_weakening","closure_grade_weakening","premise_omission","premise_closure_grade_weakening","repeated_authority_premise_omission","obligation_omission","obligation_closure_grade_weakening","material_input_omission","material_input_closure_grade_weakening","coherence_rule_omission","temporal_rule_omission","falsifier_family_omission","independence_rule_omission","external_review_lane_cardinality_weakening","negative_applicability_burden_missing","unknown_fallback_weakening","candidate_self_qualification","contract_noncanonical_or_malformed","bound_subject_variables_mismatch","admissible_proof_classes_mismatch","permitted_capabilities_mismatch"}
    assert required<=attacks

def test_sae20_second_hostile_correction_semantics_are_explicit() -> None:
    s=_load()["foundation_semantics"]
    for key in ("authoring_profile_canonically_validated_before_use","authoring_profile_binds_exact_contract_generation","frozen_json_maps_validate_sorted_unique_keys","runtime_unsupported_applicability_yields_unknown","applicability_json_equality_type_sensitive","one_shot_authority_iterables_materialized_once"):
        assert s[key] is True

def test_sae20_candidate_local_proof_is_historical_construction_evidence_only() -> None:
    p=_load()["local_construction_proof"]
    assert p["second_correction_tests_passed"]==64 and p["second_correction_tests_failed"]==0 and p["second_correction_fresh_regressions_added"]==6
    assert p["second_correction_compile_proof"]=="pass" and p["coercive_persistence_scan"]=="no_str_int_bool_coercion_sites"
    assert p["previous_exact_head"]==PREVIOUS_HEAD and p["previous_exact_head_ci_passed"]==1324 and p["previous_exact_head_ci_xfailed"]==2
    assert p["previous_exact_head_clean_clone_proof"]=="pass" and p["previous_exact_head_main_review"]=="pass"
    assert p["repository_wide_proof_claimed_for_current_generation"] is False
