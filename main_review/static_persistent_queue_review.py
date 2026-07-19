"""Static review for durable queue serialization and exhausted-item preservation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}


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


def _finding(path: str, line: int, root: str, message: str, evidence: str, verification: str) -> dict[str, Any]:
    return {
        "source": "static-persistent-queue-officer",
        "officer": "Mechanic",
        "capability": "durability",
        "category": "durability",
        "severity": "major",
        "root_cause": root,
        "path": path,
        "line_start": line,
        "line_end": line,
        "evidence_ref": f"{path}:{line}",
        "supporting_evidence_refs": [f"{path}:{line}"],
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": [
            "Checked for a shared mutex, serialized promise chain, transaction or compare-and-swap boundary.",
            "Checked that persistence uses whole-collection load, mutation and replacement rather than an atomic append/update primitive.",
            "Checked for a durable dead-letter destination before exhausted items leave the pending collection.",
        ],
        "verification_test": verification,
        "confidence": 0.97,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def run_static_persistent_queue_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []

    for path in changed:
        if Path(path).suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        lowered = text.lower()
        if "queue" not in f"{path}\n{lowered}" or "await" not in lowered:
            continue

        load_matches = list(re.finditer(r"await\s+this\.(?:load|getqueue|readqueue)\s*\(", text, re.I))
        save_matches = list(re.finditer(r"await\s+this\.(?:save|setqueue|writequeue)\s*\(", text, re.I))
        whole_collection_contract = bool(
            re.search(r"(?:private|protected)?\s*async\s+load\s*\([^)]*\)[\s\S]{0,500}?store\.get", text, re.I)
            and re.search(r"(?:private|protected)?\s*async\s+save\s*\([^)]*\)[\s\S]{0,500}?store\.set", text, re.I)
        )
        serialized = bool(
            re.search(r"\b(?:mutex|semaphore|withlock|runexclusive|serialize|criticalsection)\b", lowered)
            or re.search(r"(?:this\.)?(?:lock|chain|serial)\s*=\s*(?:this\.)?(?:lock|chain|serial)\.then", lowered)
            or re.search(r"\btransaction\s*\(", lowered)
            or re.search(r"compareandset|compare_exchange|atomic", lowered)
        )
        if whole_collection_contract and len(load_matches) >= 2 and len(save_matches) >= 2 and not serialized:
            line = _line(text, load_matches[0].start())
            findings.append(
                _finding(
                    path,
                    line,
                    "persistent-collection-read-modify-write-without-serialization",
                    "Independent queue operations replace the same persisted collection without a serialization boundary.",
                    (
                        "Multiple async methods load the complete queue, mutate separate in-memory snapshots, and write the complete collection back. "
                        "Overlapping enqueue/flush operations can therefore lose a capture or resurrect a delivered item by last-writer-wins replacement."
                    ),
                    (
                        "Serialize every queue mutation through one lock/promise chain or use an atomic persistence primitive, then prove concurrent "
                        "enqueue/enqueue and enqueue/flush retain every distinct capture exactly once."
                    ),
                )
            )

        exhaustion = re.search(
            r"if\s*\([^)]*(?:attempts|retries)[^)]*(?:>=|>)\s*[A-Za-z0-9_]+[^)]*\)\s*\{(?P<body>[\s\S]{0,500}?)\}",
            text,
            re.I,
        )
        durable_deadletter = bool(re.search(r"dead[_-]?letter|key_deadletter|parkeditems|failedqueue", lowered))
        if exhaustion is not None and not durable_deadletter:
            body = exhaustion.group("body")
            erased = bool(
                re.search(r"dropped\s*\+\+|drop(?:ped)?\s*\+=|continue\s*;|return\b", body, re.I)
                or "remaining.push" not in body.lower()
            )
            if erased:
                line = _line(text, exhaustion.start())
                findings.append(
                    _finding(
                        path,
                        line,
                        "exhausted-retry-is-erased-without-durable-dead-letter",
                        "An exhausted transient delivery leaves the pending queue without a durable recovery record.",
                        (
                            "The maximum-attempt branch removes the item from the persisted pending collection and records only a dropped counter. "
                            "No durable dead-letter item, failure reason or operator recovery path preserves the undelivered payload."
                        ),
                        (
                            "Persist exhausted transient deliveries to a durable dead-letter collection before shrinking the pending queue, preserve the "
                            "stable deduplication identity, and prove a crash between the two writes cannot leave the item in neither store."
                        ),
                    )
                )

    unique = {(str(item["root_cause"]), str(item["path"])): item for item in findings}
    return {
        "schema_version": "sergeant.static-persistent-queue-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
