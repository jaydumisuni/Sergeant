from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} anchor, found {count}.")
    return text.replace(old, new, 1)


# Centralize deterministic root-cause identity in Cpl council helpers.
council = Path("main_review/cpl_council.py")
text = council.read_text(encoding="utf-8")
old = '''def finding_key(finding: dict[str, Any]) -> tuple[object, ...]:
    message = re.sub(r"\\W+", " ", str(finding.get("message", "")).lower()).strip()
    return finding.get("path"), finding.get("line_start"), finding.get("line_end"), message
'''
new = '''ROOT_CAUSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "unsafe-shell-execution",
        re.compile(
            r"(?:shell\\s*=\\s*true|subprocess\\.(?:run|popen)|command\\s+injection|"
            r"arbitrary\\s+(?:shell\\s+)?commands?|shell\\s+command\\s+execution)",
            re.I,
        ),
    ),
    (
        "sql-injection",
        re.compile(r"(?:sql\\s+injection|unparameteri[sz]ed\\s+quer|raw\\s+sql|query\\s+concatenation)", re.I),
    ),
    (
        "unsafe-file-access",
        re.compile(r"(?:path\\s+traversal|directory\\s+traversal|untrusted\\s+path|file\\s+access\\s+without\\s+containment)", re.I),
    ),
    (
        "authorization-gap",
        re.compile(r"(?:missing\\s+authorization|lacks?\\s+(?:an?\\s+)?authorization|privileged\\s+route.*without)", re.I),
    ),
    (
        "secret-exposure",
        re.compile(r"(?:secret|credential|api\\s*key|token).*(?:leak|expos|log|print)", re.I),
    ),
)


def finding_root_cause(finding: dict[str, Any]) -> str:
    """Return a deterministic root-cause class for well-known defect shapes."""

    text = " ".join(
        str(finding.get(field, ""))
        for field in ("message", "evidence", "why_it_matters", "safer_alternative", "root_cause")
    )
    for name, pattern in ROOT_CAUSE_PATTERNS:
        if pattern.search(text):
            return name
    return str(finding.get("root_cause") or "").strip().lower()


def finding_key(finding: dict[str, Any]) -> tuple[object, ...]:
    """Identify one underlying defect across model wording and nearby line drift."""

    path = str(finding.get("path") or "").replace("\\\\", "/")
    category = str(finding.get("category") or "other").strip().lower()
    root_cause = finding_root_cause(finding)
    if root_cause:
        try:
            line_start = max(1, int(finding.get("line_start") or 1))
        except (TypeError, ValueError):
            line_start = 1
        line_window = (line_start - 1) // 10
        return path, category, root_cause, line_window

    message = re.sub(r"\\W+", " ", str(finding.get("message", "")).lower()).strip()
    return path, finding.get("line_start"), finding.get("line_end"), message
'''
text = replace_once(text, old, new, "finding_key")
council.write_text(text, encoding="utf-8")


# Reuse that identity in the pass merger instead of maintaining a second exact-string key.
review = Path("main_review/llm_review.py")
text = review.read_text(encoding="utf-8")
text = replace_once(
    text,
    "from .cpl_reasoning import (\n",
    "from .cpl_council import finding_key\nfrom .cpl_reasoning import (\n",
    "llm_review council import",
)
old = '''def _finding_key(finding: dict[str, Any]) -> tuple[object, ...]:
    message = re.sub(r"\\W+", " ", str(finding.get("message", "")).lower()).strip()
    return (
        finding.get("path"),
        finding.get("line_start"),
        finding.get("line_end"),
        message,
    )


'''
text = replace_once(text, old, "", "llm_review local finding key")
text = text.replace("key = _finding_key(finding)", "key = finding_key(finding)")
if "_finding_key(" in text:
    raise SystemExit("A stale llm_review _finding_key reference remains.")
review.write_text(text, encoding="utf-8")


# Add expected-fixture contract support to the focused live council proof.
cli = Path("main_review/cloudflare_cli.py")
text = cli.read_text(encoding="utf-8")
anchor = '''def run_council_proof(
    settings: CloudflareGatewaySettings,
    *,
    root: str | Path,
    changed_files: list[str],
) -> dict[str, Any]:
'''
replacement = '''def _finding_supporting_models(finding: dict[str, Any]) -> list[str]:
    values = [
        *finding.get("supporting_models", []),
        *finding.get("council_confirmed_by", []),
    ]
    return sorted({str(value) for value in values if str(value).strip()})


def _expected_finding_result(
    findings: list[dict[str, Any]],
    *,
    expected_path: str,
    expected_category: str,
    expected_severity: str,
    expected_evidence: str,
    minimum_supporting_models: int,
) -> dict[str, Any]:
    expected_path = expected_path.strip()
    expected_category = expected_category.strip().lower()
    expected_severity = expected_severity.strip().lower()
    expected_evidence = expected_evidence.strip().lower()
    required = bool(expected_path or expected_category or expected_severity or expected_evidence)
    matches: list[dict[str, Any]] = []
    for finding in findings:
        if expected_path and str(finding.get("path") or "") != expected_path:
            continue
        if expected_category and str(finding.get("category") or "").lower() != expected_category:
            continue
        if expected_severity and str(finding.get("severity") or "").lower() != expected_severity:
            continue
        searchable = " ".join(
            str(finding.get(field, ""))
            for field in ("message", "evidence", "why_it_matters", "safer_alternative", "root_cause")
        ).lower()
        if expected_evidence and expected_evidence not in searchable:
            continue
        models = _finding_supporting_models(finding)
        matches.append({
            "path": finding.get("path"),
            "category": finding.get("category"),
            "severity": finding.get("severity"),
            "message": finding.get("message"),
            "supporting_models": models,
            "support_count": len(models),
        })
    passed = (not required) or any(
        int(item.get("support_count", 0)) >= minimum_supporting_models for item in matches
    )
    return {
        "required": required,
        "passed": passed,
        "expected_path": expected_path,
        "expected_category": expected_category,
        "expected_severity": expected_severity,
        "expected_evidence": expected_evidence,
        "minimum_supporting_models": minimum_supporting_models,
        "matches": matches,
    }


def run_council_proof(
    settings: CloudflareGatewaySettings,
    *,
    root: str | Path,
    changed_files: list[str],
    expected_verdict: str = "",
    expected_path: str = "",
    expected_category: str = "",
    expected_severity: str = "",
    expected_evidence: str = "",
    minimum_supporting_models: int = 1,
) -> dict[str, Any]:
'''
text = replace_once(text, anchor, replacement, "run_council_proof signature")
old = '''    verdict = str(result.get("verdict") or "")
    passed = (
        result.get("status") == "completed"
        and verdict in VALID_COUNCIL_VERDICTS
        and len(distinct_models) > 1
        and council.get("true_model_independence") is True
        and council.get("complete") is True
        and not errors
        and not final_gaps
    )
'''
new = '''    verdict = str(result.get("verdict") or "")
    effective_findings = [
        item for item in council.get("effective_findings", []) if isinstance(item, dict)
    ]
    expected_result = _expected_finding_result(
        effective_findings,
        expected_path=expected_path,
        expected_category=expected_category,
        expected_severity=expected_severity,
        expected_evidence=expected_evidence,
        minimum_supporting_models=max(1, minimum_supporting_models),
    )
    expected_verdict = expected_verdict.strip().upper()
    verdict_matches = not expected_verdict or verdict == expected_verdict
    passed = (
        result.get("status") == "completed"
        and verdict in VALID_COUNCIL_VERDICTS
        and verdict_matches
        and expected_result["passed"] is True
        and len(distinct_models) > 1
        and council.get("true_model_independence") is True
        and council.get("complete") is True
        and not errors
        and not final_gaps
    )
'''
text = replace_once(text, old, new, "council proof verdict logic")
text = replace_once(
    text,
    '''        "verdict": verdict,
        "errors": errors,
        "council": council,
''',
    '''        "verdict": verdict,
        "expected_verdict": expected_verdict,
        "verdict_matches": verdict_matches,
        "expected_finding": expected_result,
        "errors": errors,
        "council": council,
''',
    "council proof result fields",
)
text = replace_once(
    text,
    '''    council.add_argument("--output")
    council.add_argument("--no-fail", action="store_true")
''',
    '''    council.add_argument("--expected-verdict", choices=sorted(VALID_COUNCIL_VERDICTS), default="")
    council.add_argument("--expected-path", default="")
    council.add_argument("--expected-category", default="")
    council.add_argument("--expected-severity", default="")
    council.add_argument("--expected-evidence", default="")
    council.add_argument("--minimum-supporting-models", type=int, default=1)
    council.add_argument("--output")
    council.add_argument("--no-fail", action="store_true")
''',
    "council proof CLI arguments",
)
text = replace_once(
    text,
    '''            payload = run_council_proof(settings, root=args.path, changed_files=changed)
''',
    '''            payload = run_council_proof(
                settings,
                root=args.path,
                changed_files=changed,
                expected_verdict=args.expected_verdict,
                expected_path=args.expected_path,
                expected_category=args.expected_category,
                expected_severity=args.expected_severity,
                expected_evidence=args.expected_evidence,
                minimum_supporting_models=max(1, args.minimum_supporting_models),
            )
''',
    "council proof invocation",
)
cli.write_text(text, encoding="utf-8")


# Change the live workflow from all-model certification to viable-council certification.
workflow = Path(".github/workflows/cloudflare-live-certification.yml")
text = workflow.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''          sergeant-cloudflare --pretty council-proof build/live-council-fixture \\
            --files src/auth.py \\
            --output build/cloudflare-council-proof.json \\
            --no-fail
''',
    '''          sergeant-cloudflare --pretty council-proof build/live-council-fixture \\
            --files src/auth.py \\
            --expected-verdict BLOCK \\
            --expected-path src/auth.py \\
            --expected-category security \\
            --expected-severity blocker \\
            --expected-evidence shell=True \\
            --minimum-supporting-models 2 \\
            --output build/cloudflare-council-proof.json \\
            --no-fail
''',
    "focused council workflow command",
)
old = '''          payload = {
              "schema_version": "sergeant.cloudflare-live-certification.v1",
              "provider": "cloudflare-workers-ai",
              "preset": "${{ inputs.preset }}",
              "route_valid": status.get("valid") is True,
              "configured_model_count": models.get("model_count", 0),
              "structured_model_pass_count": models.get("passed_count", 0),
              "all_configured_models_passed": models.get("all_passed") is True,
              "council_passed": council.get("passed") is True,
              "distinct_models": council.get("distinct_models", []),
              "model_call_count": council.get("model_call_count", 0),
              "true_model_independence": council.get("true_model_independence", False),
              "council_complete": council.get("council_complete", False),
              "errors": council.get("errors", []),
              "final_gaps": council.get("final_gaps", []),
          }
          payload["passed"] = bool(
              payload["route_valid"]
              and payload["all_configured_models_passed"]
              and payload["council_passed"]
              and payload["true_model_independence"]
              and payload["council_complete"]
          )
'''
new = '''          rows = models.get("models", []) if isinstance(models.get("models"), list) else []
          certified_models = [
              str(item.get("model"))
              for item in rows
              if isinstance(item, dict) and item.get("passed") is True and item.get("model")
          ]
          probationary_models = [
              {
                  "model": str(item.get("model")),
                  "error": item.get("error"),
                  "response": item.get("response"),
              }
              for item in rows
              if isinstance(item, dict) and item.get("passed") is not True and item.get("model")
          ]
          minimum_certified_models = 2
          payload = {
              "schema_version": "sergeant.cloudflare-live-certification.v2",
              "provider": "cloudflare-workers-ai",
              "preset": "${{ inputs.preset }}",
              "route_valid": status.get("valid") is True,
              "configured_model_count": models.get("model_count", 0),
              "structured_model_pass_count": models.get("passed_count", 0),
              "minimum_certified_models": minimum_certified_models,
              "sufficient_certified_models": len(certified_models) >= minimum_certified_models,
              "certified_models": certified_models,
              "probationary_models": probationary_models,
              "all_configured_models_passed": models.get("all_passed") is True,
              "preset_status": "fully_certified" if models.get("all_passed") is True else "partially_certified",
              "council_passed": council.get("passed") is True,
              "expected_finding_passed": council.get("expected_finding", {}).get("passed") is True,
              "verdict_matches": council.get("verdict_matches") is True,
              "distinct_models": council.get("distinct_models", []),
              "model_call_count": council.get("model_call_count", 0),
              "true_model_independence": council.get("true_model_independence", False),
              "council_complete": council.get("council_complete", False),
              "errors": council.get("errors", []),
              "final_gaps": council.get("final_gaps", []),
          }
          payload["passed"] = bool(
              payload["route_valid"]
              and payload["sufficient_certified_models"]
              and payload["council_passed"]
              and payload["expected_finding_passed"]
              and payload["verdict_matches"]
              and payload["true_model_independence"]
              and payload["council_complete"]
          )
'''
text = replace_once(text, old, new, "workflow certification summary")
workflow.write_text(text, encoding="utf-8")
