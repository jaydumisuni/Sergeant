"""SAE-70 total mandatory contract / instance / obligation closure.

The founding generation is deliberately conservative. Every mandatory ACR
contract is accounted for, applicability remains three-valued, FALSE requires a
content-bound PROVEN_NO_MATCH proof, TRUE requires an explicit contract-instance
enumeration, and obligations are composed by conservative union. No first-match,
priority, specificity, or subsumption weakening exists in this module.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .assurance_contract_registry import (
    ACRContract,
    ACRRegistry,
    ApplicabilityContext,
    ApplicabilityTruth,
    ClosureGrade,
)
from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class ContractClosureError(ReviewWorldError):
    """Raised for malformed SAE-70 contract-closure authority inputs."""


_GRADE_RANK = {
    ClosureGrade.UNKNOWN: 0,
    ClosureGrade.PARTIAL: 1,
    ClosureGrade.CONSERVATIVE_SUPERSET: 2,
    ClosureGrade.EXACT: 3,
}


def _require_sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except ReviewWorldError as exc:
        raise ContractClosureError(str(exc)) from exc


def _validated_contract(contract: ACRContract) -> ACRContract:
    if not isinstance(contract, ACRContract):
        raise ContractClosureError("contract must be an ACRContract")
    try:
        canonical = ACRContract.create(**contract.constructor_fields())
    except (TypeError, KeyError, ReviewWorldError, ValueError) as exc:
        raise ContractClosureError(f"contract generation or identity is malformed: {exc}") from exc
    if canonical.contract_id_hash != contract.contract_id_hash:
        raise ContractClosureError("contract generation or identity mismatch")
    return canonical


def _context_id(context: ApplicabilityContext) -> str:
    if not isinstance(context, ApplicabilityContext):
        raise ContractClosureError("applicability context must be ApplicabilityContext")
    if not isinstance(context.closure, ClosureGrade):
        raise ContractClosureError("applicability context closure is invalid")
    return sha256_id(
        {
            "schema_version": "sergeant.sae70-applicability-context.v1",
            "facts": dict(context.facts),
            "closure": context.closure.value,
        }
    )


def _meets(actual: ClosureGrade, required: ClosureGrade) -> bool:
    if not isinstance(actual, ClosureGrade) or not isinstance(required, ClosureGrade):
        return False
    return _GRADE_RANK[actual] >= _GRADE_RANK[required]


def _weaker(left: ClosureGrade, right: ClosureGrade) -> ClosureGrade:
    return left if _GRADE_RANK[left] <= _GRADE_RANK[right] else right


def _stronger(left: ClosureGrade, right: ClosureGrade) -> ClosureGrade:
    return left if _GRADE_RANK[left] >= _GRADE_RANK[right] else right


def _canonical_binding(binding: Mapping[str, str], required: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    if not isinstance(binding, Mapping):
        raise ContractClosureError("contract instance binding must be a mapping")
    if set(binding) != set(required):
        raise ContractClosureError("contract instance binding must cover exact bound subject variables")
    normalized: list[tuple[str, str]] = []
    for name in sorted(required):
        value = binding[name]
        if not isinstance(value, str) or not value or value != value.strip():
            raise ContractClosureError("contract instance bound subject values must be canonical non-empty strings")
        normalized.append((name, value))
    return tuple(normalized)


def _enumeration_body(
    *,
    contract_id: str,
    contract_generation: str,
    contract_id_hash: str,
    bindings: tuple[tuple[tuple[str, str], ...], ...],
    closure: ClosureGrade,
    source_basis_id: str,
) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae70-contract-instance-enumeration.v1",
        "contract_id": contract_id,
        "contract_generation": contract_generation,
        "contract_id_hash": contract_id_hash,
        "bindings": [dict(binding) for binding in bindings],
        "closure": closure.value,
        "source_basis_id": source_basis_id,
    }


@dataclass(frozen=True)
class ContractInstanceEnumeration:
    contract_id: str
    contract_generation: str
    contract_id_hash: str
    bindings: tuple[tuple[tuple[str, str], ...], ...]
    closure: ClosureGrade
    source_basis_id: str
    enumeration_id: str

    @classmethod
    def create(
        cls,
        *,
        contract: ACRContract,
        bindings: Sequence[Mapping[str, str]],
        closure: ClosureGrade,
        source_basis_id: str,
    ) -> "ContractInstanceEnumeration":
        canonical = _validated_contract(contract)
        if isinstance(bindings, (str, bytes)):
            raise ContractClosureError("contract instance bindings must be a non-string sequence")
        if not isinstance(closure, ClosureGrade):
            raise ContractClosureError("contract instance enumeration closure is invalid")
        source_basis_id = _require_sha(source_basis_id, "contract instance source_basis_id")
        required = tuple(canonical.bound_subject_variables)
        normalized = tuple(_canonical_binding(binding, required) for binding in bindings)
        if len(set(normalized)) != len(normalized):
            raise ContractClosureError("duplicate contract instance in enumeration")
        normalized = tuple(sorted(normalized))
        body = _enumeration_body(
            contract_id=canonical.contract_id,
            contract_generation=canonical.generation,
            contract_id_hash=canonical.contract_id_hash,
            bindings=normalized,
            closure=closure,
            source_basis_id=source_basis_id,
        )
        return cls(
            canonical.contract_id,
            canonical.generation,
            canonical.contract_id_hash,
            normalized,
            closure,
            source_basis_id,
            sha256_id(body),
        )

    def validate_for(self, contract: ACRContract) -> None:
        canonical = _validated_contract(contract)
        if (
            self.contract_id != canonical.contract_id
            or self.contract_generation != canonical.generation
            or self.contract_id_hash != canonical.contract_id_hash
        ):
            raise ContractClosureError("contract instance enumeration contract generation/identity mismatch")
        if not isinstance(self.closure, ClosureGrade):
            raise ContractClosureError("contract instance enumeration closure is invalid")
        _require_sha(self.source_basis_id, "contract instance source_basis_id")
        required = tuple(canonical.bound_subject_variables)
        for binding in self.bindings:
            if _canonical_binding(dict(binding), required) != binding:
                raise ContractClosureError("contract instance binding is not canonical")
        if len(set(self.bindings)) != len(self.bindings):
            raise ContractClosureError("duplicate contract instance in enumeration")
        expected = sha256_id(
            _enumeration_body(
                contract_id=self.contract_id,
                contract_generation=self.contract_generation,
                contract_id_hash=self.contract_id_hash,
                bindings=self.bindings,
                closure=self.closure,
                source_basis_id=self.source_basis_id,
            )
        )
        if self.enumeration_id != expected:
            raise ContractClosureError("contract instance enumeration identity mismatch")


def _no_match_body(
    *,
    contract_id: str,
    contract_generation: str,
    contract_id_hash: str,
    context_id: str,
    closure: ClosureGrade,
    evidence_id: str,
) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae70-proven-no-match.v1",
        "contract_id": contract_id,
        "contract_generation": contract_generation,
        "contract_id_hash": contract_id_hash,
        "context_id": context_id,
        "closure": closure.value,
        "evidence_id": evidence_id,
    }


@dataclass(frozen=True)
class ProvenNoMatch:
    contract_id: str
    contract_generation: str
    contract_id_hash: str
    context_id: str
    closure: ClosureGrade
    evidence_id: str
    proof_id: str

    @classmethod
    def create(
        cls,
        *,
        contract: ACRContract,
        context: ApplicabilityContext,
        closure: ClosureGrade,
        evidence_id: str,
    ) -> "ProvenNoMatch":
        canonical = _validated_contract(contract)
        if not isinstance(closure, ClosureGrade):
            raise ContractClosureError("PROVEN_NO_MATCH closure is invalid")
        evaluation = canonical.evaluate(context)
        if evaluation.truth is not ApplicabilityTruth.FALSE:
            raise ContractClosureError("PROVEN_NO_MATCH requires FALSE applicability")
        required = canonical.negative_applicability.required_closure
        if not _meets(closure, required):
            raise ContractClosureError("PROVEN_NO_MATCH does not meet required closure")
        evidence_id = _require_sha(evidence_id, "PROVEN_NO_MATCH evidence_id")
        context_id = _context_id(context)
        body = _no_match_body(
            contract_id=canonical.contract_id,
            contract_generation=canonical.generation,
            contract_id_hash=canonical.contract_id_hash,
            context_id=context_id,
            closure=closure,
            evidence_id=evidence_id,
        )
        return cls(
            canonical.contract_id,
            canonical.generation,
            canonical.contract_id_hash,
            context_id,
            closure,
            evidence_id,
            sha256_id(body),
        )

    def validate_for(self, contract: ACRContract, context: ApplicabilityContext) -> None:
        canonical = _validated_contract(contract)
        if (
            self.contract_id != canonical.contract_id
            or self.contract_generation != canonical.generation
            or self.contract_id_hash != canonical.contract_id_hash
        ):
            raise ContractClosureError("PROVEN_NO_MATCH contract generation/identity mismatch")
        evaluation = canonical.evaluate(context)
        if evaluation.truth is not ApplicabilityTruth.FALSE:
            raise ContractClosureError("PROVEN_NO_MATCH requires FALSE applicability")
        if self.context_id != _context_id(context):
            raise ContractClosureError("PROVEN_NO_MATCH context identity mismatch")
        required = canonical.negative_applicability.required_closure
        if not _meets(self.closure, required):
            raise ContractClosureError("PROVEN_NO_MATCH does not meet required closure")
        _require_sha(self.evidence_id, "PROVEN_NO_MATCH evidence_id")
        expected = sha256_id(
            _no_match_body(
                contract_id=self.contract_id,
                contract_generation=self.contract_generation,
                contract_id_hash=self.contract_id_hash,
                context_id=self.context_id,
                closure=self.closure,
                evidence_id=self.evidence_id,
            )
        )
        if self.proof_id != expected:
            raise ContractClosureError("PROVEN_NO_MATCH identity mismatch")


@dataclass(frozen=True)
class ContractCensusEntry:
    contract_id: str
    contract_generation: str
    applicability: ApplicabilityTruth
    disposition: str
    unresolved_facts: tuple[str, ...]


@dataclass(frozen=True)
class ExpectedContractInstance:
    contract_id: str
    contract_generation: str
    bindings: tuple[tuple[str, str], ...]
    closure: ClosureGrade
    source_basis_id: str
    contract_instance_id: str


@dataclass(frozen=True)
class ObligationProvenance:
    contract_id: str
    contract_generation: str
    contract_instance_id: str
    required_closure: ClosureGrade


@dataclass(frozen=True)
class ExpectedObligation:
    family: str
    bindings: tuple[tuple[str, str], ...]
    required_closure: ClosureGrade
    provenance: tuple[ObligationProvenance, ...]
    conflict_resolved_conservatively: bool
    obligation_id: str


@dataclass(frozen=True)
class ContractClosureResult:
    registry_id: str
    grade: ClosureGrade
    contract_census: tuple[ContractCensusEntry, ...]
    expected_instances: tuple[ExpectedContractInstance, ...]
    expected_obligations: tuple[ExpectedObligation, ...]
    blockers: tuple[str, ...]
    result_id: str


def _instance_from(
    contract: ACRContract,
    enumeration: ContractInstanceEnumeration,
    binding: tuple[tuple[str, str], ...],
) -> ExpectedContractInstance:
    body = {
        "schema_version": "sergeant.sae70-contract-instance.v1",
        "contract_id": contract.contract_id,
        "contract_generation": contract.generation,
        "contract_id_hash": contract.contract_id_hash,
        "bindings": dict(binding),
        "enumeration_id": enumeration.enumeration_id,
        "source_basis_id": enumeration.source_basis_id,
    }
    return ExpectedContractInstance(
        contract.contract_id,
        contract.generation,
        binding,
        enumeration.closure,
        enumeration.source_basis_id,
        sha256_id(body),
    )


def _validate_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ContractClosureError(f"{field} must be a mapping")
    if any(not isinstance(key, str) for key in value):
        raise ContractClosureError(f"{field} registry keys must be strings")
    return value


def compile_contract_closure(
    *,
    registry: ACRRegistry,
    contexts: Mapping[str, ApplicabilityContext],
    instance_enumerations: Mapping[str, ContractInstanceEnumeration],
    proven_no_match: Mapping[str, ProvenNoMatch],
) -> ContractClosureResult:
    """Compile the founding SAE-70 total contract and obligation frontier."""
    if not isinstance(registry, ACRRegistry):
        raise ContractClosureError("registry must be an ACRRegistry")
    try:
        canonical_registry = ACRRegistry.from_payload(registry.to_payload())
    except (ReviewWorldError, ValueError, TypeError) as exc:
        raise ContractClosureError(f"registry identity is malformed: {exc}") from exc

    contexts = _validate_mapping(contexts, "contexts")  # type: ignore[assignment]
    instance_enumerations = _validate_mapping(instance_enumerations, "instance_enumerations")  # type: ignore[assignment]
    proven_no_match = _validate_mapping(proven_no_match, "proven_no_match")  # type: ignore[assignment]

    contract_by_id = {contract.contract_id: contract for contract in canonical_registry.contracts}
    known = set(contract_by_id)
    unknown_enum_keys = set(instance_enumerations) - known
    if unknown_enum_keys:
        raise ContractClosureError(
            f"instance enumeration registry key is not a mandatory contract: {sorted(unknown_enum_keys)!r}"
        )
    unknown_no_match_keys = set(proven_no_match) - known
    if unknown_no_match_keys:
        raise ContractClosureError(
            f"PROVEN_NO_MATCH registry key is not a mandatory contract: {sorted(unknown_no_match_keys)!r}"
        )

    try:
        evaluations = canonical_registry.evaluate_all(contexts)
    except (ReviewWorldError, ValueError, TypeError) as exc:
        raise ContractClosureError(str(exc)) from exc
    evaluation_by_id = {evaluation.contract_id: evaluation for evaluation in evaluations}

    grade = ClosureGrade.EXACT
    blockers: list[str] = []
    census: list[ContractCensusEntry] = []
    expected_instances: list[ExpectedContractInstance] = []
    active_contracts: dict[str, ACRContract] = {}

    for contract in canonical_registry.contracts:
        evaluation = evaluation_by_id[contract.contract_id]
        enum_obj = instance_enumerations.get(contract.contract_id)
        no_match_obj = proven_no_match.get(contract.contract_id)

        if evaluation.truth is ApplicabilityTruth.TRUE:
            census.append(
                ContractCensusEntry(
                    contract.contract_id,
                    contract.generation,
                    evaluation.truth,
                    "ACTIVE",
                    evaluation.unresolved_facts,
                )
            )
            active_contracts[contract.contract_id] = contract
            if no_match_obj is not None:
                raise ContractClosureError("PROVEN_NO_MATCH cannot accompany TRUE applicability")
            if enum_obj is None:
                grade = ClosureGrade.UNKNOWN
                blockers.append(f"{contract.contract_id}: missing contract instance enumeration")
                continue
            if not isinstance(enum_obj, ContractInstanceEnumeration):
                raise ContractClosureError("instance enumeration contains invalid record type")
            enum_obj.validate_for(contract)
            grade = _weaker(grade, enum_obj.closure)
            if enum_obj.closure is not ClosureGrade.EXACT:
                blockers.append(
                    f"{contract.contract_id}: instance enumeration closure is {enum_obj.closure.value}, not EXACT"
                )
            expected_instances.extend(
                _instance_from(contract, enum_obj, binding) for binding in enum_obj.bindings
            )
            continue

        if evaluation.truth is ApplicabilityTruth.FALSE:
            if enum_obj is not None:
                raise ContractClosureError("contract instance enumeration cannot accompany FALSE applicability")
            if no_match_obj is None:
                grade = ClosureGrade.UNKNOWN
                blockers.append(f"{contract.contract_id}: FALSE applicability lacks PROVEN_NO_MATCH proof")
                census.append(
                    ContractCensusEntry(
                        contract.contract_id,
                        contract.generation,
                        evaluation.truth,
                        "UNKNOWN",
                        evaluation.unresolved_facts,
                    )
                )
                continue
            if not isinstance(no_match_obj, ProvenNoMatch):
                raise ContractClosureError("proven_no_match contains invalid record type")
            context = contexts.get(contract.contract_id)
            if not isinstance(context, ApplicabilityContext):
                raise ContractClosureError("PROVEN_NO_MATCH requires the exact evaluated applicability context")
            no_match_obj.validate_for(contract, context)
            grade = _weaker(grade, no_match_obj.closure)
            census.append(
                ContractCensusEntry(
                    contract.contract_id,
                    contract.generation,
                    evaluation.truth,
                    "PROVEN_NO_MATCH",
                    evaluation.unresolved_facts,
                )
            )
            continue

        if enum_obj is not None:
            raise ContractClosureError("contract instance enumeration cannot override UNKNOWN applicability")
        if no_match_obj is not None:
            raise ContractClosureError("PROVEN_NO_MATCH cannot override UNKNOWN applicability")
        grade = ClosureGrade.UNKNOWN
        unresolved = evaluation.unresolved_facts or ("<unknown-applicability>",)
        blockers.append(
            f"{contract.contract_id}: applicability remains UNKNOWN ({', '.join(unresolved)})"
        )
        census.append(
            ContractCensusEntry(
                contract.contract_id,
                contract.generation,
                evaluation.truth,
                "UNKNOWN",
                evaluation.unresolved_facts,
            )
        )

    expected_instances.sort(key=lambda item: (item.contract_id, item.bindings, item.contract_instance_id))

    obligation_origins: dict[
        tuple[str, tuple[tuple[str, str], ...]], list[ObligationProvenance]
    ] = {}
    for instance in expected_instances:
        contract = active_contracts[instance.contract_id]
        for requirement in contract.mandatory_obligations:
            key = (requirement.family, instance.bindings)
            obligation_origins.setdefault(key, []).append(
                ObligationProvenance(
                    contract.contract_id,
                    contract.generation,
                    instance.contract_instance_id,
                    requirement.required_closure,
                )
            )

    expected_obligations: list[ExpectedObligation] = []
    for (family, bindings), origins in sorted(obligation_origins.items(), key=lambda item: item[0]):
        origins = sorted(
            origins,
            key=lambda origin: (
                origin.contract_id,
                origin.contract_generation,
                origin.contract_instance_id,
                origin.required_closure.value,
            ),
        )
        required = ClosureGrade.UNKNOWN
        for origin in origins:
            required = _stronger(required, origin.required_closure)
        distinct_requirements = {origin.required_closure for origin in origins}
        provenance = tuple(origins)
        body = {
            "schema_version": "sergeant.sae70-expected-obligation.v1",
            "family": family,
            "bindings": dict(bindings),
            "required_closure": required.value,
            "provenance": [
                {
                    "contract_id": origin.contract_id,
                    "contract_generation": origin.contract_generation,
                    "contract_instance_id": origin.contract_instance_id,
                    "required_closure": origin.required_closure.value,
                }
                for origin in provenance
            ],
        }
        expected_obligations.append(
            ExpectedObligation(
                family,
                bindings,
                required,
                provenance,
                len(distinct_requirements) > 1,
                sha256_id(body),
            )
        )

    census_tuple = tuple(census)
    instances_tuple = tuple(expected_instances)
    obligations_tuple = tuple(expected_obligations)
    blockers_tuple = tuple(sorted(set(blockers)))
    result_body = {
        "schema_version": "sergeant.sae70-contract-closure-result.v1",
        "registry_id": canonical_registry.registry_id,
        "grade": grade.value,
        "contract_census": [
            {
                "contract_id": entry.contract_id,
                "contract_generation": entry.contract_generation,
                "applicability": entry.applicability.value,
                "disposition": entry.disposition,
                "unresolved_facts": list(entry.unresolved_facts),
            }
            for entry in census_tuple
        ],
        "expected_instances": [
            {
                "contract_id": instance.contract_id,
                "contract_generation": instance.contract_generation,
                "bindings": dict(instance.bindings),
                "closure": instance.closure.value,
                "source_basis_id": instance.source_basis_id,
                "contract_instance_id": instance.contract_instance_id,
            }
            for instance in instances_tuple
        ],
        "expected_obligations": [
            {
                "family": obligation.family,
                "bindings": dict(obligation.bindings),
                "required_closure": obligation.required_closure.value,
                "provenance": [
                    {
                        "contract_id": origin.contract_id,
                        "contract_generation": origin.contract_generation,
                        "contract_instance_id": origin.contract_instance_id,
                        "required_closure": origin.required_closure.value,
                    }
                    for origin in obligation.provenance
                ],
                "conflict_resolved_conservatively": obligation.conflict_resolved_conservatively,
                "obligation_id": obligation.obligation_id,
            }
            for obligation in obligations_tuple
        ],
        "blockers": list(blockers_tuple),
    }
    return ContractClosureResult(
        canonical_registry.registry_id,
        grade,
        census_tuple,
        instances_tuple,
        obligations_tuple,
        blockers_tuple,
        sha256_id(result_body),
    )
