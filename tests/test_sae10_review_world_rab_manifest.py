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
    return subprocess.run(
        ['git', 'hash-object', str(_repo_path(path))],
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def test_candidate_manifest_lifecycle_and_dependency():
    manifest = _load()
    assert manifest['lifecycle_state'] == 'CANDIDATE'
    assert manifest['proof_dependency'] == ['SAE-00']
    assert manifest['normal_verdict_authority'] is False


def test_candidate_manifest_outputs_are_exact():
    manifest = _load()
    assert manifest['produces'] == [
        'QUALIFIED_REVIEW_WORLD_CONTRACT',
        'QUALIFIED_RAB_CONTRACT',
    ]


def test_manifest_paths_are_repository_confined():
    import pytest

    with pytest.raises(AssertionError, match='non-repository manifest path'):
        _repo_path('../outside')
    with pytest.raises(AssertionError, match='non-repository manifest path'):
        _repo_path('/tmp/outside')


def test_candidate_content_blob_bindings_match_exact_repository_roster():
    manifest = _load()
    bindings = manifest['content_blobs']
    assert isinstance(bindings, dict)
    assert set(bindings) == EXPECTED_CONTENT_BLOBS
    for path, expected in bindings.items():
        assert blob(path) == expected


def test_tenfold_formation_and_local_proof_are_bound():
    manifest = _load()
    assert manifest['tenfold_proof'] == {
        'actions_required': False,
        'formation_lanes': 20,
        'local_test_result': {'failed': 0, 'passed': 71, 'xfailed': 0},
    }


def test_required_hostile_attacks_are_bound():
    manifest = _load()
    assert set(manifest['required_hostile_attacks']) == {
        'same_head_different_base',
        'wrong_merge_tree',
        'local_mutation_after_snapshot',
        'scope_downgrade',
        'unauthorized_rab_combination',
        'candidate_self_activation',
    }


def test_candidate_doc_preserves_nonactivation_boundary():
    text = DOC.read_text(encoding='utf-8')
    assert 'still **CANDIDATE**' in text
    assert 'not fabricated here' in text
    assert 'zero effect' in text
    assert 'GitHub Actions are supplementary only' in text


def test_github_hostile_review_finding_is_bound_and_repaired_locally():
    manifest = _load()
    review = manifest['github_hostile_review']
    assert review['initial_candidate_head'] == 'c977449177eb9c9f3d6034265ad97cc32180c069'
    assert review['valid_finding'] == 'spike_sem_historical_metric_current_tree_invariant'
    assert review['repair'] == 'external_exact_node_strict_xfail_preserve_historical_fixture'
    assert review['repair_local_reproof'] == {'failed': 0, 'passed': 66, 'xfailed': 1}
    followup = review['followup_review']
    assert followup['reviewed_head'] == 'bf368b46cd0120736645d87e8dc7fec4904a046a'
    assert followup['review_id'] == 5089723949
    assert followup['actionable_findings'] == 7
    assert followup['all_valid_findings_corrected_in_tenfold'] is True
    assert set(followup['valid_findings']) == {
        'manifest_exact_content_roster_and_path_confinement',
        'historical_fixture_blob_mechanical_binding',
        'plan_rab_slot_name_drift',
        'rab_authorization_record_state_validation',
        'git_environment_metadata_isolation',
        'review_scope_duplicate_payload_strict_decode',
        'historical_xfail_exact_node_strict_binding',
    }
    assert followup['replacement_local_reproof'] == {'failed': 0, 'passed': 71, 'xfailed': 0}
    expected = review['historical_fixture_blob_preserved']
    assert expected == manifest['external_authority_blobs'][str(HISTORICAL_SPIKE_FIXTURE)]
    assert blob(HISTORICAL_SPIKE_FIXTURE) == expected
