from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/81-sae10-proven-lifecycle-closeout-manifest.json"
CANDIDATE_MANIFEST_PATH = ROOT / "docs/79-sae10-review-world-rab-manifest.json"
CLOSEOUT_DOC_PATH = ROOT / "docs/80-sae10-proven-lifecycle-closeout.md"
SAE00_MANIFEST_PATH = ROOT / "docs/67-sae00-proven-lifecycle-closeout-manifest.json"
ROADMAP_PATH = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"

FINAL_CANDIDATE_HEAD = "d442013caf0c411362b54a2efcd339f4cc63ed9f"
CANDIDATE_MERGE = "65b5a34e23a42d5ade97ae7483ff1feae204e311"
SAE00_PROVEN_MERGE = "5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def _tracked_blob(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return _git("rev-parse", f"HEAD:{relative}")


def _commit_available(commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def test_sae10_closeout_advances_new_generation_without_rewriting_candidate() -> None:
    closeout = _load(MANIFEST_PATH)
    candidate = _load(CANDIDATE_MANIFEST_PATH)

    assert candidate["node"] == "SAE-10"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert closeout["node"] == "SAE-10"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["candidate_generation"]["historical_candidate_preserved_not_rewritten"] is True
    assert closeout["normal_verdict_authority"] is False


def test_sae10_closeout_binds_exact_candidate_artifacts() -> None:
    closeout = _load(MANIFEST_PATH)
    candidate = closeout["candidate_generation"]

    assert candidate["pull_request"] == 176
    assert candidate["head"] == FINAL_CANDIDATE_HEAD
    for key in ("candidate_document", "candidate_manifest", "candidate_manifest_proof", "hostile_regression_proof"):
        entry = candidate[key]
        assert _tracked_blob(ROOT / entry["path"]) == entry["blob_sha"]
    for path, expected in candidate["authority_implementation_blobs"].items():
        assert _tracked_blob(ROOT / path) == expected


def test_sae10_candidate_execution_and_hostile_review_are_exact() -> None:
    closeout = _load(MANIFEST_PATH)
    execution = closeout["candidate_execution_confirmation"]
    review = closeout["hostile_review_confirmation"]

    assert execution["exact_head"] == FINAL_CANDIDATE_HEAD
    assert execution["ci_run_id"] == 33861996272
    assert execution["full_suite"] == {
        "passed": 1258,
        "xfailed": 2,
        "failed": 0,
        "historical_xfails_only": True,
    }
    assert execution["clean_clone_proof"] == "success"
    assert execution["main_review_run_id"] == 33861996153
    assert execution["main_review"] == "pass"
    assert execution["focused_collection"] == 143
    assert execution["production_dependency_surface"] == {"passed": 129, "failed": 0, "xfailed": 0}

    assert review["owner_root_exact_head_review_id"] == 5111777001
    assert review["owner_root_review_kind"] == "COMMENT"
    assert review["owner_root_actionable_findings"] == 0
    assert review["coderabbit_targeted_verification_comment_id"] == 3933013210
    assert review["coderabbit_targeted_verification_disposition"] == "last_disputed_finding_does_not_apply"
    assert review["full_exact_head_coderabbit_review_submission"] is None
    assert review["full_exact_head_coderabbit_review_fabricated"] is False
    assert review["all_inline_review_threads_resolved"] is True


def test_sae10_closeout_binds_exact_candidate_head_to_canonical_merge() -> None:
    closeout = _load(MANIFEST_PATH)
    merge_commit = closeout["canonical_candidate_merge"]["commit"]
    candidate_head = closeout["canonical_candidate_merge"]["exact_head_guard"]
    text = CLOSEOUT_DOC_PATH.read_text(encoding="utf-8")

    assert merge_commit == CANDIDATE_MERGE
    assert candidate_head == FINAL_CANDIDATE_HEAD
    assert re.fullmatch(r"[0-9a-f]{40}", merge_commit)
    assert re.fullmatch(r"[0-9a-f]{40}", candidate_head)
    assert merge_commit in text
    assert candidate_head in text

    if _commit_available(merge_commit) and _commit_available(candidate_head):
        parents = _git("show", "-s", "--format=%P", merge_commit).split()
        assert candidate_head in parents
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", merge_commit, "HEAD"], cwd=ROOT
        )
        return

    assert _git("rev-parse", "--is-shallow-repository") == "true"


def test_sae10_closeout_requires_proven_sae00_roadmap_authority() -> None:
    closeout = _load(MANIFEST_PATH)
    sae00 = _load(SAE00_MANIFEST_PATH)
    authority = closeout["sae00_proven_authority"]

    assert sae00["node"] == "SAE-00"
    assert sae00["lifecycle_state"] == "PROVEN"
    assert authority["merge_commit"] == SAE00_PROVEN_MERGE
    assert authority["required_output"] == "ROADMAP_EXECUTION_AUTHORITY"
    assert authority["required_output"] in sae00["produces"]


def test_sae10_bootstrap_and_outputs_are_bounded() -> None:
    closeout = _load(MANIFEST_PATH)
    bootstrap = closeout["bootstrap_authority"]
    boundary = closeout["authority_boundary"]

    assert bootstrap["kind"] == "SAE00_ROADMAP_EXECUTION_PLUS_OWNER_ROOT_CONSTITUTIONAL_TCB"
    assert bootstrap["not_general_qualification_authority"] is True
    assert bootstrap["cannot_qualify_dependents"] is True
    assert bootstrap["cannot_satisfy_genesis_external_lane"] is True
    assert bootstrap["cannot_convert_business_risk_to_pass"] is True
    assert bootstrap["partial_generation_activation_allowed"] is False
    assert closeout["produces"] == [
        "QUALIFIED_REVIEW_WORLD_CONTRACT",
        "QUALIFIED_RAB_CONTRACT",
    ]
    assert boundary == {
        "normal_sergeant_verdict_authority_changed": False,
        "candidate_self_activation_allowed": False,
        "sae30_general_qualification_authority_fabricated": False,
        "genesis_activated": False,
        "partial_generation_activation_allowed": False,
    }


def test_sae10_dependency_effect_matches_frozen_roadmap() -> None:
    closeout = _load(MANIFEST_PATH)
    effect = closeout["dependency_effect"]
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

    assert "### SAE-10 — Review World + Review Authority Bundle" in roadmap
    assert "Produces `QUALIFIED_REVIEW_WORLD_CONTRACT` and `QUALIFIED_RAB_CONTRACT`." in roadmap
    assert "### SAE-20 — Assurance Contract Registry + Authoring Audit" in roadmap
    assert "**Proof requires:** `SAE-00`." in roadmap

    assert effect["sae10_proof_dependency_resolved"] is True
    assert effect["qualified_review_world_contract_available"] is True
    assert effect["qualified_rab_contract_available"] is True
    assert effect["sae20_auto_qualified"] is False
    assert effect["sae20_auto_proven"] is False
    assert effect["dependent_nodes_auto_qualified"] is False
    assert effect["dependent_nodes_auto_proven"] is False
    assert effect["partial_generation_activation_allowed"] is False


def test_sae10_closeout_artifacts_are_content_bound_and_documented() -> None:
    closeout = _load(MANIFEST_PATH)
    text = CLOSEOUT_DOC_PATH.read_text(encoding="utf-8")

    for key in ("closeout_document", "proof_fixture"):
        entry = closeout[key]
        assert _tracked_blob(ROOT / entry["path"]) == entry["blob_sha"]

    assert "Status: **PROVEN**" in text
    assert FINAL_CANDIDATE_HEAD in text
    assert CANDIDATE_MERGE in text
    assert "no full exact-`d442013...` CodeRabbit review submission" in text
    assert "QUALIFIED_REVIEW_WORLD_CONTRACT" in text
    assert "QUALIFIED_RAB_CONTRACT" in text
    assert "No normal Sergeant verdict authority transfers" in text
