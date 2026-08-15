from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PICKUP = ROOT / "PICKUP.md"
AGENTS = ROOT / "AGENTS.md"
README = ROOT / "README.md"


def test_zero_context_pickup_preserves_current_authority() -> None:
    text = PICKUP.read_text(encoding="utf-8")

    assert "model-free by default" in text
    assert "10-for-2 / tenfold doctrine has two linked meanings" in text
    assert "Twenty privates is the minimum" in text
    assert "Hermes transports orders" in text
    assert "Automatic lesson promotion and automatic merge remain forbidden" in text
    assert "project-driven continuous learning" in text
    assert "Do not start a calendar-based Week 2" in text


def test_zero_context_pickup_tracks_candidate_ready_work_without_promoting_it() -> None:
    text = PICKUP.read_text(encoding="utf-8")

    assert "learn-tgcheckm8-checkout-credential-boundary-20260723" in text
    assert "learn-tgcheckm8-checksum-path-namespace-20260723" in text
    assert "These two records are not accepted lessons" in text
    assert "frozen blind Sergeant review" in text
    assert "Teacher / Prosecutor / Defender" in text
    assert "hidden holdout" in text
    assert "owner-controlled promotion proposal" in text


def test_agent_and_readme_entrypoints_require_pickup_recovery() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    assert "PICKUP.md" in agents
    assert "PICKUP.md" in readme
    assert "live GitHub" in agents
