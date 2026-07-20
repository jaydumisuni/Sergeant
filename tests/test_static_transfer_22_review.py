from __future__ import annotations

from pathlib import Path

from main_review.static_status_review import run_static_status_review
from main_review.static_transfer_22_review import run_static_transfer_22_review


SQL_ROOT = "compound-sql-in-lookup-preserves-null-members"
RUST_ROOT = "concurrent-unsigned-distance-subtracts-independent-state-marker"
PARTITION_ROOT = "partition-local-fallback-preempts-global-identity-match"
URI_ROOT = "canonical-resource-uri-discarded-before-identity-lookup"


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_compound_sql_in_lookup_must_elide_null_members(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "tuple_lookup.py",
        """
class TupleIn(TupleLookupMixin, In):
    def process_rhs(self, compiler, connection):
        rhs = self.rhs
        if not rhs:
            raise EmptyResultSet
        result = []
        lhs = self.lhs
        for vals in rhs:
            result.append(Tuple(*[Value(val) for col, val in zip(lhs, vals)]))
        return compiler.compile(Tuple(*result))

    def get_fallback_sql(self, compiler, connection):
        rhs = self.rhs
        if not rhs:
            raise EmptyResultSet
        root = WhereNode([])
        lhs = self.lhs
        for vals in rhs:
            root.children.append(WhereNode([Exact(col, val) for col, val in zip(lhs, vals)]))
        return root.as_sql(compiler, connection)
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["tuple_lookup.py"])

    assert SQL_ROOT in _roots(result)


def test_compound_sql_in_lookup_with_null_elision_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "tuple_lookup.py",
        """
class TupleIn(TupleLookupMixin, In):
    def process_rhs(self, compiler, connection):
        rhs = self.rhs
        result = []
        lhs = self.lhs
        for vals in rhs:
            if any(val is None for val in vals):
                continue
            result.append(Tuple(*[Value(val) for col, val in zip(lhs, vals)]))
        if not result:
            raise EmptyResultSet
        return compiler.compile(Tuple(*result))
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["tuple_lookup.py"])

    assert SQL_ROOT not in _roots(result)


def test_ordinary_nested_collection_transform_is_not_sql_lookup(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "collection.py",
        """
class BatchBuilder:
    def build(self, rhs):
        result = []
        for vals in rhs:
            result.append(tuple(value for value in vals))
        return result
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["collection.py"])

    assert SQL_ROOT not in _roots(result)


def test_concurrent_unsigned_length_subtracts_inconsistent_marker(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "list.rs",
        """
impl<T> Rx<T> {
    pub(crate) fn len(&self, tx: &Tx<T>) -> usize {
        let tail_position = tx.tail_position.load(Acquire);
        tail_position - self.index - (tx.is_closed() as usize)
    }
}
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["list.rs"])

    assert RUST_ROOT in _roots(result)


def test_concurrent_unsigned_length_with_wrapping_and_guard_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "list.rs",
        """
impl<T> Rx<T> {
    pub(crate) fn len(&self, tx: &Tx<T>) -> usize {
        let tail_position = tx.tail_position.load(Acquire);
        let mut len = tail_position.wrapping_sub(self.index);
        if len == 0 {
            return 0;
        }
        if self.is_maybe_closed(tx, tail_position.wrapping_sub(1)) {
            len -= 1;
        }
        len
    }
}
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["list.rs"])

    assert RUST_ROOT not in _roots(result)


def test_unsigned_distance_without_independent_marker_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "list.rs",
        """
impl<T> Rx<T> {
    pub(crate) fn len(&self, tx: &Tx<T>) -> usize {
        let tail_position = tx.tail_position.load(Acquire);
        tail_position - self.index
    }
}
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["list.rs"])

    assert RUST_ROOT not in _roots(result)


def test_partition_local_data_fallback_can_preempt_later_uri(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "carousel.ts",
        """
export function findClickedImageIndex(sections: Section[], resource: URI, data?: Uint8Array): number {
    let globalOffset = 0;
    for (const section of sections) {
        const localIndex = findImageInList(section.images, resource, data);
        if (localIndex >= 0) {
            return globalOffset + localIndex;
        }
        globalOffset += section.images.length;
    }
    return -1;
}

function findImageInList(images: Image[], resource: URI, data?: Uint8Array): number {
    const uriStr = resource.toString();
    const byUri = images.findIndex(img => img.id === uriStr);
    if (byUri >= 0) {
        return byUri;
    }
    const byParsedUri = images.findIndex(img => URI.parse(img.id).toString() === uriStr);
    if (byParsedUri >= 0) {
        return byParsedUri;
    }
    if (data) {
        const wrapped = Buffer.wrap(data);
        return images.findIndex(img => Buffer.wrap(img.data).equals(wrapped));
    }
    return -1;
}
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["carousel.ts"])

    assert PARTITION_ROOT in _roots(result)


def test_global_uri_pass_before_data_fallback_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "carousel.ts",
        """
export function findClickedImageIndex(sections: Section[], resource: URI, data?: Uint8Array): number {
    let globalOffset = 0;
    for (const section of sections) {
        const localIndex = findImageInListByUri(section.images, resource);
        if (localIndex >= 0) {
            return globalOffset + localIndex;
        }
        globalOffset += section.images.length;
    }
    if (!data) {
        return -1;
    }
    globalOffset = 0;
    for (const section of sections) {
        const localIndex = findImageInListByData(section.images, data);
        if (localIndex >= 0) {
            return globalOffset + localIndex;
        }
        globalOffset += section.images.length;
    }
    return -1;
}

function findImageInListByUri(images: Image[], resource: URI): number {
    return images.findIndex(img => img.id === resource.toString());
}
function findImageInListByData(images: Image[], data: Uint8Array): number {
    const wrapped = Buffer.wrap(data);
    return images.findIndex(img => Buffer.wrap(img.data).equals(wrapped));
}
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["carousel.ts"])

    assert PARTITION_ROOT not in _roots(result)


def test_projection_must_preserve_canonical_resource_uri(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "carousel.ts",
        """
function deduplicateConsecutiveImages(images: ExtractedImage[]): ExtractedImage[] {
    return images.filter((img, index) => index === 0 || images[index - 1].uri.toString() !== img.uri.toString());
}
function build(images: ExtractedImage[]) {
    const dedupedImages = deduplicateConsecutiveImages(images);
    return dedupedImages.map(({ id, name, data }) => ({ id, name, data }));
}
function locate(images: Image[], resource: URI) {
    return images.findIndex(img => URI.parse(img.id).toString() === resource.toString());
}
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["carousel.ts"])

    assert URI_ROOT in _roots(result)


def test_projection_using_uri_as_identity_is_clean(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "carousel.ts",
        """
function deduplicateConsecutiveImages(images: ExtractedImage[]): ExtractedImage[] {
    return images.filter((img, index) => index === 0 || images[index - 1].uri.toString() !== img.uri.toString());
}
function build(images: ExtractedImage[]) {
    const dedupedImages = deduplicateConsecutiveImages(images);
    return dedupedImages.map(({ uri, name, data }) => ({ id: uri.toString(), name, data }));
}
function locate(images: Image[], resource: URI) {
    return images.findIndex(img => URI.parse(img.id).toString() === resource.toString());
}
""",
    )

    result = run_static_transfer_22_review(tmp_path, ["carousel.ts"])

    assert URI_ROOT not in _roots(result)


def test_normal_static_status_path_admits_transfer_22_roots(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "list.rs",
        """
impl<T> Rx<T> {
    pub(crate) fn len(&self, tx: &Tx<T>) -> usize {
        let tail_position = tx.tail_position.load(Acquire);
        tail_position - self.index - (tx.is_closed() as usize)
    }
}
""",
    )

    result = run_static_status_review(tmp_path, ["list.rs"])

    assert RUST_ROOT in _roots(result)
