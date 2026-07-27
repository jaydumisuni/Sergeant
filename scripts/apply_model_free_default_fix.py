from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    content = read(path)
    actual = content.count(old)
    if actual != count:
        raise SystemExit(f"{path}: expected {count} occurrence(s), found {actual}: {old!r}")
    write(path, content.replace(old, new))


# Core runtime: no model route is enabled unless the user explicitly opts in.
replace(
    "main_review/llm_provider.py",
    'policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "preferred").strip().lower()',
    'policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "disabled").strip().lower()',
)
replace(
    "main_review/llm_provider.py",
    'policy_raw if policy_raw in {"preferred", "required", "disabled"} else "preferred"',
    'policy_raw if policy_raw in {"preferred", "required", "disabled"} else "disabled"',
)

# VS Code package defaults and descriptions.
package = json.loads(read("package.json"))
properties = package["contributes"]["configuration"]["properties"]
properties["sergeant.provider"]["default"] = "Disabled"
properties["sergeant.provider"]["description"] = (
    "Legacy display preference. Sergeant runs model-free by default; Cpl can use optional model engines only when the user enables extra reasoning."
)
properties["sergeant.llmPolicy"]["default"] = "disabled"
properties["sergeant.llmPolicy"]["enumDescriptions"] = [
    "Enable optional Cpl model support and fall back to Sergeant's model-free officer formation when no route is available.",
    "Require optional model support before Sergeant can approve this explicitly configured gate.",
    "Use Sergeant's standard model-free Cpl and permanent-officer review.",
]
properties["sergeant.llmPolicy"]["description"] = "Optional model-support gate beneath Sergeant's model-free review system."
properties["sergeant.llmProvider"]["default"] = "disabled"
properties["sergeant.llmProvider"]["enumDescriptions"] = [
    "When model support is enabled, let Cpl discover a loopback gateway, Ollama, or LM Studio.",
    "Use the Sergeant-native Cpl local gateway as optional extra reasoning.",
    "Use Ollama as an optional engine beneath Cpl.",
    "Use LM Studio as an optional engine beneath Cpl.",
    "Use an explicitly configured endpoint as optional extra reasoning beneath Cpl.",
    "Keep Sergeant model-free.",
]
properties["sergeant.llmProvider"]["description"] = "Optional model engine route beneath Cpl; disabled by default."
properties["sergeant.llmModel"]["description"] = (
    "Optional primary model slug used only after model support is enabled. Blank lets Cpl choose from explicitly available engines."
)
write("package.json", json.dumps(package, indent=2) + "\n")

# VS Code runtime defaults.
replace("src/vscode/extension.js", 'policy: configuration.get("llmPolicy") || "preferred",', 'policy: configuration.get("llmPolicy") || "disabled",')
replace("src/vscode/extension.js", 'provider: configuration.get("llmProvider") || "auto",', 'provider: configuration.get("llmProvider") || "disabled",')
replace(
    "src/vscode/extension.js",
    'output.appendLine(`Cpl council: ${settings.policy} · ${settings.council} · ${settings.provider} · ${settings.model || "automatic model selection"} · ${settings.maxRounds} rounds · ${settings.maxMembers} members`);',
    'output.appendLine(`Sergeant review: model-free permanent officers${settings.policy === "disabled" || settings.provider === "disabled" ? "" : ` · optional Cpl model support ${settings.policy} · ${settings.council} · ${settings.provider} · ${settings.model || "automatic model selection"} · ${settings.maxRounds} rounds · ${settings.maxMembers} members`}`);',
)

# JetBrains defaults.
replace("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantRunner.kt", 'val policy = properties.getValue("sergeant.llm.policy") ?: "preferred"', 'val policy = properties.getValue("sergeant.llm.policy") ?: "disabled"')
replace("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantRunner.kt", 'val provider = properties.getValue("sergeant.llm.provider") ?: "auto"', 'val provider = properties.getValue("sergeant.llm.provider") ?: "disabled"')
replace("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt", '"policy" to "preferred",', '"policy" to "disabled",')
replace("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt", '"provider" to "auto",', '"provider" to "disabled",')
replace("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt", 'sendState("Cpl reasoning settings saved.")', 'sendState("Optional model-support settings saved.")')

# Command Center defaults and visible product wording.
replace("resources/sergeant-command-center-v2.js", "['Quartermaster', 'Models + weapons + loadout']", "['Quartermaster', 'Optional models + weapons + loadout']")
replace("resources/sergeant-command-center-v2.js", "'Cpl Council Reasoning',", "'Cpl / Officer Reasoning',")
replace("resources/sergeant-command-center-v2.js", "policy: 'preferred',", "policy: 'disabled',")
replace("resources/sergeant-command-center-v2.js", "provider: 'auto',", "provider: 'disabled',")
replace("resources/sergeant-command-center-v2.js", "const labels = ['Mission Started', 'Evidence Collected', 'Cpl Council', 'Officer Rebrief', 'Commander Report'];", "const labels = ['Mission Started', 'Evidence Collected', 'Officer Council', 'Officer Rebrief', 'Commander Report'];")
replace("resources/sergeant-command-center-v2.js", "const model = settings.model || 'best available models';", "const model = settings.model || 'optional model not selected';")
replace("resources/sergeant-command-center-v2.js", "if (settings.policy === 'disabled' || provider === 'disabled') return 'Deterministic only';", "if (settings.policy === 'disabled' || provider === 'disabled') return 'Model-free Sergeant · Cpl + permanent officers';")
replace("resources/sergeant-command-center-v2.js", "['Council Grounding', 94],", "['Officer Grounding', 94],")
replace("resources/sergeant-command-center-v2.js", "['Model Independence', 88],", "['Evidence Independence', 88],")
replace(
    "resources/sergeant-command-center-v2.js",
    "['Council Command', 'Cpl tables officer reports before multiple model members, recruits only for named gaps and repeats within strict round and member limits.'],",
    "['Council Command', 'Cpl tables permanent-officer reports first. Optional model members may be recruited only after the user enables extra reasoning and a named evidence gap justifies them.'],",
)
replace(
    "resources/sergeant-command-center-v2.js",
    "['Bounded Growth', 'Cpl forms the smallest sufficient council and adds another model only when a missing capability is named.'],",
    "['Bounded Growth', 'The model-free officer formation is standard. Optional model support stays bounded and adds an engine only when a named gap justifies it.'],",
)
replace("resources/sergeant-command-center-v2.js", "`Policy: ${state.settings.policy || 'preferred'}`", "`Policy: ${state.settings.policy || 'disabled'}`")
replace("resources/sergeant-command-center-v2.js", "`Engine route: ${state.settings.provider || 'auto'}`", "`Engine route: ${state.settings.provider || 'disabled'}`")
replace("resources/sergeant-command-center-v2.js", "`Primary model: ${state.settings.model || 'Cpl automatic council formation'}`", "`Primary model: ${state.settings.model || 'not enabled — model-free review'}`")
replace("resources/sergeant-command-center-v2.js", "battle: ['Battle comparison', 'UI proof checks', 'Regression baseline', 'Officer/model/weapon outcomes'],", "battle: ['Battle comparison', 'UI proof checks', 'Regression baseline', 'Officer/evidence/optional-model outcomes'],")

replace("resources/sergeant-command-center-v2.html", '<strong>SERGEANT</strong><small>AI CODE REVIEWER</small>', '<strong>SERGEANT</strong><small>ENGINEERING REVIEWER</small>')
replace("resources/sergeant-command-center-v2.html", '<label class="selected"><input type="radio" name="level" value="Repository Review" checked>Repository Review<small>Full deterministic and Cpl workspace review.</small></label>', '<label class="selected"><input type="radio" name="level" value="Repository Review" checked>Repository Review<small>Full model-free Cpl and permanent-officer workspace review.</small></label>')
replace("resources/sergeant-command-center-v2.html", '<label><input type="checkbox" checked>Cpl Specialist Reasoning</label>', '<label><input type="checkbox" checked>Model-free Cpl / Officer Reasoning</label>')
replace(
    "resources/sergeant-command-center-v2.html",
    '<label>Policy<select id="llmPolicySelect"><option value="preferred">Preferred — Cpl with deterministic fallback</option><option value="required">Required — no approval without Cpl</option><option value="disabled">Disabled — deterministic only</option></select></label>',
    '<label>Optional Model Support<select id="llmPolicySelect"><option value="disabled" selected>Off — model-free Sergeant (default)</option><option value="preferred">On — extra Cpl reasoning with model-free fallback</option><option value="required">Required — explicit model-assisted gate</option></select></label>',
)
replace(
    "resources/sergeant-command-center-v2.html",
    '<label>Engine Route<select id="providerSelect"><option value="auto">Automatic — Cpl, Ollama, LM Studio</option><option value="cpl">Cpl Local Gateway</option><option value="ollama">Ollama</option><option value="lm-studio">LM Studio</option><option value="openai-compatible">OpenAI-compatible endpoint</option><option value="disabled">Disabled</option></select></label>',
    '<label>Optional Engine Route<select id="providerSelect"><option value="disabled" selected>Disabled — model-free review</option><option value="auto">Automatic — loopback engines only</option><option value="cpl">Cpl Local Gateway</option><option value="ollama">Ollama</option><option value="lm-studio">LM Studio</option><option value="openai-compatible">OpenAI-compatible endpoint</option></select></label>',
)
replace("resources/sergeant-command-center-v2.html", '<label>Model<input id="llmModelInput" placeholder="Automatic: GLM-5.2 → Qwen3-Coder-Next → Kimi K2.5"></label>', '<label>Optional Model<input id="llmModelInput" placeholder="Used only when extra model reasoning is enabled"></label>')
replace(
    "resources/sergeant-command-center-v2.html",
    '<p class="muted">Cpl is Sergeant\'s native reasoning officer. Models and gateways are replaceable engines beneath it. Automatic discovery is loopback-only. Remote code leaves the machine only when you explicitly set a remote Base URL. Credentials stay in <code>SERGEANT_CPL_API_KEY</code> and are never stored in this webview.</p>',
    '<p class="muted">Sergeant runs model-free by default through Cpl, permanent officers, privates, deterministic evidence, tools, scanners and verified experience. Models are optional extra reasoning engines only when you enable them. Automatic discovery is loopback-only. Remote code leaves the machine only when you explicitly set a remote Base URL. Credentials stay in <code>SERGEANT_CPL_API_KEY</code> and are never stored in this webview.</p>',
)
replace("resources/sergeant-command-center-v2.html", '<div class="row"><span>Cpl Reasoning</span><b class="pass">ROUTED</b></div>', '<div class="row"><span>Cpl / Officer Reasoning</span><b class="pass">ACTIVE</b></div>')
replace("resources/sergeant-command-center-v2.html", '<p class="muted">Static, runtime, Cpl, UI, documentation, battle and external evidence.</p>', '<p class="muted">Static, runtime, model-free officer, optional model, UI, documentation, battle and external evidence.</p>')
replace("resources/sergeant-command-center-v2.html", '<p class="muted"><b>Evidence first. Verdict second. Nothing is assumed.</b> Sergeant gathers comparable evidence, Cpl reasons over it, and the Commander decides from verified facts.</p>', '<p class="muted"><b>Evidence first. Verdict second. Nothing is assumed.</b> Sergeant gathers comparable evidence, Cpl and the permanent officers reason model-free by default, optional models may add extra evidence, and the Commander decides from verified facts.</p>')
replace("resources/sergeant-command-center-v2.html", '<li>Compare Cpl specialists, independent models and external reviewers</li>', '<li>Compare model-free officers, optional independent models and external reviewers</li>')

# README: present model-free review as the product and multi-model as opt-in amplification.
replace(
    "README.md",
    "**Sergeant Main Review is the reviewer core. Cpl — Corporal Specialist — is Sergeant's native reasoning officer.** Models and gateways are replaceable engines beneath Cpl, not the product identity and not the architectural ceiling.",
    "**Sergeant Main Review is the reviewer core. Cpl — Corporal Specialist — is Sergeant's native reasoning officer.** Sergeant operates model-free by default through permanent officers, privates, deterministic evidence, tools, scanners, and verified experience. Models and gateways are optional replaceable engines beneath Cpl when the user enables extra reasoning; they are not the product identity, a requirement, or the architectural ceiling.",
)
replace(
    "README.md",
    "### Cpl policies\n\n**Preferred** is the product default:\n\n- deploy Cpl when a route is available;\n- keep Cpl's deterministic permanent-officer formation active when a model route is not available;\n- state clearly in the report whether Cpl ran.\n\n**Required** is the strict release gate:\n\n- no approval when the Cpl route is unavailable or fails;\n- all required deterministic and Cpl evidence must complete.\n\n**Disabled** runs deterministic review only.",
    "### Optional model-support policies\n\n**Disabled** is the product default:\n\n- run Sergeant model-free through Cpl, permanent officers, privates, deterministic evidence, tools, scanners, and verified experience;\n- do not discover or call a model endpoint;\n- preserve the same Sergeant authority, evidence, learning, and proof gates.\n\n**Preferred** is an owner-enabled extra-reasoning mode:\n\n- use optional models when an explicitly allowed route is available;\n- fall back to the complete model-free officer formation when the route is unavailable;\n- state clearly in the report whether model support ran.\n\n**Required** is an explicitly configured model-assisted gate:\n\n- no approval when the requested model route is unavailable or fails;\n- deterministic, officer, and configured model evidence must complete.",
)
replace("README.md", "- Adaptive multi-specialist and multi-model review.", "- Adaptive model-free multi-specialist review, with optional multi-model amplification when the user enables it.")
replace("README.md", "### Complete independent review\n\n```bash\nsergeant pr-review . --pretty\n```", "### Complete independent review — model-free by default\n\n```bash\nsergeant pr-review . --pretty\n```\n\nThis runs Cpl, the permanent officers, privates, deterministic evidence, tools, scanners, verified lessons, challenge, adjudication, and the Commander verdict without requiring a model login or GPU.")
replace("README.md", "export SERGEANT_CPL_PROVIDER=ollama\nexport SERGEANT_CPL_MODEL=qwen3-coder-next", "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=ollama\nexport SERGEANT_CPL_MODEL=qwen3-coder-next")
replace("README.md", "export SERGEANT_CPL_PROVIDER=lm-studio\nsergeant pr-review", "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=lm-studio\nsergeant pr-review")
replace("README.md", "export SERGEANT_CPL_PROVIDER=configured\nexport SERGEANT_CPL_BASE_URL", "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=configured\nexport SERGEANT_CPL_BASE_URL")
replace("README.md", "The earlier `SERGEANT_LLM_*` variables and `llm-status` command remain accepted as compatibility aliases for 0.4.0 integrations. New configuration should use Cpl naming.", "The default is `SERGEANT_CPL_POLICY=disabled`: Sergeant remains fully model-free unless the user explicitly enables optional model support. The earlier `SERGEANT_LLM_*` variables and `llm-status` command remain accepted as compatibility aliases for 0.4.0 integrations. New configuration should use Cpl naming.")

# Canonical Cpl documentation.
replace(
    "docs/22-semantic-open-model-review.md",
    "Cpl is Sergeant's native reasoning officer. It is not the name of a model, provider, proxy, or borrowed repository. Cpl sits under Sergeant Main Review and uses replaceable model engines to perform evidence-grounded specialist reasoning.",
    "Cpl is Sergeant's native reasoning officer. It is not the name of a model, provider, proxy, or borrowed repository. Cpl sits under Sergeant Main Review and coordinates the permanent-officer and private formation model-free by default. Replaceable model engines are optional extra reasoning support only when the user enables them.",
)
replace(
    "docs/22-semantic-open-model-review.md",
    "1. receives changed-file scope and deterministic Sergeant evidence;\n2. performs a general reasoning pass;\n3. deterministically selects specialist missions based on risk and repository context;\n4. assigns models to specialists, rotating available engines where useful;\n5. rejects unsupported or out-of-scope findings;\n6. merges supported findings by path, line range, model, and specialist;\n7. returns auditable evidence to Sergeant consensus.",
    "1. receives changed-file scope and deterministic Sergeant evidence;\n2. coordinates Cpl, permanent officers, and private evidence obligations without requiring a model;\n3. deterministically selects specialist missions based on risk and repository context;\n4. optionally assigns user-enabled model engines to a named specialist question when extra reasoning is justified;\n5. rejects unsupported or out-of-scope findings;\n6. merges supported findings by path, line range, evidence source, officer, and optional model provenance;\n7. returns auditable evidence to Sergeant consensus.",
)
replace(
    "docs/22-semantic-open-model-review.md",
    "This makes model selection only one part of Cpl. Better reasoning can come from stronger models, better decomposition, better context, specialist disagreement, stronger grounding, improved repository intelligence, and better verification loops.",
    "Models are not required for Cpl to operate. Better reasoning first comes from permanent doctrine, tenfold decomposition, verified experience, deterministic evidence, specialist disagreement, stronger grounding, repository intelligence, and verification loops. Optional models can add another reasoning source after the user enables them.",
)
replace(
    "docs/22-semantic-open-model-review.md",
    "## Model policy\n\nWhen an endpoint exposes multiple models and no model is pinned, Cpl currently prefers:",
    "## Optional model policy\n\nSergeant does not call models by default. After the user explicitly enables model support, and an allowed endpoint exposes multiple models with no pinned model, Cpl currently prefers:",
)
replace(
    "docs/22-semantic-open-model-review.md",
    "### Preferred\n\nDefault mode.\n\n- Deploy Cpl when a route is available.\n- Keep deterministic Sergeant evidence authoritative.\n- Fall back to deterministic review when the route is unavailable.\n- State clearly in the report that Cpl did not run.\n\n### Required\n\nStrict release-gate mode.\n\n- Cpl must complete before Sergeant can approve.\n- An unavailable or failed route becomes a required action.\n- Useful when both deterministic and reasoning proof are mandatory.\n\n### Disabled\n\n- Do not discover or call model endpoints.\n- Run deterministic Sergeant review only.",
    "### Disabled\n\nDefault mode.\n\n- Do not discover or call model endpoints.\n- Run the complete model-free Sergeant formation: Cpl, permanent officers, privates, deterministic evidence, tools, scanners, verified experience, challenge, Judge ledger, and Commander verdict.\n\n### Preferred\n\nOwner-enabled extra-reasoning mode.\n\n- Use optional model support when an allowed route is available.\n- Keep model-free Sergeant evidence authoritative.\n- Fall back to the complete model-free officer formation when the route is unavailable.\n- State clearly in the report that model support did not run.\n\n### Required\n\nExplicit model-assisted release-gate mode.\n\n- The configured model-support route must complete before Sergeant can approve.\n- An unavailable or failed route becomes a required action.\n- Useful only when the owner intentionally requires both model-free and model-assisted proof.",
)
replace("docs/22-semantic-open-model-review.md", "Default. Cpl deploys only specialists justified by changed paths, deterministic evidence, primary findings, and risk signals.", "When optional model support is enabled, Cpl deploys only model-assisted specialist passes justified by changed paths, deterministic evidence, primary findings, and risk signals. The model-free permanent-officer formation remains active independently.")
replace("docs/22-semantic-open-model-review.md", "export SERGEANT_CPL_PROVIDER=ollama\nexport SERGEANT_CPL_MODEL=qwen3-coder-next", "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=ollama\nexport SERGEANT_CPL_MODEL=qwen3-coder-next")
replace("docs/22-semantic-open-model-review.md", "export SERGEANT_CPL_PROVIDER=lm-studio\nsergeant pr-review", "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=lm-studio\nsergeant pr-review")
replace("docs/22-semantic-open-model-review.md", "export SERGEANT_CPL_PROVIDER=configured\nexport SERGEANT_CPL_BASE_URL", "export SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=configured\nexport SERGEANT_CPL_BASE_URL")
replace("docs/22-semantic-open-model-review.md", "The earlier `SERGEANT_LLM_*` names remain accepted as compatibility aliases for 0.4.0 integrations. New configuration and product documentation should use `SERGEANT_CPL_*`.", "The default is `SERGEANT_CPL_POLICY=disabled`; model support is opt-in. The earlier `SERGEANT_LLM_*` names remain accepted as compatibility aliases for 0.4.0 integrations. New configuration and product documentation should use `SERGEANT_CPL_*`.")

# Supporting architecture docs: multi-model is a capability, not Sergeant's normal dependency.
replace("docs/34-cpl-officer-amplification.md", "- replaceable model-powered bots attached to matching permanent officers;\n- elastic multi-model council formation;", "- optional replaceable model-powered bots attached to matching permanent officers only when the user enables extra reasoning;\n- optional elastic multi-model support council formation, never a default dependency;")
replace("docs/34-cpl-officer-amplification.md", "Models power Cpl council members and officer-support bots.", "When enabled, models may power optional Cpl council members and officer-support bots.")
replace("docs/35-cpl-council-command-and-experience.md", "- Cpl forms and chairs the model council, tables issues, deploys support, improves instructions, and reports mission state.\n- Permanent officers retain universal training, specialist doctrine, evidence duties, experience, and their own reports.\n- Models are replaceable council members and officer-support engines.", "- Cpl commands the permanent-officer formation, tables issues, improves instructions, and reports mission state model-free by default.\n- Permanent officers retain universal training, specialist doctrine, evidence duties, experience, and their own reports.\n- When the user enables extra reasoning, models are replaceable optional council members and officer-support engines.")
replace("docs/35-cpl-council-command-and-experience.md", "## Elastic council\n\nCpl starts with the models already justified by the mission and existing specialist plan.", "## Optional elastic model-support council\n\nThe model-free Cpl and permanent-officer formation is the standard path. When the user enables extra reasoning, Cpl starts with only the model support already justified by the mission and existing specialist plan.")
replace("docs/35-cpl-council-command-and-experience.md", "More models are not treated as votes.", "Optional models are not treated as votes.")
replace("docs/35-cpl-council-command-and-experience.md", "- multiple models can serve as distinct council members;", "- optional multiple models can serve as distinct council members after explicit user enablement;")

# Tests bind the product truth.
replace(
    "tests/test_llm_provider.py",
    '''def test_cpl_settings_are_enabled_by_default_but_do_not_expose_api_key(monkeypatch) -> None:\n    monkeypatch.setenv("SERGEANT_CPL_API_KEY", "secret-value")\n    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "auto")\n    monkeypatch.setenv("SERGEANT_CPL_POLICY", "preferred")\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is True\n    assert settings.policy == "preferred"\n    assert settings.public_dict()["officer"] == "Cpl"\n    assert settings.public_dict()["role"] == "Corporal Specialist"\n    assert "api_key" not in settings.public_dict()\n    assert "secret-value" not in str(settings.public_dict())\n''',
    '''def test_cpl_settings_are_model_free_by_default_and_do_not_expose_api_key(monkeypatch) -> None:\n    monkeypatch.setenv("SERGEANT_CPL_API_KEY", "secret-value")\n    for name in [\n        "SERGEANT_CPL_ENABLED",\n        "SERGEANT_LLM_ENABLED",\n        "SERGEANT_CPL_POLICY",\n        "SERGEANT_LLM_POLICY",\n    ]:\n        monkeypatch.delenv(name, raising=False)\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is False\n    assert settings.policy == "disabled"\n    assert settings.public_dict()["officer"] == "Cpl"\n    assert settings.public_dict()["role"] == "Corporal Specialist"\n    assert "api_key" not in settings.public_dict()\n    assert "secret-value" not in str(settings.public_dict())\n\n\ndef test_cpl_model_support_requires_explicit_policy_opt_in(monkeypatch) -> None:\n    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "auto")\n    monkeypatch.setenv("SERGEANT_CPL_POLICY", "preferred")\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is True\n    assert settings.policy == "preferred"\n''',
)
replace("tests/test_vscode_extension_package.py", 'assert properties["sergeant.provider"]["default"] == "Cpl Automatic Reasoning"', 'assert properties["sergeant.provider"]["default"] == "Disabled"')
replace("tests/test_vscode_extension_package.py", 'assert properties["sergeant.llmPolicy"]["default"] == "preferred"', 'assert properties["sergeant.llmPolicy"]["default"] == "disabled"')
replace("tests/test_vscode_extension_package.py", 'assert properties["sergeant.llmProvider"]["default"] == "auto"', 'assert properties["sergeant.llmProvider"]["default"] == "disabled"')
replace("tests/test_vscode_extension_package.py", '        "Cpl Council Reasoning",', '        "Cpl / Officer Reasoning",')
replace("tests/test_vscode_extension_package.py", '        "Cpl Reasoning Evidence",', '        "Cpl Reasoning Evidence",\n        "ENGINEERING REVIEWER",\n        "Off — model-free Sergeant (default)",')
replace("tests/test_vscode_extension_package.py", '    assert "Free Claude Code" not in command_center', '    assert "Free Claude Code" not in command_center\n    assert "AI CODE REVIEWER" not in command_center')

# Add canonical decision and a focused drift test.
write(
    "docs/54-model-free-default-and-optional-model-support.md",
    """# Sergeant Model-Free Default and Optional Model Support\n\n## Canonical product truth\n\nSergeant is a model-free engineering review system by default. Its normal review path uses:\n\n```text\nRepository / changed files\n→ deterministic evidence\n→ Cpl command\n→ permanent officers\n→ tenfold private cells\n→ tools, scanners, repository facts, and verified experience\n→ Analyst / Challenger / Judge reconciliation\n→ Sergeant Commander verdict\n```\n\nA user does not need an AI login, hosted model, local model, or GPU to run Sergeant's standard independent review.\n\n## Optional extra reasoning\n\nModels are optional engines beneath Cpl. They may be enabled by the user to add another reasoning source for a named officer question, deeper specialist pass, disagreement, or high-risk explicit gate. They do not replace Cpl, permanent officers, privates, deterministic proof, verified lessons, or Sergeant's final authority.\n\n```text\nDefault\nSERGEANT_CPL_POLICY=disabled\n\nOptional extra reasoning\nSERGEANT_CPL_POLICY=preferred\nSERGEANT_CPL_PROVIDER=<explicit allowed route>\n\nExplicit model-assisted gate\nSERGEANT_CPL_POLICY=required\n```\n\n`preferred` may fall back to the complete model-free formation. `required` is used only when the owner intentionally makes model support part of that specific gate.\n\n## Documentation boundary\n\nIt is valid to document multi-model routing, council limits, failover, and model reliability as optional capabilities. It is not valid to describe Sergeant as depending on multi-model review, to present model support as the standard product path, or to enable model endpoints by default.\n\nExternal reviewers such as CodeRabbit and optional models remain opponents, benchmarks, or extra evidence sources. They are not Sergeant dependencies and do not own the final verdict.\n""",
)
write(
    "tests/test_model_free_default_doctrine.py",
    """from __future__ import annotations\n\nimport json\nfrom pathlib import Path\n\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef test_product_defaults_are_model_free() -> None:\n    package = json.loads((ROOT / \"package.json\").read_text(encoding=\"utf-8\"))\n    properties = package[\"contributes\"][\"configuration\"][\"properties\"]\n    provider = (ROOT / \"main_review\" / \"llm_provider.py\").read_text(encoding=\"utf-8\")\n    vscode = (ROOT / \"src\" / \"vscode\" / \"extension.js\").read_text(encoding=\"utf-8\")\n    jetbrains_runner = (ROOT / \"adapters\" / \"jetbrains\" / \"src\" / \"main\" / \"kotlin\" / \"com\" / \"thetechguyds\" / \"sergeant\" / \"SergeantRunner.kt\").read_text(encoding=\"utf-8\")\n    command_center = (ROOT / \"resources\" / \"sergeant-command-center-v2.html\").read_text(encoding=\"utf-8\")\n\n    assert properties[\"sergeant.llmPolicy\"][\"default\"] == \"disabled\"\n    assert properties[\"sergeant.llmProvider\"][\"default\"] == \"disabled\"\n    assert 'SERGEANT_LLM_POLICY\", \"disabled\"' in provider\n    assert '|| \"disabled\"' in vscode\n    assert '?: \"disabled\"' in jetbrains_runner\n    assert \"Off — model-free Sergeant (default)\" in command_center\n    assert \"AI CODE REVIEWER\" not in command_center\n\n\ndef test_public_doctrine_says_models_are_optional_extra_reasoning() -> None:\n    readme = (ROOT / \"README.md\").read_text(encoding=\"utf-8\")\n    doctrine = (ROOT / \"docs\" / \"54-model-free-default-and-optional-model-support.md\").read_text(encoding=\"utf-8\")\n    cpl_doc = (ROOT / \"docs\" / \"22-semantic-open-model-review.md\").read_text(encoding=\"utf-8\")\n\n    for text in [readme, doctrine, cpl_doc]:\n        lowered = text.lower()\n        assert \"model-free\" in lowered\n        assert \"optional\" in lowered\n    assert \"preferred is the product default\" not in readme.lower()\n    assert \"default mode.\\n\\n- deploy cpl when a route is available\" not in cpl_doc.lower()\n""",
)

print("Applied Sergeant model-free default and optional-model documentation correction.")
