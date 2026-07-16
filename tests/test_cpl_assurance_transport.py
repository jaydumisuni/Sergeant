from __future__ import annotations

import json

from main_review.cpl_council import assess


def _pass_with_questions(*questions: object) -> dict[str, object]:
    return {
        "specialist": "generalist",
        "verdict": "PASS",
        "findings": [],
        "unanswered_questions": list(questions),
    }


def test_standard_json_question_preserves_required_assurance() -> None:
    encoded = json.dumps({
        "question": "Is runtime authorization proof available?",
        "required_assurance": True,
        "optional_context": None,
    })

    gaps = assess([_pass_with_questions(encoded)], [], [], 1)

    assert gaps[0]["type"] == "unanswered_question"
    assert gaps[0]["reason"] == "Is runtime authorization proof available?"
    assert gaps[0]["required_assurance"] is True


def test_required_assurance_true_wins_for_duplicate_question_text() -> None:
    question = "Is runtime authorization proof available?"
    passes = [
        _pass_with_questions({"question": question, "required_assurance": False}),
        _pass_with_questions({"question": question, "required_assurance": True}),
    ]

    gaps = assess(passes, [], [], 2)
    matching = [gap for gap in gaps if gap.get("reason") == question]

    assert len(matching) == 1
    assert matching[0]["required_assurance"] is True
