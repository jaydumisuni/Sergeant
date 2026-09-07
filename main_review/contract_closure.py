"""SAE-70 RED interface surface.

This file exists only to make the RED contract importable so the repository can
prove failure at the missing contract-closure behavior rather than at module
collection.  The next TDD generation replaces these deliberate
``NotImplementedError`` boundaries with the minimal implementation required by
``tests/test_contract_closure.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .assurance_contract_registry import (
    ACRContract,
    ACRRegistry,
    ApplicabilityContext,
    ClosureGrade,
)
from .review_world import ReviewWorldError


class ContractClosureError(ReviewWorldError):
    """Raised for malformed SAE-70 contract-closure authority inputs."""


@dataclass(frozen=True)
class ContractInstanceEnumeration:
    contract_id: str
    contract_generation: str
    bindings: tuple[tuple[tuple[str, str], ...], ...]
    closure: ClosureGrade
    source_basis_id: str
    enumeration_id: str

    @classmethod
    def create(
        cls,
        *,
        contract: ACRContract,
        bindings: tuple[Mapping[str, str], ...],
        closure: ClosureGrade,
        source_basis_id: str,
    ) -> "ContractInstanceEnumeration":
        raise NotImplementedError("SAE-70 contract instance enumeration is not implemented")


@dataclass(frozen=True)
class ProvenNoMatch:
    contract_id: str
    contract_generation: str
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
        raise NotImplementedError("SAE-70 PROVEN_NO_MATCH is not implemented")


def compile_contract_closure(
    *,
    registry: ACRRegistry,
    contexts: Mapping[str, ApplicabilityContext],
    instance_enumerations: Mapping[str, ContractInstanceEnumeration],
    proven_no_match: Mapping[str, ProvenNoMatch],
):
    raise NotImplementedError("SAE-70 total contract-instance-obligation closure is not implemented")
