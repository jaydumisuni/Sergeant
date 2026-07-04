from __future__ import annotations

from main_review.decision_workspace import build_decision_workspace


def test_decision_workspace_maps_review_outcomes() -> None:
    payload = build_decision_workspace(
        [
            {"source": "coderabbit", "body": "real issue", "classification": "correct"},
            {"source": "qodo", "body": "maybe", "classification": "suggestion"},
            {"source": "human", "body": "style only", "classification": "reject"},
            {"source": "reviewdog", "body": "remember this", "classification": "save_pattern"},
        ]
    )

    assert payload["summary"]["fix"] == 1
    assert payload["summary"]["consider"] == 1
    assert payload["summary"]["reject"] == 1
    assert payload["summary"]["save_pattern"] == 1
    assert len(payload["ready_for_memory"]) == 2
