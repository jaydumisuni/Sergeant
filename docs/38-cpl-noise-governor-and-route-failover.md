# Optional model-support noise governor and route failover

> **Status:** Additive protection for explicitly enabled model reasoning. Sergeant's normal model-free permanent-officer formation does not depend on this layer.

The canonical product boundary is documented in [`54-model-free-core-and-optional-reasoning.md`](54-model-free-core-and-optional-reasoning.md).

## Why this layer exists

When an owner enables one model or a bounded multi-model council, optional model reports must not become duplicate actions or distort Sergeant's verdict.

The same defect may already be proven by deterministic Sergeant evidence and then be restated by optional model support with different wording, categories, or nearby lines. Counting every restatement as another defect increases noise and lowers precision.

The governor therefore distinguishes:

- independent confirmation of an existing deterministic finding;
- model-only advisory information;
- a novel independently supported defect;
- a grounded but not yet independently supported high-impact claim.

Raw optional evidence remains visible in all cases.

## Cross-source reconciliation

Optional Cpl findings are compared with deterministic repository, diff, capability, and review-intelligence evidence using:

- normalized repository path;
- deterministic root-cause family;
- overlapping or nearby line ranges;
- precise finding matching where available.

A model report that confirms an already-proven command-execution sink strengthens the audit record without creating another required action.

## Classification contract

When optional model support runs, `cpl_review` retains raw evidence and may add:

```text
actionable_findings
confirmed_findings
advisory_findings
unconfirmed_findings
decision_findings
decision_verdict
noise_governor
route_failovers
```

### Deterministic confirmation

A grounded model finding that overlaps existing deterministic evidence is stored in `confirmed_findings`. It does not create another required action or benchmark prediction.

### Advisory

A model-only `minor` or `note` finding is stored in `advisory_findings`. It remains visible but does not downgrade the final decision by itself.

### Novel actionable finding

A novel grounded finding may become actionable only when it satisfies the normal evidence boundary. A major claim requires independent support; unsupported claims remain non-gating.

### Novel unconfirmed finding

A grounded blocker or major claim that has not satisfied the support contract remains in `unconfirmed_findings`. It is not presented as a proven additional defect.

## Verdict reconciliation

Optional follow-up can confirm, reject, or narrow an earlier claim. When a claim is rejected, the effective verdict is recomputed from the evidence that remains. A stale model `BLOCK` or `NEEDS WORK` value cannot continue influencing Sergeant after its support is removed.

Sergeant uses the Judge-qualified action surface. Raw model verdicts remain audit evidence, not final authority.

## Route failover

A selected model is not an officer. If optional support is enabled and one configured route fails, Cpl may try another explicitly configured model in bounded order.

Successful reassignment records:

```text
route_failovers[].pass
route_failovers[].failed_models
route_failovers[].completed_by
```

If every configured route fails:

- `preferred` policy falls back to the model-free permanent-officer formation and records the lost amplification;
- `required` policy fails because the owner explicitly made model reasoning a mission requirement;
- the normal officers and deterministic evidence remain intact in both cases.

## Benchmark behavior

The blind quality benchmark measures the governed action surface:

- deterministic findings remain predictions;
- optional confirmations are not duplicate predictions;
- advisories are not actionable predictions;
- novel qualified findings remain predictions;
- raw optional evidence stays available when packets are included.

## Safety boundaries

- Deterministic Sergeant evidence remains authoritative.
- Raw optional evidence is not silently deleted.
- Model-only high-impact findings require verified repository evidence.
- Provider failure never removes the permanent officers.
- No model or failover route gains repository write, merge, learning-promotion, or execution authority.
