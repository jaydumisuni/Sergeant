"""SAE-160 must reject concealed remote marks without banning visible accents."""

from pathlib import Path
import os
import subprocess

import pytest

from main_review.sae160_checkout_preflight import inspect_checkout


@pytest.fixture(autouse=True)
def _isolate_inherited_loader_controls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exclude CI runner loader and agent settings from checkout fixtures.

    SAE-160's production preflight must continue to reject these overrides.
    The isolation applies only to this test module, matching the existing
    SAE-160 repository-only preparation fixture.
    """
    for name in tuple(os.environ):
        if name.startswith(("LD_", "DYLD_")) or name in (
            "SSH_AUTH_SOCK", "SSH_AGENT_PID"
        ):
            monkeypatch.delenv(name, raising=False)


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


def test_inherited_loader_override_remains_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fixture isolation must not weaken production ambient-authority denial."""
    path, head = checkout(tmp_path)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/untrusted/runner/loader")
    result = inspect_checkout(path, head)
    assert result.blockers == ("ambient_git_authority_override",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("suffix", ("url", "fetch", "tagOpt", "pruneTags"))
@pytest.mark.parametrize("codepoint", (
    0x2065,  # reserved word-joiner slot
    0xFFF0, 0xFFF8,  # reserved specials
    0xE0000,  # reserved tag scalar
    0xE0002, 0xE001F,  # reserved tag controls
    0xE0080, 0xE00FF,  # reserved tag extension
    0xE01F0, 0xE0FFF,  # reserved variation extension
))
def test_git_accepted_reserved_default_ignorable_remote_marks_fail_closed(
    tmp_path: Path, scope: str, suffix: str, codepoint: int,
) -> None:
    """Git-accepted unassigned default-ignorable names are not review identities."""
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    remote = f"hidden{chr(codepoint)}peer"
    value = {
        "url": "https://example.invalid/remote.git",
        "fetch": f"+refs/heads/*:refs/remotes/{remote}/*",
        "tagOpt": "--no-tags",
        "pruneTags": "false",
    }[suffix]
    # The Git config write must succeed: otherwise rejection proves nothing.
    git(path, "config", "--" + scope, f"remote.{remote}.{suffix}", value)
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("suffix", ("url", "pushurl"))
@pytest.mark.parametrize("mark", (
    "\u034f",       # combining grapheme joiner
    "\u2800",       # Braille blank
    "\ufe0f",       # variation selector
    "\U000e0100",   # supplementary variation selector
    "\u2065",       # reserved default-ignorable slot
    "\ufff0",       # reserved specials
    "\U000e0002",   # reserved tag control
))
def test_invisible_remote_url_destinations_fail_closed(
    tmp_path: Path, scope: str, suffix: str, mark: str,
) -> None:
    """A visible remote name cannot launder an invisible fetch/push destination."""
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    url = f"https://example.invalid/review{mark}path.git"
    git(path, "config", "--" + scope, f"remote.origin.{suffix}", url)
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("url", (
    "https://example.invalid/cafe\u0301.git",
    "https://example.invalid/\ud55c\uae00.git",
    "https://example.invalid/ordinary space.git",
))
def test_visible_unicode_and_spaces_in_remote_url_remain_supported(
    tmp_path: Path, url: str,
) -> None:
    """The local preflight does not confuse ordinary URL text with hidden marks."""
    path, head = checkout(tmp_path)
    git(path, "config", "--local", "remote.origin.url", url)
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("suffix", ("url", "fetch", "tagOpt", "pruneTags"))
@pytest.mark.parametrize("separator", (
    "\u2044",  # fraction slash
    "\u2215",  # division slash
    "\u29f8",  # big solidus
    "\uff0f",  # fullwidth solidus
    "\u2216",  # set minus
    "\uff3c",  # fullwidth reverse solidus
))
def test_git_accepted_remote_separator_confusables_fail_closed(
    tmp_path: Path, scope: str, suffix: str, separator: str,
) -> None:
    """A visually path-like remote name must not disguise its ref namespace."""
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    remote = f"source{separator}mirror"
    value = {
        "url": "https://example.invalid/remote.git",
        "fetch": f"+refs/heads/*:refs/remotes/{remote}/*",
        "tagOpt": "--no-tags",
        "pruneTags": "false",
    }[suffix]
    # Git accepts these names; denial must come from Sergeant, not Git.
    git(path, "config", "--" + scope, f"remote.{remote}.{suffix}", value)
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scopes", (
    ("local", "local"),
    ("worktree", "worktree"),
    ("local", "worktree"),
    ("worktree", "local"),
))
@pytest.mark.parametrize("reverse", (False, True))
def test_nfc_colliding_remote_subsections_fail_closed(
    tmp_path: Path, scopes: tuple[str, str], reverse: bool,
) -> None:
    """Git accepts distinct names that normalize to one reviewed identity."""
    path, head = checkout(tmp_path)
    if "worktree" in scopes:
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    names = ("review-café", "review-cafe\u0301")
    if reverse:
        names = names[::-1]
    for scope, name in zip(scopes, names):
        git(path, "config", "--" + scope, f"remote.{name}.url",
            "https://example.invalid/remote.git")
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


def test_distinct_visible_accented_remote_names_remain_supported(
    tmp_path: Path,
) -> None:
    """NFC collision denial must not become a blanket Unicode ban."""
    path, head = checkout(tmp_path)
    for name in ("review-café", "review-cafè"):
        git(path, "config", "--local", f"remote.{name}.url",
            "https://example.invalid/remote.git")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scopes", (
    ("local", "local"),
    ("worktree", "worktree"),
    ("local", "worktree"),
    ("worktree", "local"),
))
@pytest.mark.parametrize("names", (
    ("review-A", "review-Ａ"),  # Fullwidth Latin A
    ("review-1", "review-①"),  # Circled digit one
    ("review-IV", "review-Ⅳ"),  # Roman numeral four
))
@pytest.mark.parametrize("reverse", (False, True))
def test_nfkc_colliding_remote_subsections_fail_closed(
    tmp_path: Path, scopes: tuple[str, str],
    names: tuple[str, str], reverse: bool,
) -> None:
    """Git-valid compatibility aliases must not split reviewed remote custody."""
    path, head = checkout(tmp_path)
    if "worktree" in scopes:
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    for scope, name in zip(scopes, names[::-1] if reverse else names):
        git(path, "config", "--" + scope, f"remote.{name}.url",
            "https://example.invalid/remote.git")
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("names", (
    ("review-Ａ",),
    ("review-Ａ", "review-Ｂ"),
    ("review-①", "review-②"),
))
def test_distinct_visible_compatibility_remote_names_remain_supported(
    tmp_path: Path, names: tuple[str, ...],
) -> None:
    """Do not ban standalone visible Unicode compatibility characters."""
    path, head = checkout(tmp_path)
    for name in names:
        git(path, "config", "--local", f"remote.{name}.url",
            "https://example.invalid/remote.git")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scopes", (
    ("local", "local"),
    ("worktree", "worktree"),
    ("local", "worktree"),
    ("worktree", "local"),
))
@pytest.mark.parametrize("names", (
    ("Review", "review"),
    ("review-Straße", "review-STRASSE"),
    ("review-İ", "review-i\u0307"),
))
@pytest.mark.parametrize("reverse", (False, True))
def test_casefold_colliding_remote_subsections_fail_closed(
    tmp_path: Path, scopes: tuple[str, str],
    names: tuple[str, str], reverse: bool,
) -> None:
    """Distinct Git config keys must not alias one case-insensitive identity."""
    path, head = checkout(tmp_path)
    if "worktree" in scopes:
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    for scope, name in zip(scopes, names[::-1] if reverse else names):
        git(path, "config", "--" + scope, f"remote.{name}.url",
            "https://example.invalid/remote.git")
    # Verify Git retains both independent keys: the guard, not Git's parser,
    # must reject the cross-platform identity collision.
    config_keys = git(path, "config", "--list", "--name-only").splitlines()
    assert all(f"remote.{name}.url" in config_keys for name in names)
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


def test_distinct_casefolded_remote_names_remain_supported(tmp_path: Path) -> None:
    """Visible, noncolliding remote names remain valid."""
    path, head = checkout(tmp_path)
    for name in ("review-café", "review-cafè", "review-A"):
        git(path, "config", "--local", f"remote.{name}.url",
            "https://example.invalid/remote.git")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("suffix", ("url", "fetch", "tagOpt", "pruneTags"))
@pytest.mark.parametrize("codepoint", (
    0x0378,   # unassigned Greek code point
    0x2FE0,   # unassigned ideographic description extension
    0x1D455,  # unassigned mathematical alphanumeric scalar
))
def test_git_accepted_unassigned_remote_identity_fails_closed(
    tmp_path: Path, scope: str, suffix: str, codepoint: int,
) -> None:
    """Unassigned Unicode has no stable visible remote identity across hosts."""
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    remote = f"review{chr(codepoint)}remote"
    value = {
        "url": "https://example.invalid/remote.git",
        "fetch": f"+refs/heads/*:refs/remotes/{remote}/*",
        "tagOpt": "--no-tags",
        "pruneTags": "false",
    }[suffix]
    git(path, "config", "--" + scope, f"remote.{remote}.{suffix}", value)
    assert f"remote.{remote}.{suffix}".lower() in git(
        path, "config", "--list", "--name-only"
    ).lower()
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("scope", ("local", "worktree"))
@pytest.mark.parametrize("suffix", ("url", "pushurl"))
@pytest.mark.parametrize("codepoint", (
    0x0378,   # unassigned Greek code point
    0x2FE0,   # unassigned ideographic description extension
    0x1D455,  # unassigned mathematical alphanumeric scalar
))
def test_git_accepted_unassigned_remote_url_fails_closed(
    tmp_path: Path, scope: str, suffix: str, codepoint: int,
) -> None:
    """Remote URL destinations must not borrow unassigned Unicode identity."""
    path, head = checkout(tmp_path)
    if scope == "worktree":
        git(path, "config", "--local", "extensions.worktreeConfig", "true")
    url = f"https://example.invalid/review{chr(codepoint)}source.git"
    git(path, "config", "--" + scope, f"remote.origin.{suffix}", url)
    assert git(path, "config", "--get", f"remote.origin.{suffix}") == url
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_git_metadata",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("suffix", ("url", "pushurl"))
def test_visible_unicode_remote_url_still_qualifies(tmp_path: Path, suffix: str) -> None:
    """Ordinary assigned Unicode URL path characters remain supported."""
    path, head = checkout(tmp_path)
    git(path, "config", "--local", f"remote.origin.{suffix}",
        "https://example.invalid/review-café-한글.git")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"
