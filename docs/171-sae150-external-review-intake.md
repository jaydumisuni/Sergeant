# SAE-150 external-review intake

This packet freezes the subject that may be reviewed for the mandatory Genesis independent lane. It does **not** claim that any independent review has happened yet and it does not authorize candidate merge or Genesis activation.

## Frozen subject

- Repository: jaydumisuni/Sergeant
- Pull request: #245
- Base: 126eeea5a70a0723a1bfb65b2a5dbeb6a84cf2e0
- Candidate: cd757111559b920db2a843d7ca837b2ae51eb774
- Review mode: repository-wide head
- Review World: docs/170-sae150-external-review-world.json
- Review Authority Bundle: docs/169-sae150-external-review-rab.json
- Public qualification-authority descriptor: docs/167-sae150-root-qualification-authority-registry.json
- Public provenance-verifier descriptor: docs/168-sae150-provenance-verifier-authorization.json

The whole-RAB authorization and cryptographic verification secrets live outside the candidate repository under Owner/Root state. Checked-in descriptors are inspectable identity material only; they cannot self-activate authority.

## Review requirement

Genesis requires at least **two** materially independent review instances from at least **two distinct accepted source classes**. Accepted source classes are SC-1, SC-2, SC-3, SC-4, and SC-6. SC-5 (a different AI vendor/account) does not qualify as a standalone class.

Recommended open slots are:

- **Slot A — SC-1:** an arm's-length independent security/code-review contractor or firm.
- **Slot B — SC-6:** a separately scoped third-party review service only if the engagement itself satisfies Genesis-grade independence and provenance. Ordinary PR bot commentary does not automatically qualify.

These are recommendations, not a relaxation of the accepted-class rule. Another pair of accepted classes may be used if the required independence evidence closes.

## Reviewer operating boundary

The reviewer receives the frozen repository/commit/Review World and the Assurance Evolution documents needed to understand the claims. The reviewer must select their own review approach, prompts, inputs, attack strategy, and final findings. Do not give the reviewer a conclusion to reach, a fixed finding list to confirm, repository write/admin access, Owner-controlled accounts, Owner-controlled compute, or Owner-selected final findings.

The reviewer should attempt to falsify the Genesis candidate's assurance claims, with particular attention to authority substitution, self-certification, Review-World/RAB binding, ACR/cardinality weakening, evidence/provenance forgery, UNKNOWN laundering, mutation/falsifier omission, qualification replay/revocation, Rust/Python common-mode failure, and any path by which a provisional package could gain positive verdict or activation authority.

The output may report no defects. Compensation or consideration must be for performing the review, never for producing a particular verdict.

## Evidence returned by each reviewer

Each review instance must return:

1. a timestamped immutable deliverable (report, signed review artifact, or equivalent);
2. the reviewer's persistent principal identity and organization where applicable;
3. the accepted source class;
4. the reviewer's authority/account generation or other immutable source-generation reference;
5. evidence of the relationship/control-lineage facts required by SPIKE-EXT;
6. the reviewer's own tool/model lineage where material;
7. who controlled prompts/methodology;
8. who selected inputs;
9. who selected the final submitted findings;
10. an evidence digest or artifact from which the digest can be computed.

The seven canonical control-lineage facts are source_separate, authoring_separate, corpus_separate, infrastructure_separate, prompt_control_separate, input_selection_separate, and finding_selection_separate. A verified false makes the record NOT_INDEPENDENT; any unresolved value makes it UNKNOWN_INDEPENDENCE; only seven verified true values can derive INDEPENDENT.

## Local authenticated intake

scripts/sae150_external_review_intake.py validates the frozen public authority packet and can ingest a completed reviewer deliverable. It computes the immutable evidence identity, authenticates the supplied source/control-lineage facts using the separately held Owner/Root provenance-verifier secret, and emits the canonical SAE-30 AuthenticatedProvenanceProof plus ExternalEvidenceProvenanceRecord.

The tool never writes or prints the verifier secret. Its default external authority directory is:

~/.local/state/ttg-cookpit/projects/srg/authority/sae150-genesis-v1

A different location may be supplied with --authority-dir.

A reviewer-submission JSON must contain these fields:

~~~json
{
  "source_principal_id": "persistent reviewer identity",
  "source_organization": "reviewer organization or self",
  "source_class": "SC-1",
  "source_authority_generation": "immutable reviewer/account/engagement generation",
  "creation_generation": "immutable deliverable generation or timestamped artifact id",
  "authenticated_source_provenance": "how principal/engagement/deliverable provenance was authenticated",
  "candidate_authoring_relationship": "none",
  "qualification_corpus_relationship": "none",
  "candidate_infrastructure_relationship": "none",
  "reviewer_tool_lineage": "reviewer-declared tools/models/methodology lineage",
  "prompt_controller": "reviewer",
  "input_selector": "reviewer",
  "finding_selector": "reviewer",
  "control_lineage_facts": {
    "source_separate": true,
    "authoring_separate": true,
    "corpus_separate": true,
    "infrastructure_separate": true,
    "prompt_control_separate": true,
    "input_selection_separate": true,
    "finding_selection_separate": true
  }
}
~~~

Those values are claims until their supporting engagement/provenance evidence is checked. The intake tool cryptographically authenticates the exact facts that were admitted; it does not make an unsupported claim independent.

## Current disposition

The packet is internally ready for external intake. Current external evidence count is zero. Therefore SAE-150 remains GENESIS_PROVISIONAL; candidate merge and Genesis activation remain unauthorized. The unresolved frontier is actual materially independent reviewer evidence.
