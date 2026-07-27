# Optional Model Reasoning Beneath Sergeant Cpl

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
