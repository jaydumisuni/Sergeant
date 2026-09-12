from __future__ import annotations
import pytest
from main_review.semantic_coupling import CouplingError,CouplingKind,CouplingEdge,SemanticCouplingGraph

def test_qualification_reaches_generated_persistence_and_observer_consumers():
 g=SemanticCouplingGraph.create(edges=(CouplingEdge('config:x','service:a',CouplingKind.CONFIG_CONSUMER),CouplingEdge('service:a','artifact:y',CouplingKind.GENERATED_ARTIFACT),CouplingEdge('artifact:y','db:z',CouplingKind.PERSISTENCE),CouplingEdge('db:z','observer:q',CouplingKind.OBSERVER)))
 assert g.semantic_blast_radius(('config:x',))==('artifact:y','db:z','observer:q','service:a')

def test_qualification_changed_config_reaches_unchanged_consumer():
 g=SemanticCouplingGraph.create(edges=(CouplingEdge('config:x','consumer:stable',CouplingKind.CONFIG_CONSUMER),))
 assert g.semantic_blast_radius(('config:x',))==('consumer:stable',)

def test_qualification_cycles_terminate_exactly():
 g=SemanticCouplingGraph.create(edges=(CouplingEdge('a','b',CouplingKind.PRODUCER_CONSUMER),CouplingEdge('b','c',CouplingKind.PRODUCER_CONSUMER),CouplingEdge('c','a',CouplingKind.PRODUCER_CONSUMER)))
 assert g.semantic_blast_radius(('a',))==('b','c')

def test_qualification_rejects_duplicate_and_self_edges():
 e=CouplingEdge('a','b',CouplingKind.PRODUCER_CONSUMER)
 with pytest.raises(CouplingError): SemanticCouplingGraph.create(edges=(e,e))
 with pytest.raises(CouplingError): CouplingEdge('a','a',CouplingKind.PRODUCER_CONSUMER)
