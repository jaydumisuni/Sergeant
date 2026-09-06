from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT_MANIFEST_PATH = ROOT / "docs/73-spike-id-proven-lifecycle-closeout-manifest.json"
CANDIDATE_MANIFEST_PATH = ROOT / "docs/71-spike-id-feasibility-manifest.json"
CLOSEOUT_DOC_PATH = ROOT / "docs/72-spike-id-proven-lifecycle-closeout.md"
SAE00_MANIFEST_PATH = ROOT / "docs/67-sae00-proven-lifecycle-closeout-manifest.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tracked_blob(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{relative}"],
        cwd=ROOT,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def test_spike_id_closeout_advances_new_generation_without_rewriting_candidate() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    candidate = _load(CANDIDATE_MANIFEST_PATH)

    assert candidate["node"] == "SPIKE-ID"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert closeout["node"] == "SPIKE-ID"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["authority_gain"] == "none"
    assert closeout["proof_requires"] == ["SAE-00"]
    assert all(closeout["required_outputs"].values())
    assert closeout["reconciled_candidate"]["historical_candidate_preserved_not_rewritten"] is True


def test_spike_id_closeout_binds_current_candidate_and_closeout_document() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    candidate = closeout["reconciled_candidate"]
    closeout_doc = closeout["closeout_document"]

    assert re.fullmatch(r"[0-9a-f]{40}", candidate["head"])
    assert _tracked_blob(ROOT / candidate["document"]) == candidate["document_blob_sha"]
    assert _tracked_blob(ROOT / candidate["manifest"]) == candidate["manifest_blob_sha"]
    assert _tracked_blob(ROOT / closeout_doc["path"]) == closeout_doc["blob_sha"]

    text = CLOSEOUT_DOC_PATH.read_text(encoding="utf-8")
    assert candidate["head"] in text
    assert "PROVEN FEASIBILITY" in text
    assert "NOT SAE-30 QUALIFICATION AUTHORITY" in text


def test_spike_id_closeout_requires_proven_sae00_roadmap_execution_authority() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    sae00 = _load(SAE00_MANIFEST_PATH)
    authority = closeout["sae00_proven_authority"]

    assert sae00["node"] == "SAE-00"
    assert sae00["lifecycle_state"] == "PROVEN"
    assert authority["required_output"] == "ROADMAP_EXECUTION_AUTHORITY"
    assert authority["required_output"] in sae00["produces"]


def test_spike_id_selected_mechanism_remains_feasibility_not_sae30_authority() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    mechanism = closeout["selected_initial_mechanism"]
    bootstrap = closeout["bootstrap_authority"]

    assert mechanism["qualified_for_sae30"] is False
    assert mechanism["production_authority_created"] is False
    assert mechanism["real_issuer_key_created"] is False
    assert mechanism["real_qualification_authority_registry_created"] is False
    assert mechanism["signature_authenticity_establishes_independence"] is False

    assert bootstrap["not_general_qualification_authority"] is True
    assert bootstrap["cannot_issue_qualification_attestation"] is True
    assert bootstrap["cannot_qualify_other_nodes"] is True
    assert bootstrap["cannot_establish_external_independence"] is True
    assert bootstrap["cannot_satisfy_genesis"] is True
    assert bootstrap["cannot_convert_business_risk_to_pass"] is True
    assert bootstrap["partial_generation_activation_allowed"] is False


def test_spike_id_hostile_findings_are_recorded_as_closed_controls() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    disposition = closeout["hostile_review_disposition"]

    assert disposition["p1_threads_dispositioned_and_resolved"] is True
    assert disposition["expiry_exact_boundary_fail_closed"] is True
    assert disposition["future_issued_rejected"] is True
    assert disposition["payload_issuer_identity_matches_authenticated_identity"] is True
    assert disposition["issuer_generation_comes_from_verifier_trusted_registry"] is True
    assert disposition["compromised_generation_self_relabel_attack_rejected"] is True
    assert disposition["frozen_roadmap_dependency_assertion_corrected"] is True
    assert disposition["historical_sae00_candidate_count_not_reinterpreted_as_current_tree_law"] is True
    assert disposition["sae00_lineage_proof_shallow_checkout_safe"] is True


def test_spike_id_execution_confirmation_is_exact_head_supporting_evidence() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    execution = closeout["execution_confirmation"]
    suite = execution["full_suite"]

    assert execution["exact_head"] == closeout["reconciled_candidate"]["head"]
    assert execution["github_actions_run_id"] == 33614531989
    assert suite == {
        "passed": 1083,
        "xfailed": 1,
        "failed": 0,
        "historical_xfail_only": True,
    }
    assert execution["clean_clone_proof"] == "success"
    assert execution["actions_required_for_authority"] is False
    assert len(execution["sergeant_cli_gates"]) >= 10


def test_spike_id_closeout_keeps_sae30_and_genesis_closed() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    dependency = closeout["dependency_effect"]
    gaps = set(closeout["known_sae30_obligations"])

    assert dependency["spike_id_proof_dependency_resolved"] is True
    assert dependency["spike_ext_already_proven"] is True
    assert dependency["sae30_feasibility_spike_prerequisites_available"] is True
    assert dependency["sae30_auto_qualified"] is False
    assert dependency["sae30_auto_proven"] is False
    assert dependency["genesis_auto_unblocked"] is False
    assert dependency["partial_generation_activation_allowed"] is False

    assert "real_qualification_authority_registry" in gaps
    assert "eepr_external_source_identity_control_lineage_and_independence" in gaps
    assert "judge_admitted_qualification_evidence_root_binding" in gaps


def test_spike_id_closeout_proof_fixture_is_content_bound() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    proof = closeout["proof_fixture"]

    assert proof["blob_sha"] != "PENDING_BIND_AFTER_FIXTURE_CREATION"
    assert _tracked_blob(ROOT / proof["path"]) == proof["blob_sha"]
