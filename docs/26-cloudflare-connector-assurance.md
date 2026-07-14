# Cloudflare connector workflow assurance

Assured path: `.github/workflows/cloudflare-connector-proof.yml`

## Purpose

The workflow proves the public Cloudflare connector without contacting a live
provider or requiring private credentials. It runs focused gateway tests,
credential-redaction checks, source packaging and installed-wheel execution.

## Permissions

The workflow declares `contents: read`. It does not request pull-request write,
issues write, actions write, deployments write, packages write or identity-token
permissions. It does not publish releases or mutate repository state.

## Secrets

The pull-request workflow receives no Cloudflare Account ID or API token. The
proof intentionally checks behavior when credentials are absent and verifies
that public status output contains only boolean presence indicators. Live
Workers AI tests are performed separately with operator-owned secrets stored
outside Git and outside public workflow logs.

## Rollback

Rollback removes:

- `.github/workflows/cloudflare-connector-proof.yml`;
- `main_review/cloudflare_gateway.py`;
- `main_review/cloudflare_cli.py`;
- the `sergeant-cloudflare` package entrypoint;
- Cloudflare-specific tests and documentation.

Deterministic Sergeant Core, existing Cpl routes and all other workflows remain
operational after rollback.

## Proof

Required proof is:

1. focused `tests/test_cloudflare_gateway.py` passes;
2. missing-credential status exits with the required failure code;
3. no token value appears in status artifacts;
4. source and wheel packages build;
5. the installed wheel exposes `sergeant-cloudflare`;
6. existing Sergeant CI, Main Review, standalone, intelligence, ingestion and
   multiplatform workflows remain green.

A separate live certification is required before claiming that a Cloudflare
reasoning council is operational. That certification must record multiple real
model calls and `true_model_independence: true` without exposing secrets.
