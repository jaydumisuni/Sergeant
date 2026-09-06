from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT_MANIFEST_PATH = ROOT / "docs/77-spike-sem-proven-lifecycle-closeout-manifest.json"
CANDIDATE_MANIFEST_PATH = ROOT / "docs/75-spike-sem-feasibility-manifest.json"
CLOSEOUT_DOC_PATH = ROOT / "docs/76-spike-sem-proven-lifecycle-closeout.md"
SAE00_MANIFEST_PATH = ROOT / "docs/67-sae00-proven-lifecycle-closeout-manifest.json"
ROADMAP_PATH = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tracked_blob(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def test_spike_sem_closeout_advances_new_generation_without_rewriting_candidate() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    candidate = _load(CANDIDATE_MANIFEST_PATH)

    assert candidate["node"] == "SPIKE-SEM"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert closeout["node"] == "SPIKE-SEM"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["authority_gain"] == "none"
    assert closeout["proof_requires"] == ["SAE-00"]
    assert closeout["candidate_generation"]["historical_candidate_preserved_not_rewritten"] is True


def test_spike_sem_closeout_binds_reviewed_candidate_and_spike_only_artifacts() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    candidate = closeout["candidate_generation"]

    assert candidate["pull_request"] == 175
    assert candidate["head"] == "6c213a29bcc78ba80d2107ee28692faad931a58f"
    for name in ("candidate_document", "candidate_manifest", "probe", "probe_proof", "candidate_manifest_proof"):
        entry = candidate[name]
        assert _tracked_blob(ROOT / entry["path"]) == entry["blob_sha"]

    assert candidate["production_main_review_modified"] is False
    assert candidate["probe_production_authority"] is False


def test_spike_sem_closeout_requires_proven_sae00_roadmap_execution_authority() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    sae00 = _load(SAE00_MANIFEST_PATH)
    authority = closeout["sae00_proven_authority"]

    assert sae00["node"] == "SAE-00"
    assert sae00["lifecycle_state"] == "PROVEN"
    assert authority["required_output"] == "ROADMAP_EXECUTION_AUTHORITY"
    assert authority["required_output"] in sae00["produces"]


def test_spike_sem_closeout_preserves_withdrawn_and_corrected_measurements() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    withdrawn = closeout["measurement_history"]["withdrawn_first_measurement"]
    corrected = closeout["measurement_history"]["corrected_measurement"]

    assert withdrawn["authority_status"] == "WITHDRAWN"
    assert withdrawn["github_actions_run_id"] == 33615685272
    assert withdrawn["unknown"] == 0

    assert corrected["discovery_head"] == "6f47c742ffae3bf624e4147a15c0271ea435d3a9"
    assert corrected["discovery_github_actions_run_id"] == 33619547519
    assert corrected["files_parsed"] == 136
    assert corrected["operations_used"] == 924042
    assert corrected["operation_ceiling"] == 2000000
    assert corrected["total_relations"] == 14439
    assert corrected["grades"] == {
        "EXACT": 2528,
        "CONSERVATIVE_SUPERSET": 3,
        "PARTIAL": 2008,
        "UNKNOWN": 9900,
    }
    assert corrected["rates"]["UNKNOWN"] == 0.6856430500727198
    assert corrected["rates"]["UNKNOWN"] > corrected["rates"]["EXACT"]
    assert corrected["parse_error_count"] == 0
    assert corrected["budget_exceeded"] is False


def test_spike_sem_hostile_review_and_candidate_execution_are_proven() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    review = closeout["hostile_review_disposition"]
    execution = closeout["candidate_execution_confirmation"]

    assert review["all_threads_resolved"] is True
    assert review["unresolved_calls_explicit_unknown"] is True
    assert review["lexical_shadowing_prevents_false_exact"] is True
    assert review["candidate_expansion_charged_to_operation_budget"] is True
    assert review["first_measurement_withdrawn"] is True

    assert execution["exact_head"] == "6c213a29bcc78ba80d2107ee28692faad931a58f"
    assert execution["github_actions_run_id"] == 33619792730
    assert execution["full_suite"] == {
        "passed": 1108,
        "xfailed": 1,
        "failed": 0,
        "historical_xfail_only": True,
    }
    assert execution["clean_clone_proof"] == "success"
    assert len(execution["sergeant_cli_gates"]) >= 10


def test_spike_sem_bootstrap_authority_is_bounded_and_not_semantic_authority() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    bootstrap = closeout["bootstrap_authority"]
    semantic = closeout["semantic_authority_boundary"]

    assert bootstrap["kind"] == "SAE00_ROADMAP_EXECUTION_PLUS_OWNER_ROOT_CONSTITUTIONAL_TCB"
    assert bootstrap["not_general_qualification_authority"] is True
    assert bootstrap["cannot_qualify_other_nodes"] is True
    assert bootstrap["cannot_activate_acr_domain"] is True
    assert bootstrap["cannot_create_capability_passport"] is True
    assert bootstrap["cannot_convert_unknown_to_pass"] is True
    assert bootstrap["partial_generation_activation_allowed"] is False

    assert semantic["production_semantic_analyzer_created"] is False
    assert semantic["acr_domain_activated"] is False
    assert semantic["capability_passport_created"] is False
    assert semantic["current_sergeant_verdict_authority_changed"] is False


def test_spike_sem_closeout_resolves_only_its_sae60_dependency() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    dependency = closeout["dependency_effect"]
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

    assert "### SAE-60 — Semantic Capability Qualification Foundation" in roadmap
    assert "**Proof requires:** `SAE-20`, `SAE-30`, `SAE-50`, `SPIKE-SEM`." in roadmap
    assert dependency["spike_sem_proof_dependency_resolved"] is True
    assert dependency["sae60_spike_sem_prerequisite_available"] is True
    assert dependency["sae60_remaining_proof_requires"] == ["SAE-20", "SAE-30", "SAE-50"]
    assert dependency["sae60_auto_qualified"] is False
    assert dependency["sae60_auto_proven"] is False
    assert dependency["sae20_auto_qualified"] is False
    assert dependency["partial_generation_activation_allowed"] is False


def test_spike_sem_closeout_artifacts_are_content_bound() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    document = closeout["closeout_document"]
    proof = closeout["proof_fixture"]

    assert _tracked_blob(ROOT / document["path"]) == document["blob_sha"]
    assert _tracked_blob(ROOT / proof["path"]) == proof["blob_sha"]

    text = CLOSEOUT_DOC_PATH.read_text(encoding="utf-8")
    assert "PROVEN FEASIBILITY; NO PRODUCTION SEMANTIC OR ACR AUTHORITY" in text
    assert "68.56% UNKNOWN" in text
    assert "6c213a29bcc78ba80d2107ee28692faad931a58f" in text
