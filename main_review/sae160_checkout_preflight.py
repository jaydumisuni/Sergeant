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
        "GIT_NAMESPACE", "GIT_EXTERNAL_DIFF", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
        # Git tracing can write outside the checkout before a read-only
        # preflight reaches its later fail-closed decision.
        "GIT_TRACE", "GIT_TRACE2", "GIT_TRACE2_EVENT", "GIT_TRACE2_PERF",
    }
    # Git also honors GIT_TRACE_SETUP, GIT_TRACE_PACKET, and other trace
    # variants that can write outside the checkout during the config probe.
    # Reject the entire trace namespace before starting any Git subprocess.
    if authority_env.intersection(os.environ) or any(
        name.startswith("GIT_TRACE") for name in os.environ
    ):
        # Do not even probe local config with untrusted ambient Git controls:
        # git config itself is a Git process and can honor these overrides.
        return CheckoutPreflight(expected, None, ("ambient_git_authority_override",))
    gitdir = root / ".git"
    if (
        not root.is_dir()
        or root != root.resolve()
        or not gitdir.is_dir()
        or gitdir.is_symlink()
    ):
        return CheckoutPreflight(expected, None, ("not_standalone_checkout",))
    # A private .git directory is not sufficient if another principal owns
    # or can rewrite the checkout root or one of its ancestor directories.
    # A trusted root-owned sticky directory (such as /tmp) is the exception:
    # the sticky bit prevents peers from replacing someone else's entry.
    # This is POSIX-specific custody evidence, not Windows qualification.
    if os.name == "posix":
        trusted_owners = {0, os.geteuid()}
        for directory in (root, *root.parents):
            try:
                metadata = directory.lstat()
            except OSError:
                blockers.append("mutable_checkout_ancestry")
                break
            if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid not in trusted_owners:
                blockers.append("mutable_checkout_ancestry")
                break
            if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                if metadata.st_uid != 0 or not metadata.st_mode & stat.S_ISVTX:
                    blockers.append("mutable_checkout_ancestry")
                    break
    # Mode 0755 is not sufficient custody for Git metadata: a foreign
    # owner can replace a private ref, object, index or config regardless
    # of its group/world mode. Inspect all .git descendants without
    # following directory symlinks before starting even git config.
    if os.name == "posix":
        def _metadata_walk_error(_error: OSError) -> None:
            blockers.append("mutable_git_authority_permissions")

        for directory, child_dirs, child_files in os.walk(
            gitdir, followlinks=False, onerror=_metadata_walk_error
        ):
            for entry in (Path(directory), *(
                Path(directory) / name for name in (*child_dirs, *child_files)
            )):
                try:
                    metadata = entry.lstat()
                except OSError:
                    blockers.append("mutable_git_authority_permissions")
                    break
                if metadata.st_uid not in trusted_owners:
                    blockers.append("mutable_git_authority_permissions")
                    break
            if blockers:
                break
        # A failed ownership/ancestry check must not reach git config:
        # that probe is itself a Git subprocess.
        if blockers:
            return CheckoutPreflight(expected, None, tuple(sorted(set(blockers))))

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
        # Control files can be modified by other local principals even when
        # they have no external alias. Reject before checkout Git reads them.
        if entry.is_file() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
            break
    # Git split-index sharedindex.* files are index authority, not ordinary
    # checkout data. Reject symlink and hardlink aliases before checkout Git.
    for entry in gitdir.glob("sharedindex.*"):
        if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
            blockers.append("external_git_metadata")
            break
        # A peer-writable split-index backing file can change checkout status
        # without any symlink or hardlink alias. Reject it before checkout Git.
        if entry.is_file() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
            break
    # Nested refs are authority too: a symlinked or hardlinked branch/tag ref
    # can redirect an otherwise local checkout to externally mutable metadata.
    refs = gitdir / "refs"
    if refs.is_dir() and not refs.is_symlink():
        for entry in refs.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
            # Git can resolve a nested ref through directories writable by
            # another principal even when the ref file itself is private.
            if entry.is_dir() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
                break
            if entry.is_file() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
                break
    # Git reads local exclude, attributes, and sparse-checkout rules from
    # .git/info. External aliases can mask changes from a clean status check.
    info_dir = gitdir / "info"
    if info_dir.is_symlink():
        blockers.append("external_git_metadata")
    elif info_dir.is_dir():
        for entry in info_dir.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
            # A peer-writable exclude/attributes file (or its parent) can
            # alter status semantics even without an external filesystem alias.
            if (entry.is_file() or entry.is_dir()) and (
                entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                blockers.append("mutable_git_authority_permissions")
                break
    # Git include directives borrow configuration from another path, even if
    # that path is not presently active (includeIf) or is currently missing.
    # core.fsmonitor can execute a checkout-controlled program during status;
    # reject it before issuing any Git operation that may invoke that program.
    # Checkout-controlled filter commands can also execute during Git status.
    # External diff drivers/textconv can execute during later review; status alone
    # does not establish that this checkout has no executable diff authority.
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
                 r"^(include|includeif)\..*|^core\.(fsmonitor|excludesfile|attributesfile|worktree|hookspath|sparsecheckout|sparsecheckoutcone)$|^filter\..+\.(clean|smudge|process)$|^diff\.(external|.+\.(command|textconv))$"],
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
    if pack.is_dir():
        for entry in pack.iterdir():
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_object_store")
                break
            if entry.is_file() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
                break
    # Loose Git objects can also borrow mutable external authority via symlinks
    # or hardlinks; checking pack files alone is insufficient.
    if objects.is_dir():
        for shard in objects.iterdir():
            if shard.name in {"info", "pack"}:
                continue
            if shard.is_symlink():
                blockers.append("external_object_store")
                break
            if shard.is_dir():
                if shard.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    blockers.append("mutable_git_authority_permissions")
                    break
                for entry in shard.iterdir():
                    if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                        blockers.append("external_object_store")
                        break
                    if entry.is_file() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                        blockers.append("mutable_git_authority_permissions")
                        break
                if blockers:
                    break
    # Git commit-graph and split-chain metadata are authority read during
    # history/status. Reject aliases and peer-writable files or directories at
    # every depth before issuing any checkout Git command.
    info = objects / "info"
    if info.is_dir():
        for entry in info.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_object_store")
                break
            if (entry.is_file() or entry.is_dir()) and (
                entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                blockers.append("mutable_git_authority_permissions")
                break
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
    # A populated Git submodule can leave the parent's status perfectly clean,
    # while its nested repository borrows independently configured authority.
    # Inspect index modes before status can descend into any submodule Git.
    index_entries = git("ls-files", "--stage")
    if index_entries is None:
        blockers.append("unverified_index_entries")
    elif any(
        line.startswith("160000 ") for line in index_entries.splitlines()
    ):
        blockers.append("external_submodule_dependency")
    if blockers:
        return CheckoutPreflight(expected, head, tuple(sorted(set(blockers))))
    status = git("status", "--porcelain", "--untracked-files=all")
    if status is None or status:
        blockers.append("dirty_or_unverified_checkout")
    return CheckoutPreflight(expected, head, tuple(sorted(set(blockers))))
