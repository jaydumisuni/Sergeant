"""SAE-160 HTTP remote fragments are not fetched evidence identities.

Git config stores literal fragment text, but HTTP clients do not transmit URL
fragments to the server. This is repository-only preflight, not SAE-150 proof.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import os

import pytest

from main_review.sae160_checkout_preflight import inspect_checkout


# Mirrors the exact-name and namespace guards in inspect_checkout; fixture
# isolation must not accidentally test an ambient override instead of URL custody.
_REJECTED_AMBIENT_NAMES = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_INDEX_FILE", "GIT_NAMESPACE", "GIT_EXTERNAL_DIFF",
    "GIT_REPLACE_REF_BASE", "GIT_ATTR_SOURCE", "GIT_EXEC_PATH", "GIT_SHALLOW_FILE",
    "GIT_TEMPLATE_DIR", "GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND",
    "GIT_SSH_VARIANT", "GIT_PROXY_COMMAND", "SSH_ASKPASS", "SSH_ASKPASS_REQUIRE",
    "SSH_AUTH_SOCK", "SSH_AGENT_PID", "GIT_ALLOW_PROTOCOL", "GIT_PROTOCOL_FROM_USER",
    "GIT_PROTOCOL", "GIT_TERMINAL_PROMPT", "GIT_PAGER", "GIT_EDITOR",
    "GIT_SEQUENCE_EDITOR", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG",
    "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM", "GIT_TRACE",
    "GIT_TRACE2", "GIT_TRACE2_EVENT", "GIT_TRACE2_PERF", "http_proxy",
    "https_proxy", "all_proxy", "no_proxy", "HTTP_PROXY",
    "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "SSL_CERT_FILE",
    "SSL_CERT_DIR", "CURL_CA_BUNDLE", "SSLKEYLOGFILE",
})
_REJECTED_AMBIENT_PREFIXES = (
    "GIT_TRACE", "GIT_SSL_", "GIT_PROXY_SSL_", "GIT_HTTP_", "GIT_CURL_", "GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_", "LD_", "DYLD_"
)


@pytest.fixture(autouse=True)
def _isolate_runner_transport_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep ambient authority overrides out of fragment-classification tests."""
    for name in tuple(os.environ):
        if name in _REJECTED_AMBIENT_NAMES or name.startswith(_REJECTED_AMBIENT_PREFIXES):
            monkeypatch.delenv(name, raising=False)


def _fixture_git_env() -> dict[str, str]:
    """Disable external Git config for fixture setup only, not inspect_checkout."""
    env = os.environ.copy()
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    })
    return env


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True, env=_fixture_git_env()
    ).strip()


def checkout(tmp_path: Path) -> tuple[Path, str]:
    origin = tmp_path / "origin"
    origin.mkdir()
    subprocess.check_call(["git", "init", "-q", str(origin)], env=_fixture_git_env())
    git(origin, "config", "user.email", "test@example.invalid")
    git(origin, "config", "user.name", "Fixture")
    (origin / "tracked.txt").write_text("pinned\n")
    git(origin, "add", "tracked.txt")
    git(origin, "commit", "-qm", "fixture")
    clone = tmp_path / "clone"
    subprocess.check_call(
        ["git", "clone", "-q", "--no-hardlinks", str(origin), str(clone)],
        env=_fixture_git_env()
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


def test_fixture_ignores_global_commit_signing_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A runner's global gpgSign setting must not break fixture setup."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text("[commit]\\n    gpgSign = true\\n")
    monkeypatch.setenv("HOME", str(home))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path, head = checkout(workspace)
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"
