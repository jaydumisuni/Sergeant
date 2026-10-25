"""SAE-160 checkout-shape preflight; not independent qualification evidence.

A standalone checkout must be bound to an exact head and free of mutable
worktree/alternate-object dependencies. This check does not establish that the
checkout was freshly cloned or that installation and external proof passed.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import chain
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
        # Git control itself is a replacement authority: a foreign owner of
        # .git may rewrite its descendants even when its mode is 0755.
        try:
            git_control = gitdir.lstat()
        except OSError:
            blockers.append("mutable_git_authority_ownership")
        else:
            if not stat.S_ISDIR(git_control.st_mode) or git_control.st_uid not in trusted_owners:
                blockers.append("mutable_git_authority_ownership")
    def foreign_git_owner(entry: Path) -> bool:
        """POSIX Git metadata is mutable by its owner even at mode 0644/0755."""
        if os.name != "posix":
            return False
        try:
            return entry.lstat().st_uid not in {0, os.geteuid()}
        except OSError:
            return True  # Disappearing authority cannot establish custody.

    def external_git_entry(entry: Path) -> bool:
        """Reject Git metadata aliases and special files before checkout Git."""
        return (
            entry.is_symlink()
            or (entry.exists() and not entry.is_file() and not entry.is_dir())
            or (entry.is_file() and entry.stat().st_nlink > 1)
        )

    # A standalone checkout cannot bind immutable authority to control
    # directories that other local principals can rewrite. Check before
    # invoking checkout Git, which could otherwise read swapped refs/objects.
    for relative in ("", "objects", "objects/info", "objects/pack",
                     "refs", "refs/heads", "refs/tags", "info"):
        authority_dir = gitdir / relative
        try:
            metadata = authority_dir.lstat()
        except OSError:
            continue  # Missing/invalid stores are rejected by later checks.
        mode = metadata.st_mode
        if stat.S_ISDIR(mode) and foreign_git_owner(authority_dir):
            blockers.append("mutable_git_authority_ownership")
            break
        if stat.S_ISDIR(mode) and mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
            break
    # Git control metadata can silently borrow authority from another checkout
    # even when the object store itself is local and the observed HEAD matches.
    # Pseudo-refs can influence Git status, merge/rebase state, and subsequent
    # review even when HEAD and the object store are otherwise private.
    # Check their filesystem custody before invoking any checkout Git command.
    control_files = (
        "config", "config.worktree", "HEAD", "index", "packed-refs",
        "refs", "shallow", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD",
        "REBASE_HEAD", "FETCH_HEAD", "ORIG_HEAD", "AUTO_MERGE",
        "BISECT_EXPECTED_REV",
    )
    for name in control_files:
        entry = gitdir / name
        if external_git_entry(entry):
            blockers.append("external_git_metadata")
            break
        if entry.is_file() and foreign_git_owner(entry):
            blockers.append("mutable_git_authority_ownership")
            break
        # Control files can be modified by other local principals even when
        # they have no external alias. Reject before checkout Git reads them.
        if entry.is_file() and entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
            break
    # Git split-index sharedindex.* files are index authority, not ordinary
    # checkout data. Reject symlink and hardlink aliases before checkout Git.
    for entry in gitdir.glob("sharedindex.*"):
        if external_git_entry(entry):
            blockers.append("external_git_metadata")
            break
        if entry.is_file() and foreign_git_owner(entry):
            blockers.append("mutable_git_authority_ownership")
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
            if external_git_entry(entry):
                blockers.append("external_git_metadata")
                break
            if foreign_git_owner(entry):
                blockers.append("mutable_git_authority_ownership")
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
            if external_git_entry(entry):
                blockers.append("external_git_metadata")
                break
            if foreign_git_owner(entry):
                blockers.append("mutable_git_authority_ownership")
                break
            # A peer-writable exclude/attributes file (or its parent) can
            # alter status semantics even without an external filesystem alias.
            if (entry.is_file() or entry.is_dir()) and (
                entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                blockers.append("mutable_git_authority_permissions")
                break
    # Reflogs are revision-selection history (HEAD@{n}, branch@{n}), not
    # ordinary checkout content. A symlink, hardlink, foreign owner, or
    # peer-writable directory/file can substitute history after preflight.
    # Standalone clones may legitimately omit logs; only existing metadata
    # must satisfy the same custody boundary as refs and object metadata.
    logs = gitdir / "logs"
    if logs.is_symlink() or (logs.exists() and not logs.is_dir()):
        blockers.append("external_git_metadata")
    elif logs.is_dir():
        for entry in chain((logs,), logs.rglob("*")):
            if external_git_entry(entry):
                blockers.append("external_git_metadata")
                break
            if foreign_git_owner(entry):
                blockers.append("mutable_git_authority_ownership")
                break
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
    # Executable diff drivers/textconv can run during subsequent review, even
    # when status is clean; reject their configuration before checkout Git.
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
            if external_git_entry(entry):
                blockers.append("external_object_store")
                break
            if foreign_git_owner(entry):
                blockers.append("mutable_git_authority_ownership")
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
                if foreign_git_owner(shard):
                    blockers.append("mutable_git_authority_ownership")
                    break
                if shard.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                    blockers.append("mutable_git_authority_permissions")
                    break
                for entry in shard.iterdir():
                    if external_git_entry(entry):
                        blockers.append("external_object_store")
                        break
                    if foreign_git_owner(entry):
                        blockers.append("mutable_git_authority_ownership")
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
            if external_git_entry(entry):
                blockers.append("external_object_store")
                break
            if foreign_git_owner(entry):
                blockers.append("mutable_git_authority_ownership")
                break
            if (entry.is_file() or entry.is_dir()) and (
                entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                blockers.append("mutable_git_authority_permissions")
                break
    alternates = objects / "info" / "alternates"
    if alternates.exists() or alternates.is_symlink():
        blockers.append("external_object_alternates")
    # A dangling commondir symlink is still an external authority alias:
    # exists() follows the link and incorrectly treats it as absent.
    commondir = gitdir / "commondir"
    if commondir.exists() or commondir.is_symlink():
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
