from __future__ import annotations

from pathlib import Path

from main_review.static_async_lifecycle_review import run_static_async_lifecycle_review


def _roots(result: dict) -> set[str]:
    return {str(item.get("root_cause")) for item in result.get("findings", [])}


def test_resource_claim_after_await_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "server.py"
    source.write_text(
        """
async def start(self, payload, session_id):
    for client_conn in self.connections:
        if client_conn.websocket and not client_conn.session_id:
            await client_conn.websocket.send_text(payload)
            client_conn.session_id = session_id
        """,
        encoding="utf-8",
    )
    result = run_static_async_lifecycle_review(tmp_path, ["server.py"])
    assert "resource-claim-after-await" in _roots(result)


def test_resource_claim_before_await_with_failure_release_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "server.py"
    source.write_text(
        """
async def start(self, payload, session_id):
    for client_conn in self.connections:
        if client_conn.websocket and not client_conn.session_id:
            client_conn.session_id = session_id
            try:
                await client_conn.websocket.send_text(payload)
            except Exception:
                client_conn.session_id = None
        """,
        encoding="utf-8",
    )
    result = run_static_async_lifecycle_review(tmp_path, ["server.py"])
    assert "resource-claim-after-await" not in _roots(result)


def test_locked_availability_check_and_claim_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "server.py"
    source.write_text(
        """
async def start(self, payload, session_id):
    async with self.connection_lock:
        for client_conn in self.connections:
            if client_conn.websocket and not client_conn.session_id:
                await client_conn.websocket.send_text(payload)
                client_conn.session_id = session_id
        """,
        encoding="utf-8",
    )
    result = run_static_async_lifecycle_review(tmp_path, ["server.py"])
    assert "resource-claim-after-await" not in _roots(result)


def test_unrelated_assignment_after_await_is_clean(tmp_path: Path) -> None:
    source = tmp_path / "server.py"
    source.write_text(
        """
async def refresh(self):
    if not self.cached_result:
        result = await self.fetch_result()
        self.cached_result = result
        """,
        encoding="utf-8",
    )
    result = run_static_async_lifecycle_review(tmp_path, ["server.py"])
    assert "resource-claim-after-await" not in _roots(result)


def test_terminal_status_omitted_from_end_timestamp_is_reported(tmp_path: Path) -> None:
    package = tmp_path / "browser"
    package.mkdir()
    (package / "sessions.py").write_text(
        """
import time

def update_session(status):
    updates = []
    if status in ("completed", "failed", "stopped"):
        updates.append("ended_at = ?")
        updates.append(time.time())
        """,
        encoding="utf-8",
    )
    (package / "server.py").write_text(
        """
def cleanup(manager):
    manager.update_session("session", status="cancelled")
        """,
        encoding="utf-8",
    )
    result = run_static_async_lifecycle_review(
        tmp_path,
        ["browser/sessions.py", "browser/server.py"],
    )
    assert "terminal-state-without-end-timestamp" in _roots(result)


def test_complete_terminal_timestamp_set_is_clean(tmp_path: Path) -> None:
    package = tmp_path / "browser"
    package.mkdir()
    (package / "sessions.py").write_text(
        """
import time

def update_session(status):
    updates = []
    if status in ("completed", "failed", "stopped", "cancelled"):
        updates.append("ended_at = ?")
        updates.append(time.time())
        """,
        encoding="utf-8",
    )
    (package / "server.py").write_text(
        """
def cleanup(manager):
    manager.update_session("session", status="cancelled")
        """,
        encoding="utf-8",
    )
    result = run_static_async_lifecycle_review(
        tmp_path,
        ["browser/sessions.py", "browser/server.py"],
    )
    assert "terminal-state-without-end-timestamp" not in _roots(result)
