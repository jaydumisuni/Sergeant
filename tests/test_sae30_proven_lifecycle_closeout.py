from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/93-sae30-proven-lifecycle-closeout-manifest.json"
CANDIDATE = ROOT / "docs/91-sae30-qualification-provenance-genesis-candidate-manifest.json"
DOC = ROOT / "docs/92-sae30-proven-lifecycle-closeout.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_sae30_closeout_advances_only_the_frozen_candidate() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    assert candidate["node"] == "SAE-30"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert candidate["produces_now"] == []
    assert closeout["node"] == "SAE-30"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["produces"] == [
        "QUALIFICATION_PROVENANCE_SUBSTRATE",
        "GENESIS_AUTHORITY_SUBSTRATE",
        "OWNER_RISK_SEPARATION_SUBSTRATE",
    ]
    assert closeout["normal_verdict_authority"] is False
    assert closeout["dependent_nodes_auto_proven"] is False


def test_exact_candidate_and_guarded_merge_are_bound() -> None:
    closeout = load(MANIFEST)
    candidate = closeout["candidate_generation"]
    assert candidate["pull_request"] == 188
    assert candidate["head"] == "efa5dd06411c8767ce78faed89fc2383874fe823"
    assert candidate["candidate_manifest_blob"] == "886882a51715781c50e63a2579dbeb48cd1907e1"
    merge = closeout["canonical_candidate_merge"]
    assert merge["commit"] == "81801ec06ddbcebb3b986a6d434b6ccdcbe7a3cc"
    assert merge["tree"] == "593b6253cc367a976b1cf393ce03fa748a43ee28"
    assert merge["parents"] == [
        "9cc8bc7247c804b8ba4c2f3b81a9e078bf210727",
        candidate["head"],
    ]
    assert merge["exact_head_guard"] == candidate["head"]


def test_candidate_authority_blobs_and_hostile_findings_remain_frozen() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    for path, expected in candidate["content_blobs"].items():
        assert blob(ROOT / path) == expected
    expected_findings = {
        "issuer_authentication_not_copyable_payload",
        "qualification_requires_closed_verifier_proof",
        "positive_independence_requires_authenticated_provenance",
        "external_census_excludes_ineligible_records",
        "sae170_gate_is_load_bearing",
        "issuer_suspension_revocation_and_registry_currentness",
    }
    assert set(candidate["hostile_review_findings_closed_by_candidate"]) == expected_findings
    assert set(closeout["hostile_review_confirmation"]["closed_findings"]) == expected_findings
    assert closeout["hostile_review_confirmation"]["all_inline_review_threads_resolved_before_candidate_merge"] is True


def test_execution_gate_and_dependency_law_are_preserved() -> None:
    closeout = load(MANIFEST)
    proof = closeout["candidate_execution_confirmation"]
    assert proof["exact_head"] == "efa5dd06411c8767ce78faed89fc2383874fe823"
    assert proof["ci_run_id"] == 34113914294
    assert proof["main_review_run_id"] == 34113914365
    assert proof["multiplatform_run_id"] == 34113914325
    assert proof["ci"] == proof["main_review"] == proof["multiplatform"] == "success"
    assert closeout["proof_requires"] == ["SAE-00", "SPIKE-ID", "SPIKE-EXT"]


def test_genesis_and_owner_authority_boundaries_remain_narrow() -> None:
    closeout = load(MANIFEST)
    boundary = closeout["authority_boundary"]
    assert boundary["genesis_activated"] is False
    assert boundary["sae170_exit_authority_preserved"] is True
    assert boundary["business_risk_can_become_engineering_pass"] is False
    assert boundary["semantic_capability_auto_qualified"] is False
    assert boundary["partial_generation_activation_allowed"] is False


def test_closeout_artifacts_are_content_bound_and_documented() -> None:
    closeout = load(MANIFEST)
    assert blob(DOC) == closeout["closeout_document_blob"]
    assert blob(Path(__file__)) == closeout["closeout_test_blob"]
    text = DOC.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text
    assert "does **not** activate Genesis" in text
    assert "QUALIFICATION_PROVENANCE_SUBSTRATE" in text
