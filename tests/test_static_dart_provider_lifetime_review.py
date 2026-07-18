from __future__ import annotations

from pathlib import Path

from main_review.static_dart_provider_lifetime_review import run_static_dart_provider_lifetime_review


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_nested_generic_provider_ref_after_await_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "controller.dart"
    source.write_text(
        """
@riverpod
class CategoryController extends _$CategoryController {
  Future<List<CategoryDto>?> build() async {
    final db = ref.watch(databaseProvider);
    final result = await fetchWithFallback(db);
    final sync = ref.read(syncProvider);
    return result;
  }
}
        """,
        encoding="utf-8",
    )
    result = run_static_dart_provider_lifetime_review(tmp_path, ["controller.dart"])
    assert "disposed-provider-ref-after-await" in _roots(result)


def test_nested_generic_dependencies_captured_before_await_are_clean(tmp_path: Path) -> None:
    source = tmp_path / "controller.dart"
    source.write_text(
        """
@riverpod
class CategoryController extends _$CategoryController {
  Future<List<CategoryDto>?> build() async {
    final db = ref.watch(databaseProvider);
    final sync = ref.read(syncProvider);
    final result = await fetchWithFallback(db);
    if (sync != null) sync.publish(result);
    return result;
  }
}
        """,
        encoding="utf-8",
    )
    result = run_static_dart_provider_lifetime_review(tmp_path, ["controller.dart"])
    assert "disposed-provider-ref-after-await" not in _roots(result)
