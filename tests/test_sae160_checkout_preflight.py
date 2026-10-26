"""SAE-160 standalone checkout preflight cannot grant qualification."""
from __future__ import annotations

from pathlib import Path
import os
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


@pytest.mark.parametrize("packed", (False, True))
def test_git_replace_refs_never_qualify_exact_head(tmp_path, packed):
    """Replacement refs can alter object semantics with identical HEAD/status."""
    path, head = checkout(tmp_path)
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "user.name", "Test")
    git(path, "commit", "--allow-empty", "-qm", "replacement")
    substitute = git(path, "rev-parse", "HEAD")
    git(path, "reset", "--hard", "-q", head)
    git(path, "replace", head, substitute)
    if packed:
        git(path, "pack-refs", "--all", "--prune")
        assert "refs/replace/" in (path / ".git" / "packed-refs").read_text()
    assert git(path, "rev-parse", "HEAD") == head
    assert git(path, "show", "-s", "--format=%s", "HEAD") == "replacement"
    assert git(path, "status", "--porcelain") == ""

    result = inspect_checkout(path, head)
    assert result.blockers == ("git_replace_object_dependency",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("ignore_source", ("local_exclude", "tracked_gitignore"))
def test_ignored_untracked_artifact_cannot_qualify_clean_clone(tmp_path, ignore_source):
    """Hidden mutable artifacts must not qualify a standalone clean clone."""
    path, head = checkout(tmp_path)
    if ignore_source == "local_exclude":
        (path / ".git" / "info" / "exclude").write_text("hidden-evidence.txt\n")
    else:
        (path / ".gitignore").write_text("hidden-evidence.txt\n")
        git(path, "add", ".gitignore")
        git(path, "config", "--local", "user.email", "fixture@example.invalid")
        git(path, "config", "--local", "user.name", "Fixture")
        git(path, "commit", "-qm", "fixture: tracked ignore rule")
        head = git(path, "rev-parse", "HEAD")
    (path / "hidden-evidence.txt").write_text("unreviewed content\n")
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    result = inspect_checkout(path, head)
    assert "dirty_or_unverified_checkout" in result.blockers
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX symlink fixture")
@pytest.mark.parametrize("target", (
    "../outside-proof.txt",
    "/etc/passwd",
    "tracked.txt",
))
def test_tracked_symlink_cannot_qualify_standalone_checkout(tmp_path, monkeypatch, target):
    """A clean Git index can still contain a mutable external symlink target."""
    path, _ = checkout(tmp_path)
    (path / "proof-alias").symlink_to(target)
    git(path, "add", "proof-alias")
    git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "fixture: tracked evidence symlink")
    head = git(path, "rev-parse", "HEAD")
    assert git(path, "status", "--porcelain", "--untracked-files=all",
               "--ignored=matching") == ""
    assert any(line.startswith("120000 ") for line in git(
        path, "ls-files", "--stage"
    ).splitlines())

    actual_run = subprocess.run

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)] and "status" in argv:
            raise AssertionError("tracked symlink reached checkout status")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert result.blockers == ("external_worktree_symlink_dependency",)
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX inode custody")
@pytest.mark.parametrize("custody, blocker", (
    ("external_hardlink", "external_worktree_file_dependency"),
    ("group_writable", "mutable_worktree_file_permissions"),
))
def test_tracked_regular_file_inode_custody_precedes_status(
    tmp_path, monkeypatch, custody, blocker
):
    """A tracked file can be clean yet aliased or writable by another principal."""
    path, head = checkout(tmp_path)
    tracked = path / "tracked.txt"
    if custody == "external_hardlink":
        (tmp_path / "outside-tracked-alias").hardlink_to(tracked)
        assert tracked.stat().st_nlink == 2
    else:
        tracked.chmod(tracked.stat().st_mode | 0o020)
        assert tracked.stat().st_mode & 0o020
    assert git(path, "status", "--porcelain", "--untracked-files=all",
               "--ignored=matching") == ""

    actual_run = subprocess.run

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)] and "status" in argv:
            raise AssertionError("unsafe tracked file reached checkout status")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert result.blockers == (blocker,)
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX parent custody")
@pytest.mark.parametrize(("custody", "blocker"), (
    ("group_writable", "mutable_worktree_directory_permissions"),
    ("other_writable", "mutable_worktree_directory_permissions"),
    ("symlinked_parent", "external_worktree_directory_dependency"),
))
def test_tracked_file_parent_custody_precedes_git_status(
    tmp_path, monkeypatch, custody, blocker
):
    """A private tracked inode is not standalone when its parent is mutable."""
    path, _ = checkout(tmp_path)
    parent = path / "nested"
    parent.mkdir()
    (parent / "evidence.txt").write_text("pinned\\n")
    git(path, "add", "nested/evidence.txt")
    git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "fixture: nested tracked evidence")
    head = git(path, "rev-parse", "HEAD")

    if custody == "symlinked_parent":
        outside = tmp_path / "outside-evidence-directory"
        parent.rename(outside)
        parent.symlink_to(outside, target_is_directory=True)
    else:
        parent.chmod(parent.stat().st_mode | (0o020 if custody == "group_writable" else 0o002))
        assert git(path, "status", "--porcelain", "--untracked-files=all",
                   "--ignored=matching") == ""

    actual_run = subprocess.run

    def guarded_run(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)] and "status" in argv:
            raise AssertionError("mutable tracked parent reached Git status")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", guarded_run)
    result = inspect_checkout(path, head)
    assert result.blockers == (blocker,)
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX inode custody")
@pytest.mark.parametrize("replacement", ("tracked_file", "tracked_parent"))
def test_same_byte_worktree_substitution_after_clean_status_is_rejected(
    tmp_path, monkeypatch, replacement
):
    """Status is not an atomic custody snapshot of the tracked worktree."""
    path, _ = checkout(tmp_path)
    parent = path / "nested"
    parent.mkdir()
    tracked_file = parent / "evidence.txt"
    tracked_file.write_text("pinned\\n")
    git(path, "add", "nested/evidence.txt")
    git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "fixture: nested tracked evidence")
    head = git(path, "rev-parse", "HEAD")

    actual_run = subprocess.run
    clean_status_observed = []

    def replace_after_status(argv, *args, **kwargs):
        result = actual_run(argv, *args, **kwargs)
        if list(argv[:3]) == ["git", "-C", str(path)] and "status" in argv:
            assert result.returncode == 0
            assert result.stdout == ""
            if replacement == "tracked_parent":
                parent.rename(tmp_path / "original-parent")
                parent.mkdir()
                tracked_file.write_text("pinned\\n")
            else:
                tracked_file.rename(tmp_path / "original-evidence.txt")
                tracked_file.write_text("pinned\\n")
            clean_status_observed.append(True)
        return result

    monkeypatch.setattr(subprocess, "run", replace_after_status)
    result = inspect_checkout(path, head)
    assert clean_status_observed == [True]
    assert result.blockers == ("tracked_worktree_custody_changed",)
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


def test_nul_delimited_index_preserves_tracked_whitespace_filename(tmp_path):
    """Tracked filenames with embedded newlines and trailing spaces stay intact."""
    path, _ = checkout(tmp_path)
    unusual = path / "odd\nname "
    unusual.write_text("ordinary tracked content\n")
    git(path, "add", unusual.name)
    git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "fixture: unusual tracked filename")
    head = git(path, "rev-parse", "HEAD")
    result = inspect_checkout(path, head)
    assert result.blockers == ()
    assert result.observed_head == head
    assert result.authority_gain == "NONE"


@pytest.mark.skipif(os.name != "posix", reason="raw-byte POSIX filename fixture")
def test_undecodable_tracked_index_entry_fails_closed(tmp_path):
    """Git allows non-UTF8 path bytes; decoding must not crash preflight."""
    path, _ = checkout(tmp_path)
    raw_path = os.fsencode(path) + b"/non-utf8-\xff.txt"
    with open(raw_path, "wb") as stream:
        stream.write(b"immutable evidence\n")
    git(path, "add", "-A")
    git(path, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "fixture: non-UTF8 tracked filename")
    head = git(path, "rev-parse", "HEAD")
    assert git(path, "status", "--porcelain", "--untracked-files=all",
               "--ignored=matching") == ""

    result = inspect_checkout(path, head)
    assert result.blockers == ("unverified_index_entries",)
    assert result.observed_head == head
    assert result.authority_gain == "NONE"



def test_git_index_probe_decodes_explicit_utf8_on_every_host(tmp_path, monkeypatch):
    """The index decoder must not inherit a permissive host locale."""
    path, head = checkout(tmp_path)
    actual_run = subprocess.run
    observed_encodings = []

    def capture_index_probe(argv, *args, **kwargs):
        if (list(argv[:3]) == ["git", "-C", str(path)]
                and list(argv[3:]) == ["ls-files", "--stage", "-z"]):
            observed_encodings.append(kwargs.get("encoding"))
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", capture_index_probe)
    result = inspect_checkout(path, head)
    assert observed_encodings == ["utf-8"]
    assert result.blockers == ()
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


@pytest.mark.parametrize("name,value", (
    ("GIT_CONFIG_COUNT", "0"),
    ("GIT_CONFIG_PARAMETERS", "'core.fsmonitor=/nonexistent/monitor'"),
    ("GIT_EXTERNAL_DIFF", "/nonexistent/diff"),
    ("GIT_REPLACE_REF_BASE", "refs/replace/external"),
    ("GIT_TRACE2_EVENT", "/nonexistent/trace-events"),
    ("GIT_TRACE_SETUP", "/nonexistent/setup-trace"),
    ("GIT_TRACE_PACKET", "/nonexistent/packet-trace"),
    ("GIT_TRACE_PACK_ACCESS", "/nonexistent/pack-trace"),
    ("GIT_TRACE_PERFORMANCE", "/nonexistent/performance-trace"),
    ("GIT_TRACE_CURL", "/nonexistent/curl-trace"),
    ("GIT_TRACE2_CONFIG_PARAMS", "core.fsmonitor"),
))
def test_ambient_git_controls_rejected_before_any_git_process(tmp_path, monkeypatch, name, value):
    """Ambient Git overrides must not reach even the local config probe."""
    path, head = checkout(tmp_path)
    monkeypatch.setenv(name, value)
    original_run = subprocess.run
    git_calls = []

    def reject_git_process(argv, *args, **kwargs):
        if argv and argv[0] == "git":
            git_calls.append(tuple(argv))
            raise AssertionError("Git invoked before rejecting ambient controls")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", reject_git_process)
    result = inspect_checkout(path, head)
    assert result.blockers == ("ambient_git_authority_override",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
    assert git_calls == []


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


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX Git metadata custody")
@pytest.mark.parametrize(
    "relative",
    (".git/HEAD", ".git/objects/info", ".git/objects/pack"),
)
def test_foreign_owned_git_metadata_never_reaches_git_config(
    tmp_path, monkeypatch, relative
):
    """A foreign owner can rewrite a mode-0755 Git object or ref directory."""
    import os

    path, head = checkout(tmp_path)
    target = path / relative
    assert target.exists()
    original_lstat = Path.lstat
    original_run = subprocess.run
    git_calls = []

    def foreign_metadata_lstat(self, *args, **kwargs):
        metadata = original_lstat(self, *args, **kwargs)
        if self == target:
            fields = list(metadata)
            fields[4] = 424242 if os.geteuid() != 424242 else 424243
            return os.stat_result(fields)
        return metadata

    def forbid_git_process(argv, *args, **kwargs):
        if argv and argv[0] == "git":
            git_calls.append(list(argv))
            raise AssertionError("foreign-owned Git metadata reached git subprocess")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", foreign_metadata_lstat)
    monkeypatch.setattr(subprocess, "run", forbid_git_process)
    result = inspect_checkout(path, head)

    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
    assert git_calls == []


def test_populated_gitlink_submodule_cannot_pass_standalone_preflight(tmp_path, monkeypatch):
    """A clean parent status cannot qualify independently configured submodule Git."""
    path, _ = checkout(tmp_path)
    child = tmp_path / "submodule-origin"
    child.mkdir()
    subprocess.check_call(["git", "init", "-q", str(child)])
    git(child, "config", "user.email", "test@example.invalid")
    git(child, "config", "user.name", "Test")
    (child / "child.txt").write_text("child\n")
    git(child, "add", "child.txt")
    git(child, "commit", "-qm", "child")
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "user.name", "Test")
    subprocess.check_call([
        "git", "-C", str(path), "-c", "protocol.file.allow=always",
        "submodule", "add", "-q", str(child), "vendor/child",
    ])
    git(path, "commit", "-qm", "add submodule")
    head = git(path, "rev-parse", "HEAD")
    assert git(path, "status", "--porcelain", "--untracked-files=all") == ""
    assert "160000 " in git(path, "ls-files", "--stage")

    actual_run = subprocess.run
    checkout_status_calls = []

    def forbid_checkout_status(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)] and "status" in argv[3:]:
            checkout_status_calls.append(tuple(argv))
            raise AssertionError("submodule-aware status ran before gitlink rejection")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", forbid_checkout_status)
    result = inspect_checkout(path, head)
    assert "external_submodule_dependency" in result.blockers
    assert result.authority_gain == "NONE"
    assert checkout_status_calls == []


def test_unverified_index_inventory_fails_closed_before_status(tmp_path, monkeypatch):
    """An unreadable index cannot be treated as proof of no Git submodules."""
    path, head = checkout(tmp_path)
    actual_run = subprocess.run
    status_calls = []

    def fail_index_read(argv, *args, **kwargs):
        if list(argv[:3]) == ["git", "-C", str(path)]:
            if list(argv[3:]) == ["ls-files", "--stage", "-z"]:
                raise subprocess.CalledProcessError(128, argv)
            if "status" in argv[3:]:
                status_calls.append(tuple(argv))
                raise AssertionError("status ran after index inventory failure")
        return actual_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_index_read)
    result = inspect_checkout(path, head)
    assert result.blockers == ("unverified_index_entries",)
    assert result.authority_gain == "NONE"
    assert status_calls == []


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX Git hooks custody")
def test_symlinked_hooks_directory_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A private .git with externally supplied hooks is not standalone."""
    path, head = checkout(tmp_path)
    hooks = path / ".git" / "hooks"
    external = tmp_path / "external-hooks"
    hooks.rename(external)
    hooks.symlink_to(external, target_is_directory=True)
    original_run = subprocess.run
    git_calls = []

    def forbid_git(argv, *args, **kwargs):
        if argv and argv[0] == "git":
            git_calls.append(tuple(argv))
            raise AssertionError("Git executed before rejecting external hooks")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", forbid_git)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
    assert git_calls == []


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX Git hooks custody")
def test_hardlinked_hook_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A hardlinked hook can be rewritten through another pathname."""
    path, head = checkout(tmp_path)
    external = tmp_path / "external-hook"
    external.write_text("#!/bin/sh\nexit 0\n")
    external.chmod(0o755)
    (path / ".git" / "hooks" / "pre-commit").hardlink_to(external)
    original_run = subprocess.run
    git_calls = []

    def forbid_git(argv, *args, **kwargs):
        if argv and argv[0] == "git":
            git_calls.append(tuple(argv))
            raise AssertionError("Git executed before rejecting hardlinked hook")
        return original_run(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", forbid_git)
    result = inspect_checkout(path, head)
    assert "external_git_metadata" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
    assert git_calls == []


@pytest.mark.skipif(__import__("os").name != "posix", reason="POSIX Git hooks custody")
def test_peer_writable_hooks_directory_rejected_before_checkout_git(tmp_path, monkeypatch):
    """A peer can install a hook without touching private refs or objects."""
    import stat

    path, head = checkout(tmp_path)
    hooks = path / ".git" / "hooks"
    original_mode = stat.S_IMODE(hooks.stat().st_mode)
    original_run = subprocess.run
    git_calls = []

    def forbid_git(argv, *args, **kwargs):
        if argv and argv[0] == "git":
            git_calls.append(tuple(argv))
            raise AssertionError("Git executed before rejecting mutable hooks")
        return original_run(argv, *args, **kwargs)

    try:
        hooks.chmod(original_mode | stat.S_IWGRP)
        monkeypatch.setattr(subprocess, "run", forbid_git)
        result = inspect_checkout(path, head)
    finally:
        hooks.chmod(original_mode)

    assert "mutable_git_authority_permissions" in result.blockers
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
    assert git_calls == []
