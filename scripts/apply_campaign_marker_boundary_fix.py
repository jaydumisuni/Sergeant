from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing patch anchor in {path}: {old!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once("main_review/cpl_campaign.py", "import math\n", "import math\nimport re\n")
replace_once(
    "main_review/cpl_campaign.py",
    "def _text(value: object) -> str:\n    return str(value or \"\").strip()\n\n\ndef _work_size",
    "def _text(value: object) -> str:\n    return str(value or \"\").strip()\n\n\ndef _contains_marker(text: str, marker: str) -> bool:\n    normalized = marker.lower()\n    if any(not char.isalnum() and char != \"_\" for char in normalized):\n        return normalized in text\n    return re.search(rf\"(?<![a-z0-9_]){re.escape(normalized)}(?![a-z0-9_])\", text) is not None\n\n\ndef _contains_any_marker(text: str, markers: Iterable[str]) -> bool:\n    return any(_contains_marker(text, marker) for marker in markers)\n\n\ndef _work_size",
)
replace_once(
    "main_review/cpl_campaign.py",
    "    if any(marker in text for marker in _SECURITY_MARKERS) or any(item.get(\"gates_verdict\") for item in assurances):\n",
    "    if _contains_any_marker(text, _SECURITY_MARKERS) or any(item.get(\"gates_verdict\") for item in assurances):\n",
)
replace_once(
    "main_review/cpl_campaign.py",
    "    if any(marker in text for marker in _RUNTIME_MARKERS):\n",
    "    if _contains_any_marker(text, _RUNTIME_MARKERS):\n",
)
replace_once(
    "main_review/cpl_campaign.py",
    "    requires_current_lookup = requires_current_lookup or any(marker in text for marker in _CONTRACT_MARKERS)\n",
    "    requires_current_lookup = requires_current_lookup or _contains_any_marker(text, _CONTRACT_MARKERS)\n",
)

path = ROOT / "tests" / "test_workspace_ready_campaign.py"
text = path.read_text(encoding="utf-8")
append = '''\n\ndef test_campaign_markers_do_not_match_unrelated_substrings(tmp_path: Path) -> None:\n    source = tmp_path / "src" / "authority.py"\n    source.parent.mkdir(parents=True)\n    source.write_text("def grant():\\n    return True\\n", encoding="utf-8")\n    campaign = build_cpl_campaign(\n        tmp_path,\n        ["src/authority.py", "src/streamlined.py", "src/rapid.py"],\n        officer_reports=[],\n        admitted=[],\n        advisory=[],\n        rejected=[],\n        assurances=[],\n        cpl={"status": "disabled", "passes": []},\n        offline={"complete": True},\n    )\n    officers = {item["responsible_officer"] for item in campaign["tasks"]}\n    assert "Medic" not in officers\n    assert "Mechanic" not in officers\n    assert campaign["research_requests"] == []\n\n\ndef test_campaign_markers_still_activate_on_real_terms(tmp_path: Path) -> None:\n    campaign = build_cpl_campaign(\n        tmp_path,\n        ["src/auth/token.py", "src/runtime/retry.py", "docs/api-contract.md"],\n        officer_reports=[],\n        admitted=[],\n        advisory=[],\n        rejected=[],\n        assurances=[],\n        cpl={"status": "disabled", "passes": []},\n        offline={"complete": True},\n    )\n    officers = {item["responsible_officer"] for item in campaign["tasks"]}\n    assert "Medic" in officers\n    assert "Mechanic" in officers\n    assert campaign["research_requests"]\n'''
if "test_campaign_markers_do_not_match_unrelated_substrings" not in text:
    path.write_text(text + append, encoding="utf-8")

(ROOT / "scripts" / "apply_campaign_marker_boundary_fix.py").unlink(missing_ok=True)
(ROOT / ".github" / "workflows" / "build-campaign-marker-boundary-fix.yml").unlink(missing_ok=True)
