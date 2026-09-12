from __future__ import annotations

import pytest

from main_review.assurance_integration import (
    QUALIFIED_RUST_ASSURANCE_KERNEL,
    compile_assurance_frontier,
    run_shadow_assurance,
)


def _qualified_inputs():
    return dict(
        review_world={"qualification_protocol_id": "QUALIFIED_REVIEW_WORLD_CONTRACT", "open_assurance_frontier": ["obl-1"], "authority_owner": "Sergeant"},
        registry={"qualification_protocol_id": "QUALIFIED_CONTRACT_INSTANCE_CLOSURE"},
        ledger={"qualification_protocol_id": "QUALIFIED_ASSURANCE_LEDGER", "judge_admission_required": True},
        capabilities={"qualification_protocol_id": "QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL"},
        proof_world={"qualification_protocol_id": "QUALIFIED_PROOF_WORLD"},
        falsification={"qualification_protocol_id": "QUALIFIED_FALSIFICATION_FRONTIER", "challenger_owned": True, "complete": True},
    )


class QualifiedKernel:
    qualification_protocol_id = QUALIFIED_RUST_ASSURANCE_KERNEL

    def __call__(self, _campaign):
        return {"admissible": True, "status": "QUALIFIED"}


def test_qualified_generations_are_accepted():
    campaign = compile_assurance_frontier(**_qualified_inputs())
    assert run_shadow_assurance(campaign, QualifiedKernel()).status == "QUALIFIED"


def test_integration_rejects_unqualified_dependency_generation():
    values = _qualified_inputs()
    values["proof_world"] = {"qualification_protocol_id": "UNQUALIFIED"}
    with pytest.raises(ValueError, match="qualified assurance dependency"):
        compile_assurance_frontier(**values)


def test_shadow_execution_rejects_unqualified_rust_kernel():
    campaign = compile_assurance_frontier(**_qualified_inputs())
    with pytest.raises(ValueError, match="qualified Rust assurance kernel"):
        run_shadow_assurance(campaign, lambda _: {"admissible": True, "status": "QUALIFIED"})
