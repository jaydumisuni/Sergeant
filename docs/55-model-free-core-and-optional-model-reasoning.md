# Model-free core and optional model reasoning

Sergeant's normal review system is model-free.

```text
Repository / changed files
        ↓
Deterministic evidence and bounded field investigations
        ↓
Cpl coordinates the permanent officers
        ↓
Analyst reconciliation
        ↓
Challenger falsification
        ↓
Judge admission ledger
        ↓
Hermes evidence delivery
        ↓
Sergeant verdict
```

The permanent officers, Cpl coordination, learned deterministic rules, evidence admission, assurance gates, and final verdict do not require a model, provider login, hosted API, or local GPU.

## Default product behavior

- `sergeant review` and `sergeant pr-review` run the model-free Sergeant formation.
- No model endpoint is discovered or called by default.
- A missing provider, expired credential, exhausted quota, or offline machine does not remove Sergeant's officers.
- Models never become officers, votes, final authority, or a requirement hidden behind the normal review command.

The default environment is equivalent to:

```text
SERGEANT_CPL_ENABLED=false
SERGEANT_CPL_POLICY=disabled
SERGEANT_CPL_PROVIDER=disabled
```

## Optional extra reasoning

An owner may explicitly enable one model or a bounded multi-model council when extra semantic reasoning is wanted.

This optional layer can:

- investigate unfamiliar framework behavior;
- challenge ambiguous architecture;
- provide an independent confirmation;
- explore a named evidence gap;
- deepen a strict release review when the owner chooses to require it.

Optional model output enters the same permanent-officer packets and the same Judge admission boundary. It cannot bypass deterministic evidence, create duplicate actions, silently promote learning, write code, or merge a pull request.

Example opt-in:

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROVIDER=ollama
export SERGEANT_CPL_MODEL=qwen3-coder-next
sergeant pr-review . --pretty
```

A strict owner-selected gate may use `SERGEANT_CPL_POLICY=required`. That is a mission policy chosen by the user, not Sergeant's default architecture.

## Single-model and multi-model options

- **Single model** — one optional reasoning engine supports bounded Cpl passes.
- **Multi-model council** — several explicitly configured engines may be recruited for independent reasoning or a named unresolved gap.
- **No model** — the normal and default Sergeant review path.

Multi-model support is therefore a capability, not a product dependency and not the definition of Sergeant.

## Authority boundary

```text
Owner
→ Sergeant
→ Cpl
→ permanent officers
→ deterministic tools, scanners, tests, workspace evidence
→ optional model support when explicitly enabled
```

Sergeant remains the final review authority. Durable learning remains owner-controlled and proof-bound. Automatic promotion and automatic merge remain forbidden.
