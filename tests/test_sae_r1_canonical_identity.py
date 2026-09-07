from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _contract():
    assert importlib.util.find_spec("main_review.rust_identity_vectors") is not None, "SAE-R1 Python reference encoder is missing"
    from main_review.rust_identity_vectors import (
        AuthorityObject,
        AuthorityValue,
        RustIdentityError,
        authority_id,
        canonical_authority_bytes,
        require_authority_id,
    )
    return locals()


def test_authority_encoding_is_type_sensitive_and_field_order_canonical() -> None:
    c = _contract()
    first = c["AuthorityObject"].create(
        kind="review-world",
        fields={
            "generation": c["AuthorityValue"].string("g1"),
            "active": c["AuthorityValue"].boolean(True),
            "count": c["AuthorityValue"].integer(1),
        },
    )
    reordered = c["AuthorityObject"].create(
        kind="review-world",
        fields={
            "count": c["AuthorityValue"].integer(1),
            "generation": c["AuthorityValue"].string("g1"),
            "active": c["AuthorityValue"].boolean(True),
        },
    )
    assert c["canonical_authority_bytes"](first) == c["canonical_authority_bytes"](reordered)
    assert c["authority_id"](first) == c["authority_id"](reordered)
    assert c["authority_id"](first) != c["authority_id"](
        c["AuthorityObject"].create(kind="review-world", fields={"count": c["AuthorityValue"].boolean(True), "generation": c["AuthorityValue"].string("g1"), "active": c["AuthorityValue"].boolean(True)})
    )


def test_nested_lists_preserve_order_and_nested_objects_are_canonical() -> None:
    c = _contract()
    value = c["AuthorityValue"]
    one = c["AuthorityObject"].create(
        kind="rab",
        fields={
            "refs": value.list((value.string("a"), value.string("b"))),
            "scope": value.object({"z": value.integer(2), "a": value.string("x")}),
        },
    )
    reordered_object = c["AuthorityObject"].create(
        kind="rab",
        fields={
            "scope": value.object({"a": value.string("x"), "z": value.integer(2)}),
            "refs": value.list((value.string("a"), value.string("b"))),
        },
    )
    reversed_list = c["AuthorityObject"].create(
        kind="rab",
        fields={
            "refs": value.list((value.string("b"), value.string("a"))),
            "scope": value.object({"a": value.string("x"), "z": value.integer(2)}),
        },
    )
    assert c["authority_id"](one) == c["authority_id"](reordered_object)
    assert c["authority_id"](one) != c["authority_id"](reversed_list)


def test_generation_or_domain_substitution_changes_authority_identity() -> None:
    c = _contract()
    value = c["AuthorityValue"]
    base = c["AuthorityObject"].create(kind="acr", fields={"generation": value.string("g1"), "domain": value.string("python.call.v1")})
    changed_generation = c["AuthorityObject"].create(kind="acr", fields={"generation": value.string("g2"), "domain": value.string("python.call.v1")})
    changed_domain = c["AuthorityObject"].create(kind="acr", fields={"generation": value.string("g1"), "domain": value.string("rust.call.v1")})
    assert len({c["authority_id"](base), c["authority_id"](changed_generation), c["authority_id"](changed_domain)}) == 3


def test_authority_ids_must_be_full_lowercase_sha256() -> None:
    c = _contract()
    value = c["AuthorityValue"]
    identifier = c["authority_id"](c["AuthorityObject"].create(kind="ledger", fields={"generation": value.string("g1")}))
    assert c["require_authority_id"](identifier) == identifier
    for bad in (identifier[:16], identifier.upper(), "g" * 64):
        with pytest.raises(c["RustIdentityError"]):
            c["require_authority_id"](bad)


def test_rust_identity_crate_and_frozen_cross_language_vectors_exist() -> None:
    _contract()
    assert (ROOT / "rust/sergeant-assurance-identity/Cargo.toml").is_file()
    assert (ROOT / "rust/sergeant-assurance-identity/src/lib.rs").is_file()
    vector_path = ROOT / "spec/sae-r1-canonical-vectors.txt"
    assert vector_path.is_file()
    text = vector_path.read_text(encoding="utf-8")
    for family in ("review-world", "rab", "acr", "ledger", "collection", "attestation", "provenance", "capsule"):
        assert f"{family}\t" in text
