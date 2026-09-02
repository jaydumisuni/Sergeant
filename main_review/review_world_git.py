"""SAE-10 Git fact derivation for Review Worlds."""
from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Protocol

from main_review.review_world import (
    GitHubDiffIdentity,
    GitHubReviewWorld,
    ReviewScope,
    ReviewWorldError,
    require_git_object_id,
)


class GitCommandError(ReviewWorldError):
    """Raised when exact Git identity cannot be derived without ambiguity."""


class GitObjectResolverProtocol(Protocol):
    def tree_for_commit(self, commit: str) -> str: ...
    def synthetic_merge(self, base: str, head: str) -> str: ...


class GitObjectResolver:
    """Read-only Git object resolver; commands never alter checkout/index state."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _run(self, *args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args], cwd=self.root, text=True, capture_output=True, check=False,
            )
        except OSError as error:
            raise GitCommandError(f"git command unavailable: {error}") from error
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise GitCommandError(
                f"git {' '.join(args)} failed with exit {completed.returncode}: {detail or 'no diagnostic'}"
            )
        return completed.stdout.strip()

    def tree_for_commit(self, commit: str) -> str:
        commit = require_git_object_id(commit, "commit")
        output = self._run("rev-parse", f"{commit}^{{tree}}")
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if len(lines) != 1:
            raise GitCommandError("git rev-parse returned ambiguous tree identity")
        return require_git_object_id(lines[0], "commit_tree")

    def synthetic_merge(self, base: str, head: str) -> str:
        base = require_git_object_id(base, "merge_base")
        head = require_git_object_id(head, "merge_head")
        output = self._run("merge-tree", "--write-tree", base, head)
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if len(lines) != 1:
            raise GitCommandError("git merge-tree returned ambiguous merge-result identity")
        return require_git_object_id(lines[0], "merge_tree")


def build_github_review_world(
    *, repository: str, pr_number: int, base_sha: str, head_sha: str,
    scope: ReviewScope, review_mode: str, rab_id: str, review_generation: str,
    resolver: GitObjectResolverProtocol,
) -> GitHubReviewWorld:
    """Construct one exact GitHub Review World from immutable Git object facts."""
    base_sha = require_git_object_id(base_sha, "base_sha")
    head_sha = require_git_object_id(head_sha, "head_sha")
    base_tree = resolver.tree_for_commit(base_sha)
    head_tree = resolver.tree_for_commit(head_sha)
    diff = GitHubDiffIdentity.create(
        repository=repository, base_commit=base_sha, base_tree=base_tree,
        head_commit=head_sha, head_tree=head_tree, scope=scope,
    )
    merge_tree = resolver.synthetic_merge(base_sha, head_sha) if review_mode == "merge_result" else None
    return GitHubReviewWorld.create(
        repository=repository, pr_number=pr_number, diff=diff, scope=scope,
        review_mode=review_mode, rab_id=rab_id, review_generation=review_generation,
        merge_tree=merge_tree,
    )


def build_github_review_world_from_diff(
    pull_request_diff: object, *, scope: ReviewScope, review_mode: str,
    rab_id: str, review_generation: str, resolver: GitObjectResolverProtocol,
) -> GitHubReviewWorld:
    """Reuse existing validated PullRequestDiff transport facts without trusting patch text."""
    try:
        repository = str(getattr(pull_request_diff, "repository"))
        pr_number = int(getattr(pull_request_diff, "pr_number"))
        base_sha = str(getattr(pull_request_diff, "base_sha"))
        head_sha = str(getattr(pull_request_diff, "head_sha"))
    except (AttributeError, TypeError, ValueError) as error:
        raise GitCommandError("pull-request diff transport facts are incomplete") from error
    return build_github_review_world(
        repository=repository, pr_number=pr_number, base_sha=base_sha, head_sha=head_sha,
        scope=scope, review_mode=review_mode, rab_id=rab_id,
        review_generation=review_generation, resolver=resolver,
    )
