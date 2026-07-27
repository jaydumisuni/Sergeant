# Optional Cloudflare Workers AI council

> **Status:** Optional owner-enabled reasoning. Sergeant's normal review path is model-free and does not require Cloudflare, a model roster, or an account login.

Cloudflare support is one provider option beneath Cpl. The canonical product boundary is documented in [`54-model-free-core-and-optional-reasoning.md`](54-model-free-core-and-optional-reasoning.md).

## Explicit activation

Cloudflare is not activated merely because credentials exist. The user must enable model support deliberately:

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_PROVIDER=cloudflare
export SERGEANT_CLOUDFLARE_ACCOUNT_ID=your_account_id
export SERGEANT_CLOUDFLARE_API_TOKEN=your_scoped_workers_ai_token
export SERGEANT_CPL_POLICY=preferred
```

Use `SERGEANT_CPL_POLICY=required` only when the owner intentionally makes optional model reasoning a strict gate for that mission.

Sergeant derives the endpoint:

```text
https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1
```

The Account ID is masked in reports. The token is never included in public settings or proof artifacts.

## Optional roster

After explicit activation, a built-in starter roster may be selected when no exact model or roster is supplied. An exact user roster always wins:

```bash
export SERGEANT_CPL_MODELS='@cf/qwen/qwen3-30b-a3b-fp8,@cf/zai-org/glm-4.7-flash'
```

One model provides optional extra reasoning. Several explicitly configured models allow a bounded optional council. Roster order does not create votes or authority; later models are recruited only for a named evidence gap.

## Usage guardrails

Provider allocations and pricing can change. Check the current Cloudflare Workers AI account limits before enabling the connector.

A conservative optional configuration is:

```bash
export SERGEANT_CPL_DEPTH=adaptive
export SERGEANT_CPL_MAX_PASSES=3
export SERGEANT_CPL_MAX_COUNCIL_MEMBERS=3
export SERGEANT_CPL_MAX_ROUNDS=3
export SERGEANT_CPL_MAX_OUTPUT_TOKENS=1200
export SERGEANT_CPL_MAX_INPUT_CHARS=30000
```

These are review limits, not billing guarantees. Sergeant does not silently route to another paid provider.

## Proof workflow assurance

The relevant workflow is `.github/workflows/review-intelligence-proof.yml`.

- **Normal purpose:** run deterministic model-free proof on every PR.
- **Optional purpose:** allow an explicit manual one-model or council benchmark.
- **Permissions:** read-only `contents: read`; checkout credentials are not persisted.
- **Secrets:** provider credentials are accepted only through approved secrets and are excluded from artifacts.
- **Rollback:** disable model support or dispatch deterministic mode; Sergeant's permanent officers remain available.

## Prove the optional route

```bash
sergeant cpl-status --require
sergeant-bench review-benchmarks/blind \
  --mode council \
  --require-route \
  --minimum-precision 0.90 \
  --minimum-recall 0.90 \
  --pretty
```

A valid council proof must show multiple distinct configured models, a completed council, no unresolved required gaps, and benchmark quality above the configured thresholds. It proves the optional council, not Sergeant's core.

## Correct interpretation

```text
Cloudflare not configured                    → model-free Sergeant
Cloudflare credentials present               → still model-free until enabled
One Cloudflare model explicitly enabled      → optional extra reasoning
Several Cloudflare models explicitly enabled → optional bounded council
```

Cloudflare support does not make Sergeant Cloudflare-dependent. Ollama, LM Studio, a local Cpl gateway, or another explicit OpenAI-compatible endpoint remain optional alternatives.
