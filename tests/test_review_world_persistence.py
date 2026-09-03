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
    with pytest.raises(rw.ReviewWorldError, match='(?:positive integer|mismatch|non-canonical)'):
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

# SAE-10 v6 persisted Review World canonical decode hostile regressions.

def test_scope_decode_rejects_numeric_generation_with_canonical_id():
    canonical = rw.ReviewScope._create(kind='selected_paths', paths=['src/a.py'], generation='1')
    payload = canonical.to_payload(); payload['generation'] = 1
    with pytest.raises(rw.ReviewWorldError): rw.ReviewScope.from_payload(payload)

def _scope():
    return rw.ReviewScope.selected_paths(['src/a.py'])

def _diff(*, repository='owner/repo', base_commit=A, algorithm_generation='git-tree-transition-v1'):
    s = _scope()
    return rw.GitHubDiffIdentity.create(repository=repository, base_commit=base_commit, base_tree=C, head_commit=B, head_tree=D, scope=s, algorithm_generation=algorithm_generation)

def _world(*, repository='owner/repo', pr_number=7, rab_id=R, review_generation='sae10-v1'):
    s = _scope(); d = rw.GitHubDiffIdentity.create(repository='owner/repo', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    return rw.GitHubReviewWorld.create(repository=repository, pr_number=pr_number, diff=d, scope=s, review_mode='head', rab_id=rab_id, review_generation=review_generation)

def _local(*, repository='owner/repo', local_snapshot_id=R, rab_id=R, review_generation='sae10-v1'):
    return rw.LocalReviewWorld.create(repository=repository, local_snapshot_id=local_snapshot_id, scope=_scope(), rab_id=rab_id, review_generation=review_generation)

def test_diff_decode_rejects_repository_case_normalization_with_canonical_id():
    canonical=_diff(); payload=canonical.to_payload(); payload['repository']='Owner/Repo'
    with pytest.raises(rw.ReviewWorldError): rw.GitHubDiffIdentity.from_payload(payload, scope=_scope())

def test_diff_decode_rejects_numeric_git_id_with_canonical_id():
    digits='1'*40; canonical=_diff(base_commit=digits); payload=canonical.to_payload(); payload['base_commit']=int(digits)
    with pytest.raises(rw.ReviewWorldError): rw.GitHubDiffIdentity.from_payload(payload, scope=_scope())

def test_diff_decode_rejects_numeric_algorithm_generation_with_canonical_id():
    canonical=_diff(algorithm_generation='1'); payload=canonical.to_payload(); payload['algorithm_generation']=1
    with pytest.raises(rw.ReviewWorldError): rw.GitHubDiffIdentity.from_payload(payload, scope=_scope())

def test_github_world_decode_rejects_repository_case_normalization_with_canonical_id():
    canonical=_world(); payload=canonical.to_payload(); payload['repository']='Owner/Repo'
    with pytest.raises(rw.ReviewWorldError): rw.GitHubReviewWorld.from_payload(payload)

def test_github_world_decode_rejects_string_pr_number_with_canonical_id():
    canonical=_world(); payload=canonical.to_payload(); payload['pr_number']='7'
    with pytest.raises(rw.ReviewWorldError): rw.GitHubReviewWorld.from_payload(payload)

def test_github_world_decode_rejects_numeric_rab_id_with_canonical_id():
    canonical=_world(); payload=canonical.to_payload(); payload['rab_id']=int(R)
    with pytest.raises(rw.ReviewWorldError): rw.GitHubReviewWorld.from_payload(payload)

def test_github_world_decode_rejects_numeric_review_generation_with_canonical_id():
    canonical=_world(review_generation='1'); payload=canonical.to_payload(); payload['review_generation']=1
    with pytest.raises(rw.ReviewWorldError): rw.GitHubReviewWorld.from_payload(payload)

def test_github_world_decode_rejects_empty_unresolved_entry_that_would_disappear():
    canonical=_world(); payload=canonical.to_payload(); payload['unresolved_state']=['']
    with pytest.raises(rw.ReviewWorldError): rw.GitHubReviewWorld.from_payload(payload)

def test_local_world_decode_rejects_empty_repository_becoming_none():
    canonical=_local(repository=None); payload=canonical.to_payload(); payload['repository']=''
    with pytest.raises(rw.ReviewWorldError): rw.LocalReviewWorld.from_payload(payload)

def test_local_world_decode_rejects_repository_case_normalization_with_canonical_id():
    canonical=_local(); payload=canonical.to_payload(); payload['repository']='Owner/Repo'
    with pytest.raises(rw.ReviewWorldError): rw.LocalReviewWorld.from_payload(payload)

def test_local_world_decode_rejects_numeric_snapshot_id_with_canonical_id():
    canonical=_local(); payload=canonical.to_payload(); payload['local_snapshot_id']=int(R)
    with pytest.raises(rw.ReviewWorldError): rw.LocalReviewWorld.from_payload(payload)

def test_local_world_decode_rejects_numeric_rab_id_with_canonical_id():
    canonical=_local(); payload=canonical.to_payload(); payload['rab_id']=int(R)
    with pytest.raises(rw.ReviewWorldError): rw.LocalReviewWorld.from_payload(payload)

def test_local_world_decode_rejects_numeric_review_generation_with_canonical_id():
    canonical=_local(review_generation='1'); payload=canonical.to_payload(); payload['review_generation']=1
    with pytest.raises(rw.ReviewWorldError): rw.LocalReviewWorld.from_payload(payload)

# SAE-10 v7 construction/persistence symmetry hostile regressions.

def test_scope_create_rejects_numeric_generation_before_hashing():
    with pytest.raises(rw.ReviewWorldError, match='generation must be a string'):
        rw.ReviewScope._create(kind='selected_paths', paths=['src/a.py'], generation=1)

def test_diff_create_rejects_numeric_algorithm_generation_before_hashing():
    with pytest.raises(rw.ReviewWorldError, match='algorithm_generation must be a string'):
        rw.GitHubDiffIdentity.create(repository='owner/repo', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=_scope(), algorithm_generation=1)

def test_github_world_create_rejects_numeric_review_generation_before_hashing():
    s = _scope()
    d = rw.GitHubDiffIdentity.create(repository='owner/repo', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    with pytest.raises(rw.ReviewWorldError, match='review_generation must be a string'):
        rw.GitHubReviewWorld.create(repository='owner/repo', pr_number=7, diff=d, scope=s, review_mode='head', rab_id=R, review_generation=1)

def test_local_world_create_rejects_numeric_review_generation_before_hashing():
    with pytest.raises(rw.ReviewWorldError, match='review_generation must be a string'):
        rw.LocalReviewWorld.create(repository='owner/repo', local_snapshot_id=R, scope=_scope(), rab_id=R, review_generation=1)

def test_direct_diff_validation_rejects_numeric_algorithm_generation():
    s = _scope()
    body = {
        'schema_version': 'sergeant.github-diff-identity.v1',
        'repository': 'owner/repo',
        'base_commit': A,
        'base_tree': C,
        'head_commit': B,
        'head_tree': D,
        'algorithm_generation': 1,
        'scope_id': s.scope_id,
    }
    forged = rw.GitHubDiffIdentity('sergeant.github-diff-identity.v1', 'owner/repo', A, C, B, D, 1, s.scope_id, rw.sha256_id(body))
    with pytest.raises(rw.ReviewWorldError, match='algorithm_generation must be a string'):
        forged.validate()


class _BlankStringableUnresolved:

    def __str__(self):
        return ''


def test_github_world_create_rejects_invalid_unresolved_entries_before_collapse():
    s = _scope()
    d = rw.GitHubDiffIdentity.create(repository='owner/repo', base_commit=A, base_tree=C, head_commit=B, head_tree=D, scope=s)
    bad_entries = ('', '   ', None, 7, False, _BlankStringableUnresolved())
    for bad_entry in bad_entries:
        expected = 'unresolved_state entries must be non-empty' if isinstance(bad_entry, str) else 'unresolved_state entries must be strings'
        with pytest.raises(rw.ReviewWorldError, match=expected):
            rw.GitHubReviewWorld.create(
                repository='owner/repo',
                pr_number=7,
                diff=d,
                scope=s,
                review_mode='head',
                rab_id=R,
                review_generation='sae10-v1',
                unresolved_state=[bad_entry],
            )
