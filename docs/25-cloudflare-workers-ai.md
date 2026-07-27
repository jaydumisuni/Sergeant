# Optional Cloudflare Workers AI connector

> **Status:** Optional extra-reasoning connector. Sergeant's normal reviewer, Cpl coordination, permanent officers, learned rules, and verdict do not require Cloudflare or any model provider.

The canonical product boundary is documented in [`55-model-free-core-and-optional-model-reasoning.md`](55-model-free-core-and-optional-model-reasoning.md).

Sergeant can use a user's own Cloudflare Workers AI account when the owner explicitly enables model support. The connector exposes a loopback-only OpenAI-compatible gateway so the CLI, VS Code, JetBrains, or another approved client can attach optional model reasoning to Cpl.

## What remains public

The repository contains:

- provider-neutral optional Cpl support;
- the loopback Cloudflare gateway;
- model-roster and structured-output proof commands;
- deterministic, one-model, and optional multi-model benchmark contracts;
- no THETECHGUY account IDs, tokens, or private routing policy.

Every user supplies their own Cloudflare Account ID and scoped API token. Nothing is called merely because Sergeant is installed.

## Explicit activation

Store credentials in environment variables. Do not commit them to `.env`, Git, issue comments, or workflow logs.

PowerShell:

```powershell
$env:SERGEANT_CLOUDFLARE_ACCOUNT_ID="your-account-id"
$env:SERGEANT_CLOUDFLARE_API_TOKEN="your-scoped-token"
$env:SERGEANT_CLOUDFLARE_MODELS="@cf/zai-org/glm-4.7-flash,@cf/openai/gpt-oss-120b"
$env:SERGEANT_CPL_ENABLED="true"
$env:SERGEANT_CPL_POLICY="preferred"
$env:SERGEANT_CPL_PROVIDER="cloudflare"
```

Bash:

```bash
export SERGEANT_CLOUDFLARE_ACCOUNT_ID="your-account-id"
export SERGEANT_CLOUDFLARE_API_TOKEN="your-scoped-token"
export SERGEANT_CLOUDFLARE_MODELS="@cf/zai-org/glm-4.7-flash,@cf/openai/gpt-oss-120b"
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROVIDER=cloudflare
```

A one-model roster is valid. Several models create an optional bounded council. Roster order is explicit and Sergeant does not silently add newly released or more expensive models.

## Check configuration

```bash
sergeant-cloudflare --pretty status --require
```

The status packet reports whether the Account ID and token are present but never prints either value.

## Prove configured models

```bash
sergeant-cloudflare --pretty test-models --require
```

This makes one small structured-output call to each configured model. A model is not considered ready merely because an HTTP endpoint responded; it must return the complete proof contract.

## Run the local gateway

```bash
sergeant-cloudflare --pretty gateway
```

The gateway binds to loopback and defaults to `127.0.0.1:8082`. It exposes:

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`

It refuses models outside the configured roster, requires a non-empty messages array, and does not expose an unauthenticated remote binding.

In another terminal:

```bash
sergeant-cloudflare env --shell powershell
# or
sergeant-cloudflare env --shell bash
```

Then run Sergeant with model support explicitly enabled.

## Optional multi-model proof

```bash
sergeant-cloudflare --pretty council-proof . \
  --files "main_review/example.py,tests/test_example.py" \
  --output build/cloudflare-council-proof.json
```

A valid optional council proof requires:

- at least two explicitly configured models;
- completed real model passes;
- more than one distinct model in the result;
- `true_model_independence: true`;
- a complete council;
- no provider errors;
- no unresolved final gaps.

This certifies only that optional council reasoning operated correctly. It does not define Sergeant's core, force a passing code verdict, or grant model authority.

## Cost and privacy boundary

Cloudflare usage is charged to the user's account and remains subject to the provider's allocation, pricing, and data-handling policy. Sergeant does not hide model calls or silently fall back to another paid provider.

The first configured model may handle the initial optional support pass. Later roster members are called only for a named gap, disagreement, confirmation need, or explicitly selected deeper mode.

Credentials remain outside reports and the public repository. Remote code transmission occurs only after the owner configures and enables the route.

## Correct interpretation

```text
Sergeant installed                         → model-free review
Cloudflare credentials present             → still model-free unless enabled
Cloudflare explicitly enabled, one model    → optional extra reasoning
Cloudflare explicitly enabled, several models → optional bounded council
```
