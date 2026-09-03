import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import main_review.review_world as rw
import main_review.review_world_currentness as currentness
import main_review.review_world_git as git_world

A = 'a' * 40
B = 'b' * 40
C = 'c' * 40
D = 'd' * 40
R = '1' * 64
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/79-sae10-review-world-rab-manifest.json'


def _github_world(pr_number: int) -> rw.GitHubReviewWorld:
    scope = rw.ReviewScope.repository()
    diff = rw.GitHubDiffIdentity.create(
        repository='o/r',
        base_commit=A,
        base_tree=C,
        head_commit=B,
        head_tree=D,
        scope=scope,
    )
    return rw.GitHubReviewWorld.create(
        repository='o/r',
        pr_number=pr_number,
        diff=diff,
        scope=scope,
        review_mode='head',
        rab_id=R,
        review_generation='g',
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ['git', *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
        env={'PATH': os.environ.get('PATH', '')},
    ).stdout.strip()


def _init_repo(root: Path) -> None:
    _git(root, 'init', '-q')
    _git(root, 'config', 'user.name', 'T')
    _git(root, 'config', 'user.email', 't@x')
    (root / 'src').mkdir()
    (root / 'src/a').write_text('a\n')
    _git(root, 'add', '.')
    _git(root, 'commit', '-qm', 'base')


def test_github_currentness_rejects_other_pull_request_identity():
    result = currentness.check_github_currentness(
        _github_world(1),
        _github_world(2),
        rab_authorized=True,
    )
    assert result.state == 'STALE'
    assert 'pr_number_mismatch' in result.reasons


@pytest.mark.skipif(shutil.which('git') is None, reason='git unavailable')
def test_local_snapshot_rejects_direct_forged_scope_before_hashing(tmp_path):
    _init_repo(tmp_path)
    valid = rw.ReviewScope.selected_paths(['src/a'])
    forged = rw.ReviewScope(
        schema_version=valid.schema_version,
        kind=valid.kind,
        paths=valid.paths,
        generated_artifacts=valid.generated_artifacts,
        submodules=valid.submodules,
        untracked=valid.untracked,
        generation=valid.generation,
        scope_id='f' * 64,
    )
    with pytest.raises(rw.ReviewWorldError, match='ReviewScope|scope_id|non-canonical'):
        git_world.build_local_snapshot(
            tmp_path,
            scope=forged,
            policy=git_world.LocalSnapshotPolicy.exclude_untracked(),
        )


def test_v9_completion_hostile_review_generation_is_mechanically_bound():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    review = manifest['github_hostile_review']['exact_v9_completion_hostile_review']
    assert review['reviewed_head'] == '940fd609ebc18a62bd678a09518f43ed35b04a68'
    assert review['review_run_id'] == '2c410bcc-a73a-4929-b8de-e8c5b601cba1'
    assert review['actionable_findings'] == 3
    assert set(review['valid_findings']) == {
        'github_currentness_pr_number_identity_omission',
        'local_snapshot_forged_scope_not_validated_before_hashing',
        'v9_completion_review_generation_not_mechanically_bound',
    }
    assert set(review['accepted_repairs']) == {
        'github_currentness_compares_pr_number',
        'local_snapshot_validates_scope_before_path_selection_or_hashing',
        'bind_v9_completion_review_generation_and_reproof',
    }
    assert review['red_regressions'] == {'failed_as_expected': 3}
    assert review['replacement_local_reproof'] == {'failed': 0, 'passed': 3, 'xfailed': 0}
