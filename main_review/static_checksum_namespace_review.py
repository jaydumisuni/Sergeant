"""Static checks for portable checksum-manifest path namespaces."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from .python_runtime_scan_text import python_runtime_scan_text

_TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".go",
    ".sh",
    ".bash",
    ".yml",
    ".yaml",
}
_PRODUCER_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go"}
_CHECKSUM_CONTEXT_RE = re.compile(r"(?:SHA256SUMS|sha256|checksum(?:s|_manifest| manifest)?)", re.I)
_BARE_NAME_RE = re.compile(
    r"(?:\[['\"]filename['\"]\]|\.filename\b|\.name\b|(?:os\.path\.basename|path\.basename|filepath\.Base)\s*\()",
    re.I,
)
_EXPLICIT_RELATIVE_RE = re.compile(
    r"(?:\[['\"]relative_path['\"]\]|\.relative_path\b|\.relativePath\b|\brelative_path\b|\brelativePath\b|relative_to\s*\(|filepath\.Rel\s*\(|path\.relative\s*\()",
    re.I,
)
_CWD_RE = re.compile(r"(?:Path\.cwd\s*\(\s*\)|os\.getcwd\s*\(\s*\)|process\.cwd\s*\(\s*\)|Deno\.cwd\s*\(\s*\))")
_EXPLICIT_MANIFEST_BASE_RE = re.compile(
    r"(?:manifest[^\n]{0,100}(?:\.parent|dirname\s*\()|(?:bundle|final|release|export|dist)[_-]?root)",
    re.I,
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


def _finding(
    *,
    root_cause: str,
    path: str,
    line_start: int,
    message: str,
    evidence: str,
    supporting: Iterable[str],
    falsifiers: Iterable[str],
    verification: str,
) -> dict[str, Any]:
    return {
        "source": "static-checksum-namespace-officer",
        "officer": "Mechanic",
        "capability": "integrity",
        "category": "integrity",
        "severity": "major",
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": sorted(set(supporting)),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": 0.98,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _producer_invoked_with_nested_artifact(
    producer_path: str,
    texts: Mapping[str, str],
) -> tuple[str, int] | None:
    """Return workflow evidence when producer/verifier share a root with nested artifacts."""

    producer_name = Path(producer_path).name
    for workflow_path, workflow in texts.items():
        if Path(workflow_path).suffix.lower() not in {".yml", ".yaml", ".sh", ".bash"}:
            continue
        if producer_path not in workflow and producer_name not in workflow:
            continue
        for output_arg in re.finditer(
            r"--output-dir\s+[\"']?\$(?:\{)?(?P<var>[A-Za-z_][A-Za-z0-9_]*)\}?[\"']?",
            workflow,
        ):
            variable = output_arg.group("var")
            variable_ref = rf"\$(?:\{{)?{re.escape(variable)}\}}?"
            nested = re.search(
                rf"{variable_ref}/[^\s\"']+/[^\s\"']+",
                workflow,
            )
            verifier_root = re.search(
                rf"\bcd\s+[\"']?{variable_ref}[\"']?",
                workflow,
            )
            verifier = re.search(
                r"(?:sha256sum|shasum)[^\n]{0,160}(?:-c|--check)[^\n]{0,160}SHA256SUMS",
                workflow,
                re.I,
            )
            if nested is not None and verifier_root is not None and verifier is not None:
                return workflow_path, _line(workflow, nested.start())
    return None


def _bare_checksum_producer_findings(
    path: str,
    text: str,
    texts: Mapping[str, str],
) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _PRODUCER_SUFFIXES:
        return []
    if "SHA256SUMS" not in text:
        return []

    layout = _producer_invoked_with_nested_artifact(path, texts)
    if layout is None:
        return []
    workflow_path, workflow_line = layout

    for sink in re.finditer(r"SHA256SUMS", text):
        window_start = max(0, sink.start() - 1000)
        window_end = min(len(text), sink.end() + 300)
        window = text[window_start:window_end]
        sink_local = sink.start() - window_start
        candidates = [
            (abs(match.start() - sink_local), "bare", match)
            for match in _BARE_NAME_RE.finditer(window)
        ]
        candidates.extend(
            (abs(match.start() - sink_local), "relative", match)
            for match in _EXPLICIT_RELATIVE_RE.finditer(window)
        )
        if not candidates:
            continue
        _, namespace_kind, namespace_match = min(candidates, key=lambda item: item[0])
        if namespace_kind != "bare":
            continue
        bare_offset = window_start + namespace_match.start()
        line = _line(text, bare_offset)
        return [
            _finding(
                root_cause="checksum-manifest-drops-relative-directory",
                path=path,
                line_start=line,
                message="A checksum manifest records only a basename even though the verified artifact is below the verifier root.",
                evidence=(
                    "The checksum producer formats a bare filename/basename into SHA256SUMS. The changed execution path invokes this producer "
                    "with an artifact nested below its declared output root, then verifies SHA256SUMS from that output root. The manifest entry "
                    "therefore loses the relative directory that the verifier needs to locate the shipped artifact."
                ),
                supporting=(f"{path}:{line}", f"{workflow_path}:{workflow_line}"),
                falsifiers=(
                    "Checked that the producer writes SHA256SUMS rather than unrelated display metadata.",
                    "Checked that the same changed execution path invokes the producer with an artifact below the declared output root.",
                    "Checked that checksum verification runs from that output root.",
                    "Checked that the checksum record does not already carry an explicit relative path.",
                    "A basename-only record remains valid when the artifact is actually colocated with the manifest; that layout is not flagged.",
                ),
                verification=(
                    "Record the artifact path relative to the verifier's explicit portable base (for example `bin/tool` relative to the final "
                    "output root), then verify SHA256SUMS from that same base."
                ),
            )
        ]
    return []


def _cwd_consumer_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _PRODUCER_SUFFIXES:
        return []
    if _CHECKSUM_CONTEXT_RE.search(text) is None:
        return []
    for cwd in _CWD_RE.finditer(text):
        window = text[max(0, cwd.start() - 500) : min(len(text), cwd.end() + 500)]
        if _CHECKSUM_CONTEXT_RE.search(window) is None:
            continue
        if _EXPLICIT_MANIFEST_BASE_RE.search(window) is not None:
            continue
        line = _line(text, cwd.start())
        return [
            _finding(
                root_cause="checksum-manifest-resolved-from-process-cwd",
                path=path,
                line_start=line,
                message="Checksum-manifest entries are resolved from process CWD instead of an explicit portable manifest base.",
                evidence=(
                    "The checksum path uses the process working directory while handling integrity-manifest data. That makes the same manifest "
                    "resolve to different artifacts when the verifier starts from a different directory."
                ),
                supporting=(f"{path}:{line}",),
                falsifiers=(
                    "Checked for checksum/integrity-manifest context around the CWD-based path resolution.",
                    "Checked for an explicit manifest-directory or final bundle/export/release root in the same resolution path.",
                    "A verifier anchored to the manifest's own directory or another explicit portable base is not flagged.",
                ),
                verification=(
                    "Resolve every relative manifest entry against the manifest directory or another explicit final portable root, reject absolute "
                    "and traversal entries, and prove verification succeeds from a different process working directory."
                ),
            )
        ]
    return []


def run_static_checksum_namespace_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    texts: dict[str, str] = {}
    for path in changed:
        if Path(path).suffix.lower() not in _TEXT_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if text:
            texts[path] = text

    findings: list[dict[str, Any]] = []
    for path, text in texts.items():
        scan_text = python_runtime_scan_text(text) if Path(path).suffix.lower() == ".py" else text
        findings.extend(_bare_checksum_producer_findings(path, scan_text, texts))
        findings.extend(_cwd_consumer_findings(path, scan_text))

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[(str(finding["root_cause"]), str(finding["path"]), int(finding["line_start"]))] = finding

    return {
        "schema_version": "sergeant.static-checksum-namespace-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": sorted(texts),
        "executed_project_code": False,
    }
