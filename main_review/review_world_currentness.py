"""SAE-10 Review World currentness and invalidation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from main_review.review_world import GitHubReviewWorld, LocalReviewWorld
CurrentnessState = Literal['CURRENT', 'STALE', 'UNKNOWN_CURRENTNESS']

@dataclass(frozen=True)
class CurrentnessResult:
    state: CurrentnessState
    reasons: tuple[str, ...]

def _finish(reasons: list[str], *, unknown: bool=False) -> CurrentnessResult:
    unique = tuple(dict.fromkeys(reasons))
    if unknown:
        return CurrentnessResult('UNKNOWN_CURRENTNESS', unique)
    if unique:
        return CurrentnessResult('STALE', unique)
    return CurrentnessResult('CURRENT', ())

def check_github_currentness(frozen: GitHubReviewWorld, current: GitHubReviewWorld | None, *, rab_authorized: bool | None) -> CurrentnessResult:
    frozen.validate()
    if current is None:
        return CurrentnessResult('UNKNOWN_CURRENTNESS', ('comparison_facts_unavailable',))
    current.validate()
    reasons = []
    if frozen.repository != current.repository:
        reasons.append('repository_mismatch')
    if frozen.pr_number != current.pr_number:
        reasons.append('pr_number_mismatch')
    if frozen.diff.base_commit != current.diff.base_commit or frozen.diff.base_tree != current.diff.base_tree:
        reasons.append('base_identity_mismatch')
    if frozen.diff.head_commit != current.diff.head_commit or frozen.diff.head_tree != current.diff.head_tree:
        reasons.append('head_identity_mismatch')
    if frozen.diff.diff_id != current.diff.diff_id:
        reasons.append('diff_identity_mismatch')
    if frozen.scope.scope_id != current.scope.scope_id:
        reasons.append('scope_mismatch')
    if frozen.review_mode != current.review_mode or frozen.merge_commit != current.merge_commit or frozen.merge_tree != current.merge_tree:
        reasons.append('merge_result_mismatch')
    if frozen.rab_id != current.rab_id:
        reasons.append('rab_mismatch')
    if rab_authorized is None:
        reasons.append('rab_authorization_unknown')
    elif not rab_authorized:
        reasons.append('rab_unauthorized_or_revoked')
    if frozen.review_generation != current.review_generation:
        reasons.append('review_generation_mismatch')
    if current.unresolved_state:
        reasons.append('unresolved_material_state')
    return _finish(reasons, unknown=rab_authorized is None)

def check_local_currentness(frozen: LocalReviewWorld, current: LocalReviewWorld | None, *, rab_authorized: bool | None) -> CurrentnessResult:
    frozen.validate()
    if current is None:
        return CurrentnessResult('UNKNOWN_CURRENTNESS', ('comparison_facts_unavailable',))
    current.validate()
    reasons = []
    if frozen.repository != current.repository:
        reasons.append('repository_mismatch')
    if frozen.local_snapshot_id != current.local_snapshot_id:
        reasons.append('local_snapshot_mutation')
    if frozen.scope.scope_id != current.scope.scope_id:
        reasons.append('scope_mismatch')
    if frozen.rab_id != current.rab_id:
        reasons.append('rab_mismatch')
    if rab_authorized is None:
        reasons.append('rab_authorization_unknown')
    elif not rab_authorized:
        reasons.append('rab_unauthorized_or_revoked')
    if frozen.review_generation != current.review_generation:
        reasons.append('review_generation_mismatch')
    return _finish(reasons, unknown=rab_authorized is None)
