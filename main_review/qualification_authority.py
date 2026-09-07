"""SAE-30 qualification authority, derived qualification and Genesis substrate.

Qualification authority is verifier-trusted state. Candidate payloads may repeat
issuer/generation facts for coherence, but they never select the authority that
validates them. Genesis remains provisional until the SAE-170 exit authority is
satisfied for an exact qualification package.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class QualificationAuthorityError(ReviewWorldError):
    """Raised when qualification or Genesis authority fails closed."""


class IssuerState(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise QualificationAuthorityError(f"{field} must be canonical and non-empty")
    return value


def _sha(value: object, field: str) -> str:
    try:
        return require_full_sha256(value, field)  # type: ignore[arg-type]
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise QualificationAuthorityError(str(exc)) from exc


def _ids(values: Iterable[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise QualificationAuthorityError(f"{field} must be a non-string iterable")
    out = tuple(sorted(_sha(value, field) for value in values))
    if len(set(out)) != len(out):
        raise QualificationAuthorityError(f"{field} contains duplicates")
    return out


def _strings(values: Iterable[str], field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise QualificationAuthorityError(f"{field} must be a non-string iterable")
    out = tuple(sorted(_string(value, field) for value in values))
    if not allow_empty and not out:
        raise QualificationAuthorityError(f"{field} must not be empty")
    if len(set(out)) != len(out):
        raise QualificationAuthorityError(f"{field} contains duplicates")
    return out


def _time(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise QualificationAuthorityError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _time_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class QualificationIssuerAuthorization:
    schema_version: str
    issuer_identity: str
    key_id: str
    namespace: str
    issuer_generation: str
    artifact_families: tuple[str, ...]
    domains: tuple[str, ...]
    proof_classes: tuple[str, ...]
    closure_grades: tuple[str, ...]
    control_lineage_id: str
    state: IssuerState
    authorization_id: str

    @classmethod
    def create(
        cls,
        *,
        issuer_identity: str,
        key_id: str,
        namespace: str,
        issuer_generation: str,
        artifact_families: Iterable[str],
        domains: Iterable[str],
        proof_classes: Iterable[str],
        closure_grades: Iterable[str],
        control_lineage_id: str,
        state: IssuerState,
    ) -> "QualificationIssuerAuthorization":
        if not isinstance(state, IssuerState):
            raise QualificationAuthorityError("issuer state must be an IssuerState")
        values = {
            "issuer_identity": _string(issuer_identity, "issuer_identity"),
            "key_id": _sha(key_id, "issuer key_id"),
            "namespace": _string(namespace, "issuer namespace"),
            "issuer_generation": _string(issuer_generation, "issuer_generation"),
            "artifact_families": _strings(artifact_families, "artifact family"),
            "domains": _strings(domains, "qualified domain"),
            "proof_classes": _strings(proof_classes, "proof class"),
            "closure_grades": _strings(closure_grades, "closure grade"),
            "control_lineage_id": _sha(control_lineage_id, "control_lineage_id"),
        }
        body = {
            "schema_version": "sergeant.qualification-issuer-authorization.v1",
            **{key: list(value) if isinstance(value, tuple) else value for key, value in values.items()},
            "state": state.value,
        }
        return cls(
            "sergeant.qualification-issuer-authorization.v1",
            values["issuer_identity"], values["key_id"], values["namespace"],
            values["issuer_generation"], values["artifact_families"], values["domains"],
            values["proof_classes"], values["closure_grades"], values["control_lineage_id"],
            state, sha256_id(body),
        )


@dataclass(frozen=True)
class AuthenticatedIssuer:
    issuer_identity: str
    key_id: str
    namespace: str
    issuer_generation: str

    @classmethod
    def create(cls, *, issuer_identity: str, key_id: str, namespace: str, issuer_generation: str) -> "AuthenticatedIssuer":
        return cls(
            _string(issuer_identity, "authenticated issuer identity"),
            _sha(key_id, "authenticated issuer key_id"),
            _string(namespace, "authenticated issuer namespace"),
            _string(issuer_generation, "authenticated issuer generation"),
        )


@dataclass(frozen=True)
class QualificationAuthorityRegistry:
    schema_version: str
    generation: str
    issuers: tuple[QualificationIssuerAuthorization, ...]
    revoked_attestation_ids: tuple[str, ...]
    consumed_attestation_ids: tuple[str, ...]
    registry_id: str

    @classmethod
    def create(
        cls,
        *,
        generation: str,
        issuers: Iterable[QualificationIssuerAuthorization],
        revoked_attestation_ids: Iterable[str] = (),
        consumed_attestation_ids: Iterable[str] = (),
    ) -> "QualificationAuthorityRegistry":
        generation = _string(generation, "registry generation")
        if isinstance(issuers, (str, bytes)):
            raise QualificationAuthorityError("issuers must be a non-string iterable")
        normalized = tuple(sorted(tuple(issuers), key=lambda item: (item.issuer_identity, item.issuer_generation)))
        for item in normalized:
            if not isinstance(item, QualificationIssuerAuthorization):
                raise QualificationAuthorityError("registry contains invalid issuer authorization")
        identities = [(item.issuer_identity, item.issuer_generation) for item in normalized]
        if len(set(identities)) != len(identities):
            raise QualificationAuthorityError("registry contains duplicate issuer generation")
        revoked = _ids(revoked_attestation_ids, "revoked attestation id")
        consumed = _ids(consumed_attestation_ids, "consumed attestation id")
        if set(revoked) & set(consumed):
            # A consumed attestation may later be revoked only in a successor registry
            # after callers deliberately remove it from the consumed active set.
            raise QualificationAuthorityError("attestation cannot be both consumed and revoked in one active registry")
        body = {
            "schema_version": "sergeant.qualification-authority-registry.v1",
            "generation": generation,
            "issuer_authorization_ids": [item.authorization_id for item in normalized],
            "revoked_attestation_ids": list(revoked),
            "consumed_attestation_ids": list(consumed),
        }
        return cls(
            "sergeant.qualification-authority-registry.v1", generation, normalized,
            revoked, consumed, sha256_id(body),
        )

    @property
    def authority_ids(self) -> tuple[str, ...]:
        return tuple(item.authorization_id for item in self.issuers)

    def find(self, issuer_identity: str, issuer_generation: str) -> QualificationIssuerAuthorization:
        for item in self.issuers:
            if item.issuer_identity == issuer_identity and item.issuer_generation == issuer_generation:
                return item
        raise QualificationAuthorityError("authenticated issuer generation is not authorized by trusted registry")

    def with_revoked_attestation_ids(self, values: Iterable[str]) -> "QualificationAuthorityRegistry":
        revoked = _ids(values, "revoked attestation id")
        consumed = tuple(item for item in self.consumed_attestation_ids if item not in set(revoked))
        return type(self).create(
            generation=self.generation,
            issuers=self.issuers,
            revoked_attestation_ids=revoked,
            consumed_attestation_ids=consumed,
        )

    def consume(self, attestation_id: str) -> "QualificationAuthorityRegistry":
        attestation_id = _sha(attestation_id, "attestation_id")
        if attestation_id in self.consumed_attestation_ids:
            raise QualificationAuthorityError("attestation replay detected")
        if attestation_id in self.revoked_attestation_ids:
            raise QualificationAuthorityError("attestation is revoked")
        return type(self).create(
            generation=self.generation,
            issuers=self.issuers,
            revoked_attestation_ids=self.revoked_attestation_ids,
            consumed_attestation_ids=(*self.consumed_attestation_ids, attestation_id),
        )


@dataclass(frozen=True)
class QualificationAttestation:
    schema_version: str
    subject_id: str
    artifact_family: str
    domain: str
    artifact_generation: str
    acr_generation: str
    qualification_protocol_generation: str
    evidence_root_id: str
    proof_class: str
    closure_grade: str
    issued_at: datetime
    expires_at: datetime
    issuer_identity: str
    issuer_generation: str
    attestation_id: str

    @classmethod
    def create(
        cls,
        *,
        subject_id: str,
        artifact_family: str,
        domain: str,
        artifact_generation: str,
        acr_generation: str,
        qualification_protocol_generation: str,
        evidence_root_id: str,
        proof_class: str,
        closure_grade: str,
        issued_at: datetime,
        expires_at: datetime,
        issuer_identity: str,
        issuer_generation: str,
    ) -> "QualificationAttestation":
        issued = _time(issued_at, "issued_at")
        expires = _time(expires_at, "expires_at")
        if issued >= expires:
            raise QualificationAuthorityError("attestation expiry must be after issue time")
        values = {
            "subject_id": _sha(subject_id, "subject_id"),
            "artifact_family": _string(artifact_family, "artifact_family"),
            "domain": _string(domain, "domain"),
            "artifact_generation": _string(artifact_generation, "artifact_generation"),
            "acr_generation": _string(acr_generation, "acr_generation"),
            "qualification_protocol_generation": _string(qualification_protocol_generation, "qualification protocol generation"),
            "evidence_root_id": _sha(evidence_root_id, "evidence_root_id"),
            "proof_class": _string(proof_class, "proof_class"),
            "closure_grade": _string(closure_grade, "closure_grade"),
            "issuer_identity": _string(issuer_identity, "issuer_identity"),
            "issuer_generation": _string(issuer_generation, "issuer_generation"),
        }
        body = {
            "schema_version": "sergeant.qualification-attestation.v1", **values,
            "issued_at": _time_text(issued), "expires_at": _time_text(expires),
        }
        return cls(
            "sergeant.qualification-attestation.v1",
            values["subject_id"], values["artifact_family"], values["domain"],
            values["artifact_generation"], values["acr_generation"], values["qualification_protocol_generation"],
            values["evidence_root_id"], values["proof_class"], values["closure_grade"],
            issued, expires, values["issuer_identity"], values["issuer_generation"], sha256_id(body),
        )

    def constructor_fields(self) -> dict[str, object]:
        return {
            "subject_id": self.subject_id,
            "artifact_family": self.artifact_family,
            "domain": self.domain,
            "artifact_generation": self.artifact_generation,
            "acr_generation": self.acr_generation,
            "qualification_protocol_generation": self.qualification_protocol_generation,
            "evidence_root_id": self.evidence_root_id,
            "proof_class": self.proof_class,
            "closure_grade": self.closure_grade,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "issuer_identity": self.issuer_identity,
            "issuer_generation": self.issuer_generation,
        }


@dataclass(frozen=True)
class DerivedQualification:
    state: str
    subject_id: str
    artifact_family: str
    domain: str
    artifact_generation: str
    attestation_id: str
    issuer_authorization_id: str
    evidence_root_id: str
    qualification_id: str


def admit_qualification_attestation(
    *,
    registry: QualificationAuthorityRegistry,
    attestation: QualificationAttestation,
    authenticated_issuer: AuthenticatedIssuer,
    subject_id: str,
    artifact_family: str,
    domain: str,
    artifact_generation: str,
    acr_generation: str,
    qualification_protocol_generation: str,
    evidence_root_id: str,
    candidate_control_lineage_id: str,
    now: datetime,
) -> tuple[DerivedQualification, QualificationAuthorityRegistry]:
    if not isinstance(registry, QualificationAuthorityRegistry):
        raise QualificationAuthorityError("trusted qualification registry is required")
    if not isinstance(attestation, QualificationAttestation) or not isinstance(authenticated_issuer, AuthenticatedIssuer):
        raise QualificationAuthorityError("canonical attestation and authenticated issuer are required")
    now = _time(now, "verification time")
    authorization = registry.find(authenticated_issuer.issuer_identity, authenticated_issuer.issuer_generation)
    if authorization.state is not IssuerState.ACTIVE:
        raise QualificationAuthorityError("qualification issuer is suspended or revoked")
    if (
        authenticated_issuer.key_id != authorization.key_id
        or authenticated_issuer.namespace != authorization.namespace
        or authenticated_issuer.issuer_generation != authorization.issuer_generation
    ):
        raise QualificationAuthorityError("authenticated issuer does not match verifier-trusted authorization")
    if attestation.issuer_identity != authenticated_issuer.issuer_identity or attestation.issuer_generation != authenticated_issuer.issuer_generation:
        raise QualificationAuthorityError("attestation issuer payload does not match authenticated issuer generation")
    if attestation.issued_at > now:
        raise QualificationAuthorityError("attestation is future-issued")
    if now >= attestation.expires_at:
        raise QualificationAuthorityError("attestation is expired")
    if attestation.attestation_id in registry.revoked_attestation_ids:
        raise QualificationAuthorityError("attestation is revoked")
    if attestation.attestation_id in registry.consumed_attestation_ids:
        raise QualificationAuthorityError("attestation replay detected")
    expected = {
        "subject_id": _sha(subject_id, "expected subject_id"),
        "artifact_family": _string(artifact_family, "expected artifact_family"),
        "domain": _string(domain, "expected domain"),
        "artifact_generation": _string(artifact_generation, "expected artifact_generation"),
        "acr_generation": _string(acr_generation, "expected acr_generation"),
        "qualification_protocol_generation": _string(qualification_protocol_generation, "expected qualification protocol generation"),
        "evidence_root_id": _sha(evidence_root_id, "expected evidence_root_id"),
    }
    for field, value in expected.items():
        if getattr(attestation, field) != value:
            raise QualificationAuthorityError(f"attestation {field} does not match exact expected authority")
    if attestation.artifact_family not in authorization.artifact_families or attestation.domain not in authorization.domains:
        raise QualificationAuthorityError("issuer is not authorized for artifact family/domain")
    if attestation.proof_class not in authorization.proof_classes:
        raise QualificationAuthorityError("qualification proof class exceeds issuer ceiling")
    if attestation.closure_grade not in authorization.closure_grades:
        raise QualificationAuthorityError("qualification closure grade exceeds issuer ceiling")
    candidate_lineage = _sha(candidate_control_lineage_id, "candidate_control_lineage_id")
    if candidate_lineage == authorization.control_lineage_id:
        raise QualificationAuthorityError("candidate-controlled lineage cannot issue its own qualification")
    body = {
        "schema_version": "sergeant.derived-qualification.v1",
        "subject_id": attestation.subject_id,
        "artifact_family": attestation.artifact_family,
        "domain": attestation.domain,
        "artifact_generation": attestation.artifact_generation,
        "attestation_id": attestation.attestation_id,
        "issuer_authorization_id": authorization.authorization_id,
        "evidence_root_id": attestation.evidence_root_id,
        "state": "QUALIFIED",
    }
    qualification = DerivedQualification(
        "QUALIFIED", attestation.subject_id, attestation.artifact_family, attestation.domain,
        attestation.artifact_generation, attestation.attestation_id, authorization.authorization_id,
        attestation.evidence_root_id, sha256_id(body),
    )
    return qualification, registry.consume(attestation.attestation_id)


@dataclass(frozen=True)
class GenesisQualificationPackage:
    schema_version: str
    review_world_id: str
    required_qualification_ids: tuple[str, ...]
    present_qualification_ids: tuple[str, ...]
    external_review_census_id: str
    external_review_census_satisfied: bool
    founding_final_proof_id: str | None
    generation: str
    state: str
    package_id: str

    @classmethod
    def create(
        cls,
        *,
        review_world_id: str,
        required_qualification_ids: Iterable[str],
        present_qualification_ids: Iterable[str],
        external_review_census_id: str,
        external_review_census_satisfied: bool,
        founding_final_proof_id: str | None,
        generation: str,
    ) -> "GenesisQualificationPackage":
        world = _sha(review_world_id, "Genesis review_world_id")
        required = _ids(required_qualification_ids, "required qualification id")
        present = _ids(present_qualification_ids, "present qualification id")
        if not set(present).issubset(set(required)):
            raise QualificationAuthorityError("Genesis package contains qualification outside required census")
        census = _sha(external_review_census_id, "external review census id")
        if not isinstance(external_review_census_satisfied, bool):
            raise QualificationAuthorityError("external review census state must be boolean")
        proof = None if founding_final_proof_id is None else _sha(founding_final_proof_id, "founding final proof id")
        generation = _string(generation, "Genesis generation")
        body = {
            "schema_version": "sergeant.genesis-qualification-package.v1",
            "review_world_id": world,
            "required_qualification_ids": list(required),
            "present_qualification_ids": list(present),
            "external_review_census_id": census,
            "external_review_census_satisfied": external_review_census_satisfied,
            "founding_final_proof_id": proof,
            "generation": generation,
            "state": "GENESIS_PROVISIONAL",
        }
        return cls(
            "sergeant.genesis-qualification-package.v1", world, required, present, census,
            external_review_census_satisfied, proof, generation, "GENESIS_PROVISIONAL", sha256_id(body),
        )


@dataclass(frozen=True)
class GenesisExitGate:
    schema_version: str
    package_id: str
    authority_node: str
    authorized: bool
    blockers: tuple[str, ...]
    gate_id: str


def evaluate_genesis_exit_gate(*, package: GenesisQualificationPackage, authority_node: str) -> GenesisExitGate:
    if not isinstance(package, GenesisQualificationPackage):
        raise QualificationAuthorityError("Genesis Qualification Package is required")
    node = _string(authority_node, "Genesis exit authority node")
    blockers: list[str] = []
    if node != "SAE-170":
        blockers.append("Genesis Exit authority is reserved to SAE-170")
    missing = tuple(sorted(set(package.required_qualification_ids) - set(package.present_qualification_ids)))
    if missing:
        blockers.append("mandatory qualifications remain open")
    if not package.external_review_census_satisfied:
        blockers.append("mandatory independent/external review census remains open")
    if package.founding_final_proof_id is None:
        blockers.append("founding final proof is absent")
    body = {
        "schema_version": "sergeant.genesis-exit-gate.v1",
        "package_id": package.package_id,
        "authority_node": node,
        "authorized": not blockers,
        "blockers": blockers,
    }
    return GenesisExitGate(
        "sergeant.genesis-exit-gate.v1", package.package_id, node,
        not blockers, tuple(blockers), sha256_id(body),
    )


@dataclass(frozen=True)
class GenesisActivationRecord:
    schema_version: str
    package_id: str
    exit_gate_id: str
    activation_class: str
    activation_id: str

    @classmethod
    def create(
        cls,
        *,
        package: GenesisQualificationPackage,
        exit_gate: GenesisExitGate,
        activation_class: str,
        consumed_activation_classes: Iterable[str],
    ) -> "GenesisActivationRecord":
        if not isinstance(package, GenesisQualificationPackage) or not isinstance(exit_gate, GenesisExitGate):
            raise QualificationAuthorityError("canonical package and Genesis exit gate are required")
        if exit_gate.package_id != package.package_id or not exit_gate.authorized:
            raise QualificationAuthorityError("Genesis package has not passed the authorized exit gate")
        activation_class = _string(activation_class, "activation_class")
        used = _strings(consumed_activation_classes, "consumed activation class", allow_empty=True)
        if activation_class in used:
            raise QualificationAuthorityError("Genesis one-time activation class has already been consumed")
        body = {
            "schema_version": "sergeant.genesis-activation-record.v1",
            "package_id": package.package_id,
            "exit_gate_id": exit_gate.gate_id,
            "activation_class": activation_class,
        }
        return cls(
            "sergeant.genesis-activation-record.v1", package.package_id, exit_gate.gate_id,
            activation_class, sha256_id(body),
        )
