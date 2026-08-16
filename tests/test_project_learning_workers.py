from __future__ import annotations

import json

import pytest

from main_review.hermes_learning import LearningWorkerError
from scripts import project_learning_workers as project_workers
from scripts.project_learning_workers import (
    CLOUDFLARE_ROLE_MODELS,
    _cloudflare_config,
    worker_request,
)


def test_cloudflare_project_learning_reuses_wrangle_oauth_without_persisting_it(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_LEARNING_BACKEND", "cloudflare")
    monkeypatch.delenv("SERGEANT_CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("SERGEANT_CLOUDFLARE_API_TOKEN", raising=False)

    calls: list[tuple[str, ...]] = []

    def fake_wrangler_json(*args: str):
        calls.append(args)
        if args[:2] == ("auth", "token"):
            return {"type": "oauth", "token": "oauth-runtime-secret"}
        return {"accounts": [{"id": "a" * 32, "name": "THETECHGUY"}]}

    monkeypatch.setattr(project_workers, "_wrangler_json", fake_wrangler_json)
    config = _cloudflare_config("teacher")

    assert config.endpoint == f"https://api.cloudflare.com/client/v4/accounts/{'a' * 32}/ai/v1/chat/completions"
    assert config.token == "oauth-runtime-secret"
    assert calls == [("auth", "token", "--json"), ("whoami", "--json")]


def test_cloudflare_project_learning_rejects_ambiguous_wrangle_accounts(monkeypatch) -> None:
    monkeypatch.delenv("SERGEANT_CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("SERGEANT_CLOUDFLARE_API_TOKEN", raising=False)

    def fake_wrangler_json(*args: str):
        if args[:2] == ("auth", "token"):
            return {"type": "api_token", "token": "runtime-secret"}
        return {"accounts": [{"id": "a" * 32}, {"id": "b" * 32}]}

    monkeypatch.setattr(project_workers, "_wrangler_json", fake_wrangler_json)
    with pytest.raises(LearningWorkerError, match="exactly one Account ID"):
        _cloudflare_config("teacher")


def test_cloudflare_project_learning_uses_distinct_role_models(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CLOUDFLARE_ACCOUNT_ID", "a" * 32)
    monkeypatch.setenv("SERGEANT_CLOUDFLARE_API_TOKEN", "secret")
    for role in CLOUDFLARE_ROLE_MODELS:
        monkeypatch.delenv(f"SERGEANT_{role.upper()}_MODEL", raising=False)

    configs = [_cloudflare_config(role) for role in ("teacher", "prosecutor", "defender")]

    assert {config.model for config in configs} == set(CLOUDFLARE_ROLE_MODELS.values())
    assert all(config.backend == "cloudflare" for config in configs)
    assert all(config.endpoint.endswith("/ai/v1/chat/completions") for config in configs)


def test_cloudflare_worker_reuses_bounded_contract_without_exposing_credentials(monkeypatch) -> None:
    output = {
        "role": "teacher",
        "case_id": "case-cloudflare",
        "generalized_mechanism": "producer and verifier must share one path namespace",
        "proposed_detector": "compare manifest entries with verifier working directory",
        "positive_tests": ["nested artifact verified from output root"],
        "negative_controls": ["manifest preserves the nested relative path"],
        "transfer_languages": ["python", "yaml"],
        "confidence": 0.9,
    }
    captured: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": json.dumps(output)}}]}).encode()

    def fake_urlopen(request, *args, **kwargs):
        captured["url"] = request.full_url
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return Response()

    monkeypatch.setenv("SERGEANT_LEARNING_BACKEND", "cloudflare")
    monkeypatch.setenv("SERGEANT_CLOUDFLARE_ACCOUNT_ID", "b" * 32)
    monkeypatch.setenv("SERGEANT_CLOUDFLARE_API_TOKEN", "runtime-secret")
    monkeypatch.delenv("SERGEANT_TEACHER_MODEL", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = worker_request("teacher", {"case_id": "case-cloudflare", "fixing_diff": "diff"})

    assert captured["url"] == f"https://api.cloudflare.com/client/v4/accounts/{'b' * 32}/ai/v1/chat/completions"
    assert captured["body"]["model"] == CLOUDFLARE_ROLE_MODELS["teacher"]
    assert captured["headers"]["authorization"] == "Bearer runtime-secret"
    assert result["transport"] == {
        "backend": "cloudflare",
        "model": CLOUDFLARE_ROLE_MODELS["teacher"],
        "endpoint_class": "cloudflare-workers-ai-direct-terminal",
    }
    serialized = json.dumps(result)
    assert "runtime-secret" not in serialized
    assert "b" * 32 not in serialized
