"""Isolated Teacher, Prosecutor, and Defender workers for Sergeant learning.

Workers accept only a bounded case packet and must return one JSON object. They
have no merge authority and cannot directly alter Sergeant rules. The transport
supports three isolated Hermes API profiles or GitHub Models as a temporary
first-week inference backend.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

ROLES = ("teacher", "prosecutor", "defender")
ROLE_PROMPTS = {
    "teacher": (
        "You are Sergeant's Teacher. Convert a confirmed miss and later fix into a "
        "language-agnostic mechanism. Propose a deterministic detector, positive tests, "
        "adversarial negative controls, and unrelated transfer languages. Do not copy "
        "identifiers from the fixing patch into the detector. Return JSON only."
    ),
    "prosecutor": (
        "You are Sergeant's Prosecutor. Build the strongest evidence-bound case that the "
        "defective revision violates a pre-existing behavioral contract. Distinguish root "
        "cause from symptoms and reject competing explanations. Return JSON only."
    ),
    "defender": (
        "You are Sergeant's Defender. Attempt to disprove the proposed defect and lesson. "
        "Find clean counterexamples, false-positive risks, missing evidence, and overfitting. "
        "A majority vote is irrelevant; executable evidence controls. Return JSON only."
    ),
}


class LearningWorkerError(RuntimeError):
    """Raised when a learning worker transport or contract fails."""


@dataclass(frozen=True)
class WorkerConfig:
    role: str
    backend: str
    endpoint: str
    token: str
    model: str
    timeout_seconds: int = 180

    @classmethod
    def from_env(cls, role: str) -> "WorkerConfig":
        normalized = role.lower().strip()
        if normalized not in ROLES:
            raise LearningWorkerError(f"unknown learning role: {role}")
        backend = os.environ.get("SERGEANT_LEARNING_BACKEND", "github_models").strip().lower()
        suffix = normalized.upper()
        if backend == "hermes":
            endpoint = os.environ.get(f"SERGEANT_HERMES_{suffix}_URL", "").rstrip("/")
            token = os.environ.get(f"SERGEANT_HERMES_{suffix}_KEY", "")
            model = os.environ.get(f"SERGEANT_HERMES_{suffix}_MODEL", normalized)
            if not endpoint or not token:
                raise LearningWorkerError(f"isolated Hermes {normalized} endpoint/key not configured")
            return cls(normalized, backend, f"{endpoint}/v1/chat/completions", token, model)
        if backend == "github_models":
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                raise LearningWorkerError("GITHUB_TOKEN is required for GitHub Models learning")
            model = os.environ.get(f"SERGEANT_{suffix}_MODEL", "openai/gpt-4.1")
            return cls(
                normalized,
                backend,
                "https://models.github.ai/inference/chat/completions",
                token,
                model,
            )
        raise LearningWorkerError(f"unsupported learning backend: {backend}")


def _extract_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.S | re.I)
    if fenced:
        candidate = fenced.group(1)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise LearningWorkerError("worker did not return a JSON object") from exc
        try:
            payload = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as nested:
            raise LearningWorkerError("worker returned malformed JSON") from nested
    if not isinstance(payload, dict):
        raise LearningWorkerError("worker output must be a JSON object")
    return payload


def _require_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LearningWorkerError(f"worker output requires non-empty {key}")
    return value.strip()


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise LearningWorkerError(f"worker output requires list {key}")
    return value


def validate_worker_output(role: str, case_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = role.lower().strip()
    if payload.get("role") != normalized:
        raise LearningWorkerError(f"worker role mismatch: {payload.get('role')} != {normalized}")
    if payload.get("case_id") != case_id:
        raise LearningWorkerError("worker case binding mismatch")
    confidence = float(payload.get("confidence", -1.0))
    if not 0.0 <= confidence <= 1.0:
        raise LearningWorkerError("worker confidence must be between 0 and 1")

    if normalized == "teacher":
        _require_text(payload, "generalized_mechanism")
        _require_text(payload, "proposed_detector")
        _require_list(payload, "positive_tests")
        _require_list(payload, "negative_controls")
        _require_list(payload, "transfer_languages")
    elif normalized == "prosecutor":
        _require_text(payload, "claim")
        _require_text(payload, "root_cause")
        _require_list(payload, "evidence")
        _require_list(payload, "competing_explanations_rejected")
    elif normalized == "defender":
        verdict = _require_text(payload, "verdict")
        if verdict not in {"supports", "rejects", "needs_more_evidence"}:
            raise LearningWorkerError("invalid Defender verdict")
        _require_list(payload, "counterexamples")
        _require_list(payload, "false_positive_risks")
        _require_list(payload, "missing_evidence")
    else:
        raise LearningWorkerError(f"unknown role: {role}")
    return dict(payload)


def worker_request(role: str, case_packet: Mapping[str, Any], config: WorkerConfig | None = None) -> dict[str, Any]:
    case_id = _require_text(case_packet, "case_id")
    selected = config or WorkerConfig.from_env(role)
    if selected.role != role:
        raise LearningWorkerError("worker configuration role mismatch")

    expected = {
        "teacher": {
            "role": "teacher", "case_id": case_id, "generalized_mechanism": "...",
            "proposed_detector": "...", "positive_tests": [], "negative_controls": [],
            "transfer_languages": [], "confidence": 0.0,
        },
        "prosecutor": {
            "role": "prosecutor", "case_id": case_id, "claim": "...", "root_cause": "...",
            "evidence": [], "competing_explanations_rejected": [], "confidence": 0.0,
        },
        "defender": {
            "role": "defender", "case_id": case_id, "verdict": "supports|rejects|needs_more_evidence",
            "counterexamples": [], "false_positive_risks": [], "missing_evidence": [], "confidence": 0.0,
        },
    }[role]
    user_content = json.dumps(
        {
            "instruction": "Return exactly one JSON object matching output_contract.",
            "output_contract": expected,
            "case": dict(case_packet),
        },
        sort_keys=True,
    )
    body = json.dumps(
        {
            "model": selected.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": ROLE_PROMPTS[role]},
                {"role": "user", "content": user_content},
            ],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        selected.endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {selected.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"sergeant-learning-{role}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=selected.timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LearningWorkerError(f"{role} transport failed: {exc}") from exc
    try:
        content = response_payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LearningWorkerError(f"{role} response lacks chat completion content") from exc
    result = validate_worker_output(role, case_id, _extract_json(str(content)))
    result["transport"] = {"backend": selected.backend, "model": selected.model, "endpoint_class": "isolated-hermes-profile" if selected.backend == "hermes" else "github-models"}
    return result
