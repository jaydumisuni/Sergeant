"""Static rules over Sergeant's language-neutral semantic flow graph."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .semantic_flow_graph import FlowEvent, FunctionFlow, SemanticFlowGraph, build_semantic_flow_graph


def _event_after(events: list[FlowEvent], kind: str, line: int) -> list[FlowEvent]:
    return [event for event in events if event.kind == kind and event.line > line]


def _guard_between(events: list[FlowEvent], start: int, end: int) -> bool:
    return any(event.kind == "validity_guard" and start < event.line <= end for event in events)


def _finding(
    *,
    root_cause: str,
    path: str,
    line_start: int,
    message: str,
    evidence: str,
    supporting: Iterable[str],
    falsifiers: Iterable[str],
    verification: str,
    confidence: float,
    capability: str = "concurrency",
) -> dict[str, Any]:
    return {
        "source": "semantic-flow-officer",
        "officer": "Mechanic",
        "capability": capability,
        "category": capability,
        "severity": "major",
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": list(supporting),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _provider_lifetime_findings(graph: SemanticFlowGraph) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for flow in graph.functions:
        if flow.lifecycle != "provider":
            continue
        suspends = [event for event in flow.events if event.kind == "suspend"]
        if not suspends:
            continue
        first_suspend = suspends[0]
        publications = [
            event
            for event in _event_after(flow.events, "publication", first_suspend.line)
            if event.symbol in {"provider_ref", "provider_state"}
        ]
        if not publications:
            continue
        first_publication = publications[0]
        if _guard_between(flow.events, first_suspend.line, first_publication.line):
            continue
        findings.append(
            _finding(
                root_cause="provider-lifetime-not-revalidated-after-suspension",
                path=flow.path,
                line_start=first_suspend.line,
                message="A lifecycle-bound provider resumes after suspension and publishes through ref/state without revalidating that the provider still exists.",
                evidence=(
                    f"{flow.name} in a provider lifecycle suspends at line {first_suspend.line} and performs "
                    f"{first_publication.symbol} publication at line {first_publication.line}. No validity guard lies between them."
                ),
                supporting=(f"{flow.path}:{first_suspend.line}", f"{flow.path}:{first_publication.line}"),
                falsifiers=(
                    "Checked that the function belongs to a Riverpod/notifier lifecycle.",
                    "Checked that a ref/state publication occurs after a suspension point.",
                    "Checked for a mounted/current/active/epoch guard between resumption and publication.",
                ),
                verification="Capture required dependencies before suspension or revalidate provider lifetime immediately after every async gap before touching ref/state.",
                confidence=0.97,
                capability="state_lifecycle",
            )
        )
    return findings


def _reentrant_publication_findings(graph: SemanticFlowGraph) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    publication_symbols = {"react_state", "dispatch", "map_source", "collection", "value_write", "provider_state"}
    name_signal = re.compile(r"(?:load|refresh|fetch|search|sync|poll|update)", re.I)
    for flow in graph.functions:
        if not (flow.dynamic_effect_trigger or (flow.trigger_count >= 1 and name_signal.search(flow.name))):
            continue
        suspends = [event for event in flow.events if event.kind == "suspend"]
        if not suspends:
            continue
        first_suspend = suspends[0]
        publications = [
            event
            for event in _event_after(flow.events, "publication", first_suspend.line)
            if event.symbol in publication_symbols
        ]
        if not publications:
            continue
        first_publication = publications[0]
        if _guard_between(flow.events, first_suspend.line, first_publication.line):
            continue
        if any(event.kind in {"epoch_advance", "epoch_token"} and event.line <= first_suspend.line for event in flow.events):
            continue
        findings.append(
            _finding(
                root_cause="reentrant-async-publication-without-epoch",
                path=flow.path,
                line_start=first_suspend.line,
                message="A repeatedly triggered async operation publishes after suspension without proving the result belongs to the latest invocation.",
                evidence=(
                    f"{flow.name} has {flow.trigger_count} external call trigger(s)"
                    f"{' including a dependency-driven effect' if flow.dynamic_effect_trigger else ''}, suspends at line {first_suspend.line}, "
                    f"and publishes through {first_publication.symbol} at line {first_publication.line}. No request/epoch guard protects the publication."
                ),
                supporting=(f"{flow.path}:{first_suspend.line}", f"{flow.path}:{first_publication.line}"),
                falsifiers=(
                    "Checked that the async operation can be triggered again while earlier work may remain active.",
                    "Checked for a request/generation/controller token established before suspension.",
                    "Checked for a current/active/epoch guard before the post-suspension publication.",
                ),
                verification="Assign each invocation an epoch/request identity or cancellation owner and reject superseded results before every publication sink.",
                confidence=0.95,
            )
        )
    return findings


def _resource_family(resource: str) -> str:
    normalized = resource.lower().split("?", 1)[0].rstrip("/")
    parts = [part for part in normalized.split("/") if part]
    if "auth" in parts:
        return "/".join(parts[: parts.index("auth") + 1])
    return "/".join(parts[:-1]) if len(parts) > 1 else normalized


def _cache_invalidation_findings(graph: SemanticFlowGraph) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    gets_by_function = {
        operation.function.lower(): operation
        for operation in graph.endpoints
        if operation.method == "GET"
    }
    mutations = [operation for operation in graph.endpoints if operation.method != "GET"]
    for cache in graph.mount_only_caches:
        fetch_name = str(cache.get("fetch_function") or "")
        normalized = re.sub(r"^(?:fetch|get|load)", "", fetch_name, flags=re.I).lower() or fetch_name.lower()
        read = gets_by_function.get(normalized) or gets_by_function.get(fetch_name.lower())
        if read is None:
            continue
        family = _resource_family(read.resource)
        related_mutations = [operation for operation in mutations if _resource_family(operation.resource) == family]
        if not related_mutations:
            continue
        if cache.get("listens_for_invalidation") or any(operation.invalidates for operation in related_mutations):
            continue
        line = int(cache.get("line") or 1)
        findings.append(
            _finding(
                root_cause="mount-only-cache-without-mutation-invalidation",
                path=str(cache.get("path") or read.path),
                line_start=line,
                message="A mount-only client cache has no invalidation edge from mutations of the resource it represents.",
                evidence=(
                    f"The cache reads {read.resource} through {fetch_name} once at mount, while "
                    f"{', '.join(operation.function for operation in related_mutations)} mutate the same resource family. "
                    "Neither the cache nor the mutations publish an invalidation/refetch signal."
                ),
                supporting=(
                    f"{cache.get('path')}:{line}",
                    *[f"{operation.path}:{operation.line}" for operation in related_mutations],
                ),
                falsifiers=(
                    "Checked for event subscriptions, query invalidation, shared-store updates, or refetch triggers in the cache.",
                    "Checked mutation functions for an invalidation event or cache update on success.",
                    "Checked that the read and mutation endpoints belong to the same resource family.",
                ),
                verification="Publish a resource-change signal on successful mutations and refetch/invalidate the mounted cache; guard overlapping refreshes with a monotonic request identity.",
                confidence=0.96,
                capability="api_contract",
            )
        )
    return findings


def run_static_semantic_flow_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    graph = build_semantic_flow_graph(root, changed_files)
    findings = [
        *_provider_lifetime_findings(graph),
        *_reentrant_publication_findings(graph),
        *_cache_invalidation_findings(graph),
    ]
    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        key = (
            str(finding.get("root_cause")),
            str(finding.get("path")),
            int(finding.get("line_start") or 0),
        )
        unique[key] = finding
    return {
        "schema_version": "sergeant.static-semantic-flow-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "semantic_graph": graph.to_dict(),
        "executed_project_code": False,
    }
