# Independent PR Reviewer

Main Review is the reviewer.

External tools are optional learning inputs, not merge gates.

## What it combines

- repository evidence
- changed file risk
- THETECHGUY engineering standard
- challenge mode
- decision workspace
- consensus
- optional external review comments

## Rule

CodeRabbit, Qodo, PR-Agent, reviewdog, and human comments can be consumed later, but Main Review must still reach its own verdict without them.

## Outputs

The independent reviewer returns:

- APPROVE
- COMMENT
- REQUEST_CHANGES

with confidence, required actions, evidence summary, and optional learning decisions.

## Confidence condition

The reviewer is considered working when it can approve a verified repo without external reviewer comments and request changes when proof is missing.