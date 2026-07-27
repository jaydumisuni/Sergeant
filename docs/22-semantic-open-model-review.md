# Optional model reasoning beneath Cpl

> **Current product boundary:** Sergeant's normal review path is model-free. This document describes optional extra reasoning that an owner may enable. It does not define Sergeant's core architecture.

The canonical product boundary is documented in [`55-model-free-core-and-optional-model-reasoning.md`](55-model-free-core-and-optional-model-reasoning.md). The permanent-officer formation is documented in [`44-deterministic-permanent-officer-formation.md`](44-deterministic-permanent-officer-formation.md).

## What Cpl is

Cpl — Corporal Specialist — coordinates Sergeant's permanent officers. Cpl is not a model, provider, proxy, or borrowed gateway.

```text
Repository / changed files
        ↓
Deterministic Sergeant evidence
        ↓
Cpl coordinates permanent-officer packets
        ↓
Analyst + Challenger + Judge adjudication
        ↓
Hermes canonical ledger
        ↓
Sergeant verdict
```

That formation runs without a model route.

## What optional models add

When an owner explicitly enables model support, one model or a bounded multi-model council may:

1. inspect a named semantic gap;
2. challenge unfamiliar framework behavior;
3. provide an independent confirmation;
4. deepen architecture or contract reasoning;
5. preserve unresolved uncertainty for the responsible officer.

Model output enters the same officer packet and Judge-admission boundary as every other evidence source. It cannot create an officer, vote directly on the verdict, override deterministic proof, write code, merge a pull request, or promote a lesson automatically.

## Default behavior

Sergeant does not require a model for `review` or `pr-review`.

```text
SERGEANT_CPL_ENABLED=false
SERGEANT_CPL_POLICY=disabled
SERGEANT_CPL_PROVIDER=disabled
```

A missing provider, expired credential, exhausted quota, unavailable endpoint, or offline machine removes only optional amplification. It does not remove Cpl or the permanent officers.

## Explicit opt-in

### One model

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROVIDER=ollama
export SERGEANT_CPL_MODEL=qwen3-coder-next
sergeant pr-review . --pretty
```

### Local Cpl gateway

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROVIDER=cpl
export SERGEANT_CPL_PROTOCOL=responses
export SERGEANT_CPL_BASE_URL=http://127.0.0.1:8082/v1
sergeant pr-review . --pretty
```

### LM Studio

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROVIDER=lm-studio
sergeant pr-review . --pretty
```

### Explicit OpenAI-compatible endpoint

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROVIDER=configured
export SERGEANT_CPL_BASE_URL=https://your-endpoint.example/v1
export SERGEANT_CPL_MODEL=your-model-slug
export SERGEANT_CPL_PROTOCOL=chat_completions
export SERGEANT_CPL_API_KEY=your-runtime-secret
sergeant pr-review . --pretty
```

Remote endpoints are never auto-discovered. Credentials remain environment-only and are not written to reports or committed to the repository.

## Optional policies

### Disabled — normal default

- No model endpoint is discovered or called.
- Sergeant runs its model-free permanent-officer formation.

### Preferred — optional enhancement

- Use an explicitly enabled route when available.
- Fall back to the model-free formation if the route is unavailable.
- Report whether optional support ran.

### Required — owner-selected strict gate

- The owner has chosen model reasoning as a requirement for this mission.
- An unavailable or failed route becomes a required action.
- This is not Sergeant's default product policy.

## Optional reasoning depth

- `single` — one optional general reasoning pass.
- `adaptive` — recruit only the smallest support set justified by a named gap.
- `deep` — deeper optional specialist support.
- `maximum` — largest bounded optional council.

```text
SERGEANT_CPL_DEPTH=single|adaptive|deep|maximum
SERGEANT_CPL_MAX_PASSES=1..8
```

Depth controls optional provider usage. It does not change the permanent-officer formation.

## Grounding boundary

Every optional model blocker or major claim must include:

- a supplied repository path;
- a valid line range;
- supporting source evidence;
- a concrete impact;
- a safer correction or proof path.

Unsupported blocker and major claims are rejected. Model-only minor findings remain advisory. Deterministic tests, runtime proof, explicit contracts, and verified repository facts outrank speculation.

## Single-model and multi-model support

Sergeant can use:

- no model — normal default;
- one model — optional extra reasoning;
- several explicitly configured models — optional independent council reasoning.

Multi-model support is a capability, not a product dependency and not the definition of Sergeant.

## Configuration reference

```text
SERGEANT_CPL_ENABLED=false|true
SERGEANT_CPL_POLICY=disabled|preferred|required
SERGEANT_CPL_PROVIDER=disabled|auto|cpl|ollama|lm-studio|configured|cloudflare
SERGEANT_CPL_BASE_URL=<explicit /v1 endpoint>
SERGEANT_CPL_MODEL=<provider model slug>
SERGEANT_CPL_PROTOCOL=auto|responses|chat_completions
SERGEANT_CPL_DEPTH=single|adaptive|deep|maximum
SERGEANT_CPL_MAX_PASSES=3
SERGEANT_CPL_API_KEY=<runtime secret>
SERGEANT_CPL_TIMEOUT_SECONDS=90
SERGEANT_CPL_MAX_OUTPUT_TOKENS=5000
```

The earlier `SERGEANT_LLM_*` names remain compatibility aliases for 0.4.0 integrations. New configuration should use `SERGEANT_CPL_*`.

## Authority boundary

```text
Owner
→ Sergeant
→ Cpl
→ permanent officers
→ deterministic evidence
→ optional model support when explicitly enabled
```

Sergeant remains final authority. Optional model reasoning does not change the governed learning or no-auto-merge boundaries.
