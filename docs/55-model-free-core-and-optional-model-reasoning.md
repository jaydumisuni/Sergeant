# Sergeant Product Identity — Model-Free Core, Optional Model Reasoning

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

The shipped default is `SERGEANT_CPL_POLICY=disabled`: model calls are opt-in, while Cpl, permanent officers, privates, deterministic review, proof and learning remain active.

- `SERGEANT_CPL_POLICY=disabled` guarantees model-free review.
- `SERGEANT_CPL_POLICY=preferred` permits optional model assistance when a valid route is available and otherwise continues model-free.
- `SERGEANT_CPL_POLICY=required` is an owner-selected strict gate for a mission that explicitly requires model reasoning.

For backward-compatible explicit opt-in, `SERGEANT_CPL_ENABLED=true` selects the optional `preferred` policy when the owner has not supplied a policy. An explicitly supplied `disabled` policy still wins.

Remote endpoints are never guessed. Remote code transmission requires an explicit owner-configured route. Credentials remain environment-only.

## Visual verification requirement

The public documentation and Command Center wording must be rendered at desktop and 390 × 844 mobile viewports. The proof must confirm the model-free default, optional-model labels, readable controls, non-overlapping fields, and no document-wide horizontal overflow. The executable contract lives in `tests/model-free-product-visual.spec.js` and `.github/workflows/model-free-product-visual-proof.yml`.

## Documentation rule

Public documentation must say **model-free core with optional model reasoning**. It must not describe Sergeant itself as a multi-model reviewer, claim that models power its officers, or imply that a model route is required for Cpl, review, learning, proof, installation, or normal operation.
