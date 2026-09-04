import main_review.review_world as rw
import main_review.review_world_currentness as c
R = '1' * 64
A = 'a' * 40
B = 'b' * 40
C = 'c' * 40
D = 'd' * 40

def world(base=A, scope=None, rab=R, merge=None):
    scope = scope or rw.ReviewScope.repository()
    d = rw.GitHubDiffIdentity.create(repository='o/r', base_commit=base, base_tree=C, head_commit=B, head_tree=D, scope=scope)
    return rw.GitHubReviewWorld.create(repository='o/r', pr_number=1, diff=d, scope=scope, review_mode='merge_result' if merge else 'head', rab_id=rab, review_generation='g', merge_tree=merge)

def test_current():
    assert c.check_github_currentness(world(), world(), rab_authorized=True).state == 'CURRENT'

def test_base_stale():
    assert 'base_identity_mismatch' in c.check_github_currentness(world(), world(base='e' * 40), rab_authorized=True).reasons

def test_scope_stale():
    assert 'scope_mismatch' in c.check_github_currentness(world(), world(scope=rw.ReviewScope.selected_paths(['a'])), rab_authorized=True).reasons

def test_merge_stale():
    assert 'merge_result_mismatch' in c.check_github_currentness(world(merge='e' * 40), world(merge='f' * 40), rab_authorized=True).reasons

def test_rab_stale():
    assert 'rab_unauthorized_or_revoked' in c.check_github_currentness(world(), world(), rab_authorized=False).reasons

def test_unknown():
    assert c.check_github_currentness(world(), None, rab_authorized=True).state == 'UNKNOWN_CURRENTNESS'

def test_immutable():
    w = world()
    p = w.to_payload()
    i = w.review_world_id
    c.check_github_currentness(w, world(base='e' * 40), rab_authorized=True)
    assert w.to_payload() == p and w.review_world_id == i

def test_local_mutation():
    s = rw.ReviewScope.repository()
    a = rw.LocalReviewWorld.create(repository='o/r', local_snapshot_id='2' * 64, scope=s, rab_id=R, review_generation='g')
    b = rw.LocalReviewWorld.create(repository='o/r', local_snapshot_id='3' * 64, scope=s, rab_id=R, review_generation='g')
    assert c.check_local_currentness(a, b, rab_authorized=True).reasons == ('local_snapshot_mutation',)


def test_unknown_rab_authorization_preserves_github_world_mismatch_reasons():
    result = c.check_github_currentness(world(), world(base='e' * 40), rab_authorized=None)
    assert result.state == 'UNKNOWN_CURRENTNESS'
    assert 'rab_authorization_unknown' in result.reasons
    assert 'base_identity_mismatch' in result.reasons


def test_unknown_rab_authorization_preserves_local_world_mismatch_reasons():
    s = rw.ReviewScope.repository()
    frozen = rw.LocalReviewWorld.create(repository='o/r', local_snapshot_id='2' * 64, scope=s, rab_id=R, review_generation='g')
    current = rw.LocalReviewWorld.create(repository='o/r', local_snapshot_id='3' * 64, scope=s, rab_id=R, review_generation='g')
    result = c.check_local_currentness(frozen, current, rab_authorized=None)
    assert result.state == 'UNKNOWN_CURRENTNESS'
    assert 'rab_authorization_unknown' in result.reasons
    assert 'local_snapshot_mutation' in result.reasons


def test_currentness_rejects_direct_forged_github_world_identity():
    valid = world()
    forged = rw.GitHubReviewWorld(
        schema_version=valid.schema_version,
        kind=valid.kind,
        repository=valid.repository,
        pr_number=valid.pr_number,
        diff=valid.diff,
        scope=valid.scope,
        review_mode=valid.review_mode,
        rab_id=valid.rab_id,
        review_generation=valid.review_generation,
        merge_commit=valid.merge_commit,
        merge_tree=valid.merge_tree,
        unresolved_state=valid.unresolved_state,
        review_world_id='f' * 64,
    )
    import pytest
    with pytest.raises(rw.ReviewWorldError, match='Review World|review_world_id'):
        c.check_github_currentness(forged, forged, rab_authorized=True)


def test_currentness_rejects_direct_forged_local_world_identity():
    scope = rw.ReviewScope.repository()
    valid = rw.LocalReviewWorld.create(repository='o/r', local_snapshot_id='2' * 64, scope=scope, rab_id=R, review_generation='g')
    forged = rw.LocalReviewWorld(
        schema_version=valid.schema_version,
        kind=valid.kind,
        repository=valid.repository,
        local_snapshot_id=valid.local_snapshot_id,
        scope=valid.scope,
        rab_id=valid.rab_id,
        review_generation=valid.review_generation,
        review_world_id='f' * 64,
    )
    import pytest
    with pytest.raises(rw.ReviewWorldError, match='Review World|review_world_id'):
        c.check_local_currentness(forged, forged, rab_authorized=True)
