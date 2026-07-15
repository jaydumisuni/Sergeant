from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement target, found {count}")
    write(path, text.replace(old, new, 1))


def replace_between(path: str, start: str, end: str, replacement: str) -> None:
    text = read(path)
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    write(path, text[:start_index] + replacement + text[end_index:])


def patch_cpl_runtime() -> None:
    replace_between(
        "main_review/cpl_runtime.py",
        "def _all_gaps(",
        "def run_cpl_review(",
        '''_ASSURANCE_GAP_TYPES = {"failed_member", "missing_report", "recurrence", "independent_confirmation"}\n_CONFIDENCE_GAP_TYPES = {"disagreement", "unanswered_question"}\n\n\ndef _gap_impact(gap: dict[str, Any]) -> str:\n    gap_type = str(gap.get("type") or "")\n    if gap_type in _ASSURANCE_GAP_TYPES:\n        return "assurance"\n    if gap_type in _CONFIDENCE_GAP_TYPES:\n        return "confidence"\n    return "informational"\n\n\ndef _annotate_gap_impacts(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:\n    return [{**gap, "impact": _gap_impact(gap)} for gap in gaps]\n\n\ndef _all_gaps(passes: list[dict[str, Any]], plan: list[dict[str, Any]], errors: list[str], models: list[str], experience: dict[str, Any]) -> list[dict[str, Any]]:\n    effective = _effective_passes(passes)\n    gaps = [*_recurrence_gaps(effective, experience), *assess(effective, plan, errors, len(models))]\n    return _annotate_gap_impacts(gaps)\n\n\ndef _assurance_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:\n    return [gap for gap in gaps if gap.get("impact") == "assurance"]\n\n\ndef _confidence_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:\n    return [gap for gap in gaps if gap.get("impact") == "confidence"]\n\n\ndef _final_summary(round_count: int, member_count: int, findings: list[dict[str, Any]], final_gaps: list[dict[str, Any]]) -> str:\n    assurance_count = len(_assurance_gaps(final_gaps))\n    return (\n        f"Cpl completed {round_count} council round(s) with {member_count} distinct model member(s). "\n        f"{len(findings)} effective grounded finding(s) remain, {assurance_count} assurance gap(s) remain, "\n        f"and {len(final_gaps) - assurance_count} confidence or informational gap(s) remain auditable."\n    )\n\n\n''',
    )
    replace_once(
        "main_review/cpl_runtime.py",
        '''    final_gaps = _all_gaps(passes, plan, errors, models, experience)\n    if final_gaps and verdict == "PASS":\n        verdict = "NEEDS WORK"\n    unique_models = {str(item.get("model")) for item in passes if item.get("model")}\n    independence = round(len(unique_models) / max(1, len(passes)), 3)\n    if final_gaps:\n        confidence = max(0.0, confidence - min(0.25, 0.04 * len(final_gaps)))\n    if len(passes) > 1 and len(unique_models) == 1:\n        confidence = max(0.0, confidence - 0.12)\n\n''',
        '''    final_gaps = _all_gaps(passes, plan, errors, models, experience)\n    assurance_gaps = _assurance_gaps(final_gaps)\n    confidence_gaps = _confidence_gaps(final_gaps)\n    if assurance_gaps and verdict == "PASS":\n        verdict = "NEEDS WORK"\n    unique_models = {str(item.get("model")) for item in passes if item.get("model")}\n    independence = round(len(unique_models) / max(1, len(passes)), 3)\n    if final_gaps:\n        penalty = min(0.25, 0.04 * len(assurance_gaps) + 0.02 * len(confidence_gaps))\n        confidence = max(0.0, confidence - penalty)\n    if len(passes) > 1 and len(unique_models) == 1:\n        confidence = max(0.0, confidence - 0.12)\n\n''',
    )
    replace_once(
        "main_review/cpl_runtime.py",
        '''        "final_gaps": final_gaps,\n        "complete": not final_gaps,\n''',
        '''        "final_gaps": final_gaps,\n        "assurance_gaps": assurance_gaps,\n        "confidence_gaps": confidence_gaps,\n        "assurance_complete": not assurance_gaps,\n        "complete": not assurance_gaps,\n''',
    )


def patch_pr_reviewer() -> None:
    replace_once(
        "main_review/pr_reviewer.py",
        "from .diff_review import review_changed_files\n",
        "from .diff_review import review_changed_files\nfrom .finding_ledger import build_finding_ledger\n",
    )
    replace_between(
        "main_review/pr_reviewer.py",
        "def _required_actions(",
        "def run_independent_pr_review(",
        '''def _required_actions(\n    repository_review: dict[str, Any],\n    standard: dict[str, Any],\n    diff: dict[str, Any],\n    intelligence: dict[str, Any],\n    cpl: dict[str, Any],\n    ledger: dict[str, Any],\n) -> list[str]:\n    actions = [str(action) for action in ledger.get("required_actions", []) if str(action)]\n    gating_sources = {\n        str(finding.get("source_layer"))\n        for finding in ledger.get("gating_findings", [])\n        if isinstance(finding, dict)\n    }\n    repo_verdict = repository_review.get("verdict", {})\n    if (\n        isinstance(repo_verdict, dict)\n        and repo_verdict.get("verdict") != "PASS"\n        and "repository_review" not in gating_sources\n    ):\n        actions.append(str(repo_verdict.get("suggested_next_action", "Fix repository review findings.")))\n    for blocker in standard.get("blockers", []):\n        actions.append(str(blocker))\n    diff_verdict = diff.get("verdict", {}) if isinstance(diff, dict) else {}\n    if (\n        isinstance(diff_verdict, dict)\n        and diff_verdict.get("verdict") != "PASS"\n        and "diff_review" not in gating_sources\n    ):\n        actions.append(str(diff_verdict.get("suggested_next_action", "Answer changed-file review findings.")))\n    if (\n        intelligence.get("verdict") in {"BLOCK", "NEEDS WORK"}\n        and "review_intelligence" not in gating_sources\n        and not ledger.get("gating_findings")\n    ):\n        actions.append("Answer the promoted evidence-led review finding.")\n    if cpl.get("policy") == "required" and cpl.get("status") in {"unavailable", "error"}:\n        actions.append("Configure a reachable Cpl reasoning route and rerun Sergeant.")\n    return sorted(set(action for action in actions if action))\n\n\ndef _decide(\n    repository_review: dict[str, Any],\n    standard: dict[str, Any],\n    diff: dict[str, Any],\n    intelligence: dict[str, Any],\n    challenge: dict[str, Any],\n    cpl: dict[str, Any],\n    consensus: dict[str, Any],\n    ledger: dict[str, Any],\n) -> ReviewVerdict:\n    actions = _required_actions(repository_review, standard, diff, intelligence, cpl, ledger)\n    consensus_value = consensus.get("consensus")\n    ledger_verdict = ledger.get("verdict", "PASS")\n    notes = ["External reviewer comments are optional learning inputs, not required gates."]\n    if cpl.get("status") in {"unavailable", "disabled", "error"} and cpl.get("policy") != "required":\n        notes.append("Cpl reasoning was not available; deterministic Sergeant evidence remained authoritative.")\n    if cpl.get("status") == "completed_with_warnings":\n        notes.append("Cpl completed with one or more council or officer-support warnings.")\n    council_state = cpl.get("council", {})\n    if council_state.get("mode") not in {None, "not_deployed"} and council_state.get("complete") is False:\n        notes.append("Cpl preserved unresolved confidence or informational gaps without allowing them to invent a gate.")\n    counts = ledger.get("counts", {}) if isinstance(ledger, dict) else {}\n    if counts.get("duplicate_confirmations"):\n        notes.append(f"Merged {counts.get('duplicate_confirmations')} Cpl confirmation(s) into existing findings.")\n    if counts.get("advisory"):\n        notes.append(f"Preserved {counts.get('advisory')} non-gating Cpl advisory finding(s) for audit.")\n\n    if actions or consensus_value == "BLOCK" or ledger_verdict == "BLOCK":\n        return ReviewVerdict(\n            "REQUEST_CHANGES",\n            0.92,\n            "The adjudicated evidence ledger contains blocking or required work that remains unanswered.",\n            actions,\n            notes,\n        )\n    if consensus_value == "NEEDS WORK" or ledger_verdict == "NEEDS WORK":\n        return ReviewVerdict(\n            "COMMENT",\n            0.8,\n            "The adjudicated evidence ledger contains a supported non-blocking concern that should be considered before merge.",\n            actions,\n            notes,\n        )\n\n    challenge_confidence = float(challenge.get("confidence_after_challenge", 0.8))\n    cpl_confidence = float(cpl.get("confidence", challenge_confidence))\n    confidence = min(challenge_confidence, cpl_confidence) if cpl.get("status", "").startswith("completed") else challenge_confidence\n    return ReviewVerdict(\n        "APPROVE",\n        confidence,\n        "The adjudicated finding ledger has no merge-gating blocker or major finding, and the required proof sources are satisfied.",\n        notes=notes,\n    )\n\n\ndef _cpl_consensus_source(cpl: dict[str, Any]) -> dict[str, Any] | None:\n    status = cpl.get("status")\n    if cpl.get("policy") == "required" and status in {"unavailable", "error"}:\n        return {\n            "source": "cpl-availability",\n            "verdict": "NEEDS WORK",\n            "evidence": [cpl.get("reason", "Required Cpl reasoning did not complete.")],\n        }\n    return None\n\n\n''',
    )
    replace_once(
        "main_review/pr_reviewer.py",
        '''    cpl = run_cpl_review(root_path, semantic_files, cpl_context)\n\n    external_workspace = {"summary": {"total": 0}, "decisions": [], "ready_for_memory": []}\n''',
        '''    cpl = run_cpl_review(root_path, semantic_files, cpl_context)\n    ledger = build_finding_ledger(repository_review, diff, intelligence, cpl)\n\n    external_workspace = {"summary": {"total": 0}, "decisions": [], "ready_for_memory": []}\n''',
    )
    replace_between(
        "main_review/pr_reviewer.py",
        "    consensus_sources = [\n",
        "    return {\n",
        '''    consensus_sources = [\n        {\n            "source": "main-review",\n            "verdict": repository_review.get("verdict", {}).get("verdict"),\n            "evidence": repository_review.get("evidence", {}).get("findings", []),\n        },\n        {\n            "source": "diff-review",\n            "verdict": diff.get("verdict", {}).get("verdict"),\n            "evidence": diff.get("evidence", {}).get("findings", []),\n        },\n        {\n            "source": "adjudicated-finding-ledger",\n            "verdict": ledger.get("verdict"),\n            "evidence": ledger.get("actionable_findings", []),\n        },\n        {\n            "source": "standard-engine",\n            "verdict": "PASS" if standard.get("passed") else "NEEDS WORK",\n            "evidence": standard.get("blockers", []),\n        },\n        {\n            "source": "challenge-mode",\n            "verdict": "PASS" if challenge.get("trusted") else "NEEDS WORK",\n            "evidence": challenge.get("challenges", []),\n        },\n    ]\n    cpl_source = _cpl_consensus_source(cpl)\n    if cpl_source is not None:\n        consensus_sources.append(cpl_source)\n    consensus = build_consensus(consensus_sources)\n    verdict = _decide(repository_review, standard, diff, intelligence, challenge, cpl, consensus, ledger)\n''',
    )
    replace_once(
        "main_review/pr_reviewer.py",
        '''        "review_intelligence": intelligence,\n        "cpl_review": cpl,\n''',
        '''        "review_intelligence": intelligence,\n        "finding_ledger": ledger,\n        "cpl_review": cpl,\n''',
    )
    replace_once(
        "main_review/pr_reviewer.py",
        '''    lines.append(f"- Review intelligence verdict: {packet.get('review_intelligence', {}).get('verdict')}")\n''',
        '''    lines.append(f"- Review intelligence verdict: {packet.get('review_intelligence', {}).get('verdict')}")\n    ledger = packet.get("finding_ledger", {})\n    lines.append(f"- Adjudicated ledger verdict: {ledger.get('verdict', 'unavailable')}")\n    lines.append(f"- Adjudicated findings: {ledger.get('counts', {}).get('actionable', 0)}")\n''',
    )
    replace_between(
        "main_review/pr_reviewer.py",
        "    cpl_findings = cpl.get(\"findings\", []) if isinstance(cpl, dict) else []\n",
        "    plan = cpl.get(\"reasoning_plan\", []) if isinstance(cpl, dict) else []\n",
        '''    adjudicated_findings = ledger.get("actionable_findings", []) if isinstance(ledger, dict) else []\n    if adjudicated_findings:\n        lines.extend(["", "## Adjudicated findings"])\n        for finding in adjudicated_findings[:8]:\n            lines.append(\n                f"- **{finding.get('severity')} / {finding.get('category')}** "\n                f"`{finding.get('path')}:{finding.get('line_start')}-{finding.get('line_end')}`: "\n                f"{finding.get('message')}"\n            )\n            lines.append(f"  - Evidence: {finding.get('evidence')}")\n            lines.append(f"  - Authority: {finding.get('authority')}")\n            models = finding.get("supporting_models", [])\n            if models:\n                lines.append(f"  - Supporting models: {', '.join(models)}")\n    duplicate_count = ledger.get("counts", {}).get("duplicate_confirmations", 0) if isinstance(ledger, dict) else 0\n    advisory_count = ledger.get("counts", {}).get("advisory", 0) if isinstance(ledger, dict) else 0\n    if duplicate_count or advisory_count:\n        lines.extend(["", "## Adjudication audit"])\n        lines.append(f"- Cpl duplicate confirmations merged: {duplicate_count}")\n        lines.append(f"- Non-gating Cpl advisories preserved: {advisory_count}")\n\n''',
    )
    replace_between(
        "main_review/pr_reviewer.py",
        "    ranked = packet.get(\"review_intelligence\", {}).get(\"ranked_findings\", [])\n",
        "    lines.extend([\"\", \"## Rule\"])\n",
        '''    suppressed_count = ledger.get("counts", {}).get("suppressed", 0) if isinstance(ledger, dict) else 0\n    if suppressed_count:\n        lines.extend(["", "## Preserved audit evidence"])\n        lines.append(f"- {suppressed_count} duplicate, advisory, or evidence-challenged finding(s) remain in the packet for audit.")\n''',
    )


def patch_benchmark() -> None:
    replace_between(
        "main_review/review_benchmark.py",
        "def extract_predictions(",
        "def _path_ok(",
        '''def extract_predictions(packet: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:\n    """Return the unique user-facing finding ledger and its raw candidate count."""\n\n    raw: list[tuple[str, dict[str, Any]]] = []\n    ledger = packet.get("finding_ledger", {})\n    ledger_mode = isinstance(ledger, dict) and isinstance(ledger.get("actionable_findings"), list)\n    if ledger_mode:\n        raw.extend(\n            ("finding_ledger", item)\n            for item in ledger.get("actionable_findings", [])\n            if isinstance(item, dict)\n        )\n    else:\n        raw.extend(("repository", item) for item in _bucket(packet, "repository_review"))\n        raw.extend(("diff", item) for item in _bucket(packet, "diff_review"))\n        capability = packet.get("capability_review", {})\n        if isinstance(capability, dict):\n            raw.extend(("capability", item) for item in capability.get("findings", []) if isinstance(item, dict))\n        cpl = packet.get("cpl_review", packet.get("semantic_review", {}))\n        if isinstance(cpl, dict):\n            raw.extend(("cpl", item) for item in cpl.get("findings", []) if isinstance(item, dict))\n\n    unique: list[dict[str, Any]] = []\n    seen: set[tuple[object, ...]] = set()\n    valid_count = 0\n    for source, item in raw:\n        finding = _normalize_finding(item, source)\n        if finding is None:\n            continue\n        if not ledger_mode:\n            valid_count += 1\n        key = (finding["category"], finding["message"].lower(), finding["path"], finding["line_start"])\n        if key in seen:\n            continue\n        seen.add(key)\n        unique.append(finding)\n    if ledger_mode:\n        declared = ledger.get("raw_candidate_count")\n        valid_count = max(len(unique), int(declared)) if isinstance(declared, int) else len(unique)\n    return unique, valid_count\n\n\n''',
    )


def patch_reviewer_comparison() -> None:
    replace_once(
        "main_review/reviewer_comparison.py",
        '''def _sergeant_sources(packet: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:\n    sources: list[tuple[str, dict[str, Any]]] = []\n''',
        '''def _sergeant_sources(packet: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:\n    ledger = packet.get("finding_ledger", {}) if isinstance(packet, dict) else {}\n    actionable = ledger.get("actionable_findings", []) if isinstance(ledger, dict) else []\n    if isinstance(actionable, list):\n        rows = [("finding_ledger", item) for item in actionable if isinstance(item, dict)]\n        if rows:\n            return rows\n    sources: list[tuple[str, dict[str, Any]]] = []\n''',
    )


def main() -> None:
    patch_cpl_runtime()
    patch_pr_reviewer()
    patch_benchmark()
    patch_reviewer_comparison()


if __name__ == "__main__":
    main()
