from __future__ import annotations

import pytest

from main_review.assurance_integration import (
    SHADOW_MODE,
    compile_assurance_frontier,
    run_shadow_assurance,
)


def inputs():
    return dict(
        review_world={"open_assurance_frontier": ["obl-1"], "authority_owner": "Sergeant"},
        registry={"qualified": True},
        ledger={"judge_admission_required": True},
        capabilities={"qualified": True},
        proof_world={"qualified": True},
        falsification={"challenger_owned": True, "complete": True},
    )


def test_compile_preserves_fixed_authority_ownership_and_shadow_mode():
    campaign = compile_assurance_frontier(**inputs())
    assert campaign.mode == SHADOW_MODE
    assert campaign.open_frontier == ("obl-1",)
    assert campaign.authority_owners == {
        "schedule": "Cpl",
        "specialist": "Officers",
        "falsification": "Challenger",
        "admission": "Judge",
        "constitutional_admissibility": "Rust",
        "engineering_verdict": "Sergeant",
    }
    assert campaign.genesis_activated is False


def test_missing_dependency_fails_closed():
    values = inputs(); values["registry"] = None
    with pytest.raises(ValueError, match="missing assurance dependency: registry"):
        compile_assurance_frontier(**values)


def test_officer_or_judge_bypass_is_rejected():
    values = inputs(); values["ledger"] = {"judge_admission_required": False}
    with pytest.raises(ValueError, match="Judge admission"):
        compile_assurance_frontier(**values)
    values = inputs(); values["falsification"] = {"challenger_owned": False, "complete": True}
    with pytest.raises(ValueError, match="Challenger"):
        compile_assurance_frontier(**values)


def test_rust_cannot_issue_engineering_verdict():
    campaign = compile_assurance_frontier(**inputs())
    with pytest.raises(ValueError, match="Rust kernel attempted verdict authority"):
        run_shadow_assurance(campaign, lambda _: {"admissible": True, "verdict": "PASS"})


def test_unknown_is_preserved_not_suppressed():
    campaign = compile_assurance_frontier(**inputs())
    result = run_shadow_assurance(campaign, lambda _: {"admissible": None, "status": "UNKNOWN"})
    assert result.status == "UNKNOWN"
    assert result.mode == SHADOW_MODE
    assert result.normal_verdict_override is None


def test_accidental_activation_is_impossible_before_genesis_exit():
    campaign = compile_assurance_frontier(**inputs())
    result = run_shadow_assurance(campaign, lambda _: {"admissible": True, "status": "QUALIFIED"})
    assert result.mode == SHADOW_MODE
    assert result.genesis_activated is False
    assert result.normal_verdict_override is None
