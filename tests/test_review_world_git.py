import os, shutil, subprocess
from pathlib import Path
import pytest
import main_review.review_world as rw
import main_review.review_world_git as g
A = 'a' * 40
B = 'b' * 40
C = 'c' * 40
D = 'd' * 40
R = '1' * 64

class Fake:

    def __init__(self, m='e' * 40):
        self.m = m

    def tree_for_commit(self, x):
        return {A: C, B: D}[x]

    def synthetic_merge(self, a, b):
        return self.m

def test_bind_trees():
    w = g.build_github_review_world(repository='o/r', pr_number=1, base_sha=A, head_sha=B, scope=rw.ReviewScope.repository(), review_mode='head', rab_id=R, review_generation='g', resolver=Fake())
    assert w.diff.base_tree == C and w.diff.head_tree == D

def test_merge_tree_changes():
    kw = dict(repository='o/r', pr_number=1, base_sha=A, head_sha=B, scope=rw.ReviewScope.repository(), review_mode='merge_result', rab_id=R, review_generation='g')
    x = g.build_github_review_world(**kw, resolver=Fake('e' * 40))
    y = g.build_github_review_world(**kw, resolver=Fake('f' * 40))
    assert x.review_world_id != y.review_world_id

def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=True, env={'PATH': os.environ.get('PATH', '')}).stdout.strip()

def init(root):
    git(root, 'init', '-q')
    git(root, 'config', 'user.name', 'T')
    git(root, 'config', 'user.email', 't@x')
    (root / 'src').mkdir()
    (root / 'src/a').write_text('a\n')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'base')

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_real_tree_no_mutation(tmp_path):
    init(tmp_path)
    head = git(tmp_path, 'rev-parse', 'HEAD')
    tree = git(tmp_path, 'rev-parse', 'HEAD^{tree}')
    assert g.GitObjectResolver(tmp_path).tree_for_commit(head) == tree

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_local_mutation(tmp_path):
    init(tmp_path)
    s = rw.ReviewScope.selected_paths(['src/a'])
    p = g.LocalSnapshotPolicy.exclude_untracked()
    x = g.build_local_snapshot(tmp_path, scope=s, policy=p)
    (tmp_path / 'src/a').write_text('b\n')
    y = g.build_local_snapshot(tmp_path, scope=s, policy=p)
    assert x.local_snapshot_id != y.local_snapshot_id

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_untracked_policy(tmp_path):
    init(tmp_path)
    (tmp_path / 'x').write_text('x')
    s = rw.ReviewScope.repository()
    a = g.build_local_snapshot(tmp_path, scope=s, policy=g.LocalSnapshotPolicy.exclude_untracked())
    b = g.build_local_snapshot(tmp_path, scope=s, policy=g.LocalSnapshotPolicy.include_all_untracked_in_scope())
    assert a.local_snapshot_id != b.local_snapshot_id

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_lfs_fail(tmp_path):
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.name', 'T')
    git(tmp_path, 'config', 'user.email', 't@x')
    (tmp_path / 'a').write_text('version https://git-lfs.github.com/spec/v1\noid sha256:' + 'a' * 64 + '\nsize 1\n')
    git(tmp_path, 'add', '.')
    git(tmp_path, 'commit', '-qm', 'x')
    with pytest.raises(g.GitCommandError, match='LFS'):
        g.build_local_snapshot(tmp_path, scope=rw.ReviewScope.repository(), policy=g.LocalSnapshotPolicy(untracked_policy='exclude_untracked', lfs_state='material_required'))

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_generated_fail(tmp_path):
    init(tmp_path)
    with pytest.raises(g.GitCommandError, match='generated'):
        g.build_local_snapshot(tmp_path, scope=rw.ReviewScope.repository(), policy=g.LocalSnapshotPolicy(untracked_policy='exclude_untracked', generated_state='material_unbound'))

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_git_resolver_ignores_inherited_git_dir(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    other = tmp_path / 'other'
    repo.mkdir(); other.mkdir()
    init(repo); init(other)
    (repo / 'src/a').write_text('repo-unique\n')
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'repo-unique')
    (other / 'src/a').write_text('other\n')
    git(other, 'add', '.'); git(other, 'commit', '-qm', 'other')
    head = git(repo, 'rev-parse', 'HEAD')
    tree = git(repo, 'rev-parse', 'HEAD^{tree}')
    monkeypatch.setenv('GIT_DIR', str(other / '.git'))
    assert g.GitObjectResolver(repo).tree_for_commit(head) == tree

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_local_snapshot_ignores_inherited_git_index_file(tmp_path, monkeypatch):
    init(tmp_path)
    monkeypatch.setenv('GIT_INDEX_FILE', str(tmp_path / 'ambient-index'))
    snapshot = g.build_local_snapshot(
        tmp_path,
        scope=rw.ReviewScope.repository(),
        policy=g.LocalSnapshotPolicy.exclude_untracked(),
    )
    assert any(entry.path == 'src/a' for entry in snapshot.entries)

@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_unborn_repository_has_explicit_canonical_head_state_and_builds_local_world(tmp_path):
    git(tmp_path, 'init', '-q')
    scope = rw.ReviewScope.repository()
    policy = g.LocalSnapshotPolicy.exclude_untracked()
    snapshot, world = g.build_local_review_world(
        tmp_path,
        repository=None,
        scope=scope,
        policy=policy,
        rab_id=R,
        review_generation='sae10-v1',
    )
    assert snapshot.head_state == 'unborn'
    assert snapshot.head_commit is None
    assert snapshot.head_tree is None
    assert world.local_snapshot_id == snapshot.local_snapshot_id
    repeated = g.build_local_snapshot(tmp_path, scope=scope, policy=policy)
    assert repeated.local_snapshot_id == snapshot.local_snapshot_id


@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_detached_repository_preserves_commit_tree_with_explicit_head_state(tmp_path):
    init(tmp_path)
    head = git(tmp_path, 'rev-parse', 'HEAD')
    tree = git(tmp_path, 'rev-parse', 'HEAD^{tree}')
    git(tmp_path, 'checkout', '--detach', '-q', head)
    snapshot = g.build_local_snapshot(
        tmp_path,
        scope=rw.ReviewScope.repository(),
        policy=g.LocalSnapshotPolicy.exclude_untracked(),
    )
    assert snapshot.head_state == 'detached'
    assert snapshot.head_commit == head
    assert snapshot.head_tree == tree


class _StringableTransportFact:

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


def test_pull_request_diff_transport_rejects_noncanonical_fact_types_before_construction():
    bad_cases = (
        ('repository', _StringableTransportFact('o/r')),
        ('pr_number', '1'),
        ('pr_number', True),
        ('base_sha', _StringableTransportFact(A)),
        ('head_sha', _StringableTransportFact(B)),
    )
    for field, bad_value in bad_cases:
        facts = {'repository': 'o/r', 'pr_number': 1, 'base_sha': A, 'head_sha': B}
        facts[field] = bad_value
        transport = type('TransportDiff', (), facts)()
        with pytest.raises(g.GitCommandError, match='transport facts are noncanonical'):
            g.build_github_review_world_from_diff(
                transport,
                scope=rw.ReviewScope.repository(),
                review_mode='head',
                rab_id=R,
                review_generation='g',
                resolver=Fake(),
            )


@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_unborn_head_requires_absent_branch_ref_not_dangling_or_nested_symbolic_ref(tmp_path):
    for kind in ('nested_symbolic', 'dangling_object'):
        repo = tmp_path / kind
        repo.mkdir()
        git(repo, 'init', '-q')
        branch = git(repo, 'symbolic-ref', '--short', 'HEAD')
        ref_path = repo / '.git' / 'refs' / 'heads' / branch
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        if kind == 'nested_symbolic':
            ref_path.write_text('ref: refs/heads/missing-target\n')
        else:
            ref_path.write_text('0' * 39 + '1\n')
        with pytest.raises(g.GitCommandError):
            g._resolve_local_head(g.GitObjectResolver(repo))


class _StringableGeneratedBinding:

    def __str__(self):
        return 'a' * 64


def test_bound_generated_binding_rejects_non_string_digest_before_hash_validation():
    for bad_binding in (int('1' * 64), _StringableGeneratedBinding()):
        with pytest.raises(g.GitCommandError, match='generated_binding_id must be a string'):
            g.LocalSnapshotPolicy(
                untracked_policy='exclude_untracked',
                generated_state='bound',
                generated_binding_id=bad_binding,
            )


@pytest.mark.skipif(os.name != 'posix' or shutil.which('git') is None, reason='POSIX git required')
@pytest.mark.parametrize('tracked', [True, False], ids=['tracked', 'untracked'])
def test_local_snapshot_rejects_non_utf8_symlink_targets_as_git_command_error(tmp_path, tracked):
    init(tmp_path)
    link = tmp_path / ('tracked-bad-link' if tracked else 'untracked-bad-link')
    os.symlink(b'\xff', os.fsencode(link))
    if tracked:
        git(tmp_path, 'add', link.name)
        git(tmp_path, 'commit', '-qm', 'add malformed symlink target')
        policy = g.LocalSnapshotPolicy.exclude_untracked()
    else:
        policy = g.LocalSnapshotPolicy.include_all_untracked_in_scope()
    with pytest.raises(g.GitCommandError, match='symlink target'):
        g.build_local_snapshot(tmp_path, scope=rw.ReviewScope.repository(), policy=policy)
