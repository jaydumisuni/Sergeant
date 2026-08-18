from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from main_review import training_manifest_provenance as provenance
from main_review.training_manifest_provenance import ProvenanceError
from scripts import run_static_training_set as runner


def test_untouched_transfer_cannot_opt_out_of_provenance() -> None:
    manifest = {
        "rules": {
            "classification": "untouched_transfer_validation",
            "provenance_contract": "sergeant.training-provenance.v1",
            "reviewer_code_frozen_before_target_selection": "a" * 40,
        },
        "cases": [{"case_id": "fresh-a"}],
    }

    with pytest.raises(ProvenanceError, match="cannot opt out"):
        runner._validate_provenance_policy(manifest, manifest["rules"])


def test_untouched_transfer_always_calls_manifest_validator(monkeypatch) -> None:
    manifest = {
        "set_id": "fresh-set",
        "rules": {
            "classification": "untouched_transfer_validation",
            "provenance_required": True,
        },
        "cases": [{"case_id": "fresh-a"}],
    }
    expected = {"status": "verified", "case_count": 1}
    calls: list[dict] = []

    def fake_validate(packet: dict):
        calls.append(packet)
        return expected

    monkeypatch.setattr(runner, "validate_training_manifest", fake_validate)

    assert runner._validate_provenance_policy(manifest, manifest["rules"]) == expected
    assert calls == [manifest]


def test_learned_closure_without_provenance_flag_remains_separate(monkeypatch) -> None:
    manifest = {
        "rules": {
            "classification": "learned_closure",
            "historical_fresh_score_immutable": True,
        },
        "cases": [{"case_id": "learned-a"}],
    }

    def unexpected_validate(packet: dict):
        raise AssertionError("learned closure must not rewrite the frozen fresh proof")

    monkeypatch.setattr(runner, "validate_training_manifest", unexpected_validate)

    assert runner._validate_provenance_policy(manifest, manifest["rules"]) is None


def test_provenance_git_trust_is_exact_and_invocation_scoped(tmp_path: Path, monkeypatch) -> None:
    checkout = tmp_path / "generated-checkout"
    checkout.mkdir()
    captured: list[tuple[list[str], dict]] = []

    def fake_run(command, **kwargs):
        captured.append((list(command), dict(kwargs)))
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(provenance.subprocess, "run", fake_run)
    result = provenance._run_git(checkout, "rev-parse", "HEAD")

    safe = f"safe.directory={checkout.resolve().as_posix()}"
    assert result.returncode == 0
    assert captured[0][0] == [
        "git",
        "-c",
        safe,
        "-C",
        str(checkout.resolve()),
        "rev-parse",
        "HEAD",
    ]
    serialized = " ".join(captured[0][0])
    assert "safe.directory=*" not in serialized
    assert "--global" not in serialized


def test_provenance_diff_disables_external_diff_and_textconv(tmp_path: Path, monkeypatch) -> None:
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    defective = "b" * 40
    fixing = "c" * 40
    calls: list[tuple[str, ...]] = []

    def fake_git(root: Path, *args: str, check: bool = True):
        calls.append(tuple(args))
        if args[:2] == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(args, 0, stdout=defective + "\n", stderr="")
        if args and args[0] == "diff":
            return subprocess.CompletedProcess(args, 0, stdout="src/example.py\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(provenance, "_run_git", fake_git)
    result = provenance.validate_case_provenance(
        {
            "case_id": "case-safe-diff",
            "checkout_path": str(checkout),
            "defective_ref": defective,
            "fixing_ref": fixing,
            "source_pr": 1,
            "changed_files": ["src/example.py"],
        }
    )

    assert result["status"] == "verified"
    diff_call = next(call for call in calls if call and call[0] == "diff")
    assert diff_call[:4] == ("diff", "--no-ext-diff", "--no-textconv", "--name-only")
