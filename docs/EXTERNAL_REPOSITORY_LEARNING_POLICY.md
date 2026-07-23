# External Repository Learning Policy

Sergeant may learn from useful engineering activity that happens outside the Sergeant repository. THETECHGUY repositories and suitable public repositories are valid discovery sources when their evidence can be pinned, replayed, and evaluated without contaminating the blind review.

## Discovery signals

Candidate inputs include:

- a defect-fixing commit;
- a review comment that led to a verified correction;
- a failed workflow followed by a grounded repair;
- an integrity, concurrency, security, data-loss, release, or provenance correction;
- a useful negative result that prevents a false positive;
- a repeated defect pattern across repositories or languages.

A notification, commit, bot comment, script execution, or green workflow is only a signal. It is not itself a lesson.

## Minimum candidate record

```json
{
  "source_repository": "owner/repository",
  "defective_or_pre_fix_commit": "full sha",
  "fixing_commit": "full sha",
  "source_pr_or_issue": null,
  "language": "Rust",
  "changed_files": [],
  "classification": "defect_fix | workflow_repair | review_correction | formatting_only | feature | unknown",
  "source_lineage": [],
  "licence_or_owned_repository": "owned | licence identifier",
  "blind_review_frozen_at": "Sergeant commit sha",
  "artifact_digest": "sha256",
  "durable_evidence_location": "private canonical location"
}
```

## Admission sequence

```text
discover external activity
→ classify whether it contains a real learning opportunity
→ pin the pre-fix and fixing states
→ collect only the authorized files and context
→ freeze Sergeant's blind review before fix disclosure
→ reveal and verify the fixing truth
→ derive a generalized candidate lesson
→ Teacher proposes the rule and positive evidence
→ Prosecutor challenges scope, root cause, and missing cases
→ Defender builds clean negative controls and overfitting attacks
→ test transfer on unrelated repositories or languages when appropriate
→ run hidden holdout
→ admit only proven transferable value
```

## Possible outcomes

- **Admit:** convert the verified lesson into Sergeant-owned detector code, tests, proof rules, benchmarks, or durable memory.
- **Retain as benchmark only:** useful for evaluation but not generalized enough for a permanent detector.
- **Retain as negative control:** proves that a tempting pattern should not be flagged.
- **Reject:** formatting-only, generated noise, feature work without a defect boundary, unverifiable provenance, contaminated blind evidence, or repository-specific overfitting.

## Non-negotiable boundaries

1. Never expose fixing truth before the blind result is frozen.
2. Never treat a bot, external model, reviewer, or successful workflow as authority by itself.
3. Never claim learning from formatting-only or generated changes without an independently verified defect boundary.
4. Preserve rejected lessons and reasons.
5. Preserve exact repository, commit, file, language, licence/ownership, and artifact provenance.
6. No automatic promotion or merge during controlled learning.
7. Useful external value must become Sergeant-owned doctrine, tests, benchmarks, tools, or memory rather than an unexamined dependency.
8. Sergeant remains the final admission authority.

## THETECHGUY repository intake

Owned repositories such as TechGuyCheckm8, lumi-dm, Hunter, TechGuy Tool, TechGuy DM, TechGuy IMEI, and related projects are first-class discovery sources. Their activity should be inspected for transferable review lessons even when the work is not happening in `jaydumisuni/Sergeant`.

The collector should prioritize changes that expose reusable engineering boundaries: unsafe state transitions, missing validation, concurrency races, data-loss risks, weak provenance, release-integrity failures, security mistakes, non-idempotent money operations, broken recovery, and false-success handling.

Routine formatting, naming, generated assets, and repository-specific product behaviour should normally remain outside permanent Sergeant knowledge unless they reveal a broader proven rule.
