from __future__ import annotations
import json, subprocess
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/79-sae10-review-world-rab-manifest.json'
DOC=ROOT/'docs/78-sae10-review-world-rab-contract.md'
HISTORICAL_SPIKE_FIXTURE=Path('tests/spike_sem/test_semantic_feasibility_probe.py')
EXPECTED_CONTENT_BLOBS={
'docs/78-sae10-review-world-rab-contract.md','docs/superpowers/plans/2026-09-02-sae-10-review-world-rab.md',
'main_review/review_authority_bundle.py','main_review/review_world.py','main_review/review_world_currentness.py',
'main_review/review_world_git.py','tests/conftest.py','tests/test_review_authority_bundle.py',
'tests/test_review_world_currentness.py','tests/test_review_world_git.py','tests/test_review_world_identity.py',
'tests/test_review_world_persistence.py','tests/test_sae10_hostile_matrix.py',
'tests/test_spike_sem_historical_metric_supersession.py','tests/test_sae10_review_world_rab_manifest.py'}
EXPECTED_EXTERNAL_AUTHORITY_BLOBS={
'docs/58-sergeant-assurance-evolution-founding-architecture.md','docs/59-sergeant-assurance-evolution-roadmap.md',
'docs/66-sae00-proven-lifecycle-closeout.md','docs/67-sae00-proven-lifecycle-closeout-manifest.json',
'docs/75-spike-sem-feasibility-manifest.json','docs/77-spike-sem-proven-lifecycle-closeout-manifest.json',
'docs/superpowers/specs/2026-09-02-sae-10-review-world-rab-design.md',
'tests/spike_sem/test_semantic_feasibility_probe.py'}

def _load(): return json.loads(MANIFEST.read_text(encoding='utf-8'))
def _repo_path(value):
    pure=PurePosixPath(str(value))
    if pure.is_absolute() or '..' in pure.parts: raise AssertionError(f'non-repository manifest path: {value!r}')
    resolved=(ROOT/Path(*pure.parts)).resolve(); resolved.relative_to(ROOT.resolve()); return resolved
def blob(path): return subprocess.run(['git','hash-object',str(_repo_path(path))],text=True,capture_output=True,check=True).stdout.strip()
def _assert_exact_blob_bindings(bindings, expected_paths, *, blob_fn=blob):
    assert isinstance(bindings,dict) and set(bindings)==expected_paths
    for path,expected in bindings.items(): assert blob_fn(path)==expected

def test_candidate_manifest_lifecycle_and_dependency():
    m=_load(); assert (m['schema_version'],m['lifecycle_state'],m['proof_dependency'],m['normal_verdict_authority'])==(
    'sergeant.sae10-review-world-rab-candidate.v8','CANDIDATE',['SAE-00'],False)
def test_candidate_manifest_outputs_are_exact():
    assert _load()['produces']==['QUALIFIED_REVIEW_WORLD_CONTRACT','QUALIFIED_RAB_CONTRACT']
def test_manifest_paths_are_repository_confined():
    import pytest
    for path in ('../outside','/tmp/outside'):
        with pytest.raises(AssertionError,match='non-repository manifest path'): _repo_path(path)
def test_candidate_content_blob_bindings_match_exact_repository_roster():
    _assert_exact_blob_bindings(_load()['content_blobs'],EXPECTED_CONTENT_BLOBS)
def test_external_authority_blob_bindings_match_exact_repository_roster():
    _assert_exact_blob_bindings(_load()['external_authority_blobs'],EXPECTED_EXTERNAL_AUTHORITY_BLOBS)
def test_external_authority_binding_guard_rejects_extra_member_and_hash_mismatch():
    import pytest
    b=dict(_load()['external_authority_blobs']); fake=dict(b)
    _assert_exact_blob_bindings(b,EXPECTED_EXTERNAL_AUTHORITY_BLOBS,blob_fn=lambda p:fake[str(p)])
    with pytest.raises(AssertionError):
        _assert_exact_blob_bindings({**b,'docs/extra-authority.md':'a'*40},EXPECTED_EXTERNAL_AUTHORITY_BLOBS,blob_fn=lambda p:fake[str(p)])
    bad=dict(fake); bad[next(iter(bad))]='0'*40
    with pytest.raises(AssertionError):
        _assert_exact_blob_bindings(b,EXPECTED_EXTERNAL_AUTHORITY_BLOBS,blob_fn=lambda p:bad[str(p)])
def test_tenfold_formation_and_focused_proof_are_bound():
    assert _load()['tenfold_proof']=={'actions_required':False,'formation_lanes':20,'focused_collection':127,
    'local_dependency_surface_reconciliation':{'failed':0,'passed':115,'xfailed':0,
    'basis':'v5_frozen_93_plus_14_v6_red_green_plus_5_v7_generation_strict_plus_3_v8_exact_head_regression_nodes'},
    'repository_only_focused_tests':12}
def test_required_hostile_attacks_are_bound():
    assert set(_load()['required_hostile_attacks'])=={'same_head_different_base','wrong_merge_tree','local_mutation_after_snapshot',
    'scope_downgrade','unauthorized_rab_combination','candidate_self_activation'}
def test_candidate_doc_preserves_nonactivation_boundary():
    t=DOC.read_text(encoding='utf-8')
    for marker in ('still **CANDIDATE**','not fabricated here','zero effect','GitHub Actions are supplementary only'): assert marker in t

def test_github_hostile_review_finding_is_bound_and_repaired_locally():
    m=_load(); r=m['github_hostile_review']
    assert (r['initial_candidate_head'],r['valid_finding'],r['repair'],r['repair_local_reproof'])==(
    'c977449177eb9c9f3d6034265ad97cc32180c069','spike_sem_historical_metric_current_tree_invariant',
    'external_exact_node_strict_xfail_preserve_historical_fixture',{'failed':0,'passed':66,'xfailed':1})
    f=r['followup_review']
    assert (f['reviewed_head'],f['review_id'],f['actionable_findings'],f['all_valid_findings_corrected_in_tenfold'],
    f['replacement_local_reproof'])==('bf368b46cd0120736645d87e8dc7fec4904a046a',5089723949,7,True,{'failed':0,'passed':71,'xfailed':0})
    assert set(f['valid_findings'])=={'manifest_exact_content_roster_and_path_confinement','historical_fixture_blob_mechanical_binding',
    'plan_rab_slot_name_drift','rab_authorization_record_state_validation','git_environment_metadata_isolation',
    'review_scope_duplicate_payload_strict_decode','historical_xfail_exact_node_strict_binding'}
    e=r['exact_head_review']
    assert (e['reviewed_head'],e['actionable_findings'],e['dispositioned_without_mutation'],e['replacement_local_reproof'])==(
    '323b6f33223231b5d603a3a36ee5c07ef687a96a',3,['historical_design_freeze_status_preserved'],{'failed':0,'passed':77,'xfailed':0})
    assert set(e['accepted_repairs'])=={'rab_component_authority_domain_validation','unknown_rab_authorization_preserves_world_mismatch_reasons'}
    o=r['owner_root_exact_head_review']
    assert (o['reviewed_head'],o['actionable_findings'],o['finding_class'],o['replacement_local_reproof'])==(
    '97055f975c2fe76f77b7483df885f1aa9064c560',1,'in_memory_authority_canonicality',{'failed':0,'passed':86,'xfailed':0})
    assert set(o['accepted_repairs'])=={'rab_component_direct_canonical_round_trip','nested_review_scope_diff_identity_validation',
    'currentness_rejects_forged_review_world_identity'}
    c=r['canonical_decode_exact_head_review']
    assert (c['reviewed_head'],c['actionable_findings'],c['red_regressions'],c['local_compatibility_reproof'],
    c['local_dependency_surface_reproof'],c['focused_collection'],c['intermediate_repair_head'],c['intermediate_repository_reproof'])==(
    'f20d83a7620622e3f2e96ffc26960f40a6a2df92',4,{'failed_as_expected':7},{'failed':0,'passed':70,'xfailed':0},
    {'failed':0,'passed':84,'xfailed':0},96,'4b4cc9264d1db769566b5d5defea75b72c94532b',
    {'failed':1,'passed':1210,'xfailed':2,'sole_failure':'candidate_content_blob_bindings_stale'})
    assert set(c['valid_findings'])=={'rab_authority_field_type_and_record_order_canonicality','review_scope_persisted_path_order_canonicality',
    'external_authority_exact_roster_binding','local_head_state_unborn_detached_representation'}
    p=r['owner_root_persisted_decode_review']
    assert (p['reviewed_head'],p['actionable_findings'],p['finding_class'],p['red_regressions'],p['replacement_local_reproof'],p['focused_collection'])==(
    '924d33aa188dff673a9ca7eb7c843b6222e798fe',1,'persisted_authority_decode_canonicality',{'failed_as_expected':9},
    {'failed':0,'passed':93,'xfailed':0},105)
    assert set(p['accepted_repairs'])=={'rab_component_payload_requires_precanonical_fields',
    'rab_authorization_payload_rejects_type_coercion_and_normalization','rab_authorization_set_payload_rejects_noncanonical_record_order'}
    w=r['owner_root_review_world_persisted_decode_review']
    assert (w['reviewed_head'],w['finding_class'],w['actionable_findings'],w['red_regressions'],w['intermediate_repair_head'],
    w['intermediate_repository_reproof'],w['local_selected_decoder_reproof'],w['focused_collection'],w['replacement_content_blobs'])==(
    'b3c4e409bfb7e0fd498d7790bef3b391f9595755','persisted_review_world_decode_canonicality',1,{'failed_as_expected':14},
    '0e67e3116e9d7a6a3945550eef3fdf485f25f634',
    {'ci_run_id':33693267282,'failed':2,'passed':1232,'xfailed':2,'failures':['stale_pr_number_error_message_expectation',
    'candidate_content_blob_bindings_stale'],'main_review':'pass'},{'failed':0,'passed':15,'xfailed':0},119,
    {'main_review/review_world.py':'9d6081641506bcdb205271b9a6aa5e3e60c3bc65',
    'tests/test_review_world_persistence.py':'46422a3ab99311fc4cf4b991c64de70d8e25b96b'})
    assert set(w['accepted_repairs'])=={'review_scope_payload_requires_precanonical_types_and_exact_payload',
    'github_diff_payload_rejects_type_coercion_and_repository_normalization',
    'github_review_world_payload_requires_positive_integer_pr_and_precanonical_unresolved_state',
    'local_review_world_payload_rejects_repository_none_collapse_and_authority_type_coercion'}
    q=r['exact_v6_rebound_hostile_review']
    assert (q['reviewed_head'],q['finding_class'],q['actionable_findings'],q['valid_findings'],q['reviewed_head_repository_reproof'],
    q['accepted_repairs'],q['focused_collection_after_repair'],q['disposition'])==(
    'ece5ae76b2d76763524d5be46be8bd619af300b2','manifest_historical_proof_coverage_regression',1,
    ['manifest_test_dropped_historical_review_assertions'],
    {'ci_run_id':33723267712,'failed':0,'passed':1234,'xfailed':2,'clean_clone_proof':'pass','main_review':'pass'},
    ['restore_v5_historical_review_assertions_without_new_test_node'],119,'superseded_for_freeze_by_owner_root_finding')
    assert q['replacement_manifest_test_blob']=='95a7c8023ba8f0fbb4302dc4b9143d33108527be'
    g=r['exact_generation_type_hostile_review']
    assert (g['reviewed_head'],g['review_run_id'],g['finding_class'],g['actionable_findings'],g['red_regressions'],
    g['intermediate_repair_head'],g['intermediate_repository_reproof'],g['local_generation_reproof'],g['focused_collection'])==(
    '8939f93eba730c3519f3ffe84c5e3793b6c15a90','7c0b86f6-b27e-4b33-9641-62d2868b366c',
    'review_world_generation_construction_persistence_asymmetry',1,{'failed_as_expected':5},
    '8c43caa0ea897e5d17bb6574dea1960d9a6af846',
    {'ci_run_id':33727961009,'failed':1,'passed':1238,'xfailed':2,'sole_failure':'candidate_content_blob_bindings_stale','main_review':'pass'},
    {'failed':0,'passed':5,'xfailed':0},124)
    assert set(g['accepted_repairs'])=={'review_scope_generation_requires_string_before_hashing',
    'github_diff_algorithm_generation_requires_string_before_hashing_and_validation',
    'github_review_world_generation_requires_string_before_hashing',
    'local_review_world_generation_requires_string_before_hashing'}
    assert g['replacement_content_blobs']=={
    'main_review/review_world.py':'34692d55c3944d4188c49d6546800374d9258da7',
    'tests/test_review_world_persistence.py':'99b3f1146588fc6fd79e5dca8426fde7f672abf6'}
    assert r['historical_fixture_blob_preserved']==m['external_authority_blobs'][str(HISTORICAL_SPIKE_FIXTURE)]

def test_v8_exact_head_review_findings_and_intermediate_proof_are_bound():
    v=_load()['github_hostile_review']['exact_v7_completion_hostile_review']
    assert (v['reviewed_head'],v['review_run_id'],v['finding_class'],v['actionable_findings'])==(
    '64f420aaea40594c4165ad64601b4db5547e275f','83e3c959-0d29-414a-b2ab-78f7b76aa411',
    'transport_local_head_and_unresolved_state_canonicality',3)
    assert set(v['valid_findings'])=={
    'pull_request_diff_transport_fact_type_coercion','dangling_symbolic_head_misclassified_as_unborn',
    'invalid_unresolved_state_entries_collapse_before_validation'}
    assert v['red_regressions']=={'regression_nodes_failed_as_expected':3,'hostile_cases':13}
    assert set(v['accepted_repairs'])=={
    'pull_request_diff_transport_requires_exact_fact_types',
    'unborn_head_requires_absent_branch_ref_and_rejects_nested_or_bad_refs',
    'github_review_world_unresolved_state_requires_string_nonempty_entries_before_normalization'}
    assert v['intermediate_repair_head']=='30b1f922453c63f473e38a39a70e82a1e9914d11'
    assert v['intermediate_repository_reproof']=={
    'ci_run_id':33733303167,'failed':1,'passed':1241,'xfailed':2,
    'sole_failure':'candidate_content_blob_bindings_stale','main_review_run_id':33733303192,'main_review':'pass',
    'clean_clone_proof':'blocked_by_same_stale_candidate_binding_before_supplementary_steps'}
    assert v['local_hostile_case_reproof']=={'failed':0,'passed':13,'xfailed':0}
    assert v['focused_collection']==127
    assert v['replacement_content_blobs']=={
    'main_review/review_world.py':'af4a32de1717f706d07377dcfaf65b2558f2d617',
    'main_review/review_world_git.py':'5f194b67cdceafb4b7098c5b3a8cfaa4015f3a51',
    'tests/test_review_world_git.py':'8a6e77ff54ed030184769129d186621b19423026',
    'tests/test_review_world_persistence.py':'8e8258ef7285eef59e34a2e9bd7d7f7eda7ee65e'}
