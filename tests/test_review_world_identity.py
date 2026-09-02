from __future__ import annotations

import importlib.util

import pytest

import main_review.review_world as rw

HEX_A = "a" * 40
HEX_B = "b" * 40
HEX_C = "c" * 40
HEX_D = "d" * 40
RAB = "1" * 64


def test_review_world_authority_module_exists() -> None:
    assert importlib.util.find_spec("main_review.review_world") is not None


def test_canonical_json_is_order_independent_for_object_keys() -> None:
    left = {"schema_version": "v1", "b": 2, "a": 1}
    right = {"a": 1, "b": 2, "schema_version": "v1"}
    assert rw.canonical_json_bytes(left) == rw.canonical_json_bytes(right)
    assert rw.sha256_id(left) == rw.sha256_id(right)


def test_non_json_numbers_fail_closed() -> None:
    with pytest.raises(rw.ReviewWorldError, match="non-finite"):
        rw.canonical_json_bytes({"schema_version": "v1", "value": float("nan")})


def test_truncated_authority_digest_is_rejected() -> None:
    with pytest.raises(rw.ReviewWorldError, match="64-hex"):
        rw.require_full_sha256("abc123", "rab_id")


def test_scope_paths_are_sorted_unique_and_normalized() -> None:
    scope = rw.ReviewScope.selected_paths(["src/b.py", "src/a.py", "src/a.py"])
    assert scope.paths == ("src/a.py", "src/b.py")
    assert len(scope.scope_id) == 64


def test_scope_path_traversal_is_rejected() -> None:
    with pytest.raises(rw.ReviewWorldError, match="repository-relative"):
        rw.ReviewScope.selected_paths(["../secret.txt"])


def test_same_head_different_base_changes_diff_and_world_identity() -> None:
    scope = rw.ReviewScope.repository()
    first = rw.GitHubDiffIdentity.create(
        repository="Owner/Repo",
        base_commit=HEX_A,
        base_tree=HEX_C,
        head_commit=HEX_B,
        head_tree=HEX_D,
        scope=scope,
    )
    second = rw.GitHubDiffIdentity.create(
        repository="owner/repo",
        base_commit="e" * 40,
        base_tree="f" * 40,
        head_commit=HEX_B,
        head_tree=HEX_D,
        scope=scope,
    )
    assert first.repository == "owner/repo"
    assert first.diff_id != second.diff_id

    world_a = rw.GitHubReviewWorld.create(
        repository="owner/repo",
        pr_number=7,
        diff=first,
        scope=scope,
        review_mode="head",
        rab_id=RAB,
        review_generation="sae10-v1",
    )
    world_b = rw.GitHubReviewWorld.create(
        repository="owner/repo",
        pr_number=7,
        diff=second,
        scope=scope,
        review_mode="head",
        rab_id=RAB,
        review_generation="sae10-v1",
    )
    assert world_a.review_world_id != world_b.review_world_id


def test_patch_rendering_is_not_part_of_diff_identity() -> None:
    scope = rw.ReviewScope.repository()
    left = rw.GitHubDiffIdentity.create(
        repository="owner/repo",
        base_commit=HEX_A,
        base_tree=HEX_C,
        head_commit=HEX_B,
        head_tree=HEX_D,
        scope=scope,
    )
    right = rw.GitHubDiffIdentity.create(
        repository="owner/repo",
        base_commit=HEX_A,
        base_tree=HEX_C,
        head_commit=HEX_B,
        head_tree=HEX_D,
        scope=scope,
    )
    assert left.diff_id == right.diff_id


def test_merge_result_world_requires_exact_merge_tree() -> None:
    scope = rw.ReviewScope.repository()
    diff = rw.GitHubDiffIdentity.create(
        repository="owner/repo",
        base_commit=HEX_A,
        base_tree=HEX_C,
        head_commit=HEX_B,
        head_tree=HEX_D,
        scope=scope,
    )
    with pytest.raises(rw.ReviewWorldError, match="merge tree"):
        rw.GitHubReviewWorld.create(
            repository="owner/repo",
            pr_number=7,
            diff=diff,
            scope=scope,
            review_mode="merge_result",
            rab_id=RAB,
            review_generation="sae10-v1",
        )


def test_scope_substitution_changes_world_identity() -> None:
    repository_scope = rw.ReviewScope.repository()
    selected_scope = rw.ReviewScope.selected_paths(["src/a.py"])
    repository_diff = rw.GitHubDiffIdentity.create(
        repository="owner/repo",
        base_commit=HEX_A,
        base_tree=HEX_C,
        head_commit=HEX_B,
        head_tree=HEX_D,
        scope=repository_scope,
    )
    selected_diff = rw.GitHubDiffIdentity.create(
        repository="owner/repo",
        base_commit=HEX_A,
        base_tree=HEX_C,
        head_commit=HEX_B,
        head_tree=HEX_D,
        scope=selected_scope,
    )
    repository_world = rw.GitHubReviewWorld.create(
        repository="owner/repo", pr_number=7, diff=repository_diff,
        scope=repository_scope, review_mode="head", rab_id=RAB,
        review_generation="sae10-v1",
    )
    selected_world = rw.GitHubReviewWorld.create(
        repository="owner/repo", pr_number=7, diff=selected_diff,
        scope=selected_scope, review_mode="head", rab_id=RAB,
        review_generation="sae10-v1",
    )
    assert repository_world.review_world_id != selected_world.review_world_id
