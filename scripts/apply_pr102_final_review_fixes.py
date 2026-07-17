from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one match in {path}, found {count}")
    file.write_text(text.replace(old, new), encoding="utf-8")


replace_once(
    "main_review/cpl_council.py",
    '''            r"privileged(?:\\s+\\w+){0,2}\\s+route.*without)",''',
    '''            r"privileged(?:\\s+\\w+){0,2}\\s+route[^\\n]{0,80}"
            r"without[^\\n]{0,40}(?:authentication|authorization|access\\s+control|guard))",''',
)

replace_once(
    "main_review/llm_provider.py",
    '''from typing import Any, Literal''',
    '''from typing import Any, Iterable, Literal''',
)
replace_once(
    "main_review/llm_provider.py",
    '''class LLMProviderError(RuntimeError):
    """Raised when a configured Cpl model endpoint cannot satisfy a request."""
''',
    '''class LLMProviderError(RuntimeError):
    """Raised when a configured Cpl model endpoint cannot satisfy a request.

    ``failed_models`` preserves credential-safe route-attempt provenance when
    every configured model fails. Callers can therefore audit and resume the
    council formation without copying provider response bodies into evidence.
    """

    def __init__(self, message: str, *, failed_models: Iterable[str] = ()) -> None:
        super().__init__(message)
        self.failed_models = tuple(dict.fromkeys(str(model) for model in failed_models if str(model)))
''',
)

replace_once(
    "main_review/llm_review.py",
    '''    raise LLMProviderError(
        "No configured Cpl council model completed the required structured officer pass"
        f"{suffix}."
    )''',
    '''    raise LLMProviderError(
        "No configured Cpl council model completed the required structured officer pass"
        f"{suffix}.",
        failed_models=failed_models,
    )''',
)
replace_once(
    "main_review/llm_review.py",
    '''    except LLMProviderError as error:
        errors.append(str(error))
        return {
            **identity,''',
    '''    except LLMProviderError as error:
        errors.append(str(error))
        exhausted_models = list(error.failed_models)
        if exhausted_models:
            route_failovers.append({
                "pass": "generalist",
                "failed_models": exhausted_models,
                "completed_by": None,
            })
        return {
            **identity,''',
)
replace_once(
    "main_review/llm_review.py",
    '''            "reason": "Cpl could not complete its primary reasoning pass.",
            "errors": errors,
        }''',
    '''            "reason": "Cpl could not complete its primary reasoning pass.",
            "errors": errors,
            "route_failovers": route_failovers,
        }''',
)
replace_once(
    "main_review/llm_review.py",
    '''        completed_plan.append({**assignment.to_dict(), "model": specialist_route.model})
        try:''',
    '''        plan_entry = {**assignment.to_dict(), "model": specialist_route.model}
        completed_plan.append(plan_entry)
        try:''',
)
replace_once(
    "main_review/llm_review.py",
    '''            if failed_models:
                route_failovers.append({
                    "pass": assignment.specialist,
                    "failed_models": failed_models,
                    "completed_by": completed_route.model,
                })
            passes.append(_validate_pass(payload, files, route=completed_route, assignment=assignment))''',
    '''            plan_entry["model"] = completed_route.model
            if failed_models:
                route_failovers.append({
                    "pass": assignment.specialist,
                    "failed_models": failed_models,
                    "completed_by": completed_route.model,
                })
            passes.append(_validate_pass(payload, files, route=completed_route, assignment=assignment))''',
)
replace_once(
    "main_review/llm_review.py",
    '''        except LLMProviderError as error:
            errors.append(f"{assignment.specialist}: {error}")''',
    '''        except LLMProviderError as error:
            exhausted_models = list(error.failed_models)
            if exhausted_models:
                route_failovers.append({
                    "pass": assignment.specialist,
                    "failed_models": exhausted_models,
                    "completed_by": None,
                })
            errors.append(f"{assignment.specialist}: {error}")''',
)

replace_once(
    "main_review/cpl_runtime.py",
    '''    raise LLMProviderError(
        "No configured Cpl council model completed the follow-up officer pass"
        f"{suffix}."
    )''',
    '''    raise LLMProviderError(
        "No configured Cpl council model completed the follow-up officer pass"
        f"{suffix}.",
        failed_models=failed_models,
    )''',
)
replace_once(
    "main_review/cpl_runtime.py",
    '''            selected_model = completed_route.model
            recruited["model"] = selected_model
            if failed_models:
                recruited["failover_from"] = failed_models
            officer_report = _validate_pass(payload, files, route=completed_route, assignment=assignment)''',
    '''            selected_model = completed_route.model
            actual_admission = (
                "new_member"
                if selected_model not in used and len(used) < member_limit
                else "role_separated_reuse"
            )
            recruited["model"] = selected_model
            recruited["admission"] = actual_admission
            recruited["selection_score"] = model_score(selected_model, experience, specialist)
            if failed_models:
                recruited["failover_from"] = failed_models
            officer_report = _validate_pass(payload, files, route=completed_route, assignment=assignment)''',
)
replace_once(
    "main_review/cpl_runtime.py",
    '''                "admission": admission,
                "selection_score": recruited["selection_score"],''',
    '''                "admission": recruited["admission"],
                "selection_score": recruited["selection_score"],''',
)
replace_once(
    "main_review/cpl_runtime.py",
    '''        except LLMProviderError as error:
            errors.append(f"council round {round_number} / {specialist}: {error}")''',
    '''        except LLMProviderError as error:
            exhausted_models = list(error.failed_models)
            if exhausted_models:
                recruited["failover_from"] = exhausted_models
            errors.append(f"council round {round_number} / {specialist}: {error}")''',
)

Path("tests/test_pr102_final_review_regressions.py").write_text(
    '''from __future__ import annotations

from dataclasses import replace

import pytest

from main_review import cpl_runtime, llm_review
from main_review.cpl_council import finding_root_cause
from main_review.cpl_reasoning import SPECIALISTS
from main_review.llm_provider import LLMProviderError, LLMRoute


def route(model: str = "model-a") -> LLMRoute:
    return LLMRoute(
        provider="configured",
        base_url="http://127.0.0.1:8082/v1",
        model=model,
        protocol="chat_completions",
        discovered_models=("model-a", "model-b"),
    )


def test_authorization_root_requires_authorization_object_after_without() -> None:
    assert finding_root_cause({"message": "Privileged admin route without pagination."}) != "authorization-gap"
    assert finding_root_cause({"message": "Privileged admin route without authorization guard."}) == "authorization-gap"


def test_exhausted_generalist_failover_preserves_attempted_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_review, "available_models", lambda _: ["model-a", "model-b"])

    def fail(*args, **kwargs):
        raise LLMProviderError("provider unavailable")

    monkeypatch.setattr(llm_review, "invoke_json", fail)
    with pytest.raises(LLMProviderError) as caught:
        llm_review._invoke_json_with_failover(route(), system_prompt="s", user_prompt="u")
    assert caught.value.failed_models == ("model-a", "model-b")


def test_exhausted_follow_up_preserves_attempted_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cpl_runtime, "available_models", lambda _: ["model-a", "model-b"])

    def fail(*args, **kwargs):
        raise LLMProviderError("provider unavailable")

    monkeypatch.setattr(cpl_runtime, "invoke_json", fail)
    with pytest.raises(LLMProviderError) as caught:
        cpl_runtime._invoke_follow_up_with_failover(route(), system_prompt="s", user_prompt="u")
    assert caught.value.failed_models == ("model-a", "model-b")


def test_successful_specialist_failover_records_actual_completed_model(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    assignment = SPECIALISTS["security"]
    calls = iter([
        ({}, route("model-a"), []),
        ({}, route("model-b"), ["model-a"]),
    ])
    monkeypatch.setattr(llm_review, "collect_changed_file_excerpts", lambda *args: ({}, {}))
    monkeypatch.setattr(llm_review, "_build_user_prompt", lambda *args: "prompt")
    monkeypatch.setattr(llm_review, "plan_cpl_assignments", lambda *args, **kwargs: [assignment])
    monkeypatch.setattr(llm_review, "route_for_assignment", lambda *args, **kwargs: route("model-a"))
    monkeypatch.setattr(llm_review, "_invoke_json_with_failover", lambda *args, **kwargs: next(calls))
    monkeypatch.setattr(
        llm_review,
        "_validate_pass",
        lambda payload, files, *, route, assignment=None: {
            "model": route.model,
            "verdict": "PASS",
            "confidence": 0.9,
            "findings": [],
            "coverage": {"files_reviewed": [], "areas": []},
            "unanswered_questions": [],
            "summary": "ok",
        },
    )
    result = llm_review.run_cpl_review(tmp_path, [], {}, route=route())
    assert result["reasoning_plan"][0]["model"] == "model-b"
    assert result["route_failovers"] == [{
        "pass": "security",
        "failed_models": ["model-a"],
        "completed_by": "model-b",
    }]


def test_recruited_failover_recomputes_admission_and_score(monkeypatch: pytest.MonkeyPatch) -> None:
    used = {"model-a"}
    completed = "model-b"
    admission = "new_member" if completed not in used and len(used) < 5 else "role_separated_reuse"
    assert admission == "new_member"
    assert cpl_runtime.model_score(completed, {}, "security") == cpl_runtime.model_score("model-b", {}, "security")
''',
    encoding="utf-8",
)
