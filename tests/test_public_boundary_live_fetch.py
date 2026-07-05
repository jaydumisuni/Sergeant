from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from main_review.boundary import check_action_boundary, repository_visibility_policy
from main_review.cli import main
from main_review.github_live_fetch import GitHubFetchError, fetch_pr_comments_live


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_live_github_fetch_uses_get_requests() -> None:
    calls = []

    def fake_urlopen(request, timeout):
        calls.append({"url": request.full_url, "method": request.get_method(), "timeout": timeout})
        return FakeResponse([{"body": "review note", "html_url": "https://github.com/example/repo/pull/1#issuecomment-1"}])

    with patch("urllib.request.urlopen", fake_urlopen):
        result = fetch_pr_comments_live("example/repo", 1, base_url="https://api.github.test")

    assert result.repository == "example/repo"
    assert result.pr_number == 1
    assert len(result.all_comments) == 2
    assert [call["method"] for call in calls] == ["GET", "GET"]
    assert calls[0]["url"].endswith("/repos/example/repo/issues/1/comments")
    assert calls[1]["url"].endswith("/repos/example/repo/pulls/1/comments")


def test_live_github_fetch_rejects_bad_repository_shape() -> None:
    with pytest.raises(GitHubFetchError):
        fetch_pr_comments_live("bad-shape", 1)


def test_boundary_refuses_out_of_scope_reviewer_actions() -> None:
    blocked = check_action_boundary("edit_code")
    allowed = check_action_boundary("live_fetch_read_only")
    risky_context = check_action_boundary("review", {"requires_write_token": True})

    assert blocked["allowed"] is False
    assert allowed["allowed"] is True
    assert risky_context["allowed"] is False


def test_visibility_policy_separates_public_and_private_parts() -> None:
    policy = repository_visibility_policy(is_public=True)

    assert policy["visibility"] == "public-open-source"
    assert "review engine" in policy["keep_public"]
    assert "private repo memory" in policy["keep_private"]


def test_cli_boundary_and_live_fetch_commands(capsys) -> None:
    assert main(["boundary", "edit_code", "--pretty"]) == 0
    boundary_output = capsys.readouterr().out
    assert '"allowed": false' in boundary_output

    def fake_urlopen(request, timeout):
        return FakeResponse([])

    with patch("urllib.request.urlopen", fake_urlopen):
        assert main(["live-github-comments", "example/repo", "1", "--base-url", "https://api.github.test", "--pretty"]) == 0
    live_output = capsys.readouterr().out
    assert '"source": "live-github-api"' in live_output
