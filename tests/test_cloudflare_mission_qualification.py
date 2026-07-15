from __future__ import annotations

from pathlib import Path

import pytest

from main_review import cloudflare_cli
from main_review.cloudflare_gateway import CloudflareGatewaySettings


def settings() -> CloudflareGatewaySettings:
    return CloudflareGatewaySettings(
        account_id="0123456789abcdef0123456789abcdef",
        api_token="secret-token",
        models=("@cf/qwen/model-a", "@cf/openai/model-b"),
        host="127.0.0.1",
        port=0,
        timeout_seconds=75.0,
        max_request_bytes=100_000,
    )


def fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    path = root / "src" / "auth.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        "import subprocess\n\n"
        "def run_user_command(request):\n"
        "    command = request.args.get(\"command\")\n"
        "    return subprocess.run(command, shell=True)\n",
        encoding="utf-8",
    )
    return root


def valid_payload() -> dict[str, object]:
    return {
        "verdict": "BLOCK",
        "confidence": 0.96,
        "summary": "User input reaches shell execution.",
        "findings": [
            {
                "severity": "blocker",
                "category": "security",
                "path": "src/auth.py",
                "line_start": 5,
                "line_end": 5,
                "message": "Untrusted command reaches shell execution.",
                "evidence": "return subprocess.run(command, shell=True)",
                "why_it_matters": "An attacker can execute arbitrary shell commands.",
                "safer_alternative": "Pass a validated argument vector with shell disabled.",
            }
        ],
        "unanswered_questions": [],
        "coverage": {"files_reviewed": ["src/auth.py"], "areas": ["security"]},
    }


def test_mission_qualification_admits_only_full_officer_contracts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = fixture(tmp_path)

    def fake_invoke(route: object, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        if getattr(route, "model").endswith("model-a"):
            return valid_payload()
        return {"status": "ready", "model": getattr(route, "model"), "capabilities": ["structured_json", "reasoning"]}

    monkeypatch.setattr(cloudflare_cli, "invoke_json", fake_invoke)
    result = cloudflare_cli.qualify_models(
        settings(),
        root=root,
        changed_files=["src/auth.py"],
        expected_verdict="BLOCK",
        expected_path="src/auth.py",
        expected_category="security",
        expected_severity="blocker",
        expected_evidence="shell=True",
    )

    assert result["passed_count"] == 1
    assert result["qualified_models"] == ["@cf/qwen/model-a"]
    assert result["models"][0]["passed"] is True
    assert result["models"][1]["passed"] is False


def test_mission_qualification_rejects_unverified_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = fixture(tmp_path)
    payload = valid_payload()
    payload["findings"][0]["evidence"] = "not present in the file"
    monkeypatch.setattr(cloudflare_cli, "invoke_json", lambda *args, **kwargs: payload)

    result = cloudflare_cli.qualify_models(
        settings(),
        root=root,
        changed_files=["src/auth.py"],
        expected_verdict="BLOCK",
        expected_path="src/auth.py",
        expected_category="security",
        expected_severity="blocker",
        expected_evidence="shell=True",
    )

    assert result["passed_count"] == 0
    assert all(item["passed"] is False for item in result["models"])


def test_live_workflow_uses_mission_qualified_two_member_roster() -> None:
    workflow = (Path(__file__).parents[1] / ".github" / "workflows" / "cloudflare-live-certification.yml").read_text(encoding="utf-8")

    assert "qualify-models build/live-council-fixture" in workflow
    assert "build/cloudflare-mission-model-proof.json" in workflow
    assert 'SERGEANT_CPL_MAX_PASSES: "2"' in workflow
    assert 'SERGEANT_CPL_MAX_COUNCIL_MEMBERS: "2"' in workflow
