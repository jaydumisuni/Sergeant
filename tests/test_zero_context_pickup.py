from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PICKUP = ROOT / "PICKUP.md"
AGENTS = ROOT / "AGENTS.md"
AI_START = ROOT / "AI_START_HERE.md"


def assert_in_order(text: str, *markers: str) -> None:
    """Require each recovery marker to appear after the previous marker."""
    positions = [text.index(marker) for marker in markers]
    assert positions == sorted(positions)


def test_zero_context_pickup_preserves_current_authority() -> None:
    """Keep stable Sergeant authority and project-driven learning boundaries intact."""
    text = PICKUP.read_text(encoding="utf-8")

    assert "model-free by default" in text
    assert "10-for-2 / tenfold doctrine has two linked meanings" in text
    assert "Twenty privates is the minimum" in text
    assert "dependency-frontier execution" in text
    assert "Hermes transports orders" in text
    assert "Automatic lesson promotion and automatic merge remain forbidden" in text
    assert "project-driven continuous learning" in text
    assert "calendar-based Week 2" in text
    assert "treat current GitHub truth as authoritative" in text


def test_zero_context_pickup_tracks_final_pr159_learning_disposition() -> None:
    """Recover the accepted checksum lesson and rejected credential proposal without ambiguity."""
    text = PICKUP.read_text(encoding="utf-8")
    learning_section = text[
        text.index("## Current learning state") :
        text.index("## PR #159 campaign state")
    ]

    assert "TechGuyCheckm8 checksum path-namespace lesson" in learning_section
    assert "permanently accepted" in learning_section
    assert ".github/self-learning/lessons/tgcheckm8-checksum-path-namespace-20260723.json" in learning_section
    assert "84faf9644b323792e1afd565fd4e65b653f668ee" in learning_section
    assert "learn-tgcheckm8-checkout-credential-boundary-20260723" in learning_section
    assert "is **rejected**" in learning_section
    assert "has no accepted-lesson record" in learning_section
    assert "checksum path namespace → accepted lesson" in learning_section
    assert "checkout credential boundary → rejected / no promotion" in learning_section


def test_zero_context_pickup_tracks_pr159_merge_boundary() -> None:
    """Keep lesson acceptance separate from the implementation PR merge decision."""
    text = PICKUP.read_text(encoding="utf-8")
    campaign_section = text[
        text.index("## PR #159 campaign state") :
        text.index("## External donor state")
    ]

    assert "implementation/review vehicle" in campaign_section
    assert "current `main` is an ancestor of the PR head" in campaign_section
    assert "all applicable review threads are resolved or explicitly dispositioned" in campaign_section
    assert "merge occurs only under explicit owner instruction" in campaign_section
    assert "Any branch movement invalidates the previous exact-head merge proof" in campaign_section


def test_agent_and_ai_entrypoints_require_ordered_live_pickup_recovery() -> None:
    """Require entrypoints to recover static authority before newer live GitHub state."""
    agents = AGENTS.read_text(encoding="utf-8")
    start = AI_START.read_text(encoding="utf-8")

    assert "PICKUP.md" in agents
    assert "live GitHub" in agents
    assert "PICKUP.md" in start
    assert "current `main` head" in start
    assert "open pull requests" in start
    assert_in_order(
        start,
        "`README.md`",
        "`AGENTS.md`",
        "`PICKUP.md`",
        "specific authority files",
        "Live GitHub state",
    )
