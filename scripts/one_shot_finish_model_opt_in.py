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
        raise SystemExit(f"{path}: expected exactly one match, found {count}: {old[:140]!r}")
    write(path, text.replace(old, new, 1))


# Runtime: models are opt-in, not silently preferred merely because a local route exists.
replace_once(
    "main_review/llm_provider.py",
    'policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "preferred").strip().lower()',
    'policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "disabled").strip().lower()',
)
replace_once(
    "main_review/llm_provider.py",
    'policy_raw if policy_raw in {"preferred", "required", "disabled"} else "preferred"',
    'policy_raw if policy_raw in {"preferred", "required", "disabled"} else "disabled"',
)

# VS Code runtime and compact UI.
replace_once(
    "src/vscode/extension.js",
    'policy: configuration.get("llmPolicy") || "preferred",',
    'policy: configuration.get("llmPolicy") || "disabled",',
)
replace_once(
    "src/vscode/extension.js",
    'output.appendLine(`Cpl council: ${settings.policy} · ${settings.council} · ${settings.provider} · ${settings.model || "automatic model selection"} · ${settings.maxRounds} rounds · ${settings.maxMembers} members`);',
    'output.appendLine(settings.policy === "disabled" || settings.provider === "disabled"\n    ? "Sergeant mode: model-free Cpl/officer review"\n    : `Sergeant mode: model-free core + optional ${settings.council} model support · ${settings.provider} · ${settings.model || "provider selection"} · ${settings.maxRounds} rounds · ${settings.maxMembers} members`);',
)
replace_once(
    "src/vscode/command-center.js",
    '<div class="panel"><b>Cpl — Council Command</b><p class="muted">Elastic model council, permanent-officer support, verified experience, and repeated evidence rebriefs.</p></div>',
    '<div class="panel"><b>Cpl — Model-Free Review Command</b><p class="muted">Permanent-officer and private review, verified experience, repeated evidence rebriefs, and optional model support only when enabled.</p></div>',
)
replace_once(
    "src/vscode/command-center.js",
    'Open the full Command Center for council limits, officers, armoury, model selection, and permissions.',
    'Open the full Command Center for officers, armoury, permissions, and optional model-support settings.',
)
replace_once(
    "src/vscode/command-center.js",
    'Run deterministic evidence and Cpl council reasoning',
    'Run model-free Sergeant evidence and Cpl/officer reasoning',
)

# VS Code manifest: preserve stable setting IDs and legacy value, but make model-free opt-in the default and visible meaning.
replace_once("package.json", '"default": "Cpl Automatic Reasoning",', '"default": "Model-Free Sergeant Core",')
replace_once(
    "package.json",
    '"enum": [\n            "Cpl Automatic Reasoning",',
    '"enum": [\n            "Model-Free Sergeant Core",\n            "Cpl Optional Model Reasoning",\n            "Cpl Automatic Reasoning",',
)
replace_once(
    "package.json",
    '"description": "Legacy display preference. Cpl is Sergeant\'s council-led Corporal Specialist; models and gateways are replaceable engines beneath it."',
    '"description": "Legacy display preference. Sergeant defaults to its model-free Cpl/officer core; model routes are optional extra reasoning only. The previous Cpl Automatic Reasoning value remains accepted for compatibility."',
)
replace_once("package.json", '"default": "preferred",', '"default": "disabled",')
replace_once(
    "package.json",
    '"Deploy Cpl by default and fall back to deterministic Sergeant evidence when no route is available.",\n            "Require Cpl reasoning before Sergeant can approve.",\n            "Disable Cpl reasoning and use deterministic review only."',
    '"Keep model-free Cpl/officer review active and add optional model reasoning when a valid route is available.",\n            "For an owner-selected strict mission, require the configured optional model-reasoning route before approval.",\n            "Disable model calls while keeping Cpl, permanent officers, privates, and deterministic Sergeant review active."',
)
replace_once(
    "package.json",
    '"description": "Cpl reasoning gate policy."',
    '"description": "Optional model-reasoning gate policy; Cpl and the officer/private system remain model-free."',
)
replace_once(
    "package.json",
    '"Let Cpl discover its local gateway, Ollama, or LM Studio and select the strongest available models.",\n            "Use the Sergeant-native Cpl local gateway.",\n            "Use Ollama as one engine beneath Cpl.",\n            "Use LM Studio as one engine beneath Cpl.",\n            "Use the explicitly configured endpoint as one engine beneath Cpl.",\n            "Disable Cpl reasoning."',
    '"Optionally use a valid loopback Cpl, Ollama, or LM Studio route; otherwise continue with the model-free core.",\n            "Use the Cpl local gateway as an optional model-reasoning route.",\n            "Use Ollama as an optional reasoning engine beneath Cpl.",\n            "Use LM Studio as an optional reasoning engine beneath Cpl.",\n            "Use the explicitly configured endpoint as an optional reasoning engine beneath Cpl.",\n            "Disable optional model reasoning and keep model-free Cpl/officer review."',
)
replace_once(
    "package.json",
    '"description": "Engine route beneath Cpl."',
    '"description": "Optional model engine route beneath the model-free Cpl/officer core."',
)
replace_once(
    "package.json",
    '"description": "Explicit OpenAI-compatible endpoint beneath Cpl. Remote endpoints are never auto-discovered; credentials remain in SERGEANT_CPL_API_KEY or the legacy SERGEANT_LLM_API_KEY."',
    '"description": "Optional explicit OpenAI-compatible endpoint beneath Cpl. Remote endpoints are never auto-discovered; credentials remain in SERGEANT_CPL_API_KEY or the legacy SERGEANT_LLM_API_KEY."',
)
replace_once(
    "package.json",
    '"description": "Optional primary model slug. Blank lets Cpl form its council from the strongest available models and specialist assignments."',
    '"description": "Optional model slug for extra reasoning. Blank leaves route selection to the configured provider; model-free review does not require a model."',
)
replace_once(
    "package.json",
    '"description": "Transport protocol beneath Cpl. The local Cpl gateway uses OpenAI Responses; generic engines commonly use Chat Completions."',
    '"description": "Transport protocol for optional model reasoning. The local Cpl gateway uses OpenAI Responses; generic engines commonly use Chat Completions."',
)
replace_once(
    "package.json",
    '"Cpl deploys the smallest sufficient council and adds members only for named evidence gaps.",\n            "Cpl starts with deeper specialist coverage and allows more council rounds.",\n            "Cpl deploys every specialist and the largest bounded council.",\n            "Run one Cpl generalist council member only.",\n            "Legacy alias for maximum council deployment."',
    '"When optional model support is enabled, use the smallest sufficient roster and add members only for named evidence gaps.",\n            "Use deeper optional model coverage and allow more bounded follow-up rounds.",\n            "Use the largest bounded optional model-support roster.",\n            "Use one optional general model pass only.",\n            "Legacy alias for maximum optional model-support deployment."',
)
replace_once(
    "package.json",
    '"description": "Cpl council formation mode."',
    '"description": "Optional model-support formation mode; it does not define Sergeant\'s permanent officer/private formation."',
)
replace_once(
    "package.json",
    '"description": "Maximum evidence → officer report → council rebrief rounds before unresolved gaps are returned to Sergeant."',
    '"description": "Maximum optional model-support rebrief rounds before unresolved gaps are returned to Sergeant."',
)
replace_once(
    "package.json",
    '"description": "Maximum distinct model council members Cpl may recruit for one mission."',
    '"description": "Maximum distinct optional model-support members Cpl may recruit for one mission."',
)

# Shared Command Center defaults and remaining visible wording.
replace_once("resources/sergeant-command-center-v2.js", "policy: 'preferred',", "policy: 'disabled',")
replace_once(
    "resources/sergeant-command-center-v2.html",
    '<option value="preferred">Optional models when available; model-free fallback</option><option value="required">Optional strict gate — require configured model support</option><option value="disabled">Model-free only — no model calls</option>',
    '<option value="preferred">Optional models when available; model-free fallback</option><option value="required">Optional strict gate — require configured model support</option><option value="disabled" selected>Model-free only — no model calls</option>',
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    "<span>Cpl Reasoning Evidence</span>",
    "<span>Cpl / Officer Evidence</span>",
)

# JetBrains defaults and user-visible status.
replace_once(
    "adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt",
    'sendState("Cpl reasoning settings saved.")',
    'sendState("Optional model-reasoning settings saved; model-free Cpl/officer review remains active.")',
)
replace_once(
    "adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt",
    '"policy" to "preferred",',
    '"policy" to "disabled",',
)
replace_once(
    "adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt",
    'Native fallback is ready to run deterministic review and Cpl specialist reasoning for ${project.name}.',
    'Native fallback is ready to run model-free Sergeant review and Cpl/officer reasoning for ${project.name}; model support is optional.',
)
replace_once(
    "adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt",
    'Running Sergeant deterministic review and Cpl specialist reasoning…',
    'Running Sergeant model-free review and Cpl/officer reasoning…',
)

# Submission and public proof wording.
replace_once(
    "SUBMISSION_READY.md",
    "- [x] Cpl council and verified experience",
    "- [x] Model-free Cpl/officer review and verified experience; optional model support available",
)
replace_once(
    "SUBMISSION_READY.md",
    "Sergeant is an evidence-based engineering reviewer with CLI review, App Bridge handoff, IDE Bench contracts, battle-test benchmarks, Cpl council reasoning, CI proof, clean-clone proof, production hardening, and release proof.",
    "Sergeant is a model-free evidence-based engineering reviewer with CLI review, App Bridge handoff, IDE Bench contracts, battle-test benchmarks, Cpl/officer reasoning, CI proof, clean-clone proof, production hardening, and release proof; users may optionally enable model reasoning for extra analysis.",
)
replace_once(
    "docs/submission-proof.md",
    "- [x] Cpl council and verified experience",
    "- [x] Model-free Cpl/officer review and verified experience; optional model support available",
)
replace_once(
    "docs/submission-proof.md",
    "Sergeant supports production-hardened live GitHub read-only fetch, CLI review, App Bridge review handoff, IDE Bench contracts, battle-test benchmarks, Cpl council reasoning, CI proof, clean-clone proof, and release proof.",
    "Sergeant is a model-free reviewer supporting production-hardened live GitHub read-only fetch, CLI review, App Bridge review handoff, IDE Bench contracts, battle-test benchmarks, Cpl/officer reasoning, CI proof, clean-clone proof, and release proof; optional configured models may add extra reasoning.",
)

# Runtime/default tests and public-surface regressions.
replace_once(
    "tests/test_llm_provider.py",
    "def test_cpl_settings_are_enabled_by_default_but_do_not_expose_api_key(monkeypatch) -> None:\n    monkeypatch.setenv(\"SERGEANT_CPL_API_KEY\", \"secret-value\")\n    monkeypatch.setenv(\"SERGEANT_CPL_ENABLED\", \"auto\")\n    monkeypatch.setenv(\"SERGEANT_CPL_POLICY\", \"preferred\")\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is True\n    assert settings.policy == \"preferred\"\n    assert settings.public_dict()[\"officer\"] == \"Cpl\"\n    assert settings.public_dict()[\"role\"] == \"Corporal Specialist\"\n    assert \"api_key\" not in settings.public_dict()\n    assert \"secret-value\" not in str(settings.public_dict())",
    "def test_cpl_settings_are_model_free_by_default_and_do_not_expose_api_key(monkeypatch) -> None:\n    monkeypatch.setenv(\"SERGEANT_CPL_API_KEY\", \"secret-value\")\n    for name in (\"SERGEANT_CPL_ENABLED\", \"SERGEANT_CPL_POLICY\", \"SERGEANT_LLM_ENABLED\", \"SERGEANT_LLM_POLICY\"):\n        monkeypatch.delenv(name, raising=False)\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is False\n    assert settings.policy == \"disabled\"\n    assert settings.public_dict()[\"officer\"] == \"Cpl\"\n    assert settings.public_dict()[\"role\"] == \"Corporal Specialist\"\n    assert \"api_key\" not in settings.public_dict()\n    assert \"secret-value\" not in str(settings.public_dict())\n\n\ndef test_owner_can_explicitly_enable_optional_model_reasoning(monkeypatch) -> None:\n    monkeypatch.setenv(\"SERGEANT_CPL_ENABLED\", \"true\")\n    monkeypatch.setenv(\"SERGEANT_CPL_POLICY\", \"preferred\")\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is True\n    assert settings.policy == \"preferred\"",
)
replace_once(
    "tests/test_vscode_extension_package.py",
    'assert properties["sergeant.provider"]["default"] == "Cpl Automatic Reasoning"\n    assert properties["sergeant.llmPolicy"]["default"] == "preferred"',
    'assert properties["sergeant.provider"]["default"] == "Model-Free Sergeant Core"\n    assert "Cpl Automatic Reasoning" in properties["sergeant.provider"]["enum"]\n    assert properties["sergeant.llmPolicy"]["default"] == "disabled"',
)
replace_once(
    "tests/test_vscode_extension_package.py",
    '"Cpl — Corporal Specialist",',
    '"Cpl — Model-Free Core / Optional Model Support",',
)
replace_once(
    "tests/test_vscode_extension_package.py",
    '"Cpl Reasoning Evidence",',
    '"Cpl / Officer Evidence",',
)
replace_once(
    "tests/test_vscode_extension_package.py",
    'assert "Cpl Council Reasoning" in command_center_js',
    'assert "Cpl Officer Reasoning" in command_center_js\n    assert "Optional Model Assistance" in command_center_js',
)
replace_once(
    "tests/test_vscode_extension_package.py",
    'assert "Council Command" in command_center_js',
    'assert "Model-Free Command" in command_center_js',
)

identity = read("tests/test_model_free_product_identity.py")
identity = identity.replace(
    '    provider = text("main_review/llm_provider.py")\n    assert \'LLMPolicy = Literal["preferred", "required", "disabled"]\' in provider\n    assert "Automatic discovery probes loopback endpoints only" in provider',
    '    provider = text("main_review/llm_provider.py")\n    assert \'LLMPolicy = Literal["preferred", "required", "disabled"]\' in provider\n    assert \'"SERGEANT_LLM_POLICY", "disabled"\' in provider\n    assert "Automatic discovery probes loopback endpoints only" in provider\n    package = __import__("json").loads(text("package.json"))\n    properties = package["contributes"]["configuration"]["properties"]\n    assert properties["sergeant.llmPolicy"]["default"] == "disabled"\n    assert properties["sergeant.provider"]["default"] == "Model-Free Sergeant Core"',
)
if identity == read("tests/test_model_free_product_identity.py"):
    raise SystemExit("tests/test_model_free_product_identity.py: runtime assertion marker not found")
write("tests/test_model_free_product_identity.py", identity)

# Remove one-shot machinery before the final correction commit.
(ROOT / ".github/workflows/one-shot-finish-model-opt-in.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)
print("Finished model-free defaults and corrected remaining public surfaces.")
