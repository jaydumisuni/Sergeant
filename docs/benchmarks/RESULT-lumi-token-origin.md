# Result: Lumi extension token-origin benchmark

Status: failed differential benchmark; do not merge.

Real repository and code:

```text
repository: jaydumisuni/lumi-dm
file: browser-extension/security-shim.js
pre-fix commit: 8f63f832112a2e0772e954c3e0319109ce21b6a9
verified fixing commit: a8d572258a4d53e9620970e5236ab21aa903580f
```

Ground truth after the blind report was frozen:

The pre-fix extension attached its bearer token to any loopback-host `/api/` request. The fixing commit changed the boundary to require the request origin to exactly equal the configured Lumi server origin before attaching the token.

Sergeant result without a configured model route:

```text
pre-fix verdict: REQUEST_CHANGES
fixed-control verdict: REQUEST_CHANGES
pre-fix admitted finding: Implementation changed without changed tests in the same PR.
fixed-control admitted finding: Implementation changed without changed tests in the same PR.
report digest before: 8702812917919c2a3bbdc9719dd53e6a14f507888f8b480366fa305d1ed78373
report digest after:  8702812917919c2a3bbdc9719dd53e6a14f507888f8b480366fa305d1ed78373
```

Disposition:

- Sergeant did not identify the real token-origin security defect.
- Sergeant did not distinguish the vulnerable state from the fixed control.
- The generic missing-tests finding applied equally to both repository snapshots and is not evidence that the security defect was found.
- The benchmark therefore disproves any claim that current model-free Sergeant is sufficient by itself for subtle JavaScript authentication-boundary review.
- No lesson is automatically admitted, no production detector is changed, and this benchmark branch must remain unmerged.
