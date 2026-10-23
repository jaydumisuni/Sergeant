"""SAE-160 checkout-shape preflight; not independent qualification evidence.

A standalone checkout must be bound to an exact head and free of mutable
worktree/alternate-object dependencies. This check does not establish that the
checkout was freshly cloned or that installation and external proof passed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import stat
import subprocess

from .review_world import require_git_object_id


@dataclass(frozen=True)
class CheckoutPreflight:
    expected_head: str
    observed_head: str | None
    blockers: tuple[str, ...]
    authority_gain: str = "NONE"


def inspect_checkout(checkout: Path, expected_head: str) -> CheckoutPreflight:
    """Return fail-closed, local-only evidence about a checkout's shape."""
    expected = require_git_object_id(expected_head, "SAE-160 expected_head")
    # Preserve the caller's lexical path: resolve() would conceal a symlinked
    # parent and make an externally aliased checkout appear standalone.
    root = Path(checkout).absolute()
    blockers: list[str] = []
    # Ambient Git overrides can redirect object, index or repository authority
    # outside the standalone checkout without changing its visible .git shape.
    authority_env = {
        "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_INDEX_FILE",
        "GIT_NAMESPACE", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
    }
    if authority_env.intersection(os.environ):
        blockers.append("ambient_git_authority_override")
    gitdir = root / ".git"
    if (
        not root.is_dir()
        or root != root.resolve()
        or not gitdir.is_dir()
        or gitdir.is_symlink()
    ):
        return CheckoutPreflight(expected, None, ("not_standalone_checkout",))
    # A standalone checkout cannot bind immutable authority to control
    # directories that other local principals can rewrite. Check before
    # invoking checkout Git, which could otherwise read swapped refs/objects.
    for relative in ("", "objects", "objects/info", "objects/pack",
                     "refs", "refs/heads", "refs/tags", "info"):
        authority_dir = gitdir / relative
        try:
            mode = authority_dir.lstat().st_mode
        except OSError:
            continue  # Missing/invalid stores are rejected by later checks.
        if stat.S_ISDIR(mode) and mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
            break
    # Git control metadata can silently borrow authority from another checkout
    # even when the object store itself is local and the observed HEAD matches.
    for name in ("config", "config.worktree", "HEAD", "index", "packed-refs", "refs", "shallow"):
        entry = gitdir / name
        if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
            blockers.append("external_git_metadata")
            break
    # Git split-index sharedindex.* files are index authority, not ordinary
    # checkout data. Reject symlink and hardlink aliases before checkout Git.
    if any(
        entry.is_symlink()
        or (entry.is_file() and entry.stat().st_nlink > 1)
        for entry in gitdir.glob("sharedindex.*")
    ):
        blockers.append("external_git_metadata")
    # Nested refs are authority too: a symlinked or hardlinked branch/tag ref
    # can redirect an otherwise local checkout to externally mutable metadata.
    refs = gitdir / "refs"
    if refs.is_dir() and not refs.is_symlink():
        for entry in refs.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
    # Git reads local exclude, attributes, and sparse-checkout rules from
    # .git/info. External aliases can mask changes from a clean status check.
    info_dir = gitdir / "info"
    if info_dir.is_symlink() or (
        info_dir.is_dir() and any(
            entry.is_symlink()
            or (entry.is_file() and entry.stat().st_nlink > 1)
            for entry in info_dir.rglob("*")
        )
    ):
        blockers.append("external_git_metadata")
    # Git include directives borrow configuration from another path, even if
    # that path is not presently active (includeIf) or is currently missing.
    # core.fsmonitor can execute a checkout-controlled program during status;
    # reject it before issuing any Git operation that may invoke that program.
    # Checkout-controlled filter commands can also execute during Git status.
    # core.attributesFile can borrow mutable attribute rules outside the clone.
    # Read only the local file with includes explicitly disabled; an invalid
    # config cannot establish standalone authority either.
    for config_name in ("config", "config.worktree"):
        config_file = gitdir / config_name
        if not config_file.exists() or not config_file.is_file():
            continue
        try:
            config_probe = subprocess.run(
                ["git", "config", "--no-includes", "--file", str(config_file),
                 "--name-only", "--get-regexp",
                 r"^(include|includeif)\..*|^core\.(fsmonitor|excludesfile|attributesfile|worktree|hookspath|sparsecheckout|sparsecheckoutcone)$|^filter\..+\.(clean|smudge|process)$"],
                capture_output=True, text=True, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            blockers.append("external_git_metadata")
            continue
        if config_probe.returncode not in (0, 1) or config_probe.stdout.strip():
            blockers.append("external_git_metadata")
    objects = gitdir / "objects"
    if objects.is_symlink() or not objects.is_dir():
        blockers.append("external_object_store")
    if (objects / "info").is_symlink() or (objects / "pack").is_symlink():
        blockers.append("external_object_store")
    pack = objects / "pack"
    if pack.is_dir() and any(
        entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1)
        for entry in pack.iterdir()
    ):
        blockers.append("external_object_store")
    # Loose Git objects can also borrow mutable external authority via symlinks
    # or hardlinks; checking pack files alone is insufficient.
    if objects.is_dir():
        for shard in objects.iterdir():
            if shard.name in {"info", "pack"}:
                continue
            if shard.is_symlink() or (
                shard.is_dir() and any(
                    entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1)
                    for entry in shard.iterdir()
                )
            ):
                blockers.append("external_object_store")
                break
    # Git commit-graph and other object metadata may be read from objects/info.
    # Reject external aliases there, including split commit-graph chain members.
    info = objects / "info"
    if info.is_dir() and any(
        entry.is_symlink()
        or (entry.is_file() and entry.stat().st_nlink > 1)
        or (
            entry.is_dir()
            and any(
                child.is_symlink()
                or (child.is_file() and child.stat().st_nlink > 1)
                for child in entry.iterdir()
            )
        )
        for entry in info.iterdir()
    ):
        blockers.append("external_object_store")
    alternates = objects / "info" / "alternates"
    if alternates.exists() or alternates.is_symlink():
        blockers.append("external_object_alternates")
    if (gitdir / "commondir").exists():
        blockers.append("shared_git_directory")

    # Never invoke checkout Git while its configuration or metadata can
    # redirect authority or execute an external filesystem monitor.
    # Local metadata inspection is sufficient to reject this candidate.
    if blockers:
        return CheckoutPreflight(expected, None, tuple(sorted(set(blockers))))

    # Checkout Git must not inherit host-global or system configuration.
    # In particular, an ambient core.fsmonitor can execute external code
    # during status even when the checkout's local config is clean.
    isolated_git_env = os.environ.copy()
    isolated_git_env["GIT_CONFIG_NOSYSTEM"] = "1"
    isolated_git_env["GIT_CONFIG_GLOBAL"] = os.devnull

    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True, check=True, timeout=10,
                env=isolated_git_env,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip()

    toplevel = git("rev-parse", "--show-toplevel")
    if toplevel is None or Path(toplevel).resolve() != root.resolve():
        blockers.append("checkout_root_mismatch")
    head = git("rev-parse", "--verify", "HEAD")
    if head != expected:
        blockers.append("head_mismatch")
    shallow = git("rev-parse", "--is-shallow-repository")
    if shallow != "false":
        blockers.append("shallow_or_unverified_history")
    status = git("status", "--porcelain", "--untracked-files=all")
    if status is None or status:
        blockers.append("dirty_or_unverified_checkout")
    return CheckoutPreflight(expected, head, tuple(sorted(set(blockers))))
