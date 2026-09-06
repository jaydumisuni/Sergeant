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
        ["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def test_spike_sem_manifest_is_bounded_candidate_with_no_authority_gain() -> None:
    manifest = _load(MANIFEST_PATH)
    assert manifest["schema_version"] == "sergeant.spike-sem-feasibility-manifest.v2"
    assert manifest["node"] == "SPIKE-SEM"
    assert manifest["node_title"] == "Real semantic qualification / false-UNKNOWN feasibility"
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert manifest["proof_requires"] == ["SAE-00"]
    assert manifest["authority_gain"] == "none"
    assert manifest["existing_production_mechanism"]["modified_by_spike"] is False
    assert manifest["probe"]["production_authority"] is False


def test_spike_sem_manifest_binds_candidate_document_probe_proof_and_baseline() -> None:
    manifest = _load(MANIFEST_PATH)
    for entry_name in ("candidate_document", "probe", "proof_fixture"):
        entry = manifest[entry_name]
        assert _tracked_blob(ROOT / entry["path"]) == entry["blob_sha"]
    baseline = manifest["existing_production_mechanism"]
    assert _tracked_blob(ROOT / baseline["path"]) == baseline["blob_sha"]


def test_spike_sem_dependency_and_required_construct_charter_match_frozen_roadmap() -> None:
    manifest = _load(MANIFEST_PATH)
    sae00 = _load(SAE00_MANIFEST_PATH)
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    assert sae00["node"] == "SAE-00"
    assert sae00["lifecycle_state"] == "PROVEN"
    assert "### SPIKE-SEM — Real semantic qualification / false-UNKNOWN feasibility" in roadmap
    assert "Probe at least ordinary direct calls" in roadmap
    assert "Measure EXACT cases" in roadmap
    assert "SPIKE-SEM: [SAE-00]" in roadmap
    assert all(manifest["required_constructs"].values())


def test_spike_sem_review_hardened_synthetic_matrix_is_frozen() -> None:
    matrix = _load(MANIFEST_PATH)["synthetic_required_matrix"]
    assert matrix["total_relations"] == 12
    assert matrix["grades"] == {
        "EXACT": 6,
        "CONSERVATIVE_SUPERSET": 0,
        "PARTIAL": 2,
        "UNKNOWN": 4,
    }
    assert matrix["rates"] == {
        "EXACT": 0.5,
        "CONSERVATIVE_SUPERSET": 0.0,
        "PARTIAL": 0.16666666666666666,
        "UNKNOWN": 0.3333333333333333,
    }
    assert matrix["budget_exceeded"] is False
    assert matrix["parse_error_count"] == 0


def test_spike_sem_withdraws_first_measurement_and_binds_corrected_discovery() -> None:
    manifest = _load(MANIFEST_PATH)
    invalid = manifest["invalidated_measurement"]
    corrected = manifest["corrected_real_sergeant_measurement"]

    assert invalid["discovery_head"] == "3667561baf731482d76be10a38c7cfa1ef54f2b5"
    assert invalid["discovery_github_actions_run_id"] == 33615685272
    assert invalid["authority_status"] == "WITHDRAWN"
    assert invalid["grades"]["UNKNOWN"] == 0
    assert "unresolved calls were omitted" in invalid["reason"]

    assert corrected["status"] == "FROZEN_FROM_SINGLE_SENTINEL_DISCOVERY"
    assert corrected["discovery_head"] == "6f47c742ffae3bf624e4147a15c0271ea435d3a9"
    assert corrected["discovery_github_actions_run_id"] == 33619547519
    assert corrected["discovery_test_result"] == {
        "passed": 1107,
        "failed": 1,
        "xfailed": 1,
        "sole_failure": "test_real_sergeant_main_review_semantic_metrics_are_frozen_from_observation",
    }
    assert corrected["files_parsed"] == 136
    assert corrected["operations_used"] == 924042
    assert corrected["total_relations"] == 14439
    assert corrected["grades"] == {
        "EXACT": 2528,
        "CONSERVATIVE_SUPERSET": 3,
        "PARTIAL": 2008,
        "UNKNOWN": 9900,
    }
    assert corrected["parse_error_count"] == 0
    assert corrected["budget_exceeded"] is False


def test_spike_sem_hostile_review_controls_have_execution_reproof() -> None:
    manifest = _load(MANIFEST_PATH)
    hostile = manifest["hostile_review"]
    findings = hostile["findings"]
    probe = manifest["probe"]
    resource = manifest["resource_behavior"]

    assert hostile["execution_reproof_head"] == "6f47c742ffae3bf624e4147a15c0271ea435d3a9"
    assert hostile["execution_reproof_github_actions_run_id"] == 33619547519
    assert hostile["candidate_green_reproof_pending"] is True
    assert findings["unresolved_calls_omitted_from_denominator"]["severity"] == "P1"
    assert findings["lexical_shadowing_false_exact"]["severity"] == "P2"
    assert findings["candidate_expansion_not_budgeted"]["severity"] == "P2"
    assert all(item["valid"] is True for item in findings.values())
    assert all(item["implemented"] is True for item in findings.values())
    assert all(item["execution_reproof_pending"] is False for item in findings.values())

    assert probe["every_python_call_classified"] is True
    assert probe["candidate_expansion_charged_to_budget"] is True
    assert probe["lexical_shadowing_fails_closed"] is True
    assert probe["ambiguous_module_rebinding_fails_closed"] is True
    assert resource["candidate_expansion_exhaustion_fixture_emits_unknown"] is True
    assert resource["main_review_operations_used"] == 924042
    assert resource["main_review_budget_exceeded"] is False


def test_spike_sem_false_positive_pressure_remains_bounded_microcase() -> None:
    pressure = _load(MANIFEST_PATH)["false_positive_pressure"]
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

    for value in (
        "unresolved_calls",
        "lexical_shadowing",
        "ambiguous_module_rebinding",
        "dynamic_getattr",
        "dynamic_dispatch_keys",
        "runtime_generated_target_configuration",
        "resource_budget_exhaustion",
    ):
        assert value in non_exact["UNKNOWN"]
    assert "framework_callback_registration_without_qualified_framework_invocation_semantics" in non_exact["PARTIAL"]
    assert "unresolved_receiver_attribute_name_candidate_sets" in non_exact["CONSERVATIVE_SUPERSET"]
    assert "do_not_omit_unresolved_calls_to_improve_unknown_rate" in prohibitions
    assert "do_not_ignore_candidate_expansion_in_resource_accounting" in prohibitions
    assert "do_not_reuse_invalidated_first_measurement" in prohibitions
    assert "No current Sergeant verdict" in text
