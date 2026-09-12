from __future__ import annotations

import pytest
from main_review.authority_effect_reasoning import AuthorityEffectError, AuthorityEffectGraph, CausalCertainty, DelegationEdge, EffectEdge, Principal

def test_qualification_transitive_and_alternate_authority_paths():
    g=AuthorityEffectGraph.create(principals=(Principal('root'),Principal('a'),Principal('b'),Principal('sink')),delegations=(DelegationEdge('root','a','write'),DelegationEdge('root','b','write'),DelegationEdge('a','sink','write'),DelegationEdge('b','sink','write')),effects=(EffectEdge('sink','db:x','mutate',CausalCertainty.EXACT),),bounded_external_effects=('db:x',))
    assert g.authority_paths('root','sink') == (('root','a','sink'),('root','b','sink'))
    assert g.effective_reach('root').effects == ('db:x',)

def test_qualification_unknown_causal_edges_do_not_become_exact_effects():
    g=AuthorityEffectGraph.create(principals=(Principal('root'),),delegations=(),effects=(EffectEdge('root','net:x','emit',CausalCertainty.UNKNOWN),),bounded_external_effects=('net:x',))
    r=g.effective_reach('root'); assert r.exact is False; assert r.effects == (); assert r.unknown_edges

def test_qualification_rejects_incomplete_external_effect_census():
    with pytest.raises(AuthorityEffectError, match='census'):
        AuthorityEffectGraph.create(principals=(Principal('root'),),delegations=(),effects=(EffectEdge('root','db:x','mutate',CausalCertainty.EXACT),),bounded_external_effects=())

def test_qualification_rejects_tenfold_command_authority_import():
    with pytest.raises(AuthorityEffectError, match='Tenfold'):
        AuthorityEffectGraph.create(principals=(Principal('tenfold-command'),Principal('sergeant')),delegations=(DelegationEdge('tenfold-command','sergeant','command'),),effects=(),bounded_external_effects=())
