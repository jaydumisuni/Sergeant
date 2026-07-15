from __future__ import annotations

from pathlib import Path

from main_review.capability_policy import normalize_capability_review


def test_workflow_embedded_python_is_not_promoted_to_taint_defect(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "proof.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        """name: Proof
jobs:
  verify:
    steps:
      - run: |
          python - <<'PY'
          import json
          from pathlib import Path
          payload = json.loads(Path('build/model-proof.json').read_text())
          request = payload.get('request')
          with Path('build/summary.json').open('w') as handle:
              json.dump(request, handle)
          PY
""",
        encoding="utf-8",
    )
    packet = {
        "verdict": "NEEDS WORK",
        "changed_files": [".github/workflows/proof.yml"],
        "findings": [
            {
                "capability": "data_flow",
                "severity": "major",
                "path": ".github/workflows/proof.yml",
                "message": "User-controlled input appears near a risky sink.",
                "evidence": "Input and sink patterns were both detected in the changed file.",
            },
            {
                "capability": "security_taint",
                "severity": "major",
                "path": ".github/workflows/proof.yml",
                "message": "Potential tainted input path needs validation review.",
                "evidence": "Input source and security-sensitive operation are both present.",
            },
        ],
    }

    normalized = normalize_capability_review(packet, tmp_path)

    assert normalized["verdict"] == "PASS"
    assert len(normalized["findings"]) == 2
    assert all(item["severity"] == "note" for item in normalized["findings"])
    assert all(item["configuration_signal"] is True for item in normalized["findings"])
    assert all(item["direct_evidence"] is False for item in normalized["findings"])
    assert len(normalized["policy_adjustments"]) == 2


def test_real_python_request_to_file_sink_remains_major(tmp_path: Path) -> None:
    source = tmp_path / "src" / "files.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        """def download(request):
    name = request.args.get('name')
    return open('/srv/files/' + name, 'rb')
""",
        encoding="utf-8",
    )
    packet = {
        "verdict": "PASS",
        "changed_files": ["src/files.py"],
        "findings": [],
    }

    normalized = normalize_capability_review(packet, tmp_path)

    assert normalized["verdict"] == "NEEDS WORK"
    majors = [item for item in normalized["findings"] if item["severity"] == "major"]
    assert {item["capability"] for item in majors} == {"data_flow", "security_taint"}
    assert all(item["root_cause"] == "unsafe-file-access" for item in majors)
