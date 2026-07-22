from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from main_review import cloudflare_cli
from main_review.cloudflare_gateway import (
    CloudflareGatewayError,
    CloudflareGatewaySettings,
    build_server,
    is_loopback_host,
)


def settings(**overrides: object) -> CloudflareGatewaySettings:
    values = {
        "account_id": "0123456789abcdef0123456789abcdef",
        "api_token": "secret-token",
        "models": (
            "@cf/zai-org/glm-4.7-flash",
            "@cf/openai/gpt-oss-120b",
        ),
        "host": "127.0.0.1",
        "port": 0,
        "timeout_seconds": 10.0,
        "max_request_bytes": 100_000,
    }
    values.update(overrides)
    return CloudflareGatewaySettings(**values)  # type: ignore[arg-type]


def _start_gateway(configured: CloudflareGatewaySettings) -> tuple[object, threading.Thread, int]:
    server = build_server(configured)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, int(server.server_address[1])


def _stop_gateway(server: object, thread: threading.Thread) -> None:
    server.shutdown()  # type: ignore[attr-defined]
    server.server_close()  # type: ignore[attr-defined]
    thread.join(timeout=3)


def test_public_settings_never_expose_credentials() -> None:
    payload = settings().public_dict()

    assert payload["configured"] is True
    assert payload["api_token_present"] is True
    assert "secret-token" not in json.dumps(payload)
    assert "api_token" not in payload


def test_account_id_must_be_32_character_hexadecimal() -> None:
    with pytest.raises(CloudflareGatewayError, match="32-character hexadecimal"):
        settings(account_id="account-123").validate()


def test_gateway_is_loopback_only() -> None:
    assert is_loopback_host("127.0.0.1") is True
    assert is_loopback_host("localhost") is True

    with pytest.raises(CloudflareGatewayError, match="loopback-only"):
        settings(host="0.0.0.0").validate()


def test_model_roster_is_required_and_cloudflare_scoped() -> None:
    with pytest.raises(CloudflareGatewayError, match="At least one"):
        settings(models=()).validate()

    with pytest.raises(CloudflareGatewayError, match="@cf/"):
        settings(models=("not-cloudflare",)).validate()


def test_gateway_exposes_openai_compatible_model_list() -> None:
    configured = settings()
    server, thread, port = _start_gateway(configured)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=3) as response:
            payload = json.loads(response.read())
        assert [item["id"] for item in payload["data"]] == list(configured.models)
    finally:
        _stop_gateway(server, thread)


def test_gateway_rejects_models_outside_roster_as_client_error() -> None:
    server, thread, port = _start_gateway(settings())
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=json.dumps({"model": "@cf/unknown/model", "messages": [{"role": "user", "content": "hello"}]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as raised:
            urllib.request.urlopen(request, timeout=3)
        assert raised.value.code == 400
        assert "not in the configured Cloudflare roster" in raised.value.read().decode()
    finally:
        _stop_gateway(server, thread)


def test_gateway_rejects_streaming_and_missing_messages_as_client_errors() -> None:
    server, thread, port = _start_gateway(settings())
    try:
        for payload, expected in (
            ({"model": "@cf/zai-org/glm-4.7-flash", "messages": [{"role": "user", "content": "hello"}], "stream": True}, "Streaming"),
            ({"model": "@cf/zai-org/glm-4.7-flash"}, "messages array"),
        ):
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with pytest.raises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=3)
            assert raised.value.code == 400
            assert expected in raised.value.read().decode()
    finally:
        _stop_gateway(server, thread)


def test_cloudflare_route_exposes_full_model_roster() -> None:
    route = cloudflare_cli.cloudflare_route(settings())

    assert route.provider == "cloudflare-workers-ai"
    assert route.protocol == "chat_completions"
    assert route.model == "@cf/zai-org/glm-4.7-flash"
    assert route.discovered_models == settings().models
    assert route.base_url.endswith("/ai/v1")


def test_model_proof_calls_every_configured_model(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def fake_invoke(route: object, *, system_prompt: str, user_prompt: str) -> dict[str, object]:
        model = getattr(route, "model")
        called.append(model)
        return {"status": "ready", "model": model, "capabilities": ["structured_json", "reasoning"]}

    monkeypatch.setattr(cloudflare_cli, "invoke_json", fake_invoke)

    result = cloudflare_cli.test_models(settings())

    assert result["all_passed"] is True
    assert result["passed_count"] == 2
    assert called == list(settings().models)


def test_model_proof_rejects_incomplete_structured_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cloudflare_cli,
        "invoke_json",
        lambda *args, **kwargs: {"status": "ready", "model": getattr(args[0], "model")},
    )

    result = cloudflare_cli.test_models(settings())

    assert result["all_passed"] is False
    assert result["passed_count"] == 0


def test_council_proof_requires_complete_real_model_independence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.py"
    source.write_text("def add(left, right):\n    return left + right\n", encoding="utf-8")

    def fake_review(*args: object, **kwargs: object) -> dict[str, object]:
        return {
            "status": "completed",
            "verdict": "NEEDS WORK",
            "passes": [
                {"model": "@cf/zai-org/glm-4.7-flash"},
                {"model": "@cf/openai/gpt-oss-120b"},
            ],
            "errors": [],
            "council": {
                "true_model_independence": True,
                "complete": True,
                "final_gaps": [],
            },
        }

    monkeypatch.setattr(cloudflare_cli, "run_cpl_review", fake_review)

    result = cloudflare_cli.run_council_proof(
        settings(),
        root=tmp_path,
        changed_files=["sample.py"],
    )

    assert result["passed"] is True
    assert result["true_model_independence"] is True
    assert result["council_complete"] is True
    assert result["distinct_models"] == [
        "@cf/openai/gpt-oss-120b",
        "@cf/zai-org/glm-4.7-flash",
    ]


def test_council_proof_uses_raw_effective_findings_after_product_adjudication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    finding = {
        "severity": "blocker",
        "category": "security",
        "path": "sample.py",
        "line_start": 2,
        "line_end": 2,
        "message": "Untrusted input reaches shell execution.",
        "evidence": "subprocess.run(command, shell=True)",
        "evidence_verified": True,
    }
    passes = [
        {"model": "@cf/zai-org/glm-4.7-flash", "findings": [finding]},
        {"model": "@cf/openai/gpt-oss-120b", "findings": [finding]},
    ]
    monkeypatch.setattr(
        cloudflare_cli,
        "run_cpl_review",
        lambda *args, **kwargs: {
            "status": "completed",
            "verdict": "BLOCK",
            "findings": [],
            "passes": passes,
            "errors": [],
            "council": {
                "true_model_independence": True,
                "complete": True,
                "final_gaps": [],
                "effective_findings": [finding],
                "adjudicated_findings": [],
            },
        },
    )

    result = cloudflare_cli.run_council_proof(
        settings(),
        root=tmp_path,
        changed_files=["sample.py"],
        expected_verdict="BLOCK",
        expected_path="sample.py",
        expected_category="security",
        expected_severity="blocker",
        expected_evidence="shell=True",
        minimum_supporting_models=2,
    )

    assert result["passed"] is True
    assert result["expected_finding"]["passed"] is True
    assert result["expected_finding"]["matches"][0]["support_count"] == 2


@pytest.mark.parametrize(
    ("status", "complete", "errors", "gaps"),
    [
        ("completed_with_warnings", True, ["provider warning"], []),
        ("completed", False, [], [{"type": "missing_report"}]),
        ("completed", True, [], [{"type": "unanswered_question"}]),
    ],
)
def test_council_proof_rejects_failed_or_incomplete_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
    complete: bool,
    errors: list[str],
    gaps: list[dict[str, str]],
) -> None:
    monkeypatch.setattr(
        cloudflare_cli,
        "run_cpl_review",
        lambda *args, **kwargs: {
            "status": status,
            "verdict": "PASS",
            "passes": [
                {"model": "@cf/zai-org/glm-4.7-flash"},
                {"model": "@cf/openai/gpt-oss-120b"},
            ],
            "errors": errors,
            "council": {
                "true_model_independence": True,
                "complete": complete,
                "final_gaps": gaps,
            },
        },
    )

    result = cloudflare_cli.run_council_proof(settings(), root=tmp_path, changed_files=["sample.py"])

    assert result["passed"] is False


def test_council_proof_rejects_single_model_roster(tmp_path: Path) -> None:
    with pytest.raises(CloudflareGatewayError, match="at least two"):
        cloudflare_cli.run_council_proof(
            settings(models=("@cf/zai-org/glm-4.7-flash",)),
            root=tmp_path,
            changed_files=["sample.py"],
        )


def test_shell_environment_output_uses_native_safe_quoting() -> None:
    values = {"SERGEANT_CPL_MODEL": "$(echo pwned)'value"}

    bash = cloudflare_cli._render_shell(values, "bash")
    powershell = cloudflare_cli._render_shell(values, "powershell")

    assert bash == "export SERGEANT_CPL_MODEL='$(echo pwned)'\"'\"'value'"
    assert powershell == "$env:SERGEANT_CPL_MODEL='$(echo pwned)''value'"
