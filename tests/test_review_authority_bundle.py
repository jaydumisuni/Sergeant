import pytest
import main_review.review_authority_bundle as r

def comp(name, g, seed='a'):
    return r.RABComponent.active(name=name, generation=g, content_id=seed * 64, authority_domain='sergeant')

def test_exact_authorized():
    b = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'g1'))
    a = r.RABAuthorizationSet.create([r.RABAuthorization.authorized(b.rab_id, 'auth1', 'root')])
    assert r.authorize_rab(b, a).authorized

def test_combination_not_authorized():
    b1 = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'g1', 'a'))
    b2 = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'g2', 'b'))
    a = r.RABAuthorizationSet.create([r.RABAuthorization.authorized(b1.rab_id, 'auth1', 'root')])
    assert r.authorize_rab(b2, a).reason == 'rab_not_authorized_as_whole'

def test_candidate_no_self_auth():
    b = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'candidate'))
    assert not r.authorize_rab(b, r.RABAuthorizationSet.create([])).authorized

def test_latest_rejected():
    with pytest.raises(r.ReviewAuthorityBundleError, match='mutable authority alias'):
        comp('root_authority', 'latest')

def test_future_slots_explicit():
    b = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'g1'))
    p = b.to_payload()
    assert set(p['components']) == set(r.RAB_SLOTS)
    assert p['components']['qualification_authority_registry']['lifecycle_state'] == 'inactive_not_yet_established'

def test_revoked():
    b = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'g1'))
    a = r.RABAuthorizationSet.create([r.RABAuthorization.revoked(b.rab_id, 'auth2', 'root', 'x')])
    assert r.authorize_rab(b, a).reason == 'rab_revoked'

def test_duplicate_record_rejected():
    b = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'g1'))
    x = r.RABAuthorization.authorized(b.rab_id, 'auth', 'root')
    with pytest.raises(r.ReviewAuthorityBundleError, match='duplicate'):
        r.RABAuthorizationSet.create([x, x])

def test_forged_unknown_authorization_state_is_never_accepted():
    b = r.ReviewAuthorityBundle.create(root_authority=comp('root_authority', 'g1'))
    forged = r.RABAuthorization(
        rab_id=b.rab_id,
        state='forged',
        authorization_generation='auth1',
        root_basis='root',
        reason=None,
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='invalid RAB authorization state'):
        r.RABAuthorizationSet.create([forged])

@pytest.mark.parametrize('state,generation,content_id,basis', [
    ('active', 'g1', 'a' * 64, None),
    ('inactive_not_yet_established', None, None, 'not established'),
    ('prohibited', None, None, 'prohibited by authority'),
])
def test_direct_component_construction_rejects_empty_authority_domain(state, generation, content_id, basis):
    forged = r.RABComponent(
        name='root_authority',
        lifecycle_state=state,
        generation=generation,
        content_id=content_id,
        basis=basis,
        authority_domain='',
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='authority_domain'):
        r.ReviewAuthorityBundle.create(root_authority=forged)


def test_direct_component_construction_rejects_noncanonical_authority_domain():
    forged = r.RABComponent(
        name='root_authority',
        lifecycle_state='active',
        generation='g1',
        content_id='a' * 64,
        basis=None,
        authority_domain=' sergeant ',
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='authority_domain'):
        r.ReviewAuthorityBundle.create(root_authority=forged)

@pytest.mark.parametrize('state,basis', [
    ('inactive_not_yet_established', 'not established'),
    ('prohibited', 'prohibited by authority'),
])
def test_direct_inactive_component_rejects_noncanonical_authority_domain(state, basis):
    forged = r.RABComponent(
        name='root_authority',
        lifecycle_state=state,
        generation=None,
        content_id=None,
        basis=basis,
        authority_domain='alternate-domain',
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='authority_domain'):
        r.ReviewAuthorityBundle.create(root_authority=forged)


def test_direct_active_component_rejects_noncanonical_generation():
    forged = r.RABComponent(
        name='root_authority',
        lifecycle_state='active',
        generation=' g1 ',
        content_id='a' * 64,
        basis=None,
        authority_domain='sergeant',
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='generation'):
        r.ReviewAuthorityBundle.create(root_authority=forged)


@pytest.mark.parametrize('state', ['inactive_not_yet_established', 'prohibited'])
def test_direct_inactive_component_rejects_noncanonical_basis(state):
    forged = r.RABComponent(
        name='root_authority',
        lifecycle_state=state,
        generation=None,
        content_id=None,
        basis=' padded basis ',
        authority_domain='sergeant-assurance',
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='basis'):
        r.ReviewAuthorityBundle.create(root_authority=forged)

@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('authority_domain', 123),
        ('generation', 123),
        ('content_id', int('1' * 64)),
    ],
)
def test_direct_active_rab_component_rejects_non_string_authority_fields(field, value):
    values = dict(
        name='root_authority',
        lifecycle_state='active',
        generation='g1',
        content_id='a' * 64,
        basis=None,
        authority_domain='sergeant',
    )
    values[field] = value
    component = r.RABComponent(**values)
    with pytest.raises(r.ReviewAuthorityBundleError, match=field):
        r.ReviewAuthorityBundle.create(root_authority=component)


def test_direct_inactive_rab_component_rejects_non_string_basis():
    component = r.RABComponent(
        name='root_authority',
        lifecycle_state='inactive_not_yet_established',
        generation=None,
        content_id=None,
        basis=123,
        authority_domain='sergeant-assurance',
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='basis'):
        r.ReviewAuthorityBundle.create(root_authority=component)


def test_direct_authorization_set_rejects_noncanonical_record_order():
    first = r.RABAuthorization.authorized('b' * 64, 'auth-g1', 'root')
    second = r.RABAuthorization.authorized('a' * 64, 'auth-g1', 'root')
    records = (first, second)
    body = {
        'schema_version': 'sergeant.rab-authorization-set.v1',
        'records': [record.to_payload() for record in records],
    }
    forged = r.RABAuthorizationSet(
        'sergeant.rab-authorization-set.v1',
        records,
        __import__('main_review.review_world', fromlist=['sha256_id']).sha256_id(body),
    )
    with pytest.raises(r.ReviewAuthorityBundleError, match='order|canonical'):
        forged.expected_id()
