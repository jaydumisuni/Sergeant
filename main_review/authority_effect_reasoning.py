"""SAE-130A bounded principal/delegation/effect reasoning."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

class AuthorityEffectError(ValueError):
    pass

class CausalCertainty(str, Enum):
    EXACT = "EXACT"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True, order=True)
class Principal:
    name: str
    def __post_init__(self):
        if not self.name or self.name != self.name.strip():
            raise AuthorityEffectError("principal name must be canonical")

@dataclass(frozen=True, order=True)
class DelegationEdge:
    source: str
    target: str
    permission: str
    def __post_init__(self):
        if not all(isinstance(v,str) and v and v==v.strip() for v in (self.source,self.target,self.permission)):
            raise AuthorityEffectError("delegation edge must be canonical")

@dataclass(frozen=True, order=True)
class EffectEdge:
    source: str
    effect: str
    operation: str
    certainty: CausalCertainty
    def __post_init__(self):
        if not all(isinstance(v,str) and v and v==v.strip() for v in (self.source,self.effect,self.operation)):
            raise AuthorityEffectError("effect edge must be canonical")
        if not isinstance(self.certainty,CausalCertainty):
            raise AuthorityEffectError("causal certainty must be canonical")

@dataclass(frozen=True)
class EffectiveReach:
    principals: tuple[str,...]
    effects: tuple[str,...]
    unknown_edges: tuple[str,...]
    exact: bool

@dataclass(frozen=True)
class AuthorityEffectGraph:
    principals: tuple[Principal,...]
    delegations: tuple[DelegationEdge,...]
    effects: tuple[EffectEdge,...]
    bounded_external_effects: tuple[str,...]

    @classmethod
    def create(cls, *, principals: Sequence[Principal], delegations: Sequence[DelegationEdge], effects: Sequence[EffectEdge], bounded_external_effects: Sequence[str]) -> "AuthorityEffectGraph":
        ps=tuple(principals); ds=tuple(delegations); es=tuple(effects); census=tuple(sorted(set(bounded_external_effects)))
        names={p.name for p in ps}
        if len(names)!=len(ps): raise AuthorityEffectError("principal roster contains duplicates")
        if any('tenfold' in p.name.lower() and 'command' in p.name.lower() for p in ps) or any('tenfold' in d.source.lower() and d.permission.lower()=='command' for d in ds):
            raise AuthorityEffectError("Tenfold command authority is outside Sergeant SAE-130A")
        for d in ds:
            if d.source not in names or d.target not in names: raise AuthorityEffectError("delegation references unknown principal")
        for e in es:
            if e.source not in names: raise AuthorityEffectError("effect references unknown principal")
            if e.effect not in census: raise AuthorityEffectError("external effect census is incomplete")
        if len(census)!=len(tuple(bounded_external_effects)): raise AuthorityEffectError("external effect census must be unique")
        return cls(tuple(sorted(ps)), tuple(sorted(ds)), tuple(sorted(es)), census)

    def authority_paths(self, source: str, target: str) -> tuple[tuple[str,...],...]:
        adjacency: dict[str,list[str]]={p.name:[] for p in self.principals}
        for d in self.delegations: adjacency[d.source].append(d.target)
        paths=[]
        def walk(node: str, path: tuple[str,...]):
            if node==target:
                paths.append(path); return
            for nxt in sorted(adjacency.get(node,())):
                if nxt not in path: walk(nxt, path+(nxt,))
        if source in adjacency and target in adjacency: walk(source,(source,))
        return tuple(sorted(paths))

    def effective_reach(self, source: str) -> EffectiveReach:
        names={p.name for p in self.principals}
        if source not in names: raise AuthorityEffectError("source principal is unknown")
        reached={source}; changed=True
        while changed:
            changed=False
            for d in self.delegations:
                if d.source in reached and d.target not in reached:
                    reached.add(d.target); changed=True
        exact_effects=set(); unknown=[]
        for e in self.effects:
            if e.source not in reached: continue
            if e.certainty is CausalCertainty.EXACT: exact_effects.add(e.effect)
            else: unknown.append(f"{e.source}->{e.effect}:{e.operation}")
        return EffectiveReach(tuple(sorted(reached)),tuple(sorted(exact_effects)),tuple(sorted(unknown)),not unknown)
