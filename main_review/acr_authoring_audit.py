"""SAE-20 independent ACR Authoring Audit foundation."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from .assurance_contract_registry import (
    ACRContract,
    ApplicabilityPredicate,
    CardinalityKind,
    ClosureGrade,
    CollectionRequirement,
    ContractRequirement,
    NegativeApplicabilityBurden,
    RegistryError,
)
from .review_world import require_full_sha256, sha256_id

class AuthoringAuditStatus(str, Enum): CLEAN="CLEAN"; DEFICIENT="DEFICIENT"
class ACREscapeDisposition(str, Enum): SUSPEND_OR_REVOKE="SUSPEND_OR_REVOKE"

def _string(value: object, field: str) -> str:
    if not isinstance(value,str) or not value or value!=value.strip(): raise ValueError(f"{field} must be canonical and non-empty")
    return value

def _strings(values: Sequence[str], field: str) -> tuple[str,...]:
    if isinstance(values,(str,bytes)): raise ValueError(f"{field} must be a non-string sequence")
    out=tuple(sorted(_string(v,field) for v in values))
    if len(set(out))!=len(out): raise ValueError(f"{field} contains duplicates")
    return out

def _requirements(values: Sequence[ContractRequirement], field: str) -> tuple[ContractRequirement,...]:
    if isinstance(values,(str,bytes)): raise ValueError(f"{field} must be a non-string sequence")
    out=[]
    for item in values:
        if not isinstance(item,ContractRequirement): raise ValueError(f"{field} contains invalid item")
        ContractRequirement.from_payload(item.to_payload())
        out.append(item)
    out.sort(key=lambda x:x.family)
    if len({x.family for x in out})!=len(out): raise ValueError(f"{field} contains duplicate families")
    return tuple(out)

@dataclass(frozen=True)
class AuthoringAuditFinding:
    family: str
    detail: str

@dataclass(frozen=True)
class AuthoringAuditResult:
    status: AuthoringAuditStatus
    findings: tuple[AuthoringAuditFinding,...]
    qualifies_contract: bool=False

@dataclass(frozen=True)
class AuthoringAuditProfile:
    schema_version: str
    profile_id: str
    generation: str
    contract_id: str
    domain_id: str
    domain_hash: str
    expected_applicability: ApplicabilityPredicate
    independent_basis_ids: tuple[str,...]
    required_applicability_facts: tuple[str,...]
    required_bound_subject_variables: tuple[str,...]
    required_semantic_carriers: tuple[str,...]
    required_consumer_interpretation_families: tuple[str,...]
    required_affected_relations: tuple[str,...]
    required_collections: tuple[CollectionRequirement,...]
    required_premises: tuple[ContractRequirement,...]
    required_repeated_authority_premise_families: tuple[str,...]
    required_obligations: tuple[ContractRequirement,...]
    required_admissible_proof_classes: tuple[str,...]
    required_material_inputs: tuple[ContractRequirement,...]
    required_coherence_rules: tuple[str,...]
    required_temporal_rules: tuple[str,...]
    required_falsifier_families: tuple[str,...]
    required_independence: tuple[str,...]
    required_permitted_capabilities: tuple[str,...]
    required_external_review_lanes: tuple[tuple[str,int],...]
    require_negative_applicability_burden: bool
    require_unknown_fallback: bool
    profile_hash: str

    @classmethod
    def create(cls,*,profile_id,generation,contract_id,domain_id,domain_hash,expected_applicability,
               independent_basis_ids,required_applicability_facts,required_bound_subject_variables,
               required_semantic_carriers,required_consumer_interpretation_families,required_affected_relations,
               required_collections,required_premises,required_repeated_authority_premise_families,required_obligations,
               required_admissible_proof_classes,required_material_inputs,required_coherence_rules,required_temporal_rules,
               required_falsifier_families,required_independence,required_permitted_capabilities,required_external_review_lanes,
               require_negative_applicability_burden,require_unknown_fallback):
        profile_id=_string(profile_id,"profile_id"); generation=_string(generation,"audit generation")
        contract_id=_string(contract_id,"contract_id"); domain_id=_string(domain_id,"domain_id")
        domain_hash=require_full_sha256(domain_hash,"domain_hash")
        if not isinstance(expected_applicability,ApplicabilityPredicate): raise ValueError("expected_applicability must be ApplicabilityPredicate")
        expected_applicability.validate()
        facts=_strings(required_applicability_facts,"required_applicability_facts")
        if facts != expected_applicability.referenced_facts():
            raise ValueError("required_applicability_facts must exactly match expected applicability references")
        bases=tuple(sorted(require_full_sha256(x,"independent_basis_id") for x in independent_basis_ids))
        if not bases: raise ValueError("authoring audit requires at least one independent basis")
        if len(set(bases))!=len(bases): raise ValueError("independent basis IDs contain duplicates")
        collections=tuple(sorted(required_collections,key=lambda x:x.family))
        if len({x.family for x in collections})!=len(collections): raise ValueError("required collection families contain duplicates")
        for x in collections:
            if not isinstance(x,CollectionRequirement): raise ValueError("required_collections contains invalid item")
            CollectionRequirement.from_payload(x.to_payload())
        if not isinstance(required_external_review_lanes,Mapping): raise ValueError("required_external_review_lanes must be a mapping")
        lanes=[]
        for name,minimum in required_external_review_lanes.items():
            name=_string(name,"external review lane")
            if not isinstance(minimum,int) or isinstance(minimum,bool) or minimum<=0: raise ValueError("external review lane minimum must be positive")
            lanes.append((name,minimum))
        lanes.sort()
        if require_negative_applicability_burden is not True or require_unknown_fallback is not True:
            raise ValueError("SAE-20 authoring profile must require negative-applicability burden and UNKNOWN fallback")
        vals={
            "required_bound_subject_variables":_strings(required_bound_subject_variables,"required_bound_subject_variables"),
            "required_semantic_carriers":_strings(required_semantic_carriers,"required_semantic_carriers"),
            "required_consumer_interpretation_families":_strings(required_consumer_interpretation_families,"required_consumer_interpretation_families"),
            "required_affected_relations":_strings(required_affected_relations,"required_affected_relations"),
            "required_premises":_requirements(required_premises,"required_premises"),
            "required_repeated_authority_premise_families":_strings(required_repeated_authority_premise_families,"required_repeated_authority_premise_families"),
            "required_obligations":_requirements(required_obligations,"required_obligations"),
            "required_admissible_proof_classes":_strings(required_admissible_proof_classes,"required_admissible_proof_classes"),
            "required_material_inputs":_requirements(required_material_inputs,"required_material_inputs"),
            "required_coherence_rules":_strings(required_coherence_rules,"required_coherence_rules"),
            "required_temporal_rules":_strings(required_temporal_rules,"required_temporal_rules"),
            "required_falsifier_families":_strings(required_falsifier_families,"required_falsifier_families"),
            "required_independence":_strings(required_independence,"required_independence"),
            "required_permitted_capabilities":_strings(required_permitted_capabilities,"required_permitted_capabilities"),
        }
        body={"schema_version":"sergeant.acr-authoring-audit-profile.v2","profile_id":profile_id,"generation":generation,"contract_id":contract_id,
              "domain_id":domain_id,"domain_hash":domain_hash,"expected_applicability":expected_applicability.to_payload(),"independent_basis_ids":list(bases),
              "required_applicability_facts":list(facts),"required_bound_subject_variables":list(vals["required_bound_subject_variables"]),
              "required_semantic_carriers":list(vals["required_semantic_carriers"]),"required_consumer_interpretation_families":list(vals["required_consumer_interpretation_families"]),
              "required_affected_relations":list(vals["required_affected_relations"]),"required_collections":[x.to_payload() for x in collections],
              "required_premises":[x.to_payload() for x in vals["required_premises"]],"required_repeated_authority_premise_families":list(vals["required_repeated_authority_premise_families"]),
              "required_obligations":[x.to_payload() for x in vals["required_obligations"]],"required_admissible_proof_classes":list(vals["required_admissible_proof_classes"]),
              "required_material_inputs":[x.to_payload() for x in vals["required_material_inputs"]],"required_coherence_rules":list(vals["required_coherence_rules"]),
              "required_temporal_rules":list(vals["required_temporal_rules"]),"required_falsifier_families":list(vals["required_falsifier_families"]),
              "required_independence":list(vals["required_independence"]),"required_permitted_capabilities":list(vals["required_permitted_capabilities"]),
              "required_external_review_lanes":{k:v for k,v in lanes},"require_negative_applicability_burden":True,"require_unknown_fallback":True}
        return cls(body["schema_version"],profile_id,generation,contract_id,domain_id,domain_hash,expected_applicability,bases,facts,
                   vals["required_bound_subject_variables"],vals["required_semantic_carriers"],vals["required_consumer_interpretation_families"],vals["required_affected_relations"],collections,
                   vals["required_premises"],vals["required_repeated_authority_premise_families"],vals["required_obligations"],vals["required_admissible_proof_classes"],vals["required_material_inputs"],
                   vals["required_coherence_rules"],vals["required_temporal_rules"],vals["required_falsifier_families"],vals["required_independence"],vals["required_permitted_capabilities"],tuple(lanes),True,True,sha256_id(body))

    def to_payload(self):
        return {"schema_version":self.schema_version,"profile_id":self.profile_id,"generation":self.generation,"contract_id":self.contract_id,
                "domain_id":self.domain_id,"domain_hash":self.domain_hash,"expected_applicability":self.expected_applicability.to_payload(),
                "independent_basis_ids":list(self.independent_basis_ids),"required_applicability_facts":list(self.required_applicability_facts),
                "required_bound_subject_variables":list(self.required_bound_subject_variables),"required_semantic_carriers":list(self.required_semantic_carriers),
                "required_consumer_interpretation_families":list(self.required_consumer_interpretation_families),"required_affected_relations":list(self.required_affected_relations),
                "required_collections":[x.to_payload() for x in self.required_collections],"required_premises":[x.to_payload() for x in self.required_premises],
                "required_repeated_authority_premise_families":list(self.required_repeated_authority_premise_families),"required_obligations":[x.to_payload() for x in self.required_obligations],
                "required_admissible_proof_classes":list(self.required_admissible_proof_classes),"required_material_inputs":[x.to_payload() for x in self.required_material_inputs],
                "required_coherence_rules":list(self.required_coherence_rules),"required_temporal_rules":list(self.required_temporal_rules),
                "required_falsifier_families":list(self.required_falsifier_families),"required_independence":list(self.required_independence),
                "required_permitted_capabilities":list(self.required_permitted_capabilities),"required_external_review_lanes":{k:v for k,v in self.required_external_review_lanes},
                "require_negative_applicability_burden":self.require_negative_applicability_burden,"require_unknown_fallback":self.require_unknown_fallback,"profile_hash":self.profile_hash}

    @classmethod
    def from_payload(cls,p):
        expected=set(cls.__dataclass_fields__)
        if set(p)!=expected: raise ValueError("AuthoringAuditProfile persisted payload has wrong fields")
        if p["schema_version"]!="sergeant.acr-authoring-audit-profile.v2": raise ValueError("unknown AuthoringAuditProfile schema")
        list_fields={"independent_basis_ids","required_applicability_facts","required_bound_subject_variables","required_semantic_carriers","required_consumer_interpretation_families","required_affected_relations","required_collections","required_premises","required_repeated_authority_premise_families","required_obligations","required_admissible_proof_classes","required_material_inputs","required_coherence_rules","required_temporal_rules","required_falsifier_families","required_independence","required_permitted_capabilities"}
        if any(not isinstance(p[f],list) for f in list_fields): raise ValueError("AuthoringAuditProfile sequence fields must be arrays")
        if not isinstance(p["required_external_review_lanes"],Mapping): raise ValueError("required_external_review_lanes must be an object")
        obj=cls.create(profile_id=p["profile_id"],generation=p["generation"],contract_id=p["contract_id"],domain_id=p["domain_id"],domain_hash=p["domain_hash"],
                       expected_applicability=ApplicabilityPredicate.from_payload(p["expected_applicability"]),independent_basis_ids=p["independent_basis_ids"],
                       required_applicability_facts=p["required_applicability_facts"],required_bound_subject_variables=p["required_bound_subject_variables"],
                       required_semantic_carriers=p["required_semantic_carriers"],required_consumer_interpretation_families=p["required_consumer_interpretation_families"],
                       required_affected_relations=p["required_affected_relations"],required_collections=tuple(CollectionRequirement.from_payload(x) for x in p["required_collections"]),
                       required_premises=tuple(ContractRequirement.from_payload(x) for x in p["required_premises"]),required_repeated_authority_premise_families=p["required_repeated_authority_premise_families"],
                       required_obligations=tuple(ContractRequirement.from_payload(x) for x in p["required_obligations"]),required_admissible_proof_classes=p["required_admissible_proof_classes"],
                       required_material_inputs=tuple(ContractRequirement.from_payload(x) for x in p["required_material_inputs"]),required_coherence_rules=p["required_coherence_rules"],
                       required_temporal_rules=p["required_temporal_rules"],required_falsifier_families=p["required_falsifier_families"],required_independence=p["required_independence"],
                       required_permitted_capabilities=p["required_permitted_capabilities"],required_external_review_lanes=p["required_external_review_lanes"],
                       require_negative_applicability_burden=p["require_negative_applicability_burden"],require_unknown_fallback=p["require_unknown_fallback"])
        if require_full_sha256(p["profile_hash"],"profile_hash")!=obj.profile_hash: raise ValueError("profile_hash mismatch")
        if obj.to_payload()!=p: raise ValueError("AuthoringAuditProfile persisted payload is not canonical")
        return obj

def _finding(findings,family,detail): findings.append(AuthoringAuditFinding(family,detail))
def _closure_rank(g): return {ClosureGrade.UNKNOWN:0,ClosureGrade.PARTIAL:1,ClosureGrade.CONSERVATIVE_SUPERSET:2,ClosureGrade.EXACT:3}[g]
def _cardinality_at_least(actual,required):
    if actual.kind is not required.kind: return False
    if required.kind is CardinalityKind.BOUNDED_N: return actual.maximum is not None and required.maximum is not None and actual.maximum>=required.maximum
    return actual.maximum==required.maximum

def _audit_requirement_set(findings,actual,required,label):
    actual_by={x.family:x for x in actual}; required_by={x.family:x for x in required}
    missing=set(required_by)-set(actual_by)
    if missing: _finding(findings,f"{label}_omission",f"missing required families: {sorted(missing)!r}")
    for family,expected in required_by.items():
        got=actual_by.get(family)
        if got is not None and _closure_rank(got.required_closure)<_closure_rank(expected.required_closure):
            _finding(findings,f"{label}_closure_grade_weakening",f"{family} closure {got.required_closure.value} is below {expected.required_closure.value}")

def audit_contract_authoring(contract: ACRContract, profile: AuthoringAuditProfile) -> AuthoringAuditResult:
    if not isinstance(contract,ACRContract) or not isinstance(profile,AuthoringAuditProfile): raise ValueError("authoring audit requires ACRContract and AuthoringAuditProfile")
    findings=[]
    canonical=True
    try: ACRContract.from_payload(contract.to_payload())
    except Exception as exc:
        canonical=False; _finding(findings,"contract_noncanonical_or_malformed",f"candidate contract failed canonical validation: {type(exc).__name__}")

    if not canonical:
        negative_ok=False
        try:
            if isinstance(contract.negative_applicability,NegativeApplicabilityBurden):
                contract.negative_applicability.validate(); negative_ok=True
        except (RegistryError, AttributeError, TypeError):
            negative_ok=False
        if profile.require_negative_applicability_burden and not negative_ok:
            _finding(findings,"negative_applicability_burden_missing","canonical PROVEN_NO_MATCH burden with sufficient closure missing")
        if getattr(contract,"unsupported_fallback",None)!="UNKNOWN":
            _finding(findings,"unknown_fallback_weakening","unsupported fallback must be UNKNOWN")
        if getattr(contract,"self_qualification_allowed",None) is not False:
            _finding(findings,"candidate_self_qualification","candidate contract attempted to grant qualification")
        ordered=tuple(sorted(set(findings),key=lambda x:(x.family,x.detail)))
        return AuthoringAuditResult(AuthoringAuditStatus.DEFICIENT,ordered,False)

    if contract.contract_id!=profile.contract_id or contract.domain.domain_id!=profile.domain_id or contract.domain.domain_hash!=profile.domain_hash:
        _finding(findings,"audit_scope_mismatch","contract/profile identity or exact bounded-domain identity mismatch")
    try:
        if contract.applicability.to_payload()!=profile.expected_applicability.to_payload():
            _finding(findings,"applicability_semantics_mismatch","applicability operator/value/tree differs from independently audited predicate")
        refs=set(contract.applicability.referenced_facts())
    except Exception:
        refs=set()
    missing=set(profile.required_applicability_facts)-refs
    if missing: _finding(findings,"applicability_omission",f"missing applicability facts: {sorted(missing)!r}")

    exact_fields=(
        ("bound_subject_variables_mismatch",profile.required_bound_subject_variables,contract.bound_subject_variables),
        ("admissible_proof_classes_mismatch",profile.required_admissible_proof_classes,contract.admissible_proof_classes),
        ("permitted_capabilities_mismatch",profile.required_permitted_capabilities,contract.permitted_capabilities),
    )
    for family,expected,actual in exact_fields:
        if tuple(actual)!=tuple(expected): _finding(findings,family,"candidate authority field differs from independently audited profile")

    for family,expected,actual in (
        ("semantic_carrier_omission",set(profile.required_semantic_carriers),set(contract.semantic_carrier_families)),
        ("consumer_interpretation_omission",set(profile.required_consumer_interpretation_families),set(contract.consumer_interpretation_families)),
        ("affected_relation_omission",set(profile.required_affected_relations),set(contract.affected_relation_families)),
        ("repeated_authority_premise_omission",set(profile.required_repeated_authority_premise_families),set(contract.repeated_authority_premise_families)),
        ("coherence_rule_omission",set(profile.required_coherence_rules),set(contract.coherence_rules)),
        ("temporal_rule_omission",set(profile.required_temporal_rules),set(contract.temporal_rules)),
        ("falsifier_family_omission",set(profile.required_falsifier_families),set(contract.mandatory_falsifier_families)),
        ("independence_rule_omission",set(profile.required_independence),set(contract.required_independence)),
    ):
        absent=expected-actual
        if absent: _finding(findings,family,f"missing required families/rules: {sorted(absent)!r}")

    _audit_requirement_set(findings,contract.mandatory_premises,profile.required_premises,"premise")
    _audit_requirement_set(findings,contract.mandatory_obligations,profile.required_obligations,"obligation")
    _audit_requirement_set(findings,contract.material_inputs,profile.required_material_inputs,"material_input")

    actual_collections={x.family:x for x in contract.collections}
    for required in profile.required_collections:
        actual=actual_collections.get(required.family)
        if actual is None: _finding(findings,"collection_omission",f"missing collection {required.family}"); continue
        if actual.semantics is not required.semantics or not _cardinality_at_least(actual.cardinality,required.cardinality):
            _finding(findings,"collection_semantics_or_cardinality_weakening",f"weakened collection {required.family}")
        if _closure_rank(actual.required_closure)<_closure_rank(required.required_closure):
            _finding(findings,"closure_grade_weakening",f"weakened closure for {required.family}")

    actual_lanes={x.lane_id:x.minimum_instances for x in contract.external_review_lanes}
    for lane_id,minimum in profile.required_external_review_lanes:
        if actual_lanes.get(lane_id,0)<minimum: _finding(findings,"external_review_lane_cardinality_weakening",f"{lane_id} requires at least {minimum}")

    negative_ok=False
    try:
        if isinstance(contract.negative_applicability,NegativeApplicabilityBurden):
            contract.negative_applicability.validate(); negative_ok=True
    except RegistryError: negative_ok=False
    if profile.require_negative_applicability_burden and not negative_ok:
        _finding(findings,"negative_applicability_burden_missing","canonical PROVEN_NO_MATCH burden with sufficient closure missing")
    if profile.require_unknown_fallback and contract.unsupported_fallback!="UNKNOWN": _finding(findings,"unknown_fallback_weakening","unsupported fallback must be UNKNOWN")
    if contract.self_qualification_allowed is not False: _finding(findings,"candidate_self_qualification","candidate contract attempted to grant qualification")

    ordered=tuple(sorted(set(findings),key=lambda x:(x.family,x.detail)))
    return AuthoringAuditResult(AuthoringAuditStatus.DEFICIENT if ordered else AuthoringAuditStatus.CLEAN,ordered,False)

@dataclass(frozen=True)
class ACRQualificationEscapeRecord:
    schema_version: str; registry_id: str; contract_id: str; escaped_generation: str; defect_family: str; evidence_ids: tuple[str,...]
    disposition: ACREscapeDisposition; impact_analysis_required: bool; automatic_corrected_contract_promotion_allowed: bool; permanent_qualification_evidence: bool; escape_id: str
    def to_payload(self):
        return {"schema_version":self.schema_version,"registry_id":self.registry_id,"contract_id":self.contract_id,"escaped_generation":self.escaped_generation,"defect_family":self.defect_family,"evidence_ids":list(self.evidence_ids),"disposition":self.disposition.value,"impact_analysis_required":self.impact_analysis_required,"automatic_corrected_contract_promotion_allowed":self.automatic_corrected_contract_promotion_allowed,"permanent_qualification_evidence":self.permanent_qualification_evidence,"escape_id":self.escape_id}
    @classmethod
    def from_payload(cls,p):
        expected={"schema_version","registry_id","contract_id","escaped_generation","defect_family","evidence_ids","disposition","impact_analysis_required","automatic_corrected_contract_promotion_allowed","permanent_qualification_evidence","escape_id"}
        if set(p)!=expected: raise ValueError("ACR qualification escape payload has wrong fields")
        if p["schema_version"]!="sergeant.acr-qualification-escape.v1": raise ValueError("unknown ACR qualification escape schema")
        if p["disposition"]!=ACREscapeDisposition.SUSPEND_OR_REVOKE.value: raise ValueError("qualification escape must suspend or revoke")
        if p["impact_analysis_required"] is not True: raise ValueError("qualification escape requires impact analysis")
        if p["automatic_corrected_contract_promotion_allowed"] is not False: raise ValueError("qualification escape cannot auto-promote corrected contract")
        if p["permanent_qualification_evidence"] is not True: raise ValueError("qualification escape must become permanent qualification evidence")
        if not isinstance(p["evidence_ids"],list): raise ValueError("qualification escape evidence_ids must be an array")
        obj=record_qualification_escape(registry_id=p["registry_id"],contract_id=p["contract_id"],escaped_generation=p["escaped_generation"],defect_family=p["defect_family"],evidence_ids=p["evidence_ids"])
        if require_full_sha256(p["escape_id"],"escape_id")!=obj.escape_id: raise ValueError("escape_id mismatch")
        if obj.to_payload()!=p: raise ValueError("ACR qualification escape payload is non-canonical")
        return obj

def record_qualification_escape(*,registry_id,contract_id,escaped_generation,defect_family,evidence_ids):
    registry_id=require_full_sha256(registry_id,"registry_id"); contract_id=_string(contract_id,"contract_id"); escaped_generation=_string(escaped_generation,"escaped_generation"); defect_family=_string(defect_family,"defect_family")
    evidence=tuple(sorted(require_full_sha256(x,"evidence_id") for x in evidence_ids))
    if not evidence: raise ValueError("qualification escape requires evidence")
    if len(set(evidence))!=len(evidence): raise ValueError("qualification escape evidence contains duplicates")
    body={"schema_version":"sergeant.acr-qualification-escape.v1","registry_id":registry_id,"contract_id":contract_id,"escaped_generation":escaped_generation,"defect_family":defect_family,"evidence_ids":list(evidence),"disposition":ACREscapeDisposition.SUSPEND_OR_REVOKE.value,"impact_analysis_required":True,"automatic_corrected_contract_promotion_allowed":False,"permanent_qualification_evidence":True}
    return ACRQualificationEscapeRecord(body["schema_version"],registry_id,contract_id,escaped_generation,defect_family,evidence,ACREscapeDisposition.SUSPEND_OR_REVOKE,True,False,True,sha256_id(body))
