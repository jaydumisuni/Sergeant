"""SAE-160 must reject concealed remote marks without banning visible accents."""

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
    subprocess.check_call(["git", "init", "-q", str(origin)])
    git(origin, "config", "user.email", "test@example.invalid")
    git(origin, "config", "user.name", "Test")
    (origin / "tracked.txt").write_text("frozen\n")
    git(origin, "add", "tracked.txt")
    git(origin, "commit", "-qm", "fixture")
    clone = tmp_path / "clone"
    subprocess.check_call([
        "git", "clone", "--no-hardlinks", "-q", str(origin), str(clone)
    ])
    return clone, git(clone, "rev-parse", "HEAD")


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("remote", (
    "hidden\u1160peer",  # Hangul jungseong filler
    "hidden\u17b4peer",  # Khmer vowel inherent AQ
    "hidden\u17b5peer",  # Khmer vowel inherent AA
    "hidden\u180bpeer",  # Mongolian variation selector one
    "hidden\u180fpeer",  # Mongolian variation selector four
    "hidden\ufe0fpeer",  # Variation selector 16
    "hidden\U000e0100peer",  # Variation selector 17
    "hidden\U000e01efpeer",  # Variation selector 256
))
@pytest.mark.parametrize("suffix", ("url", "fetch", "tagOpt", "pruneTags"))
def test_git_accepted_default_ignorable_remote_marks_fail_closed(
    tmp_path, scope, remote, suffix,
):
    """A clean Git checkout does not qualify visually hidden remote keys."""
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    value = {
        "url": "https://example.invalid/remote.git",
        "fetch": f"+refs/heads/*:refs/remotes/{remote}/*",
        "tagOpt": "--no-tags",
        "pruneTags": "false",
    }[suffix]
    git(path, "config", "--" + scope, f"remote.{remote}.{suffix}", value)
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("remote", ("visible-cafe\u0301", "visible-\ud55c\uae00"))
def test_visible_combining_accents_and_hangul_remain_supported(
    tmp_path, scope, remote,
):
    """Ordinary visible Unicode names retain the checkout-only authority."""
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    git(path, "config", "--" + scope, f"remote.{remote}.url",
        "https://example.invalid/remote.git")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"
