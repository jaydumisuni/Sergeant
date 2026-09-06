"""SAE-20 immutable Assurance Contract Registry foundation.

This module defines candidate contract semantics only. It deliberately contains
no producer-writable qualification state or activation path; qualification
issuance belongs to SAE-30.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class RegistryError(ReviewWorldError):
    pass


def _string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise RegistryError(f"{field} must be a string")
    if value != value.strip() or not value:
        raise RegistryError(f"{field} must be canonical and non-empty")
    return value


def _identifiers(values: Sequence[str], field: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise RegistryError(f"{field} must be a non-string sequence")
    result = tuple(_string(value, field) for value in values)
    if not allow_empty and not result:
        raise RegistryError(f"{field} must not be empty")
    if len(set(result)) != len(result):
        raise RegistryError(f"{field} contains duplicates")
    return tuple(sorted(result))


def _expect_keys(payload: Mapping[str, object], required: set[str], label: str) -> None:
    if not isinstance(payload, Mapping):
        raise RegistryError(f"{label} must be an object")
    missing = required - set(payload)
    extra = set(payload) - required
    if missing:
        raise RegistryError(f"{label} missing required fields: {sorted(missing)!r}")
    if extra:
        raise RegistryError(f"{label} has unexpected fields: {sorted(extra)!r}")


class ApplicabilityTruth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class ClosureGrade(str, Enum):
    EXACT = "EXACT"
    CONSERVATIVE_SUPERSET = "CONSERVATIVE_SUPERSET"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class CollectionSemantics(str, Enum):
    SET = "SET"
    MULTISET = "MULTISET"
    ORDER = "ORDER"


class CardinalityKind(str, Enum):
    ZERO_OR_ONE = "ZERO_OR_ONE"
    EXACTLY_ONE = "EXACTLY_ONE"
    FINITE = "FINITE"
    BOUNDED_N = "BOUNDED_N"
    OPEN = "OPEN"


@dataclass(frozen=True)
class ApplicabilityResult:
    truth: ApplicabilityTruth
    unresolved_facts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplicabilityContext:
    facts: Mapping[str, object]
    closure: ClosureGrade

    @classmethod
    def exact(cls, facts: Mapping[str, object]) -> "ApplicabilityContext":
        if not isinstance(facts, Mapping):
            raise RegistryError("applicability facts must be a mapping")
        return cls(dict(facts), ClosureGrade.EXACT)

    @classmethod
    def partial(cls, facts: Mapping[str, object]) -> "ApplicabilityContext":
        if not isinstance(facts, Mapping):
            raise RegistryError("applicability facts must be a mapping")
        return cls(dict(facts), ClosureGrade.PARTIAL)


@dataclass(frozen=True)
class ApplicabilityPredicate:
    op: str
    fact: str | None = None
    expected: object | None = None
    children: tuple["ApplicabilityPredicate", ...] = ()

    @classmethod
    def fact_equals(cls, fact: str, expected: object) -> "ApplicabilityPredicate":
        return cls("fact_equals", _string(fact, "applicability fact"), expected, ())

    @classmethod
    def fact_absent(cls, fact: str) -> "ApplicabilityPredicate":
        return cls("fact_absent", _string(fact, "applicability fact"), None, ())

    @classmethod
    def all_of(cls, *children: "ApplicabilityPredicate") -> "ApplicabilityPredicate":
        return cls._composite("all", children)

    @classmethod
    def any_of(cls, *children: "ApplicabilityPredicate") -> "ApplicabilityPredicate":
        return cls._composite("any", children)

    @classmethod
    def negate(cls, child: "ApplicabilityPredicate") -> "ApplicabilityPredicate":
        if not isinstance(child, ApplicabilityPredicate):
            raise RegistryError("not predicate child must be an ApplicabilityPredicate")
        child.validate()
        return cls("not", None, None, (child,))

    @classmethod
    def _composite(cls, op: str, children: Sequence["ApplicabilityPredicate"]) -> "ApplicabilityPredicate":
        if isinstance(children, (str, bytes)) or not children:
            raise RegistryError(f"{op} applicability requires at least one child")
        normalized = tuple(children)
        for child in normalized:
            if not isinstance(child, ApplicabilityPredicate):
                raise RegistryError("applicability child must be an ApplicabilityPredicate")
            child.validate()
        return cls(op, None, None, normalized)

    def validate(self) -> None:
        if self.op == "fact_equals":
            _string(self.fact, "applicability fact")
            if self.children:
                raise RegistryError("fact_equals cannot carry children")
            return
        if self.op == "fact_absent":
            _string(self.fact, "applicability fact")
            if self.expected is not None or self.children:
                raise RegistryError("fact_absent has non-canonical fields")
            return
        if self.op in {"all", "any"}:
            if self.fact is not None or self.expected is not None or not self.children:
                raise RegistryError(f"{self.op} predicate is malformed")
            for child in self.children:
                child.validate()
            return
        if self.op == "not":
            if self.fact is not None or self.expected is not None or len(self.children) != 1:
                raise RegistryError("not predicate is malformed")
            self.children[0].validate()
            return
        raise RegistryError(f"unknown applicability operation: {self.op!r}")

    def referenced_facts(self) -> tuple[str, ...]:
        self.validate()
        if self.fact is not None:
            return (self.fact,)
        return tuple(sorted({fact for child in self.children for fact in child.referenced_facts()}))

    def evaluate(self, context: ApplicabilityContext) -> ApplicabilityResult:
        self.validate()
        if not isinstance(context, ApplicabilityContext):
            raise RegistryError("applicability context has invalid type")
        if self.op == "fact_equals":
            assert self.fact is not None
            if self.fact not in context.facts:
                return ApplicabilityResult(ApplicabilityTruth.UNKNOWN, (self.fact,))
            return ApplicabilityResult(
                ApplicabilityTruth.TRUE if context.facts[self.fact] == self.expected else ApplicabilityTruth.FALSE
            )
        if self.op == "fact_absent":
            assert self.fact is not None
            if self.fact in context.facts:
                return ApplicabilityResult(ApplicabilityTruth.FALSE)
            if context.closure is ClosureGrade.EXACT:
                return ApplicabilityResult(ApplicabilityTruth.TRUE)
            return ApplicabilityResult(ApplicabilityTruth.UNKNOWN, (self.fact,))
        if self.op == "not":
            result = self.children[0].evaluate(context)
            if result.truth is ApplicabilityTruth.TRUE:
                return ApplicabilityResult(ApplicabilityTruth.FALSE, result.unresolved_facts)
            if result.truth is ApplicabilityTruth.FALSE:
                return ApplicabilityResult(ApplicabilityTruth.TRUE, result.unresolved_facts)
            return result
        results = tuple(child.evaluate(context) for child in self.children)
        unresolved = tuple(sorted({fact for result in results for fact in result.unresolved_facts}))
        if self.op == "all":
            if any(result.truth is ApplicabilityTruth.FALSE for result in results):
                return ApplicabilityResult(ApplicabilityTruth.FALSE)
            if all(result.truth is ApplicabilityTruth.TRUE for result in results):
                return ApplicabilityResult(ApplicabilityTruth.TRUE)
            return ApplicabilityResult(ApplicabilityTruth.UNKNOWN, unresolved)
        if any(result.truth is ApplicabilityTruth.TRUE for result in results):
            return ApplicabilityResult(ApplicabilityTruth.TRUE)
        if all(result.truth is ApplicabilityTruth.FALSE for result in results):
            return ApplicabilityResult(ApplicabilityTruth.FALSE)
        return ApplicabilityResult(ApplicabilityTruth.UNKNOWN, unresolved)

    def to_payload(self) -> dict[str, object]:
        self.validate()
        return {
            "op": self.op,
            "fact": self.fact,
            "expected": self.expected,
            "children": [child.to_payload() for child in self.children],
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ApplicabilityPredicate":
        _expect_keys(payload, {"op", "fact", "expected", "children"}, "ApplicabilityPredicate")
        op = _string(payload["op"], "applicability op")
        children_raw = payload["children"]
        if not isinstance(children_raw, list):
            raise RegistryError("applicability children must be an array")
        children = tuple(cls.from_payload(item) for item in children_raw)
        fact = payload["fact"]
        if fact is not None and not isinstance(fact, str):
            raise RegistryError("applicability fact must be string or null")
        obj = cls(op, fact, payload["expected"], children)
        obj.validate()
        if obj.to_payload() != payload:
            raise RegistryError("ApplicabilityPredicate persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class BoundedDomain:
    domain_id: str
    generation: str
    dimensions: tuple[tuple[str, int], ...]
    domain_hash: str

    @classmethod
    def create(cls, *, domain_id: str, generation: str, dimensions: Mapping[str, int]) -> "BoundedDomain":
        domain_id = _string(domain_id, "domain_id")
        generation = _string(generation, "domain generation")
        if not isinstance(dimensions, Mapping) or not dimensions:
            raise RegistryError("bounded domain requires at least one explicit dimension limit")
        normalized: list[tuple[str, int]] = []
        for key, value in dimensions.items():
            key = _string(key, "domain dimension")
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise RegistryError(f"domain dimension {key!r} must have a positive integer bound")
            normalized.append((key, value))
        normalized.sort()
        if len({key for key, _ in normalized}) != len(normalized):
            raise RegistryError("bounded domain contains duplicate dimensions")
        body = {
            "schema_version": "sergeant.acr-bounded-domain.v1",
            "domain_id": domain_id,
            "generation": generation,
            "dimensions": {key: value for key, value in normalized},
        }
        return cls(domain_id, generation, tuple(normalized), sha256_id(body))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "sergeant.acr-bounded-domain.v1",
            "domain_id": self.domain_id,
            "generation": self.generation,
            "dimensions": {key: value for key, value in self.dimensions},
            "domain_hash": self.domain_hash,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "BoundedDomain":
        _expect_keys(payload, {"schema_version", "domain_id", "generation", "dimensions", "domain_hash"}, "BoundedDomain")
        if payload["schema_version"] != "sergeant.acr-bounded-domain.v1":
            raise RegistryError("unknown bounded-domain schema")
        dimensions = payload["dimensions"]
        if not isinstance(dimensions, Mapping):
            raise RegistryError("bounded-domain dimensions must be an object")
        obj = cls.create(domain_id=payload["domain_id"], generation=payload["generation"], dimensions=dimensions)
        if require_full_sha256(payload["domain_hash"], "domain_hash") != obj.domain_hash:
            raise RegistryError("domain_hash mismatch")
        if obj.to_payload() != payload:
            raise RegistryError("BoundedDomain persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class CardinalitySpec:
    kind: CardinalityKind
    maximum: int | None

    @classmethod
    def zero_or_one(cls) -> "CardinalitySpec":
        return cls(CardinalityKind.ZERO_OR_ONE, 1)

    @classmethod
    def exactly_one(cls) -> "CardinalitySpec":
        return cls(CardinalityKind.EXACTLY_ONE, 1)

    @classmethod
    def finite(cls) -> "CardinalitySpec":
        return cls(CardinalityKind.FINITE, None)

    @classmethod
    def bounded_n(cls, maximum: int) -> "CardinalitySpec":
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
            raise RegistryError("BOUNDED_N maximum must be a positive integer")
        return cls(CardinalityKind.BOUNDED_N, maximum)

    @classmethod
    def open(cls) -> "CardinalitySpec":
        return cls(CardinalityKind.OPEN, None)

    def validate(self) -> None:
        if not isinstance(self.kind, CardinalityKind):
            raise RegistryError("invalid cardinality kind")
        if self.kind in {CardinalityKind.ZERO_OR_ONE, CardinalityKind.EXACTLY_ONE} and self.maximum != 1:
            raise RegistryError(f"{self.kind.value} must have maximum=1")
        if self.kind is CardinalityKind.BOUNDED_N and (
            not isinstance(self.maximum, int) or isinstance(self.maximum, bool) or self.maximum <= 0
        ):
            raise RegistryError("BOUNDED_N requires positive maximum")
        if self.kind in {CardinalityKind.FINITE, CardinalityKind.OPEN} and self.maximum is not None:
            raise RegistryError(f"{self.kind.value} cannot carry maximum")

    def to_payload(self) -> dict[str, object]:
        self.validate()
        return {"kind": self.kind.value, "maximum": self.maximum}

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "CardinalitySpec":
        _expect_keys(payload, {"kind", "maximum"}, "CardinalitySpec")
        try:
            kind = CardinalityKind(payload["kind"])
        except (ValueError, TypeError) as error:
            raise RegistryError("invalid cardinality kind") from error
        obj = cls(kind, payload["maximum"])
        obj.validate()
        if obj.to_payload() != payload:
            raise RegistryError("CardinalitySpec persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class CollectionRequirement:
    family: str
    semantics: CollectionSemantics
    cardinality: CardinalitySpec
    required_closure: ClosureGrade

    @classmethod
    def create(
        cls,
        family: str,
        semantics: CollectionSemantics,
        cardinality: CardinalitySpec,
        required_closure: ClosureGrade,
    ) -> "CollectionRequirement":
        family = _string(family, "collection family")
        if not isinstance(semantics, CollectionSemantics):
            raise RegistryError("invalid collection semantics")
        if not isinstance(cardinality, CardinalitySpec):
            raise RegistryError("invalid cardinality specification")
        cardinality.validate()
        if not isinstance(required_closure, ClosureGrade):
            raise RegistryError("invalid required closure grade")
        return cls(family, semantics, cardinality, required_closure)

    def to_payload(self) -> dict[str, object]:
        return {
            "family": self.family,
            "semantics": self.semantics.value,
            "cardinality": self.cardinality.to_payload(),
            "required_closure": self.required_closure.value,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "CollectionRequirement":
        _expect_keys(payload, {"family", "semantics", "cardinality", "required_closure"}, "CollectionRequirement")
        try:
            semantics = CollectionSemantics(payload["semantics"])
            closure = ClosureGrade(payload["required_closure"])
        except (ValueError, TypeError) as error:
            raise RegistryError("invalid collection requirement enum") from error
        if not isinstance(payload["cardinality"], Mapping):
            raise RegistryError("collection cardinality must be an object")
        obj = cls.create(payload["family"], semantics, CardinalitySpec.from_payload(payload["cardinality"]), closure)
        if obj.to_payload() != payload:
            raise RegistryError("CollectionRequirement persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class ContractRequirement:
    family: str
    required_closure: ClosureGrade

    @classmethod
    def create(cls, family: str, required_closure: ClosureGrade) -> "ContractRequirement":
        family = _string(family, "requirement family")
        if not isinstance(required_closure, ClosureGrade):
            raise RegistryError("invalid requirement closure grade")
        return cls(family, required_closure)

    def to_payload(self) -> dict[str, object]:
        return {"family": self.family, "required_closure": self.required_closure.value}

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ContractRequirement":
        _expect_keys(payload, {"family", "required_closure"}, "ContractRequirement")
        try:
            closure = ClosureGrade(payload["required_closure"])
        except (ValueError, TypeError) as error:
            raise RegistryError("invalid requirement closure grade") from error
        obj = cls.create(payload["family"], closure)
        if obj.to_payload() != payload:
            raise RegistryError("ContractRequirement persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class NegativeApplicabilityBurden:
    mode: str
    required_closure: ClosureGrade

    @classmethod
    def proven_no_match(cls, required_closure: ClosureGrade) -> "NegativeApplicabilityBurden":
        if required_closure not in {ClosureGrade.EXACT, ClosureGrade.CONSERVATIVE_SUPERSET}:
            raise RegistryError("PROVEN_NO_MATCH requires sufficient positive closure")
        return cls("PROVEN_NO_MATCH", required_closure)

    def to_payload(self) -> dict[str, object]:
        return {"mode": self.mode, "required_closure": self.required_closure.value}

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "NegativeApplicabilityBurden":
        _expect_keys(payload, {"mode", "required_closure"}, "NegativeApplicabilityBurden")
        if payload["mode"] != "PROVEN_NO_MATCH":
            raise RegistryError("negative applicability mode must be PROVEN_NO_MATCH")
        try:
            closure = ClosureGrade(payload["required_closure"])
        except (ValueError, TypeError) as error:
            raise RegistryError("invalid negative-applicability closure") from error
        obj = cls.proven_no_match(closure)
        if obj.to_payload() != payload:
            raise RegistryError("NegativeApplicabilityBurden persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class ExternalReviewLane:
    lane_id: str
    minimum_instances: int
    independence_required: bool

    @classmethod
    def create(cls, lane_id: str, minimum_instances: int, independence_required: bool = True) -> "ExternalReviewLane":
        lane_id = _string(lane_id, "external review lane")
        if not isinstance(minimum_instances, int) or isinstance(minimum_instances, bool) or minimum_instances <= 0:
            raise RegistryError("external review lane minimum_instances must be positive")
        if independence_required is not True:
            raise RegistryError("mandatory external review lanes must require independence")
        return cls(lane_id, minimum_instances, True)

    def to_payload(self) -> dict[str, object]:
        return {
            "lane_id": self.lane_id,
            "minimum_instances": self.minimum_instances,
            "independence_required": self.independence_required,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ExternalReviewLane":
        _expect_keys(payload, {"lane_id", "minimum_instances", "independence_required"}, "ExternalReviewLane")
        obj = cls.create(payload["lane_id"], payload["minimum_instances"], payload["independence_required"])
        if obj.to_payload() != payload:
            raise RegistryError("ExternalReviewLane persisted payload is not canonical")
        return obj


def _requirements(values: Sequence[ContractRequirement], field: str) -> tuple[ContractRequirement, ...]:
    if isinstance(values, (str, bytes)):
        raise RegistryError(f"{field} must be a non-string sequence")
    for item in values:
        if not isinstance(item, ContractRequirement):
            raise RegistryError(f"{field} contains invalid item")
    result = tuple(sorted(values, key=lambda item: item.family))
    if len({item.family for item in result}) != len(result):
        raise RegistryError(f"{field} contains duplicate families")
    return result


def _collections(values: Sequence[CollectionRequirement]) -> tuple[CollectionRequirement, ...]:
    if isinstance(values, (str, bytes)):
        raise RegistryError("collections must be a non-string sequence")
    for item in values:
        if not isinstance(item, CollectionRequirement):
            raise RegistryError("collections contains invalid item")
    result = tuple(sorted(values, key=lambda item: item.family))
    if len({item.family for item in result}) != len(result):
        raise RegistryError("collections contains duplicate families")
    return result


def _external_lanes(values: Sequence[ExternalReviewLane]) -> tuple[ExternalReviewLane, ...]:
    if isinstance(values, (str, bytes)):
        raise RegistryError("external_review_lanes must be a non-string sequence")
    for item in values:
        if not isinstance(item, ExternalReviewLane):
            raise RegistryError("external_review_lanes contains invalid item")
    result = tuple(sorted(values, key=lambda item: item.lane_id))
    if len({item.lane_id for item in result}) != len(result):
        raise RegistryError("external_review_lanes contains duplicates")
    return result


@dataclass(frozen=True)
class ACRContract:
    schema_version: str
    contract_id: str
    generation: str
    domain: BoundedDomain
    applicability: ApplicabilityPredicate
    bound_subject_variables: tuple[str, ...]
    semantic_carrier_families: tuple[str, ...]
    consumer_interpretation_families: tuple[str, ...]
    affected_relation_families: tuple[str, ...]
    collections: tuple[CollectionRequirement, ...]
    mandatory_premises: tuple[ContractRequirement, ...]
    repeated_authority_premise_families: tuple[str, ...]
    mandatory_obligations: tuple[ContractRequirement, ...]
    admissible_proof_classes: tuple[str, ...]
    material_inputs: tuple[ContractRequirement, ...]
    coherence_rules: tuple[str, ...]
    temporal_rules: tuple[str, ...]
    mandatory_falsifier_families: tuple[str, ...]
    required_independence: tuple[str, ...]
    permitted_capabilities: tuple[str, ...]
    negative_applicability: NegativeApplicabilityBurden
    external_review_lanes: tuple[ExternalReviewLane, ...]
    unsupported_fallback: str
    mandatory: bool
    self_qualification_allowed: bool
    contract_id_hash: str

    @classmethod
    def create(
        cls,
        *,
        contract_id: str,
        generation: str,
        domain: BoundedDomain,
        applicability: ApplicabilityPredicate,
        bound_subject_variables: Sequence[str],
        semantic_carrier_families: Sequence[str],
        consumer_interpretation_families: Sequence[str],
        affected_relation_families: Sequence[str],
        collections: Sequence[CollectionRequirement],
        mandatory_premises: Sequence[ContractRequirement],
        repeated_authority_premise_families: Sequence[str],
        mandatory_obligations: Sequence[ContractRequirement],
        admissible_proof_classes: Sequence[str],
        material_inputs: Sequence[ContractRequirement],
        coherence_rules: Sequence[str],
        temporal_rules: Sequence[str],
        mandatory_falsifier_families: Sequence[str],
        required_independence: Sequence[str],
        permitted_capabilities: Sequence[str],
        negative_applicability: NegativeApplicabilityBurden,
        external_review_lanes: Sequence[ExternalReviewLane],
        unsupported_fallback: str,
    ) -> "ACRContract":
        contract_id = _string(contract_id, "contract_id")
        generation = _string(generation, "contract generation")
        if not isinstance(domain, BoundedDomain):
            raise RegistryError("domain must be a BoundedDomain")
        BoundedDomain.from_payload(domain.to_payload())
        if not isinstance(applicability, ApplicabilityPredicate):
            raise RegistryError("applicability must be declarative ApplicabilityPredicate")
        applicability.validate()
        if not isinstance(negative_applicability, NegativeApplicabilityBurden):
            raise RegistryError("negative applicability requires explicit PROVEN_NO_MATCH burden")
        NegativeApplicabilityBurden.from_payload(negative_applicability.to_payload())
        fallback = _string(unsupported_fallback, "unsupported_fallback")
        if fallback != "UNKNOWN":
            raise RegistryError("unsupported fallback must be UNKNOWN")
        values = {
            "bound_subject_variables": _identifiers(bound_subject_variables, "bound_subject_variables", allow_empty=False),
            "semantic_carrier_families": _identifiers(semantic_carrier_families, "semantic_carrier_families", allow_empty=False),
            "consumer_interpretation_families": _identifiers(consumer_interpretation_families, "consumer_interpretation_families"),
            "affected_relation_families": _identifiers(affected_relation_families, "affected_relation_families"),
            "collections": _collections(collections),
            "mandatory_premises": _requirements(mandatory_premises, "mandatory_premises"),
            "repeated_authority_premise_families": _identifiers(repeated_authority_premise_families, "repeated_authority_premise_families"),
            "mandatory_obligations": _requirements(mandatory_obligations, "mandatory_obligations"),
            "admissible_proof_classes": _identifiers(admissible_proof_classes, "admissible_proof_classes", allow_empty=False),
            "material_inputs": _requirements(material_inputs, "material_inputs"),
            "coherence_rules": _identifiers(coherence_rules, "coherence_rules"),
            "temporal_rules": _identifiers(temporal_rules, "temporal_rules"),
            "mandatory_falsifier_families": _identifiers(mandatory_falsifier_families, "mandatory_falsifier_families"),
            "required_independence": _identifiers(required_independence, "required_independence"),
            "permitted_capabilities": _identifiers(permitted_capabilities, "permitted_capabilities"),
            "external_review_lanes": _external_lanes(external_review_lanes),
        }
        body = {
            "schema_version": "sergeant.acr-contract.v1",
            "contract_id": contract_id,
            "generation": generation,
            "domain": domain.to_payload(),
            "applicability": applicability.to_payload(),
            **{key: [item.to_payload() for item in value] if key in {"collections", "mandatory_premises", "mandatory_obligations", "material_inputs", "external_review_lanes"} else list(value) for key, value in values.items()},
            "negative_applicability": negative_applicability.to_payload(),
            "unsupported_fallback": fallback,
            "mandatory": True,
            "self_qualification_allowed": False,
        }
        digest = sha256_id(body)
        return cls(
            "sergeant.acr-contract.v1", contract_id, generation, domain, applicability,
            values["bound_subject_variables"], values["semantic_carrier_families"], values["consumer_interpretation_families"], values["affected_relation_families"],
            values["collections"], values["mandatory_premises"], values["repeated_authority_premise_families"], values["mandatory_obligations"], values["admissible_proof_classes"],
            values["material_inputs"], values["coherence_rules"], values["temporal_rules"], values["mandatory_falsifier_families"],
            values["required_independence"], values["permitted_capabilities"], negative_applicability, values["external_review_lanes"],
            fallback, True, False, digest,
        )

    def constructor_fields(self) -> dict[str, object]:
        return {
            "contract_id": self.contract_id,
            "generation": self.generation,
            "domain": self.domain,
            "applicability": self.applicability,
            "bound_subject_variables": self.bound_subject_variables,
            "semantic_carrier_families": self.semantic_carrier_families,
            "consumer_interpretation_families": self.consumer_interpretation_families,
            "affected_relation_families": self.affected_relation_families,
            "collections": self.collections,
            "mandatory_premises": self.mandatory_premises,
            "repeated_authority_premise_families": self.repeated_authority_premise_families,
            "mandatory_obligations": self.mandatory_obligations,
            "admissible_proof_classes": self.admissible_proof_classes,
            "material_inputs": self.material_inputs,
            "coherence_rules": self.coherence_rules,
            "temporal_rules": self.temporal_rules,
            "mandatory_falsifier_families": self.mandatory_falsifier_families,
            "required_independence": self.required_independence,
            "permitted_capabilities": self.permitted_capabilities,
            "negative_applicability": self.negative_applicability,
            "external_review_lanes": self.external_review_lanes,
            "unsupported_fallback": self.unsupported_fallback,
        }

    def evaluate(self, context: ApplicabilityContext) -> ApplicabilityResult:
        return self.applicability.evaluate(context)

    def to_payload(self) -> dict[str, object]:
        fields = self.constructor_fields()
        return {
            "schema_version": self.schema_version,
            "contract_id": self.contract_id,
            "generation": self.generation,
            "domain": self.domain.to_payload(),
            "applicability": self.applicability.to_payload(),
            "bound_subject_variables": list(self.bound_subject_variables),
            "semantic_carrier_families": list(self.semantic_carrier_families),
            "consumer_interpretation_families": list(self.consumer_interpretation_families),
            "affected_relation_families": list(self.affected_relation_families),
            "collections": [item.to_payload() for item in self.collections],
            "mandatory_premises": [item.to_payload() for item in self.mandatory_premises],
            "repeated_authority_premise_families": list(self.repeated_authority_premise_families),
            "mandatory_obligations": [item.to_payload() for item in self.mandatory_obligations],
            "admissible_proof_classes": list(self.admissible_proof_classes),
            "material_inputs": [item.to_payload() for item in self.material_inputs],
            "coherence_rules": list(self.coherence_rules),
            "temporal_rules": list(self.temporal_rules),
            "mandatory_falsifier_families": list(self.mandatory_falsifier_families),
            "required_independence": list(self.required_independence),
            "permitted_capabilities": list(self.permitted_capabilities),
            "negative_applicability": self.negative_applicability.to_payload(),
            "external_review_lanes": [item.to_payload() for item in self.external_review_lanes],
            "unsupported_fallback": self.unsupported_fallback,
            "mandatory": self.mandatory,
            "self_qualification_allowed": self.self_qualification_allowed,
            "contract_id_hash": self.contract_id_hash,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ACRContract":
        required = {
            "schema_version", "contract_id", "generation", "domain", "applicability", "bound_subject_variables",
            "semantic_carrier_families", "consumer_interpretation_families", "affected_relation_families", "collections", "mandatory_premises", "repeated_authority_premise_families", "mandatory_obligations",
            "admissible_proof_classes", "material_inputs", "coherence_rules", "temporal_rules", "mandatory_falsifier_families",
            "required_independence", "permitted_capabilities", "negative_applicability", "external_review_lanes", "unsupported_fallback",
            "mandatory", "self_qualification_allowed", "contract_id_hash",
        }
        _expect_keys(payload, required, "ACRContract")
        if payload["schema_version"] != "sergeant.acr-contract.v1":
            raise RegistryError("unknown ACRContract schema")
        if payload["mandatory"] is not True:
            raise RegistryError("SAE-20 v1 ACR contract must remain mandatory")
        if payload["self_qualification_allowed"] is not False:
            raise RegistryError("candidate ACR contract cannot self-qualify")
        list_fields = [
            "bound_subject_variables", "semantic_carrier_families", "consumer_interpretation_families", "affected_relation_families", "collections", "mandatory_premises", "repeated_authority_premise_families",
            "mandatory_obligations", "admissible_proof_classes", "material_inputs", "coherence_rules", "temporal_rules",
            "mandatory_falsifier_families", "required_independence", "permitted_capabilities", "external_review_lanes",
        ]
        if any(not isinstance(payload[field], list) for field in list_fields):
            raise RegistryError("ACRContract sequence fields must be arrays")
        obj = cls.create(
            contract_id=payload["contract_id"], generation=payload["generation"],
            domain=BoundedDomain.from_payload(payload["domain"]), applicability=ApplicabilityPredicate.from_payload(payload["applicability"]),
            bound_subject_variables=payload["bound_subject_variables"], semantic_carrier_families=payload["semantic_carrier_families"],
            consumer_interpretation_families=payload["consumer_interpretation_families"], affected_relation_families=payload["affected_relation_families"],
            collections=tuple(CollectionRequirement.from_payload(x) for x in payload["collections"]),
            mandatory_premises=tuple(ContractRequirement.from_payload(x) for x in payload["mandatory_premises"]),
            repeated_authority_premise_families=payload["repeated_authority_premise_families"], mandatory_obligations=tuple(ContractRequirement.from_payload(x) for x in payload["mandatory_obligations"]),
            admissible_proof_classes=payload["admissible_proof_classes"],
            material_inputs=tuple(ContractRequirement.from_payload(x) for x in payload["material_inputs"]),
            coherence_rules=payload["coherence_rules"], temporal_rules=payload["temporal_rules"],
            mandatory_falsifier_families=payload["mandatory_falsifier_families"], required_independence=payload["required_independence"],
            permitted_capabilities=payload["permitted_capabilities"],
            negative_applicability=NegativeApplicabilityBurden.from_payload(payload["negative_applicability"]),
            external_review_lanes=tuple(ExternalReviewLane.from_payload(x) for x in payload["external_review_lanes"]),
            unsupported_fallback=payload["unsupported_fallback"],
        )
        if require_full_sha256(payload["contract_id_hash"], "contract_id_hash") != obj.contract_id_hash:
            raise RegistryError("contract_id_hash mismatch")
        if obj.to_payload() != payload:
            raise RegistryError("ACRContract persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class ACRContractEvaluation:
    contract_id: str
    contract_generation: str
    truth: ApplicabilityTruth
    unresolved_facts: tuple[str, ...]
    evaluation_present: bool


@dataclass(frozen=True)
class ACRRegistry:
    schema_version: str
    generation: str
    contracts: tuple[ACRContract, ...]
    registry_id: str

    @classmethod
    def create(cls, *, generation: str, contracts: Sequence[ACRContract]) -> "ACRRegistry":
        generation = _string(generation, "registry generation")
        if isinstance(contracts, (str, bytes)):
            raise RegistryError("contracts must be a non-string sequence")
        normalized = tuple(sorted(contracts, key=lambda item: (item.contract_id, item.generation)))
        for contract in normalized:
            if not isinstance(contract, ACRContract):
                raise RegistryError("registry contains invalid contract type")
            ACRContract.from_payload(contract.to_payload())
        contract_ids = [contract.contract_id for contract in normalized]
        if len(set(contract_ids)) != len(contract_ids):
            raise RegistryError("duplicate contract_id in registry")
        body = {
            "schema_version": "sergeant.acr-registry.v1",
            "generation": generation,
            "contracts": [contract.to_payload() for contract in normalized],
        }
        return cls("sergeant.acr-registry.v1", generation, normalized, sha256_id(body))

    def evaluate_all(self, contexts: Mapping[str, ApplicabilityContext]) -> tuple[ACRContractEvaluation, ...]:
        if not isinstance(contexts, Mapping):
            raise RegistryError("registry evaluation contexts must be a mapping")
        known = {contract.contract_id for contract in self.contracts}
        unknown = set(contexts) - known
        if unknown:
            raise RegistryError(f"evaluation supplied unknown contract IDs: {sorted(unknown)!r}")
        evaluations: list[ACRContractEvaluation] = []
        for contract in self.contracts:
            context = contexts.get(contract.contract_id)
            if context is None:
                evaluations.append(ACRContractEvaluation(
                    contract.contract_id, contract.generation, ApplicabilityTruth.UNKNOWN, ("<missing-evaluation>",), False
                ))
                continue
            if not isinstance(context, ApplicabilityContext):
                raise RegistryError(f"evaluation context for {contract.contract_id} has invalid type")
            result = contract.evaluate(context)
            evaluations.append(ACRContractEvaluation(
                contract.contract_id, contract.generation, result.truth, result.unresolved_facts, True
            ))
        return tuple(evaluations)

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "generation": self.generation,
            "contracts": [contract.to_payload() for contract in self.contracts],
            "registry_id": self.registry_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ACRRegistry":
        _expect_keys(payload, {"schema_version", "generation", "contracts", "registry_id"}, "ACRRegistry")
        if payload["schema_version"] != "sergeant.acr-registry.v1":
            raise RegistryError("unknown ACRRegistry schema")
        if not isinstance(payload["contracts"], list):
            raise RegistryError("registry contracts must be an array")
        obj = cls.create(generation=payload["generation"], contracts=tuple(ACRContract.from_payload(x) for x in payload["contracts"]))
        if require_full_sha256(payload["registry_id"], "registry_id") != obj.registry_id:
            raise RegistryError("registry_id mismatch")
        if obj.to_payload() != payload:
            raise RegistryError("ACRRegistry persisted payload is not canonical")
        return obj
