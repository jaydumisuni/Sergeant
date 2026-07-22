from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "controlled-self-learning-week-1.yml"


def _job_block(workflow: str, job: str, *, next_job: str | None = None) -> str:
    marker = f"  {job}:\n"
    start = workflow.index(marker)
    if next_job is None:
        return workflow[start:]
    end = workflow.index(f"  {next_job}:\n", start + len(marker))
    return workflow[start:end]


def test_controlled_learning_targets_main_and_uses_the_active_pr_branch() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "      - main" in workflow
    assert "      - fix/coderabbit-campaign-integrity" not in workflow
    assert "TARGET_BRANCH: ${{ github.event.pull_request.head.ref }}" in workflow
    assert "AUTHORITY_HEAD: ${{ github.event.pull_request.head.sha }}" in workflow
    assert '--target-branch "${TARGET_BRANCH}"' in workflow


def test_round_authorization_remains_explicit_and_model_free_review_is_preserved() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    validate = _job_block(workflow, "validate", next_job="learn")
    learn = _job_block(workflow, "learn", next_job="publish")

    assert 'index("self-learning-authorized") != null' in validate
    assert '[[ "${subject}" == START_CONTROLLED_SELF_LEARNING* ]]' in validate
    assert 'SERGEANT_LLM_ENABLED: "false"' in workflow
    assert 'SERGEANT_CPL_ENABLED: "false"' in workflow
    assert "models: read" in learn
    assert "contents: read" in learn
    assert "contents: write" not in learn


def test_publish_job_is_a_read_only_owner_handoff() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    publish = _job_block(workflow, "publish")

    assert "name: Stage owner-controlled proposal handoff" in publish
    assert "contents: read" in publish
    assert "contents: write" not in publish
    assert "pull-requests: write" not in publish
    assert "git push" not in publish
    assert "gh pr create" not in publish
    assert 'test "$(jq -r \'.automatic_promotions\' "${index}")" = "0"' in publish
    assert 'test "$(jq -r \'.automatic_merges\' "${index}")" = "0"' in publish
    assert 'test "$(jq -r \'.authority_head\' "${index}")" = "${AUTHORITY_HEAD}"' in publish
    assert "This workflow has no branch, pull-request, merge, or promotion authority." in publish
