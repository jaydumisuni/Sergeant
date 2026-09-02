# SPIKE-EXT — Genuine External-Review Sourcing Feasibility

Date: 2026-09-02

Status: **SPIKE-EXT CANDIDATE, ANALYSIS-ONLY, PROOF PENDING SAE-00** — no real external reviewer was contacted, engaged, hired, or contracted while producing this document. Authority gain: none, per `docs/59` section 6.

This document is the founding node of the SPIKE-EXT bounded feasibility spike defined in `docs/59-sergeant-assurance-evolution-roadmap.md` section 6, `SPIKE-EXT — Genuine external-review sourcing feasibility`. It, `docs/65-spike-ext-external-review-sourcing-feasibility-manifest.json`, and `tests/test_spike_ext_external_review_sourcing_feasibility.py` together produce what that node requires.

## 1. What SPIKE-EXT requires

Quoted from `docs/59` section 6:

> **Proof requires:** `SAE-00`.
>
> Purpose: establish at least one practical source class and provenance route for the future Genesis materially-independent hostile qualification lane.
>
> Must produce:
>
> - acceptable external source classes;
> - authentication/provenance route;
> - independence/control-lineage criteria;
> - expected mandatory external-review lane cardinality proposal;
> - sourcing/logistics disposition.
>
> Current project-controlled AI hostile-review rounds remain `NOT_INDEPENDENT`; they may remain internal hostile evidence but cannot satisfy Genesis external qualification.
>
> Failure to source a reviewer does not weaken the law: implementation may continue, but Genesis qualification cannot prove.
>
> Authority gain: none.

Sections 2 through 6 below produce the five required outputs, in order. Section 7 states this spike's honest disposition. Section 8 states what this spike explicitly does not establish, to prevent a future reader from mistaking analysis for a solved problem.

## 2. Dependency state and anchor

Per `docs/59` section 15, `SPIKE-EXT: [SAE-00]`. This spike's own proof formally requires `SAE-00` to close.

At the time this document was written, `SAE-00 — Founding authority and preservation reference` exists as a reviewed candidate on branch `roadmap/sae-00-founding-authority-reference` (built in parallel by another executor, per `docs/59` section 2's explicit allowance for parallel spike preparation before upstream freezes), but has **not yet merged into canonical `main`**. `docs/62-sae00-founding-authority-and-preservation-reference.md` and `docs/63-sae00-founding-authority-reference-manifest.json` are therefore cited as the current SAE-00 candidate anchor, not as already-closed upstream proof. This document does not hash-bind those two files, because they do not yet exist on the `main`-based branch this document ships on; binding to files absent from this branch would be a fabricated reference, not real provenance.

Consequently, and honestly: this document's own lifecycle state (section 9) cannot exceed `CANDIDATE` / `REVIEWED` until `SAE-00` itself merges to canonical `main` and this spike is reconciled against the exact merged SAE-00 generation. This is the correct application of `docs/59` section 3's forbidden equivalences — `CODE EXISTS != QUALIFIED` — to this spike's own proof state, not a special exception for it.

This document's substantive anchor for "current recovered Sergeant state" is therefore the stable, already-merged pair `docs/58-sergeant-assurance-evolution-founding-architecture.md` and `docs/59-sergeant-assurance-evolution-roadmap.md` (merged via PR #168, `main` commit `9976e43f0d4d318ee4ffd2c4389bd87f520a7757`), plus live repository evidence gathered directly (`PICKUP.md`, `docs/01-research-sources.md`, `docs/12-external-review-learning-loop.md`, `docs/51-cross-repository-learning-intake.md`, `.github/self-learning/cross-repository-sources.json`).

## 3. Independence disposition states (recovered, not redefined)

`docs/58` section 13 (External Evidence Provenance Law) defines independence disposition as exactly one of three states. Quoted verbatim:

> Independence disposition is exactly one of:
>
> - `INDEPENDENT`
> - `NOT_INDEPENDENT`
> - `UNKNOWN_INDEPENDENCE`
>
> Only `INDEPENDENT` may satisfy a mandatory independent lane. Missing provenance is `UNKNOWN_INDEPENDENCE`.
>
> Independence is about control lineage, not surface variation. Different file/chat/model/account/session/tool does not create independence by itself.

This spike does not redefine these three states. It builds the concrete, applicable checklist (section 5) an executor uses to place a specific proposed reviewer arrangement into one of them, and it never treats an unverified arrangement as anything better than `UNKNOWN_INDEPENDENCE`.

## 4. Acceptable external source classes

Six source classes were analyzed for concrete sourcing method, payment/incentive model, and — the hard part — how independence would actually be proven after the fact. None was contacted, engaged, or tested; this is options analysis only, per this spike's explicit scope boundary.

### 4.1 Paid independent security/code-review contractors or firms

**Sourcing:** engage a freelance security researcher or a boutique application-security consultancy with no prior relationship to the project, through a marketplace (e.g. an established freelance/contracting platform) or direct outreach, under an explicit paid statement-of-work scoped to hostile review of a frozen Assurance Evolution Review World/RAB/ACR generation.

**Payment/incentive:** real money — a fixed-fee or hourly engagement, typically representing a genuine cost (from several hundred to several thousand USD for a meaningful pass), invoiced through a normal arm's-length commercial transaction.

**Independence-proof approach:** signed engagement contract or statement of work naming the contractor's own independent business entity; payment record showing an ordinary commercial rate (not a token/symbolic payment structured to look real); contractor's own equipment, account, and infrastructure; no pre-existing personal, familial, or business relationship between contractor and Owner disclosed or discoverable; contractor-authored review methodology, not an Owner-scripted question list; deliverable signed/timestamped by the contractor.

**Logistical honesty:** this is the class most likely to survive independence scrutiny cleanly, because a genuine commercial engagement is the easiest relationship to document as arm's-length. It is also the class requiring a real budget and a real vendor-selection process that do not currently exist in this repository's evidenced state (no procurement process, no existing contractor relationship, no allocated budget line is recorded anywhere in `docs/`, `PICKUP.md`, or `.github/`).

### 4.2 Academic/research collaborators

**Sourcing:** cold outreach to a university software-engineering, security, or formal-methods research group with a genuine research interest in supply-chain assurance, program verification, or AI-assisted review; propose a collaboration in exchange for research material access, co-authorship, or a case-study relationship rather than direct payment.

**Independence-proof approach:** university/institutional affiliation predating any contact with this project; no consulting or funding relationship to the Owner; publication or attribution under the collaborator's own name/institution; explicit written confirmation the collaborator was not directed toward a predetermined conclusion.

**Logistical honesty:** this is the least logistically ready class today. It depends on finding a genuinely interested research group, which requires an existing academic network or a compelling enough research angle to attract cold-outreach interest, and academic engagement timelines are typically measured in months to a semester, not days. No existing academic relationship is evidenced anywhere in this repository.

### 4.3 Structured public bug-bounty-style programme

**Sourcing:** publish a scoped, funded bounty inviting the public to attack specific Assurance Evolution claims (e.g. "find a case where a qualified ACR contract omits a mandatory obligation family" or "find a case where the Rust kernel admits an incomplete collection"), either self-hosted (a funded GitHub issue/label programme with a defined payout) or through an existing bounty platform.

**Independence-proof approach:** participant identity capture (at minimum a persistent public handle, ideally a verifiable real-world identity for payout purposes); payout record as an arm's-length transaction; explicit confirmation the participant is not the Owner and was not directed by the Owner.

**Logistical honesty:** this requires a funded payout pool and genuine public visibility/marketing to attract participants. It is also a poor fit for this specific need: conventional bug bounties reward finding exploitable vulnerabilities in running software, not attacking the completeness of a constitutional specification document or an assurance-kernel design — the participant pool that would actually engage with this kind of architectural/specification-completeness hostile review is narrow, and no existing bounty programme or platform relationship is evidenced in this repository.

### 4.4 Independent open-source maintainers reviewing in exchange for something

**Sourcing:** approach maintainers of comparable review tooling — for example genuine upstream `Kilo-Org/kilocode` maintainers (not the owner-controlled mirror `jaydumisuni/kilocode` recorded in `docs/01`, which is explicitly the same-owner side of that relationship and therefore not a candidate for independence), or maintainers of `qodo-ai/pr-agent`, `reviewdog/reviewdog`, or similar projects already studied in `docs/01-research-sources.md` — proposing a mutual review swap, a small sponsorship, or GitHub-Sponsors-style credit in exchange for a hostile review pass.

**Independence-proof approach:** maintainer's GitHub identity and contribution history predating any engagement with this project; no payment flowing from the Owner beyond the disclosed swap consideration; review delivered from the maintainer's own account/infrastructure; maintainer's own selection of what to flag.

**Logistical honesty:** plausible in principle — `docs/01` already documents genuine study of these projects — but no actual relationship with any of their maintainers is evidenced anywhere in this repository today. This remains a cold-outreach proposition, not a warm one.

### 4.5 A different AI vendor/account operated by an unaffiliated third party

Included explicitly because it is the most tempting **false positive**, and this spike's mandate is to avoid exactly that mistake.

**Why it does not, by itself, establish independence:** `docs/58` section 13 is unambiguous — "Different file/chat/model/account/session/tool does not create independence by itself." An Owner-controlled account on a different AI vendor, paid for with Owner funds, prompted by the Owner, with findings selected and submitted by the Owner, is `NOT_INDEPENDENT` regardless of which vendor's model answered the prompt. Vendor diversity is a property of the tool, not of the control lineage.

**The only way this class could ever count:** it is not actually a standalone source class. It collapses into class 4.1 or 4.4 above — a genuinely independent human or organization principal, with their own account, their own prompt-authoring, and their own selection of what to submit, who happens to choose an AI tool as part of how they produce their review. `docs/58` section 13 explicitly allows this: "An independent reviewer may use AI as tooling if the independent reviewer controls and adopts the review and source provenance closes." The independence comes from the human/organizational principal, never from the vendor name.

This spike records this class only as a warning against a specific false-positive pattern, not as an acceptable source class in its own right.

### 4.6 Existing paid third-party review SaaS already integrated in this repository (CodeRabbit)

**Current state, recovered from this repository's own evidence:** CodeRabbit is a commercial third-party AI review product from CodeRabbit, an entity distinct from and with no evidenced equity/personal relationship to the Owner. It is already integrated into this project's normal pull-request workflow — `docs/12-external-review-learning-loop.md` documents an explicit intake process for its comments, and `PICKUP.md` repeatedly records "CodeRabbit was green" as part of pre-merge proof for PR #159 and PR #165. Existing branches (`battle/coderabbit-t30` through `t34`, `fix/coderabbit-campaign-integrity`) show substantial prior operational history with this vendor.

**Sourcing to reach Genesis-grade use:** this is not "already solved" — `docs/01` and `docs/12` are explicit that "External reviewers are training material, not final authority" and that CodeRabbit's current role is teaching Main Review, not serving as an independent qualification authority. Its default product operation is ordinary PR-diff commentary (bugs, style, security patterns in a diff), not hostile qualification-grade adversarial attack against a frozen constitutional ACR/RAB specification document. Elevating it to a Genesis-lane candidate would require a new, explicit, scoped, paid engagement (if CodeRabbit or a comparable vendor offers a professional-services tier beyond default automated commentary) tasked specifically with attacking the Assurance Evolution specification's completeness, not merely commenting on a diff.

**Independence-proof approach:** CodeRabbit Inc. has no equity, personal, or repository-write relationship to the Owner beyond being a paying SaaS customer; the review methodology and prompting are CodeRabbit's own product logic, not Owner-authored; the billing relationship is an ordinary arm's-length commercial transaction; the specific hostile-qualification tasking (if pursued) would need to be documented as a distinct engagement separate from the vendor's default automated commentary, so that the EEPR record can attribute "who selected review inputs" correctly.

**Logistical honesty:** of every class analyzed, this is the one with the most existing operational relationship and the shortest realistic path to a first real engagement, precisely because the commercial relationship already exists. It is not yet a Genesis-grade hostile-qualification lane today — it is currently used, by this repository's own documented rule, as training material rather than qualification authority.

## 5. Independence / control-lineage criteria

A specific proposed reviewer arrangement is `INDEPENDENT` only if **all nine** of the following are true and evidenced.

1. The reviewer is a distinct legal or natural person who is not the Owner and is not an entity the Owner controls, is employed by, or holds equity in.
2. The reviewer has no financial dependency on the Owner beyond the specific arm's-length review engagement itself.
3. The reviewer has no undisclosed pre-existing personal relationship with the Owner that could bias findings.
4. The reviewer was not granted repository write or admin access as part of or before the review.
5. The reviewer authored or selected their own review approach, prompts, and inputs rather than being handed a fixed script or a predetermined conclusion by the Owner.
6. The reviewer used their own compute, account, and infrastructure rather than Owner-provisioned or Owner-configured infrastructure.
7. The reviewer, not the Owner, selected and controlled which findings were submitted as the final review output.
8. Any payment, reciprocal consideration, or engagement benefit was structured as compensation for performing the review, never contingent on reaching a particular verdict or outcome — this covers unpaid or reciprocal arrangements (section 4.2, 4.4) exactly the same way it covers a paid one: the requirement is outcome-independence, not the presence of money. An arrangement with no consideration at all trivially satisfies this criterion.
9. The engagement and deliverable are bound to an authenticated External Evidence Provenance Record satisfying `docs/58` section 13 before independence can be claimed rather than merely asserted.

**Disposition resolution is a strict precedence order, not three independent checks, because exactly one of the three states must result even when evidence is mixed** (for example, one criterion verified false and a separate criterion simply undocumented):

1. If **any** criterion is verified **false**, the disposition is `NOT_INDEPENDENT` — regardless of the state of any other criterion. A confirmed disqualifying fact always wins over an unrelated unknown.
2. Otherwise, if **any** criterion is unverifiable or undocumented, the disposition is `UNKNOWN_INDEPENDENCE`, consistent with `docs/58` section 13's "missing provenance is `UNKNOWN_INDEPENDENCE`." This includes the default state before any real arrangement exists, where all nine are simultaneously undocumented.
3. Only if **all nine** are verified **true** with evidence is the disposition `INDEPENDENT`.

Criterion 6 is the specific rule that closes the section 4.5 false-positive trap: an arrangement fails criterion 6 — and is therefore `NOT_INDEPENDENT` under precedence rule 1 — the moment the reviewing account, API key, or billing is Owner-controlled, regardless of which AI vendor answered the prompt, and regardless of whether other criteria remain unverified.

Criterion 9 is deliberately circular with section 6 below: this spike treats "we claim independence" and "we can produce an authenticated provenance record proving independence" as the same requirement. A claim without the record leaves criterion 9 undocumented, which — under precedence rule 2, and assuming no other criterion is affirmatively false — resolves to `UNKNOWN_INDEPENDENCE`.

## 6. Authentication/provenance route

Every evidence item counted toward the mandatory independent lane must carry an authenticated External Evidence Provenance Record (EEPR) per `docs/58` section 13's field list (evidence identity/digest, exact candidate/Review World, evidence-source principal identity, authenticated source provenance, source individual/organization, source authority generation, creation time/generation, relationship to candidate authoring lineage, relationship to qualification-corpus lineage, relationship to candidate-controlled infrastructure, reviewer/tool/model lineage where material, who controlled review prompt/instructions, who selected review inputs, who selected/accepted findings, provenance-verification method, independence disposition).

This spike proposes a concrete capture route, built from primitives already realistic for a project this size, without inventing new cryptographic infrastructure that does not yet exist:

1. **Submission channel binding.** The reviewer submits their deliverable through a channel that itself carries identity — for example a signed commit/tag from the reviewer's own GitHub account on a fork or a dedicated intake repository, a signed email (PGP/S-MIME), or a platform-authenticated submission (a freelance-marketplace deliverable page, a bounty-platform submission record) — never a copy-pasted document with no origin channel.
2. **Content-addressed hash binding.** The exact submitted artifact bytes are hashed (the same git-blob-SHA approach already used throughout this repository's Assurance Evolution proof fixtures, e.g. `tests/test_assurance_evolution_roadmap_freeze.py` and `tests/test_sae00_founding_authority_reference.py`) and that hash — not a mutable reference — becomes the EEPR's evidence identity.
3. **Trusted receipt time, not an author-supplied date.** The captured timestamp must be a time observed and recorded by a party other than the submitter — a receiving platform's own server-side event time (e.g. GitHub API `created_at` on the push/PR/comment event, not the git commit's author-supplied `--date`, which `git commit`'s own documentation describes as an overridable "override date for commit"), a bounty/marketplace platform's delivery-record timestamp, or, for the strongest available guarantee, an RFC 3161 trusted-timestamp obtained on the hashed artifact from an independent timestamping authority. An email `Date` header, even with DKIM verification, is explicitly **insufficient by itself**: DKIM authenticates that the sender's mail server transmitted that header value, not that the header's claimed time is true — a colluding or careless submitter can still backdate the visible date while DKIM still validates. Any author-supplied or client-side timestamp may be recorded as supplementary context, but only a receiver-observed or RFC-3161 time counts toward the EEPR's protection against backdating.
4. **Explicit control-lineage statement.** The reviewer (or the engaging party, cross-checked against the reviewer where possible) states in the deliverable itself, or in a companion attestation, who controlled the prompt/instructions, who selected the inputs reviewed, and who selected which findings were submitted — directly populating the three EEPR fields that most determine independence disposition.
5. **Reviewer identity/provenance-verification method recorded.** However identity was checked (business registration lookup, platform-verified account, institutional email/affiliation, in-person or video-call verification) is itself recorded as the EEPR's `provenance-verification method`, so a later reviewer of the reviewer can judge how strong that verification actually was rather than trusting an unstated method.
6. **Independence disposition assigned and justified.** The nine criteria in section 5 are evaluated explicitly against the captured evidence, and the resulting disposition (`INDEPENDENT` / `NOT_INDEPENDENT` / `UNKNOWN_INDEPENDENCE`) is recorded with the specific criterion evidence that supports it — not asserted as a bare label.

This route is intentionally implementation-agnostic about *identity technology* — it does not require a PKI, a DID system, or any specific signing scheme to exist first. `SPIKE-ID — Identity / authenticated provenance feasibility` (`docs/59` section 6) is the sibling spike chartered to design the deeper Qualification Authority identity/attestation mechanism that `SAE-30` will eventually formalize; this spike's route is deliberately the minimum viable capture discipline that would already produce a defensible EEPR using tools that exist today, and it is fully compatible with being strengthened once SPIKE-ID's mechanism exists. SPIKE-ID's own output was not available to read at the time this document was written (no committed content existed on its branch), so this document cites it by role and does not depend on any of its specific findings.

## 7. Expected mandatory external-review lane cardinality proposal

**Proposal: minimum 2, target 3, drawn from at least 2 distinct source classes (section 4.1 through 4.6, excluding 4.5).**

Reasoning:

- **One lane is fragile.** A single independent reviewer is a single point of failure: if that reviewer is later found to have been mistaken, incompetent, compromised, or — despite the control-lineage checklist — subtly non-independent in a way the checklist did not catch, the entire mandatory external lane collapses to nothing, and there is no way to distinguish "the architecture is sound" from "the one reviewer missed something" after the fact.
- **Two lanes establish a floor for cross-check.** A second independent lane lets a genuine finding be corroborated, or a spurious one be caught, without requiring a large or expensive review programme. This mirrors ordinary security-assurance practice, where a second opinion on critical findings is a common minimum bar.
- **Three lanes widen coverage rather than adjudicate by count.** This is deliberately not a voting mechanism: per `docs/58` section 1, evidence providers create facts, not verdict votes, and external reviewers remain witnesses, never Sergeant authority — a genuine finding reported by one lane and missed by the other two must still be admitted and reconciled by Judge/Sergeant on its own merits, exactly as if all three lanes had reported it. What a third lane buys is not tie-breaking power over the other two; it is additional independent coverage, reducing the probability that a real omission escapes every lane simultaneously. More lanes catching more distinct things is the goal — not lanes out-voting each other.
- **Diversity across source classes matters as much as raw count.** Two lanes purchased from the same firm, or two reviewers with overlapping training/background, can share correlated blind spots — this echoes `docs/58` section 11's "Different implementation language or tool name alone does not establish independence" principle applied to reviewer sourcing rather than tooling: two lanes from one source class are still each individually admissible, but they do not by themselves demonstrate the kind of perspective diversity that catching a genuinely novel omission is more likely to require. Requiring at least two distinct source classes among the minimum is this spike's concrete answer to that risk.
- **Realism bound.** This is a single-owner project (`THETECHGUY DIGITAL SOLUTIONS`, one git identity across the visible commit history) with no evidenced dedicated assurance budget. Proposing a large N (five, ten) would be qualification-theater unconnected to what section 8 below shows is realistically achievable; three genuinely independent lanes is already a meaningfully higher bar than this project has ever cleared for external review.

This is a **proposal**, not a binding law. `docs/59` section 6 asks SPIKE-EXT to produce "expected mandatory external-review lane cardinality proposal," and `docs/59` section 7 (`SAE-20`) explicitly charters the ACR Authoring Audit to include "mandatory external-review-lane-cardinality attacks" — the actual mandatory number is determined there, under full hostile review, not frozen unilaterally by this spike.

## 8. Sourcing/logistics disposition — honest result

**Disposition: open gap. No genuinely independent external-review source was found active or engaged for this project as of the live evidence captured for this spike (2026-09-02).** This is a bounded, dated claim about the evidence actually checked, not an unbounded assertion about the eternal present — per `AI_START_HERE.md`'s recovery requirement, "current" claims must bind to live-recovered state rather than an unverified general belief, so if a genuinely independent lane is engaged after this date, this disposition is stale for that new fact and must be re-checked against fresh live evidence before being relied on, exactly like any other Review-World-bound claim in this repository.

The evidence for this, gathered directly rather than assumed, all captured live during this spike's construction session:

- `.github/self-learning/cross-repository-sources.json`'s `confirmed_sources` list contains exactly three entries — `jaydumisuni/TechGuyCheckm8`, `jaydumisuni/lumi-dm`, `jaydumisuni/Oracle-` — and all three are explicitly tagged `"source_class": "thetechguy-owned"`. Every currently confirmed cross-repository learning source is owner-owned. None is independent by any definition in `docs/58` section 13.
- `docs/01-research-sources.md`'s KiloCode entry is explicit that the *owner-controlled mirror* (`jaydumisuni/kilocode`) is the practical inspection source, while the genuinely external upstream (`Kilo-Org/kilocode`) remains a donor-study subject, not a reviewer relationship — no actual engagement with upstream Kilo-Org maintainers is evidenced.
- `PICKUP.md`'s Oracle PR #150 disposition (section "The Oracle PR #150 candidate... is also rejected") is the closest precedent this project has to "AI review from a different account/vendor," and it was explicitly rejected — not for lacking a different vendor, but for overfitting and missing negative-control proof, and it was never claimed to be independent in the first place. It is direct precedent that a superficially different-looking review is not automatically a solved independence problem, reinforcing section 4.5's caution.
- The one relationship with real operational history and a distinct third-party commercial principal — CodeRabbit (section 4.6) — exists, but by this repository's own governing rule (`docs/12`) is currently scoped as review training material, not qualification authority, and no dedicated hostile-qualification engagement with it has been proposed to or agreed by the Owner.
- No evidence anywhere in this repository shows an existing paid contractor relationship, an existing academic collaboration, an existing bounty programme, or an existing independent-maintainer swap arrangement (section 4.1 through 4.4).
- A live check of this repository's own GitHub state, run directly rather than assumed: `gh api repos/jaydumisuni/Sergeant/contributors` returns exactly two accounts (`jaydumisuni` and `github-actions[bot]`); `gh api repos/jaydumisuni/Sergeant/collaborators` returns exactly one human account (`jaydumisuni`, with admin/maintain/push access); and the reviewer set across a sample of the twenty most recent pull requests contains no account other than `jaydumisuni` (the Owner), `coderabbitai` (bot, skipped by default on this repository's star count per its own PR comments), and `chatgpt-codex-connector` (bot). No independent human reviewer account appears anywhere in this repository's live, checkable GitHub state at capture time.

**Nearest practical path, in order of current relationship-readiness, if the Owner chooses to act on this analysis in the future (this spike does not initiate any of it):**

1. Elevate the existing CodeRabbit commercial relationship (section 4.6) to a distinct, explicitly scoped, paid hostile-qualification engagement against a frozen Assurance Evolution specification generation, with the EEPR capture route in section 6 applied from the start.
2. In parallel or afterward, engage one paid independent security/code-review contractor or firm (section 4.1) with no prior relationship to the Owner, to reach the two-distinct-source-class floor proposed in section 7.

Per `docs/59` section 6: "Failure to source a reviewer does not weaken the law: implementation may continue, but Genesis qualification cannot prove." This spike reports that failure honestly rather than manufacturing a false positive. `SAE-30`, which formally requires this spike per `docs/59` section 15, may proceed to build the qualification/provenance substrate itself — that substrate's existence does not require a reviewer to already be engaged — but `SAE-150` (Integrated Genesis Qualification Campaign) cannot close its mandatory independent lane until a real arrangement satisfying section 5's nine criteria actually exists and is captured through section 6's route.

## 9. What this spike does not establish

Stated explicitly, to prevent this analysis from being misread later as more than it is:

- It does not establish that any source class **currently** satisfies `INDEPENDENT` disposition — no real arrangement exists yet to evaluate.
- It does not claim CodeRabbit, or any other class in section 4, has already produced independent evidence. CodeRabbit's current role, by this repository's own rule, remains training material.
- It does not claim that using a different AI vendor or account, by itself, ever satisfies independence — section 4.5 and criterion 6 exist specifically to foreclose that false positive.
- It does not contract, hire, contact, or otherwise engage any real external reviewer, contractor, academic, bounty participant, or maintainer. No outreach occurred while producing this document.
- It does not change SAE-30's, SAE-150's, or any other programme's proof dependencies, obligations, or authority boundaries defined in `docs/59`.
- It does not grant any normal Sergeant verdict authority, per `docs/59` section 6's explicit "Authority gain: none."

## 10. Recovery statement for a future zero-context agent

A future zero-context agent has correctly recovered SPIKE-EXT when it can state: this spike's proof formally requires `SAE-00`, which had not yet merged to canonical `main` at the time this spike was written, so this spike's own lifecycle state cannot exceed `CANDIDATE`/`REVIEWED`; six source classes were analyzed, of which the sixth (an existing CodeRabbit commercial relationship) is the most logistically ready and the fifth (a different Owner-controlled AI vendor account) is explicitly *not* an acceptable independent source by itself; nine independence/control-lineage criteria determine `INDEPENDENT` / `NOT_INDEPENDENT` / `UNKNOWN_INDEPENDENCE` disposition for any specific proposed arrangement; a concrete, tool-agnostic EEPR capture route was proposed and is compatible with but not blocked on SPIKE-ID; a minimum-2/target-3/two-distinct-source-classes cardinality was proposed for `SAE-20`'s ACR Authoring Audit to formally set; and the honest sourcing disposition is an **open gap** — no genuinely independent external-review source is currently engaged for this project, and this spike did not attempt to change that, per its explicit scope boundary.
