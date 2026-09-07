from __future__ import annotations

from dataclasses import replace

from main_review.assurance_contract_registry import BoundedDomain, ClosureGrade
from main_review.capability_qualification import (
    CANDIDATE_STATE,
    CapabilityPassport,
    analyze_bounded_indirect_calls,
)
from main_review.review_world import sha256_id
from tests.semantic_oracle.bounded_call_oracle import (
    HOLDOUT_FIXTURE,
    ORACLE_IMPLEMENTATION_LINEAGE_ID,
    TRAINING_FIXTURE,
    TRANSFER_FIXTURE,
    exact_match,
    expected_relations,
)


IMPLEMENTATION_LINEAGE = sha256_id({"implementation": "sae60-python-ast-bounded-dispatch-v1"})
PARSER_LINEAGE = sha256_id({"parser": "cpython-ast", "generation": "3.11-v1"})
FRAMEWORK_LINEAGE = sha256_id({"framework": "python-language-semantics", "generation": "3.11"})
COMMON_MODE = sha256_id({"common_mode": "production-static-analyzer-control-v1"})
CONTROL_LINEAGE = sha256_id({"control": "sae60-candidate-authoring-v1"})


def _passport(*, max_ast_nodes: int = 500, max_source_bytes: int = 20_000) -> CapabilityPassport:
    domain = BoundedDomain.create(
        domain_id="python.bounded-literal-dispatch.v1",
        generation="domain-gen-1",
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
        artifact_generation="sae60-candidate-gen-1",
        parser_generation="cpython-ast-3.11-v1",
        framework_generation="python-language-3.11",
        qualification_protocol_generation="sae60-qualification-v1",
        proof_ceiling="BOUNDED_EXHAUSTIVE_ORACLE",
        closure_ceiling=ClosureGrade.EXACT,
        implementation_lineage_id=IMPLEMENTATION_LINEAGE,
        parser_lineage_id=PARSER_LINEAGE,
        framework_lineage_id=FRAMEWORK_LINEAGE,
        common_mode_lineage_id=COMMON_MODE,
        control_lineage_id=CONTROL_LINEAGE,
    )


def _observed(result) -> tuple[tuple[str, str, str], ...]:
    return tuple((relation.table, relation.key, relation.target) for relation in result.relations if relation.target is not None)


def test_passport_is_generation_domain_and_lineage_bound_but_not_self_qualified() -> None:
    passport = _passport()
    assert passport.lifecycle_state == CANDIDATE_STATE
    assert passport.domain.domain_id == "python.bounded-literal-dispatch.v1"
    assert passport.domain.generation == "domain-gen-1"
    assert passport.parser_generation == "cpython-ast-3.11-v1"
    assert passport.framework_generation == "python-language-3.11"
    assert passport.proof_ceiling == "BOUNDED_EXHAUSTIVE_ORACLE"
    assert passport.closure_ceiling is ClosureGrade.EXACT
    assert passport.implementation_lineage_id != ORACLE_IMPLEMENTATION_LINEAGE_ID
    assert len(passport.passport_id) == 64


def test_training_fixture_matches_independently_authored_exact_oracle() -> None:
    result = analyze_bounded_indirect_calls(TRAINING_FIXTURE.source, passport=_passport())
    assert result.grade is ClosureGrade.EXACT
    assert result.resource_exhausted is False
    assert result.blockers == ()
    assert exact_match(TRAINING_FIXTURE, _observed(result))


def test_hidden_holdout_matches_without_candidate_specific_fixture_logic() -> None:
    result = analyze_bounded_indirect_calls(HOLDOUT_FIXTURE.source, passport=_passport())
    assert result.grade is ClosureGrade.EXACT
    assert exact_match(HOLDOUT_FIXTURE, _observed(result))


def test_transfer_fixture_with_new_names_and_table_matches_oracle() -> None:
    result = analyze_bounded_indirect_calls(TRANSFER_FIXTURE.source, passport=_passport())
    assert result.grade is ClosureGrade.EXACT
    assert exact_match(TRANSFER_FIXTURE, _observed(result))


def test_deletion_and_undercount_mutations_are_detected_by_independent_oracle() -> None:
    result = analyze_bounded_indirect_calls(TRAINING_FIXTURE.source, passport=_passport())
    observed = _observed(result)
    assert exact_match(TRAINING_FIXTURE, observed)
    assert not exact_match(TRAINING_FIXTURE, observed[:-1])
    assert not exact_match(TRAINING_FIXTURE, observed[1:])
    assert len(expected_relations(TRAINING_FIXTURE)) == 4


def test_dynamic_key_is_unknown_and_never_invents_one_of_the_table_targets() -> None:
    source = '''def left():
    return 1

def right():
    return 2

TABLE = {"left": left, "right": right}

def dispatch(key):
    return TABLE[key]()
'''
    result = analyze_bounded_indirect_calls(source, passport=_passport())
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("dynamic dispatch key" in blocker for blocker in result.blockers)
    assert all(relation.target is None for relation in result.relations)


def test_table_mutation_or_escape_prevents_exact_closure() -> None:
    source = '''def first():
    return 1

def second():
    return 2

TABLE = {"first": first}
TABLE["second"] = second
TABLE["first"]()
'''
    result = analyze_bounded_indirect_calls(source, passport=_passport())
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("mutated or escaped" in blocker for blocker in result.blockers)


def test_lexical_shadowing_of_dispatch_table_is_unknown() -> None:
    source = '''def real():
    return 1

TABLE = {"real": real}

def invoke(TABLE):
    return TABLE["real"]()
'''
    result = analyze_bounded_indirect_calls(source, passport=_passport())
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("shadowed" in blocker for blocker in result.blockers)


def test_parse_failure_and_resource_exhaustion_fail_closed_to_unknown() -> None:
    broken = analyze_bounded_indirect_calls("def broken(:\n    pass\n", passport=_passport())
    assert broken.grade is ClosureGrade.UNKNOWN
    assert any("parse" in blocker.lower() for blocker in broken.blockers)

    source = TRAINING_FIXTURE.source + "\n" + "\n".join(f"x_{index} = {index}" for index in range(100))
    exhausted = analyze_bounded_indirect_calls(source, passport=_passport(max_ast_nodes=20))
    assert exhausted.grade is ClosureGrade.UNKNOWN
    assert exhausted.resource_exhausted is True
    assert any("resource" in blocker.lower() for blocker in exhausted.blockers)


def test_wrong_parser_or_domain_generation_cannot_reuse_exact_measurement() -> None:
    passport = _passport()
    wrong_parser = replace(passport, parser_generation="cpython-ast-3.12-v1")
    result = analyze_bounded_indirect_calls(TRAINING_FIXTURE.source, passport=wrong_parser)
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("parser generation" in blocker for blocker in result.blockers)

    wrong_domain = replace(
        passport,
        domain=BoundedDomain.create(
            domain_id="python.general-call-semantics.v1",
            generation="domain-gen-1",
            dimensions=dict(passport.domain.dimensions),
        ),
    )
    result = analyze_bounded_indirect_calls(TRAINING_FIXTURE.source, passport=wrong_domain)
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("unsupported capability domain" in blocker for blocker in result.blockers)


def test_passport_identity_changes_with_generation_domain_or_proof_ceiling() -> None:
    passport = _passport()
    changed_generation = CapabilityPassport.create(
        capability_name=passport.capability_name,
        domain=passport.domain,
        artifact_generation="sae60-candidate-gen-2",
        parser_generation=passport.parser_generation,
        framework_generation=passport.framework_generation,
        qualification_protocol_generation=passport.qualification_protocol_generation,
        proof_ceiling=passport.proof_ceiling,
        closure_ceiling=passport.closure_ceiling,
        implementation_lineage_id=passport.implementation_lineage_id,
        parser_lineage_id=passport.parser_lineage_id,
        framework_lineage_id=passport.framework_lineage_id,
        common_mode_lineage_id=passport.common_mode_lineage_id,
        control_lineage_id=passport.control_lineage_id,
    )
    changed_ceiling = replace(passport, proof_ceiling="BOUNDED_CORPUS_ONLY")
    assert changed_generation.passport_id != passport.passport_id
    assert changed_ceiling.passport_id == passport.passport_id, (
        "dataclass replacement must not be accepted as a newly issued passport identity; "
        "callers must create a canonical passport instead"
    )
