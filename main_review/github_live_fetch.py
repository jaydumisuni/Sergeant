"""Read-only live GitHub API fetch for PR comments.

This module is the only built-in Sergeant module that makes network calls to
GitHub. The network-free parser remains github_collector.py.

Security posture:
- GET only.
- Public/read-only data only.
- Optional read-only token for rate limits/private repos.
- No PR code execution.
- No shell execution.
- No eval/exec of response data.
- Failures raise GitHubFetchError instead of pretending there were no comments.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


class GitHubFetchError(RuntimeError):
    """Raised when a live GitHub API fetch fails."""


@dataclass(frozen=True)
class GitHubFetchResult:
    repository: str
    pr_number: int
    issue_comments: list[dict[str, Any]]
    review_comments: list[dict[str, Any]]
    source: str = "live-github-api"

    @property
    def all_comments(self) -> list[dict[str, Any]]:
        return [*self.issue_comments, *self.review_comments]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["all_comments"] = self.all_comments
        return payload


def _get_json(url: str, token: str | None) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sergeant-review"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace") if error.fp else ""
        raise GitHubFetchError(f"GitHub API returned HTTP {error.code} for {url}: {body[:300]}") from error
    except urllib.error.URLError as error:
        raise GitHubFetchError(f"Network error reaching {url}: {error.reason}") from error
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise GitHubFetchError(f"GitHub API returned non-JSON response for {url}") from error


def fetch_pr_comments_live(repository: str, pr_number: int, *, token: str | None = None, base_url: str = "https://api.github.com") -> GitHubFetchResult:
    """Fetch real PR issue comments and review comments from GitHub."""
    if "/" not in repository:
        raise GitHubFetchError(f'repository must be "owner/repo", got: {repository!r}')
    if pr_number <= 0:
        raise GitHubFetchError(f"pr_number must be positive, got: {pr_number!r}")
    base = base_url.rstrip("/")
    issue_comments_url = f"{base}/repos/{repository}/issues/{pr_number}/comments"
    review_comments_url = f"{base}/repos/{repository}/pulls/{pr_number}/comments"
    issue_comments = _get_json(issue_comments_url, token)
    review_comments = _get_json(review_comments_url, token)
    if not isinstance(issue_comments, list):
        raise GitHubFetchError(f"Unexpected issue-comments payload shape from {issue_comments_url}")
    if not isinstance(review_comments, list):
        raise GitHubFetchError(f"Unexpected review-comments payload shape from {review_comments_url}")
    return GitHubFetchResult(
        repository=repository,
        pr_number=pr_number,
        issue_comments=[item for item in issue_comments if isinstance(item, dict)],
        review_comments=[item for item in review_comments if isinstance(item, dict)],
    )
