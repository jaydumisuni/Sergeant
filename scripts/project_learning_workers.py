"""Project-driven learning worker transport.

This wrapper keeps Sergeant's stable Hermes worker contract unchanged while
allowing trusted post-merge project-learning runs to use Cloudflare Workers AI.
Cloudflare credentials are read only at runtime and are never included in the
returned worker evidence.
"""

from __future__ import annotations

import os
from typing import Any, Mapping

from main_review.cloudflare_models import cloudflare_base_url
from main_review.hermes_learning import (
    LearningWorkerError,
    ROLES,
    WorkerConfig,
    worker_request as _base_worker_request,
)

CLOUDFLARE_ROLE_MODELS = {
    "teacher": "@cf/zai-org/glm-4.7-flash",
    "prosecutor": "@cf/qwen/qwen3-30b-a3b-fp8",
    "defender": "@cf/openai/gpt-oss-20b",
}


def _cloudflare_config(role: str) -> WorkerConfig:
    normalized = role.lower().strip()
    if normalized not in ROLES:
        raise LearningWorkerError(f"unknown learning role: {role}")
    account_id = os.environ.get("SERGEANT_CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("SERGEANT_CLOUDFLARE_API_TOKEN", "").strip()
    base_url = cloudflare_base_url(account_id)
    if not base_url or not token:
        raise LearningWorkerError("Cloudflare project-learning account/token not configured")
    suffix = normalized.upper()
    model = os.environ.get(
        f"SERGEANT_{suffix}_MODEL",
        CLOUDFLARE_ROLE_MODELS[normalized],
    ).strip()
    if not model.startswith("@cf/"):
        raise LearningWorkerError(f"Cloudflare {normalized} model must be an @cf/ Workers AI model")
    return WorkerConfig(
        role=normalized,
        backend="cloudflare",
        endpoint=f"{base_url}/chat/completions",
        token=token,
        model=model,
    )


def worker_request(
    role: str,
    case_packet: Mapping[str, Any],
    config: WorkerConfig | None = None,
) -> dict[str, Any]:
    """Run one bounded learning worker through Cloudflare or stable Hermes."""

    backend = os.environ.get("SERGEANT_LEARNING_BACKEND", "hermes").strip().lower()
    selected = config
    if selected is None and backend == "cloudflare":
        selected = _cloudflare_config(role)
    result = _base_worker_request(role, case_packet, config=selected)
    if selected is not None and selected.backend == "cloudflare":
        result["transport"] = {
            "backend": "cloudflare",
            "model": selected.model,
            "endpoint_class": "cloudflare-workers-ai",
        }
    return result
