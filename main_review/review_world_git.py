"""SAE-10 Git fact derivation for Review Worlds."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, os, subprocess
from pathlib import Path
from typing import Literal, Protocol, Sequence
from main_review.review_world import GitHubDiffIdentity, GitHubReviewWorld, LocalReviewWorld, ReviewScope, ReviewWorldError, require_full_sha256, require_git_object_id, sha256_id

class GitCommandError(ReviewWorldError):
    pass

class GitObjectResolverProtocol(Protocol):

    def tree_for_commit(self, commit: str) -> str:
        ...

    def synthetic_merge(self, base: str, head: str) -> str:
        ...

class GitObjectResolver:

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _run(self, *args: str) -> str:
        try:
            c = subprocess.run(['git', *args], cwd=self.root, text=True, capture_output=True, check=False)
        except OSError as e:
            raise GitCommandError(f'git command unavailable: {e}') from e
        if c.returncode != 0:
            detail = (c.stderr or c.stdout).strip()
            raise GitCommandError(f"git {' '.join(args)} failed with exit {c.returncode}: {detail or 'no diagnostic'}")
        return c.stdout.strip()

    def _run_bytes(self, *args: str) -> bytes:
        try:
            c = subprocess.run(['git', *args], cwd=self.root, capture_output=True, check=False)
        except OSError as e:
            raise GitCommandError(f'git command unavailable: {e}') from e
        if c.returncode != 0:
            detail = (c.stderr or c.stdout).decode('utf-8', errors='replace').strip()
            raise GitCommandError(f"git {' '.join(args)} failed with exit {c.returncode}: {detail or 'no diagnostic'}")
        return c.stdout

    def tree_for_commit(self, commit: str) -> str:
        commit = require_git_object_id(commit, 'commit')
        out = self._run('rev-parse', f'{commit}^{{tree}}')
        lines = [x.strip() for x in out.splitlines() if x.strip()]
        if len(lines) != 1:
            raise GitCommandError('git rev-parse returned ambiguous tree identity')
        return require_git_object_id(lines[0], 'commit_tree')

    def synthetic_merge(self, base: str, head: str) -> str:
        base = require_git_object_id(base, 'merge_base')
        head = require_git_object_id(head, 'merge_head')
        out = self._run('merge-tree', '--write-tree', base, head)
        lines = [x.strip() for x in out.splitlines() if x.strip()]
        if len(lines) != 1:
            raise GitCommandError('git merge-tree returned ambiguous merge-result identity')
        return require_git_object_id(lines[0], 'merge_tree')

def build_github_review_world(*, repository: str, pr_number: int, base_sha: str, head_sha: str, scope: ReviewScope, review_mode: str, rab_id: str, review_generation: str, resolver: GitObjectResolverProtocol) -> GitHubReviewWorld:
    base_sha = require_git_object_id(base_sha, 'base_sha')
    head_sha = require_git_object_id(head_sha, 'head_sha')
    bt = resolver.tree_for_commit(base_sha)
    ht = resolver.tree_for_commit(head_sha)
    diff = GitHubDiffIdentity.create(repository=repository, base_commit=base_sha, base_tree=bt, head_commit=head_sha, head_tree=ht, scope=scope)
    mt = resolver.synthetic_merge(base_sha, head_sha) if review_mode == 'merge_result' else None
    return GitHubReviewWorld.create(repository=repository, pr_number=pr_number, diff=diff, scope=scope, review_mode=review_mode, rab_id=rab_id, review_generation=review_generation, merge_tree=mt)

def build_github_review_world_from_diff(pull_request_diff: object, *, scope: ReviewScope, review_mode: str, rab_id: str, review_generation: str, resolver: GitObjectResolverProtocol) -> GitHubReviewWorld:
    try:
        repository = str(getattr(pull_request_diff, 'repository'))
        pr_number = int(getattr(pull_request_diff, 'pr_number'))
        base_sha = str(getattr(pull_request_diff, 'base_sha'))
        head_sha = str(getattr(pull_request_diff, 'head_sha'))
    except (AttributeError, TypeError, ValueError) as e:
        raise GitCommandError('pull-request diff transport facts are incomplete') from e
    return build_github_review_world(repository=repository, pr_number=pr_number, base_sha=base_sha, head_sha=head_sha, scope=scope, review_mode=review_mode, rab_id=rab_id, review_generation=review_generation, resolver=resolver)

def _normalize_policy_paths(paths: Sequence[str]) -> tuple[str, ...]:
    return () if not paths else ReviewScope.selected_paths(paths).paths

@dataclass(frozen=True)
class LocalSnapshotPolicy:
    untracked_policy: Literal['exclude_untracked', 'include_selected_untracked', 'include_all_untracked_in_scope']
    lfs_state: Literal['pointer_identity_only', 'material_required'] = 'pointer_identity_only'
    generated_state: Literal['not_material', 'bound', 'material_unbound'] = 'not_material'
    generated_binding_id: str | None = None
    selected_untracked: tuple[str, ...] = ()
    submodule_state: Literal['gitlink_only', 'material_required'] = 'material_required'

    def __post_init__(self) -> None:
        if self.untracked_policy not in {'exclude_untracked', 'include_selected_untracked', 'include_all_untracked_in_scope'}:
            raise GitCommandError('invalid untracked snapshot policy')
        if self.lfs_state not in {'pointer_identity_only', 'material_required'}:
            raise GitCommandError('invalid LFS snapshot policy')
        if self.generated_state not in {'not_material', 'bound', 'material_unbound'}:
            raise GitCommandError('invalid generated-state snapshot policy')
        if self.submodule_state not in {'gitlink_only', 'material_required'}:
            raise GitCommandError('invalid submodule snapshot policy')
        normalized = _normalize_policy_paths(self.selected_untracked)
        object.__setattr__(self, 'selected_untracked', normalized)
        if self.untracked_policy == 'include_selected_untracked' and (not normalized):
            raise GitCommandError('selected-untracked policy requires explicit paths')
        if self.untracked_policy != 'include_selected_untracked' and normalized:
            raise GitCommandError('selected_untracked paths require include_selected_untracked policy')
        if self.generated_state == 'bound':
            object.__setattr__(self, 'generated_binding_id', require_full_sha256(str(self.generated_binding_id or ''), 'generated_binding_id'))
        elif self.generated_binding_id is not None:
            raise GitCommandError('generated_binding_id is only valid for bound generated state')

    @classmethod
    def exclude_untracked(cls):
        return cls(untracked_policy='exclude_untracked')

    @classmethod
    def include_all_untracked_in_scope(cls):
        return cls(untracked_policy='include_all_untracked_in_scope')

    @classmethod
    def include_selected_untracked(cls, paths: Sequence[str]):
        return cls(untracked_policy='include_selected_untracked', selected_untracked=tuple(paths))

    def to_payload(self) -> dict[str, object]:
        return {'untracked_policy': self.untracked_policy, 'selected_untracked': list(self.selected_untracked), 'lfs_state': self.lfs_state, 'generated_state': self.generated_state, 'generated_binding_id': self.generated_binding_id, 'submodule_state': self.submodule_state}

@dataclass(frozen=True)
class LocalPathState:
    path: str
    object_kind: str
    index_mode: str | None
    index_oid: str | None
    worktree_sha256: str | None
    state: str
    symlink_target: str | None = None
    submodule_commit: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {'path': self.path, 'object_kind': self.object_kind, 'index_mode': self.index_mode, 'index_oid': self.index_oid, 'worktree_sha256': self.worktree_sha256, 'state': self.state, 'symlink_target': self.symlink_target, 'submodule_commit': self.submodule_commit}

@dataclass(frozen=True)
class LocalSnapshot:
    schema_version: str
    head_commit: str
    head_tree: str
    scope: ReviewScope
    policy: LocalSnapshotPolicy
    entries: tuple[LocalPathState, ...]
    selected_scope_digest: str
    local_snapshot_id: str

    def to_payload(self, *, include_id: bool=True) -> dict[str, object]:
        p = {'schema_version': self.schema_version, 'head_commit': self.head_commit, 'head_tree': self.head_tree, 'scope': self.scope.to_payload(), 'policy': self.policy.to_payload(), 'entries': [e.to_payload() for e in self.entries], 'selected_scope_digest': self.selected_scope_digest}
        if include_id:
            p['local_snapshot_id'] = self.local_snapshot_id
        return p

def _decode_git_path(raw: bytes) -> str:
    try:
        path = raw.decode('utf-8')
    except UnicodeDecodeError as e:
        raise GitCommandError('local Review World cannot canonically encode non-UTF-8 Git path') from e
    return ReviewScope.selected_paths([path]).paths[0]

def _path_in_scope(path: str, scope: ReviewScope) -> bool:
    if scope.kind == 'repository':
        return True
    return any((path == s or path.startswith(s.rstrip('/') + '/') for s in scope.paths))

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def _is_lfs_pointer(path: Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        with path.open('rb') as f:
            prefix = f.read(512)
    except OSError:
        return False
    return prefix.startswith(b'version https://git-lfs.github.com/spec/v1\n') and b'\noid sha256:' in prefix

def _parse_nul_paths(raw: bytes) -> set[str]:
    return {_decode_git_path(x) for x in raw.split(b'\x00') if x}

def _index_entries(resolver: GitObjectResolver, scope: ReviewScope) -> list[tuple[str, str, str]]:
    entries = []
    for record in resolver._run_bytes('ls-files', '-s', '-z').split(b'\x00'):
        if not record:
            continue
        try:
            meta, raw_path = record.split(b'\t', 1)
            mode_raw, oid_raw, stage_raw = meta.split(b' ', 2)
            mode = mode_raw.decode('ascii')
            oid = require_git_object_id(oid_raw.decode('ascii'), 'index_oid')
            stage = stage_raw.decode('ascii')
        except (ValueError, UnicodeDecodeError, ReviewWorldError) as e:
            raise GitCommandError('git index entry is malformed or ambiguous') from e
        if stage != '0':
            raise GitCommandError('unmerged index stage prevents exact local snapshot')
        path = _decode_git_path(raw_path)
        if _path_in_scope(path, scope):
            entries.append((mode, oid, path))
    return entries

def _submodule_state(root: Path, path: str, index_oid: str, policy: LocalSnapshotPolicy) -> LocalPathState:
    subroot = root / path
    if policy.submodule_state == 'gitlink_only':
        return LocalPathState(path, 'submodule', '160000', index_oid, None, 'gitlink_only', submodule_commit=index_oid)
    if not subroot.is_dir():
        raise GitCommandError(f'submodule material unavailable for {path}')
    resolver = GitObjectResolver(subroot)
    try:
        commit = require_git_object_id(resolver._run('rev-parse', 'HEAD'), 'submodule_commit')
        status = resolver._run('status', '--porcelain=v1')
    except ReviewWorldError as e:
        raise GitCommandError(f'submodule material unresolved for {path}: {e}') from e
    if commit != index_oid or status:
        raise GitCommandError(f'submodule material unresolved/dirty for {path}')
    return LocalPathState(path, 'submodule', '160000', index_oid, None, 'unchanged', submodule_commit=commit)

def build_local_snapshot(root: str | Path, *, scope: ReviewScope, policy: LocalSnapshotPolicy) -> LocalSnapshot:
    root = Path(root)
    resolver = GitObjectResolver(root)
    if policy.generated_state == 'material_unbound':
        raise GitCommandError('generated material is declared but has no exact binding')
    head_commit = require_git_object_id(resolver._run('rev-parse', '--verify', 'HEAD'), 'head_commit')
    head_tree = resolver.tree_for_commit(head_commit)
    modified = _parse_nul_paths(resolver._run_bytes('diff-files', '--name-only', '-z'))
    staged = _parse_nul_paths(resolver._run_bytes('diff-index', '--cached', '--name-only', '-z', 'HEAD', '--'))
    states = []
    for mode, oid, path in _index_entries(resolver, scope):
        absolute = root / path
        if mode == '160000':
            states.append(_submodule_state(root, path, oid, policy))
            continue
        if not absolute.exists() and (not absolute.is_symlink()):
            states.append(LocalPathState(path, 'tracked', mode, oid, None, 'deleted'))
            continue
        state = 'modified' if path in modified or path in staged else 'unchanged'
        if absolute.is_symlink():
            target = os.readlink(absolute)
            digest = hashlib.sha256(target.encode('utf-8')).hexdigest()
            states.append(LocalPathState(path, 'symlink', mode, oid, digest, state, symlink_target=target))
            continue
        if not absolute.is_file():
            raise GitCommandError(f'unsupported tracked worktree object for exact snapshot: {path}')
        if policy.lfs_state == 'material_required' and _is_lfs_pointer(absolute):
            raise GitCommandError(f'LFS material required but only pointer identity is available for {path}')
        states.append(LocalPathState(path, 'file', mode, oid, _sha256_file(absolute), state))
    untracked = _parse_nul_paths(resolver._run_bytes('ls-files', '--others', '-z'))
    for path in sorted(untracked):
        if not _path_in_scope(path, scope):
            continue
        include = policy.untracked_policy == 'include_all_untracked_in_scope'
        if policy.untracked_policy == 'include_selected_untracked':
            include = path in policy.selected_untracked
        if not include:
            continue
        absolute = root / path
        if absolute.is_symlink():
            target = os.readlink(absolute)
            digest = hashlib.sha256(target.encode('utf-8')).hexdigest()
            states.append(LocalPathState(path, 'symlink', None, None, digest, 'untracked', symlink_target=target))
        elif absolute.is_file():
            if policy.lfs_state == 'material_required' and _is_lfs_pointer(absolute):
                raise GitCommandError(f'LFS material required but only pointer identity is available for {path}')
            states.append(LocalPathState(path, 'file', None, None, _sha256_file(absolute), 'untracked'))
        else:
            raise GitCommandError(f'unsupported untracked object for exact snapshot: {path}')
    states.sort(key=lambda x: x.path)
    scope_payload = {'scope_id': scope.scope_id, 'policy': policy.to_payload(), 'entries': [e.to_payload() for e in states]}
    selected_scope_digest = sha256_id(scope_payload)
    body = {'schema_version': 'sergeant.local-snapshot.v1', 'head_commit': head_commit, 'head_tree': head_tree, 'scope': scope.to_payload(), 'policy': policy.to_payload(), 'entries': [e.to_payload() for e in states], 'selected_scope_digest': selected_scope_digest}
    return LocalSnapshot('sergeant.local-snapshot.v1', head_commit, head_tree, scope, policy, tuple(states), selected_scope_digest, sha256_id(body))

def build_local_review_world(root: str | Path, *, repository: str | None, scope: ReviewScope, policy: LocalSnapshotPolicy, rab_id: str, review_generation: str) -> tuple[LocalSnapshot, LocalReviewWorld]:
    snapshot = build_local_snapshot(root, scope=scope, policy=policy)
    world = LocalReviewWorld.create(repository=repository, local_snapshot_id=snapshot.local_snapshot_id, scope=scope, rab_id=rab_id, review_generation=review_generation)
    return (snapshot, world)
