from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_MEMORY = ROOT / "AGENTS.md"
CLAUDE_MEMORY = ROOT / "CLAUDE.md"
COPILOT_MEMORY = ROOT / ".github" / "copilot-instructions.md"
EXTERNAL_POLICY = ROOT / "docs" / "EXTERNAL_REPOSITORY_LEARNING_POLICY.md"


def test_tenfold_method_preserves_both_valid_meanings() -> None:
    memory = AGENT_MEMORY.read_text(encoding="utf-8")

    assert "two distinct, valid meanings" in memory
    assert "Assistant execution method" in memory
    assert "Sergeant internal force doctrine" in memory
    assert "one coordinating lead" in memory
    assert "split the work across parallel specialist roles" in memory
    assert "normally justified human-equivalent workers × 10" in memory
    assert "2 workers → 20 privates" in memory
    assert "5 workers → 50 privates" in memory
    assert "Hermes transports orders and evidence" in memory
    assert "Twenty is the minimum machine-scale formation" in memory


def test_agent_memory_uses_context_instead_of_erasing_a_meaning() -> None:
    memory = AGENT_MEMORY.read_text(encoding="utf-8")

    assert "The user's exact wording and current context define which meaning is active" in memory
    assert "assistant execution method" in memory
    assert "Sergeant force doctrine" in memory
    assert "A request may intentionally invoke both" in memory
    assert "Do not collapse a dual-context instruction into only one meaning again" in memory


def test_external_repository_activity_is_governed_candidate_learning() -> None:
    memory = AGENT_MEMORY.read_text(encoding="utf-8")
    policy = EXTERNAL_POLICY.read_text(encoding="utf-8")

    for text in (memory, policy):
        assert "external" in text.lower()
        assert "candidate" in text.lower()
        assert "provenance" in text.lower()
        assert "blind" in text.lower()
        assert "negative controls" in text.lower()
        assert "transfer" in text.lower()
        assert "Sergeant-owned" in text

    assert "GitHub notification" in memory
    assert "does **not** become knowledge automatically" in memory
    assert "rejected lessons" in memory


def test_major_agent_entry_points_share_the_dual_memory() -> None:
    claude = CLAUDE_MEMORY.read_text(encoding="utf-8")
    copilot = COPILOT_MEMORY.read_text(encoding="utf-8")

    assert "[`AGENTS.md`](AGENTS.md)" in claude
    assert "[`AGENTS.md`](../AGENTS.md)" in copilot
    for text in (claude, copilot):
        assert "two valid meanings" in text
        assert "Assistant execution" in text or "assistant execution" in text
        assert "Sergeant" in text
        assert "20 privates" in text
        assert "other repositories" in text or "repositories outside Sergeant" in text
        assert "candidate" in text
        assert "blind" in text
