from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise RuntimeError(f"{path}: expected one exact match for {old[:100]!r}")
    target.write_text(content.replace(old, new, 1), encoding="utf-8")


replace_once(
    "main_review/llm_provider.py",
    '''        policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "disabled").strip().lower()\n        policy: LLMPolicy = (\n            policy_raw if policy_raw in {"preferred", "required", "disabled"} else "disabled"\n        )  # type: ignore[assignment]\n        enabled_raw = _env("SERGEANT_CPL_ENABLED", "SERGEANT_LLM_ENABLED", "auto").strip().lower()\n        enabled = policy != "disabled" and enabled_raw not in {"0", "false", "no", "off", "disabled"}\n        provider = _normalize_provider(_env("SERGEANT_CPL_PROVIDER", "SERGEANT_LLM_PROVIDER", "auto"))\n        base_url = _env("SERGEANT_CPL_BASE_URL", "SERGEANT_LLM_BASE_URL", "").strip()\n        api_key = _env("SERGEANT_CPL_API_KEY", "SERGEANT_LLM_API_KEY", "").strip()\n        model = _env("SERGEANT_CPL_MODEL", "SERGEANT_LLM_MODEL", "").strip()\n''',
    '''        policy_value = os.getenv("SERGEANT_CPL_POLICY")\n        if policy_value is None:\n            policy_value = os.getenv("SERGEANT_LLM_POLICY")\n        enabled_raw = _env("SERGEANT_CPL_ENABLED", "SERGEANT_LLM_ENABLED", "auto").strip().lower()\n        provider = _normalize_provider(_env("SERGEANT_CPL_PROVIDER", "SERGEANT_LLM_PROVIDER", "auto"))\n        base_url = _env("SERGEANT_CPL_BASE_URL", "SERGEANT_LLM_BASE_URL", "").strip()\n        api_key = _env("SERGEANT_CPL_API_KEY", "SERGEANT_LLM_API_KEY", "").strip()\n        model = _env("SERGEANT_CPL_MODEL", "SERGEANT_LLM_MODEL", "").strip()\n        explicit_enable = enabled_raw in {"1", "true", "yes", "on", "enabled"}\n        explicit_route = provider not in {"auto", "disabled"} or bool(base_url)\n        policy_raw = (\n            policy_value if policy_value is not None else ("preferred" if explicit_enable or explicit_route else "disabled")\n        ).strip().lower()\n        policy: LLMPolicy = (\n            policy_raw if policy_raw in {"preferred", "required", "disabled"} else "disabled"\n        )  # type: ignore[assignment]\n        enabled = policy != "disabled" and enabled_raw not in {"0", "false", "no", "off", "disabled"}\n''',
)

replace_once(
    "tests/test_llm_cli.py",
    '    assert payload["cpl_review"]["policy"] == "preferred"',
    '    assert payload["cpl_review"]["policy"] == "disabled"',
)

replace_once(
    "tests/test_vscode_extension_package.py",
    '    assert "Cpl Council Reasoning" in command_center_js',
    '    assert "Optional Cpl Model Reasoning" in command_center_js',
)

visual = "tests/command-center-visual.spec.js"
replace_once(visual, "  await expect(page.locator('#providerSelect')).toHaveValue('auto');", "  await expect(page.locator('#providerSelect')).toHaveValue('disabled');")
replace_once(visual, "  await expect(page.locator('#llmPolicySelect')).toHaveValue('preferred');", "  await expect(page.locator('#llmPolicySelect')).toHaveValue('disabled');")
replace_once(visual, "  await expect(page.locator('#semanticRoute')).toContainText('Cpl · adaptive council · auto');", "  await expect(page.locator('#semanticRoute')).toContainText('Deterministic only');")
replace_once(
    visual,
    '''    policy: 'preferred',\n    provider: 'auto',\n    baseUrl: '',\n    model: '',\n    protocol: 'auto',\n    council: 'adaptive',\n    maxRounds: 2,\n    maxMembers: 5,''',
    '''    policy: 'disabled',\n    provider: 'disabled',\n    baseUrl: '',\n    model: '',\n    protocol: 'auto',\n    council: 'adaptive',\n    maxRounds: 2,\n    maxMembers: 5,''',
)
replace_once(
    visual,
    '''          policy: 'preferred',\n          provider: 'auto',\n          baseUrl: '',\n          model: '',\n          protocol: 'auto',\n          council: 'adaptive',\n          maxRounds: 2,\n          maxMembers: 5,''',
    '''          policy: 'disabled',\n          provider: 'disabled',\n          baseUrl: '',\n          model: '',\n          protocol: 'auto',\n          council: 'adaptive',\n          maxRounds: 2,\n          maxMembers: 5,''',
)
