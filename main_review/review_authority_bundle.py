"""SAE-10 immutable Review Authority Bundle contracts."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from main_review.review_world import ReviewWorldError, require_full_sha256, sha256_id
RAB_SLOTS = ('epistemic_constitution', 'safety_constitution', 'acr_generation', 'capability_passport_registry', 'obligation_law', 'evidence_law', 'independence_law', 'rust_contract_kernel', 'qualification_authority_registry', 'root_authority')
_MUTABLE_ALIASES = {'latest', 'current', 'head', 'tip', 'main', 'master'}

class ReviewAuthorityBundleError(ReviewWorldError):
    pass

def _expect_keys(payload, required, label):
    if not isinstance(payload, dict):
        raise ReviewAuthorityBundleError(f'{label} must be an object')
    keys = set(payload)
    missing = set(required) - keys
    extra = keys - set(required)
    if missing:
        raise ReviewAuthorityBundleError(f'{label} missing required fields: {sorted(missing)!r}')
    if extra:
        raise ReviewAuthorityBundleError(f'{label} has unexpected fields: {sorted(extra)!r}')

def _require_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ReviewAuthorityBundleError(f'{field} must be a string')
    return value

def _require_generation(value: str, field: str) -> str:
    raw = _require_string(value, field)
    candidate = raw.strip()
    if not candidate:
        raise ReviewAuthorityBundleError(f'{field} must be non-empty')
    if candidate.lower() in _MUTABLE_ALIASES:
        raise ReviewAuthorityBundleError(f'{field} uses mutable authority alias {candidate!r}')
    return candidate

def _require_authority_domain(value: str, field: str) -> str:
    raw = _require_string(value, field)
    candidate = raw.strip()
    if not candidate:
        raise ReviewAuthorityBundleError(f'{field} must be non-empty')
    if raw != candidate:
        raise ReviewAuthorityBundleError(f'{field} must be canonical without surrounding whitespace')
    return candidate

@dataclass(frozen=True)
class RABComponent:
    name: str
    lifecycle_state: Literal['active', 'inactive_not_yet_established', 'prohibited']
    generation: str | None
    content_id: str | None
    basis: str | None
    authority_domain: str

    @classmethod
    def active(cls, *, name: str, generation: str, content_id: str, authority_domain: str) -> 'RABComponent':
        if name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f'unknown RAB component slot: {name!r}')
        generation = _require_generation(generation, f'{name}.generation')
        content_id = require_full_sha256(_require_string(content_id, f'{name}.content_id'), f'{name}.content_id')
        domain = _require_authority_domain(authority_domain, f'{name}.authority_domain')
        return cls(name, 'active', generation, content_id, None, domain)

    @classmethod
    def inactive(cls, *, name: str, basis: str) -> 'RABComponent':
        if name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f'unknown RAB component slot: {name!r}')
        raw_basis = _require_string(basis, f'{name}.basis')
        basis = raw_basis.strip()
        if not basis:
            raise ReviewAuthorityBundleError(f'{name}.basis must be non-empty')
        return cls(name, 'inactive_not_yet_established', None, None, basis, 'sergeant-assurance')

    @classmethod
    def prohibited(cls, *, name: str, basis: str) -> 'RABComponent':
        if name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f'unknown RAB component slot: {name!r}')
        raw_basis = _require_string(basis, f'{name}.basis')
        basis = raw_basis.strip()
        if not basis:
            raise ReviewAuthorityBundleError(f'{name}.basis must be non-empty')
        return cls(name, 'prohibited', None, None, basis, 'sergeant-assurance')

    def to_payload(self) -> dict[str, object]:
        return {'name': self.name, 'lifecycle_state': self.lifecycle_state, 'generation': self.generation, 'content_id': self.content_id, 'basis': self.basis, 'authority_domain': self.authority_domain}

    def validate(self) -> None:
        if self.name not in RAB_SLOTS:
            raise ReviewAuthorityBundleError(f'unknown RAB component slot: {self.name!r}')
        domain = _require_authority_domain(self.authority_domain, f'{self.name}.authority_domain')
        if self.lifecycle_state == 'active':
            generation = _require_generation(self.generation, f'{self.name}.generation')
            if generation != self.generation:
                raise ReviewAuthorityBundleError(f'{self.name}.generation must be canonical without surrounding whitespace')
            require_full_sha256(_require_string(self.content_id, f'{self.name}.content_id'), f'{self.name}.content_id')
            if self.basis is not None:
                raise ReviewAuthorityBundleError(f'active {self.name} cannot carry inactive basis')
        elif self.lifecycle_state in {'inactive_not_yet_established', 'prohibited'}:
            if domain != 'sergeant-assurance':
                raise ReviewAuthorityBundleError(f'{self.name}.authority_domain must be sergeant-assurance while inactive/prohibited')
            if self.generation is not None or self.content_id is not None:
                raise ReviewAuthorityBundleError(f'inactive/prohibited {self.name} cannot carry active identity')
            raw_basis = _require_string(self.basis, f'{self.name}.basis')
            basis = raw_basis.strip()
            if not basis:
                raise ReviewAuthorityBundleError(f'{self.name}.basis must be non-empty')
            if basis != raw_basis:
                raise ReviewAuthorityBundleError(f'{self.name}.basis must be canonical without surrounding whitespace')
        else:
            raise ReviewAuthorityBundleError(f'invalid lifecycle state for {self.name}')

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> 'RABComponent':
        _expect_keys(payload, {'name', 'lifecycle_state', 'generation', 'content_id', 'basis', 'authority_domain'}, 'RABComponent')
        state = str(payload['lifecycle_state'])
        name = str(payload['name'])
        domain = payload['authority_domain']
        basis = payload['basis']
        if state == 'active':
            obj = cls.active(name=name, generation=payload['generation'], content_id=payload['content_id'], authority_domain=domain)
        elif state == 'inactive_not_yet_established':
            obj = cls.inactive(name=name, basis=basis)
        elif state == 'prohibited':
            obj = cls.prohibited(name=name, basis=basis)
        else:
            raise ReviewAuthorityBundleError(f'invalid lifecycle state for {name}')
        if obj.authority_domain != domain:
            raise ReviewAuthorityBundleError(f'authority domain mismatch for {name}')
        return obj

@dataclass(frozen=True)
class ReviewAuthorityBundle:
    schema_version: str
    components: tuple[RABComponent, ...]
    rab_id: str

    @classmethod
    def create(cls, **components: RABComponent) -> 'ReviewAuthorityBundle':
        unknown = set(components) - set(RAB_SLOTS)
        if unknown:
            raise ReviewAuthorityBundleError(f'unknown RAB slots: {sorted(unknown)!r}')
        ordered = []
        for slot in RAB_SLOTS:
            component = components.get(slot) or RABComponent.inactive(name=slot, basis=f'{slot} not yet established in SAE-10 generation 1')
            if component.name != slot:
                raise ReviewAuthorityBundleError(f'RAB slot {slot!r} received descriptor for {component.name!r}')
            component.validate()
            ordered.append(component)
        body = {'schema_version': 'sergeant.review-authority-bundle.v1', 'components': {item.name: item.to_payload() for item in ordered}}
        return cls('sergeant.review-authority-bundle.v1', tuple(ordered), sha256_id(body))

    def to_payload(self, *, include_id: bool=True) -> dict[str, object]:
        payload = {'schema_version': self.schema_version, 'components': {item.name: item.to_payload() for item in self.components}}
        if include_id:
            payload['rab_id'] = self.rab_id
        return payload

    def expected_id(self) -> str:
        if self.schema_version != 'sergeant.review-authority-bundle.v1':
            raise ReviewAuthorityBundleError('unknown RAB schema version')
        if tuple((item.name for item in self.components)) != RAB_SLOTS:
            raise ReviewAuthorityBundleError('RAB component roster/order is not canonical')
        for item in self.components:
            item.validate()
        return sha256_id(self.to_payload(include_id=False))

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> 'ReviewAuthorityBundle':
        _expect_keys(payload, {'schema_version', 'components', 'rab_id'}, 'ReviewAuthorityBundle')
        if payload['schema_version'] != 'sergeant.review-authority-bundle.v1':
            raise ReviewAuthorityBundleError('unknown RAB schema version')
        components = payload['components']
        if not isinstance(components, dict):
            raise ReviewAuthorityBundleError('RAB components must be an object')
        if set(components) != set(RAB_SLOTS):
            raise ReviewAuthorityBundleError('RAB component roster is not canonical')
        parsed = {name: RABComponent.from_payload(components[name]) for name in RAB_SLOTS}
        obj = cls.create(**parsed)
        if require_full_sha256(str(payload['rab_id']), 'rab_id') != obj.rab_id:
            raise ReviewAuthorityBundleError('rab_id mismatch')
        return obj

@dataclass(frozen=True)
class RABAuthorization:
    rab_id: str
    state: Literal['authorized', 'revoked', 'suspended']
    authorization_generation: str
    root_basis: str
    reason: str | None

    @classmethod
    def authorized(cls, rab_id: str, authorization_generation: str, root_basis: str) -> 'RABAuthorization':
        return cls._create(rab_id, 'authorized', authorization_generation, root_basis, None)

    @classmethod
    def revoked(cls, rab_id: str, authorization_generation: str, root_basis: str, reason: str) -> 'RABAuthorization':
        return cls._create(rab_id, 'revoked', authorization_generation, root_basis, reason)

    @classmethod
    def suspended(cls, rab_id: str, authorization_generation: str, root_basis: str, reason: str) -> 'RABAuthorization':
        return cls._create(rab_id, 'suspended', authorization_generation, root_basis, reason)

    @classmethod
    def _create(cls, rab_id: str, state: str, authorization_generation: str, root_basis: str, reason: str | None) -> 'RABAuthorization':
        rab_id = require_full_sha256(rab_id, 'authorization.rab_id')
        generation = _require_generation(authorization_generation, 'authorization_generation')
        basis = str(root_basis or '').strip()
        if not basis:
            raise ReviewAuthorityBundleError('root_basis must be non-empty')
        if state not in {'authorized', 'revoked', 'suspended'}:
            raise ReviewAuthorityBundleError('invalid RAB authorization state')
        normalized = str(reason or '').strip() or None
        if state != 'authorized' and normalized is None:
            raise ReviewAuthorityBundleError(f'{state} RAB authorization requires a reason')
        if state == 'authorized' and normalized is not None:
            raise ReviewAuthorityBundleError('authorized RAB record cannot carry revocation reason')
        return cls(rab_id, state, generation, basis, normalized)

    def validate(self) -> None:
        normalized = type(self)._create(
            self.rab_id,
            self.state,
            self.authorization_generation,
            self.root_basis,
            self.reason,
        )
        if normalized != self:
            raise ReviewAuthorityBundleError('RAB authorization record is not canonical')

    def to_payload(self) -> dict[str, object]:
        return {'rab_id': self.rab_id, 'state': self.state, 'authorization_generation': self.authorization_generation, 'root_basis': self.root_basis, 'reason': self.reason}

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> 'RABAuthorization':
        _expect_keys(payload, {'rab_id', 'state', 'authorization_generation', 'root_basis', 'reason'}, 'RABAuthorization')
        state = str(payload['state'])
        reason = None if payload['reason'] is None else str(payload['reason'])
        if state == 'authorized' and reason is not None:
            raise ReviewAuthorityBundleError('authorized RAB record cannot carry reason')
        if state == 'authorized':
            return cls.authorized(str(payload['rab_id']), str(payload['authorization_generation']), str(payload['root_basis']))
        if state == 'revoked':
            return cls.revoked(str(payload['rab_id']), str(payload['authorization_generation']), str(payload['root_basis']), str(reason or ''))
        if state == 'suspended':
            return cls.suspended(str(payload['rab_id']), str(payload['authorization_generation']), str(payload['root_basis']), str(reason or ''))
        raise ReviewAuthorityBundleError('invalid RAB authorization state')

@dataclass(frozen=True)
class RABAuthorizationSet:
    schema_version: str
    records: tuple[RABAuthorization, ...]
    authorization_set_id: str

    @classmethod
    def create(cls, records: list[RABAuthorization] | tuple[RABAuthorization, ...]) -> 'RABAuthorizationSet':
        validated = []
        for record in records:
            if not isinstance(record, RABAuthorization):
                raise ReviewAuthorityBundleError('RAB authorization set contains an invalid record type')
            record.validate()
            validated.append(record)
        seen = set()
        ordered = []
        for record in sorted(validated, key=lambda item: item.rab_id):
            if record.rab_id in seen:
                raise ReviewAuthorityBundleError(f'duplicate RAB authorization record for {record.rab_id}')
            seen.add(record.rab_id)
            ordered.append(record)
        body = {'schema_version': 'sergeant.rab-authorization-set.v1', 'records': [item.to_payload() for item in ordered]}
        return cls('sergeant.rab-authorization-set.v1', tuple(ordered), sha256_id(body))

    def to_payload(self, *, include_id: bool=True) -> dict[str, object]:
        payload = {'schema_version': self.schema_version, 'records': [item.to_payload() for item in self.records]}
        if include_id:
            payload['authorization_set_id'] = self.authorization_set_id
        return payload

    def expected_id(self) -> str:
        if self.schema_version != 'sergeant.rab-authorization-set.v1':
            raise ReviewAuthorityBundleError('unknown RAB authorization-set schema version')
        for record in self.records:
            if not isinstance(record, RABAuthorization):
                raise ReviewAuthorityBundleError('RAB authorization set contains an invalid record type')
            record.validate()
        if len({item.rab_id for item in self.records}) != len(self.records):
            raise ReviewAuthorityBundleError('duplicate RAB authorization record')
        canonical_order = tuple(sorted(self.records, key=lambda item: item.rab_id))
        if tuple(self.records) != canonical_order:
            raise ReviewAuthorityBundleError('RAB authorization records are not in canonical rab_id order')
        return sha256_id(self.to_payload(include_id=False))

    def find(self, rab_id: str) -> RABAuthorization | None:
        rab_id = require_full_sha256(rab_id, 'rab_id')
        return next((record for record in self.records if record.rab_id == rab_id), None)

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> 'RABAuthorizationSet':
        _expect_keys(payload, {'schema_version', 'records', 'authorization_set_id'}, 'RABAuthorizationSet')
        if payload['schema_version'] != 'sergeant.rab-authorization-set.v1':
            raise ReviewAuthorityBundleError('unknown RAB authorization-set schema version')
        records = payload['records']
        if not isinstance(records, list):
            raise ReviewAuthorityBundleError('RAB authorization records must be an array')
        obj = cls.create([RABAuthorization.from_payload(item) for item in records])
        if require_full_sha256(str(payload['authorization_set_id']), 'authorization_set_id') != obj.authorization_set_id:
            raise ReviewAuthorityBundleError('authorization_set_id mismatch')
        return obj

@dataclass(frozen=True)
class RABAuthorizationResult:
    authorized: bool
    reason: str
    rab_id: str
    authorization_generation: str | None = None

def authorize_rab(bundle: ReviewAuthorityBundle, authorization_set: RABAuthorizationSet) -> RABAuthorizationResult:
    if bundle.expected_id() != bundle.rab_id:
        return RABAuthorizationResult(False, 'rab_identity_mismatch', bundle.rab_id)
    if authorization_set.expected_id() != authorization_set.authorization_set_id:
        return RABAuthorizationResult(False, 'authorization_set_identity_mismatch', bundle.rab_id)
    record = authorization_set.find(bundle.rab_id)
    if record is None:
        return RABAuthorizationResult(False, 'rab_not_authorized_as_whole', bundle.rab_id)
    if record.state == 'revoked':
        return RABAuthorizationResult(False, 'rab_revoked', bundle.rab_id, record.authorization_generation)
    if record.state == 'suspended':
        return RABAuthorizationResult(False, 'rab_suspended', bundle.rab_id, record.authorization_generation)
    if record.state != 'authorized':
        return RABAuthorizationResult(False, 'invalid_authorization_state', bundle.rab_id, record.authorization_generation)
    return RABAuthorizationResult(True, 'authorized', bundle.rab_id, record.authorization_generation)
