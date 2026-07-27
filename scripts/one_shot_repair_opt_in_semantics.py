from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text.rstrip() + "\n", encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:160]!r}")
    write(path, text.replace(old, new, 1))


replace_once(
    "main_review/llm_provider.py",
    '''        policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "disabled").strip().lower()
        policy: LLMPolicy = (
            policy_raw if policy_raw in {"preferred", "required", "disabled"} else "disabled"
        )  # type: ignore[assignment]
        enabled_raw = _env("SERGEANT_CPL_ENABLED", "SERGEANT_LLM_ENABLED", "auto").strip().lower()
        enabled = policy != "disabled" and enabled_raw not in {"0", "false", "no", "off", "disabled"}
''',
    '''        policy_names = ("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY")
        enabled_names = ("SERGEANT_CPL_ENABLED", "SERGEANT_LLM_ENABLED")
        policy_explicit = any(os.environ.get(name, "").strip() for name in policy_names)
        enabled_explicit = any(os.environ.get(name, "").strip() for name in enabled_names)
        policy_raw = _env(*policy_names, "disabled").strip().lower()
        enabled_raw = _env(*enabled_names, "auto").strip().lower()

        # The shipped state is model-free. An explicit legacy/CLI enable flag is
        # still a deliberate opt-in and therefore selects the compatibility
        # `preferred` policy unless the owner explicitly supplied a policy.
        if (
            not policy_explicit
            and enabled_explicit
            and enabled_raw in {"1", "true", "yes", "on", "enabled"}
        ):
            policy_raw = "preferred"

        policy: LLMPolicy = (
            policy_raw if policy_raw in {"preferred", "required", "disabled"} else "disabled"
        )  # type: ignore[assignment]
        enabled = policy != "disabled" and enabled_raw not in {"0", "false", "no", "off", "disabled"}
''',
)

replace_once(
    "tests/test_llm_cli.py",
    '    assert payload["cpl_review"]["policy"] == "preferred"',
    '    assert payload["cpl_review"]["policy"] == "disabled"',
)
replace_once(
    "tests/test_jetbrains_command_center.py",
    '    assert "Cpl reasoning settings saved." in tool_window',
    '    assert "Optional model-reasoning settings saved" in tool_window',
)
replace_once(
    "tests/test_jetbrains_command_center.py",
    '    assert "deterministic review and Cpl specialist reasoning" in tool_window',
    '    assert "model-free Sergeant review and Cpl/officer reasoning" in tool_window',
)
replace_once(
    "tests/test_model_free_product_identity.py",
    '        "does not require",',
    '        "does **not** require",',
)

# Bind the explicit opt-in compatibility behavior so default-off does not break
# users who deliberately set SERGEANT_CPL_ENABLED=true.
provider_tests = read("tests/test_llm_provider.py")
marker = '''def test_owner_can_explicitly_enable_optional_model_reasoning(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "true")
    monkeypatch.setenv("SERGEANT_CPL_POLICY", "preferred")

    settings = LLMSettings.from_environment()

    assert settings.enabled is True
    assert settings.policy == "preferred"
'''
replacement = '''def test_owner_can_explicitly_enable_optional_model_reasoning(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "true")
    monkeypatch.setenv("SERGEANT_CPL_POLICY", "preferred")

    settings = LLMSettings.from_environment()

    assert settings.enabled is True
    assert settings.policy == "preferred"


def test_explicit_enable_flag_is_a_compatible_opt_in_without_policy(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "true")
    monkeypatch.delenv("SERGEANT_CPL_POLICY", raising=False)
    monkeypatch.delenv("SERGEANT_LLM_POLICY", raising=False)

    settings = LLMSettings.from_environment()

    assert settings.enabled is True
    assert settings.policy == "preferred"
'''
if provider_tests.count(marker) != 1:
    raise SystemExit("tests/test_llm_provider.py: explicit opt-in marker missing")
write("tests/test_llm_provider.py", provider_tests.replace(marker, replacement, 1))

(ROOT / ".github/workflows/one-shot-repair-opt-in-semantics.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)
print("Repaired explicit model opt-in semantics and aligned regression expectations.")
