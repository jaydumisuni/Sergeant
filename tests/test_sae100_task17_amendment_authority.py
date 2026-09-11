from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-09-07-sae-30-through-100.md"


def test_task17_amendment_preserves_frozen_predecessors_and_requires_non_mutating_successor_seams():
    text = PLAN.read_text(encoding="utf-8")
    task17 = text.split("### Task 17:", 1)[1].split("### Task 18:", 1)[0]
    assert "Preserve unchanged (frozen predecessor)" in task17
    assert "main_review/officer_council.py" in task17
    assert "main_review/judge_assurance_adapter.py" in task17
    assert "main_review/final_proof.py" in task17
    assert "successor/non-mutating integration seams" in task17
    assert "must not alter the frozen blobs" in task17


def test_task17_amendment_keeps_original_authority_boundaries():
    text = PLAN.read_text(encoding="utf-8")
    task17 = text.split("### Task 17:", 1)[1].split("### Task 18:", 1)[0]
    assert "Sergeant remains final engineering-verdict owner" in task17
    assert "Output mode before Genesis Exit is only `SHADOW_OR_QUALIFICATION_ONLY`" in task17
    assert "assurance result cannot replace normal verdict before Genesis Exit" in task17
