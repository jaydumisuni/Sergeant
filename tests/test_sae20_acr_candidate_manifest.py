from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/83-sae20-acr-authoring-audit-candidate-manifest.json"

BASE = "e4cd5af49823a97451a998a3ae553a1cefb2d97d"
SAE00_CLOSEOUT = "5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910"


def _load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", path], cwd=ROOT, text=True).strip()


def test_sae20_candidate_lifecycle_and_dependency_boundary() -> None:
    m = _load()
    assert m["node"] == "SAE-20"
    assert m["lifecycle_state"] == "CANDIDATE"
    assert m["candidate_revision"] == 2
    assert m["construction_base"] == BASE
    assert m["proof_requires"] == ["SAE-00"]
    assert m["sae00_proven_authority"]["closeout_merge"] == SAE00_CLOSEOUT
    assert m["normal_verdict_authority"] is False
    assert m["produces_now"] == []
    assert m["produces_if_proven"] == ["QUALIFIED_ACR_FOUNDATION"]


def test_sae20_candidate_binds_every_declared_content_blob() -> None:
    m = _load()
    for path, expected in m["content_blobs"].items():
        assert _blob(path) == expected, path


def test_sae20_candidate_binds_frozen_authority_blobs() -> None:
    m = _load()
    for entry in m["authority_sources"].values():
        assert _blob(entry["path"]) == entry["blob_sha"]


def test_sae20_candidate_does_not_self_qualify_or_fabricate_sae30() -> None:
    b = _load()["qualification_boundary"]
    assert b["candidate_self_qualification_allowed"] is False
    assert b["audit_clean_means_qualified"] is False
    assert b["sae30_qualification_authority_fabricated"] is False
    assert b["genesis_activated"] is False
    assert b["dependent_nodes_auto_qualified"] is False
    assert b["dependent_nodes_auto_proven"] is False


def test_sae20_candidate_authoring_attack_roster_is_complete() -> None:
    attacks = set(_load()["authoring_audit_attack_families"])
    required = {
        "applicability_omission",
        "applicability_semantics_weakening",
        "semantic_carrier_omission",
        "consumer_interpretation_omission",
        "affected_relation_omission",
        "collection_semantics_or_cardinality_weakening",
        "closure_grade_weakening",
        "premise_omission",
        "repeated_authority_premise_omission",
        "obligation_omission",
        "material_input_omission",
        "coherence_rule_omission",
        "temporal_rule_omission",
        "falsifier_family_omission",
        "independence_rule_omission",
        "external_review_lane_cardinality_weakening",
        "negative_applicability_burden_missing",
        "unknown_fallback_weakening",
        "candidate_self_qualification",
        "audit_scope_mismatch",
        "noncanonical_contract",
        "noncanonical_profile",
        "mutable_generation_alias",
    }
    assert required <= attacks


def test_sae20_candidate_records_internal_review_without_laundering_independence() -> None:
    review = _load()["internal_hostile_review"]
    assert review["independence_disposition"] == "NOT_INDEPENDENT"
    assert review["candidate_revision_before_review"] == 1
    assert review["candidate_revision_after_correction"] == 2
    assert review["qualification_credit"] is False
    assert len(review["defects_corrected"]) >= 4


def test_sae20_candidate_local_proof_is_historical_and_focused_only() -> None:
    proof = _load()["local_construction_proof"]
    assert proof["initial_production_tests_passed"] == 34
    assert proof["initial_production_tests_failed"] == 0
    assert proof["post_review_repository_audit_tests_passed"] == 24
    assert proof["post_review_focused_hardening_tests_passed"] == 11
    assert proof["post_review_correction_harness_total_passed"] == 35
    assert proof["post_review_correction_harness_tests_failed"] == 0
    assert proof["corrected_audit_compile_proof"] == "pass"
    assert proof["repository_wide_proof_claimed"] is False
