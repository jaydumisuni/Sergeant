from __future__ import annotations

from main_review.assurance_integration import (
    QUALIFIED_RUST_ASSURANCE_KERNEL,
    SHADOW_MODE,
    compile_assurance_frontier,
    run_shadow_assurance,
)


class QualifiedKernel:
    qualification_protocol_id = QUALIFIED_RUST_ASSURANCE_KERNEL

    def __init__(self, **result):
        self.result = result

    def __call__(self, _campaign):
        return dict(self.result)


def _campaign():
    return compile_assurance_frontier(
        {"qualification_protocol_id": "QUALIFIED_REVIEW_WORLD_CONTRACT", "authority_owner": "Sergeant", "open_assurance_frontier": ["contract-a", "obligation-b"]},
        {"qualification_protocol_id": "QUALIFIED_CONTRACT_INSTANCE_CLOSURE"},
        {"qualification_protocol_id": "QUALIFIED_ASSURANCE_LEDGER", "judge_admission_required": True},
        {"qualification_protocol_id": "QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL"},
        {"qualification_protocol_id": "QUALIFIED_PROOF_WORLD"},
        {"qualification_protocol_id": "QUALIFIED_FALSIFICATION_FRONTIER", "challenger_owned": True},
    )


def test_shadow_mode_preserves_normal_sergeant_authority():
    campaign = _campaign()
    result = run_shadow_assurance(campaign, QualifiedKernel(admissible=True, status="QUALIFIED"))
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
    assert campaign.review_world["qualification_protocol_id"] == "QUALIFIED_REVIEW_WORLD_CONTRACT"
    assert campaign.registry["qualification_protocol_id"] == "QUALIFIED_CONTRACT_INSTANCE_CLOSURE"
    assert campaign.ledger["qualification_protocol_id"] == "QUALIFIED_ASSURANCE_LEDGER"
    assert campaign.capabilities["qualification_protocol_id"] == "QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL"
    assert campaign.proof_world["qualification_protocol_id"] == "QUALIFIED_PROOF_WORLD"
    assert campaign.falsification["qualification_protocol_id"] == "QUALIFIED_FALSIFICATION_FRONTIER"


def test_unknown_is_conserved_in_shadow_result():
    result = run_shadow_assurance(_campaign(), QualifiedKernel(admissible=None, status="QUALIFIED"))
    assert result.admissible is None
    assert result.status == "UNKNOWN"


def test_rust_cannot_issue_engineering_verdict():
    try:
        run_shadow_assurance(_campaign(), QualifiedKernel(admissible=True, engineering_verdict="APPROVE"))
    except ValueError as exc:
        assert "verdict authority" in str(exc)
    else:
        raise AssertionError("Rust verdict issuance must fail closed")


def test_missing_judge_or_challenger_authority_fails_closed():
    base = {
        "review_world": {"qualification_protocol_id": "QUALIFIED_REVIEW_WORLD_CONTRACT", "authority_owner": "Sergeant", "open_assurance_frontier": []},
        "registry": {"qualification_protocol_id": "QUALIFIED_CONTRACT_INSTANCE_CLOSURE"},
        "capabilities": {"qualification_protocol_id": "QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL"},
        "proof_world": {"qualification_protocol_id": "QUALIFIED_PROOF_WORLD"},
    }
    for ledger, falsification in [
        ({"qualification_protocol_id": "QUALIFIED_ASSURANCE_LEDGER", "judge_admission_required": False}, {"qualification_protocol_id": "QUALIFIED_FALSIFICATION_FRONTIER", "challenger_owned": True}),
        ({"qualification_protocol_id": "QUALIFIED_ASSURANCE_LEDGER", "judge_admission_required": True}, {"qualification_protocol_id": "QUALIFIED_FALSIFICATION_FRONTIER", "challenger_owned": False}),
    ]:
        try:
            compile_assurance_frontier(base["review_world"], base["registry"], ledger, base["capabilities"], base["proof_world"], falsification)
        except ValueError:
            continue
        raise AssertionError("authority bypass must fail closed")
