from copy import deepcopy
import shutil, subprocess
from pathlib import Path
import pytest
import main_review.review_world as rw
import main_review.review_world_git as gitw
import main_review.review_world_currentness as cur
import main_review.review_authority_bundle as rab
R = '1' * 64
A = 'a' * 40
B = 'b' * 40
C = 'c' * 40
D = 'd' * 40

def gh(base=A, scope=None, rab_id=R, merge=None, repo='owner/repo'):
    scope = scope or rw.ReviewScope.repository()
    d = rw.GitHubDiffIdentity.create(repository=repo, base_commit=base, base_tree=C, head_commit=B, head_tree=D, scope=scope)
    return rw.GitHubReviewWorld.create(repository=repo, pr_number=7, diff=d, scope=scope, review_mode='merge_result' if merge else 'head', rab_id=rab_id, review_generation='sae10-v1', merge_tree=merge)

def comp(g='g1', seed='a'):
    return rab.RABComponent.active(name='root_authority', generation=g, content_id=seed * 64, authority_domain='sergeant')

def _git(root, *args):
    return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()

def _repo(root):
    _git(root, 'init', '-q')
    _git(root, 'config', 'user.name', 'T')
    _git(root, 'config', 'user.email', 't@x')
    (root / 'a').write_text('one\n')
    _git(root, 'add', '.')
    _git(root, 'commit', '-qm', 'one')

def test_sae10_same_head_different_base_cannot_reuse_positive_world():
    assert cur.check_github_currentness(gh(), gh(base='e' * 40), rab_authorized=True).state == 'STALE'

def test_sae10_wrong_merge_tree_invalidates_merge_readiness_world():
    assert 'merge_result_mismatch' in cur.check_github_currentness(gh(merge='e' * 40), gh(merge='f' * 40), rab_authorized=True).reasons

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_sae10_local_mutation_after_snapshot_is_stale_not_rewritten(tmp_path: Path):
    _repo(tmp_path)
    scope = rw.ReviewScope.repository()
    policy = gitw.LocalSnapshotPolicy.exclude_untracked()
    snap1, w1 = gitw.build_local_review_world(tmp_path, repository='owner/repo', scope=scope, policy=policy, rab_id=R, review_generation='sae10-v1')
    old = w1.review_world_id
    (tmp_path / 'a').write_text('two\n')
    snap2, w2 = gitw.build_local_review_world(tmp_path, repository='owner/repo', scope=scope, policy=policy, rab_id=R, review_generation='sae10-v1')
    res = cur.check_local_currentness(w1, w2, rab_authorized=True)
    assert res.state == 'STALE' and 'local_snapshot_mutation' in res.reasons and (w1.review_world_id == old) and (snap1.local_snapshot_id != snap2.local_snapshot_id)

def test_sae10_scope_downgrade_cannot_satisfy_repository_world():
    assert 'scope_mismatch' in cur.check_github_currentness(gh(), gh(scope=rw.ReviewScope.selected_paths(['a'])), rab_authorized=True).reasons

def test_sae10_unauthorized_rab_combination_fails_even_when_components_are_known():
    b1 = rab.ReviewAuthorityBundle.create(root_authority=comp('g1', 'a'))
    b2 = rab.ReviewAuthorityBundle.create(root_authority=comp('g2', 'b'))
    trusted = rab.RABAuthorizationSet.create([rab.RABAuthorization.authorized(b1.rab_id, 'root-g1', 'root')])
    assert rab.authorize_rab(b2, trusted).reason == 'rab_not_authorized_as_whole'

def test_sae10_candidate_attempt_to_alter_active_review_authority_has_zero_effect():
    active = rab.ReviewAuthorityBundle.create(root_authority=comp('g1', 'a'))
    candidate = rab.ReviewAuthorityBundle.create(root_authority=comp('candidate-g2', 'b'))
    trusted = rab.RABAuthorizationSet.create([rab.RABAuthorization.authorized(active.rab_id, 'root-g1', 'root')])
    assert rab.authorize_rab(active, trusted).authorized and (not rab.authorize_rab(candidate, trusted).authorized)

def test_identical_world_facts_reproduce_identity():
    assert gh().review_world_id == gh().review_world_id

def test_repository_substitution_changes_identity():
    assert gh(repo='owner/a').review_world_id != gh(repo='owner/b').review_world_id

def test_truncated_authority_ids_fail_closed():
    with pytest.raises(rw.ReviewWorldError):
        rw.LocalReviewWorld.create(repository='o/r', local_snapshot_id='1' * 64, scope=rw.ReviewScope.repository(), rab_id='abc', review_generation='g')

def test_latest_authority_substitution_rejected():
    with pytest.raises(rab.ReviewAuthorityBundleError):
        comp('latest', 'a')

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_untracked_policy_changes_local_identity(tmp_path: Path):
    _repo(tmp_path)
    (tmp_path / 'u').write_text('u')
    s = rw.ReviewScope.repository()
    a = gitw.build_local_snapshot(tmp_path, scope=s, policy=gitw.LocalSnapshotPolicy.exclude_untracked())
    b = gitw.build_local_snapshot(tmp_path, scope=s, policy=gitw.LocalSnapshotPolicy.include_all_untracked_in_scope())
    assert a.local_snapshot_id != b.local_snapshot_id

def test_revoked_rab_currentness_is_stale():
    assert cur.check_github_currentness(gh(), gh(), rab_authorized=False).state == 'STALE'

def test_persisted_world_tamper_fails_closed():
    p = gh().to_payload()
    p['diff']['head_tree'] = 'e' * 40
    with pytest.raises(rw.ReviewWorldError, match='diff_id mismatch'):
        rw.GitHubReviewWorld.from_payload(p)

def test_unknown_persisted_field_fails_closed():
    p = gh().to_payload()
    p['authority_alias'] = 'latest'
    with pytest.raises(rw.ReviewWorldError, match='unexpected fields'):
        rw.GitHubReviewWorld.from_payload(p)
