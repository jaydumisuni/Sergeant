from __future__ import annotations

from pathlib import Path

from main_review.static_transfer_17_review import run_static_transfer_17_review


CONNECTION_ROOT = "reserved-db-connection-escapes-through-prepared-statement"
REVISION_ROOT = "revision-allocating-append-is-not-serialized-through-commit-publication"


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_reserved_connection_must_not_escape_through_statement(tmp_path: Path) -> None:
    source = tmp_path / "generic.go"
    source.write_text(
        '''
package generic
func (d *Generic) prepare(ctx context.Context, query *Named) (*Stmt, error) {
    conn, err := d.DB.Conn(ctx)
    if err != nil { return nil, err }
    stmt, err := conn.PrepareContext(ctx, query.SQL)
    if err != nil { return nil, err }
    return &Stmt{Stmt: stmt}, nil
}
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["generic.go"])

    assert CONNECTION_ROOT in _roots(result)


def test_database_owned_prepare_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "generic.go"
    source.write_text(
        '''
package generic
func (d *Generic) prepare(ctx context.Context, query *Named) (*Stmt, error) {
    stmt, err := d.DB.PrepareContext(ctx, query.SQL)
    if err != nil { return nil, err }
    return &Stmt{Stmt: stmt}, nil
}
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["generic.go"])

    assert CONNECTION_ROOT not in _roots(result)


def test_explicit_connection_close_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "generic.go"
    source.write_text(
        '''
package generic
func (d *Generic) prepareAndRun(ctx context.Context, query *Named) error {
    conn, err := d.DB.Conn(ctx)
    if err != nil { return err }
    defer conn.Close()
    stmt, err := conn.PrepareContext(ctx, query.SQL)
    if err != nil { return err }
    defer stmt.Close()
    return nil
}
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["generic.go"])

    assert CONNECTION_ROOT not in _roots(result)


def test_revision_append_requires_serialized_commit_publication(tmp_path: Path) -> None:
    source = tmp_path / "sql.go"
    source.write_text(
        '''
package sqllog
func (s *SQLLog) Append(ctx context.Context, event *Event) (int64, error) {
    currentRev := s.currentRev.Load()
    rev, err := s.d.Insert(ctx, event.Key)
    if err != nil { return 0, err }
    if s.currentRev.CompareAndSwap(currentRev, rev) {
        select { case s.notify <- rev: default: }
    }
    return rev, nil
}
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["sql.go"])

    assert REVISION_ROOT in _roots(result)


def test_serialized_append_with_monotonic_retry_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "sql.go"
    source.write_text(
        '''
package sqllog
func (s *SQLLog) Append(ctx context.Context, event *Event) (int64, error) {
    s.appendMu.Lock()
    defer s.appendMu.Unlock()
    currentRev := s.currentRev.Load()
    rev, err := s.d.Insert(ctx, event.Key)
    if err != nil { return 0, err }
    for currentRev < rev && !s.currentRev.CompareAndSwap(currentRev, rev) {
        currentRev = s.currentRev.Load()
    }
    select { case s.notify <- rev: default: }
    return rev, nil
}
''',
        encoding="utf-8",
    )

    result = run_static_transfer_17_review(tmp_path, ["sql.go"])

    assert REVISION_ROOT not in _roots(result)
