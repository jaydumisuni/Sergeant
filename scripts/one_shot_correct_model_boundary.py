from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text.rstrip() + "\n", encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:120]!r}")
    write(path, text.replace(old, new, 1))


canonical = r'''# Sergeant Product Identity — Model-Free Core, Optional Model Reasoning

## Canonical statement

**Sergeant is a model-free engineering review system.**

Its normal reviewer is Sergeant Main Review working through Cpl, permanent officers, privates, deterministic rules, repository evidence, scanners, tests, runtime proof, verified lessons, and the Judge/Commander evidence gate.

Sergeant does **not** require:

- an AI account or login;
- an API key;
- a hosted model provider;
- a local language model;
- a large GPU;
- one model or multiple models.

The permanent officers and privates are native Sergeant roles. They are not prompts pretending to be officers and they do not disappear when no model route exists.

## Normal model-free path

```text
Repository / changed files
        ↓
Sergeant deterministic evidence
        ↓
Cpl mission planning
        ↓
Permanent officers
        ↓
Privates, tools, scanners, repository evidence and verified lessons
        ↓
Analyst / Challenger / Judge reconciliation
        ↓
Sergeant verdict
```

This path remains available when every model setting is absent or disabled.

## Optional extra reasoning

A user may deliberately connect one model or a bounded roster of models when they want additional semantic reasoning.

```text
Model-free Sergeant review
        +
optional owner-enabled model support
        ↓
extra evidence for a named officer question
        ↓
grounding, challenge and reconciliation
        ↓
Sergeant still issues the verdict
```

Optional model support may provide:

- a second interpretation of a difficult code path;
- deeper semantic or architectural reasoning;
- independent confirmation of a named high-risk finding;
- focused follow-up on an unresolved officer question;
- comparison evidence during benchmarks.

It is not required for ordinary review, learning, proof, installation, or product identity. A multi-model council is only one optional configuration of that support layer. It is not Sergeant's default architecture.

## Authority boundary

Models, CodeRabbit and other external reviewers are witnesses and optional evidence sources. They cannot:

- replace Cpl or a permanent officer;
- turn an unsupported claim into a defect;
- promote a lesson;
- modify or merge project code;
- overrule Sergeant's final verdict.

Current repository evidence, deterministic proof, verified lessons, tests and explicit contracts outrank model opinion.

## Configuration meaning

- `SERGEANT_CPL_POLICY=disabled` guarantees model-free review.
- `SERGEANT_CPL_POLICY=preferred` permits optional model assistance when a valid route is available and otherwise continues model-free.
- `SERGEANT_CPL_POLICY=required` is an owner-selected strict gate for a mission that explicitly requires model reasoning.

Remote endpoints are never guessed. Remote code transmission requires an explicit owner-configured route. Credentials remain environment-only.

## Documentation rule

Public documentation must say **model-free core with optional model reasoning**. It must not describe Sergeant itself as a multi-model reviewer, claim that models power its officers, or imply that a model route is required for Cpl, review, learning, proof, installation, or normal operation.
'''
write("docs/55-model-free-core-and-optional-model-reasoning.md", canonical)

# README: keep the existing product guide, but correct the identity and optional boundary.
replace_once(
    "README.md",
    "Sergeant inspects repositories, reviews pull requests, verifies engineering standards, and produces evidence-based reports. It is not a one-shot coding assistant. It is the reviewer that challenges assumptions, checks proof, and reports what remains before merge or release.\n",
    "Sergeant inspects repositories, reviews pull requests, verifies engineering standards, and produces evidence-based reports. It is not a one-shot coding assistant. It is the reviewer that challenges assumptions, checks proof, and reports what remains before merge or release.\n\n**Sergeant's reviewer core is model-free.** Cpl, permanent officers, privates, deterministic rules, repository evidence, scanners, tests, runtime proof, and verified lessons operate without an AI login, API key, local model, hosted provider, or large GPU. A user may optionally connect one or more models for extra reasoning, but models are support evidence—not Sergeant's identity, command system, or final authority. See [`docs/55-model-free-core-and-optional-model-reasoning.md`](docs/55-model-free-core-and-optional-model-reasoning.md).\n",
)
replace_once(
    "README.md",
    "Optional model support amplifies officer packets",
    "Optional owner-enabled model support may add extra reasoning",
)
replace_once(
    "README.md",
    "**Sergeant Main Review is the reviewer core. Cpl — Corporal Specialist — is Sergeant's native reasoning officer.** Models and gateways are replaceable engines beneath Cpl, not the product identity and not the architectural ceiling.",
    "**Sergeant Main Review is the model-free reviewer core. Cpl — Corporal Specialist — is Sergeant's native coordination and reasoning officer.** Cpl, permanent officers and privates remain active without models. A configured model or bounded model roster is an optional support engine for extra reasoning; it is not the product identity, a dependency, or the architectural ceiling.",
)
replace_once(
    "README.md",
    "4. recruits and rotates available models only when they can strengthen a named officer question;",
    "4. when the owner enables model support, may recruit one or more available models only for a named officer question;",
)
replace_once("README.md", "### Engine routes", "### Optional model engine routes")
replace_once(
    "README.md",
    "Automatic discovery probes loopback endpoints only. Sergeant never guesses a remote service. Code can leave the machine only when an owner explicitly configures a remote base URL.",
    "These routes are optional. The model-free reviewer does not require any of them. Compatibility discovery probes loopback endpoints only; Sergeant never guesses a remote service. Code can leave the machine only when an owner explicitly configures a remote base URL.",
)
replace_once(
    "README.md",
    "When multiple models are exposed and no model is pinned, Cpl currently prefers:",
    "When optional model support is enabled, an endpoint exposes multiple models, and no model is pinned, Cpl currently prefers:",
)
replace_once(
    "README.md",
    "**Preferred** is the product default:",
    "**Preferred** is the compatibility policy for optional model assistance—not Sergeant's product identity or a requirement:",
)
replace_once(
    "README.md",
    "- deploy Cpl when a route is available;\n- keep Cpl's deterministic permanent-officer formation active when a model route is not available;",
    "- keep Cpl's model-free permanent-officer formation active at all times;\n- add model reasoning only when a valid route is available;",
)
replace_once(
    "README.md",
    "- Adaptive multi-specialist and multi-model review.",
    "- Adaptive multi-specialist model-free review, with optional one-model or bounded multi-model reasoning support.",
)
replace_once(
    "README.md",
    "- Cpl controls for policy, engine route, model, base URL, protocol, and reasoning depth.",
    "- Optional model-reasoning controls for policy, engine route, model, base URL, protocol, and reasoning depth; the normal officer review remains model-free.",
)
replace_once(
    "README.md",
    "## Strictest defensible review gate",
    "## Optional strict model-assisted review gate",
)
replace_once(
    "README.md",
    "For high-risk releases:",
    "For a high-risk release where the owner explicitly wants model reasoning in addition to the model-free gate:",
)

# Persistent agent memory.
replace_once(
    "AGENTS.md",
    "Hermes carries orders, evidence, status, and provenance across every level. Hermes does not command, promote lessons, or issue Sergeant's final verdict.\n",
    "Hermes carries orders, evidence, status, and provenance across every level. Hermes does not command, promote lessons, or issue Sergeant's final verdict.\n\n## Model-free product boundary\n\nSergeant's core reviewer is model-free. Cpl, permanent officers and privates are native Sergeant roles, not model personas. They operate through deterministic rules, repository evidence, scanners, tests, runtime proof, verified lessons and approved tools without requiring an AI login, API key, local model, hosted provider or large GPU.\n\nOne model or a bounded multi-model council may be connected only as **optional owner-enabled extra reasoning** for named officer questions. Models are replaceable support evidence beneath the command chain; they are not required for normal review or learning and never receive lesson-promotion, write, merge or final-verdict authority. Future documentation must use the phrase **model-free core with optional model reasoning** and must not present Sergeant itself as a multi-model reviewer.\n",
)
replace_once(
    "AGENTS.md",
    "Permanent officers own specialist doctrine and split code review or learning work into distinct evidence obligations. Privates investigate those obligations in parallel through deterministic checks, models, tools, scanners, repository evidence, or approved workspace capabilities.",
    "Permanent officers own specialist doctrine and split code review or learning work into distinct evidence obligations. Privates investigate those obligations in parallel through deterministic checks, tools, scanners, repository evidence, verified lessons, or approved workspace capabilities; optional models may contribute only when the owner has enabled that support.",
)

for path in ("CLAUDE.md", ".github/copilot-instructions.md"):
    text = read(path)
    marker = "\nDo not erase or redesign" if path == "CLAUDE.md" else "\nDo not remove, weaken"
    insertion = "\nSergeant itself is a **model-free engineering reviewer**. Cpl, officers and privates do not require models. One or multiple models are optional owner-enabled extra reasoning only, never the product identity or final authority.\n"
    if insertion.strip() not in text:
        index = text.index(marker)
        text = text[:index] + insertion + text[index:]
        write(path, text)

# Replace outdated model-centric architecture documents with accurate current contracts.
write("docs/22-semantic-open-model-review.md", r'''# Optional Model Reasoning Beneath Sergeant Cpl

Sergeant's core review path is model-free. Cpl is Sergeant's native coordination and reasoning officer, not a model, provider, proxy, or gateway name. Permanent officers and privates remain active when no model route exists.

The canonical product boundary is documented in [`55-model-free-core-and-optional-model-reasoning.md`](55-model-free-core-and-optional-model-reasoning.md).

## Normal path

```text
Repository / changed files
        ↓
Deterministic Sergeant evidence
        ↓
Cpl mission planning
        ↓
Permanent officers and privates
        ↓
Grounding, challenge and Judge reconciliation
        ↓
Sergeant verdict
```

No AI login, API key, local model, hosted provider or large GPU is required.

## Optional support path

When the owner deliberately enables a route, Cpl may ask one model or a bounded roster of models to provide extra reasoning for a named officer question.

```text
Model-free officer investigation
        +
optional model response
        ↓
evidence grounding and rejection
        ↓
officer / Analyst / Challenger reconciliation
        ↓
Sergeant verdict
```

Models never replace Cpl or the permanent officers. Raw model verdict text cannot override validated findings.

## Optional engine routes

| Route | Default endpoint | Protocol |
| --- | --- | --- |
| Cpl local gateway | `http://127.0.0.1:8082/v1` | OpenAI Responses |
| Ollama | `http://127.0.0.1:11434/v1` | Chat Completions |
| LM Studio | `http://127.0.0.1:1234/v1` | Chat Completions |
| Owner-configured endpoint | explicit | Responses or Chat Completions |

Loopback discovery is compatibility behavior only. Remote endpoints are never guessed; remote code transmission requires an explicit owner-configured URL.

## Policies

- `disabled` — guaranteed model-free review.
- `preferred` — model-free review remains active; optional model reasoning runs only when a valid route is available.
- `required` — owner-selected mission gate that refuses approval if the explicitly required model route fails.

## Reasoning depth

`adaptive`, `deep`, `maximum` and `single` control optional model pass depth. They do not control whether Sergeant's permanent officers exist or whether deterministic review runs.

## Grounding boundary

Every optional model blocker or major must include a supplied repository path, valid location, direct evidence, concrete impact and safer proof path. Unsupported high-severity claims are discarded; minor unsupported claims become notes. Current repository facts, deterministic proof, tests, runtime evidence, verified lessons and explicit contracts outrank model opinion.

## Configuration

```text
SERGEANT_CPL_ENABLED=auto|true|false
SERGEANT_CPL_POLICY=preferred|required|disabled
SERGEANT_CPL_PROVIDER=auto|cpl|ollama|lm-studio|configured
SERGEANT_CPL_BASE_URL=<explicit /v1 endpoint>
SERGEANT_CPL_MODEL=<provider model slug>
SERGEANT_CPL_PROTOCOL=auto|responses|chat_completions
SERGEANT_CPL_DEPTH=adaptive|deep|maximum|single
SERGEANT_CPL_API_KEY=<runtime secret>
```

Credentials are environment-only and are not stored by the Command Center or written to reports.

## Authority

Model assistance is optional evidence. It receives no repository write, patch, merge, lesson-promotion or final-verdict authority. Sergeant remains the final engineering authority.
''')

write("docs/34-cpl-officer-amplification.md", r'''# Cpl Officer Coordination and Optional Reasoning Amplification

Cpl is Sergeant's senior native coordination and reasoning officer. Cpl and the permanent squad are model-free and remain fully operational when no model route exists.

Every permanent officer retains universal training, specialist doctrine, mission loadouts, evidence obligations, an officer report and verified experience. Privates investigate bounded evidence obligations through deterministic rules, repository evidence, scanners, tests, runtime proof, verified lessons and approved tools.

## Native model-free duties

Cpl provides:

- shared grounded mission intelligence;
- deterministic specialist assignment;
- officer/private decomposition and cross-checking;
- repeated issue-table and rebrief loops;
- verified experience retrieval and recurrence detection;
- auditable supported findings and unresolved gaps returned to Sergeant.

## Optional model support

If the owner enables it, Cpl may attach one model or a bounded model roster to a named officer question for extra semantic reasoning or independent confirmation. This is additive support, not the foundation of Cpl or the squad.

Current optional support mapping:

| Extra reasoning specialty | Responsible permanent officer |
| --- | --- |
| Correctness / Architecture / Tests | Engineer |
| Security | Medic |
| Performance / Concurrency | Mechanic |

The command relationship is:

```text
Sergeant commands.
Cpl coordinates the model-free field operation.
Permanent officers own their specialties and experience.
Privates gather evidence through approved capabilities.
Optional models may support a named question when enabled.
Judge qualifies outcomes.
Archivist governs durable experience.
Hermes delivers evidence accurately.
```

A model is never an officer. A model response cannot replace the permanent officer, promote a lesson, write code, merge a branch or issue Sergeant's verdict.

The optional council contract is documented in [`35-cpl-council-command-and-experience.md`](35-cpl-council-command-and-experience.md).
''')

write("docs/35-cpl-council-command-and-experience.md", r'''# Cpl Command, Optional Model Council and Verified Experience

## Status

Sergeant's implemented command and experience system is model-free. The model council is an optional support mode that activates only when the owner supplies or permits a route.

## Command relationship

```text
Sergeant / Commander
        ↓
Cpl — native coordination and reasoning
        ↓
Permanent officers
        ↓
Privates, Armoury tools, tests, scanners and repository evidence
        ↓
Judge-qualified outcomes
        ↓
Archivist-governed experience
```

- Sergeant owns the final engineering verdict and deterministic gates.
- Cpl plans, tables issues, rebriefs officers and reports mission state without requiring a model.
- Permanent officers retain doctrine, evidence duties and experience.
- Models, when enabled, are replaceable optional witnesses or support engines.
- Human or Judge-confirmed outcomes are required before durable learning.

## Optional bounded council

A user may enable one model or multiple configured models for extra reasoning. Cpl recruits another model only for a named gap such as a failed optional pass, disagreement, unanswered evidence question or requested independent confirmation.

```text
SERGEANT_CPL_MAX_ROUNDS=1..6
SERGEANT_CPL_MAX_COUNCIL_MEMBERS=1..12
```

These limits govern optional model calls. They do not scale or define Sergeant's permanent officer/private formation.

Model reports are evidence, not votes. Repository evidence, deterministic proof, officer relevance, independence, objections and verified experience remain visible.

## Optional council loop

```text
1. Cpl retrieves verified and rejected experience.
2. Permanent officers and privates inspect current evidence.
3. Cpl tables their reports.
4. If optional model support is enabled, Cpl may assign a named gap.
5. The response is grounded, challenged and reconciled by the responsible officer.
6. Unsupported claims are rejected; unresolved questions remain visible.
7. Cpl returns effective findings and remaining gaps to Sergeant.
```

No optional model response can produce PASS while a required deterministic or officer gap remains unresolved.

## Experience system

Canonical lessons remain in `.main-review/memory.json`; operational experience is append-only in `.main-review/cpl-experience.jsonl`.

Raw model findings are never written directly to durable experience:

```text
review evidence
→ explicit human/Judge outcome
→ governed lesson candidate
→ controls, transfer and holdout
→ owner-controlled admission
→ future retrieval
```

Officers keep verified experience even when every model is removed or replaced.

## Output contract

`cpl_review` may include council fields for compatibility and optional model evidence, but empty or absent model-member data does not mean Cpl or the permanent officers failed to run. Reports must distinguish:

- model-free officer evidence;
- optional model evidence;
- confirmations;
- advisories;
- rejected claims;
- unresolved gaps;
- final Sergeant decision evidence.

## Safety

- Read-only review remains default.
- Models have no write, execution, promotion or merge authority.
- Remote endpoints are never auto-discovered.
- Credentials remain environment-only.
- Current repository and runtime evidence outrank stale memory and model opinion.
- Sergeant remains final authority.
''')

# Optional connector and benchmark docs.
replace_once(
    "docs/25-cloudflare-workers-ai.md",
    "# Cloudflare Workers AI connector\n\nSergeant can use a user's own Cloudflare Workers AI account",
    "# Optional Cloudflare Workers AI connector\n\nSergeant's core reviewer is model-free. When a user wants extra model reasoning, Sergeant can optionally use that user's own Cloudflare Workers AI account",
)
replace_once(
    "docs/25-cloudflare-workers-ai.md",
    "- the provider-neutral Cpl council;",
    "- the model-free Cpl/officer core plus an optional provider-neutral model-support council;",
)
replace_once(
    "docs/25-cloudflare-workers-ai.md",
    "- deterministic and multi-model benchmark contracts;",
    "- deterministic benchmark contracts and optional multi-model benchmark contracts;",
)
replace_once(
    "docs/25-cloudflare-workers-ai.md",
    "## Prove a real multi-model council",
    "## Optionally prove a real multi-model support council",
)

replace_once(
    "docs/38-cpl-noise-governor-and-route-failover.md",
    "Implemented as an additive layer between Cpl's raw council output and Sergeant's final action/consensus surface.",
    "Implemented as an additive governor for optional model-support output before it reaches Sergeant's final action/consensus surface. Sergeant's model-free officer path does not depend on this layer.",
)
replace_once(
    "docs/38-cpl-noise-governor-and-route-failover.md",
    "A multi-model council can be useful without every model report becoming a separate review comment.",
    "When a user enables a multi-model support council, it can add useful reasoning without every model report becoming a separate review comment.",
)
replace_once(
    "docs/38-cpl-noise-governor-and-route-failover.md",
    "A selected model is not the officer and is not allowed to collapse the officer pass merely because its route fails.",
    "A selected optional model is not the officer and is not allowed to collapse the native officer pass merely because its route fails.",
)

replace_once(
    "docs/39-review-intelligence-proof.md",
    "- Cpl pass count and distinct models;\n- route readiness.",
    "- model-free Cpl/officer coverage;\n- optional model pass count, distinct models and route readiness when enabled.",
)
replace_once(
    "docs/39-review-intelligence-proof.md",
    "- `one-model` measures one configured model serving bounded Cpl passes.\n- `council` measures the configured multi-model Cpl council.",
    "- `one-model` optionally measures one configured model adding bounded reasoning support.\n- `council` optionally measures a configured multi-model support council.\n\nNeither optional mode defines Sergeant's core reviewer; `deterministic` exercises the normal model-free product path.",
)

replace_once(
    "docs/hackathon-submission.md",
    "- [x] Cpl multi-model council and verified experience",
    "- [x] Model-free Cpl/officer review and verified experience; optional multi-model support proof",
)
replace_once(
    "docs/hackathon-submission.md",
    "Sergeant strengthens the full submission because it is not only an AI tool; it is proof infrastructure around AI-built systems.",
    "Sergeant strengthens the full submission because it is a model-free proof and review system around AI-built systems, with optional model reasoning when a user chooses it.",
)

# Public Command Center copy: no runtime contract change, only truthful presentation.
replace_once("resources/sergeant-command-center-v2.html", "<small>AI CODE REVIEWER</small>", "<small>ENGINEERING REVIEW SYSTEM</small>")
replace_once(
    "resources/sergeant-command-center-v2.html",
    "Delivering verified code reviews with deterministic proof and Cpl specialist reasoning.",
    "Delivering verified model-free code reviews, with optional model reasoning when enabled.",
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    "Full deterministic and Cpl workspace review.",
    "Full model-free Sergeant workspace review; optional extra reasoning when enabled.",
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    "<article class=\"panel\"><h4>Cpl — Corporal Specialist</h4>",
    "<article class=\"panel\"><h4>Cpl — Model-Free Core / Optional Model Support</h4>",
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    "<option value=\"preferred\">Preferred — Cpl with deterministic fallback</option><option value=\"required\">Required — no approval without Cpl</option><option value=\"disabled\">Disabled — deterministic only</option>",
    "<option value=\"preferred\">Optional models when available; model-free fallback</option><option value=\"required\">Optional strict gate — require configured model support</option><option value=\"disabled\">Model-free only — no model calls</option>",
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    "Cpl is Sergeant's native reasoning officer. Models and gateways are replaceable engines beneath it.",
    "Cpl, permanent officers and privates are Sergeant's native model-free review system. Models and gateways are optional extra-reasoning support only.",
)
replace_once(
    "resources/sergeant-command-center-v2.html",
    "Compare Cpl specialists, independent models and external reviewers",
    "Compare model-free Cpl/officer evidence, optional models and external reviewers",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "['Cpl', 'Council-led field reasoning'],\n    ['Quartermaster', 'Models + weapons + loadout'],",
    "['Cpl', 'Model-free field coordination and reasoning'],\n    ['Quartermaster', 'Tools + weapons + optional model routes'],",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "'Cpl Council Reasoning',",
    "'Cpl Officer Reasoning',\n    'Optional Model Assistance',",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "const labels = ['Mission Started', 'Evidence Collected', 'Cpl Council', 'Officer Rebrief', 'Commander Report'];",
    "const labels = ['Mission Started', 'Evidence Collected', 'Cpl / Officers', 'Officer Rebrief', 'Commander Report'];",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "if (settings.policy === 'disabled' || provider === 'disabled') return 'Deterministic only';\n    return `Cpl · ${settings.council || 'adaptive'} council · ${provider} · ${model} · ${settings.maxRounds || 2}r/${settings.maxMembers || 5}m`;",
    "if (settings.policy === 'disabled' || provider === 'disabled') return 'Model-free Sergeant core';\n    return `Model-free core + optional ${settings.council || 'adaptive'} model support · ${provider} · ${model} · ${settings.maxRounds || 2}r/${settings.maxMembers || 5}m`;",
)
replace_once("resources/sergeant-command-center-v2.js", "['Cpl Council', cplRouteLabel(settings)]", "['Optional Model Reasoning', cplRouteLabel(settings)]")
replace_once("resources/sergeant-command-center-v2.js", "['Model Independence', 88]", "['Cross-check Independence', 88]")
replace_once(
    "resources/sergeant-command-center-v2.js",
    "['Council Command', 'Cpl tables officer reports before multiple model members, recruits only for named gaps and repeats within strict round and member limits.'],",
    "['Model-Free Command', 'Cpl tables and reconciles permanent-officer and private evidence without models; optional models may be recruited only for named gaps.'],",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "['Bounded Growth', 'Cpl forms the smallest sufficient council and adds another model only when a missing capability is named.'],",
    "['Optional Bounded Support', 'When model support is enabled, Cpl uses the smallest sufficient roster and adds another model only for a named gap.'],",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "'Officer: Cpl — Council-led Corporal Specialist',",
    "'Officer: Cpl — native model-free Corporal Specialist',",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "`Primary model: ${state.settings.model || 'Cpl automatic council formation'}`",
    "`Optional model: ${state.settings.model || 'not pinned; model-free core remains available'}`",
)
replace_once(
    "resources/sergeant-command-center-v2.js",
    "['Cpl Council Evidence', 'Grounded reports, council rounds, recruited members, disagreements and officer rebriefs.'],",
    "['Cpl / Officer Evidence', 'Model-free officer reports and rebriefs, plus optional model-support rounds when enabled.'],",
)

# Add an explicit status notice to the historical V2 specification without rewriting its full history.
replace_once(
    "docs/sergeant-v2-master-specification.html",
    "The highest law remains unchanged: Sergeant commands. Specialists advise. Evidence decides.",
    "The highest law remains unchanged: Sergeant commands. Specialists advise. Evidence decides.\n\nCURRENT PRODUCT BOUNDARY: Sergeant's core reviewer, Cpl, permanent officers and privates are model-free. One or multiple models are optional owner-enabled extra reasoning only; they are not required by the architecture or normal operation.",
)

# Regression prevents the identity drift from returning.
write("tests/test_model_free_product_identity.py", r'''from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_canonical_model_boundary_is_explicit() -> None:
    canonical = text("docs/55-model-free-core-and-optional-model-reasoning.md")
    for phrase in (
        "Sergeant is a model-free engineering review system",
        "does not require",
        "optional owner-enabled model support",
        "A multi-model council is only one optional configuration",
        "Sergeant still issues the verdict",
    ):
        assert phrase in canonical


def test_primary_public_docs_do_not_present_multi_model_as_the_product() -> None:
    readme = text("README.md")
    assert "Sergeant's reviewer core is model-free" in readme
    assert "optional one-model or bounded multi-model reasoning support" in readme
    assert "Adaptive multi-specialist and multi-model review." not in readme
    assert "Cpl multi-model council and verified experience" not in text("docs/hackathon-submission.md")


def test_agent_memory_preserves_model_free_identity() -> None:
    agents = text("AGENTS.md")
    assert "## Model-free product boundary" in agents
    assert "Cpl, permanent officers and privates are native Sergeant roles" in agents
    assert "optional owner-enabled extra reasoning" in agents
    assert "must not present Sergeant itself as a multi-model reviewer" in agents
    assert "model-free engineering reviewer" in text("CLAUDE.md")
    assert "model-free engineering reviewer" in text(".github/copilot-instructions.md")


def test_optional_model_docs_keep_authority_below_sergeant() -> None:
    for path in (
        "docs/22-semantic-open-model-review.md",
        "docs/34-cpl-officer-amplification.md",
        "docs/35-cpl-council-command-and-experience.md",
    ):
        value = text(path)
        assert "model-free" in value.lower()
        assert "optional" in value.lower()
        assert "Sergeant" in value
    assert "Models never replace Cpl or the permanent officers" in text(
        "docs/22-semantic-open-model-review.md"
    )


def test_command_center_visibly_separates_core_from_optional_models() -> None:
    html = text("resources/sergeant-command-center-v2.html")
    script = text("resources/sergeant-command-center-v2.js")
    assert "ENGINEERING REVIEW SYSTEM" in html
    assert "Model-Free Core / Optional Model Support" in html
    assert "Model-free only — no model calls" in html
    assert "Model-free Sergeant core" in script
    assert "Optional Model Assistance" in script
    assert "Cross-check Independence" in script


def test_runtime_configuration_contract_remains_honest() -> None:
    provider = text("main_review/llm_provider.py")
    assert 'LLMPolicy = Literal["preferred", "required", "disabled"]' in provider
    assert "Automatic discovery probes loopback endpoints only" in provider
    canonical = text("docs/55-model-free-core-and-optional-model-reasoning.md")
    assert "SERGEANT_CPL_POLICY=disabled" in canonical
    assert "SERGEANT_CPL_POLICY=preferred" in canonical
    assert "SERGEANT_CPL_POLICY=required" in canonical
''')

# Remove this one-shot machinery before committing the actual correction.
(ROOT / ".github/workflows/one-shot-model-boundary.yml").unlink(missing_ok=True)
Path(__file__).unlink(missing_ok=True)
print("Corrected Sergeant model-free identity and optional model-support documentation.")
