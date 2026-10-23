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
