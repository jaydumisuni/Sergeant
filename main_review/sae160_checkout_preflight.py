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
        "GIT_EXEC_PATH", "GIT_ATTR_SOURCE",
        "GIT_SHALLOW_FILE", "GIT_REPLACE_REF_BASE", "GIT_NO_REPLACE_OBJECTS",
        "GIT_CEILING_DIRECTORIES", "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    }
    # Numbered GIT_CONFIG_KEY_n/VALUE_n and GIT_CONFIG_NOSYSTEM can alter
    # Git configuration even without the fixed-name overrides above.
    if authority_env.intersection(os.environ) or any(
        key.startswith(("GIT_CONFIG_", "GIT_TRACE", "GIT_TRACE2")) for key in os.environ
    ):
        blockers.append("ambient_git_authority_override")
    # Never invoke Git under inherited authority/trace overrides, even for
    # a diagnostic config probe: those variables can trigger external writes.
    if "ambient_git_authority_override" in blockers:
        return CheckoutPreflight(expected, None, tuple(blockers))
    # Reject missing and dangling paths before ancestor custody checks: a
    # sticky shared ancestor would otherwise stat a nonexistent child.
    if not root.is_dir():
        return CheckoutPreflight(expected, None, ("not_standalone_checkout",))
    # A peer-writable checkout root permits replacement of tracked source files
    # between exact-head inspection and qualification, even with private .git.
    if root.is_dir() and root.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        blockers.append("mutable_checkout_root_permissions")
    # A peer-writable immediate parent can replace the entire checkout
    # directory between inspection and use, regardless of root permissions.
    # A sticky parent (such as /tmp) still allows replacement by the owner
    # of the entry, so it is not sufficient authority for this preflight.
    # Every ancestor is part of the path's custody. A peer-writable
    # grandparent can replace an otherwise private parent directory.
    child = root
    for ancestor in root.parents:
        if ancestor.is_dir():
            mode = ancestor.stat().st_mode
            if mode & (stat.S_IWGRP | stat.S_IWOTH):
                # Sticky shared roots protect an entry owned by this process
                # from replacement by other unprivileged principals.
                if not (mode & stat.S_ISVTX and child.stat().st_uid == os.getuid()):
                    blockers.append("mutable_checkout_parent_permissions")
                    break
        child = ancestor
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
    for name in ("config", "config.worktree", "HEAD", "index", "packed-refs", "refs", "shallow",
                 "FETCH_HEAD", "ORIG_HEAD", "MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD",
                 "BISECT_START", "BISECT_LOG", "AUTO_MERGE"):
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
    if refs.is_symlink():
        blockers.append("external_git_metadata")
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
        # The directory itself can be replaced by peers even when its current
        # attribute and sparse-checkout files are private.
        if info_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
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
    # Git reflogs are writable control metadata. An aliased log can redirect
    # a later ref update outside the standalone checkout even if refs are local.
    logs_dir = gitdir / "logs"
    if logs_dir.is_symlink():
        blockers.append("external_git_metadata")
    elif logs_dir.is_dir():
        if logs_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
        for entry in logs_dir.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
            if (entry.is_file() or entry.is_dir()) and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
                break
    # Default Git hooks are executable checkout control metadata. Even if
    # this read-only preflight does not execute hooks, accepting an externally
    # aliased hook would make the qualified checkout unsafe for later actions.
    hooks_dir = gitdir / "hooks"
    if hooks_dir.is_symlink():
        blockers.append("external_git_metadata")
    elif hooks_dir.is_dir():
        if hooks_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
        for entry in hooks_dir.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
            if (entry.is_file() or entry.is_dir()) and entry.stat().st_mode & (
                stat.S_IWGRP | stat.S_IWOTH
            ):
                blockers.append("mutable_git_authority_permissions")
                break
    # Rerere cache entries can affect a later conflict resolution. Treat this
    # checkout-owned Git control tree with the same alias/permission custody
    # rules as hooks and reflogs, before any checkout Git invocation.
    rerere_dir = gitdir / "rr-cache"
    if rerere_dir.is_symlink():
        blockers.append("external_git_metadata")
    elif rerere_dir.is_dir():
        if rerere_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
        for entry in rerere_dir.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
            if (entry.is_file() or entry.is_dir()) and entry.stat().st_mode & (
                stat.S_IWGRP | stat.S_IWOTH
            ):
                blockers.append("mutable_git_authority_permissions")
                break
    # Submodule Git directories are checkout-owned control metadata too.
    # A linked or peer-writable module store must not inherit authority.
    modules_dir = gitdir / "modules"
    if modules_dir.is_symlink():
        blockers.append("external_git_metadata")
    elif modules_dir.is_dir():
        if modules_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
        for entry in modules_dir.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
            if (entry.is_file() or entry.is_dir()) and entry.stat().st_mode & (
                stat.S_IWGRP | stat.S_IWOTH
            ):
                blockers.append("mutable_git_authority_permissions")
                break
    # Legacy Git remotes/branches definitions are still repository control
    # metadata. An aliased or peer-writable entry can redirect later Git
    # operations even if modern refs and config are private.
    for legacy_name in ("branches", "remotes"):
        legacy_dir = gitdir / legacy_name
        if legacy_dir.is_symlink():
            blockers.append("external_git_metadata")
        elif legacy_dir.is_dir():
            if legacy_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
            for entry in legacy_dir.rglob("*"):
                if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                    blockers.append("external_git_metadata")
                    break
                if (entry.is_file() or entry.is_dir()) and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    blockers.append("mutable_git_authority_permissions")
                    break
    # In-progress cherry-pick and rebase control trees can influence later
    # Git operations. Reject external aliases and peer-writable custody before
    # invoking even a diagnostic Git command.
    for operation_name in ("sequencer", "rebase-merge", "rebase-apply"):
        operation_dir = gitdir / operation_name
        if operation_dir.is_symlink():
            blockers.append("external_git_metadata")
        elif operation_dir.is_dir():
            if operation_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
            for entry in operation_dir.rglob("*"):
                if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                    blockers.append("external_git_metadata")
                    break
                if (entry.is_file() or entry.is_dir()) and entry.stat().st_mode & (
                    stat.S_IWGRP | stat.S_IWOTH
                ):
                    blockers.append("mutable_git_authority_permissions")
                    break
    # A known local metadata blocker must stop before even the diagnostic
    # git-config probe; no Git subprocess is safe under aliased authority.
    if blockers:
        return CheckoutPreflight(expected, None, tuple(sorted(set(blockers))))

    objects = gitdir / "objects"
    # The object-store root itself must not be peer-writable: an attacker
    # could replace object shards after local metadata inspection.
    if objects.is_dir() and objects.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        blockers.append("mutable_git_authority_permissions")
    if objects.is_symlink() or not objects.is_dir():
        blockers.append("external_object_store")
    if (objects / "info").is_symlink() or (objects / "pack").is_symlink():
        blockers.append("external_object_store")
    pack = objects / "pack"
    if pack.is_dir():
        # The pack directory itself is object authority: a peer-writable
        # directory permits pack replacement even when current files are private.
        if pack.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
        for entry in pack.iterdir():
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_object_store")
                break
            if entry.is_file() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
                break
            # Pack adjunct directories (for example multi-pack-index metadata)
            # must not introduce a writable or externally aliased subtree.
            if entry.is_dir():
                for nested in entry.rglob("*"):
                    if nested.is_symlink() or (nested.is_file() and nested.stat().st_nlink > 1):
                        blockers.append("external_object_store")
                        break
                    if (nested.is_file() or nested.is_dir()) and (
                        nested.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                    ):
                        blockers.append("mutable_git_authority_permissions")
                        break
                if entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    blockers.append("mutable_git_authority_permissions")
                if blockers:
                    break
    # Loose Git objects can also borrow mutable external authority via symlinks
    # or hardlinks; checking pack files alone is insufficient.
    if objects.is_dir():
        for shard in objects.iterdir():
            if shard.name in {"info", "pack"}:
                continue
            if shard.is_symlink() or (shard.is_file() and shard.stat().st_nlink > 1):
                blockers.append("external_object_store")
                break
            if shard.is_file() and shard.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                blockers.append("mutable_git_authority_permissions")
                break
            if shard.is_dir():
                if shard.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    blockers.append("mutable_git_authority_permissions")
                    break
                # Reject aliases and mutable metadata at every nested depth,
                # not only immediate loose-object children.
                for entry in shard.rglob("*"):
                    if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                        blockers.append("external_object_store")
                        break
                    if (entry.is_file() or entry.is_dir()) and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                        blockers.append("mutable_git_authority_permissions")
                        break
                if blockers:
                    break
    # Git commit-graph and split-chain metadata are authority read during
    # history/status. Reject aliases and peer-writable files or directories at
    # every depth before issuing any checkout Git command.
    info = objects / "info"
    if info.is_dir() and info.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        blockers.append("mutable_git_authority_permissions")
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
    # A dangling commondir symlink is still an external authority binding.
    # Path.exists() follows the link and would silently miss that case.
    commondir = gitdir / "commondir"
    if commondir.exists() or commondir.is_symlink():
        blockers.append("shared_git_directory")

    # Never invoke checkout Git while its configuration or metadata can
    # redirect authority or execute an external filesystem monitor.
    # Local metadata inspection is sufficient to reject this candidate.
    if blockers:
        return CheckoutPreflight(expected, None, tuple(sorted(set(blockers))))

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
        # Already rejected aliases must never be read through git config.
        if config_file.is_symlink() or config_file.stat().st_nlink > 1:
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

    if blockers:
        return CheckoutPreflight(expected, None, tuple(sorted(set(blockers))))

    # Checkout Git must not inherit host-global or system configuration.
    # In particular, an ambient core.fsmonitor can execute external code
    # during status even when the checkout's local config is clean.
    isolated_git_env = os.environ.copy()
    isolated_git_env["GIT_CONFIG_NOSYSTEM"] = "1"
    isolated_git_env["GIT_CONFIG_GLOBAL"] = os.devnull
    # A read-only exact-head preflight must not download missing promisor objects.
    isolated_git_env["GIT_NO_LAZY_FETCH"] = "1"

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
