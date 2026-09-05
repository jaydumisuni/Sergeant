"""SAE-20 immutable Assurance Contract Registry foundation."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from .review_world import ReviewWorldError, require_full_sha256, sha256_id

class RegistryError(ReviewWorldError):
    pass

def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RegistryError(f"{field} must be canonical and non-empty")
    return value

def _expect_keys(payload: Mapping[str, object], required: set[str], label: str) -> None:
    if not isinstance(payload, Mapping):
        raise RegistryError(f"{label} must be an object")
    missing = required - set(payload); extra = set(payload) - required
    if missing: raise RegistryError(f"{label} missing required fields: {sorted(missing)!r}")
    if extra: raise RegistryError(f"{label} has unexpected fields: {sorted(extra)!r}")

def _identifiers(values: Sequence[str], field: str, *, allow_empty: bool=True) -> tuple[str,...]:
    if isinstance(values,(str,bytes)): raise RegistryError(f"{field} must be a non-string sequence")
    out = tuple(sorted(_string(v,field) for v in values))
    if not allow_empty and not out: raise RegistryError(f"{field} must not be empty")
    if len(set(out)) != len(out): raise RegistryError(f"{field} contains duplicates")
    return out

@dataclass(frozen=True)
class _FrozenJSONMap(Mapping[str, object]):
    items_tuple: tuple[tuple[str, object], ...]
    def __getitem__(self, key: str) -> object:
        for k,v in self.items_tuple:
            if k == key: return v
        raise KeyError(key)
    def __iter__(self): return (k for k,_ in self.items_tuple)
    def __len__(self): return len(self.items_tuple)
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other.items())
        return False

def _freeze_json(value: object, field: str="applicability expected") -> object:
    if value is None or isinstance(value,(str,bool,int)): return value
    if isinstance(value,float):
        if not math.isfinite(value): raise RegistryError(f"{field} rejects non-finite numbers")
        return value
    if isinstance(value, Mapping):
        pairs=[]
        for k,v in value.items():
            if not isinstance(k,str): raise RegistryError(f"{field} object keys must be strings")
            pairs.append((k,_freeze_json(v,field)))
        pairs.sort(key=lambda item:item[0])
        if len({k for k,_ in pairs}) != len(pairs): raise RegistryError(f"{field} contains duplicate object keys")
        return _FrozenJSONMap(tuple(pairs))
    if isinstance(value,(list,tuple)):
        return tuple(_freeze_json(v,field) for v in value)
    raise RegistryError(f"{field} must be JSON-compatible")

def _is_frozen_json(value: object) -> bool:
    if value is None or isinstance(value,(str,bool,int)): return True
    if isinstance(value,float): return math.isfinite(value)
    if isinstance(value,_FrozenJSONMap): return all(_is_frozen_json(v) for _,v in value.items_tuple)
    if isinstance(value,tuple): return all(_is_frozen_json(v) for v in value)
    return False

def _thaw_json(value: object) -> object:
    if isinstance(value,_FrozenJSONMap): return {k:_thaw_json(v) for k,v in value.items_tuple}
    if isinstance(value,tuple): return [_thaw_json(v) for v in value]
    return value

class ApplicabilityTruth(str, Enum): TRUE="TRUE"; FALSE="FALSE"; UNKNOWN="UNKNOWN"
class ClosureGrade(str, Enum): EXACT="EXACT"; CONSERVATIVE_SUPERSET="CONSERVATIVE_SUPERSET"; PARTIAL="PARTIAL"; UNKNOWN="UNKNOWN"
class CollectionSemantics(str, Enum): SET="SET"; MULTISET="MULTISET"; ORDER="ORDER"
class CardinalityKind(str, Enum): ZERO_OR_ONE="ZERO_OR_ONE"; EXACTLY_ONE="EXACTLY_ONE"; FINITE="FINITE"; BOUNDED_N="BOUNDED_N"; OPEN="OPEN"

@dataclass(frozen=True)
class ApplicabilityResult:
    truth: ApplicabilityTruth
    unresolved_facts: tuple[str,...]=()

@dataclass(frozen=True)
class ApplicabilityContext:
    facts: Mapping[str,object]
    closure: ClosureGrade
    @classmethod
    def exact(cls,facts: Mapping[str,object]):
        if not isinstance(facts,Mapping): raise RegistryError("applicability facts must be a mapping")
        return cls(dict(facts),ClosureGrade.EXACT)
    @classmethod
    def partial(cls,facts: Mapping[str,object]):
        if not isinstance(facts,Mapping): raise RegistryError("applicability facts must be a mapping")
        return cls(dict(facts),ClosureGrade.PARTIAL)

@dataclass(frozen=True)
class ApplicabilityPredicate:
    op: str
    fact: str|None=None
    expected: object|None=None
    children: tuple['ApplicabilityPredicate',...]=()
    @classmethod
    def fact_equals(cls,fact: str, expected: object):
        return cls("fact_equals",_string(fact,"applicability fact"),_freeze_json(expected),())
    @classmethod
    def fact_absent(cls,fact: str): return cls("fact_absent",_string(fact,"applicability fact"),None,())
    @classmethod
    def all_of(cls,*children): return cls._composite("all",children)
    @classmethod
    def any_of(cls,*children): return cls._composite("any",children)
    @classmethod
    def negate(cls,child):
        if not isinstance(child,ApplicabilityPredicate): raise RegistryError("not predicate child must be an ApplicabilityPredicate")
        child.validate(); return cls("not",None,None,(child,))
    @classmethod
    def _composite(cls,op,children):
        if isinstance(children,(str,bytes)) or not children: raise RegistryError(f"{op} applicability requires at least one child")
        children=tuple(children)
        for c in children:
            if not isinstance(c,ApplicabilityPredicate): raise RegistryError("applicability child must be an ApplicabilityPredicate")
            c.validate()
        return cls(op,None,None,children)
    def validate(self):
        if self.op=="fact_equals":
            _string(self.fact,"applicability fact")
            if self.children or not _is_frozen_json(self.expected): raise RegistryError("fact_equals must carry canonical immutable JSON expected value")
            return
        if self.op=="fact_absent":
            _string(self.fact,"applicability fact")
            if self.expected is not None or self.children: raise RegistryError("fact_absent has non-canonical fields")
            return
        if self.op in {"all","any"}:
            if self.fact is not None or self.expected is not None or not self.children: raise RegistryError(f"{self.op} predicate is malformed")
            for c in self.children: c.validate()
            return
        if self.op=="not":
            if self.fact is not None or self.expected is not None or len(self.children)!=1: raise RegistryError("not predicate is malformed")
            self.children[0].validate(); return
        raise RegistryError(f"unknown applicability operation: {self.op!r}")
    def referenced_facts(self):
        self.validate()
        if self.fact is not None: return (self.fact,)
        return tuple(sorted({f for c in self.children for f in c.referenced_facts()}))
    def evaluate(self,context: ApplicabilityContext):
        self.validate()
        if not isinstance(context,ApplicabilityContext): raise RegistryError("applicability context has invalid type")
        if self.op=="fact_equals":
            assert self.fact is not None
            if self.fact not in context.facts: return ApplicabilityResult(ApplicabilityTruth.UNKNOWN,(self.fact,))
            return ApplicabilityResult(ApplicabilityTruth.TRUE if _freeze_json(context.facts[self.fact])==self.expected else ApplicabilityTruth.FALSE)
        if self.op=="fact_absent":
            assert self.fact is not None
            if self.fact in context.facts: return ApplicabilityResult(ApplicabilityTruth.FALSE)
            if context.closure is ClosureGrade.EXACT: return ApplicabilityResult(ApplicabilityTruth.TRUE)
            return ApplicabilityResult(ApplicabilityTruth.UNKNOWN,(self.fact,))
        if self.op=="not":
            r=self.children[0].evaluate(context)
            if r.truth is ApplicabilityTruth.TRUE: return ApplicabilityResult(ApplicabilityTruth.FALSE,r.unresolved_facts)
            if r.truth is ApplicabilityTruth.FALSE: return ApplicabilityResult(ApplicabilityTruth.TRUE,r.unresolved_facts)
            return r
        results=tuple(c.evaluate(context) for c in self.children)
        unresolved=tuple(sorted({f for r in results for f in r.unresolved_facts}))
        if self.op=="all":
            if any(r.truth is ApplicabilityTruth.FALSE for r in results): return ApplicabilityResult(ApplicabilityTruth.FALSE)
            if all(r.truth is ApplicabilityTruth.TRUE for r in results): return ApplicabilityResult(ApplicabilityTruth.TRUE)
            return ApplicabilityResult(ApplicabilityTruth.UNKNOWN,unresolved)
        if any(r.truth is ApplicabilityTruth.TRUE for r in results): return ApplicabilityResult(ApplicabilityTruth.TRUE)
        if all(r.truth is ApplicabilityTruth.FALSE for r in results): return ApplicabilityResult(ApplicabilityTruth.FALSE)
        return ApplicabilityResult(ApplicabilityTruth.UNKNOWN,unresolved)
    def to_payload(self):
        self.validate()
        return {"op":self.op,"fact":self.fact,"expected":_thaw_json(self.expected),"children":[c.to_payload() for c in self.children]}
    @classmethod
    def from_payload(cls,payload):
        _expect_keys(payload,{"op","fact","expected","children"},"ApplicabilityPredicate")
        op=_string(payload["op"],"applicability op")
        ch=payload["children"]
        if not isinstance(ch,list): raise RegistryError("applicability children must be an array")
        children=tuple(cls.from_payload(x) for x in ch)
        fact=payload["fact"]
        if fact is not None and not isinstance(fact,str): raise RegistryError("applicability fact must be string or null")
        if op=="fact_equals":
            if fact is None or children: raise RegistryError("fact_equals malformed")
            obj=cls.fact_equals(fact,payload["expected"])
        elif op=="fact_absent":
            if fact is None or payload["expected"] is not None or children: raise RegistryError("fact_absent malformed")
            obj=cls.fact_absent(fact)
        elif op=="all": obj=cls.all_of(*children)
        elif op=="any": obj=cls.any_of(*children)
        elif op=="not":
            if len(children)!=1: raise RegistryError("not predicate is malformed")
            obj=cls.negate(children[0])
        else: raise RegistryError(f"unknown applicability operation: {op!r}")
        if obj.to_payload()!=payload: raise RegistryError("ApplicabilityPredicate persisted payload is not canonical")
        return obj

@dataclass(frozen=True)
class BoundedDomain:
    domain_id: str; generation: str; dimensions: tuple[tuple[str,int],...]; domain_hash: str
    @classmethod
    def create(cls,*,domain_id,generation,dimensions):
        domain_id=_string(domain_id,"domain_id"); generation=_string(generation,"domain generation")
        if not isinstance(dimensions,Mapping) or not dimensions: raise RegistryError("bounded domain requires at least one explicit dimension limit")
        out=[]
        for k,v in dimensions.items():
            k=_string(k,"domain dimension")
            if not isinstance(v,int) or isinstance(v,bool) or v<=0: raise RegistryError(f"domain dimension {k!r} must have a positive integer bound")
            out.append((k,v))
        out.sort()
        if len({k for k,_ in out})!=len(out): raise RegistryError("bounded domain contains duplicate dimensions")
        body={"schema_version":"sergeant.acr-bounded-domain.v1","domain_id":domain_id,"generation":generation,"dimensions":{k:v for k,v in out}}
        return cls(domain_id,generation,tuple(out),sha256_id(body))
    def to_payload(self): return {"schema_version":"sergeant.acr-bounded-domain.v1","domain_id":self.domain_id,"generation":self.generation,"dimensions":{k:v for k,v in self.dimensions},"domain_hash":self.domain_hash}
    @classmethod
    def from_payload(cls,p):
        _expect_keys(p,{"schema_version","domain_id","generation","dimensions","domain_hash"},"BoundedDomain")
        if p["schema_version"]!="sergeant.acr-bounded-domain.v1": raise RegistryError("unknown bounded-domain schema")
        if not isinstance(p["dimensions"],Mapping): raise RegistryError("bounded-domain dimensions must be an object")
        obj=cls.create(domain_id=p["domain_id"],generation=p["generation"],dimensions=p["dimensions"])
        if require_full_sha256(p["domain_hash"],"domain_hash")!=obj.domain_hash: raise RegistryError("domain_hash mismatch")
        if obj.to_payload()!=p: raise RegistryError("BoundedDomain persisted payload is not canonical")
        return obj

@dataclass(frozen=True)
class CardinalitySpec:
    kind: CardinalityKind; maximum: int|None
    @classmethod
    def zero_or_one(cls): return cls(CardinalityKind.ZERO_OR_ONE,1)
    @classmethod
    def exactly_one(cls): return cls(CardinalityKind.EXACTLY_ONE,1)
    @classmethod
    def finite(cls): return cls(CardinalityKind.FINITE,None)
    @classmethod
    def bounded_n(cls,maximum):
        if not isinstance(maximum,int) or isinstance(maximum,bool) or maximum<=0: raise RegistryError("BOUNDED_N maximum must be a positive integer")
        return cls(CardinalityKind.BOUNDED_N,maximum)
    @classmethod
    def open(cls): return cls(CardinalityKind.OPEN,None)
    def validate(self):
        if not isinstance(self.kind,CardinalityKind): raise RegistryError("invalid cardinality kind")
        if self.kind in {CardinalityKind.ZERO_OR_ONE,CardinalityKind.EXACTLY_ONE} and self.maximum!=1: raise RegistryError(f"{self.kind.value} must have maximum=1")
        if self.kind is CardinalityKind.BOUNDED_N and (not isinstance(self.maximum,int) or isinstance(self.maximum,bool) or self.maximum<=0): raise RegistryError("BOUNDED_N requires positive maximum")
        if self.kind in {CardinalityKind.FINITE,CardinalityKind.OPEN} and self.maximum is not None: raise RegistryError(f"{self.kind.value} cannot carry maximum")
    def to_payload(self): self.validate(); return {"kind":self.kind.value,"maximum":self.maximum}
    @classmethod
    def from_payload(cls,p):
        _expect_keys(p,{"kind","maximum"},"CardinalitySpec")
        try: k=CardinalityKind(p["kind"])
        except (ValueError,TypeError) as e: raise RegistryError("invalid cardinality kind") from e
        obj=cls(k,p["maximum"]); obj.validate()
        if obj.to_payload()!=p: raise RegistryError("CardinalitySpec persisted payload is not canonical")
        return obj

@dataclass(frozen=True)
class CollectionRequirement:
    family: str; semantics: CollectionSemantics; cardinality: CardinalitySpec; required_closure: ClosureGrade
    @classmethod
    def create(cls,family,semantics,cardinality,required_closure):
        family=_string(family,"collection family")
        if not isinstance(semantics,CollectionSemantics): raise RegistryError("invalid collection semantics")
        if not isinstance(cardinality,CardinalitySpec): raise RegistryError("invalid cardinality specification")
        cardinality.validate()
        if not isinstance(required_closure,ClosureGrade): raise RegistryError("invalid required closure grade")
        return cls(family,semantics,cardinality,required_closure)
    def to_payload(self): return {"family":self.family,"semantics":self.semantics.value,"cardinality":self.cardinality.to_payload(),"required_closure":self.required_closure.value}
    @classmethod
    def from_payload(cls,p):
        _expect_keys(p,{"family","semantics","cardinality","required_closure"},"CollectionRequirement")
        try: s=CollectionSemantics(p["semantics"]); c=ClosureGrade(p["required_closure"])
        except (ValueError,TypeError) as e: raise RegistryError("invalid collection requirement enum") from e
        if not isinstance(p["cardinality"],Mapping): raise RegistryError("collection cardinality must be an object")
        obj=cls.create(p["family"],s,CardinalitySpec.from_payload(p["cardinality"]),c)
        if obj.to_payload()!=p: raise RegistryError("CollectionRequirement persisted payload is not canonical")
        return obj

@dataclass(frozen=True)
class ContractRequirement:
    family: str; required_closure: ClosureGrade
    @classmethod
    def create(cls,family,required_closure):
        family=_string(family,"requirement family")
        if not isinstance(required_closure,ClosureGrade): raise RegistryError("invalid requirement closure grade")
        return cls(family,required_closure)
    def to_payload(self): return {"family":self.family,"required_closure":self.required_closure.value}
    @classmethod
    def from_payload(cls,p):
        _expect_keys(p,{"family","required_closure"},"ContractRequirement")
        try: c=ClosureGrade(p["required_closure"])
        except (ValueError,TypeError) as e: raise RegistryError("invalid requirement closure grade") from e
        obj=cls.create(p["family"],c)
        if obj.to_payload()!=p: raise RegistryError("ContractRequirement persisted payload is not canonical")
        return obj

@dataclass(frozen=True)
class NegativeApplicabilityBurden:
    mode: str; required_closure: ClosureGrade
    @classmethod
    def proven_no_match(cls,required_closure):
        if required_closure not in {ClosureGrade.EXACT,ClosureGrade.CONSERVATIVE_SUPERSET}: raise RegistryError("PROVEN_NO_MATCH requires sufficient positive closure")
        return cls("PROVEN_NO_MATCH",required_closure)
    def validate(self):
        if self.mode!="PROVEN_NO_MATCH": raise RegistryError("negative applicability mode must be PROVEN_NO_MATCH")
        if self.required_closure not in {ClosureGrade.EXACT,ClosureGrade.CONSERVATIVE_SUPERSET}: raise RegistryError("PROVEN_NO_MATCH requires sufficient positive closure")
    def to_payload(self): self.validate(); return {"mode":self.mode,"required_closure":self.required_closure.value}
    @classmethod
    def from_payload(cls,p):
        _expect_keys(p,{"mode","required_closure"},"NegativeApplicabilityBurden")
        if p["mode"]!="PROVEN_NO_MATCH": raise RegistryError("negative applicability mode must be PROVEN_NO_MATCH")
        try: c=ClosureGrade(p["required_closure"])
        except (ValueError,TypeError) as e: raise RegistryError("invalid negative-applicability closure") from e
        obj=cls.proven_no_match(c)
        if obj.to_payload()!=p: raise RegistryError("NegativeApplicabilityBurden persisted payload is not canonical")
        return obj

@dataclass(frozen=True)
class ExternalReviewLane:
    lane_id: str; minimum_instances: int; independence_required: bool
    @classmethod
    def create(cls,lane_id,minimum_instances,independence_required=True):
        lane_id=_string(lane_id,"external review lane")
        if not isinstance(minimum_instances,int) or isinstance(minimum_instances,bool) or minimum_instances<=0: raise RegistryError("external review lane minimum_instances must be positive")
        if independence_required is not True: raise RegistryError("mandatory external review lanes must require independence")
        return cls(lane_id,minimum_instances,True)
    def to_payload(self): return {"lane_id":self.lane_id,"minimum_instances":self.minimum_instances,"independence_required":self.independence_required}
    @classmethod
    def from_payload(cls,p):
        _expect_keys(p,{"lane_id","minimum_instances","independence_required"},"ExternalReviewLane")
        obj=cls.create(p["lane_id"],p["minimum_instances"],p["independence_required"])
        if obj.to_payload()!=p: raise RegistryError("ExternalReviewLane persisted payload is not canonical")
        return obj

def _requirements(values,field):
    if isinstance(values,(str,bytes)): raise RegistryError(f"{field} must be a non-string sequence")
    for x in values:
        if not isinstance(x,ContractRequirement): raise RegistryError(f"{field} contains invalid item")
    out=tuple(sorted(values,key=lambda x:x.family))
    if len({x.family for x in out})!=len(out): raise RegistryError(f"{field} contains duplicate families")
    return out

def _collections(values):
    if isinstance(values,(str,bytes)): raise RegistryError("collections must be a non-string sequence")
    for x in values:
        if not isinstance(x,CollectionRequirement): raise RegistryError("collections contains invalid item")
    out=tuple(sorted(values,key=lambda x:x.family))
    if len({x.family for x in out})!=len(out): raise RegistryError("collections contains duplicate families")
    return out

def _external_lanes(values):
    if isinstance(values,(str,bytes)): raise RegistryError("external_review_lanes must be a non-string sequence")
    for x in values:
        if not isinstance(x,ExternalReviewLane): raise RegistryError("external_review_lanes contains invalid item")
    out=tuple(sorted(values,key=lambda x:x.lane_id))
    if len({x.lane_id for x in out})!=len(out): raise RegistryError("external_review_lanes contains duplicates")
    return out

@dataclass(frozen=True)
class ACRContract:
    schema_version: str; contract_id: str; generation: str; domain: BoundedDomain; applicability: ApplicabilityPredicate
    bound_subject_variables: tuple[str,...]; semantic_carrier_families: tuple[str,...]; consumer_interpretation_families: tuple[str,...]; affected_relation_families: tuple[str,...]
    collections: tuple[CollectionRequirement,...]; mandatory_premises: tuple[ContractRequirement,...]; repeated_authority_premise_families: tuple[str,...]
    mandatory_obligations: tuple[ContractRequirement,...]; admissible_proof_classes: tuple[str,...]; material_inputs: tuple[ContractRequirement,...]
    coherence_rules: tuple[str,...]; temporal_rules: tuple[str,...]; mandatory_falsifier_families: tuple[str,...]; required_independence: tuple[str,...]; permitted_capabilities: tuple[str,...]
    negative_applicability: NegativeApplicabilityBurden; external_review_lanes: tuple[ExternalReviewLane,...]; unsupported_fallback: str; mandatory: bool; self_qualification_allowed: bool; contract_id_hash: str
    @classmethod
    def create(cls,**kw):
        contract_id=_string(kw["contract_id"],"contract_id"); generation=_string(kw["generation"],"contract generation")
        domain=kw["domain"]
        if not isinstance(domain,BoundedDomain): raise RegistryError("domain must be a BoundedDomain")
        BoundedDomain.from_payload(domain.to_payload())
        app=kw["applicability"]
        if not isinstance(app,ApplicabilityPredicate): raise RegistryError("applicability must be declarative ApplicabilityPredicate")
        app.validate()
        neg=kw["negative_applicability"]
        if not isinstance(neg,NegativeApplicabilityBurden): raise RegistryError("negative applicability requires explicit PROVEN_NO_MATCH burden")
        neg.validate()
        fallback=_string(kw["unsupported_fallback"],"unsupported_fallback")
        if fallback!="UNKNOWN": raise RegistryError("unsupported fallback must be UNKNOWN")
        vals={
            "bound_subject_variables":_identifiers(kw["bound_subject_variables"],"bound_subject_variables",allow_empty=False),
            "semantic_carrier_families":_identifiers(kw["semantic_carrier_families"],"semantic_carrier_families",allow_empty=False),
            "consumer_interpretation_families":_identifiers(kw["consumer_interpretation_families"],"consumer_interpretation_families"),
            "affected_relation_families":_identifiers(kw["affected_relation_families"],"affected_relation_families"),
            "collections":_collections(kw["collections"]),
            "mandatory_premises":_requirements(kw["mandatory_premises"],"mandatory_premises"),
            "repeated_authority_premise_families":_identifiers(kw["repeated_authority_premise_families"],"repeated_authority_premise_families"),
            "mandatory_obligations":_requirements(kw["mandatory_obligations"],"mandatory_obligations"),
            "admissible_proof_classes":_identifiers(kw["admissible_proof_classes"],"admissible_proof_classes",allow_empty=False),
            "material_inputs":_requirements(kw["material_inputs"],"material_inputs"),
            "coherence_rules":_identifiers(kw["coherence_rules"],"coherence_rules"),
            "temporal_rules":_identifiers(kw["temporal_rules"],"temporal_rules"),
            "mandatory_falsifier_families":_identifiers(kw["mandatory_falsifier_families"],"mandatory_falsifier_families"),
            "required_independence":_identifiers(kw["required_independence"],"required_independence"),
            "permitted_capabilities":_identifiers(kw["permitted_capabilities"],"permitted_capabilities"),
            "external_review_lanes":_external_lanes(kw["external_review_lanes"]),
        }
        body={"schema_version":"sergeant.acr-contract.v1","contract_id":contract_id,"generation":generation,"domain":domain.to_payload(),"applicability":app.to_payload(),
              "bound_subject_variables":list(vals["bound_subject_variables"]),"semantic_carrier_families":list(vals["semantic_carrier_families"]),"consumer_interpretation_families":list(vals["consumer_interpretation_families"]),"affected_relation_families":list(vals["affected_relation_families"]),
              "collections":[x.to_payload() for x in vals["collections"]],"mandatory_premises":[x.to_payload() for x in vals["mandatory_premises"]],"repeated_authority_premise_families":list(vals["repeated_authority_premise_families"]),"mandatory_obligations":[x.to_payload() for x in vals["mandatory_obligations"]],"admissible_proof_classes":list(vals["admissible_proof_classes"]),"material_inputs":[x.to_payload() for x in vals["material_inputs"]],"coherence_rules":list(vals["coherence_rules"]),"temporal_rules":list(vals["temporal_rules"]),"mandatory_falsifier_families":list(vals["mandatory_falsifier_families"]),"required_independence":list(vals["required_independence"]),"permitted_capabilities":list(vals["permitted_capabilities"]),"negative_applicability":neg.to_payload(),"external_review_lanes":[x.to_payload() for x in vals["external_review_lanes"]],"unsupported_fallback":fallback,"mandatory":True,"self_qualification_allowed":False}
        digest=sha256_id(body)
        return cls("sergeant.acr-contract.v1",contract_id,generation,domain,app,vals["bound_subject_variables"],vals["semantic_carrier_families"],vals["consumer_interpretation_families"],vals["affected_relation_families"],vals["collections"],vals["mandatory_premises"],vals["repeated_authority_premise_families"],vals["mandatory_obligations"],vals["admissible_proof_classes"],vals["material_inputs"],vals["coherence_rules"],vals["temporal_rules"],vals["mandatory_falsifier_families"],vals["required_independence"],vals["permitted_capabilities"],neg,vals["external_review_lanes"],fallback,True,False,digest)
    def constructor_fields(self):
        return {k:getattr(self,k) for k in ("contract_id","generation","domain","applicability","bound_subject_variables","semantic_carrier_families","consumer_interpretation_families","affected_relation_families","collections","mandatory_premises","repeated_authority_premise_families","mandatory_obligations","admissible_proof_classes","material_inputs","coherence_rules","temporal_rules","mandatory_falsifier_families","required_independence","permitted_capabilities","negative_applicability","external_review_lanes","unsupported_fallback")}
    def evaluate(self,context): return self.applicability.evaluate(context)
    def to_payload(self):
        self.applicability.validate(); self.negative_applicability.validate()
        return {"schema_version":self.schema_version,"contract_id":self.contract_id,"generation":self.generation,"domain":self.domain.to_payload(),"applicability":self.applicability.to_payload(),"bound_subject_variables":list(self.bound_subject_variables),"semantic_carrier_families":list(self.semantic_carrier_families),"consumer_interpretation_families":list(self.consumer_interpretation_families),"affected_relation_families":list(self.affected_relation_families),"collections":[x.to_payload() for x in self.collections],"mandatory_premises":[x.to_payload() for x in self.mandatory_premises],"repeated_authority_premise_families":list(self.repeated_authority_premise_families),"mandatory_obligations":[x.to_payload() for x in self.mandatory_obligations],"admissible_proof_classes":list(self.admissible_proof_classes),"material_inputs":[x.to_payload() for x in self.material_inputs],"coherence_rules":list(self.coherence_rules),"temporal_rules":list(self.temporal_rules),"mandatory_falsifier_families":list(self.mandatory_falsifier_families),"required_independence":list(self.required_independence),"permitted_capabilities":list(self.permitted_capabilities),"negative_applicability":self.negative_applicability.to_payload(),"external_review_lanes":[x.to_payload() for x in self.external_review_lanes],"unsupported_fallback":self.unsupported_fallback,"mandatory":self.mandatory,"self_qualification_allowed":self.self_qualification_allowed,"contract_id_hash":self.contract_id_hash}
    @classmethod
    def from_payload(cls,p):
        req={"schema_version","contract_id","generation","domain","applicability","bound_subject_variables","semantic_carrier_families","consumer_interpretation_families","affected_relation_families","collections","mandatory_premises","repeated_authority_premise_families","mandatory_obligations","admissible_proof_classes","material_inputs","coherence_rules","temporal_rules","mandatory_falsifier_families","required_independence","permitted_capabilities","negative_applicability","external_review_lanes","unsupported_fallback","mandatory","self_qualification_allowed","contract_id_hash"}
        _expect_keys(p,req,"ACRContract")
        if p["schema_version"]!="sergeant.acr-contract.v1": raise RegistryError("unknown ACRContract schema")
        if p["mandatory"] is not True: raise RegistryError("SAE-20 v1 ACR contract must remain mandatory")
        if p["self_qualification_allowed"] is not False: raise RegistryError("candidate ACR contract cannot self-qualify")
        seqfields=req & {"bound_subject_variables","semantic_carrier_families","consumer_interpretation_families","affected_relation_families","collections","mandatory_premises","repeated_authority_premise_families","mandatory_obligations","admissible_proof_classes","material_inputs","coherence_rules","temporal_rules","mandatory_falsifier_families","required_independence","permitted_capabilities","external_review_lanes"}
        if any(not isinstance(p[f],list) for f in seqfields): raise RegistryError("ACRContract sequence fields must be arrays")
        obj=cls.create(contract_id=p["contract_id"],generation=p["generation"],domain=BoundedDomain.from_payload(p["domain"]),applicability=ApplicabilityPredicate.from_payload(p["applicability"]),bound_subject_variables=p["bound_subject_variables"],semantic_carrier_families=p["semantic_carrier_families"],consumer_interpretation_families=p["consumer_interpretation_families"],affected_relation_families=p["affected_relation_families"],collections=tuple(CollectionRequirement.from_payload(x) for x in p["collections"]),mandatory_premises=tuple(ContractRequirement.from_payload(x) for x in p["mandatory_premises"]),repeated_authority_premise_families=p["repeated_authority_premise_families"],mandatory_obligations=tuple(ContractRequirement.from_payload(x) for x in p["mandatory_obligations"]),admissible_proof_classes=p["admissible_proof_classes"],material_inputs=tuple(ContractRequirement.from_payload(x) for x in p["material_inputs"]),coherence_rules=p["coherence_rules"],temporal_rules=p["temporal_rules"],mandatory_falsifier_families=p["mandatory_falsifier_families"],required_independence=p["required_independence"],permitted_capabilities=p["permitted_capabilities"],negative_applicability=NegativeApplicabilityBurden.from_payload(p["negative_applicability"]),external_review_lanes=tuple(ExternalReviewLane.from_payload(x) for x in p["external_review_lanes"]),unsupported_fallback=p["unsupported_fallback"])
        if require_full_sha256(p["contract_id_hash"],"contract_id_hash")!=obj.contract_id_hash: raise RegistryError("contract_id_hash mismatch")
        if obj.to_payload()!=p: raise RegistryError("ACRContract persisted payload is not canonical")
        return obj

@dataclass(frozen=True)
class ACRContractEvaluation:
    contract_id: str; contract_generation: str; truth: ApplicabilityTruth; unresolved_facts: tuple[str,...]; evaluation_present: bool

@dataclass(frozen=True)
class ACRRegistry:
    schema_version: str; generation: str; contracts: tuple[ACRContract,...]; registry_id: str
    @classmethod
    def create(cls,*,generation,contracts):
        generation=_string(generation,"registry generation")
        if isinstance(contracts,(str,bytes)): raise RegistryError("contracts must be a non-string sequence")
        normalized=tuple(sorted(contracts,key=lambda x:(x.contract_id,x.generation)))
        for c in normalized:
            if not isinstance(c,ACRContract): raise RegistryError("registry contains invalid contract type")
            ACRContract.from_payload(c.to_payload())
        ids=[c.contract_id for c in normalized]
        if len(set(ids))!=len(ids): raise RegistryError("duplicate contract_id in registry")
        body={"schema_version":"sergeant.acr-registry.v1","generation":generation,"contracts":[c.to_payload() for c in normalized]}
        return cls("sergeant.acr-registry.v1",generation,normalized,sha256_id(body))
    def evaluate_all(self,contexts):
        if not isinstance(contexts,Mapping): raise RegistryError("registry evaluation contexts must be a mapping")
        known={c.contract_id for c in self.contracts}; unknown=set(contexts)-known
        if unknown: raise RegistryError(f"evaluation supplied unknown contract IDs: {sorted(unknown)!r}")
        out=[]
        for c in self.contracts:
            ctx=contexts.get(c.contract_id)
            if ctx is None: out.append(ACRContractEvaluation(c.contract_id,c.generation,ApplicabilityTruth.UNKNOWN,("<missing-evaluation>",),False)); continue
            if not isinstance(ctx,ApplicabilityContext): raise RegistryError(f"evaluation context for {c.contract_id} has invalid type")
            r=c.evaluate(ctx); out.append(ACRContractEvaluation(c.contract_id,c.generation,r.truth,r.unresolved_facts,True))
        return tuple(out)
    def to_payload(self): return {"schema_version":self.schema_version,"generation":self.generation,"contracts":[c.to_payload() for c in self.contracts],"registry_id":self.registry_id}
    @classmethod
    def from_payload(cls,p):
        _expect_keys(p,{"schema_version","generation","contracts","registry_id"},"ACRRegistry")
        if p["schema_version"]!="sergeant.acr-registry.v1": raise RegistryError("unknown ACRRegistry schema")
        if not isinstance(p["contracts"],list): raise RegistryError("registry contracts must be an array")
        obj=cls.create(generation=p["generation"],contracts=tuple(ACRContract.from_payload(x) for x in p["contracts"]))
        if require_full_sha256(p["registry_id"],"registry_id")!=obj.registry_id: raise RegistryError("registry_id mismatch")
        if obj.to_payload()!=p: raise RegistryError("ACRRegistry persisted payload is not canonical")
        return obj
