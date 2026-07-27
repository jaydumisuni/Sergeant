from __future__ import annotations

from main_review.llm_provider import (
    LLMRoute,
    LLMSettings,
    discover_route,
    select_model,
)


def test_select_model_prefers_open_source_deep_coding_route() -> None:
    models = (
        "provider/random-chat-model",
        "provider/qwen3-coder-next",
        "provider/glm-5.2",
        "provider/kimi-k2.5",
    )

    assert select_model(models) == "provider/glm-5.2"
    assert select_model(models, "provider/qwen3-coder-next") == "provider/qwen3-coder-next"


def test_cpl_settings_are_model_free_by_default(monkeypatch) -> None:
    for name in [
        "SERGEANT_CPL_POLICY",
        "SERGEANT_LLM_POLICY",
        "SERGEANT_CPL_ENABLED",
        "SERGEANT_LLM_ENABLED",
        "SERGEANT_CPL_PROVIDER",
        "SERGEANT_LLM_PROVIDER",
        "SERGEANT_CPL_BASE_URL",
        "SERGEANT_LLM_BASE_URL",
    ]:
        monkeypatch.delenv(name, raising=False)

    settings = LLMSettings.from_environment()

    assert settings.enabled is False
    assert settings.policy == "disabled"
    assert settings.provider == "disabled"


def test_user_can_explicitly_enable_optional_cpl_reasoning_without_exposing_api_key(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CPL_API_KEY", "secret-value")
    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "true")
    monkeypatch.setenv("SERGEANT_CPL_POLICY", "preferred")

    settings = LLMSettings.from_environment()

    assert settings.enabled is True
    assert settings.policy == "preferred"
    assert settings.public_dict()["officer"] == "Cpl"
    assert settings.public_dict()["role"] == "Corporal Specialist"
    assert "api_key" not in settings.public_dict()
    assert "secret-value" not in str(settings.public_dict())


def test_cpl_environment_takes_precedence_over_legacy_llm_environment(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("SERGEANT_CPL_PROVIDER", "cpl")
    monkeypatch.setenv("SERGEANT_LLM_MODEL", "legacy-model")
    monkeypatch.setenv("SERGEANT_CPL_MODEL", "cpl-model")

    settings = LLMSettings.from_environment()

    assert settings.provider == "cpl"
    assert settings.model == "cpl-model"


def test_discover_route_uses_explicit_openai_compatible_endpoint(monkeypatch) -> None:
    settings = LLMSettings(
        enabled=True,
        policy="preferred",
        provider="configured",
        base_url="https://example.invalid/v1",
        model="provider/glm-5.2",
        protocol="chat_completions",
        api_key="token",
        timeout_seconds=30.0,
        max_output_tokens=4000,
    )

    monkeypatch.setattr(
        "main_review.llm_provider.list_models",
        lambda *args, **kwargs: ("provider/glm-5.2", "provider/qwen3-coder-next"),
    )

    route = discover_route(settings)

    assert route == LLMRoute(
        provider="configured",
        base_url="https://example.invalid/v1",
        model="provider/glm-5.2",
        protocol="chat_completions",
        api_key="token",
        timeout_seconds=30.0,
        max_output_tokens=4000,
        discovered_models=("provider/glm-5.2", "provider/qwen3-coder-next"),
    )


def test_discover_route_uses_responses_protocol_for_cpl(monkeypatch) -> None:
    settings = LLMSettings(
        enabled=True,
        policy="preferred",
        provider="cpl",
        base_url="",
        model="",
        protocol="auto",
        api_key="",
        timeout_seconds=30.0,
        max_output_tokens=4000,
    )
    monkeypatch.setattr(
        "main_review.llm_provider.list_models",
        lambda *args, **kwargs: ("gateway/qwen3-coder-next",),
    )

    route = discover_route(settings)

    assert route is not None
    assert route.provider == "cpl"
    assert route.protocol == "responses"
    assert route.model == "gateway/qwen3-coder-next"
    assert route.public_dict()["officer"] == "Cpl"


def test_legacy_gateway_provider_name_is_normalized_to_cpl(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_LLM_PROVIDER", "fcc")
    monkeypatch.delenv("SERGEANT_CPL_PROVIDER", raising=False)

    settings = LLMSettings.from_environment()

    assert settings.provider == "cpl"
