from __future__ import annotations

import pytest

import main_review.review_authority_bundle as rab


def active(slot: str, generation: str, seed: str = "a") -> object:
    return rab.RABComponent.active(
        name=slot,
        generation=generation,
        content_id=seed * 64,
        authority_domain="sergeant-assurance",
    )


def test_individually_known_components_do_not_authorize_new_combination() -> None:
    first = rab.ReviewAuthorityBundle.create(
        epistemic_constitution=active("epistemic_constitution", "g1", "a")
    )
    second = rab.ReviewAuthorityBundle.create(
        epistemic_constitution=active("epistemic_constitution", "g2", "b")
    )
    trusted = rab.RABAuthorizationSet.create([
        rab.RABAuthorization.authorized(
            first.rab_id, "root-gen-1", "OWNER_ROOT_CONSTITUTIONAL_TCB"
        )
    ])
    result = rab.authorize_rab(second, trusted)
    assert result.authorized is False
    assert result.reason == "rab_not_authorized_as_whole"


def test_exact_rab_id_is_authorized_as_whole() -> None:
    bundle = rab.ReviewAuthorityBundle.create(
        epistemic_constitution=active("epistemic_constitution", "g1", "a")
    )
    trusted = rab.RABAuthorizationSet.create([
        rab.RABAuthorization.authorized(
            bundle.rab_id, "root-gen-1", "OWNER_ROOT_CONSTITUTIONAL_TCB"
        )
    ])
    result = rab.authorize_rab(bundle, trusted)
    assert result.authorized is True
    assert result.reason == "authorized"


def test_candidate_manifest_cannot_authorize_itself() -> None:
    candidate = rab.ReviewAuthorityBundle.create(
        epistemic_constitution=active("epistemic_constitution", "candidate-g2", "c")
    )
    trusted = rab.RABAuthorizationSet.create([])
    result = rab.authorize_rab(candidate, trusted)
    assert result.authorized is False
    assert result.reason == "rab_not_authorized_as_whole"


def test_mutable_alias_is_rejected_as_component_generation() -> None:
    with pytest.raises(rab.ReviewAuthorityBundleError, match="mutable authority alias"):
        rab.RABComponent.active(
            name="epistemic_constitution",
            generation="latest",
            content_id="a" * 64,
            authority_domain="sergeant-assurance",
        )


def test_omitted_future_slots_are_explicitly_inactive_and_hashed() -> None:
    bundle = rab.ReviewAuthorityBundle.create(
        root_authority=active("root_authority", "root-g1", "d")
    )
    payload = bundle.to_payload()
    slots = payload["components"]
    assert isinstance(slots, dict)
    assert set(slots) == set(rab.RAB_SLOTS)
    assert slots["qualification_authority_registry"]["lifecycle_state"] == "inactive_not_yet_established"
    assert len(bundle.rab_id) == 64


def test_revoked_exact_rab_is_not_usable() -> None:
    bundle = rab.ReviewAuthorityBundle.create(
        root_authority=active("root_authority", "root-g1", "e")
    )
    trusted = rab.RABAuthorizationSet.create([
        rab.RABAuthorization.revoked(
            bundle.rab_id, "root-gen-2", "OWNER_ROOT_CONSTITUTIONAL_TCB", "superseded"
        )
    ])
    result = rab.authorize_rab(bundle, trusted)
    assert result.authorized is False
    assert result.reason == "rab_revoked"


def test_duplicate_authorization_records_fail_closed() -> None:
    bundle = rab.ReviewAuthorityBundle.create(
        root_authority=active("root_authority", "root-g1", "f")
    )
    record = rab.RABAuthorization.authorized(
        bundle.rab_id, "root-gen-1", "OWNER_ROOT_CONSTITUTIONAL_TCB"
    )
    with pytest.raises(rab.ReviewAuthorityBundleError, match="duplicate"):
        rab.RABAuthorizationSet.create([record, record])
