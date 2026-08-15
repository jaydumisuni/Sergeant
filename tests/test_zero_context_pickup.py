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
    assert "Hermes transports orders" in text
    assert "Automatic lesson promotion and automatic merge remain forbidden" in text
    assert "project-driven continuous learning" in text
    assert "Do not start a calendar-based Week 2" in text
    assert "treat current GitHub truth as authoritative" in text


def test_zero_context_pickup_tracks_candidate_ready_work_without_promoting_it() -> None:
    """Keep candidate-ready TechGuyCheckm8 lineages scoped as unpromoted work."""
    text = PICKUP.read_text(encoding="utf-8")
    candidate_section = text[
        text.index("Two additional TechGuyCheckm8 repaired defect lineages") :
        text.index("Authoritative candidate records:")
    ]

    assert "learn-tgcheckm8-checkout-credential-boundary-20260723" in candidate_section
    assert "learn-tgcheckm8-checksum-path-namespace-20260723" in candidate_section
    assert "These two records are not accepted lessons" in candidate_section
    assert "frozen blind Sergeant review" in candidate_section
    assert "Teacher / Prosecutor / Defender" in candidate_section
    assert "hidden holdout" in candidate_section
    assert "owner-controlled promotion proposal" in candidate_section


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
