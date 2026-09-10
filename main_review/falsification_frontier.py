"""SAE-90 Mandatory Falsification / Challenger candidate substrate.

The compiler derives mandatory falsifier *instances* from exact SAE-70
obligation provenance and exact SAE-80 qualified Proof World authority. Open or
statistical search remains UNKNOWN. This candidate never emits the later
``QUALIFIED_FALSIFICATION_FRONTIER`` protocol authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import product
import math

from .assurance_contract_registry import ACRRegistry, ClosureGrade
from .contract_closure import ExpectedObligation
from .proof_world_protocol import QualifiedProofWorld, validate_qualified_proof_world
from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class FalsificationFrontierError(ReviewWorldError):
    """Raised for malformed or authority-incompatible SAE-90 inputs."""


class FalsifierSearchMode(str, Enum):
    EXHAUSTIVE_BOUNDED = "EXHAUSTIVE_BOUNDED"
    OPEN_SEARCH = "OPEN_SEARCH"
    STATISTICAL = "STATISTICAL"


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise FalsificationFrontierError(f"{field} must be a canonical non-empty string")
    return value


def _sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except ReviewWorldError as exc:
        raise FalsificationFrontierError(str(exc)) from exc


def _scalar(value: object, field: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise FalsificationFrontierError(f"{field} must be an immutable JSON scalar")


def _scalar_key(value: object) -> tuple[str, str]:
    value = _scalar(value, "falsifier parameter value")
    return type(value).__name__, sha256_id({"value": value})


@dataclass(frozen=True)
class FalsifierParameterDomain:
    contract_id: str
    contract_generation: str
    family: str
    parameters: tuple[tuple[str, tuple[object, ...]], ...]
    closed: bool
    domain_id: str

    @classmethod
    def create(cls, *, contract_id: str, contract_generation: str, family: str, parameters: Mapping[str, Sequence[object]], closed: bool) -> "FalsifierParameterDomain":
        contract_id = _string(contract_id, "falsifier contract ID")
        contract_generation = _string(contract_generation, "falsifier contract generation")
        family = _string(family, "falsifier family")
        if not isinstance(parameters, Mapping):
            raise FalsificationFrontierError("falsifier parameters must be a mapping")
        if not isinstance(closed, bool):
            raise FalsificationFrontierError("falsifier domain closed flag must be boolean")
        rows=[]
        for raw_name, raw_values in parameters.items():
            name=_string(raw_name, "falsifier parameter name")
            if isinstance(raw_values,(str,bytes)) or not isinstance(raw_values,Sequence):
                raise FalsificationFrontierError(f"falsifier parameter {name} must be a sequence")
            values=tuple(_scalar(v,f"falsifier parameter {name}") for v in raw_values)
            if not values:
                raise FalsificationFrontierError(f"falsifier parameter {name} cannot have an empty domain")
            if len({_scalar_key(v) for v in values}) != len(values):
                raise FalsificationFrontierError(f"falsifier parameter {name} contains duplicate values")
            rows.append((name,tuple(sorted(values,key=_scalar_key))))
        canonical=tuple(sorted(rows))
        body={"schema_version":"sergeant.sae90-falsifier-parameter-domain.v1","contract_id":contract_id,"contract_generation":contract_generation,"family":family,"parameters":{k:list(v) for k,v in canonical},"closed":closed}
        return cls(contract_id,contract_generation,family,canonical,closed,sha256_id(body))


def _validate_domain(value: FalsifierParameterDomain) -> FalsifierParameterDomain:
    if not isinstance(value,FalsifierParameterDomain):
        raise FalsificationFrontierError("invalid falsifier parameter domain record")
    canonical=FalsifierParameterDomain.create(contract_id=value.contract_id,contract_generation=value.contract_generation,family=value.family,parameters=dict(value.parameters),closed=value.closed)
    if canonical != value:
        raise FalsificationFrontierError("falsifier parameter domain identity mismatch")
    return value


@dataclass(frozen=True)
class FalsifierInstance:
    qualified_proof_world_id: str
    obligation_id: str
    contract_id: str
    contract_generation: str
    contract_instance_id: str
    family: str
    parameter_domain_id: str
    parameters: tuple[tuple[str, object], ...]
    instance_id: str

    @classmethod
    def create(cls, *, qualified_proof_world_id: str, obligation_id: str, contract_instance_id: str, domain: FalsifierParameterDomain, parameters: Mapping[str, object]) -> "FalsifierInstance":
        qualified_proof_world_id=_sha(qualified_proof_world_id,"qualified Proof World ID")
        obligation_id=_sha(obligation_id,"expected obligation ID")
        contract_instance_id=_sha(contract_instance_id,"contract instance ID")
        domain=_validate_domain(domain)
        if not domain.closed:
            raise FalsificationFrontierError("cannot enumerate exact instances from an open parameter domain")
        supplied=tuple(sorted((_string(k,"falsifier parameter name"),_scalar(v,"falsifier parameter value")) for k,v in parameters.items()))
        expected_names=tuple(k for k,_ in domain.parameters)
        if tuple(k for k,_ in supplied) != expected_names:
            raise FalsificationFrontierError("falsifier instance parameters do not exactly match domain")
        allowed={k:{_scalar_key(v) for v in vals} for k,vals in domain.parameters}
        for k,v in supplied:
            if _scalar_key(v) not in allowed[k]:
                raise FalsificationFrontierError(f"falsifier parameter {k} is outside the closed domain")
        body={"schema_version":"sergeant.sae90-falsifier-instance.v1","qualified_proof_world_id":qualified_proof_world_id,"obligation_id":obligation_id,"contract_id":domain.contract_id,"contract_generation":domain.contract_generation,"contract_instance_id":contract_instance_id,"family":domain.family,"parameter_domain_id":domain.domain_id,"parameters":dict(supplied)}
        return cls(qualified_proof_world_id,obligation_id,domain.contract_id,domain.contract_generation,contract_instance_id,domain.family,domain.domain_id,supplied,sha256_id(body))


def _instance_body(value: FalsifierInstance) -> dict[str,object]:
    return {"schema_version":"sergeant.sae90-falsifier-instance.v1","qualified_proof_world_id":value.qualified_proof_world_id,"obligation_id":value.obligation_id,"contract_id":value.contract_id,"contract_generation":value.contract_generation,"contract_instance_id":value.contract_instance_id,"family":value.family,"parameter_domain_id":value.parameter_domain_id,"parameters":dict(value.parameters)}


@dataclass(frozen=True)
class CounterWorldEvidence:
    instance: FalsifierInstance
    baseline_state_id: str
    mutated_state_id: str
    result: str
    search_mode: FalsifierSearchMode
    basis_id: str
    evidence_id: str

    @classmethod
    def create(cls, *, instance: FalsifierInstance, baseline_state_id: str, mutated_state_id: str, result: str, search_mode: FalsifierSearchMode, basis_id: str) -> "CounterWorldEvidence":
        if not isinstance(instance,FalsifierInstance) or instance.instance_id != sha256_id(_instance_body(instance)):
            raise FalsificationFrontierError("falsifier instance identity mismatch")
        baseline_state_id=_sha(baseline_state_id,"baseline counter-world state ID")
        mutated_state_id=_sha(mutated_state_id,"mutated counter-world state ID")
        if baseline_state_id == mutated_state_id:
            raise FalsificationFrontierError("no-op falsifier mutation is inadmissible")
        result=_string(result,"falsifier result")
        if result not in {"SURVIVED","FALSIFIED","UNKNOWN"}:
            raise FalsificationFrontierError("falsifier result must be SURVIVED, FALSIFIED, or UNKNOWN")
        if not isinstance(search_mode,FalsifierSearchMode):
            raise FalsificationFrontierError("falsifier search mode is invalid")
        basis_id=_sha(basis_id,"counter-world evidence basis ID")
        body={"schema_version":"sergeant.sae90-counter-world-evidence.v1","instance_id":instance.instance_id,"baseline_state_id":baseline_state_id,"mutated_state_id":mutated_state_id,"result":result,"search_mode":search_mode.value,"basis_id":basis_id}
        return cls(instance,baseline_state_id,mutated_state_id,result,search_mode,basis_id,sha256_id(body))


@dataclass(frozen=True)
class FalsificationFrontier:
    qualified_proof_world_id: str
    registry_id: str
    obligation_id: str
    parameter_domain_ids: tuple[str,...]
    expected_instances: tuple[FalsifierInstance,...]
    evidence: tuple[CounterWorldEvidence,...]
    grade: ClosureGrade
    blockers: tuple[str,...]
    frontier_id: str


def _validate_obligation(value: ExpectedObligation) -> ExpectedObligation:
    if not isinstance(value,ExpectedObligation):
        raise FalsificationFrontierError("SAE-90 requires an ExpectedObligation")
    body={"schema_version":"sergeant.sae70-expected-obligation.v1","family":value.family,"bindings":dict(value.bindings),"required_closure":value.required_closure.value,"provenance":[{"contract_id":o.contract_id,"contract_generation":o.contract_generation,"contract_instance_id":o.contract_instance_id,"required_closure":o.required_closure.value} for o in value.provenance]}
    if value.obligation_id != sha256_id(body):
        raise FalsificationFrontierError("expected obligation identity mismatch")
    return value


def _enumerate(*, qualified: QualifiedProofWorld, obligation: ExpectedObligation, origin, domain: FalsifierParameterDomain) -> tuple[FalsifierInstance,...]:
    if not domain.closed: return ()
    names=tuple(k for k,_ in domain.parameters); value_sets=tuple(v for _,v in domain.parameters)
    combinations=product(*value_sets) if value_sets else ((),)
    return tuple(FalsifierInstance.create(qualified_proof_world_id=qualified.qualification_id,obligation_id=obligation.obligation_id,contract_instance_id=origin.contract_instance_id,domain=domain,parameters=dict(zip(names,row,strict=True))) for row in combinations)


def compile_falsification_frontier(*, qualified_proof_world: QualifiedProofWorld, expected_obligation: ExpectedObligation, registry: ACRRegistry, parameter_domains: Sequence[FalsifierParameterDomain], evidence: Sequence[CounterWorldEvidence]) -> FalsificationFrontier:
    try: qualified=validate_qualified_proof_world(qualified_proof_world)
    except ReviewWorldError as exc: raise FalsificationFrontierError(f"invalid SAE-80 qualified Proof World: {exc}") from exc
    obligation=_validate_obligation(expected_obligation)
    if qualified.obligation_id != obligation.obligation_id:
        raise FalsificationFrontierError("qualified Proof World and expected obligation disagree")
    if not isinstance(registry,ACRRegistry):
        raise FalsificationFrontierError("SAE-90 requires an ACRRegistry")
    try: canonical_registry=ACRRegistry.from_payload(registry.to_payload())
    except (ReviewWorldError,TypeError,ValueError) as exc: raise FalsificationFrontierError(f"SAE-90 registry is malformed: {exc}") from exc
    if canonical_registry != registry: raise FalsificationFrontierError("SAE-90 registry is not canonical")
    if qualified.registry_id != registry.registry_id: raise FalsificationFrontierError("qualified Proof World and SAE-90 registry disagree")
    contracts={(c.contract_id,c.generation):c for c in registry.contracts}
    domain_map={}
    for raw in parameter_domains:
        d=_validate_domain(raw); key=(d.contract_id,d.contract_generation,d.family)
        if key in domain_map: raise FalsificationFrontierError(f"duplicate falsifier parameter domain for {key}")
        domain_map[key]=d
    blockers=[]; expected=[]; required_keys=set()
    for origin in obligation.provenance:
        contract=contracts.get((origin.contract_id,origin.contract_generation))
        if contract is None: raise FalsificationFrontierError("obligation provenance contract is absent from qualified registry")
        for family in contract.mandatory_falsifier_families:
            key=(contract.contract_id,contract.generation,family); required_keys.add(key); d=domain_map.get(key)
            if d is None: blockers.append(f"missing parameter domain for mandatory falsifier family {key}"); continue
            if not d.closed: blockers.append(f"falsifier parameter domain for {key} is not closed"); continue
            expected.extend(_enumerate(qualified=qualified,obligation=obligation,origin=origin,domain=d))
    extras=sorted(set(domain_map)-required_keys)
    if extras: raise FalsificationFrontierError(f"parameter domains include non-mandatory falsifier families: {extras}")
    expected_by_id={i.instance_id:i for i in expected}; expected_tuple=tuple(sorted(expected_by_id.values(),key=lambda i:i.instance_id))
    evidence_by_id={}
    for item in evidence:
        if not isinstance(item,CounterWorldEvidence): raise FalsificationFrontierError("invalid counter-world evidence record")
        target=expected_by_id.get(item.instance.instance_id)
        if target is None: raise FalsificationFrontierError("counter-world evidence targets an unexpected falsifier instance")
        if item.instance != target: raise FalsificationFrontierError("counter-world evidence instance does not match canonical frontier instance")
        canonical=CounterWorldEvidence.create(instance=item.instance,baseline_state_id=item.baseline_state_id,mutated_state_id=item.mutated_state_id,result=item.result,search_mode=item.search_mode,basis_id=item.basis_id)
        if canonical != item: raise FalsificationFrontierError("counter-world evidence identity mismatch")
        if target.instance_id in evidence_by_id: raise FalsificationFrontierError("duplicate counter-world evidence for falsifier instance")
        evidence_by_id[target.instance_id]=item
    for instance in expected_tuple:
        item=evidence_by_id.get(instance.instance_id)
        if item is None: blockers.append(f"missing falsifier instance evidence {instance.instance_id}"); continue
        if item.search_mode is not FalsifierSearchMode.EXHAUSTIVE_BOUNDED: blockers.append(f"{item.search_mode.value.lower()} evidence cannot establish exhaustive falsifier closure for {instance.instance_id}")
        if item.result=="FALSIFIED": blockers.append(f"falsifier instance {instance.instance_id} falsified the preferred conclusion")
        elif item.result=="UNKNOWN": blockers.append(f"falsifier instance {instance.instance_id} remains UNKNOWN")
    blockers_tuple=tuple(sorted(set(blockers))); grade=ClosureGrade.EXACT if not blockers_tuple else ClosureGrade.UNKNOWN
    evidence_tuple=tuple(sorted(evidence_by_id.values(),key=lambda e:e.instance.instance_id)); domain_ids=tuple(domain_map[k].domain_id for k in sorted(required_keys) if k in domain_map)
    body={"schema_version":"sergeant.sae90-falsification-frontier.v1","qualified_proof_world_id":qualified.qualification_id,"registry_id":registry.registry_id,"obligation_id":obligation.obligation_id,"parameter_domain_ids":list(domain_ids),"expected_instance_ids":[i.instance_id for i in expected_tuple],"evidence_ids":[e.evidence_id for e in evidence_tuple],"grade":grade.value,"blockers":list(blockers_tuple)}
    return FalsificationFrontier(qualified.qualification_id,registry.registry_id,obligation.obligation_id,domain_ids,expected_tuple,evidence_tuple,grade,blockers_tuple,sha256_id(body))
