from __future__ import annotations

from pathlib import Path

from main_review.officer_council import run_deterministic_officer_council


def _write(root: Path, relative: str, text: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return relative


def test_officers_catch_the_pr103_miss_family_without_models(tmp_path: Path) -> None:
    changed = [
        _write(
            tmp_path,
            ".github/workflows/cloudflare-full-council-certification.yml",
            """name: certification
on:
  pull_request:
    paths:
      - 'main_review/cloudflare_incremental_certification.py'
jobs:
  certify:
    env:
      SERGEANT_CLOUDFLARE_ACCOUNT_ID: ${{ secrets.SERGEANT_CLOUDFLARE_ACCOUNT_ID }}
      SERGEANT_CLOUDFLARE_API_TOKEN: ${{ secrets.SERGEANT_CLOUDFLARE_API_TOKEN }}
    steps:
      - uses: actions/checkout@v4
      - run: python -m pip install -e .
      - run: python -m pytest -q tests/test_cloudflare_usage_governor.py
      - name: Enforce all-member certification
        run: |
          python - <<'PY'
          payload = {'passed': True}
          assert payload.get('passed') is True
          PY
""",
        ),
        _write(tmp_path, "tests/test_cloudflare_incremental_certification.py", "def test_resume():\n    assert True\n"),
        _write(
            tmp_path,
            "main_review/cloudflare_cli.py",
            """def _proof_contract_matches(payload, model):
    candidates = [payload]
    for key in (\"required\", \"result\"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)

_SECURITY_COVERAGE_MARKERS = (\"security\", \"auth\", \"rce\")
def _coverage_area_matches(area):
    return any(marker in area for marker in _SECURITY_COVERAGE_MARKERS)
""",
        ),
        _write(
            tmp_path,
            "main_review/cloudflare_incremental_certification.py",
            """def _fresh_ledger():
    return {\"budget_blocked\": False, \"quota_blocked_day\": \"\"}
""",
        ),
        _write(
            tmp_path,
            "main_review/cloudflare_scout_qualification.py",
            """from pathlib import Path
def qualify(root, file):
    source = Path(root) / file
    return source.read_text()
""",
        ),
        _write(
            tmp_path,
            "main_review/cloudflare_usage.py",
            """import threading
_STATE_LOCK = threading.RLock()
def save(path):
    temporary = path.with_suffix(path.suffix + \".tmp\")
    temporary.write_text('{}')
    temporary.replace(path)
""",
        ),
        _write(
            tmp_path,
            "main_review/llm_provider.py",
            """import json
def is_cloudflare_quota_error(message):
    lowered = message.lower()
    return 'http 429' in lowered or '4006' in lowered

def _json_candidate_score(payload):
    return 10, len(json.dumps(payload))

def parse(objects):
    return max(objects, key=_json_candidate_score)
""",
        ),
    ]

    result = run_deterministic_officer_council(tmp_path, changed, {})

    assert result["model_required"] is False
    assert result["model_used"] is False
    assert result["verdict"] == "BLOCK"
    rules = {item["rule_id"] for item in result["findings"]}
    assert rules == {
        "proof-test-not-enforced",
        "pr-head-executes-with-provider-secrets",
        "exact-roster-not-enforced",
        "prompt-echo-can-pass-proof",
        "security-marker-substring-collision",
        "budget-block-never-expires",
        "scout-path-escapes-root",
        "usage-reservation-not-process-atomic",
        "transient-429-opens-daily-circuit",
        "verbose-json-beats-final-answer",
    }
    officers = {item["officer"] for item in result["officers"]}
    assert officers == {
        "Scout",
        "Quartermaster",
        "Engineer",
        "Medic",
        "Mechanic",
        "Analyst",
        "Challenger",
        "Judge",
        "Archivist",
    }


def test_clean_officer_council_still_challenges_high_risk_clean_verdict(tmp_path: Path) -> None:
    changed = [
        _write(
            tmp_path,
            "main_review/provider.py",
            """def normalize_status(status: str) -> str:
    return status.strip().lower()
""",
        )
    ]

    result = run_deterministic_officer_council(tmp_path, changed, {})

    assert result["findings"] == []
    assert result["verdict"] == "NEEDS WORK"
    assert result["unresolved_questions"]
    assert "explicit clean-proof explanation" in result["unresolved_questions"][0]


def test_clean_low_risk_change_can_pass_without_models(tmp_path: Path) -> None:
    changed = [_write(tmp_path, "src/formatting.py", "def title(value: str) -> str:\n    return value.title()\n")]

    result = run_deterministic_officer_council(tmp_path, changed, {})

    assert result["verdict"] == "PASS"
    assert result["findings"] == []
    assert result["unresolved_questions"] == []
    assert result["amplification"]["required_for_baseline"] is False
