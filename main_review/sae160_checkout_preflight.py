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
        "GIT_NAMESPACE", "GIT_EXTERNAL_DIFF", "GIT_REPLACE_REF_BASE",
        "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
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
    # Default hooks are executable Git metadata. A symlinked hooks directory,
    # a hardlinked hook or a peer-writable hook can borrow mutable code from
    # outside this checkout even when HEAD and status are clean. Check before
    # starting any checkout Git subprocess; a clean status cannot qualify hooks.
    hooks_dir = gitdir / "hooks"
    if hooks_dir.is_symlink() or (hooks_dir.exists() and not hooks_dir.is_dir()):
        blockers.append("external_git_metadata")
    elif hooks_dir.is_dir():
        if os.name == "posix" and hooks_dir.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            blockers.append("mutable_git_authority_permissions")
        for entry in hooks_dir.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                blockers.append("external_git_metadata")
                break
            if os.name == "posix" and (entry.is_file() or entry.is_dir()) and (
                entry.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                blockers.append("mutable_git_authority_permissions")
                break
    # Any already-observed unsafe metadata must stop before the local Git
    # config probe, which is itself a Git subprocess.
    if blockers:
        return CheckoutPreflight(expected, None, tuple(sorted(set(blockers))))
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
    # Git replace refs can silently substitute an object while HEAD and status
    # remain unchanged. Disable replacement during every checkout Git probe.
    isolated_git_env["GIT_NO_REPLACE_OBJECTS"] = "1"
    # A read-only status must not refresh the index while its inode identity
    # is being compared across independent Git probes.
    isolated_git_env["GIT_OPTIONAL_LOCKS"] = "0"

    def control_identity(entry: Path) -> tuple[int, ...] | None:
        """Snapshot an authority file without following a substituted symlink."""
        try:
            metadata = entry.lstat()
        except OSError:
            return None
        if not stat.S_ISREG(metadata.st_mode):
            return None
        return (
            metadata.st_dev, metadata.st_ino, metadata.st_mode,
            metadata.st_uid, metadata.st_gid, metadata.st_nlink,
            metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns,
        )

    # HEAD/index and optional configuration/ref tables are independently
    # consulted by Git probes. Bind their pathname identities across the
    # final clean status; missing optional files must remain missing.
    # This is before/after custody, not an atomic filesystem snapshot.
    required_controls = (gitdir / "HEAD", gitdir / "index")
    optional_controls = (
        gitdir / "config", gitdir / "config.worktree", gitdir / "packed-refs",
    )
    control_entries = (*required_controls, *optional_controls)
    original_controls = {
        entry: control_identity(entry) for entry in control_entries
    }
    if (any(original_controls[entry] is None for entry in required_controls)
            or any(entry.is_symlink() or (
                entry.exists() and original_controls[entry] is None
            ) for entry in optional_controls)):
        return CheckoutPreflight(expected, None, ("unverified_git_control_custody",))

    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True, text=True, encoding="utf-8",
                check=True, timeout=10, env=isolated_git_env,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
                UnicodeDecodeError):
            # Git permits raw-byte POSIX filenames; undecodable index/status
            # output is unverified evidence, not a preflight exception.
            return None
        return result.stdout if "-z" in args else result.stdout.strip()

    toplevel = git("rev-parse", "--show-toplevel")
    if toplevel is None or Path(toplevel).resolve() != root.resolve():
        blockers.append("checkout_root_mismatch")
    # Loose and packed refs/replace both change Git object interpretation.
    # Reject them even though the isolated probes disable substitution.
    replace_refs = git("for-each-ref", "--format=%(refname)", "refs/replace")
    if replace_refs is None:
        return CheckoutPreflight(expected, None, ("unverified_replace_refs",))
    if replace_refs:
        return CheckoutPreflight(expected, None, ("git_replace_object_dependency",))
    head = git("rev-parse", "--verify", "HEAD")
    if head != expected:
        blockers.append("head_mismatch")
    shallow = git("rev-parse", "--is-shallow-repository")
    if shallow != "false":
        blockers.append("shallow_or_unverified_history")
    # A populated Git submodule can leave the parent's status perfectly clean,
    # while its nested repository borrows independently configured authority.
    # Inspect index modes before status can descend into any submodule Git.
    # NUL-delimited stage output preserves literal newlines, tabs and spaces
    # in tracked filenames. A clean status does not prove tracked-file inode
    # custody: hardlinks can alias external mutable data, and peer-writable
    # files can change independently of the Git index.
    # Bind the observed worktree inodes and ancestor directories to the final
    # status result. A clean Git status alone cannot detect a same-byte path
    # replacement immediately after its scan. This is a bounded readback,
    # not a claim of atomic or race-free filesystem custody.
    def custody_identity(metadata: os.stat_result) -> tuple[int, ...]:
        return (
            metadata.st_dev, metadata.st_ino, metadata.st_mode,
            metadata.st_uid, metadata.st_gid, metadata.st_nlink,
            metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns,
        )

    try:
        tracked_custody: dict[Path, tuple[int, ...]] = {
            root: custody_identity(root.lstat())
        }
    except OSError:
        return CheckoutPreflight(expected, head, ("unverified_worktree_directory_custody",))

    index_entries = git("ls-files", "--stage", "-z")
    if index_entries is None:
        blockers.append("unverified_index_entries")
    else:
        for entry in index_entries.split("\0"):
            if not entry:
                continue
            header, separator, relative_path = entry.partition("\t")
            mode = header.split(" ", 1)[0]
            if not separator or not relative_path:
                blockers.append("unverified_index_entries")
                break
            if mode == "160000":
                blockers.append("external_submodule_dependency")
                continue
            if mode == "120000":
                blockers.append("external_worktree_symlink_dependency")
                continue
            if mode not in {"100644", "100755"}:
                blockers.append("unverified_index_entries")
                continue
            # The tracked inode can be private while an intermediate directory
            # is writable by a peer (or replaced with a symlink). Reject such
            # path custody before running Git status, which may read that path.
            indexed_path = Path(relative_path)
            if indexed_path.is_absolute() or any(
                part in {".", ".."} for part in indexed_path.parts
            ):
                blockers.append("unverified_index_entries")
                continue
            parent = root
            parent_failed = False
            for component in indexed_path.parts[:-1]:
                parent = parent / component
                try:
                    parent_metadata = parent.lstat()
                except OSError:
                    blockers.append("unverified_worktree_directory_custody")
                    parent_failed = True
                    break
                if not stat.S_ISDIR(parent_metadata.st_mode):
                    blockers.append("external_worktree_directory_dependency")
                    parent_failed = True
                    break
                if os.name == "posix" and (
                    parent_metadata.st_uid not in trusted_owners
                    or parent_metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                ):
                    blockers.append("mutable_worktree_directory_permissions")
                    parent_failed = True
                    break
                observed_parent = custody_identity(parent_metadata)
                if (parent in tracked_custody
                        and tracked_custody[parent] != observed_parent):
                    blockers.append("tracked_worktree_custody_changed")
                    parent_failed = True
                    break
                tracked_custody[parent] = observed_parent
            if parent_failed:
                continue
            tracked_file = root / relative_path
            try:
                metadata = tracked_file.lstat()
            except OSError:
                blockers.append("unverified_worktree_file_custody")
                continue
            observed_file = custody_identity(metadata)
            if (tracked_file in tracked_custody
                    and tracked_custody[tracked_file] != observed_file):
                blockers.append("tracked_worktree_custody_changed")
            tracked_custody[tracked_file] = observed_file
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                blockers.append("external_worktree_file_dependency")
            if os.name == "posix" and (
                metadata.st_uid not in trusted_owners
                or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            ):
                blockers.append("mutable_worktree_file_permissions")
    # Never run status against unverified index modes or tracked file aliases.
    # A normal dirty checkout still reaches status for independent reporting.
    if any(name in blockers for name in (
        "unverified_index_entries",
        "external_submodule_dependency",
        "external_worktree_symlink_dependency",
        "unverified_worktree_file_custody",
        "external_worktree_file_dependency",
        "mutable_worktree_file_permissions",
        "unverified_worktree_directory_custody",
        "external_worktree_directory_dependency",
        "mutable_worktree_directory_permissions",
        "tracked_worktree_custody_changed",
    )):
        return CheckoutPreflight(expected, head, tuple(sorted(set(blockers))))
    # Porcelain status without --ignored hides untracked files concealed by
    # tracked .gitignore or private .git/info/exclude rules. Such files are
    # mutable workspace inputs and cannot satisfy clean-clone custody.
    status = git("status", "--porcelain", "--untracked-files=all", "--ignored=matching")
    if status is None or status:
        blockers.append("dirty_or_unverified_checkout")
    # A same-byte replacement or appearance/disappearance of Git control
    # metadata after one probe is not made safe by a clean status.
    if any(control_identity(entry) != original_controls[entry]
           for entry in control_entries):
        blockers.append("git_control_metadata_changed")
    # Recheck every tracked file and intermediate directory after status.
    # Device/inode plus metadata timestamps catch stable substitutions and
    # in-place writes that occurred across the non-atomic Git status scan.
    for tracked_path, original_identity in tracked_custody.items():
        try:
            observed_identity = custody_identity(tracked_path.lstat())
        except OSError:
            blockers.append("tracked_worktree_custody_changed")
            break
        if observed_identity != original_identity:
            blockers.append("tracked_worktree_custody_changed")
            break
    return CheckoutPreflight(expected, head, tuple(sorted(set(blockers))))
