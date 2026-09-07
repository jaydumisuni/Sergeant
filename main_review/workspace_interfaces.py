"""Replaceable Ptah/Hunter Workspace and live-research adapter boundaries."""

from __future__ import annotations

import re
from typing import Any, Protocol

from .operational_contracts import validate_evidence_packet


class WorkspaceAdapter(Protocol):
    name: str

    def capabilities(self) -> set[str]: ...

    def execute(self, request: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]: ...


class ResearchAdapter(Protocol):
    name: str

    def capabilities(self) -> set[str]: ...

    def lookup(self, request: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]: ...


class UnavailableWorkspaceAdapter:
    name = "unavailable-workspace"

    def capabilities(self) -> set[str]:
        return set()

    def execute(self, request: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
        return {**request, "status": "awaiting_adapter", "reason": "No workspace facility is connected."}


class UnavailableResearchAdapter:
    name = "unavailable-research"

    def capabilities(self) -> set[str]:
        return set()

    def lookup(self, request: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
        return {**request, "status": "awaiting_adapter", "reason": "No governed live-research facility is connected."}


_FACILITY_CAPABILITY = {
    "repository": "repository",
    "test": "test_runner",
    "runtime": "runtime",
    "browser": "browser",
    "device": "device",
    "artifact": "artifact_store",
}
_FORBIDDEN_RESULT_KEYS = {
    "mission",
    "tasks",
    "authorized_tasks",
    "pending_authorizations",
    "verdict",
    "final_verdict",
    "sergeant_verdict",
}
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _bounded_failure(request: dict[str, Any], task: dict[str, Any], adapter_name: str, kind: str, error: Exception) -> dict[str, Any]:
    return {
        "request_id": request.get("request_id"),
        "mission_id": task.get("mission_id"),
        "task_id": task.get("task_id"),
        "adapter": adapter_name,
        "status": "failed",
        "error_kind": kind,
        "error_type": type(error).__name__,
        "reason": "The adapter failed inside its bounded request; no authority or evidence was accepted.",
    }


def _safe_capabilities(adapter: object) -> tuple[set[str], Exception | None]:
    capabilities = getattr(adapter, "capabilities", None)
    if not callable(capabilities):
        return set(), TypeError("adapter does not expose capabilities()")
    try:
        return {str(item) for item in capabilities() if str(item)}, None
    except Exception as error:  # adapter boundary: failure becomes bounded state
        return set(), error


def _validate_result(result: object, request: dict[str, Any], task: dict[str, Any], adapter_name: str) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError(f"{adapter_name} returned a non-object result")
    forbidden = _FORBIDDEN_RESULT_KEYS.intersection(result)
    if forbidden:
        raise ValueError(f"{adapter_name} attempted to return command-authority fields: {sorted(forbidden)}")
    if result.get("request_id") not in {None, request.get("request_id")}:
        raise ValueError(f"{adapter_name} returned evidence for another request")
    if result.get("task_id") not in {None, task.get("task_id")}:
        raise ValueError(f"{adapter_name} returned evidence for another task")
    return {
        **result,
        "request_id": request.get("request_id"),
        "mission_id": task.get("mission_id"),
        "task_id": task.get("task_id"),
        "adapter": adapter_name,
    }


def _validate_adapter_evidence(
    result: dict[str, Any],
    request: dict[str, Any],
    task: dict[str, Any],
    *,
    adapter_name: str,
    research: bool,
) -> dict[str, Any] | None:
    packet = result.get("evidence_packet")
    if not isinstance(packet, dict):
        return None
    provenance = packet.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError("adapter evidence requires provenance")
    required = {"adapter", "observed_at"}
    if research:
        required.update({"source", "retrieved_at", "supported_claim", "freshness"})
    missing = sorted(key for key in required if not provenance.get(key))
    if missing:
        raise ValueError(f"adapter evidence is missing provenance fields: {missing}")
    if provenance.get("adapter") != adapter_name:
        raise ValueError("adapter evidence provenance does not match the executing adapter")
    if research:
        allowed_sources = {
            str(item).strip()
            for item in request.get("allowed_sources", [])
            if str(item).strip()
        }
        source = str(provenance.get("source") or "").strip()
        if source not in allowed_sources:
            raise ValueError("research evidence source is not authorized by the originating request")
    return validate_evidence_packet(packet, task)


def _execution_request(
    request: dict[str, Any],
    task_id: str,
    dependency_bindings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Bind an adapter invocation to Cpl's exact frozen upstream evidence."""

    return {
        **request,
        "dependency_bindings": [dict(item) for item in dependency_bindings.get(task_id, [])],
    }


def _dependency_bindings_are_complete(task: dict[str, Any], bindings: list[dict[str, Any]]) -> bool:
    dependencies = [str(item) for item in task.get("dependencies", []) if str(item)]
    if not dependencies:
        return True
    if len(bindings) != len(dependencies):
        return False
    by_id: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        task_id = str(binding.get("task_id") or "")
        if not task_id or task_id in by_id:
            return False
        by_id[task_id] = binding
    if set(by_id) != set(dependencies):
        return False
    for dependency in dependencies:
        binding = by_id[dependency]
        if not str(binding.get("source_revision") or "").strip():
            return False
        if not _SHA256_RE.fullmatch(str(binding.get("evidence_digest") or "").lower()):
            return False
        if not isinstance(binding.get("provenance"), dict) or not binding.get("provenance"):
            return False
    return True


def dispatch_authorized_requests(
    campaign: dict[str, Any],
    *,
    workspace: WorkspaceAdapter | None = None,
    research: ResearchAdapter | None = None,
) -> dict[str, Any]:
    """Dispatch only the currently unblocked Tenfold frontier, isolating failures.

    Legacy campaigns without a ``tenfold_execution`` packet retain their prior
    all-authorized behavior.  Current campaigns bind execution to Cpl's frontier;
    adapters cannot schedule blocked/dependent tasks themselves.  Dependent
    invocations receive the exact frozen upstream bindings from Cpl state so the
    execution facility cannot substitute or infer dependency truth.
    """

    workspace = workspace or UnavailableWorkspaceAdapter()
    research = research or UnavailableResearchAdapter()
    workspace_capabilities, workspace_capability_error = _safe_capabilities(workspace)
    research_capabilities, research_capability_error = _safe_capabilities(research)
    tasks = {item["task_id"]: item for item in campaign.get("tasks", [])}
    tenfold = campaign.get("tenfold_execution")
    frontier_task_ids: set[str] | None = None
    dependency_bindings: dict[str, list[dict[str, Any]]] = {}
    if isinstance(tenfold, dict):
        frontier_task_ids = {str(item) for item in tenfold.get("frontier_task_ids", []) if str(item)}
        raw_bindings = tenfold.get("dependency_bindings", {})
        if isinstance(raw_bindings, dict):
            dependency_bindings = {
                str(task_id): [dict(item) for item in bindings if isinstance(item, dict)]
                for task_id, bindings in raw_bindings.items()
                if isinstance(bindings, list)
            }
    workspace_results: list[dict[str, Any]] = []
    research_results: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []

    for request in campaign.get("workspace_requests", []):
        task = tasks.get(request.get("task_id"))
        if task is None or task.get("status") != "authorized":
            workspace_results.append({**request, "status": "rejected", "reason": "Task is not authorized."})
            continue
        if frontier_task_ids is not None and task["task_id"] not in frontier_task_ids:
            workspace_results.append({
                **request,
                "status": "deferred",
                "reason": "Task is authorized but not on the currently unblocked Tenfold frontier.",
            })
            continue
        execution_request = _execution_request(request, task["task_id"], dependency_bindings)
        if not _dependency_bindings_are_complete(task, execution_request["dependency_bindings"]):
            workspace_results.append({
                **execution_request,
                "status": "rejected",
                "reason": "Task cannot dispatch without complete frozen dependency bindings.",
            })
            continue
        if not set(execution_request.get("scope", [])).issubset(set(task.get("scope", []))):
            workspace_results.append({**execution_request, "status": "rejected", "reason": "Request escaped task scope."})
            continue
        if workspace_capability_error is not None:
            workspace_results.append(_bounded_failure(execution_request, task, workspace.name, "adapter_capability_error", workspace_capability_error))
            continue
        required = _FACILITY_CAPABILITY.get(
            str(execution_request.get("facility") or ""),
            str(execution_request.get("facility") or ""),
        )
        if required and required not in workspace_capabilities:
            workspace_results.append({
                **execution_request,
                "status": "awaiting_capability",
                "reason": f"Workspace adapter does not provide required capability: {required}",
            })
            continue
        try:
            result = _validate_result(
                workspace.execute(execution_request, task),
                execution_request,
                task,
                workspace.name,
            )
            packet = _validate_adapter_evidence(
                result,
                execution_request,
                task,
                adapter_name=workspace.name,
                research=False,
            )
        except Exception as error:  # one failed request must not cancel independent work
            workspace_results.append(
                _bounded_failure(execution_request, task, workspace.name, "adapter_execution_or_result_error", error)
            )
            continue
        workspace_results.append(result)
        if packet is not None:
            evidence.append(packet)

    for request in campaign.get("research_requests", []):
        task = tasks.get(request.get("task_id"))
        if task is None or task.get("status") != "authorized":
            research_results.append({**request, "status": "rejected", "reason": "Task is not authorized."})
            continue
        if frontier_task_ids is not None and task["task_id"] not in frontier_task_ids:
            research_results.append({
                **request,
                "status": "deferred",
                "reason": "Task is authorized but not on the currently unblocked Tenfold frontier.",
            })
            continue
        execution_request = _execution_request(request, task["task_id"], dependency_bindings)
        if not _dependency_bindings_are_complete(task, execution_request["dependency_bindings"]):
            research_results.append({
                **execution_request,
                "status": "rejected",
                "reason": "Task cannot dispatch without complete frozen dependency bindings.",
            })
            continue
        if research_capability_error is not None:
            research_results.append(_bounded_failure(execution_request, task, research.name, "adapter_capability_error", research_capability_error))
            continue
        if "research" not in research_capabilities:
            research_results.append({
                **execution_request,
                "status": "awaiting_capability",
                "reason": "Research adapter does not provide governed research capability.",
            })
            continue
        try:
            result = _validate_result(
                research.lookup(execution_request, task),
                execution_request,
                task,
                research.name,
            )
            packet = _validate_adapter_evidence(
                result,
                execution_request,
                task,
                adapter_name=research.name,
                research=True,
            )
        except Exception as error:  # research failure remains bounded to this request
            research_results.append(
                _bounded_failure(execution_request, task, research.name, "adapter_execution_or_result_error", error)
            )
            continue
        research_results.append(result)
        if packet is not None:
            evidence.append(packet)

    return {
        "workspace_adapter": workspace.name,
        "workspace_capabilities": sorted(workspace_capabilities),
        "research_adapter": research.name,
        "research_capabilities": sorted(research_capabilities),
        "frontier_enforced": frontier_task_ids is not None,
        "frontier_task_ids": sorted(frontier_task_ids or []),
        "workspace_results": workspace_results,
        "research_results": research_results,
        "evidence_packets": evidence,
        "authority_preserved": True,
    }
