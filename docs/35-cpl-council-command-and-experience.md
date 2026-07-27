# Cpl Command, Optional Model Council and Verified Experience

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
