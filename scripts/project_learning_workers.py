"""Project-driven learning worker transport.

This wrapper keeps Sergeant's stable Hermes worker contract unchanged while
allowing an owner-authorized direct-terminal learning run to use Cloudflare
Workers AI. Cloudflare credentials are recovered at runtime from explicit
environment variables or the workstation's existing Wrangler authentication;
secrets are never written into returned learning evidence.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
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
_ACCOUNT_ID_RE = re.compile(r"^[A-Fa-f0-9]{32}$")


def _wrangler_json(*args: str) -> dict[str, Any]:
    """Run one read-only Wrangler identity command without echoing its output."""

    executable = os.environ.get("SERGEANT_WRANGLER_EXECUTABLE", "npx").strip() or "npx"
    command = [executable, "wrangler", *args]
    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        payload = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        # Do not include stdout/stderr: auth-token output can contain a secret.
        raise LearningWorkerError("Wrangler authentication lookup failed") from exc
    if not isinstance(payload, dict):
        raise LearningWorkerError("Wrangler authentication lookup returned invalid JSON")
    return payload


def _account_ids(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Extract account IDs only from account-shaped Wrangler JSON fields."""

    found: list[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if _ACCOUNT_ID_RE.fullmatch(text) and text not in found:
            found.append(text)

    def account_object(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        for key in ("id", "account_id", "accountId"):
            add(value.get(key))
        nested = value.get("account")
        if isinstance(nested, Mapping):
            account_object(nested)

    for key in ("account", "default_account", "defaultAccount"):
        account_object(payload.get(key))
    for key in ("account_id", "accountId"):
        add(payload.get(key))
    for key in ("accounts", "memberships"):
        values = payload.get(key)
        if isinstance(values, list):
            for value in values:
                account_object(value)
    return tuple(found)


def _cloudflare_credentials() -> tuple[str, str]:
    """Resolve one Account ID and bearer token without persisting either value."""

    account_id = os.environ.get("SERGEANT_CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("SERGEANT_CLOUDFLARE_API_TOKEN", "").strip()

    if account_id and not _ACCOUNT_ID_RE.fullmatch(account_id):
        raise LearningWorkerError("Cloudflare project-learning Account ID is invalid")

    if not token:
        auth = _wrangler_json("auth", "token", "--json")
        auth_type = str(auth.get("type") or "").strip().lower()
        if auth_type not in {"api_token", "oauth"}:
            raise LearningWorkerError(
                "Wrangler project-learning auth must resolve to an API token or OAuth token"
            )
        token = str(auth.get("token") or "").strip()
        if not token:
            raise LearningWorkerError("Wrangler project-learning token is empty")

    if not account_id:
        whoami = _wrangler_json("whoami", "--json")
        ids = _account_ids(whoami)
        if len(ids) != 1:
            raise LearningWorkerError(
                "Wrangler project-learning requires exactly one Account ID; set "
                "SERGEANT_CLOUDFLARE_ACCOUNT_ID when multiple accounts are available"
            )
        account_id = ids[0]

    return account_id, token


def _cloudflare_config(role: str) -> WorkerConfig:
    normalized = role.lower().strip()
    if normalized not in ROLES:
        raise LearningWorkerError(f"unknown learning role: {role}")
    account_id, token = _cloudflare_credentials()
    base_url = cloudflare_base_url(account_id)
    if not base_url:
        raise LearningWorkerError("Cloudflare project-learning Account ID is invalid")
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


def _max_attempts() -> int:
    try:
        value = int(os.environ.get("SERGEANT_LEARNING_MAX_ATTEMPTS", "3"))
    except ValueError as exc:
        raise LearningWorkerError("SERGEANT_LEARNING_MAX_ATTEMPTS must be an integer") from exc
    if not 1 <= value <= 5:
        raise LearningWorkerError("SERGEANT_LEARNING_MAX_ATTEMPTS must be between 1 and 5")
    return value


def worker_request(
    role: str,
    case_packet: Mapping[str, Any],
    config: WorkerConfig | None = None,
) -> dict[str, Any]:
    """Run one bounded learning worker with bounded retries for transient/model failures."""

    backend = os.environ.get("SERGEANT_LEARNING_BACKEND", "hermes").strip().lower()
    selected = config
    if selected is None and backend == "cloudflare":
        selected = _cloudflare_config(role)

    attempts = _max_attempts() if selected is not None and selected.backend == "cloudflare" else 1
    last_error: LearningWorkerError | None = None
    for attempt in range(1, attempts + 1):
        try:
            result = _base_worker_request(role, case_packet, config=selected)
            if selected is not None and selected.backend == "cloudflare":
                result["transport"] = {
                    "backend": "cloudflare",
                    "model": selected.model,
                    "endpoint_class": "cloudflare-workers-ai-direct-terminal",
                    "attempts": attempt,
                }
            return result
        except LearningWorkerError as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            time.sleep(min(4.0, 0.5 * (2 ** (attempt - 1))))

    assert last_error is not None
    raise last_error
