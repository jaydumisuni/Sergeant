# Cpl — Sergeant's Corporal Specialist

Cpl is Sergeant's native reasoning officer. It is not the name of a model, provider, proxy, or borrowed repository. Cpl sits under Sergeant Main Review and uses replaceable model engines to perform evidence-grounded specialist reasoning.

```text
Repository / changed files
        ↓
Deterministic Sergeant evidence
        ↓
Cpl mission planning
        ↓
General reasoning pass
        ↓
Risk-selected specialist passes
        ↓
Evidence grounding and rejection
        ↓
Sergeant cross-source consensus
        ↓
Commander verdict
```

## Command relationship

- **Sergeant Main Review** is the reviewer core and final engineering authority.
- **Cpl — Corporal Specialist** is Sergeant's reasoning officer.
- Models are engines beneath Cpl.
- Gateways are transports beneath Cpl.
- Deterministic proof remains stronger than unsupported model opinion.

The initial transport boundary was informed by useful open-source gateway patterns: stable OpenAI-compatible protocols, provider separation, and model routing behind one endpoint. Sergeant does not carry an upstream gateway's identity or stop at its feature ceiling. Cpl owns the reasoning mission and can continue evolving independently.

## What Cpl adds beyond a gateway

A gateway forwards requests. Cpl performs review orchestration:

1. receives changed-file scope and deterministic Sergeant evidence;
2. performs a general reasoning pass;
3. deterministically selects specialist missions based on risk and repository context;
4. assigns models to specialists, rotating available engines where useful;
5. rejects unsupported or out-of-scope findings;
6. merges supported findings by path, line range, model, and specialist;
7. returns auditable evidence to Sergeant consensus.

Current specialists:

- Correctness
- Security
- Architecture
- Tests and Contracts
- Performance and Concurrency

This makes model selection only one part of Cpl. Better reasoning can come from stronger models, better decomposition, better context, specialist disagreement, stronger grounding, improved repository intelligence, and better verification loops.

## Engine routes

| Engine route | Default endpoint | Protocol |
| --- | --- | --- |
| Cpl local gateway | `http://127.0.0.1:8082/v1` | OpenAI Responses |
| Ollama | `http://127.0.0.1:11434/v1` | Chat Completions |
| LM Studio | `http://127.0.0.1:1234/v1` | Chat Completions |
| Explicit hosted/self-hosted endpoint | configured by owner | Responses or Chat Completions |

Automatic discovery probes loopback endpoints only. Sergeant never guesses a remote endpoint. Code can leave the machine only when the owner explicitly configures a remote base URL.

## Model policy

When an endpoint exposes multiple models and no model is pinned, Cpl currently prefers:

1. GLM-5.2
2. Qwen3-Coder-Next
3. Kimi K2.5
4. GLM-5.1
5. Qwen3-Coder
6. Kimi K2
7. the provider's first available model

This is a routing policy, not a permanent claim that one model is universally best. Cpl can rotate different models across specialist assignments and owners can pin role-specific models.

Examples:

```text
SERGEANT_CPL_SECURITY_MODEL=<security-focused-model>
SERGEANT_CPL_ARCHITECTURE_MODEL=<architecture-focused-model>
SERGEANT_CPL_TESTS_CONTRACTS_MODEL=<contract-focused-model>
```

## Cpl policies

### Preferred

Default mode.

- Deploy Cpl when a route is available.
- Keep deterministic Sergeant evidence authoritative.
- Fall back to deterministic review when the route is unavailable.
- State clearly in the report that Cpl did not run.

### Required

Strict release-gate mode.

- Cpl must complete before Sergeant can approve.
- An unavailable or failed route becomes a required action.
- Useful when both deterministic and reasoning proof are mandatory.

### Disabled

- Do not discover or call model endpoints.
- Run deterministic Sergeant review only.

## Reasoning depth

### Adaptive

Default. Cpl deploys only specialists justified by changed paths, deterministic evidence, primary findings, and risk signals.

### Deep

Always includes correctness, architecture, and tests/contracts specialist passes, plus risk-triggered specialists.

### Maximum

Deploys every current specialist up to the configured pass budget. This is the strongest built-in reasoning mode, but it costs more time and provider usage.

### Single

Runs only the general Cpl pass.

```text
SERGEANT_CPL_DEPTH=adaptive|deep|maximum|single
SERGEANT_CPL_MAX_PASSES=1..8
```

## Grounding boundary

Every Cpl blocker or major finding must include:

- a supplied repository path;
- a valid line range;
- evidence present in that range or file;
- a concrete impact;
- a safer correction or proof path.

Sergeant validates these fields before consensus.

- Unsupported blocker and major findings are discarded.
- Unsupported minor findings are weakened to notes.
- Files outside the supplied review scope are rejected.
- Raw model verdict text cannot override validated findings.
- Tests, runtime proof, explicit contracts, and verified repository facts outrank speculation.

Cpl improves the quality and depth of reasoning. It does not make review infallible or justify a literal guarantee of zero defects.

## Workspace scope

For pull requests and changed-file missions, the declared changed files are supplied to Cpl.

For a full workspace mission with no changed-file list, Sergeant creates a bounded, risk-first sample. Infrastructure, configuration, database, source, UI, tests, and documentation are prioritized, with high-risk paths first.

```text
SERGEANT_CPL_MAX_INPUT_CHARS=120000
SERGEANT_CPL_MAX_FILE_CHARS=18000
```

Binary files and paths outside the repository root are excluded.

## CLI

Check Cpl:

```bash
sergeant cpl-status --pretty
```

Require a working Cpl route:

```bash
sergeant cpl-status --require --pretty
```

Run the complete reviewer:

```bash
sergeant pr-review . --pretty
```

Review explicit files:

```bash
sergeant pr-review . --files "src/app.py,tests/test_app.py" --pretty
```

### Cpl local gateway

```bash
export SERGEANT_CPL_PROVIDER=cpl
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROTOCOL=responses
export SERGEANT_CPL_BASE_URL=http://127.0.0.1:8082/v1
sergeant cpl-status --require --pretty
```

### Ollama

```bash
export SERGEANT_CPL_PROVIDER=ollama
export SERGEANT_CPL_MODEL=qwen3-coder-next
sergeant pr-review . --pretty
```

### LM Studio

```bash
export SERGEANT_CPL_PROVIDER=lm-studio
sergeant pr-review . --pretty
```

### Explicit OpenAI-compatible endpoint

```bash
export SERGEANT_CPL_PROVIDER=configured
export SERGEANT_CPL_BASE_URL=https://your-endpoint.example/v1
export SERGEANT_CPL_MODEL=your-model-slug
export SERGEANT_CPL_PROTOCOL=chat_completions
export SERGEANT_CPL_API_KEY=your-runtime-secret
sergeant pr-review . --pretty
```

The API key is read from the process environment. It is not returned by `cpl-status`, stored in the Command Center webview, written to reports, or committed to the repository.

## Configuration reference

```text
SERGEANT_CPL_ENABLED=auto|true|false
SERGEANT_CPL_POLICY=preferred|required|disabled
SERGEANT_CPL_PROVIDER=auto|cpl|ollama|lm-studio|configured
SERGEANT_CPL_BASE_URL=<explicit /v1 endpoint>
SERGEANT_CPL_MODEL=<provider model slug>
SERGEANT_CPL_PROTOCOL=auto|responses|chat_completions
SERGEANT_CPL_DEPTH=adaptive|deep|maximum|single
SERGEANT_CPL_MAX_PASSES=3
SERGEANT_CPL_API_KEY=<runtime secret>
SERGEANT_CPL_TIMEOUT_SECONDS=90
SERGEANT_CPL_MAX_OUTPUT_TOKENS=5000
SERGEANT_CPL_MAX_INPUT_CHARS=120000
SERGEANT_CPL_MAX_FILE_CHARS=18000
```

The earlier `SERGEANT_LLM_*` names remain accepted as compatibility aliases for 0.4.0 integrations. New configuration and product documentation should use `SERGEANT_CPL_*`.

## IDE behavior

VS Code and JetBrains share the same Cpl controls:

- policy;
- engine route;
- model slug;
- explicit base URL;
- transport protocol;
- reasoning depth.

Both IDEs run workspace, current-file, and changed-file review through `sergeant pr-review`. API keys remain environment-only. The single-mission gate prevents overlapping deterministic and Cpl missions from racing over report state.

## Strictest defensible gate

```text
SERGEANT_CPL_POLICY=required
SERGEANT_CPL_DEPTH=maximum
```

Then require:

- deterministic repository review;
- diff review;
- standards verification;
- capability review;
- Cpl route available;
- grounded Cpl general pass;
- all justified specialist passes;
- tests and runtime proof;
- consensus with no unanswered major or blocker.

The direction is not to imitate a gateway forever. The direction is to make Cpl the strongest reasoning officer Sergeant can support while preserving evidence, auditability, privacy, and Sergeant's final authority.
