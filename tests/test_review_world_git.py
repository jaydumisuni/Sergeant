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
