# SAE-R1 — Rust Canonical Identity and Encoding Candidate

Lifecycle: **CANDIDATE**.

Construction base: `535699dc5952f5309eaa843098b21457439af706`.

RED generation `932d803a34a52a9b5a77e2f536fd9c9abd9f3126` proved the SAE-R1 implementation was absent: the repository retained only its two historical XFAILs and the five new SAE-R1 tests failed solely because the Python reference encoder did not exist.

First complete GREEN generation: `69325e915afc4227ab595d1edd68fc673184851b`.

## Candidate contract

This candidate provides an independently implemented Rust authority-identity path for the already-PROVEN SAE-10 Review World/RAB, SAE-20 ACR and SAE-40 ledger families.

Python and Rust share only a frozen data-vector specification. Rust imports no Python code and the crate has no third-party dependencies. The Rust implementation contains its own canonical encoder and SHA-256 implementation.

The canonical encoding is type-sensitive, length-prefixed and field-order canonical. Ordered lists retain order. Authority-bearing IDs are full lowercase 64-hex SHA-256 digests; truncation and uppercase substitution fail closed. Generation/domain substitution changes identity.

Frozen vector families cover Review World, RAB, ACR, ledger, collection, attestation, provenance and capsule authority shapes.

The dedicated `SAE Rust Proof` workflow runs the Rust crate independently and proves the frozen Rust/Python vectors agree.

## Authority boundary

This is not yet `QUALIFIED_RUST_IDENTITY_FOUNDATION`. No Rust verdict authority, normal Sergeant verdict authority, Genesis activation, or downstream node qualification is granted by this candidate. A separate qualification/lifecycle closeout must bind the exact reviewed candidate and guarded merge.
