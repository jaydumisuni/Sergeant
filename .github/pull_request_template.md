# Main Review PR Checklist

## What changed?

Describe the change clearly.

## Review standard

Before merge, this change should be able to answer:

- Does it solve the stated problem?
- Does it keep the architecture clean?
- Does it avoid public/private leakage?
- Does it avoid unsafe reviewer execution paths?
- Does it keep documentation truthful?
- Does it include enough proof/tests for the risk level?

## Verdict expectation

Expected reviewer verdict:

- [ ] PASS
- [ ] NEEDS WORK
- [ ] BLOCK

## Safety notes

- [ ] No secrets or credentials added.
- [ ] No untrusted execution path added.
- [ ] No write token required for analysis.
- [ ] No private Hunter/THETECHGUY details exposed publicly.

## Notes for reviewer

Add any context the reviewer should know.