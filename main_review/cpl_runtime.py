"""Council-led Cpl runtime with officer feedback and verified experience."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .cpl_council import agreement, assess, available_models, instruction, max_members, max_rounds
from .cpl_council_prompt import follow_up_prompt, member_records, report_table
from .cpl_experience import detect_recurrences, retrieve_experience
from .cpl_reasoning import SPECIALISTS, specialist_system_prompt
from .llm_provider import LLMProviderError, LLMRoute, LLMSettings, discover_route, invoke_json
from .llm_review import (
    SYSTEM_PROMPT,
    _build_user_prompt,
    _merge_passes,
    _validate_pass,
    collect_changed_file_excerpts,
    run_cpl_review as run_cpl_review_once,
)


def _annotate_base(result: dict[str, Any]) -> None:
    plan = {str(item.get("specialist")): item for item in result.get("reasoning_plan", []) if isinstance(item, dict)}
    for report in result.get("passes", []):
        specialist = str(report.get("specialist") or "generalist")
        report.setdefault("council_round", 1)
        report.setdefault("council_member_role", "core_member")
        report.setdefault("supported_officer", plan.get(specialist, {}).get("officer") or ("Cpl" if specialist == "generalist" else None))


def _choose_model(models: list[str], used: set[str], fallback: str, member_limit: int) -> tuple[str, str]:
    unused = [model for model in models if model not in used]
    if unused and len(used) < member_limit:
        return unused[0], "new_member"
    return fallback, "role_separated_reuse"


def _coverage(passes: list[dict[str, Any]], original: dict[str, Any]) -> dict[str, Any]:
    files = sorted({path for item in passes for path in item.get("coverage", {}).get("files_reviewed", [])})
    areas = sorted({area for item in passes for area in item.get("coverage", {}).get("areas", [])})
    return {**original, "files_reviewed": files, "areas": areas}


def run_cpl_review(
    root: str | Path,
    changed_files: list[str],
    deterministic_context: dict[str, Any],
    *,
    settings: LLMSettings | None = None,
    route: LLMRoute | None = None,
) -> dict[str, Any]:
    """Run Cpl as an elastic model council commanding permanent officers."""

    root_path = Path(root)
    settings = settings or LLMSettings.from_environment()
    experience = retrieve_experience(root_path, changed_files, officers={item.officer for item in SPECIALISTS.values()})
    enriched_context = {
        **deterministic_context,
        "cpl_verified_experience": {
            "events": experience.get("events", [])[:12],
            "canonical_lessons": experience.get("canonical_lessons", [])[:8],
            "anti_repeat_rule": experience.get("anti_repeat_rule"),
        },
    }
    resolved_route = route or (discover_route(settings) if settings.enabled else None)
    result = run_cpl_review_once(root_path, changed_files, enriched_context, settings=settings, route=resolved_route)
    result["experience"] = experience
    result["memory_checked"] = True

    if result.get("status") not in {"completed", "completed_with_warnings"} or resolved_route is None:
        result["council"] = {"mode": "not_deployed", "rounds": [], "members": [], "complete": result.get("status") == "disabled"}
        result["recurrences"] = []
        return result

    _annotate_base(result)
    passes = list(result.get("passes", []))
    plan = list(result.get("reasoning_plan", []))
    errors = list(result.get("errors", []))
    models = available_models(resolved_route)
    used = {str(item.get("model")) for item in passes if item.get("model")}
    rounds: list[dict[str, Any]] = []
    recruitment: list[dict[str, Any]] = []
    previous_signature: tuple[tuple[str, str, str], ...] | None = None
    files, excerpts = collect_changed_file_excerpts(root_path, changed_files)
    base_prompt = _build_user_prompt(changed_files, excerpts, enriched_context)

    for round_number in range(2, max_rounds() + 1):
        gaps_before = assess(passes, plan, errors, len(models))
        if not gaps_before:
            break
        signature = tuple((str(item.get("type")), str(item.get("specialist")), str(item.get("reason"))) for item in gaps_before)
        if signature == previous_signature:
            break
        previous_signature = signature
        gap = gaps_before[0]
        specialist = str(gap.get("specialist") or "correctness")
        assignment = SPECIALISTS.get(specialist, SPECIALISTS["correctness"])
        command = instruction(gap, round_number)
        selected_model, admission = _choose_model(models, used, resolved_route.model, max_members())
        selected_route = replace(resolved_route, model=selected_model)
        recruited = {
            "round": round_number,
            "model": selected_model,
            "admission": admission,
            "required_capability": specialist,
            "reason": gap.get("reason"),
            "temporary": True,
        }
        recruitment.append(recruited)
        table = report_table(passes)
        officer_report: dict[str, Any] | None = None
        try:
            payload = invoke_json(
                selected_route,
                system_prompt=specialist_system_prompt(SYSTEM_PROMPT, assignment),
                user_prompt=follow_up_prompt(base_prompt, table, command, experience, round_number),
            )
            officer_report = _validate_pass(payload, files, route=selected_route, assignment=assignment)
            officer_report.update({
                "council_round": round_number,
                "council_member_role": "recruited_gap_specialist",
                "supported_officer": assignment.officer,
                "instruction_received": command,
                "admission": admission,
            })
            passes.append(officer_report)
            used.add(selected_model)
        except LLMProviderError as error:
            errors.append(f"council round {round_number} / {specialist}: {error}")
        rounds.append({
            "round": round_number,
            "table": table,
            "gaps_before": gaps_before,
            "instructions": [command],
            "recruitment": recruited,
            "officer_report": officer_report,
            "gaps_after": assess(passes, plan, errors, len(models)),
        })

    findings, verdict, confidence = _merge_passes(passes)
    final_gaps = assess(passes, plan, errors, len(models))
    unique_models = {str(item.get("model")) for item in passes if item.get("model")}
    independence = round(len(unique_models) / max(1, len(passes)), 3)
    if final_gaps:
        confidence = max(0.0, confidence - min(0.25, 0.04 * len(final_gaps)))
    if len(passes) > 1 and len(unique_models) == 1:
        confidence = max(0.0, confidence - 0.12)

    result.update({
        "status": "completed" if not errors else "completed_with_warnings",
        "verdict": verdict,
        "confidence": round(confidence, 3),
        "summary": " ".join(item.get("summary", "") for item in passes if item.get("summary")).strip(),
        "findings": findings,
        "passes": passes,
        "coverage": _coverage(passes, result.get("coverage", {})),
        "unanswered_questions": sorted({question for item in passes for question in item.get("unanswered_questions", [])}),
        "errors": errors,
        "reason": "Cpl retrieved verified experience, tabled officer reports, recruited council support for named gaps, and returned grounded evidence to Sergeant.",
    })
    result["recurrences"] = detect_recurrences(findings, experience)
    result["council"] = {
        "mode": "elastic_multi_model" if len(unique_models) > 1 else "single_model_role_separated",
        "core_round": 1,
        "rounds": rounds,
        "round_count": 1 + len(rounds),
        "max_rounds": max_rounds(),
        "members": member_records(passes),
        "member_count": len(unique_models),
        "max_members": max_members(),
        "recruitment": recruitment,
        "agreement": agreement(passes),
        "model_independence": independence,
        "true_model_independence": len(unique_models) > 1,
        "final_gaps": final_gaps,
        "complete": not final_gaps,
        "limitations": ["Only one model served multiple role-separated passes."] if len(unique_models) == 1 and len(passes) > 1 else [],
        "officer_instructions": [command for item in rounds for command in item.get("instructions", [])],
    }
    return result


def run_llm_review(
    root: str | Path,
    changed_files: list[str],
    deterministic_context: dict[str, Any],
    *,
    settings: LLMSettings | None = None,
    route: LLMRoute | None = None,
) -> dict[str, Any]:
    return run_cpl_review(root, changed_files, deterministic_context, settings=settings, route=route)
