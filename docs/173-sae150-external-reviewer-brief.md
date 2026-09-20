# SAE-150 independent hostile review request

Sergeant is seeking **two materially independent external review instances from two distinct accepted source classes** against one frozen candidate. This request is intentionally scoped so reviewers control their own methodology, inputs, tools, and final findings.

## Frozen subject

- Repository: `jaydumisuni/Sergeant`
- Pull request: `#245`
- Candidate commit: `cd757111559b920db2a843d7ca837b2ae51eb774`
- Base commit: `126eeea5a70a0723a1bfb65b2a5dbeb6a84cf2e0`
- Review World ID: `5740cbfd2df05b8d1ee59e6c6452b746d4dee706b1f7ae6ae1460f13706899af`
- RAB ID: `da6f2c3b23a70bce4ee4d43ba3f721e482fc6ae0d0e0a863e1dadf991cf2d1cb`

The exact public intake material is in:

- `docs/167-sae150-root-qualification-authority-registry.json`
- `docs/168-sae150-provenance-verifier-authorization.json`
- `docs/169-sae150-external-review-rab.json`
- `docs/170-sae150-external-review-world.json`
- `docs/171-sae150-external-review-intake.md`
- `docs/172-sae150-external-review-intake-manifest.json`

## Who can satisfy a lane

Accepted source classes are:

- **SC-1:** independent security/code-review contractor or firm.
- **SC-2:** academic/research collaborator.
- **SC-3:** structured public bug-bounty-style participant under a qualifying programme.
- **SC-4:** independent open-source maintainer.
- **SC-6:** qualifying third-party review service under an engagement that independently satisfies the provenance/control-lineage rules.

A second account, model, vendor, session, or tool controlled by the repository owner is **not** an independent source class.

## Reviewer autonomy

A reviewer must use their **own** methodology. The repository owner does not select the prompts, detailed attack plan, inputs, or final findings. Reviewers should attempt to falsify whatever claims they judge important in the frozen candidate, including any route to self-certification, authority substitution, evidence/provenance forgery, UNKNOWN laundering, weakened cardinality, replay/currentness failure, or accidental positive authority.

No particular verdict is expected. "No defects found" is acceptable if that is the reviewer's independent conclusion.

## Required return material

Please return:

1. a timestamped immutable review deliverable;
2. persistent reviewer identity and organization where applicable;
3. source class (SC-1/2/3/4/6);
4. immutable engagement/account/reviewer-generation reference;
5. how reviewer identity and deliverable provenance can be authenticated;
6. reviewer-selected tool/model/methodology lineage where material;
7. confirmation of who controlled methodology/prompts;
8. confirmation of who selected review inputs;
9. confirmation of who selected final submitted findings;
10. enough evidence to establish the seven canonical control-lineage facts.

The seven facts are:

- source separation;
- candidate-authoring separation;
- qualification-corpus separation;
- infrastructure separation;
- prompt/methodology-control separation;
- input-selection separation;
- finding-selection separation.

A verified false makes the review non-independent. An unresolved fact remains UNKNOWN and does not count. Only fully authenticated, fully independent evidence can satisfy the Genesis lane.

## Submission

A machine-readable submission template is in `docs/174-sae150-external-review-submission-template.json`. The repository owner will authenticate the returned material through the SAE-30 provenance verifier; reviewers do not receive any Owner/Root verification secret.
