"""SAE-10 immutable Review Authority Bundle contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from main_review.review_world import ReviewWorldError, require_full_sha256, sha256_id


RAB_SLOTS = (
    "epistemic_constitution",
    "safety_constitution",
    "acr_generation",
    "capability_passport_registry",
    "obligation_law",
    "evidence_law",
    "independence_law",
    "rust_contract_kernel",
    "qualification_authority_registry",
    "root_authority",
)
_MUTABLE_ALIASES = {"latest", "current", "head", "tip", "main", "master"}


class ReviewAuthorityBundleError(ReviewWorldError):
    """Raised when an RAB or its trusted authorization is ambiguous or invalid."""


def _require_generation(value: str, field: str) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        raise ReviewAuthorityBundleError(f"{field} must be non-empty")
    if candidate.lower() in _MUTABLE_ALIASES:
        raise ReviewAuthorityBundleError(f"{field} uses mutable authority alias {candidate!r}")
    return candidate


@dataclass(frozen=True)
class RABComponent:
    name: str
    lifecycle_state: Literal["active", "inactive_not_yet_established", "prohibited"]
    generation: str | None
    content_id: str | None
    basis: str | None
    authority_domain: str

    @classmethod
    def active(cls, *, name: str, generation: str, content_id: str, authority_domain: str) -> "RABComponent":
        if name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f"unknown RAB component slot: {name!r}")
        generation = _require_generation(generation, f"{name}.generation")
        content_id = require_full_sha256(content_id, f"{name}.content_id")
        domain = str(authority_domain or "").strip()
        if not domain:
            raise ReviewAuthorityBundleError(f"{name}.authority_domain must be non-empty")
        return cls(name, "active", generation, content_id, None, domain)

    @classmethod
    def inactive(cls, *, name: str, basis: str) -> "RABComponent":
        if name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f"unknown RAB component slot: {name!r}")
        basis = str(basis or "").strip()
        if not basis:
            raise ReviewAuthorityBundleError(f"{name}.basis must be non-empty")
        return cls(name, "inactive_not_yet_established", None, None, basis, "sergeant-assurance")

    @classmethod
    def prohibited(cls, *, name: str, basis: str) -> "RABComponent":
        if name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f"unknown RAB component slot: {name!r}")
        basis = str(basis or "").strip()
        if not basis:
            raise ReviewAuthorityBundleError(f"{name}.basis must be non-empty")
        return cls(name, "prohibited", None, None, basis, "sergeant-assurance")

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "lifecycle_state": self.lifecycle_state,
            "generation": self.generation,
            "content_id": self.content_id,
            "basis": self.basis,
            "authority_domain": self.authority_domain,
        }

    def validate(self) -> None:
        if self.name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f"unknown RAB component slot: {self.name!r}")
        if self.lifecycle_state == "active":
            _require_generation(str(self.generation or ""), f"{self.name}.generation")
            require_full_sha256(str(self.content_id or ""), f"{self.name}.content_id")
            if self.basis is not None:
                raise ReviewAuthorityBundleError(f"active {self.name} cannot carry inactive basis")
        elif self.lifecycle_state in {"inactive_not_yet_established", "prohibited"}:
            if self.generation is not None or self.content_id is not None:
                raise ReviewAuthorityBundleError(f"inactive/prohibited {self.name} cannot carry active identity")
            if not str(self.basis or "").strip():
                raise ReviewAuthorityBundleError(f"{self.name}.basis must be non-empty")
        else:
            raise ReviewAuthorityBundleError(f"invalid lifecycle state for {self.name}")


@dataclass(frozen=True)
class ReviewAuthorityBundle:
    schema_version: str
    components: tuple[RABComponent, ...]
    rab_id: str

    @classmethod
    def create(cls, **components: RABComponent) -> "ReviewAuthorityBundle":
        unknown = set(components) - set(RAB_SLOTS)
        if unknown:
            raise ReviewAuthorityBundleError(f"unknown RAB slots: {sorted(unknown)!r}")
        ordered: list[RABComponent] = []
        for slot in RAB_SLOTS:
            component = components.get(slot)
            if component is None:
                component = RABComponent.inactive(name=slot, basis=f"{slot} not yet established in SAE-10 generation 1")
            if component.name != slot:
                raise ReviewAuthorityBundleError(f"RAB slot {slot!r} received descriptor for {component.name!r}")
            component.validate()
            ordered.append(component)
        body: dict[str, object] = {
            "schema_version": "sergeant.review-authority-bundle.v1",
            "components": {item.name: item.to_payload() for item in ordered},
        }
        return cls("sergeant.review-authority-bundle.v1", tuple(ordered), sha256_id(body))

    def to_payload(self, *, include_id: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "components": {item.name: item.to_payload() for item in self.components},
        }
        if include_id:
            payload["rab_id"] = self.rab_id
        return payload

    def expected_id(self) -> str:
        if self.schema_version != "sergeant.review-authority-bundle.v1":
            raise ReviewAuthorityBundleError("unknown RAB schema version")
        if tuple(item.name for item in self.components) != RAB_SLOTS:
            raise ReviewAuthorityBundleError("RAB component roster/order is not canonical")
        for item in self.components:
            item.validate()
        return sha256_id(self.to_payload(include_id=False))


@dataclass(frozen=True)
class RABAuthorization:
    rab_id: str
    state: Literal["authorized", "revoked", "suspended"]
    authorization_generation: str
    root_basis: str
    reason: str | None

    @classmethod
    def authorized(cls, rab_id: str, authorization_generation: str, root_basis: str) -> "RABAuthorization":
        return cls._create(rab_id, "authorized", authorization_generation, root_basis, None)

    @classmethod
    def revoked(cls, rab_id: str, authorization_generation: str, root_basis: str, reason: str) -> "RABAuthorization":
        return cls._create(rab_id, "revoked", authorization_generation, root_basis, reason)

    @classmethod
    def suspended(cls, rab_id: str, authorization_generation: str, root_basis: str, reason: str) -> "RABAuthorization":
        return cls._create(rab_id, "suspended", authorization_generation, root_basis, reason)

    @classmethod
    def _create(cls, rab_id: str, state: str, authorization_generation: str, root_basis: str, reason: str | None) -> "RABAuthorization":
        rab_id = require_full_sha256(rab_id, "authorization.rab_id")
        generation = _require_generation(authorization_generation, "authorization_generation")
        basis = str(root_basis or "").strip()
        if not basis:
            raise ReviewAuthorityBundleError("root_basis must be non-empty")
        if state not in {"authorized", "revoked", "suspended"}:
            raise ReviewAuthorityBundleError("invalid RAB authorization state")
        normalized_reason = str(reason or "").strip() or None
        if state != "authorized" and normalized_reason is None:
            raise ReviewAuthorityBundleError(f"{state} RAB authorization requires a reason")
        if state == "authorized" and normalized_reason is not None:
            raise ReviewAuthorityBundleError("authorized RAB record cannot carry revocation reason")
        return cls(rab_id, state, generation, basis, normalized_reason)

    def to_payload(self) -> dict[str, object]:
        return {
            "rab_id": self.rab_id,
            "state": self.state,
            "authorization_generation": self.authorization_generation,
            "root_basis": self.root_basis,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class RABAuthorizationSet:
    schema_version: str
    records: tuple[RABAuthorization, ...]
    authorization_set_id: str

    @classmethod
    def create(cls, records: list[RABAuthorization] | tuple[RABAuthorization, ...]) -> "RABAuthorizationSet":
        seen: set[str] = set()
        ordered: list[RABAuthorization] = []
        for record in sorted(records, key=lambda item: item.rab_id):
            if record.rab_id in seen:
                raise ReviewAuthorityBundleError(f"duplicate RAB authorization record for {record.rab_id}")
            seen.add(record.rab_id)
            ordered.append(record)
        body: dict[str, object] = {
            "schema_version": "sergeant.rab-authorization-set.v1",
            "records": [item.to_payload() for item in ordered],
        }
        return cls("sergeant.rab-authorization-set.v1", tuple(ordered), sha256_id(body))

    def to_payload(self, *, include_id: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "records": [item.to_payload() for item in self.records],
        }
        if include_id:
            payload["authorization_set_id"] = self.authorization_set_id
        return payload

    def expected_id(self) -> str:
        if self.schema_version != "sergeant.rab-authorization-set.v1":
            raise ReviewAuthorityBundleError("unknown RAB authorization-set schema version")
        if len({item.rab_id for item in self.records}) != len(self.records):
            raise ReviewAuthorityBundleError("duplicate RAB authorization record")
        return sha256_id(self.to_payload(include_id=False))

    def find(self, rab_id: str) -> RABAuthorization | None:
        rab_id = require_full_sha256(rab_id, "rab_id")
        return next((record for record in self.records if record.rab_id == rab_id), None)


@dataclass(frozen=True)
class RABAuthorizationResult:
    authorized: bool
    reason: str
    rab_id: str
    authorization_generation: str | None = None


def authorize_rab(bundle: ReviewAuthorityBundle, authorization_set: RABAuthorizationSet) -> RABAuthorizationResult:
    expected_rab = bundle.expected_id()
    if expected_rab != bundle.rab_id:
        return RABAuthorizationResult(False, "rab_identity_mismatch", bundle.rab_id)
    expected_set = authorization_set.expected_id()
    if expected_set != authorization_set.authorization_set_id:
        return RABAuthorizationResult(False, "authorization_set_identity_mismatch", bundle.rab_id)
    record = authorization_set.find(bundle.rab_id)
    if record is None:
        return RABAuthorizationResult(False, "rab_not_authorized_as_whole", bundle.rab_id)
    if record.state == "revoked":
        return RABAuthorizationResult(False, "rab_revoked", bundle.rab_id, record.authorization_generation)
    if record.state == "suspended":
        return RABAuthorizationResult(False, "rab_suspended", bundle.rab_id, record.authorization_generation)
    return RABAuthorizationResult(True, "authorized", bundle.rab_id, record.authorization_generation)
