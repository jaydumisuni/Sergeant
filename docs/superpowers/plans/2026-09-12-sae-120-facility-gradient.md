# SAE-120 GitHub / Local Facility Gradient Implementation Plan

**Goal:** Preserve one exact assurance law across constrained GitHub and richer owner-approved local/IDE facilities, while making missing facilities fail closed and local writes explicit.

**Architecture:** Add a successor-only facility contract surface. Every facility binds the same ACR/Judge/Rust/PASS-law identities. GitHub is read-only. Local facilities may advertise richer evidence capabilities and explicit owner-approved writes, but those capabilities cannot alter verdict semantics or authority identities. Requirement evaluation yields `AVAILABLE` or `UNKNOWN`; missing required facility/capability never degrades into weaker PASS.

- [ ] RED: hostile tests for law mismatch, GitHub write attempt, unapproved local write, missing facility/capability, and richer-local verdict override.
- [ ] Implement minimum canonical facility records and fail-closed evaluator.
- [ ] Add candidate docs/manifest and prove no authority gain at candidate merge.
- [ ] Run focused proof, diff check, complete suite, independent last-PROVEN review, publish only on exact-head proof.
