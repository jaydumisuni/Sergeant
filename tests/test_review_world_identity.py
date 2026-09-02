import pytest
import main_review.review_world as rw
A = 'a' * 40
B = 'b' * 40
C = 'c' * 40
D = 'd' * 40
R = '1' * 64

def test_canonical_order():
    assert rw.canonical_json_bytes({'b': 2, 'a': 1}) == rw.canonical_json_bytes({'a': 1, 'b': 2})

def test_nan_rejected():
    with pytest.raises(rw.ReviewWorldError, match='non-finite'):
        rw.canonical_json_bytes({'x': float('nan')})

def test_truncated_rejected():
    with pytest.raises(rw.ReviewWorldError, match='64-hex'):
        rw.require_full_sha256('abc', 'id')

def test_scope_sorted():
    assert rw.ReviewScope.selected_paths(['b', 'a', 'a']).paths == ('a', 'b')

def test_scope_traversal():
    with pytest.raises(rw.ReviewWorldError):
        rw.ReviewScope.selected_paths(['../x'])

def test_same_head_diff_base():
    s = rw.ReviewScope.repository()
    x = rw.GitHubDiffIdentity.create(repository='Owner/Repo', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    y = rw.GitHubDiffIdentity.create(repository='owner/repo', base_commit='e' * 40, base_tree='f' * 40, head_commit=B, head_tree=D, scope=s)
    assert x.diff_id != y.diff_id

def test_patch_not_input():
    s = rw.ReviewScope.repository()
    x = rw.GitHubDiffIdentity.create(repository='o/r', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    y = rw.GitHubDiffIdentity.create(repository='o/r', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    assert x.diff_id == y.diff_id

def test_merge_requires_tree():
    s = rw.ReviewScope.repository()
    d = rw.GitHubDiffIdentity.create(repository='o/r', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    with pytest.raises(rw.ReviewWorldError, match='merge tree'):
        rw.GitHubReviewWorld.create(repository='o/r', pr_number=1, diff=d, scope=s, review_mode='merge_result', rab_id=R, review_generation='g')

def test_scope_changes_world():
    s1 = rw.ReviewScope.repository()
    s2 = rw.ReviewScope.selected_paths(['a'])
    d1 = rw.GitHubDiffIdentity.create(repository='o/r', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s1)
    d2 = rw.GitHubDiffIdentity.create(repository='o/r', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s2)
    w1 = rw.GitHubReviewWorld.create(repository='o/r', pr_number=1, diff=d1, scope=s1, review_mode='head', rab_id=R, review_generation='g')
    w2 = rw.GitHubReviewWorld.create(repository='o/r', pr_number=1, diff=d2, scope=s2, review_mode='head', rab_id=R, review_generation='g')
    assert w1.review_world_id != w2.review_world_id


def test_direct_noncanonical_scope_cannot_seed_diff_identity():
    forged = rw.ReviewScope(
        schema_version='sergeant.review-scope.v1',
        kind='repository',
        paths=('src',),
        generated_artifacts='excluded',
        submodules='excluded',
        untracked='excluded',
        generation='scope-v1',
        scope_id=R,
    )
    with pytest.raises(rw.ReviewWorldError, match='ReviewScope|scope'):
        rw.GitHubDiffIdentity.create(repository='o/r', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=forged)


def test_direct_forged_diff_identity_cannot_seed_review_world():
    scope = rw.ReviewScope.repository()
    forged = rw.GitHubDiffIdentity(
        schema_version='sergeant.github-diff-identity.v1',
        repository='o/r',
        base_commit=A,
        base_tree=C,
        head_commit=B,
        head_tree=D,
        algorithm_generation='git-tree-transition-v1',
        scope_id=scope.scope_id,
        diff_id=R,
    )
    with pytest.raises(rw.ReviewWorldError, match='diff'):
        rw.GitHubReviewWorld.create(repository='o/r', pr_number=1, diff=forged, scope=scope, review_mode='head', rab_id=R, review_generation='g')
