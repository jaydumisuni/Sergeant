# Full Cloudflare council certification assurance

Assured path: `.github/workflows/cloudflare-full-council-certification.yml`

## Purpose

The workflow performs exact-head live admission proof for every unique Cloudflare
Workers AI member in Sergeant's public council roster without restarting the whole
exam after a provider quota interruption.

Each member receives one role-appropriate mission:

- six reasoning and coding members complete the evidence-grounded security officer
  mission;
- Granite 4.0 H Micro completes a Scout evidence-extraction mission with exact
  values, file coverage and line evidence.

A parseable role-mission response proves structured transport. The workflow does
not spend a second model call on a redundant handshake before the real mission.

The workflow is a certification gate. It does not review arbitrary repositories,
run pull-request-controlled project code, apply patches, publish releases or grant
models any repository authority.

## Resumable exact-head ledger

The workflow preserves two credential-safe JSON records as a GitHub Actions artifact:

- `full-council-ledger.json` stores member proof by exact commit and contract version;
- `cloudflare-usage-state.json` stores conservative daily neuron reservations and the
  provider quota-circuit state.

At the beginning of a later run, Sergeant restores the newest ledger artifact.
Passing members from the same exact head and contract are skipped. A changed commit
or changed certification contract invalidates the member passes and creates a fresh
ledger. Daily usage state is retained independently so repeated commits cannot keep
probing an already exhausted account.

After every member, the ledger is written before the next member begins. A runner or
quota interruption therefore preserves all earlier successful proof.

## Quota and budget behavior

Sergeant reserves a conservative neuron estimate before every Cloudflare inference
request. The estimate uses the public per-model input/output neuron rates recorded in
`main_review/cloudflare_models.py`, the bounded input size and the maximum output
budget. Models without a recorded public rate use an explicit conservative fallback
reservation.

Public configuration variables:

- `SERGEANT_CLOUDFLARE_DAILY_BUDGET_NEURONS` — local daily ceiling; default `10000`;
- `SERGEANT_CLOUDFLARE_SAFETY_RESERVE_NEURONS` — capacity kept outside this Sergeant
  workflow; default `2500`;
- `SERGEANT_CLOUDFLARE_UNKNOWN_MODEL_RESERVATION_NEURONS` — reservation for a model
  without published rates; default `2500`;
- `SERGEANT_CLOUDFLARE_USAGE_STATE` — persistent state-file location;
- `SERGEANT_CLOUDFLARE_USAGE_GOVERNOR` — explicit governor enable/disable switch.

If the next request would exceed the local daily budget, Sergeant stops before any
network request. When Cloudflare returns HTTP `429` / provider code `4006`, Sergeant:

1. opens the quota circuit until the next UTC day;
2. does not retry the same model through another API shape;
3. does not fail over through the remaining model roster;
4. records the current member as quota-blocked rather than model-failed;
5. uploads the completed ledger so the next run resumes only missing members.

Quota blocking proves neither model success nor model failure.

## Permissions

The workflow declares:

- `contents: read` for exact-head checkout;
- `actions: read` to restore its own earlier credential-safe ledger artifact.

Checkout uses `persist-credentials: false`, so the GitHub token is not retained in
the repository configuration. The workflow cannot push commits, create comments,
modify pull requests, dispatch deployments, publish packages or merge changes.

Every model call is initiated by Sergeant's allowlisted Cloudflare connector. The
models receive bounded fixture text and cannot invoke shell commands, network tools
or repository writes.

## Secrets

The live proof reads these operator-owned GitHub Actions secrets:

- `SERGEANT_CLOUDFLARE_ACCOUNT_ID`;
- `SERGEANT_CLOUDFLARE_API_TOKEN`.

They are used only to construct the Cloudflare Workers AI route. They are never
written to Git, passed as command-line arguments or copied into the public summary.
Before artifact upload, the workflow scans the summary, certification ledger and
usage state for both configured secret values. Evidence upload is allowed only when
that scan succeeds.

Public status output masks the Account ID and reports credential presence as
booleans.

## Rollback

Rollback removes:

- `.github/workflows/cloudflare-full-council-certification.yml`;
- `main_review/cloudflare_incremental_certification.py`;
- `main_review/cloudflare_scout_qualification.py`;
- `main_review/cloudflare_usage.py`;
- the full-roster compatibility additions in `main_review/cloudflare_cli.py`,
  `main_review/cloudflare_models.py` and `main_review/llm_provider.py`;
- the full-roster, incremental-ledger and usage-governor tests;
- the Qwen2.5 proof-budget expectation in
  `tests/test_cloudflare_native_fallback.py`;
- this assurance document.

The two-member mission-qualified baseline, deterministic Sergeant Core, permanent
officers, provider-neutral Cpl routing and all non-Cloudflare routes remain usable
after rollback.

## Proof

The change is acceptable only when all of the following are true:

1. focused compatibility, usage-governor and incremental-ledger tests pass;
2. the complete repository test suite passes;
3. normal CI, Main Review, Review Intelligence, Reviewer Comparison, Live GitHub
   Ingestion, Standalone Service, Cloudflare Connector and Multiplatform proofs pass;
4. the Cloudflare route validates without exposing credentials;
5. every member has a role-mission result on the same exact candidate head;
6. the role mission proves structured transport for seven of seven members;
7. the six reasoning/coding members pass their complete officer mission;
8. Granite passes the grounded Scout evidence-extraction mission;
9. the final certified roster contains all seven unique members;
10. the credential scan succeeds before artifact upload;
11. the artifact records the exact tested commit and contains no configured secret;
12. a synthetic 429 test proves one network attempt only and a persistent circuit;
13. a synthetic local-budget test proves no network request is sent.

The workflow remains incomplete when the provider quota or local budget blocks it.
The exact-head ledger must resume after capacity becomes available; it must not rerun
already certified members.

## Operational cost boundary

The seven-member live proof is required only for roster, transport or certification-
contract changes. Ordinary Sergeant pull requests use the already certified default
formation and recruit additional members only for a real evidence gap.

This governor is the direct Sergeant protection layer. Private shared Hunter/Sergeant
accounting, cross-service reservations and paid-provider routing remain a later
private gateway responsibility and must not be claimed from this public workflow.
