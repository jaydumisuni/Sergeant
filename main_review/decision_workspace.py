"""Decision workspace for classified review comments.

The workspace turns reviewer comments into explicit decisions so Main Review can
explain what was fixed, rejected, considered, or saved as a pattern.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Decision = Literal["fix", "consider", "reject", "save_pattern", "needs_classification"]

CLASSIFICATION_TO_DECISION: dict[str, Decision] = {
    "correct": "fix",
    "suggestion": "consider",
    "reject": "reject",
    "save_pattern": "save_pattern",
    "unclassified": "needs_classification",
}


@dataclass(frozen=True)
class DecisionRecord:
    source: str
    body: str
    decision: Decision
    reason: str
    path: str | None = None
    line: int | None = None
    evidence: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    memory_candidate: bool = False
    confidence: float = 0.5

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_decision_workspace(comments: list[dict[str, object]]) -> dict[str, object]:
    decisions: list[DecisionRecord] = []
    for comment in comments:
        classification = str(comment.get("classification", "unclassified"))
        decision = CLASSIFICATION_TO_DECISION.get(classification, "needs_classification")
        body = str(comment.get("body", "")).strip()
        source = str(comment.get("source", "external-review"))
        reason = str(comment.get("reason", "")).strip()
        tags = [str(tag) for tag in comment.get("tags", [])] if isinstance(comment.get("tags", []), list) else []
        evidence = [str(item) for item in comment.get("evidence", [])] if isinstance(comment.get("evidence", []), list) else []
        if not reason:
            reason = {
                "fix": "Comment is classified as correct and should be fixed or tracked.",
                "consider": "Comment is useful but must be compared against architecture before action.",
                "reject": "Comment is classified as rejected and should not change implementation.",
                "save_pattern": "Comment should become reusable review knowledge.",
                "needs_classification": "Comment needs human or reviewer classification before action.",
            }[decision]
        decisions.append(
            DecisionRecord(
                source=source,
                body=body,
                decision=decision,
                reason=reason,
                path=str(comment.get("path")) if comment.get("path") else None,
                line=int(comment["line"]) if comment.get("line") not in {None, ""} else None,
                evidence=evidence,
                tags=tags,
                memory_candidate=decision in {"fix", "save_pattern"},
                confidence={"fix": 0.75, "consider": 0.55, "reject": 0.7, "save_pattern": 0.65, "needs_classification": 0.2}[decision],
            )
        )

    counts: dict[str, int] = {"fix": 0, "consider": 0, "reject": 0, "save_pattern": 0, "needs_classification": 0}
    for decision in decisions:
        counts[decision.decision] += 1

    return {
        "summary": {"total": len(decisions), **counts},
        "decisions": [decision.to_dict() for decision in decisions],
        "ready_for_memory": [decision.to_dict() for decision in decisions if decision.memory_candidate],
    }
