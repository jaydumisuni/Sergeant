# SAE-110 Assurance Capsule / Recovery / Currentness / Owner Risk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the content-addressed SAE-110 Assurance Capsule, exact-generation durable recovery/currentness protocol, invalidation/provenance escape handling, and explicit Owner-risk separation required by the canonical roadmap.

**Architecture:** Add one focused `main_review/assurance_capsule.py` authority surface using the existing canonical SHA-256 encoding helpers and existing `EngineeringVerdictRecord` / `BusinessRiskDecisionRecord` types. Capsules commit to both authority-bearing collection roots and their closure-witness roots. A filesystem archive persists canonical payloads by exact capsule ID and recovery requires exact ID + exact subject generation; there is deliberately no latest-compatible lookup. Invalidation is append-only and currentness checks fail closed.

**Tech Stack:** Python 3.11+, dataclasses, canonical JSON/SHA-256 helpers already in `main_review.review_world`, pytest.

**Spec:** `docs/59-sergeant-assurance-evolution-roadmap.md` SAE-110 plus `docs/58-sergeant-assurance-evolution-founding-architecture.md` §22.

## Global Constraints

- Preserve SAE-100 and every frozen predecessor byte-for-byte unless the roadmap explicitly requires a new successor surface.
- Historical PASS remains attached to its exact world and cannot render as current/global PASS when stale or scoped.
- Owner business-risk decisions remain disjoint from engineering evidence/verdict authority.
- Recovery must require exact capsule identity and exact generation; no newest/latest-compatible selection.
- Capsule identity must commit to closure witnesses, UNKNOWNs, provenance/currentness metadata, Rust admissibility, and Sergeant engineering verdict identity.

---

### Task 1: Capsule identity and closure commitments

**Files:**
- Create: `main_review/assurance_capsule.py`
- Create: `tests/test_assurance_capsule.py`

**Interfaces:**
- Consumes: `sha256_id`, `require_full_sha256`, `EngineeringVerdictRecord`.
- Produces: `CollectionCommitment.create(...)`, `AssuranceCapsuleRecord.create(...)`, canonical `to_payload()` / `from_payload()`.

- [ ] Write hostile tests proving omitted closure witness, duplicate/noncanonical member roots, malformed authority IDs, wrong engineering-verdict Review World, and identity mutation fail closed.
- [ ] Run `pytest -q tests/test_assurance_capsule.py` and observe RED because the module does not exist.
- [ ] Implement the minimum canonical dataclasses and validation.
- [ ] Re-run the focused test until GREEN.

### Task 2: Currentness, invalidation and provenance escape

**Files:**
- Modify: `main_review/assurance_capsule.py`
- Modify: `tests/test_assurance_capsule.py`

**Interfaces:**
- Produces: `CapsuleCurrentness`, `InvalidationRecord`, `require_current_capsule(...)`.

- [ ] Add RED tests for stale generation, wrong scope/domain, invalidated capsule, stale PASS rendering, and provenance escape.
- [ ] Implement exact fail-closed currentness/invalidation checks; historical records remain readable but not current.
- [ ] Re-run focused tests.

### Task 3: Archivist durable exact-generation recovery

**Files:**
- Modify: `main_review/assurance_capsule.py`
- Modify: `tests/test_assurance_capsule.py`

**Interfaces:**
- Produces: `AssuranceCapsuleArchive.store(...)`, `recover_exact(...)`, `invalidate(...)`.

- [ ] Add RED tests proving zero-context recovery from disk reproduces the exact capsule, tampered payloads fail, wrong generation fails, and there is no latest-compatible fallback.
- [ ] Implement content-addressed JSON persistence and append-only invalidation records with exact hash verification.
- [ ] Re-run focused tests.

### Task 4: Owner-risk separation and qualification artifacts

**Files:**
- Modify: `tests/test_assurance_capsule.py`
- Create: `docs/128-sae110-assurance-capsule-candidate.md`
- Create: `docs/129-sae110-assurance-capsule-candidate-manifest.json`

**Interfaces:**
- Consumes: existing `BusinessRiskDecisionRecord`.
- Produces: hostile proof that risk acceptance is never an engineering-evidence/capsule currentness input.

- [ ] Add test that a business-risk record cannot substitute for the engineering-verdict ID or make a stale/invalid capsule current.
- [ ] Record exact candidate artifact inventory, dependency identities, authority gain `QUALIFIED_ASSURANCE_CAPSULE` / `QUALIFIED_RECOVERY_PROTOCOL`, and explicit no-Genesis/no-normal-verdict gain.
- [ ] Run focused tests, `git diff --check`, full `pytest -q`, independent last-PROVEN review, then publish only if exact-head proof is green.
