"""The real client is exercised with a fake session and never opens a socket."""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest
import requests

from lupaxa.github_token_validator.client import (
    GitHubRateLimitError,
    GitHubResponse,
    GitHubTransportError,
    GitHubUnauthorizedError,
    RequestsGitHubClient,
)

_TOKEN = "ghp_secretvalue"


def _response(status: int, payload: object | None = None, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status
    response.headers = {"X-RateLimit-Limit": "5000"}
    response.text = text
    if payload is None:
        response.json.side_effect = ValueError("no json")
    else:
        response.json.return_value = payload
    return response


def _client(response: MagicMock | Exception) -> tuple[RequestsGitHubClient, MagicMock]:
    session = MagicMock()
    if isinstance(response, Exception):
        session.get.side_effect = response
    else:
        session.get.return_value = response
    return RequestsGitHubClient(_TOKEN, 10, session=session), session


def test_get_sends_bearer_headers_and_discards_the_body() -> None:
    client, session = _client(
        _response(200, [{"path": "leaked-repo-path"}], "leaked-repo-path")
    )
    result = client.get("/user/repos?per_page=1")
    assert result == GitHubResponse(200, {"X-RateLimit-Limit": "5000"}, None)
    assert "leaked-repo-path" not in repr(result)
    session.get.return_value.json.assert_not_called()
    url = session.get.call_args.args[0]
    headers = session.get.call_args.kwargs["headers"]
    assert url == "https://api.github.com/user/repos?per_page=1"
    assert headers["Authorization"] == "Bearer ghp_secretvalue"
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["X-GitHub-Api-Version"] == "2022-11-28"
    assert headers["User-Agent"] == "lupaxa-github-token-validator"
    assert session.get.call_args.kwargs["timeout"] == 10


def test_read_login_keeps_only_the_login_string() -> None:
    client, _session = _client(
        _response(200, {"login": "octocat", "name": "leaked-name"})
    )
    result = client.get("/user", read_login=True)
    assert result.login == "octocat"
    assert "leaked-name" not in repr(result)


def test_missing_login_is_none() -> None:
    client, _session = _client(_response(200, {"id": 1}))
    assert client.get("/user", read_login=True).login is None


@pytest.mark.parametrize(
    ("status", "error_type", "message"),
    [
        (401, GitHubUnauthorizedError, "GitHub rejected the token (HTTP 401)."),
        (429, GitHubRateLimitError, "GitHub rate limit exceeded (HTTP 429)."),
    ],
)
def test_auth_and_rate_limit_errors_omit_the_token(
    status: int,
    error_type: type[Exception],
    message: str,
) -> None:
    client, _session = _client(_response(status, text=_TOKEN))
    with pytest.raises(error_type, match=re.escape(message)) as caught:
        client.get("/user")
    assert _TOKEN not in str(caught.value)


def test_other_request_errors_omit_the_token() -> None:
    client, _session = _client(requests.exceptions.InvalidURL(_TOKEN))
    with pytest.raises(
        GitHubTransportError, match=re.escape("GitHub request failed.")
    ) as caught:
        client.get("/user")
    assert _TOKEN not in str(caught.value)


def test_forbidden_rate_limit_stops_the_run() -> None:
    exhausted = _response(403, text=_TOKEN)
    exhausted.headers["X-RateLimit-Remaining"] = "0"
    client, _session = _client(exhausted)
    with pytest.raises(
        GitHubRateLimitError,
        match=re.escape("GitHub rate limit exceeded (HTTP 403)."),
    ) as caught:
        client.get("/user")
    assert _TOKEN not in str(caught.value)
    retrying = _response(403, text=_TOKEN)
    retrying.headers["Retry-After"] = "12"
    retry_client, _session = _client(retrying)
    with pytest.raises(GitHubRateLimitError):
        retry_client.get("/orgs/acme")


def test_forbidden_with_remaining_quota_is_not_a_rate_limit() -> None:
    denied = _response(403, text=_TOKEN)
    denied.headers["X-RateLimit-Remaining"] = "10"
    client, _session = _client(denied)
    assert client.get("/user").status_code == 403


def test_owned_session_is_closed_and_injected_session_is_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = MagicMock()
    monkeypatch.setattr(requests, "Session", lambda: created)
    owned = RequestsGitHubClient(_TOKEN, 10)
    owned.close()
    created.close.assert_called_once()
    injected = MagicMock()
    client = RequestsGitHubClient(_TOKEN, 10, session=injected)
    client.close()
    injected.close.assert_not_called()


def test_timeout_and_connection_errors_omit_the_token() -> None:
    timeout_client, _session = _client(requests.Timeout(_TOKEN))
    with pytest.raises(
        GitHubTransportError, match=re.escape("GitHub request timed out.")
    ) as caught:
        timeout_client.get("/user")
    assert _TOKEN not in str(caught.value)
    connection_client, _session = _client(requests.ConnectionError(_TOKEN))
    with pytest.raises(
        GitHubTransportError,
        match=re.escape("GitHub request failed: connection error."),
    ) as caught:
        connection_client.get("/user")
    assert _TOKEN not in str(caught.value)
