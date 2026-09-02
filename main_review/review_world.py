"""SAE-10 canonical Review World authority contracts."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Literal, Mapping, Sequence
_AUTH_SHA256_RE = re.compile('^[0-9a-f]{64}$')
_GIT_OID_RE = re.compile('^(?:[0-9a-f]{40}|[0-9a-f]{64})$')
_REPOSITORY_RE = re.compile('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
_SCOPE_KINDS = {'repository', 'changed_files', 'selected_paths'}
_REVIEW_MODES = {'head', 'merge_result'}

class ReviewWorldError(ValueError):
    pass

def _validate_json_value(value: object, *, path: str='$') -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ReviewWorldError(f'canonical JSON rejects non-finite number at {path}')
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ReviewWorldError(f'canonical JSON requires string object keys at {path}')
            _validate_json_value(nested, path=f'{path}.{key}')
        return
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _validate_json_value(nested, path=f'{path}[{index}]')
        return
    raise ReviewWorldError(f'canonical JSON rejects unsupported value at {path}: {type(value).__name__}')

def canonical_json_bytes(value: Mapping[str, object]) -> bytes:
    if not isinstance(value, Mapping):
        raise ReviewWorldError('canonical JSON root must be an object')
    _validate_json_value(value)
    try:
        rendered = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ReviewWorldError(f'canonical JSON encoding failed: {error}') from error
    return rendered.encode('utf-8')

def sha256_id(value: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()

def require_full_sha256(value: str, field: str) -> str:
    candidate = str(value or '')
    if not _AUTH_SHA256_RE.fullmatch(candidate):
        raise ReviewWorldError(f'{field} must be a full lowercase 64-hex SHA-256 digest')
    return candidate

def require_git_object_id(value: str, field: str) -> str:
    candidate = str(value or '')
    if not _GIT_OID_RE.fullmatch(candidate):
        raise ReviewWorldError(f'{field} must be a full lowercase 40-hex or 64-hex Git object id')
    return candidate

def normalize_repository_identity(repository: str) -> str:
    candidate = str(repository or '').strip()
    if not _REPOSITORY_RE.fullmatch(candidate):
        raise ReviewWorldError('repository identity must be owner/name')
    return candidate.lower()

def _expect_keys(payload: Mapping[str, object], required: set[str], *, optional: set[str]=set(), label: str) -> None:
    keys = set(payload)
    missing = required - keys
    extra = keys - required - optional
    if missing:
        raise ReviewWorldError(f'{label} missing required fields: {sorted(missing)!r}')
    if extra:
        raise ReviewWorldError(f'{label} has unexpected fields: {sorted(extra)!r}')

def _normalize_repo_path(path: str) -> str:
    candidate = str(path or '')
    if not candidate or '\x00' in candidate or '\\' in candidate or candidate.startswith('/'):
        raise ReviewWorldError(f'path must be normalized repository-relative: {candidate!r}')
    parts = candidate.split('/')
    if any((part in {'', '.', '..'} for part in parts)):
        raise ReviewWorldError(f'path must be normalized repository-relative: {candidate!r}')
    return '/'.join(parts)

@dataclass(frozen=True)
class ReviewScope:
    schema_version: str
    kind: Literal['repository', 'changed_files', 'selected_paths']
    paths: tuple[str, ...]
    generated_artifacts: Literal['excluded', 'included', 'unresolved']
    submodules: Literal['excluded', 'included', 'unresolved']
    untracked: Literal['excluded', 'selected', 'all_in_scope', 'unresolved']
    generation: str
    scope_id: str

    @classmethod
    def _create(cls, *, kind: str, paths: Sequence[str], generated_artifacts: str='excluded', submodules: str='excluded', untracked: str='excluded', generation: str='scope-v1') -> 'ReviewScope':
        if kind not in _SCOPE_KINDS:
            raise ReviewWorldError(f'unknown scope kind: {kind!r}')
        normalized = tuple(sorted({_normalize_repo_path(path) for path in paths}))
        if kind == 'repository' and normalized:
            raise ReviewWorldError('repository scope cannot carry selected paths')
        if kind != 'repository' and (not normalized):
            raise ReviewWorldError(f'{kind} scope requires at least one repository-relative path')
        if generated_artifacts not in {'excluded', 'included', 'unresolved'}:
            raise ReviewWorldError('invalid generated-artifacts scope policy')
        if submodules not in {'excluded', 'included', 'unresolved'}:
            raise ReviewWorldError('invalid submodule scope policy')
        if untracked not in {'excluded', 'selected', 'all_in_scope', 'unresolved'}:
            raise ReviewWorldError('invalid untracked scope policy')
        if not generation:
            raise ReviewWorldError('scope generation must be non-empty')
        body = {'schema_version': 'sergeant.review-scope.v1', 'kind': kind, 'paths': list(normalized), 'generated_artifacts': generated_artifacts, 'submodules': submodules, 'untracked': untracked, 'generation': generation}
        return cls('sergeant.review-scope.v1', kind, normalized, generated_artifacts, submodules, untracked, generation, sha256_id(body))

    @classmethod
    def repository(cls) -> 'ReviewScope':
        return cls._create(kind='repository', paths=())

    @classmethod
    def changed_files(cls, paths: Sequence[str]) -> 'ReviewScope':
        return cls._create(kind='changed_files', paths=paths)

    @classmethod
    def selected_paths(cls, paths: Sequence[str]) -> 'ReviewScope':
        return cls._create(kind='selected_paths', paths=paths)

    def to_payload(self, *, include_id: bool=True) -> dict[str, object]:
        payload = {'schema_version': self.schema_version, 'kind': self.kind, 'paths': list(self.paths), 'generated_artifacts': self.generated_artifacts, 'submodules': self.submodules, 'untracked': self.untracked, 'generation': self.generation}
        if include_id:
            payload['scope_id'] = self.scope_id
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> 'ReviewScope':
        _expect_keys(payload, {'schema_version', 'kind', 'paths', 'generated_artifacts', 'submodules', 'untracked', 'generation', 'scope_id'}, label='ReviewScope')
        if payload['schema_version'] != 'sergeant.review-scope.v1':
            raise ReviewWorldError('unknown ReviewScope schema version')
        paths = payload['paths']
        if not isinstance(paths, list) or not all((isinstance(x, str) for x in paths)):
            raise ReviewWorldError('ReviewScope paths must be a string array')
        obj = cls._create(kind=str(payload['kind']), paths=paths, generated_artifacts=str(payload['generated_artifacts']), submodules=str(payload['submodules']), untracked=str(payload['untracked']), generation=str(payload['generation']))
        if require_full_sha256(str(payload['scope_id']), 'scope_id') != obj.scope_id:
            raise ReviewWorldError('scope_id mismatch')
        return obj

@dataclass(frozen=True)
class GitHubDiffIdentity:
    schema_version: str
    repository: str
    base_commit: str
    base_tree: str
    head_commit: str
    head_tree: str
    algorithm_generation: str
    scope_id: str
    diff_id: str

    @classmethod
    def create(cls, *, repository: str, base_commit: str, base_tree: str, head_commit: str, head_tree: str, scope: ReviewScope, algorithm_generation: str='git-tree-transition-v1') -> 'GitHubDiffIdentity':
        repository_id = normalize_repository_identity(repository)
        base_commit = require_git_object_id(base_commit, 'base_commit')
        base_tree = require_git_object_id(base_tree, 'base_tree')
        head_commit = require_git_object_id(head_commit, 'head_commit')
        head_tree = require_git_object_id(head_tree, 'head_tree')
        if not algorithm_generation:
            raise ReviewWorldError('diff identity algorithm generation must be non-empty')
        require_full_sha256(scope.scope_id, 'scope_id')
        body = {'schema_version': 'sergeant.github-diff-identity.v1', 'repository': repository_id, 'base_commit': base_commit, 'base_tree': base_tree, 'head_commit': head_commit, 'head_tree': head_tree, 'algorithm_generation': algorithm_generation, 'scope_id': scope.scope_id}
        return cls('sergeant.github-diff-identity.v1', repository_id, base_commit, base_tree, head_commit, head_tree, algorithm_generation, scope.scope_id, sha256_id(body))

    def to_payload(self, *, include_id: bool=True) -> dict[str, object]:
        payload = {'schema_version': self.schema_version, 'repository': self.repository, 'base_commit': self.base_commit, 'base_tree': self.base_tree, 'head_commit': self.head_commit, 'head_tree': self.head_tree, 'algorithm_generation': self.algorithm_generation, 'scope_id': self.scope_id}
        if include_id:
            payload['diff_id'] = self.diff_id
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, object], *, scope: ReviewScope) -> 'GitHubDiffIdentity':
        _expect_keys(payload, {'schema_version', 'repository', 'base_commit', 'base_tree', 'head_commit', 'head_tree', 'algorithm_generation', 'scope_id', 'diff_id'}, label='GitHubDiffIdentity')
        if payload['schema_version'] != 'sergeant.github-diff-identity.v1':
            raise ReviewWorldError('unknown GitHubDiffIdentity schema version')
        if str(payload['scope_id']) != scope.scope_id:
            raise ReviewWorldError('diff scope_id does not match decoded ReviewScope')
        obj = cls.create(repository=str(payload['repository']), base_commit=str(payload['base_commit']), base_tree=str(payload['base_tree']), head_commit=str(payload['head_commit']), head_tree=str(payload['head_tree']), scope=scope, algorithm_generation=str(payload['algorithm_generation']))
        if require_full_sha256(str(payload['diff_id']), 'diff_id') != obj.diff_id:
            raise ReviewWorldError('diff_id mismatch')
        return obj

@dataclass(frozen=True)
class GitHubReviewWorld:
    schema_version: str
    kind: Literal['github_pr']
    repository: str
    pr_number: int
    diff: GitHubDiffIdentity
    scope: ReviewScope
    review_mode: Literal['head', 'merge_result']
    rab_id: str
    review_generation: str
    merge_commit: str | None
    merge_tree: str | None
    unresolved_state: tuple[str, ...]
    review_world_id: str

    @classmethod
    def create(cls, *, repository: str, pr_number: int, diff: GitHubDiffIdentity, scope: ReviewScope, review_mode: str, rab_id: str, review_generation: str, merge_commit: str | None=None, merge_tree: str | None=None, unresolved_state: Sequence[str]=()) -> 'GitHubReviewWorld':
        repository_id = normalize_repository_identity(repository)
        if pr_number <= 0:
            raise ReviewWorldError('pr_number must be positive')
        if diff.repository != repository_id:
            raise ReviewWorldError('diff repository identity does not match Review World repository')
        if diff.scope_id != scope.scope_id:
            raise ReviewWorldError('diff scope identity does not match Review World scope')
        if review_mode not in _REVIEW_MODES:
            raise ReviewWorldError(f'unknown review mode: {review_mode!r}')
        rab_id = require_full_sha256(rab_id, 'rab_id')
        if not review_generation:
            raise ReviewWorldError('review generation must be non-empty')
        unresolved = tuple(sorted({str(item).strip() for item in unresolved_state if str(item).strip()}))
        if unresolved:
            raise ReviewWorldError('exact positive Review World cannot contain unresolved state')
        if review_mode == 'merge_result':
            if merge_tree is None:
                raise ReviewWorldError('merge-result Review World requires exact merge tree identity')
            merge_tree = require_git_object_id(merge_tree, 'merge_tree')
            if merge_commit is not None:
                merge_commit = require_git_object_id(merge_commit, 'merge_commit')
        elif merge_commit is not None or merge_tree is not None:
            raise ReviewWorldError('head Review World cannot carry merge-result identity')
        body = {'schema_version': 'sergeant.review-world.github-pr.v1', 'kind': 'github_pr', 'repository': repository_id, 'pr_number': pr_number, 'diff': diff.to_payload(), 'scope': scope.to_payload(), 'review_mode': review_mode, 'rab_id': rab_id, 'review_generation': review_generation, 'merge_commit': merge_commit, 'merge_tree': merge_tree, 'unresolved_state': list(unresolved)}
        return cls('sergeant.review-world.github-pr.v1', 'github_pr', repository_id, pr_number, diff, scope, review_mode, rab_id, review_generation, merge_commit, merge_tree, unresolved, sha256_id(body))

    def to_payload(self, *, include_id: bool=True) -> dict[str, object]:
        payload = {'schema_version': self.schema_version, 'kind': self.kind, 'repository': self.repository, 'pr_number': self.pr_number, 'diff': self.diff.to_payload(), 'scope': self.scope.to_payload(), 'review_mode': self.review_mode, 'rab_id': self.rab_id, 'review_generation': self.review_generation, 'merge_commit': self.merge_commit, 'merge_tree': self.merge_tree, 'unresolved_state': list(self.unresolved_state)}
        if include_id:
            payload['review_world_id'] = self.review_world_id
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> 'GitHubReviewWorld':
        _expect_keys(payload, {'schema_version', 'kind', 'repository', 'pr_number', 'diff', 'scope', 'review_mode', 'rab_id', 'review_generation', 'merge_commit', 'merge_tree', 'unresolved_state', 'review_world_id'}, label='GitHubReviewWorld')
        if payload['schema_version'] != 'sergeant.review-world.github-pr.v1' or payload['kind'] != 'github_pr':
            raise ReviewWorldError('unknown GitHubReviewWorld schema/kind')
        scope_payload = payload['scope']
        diff_payload = payload['diff']
        if not isinstance(scope_payload, Mapping) or not isinstance(diff_payload, Mapping):
            raise ReviewWorldError('Review World scope/diff must be objects')
        scope = ReviewScope.from_payload(scope_payload)
        diff = GitHubDiffIdentity.from_payload(diff_payload, scope=scope)
        unresolved = payload['unresolved_state']
        if not isinstance(unresolved, list) or not all((isinstance(x, str) for x in unresolved)):
            raise ReviewWorldError('unresolved_state must be a string array')
        obj = cls.create(repository=str(payload['repository']), pr_number=int(payload['pr_number']), diff=diff, scope=scope, review_mode=str(payload['review_mode']), rab_id=str(payload['rab_id']), review_generation=str(payload['review_generation']), merge_commit=None if payload['merge_commit'] is None else str(payload['merge_commit']), merge_tree=None if payload['merge_tree'] is None else str(payload['merge_tree']), unresolved_state=unresolved)
        if require_full_sha256(str(payload['review_world_id']), 'review_world_id') != obj.review_world_id:
            raise ReviewWorldError('review_world_id mismatch')
        return obj

@dataclass(frozen=True)
class LocalReviewWorld:
    schema_version: str
    kind: Literal['local']
    repository: str | None
    local_snapshot_id: str
    scope: ReviewScope
    rab_id: str
    review_generation: str
    review_world_id: str

    @classmethod
    def create(cls, *, repository: str | None, local_snapshot_id: str, scope: ReviewScope, rab_id: str, review_generation: str) -> 'LocalReviewWorld':
        repository_id = normalize_repository_identity(repository) if repository else None
        local_snapshot_id = require_full_sha256(local_snapshot_id, 'local_snapshot_id')
        rab_id = require_full_sha256(rab_id, 'rab_id')
        if not review_generation:
            raise ReviewWorldError('review generation must be non-empty')
        body = {'schema_version': 'sergeant.review-world.local.v1', 'kind': 'local', 'repository': repository_id, 'local_snapshot_id': local_snapshot_id, 'scope': scope.to_payload(), 'rab_id': rab_id, 'review_generation': review_generation}
        return cls('sergeant.review-world.local.v1', 'local', repository_id, local_snapshot_id, scope, rab_id, review_generation, sha256_id(body))

    def to_payload(self, *, include_id: bool=True) -> dict[str, object]:
        payload = {'schema_version': self.schema_version, 'kind': self.kind, 'repository': self.repository, 'local_snapshot_id': self.local_snapshot_id, 'scope': self.scope.to_payload(), 'rab_id': self.rab_id, 'review_generation': self.review_generation}
        if include_id:
            payload['review_world_id'] = self.review_world_id
        return payload

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> 'LocalReviewWorld':
        _expect_keys(payload, {'schema_version', 'kind', 'repository', 'local_snapshot_id', 'scope', 'rab_id', 'review_generation', 'review_world_id'}, label='LocalReviewWorld')
        if payload['schema_version'] != 'sergeant.review-world.local.v1' or payload['kind'] != 'local':
            raise ReviewWorldError('unknown LocalReviewWorld schema/kind')
        scope_payload = payload['scope']
        if not isinstance(scope_payload, Mapping):
            raise ReviewWorldError('Local Review World scope must be an object')
        scope = ReviewScope.from_payload(scope_payload)
        obj = cls.create(repository=None if payload['repository'] is None else str(payload['repository']), local_snapshot_id=str(payload['local_snapshot_id']), scope=scope, rab_id=str(payload['rab_id']), review_generation=str(payload['review_generation']))
        if require_full_sha256(str(payload['review_world_id']), 'review_world_id') != obj.review_world_id:
            raise ReviewWorldError('review_world_id mismatch')
        return obj
