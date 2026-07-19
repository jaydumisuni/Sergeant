from __future__ import annotations

from pathlib import Path

from main_review.static_status_review import run_static_status_review
from main_review.static_transfer_13_review import run_static_transfer_13_review


GOROUTINE_ROOT = "detached-goroutine-without-panic-containment"
SELECTOR_ROOT = "documented-default-selector-forwarded-without-resolution"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_detached_anonymous_goroutine_without_recover_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "worker.go"
    source.write_text(
        '''
package worker

func start(w *Worker) {
    go func() {
        w.Refresh()
    }()
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["worker.go"])

    assert GOROUTINE_ROOT in _roots(result)


def test_detached_anonymous_goroutine_with_entry_recover_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "worker.go"
    source.write_text(
        '''
package worker

func start(w *Worker) {
    go func() {
        defer func() {
            if recovered := recover(); recovered != nil {
                log.Printf("background refresh panic: %v", recovered)
            }
        }()
        w.Refresh()
    }()
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["worker.go"])

    assert GOROUTINE_ROOT not in _roots(result)


def test_direct_detached_function_without_recover_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "sweep.go"
    source.write_text(
        '''
package worker

func launch(store *Store) {
    go sweep(store)
}

func sweep(store *Store) {
    store.DeleteExpired()
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["sweep.go"])

    assert GOROUTINE_ROOT in _roots(result)


def test_direct_detached_function_with_local_recover_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "sweep.go"
    source.write_text(
        '''
package worker

func launch(store *Store) {
    go sweep(store)
}

func sweep(store *Store) {
    defer func() {
        if recovered := recover(); recovered != nil {
            log.Printf("sweep panic: %v", recovered)
        }
    }()
    store.DeleteExpired()
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["sweep.go"])

    assert GOROUTINE_ROOT not in _roots(result)


def test_structured_errgroup_task_is_not_misclassified_as_detached(tmp_path: Path) -> None:
    source = tmp_path / "worker.go"
    source.write_text(
        '''
package worker

func start(group *errgroup.Group, w *Worker) {
    group.Go(func() error {
        return w.Refresh()
    })
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["worker.go"])

    assert GOROUTINE_ROOT not in _roots(result)


def test_documented_empty_selector_forwarded_without_resolution_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "supervisor.go"
    source.write_text(
        '''
package supervisor

// CreateOptions has a valid zero value: an empty Model resolves to the configured default.
type CreateOptions struct {
    Model string
    Root string
}

func (s *Supervisor) Create(ctx context.Context, opts CreateOptions) error {
    return s.runner.New(ctx, runner.Options{
        Model: opts.Model,
        Root: opts.Root,
    })
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["supervisor.go"])

    assert SELECTOR_ROOT in _roots(result)


def test_documented_empty_selector_resolved_before_forwarding_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "supervisor.go"
    source.write_text(
        '''
package supervisor

// CreateOptions has a valid zero value: an empty Model resolves to the configured default.
type CreateOptions struct {
    Model string
}

func (s *Supervisor) Create(ctx context.Context, opts CreateOptions) error {
    if opts.Model == "" {
        opts.Model = s.defaultModel
    }
    return s.runner.New(ctx, runner.Options{Model: opts.Model})
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["supervisor.go"])

    assert SELECTOR_ROOT not in _roots(result)


def test_required_selector_with_empty_guard_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "supervisor.go"
    source.write_text(
        '''
package supervisor

// CreateOptions requires Model to be set by the caller.
type CreateOptions struct {
    Model string
}

func (s *Supervisor) Create(ctx context.Context, opts CreateOptions) error {
    if opts.Model == "" {
        return ErrNoModel
    }
    return s.runner.New(ctx, runner.Options{Model: opts.Model})
}
        ''',
        encoding="utf-8",
    )

    result = run_static_transfer_13_review(tmp_path, ["supervisor.go"])

    assert SELECTOR_ROOT not in _roots(result)


def test_status_bundle_exposes_both_transfer_13_roots(tmp_path: Path) -> None:
    goroutine = tmp_path / "worker.go"
    goroutine.write_text(
        '''
package worker

func start(w *Worker) {
    go func() { w.Refresh() }()
}
        ''',
        encoding="utf-8",
    )
    selector = tmp_path / "supervisor.go"
    selector.write_text(
        '''
package supervisor

// CreateOptions has a valid zero value: empty Backend resolves to the default backend.
type CreateOptions struct {
    Backend string
}

func (s *Supervisor) Create(opts CreateOptions) error {
    return s.runtime.Start(RuntimeOptions{Backend: opts.Backend})
}
        ''',
        encoding="utf-8",
    )

    result = run_static_status_review(tmp_path, ["worker.go", "supervisor.go"])

    assert {GOROUTINE_ROOT, SELECTOR_ROOT}.issubset(_roots(result))
    assert result["static_transfer_13_review"]["finding_count"] == 2
