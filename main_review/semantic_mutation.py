"""SAE-130D semantic mutation / falsification qualification."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class MutationCampaignError(ValueError):
    """Raised when mutation evidence is malformed or noncanonical."""


class MutationKind(str, Enum):
    GUARD_DELETION = "guard_deletion"
    AUTHORITY_SUBSTITUTION = "authority_substitution"
    ROUTE_ADDITION = "route_addition"
    MISSING_BINDING_OR_MEMBER = "missing_binding_or_member"
    RECOVERY_BREAKAGE = "recovery_breakage"
    GENERATION_OR_STATE_MUTATION = "generation_or_state_mutation"
    EVIDENCE_OMISSION = "evidence_omission"
    NO_OP_DETECTION = "no_op_detection"


def _canonical_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise MutationCampaignError(f"{field} must be canonical")
    return value


@dataclass(frozen=True)
class MutationProbe:
    mutant_id: str
    kind: MutationKind
    baseline_identity: str
    mutated_identity: str
    killed: bool
    detector: str

    @classmethod
    def create(
        cls,
        *,
        mutant_id: str,
        kind: MutationKind,
        baseline_identity: str,
        mutated_identity: str,
        killed: bool,
        detector: str,
    ) -> "MutationProbe":
        mutant_id = _canonical_text(mutant_id, field="mutant_id")
        if not isinstance(kind, MutationKind):
            raise MutationCampaignError("kind must be canonical")
        baseline_identity = _canonical_text(baseline_identity, field="baseline_identity")
        mutated_identity = _canonical_text(mutated_identity, field="mutated_identity")
        if type(killed) is not bool:
            raise MutationCampaignError("killed must be boolean")
        detector = _canonical_text(detector, field="detector")

        changed = baseline_identity != mutated_identity
        if kind is MutationKind.NO_OP_DETECTION:
            if changed:
                raise MutationCampaignError("no-op detector mutant changed semantics")
        elif not changed:
            raise MutationCampaignError("material mutant is a no-op")

        return cls(
            mutant_id=mutant_id,
            kind=kind,
            baseline_identity=baseline_identity,
            mutated_identity=mutated_identity,
            killed=killed,
            detector=detector,
        )


@dataclass(frozen=True)
class MutationCampaignResult:
    qualified: bool
    killed_mutants: tuple[str, ...]
    surviving_mutants: tuple[str, ...]
    missing_required_kinds: tuple[str, ...]


@dataclass(frozen=True)
class SemanticMutationCampaign:
    probes: tuple[MutationProbe, ...]

    @classmethod
    def create(cls, *, probes: Sequence[MutationProbe]) -> "SemanticMutationCampaign":
        values = tuple(probes)
        if any(not isinstance(probe, MutationProbe) for probe in values):
            raise MutationCampaignError("campaign contains noncanonical probe")
        identities = [probe.mutant_id for probe in values]
        if len(identities) != len(set(identities)):
            raise MutationCampaignError("duplicate mutant identity")
        return cls(probes=values)

    def evaluate(self) -> MutationCampaignResult:
        present = {probe.kind for probe in self.probes}
        missing = tuple(kind.value for kind in MutationKind if kind not in present)
        killed = tuple(sorted(probe.mutant_id for probe in self.probes if probe.killed))
        surviving = tuple(sorted(probe.mutant_id for probe in self.probes if not probe.killed))
        return MutationCampaignResult(
            qualified=not missing and not surviving,
            killed_mutants=killed,
            surviving_mutants=surviving,
            missing_required_kinds=missing,
        )
