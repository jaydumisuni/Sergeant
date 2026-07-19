"""Provenance validation for frozen external review-training manifests."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_FRESH_CLASSIFICATION = "untouched_transfer_validation"
_PROVENANCE_VERSION = "sergeant.training-provenance.v1"


class ProvenanceError(ValueError):
    """Raised when a training manifest cannot prove its claimed lineage."""


def _run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = ["git", "-C", str(root), *args]
    try:
        return subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            detail = (exc.stderr or exc.stdout or "").strip()
        else:
            detail = str(exc)
        raise ProvenanceError(
            f"git command failed in {root}: {' '.join(args)}: {detail}"
        ) from exc


def _require_text(mapping: dict[str, Any], key: str, *, case_id: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProvenanceError(f"case {case_id} requires non-empty `{key}`")
    return value.strip()


def _require_sha(value: str, *, field: str, case_id: str) -> str:
    lowered = value.lower()
    if not _SHA_RE.fullmatch(lowered):
        raise ProvenanceError(
            f"case {case_id} `{field}` must be a full 40-character commit SHA"
        )
    return lowered


def _normalise_paths(
    value: object,
    *,
    field: str,
    case_id: str,
    required: bool,
) -> list[str]:
    if value is None and not required:
        return []
    if not isinstance(value, list):
        raise ProvenanceError(f"case {case_id} `{field}` must be a list")
    rows: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ProvenanceError(
                f"case {case_id} `{field}` contains an empty or non-string path"
            )
        path = item.strip().replace("\\", "/")
        if path.startswith("/") or ".." in Path(path).parts:
            raise ProvenanceError(
                f"case {case_id} `{field}` contains unsafe path: {path}"
            )
        if path not in rows:
            rows.append(path)
    if required and not rows:
        raise ProvenanceError(
            f"case {case_id} requires at least one `{field}` path"
        )
    return rows


def _commit_exists(root: Path, ref: str, *, case_id: str, field: str) -> None:
    result = _run_git(root, "cat-file", "-e", f"{ref}^{{commit}}", check=False)
    if result.returncode != 0:
        raise ProvenanceError(
            f"case {case_id} `{field}` is not available in checkout: {ref}"
        )


def _path_exists_at(
    root: Path,
    ref: str,
    path: str,
    *,
    case_id: str,
    field: str,
) -> None:
    result = _run_git(root, "cat-file", "-e", f"{ref}:{path}", check=False)
    if result.returncode != 0:
        raise ProvenanceError(
            f"case {case_id} `{field}` path does not exist at defective ref "
            f"{ref}: {path}"
        )


def validate_case_provenance(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "<unknown>")
    checkout = Path(
        _require_text(case, "checkout_path", case_id=case_id)
    ).resolve()
    if not checkout.is_dir():
        raise ProvenanceError(f"case {case_id} checkout is missing: {checkout}")
    if not (checkout / ".git").exists():
        raise ProvenanceError(
            f"case {case_id} checkout is not a Git repository: {checkout}"
        )

    defective = _require_sha(
        _require_text(case, "defective_ref", case_id=case_id),
        field="defective_ref",
        case_id=case_id,
    )
    fixing = _require_sha(
        _require_text(case, "fixing_ref", case_id=case_id),
        field="fixing_ref",
        case_id=case_id,
    )
    if defective == fixing:
        raise ProvenanceError(
            f"case {case_id} defective and fixing refs are identical"
        )

    source_pr = case.get("source_pr")
    source_lineage = case.get("source_lineage")
    if not (isinstance(source_pr, int) and source_pr > 0):
        if not isinstance(source_lineage, str) or not source_lineage.strip():
            raise ProvenanceError(
                f"case {case_id} requires a positive `source_pr` or "
                "non-empty `source_lineage`"
            )

    changed_files = _normalise_paths(
        case.get("changed_files"),
        field="changed_files",
        case_id=case_id,
        required=True,
    )
    context_files = _normalise_paths(
        case.get("context_files"),
        field="context_files",
        case_id=case_id,
        required=False,
    )
    overlap = sorted(set(changed_files) & set(context_files))
    if overlap:
        raise ProvenanceError(
            f"case {case_id} paths cannot be both changed and context-only: "
            f"{', '.join(overlap)}"
        )

    _commit_exists(
        checkout, defective, case_id=case_id, field="defective_ref"
    )
    _commit_exists(checkout, fixing, case_id=case_id, field="fixing_ref")

    ancestor = _run_git(
        checkout,
        "merge-base",
        "--is-ancestor",
        defective,
        fixing,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ProvenanceError(
            f"case {case_id} fixing ref is not a descendant of defective ref"
        )

    head = _run_git(checkout, "rev-parse", "HEAD").stdout.strip().lower()
    if head != defective:
        raise ProvenanceError(
            f"case {case_id} checkout HEAD must equal defective_ref: "
            f"{head} != {defective}"
        )

    diff = _run_git(
        checkout,
        "diff",
        "--name-only",
        defective,
        fixing,
        "--",
        *changed_files,
    ).stdout.splitlines()
    changed_by_fix = {
        line.strip().replace("\\", "/") for line in diff if line.strip()
    }
    missing = [path for path in changed_files if path not in changed_by_fix]
    if missing:
        raise ProvenanceError(
            f"case {case_id} fixing lineage does not modify scored paths: "
            f"{', '.join(missing)}"
        )

    for path in changed_files:
        _path_exists_at(
            checkout,
            defective,
            path,
            case_id=case_id,
            field="changed_files",
        )
    for path in context_files:
        _path_exists_at(
            checkout,
            defective,
            path,
            case_id=case_id,
            field="context_files",
        )

    return {
        "case_id": case_id,
        "defective_ref": defective,
        "fixing_ref": fixing,
        "changed_files": changed_files,
        "context_files": context_files,
        "source_pr": source_pr,
        "source_lineage": source_lineage,
        "status": "verified",
    }


def validate_training_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    rules = manifest.get("rules")
    if not isinstance(rules, dict):
        raise ProvenanceError("training manifest requires a `rules` object")
    classification = rules.get("classification")
    if classification != _FRESH_CLASSIFICATION:
        raise ProvenanceError(
            f"provenance v1 only validates `{_FRESH_CLASSIFICATION}` manifests"
        )
    if rules.get("provenance_contract") != _PROVENANCE_VERSION:
        raise ProvenanceError(
            "fresh manifest requires "
            f"rules.provenance_contract={_PROVENANCE_VERSION}"
        )
    reviewer = rules.get("reviewer_code_frozen_before_target_selection")
    if not isinstance(reviewer, str) or not _SHA_RE.fullmatch(reviewer.lower()):
        raise ProvenanceError(
            "fresh manifest requires a full "
            "reviewer_code_frozen_before_target_selection SHA"
        )

    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ProvenanceError(
            "training manifest must contain at least one case"
        )
    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in cases:
        if not isinstance(raw, dict):
            raise ProvenanceError("every training case must be an object")
        case_id = str(raw.get("case_id") or "")
        if not case_id or case_id in seen:
            raise ProvenanceError(
                f"case ids must be non-empty and unique: {case_id!r}"
            )
        seen.add(case_id)
        verified.append(validate_case_provenance(raw))

    return {
        "schema_version": _PROVENANCE_VERSION,
        "set_id": manifest.get("set_id"),
        "reviewer_head": reviewer.lower(),
        "case_count": len(verified),
        "cases": verified,
        "status": "verified",
    }
