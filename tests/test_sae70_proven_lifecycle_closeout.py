from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/109-sae70-proven-lifecycle-closeout-manifest.json"
CANDIDATE = ROOT / "docs/107-sae70-contract-obligation-closure-candidate-manifest.json"
DOC = ROOT / "docs/108-sae70-proven-lifecycle-closeout.md"
CAMPAIGN = ROOT / "tests/test_sae70_qualification_campaign.py"
PROTOCOL = ROOT / "main_review/contract_closure_protocol.py"
ROADMAP = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_sae70_closeout_advances_only_the_frozen_candidate_authority() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)

    assert candidate["node"] == closeout["node"] == "SAE-70"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert candidate["produces_now"] == []
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["produces"] == [
        "QUALIFIED_CONTRACT_INSTANCE_CLOSURE",
        "QUALIFIED_EXPECTED_OBLIGATION_COMPILER",
    ]
    assert closeout["normal_verdict_authority"] is False
    assert closeout["genesis_activated"] is False
    assert closeout["dependent_nodes_auto_proven"] is False
    assert closeout["partial_generation_activation"] is False


def test_exact_candidate_and_guarded_candidate_merge_are_bound() -> None:
    closeout = load(MANIFEST)
    generation = closeout["candidate_generation"]
    merge = closeout["canonical_candidate_merge"]

    assert generation["pull_request"] == 196
    assert generation["head"] == "9f6f5b9800e0143f4614a904b780f3767305eb12"
    assert generation["tree"] == "c2c8a2482b5b8ffbbeb1e8f9f9f4d3bcb39ccef4"
    assert generation["candidate_document_blob"] == "04d453a619337b475ce5c7d2e34aa9933372fd54"
    assert generation["candidate_manifest_blob"] == "19976a9e39b6277ac82ce164b486bdc5507076ed"

    assert merge["commit"] == "281b97c94fb77693d9c9df89b6a4ef67896185c0"
    assert merge["tree"] == generation["tree"]
    assert merge["parents"] == [
        "6d4ecc03782fa72d517e0b111a3757e4b2f65cf0",
        generation["head"],
    ]
    assert merge["exact_head_guard"] == generation["head"]


def test_historical_candidate_content_remains_unchanged() -> None:
    candidate = load(CANDIDATE)
    for path, expected in candidate["content_blobs"].items():
        assert blob(ROOT / path) == expected
    assert blob(ROOT / candidate["candidate_document"]) == candidate["candidate_document_blob"]
    assert blob(CANDIDATE) == "19976a9e39b6277ac82ce164b486bdc5507076ed"


def test_qualification_hardening_is_separate_and_content_bound() -> None:
    closeout = load(MANIFEST)
    hardening = closeout["qualification_hardening_generation"]

    assert hardening["red_head"] == "f85613d003ae7803311eeda4afc3fbbe364f46d4"
    assert hardening["red_ci_run_id"] == 34135393353
    assert hardening["red_qualification_failures"] == 10
    assert hardening["red_existing_passes"] == 1523
    assert hardening["red_historical_xfails"] == 2
    assert hardening["head"] == "8a25dbd69e9498b38c6f3f137e8140313a04a335"
    assert hardening["tree"] == "b2828cad58cb8bbc034582798f7ba8992208e381"
    assert hardening["qualification_protocol_generation"] == "sae70-qualification-v1"
    assert hardening["protocol_blob"] == blob(PROTOCOL)
    assert hardening["qualification_campaign_blob"] == blob(CAMPAIGN)
    assert hardening["candidate_compiler_rewritten"] is False


def test_hardening_execution_confirmation_is_exact_head_and_green() -> None:
    proof = load(MANIFEST)["hardening_execution_confirmation"]
    assert proof["exact_head"] == "8a25dbd69e9498b38c6f3f137e8140313a04a335"
    assert proof["ci_run_id"] == 34135754332
    assert proof["main_review_run_id"] == 34135754341
    assert proof["multiplatform_run_id"] == 34135754385
    assert proof["review_intelligence_run_id"] == 34135754371
    assert proof["reviewer_comparison_run_id"] == 34135754345
    assert proof["standalone_service_run_id"] == 34135754411
    assert proof["live_github_ingestion_run_id"] == 34135754259
    assert proof["final_static_transfer_holdout_run_id"] == 34135754195
    assert proof["clean_clone_full_chain"] == "success"
    assert proof["all_triggered_model_free_workflows"] == "success"
    for key, value in proof.items():
        if key.endswith("_run_id") or key in {
            "exact_head",
            "clean_clone_full_chain",
            "all_triggered_model_free_workflows",
        }:
            continue
        assert value == "success"


def test_qualification_scope_requires_exact_canonical_recomputation() -> None:
    closeout = load(MANIFEST)
    scope = closeout["qualified_scope"]

    assert scope["mandatory_contract_census_total"] is True
    assert scope["unknown_conserved"] is True
    assert scope["false_requires_proven_no_match"] is True
    assert scope["contract_instances_explicit_and_content_bound"] is True
    assert scope["expected_obligations_conservative_union"] is True
    assert scope["all_obligation_provenance_preserved"] is True
    assert scope["qualification_requires_canonical_recomputation"] is True
    assert scope["qualification_requires_exact_closure"] is True
    assert scope["historical_registry_replay_allowed"] is False
    assert scope["first_match_weakening_allowed"] is False


def test_closeout_artifacts_dependency_law_and_authority_boundary_are_bound() -> None:
    closeout = load(MANIFEST)

    assert closeout["proof_requires"] == ["SAE-20", "SAE-50", "SAE-60"]
    assert blob(DOC) == closeout["closeout_document_blob"]
    assert blob(Path(__file__)) == closeout["proof_fixture"]["blob_sha"]
    assert blob(CAMPAIGN) == closeout["qualification_campaign_blob"]
    assert blob(PROTOCOL) == closeout["qualification_protocol_blob"]

    text = DOC.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text
    assert "QUALIFIED_CONTRACT_INSTANCE_CLOSURE" in text
    assert "QUALIFIED_EXPECTED_OBLIGATION_COMPILER" in text
    assert "does **not**" in text
    assert "activate Genesis" in text
    assert "prove or activate SAE-80" in text

    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "### SAE-70" in roadmap
    assert "QUALIFIED_CONTRACT_INSTANCE_CLOSURE" in roadmap
    assert "QUALIFIED_EXPECTED_OBLIGATION_COMPILER" in roadmap
