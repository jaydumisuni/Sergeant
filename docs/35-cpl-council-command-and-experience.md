# Optional Cpl model council and verified experience

> **Status:** Implemented optional capability. It is not Sergeant's normal review architecture. Sergeant's permanent-officer formation remains model-free.

The current product boundary is defined in [`55-model-free-core-and-optional-model-reasoning.md`](55-model-free-core-and-optional-model-reasoning.md).

## Command relationship

```text
Sergeant / Commander
        ↓
Cpl coordinates the permanent officers
        ↓
Deterministic tools, tests, scanners, and workspace evidence
        ↓
Optional model support when explicitly enabled
        ↓
Judge-qualified outcomes
        ↓
Archivist-governed experience
```

- Sergeant owns the final engineering verdict and deterministic gates.
- Cpl exists and coordinates the field operation without a model route.
- Permanent officers retain doctrine, evidence duties, experience, and their own reports.
- Models are optional, replaceable support engines.
- Human or Judge-confirmed outcomes are required before durable learning.

## When an optional council may be used

An owner may explicitly enable one model or a bounded multi-model council when extra reasoning is wanted. Cpl may recruit another configured model only for a named gap such as:

- a planned optional support pass failed;
- independent reasoning disagrees;
- an unanswered semantic question remains;
- a novel blocker or major claim needs independent confirmation;
- verified memory indicates a possible recurrence.

```text
SERGEANT_CPL_ENABLED=true
SERGEANT_CPL_POLICY=preferred|required
SERGEANT_CPL_MAX_ROUNDS=1..6
SERGEANT_CPL_MAX_COUNCIL_MEMBERS=1..12
```

`preferred` adds optional reasoning while preserving model-free fallback. `required` is an owner-selected strict mission gate. Neither is the normal model-free default.

## Optional council loop

```text
1. Cpl retrieves relevant verified and rejected experience.
2. The permanent officers complete their normal evidence duties.
3. An explicitly enabled model examines a named officer question.
4. Cpl tables the optional report beside deterministic evidence.
5. Cpl detects a named unresolved gap.
6. A bounded follow-up model may confirm, reject, narrow, or preserve uncertainty.
7. Judge applies the normal evidence-admission boundary.
8. Cpl returns effective findings, remaining gaps, and council history to Sergeant.
```

More models are not votes. Repository evidence, deterministic proof, officer relevance, independence, objections, and recurrence history remain visible.

A PASS response from a model does not resolve a tracked issue by itself. A follow-up must answer the exact tabled question with an explicit disposition:

```json
{
  "council_resolution": {
    "status": "answered | unresolved",
    "disposition": "confirmed | rejected | narrowed | not_applicable | unresolved",
    "answer": "direct evidence-based answer",
    "target_finding": {}
  }
}
```

## Experience system

The canonical engineering lesson store remains:

```text
.main-review/memory.json
```

Operational experience is append-only:

```text
.main-review/cpl-experience.jsonl
```

The ledger may record verified, rejected, or superseded outcomes for Cpl decisions, permanent officers, optional model support, and Armoury weapons. Profiles are derived from evidence events rather than silently mutated.

Raw model findings are never written directly to durable experience.

```text
Review finding
→ explicit human/Judge outcome
→ canonical lesson candidate
→ controls and transfer proof
→ owner-controlled admission
→ future retrieval
```

## Anti-repeat behavior

The system does not promise that code can never reintroduce the same defect. It enforces the realistic rule:

> Applicable verified experience must influence the next mission, or Sergeant must preserve why it could not be reused.

## Output contract

When optional model support runs, `cpl_review` may include:

```text
memory_checked
experience
recurrences
council.mode
council.rounds
council.members
council.recruitment
council.agreement
council.model_independence
council.final_gaps
council.complete
council.officer_instructions
council.effective_findings
```

When model support is disabled or unavailable, the permanent `officer_council` remains the canonical review formation and records the actual model-support status.

## Safety

- Read-only review remains the default.
- No model receives repository write or merge authority.
- Remote endpoints are never auto-discovered.
- Credentials remain environment-only.
- Unsupported blocker or major findings are rejected.
- Current repository and runtime evidence outrank stale memory.
- Sergeant remains final authority.
- Automatic lesson promotion and automatic merge remain forbidden.

## Correct interpretation

```text
No model                 → normal Sergeant review
One configured model     → optional extra reasoning
Several configured models → optional bounded council reasoning
```

Multi-model support is a capability, not a dependency and not the definition of Sergeant.
