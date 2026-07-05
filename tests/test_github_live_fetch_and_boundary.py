from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from main_review.boundary import check_action_boundary, repository_visibility_policy
from main_review.github_live_fetch import GitHubFetchError, fetch_pr_comments_live


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_live_fetch_uses_read_only_github_endpoints() -> None:
    calls: list[str] = []

    def fake_urlopen(request, timeout=15):
        calls.append(request.full_url)
        assert request.get_method() == "GET"
        return _FakeResponse([{"body": "review note"}])

    with patch("urllib.request.urlopen", fake_urlopen):
        result = fetch_pr_comments_live("owner/repo", 7, token="read-only-token")

    assert result.source == "live-github-api"
    assert len(result.all_comments) == 2
    assert calls == [
        "https://api.github.com/repos/owner/repo/issues/7/comments",
        "https://api.github.com/repos/owner/repo/pulls/7/comments",
    ]


def test_live_fetch_raises_clear_error_on_http_failure() -> None:
    def fake_urlopen(request, timeout=15):
        raise urllib.error.HTTPError(request.full_url, 403, "rate limited", {}, io.BytesIO(b'{"message":"rate limit"}'))

    with patch("urllib.request.urlopen", fake_urlopen):
        with pytest.raises(GitHubFetchError, match="HTTP 403"):
            fetch_pr_comments_live("owner/repo", 7)


def test_boundary_refuses_patch_writing_and_untrusted_execution() -> None:
    assert check_action_boundary("write_patch")["allowed"] is False
    assert check_action_boundary("review")["allowed"] is True
    assert check_action_boundary("custom", {"executes_untrusted_code": True})["allowed"] is False
    assert check_action_boundary("custom", {"requires_write_token": True})["allowed"] is False


def test_visibility_policy_splits_public_and_private_material() -> None:
    policy = repository_visibility_policy(is_public=True)

    assert policy["visibility"] == "public-open-source"
    assert "review engine" in policy["keep_public"]
    assert "THETECHGUY/Hunter private project rules" in policy["keep_private"]
