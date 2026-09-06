"""SAE-40 Judge Assurance Ledger and authority-bearing record identity.

This module amplifies Sergeant's existing Judge.  It does not create another
adjudicator or verdict engine.  Authority-bearing records bind the exact Review
World, RAB and scope with full SHA-256 identities; legacy ``finding_id`` values
remain presentation aliases only.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
import json
from typing import Any

from .review_world import ReviewWorldError, canonical_json_bytes, require_full_sha256, sha256_id


class AssuranceLedgerError(ReviewWorldError):
    """Raised when an assurance-ledger authority boundary is ambiguous."""


_MUTABLE_GENERATION_ALIASES = {"latest", "current", "head", "tip", "main", "master"}


class LedgerRecordKind(str, Enum):
    REVIEW_WORLD = "review_world"
    ACR_EVALUATION = "acr_evaluation"
    COLLECTION_CLOSURE = "collection_closure"
    CONTRACT_INSTANCE = "contract_instance"
    CLAIM = "claim"
    OBLIGATION = "obligation"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"
    FALSIFIER_INSTANCE = "falsifier_instance"
    CONTRADICTION = "contradiction"
    QUALIFICATION_EVIDENCE = "qualification_evidence"
    ADMISSION = "admission"
    INVALIDATION = "invalidation"
    VERDICT_LINEAGE = "verdict_lineage"


class LedgerEpistemicState(str, Enum):
    ASSERTED = "ASSERTED"
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    CONTRADICTED = "CONTRADICTED"
    INAPPLICABLE = "INAPPLICABLE"
    INVALIDATED = "INVALIDATED"


def _string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise AssuranceLedgerError(f"{field} must be a string")
    if not value or value != value.strip():
        raise AssuranceLedgerError(f"{field} must be canonical and non-empty")
    return value


def _generation(value: object, field: str = "generation") -> str:
    candidate = _string(value, field)
    if candidate.lower() in _MUTABLE_GENERATION_ALIASES:
        raise AssuranceLedgerError(f"{field} uses mutable authority alias {candidate!r}")
    return candidate


def _sha(value: object, field: str) -> str:
    try:
        return require_full_sha256(value, field)  # type: ignore[arg-type]
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise AssuranceLedgerError(str(exc)) from exc


def _sha_tuple(values: Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise AssuranceLedgerError(f"{field} must be a non-string iterable")
    out = tuple(sorted(_sha(value, field) for value in values))
    if len(set(out)) != len(out):
        raise AssuranceLedgerError(f"{field} contains duplicates")
    return out


def _presentation_ids(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise AssuranceLedgerError("presentation_ids must be a non-string iterable")
    out = tuple(sorted(_string(value, "presentation id") for value in values))
    return tuple(dict.fromkeys(out))


def _canonical_payload_json(payload: Mapping[str, object]) -> str:
    if not isinstance(payload, Mapping):
        raise AssuranceLedgerError("ledger payload must be an object")
    try:
        return canonical_json_bytes(payload).decode("utf-8")
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise AssuranceLedgerError(f"ledger payload is not canonical JSON: {exc}") from exc


def _payload_object(payload_json: str) -> dict[str, object]:
    try:
        decoded = json.loads(payload_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - constructor prevents it
        raise AssuranceLedgerError("stored ledger payload is invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise AssuranceLedgerError("stored ledger payload must decode to an object")
    return decoded


def _expect_keys(payload: Mapping[str, object], required: set[str], label: str) -> None:
    if not isinstance(payload, Mapping):
        raise AssuranceLedgerError(f"{label} must be an object")
    missing = required - set(payload)
    extra = set(payload) - required
    if missing:
        raise AssuranceLedgerError(f"{label} missing required fields: {sorted(missing)!r}")
    if extra:
        raise AssuranceLedgerError(f"{label} has unexpected fields: {sorted(extra)!r}")


@dataclass(frozen=True)
class LedgerRecord:
    schema_version: str
    kind: LedgerRecordKind
    review_world_id: str
    rab_id: str
    scope_id: str
    generation: str
    occurrence: int
    epistemic_state: LedgerEpistemicState
    authority_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    related_record_ids: tuple[str, ...]
    payload_json: str
    presentation_ids: tuple[str, ...]
    record_id: str

    @classmethod
    def create(
        cls,
        *,
        kind: LedgerRecordKind,
        review_world_id: str,
        rab_id: str,
        scope_id: str,
        generation: str,
        occurrence: int,
        epistemic_state: LedgerEpistemicState,
        authority_refs: Iterable[str] = (),
        provenance_refs: Iterable[str] = (),
        related_record_ids: Iterable[str] = (),
        payload: Mapping[str, object],
        presentation_ids: Iterable[str] = (),
    ) -> "LedgerRecord":
        if not isinstance(kind, LedgerRecordKind):
            raise AssuranceLedgerError("kind must be a LedgerRecordKind")
        world = _sha(review_world_id, "review_world_id")
        rab = _sha(rab_id, "rab_id")
        scope = _sha(scope_id, "scope_id")
        generation = _generation(generation, "record generation")
        if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 0:
            raise AssuranceLedgerError("occurrence must be a non-negative integer")
        if not isinstance(epistemic_state, LedgerEpistemicState):
            raise AssuranceLedgerError("epistemic_state must be a LedgerEpistemicState")
        authorities = _sha_tuple(authority_refs, "authority reference")
        provenance = _sha_tuple(provenance_refs, "provenance reference")
        related = _sha_tuple(related_record_ids, "related record id")
        payload_json = _canonical_payload_json(payload)
        aliases = _presentation_ids(presentation_ids)
        body = {
            "schema_version": "sergeant.assurance-ledger-record.v1",
            "kind": kind.value,
            "review_world_id": world,
            "rab_id": rab,
            "scope_id": scope,
            "generation": generation,
            "occurrence": occurrence,
            "epistemic_state": epistemic_state.value,
            "authority_refs": list(authorities),
            "provenance_refs": list(provenance),
            "related_record_ids": list(related),
            "payload": _payload_object(payload_json),
        }
        return cls(
            "sergeant.assurance-ledger-record.v1",
            kind,
            world,
            rab,
            scope,
            generation,
            occurrence,
            epistemic_state,
            authorities,
            provenance,
            related,
            payload_json,
            aliases,
            sha256_id(body),
        )

    def constructor_fields(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "review_world_id": self.review_world_id,
            "rab_id": self.rab_id,
            "scope_id": self.scope_id,
            "generation": self.generation,
            "occurrence": self.occurrence,
            "epistemic_state": self.epistemic_state,
            "authority_refs": self.authority_refs,
            "provenance_refs": self.provenance_refs,
            "related_record_ids": self.related_record_ids,
            "payload": self.payload(),
            "presentation_ids": self.presentation_ids,
        }

    def payload(self) -> dict[str, object]:
        # Return a fresh object; callers cannot mutate the authority snapshot.
        return _payload_object(self.payload_json)

    def authority_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind.value,
            "review_world_id": self.review_world_id,
            "rab_id": self.rab_id,
            "scope_id": self.scope_id,
            "generation": self.generation,
            "occurrence": self.occurrence,
            "epistemic_state": self.epistemic_state.value,
            "authority_refs": list(self.authority_refs),
            "provenance_refs": list(self.provenance_refs),
            "related_record_ids": list(self.related_record_ids),
            "payload": self.payload(),
        }

    def to_payload(self) -> dict[str, object]:
        return {
            **self.authority_payload(),
            "presentation_ids": list(self.presentation_ids),
            "record_id": self.record_id,
        }

    def validate(self) -> None:
        canonical = type(self).create(**self.constructor_fields())
        if canonical.record_id != _sha(self.record_id, "record_id"):
            raise AssuranceLedgerError("record_id mismatch")
        if canonical != self:
            raise AssuranceLedgerError("ledger record is non-canonical")

    def with_presentation_ids(self, presentation_ids: Iterable[str]) -> "LedgerRecord":
        return type(self).create(**{**self.constructor_fields(), "presentation_ids": presentation_ids})

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "LedgerRecord":
        _expect_keys(
            payload,
            {
                "schema_version", "kind", "review_world_id", "rab_id", "scope_id", "generation",
                "occurrence", "epistemic_state", "authority_refs", "provenance_refs",
                "related_record_ids", "payload", "presentation_ids", "record_id",
            },
            "LedgerRecord",
        )
        if payload["schema_version"] != "sergeant.assurance-ledger-record.v1":
            raise AssuranceLedgerError("unknown ledger record schema version")
        try:
            kind = LedgerRecordKind(payload["kind"])
            state = LedgerEpistemicState(payload["epistemic_state"])
        except (TypeError, ValueError) as exc:
            raise AssuranceLedgerError("invalid ledger record enum") from exc
        for field in ("authority_refs", "provenance_refs", "related_record_ids", "presentation_ids"):
            if not isinstance(payload[field], list):
                raise AssuranceLedgerError(f"{field} must be an array")
        if not isinstance(payload["payload"], Mapping):
            raise AssuranceLedgerError("payload must be an object")
        obj = cls.create(
            kind=kind,
            review_world_id=payload["review_world_id"],  # type: ignore[arg-type]
            rab_id=payload["rab_id"],  # type: ignore[arg-type]
            scope_id=payload["scope_id"],  # type: ignore[arg-type]
            generation=payload["generation"],  # type: ignore[arg-type]
            occurrence=payload["occurrence"],  # type: ignore[arg-type]
            epistemic_state=state,
            authority_refs=payload["authority_refs"],  # type: ignore[arg-type]
            provenance_refs=payload["provenance_refs"],  # type: ignore[arg-type]
            related_record_ids=payload["related_record_ids"],  # type: ignore[arg-type]
            payload=payload["payload"],  # type: ignore[arg-type]
            presentation_ids=payload["presentation_ids"],  # type: ignore[arg-type]
        )
        if _sha(payload["record_id"], "record_id") != obj.record_id:
            raise AssuranceLedgerError("record_id mismatch")
        if obj.to_payload() != dict(payload):
            raise AssuranceLedgerError("LedgerRecord persisted payload is not canonical")
        return obj


@dataclass(frozen=True)
class JudgeAssuranceLedger:
    schema_version: str
    review_world_id: str
    rab_id: str
    generation: str
    records: tuple[LedgerRecord, ...]
    parent_ledger_ids: tuple[str, ...]
    ledger_id: str

    @classmethod
    def create(
        cls,
        *,
        review_world_id: str,
        rab_id: str,
        generation: str,
        records: Iterable[LedgerRecord],
        parent_ledger_ids: Iterable[str] = (),
    ) -> "JudgeAssuranceLedger":
        world = _sha(review_world_id, "ledger review_world_id")
        rab = _sha(rab_id, "ledger rab_id")
        generation = _generation(generation, "ledger generation")
        if isinstance(records, (str, bytes)):
            raise AssuranceLedgerError("records must be a non-string iterable")
        canonical_by_id: dict[str, LedgerRecord] = {}
        for record in records:
            if not isinstance(record, LedgerRecord):
                raise AssuranceLedgerError("ledger contains an invalid record type")
            record.validate()
            if record.review_world_id != world:
                raise AssuranceLedgerError("ledger record belongs to a different Review World")
            if record.rab_id != rab:
                raise AssuranceLedgerError("ledger record belongs to a different RAB")
            existing = canonical_by_id.get(record.record_id)
            if existing is None:
                canonical_by_id[record.record_id] = record
            else:
                # Same authority identity: only presentation aliases may differ.
                if existing.authority_payload() != record.authority_payload():
                    raise AssuranceLedgerError("same record_id has conflicting authority payload")
                aliases = tuple(sorted(set(existing.presentation_ids) | set(record.presentation_ids)))
                canonical_by_id[record.record_id] = existing.with_presentation_ids(aliases)
        ordered = tuple(canonical_by_id[key] for key in sorted(canonical_by_id))
        record_ids = set(canonical_by_id)
        for record in ordered:
            missing_links = set(record.related_record_ids) - record_ids
            if missing_links:
                raise AssuranceLedgerError(
                    f"ledger record {record.record_id} has dangling related_record_ids: {sorted(missing_links)!r}"
                )
        parents = _sha_tuple(parent_ledger_ids, "parent ledger id")
        body = {
            "schema_version": "sergeant.judge-assurance-ledger.v1",
            "review_world_id": world,
            "rab_id": rab,
            "generation": generation,
            "records": [record.to_payload() for record in ordered],
            "parent_ledger_ids": list(parents),
        }
        return cls(
            "sergeant.judge-assurance-ledger.v1",
            world,
            rab,
            generation,
            ordered,
            parents,
            sha256_id(body),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "review_world_id": self.review_world_id,
            "rab_id": self.rab_id,
            "generation": self.generation,
            "records": [record.to_payload() for record in self.records],
            "parent_ledger_ids": list(self.parent_ledger_ids),
            "ledger_id": self.ledger_id,
        }

    def validate(self) -> None:
        canonical = type(self).create(
            review_world_id=self.review_world_id,
            rab_id=self.rab_id,
            generation=self.generation,
            records=self.records,
            parent_ledger_ids=self.parent_ledger_ids,
        )
        if canonical.ledger_id != _sha(self.ledger_id, "ledger_id"):
            raise AssuranceLedgerError("ledger_id mismatch")
        if canonical != self:
            raise AssuranceLedgerError("Judge assurance ledger is non-canonical")

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "JudgeAssuranceLedger":
        _expect_keys(
            payload,
            {"schema_version", "review_world_id", "rab_id", "generation", "records", "parent_ledger_ids", "ledger_id"},
            "JudgeAssuranceLedger",
        )
        if payload["schema_version"] != "sergeant.judge-assurance-ledger.v1":
            raise AssuranceLedgerError("unknown Judge assurance ledger schema version")
        if not isinstance(payload["records"], list) or not isinstance(payload["parent_ledger_ids"], list):
            raise AssuranceLedgerError("ledger records and parent_ledger_ids must be arrays")
        records = tuple(LedgerRecord.from_payload(item) for item in payload["records"] if isinstance(item, Mapping))
        if len(records) != len(payload["records"]):
            raise AssuranceLedgerError("ledger records contain a non-object entry")
        obj = cls.create(
            review_world_id=payload["review_world_id"],  # type: ignore[arg-type]
            rab_id=payload["rab_id"],  # type: ignore[arg-type]
            generation=payload["generation"],  # type: ignore[arg-type]
            records=records,
            parent_ledger_ids=payload["parent_ledger_ids"],  # type: ignore[arg-type]
        )
        if _sha(payload["ledger_id"], "ledger_id") != obj.ledger_id:
            raise AssuranceLedgerError("ledger_id mismatch")
        if obj.to_payload() != dict(payload):
            raise AssuranceLedgerError("JudgeAssuranceLedger persisted payload is not canonical")
        return obj

    def merge(self, other: "JudgeAssuranceLedger", *, generation: str) -> "JudgeAssuranceLedger":
        self.validate()
        if not isinstance(other, JudgeAssuranceLedger):
            raise AssuranceLedgerError("can merge only another JudgeAssuranceLedger")
        other.validate()
        if self.review_world_id != other.review_world_id:
            raise AssuranceLedgerError("cannot merge ledgers from different Review Worlds")
        if self.rab_id != other.rab_id:
            raise AssuranceLedgerError("cannot merge ledgers from different RABs")
        parents = set(self.parent_ledger_ids) | set(other.parent_ledger_ids) | {self.ledger_id, other.ledger_id}
        return type(self).create(
            review_world_id=self.review_world_id,
            rab_id=self.rab_id,
            generation=generation,
            records=(*self.records, *other.records),
            parent_ledger_ids=parents,
        )
