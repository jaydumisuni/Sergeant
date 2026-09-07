"""Python reference implementation for the frozen SAE-R1 authority encoding.

Rust must implement the same specification independently. This module is a
reference/vector producer only; it is not imported by the Rust crate.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import re
from typing import Mapping, Sequence


class RustIdentityError(ValueError):
    """Raised when an authority object cannot be canonically encoded."""


_AUTHORITY_RE = re.compile(r"^[0-9a-f]{64}$")
_PREFIX = b"SERGEANT-AUTHORITY-V1\x00"


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise RustIdentityError(f"{field} must be canonical and non-empty")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise RustIdentityError(f"{field} must be valid UTF-8") from exc
    return value


def _u32(length: int) -> bytes:
    if length < 0 or length > 0xFFFFFFFF:
        raise RustIdentityError("canonical value exceeds u32 length bound")
    return length.to_bytes(4, "big")


def _blob(data: bytes) -> bytes:
    return _u32(len(data)) + data


class AuthorityValueKind(str, Enum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    LIST = "list"
    OBJECT = "object"
    BYTES = "bytes"
    NULL = "null"


@dataclass(frozen=True)
class AuthorityValue:
    kind: AuthorityValueKind
    value: object

    @classmethod
    def string(cls, value: str) -> "AuthorityValue":
        return cls(AuthorityValueKind.STRING, _text(value, "authority string"))

    @classmethod
    def boolean(cls, value: bool) -> "AuthorityValue":
        if not isinstance(value, bool):
            raise RustIdentityError("authority boolean must be bool")
        return cls(AuthorityValueKind.BOOLEAN, value)

    @classmethod
    def integer(cls, value: int) -> "AuthorityValue":
        if not isinstance(value, int) or isinstance(value, bool) or not (-(1 << 63) <= value < (1 << 63)):
            raise RustIdentityError("authority integer must be canonical signed 64-bit integer")
        return cls(AuthorityValueKind.INTEGER, value)

    @classmethod
    def list(cls, values: Sequence["AuthorityValue"]) -> "AuthorityValue":
        if isinstance(values, (str, bytes)):
            raise RustIdentityError("authority list must be a non-string sequence")
        normalized = tuple(values)
        if not all(isinstance(item, AuthorityValue) for item in normalized):
            raise RustIdentityError("authority list members must be AuthorityValue")
        return cls(AuthorityValueKind.LIST, normalized)

    @classmethod
    def object(cls, fields: Mapping[str, "AuthorityValue"]) -> "AuthorityValue":
        return cls(AuthorityValueKind.OBJECT, _fields(fields))

    @classmethod
    def bytes(cls, value: bytes) -> "AuthorityValue":
        if not isinstance(value, bytes):
            raise RustIdentityError("authority bytes value must be bytes")
        return cls(AuthorityValueKind.BYTES, value)

    @classmethod
    def null(cls) -> "AuthorityValue":
        return cls(AuthorityValueKind.NULL, None)

    def encode(self) -> bytes:
        if self.kind is AuthorityValueKind.STRING:
            return b"s" + _blob(str(self.value).encode("utf-8"))
        if self.kind is AuthorityValueKind.BOOLEAN:
            return b"b" + (b"\x01" if self.value is True else b"\x00")
        if self.kind is AuthorityValueKind.INTEGER:
            return b"i" + int(self.value).to_bytes(8, "big", signed=True)
        if self.kind is AuthorityValueKind.LIST:
            values = self.value
            assert isinstance(values, tuple)
            return b"l" + _u32(len(values)) + b"".join(item.encode() for item in values)
        if self.kind is AuthorityValueKind.OBJECT:
            fields = self.value
            assert isinstance(fields, tuple)
            return b"o" + _encode_fields(fields)
        if self.kind is AuthorityValueKind.BYTES:
            value = self.value
            assert isinstance(value, bytes)
            return b"x" + _blob(value)
        if self.kind is AuthorityValueKind.NULL:
            return b"n"
        raise RustIdentityError("unsupported authority value kind")


def _fields(fields: Mapping[str, AuthorityValue]) -> tuple[tuple[str, AuthorityValue], ...]:
    if not isinstance(fields, Mapping):
        raise RustIdentityError("authority fields must be a mapping")
    normalized: list[tuple[str, AuthorityValue]] = []
    for key, value in fields.items():
        key = _text(key, "authority field name")
        if not isinstance(value, AuthorityValue):
            raise RustIdentityError(f"authority field {key!r} is not AuthorityValue")
        normalized.append((key, value))
    normalized.sort(key=lambda item: item[0].encode("utf-8"))
    names = [name for name, _ in normalized]
    if len(set(names)) != len(names):
        raise RustIdentityError("authority object contains duplicate field name")
    return tuple(normalized)


def _encode_fields(fields: tuple[tuple[str, AuthorityValue], ...]) -> bytes:
    encoded = [_u32(len(fields))]
    for name, value in fields:
        encoded.append(_blob(name.encode("utf-8")))
        encoded.append(value.encode())
    return b"".join(encoded)


@dataclass(frozen=True)
class AuthorityObject:
    kind: str
    fields: tuple[tuple[str, AuthorityValue], ...]

    @classmethod
    def create(cls, *, kind: str, fields: Mapping[str, AuthorityValue]) -> "AuthorityObject":
        return cls(_text(kind, "authority object kind"), _fields(fields))


def canonical_authority_bytes(value: AuthorityObject) -> bytes:
    if not isinstance(value, AuthorityObject):
        raise RustIdentityError("AuthorityObject is required")
    return _PREFIX + _blob(value.kind.encode("utf-8")) + _encode_fields(value.fields)


def authority_id(value: AuthorityObject) -> str:
    return hashlib.sha256(canonical_authority_bytes(value)).hexdigest()


def require_authority_id(value: object) -> str:
    if not isinstance(value, str) or not _AUTHORITY_RE.fullmatch(value):
        raise RustIdentityError("authority id must be a full lowercase 64-hex SHA-256 digest")
    return value


def frozen_vector_object(family: str) -> AuthorityObject:
    """Canonical object used by both implementations for frozen vector proof."""
    family = _text(family, "vector family")
    return AuthorityObject.create(
        kind=family,
        fields={
            "active": AuthorityValue.boolean(True),
            "count": AuthorityValue.integer(1),
            "domain": AuthorityValue.string(f"{family}.v1"),
            "generation": AuthorityValue.string("g1"),
            "refs": AuthorityValue.list((AuthorityValue.string("a"), AuthorityValue.string("b"))),
            "scope": AuthorityValue.object({"a": AuthorityValue.string("x"), "z": AuthorityValue.integer(2)}),
        },
    )
