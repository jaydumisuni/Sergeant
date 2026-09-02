from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/75-spike-sem-feasibility-manifest.json"
DOC_PATH = ROOT / "docs/74-spike-sem-semantic-feasibility.md"
SAE00_MANIFEST_PATH = ROOT / "docs/67-sae00-proven-lifecycle-closeout-manifest.json"
ROADMAP_PATH = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"


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


def test_spike_sem_manifest_is_bounded_candidate_with_no_authority_gain() -> None:
    manifest = _load(MANIFEST_PATH)

    assert manifest["schema_version"] == "sergeant.spike-sem-feasibility-manifest.v1"
    assert manifest["node"] == "SPIKE-SEM"
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert manifest["proof_requires"] == ["SAE-00"]
    assert manifest["authority_gain"] == "none"
    assert manifest["existing_production_mechanism"]["modified_by_spike"] is False
    assert manifest["probe"]["assurance_evolution_runtime_implementation"] is False
    assert manifest["probe"]["production_authority"] is False


def test_spike_sem_manifest_binds_candidate_document_probe_and_current_baseline() -> None:
    manifest = _load(MANIFEST_PATH)

    candidate = manifest["candidate_document"]
    probe = manifest["probe"]
    proof = manifest["proof_fixture"]
    baseline = manifest["existing_production_mechanism"]

    assert _tracked_blob(ROOT / candidate["path"]) == candidate["blob_sha"]
    assert _tracked_blob(ROOT / probe["path"]) == probe["blob_sha"]
    assert _tracked_blob(ROOT / proof["path"]) == proof["blob_sha"]
    assert _tracked_blob(ROOT / baseline["path"]) == baseline["blob_sha"]


def test_spike_sem_dependency_and_required_construct_charter_match_frozen_roadmap() -> None:
    manifest = _load(MANIFEST_PATH)
    sae00 = _load(SAE00_MANIFEST_PATH)
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

    assert sae00["node"] == "SAE-00"
    assert sae00["lifecycle_state"] == "PROVEN"
    assert "### SPIKE-SEM — Semantic-analysis feasibility and UNKNOWN-rate study" in roadmap
    assert "Probe at least ordinary direct calls" in roadmap
    assert "Measure EXACT cases" in roadmap
    assert "SPIKE-SEM: [SAE-00]" in roadmap
    assert all(manifest["required_constructs"].values())


def test_spike_sem_synthetic_matrix_proves_exact_partial_unknown_and_budget_behavior() -> None:
    manifest = _load(MANIFEST_PATH)
    matrix = manifest["synthetic_required_matrix"]
    resource = manifest["resource_behavior"]

    assert matrix["total_relations"] == 10
    assert matrix["grades"] == {
        "EXACT": 6,
        "CONSERVATIVE_SUPERSET": 0,
        "PARTIAL": 2,
        "UNKNOWN": 2,
    }
    assert matrix["rates"] == {
        "EXACT": 0.6,
        "CONSERVATIVE_SUPERSET": 0.0,
        "PARTIAL": 0.2,
        "UNKNOWN": 0.2,
    }
    assert matrix["budget_exceeded"] is False
    assert resource["explicit_exhaustion_fixture_emits_unknown"] is True
    assert resource["universal_budget_sufficiency_claimed"] is False


def test_spike_sem_real_sergeant_measurement_is_exactly_recoverable() -> None:
    manifest = _load(MANIFEST_PATH)
    measured = manifest["real_sergeant_measurement"]

    assert measured["discovery_head"] == "3667561baf731482d76be10a38c7cfa1ef54f2b5"
    assert measured["discovery_github_actions_run_id"] == 33615685272
    assert measured["discovery_test_result"] == {
        "passed": 1096,
        "failed": 1,
        "xfailed": 1,
        "expected_single_failure": "test_real_sergeant_main_review_semantic_metrics_are_frozen_from_observation",
        "purpose": "mechanically expose fresh metrics before freezing them",
    }
    assert measured["files_parsed"] == 136
    assert measured["states_visited"] == 225231
    assert measured["total_relations"] == 4539
    assert measured["grades"] == {
        "EXACT": 2528,
        "CONSERVATIVE_SUPERSET": 3,
        "PARTIAL": 2008,
        "UNKNOWN": 0,
    }
    assert measured["parse_error_count"] == 0
    assert measured["budget_exceeded"] is False


def test_spike_sem_false_positive_pressure_is_bounded_to_adversarial_microcase() -> None:
    manifest = _load(MANIFEST_PATH)
    pressure = manifest["false_positive_pressure"]

    assert pressure["production_baseline_reported_callers"] == 2
    assert pressure["ground_truth_callers"] == 1
    assert pressure["false_positive_callers"] == 1
    assert pressure["adversarial_reported_set_false_positive_rate"] == 0.5
    assert pressure["universal_real_world_rate_claimed"] is False
    assert "not eligible" in pressure["result"]


def test_spike_sem_recommendation_keeps_unclosed_constructs_non_exact() -> None:
    manifest = _load(MANIFEST_PATH)
    non_exact = manifest["non_exact_domain_recommendation"]
    prohibitions = set(manifest["prohibitions"])
    text = DOC_PATH.read_text(encoding="utf-8")

    assert "dynamic_getattr" in non_exact["UNKNOWN"]
    assert "dynamic_dispatch_keys" in non_exact["UNKNOWN"]
    assert "runtime_generated_target_configuration" in non_exact["UNKNOWN"]
    assert "resource_budget_exhaustion" in non_exact["UNKNOWN"]
    assert "framework_callback_registration_without_qualified_framework_invocation_semantics" in non_exact["PARTIAL"]
    assert "unresolved_receiver_attribute_name_candidate_sets" in non_exact["CONSERVATIVE_SUPERSET"]

    assert "do_not_promote_bare_name_call_graph_correlation_to_exact_semantics" in prohibitions
    assert "do_not_lower_dynamic_or_unclosed_constructs_below_unknown_to_improve_coverage" in prohibitions
    assert "do_not_claim_zero_unknown_in_current_corpus_means_universal_dynamic_coverage" in prohibitions
    assert "No current Sergeant verdict" in text
