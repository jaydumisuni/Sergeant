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


def test_keep_alive_notifier_state_after_await_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "sacred_location_provider.dart"
    source.write_text(
        """
@Riverpod(keepAlive: true)
class SacredLocationNotifier extends _$SacredLocationNotifier {
  Future<void> setManualCity(Location loc) async {
    final prefs = await SharedPreferences.getInstance();
    await writeLocation(prefs, loc);
    state = loc;
    ref.invalidate(inIsraelProvider);
  }
}
        """,
        encoding="utf-8",
    )
    result = run_static_dart_provider_lifetime_review(
        tmp_path,
        ["sacred_location_provider.dart"],
    )
    assert "disposed-provider-ref-after-await" in _roots(result)


def test_lifecycle_helper_called_after_await_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "sacred_location_provider.dart"
    source.write_text(
        """
@Riverpod(keepAlive: true)
class SacredLocationNotifier extends _$SacredLocationNotifier {
  Future<void> setManualCoords(Location loc) async {
    state = loc;
    final prefs = await SharedPreferences.getInstance();
    await writeLocation(prefs, loc);
    await _pushSnapshot();
  }

  Future<void> _pushSnapshot() async {
    await ref.read(syncProvider)?.pushSnapshot();
  }
}
        """,
        encoding="utf-8",
    )
    result = run_static_dart_provider_lifetime_review(
        tmp_path,
        ["sacred_location_provider.dart"],
    )
    assert "disposed-provider-ref-after-await" in _roots(result)


def test_mounted_guard_before_lifecycle_helper_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "sacred_location_provider.dart"
    source.write_text(
        """
@Riverpod(keepAlive: true)
class SacredLocationNotifier extends _$SacredLocationNotifier {
  Future<void> setManualCoords(Location loc) async {
    state = loc;
    final prefs = await SharedPreferences.getInstance();
    await writeLocation(prefs, loc);
    if (!ref.mounted) return;
    await _pushSnapshot();
  }

  Future<void> _pushSnapshot() async {
    await ref.read(syncProvider)?.pushSnapshot();
  }
}
        """,
        encoding="utf-8",
    )
    result = run_static_dart_provider_lifetime_review(
        tmp_path,
        ["sacred_location_provider.dart"],
    )
    assert "disposed-provider-ref-after-await" not in _roots(result)
