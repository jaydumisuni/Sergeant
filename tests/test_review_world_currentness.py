from __future__ import annotations

import main_review.review_world as rw
import main_review.review_world_currentness as cur

RAB = "1" * 64
BASE = "a" * 40
HEAD = "b" * 40
BASE_TREE = "c" * 40
HEAD_TREE = "d" * 40


def github_world(*, base: str = BASE, head: str = HEAD, scope: rw.ReviewScope | None = None, rab_id: str = RAB, merge_tree: str | None = None) -> rw.GitHubReviewWorld:
    scope = scope or rw.ReviewScope.repository()
    diff = rw.GitHubDiffIdentity.create(repository="owner/repo", base_commit=base, base_tree=BASE_TREE, head_commit=head, head_tree=HEAD_TREE, scope=scope)
    mode = "merge_result" if merge_tree else "head"
    return rw.GitHubReviewWorld.create(repository="owner/repo", pr_number=7, diff=diff, scope=scope, review_mode=mode, rab_id=rab_id, review_generation="sae10-v1", merge_tree=merge_tree)


def test_exact_identical_github_world_is_current() -> None:
    frozen = github_world()
    result = cur.check_github_currentness(frozen, frozen, rab_authorized=True)
    assert result.state == "CURRENT"
    assert result.reasons == ()


def test_same_head_different_base_is_stale_with_specific_reason() -> None:
    frozen = github_world()
    changed = github_world(base="e" * 40)
    result = cur.check_github_currentness(frozen, changed, rab_authorized=True)
    assert result.state == "STALE"
    assert "base_identity_mismatch" in result.reasons


def test_scope_downgrade_is_stale() -> None:
    frozen = github_world(scope=rw.ReviewScope.repository())
    changed = github_world(scope=rw.ReviewScope.selected_paths(["src/a.py"]))
    result = cur.check_github_currentness(frozen, changed, rab_authorized=True)
    assert result.state == "STALE"
    assert "scope_mismatch" in result.reasons


def test_wrong_merge_tree_is_stale() -> None:
    frozen = github_world(merge_tree="e" * 40)
    changed = github_world(merge_tree="f" * 40)
    result = cur.check_github_currentness(frozen, changed, rab_authorized=True)
    assert result.state == "STALE"
    assert "merge_result_mismatch" in result.reasons


def test_revoked_rab_makes_world_stale() -> None:
    frozen = github_world()
    result = cur.check_github_currentness(frozen, frozen, rab_authorized=False)
    assert result.state == "STALE"
    assert "rab_unauthorized_or_revoked" in result.reasons


def test_unknown_live_fact_returns_unknown_currentness_not_current() -> None:
    frozen = github_world()
    result = cur.check_github_currentness(frozen, None, rab_authorized=True)
    assert result.state == "UNKNOWN_CURRENTNESS"
    assert result.reasons == ("comparison_facts_unavailable",)


def test_currentness_check_does_not_rewrite_historical_world() -> None:
    frozen = github_world()
    before_payload = frozen.to_payload()
    before_id = frozen.review_world_id
    changed = github_world(base="e" * 40)
    cur.check_github_currentness(frozen, changed, rab_authorized=True)
    assert frozen.to_payload() == before_payload
    assert frozen.review_world_id == before_id


def test_local_snapshot_mutation_is_stale() -> None:
    scope = rw.ReviewScope.repository()
    frozen = rw.LocalReviewWorld.create(repository="owner/repo", local_snapshot_id="2" * 64, scope=scope, rab_id=RAB, review_generation="sae10-v1")
    changed = rw.LocalReviewWorld.create(repository="owner/repo", local_snapshot_id="3" * 64, scope=scope, rab_id=RAB, review_generation="sae10-v1")
    result = cur.check_local_currentness(frozen, changed, rab_authorized=True)
    assert result.state == "STALE"
    assert result.reasons == ("local_snapshot_mutation",)
