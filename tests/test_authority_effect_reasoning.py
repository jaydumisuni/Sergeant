from __future__ import annotations

import pytest

from main_review.authority_effect_reasoning import (
    AuthorityEffectError,
    AuthorityEffectGraph,
    CausalCertainty,
    DelegationEdge,
    EffectEdge,
    Principal,
)


def test_effective_authority_reach_includes_transitive_delegation_and_effects():
    graph = AuthorityEffectGraph.create(
        principals=(Principal('owner'), Principal('service'), Principal('worker')),
        delegations=(DelegationEdge('owner','service','write'), DelegationEdge('service','worker','write')),
        effects=(EffectEdge('worker','db:orders','mutate',CausalCertainty.EXACT),),
        bounded_external_effects=('db:orders',),
    )
    reach = graph.effective_reach('owner')
    assert reach.principals == ('owner','service','worker')
    assert reach.effects == ('db:orders',)
    assert reach.unknown_edges == ()


def test_alternate_authority_paths_are_preserved_not_collapsed():
    graph = AuthorityEffectGraph.create(
        principals=(Principal('a'), Principal('b'), Principal('c'), Principal('d')),
        delegations=(DelegationEdge('a','b','read'), DelegationEdge('a','c','read'), DelegationEdge('b','d','read'), DelegationEdge('c','d','read')),
        effects=(), bounded_external_effects=(),
    )
    assert graph.authority_paths('a','d') == (('a','b','d'),('a','c','d'))


def test_unknown_causal_edge_conserves_unknown_and_blocks_exact_effect_reach():
    graph = AuthorityEffectGraph.create(
        principals=(Principal('a'),), delegations=(),
        effects=(EffectEdge('a','network:unknown','emit',CausalCertainty.UNKNOWN),),
        bounded_external_effects=('network:unknown',),
    )
    reach = graph.effective_reach('a')
    assert reach.effects == ()
    assert reach.unknown_edges == ('a->network:unknown:emit',)
    assert reach.exact is False


def test_external_effect_census_must_be_bounded_and_complete_for_exact_reach():
    with pytest.raises(AuthorityEffectError, match='census'):
        AuthorityEffectGraph.create(
            principals=(Principal('a'),), delegations=(),
            effects=(EffectEdge('a','db:x','mutate',CausalCertainty.EXACT),),
            bounded_external_effects=(),
        )


def test_tenfold_command_authority_is_not_imported():
    with pytest.raises(AuthorityEffectError, match='Tenfold'):
        AuthorityEffectGraph.create(
            principals=(Principal('tenfold-command'), Principal('sergeant')),
            delegations=(DelegationEdge('tenfold-command','sergeant','command'),),
            effects=(), bounded_external_effects=(),
        )
