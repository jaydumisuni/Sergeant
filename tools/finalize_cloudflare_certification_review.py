from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one {label} anchor, found {count}.")
    return text.replace(old, new, 1)


council = Path("main_review/cpl_council.py")
text = council.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''        for field in ("message", "evidence", "why_it_matters", "safer_alternative", "root_cause")
''',
    '''        for field in ("message", "evidence", "why_it_matters", "root_cause")
''',
    "observed-defect root-cause fields",
)
text = replace_once(
    text,
    '''                    and any(findings_match(finding, candidate) for candidate in other.get("findings", []))
''',
    '''                    and any(
                        candidate.get("severity") in {"blocker", "major"}
                        and findings_match(finding, candidate)
                        for candidate in other.get("findings", [])
                    )
''',
    "high-impact independent support filter",
)
council.write_text(text, encoding="utf-8")


review = Path("main_review/llm_review.py")
text = review.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''ALLOWED_VERDICTS = {"PASS", "NEEDS WORK", "BLOCK"}
ALLOWED_SEVERITIES = {"blocker", "major", "minor", "note"}
''',
    '''ALLOWED_VERDICTS = {"PASS", "NEEDS WORK", "BLOCK"}
ALLOWED_SEVERITIES = {"blocker", "major", "minor", "note"}
SEVERITY_RANK = {"note": 0, "minor": 1, "major": 2, "blocker": 3}
''',
    "severity rank constant",
)
old = '''            models = merged.setdefault("supporting_models", [])
            if item.get("model") not in models:
                models.append(item.get("model"))
            specialists = merged.setdefault("supporting_specialists", [])
            if item.get("specialist") not in specialists:
                specialists.append(item.get("specialist"))
'''
new = '''            incoming_severity = str(finding.get("severity") or "note")
            existing_severity = str(merged.get("severity") or "note")
            if SEVERITY_RANK.get(incoming_severity, 0) > SEVERITY_RANK.get(existing_severity, 0):
                for field in (
                    "severity",
                    "category",
                    "path",
                    "line_start",
                    "line_end",
                    "message",
                    "evidence",
                    "evidence_verified",
                    "why_it_matters",
                    "safer_alternative",
                    "root_cause",
                ):
                    if field in finding:
                        merged[field] = finding[field]
            models = merged.setdefault("supporting_models", [])
            if item.get("model") not in models:
                models.append(item.get("model"))
            specialists = merged.setdefault("supporting_specialists", [])
            if item.get("specialist") not in specialists:
                specialists.append(item.get("specialist"))
'''
text = replace_once(text, old, new, "strongest severity reconciliation")
review.write_text(text, encoding="utf-8")


cli = Path("main_review/cloudflare_cli.py")
text = cli.read_text(encoding="utf-8")
old = '''def _completed_matching_models(finding: dict[str, Any], passes: list[dict[str, Any]]) -> list[str]:
    return sorted({
        str(report.get("model"))
        for report in passes
        if report.get("model")
        and any(findings_match(finding, candidate) for candidate in report.get("findings", []))
    })
'''
new = '''def _candidate_meets_expected_contract(
    candidate: dict[str, Any],
    *,
    expected_category: str,
    expected_severity: str,
    expected_evidence: str,
) -> bool:
    if expected_category and str(candidate.get("category") or "").lower() != expected_category:
        return False
    if expected_severity and str(candidate.get("severity") or "").lower() != expected_severity:
        return False
    if expected_evidence:
        evidence = str(candidate.get("evidence") or "").lower()
        if candidate.get("evidence_verified") is not True or expected_evidence not in evidence:
            return False
    return True


def _completed_matching_models(
    finding: dict[str, Any],
    passes: list[dict[str, Any]],
    *,
    expected_category: str,
    expected_severity: str,
    expected_evidence: str,
) -> list[str]:
    return sorted({
        str(report.get("model"))
        for report in passes
        if report.get("model")
        and any(
            findings_match(finding, candidate)
            and _candidate_meets_expected_contract(
                candidate,
                expected_category=expected_category,
                expected_severity=expected_severity,
                expected_evidence=expected_evidence,
            )
            for candidate in report.get("findings", [])
        )
    })
'''
text = replace_once(text, old, new, "completed matching model qualification")
text = replace_once(
    text,
    '''        models = _completed_matching_models(finding, passes)
''',
    '''        models = _completed_matching_models(
            finding,
            passes,
            expected_category=expected_category,
            expected_severity=expected_severity,
            expected_evidence=expected_evidence,
        )
''',
    "expected finding support invocation",
)
cli.write_text(text, encoding="utf-8")


tests = Path("tests/test_cloudflare_certification_semantics.py")
text = tests.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''def test_expected_contract_uses_verified_evidence_only() -> None:
    finding = _shell_finding(line=4, message="Unsafe command", evidence="subprocess.run(command)")
    finding["safer_alternative"] = "Avoid shell=True."
    finding["supporting_models"] = [MODEL_A, MODEL_B]
''',
    '''def test_expected_contract_uses_verified_evidence_only() -> None:
    finding = _shell_finding(
        line=4,
        message="Unsafe command",
        evidence="subprocess.run(command, shell=True)",
    )
    finding["evidence_verified"] = False
    finding["supporting_models"] = [MODEL_A, MODEL_B]
''',
    "verified evidence isolation test",
)
append = '''


def test_remediation_text_does_not_define_root_cause() -> None:
    finding = _shell_finding(
        line=4,
        message="Subprocess environment inherits an unsafe PATH",
        evidence="subprocess.run([tool, '--version'], shell=False)",
    )
    finding["why_it_matters"] = "Executable resolution may select an unintended binary."
    finding["safer_alternative"] = "Keep shell=True disabled and use an absolute executable path."

    assert finding_root_cause(finding) != "unsafe-shell-execution"


def test_pass_merger_retains_strongest_severity_regardless_of_order() -> None:
    major = _shell_finding(line=4, message="Command injection risk", evidence="shell=True")
    major["severity"] = "major"
    blocker = _shell_finding(line=5, message="Arbitrary shell command execution", evidence="shell=True")
    blocker["severity"] = "blocker"

    for ordered in ((major, blocker), (blocker, major)):
        findings, verdict, _ = _merge_passes([
            {
                "model": MODEL_A,
                "specialist": "generalist",
                "verdict": "NEEDS WORK",
                "confidence": 0.9,
                "findings": [ordered[0]],
            },
            {
                "model": MODEL_B,
                "specialist": "security",
                "verdict": "BLOCK",
                "confidence": 0.9,
                "findings": [ordered[1]],
            },
        ])

        assert len(findings) == 1
        assert findings[0]["severity"] == "blocker"
        assert verdict == "BLOCK"


def test_expected_support_requires_each_model_to_meet_full_contract() -> None:
    blocker = _shell_finding(line=4, message="Command injection", evidence="shell=True")
    weaker = _shell_finding(line=5, message="Shell execution concern", evidence="shell=True")
    weaker["severity"] = "minor"
    result = cloudflare_cli._expected_finding_result(
        [blocker],
        [
            {"model": MODEL_A, "findings": [blocker]},
            {"model": MODEL_B, "findings": [weaker]},
        ],
        expected_path="src/auth.py",
        expected_category="security",
        expected_severity="blocker",
        expected_evidence="shell=true",
        minimum_supporting_models=2,
    )

    assert result["passed"] is False
    assert result["matches"][0]["supporting_models"] == [MODEL_A]
'''
if "test_remediation_text_does_not_define_root_cause" not in text:
    text += append
tests.write_text(text, encoding="utf-8")
