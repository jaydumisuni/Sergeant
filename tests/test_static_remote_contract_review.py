from __future__ import annotations

from pathlib import Path

from main_review.static_remote_contract_review import run_static_remote_contract_review
from main_review.static_status_review import run_static_status_review


ROOT = "remote-collection-contract-violation-collapsed-to-empty"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_remote_list_shape_violation_returning_empty_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "trip_service.dart"
    source.write_text(
        """
class TripService {
  final ApiClient _apiClient;

  Future<List<Map<String, dynamic>>> fetchTripItems(String tripId) async {
    final body = await _apiClient.get('/api/trips/$tripId/items');
    if (body is! List) return [];
    return List<Map<String, dynamic>>.from(body);
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_remote_contract_review(tmp_path, ["trip_service.dart"])

    assert ROOT in _roots(result)


def test_remote_list_shape_violation_raising_contract_error_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "trip_service.dart"
    source.write_text(
        """
class TripService {
  final ApiClient _apiClient;

  Future<List<Map<String, dynamic>>> fetchTripItems(String tripId) async {
    final body = await _apiClient.get('/api/trips/$tripId/items');
    if (body is! List) {
      throw StateError('Unexpected trip items response type');
    }
    return List<Map<String, dynamic>>.from(body);
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_remote_contract_review(tmp_path, ["trip_service.dart"])

    assert ROOT not in _roots(result)


def test_optional_local_cache_miss_returning_empty_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "cache.dart"
    source.write_text(
        """
Future<List<Map<String, dynamic>>> loadCachedTrips(LocalStore store) async {
  final body = await store.read('trip-cache');
  if (body is! List) return [];
  return List<Map<String, dynamic>>.from(body);
}
        """,
        encoding="utf-8",
    )

    result = run_static_remote_contract_review(tmp_path, ["cache.dart"])

    assert ROOT not in _roots(result)


def test_status_bundle_exposes_remote_contract_root(tmp_path: Path) -> None:
    source = tmp_path / "trip_service.dart"
    source.write_text(
        """
class TripService {
  final ApiClient _apiClient;

  Future<List<Map<String, dynamic>>> fetchTripItems(String tripId) async {
    final body = await _apiClient.get('/api/trips/$tripId/items');
    if (body is! List) return const [];
    return List<Map<String, dynamic>>.from(body);
  }
}
        """,
        encoding="utf-8",
    )

    result = run_static_status_review(tmp_path, ["trip_service.dart"])

    assert ROOT in _roots(result)
