from __future__ import annotations

import json
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/79-sae10-review-world-rab-manifest.json'
DOC = ROOT / 'docs/78-sae10-review-world-rab-contract.md'
HISTORICAL_SPIKE_FIXTURE = Path('tests/spike_sem/test_semantic_feasibility_probe.py')
EXPECTED_CONTENT_BLOBS = {
    'docs/78-sae10-review-world-rab-contract.md',
    'docs/superpowers/plans/2026-09-02-sae-10-review-world-rab.md',
    'main_review/review_authority_bundle.py',
    'main_review/review_world.py',
    'main_review/review_world_currentness.py',
    'main_review/review_world_git.py',
    'tests/conftest.py',
    'tests/test_review_authority_bundle.py',
    'tests/test_review_world_currentness.py',
    'tests/test_review_world_git.py',
    'tests/test_review_world_identity.py',
    'tests/test_review_world_persistence.py',
    'tests/test_sae10_hostile_matrix.py',
    'tests/test_spike_sem_historical_metric_supersession.py',
    'tests/test_sae10_review_world_rab_manifest.py',
}
EXPECTED_EXTERNAL_AUTHORITY_BLOBS = {
    'docs/58-sergeant-assurance-evolution-founding-architecture.md',
    'docs/59-sergeant-assurance-evolution-roadmap.md',
    'docs/66-sae00-proven-lifecycle-closeout.md',
    'docs/67-sae00-proven-lifecycle-closeout-manifest.json',
    'docs/75-spike-sem-feasibility-manifest.json',
    'docs/77-spike-sem-proven-lifecycle-closeout-manifest.json',
    'docs/superpowers/specs/2026-09-02-sae-10-review-world-rab-design.md',
    'tests/spike_sem/test_semantic_feasibility_probe.py',
}

def _load() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding='utf-8'))

def _repo_path(value: str | Path) -> Path:
    pure = PurePosixPath(str(value))
    if pure.is_absolute() or '..' in pure.parts:
        raise AssertionError(f'non-repository manifest path: {value!r}')
    resolved = (ROOT / Path(*pure.parts)).resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved

def blob(path: str | Path) -> str:
    return subprocess.run(['git', 'hash-object', str(_repo_path(path))], text=True, capture_output=True, check=True).stdout.strip()

def _assert_exact_blob_bindings(bindings: object, expected_paths: set[str], *, blob_fn=blob) -> None:
    assert isinstance(bindings, dict)
    assert set(bindings) == expected_paths
    for path, expected in bindings.items():
        assert blob_fn(path) == expected

def test_candidate_manifest_lifecycle_and_dependency():
    manifest = _load()
    assert manifest['schema_version'] == 'sergeant.sae10-review-world-rab-candidate.v6'
    assert manifest['lifecycle_state'] == 'CANDIDATE'
    assert manifest['proof_dependency'] == ['SAE-00']
    assert manifest['normal_verdict_authority'] is False

def test_candidate_manifest_outputs_are_exact():
    assert _load()['produces'] == ['QUALIFIED_REVIEW_WORLD_CONTRACT', 'QUALIFIED_RAB_CONTRACT']

def test_manifest_paths_are_repository_confined():
    import pytest
    with pytest.raises(AssertionError, match='non-repository manifest path'):
        _repo_path('../outside')
    with pytest.raises(AssertionError, match='non-repository manifest path'):
        _repo_path('/tmp/outside')

def test_candidate_content_blob_bindings_match_exact_repository_roster():
    manifest = _load()
    _assert_exact_blob_bindings(manifest['content_blobs'], EXPECTED_CONTENT_BLOBS)

def test_external_authority_blob_bindings_match_exact_repository_roster():
    manifest = _load()
    _assert_exact_blob_bindings(manifest['external_authority_blobs'], EXPECTED_EXTERNAL_AUTHORITY_BLOBS)

def test_external_authority_binding_guard_rejects_extra_member_and_hash_mismatch():
    import pytest
    manifest = _load()
    bindings = dict(manifest['external_authority_blobs'])
    fake_hashes = dict(bindings)
    fake_blob = lambda path: fake_hashes[str(path)]
    _assert_exact_blob_bindings(bindings, EXPECTED_EXTERNAL_AUTHORITY_BLOBS, blob_fn=fake_blob)
    with pytest.raises(AssertionError):
        _assert_exact_blob_bindings({**bindings, 'docs/extra-authority.md': 'a' * 40}, EXPECTED_EXTERNAL_AUTHORITY_BLOBS, blob_fn=fake_blob)
    bad = dict(fake_hashes)
    first = next(iter(bad)); bad[first] = '0' * 40
    with pytest.raises(AssertionError):
        _assert_exact_blob_bindings(bindings, EXPECTED_EXTERNAL_AUTHORITY_BLOBS, blob_fn=lambda path: bad[str(path)])

def test_tenfold_formation_and_focused_proof_are_bound():
    manifest = _load()
    assert manifest['tenfold_proof'] == {
        'actions_required': False,
        'formation_lanes': 20,
        'focused_collection': 119,
        'local_dependency_surface_reconciliation': {
            'failed': 0,
            'passed': 107,
            'xfailed': 0,
            'basis': 'v5_frozen_93_plus_14_fresh_red_green_nodes',
        },
        'repository_only_focused_tests': 12,
    }

def test_required_hostile_attacks_are_bound():
    assert set(_load()['required_hostile_attacks']) == {
        'same_head_different_base', 'wrong_merge_tree', 'local_mutation_after_snapshot',
        'scope_downgrade', 'unauthorized_rab_combination', 'candidate_self_activation',
    }

def test_candidate_doc_preserves_nonactivation_boundary():
    text = DOC.read_text(encoding='utf-8')
    assert 'still **CANDIDATE**' in text
    assert 'not fabricated here' in text
    assert 'zero effect' in text
    assert 'GitHub Actions are supplementary only' in text

def test_github_hostile_review_finding_is_bound_and_repaired_locally():
    manifest = _load(); review = manifest['github_hostile_review']
    assert review['initial_candidate_head'] == 'c977449177eb9c9f3d6034265ad97cc32180c069'
    assert review['valid_finding'] == 'spike_sem_historical_metric_current_tree_invariant'
    assert review['repair'] == 'external_exact_node_strict_xfail_preserve_historical_fixture'
    assert review['repair_local_reproof'] == {'failed': 0, 'passed': 66, 'xfailed': 1}
    followup = review['followup_review']
    assert followup['reviewed_head'] == 'bf368b46cd0120736645d87e8dc7fec4904a046a'
    assert followup['review_id'] == 5089723949
    assert followup['actionable_findings'] == 7
    assert followup['all_valid_findings_corrected_in_tenfold'] is True
    exact = review['exact_head_review']
    assert exact['reviewed_head'] == '323b6f33223231b5d603a3a36ee5c07ef687a96a'
    assert exact['actionable_findings'] == 3
    owner_root = review['owner_root_exact_head_review']
    assert owner_root['reviewed_head'] == '97055f975c2fe76f77b7483df885f1aa9064c560'
    assert owner_root['finding_class'] == 'in_memory_authority_canonicality'
    canonical = review['canonical_decode_exact_head_review']
    assert canonical['reviewed_head'] == 'f20d83a7620622e3f2e96ffc26960f40a6a2df92'
    assert canonical['red_regressions'] == {'failed_as_expected': 7}
    persisted = review['owner_root_persisted_decode_review']
    assert persisted['reviewed_head'] == '924d33aa188dff673a9ca7eb7c843b6222e798fe'
    assert persisted['red_regressions'] == {'failed_as_expected': 9}
    assert persisted['focused_collection'] == 105
    world = review['owner_root_review_world_persisted_decode_review']
    assert world['reviewed_head'] == 'b3c4e409bfb7e0fd498d7790bef3b391f9595755'
    assert world['finding_class'] == 'persisted_review_world_decode_canonicality'
    assert world['actionable_findings'] == 1
    assert world['red_regressions'] == {'failed_as_expected': 14}
    assert set(world['accepted_repairs']) == {
        'review_scope_payload_requires_precanonical_types_and_exact_payload',
        'github_diff_payload_rejects_type_coercion_and_repository_normalization',
        'github_review_world_payload_requires_positive_integer_pr_and_precanonical_unresolved_state',
        'local_review_world_payload_rejects_repository_none_collapse_and_authority_type_coercion',
    }
    assert world['intermediate_repair_head'] == '0e67e3116e9d7a6a3945550eef3fdf485f25f634'
    assert world['intermediate_repository_reproof'] == {
        'ci_run_id': 33693267282,
        'failed': 2,
        'passed': 1232,
        'xfailed': 2,
        'failures': ['stale_pr_number_error_message_expectation', 'candidate_content_blob_bindings_stale'],
        'main_review': 'pass',
    }
    assert world['local_selected_decoder_reproof'] == {'failed': 0, 'passed': 15, 'xfailed': 0}
    assert world['focused_collection'] == 119
    assert world['replacement_content_blobs'] == {
        'main_review/review_world.py': '9d6081641506bcdb205271b9a6aa5e3e60c3bc65',
        'tests/test_review_world_persistence.py': '46422a3ab99311fc4cf4b991c64de70d8e25b96b',
    }
    expected = review['historical_fixture_blob_preserved']
    assert expected == manifest['external_authority_blobs'][str(HISTORICAL_SPIKE_FIXTURE)]
