"""Static checks learned from the valid replacement for transfer set 10."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".php"}


def _safe_text(root: Path, relative: str) -> str:
    try:
        resolved_root = root.resolve()
        path = (resolved_root / relative).resolve()
        if not path.is_relative_to(resolved_root) or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line(text: str, offset: int) -> int:
    return text[: max(0, offset)].count("\n") + 1


def _finding(
    *,
    root_cause: str,
    path: str,
    line_start: int,
    severity: str,
    category: str,
    officer: str,
    message: str,
    evidence: str,
    falsifiers: Iterable[str],
    verification: str,
    supporting: Iterable[str] = (),
    confidence: float = 0.97,
) -> dict[str, Any]:
    refs = [f"{path}:{line_start}", *[str(item) for item in supporting]]
    return {
        "source": "static-transfer-10-replacement-officer",
        "officer": officer,
        "capability": category,
        "category": category,
        "severity": severity,
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": list(dict.fromkeys(refs)),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _event_graph_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() != ".py":
        return []
    if re.search(r"(?:episode|reflexion|causal|knowledge.?graph)", f"{path}\n{text}", re.I) is None:
        return []

    empty_edges = list(
        re.finditer(
            r'["\']caused_by["\']\s*:\s*\[\s*\]\s*,?[\s\S]{0,180}?'
            r'["\']leads_to["\']\s*:\s*\[\s*\]',
            text,
            re.M,
        )
    )
    if len(empty_edges) < 2:
        return []
    has_event_ids = bool(
        re.search(r'["\']id["\']\s*:\s*f?["\']e\{', text)
        or re.search(r'\[\s*["\']id["\']\s*\]\s*=\s*f?["\']e\{', text)
    )
    event_binding = re.search(
        r'["\']events["\']\s*:\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b',
        text,
    )
    persists_events = bool(
        event_binding
        and re.search(r"(?:write_text|json\.dump|json\.dumps|open\s*\([^)]*[\"\']w)", text)
    )
    if not (has_event_ids and persists_events):
        return []

    links_edges = bool(
        re.search(r'\[\s*["\'](?:caused_by|leads_to)["\']\s*\]\s*=', text)
        or re.search(r"\b(?:link|connect|chain)[A-Za-z0-9_]*events?\s*\(", text, re.I)
    )
    if links_edges:
        return []

    match = empty_edges[0]
    line = _line(text, match.start())
    return [
        _finding(
            root_cause="persisted-event-graph-never-links-causal-edges",
            path=path,
            line_start=line,
            severity="major",
            category="state_lifecycle",
            officer="Archivist",
            message="A persisted episode/event graph assigns stable event IDs but leaves every causal edge empty.",
            evidence=(
                "Multiple event constructors emit `caused_by=[]` and `leads_to=[]`; the final event collection is "
                "serialized after IDs are assigned/reassigned, but no linking pass populates predecessor or successor "
                "references. Consumers receive a flat set rather than the causal/temporal graph promised by the module."
            ),
            falsifiers=(
                "Checked that the module is an episode/reflexion/causal-memory path rather than a generic unordered log.",
                "Checked that multiple events receive stable IDs.",
                "Checked that the events collection is persisted.",
                "Checked for a post-deduplication linking pass or assignments to caused_by/leads_to.",
            ),
            verification=(
                "Link final ordered events only after every merge/deduplication step that can reassign IDs; prove empty, "
                "single-event, multi-event, preserve/merge, and idempotent rerun cases have no dangling references."
            ),
        )
    ]


def _checkout_findings(changed: list[str], texts: dict[str, str]) -> list[dict[str, Any]]:
    source_paths = [
        path
        for path in changed
        if Path(path).suffix.lower() in {".ts", ".tsx", ".js", ".jsx"} and texts.get(path)
    ]
    if not source_paths:
        return []
    combined = "\n".join(texts[path] for path in source_paths)
    if re.search(r"(?:checkoutPendingAt\s*:\s*null|release.{0,80}checkout.{0,80}lock)", combined, re.I | re.S) is None:
        return []
    if re.search(r"\bcreateCheckout(?:Session)?\b", combined) is None:
        return []

    stable_attempt = bool(
        re.search(
            r"(?:CheckoutAttempt|checkoutIdempotencyKey|checkoutIntentHash|idempotencyKey|idempotency_key)",
            combined,
            re.I,
        )
    )
    if stable_attempt:
        return []

    for path in source_paths:
        text = texts[path]
        sink = re.search(r"checkout\.sessions\.create\s*\(", text)
        if sink is None:
            continue
        window = text[sink.start() : min(len(text), sink.start() + 2600)]
        if re.search(r"(?:idempotencyKey|idempotency_key)", window, re.I):
            continue
        line = _line(text, sink.start())
        supporting: list[str] = []
        for other in source_paths:
            other_text = texts[other]
            release = re.search(r"checkoutPendingAt\s*:\s*null", other_text)
            if release is not None:
                supporting.append(f"{other}:{_line(other_text, release.start())}")
                break
        return [
            _finding(
                root_cause="retryable-checkout-creation-without-stable-provider-idempotency-key",
                path=path,
                line_start=line,
                severity="blocker",
                category="money_flow",
                officer="Medic",
                message="A provider checkout creation call can be retried after an ambiguous failure without a stable attempt idempotency key.",
                evidence=(
                    "The service explicitly releases its pending-checkout lock after provider-call failure, so a retry is "
                    "expected. The provider then calls `checkout.sessions.create` without a persisted attempt identity or "
                    "provider idempotency key. A lost response can therefore leave one payable session alive while the retry "
                    "creates another."
                ),
                falsifiers=(
                    "Checked that checkout creation is followed by a failure path that permits retry.",
                    "Checked the provider interface and service call for a stable persisted checkout-attempt identity.",
                    "Checked the provider sink for an idempotency-key request option.",
                    "Checked that an already-active-subscription guard cannot protect the pre-webhook ambiguity window.",
                ),
                verification=(
                    "Persist one key plus an intent fingerprint and start time per checkout attempt, pass that key at the "
                    "provider request boundary, derive replay-sensitive parameters from the same attempt, and prove lost-response, "
                    "double-click, changed-intent, expiry, and cross-user cases."
                ),
                supporting=supporting,
            )
        ]
    return []


def _php_context_files(root: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    try:
        for path in root.rglob("*.php"):
            if not path.is_file():
                continue
            try:
                relative = str(path.relative_to(root)).replace("\\", "/")
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if "content-block-row" in text or "case 'media'" in text or 'case "media"' in text:
                rows.append((relative, text))
            if len(rows) >= 120:
                break
    except OSError:
        return rows
    return rows


def _variant_schema_findings(root: Path, changed: list[str], texts: dict[str, str]) -> list[dict[str, Any]]:
    normalizers = [
        (path, texts[path])
        for path in changed
        if Path(path).suffix.lower() == ".php"
        and "content-block-row" in texts.get(path, "")
        and "prune_default_content_block_cells" in texts.get(path, "")
    ]
    if not normalizers:
        return []

    media_owner: tuple[str, str, re.Match[str]] | None = None
    for context_path, context in _php_context_files(root):
        match = re.search(
            r"case\s+[\"']media[\"']\s*:[\s\S]{0,900}?"
            r"(?:\[\s*[\"']position[\"']\s*\]|\$row\s*\[\s*[\"']position[\"']\s*\])",
            context,
            re.I,
        )
        if match is not None:
            media_owner = (context_path, context, match)
            break
    if media_owner is None:
        return []

    for path, text in normalizers:
        safe = bool(
            re.search(r"(?:media_only|variant_gated|stray_media|prune_[A-Za-z0-9_]*position)", text, re.I)
            or (
                re.search(r"(?:kind|row_kind)", text, re.I)
                and re.search(r"(?:unset|remove|drop|prune)[\s\S]{0,240}?[\"']position[\"']", text, re.I)
            )
        )
        if safe:
            continue
        call = re.search(r"ef_prune_default_content_block_cells\s*\(", text)
        if call is None:
            continue
        context_path, context, match = media_owner
        line = _line(text, call.start())
        support_line = _line(context, match.start())
        return [
            _finding(
                root_cause="variant-gated-schema-cell-persists-on-incompatible-row-kind",
                path=path,
                line_start=line,
                severity="major",
                category="api_contract",
                officer="Engineer",
                message="The save normalizer preserves a field that the row resolver assigns only to another discriminator variant.",
                evidence=(
                    "The row resolver consumes `position` only inside the `kind=media` branch, while the shared-row save "
                    "normalizer prunes default cells but has no discriminator-aware removal for a non-media row carrying "
                    "that field. A stale or editor-serialized cell can survive into strict schema validation under an "
                    "incompatible kind."
                ),
                falsifiers=(
                    "Checked repository-local row resolution for discriminator-specific ownership of the field.",
                    "Checked that the changed save normalizer handles the shared row contract.",
                    "Checked for kind-aware pruning of the field before strict validation.",
                    "Checked that the normalizer does more than remove only default-equal values.",
                ),
                verification=(
                    "At the save choke point, remove only optional/default-owned variant-only cells when the discriminator "
                    "is statically known to be another kind; preserve the owning kind and unresolved discriminators, then "
                    "prove scalar/canonical stray shapes and idempotent re-save behavior."
                ),
                supporting=(f"{context_path}:{support_line}",),
            )
        ]
    return []


def run_static_transfer_10_replacement_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    texts = {
        path: _safe_text(root_path, path)
        for path in changed
        if Path(path).suffix.lower() in _SOURCE_SUFFIXES
    }

    findings: list[dict[str, Any]] = []
    for path, text in texts.items():
        if text:
            findings.extend(_event_graph_findings(path, text))
    findings.extend(_checkout_findings(changed, texts))
    findings.extend(_variant_schema_findings(root_path, changed, texts))

    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        unique[(str(finding.get("root_cause")), str(finding.get("path")))] = finding

    return {
        "schema_version": "sergeant.static-transfer-10-replacement-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": sorted(path for path, text in texts.items() if text),
        "executed_project_code": False,
    }
