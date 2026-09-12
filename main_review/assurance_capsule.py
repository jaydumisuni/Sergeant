"""SAE-110 content-addressed Assurance Capsule and exact recovery protocol."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .owner_risk import EngineeringVerdict, EngineeringVerdictRecord
from .review_world import ReviewWorldError, canonical_json_bytes, require_full_sha256, sha256_id

ADMISSIBLE = "ADMISSIBLE"
INADMISSIBLE = "INADMISSIBLE"


class AssuranceCapsuleError(ReviewWorldError):
    """Raised when capsule authority, currentness, or durable replay is invalid."""


def _sha(value: object, field: str) -> str:
    try:
        return require_full_sha256(value, field)  # type: ignore[arg-type]
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise AssuranceCapsuleError(str(exc)) from exc


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AssuranceCapsuleError(f"{field} must be canonical and non-empty")
    return value


def _ids(values: Sequence[str], field: str) -> tuple[str, ...]:
    normalized = tuple(_sha(value, field) for value in values)
    if normalized != tuple(sorted(set(normalized))):
        raise AssuranceCapsuleError(f"{field} must be unique canonical sorted authority IDs")
    return normalized


@dataclass(frozen=True)
class CollectionCommitment:
    schema_version: str
    name: str
    root_id: str
    closure_witness_id: str
    commitment_id: str

    @classmethod
    def create(cls, *, name: str, root_id: str, closure_witness_id: str) -> "CollectionCommitment":
        name = _text(name, "collection name")
        root_id = _sha(root_id, "collection root")
        if not closure_witness_id:
            raise AssuranceCapsuleError("collection closure witness is required")
        closure_witness_id = _sha(closure_witness_id, "collection closure witness")
        body = {
            "schema_version": "sergeant.sae110-collection-commitment.v1",
            "name": name,
            "root_id": root_id,
            "closure_witness_id": closure_witness_id,
        }
        return cls(body["schema_version"], name, root_id, closure_witness_id, sha256_id(body))

    def to_payload(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "root_id": self.root_id,
            "closure_witness_id": self.closure_witness_id,
            "commitment_id": self.commitment_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "CollectionCommitment":
        value = cls.create(
            name=payload.get("name"),  # type: ignore[arg-type]
            root_id=payload.get("root_id"),  # type: ignore[arg-type]
            closure_witness_id=payload.get("closure_witness_id"),  # type: ignore[arg-type]
        )
        if payload.get("schema_version") != value.schema_version or payload.get("commitment_id") != value.commitment_id:
            raise AssuranceCapsuleError("collection commitment identity mismatch")
        if dict(payload) != value.to_payload():
            raise AssuranceCapsuleError("collection commitment payload is non-canonical")
        return value


def _verdict_payload(value: EngineeringVerdictRecord) -> dict[str, str]:
    return {
        "schema_version": value.schema_version,
        "review_world_id": value.review_world_id,
        "evidence_root_id": value.evidence_root_id,
        "sergeant_authority_id": value.sergeant_authority_id,
        "verdict": value.verdict.value,
        "record_id": value.record_id,
    }


def _verdict_from_payload(payload: Mapping[str, object]) -> EngineeringVerdictRecord:
    try:
        verdict = EngineeringVerdict(str(payload["verdict"]))
        value = EngineeringVerdictRecord.create(
            review_world_id=str(payload["review_world_id"]),
            evidence_root_id=str(payload["evidence_root_id"]),
            sergeant_authority_id=str(payload["sergeant_authority_id"]),
            verdict=verdict,
        )
    except (KeyError, ValueError, TypeError, ReviewWorldError) as exc:
        raise AssuranceCapsuleError(f"engineering verdict payload is invalid: {exc}") from exc
    if payload.get("schema_version") != value.schema_version or payload.get("record_id") != value.record_id:
        raise AssuranceCapsuleError("engineering verdict identity mismatch")
    if dict(payload) != _verdict_payload(value):
        raise AssuranceCapsuleError("engineering verdict payload is non-canonical")
    return value


@dataclass(frozen=True)
class AssuranceCapsuleRecord:
    schema_version: str
    review_world_id: str
    rab_id: str
    acr_generation: str
    scope_id: str
    domain_id: str
    contract_evaluation_root: str
    contract_instance: CollectionCommitment
    obligations: CollectionCommitment
    ledger: CollectionCommitment
    evidence: CollectionCommitment
    admitted_finding_ids: tuple[str, ...]
    unknown_ids: tuple[str, ...]
    qualification_generation: str
    facility_generation: str
    rust_admissibility: str
    engineering_verdict: EngineeringVerdictRecord
    subject_generation: str
    current_generation: str
    provenance_root_id: str
    created_at_utc: str
    capsule_id: str

    @classmethod
    def create(
        cls, *, review_world_id: str, rab_id: str, acr_generation: str,
        scope_id: str, domain_id: str, contract_evaluation_root: str,
        contract_instance: CollectionCommitment, obligations: CollectionCommitment,
        ledger: CollectionCommitment, evidence: CollectionCommitment,
        admitted_finding_ids: Sequence[str], unknown_ids: Sequence[str],
        qualification_generation: str, facility_generation: str, rust_admissibility: str,
        engineering_verdict: EngineeringVerdictRecord, subject_generation: str,
        current_generation: str, provenance_root_id: str, created_at_utc: str,
    ) -> "AssuranceCapsuleRecord":
        review_world_id = _sha(review_world_id, "review_world_id")
        rab_id = _sha(rab_id, "rab_id")
        scope_id = _sha(scope_id, "scope_id")
        domain_id = _sha(domain_id, "domain_id")
        contract_evaluation_root = _sha(contract_evaluation_root, "contract_evaluation_root")
        provenance_root_id = _sha(provenance_root_id, "provenance_root_id")
        acr_generation = _text(acr_generation, "acr_generation")
        qualification_generation = _text(qualification_generation, "qualification_generation")
        facility_generation = _text(facility_generation, "facility_generation")
        subject_generation = _text(subject_generation, "subject_generation")
        current_generation = _text(current_generation, "current_generation")
        created_at_utc = _text(created_at_utc, "created_at_utc")
        if not created_at_utc.endswith("Z"):
            raise AssuranceCapsuleError("created_at_utc must be explicit UTC")
        if rust_admissibility not in {ADMISSIBLE, INADMISSIBLE}:
            raise AssuranceCapsuleError("rust admissibility must be ADMISSIBLE or INADMISSIBLE")
        if not isinstance(engineering_verdict, EngineeringVerdictRecord):
            raise AssuranceCapsuleError("engineering verdict must be an EngineeringVerdictRecord")
        if engineering_verdict.review_world_id != review_world_id:
            raise AssuranceCapsuleError("engineering verdict Review World does not match capsule")
        commitments = (contract_instance, obligations, ledger, evidence)
        if not all(isinstance(item, CollectionCommitment) for item in commitments):
            raise AssuranceCapsuleError("capsule collection commitments must be canonical")
        expected_names = ("contract_instances", "expected_obligations", "judge_ledger", "evidence")
        if tuple(item.name for item in commitments) != expected_names:
            raise AssuranceCapsuleError("capsule collection commitment roster is non-canonical")
        admitted = _ids(admitted_finding_ids, "admitted finding ID")
        unknowns = _ids(unknown_ids, "UNKNOWN ID")
        body = {
            "schema_version": "sergeant.sae110-assurance-capsule.v1",
            "review_world_id": review_world_id,
            "rab_id": rab_id,
            "acr_generation": acr_generation,
            "scope_id": scope_id,
            "domain_id": domain_id,
            "contract_evaluation_root": contract_evaluation_root,
            "contract_instance": contract_instance.to_payload(),
            "obligations": obligations.to_payload(),
            "ledger": ledger.to_payload(),
            "evidence": evidence.to_payload(),
            "admitted_finding_ids": list(admitted),
            "unknown_ids": list(unknowns),
            "qualification_generation": qualification_generation,
            "facility_generation": facility_generation,
            "rust_admissibility": rust_admissibility,
            "engineering_verdict": _verdict_payload(engineering_verdict),
            "subject_generation": subject_generation,
            "current_generation": current_generation,
            "provenance_root_id": provenance_root_id,
            "created_at_utc": created_at_utc,
        }
        return cls(
            body["schema_version"], review_world_id, rab_id, acr_generation, scope_id, domain_id,
            contract_evaluation_root, contract_instance, obligations, ledger, evidence, admitted, unknowns,
            qualification_generation, facility_generation, rust_admissibility, engineering_verdict,
            subject_generation, current_generation, provenance_root_id, created_at_utc, sha256_id(body),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "review_world_id": self.review_world_id,
            "rab_id": self.rab_id,
            "acr_generation": self.acr_generation,
            "scope_id": self.scope_id,
            "domain_id": self.domain_id,
            "contract_evaluation_root": self.contract_evaluation_root,
            "contract_instance": self.contract_instance.to_payload(),
            "obligations": self.obligations.to_payload(),
            "ledger": self.ledger.to_payload(),
            "evidence": self.evidence.to_payload(),
            "admitted_finding_ids": list(self.admitted_finding_ids),
            "unknown_ids": list(self.unknown_ids),
            "qualification_generation": self.qualification_generation,
            "facility_generation": self.facility_generation,
            "rust_admissibility": self.rust_admissibility,
            "engineering_verdict": _verdict_payload(self.engineering_verdict),
            "subject_generation": self.subject_generation,
            "current_generation": self.current_generation,
            "provenance_root_id": self.provenance_root_id,
            "created_at_utc": self.created_at_utc,
            "capsule_id": self.capsule_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "AssuranceCapsuleRecord":
        try:
            value = cls.create(
                review_world_id=payload["review_world_id"], rab_id=payload["rab_id"],  # type: ignore[arg-type]
                acr_generation=payload["acr_generation"], scope_id=payload["scope_id"],  # type: ignore[arg-type]
                domain_id=payload["domain_id"], contract_evaluation_root=payload["contract_evaluation_root"],  # type: ignore[arg-type]
                contract_instance=CollectionCommitment.from_payload(payload["contract_instance"]),  # type: ignore[arg-type]
                obligations=CollectionCommitment.from_payload(payload["obligations"]),  # type: ignore[arg-type]
                ledger=CollectionCommitment.from_payload(payload["ledger"]),  # type: ignore[arg-type]
                evidence=CollectionCommitment.from_payload(payload["evidence"]),  # type: ignore[arg-type]
                admitted_finding_ids=payload["admitted_finding_ids"], unknown_ids=payload["unknown_ids"],  # type: ignore[arg-type]
                qualification_generation=payload["qualification_generation"], facility_generation=payload["facility_generation"],  # type: ignore[arg-type]
                rust_admissibility=payload["rust_admissibility"],  # type: ignore[arg-type]
                engineering_verdict=_verdict_from_payload(payload["engineering_verdict"]),  # type: ignore[arg-type]
                subject_generation=payload["subject_generation"], current_generation=payload["current_generation"],  # type: ignore[arg-type]
                provenance_root_id=payload["provenance_root_id"], created_at_utc=payload["created_at_utc"],  # type: ignore[arg-type]
            )
        except KeyError as exc:
            raise AssuranceCapsuleError(f"capsule payload missing {exc.args[0]}") from exc
        if payload.get("schema_version") != value.schema_version or payload.get("capsule_id") != value.capsule_id:
            raise AssuranceCapsuleError("capsule identity mismatch")
        if dict(payload) != value.to_payload():
            raise AssuranceCapsuleError("capsule payload is non-canonical")
        return value


@dataclass(frozen=True)
class InvalidationRecord:
    schema_version: str
    capsule_id: str
    reason: str
    provenance_escape_id: str
    invalidated_at_utc: str
    record_id: str

    @classmethod
    def create(cls, *, capsule_id: str, reason: str, provenance_escape_id: str, invalidated_at_utc: str) -> "InvalidationRecord":
        capsule_id = _sha(capsule_id, "capsule_id")
        reason = _text(reason, "invalidation reason")
        provenance_escape_id = _sha(provenance_escape_id, "provenance_escape_id")
        invalidated_at_utc = _text(invalidated_at_utc, "invalidated_at_utc")
        if not invalidated_at_utc.endswith("Z"):
            raise AssuranceCapsuleError("invalidated_at_utc must be explicit UTC")
        body = {
            "schema_version": "sergeant.sae110-capsule-invalidation.v1",
            "capsule_id": capsule_id,
            "reason": reason,
            "provenance_escape_id": provenance_escape_id,
            "invalidated_at_utc": invalidated_at_utc,
        }
        return cls(body["schema_version"], capsule_id, reason, provenance_escape_id, invalidated_at_utc, sha256_id(body))

    def to_payload(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version, "capsule_id": self.capsule_id,
            "reason": self.reason, "provenance_escape_id": self.provenance_escape_id,
            "invalidated_at_utc": self.invalidated_at_utc, "record_id": self.record_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "InvalidationRecord":
        value = cls.create(
            capsule_id=payload.get("capsule_id"), reason=payload.get("reason"),  # type: ignore[arg-type]
            provenance_escape_id=payload.get("provenance_escape_id"),  # type: ignore[arg-type]
            invalidated_at_utc=payload.get("invalidated_at_utc"),  # type: ignore[arg-type]
        )
        if payload.get("schema_version") != value.schema_version or payload.get("record_id") != value.record_id:
            raise AssuranceCapsuleError("invalidation identity mismatch")
        if dict(payload) != value.to_payload():
            raise AssuranceCapsuleError("invalidation payload is non-canonical")
        return value


def require_current_capsule(
    capsule: AssuranceCapsuleRecord, *, expected_generation: str, expected_scope_id: str,
    expected_domain_id: str, invalidations: Sequence[InvalidationRecord],
) -> AssuranceCapsuleRecord:
    if not isinstance(capsule, AssuranceCapsuleRecord):
        raise AssuranceCapsuleError("currentness requires an AssuranceCapsuleRecord")
    if capsule.subject_generation != expected_generation or capsule.current_generation != expected_generation:
        raise AssuranceCapsuleError("capsule generation is stale or incompatible")
    if capsule.scope_id != _sha(expected_scope_id, "expected_scope_id"):
        raise AssuranceCapsuleError("capsule scope is incompatible")
    if capsule.domain_id != _sha(expected_domain_id, "expected_domain_id"):
        raise AssuranceCapsuleError("capsule domain is incompatible")
    for record in invalidations:
        if not isinstance(record, InvalidationRecord):
            raise AssuranceCapsuleError("invalidation roster is non-canonical")
        if record.capsule_id == capsule.capsule_id:
            raise AssuranceCapsuleError("capsule is invalidated")
    return capsule


class AssuranceCapsuleArchive:
    """Archivist-facing content-addressed store with exact-generation recovery only."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.capsules = self.root / "capsules"
        self.invalidations = self.root / "invalidations"
        self.capsules.mkdir(parents=True, exist_ok=True)
        self.invalidations.mkdir(parents=True, exist_ok=True)

    def store(self, capsule: AssuranceCapsuleRecord) -> Path:
        if not isinstance(capsule, AssuranceCapsuleRecord):
            raise AssuranceCapsuleError("archive accepts only canonical AssuranceCapsuleRecord values")
        path = self.capsules / f"{capsule.capsule_id}.json"
        data = canonical_json_bytes(capsule.to_payload())
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return path

    def recover_exact(self, capsule_id: str, *, expected_generation: str) -> AssuranceCapsuleRecord:
        capsule_id = _sha(capsule_id, "capsule_id")
        path = self.capsules / f"{capsule_id}.json"
        if not path.is_file():
            raise AssuranceCapsuleError("exact capsule not found")
        try:
            payload = json.loads(path.read_text())
            capsule = AssuranceCapsuleRecord.from_payload(payload)
        except (json.JSONDecodeError, OSError, TypeError, ValueError, ReviewWorldError) as exc:
            raise AssuranceCapsuleError(f"capsule identity or payload verification failed: {exc}") from exc
        if capsule.capsule_id != capsule_id:
            raise AssuranceCapsuleError("capsule identity does not match requested exact ID")
        if capsule.subject_generation != expected_generation:
            raise AssuranceCapsuleError("capsule generation does not match requested exact generation")
        return capsule

    def invalidate(self, capsule_id: str, *, reason: str, provenance_escape_id: str, invalidated_at_utc: str) -> InvalidationRecord:
        record = InvalidationRecord.create(
            capsule_id=capsule_id, reason=reason, provenance_escape_id=provenance_escape_id,
            invalidated_at_utc=invalidated_at_utc,
        )
        path = self.invalidations / f"{record.record_id}.json"
        if not path.exists():
            path.write_bytes(canonical_json_bytes(record.to_payload()))
        return record

    def _invalidations_for(self, capsule_id: str) -> tuple[InvalidationRecord, ...]:
        rows: list[InvalidationRecord] = []
        for path in sorted(self.invalidations.glob("*.json")):
            try:
                record = InvalidationRecord.from_payload(json.loads(path.read_text()))
            except (json.JSONDecodeError, OSError, TypeError, ValueError, ReviewWorldError) as exc:
                raise AssuranceCapsuleError(f"invalidation replay failed closed: {exc}") from exc
            if record.capsule_id == capsule_id:
                rows.append(record)
        return tuple(rows)

    def recover_current(
        self, capsule_id: str, *, expected_generation: str,
        expected_scope_id: str, expected_domain_id: str,
    ) -> AssuranceCapsuleRecord:
        capsule = self.recover_exact(capsule_id, expected_generation=expected_generation)
        return require_current_capsule(
            capsule, expected_generation=expected_generation, expected_scope_id=expected_scope_id,
            expected_domain_id=expected_domain_id, invalidations=self._invalidations_for(capsule.capsule_id),
        )
