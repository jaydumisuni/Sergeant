from __future__ import annotations

from pathlib import Path

path = Path("main_review/cpl_runtime.py")
text = path.read_text(encoding="utf-8")

old = """from .cpl_experience import detect_recurrences, retrieve_experience
from .cpl_reasoning import SPECIALISTS, specialist_system_prompt
"""
new = """from .cpl_experience import detect_recurrences, retrieve_experience
from .finding_adjudication import adjudicate_cpl_findings, classify_council_gaps
from .cpl_reasoning import SPECIALISTS, specialist_system_prompt
"""
assert old in text, "cpl_runtime import anchor changed"
text = text.replace(old, new, 1)

old = """    effective_passes = _effective_passes(passes)
    findings, verdict, confidence = _merge_passes(effective_passes)
    _annotate_confirmations(findings, passes)
    final_gaps = _all_gaps(passes, plan, errors, models, experience)
    if final_gaps and verdict == "PASS":
        verdict = "NEEDS WORK"
    unique_models = {str(item.get("model")) for item in passes if item.get("model")}
    independence = round(len(unique_models) / max(1, len(passes)), 3)
"""
new = """    effective_passes = _effective_passes(passes)
    raw_findings, raw_verdict, confidence = _merge_passes(effective_passes)
    _annotate_confirmations(raw_findings, passes)
    final_gaps = _all_gaps(passes, plan, errors, models, experience)
    gap_classification = classify_council_gaps(final_gaps)
    unique_models = {str(item.get("model")) for item in passes if item.get("model")}
    minimum_supporting_models = 2 if len(unique_models) > 1 else 1
    adjudication = adjudicate_cpl_findings(
        raw_findings,
        deterministic_context,
        minimum_supporting_models=minimum_supporting_models,
    )
    findings = list(adjudication["actionable_findings"])
    verdict = str(adjudication["verdict"])
    if gap_classification["verdict_gaps"] and verdict == "PASS":
        verdict = "NEEDS WORK"
    independence = round(len(unique_models) / max(1, len(passes)), 3)
"""
assert old in text, "cpl_runtime final merge anchor changed"
text = text.replace(old, new, 1)

old = """        "verdict": verdict,
        "confidence": round(confidence, 3),
        "summary": _final_summary(round_count, len(unique_models), findings, final_gaps),
        "findings": findings,
        "passes": passes,
        "coverage": _coverage(effective_passes, result.get("coverage", {})),
        "unanswered_questions": unresolved_questions,
        "errors": errors,
        "reason": "Cpl retrieved verified experience, selected council members from proven service records, tabled officer reports, explicitly adjudicated earlier findings, and returned grounded evidence to Sergeant.",
"""
new = """        "verdict": verdict,
        "raw_verdict": raw_verdict,
        "confidence": round(confidence, 3),
        "summary": _final_summary(round_count, len(unique_models), findings, final_gaps),
        "findings": findings,
        "raw_findings": raw_findings,
        "adjudication": adjudication,
        "confirmations": adjudication["confirmations"],
        "advisory_findings": adjudication["advisory_findings"],
        "rejected_findings": adjudication["rejected_findings"],
        "passes": passes,
        "coverage": _coverage(effective_passes, result.get("coverage", {})),
        "unanswered_questions": unresolved_questions,
        "errors": errors,
        "reason": "Cpl retrieved verified experience, selected council members from proven service records, tabled officer reports, explicitly adjudicated earlier findings, and returned grounded evidence to Sergeant. Deterministic Sergeant findings retain gate authority; Cpl confirmations, advice, and rejected claims remain separately auditable.",
"""
assert old in text, "cpl_runtime result anchor changed"
text = text.replace(old, new, 1)

old = '    result["recurrences"] = detect_recurrences(findings, experience)\n'
new = '    result["recurrences"] = detect_recurrences(raw_findings, experience)\n'
assert old in text, "cpl_runtime recurrence anchor changed"
text = text.replace(old, new, 1)

old = """        "final_gaps": final_gaps,
        "complete": not final_gaps,
        "limitations": ["Only one model served multiple role-separated passes."] if len(unique_models) == 1 and len(passes) > 1 else [],
        "officer_instructions": [command for item in rounds for command in item.get("instructions", [])],
        "effective_findings": findings,
"""
new = """        "final_gaps": final_gaps,
        "verdict_gaps": gap_classification["verdict_gaps"],
        "confidence_gaps": gap_classification["confidence_gaps"],
        "informational_gaps": gap_classification["informational_gaps"],
        "complete": not final_gaps,
        "verdict_complete": not gap_classification["verdict_gaps"],
        "limitations": ["Only one model served multiple role-separated passes."] if len(unique_models) == 1 and len(passes) > 1 else [],
        "officer_instructions": [command for item in rounds for command in item.get("instructions", [])],
        "effective_findings": raw_findings,
        "adjudicated_findings": findings,
"""
assert old in text, "cpl_runtime council anchor changed"
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
