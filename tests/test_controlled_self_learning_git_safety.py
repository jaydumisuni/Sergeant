from __future__ import annotations

from pathlib import Path

from scripts import run_controlled_self_learning as controlled


def _case() -> dict:
    return {
        "case_id": "case-git-safety",
        "repository": "jaydumisuni/example",
        "source_event_url": "https://github.com/jaydumisuni/example/commit/source",
        "defective_ref": "b" * 40,
        "fixing_ref": "c" * 40,
        "scored_paths": ["src/example.py"],
        "language": "python",
    }


def test_generated_checkout_git_commands_use_exact_invocation_scoped_safe_directory(tmp_path: Path, monkeypatch) -> None:
    case = _case()
    root = tmp_path / "checkouts"
    root.mkdir()
    destination = root / case["case_id"]
    calls: list[tuple[str, ...]] = []

    def fake_run(*args: str, cwd=None, capture: bool = False) -> str:
        calls.append(tuple(args))
        if args[:2] == ("git", "init"):
            (destination / ".git" / "info").mkdir(parents=True, exist_ok=True)
        if "checkout" in args:
            source = destination / "src" / "example.py"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("print('defective')\n", encoding="utf-8")
        if capture and args[-2:] == ("rev-parse", "HEAD"):
            return case["defective_ref"] + "\n"
        return ""

    monkeypatch.setattr(controlled, "_run", fake_run)

    assert controlled._checkout(case, root) == destination

    assert calls[0] == ("git", "init", str(destination))
    expected_safe = f"safe.directory={destination.resolve().as_posix()}"
    for call in calls[1:]:
        assert call[:5] == ("git", "-c", expected_safe, "-C", str(destination))
        assert "safe.directory=*" not in call
        assert "--global" not in call


def test_truth_diff_uses_same_exact_safe_directory_override(tmp_path: Path, monkeypatch) -> None:
    case = _case()
    checkout = tmp_path / "generated-checkout"
    checkout.mkdir()
    calls: list[tuple[Path, tuple[str, ...], bool]] = []

    def fake_git_in_checkout(path: Path, *args: str, capture: bool = False) -> str:
        calls.append((path, tuple(args), capture))
        return "diff --git a/src/example.py b/src/example.py\n"

    monkeypatch.setattr(controlled, "_git_in_checkout", fake_git_in_checkout)
    packet = controlled._truth_packet(case, checkout, {"summaries": [{"finding_count": 1}]})

    assert packet["fixing_diff"].startswith("diff --git")
    assert calls == [
        (
            checkout,
            (
                "diff",
                "--no-ext-diff",
                "--unified=25",
                case["defective_ref"],
                case["fixing_ref"],
                "--",
                "src/example.py",
            ),
            True,
        )
    ]


def test_git_helper_never_uses_wildcard_or_persistent_global_trust(tmp_path: Path, monkeypatch) -> None:
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    captured: list[tuple[str, ...]] = []

    def fake_run(*args: str, cwd=None, capture: bool = False) -> str:
        captured.append(tuple(args))
        return ""

    monkeypatch.setattr(controlled, "_run", fake_run)
    controlled._git_in_checkout(checkout, "status", "--porcelain")

    expected_safe = f"safe.directory={checkout.resolve().as_posix()}"
    assert captured == [("git", "-c", expected_safe, "-C", str(checkout), "status", "--porcelain")]
    serialized = " ".join(captured[0])
    assert "safe.directory=*" not in serialized
    assert "--global" not in serialized
