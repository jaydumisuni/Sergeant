"""External review ingestion foundation.

This module turns external reviewer comments into structured learning items.
It does not call GitHub directly in v1. It normalizes exported/copied comments
so CodeRabbit/Qodo/etc. feedback can be classified and converted into memory.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

Classification = Literal["correct", "suggestion", "reject", "save_pattern", "unclassified"]

CLASSIFICATION_ALIASES = {
    "green": "correct",
    "correct": "correct",
    "fix": "correct",
    "yellow": "suggestion",
    "suggestion": "suggestion",
    "consider": "suggestion",
    "red": "reject",
    "reject": "reject",
    "no": "reject",
    "brain": "save_pattern",
    "pattern": "save_pattern",
    "save": "save_pattern",
    "learn": "save_pattern",
}


@dataclass(frozen=True)
class ExternalReviewComment:
    source: str
    body: str
    repository: str = ""
    pr_number: int | None = None
    path: str | None = None
    line: int | None = None
    author: str | None = None
    url: str | None = None
    classification: Classification = "unclassified"
    reason: str = ""
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class IngestionSummary:
    total: int
    correct: int
    suggestion: int
    reject: int
    save_pattern: int
    unclassified: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def normalize_classification(value: str | None) -> Classification:
    if not value:
        return "unclassified"
    normalized = value.strip().lower().replace(" ", "_").replace("🟢", "green").replace("🟡", "yellow").replace("🔴", "red").replace("🧠", "brain")
    return CLASSIFICATION_ALIASES.get(normalized, "unclassified")  # type: ignore[return-value]


def load_external_comments(path: str | Path) -> list[ExternalReviewComment]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_comments = payload.get("comments", payload if isinstance(payload, list) else [])
    comments: list[ExternalReviewComment] = []
    for item in raw_comments:
        comments.append(
            ExternalReviewComment(
                source=str(item.get("source", "external-review")),
                body=str(item.get("body", "")).strip(),
                repository=str(item.get("repository", "")),
                pr_number=item.get("pr_number"),
                path=item.get("path"),
                line=item.get("line"),
                author=item.get("author"),
                url=item.get("url"),
                classification=normalize_classification(item.get("classification")),
                reason=str(item.get("reason", "")),
                tags=list(item.get("tags", [])),
            )
        )
    return comments


def summarize_comments(comments: list[ExternalReviewComment]) -> IngestionSummary:
    counts = {"correct": 0, "suggestion": 0, "reject": 0, "save_pattern": 0, "unclassified": 0}
    for comment in comments:
        counts[comment.classification] += 1
    return IngestionSummary(total=len(comments), **counts)


def export_learning_candidates(comments: list[ExternalReviewComment]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for comment in comments:
        if comment.classification not in {"correct", "save_pattern"}:
            continue
        title_seed = comment.body.splitlines()[0][:80] if comment.body else "External review pattern"
        candidates.append(
            {
                "kind": "lesson" if comment.classification == "correct" else "principle",
                "title": f"External review: {title_seed}",
                "summary": comment.body,
                "reason": comment.reason or "External reviewer signal survived classification and should be considered for Main Review learning.",
                "status": "proposed",
                "evidence": [comment.url] if comment.url else [],
                "tags": sorted(set(["external-review", comment.source, *comment.tags])),
                "applies_to": [comment.path] if comment.path else [],
                "confidence": 0.7 if comment.classification == "correct" else 0.6,
            }
        )
    return candidates


def ingest_external_review_file(path: str | Path) -> dict[str, object]:
    comments = load_external_comments(path)
    return {
        "summary": summarize_comments(comments).to_dict(),
        "comments": [comment.to_dict() for comment in comments],
        "learning_candidates": export_learning_candidates(comments),
    }
