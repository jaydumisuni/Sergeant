"""A sticky /tmp ancestor is not permission to trust a sticky checkout root.

A root-owned sticky ancestor protects the checkout directory entry. A
root-owned sticky checkout root itself remains writable by other principals,
who can add mutable workspace inputs before a non-atomic status inspection.
This is SAE-160 repository-only preparation, not SAE-150 qualification.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess

import pytest

from main_review.sae160_checkout_preflight import inspect_checkout


@pytest.mark.skipif(os.name != "posix", reason="POSIX sticky directory custody")
@pytest.mark.parametrize("permissions", (0o1777, 0o1770))
def test_root_owned_sticky_checkout_root_fails_before_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, permissions: int
) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / ".git").mkdir()

    # Model the privileged-owner case on unprivileged CI runners without
    # requiring chown or changing the runner's actual filesystem permissions.
    original_lstat = Path.lstat

    def simulated_lstat(path: Path) -> os.stat_result:
        metadata = original_lstat(path)
        if path == checkout:
            fields = list(metadata)
            fields[0] = stat.S_IFDIR | permissions
            fields[4] = 0  # root owner
            return os.stat_result(fields)
        return metadata

    monkeypatch.setattr(Path, "lstat", simulated_lstat)
    # Ambient transport policy is not the condition under test.
    monkeypatch.setattr(os, "environ", {})

    def unexpected_git(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("peer-writable checkout root must fail before Git")

    monkeypatch.setattr(subprocess, "run", unexpected_git)
    result = inspect_checkout(checkout, "a" * 40)
    assert result.blockers == ("mutable_checkout_ancestry",)
    assert result.observed_head is None
    assert result.authority_gain == "NONE"
