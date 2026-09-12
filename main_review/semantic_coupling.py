"""SAE-130B bounded semantic-coupling reasoning."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

class CouplingError(ValueError):
    pass

class CouplingKind(str, Enum):
    PRODUCER_CONSUMER = "PRODUCER_CONSUMER"
    CONFIG_CONSUMER = "CONFIG_CONSUMER"
    GENERATED_ARTIFACT = "GENERATED_ARTIFACT"
    PERSISTENCE = "PERSISTENCE"
    OBSERVER = "OBSERVER"

@dataclass(frozen=True, order=True)
class CouplingEdge:
    source: str
    target: str
    kind: CouplingKind
    def __post_init__(self):
        if not all(isinstance(v,str) and v and v == v.strip() for v in (self.source,self.target)):
            raise CouplingError("coupling endpoints must be canonical")
        if self.source == self.target:
            raise CouplingError("self coupling is not admissible")
        if not isinstance(self.kind, CouplingKind):
            raise CouplingError("coupling kind must be canonical")

@dataclass(frozen=True)
class SemanticCouplingGraph:
    edges: tuple[CouplingEdge,...]

    @classmethod
    def create(cls, *, edges: Sequence[CouplingEdge]) -> "SemanticCouplingGraph":
        values=tuple(edges)
        if len(set(values)) != len(values):
            raise CouplingError("duplicate coupling edge")
        return cls(tuple(sorted(values)))

    def semantic_blast_radius(self, changed: Sequence[str]) -> tuple[str,...]:
        seeds=tuple(changed)
        if not seeds or any(not isinstance(v,str) or not v or v != v.strip() for v in seeds):
            raise CouplingError("changed surface roster must be canonical and non-empty")
        reached=set(seeds)
        frontier=list(seeds)
        adjacency: dict[str,list[str]]={}
        for edge in self.edges:
            adjacency.setdefault(edge.source,[]).append(edge.target)
        while frontier:
            node=frontier.pop()
            for target in sorted(adjacency.get(node,())):
                if target not in reached:
                    reached.add(target); frontier.append(target)
        return tuple(sorted(reached-set(seeds)))
