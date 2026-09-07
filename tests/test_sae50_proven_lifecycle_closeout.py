from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/101-sae50-proven-lifecycle-closeout-manifest.json"
CANDIDATE = ROOT / "docs/99-sae50-total-closure-candidate-manifest.json"
DOC = ROOT / "docs/100-sae50-proven-lifecycle-closeout.md"
ROADMAP = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_sae50_closeout_advances_only_the_frozen_candidate() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    assert candidate["node"] == "SAE-50"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert candidate["produces_now"] == []
    assert closeout["node"] == "SAE-50"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["produces"] == ["QUALIFIED_SET_VALUED_CLOSURE_CORE"]
    assert closeout["normal_verdict_authority"] is False
    assert closeout["dependent_nodes_auto_proven"] is False


def test_exact_candidate_merge_and_authority_blobs_are_bound() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    generation = closeout["candidate_generation"]
    assert generation["pull_request"] == 190
    assert generation["head"] == "69c3e0dca33f42cf725c2301cd39800cb1be1783"
    assert generation["tree"] == "9a35e4d279839c19dd11b414ac2add547ae5800b"
    assert generation["candidate_manifest_blob"] == "3429dc8796cf96d58aef6dee51e41a58acbfb5a7"
    for path, expected in candidate["content_blobs"].items():
        assert blob(ROOT / path) == expected
    merge = closeout["canonical_candidate_merge"]
    assert merge["commit"] == "ef0a94f968eae5aecd60954f8b67b87bcb5886cb"
    assert merge["tree"] == generation["tree"]
    assert merge["parents"] == [
        "535699dc5952f5309eaa843098b21457439af706",
        generation["head"],
    ]
    assert merge["exact_head_guard"] == generation["head"]


def test_execution_and_hostile_review_gate_are_preserved() -> None:
    closeout = load(MANIFEST)
    proof = closeout["candidate_execution_confirmation"]
    assert proof["exact_head"] == "69c3e0dca33f42cf725c2301cd39800cb1be1783"
    assert proof["ci_run_id"] == 34112836393
    assert proof["main_review_run_id"] == 34112836449
    assert proof["ci"] == "success"
    assert proof["main_review"] == "success"
    assert proof["clean_clone_proof"] == "success"
    assert all(proof["hostile_regressions"].values())
    assert closeout["hostile_review_confirmation"]["all_inline_review_threads_resolved_before_candidate_merge"] is True


def test_dependency_law_and_authority_boundary_remain_narrow() -> None:
    closeout = load(MANIFEST)
    assert closeout["proof_requires"] == ["SAE-10", "SAE-20", "SAE-40"]
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "### SAE-50 — Total Coverage + Total Set-Valued Closure Core" in roadmap
    assert "Produces `QUALIFIED_SET_VALUED_CLOSURE_CORE`." in roadmap
    boundary = closeout["authority_boundary"]
    assert boundary["genesis_activated"] is False
    assert boundary["semantic_capability_auto_qualified"] is False
    assert boundary["contract_instance_closure_auto_qualified"] is False
    assert boundary["rust_kernel_auto_qualified"] is False
    assert boundary["partial_generation_activation_allowed"] is False


def test_closeout_artifacts_are_content_bound_and_documented() -> None:
    closeout = load(MANIFEST)
    assert blob(DOC) == closeout["closeout_document_blob"]
    text = DOC.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text
    assert "QUALIFIED_SET_VALUED_CLOSURE_CORE" in text
    assert "does not rewrite the historical candidate" in text
