from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from main_review.assurance_contract_registry import BoundedDomain, ClosureGrade
from main_review.capability_qualification import CapabilityPassport, analyze_bounded_indirect_calls
from main_review.review_world import sha256_id
from tests.semantic_oracle.bounded_call_oracle import (
    HOLDOUT_FIXTURE,
    ORACLE_IMPLEMENTATION_LINEAGE_ID,
    TRAINING_FIXTURE,
    TRANSFER_FIXTURE,
    exact_match,
    expected_relations,
)


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_LINEAGE = sha256_id({"implementation": "sae60-python-ast-bounded-dispatch-v1"})
PARSER_LINEAGE = sha256_id({"parser": "cpython-ast", "generation": "3.11-v1"})
FRAMEWORK_LINEAGE = sha256_id({"framework": "python-language-semantics", "generation": "3.11"})
COMMON_MODE = sha256_id({"common_mode": "production-static-analyzer-control-v1"})
CONTROL_LINEAGE = sha256_id({"control": "sae60-candidate-authoring-v1"})


def passport(
    *,
    artifact_generation: str = "sae60-candidate-gen-1",
    domain_generation: str = "domain-gen-1",
    domain_id: str = "python.bounded-literal-dispatch.v1",
    parser_generation: str = "cpython-ast-3.11-v1",
    framework_generation: str = "python-language-3.11",
    proof_ceiling: str = "BOUNDED_EXHAUSTIVE_ORACLE",
    max_ast_nodes: int = 500,
    max_source_bytes: int = 20_000,
) -> CapabilityPassport:
    domain = BoundedDomain.create(
        domain_id=domain_id,
        generation=domain_generation,
        dimensions={
            "max_source_bytes": max_source_bytes,
            "max_ast_nodes": max_ast_nodes,
            "max_dispatch_tables": 8,
            "max_table_entries": 32,
        },
    )
    return CapabilityPassport.create(
        capability_name="python-bounded-literal-dispatch",
        domain=domain,
        artifact_generation=artifact_generation,
        parser_generation=parser_generation,
        framework_generation=framework_generation,
        qualification_protocol_generation="sae60-qualification-v1",
        proof_ceiling=proof_ceiling,
        closure_ceiling=ClosureGrade.EXACT,
        implementation_lineage_id=IMPLEMENTATION_LINEAGE,
        parser_lineage_id=PARSER_LINEAGE,
        framework_lineage_id=FRAMEWORK_LINEAGE,
        common_mode_lineage_id=COMMON_MODE,
        control_lineage_id=CONTROL_LINEAGE,
    )


def observed(result) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (relation.table, relation.key, relation.target)
        for relation in result.relations
        if relation.key is not None and relation.target is not None
    )


def test_exact_training_hidden_holdout_and_transfer_are_all_independently_closed() -> None:
    p = passport()
    for fixture in (TRAINING_FIXTURE, HOLDOUT_FIXTURE, TRANSFER_FIXTURE):
        result = analyze_bounded_indirect_calls(fixture.source, passport=p)
        assert result.grade is ClosureGrade.EXACT
        assert result.blockers == ()
        assert result.resource_exhausted is False
        assert exact_match(fixture, observed(result))


def test_omission_order_and_cardinality_mutations_fail_independent_oracle() -> None:
    result = analyze_bounded_indirect_calls(HOLDOUT_FIXTURE.source, passport=passport())
    baseline = observed(result)
    assert result.grade is ClosureGrade.EXACT
    assert exact_match(HOLDOUT_FIXTURE, baseline)
    assert len(baseline) >= 3

    omitted = baseline[:-1]
    reordered = tuple(reversed(baseline))
    duplicated = baseline + (baseline[0],)
    injected = baseline + (("RELEASE_STEPS", "ghost", "ghost"),)

    assert not exact_match(HOLDOUT_FIXTURE, omitted)
    assert not exact_match(HOLDOUT_FIXTURE, reordered)
    assert not exact_match(HOLDOUT_FIXTURE, duplicated)
    assert not exact_match(HOLDOUT_FIXTURE, injected)


def test_historical_replay_cannot_cross_passport_generation_identity() -> None:
    generation_one = passport()
    generation_two = passport(artifact_generation="sae60-candidate-gen-2")
    result = analyze_bounded_indirect_calls(TRAINING_FIXTURE.source, passport=generation_one)

    assert result.grade is ClosureGrade.EXACT
    assert result.passport_id == generation_one.passport_id
    assert generation_two.passport_id != generation_one.passport_id
    assert result.passport_id != generation_two.passport_id

    forged_current = replace(generation_two, passport_id=generation_one.passport_id)
    forged_result = analyze_bounded_indirect_calls(TRAINING_FIXTURE.source, passport=forged_current)
    assert forged_result.grade is ClosureGrade.UNKNOWN
    assert any("identity mismatch" in blocker for blocker in forged_result.blockers)


def test_historical_oracle_fixture_replay_is_digest_bound() -> None:
    stale = replace(HOLDOUT_FIXTURE, source=HOLDOUT_FIXTURE.source + "\n# changed-generation\n")
    with pytest.raises(AssertionError, match="frozen digest"):
        expected_relations(stale)


def test_only_the_measured_bounded_domain_can_reach_exact() -> None:
    general_domain = passport(domain_id="python.general-call-semantics.v1")
    wrong_domain_generation = passport(domain_generation="domain-gen-2")
    wrong_parser = passport(parser_generation="cpython-ast-3.12-v1")
    wrong_framework = passport(framework_generation="python-language-3.12")
    weaker_ceiling = passport(proof_ceiling="BOUNDED_CORPUS_ONLY")

    cases = (
        (general_domain, "unsupported capability domain"),
        (wrong_domain_generation, "unsupported capability domain generation"),
        (wrong_parser, "unsupported parser generation"),
        (wrong_framework, "unsupported framework generation"),
        (weaker_ceiling, "proof/closure ceiling"),
    )
    for p, expected in cases:
        result = analyze_bounded_indirect_calls(TRAINING_FIXTURE.source, passport=p)
        assert result.grade is ClosureGrade.UNKNOWN
        assert any(expected in blocker for blocker in result.blockers)


def test_dynamic_and_resource_exhausted_constructs_remain_unknown() -> None:
    dynamic = '''def left():
    return 1

def right():
    return 2

TABLE = {"left": left, "right": right}
def dispatch(key):
    return TABLE[key]()
'''
    result = analyze_bounded_indirect_calls(dynamic, passport=passport())
    assert result.grade is ClosureGrade.UNKNOWN
    assert all(relation.target is None for relation in result.relations)

    oversized = TRAINING_FIXTURE.source + "\n" + "\n".join(
        f"filler_{index} = {index}" for index in range(100)
    )
    exhausted = analyze_bounded_indirect_calls(oversized, passport=passport(max_ast_nodes=20))
    assert exhausted.grade is ClosureGrade.UNKNOWN
    assert exhausted.resource_exhausted is True
    assert any("resource" in blocker.lower() for blocker in exhausted.blockers)


def test_oracle_and_candidate_have_distinct_implementation_and_source_lineage() -> None:
    assert IMPLEMENTATION_LINEAGE != ORACLE_IMPLEMENTATION_LINEAGE_ID

    oracle_text = (ROOT / "tests/semantic_oracle/bounded_call_oracle.py").read_text(encoding="utf-8")
    candidate_text = (ROOT / "main_review/capability_qualification.py").read_text(encoding="utf-8")

    assert "main_review.capability_qualification" not in oracle_text
    assert "tests.semantic_oracle" not in candidate_text
    assert "ast.parse" not in oracle_text
    assert "ast.parse" in candidate_text


def test_qualification_does_not_expand_normal_verdict_or_genesis_authority() -> None:
    candidate_manifest = (ROOT / "docs/103-sae60-semantic-capability-candidate-manifest.json").read_text(
        encoding="utf-8"
    )
    assert '"normal_verdict_authority": false' in candidate_manifest
    assert '"genesis_activated": false' in candidate_manifest
    assert '"produces_now": []' in candidate_manifest
    assert '"QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL"' in candidate_manifest
    assert '"python.bounded-literal-dispatch.v1"' in candidate_manifest
