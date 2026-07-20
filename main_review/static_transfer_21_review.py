"""Static checks learned after transfer set 21's blind artifact was frozen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


_CS_SUFFIXES = {".cs"}


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


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _record_fields(files: dict[str, str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    pattern = re.compile(
        r"\brecord\s+struct\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<body>[\s\S]*?)\)\s*;",
        re.M,
    )
    for text in files.values():
        for match in pattern.finditer(text):
            fields: set[str] = set()
            for segment in match.group("body").split(","):
                candidate = re.search(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*$", segment.strip())
                if candidate is not None:
                    fields.add(candidate.group("name"))
            if fields:
                result.setdefault(match.group("name"), set()).update(fields)
    return result


def _finding(
    *,
    path: str,
    line_start: int,
    result_type: str,
    result_variable: str,
    output_field: str,
    contract_field: str,
    supporting: Iterable[str],
) -> dict[str, Any]:
    refs = [f"{path}:{line_start}", *[str(item) for item in supporting]]
    return {
        "source": "static-transfer-21-officer",
        "officer": "Engineer",
        "capability": "api_contract",
        "category": "api_contract",
        "severity": "blocker",
        "root_cause": "contract-result-field-discarded-by-adapter-default",
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": list(dict.fromkeys(refs)),
        "message": (
            "An adapter receives a populated contract result but replaces one of its "
            "declared fields with a hard-coded default at the final consumer boundary."
        ),
        "evidence": (
            f"`{result_variable}` has contract type `{result_type}` with field "
            f"`{contract_field}`, and sibling output fields are copied from that object, "
            f"but output field `{output_field}` is assigned a default constant instead. "
            "The cross-layer contract value is therefore lost before reaching consumers."
        ),
        "falsifiers_checked": [
            "Required a typed contract result returned by a Get/Read/Load/Fetch method in the same adapter region.",
            "Required the defaulted output field to match a declared field on that contract result type.",
            "Required at least two sibling output fields to be copied from the same result object.",
            "Excluded direct field forwarding, result types without the field, and isolated default initialization.",
        ],
        "verification_test": (
            f"Forward `{result_variable}.{contract_field}` into `{output_field}` and prove "
            "non-default flag/value combinations survive the complete contract-to-adapter path."
        ),
        "confidence": 0.99,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _adapter_default_findings(files: dict[str, str]) -> list[dict[str, Any]]:
    record_fields = _record_fields(files)
    if not record_fields:
        return []

    findings: list[dict[str, Any]] = []
    default_assignment = re.compile(
        r"\b(?P<target>[A-Za-z_][A-Za-z0-9_]*)->(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
        r"\s*=\s*(?P<value>0|false|null|default(?:\s*\([^;]*\))?)\s*;",
        re.I,
    )
    result_assignment = re.compile(
        r"\b(?P<type>(?:[A-Za-z_][A-Za-z0-9_]*\.)*[A-Za-z_][A-Za-z0-9_]*)"
        r"\s+(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
        r"[^;]{0,500}?\.(?:Get|Read|Load|Fetch)[A-Za-z0-9_]*\s*\([^;]*\)\s*;",
        re.S,
    )

    for path, text in files.items():
        if Path(path).suffix.lower() not in _CS_SUFFIXES:
            continue
        for default in default_assignment.finditer(text):
            window_start = max(0, default.start() - 2400)
            window_end = min(len(text), default.end() + 900)
            window = text[window_start:window_end]
            before_default = text[window_start:default.start()]
            candidates = list(result_assignment.finditer(before_default))
            if not candidates:
                continue
            result = candidates[-1]
            result_type = result.group("type").split(".")[-1]
            result_variable = result.group("var")
            declared = record_fields.get(result_type, set())
            if not declared:
                continue

            output_field = default.group("field")
            contract_field = next(
                (
                    field
                    for field in declared
                    if _normalize(field) == _normalize(output_field)
                ),
                None,
            )
            if contract_field is None:
                continue

            target = default.group("target")
            sibling = re.compile(
                rf"\b{re.escape(target)}->(?P<out>[A-Za-z_][A-Za-z0-9_]*)"
                rf"\s*=\s*[^;]{{0,240}}\b{re.escape(result_variable)}\."
                r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)\b[^;]*;",
                re.S,
            )
            sibling_rows = list(sibling.finditer(window))
            copied_fields = {
                row.group("field")
                for row in sibling_rows
                if _normalize(row.group("out")) != _normalize(output_field)
            }
            if len(copied_fields) < 2:
                continue

            result_line = _line(text, window_start + result.start())
            findings.append(
                _finding(
                    path=path,
                    line_start=_line(text, default.start()),
                    result_type=result_type,
                    result_variable=result_variable,
                    output_field=output_field,
                    contract_field=contract_field,
                    supporting=(f"{path}:{result_line}",),
                )
            )
    return findings


def run_static_transfer_21_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    files = {
        path: text
        for path in changed
        if Path(path).suffix.lower() in _CS_SUFFIXES
        and (text := _safe_text(root_path, path))
    }
    findings = _adapter_default_findings(files)

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[
            (
                str(finding.get("root_cause")),
                str(finding.get("path")),
                int(finding.get("line_start") or 0),
            )
        ] = finding

    return {
        "schema_version": "sergeant.static-transfer-21-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
    }
