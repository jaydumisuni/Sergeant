# Blind reviewer-intelligence proof

Sergeant's operational tests prove that the product runs safely. The blind reviewer-intelligence proof measures a different question:

```text
Does Sergeant independently find the right defects without reading the answer key or existing reviewer comments?
```

Sergeant's primary benchmark mode is model-free. One-model and multi-model modes are optional comparisons that measure the extra reasoning an owner may enable.

## Blindness boundary

Each benchmark case contains two separate sections:

- repository files and changed-file scope;
- expected findings used only for scoring.

The benchmark engine materializes only repository files into a temporary workspace. Expected findings remain outside the workspace and are loaded only after `run_independent_pr_review()` returns.

Existing pull-request review comments are excluded from live battle comparison by default. They may be included only through an explicit assisted comparison.

## Metrics

The benchmark reports:

- precision;
- recall;
- F1;
- false positives and false negatives;
- verdict accuracy;
- severity accuracy;
- affected-path accuracy;
- line localization accuracy;
- root-cause accuracy;
- duplicate rate;
- finding completeness;
- review duration;
- permanent-officer and route state;
- optional model pass count and distinct models when enabled.

Review-output completeness is not a score for code quality. When Sergeant produces no ranked findings, completeness is reported as not evaluated rather than a misleading `100`.

## Modes

```text
sergeant-bench --mode deterministic
sergeant-bench --mode one-model --require-route
sergeant-bench --mode council --require-route
```

- `deterministic` — canonical Sergeant benchmark. Proves the model-free scanners, learned rules, permanent officers, policy, intelligence, Judge ledger, and final gate.
- `one-model` — optional comparison. Measures one explicitly configured model serving bounded Cpl support passes.
- `council` — optional comparison. Measures an explicitly configured bounded multi-model council.

The latter two do not define the product architecture. They measure whether optional reasoning improves, harms, or leaves unchanged the model-free baseline.

Model/provider configuration remains external. Public artifacts record only credential-safe route status, configured model identifiers, and aggregate metrics.

## Noise boundary

Repository-wide scanners remain broad, but pull-request review separates:

- findings connected to changed files;
- global credential/security blockers;
- unrelated historical background findings;
- self-referential rule/control-plane matches that are explicitly suppressed.

Background findings remain available to officers and humans as context but do not dominate the current change gate.

Committed battle fixtures, expected-answer prose, and project documentation are not scanned as live battle evidence. Learned rules operate on code or patch evidence, not their own answer descriptions. Self-referential matches are suppressed review noise rather than product defects.

## Finding contract

A blocker or major finding reaches the gate only when it survives evidence challenge. Promoted findings should identify:

- what is wrong;
- the affected path and line when available;
- direct evidence;
- the triggering condition;
- the consequence;
- a safer alternative;
- a focused verification test.

Generic or lexical signals remain visible but are non-gating until stronger evidence exists. Known safe evidence can downgrade a lexical signal without hiding the trace.

## Workflow assurance

Workflow:

```text
.github/workflows/review-intelligence-proof.yml
```

- **Purpose:** run focused adversarial tests and the model-free blind suites. Optional manual runs may also compare one-model or council modes.
- **Permissions:** `contents: read` only.
- **Secrets:** optional route values are read from environment-backed GitHub secrets only during explicitly configured runs. They are not command-line arguments or uploaded artifacts.
- **Proof:** benchmark JSON artifacts expose metrics and missed/extra findings while excluding credentials and expected-answer material from review input.

Container packaging:

```text
Dockerfile
```

The standalone workflow builds the image, runs it as non-root with hardened filesystem/capability settings, checks health and API behavior, and proves installed model-free benchmark discovery outside the source tree. Optional provider credentials are never copied into the image.

## Correct interpretation

```text
Model-free benchmark → proves Sergeant
One-model benchmark → measures optional reasoning delta
Council benchmark   → measures optional multi-model reasoning delta
```
