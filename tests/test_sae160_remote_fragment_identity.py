"""SAE-160 HTTP remote fragments are not fetched evidence identities.

Git config stores literal fragment text, but HTTP clients do not transmit URL
fragments to the server. This is repository-only preflight, not SAE-150 proof.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from main_review.sae160_checkout_preflight import inspect_checkout


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True
    ).strip()


def checkout(tmp_path: Path) -> tuple[Path, str]:
    origin = tmp_path / "origin"
    origin.mkdir()
    subprocess.check_call(["git", "init", "-q", str(origin)])
    git(origin, "config", "user.email", "test@example.invalid")
    git(origin, "config", "user.name", "Fixture")
    (origin / "tracked.txt").write_text("pinned\n")
    git(origin, "add", "tracked.txt")
    git(origin, "commit", "-qm", "fixture")
    clone = tmp_path / "clone"
    subprocess.check_call(
        ["git", "clone", "-q", "--no-hardlinks", str(origin), str(clone)]
    )
    return clone, git(clone, "rev-parse", "HEAD")


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("field", ("url", "pushurl"))
@pytest.mark.parametrize("scheme", ("http", "https"))
@pytest.mark.parametrize("fragment", ("#review-a", "#"))
def test_http_remote_literal_fragment_fails_closed(
    tmp_path: Path, scope: str, field: str, scheme: str, fragment: str
) -> None:
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    value = f"{scheme}://example.invalid/repo.git{fragment}"
    git(path, "config", "--" + scope, f"remote.origin.{field}", value)
    assert git(path, "config", "--" + scope, "--get", f"remote.origin.{field}") == value
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("field", ("url", "pushurl"))
@pytest.mark.parametrize("value", (
    "https://example.invalid/repo%23review.git",
    "https://example.invalid/repo.git?ref=review%23a",
    "http://example.invalid/repo.git?ref=review",
    "git@example.invalid:repo#literal.git",
))
def test_encoded_hash_query_and_non_http_literal_remain_supported(
    tmp_path: Path, scope: str, field: str, value: str
) -> None:
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    git(path, "config", "--" + scope, f"remote.origin.{field}", value)
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"
