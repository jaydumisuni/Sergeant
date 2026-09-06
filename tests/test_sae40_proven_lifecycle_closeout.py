from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/89-sae40-proven-lifecycle-closeout-manifest.json"
CANDIDATE = ROOT / "docs/87-sae40-judge-assurance-ledger-candidate-manifest.json"
DOC = ROOT / "docs/88-sae40-proven-lifecycle-closeout.md"
QUAL = ROOT / "tests/test_sae40_qualification_campaign.py"
SAE10 = ROOT / "docs/81-sae10-proven-lifecycle-closeout-manifest.json"
SAE20 = ROOT / "docs/85-sae20-proven-lifecycle-closeout-manifest.json"
ROADMAP = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"

HEAD = "c910b7a08e7b33c5ec69cb115affc044aed4df8e"
TREE = "bd267e4fd1578f7df3d33befb1a4a18b2dcbcb9a"
MERGE = "ac88df42983274163e939ee0211ee0ab7b51b356"
MERGE_TREE = "bd267e4fd1578f7df3d33befb1a4a18b2dcbcb9a"
PREVIOUS_MAIN = "2a1d16f9772997d993d0f0d41e1c5161f222f136"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def blob(path: Path) -> str:
    return git("rev-parse", f"HEAD:{path.relative_to(ROOT).as_posix()}")


def available(commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def test_lifecycle_advances_without_rewriting_candidate_generation() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    assert candidate["node"] == "SAE-40"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert candidate["produces_now"] == []
    assert candidate["produces_if_proven"] == ["QUALIFIED_ASSURANCE_LEDGER"]
    assert closeout["node"] == "SAE-40"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["normal_verdict_authority"] is False
    assert closeout["produces"] == ["QUALIFIED_ASSURANCE_LEDGER"]
    assert closeout["candidate_generation"]["historical_candidate_preserved_not_rewritten"] is True


def test_exact_candidate_artifacts_and_production_semantics_are_content_bound() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)
    generation = closeout["candidate_generation"]
    assert generation["pull_request"] == 180
    assert generation["head"] == HEAD
    assert generation["tree"] == TREE
    assert blob(CANDIDATE) == generation["candidate_manifest"]["blob_sha"]
    assert generation["candidate_manifest"]["blob_sha"] == "5a068f44432cd7784d8f97e3be0f1b849ac2bb96"
    for path, expected in candidate["content_blobs"].items():
        assert blob(ROOT / path) == expected
    assert generation["authority_implementation_blobs"] == {
        "main_review/assurance_ledger.py": "93c9528f107679cd1c844937a925a461c8df07c8",
        "main_review/judge_assurance_adapter.py": "522b01881894e2acf5898a32964c04303b585307",
    }
    for path, expected in generation["authority_implementation_blobs"].items():
        assert blob(ROOT / path) == expected


def test_candidate_execution_proof_is_exact_head_and_artifact_bound() -> None:
    evidence = load(MANIFEST)["candidate_execution_confirmation"]
    expected = {"passed": 1388, "xfailed": 2, "failed": 0, "historical_xfails_only": True}
    assert evidence["exact_head"] == HEAD
    assert evidence["ci_run_id"] == 34035737232
    assert evidence["full_suite"] == expected
    assert evidence["clean_clone_suite"] == expected
    assert evidence["clean_clone_proof"] == "success"
    assert evidence["pytest_artifact_digest"] == "sha256:0c2ed796220f21072753fb53d4ddcb6141bd6302d32befb20c028565939d23db"
    assert evidence["clean_clone_artifact_digest"] == "sha256:257a68c1ebb6994ebf606f4a4397df3e5ee2cfb8cb05b606f947470379b7e5c5"
    assert evidence["live_battle_artifact_digest"] == "sha256:a6162cc92eb368fb6656abcd555b0c013677cec61caef70051f7bc4e6ef3d97b"
    assert evidence["main_review_run_id"] == 34035737201
    assert evidence["main_review"] == "success"
    assert evidence["main_review_artifact_digest"] == "sha256:ee747f2d9a84ab6b1e883a53e8ce5fd34a35f25f44045e469c140362114a4ccf"
    assert all(evidence["clean_clone_proof_steps"].values())


def test_hostile_review_history_is_preserved_and_current_threads_closed() -> None:
    candidate = load(CANDIDATE)
    review = load(MANIFEST)["hostile_review_confirmation"]
    assert review["reviewed_head"] == HEAD
    assert review["coderabbit_exact_head_status"] == "success"
    assert review["all_inline_review_threads_resolved_before_candidate_merge"] is True
    assert review["historical_red_generations"] == candidate["hostile_review"]["red_generations"]
    assert review["historical_green_correction_generations"] == candidate["hostile_review"]["green_correction_generations"]
    assert review["historical_external_findings_suppressed"] is False
    assert review["external_independence_claimed"] is False


def test_qualification_campaign_is_bounded_and_content_bound() -> None:
    qualification = load(MANIFEST)["assurance_ledger_qualification_campaign"]
    assert qualification["fixture_path"] == "tests/test_sae40_qualification_campaign.py"
    assert blob(QUAL) == qualification["fixture_blob_sha"]
    for key in (
        "presentation_alias_non_authority_attack",
        "claim_and_admission_occurrence_multiplicity_attack",
        "unknown_conservation_attack",
        "contradiction_conservation_attack",
        "world_rab_scope_substitution_attack",
        "cross_world_and_rab_merge_attack",
        "persisted_tamper_and_dangling_link_attack",
        "malformed_authority_input_attack",
        "adapter_alias_reorder_attack",
        "judge_metadata_leak_attack",
        "orphan_disposition_attack",
        "assurance_status_gate_mismatch_attack",
    ):
        assert qualification[key] is True
    assert qualification["project_authored_campaign_is_external_independence"] is False
    assert qualification["universal_semantic_completeness_claimed"] is False
    assert qualification["dependent_nodes_auto_qualified"] is False


def test_guarded_candidate_merge_is_exact_and_ancestry_preserved() -> None:
    merge = load(MANIFEST)["canonical_candidate_merge"]
    assert merge == {
        "commit": MERGE,
        "tree": MERGE_TREE,
        "parents": [PREVIOUS_MAIN, HEAD],
        "exact_head_guard": HEAD,
        "merge_method": "merge_commit",
    }
    assert re.fullmatch(r"[0-9a-f]{40}", MERGE)
    text = DOC.read_text(encoding="utf-8")
    for identity in (HEAD, TREE, MERGE, MERGE_TREE, PREVIOUS_MAIN):
        assert identity in text
    if available(MERGE):
        assert git("show", "-s", "--format=%T", MERGE) == MERGE_TREE
        assert git("show", "-s", "--format=%P", MERGE).split() == [PREVIOUS_MAIN, HEAD]
        subprocess.check_call(["git", "merge-base", "--is-ancestor", MERGE, "HEAD"], cwd=ROOT)
    else:
        assert git("rev-parse", "--is-shallow-repository") == "true"


def test_proven_dependencies_match_frozen_roadmap_without_auto_proving_dependents() -> None:
    manifest = load(MANIFEST)
    sae10 = load(SAE10)
    sae20 = load(SAE20)
    assert manifest["proof_requires"] == ["SAE-10", "SAE-20"]
    assert "QUALIFIED_REVIEW_WORLD_CONTRACT" in sae10["produces"]
    assert "QUALIFIED_RAB_CONTRACT" in sae10["produces"]
    assert "QUALIFIED_ACR_FOUNDATION" in sae20["produces"]
    assert "**Proof requires:** `SAE-10`, `SAE-20`." in ROADMAP.read_text(encoding="utf-8")
    effect = manifest["dependency_effect"]
    assert effect["sae40_proof_dependencies_resolved"] is True
    assert effect["qualified_assurance_ledger_available_after_canonical_closeout_merge"] is True
    assert effect["sae_r1_auto_qualified"] is False
    assert effect["sae50_auto_qualified"] is False
    assert effect["dependent_nodes_auto_proven"] is False


def test_authority_boundary_does_not_escalate_closeout_or_separate_workflow_debt() -> None:
    manifest = load(MANIFEST)
    boundary = manifest["authority_boundary"]
    assert boundary["normal_sergeant_verdict_authority_changed"] is False
    assert boundary["second_judge_created"] is False
    assert boundary["sae30_general_qualification_authority_fabricated"] is False
    assert boundary["eepr_independence_claimed"] is False
    assert boundary["genesis_activated"] is False
    assert boundary["partial_generation_activation_allowed"] is False
    assert boundary["model_free_transfer_failures_counted_as_sae40_pass"] is False
    debt = manifest["separate_repository_debt"]
    assert debt["issue"] == 181
    assert debt["scope"] == "inherited Model-Free Transfer workflow failures"
    assert debt["resolved_by_sae40"] is False


def test_closeout_artifacts_are_content_bound_and_documented() -> None:
    manifest = load(MANIFEST)
    assert blob(DOC) == manifest["closeout_document"]["blob_sha"]
    assert blob(ROOT / manifest["proof_fixture"]["path"]) == manifest["proof_fixture"]["blob_sha"]
    text = DOC.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text
    assert "QUALIFIED_ASSURANCE_LEDGER" in text
    assert "no production-semantic change" in text
    assert "does not claim universal semantic completeness" in text
    assert "issue `#181`" in text
