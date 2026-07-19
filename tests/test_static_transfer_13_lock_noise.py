from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_13_review import run_static_transfer_13_review


ROOT = "detached-goroutine-without-panic-containment"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_anonymous_lock_scoped_counter_mutation_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "counter.go"
    source.write_text(
        """package internal
func update() {
    go func() {
        mu.Lock()
        sharedCounter++
        mu.Unlock()
    }()
}
""",
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["counter.go"])

    assert ROOT not in _roots(result)


def test_direct_lock_scoped_counter_mutation_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "counter.go"
    source.write_text(
        """package internal
func update() { go increment() }
func increment() {
    mu.Lock()
    sharedCounter += 1
    mu.Unlock()
}
""",
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["counter.go"])

    assert ROOT not in _roots(result)


def test_lock_scoped_arbitrary_store_call_still_gates(tmp_path: Path) -> None:
    source = tmp_path / "worker.go"
    source.write_text(
        """package internal
func update(store *Store) {
    go func() {
        mu.Lock()
        store.Refresh()
        mu.Unlock()
    }()
}
""",
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["worker.go"])

    assert ROOT in _roots(result)
