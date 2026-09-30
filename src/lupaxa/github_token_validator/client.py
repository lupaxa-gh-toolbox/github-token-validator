"""Read-only GitHub GET client."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

import requests
from requests import Session

from lupaxa.github_token_validator.constants import (
    API_BASE_URL,
    API_VERSION,
    USER_AGENT,
)


class GitHubUnauthorizedError(Exception):
    """GitHub returned HTTP 401."""


class GitHubRateLimitError(Exception):
    """GitHub returned HTTP 429."""


class GitHubTransportError(Exception):
    """The request timed out or the connection failed."""


@dataclass(frozen=True, slots=True)
class GitHubResponse:
    """Status, headers, and the optional login from GET /user."""

    status_code: int
    headers: dict[str, str]
    login: str | None


class GitHubClient(Protocol):
    """Injectable GET client used by the probe runner."""

    def get(self, path: str, *, read_login: bool = False) -> GitHubResponse:
        """Perform one GET and return status data."""
        raise NotImplementedError


class RequestsGitHubClient:
    """requests-backed client. The token is sent only as a Bearer header."""

    def __init__(
        self, token: str, timeout: int, session: Session | None = None
    ) -> None:
        """Store the token, timeout, and session."""
        self._token = token
        self._timeout = timeout
        self._owns_session = session is None
        self._session = requests.Session() if session is None else session

    def close(self) -> None:
        """Close the session this client created."""
        if self._owns_session:
            self._session.close()

    def get(self, path: str, *, read_login: bool = False) -> GitHubResponse:
        """GET ``path`` and discard the body unless ``read_login`` is set."""
        try:
            response = self._session.get(
                f"{API_BASE_URL}{path}",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": API_VERSION,
                    "User-Agent": USER_AGENT,
                },
                timeout=self._timeout,
            )
        except requests.Timeout:
            raise GitHubTransportError("GitHub request timed out.") from None
        except requests.ConnectionError:
            raise GitHubTransportError(
                "GitHub request failed: connection error."
            ) from None
        except requests.RequestException:
            raise GitHubTransportError("GitHub request failed.") from None
        if response.status_code == 401:
            raise GitHubUnauthorizedError("GitHub rejected the token (HTTP 401).")
        if _rate_limited(response.status_code, response.headers):
            raise GitHubRateLimitError(
                f"GitHub rate limit exceeded (HTTP {response.status_code})."
            )
        return GitHubResponse(
            response.status_code,
            {str(key): str(value) for key, value in response.headers.items()},
            _login(response) if read_login else None,
        )


def _rate_limited(status_code: int, headers: Mapping[str, str]) -> bool:
    """Return whether this response is a primary or secondary rate limit."""
    if status_code == 429:
        return True
    if status_code != 403:
        return False
    remaining = _header(headers, "X-RateLimit-Remaining")
    if remaining == "0":
        return True
    return _header(headers, "Retry-After") is not None


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Return one header, ignoring case and blank text."""
    wanted = name.lower()
    for key, value in headers.items():
        text = str(value).strip()
        if key.lower() == wanted and text != "":
            return text
    return None


def _login(response: requests.Response) -> str | None:
    try:
        payload: object = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("login")
    if isinstance(value, str) and value.strip() != "":
        return value
    return None
