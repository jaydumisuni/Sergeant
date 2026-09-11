from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION_TEST = "tests/test_sae_r2_qualification_campaign.py"


def _workflow(name: str) -> str:
    return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")


def test_r2_workflow_triggers_on_and_executes_qualification_campaign():
    text = _workflow("sae-r2-rust-proof.yml")
    assert text.count(QUALIFICATION_TEST) >= 3  # pull trigger + push trigger + pytest command


def test_general_sae_rust_workflow_does_not_leave_r2_qualification_unproved_when_it_is_triggered():
    text = _workflow("sae-rust-proof.yml")
    assert text.count(QUALIFICATION_TEST) >= 3  # pull trigger + push trigger + pytest command
