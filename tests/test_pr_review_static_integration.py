from __future__ import annotations

import json
from pathlib import Path

from main_review.cli import main


def _make_verified_repo(root: Path, source: str) -> None:
    (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "server.py").write_text(source, encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_server.py").write_text("def test_placeholder(): assert True\n", encoding="utf-8")
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


def _run_cli(root: Path, capsys, monkeypatch) -> dict:
    monkeypatch.setenv("SERGEANT_LLM_ENABLED", "false")
    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "false")
    monkeypatch.setenv("SERGEANT_CPL_POLICY", "disabled")
    exit_code = main(
        [
            "pr-review",
            str(root),
            "--files",
            "src/server.py,tests/test_server.py",
            "--pretty",
        ]
    )
    assert exit_code == 0
    return json.loads(capsys.readouterr().out)


def _admitted_roots(packet: dict) -> set[str]:
    return {
        str(item.get("root_cause"))
        for item in packet.get("officer_council", {}).get("admitted_findings", [])
        if isinstance(item, dict)
    }


def test_documented_pr_review_cli_admits_claim_after_await(tmp_path: Path, capsys, monkeypatch) -> None:
    _make_verified_repo(
        tmp_path,
        """
async def start(self, payload, session_id):
    for client_conn in self.connections:
        if client_conn.websocket and not client_conn.session_id:
            await client_conn.websocket.send_text(payload)
            client_conn.session_id = session_id
""",
    )

    packet = _run_cli(tmp_path, capsys, monkeypatch)

    assert "resource-claim-after-await" in _admitted_roots(packet)
    assert packet["verdict"]["verdict"] == "REQUEST_CHANGES"
    invariant_roots = {
        str(item.get("root_cause"))
        for item in packet.get("capability_review", {})
        .get("static_invariant_review", {})
        .get("findings", [])
        if isinstance(item, dict)
    }
    assert "resource-claim-after-await" in invariant_roots


def test_documented_pr_review_cli_keeps_claim_before_await_clean(tmp_path: Path, capsys, monkeypatch) -> None:
    _make_verified_repo(
        tmp_path,
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
    )

    packet = _run_cli(tmp_path, capsys, monkeypatch)

    assert "resource-claim-after-await" not in _admitted_roots(packet)
