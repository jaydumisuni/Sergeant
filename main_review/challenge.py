"""Challenge mode for Main Review.

Challenge mode tries to weaken the reviewer's own conclusion before the final
verdict is trusted.
"""

from __future__ import annotations

from typing import Any


def run_challenge_mode(review_payload: dict[str, Any]) -> dict[str, Any]:
    verdict = review_payload.get("verdict", {}) if isinstance(review_payload, dict) else {}
    evidence = review_payload.get("evidence", {}) if isinstance(review_payload, dict) else {}
    findings = evidence.get("findings", []) if isinstance(evidence, dict) else []
    verdict_value = verdict.get("verdict") if isinstance(verdict, dict) else None

    challenges: list[dict[str, object]] = []
    if verdict_value == "PASS" and findings:
        challenges.append(
            {
                "question": "PASS includes findings. Are they truly non-blocking?",
                "risk": "Minor findings may hide architecture or proof gaps if not reviewed.",
                "result": "accepted_if_minor_only",
            }
        )
    if verdict_value == "PASS" and not findings:
        challenges.append(
            {
                "question": "No findings found. Did evidence providers cover the changed surface?",
                "risk": "A clean report is only as strong as the evidence providers used.",
                "result": "requires_scope_check",
            }
        )
    if verdict_value in {"NEEDS WORK", "BLOCK"}:
        challenges.append(
            {
                "question": "Can the finding be reproduced from evidence?",
                "risk": "The reviewer must not block on vague or unsupported claims.",
                "result": "requires_evidence_trace",
            }
        )

    confidence = 0.9 if verdict_value == "PASS" and not findings else 0.65
    return {
        "challenged": True,
        "original_verdict": verdict_value,
        "confidence_after_challenge": confidence,
        "challenges": challenges,
        "trusted": verdict_value == "PASS" and confidence >= 0.65,
    }
