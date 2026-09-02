from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import main_review.review_world as rw
import main_review.review_world_git as rwg

BASE = "a" * 40
HEAD = "b" * 40
BASE_TREE = "c" * 40
HEAD_TREE = "d" * 40
MERGE_TREE_A = "e" * 40
MERGE_TREE_B = "f" * 40
RAB = "1" * 64


class FakeResolver:
    def __init__(self, *, merge_tree: str = MERGE_TREE_A) -> None:
        self.merge_tree = merge_tree

    def tree_for_commit(self, commit: str) -> str:
        return {BASE: BASE_TREE, HEAD: HEAD_TREE}[commit]

    def synthetic_merge(self, base: str, head: str) -> str:
        assert base == BASE
        assert head == HEAD
        return self.merge_tree


def test_github_world_binds_exact_head_and_base_trees() -> None:
    world = rwg.build_github_review_world(
        repository="Owner/Repo", pr_number=12, base_sha=BASE, head_sha=HEAD,
        scope=rw.ReviewScope.repository(), review_mode="head", rab_id=RAB,
        review_generation="sae10-v1", resolver=FakeResolver(),
    )
    assert world.repository == "owner/repo"
    assert world.diff.base_tree == BASE_TREE
    assert world.diff.head_tree == HEAD_TREE
    assert world.merge_tree is None


def test_wrong_merge_tree_cannot_reuse_merge_readiness_world() -> None:
    scope = rw.ReviewScope.repository()
    first = rwg.build_github_review_world(
        repository="owner/repo", pr_number=12, base_sha=BASE, head_sha=HEAD,
        scope=scope, review_mode="merge_result", rab_id=RAB,
        review_generation="sae10-v1", resolver=FakeResolver(merge_tree=MERGE_TREE_A),
    )
    second = rwg.build_github_review_world(
        repository="owner/repo", pr_number=12, base_sha=BASE, head_sha=HEAD,
        scope=scope, review_mode="merge_result", rab_id=RAB,
        review_generation="sae10-v1", resolver=FakeResolver(merge_tree=MERGE_TREE_B),
    )
    assert first.merge_tree == MERGE_TREE_A
    assert second.merge_tree == MERGE_TREE_B
    assert first.review_world_id != second.review_world_id


def test_repository_substitution_changes_world_identity() -> None:
    scope = rw.ReviewScope.repository()
    first = rwg.build_github_review_world(
        repository="owner/repo-a", pr_number=12, base_sha=BASE, head_sha=HEAD,
        scope=scope, review_mode="head", rab_id=RAB,
        review_generation="sae10-v1", resolver=FakeResolver(),
    )
    second = rwg.build_github_review_world(
        repository="owner/repo-b", pr_number=12, base_sha=BASE, head_sha=HEAD,
        scope=scope, review_mode="head", rab_id=RAB,
        review_generation="sae10-v1", resolver=FakeResolver(),
    )
    assert first.review_world_id != second.review_world_id


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=True,
        env={"PATH": __import__("os").environ.get("PATH", "")},
    )
    return completed.stdout.strip()


def test_real_resolver_reads_commit_tree_without_worktree_mutation(tmp_path: Path) -> None:
    if __import__("shutil").which("git") is None:
        pytest.skip("git unavailable")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "SAE10 Test")
    _git(tmp_path, "config", "user.email", "sae10@example.invalid")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "one")
    commit = _git(tmp_path, "rev-parse", "HEAD")
    expected_tree = _git(tmp_path, "rev-parse", "HEAD^{tree}")
    before = _git(tmp_path, "status", "--porcelain=v1")
    resolver = rwg.GitObjectResolver(tmp_path)
    assert resolver.tree_for_commit(commit) == expected_tree
    assert _git(tmp_path, "status", "--porcelain=v1") == before


def test_real_resolver_produces_synthetic_merge_tree_without_checkout_mutation(tmp_path: Path) -> None:
    if __import__("shutil").which("git") is None:
        pytest.skip("git unavailable")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "SAE10 Test")
    _git(tmp_path, "config", "user.email", "sae10@example.invalid")
    (tmp_path / "base.txt").write_text("base\n", encoding="utf-8")
    _git(tmp_path, "add", "base.txt")
    _git(tmp_path, "commit", "-qm", "base")
    base = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "checkout", "-qb", "feature")
    (tmp_path / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(tmp_path, "add", "feature.txt")
    _git(tmp_path, "commit", "-qm", "feature")
    head = _git(tmp_path, "rev-parse", "HEAD")
    before_head = head
    before_status = _git(tmp_path, "status", "--porcelain=v1")
    resolver = rwg.GitObjectResolver(tmp_path)
    merge_tree = resolver.synthetic_merge(base, head)
    assert len(merge_tree) in {40, 64}
    assert _git(tmp_path, "rev-parse", "HEAD") == before_head
    assert _git(tmp_path, "status", "--porcelain=v1") == before_status


def _init_local_repo(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "SAE10 Test")
    _git(root, "config", "user.email", "sae10@example.invalid")
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "a.txt").write_text("alpha\n", encoding="utf-8")
    _git(root, "add", "src/a.txt")
    _git(root, "commit", "-qm", "baseline")


def test_local_selected_file_mutation_changes_snapshot_id(tmp_path: Path) -> None:
    if __import__("shutil").which("git") is None:
        pytest.skip("git unavailable")
    _init_local_repo(tmp_path)
    scope = rw.ReviewScope.selected_paths(["src/a.txt"])
    policy = rwg.LocalSnapshotPolicy.exclude_untracked()
    first = rwg.build_local_snapshot(tmp_path, scope=scope, policy=policy)
    (tmp_path / "src" / "a.txt").write_text("beta\n", encoding="utf-8")
    second = rwg.build_local_snapshot(tmp_path, scope=scope, policy=policy)
    assert first.local_snapshot_id != second.local_snapshot_id
    assert first.selected_scope_digest != second.selected_scope_digest


def test_untracked_policy_changes_snapshot_identity(tmp_path: Path) -> None:
    if __import__("shutil").which("git") is None:
        pytest.skip("git unavailable")
    _init_local_repo(tmp_path)
    (tmp_path / "extra.txt").write_text("extra\n", encoding="utf-8")
    scope = rw.ReviewScope.repository()
    excluded = rwg.build_local_snapshot(tmp_path, scope=scope, policy=rwg.LocalSnapshotPolicy.exclude_untracked())
    included = rwg.build_local_snapshot(tmp_path, scope=scope, policy=rwg.LocalSnapshotPolicy.include_all_untracked_in_scope())
    assert excluded.local_snapshot_id != included.local_snapshot_id
    assert not any(entry.path == "extra.txt" for entry in excluded.entries)
    assert any(entry.path == "extra.txt" and entry.state == "untracked" for entry in included.entries)


def test_local_review_world_binds_snapshot_id_and_rab(tmp_path: Path) -> None:
    if __import__("shutil").which("git") is None:
        pytest.skip("git unavailable")
    _init_local_repo(tmp_path)
    snapshot, world = rwg.build_local_review_world(
        tmp_path, repository="owner/repo", scope=rw.ReviewScope.repository(),
        policy=rwg.LocalSnapshotPolicy.exclude_untracked(), rab_id=RAB,
        review_generation="sae10-v1",
    )
    assert world.local_snapshot_id == snapshot.local_snapshot_id
    assert world.rab_id == RAB
    assert len(world.review_world_id) == 64


def test_material_lfs_pointer_without_materialized_object_fails_closed(tmp_path: Path) -> None:
    if __import__("shutil").which("git") is None:
        pytest.skip("git unavailable")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.name", "SAE10 Test")
    _git(tmp_path, "config", "user.email", "sae10@example.invalid")
    pointer = "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 123\n"
    (tmp_path / "asset.bin").write_text(pointer, encoding="utf-8")
    _git(tmp_path, "add", "asset.bin")
    _git(tmp_path, "commit", "-qm", "lfs pointer")
    with pytest.raises(rwg.GitCommandError, match="LFS"):
        rwg.build_local_snapshot(
            tmp_path, scope=rw.ReviewScope.repository(),
            policy=rwg.LocalSnapshotPolicy(
                untracked_policy="exclude_untracked", lfs_state="material_required",
                generated_state="not_material",
            ),
        )


def test_material_generated_state_without_binding_fails_closed(tmp_path: Path) -> None:
    if __import__("shutil").which("git") is None:
        pytest.skip("git unavailable")
    _init_local_repo(tmp_path)
    with pytest.raises(rwg.GitCommandError, match="generated"):
        rwg.build_local_snapshot(
            tmp_path, scope=rw.ReviewScope.repository(),
            policy=rwg.LocalSnapshotPolicy(
                untracked_policy="exclude_untracked", lfs_state="pointer_identity_only",
                generated_state="material_unbound",
            ),
        )
