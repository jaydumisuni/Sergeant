from __future__ import annotations

from main_review.assurance_integration import SHADOW_MODE, compile_assurance_frontier, run_shadow_assurance


def _campaign():
    return compile_assurance_frontier(
        {"authority_owner": "Sergeant", "open_assurance_frontier": ["contract-a", "obligation-b"]},
        {"qualified": True},
        {"judge_admission_required": True},
        {"qualified": True},
        {"qualified": True},
        {"challenger_owned": True},
    )


def test_shadow_mode_preserves_normal_sergeant_authority():
    campaign = _campaign()
    result = run_shadow_assurance(campaign, lambda _c: {"admissible": True, "status": "QUALIFIED"})
    assert campaign.mode == SHADOW_MODE
    assert result.mode == SHADOW_MODE
    assert result.normal_verdict_override is None
    assert result.genesis_activated is False


def test_qualified_components_are_exercised_without_authority_inversion():
    campaign = _campaign()
    assert campaign.authority_owners == {
        "schedule": "Cpl",
        "specialist": "Officers",
        "falsification": "Challenger",
        "admission": "Judge",
        "constitutional_admissibility": "Rust",
        "engineering_verdict": "Sergeant",
    }
    assert campaign.open_frontier == ("contract-a", "obligation-b")


def test_unknown_is_conserved_in_shadow_result():
    result = run_shadow_assurance(_campaign(), lambda _c: {"admissible": None, "status": "QUALIFIED"})
    assert result.admissible is None
    assert result.status == "UNKNOWN"


def test_rust_cannot_issue_engineering_verdict():
    try:
        run_shadow_assurance(_campaign(), lambda _c: {"admissible": True, "engineering_verdict": "APPROVE"})
    except ValueError as exc:
        assert "verdict authority" in str(exc)
    else:
        raise AssertionError("Rust verdict issuance must fail closed")


def test_missing_judge_or_challenger_authority_fails_closed():
    for ledger, falsification in [
        ({"judge_admission_required": False}, {"challenger_owned": True}),
        ({"judge_admission_required": True}, {"challenger_owned": False}),
    ]:
        try:
            compile_assurance_frontier({"authority_owner": "Sergeant", "open_assurance_frontier": []}, {}, ledger, {}, {}, falsification)
        except ValueError:
            continue
        raise AssertionError("authority bypass must fail closed")
