"""Versioned command, task, and evidence contracts for Cpl operations.

These contracts exist before Ptah/Hunter Workspace.  They let Sergeant plan,
authorize, audit, and replay work without pretending an execution facility is
already connected.  Models and workspace tools are replaceable capabilities;
permanent officers and Sergeant authority remain stable.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

CONTRACT_VERSION = "sergeant.operational-contracts.v1"
PRIVATE_FORCE_MULTIPLIER = 10
MINIMUM_PRIVATE_FORCE = 20
FORBIDDEN_EVIDENCE_KEYS = {
    "verdict",
    "final_verdict",
    "approve",
    "approved",
    "block",
    "sergeant_verdict",
}
_TASK_STATUS_VALUES = {"authorized", "in_progress", "blocked", "failed", "completed"}
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_RE = re.compile(
    r"(?i)(?:api[_-]?key|authorization|bearer|password|passwd|secret|token)\s*[:=]\s*[^\s,;]+"
)
_LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:\\|/(?:home|root|users|private|workspace)/)", re.IGNORECASE)


def stable_id(prefix: str, *parts: object) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return f"{prefix}-" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def private_force_size(human_equivalent_workers: int) -> int:
    """Scale ordinary worker need by ten, with twenty as the minimum formation."""

    human = max(1, int(human_equivalent_workers))
    return max(MINIMUM_PRIVATE_FORCE, human * PRIVATE_FORCE_MULTIPLIER)


def mission_packet(
    *,
    objective: str,
    scope: Iterable[str],
    constraints: Iterable[str],
    required_proof: Iterable[str],
    permissions: Iterable[str] = ("read_repository", "run_approved_tools"),
    privacy: str = "repository_scoped",
) -> dict[str, Any]:
    normalized_scope = sorted({str(item) for item in scope if str(item)})
    mission_id = stable_id("mission", objective, normalized_scope)
    return {
        "schema_version": CONTRACT_VERSION,
        "mission_id": mission_id,
        "issued_by": "Sergeant",
        "commanded_by": "Cpl",
        "objective": str(objective).strip(),
        "scope": normalized_scope,
        "constraints": [str(item) for item in constraints if str(item)],
        "permissions": [str(item) for item in permissions if str(item)],
        "required_proof": [str(item) for item in required_proof if str(item)],
        "privacy": privacy,
        "authority_boundary": {
            "sergeant": "defines mission, gates, required proof, and final verdict",
            "cpl": "commands the investigation campaign and council rounds",
            "officers": "own specialist doctrine and authorize bounded work",
            "privates": "execute assigned evidence obligations without changing authority",
            "models": "replaceable reasoning engines with no rank",
            "workspace": "replaceable execution facilities with no decision authority",
            "hermes": "transports and preserves; never commands or decides",
        },
    }


def task_packet(
    *,
    mission_id: str,
    officer: str,
    objective: str,
    scope: Iterable[str],
    questions: Iterable[str],
    required_evidence: Iterable[str],
    allowed_capabilities: Iterable[str],
    human_equivalent_workers: int = 2,
    dependencies: Iterable[str] = (),
    stop_conditions: Iterable[str] = (
        "required evidence found",
        "scope exhausted",
        "missing dependency requires escalation",
    ),
    escalation_conditions: Iterable[str] = (
        "scope extension required",
        "contradictory grounded evidence",
        "required capability unavailable",
    ),
    execution_mode: str = "private_cell",
) -> dict[str, Any]:
    normalized_scope = sorted({str(item) for item in scope if str(item)})
    task_id = stable_id("task", mission_id, officer, objective, normalized_scope)
    private_count = private_force_size(human_equivalent_workers) if execution_mode == "private_cell" else 0
    return {
        "schema_version": CONTRACT_VERSION,
        "mission_id": mission_id,
        "task_id": task_id,
        "assigned_by": officer,
        "responsible_officer": officer,
        "objective": str(objective).strip(),
        "scope": normalized_scope,
        "questions": [str(item) for item in questions if str(item)],
        "required_evidence": [str(item) for item in required_evidence if str(item)],
        "allowed_capabilities": sorted({str(item) for item in allowed_capabilities if str(item)}),
        "dependencies": [str(item) for item in dependencies if str(item)],
        "budget": {
            "human_equivalent_workers": max(1, int(human_equivalent_workers)),
            "private_force_multiplier": PRIVATE_FORCE_MULTIPLIER,
            "private_count": private_count,
            "max_rounds": 3,
            "external_paid_calls": 0,
        },
        "stop_conditions": [str(item) for item in stop_conditions if str(item)],
        "escalation_conditions": [str(item) for item in escalation_conditions if str(item)],
        "execution_mode": execution_mode,
        "status": "authorized",
        "may_issue_verdict": False,
        "may_expand_scope": False,
        "reports_to": officer,
    }


def task_status_packet(
    *,
    mission_id: str,
    task_id: str,
    worker_id: str,
    status: str,
    source_revision: str | None = None,
    evidence_digest: str | None = None,
    provenance: dict[str, Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Return bounded execution status without transferring command or verdict authority.

    A completed task may unblock dependent work only when its result is bound to an
    exact source revision and a SHA-256 evidence digest.  Other states cannot carry
    a completion binding.
    """

    normalized_status = str(status).strip()
    if normalized_status not in _TASK_STATUS_VALUES:
        raise ValueError(f"unsupported task execution status: {normalized_status}")
    packet: dict[str, Any] = {
        "schema_version": CONTRACT_VERSION,
        "mission_id": str(mission_id),
        "task_id": str(task_id),
        "worker_id": str(worker_id),
        "status": normalized_status,
        "reason": str(reason or "").strip(),
        "may_issue_verdict": False,
        "may_schedule": False,
    }
    if normalized_status == "completed":
        revision = str(source_revision or "").strip()
        digest = str(evidence_digest or "").strip().lower()
        proof_provenance = dict(provenance or {})
        if not revision:
            raise ValueError("completed task status requires an exact source revision")
        if not _SHA256_RE.fullmatch(digest):
            raise ValueError("completed task status requires a sha256 evidence digest")
        if not proof_provenance:
            raise ValueError("completed task status requires provenance")
        packet["result_binding"] = {
            "source_revision": revision,
            "evidence_digest": digest,
            "provenance": proof_provenance,
        }
    elif source_revision or evidence_digest:
        raise ValueError("non-completed task status cannot claim a frozen result binding")
    return packet


def validate_task_status_packet(packet: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    forbidden = FORBIDDEN_EVIDENCE_KEYS.intersection(packet)
    if forbidden:
        raise ValueError(f"task status cannot issue command verdict fields: {sorted(forbidden)}")
    if packet.get("mission_id") != task.get("mission_id") or packet.get("task_id") != task.get("task_id"):
        raise ValueError("task status does not belong to the authorized task")
    if packet.get("may_issue_verdict") not in {None, False} or packet.get("may_schedule") not in {None, False}:
        raise ValueError("task status cannot acquire command or verdict authority")
    status = str(packet.get("status") or "")
    if status not in _TASK_STATUS_VALUES:
        raise ValueError(f"unsupported task execution status: {status}")
    binding = packet.get("result_binding")
    if status == "completed":
        if not isinstance(binding, dict):
            raise ValueError("completed task status requires a frozen result binding")
        if not str(binding.get("source_revision") or "").strip():
            raise ValueError("completed task binding requires an exact source revision")
        if not _SHA256_RE.fullmatch(str(binding.get("evidence_digest") or "").lower()):
            raise ValueError("completed task binding requires a sha256 evidence digest")
        if not isinstance(binding.get("provenance"), dict) or not binding.get("provenance"):
            raise ValueError("completed task binding requires provenance")
    elif binding is not None:
        raise ValueError("only completed task status may bind frozen upstream evidence")
    return packet


def workspace_request(
    *,
    mission_id: str,
    task_id: str,
    facility: str,
    action: str,
    scope: Iterable[str],
    required_artifacts: Iterable[str],
    privacy: str = "repository_scoped",
) -> dict[str, Any]:
    normalized_scope = sorted({str(item) for item in scope if str(item)})
    return {
        "schema_version": CONTRACT_VERSION,
        "request_id": stable_id("workspace", mission_id, task_id, facility, action, normalized_scope),
        "mission_id": mission_id,
        "task_id": task_id,
        "facility": facility,
        "action": action,
        "scope": normalized_scope,
        "required_artifacts": [str(item) for item in required_artifacts if str(item)],
        "privacy": privacy,
        "status": "awaiting_adapter",
        "authority": "authorized task only",
    }


def research_request(
    *,
    mission_id: str,
    task_id: str,
    question: str,
    allowed_sources: Iterable[str],
    freshness: str = "current",
    privacy: str = "public_metadata_only",
) -> dict[str, Any]:
    clean_question = str(question).strip()
    if not clean_question:
        raise ValueError("research question is required")
    if _SECRET_RE.search(clean_question) or _LOCAL_PATH_RE.search(clean_question):
        raise ValueError("research requests cannot contain credentials or private local paths")
    sources = sorted({str(item).strip() for item in allowed_sources if str(item).strip()})
    if not sources:
        raise ValueError("research requests require an explicit source policy")
    return {
        "schema_version": CONTRACT_VERSION,
        "request_id": stable_id("research", mission_id, task_id, clean_question, sources),
        "mission_id": mission_id,
        "task_id": task_id,
        "question": clean_question,
        "allowed_sources": sources,
        "freshness": freshness,
        "privacy": privacy,
        "status": "awaiting_adapter",
        "required_provenance": ["source", "retrieved_at", "supported_claim", "freshness"],
        "authority": "evidence provider only",
    }


def evidence_packet(
    *,
    mission_id: str,
    task_id: str,
    worker_id: str,
    claims: Iterable[dict[str, Any]],
    evidence_refs: Iterable[str],
    falsifiers_checked: Iterable[str] = (),
    uncertainty: Iterable[str] = (),
    questions_for_officer: Iterable[str] = (),
    provenance: dict[str, Any] | None = None,
    confidence: float = 0.0,
    status: str = "completed",
) -> dict[str, Any]:
    return {
        "schema_version": CONTRACT_VERSION,
        "mission_id": mission_id,
        "task_id": task_id,
        "worker_id": worker_id,
        "status": status,
        "claims": [dict(item) for item in claims],
        "evidence_refs": [str(item) for item in evidence_refs if str(item)],
        "falsifiers_checked": [str(item) for item in falsifiers_checked if str(item)],
        "uncertainty": [str(item) for item in uncertainty if str(item)],
        "questions_for_officer": [str(item) for item in questions_for_officer if str(item)],
        "provenance": dict(provenance or {}),
        "confidence": max(0.0, min(1.0, float(confidence))),
        "may_issue_verdict": False,
    }


def validate_evidence_packet(packet: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    forbidden = FORBIDDEN_EVIDENCE_KEYS.intersection(packet)
    if forbidden:
        raise ValueError(f"private evidence cannot issue command verdict fields: {sorted(forbidden)}")
    if packet.get("mission_id") != task.get("mission_id") or packet.get("task_id") != task.get("task_id"):
        raise ValueError("evidence packet does not belong to the authorized task")
    if packet.get("may_issue_verdict") not in {None, False}:
        raise ValueError("private evidence cannot acquire verdict authority")
    scope = {str(item) for item in task.get("scope", [])}
    for reference in packet.get("evidence_refs", []):
        text = str(reference)
        if "://" in text or not scope:
            continue
        path = text.split(":", 1)[0]
        if path not in scope:
            raise ValueError(f"evidence reference escaped authorized scope: {path}")
    return packet