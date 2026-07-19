"""Static review for Git operations over untrusted repository content."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".go", ".py", ".js", ".jsx", ".ts", ".tsx", ".sh", ".bash"}
_UNTRUSTED_CONTEXT = (
    "worktree",
    "pull request",
    "pull-request",
    "fork",
    "review task",
    "head branch",
    ".gitmodules",
)


def _safe_text(root: Path, relative: str) -> str:
    try:
        resolved_root = root.resolve()
        path = (resolved_root / relative).resolve()
        if not path.is_relative_to(resolved_root) or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line(text: str, offset: int) -> int:
    return text[: max(0, offset)].count("\n") + 1


def _is_hardened(text: str) -> bool:
    lowered = text.lower()
    transport_default_deny = "protocol.allow=never" in lowered
    command_transport_disabled = "protocol.ext.allow=never" in lowered
    hooks_disabled = "core.hookspath" in lowered
    noninteractive = (
        "git_terminal_prompt=0" in lowered
        or "newnoninteractivegitcmd" in lowered
        or "batchmode=yes" in lowered
    )
    return transport_default_deny and command_transport_disabled and hooks_disabled and noninteractive


def _finding(path: str, line: int) -> dict[str, Any]:
    return {
        "source": "static-untrusted-git-officer",
        "officer": "Challenger",
        "capability": "security",
        "category": "security",
        "severity": "critical",
        "root_cause": "untrusted-git-submodule-init-without-transport-hardening",
        "path": path,
        "line_start": line,
        "line_end": line,
        "evidence_ref": f"{path}:{line}",
        "supporting_evidence_refs": [f"{path}:{line}"],
        "message": "Git initializes submodules from externally controlled repository metadata without a deny-by-default transport and hook boundary.",
        "evidence": (
            "The command executes `git submodule update --init` in a review/worktree context, while the command construction does not "
            "pin protocol.allow=never, protocol.ext.allow=never, a disabled hooks path, and non-interactive Git execution."
        ),
        "falsifiers_checked": [
            "Checked for a review, fork, HEAD, worktree or .gitmodules trust-boundary signal.",
            "Checked for command-line protocol default-deny and explicit ext transport denial.",
            "Checked for hook neutralization and non-interactive Git environment handling.",
        ],
        "verification_test": (
            "Build the submodule command through one hardened sink, deny every protocol by default, allow only required transports, "
            "disable hooks and prompts, then prove ext::, file:// and plain-http submodules cannot execute or fetch."
        ),
        "confidence": 0.99,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def run_static_untrusted_git_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []

    command_re = re.compile(
        r"(?:exec\.Command(?:Context)?|subprocess\.(?:run|Popen|check_call|check_output)|\b(?:run|exec|spawn)\s*\()"
        r"[\s\S]{0,500}?[\"']git[\"'][\s\S]{0,500}?[\"']submodule[\"'][\s\S]{0,300}?[\"']update[\"']"
        r"[\s\S]{0,300}?--init",
        re.I,
    )
    shell_re = re.compile(r"\bgit\s+submodule\s+update\b[^\n]{0,300}--init", re.I)

    for path in changed:
        if Path(path).suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        lowered = f"{path}\n{text}".lower()
        if not any(signal in lowered for signal in _UNTRUSTED_CONTEXT):
            continue
        match = command_re.search(text) or shell_re.search(text)
        if match is None or _is_hardened(text):
            continue
        findings.append(_finding(path, _line(text, match.start())))

    unique = {(str(item["root_cause"]), str(item["path"])): item for item in findings}
    return {
        "schema_version": "sergeant.static-untrusted-git-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
