from copy import deepcopy
import pytest
import main_review.review_world as rw
import main_review.review_authority_bundle as rab
R = '1' * 64
A = 'a' * 40
B = 'b' * 40
C = 'c' * 40
D = 'd' * 40

def make_world():
    s = rw.ReviewScope.selected_paths(['src/a.py'])
    d = rw.GitHubDiffIdentity.create(repository='owner/repo', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    return rw.GitHubReviewWorld.create(repository='owner/repo', pr_number=7, diff=d, scope=s, review_mode='head', rab_id=R, review_generation='sae10-v1')

def test_review_world_round_trip_verifies_embedded_ids():
    world = make_world()
    recovered = rw.GitHubReviewWorld.from_payload(world.to_payload())
    assert recovered == world

def test_scope_tamper_with_old_id_is_rejected():
    payload = make_world().to_payload()
    payload['scope']['paths'] = ['src/b.py']
    with pytest.raises(rw.ReviewWorldError, match='scope_id mismatch'):
        rw.GitHubReviewWorld.from_payload(payload)

def test_diff_tamper_with_old_id_is_rejected():
    payload = make_world().to_payload()
    payload['diff']['base_commit'] = 'e' * 40
    with pytest.raises(rw.ReviewWorldError, match='diff_id mismatch'):
        rw.GitHubReviewWorld.from_payload(payload)

def test_world_tamper_with_old_id_is_rejected():
    payload = make_world().to_payload()
    payload['review_generation'] = 'sae10-v2'
    with pytest.raises(rw.ReviewWorldError, match='review_world_id mismatch'):
        rw.GitHubReviewWorld.from_payload(payload)

def test_unknown_fields_fail_closed():
    payload = make_world().to_payload()
    payload['latest_compatible_authority'] = True
    with pytest.raises(rw.ReviewWorldError, match='unexpected fields'):
        rw.GitHubReviewWorld.from_payload(payload)

def comp(name, seed='a'):
    return rab.RABComponent.active(name=name, generation='g1', content_id=seed * 64, authority_domain='sergeant')

def test_rab_round_trip_verifies_embedded_id():
    bundle = rab.ReviewAuthorityBundle.create(root_authority=comp('root_authority'))
    assert rab.ReviewAuthorityBundle.from_payload(bundle.to_payload()) == bundle

def test_rab_component_tamper_with_old_id_is_rejected():
    bundle = rab.ReviewAuthorityBundle.create(root_authority=comp('root_authority'))
    payload = deepcopy(bundle.to_payload())
    payload['components']['root_authority']['generation'] = 'g2'
    with pytest.raises(rab.ReviewAuthorityBundleError, match='rab_id mismatch'):
        rab.ReviewAuthorityBundle.from_payload(payload)

def test_authorization_set_round_trip_and_tamper_check():
    bundle = rab.ReviewAuthorityBundle.create(root_authority=comp('root_authority'))
    auth = rab.RABAuthorizationSet.create([rab.RABAuthorization.authorized(bundle.rab_id, 'auth-g1', 'root')])
    assert rab.RABAuthorizationSet.from_payload(auth.to_payload()) == auth
    payload = deepcopy(auth.to_payload())
    payload['records'][0]['authorization_generation'] = 'auth-g2'
    with pytest.raises(rab.ReviewAuthorityBundleError, match='authorization_set_id mismatch'):
        rab.RABAuthorizationSet.from_payload(payload)

def test_scope_payload_with_duplicate_paths_is_rejected_even_with_recomputed_id():
    scope = rw.ReviewScope.selected_paths(['src/a.py', 'src/b.py'])
    payload = scope.to_payload()
    payload['paths'] = ['src/a.py', 'src/a.py', 'src/b.py']
    payload['scope_id'] = rw.sha256_id({k: v for k, v in payload.items() if k != 'scope_id'})
    with pytest.raises(rw.ReviewWorldError, match='(?:mismatch|non-canonical)'):
        rw.ReviewScope.from_payload(payload)

def test_world_numeric_type_coercion_is_rejected_even_with_recomputed_id():
    payload = make_world().to_payload()
    payload['pr_number'] = 7.0
    body = {k: v for k, v in payload.items() if k != 'review_world_id'}
    payload['review_world_id'] = rw.sha256_id(body)
    with pytest.raises(rw.ReviewWorldError, match='(?:mismatch|non-canonical)'):
        rw.GitHubReviewWorld.from_payload(payload)

def test_authorized_record_with_reason_is_rejected_not_normalized():
    bundle = rab.ReviewAuthorityBundle.create(root_authority=comp('root_authority'))
    auth = rab.RABAuthorizationSet.create([rab.RABAuthorization.authorized(bundle.rab_id, 'auth-g1', 'root')])
    payload = deepcopy(auth.to_payload())
    payload['records'][0]['reason'] = 'candidate explanation'
    payload['authorization_set_id'] = rw.sha256_id({'schema_version': payload['schema_version'], 'records': payload['records']})
    with pytest.raises(rab.ReviewAuthorityBundleError, match='authorized.*reason|non-canonical|mismatch'):
        rab.RABAuthorizationSet.from_payload(payload)

def test_authorized_record_standalone_reason_is_rejected():
    bundle = rab.ReviewAuthorityBundle.create(root_authority=comp('root_authority'))
    record = rab.RABAuthorization.authorized(bundle.rab_id, 'auth-g1', 'root').to_payload()
    record['reason'] = 'not allowed'
    with pytest.raises(rab.ReviewAuthorityBundleError, match='authorized.*reason|non-canonical'):
        rab.RABAuthorization.from_payload(record)

def test_scope_payload_duplicate_paths_rejected_even_with_canonical_deduplicated_id():
    scope = rw.ReviewScope.selected_paths(['src/a.py', 'src/b.py'])
    payload = scope.to_payload()
    payload['paths'] = ['src/a.py', 'src/a.py', 'src/b.py']
    with pytest.raises(rw.ReviewWorldError, match='non-canonical'):
        rw.ReviewScope.from_payload(payload)
