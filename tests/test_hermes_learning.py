from __future__ import annotations

import json

import pytest

from main_review.hermes_learning import (
    LearningWorkerError,
    WorkerConfig,
    validate_worker_output,
    worker_request,
)


def test_teacher_contract_requires_generalized_controls() -> None:
    packet = {
        "role": "teacher",
        "case_id": "case-a",
        "generalized_mechanism": "resource claim happens after an await",
        "proposed_detector": "track claim ordering across suspension points",
        "positive_tests": ["claim after await"],
        "negative_controls": ["claim before await with rollback"],
        "transfer_languages": ["rust", "java"],
        "confidence": 0.8,
    }
    assert validate_worker_output("teacher", "case-a", packet)["proposed_detector"]


def test_role_and_case_binding_are_strict() -> None:
    with pytest.raises(LearningWorkerError, match="role mismatch"):
        validate_worker_output(
            "teacher",
            "case-a",
            {
                "role": "defender",
                "case_id": "case-a",
                "confidence": 0.5,
            },
        )


def test_defender_verdict_is_bounded() -> None:
    with pytest.raises(LearningWorkerError, match="invalid Defender"):
        validate_worker_output(
            "defender",
            "case-a",
            {
                "role": "defender",
                "case_id": "case-a",
                "verdict": "majority_wins",
                "counterexamples": [],
                "false_positive_risks": [],
                "missing_evidence": [],
                "confidence": 0.5,
            },
        )


def test_hermes_profiles_require_separate_endpoint_and_key(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_LEARNING_BACKEND", "hermes")
    monkeypatch.delenv("SERGEANT_HERMES_TEACHER_URL", raising=False)
    monkeypatch.delenv("SERGEANT_HERMES_TEACHER_KEY", raising=False)
    with pytest.raises(LearningWorkerError, match="Teacher|teacher"):
        WorkerConfig.from_env("teacher")


def test_worker_request_accepts_openai_compatible_hermes_response(monkeypatch) -> None:
    output = {
        "role": "prosecutor",
        "case_id": "case-a",
        "claim": "the old order exposes invalid state",
        "root_cause": "state publication precedes validation",
        "evidence": ["src/runtime.py"],
        "competing_explanations_rejected": ["format-only change"],
        "confidence": 0.9,
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": json.dumps(output)}}]}).encode()

    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    result = worker_request(
        "prosecutor",
        {"case_id": "case-a", "fixing_diff": "diff"},
        config=WorkerConfig(
            role="prosecutor",
            backend="hermes",
            endpoint="http://127.0.0.1:8644/v1/chat/completions",
            token="secret",
            model="prosecutor",
        ),
    )
    assert result["root_cause"] == "state publication precedes validation"
    assert result["transport"]["endpoint_class"] == "isolated-hermes-profile"
    assert result["transport"]["structured_json"] is False


def test_structured_json_request_binds_defender_role_and_exact_case(monkeypatch) -> None:
    output = {
        "role": "defender",
        "case_id": "case-structured",
        "verdict": "needs_more_evidence",
        "counterexamples": ["clean credential boundary with explicit token handoff"],
        "false_positive_risks": ["treating every checkout auth failure as credential leakage"],
        "missing_evidence": ["negative control with a valid isolated credential scope"],
        "confidence": 0.72,
    }
    captured: dict[str, object] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": output}}]}).encode()

    def fake_urlopen(request, *args, **kwargs):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = worker_request(
        "defender",
        {"case_id": "case-structured", "fixing_diff": "diff"},
        config=WorkerConfig(
            role="defender",
            backend="cloudflare",
            endpoint="https://example.invalid/ai/v1/chat/completions",
            token="secret",
            model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            structured_json=True,
        ),
    )

    body = captured["body"]
    response_format = body["response_format"]
    assert response_format["type"] == "json_schema"
    schema = response_format["json_schema"]
    assert schema["properties"]["role"]["enum"] == ["defender"]
    assert schema["properties"]["case_id"]["enum"] == ["case-structured"]
    assert schema["properties"]["verdict"]["enum"] == [
        "supports",
        "rejects",
        "needs_more_evidence",
    ]
    assert set(schema["required"]) == set(schema["properties"])
    assert result["case_id"] == "case-structured"
    assert result["transport"]["structured_json"] is True
