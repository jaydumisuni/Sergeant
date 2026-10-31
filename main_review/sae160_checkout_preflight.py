"""SAE-160 checkout-shape preflight; not independent qualification evidence.

A standalone checkout must be bound to an exact head and free of mutable
worktree/alternate-object dependencies. This check does not establish that the
checkout was freshly cloned or that installation and external proof passed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import re
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
        # Attribute source overrides can replace tracked tree attribute rules
        # during Git probes without changing HEAD or checkout status.
        "GIT_ATTR_SOURCE",
        # Helper lookup and shallow-history metadata are external Git inputs.
        # Reject before even the local config subprocess is started.
        "GIT_EXEC_PATH", "GIT_SHALLOW_FILE",
        # Git init/clone can import executable hooks from an ambient template.
        # A repository-only qualification caller must not supply that source.
        "GIT_TEMPLATE_DIR",
        # Git's credential/SSH helper environment can nominate executable
        # transports outside this checkout. Standalone evidence preflight
        # must not inherit those process-launch authorities even if its
        # current read-only probe sequence never needs network access.
        "GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND",
        "GIT_SSH_VARIANT", "GIT_PROXY_COMMAND",
        # OpenSSH can execute an inherited askpass helper independently of
        # Git's own GIT_ASKPASS setting; REQUIRE controls when it is used.
        # Neither is bound by an exact checkout HEAD or local config.
        "SSH_ASKPASS", "SSH_ASKPASS_REQUIRE",
        # An inherited SSH agent socket exposes credential-bearing transport
        # outside this checkout even when Git's own helper env is unset.
        "SSH_AUTH_SOCK", "SSH_AGENT_PID",
        # Git protocol allow-lists and wire negotiation are caller-controlled
        # transport policy, even if the current checkout probes are local.
        "GIT_ALLOW_PROTOCOL", "GIT_PROTOCOL_FROM_USER", "GIT_PROTOCOL",
        # Terminal prompting is inherited credential interaction policy.
        "GIT_TERMINAL_PROMPT",
        # Executable pager/editor overrides remain unbound even when the
        # current read-only probe does not invoke an interactive command.
        "GIT_PAGER", "GIT_EDITOR", "GIT_SEQUENCE_EDITOR",
        "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
        # Reject inherited system-config suppression as caller policy even
        # though isolated Git probes independently pin their own setting.
        "GIT_CONFIG_NOSYSTEM",
        # Git tracing can write outside the checkout before a read-only
        # preflight reaches its later fail-closed decision.
        "GIT_TRACE", "GIT_TRACE2", "GIT_TRACE2_EVENT", "GIT_TRACE2_PERF",
        # libcurl inherits proxy destinations, credentials and bypass rules
        # independently of Git's http.proxy configuration. Reject before
        # the first Git subprocess rather than copying them into its env.
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        # TLS libraries and curl can inherit trust-store locations independently
        # of Git's own GIT_SSL_* overrides. SSLKEYLOGFILE can additionally
        # redirect TLS session-key material to a caller-selected destination.
        # Neither trust input nor key-log output belongs to this checkout.
        "SSL_CERT_FILE", "SSL_CERT_DIR", "CURL_CA_BUNDLE", "SSLKEYLOGFILE",
    }
    # Git also honors GIT_TRACE_SETUP, GIT_TRACE_PACKET, and other trace
    # variants that can write outside the checkout during the config probe.
    # Reject the entire trace namespace before starting any Git subprocess.
    # Dynamic-loader controls can replace Git code before any config probe.
    # Ambient Git TLS overrides can also replace remote trust roots, client
    # identities or verification policy without appearing in local config.
    # Proxy TLS has a separate GIT_PROXY_SSL_* environment namespace; it
    # can replace proxy trust roots and client credentials independently.
    # A read-only Git command cannot certify those unbound authorities.
    # Git HTTP and curl environment namespaces also change transport
    # timeouts, parallelism, diagnostics and credential interaction.
    # Orphaned indexed config keys/values remain unbound caller policy even
    # when GIT_CONFIG_COUNT is absent; reject before constructing isolated Git.
    if authority_env.intersection(os.environ) or any(
        name.startswith(("GIT_TRACE", "GIT_SSL_", "GIT_PROXY_SSL_",
                         "GIT_HTTP_", "GIT_CURL_", "GIT_CONFIG_KEY_",
                         "GIT_CONFIG_VALUE_", "LD_", "DYLD_"))
        for name in os.environ
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
        # The safety walk is a pre-Git authority read. Retain each directory's
        # identity so an entry inserted after its listing cannot silently
        # become part of the later trusted metadata snapshot.
        initial_directory_epochs: dict[Path, tuple[int, ...]] = {}

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
                # Every Git metadata entry is control-plane material, even
                # pseudorefs, reflogs and submodule stores. A symlink (including
                # a dangling one), hardlink or special file can borrow external
                # authority before the first config probe. os.walk deliberately
                # does not follow directory links; lstat still sees the alias.
                mode = metadata.st_mode
                if stat.S_ISDIR(mode):
                    epoch = (
                        metadata.st_dev, metadata.st_ino, mode,
                        metadata.st_uid, metadata.st_gid, metadata.st_nlink,
                        metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns,
                    )
                    previous = initial_directory_epochs.setdefault(entry, epoch)
                    if previous != epoch:
                        blockers.append("git_metadata_directory_epoch_changed")
                        break
                # Set-ID Git control files, including executable hooks, carry
                # privilege not represented by HEAD or a clean worktree status.
                # Reject before even the first local Git config subprocess.
                if stat.S_ISREG(mode) and mode & (stat.S_ISUID | stat.S_ISGID):
                    blockers.append("privileged_git_metadata")
                    break
                # Linux file capabilities can grant executable privilege
                # without changing the Git mode or HEAD. Fail before Git.
                if os.name == "posix" and stat.S_ISREG(mode):
                    try:
                        if "security.capability" in os.listxattr(
                            entry, follow_symlinks=False
                        ):
                            blockers.append("privileged_git_metadata_xattr")
                            break
                    except (OSError, AttributeError, TypeError, ValueError):
                        blockers.append("unverified_git_metadata_xattr_custody")
                        break
                if (stat.S_ISLNK(mode)
                        or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode))
                        or (stat.S_ISREG(mode) and metadata.st_nlink > 1)):
                    relative = entry.relative_to(gitdir)
                    if relative.parts == ("objects", "info", "alternates"):
                        blocker = "external_object_alternates"
                    elif relative.parts[:1] == ("objects",):
                        blocker = "external_object_store"
                    elif relative.parts[:1] == ("modules",):
                        blocker = "external_submodule_dependency"
                    else:
                        blocker = "external_git_metadata"
                    blockers.append(blocker)
                    break
                if (metadata.st_uid not in trusted_owners
                        or mode & (stat.S_IWGRP | stat.S_IWOTH)):
                    blockers.append("mutable_git_authority_permissions")
                    break
            if blockers:
                break
        # os.walk lists children before yielding their parent. A late addition
        # after that listing can otherwise enter the first complete-tree
        # snapshot as a stable, apparently trusted baseline. Recheck every
        # directory epoch before even the first Git config subprocess.
        if not blockers:
            for entry, before in initial_directory_epochs.items():
                try:
                    metadata = entry.lstat()
                    after = (
                        metadata.st_dev, metadata.st_ino, metadata.st_mode,
                        metadata.st_uid, metadata.st_gid, metadata.st_nlink,
                        metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns,
                    )
                except OSError:
                    after = None
                if after != before:
                    blockers.append("git_metadata_directory_epoch_changed")
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
    # Git reads more than HEAD, refs and objects. Directory permissions or
    # hook/info/log metadata can change after the initial safe walk without
    # changing HEAD, the index or the observed worktree. Bind the complete
    # local .git tree, including its root, across all read-only Git probes.
    def git_metadata_tree_snapshot() -> tuple[tuple[str, tuple[int, ...]], ...] | None:
        observed: list[tuple[str, tuple[int, ...]]] = []

        def walk_error(error: OSError) -> None:
            raise error

        try:
            for directory, child_dirs, child_files in os.walk(
                gitdir, followlinks=False, onerror=walk_error
            ):
                for entry in (Path(directory), *(
                    Path(directory) / name for name in (*child_dirs, *child_files)
                )):
                    metadata = entry.lstat()
                    mode = metadata.st_mode
                    if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                        return None
                    if stat.S_ISREG(mode) and metadata.st_nlink != 1:
                        return None
                    # The initial walk is not atomic with this snapshot.
                    # Never freeze a newly set-ID Git file as trusted metadata.
                    if stat.S_ISREG(mode) and mode & (stat.S_ISUID | stat.S_ISGID):
                        return None
                    # Revalidate capability custody at each Git readback.
                    if os.name == "posix" and stat.S_ISREG(mode):
                        try:
                            if "security.capability" in os.listxattr(
                                entry, follow_symlinks=False
                            ):
                                return None
                        except (OSError, AttributeError, TypeError, ValueError):
                            return None
                    if os.name == "posix" and (
                        metadata.st_uid not in trusted_owners
                        or mode & (stat.S_IWGRP | stat.S_IWOTH)
                    ):
                        return None
                    identity = (
                        metadata.st_dev, metadata.st_ino, mode,
                        metadata.st_uid, metadata.st_gid, metadata.st_nlink,
                        metadata.st_size,
                    )
                    # Git refreshes split-index timestamps during read probes.
                    # Bind the bytes, inode, size and permissions instead;
                    # all other Git metadata retains strict timestamp custody.
                    split_index = (
                        entry.parent == gitdir
                        and entry.name.startswith("sharedindex.")
                        and len(entry.name) - len("sharedindex.") in (40, 64)
                        and all(ch in "0123456789abcdef"
                                for ch in entry.name[len("sharedindex."):])
                    )
                    if split_index:
                        if not stat.S_ISREG(mode):
                            return None
                        digest = hashlib.sha256()
                        fd = os.open(entry, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                        with os.fdopen(fd, "rb") as source:
                            before = os.fstat(source.fileno())
                            if (
                                before.st_dev, before.st_ino, before.st_mode,
                                before.st_uid, before.st_gid, before.st_nlink,
                                before.st_size,
                            ) != identity:
                                return None
                            for chunk in iter(lambda: source.read(1048576), b""):
                                digest.update(chunk)
                            after = os.fstat(source.fileno())
                            if (
                                after.st_dev, after.st_ino, after.st_mode,
                                after.st_uid, after.st_gid, after.st_nlink,
                                after.st_size,
                            ) != identity:
                                return None
                        fingerprint = identity + (int.from_bytes(digest.digest(), "big"),)
                    else:
                        fingerprint = identity + (
                            metadata.st_mtime_ns, metadata.st_ctime_ns,
                        )
                    observed.append((
                        str(entry.relative_to(gitdir)), fingerprint,
                    ))
            return tuple(sorted(observed))
        except OSError:
            return None

    original_git_metadata = git_metadata_tree_snapshot()
    if original_git_metadata is None:
        return CheckoutPreflight(expected, None, ("unverified_git_metadata_custody",))

    # Snapshot control metadata before the safe config probe. A replacement
    # between that probe and checkout Git must not inherit unchecked settings.
    def control_identity(entry: Path) -> tuple[int, ...] | str | None:
        """Distinguish absent controls from invalid or substituted metadata."""
        try:
            metadata = entry.lstat()
        except FileNotFoundError:
            return "ABSENT"
        except OSError:
            return None
        # The initial metadata walk is not atomic with this snapshot. A
        # control file can acquire an external hardlink or peer-write access
        # after that walk but before the first identity is recorded. Never
        # accept such a stable-but-unsafe identity as the baseline.
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            return None
        if os.name == "posix" and (
            metadata.st_uid not in trusted_owners
            or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            return None
        return (
            metadata.st_dev, metadata.st_ino, metadata.st_mode,
            metadata.st_uid, metadata.st_gid, metadata.st_nlink,
            metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns,
        )

    # HEAD/index, optional configuration/ref tables, and local info rules are
    # independently consulted by Git probes. In particular, info/exclude can
    # conceal untracked evidence and info/attributes can alter path semantics
    # without changing HEAD or the index. Bind their pathname identities across
    # the final clean status; missing optional files must remain missing.
    # This is before/after custody, not an atomic filesystem snapshot.
    required_controls = (gitdir / "HEAD", gitdir / "index")
    optional_controls = (
        gitdir / "config", gitdir / "config.worktree", gitdir / "packed-refs",
        gitdir / "info" / "exclude", gitdir / "info" / "attributes",
    )
    control_entries = (*required_controls, *optional_controls)
    original_controls = {
        entry: control_identity(entry) for entry in control_entries
    }
    # A missing optional entry is allowed only while it stays missing.
    # Symlinks (including dangling ones), directories and stat failures are
    # invalid, not equivalent to absence; HEAD/index must be regular files.
    if (any(not isinstance(original_controls[entry], tuple)
            for entry in required_controls)
            or any(original_controls[entry] is None
                   for entry in optional_controls)):
        return CheckoutPreflight(expected, None, ("unverified_git_control_custody",))

    # Loose refs are independent Git authority. A clean status and a stable
    # symbolic HEAD file cannot prove that its target ref (or another ref)
    # was not swapped or introduced during the Git probes. Bind the entire
    # loose-ref namespace before config and again after the final status.
    def loose_ref_snapshot() -> tuple[tuple[str, tuple[int, ...]], ...] | None:
        ref_root = gitdir / "refs"
        try:
            entries = (ref_root, *ref_root.rglob("*"))
            observed = []
            for entry in entries:
                metadata = entry.lstat()
                mode = metadata.st_mode
                if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                    return None
                if stat.S_ISREG(mode) and metadata.st_nlink != 1:
                    return None
                if os.name == "posix" and (
                    metadata.st_uid not in trusted_owners
                    or mode & (stat.S_IWGRP | stat.S_IWOTH)
                ):
                    return None
                observed.append((
                    str(entry.relative_to(gitdir)),
                    (metadata.st_dev, metadata.st_ino, mode,
                     metadata.st_uid, metadata.st_gid, metadata.st_nlink,
                     metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns),
                ))
            return tuple(sorted(observed))
        except OSError:
            return None

    original_loose_refs = loose_ref_snapshot()
    if original_loose_refs is None:
        return CheckoutPreflight(expected, None, ("unverified_git_ref_custody",))

    # Object packs, loose objects and commit-graph metadata are independent
    # authority read by checkout Git. A same-byte pack-index replacement can
    # leave HEAD and status unchanged, so bind every object-store pathname
    # and inode across the non-atomic read-only probes.
    def object_store_snapshot() -> tuple[tuple[str, tuple[int, ...]], ...] | None:
        object_root = gitdir / "objects"
        observed: list[tuple[str, tuple[int, ...]]] = []

        def walk_error(error: OSError) -> None:
            raise error

        try:
            if not object_root.is_dir() or object_root.is_symlink():
                return None
            for directory, child_dirs, child_files in os.walk(
                object_root, followlinks=False, onerror=walk_error
            ):
                for entry in (Path(directory), *(
                    Path(directory) / name for name in (*child_dirs, *child_files)
                )):
                    metadata = entry.lstat()
                    mode = metadata.st_mode
                    if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                        return None
                    if stat.S_ISREG(mode) and metadata.st_nlink != 1:
                        return None
                    if os.name == "posix" and (
                        metadata.st_uid not in trusted_owners
                        or mode & (stat.S_IWGRP | stat.S_IWOTH)
                    ):
                        return None
                    observed.append((
                        str(entry.relative_to(gitdir)),
                        (metadata.st_dev, metadata.st_ino, mode,
                         metadata.st_uid, metadata.st_gid, metadata.st_nlink,
                         metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns),
                    ))
            return tuple(sorted(observed))
        except OSError:
            return None

    original_objects = object_store_snapshot()
    if original_objects is None:
        return CheckoutPreflight(expected, None, ("unverified_git_object_store_custody",))

    # A caller-controlled PATH can substitute Git itself before any local
    # config or checkout probe. On POSIX, constrain executable lookup to the
    # system's standard command directories; never inherit a workspace or
    # user-writable tool directory for an authority-bearing Git subprocess.
    # This is POSIX source custody, not Windows executable qualification.
    isolated_git_env = os.environ.copy()
    if os.name == "posix":
        isolated_git_env["PATH"] = os.defpath
    isolated_git_env["GIT_CONFIG_NOSYSTEM"] = "1"
    isolated_git_env["GIT_CONFIG_GLOBAL"] = os.devnull
    isolated_git_env["GIT_NO_REPLACE_OBJECTS"] = "1"
    # Repository-only evidence must never trigger a promisor remote fetch.
    # Override even an inherited GIT_NO_LAZY_FETCH=0 before config or object probes.
    isolated_git_env["GIT_NO_LAZY_FETCH"] = "1"
    isolated_git_env["GIT_OPTIONAL_LOCKS"] = "0"
    # Git reads default XDG/HOME attributes and ignore files even when its
    # global configuration is disabled. Those mutable files can change status
    # interpretation without changing the checkout or pinned local config.
    # Command-scope overrides retain repository-tracked .gitattributes and
    # .gitignore while eliminating ambient default attribute/ignore authority.
    isolated_git_env["GIT_ATTR_NOSYSTEM"] = "1"
    isolated_git_env["GIT_CONFIG_COUNT"] = "2"
    isolated_git_env["GIT_CONFIG_KEY_0"] = "core.attributesFile"
    isolated_git_env["GIT_CONFIG_VALUE_0"] = os.devnull
    isolated_git_env["GIT_CONFIG_KEY_1"] = "core.excludesFile"
    isolated_git_env["GIT_CONFIG_VALUE_1"] = os.devnull

    # Git include directives borrow configuration from another path, even if
    # that path is not presently active (includeIf) or is currently missing.
    # core.fsmonitor can execute a checkout-controlled program during status;
    # reject it before issuing any Git operation that may invoke that program.
    # Checkout-controlled filter commands can also execute during Git status.
    # External diff drivers/textconv can execute during later review; status alone
    # does not establish that this checkout has no executable diff authority.
    # core.attributesFile can borrow mutable attribute rules outside the clone.
    # Credential username settings (global or URL-scoped) also supply an
    # unpinned HTTP authentication identity without a credential helper.
    # core.ignoreStat can mark tracked paths assume-unchanged and make a
    # clean Git status insufficient evidence of the on-disk checkout. Reject
    # this unbound local status policy before running checkout Git.
    # Local SSH/proxy and credential helpers are executable transport
    # authorities just like their ambient environment equivalents. Reject
    # them before any checkout Git probe, including URL-scoped helpers.
    # Per-remote uploadpack/receivepack and vcs overrides can select external
    # transport executables despite an otherwise clean local checkout.
    # url.*.insteadOf/pushInsteadOf rewrites can redirect future fetch/push
    # destinations without changing the clean checkout or its origin URL.
    # Local pagers, askpass/editor programs, and signature programs are
    # executable review helpers. A clean status cannot bind their code or
    # destination to the checkout.
    # Auxiliary diff/merge tools, custom merge drivers, interactive diff
    # filters and alternate-ref commands are executable local config, not
    # bound by a clean status. merge.<name>.driver is separate from mergetool.
    # SSH signature signer/revocation files borrow external trust inputs.
    # Git shell aliases and SSH default-key commands are also executable
    # review/signing helpers even when HEAD/status remain clean.
    # Custom remote protocols may launch git-remote-* helpers even without
    # remote.<name>.vcs; protocol.*.allow can enable ext:: shell transports.
    # Reject these unbound executable transports before checkout Git probes.
    # Remote-specific proxy and proxy-auth choices override global HTTP
    # transport custody and cannot borrow an unbound proxy endpoint.
    # HTTP TLS roots, client credentials, cookies, headers and proxies can
    # borrow external trust or secret material; reject local and URL-scoped
    # variants before invoking checkout Git, without banning benign tuning.
    # Explicit HTTP TLS verification, backend, protocol/cipher and Schannel
    # revocation/CA policy (including URL scopes) are unbound transport trust
    # decisions even when no external credential file is named.
    # Proxy authentication selection, empty GSS negotiation and credential
    # delegation also change the remote authentication authority boundary.
    # Partial-clone/promisor settings can lazily borrow missing objects from a
    # remote even when the present local HEAD and status appear clean. A
    # repository-only checkout must reject those settings before Git object
    # probes can trigger a network fetch.
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
                 r"^(include|includeif)\..*|^core\.(fsmonitor|ignorestat|excludesfile|attributesfile|worktree|hookspath|sparsecheckout|sparsecheckoutcone|sshcommand|gitproxy|askpass|editor)$|^credential\.(helper|username|.+\.(helper|username))$|^filter\..+\.(clean|smudge|process)$|^diff\.(external|.+\.(command|textconv))$|^core\.pager$|^pager\..+$|^sequence\.editor$|^interactive\.difffilter$|^difftool\..+\.cmd$|^mergetool\..+\.cmd$|^merge\..+\.driver$|^core\.alternaterefscommand$|^gpg(\.[^.]+)?\.program$|^gpg\.ssh\.defaultkeycommand$|^gpg\.ssh\.(allowedsignersfile|revocationfile)$|^alias\..+$|^extensions\.partialclone$|^remote\..+\.(promisor|partialclonefilter|uploadpack|receivepack|vcs|proxy|proxyauthmethod)$|^url\..+\.(insteadof|pushinsteadof)$|^protocol\..+\.allow$|^http(\..+)?\.(sslcainfo|sslcapath|sslcert|sslkey|proxysslcainfo|proxysslcapath|proxysslcert|proxysslkey|pinnedpubkey|cookiefile|extraheader|proxy|sslverify|proxysslverify|proxyauthmethod|emptyauth|delegation|sslbackend|sslversion|sslcipherlist|schannelcheckrevoke|schannelusesslcainfo)$"],
                capture_output=True, text=True, timeout=10,
                env=isolated_git_env,
            )
        except (OSError, subprocess.TimeoutExpired):
            blockers.append("external_git_metadata")
            continue
        if config_probe.returncode not in (0, 1) or config_probe.stdout.strip():
            blockers.append("external_git_metadata")
        # A normal origin URL is permitted, but Git's remote-helper syntax
        # (ext::, custom:: or custom://) selects executable transports outside
        # this checkout. Inspect values, not merely config keys, and preserve
        # legitimate https/ssh/git/file remote URLs, including Git's built-in
        # git+ssh and ssh+git aliases (both dispatch through ordinary SSH).
        try:
            remote_probe = subprocess.run(
                ["git", "config", "--no-includes", "--file", str(config_file),
                 "--null", "--get-regexp", r"^remote\..+\.(url|pushurl)$"],
                capture_output=True, text=True, encoding="utf-8", timeout=10,
                env=isolated_git_env,
            )
        except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
            blockers.append("external_git_metadata")
            continue
        if remote_probe.returncode not in (0, 1):
            blockers.append("external_git_metadata")
        elif remote_probe.returncode == 0:
            for record in remote_probe.stdout.split("\0"):
                if not record:
                    continue
                key, separator, url = record.partition("\n")
                if not separator or not key or not url:
                    blockers.append("external_git_metadata")
                    break
                # Git config can store C0/C1 Unicode controls in remote URLs.
                # In particular, U+0085 is Unicode whitespace and bypasses
                # scheme-anchored checks while leaving HEAD/worktree clean.
                # Neither fetch nor push metadata may borrow that authority.
                if any(ord(char) < 0x20 or 0x7f <= ord(char) <= 0x9f
                       for char in url):
                    blockers.append("external_git_metadata")
                    break
                # HTTP userinfo carries a remote authentication identity or
                # secret outside the independently qualified checkout policy.
                # A clean HEAD does not authorize credentials embedded in a
                # fetch or push URL; ordinary SSH user@host remains permitted.
                # libcurl can interpret http:///user:secret@host as an
                # authenticated HTTP endpoint despite the extra slash.
                # Require a nonempty authority immediately after // rather
                # than trusting the first slash to delimit credentials.
                if (re.match(r"^https?:///", url)
                        or re.match(r"^https?://[^/?#]*@", url)):
                    blockers.append("external_git_metadata")
                    break
                transport = re.match(
                    r"^([^:/\s]+)(::|://)", url
                )
                if transport and (
                    transport.group(2) == "::"
                    or transport.group(1)
                    not in {"http", "https", "ssh", "git+ssh", "ssh+git", "git", "file"}
                ):
                    blockers.append("external_git_metadata")
                    break
    # A config probe is safe only for the exact control identities it read.
    # In particular, a late core.fsmonitor/filter injection must be rejected
    # before any checkout Git subprocess can execute the new configuration.
    if any(control_identity(entry) != original_controls[entry]
           for entry in control_entries):
        return CheckoutPreflight(expected, None, ("git_control_metadata_changed",))
    if loose_ref_snapshot() != original_loose_refs:
        return CheckoutPreflight(expected, None, ("git_ref_metadata_changed",))
    if object_store_snapshot() != original_objects:
        return CheckoutPreflight(expected, None, ("git_object_store_changed",))
    if git_metadata_tree_snapshot() != original_git_metadata:
        return CheckoutPreflight(expected, None, ("git_metadata_tree_changed",))
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

    # All checkout Git probes reuse the pre-config, system-path environment.
    # Replacement refs and optional index writes remain disabled throughout.

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

    # The ancestry walk and later Git probes are not atomic. Re-admit the
    # checkout root immediately before the first checkout Git subprocess:
    # a newly peer-writable or foreign-owned root must not become a trusted
    # snapshot merely because its changed identity stays stable thereafter.
    def checkout_root_custody_safe(metadata: os.stat_result) -> bool:
        if not stat.S_ISDIR(metadata.st_mode):
            return False
        if os.name != "posix":
            return True
        if metadata.st_uid not in trusted_owners:
            return False
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            return metadata.st_uid == 0 and bool(metadata.st_mode & stat.S_ISVTX)
        return True

    # The initial ancestry walk precedes metadata/config inspection. Recheck
    # every ancestor, not only the root: a newly peer-writable or foreign-owned
    # parent could otherwise replace the checkout before the first Git probe.
    def checkout_ancestry_custody_safe() -> bool:
        try:
            return all(
                checkout_root_custody_safe(directory.lstat())
                for directory in (root, *root.parents)
            )
        except OSError:
            return False

    if not checkout_ancestry_custody_safe():
        return CheckoutPreflight(expected, None, ("mutable_checkout_ancestry",))

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
        root_metadata = root.lstat()
        if not checkout_root_custody_safe(root_metadata):
            return CheckoutPreflight(expected, head, ("mutable_checkout_ancestry",))
        tracked_custody: dict[Path, tuple[int, ...]] = {
            root: custody_identity(root_metadata)
        }
    except OSError:
        return CheckoutPreflight(expected, head, ("unverified_worktree_directory_custody",))

    index_entries = git("ls-files", "--stage", "-z")
    indexed_directories = {root}
    indexed_files: set[Path] = set()
    tracked_xattrs: dict[Path, tuple[tuple[str, bytes], ...]] = {}
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
                indexed_directories.add(parent)
            if parent_failed:
                continue
            tracked_file = root / relative_path
            indexed_files.add(tracked_file)
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
            # Git does not store POSIX extended attributes. A capability xattr
            # can grant executable privilege without changing the indexed blob
            # or executable bit, so status cannot establish its absence.
            # Bind nonprivileged attribute *values* as well as names: the same
            # name with changed bytes is a different untracked filesystem input.
            # Failure to read any value is unknown, never a clean checkout.
            if os.name == "posix":
                try:
                    names = tuple(sorted(os.listxattr(
                        tracked_file, follow_symlinks=False
                    )))
                    if "security.capability" in names:
                        blockers.append("tracked_worktree_privileged_xattr")
                    else:
                        tracked_xattrs[tracked_file] = tuple(
                            (name, os.getxattr(
                                tracked_file, name, follow_symlinks=False
                            )) for name in names
                        )
                except (OSError, AttributeError, TypeError, ValueError):
                    blockers.append("unverified_worktree_xattr_custody")
            # Git status may ignore executable-bit drift when core.filemode=false.
            # Bind the physical POSIX executable bits to the staged Git mode
            # directly; a clean status cannot establish this parity.
            if os.name == "posix" and stat.S_ISREG(metadata.st_mode):
                # Git records only 100644/100755 executable parity, not set-ID
                # privilege transitions. A clean status cannot admit a tracked
                # file carrying an unrepresented set-user/group-ID bit.
                if metadata.st_mode & (stat.S_ISUID | stat.S_ISGID):
                    blockers.append("tracked_worktree_privileged_mode")
                if bool(metadata.st_mode & 0o111) != (mode == "100755"):
                    blockers.append("tracked_worktree_mode_mismatch")
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
        "tracked_worktree_mode_mismatch",
        "tracked_worktree_privileged_mode",
        "tracked_worktree_privileged_xattr",
        "unverified_worktree_xattr_custody",
        "unverified_worktree_directory_custody",
        "external_worktree_directory_dependency",
        "mutable_worktree_directory_permissions",
        "tracked_worktree_custody_changed",
    )):
        return CheckoutPreflight(expected, head, tuple(sorted(set(blockers))))
    # Index visibility flags can make a modified tracked file appear clean:
    # assume-unchanged (lowercase tag) and skip-worktree (S) both suppress
    # normal status checks. Refuse those flags before trusting status; the
    # standalone evidence checkout requires ordinary tracked-file visibility.
    index_visibility = git("ls-files", "-v", "-z")
    if index_visibility is None or index_entries is None:
        return CheckoutPreflight(expected, head, ("unverified_index_visibility",))
    visible_entries = [entry for entry in index_visibility.split("\0") if entry]
    staged_entries = [entry for entry in index_entries.split("\0") if entry]
    if (len(visible_entries) != len(staged_entries)
            or any(not entry.startswith("H ") for entry in visible_entries)):
        return CheckoutPreflight(expected, head, ("unverified_index_visibility",))
    # Porcelain status without --ignored hides untracked files concealed by
    # tracked .gitignore or private .git/info/exclude rules. Such files are
    # mutable workspace inputs and cannot satisfy clean-clone custody.
    status = git("status", "--porcelain", "--untracked-files=all", "--ignored=matching")
    if status is None or status:
        blockers.append("dirty_or_unverified_checkout")
    # Git status can hide untracked case-folded aliases when core.ignorecase
    # is enabled on a case-sensitive filesystem. It also omits empty untracked
    # directories. Enumerate every direct child of each indexed directory
    # against the exact, case-sensitive index path set. This is independent of
    # Git's ignore/casefold heuristics and does not follow symlink targets.
    # Ordinary dirty status already blocks admission; this closes the false
    # clean result without changing the established dirty-checkout verdict.
    for directory in (indexed_directories if status == "" else ()):
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if directory == root and entry.name == ".git":
                        continue
                    child = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        if child not in indexed_directories:
                            blockers.append("untracked_worktree_directory")
                            break
                    elif child not in indexed_files:
                        blockers.append("untracked_worktree_entry")
                        break
        except OSError:
            blockers.append("unverified_worktree_directory_custody")
            break
        if ("untracked_worktree_directory" in blockers
                or "untracked_worktree_entry" in blockers):
            break
    # A same-byte replacement or appearance/disappearance of Git control
    # metadata after one probe is not made safe by a clean status.
    if any(control_identity(entry) != original_controls[entry]
           for entry in control_entries):
        blockers.append("git_control_metadata_changed")
    if loose_ref_snapshot() != original_loose_refs:
        blockers.append("git_ref_metadata_changed")
    if object_store_snapshot() != original_objects:
        blockers.append("git_object_store_changed")
    if not blockers and git_metadata_tree_snapshot() != original_git_metadata:
        blockers.append("git_metadata_tree_changed")
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
    # Bind attribute names and contents across Git status. Check names first
    # so a newly introduced capability is rejected even if its bytes cannot
    # be read; a stable name with modified bytes is equally unverified.
    for tracked_path, original_attributes in tracked_xattrs.items():
        try:
            names = tuple(sorted(os.listxattr(
                tracked_path, follow_symlinks=False
            )))
            if names != tuple(name for name, _ in original_attributes):
                blockers.append("tracked_worktree_xattr_changed")
                break
            observed_attributes = tuple(
                (name, os.getxattr(
                    tracked_path, name, follow_symlinks=False
                )) for name in names
            )
        except (OSError, AttributeError, TypeError, ValueError):
            blockers.append("unverified_worktree_xattr_custody")
            break
        if observed_attributes != original_attributes:
            blockers.append("tracked_worktree_xattr_changed")
            break
    # A clean status is not proof if checkout ancestry lost custody during
    # the Git probes. This is a bounded readback, not an atomic snapshot.
    if not checkout_ancestry_custody_safe():
        blockers.append("mutable_checkout_ancestry")
    return CheckoutPreflight(expected, head, tuple(sorted(set(blockers))))
