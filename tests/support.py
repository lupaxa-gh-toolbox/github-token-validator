"""Fake GitHub client for tests. It does not open a socket."""

from __future__ import annotations

from lupaxa.github_token_validator.client import GitHubResponse


class FakeGitHubClient:
    """Scripted responses keyed by request path."""

    def __init__(
        self,
        responses: dict[str, GitHubResponse | Exception],
        default: GitHubResponse | Exception | None = None,
    ) -> None:
        """Store scripted responses."""
        self.calls: list[tuple[str, bool]] = []
        self.closed = False
        self._responses = responses
        self._default = default

    def close(self) -> None:
        """Record that the runner finished with this client."""
        self.closed = True

    def get(self, path: str, *, read_login: bool = False) -> GitHubResponse:
        """Return the scripted response for ``path``."""
        self.calls.append((path, read_login))
        item = self._responses.get(path, self._default)
        if item is None:
            raise AssertionError(path)
        if isinstance(item, Exception):
            raise item
        if read_login:
            return item
        return GitHubResponse(item.status_code, item.headers, None)


def user_response(
    login: str | None = "octocat",
    scopes: str | None = "repo",
) -> GitHubResponse:
    """Build a GET /user response with rate-limit headers."""
    headers = {
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Used": "7",
        "X-RateLimit-Remaining": "4993",
        "X-RateLimit-Reset": "1700000000",
    }
    if scopes is not None:
        headers["X-OAuth-Scopes"] = scopes
    return GitHubResponse(200, headers, login)
