from __future__ import annotations

import json
from pathlib import Path

from main_review.cli import main


def _make_verified_repo(root: Path) -> None:
    (root / "pyproject.toml").write_text("[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8")
    (root / "main_review").mkdir()
    (root / "tests").mkdir()
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (root / "docs").mkdir()
    for name in (
        "12-external-review-learning-loop.md",
        "19-thetechguy-engineering-standard.md",
        "20-clean-clone-proof.md",
        "21-open-source-reviewer-patterns.md",
    ):
        (root / "docs" / name).write_text("# Doc\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "tests" / "test_server.py").write_text("def test_placeholder(): assert True\n", encoding="utf-8")


def _run_pr_review(root: Path, files: str, capsys) -> dict:
    exit_code = main(["pr-review", str(root), "--files", files])
    assert exit_code == 0
    return json.loads(capsys.readouterr().out)


def _admitted_roots(packet: dict) -> set[str]:
    council = packet.get("officer_council", {})
    return {
        str(item.get("root_cause"))
        for item in council.get("admitted_findings", [])
        if isinstance(item, dict)
    }


def test_documented_pr_review_admits_resource_claim_after_await(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _make_verified_repo(tmp_path)
    monkeypatch.setenv("SERGEANT_LLM_ENABLED", "false")
    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "false")
    monkeypatch.setenv("SERGEANT_CPL_POLICY", "disabled")
    (tmp_path / "src" / "server.py").write_text(
        """
async def start(self, payload, session_id):
    for client_conn in self.connections:
        if client_conn.websocket and not client_conn.session_id:
            await client_conn.websocket.send_text(payload)
            client_conn.session_id = session_id
        """,
        encoding="utf-8",
    )

    packet = _run_pr_review(tmp_path, "src/server.py,tests/test_server.py", capsys)

    assert "resource-claim-after-await" in _admitted_roots(packet)
    assert packet["verdict"]["verdict"] == "REQUEST_CHANGES"
    invariant_roots = {
        str(item.get("root_cause"))
        for item in packet["capability_review"]["static_invariant_review"]["findings"]
    }
    assert "resource-claim-after-await" in invariant_roots


def test_documented_pr_review_requires_real_terminal_state_evidence(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _make_verified_repo(tmp_path)
    monkeypatch.setenv("SERGEANT_LLM_ENABLED", "false")
    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "false")
    monkeypatch.setenv("SERGEANT_CPL_POLICY", "disabled")
    browser = tmp_path / "src" / "browser"
    browser.mkdir()
    (browser / "sessions.py").write_text(
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
    server = browser / "server.py"
    server.write_text(
        """
def cleanup(manager):
    manager.update_session("session", status="cancelled")
        """,
        encoding="utf-8",
    )

    packet = _run_pr_review(
        tmp_path,
        "src/browser/sessions.py,src/browser/server.py,tests/test_server.py",
        capsys,
    )
    assert "terminal-state-without-end-timestamp" in _admitted_roots(packet)

    server.write_text(
        """
def cleanup(manager):
    manager.update_session("session", status="completed")
        """,
        encoding="utf-8",
    )
    clean_packet = _run_pr_review(
        tmp_path,
        "src/browser/sessions.py,src/browser/server.py,tests/test_server.py",
        capsys,
    )
    assert "terminal-state-without-end-timestamp" not in _admitted_roots(clean_packet)
