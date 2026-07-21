# Adaptive multilingual curriculum

Sergeant training advances by proof, not elapsed time or case count.

## Difficulty law

When the current repository tier becomes routine, the next round must use a larger or semantically harder repository. Promotion is limited to one tier per evidence window.

A promotion window requires at least three completed rounds with:

- recall of at least 0.80 against confirmed defects;
- false-positive rate no greater than 0.10;
- complete provenance;
- complete evidence-integrity checks.

A miss, noisy round, or incomplete proof holds the current tier. It does not silently rewrite the frozen score and it does not grant lesson-promotion authority.

The tiers are:

1. **focused** — up to 4 changed files, 500 changed lines, one package;
2. **component** — up to 12 files, 2,500 lines, two packages;
3. **subsystem** — up to 30 files, 8,000 lines, four packages;
4. **system** — up to 100 files, 25,000 lines, ten packages;
5. **large-system** — repositories or changes beyond those bounds.

Cross-component, concurrency/lifecycle, and highly novel defects can raise semantic difficulty even when raw file counts are smaller.

## Ten-times private-force law

The existing Sergeant command contract remains authoritative:

- estimate the ordinary human-equivalent worker need;
- multiply it by ten;
- never deploy fewer than twenty privates for a meaningful atomic investigation.

Focused work starts at 2 human-equivalent workers / 20 privates. Larger system work can rise to 12 human-equivalent workers / 120 privates. Additional grounded questions or contradictions require separate officer and Cpl authorization before another private cell is created.

## Language rotation

Rust is a high-value accelerator for ownership, lifetime, concurrency, error-path, unsafe-boundary, and state-transition defects. It must not dominate the curriculum.

The planner therefore enforces:

- no same language twice consecutively;
- no more than two cases from one language family in the most recent five;
- no more than two Rust cases in the most recent ten;
- preference for a different language family after every selected case.

A lesson discovered in Rust must later prove transfer in unrelated languages before becoming a broad permanent rule.

## Authority boundary

The adaptive planner may:

- choose the next difficulty tier;
- select provenance-complete candidates;
- rotate languages;
- assign bounded private-force budgets;
- produce a replayable round plan.

It may not:

- declare a lesson true;
- change Sergeant's verdict;
- merge a learning pull request;
- expose hidden fixing truth before the blind result is frozen;
- weaken provenance, negative controls, or holdout requirements.

The plan is an input to the existing freeze → blind review → truth reveal → lesson proposal → adversarial controls → untouched transfer → promotion process.
