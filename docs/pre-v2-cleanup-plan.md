# Sergeant Pre-V2 Cleanup Plan

Status: prepared after v1 release and branch protection.

## Goal

Move from the messy post-v1 branch state into a clean V2 development baseline without losing the released work or the lessons learned from the messy branch history.

## Current protected baseline

Keep:

- `main` — released and protected v1 baseline.
- `v1` — release tag.
- `v2-lab` — clean future V2 work branch.
- `archive/all-pre-v2-branch-history` — archive marker created before deleting noisy branches.

## Important limitation

A single Git branch can only point to one commit. It cannot preserve every old branch tip by itself.

So `archive/all-pre-v2-branch-history` is a repository marker, not a full bundle of every deleted branch. If full recovery of every branch tip is required before deletion, create a local Git bundle first.

Recommended full local archive command:

```bash
git fetch --all --tags
git bundle create sergeant-pre-v2-all-refs.bundle --all --tags
```

Verify the bundle:

```bash
git bundle verify sergeant-pre-v2-all-refs.bundle
```

## Lesson learned

The old branch list contained signs of retry-loop development:

- repeated numbered feature branches
- branches named with `ignore`, `loop`, `mistake`, `stop`, and similar language
- multiple near-duplicate attempts at the same feature

The lesson is not to preserve that workflow. The lesson is to prevent it happening again.

Future rule:

> If a tool or agent creates repeated failed branches, stop branching, audit the current state, preserve one archive point, and continue only from a clean branch.

## Clean future branch policy

Allowed branch families:

- `feature/...`
- `fix/...`
- `docs/...`
- `release/...`
- `v2-lab/...`
- `archive/...`

Avoid:

- emotional branch names
- repeated numbered retries without review
- `ignore`, `mistake`, `loop`, `noop`, or temporary names on remote

## Cleanup path

1. Create local full bundle if old branch recovery matters.
2. Keep `main`, `v1`, `v2-lab`, and the archive marker.
3. Delete noisy remote branches from GitHub UI or local terminal.
4. Start all V2 work from `v2-lab`.

## Safe deletion command pattern

After local bundle verification, delete a remote branch with:

```bash
git push origin --delete branch-name
```

Do not delete `main`, `v1`, `v2-lab`, or `archive/all-pre-v2-branch-history`.
