from __future__ import annotations

import json

import pytest

from main_review import llm_provider


def _route() -> llm_provider.LLMRoute:
    return llm_provider.LLMRoute(
        provider="cloudflare-workers-ai",
        base_url="https://api.cloudflare.com/client/v4/accounts/0123456789abcdef0123456789abcdef/ai/v1",
        model="@cf/qwen/qwq-32b",
        protocol="chat_completions",
        api_key="secret",
        max_output_tokens=1200,
    )


def test_extracts_nested_structured_result_response() -> None:
    expected = {
        "status": "ready",
        "model": "@cf/qwen/qwq-32b",
        "verdict": "NEEDS WORK",
        "coverage": {"files_reviewed": ["src/session.py"]},
        "finding": {"path": "src/session.py", "severity": "major"},
    }

    text = llm_provider._extract_text(
        {"success": True, "result": {"response": expected, "tool_calls": [], "usage": {}}},
        "chat_completions",
    )

    assert json.loads(text) == expected


def test_native_fallback_returns_nested_structured_object(monkeypatch) -> None:
    expected = {
        "status": "ready",
        "model": "@cf/qwen/qwq-32b",
        "verdict": "NEEDS WORK",
        "coverage": {"areas": ["concurrency"]},
        "finding": {"path": "src/session.py", "severity": "major"},
    }
    responses = iter(
        [
            {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]},
            {"success": True, "result": {"response": expected, "tool_calls": [], "usage": {}}},
        ]
    )

    monkeypatch.setattr(
        llm_provider,
        "_load_json_response",
        lambda request, timeout: next(responses),
    )

    assert llm_provider.invoke_json(_route(), system_prompt="system", user_prompt="user") == expected


def test_metadata_dictionary_is_not_promoted_to_model_output() -> None:
    assert llm_provider._text_value({"usage": {"input_tokens": 10}}) == ""

    with pytest.raises(llm_provider.LLMProviderError, match="did not contain text output"):
        llm_provider._extract_text(
            {"success": True, "result": {"response": {"usage": {"input_tokens": 10}}}},
            "chat_completions",
        )


def test_existing_text_response_envelope_is_unchanged() -> None:
    assert llm_provider._extract_text(
        {"result": {"response": '{"status":"ready"}'}},
        "chat_completions",
    ) == '{"status":"ready"}'
