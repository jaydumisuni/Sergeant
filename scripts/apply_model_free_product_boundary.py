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


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}: {old[:100]!r}")
    write(path, content.replace(old, new, 1))


def replace_all(path: str, old: str, new: str, *, minimum: int = 1) -> None:
    content = read(path)
    count = content.count(old)
    if count < minimum:
        raise RuntimeError(f"{path}: expected at least {minimum} matches, found {count}: {old[:100]!r}")
    write(path, content.replace(old, new))


def update_readme() -> None:
    path = "README.md"
    replace_once(
        path,
        "Sergeant inspects repositories, reviews pull requests, verifies engineering standards, and produces evidence-based reports. It is not a one-shot coding assistant. It is the reviewer that challenges assumptions, checks proof, and reports what remains before merge or release.\n",
        "Sergeant inspects repositories, reviews pull requests, verifies engineering standards, and produces evidence-based reports. It is not a one-shot coding assistant. It is the reviewer that challenges assumptions, checks proof, and reports what remains before merge or release.\n\n**Sergeant is model-free by default.** Its Cpl, permanent officers, privates, deterministic detectors, scanners, tools, memory, and evidence gates operate without an AI login, hosted model, or major GPU. A user may explicitly enable one or multiple models as optional extra reasoning beneath Cpl; that support never becomes Sergeant's identity, dependency, vote, or final authority.\n",
    )
    replace_once(
        path,
        "**Sergeant Main Review is the reviewer core. Cpl — Corporal Specialist — is Sergeant's native reasoning officer.** Models and gateways are replaceable engines beneath Cpl, not the product identity and not the architectural ceiling.",
        "**Sergeant Main Review is the reviewer core. Cpl — Corporal Specialist — is Sergeant's native model-free coordination and reasoning officer.** Models and gateways are optional, replaceable extra-reasoning engines beneath Cpl. They are not required for normal review, not the product identity, and not the architectural ceiling.",
    )
    replace_once(
        path,
        "Cpl is not a model name or a renamed proxy. It is Sergeant's reasoning layer.",
        "Cpl is not a model name or a renamed proxy. It is Sergeant's model-free coordination and reasoning layer; optional models can amplify a named officer question only after the user enables them.",
    )
    replace_once(
        path,
        "4. recruits and rotates available models only when they can strengthen a named officer question;",
        "4. uses one or multiple models only when the user explicitly enables optional extra reasoning for a named officer question;",
    )
    replace_once(
        path,
        "### Engine routes\n\n| Engine route | Default endpoint | Protocol |",
        "### Optional extra-reasoning engine routes\n\nThese routes are disabled by default. Configure and enable one only when additional model reasoning is desired; Sergeant's normal review remains model-free.\n\n| Engine route | Default endpoint | Protocol |",
    )
    replace_once(
        path,
        "When multiple models are exposed and no model is pinned, Cpl currently prefers:",
        "When optional model support is enabled, multiple models are exposed, and no model is pinned, Cpl currently prefers:",
    )
    replace_once(
        path,
        "### Cpl policies\n\n**Preferred** is the product default:\n\n- deploy Cpl when a route is available;\n- keep Cpl's deterministic permanent-officer formation active when a model route is not available;\n- state clearly in the report whether Cpl ran.\n\n**Required** is the strict release gate:\n\n- no approval when the Cpl route is unavailable or fails;\n- all required deterministic and Cpl evidence must complete.\n\n**Disabled** runs deterministic review only.",
        "### Optional model-support policies\n\n**Disabled** is the product default:\n\n- run Sergeant's model-free Cpl, permanent-officer, private-force, deterministic, scanner, memory, and proof system;\n- do not discover or call any model endpoint;\n- require no AI login, hosted provider, or major GPU.\n\n**Preferred** is a user opt-in extra-reasoning mode:\n\n- call a configured model route when available;\n- preserve the full model-free officer formation and fall back to it when the optional route is unavailable;\n- state clearly in the report whether optional model support ran.\n\n**Required** is an explicit user-selected strict model-assisted release gate:\n\n- no approval when the configured optional route is unavailable or fails;\n- all deterministic and requested model-support evidence must complete.",
    )
    replace_once(
        path,
        "- Cpl controls for policy, engine route, model, base URL, protocol, and reasoning depth.",
        "- Optional Cpl model-support controls for policy, engine route, model, base URL, protocol, and reasoning depth; normal review starts model-free.",
    )
    replace_once(
        path,
        "- Evidence-grounded Cpl reasoning.\n- Adaptive multi-specialist and multi-model review.",
        "- Model-free Cpl, permanent-officer, and private-force reasoning.\n- Adaptive multi-specialist review, with optional single- or multi-model amplification when explicitly enabled.",
    )
    replace_once(
        path,
        "### Complete independent review\n\n```bash\nsergeant pr-review . --pretty\n```",
        "### Complete independent review\n\nThis is model-free by default. It uses Sergeant's deterministic evidence, Cpl coordination, permanent officers, privates, memory, and proof gates without calling a model endpoint.\n\n```bash\nsergeant pr-review . --pretty\n```",
    )
    replace_once(
        path,
        "### Cpl local gateway\n\n```bash\nexport SERGEANT_CPL_PROVIDER=cpl\nexport SERGEANT_CPL_POLICY=preferred",
        "### Optional Cpl local-gateway reasoning\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_PROVIDER=cpl\nexport SERGEANT_CPL_POLICY=preferred",
    )
    replace_once(
        path,
        "### Ollama\n\n```bash\nexport SERGEANT_CPL_PROVIDER=ollama",
        "### Optional Ollama reasoning\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=ollama",
    )
    replace_once(
        path,
        "### LM Studio\n\n```bash\nexport SERGEANT_CPL_PROVIDER=lm-studio",
        "### Optional LM Studio reasoning\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=lm-studio",
    )
    replace_once(
        path,
        "### Explicit OpenAI-compatible endpoint\n\n```bash\nexport SERGEANT_CPL_PROVIDER=configured",
        "### Optional explicit OpenAI-compatible reasoning\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=configured",
    )
    replace_once(
        path,
        "The earlier `SERGEANT_LLM_*` variables and `llm-status` command remain accepted as compatibility aliases for 0.4.0 integrations. New configuration should use Cpl naming.",
        "The default policy is `disabled`, which means model-free Sergeant review. Setting `SERGEANT_CPL_POLICY=preferred` or `required` is an explicit user opt-in to optional model support. The earlier `SERGEANT_LLM_*` variables and `llm-status` command remain accepted as compatibility aliases for 0.4.0 integrations. New configuration should use Cpl naming.",
    )


def update_agents() -> None:
    path = "AGENTS.md"
    replace_once(
        path,
        "Hermes carries orders, evidence, status, and provenance across every level. Hermes does not command, promote lessons, or issue Sergeant's final verdict.\n",
        "Hermes carries orders, evidence, status, and provenance across every level. Hermes does not command, promote lessons, or issue Sergeant's final verdict.\n\n## Model-free core and optional reasoning boundary\n\nSergeant's normal review is **model-free by default**. Cpl, permanent officers, privates, deterministic detectors, scanners, tools, verified memory, and proof gates must remain useful without an AI login, hosted provider, or major GPU.\n\nModels are optional extra-reasoning engines beneath the command chain. They may be enabled only by an explicit owner or user choice. One model or several models may assist a named officer investigation, but they are evidence inputs rather than votes, never replace officers or privates, never become a dependency for normal review, and never issue the final verdict. Model discovery, credentials, and provider usage must remain visibly disabled until that opt-in occurs.\n",
    )


def update_product_brief() -> None:
    replace_once("docs/00-product-brief.md", "- AI reasoning", "- optional model reasoning")


def update_semantic_doc() -> None:
    path = "docs/22-semantic-open-model-review.md"
    replace_once(
        path,
        "# Cpl — Sergeant's Corporal Specialist\n\nCpl is Sergeant's native reasoning officer. It is not the name of a model, provider, proxy, or borrowed repository. Cpl sits under Sergeant Main Review and uses replaceable model engines to perform evidence-grounded specialist reasoning.",
        "# Cpl — Model-Free Core and Optional Model Support\n\nCpl is Sergeant's native model-free coordination and reasoning officer. It is not the name of a model, provider, proxy, or borrowed repository. Cpl sits under Sergeant Main Review and coordinates permanent officers, privates, deterministic evidence, tools, scanners, and verified memory without requiring a model. One or multiple replaceable model engines may be enabled by the user as optional extra reasoning for named specialist questions.",
    )
    replace_once(
        path,
        "General reasoning pass\n        ↓\nRisk-selected specialist passes",
        "Model-free officer/private formation\n        ↓\nRisk-selected specialist investigations\n        ↓\nOptional model support when user enabled",
    )
    replace_once(path, "- Models are engines beneath Cpl.", "- Models are optional extra-reasoning engines beneath Cpl and are disabled by default.")
    replace_once(
        path,
        "2. performs a general reasoning pass;\n3. deterministically selects specialist missions based on risk and repository context;\n4. assigns models to specialists, rotating available engines where useful;",
        "2. coordinates the model-free permanent-officer and private-force formation;\n3. deterministically selects specialist missions based on risk and repository context;\n4. assigns optional model support to specialists only after the user enables it, rotating available engines where useful;",
    )
    replace_once(
        path,
        "## Engine routes\n\n| Engine route | Default endpoint | Protocol |",
        "## Default model-free boundary\n\nNormal Sergeant review does not discover or call model endpoints. Cpl, permanent officers, privates, deterministic detectors, scanners, tools, memory, and proof remain active. Optional model support requires an explicit user-selected `preferred` or `required` policy.\n\n## Optional engine routes\n\n| Engine route | Default endpoint | Protocol |",
    )
    replace_once(
        path,
        "## Model policy\n\nWhen an endpoint exposes multiple models and no model is pinned, Cpl currently prefers:",
        "## Optional model policy\n\nThis section applies only after a user enables model support. When an endpoint exposes multiple models and no model is pinned, Cpl currently prefers:",
    )
    replace_once(
        path,
        "### Preferred\n\nDefault mode.\n\n- Deploy Cpl when a route is available.\n- Keep deterministic Sergeant evidence authoritative.\n- Fall back to deterministic review when the route is unavailable.\n- State clearly in the report that Cpl did not run.\n\n### Required\n\nStrict release-gate mode.\n\n- Cpl must complete before Sergeant can approve.\n- An unavailable or failed route becomes a required action.\n- Useful when both deterministic and reasoning proof are mandatory.\n\n### Disabled\n\n- Do not discover or call model endpoints.\n- Run deterministic Sergeant review only.",
        "### Disabled\n\nProduct default.\n\n- Do not discover or call model endpoints.\n- Run the complete model-free Sergeant formation: Cpl coordination, permanent officers, privates, deterministic evidence, scanners, tools, memory, and proof.\n\n### Preferred\n\nUser opt-in extra-reasoning mode.\n\n- Call the configured optional route when available.\n- Keep model-free Sergeant evidence authoritative.\n- Fall back to the model-free formation when the route is unavailable.\n- State clearly whether optional model support ran.\n\n### Required\n\nExplicit user-selected strict model-assisted release gate.\n\n- The configured optional route must complete before Sergeant can approve.\n- An unavailable or failed route becomes a required action.\n- Useful when the user intentionally requires both model-free and model-assisted proof.",
    )
    replace_once(
        path,
        "### Cpl local gateway\n\n```bash\nexport SERGEANT_CPL_PROVIDER=cpl",
        "### Optional Cpl local gateway\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=cpl",
    )
    replace_once(
        path,
        "### Ollama\n\n```bash\nexport SERGEANT_CPL_PROVIDER=ollama",
        "### Optional Ollama support\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=ollama",
    )
    replace_once(
        path,
        "### LM Studio\n\n```bash\nexport SERGEANT_CPL_PROVIDER=lm-studio",
        "### Optional LM Studio support\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=lm-studio",
    )
    replace_once(
        path,
        "### Explicit OpenAI-compatible endpoint\n\n```bash\nexport SERGEANT_CPL_PROVIDER=configured",
        "### Optional explicit OpenAI-compatible support\n\n```bash\nexport SERGEANT_CPL_ENABLED=true\nexport SERGEANT_CPL_POLICY=preferred\nexport SERGEANT_CPL_PROVIDER=configured",
    )
    replace_once(
        path,
        "The direction is not to imitate a gateway forever. The direction is to make Cpl the strongest reasoning officer Sergeant can support while preserving evidence, auditability, privacy, and Sergeant's final authority.",
        "The direction is to keep Cpl and Sergeant strong model-free reviewers while allowing users to attach optional extra reasoning without weakening evidence, auditability, privacy, or Sergeant's final authority.",
    )


def update_historical_model_docs() -> None:
    replace_once(
        "docs/34-cpl-officer-amplification.md",
        "# Cpl Officer Amplification\n",
        "# Cpl Officer Amplification\n\n> **Product boundary:** this document describes optional model amplification. Sergeant's default Cpl, officer, private, deterministic, tool, scanner, memory, and proof formation is model-free. Models run only after explicit user opt-in.\n",
    )
    replace_once(
        "docs/34-cpl-officer-amplification.md",
        "Cpl adds a higher field-command reasoning layer:\n\n- shared grounded mission intelligence for every deployed officer;\n- deterministic decomposition of specialist support assignments;\n- replaceable model-powered bots attached to matching permanent officers;\n- elastic multi-model council formation;",
        "Cpl's model-free field-command layer provides shared grounded mission intelligence and deterministic specialist decomposition for every deployed officer. When a user enables optional extra reasoning, Cpl can additionally provide:\n\n- replaceable model-powered support bots attached to matching permanent officers;\n- bounded single- or multi-model council formation;",
    )
    replace_once(
        "docs/35-cpl-council-command-and-experience.md",
        "# Cpl Council Command and Verified Experience\n",
        "# Cpl Council Command and Verified Experience\n\n> **Product boundary:** the model council is an optional extra-reasoning capability, not Sergeant's default operating mode. The normal Cpl/officer/private formation is model-free and remains complete without a provider, AI login, or major GPU.\n",
    )
    replace_once(
        "docs/35-cpl-council-command-and-experience.md",
        "- Cpl forms and chairs the model council, tables issues, deploys support, improves instructions, and reports mission state.",
        "- Cpl coordinates the model-free field operation and, only when the user enables optional model support, forms and chairs a bounded model council, tables issues, deploys support, improves instructions, and reports mission state.",
    )
    replace_once(
        "docs/35-cpl-council-command-and-experience.md",
        "## Elastic council\n\nCpl starts with the models already justified by the mission and existing specialist plan.",
        "## Optional elastic model council\n\nAfter explicit user opt-in, Cpl starts with the models already justified by the mission and existing specialist plan.",
    )
    replace_once(
        "docs/25-cloudflare-workers-ai.md",
        "# Cloudflare Workers AI connector\n",
        "# Cloudflare Workers AI connector\n\n> **Optional capability:** this connector is not required for Sergeant review. Normal Sergeant operation is model-free; a user enables this connector only when they want additional model reasoning.\n",
    )


def update_provider_defaults() -> None:
    path = "main_review/llm_provider.py"
    replace_once(
        path,
        'policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "preferred").strip().lower()',
        'policy_raw = _env("SERGEANT_CPL_POLICY", "SERGEANT_LLM_POLICY", "disabled").strip().lower()',
    )
    replace_once(
        path,
        'policy_raw if policy_raw in {"preferred", "required", "disabled"} else "preferred"',
        'policy_raw if policy_raw in {"preferred", "required", "disabled"} else "disabled"',
    )
    replace_once(
        path,
        'if provider == "auto" and not base_url and cloudflare_base and cloudflare_token:',
        'if enabled and provider == "auto" and not base_url and cloudflare_base and cloudflare_token:',
    )


def update_package_defaults() -> None:
    path = ROOT / "package.json"
    package = json.loads(path.read_text(encoding="utf-8"))
    props = package["contributes"]["configuration"]["properties"]
    props["sergeant.provider"]["default"] = "Disabled"
    props["sergeant.provider"]["description"] = (
        "Legacy display preference. Sergeant is model-free by default; Cpl model support is an optional extra-reasoning capability."
    )
    props["sergeant.llmPolicy"]["default"] = "disabled"
    props["sergeant.llmPolicy"]["enumDescriptions"] = [
        "User-enabled optional Cpl model reasoning with model-free fallback.",
        "User-enabled strict gate that requires the configured optional Cpl model route.",
        "Default model-free Sergeant review with Cpl, officers, privates, tools, scanners, memory, and proof.",
    ]
    props["sergeant.llmPolicy"]["description"] = "Optional Cpl model-support gate policy. Disabled is the model-free product default."
    props["sergeant.llmProvider"]["default"] = "disabled"
    props["sergeant.llmProvider"]["enumDescriptions"] = [
        "After model support is enabled, let Cpl discover a local gateway, Ollama, or LM Studio.",
        "Use the Sergeant-native Cpl local gateway as an optional engine.",
        "Use Ollama as an optional engine beneath Cpl.",
        "Use LM Studio as an optional engine beneath Cpl.",
        "Use the explicitly configured endpoint as an optional engine beneath Cpl.",
        "Default model-free Sergeant review; do not discover or call models.",
    ]
    props["sergeant.llmProvider"]["description"] = "Optional extra-reasoning engine route beneath Cpl."
    props["sergeant.llmModel"]["description"] = (
        "Optional primary model slug used only after model support is enabled. Blank lets Cpl choose among explicitly available optional engines."
    )
    path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")


def update_ide_defaults() -> None:
    replace_once(
        "src/vscode/extension.js",
        'policy: configuration.get("llmPolicy") || "preferred",\n    provider: configuration.get("llmProvider") || "auto",',
        'policy: configuration.get("llmPolicy") || "disabled",\n    provider: configuration.get("llmProvider") || "disabled",',
    )
    replace_once(
        "src/vscode/extension.js",
        'output.appendLine(`Cpl council: ${settings.policy} · ${settings.council} · ${settings.provider} · ${settings.model || "automatic model selection"} · ${settings.maxRounds} rounds · ${settings.maxMembers} members`);',
        'output.appendLine(settings.policy === "disabled" || settings.provider === "disabled"\n    ? "Sergeant mode: model-free Cpl + permanent officers + privates"\n    : `Optional Cpl model support: ${settings.policy} · ${settings.council} · ${settings.provider} · ${settings.model || "automatic optional model selection"} · ${settings.maxRounds} rounds · ${settings.maxMembers} members`);',
    )
    replace_once(
        "adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantRunner.kt",
        'val policy = properties.getValue("sergeant.llm.policy") ?: "preferred"\n        val provider = properties.getValue("sergeant.llm.provider") ?: "auto"',
        'val policy = properties.getValue("sergeant.llm.policy") ?: "disabled"\n        val provider = properties.getValue("sergeant.llm.provider") ?: "disabled"',
    )
    replace_once(
        "adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt",
        '"policy" to "preferred",\n            "provider" to "auto",',
        '"policy" to "disabled",\n            "provider" to "disabled",',
    )


def update_command_center() -> None:
    js = "resources/sergeant-command-center-v2.js"
    replace_once(js, "['Cpl', 'Council-led field reasoning']", "['Cpl', 'Model-free field coordination; optional extra reasoning']")
    replace_once(js, "['Quartermaster', 'Models + weapons + loadout']", "['Quartermaster', 'Tools + optional models + loadout']")
    replace_once(js, "'Cpl Council Reasoning',", "'Optional Cpl Model Reasoning',")
    replace_once(js, "policy: 'preferred',\n      provider: 'auto',", "policy: 'disabled',\n      provider: 'disabled',")
    replace_once(js, "'Cpl Council', 'Officer Rebrief'", "'Officer Review', 'Officer Rebrief'")
    replace_once(js, "['Model Independence', 88]", "['Optional Model Boundary', 100]")
    replace_once(
        js,
        "['Council Command', 'Cpl tables officer reports before multiple model members, recruits only for named gaps and repeats within strict round and member limits.']",
        "['Cpl Coordination', 'Cpl coordinates the model-free officer/private formation. Optional model members are recruited only after user opt-in and only for named gaps.']",
    )
    replace_once(
        js,
        "['Bounded Growth', 'Cpl forms the smallest sufficient council and adds another model only when a missing capability is named.']",
        "['Optional Bounded Growth', 'When model support is enabled, Cpl forms the smallest sufficient council and adds another model only when a missing capability is named.']",
    )
    replace_once(js, "`Policy: ${state.settings.policy || 'preferred'}`", "`Policy: ${state.settings.policy || 'disabled'}`")
    replace_once(js, "`Engine route: ${state.settings.provider || 'auto'}`", "`Engine route: ${state.settings.provider || 'disabled'}`")

    html = "resources/sergeant-command-center-v2.html"
    replace_once(html, "<small>AI CODE REVIEWER</small>", "<small>ENGINEERING REVIEWER</small>")
    replace_once(
        html,
        "Delivering verified code reviews with deterministic proof and Cpl specialist reasoning.",
        "Delivering verified model-free code reviews with Cpl, permanent officers, privates, deterministic proof, and optional user-enabled extra reasoning.",
    )
    replace_once(html, '<b id="semanticRoute">Automatic</b>', '<b id="semanticRoute">Model-free</b>')
    replace_once(
        html,
        "Full deterministic and Cpl workspace review.",
        "Full model-free Cpl, officer, private, deterministic, memory, and proof review.",
    )
    replace_once(
        html,
        '<label><input type="checkbox" checked>Cpl Specialist Reasoning</label>',
        '<label><input type="checkbox">Optional Model Reasoning</label>',
    )
    replace_once(
        html,
        '<label>Policy<select id="llmPolicySelect"><option value="preferred">Preferred — Cpl with deterministic fallback</option><option value="required">Required — no approval without Cpl</option><option value="disabled">Disabled — deterministic only</option></select></label>',
        '<label>Optional Model Support<select id="llmPolicySelect"><option value="disabled">Disabled — model-free Sergeant (default)</option><option value="preferred">Preferred — optional reasoning with model-free fallback</option><option value="required">Required — user-selected model-assisted gate</option></select></label>',
    )
    replace_once(
        html,
        '<label>Engine Route<select id="providerSelect"><option value="auto">Automatic — Cpl, Ollama, LM Studio</option><option value="cpl">Cpl Local Gateway</option><option value="ollama">Ollama</option><option value="lm-studio">LM Studio</option><option value="openai-compatible">OpenAI-compatible endpoint</option><option value="disabled">Disabled</option></select></label>',
        '<label>Optional Engine Route<select id="providerSelect"><option value="disabled">Disabled — no model endpoint</option><option value="auto">Automatic local route after opt-in</option><option value="cpl">Cpl Local Gateway</option><option value="ollama">Ollama</option><option value="lm-studio">LM Studio</option><option value="openai-compatible">OpenAI-compatible endpoint</option></select></label>',
    )
    replace_once(
        html,
        "Cpl is Sergeant's native reasoning officer. Models and gateways are replaceable engines beneath it. Automatic discovery is loopback-only.",
        "Cpl is Sergeant's native model-free coordination and reasoning officer. Models and gateways are optional extra-reasoning engines beneath it and remain disabled until the user enables them. Automatic discovery is loopback-only after opt-in.",
    )
    replace_once(
        html,
        '<div class="row"><span>Cpl Reasoning</span><b class="pass">ROUTED</b></div>',
        '<div class="row"><span>Cpl / Officer Formation</span><b class="pass">MODEL-FREE</b></div>',
    )
    replace_once(
        html,
        "Static, runtime, Cpl, UI, documentation, battle and external evidence.",
        "Static, runtime, model-free Cpl/officer, UI, documentation, battle, external, and optional model evidence.",
    )
    replace_once(
        html,
        "Sergeant gathers comparable evidence, Cpl reasons over it, and the Commander decides from verified facts.",
        "Sergeant gathers comparable evidence, Cpl coordinates the model-free officer/private formation, and the Commander decides from verified facts. Optional model reasoning contributes evidence only when the user enables it.",
    )
    replace_once(
        html,
        "Compare Cpl specialists, independent models and external reviewers",
        "Compare Cpl specialists, optional independent models when enabled, and external reviewers",
    )


def write_canonical_doc() -> None:
    write(
        "docs/54-model-free-core-and-optional-reasoning.md",
        """# Sergeant Model-Free Core and Optional Reasoning Boundary

## Canonical product truth

Sergeant's normal review is model-free.

```text
Repository / changed files
→ Cpl model-free coordination
→ permanent officers
→ tenfold private cells
→ deterministic detectors, scanners, tools, memory, and workspace evidence
→ Analyst / Challenger / Judge reconciliation
→ Sergeant verdict
```

This path requires no AI login, hosted model provider, or major GPU. It is the product, not a fallback or reduced mode.

## Optional extra reasoning

A user may explicitly enable one model or several models beneath Cpl when additional semantic reasoning is desired. Optional model support can:

- deepen a named officer investigation;
- challenge or confirm a grounded finding;
- investigate an unresolved council gap;
- provide periodic external calibration;
- assist isolated Teacher, Prosecutor, or Defender learning roles.

Optional models are evidence inputs. They are not officers, votes, final authority, or prerequisites for normal review. They cannot promote lessons, merge changes, or override deterministic proof and verified repository facts.

## Defaults

```text
SERGEANT_CPL_POLICY=disabled
SERGEANT_CPL_PROVIDER=disabled
```

`preferred` and `required` are explicit opt-in policies:

- `preferred` adds optional model reasoning and falls back to the complete model-free formation;
- `required` is a user-selected strict model-assisted gate for a particular mission or release.

Sergeant must not auto-enable model use merely because credentials, a local endpoint, Cloudflare configuration, Ollama, or LM Studio are present.

## Learning boundary

Models may help teach during controlled learning, but a lesson is not permanent merely because a model proposed it. Promotion still requires frozen blind review, verified fixing truth, Teacher / Prosecutor / Defender challenge, negative controls, unrelated transfer, hidden holdout, and owner approval. When practical, accepted lessons become model-free Sergeant capability through permanent officer doctrine, deterministic detection, tests, and durable memory.

## Documentation rule

Public documentation, IDE defaults, examples, screenshots, and marketing must lead with the model-free product. Multi-model council material must be labelled as optional user-enabled extra reasoning. Historical implementation documents may describe that capability, but may not present it as Sergeant's default identity or dependency.
""",
    )


def update_tests() -> None:
    path = "tests/test_llm_provider.py"
    content = read(path)
    old = '''def test_cpl_settings_are_enabled_by_default_but_do_not_expose_api_key(monkeypatch) -> None:\n    monkeypatch.setenv("SERGEANT_CPL_API_KEY", "secret-value")\n    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "auto")\n    monkeypatch.setenv("SERGEANT_CPL_POLICY", "preferred")\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is True\n    assert settings.policy == "preferred"\n    assert settings.public_dict()["officer"] == "Cpl"\n    assert settings.public_dict()["role"] == "Corporal Specialist"\n    assert "api_key" not in settings.public_dict()\n    assert "secret-value" not in str(settings.public_dict())\n'''
    new = '''def test_cpl_settings_are_model_free_by_default(monkeypatch) -> None:\n    for name in [\n        "SERGEANT_CPL_POLICY",\n        "SERGEANT_LLM_POLICY",\n        "SERGEANT_CPL_ENABLED",\n        "SERGEANT_LLM_ENABLED",\n        "SERGEANT_CPL_PROVIDER",\n        "SERGEANT_LLM_PROVIDER",\n    ]:\n        monkeypatch.delenv(name, raising=False)\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is False\n    assert settings.policy == "disabled"\n\n\ndef test_user_can_explicitly_enable_optional_cpl_reasoning_without_exposing_api_key(monkeypatch) -> None:\n    monkeypatch.setenv("SERGEANT_CPL_API_KEY", "secret-value")\n    monkeypatch.setenv("SERGEANT_CPL_ENABLED", "true")\n    monkeypatch.setenv("SERGEANT_CPL_POLICY", "preferred")\n\n    settings = LLMSettings.from_environment()\n\n    assert settings.enabled is True\n    assert settings.policy == "preferred"\n    assert settings.public_dict()["officer"] == "Cpl"\n    assert settings.public_dict()["role"] == "Corporal Specialist"\n    assert "api_key" not in settings.public_dict()\n    assert "secret-value" not in str(settings.public_dict())\n'''
    if content.count(old) != 1:
        raise RuntimeError("tests/test_llm_provider.py: stale expected default test")
    write(path, content.replace(old, new, 1))

    path = "tests/test_vscode_extension_package.py"
    replace_once(path, 'assert properties["sergeant.provider"]["default"] == "Cpl Automatic Reasoning"', 'assert properties["sergeant.provider"]["default"] == "Disabled"')
    replace_once(path, 'assert properties["sergeant.llmPolicy"]["default"] == "preferred"', 'assert properties["sergeant.llmPolicy"]["default"] == "disabled"')
    replace_once(path, 'assert properties["sergeant.llmProvider"]["default"] == "auto"', 'assert properties["sergeant.llmProvider"]["default"] == "disabled"')

    write(
        "tests/test_model_free_product_contract.py",
        """from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_product_truth_is_model_free_with_optional_model_support() -> None:
    readme = text("README.md")
    agents = text("AGENTS.md")
    semantic = text("docs/22-semantic-open-model-review.md")
    canonical = text("docs/54-model-free-core-and-optional-reasoning.md")

    for document in [readme, agents, semantic, canonical]:
        assert "model-free" in document.lower()
        assert "optional" in document.lower()

    assert "Preferred is the product default" not in readme
    assert "Adaptive multi-specialist and multi-model review" not in readme
    assert "Default mode.\n\n- Deploy Cpl when a route is available." not in semantic


def test_runtime_and_ide_defaults_do_not_enable_models() -> None:
    provider = text("main_review/llm_provider.py")
    extension = text("src/vscode/extension.js")
    runner = text("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantRunner.kt")
    tool_window = text("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt")
    command_center = text("resources/sergeant-command-center-v2.js")
    package = json.loads(text("package.json"))
    props = package["contributes"]["configuration"]["properties"]

    assert '"SERGEANT_LLM_POLICY", "disabled"' in provider
    assert 'else "disabled"' in provider
    assert 'policy: configuration.get("llmPolicy") || "disabled"' in extension
    assert 'provider: configuration.get("llmProvider") || "disabled"' in extension
    assert '?: "disabled"' in runner
    assert '"policy" to "disabled"' in tool_window
    assert '"provider" to "disabled"' in tool_window
    assert "policy: 'disabled'" in command_center
    assert "provider: 'disabled'" in command_center
    assert props["sergeant.provider"]["default"] == "Disabled"
    assert props["sergeant.llmPolicy"]["default"] == "disabled"
    assert props["sergeant.llmProvider"]["default"] == "disabled"


def test_command_center_presents_models_as_optional() -> None:
    html = text("resources/sergeant-command-center-v2.html")
    js = text("resources/sergeant-command-center-v2.js")

    assert "ENGINEERING REVIEWER" in html
    assert "Disabled — model-free Sergeant (default)" in html
    assert "Optional Model Reasoning" in html
    assert "AI CODE REVIEWER" not in html
    assert "Optional Cpl Model Reasoning" in js
""",
    )


def main() -> None:
    update_readme()
    update_agents()
    update_product_brief()
    update_semantic_doc()
    update_historical_model_docs()
    update_provider_defaults()
    update_package_defaults()
    update_ide_defaults()
    update_command_center()
    write_canonical_doc()
    update_tests()


if __name__ == "__main__":
    main()
