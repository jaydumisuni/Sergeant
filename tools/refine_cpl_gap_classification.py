from __future__ import annotations

from pathlib import Path

path = Path("main_review/finding_adjudication.py")
text = path.read_text(encoding="utf-8")

old = '''CONFIDENCE_GAP_TYPES = {"failed_member", "disagreement", "unanswered_question"}

_SECURITY_CATEGORIES'''
new = '''CONFIDENCE_GAP_TYPES = {"failed_member", "disagreement"}
_REQUIRED_ASSURANCE_WORDS = {
    "authorization",
    "credential",
    "evidence",
    "permission",
    "proof",
    "required",
    "runtime",
    "security",
    "test",
    "verification",
    "verify",
}

_SECURITY_CATEGORIES'''
assert old in text, "gap constant anchor changed"
text = text.replace(old, new, 1)

old = '''        if gap_type in VERDICT_GAP_TYPES:
            verdict_gaps.append(gap)
        elif gap_type in CONFIDENCE_GAP_TYPES:
            confidence_gaps.append(gap)
        else:
            informational_gaps.append(gap)
'''
new = '''        reason = str(gap.get("reason") or "").lower()
        required_assurance = bool(set(re.findall(r"[a-z_][a-z0-9_]+", reason)) & _REQUIRED_ASSURANCE_WORDS)
        if gap_type in VERDICT_GAP_TYPES or (gap_type == "unanswered_question" and required_assurance):
            verdict_gaps.append(gap)
        elif gap_type in CONFIDENCE_GAP_TYPES or gap_type == "unanswered_question":
            confidence_gaps.append(gap)
        else:
            informational_gaps.append(gap)
'''
assert old in text, "gap classification anchor changed"
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

path = Path("tests/test_cpl_finding_adjudication.py")
text = path.read_text(encoding="utf-8")
old = '''    assert [item["type"] for item in result["verdict_gaps"]] == ["independent_confirmation"]


def _settings()'''
new = '''    assert [item["type"] for item in result["verdict_gaps"]] == ["independent_confirmation"]


def test_required_runtime_proof_question_remains_a_verdict_gap() -> None:
    result = classify_council_gaps([
        {"type": "unanswered_question", "reason": "Runtime proof for the changed branch is missing."},
    ])

    assert result["confidence_gaps"] == []
    assert result["verdict_gaps"][0]["type"] == "unanswered_question"


def _settings()'''
assert old in text, "test anchor changed"
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")

path = Path("docs/29-cpl-finding-adjudication.md")
text = path.read_text(encoding="utf-8")
old = '''- a low-risk question remains unanswered.

Confidence-only gaps reduce confidence'''
new = '''- a low-risk question remains unanswered.

An unanswered question remains verdict-affecting when it explicitly identifies missing required evidence, runtime proof, verification, tests, security, authorization, permission, credential, or equivalent assurance.

Confidence-only gaps reduce confidence'''
assert old in text, "documentation anchor changed"
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
