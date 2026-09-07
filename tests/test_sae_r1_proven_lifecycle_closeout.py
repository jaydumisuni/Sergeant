from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from main_review.rust_identity_vectors import RustIdentityError, require_authority_id


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/97-sae-r1-proven-lifecycle-closeout-manifest.json"
CANDIDATE = ROOT / "docs/95-sae-r1-rust-canonical-identity-candidate-manifest.json"
DOC = ROOT / "docs/96-sae-r1-proven-lifecycle-closeout.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_r1_closeout_advances_only_the_frozen_candidate() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    assert candidate["node"] == "SAE-R1"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert candidate["produces_now"] == []
    assert closeout["node"] == "SAE-R1"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["produces"] == ["QUALIFIED_RUST_IDENTITY_FOUNDATION"]
    assert closeout["normal_verdict_authority"] is False
    assert closeout["dependent_nodes_auto_proven"] is False


def test_exact_candidate_merge_and_frozen_blobs_are_bound() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    generation = closeout["candidate_generation"]
    assert generation["pull_request"] == 189
    assert generation["head"] == "a53e4ee9cc73f325e1c5f81387638b0762359f77"
    assert generation["candidate_manifest_blob"] == "381dce7367f6546dc5babb7c793a2d60c67f20a8"
    for path, expected in candidate["content_blobs"].items():
        assert blob(ROOT / path) == expected
    merge = closeout["canonical_candidate_merge"]
    assert merge["commit"] == "54b37d33674efcd986a07df6d7ccaa03a01025c4"
    assert merge["tree"] == "b53a5e99771fefa88c7e726c8678c530648b3b21"
    assert merge["parents"] == [
        "81801ec06ddbcebb3b986a6d434b6ccdcbe7a3cc",
        generation["head"],
    ]
    assert merge["exact_head_guard"] == generation["head"]


def test_candidate_and_post_merge_execution_proofs_are_preserved() -> None:
    closeout = load(MANIFEST)
    proof = closeout["candidate_execution_confirmation"]
    assert proof["exact_head"] == "a53e4ee9cc73f325e1c5f81387638b0762359f77"
    assert proof["ci_run_id"] == 34114064133
    assert proof["main_review_run_id"] == 34114064048
    assert proof["sae_rust_proof_run_id"] == 34114064108
    assert proof["multiplatform_run_id"] == 34114064085
    assert proof["ci"] == proof["main_review"] == proof["sae_rust_proof"] == proof["multiplatform"] == "success"
    post = closeout["post_merge_execution_confirmation"]
    assert post["canonical_merge"] == "54b37d33674efcd986a07df6d7ccaa03a01025c4"
    assert post["completed_push_workflows"] == 5
    assert post["successful_push_workflows"] == 5


def test_identity_foundation_has_no_shared_implementation_bridge() -> None:
    candidate = load(CANDIDATE)
    assert candidate["independence"] == {
        "shared_implementation": False,
        "shared_frozen_specification_vectors": True,
        "rust_third_party_dependencies": False,
        "python_and_rust_both_checked_against_exact_frozen_bytes": True,
        "focused_python_proofs_executed_by_rust_workflow": True,
    }
    cargo = (ROOT / "rust/sergeant-assurance-identity/Cargo.toml").read_text(encoding="utf-8")
    assert cargo.strip().endswith("[dependencies]")
    rust = (ROOT / "rust/sergeant-assurance-identity/src/lib.rs").read_text(encoding="utf-8").lower()
    assert "pyo3" not in rust
    assert "std::process" not in rust
    assert "command::new" not in rust


def test_truncated_and_noncanonical_authority_ids_fail_closed() -> None:
    valid = "a" * 64
    assert require_authority_id(valid) == valid
    for invalid in (valid[:-1], valid + "a", "A" * 64, "g" * 64, "0x" + valid):
        with pytest.raises(RustIdentityError, match="full lowercase 64-hex"):
            require_authority_id(invalid)


def test_closeout_artifacts_are_content_bound_and_documented() -> None:
    closeout = load(MANIFEST)
    assert blob(DOC) == closeout["closeout_document_blob"]
    assert blob(Path(__file__)) == closeout["closeout_test_blob"]
    text = DOC.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text
    assert "QUALIFIED_RUST_IDENTITY_FOUNDATION" in text
    assert "does not grant Rust verdict authority" in text
