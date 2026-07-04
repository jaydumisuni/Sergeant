"""THETECHGUY engineering standard executable checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .diff_review import review_changed_files
from .verification import verify_repository_standard


def check_claims_match_implementation(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    docs_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(root_path.glob("docs/*.md"))
    )
    findings: list[dict[str, object]] = []
    if "AI reasoning" in docs_text and not any(root_path.glob("main_review/*reason*.py")):
        findings.append(
            {
                "severity": "major",
                "category": "claims",
                "message": "Documentation claims AI reasoning but no reasoning module exists.",
                "evidence": "Claims must match implementation before release.",
            }
        )
    if "clean-clone" in docs_text and not (root_path / ".github" / "workflows" / "ci.yml").exists():
        findings.append(
            {
                "severity": "major",
                "category": "proof",
                "message": "Clean-clone proof is documented but CI workflow is missing.",
                "evidence": "Proof claims need executable proof path.",
            }
        )
    return {"finding_count": len(findings), "findings": findings}


def run_standard_engine(root: str | Path = ".", changed_files: list[str] | None = None) -> dict[str, Any]:
    root_path = Path(root)
    verification = verify_repository_standard(root_path).to_dict()
    claims = check_claims_match_implementation(root_path)
    diff = review_changed_files(changed_files or []) if changed_files is not None else None

    blockers: list[str] = []
    if verification.get("status") != "verified":
        blockers.append("Verification standard is not fully verified.")
    if claims.get("finding_count", 0):
        blockers.append("Claims do not fully match implementation.")

    return {
        "passed": not blockers,
        "blockers": blockers,
        "verification": verification,
        "claims": claims,
        "diff_review": diff,
        "standard": "THETECHGUY Engineering Standard v1",
    }
