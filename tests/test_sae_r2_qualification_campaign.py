from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRUCTURAL = ROOT / "rust/sergeant-assurance-kernel/tests/structural_authority.rs"
MANIFEST = ROOT / "docs/121-sae-r2-proven-lifecycle-closeout-manifest.json"
ROADMAP = ROOT / "docs/superpowers/plans/2026-09-07-sae-30-through-100.md"


def _blob(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=ROOT, text=True
    ).strip()


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_task16_required_qualification_campaign_artifact_exists():
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "### Task 16: SAE-R2 PROVEN Closeout" in roadmap
    assert "tests/test_sae_r2_qualification_campaign.py" in roadmap
    assert Path(__file__).name == "test_sae_r2_qualification_campaign.py"


def test_frozen_rust_campaign_covers_required_hostile_qualification_attacks():
    campaign = STRUCTURAL.read_text(encoding="utf-8")
    required_attacks = {
        "fabricated qualification": "fn fabricated_qualification_is_rejected",
        "unauthorized issuer": "fn unauthorized_qualification_issuer_is_rejected",
        "incomplete collection": "fn incomplete_collection_is_rejected",
        "duplicate set member": "fn duplicated_member_cannot_fake_exact_set_closure",
        "wrong generation": "fn wrong_generation_authority_is_rejected",
        "revoked authority": "fn revoked_authority_is_rejected",
        "missing attestation": "fn missing_attestation_is_rejected",
        "review world/RAB/scope drift": "fn review_world_must_bind_exact_rab_and_scope",
        "proof/falsifier obligation drift": "fn proof_world_and_falsifier_frontier_must_bind_expected_authority",
        "closure certificate/source drift": "fn closure_certificates_must_bind_collection_and_source_basis",
        "external provenance cardinality": "fn external_provenance_cardinality_is_exact",
    }
    missing = [name for name, marker in required_attacks.items() if marker not in campaign]
    assert not missing, f"qualification campaign lost hostile cases: {missing}"


def test_closeout_manifest_binds_exact_frozen_qualification_campaign_blob():
    manifest = _manifest()
    candidate = manifest["candidate_generation"]
    assert candidate["structural_campaign_blob"] == _blob(STRUCTURAL)
    assert candidate["head"] == "c38dd512ddcb2d8c759d034a1d1c32b9b572b10f"
    assert manifest["canonical_candidate_merge"]["commit"] == "cc3168f6a5b49a5b4c4d49303a0bd5fb35e7b335"
    assert manifest["candidate_proof_identity"]["verdict"] == "APPROVE"
    assert manifest["candidate_proof_identity"]["required_actions"] == []


def test_qualified_scope_is_not_weaker_than_the_frozen_structural_campaign():
    scope = _manifest()["qualified_scope"]
    required_true = (
        "structural_authority_records_required",
        "qualification_attestations_registry_derived",
        "exact_unique_collection_closure_required",
        "review_world_rab_scope_binding_required",
        "closure_certificate_subject_source_binding_required",
        "contract_instance_obligation_authority_chain_required",
        "capability_passport_registry_binding_required",
        "proof_world_review_world_obligation_binding_required",
        "falsifier_expected_obligation_binding_required",
        "external_provenance_cardinality_unique_required",
        "current_generation_required",
        "revocation_rejected",
        "python_expected_list_authority_rejected",
        "shared_implementation_claim_rejected",
    )
    assert all(scope[key] is True for key in required_true)
    assert scope["unknown_conservation"] == "fail_closed"


def test_repair_does_not_rewrite_frozen_candidate_or_grant_new_authority():
    manifest = _manifest()
    assert manifest["node"] == "SAE-R2"
    assert manifest["lifecycle_state"] == "PROVEN"
    assert manifest["produces"] == ["QUALIFIED_RUST_ASSURANCE_KERNEL"]
    assert manifest["normal_verdict_authority"] is False
    assert manifest["genesis_activated"] is False
    assert manifest["dependent_nodes_auto_proven"] is False
    assert manifest["partial_generation_activation"] is False
