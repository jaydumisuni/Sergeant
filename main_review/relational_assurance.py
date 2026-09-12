"""SAE-130E relational assurance qualification."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class RelationalAssuranceError(ValueError):
    """Raised when relational evidence is malformed or noncanonical."""


class RelationKind(str, Enum):
    OLD_VS_NEW = "old_vs_new"
    PRODUCER_VS_CONSUMER = "producer_vs_consumer"
    SERIALIZER_VS_PARSER = "serializer_vs_parser"
    AUTHORIZED_VS_UNAUTHORIZED_WORLD = "authorized_vs_unauthorized_world"
    SINGLE_EXECUTION_VS_RETRY = "single_execution_vs_retry"
    PYTHON_VS_RUST = "python_vs_rust"
    EXPECTED_VS_OBSERVED_EFFECT_SET = "expected_vs_observed_effect_set"


def _canonical(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RelationalAssuranceError(f"{field} must be canonical")
    return value


@dataclass(frozen=True)
class RelationProbe:
    probe_id: str
    kind: RelationKind
    left_identity: str
    right_identity: str
    relation_holds: bool
    equivalent: bool
    detector: str

    @classmethod
    def create(cls, *, probe_id: str, kind: RelationKind, left_identity: str, right_identity: str, relation_holds: bool, equivalent: bool, detector: str) -> "RelationProbe":
        probe_id = _canonical(probe_id, field="probe_id")
        if not isinstance(kind, RelationKind):
            raise RelationalAssuranceError("kind must be canonical")
        left_identity = _canonical(left_identity, field="left_identity")
        right_identity = _canonical(right_identity, field="right_identity")
        if type(relation_holds) is not bool or type(equivalent) is not bool:
            raise RelationalAssuranceError("relation flags must be boolean")
        detector = _canonical(detector, field="detector")
        if kind is RelationKind.PYTHON_VS_RUST:
            if not equivalent:
                raise RelationalAssuranceError("cross-runtime relation requires declared semantic equivalence")
        elif left_identity == right_identity:
            raise RelationalAssuranceError("material relation must compare distinct worlds")
        return cls(probe_id, kind, left_identity, right_identity, relation_holds, equivalent, detector)


@dataclass(frozen=True)
class RelationalAssuranceResult:
    qualified: bool
    passed_relations: tuple[str, ...]
    failed_relations: tuple[str, ...]
    missing_required_kinds: tuple[str, ...]


@dataclass(frozen=True)
class RelationalAssuranceCampaign:
    probes: tuple[RelationProbe, ...]

    @classmethod
    def create(cls, *, probes: Sequence[RelationProbe]) -> "RelationalAssuranceCampaign":
        values = tuple(probes)
        if any(not isinstance(p, RelationProbe) for p in values):
            raise RelationalAssuranceError("campaign contains noncanonical probe")
        ids = [p.probe_id for p in values]
        if len(ids) != len(set(ids)):
            raise RelationalAssuranceError("duplicate relation identity")
        kinds = [p.kind for p in values]
        if len(kinds) != len(set(kinds)):
            raise RelationalAssuranceError("duplicate relation kind")
        return cls(values)

    def evaluate(self) -> RelationalAssuranceResult:
        present = {p.kind for p in self.probes}
        missing = tuple(k.value for k in RelationKind if k not in present)
        passed = tuple(sorted(p.probe_id for p in self.probes if p.relation_holds))
        failed = tuple(sorted(p.probe_id for p in self.probes if not p.relation_holds))
        return RelationalAssuranceResult(qualified=not missing and not failed, passed_relations=passed, failed_relations=failed, missing_required_kinds=missing)
