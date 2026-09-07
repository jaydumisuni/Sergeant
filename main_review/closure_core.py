"""SAE-50 Total Coverage and Total Set-Valued Closure core.

The core never infers completeness from a convenient subset. Positive EXACT
closure requires an externally rooted exact basis plus a matching complete
witness. Resource exhaustion and uncertain bases conserve UNKNOWN/PARTIAL.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .assurance_contract_registry import ClosureGrade, CollectionSemantics
from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class ClosureCoreError(ReviewWorldError):
    """Raised when collection-closure authority is incomplete or invalidated."""


def _sha(value: object, field: str) -> str:
    try:
        return require_full_sha256(value, field)  # type: ignore[arg-type]
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise ClosureCoreError(str(exc)) from exc


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ClosureCoreError(f"{field} must be canonical and non-empty")
    return value


def _members(values: Iterable[str], semantics: CollectionSemantics, field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ClosureCoreError(f"{field} must be a non-string iterable")
    raw = tuple(_string(value, field) for value in values)
    if semantics is CollectionSemantics.SET:
        if len(set(raw)) != len(raw):
            raise ClosureCoreError(f"{field} SET contains duplicate members")
        return tuple(sorted(raw))
    if semantics is CollectionSemantics.MULTISET:
        return tuple(sorted(raw))
    if semantics is CollectionSemantics.ORDER:
        return raw
    raise ClosureCoreError("unsupported collection semantics")


def _member_root(semantics: CollectionSemantics, members: tuple[str, ...]) -> str:
    return sha256_id({
        "schema_version": "sergeant.closure-members.v1",
        "semantics": semantics.value,
        "members": list(members),
    })


@dataclass(frozen=True)
class ClosureBasis:
    schema_version: str
    source_basis_id: str
    source_basis_kind: str
    semantics: CollectionSemantics
    members: tuple[str, ...]
    grade: ClosureGrade
    member_root: str
    basis_id: str

    @classmethod
    def create(
        cls,
        *,
        source_basis_id: str,
        source_basis_kind: str,
        semantics: CollectionSemantics,
        members: Iterable[str],
        grade: ClosureGrade,
    ) -> "ClosureBasis":
        source = _sha(source_basis_id, "source_basis_id")
        kind = _string(source_basis_kind, "source_basis_kind")
        if kind == "self_declared":
            raise ClosureCoreError("self-defining universe cannot provide positive closure authority")
        if not isinstance(semantics, CollectionSemantics):
            raise ClosureCoreError("semantics must be CollectionSemantics")
        if not isinstance(grade, ClosureGrade):
            raise ClosureCoreError("grade must be ClosureGrade")
        canonical_members = _members(members, semantics, "basis member")
        root = _member_root(semantics, canonical_members)
        body = {
            "schema_version": "sergeant.closure-basis.v1",
            "source_basis_id": source,
            "source_basis_kind": kind,
            "semantics": semantics.value,
            "members": list(canonical_members),
            "grade": grade.value,
            "member_root": root,
        }
        return cls(
            "sergeant.closure-basis.v1", source, kind, semantics,
            canonical_members, grade, root, sha256_id(body),
        )


@dataclass(frozen=True)
class ClosureWitness:
    schema_version: str
    basis_id: str
    members: tuple[str, ...]
    declared_complete: bool
    witness_id: str

    @classmethod
    def create(
        cls,
        *,
        basis_id: str,
        members: Iterable[str],
        declared_complete: bool,
    ) -> "ClosureWitness":
        basis = _sha(basis_id, "witness basis_id")
        if not isinstance(declared_complete, bool):
            raise ClosureCoreError("declared_complete must be boolean")
        # Witness member order is preserved here. Evaluation canonicalizes it
        # under the basis semantics, which prevents a witness from choosing its
        # own semantics while still allowing ORDER to remain material.
        if isinstance(members, (str, bytes)):
            raise ClosureCoreError("witness members must be a non-string iterable")
        raw = tuple(_string(value, "witness member") for value in members)
        body = {
            "schema_version": "sergeant.closure-witness.v1",
            "basis_id": basis,
            "members": list(raw),
            "declared_complete": declared_complete,
        }
        return cls("sergeant.closure-witness.v1", basis, raw, declared_complete, sha256_id(body))


@dataclass(frozen=True)
class ClosureCertificate:
    schema_version: str
    basis_id: str
    semantics: CollectionSemantics
    member_root: str
    witness_id: str
    certificate_id: str

    def validate_against(self, basis: ClosureBasis) -> None:
        if not isinstance(basis, ClosureBasis):
            raise ClosureCoreError("closure certificate requires canonical basis")
        if basis.basis_id != self.basis_id or basis.member_root != self.member_root or basis.semantics is not self.semantics:
            raise ClosureCoreError("closure certificate invalidated by late member, basis, or semantics change")


@dataclass(frozen=True)
class ClosureResult:
    grade: ClosureGrade
    complete: bool
    proven_empty: bool
    blockers: tuple[str, ...]
    certificate: ClosureCertificate | None


def _same_collection(semantics: CollectionSemantics, expected: tuple[str, ...], observed: tuple[str, ...]) -> bool:
    if semantics is CollectionSemantics.SET:
        return set(expected) == set(observed) and len(expected) == len(set(observed))
    if semantics is CollectionSemantics.MULTISET:
        return Counter(expected) == Counter(observed)
    return expected == observed


def _difference_blockers(semantics: CollectionSemantics, expected: tuple[str, ...], observed: tuple[str, ...]) -> tuple[str, ...]:
    if semantics is CollectionSemantics.ORDER and expected != observed:
        return ("member order does not match exact basis",)
    expected_counts = Counter(expected)
    observed_counts = Counter(observed)
    missing = tuple(sorted((expected_counts - observed_counts).elements()))
    extra = tuple(sorted((observed_counts - expected_counts).elements()))
    blockers: list[str] = []
    if missing:
        blockers.append(f"missing basis members: {missing!r}")
    if extra:
        blockers.append(f"unexpected witness members: {extra!r}")
    if not blockers:
        blockers.append("collection witness does not match basis semantics")
    return tuple(blockers)


def evaluate_closure(*, basis: ClosureBasis, witness: ClosureWitness) -> ClosureResult:
    if not isinstance(basis, ClosureBasis) or not isinstance(witness, ClosureWitness):
        raise ClosureCoreError("canonical closure basis and witness are required")
    if witness.basis_id != basis.basis_id:
        raise ClosureCoreError("closure witness is bound to a different basis")
    observed = _members(witness.members, basis.semantics, "witness member")
    same = _same_collection(basis.semantics, basis.members, observed)
    blockers: list[str] = []
    if not witness.declared_complete:
        blockers.append("witness does not declare complete enumeration")
    if not same:
        blockers.extend(_difference_blockers(basis.semantics, basis.members, observed))
    if basis.grade is not ClosureGrade.EXACT:
        blockers.append(f"source basis closure grade is {basis.grade.value}, not EXACT")
    complete = basis.grade is ClosureGrade.EXACT and witness.declared_complete and same
    if complete:
        body = {
            "schema_version": "sergeant.closure-certificate.v1",
            "basis_id": basis.basis_id,
            "semantics": basis.semantics.value,
            "member_root": basis.member_root,
            "witness_id": witness.witness_id,
        }
        certificate = ClosureCertificate(
            "sergeant.closure-certificate.v1", basis.basis_id, basis.semantics,
            basis.member_root, witness.witness_id, sha256_id(body),
        )
        return ClosureResult(ClosureGrade.EXACT, True, not basis.members, (), certificate)
    if basis.grade is ClosureGrade.UNKNOWN:
        grade = ClosureGrade.UNKNOWN
    elif basis.grade is ClosureGrade.PARTIAL:
        grade = ClosureGrade.PARTIAL
    elif basis.grade is ClosureGrade.CONSERVATIVE_SUPERSET:
        grade = ClosureGrade.CONSERVATIVE_SUPERSET
    else:
        grade = ClosureGrade.PARTIAL
    return ClosureResult(grade, False, False, tuple(blockers), None)


@dataclass(frozen=True)
class AffectedRelationFixpoint:
    members: tuple[str, ...]
    grade: ClosureGrade
    resource_exhausted: bool
    operations: int
    fixpoint_id: str


def affected_relation_fixpoint(
    *,
    seeds: Iterable[str],
    edges: Iterable[tuple[str, str]],
    budget: int,
) -> AffectedRelationFixpoint:
    if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
        raise ClosureCoreError("fixpoint budget must be a positive integer")
    if isinstance(seeds, (str, bytes)) or isinstance(edges, (str, bytes)):
        raise ClosureCoreError("fixpoint seeds/edges must be non-string iterables")
    reached = {_string(seed, "fixpoint seed") for seed in seeds}
    normalized_edges: list[tuple[str, str]] = []
    for edge in edges:
        if not isinstance(edge, tuple) or len(edge) != 2:
            raise ClosureCoreError("affected relation edge must be a pair")
        normalized_edges.append((_string(edge[0], "edge source"), _string(edge[1], "edge target")))
    operations = 0
    changed = True
    exhausted = False
    while changed:
        changed = False
        for source, target in normalized_edges:
            if source not in reached or target in reached:
                continue
            if operations >= budget:
                exhausted = True
                changed = False
                break
            operations += 1
            reached.add(target)
            changed = True
        if exhausted:
            break
    members = tuple(sorted(reached))
    grade = ClosureGrade.UNKNOWN if exhausted else ClosureGrade.EXACT
    body = {
        "schema_version": "sergeant.affected-relation-fixpoint.v1",
        "members": list(members),
        "grade": grade.value,
        "resource_exhausted": exhausted,
        "operations": operations,
    }
    return AffectedRelationFixpoint(members, grade, exhausted, operations, sha256_id(body))
