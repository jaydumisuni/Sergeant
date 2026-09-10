from __future__ import annotations

from dataclasses import replace

import pytest

from main_review.assurance_contract_registry import ClosureGrade
from main_review.falsification_frontier import FalsifierSearchMode, compile_falsification_frontier
from main_review.falsification_frontier_protocol import (
    QUALIFIED_FALSIFICATION_FRONTIER,
    FalsificationFrontierQualificationError,
    qualify_falsification_frontier,
    validate_qualified_falsification_frontier,
)
from tests.test_sae90_falsification_campaign import qualified_sae80, domain, evidence


def exact_fixture():
    parts, qualified = qualified_sae80()
    contract = parts[0].contracts[0]
    domains = (domain(contract),)
    preview = compile_falsification_frontier(
        qualified_proof_world=qualified, expected_obligation=parts[2], registry=parts[0],
        parameter_domains=domains, evidence=(),
    )
    evidence_items = tuple(evidence(item) for item in preview.expected_instances)
    result = compile_falsification_frontier(
        qualified_proof_world=qualified, expected_obligation=parts[2], registry=parts[0],
        parameter_domains=domains, evidence=evidence_items,
    )
    assert result.grade is ClosureGrade.EXACT and not result.blockers
    return parts, qualified, domains, evidence_items, result


def qualify(parts):
    base, qualified, domains, evidence_items, result = parts
    return qualify_falsification_frontier(
        qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
        parameter_domains=domains, evidence=evidence_items, result=result,
    )


def test_exact_bounded_frontier_crosses_qualification_boundary() -> None:
    fixture = exact_fixture()
    q = qualify(fixture)
    assert q.protocol_id == QUALIFIED_FALSIFICATION_FRONTIER
    assert q.frontier_id == fixture[4].frontier_id
    assert q.qualified_proof_world_id == fixture[1].qualification_id
    assert len(q.qualification_id) == 64


def test_supplied_frontier_must_equal_canonical_recomputation() -> None:
    fixture = exact_fixture()
    forged = replace(fixture[4], frontier_id="0" * 64)
    with pytest.raises(FalsificationFrontierQualificationError, match="canonical recomputation"):
        qualify_falsification_frontier(
            qualified_proof_world=fixture[1], expected_obligation=fixture[0][2], registry=fixture[0][0],
            parameter_domains=fixture[2], evidence=fixture[3], result=forged,
        )


def test_missing_instance_evidence_cannot_qualify() -> None:
    base, qualified, domains, _, _ = exact_fixture()
    result = compile_falsification_frontier(
        qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
        parameter_domains=domains, evidence=(),
    )
    with pytest.raises(FalsificationFrontierQualificationError, match="EXACT|blocked"):
        qualify_falsification_frontier(
            qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
            parameter_domains=domains, evidence=(), result=result,
        )


def test_open_parameter_domain_cannot_qualify() -> None:
    base, qualified = qualified_sae80()
    c = base[0].contracts[0]
    domains = (domain(c, closed=False),)
    result = compile_falsification_frontier(
        qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
        parameter_domains=domains, evidence=(),
    )
    with pytest.raises(FalsificationFrontierQualificationError, match="EXACT|blocked"):
        qualify_falsification_frontier(
            qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
            parameter_domains=domains, evidence=(), result=result,
        )


def test_statistical_search_cannot_qualify_as_exhaustive() -> None:
    base, qualified = qualified_sae80()
    c = base[0].contracts[0]
    domains = (domain(c, values=("/admin",)),)
    preview = compile_falsification_frontier(
        qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
        parameter_domains=domains, evidence=(),
    )
    items = (evidence(preview.expected_instances[0], search_mode=FalsifierSearchMode.STATISTICAL),)
    result = compile_falsification_frontier(
        qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
        parameter_domains=domains, evidence=items,
    )
    with pytest.raises(FalsificationFrontierQualificationError, match="EXACT|blocked"):
        qualify_falsification_frontier(
            qualified_proof_world=qualified, expected_obligation=base[2], registry=base[0],
            parameter_domains=domains, evidence=items, result=result,
        )


def test_qualified_record_is_content_addressed_and_not_self_mutable() -> None:
    q = qualify(exact_fixture())
    with pytest.raises(FalsificationFrontierQualificationError, match="qualification identity"):
        validate_qualified_falsification_frontier(replace(q, qualification_id="0" * 64))
    assert validate_qualified_falsification_frontier(q) == q
