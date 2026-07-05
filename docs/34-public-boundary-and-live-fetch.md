# Public Boundary and Live GitHub Fetch

Sergeant is public/open-source review infrastructure.

It can be used inside THETECHGUY/Hunter, but private project rules, private memories, customer evidence, and deployment secrets must stay outside the public repository.

## Public-safe capability

`main_review/github_live_fetch.py` adds read-only live GitHub PR comment fetching.

It is intentionally separate from `github_collector.py`:

- `github_collector.py` stays a pure parser.
- `github_live_fetch.py` is the only built-in module that performs GitHub network fetches.

## Security boundary

Allowed:

- read-only public API fetch
- optional read-only token
- static review
- external evidence ingestion
- verified learning from human outcomes

Refused:

- running pull-request supplied project code during review
- running shell commands from PR content
- using write tokens during analysis
- silently converting fetch failures into empty comments
- writing patches as part of review

## CLI

```bash
main-review live-github-comments jaydumisuni/Sergeant 1 --pretty
main-review boundary run_untrusted_code --pretty
main-review visibility-policy --pretty
```

## Honest testing claim

Secret detection is proven by a planted temp-file positive case.

GitHub PR ingestion now has two layers:

1. network-free payload parsing through `github_collector.py`
2. optional read-only live API fetching through `github_live_fetch.py`

CI tests mock the live network layer because real GitHub calls are rate-limit and network dependent.