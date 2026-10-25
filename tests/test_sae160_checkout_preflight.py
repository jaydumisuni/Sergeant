"""SAE-160 standalone checkout preflight cannot grant qualification."""
from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from main_review.sae160_checkout_preflight import inspect_checkout


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def checkout(tmp_path: Path) -> tuple[Path, str]:
    origin = tmp_path / "origin"
    origin.mkdir()
    subprocess.check_call(["git", "init", "-q", str(origin)])
    git(origin, "config", "user.email", "test@example.invalid")
    git(origin, "config", "user.name", "Test")
    (origin / "tracked.txt").write_text("fixed\n")
    git(origin, "add", "tracked.txt")
    git(origin, "commit", "-qm", "fixture")
    clone = tmp_path / "clone"
    subprocess.check_call(["git", "clone", "--no-hardlinks", "-q", str(origin), str(clone)])
    return clone, git(clone, "rev-parse", "HEAD")


def test_standalone_clean_exact_checkout_is_only_preflight(tmp_path):
    path, head = checkout(tmp_path)
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


def test_wrong_head_and_dirty_checkout_fail_closed(tmp_path):
    path, head = checkout(tmp_path)
    (path / "tracked.txt").write_text("changed\n")
    (path / "untracked.txt").write_text("new\n")
    result = inspect_checkout(path, "f" * 40)
    assert result.blockers == ("dirty_or_unverified_checkout", "head_mismatch")
    assert result.authority_gain == "NONE"


def test_linked_worktree_is_not_standalone_clone(tmp_path):
    path, head = checkout(tmp_path)
    linked = tmp_path / "linked"
    git(path, "worktree", "add", "-q", "--detach", str(linked))
    result = inspect_checkout(linked, head)
    assert result.blockers == ("not_standalone_checkout",)


def test_external_object_alternates_are_not_accepted(tmp_path):
    path, head = checkout(tmp_path)
    alternates = path / ".git" / "objects" / "info" / "alternates"
    alternates.write_text(str(tmp_path / "origin" / ".git" / "objects") + "\n")
    result = inspect_checkout(path, head)
    assert "external_object_alternates" in result.blockers


def test_directory_without_git_identity_fails_closed(tmp_path):
    result = inspect_checkout(tmp_path, "f" * 40)
    assert result.blockers == ("not_standalone_checkout",)
    assert result.authority_gain == "NONE"


def test_external_object_store_symlink_is_not_standalone(tmp_path):
    path, head = checkout(tmp_path)
    objects = path / ".git" / "objects"
    outside = tmp_path / "external-objects"
    objects.rename(outside)
    objects.symlink_to(outside, target_is_directory=True)
    result = inspect_checkout(path, head)
    assert "external_object_store" in result.blockers
    assert result.authority_gain == "NONE"


def test_dangling_alternates_symlink_is_rejected(tmp_path):
    path, head = checkout(tmp_path)
    alternates = path / ".git" / "objects" / "info" / "alternates"
    alternates.symlink_to(tmp_path / "missing-object-store")
    result = inspect_checkout(path, head)
    assert "external_object_alternates" in result.blockers


def test_symlinked_pack_file_cannot_borrow_external_objects(tmp_path):
    path, head = checkout(tmp_path)
    external = tmp_path / "external.pack"
    external.write_bytes(b"not a git pack")
    borrowed = path / ".git" / "objects" / "pack" / "borrowed.pack"
    borrowed.symlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_object_store" in result.blockers
    assert result.authority_gain == "NONE"


def test_hardlinked_pack_file_cannot_borrow_external_objects(tmp_path):
    path, head = checkout(tmp_path)
    external = tmp_path / "external.pack"
    external.write_bytes(b"not a git pack")
    borrowed = path / ".git" / "objects" / "pack" / "borrowed.pack"
    borrowed.hardlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_object_store" in result.blockers
    assert result.authority_gain == "NONE"


def test_external_loose_object_symlink_is_rejected(tmp_path):
    path, head = checkout(tmp_path)
    loose_dir = path / ".git" / "objects" / "ab"
    loose_dir.mkdir(exist_ok=True)
    outside = tmp_path / "external-loose-object"
    outside.write_bytes(b"external mutable object")
    (loose_dir / "1234567890abcdef1234567890abcdef123456").symlink_to(outside)
    result = inspect_checkout(path, head)
    assert "external_object_store" in result.blockers
    assert result.authority_gain == "NONE"


def test_symlinked_commit_graph_cannot_borrow_external_object_metadata(tmp_path):
    path, head = checkout(tmp_path)
    external = tmp_path / "external-commit-graph"
    external.write_bytes(b"untrusted mutable graph")
    (path / ".git" / "objects" / "info" / "commit-graph").symlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_object_store" in result.blockers
    assert result.authority_gain == "NONE"


def test_ambient_git_authority_override_is_not_standalone(tmp_path, monkeypatch):
    path, head = checkout(tmp_path)
    external = tmp_path / "external-objects"
    external.mkdir()
    for key in ("GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_INDEX_FILE"):
        with monkeypatch.context() as scoped:
            scoped.setenv(key, str(external))
            result = inspect_checkout(path, head)
        assert "ambient_git_authority_override" in result.blockers
        assert result.authority_gain == "NONE"


def test_symlinked_git_config_is_not_standalone_authority(tmp_path):
    path, head = checkout(tmp_path)
    config = path / ".git" / "config"
    external = tmp_path / "external-config"
    external.write_bytes(config.read_bytes())
    config.unlink()
    config.symlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_hardlinked_git_head_is_not_standalone_authority(tmp_path):
    path, head = checkout(tmp_path)
    head_file = path / ".git" / "HEAD"
    external = tmp_path / "external-HEAD"
    head_file.rename(external)
    head_file.hardlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_hardlinked_commit_graph_cannot_borrow_external_object_metadata(tmp_path):
    path, head = checkout(tmp_path)
    assert inspect_checkout(path, head).blockers == ()
    external = tmp_path / "external-commit-graph"
    external.write_bytes(b"mutable external commit graph")
    (path / ".git" / "objects" / "info" / "commit-graph").hardlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_object_store" in result.blockers
    assert result.authority_gain == "NONE"


def test_external_git_index_is_not_standalone_authority(tmp_path):
    path, head = checkout(tmp_path)
    index = path / ".git" / "index"
    external = tmp_path / "external-index"
    external.write_bytes(index.read_bytes())
    index.unlink()
    index.symlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_symlinked_branch_ref_cannot_borrow_external_authority(tmp_path):
    path, head = checkout(tmp_path)
    ref = path / ".git" / "refs" / "heads" / "master"
    assert ref.is_file()
    external = tmp_path / "external-ref"
    external.write_bytes(ref.read_bytes())
    ref.unlink()
    ref.symlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_shared_writable_nested_ref_directory_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A nested refs directory writable by peers can swap a branch ref."""
    path, head = checkout(tmp_path)
    git(path, "update-ref", "refs/heads/nested/topic", head)
    nested = path / ".git" / "refs" / "heads" / "nested"
    nested.chmod(0o777)
    assert nested.stat().st_mode & 0o022

    original_run = subprocess.run
    checkout_commands = []

    def watched_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("untrusted checkout Git executed")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", watched_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.authority_gain == "NONE"
    assert checkout_commands == []


def test_git_info_exclude_external_alias_is_rejected(tmp_path):
    """Git's local exclude file cannot be supplied by external mutable metadata."""
    path, head = checkout(tmp_path)
    external = tmp_path / "outside-exclude"
    external.write_text("ignored-by-external-file\n")
    exclude = path / ".git" / "info" / "exclude"
    exclude.unlink()
    exclude.symlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_git_info_exclude_external_hardlink_is_rejected(tmp_path):
    """Hardlinked exclusion rules are externally mutable checkout authority."""
    path, head = checkout(tmp_path)
    external = tmp_path / "outside-exclude"
    external.write_text("ignored-by-external-file\n")
    exclude = path / ".git" / "info" / "exclude"
    exclude.unlink()
    exclude.hardlink_to(external)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_external_git_config_include_is_rejected(tmp_path):
    """A local config include must not import mutable external checkout rules."""
    path, head = checkout(tmp_path)
    external = tmp_path / "outside-git-config"
    external.write_text("[core]\n\texcludesFile = /tmp/borrowed-excludes\n")
    git(path, "config", "--local", "include.path", str(external))
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_conditional_git_config_include_is_rejected(tmp_path):
    """A conditional include is external authority even if inactive now."""
    path, head = checkout(tmp_path)
    external = tmp_path / "conditional-git-config"
    external.write_text("[core]\n\tignorecase = true\n")
    git(path, "config", "--local", "includeIf.gitdir:*/.path", str(external))
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_core_fsmonitor_configuration_is_not_standalone_authority(tmp_path):
    """Git status must not invoke a checkout-controlled external fsmonitor."""
    path, head = checkout(tmp_path)
    git(path, "config", "--local", "core.fsmonitor", "/nonexistent/host-fsmonitor")
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_core_fsmonitor_preflight_never_invokes_checkout_git(tmp_path, monkeypatch):
    """Fail closed before status can execute a configured fsmonitor program."""
    path, head = checkout(tmp_path)
    git(path, "config", "--local", "core.fsmonitor", "/nonexistent/host-fsmonitor")
    actual_run = subprocess.run
    checkout_commands = []

    def watched_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("untrusted Git checkout command invoked")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", watched_run)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


def test_core_excludesfile_cannot_hide_untracked_files(tmp_path):
    """An external ignore file must not hide untracked checkout contents."""
    path, head = checkout(tmp_path)
    external = tmp_path / "external-exclude"
    external.write_text("hidden-untracked.txt\n")
    git(path, "config", "--local", "core.excludesFile", str(external))
    (path / "hidden-untracked.txt").write_text("unreviewed\n")
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


def test_core_worktree_redirect_is_rejected_before_checkout_git(tmp_path, monkeypatch):
    """An external worktree target cannot supply checkout identity."""
    path, head = checkout(tmp_path)
    git(path, "config", "--local", "core.worktree", str(tmp_path / "external-tree"))
    actual_run = subprocess.run
    checkout_commands = []

    def watched_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("untrusted Git checkout command invoked")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", watched_run)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


def test_global_fsmonitor_is_isolated_from_checkout_git(tmp_path, monkeypatch):
    """Checkout Git must not inherit host-global executable configuration."""
    import os

    path, head = checkout(tmp_path)
    home = tmp_path / "isolated-home"
    home.mkdir()
    (home / ".gitconfig").write_text(
        "[core]\n\tfsmonitor = /nonexistent/host-fsmonitor\n"
    )
    monkeypatch.setenv("HOME", str(home))
    actual_run = subprocess.run

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            child_env = kwargs.get("env") or {}
            assert child_env.get("GIT_CONFIG_NOSYSTEM") == "1"
            assert child_env.get("GIT_CONFIG_GLOBAL") == os.devnull
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


def test_external_hooks_path_is_not_standalone_authority(tmp_path):
    path, head = checkout(tmp_path)
    external = tmp_path / "outside-hooks"
    external.mkdir()
    git(path, "config", "--local", "core.hooksPath", str(external))
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


def test_external_shallow_metadata_is_rejected_before_checkout_git(tmp_path, monkeypatch):
    """Shallow boundary metadata must not be borrowed through an external hardlink."""
    path, head = checkout(tmp_path)
    outside = tmp_path / "external-shallow"
    outside.write_text(head + "\n")
    (path / ".git" / "shallow").hardlink_to(outside)
    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("untrusted checkout Git invoked")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


def test_checkout_rejects_filter_process_execution_authority(tmp_path):
    """A checkout-controlled Git filter may execute during status and cannot qualify."""
    path, head = checkout(tmp_path)
    git(path, "config", "--local", "filter.untrusted.process", "/nonexistent/checkout-filter")
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.authority_gain == "NONE"


def test_sparse_checkout_flags_cannot_qualify_full_standalone_clone(tmp_path, monkeypatch):
    """Sparse-checkout configuration can conceal missing tracked files."""
    path, head = checkout(tmp_path)
    actual_run = subprocess.run
    for key in ("core.sparseCheckout", "core.sparseCheckoutCone"):
        git(path, "config", "--local", key, "true")
        checkout_commands = []

        def guarded_run(argv, *args, **kwargs):
            if list(argv[:3]) == ["git", "-C", str(path)]:
                checkout_commands.append(list(argv))
                raise AssertionError("sparse checkout Git invoked before preflight")
            return actual_run(argv, *args, **kwargs)

        with monkeypatch.context() as scope:
            scope.setattr(subprocess, "run", guarded_run)
            result = inspect_checkout(path, head)
        assert "external_git_metadata" in result.blockers
        assert result.observed_head is None
        assert checkout_commands == []
        assert result.authority_gain == "NONE"
        git(path, "config", "--local", "--unset", key)


def test_external_attributes_file_is_not_standalone_authority(tmp_path):
    """A checkout must not borrow mutable attribute rules outside its .git directory."""
    path, head = checkout(tmp_path)
    outside = tmp_path / "outside-attributes"
    outside.write_text("*.txt -text\n")
    git(path, "config", "--local", "core.attributesFile", str(outside))
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_external_split_index_alias_is_rejected_before_checkout_git(tmp_path, monkeypatch, alias_kind):
    """A split-index alias cannot borrow mutable index authority from elsewhere."""
    path, head = checkout(tmp_path)
    outside = tmp_path / "external-shared-index"
    outside.write_bytes(b"externally mutable index metadata")
    shared_index = path / ".git" / ("sharedindex." + "a" * 40)
    if alias_kind == "symlink":
        shared_index.symlink_to(outside)
    else:
        shared_index.hardlink_to(outside)

    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("untrusted checkout Git invoked")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


def test_peer_writable_shared_index_is_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A split-index backing file writable by peers is mutable Git index authority."""
    path, head = checkout(tmp_path)
    shared_index = path / ".git" / ("sharedindex." + "a" * 40)
    shared_index.write_bytes(b"mutable split index")
    shared_index.chmod(0o666)

    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("mutable split index reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


def test_symlinked_checkout_root_is_rejected_before_checkout_git(tmp_path, monkeypatch):
    """An aliased root is not an independently identified standalone clone."""
    path, head = checkout(tmp_path)
    alias = tmp_path / "checkout-alias"
    alias.symlink_to(path, target_is_directory=True)
    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(alias)]:
            checkout_commands.append(list(argv))
            raise AssertionError("untrusted checkout Git invoked")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(alias, head)
    assert result.blockers == ("not_standalone_checkout",)
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


def test_symlinked_checkout_parent_is_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A checkout reached through a symlinked parent is not independent."""
    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    path, head = checkout(real_parent)
    alias_parent = tmp_path / "alias-parent"
    alias_parent.symlink_to(real_parent, target_is_directory=True)
    alias = alias_parent / path.name
    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(alias)]:
            checkout_commands.append(list(argv))
            raise AssertionError("aliased checkout Git invoked before preflight")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(alias, head)
    assert result.blockers == ("not_standalone_checkout",)
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("mutable_dir", (".git", ".git/objects", ".git/refs/heads"))
def test_shared_writable_git_authority_directory_rejected_before_checkout_git(tmp_path, monkeypatch, mutable_dir):
    """A shared-writable control directory lets another actor swap Git authority."""
    import stat

    path, head = checkout(tmp_path)
    target = path / mutable_dir
    target.chmod(target.stat().st_mode | stat.S_IWGRP)
    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("shared-writable checkout Git invoked before preflight")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("mutable_file", (".git/config", ".git/HEAD", ".git/index", ".git/refs/heads/master"))
def test_shared_writable_git_control_file_rejected_before_checkout_git(tmp_path, monkeypatch, mutable_file):
    """Mutable Git identity and index files cannot establish standalone authority."""
    import stat

    path, head = checkout(tmp_path)
    target = path / mutable_file
    assert target.is_file()
    target.chmod(target.stat().st_mode | stat.S_IWGRP)
    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("shared-writable Git control file reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("mutable_target", ("loose_shard", "loose_object", "pack_file"))
def test_shared_writable_git_object_material_rejected_before_checkout_git(
    tmp_path, monkeypatch, mutable_target
):
    """A different local principal must not rewrite Git objects before verification."""
    import stat

    path, head = checkout(tmp_path)
    if mutable_target == "pack_file":
        target = path / ".git" / "objects" / "pack" / "mutable.pack"
        target.write_bytes(b"untrusted pack content")
    else:
        shard = path / ".git" / "objects" / "ab"
        shard.mkdir(exist_ok=True)
        target = shard if mutable_target == "loose_shard" else shard / ("0" * 38)
        if mutable_target == "loose_object":
            target.write_bytes(b"untrusted loose object")
    target.chmod(target.stat().st_mode | stat.S_IWGRP)
    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("shared-writable Git objects reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("metadata_file", (".git/info/exclude", ".git/info/attributes"))
def test_shared_writable_git_info_file_rejected_before_checkout_git(
    tmp_path, monkeypatch, metadata_file
):
    """A peer-writable exclude or attributes file can change Git status semantics."""
    path, head = checkout(tmp_path)
    target = path / metadata_file
    if not target.exists():
        target.write_text("*.txt -text\n")
    target.chmod(target.stat().st_mode | 0o022)

    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("peer-writable info metadata reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("target_kind", ("commit_graph", "chain_directory", "chain_file"))
def test_mutable_commit_graph_metadata_rejected_before_checkout_git(tmp_path, monkeypatch, target_kind):
    """Git object-info authority cannot be peer-writable before checkout Git."""
    path, head = checkout(tmp_path)
    info = path / ".git" / "objects" / "info"
    if target_kind == "commit_graph":
        target = info / "commit-graph"
        target.write_bytes(b"untrusted graph")
    else:
        chain = info / "commit-graphs"
        chain.mkdir()
        target = chain
        if target_kind == "chain_file":
            target = chain / "commit-graph-chain"
            target.write_text("untrusted chain\n")
    target.chmod(target.stat().st_mode | 0o022)

    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("peer-writable commit graph reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX directory custody")
@pytest.mark.parametrize("level", ("checkout", "parent"))
def test_mutable_checkout_ancestry_rejected_before_checkout_git(tmp_path, monkeypatch, level):
    """A peer-writable parent can replace a private .git directory wholesale."""
    import stat

    path, head = checkout(tmp_path)
    target = path if level == "checkout" else path.parent
    original_mode = stat.S_IMODE(target.stat().st_mode)
    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("mutable checkout ancestor reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    try:
        target.chmod(original_mode | stat.S_IWGRP)
        monkeypatch.setattr(subprocess, "run", guarded_run)
        result = inspect_checkout(path, head)
    finally:
        target.chmod(original_mode)

    assert "mutable_checkout_ancestry" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX directory custody")
def test_foreign_owned_checkout_parent_rejected_even_when_not_peer_writable(tmp_path, monkeypatch):
    """Mode 0755 does not prevent the owning foreign principal replacing a child."""
    import os

    path, head = checkout(tmp_path)
    parent = path.parent
    actual_lstat = Path.lstat
    actual_run = subprocess.run
    checkout_commands = []

    def foreign_parent_lstat(self, *args, **kwargs):
        metadata = actual_lstat(self, *args, **kwargs)
        if self == parent:
            fields = list(metadata)
            fields[4] = 424242 if os.geteuid() != 424242 else 424243
            return os.stat_result(fields)
        return metadata

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("foreign-owned checkout ancestor reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", foreign_parent_lstat)
    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)

    assert "mutable_checkout_ancestry" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"

@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX directory custody")
def test_foreign_owned_git_directory_rejected_before_checkout_git(tmp_path, monkeypatch):
    """An unrelated owner of .git can rewrite its private-looking metadata."""
    import os

    path, head = checkout(tmp_path)
    gitdir = path / ".git"
    original_lstat = Path.lstat
    original_run = subprocess.run
    checkout_commands = []

    def foreign_gitdir_lstat(self, *args, **kwargs):
        metadata = original_lstat(self, *args, **kwargs)
        if self == gitdir:
            fields = list(metadata)
            fields[4] = 424242 if os.geteuid() != 424242 else 424243
            return os.stat_result(fields)
        return metadata

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("foreign-owned Git control directory reached checkout Git")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", foreign_gitdir_lstat)
    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)

    assert "mutable_git_authority_ownership" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX ownership custody")
@pytest.mark.parametrize(
    "relative",
    ("objects/pack", "refs/heads", "refs/heads/nested", "config", "objects/info/commit-graphs"),
)
def test_foreign_owned_nested_git_authority_rejected_before_checkout_git(
    tmp_path, monkeypatch, relative
):
    """Mode 0755/0644 cannot protect Git authority owned by a foreign principal."""
    import os

    path, head = checkout(tmp_path)
    target = path / ".git" / relative
    if relative in ("refs/heads/nested", "objects/info/commit-graphs"):
        target.mkdir()
    original_lstat = Path.lstat
    original_run = subprocess.run
    checkout_commands = []

    def foreign_authority_lstat(self, *args, **kwargs):
        metadata = original_lstat(self, *args, **kwargs)
        if self == target:
            fields = list(metadata)
            fields[4] = 424242 if os.geteuid() != 424242 else 424243
            return os.stat_result(fields)
        return metadata

    def observed_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", foreign_authority_lstat)
    monkeypatch.setattr(subprocess, "run", observed_run)
    result = inspect_checkout(path, head)

    assert "mutable_git_authority_ownership" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX Git metadata custody")
@pytest.mark.parametrize(
    "name", ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REBASE_HEAD", "FETCH_HEAD", "ORIG_HEAD")
)
@pytest.mark.parametrize("alias", ("symlink", "hardlink", "peer_writable"))
def test_pseudoref_custody_rejected_before_checkout_git(tmp_path, monkeypatch, name, alias):
    """Pseudo-refs used by Git status/recovery cannot borrow mutable authority."""
    path, head = checkout(tmp_path)
    entry = path / ".git" / name
    if entry.is_symlink() or entry.exists():
        entry.unlink()
    external = tmp_path / ("external-" + name)
    external.write_text(head + "\n")
    if alias == "symlink":
        entry.symlink_to(external)
    elif alias == "hardlink":
        entry.hardlink_to(external)
    else:
        entry.write_text(head + "\n")
        entry.chmod(0o666)

    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(list(argv))
            raise AssertionError("mutable pseudo-ref reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    expected_blocker = (
        "mutable_git_authority_permissions"
        if alias == "peer_writable" else "external_git_metadata"
    )
    assert expected_blocker in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"



def test_private_orig_head_does_not_borrow_external_authority(tmp_path):
    """A normal private pseudo-ref is permitted; only mutable aliases fail."""
    path, head = checkout(tmp_path)
    (path / ".git" / "ORIG_HEAD").write_text(head + "\n")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("dangling", (False, True))
def test_symlinked_object_info_root_rejected_before_checkout_git(
    tmp_path, monkeypatch, dangling
):
    """Even empty or dangling borrowed object-info directories are not local authority."""
    path, head = checkout(tmp_path)
    info = path / ".git" / "objects" / "info"
    outside = tmp_path / "outside-object-info"
    info.rename(outside)
    target = tmp_path / "missing-object-info" if dangling else outside
    info.symlink_to(target, target_is_directory=True)

    actual_run = subprocess.run
    checkout_commands = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(tuple(argv))
            raise AssertionError("borrowed object-info reached checkout Git")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "external_object_store" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
    assert checkout_commands == []


@pytest.mark.parametrize("key", (
    "diff.external",
    "diff.untrusted.command",
    "diff.untrusted.textconv",
    "diff.nested.driver.textconv",
))
def test_executable_diff_configuration_is_rejected_before_checkout_git(tmp_path, monkeypatch, key):
    """Diff drivers/textconv are executable review authority, not passive metadata."""
    path, head = checkout(tmp_path)
    git(path, "config", "--local", key, "/nonexistent/host-diff")
    actual_run = subprocess.run
    checkout_commands = []

    def watched_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_commands.append(tuple(argv))
            raise AssertionError("checkout Git invoked before rejecting executable diff")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", watched_run)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert checkout_commands == []
    assert result.authority_gain == "NONE"


def test_ambient_external_diff_override_is_not_standalone(tmp_path, monkeypatch):
    path, head = checkout(tmp_path)
    monkeypatch.setenv("GIT_EXTERNAL_DIFF", "/nonexistent/host-diff")
    result = inspect_checkout(path, head)
    assert result.blockers == ("ambient_git_authority_override",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


def test_dangling_commondir_alias_is_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A dangling common-dir alias is mutable external Git authority, not absence."""
    path, head = checkout(tmp_path)
    (path / ".git" / "commondir").symlink_to(tmp_path / "not-yet-present")
    original_run = subprocess.run
    checkout_calls = []

    def guard_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_calls.append(list(argv))
            raise AssertionError("checkout Git reached dangling common-dir authority")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guard_run)
    result = inspect_checkout(path, head)
    assert "shared_git_directory" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
    assert checkout_calls == []


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX FIFO metadata")
@pytest.mark.parametrize(
    "relative,blocker",
    (
        ("HEAD", "external_git_metadata"),
        ("config", "external_git_metadata"),
        ("refs/heads/master", "external_git_metadata"),
        ("objects/info/commit-graph", "external_object_store"),
        ("objects/pack/pack-bogus.pack", "external_object_store"),
        ("objects/ab/" + "0" * 38, "external_object_store"),
    ),
)
def test_special_git_metadata_rejected_before_checkout_git(tmp_path, monkeypatch, relative, blocker):
    """Git authority supplied as a FIFO must fail closed without blocking Git."""
    import os

    path, head = checkout(tmp_path)
    entry = path / ".git" / relative
    if entry.exists():
        entry.unlink()
    entry.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(entry, 0o600)
    original_run = subprocess.run
    checkout_calls = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_calls.append(list(argv))
            raise AssertionError("special Git metadata reached checkout Git")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert blocker in result.blockers
    assert result.observed_head is None
    assert checkout_calls == []
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("alias", ("symlink", "hardlink", "peer_writable"))
def test_reflog_metadata_custody_rejected_before_checkout_git(tmp_path, monkeypatch, alias):
    """Git revision selectors can consume reflogs; external mutable logs are not standalone."""
    path, head = checkout(tmp_path)
    log = path / ".git" / "logs" / "HEAD"
    outside = tmp_path / "external-reflog"
    outside.write_bytes(log.read_bytes())
    if alias == "symlink":
        log.unlink()
        log.symlink_to(outside)
    elif alias == "hardlink":
        log.unlink()
        log.hardlink_to(outside)
    else:
        log.chmod(0o666)

    original_run = subprocess.run
    checkout_calls = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_calls.append(list(argv))
            raise AssertionError("mutable reflog reached checkout Git")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    blocker = (
        "mutable_git_authority_permissions"
        if alias == "peer_writable"
        else "external_git_metadata"
    )
    assert blocker in result.blockers
    assert result.observed_head is None
    assert checkout_calls == []
    assert result.authority_gain == "NONE"


def test_peer_writable_nested_reflog_directory_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A peer-writable reflog parent permits a replacement even when logs are private."""
    path, head = checkout(tmp_path)
    logs = path / ".git" / "logs" / "refs" / "heads"
    assert logs.is_dir()
    logs.chmod(0o777)
    original_run = subprocess.run
    checkout_calls = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_calls.append(list(argv))
            raise AssertionError("mutable reflog directory reached checkout Git")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert checkout_calls == []
    assert result.authority_gain == "NONE"



@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX metadata custody")
@pytest.mark.parametrize(
    "mutation,expected_blocker",
    (
        ("modules_symlink", "external_git_metadata"),
        ("modules_peer_writable", "mutable_git_authority_permissions"),
        ("nested_config_symlink", "external_git_metadata"),
        ("nested_config_hardlink", "external_git_metadata"),
        ("nested_fifo", "external_git_metadata"),
    ),
)
def test_git_submodule_metadata_custody_rejected_before_checkout_git(
    tmp_path, monkeypatch, mutation, expected_blocker
):
    """Git submodule metadata cannot borrow externally mutable authority."""
    import os

    path, head = checkout(tmp_path)
    modules = path / ".git" / "modules"
    outside = tmp_path / "external-submodule-metadata"
    outside.mkdir()
    if mutation == "modules_symlink":
        modules.symlink_to(outside, target_is_directory=True)
    else:
        modules.mkdir()
        if mutation == "modules_peer_writable":
            modules.chmod(0o777)
        else:
            nested = modules / "vendor"
            nested.mkdir()
            entry = nested / ("HEAD" if mutation == "nested_fifo" else "config")
            if mutation == "nested_fifo":
                os.mkfifo(entry)
            else:
                source = outside / "config"
                source.write_text("[core]\n\trepositoryformatversion = 0\n")
                if mutation == "nested_config_symlink":
                    entry.symlink_to(source)
                else:
                    entry.hardlink_to(source)

    original_run = subprocess.run
    checkout_calls = []

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            checkout_calls.append(list(argv))
            raise AssertionError("submodule metadata reached checkout Git")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert expected_blocker in result.blockers
    assert result.observed_head is None
    assert checkout_calls == []
    assert result.authority_gain == "NONE"



def test_private_submodule_metadata_does_not_reject_parent_checkout(tmp_path):
    """Owned, non-aliased module metadata is not itself an external dependency."""
    path, head = checkout(tmp_path)
    module = path / ".git" / "modules" / "vendor"
    module.mkdir(parents=True)
    (module / "config").write_text("[core]\n\trepositoryformatversion = 0\n")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"
