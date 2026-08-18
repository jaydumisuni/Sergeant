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
    assert "learn-oracle-oidc-workflow-identity-20260817" in learning_section
    assert "rejected for lesson promotion" in learning_section
    assert "No accepted lesson file exists for this case" in learning_section


def test_zero_context_pickup_tracks_merged_pr159_authority() -> None:
    """Keep the completed PR159 learning campaign bound to its exact merged authority."""
    text = PICKUP.read_text(encoding="utf-8")
    campaign_section = text[
        text.index("## PR #159 campaign state") :
        text.index("## PR #165 campaign state")
    ]

    assert "is **merged and complete**" in campaign_section
    assert "7a1a5b1fad564d39ae67864505a5f086d94687c1" in campaign_section
    assert "9f653412cd056119aa2231ac4a6b5d3f8c53c03b" in campaign_section
    assert "two-parent merge commit" in campaign_section
    assert "fresh Main Review and Final Static Transfer Holdout" in campaign_section
    assert "CodeRabbit was green" in campaign_section
    assert "Do not reopen or duplicate it" in campaign_section


def test_zero_context_pickup_tracks_merged_pr165_rejection_authority() -> None:
    """Recover the completed Oracle council and its rejected lesson without replaying it."""
    text = PICKUP.read_text(encoding="utf-8")
    campaign_section = text[
        text.index("## PR #165 campaign state") :
        text.index("## External donor state")
    ]

    assert "is **merged and complete**" in campaign_section
    assert "b7b3be4ca9acf3c2f853ad03758e18131a69895b" in campaign_section
    assert "5753c5d1cff953c4591d009cc819c3eca661b56c" in campaign_section
    assert "kratos-HP-290-G4-Microtower-PC" in campaign_section
    assert "15 hashed files" in campaign_section
    assert "zero automatic promotions" in campaign_section
    assert "Sergeant rejected the proposal" in campaign_section
    assert "Do not create an accepted lesson" in campaign_section


def test_zero_context_pickup_moves_next_work_beyond_completed_campaigns() -> None:
    """Require new provenance-complete evidence instead of replaying PR159 or PR165."""
    text = PICKUP.read_text(encoding="utf-8")
    next_section = text[
        text.index("## Next valid work") :
        text.index("## Completion boundary")
    ]

    assert "new provenance-complete THETECHGUY engineering fixes" in next_section
    assert "verify defective ref + fixing ref + scored production paths" in next_section
    assert "Teacher / Prosecutor / Defender" in next_section
    assert "owner-controlled promotion proposal" in next_section
    assert "rejected PR #159 credential proposal" in next_section
    assert "rejected PR #165 Oracle proposal" in next_section
    assert "do not duplicate the accepted checksum lesson" in next_section


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
