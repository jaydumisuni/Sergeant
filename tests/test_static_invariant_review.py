from __future__ import annotations

from pathlib import Path

from main_review.static_invariant_review import run_static_invariant_review


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_active_session_without_delivery_ack_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "server.py"
    source.write_text(
        """
async def _handle_start_session(self, message, conn):
    sent_to_extension = False
    for candidate in self.connections:
        try:
            await candidate.send(message)
            sent_to_extension = True
        except Exception:
            pass
    return {"status": "running", "start_automation_sent": sent_to_extension}
        """,
        encoding="utf-8",
    )
    assert "active-state-without-delivery-ack" in _roots(run_static_invariant_review(tmp_path, ["server.py"]))


def test_active_session_fail_closed_delivery_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "server.py"
    source.write_text(
        """
async def _handle_start_session(self, message, conn):
    sent_to_extension = False
    for candidate in self.connections:
        await candidate.send(message)
        sent_to_extension = True
    if not sent_to_extension:
        return {"status": "failed", "error": "not delivered"}
    return {"status": "running", "start_automation_sent": True}
        """,
        encoding="utf-8",
    )
    assert "active-state-without-delivery-ack" not in _roots(run_static_invariant_review(tmp_path, ["server.py"]))


def test_go_map_to_persisted_slice_without_sort_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "controller.go"
    source.write_text(
        """
package controller
func mergeConfig() Config {
    secretResourcesMap := make(map[string]bool)
    merged.Spec.KbsSecretResources = make([]string, 0, len(secretResourcesMap))
    for secret := range secretResourcesMap {
        merged.Spec.KbsSecretResources = append(merged.Spec.KbsSecretResources, secret)
    }
    return merged
}
        """,
        encoding="utf-8",
    )
    assert "nondeterministic-persisted-order" in _roots(run_static_invariant_review(tmp_path, ["controller.go"]))


def test_go_map_to_persisted_slice_with_sort_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "controller.go"
    source.write_text(
        """
package controller
func mergeConfig() Config {
    secretResourcesMap := make(map[string]bool)
    merged.Spec.KbsSecretResources = make([]string, 0, len(secretResourcesMap))
    for secret := range secretResourcesMap {
        merged.Spec.KbsSecretResources = append(merged.Spec.KbsSecretResources, secret)
    }
    sort.Strings(merged.Spec.KbsSecretResources)
    return merged
}
        """,
        encoding="utf-8",
    )
    assert "nondeterministic-persisted-order" not in _roots(run_static_invariant_review(tmp_path, ["controller.go"]))


def test_bounded_parser_dereference_without_guard_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "parser.hpp"
    source.write_text(
        """
const char* skip_value(const char* p, const char* end) noexcept {
    switch (*p) {
      case 't': return p + 4;
      default: return p;
    }
}
        """,
        encoding="utf-8",
    )
    assert "cursor-dereference-before-end-check" in _roots(run_static_invariant_review(tmp_path, ["parser.hpp"]))


def test_bounded_parser_guard_before_dereference_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "parser.hpp"
    source.write_text(
        """
const char* skip_value(const char* p, const char* end) noexcept {
    if (p >= end) return p;
    switch (*p) {
      case 't': return p + 4 <= end ? p + 4 : end;
      default: return p;
    }
}
        """,
        encoding="utf-8",
    )
    assert "cursor-dereference-before-end-check" not in _roots(run_static_invariant_review(tmp_path, ["parser.hpp"]))
