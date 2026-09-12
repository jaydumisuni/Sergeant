from __future__ import annotations

import pytest

from main_review.semantic_coupling import (CouplingError, CouplingKind, CouplingEdge, SemanticCouplingGraph)


def test_changed_producer_reaches_unchanged_consumer_and_generated_artifact():
    g=SemanticCouplingGraph.create(edges=(
        CouplingEdge('config:billing','service:checkout',CouplingKind.CONFIG_CONSUMER),
        CouplingEdge('service:checkout','artifact:routes.json',CouplingKind.GENERATED_ARTIFACT),
    ))
    assert g.semantic_blast_radius(('config:billing',)) == ('artifact:routes.json','service:checkout')

def test_persistence_and_observer_coupling_are_included():
    g=SemanticCouplingGraph.create(edges=(
        CouplingEdge('writer','db:orders',CouplingKind.PERSISTENCE),
        CouplingEdge('db:orders','metrics:orders',CouplingKind.OBSERVER),
    ))
    assert g.semantic_blast_radius(('writer',)) == ('db:orders','metrics:orders')

def test_cycles_are_bounded_and_do_not_duplicate_radius():
    g=SemanticCouplingGraph.create(edges=(CouplingEdge('a','b',CouplingKind.PRODUCER_CONSUMER),CouplingEdge('b','a',CouplingKind.PRODUCER_CONSUMER)))
    assert g.semantic_blast_radius(('a',)) == ('b',)

def test_duplicate_edges_fail_closed():
    edge=CouplingEdge('a','b',CouplingKind.PRODUCER_CONSUMER)
    with pytest.raises(CouplingError, match='duplicate'):
        SemanticCouplingGraph.create(edges=(edge,edge))

def test_noncanonical_or_self_edges_fail_closed():
    with pytest.raises(CouplingError): CouplingEdge(' a','b',CouplingKind.PRODUCER_CONSUMER)
    with pytest.raises(CouplingError): CouplingEdge('a','a',CouplingKind.PRODUCER_CONSUMER)
